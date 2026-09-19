import time
from typing import Dict, Any, Optional, List

from src.compass.evoi import EvidenceActionType
from src.graph.scope import GraphScopeStatus
from src.tools.base import EvidenceTool, ToolExecutionResult
from src.tools.normalizer import EvidenceNormalizer
from src.tools.mock_actions import simulate_customer_reply, simulate_step_up_auth

class CustomerVerificationTool(EvidenceTool):
    """External out-of-band customer SMS/IVR verification challenge tool."""

    @property
    def action_id(self) -> str:
        return "VERIFY_WITH_CUSTOMER"

    @property
    def action_type(self) -> EvidenceActionType:
        return EvidenceActionType.CUSTOMER_INTERACTION

    @property
    def tool_name(self) -> str:
        return "simulate_customer_reply"

    @property
    def required_parameters(self) -> List[str]:
        return []

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        ctx = context or {}
        case_id = params.get("case_id") or ctx.get("case_id") or ctx.get("investigation_id", "UNKNOWN-CASE")
        prompt = params.get("prompt", "Did you authorize this transaction?")
        trigger_type = params.get("trigger_type") or ctx.get("trigger_type", "risk_score")
        fixture_response = params.get("fixture_response") or ctx.get("fixture_response")

        start_time = time.perf_counter()
        raw_result = simulate_customer_reply(
            case_id=case_id,
            prompt=prompt,
            trigger_type=trigger_type,
            fixture_response=fixture_response
        )
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        target_entities = {
            "customer_id": str(params.get("customer_id") or ctx.get("customer_id", "")),
            "flagged_txn_id": str(params.get("flagged_txn_id") or ctx.get("flagged_txn_id", "")),
            "card_id": str(params.get("card_id") or ctx.get("card_id", ""))
        }

        # Status determination
        status_val = raw_result.get("status", "COMPLETED")
        scope_status = GraphScopeStatus.DATA_AVAILABLE if status_val == "COMPLETED" else GraphScopeStatus.NO_MATCH

        evidence_item = EvidenceNormalizer.normalize(
            action_id=self.action_id,
            tool_name=self.tool_name,
            scope_status=scope_status,
            raw_data=raw_result,
            target_entities=target_entities,
            context=ctx
        )

        return ToolExecutionResult(
            action_id=self.action_id,
            tool_name=self.tool_name,
            parameters=params,
            status=status_val,
            scope_status=scope_status,
            raw_data=raw_result,
            evidence_item=evidence_item,
            message=f"Customer verification finished with status {status_val}.",
            duration_ms=duration_ms
        )

class StepUpAuthTool(EvidenceTool):
    """Cryptographic in-flight step-up MFA challenge tool."""

    @property
    def action_id(self) -> str:
        return "STEP_UP_AUTH"

    @property
    def action_type(self) -> EvidenceActionType:
        return EvidenceActionType.STEP_UP_AUTHENTICATION

    @property
    def tool_name(self) -> str:
        return "simulate_step_up_auth"

    @property
    def required_parameters(self) -> List[str]:
        return []

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        ctx = context or {}
        case_id = params.get("case_id") or ctx.get("case_id") or ctx.get("investigation_id", "UNKNOWN-CASE")
        fixture_result = params.get("fixture_result") if "fixture_result" in params else ctx.get("fixture_result")

        start_time = time.perf_counter()
        raw_result = simulate_step_up_auth(
            case_id=case_id,
            fixture_result=fixture_result
        )
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        target_entities = {
            "customer_id": str(params.get("customer_id") or ctx.get("customer_id", "")),
            "flagged_txn_id": str(params.get("flagged_txn_id") or ctx.get("flagged_txn_id", "")),
            "card_id": str(params.get("card_id") or ctx.get("card_id", ""))
        }

        status_val = raw_result.get("status", "COMPLETED")
        scope_status = GraphScopeStatus.DATA_AVAILABLE if status_val == "COMPLETED" else GraphScopeStatus.NO_MATCH

        evidence_item = EvidenceNormalizer.normalize(
            action_id=self.action_id,
            tool_name=self.tool_name,
            scope_status=scope_status,
            raw_data=raw_result,
            target_entities=target_entities,
            context=ctx
        )

        return ToolExecutionResult(
            action_id=self.action_id,
            tool_name=self.tool_name,
            parameters=params,
            status=status_val,
            scope_status=scope_status,
            raw_data=raw_result,
            evidence_item=evidence_item,
            message=f"Step-up MFA authentication finished with status {status_val}.",
            duration_ms=duration_ms
        )
