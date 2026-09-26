"""Customer profiling package."""

from aml_copilot.profiling.customer_profile import (
    BehavioralIndicator,
    CustomerProfile,
    LargestTransactionRecord,
)
from aml_copilot.profiling.profiler import build_customer_profile

__all__ = [
    "BehavioralIndicator",
    "CustomerProfile",
    "LargestTransactionRecord",
    "build_customer_profile",
]
