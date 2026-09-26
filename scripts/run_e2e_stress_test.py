"""Run end-to-end investigation stress test against the 54-transaction statement.

Captures all required criteria:
1. transaction count
2. rule findings
3. anomaly findings
4. profile findings
5. network findings
6. RAG findings
7. provider sequence
8. context-budget telemetry
9. critic result
10. revision count
11. report validation result
12. final investigation status
"""

import json
import sys
import time
from pathlib import Path

from aml_copilot.agents.investigation_agent import run_investigation
from aml_copilot.events.models import InvestigationEvent
from aml_copilot.logger import get_logger
from aml_copilot.rag.service import RAGService
from aml_copilot.reporting.formatter import format_report_markdown
from aml_copilot.reporting.generator import generate_investigation_report
from aml_copilot.reporting.validation import validate_report_evidence
from aml_copilot.services.pdf_parser import extract_pdf_text
from aml_copilot.services.transaction_parser import parse_transactions

logger = get_logger(__name__)

PDF_PATH = "data/statements/ultimate_publish_stress_statement.pdf"
QUESTION = "Investigate unusual movement of funds in this account and highlight transactions requiring human review."


def main():
    print("=" * 60)
    print("AML INVESTIGATION COPILOT — 54-TXN END-TO-END STRESS TEST")
    print("=" * 60)

    # 1. PDF Ingestion & Parsing
    pdf_path = Path(PDF_PATH)
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found at {PDF_PATH}")
        sys.exit(1)

    print(f"\n[1] Ingesting PDF: {PDF_PATH}")
    doc = extract_pdf_text(str(pdf_path))
    statement = parse_transactions(doc)
    txn_count = len(statement.transactions)
    print(f"    Customer: {statement.customer_name}")
    print(f"    Account:  {statement.account_number}")
    print(f"    Period:   {statement.statement_period}")
    print(f"    Transaction Count: {txn_count}")

    # Track lifecycle telemetry
    events_log = []
    providers_attempted = []
    context_reports = []

    def event_callback(evt: InvestigationEvent):
        events_log.append(evt)
        if evt.event_type in ["LLM_PROVIDER_ATTEMPT", "LLM_FAILOVER_DISPATCH"]:
            p = evt.metadata.get("provider") or evt.metadata.get("providers")
            if p and p not in providers_attempted:
                providers_attempted.append(str(p))
        if evt.event_type == "NODE_STARTED" and "context_estimated_tokens" in evt.metadata:
            context_reports.append(evt.metadata)
        print(f"  [{evt.event_type}] {evt.message[:95]}")

    # 2. Run Investigation Agent
    print(f"\n[2] Executing Agent Investigation...")
    rag_service = RAGService(knowledge_dir="data/knowledge")

    start_t = time.time()
    investigation = run_investigation(
        statement=statement,
        question=QUESTION,
        rag_service=rag_service,
        include_rag=True,
        include_profile=True,
        include_network=True,
        enable_critic=True,
        max_revisions=2,
        event_callback=event_callback,
        investigation_id="INV-STRESS-54",
    )
    elapsed = round(time.time() - start_t, 2)
    print(f"\n    Investigation completed in {elapsed}s")

    # 3. Generate Evidence-Grounded Report
    print(f"\n[3] Generating and Validating Report...")
    canonical_ev = investigation.canonical_evidence
    report = generate_investigation_report(
        statement=statement,
        investigation=investigation,
        canonical_evidence=canonical_ev,
    )

    # 4. Strict Evidence Provenance Validation
    validation_res = validate_report_evidence(report, canonical_ev, statement)

    # Output Markdown and JSON Reports to File
    md_content = format_report_markdown(report)
    out_path = Path("stress_test_final_report.md")
    out_path.write_text(md_content)
    print(f"    Final Markdown Report written to: {out_path.resolve()}")

    json_path = Path("stress_test_final_report.json")
    json_path.write_text(report.model_dump_json(indent=2))
    print(f"    Final JSON Report written to:     {json_path.resolve()}")

    # 5. Summary Telemetry
    print("\n" + "=" * 60)
    print("FINAL INVESTIGATION STRESS TEST SUMMARY")
    print("=" * 60)
    print(f"1. Transaction Count:        {txn_count}")
    print(f"2. Rule Findings:           {len(report.detection_findings)} triggered rules")
    print(f"3. Anomaly Findings:        {len(report.anomaly_findings)} anomalies: {[af.transaction_id for af in report.anomaly_findings]}")
    print(f"4. Profile Findings:        Turnover ₹{report.customer_profile.total_credits:,.2f} Cr / ₹{report.customer_profile.total_debits:,.2f} Dr ({report.customer_profile.active_days} active days)")
    print(f"5. Network Findings:        {len(report.network_findings)} patterns")
    print(f"6. RAG Findings:            {len(report.aml_reference_context)} reference source(s)")
    print(f"7. Provider Sequence:       {' -> '.join(providers_attempted) or 'Default configured provider'}")
    print(f"8. Context-Budget:          {len(context_reports)} LLM calls budgeted (Max tokens: {max(c.get('context_estimated_tokens', 0) for c in context_reports) if context_reports else 'N/A'})")
    print(f"9. Critic Result:           Status={report.critic_validation.status}, Passed={report.critic_validation.passed}, Issues={len(report.critic_validation.issues)}")
    print(f"9b. Human Review Items:     {len(report.human_review_items)} prioritized (Top: {[item.transaction_id for item in report.human_review_items[:5]]})")
    print(f"10. Revision Count:         {report.revision_history.revision_count}")
    print(f"11. Report Provenance:      Passed={validation_res.passed} (Errors: {len(validation_res.errors)}, Failures: {len(validation_res.provenance_failures)})")
    print(f"12. Final Status:           {'NORMAL_COMPLETION' if validation_res.passed and report.critic_validation.passed and investigation.status in ('COMPLETED', 'NORMAL_COMPLETION') else investigation.status}")
    print("=" * 60)

    # Check Acceptance Criteria
    assert txn_count == 54, "Transaction count must be 54"
    assert [af.transaction_id for af in report.anomaly_findings] == [
        "TXN401", "TXN404", "TXN434", "TXN442", "TXN445", "TXN451"
    ], "Anomaly IDs do not match exact Isolation Forest output!"
    assert len(report.human_review_items) < 54, "Human review items must be a prioritized subset (< 54)"
    assert [item.transaction_id for item in report.human_review_items[:2]] == ["TXN445", "TXN434"], "Top converged items must be TXN445 and TXN434"
    assert validation_res.passed, f"Report evidence provenance validation failed: {validation_res.errors}"
    assert report.critic_validation.passed, f"Critic validation failed: {report.critic_validation.issues}"
    print("\nALL STRESS TEST ACCEPTANCE CRITERIA SATISFIED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
