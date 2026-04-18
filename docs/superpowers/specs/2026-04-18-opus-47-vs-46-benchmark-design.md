# Opus 4.7 vs 4.6 Benchmark — Design Spec

**Date:** 2026-04-18
**Status:** Draft — awaiting user review before implementation planning
**Goal:** Reproduce the field report (akagr-work `opus-4.7-testing/token-tests.py`) comparing Opus 4.7 vs 4.6 token consumption, latency, and cost on AWS Bedrock, with statistical rigor (5-run averaging), documented deltas versus the original report, and an auth-method comparison.

---

## Reference material

Two linked blog posts dated 2026-04-16 and 2026-04-17:

1. **Launch day report (Apr 16):** Opus 4.7 confirmed ACTIVE on Bedrock; Mantle endpoint introduced; 11 pass/fail smoke tests; 38% latency advantage on an architecture prompt.
2. **Token-overhead investigation (Apr 17):** Three token-consumption tests run against `global.` inference profiles with a Mantle cross-check. This spec reproduces those three tests plus the Mantle cross-check.

The original script path is `anthropic/opus-4.7-testing/token-tests.py` in the `akagr-work` repo. We do not have that source, so we reconstruct based on the published numbers and prose.

## Scope

**In scope (default run):**
- Test 1: Effort level vs token consumption (5 cases: 4× Opus 4.7 effort levels + 1× Opus 4.6)
- Test 2: Prompt length scaling (4 cases: 2 prompts × 2 models)
- Test 3: Parallel tool use cost (2 cases: 4.7, 4.6)
- Test 4 (mantle cross-check): Same cases as Tests 1–3 re-run via Mantle endpoint to verify identical token counts and measure latency delta
- All 3P (Bedrock) via `global.anthropic.claude-opus-4-*` inference profiles, us-east-1
- 5 runs per case with mean ± stdev
- JSON (raw + aggregated) + Markdown report

**Extension (spec-only, 3P-only):**
- Auth-method comparison: IAM role vs Bedrock API Key (`AWS_BEARER_TOKEN_BEDROCK`). Adds a small case matrix to Test 4, not a separate test.

