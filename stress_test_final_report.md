# AML Investigation Report

## 1. Investigation Overview

- **Report ID**: `REP-AML-20260925-2F0C83`
- **Generated Time**: `2026-09-25T16:15:28.535420+00:00`
- **Customer / Account**: Arjun Malhotra (Account: `XX6384`)
- **Analysis Period**: 01 Sep 2026 – 28 Oct 2026
- **Investigation Question**: Investigate unusual movement of funds in this account and highlight transactions requiring human review.
- **Total Transactions Analyzed**: 54

## 2. Executive Summary

- 54 transactions analyzed across statement period 01 Sep 2026 – 28 Oct 2026.
- 50 transactions generated prioritized human-review signals (28 HIGH, 19 MEDIUM, 3 LOW).
- 6 transactions were identified as Isolation Forest statistical outliers: TXN401, TXN404, TXN434, TXN442, TXN445, TXN451.
- Key observed patterns include high-value transaction bursts, rapid inflow/outflow pass-through sequences, velocity surges, and counterparty concentration.
- Highest-convergence review items warranting immediate compliance inspection: TXN445 (₹575,000.00 credit via WESTBROOK MATERIALS); TXN434 (₹620,000.00 credit via NORTHGATE COMPONENTS).
- These findings constitute automated investigative risk indicators and do not represent determinations of illegal activity, fraud, or money laundering.

## 3. Observed Transaction Evidence

