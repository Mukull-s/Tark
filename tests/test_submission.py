import os
import json
import pytest

CASES_DIR = r"c:\Users\Mukul\Desktop\Tark\cases"

def test_all_20_cases_exist():
    for i in range(1, 21):
        cid = f"HHG-{i:03d}"
        path = os.path.join(CASES_DIR, f"{cid}.json")
        assert os.path.exists(path), f"Missing answer file: {path}"

def test_schema_conformance():
    valid_patterns = {
        "card_testing", 
        "card_not_present_fraud", 
        "card_not_present_fraud_new_device", 
        "out_of_region_use", 
        "account_takeover", 
        "undocumented", 
        "none"
    }

    for f in os.listdir(CASES_DIR):
        if not f.endswith(".json"):
            continue
        path = os.path.join(CASES_DIR, f)
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        # 1. Top level keys
        for key in ["case_id", "case", "evidence_requests", "next_best_actions", "sar", "stop_reason", "tool_calls", "tokens", "latency_s"]:
            assert key in data, f"Missing top level key '{key}' in {f}"

        c = data["case"]
        # 2. Case attributes
        assert isinstance(c["fraud_probability"], (float, int)), f"fraud_probability must be number in {f}"
        assert c["pattern"] in valid_patterns, f"Invalid pattern '{c['pattern']}' in {f}"
        assert c["written_to_graph"] is True, f"written_to_graph must be True in {f}"
        assert len(c["graph_case_id"]) > 0, f"graph_case_id must not be empty in {f}"

        # 3. Legitimate cases: exposure must be 0 and affected txns empty
        if c["verdict"] == "legitimate":
            assert len(c["affected_txn_ids"]) == 0, f"Legitimate case {f} must have empty affected_txn_ids"
            assert c["exposure_usd"] == 0.0, f"Legitimate case {f} must have exposure 0.0"

        # 4. Next best actions
        nba = data["next_best_actions"]
        assert "initial" in nba and "final" in nba, f"nba must have initial and final in {f}"
        assert "what_changed" in nba, f"Missing what_changed in {f}"

        # 5. SAR agreement
        has_file_report = any(a["action"] == "FILE_REPORT" for a in nba["final"])
        assert data["sar"]["file"] == has_file_report, f"sar.file must agree with FILE_REPORT action in {f}"
        if data["sar"]["file"]:
            assert data["sar"]["narrative"] is not None and len(data["sar"]["narrative"]) > 50, f"Missing SAR narrative in {f}"

    print("\nALL 20 BENCHMARK ANSWER FILES PASSED VALIDATION PERFECTLY!")

if __name__ == "__main__":
    test_all_20_cases_exist()
    test_schema_conformance()
