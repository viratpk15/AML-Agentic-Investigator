# AML Investigation Copilot

An educational, production-style Anti-Money Laundering (AML) Investigation Copilot built using modern Python, LangGraph orchestration, transaction analytics, machine learning anomaly detection, and agentic LLM workflows.

---

## 🎯 Architecture & Design Principles

The system processes synthetic bank transaction statements (PDFs), extracts structured transactions, executes analytics and ML-based anomaly detection, and coordinates agentic investigation workflows to generate evidence-backed investigation reports.

### Core Architectural Layers
1. **Services**: PDF/Document parsing & extraction (M2-M3)
2. **Models**: Structured Pydantic schemas & state representation (M3, M10)
3. **ML**: Feature engineering, rule detection, Isolation Forest (M4-M7)
4. **Tools**: Controlled functions exposed to LLM agents (M8)
5. **Agents**: Specialized role-based agents (Profiler, Investigator, Critic) (M9, M12, M14, M15)
6. **RAG**: AML domain knowledge base, embeddings & vector search (M11)
7. **Orchestration**: Multi-agent LangGraph workflow execution (M10)
8. **UI/API**: Gradio & FastAPI human review interface (M17)

---

---

## 📌 Problem: Why AML Investigation is Difficult

Anti-Money Laundering (AML) transaction monitoring and suspicious activity investigations face severe operational bottlenecks:
1. **Severe False-Positive Fatigue**: Legacy rule engines generate overwhelming volumes of alerts (often 90–95%+ false positives), burying genuinely suspicious typologies under routine commercial operations.
2. **Context Fragmentation**: Investigators must manually synthesize transaction ledgers, customer profiles, counterparty relationships, and regulatory typologies across disconnected tools.
3. **Hallucination & Provenance Risks**: Naive LLM adoption in compliance leads to invented transaction IDs, distorted amounts, hallucinated counterparty names, and legally dangerous accusations.
4. **Time & Cost Pressure**: Thorough manual narrative synthesis and transaction-by-transaction verification take hours per case, driving immense compliance backlogs.

---

## 💡 Solution: AI-Assisted Investigation Workflow

The **AML Investigation Copilot** couples deterministic Python verification and unsupervised ML with an agentic LangGraph orchestrator:
* **Strict Evidence Grounding**: The LLM never synthesizes final transaction records; all numbers, dates, counterparties, and anomaly scores flow from an immutable `CanonicalEvidence` contract.
* **Multi-Signal Evidence Convergence**: Prioritizes compliance attention onto transactions exhibiting simultaneous triggers across rule-based screenings, statistical anomaly detection, rapid pass-through velocity, and graph topology anomalies.
* **Adversarial Senior Compliance Critic**: A dedicated LangGraph verification node validates every transaction reference and guardrail, triggering deterministic revisions if any grounding issues arise.
* **Production-Grade Auditability**: Outputs verifiable 14-section investigation dossiers in both Markdown and canonical structured JSON formats with complete provenance chains.

---

## 🏛️ System Architecture

```text
PDF Statement
     │
     ▼
PyMuPDF Text Extractor
     │
     ▼
Transaction Parser & Validator (Pydantic)
     │
     ├──────────────────────────┬──────────────────────────┬──────────────────────────┐
     ▼                          ▼                          ▼                          ▼
Deterministic Rules &      Customer Profiler        NetworkX Directed         AML Knowledge Base
Isolation Forest Outliers   (Turnover / Ratios)      Graph & Topology         (Vector Search / RAG)
     │                          │                          │                          │
     └──────────────────────────┴────────────┬─────────────┴──────────────────────────┘
                                             │
                                             ▼
                             LangGraph Multi-Agent Orchestrator
                             [Investigator ⇄ Tools ⇄ Synthesis]
                                             │
                                             ▼
                             Adversarial Senior Compliance Critic
                               (Deterministic Grounding Verification)
                                             │
                                             ▼
                              Immutable Canonical Evidence Contract
                                             │
                                             ├─────────────────────────────┐
                                             ▼                             ▼
                              Prioritized Human Review Queue     14-Section Report Engine
                                (Top Convergence / Tiers)         (Markdown & Canonical JSON)
```

---

## 🧠 AI Components & Core Technologies

