# OpenAPI Test Copilot

A developer tool that turns an OpenAPI contract into a reviewable API test plan and an executable pytest suite. It creates a deterministic schema-based baseline offline and can optionally ask an OpenAI-compatible LLM for additional *manual-review* edge-case ideas.

## Why it is useful

- Parses OpenAPI 3 JSON or YAML operations, parameters, and request-body schemas.
- Builds representative valid requests from examples, enums, formats, and schema constraints.
- Adds negative scenarios for missing required fields, invalid types/formats, path parameter violations, and boundary constraints.
- Exports `test_cases.json`, `TEST_PLAN.md`, a parameterized `test_api_contract.py`, and a category-level `coverage_summary.json`.
- Optional LLM augmentation proposes up to eight further scenarios; LLM suggestions are marked `manual_review` and never silently become passing/failing assertions.
- Includes unit tests and an example OpenAPI contract from the companion marketplace demo.
- Rejects duplicate JSON/YAML keys, caps input/operation counts and generated example sizes, validates inferred examples against known constraints, and avoids emitting secret-like body examples into generated files.

## Run the example

Python 3.11+ is recommended.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m testcopilot.cli examples/marketplace.openapi.json --out outputs
```

The CLI is offline by default. Read `outputs/TEST_PLAN.md` and inspect/edit `outputs/test_cases.json` before running the generated tests. The loader applies file-size, nesting, node-count, and route checks. Recursive, malformed, secret-bearing, oversized, or unsupported schema shapes are marked for manual review instead of being treated as executable positive cases. Very large string/array bounds never trigger allocation of enormous example payloads.

## Run tests

```bash
python -m pytest -q
```

## Run generated tests against a running API

Start the companion marketplace demo on `http://127.0.0.1:8000`, then in this project's `outputs` directory run:

```bash
TARGET_BASE_URL=http://127.0.0.1:8000 pytest -q -s test_api_contract.py
```

On PowerShell:

```powershell
$env:TARGET_BASE_URL = "http://127.0.0.1:8000"
pytest -q -s test_api_contract.py
```

Because the generator uses schema-level heuristics, some APIs need test data setup or operation-specific expectations. It intentionally skips successful automated cases when credentials, custom serialization, recursive schema examples, unsupported constraints, or explicit success responses are missing. For secured operations without a credential fixture, only the missing-auth check is executable; other checks are left for credentialed manual setup rather than passing because the API returned 401. Generated tests do not follow redirects, do not send empty JSON bodies on body-less operations, validate that paths are relative before making requests, apply connect/request timeouts, and avoid printing raw response bodies into test logs.

**Never point generated tests at production by default.** Cases can issue mutating `POST`, `PUT`, `PATCH`, or `DELETE` requests to the configured target. Use a disposable local/test environment and seed/reset its data. Status-only expectations are a smoke/contract baseline, not a substitute for response-schema and business-invariant assertions.

## Optional LLM augmentation

The deterministic baseline always runs without a model or API key. To request extra ideas through an OpenAI-compatible Chat Completions endpoint:

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1" # optional
export OPENAI_MODEL="gpt-4o-mini"                # optional
python -m testcopilot.cli examples/marketplace.openapi.json --out outputs-ai --ai
```

A compatible local gateway can be used by changing `OPENAI_BASE_URL`. Keep credentials out of source control. With `--ai`, the tool sends a minimized summary of route names, operation identifiers, and schema constraints; descriptions, examples, defaults, and fields whose names look like credentials are omitted. Route names can still reveal internal API structure, so do not use the external LLM option with confidential API specifications unless approved. LLM-generated cases are suggestions only and require review.

## Design boundaries

- Only local `$ref` references are resolved. Remote references are not fetched; recursive, pattern-constrained, and `allOf` schemas may need hand-authored examples.
- The generator does not execute model-generated code; it asks for structured test ideas only.
- HTTP expectations are broad (`2xx`, `4xx`, `401_or_403`) and should be refined for the target service.
- Non-JSON request bodies and complex parameter serialization are marked for manual review.
- This is a test generation assistant, not proof of complete API coverage or correctness.
