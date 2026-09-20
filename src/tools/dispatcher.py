import time
import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

from src.evidence.ledger import EvidenceLedger
from src.evidence.types import EvidenceItem
from src.belief.engine import BeliefEngine
from src.belief.calibration import PriorProfile
from src.belief.state import InvestigationState, DecisionState
from src.compass.evoi import CandidateEvidenceEvaluation
from src.graph.scope import GraphScopeStatus
from src.tools.base import EvidenceTool, ToolExecutionResult, EvidenceExecutionTrace
from src.tools.graph_tools import (
    DeviceAnalysisTool,
    CardSequenceTool,
    TxnVelocityTool,
    RegionAnalysisTool,
    CustomerProfileTool,
    SimilarCasesTool
)
from src.tools.external_tools import (
    CustomerVerificationTool,
    StepUpAuthTool
)

logger = logging.getLogger("tark.tools.dispatcher")

class EvidenceToolDispatcher:
    """Deterministic, controlled dispatcher executing approved evidence tools.
    
    Security & Boundary Guarantees:
    - Only explicitly registered EvidenceTools can be dispatched.
    - No dynamic eval(), no arbitrary imports, no shell execution.
    - Idempotency guards prevent duplicate evidence acquisition.
    - Full provenance and state transitions are captured in EvidenceExecutionTrace.
    """

    def __init__(self, belief_engine: Optional[BeliefEngine] = None):
        self.belief_engine = belief_engine or BeliefEngine()
        self._registry: Dict[str, EvidenceTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Registers the canonical Phase 4.2 evidence tool inventory."""
        self.register_tool(DeviceAnalysisTool())
        self.register_tool(CardSequenceTool())
        self.register_tool(TxnVelocityTool())
        self.register_tool(RegionAnalysisTool())
        self.register_tool(CustomerProfileTool())
        self.register_tool(SimilarCasesTool())
        self.register_tool(CustomerVerificationTool())
        self.register_tool(StepUpAuthTool())

    def register_tool(self, tool: EvidenceTool):
        """Registers an evidence tool into the controlled dispatcher."""
        self._registry[tool.action_id] = tool
        self._registry[tool.tool_name] = tool

    def get_tool(self, action_or_tool_name: str) -> Optional[EvidenceTool]:
        """Retrieves a registered tool by action_id or tool_name."""
        return self._registry.get(action_or_tool_name)

    def is_action_already_executed(
        self,
        state: InvestigationState,
        action_id: str,
        params: Dict[str, Any]
    ) -> bool:
        """Determines if the exact evidence action has already been executed in this investigation."""
        tool = self.get_tool(action_id)
        tool_name = tool.tool_name if tool else action_id
        
        for item in state.evidence_items:
            # Check matching query name or source
            if item.graph_query == tool_name or tool_name in str(item.source):
                t_id = params.get("t_id")
                if t_id:
                    if (item.target_entity == str(t_id) or 
                        item.source_entity == str(t_id) or 
                        item.details.get("t_id") == str(t_id) or
                        item.details.get("flagged_txn_id") == str(t_id)):
                        return True
                c_id = params.get("c_id")
                if c_id:
                    if (item.source_entity == str(c_id) or 
                        item.target_entity == str(c_id) or 
                        item.details.get("c_id") == str(c_id)):
                        return True
                cust_id = params.get("cust_id")
                if cust_id:
                    if (item.source_entity == str(cust_id) or 
                        item.target_entity == str(cust_id) or 
                        item.details.get("cust_id") == str(cust_id)):
                        return True
                if not any(k in params for k in ["t_id", "c_id", "cust_id"]):
                    return True
        return False

    def dispatch_and_update(
        self,
        state: InvestigationState,
        candidate_action: Union[CandidateEvidenceEvaluation, Dict[str, Any], str],
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[InvestigationState, ToolExecutionResult, EvidenceExecutionTrace]:
        """Executes one approved candidate evidence action, ingests the resulting EvidenceItem,
        updates the InvestigationState, and returns the updated state with full observability trace.
        """
        start_time_dt = datetime.datetime.now(datetime.timezone.utc)
        start_time_iso = start_time_dt.isoformat()
        start_perf = time.perf_counter()

        # 1. Resolve Action ID and Parameters
        if isinstance(candidate_action, CandidateEvidenceEvaluation):
            action_id = candidate_action.action_id
            tool_name = candidate_action.tool_name
            params = dict(candidate_action.parameters)
        elif isinstance(candidate_action, dict):
            action_id = candidate_action.get("action_id", "")
            tool_name = candidate_action.get("tool_name", action_id)
            params = dict(candidate_action.get("parameters", {}))
        else:
            action_id = str(candidate_action)
            tool = self.get_tool(action_id)
            tool_name = tool.tool_name if tool else action_id
            params = {}

        if parameters:
            params.update(parameters)

        # Merge defaults from state target entities if missing
        if "t_id" not in params and state.trigger.get("flagged_txn_id"):
            params["t_id"] = state.trigger["flagged_txn_id"]
        if "c_id" not in params and state.target_entities.get("card_id"):
            params["c_id"] = state.target_entities["card_id"]
        if "cust_id" not in params and state.target_entities.get("customer_id"):
            params["cust_id"] = state.target_entities["customer_id"]
        if "txn_addr1" not in params and state.trigger.get("txn_addr1"):
            params["txn_addr1"] = state.trigger["txn_addr1"]
        txn_ts = (
            state.trigger.get("timestamp")
            or state.trigger.get("ts")
            or state.target_entities.get("timestamp")
            or state.target_entities.get("ts")
        )
        if "anchor_ts" not in params and txn_ts:
            params["anchor_ts"] = txn_ts
        if "target_ts" not in params and txn_ts:
            params["target_ts"] = txn_ts

        # Baseline metrics before execution
        belief_before = state.belief_state.get("fraud_probability", 0.5)
        coverage_before = state.uncertainty.evidence_coverage
        decision_state_before = state.decision_state.value
        gate_passed_before = state.decision_gate_passed

        ctx = dict(context or {})
        ctx.update({
            "investigation_id": state.investigation_id,
            "trigger": state.trigger,
            "target_entities": state.target_entities,
            "case_id": state.investigation_id,
            "pattern": state.secondary_typology,
            "trigger_type": state.trigger.get("trigger_type", "risk_score")
        })

        # 2. Check Dispatcher Registration
        tool = self.get_tool(action_id)
        if not tool:
            duration_ms = round((time.perf_counter() - start_perf) * 1000, 2)
            end_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            res = ToolExecutionResult(
                action_id=action_id,
                tool_name=tool_name,
                parameters=params,
                status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                message=f"Action '{action_id}' is not a registered approved evidence tool.",
                duration_ms=duration_ms
            )
            trace = EvidenceExecutionTrace(
                investigation_id=state.investigation_id,
                selected_action=action_id,
                tool_name=tool_name,
                parameters=params,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=duration_ms,
                execution_status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE.value,
                belief_before=belief_before,
                belief_after=belief_before,
                coverage_before=coverage_before,
                coverage_after=coverage_before,
                decision_state_before=decision_state_before,
                decision_state_after=decision_state_before,
                gate_passed_before=gate_passed_before,
                gate_passed_after=gate_passed_before,
                message=f"Action '{action_id}' rejected by dispatcher."
            )
            return state, res, trace

        # 3. Idempotency Check: Prevent duplicate execution of already observed action
        if self.is_action_already_executed(state, action_id, params):
            duration_ms = round((time.perf_counter() - start_perf) * 1000, 2)
            end_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            res = ToolExecutionResult(
                action_id=action_id,
                tool_name=tool.tool_name,
                parameters=params,
                status="DUPLICATE",
                scope_status=GraphScopeStatus.DATA_AVAILABLE,
                message=f"Evidence action {action_id} has already been executed for target parameters.",
                duration_ms=duration_ms
            )
            trace = EvidenceExecutionTrace(
                investigation_id=state.investigation_id,
                selected_action=action_id,
                tool_name=tool.tool_name,
                parameters=params,
                start_time=start_time_iso,
                end_time=end_time_iso,
                duration_ms=duration_ms,
                execution_status="DUPLICATE",
                scope_status=GraphScopeStatus.DATA_AVAILABLE.value,
                belief_before=belief_before,
                belief_after=belief_before,
                coverage_before=coverage_before,
                coverage_after=coverage_before,
                decision_state_before=decision_state_before,
                decision_state_after=decision_state_before,
                gate_passed_before=gate_passed_before,
                gate_passed_after=gate_passed_before,
                message=f"Suppressed duplicate execution of {action_id}."
            )
            return state, res, trace

        # 4. Execute Concrete Tool
        execution_res = tool.execute(params=params, context=ctx)
        evidence_item = execution_res.evidence_item

        # 5. Ingest EvidenceItem into Evidence Ledger & Update InvestigationState
        updated_ledger = EvidenceLedger(items=list(state.evidence_items))
        if evidence_item:
            updated_ledger.add(evidence_item)

        prior_p = state.belief_state.get("prior_prob")
        prior_prof = PriorProfile(state.belief_state.get("prior_profile", PriorProfile.ALERT_CONDITIONED.value))

        updated_state = self.belief_engine.evaluate_investigation(
            investigation_id=state.investigation_id,
            trigger=state.trigger,
            target_entities=state.target_entities,
            ledger=updated_ledger,
            prior_profile=prior_prof,
            prior_p=prior_p
        )

        duration_ms = round((time.perf_counter() - start_perf) * 1000, 2)
        end_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 6. Construct Structured Observability Trace
        trace = EvidenceExecutionTrace(
            investigation_id=state.investigation_id,
            selected_action=action_id,
            tool_name=tool.tool_name,
            parameters=params,
            start_time=start_time_iso,
            end_time=end_time_iso,
            duration_ms=duration_ms,
            execution_status=execution_res.status,
            scope_status=execution_res.scope_status.value,
            evidence_id=evidence_item.evidence_id if evidence_item else None,
            resulting_evidence_type=evidence_item.evidence_type.value if evidence_item else None,
            belief_before=belief_before,
            belief_after=updated_state.belief_state.get("fraud_probability", 0.5),
            coverage_before=coverage_before,
            coverage_after=updated_state.uncertainty.evidence_coverage,
            decision_state_before=decision_state_before,
            decision_state_after=updated_state.decision_state.value,
            gate_passed_before=gate_passed_before,
            gate_passed_after=updated_state.decision_gate_passed,
            message=execution_res.message
        )

        return updated_state, execution_res, trace
