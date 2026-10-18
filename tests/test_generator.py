import json
from pathlib import Path
from testcopilot.generator import generate_scenarios, load_spec, write_outputs


def sample_spec():
    return {
        "openapi": "3.0.3",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {"operationId": "listItems", "parameters": [{"name": "limit", "in": "query", "required": True, "schema": {"type": "integer", "minimum": 1, "maximum": 100}}], "responses": {"200": {"description": "ok"}}},
                "post": {"operationId": "createItem", "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["name", "price"], "properties": {"name": {"type": "string", "minLength": 2, "maxLength": 20}, "price": {"type": "number", "minimum": 1}}}}}}, "responses": {"201": {"description": "created"}}}
            },
            "/items/{item_id}": {"get": {"operationId": "getItem", "parameters": [{"name": "item_id", "in": "path", "required": True, "schema": {"type": "integer"}}], "responses": {"200": {"description": "ok"}}}}
        }
    }


def test_generates_positive_and_negative_scenarios():
    cases = generate_scenarios(sample_spec())
    categories = {case["category"] for case in cases}
    assert "positive" in categories
    assert "required_field" in categories
    assert "invalid_type" in categories
    assert "boundary" in categories or "invalid_type_or_constraint" in categories
    assert any(case["name"] == "invalid path parameter 'item_id'" for case in cases)


def test_required_body_field_missing_scenario_is_generated():
    cases = generate_scenarios(sample_spec())
    case = next(case for case in cases if case["name"] == "omit required body field 'name'")
    assert "name" not in case["body"]
    assert case["expected"] == "4xx"


def test_output_files_are_well_formed(tmp_path):
    spec = sample_spec(); cases = generate_scenarios(spec)
    write_outputs(spec, cases, tmp_path)
    assert json.loads((tmp_path / "test_cases.json").read_text())
    assert "Test scenarios" in (tmp_path / "TEST_PLAN.md").read_text()
    generated_test = (tmp_path / "test_api_contract.py").read_text()
    compile(generated_test, "test_api_contract.py", "exec")
    summary = json.loads((tmp_path / "coverage_summary.json").read_text())
    assert summary["scenario_count"] == len(cases)


def test_load_spec_json(tmp_path):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(sample_spec()))
    assert load_spec(path)["info"]["title"] == "Test API"


def test_rejects_absolute_or_network_paths(tmp_path):
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps({"openapi": "3.0.3", "info": {"title": "Unsafe", "version": "1"}, "paths": {"https://evil.example/collect": {}}}))
    import pytest
    with pytest.raises(ValueError, match="Invalid OpenAPI path key"):
        load_spec(path)


def test_invalid_union_value_is_skipped_to_avoid_false_negative_case():
    from testcopilot.generator import invalid_value
    schema = {"anyOf": [{"type": "integer"}, {"type": "string"}]}
    assert invalid_value(schema, {}) is None


def test_recursive_nullable_schema_does_not_recurse_forever():
    from testcopilot.generator import example_for
    spec = {
        "components": {"schemas": {
            "Node": {
                "type": "object", "required": ["value", "next"],
                "properties": {
                    "value": {"type": "integer", "minimum": 1},
                    "next": {"anyOf": [{"$ref": "#/components/schemas/Node"}, {"type": "null"}]},
                },
            }
        }}
    }
    sample = example_for({"$ref": "#/components/schemas/Node"}, spec=spec)
    assert sample == {"value": 1, "next": None}


def test_generated_tests_do_not_follow_redirects_or_send_null_body():
    from testcopilot.generator import render_pytest
    generated = render_pytest([])
    assert "follow_redirects=False" in generated
    assert 'if case.get("body") is not None:' in generated
    compile(generated, "test_api_contract.py", "exec")


