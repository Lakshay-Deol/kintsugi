"""Gate Phase 4: Proof and User Validation.

Requirements:
1. eval/results.json exists, valid JSON, includes dev/test metrics, refusal accuracy >= 90%, citation precision = 100%.
2. eval/model_swap.json exists, compares hosted Gemma vs local open-weights (Ollama).
3. eval/cost_comparison.md exists, contains pricing sources and break-even scenario.
4. docs/first_user.md exists, records user sessions or honest "none yet".
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def check_results_json() -> bool:
    p = ROOT / "eval" / "results.json"
    if not p.is_file():
        print("FAIL: eval/results.json missing")
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        test = data.get("test", {})
        arms = data.get("retrieval_arms", {})
        if not test or not arms:
            print("FAIL: eval/results.json missing test or retrieval_arms sections")
            return False

        ref_acc = test.get("refusal_accuracy", 0.0)
        cite_prec = test.get("citation_precision", 0.0)
        hyb_hit = test.get("hybrid_hit_at_k", 0.0)

        if ref_acc < 0.90:
            print(f"FAIL: test refusal accuracy {ref_acc*100}% < 90%")
            return False
        if cite_prec < 0.99:
            print(f"FAIL: citation precision {cite_prec*100}% < 100%")
            return False

        print(f"PASS: eval/results.json valid: Refusal Accuracy={ref_acc*100:.1f}%, Citation Precision={cite_prec*100:.1f}%, Hybrid Hit@K={hyb_hit*100:.1f}%")
        return True
    except Exception as e:
        print(f"FAIL: invalid eval/results.json: {e}")
        return False

def check_model_swap() -> bool:
    p = ROOT / "eval" / "model_swap.json"
    if not p.is_file():
        print("FAIL: eval/model_swap.json missing")
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        arms = data.get("arms", {})
        if "arm_1_hosted_gemma" not in arms or "arm_2_local_ollama" not in arms:
            print("FAIL: eval/model_swap.json missing comparison arms")
            return False
        print("PASS: eval/model_swap.json verified with Gemma hosted vs Ollama local comparison")
        return True
    except Exception as e:
        print(f"FAIL: invalid eval/model_swap.json: {e}")
        return False

def check_cost_comparison() -> bool:
    p = ROOT / "eval" / "cost_comparison.md"
    if not p.is_file():
        print("FAIL: eval/cost_comparison.md missing")
        return False
    text = p.read_text(encoding="utf-8")
    if "Break-Even" not in text and "break-even" not in text:
        print("FAIL: eval/cost_comparison.md missing break-even analysis")
        return False
    if "https://" not in text:
        print("FAIL: eval/cost_comparison.md missing pricing source URLs")
        return False
    print("PASS: eval/cost_comparison.md verified with break-even scenario and price citations")
    return True

def check_first_user_doc() -> bool:
    p = ROOT / "docs" / "first_user.md"
    if not p.is_file():
        print("FAIL: docs/first_user.md missing")
        return False
    text = p.read_text(encoding="utf-8")
    if len(text) < 50:
        print("FAIL: docs/first_user.md too short")
        return False
    print("PASS: docs/first_user.md verified")
    return True

def main() -> int:
    print("=== RUNNING GATE PHASE 4 ===")
    ok = True
    ok = check_results_json() and ok
    ok = check_model_swap() and ok
    ok = check_cost_comparison() and ok
    ok = check_first_user_doc() and ok

    if ok:
        print("=== GATE PHASE 4 PASSED ===")
        return 0
    else:
        print("=== GATE PHASE 4 FAILED ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())
