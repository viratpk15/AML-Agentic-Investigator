"""Error classification logic — determines if an LLM failure is retryable.

Keeps provider-agnostic error inspection in one place so the failover manager
does not need to import or depend on any provider SDK.
"""

from __future__ import annotations

import re
from typing import Optional

from aml_copilot.llm.exceptions import ProviderAuthError, ProviderRetryableError
from aml_copilot.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Retryable HTTP status codes
# ---------------------------------------------------------------------------
_RETRYABLE_STATUS_CODES = {
    404,   # Not Found — model deprecated/missing on this provider; try next provider
    413,   # Request Entity Too Large / request too large
    429,   # Too Many Requests / rate limit / quota
    500,   # Internal Server Error (transient)
    502,   # Bad Gateway
    503,   # Service Unavailable
    504,   # Gateway Timeout
}

# Non-retryable status codes — switching provider won't help
_AUTH_STATUS_CODES = {
    401,   # Unauthorized — invalid API key
    403,   # Forbidden — wrong permissions / billing issue specific to account
    # Note: 404 is intentionally NOT here — a missing/deprecated model on one provider
    # should still trigger failover to try the next provider in the chain.
}

# ---------------------------------------------------------------------------
# Keyword patterns for error message inspection
# ---------------------------------------------------------------------------
_RETRYABLE_PATTERNS = [
    r"request\s+too\s+large",
    r"context\s+(length|window)\s+exceeded",
    r"maximum\s+context\s+length",
    r"token\s+(limit|quota|budget)",
    r"rate\s+limit",
    r"tpm\s+limit",
    r"rpm\s+limit",
    r"quota\s+(exceeded|exhausted|limit)",
    r"too\s+many\s+requests",
    r"model\s+(overloaded|unavailable|not\s+available|not\s+found|no\s+longer\s+available|deprecated)",
    r"service\s+(unavailable|temporarily\s+unavailable)",
    r"connection\s+(error|refused|reset|timed?\s*out)",
    r"timeout",
    r"server\s+(error|unavailable)",
    r"5\d{2}\b",
    r"overloaded",
    r"capacity",
    r"try\s+again",
    r"retry",
    r"not_found",
    r"NOT_FOUND",
]

_AUTH_PATTERNS = [
    r"invalid\s+api\s+key",
    r"authentication\s+(failed|error)",
    r"unauthorized",
    r"api\s+key\s+(invalid|not\s+found|missing|expired)",
    r"incorrect\s+api\s+key",
    r"no\s+api\s+key\s+provided",
    r"invalid\s+(credentials?|token)",
    r"permission\s+denied",
    r"billing\s+(not\s+active|inactive|suspended)",
    r"malformed\s+(request|tool|schema|function)",
    r"invalid\s+request",
    r"schema\s+(validation|error)",
    r"tool\s+(definition|schema)\s+(invalid|error)",
]

_RETRYABLE_RE = re.compile("|".join(_RETRYABLE_PATTERNS), re.IGNORECASE)
_AUTH_RE = re.compile("|".join(_AUTH_PATTERNS), re.IGNORECASE)


def _extract_status_code(exc: BaseException) -> Optional[int]:
    """Attempt to extract an HTTP status code from a provider exception.

    Checks common SDK attributes: status_code, status, http_status, code.
    Also scans the error message text for patterns like '413'.
    """
    for attr in ("status_code", "status", "http_status", "code", "response_status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int) and 100 <= val < 600:
            return val

    # Some SDK wrappers embed it in a nested response object
    response = getattr(exc, "response", None)
    if response is not None:
        for attr in ("status_code", "status"):
            val = getattr(response, attr, None)
            if isinstance(val, int) and 100 <= val < 600:
                return val

    # Fall back to scanning the string representation
    msg = str(exc)
    match = re.search(r"\b(4\d{2}|5\d{2})\b", msg)
    if match:
        return int(match.group(1))

    return None


def classify_provider_error(
    exc: BaseException,
    provider: str = "unknown",
) -> ProviderRetryableError | ProviderAuthError:
    """Classify a raw provider SDK exception as retryable or non-retryable.

    Returns either:
    - ProviderRetryableError: safe to attempt failover to next provider
    - ProviderAuthError: should NOT trigger failover (misconfiguration)
    """
    message = str(exc)
    status_code = _extract_status_code(exc)

    logger.debug(
        f"[LLM Classifier] Classifying error from '{provider}': "
        f"status={status_code}, type={type(exc).__name__}"
    )

    # --- Check HTTP status code first (most reliable) ---
    if status_code in _AUTH_STATUS_CODES:
        return ProviderAuthError(
            f"[{provider}] Authentication/permission error (HTTP {status_code}): {message}",
            provider=provider,
            status_code=status_code,
        )

    if status_code in _RETRYABLE_STATUS_CODES:
        reason = _reason_from_status(status_code)
        return ProviderRetryableError(
            f"[{provider}] Retryable provider error (HTTP {status_code}): {message}",
            provider=provider,
            status_code=status_code,
            reason=reason,
        )

    # --- Fall back to message text matching ---
    if _AUTH_RE.search(message):
        return ProviderAuthError(
            f"[{provider}] Authentication/configuration error: {message}",
            provider=provider,
            status_code=status_code or 0,
        )

    if _RETRYABLE_RE.search(message):
        reason = _reason_from_message(message)
        return ProviderRetryableError(
            f"[{provider}] Retryable provider error: {message}",
            provider=provider,
            status_code=status_code or 0,
            reason=reason,
        )

    # --- Unknown errors are treated as retryable by default ---
    # The investigation should not crash on an ambiguous error; let the
    # fallback try. If the fallback also fails, the error chain is preserved.
    logger.warning(
        f"[LLM Classifier] Unclassified error from '{provider}' (treating as retryable): {message}"
    )
    return ProviderRetryableError(
        f"[{provider}] Unclassified provider error (treated as retryable): {message}",
        provider=provider,
        status_code=status_code or 0,
        reason="unclassified",
    )


def _reason_from_status(status_code: int) -> str:
    return {
        404: "model_not_found",
        413: "request_too_large",
        429: "rate_limit_exceeded",
        500: "server_error",
        502: "bad_gateway",
        503: "service_unavailable",
        504: "gateway_timeout",
    }.get(status_code, "provider_error")


def _reason_from_message(message: str) -> str:
    """Extract a short reason slug from the error message for SSE telemetry."""
    low = message.lower()
    if "too large" in low or "context length" in low or "token" in low:
        return "request_too_large"
    if "rate limit" in low or "tpm" in low or "rpm" in low:
        return "rate_limit_exceeded"
    if "quota" in low:
        return "quota_exhausted"
    if "timeout" in low or "timed out" in low:
        return "timeout"
    if "unavailable" in low or "overload" in low:
        return "service_unavailable"
    return "provider_error"
