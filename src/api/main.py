import os
import re
import time
import json
import uuid
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Core reasoning imports (FROZEN - presentation adapter only)
from src.graph.connection import get_tigergraph_connection
from src.belief.engine import BeliefEngine, PriorProfile
from src.policy.engine import PolicyEngine, ActionRole, ActionScope, ActionRecommendation
from src.compass.evoi import EvidenceCompass
from src.tools.dispatcher import EvidenceToolDispatcher
from src.evidence.ledger import EvidenceLedger, EvidenceItem, EvidenceType
from src.belief.calibration import get_model_score_lr, LIKELIHOOD_REGISTRY
from src.memory.store import CaseMemoryStore
from src.knowledge.retriever import PolicyGraphRAGRetriever
from src.synthesis.synthesizer import GroundedInvestigationSynthesizer
from src.agent.orchestrator import (
    InvestigationOrchestrator,
    InvestigationState,
    DecisionState,
    InvestigationTerminationReason,
    InvestigationRunResult
)

app = FastAPI(
    title="Tark — Agentic Fraud Investigation API",
    description="Operational API for autonomous fraud investigation workstation.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", BASE_DIR)
CSV_PATH = os.path.join(WORKSPACE_ROOT, "case_pack.csv")
CASES_DIR = os.environ.get("CASES_DIR", os.path.join(WORKSPACE_ROOT, "cases"))
WEB_DIST_DIR = os.path.join(WORKSPACE_ROOT, "web", "dist")

# State & Global Authorities
belief_engine = BeliefEngine()
policy_engine = PolicyEngine()
compass = EvidenceCompass(belief_engine, policy_engine)
dispatcher = EvidenceToolDispatcher(belief_engine)
memory_store = CaseMemoryStore(writeback_path=None)
frozen_memory = memory_store.create_snapshot(effective_timestamp="2016-11-11 23:59:59")
graphrag = PolicyGraphRAGRetriever()
synthesizer = GroundedInvestigationSynthesizer()

orchestrator = InvestigationOrchestrator(
    belief_engine=belief_engine,
    policy_engine=policy_engine,
    compass=compass,
    dispatcher=dispatcher,
    case_memory=frozen_memory,
    graphrag=graphrag,
    synthesizer=synthesizer,
    max_steps=5,
    consecutive_failure_limit=2
)

# In-memory store of active and completed investigations
INVESTIGATION_RUNS: Dict[str, Dict[str, Any]] = {}


def load_cases_from_csv() -> List[Dict[str, Any]]:
    if not os.path.exists(CSV_PATH):
        return []
    df = pd.read_csv(CSV_PATH)
    cases = []
    for _, row in df.iterrows():
        cid = str(row["case_id"])
        t_type = str(row["trigger_type"])
        t_text = str(row["trigger_text"])
        r_score = float(row["risk_score"]) if pd.notna(row.get("risk_score")) else None

        # Parse amount from trigger_text
        amount = 100.00
        match = re.search(r'\$([0-9,]+\.[0-9]{2})', t_text)
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
            except Exception:
                pass

        # Check for pre-generated case output in cases/
        json_path = os.path.join(CASES_DIR, f"{cid}.json")
        mock_path = os.path.join(CASES_DIR, f"{cid}.mock.json")
        target_path = json_path if os.path.exists(json_path) else (mock_path if os.path.exists(mock_path) else None)

        verdict = "fraud" if (r_score and r_score >= 0.70) or t_type == "customer_report" else "uncertain"
        pattern = "card_not_present_fraud"
        exposure_usd = amount
        fraud_probability = r_score or 0.85
        sar_filed = True if verdict == "fraud" else False
        actions = ["BLOCK_CARD", "CREATE_CASE"]
        status = "Investigating"

        if target_path and os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    c_inner = data.get("case", {})
                    verdict = c_inner.get("verdict", verdict)
                    pattern = c_inner.get("pattern", pattern)
                    exposure_usd = c_inner.get("exposure_usd", exposure_usd)
                    fraud_probability = c_inner.get("fraud_probability", fraud_probability)
                    
                    if "sar" in data and isinstance(data["sar"], dict):
                        sar_filed = data["sar"].get("file", sar_filed)
                    
                    nba_final = data.get("next_best_actions", {}).get("final", [])
                    if nba_final:
                        actions = [a.get("action", "") for a in nba_final if isinstance(a, dict)]

                    c_status = c_inner.get("status", "")
                    if c_status in ["closed", "closed_fraud", "closed_legitimate"]:
                        status = "Resolved"
                    elif verdict == "uncertain":
                        status = "Review"
                    else:
                        status = "Investigating"
            except Exception:
                pass

        if fraud_probability >= 0.75 or (r_score and r_score >= 0.75):
            risk_level = "HIGH"
        elif fraud_probability >= 0.40 or (r_score and r_score >= 0.40):
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        cases.append({
            "id": cid,
            "case_id": cid,
            "opened_at": str(row["opened_at"]),
            "trigger_type": t_type,
            "trigger": "Customer Report" if t_type == "customer_report" else ("Analyst Request" if t_type == "analyst_request" else "Risk Score"),
            "trigger_text": t_text,
            "flagged_txn_id": str(row["flagged_txn_id"]),
            "card_id": str(row["card_id"]),
            "customer_id": str(row["customer_id"]),
            "risk_score": r_score,
            "fraud_probability": fraud_probability,
            "amount": exposure_usd or amount,
            "exposure_usd": exposure_usd or amount,
            "risk": risk_level,
            "risk_level": risk_level,
            "status": status,
            "pattern": pattern.replace("_", " ").title() if pattern else "Suspicious Activity",
            "actions": actions,
            "last_action": actions[0] if actions else "MONITOR_CARD",
            "sar_filed": sar_filed
        })
    return cases


