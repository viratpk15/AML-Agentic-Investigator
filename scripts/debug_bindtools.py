#!/usr/bin/env python3
"""Diagnostic: simulate exactly what graph.py does — bind tools, then _generate."""
import sys
sys.path.insert(0, "src")

from aml_copilot.config import get_settings
from aml_copilot.llm.classifier import classify_provider_error
from aml_copilot.llm.factory import LLMFactory
from aml_copilot.llm.failover import FailoverLLM
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

s = get_settings()

# Build FailoverLLM
factory = LLMFactory(settings=s)
flm = FailoverLLM.from_factory(factory=factory)
print("Providers before bind:", flm.provider_names)

# Simulate tool binding like graph.py does
@tool
def dummy_tool(query: str) -> str:
    """A dummy tool."""
    return f"result for {query}"

bound = flm.bind_tools([dummy_tool])
print("Providers after bind:", bound.provider_names)
print("bound type:", type(bound).__name__)
print("Provider[0][1] type:", type(bound.providers[0][1]).__name__)

# Now try _generate on the bound instance
msgs = [SystemMessage(content="You are an AML investigator."), HumanMessage(content="Summarize the investigation. No tool calls needed.")]
try:
    result = bound._generate(msgs)
    print("SUCCESS:", result.generations[0].message.content[:200])
except Exception as exc:
    print("\nFAILED:")
    print(f"  TYPE: {type(exc).__name__}")
    print(f"  MRO: {[c.__name__ for c in type(exc).__mro__]}")
    print(f"  str: {str(exc)[:600]}")
    print(f"  status_code: {getattr(exc, 'status_code', '---')}")
    resp = getattr(exc, 'response', None)
    if resp:
        print(f"  response.status_code: {getattr(resp, 'status_code', '---')}")
    classified = classify_provider_error(exc, "groq")
    print(f"\nClassifier: {type(classified).__name__} reason={getattr(classified, 'reason', 'N/A')}")

# Also check: what does invoke() do?
print("\n--- Testing .invoke() directly on bound FailoverLLM ---")
try:
    result2 = bound.invoke(msgs)
    print("invoke() SUCCESS:", result2.content[:200])
except Exception as exc2:
    print(f"invoke() FAILED: {type(exc2).__name__}: {str(exc2)[:400]}")
    print(f"  status_code: {getattr(exc2, 'status_code', '---')}")
    resp2 = getattr(exc2, 'response', None)
    if resp2:
        print(f"  response.status_code: {getattr(resp2, 'status_code', '---')}")