* **Isolation Forest**: Unsupervised tree-based anomaly detection fitted on 12-dimensional transaction feature vectors (amount, temporal velocity, cash flow direction, day-of-week, ratio-to-median) with reproducible seeds.
* **LangGraph Orchestrator**: Cyclic state graph coordinating multi-step investigative reasoning, controlled tool invocation, context budgeting, and termination guards.
* **Retrieval-Augmented Generation (RAG)**: Local vector database housing AML typologies (layering, structuring, round-tripping, conduit accounts) to provide non-accusatory contextual guidance.
* **LLM Provider Abstraction & Failover**: Robust multi-provider failover chain (`Groq` → `OpenRouter` → `Gemini` → `Ollama`) with automatic retryable status handling and context token budgeting.
* **Evidence Grounding**: Formal `CanonicalEvidence` data contracts preventing LLM hallucination of transactions, counterparties, or contiguous ID ranges.
* **Senior Compliance Critic & Revision**: Independent inspection node that mechanically audits LLM narrative drafts against canonical statement ledgers before final sign-off.

---

## 🛡️ Safety & Compliance Boundary

> [!IMPORTANT]
> **Regulatory Notice & Compliance Boundary:**
> The AML Investigation Copilot generates automated **investigative signals, analytical risk indicators, and evidence summaries**. It **does NOT** determine legal guilt, fraud, money laundering, or criminal liability. Final decisions regarding Suspicious Activity Reports (SAR/STR), customer offboarding, and regulatory disclosures remain the exclusive responsibility of qualified human compliance officers.

---

## 🔬 Reproducibility & Environment Setup

### Prerequisites
* **Python**: 3.12 or newer
* **Package Manager**: `uv` (recommended) or `pip`
* **Node.js**: v18+ (for Next.js frontend)

### Environment Variables
Create a `.env` file in the project root:
```env
# LLM Provider Configuration
LLM_PROVIDER="groq"
LLM_FALLBACK_PROVIDERS="openrouter,nvidia"

# Primary LLM Provider (Groq)
GROQ_API_KEY=your_groq_api_key_here

# Fallback LLM Provider 1 (OpenRouter)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Fallback LLM Provider 2 (NVIDIA NIM / build.nvidia.com)
NVIDIA_API_KEY=your_nvidia_api_key_here
NVIDIA_MODEL="meta/llama-3.2-11b-vision-instruct"
NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"

# Application Configuration
AML_ENVIRONMENT=production
AML_CONTEXT_BUDGET=5000
```

### Setup & Installation
```bash
# 1. Clone repository and install Python dependencies
uv sync

# 2. Install Frontend dependencies
cd frontend
npm install
cd ..
```

### Running Tests
Execute the full deterministic regression test suite (270+ passing tests):
```bash
uv run pytest -q
```

### Running the End-to-End Stress Test Demo
Execute the full 54-transaction stress test with real ML, rules, network graph, and report generation:
```bash
uv run python scripts/run_e2e_stress_test.py
```

### Running the Full Interactive Application
```bash
# Terminal 1 — FastAPI Backend (Port 8000)
uv run uvicorn aml_copilot.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Next.js AI Command Center (Port 3000)
cd frontend && npm run dev
```

---

## 🚀 Milestone Progress Tracker

- [x] **M1: Foundation Setup** (Package layout, Pydantic settings, simple logging, pytest)
- [x] **M2: PDF Ingestion** (PyMuPDF document extraction & page mapping)
- [x] **M3: Parsing & Validation** (Regex tokens, date/amount cleaning, Transaction Pydantic models)
- [x] **M4: Analytics** (Deterministic volume, cash flow, counterparty, time gap statistics)
- [x] **M5: Features** (12 deterministic temporal & transactional numerical features)
- [x] **M6: Rules Engine** (Configurable AML screening rules for spikes, velocity, and pass-through)
- [x] **M7: Isolation Forest** (Unsupervised anomaly detection with reproducible seeds & small-sample fallback)
- [x] **M8: Agent Tools** (Modular Pydantic tool layer: analyze, statistics, search, detect)
- [x] **M9: Single Tool Agent** (First tool-using AML investigation agent with inspect-reason-act loop)
- [x] **M10: LangGraph Workflow** (Explicit StateGraph orchestrating Agent, Tools, and Conditional Routing)
- [x] **M11: RAG System** (External AML knowledge retrieval, local vector store, chunking, RAG tool, Agentic routing)
- [x] **M12: Customer Profiling** (Deterministic behavioral profiling, cash flow ratios, turnover indicators)
- [x] **M13: Network Analysis** (NetworkX directed graphs, counterparty metrics, topological flow patterns)
- [x] **M14: Investigation Agent** (Structured evidence gathering, investigation planning, findings synthesis)
- [x] **M15: Critic & Revision Loop** (Skeptical critique node, deterministic Python verification, revision cycles, loop guards)
- [x] **M16: Report Engine** (Deterministic evidence assembly, Markdown & JSON formats, audit trail)
- [x] **M17: AI Command Center & FastAPI** (Next.js 14, R3F 3D Core, React Flow network, telemetry stream, FastAPI backend)
- [x] **M18: Real-Time Investigation Engine** (Server-Sent Events streaming, LangGraph instrumentation, live 3D & topology sync)
- [x] **M19: Productization & Report Integrity** (Report contradiction resolution, Evidence Convergence, UI drawers/modals, history, demo mode)

