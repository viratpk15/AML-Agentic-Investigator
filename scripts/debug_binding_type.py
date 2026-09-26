#!/usr/bin/env python3
"""Check what _ChatModelBinding._generate does and how to call it properly."""
import sys
sys.path.insert(0, "src")

from langchain_groq import ChatGroq
from langchain_core.tools import tool

@tool
def dummy(query: str) -> str:
    """Dummy."""
    return query

# Check what bind_tools returns
import os
key = os.environ.get("GROQ_API_KEY", "")
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.0, api_key=key)
bound = llm.bind_tools([dummy])

print("Type of bound:", type(bound).__name__)
print("MRO:", [c.__name__ for c in type(bound).__mro__])
print("Has _generate:", hasattr(bound, "_generate"))
print("Has invoke:", hasattr(bound, "invoke"))

# Does _generate exist?
if hasattr(bound, "_generate"):
    import inspect
    print("_generate defined in:", type(bound).__name__)
    try:
        src_class = [c for c in type(bound).__mro__ if "_generate" in c.__dict__]
        print("_generate owner:", [c.__name__ for c in src_class])
    except Exception:
        pass

# What does invoke call internally?
from langchain_core.messages import HumanMessage
msgs = [HumanMessage(content="Hello")]

# Try calling _generate directly on the bound model
try:
    result = bound._generate(msgs)
    print("_generate result:", result.generations[0].message.content[:100])
except Exception as exc:
    print(f"_generate FAILED: {type(exc).__name__}: {str(exc)[:300]}")

# Try invoke
try:
    result2 = bound.invoke(msgs)
    print("invoke result:", result2.content[:100])
except Exception as exc2:
    print(f"invoke FAILED: {type(exc2).__name__}: {str(exc2)[:300]}")