def test_yaml_recursive_alias_is_rejected(tmp_path):
    import pytest
    from testcopilot.generator import load_spec
    path = tmp_path / "cycle.yaml"
    path.write_text('openapi: "3.0.3"\ninfo:\n  title: Cycle\n  version: "1"\npaths: &routes\n  /x:\n    get: *routes\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Cyclic YAML aliases"):
        load_spec(path)


def test_non_json_request_body_is_marked_for_manual_review():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Uploads", "version": "1"},
        "paths": {"/upload": {"post": {
            "operationId": "upload", "requestBody": {"required": True, "content": {
                "multipart/form-data": {"schema": {"type": "object", "properties": {"file": {"type": "string"}}}}
            }}, "responses": {"201": {"description": "created"}}
        }}}
    }
    case = generate_scenarios(spec)[0]
    assert case["expected"] == "manual_review"


def test_secured_positive_request_is_not_run_without_credentials():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Secured", "version": "1"},
        "security": [{"BearerAuth": []}],
        "paths": {"/private": {"get": {"operationId": "privateRead", "responses": {"200": {"description": "ok"}}}}}
    }
    cases = generate_scenarios(spec)
    assert next(c for c in cases if c["category"] == "manual_review")["expected"] == "manual_review"
    assert next(c for c in cases if c["category"] == "security")["expected"] == "401_or_403"


def test_llm_context_excludes_examples_and_sensitive_fields():
    import json
    from testcopilot.generator import _llm_context
    spec = {
        "openapi": "3.0.3", "info": {"title": "Login", "version": "1"},
        "paths": {"/login": {"post": {
            "operationId": "login", "description": "private free-form details",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "properties": {
                    "password": {"type": "string", "example": "TOP-SECRET-PASSWORD"},
                    "displayName": {"type": "string", "example": "private-name-example"}
                }
            }}}}, "responses": {"200": {"description": "ok"}}
        }}}
    }
    safe = json.dumps(_llm_context(spec))
    assert "TOP-SECRET-PASSWORD" not in safe
    assert "private-name-example" not in safe
    assert "private free-form details" not in safe
    assert '"password"' not in safe


def test_yaml_dates_remain_json_compatible_strings(tmp_path):
    from testcopilot.generator import load_spec
    path = tmp_path / "date.yaml"
    path.write_text(
        'openapi: "3.0.3"\ninfo:\n  title: Demo\n  version: "1"\npaths:\n'
        '  /items:\n    get:\n      parameters:\n        - name: on_date\n'
        '          in: query\n          schema:\n            type: string\n'
        '            format: date\n            example: 2026-10-19\n',
        encoding="utf-8",
    )
    loaded = load_spec(path)
    example = loaded["paths"]["/items"]["get"]["parameters"][0]["schema"]["example"]
    assert example == "2026-10-19"
    assert isinstance(example, str)


