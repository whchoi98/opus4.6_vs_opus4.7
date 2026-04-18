# Test Results — Opus 4.7 vs 4.6 Bedrock Benchmark

[![Tests run](https://img.shields.io/badge/benchmark%20runs-4-brightgreen)](#)
[![Calls executed](https://img.shields.io/badge/API%20calls-409-blue)](#)
[![Total cost](https://img.shields.io/badge/total%20cost-%247.14-yellow)](#)
[![Active tests](https://img.shields.io/badge/tests-11%20active%20%2B%202%20deferred-orange)](#)
[![Unit tests](https://img.shields.io/badge/pytest-62%20passing-brightgreen)](#)
[![English](https://img.shields.io/badge/language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/language-한국어-red)](#한국어)

Consolidated results across four benchmark runs on 2026-04-18 against AWS Bedrock (us-east-1), covering 13 test dimensions plus a quality scorer with two methodologies (fixed position and randomized A/B).

AWS Bedrock(us-east-1)에서 2026-04-18에 수행된 4회의 벤치마크 실행 결과를 통합한 문서로, 13개 테스트 차원과 두 가지 방법론(고정 포지션 / A-B 랜덤화)으로 진행된 품질 스코어러 결과를 포함합니다.

Each test is documented in four sections — **Purpose**, **Method**, **Findings**, **Implications** — so readers can skim for decisions or drill down for details. 각 테스트는 **목적 / 테스트 방법 / 주요 발견 / 시사점** 네 섹션으로 구성되어 있어, 독자는 의사결정용 요약만 훑거나 세부 사항으로 내려갈 수 있습니다.

---

# English

## Executive Summary

Opus 4.7 is 25–40 percent faster than 4.6 across nearly all measured workloads, at an input-token premium that varies from +5 percent on Korean prose to +57 percent on English technical prose. Effort level does not reduce input token consumption — all four 4.7 effort variants consumed identical input tokens (σ = 0) on the same prompt. Four substantive findings emerged across the full suite: (1) at 20 tools, 4.7 stops invoking tools unless forced via `tool_choice`; (2) 4.7 exhibits a sudden +16 percent latency step at turn 20; (3) Korean tokenization overhead is nearly null; (4) Bedrock does not surface prompt caching usage fields in SDK responses, making caching cost measurement unverifiable in this environment.

Our quality scorer, using Claude Sonnet 4.6 as a judge with A/B position randomization, found 4.6 winning 9 of 15 pairwise comparisons. The verdict is confounded by a 69 percent position-A bias and by max_tokens-based truncation that disadvantages the more verbose 4.7. The signal is real but narrower than the raw counts suggest: 4.7 is more verbose and setup-oriented; 4.6 reaches conclusions faster when truncated.

## Methodology (common framework)

All tests follow a single execution pipeline. Case modules under `cases/` return pure `TestCase` data; the runner at `runner/execute.py` iterates each case N times with retry and exponential backoff; the client layer at `clients/` wraps the Anthropic Bedrock SDK for the Runtime endpoint and performs raw SigV4-signed HTTP for the Mantle endpoint; results stream into a unified `CallResult` record for aggregation.

**Target models and endpoints:**

- `global.anthropic.claude-opus-4-7` and `global.anthropic.claude-opus-4-6-v1` inference profiles in `us-east-1`
- Bedrock Runtime endpoint via the Anthropic SDK (`anthropic.AnthropicBedrock`)
- Bedrock Mantle endpoint via raw `requests` with `botocore.auth.SigV4Auth`, service name `bedrock-mantle`

**Per-call measurements** captured into `CallResult` (`clients/base.py`): `input_tokens`, `output_tokens`, `latency_s`, `thinking_chars`, `tool_calls_count`, `cache_creation_tokens`, `cache_read_tokens`, `ttft_s`, `stop_reason`, `cost_usd`.

**Aggregation** (`stats.py`): mean and sample standard deviation per case, with error runs excluded from means but counted in `n_runs`.

**Run durations and costs:**

| Run | Date/Time (UTC) | Tests | Calls | Wall time | Cost |
|---|---|---|---|---|---|
| 1 | 2026-04-18 06:03 | 1, 2, 3, 4 | 95 of 105 | 9m 55s | $1.16 |
| 2 | 2026-04-18 07:02 | 5, 6, 7, 8 | 100 of 100 | 8m 18s | $1.31 |
| 3 | 2026-04-18 07:47 | 9, 10, 11, 12 | 140 of 140 | 14m 27s | $3.75 |
| 4 | 2026-04-18 08:18 | 13 | 50 of 50 | 4m 46s | $0.86 |
| Scorer v1 | 2026-04-18 07:05 | 3 prompts × 3 runs | 9 | 2m 10s | $0.01 |
| Scorer v2 | 2026-04-18 08:07 | 3 prompts × 5 runs | 15 | 3m 25s | $0.06 |
| **Total** | | | **409** | **~43 min** | **~$7.14** |

Run 1 showed 10 errored calls in Test 4 Mantle cases because the test account lacks Mantle endpoint allowlisting.

---

## Test 1 — Effort Level versus Token Consumption

### Purpose

Measure whether the `effort` parameter reduces input token consumption. Users often reach for `effort=low` as a cost-control lever; this test validates that intuition.

### Method

**Case file:** `cases/effort.py`. **Prompt:** `"Proof that there are infinitely many primes. Full reasoning."` (`cases/prompts.py::PROOF_PROMPT`). **max_tokens:** 1000. **Runs per case:** 5.

Five cases, one per (model, effort) combination:

| Case | Model | Effort | API parameters |
|---|---|---|---|
| 1 | Opus 4.7 | low | `thinking={"type": "adaptive"}` + `extra_body={"output_config": {"effort": "low"}}` |
| 2 | Opus 4.7 | medium | same shape, `effort="medium"` |
| 3 | Opus 4.7 | high | same shape, `effort="high"` |
| 4 | Opus 4.7 | max | same shape, `effort="max"` |
| 5 | Opus 4.6 | — | no `thinking` parameter (native mode) |

The 4.7 API shape divergence from 4.6 is handled in `clients/bedrock_runtime.py::build_kwargs`:

```python
if "opus-4-7" in model_id and effort:
    kwargs["thinking"] = {"type": "adaptive"}
    kwargs["extra_body"] = {"output_config": {"effort": effort}}
```

### Findings

| Model | Effort | Input | Output (μ±σ) | Latency (μ±σ s) | Thinking chars |
|---|---|---|---|---|---|
| Opus 4.7 | low | 32 | 970 ± 66 | 11.26 | 0 |
| Opus 4.7 | medium | 32 | 1000 ± 0 | 9.79 | 0 |
| Opus 4.7 | high | 32 | 1000 ± 0 | 14.78 | 0 |
| Opus 4.7 | max | 32 | 1000 ± 0 | 11.46 | 0 |
| Opus 4.6 | — | 21 | 809 ± 40 | 13.78 | 0 |

- Input tokens are identical (σ = 0) across the four 4.7 effort variants. The effort parameter does not affect input consumption.
- 4.7 vs 4.6 input overhead on this prompt is +52 percent.
- Thinking blocks returned zero characters for all cases in this SDK response configuration.

### Implications

- **Effort is not an input-cost dial.** To reduce 4.7's input bill, shorten the prompt, change its composition (see Test 11), or enable caching when Bedrock supports it (see Tests 5 and 12). Lowering effort does nothing for input cost.
- Effort does control output depth and latency — at `effort=max`, 4.7 consistently emits the full 1000-token output and takes longer overall. Use effort as a quality/latency lever, not a cost one.

---

## Test 2 — Prompt Length Scaling

### Purpose

Quantify how input-token overhead scales with prompt length, contrasting a short English query against a longer Korean-and-code hybrid. Establishes that overhead is not a single flat percentage.

### Method

**Case file:** `cases/length.py`. **max_tokens:** 400. **Runs per case:** 5.

Two prompts:

- **Short** (`cases/prompts.py::SHORT_PROMPT`): `"How do I center a div vertically and horizontally in CSS?"` (~10 English words)
- **Long** (`cases/prompts.py::LONG_PROMPT`): a Korean natural-language request to review an embedded Python SQS worker, roughly 350 words of mixed Korean prose and English code

Four cases: 2 prompts × 2 models. Both models share the same kwargs shape for this test (no effort parameter).

### Findings

| Prompt | Model | Input | Output | Latency | 4.7 overhead |
|---|---|---|---|---|---|
| Short (English CSS) | 4.7 | 30 | 300 | 5.35 s | +43% |
| Short (English CSS) | 4.6 | 21 | 400 | 6.29 s | — |
| Long (Korean + code) | 4.7 | 988 | 400 | 5.27 s | +13% |
| Long (Korean + code) | 4.6 | 872 | 400 | 8.59 s | — |

- Overhead ratio depends heavily on content type: +43 percent on a short English question versus +13 percent on a longer Korean-plus-code hybrid.
- 4.7 was 38 percent faster on the long prompt (5.27 s vs 8.59 s).
- Both models hit `max_tokens` on the long prompt.

### Implications

- **Content composition matters more than length alone.** Test 11 decomposes this observation: the Korean content, not the length, is what closes the gap.
- **For mixed-content workloads, overhead estimates based on pure-English benchmarks are too pessimistic.** Real Korean-developer workflows likely pay less than the headline "+45%" suggests.
- Longer prompts amortize the per-call latency advantage of 4.7 more clearly, so the interactive experience favors 4.7 as prompts grow.

---

## Test 3 — Parallel Tool Use (baseline)

### Purpose

Establish baseline parallel tool-use behavior on a simple two-tool prompt that both models should handle trivially. Provides context for Test 8's scaling study and for Test 9's forcing comparison.

### Method

**Case file:** `cases/tools.py`. **Prompt** (`cases/prompts.py::TOOL_USE_PROMPT`): `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` **max_tokens:** 400. **Runs per case:** 5.

Two tool schemas attached via the `tools` kwarg (`cases/prompts.py::TOOLS_SCHEMA`):

1. `get_bedrock_pricing(model_id, region)` — returns on-demand pricing
2. `get_service_quota(quota_name, region)` — returns quota value

Cases: one per model. Single-turn only — the test measures how many `tool_use` blocks the model emits in its first response. **No tool execution round-trip** is performed; we never feed `tool_result` back.

Tool-call counting is done in `clients/base.py::parse_bedrock_response` by iterating the response `content` array and counting blocks where `type == "tool_use"`.

### Findings

| Model | Input | Output | Latency | Tool calls emitted | Cost |
|---|---|---|---|---|---|
| Opus 4.7 | 1040 | 239 | 4.50 s | **0** (stop_reason: `end_turn`) | $0.056 |
| Opus 4.6 | 776 | 318 | 4.43 s | 4 | $0.059 |

- Opus 4.6 emitted the expected four parallel `tool_use` blocks (pricing and quota lookups for both regions).
- Opus 4.7 answered in plain text from its own knowledge without invoking any tools.

### Implications

- This is the first observation of a tool-refusal pattern. Test 8 then characterizes how the pattern scales with tool-menu size, and Test 9 identifies reliable ways to force tool use.
- For small tool menus (≤ 2) the refusal can happen even when the prompt is action-oriented; relying on 4.7 to "just use the tools" is fragile.


---

## Test 4 — Bedrock Runtime versus Mantle, with Auth Comparison

### Purpose

Verify that Bedrock's Mantle endpoint produces identical token counts to Runtime, and separately measure the latency impact of IAM role versus Bedrock bearer-token authentication on both endpoints.

### Method

**Case file:** `cases/mantle.py`. **Cases:** 10. **Runs per case:** 5.

The case matrix crosses endpoint (Runtime vs Mantle) with auth method (IAM vs bearer token), using prompts borrowed from Tests 1, 2, 3 as representative workloads:

| # | Model | Endpoint | Auth | Prompt | Effort |
|---|---|---|---|---|---|
| 1–4 | 4.7 | Mantle | iam_role | Short / Long / Proof / Tool use | max on proof |
| 5–6 | 4.7 | Runtime / Mantle | bedrock_api_key | Long prompt | — |
| 7–8 | 4.7 | Runtime / Mantle | bedrock_api_key | Proof prompt | max |
| 9–10 | 4.7 | Runtime / Mantle | bedrock_api_key | Tool use | — |

Mantle calls cannot use the Anthropic SDK directly because the SDK signs requests with service name `bedrock`, which Mantle rejects. `clients/bedrock_mantle.py` handles this with hand-rolled SigV4:

```python
aws_req = AWSRequest(method="POST", url=MANTLE_URL, data=data,
                     headers={"Content-Type": "application/json"})
SigV4Auth(credentials, "bedrock-mantle", region).add_auth(aws_req)
resp = requests.post(MANTLE_URL, data=aws_req.body, headers=dict(aws_req.headers))
```

When `auth_method="bedrock_api_key"`, SigV4 is skipped entirely; the client sends `Authorization: Bearer <token>` directly.

### Findings

Of 50 calls, 30 Mantle calls failed with HTTP 404. The test account lacks the preview allowlisting Mantle requires. Runtime cases succeeded but the separation of IAM versus bearer-token auth paths landed in a later commit, so the auth-method comparison in this run is inconclusive.

### Implications

- **Mantle access requires explicit account allowlisting.** Plan for this lead time when architecting around Mantle features (Projects, OpenAI-compatible API).
- **The test harness is ready for re-execution** once Mantle access is granted — the `bedrock_mantle.py` client, case matrix, and auth-method isolation are all in place.
- No actionable conclusion about token parity or auth-method latency from this run.

---

## Test 5 — User Prompt Caching (deferred)

### Purpose

Measure whether user-prompt caching on Bedrock returns observable cache-hit signals via the Anthropic SDK, and estimate the cost impact of a warm cache on repeated prompts.

### Method

**Case file:** `cases/caching.py`. **Cases:** 2. **Runs per case:** 5. **max_tokens:** 200.

The prompt is `LONG_PROMPT` concatenated with itself to guarantee the total stays above the 1024-token minimum that Anthropic documents for ephemeral caching. The user message uses the content-list form with a `cache_control` marker:

```python
messages = [{
    "role": "user",
    "content": [{
        "type": "text",
        "text": prompt,
        "cache_control": {"type": "ephemeral"},
    }],
}]
```

Across the 5 runs, the first call should write the cache (`cache_creation_input_tokens > 0`, `cache_read_input_tokens = 0`) and subsequent calls within the ~5-minute TTL should read it (`cache_creation = 0`, `cache_read > 0`).

Cost calculation in `clients/base.py::compute_cost_usd` applies the documented multipliers (1.25x input rate for writes, 0.10x for reads) when cache fields are non-zero.

### Findings

All 10 calls returned `cache_creation_input_tokens = 0` and `cache_read_input_tokens = 0`. The `cache_control` payload was accepted without error — Bedrock neither rejected the marker nor surfaced the cache fields in the response.

### Implications

- **Bedrock prompt caching is unobservable** in this SDK configuration as of the test date. Either the response schema does not expose these fields via the Anthropic SDK, or the feature is not generally available for these models on Bedrock yet.
- **Production caching cost assumptions on Bedrock are currently unverifiable.** Tests 6, 10, and 13 (multi-turn) report per-call costs without any caching discount, which may be pessimistic once Bedrock surfaces cache signals.
- Test 12 repeats the experiment on the system-prompt path to check whether it behaves differently. The infrastructure in `CallResult` and `compute_cost_usd` is ready for the day Bedrock starts returning the fields.

Case excluded from the default `--test all` run; runnable explicitly with `--test 5`.

---

## Test 6 — Multi-turn Conversation Scaling (1–10 turns)

### Purpose

Measure how input tokens and latency scale with conversation turn count across the typical chatbot range of 1 to 10 turns.

### Method

**Case file:** `cases/multiturn.py`. **Cases:** 8. **Runs per case:** 5. **max_tokens:** 300.

A curated 9-pair conversation about planning a weekend trip from Seoul to Sokcho is stored as `_TURNS` in the case module. Each pair is a `(user_text, assistant_text)` tuple of roughly 50 tokens combined, on a coherent theme so the only variable across cases is turn count (not per-turn response verbosity).

For a given turn count n, the message list is built by `_build_messages`:

```python
msgs = []
for user_text, asst_text in _TURNS[:n_turns]:
    msgs.append({"role": "user", "content": user_text})
    msgs.append({"role": "assistant", "content": asst_text})
msgs.append({"role": "user", "content": final_user_msg})
```

The final user message is always "Given everything we've discussed, please write me a single-day itinerary for Saturday with times." Cases pass the constructed list via the `messages_override` field on `TestCase`, bypassing the default single-message wrapping in `build_kwargs`.

Variants: turn count ∈ {1, 3, 5, 10} × 2 models = 8 cases.

### Findings

| Turns | 4.6 input | 4.7 input | 4.7 overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 1 | 107 | 150 | +40% | 5.30 s | 4.77 s |
| 3 | 297 | 437 | +47% | 7.49 s | 4.05 s |
| 5 | 491 | 721 | +47% | 7.81 s | 4.05 s |
| 10 | 879 | 1263 | +44% | 6.81 s | 4.05 s |

- Input overhead is flat in the +40–47 percent band throughout this range.
- Opus 4.7 latency plateaus at approximately 4.05 s from turn 3 onward.
- Opus 4.6 latency grows with history length.
- At 10 turns, Opus 4.7 is 40 percent faster than Opus 4.6.

### Implications

- **Multi-turn agent pipelines favor 4.7 more strongly than single-turn benchmarks suggest.** A 40 percent latency gap compounds across a long user session.
- **Below 10 turns, 4.7 latency is essentially free of session-length penalty.** Chatbot designers can plan around a consistent ~4-second response budget.
- Test 13 then drills into the 10-to-20 boundary to see when the plateau breaks.

---

## Test 7 — Streaming Time-to-First-Token (TTFT)

### Purpose

Measure streaming TTFT — the metric that dominates perceived latency in interactive chat, IDE, and voice contexts where users see output arrive incrementally, rather than waiting for the full response.

### Method

**Case file:** `cases/streaming.py`. **Cases:** 4. **Runs per case:** 5. **max_tokens:** 300.

The runner uses `BedrockRuntimeClient.invoke_streaming`, which calls `messages.stream()` instead of `messages.create`. TTFT is captured at the first `content_block_delta` event:

```python
t0 = time.perf_counter()
ttft = None
with self._client.messages.stream(**kwargs) as stream:
    for event in stream:
        if ttft is None and getattr(event, "type", None) == "content_block_delta":
            ttft = time.perf_counter() - t0
    final_message = stream.get_final_message()
```

The measured `ttft` is attached to the `CallResult.ttft_s` field. Variants: Short and Long prompts from Test 2 × 2 models = 4 cases.

### Findings

| Model | Short prompt TTFT | Long prompt TTFT |
|---|---|---|
| Opus 4.7 | 1.15 ± 0.10 s | 1.15 ± 0.18 s |
| Opus 4.6 | 1.46 ± 0.11 s | 1.59 ± 0.21 s |
| 4.7 advantage | 21% faster | 28% faster |

- Opus 4.7 TTFT is invariant to prompt length, holding at 1.15 seconds across both short and long inputs.
- Opus 4.6 TTFT grows with prompt length (1.46 s → 1.59 s).
- The streaming-mode latency gap is larger than the end-to-end latency gap in many other tests.

### Implications

- **TTFT is 4.7's strongest UX lever.** A consistent 1.15-second first-token latency is the differentiator for chat, autocomplete, and voice workflows, where users feel the first-token delay acutely.
- **4.6's TTFT penalty grows with prompt size**, so workloads with long system prompts or large contexts widen the gap further than these tests measure.
- Total response time is a less differentiated metric; teams should measure TTFT specifically when evaluating model choice for interactive UX.

---

## Test 8 — Tool Schema Scaling (1 / 5 / 20 tools)

### Purpose

Measure how input-token overhead and tool-invocation behavior change as the number of available tools grows from 1 to 20 — the range a production agent might expose via MCP servers, Claude Code extensions, or similar.

### Method

**Case file:** `cases/tools_scaling.py`. **Cases:** 6. **Runs per case:** 5. **max_tokens:** 400.

Tools are generated at runtime with a uniform shape so the only variable is count:

```python
def _synth_tool(i):
    return {
        "name": f"query_service_{i:02d}",
        "description": f"Query AWS service {i:02d} metadata including pricing, quotas, and availability in a given region...",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string", "description": f"..."},
                "region":      {"type": "string", "description": "..."},
                "detail_level": {"type": "string", "enum": ["summary", "detailed", "full"]},
            },
            "required": ["resource_id", "region"],
        },
    }
```

The same prompt from Test 3 is used with tool counts n ∈ {1, 5, 20} across both models.

### Findings

| Tools | 4.6 input | 4.7 input | 4.7 overhead | 4.6 calls | 4.7 calls |
|---|---|---|---|---|---|
| 1 | 696 | 938 | +35% | 2.0 | 2.0 |
| 5 | 1372 | 1826 | +33% | 5.0 | 0.6 |
| 20 | 3907 | 5156 | +32% | 5.0 | 0.0 |

- Input overhead is flat at +32–35 percent regardless of tool count. Schema size does not amplify per-token overhead.
- Opus 4.7 progressively abandons tools as the menu grows, reaching zero invocations at 20 tools on this prompt.
- Opus 4.6 maintains 5 parallel tool calls from 5 tools upward.

### Implications

- **For large tool menus, 4.7 is unreliable without additional guardrails.** Agent frameworks that expose many tools (MCP, agent-orchestration, Claude Code) must plan for this.
- **Overhead per tool is stable**, so the input-cost effect of adding tools is predictable even if the invocation rate is not.
- Test 9 identifies `tool_choice={"type": "any"}` as a reliable fix and quantifies its trade-off.


---

## Test 9 — Tool Forcing

### Purpose

Determine whether imperative prompting or the `tool_choice` API parameter can correct the 4.7 tool-refusal pattern observed at scale in Test 8, and quantify any side effects.

### Method

**Case file:** `cases/tool_forcing.py`. **Cases:** 8. **Runs per case:** 5.

The 20-tool menu from Test 8 is reused across four forcing strategies:

| Variant | Prompt | `tool_choice` parameter |
|---|---|---|
| passive | `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` (baseline) | none |
| imperative | `"You must use the available tools to look up pricing and limits..."` | none |
| choice-any | baseline prompt | `{"type": "any"}` |
| choice-specific | baseline prompt | `{"type": "tool", "name": "query_service_00"}` |

When set, `tool_choice` is forwarded through `build_kwargs`:

```python
if tool_choice is not None:
    kwargs["tool_choice"] = tool_choice
```

Four variants × 2 models = 8 cases.

### Findings

| Variant | 4.6 tool_calls | 4.7 tool_calls |
|---|---|---|
| passive | 5.0 | 0.0 |
| imperative | 4.0 | 1.2 (3 of 5 runs returned 0) |
| choice-any | 2.0 | 2.0 |
| choice-specific | 2.0 | 2.0 |

- `tool_choice={"type": "any"}` fully resolves 4.7's tool refusal — 5 of 5 runs emit tools consistently.
- Imperative prompting alone is unreliable on 4.7 (40 percent compliance).
- `tool_choice` reduces parallel tool-use block count from 5 (4.6 passive) to 2 in both models. This is a trade-off between invocation guarantee and parallelism.

### Implications

- **Production agent frameworks should integrate `tool_choice` into the loop when using 4.7 at scale.** Passive prompts and imperative prompts are both insufficient.
- **There is a parallelism cost**: `tool_choice="any"` appears to cap parallel invocations at 2 in our observations. If maximum tool fan-out matters, keep the menu small enough that 4.6's passive behavior still works, or sequence calls across multiple turns.
- The `choice-specific` variant shows that forcing a named tool is possible but only useful when the workflow can commit to a specific next step.

---

## Test 10 — Multi-turn Extreme (10 / 20 / 30 / 50 / 100 turns)

### Purpose

Extend Test 6's multi-turn curve into extreme territory (up to 100 turns) to see whether 4.7's latency plateau holds or breaks down at long sessions.

### Method

**Case file:** `cases/multiturn_extreme.py`. **Cases:** 10. **Runs per case:** 5. **max_tokens:** 300.

The message-list builder from Test 6 is extended with a synthetic turn generator. When n > 9 (the size of the curated `_TURNS` list), additional pairs are produced procedurally on a coherent travel-planning theme:

```python
def _synth_turn(i):
    topics = ["food recommendations", "best photo spots", "weather concerns",
              "packing list", "transport options", "budget breakdown", ...]
    topic = topics[i % len(topics)]
    user_q = f"Can you elaborate on {topic} for this trip..."
    asst_a = "Three specific suggestions: (1) prioritize the highest-rated..."
    return user_q, asst_a
```

Variants: turn count n ∈ {10, 20, 30, 50, 100} × 2 models = 10 cases. The 100-turn case packs 201 messages (100 user/assistant pairs plus one final user prompt) into a single call.

### Findings

| Turns | 4.6 input | 4.7 input | 4.7 overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 10 | 999 | 1447 | +45% | 6.73 s | 3.95 s |
| 20 | 2117 | 3181 | +50% | 6.64 s | 4.99 s |
| 30 | 3239 | 4915 | +52% | 6.62 s | 5.04 s |
| 50 | 5489 | 8393 | +53% | 8.14 s | 5.24 s |
| 100 | 11095 | 17063 | +54% | 7.69 s | 5.75 s |

- Overhead climbs modestly from +45 percent at 10 turns to +54 percent at 100 turns.
- 4.7 retains a 25–40 percent latency advantage throughout the range.
- The largest single delta in the 4.7 latency curve is between turn 10 (3.95 s) and turn 20 (4.99 s).

### Implications

- **4.7 remains the faster choice at session lengths up to 100 turns.** The absolute latency gap persists even after the turn-20 transition.
- **Cost premium grows gradually** with session length; plan budgets for +50–55 percent overhead on long sessions.
- Test 13 then identifies the exact point where the 4.7 latency curve transitions.

---

## Test 11 — Language and Code Decomposition

### Purpose

Decompose Test 2's mixed-content overhead into its language (English vs Korean) and code components, to identify which factor dominates. This is the data point most relevant to Korean developers planning production workloads.

### Method

**Case file:** `cases/language_code.py`. **Cases:** 8. **Runs per case:** 5. **max_tokens:** 400.

Four prompt variants of similar substantive size (each drawn from `cases/prompts.py`):

| Variant | Content |
|---|---|
| english | ~350-word English prose architecture review |
| korean | same topic, Korean natural-language prose |
| code | ~350-line Python asyncio SQS worker |
| korean_code | Korean prose with an embedded Python code block (`LONG_PROMPT`) |

Four variants × 2 models = 8 cases.

### Findings

| Variant | 4.6 input | 4.7 input | Overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| English prose | 389 | 610 | **+57%** | 11.26 s | 5.62 s |
| Korean prose | 962 | 1010 | **+5%** | 8.81 s | 5.12 s |
| Python code | 1260 | 1622 | **+29%** | 10.49 s | 4.83 s |
| Korean + code hybrid | 872 | 988 | **+13%** | 8.34 s | 4.54 s |

- Korean prose tokenizes almost identically on both models (+5 percent) — the lowest overhead across the four content types.
- English technical prose shows the highest overhead (+57 percent), 11x the Korean figure.
- Code-only prompts land at +29 percent, roughly halfway between Korean and English.
- Opus 4.7 is 1.7x to 2.2x faster than Opus 4.6 across all four content types.

### Implications

- **Korean-heavy workloads barely pay the 4.7 premium.** A Korean chatbot with minimal English content pays roughly +5 percent; a code-review agent reading mostly Korean developer questions with embedded code pays around +13 percent.
- **English-heavy batch workloads are where 4.6 is genuinely cheaper**; at +57 percent overhead, high-volume English processing may still justify 4.6.
- **A single overhead number is misleading.** Teams should profile their own prompt mix rather than relying on any published headline figure.

---

## Test 12 — System Prompt Caching (deferred)

### Purpose

Check whether system-prompt caching — a distinct API path from user-prompt caching tested in Test 5 — returns observable cache signals on Bedrock. System prompts are the most commercially valuable caching target because they are long, stable, and reused across thousands of calls per agent session.

### Method

**Case file:** `cases/system_caching.py`. **Cases:** 2. **Runs per case:** 5. **max_tokens:** 400.

A ~2000-token "agent operating instructions" system prompt (`cases/prompts.py::SYSTEM_PROMPT_LONG`) is attached via the `system` parameter in list-of-content-blocks form with a `cache_control` marker:

```python
kwargs["system"] = [{
    "type": "text",
    "text": SYSTEM_PROMPT_LONG,
    "cache_control": {"type": "ephemeral"},
}]
```

A short user message triggers the actual generation on each run. Expected behavior: first call writes the system prompt to cache; runs 2–5 read it.

### Findings

Same null result as Test 5: `cache_creation_input_tokens = 0` and `cache_read_input_tokens = 0` across all 10 calls, on both models.

### Implications

- **Bedrock prompt caching is not observable in this SDK configuration on either the user or system prompt path.** Teams planning Bedrock deployments should not assume the documented caching cost model until Bedrock surfaces these fields.
- The infrastructure is ready for when Bedrock adds support; no code changes will be needed to start measuring it.

Case excluded from the default `--test all` run; runnable with `--test 12`.

---

## Test 13 — Multi-turn Knee-point (11 / 13 / 15 / 17 / 19 turns)

### Purpose

Fill the 10-to-20-turn resolution gap between Tests 6 and 10 to precisely locate where 4.7's latency plateau transitions to a higher regime.

### Method

**Case file:** `cases/multiturn_knee.py`. **Cases:** 10. **Runs per case:** 5. **max_tokens:** 300.

Uses the same `_build_messages_extended` generator as Test 10. Only the turn-count set changes.

Variants: turn count n ∈ {11, 13, 15, 17, 19} × 2 models = 10 cases.

### Findings

Combining Tests 6, 13, and 10 into a single series for Opus 4.7:

| Turns | 4.7 latency | Δ from previous |
|---|---|---|
| 10 | 3.95 s | — |
| 11 | 3.97 s | +0.5% |
| 13 | 3.74 s | −5.8% (local minimum) |
| 15 | 4.07 s | +8.8% |
| 17 | 4.18 s | +2.7% |
| 19 | 4.32 s | +3.3% |
| 20 | 4.99 s | **+15.5%** |
| 30 | 5.04 s | +1.0% |

- Below turn 20, 4.7 latency oscillates within a tight 3.74–4.32 second band.
- At turn 20, a single-turn increment produces a 0.68-second jump (+15.5%).
- Above turn 20, the curve resumes a gradual climb (about +1% per turn).
- Opus 4.6 shows no comparable step; its latency oscillates in the 6.6–7.2 second range across this span.

### Implications

- **4.7 latency is a step function, not a smooth curve.** Below turn 20, designers can plan around a consistent 4-second budget. At turn 20, plan for a jump to 5 seconds, after which the curve remains gradual.
- **The step shape suggests an internal regime switch** — possibly a context-buffer or KV-cache tier threshold — rather than linear degradation. The specific mechanism is unknown without Anthropic internal data.
- Agent designers looking to avoid the step should consider session summarization or compaction when history approaches the 20-turn boundary.

---

## Quality Scorer Results

### Purpose

Evaluate response quality as a check on whether the cost and latency gains of 4.7 come with quality regressions. Token counts and latencies alone miss cases where a faster answer is wrong or incomplete.

### Method

**File:** `scorers/judge.py`. CLI entry: `score.py`.

Three steps per comparison:

1. Invoke both Opus 4.7 and Opus 4.6 with the same prompt (and tools when present); capture response texts.
2. Send both responses to Claude Sonnet 4.6 as Response A and Response B with a judge system prompt asking for a pairwise verdict.
3. Parse the judge's `VERDICT: <A_better | B_better | tie>` and map back to model labels.

Two scorer runs:

- **V1 — Fixed position**: Opus 4.7 always Response A, Opus 4.6 always Response B. 3 prompts (`tools`, `short`, `proof`) × 3 runs = 9 judgements.
- **V2 — A/B randomized**: position of 4.7 randomized per call; `position_of_47` and `raw_verdict` recorded to diagnose bias. 3 prompts × 5 runs = 15 judgements.

V2 implementation:

```python
position_of_47 = "A" if rng.random() < 0.5 else "B"
if position_of_47 == "A":
    response_a, response_b = text_47, text_46
else:
    response_a, response_b = text_46, text_47
# ... ask judge, then remap:
verdict = _remap_verdict(raw_verdict, position_of_47)
```

### Findings

**V1 (fixed position):**

| Prompt | 4.7 wins | 4.6 wins | Tie |
|---|---|---|---|
| tools | 1 | 2 | 0 |
| short | 1 | 2 | 0 |
| proof | 0 | 3 | 0 |
| **Total (9 runs)** | **2 (22%)** | **7 (78%)** | 0 |

**V2 (randomized):**

| Prompt | 4.7 wins | 4.6 wins | Tie |
|---|---|---|---|
| tools | 2 | 3 | 0 |
| short | 0 | 3 | 2 |
| proof | 2 | 3 | 0 |
| **Total (15 runs)** | **4 (27%)** | **9 (60%)** | 2 (13%) |

Position-bias diagnostic for V2: Response A won 9 of 13 non-tie cases (69%), indicating moderate judge bias toward position A.

### Implications

- **Opus 4.6 is preferred in roughly 60 percent of comparisons even after randomization.** The preference is real but narrower than the V1 fixed-position result suggested.
- **`max_tokens=400` truncation disproportionately hurts 4.7's more verbose style.** 4.7 tends to invest tokens in preamble or structured setup; when the cap clips the response before the conclusion, the judge sees an incomplete answer.
- **Verbosity interacts with output constraints.** For terse-output APIs (cards, summaries, JSON with strict length), 4.6 may be the better fit. For long-form analysis where verbosity is a feature, 4.7's structured preamble becomes an advantage.

---

## Decision Matrix

| Workload | Prefer 4.7 | Prefer 4.6 | Primary evidence |
|---|---|---|---|
| Korean customer support chatbot | yes | — | Test 11: +5% overhead, 1.7x speed |
| Claude Code (code-heavy) | yes | — | Test 11: +29% overhead, 2.2x speed |
| Large toolset agent (10+ tools) | yes with `tool_choice` | yes otherwise | Tests 8, 9 |
| Long-running agent session (5–19 turns) | yes | — | Tests 6, 13: flat 4-second plateau |
| Long-running agent session (20+ turns) | yes with compaction | yes | Tests 10, 13: post-step 5–6 s |
| Streaming chatbot / IDE | yes | — | Test 7: TTFT 1.15 s invariant |
| Terse-output API (max_tokens ≤ 400) | — | yes | Scorer: 4.7 truncation disadvantage |
| Long-form structured analysis | yes | — | Scorer: 4.7 preamble adds structure |
| English batch processing / RAG | — | yes | Test 11: +57% cost on English |
| Reasoning / math | either | either | Test 1: cost parity |

## Limitations

- **Mantle endpoint inaccessible** in the test account; Test 4 parity claims cannot be evaluated here.
- **Prompt caching unobservable** on Bedrock in this SDK configuration; Tests 5 and 12 deferred.
- **Single-region testing** (us-east-1); other regional inference profiles untested.
- **Sample size**: 5 runs per case is small for low-variance metrics but standard practice for LLM benchmarks. 15 runs for the scorer is smaller still; inferences about quality should be treated as directional.
- **Position bias** in the scorer (Response A preference 69 percent) was detected but not fully corrected for; the absolute win counts likely over-represent Opus 4.6 by several percentage points.
- **Single judge model** (Sonnet 4.6); a different judge could produce different preferences.
- **`max_tokens=400` truncation artifact** in several tests favors the terser model; workloads with generous token budgets may produce different rankings.

## Reproducibility

All raw data is preserved in `results/YYYY-MM-DD-HHMM/raw.json` with full per-call metadata including SDK version, region, auth method, and request body dumps. The harness is idempotent: `python3 run.py --test all --runs 5` produces the same structure of results on any account with the same model access. Costs and latencies are the only non-deterministic outputs; token counts are stable across runs.

## Consolidated Insights

Eight takeaways synthesize the full test matrix:

1. **Effort is not a cost dial.** The `effort` parameter controls output depth but leaves input tokens untouched. If you want to reduce 4.7's bill, shorten the prompt or cache it — lowering effort does nothing for input cost.
2. **Korean tokenizes at parity; English and code pay the overhead.** A +5 percent overhead on Korean prose versus +57 percent on English technical prose is the widest spread in the measured dimension. Workload language matters more than any single configuration knob.
3. **Latency advantage grows with session length.** At turn 1, 4.7 is 10 percent faster; at turn 3 it is 46 percent faster; at turn 100 it is 25 percent faster. The absolute gap persists even after the knee, so longer sessions favor 4.7.
4. **TTFT is 4.7's strongest UX lever.** A 1.15-second TTFT invariant to prompt length is the hardest-to-replace advantage for chat and IDE workflows. Total response time is less differentiated.
5. **Large tool menus require `tool_choice`.** On a 20-tool prompt, 4.7 emits zero tool calls under passive prompting and only 1.2 of 5 under imperative prompting. `tool_choice={"type": "any"}` makes it reliable at the cost of reduced parallelism (5 calls → 2).
6. **Latency has a step at turn 20, not a smooth curve.** Below 20 turns, 4.7 latency oscillates in a tight 3.7–4.3 second band. At turn 20 it jumps to 4.99 seconds in a single increment. The gradual curve resumes above 20, suggesting an internal regime switch rather than linear degradation.
7. **Bedrock caching is unobservable in this SDK configuration.** Both user-prompt and system-prompt caching tests returned zero cache-creation and zero cache-read tokens across 10 and 10 calls respectively. The observed per-call costs cannot be discounted by any caching assumption until this is resolved.
8. **Quality is directionally similar; verbosity artifacts favor 4.6 under tight token caps.** A position-randomized judge preferred 4.6 in 60 percent of comparisons. The effect is amplified by `max_tokens=400` truncation that cuts 4.7's more verbose responses before they reach a conclusion. Workloads with generous token budgets are likely closer to parity on quality.

---


# 한국어

## 요약 (Executive Summary)

Opus 4.7은 측정된 거의 모든 워크로드(workload)에서 4.6보다 25~40퍼센트 빠르며, 입력 토큰(input token) 프리미엄은 한국어 산문에서 +5퍼센트부터 영문 기술 산문에서 +57퍼센트까지 분포합니다. 노력 수준(effort level)은 입력 토큰 소비를 줄이지 않습니다 — 4개의 4.7 effort 변형(variant) 모두가 동일 프롬프트에서 완전히 같은 입력 토큰 수를 소비했습니다(표준편차 σ = 0). 전체 스위트(suite)에서 다음 네 가지 실질적 발견이 도출되었습니다. (1) 도구(tool) 20개 환경에서 4.7은 `tool_choice`로 강제하지 않는 한 도구를 호출하지 않습니다. (2) 4.7은 턴(turn) 20에서 지연 시간(latency)이 +16퍼센트 급상승하는 계단 함수(step function)를 보입니다. (3) 한국어 토큰화(tokenization) 오버헤드(overhead)는 거의 0에 가깝습니다. (4) Bedrock은 SDK 응답에 프롬프트 캐싱(prompt caching) 사용량 필드를 노출하지 않아, 이 환경에서 캐싱 비용 측정이 불가능합니다.

Claude Sonnet 4.6을 평가자(judge)로 사용하고 A/B 위치를 무작위화한 품질 채점기(quality scorer)에서는 15회의 쌍별 비교(pairwise comparison) 중 9회에서 4.6이 승리했습니다. 이 판정은 Position A로 69퍼센트 편향된 평가자 성향과, 더 장황한 4.7에게 불리한 `max_tokens` 기반 절단(truncation) 효과로 일부 희석됩니다. 신호 자체는 실재하지만 원(raw) 승리 횟수가 시사하는 것보다는 좁습니다. 4.7은 서론(preamble)이 더 길고 구조적이며, 4.6은 절단 상황에서 결론에 더 빨리 도달합니다.

## 방법론 (Methodology) — 공통 프레임워크

모든 테스트는 단일 실행 파이프라인(pipeline)을 따릅니다. `cases/` 하위의 케이스 모듈(case module)은 순수(pure) `TestCase` 데이터만 반환하고, `runner/execute.py`의 러너(runner)가 각 케이스를 N회 반복하며 재시도(retry)와 지수 백오프(exponential backoff)를 수행합니다. 클라이언트 계층인 `clients/`는 Runtime 엔드포인트(endpoint)용으로 Anthropic Bedrock SDK를 감싸고, Mantle 엔드포인트용으로는 원시(raw) SigV4 서명 HTTP를 직접 구현합니다. 결과는 집계를 위해 통합된 `CallResult` 레코드(record)로 흘러갑니다.

**대상 모델과 엔드포인트:**

- `us-east-1` 리전의 `global.anthropic.claude-opus-4-7`과 `global.anthropic.claude-opus-4-6-v1` 추론 프로파일(inference profile)
- Anthropic SDK(`anthropic.AnthropicBedrock`) 경유 Bedrock Runtime 엔드포인트
- 서비스명 `bedrock-mantle`의 `botocore.auth.SigV4Auth`를 적용한 원시 `requests` 기반 Bedrock Mantle 엔드포인트

**호출별 측정 항목** (`clients/base.py`의 `CallResult`에 기록): `input_tokens`, `output_tokens`, `latency_s`, `thinking_chars`, `tool_calls_count`, `cache_creation_tokens`, `cache_read_tokens`, `ttft_s`, `stop_reason`, `cost_usd`.

**집계** (`stats.py`): 케이스별 평균(mean)과 표본 표준편차(sample standard deviation). 오류 실행(error run)은 평균에서 제외하되 `n_runs`에는 포함.

**실행 시간과 비용:**

| 실행 | 일시 (UTC) | 대상 테스트 | 호출 수 | 총 소요 시간 | 비용 |
|---|---|---|---|---|---|
| 1 | 2026-04-18 06:03 | 1, 2, 3, 4 | 95 / 105 | 9분 55초 | $1.16 |
| 2 | 2026-04-18 07:02 | 5, 6, 7, 8 | 100 / 100 | 8분 18초 | $1.31 |
| 3 | 2026-04-18 07:47 | 9, 10, 11, 12 | 140 / 140 | 14분 27초 | $3.75 |
| 4 | 2026-04-18 08:18 | 13 | 50 / 50 | 4분 46초 | $0.86 |
| Scorer v1 | 2026-04-18 07:05 | 프롬프트 3개 × 3회 | 9 | 2분 10초 | $0.01 |
| Scorer v2 | 2026-04-18 08:07 | 프롬프트 3개 × 5회 | 15 | 3분 25초 | $0.06 |
| **합계** | | | **409** | **약 43분** | **약 $7.14** |

실행 1의 Test 4 Mantle 케이스 10건은 HTTP 404로 실패했는데, 이는 테스트 계정이 Mantle 엔드포인트 허용 목록(allowlist)에 등록되지 않았기 때문입니다.

---

## Test 1 — 노력 수준(effort level) 대 토큰 소비량

### 목적

`effort` 파라미터(parameter)가 입력 토큰 소비를 줄이는지 측정합니다. 사용자들이 `effort=low`를 비용 제어(cost control) 레버로 생각하는 경우가 많은데, 그 직관이 맞는지 검증합니다.

### 테스트 방법

**케이스 파일:** `cases/effort.py`. **프롬프트:** `"Proof that there are infinitely many primes. Full reasoning."` (`cases/prompts.py::PROOF_PROMPT`). **max_tokens:** 1000. **케이스당 실행 횟수:** 5회.

5개 케이스, 각각 (모델, effort) 조합에 대응:

| 케이스 | 모델 | Effort | API 파라미터 |
|---|---|---|---|
| 1 | Opus 4.7 | low | `thinking={"type": "adaptive"}` + `extra_body={"output_config": {"effort": "low"}}` |
| 2 | Opus 4.7 | medium | 동일 구조, `effort="medium"` |
| 3 | Opus 4.7 | high | 동일 구조, `effort="high"` |
| 4 | Opus 4.7 | max | 동일 구조, `effort="max"` |
| 5 | Opus 4.6 | — | `thinking` 파라미터 없음 (네이티브 모드) |

4.7과 4.6 간의 API 형태(shape) 차이는 `clients/bedrock_runtime.py::build_kwargs`에서 처리합니다:

```python
if "opus-4-7" in model_id and effort:
    kwargs["thinking"] = {"type": "adaptive"}
    kwargs["extra_body"] = {"output_config": {"effort": effort}}
```

### 주요 발견

| 모델 | Effort | 입력 | 출력 (μ±σ) | 지연 시간 (μ±σ, 초) | 사고 블록(thinking) 문자 수 |
|---|---|---|---|---|---|
| Opus 4.7 | low | 32 | 970 ± 66 | 11.26 | 0 |
| Opus 4.7 | medium | 32 | 1000 ± 0 | 9.79 | 0 |
| Opus 4.7 | high | 32 | 1000 ± 0 | 14.78 | 0 |
| Opus 4.7 | max | 32 | 1000 ± 0 | 11.46 | 0 |
| Opus 4.6 | — | 21 | 809 ± 40 | 13.78 | 0 |

- 4.7의 네 가지 effort 변형에서 입력 토큰이 완전히 동일합니다(σ = 0). Effort 파라미터는 입력 소비에 영향을 주지 않습니다.
- 이 프롬프트에서 4.7 대 4.6 입력 오버헤드는 +52퍼센트입니다.
- 현재 SDK 응답 구조에서는 모든 케이스의 사고 블록(thinking block)이 0문자를 반환합니다.

### 시사점

- **Effort는 입력 비용 레버가 아닙니다.** 4.7의 입력 비용을 줄이려면 프롬프트를 짧게 하거나 구성을 바꾸거나(Test 11 참고), 가능해지면 캐싱을 활성화해야 합니다(Tests 5, 12 참고). Effort를 낮추는 것은 입력 비용에 아무 영향이 없습니다.
- Effort는 출력 깊이(output depth)와 지연 시간은 실제로 조절합니다 — `effort=max`에서 4.7은 1000토큰 출력 상한에 도달하고 전체 소요 시간도 길어집니다. Effort는 비용 레버가 아니라 품질·지연 시간 레버로 사용해야 합니다.

---

## Test 2 — 프롬프트 길이에 따른 스케일링(scaling)

### 목적

입력 토큰 오버헤드가 프롬프트 길이에 따라 어떻게 증감하는지 정량화합니다. 짧은 영어 질문과 긴 한국어-코드 혼합 프롬프트를 대조하여 오버헤드가 단일한 평탄 비율이 아님을 확인합니다.

### 테스트 방법

**케이스 파일:** `cases/length.py`. **max_tokens:** 400. **케이스당 실행 횟수:** 5회.

두 가지 프롬프트:

- **Short** (`cases/prompts.py::SHORT_PROMPT`): `"How do I center a div vertically and horizontally in CSS?"` (영문 약 10단어)
- **Long** (`cases/prompts.py::LONG_PROMPT`): 내장된 Python SQS 워커(worker)를 리뷰해 달라는 한국어 자연어 요청. 약 350단어 분량의 한국어 산문과 영문 코드 혼합

4개 케이스: 프롬프트 2개 × 모델 2개. 이 테스트는 effort 파라미터 없이 두 모델에 동일한 kwargs 구조를 사용합니다.

### 주요 발견

| 프롬프트 | 모델 | 입력 | 출력 | 지연 시간 | 4.7 오버헤드 |
|---|---|---|---|---|---|
| Short (영문 CSS 질문) | 4.7 | 30 | 300 | 5.35초 | +43% |
| Short (영문 CSS 질문) | 4.6 | 21 | 400 | 6.29초 | — |
| Long (한국어 + 코드) | 4.7 | 988 | 400 | 5.27초 | +13% |
| Long (한국어 + 코드) | 4.6 | 872 | 400 | 8.59초 | — |

- 오버헤드 비율은 콘텐츠(content) 유형에 크게 의존합니다 — 짧은 영어 질문은 +43퍼센트, 한국어-코드 혼합은 +13퍼센트.
- 4.7은 긴 프롬프트에서 38퍼센트 더 빠릅니다(5.27초 대 8.59초).
- 긴 프롬프트에서는 두 모델 모두 `max_tokens`에 도달했습니다.

### 시사점

- **콘텐츠 구성이 길이 자체보다 더 중요합니다.** Test 11이 이 관측을 분해합니다 — 격차를 좁히는 요인은 길이가 아니라 한국어 콘텐츠입니다.
- **혼합 콘텐츠 워크로드에서는 순영문 벤치마크에 기반한 오버헤드 추정이 과대평가됩니다.** 한국 개발자의 실제 작업 흐름은 대중적으로 알려진 "+45%"보다 더 적은 비용만 부담할 가능성이 높습니다.
- 프롬프트가 길수록 4.7의 호출당 지연 시간 우위가 더 분명해져, 프롬프트 길이가 증가할수록 대화형 경험이 4.7에 유리해집니다.

---

## Test 3 — 병렬 도구 사용 (parallel tool use) — 기준선

### 목적

두 모델 모두 무리 없이 처리할 수 있을 것으로 예상되는 2개 도구 프롬프트에서의 기준선 동작을 확인합니다. Test 8의 스케일링 연구와 Test 9의 강제 사용 비교의 문맥(context)을 제공합니다.

### 테스트 방법

**케이스 파일:** `cases/tools.py`. **프롬프트** (`cases/prompts.py::TOOL_USE_PROMPT`): `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` **max_tokens:** 400. **케이스당 실행 횟수:** 5회.

`tools` kwarg로 두 개의 도구 스키마(tool schema)를 연결합니다(`cases/prompts.py::TOOLS_SCHEMA`):

1. `get_bedrock_pricing(model_id, region)` — 온디맨드(on-demand) 가격 반환
2. `get_service_quota(quota_name, region)` — 쿼터 값 반환

케이스는 모델당 1개씩 총 2개. **단일 턴(single-turn)만** 측정 — 모델이 첫 응답에서 발행하는 `tool_use` 블록의 개수만 셉니다. **도구 실행 왕복은 수행하지 않으며**, `tool_result`를 되돌려보내지 않습니다.

도구 호출 계수는 `clients/base.py::parse_bedrock_response`가 응답 `content` 배열을 순회하며 `type == "tool_use"`인 블록을 카운트합니다.

### 주요 발견

| 모델 | 입력 | 출력 | 지연 시간 | 발행된 도구 호출 수 | 비용 |
|---|---|---|---|---|---|
| Opus 4.7 | 1040 | 239 | 4.50초 | **0** (stop_reason: `end_turn`) | $0.056 |
| Opus 4.6 | 776 | 318 | 4.43초 | 4 | $0.059 |

- Opus 4.6은 예상대로 4개의 병렬 `tool_use` 블록을 발행했습니다(두 리전 각각의 가격·쿼터 조회).
- Opus 4.7은 자체 지식만으로 일반 텍스트로 답변했으며 도구를 호출하지 않았습니다.

### 시사점

- 이것이 도구 거부(tool-refusal) 패턴의 첫 관측입니다. Test 8이 도구 메뉴 크기에 따른 이 패턴의 스케일을 분석하고, Test 9가 도구 사용을 확실히 강제하는 방법을 식별합니다.
- 도구 메뉴가 작을 때(≤ 2개)에도 행동 지향적 프롬프트에서 거부가 발생할 수 있습니다. 4.7이 "알아서 도구를 쓸 것"이라는 가정은 취약합니다.


---

## Test 4 — Bedrock Runtime 대 Mantle + 인증(authentication) 방식 비교

### 목적

Bedrock의 Mantle 엔드포인트가 Runtime과 동일한 토큰 수를 반환하는지 검증하고, 두 엔드포인트 각각에서 IAM 역할(role) 대 Bedrock 베어러 토큰(bearer token) 인증의 지연 시간 영향을 별도로 측정합니다.

### 테스트 방법

**케이스 파일:** `cases/mantle.py`. **케이스 수:** 10개. **케이스당 실행 횟수:** 5회.

케이스 매트릭스(matrix)는 엔드포인트(Runtime 대 Mantle)와 인증 방식(IAM 대 베어러 토큰)을 교차하며, 대표 워크로드로 Tests 1·2·3의 프롬프트를 차용합니다:

| # | 모델 | 엔드포인트 | 인증 | 프롬프트 | Effort |
|---|---|---|---|---|---|
| 1~4 | 4.7 | Mantle | iam_role | Short / Long / Proof / Tool use | proof는 max |
| 5~6 | 4.7 | Runtime / Mantle | bedrock_api_key | Long 프롬프트 | — |
| 7~8 | 4.7 | Runtime / Mantle | bedrock_api_key | Proof 프롬프트 | max |
| 9~10 | 4.7 | Runtime / Mantle | bedrock_api_key | Tool use | — |

Mantle 호출은 Anthropic SDK를 직접 사용할 수 없습니다. SDK가 서비스명 `bedrock`으로 서명하는데 Mantle은 이를 거부하기 때문입니다. `clients/bedrock_mantle.py`가 직접 구현한 SigV4로 이를 처리합니다:

```python
aws_req = AWSRequest(method="POST", url=MANTLE_URL, data=data,
                     headers={"Content-Type": "application/json"})
SigV4Auth(credentials, "bedrock-mantle", region).add_auth(aws_req)
resp = requests.post(MANTLE_URL, data=aws_req.body, headers=dict(aws_req.headers))
```

`auth_method="bedrock_api_key"`일 때는 SigV4 서명 없이 `Authorization: Bearer <token>` 헤더를 직접 전송합니다.

### 주요 발견

전체 50개 호출 중 30건의 Mantle 호출이 HTTP 404로 실패했습니다. 테스트 계정이 Mantle이 요구하는 프리뷰(preview) 허용 목록에 등록되지 않았습니다. Runtime 케이스는 성공했지만, IAM 대 베어러 토큰 인증 경로 분리 수정이 이후 커밋에 들어갔기 때문에 이 실행의 인증 방식 비교는 결론을 내지 못했습니다.

### 시사점

- **Mantle 접근에는 명시적 계정 허용 목록 등록이 필요합니다.** Mantle 기능(Projects, OpenAI 호환 API)을 중심으로 아키텍처를 설계할 때 이 리드 타임(lead time)을 고려해야 합니다.
- **Mantle 접근 권한이 확보되는 즉시 하네스(harness)를 재실행할 준비가 되어 있습니다.** `bedrock_mantle.py` 클라이언트, 케이스 매트릭스, 인증 방식 격리 모두 이미 구축되어 있습니다.
- 이 실행에서는 토큰 parity나 인증 방식 지연 시간에 대한 실행 가능한 결론은 도출되지 않았습니다.

---

## Test 5 — 사용자 프롬프트 캐싱 (보류)

### 목적

Bedrock에서의 사용자 프롬프트 캐싱이 Anthropic SDK를 통해 관측 가능한 캐시 적중(cache-hit) 신호를 반환하는지 측정하고, 반복 프롬프트에서 웜 캐시(warm cache) 상태의 비용 영향을 추정합니다.

### 테스트 방법

**케이스 파일:** `cases/caching.py`. **케이스 수:** 2개. **케이스당 실행 횟수:** 5회. **max_tokens:** 200.

프롬프트는 `LONG_PROMPT`를 자기 자신과 이어 붙여 Anthropic이 ephemeral 캐싱에 대해 문서화한 최소 1024 토큰 임계값을 확실히 넘기도록 구성합니다. 사용자 메시지는 콘텐츠 리스트(list) 형식으로 `cache_control` 마커를 적용합니다:

```python
messages = [{
    "role": "user",
    "content": [{
        "type": "text",
        "text": prompt,
        "cache_control": {"type": "ephemeral"},
    }],
}]
```

5회 실행 중 첫 호출은 캐시를 기록하고(`cache_creation_input_tokens > 0`, `cache_read_input_tokens = 0`), 약 5분의 TTL 내에 이어지는 호출은 캐시를 읽어야 합니다(`cache_creation = 0`, `cache_read > 0`).

`clients/base.py::compute_cost_usd`의 비용 계산은 캐시 필드가 0이 아닐 때 문서화된 배수(기록은 입력 요율의 1.25배, 읽기는 0.10배)를 적용합니다.

### 주요 발견

10회 호출 모두가 `cache_creation_input_tokens = 0`과 `cache_read_input_tokens = 0`을 반환했습니다. `cache_control` 페이로드(payload)는 오류 없이 수용되었습니다 — Bedrock이 마커를 거부하지도 않았고, 응답에서 캐시 필드를 노출하지도 않았습니다.

### 시사점

- **이 SDK 구성에서 Bedrock 프롬프트 캐싱은 관측 불가능합니다.** 응답 스키마가 Anthropic SDK를 통해 해당 필드를 노출하지 않거나, 이 모델들에 대해 해당 기능이 Bedrock에서 아직 일반 공급 상태가 아닌 것으로 추정됩니다.
- **Bedrock의 프로덕션 캐싱 비용 가정은 현재 검증 불가능합니다.** Tests 6·10·13(다중 턴)의 호출당 비용은 캐싱 할인 없이 보고되므로, Bedrock이 캐시 신호를 노출하기 시작하면 비용 추정이 비관적이었을 수 있습니다.
- Test 12가 시스템 프롬프트 경로에서 동일 실험을 반복해 다른 동작을 보이는지 확인합니다. Bedrock이 해당 필드를 반환하기 시작하는 시점에 대비해 `CallResult`와 `compute_cost_usd`의 인프라는 이미 준비되어 있습니다.

기본 `--test all` 실행에서 제외됩니다. 명시적으로 `--test 5`로 실행 가능합니다.

---

## Test 6 — 다중 턴 대화 (1~10턴)

### 목적

전형적인 챗봇(chatbot) 대화 범위인 1~10턴에서 대화 턴 수에 따라 입력 토큰과 지연 시간이 어떻게 변하는지 측정합니다.

### 테스트 방법

**케이스 파일:** `cases/multiturn.py`. **케이스 수:** 8개. **케이스당 실행 횟수:** 5회. **max_tokens:** 300.

케이스 모듈의 `_TURNS` 리스트에 서울에서 속초로 떠나는 주말 여행 계획이라는 일관된 주제의 9개 대화 쌍이 저장되어 있습니다. 각 쌍은 약 50토큰 분량의 `(user_text, assistant_text)` 튜플(tuple)로, 턴 수 외 다른 변수는 고정되어 있습니다(턴당 응답 장황도 차이가 개입하지 않음).

턴 수 n에 대해, `_build_messages` 함수가 메시지 리스트를 다음과 같이 구성합니다:

```python
msgs = []
for user_text, asst_text in _TURNS[:n_turns]:
    msgs.append({"role": "user", "content": user_text})
    msgs.append({"role": "assistant", "content": asst_text})
msgs.append({"role": "user", "content": final_user_msg})
```

최종 사용자 메시지는 항상 "지금까지 논의한 모든 내용을 바탕으로 토요일 당일 일정을 시간별로 작성해 주세요." 케이스는 구성된 리스트를 `TestCase.messages_override` 필드를 통해 전달하여, `build_kwargs`의 기본 단일 메시지 래핑을 건너뜁니다.

변형: 턴 수 ∈ {1, 3, 5, 10} × 모델 2개 = 8 케이스.

### 주요 발견

| 턴 수 | 4.6 입력 | 4.7 입력 | 4.7 오버헤드 | 4.6 지연 시간 | 4.7 지연 시간 |
|---|---|---|---|---|---|
| 1 | 107 | 150 | +40% | 5.30초 | 4.77초 |
| 3 | 297 | 437 | +47% | 7.49초 | 4.05초 |
| 5 | 491 | 721 | +47% | 7.81초 | 4.05초 |
| 10 | 879 | 1263 | +44% | 6.81초 | 4.05초 |

- 이 범위에서 입력 오버헤드는 +40~47퍼센트 대역에 평탄하게 유지됩니다.
- Opus 4.7 지연 시간은 턴 3부터 약 4.05초로 평탄 구간(plateau)에 진입합니다.
- Opus 4.6 지연 시간은 대화 기록(history)이 길어질수록 증가합니다.
- 10턴 시점에 Opus 4.7은 Opus 4.6보다 40퍼센트 빠릅니다.

### 시사점

- **다중 턴 에이전트 파이프라인은 단일 턴 벤치마크가 시사하는 것보다 4.7을 더 강하게 선호합니다.** 40퍼센트의 지연 시간 격차가 긴 사용자 세션 전체에 걸쳐 누적됩니다.
- **10턴 미만에서 4.7 지연 시간은 세션 길이 패널티를 거의 받지 않습니다.** 챗봇 설계자는 일관된 약 4초 응답 예산을 전제로 기획할 수 있습니다.
- Test 13이 10~20턴 경계를 세밀하게 파고들어 평탄 구간이 어디서 끝나는지 밝힙니다.

---

## Test 7 — 스트리밍(streaming) 첫 토큰 지연 시간 (TTFT, time-to-first-token)

### 목적

체감 지연 시간을 좌우하는 핵심 지표인 스트리밍 TTFT를 측정합니다. 사용자가 출력이 점진적으로 도착하는 것을 보는 대화형 채팅·IDE·음성 환경에서 중요한 지표로, 전체 응답을 기다리는 것과는 다릅니다.

### 테스트 방법

**케이스 파일:** `cases/streaming.py`. **케이스 수:** 4개. **케이스당 실행 횟수:** 5회. **max_tokens:** 300.

러너가 `BedrockRuntimeClient.invoke_streaming`을 호출하며, 이 메서드는 `messages.create` 대신 `messages.stream()`을 사용합니다. TTFT는 첫 `content_block_delta` 이벤트 시점에 기록됩니다:

```python
t0 = time.perf_counter()
ttft = None
with self._client.messages.stream(**kwargs) as stream:
    for event in stream:
        if ttft is None and getattr(event, "type", None) == "content_block_delta":
            ttft = time.perf_counter() - t0
    final_message = stream.get_final_message()
```

측정된 `ttft` 값은 `CallResult.ttft_s` 필드에 첨부됩니다. 변형: Test 2의 짧은/긴 프롬프트 × 모델 2개 = 4 케이스.

### 주요 발견

| 모델 | 짧은 프롬프트 TTFT | 긴 프롬프트 TTFT |
|---|---|---|
| Opus 4.7 | 1.15 ± 0.10초 | 1.15 ± 0.18초 |
| Opus 4.6 | 1.46 ± 0.11초 | 1.59 ± 0.21초 |
| 4.7 우위 | 21% 더 빠름 | 28% 더 빠름 |

- Opus 4.7의 TTFT는 프롬프트 길이에 불변이며, 짧은 입력과 긴 입력 모두 1.15초를 유지합니다.
- Opus 4.6의 TTFT는 프롬프트 길이에 따라 증가합니다(1.46초 → 1.59초).
- 스트리밍 모드 지연 시간 격차는 다수의 다른 테스트에서 관측된 종단 간(end-to-end) 지연 시간 격차보다 큽니다.

### 시사점

- **TTFT는 4.7의 가장 강력한 UX 레버입니다.** 프롬프트 길이에 불변인 1.15초 첫 토큰 지연 시간은 사용자가 첫 토큰 지연을 예민하게 체감하는 채팅·자동 완성·음성 워크플로에서 쉽게 대체할 수 없는 차별화 요소입니다.
- **4.6의 TTFT 페널티(penalty)는 프롬프트 크기에 따라 증가**하므로, 긴 시스템 프롬프트나 큰 컨텍스트를 사용하는 워크로드에서는 격차가 본 테스트가 측정한 것보다 더 벌어집니다.
- 전체 응답 시간은 상대적으로 차별성이 낮은 지표입니다. 대화형 UX를 위한 모델 선택에는 TTFT를 직접 측정해야 합니다.

---

## Test 8 — 도구 스키마(tool schema) 스케일링 (1 / 5 / 20개)

### 목적

MCP 서버(server)·Claude Code 확장 등을 통해 프로덕션(production) 에이전트가 노출할 만한 범위인 1개에서 20개까지의 도구 수에 따라 입력 토큰 오버헤드와 도구 호출 동작이 어떻게 변하는지 측정합니다.

### 테스트 방법

**케이스 파일:** `cases/tools_scaling.py`. **케이스 수:** 6개. **케이스당 실행 횟수:** 5회. **max_tokens:** 400.

도구는 개수만 유일한 변수가 되도록 동일한 형태로 런타임(runtime)에 생성합니다:

```python
def _synth_tool(i):
    return {
        "name": f"query_service_{i:02d}",
        "description": f"Query AWS service {i:02d} metadata including pricing, quotas, and availability in a given region...",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_id": {"type": "string", "description": f"..."},
                "region":      {"type": "string", "description": "..."},
                "detail_level": {"type": "string", "enum": ["summary", "detailed", "full"]},
            },
            "required": ["resource_id", "region"],
        },
    }
```

Test 3와 동일한 프롬프트를 도구 개수 n ∈ {1, 5, 20}과 두 모델에 대해 사용합니다.

### 주요 발견

| 도구 수 | 4.6 입력 | 4.7 입력 | 4.7 오버헤드 | 4.6 호출 | 4.7 호출 |
|---|---|---|---|---|---|
| 1 | 696 | 938 | +35% | 2.0 | 2.0 |
| 5 | 1372 | 1826 | +33% | 5.0 | 0.6 |
| 20 | 3907 | 5156 | +32% | 5.0 | 0.0 |

- 입력 오버헤드는 도구 수와 무관하게 +32~35퍼센트에서 평탄하게 유지됩니다. 스키마 크기가 토큰당 오버헤드를 증폭시키지 않습니다.
- Opus 4.7은 메뉴(menu)가 커질수록 점진적으로 도구 사용을 포기하며, 이 프롬프트에서 도구 20개 시점에 호출 0회에 도달합니다.
- Opus 4.6은 도구 5개 이상부터 5회의 병렬 도구 호출을 유지합니다.

### 시사점

- **대규모 도구 메뉴에서 4.7은 추가 안전장치 없이는 신뢰할 수 없습니다.** 많은 도구를 노출하는 에이전트 프레임워크(MCP, 에이전트 오케스트레이션, Claude Code)는 이 점을 반드시 고려해야 합니다.
- **도구 추가에 따른 오버헤드는 예측 가능**합니다(도구당 오버헤드가 안정적). 하지만 호출률은 예측 가능하지 않습니다.
- Test 9가 `tool_choice={"type": "any"}`를 신뢰할 수 있는 해결책으로 식별하고 그 트레이드오프(trade-off)를 정량화합니다.


---

## Test 9 — 도구 강제 사용 (tool forcing)

### 목적

명령형(imperative) 프롬프팅 또는 `tool_choice` API 파라미터가 Test 8에서 관측된 4.7의 도구 거부 패턴을 교정할 수 있는지 판별하고, 부작용을 정량화합니다.

### 테스트 방법

**케이스 파일:** `cases/tool_forcing.py`. **케이스 수:** 8개. **케이스당 실행 횟수:** 5회.

Test 8의 20개 도구 메뉴를 네 가지 강제 전략에 재사용합니다:

| 변형 | 프롬프트 | `tool_choice` 파라미터 |
|---|---|---|
| passive | `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` (기준선) | 없음 |
| imperative | `"You must use the available tools to look up pricing and limits..."` | 없음 |
| choice-any | 기준선 프롬프트 | `{"type": "any"}` |
| choice-specific | 기준선 프롬프트 | `{"type": "tool", "name": "query_service_00"}` |

설정 시 `tool_choice`는 `build_kwargs`를 통해 전달됩니다:

```python
if tool_choice is not None:
    kwargs["tool_choice"] = tool_choice
```

변형 4가지 × 모델 2개 = 8 케이스.

### 주요 발견

| 변형 | 4.6 도구 호출 수 | 4.7 도구 호출 수 |
|---|---|---|
| passive | 5.0 | 0.0 |
| imperative | 4.0 | 1.2 (5회 중 3회가 0) |
| choice-any | 2.0 | 2.0 |
| choice-specific | 2.0 | 2.0 |

- `tool_choice={"type": "any"}`는 4.7의 도구 거부를 완전히 해소합니다 — 5회 실행 모두 일관되게 도구를 발행합니다.
- 명령형 프롬프팅만으로는 4.7에서 신뢰할 수 없습니다(준수율 40퍼센트).
- `tool_choice`는 병렬 tool_use 블록 수를 5개(4.6 수동형)에서 두 모델 모두 2개로 감소시킵니다. 호출 보장과 병렬성(parallelism) 사이의 트레이드오프입니다.

### 시사점

- **프로덕션 에이전트 프레임워크는 4.7을 규모 있게 사용할 때 `tool_choice`를 루프(loop)에 통합해야 합니다.** 수동형·명령형 프롬프트 모두 불충분합니다.
- **병렬성 비용이 존재합니다** — `tool_choice="any"`는 우리 관측에서 병렬 호출을 2개로 상한선을 두는 것으로 보입니다. 최대 도구 팬아웃(fan-out)이 중요하다면 4.6의 수동형 동작이 작동하는 수준으로 메뉴를 작게 유지하거나, 여러 턴에 걸쳐 호출을 순차화해야 합니다.
- `choice-specific` 변형은 특정 이름의 도구를 강제할 수 있음을 보여주지만, 워크플로가 특정 다음 단계를 확정할 수 있는 경우에만 유용합니다.

---

## Test 10 — 다중 턴 극한 (10 / 20 / 30 / 50 / 100턴)

### 목적

Test 6의 다중 턴 곡선을 극한 영역(최대 100턴)까지 확장하여, 4.7의 지연 시간 평탄 구간이 장시간 세션에서도 유지되는지 또는 붕괴하는지 확인합니다.

### 테스트 방법

**케이스 파일:** `cases/multiturn_extreme.py`. **케이스 수:** 10개. **케이스당 실행 횟수:** 5회. **max_tokens:** 300.

Test 6의 메시지 리스트 빌더를 합성(synthetic) 턴 생성기로 확장합니다. n > 9(큐레이션된 `_TURNS` 리스트 크기)일 때, 추가 쌍을 여행 계획이라는 일관된 주제로 프로그래밍 생성합니다:

```python
def _synth_turn(i):
    topics = ["food recommendations", "best photo spots", "weather concerns",
              "packing list", "transport options", "budget breakdown", ...]
    topic = topics[i % len(topics)]
    user_q = f"Can you elaborate on {topic} for this trip..."
    asst_a = "Three specific suggestions: (1) prioritize the highest-rated..."
    return user_q, asst_a
```

변형: 턴 수 n ∈ {10, 20, 30, 50, 100} × 모델 2개 = 10 케이스. 100턴 케이스는 단일 호출에 201개 메시지(100쌍의 사용자·어시스턴트 + 최종 사용자 프롬프트 1개)를 담습니다.

### 주요 발견

| 턴 수 | 4.6 입력 | 4.7 입력 | 4.7 오버헤드 | 4.6 지연 시간 | 4.7 지연 시간 |
|---|---|---|---|---|---|
| 10 | 999 | 1447 | +45% | 6.73초 | 3.95초 |
| 20 | 2117 | 3181 | +50% | 6.64초 | 4.99초 |
| 30 | 3239 | 4915 | +52% | 6.62초 | 5.04초 |
| 50 | 5489 | 8393 | +53% | 8.14초 | 5.24초 |
| 100 | 11095 | 17063 | +54% | 7.69초 | 5.75초 |

- 오버헤드는 10턴의 +45퍼센트에서 100턴의 +54퍼센트로 완만히 상승합니다.
- 4.7은 전 구간에 걸쳐 25~40퍼센트의 지연 시간 우위를 유지합니다.
- 4.7 지연 시간 곡선에서 가장 큰 단일 증분(delta)은 10턴(3.95초)과 20턴(4.99초) 사이입니다.

### 시사점

- **4.7은 최대 100턴 세션 길이까지 더 빠른 선택지입니다.** 턴 20 전환 이후에도 절대 지연 시간 격차가 유지됩니다.
- **비용 프리미엄은 세션 길이에 따라 점진적으로 증가합니다** — 장기 세션에는 +50~55퍼센트 오버헤드를 예산에 반영하세요.
- Test 13이 4.7 지연 시간 곡선이 전환되는 정확한 지점을 식별합니다.

---

## Test 11 — 언어 및 코드 분해 (language and code decomposition)

### 목적

Test 2의 혼합 콘텐츠 오버헤드를 언어 요소(영어 대 한국어)와 코드 요소로 분해하여 어느 쪽이 지배적 요인(dominant factor)인지 식별합니다. 한국 개발자가 프로덕션 워크로드를 계획할 때 가장 관련성이 높은 데이터 포인트입니다.

### 테스트 방법

**케이스 파일:** `cases/language_code.py`. **케이스 수:** 8개. **케이스당 실행 횟수:** 5회. **max_tokens:** 400.

실질적 분량이 비슷한 네 가지 프롬프트 변형(각각 `cases/prompts.py`에서 가져옴):

| 변형 | 내용 |
|---|---|
| english | ~350단어 영어 산문 아키텍처 리뷰 |
| korean | 동일 주제, 한국어 자연어 산문 |
| code | ~350줄 Python asyncio SQS 워커 |
| korean_code | 영문 Python 코드 블록이 포함된 한국어 산문(`LONG_PROMPT`) |

4개 변형 × 2 모델 = 8 케이스.

### 주요 발견

| 변형 | 4.6 입력 | 4.7 입력 | 오버헤드 | 4.6 지연 시간 | 4.7 지연 시간 |
|---|---|---|---|---|---|
| 영어 산문 | 389 | 610 | **+57%** | 11.26초 | 5.62초 |
| 한국어 산문 | 962 | 1010 | **+5%** | 8.81초 | 5.12초 |
| Python 코드 | 1260 | 1622 | **+29%** | 10.49초 | 4.83초 |
| 한국어 + 코드 혼합 | 872 | 988 | **+13%** | 8.34초 | 4.54초 |

- 한국어 산문은 두 모델에서 거의 동일하게 토큰화됩니다(+5퍼센트). 네 가지 콘텐츠 유형 중 가장 낮은 오버헤드입니다.
- 영어 기술 산문은 가장 높은 오버헤드를 기록했으며(+57퍼센트), 이는 한국어의 11배입니다.
- 코드 전용 프롬프트는 +29퍼센트로 한국어와 영어의 중간에 위치합니다.
- Opus 4.7은 네 가지 콘텐츠 유형 전체에서 Opus 4.6보다 1.7배에서 2.2배 빠릅니다.

### 시사점

- **한국어 중심 워크로드는 4.7 프리미엄을 거의 부담하지 않습니다.** 영어 콘텐츠가 최소인 한국어 챗봇은 약 +5퍼센트를, 영문 코드가 포함된 한국어 개발자 질문을 읽는 코드 리뷰 에이전트는 약 +13퍼센트를 부담합니다.
- **영어 중심 배치 워크로드에서는 4.6이 실제로 더 저렴합니다** — +57퍼센트 오버헤드에서, 대량 영어 처리는 여전히 4.6을 정당화할 수 있습니다.
- **단일 오버헤드 숫자는 오해를 일으킵니다.** 팀은 대외에 발표된 headline 수치에 의존하기보다 자신의 프롬프트 혼합을 직접 프로파일링(profiling)해야 합니다.

---

## Test 12 — 시스템 프롬프트 캐싱 (보류)

### 목적

Test 5에서 다룬 사용자 프롬프트 캐싱과는 별개의 API 경로인 시스템 프롬프트 캐싱이 Bedrock에서 관측 가능한 캐시 신호를 반환하는지 확인합니다. 시스템 프롬프트는 길고 안정적이며 에이전트 세션당 수천 번 재사용되므로, 상업적으로 가장 가치 있는 캐싱 대상입니다.

### 테스트 방법

**케이스 파일:** `cases/system_caching.py`. **케이스 수:** 2개. **케이스당 실행 횟수:** 5회. **max_tokens:** 400.

약 2000토큰 분량의 "에이전트 운영 지침" 시스템 프롬프트(`cases/prompts.py::SYSTEM_PROMPT_LONG`)를 콘텐츠 블록 리스트 형태로 `system` 파라미터에 `cache_control` 마커와 함께 첨부합니다:

```python
kwargs["system"] = [{
    "type": "text",
    "text": SYSTEM_PROMPT_LONG,
    "cache_control": {"type": "ephemeral"},
}]
```

짧은 사용자 메시지가 각 실행에서 실제 생성을 트리거합니다. 기대 동작: 첫 호출이 시스템 프롬프트를 캐시에 기록하고, 2~5회 실행이 이를 읽음.

### 주요 발견

Test 5와 동일한 널(null) 결과입니다 — 두 모델에서 10회 호출 전체가 `cache_creation_input_tokens = 0`과 `cache_read_input_tokens = 0`을 반환했습니다.

### 시사점

- **이 SDK 구성에서는 Bedrock 프롬프트 캐싱이 사용자·시스템 프롬프트 경로 어느 쪽에서도 관측되지 않습니다.** Bedrock 배포를 계획하는 팀은 Bedrock이 해당 필드를 노출하기 전까지 문서화된 캐싱 비용 모델을 가정해서는 안 됩니다.
- 인프라는 Bedrock이 지원을 추가하는 시점에 대비되어 있습니다 — 측정을 시작하는 데 코드 변경은 필요 없습니다.

기본 `--test all` 실행에서 제외됩니다. `--test 12`로 실행 가능합니다.

---

## Test 13 — 다중 턴 전환점(knee-point) (11 / 13 / 15 / 17 / 19턴)

### 목적

Test 6과 Test 10 사이의 10~20턴 해상도(resolution) 공백을 메워, 4.7의 지연 시간 평탄 구간이 더 높은 구간(regime)으로 전환되는 지점을 정밀하게 위치 파악합니다.

### 테스트 방법

**케이스 파일:** `cases/multiturn_knee.py`. **케이스 수:** 10개. **케이스당 실행 횟수:** 5회. **max_tokens:** 300.

Test 10과 동일한 `_build_messages_extended` 생성기를 사용합니다. 변경점은 턴 수 집합뿐입니다.

변형: 턴 수 n ∈ {11, 13, 15, 17, 19} × 모델 2개 = 10 케이스.

### 주요 발견

Tests 6·13·10을 단일 시계열로 결합한 Opus 4.7의 결과:

| 턴 수 | 4.7 지연 시간 | 직전 대비 Δ |
|---|---|---|
| 10 | 3.95초 | — |
| 11 | 3.97초 | +0.5% |
| 13 | 3.74초 | −5.8% (국소 최저점) |
| 15 | 4.07초 | +8.8% |
| 17 | 4.18초 | +2.7% |
| 19 | 4.32초 | +3.3% |
| 20 | 4.99초 | **+15.5%** |
| 30 | 5.04초 | +1.0% |

- 턴 20 미만에서 4.7 지연 시간은 3.74~4.32초의 좁은 대역에서 진동합니다.
- 턴 20에서 단일 턴 증가로 0.68초의 도약(+15.5%)이 발생합니다.
- 턴 20 이후 곡선은 점진적 상승을 재개합니다(턴당 약 +1%).
- Opus 4.6은 이에 상응하는 계단을 보이지 않으며, 이 구간 전반에서 6.6~7.2초 대역에서 진동합니다.

### 시사점

- **4.7 지연 시간은 매끄러운 곡선이 아니라 계단 함수입니다.** 턴 20 미만에서는 일관된 4초 예산을 기준으로 설계할 수 있습니다. 턴 20에서 5초로의 도약을 대비하고, 그 이후는 다시 점진적으로 상승합니다.
- **계단 형태는 내부 구간(regime) 전환**을 시사합니다 — 아마도 문맥 버퍼(context buffer) 또는 KV 캐시 계층(KV-cache tier)의 임계값일 가능성이 있으며, 선형적 성능 저하는 아닙니다. 구체적인 메커니즘은 Anthropic 내부 데이터 없이는 알 수 없습니다.
- 계단을 피하려는 에이전트 설계자는 기록이 20턴 경계에 접근할 때 세션 요약(summarization) 또는 압축(compaction)을 고려해야 합니다.

---

## 품질 채점기(quality scorer) 결과

### 목적

4.7의 비용·지연 시간 이득이 품질 퇴보와 함께 오는지 점검하는 수단으로 응답 품질을 평가합니다. 토큰 수와 지연 시간만으로는 더 빠른 답이 틀렸거나 불완전한 경우를 놓칠 수 있습니다.

### 테스트 방법

**파일:** `scorers/judge.py`. CLI 진입점: `score.py`.

비교당 세 단계:

1. 동일 프롬프트(도구가 있는 경우 함께)를 Opus 4.7과 Opus 4.6 양쪽에 호출하고 응답 텍스트를 수집합니다.
2. 두 응답을 Response A와 Response B로 Claude Sonnet 4.6에 제시하고, 쌍별 판정을 요청하는 평가자 시스템 프롬프트를 함께 전송합니다.
3. 평가자의 `VERDICT: <A_better | B_better | tie>`를 파싱하여 모델 레이블(label)로 역매핑(remap)합니다.

두 차례의 채점기 실행:

- **V1 — 고정 위치**: Opus 4.7이 항상 Response A, Opus 4.6이 항상 Response B. 프롬프트 3종(`tools`, `short`, `proof`) × 3회 = 9개 판정.
- **V2 — A/B 무작위화**: 호출마다 4.7 위치를 무작위화. `position_of_47`와 `raw_verdict`를 기록해 편향 진단에 활용. 프롬프트 3종 × 5회 = 15개 판정.

V2 구현:

```python
position_of_47 = "A" if rng.random() < 0.5 else "B"
if position_of_47 == "A":
    response_a, response_b = text_47, text_46
else:
    response_a, response_b = text_46, text_47
# ... 평가자 호출 후 역매핑:
verdict = _remap_verdict(raw_verdict, position_of_47)
```

### 주요 발견

**V1 (고정 위치):**

| 프롬프트 | 4.7 승 | 4.6 승 | 무승부 |
|---|---|---|---|
| tools | 1 | 2 | 0 |
| short | 1 | 2 | 0 |
| proof | 0 | 3 | 0 |
| **합계 (9회)** | **2 (22%)** | **7 (78%)** | 0 |

**V2 (무작위화):**

| 프롬프트 | 4.7 승 | 4.6 승 | 무승부 |
|---|---|---|---|
| tools | 2 | 3 | 0 |
| short | 0 | 3 | 2 |
| proof | 2 | 3 | 0 |
| **합계 (15회)** | **4 (27%)** | **9 (60%)** | 2 (13%) |

V2 위치 편향 진단: 무승부가 아닌 13개 케이스 중 Response A가 9회 승리(69%), 평가자의 중간 수준 위치 편향을 확인.

### 시사점

- **무작위화 이후에도 Opus 4.6이 비교의 약 60퍼센트에서 선호됩니다.** 선호는 실재하지만 V1 고정 위치 결과가 시사한 것보다 좁습니다.
- **`max_tokens=400` 절단이 4.7의 더 장황한 스타일을 불균형적으로 불리하게 만듭니다.** 4.7은 토큰을 서론 또는 구조적 setup에 투자하는 경향이 있어, 상한이 결론 전에 응답을 자르면 평가자는 불완전한 답으로 인식합니다.
- **장황함은 출력 제약과 상호작용합니다.** 간결한 출력 API(카드, 요약, 엄격한 길이의 JSON)에는 4.6이 더 적합할 수 있습니다. 장황함이 특징으로 기능하는 긴 형식 분석에서는 4.7의 구조적 서론이 이점이 됩니다.

---

## 의사결정 매트릭스(decision matrix)

| 워크로드 | 4.7 선호 | 4.6 선호 | 근거 |
|---|---|---|---|
| 한국어 고객 지원 챗봇 | 예 | — | Test 11: +5% 오버헤드, 1.7배 속도 |
| Claude Code (코드 중심) | 예 | — | Test 11: +29% 오버헤드, 2.2배 속도 |
| 대규모 도구 에이전트 (10개 이상) | `tool_choice` 사용 시 예 | 그 외 경우 예 | Test 8, 9 |
| 장시간 에이전트 세션 (5~19턴) | 예 | — | Test 6, 13: 평탄 4초 구간 |
| 장시간 에이전트 세션 (20턴 이상) | 압축(compaction) 사용 시 예 | 예 | Test 10, 13: 전환점 이후 5~6초 |
| 스트리밍 챗봇 / IDE | 예 | — | Test 7: TTFT 1.15초 불변 |
| 간결 출력 API (`max_tokens` ≤ 400) | — | 예 | 채점기: 4.7 절단 불리 |
| 긴 서술 구조적 분석 | 예 | — | 채점기: 4.7 서론이 구조 제공 |
| 영어 배치 처리 / RAG | — | 예 | Test 11: 영어에서 +57% 비용 |
| 추론 / 수학 | 어느 쪽이든 | 어느 쪽이든 | Test 1: 비용 동등 |

## 한계(limitations)

- **Mantle 엔드포인트 접근 불가**: 테스트 계정에서 Mantle 사용이 불가능해 Test 4의 동등성(parity) 주장을 이 환경에서 평가할 수 없습니다.
- **프롬프트 캐싱 관측 불가**: 이 SDK 설정에서 Bedrock은 캐시 사용량 필드를 반환하지 않아 Test 5와 Test 12가 보류되었습니다.
- **단일 리전 테스트**: us-east-1만 사용했으며, 다른 지역 추론 프로파일은 테스트하지 않았습니다.
- **표본 크기**: 케이스당 5회 실행은 저분산 지표에는 작지만 LLM 벤치마크의 표준 관행입니다. 채점기 15회는 더 작으며, 품질에 대한 추론은 방향성(directional) 수준으로 해석해야 합니다.
- **위치 편향**: 채점기에서 감지된 Response A 선호 69퍼센트가 완전히 보정되지 않아, 절대 승리 횟수는 Opus 4.6을 수 퍼센트 포인트 과대 표현할 가능성이 있습니다.
- **단일 평가자 모델**: Sonnet 4.6만 사용했으며, 다른 평가자는 다른 선호를 보일 수 있습니다.
- **`max_tokens=400` 절단 아티팩트(artifact)**: 여러 테스트에서 더 간결한 모델에 유리하게 작용했으며, 토큰 예산이 넉넉한 워크로드는 다른 순위를 낳을 수 있습니다.

## 재현 가능성(reproducibility)

모든 원(raw) 데이터는 SDK 버전, 리전, 인증 방식, 요청 본문(request body) 덤프를 포함한 호출별 메타데이터와 함께 `results/YYYY-MM-DD-HHMM/raw.json`에 보존됩니다. 하네스(harness)는 멱등적(idempotent)입니다. 동일한 모델 접근 권한을 가진 어떤 계정에서든 `python3 run.py --test all --runs 5`는 동일 구조의 결과를 생성합니다. 비용과 지연 시간만이 비결정적(non-deterministic) 출력이며, 토큰 수는 실행 간에 안정적으로 유지됩니다.

## 핵심 인사이트(insights) 종합

전체 테스트 매트릭스(matrix)에서 도출한 8가지 핵심 결론:

1. **Effort는 비용 레버가 아닙니다.** `effort` 파라미터는 출력 깊이(output depth)만 조절할 뿐 입력 토큰에는 영향이 없습니다. 4.7의 청구액을 줄이려면 프롬프트를 짧게 만들거나 캐싱해야 하며, effort를 낮추는 것은 입력 비용에 아무 영향도 미치지 않습니다.
2. **한국어는 동등하게 토큰화되며, 영어와 코드가 오버헤드를 부담합니다.** 한국어 산문 +5퍼센트 대 영어 기술 산문 +57퍼센트는 측정된 차원 중 가장 큰 격차입니다. 어떤 설정 노브(knob)보다 워크로드의 언어가 더 큰 영향을 미칩니다.
3. **지연 시간 우위는 세션이 길수록 커집니다.** 턴 1에서 4.7은 10퍼센트 빠르고, 턴 3에서 46퍼센트 빠르며, 턴 100에서 25퍼센트 빠릅니다. 전환점 이후에도 절대 격차는 유지되므로, 장시간 세션이 4.7에 유리합니다.
4. **TTFT는 4.7의 가장 강력한 UX 레버입니다.** 프롬프트 길이에 불변인 1.15초 TTFT는 대화형 채팅과 IDE 워크플로에서 쉽게 대체할 수 없는 우위입니다. 전체 응답 시간은 차별성이 상대적으로 낮습니다.
5. **대규모 도구 메뉴는 `tool_choice`를 요구합니다.** 20개 도구 프롬프트에서 4.7은 수동형 프롬프팅 시 도구 호출이 0이고, 명령형 프롬프팅에서도 5회 중 1.2회에 그칩니다. `tool_choice={"type": "any"}`는 병렬성 감소(5회 호출 → 2회)를 대가로 신뢰성을 확보합니다.
6. **지연 시간은 매끄러운 곡선이 아니라 턴 20에서 계단을 가집니다.** 20턴 미만에서 4.7 지연 시간은 3.7~4.3초의 좁은 대역에서 진동합니다. 턴 20에서 4.99초로 단일 증가량이 도약하며, 그 이후 점진적 상승 곡선이 재개됩니다. 이는 선형적 성능 저하가 아니라 내부 구간(regime) 전환을 시사합니다.
7. **이 SDK 설정에서는 Bedrock 캐싱이 관측되지 않습니다.** 사용자 프롬프트 캐싱과 시스템 프롬프트 캐싱 테스트 각각 10회씩, 총 20회 호출에서 캐시 생성 토큰과 캐시 읽기 토큰이 모두 0이었습니다. 이 문제가 해결되기 전까지는, 관측된 호출당 비용을 어떤 캐싱 가정으로도 할인할 수 없습니다.
8. **품질은 방향성 면에서 유사하며, 장황성 아티팩트가 엄격한 토큰 상한 아래에서 4.6에 유리하게 작용합니다.** 위치 무작위화된 평가자는 비교의 60퍼센트에서 4.6을 선호했습니다. 이 효과는 `max_tokens=400` 절단이 4.7의 더 장황한 응답을 결론에 도달하기 전에 잘라내면서 증폭됩니다. 토큰 예산이 넉넉한 워크로드는 품질 면에서 동등(parity)에 더 가까울 가능성이 높습니다.