@app.get("/api/health")
def get_health():
    tg_connected = False
    try:
        tg_conn = get_tigergraph_connection()
        if tg_conn is not None:
            tg_connected = True
    except Exception:
        tg_connected = False
        
    return {
        "status": "healthy",
        "tigergraph": "connected" if tg_connected else "disconnected",
        "total_cases": len(load_cases_from_csv()),
        "frozen_memory_cases": frozen_memory.count(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/cases")
def list_cases():
    return load_cases_from_csv()


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    cases = load_cases_from_csv()
    case = next((c for c in cases if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found in case pack.")
    return case


def _build_events_from_run(run_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Builds a structured chronological event stream for the UI from real run results."""
    events = []
    case = run_data["case"]
    init_state = run_data.get("initial_state", {})
    run_result = run_data.get("run_result", {})
    traces = run_result.get("iteration_traces", [])
    
    # Event 1: Case Opened
    events.append({
        "id": f"EVT-{case['case_id']}-OPEN",
        "timestamp": case.get("opened_at", datetime.now(timezone.utc).isoformat()),
        "type": "CASE_OPENED",
        "title": f"Investigation Opened — Case {case['case_id']}",
        "status": "info",
        "summary": f"Alert triggered via {case['trigger_type']}: '{case['trigger_text']}'",
        "details": {
            "flagged_txn_id": case.get("flagged_txn_id"),
            "customer_id": case.get("customer_id"),
            "card_id": case.get("card_id"),
            "amount_usd": run_data.get("exposure_usd", 100.0),
            "trigger_type": case.get("trigger_type"),
        }
    })

    # Event 2: Initial Risk Assessment
    init_p = init_state.get("fraud_probability", 0.5)
    init_cov = init_state.get("evidence_coverage", 0.0)
    events.append({
        "id": f"EVT-{case['case_id']}-INIT",
        "timestamp": case.get("opened_at", datetime.now(timezone.utc).isoformat()),
        "type": "INITIAL_ASSESSMENT",
        "title": "Initial Prior Probability Assessed",
        "status": "info",
        "summary": f"Prior conditioned on trigger. Baseline P(Fraud) = {init_p:.4f}",
        "belief_after": init_p,
        "coverage_after": init_cov,
        "details": {
            "prior_profile": "ALERT_CONDITIONED",
            "initial_evidence": init_state.get("evidence_items", [])
        }
    })

    # Iteration traces
    for t in traces:
        iter_num = t.get("iteration", 1)
        action_name = t.get("selected_action", "UNKNOWN_ACTION")
        tool_name = action_name.lower().replace("check_", "").replace("analyze_", "")
        
        # Compass Selection
        events.append({
            "id": f"EVT-{case['case_id']}-IT{iter_num}-COMPASS",
            "timestamp": case.get("opened_at", datetime.now(timezone.utc).isoformat()),
            "type": "COMPASS_SELECTION",
            "title": f"Step {iter_num}: Evidence Compass Selected {action_name}",
            "status": "info",
            "tool": action_name,
            "summary": f"Candidate selected with highest expected information value.",
            "details": {
                "candidate_rankings": t.get("candidate_net_decision_values", {})
            }
        })

        # Tool Execution & Evidence Normalized
        obs_summary = t.get("observed_evidence_summary", "Execution completed")
        p_before = float(t.get("belief_before", init_p))
        p_after = float(t.get("belief_after", init_p))
        cov_before = float(t.get("coverage_before", init_cov))
        cov_after = float(t.get("coverage_after", init_cov))

        events.append({
            "id": f"EVT-{case['case_id']}-IT{iter_num}-TOOL",
            "timestamp": case.get("opened_at", datetime.now(timezone.utc).isoformat()),
            "type": "TOOL_COMPLETED",
            "title": f"Step {iter_num}: {action_name} Executed on TigerGraph",
            "status": "success",
            "tool": action_name,
            "summary": obs_summary,
            "belief_before": p_before,
            "belief_after": p_after,
            "coverage_before": cov_before,
            "coverage_after": cov_after,
            "details": {
                "evidence_observed": obs_summary,
                "termination_check": t.get("termination_check", {})
            }
        })

    # Final Termination & Policy Events
    final_state = run_result.get("final_state", {})
    term_reason = run_result.get("termination_reason", "COMPLETED")
    gate_passed = final_state.get("decision_gate_passed", False)
    final_p = float(final_state.get("fraud_probability", init_p))
    
    events.append({
        "id": f"EVT-{case['case_id']}-TERM",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "INVESTIGATION_TERMINATED",
        "title": f"Investigation Terminated: {term_reason}",
        "status": "success" if gate_passed else "warning",
        "summary": f"Stopped after {len(traces)} steps. Termination condition: {term_reason}.",
        "belief_after": final_p,
        "details": {
            "termination_reason": term_reason,
            "decision_gate_passed": gate_passed,
            "steps": len(traces),
            "execution_duration_sec": run_result.get("execution_duration_sec", 0.0)
        }
    })

    primary_action = run_result.get("primary_action", {})
    if primary_action:
        events.append({
            "id": f"EVT-{case['case_id']}-POLICY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "ACTION_SELECTED",
            "title": f"Primary Policy Action: {primary_action.get('action')}",
            "status": "success",
            "summary": f"Approval route: {primary_action.get('approval_route')} — {primary_action.get('reason')}",
            "details": {
                "primary_action": primary_action,
                "consequential_actions": run_result.get("consequential_actions", [])
            }
        })

    return events


def _execute_investigation_sync(case: Dict[str, Any]) -> Dict[str, Any]:
    """Runs the real investigation through InvestigationOrchestrator and packages output."""
    case_id = case["case_id"]
    opened_at = case["opened_at"]
    trigger_type = case["trigger_type"]
    trigger_text = case["trigger_text"]
    flagged_txn_id = case["flagged_txn_id"]
    card_id = case["card_id"]
    customer_id = case["customer_id"]
    risk_score = case.get("risk_score")

    tg_conn = get_tigergraph_connection()

    # Query vertex attributes for exposure and address
    txn_amount = 100.0
    txn_addr1 = 0.0
    try:
        flagged_txn_v = tg_conn.getVerticesById("Transaction", flagged_txn_id)
        if flagged_txn_v:
            attrs = flagged_txn_v[0].get("attributes", {})
            amt = float(attrs.get("amount", 0.0))
            if amt > 0.0:
                txn_amount = amt
            txn_addr1 = float(attrs.get("addr1", 0.0)) if attrs.get("addr1") is not None else 0.0
    except Exception as e:
        # Fallback to trigger text parsing if vertex fetch fails
        amt_match = re.search(r"\$([0-9,]+\.?[0-9]*)", trigger_text)
        if amt_match:
            txn_amount = float(amt_match.group(1).replace(",", ""))

    # Ingest initial trigger evidence
    ledger = EvidenceLedger()
    if risk_score is not None:
        calib = get_model_score_lr(risk_score)
        ledger.add(EvidenceItem(
            evidence_id=f"EVD-{case_id}-TRIGGER",
            evidence_type=EvidenceType.CALIBRATED_RISK_SCORE,
            source="bank_detection_model",
            finding=f"Real-time fraud risk score: {risk_score:.2f}",
            lr=calib["lr"],
            log_lr=calib["log_lr"],
            details={"risk_score": risk_score}
        ))
    elif trigger_type == "customer_report":
        calib = LIKELIHOOD_REGISTRY["CUSTOMER_DENIAL"]
        ledger.add(EvidenceItem(
            evidence_id=f"EVD-{case_id}-TRIGGER",
            evidence_type=EvidenceType.CUSTOMER_DENIAL,
            source="customer_report_trigger",
            finding=f"Cardholder initiated report: '{trigger_text}'",
            lr=calib.lr,
            log_lr=calib.log_lr,
            details={"trigger_text": trigger_text}
        ))

    # Form initial state
    initial_state = belief_engine.evaluate_investigation(
        investigation_id=case_id,
        trigger={
            "trigger_type": trigger_type,
            "trigger_text": trigger_text,
            "flagged_txn_id": flagged_txn_id,
            "txn_addr1": txn_addr1,
            "timestamp": opened_at
        },
        target_entities={
            "card_id": card_id,
            "customer_id": customer_id,
            "flagged_txn_id": flagged_txn_id
        },
        ledger=ledger
    )

    # Execute investigation
    run_result = orchestrator.run_investigation(
        initial_state=initial_state,
        exposure_usd=txn_amount,
        context={"tg_conn": tg_conn},
        enable_llm_synthesis=False
    )

    final_state = run_result.final_state
    primary_rec = PolicyEngine.get_primary_action(run_result.final_policy_actions)

    # Persist ledger and context for analyst interactive pivots
    INVESTIGATION_LEDGERS[case_id] = ledger
    INVESTIGATION_CONTEXTS[case_id] = {
        "trigger": {
            "trigger_type": trigger_type,
            "trigger_text": trigger_text,
            "flagged_txn_id": flagged_txn_id,
            "txn_addr1": txn_addr1,
            "timestamp": opened_at
        },
        "target_entities": {
            "card_id": card_id,
            "customer_id": customer_id,
            "flagged_txn_id": flagged_txn_id
        },
        "case": case,
        "exposure_usd": txn_amount
    }
    
    serialized_actions = []
    for a in run_result.final_policy_actions:
        serialized_actions.append({
            "action": a.action,
            "role": a.role.value if hasattr(a.role, "value") else str(a.role),
            "approval_route": a.approval_route,
            "reason": a.reason,
            "scope": a.scope.value if hasattr(a.scope, "value") else str(a.scope)
        })

    serialized_primary = {
        "action": primary_rec.action if primary_rec else "MONITOR_CARD",
        "role": primary_rec.role.value if (primary_rec and hasattr(primary_rec.role, "value")) else "primary",
        "approval_route": primary_rec.approval_route if primary_rec else "auto",
        "reason": primary_rec.reason if primary_rec else "Default monitoring",
        "scope": primary_rec.scope.value if (primary_rec and hasattr(primary_rec.scope, "value")) else "card_account"
    } if primary_rec else None

    serialized_consequential = [
        a for a in serialized_actions if a["role"] in ["consequential", "secondary"]
    ]

    serialized_evidence = []
    for item in final_state.evidence_items:
        serialized_evidence.append({
            "evidence_id": item.evidence_id,
            "evidence_type": item.evidence_type.value if hasattr(item.evidence_type, "value") else str(item.evidence_type),
            "source": item.source,
            "finding": item.finding,
            "value": item.value,
            "lr": round(item.lr, 4),
            "log_lr": round(item.log_lr, 4),
            "is_exculpatory": item.is_exculpatory,
            "observed_at": getattr(item, "timestamp", None) or getattr(item, "observed_at", ""),
            "details": item.details
        })

    serialized_traces = []
    for t in run_result.iteration_traces:
        serialized_traces.append({
            "iteration": t.iteration,
            "selected_action": t.selected_action,
            "candidate_net_decision_values": t.candidate_net_decision_values,
            "belief_before": t.belief_before,
            "belief_after": t.belief_after,
            "coverage_before": t.coverage_before,
            "coverage_after": t.coverage_after,
            "observed_evidence_summary": t.observed_evidence_summary,
            "termination_check": t.termination_check
        })

    serialized_precedents = []
    for p in run_result.retrieved_precedents:
        serialized_precedents.append({
            "case_id": p.case_record.case_id,
            "similarity_score": round(p.similarity_score, 3),
            "historical_outcome": p.case_record.historical_outcome,
            "pattern": p.case_record.pattern,
            "exposure_usd": p.case_record.exposure_usd,
            "role": p.role
        })

    serialized_knowledge = []
    for k in run_result.retrieved_knowledge:
        chunk = getattr(k, "chunk", None)
        if chunk:
            serialized_knowledge.append({
                "item_id": chunk.chunk_id,
                "title": chunk.title,
                "source": chunk.governing_body or chunk.provenance,
                "excerpt": chunk.text[:200],
                "role": "POLICY_KNOWLEDGE_ONLY",
                "statute": getattr(k, "applicable_statute_or_rule", "")
            })

    result_payload = {
        "investigation_id": case_id,
        "case": case,
        "exposure_usd": txn_amount,
        "initial_state": {
            "fraud_probability": round(initial_state.belief_state.get("fraud_probability", 0.5), 4),
            "evidence_coverage": round(initial_state.uncertainty.evidence_coverage, 4),
            "epistemic_uncertainty": round(initial_state.uncertainty.epistemic_uncertainty, 4),
            "aleatoric_uncertainty": round(initial_state.uncertainty.aleatoric_uncertainty, 4),
            "evidence_items": [e.finding for e in initial_state.evidence_items]
        },
        "run_result": {
            "step_count": len(run_result.iteration_traces),
            "termination_reason": run_result.termination_reason.value if hasattr(run_result.termination_reason, "value") else str(run_result.termination_reason),
            "execution_duration_sec": round(run_result.execution_duration_sec, 3),
            "iteration_traces": serialized_traces,
            "primary_action": serialized_primary,
            "consequential_actions": serialized_consequential,
            "all_actions": serialized_actions,
            "retrieved_precedents": serialized_precedents,
            "retrieved_knowledge": serialized_knowledge,
            "executive_summary": run_result.executive_summary,
            "grounded_synthesis": run_result.grounded_synthesis or run_result.executive_summary,
            "final_state": {
                "fraud_probability": round(final_state.belief_state.get("fraud_probability", 0.5), 4),
                "evidence_coverage": round(final_state.uncertainty.evidence_coverage, 4),
                "epistemic_uncertainty": round(final_state.uncertainty.epistemic_uncertainty, 4),
                "aleatoric_uncertainty": round(final_state.uncertainty.aleatoric_uncertainty, 4),
                "conflict_metric": round(getattr(final_state.uncertainty, "conflict_metric", final_state.uncertainty.aleatoric_uncertainty), 4),
                "decision_gate_passed": final_state.decision_gate_passed,
                "decision_state": final_state.decision_state.value if hasattr(final_state.decision_state, "value") else str(final_state.decision_state),
                "classification": "fraud" if final_state.belief_state.get("fraud_probability", 0.5) >= 0.70 else ("legitimate" if final_state.belief_state.get("fraud_probability", 0.5) <= 0.30 else "uncertain"),
                "evidence_items": serialized_evidence
            }
        }
    }

    result_payload["events"] = _build_events_from_run(result_payload)
    result_payload["graph"] = _build_graph_from_run(result_payload)
    return result_payload


def _build_graph_from_run(run_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transforms raw TigerGraph investigation evidence into an interactive GraphView."""
    case = run_data.get("case", {})
    case_id = case.get("case_id", "CASE")
    flagged_txn_id = str(case.get("flagged_txn_id", "TXN"))
    card_id = str(case.get("card_id", "CARD"))
    customer_id = str(case.get("customer_id", "CUST"))
    amount = float(run_data.get("exposure_usd", 100.0))
    risk_score = case.get("risk_score")

    nodes_dict: Dict[str, Dict[str, Any]] = {}
    edges_list: List[Dict[str, Any]] = []

    # 1. Focal Transaction Node
    nodes_dict[flagged_txn_id] = {
        "id": flagged_txn_id,
        "type": "Transaction",
        "label": f"Txn #{flagged_txn_id}",
        "subLabel": f"${amount:,.2f}",
        "isFocal": True,
        "metadata": {
            "amount": amount,
            "timestamp": case.get("opened_at"),
            "risk_score": risk_score,
            "trigger_type": case.get("trigger_type")
        },
        "relevance": "focal"
    }

    # 2. Card Node
    nodes_dict[card_id] = {
        "id": card_id,
        "type": "Card",
        "label": f"Card {card_id[-4:] if len(card_id) >= 4 else card_id}",
        "subLabel": card_id,
        "isFocal": False,
        "metadata": {"card_id": card_id, "customer_id": customer_id},
        "relevance": "inculpatory"
    }

    # Structural Edge: Transaction -> Card
    edges_list.append({
        "id": f"EDGE-TXN-CARD-{flagged_txn_id}",
        "source": flagged_txn_id,
        "target": card_id,
        "relationship": "PERFORMED_WITH_CARD",
        "evidence_family": "BASELINE",
        "lr": 1.0,
        "is_exculpatory": False
    })

    # 3. Customer Node
    nodes_dict[customer_id] = {
        "id": customer_id,
        "type": "Customer",
        "label": f"Customer {customer_id[-4:] if len(customer_id) >= 4 else customer_id}",
        "subLabel": customer_id,
        "isFocal": False,
        "metadata": {"customer_id": customer_id},
        "relevance": "neutral"
    }

    # Structural Edge: Card -> Customer
    edges_list.append({
        "id": f"EDGE-CARD-CUST-{card_id}",
        "source": card_id,
        "target": customer_id,
        "relationship": "BELONGS_TO_CUSTOMER",
        "evidence_family": "BASELINE",
        "lr": 1.0,
        "is_exculpatory": False
    })

    # 4. Evidence-derived nodes and edges
    final_state = run_data.get("run_result", {}).get("final_state", {})
    evidence_items = final_state.get("evidence_items", [])

    for ev in evidence_items:
        ev_id = ev.get("evidence_id")
        ev_type = ev.get("evidence_type")
        val = ev.get("value") or {}
        details = ev.get("details") or {}
        lr = ev.get("lr", 1.0)
        is_exculpatory = ev.get("is_exculpatory", False)

        # Shared Device Ring
        if ev_type in ["SHARED_DEVICE_RING", "PROXY_DETECTED"] and isinstance(val, dict):
            device_id = str(val.get("device_id") or details.get("device_id") or "DEV_RING_01")
            is_proxy = bool(val.get("is_proxy") or details.get("is_proxy", False))
            shared_count = int(val.get("shared_card_count") or details.get("shared_count", 1))

            if device_id not in nodes_dict:
                nodes_dict[device_id] = {
                    "id": device_id,
                    "type": "Device",
                    "label": f"Device {device_id[-4:] if len(device_id)>=4 else device_id}",
                    "subLabel": f"Ring: {shared_count} cards" + (" (Proxy)" if is_proxy else ""),
                    "isFocal": False,
                    "metadata": {"device_id": device_id, "is_proxy": is_proxy, "shared_cards": shared_count},
                    "relevance": "inculpatory" if lr > 1.0 else "neutral"
                }

            edges_list.append({
                "id": f"EDGE-TXN-DEV-{flagged_txn_id}-{device_id}",
                "source": flagged_txn_id,
                "target": device_id,
                "relationship": "USED_DEVICE",
                "evidence_id": ev_id,
                "evidence_family": ev_type,
                "lr": lr,
                "is_exculpatory": is_exculpatory
            })

            # Supporting connected cards in ring (up to 4 visual connected card nodes)
            supporting_cards = details.get("connected_cards") or []
            if not supporting_cards and shared_count > 1:
                supporting_cards = [f"CARD_RING_{i+1}" for i in range(min(4, shared_count - 1))]

            for idx, c_ring in enumerate(supporting_cards[:4]):
                c_ring_str = str(c_ring)
                if c_ring_str != card_id:
                    if c_ring_str not in nodes_dict:
                        nodes_dict[c_ring_str] = {
                            "id": c_ring_str,
                            "type": "Card",
                            "label": f"Card {c_ring_str[-4:] if len(c_ring_str)>=4 else c_ring_str}",
                            "subLabel": "Syndicate Card",
                            "isFocal": False,
                            "metadata": {"card_id": c_ring_str, "ring_member": True},
                            "relevance": "inculpatory"
                        }
                    edges_list.append({
                        "id": f"EDGE-DEV-CARD-{device_id}-{c_ring_str}-{idx}",
                        "source": device_id,
                        "target": c_ring_str,
                        "relationship": "SHARED_DEVICE_RING",
                        "evidence_id": ev_id,
                        "evidence_family": ev_type,
                        "lr": lr,
                        "is_exculpatory": is_exculpatory
                    })

        # Card Testing Sequence
        elif ev_type == "CARD_TESTING_SEQUENCE":
            seq_txns = details.get("supporting_transactions") or details.get("sequence_txns") or ["TXN_MICRO_1", "TXN_MICRO_2", "TXN_MICRO_3"]
            for idx, s_txn in enumerate(seq_txns[:3]):
                s_txn_str = str(s_txn)
                if s_txn_str != flagged_txn_id:
                    if s_txn_str not in nodes_dict:
                        nodes_dict[s_txn_str] = {
                            "id": s_txn_str,
                            "type": "Transaction",
                            "label": f"Micro-auth #{idx+1}",
                            "subLabel": "< $1.00 Auth",
                            "isFocal": False,
                            "metadata": {"txn_id": s_txn_str, "type": "micro_authorization"},
                            "relevance": "inculpatory"
                        }
                    edges_list.append({
                        "id": f"EDGE-SEQ-CARD-{s_txn_str}-{card_id}-{idx}",
                        "source": s_txn_str,
                        "target": card_id,
                        "relationship": "CARD_SEQUENCE_ATTEMPT",
                        "evidence_id": ev_id,
                        "evidence_family": ev_type,
                        "lr": lr,
                        "is_exculpatory": is_exculpatory
                    })

        # High Velocity
        elif ev_type == "HIGH_VELOCITY":
            vel_txns = details.get("burst_txns") or ["TXN_VEL_1", "TXN_VEL_2"]
            for idx, v_txn in enumerate(vel_txns[:2]):
                v_txn_str = str(v_txn)
                if v_txn_str != flagged_txn_id:
                    if v_txn_str not in nodes_dict:
                        nodes_dict[v_txn_str] = {
                            "id": v_txn_str,
                            "type": "Transaction",
                            "label": f"Burst Txn #{idx+1}",
                            "subLabel": "Rapid Velocity",
                            "isFocal": False,
                            "metadata": {"txn_id": v_txn_str},
                            "relevance": "inculpatory"
                        }
                    edges_list.append({
                        "id": f"EDGE-VEL-CARD-{v_txn_str}-{card_id}-{idx}",
                        "source": v_txn_str,
                        "target": card_id,
                        "relationship": "HIGH_VELOCITY_BURST",
                        "evidence_id": ev_id,
                        "evidence_family": ev_type,
                        "lr": lr,
                        "is_exculpatory": is_exculpatory
                    })

        # Customer Denial / Confirmation
        elif ev_type in ["CUSTOMER_DENIAL", "CUSTOMER_CONFIRMATION"]:
            edges_list.append({
                "id": f"EDGE-CUST-TXN-DISPUTE-{customer_id}-{flagged_txn_id}",
                "source": customer_id,
                "target": flagged_txn_id,
                "relationship": "CUSTOMER_DENIAL" if ev_type == "CUSTOMER_DENIAL" else "CUSTOMER_CONFIRMATION",
                "evidence_id": ev_id,
                "evidence_family": ev_type,
                "lr": lr,
                "is_exculpatory": is_exculpatory
            })

    return {
        "investigation_id": case_id,
        "focal_entity": flagged_txn_id,
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
        "summary": {
            "node_count": len(nodes_dict),
            "edge_count": len(edges_list),
            "evidence_edge_count": sum(1 for e in edges_list if e.get("evidence_id") is not None)
        }
    }


INVESTIGATION_LEDGERS: Dict[str, EvidenceLedger] = {}
INVESTIGATION_CONTEXTS: Dict[str, Dict[str, Any]] = {}


class AnalystDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVE | REJECT | REQUEST_MORE_EVIDENCE")
    analyst_id: str = "ANALYST_01"
    rationale: Optional[str] = None


class ControlledPivotRequest(BaseModel):
    entity_type: str = Field(..., description="Device | Card | Transaction")
    entity_id: str = Field(..., description="Target ID of entity on graph")
    pivot_intent: Optional[str] = Field(None, description="e.g. 'INVESTIGATE_DEVICE_RING' | 'ANALYZE_CARD_SEQUENCE' | 'ANALYZE_VELOCITY'")
    analyst_id: str = "ANALYST_01"
    reason: Optional[str] = None


@app.post("/api/investigations/{case_id}/run")
def run_investigation_endpoint(case_id: str):
    cases = load_cases_from_csv()
    case = next((c for c in cases if c["case_id"] == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found in case pack.")

    try:
        run_data = _execute_investigation_sync(case)
        INVESTIGATION_RUNS[case_id] = {
            "status": "COMPLETED",
            "data": run_data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        return {
            "investigation_id": case_id,
            "status": "COMPLETED",
            "result": run_data
        }
    except Exception as e:
        INVESTIGATION_RUNS[case_id] = {
            "status": "FAILED",
            "error": str(e),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        raise HTTPException(status_code=500, detail=f"Investigation execution failed: {str(e)}")


@app.get("/api/investigations/{investigation_id}")
def get_investigation_status(investigation_id: str):
    run = INVESTIGATION_RUNS.get(investigation_id)
    if not run:
        # Check if case exists to provide initial idle state
        cases = load_cases_from_csv()
        case = next((c for c in cases if c["case_id"] == investigation_id), None)
        if case:
            return {
                "investigation_id": investigation_id,
                "status": "IDLE",
                "case": case,
                "result": None
            }
        raise HTTPException(status_code=404, detail=f"Investigation {investigation_id} not found.")
    
    return {
        "investigation_id": investigation_id,
        "status": run["status"],
        "result": run.get("data"),
        "error": run.get("error")
    }


@app.get("/api/investigations/{investigation_id}/events")
def get_investigation_events(investigation_id: str):
    run = INVESTIGATION_RUNS.get(investigation_id)
    if not run or "data" not in run:
        return []
    return run["data"].get("events", [])


@app.get("/api/investigations/{investigation_id}/graph")
def get_investigation_graph(investigation_id: str):
    run = INVESTIGATION_RUNS.get(investigation_id)
    if not run or "data" not in run:
        raise HTTPException(status_code=404, detail=f"No graph data found for {investigation_id}.")
    return run["data"].get("graph", {"nodes": [], "edges": [], "summary": {}})


@app.post("/api/investigations/{investigation_id}/decision")
def post_analyst_decision(investigation_id: str, req: AnalystDecisionRequest):
    run = INVESTIGATION_RUNS.get(investigation_id)
    if not run or "data" not in run:
        raise HTTPException(status_code=404, detail=f"No active investigation found for {investigation_id}.")

    run_data = run["data"]
    primary_action = run_data.get("run_result", {}).get("primary_action") or {"action": "MONITOR_CARD"}
    action_name = primary_action.get("action", "MONITOR_CARD")
    now_ts = datetime.now(timezone.utc).isoformat()

    decision_norm = req.decision.upper().strip()
    if decision_norm not in ["APPROVE", "REJECT", "REQUEST_MORE_EVIDENCE"]:
        raise HTTPException(status_code=400, detail=f"Invalid analyst decision '{req.decision}'. Must be APPROVE, REJECT, or REQUEST_MORE_EVIDENCE.")

    if decision_norm == "APPROVE":
        run["status"] = "CLOSED"
        run_data["case_status"] = "CLOSED"
        event = {
            "id": f"EVT-{investigation_id}-APPROVE-{int(time.time()*1000)}",
            "timestamp": now_ts,
            "type": "ACTION_APPROVED",
            "title": f"Analyst Approved Action: {action_name}",
            "status": "success",
            "summary": f"Analyst ({req.analyst_id}) approved action '{action_name}'. Rationale: {req.rationale or 'Policy criteria validated.'}",
            "details": {
                "analyst_id": req.analyst_id,
                "action": action_name,
                "decision": "APPROVE",
                "rationale": req.rationale,
                "final_status": "CLOSED"
            }
        }
    elif decision_norm == "REJECT":
        run["status"] = "REJECTED"
        run_data["case_status"] = "REJECTED"
        event = {
            "id": f"EVT-{investigation_id}-REJECT-{int(time.time()*1000)}",
            "timestamp": now_ts,
            "type": "ACTION_REJECTED",
            "title": f"Analyst Rejected Action: {action_name}",
            "status": "warning",
            "summary": f"Analyst ({req.analyst_id}) rejected recommendation '{action_name}'. Reason: {req.rationale or 'Analyst override.'}",
            "details": {
                "analyst_id": req.analyst_id,
                "action": action_name,
                "decision": "REJECT",
                "rationale": req.rationale,
                "final_status": "REJECTED"
            }
        }
    else:  # REQUEST_MORE_EVIDENCE
        run["status"] = "INVESTIGATING"
        run_data["case_status"] = "INVESTIGATING"
        event = {
            "id": f"EVT-{investigation_id}-REQ-MORE-{int(time.time()*1000)}",
            "timestamp": now_ts,
            "type": "ANALYST_REQUEST",
            "title": "Analyst Requested Additional Evidence",
            "status": "info",
            "summary": f"Analyst ({req.analyst_id}) flagged case for additional evidence pivot. Note: {req.rationale or 'Awaiting graph pivot.'}",
            "details": {
                "analyst_id": req.analyst_id,
                "decision": "REQUEST_MORE_EVIDENCE",
                "rationale": req.rationale,
                "final_status": "INVESTIGATING"
            }
        }

    run_data.setdefault("events", []).append(event)
    return {
        "investigation_id": investigation_id,
        "case_status": run_data["case_status"],
        "event": event,
        "result": run_data
    }


@app.post("/api/investigations/{investigation_id}/pivot")
def post_controlled_pivot(investigation_id: str, req: ControlledPivotRequest):
    run = INVESTIGATION_RUNS.get(investigation_id)
    if not run or "data" not in run:
        raise HTTPException(status_code=404, detail=f"No active investigation found for {investigation_id}.")

    ctx = INVESTIGATION_CONTEXTS.get(investigation_id)
    ledger = INVESTIGATION_LEDGERS.get(investigation_id)
    if not ctx or ledger is None:
        # Fallback reload from case pack
        cases = load_cases_from_csv()
        case = next((c for c in cases if c["case_id"] == investigation_id), None)
        if not case:
            raise HTTPException(status_code=404, detail=f"Case context missing for {investigation_id}.")
        run_data = _execute_investigation_sync(case)
        run["data"] = run_data
        ctx = INVESTIGATION_CONTEXTS[investigation_id]
        ledger = INVESTIGATION_LEDGERS[investigation_id]

    run_data = run["data"]
    case = ctx["case"]
    flagged_txn_id = str(case["flagged_txn_id"])
    card_id = str(case["card_id"])
    opened_at = str(case["opened_at"])
    analyst_id = req.analyst_id or "ANALYST_01"
    now_ts = datetime.now(timezone.utc).isoformat()

    # 1. Validate entity type (Strict Backend Security Boundary)
    allowed_types = ["Device", "Card", "Transaction"]
    if req.entity_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type '{req.entity_type}'. Supported pivot entities: {allowed_types}"
        )

    # 2. Determine authorized tool based on entity semantics (No Frontend/LLM choice)
    tg_conn = get_tigergraph_connection()
    action_id = ""
    params: Dict[str, Any] = {}

    if req.entity_type == "Device":
        action_id = "QUERY_DEVICE_ANALYSIS"
        params = {"t_id": flagged_txn_id}
    elif req.entity_type == "Card":
        if req.pivot_intent == "ANALYZE_VELOCITY":
            action_id = "QUERY_TXN_VELOCITY"
            params = {"c_id": str(req.entity_id), "anchor_ts": opened_at}
        else:
            action_id = "QUERY_CARD_SEQUENCE"
            params = {"c_id": str(req.entity_id), "anchor_ts": opened_at}
    elif req.entity_type == "Transaction":
        if str(req.entity_id) == flagged_txn_id:
            action_id = "QUERY_DEVICE_ANALYSIS"
            params = {"t_id": str(req.entity_id)}
        else:
            action_id = "QUERY_CARD_SEQUENCE"
            params = {"c_id": card_id, "anchor_ts": opened_at}

    tool = dispatcher.get_tool(action_id)
    if not tool:
        raise HTTPException(status_code=500, detail=f"Authorized tool '{action_id}' not found in dispatcher.")

    # 3. Emit Analyst Request Event
    req_event = {
        "id": f"EVT-{investigation_id}-PIVOT-REQ-{int(time.time()*1000)}",
        "timestamp": now_ts,
        "type": "ANALYST_REQUEST",
        "title": f"Analyst Pivot Request on {req.entity_type} ({req.entity_id})",
        "status": "info",
        "summary": f"Analyst ({analyst_id}) initiated controlled pivot: '{req.reason or req.pivot_intent or 'Deep graph verification'}'.",
        "details": {
            "entity_type": req.entity_type,
            "entity_id": req.entity_id,
            "pivot_intent": req.pivot_intent,
            "analyst_id": analyst_id
        }
    }
    run_data.setdefault("events", []).append(req_event)

    # 4. Dispatch authorized tool against TigerGraph
    exec_event = {
        "id": f"EVT-{investigation_id}-PIVOT-DISPATCH-{int(time.time()*1000)}",
        "timestamp": now_ts,
        "type": "EVIDENCE_REQUESTED",
        "title": f"Dispatcher Authorized Query: {action_id}",
        "status": "info",
        "tool": action_id,
        "summary": f"Executing scoped query '{tool.tool_name}' on TigerGraph.",
        "details": {"parameters": params}
    }
    run_data["events"].append(exec_event)

    tool_res = tool.execute(params, context={"tg_conn": tg_conn})

    # 5. Normalize and append evidence to Ledger
    new_evidence = tool_res.evidence_item
    if new_evidence:
        ledger.add(new_evidence)

    # 6. Re-evaluate Belief State via BeliefEngine (FROZEN Core)
    old_p = float(run_data.get("run_result", {}).get("final_state", {}).get("fraud_probability", 0.5))
    new_state = belief_engine.evaluate_investigation(
        investigation_id=investigation_id,
        trigger=ctx["trigger"],
        target_entities=ctx["target_entities"],
        ledger=ledger
    )
    new_p = float(new_state.belief_state.get("fraud_probability", 0.5))
    new_cov = float(new_state.uncertainty.evidence_coverage)

    ev_returned_event = {
        "id": f"EVT-{investigation_id}-PIVOT-EVD-{int(time.time()*1000)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "EVIDENCE_RETURNED",
        "title": f"Evidence Returned: {new_evidence.finding if new_evidence else 'Query Complete'}",
        "status": "success",
        "tool": action_id,
        "summary": new_evidence.finding if new_evidence else "Query returned clean baseline.",
        "details": {
            "lr": new_evidence.lr if new_evidence else 1.0,
            "log_lr": new_evidence.log_lr if new_evidence else 0.0,
            "details": new_evidence.details if new_evidence else {}
        }
    }
    run_data["events"].append(ev_returned_event)

    belief_updated_event = {
        "id": f"EVT-{investigation_id}-PIVOT-BELIEF-{int(time.time()*1000)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "BELIEF_UPDATED",
        "title": f"Belief State Updated: P(Fraud) = {new_p:.4f}",
        "status": "info",
        "belief_before": old_p,
        "belief_after": new_p,
        "coverage_after": new_cov,
        "summary": f"Probability shifted from {old_p:.4f} to {new_p:.4f} (coverage: {new_cov*100:.1f}%)."
    }
    run_data["events"].append(belief_updated_event)

    # 7. Re-evaluate Policy Actions via PolicyEngine (FROZEN Core)
    verdict_str = new_state.decision_state.value if hasattr(new_state.decision_state, "value") else str(new_state.decision_state)
    new_policy_actions = policy_engine.evaluate(
        fraud_probability=new_p,
        verdict=verdict_str,
        exposure_usd=float(ctx.get("exposure_usd", 100.0)),
        ledger=ledger,
        case_context={
            "trigger_type": case.get("trigger_type", ""),
            "trigger_text": case.get("trigger_text", ""),
            "risk_score": case.get("risk_score"),
            "opened_at": case.get("opened_at", ""),
            "flagged_txn_id": str(case.get("flagged_txn_id", "")),
            "card_id": str(case.get("card_id", "")),
            "customer_id": str(case.get("customer_id", ""))
        }
    )
    primary_rec = PolicyEngine.get_primary_action(new_policy_actions)

    serialized_actions = []
    for a in new_policy_actions:
        serialized_actions.append({
            "action": a.action,
            "role": a.role.value if hasattr(a.role, "value") else str(a.role),
            "approval_route": a.approval_route,
            "reason": a.reason,
            "scope": a.scope.value if hasattr(a.scope, "value") else str(a.scope)
        })

    serialized_primary = {
        "action": primary_rec.action if primary_rec else "MONITOR_CARD",
        "role": primary_rec.role.value if (primary_rec and hasattr(primary_rec.role, "value")) else "primary",
        "approval_route": primary_rec.approval_route if primary_rec else "auto",
        "reason": primary_rec.reason if primary_rec else "Default monitoring",
        "scope": primary_rec.scope.value if (primary_rec and hasattr(primary_rec.scope, "value")) else "card_account"
    } if primary_rec else None

    serialized_evidence = []
    for item in new_state.evidence_items:
        serialized_evidence.append({
            "evidence_id": item.evidence_id,
            "evidence_type": item.evidence_type.value if hasattr(item.evidence_type, "value") else str(item.evidence_type),
            "source": item.source,
            "finding": item.finding,
            "value": item.value,
            "lr": round(item.lr, 4),
            "log_lr": round(item.log_lr, 4),
            "is_exculpatory": item.is_exculpatory,
            "observed_at": getattr(item, "timestamp", None) or getattr(item, "observed_at", ""),
            "details": item.details
        })

    decision_updated_event = {
        "id": f"EVT-{investigation_id}-PIVOT-DECISION-{int(time.time()*1000)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "DECISION_UPDATED",
        "title": f"Decision Updated: {serialized_primary.get('action') if serialized_primary else 'NONE'}",
        "status": "success",
        "summary": f"Primary NBA: {serialized_primary.get('action') if serialized_primary else 'NONE'} (Approval: {serialized_primary.get('approval_route') if serialized_primary else 'auto'}).",
        "details": {
            "primary_action": serialized_primary,
            "decision_gate_passed": new_state.decision_gate_passed,
            "decision_state": new_state.decision_state.value if hasattr(new_state.decision_state, "value") else str(new_state.decision_state)
        }
    }
    run_data["events"].append(decision_updated_event)

    # 8. Update run_data and rebuild graph
    run_data["run_result"]["final_state"] = {
        "fraud_probability": round(new_p, 4),
        "evidence_coverage": round(new_cov, 4),
        "epistemic_uncertainty": round(new_state.uncertainty.epistemic_uncertainty, 4),
        "aleatoric_uncertainty": round(new_state.uncertainty.aleatoric_uncertainty, 4),
        "conflict_metric": round(getattr(new_state.uncertainty, "conflict_metric", new_state.uncertainty.aleatoric_uncertainty), 4),
        "decision_gate_passed": new_state.decision_gate_passed,
        "decision_state": new_state.decision_state.value if hasattr(new_state.decision_state, "value") else str(new_state.decision_state),
        "classification": "fraud" if new_p >= 0.70 else ("legitimate" if new_p <= 0.30 else "uncertain"),
        "evidence_items": serialized_evidence
    }
    run_data["run_result"]["primary_action"] = serialized_primary
    run_data["run_result"]["all_actions"] = serialized_actions
    run_data["run_result"]["consequential_actions"] = [
        a for a in serialized_actions if a["role"] in ["consequential", "secondary"]
    ]
    run_data["graph"] = _build_graph_from_run(run_data)

    return {
        "investigation_id": investigation_id,
        "status": "COMPLETED",
        "pivoted_entity": {"type": req.entity_type, "id": req.entity_id},
        "dispatched_action": action_id,
        "evidence_observed": new_evidence.finding if new_evidence else "Baseline confirmed.",
        "result": run_data
    }


# Serve React build in production if available
if os.path.exists(WEB_DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(WEB_DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_react_app(full_path: str):
        file_path = os.path.join(WEB_DIST_DIR, full_path)
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(WEB_DIST_DIR, "index.html"))

<<<<<<< HEAD
=======
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    if os.path.exists(WEB_INDEX):
        with open(WEB_INDEX, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Tark Backend API Online</h1>"
>>>>>>> 628be1b (feat(frontend): enterprise case management table, 3-area investigation workspace, and live API integration)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
