from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MemoryProvenanceType(str, Enum):
    HISTORICAL_CSV = "closed_cases_history.csv"
    TIGERGRAPH_CLOSED_CASE = "TigerGraph:ClosedCase"
    INVESTIGATION_WRITEBACK = "InvestigationCase_writeback"
    EXTERNAL_PRECEDENT = "external_precedent"


class CaseMemoryRecord(BaseModel):
    """Canonical representation of a historical closed fraud investigation.
    
    CRITICAL ARCHITECTURAL BOUNDARY:
    Historical cases are contextual precedent only.
    They must never be ingested as EvidenceItems, never receive Likelihood Ratios,
    never alter posterior fraud probabilities, and never fabricate evidence coverage.
    """
    case_id: str = Field(description="Unique historical case identifier (e.g. CC-0001, INV-2026-...)")
    customer_id: Optional[str] = Field(default=None, description="Cardholder identifier if known")
    card_id: Optional[str] = Field(default=None, description="Primary card identifier involved")
    opened_at: Optional[str] = Field(default=None, description="Case opening timestamp ISO")
    closed_at: Optional[str] = Field(default=None, description="Case disposition timestamp ISO")
    historical_outcome: str = Field(description="Historical disposition label (e.g. confirmed_fraud, cleared, fraud, legitimate)")
    pattern: str = Field(default="unknown", description="Investigative typology/pattern classification")
    first_fraud_txn_id: Optional[str] = Field(default=None, description="Root transaction flagged")
    txn_ids: List[str] = Field(default_factory=list, description="All transactions connected to this historical case")
    n_txns: int = Field(default=1, description="Count of transactions involved")
    exposure_usd: float = Field(default=0.0, description="Total dollar exposure of historical case")
    connected_card_ids: List[str] = Field(default_factory=list, description="Other cards connected to this incident")
    actions_taken: List[str] = Field(default_factory=list, description="Operational actions taken upon closure")
    report_filed: bool = Field(default=False, description="Whether regulatory SAR/report was filed")
    analyst_notes: str = Field(default="", description="Investigator notes detailing case mechanics and findings")
    evidence_families_observed: List[str] = Field(default_factory=list, description="Evidence families observed in historical case")
    decisive_evidence: Optional[str] = Field(default=None, description="Decisive evidence that determined historical outcome")
    approval_route: Optional[str] = Field(default="auto", description="Approval route required for historical actions")
    policy_references: List[str] = Field(default_factory=list, description="Bank policy rules cited in disposition")
    provenance: str = Field(default=MemoryProvenanceType.HISTORICAL_CSV.value, description="Origin lineage of memory record")


class CaseSimilarityDimensions(BaseModel):
    """Decomposition of multi-attribute similarity between current investigation and historical case."""
    same_customer: bool = Field(default=False)
    same_card: bool = Field(default=False)
    same_pattern: bool = Field(default=False)
    connected_card_overlap: bool = Field(default=False)
    exposure_proximity: float = Field(default=0.0, ge=0.0, le=1.0)
    velocity_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    textual_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class SimilarCaseMatch(BaseModel):
    """Contextual precedent retrieved from case memory for an active investigation.
    
    Guarantees strict separation from observed graph evidence:
    - Never receives an LR
    - Never modifies belief state
    - Retains full structural explanation of why it was deemed similar
    - Exposes explicit temporal and data provenance
    """
    case_record: CaseMemoryRecord
    similarity_score: float = Field(ge=0.0, le=1.0, description="Composite similarity metric [0.0 - 1.0]")
    dimensions: CaseSimilarityDimensions
    shared_features: List[str] = Field(default_factory=list, description="Human-readable list of overlapping attributes")
    explanation: str = Field(description="Structured explanation of similarity rationale")
    role: str = Field(default="CONTEXTUAL_PRECEDENT_ONLY", description="Explicit memory role disclaimer")
    historical_timestamp: Optional[str] = Field(default=None, description="Authoritative closure timestamp of historical case")
    eligibility_reason: str = Field(default="", description="Temporal and data provenance rationale for case eligibility")

    @property
    def matching_features(self) -> List[str]:
        """Alias for shared_features for evaluation transparency."""
        return self.shared_features

    @property
    def case_id(self) -> str:
        """Top-level property for direct case ID access."""
        return self.case_record.case_id
