from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_is_versioned():
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "AdaptiveLearn AI API"


def test_health_reports_every_dependency():
    r = client.get("/api/v1/health")
    assert r.status_code in (200, 503)
    assert set(r.json()) == {"database", "redis", "r2"}


def test_test_only_routes_are_not_mounted_outside_test_env():
    import subprocess
    import sys

    code = (
        "import os; os.environ['ENVIRONMENT']='development';"
        "from app.main import app;"
        "print(any('__test__' in getattr(r, 'path', '') for r in app.routes))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
