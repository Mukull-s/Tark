import os
import json

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_comparison():
    val_raw_path = os.path.join(WORKSPACE_ROOT, "analysis", "phase4.6.2_validation_raw_results.json")
    base_raw_path = os.path.join(WORKSPACE_ROOT, "analysis", "phase4.5_baseline_raw_results.json")

    if not os.path.exists(val_raw_path):
        print(f"Error: {val_raw_path} not found!")
        return

    if not os.path.exists(base_raw_path):
        print(f"Error: {base_raw_path} not found!")
        return

    val_results = json.load(open(val_raw_path, encoding="utf-8"))
    base_results = {r["case_id"]: r for r in json.load(open(base_raw_path, encoding="utf-8"))}

    print(f"Loaded {len(val_results)} validation results and {len(base_results)} baseline results.")

    comparisons = []
    val_correct_verdict = 0
    val_correct_nba = 0
    base_correct_verdict = 0
    base_correct_nba = 0

    val_steps_total = 0
    val_cov_total = 0.0
    val_pfraud_total = 0.0
    val_gate_pass_count = 0
    val_prec_count = 0
    val_k_count = 0

    base_steps_total = 0
    base_cov_total = 0.0
    base_pfraud_total = 0.0
    base_gate_pass_count = 0
    base_prec_count = 0
    base_k_count = 0

    for r in val_results:
        cid = r["case_id"]
        gt_path = os.path.join(WORKSPACE_ROOT, "cases", f"{cid}.json")
        if not os.path.exists(gt_path):
            print(f"Warning: Ground truth {gt_path} not found!")
            continue
        gt = json.load(open(gt_path, encoding="utf-8"))
        gt_case = gt.get("case", {})
        gt_verdict_raw = gt_case.get("verdict", "unknown")
        gt_p_fraud = gt_case.get("fraud_probability", 0.5)
        gt_actions = [a.get("action") for a in gt.get("next_best_actions", {}).get("final", [])]
        gt_primary_action = gt_actions[0] if gt_actions else "NONE"
        norm_gt_verdict = "fraud" if "fraud" in gt_verdict_raw.lower() else ("legitimate" if "cleared" in gt_verdict_raw.lower() or "legit" in gt_verdict_raw.lower() else "uncertain")

        # Validation stats
        val_p_fraud = r["final_p_fraud"]
        val_classification = r["final_classification"]
        val_primary_action = r["primary_action"]
        val_secondary_actions = r.get("secondary_actions", [])
        val_consequential_actions = r.get("consequential_actions", [])
        val_all_actions = r["policy_actions"]
        val_steps = r["evidence_steps"]
        val_cov = r["evidence_coverage"]
        val_gate = r["decision_gate_passed"]
        val_precedents = len(r.get("retrieved_precedents", []))
        val_knowledge = len(r.get("retrieved_knowledge", []))

        val_verdict_match = (val_classification == norm_gt_verdict)
        val_nba_match = (val_primary_action == gt_primary_action)
        if val_verdict_match:
            val_correct_verdict += 1
        if val_nba_match:
            val_correct_nba += 1

        val_steps_total += val_steps
        val_cov_total += val_cov
        val_pfraud_total += val_p_fraud
        if val_gate:
            val_gate_pass_count += 1
        val_prec_count += val_precedents
        val_k_count += val_knowledge

        # Baseline stats
        base_r = base_results.get(cid, {})
        base_p_fraud = base_r.get("final_p_fraud", 0.0)
        base_classification = base_r.get("final_classification", "")
        base_primary_action = base_r.get("next_best_action", "")
        base_steps = base_r.get("evidence_steps", 0)
        base_cov = base_r.get("evidence_coverage", 0.0)
        base_gate = base_r.get("decision_gate_passed", False)
        base_precedents = len(base_r.get("retrieved_precedents", []))
        base_knowledge = len(base_r.get("retrieved_knowledge", []))

        base_verdict_match = (base_classification == norm_gt_verdict)
        base_nba_match = (base_primary_action == gt_primary_action)
        if base_verdict_match:
            base_correct_verdict += 1
        if base_nba_match:
            base_correct_nba += 1

        base_steps_total += base_steps
        base_cov_total += base_cov
        base_pfraud_total += base_p_fraud
        if base_gate:
            base_gate_pass_count += 1
        base_prec_count += base_precedents
        base_k_count += base_knowledge

        comp = {
            "case_id": cid,
            "trigger_type": r["trigger_type"],
            "risk_score": r.get("risk_score"),
            "exposure_usd": r.get("exposure_usd"),
            "gt_verdict": norm_gt_verdict,
            "gt_p_fraud": gt_p_fraud,
            "gt_primary_action": gt_primary_action,
            "gt_all_actions": gt_actions,
            # Validation Phase 4.6.2
            "val_p_fraud": val_p_fraud,
            "val_verdict": val_classification,
            "val_verdict_match": val_verdict_match,
            "val_primary_action": val_primary_action,
            "val_secondary_actions": val_secondary_actions,
            "val_consequential_actions": val_consequential_actions,
            "val_all_actions": val_all_actions,
            "val_nba_match": val_nba_match,
            "val_steps": val_steps,
            "val_coverage": val_cov,
            "val_gate_passed": val_gate,
            "val_termination": r["termination_reason"],
            "val_precedents_count": val_precedents,
            "val_knowledge_count": val_knowledge,
            "val_policy_reason": r.get("policy_reason", ""),
            "val_action_recommendations": r.get("action_recommendations", []),
            "val_evidence_items": r.get("evidence_items", []),
            # Baseline Phase 4.5
            "base_p_fraud": base_p_fraud,
            "base_verdict": base_classification,
            "base_verdict_match": base_verdict_match,
            "base_primary_action": base_primary_action,
            "base_nba_match": base_nba_match,
            "base_steps": base_steps,
            "base_coverage": base_cov,
            "base_gate_passed": base_gate,
            "base_termination": base_r.get("termination_reason", ""),
            "base_precedents_count": base_precedents,
            "base_knowledge_count": base_knowledge,
        }
        comparisons.append(comp)

    n = len(comparisons)
    print("=" * 80)
    print(f"BENCHMARK COMPARISON SUMMARY (N = {n})")
    print("=" * 80)
    print(f"Metric                          Phase 4.5 Baseline    Phase 4.6.2 Validation   Delta")
    print(f"--------------------------------------------------------------------------------")
    print(f"Fraud-Label Agreement           {base_correct_verdict}/{n} ({base_correct_verdict/n*100:.1f}%)        {val_correct_verdict}/{n} ({val_correct_verdict/n*100:.1f}%)         {val_correct_verdict - base_correct_verdict:+d}")
    print(f"NBA Agreement                   {base_correct_nba}/{n} ({base_correct_nba/n*100:.1f}%)         {val_correct_nba}/{n} ({val_correct_nba/n*100:.1f}%)        {val_correct_nba - base_correct_nba:+d}")
    print(f"Decision Gate Pass Rate         {base_gate_pass_count}/{n} ({base_gate_pass_count/n*100:.1f}%)       {val_gate_pass_count}/{n} ({val_gate_pass_count/n*100:.1f}%)        {val_gate_pass_count - base_gate_pass_count:+d}")
    print(f"Avg Investigation Steps         {base_steps_total/n:.2f}                  {val_steps_total/n:.2f}                   {val_steps_total/n - base_steps_total/n:+.2f}")
    print(f"Avg Evidence Coverage           {base_cov_total/n:.4f}                {val_cov_total/n:.4f}                 {val_cov_total/n - base_cov_total/n:+.4f}")
    print(f"Avg Final P(Fraud)              {base_pfraud_total/n:.4f}                {val_pfraud_total/n:.4f}                 {val_pfraud_total/n - base_pfraud_total/n:+.4f}")
    print(f"Avg Case Precedents Retrieved   {base_prec_count/n:.2f}                  {val_prec_count/n:.2f}                   {val_prec_count/n - base_prec_count/n:+.2f}")
    print(f"Avg Knowledge Chunks Retrieved  {base_k_count/n:.2f}                  {val_k_count/n:.2f}                   {val_k_count/n - base_k_count/n:+.2f}")

    print("\nCase-by-Case NBA & Verdict Comparison:")
    print("| Case | Trigger | Base Action | Val Action (PRIMARY) | GT Action | NBA Match | Val Verdict | GT Verdict | V Match |")
    print("|---|---|---|---|---|---|---|---|---|")
    for c in comparisons:
        nba_icon = "PASS" if c["val_nba_match"] else "FAIL"
        v_icon = "PASS" if c["val_verdict_match"] else "FAIL"
        print(f"| {c['case_id']} | {c['trigger_type']} | {c['base_primary_action']} | {c['val_primary_action']} | {c['gt_primary_action']} | {nba_icon} | {c['val_verdict']} | {c['gt_verdict']} | {v_icon} |")

    out_comp_path = os.path.join(WORKSPACE_ROOT, "analysis", "phase4.6.2_comparison_results.json")
    with open(out_comp_path, "w", encoding="utf-8") as f:
        json.dump(comparisons, f, indent=2)
    print(f"\nSaved detailed comparison to {out_comp_path}")
    return comparisons

if __name__ == "__main__":
    run_comparison()