---

## 🕸️ M10 — LangGraph Orchestration

### Why LangGraph?

In **M9**, the agent loop was manually managed in Python code:

```python
# M9 Manual Approach:
for iteration in range(max_iterations):
    ai_msg = llm_with_tools.invoke(messages)
    if not ai_msg.tool_calls:
        break
    for tool_call in ai_msg.tool_calls:
        execute_tool(...)
```

In **M10**, this manual control flow is replaced by an explicit, auditable **LangGraph StateGraph**:

* **M9**: Python imperatively controls the loop using local variables and `break` statements.
* **M10**: LangGraph represents and controls the workflow explicitly as a declarative state machine.

### Core Concepts

* **State**: The shared execution memory passed from step to step (`InvestigationState` storing dialogue messages, active statement, tool execution records, and iteration counters).
* **Node**: An isolated unit of work:
  * **Agent Node**: Calls the LLM with messages and tools bound, yielding an `AIMessage`. Does *not* execute tools directly.
  * **Tool Node**: Inspects requested `tool_calls`, executes local Python functions via `ToolRegistry`, and emits `ToolMessage` results. Does *not* prompt the LLM.
* **Edge**: A fixed transition between units of work (`START -> agent`, `tools -> agent`).
* **Conditional Edge**: A dynamic routing function (`should_continue`) that inspects the latest message and iteration boundaries to decide where to go next (`tools` vs. `END`).
* **Graph**: The compiled, executable state machine managing the entire lifecycle.

### Workflow Topology

```text
                     START
                       │
                       ▼
                 ┌───────────┐
       ┌────────►│Agent Node │
       │         │   (LLM)   │
       │         └─────┬─────┘
       │               │
       │        should_continue
       │          /         \
  [tool_calls]  YES          NO  [no tool calls OR max iterations]
       │        /             \
       │       ▼               ▼
       │ ┌───────────┐        END
       └─┤ Tool Node │
         └───────────┘
```

---

## 📚 M11 — Agentic RAG (Retrieval-Augmented Generation)

### What is RAG?

$$\text{RAG} = \text{Retrieval-Augmented Generation}$$

```text
Retrieve relevant external knowledge
        ↓
Give it to the LLM
        ↓
LLM generates a grounded response
```

Without RAG, an LLM relies solely on internal parameters or whatever is packed into the system prompt. With RAG, the system dynamically pulls accurate external domain guidance on demand.

### What is an Embedding?

$$\text{Text} \longrightarrow \text{Numerical Vector}$$

An embedding converts words or chunks into a dense array of numbers where semantically similar text produces vectors that lie close to each other in vector space (measured via cosine similarity or dot product).

> **Core Principle**: An embedding converts text into a numerical vector where semantically similar text should have nearby representations.

### What is a Vector Store?

A lightweight storage engine (`LocalVectorStore`) that indexes text chunks alongside their corresponding numerical embedding vectors and performs fast vector similarity searches (such as cosine distance).

### What is Chunking?

Dividing large documents into smaller, meaningful, section-aware excerpts (`DocumentChunk`) while preserving essential provenance metadata:
* `source`: Original file name (e.g. `aml_red_flags.md`)
* `section`: Heading or topic (e.g. `Rapid Movement of Funds`)
* `chunk_index`: Position within the document
* `title`: Document title

### What is a Retriever?

A query interface that takes an investigator's conceptual question, generates a query embedding, queries the vector store, and returns formatted, evidence-backed excerpts with source citations.

```text
User query
    ↓
Similarity search
    ↓
Relevant knowledge chunks
```

### What Makes This "Agentic" RAG?

In standard (static) RAG pipelines, every query unconditionally hits the retriever before calling the LLM:

```text
[Traditional RAG]
Question ──► Retriever ──► Prompt ──► LLM ──► Answer
```

In **Agentic RAG**, retrieval is exposed to the LangGraph agent as a **controlled tool** (`search_aml_knowledge`). The agent reasons about the user's question and decides autonomously whether external guidance is required:

