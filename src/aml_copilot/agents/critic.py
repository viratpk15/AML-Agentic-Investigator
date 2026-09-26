"""Critic role performing deterministic and LLM-assisted verification of investigation drafts."""

import re
from typing import Any, Callable, Dict, List, Optional, Set
from langchain_core.language_models.chat_models import BaseChatModel

from aml_copilot.agents.models import CritiqueResult
from aml_copilot.agents.state import InvestigationState, emit_investigation_event
from aml_copilot.logger import get_logger
from aml_copilot.models.transaction import TransactionStatement

logger = get_logger(__name__)

CRITIC_SYSTEM_PROMPT = """You are a meticulous, skeptical Senior AML Quality & Audit Critic.
Your duty is NOT to write or rewrite the investigation, but to scrutinize an investigation draft for:
1. Unsupported claims or hallucinated evidence.
2. Inconsistent transaction IDs, dates, or amounts.
3. Premature or illegal conclusions (declaring guilt, crime, or demanding account closure).
4. Missing required evidence needed to answer the analyst's question.

Be rigorous and objective. If any claim is unbacked or oversteps compliance safety boundaries, flag it immediately."""

PROHIBITED_SAFETY_PATTERNS = [
    (r"\b(guilty\s+of\s+(?:money\s+laundering|fraud|crime))\b", "Declaring customer guilt"),
    (r"\b(is\s+laundering\s+money)\b", "Definitive money laundering claim"),
    (r"\b(committed\s+(?:a\s+)?crime)\b", "Criminal accusation"),
    (r"\b(criminal\s+(?:act|conduct|liability)\s+established)\b", "Declaring criminal liability"),
    (r"\b(close\s+(?:the\s+)?account)\b", "Mandating account closure"),
    (r"\b(file\s+(?:a\s+|an\s+)?(?:sar|str|suspicious\s+transaction\s+report))\b", "Autonomous regulatory reporting order"),
]


