# Apex-AML

Query-driven Anti-Money Laundering (AML) compliance engine using dynamic tool orchestration and deterministic routing. Bypasses fixed sequential pipelines to execute only query-relevant detection modules.

## Overview

Traditional AML systems evaluate every query through a rigid pipeline (`EDA -> Preprocessing -> Full Model Inference -> Narrative`). This adds unnecessary latency on simple lookups and inflates false-positive volume, since every query pays the cost of every stage regardless of what it actually asks for.

Apex-AML parses natural language queries into structured parameters (`customer_id`, `date_range_days`, `pattern_type`, `min_transaction_count`, `max_amount`) and compiles a dynamic execution DAG. Tools irrelevant to the query's intent are skipped at runtime, not just at planning time — the skip decision is logged and returned in the response trace so it can be audited after the fact.

## Core Architecture

The system consists of a Pydantic-based state router, five modular detection tools, and a FastAPI server delivering structured compliance trace payloads to a React monitoring terminal.
No LLM is used in the routing, detection, or explanation path. Intent parsing is regex-based against a fixed set of query patterns (structuring, threshold aggregation, entity lookup, global profiling). This is a deliberate reliability choice: the parser has zero external dependencies and zero network calls, so it cannot fail due to an API outage or rate limit during evaluation.

### Tools

| Tool | File | Function |
|---|---|---|
| EDA | `tools/feature_eng.py` (profiling path) | Dataset-wide distribution summary. Runs only on broad/exploratory queries. |
| Feature Engineering | `tools/feature_eng.py` | Rolling 24h sub-$10,000 transaction count/sum, inter-transaction velocity, z-score amount deviation against customer history. |
| Graph Engine | `tools/feature_eng.py` (NetworkX) | Multi-hop layering detection via bounded k-hop ego subgraph around the queried entity. Deliberately not computed on the full transaction graph — global centrality would make single-entity lookups the slowest query type instead of the fastest. |
| Detection (Rules) | `tools/detection.py` | Deterministic threshold check against FinCEN 31 CFR 1010.311 (sub-$10,000 clustering) and layering pattern flags from the graph engine. Primary detection layer. |
| Detection (ML) | `tools/detection.py` | IsolationForest over aggregated per-customer features. Fallback layer, only invoked when query intent requires statistical anomaly detection. Explainability is reported as z-score deviation of the top-2 contributing features against the population mean, not SHAP — IsolationForest + SHAP KernelExplainer was evaluated and rejected during development due to latency and brittleness on this estimator. |
| Risk Classification | `tools/risk.py` | Deterministic tier mapping. Any rule or layering violation forces HIGH/REPORT regardless of ML output — rules take precedence over the ML layer by design, since they are the auditable, statute-cited signal. |
| Explanation | `tools/explain.py` | Templated string assembly from rule/ML/graph output. No LLM involvement in this path — every line traces back to a computed value. |

## Dataset

`data/synthetic_generator.py` produces `data/transactions.csv`: 6,218 transactions (seed=42), spanning June 1 - July 24, 2026, across a normal population plus 15 deliberately planted scenarios:

- Customers 9001-9005: structuring (sub-$10,000 clustering, 10-12 transactions within an 18-24h window)
- Customers 9006-9010: layering (single large inbound transfer split across 6-8 outbound accounts within a tight time window)
- Customers 9011-9015: mixed structuring + layering behavior on the same entity

Ground truth for all 15 scenarios, including expected detection path and expected risk tier, is documented in `data/ground_truth_manifest.json`. This manifest is what the detection layer is validated against — it is not an independent real-world benchmark, and results should be read as "matches a documented synthetic specification," not as a generalization claim.

## Example Queries and Routing Behavior

Verified against the running system (measured, not projected):

| Query | Tools Executed | Tools Skipped |
|---|---|---|
| "Find structuring patterns in the last 30 days" | feature_eng, rules, ml, risk, explain | eda, graph |
| "Which customers made 10+ transactions under $10,000?" | feature_eng, rules, risk, explain | eda, ml, graph |
| "Is customer 9006 suspicious?" | feature_eng, graph, rules, risk, explain | eda, ml |
| "Profile global dataset transaction distribution" | eda | feature_eng, rules, ml, graph, risk, explain |

Each query produces a distinct execution path. This is the core requirement of the problem statement and is enforced structurally by the DAG compiler in `agent/planner.py`, not asserted after the fact.

Measured response times (warm cache, after first request): 250-280ms for rule/graph-based queries, under 2ms for pure EDA profiling. First request in a process incurs a one-time cost (~800-1200ms) for feature computation and IsolationForest fit, which is then cached for the process lifetime.

## Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python data/synthetic_generator.py

python -m uvicorn backend.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend expects the backend at `http://localhost:8000`. Both must be running for the UI to return results.

## API

`POST /api/chat`

Request:
```json
{ "query": "Is customer 9006 suspicious?" }
```

Response: `AgentTrace` object (see `agent/schemas.py`) — includes parsed intent, per-tool execution trace with duration and skip/execute reason, evidence list with statute references and risk tiers, and total response time.

`GET /api/health` — returns loaded customer count, used to confirm the dataset is loaded.

## Known Limitations

- Intent parsing is regex-based only. An LLM-primary parsing layer was scoped but not implemented; `parsed_by` in every response will read `regex_fallback`. The regex parser was prioritized because it has no failure mode dependent on external services, which matters more for a live demo than natural-language flexibility.
- The customer population scanned per query is currently the full dataset (or a date-filtered subset when `date_range_days` is present in the query), not a database-backed filtered query. This is appropriate at the current data scale (6,218 rows) but would need to move to a real datastore with indexed queries beyond a few hundred thousand transactions.
- ML-layer explainability is a statistical deviation summary (z-score against population mean), not a formal SHAP attribution. This was a deliberate scope decision, documented above under Tools.

## Tools, Libraries & AI Assistance Disclosure

- **Core stack:** Python 3.11, FastAPI, Pandas, NumPy, scikit-learn, NetworkX, React, Vite, Tailwind CSS, lucide-react.
- **Agentic orchestration:** Custom Pydantic-based state machine (`agent/planner.py`, `agent/orchestrator.py`). No third-party agent framework (LangChain, CrewAI, AutoGen) is used.
- **LLM usage:** None in the current build. All routing, detection, and explanation logic is deterministic Python.
- **AI coding assistance:** Portions of this codebase were developed with AI-assisted pair programming (Claude). All architectural decisions, threshold tuning, and validation against the ground truth manifest were reviewed and verified manually against real command-line and API output during development.
