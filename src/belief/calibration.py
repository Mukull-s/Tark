import math
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class CalibrationClassification(str, Enum):
    EMPIRICAL = "EMPIRICAL"              # Statistically calculated from training partition
    POLICY_DEFINED = "POLICY_DEFINED"    # Mandated by bank risk governance rules
    HEURISTIC = "HEURISTIC"              # Domain heuristic based on fraud typologies
    PROVISIONAL = "PROVISIONAL"          # Uncalibrated / placeholder parameter

class EvidenceFamily(str, Enum):
    DEVICE_INFRASTRUCTURE = "DEVICE_INFRASTRUCTURE"
    TRANSACTION_VELOCITY = "TRANSACTION_VELOCITY"
    BEHAVIORAL_BASELINE = "BEHAVIORAL_BASELINE"
    GEOGRAPHIC_LOCATION = "GEOGRAPHIC_LOCATION"
    CUSTOMER_DISPUTE = "CUSTOMER_DISPUTE"
    MODEL_SCORE = "MODEL_SCORE"
    CASE_HISTORY = "CASE_HISTORY"

class LikelihoodRatioMetadata(BaseModel):
    evidence_type: str
    lr: float
    log_lr: float
    family: EvidenceFamily
    classification: CalibrationClassification
    description: str
    reliability: float = 1.0
    family_ceiling_log_lr: float = 5.0   # Maximum cumulative log-LR allowed from this family

# Prior Probability Profiles
class PriorProfile(str, Enum):
    ALERT_CONDITIONED = "ALERT_CONDITIONED"         # P(Fraud | Model Alert or Inbound Dispute) ~ 0.8383
    UNCONDITIONED_POPULATION = "UNCONDITIONED_POP"  # P(Fraud | General Transaction Stream) ~ 0.005
    UNIFORM_NON_INFORMATIVE = "UNIFORM"             # P(Fraud) = 0.50 (Maximum entropy baseline)

PRIOR_REGISTRY: Dict[PriorProfile, Dict[str, Any]] = {
    PriorProfile.ALERT_CONDITIONED: {
        "p_fraud": 0.8383,
        "log_odds": 1.6454,
        "classification": CalibrationClassification.EMPIRICAL,
        "source": "closed_cases_history.csv (4665 fraud / 5565 total alerted cases)",
        "notes": "Valid ONLY for alerted or escalated cases. Must NOT be applied to general transactions."
    },
    PriorProfile.UNCONDITIONED_POPULATION: {
        "p_fraud": 0.005,
        "log_odds": -5.2933,
        "classification": CalibrationClassification.PROVISIONAL,
        "source": "Industry baseline (~0.5% fraud rate across unselected card volume)",
        "notes": "Provisional transaction-level unconditioned base rate."
    },
    PriorProfile.UNIFORM_NON_INFORMATIVE: {
        "p_fraud": 0.50,
        "log_odds": 0.0,
        "classification": CalibrationClassification.HEURISTIC,
        "source": "Theoretical maximum entropy neutral prior",
        "notes": "Zero prior bias; belief updates driven purely by observed evidence."
    }
}

