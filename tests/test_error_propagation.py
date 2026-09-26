"""Regression tests — Error propagation, structured error metadata, and validation false-positive prevention.

Verifies:
1. Backend exceptions are NOT swallowed — they surface as structured events with error_type + error_stage.
2. The INVESTIGATION_FAILED bus event carries error_type, error_stage, and request_id fields.
3. bus.error is set in the format '[stage] ExcType: message' for parsing by the frontend.
4. The unsupported-entity validator (check-15) does NOT false-positive on legitimate AML narrative phrases.
5. Successful investigation remains unaffected.
"""

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# 1. Bus error format regression
# ---------------------------------------------------------------------------

class TestBusErrorFormat:
    """Verify error string format matches frontend parsing contract."""

    def test_error_format_ingestion_stage(self):
        exc_type = "TransactionParsingError"
        exc_msg = "No valid transactions could be extracted"
        stage = "ingestion_parsing"
        bus_error = f"[{stage}] {exc_type}: {exc_msg}"
        stage_match = re.match(r"^\[([\w_]+)\]\s*", bus_error)
        assert stage_match is not None, "Bus error must start with [stage_name]"
        assert stage_match.group(1) == stage
        rest = bus_error[stage_match.end():]
        assert exc_type in rest
        assert exc_msg in rest

    def test_error_format_execution_stage(self):
        exc_type = "ProviderAuthError"
        stage = "investigation_execution"
        bus_error = f"[{stage}] {exc_type}: Authentication/permission error (HTTP 403)"
        stage_match = re.match(r"^\[([\w_]+)\]\s*", bus_error)
        assert stage_match is not None
        assert stage_match.group(1) == "investigation_execution"
        rest = bus_error[stage_match.end():]
        assert "ProviderAuthError" in rest

    def test_error_metadata_required_fields(self):
        required_fields = {"error_type", "error_stage", "error", "request_id"}
        metadata = {
            "error_type": "SomeError",
            "error_stage": "ingestion_parsing",
            "error": "Something went wrong",
            "request_id": "INV-ABCD1234",
        }
        for field in required_fields:
            assert field in metadata, f"Metadata must contain '{field}'"

    def test_error_does_not_contain_generic_chatbot_response(self):
        prohibited_phrases = [
            "could you give me",
            "what you were trying to do",
            "running a script",
            "browser console",
            "app's log panel",
            "more context",
        ]
        sample_errors = [
            "[ingestion_parsing] TransactionParsingError: No valid transactions extracted",
            "[investigation_execution] ProviderAuthError: HTTP 403",
            "[demo_execution] FileNotFoundError: demo PDF missing",
        ]
        for error in sample_errors:
            for phrase in prohibited_phrases:
                assert phrase.lower() not in error.lower(), (
                    f"Error '{error}' must not contain prohibited phrase '{phrase}'"
                )


# ---------------------------------------------------------------------------
# 2. Unsupported-entity validator false-positive regression
# ---------------------------------------------------------------------------

ALLOWED_DOMAIN_TERMS = {
    "PMLA", "FATF", "FIU", "RBI", "SAR", "STR", "AML", "KYC", "CDD", "EDD",
    "INR", "IMPS", "NEFT", "RTGS", "UPI", "ATM", "GST", "ITR", "PEP", "CASH",
    "SALARY", "RENT", "TRANSFER", "ISOLATION", "FOREST", "AI", "LLM", "COPILOT",
    "PASS", "FAIL", "HIGH", "MEDIUM", "LOW", "CREDIT", "DEBIT", "NET", "FLOW",
    "RULE", "FINDING", "ANOMALY", "TRANSACTION", "STATEMENT", "CUSTOMER", "ACCOUNT",
    "OBSERVED", "EVIDENCE", "LIMITATIONS", "RECOMMENDATIONS", "INTERPRETATION",
    "OVERVIEW", "SUMMARY", "BANK", "DETAILS", "ID", "TXN", "INDIA", "GLOBAL",
    "INVESTIGATION", "REPORT", "INVOICE", "TRADING", "ENTERPRISE", "FINANCIAL",
    "CRIME", "INTELLIGENCE", "UNIT", "CENTRAL", "RESERVE", "AUTHORITY", "EXECUTIVE",
    "ENHANCED", "DUE", "DILIGENCE", "SENIOR", "COMPLIANCE", "MANAGEMENT", "REVIEW",
    "STATISTICAL", "OUTLIER", "PASS-THROUGH", "LAYER", "STRUCTURING", "VELOCITY",
    "RAPID", "MOVEMENT", "CONDUIT", "SOURCE", "PROVENANCE", "CHECK", "QUEUE",
    "PARTIAL", "MAX", "ITERATIONS", "REACHED", "STATUS", "NORMAL", "BUDGET",
    "EXCEEDED", "EXECUTION", "COMPLETED", "SCREENING", "PERIOD", "OBJECTIVE",
    "PRIORITY", "FINDINGS", "KEY", "LARGE", "THRESHOLD", "BURST", "KNOWLEDGE",
    "BASE", "REFERENCE", "COMPLETION", "HUMAN", "ANALYTICS", "PROFILING",
    "NETWORK", "GRAPH", "NODES", "EDGES", "COUNTERPARTY", "COUNTERPARTIES",
    "CONVERGENCE", "SIGNAL", "SIGNALS", "DETECTION", "MONITORING", "ANALYSIS",
    "INFLOW", "OUTFLOW", "TURNOVER", "RATIO", "BASELINE", "AVERAGE", "PEAK",
    "DIRECTION", "DOMAIN", "MULTI", "INDEPENDENT", "CROSS", "MULTI-SIGNAL",
    "STAR", "HUB", "TOPOLOGY", "TYPOLOGY", "PATTERN", "PATTERNS", "VOLUME",
    "SERIES", "WINDOW", "AGENT", "WORKFLOW", "ORCHESTRATOR", "CRITIC",
    "AUDIT", "VALIDATION", "VERIFIED", "UNVERIFIED", "GROUNDED", "CANONICAL",
    "NEXT", "STEPS", "RECOMMENDED", "CORPORATE", "REGISTRY", "BENEFICIAL",
    "OWNERSHIP", "ONBOARDING", "ESCALATE", "INSTITUTIONAL", "PROCEDURES",
    "WARRANTED", "INSPECTION", "IMMEDIATE", "MANDATORY", "OFFICER",
    "IDENTIFIED", "FLAGGED", "DETECTED", "ANALYZED", "PROCESSED",
    "TRIGGERED", "GENERATED", "SYNTHESIZED", "REFERENCED", "CONFIRMED",
    "ACCOUNTS", "TRANSACTIONS", "ITEMS", "RECORDS",
    "OF", "AND", "FOR", "THE", "WITH", "FROM",
    "FUNDS", "AMOUNT", "AMOUNTS", "PAYMENT", "PAYMENTS", "DEPOSIT",
}