def test_malformed_llm_response_falls_back_to_deterministic_cases(monkeypatch):
    from testcopilot.generator import augment_with_llm

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size=-1):
            data = b'{"choices": {"not": "a list"}}'
            return data if size < 0 else data[:size]

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("testcopilot.generator.urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())
    original = generate_scenarios(sample_spec())
    cases, note = augment_with_llm(sample_spec(), original)
    assert cases == original
    assert note and "unexpected structure" in note


def test_optional_llm_augmentation_parses_manual_review_ideas(monkeypatch):
    from testcopilot.generator import augment_with_llm

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size=-1):
            payload = {"choices": [{"message": {"content": '[{"operation_id":"listItems","method":"GET","path":"/items","name":"pagination boundary","category":"pagination","rationale":"Check limit edges"}]'}}]}
            data = json.dumps(payload).encode()
            return data if size < 0 else data[:size]

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("testcopilot.generator.urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())
    spec = sample_spec()
    cases, note = augment_with_llm(spec, generate_scenarios(spec))
    assert note is None
    assert any(case["expected"] == "manual_review" and case["name"] == "pagination boundary" for case in cases)



def test_duplicate_json_keys_are_rejected(tmp_path):
    import pytest
    path = tmp_path / "duplicate.json"
    path.write_text('{"openapi":"3.0.3","info":{"title":"A","title":"B","version":"1"},"paths":{}}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        load_spec(path)


def test_duplicate_yaml_keys_are_rejected(tmp_path):
    import pytest
    path = tmp_path / "duplicate.yaml"
    path.write_text('openapi: "3.0.3"\ninfo:\n  title: First\n  title: Second\n  version: "1"\npaths: {}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate key"):
        load_spec(path)


def test_enormous_string_and_array_constraints_do_not_allocate_huge_examples():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Bounds", "version": "1"},
        "paths": {"/submit": {"post": {
            "operationId": "submit", "requestBody": {"required": True, "content": {"application/json": {
                "schema": {"type": "object", "required": ["name"], "properties": {
                    "name": {"type": "string", "minLength": 10**12},
                    "items": {"type": "array", "minItems": 10**12, "items": {"type": "integer"}}
                }}
            }}}, "responses": {"201": {"description": "created"}}
        }}}
    }
    cases = generate_scenarios(spec)
    assert cases
    assert all(case["expected"] == "manual_review" for case in cases)


def test_inconsistent_explicit_example_is_not_called_positive():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Example validation", "version": "1"},
        "paths": {"/create": {"post": {
            "operationId": "create", "requestBody": {"required": True, "content": {"application/json": {
                "schema": {"type": "object", "required": ["name"], "properties": {
                    "name": {"type": "string", "minLength": 5, "example": "xy"}
                }}
            }}}, "responses": {"201": {"description": "created"}}
        }}}
    }
    cases = generate_scenarios(spec)
    assert cases[0]["expected"] == "manual_review"


def test_sensitive_body_example_is_never_written_to_test_cases():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Sensitive", "version": "1"},
        "paths": {"/login": {"post": {
            "operationId": "login", "requestBody": {"required": True, "content": {"application/json": {
                "schema": {"type": "object", "required": ["username", "password"], "properties": {
                    "username": {"type": "string", "example": "demo"},
                    "password": {"type": "string", "example": "TOP-SECRET"}
                }}
            }}}, "responses": {"200": {"description": "ok"}}
        }}}
    }
    cases = generate_scenarios(spec)
    assert all("TOP-SECRET" not in json.dumps(case) for case in cases)
    assert cases[0]["expected"] == "manual_review"


def test_secured_operation_does_not_generate_false_positive_validation_cases():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Protected", "version": "1"},
        "security": [{"BearerAuth": []}],
        "paths": {"/private": {"post": {
            "operationId": "privatePost", "requestBody": {"required": True, "content": {"application/json": {
                "schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
            }}}, "responses": {"201": {"description": "created"}}
        }}}
    }
    cases = generate_scenarios(spec)
    assert {case["category"] for case in cases} == {"manual_review", "security"}
    assert not any(case["expected"] == "4xx" for case in cases)


def test_generated_max_length_boundary_is_capped():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Large boundary", "version": "1"},
        "paths": {"/create": {"post": {
            "operationId": "create", "requestBody": {"required": True, "content": {"application/json": {
                "schema": {"type": "object", "required": ["name"], "properties": {
                    "name": {"type": "string", "minLength": 1, "maxLength": 10**12}
                }}
            }}}, "responses": {"201": {"description": "created"}}
        }}}
    }
    cases = generate_scenarios(spec)
    assert any(case["expected"] == "manual_review" and "bounded fixture" in case["name"] for case in cases)



def test_generated_test_diagnostics_do_not_print_raw_response_body():
    from testcopilot.generator import render_pytest
    generated = render_pytest([])
    assert "response.text[:400]" not in generated
    assert "body-bytes={len(response.content)}" in generated



def test_input_size_is_checked_against_bytes_read(tmp_path):
    import pytest
    from testcopilot.generator import MAX_SPEC_BYTES
    path = tmp_path / "too-large.json"
    path.write_bytes(b" " * (MAX_SPEC_BYTES + 1))
    with pytest.raises(ValueError, match="size limit"):
        load_spec(path)


def test_malformed_schema_becomes_manual_review_instead_of_traceback():
    spec = {
        "openapi": "3.0.3", "info": {"title": "Malformed schema", "version": "1"},
        "paths": {"/x": {"post": {
            "operationId": "create", "requestBody": {"required": True, "content": {
                "application/json": {"schema": {"type": "object", "properties": ["not", "a", "mapping"]}}
            }}, "responses": {"201": {"description": "created"}}
        }}}
    }
    cases = generate_scenarios(spec)
    assert cases and cases[0]["expected"] == "manual_review"
