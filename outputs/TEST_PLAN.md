# API Test Plan: Marketplace Discovery & Order Engine

- OpenAPI version: `3.1.0`
- Service version: `1.0.0`
- Generated scenarios: **27**

## Coverage summary

| Category | Cases |
|---|---:|
| Boundary | 5 |
| Invalid Type | 2 |
| Invalid Type Or Constraint | 7 |
| Positive | 6 |
| Required Field | 7 |

## Test scenarios

| ID | Operation | Scenario | Expectation |
|---|---|---|---|
| TC-748D4D | `GET /health` | valid representative request | `2xx` |
| TC-7A6D9B | `POST /listings` | valid representative request | `2xx` |
| TC-E721C6 | `POST /listings` | omit required body field 'title' | `4xx` |
| TC-24B25C | `POST /listings` | omit required body field 'category' | `4xx` |
| TC-83009C | `POST /listings` | omit required body field 'seller' | `4xx` |
| TC-911E10 | `POST /listings` | omit required body field 'price' | `4xx` |
| TC-7E1C76 | `POST /listings` | omit required body field 'quantity' | `4xx` |
| TC-7F5636 | `POST /listings` | invalid value for body field 'title' | `4xx` |
| TC-E44891 | `POST /listings` | overlength body field 'title' | `4xx` |
| TC-437528 | `POST /listings` | invalid value for body field 'description' | `4xx` |
| TC-37FF31 | `POST /listings` | overlength body field 'description' | `4xx` |
| TC-D95B9A | `POST /listings` | invalid value for body field 'category' | `4xx` |
| TC-FA08E2 | `POST /listings` | overlength body field 'category' | `4xx` |
| TC-634A0B | `POST /listings` | invalid value for body field 'seller' | `4xx` |
| TC-9F3942 | `POST /listings` | overlength body field 'seller' | `4xx` |
| TC-37139A | `POST /listings` | invalid value for body field 'item_condition' | `4xx` |
| TC-81B12B | `POST /listings` | invalid value for body field 'quantity' | `4xx` |
| TC-7E83EA | `POST /listings` | below-minimum body field 'quantity' | `4xx` |
| TC-0F9969 | `GET /listings` | valid representative request | `2xx` |
| TC-00C182 | `GET /listings/1` | valid representative request | `2xx` |
| TC-2C7F7F | `GET /listings/not-an-integer` | invalid path parameter 'listing_id' | `4xx` |
| TC-A7FD66 | `POST /orders` | valid representative request | `2xx` |
| TC-451714 | `POST /orders` | omit required header 'Idempotency-Key' | `4xx` |
| TC-C7ED07 | `POST /orders` | omit required body field 'items' | `4xx` |
| TC-E9EB1E | `POST /orders` | invalid value for body field 'items' | `4xx` |
| TC-439607 | `GET /orders/1` | valid representative request | `2xx` |
| TC-27532F | `GET /orders/not-an-integer` | invalid path parameter 'order_id' | `4xx` |

## How to execute generated tests

1. Start the API under test.
2. Set `TARGET_BASE_URL` to its base URL (default `http://127.0.0.1:8000`).
3. Run `pytest -q test_api_contract.py` from this output directory.
4. Review any `manual_review` scenarios before converting them to automated assertions.

## Interpretation notes

- Test data and generated inputs are examples inferred from the OpenAPI schema; they may need endpoint-specific setup.
- A passing schema-derived request is not proof of business correctness. Add stateful tests for inventory, permissions, and cross-resource invariants.
- Some malformed paths are expected to be routed differently across frameworks; review observed results rather than blindly weakening assertions.