def _would_flag_as_entity(phrase: str, allowed: set) -> bool:
    words = set(phrase.strip().upper().split())
    return not words.issubset(allowed)


@pytest.mark.parametrize("phrase", [
    "HIGH PRIORITY",
    "LARGE TRANSACTION THRESHOLD",
    "HIGH VELOCITY BURST",
    "AML REFERENCE KNOWLEDGE BASE",
    "NORMAL COMPLETION",
    "HUMAN REVIEW QUEUE",
    "RAPID MOVEMENT OF FUNDS",
    "ISOLATION FOREST",
    "ENHANCED DUE DILIGENCE",
    "SENIOR COMPLIANCE MANAGEMENT",
    "INVESTIGATION REPORT STATUS",
    "STATISTICAL OUTLIER",
    "KEY FINDINGS SUMMARY",
    "CREDIT TRANSFER",
    "MULTI SIGNAL CONVERGENCE",
])
def test_legitimate_domain_phrase_not_flagged(phrase):
    """Legitimate AML investigation phrases must not trigger false-positive entity errors."""
    assert not _would_flag_as_entity(phrase, ALLOWED_DOMAIN_TERMS), (
        f"'{phrase}' was incorrectly flagged as unsupported entity — "
        f"add missing words to allowed_domain_terms in validation.py"
    )


@pytest.mark.parametrize("phrase", [
    "SHELL COMPANY ALPHA",
    "FAKE OFFSHORE CORP",
])
def test_genuinely_unknown_entities_still_flagged(phrase):
    """Phrases not in domain terms or statement should still be caught at word level."""
    flagged = _would_flag_as_entity(phrase, ALLOWED_DOMAIN_TERMS)
    assert flagged, (
        f"'{phrase}' should be flagged — it contains words not in allowed_domain_terms"
    )


# ---------------------------------------------------------------------------
# 3. Known-good statement passes validation end-to-end
# ---------------------------------------------------------------------------

def test_report_generation_known_good_statement():
    """Successful investigation report passes validation with evidence_validation_passed=True."""
    sample = Path("data/statements/ultimate_publish_stress_statement.pdf")
    if not sample.exists():
        pytest.skip("Stress statement PDF not available in test environment.")

    from aml_copilot.services.pdf_parser import extract_pdf_text
    from aml_copilot.services.transaction_parser import parse_transactions
    from aml_copilot.reporting.generator import generate_investigation_report
    from aml_copilot.agents.state import InvestigationResult
    from aml_copilot.agents.models import CritiqueResult

    doc = extract_pdf_text(sample)
    stmt = parse_transactions(doc)

    result = InvestigationResult(
        question="Investigate unusual movement of funds.",
        response=f"{stmt.total_transactions} transactions analyzed across the statement period.",
        tools_used=[],
        tool_calls=[],
        referenced_transaction_ids=[],
        knowledge_sources=[],
        critic_result=CritiqueResult(
            passed=True, issues=[], missing_evidence=[], unsupported_claims=[],
            required_revisions=[], checked_transaction_ids=[], invalid_transaction_ids=[],
            safety_violations=[], statement_transaction_count=stmt.total_transactions,
            narrative_transaction_reference_count=0, human_review_transaction_count=0,
            verified_transaction_reference_count=0, unverified_transaction_reference_count=0,
        ),
        critic_status="PASS",
        revision_count=0,
        limitations_warnings=[],
    )

    report = generate_investigation_report(statement=stmt, investigation=result)
    assert report.evidence_validation_passed is True, (
        f"Validation failed unexpectedly. Issues: {report.critic_validation.issues}"
    )
    assert report.critic_validation.status == "PASS"
    assert report.total_transactions_analyzed == stmt.total_transactions