```text
[Agentic RAG in LangGraph]
Question
   ↓
Agent Node
   ↓
"Do I need external AML guidance?"
   /                            \
 YES                             NO
  │                               │
  ▼                               ▼
RAG Tool (`search_aml_knowledge`)  Transaction Tools (`search_transactions`, etc.)
  │                               │
  └───────────────┬───────────────┘
                  ▼
              Agent Node
                  │
                  ▼
          Grounded Response
```

### Factual Evidence vs. Reference Knowledge

A fundamental rule of the AML Copilot architecture is maintaining strict separation between customer facts and external guidance:

```text
TRANSACTION DATA (Customer Specific)          AML KNOWLEDGE BASE (General Reference)
────────────────────────────────────          ───────────────────────────────────────
• "TXN005: ₹480,000 credit from Orion"        • "Conduit accounts pass funds rapidly"
• "TXN006: ₹475,000 debit within 4 hours"     • "Structuring splits amounts below caps"
• Customer balances, dates, counterparties    • CDD, EDD, and source-of-wealth criteria
```

The agent synthesizes these streams using grounded reasoning without ever asserting that reference typologies constitute proof of crime or legal guilt.

---

## 👤 M12 — Customer Profiling

### What is Customer Profiling?

```text
Raw transactions
      ↓
Behavioral statistics
      ↓
Customer Profile
```

While transaction tools answer *"What transactions occurred?"* and detection rules answer *"Which transactions trigger anomaly thresholds?"*, **customer profiling** answers:

> **"What does this customer's overall transaction behavior look like?"**

> ⚠️ **Key AML Principle**: Customer profiling summarizes behavior; it does not determine guilt or compliance status.

### Profiling Components & Metrics

A `CustomerProfile` extracts:
* **Aggregate Volumes**: Total transactions, credits, debits, and net cash flow (e.g. 15 transactions, ₹1.065M credits, ₹1.627M debits).
* **Magnitude Statistics**: Average, median, and maximum transaction amount (e.g. largest single transaction ₹480k).
* **Flow Orientation**: Dominant flow type (`credit`, `debit`, or `balanced`) and credit-to-debit ratio.
* **Counterparty Scope**: Unique counterparties and newly introduced counterparty counts.
* **Temporal Velocity**: Active days, transaction frequency, and daily volume turnover.
* **Factual Behavioral Indicators**:
  * `high_value_activity`: Outsized single-transaction amounts.
  * `high_transaction_volume`: Elevated cumulative turnover across statement duration.
  * `many_counterparties`: Multiple distinct counterparty relationships.
  * `rapid_fund_movement`: Fast turnaround between large incoming credits and outgoing debits.
  * `frequent_new_counterparties`: Frequent first-seen counterparties.

---

## 🕸️ M13 — Network Analysis

### What is Network Analysis?

```text
Transactions
     ↓
Graph (NetworkX)
     ↓
Customer ↔ Counterparties
     ↓
Network metrics
     ↓
Relationship insights
```

Network analysis moves beyond isolated individual transactions to examine **relationships and directional fund flows** across the customer's entire transactional ecosystem.

### Graph Terminology

* **Node**: An entity in the financial network (the primary `Customer` or a third-party `Counterparty`).
* **Edge**: A directed relationship established by transaction fund flow (e.g. `ORION TRADING ──₹480k──► Customer`).
* **Degree**: The total number of unique entity connections linked to a node.
  * `in_degree`: Number of counterparties sending funds into the customer.
  * `out_degree`: Number of counterparties receiving disbursements from the customer.
* **Network Analysis**: Evaluates topological patterns, degree centrality, flow directionality, and intermediary conduit roles rather than treating each transaction in isolation.

### Observable Network Patterns

1. **One-to-Many Star Topology**: The customer distributes or gathers funds across a wide array of counterparties.
2. **Dominant High-Value Counterparty**: A single entity accounts for a disproportionate share (e.g. >30%) of overall counterparty volume.
3. **Rapid Flow Between Counterparties (Conduit Relationship)**: Funds received from Counterparty A (e.g. `ORION TRADING`, TXN005) are swiftly disbursed to Counterparty B (e.g. `RAHUL SERVICES`, TXN006).

---

## 🔍 M14 — Investigation Agent

The Investigation Agent converts raw tool interactions into a structured, evidence-grounded investigative process.

```text
Tool-Using Agent ──► Evidence Gathering ──► Investigation Synthesis
```

### Core Architectural Separation

