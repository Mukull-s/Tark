import time
from typing import Dict, Any, Optional, List

from src.compass.evoi import EvidenceActionType
from src.graph.scope import GraphScope, GraphScopeStatus, ScopeResponse
from src.graph.connection import get_tigergraph_connection
from src.tools.base import EvidenceTool, ToolExecutionResult
from src.tools.normalizer import EvidenceNormalizer

class BaseGraphEvidenceTool(EvidenceTool):
    """Abstract base for TigerGraph GSQL evidence queries with scope boundary enforcement."""

    @property
    def action_type(self) -> EvidenceActionType:
        return EvidenceActionType.GSQL_QUERY

    def _execute_scoped_query(
        self,
        params: Dict[str, Any],
        target_entity_type: str,
        target_entity_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        ctx = context or {}
        if "tg_conn" in ctx:
            conn = ctx["tg_conn"]
        else:
            conn = get_tigergraph_connection()

        graph_scope = ctx.get("graph_scope")
        if graph_scope is None:
            graph_scope = GraphScope()

        start_time = time.perf_counter()
        
        # Check connection availability
        if conn is None:
            scope_resp = ScopeResponse(
                status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                entity_type=target_entity_type,
                entity_id=target_entity_id,
                query_name=self.tool_name,
                message=f"TigerGraph database connection unavailable for {self.tool_name}."
            )
        else:
            scope_resp = graph_scope.query_with_scope(
                conn=conn,
                query_name=self.tool_name,
                params=params,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        target_entities = {
            target_entity_type.lower(): target_entity_id,
            "flagged_txn_id": str(params.get("t_id", "")),
            "card_id": str(params.get("c_id", "")),
            "customer_id": str(params.get("cust_id", ""))
        }
        
        evidence_item = EvidenceNormalizer.normalize(
            action_id=self.action_id,
            tool_name=self.tool_name,
            scope_status=scope_resp.status,
            raw_data=scope_resp.data,
            target_entities=target_entities,
            context=ctx
        )

        return ToolExecutionResult(
            action_id=self.action_id,
            tool_name=self.tool_name,
            parameters=params,
            status=scope_resp.status.value,
            scope_status=scope_resp.status,
            raw_data=scope_resp.data,
            evidence_item=evidence_item,
            message=scope_resp.message,
            error_details=scope_resp.error_details,
            duration_ms=duration_ms
        )

class DeviceAnalysisTool(BaseGraphEvidenceTool):
    """Tool executing GSQL device_analysis for digital device sharing clusters."""

    @property
    def action_id(self) -> str:
        return "QUERY_DEVICE_ANALYSIS"

    @property
    def tool_name(self) -> str:
        return "device_analysis"

    @property
    def required_parameters(self) -> List[str]:
        return ["t_id"]

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        if not self.validate_parameters(params):
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                message="Missing required parameter 't_id'."
            )
        txn_id = str(params["t_id"])
        return self._execute_scoped_query(
            params={"t_id": txn_id},
            target_entity_type="Transaction",
            target_entity_id=txn_id,
            context=context
        )

class CardSequenceTool(BaseGraphEvidenceTool):
    """Tool executing GSQL card_sequence for micro-authorization testing velocity."""

    @property
    def action_id(self) -> str:
        return "QUERY_CARD_SEQUENCE"

    @property
    def tool_name(self) -> str:
        return "card_sequence"

    @property
    def required_parameters(self) -> List[str]:
        return ["c_id", "anchor_ts"]

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        # Merge context anchor_ts if not in params
        anchor_ts = params.get("anchor_ts") or (context or {}).get("anchor_ts")
        card_id = params.get("c_id")

        if not card_id or not anchor_ts:
            missing = []
            if not card_id:
                missing.append("c_id")
            if not anchor_ts:
                missing.append("anchor_ts")
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                message=f"Missing required parameter(s): {missing}."
            )
        
        card_id = str(card_id)
        anchor_ts = str(anchor_ts)
        window_hours = int(params.get("window_hours", 24))
        
        query_params = {
            "c_id": card_id,
            "anchor_ts": anchor_ts,
            "window_hours": window_hours
        }
        return self._execute_scoped_query(
            params=query_params,
            target_entity_type="Card",
            target_entity_id=card_id,
            context=context
        )

