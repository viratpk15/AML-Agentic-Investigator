"""Pydantic schemas for bank transactions and statements."""

import datetime as dt
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class Transaction(BaseModel):
    """Structured and validated bank transaction record."""

    date: dt.date = Field(..., description="Transaction date")

    transaction_id: Optional[str] = Field(
        default=None, description="Unique transaction identifier if present"
    )
    description: str = Field(..., min_length=1, description="Raw transaction description")
    debit: Optional[float] = Field(
        default=None, ge=0.0, description="Debit amount (money leaving account)"
    )
    credit: Optional[float] = Field(
        default=None, ge=0.0, description="Credit amount (money entering account)"
    )
    balance: float = Field(..., description="Account balance after transaction")
    counterparty: Optional[str] = Field(
        default=None, description="Extracted counterparty name if identifiable"
    )

    @model_validator(mode="after")
    def validate_amounts(self) -> "Transaction":
        """Validate transaction debit/credit invariants."""
        has_debit = self.debit is not None and self.debit > 0
        has_credit = self.credit is not None and self.credit > 0

        if has_debit and has_credit:
            raise ValueError(
                f"Transaction cannot have both positive debit ({self.debit}) and positive credit ({self.credit})."
            )

        if not has_debit and not has_credit:
            # Check if neither was provided or both are 0 / None
            if self.debit is None and self.credit is None:
                raise ValueError("Transaction must have either a debit or credit amount.")

        return self


class TransactionStatement(BaseModel):
    """Collection model for a validated statement containing transactions and account metadata."""

    account_number: Optional[str] = Field(
        default=None, description="Bank account identifier"
    )
    customer_name: Optional[str] = Field(
        default=None, description="Customer or account holder name"
    )
    statement_period: Optional[str] = Field(
        default=None, description="Statement period range string"
    )
    transactions: List[Transaction] = Field(
        default_factory=list, description="List of validated transactions"
    )

    @property
    def total_transactions(self) -> int:
        """Return the count of transactions in the statement."""
        return len(self.transactions)
