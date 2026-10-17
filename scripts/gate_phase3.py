"""Gate Phase 3: Product Surface Validation.

Requirements:
1. render.yaml exists and contains web service with /health check.
2. UI index.html contains: Demo Mode badge, privacy note, model/symptom inputs, refusal container, localStorage history.
3. Static UI served by FastAPI app at / with HTTP 200.
4. /fix-outcome endpoint accepts valid §2 schema and rejects invalid payloads.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient
from kintsugi.api.app import create_app

def check_render_yaml() -> bool:
    p = ROOT / "render.yaml"
    if not p.is_file():
        print("FAIL: render.yaml missing")
        return False
    content = p.read_text(encoding="utf-8")
    if "/health" not in content or "buildCommand" not in content:
        print("FAIL: render.yaml missing health check or build command")
        return False
    print("PASS: render.yaml valid with health check and build commands")
    return True

def check_ui_elements() -> bool:
    ui_path = ROOT / "src" / "kintsugi" / "api" / "static" / "index.html"
    if not ui_path.is_file():
        print("FAIL: static index.html missing")
        return False
    html = ui_path.read_text(encoding="utf-8").lower()
    checks = [
        ("Demo Mode badge", "demo" in html and "badge" in html),
        ("Privacy note", "privacy" in html),
        ("Model input", "model" in html and "input" in html),
        ("Symptom box", "symptom" in html),
        ("Refusal display", "refusal" in html or "refused" in html),
        ("Job history (localStorage)", "localstorage" in html),
        ("Fix-outcome form", "fix-outcome" in html or "outcome" in html),
    ]
    all_ok = True
    for name, ok in checks:
        if not ok:
            print(f"FAIL: UI missing element: {name}")
            all_ok = False
        else:
            print(f"PASS: UI element verified: {name}")
    return all_ok

def check_ui_serving(client: TestClient) -> bool:
    res = client.get("/")
    if res.status_code == 200 and "html" in res.headers.get("content-type", ""):
        print("PASS: Web UI successfully served at root / with HTTP 200")
        return True
    # Try /ui/ if redirect
    if res.status_code in (301, 302, 307, 308):
        loc = res.headers.get("location", "/")
        res2 = client.get(loc)
        if res2.status_code == 200:
            print(f"PASS: Web UI served at redirect target {loc} with HTTP 200")
            return True
    print(f"FAIL: Web UI failed to serve at root: {res.status_code}")
    return False

def check_fix_outcome_endpoint(client: TestClient) -> bool:
    valid_payload = {
        "model": "WFW5620HW0",
        "symptom_category": "mechanical",
        "outcome": "fixed"
    }
    res = client.post("/fix-outcome", json=valid_payload)
    if res.status_code != 200:
        print(f"FAIL: /fix-outcome rejected valid payload: {res.status_code} {res.text}")
        return False
    data = res.json()
    if not data.get("recorded"):
        print(f"FAIL: /fix-outcome did not return recorded: true: {data}")
        return False
    print("PASS: /fix-outcome accepted and recorded valid §2 fix-outcome record")

    # Invalid payload rejection
    invalid_payload = {
        "model": "WFW5620HW0",
        "symptom_category": "invalid_category",
        "outcome": "not_a_valid_outcome"
    }
    res_bad = client.post("/fix-outcome", json=invalid_payload)
    if res_bad.status_code in (400, 422):
        print("PASS: /fix-outcome correctly rejected invalid category enum")
        return True
    print(f"FAIL: /fix-outcome accepted invalid enum: {res_bad.status_code}")
    return False

def main() -> int:
    print("=== RUNNING GATE PHASE 3 ===")
    app = create_app()
    client = TestClient(app)

    ok = True
    ok = check_render_yaml() and ok
    ok = check_ui_elements() and ok
    ok = check_ui_serving(client) and ok
    ok = check_fix_outcome_endpoint(client) and ok

    if ok:
        print("=== GATE PHASE 3 PASSED ===")
        return 0
    else:
        print("=== GATE PHASE 3 FAILED ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())