class TxnVelocityTool(BaseGraphEvidenceTool):
    """Tool executing GSQL txn_velocity for 24h transaction volume aggregation."""

    @property
    def action_id(self) -> str:
        return "QUERY_TXN_VELOCITY"

    @property
    def tool_name(self) -> str:
        return "txn_velocity"

    @property
    def required_parameters(self) -> List[str]:
        return ["c_id", "target_ts"]

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        # Merge context target_ts if not in params
        target_ts = params.get("target_ts") or (context or {}).get("target_ts")
        card_id = params.get("c_id")

        if not card_id or not target_ts:
            missing = []
            if not card_id:
                missing.append("c_id")
            if not target_ts:
                missing.append("target_ts")
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                message=f"Missing required parameter(s): {missing}."
            )
        
        card_id = str(card_id)
        target_ts = str(target_ts)
        window_hours = int(params.get("window_hours", 24))
        
        query_params = {
            "c_id": card_id,
            "target_ts": target_ts,
            "window_hours": window_hours
        }
        return self._execute_scoped_query(
            params=query_params,
            target_entity_type="Card",
            target_entity_id=card_id,
            context=context
        )

class RegionAnalysisTool(BaseGraphEvidenceTool):
    """Tool executing GSQL region_analysis for billing location anomalies."""

    @property
    def action_id(self) -> str:
        return "QUERY_REGION_ANALYSIS"

    @property
    def tool_name(self) -> str:
        return "region_analysis"

    @property
    def required_parameters(self) -> List[str]:
        return ["cust_id"]

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        if not self.validate_parameters(params):
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                message="Missing required parameter 'cust_id'."
            )
        cust_id = str(params["cust_id"])
        txn_addr1 = float(params.get("txn_addr1", 0.0))
        
        query_params = {
            "cust_id": cust_id,
            "txn_addr1": txn_addr1
        }
        return self._execute_scoped_query(
            params=query_params,
            target_entity_type="Customer",
            target_entity_id=cust_id,
            context=context
        )

class CustomerProfileTool(BaseGraphEvidenceTool):
    """Tool executing GSQL customer_profile for historical customer baseline."""

    @property
    def action_id(self) -> str:
        return "QUERY_CUSTOMER_PROFILE"

    @property
    def tool_name(self) -> str:
        return "customer_profile"

    @property
    def required_parameters(self) -> List[str]:
        return ["cust_id"]

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        if not self.validate_parameters(params):
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                message="Missing required parameter 'cust_id'."
            )
        cust_id = str(params["cust_id"])
        return self._execute_scoped_query(
            params={"cust_id": cust_id},
            target_entity_type="Customer",
            target_entity_id=cust_id,
            context=context
        )

class SimilarCasesTool(BaseGraphEvidenceTool):
    """Tool executing GSQL similar_cases for historical precedent case retrieval."""

    @property
    def action_id(self) -> str:
        return "QUERY_SIMILAR_CASES"

    @property
    def tool_name(self) -> str:
        return "similar_cases"

    @property
    def required_parameters(self) -> List[str]:
        return ["c_id"]

    def execute(self, params: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ToolExecutionResult:
        if not self.validate_parameters(params):
            return ToolExecutionResult(
                action_id=self.action_id,
                tool_name=self.tool_name,
                parameters=params,
                status="REJECTED",
                scope_status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                message="Missing required parameter 'c_id'."
            )
        card_id = str(params["c_id"])
        target_pattern = str(params.get("target_pattern") or (context or {}).get("pattern", "card_testing"))
        
        query_params = {
            "c_id": card_id,
            "target_pattern": target_pattern
        }
        return self._execute_scoped_query(
            params=query_params,
            target_entity_type="Card",
            target_entity_id=card_id,
            context=context
        )