* **Agent**: Gathers and interprets evidence, chooses relevant tools dynamically based on the investigation query, and synthesizes findings into a coherent draft.
* **Tool**: Executes deterministic Python functions (analytics, rules, Isolation Forest, profiling, network analysis, RAG retrieval) and returns structured JSON outputs.
* **State**: The shared, auditable investigation memory (`InvestigationState`) carrying the question, message history, tool execution records, structured findings, draft artifacts, critic feedback, and iteration counters.

### Investigation Synthesis & Findings Model

Rather than producing a single untyped blob of markdown, the synthesis stage extracts structured Pydantic models:
* `EvidenceReference`: Concrete pointer to supporting evidence (transaction IDs, source type, numerical details).
* `InvestigationFinding`: Factual finding with associated evidence references, source type, and confidence score.
* `InvestigationDraft`: Structured artifact categorizing **Observed Evidence** (facts from the statement), **Analytical Findings** (rule/model signals), **Network Findings** (counterparty topology), **Reference Context** (educational AML typologies), and **Interpretation**.

---

## ⚖️ M15 — Critic & Revision Loop

The Critic & Revision Loop introduces an adversarial verification layer that protects against common LLM failure modes before an investigation result is finalized.

```text
       Draft
         │
         ▼
       Critic
      /      \
   PASS      FAIL
    │          │
    ▼          ▼
  Final    Revision
  (END)        │
               ▼
          Agent / Tools
               │
               ▼
             Draft
               │
               ▼
             Critic
```

### Why Do We Need a Critic?

LLMs acting alone frequently suffer from:
1. **Hallucinated or unsupported claims** (asserting patterns without underlying transactions).
2. **Missing required evidence** (failing to inspect transactions specifically queried by the human analyst).
3. **Incorrect factual identifiers** (citing non-existent transaction IDs or mismatched amounts/dates).
4. **Overconfident or prohibited conclusions** (declaring legal guilt, criminal fraud, or issuing autonomous account closure orders).

The Critic acts as a skeptical auditor with a dedicated prompt and strict verification criteria.

### Deterministic Python Validation vs. LLM Critic

$$\text{Critic} \neq \text{Proof}$$

To prevent LLM hallucination in the verification layer itself, factual verification is handled **deterministically in Python**:

| Validation Dimension | Mechanism | Rule |
| :--- | :--- | :--- |
| **Transaction ID Existence** | Python regex & set lookup | Every cited `TXN\d+` must exist in `statement.transactions`. |
| **Amount Reconciliation** | Python parsing & numeric check | Cited amount must match transaction credit, debit, or balance. |
| **Date Consistency** | Python string comparison | Cited dates must match the transaction's recorded statement date. |
| **AML Safety Boundaries** | Regex pattern matching | Prohibits declarations of guilt, crime, money laundering, or orders to close accounts / file SARs. |
| **Missing Evidence** | Python query inspection | Question-specific transaction inquiries must be analyzed in the draft. |
| **Reasoning Quality** | Critic LLM Review | Assesses logical soundness and clarity of interpretation. |

### Revision Loop & Loop Guards

When the Critic issues a `FAIL`, it emits a structured `CritiqueResult` detailing specific issues, missing evidence, and required revisions. The `revision` node injects this structured feedback as a high-priority prompt, allowing the Investigator to gather additional evidence or correct inaccurate claims.

To eliminate the risk of infinite loops, the workflow enforces a strict `max_revisions` ceiling (default: `2`). If unresolved issues persist after reaching the revision limit, the graph safely routes to `END` and appends an explicit limitation warning to the final audit record.

---

## 🔄 Major Agentic Pattern

Milestones M14 and M15 demonstrate an end-to-end, multi-role Agentic AI pattern:

```text
REASON ──► ACT ──► OBSERVE ──► SYNTHESIZE ──► CRITIQUE ──► REVISE ──► FINALIZE
```

This pattern moves far beyond simple "Prompt → Answer" completion, creating a **stateful, self-correcting workflow** with verifiable evidence grounding and strict safety guardrails.

---

## 📑 M16 — Investigation Report Engine

The Investigation Report Engine converts the verified final investigation state into a deterministic, professional compliance report.

```text
Verified State ──► Report Generator ──► Structured Report (Pydantic) ──► Markdown / JSON
```

### Deterministic Traceability Guarantees

1. **Zero Hallucinated Evidence**: Transaction amounts, dates, and counterparties in the report are pulled strictly from the verified `statement.transactions`.
2. **Deterministic Computations**: Numerical metrics (turnover, credit/debit totals, ratios, counterparty counts) are computed by deterministic Python services, never by the LLM.
3. **Audit Visibility**: Critic audit status (`PASS`/`FAIL`), checked IDs, invalid IDs, safety constraints, and revision counts are permanently recorded in the report model.
4. **Mandatory Human Review Banner**: Explicitly labels the report as an analytical aid and preserves non-accusatory compliance boundaries.