**Out of scope (code-supported, disabled by default):**
- 1P Anthropic direct API (infrastructure exists; requires `ANTHROPIC_API_KEY` with credits — current env key has zero credits).
- Regional profiles (`us.`, `eu.`, `jp.`) — blog tests all used `global.`.
- Streaming and vision tests (launch-day blog covered these; not part of the token-overhead investigation we're reproducing).

## Key findings from pre-flight smoke test (2026-04-18)

These shaped the architecture and must be encoded in the client layer:

### Opus 4.7 thinking/effort API (new shape)

```python
client.messages.create(
    model="global.anthropic.claude-opus-4-7",
    thinking={"type": "adaptive"},
    extra_body={"output_config": {"effort": "low|medium|high|max"}},
    ...
)
```

Both `thinking.type="enabled"` and `budget_tokens` return `ValidationException` on 4.7. Verified against the running API.

### Opus 4.6 thinking API (legacy shape)

```python
client.messages.create(
    model="global.anthropic.claude-opus-4-6-v1",
    # No thinking kwarg = model's native adaptive behavior,
    # which surfaces visible thinking blocks by default (per Apr 17 blog).
    ...
)
```

### Mantle endpoint requires raw SigV4, not the SDK

The Anthropic SDK's `AnthropicBedrock(base_url=mantle_url)` signs with service name `bedrock`. Mantle rejects that — it expects service name `bedrock-mantle`. The Apr 16 blog confirms: "boto3 SDK doesn't support it natively."

**Resolution:** Mantle calls go through a hand-rolled HTTP client using `requests` + `botocore.auth.SigV4Auth` with `service_name="bedrock-mantle"` and URL path `/anthropic/v1/messages`.

### Other observed behaviors

- **Thinking chars on 4.7:** Always 0 regardless of effort, even at `max`. Confirmed.
- **Thinking chars on 4.6:** Non-zero without any explicit thinking kwarg. Confirmed.
- **Effort parameter:** Affects output tokens substantially (low=~470, max>1800 in smoke). Does not affect input tokens.
- **`AWS_BEARER_TOKEN_BEDROCK`:** Accepted by `AnthropicBedrock` transparently via boto3 credential chain. Works alongside IAM role as an alternative auth path.

## Architecture

### Directory layout

```
/home/ec2-user/my-project/Opus4.6vsOpus4.7/
├── run.py                          # CLI entry point, runs the loop
├── config.py                       # Model IDs, endpoints, pricing, effort mapping
├── clients/
│   ├── __init__.py
│   ├── base.py                     # CallResult dataclass + Client protocol
│   ├── anthropic_1p.py             # Anthropic direct (disabled by default)
│   ├── bedrock_runtime.py          # AnthropicBedrock for bedrock-runtime endpoint
│   └── bedrock_mantle.py           # Raw requests + SigV4 for bedrock-mantle endpoint
├── stats.py                        # Aggregation (mean, stdev, success rate)
├── reporter.py                     # JSON + Markdown writers
├── cases/
│   ├── __init__.py
│   ├── base.py                     # TestCase dataclass
│   ├── prompts.py                  # Shared prompt strings + tool schemas
│   ├── effort.py                   # Test 1 cases
│   ├── length.py                   # Test 2 cases
│   ├── tools.py                    # Test 3 cases
│   └── mantle.py                   # Test 4 cases
├── tests/                          # pytest unit tests (not benchmark cases)
│   ├── test_config.py
│   ├── test_stats.py
│   ├── test_clients_base.py
│   └── test_reporter.py            # Cross-endpoint + auth-method cases
├── results/
│   └── YYYY-MM-DD-HHMM/
│       ├── raw.json
│       ├── aggregated.json
│       └── report.md
├── requirements.txt                # anthropic, boto3, botocore, requests, rich
├── .env.local.example
└── .gitignore                      # .env.local, results/, __pycache__
```

### CallResult — the single measurement contract

```python
@dataclass(frozen=True)
class CallResult:
    # Measurements
    input_tokens: int
    output_tokens: int
    latency_s: float
    thinking_chars: int
    tool_calls_count: int

    # Context for grouping in the report
    backend: str                  # "1p" | "bedrock_runtime" | "bedrock_mantle"
    auth_method: str              # "api_key" | "iam_role" | "bedrock_api_key"
    model_id: str
    effort: Optional[str]
    prompt_label: str             # short identifier, e.g. "short-5w", "long-350w"

    # Debugging / auditing
    stop_reason: str
    cost_usd: float
    run_index: int
    test_id: str
    error: Optional[str] = None
```

### Client layering

**`clients/bedrock_runtime.py`** — thin wrapper around `anthropic.AnthropicBedrock`. Internally branches on model ID to send the correct thinking/effort shape:

```python
def _build_kwargs(model_id, prompt, max_tokens, effort, tools):
    kwargs = {"model": model_id, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": prompt}]}
    if tools:
        kwargs["tools"] = tools
    if "opus-4-7" in model_id and effort:
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["extra_body"] = {"output_config": {"effort": effort}}
    elif "opus-4-6" in model_id:
        # No thinking kwarg → matches blog's "adaptive+high" 4.6 behavior
        pass
    return kwargs
```

**`clients/bedrock_mantle.py`** — hand-rolled because SDK doesn't support it:

```python
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session

class BedrockMantleClient:
    URL_TEMPLATE = "https://bedrock-mantle.{region}.api.aws/anthropic/v1/messages"

    def __init__(self, region="us-east-1", auth_method="iam_role"):
        self.region = region
        self.url = self.URL_TEMPLATE.format(region=region)
        self._session = Session()
        # Credentials resolved from boto3 chain — picks up IAM role, env vars,
        # or AWS_BEARER_TOKEN_BEDROCK if supported by the chain
        self._credentials = self._session.get_credentials()

    def invoke(self, *, model_id, prompt, max_tokens, effort=None, tools=None):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if tools:
            body["tools"] = tools
        if "opus-4-7" in model_id and effort:
            body["thinking"] = {"type": "adaptive"}
            body["output_config"] = {"effort": effort}

        req = AWSRequest(method="POST", url=self.url, data=json.dumps(body),
                         headers={"Content-Type": "application/json"})
        SigV4Auth(self._credentials, "bedrock-mantle", self.region).add_auth(req)

        t0 = time.perf_counter()
        resp = requests.post(self.url, data=req.body, headers=dict(req.headers))
        latency = time.perf_counter() - t0
        resp.raise_for_status()
        # Parsing helper from clients/base.py produces CallResult; see Implementation notes.
        return _parse_bedrock_response(
            resp.json(), latency, backend="bedrock_mantle",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
        )
```

The response parser is shared with `bedrock_runtime.py` — both return the same JSON shape for `usage`, `content`, and `stop_reason`.

**`clients/anthropic_1p.py`** — wraps `anthropic.Anthropic`. Disabled unless `--backend 1p` is explicitly passed. No Mantle counterpart (Mantle is Bedrock-only).

## Config

```python
MODELS_1P = {
    "opus-4.7": "claude-opus-4-7",
    "opus-4.6": "claude-opus-4-6",
}

MODELS_3P = {
    "opus-4.7": "global.anthropic.claude-opus-4-7",
    "opus-4.6": "global.anthropic.claude-opus-4-6-v1",
}

PRICING = {  # USD per MTok — global profile pricing per Apr 16 blog
    "opus-4.7": {"input": 5.00, "output": 25.00},
    "opus-4.6": {"input": 5.00, "output": 25.00},
}

BEDROCK_REGION = "us-east-1"
MANTLE_URL = "https://bedrock-mantle.us-east-1.api.aws/anthropic/v1/messages"

DEFAULT_RUNS = 5
INTER_CALL_DELAY_S = 0.2
BACKEND_SWITCH_DELAY_S = 0.5
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_S = 2.0
```

## Test definitions

All prompts and schemas are centralized in `tests/prompts.py` for single-source-of-truth reproducibility.

### Test 1 — Effort level vs token consumption

**Prompt (exact, from Apr 17 blog):**
```
Proof that there are infinitely many primes. Full reasoning.
```

**max_tokens:** 1000 (matches blog; `effort=high` and `max` hit the cap at exactly 1000 output).

**Cases:**
| # | Model | Effort config | Blog expected input | Blog expected thinking chars |
|---|---|---|---|---|
| 1 | global Opus 4.7 | `output_config.effort=low` + `thinking.adaptive` | 37 | 0 |
| 2 | global Opus 4.7 | `effort=medium` | 37 | 0 |
| 3 | global Opus 4.7 | `effort=high` | 37 | 0 |
| 4 | global Opus 4.7 | `effort=max` | 37 | 0 |
| 5 | global Opus 4.6 | no thinking kwarg (native adaptive) | 23 | ~856 |

**Calls:** 5 × 5 runs = 25 on runtime. Plus Test 4 replay on mantle.

### Test 2 — Prompt length scaling

Prompts chosen to reflect real workloads of Claude heavy users (developers and general users). The blog numbers are a reference but NOT a strict matching target — our prompts are representative of actual use, so token counts will differ; what we reproduce is the **scaling behavior** (short vs long overhead growth).

**Short prompt (English, ~10 words — typical dev quick question):**
```
How do I center a div vertically and horizontally in CSS?
```

**Long prompt (Korean request with embedded English code, ~350 words equivalent — typical code review pattern for Korean developers):**

> 다음 Python 함수를 리뷰하고 개선 방안을 제시해 주세요. SQS 큐에서 메시지를 가져와 처리하고 실패를 다루는 백그라운드 작업 처리기를 만들고 있습니다. 테스트 환경에서는 동작하지만 프로덕션 엣지 케이스가 걱정됩니다.
>
> ```python
> import boto3, json, time, logging
> from botocore.exceptions import ClientError
>
> logger = logging.getLogger(__name__)
> sqs = boto3.client("sqs")
>
> def process_queue(queue_url, handler, max_messages=10, wait_time=20):
>     while True:
>         try:
>             resp = sqs.receive_message(
>                 QueueUrl=queue_url,
>                 MaxNumberOfMessages=max_messages,
>                 WaitTimeSeconds=wait_time,
>                 MessageAttributeNames=["All"],
>             )
>             messages = resp.get("Messages", [])
>             if not messages:
>                 continue
>             for msg in messages:
>                 try:
>                     body = json.loads(msg["Body"])
>                     handler(body)
>                     sqs.delete_message(
>                         QueueUrl=queue_url,
>                         ReceiptHandle=msg["ReceiptHandle"],
>                     )
>                 except Exception as e:
>                     logger.error(f"failed: {e}")
>         except ClientError as e:
>             logger.error(f"sqs error: {e}")
>             time.sleep(5)
> ```
>
> 특히 다음을 중점적으로 짚어 주세요: (1) handler()가 일시적 오류를 던질 때와 영구적 오류를 던질 때 — 둘을 다르게 취급해야 할까요? (2) 내부 try/except가 Exception을 광범위하게 잡는데 — 이게 워커를 중단시켜야 할 버그를 감추고 있지는 않을까요? (3) 백프레셔 처리가 없습니다; 하류 처리가 느려지면 메시지가 계속 당겨지고 visibility timeout이 처리 중간에 만료될 수 있습니다. 어떻게 고치시겠나요? (4) Graceful shutdown: SIGTERM을 받으면 (예: ECS가 컨테이너를 중지할 때) 루프가 계속 돌면서 메시지를 반쯤 처리한 상태로 남길 수 있습니다. (5) ClientError에 대한 `time.sleep(5)`는 무딘 도구입니다 — 더 견고한 재시도 전략은 무엇인가요? (6) 프로덕션에서 실제로 디버깅하려면 logging 외에 어떤 관측성을 추가해야 할까요? 구체적으로 설명하고, 상위 세 가지 권장사항에 대해 코드를 보여주세요. 전체 재작성보다 점진적 변경을 선호합니다.

**Rationale for prompt choice:**
- Short: a quintessential dev quick-question — representative of high-frequency, low-context calls.
- Long: Korean natural language + English code block — this is a very common hybrid pattern in Korean developer workflows (asking about English code in Korean). Also stresses the tokenizer on two fronts: CJK characters (Korean tokenization differences) and code (schema/symbol tokenization differences).

**max_tokens:** 400 for both prompts (blog value; short will not hit the cap, long may).

**Cases:**
| # | Model | Prompt | Expected behavior |
|---|---|---|---|
| 1 | global Opus 4.7 | short | Quick answer, <100 out, low latency |
| 2 | global Opus 4.7 | long | Structured code-review, likely hits 400 cap |
| 3 | global Opus 4.6 | short | Same shape as case 1 with fewer input tokens |
| 4 | global Opus 4.6 | long | Structured code-review, likely hits 400 cap |

**Expected token range (our workloads, not blog's):**
- Short: 4.6 ≈ 15–20 in / 4.7 ≈ 19–26 in (+25–35% overhead expected)
- Long: 4.6 ≈ 500–700 in / 4.7 ≈ 700–1000 in (+35–50% overhead expected — Korean + code compounds tokenizer differences)

**Calls:** 4 × 5 runs = 20.

### Test 3 — Parallel tool use

**Prompt (exact wording from Apr 16 blog):**
```
Look up pricing and limits for Bedrock in us-east-1 and eu-west-1.
```

**Tool schemas:**
Two tools — `get_bedrock_pricing(model_id, region)` and `get_service_quota(quota_name, region)` — defined in `prompts.py`. Single-turn only: we measure how many `tool_use` blocks the model emits, not tool execution.

**max_tokens:** 400 (blog 4.7 output=270, 4.6=211 — well under cap).

**Cases:**
| # | Model | Blog expected in / out | Blog expected parallel calls |
|---|---|---|---|
| 1 | global Opus 4.7 | 888 / 270 | 4 |
| 2 | global Opus 4.6 | 653 / 211 | 4 |

**Calls:** 2 × 5 runs = 10.

### Test 4 — Mantle cross-check + auth-method extension

Subset of Tests 1–3, re-run via Mantle endpoint to verify identical token counts and measure latency delta. Adds an auth-method column.

**Cases (runtime vs mantle × auth matrix):**
| # | Model | Endpoint | Auth method | Prompt | Effort | Tools | Purpose |
|---|---|---|---|---|---|---|---|
| 1 | Opus 4.7 | mantle | iam_role | Test 2 short | — | no | Mantle parity — short |
| 2 | Opus 4.7 | mantle | iam_role | Test 2 long | — | no | Mantle parity — long |
| 3 | Opus 4.7 | mantle | iam_role | Test 1 prompt | max | no | Mantle parity — reasoning |
| 4 | Opus 4.7 | mantle | iam_role | Test 3 prompt | — | yes | Mantle parity — tool use |
| 5 | Opus 4.7 | runtime | bedrock_api_key | Test 2 long | — | no | Auth — long (runtime) |
| 6 | Opus 4.7 | mantle | bedrock_api_key | Test 2 long | — | no | Auth — long (mantle) |
| 7 | Opus 4.7 | runtime | bedrock_api_key | Test 1 prompt | max | no | Auth — reasoning (runtime) |
| 8 | Opus 4.7 | mantle | bedrock_api_key | Test 1 prompt | max | no | Auth — reasoning (mantle) |
| 9 | Opus 4.7 | runtime | bedrock_api_key | Test 3 prompt | — | yes | Auth — tool use (runtime) |
| 10 | Opus 4.7 | mantle | bedrock_api_key | Test 3 prompt | — | yes | Auth — tool use (mantle) |

Cases 1–4 confirm token-count parity between runtime and Mantle (the blog claim). Cases 5–10 extend the auth-method comparison across Tests 1, 2, and 3 so the latency effect of `iam_role` vs `bedrock_api_key` is measured on all three representative workloads (reasoning, long prompt, tool use), on both endpoints.

Each auth-compare case has an implicit baseline counterpart:
- Case 5 pairs with Test 2 main run (long, runtime, iam_role)
- Case 6 pairs with Test 4 case 2 (long, mantle, iam_role)
- Case 7 pairs with Test 1 main case 4 (effort=max, runtime, iam_role)
- Case 8 pairs with Test 4 case 3 (effort=max, mantle, iam_role)
- Case 9 pairs with Test 3 main case 1 (tool use, runtime, iam_role)
- Case 10 pairs with Test 4 case 4 (tool use, mantle, iam_role)

**Expected findings:**
- Token counts identical runtime vs mantle.
- Mantle latency +4–14% on standard tasks, +66% on `effort=max`.
- Auth method has negligible latency impact (hypothesis; the extension verifies).

**Calls:** 10 × 5 runs = 50.

### Total call budget

| Test | Cases | Runs | Total calls |
|---|---|---|---|
| 1 | 5 | 5 | 25 |
| 2 | 4 | 5 | 20 |
| 3 | 2 | 5 | 10 |
| 4 | 10 | 5 | 50 |
| Smoke + preflight | 3 | 1 | 3 |
| **Total** | | | **108** |

**Estimated cost:** $0.80–$2.00. The `effort=max` cases dominate — one such case with 1000 output tokens × $25/MTok × 5 runs = $0.125. Test 4 now has two `effort=max` auth-compare cases (cases 7, 8) on top of Test 1's four plus Test 4 case 3, so six `effort=max` cases × $0.125 ≈ $0.75 of the total.

**Estimated duration:** 20–30 min with 200 ms inter-call delay.

## Execution flow

### CLI

```
python run.py --test all --runs 5                    # Default
python run.py --test 1,2 --runs 3                    # Subset
python run.py --test 4 --runs 5                      # Mantle only
python run.py --backend 1p --test 1 --runs 3         # 1P (requires credits)
python run.py --dry-run                              # Plan only
python run.py --report-only results/2026-04-18-1400  # Regenerate report
```

### Pre-flight

1. Load `.env.local`.
2. Validate auth paths for selected backends.
3. SDK version log.
4. Smoke call: Opus 4.6 via runtime, `max_tokens=20`, prompt `"ping"`. Abort if fails.
5. Smoke call: Opus 4.7 effort API shape detection (`thinking.adaptive + output_config.effort=low`). Log result.
6. If Mantle in scope, one smoke call via Mantle to verify SigV4 signing works.
7. Print plan: total calls, expected cost, ETA.

### Error handling

- `RateLimitError` (429) → exponential backoff 2, 4, 8s.
- 5xx → retry same.
- 4xx other → no retry, record error, continue.
- Failed run excluded from aggregation; case marked `success_rate < 1.0` in report.
- `KeyboardInterrupt` → flush partial `raw.json` and exit cleanly.

## Report format

`report.md` structure:

1. **Header:** date, SDK version, AWS region, backends used, auth methods, total calls, total cost, wall time.
2. **Pre-flight results:** smoke test pass/fail, effort API mode detected.
3. **Test 1 — Effort level:** table with `mean ± stdev` for latency and output; input should be constant. Blog expected column for comparison.
4. **Test 2 — Prompt length:** same format. Includes `delta_vs_blog` column flagging where our numbers diverge by >10%.
5. **Test 3 — Tool use:** tokens, cost per call, parallel call count. Blog expected column.
6. **Test 4 — Mantle:** runtime vs mantle side-by-side, auth method column.
7. **Summary section:** 4.7 vs 4.6 input overhead per test; confirms or refutes blog's overall conclusions (effort is not a cost dial; 4.7 is faster, not cheaper).
8. **API-shape appendix:** documents the `thinking.adaptive` + `output_config.effort` divergence.
9. **Divergence log:** any case where our numbers deviated materially from blog. Typed reasons (SDK version, prompt synthesis, account-level quirk, etc.).

`raw.json`: list of all `CallResult` objects plus metadata (start ts, end ts, SDK version, region).

`aggregated.json`: indexed by `(test_id, case_name, backend, auth_method)` with means, stdevs, success rates, and total cost.

## Reproducibility safeguards

- SDK version and timestamp logged in report header and JSON metadata.
- Prompts kept in `cases/prompts.py`; no inline strings in case modules.
- Seed used for prompt synthesis if Test 2 long-prompt generator uses any randomness (none planned, but document if added).
- Every case's full request body and response (redacted of auth headers) is dumped to `results/<ts>/calls/case_<n>_run_<i>.json` for post-hoc debugging. **Default: ON.** Use `--no-save-bodies` to disable. Rationale: forensic comparison with blog numbers is a primary goal; the bodies are small (a few KB each × ~100 calls = well under 1 MB total).

## Implementation notes (for the planning phase)

- Use `Protocol` for the Client interface — no ABC.
- `bedrock_runtime.py` and `bedrock_mantle.py` share a response-parsing helper (`_parse_response`) placed in `clients/base.py`.
- No retry logic inside client modules. Retries live in `run.py` only.
- `reporter.py` is re-runnable from `raw.json` alone — enables tweaking the report format without rerunning the expensive calls.
- Progress display: `rich.progress`. Plain fallback for non-TTY.
- Secrets: `.env.local` loaded with `python-dotenv`. Never committed. Never logged.

## Blog claims to verify (quantitative targets)

The Apr 17 blog post concludes with a summary table and a set of "practice guidance" claims. Our reproduction verifies or refutes each one. The report's summary section must restate each claim side-by-side with our measured result.

### Core claims (from blog body)

| Claim | Source | Verification target |
|---|---|---|
| Effort level does not affect input tokens | Test 1 | All four 4.7 effort cases have identical input token counts |
| 4.7 input tokens: 37 at this prompt | Test 1 | Within ±5% of 37 |
| 4.6 input tokens: 23 at this prompt | Test 1 | Within ±5% of 23 |
| 4.7 overhead on proof prompt: +61% vs 4.6 | Test 1 | 55–70% |
| 4.7 thinking chars always 0 | Tests 1, 4 | Zero on all 4.7 cases |
| 4.6 thinking chars on proof prompt: ~856 | Test 1 | Within 500–1200 |
| Short-prompt overhead: ~+25% (blog); our prompts are different so direct number match not expected | Test 2 | 20–35% overhead (trend, not absolute) |
| Long-prompt overhead: ~+45% (blog); our Korean+code prompt may show higher overhead | Test 2 | 35–55% overhead (trend, not absolute) |
| Overhead scales with prompt length (short < long) | Test 2 | Verify long overhead % > short overhead % |
| Output token counts identical at same max_tokens | Test 2 | 4.7 output == 4.6 output ± 5% (looser tolerance — different prompts than blog) |
| Tool use: 4 parallel calls on both models | Test 3 | Both emit exactly 4 tool_use blocks |
| Tool use cost premium: +31% | Test 3 | 25–40% |
| Tool use input overhead: +36% | Test 3 | 30–45% |
| Tool use output overhead: +28% | Test 3 | 22–35% |
| Mantle token counts identical to runtime | Test 4 | 100% match |
| Mantle latency +4–14% on standard tasks | Test 4 | Within 0–25% |
| Mantle effort:max latency gap: ~66% | Test 4 | 40–90% |

### Summary-table claims (from blog's final table)

"Faster" percentage convention matches the blog: `(t_4.6 − t_4.7) / t_4.6 × 100%`. Example: 4.6=10s, 4.7=5s → 50% faster. Cost premium: `(cost_4.7 − cost_4.6) / cost_4.6 × 100%`.

| Workload | Blog: 4.7 latency advantage | Blog: 4.7 cost premium | Our verification target |
|---|---|---|---|
| Short prompt | +51% faster | +5% more expensive | Latency 40–65% faster; cost premium 0–15% |
| Long prompt | +55% faster | +5% more expensive | Latency 45–70% faster; cost premium 0–15% |
| Reasoning | +46% faster | Comparable | Latency 35–60% faster; cost premium −5 to +10% |
| Tool use | +26% faster | +31% more expensive | Latency 18–35% faster; cost premium 25–40% |

### Practice-guidance claims (qualitative → report assertions)

The blog states several qualitative guidance claims in "What this means in practice". Our report must address each, marked with Confirmed / Refuted / Not tested:

- "Effort level is not a cost dial" — **Confirmed** if Test 1 shows identical input tokens across effort levels.
- "4.7 is faster, not cheaper" — **Confirmed** if all four workloads in the summary table show latency advantage and cost premium simultaneously.
- "Tool use has the widest cost gap because tool schemas inflate input" — **Confirmed** if Test 3 cost premium is the largest of the four workloads.
- "Visible reasoning chains only on 4.6" — **Confirmed** if 4.6 thinking_chars > 0 in every relevant case while 4.7 thinking_chars == 0.

## Acceptance criteria

Implementation is complete when:

- [ ] `python run.py --dry-run` prints a plan matching the "Total call budget" table (108 calls).
- [ ] `python run.py --test all` runs to completion without unhandled exceptions and produces `raw.json`, `aggregated.json`, `report.md`.
- [ ] All claims in the "Blog claims to verify" table above are evaluated in the report — each with a pass/fail status and the measured value next to the blog value.
- [ ] Divergences from blog numbers are documented in the Divergence log with at least a reasoned hypothesis (SDK version, prompt wording, account quirk, etc.).
- [ ] The report's final section restates the blog's "When to use 4.6 instead" / "When 4.7 wins" decision guide and marks each bullet Confirmed / Refuted / Insufficient data based on our runs.

## Review decisions (approved 2026-04-18)

1. **Test 2 prompts:** ✅ Finalized — short is an English CSS quick-question; long is a Korean code-review request with embedded English Python code (realistic Korean developer pattern). Blog numbers demoted to "reference only" per user direction; we reproduce the *scaling behavior* (short vs long overhead growth), not absolute token counts.
2. **Test 4 auth-method cases:** ✅ Expanded to cover Tests 1, 2, 3 on both endpoints (cases 5–10 added). +20 calls, total 108.
3. **`--save-bodies` default:** ✅ ON by default. `--no-save-bodies` to disable.
4. **Test 4 `effort=max` on mantle × 5 runs:** ✅ Approved. Cost contribution ~$0.125 × 5 = $0.625 per case; two such cases (cases 3 and 8) ≈ $1.25 of total budget.
