import json
import re
from typing import Any, Dict, List
from aml_copilot.reporting.models import InvestigationReport


def _clean_narrative_text(text: str) -> str:
    """Remove duplicate report titles or nested report markdown headers from narrative text."""
    if not text:
        return ""
    # Remove nested title if present
    cleaned = re.sub(r"(?im)^#\s+AML\s+Investigation\s+Report\s*$", "", text)
    # Remove nested section headers if LLM attempted to write its own report
    cleaned = re.sub(
        r"(?im)^##\s+\d*\.?\s*(?:Investigation\s+Overview|Executive\s+Summary|Observed\s+Transaction\s+Evidence|Transaction\s+Summary|Detection\s+Findings|Rule\s+Findings|Statistical\s+Anomalies|Customer\s+Profile|Network\s+Analysis|AML\s+Knowledge\s+Context|AML\s+Reference\s+Context|Evidence\s+Convergence|Human\s+Review\s+Queue|Interpretation|Limitations|Recommended\s+Next\s+Steps|Recommendations|Critic\s+Validation|Human\s+Review)\s*$",
        "",
        cleaned,
    )
    # Strip excessive blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def format_report_markdown(report: InvestigationReport) -> str:
    """Format an InvestigationReport into a professional, human-readable Markdown document.

    Follows the 14-section compliance audit standard:
    1. Investigation Overview
    2. Executive Summary (5-8 concise bullets)
    3. Observed Transaction Evidence
    4. Detection Findings (Grouped Rules + Exact Statistical Anomalies)
    5. Customer Profile
    6. Network Analysis (Distinguishing Counterparties from Graph Nodes)
    7. AML Knowledge Context (AML Reference Knowledge Base)
    8. Evidence Convergence (Top Converged Review Items)
    9. Human Review Queue (Summary & Priority Breakdown)
    10. Interpretation
    11. Limitations
    12. Recommended Next Steps
    13. Critic Validation
    14. Human Review (Detailed Structured Queue)
    """
    lines: List[str] = []

    # Title
    lines.append("# AML Investigation Report")
    lines.append("")

    # 1. Investigation Overview
    lines.append("## 1. Investigation Overview")
    lines.append("")
    lines.append(f"- **Report ID**: `{report.report_id}`")
    lines.append(f"- **Generated Time**: `{report.generated_at}`")
    lines.append(f"- **Customer / Account**: {report.customer_name} (Account: `{report.account_number}`)")
    lines.append(f"- **Analysis Period**: {report.statement_period}")
    lines.append(f"- **Investigation Question**: {report.investigation_question}")
    lines.append(f"- **Total Transactions Analyzed**: {report.total_transactions_analyzed or len(report.observed_evidence)}")
    lines.append("")

    # 2. Executive Summary
    lines.append("## 2. Executive Summary")
    lines.append("")
    if report.executive_summary_bullets:
        for b in report.executive_summary_bullets:
            lines.append(f"- {_clean_narrative_text(b)}")
    else:
        lines.append(_clean_narrative_text(report.executive_summary))
    lines.append("")

    # 3. Observed Transaction Evidence
    lines.append("## 3. Observed Transaction Evidence")
    lines.append("")
    if report.observed_evidence:
        lines.append("| Transaction ID | Date | Flow | Amount (INR) | Counterparty | Verification |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for ev in report.observed_evidence:
            amt_str = f"₹{ev.amount:,.2f}" if ev.amount is not None else "N/A"
            flow_str = ev.flow_type.upper() if ev.flow_type else "N/A"
            date_str = ev.date or "N/A"
            cp_str = ev.counterparty or "Unspecified"
            ver_str = "✓ Verified in Statement" if ev.verified_in_statement else "✗ Unverified"
            lines.append(f"| `{ev.transaction_id}` | {date_str} | {flow_str} | {amt_str} | {cp_str} | {ver_str} |")
    else:
        lines.append("*No specific transaction IDs were directly cited in the statement.*")
    lines.append("")

    # High-Value Transactions under configured monitoring threshold
    if report.report_dto and report.report_dto.transactions.high_value_transactions:
        high_val = report.report_dto.transactions.high_value_transactions
        lines.append("### High-Value Transactions (Configured Monitoring Threshold)")
        lines.append("")
        lines.append("Transactions meeting or exceeding the configured monitoring threshold (₹200,000.00):")
        lines.append("")
        lines.append("| Transaction ID | Date | Flow | Amount (INR) | Counterparty |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for ht in high_val:
            lines.append(f"| `{ht.transaction_id}` | {ht.date or 'N/A'} | {ht.direction.upper()} | ₹{ht.amount:,.2f} | {ht.counterparty or 'Unspecified'} |")
        lines.append("")

    # 4. Detection Findings
    lines.append("## 4. Detection Findings")
    lines.append("")
    lines.append("### Rule-Based Signals")
    lines.append("")
    if report.rule_summary_groups:
        for rsg in report.rule_summary_groups:
            sev_str = ", ".join(f"{k}: {v}" for k, v in rsg.severity_distribution.items())
            txns_preview = ", ".join(f"`{t}`" for t in rsg.supporting_transaction_ids[:10])
            if len(rsg.supporting_transaction_ids) > 10:
                txns_preview += f" ... (+{len(rsg.supporting_transaction_ids) - 10} more)"
            lines.append(f"- **{rsg.rule_name}** (`{rsg.rule_id}`)")
            lines.append(f"  - **Total Triggered**: {rsg.count} instance(s) ({sev_str})")
            if rsg.observation_summary:
                lines.append(f"  - **Condition Summary**: {rsg.observation_summary}")
            if rsg.representative_examples:
                lines.append(f"  - **Representative Examples**: {', '.join(rsg.representative_examples)}")
            lines.append(f"  - **Supporting Transactions**: {txns_preview}")
        lines.append("")
    elif report.detection_findings:
        for df in report.detection_findings:
            txns_str = ", ".join(f"`{t}`" for t in df.supporting_transaction_ids) if df.supporting_transaction_ids else "None"
            lines.append(f"- **{df.rule_name}** (`{df.rule_id}`, Severity: **{df.severity}**)")
            lines.append(f"  - *Observation*: {df.explanation}")
            lines.append(f"  - *Supporting Transactions*: {txns_str}")
        lines.append("")
    else:
        lines.append("*No deterministic AML rule signals were triggered.*")
        lines.append("")

    lines.append("### Statistical Anomalies (Isolation Forest)")
    lines.append("")
    if report.anomaly_findings:
        anom_ids_str = ", ".join(f"`{af.transaction_id}`" for af in report.anomaly_findings)
        lines.append(f"Isolation Forest unsupervised anomaly detection flagged **{len(report.anomaly_findings)}** statistical outliers: {anom_ids_str}.")
        lines.append("")
        lines.append("| Transaction ID | Anomaly Score | Status | Key Feature Context | Provenance |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for af in report.anomaly_findings:
            ctx_str = ", ".join(f"{k}={v:.1f}" for k, v in list(af.feature_context.items())[:3])
            lines.append(f"| `{af.transaction_id}` | {af.anomaly_score:.4f} | Statistical Outlier | {ctx_str} | Verified Model Output |")
        lines.append("")
    else:
        lines.append("*No statistical anomalies were identified by Isolation Forest.*")
        lines.append("")

    # 5. Customer Profile
    lines.append("## 5. Customer Profile")
    lines.append("")
    if report.customer_profile:
        p = report.customer_profile
        lines.append(f"- **Transaction Count**: {p.total_transactions} ({p.active_days} active days)")
        lines.append(f"- **Turnover**: Credits: ₹{p.total_credits:,.2f} | Debits: ₹{p.total_debits:,.2f} | Net Flow: ₹{p.net_cash_flow:,.2f}")
        lines.append(f"- **Average Transaction**: ₹{p.average_transaction_amount:,.2f}")
        if p.credit_to_debit_ratio is not None:
            lines.append(f"- **Credit-to-Debit Ratio**: {p.credit_to_debit_ratio:.2f}")
        lines.append(f"- **Unique Counterparties**: {p.unique_counterparties}")
        if p.largest_credit_amount:
            lines.append(f"- **Peak Credit**: ₹{p.largest_credit_amount:,.2f}")
        if p.largest_debit_amount:
            lines.append(f"- **Peak Debit**: ₹{p.largest_debit_amount:,.2f}")
        if p.indicators:
            lines.append("- **Behavioral Indicators**:")
            for ind in p.indicators:
                lines.append(f"  - {ind}")
    else:
        lines.append("*Customer profile data not generated for this statement.*")
    lines.append("")

    # 6. Network Analysis
    lines.append("## 6. Network Analysis")
    lines.append("")
    if report.network_summary:
        ns = report.network_summary
        lines.append(f"- **Unique Counterparties**: {ns.unique_counterparties}")
        lines.append(f"- **Total Graph Nodes**: {ns.graph_nodes} (1 customer account + {ns.unique_counterparties} unique counterparties)")
        lines.append(f"- **Total Graph Edges**: {ns.graph_edges}")
        if ns.dominant_counterparties:
            lines.append(f"- **Dominant Counterparties**: {', '.join(ns.dominant_counterparties)}")
        lines.append("")

    if report.network_findings:
        lines.append("### Relational Topology Findings")
        for nf in report.network_findings:
            nodes_str = ", ".join(nf.involved_nodes) if nf.involved_nodes else "N/A"
            txns_str = ", ".join(f"`{t}`" for t in nf.supporting_transaction_ids[:6])
            if len(nf.supporting_transaction_ids) > 6:
                txns_str += f" ... (+{len(nf.supporting_transaction_ids) - 6} more)"
            lines.append(f"- **{nf.pattern_name.replace('_', ' ').title()}**")
            lines.append(f"  - *Structure*: {nf.description}")
            lines.append(f"  - *Involved Entities*: {nodes_str}")
            lines.append(f"  - *Transactions*: {txns_str}")
    else:
        lines.append("*No complex counterparty relationship patterns detected.*")
    lines.append("")

    # 7. AML Knowledge Context
    lines.append("## 7. AML Knowledge Context")
    lines.append("")
    if report.aml_reference_context:
        lines.append("References retrieved from the project's verified AML reference knowledge base:")
        lines.append("")
        for kr in report.aml_reference_context:
            lines.append(f"- **{kr.title or kr.source}** (`{kr.source}`)")
            if kr.snippet:
                lines.append(f"  - *Retrieved Guidance*: {kr.snippet}")
            lines.append("  - *Application*: Serves as investigative reference for observed velocity, structuring, or pass-through typologies without implying guilt.")
    else:
        lines.append("*No AML reference guidance items were retrieved during this investigation.*")
    lines.append("")

    # 8. Evidence Convergence
    lines.append("## 8. Evidence Convergence")
    lines.append("")
    lines.append("Prioritized transactions demonstrating simultaneous convergence across multiple independent detection domains:")
    lines.append("")
    if report.evidence_convergence:
        lines.append("| Priority | Transaction ID | Date | Flow | Amount (INR) | Counterparty | Independent Signal Domains | Supporting Reasons |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for ec in report.evidence_convergence:
            prio_badge = f"**{ec.priority}**" if ec.priority == "HIGH" else ec.priority
            dt_str = ec.date or "N/A"
            dir_str = (ec.direction or "N/A").upper()
            amt_str = f"₹{ec.amount:,.2f}" if ec.amount is not None else "N/A"
            cp_str = ec.counterparty or "Unspecified"
            doms_str = ", ".join(ec.signal_domains) if ec.signal_domains else "General"
            reasons_str = ", ".join(f"`{r}`" for r in ec.reasons[:4])
            if len(ec.reasons) > 4:
                reasons_str += f" (+{len(ec.reasons) - 4} more)"
            lines.append(f"| {prio_badge} | `{ec.transaction_id}` | {dt_str} | {dir_str} | {amt_str} | {cp_str} | {doms_str} | {reasons_str} |")
    else:
        lines.append("*No multi-signal evidence convergence items identified.*")
    lines.append("")

    # 9. Human Review Queue Summary
    lines.append("## 9. Human Review Queue")
    lines.append("")
    if report.human_review_summary:
        hrs = report.human_review_summary
        lines.append(f"- **Total Transactions Analyzed**: {hrs.get('total_analyzed', len(report.observed_evidence))}")
        lines.append(f"- **Prioritized Review Items**: {hrs.get('prioritized_review_count', len(report.human_review_items))}")
        lines.append(f"- **HIGH Priority Items**: {hrs.get('high_priority_count', 0)}")
        lines.append(f"- **MEDIUM Priority Items**: {hrs.get('medium_priority_count', 0)}")
        lines.append(f"- **LOW Priority Items**: {hrs.get('low_priority_count', 0)}")
    else:
        lines.append(f"- **Prioritized Review Items**: {len(report.human_review_items)}")
    lines.append("")
    lines.append("Queue items are ranked deterministically by priority tier, independent domain count, trigger reason count, and transaction amount.")
    lines.append("")

    # 10. Interpretation
    lines.append("## 10. Interpretation")
    lines.append("")
    lines.append(_clean_narrative_text(report.interpretation or report.executive_summary))
    lines.append("")

    # 11. Limitations
    lines.append("## 11. Limitations")
    lines.append("")
    for lim in report.limitations:
        lines.append(f"- {lim}")
    lines.append("")

    # 12. Recommended Next Steps
    lines.append("## 12. Recommended Next Steps")
    lines.append("")
    if report.next_steps:
        for ns in report.next_steps:
            lines.append(f"- {ns}")
    else:
        lines.append("- Review KYC/CDD documentation and declared business profile.")
        lines.append("- Examine transaction purpose and source documentation for peak transfers.")
        lines.append("- Compare observed flow velocities against expected customer activity.")
        lines.append("- Escalate findings to compliance management in accordance with institutional procedures.")
    lines.append("")

    # 13. Critic Validation
    lines.append("## 13. Critic Validation")
    lines.append("")
    cv = report.critic_validation
    status_badge = "**PASSED** ✓" if cv.passed else "**FAILED** ✗"
    lines.append(f"- **Audit Outcome**: {status_badge}")
    lines.append(f"- **Evidence References Checked**: {cv.narrative_transaction_reference_count} confirmed")
    lines.append(f"- **Statement Transactions Analyzed**: {cv.statement_transaction_count}")
    lines.append(f"- **Verified References**: {cv.verified_transaction_reference_count}")
    lines.append(f"- **Unverified References**: {cv.unverified_transaction_reference_count}")
    lines.append(f"- **Human Review Queue Items**: {cv.human_review_transaction_count}")
    if cv.invalid_transaction_ids:
        lines.append(f"- **Invalid Identifiers Flagged**: {', '.join(cv.invalid_transaction_ids)}")
    if cv.issues:
        lines.append("- **Audit Issues Identified**:")
        for iss in cv.issues:
            lines.append(f"  - {iss}")
    if cv.safety_violations:
        lines.append("- **Safety Boundary Flags**:")
        for sv in cv.safety_violations:
            lines.append(f"  - {sv}")
    if cv.passed and not cv.issues:
        if cv.verified_transaction_reference_count > 0:
            lines.append(
                f"- **Factual Grounding**: All {cv.verified_transaction_reference_count} referenced transactions, "
                "dates, amounts, and flow directions match verified statement records. No unverified legal accusations detected."
            )
        else:
            lines.append(
                "- **Factual Grounding**: No narrative transaction references required verification; "
                "statement records and safety guardrails audited with zero discrepancies."
            )
    lines.append("")

    rh = report.revision_history
    lines.append(f"- **Revision Cycles**: {rh.revision_count} of maximum {rh.max_revisions}")
    if rh.revisions_applied:
        lines.append("- **Self-Correction**: Revision cycle incorporated Critic audit feedback.")
    if rh.unresolved_limitations:
        lines.append("> ⚠️ **Warning**: Investigation completed with unresolved validation limitations. Human review is required.")
    lines.append("")

    # 14. Human Review (Detailed Structured Queue)
    lines.append("## 14. Human Review")
    lines.append("")
    if report.human_review_items:
        lines.append("### Prioritized Transaction Queue")
        lines.append("| Priority | Transaction ID | Date | Flow | Amount (INR) | Counterparty | Triggered Reasons |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for hr in report.human_review_items:
            tid = getattr(hr, "transaction_id", hr.get("transaction_id") if isinstance(hr, dict) else "")
            prio = getattr(hr, "priority", hr.get("priority", "MEDIUM") if isinstance(hr, dict) else "MEDIUM")
            dt_val = getattr(hr, "date", hr.get("date") if isinstance(hr, dict) else None) or "N/A"
            flow = getattr(hr, "direction", hr.get("direction") if isinstance(hr, dict) else None) or "N/A"
            amt = getattr(hr, "amount", hr.get("amount") if isinstance(hr, dict) else None)
            amt_str = f"₹{amt:,.2f}" if amt is not None else "N/A"
            cp = getattr(hr, "counterparty", hr.get("counterparty") if isinstance(hr, dict) else None) or "Unspecified"
            reasons = getattr(hr, "reasons", hr.get("reasons", []) if isinstance(hr, dict) else [])
            reasons_str = ", ".join(f"`{r}`" for r in reasons) if reasons else "None"
            prio_badge = f"**{prio}**" if prio == "HIGH" else prio
            lines.append(f"| {prio_badge} | `{tid}` | {dt_val} | {flow.upper()} | {amt_str} | {cp} | {reasons_str} |")
        lines.append("")

    lines.append(report.human_review_recommendation)
    lines.append("")

    return "\n".join(lines)


def format_report_json(report: InvestigationReport) -> str:
    """Serialize an InvestigationReport into structured JSON with indentation."""
    return report.model_dump_json(indent=2)

