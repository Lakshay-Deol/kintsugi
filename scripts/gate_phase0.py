"""Gate Phase 0: Setup and Risk-First Slice Validation."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

def check_file(rel_path: str, min_bytes: int = 10) -> bool:
    p = ROOT / rel_path
    if not p.is_file():
        print(f"FAIL: missing {rel_path}")
        return False
    size = p.stat().st_size
    if size < min_bytes:
        print(f"FAIL: {rel_path} too small ({size} bytes)")
        return False
    print(f"PASS: {rel_path} exists ({size} bytes)")
    return True

def check_embedder() -> bool:
    try:
        from kintsugi.ingest.embedder import embed_query
        vec = embed_query("test probe")
        if len(vec) == 384:
            print("PASS: fastembed embedding dimension == 384")
            return True
        print(f"FAIL: embedding dim was {len(vec)}, expected 384")
        return False
    except Exception as e:
        print(f"FAIL: embedder check failed: {e}")
        return False

def check_app_health() -> bool:
    try:
        from fastapi.testclient import TestClient
        from kintsugi.api.app import create_app
        app = create_app()
        client = TestClient(app)
        res = client.get("/health")
        if res.status_code == 200:
            data = res.json()
            if "status" in data and data.get("version"):
                print(f"PASS: /health returned 200 with status={data.get('status')} version={data.get('version')}")
                return True
        print(f"FAIL: /health returned {res.status_code}: {res.text}")
        return False
    except Exception as e:
        print(f"FAIL: /health testclient failed: {e}")
        return False

def main() -> int:
    print("=== RUNNING GATE PHASE 0 ===")
    ok = True
    ok = check_file("docs/manuals.md", 100) and ok
    ok = check_file("docs/decisions.md", 100) and ok
    ok = check_file("docs/first_user.md", 50) and ok
    ok = check_file("docs/reuse_ledger.md", 100) and ok
    ok = check_file("render.yaml", 50) and ok
    ok = check_file(".env.example", 50) and ok
    ok = check_file(".gitleaks.toml", 50) and ok
    ok = check_file("pyproject.toml", 100) and ok
    ok = check_file("LICENSE", 100) and ok
    ok = check_embedder() and ok
    ok = check_app_health() and ok

    if ok:
        print("=== GATE PHASE 0 PASSED ===")
        return 0
    else:
        print("=== GATE PHASE 0 FAILED ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())