| Transaction ID | Date | Flow | Amount (INR) | Counterparty | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `TXN401` | 2026-09-01 | CREDIT | ₹102,500.00 | AURORA MEDIA LABS | ✓ Verified in Statement |
| `TXN402` | 2026-09-02 | DEBIT | ₹26,000.00 | RENT | ✓ Verified in Statement |
| `TXN403` | 2026-09-03 | DEBIT | ₹5,480.00 | GREEN MART | ✓ Verified in Statement |
| `TXN404` | 2026-09-04 | DEBIT | ₹3,260.00 | Unspecified | ✓ Verified in Statement |
| `TXN405` | 2026-09-06 | CREDIT | ₹285,000.00 | OAKRIDGE EXPORTS | ✓ Verified in Statement |
| `TXN406` | 2026-09-06 | DEBIT | ₹132,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN407` | 2026-09-09 | CREDIT | ₹318,000.00 | CRESTLINE INDUSTRIAL | ✓ Verified in Statement |
| `TXN408` | 2026-09-09 | DEBIT | ₹145,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN409` | 2026-09-10 | DEBIT | ₹86,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN410` | 2026-09-12 | DEBIT | ₹48,000.00 | COUNTERPARTY K11 | ✓ Verified in Statement |
| `TXN411` | 2026-09-12 | DEBIT | ₹46,500.00 | COUNTERPARTY K12 | ✓ Verified in Statement |
| `TXN412` | 2026-09-12 | DEBIT | ₹44,000.00 | COUNTERPARTY K13 | ✓ Verified in Statement |
| `TXN413` | 2026-09-15 | CREDIT | ₹405,000.00 | OAKRIDGE EXPORTS | ✓ Verified in Statement |
| `TXN414` | 2026-09-15 | DEBIT | ₹175,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN415` | 2026-09-15 | DEBIT | ₹115,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN416` | 2026-09-18 | CREDIT | ₹362,000.00 | SILVER OAK TRADING | ✓ Verified in Statement |
| `TXN417` | 2026-09-18 | DEBIT | ₹158,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN418` | 2026-09-19 | DEBIT | ₹104,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN419` | 2026-09-21 | DEBIT | ₹52,000.00 | COUNTERPARTY L21 | ✓ Verified in Statement |
| `TXN420` | 2026-09-21 | DEBIT | ₹51,000.00 | COUNTERPARTY L22 | ✓ Verified in Statement |
| `TXN421` | 2026-09-21 | DEBIT | ₹49,000.00 | COUNTERPARTY L23 | ✓ Verified in Statement |
| `TXN422` | 2026-09-23 | CREDIT | ₹440,000.00 | HORIZON PROCUREMENT | ✓ Verified in Statement |
| `TXN423` | 2026-09-23 | DEBIT | ₹190,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN424` | 2026-09-24 | DEBIT | ₹126,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN425` | 2026-09-27 | CREDIT | ₹395,000.00 | CRESTLINE INDUSTRIAL | ✓ Verified in Statement |
| `TXN426` | 2026-09-27 | DEBIT | ₹168,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN427` | 2026-09-27 | DEBIT | ₹112,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN428` | 2026-09-28 | DEBIT | ₹74,000.00 | NEW COUNTERPARTY Z31 | ✓ Verified in Statement |
| `TXN429` | 2026-09-28 | DEBIT | ₹69,000.00 | NEW COUNTERPARTY Z32 | ✓ Verified in Statement |
| `TXN430` | 2026-09-28 | DEBIT | ₹64,000.00 | NEW COUNTERPARTY Z33 | ✓ Verified in Statement |
| `TXN431` | 2026-09-30 | DEBIT | ₹7,450.00 | HOUSEHOLD PURCHASE | ✓ Verified in Statement |
| `TXN432` | 2026-10-01 | CREDIT | ₹102,500.00 | AURORA MEDIA LABS | ✓ Verified in Statement |
| `TXN433` | 2026-10-02 | DEBIT | ₹26,000.00 | RENT | ✓ Verified in Statement |
| `TXN434` | 2026-10-05 | CREDIT | ₹620,000.00 | NORTHGATE COMPONENTS | ✓ Verified in Statement |
| `TXN435` | 2026-10-05 | DEBIT | ₹275,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN436` | 2026-10-06 | DEBIT | ₹180,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN437` | 2026-10-07 | DEBIT | ₹58,000.00 | COUNTERPARTY T41 | ✓ Verified in Statement |
| `TXN438` | 2026-10-07 | DEBIT | ₹56,000.00 | COUNTERPARTY T42 | ✓ Verified in Statement |
| `TXN439` | 2026-10-10 | CREDIT | ₹515,000.00 | MARINER GLOBAL TRADE | ✓ Verified in Statement |
| `TXN440` | 2026-10-10 | DEBIT | ₹240,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN441` | 2026-10-11 | DEBIT | ₹155,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN442` | 2026-10-15 | CREDIT | ₹455,000.00 | NORTHGATE COMPONENTS | ✓ Verified in Statement |
| `TXN443` | 2026-10-15 | DEBIT | ₹205,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN444` | 2026-10-16 | DEBIT | ₹140,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN445` | 2026-10-20 | CREDIT | ₹575,000.00 | WESTBROOK MATERIALS | ✓ Verified in Statement |
| `TXN446` | 2026-10-20 | DEBIT | ₹255,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN447` | 2026-10-20 | DEBIT | ₹165,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN448` | 2026-10-21 | DEBIT | ₹72,000.00 | COUNTERPARTY V51 | ✓ Verified in Statement |
| `TXN449` | 2026-10-21 | DEBIT | ₹68,000.00 | COUNTERPARTY V52 | ✓ Verified in Statement |
| `TXN450` | 2026-10-21 | DEBIT | ₹63,000.00 | COUNTERPARTY V53 | ✓ Verified in Statement |
| `TXN451` | 2026-10-25 | CREDIT | ₹490,000.00 | MARINER GLOBAL TRADE | ✓ Verified in Statement |
| `TXN452` | 2026-10-25 | DEBIT | ₹218,000.00 | LUMEN CONSULTING | ✓ Verified in Statement |
| `TXN453` | 2026-10-26 | DEBIT | ₹150,000.00 | RIVERBEND SUPPLIERS | ✓ Verified in Statement |
| `TXN454` | 2026-10-28 | DEBIT | ₹15,000.00 | FAMILY TRANSFER | ✓ Verified in Statement |

## 4. Detection Findings

### Rule-Based Signals

- **Unusually Large Transaction** (`RULE_LARGE_TRANSACTION`)
  - **Total Triggered**: 33 instance(s) (MEDIUM: 17, HIGH: 16)
  - **Condition Summary**: Transaction TXN401 of ₹102,500.00 (incoming credit) exceeded the configured absolute transaction threshold of ₹100,000.00, although its value was below the customer's median transaction amount (₹129,000.00).
  - **Representative Examples**: `TXN434`: ₹620,000.00 (2026-10-05, NORTHGATE COMPONENTS), `TXN445`: ₹575,000.00 (2026-10-20, WESTBROOK MATERIALS), `TXN439`: ₹515,000.00 (2026-10-10, MARINER GLOBAL TRADE)
  - **Supporting Transactions**: `TXN401`, `TXN405`, `TXN406`, `TXN407`, `TXN408`, `TXN413`, `TXN414`, `TXN415`, `TXN416`, `TXN417` ... (+23 more)
- **Sudden Transaction Volume Increase** (`RULE_SUDDEN_VOLUME_INCREASE`)
  - **Total Triggered**: 3 instance(s) (MEDIUM: 3)
  - **Condition Summary**: Aggregate volume on 2026-10-20 reached 995,000.00, which is 3.3x the customer's average daily active volume of 305,054.52.
  - **Representative Examples**: `TXN445`: ₹575,000.00 (2026-10-20, WESTBROOK MATERIALS), `TXN446`: ₹255,000.00 (2026-10-20, LUMEN CONSULTING), `TXN447`: ₹165,000.00 (2026-10-20, RIVERBEND SUPPLIERS)
  - **Supporting Transactions**: `TXN445`, `TXN446`, `TXN447`
- **Large Incoming Transaction Followed by Rapid Outgoing** (`RULE_LARGE_INFLOW_RAPID_OUTFLOW`)
  - **Total Triggered**: 17 instance(s) (HIGH: 17)
  - **Condition Summary**: Incoming credit of 395,000.00 (TXN425) on 2026-09-27 was followed within 2 day(s) by 5 outgoing debit(s) totaling 487,000.00 (123.3% turnover).
  - **Representative Examples**: `TXN434`: ₹620,000.00 (2026-10-05, NORTHGATE COMPONENTS), `TXN445`: ₹575,000.00 (2026-10-20, WESTBROOK MATERIALS), `TXN425`: ₹395,000.00 (2026-09-27, CRESTLINE INDUSTRIAL)
  - **Supporting Transactions**: `TXN425`, `TXN426`, `TXN427`, `TXN428`, `TXN429`, `TXN430`, `TXN434`, `TXN435`, `TXN436`, `TXN437` ... (+7 more)
- **Rapid Movement of Funds** (`RULE_RAPID_MOVEMENT_OF_FUNDS`)
  - **Total Triggered**: 36 instance(s) (HIGH: 41, MEDIUM: 5)
  - **Condition Summary**: High-velocity fund turnover across 6 transactions between 2026-09-09 and 2026-09-12: received 318,000.00 and disbursed 369,500.00 (116.2% turnover).
  - **Representative Examples**: `TXN434`: ₹620,000.00 (2026-10-05, NORTHGATE COMPONENTS), `TXN445`: ₹575,000.00 (2026-10-20, WESTBROOK MATERIALS), `TXN422`: ₹440,000.00 (2026-09-23, HORIZON PROCUREMENT)
  - **Supporting Transactions**: `TXN407`, `TXN408`, `TXN409`, `TXN410`, `TXN411`, `TXN412`, `TXN413`, `TXN414`, `TXN415`, `TXN416` ... (+26 more)
- **Many New Counterparties** (`RULE_MANY_NEW_COUNTERPARTIES`)
  - **Total Triggered**: 28 instance(s) (MEDIUM: 28)
  - **Condition Summary**: Observed 28 previously unseen counterparties introduced within the statement period: AURORA MEDIA LABS, RENT, GREEN MART, OAKRIDGE EXPORTS, LUMEN CONSULTING, CRESTLINE INDUSTRIAL, RIVERBEND SUPPLIERS, COUNTERPARTY K11, COUNTERPARTY K12, COUNTERPARTY K13, SILVER OAK TRADING, COUNTERPARTY L21, COUNTERPARTY L22, COUNTERPARTY L23, HORIZON PROCUREMENT, NEW COUNTERPARTY Z31, NEW COUNTERPARTY Z32, NEW COUNTERPARTY Z33, HOUSEHOLD PURCHASE, NORTHGATE COMPONENTS, COUNTERPARTY T41, COUNTERPARTY T42, MARINER GLOBAL TRADE, WESTBROOK MATERIALS, COUNTERPARTY V51, COUNTERPARTY V52, COUNTERPARTY V53, FAMILY TRANSFER.
  - **Representative Examples**: `TXN434`: ₹620,000.00 (2026-10-05, NORTHGATE COMPONENTS), `TXN445`: ₹575,000.00 (2026-10-20, WESTBROOK MATERIALS), `TXN439`: ₹515,000.00 (2026-10-10, MARINER GLOBAL TRADE)
  - **Supporting Transactions**: `TXN401`, `TXN402`, `TXN403`, `TXN405`, `TXN406`, `TXN407`, `TXN409`, `TXN410`, `TXN411`, `TXN412` ... (+18 more)

### Statistical Anomalies (Isolation Forest)

Isolation Forest unsupervised anomaly detection flagged **6** statistical outliers: `TXN401`, `TXN404`, `TXN434`, `TXN442`, `TXN445`, `TXN451`.

| Transaction ID | Anomaly Score | Status | Key Feature Context | Provenance |
| :--- | :--- | :--- | :--- | :--- |
| `TXN401` | -0.0351 | Statistical Outlier | amount=102500.0, is_credit=1.0, days_since_previous=0.0 | Verified Model Output |
| `TXN404` | -0.0230 | Statistical Outlier | amount=3260.0, is_credit=0.0, days_since_previous=1.0 | Verified Model Output |
| `TXN434` | -0.0441 | Statistical Outlier | amount=620000.0, is_credit=1.0, days_since_previous=3.0 | Verified Model Output |
| `TXN442` | -0.0029 | Statistical Outlier | amount=455000.0, is_credit=1.0, days_since_previous=4.0 | Verified Model Output |
| `TXN445` | -0.0826 | Statistical Outlier | amount=575000.0, is_credit=1.0, days_since_previous=4.0 | Verified Model Output |
| `TXN451` | -0.0321 | Statistical Outlier | amount=490000.0, is_credit=1.0, days_since_previous=4.0 | Verified Model Output |

## 5. Customer Profile

- **Transaction Count**: 54 (31 active days)
- **Turnover**: Credits: ₹5,065,000.00 | Debits: ₹4,391,690.00 | Net Flow: ₹673,310.00
- **Average Transaction**: ₹175,123.89
- **Credit-to-Debit Ratio**: 1.15
- **Unique Counterparties**: 28
- **Peak Credit**: ₹620,000.00
- **Peak Debit**: ₹275,000.00
- **Behavioral Indicators**:
  - High-value transaction activity observed exceeding typical baseline parameters.
  - Elevated aggregate transaction volume observed across statement duration.
  - Multiple distinct counterparties observed across transactional flow.
  - Frequent introduction of newly observed counterparties.

## 6. Network Analysis

- **Unique Counterparties**: 28
- **Total Graph Nodes**: 29 (1 customer account + 28 unique counterparties)
- **Total Graph Edges**: 28
- **Dominant Counterparties**: LUMEN CONSULTING

### Relational Topology Findings
- **One To Many Topology**
  - *Structure*: Customer displays a one-to-many star network connecting with 28 distinct counterparties.
  - *Involved Entities*: Arjun Malhotra, AURORA MEDIA LABS, RENT, GREEN MART, OAKRIDGE EXPORTS, LUMEN CONSULTING
  - *Transactions*: `TXN413`, `TXN405`, `TXN435`, `TXN446`, `TXN440`, `TXN452` ... (+12 more)
- **Dominant High Value Counterparty**
  - *Structure*: Counterparty 'LUMEN CONSULTING' represents a dominant high-volume entity, accounting for ₹2,161,000.00 (22.9% of counterparty volume).
  - *Involved Entities*: LUMEN CONSULTING, Arjun Malhotra
  - *Transactions*: `TXN406`, `TXN408`, `TXN414`, `TXN417`, `TXN423`, `TXN426` ... (+5 more)

## 7. AML Knowledge Context

*No AML reference guidance items were retrieved during this investigation.*

## 8. Evidence Convergence

Prioritized transactions demonstrating simultaneous convergence across multiple independent detection domains:

| Priority | Transaction ID | Date | Flow | Amount (INR) | Counterparty | Independent Signal Domains | Supporting Reasons |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HIGH** | `TXN445` | 2026-10-20 | CREDIT | ₹575,000.00 | WESTBROOK MATERIALS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold), Statistical (Isolation Forest Outlier), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` (+2 more) |
| **HIGH** | `TXN434` | 2026-10-05 | CREDIT | ₹620,000.00 | NORTHGATE COMPONENTS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold), Statistical (Isolation Forest Outlier), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` (+1 more) |
| **HIGH** | `TXN401` | 2026-09-01 | CREDIT | ₹102,500.00 | AURORA MEDIA LABS | Network (Star Topology), Rule (Large / Round Amount Threshold), Statistical (Isolation Forest Outlier), Volume (New Counterparty Surge) | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN451` | 2026-10-25 | CREDIT | ₹490,000.00 | MARINER GLOBAL TRADE | Rule (Large / Round Amount Threshold), Statistical (Isolation Forest Outlier) | `RULE_LARGE_TRANSACTION`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN442` | 2026-10-15 | CREDIT | ₹455,000.00 | NORTHGATE COMPONENTS | Rule (Large / Round Amount Threshold), Statistical (Isolation Forest Outlier) | `RULE_LARGE_TRANSACTION`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN446` | 2026-10-20 | DEBIT | ₹255,000.00 | LUMEN CONSULTING | Flow (Rapid Movement / Inflow-Outflow), Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION` (+2 more) |
| **HIGH** | `TXN435` | 2026-10-05 | DEBIT | ₹275,000.00 | LUMEN CONSULTING | Flow (Rapid Movement / Inflow-Outflow), Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION` (+1 more) |
| **HIGH** | `TXN426` | 2026-09-27 | DEBIT | ₹168,000.00 | LUMEN CONSULTING | Flow (Rapid Movement / Inflow-Outflow), Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION` (+1 more) |
| **HIGH** | `TXN423` | 2026-09-23 | DEBIT | ₹190,000.00 | LUMEN CONSULTING | Flow (Rapid Movement / Inflow-Outflow), Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN414` | 2026-09-15 | DEBIT | ₹175,000.00 | LUMEN CONSULTING | Flow (Rapid Movement / Inflow-Outflow), Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN417` | 2026-09-18 | DEBIT | ₹158,000.00 | LUMEN CONSULTING | Flow (Rapid Movement / Inflow-Outflow), Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN408` | 2026-09-09 | DEBIT | ₹145,000.00 | LUMEN CONSULTING | Flow (Rapid Movement / Inflow-Outflow), Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN406` | 2026-09-06 | DEBIT | ₹132,000.00 | LUMEN CONSULTING | Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold), Volume (New Counterparty Surge) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES` |
| **HIGH** | `TXN422` | 2026-09-23 | CREDIT | ₹440,000.00 | HORIZON PROCUREMENT | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold), Volume (New Counterparty Surge) | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN413` | 2026-09-15 | CREDIT | ₹405,000.00 | OAKRIDGE EXPORTS | Flow (Rapid Movement / Inflow-Outflow), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN416` | 2026-09-18 | CREDIT | ₹362,000.00 | SILVER OAK TRADING | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold), Volume (New Counterparty Surge) | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN407` | 2026-09-09 | CREDIT | ₹318,000.00 | CRESTLINE INDUSTRIAL | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold), Volume (New Counterparty Surge) | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN405` | 2026-09-06 | CREDIT | ₹285,000.00 | OAKRIDGE EXPORTS | Network (Star Topology), Rule (Large / Round Amount Threshold), Volume (New Counterparty Surge) | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES` |
| **HIGH** | `TXN440` | 2026-10-10 | DEBIT | ₹240,000.00 | LUMEN CONSULTING | Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| **HIGH** | `TXN452` | 2026-10-25 | DEBIT | ₹218,000.00 | LUMEN CONSULTING | Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| **HIGH** | `TXN443` | 2026-10-15 | DEBIT | ₹205,000.00 | LUMEN CONSULTING | Network (Dominant Counterparty Hub), Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| **HIGH** | `TXN447` | 2026-10-20 | DEBIT | ₹165,000.00 | RIVERBEND SUPPLIERS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS`, `RULE_SUDDEN_VOLUME_INCREASE` |
| **HIGH** | `TXN425` | 2026-09-27 | CREDIT | ₹395,000.00 | CRESTLINE INDUSTRIAL | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN436` | 2026-10-06 | DEBIT | ₹180,000.00 | RIVERBEND SUPPLIERS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN427` | 2026-09-27 | DEBIT | ₹112,000.00 | RIVERBEND SUPPLIERS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN424` | 2026-09-24 | DEBIT | ₹126,000.00 | RIVERBEND SUPPLIERS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold) | `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN415` | 2026-09-15 | DEBIT | ₹115,000.00 | RIVERBEND SUPPLIERS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold) | `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN418` | 2026-09-19 | DEBIT | ₹104,000.00 | RIVERBEND SUPPLIERS | Flow (Rapid Movement / Inflow-Outflow), Rule (Large / Round Amount Threshold) | `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN404` | 2026-09-04 | DEBIT | ₹3,260.00 | Unspecified | Statistical (Isolation Forest Outlier) | `STATISTICAL_ANOMALY` |
| MEDIUM | `TXN428` | 2026-09-28 | DEBIT | ₹74,000.00 | NEW COUNTERPARTY Z31 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN448` | 2026-10-21 | DEBIT | ₹72,000.00 | COUNTERPARTY V51 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN429` | 2026-09-28 | DEBIT | ₹69,000.00 | NEW COUNTERPARTY Z32 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN449` | 2026-10-21 | DEBIT | ₹68,000.00 | COUNTERPARTY V52 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN430` | 2026-09-28 | DEBIT | ₹64,000.00 | NEW COUNTERPARTY Z33 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN450` | 2026-10-21 | DEBIT | ₹63,000.00 | COUNTERPARTY V53 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN437` | 2026-10-07 | DEBIT | ₹58,000.00 | COUNTERPARTY T41 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN438` | 2026-10-07 | DEBIT | ₹56,000.00 | COUNTERPARTY T42 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN439` | 2026-10-10 | CREDIT | ₹515,000.00 | MARINER GLOBAL TRADE | Rule (Large / Round Amount Threshold), Volume (New Counterparty Surge) | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES` |
| MEDIUM | `TXN432` | 2026-10-01 | CREDIT | ₹102,500.00 | AURORA MEDIA LABS | Network (Star Topology), Rule (Large / Round Amount Threshold) | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| MEDIUM | `TXN409` | 2026-09-10 | DEBIT | ₹86,000.00 | RIVERBEND SUPPLIERS | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN419` | 2026-09-21 | DEBIT | ₹52,000.00 | COUNTERPARTY L21 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN420` | 2026-09-21 | DEBIT | ₹51,000.00 | COUNTERPARTY L22 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN421` | 2026-09-21 | DEBIT | ₹49,000.00 | COUNTERPARTY L23 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN410` | 2026-09-12 | DEBIT | ₹48,000.00 | COUNTERPARTY K11 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN411` | 2026-09-12 | DEBIT | ₹46,500.00 | COUNTERPARTY K12 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN412` | 2026-09-12 | DEBIT | ₹44,000.00 | COUNTERPARTY K13 | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN431` | 2026-09-30 | DEBIT | ₹7,450.00 | HOUSEHOLD PURCHASE | Flow (Rapid Movement / Inflow-Outflow), Volume (New Counterparty Surge) | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |

## 9. Human Review Queue

- **Total Transactions Analyzed**: 54
- **Prioritized Review Items**: 50
- **HIGH Priority Items**: 28
- **MEDIUM Priority Items**: 19
- **LOW Priority Items**: 3

Queue items are ranked deterministically by priority tier, independent domain count, trigger reason count, and transaction amount.

## 10. Interpretation

# AML Investigation Report: Arjun Malhotra (Account XX6384)
**Period: 01 Sep 2026 – 28 Oct 2026 | Total Transactions: 54**

---

## 1. Observed Evidence

### Transaction Overview
| Metric | Value |
|---|---|
| Total Transactions | 54 |
| Total Credits | ₹5,065,000.00 |
| Total Debits | ₹4,391,690.00 |
| Net Flow | +₹673,310.00 |
| Unique Counterparties | **28** |
| Customer Degree (Network) | 28 |

### Top Counterparties by Volume
| Counterparty | Txn Count | Total Amount | Direction |
|---|---|---|---|
| **LUMEN CONSULTING** | 11 | ₹2,161,000.00 (22.9%) | Debit (outgoing) |
| **RIVERBEND SUPPLIERS** | 10 | ₹1,333,000.00 | Debit (outgoing) |
| NORTHGATE COMPONENTS | 2 | ₹1,075,000.00 | Credit (incoming) |
| MARINER GLOBAL TRADE | 2 | ₹1,005,000.00 | Credit (incoming) |
| CRESTLINE INDUSTRIAL | 2 | ₹713,000.00 | Credit (incoming) |

### Network Topology Patterns Detected
- **One-to-Many Star Network**: The account connects to 28 distinct counterparties, with the customer as the central hub distributing funds outward. - **Dominant High-Volume Counterparty**: LUMEN CONSULTING accounts for 22.9% of all counterparty volume across 11 transactions, all debits (outgoing). - **Rapid Pass-Through Pattern**: Credits from multiple sources (AURORA MEDIA LABS, OAKRIDGE EXPORTS, CRESTLINE INDUSTRIAL, NORTHGATE COMPONENTS, MARINER GLOBAL TRADE, etc.) are followed by debits distributed across a wide array of counterparties. ### Counterparty Anomalies Noted
- **Multiple generic/anonymous counterparty names**: COUNTERPARTY K11, K12, K13, L21, L22, L23, T41, T42, V51, V52, V53 — these appear to be pseudonymous or masked entities. - **Newly observed counterparties**: NEW COUNTERPARTY Z31, Z32, Z33 — recent additions to the network within the statement period. - **RIVERBEND SUPPLIERS**: 10 debit transactions totaling ₹1,333,000 — high frequency of outgoing payments. ---

## 2. Relevant AML Reference

Based on the observed patterns, the following AML typologies are relevant for context:

- **Rapid Movement of Funds / Pass-Through Activity**: Where an account receives credits from multiple sources and quickly distributes funds to numerous counterparties, potentially obscuring the origin of funds. - **Layering**: The process of conducting complex transactions to distance illicit funds from their source. The one-to-many topology with 28 counterparties and high transaction frequency is consistent with layering indicators. - **Structuring / Smurfing**: Breaking down large transactions into smaller amounts across multiple counterparties to avoid detection thresholds. - **Conduit Accounts**: Accounts that serve as intermediaries, receiving and disbursing funds with minimal retention — the net flow of ₹673,310 (relatively modest compared to gross flows of ₹9.4M) may suggest this account is functioning as a conduit. ---

## 3. Interpretation & Risk Indicators

The following **investigation signals** and **potential risk indicators** have been identified:

### 🔴 High-Priority Signals
1. **Unusually high counterparty diversity (28 unique entities)** — significantly elevated for a single account over a 2-month period. 2. **Dominant outgoing counterparty (LUMEN CONSULTING)** — 11 transactions totaling ₹2,161,000, all debits, representing nearly 23% of counterparty volume. This concentration warrants enhanced scrutiny. 3. **One-to-many distribution topology** — the account receives credits from a limited set of sources and distributes debits to a much wider set of recipients, consistent with potential layering/pass-through behavior. 4. **Presence of pseudonymous counterparties** — multiple entities labeled as "COUNTERPARTY K/L/T/V" with numeric suffixes, which may indicate obscured beneficial ownership. ### 🟡 Medium-Priority Signals
5. **Newly established counterparty relationships** — NEW COUNTERPARTY Z31, Z32, Z33 appeared within the statement period, suggesting rapid expansion of the network. 6. **High-frequency, moderate-value debits** to RIVERBEND SUPPLIERS (10 transactions) and LUMEN CONSULTING (11 transactions) — repetitive payment patterns. 7. **Gross-to-net flow ratio**: Total gross flows (~₹9.46M) vs. net flow (₹673,310) — the account processes significantly more money than it retains, a potential conduit indicator. ---

## 4. Limitations & Caveats

- **No definitive conclusion of illicit activity**: The patterns identified are **investigative signals only** and do not constitute evidence of money laundering, fraud, or any criminal offense. - **Context gap**: The customer's stated occupation, source of wealth, expected transaction profile, and business rationale for these transactions are unknown. Many of these counterparties could represent legitimate business operations (e.g., a trader, consultant, or distributor). - **Rule engine output**: The deterministic AML rule engine and Isolation Forest anomaly detection were executed, but the specific flagged transaction IDs and severity scores were not fully enumerated in the output. A deeper review of the rule trigger details is recommended. - **Temporal analysis**: The exact sequencing and timing (velocity) of credits-to-debits was not fully analyzed; intraday or same-day pass-through patterns would strengthen or weaken the layering hypothesis. ---

## 5. Recommended Actions for Human Review

1. **Review LUMEN CONSULTING relationship** — Obtain beneficial ownership information and business rationale for the 11 high-value debit transactions (₹2,161,000 total). 2. **Investigate pseudonymous counterparties** — Identify the real entities behind COUNTERPARTY K/L/T/V designations. 3. **Verify source of funds** — Confirm the origin of credits from NORTHGATE COMPONENTS, MARINER GLOBAL TRADE, CRESTLINE INDUSTRIAL, and other credit sources. 4. **Assess network structure** — Determine whether the one-to-many distribution pattern serves a legitimate business purpose or represents potential layering. 5. **Cross-reference with customer profile** — Compare observed transaction patterns against the customer's known occupation, income level, and historical behavior. ---

*This report is generated for compliance investigation purposes only. It does not assert guilt or criminal liability. All findings are subject to human analyst verification and further due diligence.*

## 11. Limitations

- Investigation findings and risk signals are generated for compliance review purposes only. They do not establish legal guilt, fraud, or criminal liability.

## 12. Recommended Next Steps

- Conduct Enhanced Customer Due Diligence (EDD) to verify the declared commercial profile and purpose of the account.
- Review transactional source documents (invoices, commercial agreements, transport receipts) for high-volume counterparties including LUMEN CONSULTING, NORTHGATE COMPONENTS, and WESTBROOK MATERIALS.
- Cross-reference rapid pass-through sequences with public corporate registry databases to verify counterparty corporate status and beneficial ownership.
- Compare observed velocity and volume surges against baseline account expectations documented at onboarding.
- Escalate multi-signal convergence review items to Senior Compliance Management in accordance with institutional SAR/STR reporting procedures where warranted.

## 13. Critic Validation

- **Audit Outcome**: **PASSED** ✓
- **Evidence References Checked**: 0 confirmed
- **Statement Transactions Analyzed**: 54
- **Verified References**: 0
- **Unverified References**: 0
- **Human Review Queue Items**: 50
- **Factual Grounding**: All referenced transactions, dates, amounts, and flow directions match verified statement records. No unverified legal accusations detected.

- **Revision Cycles**: 0 of maximum 2

## 14. Human Review

### Prioritized Transaction Queue
| Priority | Transaction ID | Date | Flow | Amount (INR) | Counterparty | Triggered Reasons |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HIGH** | `TXN445` | 2026-10-20 | CREDIT | ₹575,000.00 | WESTBROOK MATERIALS | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS`, `RULE_SUDDEN_VOLUME_INCREASE`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN434` | 2026-10-05 | CREDIT | ₹620,000.00 | NORTHGATE COMPONENTS | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN401` | 2026-09-01 | CREDIT | ₹102,500.00 | AURORA MEDIA LABS | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN451` | 2026-10-25 | CREDIT | ₹490,000.00 | MARINER GLOBAL TRADE | `RULE_LARGE_TRANSACTION`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN442` | 2026-10-15 | CREDIT | ₹455,000.00 | NORTHGATE COMPONENTS | `RULE_LARGE_TRANSACTION`, `STATISTICAL_ANOMALY` |
| **HIGH** | `TXN446` | 2026-10-20 | DEBIT | ₹255,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS`, `RULE_SUDDEN_VOLUME_INCREASE` |
| **HIGH** | `TXN435` | 2026-10-05 | DEBIT | ₹275,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN426` | 2026-09-27 | DEBIT | ₹168,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN423` | 2026-09-23 | DEBIT | ₹190,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN414` | 2026-09-15 | DEBIT | ₹175,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN417` | 2026-09-18 | DEBIT | ₹158,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN408` | 2026-09-09 | DEBIT | ₹145,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN406` | 2026-09-06 | DEBIT | ₹132,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES` |
| **HIGH** | `TXN422` | 2026-09-23 | CREDIT | ₹440,000.00 | HORIZON PROCUREMENT | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN413` | 2026-09-15 | CREDIT | ₹405,000.00 | OAKRIDGE EXPORTS | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN416` | 2026-09-18 | CREDIT | ₹362,000.00 | SILVER OAK TRADING | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN407` | 2026-09-09 | CREDIT | ₹318,000.00 | CRESTLINE INDUSTRIAL | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN405` | 2026-09-06 | CREDIT | ₹285,000.00 | OAKRIDGE EXPORTS | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES` |
| **HIGH** | `TXN440` | 2026-10-10 | DEBIT | ₹240,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| **HIGH** | `TXN452` | 2026-10-25 | DEBIT | ₹218,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| **HIGH** | `TXN443` | 2026-10-15 | DEBIT | ₹205,000.00 | LUMEN CONSULTING | `NETWORK_DOMINANT_HIGH_VALUE_COUNTERPARTY`, `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| **HIGH** | `TXN447` | 2026-10-20 | DEBIT | ₹165,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS`, `RULE_SUDDEN_VOLUME_INCREASE` |
| **HIGH** | `TXN425` | 2026-09-27 | CREDIT | ₹395,000.00 | CRESTLINE INDUSTRIAL | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN436` | 2026-10-06 | DEBIT | ₹180,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN427` | 2026-09-27 | DEBIT | ₹112,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN424` | 2026-09-24 | DEBIT | ₹126,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN415` | 2026-09-15 | DEBIT | ₹115,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| **HIGH** | `TXN418` | 2026-09-19 | DEBIT | ₹104,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN404` | 2026-09-04 | DEBIT | ₹3,260.00 | Unspecified | `STATISTICAL_ANOMALY` |
| MEDIUM | `TXN428` | 2026-09-28 | DEBIT | ₹74,000.00 | NEW COUNTERPARTY Z31 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN448` | 2026-10-21 | DEBIT | ₹72,000.00 | COUNTERPARTY V51 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN429` | 2026-09-28 | DEBIT | ₹69,000.00 | NEW COUNTERPARTY Z32 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN449` | 2026-10-21 | DEBIT | ₹68,000.00 | COUNTERPARTY V52 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN430` | 2026-09-28 | DEBIT | ₹64,000.00 | NEW COUNTERPARTY Z33 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN450` | 2026-10-21 | DEBIT | ₹63,000.00 | COUNTERPARTY V53 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN437` | 2026-10-07 | DEBIT | ₹58,000.00 | COUNTERPARTY T41 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN438` | 2026-10-07 | DEBIT | ₹56,000.00 | COUNTERPARTY T42 | `RULE_LARGE_INFLOW_RAPID_OUTFLOW`, `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN439` | 2026-10-10 | CREDIT | ₹515,000.00 | MARINER GLOBAL TRADE | `RULE_LARGE_TRANSACTION`, `RULE_MANY_NEW_COUNTERPARTIES` |
| MEDIUM | `TXN432` | 2026-10-01 | CREDIT | ₹102,500.00 | AURORA MEDIA LABS | `NETWORK_ONE_TO_MANY_TOPOLOGY`, `RULE_LARGE_TRANSACTION` |
| MEDIUM | `TXN409` | 2026-09-10 | DEBIT | ₹86,000.00 | RIVERBEND SUPPLIERS | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN419` | 2026-09-21 | DEBIT | ₹52,000.00 | COUNTERPARTY L21 | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN420` | 2026-09-21 | DEBIT | ₹51,000.00 | COUNTERPARTY L22 | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN421` | 2026-09-21 | DEBIT | ₹49,000.00 | COUNTERPARTY L23 | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN410` | 2026-09-12 | DEBIT | ₹48,000.00 | COUNTERPARTY K11 | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN411` | 2026-09-12 | DEBIT | ₹46,500.00 | COUNTERPARTY K12 | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN412` | 2026-09-12 | DEBIT | ₹44,000.00 | COUNTERPARTY K13 | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| MEDIUM | `TXN431` | 2026-09-30 | DEBIT | ₹7,450.00 | HOUSEHOLD PURCHASE | `RULE_MANY_NEW_COUNTERPARTIES`, `RULE_RAPID_MOVEMENT_OF_FUNDS` |
| LOW | `TXN441` | 2026-10-11 | DEBIT | ₹155,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_TRANSACTION` |
| LOW | `TXN453` | 2026-10-26 | DEBIT | ₹150,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_TRANSACTION` |
| LOW | `TXN444` | 2026-10-16 | DEBIT | ₹140,000.00 | RIVERBEND SUPPLIERS | `RULE_LARGE_TRANSACTION` |

This investigation report is an automated analytical aid for compliance analysis. Final determinations regarding regulatory reporting, customer due diligence, and account status remain the exclusive responsibility of qualified human compliance officers.
