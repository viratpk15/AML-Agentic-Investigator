#!/usr/bin/env python3
"""Diagnostic: capture the real exception type from Groq on a large request."""
import sys
sys.path.insert(0, "src")

from aml_copilot.config import get_settings

s = get_settings()
print(f"LLM_PROVIDER: {s.llm_provider}")
print(f"LLM_FALLBACK_PROVIDERS: {s.llm_fallback_providers!r}")
print(f"GROQ_API_KEY present: {bool(s.groq_api_key)}")
print(f"GEMINI_API_KEY present: {bool(s.gemini_api_key)}")
print(f"GROQ_MODEL: {s.groq_model}")
print(f"GEMINI_MODEL: {s.gemini_model}")
print()

# Try building the FailoverLLM
from aml_copilot.llm.factory import LLMFactory
from aml_copilot.llm.failover import FailoverLLM

factory = LLMFactory(settings=s)
print("Primary config:", factory.primary_config())
print("Fallback configs:", factory.fallback_configs())
print()

flm = FailoverLLM.from_factory(factory=factory)
print("FailoverLLM provider_names:", flm.provider_names)
print()

# Fire a minimal call to Groq and capture the raw exception
from langchain_core.messages import HumanMessage

try:
    from langchain_groq import ChatGroq
    llm = ChatGroq(
        model=s.groq_model,
        temperature=0.0,
        api_key=s.groq_api_key,
    )
    # Tiny call
    result = llm.invoke([HumanMessage(content="Hi")])
    print("Groq call succeeded:", result.content[:100])
except Exception as exc:
    print(f"Groq exception TYPE: {type(exc).__name__}")
    print(f"Groq exception MRO: {[c.__name__ for c in type(exc).__mro__]}")
    print(f"Groq exception str: {str(exc)[:500]}")
    print(f"Groq status_code attr: {getattr(exc, 'status_code', 'NOT FOUND')}")
    print(f"Groq status attr: {getattr(exc, 'status', 'NOT FOUND')}")
    print(f"Groq response attr: {getattr(exc, 'response', 'NOT FOUND')}")
    resp = getattr(exc, 'response', None)
    if resp:
        print(f"  response.status_code: {getattr(resp, 'status_code', 'NOT FOUND')}")
    print(f"Groq body attr: {getattr(exc, 'body', 'NOT FOUND')}")
    print()
    # Run through classifier
    from aml_copilot.llm.classifier import classify_provider_error
    classified = classify_provider_error(exc, "groq")
    print(f"Classified as: {type(classified).__name__} reason={getattr(classified, 'reason', 'N/A')}")