### Standardized 10-Section Compliance Structure

The engine generates Markdown following standard banking compliance audit layouts:
1. **Investigation Question**
2. **Executive Summary**
3. **1. Observed Evidence** (Detailed ledger table with verification status)
4. **2. Detection Findings** (Deterministic rule signals & Isolation Forest anomaly context)
5. **3. Customer Profile** (Turnover, active days, cash flow direction, behavioral indicators)
6. **4. Transaction Network** (Counterparty relationships and topological flow patterns)
7. **5. AML Knowledge Context** (Retrieved typologies from regulatory guidance)
8. **6. Interpretation** (Objective synthesis connecting evidence to typologies)
9. **7. Critic Validation** (Adversarial verification status and checked IDs)
10. **8. Revision History** (Self-correction cycles and loop guard records)
11. **9. Limitations** (Data boundaries, sample size warnings, disclaimers)
12. **10. Human Review** (Exclusive responsibility of qualified human compliance officers)

---

## 🛰️ M17 — Futuristic AI Investigation Command Center & FastAPI

M17 implements a production-grade **AI Financial Intelligence Command Center** designed for portfolio presentation, research review, and live demonstration.

```text
┌───────────────────────────────────────────────┐
│        Next.js 14 Web Command Center          │
│   (3D Core + React Flow + Live Telemetry)     │
└───────────────────────┬───────────────────────┘
                        │ HTTP / JSON
                        ▼
┌───────────────────────────────────────────────┐
│              FastAPI REST Backend             │
│   (/health, /investigate [Multipart], /demo)  │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│      LangGraph Multi-Role Orchestrator        │
│  (Investigator ↔ Tools ↔ Critic ↔ Revision)   │
└───────────────────────────────────────────────┘
```

### Hero Features

1. **3D AI Investigation Core** (`React Three Fiber` / `Three.js`):
   - Glowing central nucleus with outer wireframe shell, multi-axis orbital rings, and dynamic particle cloud.
   - Responds visually to orchestrator states: `IDLE` (breathing cyan), `ANALYZING` (rapid pulse), `TOOL_EXECUTION` (amber orbit), `RAG_RETRIEVAL` (blue stream), `CRITIC`/`REVISION` (purple radar scan), `COMPLETE` (emerald glow).
2. **Live LangGraph Topology Visualizer** (`Framer Motion`):
   - Interactive representation of the state machine: `Investigator Node` $\rightarrow$ `Tool Node` $\rightarrow$ `Synthesis Node` $\rightarrow$ `Critic Node` $\rightarrow$ `Revision Node` $\rightarrow$ `Final Report`.
   - Real-time active node pulses, progress tracking, and self-correction feedback loop indicators.
3. **Interactive Directed Transaction Network** (`React Flow` / `@xyflow/react`):
   - Node-link graph mapping central Customer to incoming remitters (cyan) and outgoing beneficiaries (purple).
   - Animated directed transaction edges with formatted monetary flows (e.g. `₹480K`).
   - Clickable node drawer displaying entity volumes, roles, and associated transaction IDs.
4. **Detection & Outliers Visualization**:
   - Visual cards for rule signals (`RULE_LARGE_TRANSACTION`, `RULE_RAPID_MOVEMENT_OF_FUNDS`) with severity badges and transaction tags.
   - Statistical anomaly cards with Isolation Forest decision scores and feature contributions.
   - Distinct disclaimer separating statistical anomaly from criminal guilt.
5. **Customer Behavioral Profile Hub**:
   - Animated KPI cards for Total Turnover, Net Cash Flow, Active Days, Unique Counterparties, and Peak Inflows/Outflows.
   - Factual behavioral classification indicators.
6. **AML Knowledge RAG Explorer**:
   - Cards showing retrieved guidance documents (`aml_red_flags.md`, `aml_transaction_monitoring.md`) and contextual excerpts.
7. **Adversarial Critic & Audit Panel**:
   - Real-time verification checklist: Transaction ID Existence, Amount Reconciliation, Date Matching, Safety Boundary Review.
   - Revision counter (`1/2 Revisions Applied`) and self-correction narrative.
8. **Report View with Dual Export**:
   - Complete rendered compliance report with one-click **"Export Markdown"** and **"Export JSON"** buttons.
