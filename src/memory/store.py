import os
import csv
import json
import logging
from typing import Dict, List, Optional
from threading import RLock
from datetime import datetime, timezone

from src.memory.models import CaseMemoryRecord, MemoryProvenanceType

logger = logging.getLogger(__name__)


class CaseMemoryStore:
    """Thread-safe storage and indexing engine for historical fraud investigations.
    
    Provides fast lookup across historical cases (from closed_cases_history.csv and
    investigation write-backs).
    
    CRITICAL SECURITY & INTEGRITY CONSTRAINTS:
    - Never stores or leaks benchmark ground truth labels.
    - Represents historical outcomes strictly as historical precedent.
    - Preserves audit provenance on all written and retrieved records.
    - Enforces deterministic memory snapshot isolation and temporal cutoffs.
    """

    def __init__(
        self,
        csv_path: Optional[str] = None,
        writeback_path: Optional[str] = None,
        is_frozen: bool = False,
        effective_timestamp: Optional[str] = None
    ):
        self._lock = RLock()
        self._cases_by_id: Dict[str, CaseMemoryRecord] = {}
        self._cases_by_card: Dict[str, List[str]] = {}
        self._cases_by_customer: Dict[str, List[str]] = {}
        self._cases_by_pattern: Dict[str, List[str]] = {}
        self.is_frozen = is_frozen
        self.effective_timestamp = effective_timestamp
        
        # Default data paths
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.csv_path = csv_path if csv_path is not None else os.path.join(base_dir, "closed_cases_history.csv")
        self.writeback_path = writeback_path if writeback_path is not None else os.path.join(base_dir, "cases", "memory_writebacks.jsonl")

        # Load initial historical data
        if self.csv_path and os.path.exists(self.csv_path):
            self._load_from_csv(self.csv_path)

        # Load previously persisted writebacks if present
        if self.writeback_path and os.path.exists(self.writeback_path):
            self._load_from_writeback(self.writeback_path)

    def _load_from_csv(self, path: str):
        """Parses closed_cases_history.csv into structured CaseMemoryRecords."""
        with open(path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    case_id = row.get("case_id", "").strip()
                    if not case_id:
                        continue

                    # Parse pipe-separated lists
                    actions_raw = row.get("actions_taken", "")
                    actions = [a.strip() for a in actions_raw.split("|") if a.strip()]

                    txns_raw = row.get("txn_ids", "")
                    txns = [t.strip() for t in txns_raw.split("|") if t.strip()]

                    cards_raw = row.get("connected_card_ids", "")
                    conn_cards = [c.strip() for c in cards_raw.split("|") if c.strip()]

                    try:
                        exposure = float(row.get("exposure_usd", 0.0) or 0.0)
                    except (ValueError, TypeError):
                        exposure = 0.0

                    try:
                        n_txns = int(row.get("n_txns", 1) or 1)
                    except (ValueError, TypeError):
                        n_txns = len(txns) if txns else 1

                    report_filed = str(row.get("report_filed", "No")).strip().lower() in ["yes", "true", "1"]

                    # Extract inferred evidence families from analyst notes/pattern
                    pattern = row.get("pattern", "unknown").strip().lower()
                    analyst_notes = row.get("analyst_notes", "").strip()
                    evidence_families = self._infer_evidence_families(pattern, analyst_notes)
                    decisive_ev = self._infer_decisive_evidence(analyst_notes)

                    record = CaseMemoryRecord(
                        case_id=case_id,
                        customer_id=row.get("customer_id", "").strip() or None,
                        card_id=row.get("card_id", "").strip() or None,
                        opened_at=row.get("opened_at", "").strip() or None,
                        closed_at=row.get("closed_at", "").strip() or None,
                        historical_outcome=row.get("outcome", "unknown").strip(),
                        pattern=pattern,
                        first_fraud_txn_id=row.get("first_fraud_txn_id", "").strip() or None,
                        txn_ids=txns,
                        n_txns=n_txns,
                        exposure_usd=exposure,
                        connected_card_ids=conn_cards,
                        actions_taken=actions,
                        report_filed=report_filed,
                        analyst_notes=analyst_notes,
                        evidence_families_observed=evidence_families,
                        decisive_evidence=decisive_ev,
                        provenance=MemoryProvenanceType.HISTORICAL_CSV.value
                    )
                    if self.effective_timestamp:
                        ts = record.closed_at or record.opened_at
                        if not ts or not self._is_timestamp_on_or_before(ts, self.effective_timestamp):
                            continue
                    self._index_record(record)
                except Exception as e:
                    logger.debug(f"Error parsing row in {path}: {e}")

    def _infer_evidence_families(self, pattern: str, notes: str) -> List[str]:
        """Infers which core evidence families were involved in the historical case."""
        fams = set()
        text = f"{pattern} {notes}".lower()
        if "device" in text or "phone" in text or "trident" in text or "proxy" in text:
            fams.add("DEVICE_INFRASTRUCTURE")
        if "region" in text or "travel" in text or "country" in text or "billing" in text:
            fams.add("GEOGRAPHIC_LOCATION")
        if "velocity" in text or "testing" in text or "sequence" in text or "micro" in text:
            fams.add("TRANSACTION_VELOCITY")
        if "customer" in text or "reported" in text or "confirmed" in text or "disputed" in text or "denied" in text:
            fams.add("CUSTOMER_DISPUTE")
        if "score" in text or "model" in text or "scored" in text:
            fams.add("RISK_SCORE")
        return sorted(list(fams))

    def _infer_decisive_evidence(self, notes: str) -> Optional[str]:
        """Identifies what historical evidence was pivotal in the analyst conclusion."""
        text = notes.lower()
        if "cardholder confirmed travel" in text:
            return "Customer Travel Confirmation (Exculpatory)"
        if "cardholder reported unrecognized" in text:
            return "Cardholder Dispute / Denial (Inculpatory)"
        if "cardholder confirmed the purchase" in text:
            return "Cardholder Legitimate Purchase Confirmation (Exculpatory)"
        if "device added to profile" in text:
            return "Device Profile Verification"
        if "online transactions came from" in text:
            return "Unauthorized Device Infrastructure Signature"
        return None

    def _load_from_writeback(self, path: str):
        """Loads dynamically written-back completed investigations."""
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    record = CaseMemoryRecord(**data)
                    if self.effective_timestamp:
                        ts = record.closed_at or record.opened_at
                        if not ts or not self._is_timestamp_on_or_before(ts, self.effective_timestamp):
                            continue
                    self._index_record(record)
        except Exception as e:
            logger.warning(f"Could not load writeback file {path}: {e}")

    def _index_record(self, record: CaseMemoryRecord):
        """Adds record to primary and secondary lookup indexes."""
        with self._lock:
            self._cases_by_id[record.case_id] = record
            if record.card_id:
                self._cases_by_card.setdefault(record.card_id, []).append(record.case_id)
            if record.customer_id:
                self._cases_by_customer.setdefault(record.customer_id, []).append(record.case_id)
            if record.pattern:
                self._cases_by_pattern.setdefault(record.pattern, []).append(record.case_id)

    @staticmethod
    def _is_timestamp_on_or_before(ts: Optional[str], cutoff: str) -> bool:
        """Determines if a case closure timestamp occurred on or before the cutoff timestamp."""
        if not ts or not cutoff:
            return False
        try:
            s_ts = str(ts).strip().replace(" ", "T")
            s_cutoff = str(cutoff).strip().replace(" ", "T")
            dt_ts = datetime.fromisoformat(s_ts)
            dt_cutoff = datetime.fromisoformat(s_cutoff)
            if dt_ts.tzinfo is None:
                dt_ts = dt_ts.replace(tzinfo=timezone.utc)
            if dt_cutoff.tzinfo is None:
                dt_cutoff = dt_cutoff.replace(tzinfo=timezone.utc)
            return dt_ts <= dt_cutoff
        except Exception:
            return str(ts) <= str(cutoff)

    def create_snapshot(self, effective_timestamp: Optional[str] = None) -> "CaseMemoryStore":
        """Creates an immutable, frozen memory snapshot filtered to cases closed on or before effective_timestamp.
        
        Guarantees that during benchmark evaluation:
        - Memory is frozen (writeback blocked)
        - Historical cases closed after effective_timestamp are strictly excluded
        - Cross-case memory contamination is eliminated
        """
        with self._lock:
            cutoff = effective_timestamp or self.effective_timestamp
            snapshot = CaseMemoryStore(
                csv_path=None,
                writeback_path=None,
                is_frozen=True,
                effective_timestamp=cutoff
            )
            for cid, record in self._cases_by_id.items():
                if cutoff:
                    ts = record.closed_at or record.opened_at
                    if not ts or not self._is_timestamp_on_or_before(ts, cutoff):
                        continue
                snapshot._index_record(record.model_copy(deep=True))
            return snapshot

    def add_case(self, record: CaseMemoryRecord, persist: bool = True) -> bool:
        """Writes a newly completed investigation record into case memory.
        
        If store is frozen (e.g. during benchmark evaluation), writeback is strictly
        prohibited to guarantee zero cross-case memory contamination.
        """
        if self.is_frozen:
            logger.debug(f"CaseMemoryStore is frozen. Writeback rejected for case {record.case_id}.")
            return False

        with self._lock:
            self._index_record(record)
            if persist and self.writeback_path:
                try:
                    os.makedirs(os.path.dirname(self.writeback_path), exist_ok=True)
                    with open(self.writeback_path, mode="a", encoding="utf-8") as f:
                        f.write(json.dumps(record.model_dump()) + "\n")
                except Exception as e:
                    logger.warning(f"Failed to persist memory write-back to {self.writeback_path}: {e}")
            return True

    def write_case(self, record: CaseMemoryRecord, persist: bool = True) -> bool:
        """Alias for add_case to write a case record into memory."""
        return self.add_case(record, persist=persist)

    def get_case(self, case_id: str) -> Optional[CaseMemoryRecord]:
        """Retrieves a single case by identifier."""
        with self._lock:
            return self._cases_by_id.get(case_id)

    def get_by_card(self, card_id: str) -> List[CaseMemoryRecord]:
        with self._lock:
            cids = self._cases_by_card.get(card_id, [])
            return [self._cases_by_id[cid] for cid in cids if cid in self._cases_by_id]

    def get_by_customer(self, customer_id: str) -> List[CaseMemoryRecord]:
        with self._lock:
            cids = self._cases_by_customer.get(customer_id, [])
            return [self._cases_by_id[cid] for cid in cids if cid in self._cases_by_id]

    def get_by_pattern(self, pattern: str) -> List[CaseMemoryRecord]:
        with self._lock:
            cids = self._cases_by_pattern.get(pattern.lower(), [])
            return [self._cases_by_id[cid] for cid in cids if cid in self._cases_by_id]

    def all_cases(self) -> List[CaseMemoryRecord]:
        with self._lock:
            return list(self._cases_by_id.values())

    def count(self) -> int:
        with self._lock:
            return len(self._cases_by_id)
