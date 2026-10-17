"""Gate Phase 2: Retrieval, Safety and Answers Validation.

Requirements:
1. Every unanswerable question is refused BEFORE an LLM call:
   - Unknown model -> MODEL_NOT_FOUND
   - Out-of-manual query -> LOW_RELEVANCE or NO_MODEL_EVIDENCE
   - Hazard procedure query (gas/refrigerant) -> HAZARD_REFERRAL
2. No answer cites a page outside its retrieved set (programmatic check of citation_check()).
3. /answer endpoint functions with status, answer, citations, reason_code, warnings.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient
from kintsugi.api.app import create_app
from kintsugi.safety.gates import citation_check

def check_unanswerable_refusals(client: TestClient) -> bool:
    unanswerable_cases = [
        # (model, symptom, expected_reason)
        ("NON_EXISTENT_WASHER_999", "washer won't turn on", "MODEL_NOT_FOUND"),
        ("WFW5620HW0", "how to bake sourdough bread in washer", "LOW_RELEVANCE"),
        ("WFW5620HW0", "repair natural gas leak line pipe", "HAZARD_REFERRAL"),
        ("GTW685BSLWS", "recharge freon refrigerant r134a compressor leak", "HAZARD_REFERRAL"),
    ]

    all_passed = True
    for model, symptom, expected_reason in unanswerable_cases:
        payload = {"model_number": model, "symptom": symptom}
        res = client.post("/answer", json=payload)
        if res.status_code != 200:
            print(f"FAIL: /answer returned {res.status_code} for {payload}")
            all_passed = False
            continue
        data = res.json()
        status = data.get("status")
        reason = data.get("reason_code")
        if status != "refused":
            print(f"FAIL: expected refused for {payload}, got status={status}")
            all_passed = False
        elif expected_reason and reason != expected_reason:
            print(f"FAIL: expected reason={expected_reason}, got {reason} for {payload}")
            all_passed = False
        else:
            print(f"PASS: correctly refused ({reason}): '{symptom[:35]}...' [model={model}]")
    return all_passed

def check_citation_precision() -> bool:
    # Test citation check strips pages not in retrieved set
    retrieved_chunks = [
        {"page": 3, "text": "service mode"},
        {"page": 4, "text": "door lock error"},
    ]
    # Claimed citations include page 4 (valid) and page 99 (invalid hallucination)
    claimed = [
        {"page": 4, "claim": "check DL3 connector", "excerpt": "DL3 connector"},
        {"page": 99, "claim": "replace motor on page 99", "excerpt": "invalid page"},
    ]
    result = citation_check(claimed, retrieved_chunks)
    if 99 in [c.get("page") for c in result.valid_citations]:
        print("FAIL: citation check allowed invalid page 99 to pass!")
        return False
    if 99 not in result.stripped_pages:
        print("FAIL: citation check failed to record page 99 in stripped_pages")
        return False
    if len(result.valid_citations) != 1 or result.valid_citations[0].get("page") != 4:
        print("FAIL: valid citation page 4 was not preserved")
        return False
    print("PASS: citation_check correctly stripped ungrounded page 99 and kept valid page 4")
    return True

def check_answerable_response(client: TestClient) -> bool:
    payload = {"model_number": "WFW5620HW0", "symptom": "error code F5E2 door lock"}
    res = client.post("/answer", json=payload)
    if res.status_code != 200:
        print(f"FAIL: /answer returned {res.status_code}")
        return False
    data = res.json()
    if not data.get("answer"):
        print("FAIL: empty answer in response")
        return False
    citations = data.get("citations", [])
    print(f"PASS: answerable query returned status={data.get('status')} with {len(citations)} citations")
    return True

def main() -> int:
    print("=== RUNNING GATE PHASE 2 ===")
    app = create_app()
    client = TestClient(app)

    ok = True
    ok = check_unanswerable_refusals(client) and ok
    ok = check_citation_precision() and ok
    ok = check_answerable_response(client) and ok

    if ok:
        print("=== GATE PHASE 2 PASSED ===")
        return 0
    else:
        print("=== GATE PHASE 2 FAILED ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())
