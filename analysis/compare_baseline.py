import os
import json

def compare():
    raw_results = json.load(open("analysis/phase4.5_baseline_raw_results.json"))
    print(f"Loaded {len(raw_results)} baseline results.")

    comparisons = []
    correct_verdict = 0
    correct_action = 0

    for r in raw_results:
        cid = r["case_id"]
        gt_path = os.path.join("cases", f"{cid}.json")
        if not os.path.exists(gt_path):
            print(f"Warning: Ground truth {gt_path} not found!")
            continue
        gt = json.load(open(gt_path))
        gt_case = gt.get("case", {})
        gt_verdict = gt_case.get("verdict", "unknown")
        gt_p_fraud = gt_case.get("fraud_probability", 0.5)
        gt_actions = [a.get("action") for a in gt.get("next_best_actions", {}).get("final", [])]
        gt_primary_action = gt_actions[0] if gt_actions else "NONE"

        tark_p_fraud = r["final_p_fraud"]
        tark_classification = r["final_classification"]
        tark_actions = r["policy_actions"]
        tark_primary_action = r["next_best_action"]

        # Verdict alignment
        norm_gt_verdict = "fraud" if "fraud" in gt_verdict.lower() else ("legitimate" if "cleared" in gt_verdict.lower() or "legit" in gt_verdict.lower() else "uncertain")
        verdict_match = (tark_classification == norm_gt_verdict)
        if verdict_match:
            correct_verdict += 1

        # Action alignment: primary match or set intersection
        action_match = (tark_primary_action == gt_primary_action) or (tark_primary_action in gt_actions)
        if action_match:
            correct_action += 1

        comp = {
            "case_id": cid,
            "trigger_type": r["trigger_type"],
            "tark_p_fraud": tark_p_fraud,
            "gt_p_fraud": gt_p_fraud,
            "tark_verdict": tark_classification,
            "gt_verdict": norm_gt_verdict,
            "verdict_match": verdict_match,
            "tark_primary_action": tark_primary_action,
            "gt_primary_action": gt_primary_action,
            "action_match": action_match,
            "tark_all_actions": tark_actions,
            "gt_all_actions": gt_actions,
            "tark_steps": r["evidence_steps"],
            "tark_coverage": r["evidence_coverage"],
            "gate_passed": r["decision_gate_passed"],
            "termination": r["termination_reason"]
        }
        comparisons.append(comp)

    print(f"Verdict Agreement: {correct_verdict} / {len(comparisons)} ({correct_verdict/len(comparisons)*100:.1f}%)")
    print(f"Action Agreement:  {correct_action} / {len(comparisons)} ({correct_action/len(comparisons)*100:.1f}%)")

    print("\nDetailed Breakdown:")
    print("| Case | Trigger | Tark P | GT P | Tark Verdict | GT Verdict | V-Match | Tark Action | GT Action | A-Match | Gate | Steps |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in comparisons:
        v_icon = "PASS" if c["verdict_match"] else "FAIL"
        a_icon = "PASS" if c["action_match"] else "FAIL"
        print(f"| {c['case_id']} | {c['trigger_type']} | {c['tark_p_fraud']:.3f} | {c['gt_p_fraud']:.3f} | {c['tark_verdict']} | {c['gt_verdict']} | {v_icon} | {c['tark_primary_action']} | {c['gt_primary_action']} | {a_icon} | {c['gate_passed']} | {c['tark_steps']} |")

    # Save comparison table
    with open("analysis/phase4.5_comparison_results.json", "w") as f:
        json.dump(comparisons, f, indent=2)

if __name__ == "__main__":
    compare()
