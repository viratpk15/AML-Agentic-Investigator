"""Reporting subpackage for structured AML Investigation Reports."""

from .formatter import (
    format_report_json,
    format_report_markdown,
)
from .generator import generate_investigation_report
from .models import (
    AnomalyFindingItem,
    CriticSummary,
    CustomerProfileSummary,
    DetectionFindingItem,
    EvidenceItem,
    InvestigationReport,
    KnowledgeReferenceItem,
    NetworkFindingItem,
    RevisionSummary,
)

__all__ = [
    "EvidenceItem",
    "DetectionFindingItem",
    "AnomalyFindingItem",
    "CustomerProfileSummary",
    "NetworkFindingItem",
    "KnowledgeReferenceItem",
    "CriticSummary",
    "RevisionSummary",
    "InvestigationReport",
    "generate_investigation_report",
    "format_report_markdown",
    "format_report_json",
]
