# Test Results — Opus 4.7 vs 4.6 Bedrock Benchmark

[![Tests run](https://img.shields.io/badge/benchmark%20runs-4-brightgreen)](#)
[![Calls executed](https://img.shields.io/badge/API%20calls-345-blue)](#)
[![Total cost](https://img.shields.io/badge/total%20cost-%247.14-yellow)](#)
[![Active tests](https://img.shields.io/badge/tests-11%20active%20%2B%202%20deferred-orange)](#)
[![Unit tests](https://img.shields.io/badge/pytest-62%20passing-brightgreen)](#)
[![English](https://img.shields.io/badge/language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/language-한국어-red)](#한국어)

Consolidated results across four benchmark runs on 2026-04-18 against AWS Bedrock (us-east-1), covering 13 test dimensions plus a quality scorer with two methodologies (fixed position and randomized A/B).

AWS Bedrock(us-east-1)에서 2026-04-18에 수행된 4회의 벤치마크 실행 결과를 통합한 문서로, 13개 테스트 차원과 두 가지 방법론(고정 포지션 / A-B 랜덤화)으로 진행된 품질 스코어러 결과를 포함합니다.

---

# English

## Executive Summary

Opus 4.7 is 25–40 percent faster than 4.6 across nearly all measured workloads, at an input-token premium that varies from +5 percent on Korean prose to +57 percent on English technical prose. Effort level does not reduce input token consumption — all four 4.7 effort variants consumed identical input tokens (σ = 0) on the same prompt. Four substantive findings emerged across the full suite: (1) at 20 tools, 4.7 stops invoking tools unless forced via `tool_choice`; (2) 4.7 exhibits a sudden +16 percent latency step at turn 20; (3) Korean tokenization overhead is nearly null; (4) Bedrock does not surface prompt caching usage fields in SDK responses, making caching cost measurement unverifiable in this environment.

Our quality scorer, using Claude Sonnet 4.6 as a judge with A/B position randomization, found 4.6 winning 9 of 15 pairwise comparisons. The verdict is confounded by a 69 percent position-A bias and by max_tokens-based truncation that disadvantages the more verbose 4.7. The signal is real but narrower than the raw counts suggest: 4.7 is more verbose and setup-oriented; 4.6 reaches conclusions faster when truncated.

## Methodology

All calls went to `global.anthropic.claude-opus-4-7` and `global.anthropic.claude-opus-4-6-v1` inference profiles in `us-east-1`, via Bedrock Runtime (Anthropic SDK) and Bedrock Mantle (raw HTTP with SigV4 signing, service name `bedrock-mantle`). Each case ran five times; aggregate statistics report mean and sample standard deviation with error-runs excluded from means but counted in `n_runs`. Costs were computed from token counts using the `PRICING` constants in `config.py`.

Run durations and costs:

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

## Test 1 — Effort Level versus Token Consumption

**Purpose:** Measure whether the `effort` parameter affects input token consumption — a common assumption that users might reach for as a cost-control lever.

Prompt: `"Proof that there are infinitely many primes. Full reasoning."`

| Model | Effort | Input | Output (μ±σ) | Latency (μ±σ s) | Thinking chars |
|---|---|---|---|---|---|
| Opus 4.7 | low | 32 | 970 ± 66 | 11.26 | 0 |
| Opus 4.7 | medium | 32 | 1000 ± 0 | 9.79 | 0 |
| Opus 4.7 | high | 32 | 1000 ± 0 | 14.78 | 0 |
| Opus 4.7 | max | 32 | 1000 ± 0 | 11.46 | 0 |
| Opus 4.6 | — | 21 | 809 ± 40 | 13.78 | 0 |

Findings:

- Input tokens are identical across the four 4.7 effort variants (σ = 0). The effort parameter does not affect input consumption.
- Measured 4.7 vs 4.6 overhead on this prompt is +52 percent.
- Thinking blocks returned zero characters for all cases, including the 4.6 native-mode invocation, in our current SDK response shape on Bedrock.

## Test 2 — Prompt Length Scaling

**Purpose:** Quantify how input-token overhead scales with prompt length, contrasting a short English query against a longer Korean-and-code hybrid.

| Prompt | Model | Input | Output | Latency | 4.7 overhead |
|---|---|---|---|---|---|
| Short English CSS question | 4.7 | 30 | 300 | 5.35 s | +43% |
| Short English CSS question | 4.6 | 21 | 400 | 6.29 s | — |
| Long Korean prose + English code | 4.7 | 988 | 400 | 5.27 s | +13% |
| Long Korean prose + English code | 4.6 | 872 | 400 | 8.59 s | — |

Findings:

- Overhead ratio depends heavily on content type. A short English question produced +43 percent, while a longer Korean-plus-code hybrid produced only +13 percent. Test 11 decomposes this further.
- 4.7 was 38 percent faster on the long prompt (5.27 s vs 8.59 s).
- Both models hit `max_tokens` on the long prompt.

## Test 3 — Parallel Tool Use (baseline)

**Purpose:** Establish baseline parallel tool-use behavior on a simple two-tool prompt that both models should handle trivially, as context for Test 8's scaling study.

Prompt: `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` with two tool schemas.

| Model | Input | Output | Latency | Tool calls emitted | Cost |
|---|---|---|---|---|---|
| Opus 4.7 | 1040 | 239 | 4.50 s | **0** | $0.056 |
| Opus 4.6 | 776 | 318 | 4.43 s | 4 | $0.059 |

Findings:

- Opus 4.6 emitted the expected four parallel `tool_use` blocks. Opus 4.7 answered from its own knowledge, stop reason `end_turn`, no tool invocations.
- This is the first appearance of a tool-refusal pattern that Test 8 then characterizes by tool-menu size.

## Test 4 — Bedrock Runtime versus Mantle, with Auth Comparison

**Purpose:** Verify that Bedrock's Mantle endpoint produces identical token counts to Runtime, and separately measure the latency impact of IAM versus bearer-token authentication.

Of 10 cases (50 calls), 30 calls failed with HTTP 404 on the Mantle endpoint. The test account lacks the preview allowlisting Mantle requires. Runtime cases succeeded, but the auth-method comparison under the SDK-level bearer-token vs IAM distinction was inconclusive in this run because the separation fix landed in a later commit.

Results are not actionable without Mantle access. The infrastructure — raw SigV4 signing with service name `bedrock-mantle` and separated auth paths — is in place for re-running once the account is allowlisted.

## Test 5 — Prompt Caching (deferred)

**Purpose:** Measure whether user-prompt caching on Bedrock returns observable cache-hit signals in the Anthropic SDK response, and estimate the cost impact of a warm cache.

Status: deferred. All 10 calls returned `cache_creation_input_tokens = 0` and `cache_read_input_tokens = 0` despite sending `cache_control={"type": "ephemeral"}` markers on prompts well over the 1024-token threshold. The `cache_control` payload was accepted without error, so either the Bedrock response schema does not surface these fields via the Anthropic SDK in this configuration, or the feature is not generally available for these models on Bedrock as of the test date. Excluded from the default `--test all` run; runnable with `--test 5`.

## Test 6 — Multi-turn Conversation Scaling (1–10 turns)

**Purpose:** Measure how input tokens and latency scale with conversation turn count across the typical chatbot range of 1 to 10 turns.

| Turns | 4.6 input | 4.7 input | 4.7 overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 1 | 107 | 150 | +40% | 5.30 s | 4.77 s |
| 3 | 297 | 437 | +47% | 7.49 s | 4.05 s |
| 5 | 491 | 721 | +47% | 7.81 s | 4.05 s |
| 10 | 879 | 1263 | +44% | 6.81 s | 4.05 s |

Findings:

- Input overhead is flat in the +40–47 percent band regardless of turn count in this range.
- Opus 4.7 latency plateaus at approximately 4.05 s from turn 3 onward in this range; Opus 4.6 latency grows with history length.
- At 10 turns, Opus 4.7 is 40 percent faster than Opus 4.6.

## Test 7 — Streaming Time-to-First-Token

**Purpose:** Measure streaming time-to-first-token (TTFT), the metric that dominates perceived latency in interactive chat and IDE contexts where users see output arrive incrementally.

| Model | Short prompt TTFT | Long prompt TTFT |
|---|---|---|
| Opus 4.7 | 1.15 ± 0.10 s | 1.15 ± 0.18 s |
| Opus 4.6 | 1.46 ± 0.11 s | 1.59 ± 0.21 s |
| 4.7 advantage | 21% faster | 28% faster |

Findings:

- Opus 4.7 TTFT is invariant to prompt length in this range, holding at 1.15 seconds for both the short CSS question and the long prompt.
- Opus 4.6 TTFT grows with prompt length.
- The streaming-mode latency gap is larger than the end-to-end latency gap in many tests, which matters for interactive UX.

## Test 8 — Tool Schema Scaling (1 / 5 / 20 tools)

**Purpose:** Measure how input-token overhead and tool-invocation behavior change as the number of available tools grows from 1 to 20, the range a production agent might expose.

| Tools | 4.6 input | 4.7 input | 4.7 overhead | 4.6 calls | 4.7 calls |
|---|---|---|---|---|---|
| 1 | 696 | 938 | +35% | 2.0 | 2.0 |
| 5 | 1372 | 1826 | +33% | 5.0 | 0.6 |
| 20 | 3907 | 5156 | +32% | 5.0 | 0.0 |

Findings:

- Input overhead is flat at +32–35 percent regardless of tool count; schema size does not amplify per-token overhead.
- Opus 4.7 progressively abandons tools as the menu grows, reaching zero invocations at 20 tools on this prompt.
- Opus 4.6 maintains consistent tool invocation across scales.

## Test 9 — Tool Forcing

**Purpose:** Determine whether imperative prompting or the `tool_choice` API parameter can correct the 4.7 tool-refusal pattern observed at scale in Test 8.

Four variants at the 20-tool menu established in Test 8. Measured tool_calls_count per variant.

| Variant | Method | 4.6 tool_calls | 4.7 tool_calls |
|---|---|---|---|
| passive | baseline prompt | 5.0 | 0.0 |
| imperative | "You must use the tools…" | 4.0 | 1.2 (3 of 5 returned 0) |
| choice-any | `tool_choice={"type": "any"}` | 2.0 | 2.0 |
| choice-specific | `tool_choice={"type": "tool", "name": …}` | 2.0 | 2.0 |

Findings:

- `tool_choice={"type": "any"}` fully resolves the 4.7 tool-refusal observed in Test 8; 5 of 5 runs emit tools consistently.
- Imperative prompting alone is unreliable (40 percent compliance on 4.7).
- `tool_choice` reduces parallel tool-use block count from 5 (4.6 passive) to 2 in both models, indicating a trade-off between parallelism and invocation guarantee.

## Test 10 — Multi-turn Extreme (10 / 20 / 30 / 50 / 100 turns)

**Purpose:** Extend the multi-turn curve into extreme territory (up to 100 turns) to see whether 4.7's latency plateau holds or breaks down at long sessions.

| Turns | 4.6 input | 4.7 input | 4.7 overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 10 | 999 | 1447 | +45% | 6.73 s | 3.95 s |
| 20 | 2117 | 3181 | +50% | 6.64 s | 4.99 s |
| 30 | 3239 | 4915 | +52% | 6.62 s | 5.04 s |
| 50 | 5489 | 8393 | +53% | 8.14 s | 5.24 s |
| 100 | 11095 | 17063 | +54% | 7.69 s | 5.75 s |

Findings:

- Overhead climbs modestly from +45 percent at 10 turns to +54 percent at 100 turns.
- 4.7 retains a latency advantage from 25 to 40 percent throughout the range.
- The jump from turn 10 latency (3.95 s) to turn 20 latency (4.99 s) is the largest single delta in the curve; Test 13 explores this boundary at finer resolution.

## Test 11 — Language and Code Decomposition

**Purpose:** Decompose the mixed-content overhead observed in Test 2 into its language (English vs Korean) and code components, to identify which factor dominates.

| Variant | 4.6 input | 4.7 input | Overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| English prose | 389 | 610 | **+57%** | 11.26 s | 5.62 s |
| Korean prose | 962 | 1010 | **+5%** | 8.81 s | 5.12 s |
| Python code | 1260 | 1622 | **+29%** | 10.49 s | 4.83 s |
| Korean + code hybrid | 872 | 988 | **+13%** | 8.34 s | 4.54 s |

Findings:

- Korean prose tokenizes almost identically on both models (+5 percent) — the lowest overhead across the four content types.
- English technical prose shows the highest overhead in our tests (+57 percent), 11 times higher than Korean.
- Code-only prompts land at +29 percent, roughly halfway between Korean and English.
- Opus 4.7 is 1.7x to 2.2x faster than Opus 4.6 across all four content types.

## Test 12 — System Prompt Caching (deferred)

**Purpose:** Check whether system-prompt caching (a distinct API path from user-prompt caching tested in Test 5) returns observable cache signals on Bedrock.

Same null result as Test 5: `cache_creation_input_tokens = 0` and `cache_read_input_tokens = 0` across all five runs, on both models, with a 2000-token system prompt carrying a `cache_control` marker. Deferred pending clarification of Bedrock's prompt-caching observability.

## Test 13 — Multi-turn Knee-point (11 / 13 / 15 / 17 / 19 turns)

**Purpose:** Fill the 10-to-20-turn resolution gap between Tests 6 and 10 to precisely locate where 4.7's latency plateau transitions to a higher regime.

Fills the resolution gap between Test 6 (1–10) and Test 10 (10–100).

| Turns | 4.6 latency | 4.7 latency | Δ from previous (4.7) |
|---|---|---|---|
| 10 | 6.73 s | 3.95 s | — |
| 11 | 6.40 s | 3.97 s | +0.5% |
| 13 | 7.22 s | 3.74 s | −5.8% (local minimum) |
| 15 | 6.82 s | 4.07 s | +8.8% |
| 17 | 7.04 s | 4.18 s | +2.7% |
| 19 | 6.75 s | 4.32 s | +3.3% |
| 20 | 6.64 s | 4.99 s | **+15.5%** |
| 30 | 6.62 s | 5.04 s | +1.0% |

Finding:

- Opus 4.7 exhibits a step function at turn 20: a single turn-count increment produces a 0.68-second jump (+16 percent), after which the latency curve resumes its gradual climb. This is not smooth degradation; it has the shape of a threshold being crossed (possibly context-buffer or KV-cache tier switching). Opus 4.6 shows no comparable step.

## Quality Scorer Results

Both scorer versions use Sonnet 4.6 as judge, pairwise comparison format, same three prompts (`tools`, `short`, `proof`).

### Version 1 — Fixed position (Opus 4.7 always Response A)

| Prompt | 4.7 wins | 4.6 wins | Tie |
|---|---|---|---|
| tools | 1 | 2 | 0 |
| short | 1 | 2 | 0 |
| proof | 0 | 3 | 0 |
| **Total (9 runs)** | **2 (22%)** | **7 (78%)** | 0 |

### Version 2 — A/B position randomized

| Prompt | 4.7 wins | 4.6 wins | Tie |
|---|---|---|---|
| tools | 2 | 3 | 0 |
| short | 0 | 3 | 2 |
| proof | 2 | 3 | 0 |
| **Total (15 runs)** | **4 (27%)** | **9 (60%)** | 2 (13%) |

Position-bias diagnostic for v2: Response A won 9 of 13 non-tie cases (69 percent), indicating moderate positional bias by the judge. Even correcting for this, Opus 4.6 maintains a clear majority.

Findings:

- Opus 4.6 is preferred in roughly 60 percent of pairwise comparisons even with position randomization.
- The preference is partially explained by `max_tokens=400` truncation: Opus 4.7's more verbose preamble style leaves it truncated before reaching a conclusion, while Opus 4.6's terser style reaches a conclusion within the cap.
- When Opus 4.7 was placed in Response B, it won 0 of 7 comparisons. When placed in Response A, it won 4 of 8. The position effect is real.

## Decision Matrix

| Workload | Prefer 4.7 | Prefer 4.6 | Primary evidence |
|---|---|---|---|
| Korean customer support chatbot | yes | — | Test 11: +5% overhead, 1.7x speed |
| Claude Code (code-heavy) | yes | — | Test 11: +29% overhead, 2.2x speed |
| Large toolset agent (10+ tools) | yes w/ `tool_choice` | yes otherwise | Tests 8, 9 |
| Long-running agent session (5–19 turns) | yes | — | Tests 6, 13: flat 4 s plateau |
| Long-running agent session (20+ turns) | yes w/ compaction | yes | Tests 10, 13: post-knee 5–6 s |
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

## 방법론 (Methodology)

모든 호출은 `us-east-1` 리전의 `global.anthropic.claude-opus-4-7` 및 `global.anthropic.claude-opus-4-6-v1` 추론 프로파일(inference profile)을 대상으로 했으며, Bedrock Runtime(Anthropic SDK 경유)과 Bedrock Mantle(서비스명 `bedrock-mantle`의 SigV4 서명을 적용한 raw HTTP 경유) 두 경로로 진행했습니다. 각 케이스(case)는 5회씩 실행했고, 집계 통계는 오류 실행(error run)을 평균 계산에서 제외하되 `n_runs`에는 포함한 상태로 평균과 표본 표준편차를 보고합니다. 비용은 `config.py`의 `PRICING` 상수를 사용해 토큰 수로부터 산출했습니다.

실행 시간과 비용 요약:

| 실행 | 일시 (UTC) | 대상 테스트 | 호출 수 | 총 소요 시간 | 비용 |
|---|---|---|---|---|---|
| 1 | 2026-04-18 06:03 | 1, 2, 3, 4 | 95 / 105 | 9분 55초 | $1.16 |
| 2 | 2026-04-18 07:02 | 5, 6, 7, 8 | 100 / 100 | 8분 18초 | $1.31 |
| 3 | 2026-04-18 07:47 | 9, 10, 11, 12 | 140 / 140 | 14분 27초 | $3.75 |
| 4 | 2026-04-18 08:18 | 13 | 50 / 50 | 4분 46초 | $0.86 |
| Scorer v1 | 2026-04-18 07:05 | 프롬프트 3개 × 3회 | 9 | 2분 10초 | $0.01 |
| Scorer v2 | 2026-04-18 08:07 | 프롬프트 3개 × 5회 | 15 | 3분 25초 | $0.06 |
| **합계** | | | **409** | **약 43분** | **약 $7.14** |

실행 1의 Test 4 Mantle 케이스 10건은 HTTP 404로 실패했는데, 이는 테스트 계정이 Mantle 엔드포인트(endpoint) 허용 목록(allowlist)에 등록되지 않았기 때문입니다.

## Test 1 — 노력 수준(effort level) 대 토큰 소비량

**목적:** `effort` 파라미터가 입력 토큰 소비에 영향을 주는지 — 사용자들이 비용 제어(cost control) 레버로 기대할 법한 가정 — 을 측정합니다.

프롬프트(prompt): `"Proof that there are infinitely many primes. Full reasoning."`

| 모델 | Effort | 입력 | 출력 (μ±σ) | 지연 시간 (μ±σ, 초) | 사고 블록(thinking) 문자 수 |
|---|---|---|---|---|---|
| Opus 4.7 | low | 32 | 970 ± 66 | 11.26 | 0 |
| Opus 4.7 | medium | 32 | 1000 ± 0 | 9.79 | 0 |
| Opus 4.7 | high | 32 | 1000 ± 0 | 14.78 | 0 |
| Opus 4.7 | max | 32 | 1000 ± 0 | 11.46 | 0 |
| Opus 4.6 | — | 21 | 809 ± 40 | 13.78 | 0 |

주요 발견:

- 4.7의 네 가지 effort 변형에서 입력 토큰 수가 완전히 동일합니다(σ = 0). Effort 파라미터는 입력 소비에 영향을 주지 않습니다.
- 이 프롬프트에서 측정된 4.7 대 4.6 오버헤드는 +52퍼센트입니다.
- 현재 Bedrock의 SDK 응답 구조에서는 4.6의 native 모드 호출을 포함해 모든 케이스의 사고 블록(thinking block)이 0문자를 반환합니다.

## Test 2 — 프롬프트 길이에 따른 스케일링(scaling)

**목적:** 입력 토큰 오버헤드가 프롬프트 길이에 따라 어떻게 증감하는지, 짧은 영어 질문과 긴 한국어-코드 혼합 프롬프트를 대조해 정량화합니다.

| 프롬프트 | 모델 | 입력 | 출력 | 지연 시간 | 4.7 오버헤드 |
|---|---|---|---|---|---|
| 짧은 영문 CSS 질문 | 4.7 | 30 | 300 | 5.35초 | +43% |
| 짧은 영문 CSS 질문 | 4.6 | 21 | 400 | 6.29초 | — |
| 긴 한국어 산문 + 영문 코드 | 4.7 | 988 | 400 | 5.27초 | +13% |
| 긴 한국어 산문 + 영문 코드 | 4.6 | 872 | 400 | 8.59초 | — |

주요 발견:

- 오버헤드 비율은 콘텐츠(content) 유형에 따라 크게 달라집니다. 짧은 영어 질문은 +43퍼센트, 한국어-코드 혼합은 +13퍼센트였습니다. Test 11이 이 격차를 요인별로 분해합니다.
- 4.7은 긴 프롬프트에서 38퍼센트 더 빠릅니다(5.27초 대 8.59초).
- 긴 프롬프트에서는 두 모델 모두 `max_tokens` 상한에 도달했습니다.

## Test 3 — 병렬 도구 사용 (parallel tool use) — 기준선

**목적:** Test 8의 스키마(schema) 스케일링 테스트의 문맥(context) 역할로, 두 모델 모두가 무리 없이 처리할 것으로 예상되는 2개 도구 프롬프트에서의 기준선 동작을 확인합니다.

프롬프트: `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` + 도구 스키마 2개.

| 모델 | 입력 | 출력 | 지연 시간 | 발행된 도구 호출 수 | 비용 |
|---|---|---|---|---|---|
| Opus 4.7 | 1040 | 239 | 4.50초 | **0** | $0.056 |
| Opus 4.6 | 776 | 318 | 4.43초 | 4 | $0.059 |

주요 발견:

- Opus 4.6은 예상대로 4개의 병렬 `tool_use` 블록을 발행했습니다. Opus 4.7은 자체 지식만으로 답변했으며, 종료 사유(stop reason)는 `end_turn`, 도구 호출은 없었습니다.
- 이것이 도구 거부(tool-refusal) 패턴의 첫 관측 사례이며, Test 8이 도구 메뉴 크기에 따른 이 패턴을 본격적으로 분석합니다.

## Test 4 — Bedrock Runtime 대 Mantle + 인증(authentication) 방식 비교

**목적:** Bedrock의 Mantle 엔드포인트가 Runtime과 동일한 토큰 수를 반환하는지 확인하고, IAM 대 베어러 토큰(bearer token) 인증의 지연 시간 영향을 별도로 측정합니다.

10개 케이스(총 50회 호출) 중 30회가 Mantle 엔드포인트에서 HTTP 404로 실패했습니다. 테스트 계정이 Mantle이 요구하는 프리뷰(preview) 허용 목록에 등록되지 않았기 때문입니다. Runtime 케이스는 성공했지만, SDK 레벨의 베어러 토큰 대 IAM 구분 하의 인증 방식 비교는 이 실행에서는 결론을 내리지 못했습니다 — 분리 수정이 이후 커밋(commit)에 반영되었기 때문입니다.

Mantle 접근 권한 없이는 실행 가능한(actionable) 결론을 낼 수 없습니다. 인프라스트럭처(infrastructure) — 서비스명 `bedrock-mantle`의 raw SigV4 서명과 분리된 인증 경로 — 는 계정 허용 목록 등록 후 재실행이 가능한 상태로 준비되어 있습니다.

## Test 5 — 프롬프트 캐싱(prompt caching) — 보류

**목적:** Bedrock에서의 사용자 프롬프트 캐싱이 Anthropic SDK 응답에 관측 가능한 캐시 적중(cache-hit) 신호를 반환하는지, 그리고 웜 캐시(warm cache) 상태에서의 비용 영향을 추정합니다.

상태: 보류. 1024 토큰 임계값을 넉넉히 넘는 프롬프트에 `cache_control={"type": "ephemeral"}` 마커를 적용했음에도, 10회 호출 모두가 `cache_creation_input_tokens = 0`과 `cache_read_input_tokens = 0`을 반환했습니다. `cache_control` 페이로드(payload)는 오류 없이 수용되었으므로, 이 설정의 Bedrock 응답 스키마가 Anthropic SDK를 통해 해당 필드를 노출하지 않거나, 또는 테스트 시점에 이 기능이 해당 모델에 대해 일반 공급(General Availability) 상태가 아닌 것으로 추정됩니다. 기본 `--test all` 실행에서 제외되며, `--test 5`로는 계속 실행 가능합니다.

## Test 6 — 다중 턴(multi-turn) 대화 스케일링 (1~10턴)

**목적:** 전형적인 챗봇(chatbot) 대화 범위인 1~10턴에서 대화 턴 수에 따라 입력 토큰과 지연 시간이 어떻게 변하는지 측정합니다.

| 턴 수 | 4.6 입력 | 4.7 입력 | 4.7 오버헤드 | 4.6 지연 시간 | 4.7 지연 시간 |
|---|---|---|---|---|---|
| 1 | 107 | 150 | +40% | 5.30초 | 4.77초 |
| 3 | 297 | 437 | +47% | 7.49초 | 4.05초 |
| 5 | 491 | 721 | +47% | 7.81초 | 4.05초 |
| 10 | 879 | 1263 | +44% | 6.81초 | 4.05초 |

주요 발견:

- 이 구간에서 입력 오버헤드는 턴 수와 무관하게 +40~47퍼센트 대역에서 평평하게 유지됩니다.
- Opus 4.7 지연 시간은 이 구간에서 턴 3부터 약 4.05초로 평탄 구간(plateau)에 진입합니다. Opus 4.6은 대화 기록(history)이 길어질수록 지연 시간이 증가합니다.
- 10턴 시점에 Opus 4.7은 Opus 4.6보다 40퍼센트 빠릅니다.

## Test 7 — 스트리밍(streaming) 첫 토큰 지연 시간 (TTFT, time-to-first-token)

**목적:** 사용자가 출력을 점진적으로 보는 대화형 채팅과 IDE 환경에서 체감 지연 시간을 좌우하는 핵심 지표인 스트리밍 TTFT를 측정합니다.

| 모델 | 짧은 프롬프트 TTFT | 긴 프롬프트 TTFT |
|---|---|---|
| Opus 4.7 | 1.15 ± 0.10초 | 1.15 ± 0.18초 |
| Opus 4.6 | 1.46 ± 0.11초 | 1.59 ± 0.21초 |
| 4.7 우위 | 21% 더 빠름 | 28% 더 빠름 |

주요 발견:

- Opus 4.7의 TTFT는 이 범위에서 프롬프트 길이에 불변이며, 짧은 CSS 질문과 긴 프롬프트 양쪽 모두에서 1.15초를 유지합니다.
- Opus 4.6의 TTFT는 프롬프트 길이에 따라 증가합니다.
- 스트리밍 모드 지연 시간 격차는 다수 테스트에서 종단 간(end-to-end) 지연 시간 격차보다 큰데, 이는 대화형 UX(user experience)에 중요한 의미를 갖습니다.

## Test 8 — 도구 스키마(tool schema) 스케일링 (1 / 5 / 20개)

**목적:** 사용 가능한 도구 수가 1개에서 20개로 증가함에 따라 — 프로덕션(production) 에이전트가 노출할 만한 범위 — 입력 토큰 오버헤드와 도구 호출 동작이 어떻게 변하는지 측정합니다.

| 도구 수 | 4.6 입력 | 4.7 입력 | 4.7 오버헤드 | 4.6 호출 | 4.7 호출 |
|---|---|---|---|---|---|
| 1 | 696 | 938 | +35% | 2.0 | 2.0 |
| 5 | 1372 | 1826 | +33% | 5.0 | 0.6 |
| 20 | 3907 | 5156 | +32% | 5.0 | 0.0 |

주요 발견:

- 입력 오버헤드는 도구 수와 무관하게 +32~35퍼센트에서 평평하게 유지됩니다. 스키마 크기는 토큰당(per-token) 오버헤드를 증폭시키지 않습니다.
- Opus 4.7은 메뉴(menu)가 커질수록 점진적으로 도구 사용을 포기하며, 이 프롬프트에서 도구 20개 시점에 호출 0회에 도달합니다.
- Opus 4.6은 스케일 전반에 걸쳐 일관된 도구 호출을 유지합니다.

## Test 9 — 도구 강제 사용 (tool forcing)

**목적:** Test 8에서 대규모 도구 환경에서 관측된 4.7의 도구 거부 패턴을, 명령형(imperative) 프롬프팅 또는 `tool_choice` API 파라미터로 교정할 수 있는지 판별합니다.

Test 8에서 구축한 20개 도구 메뉴 위에서 4개 변형을 측정했습니다.

| 변형 | 방법 | 4.6 도구 호출 수 | 4.7 도구 호출 수 |
|---|---|---|---|
| 수동형(passive) | 기준선 프롬프트 | 5.0 | 0.0 |
| 명령형(imperative) | "반드시 도구를 사용하세요..." | 4.0 | 1.2 (5회 중 3회가 0) |
| choice-any | `tool_choice={"type": "any"}` | 2.0 | 2.0 |
| choice-specific | `tool_choice={"type": "tool", "name": ...}` | 2.0 | 2.0 |

주요 발견:

- `tool_choice={"type": "any"}`는 Test 8에서 관측된 4.7의 도구 거부 현상을 완전히 해소합니다. 5회 실행 모두가 일관되게 도구를 발행합니다.
- 명령형 프롬프팅만으로는 신뢰할 수 없습니다(4.7에서 준수율 40퍼센트).
- `tool_choice`는 병렬 tool_use 블록 수를 5개(4.6 수동형)에서 두 모델 모두 2개로 감소시켜, 병렬성(parallelism)과 호출 보장(invocation guarantee) 사이의 절충(trade-off)을 드러냅니다.

## Test 10 — 다중 턴 극한 (10 / 20 / 30 / 50 / 100턴)

**목적:** Test 6의 다중 턴 곡선을 극한 영역(최대 100턴)까지 확장하여, 4.7의 지연 시간 평탄 구간이 장시간 세션에서도 유지되는지 또는 붕괴하는지 확인합니다.

| 턴 수 | 4.6 입력 | 4.7 입력 | 4.7 오버헤드 | 4.6 지연 시간 | 4.7 지연 시간 |
|---|---|---|---|---|---|
| 10 | 999 | 1447 | +45% | 6.73초 | 3.95초 |
| 20 | 2117 | 3181 | +50% | 6.64초 | 4.99초 |
| 30 | 3239 | 4915 | +52% | 6.62초 | 5.04초 |
| 50 | 5489 | 8393 | +53% | 8.14초 | 5.24초 |
| 100 | 11095 | 17063 | +54% | 7.69초 | 5.75초 |

주요 발견:

- 오버헤드는 10턴의 +45퍼센트에서 100턴의 +54퍼센트로 완만하게 상승합니다.
- 4.7은 전 구간에 걸쳐 25~40퍼센트의 지연 시간 우위를 유지합니다.
- 10턴 지연 시간(3.95초)에서 20턴 지연 시간(4.99초)으로의 도약은 곡선에서 가장 큰 단일 증분(delta)입니다. Test 13이 이 경계를 더 정밀한 해상도(resolution)로 탐색합니다.

## Test 11 — 언어 및 코드 분해 (language and code decomposition)

**목적:** Test 2에서 관측된 혼합 콘텐츠 오버헤드를 언어 요소(영어 대 한국어)와 코드 요소로 분해하여, 어느 쪽이 지배적 요인(dominant factor)인지 식별합니다.

| 변형 | 4.6 입력 | 4.7 입력 | 오버헤드 | 4.6 지연 시간 | 4.7 지연 시간 |
|---|---|---|---|---|---|
| 영어 산문 | 389 | 610 | **+57%** | 11.26초 | 5.62초 |
| 한국어 산문 | 962 | 1010 | **+5%** | 8.81초 | 5.12초 |
| Python 코드 | 1260 | 1622 | **+29%** | 10.49초 | 4.83초 |
| 한국어 + 코드 혼합 | 872 | 988 | **+13%** | 8.34초 | 4.54초 |

주요 발견:

- 한국어 산문은 두 모델에서 거의 동일하게 토큰화되며(+5퍼센트), 네 가지 콘텐츠 유형 중 가장 낮은 오버헤드를 보입니다.
- 영어 기술 산문은 본 테스트에서 가장 높은 오버헤드를 기록했으며(+57퍼센트), 이는 한국어의 11배에 달합니다.
- 코드 전용 프롬프트는 +29퍼센트에 도달해 한국어와 영어의 중간쯤에 위치합니다.
- Opus 4.7은 네 가지 콘텐츠 유형 전체에서 Opus 4.6보다 1.7배에서 2.2배 빠릅니다.

## Test 12 — 시스템 프롬프트 캐싱(system prompt caching) — 보류

**목적:** Test 5에서 다룬 사용자 프롬프트 캐싱과는 별개의 API 경로인 시스템 프롬프트 캐싱이 Bedrock에서 관측 가능한 캐시 신호를 반환하는지 확인합니다.

Test 5와 동일한 널(null) 결과입니다. 2000 토큰 규모의 시스템 프롬프트에 `cache_control` 마커를 적용했음에도, 두 모델 모두에서 5회 실행 전체가 `cache_creation_input_tokens = 0`과 `cache_read_input_tokens = 0`을 반환했습니다. Bedrock의 프롬프트 캐싱 관측 가능성(observability)이 명확해질 때까지 보류합니다.

## Test 13 — 다중 턴 전환점(knee-point) (11 / 13 / 15 / 17 / 19턴)

**목적:** Test 6(1~10턴)과 Test 10(10~100턴) 사이의 해상도 공백을 메워, 4.7의 지연 시간 평탄 구간이 더 높은 구간(regime)으로 전환되는 지점을 정밀하게 위치 파악합니다.

| 턴 수 | 4.6 지연 시간 | 4.7 지연 시간 | 직전 대비 Δ (4.7) |
|---|---|---|---|
| 10 | 6.73초 | 3.95초 | — |
| 11 | 6.40초 | 3.97초 | +0.5% |
| 13 | 7.22초 | 3.74초 | −5.8% (국소 최저점) |
| 15 | 6.82초 | 4.07초 | +8.8% |
| 17 | 7.04초 | 4.18초 | +2.7% |
| 19 | 6.75초 | 4.32초 | +3.3% |
| 20 | 6.64초 | 4.99초 | **+15.5%** |
| 30 | 6.62초 | 5.04초 | +1.0% |

주요 발견:

- Opus 4.7은 턴 20에서 계단 함수(step function)를 보입니다. 단일 턴 증가로 0.68초의 도약(+16퍼센트)이 발생하며, 이후 지연 시간 곡선은 점진적 상승을 재개합니다. 이는 매끄러운 성능 저하가 아니라 임계값 교차(threshold crossing)의 형태로, 문맥 버퍼(context buffer) 또는 KV 캐시 계층(KV-cache tier) 전환의 가능성을 시사합니다. Opus 4.6은 이에 상응하는 계단을 보이지 않습니다.

## 품질 채점기(quality scorer) 결과

두 채점기 버전 모두 Claude Sonnet 4.6을 평가자(judge)로 사용하고, 쌍별 비교 형식으로 동일한 3개 프롬프트(`tools`, `short`, `proof`)를 대상으로 했습니다.

### 버전 1 — 고정 위치 (Opus 4.7이 항상 Response A)

| 프롬프트 | 4.7 승 | 4.6 승 | 무승부 |
|---|---|---|---|
| tools | 1 | 2 | 0 |
| short | 1 | 2 | 0 |
| proof | 0 | 3 | 0 |
| **합계 (9회)** | **2 (22%)** | **7 (78%)** | 0 |

### 버전 2 — A/B 위치 무작위화(randomized)

| 프롬프트 | 4.7 승 | 4.6 승 | 무승부 |
|---|---|---|---|
| tools | 2 | 3 | 0 |
| short | 0 | 3 | 2 |
| proof | 2 | 3 | 0 |
| **합계 (15회)** | **4 (27%)** | **9 (60%)** | 2 (13%) |

V2 위치 편향(position bias) 진단: 무승부가 아닌 13개 케이스 중 Response A가 9회 승리(69퍼센트)해, 평가자가 중간 수준의 위치 편향을 보임을 확인했습니다. 이 편향을 보정해도 Opus 4.6이 명확한 다수를 유지합니다.

주요 발견:

- 위치 무작위화 이후에도 쌍별 비교의 약 60퍼센트에서 Opus 4.6이 선호됩니다.
- 이 선호는 `max_tokens=400`에 의한 절단으로 일부 설명됩니다 — Opus 4.7의 더 장황한 서론 스타일은 결론에 도달하기 전에 절단되는 반면, Opus 4.6의 간결한 스타일은 상한 내에서 결론에 도달합니다.
- Opus 4.7이 Response B에 배치됐을 때는 7회 비교 중 0회 승리했습니다. Response A에 배치됐을 때는 8회 중 4회 승리했습니다. 위치 효과는 실재합니다.

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