9. **Live Telemetry Stream**:
   - Terminal-style real-time event feed logging orchestrator timestamps, tool invocations, and critic verdicts.
10. **Zero-Latency Demo Mode**:
    - Header toggle switch enabling instant presentation on synthetic customer data (`Arjun Mehta`, 15 transactions) with no live API key required.

---

## ⚡ Running the System

### 1. Launch FastAPI Backend

```bash
# In project root:
uv run uvicorn aml_copilot.api.main:app --host 0.0.0.0 --port 8000 --reload
```

* API Docs (Swagger): `http://localhost:8000/docs`
* Health Check: `http://localhost:8000/health`
* Demo Endpoint: `http://localhost:8000/demo`

### 2. Launch Next.js Command Center

```bash
# In frontend directory:
cd frontend
npm run dev
```

* Open: `http://localhost:3000`

---

## ⚡ M18 — Real-Time Investigation Engine & Live Command Center

M18 replaces simulated client-side state progression with an **event-driven Server-Sent Events (SSE) streaming architecture** directly instrumented into the LangGraph execution lifecycle.

### Architecture Overview

```text
               User clicks "START INVESTIGATION"
                             │
                             ▼
                 POST /investigations
             (Immediate Acknowledgment 200)
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
   Background Worker Task         GET /investigations/{id}/events
 (LangGraph + Critic Loop)             (Server-Sent Events)
              │                             │
              ▼                             ▼
    Real Lifecycle Events         Real-Time Telemetry Stream
              │                             │
              └──────────────►──────────────┘
                             │
                             ▼
      Next.js AI Financial Intelligence Command Center
 ├── 3D AI Investigation Nucleus (State-Reactive Three.js)
 ├── LangGraph Visualizer (Node-Pulsing & Revision Loop)
 ├── Live Telemetry Terminal (Chronological Execution Log)
 └── Adversarial Critic Audit (Factual Verification Checklist)
```

### Event Taxonomy (`EventType`)

Every major stage of the agentic investigation emits a strongly typed `InvestigationEvent` with timestamps, node identifiers, iteration/revision counts, and structured metadata:

| Event Type | Emitting Node | Description |
| :--- | :--- | :--- |
| `INVESTIGATION_STARTED` | Graph Entry | Background worker starts processing statement. |
| `NODE_STARTED` | Investigator | Agent begins reasoning cycle and evaluating plan. |
| `NODE_COMPLETED` | Investigator | Agent concludes reasoning or requests tool executions. |
| `TOOL_STARTED` | Tools | Specific deterministic tool invoked (e.g. `detect_anomalies`). |
| `TOOL_COMPLETED` | Tools | Tool finishes and returns verified ledger data. |
| `RAG_STARTED` | Tools / RAG | Knowledge retrieval initiated from vector base. |
| `RAG_COMPLETED` | Tools / RAG | Typology documents retrieved and cited. |
| `SYNTHESIS_STARTED` | Synthesis | Evidence structuring into an investigation draft. |
| `SYNTHESIS_COMPLETED` | Synthesis | Draft completed with verified finding records. |
| `CRITIC_STARTED` | Critic | Adversarial audit begins evaluating claims & IDs. |
| `CRITIC_PASSED` | Critic | Audit succeeded: 100% evidence verified in ledger. |
| `CRITIC_FAILED` | Critic | Audit rejected draft; emits specific issues in metadata. |
| `REVISION_STARTED` | Revision | Self-correction loop triggers revision cycle. |
| `REVISION_COMPLETED` | Revision | Corrective feedback dispatched back to Investigator. |
| `REPORT_GENERATED` | Reporting | Structured Pydantic & Markdown reports compiled. |
| `INVESTIGATION_COMPLETED` | Graph Exit | Investigation concludes; client retrieves report. |
| `INVESTIGATION_FAILED` | Error Handler | Execution failure caught safely without leaks. |

### Per-Investigation Event Bus (`InvestigationEventBus`)

To ensure concurrent safety and avoid shared global state:
- Each investigation is assigned a dedicated `InvestigationEventBus` keyed by `investigation_id`.
- The bus retains a historical replay buffer: if a client reconnects or experiences latency, prior events are replayed in chronological order before live events stream.
- Event broadcasting is thread-safe (`loop.call_soon_threadsafe`), allowing synchronous LangGraph nodes to run in worker threads while FastAPI streams asynchronously over HTTP.

### Real-Time API Endpoints

1. **`POST /investigations`**
   - Ingests multipart form: `file` (.pdf) and `question` (string).
   - Generates unique tracking ID (e.g. `INV-A1B2C3D4`).
   - Immediately returns:
     ```json
     {
       "investigation_id": "INV-A1B2C3D4",
       "status": "QUEUED",
       "message": "Investigation registered and queued for execution."
     }
     ```
