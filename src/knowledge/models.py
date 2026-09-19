from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class KnowledgeCategory(str, Enum):
    POLICY_RULE = "POLICY_RULE"
    FRAUD_TYPOLOGY = "FRAUD_TYPOLOGY"
    REGULATORY_STATUTE = "REGULATORY_STATUTE"
    INVESTIGATION_PROCEDURE = "INVESTIGATION_PROCEDURE"


class KnowledgeChunk(BaseModel):
    """Authoritative passage of regulatory, policy, or typology knowledge.
    
    CRITICAL ARCHITECTURAL BOUNDARY:
    Retrieved knowledge passages provide regulatory and operational guidance only.
    They must never directly modify fraud probability, never fabricate evidence coverage,
    and never bypass Decision Gate blocks.
    """
    chunk_id: str = Field(description="Unique knowledge chunk identifier (e.g. KNOW-POLICY-R5)")
    title: str = Field(description="Descriptive header of standard or rule")
    category: KnowledgeCategory
    text: str = Field(description="Verbatim grounded text of rule or typology description")
    applicable_rules: List[str] = Field(default_factory=list, description="Policy rule tags (e.g. ['R5', 'R2'])")
    applicable_typologies: List[str] = Field(default_factory=list, description="Typology tags (e.g. ['card_testing'])")
    governing_body: str = Field(description="Regulatory or corporate authority (e.g. 'FinCEN', 'FATF', 'Bank Risk Policy')")
    section_reference: str = Field(description="Specific clause, rule, or statutory citation (e.g. 'Rule R5.2', '31 CFR 1020.320')")
    version: str = Field(default="2026.1", description="Policy or regulation version identifier")
    provenance: str = Field(default="Bank Governance Repository", description="Lineage source of document")


class RetrievedKnowledgeItem(BaseModel):
    """Contextual knowledge chunk retrieved by Policy GraphRAG for an active case."""
    chunk: KnowledgeChunk
    relevance_score: float = Field(ge=0.0, le=1.0, description="GraphRAG relevance affinity [0.0 - 1.0]")
    match_rationale: str = Field(description="Explicit explanation of why this rule or statute applies to current graph evidence")
    applicable_statute_or_rule: str = Field(description="Primary rule/statute code")
