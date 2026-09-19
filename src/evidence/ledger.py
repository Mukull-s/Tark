from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.evidence.types import EvidenceItem, EvidenceType

class EvidenceLedger(BaseModel):
    items: List[EvidenceItem] = Field(default_factory=list)

    def add(self, item: EvidenceItem):
        self.items.append(item)

    def get_by_type(self, evidence_type: EvidenceType) -> List[EvidenceItem]:
        return [i for i in self.items if i.evidence_type == evidence_type]

    def total_log_lr(self) -> float:
        return sum(item.log_lr for item in self.items)

    def to_summary_dict(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": item.evidence_type.value,
                "source": item.source,
                "finding": item.finding,
                "lr": item.lr,
                "log_lr": item.log_lr,
                "exculpatory": item.is_exculpatory
            }
            for item in self.items
        ]
