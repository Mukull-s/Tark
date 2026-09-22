"""Memory Hygiene & Frozen-Snapshot Integrity Tests.

Verifies:
1. The persisted case-memory writeback log contains no synthetic dummy rows
   (e.g. F3-SELF / F4-FUT) and no benchmark-leaking identifiers.
2. Passing ``writeback_path=None`` / ``csv_path=None`` truly disables those
   sources (rather than silently falling back to the shared default file).
3. Frozen snapshots reject write-back, guaranteeing zero cross-case
   contamination during benchmark/evaluation runs.
"""

import os
import json
import pathlib

from src.memory.store import CaseMemoryStore

WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parent.parent
WRITEBACK_PATH = WORKSPACE_ROOT / "cases" / "memory_writebacks.jsonl"

FORBIDDEN_DUMMY_IDS = {"F3-SELF", "F4-FUT"}
# Legitimate provenance prefixes for persisted investigation write-backs.
ALLOWED_CASE_PREFIXES = ("INV-", "CC-", "TXN-", "CLEARED-", "HHG-")


def _read_writeback_rows():
    if not WRITEBACK_PATH.exists():
        return []
    rows = []
    with open(WRITEBACK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def test_writeback_log_contains_no_dummy_rows():
    """The persisted writeback log must never contain the synthetic F3-SELF/F4-FUT loop."""
    rows = _read_writeback_rows()
    case_ids = {str(r.get("case_id", "")) for r in rows}
    assert not (case_ids & FORBIDDEN_DUMMY_IDS), (
        f"memory_writebacks.jsonl contains synthetic dummy rows: {case_ids & FORBIDDEN_DUMMY_IDS}"
    )


def test_writeback_log_only_real_provenance():
    """Any persisted row must be a real investigation/closed-case record."""
    for r in _read_writeback_rows():
        cid = str(r.get("case_id", ""))
        assert cid.startswith(ALLOWED_CASE_PREFIXES), f"Unexpected writeback case_id: {cid}"
        # Dummy records carried the historical-CSV provenance while living in the writeback log.
        assert r.get("analyst_notes") != "" or r.get("txn_ids"), (
            f"Writeback row {cid} looks like an empty placeholder."
        )


def test_explicit_none_disables_writeback_and_csv():
    """``None`` must fully disable a source (no silent fallback to shared defaults)."""
    store = CaseMemoryStore(csv_path=None, writeback_path=None)
    assert store.csv_path is None
    assert store.writeback_path is None
    assert store.count() == 0

    from src.memory.models import CaseMemoryRecord

    rec = CaseMemoryRecord(
        case_id="INV-HYGIENE-TEST",
        historical_outcome="cleared",
        pattern="none",
    )
    assert store.add_case(rec, persist=True) is True  # in-memory only
    assert store.writeback_path is None
    assert not WRITEBACK_PATH.exists() or "INV-HYGIENE-TEST" not in WRITEBACK_PATH.read_text(encoding="utf-8")


def test_frozen_snapshot_rejects_writeback():
    """Frozen snapshots must reject write-back and preserve an immutable cutoff."""
    store = CaseMemoryStore(writeback_path=None)
    before = store.count()
    snapshot = store.create_snapshot(effective_timestamp="2016-11-11 23:59:59")
    assert snapshot.is_frozen is True
    assert snapshot.count() == before

    from src.memory.models import CaseMemoryRecord

    rec = CaseMemoryRecord(
        case_id="INV-FROZEN-REJECT",
        historical_outcome="confirmed_fraud",
        pattern="card_testing",
    )
    assert snapshot.add_case(rec, persist=True) is False
    assert snapshot.count() == before
    assert snapshot.get_case("INV-FROZEN-REJECT") is None


def test_frozen_snapshot_excludes_future_cases():
    """Snapshot must strictly exclude cases closed after the cutoff timestamp."""
    store = CaseMemoryStore(writeback_path=None)
    snapshot = store.create_snapshot(effective_timestamp="2016-11-11 23:59:59")
    for record in snapshot.all_cases():
        ts = record.closed_at or record.opened_at
        if not ts:
            continue
        # All retained records must be on/before the frozen cutoff.
        assert CaseMemoryStore._is_timestamp_on_or_before(ts, "2016-11-11 23:59:59")
