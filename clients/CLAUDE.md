# clients/

Backend API wrappers. One file per backend/endpoint.

## Rules

- **Single responsibility:** each client wraps exactly one API and produces `CallResult`.
- **No retry logic here.** Retries live in `runner/execute.py`.
- **Shared parsing:** `clients/base.py::parse_bedrock_response` is the only place that converts a raw response dict → `CallResult`. All clients funnel through it.
- **Auth isolation:** `bedrock_runtime.py` and `bedrock_mantle.py` both support `auth_method` ∈ {`"iam_role"`, `"bedrock_api_key"`}. These must produce genuinely different HTTP requests (different Authorization header), not silently share boto3's credential chain.

## Files

- `base.py` — `CallResult` dataclass (frozen), `compute_cost_usd`, `parse_bedrock_response`.
- `bedrock_runtime.py` — `anthropic.AnthropicBedrock` wrapper. Uses `_build_runtime_sdk_client` to hide `AWS_BEARER_TOKEN_BEDROCK` during IAM-mode client construction.
- `bedrock_mantle.py` — raw `requests` + `SigV4Auth` with service name `bedrock-mantle`. Handles bearer vs SigV4 via `auth_method`.
- `anthropic_1p.py` — `anthropic.Anthropic` wrapper. Currently disabled at runtime (no API credits).

## Adding a new client

1. Inherit the `invoke(...)` method signature from existing clients (see `BedrockRuntimeClient.invoke`).
2. Return `CallResult` via `parse_bedrock_response` — do not construct `CallResult` directly.
3. Add a unit test of your kwargs builder (see `tests/test_bedrock_runtime.py::test_build_kwargs_*`).
4. Register in `runner/execute.py::select_client` if this is a new backend.