LIKELIHOOD_REGISTRY: Dict[str, LikelihoodRatioMetadata] = {
    "CARD_TESTING_SEQUENCE": LikelihoodRatioMetadata(
        evidence_type="CARD_TESTING_SEQUENCE",
        lr=34.3,
        log_lr=3.535,
        family=EvidenceFamily.TRANSACTION_VELOCITY,
        classification=CalibrationClassification.PROVISIONAL,
        description="3+ small authorizations (<$5) followed by larger transaction within 24h",
        family_ceiling_log_lr=4.5
    ),
    "HIGH_VELOCITY": LikelihoodRatioMetadata(
        evidence_type="HIGH_VELOCITY",
        lr=2.5,
        log_lr=0.916,
        family=EvidenceFamily.TRANSACTION_VELOCITY,
        classification=CalibrationClassification.PROVISIONAL,
        description="10+ transactions within 24h window",
        family_ceiling_log_lr=4.5
    ),
    "SHARED_DEVICE_RING": LikelihoodRatioMetadata(
        evidence_type="SHARED_DEVICE_RING",
        lr=14.2,
        log_lr=2.653,
        family=EvidenceFamily.DEVICE_INFRASTRUCTURE,
        classification=CalibrationClassification.PROVISIONAL,
        description="Same digital device profile shared across multiple distinct cards",
        family_ceiling_log_lr=4.0
    ),
    "PROXY_DETECTED": LikelihoodRatioMetadata(
        evidence_type="PROXY_DETECTED",
        lr=3.8,
        log_lr=1.335,
        family=EvidenceFamily.DEVICE_INFRASTRUCTURE,
        classification=CalibrationClassification.PROVISIONAL,
        description="Transaction originated from anonymous/hidden proxy",
        family_ceiling_log_lr=4.0
    ),
    "CNP_NEW_DEVICE": LikelihoodRatioMetadata(
        evidence_type="CNP_NEW_DEVICE",
        lr=1.31,
        log_lr=0.273,
        family=EvidenceFamily.DEVICE_INFRASTRUCTURE,
        classification=CalibrationClassification.PROVISIONAL,
        description="Card-not-present transaction on previously unseen device",
        family_ceiling_log_lr=4.0
    ),
    "CUSTOMER_DENIAL": LikelihoodRatioMetadata(
        evidence_type="CUSTOMER_DENIAL",
        lr=18.5,
        log_lr=2.918,
        family=EvidenceFamily.CUSTOMER_DISPUTE,
        classification=CalibrationClassification.POLICY_DEFINED,
        description="Customer disputes or explicitly denies transaction authorization",
        family_ceiling_log_lr=5.0
    ),
    "CUSTOMER_CONFIRMATION": LikelihoodRatioMetadata(
        evidence_type="CUSTOMER_CONFIRMATION",
        lr=0.05,
        log_lr=-2.996,
        family=EvidenceFamily.CUSTOMER_DISPUTE,
        classification=CalibrationClassification.POLICY_DEFINED,
        description="Customer confirms transaction was authorized (strongly exculpatory)",
        family_ceiling_log_lr=5.0
    ),
    "CUSTOMER_COMMUNICATION_UNAVAILABLE": LikelihoodRatioMetadata(
        evidence_type="CUSTOMER_COMMUNICATION_UNAVAILABLE",
        lr=1.0,
        log_lr=0.0,
        family=EvidenceFamily.CUSTOMER_DISPUTE,
        classification=CalibrationClassification.POLICY_DEFINED,
        description="Customer verification or challenge was unavailable, timed out, or not completed (neutral)",
        family_ceiling_log_lr=5.0
    ),
    "OUT_OF_REGION": LikelihoodRatioMetadata(
        evidence_type="OUT_OF_REGION",
        lr=0.26,
        log_lr=-1.357,
        family=EvidenceFamily.GEOGRAPHIC_LOCATION,
        classification=CalibrationClassification.EMPIRICAL,
        description="Transaction in unobserved billing region (empirically correlated with travel in IEEE-CIS)",
        family_ceiling_log_lr=2.5
    ),
    "RECURRING_CHARGE_MATCH": LikelihoodRatioMetadata(
        evidence_type="RECURRING_CHARGE_MATCH",
        lr=0.08,
        log_lr=-2.526,
        family=EvidenceFamily.BEHAVIORAL_BASELINE,
        classification=CalibrationClassification.POLICY_DEFINED,
        description="Transaction matches monthly recurring billing cadence and amount",
        family_ceiling_log_lr=3.5
    ),
    "BEHAVIORAL_BASELINE": LikelihoodRatioMetadata(
        evidence_type="BEHAVIORAL_BASELINE",
        lr=1.0,
        log_lr=0.0,
        family=EvidenceFamily.BEHAVIORAL_BASELINE,
        classification=CalibrationClassification.EMPIRICAL,
        description="Normal customer historical activity baseline (neutral)",
        family_ceiling_log_lr=0.0
    )
}

# Score Calibration Bins
SCORE_CALIBRATION_BINS = [
    {"range": (0.0, 0.3), "lr": 0.15, "log_lr": -1.897, "classification": CalibrationClassification.EMPIRICAL},
    {"range": (0.3, 0.6), "lr": 0.85, "log_lr": -0.163, "classification": CalibrationClassification.EMPIRICAL},
    {"range": (0.6, 0.8), "lr": 2.4,  "log_lr": 0.875,  "classification": CalibrationClassification.EMPIRICAL},
    {"range": (0.8, 1.0), "lr": 6.8,  "log_lr": 1.917,  "classification": CalibrationClassification.EMPIRICAL}
]

def get_calibrated_lr(evidence_type: str) -> Optional[LikelihoodRatioMetadata]:
    """Retrieves calibrated metadata for an evidence type."""
    return LIKELIHOOD_REGISTRY.get(evidence_type)

def get_model_score_lr(score: float) -> Dict[str, Any]:
    """Resolves binned empirical likelihood ratio for raw risk score."""
    for b in SCORE_CALIBRATION_BINS:
        if b["range"][0] <= score < b["range"][1] or (b["range"][1] == 1.0 and score <= 1.0):
            return b
    return {"lr": 1.0, "log_lr": 0.0, "classification": CalibrationClassification.HEURISTIC}
