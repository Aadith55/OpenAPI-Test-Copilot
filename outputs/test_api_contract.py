"""Generated API contract tests. Review test_cases.json before running against real services."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import httpx
import pytest

BASE_URL = os.getenv("TARGET_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
CASES = json.loads((Path(__file__).parent / "test_cases.json").read_text(encoding="utf-8"))
EXECUTABLE = [c for c in CASES if c["expected"] != "manual_review"]
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}

def _assert_safe_case(case):
    path = case.get("path", "")
    if not isinstance(path, str):
        pytest.fail("Refusing to send a generated case with a non-string path")
    parsed = urlsplit(path)
    if (not path.startswith("/") or path.startswith("//")
            or parsed.scheme or parsed.netloc or "\\" in path or "\r" in path or "\n" in path):
        pytest.fail("Refusing to send a generated case to a non-relative or malformed path")
    method = case.get("method", "")
    if not isinstance(method, str) or method.upper() not in ALLOWED_METHODS:
        pytest.fail("Refusing to send a generated case with an unsupported HTTP method")
    if case.get("expected") not in {"2xx", "4xx", "401_or_403"}:
        pytest.fail("Refusing to run a case with an unsupported expected-result rule")

@pytest.mark.parametrize("case", EXECUTABLE, ids=lambda c: c["id"] + "-" + c["name"][:42])
def test_openapi_scenario(case):
    _assert_safe_case(case)
    request_kwargs = {"params": case.get("query") or {}, "headers": case.get("headers") or {}}
    if case.get("body") is not None:
        request_kwargs["json"] = case["body"]
    try:
        with httpx.Client(base_url=BASE_URL, follow_redirects=False, timeout=httpx.Timeout(15.0, connect=3.0)) as client:
            response = client.request(case["method"], case["path"], **request_kwargs)
    except httpx.HTTPError as exc:
        pytest.fail(f"{case['name']}: request to target API failed ({type(exc).__name__})")
    expected = case["expected"]
    # Do not dump raw response bodies into CI logs: errors can accidentally
    # contain tokens, personal data, or echoed request values.
    content_type = response.headers.get("content-type", "unknown")[:80]
    response_hint = f"content-type={content_type}, body-bytes={len(response.content)}"
    if expected == "2xx":
        assert 200 <= response.status_code < 300, f"{case['name']}: expected 2xx, got {response.status_code} ({response_hint})"
    elif expected == "4xx":
        assert 400 <= response.status_code < 500, f"{case['name']}: expected 4xx, got {response.status_code} ({response_hint})"
    elif expected == "401_or_403":
        assert response.status_code in {401, 403}, f"{case['name']}: expected 401/403, got {response.status_code} ({response_hint})"
