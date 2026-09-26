"""Lightweight investigation history management service.

Persists completed investigation records and allows retrieval of past reports.
Stores metadata and reports without sensitive credentials.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from aml_copilot.logger import get_logger
from aml_copilot.reporting.models import InvestigationReport

logger = get_logger(__name__)

HISTORY_DIR = Path("data/history")


class InvestigationHistoryRecord(BaseModel):
    """Metadata summary of a past investigation run."""

    investigation_id: str
    report_id: str
    timestamp: str
    customer_name: str
    account_number: str
    statement_period: str
    transaction_count: int
    status: str
    review_count: int
    high_priority_count: int
    runtime_seconds: float = 0.0
    report_path: Optional[str] = None


class InvestigationHistoryService:
    """Service for saving and retrieving investigation records."""

    def __init__(self, base_dir: Path = HISTORY_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / "history_index.json"
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self.index_path.exists():
            try:
                self.index_path.write_text("[]", encoding="utf-8")
            except Exception as exc:
                logger.warning(f"Could not initialize history index: {exc}")

    def list_history(self) -> List[InvestigationHistoryRecord]:
        """Return all past investigation records sorted newest first."""
        if not self.index_path.exists():
            return []
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            records = [InvestigationHistoryRecord(**item) for item in data]
            records.sort(key=lambda r: r.timestamp, reverse=True)
            return records
        except Exception as exc:
            logger.error(f"Failed to read history index: {exc}")
            return []

    def save_run(
        self,
        investigation_id: str,
        report: InvestigationReport,
        markdown_text: str,
        status: str = "COMPLETED",
        runtime_seconds: float = 0.0,
    ) -> InvestigationHistoryRecord:
        """Save an investigation run to history."""
        high_count = 0
        review_count = len(report.human_review_items)
        for item in report.human_review_items:
            prio = getattr(item, "priority", item.get("priority") if isinstance(item, dict) else "")
            if prio == "HIGH":
                high_count += 1

        report_file = self.base_dir / f"{report.report_id}.json"
        md_file = self.base_dir / f"{report.report_id}.md"

        try:
            report_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            md_file.write_text(markdown_text, encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Failed to write history report files for {report.report_id}: {exc}")

        record = InvestigationHistoryRecord(
            investigation_id=investigation_id,
            report_id=report.report_id,
            timestamp=report.generated_at,
            customer_name=report.customer_name,
            account_number=report.account_number,
            statement_period=report.statement_period,
            transaction_count=report.total_transactions_analyzed or len(report.observed_evidence),
            status=status,
            review_count=review_count,
            high_priority_count=high_count,
            runtime_seconds=round(runtime_seconds, 2),
            report_path=str(report_file),
        )

        try:
            records = self.list_history()
            # Update or append
            updated = [r for r in records if r.investigation_id != investigation_id and r.report_id != report.report_id]
            updated.insert(0, record)
            self.index_path.write_text(
                json.dumps([r.model_dump() for r in updated], indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.error(f"Failed to update history index: {exc}")

        return record

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full report json and markdown by report_id."""
        report_file = self.base_dir / f"{report_id}.json"
        md_file = self.base_dir / f"{report_id}.md"

        if not report_file.exists():
            return None

        try:
            report_data = json.loads(report_file.read_text(encoding="utf-8"))
            markdown = md_file.read_text(encoding="utf-8") if md_file.exists() else ""
            return {"report": report_data, "markdown": markdown}
        except Exception as exc:
            logger.error(f"Failed to load history report {report_id}: {exc}")
            return None


_history_service_instance: Optional[InvestigationHistoryService] = None


def get_history_service() -> InvestigationHistoryService:
    """Singleton getter for history service."""
    global _history_service_instance
    if _history_service_instance is None:
        _history_service_instance = InvestigationHistoryService()
    return _history_service_instance
