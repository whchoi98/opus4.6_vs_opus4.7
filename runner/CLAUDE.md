# runner/

Orchestration layer. Owns the benchmark loop, retries, and case dispatch.

## Rules

- **All retry logic lives here.** Specifically in `execute.py::execute_case_with_retry`. Client modules must not retry.
- **Client instances are cached** per `(backend, auth_method)` tuple in `execute.py::_CLIENT_CACHE`. New auth method → new cached instance.
- **Streaming is a separate invoke path.** `_invoke_case` dispatches to `client.invoke_streaming()` when `case.streaming=True`, else `client.invoke()`.

## Files

- `preflight.py` — `load_env()` loads `.env.local`; `check_auth_env({"bedrock", "1p"})` validates.
- `dispatch.py` — `TEST_MODULES` maps test IDs to case modules; `collect_cases(selected)` flattens.
- `execute.py` — `select_client` (cache), `_backoff_seconds`, `_invoke_case` (route to invoke/invoke_streaming), `execute_case_with_retry` (main loop with exponential backoff on 5xx / RateLimitError).

## Retry policy

- `anthropic.RateLimitError` → retry with exponential backoff (2s, 4s, 8s...)
- `anthropic.APIStatusError` with 5xx → retry same
- `requests.HTTPError` with 5xx → retry same (Mantle path)
- 4xx and other exceptions → break immediately, return `CallResult` with `error` set

## Config knobs (in `config.py`)

- `RETRY_MAX_ATTEMPTS` (default 3)
- `RETRY_BACKOFF_BASE_S` (default 2.0)
- `INTER_CALL_DELAY_S` (default 0.2)
- `BACKEND_SWITCH_DELAY_S` (default 0.5)
