import os
import re
import pandas as pd
import pytest
import sys

sys.path.insert(0, r"c:\Users\Mukul\Desktop\Tark")

from src.belief.engine import BeliefEngine
from src.policy.engine import PolicyEngine
from src.planner.decision_flip import DecisionFlipPlanner
from src.tools.llm_client import LLMClient
from bench.run import run_investigation_for_case

class MockTigerGraphConnection:
    """Mock TG connection for offline integrity verification."""
    def getVerticesById(self, vertex_type, vertex_id):
        return []

    def runInstalledQuery(self, query_name, params):
        if query_name == "customer_profile":
            return [{'total_txns': 0, 'total_amount': 0, 'avg_amount': 0}]
        elif query_name == "device_analysis":
            return [{'device_id': '', 'device_info': '', 'shared_card_count': 0, 'connected_cards': []}]
        elif query_name == "similar_cases":
            return []
        return []

    def upsertVertices(self, vertex_type, vertices):
        return len(vertices)

    def upsertEdges(self, source_type, edge_type, target_type, edges):
        return len(edges)

class MockLLMClient:
    """Mock LLM client to avoid remote API calls during automated tests."""
    def generate(self, system_prompt, user_prompt, temperature=0.1, max_tokens=1500):
        return "MOCK SAR NARRATIVE FOR INTEGRITY TEST"

def test_static_code_integrity():
    """Verify no benchmark case IDs, hardcoded entities, or trigger numbers exist in production code."""
    scan_dirs = [
        r"c:\Users\Mukul\Desktop\Tark\src",
        r"c:\Users\Mukul\Desktop\Tark\bench",
        r"c:\Users\Mukul\Desktop\Tark\etl",
        r"c:\Users\Mukul\Desktop\Tark\queries"
    ]
    forbidden_patterns = [
        r'case_id\s*==\s*["\']HHG-',
        r'["\']HHG-014["\']',
        r'["\']HHG-012["\']',
        r'["\']444\.0["\']',
        r'["\']264\.0["\']',
        r'["\']C13487-K1["\']',
        r'["\']C09214-K2["\']',
        r'["\']CC-0001["\']\s*,\s*["\']CC-0007["\']'
    ]

    for d in scan_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if not file.endswith((".py", ".gsql")):
                    continue
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                for pat in forbidden_patterns:
                    matches = re.findall(pat, content)
                    assert len(matches) == 0, f"Found forbidden hardcoded pattern '{pat}' in {file_path}"

def test_behavioral_invariance_to_case_id():
    """Verify that case_id is strictly an identifier and has ZERO influence on investigation logic."""
    belief_engine = BeliefEngine()
    policy_engine = PolicyEngine()
    planner = DecisionFlipPlanner(belief_engine, policy_engine)
    mock_conn = MockTigerGraphConnection()
    mock_llm = MockLLMClient()

    # Base test row
    row_original = {
        "case_id": "HHG-001",
        "opened_at": "2016-12-05 01:55:28",
        "trigger_type": "risk_score",
        "trigger_text": "Real-time model scored transaction 3514030 ($77.07, in billing region 444.0) at 0.61. Review and decide.",
        "flagged_txn_id": "3514030",
        "card_id": "C12382-K1",
        "customer_id": "C12382",
        "risk_score": 0.61
    }

    # Identical payload with synthetic case_id
    row_synthetic = dict(row_original)
    row_synthetic["case_id"] = "SYNTHETIC-999"

    res_orig = run_investigation_for_case(
        row=row_original,
        conn=mock_conn,
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        planner=planner,
        llm_client=mock_llm
    )

    res_synth = run_investigation_for_case(
        row=row_synthetic,
        conn=mock_conn,
        belief_engine=belief_engine,
        policy_engine=policy_engine,
        planner=planner,
        llm_client=mock_llm
    )

    # Assert mathematical and logical identity
    assert res_orig["case"]["verdict"] == res_synth["case"]["verdict"]
    assert res_orig["case"]["fraud_probability"] == res_synth["case"]["fraud_probability"]
    assert res_orig["case"]["pattern"] == res_synth["case"]["pattern"]
    assert res_orig["case"]["exposure_usd"] == res_synth["case"]["exposure_usd"]
    assert res_orig["case"]["affected_txn_ids"] == res_synth["case"]["affected_txn_ids"]
    assert res_orig["case"]["connected_card_ids"] == res_synth["case"]["connected_card_ids"]
    assert res_orig["next_best_actions"]["final"] == res_synth["next_best_actions"]["final"]
    assert res_orig["sar"]["file"] == res_synth["sar"]["file"]
    print("\nBehavioral invariance verified: changing case_id produces identical reasoning and actions.")

if __name__ == "__main__":
    test_static_code_integrity()
    test_behavioral_invariance_to_case_id()
    print("ALL BENCHMARK INTEGRITY TESTS PASSED.")
