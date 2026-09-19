import uuid
import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.evidence.types import EvidenceItem, EvidenceType
from src.compass.evoi import EvidenceActionType
from src.graph.scope import GraphScopeStatus

class ToolExecutionResult(BaseModel):
    """Structured, immutable output of executing an approved evidence tool."""
    execution_id: str = Field(default_factory=lambda: f"EXEC-{uuid.uuid4().hex[:8].upper()}")
    action_id: str
    tool_name: str
    parameters: Dict[str, Any]
    
    # Status & Scope
    status: str = Field(description="SUCCESS, FAILURE, OUT_OF_SCOPE, NO_MATCH, DUPLICATE, REJECTED")
    scope_status: GraphScopeStatus
    raw_data: Any = None
    
    # Output Evidence
    evidence_item: Optional[EvidenceItem] = None
    
    # Execution Metadata
    message: str = ""
    error_details: Optional[str] = None
    execution_timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    duration_ms: float = 0.0

class EvidenceExecutionTrace(BaseModel):
    """Observability trace capturing the complete state transition for an executed evidence action."""
    trace_id: str = Field(default_factory=lambda: f"TRC-{uuid.uuid4().hex[:8].upper()}")
    investigation_id: str
    selected_action: str
    tool_name: str
    parameters: Dict[str, Any]
    
    start_time: str
    end_time: str
    duration_ms: float
    
    execution_status: str
    scope_status: str
    evidence_id: Optional[str] = None
    resulting_evidence_type: Optional[str] = None
    
    # State delta metrics
    belief_before: float
    belief_after: float
    coverage_before: float
    coverage_after: float
    decision_state_before: str
    decision_state_after: str
    gate_passed_before: bool
    gate_passed_after: bool
    
    message: str

class EvidenceTool(ABC):
    """Canonical interface for an approved Tark evidence collection tool."""

    @property
    @abstractmethod
    def action_id(self) -> str:
        """Unique identifier matching CandidateEvidenceEvaluation.action_id."""
        pass

    @property
    @abstractmethod
    def action_type(self) -> EvidenceActionType:
        """Action classification: GSQL_QUERY, CUSTOMER_INTERACTION, etc."""
        pass

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Physical query or function name."""
        pass

    @property
    @abstractmethod
    def required_parameters(self) -> List[str]:
        """List of required parameter keys."""
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validates that all required parameters are provided and non-empty."""
        for req in self.required_parameters:
            if req not in params or params[req] is None or params[req] == "":
                return False
        return True

    @abstractmethod
    def execute(
        self,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecutionResult:
        """Executes the tool and returns a structured ToolExecutionResult."""
        pass