def evaluate_investigation_draft(
    draft_text: str,
    statement: TransactionStatement,
    question: str = "",
    canonical_evidence: Optional[Any] = None,
) -> CritiqueResult:
    """Perform comprehensive deterministic checks on an investigation draft.

    Verifies two distinct requirements:
    A. SOURCE EXISTENCE: Does the transaction exist in the customer statement?
    B. SOURCE CLAIM & PROVENANCE: Was the transaction actually flagged by the claimed source?
       (e.g., Isolation Forest anomaly vs. rule trigger vs. normal transaction).

    Args:
        draft_text: Synthesized text of the investigation draft.
        statement: Validated customer TransactionStatement.
        question: The original investigation query.
        canonical_evidence: Optional pre-computed CanonicalEvidence. If None, built deterministically.

    Returns:
        Structured CritiqueResult indicating pass/fail status and specific issues.
    """
    issues: List[str] = []
    missing_evidence: List[str] = []
    unsupported_claims: List[str] = []
    required_revisions: List[str] = []
    checked_txn_ids: List[str] = []
    invalid_txn_ids: List[str] = []
    safety_violations: List[str] = []

    content = draft_text or ""
    clean_text = content.strip()

    # 1. Minimum Content & Substantiveness Check
    if not clean_text:
        issues.append("Investigation draft is empty.")
        missing_evidence.append("Comprehensive summary of transactional activity and evidence.")
        required_revisions.append("Gather transaction evidence using available tools and provide an objective findings narrative.")

    # 2. Extract and Validate Transaction IDs against Statement
    stmt_txns = {t.transaction_id: t for t in statement.transactions if t.transaction_id}
    cited_ids = sorted(list(set(re.findall(r"\bTXN\d+\b", clean_text))))

    # Resolve Canonical Evidence for Provenance Verification
    if canonical_evidence is None:
        try:
            from aml_copilot.models.evidence import build_canonical_evidence
            canonical_evidence = build_canonical_evidence(statement)
        except Exception:
            canonical_evidence = None

    actual_anomaly_ids = set(canonical_evidence.anomaly_transaction_ids) if canonical_evidence else set()
    actual_rule_map: Dict[str, Set[str]] = {}
    if canonical_evidence:
        for rf in canonical_evidence.rule_findings:
            actual_rule_map.setdefault(rf.rule_id, set()).update(rf.supporting_transaction_ids)

    for tid in cited_ids:
        checked_txn_ids.append(tid)
        if tid not in stmt_txns:
            invalid_txn_ids.append(tid)
            msg = f"Cited transaction identifier '{tid}' does not exist in the customer statement."
            issues.append(msg)
            unsupported_claims.append(msg)
            required_revisions.append(f"Remove or correct non-existent transaction '{tid}'.")
        else:
            t = stmt_txns[tid]
            # Find sentences containing this tid
            sentences = [s for s in re.split(r"[.\n]", clean_text) if tid in s]
            for s in sentences:
                # Strip dates like 2026-08-10 before searching for amounts so year does not match as an amount
                s_no_dates = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", s)
                # Look for amounts in sentence: e.g. ₹480,000 or 480,000 or 480000
                amounts_found = re.findall(
                    r"(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|\b[0-9]{4,}(?:\.[0-9]+)?\b)",
                    s_no_dates,
                    flags=re.IGNORECASE,
                )
                for amt_str in amounts_found:
                    try:
                        amt_val = float(amt_str.replace(",", "").strip())
                    except ValueError:
                        continue

                    # If this number appears directly tied to this transaction ID, verify it matches
                    # credit, debit, or balance
                    valid_amounts = [val for val in [t.credit, t.debit, t.balance] if val is not None]
                    matches_any = any(abs(amt_val - v) < 1.0 for v in valid_amounts)

                    if not matches_any and any(
                        w in s.lower()
                        for w in ["amount of", "transfer of", "credit of", "debit of", "valued at", "of ₹", "of rs"]
                    ):
                        msg = (
                            f"Amount ₹{amt_val:,.2f} mentioned with '{tid}' does not match "
                            f"statement records (credit: {t.credit}, debit: {t.debit}, balance: {t.balance})."
                        )
                        issues.append(msg)
                        unsupported_claims.append(msg)
                        required_revisions.append(f"Verify and correct amount cited for '{tid}'.")

                # Check dates mentioned specifically for this transaction ID
                date_matches = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", s)
                for d_str in date_matches:
                    if str(t.date) != d_str:
                        msg = f"Date {d_str} cited for '{tid}' does not match statement date {t.date}."
                        issues.append(msg)
                        unsupported_claims.append(msg)
                        required_revisions.append(f"Correct the date cited for '{tid}' to {t.date}.")

                # Flow direction check scoped to local context window of this tid
                tid_idx = s.find(tid)
                w_start = max(0, tid_idx - 65)
                w_end = min(len(s), tid_idx + 65)
                local_s = s[w_start:w_end].lower()

                is_credit_claim = any(w in local_s for w in ["incoming credit", "credit of", "received from", "deposit of", "credit transfer"])
                is_debit_claim = any(w in local_s for w in ["outgoing debit", "debit of", "transferred to", "payment to", "withdrawal of", "debit transfer"])
                if is_credit_claim and not is_debit_claim and t.credit is None and t.debit is not None:
                    msg = f"Direction mismatch for '{tid}': claimed as incoming credit, but statement record is an outgoing debit of ₹{t.debit:,.2f}."
                    issues.append(msg)
                    unsupported_claims.append(msg)
                    required_revisions.append(f"Correct flow direction of '{tid}' to debit.")
                elif is_debit_claim and not is_credit_claim and t.debit is None and t.credit is not None:
                    msg = f"Direction mismatch for '{tid}': claimed as outgoing debit, but statement record is an incoming credit of ₹{t.credit:,.2f}."
                    issues.append(msg)
                    unsupported_claims.append(msg)
                    required_revisions.append(f"Correct flow direction of '{tid}' to credit.")

    # 3. Anomaly Claim Provenance Verification
    # Scrutinize whether any transaction is claimed to be an anomaly when it was NOT flagged
    sentences = [s.strip() for s in re.split(r"[.\n]", clean_text) if s.strip()]
    for s in sentences:
        low_s = s.lower()
        # Look for anomaly indicators in sentence
        is_anomaly_sentence = any(
            kw in low_s
            for kw in [
                "isolation forest",
                "statistical anomal",
                "statistical outlier",
                "flagged as anomal",
                "anomaly transaction",
                "anomalous transaction",
                "detected anomaly",
                "detected anomalies",
                "anomaly signals",
                "anomaly score",
            ]
        )
        if is_anomaly_sentence and not any(neg in low_s for neg in ["not an anomaly", "no anomaly", "not anomalous", "non-anomalous", "within normal"]):
            s_tids = re.findall(r"\bTXN\d+\b", s)
            for tid in s_tids:
                if tid in stmt_txns and tid not in actual_anomaly_ids:
                    msg = (
                        f"Provenance failure: Transaction '{tid}' is claimed as an Isolation Forest anomaly or statistical outlier, "
                        f"but was NOT flagged by the anomaly detection pipeline (actual anomalies: {sorted(list(actual_anomaly_ids)) or 'None'})."
                    )
                    issues.append(msg)
                    unsupported_claims.append(msg)
                    required_revisions.append(
                        f"Correct claim: transaction '{tid}' was not flagged as an anomaly. "
                        f"Only transactions {sorted(list(actual_anomaly_ids))} are verified Isolation Forest anomalies."
                    )

    # 4. Rule Trigger Provenance Verification
    # Scrutinize whether any transaction is claimed to trigger a specific rule when it did not
    rule_claim_patterns = [
        ("RULE_LARGE_TRANSACTION", [r"\blarge\s+transaction\b", r"\bexceeded\s+(?:the\s+)?(?:absolute\s+)?threshold\b"]),
        ("RULE_SUDDEN_VOLUME_INCREASE", [r"\bsudden\s+volume\b", r"\bvolume\s+spike\b", r"\bvolume\s+increase\b"]),
        ("RULE_LARGE_INFLOW_RAPID_OUTFLOW", [r"\bpass-through\b", r"\blayering\b", r"\binflow[/\s]+rapid\s+outflow\b"]),
        ("RULE_RAPID_FUNDS_MOVEMENT", [r"\brapid\s+movement\b", r"\brapid\s+velocity\b", r"\brapid\s+flow\b"]),
        ("RULE_MANY_NEW_COUNTERPARTIES", [r"\bmany\s+new\s+counterparties\b", r"\bnew\s+counterpart(?:y|ies)\s+surge\b"]),
        ("RULE_HIGH_TRANSACTION_FREQUENCY", [r"\bhigh\s+frequency\b", r"\bfrequency\s+spike\b", r"\bfrequency\s+surge\b"]),
        ("RULE_ROUND_AMOUNT", [r"\bround\s+amount\b", r"\bstructuring\b"]),
    ]

    for s in sentences:
        s_tids = re.findall(r"\bTXN\d+\b", s)
        if not s_tids:
            continue
        low_s = s.lower()
        for rule_id, patterns in rule_claim_patterns:
            rule_claimed = (rule_id.lower() in low_s) or any(re.search(pat, low_s) for pat in patterns)
            if rule_claimed and any(trig in low_s for trig in ["triggered", "flagged by", "matched", "identified by", "violat", "supporting", "under rule", "as a "]):
                valid_rule_tids = actual_rule_map.get(rule_id, set())
                for tid in s_tids:
                    if tid in stmt_txns and tid not in valid_rule_tids:
                        msg = (
                            f"Provenance failure: Transaction '{tid}' is claimed to trigger '{rule_id}', "
                            f"but is not in actual rule detection output (actual triggering transactions: {sorted(list(valid_rule_tids)) or 'None'})."
                        )
                        issues.append(msg)
                        unsupported_claims.append(msg)
                        required_revisions.append(
                            f"Correct rule claim: '{tid}' did not trigger '{rule_id}'."
                        )

    # 4b. Human Review Provenance Verification
    # If the draft claims a transaction specifically requires human review or flags it for review,
    # verify that the transaction actually has supporting detection signals in canonical evidence
    valid_review_tids = {item.transaction_id for item in canonical_evidence.human_review_items} if canonical_evidence else set()
    hr_patterns = [
        r"\brequires?\s+human\s+review\b",
        r"\brecommended\s+for\s+(?:human\s+)?review\b",
        r"\bhighlighted\s+for\s+(?:human\s+)?review\b",
        r"\bhuman\s+review\s+(?:required|recommended|shortlist|item)\b",
        r"\bescalat(?:e|ed|ion)\s+for\s+review\b",
    ]
    for s in sentences:
        low_s = s.lower()
        if any(re.search(p, low_s) for p in hr_patterns):
            s_tids = re.findall(r"\bTXN\d+\b", s)
            for tid in s_tids:
                if tid in stmt_txns and canonical_evidence and tid not in valid_review_tids:
                    msg = (
                        f"Provenance failure: Transaction '{tid}' is claimed to require human review, "
                        f"but has no supporting risk signals or convergence in canonical evidence."
                    )
                    issues.append(msg)
                    unsupported_claims.append(msg)
                    required_revisions.append(
                        f"Remove human review recommendation for '{tid}' as it lacks supporting evidence."
                    )

    # 5. Check for specific transactions mentioned in the Question
    if question:
        question_txns = re.findall(r"\bTXN\d+\b", question)
        for q_tid in question_txns:
            if q_tid in stmt_txns and q_tid not in cited_ids:
                msg = f"Investigation question specifically inquires about '{q_tid}', but it is not cited or analyzed in the draft."
                missing_evidence.append(msg)
                issues.append(msg)
                required_revisions.append(f"Inspect transaction '{q_tid}' using search_transactions and include it in findings.")

    # 6. Rapid Movement / Conduit Evidence Check
    rapid_patterns = [
        r"rapid\s+(?:movement|inflow|outflow|pass-through|flow)\s+(?:was\s+observed|detected|identified|found)",
        r"observed\s+rapid\s+(?:movement|inflow|outflow|pass-through|flow)",
    ]
    claims_rapid = any(re.search(p, clean_text, flags=re.IGNORECASE) for p in rapid_patterns)
    if claims_rapid and len(checked_txn_ids) < 2:
        msg = "Factual claim of rapid fund movement requires citing both the incoming credit and outgoing debit transaction IDs."
        missing_evidence.append(msg)
        issues.append(msg)
        required_revisions.append("Identify and cite the specific credit and debit transaction IDs substantiating the rapid movement pattern.")

    # 7. AML Safety & Compliance Boundary Violations
    for pattern, desc in PROHIBITED_SAFETY_PATTERNS:
        matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
        if matches:
            violation_str = matches[0] if isinstance(matches[0], str) else matches[0][0]
            safety_violations.append(f"{desc}: '{violation_str}'")
            unsupported_claims.append(f"Prohibited compliance assertion: '{violation_str}'. The system must NOT declare legal guilt or make autonomous enforcement decisions.")
            issues.append(f"Safety boundary violated: {desc}")
            required_revisions.append("Rephrase findings using professional non-judgmental language: 'unusual activity observed', 'investigation signal', 'warrants compliance review'.")

    # 7. Overall Pass/Fail Status
    passed = (
        len(issues) == 0
        and len(unsupported_claims) == 0
        and len(safety_violations) == 0
        and len(missing_evidence) == 0
    )

    # 8. Deterministic Transaction Counting Metrics
    stmt_count = len(statement.transactions) if statement and statement.transactions else 0
    narrative_ref_count = len(cited_ids)
    hr_count = (
        len(canonical_evidence.human_review_items)
        if canonical_evidence and getattr(canonical_evidence, "human_review_items", None)
        else 0
    )
    verified_ref_count = len([tid for tid in cited_ids if tid in stmt_txns])
    unverified_ref_count = len(invalid_txn_ids)

    return CritiqueResult(
        passed=passed,
        issues=issues,
        missing_evidence=missing_evidence,
        unsupported_claims=unsupported_claims,
        required_revisions=required_revisions,
        checked_transaction_ids=checked_txn_ids,
        invalid_transaction_ids=invalid_txn_ids,
        safety_violations=safety_violations,
        statement_transaction_count=stmt_count,
        narrative_transaction_reference_count=narrative_ref_count,
        human_review_transaction_count=hr_count,
        verified_transaction_reference_count=verified_ref_count,
        unverified_transaction_reference_count=unverified_ref_count,
    )


