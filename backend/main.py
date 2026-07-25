"""
FastAPI entry point. Loads the orchestrator once at startup (data + models
cached in memory for the lifetime of the process), exposes it via /api/chat.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent.orchestrator import ApexOrchestrator

app = FastAPI(title="Apex-AML Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon scope -- lock this down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ApexOrchestrator()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "customers_loaded": int(orchestrator.df_raw["customer_id"].nunique())}


@app.post("/api/chat")
def chat(payload: dict):
    """
    Expects: {"query": "Find structuring patterns in the last 30 days"}
    Returns: AgentTrace as JSON (matches agent/schemas.py contract).
    """
    query = payload.get("query", "").strip()
    if not query:
        return {"error": "query field is required and cannot be empty"}

    trace = orchestrator.run_query(query)
    return trace.model_dump()
