import uuid
from enum import Enum
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field

class EvidenceType(str, Enum):
    BEHAVIORAL_BASELINE = "BEHAVIORAL_BASELINE"
    CARD_TESTING_SEQUENCE = "CARD_TESTING_SEQUENCE"
    OUT_OF_REGION = "OUT_OF_REGION"
    CNP_NEW_DEVICE = "CNP_NEW_DEVICE"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    SHARED_DEVICE_RING = "SHARED_DEVICE_RING"
    PROXY_DETECTED = "PROXY_DETECTED"
    CUSTOMER_DENIAL = "CUSTOMER_DENIAL"
    CUSTOMER_CONFIRMATION = "CUSTOMER_CONFIRMATION"
    CUSTOMER_COMMUNICATION_UNAVAILABLE = "CUSTOMER_COMMUNICATION_UNAVAILABLE"
    RECURRING_CHARGE_MATCH = "RECURRING_CHARGE_MATCH"
    CALIBRATED_RISK_SCORE = "CALIBRATED_RISK_SCORE"
    SIMILAR_CASE_PRECEDENT = "SIMILAR_CASE_PRECEDENT"
    HIGH_VELOCITY = "HIGH_VELOCITY"

class EvidenceDirection(str, Enum):
    SUPPORTS = "SUPPORTS"          # Supports fraud hypothesis (inculpatory, LR > 1.0)
    CONTRADICTS = "CONTRADICTS"    # Contradicts fraud hypothesis (exculpatory, LR < 1.0)
    NEUTRAL = "NEUTRAL"            # Baseline context or uninformative (LR == 1.0)

class EvidenceItem(BaseModel):
    """Canonical Evidence Object Contract for Tark Investigation Engine.
    Preserves strict provenance, graph traversal attribution, and belief updates.
    """
    evidence_id: str = Field(default_factory=lambda: f"EVD-{uuid.uuid4().hex[:8].upper()}")
    evidence_type: EvidenceType
    value: Any = Field(default=None, description="Raw quantitative or categorical value observed")
    source: str = Field(description="Query name, model signal, inbound channel, or external gateway")
    finding: str = Field(description="Human readable explanation of the evidence finding")
    provenance: str = Field(default="", description="Explicit data lineage tracing to source CSV or database table")
    
    # Entity Attribution
    source_entity: Optional[str] = Field(default=None, description="Starting vertex/entity in graph traversal")
    target_entity: Optional[str] = Field(default=None, description="Ending vertex/entity reached in graph traversal")
    graph_query: Optional[str] = Field(default=None, description="Name of installed GSQL query that produced this finding")
    
    # Provenance Graph Links
    supporting_transaction_ids: List[str] = Field(default_factory=list, description="Associated transaction IDs")
    supporting_entities: List[str] = Field(default_factory=list, description="Connected cards, devices, or accounts")
    timestamp: Optional[str] = Field(default=None, description="Observation or event timestamp")
    
    # Scoring Metadata
    reliability: float = Field(default=1.0, description="Data source confidence [0.0 - 1.0]")
    lr: float = Field(default=1.0, description="Empirical Likelihood Ratio P(E|Fraud)/P(E|Legit)")
    log_lr: float = Field(default=0.0, description="Natural logarithm of the Likelihood Ratio")
    direction: EvidenceDirection = Field(default=EvidenceDirection.NEUTRAL, description="Direction of evidentiary shift")
    is_exculpatory: bool = Field(default=False, description="True if evidence points towards legitimate")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed query metrics or attribute payload")

    def __init__(self, **data):
        super().__init__(**data)
        # Harmonize direction and is_exculpatory
        if "direction" not in data or data["direction"] == EvidenceDirection.NEUTRAL:
            if self.is_exculpatory or self.lr < 1.0:
                self.direction = EvidenceDirection.CONTRADICTS
                self.is_exculpatory = True
            elif self.lr > 1.0:
                self.direction = EvidenceDirection.SUPPORTS
                self.is_exculpatory = False
            else:
                self.direction = EvidenceDirection.NEUTRAL
                self.is_exculpatory = False
        else:
            if self.direction == EvidenceDirection.CONTRADICTS:
                self.is_exculpatory = True
            elif self.direction == EvidenceDirection.SUPPORTS:
                self.is_exculpatory = False

        # Set graph_query and provenance if unset
        if not self.graph_query and self.source in [
            "customer_profile", "txn_velocity", "device_analysis",
            "card_sequence", "region_analysis", "similar_cases"
        ]:
            self.graph_query = self.source
            if not self.provenance:
                self.provenance = f"tigergraph_gsql_{self.source}"
