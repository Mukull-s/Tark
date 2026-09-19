from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from src.evidence.types import EvidenceItem, EvidenceDirection
from src.belief.calibration import EvidenceFamily

class WorldHypothesis(str, Enum):
    """Mutually exclusive world states of nature.
    Note: INSUFFICIENT_EVIDENCE is an epistemic decision state, not a competing world state.
    """
    FRAUD = "FRAUD"
    LEGITIMATE = "LEGITIMATE"

# Backwards compatibility alias
HypothesisType = WorldHypothesis

class HypothesisStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    REFUTED = "REFUTED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"

class HypothesisState(BaseModel):
    hypothesis: WorldHypothesis
    probability: float = Field(default=0.5, ge=0.0, le=1.0, description="Posterior probability of this world state (sum of world states = 1.0)")
    log_odds: float = Field(default=0.0)
    status: HypothesisStatus = Field(default=HypothesisStatus.ACTIVE)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    net_weight: float = Field(default=0.0)

class ContradictionItem(BaseModel):
    contradiction_id: str
    description: str
    inculpatory_evidence_ids: List[str]
    exculpatory_evidence_ids: List[str]
    conflict_magnitude: float = Field(ge=0.0, le=1.0, description="Normalized severity of evidence conflict [0.0 - 1.0]")
    resolution_status: str = Field(default="UNRESOLVED")

class MissingInfoItem(BaseModel):
    missing_id: str
    dimension: str             # e.g., "GEOGRAPHIC_LOCATION", "DEVICE_INFRASTRUCTURE"
    entity: str                # Target entity identifier
    reason: str                # DATA_OUT_OF_SCOPE, UNOBSERVED, GRAPH_QUERY_FAILURE, TIMEOUT
    impact_severity: str       # LOW, MEDIUM, CRITICAL
    actionable_query: Optional[str] = None

class UncertaintyState(BaseModel):
    """Explicit, multi-dimensional uncertainty state.
    Distinguishes observed coverage, missing data, out-of-scope data, and conflicting signals.
    """
    epistemic_uncertainty: float = Field(default=0.5, ge=0.0, le=1.0, description="Uncertainty due to missing/unobserved data")
    aleatoric_uncertainty: float = Field(default=0.0, ge=0.0, le=1.0, description="Uncertainty due to conflicting evidence")
    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Fraction of core investigative dimensions observed")
    evidence_completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="Backwards-compatible alias for evidence_coverage")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Overall trustworthiness of probability")
    data_coverage: Dict[str, bool] = Field(default_factory=dict, description="Coverage flags per core dimension")
    observed_dimensions: List[str] = Field(default_factory=list, description="Core dimensions observed in evidence")
    missing_dimensions: List[str] = Field(default_factory=list, description="Core dimensions currently unobserved")
    unavailable_dimensions: List[str] = Field(default_factory=list, description="Dimensions reporting DATA_OUT_OF_SCOPE or GRAPH_QUERY_FAILURE")
    uncertainty_reasons: List[str] = Field(default_factory=list, description="Explicit qualitative explanations of remaining uncertainty")

class ReasoningStep(BaseModel):
    step: int
    event: str
    evidence_id: Optional[str] = None
    evidence_type: Optional[str] = None
    family: Optional[str] = None
    raw_lr: float = 1.0
    discount_factor: float = 1.0
    effective_log_lr: float = 0.0
    prior_log_odds: float
    posterior_log_odds: float
    posterior_prob: float
    uncertainty_delta: float = 0.0
    rationale: str

class DecisionState(str, Enum):
    """Formal decision and epistemic determination states."""
    PENDING = "PENDING"
    DECIDED = "DECIDED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"

class InvestigationState(BaseModel):
    """First-class Investigation State Model for Tark Reasoning Engine.
    Exposes complete belief, world hypotheses, uncertainty, decision gating, and machine-readable reasoning trace.
    """
    investigation_id: str
    trigger: Dict[str, Any] = Field(default_factory=dict)
    target_entities: Dict[str, str] = Field(default_factory=dict)
    
    # World Hypotheses (FRAUD and LEGITIMATE only)
    hypotheses: Dict[WorldHypothesis, HypothesisState] = Field(default_factory=dict)
    primary_hypothesis: WorldHypothesis = Field(default=WorldHypothesis.FRAUD)
    secondary_typology: str = Field(default="undocumented")
    
    # Evidence & Belief
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    belief_state: Dict[str, Any] = Field(default_factory=dict)
    
    # Explicit Uncertainty & Contradictions
    uncertainty: UncertaintyState = Field(default_factory=UncertaintyState)
    contradictions: List[ContradictionItem] = Field(default_factory=list)
    missing_information: List[MissingInfoItem] = Field(default_factory=list)
    
    # Decision Gating & Policy
    decision_state: DecisionState = Field(default=DecisionState.PENDING)
    decision_gate_passed: bool = Field(default=False, description="True if evidence satisfies all automated decision contract criteria")
    decision_gate_blocks: List[str] = Field(default_factory=list, description="List of unmet decision contract requirements if blocked")
    decision_rationale: str = Field(default="")
    
    # Action Planning State (Prepared for Phase 4 consumption)
    candidate_actions: List[Dict[str, Any]] = Field(default_factory=list)
    policy_constraints: List[str] = Field(default_factory=list)
    approval_requirements: List[str] = Field(default_factory=list)
    
    # Traceability
    reasoning_history: List[ReasoningStep] = Field(default_factory=list)
