#!/usr/bin/env python3
"""Diagnostic: send an oversized payload to trigger the 413/429 and see the raw exception."""
import sys
sys.path.insert(0, "src")

from aml_copilot.config import get_settings
from langchain_core.messages import HumanMessage, SystemMessage

s = get_settings()

# Build a payload large enough to exceed Groq's 8000 TPM limit
big_content = "Analyse this transaction data: " + ("suspicious UPI transfer " * 600)

from langchain_groq import ChatGroq
llm = ChatGroq(
    model=s.groq_model,
    temperature=0.0,
    api_key=s.groq_api_key,
)

try:
    result = llm.invoke([HumanMessage(content=big_content)])
    print("UNEXPECTEDLY succeeded:", result.content[:100])
except Exception as exc:
    print(f"Exception TYPE: {type(exc).__name__}")
    print(f"Exception MRO: {[c.__name__ for c in type(exc).__mro__]}")
    msg = str(exc)
    print(f"Exception str (first 800): {msg[:800]}")
    print()
    print(f"  status_code: {getattr(exc, 'status_code', '---')}")
    print(f"  status:      {getattr(exc, 'status', '---')}")
    print(f"  code:        {getattr(exc, 'code', '---')}")
    print(f"  error_code:  {getattr(exc, 'error_code', '---')}")
    resp = getattr(exc, 'response', None)
    if resp is not None:
        print(f"  response type: {type(resp).__name__}")
        print(f"  response.status_code: {getattr(resp, 'status_code', '---')}")
    body = getattr(exc, 'body', None)
    if body:
        print(f"  body: {str(body)[:300]}")

    # What does our classifier make of it?
    from aml_copilot.llm.classifier import classify_provider_error
    classified = classify_provider_error(exc, "groq")
    print()
    print(f"Classifier output: {type(classified).__name__}")
    print(f"  reason:       {getattr(classified, 'reason', 'N/A')}")
    print(f"  status_code:  {classified.status_code}")
    print(f"  message:      {str(classified)[:300]}")