2. **`POST /investigations/demo`**
   - Triggers the synthetic demonstration statement (`suspicious_statement.pdf`) through the real event stream without requiring external API keys.
3. **`GET /investigations/{id}/events`**
   - Server-Sent Events endpoint streaming structured JSON chunks:
     ```http
     event: investigation_event
     data: {"event_id":"evt_123","investigation_id":"INV-A1B2C3D4","event_type":"NODE_STARTED","node":"investigator","message":"Investigator evaluating transaction evidence...","timestamp":"2026-09-25T09:30:00Z","metadata":{}}
     ```
4. **`GET /investigations/{id}`**
   - Queries current status (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`), latest event, elapsed execution time, and completed `report` and `markdown`.

### UI Integration

- **3D AI Core (`InvestigationCore3D.tsx`)**: Directly responds to engine states (`ANALYZING` cyan glow, `TOOL_EXECUTION` amber speed-up, `RAG_RETRIEVAL` blue aura, `CRITIC` purple scan, `REVISION` pulse, `COMPLETE` emerald radiance).
- **Topology Visualizer (`LangGraphVisualizer.tsx`)**: Lights up whichever node is executing in real time and animates the feedback loop on revision.
- **Telemetry Console (`TelemetryStream.tsx`)**: Auto-scrolls real backend events as they fire with zero simulated timers.

---

## 🤖 Agentic Architecture

The system bridges deterministic statistical detection with agentic LLM reasoning.

### Mental Model

$$\text{Agent} = \text{LLM} + \text{Tools} + \text{Decision Loop}$$

- **Tools**: Deterministic, typed interfaces wrapping underlying analytics, search, rules, machine learning, customer profiling, and NetworkX network pipelines.
- **LLM**: The reasoning engine that interprets the investigator's question, plans tool usage, and synthesizes findings into professional compliance narratives.
- **Decision Loop**: The inspect-reason-act cycle where the model chooses a tool, receives structured tool output, evaluates the evidence, and decides whether to query further or conclude its investigation.

### Tool-Calling Loop

```text
User Investigation Question
            ↓
      LLM Reasoning
            ↓
      Decide Tool Call
            ↓
  ┌─────────────────────────────┐
  │ analyze_transactions        │ → Behavioral volume, cash flow, time gaps
  │ get_transaction_statistics  │ → Concise summaries, credit/debit aggregates
  │ search_transactions         │ → Exact filtering by counterparty, amount, date
  │ detect_anomalies            │ → Rule screening & Isolation Forest outliers
  │ get_customer_profile        │ → Holistic behavioral baseline, turnover, indicators
  │ analyze_transaction_network │ → NetworkX graph, counterparty topology, flow paths
  │ search_aml_knowledge        │ → External AML regulatory typologies and guidance
  └─────────────────────────────┘
            ↓
     Structured Output
            ↓
      LLM Synthesizes
            ↓
Investigation Response (Citing verified Transaction IDs & Evidence)
```

---

## 🛠️ Setup & Local Development

### Prerequisites
- Python 3.12+
- `uv` package manager

### Environment Setup
```bash
# Clone repository
git clone <repo-url>
cd AML_agent_orc

# Create virtualenv and sync dependencies
uv sync

# Copy example environment settings
cp .env.example .env
```

### LLM Provider Configuration

The AML Investigation Copilot supports both **Groq** and **OpenAI** as LLM reasoning providers via standard environment variables in `.env`.

> 🔒 **Security Notice**: Never commit API keys or push `.env` to source control. `.env` is permanently gitignored.

#### Option A: Groq (Recommended for Ultra-Fast Inference)

Configure `.env` with:
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.0
LLM_MAX_ITERATIONS=5
```

Recommended Groq models:
- `llama-3.3-70b-versatile` (Default recommended for complex compliance reasoning)
- `llama-3.1-8b-instant` (Fast lightweight alternative)

#### Option B: OpenAI

Configure `.env` with:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.0
LLM_MAX_ITERATIONS=5
```

Recommended OpenAI models:
- `gpt-4o-mini` (Fast and cost-effective)
- `gpt-4o` (Comprehensive reasoning)

#### Zero-API-Key Demo Mode

You can explore and demonstrate the system without any LLM API key by utilizing the built-in synthetic demonstration mode via the web UI or `/demo` / `POST /investigations/demo` endpoints.

### Running Tests
```bash
uv run pytest
```
