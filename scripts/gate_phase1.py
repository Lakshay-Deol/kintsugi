"""Gate Phase 1: Data Layer Validation.

Requirements:
1. evidence/phase1_chunks.json exists and has non-zero chunk counts for each manual.
2. 5 test questions return expected gold pages in top-k.
3. Filtered search returns only chunks for the requested brand/model.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from kintsugi.retrieval.search import hybrid_search, vector_search

def check_evidence_file() -> bool:
    path = ROOT / "evidence" / "phase1_chunks.json"
    if not path.is_file():
        print("FAIL: evidence/phase1_chunks.json missing")
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if len(data) < 3:
            print(f"FAIL: expected at least 3 manuals in evidence, got {len(data)}")
            return False
        for item in data:
            if item.get("chunk_count", 0) <= 0:
                print(f"FAIL: manual {item.get('manual_id')} has 0 chunks")
                return False
            print(f"PASS: manual {item.get('manual_id')} ({item.get('model')}) has {item.get('chunk_count')} chunks")
        return True
    except Exception as e:
        print(f"FAIL: invalid evidence JSON: {e}")
        return False

def check_model_isolation() -> bool:
    # Test that querying for Whirlpool WFW5620HW0 returns ONLY Whirlpool chunks
    hits, _, _ = hybrid_search("drain pump error filter", "Whirlpool", "WFW5620HW0")
    if not hits:
        print("FAIL: no hits returned for model isolation test")
        return False
    for h in hits:
        if h.get("model") != "WFW5620HW0":
            print(f"FAIL: leakage detected! Got chunk from model {h.get('model')}")
            return False
    print(f"PASS: model isolation verified ({len(hits)} hits all belonging to WFW5620HW0)")
    return True

def check_gold_pages() -> bool:
    test_cases = [
        ("What does error code F5E2 mean on my washer?", "Whirlpool", "WFW5620HW0", [4]),
        ("How to clean the drain pump coin trap filter?", "Whirlpool", "WFW5620HW0", [7, 11]),
        ("How do I enter service mode on washer?", "GE", "GTW685BSLWS", [3]),
        ("What does error code E18 or drain pump blocked mean?", "Bosch", "WAT28400UC", [4]),
        ("What is the resistance of the water heating element?", "Bosch", "WAT28400UC", [6]),
    ]

    all_passed = True
    for query, brand, model, gold_pages in test_cases:
        hits, vec_score, bm25_score = hybrid_search(query, brand, model)
        retrieved_pages = [h.get("page") for h in hits]
        hit = any(p in retrieved_pages for p in gold_pages)
        if hit:
            print(f"PASS: '{query[:40]}...' -> found gold page in {retrieved_pages}")
        else:
            print(f"FAIL: '{query[:40]}...' -> gold {gold_pages} not in {retrieved_pages}")
            all_passed = False
    return all_passed

def main() -> int:
    print("=== RUNNING GATE PHASE 1 ===")
    ok = True
    ok = check_evidence_file() and ok
    ok = check_model_isolation() and ok
    ok = check_gold_pages() and ok

    if ok:
        print("=== GATE PHASE 1 PASSED ===")
        return 0
    else:
        print("=== GATE PHASE 1 FAILED ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())