def create_critic_node(
    statement: TransactionStatement,
    critic_llm: Optional[BaseChatModel] = None,
) -> Callable[[InvestigationState], Dict[str, Any]]:
    """Create the Critic Node function for the LangGraph workflow.

    Responsibilities:
    1. Inspect the latest investigation draft from state.
    2. Execute deterministic Python checks (valid IDs, amounts, dates, safety boundaries).
    3. Optionally run LLM critic for nuanced reasoning critique if configured.
    4. Emit a structured CritiqueResult and update state status ('PASS' or 'FAIL').
    """

    def critic_node(state: InvestigationState) -> Dict[str, Any]:
        draft_text = state.get("final_response") or ""
        if not draft_text and state.get("draft"):
            draft_text = state["draft"].raw_response

        question = state.get("question", "")
        logger.info(f"[Graph: Critic Node] Evaluating investigation draft ({len(draft_text)} chars)")
        emit_investigation_event(
            state,
            event_type="CRITIC_STARTED",
            node="critic",
            message="Senior Compliance Critic auditing draft against statement records and safety boundaries...",
        )

        critique = evaluate_investigation_draft(
            draft_text=draft_text,
            statement=statement,
            question=question,
            canonical_evidence=state.get("canonical_evidence"),
        )

        status = "PASS" if critique.passed else "FAIL"
        feedback_parts: List[str] = []
        if not critique.passed:
            if critique.issues:
                feedback_parts.append("Issues Found:\n- " + "\n- ".join(critique.issues))
            if critique.missing_evidence:
                feedback_parts.append("Missing Evidence:\n- " + "\n- ".join(critique.missing_evidence))
            if critique.unsupported_claims:
                feedback_parts.append("Unsupported Claims:\n- " + "\n- ".join(critique.unsupported_claims))
            if critique.required_revisions:
                feedback_parts.append("Required Revisions:\n- " + "\n- ".join(critique.required_revisions))

        critic_feedback = "\n\n".join(feedback_parts)
        logger.info(f"[Graph: Critic Node] Status: {status} (Issues: {len(critique.issues)}, Violations: {len(critique.safety_violations)})")

        if critique.passed:
            emit_investigation_event(
                state,
                event_type="CRITIC_PASSED",
                node="critic",
                status="PASS",
                message=f"Critic audit PASSED: {len(critique.checked_transaction_ids)} transaction ID(s) and safety guardrails verified.",
                metadata={
                    "checked_transaction_ids": critique.checked_transaction_ids,
                },
            )
        else:
            emit_investigation_event(
                state,
                event_type="CRITIC_FAILED",
                node="critic",
                status="FAIL",
                message=f"Critic audit FAILED: {len(critique.issues)} issue(s) identified (Safety violations: {len(critique.safety_violations)}).",
                metadata={
                    "issues": critique.issues,
                    "missing_evidence": critique.missing_evidence,
                    "unsupported_claims": critique.unsupported_claims,
                    "safety_violations": critique.safety_violations,
                    "required_revisions": critique.required_revisions,
                    "invalid_transaction_ids": critique.invalid_transaction_ids,
                },
            )

        return {
            "critic_result": critique,
            "critic_status": status,
            "critic_feedback": critic_feedback,
        }

    return critic_node
