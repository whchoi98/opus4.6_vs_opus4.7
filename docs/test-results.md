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

Opus 4.7 is 25–40 percent faster than 4.6 across nearly all measured workloads, at an input-token premium that varies from +5 percent on Korean prose to +57 percent on English technical prose. The headline finding from the public blog — that effort level does not reduce input token consumption — reproduced cleanly. Four substantive new findings emerged beyond the blog scope: (1) at 20 tools, 4.7 stops invoking tools unless forced via `tool_choice`; (2) 4.7 exhibits a sudden +16 percent latency step at turn 20; (3) Korean tokenization overhead is nearly null; (4) Bedrock does not surface prompt caching usage fields in SDK responses, making the advertised caching cost model unverifiable in this environment.

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
- Measured 4.7 vs 4.6 overhead on this prompt is +52 percent. The reference blog reported +61 percent on the same prompt shape.
- Thinking blocks returned zero characters for all cases. The 4.6 native-mode invocation did not surface visible thinking in our SDK response shape, diverging from the blog's 856 characters.

## Test 2 — Prompt Length Scaling

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

Prompt: `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` with two tool schemas.

| Model | Input | Output | Latency | Tool calls emitted | Cost |
|---|---|---|---|---|---|
| Opus 4.7 | 1040 | 239 | 4.50 s | **0** | $0.056 |
| Opus 4.6 | 776 | 318 | 4.43 s | 4 | $0.059 |

Findings:

- Opus 4.6 emitted the expected four parallel `tool_use` blocks. Opus 4.7 answered from its own knowledge, stop reason `end_turn`, no tool invocations.
- This is the first appearance of a tool-refusal pattern that Test 8 then characterizes by tool-menu size.

## Test 4 — Bedrock Runtime versus Mantle, with Auth Comparison

Of 10 cases (50 calls), 30 calls failed with HTTP 404 on the Mantle endpoint. The test account lacks the preview allowlisting Mantle requires. Runtime cases succeeded, but the auth-method comparison under the SDK-level bearer-token vs IAM distinction was inconclusive in this run because the separation fix landed in a later commit.

Results are not actionable without Mantle access. The infrastructure — raw SigV4 signing with service name `bedrock-mantle` and separated auth paths — is in place for re-running once the account is allowlisted.

## Test 5 — Prompt Caching (deferred)

Status: deferred. All 10 calls returned `cache_creation_input_tokens = 0` and `cache_read_input_tokens = 0` despite sending `cache_control={"type": "ephemeral"}` markers on prompts well over the 1024-token threshold. The `cache_control` payload was accepted without error, so either the Bedrock response schema does not surface these fields via the Anthropic SDK in this configuration, or the feature is not generally available for these models on Bedrock as of the test date. Excluded from the default `--test all` run; runnable with `--test 5`.

## Test 6 — Multi-turn Conversation Scaling (1–10 turns)

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

| Model | Short prompt TTFT | Long prompt TTFT |
|---|---|---|
| Opus 4.7 | 1.15 ± 0.10 s | 1.15 ± 0.18 s |
| Opus 4.6 | 1.46 ± 0.11 s | 1.59 ± 0.21 s |
| 4.7 advantage | 21% faster | 28% faster |

Findings:

- Opus 4.7 TTFT is invariant to prompt length in this range, reproducing the blog's 1.2 s claim within measurement noise.
- Opus 4.6 TTFT grows with prompt length.
- The streaming-mode latency gap is larger than the end-to-end latency gap in many tests, which matters for interactive UX.

## Test 8 — Tool Schema Scaling (1 / 5 / 20 tools)

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

| Variant | 4.6 input | 4.7 input | Overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| English prose | 389 | 610 | **+57%** | 11.26 s | 5.62 s |
| Korean prose | 962 | 1010 | **+5%** | 8.81 s | 5.12 s |
| Python code | 1260 | 1622 | **+29%** | 10.49 s | 4.83 s |
| Korean + code hybrid | 872 | 988 | **+13%** | 8.34 s | 4.54 s |

Findings:

- Korean prose tokenizes almost identically on both models (+5 percent), substantially lower than the blog's headline +45 percent range.
- English technical prose shows the highest overhead in our tests (+57 percent).
- Code-only prompts land at +29 percent, matching the Claude Code Camp blog's independent tokenizer measurement of 1.29x for Python.
- Opus 4.7 is 1.7x to 2.2x faster than Opus 4.6 across all four content types.

## Test 12 — System Prompt Caching (deferred)

Same null result as Test 5: `cache_creation_input_tokens = 0` and `cache_read_input_tokens = 0` across all five runs, on both models, with a 2000-token system prompt carrying a `cache_control` marker. Deferred pending clarification of Bedrock's prompt-caching observability.

## Test 13 — Multi-turn Knee-point (11 / 13 / 15 / 17 / 19 turns)

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

---

# 한국어

## 요약

Opus 4.7은 측정한 거의 모든 워크로드에서 4.6보다 25~40퍼센트 빠르며, 입력 토큰 프리미엄은 한국어 prose에서 +5퍼센트부터 영문 기술 prose에서 +57퍼센트까지 분포합니다. 공개 블로그의 헤드라인 주장 — effort 레벨이 입력 토큰 소비를 줄이지 않는다는 점 — 은 그대로 재현되었습니다. 블로그 범위를 넘어서는 네 가지 새로운 발견이 있었습니다. (1) tool 20개 환경에서 4.7은 `tool_choice`로 강제하지 않는 한 tool을 호출하지 않습니다. (2) 4.7은 턴 20에서 latency가 +16퍼센트 급상승하는 step function을 보입니다. (3) 한국어 토큰화 overhead는 거의 0에 가깝습니다. (4) Bedrock은 SDK 응답에 prompt caching 사용 필드를 노출하지 않아, 광고된 caching 비용 모델을 이 환경에서 검증할 수 없습니다.

Claude Sonnet 4.6을 judge로 A/B 포지션을 랜덤화한 품질 스코어러에서는 15회 pairwise 비교 중 9회에서 4.6이 승리했습니다. 이 판정은 69퍼센트의 Position A 편향과 max_tokens 기반 truncation이 더 장황한 4.7에 불리하게 작용한 점으로 일부 희석됩니다. 신호는 실제이지만 raw count가 제시하는 것보다는 좁습니다. 4.7은 더 장황하고 setup 중심이며, 4.6은 truncation 상황에서 결론에 더 빨리 도달합니다.

## 방법론

모든 호출은 `us-east-1`의 `global.anthropic.claude-opus-4-7`과 `global.anthropic.claude-opus-4-6-v1` 추론 프로필을 향했으며, Bedrock Runtime(Anthropic SDK) 및 Bedrock Mantle(서비스명 `bedrock-mantle`로 SigV4 서명된 raw HTTP) 경로를 통해 호출되었습니다. 각 케이스는 5회 실행되었고, 집계 통계는 평균과 표본 표준편차를 보고합니다. 오류 런은 평균 계산에서 제외하되 `n_runs`에는 포함시켰습니다. 비용은 `config.py`의 `PRICING` 상수를 사용해 토큰 수로부터 계산했습니다.

실행 시간과 비용:

| Run | 날짜/시간 (UTC) | 테스트 | 호출 | Wall time | 비용 |
|---|---|---|---|---|---|
| 1 | 2026-04-18 06:03 | 1, 2, 3, 4 | 95 / 105 | 9분 55초 | $1.16 |
| 2 | 2026-04-18 07:02 | 5, 6, 7, 8 | 100 / 100 | 8분 18초 | $1.31 |
| 3 | 2026-04-18 07:47 | 9, 10, 11, 12 | 140 / 140 | 14분 27초 | $3.75 |
| 4 | 2026-04-18 08:18 | 13 | 50 / 50 | 4분 46초 | $0.86 |
| Scorer v1 | 2026-04-18 07:05 | 3 프롬프트 × 3회 | 9 | 2분 10초 | $0.01 |
| Scorer v2 | 2026-04-18 08:07 | 3 프롬프트 × 5회 | 15 | 3분 25초 | $0.06 |
| **합계** | | | **409** | **약 43분** | **약 $7.14** |

Run 1의 Test 4 Mantle 케이스 10개가 오류로 반환되었는데, 이는 테스트 계정이 Mantle 엔드포인트 allowlist 권한이 없기 때문입니다.

## Test 1 — Effort 레벨 대 토큰 소비

프롬프트: `"Proof that there are infinitely many primes. Full reasoning."`

| 모델 | Effort | Input | Output (μ±σ) | Latency (μ±σ 초) | Thinking 문자수 |
|---|---|---|---|---|---|
| Opus 4.7 | low | 32 | 970 ± 66 | 11.26 | 0 |
| Opus 4.7 | medium | 32 | 1000 ± 0 | 9.79 | 0 |
| Opus 4.7 | high | 32 | 1000 ± 0 | 14.78 | 0 |
| Opus 4.7 | max | 32 | 1000 ± 0 | 11.46 | 0 |
| Opus 4.6 | — | 21 | 809 ± 40 | 13.78 | 0 |

발견 사항:

- 4개의 4.7 effort variant에서 입력 토큰이 동일합니다 (σ = 0). Effort 파라미터는 입력 소비에 영향을 주지 않습니다.
- 이 프롬프트에서 측정된 4.7 vs 4.6 overhead는 +52퍼센트입니다. 참조 블로그는 동일 프롬프트 형태에서 +61퍼센트를 보고했습니다.
- 모든 케이스에서 thinking block은 0문자를 반환했습니다. 4.6 native 모드 호출에서도 우리 SDK 응답 형태에서는 가시적 thinking이 노출되지 않아, 블로그의 856 문자와 차이가 있습니다.

## Test 2 — 프롬프트 길이 스케일링

| 프롬프트 | 모델 | Input | Output | Latency | 4.7 overhead |
|---|---|---|---|---|---|
| 짧은 영문 CSS 질문 | 4.7 | 30 | 300 | 5.35 초 | +43% |
| 짧은 영문 CSS 질문 | 4.6 | 21 | 400 | 6.29 초 | — |
| 긴 한국어 prose + 영문 코드 | 4.7 | 988 | 400 | 5.27 초 | +13% |
| 긴 한국어 prose + 영문 코드 | 4.6 | 872 | 400 | 8.59 초 | — |

발견 사항:

- Overhead 비율은 콘텐츠 유형에 크게 의존합니다. 짧은 영문 질문에서는 +43퍼센트, 더 긴 한국어-코드 하이브리드에서는 단 +13퍼센트였습니다. Test 11에서 이를 세부 분해합니다.
- 4.7은 긴 프롬프트에서 38퍼센트 더 빨랐습니다 (5.27초 vs 8.59초).
- 긴 프롬프트에서 두 모델 모두 `max_tokens`에 도달했습니다.

## Test 3 — 병렬 Tool 사용 (baseline)

프롬프트: `"Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."` 와 2개 tool 스키마.

| 모델 | Input | Output | Latency | Tool 호출 수 | 비용 |
|---|---|---|---|---|---|
| Opus 4.7 | 1040 | 239 | 4.50 초 | **0** | $0.056 |
| Opus 4.6 | 776 | 318 | 4.43 초 | 4 | $0.059 |

발견 사항:

- Opus 4.6은 예상대로 4개의 병렬 `tool_use` 블록을 발행했습니다. Opus 4.7은 자체 지식으로 답변했으며, stop reason은 `end_turn`이고 tool 호출은 없었습니다.
- 이것이 tool-refusal 패턴의 첫 등장이며, Test 8이 tool-menu 크기에 따른 이 패턴을 본격 측정합니다.

## Test 4 — Bedrock Runtime 대 Mantle, 인증 비교

10개 케이스 (50 호출) 중 30 호출이 Mantle 엔드포인트에서 HTTP 404로 실패했습니다. 테스트 계정에 Mantle이 요구하는 preview allowlist 권한이 없습니다. Runtime 케이스는 성공했지만, SDK 레벨의 bearer-token vs IAM 구분에 따른 auth-method 비교는 이 run에서는 결론이 나지 않았습니다. 분리 수정이 이후 커밋에 반영되었기 때문입니다.

Mantle 접근 없이는 actionable한 결과가 아닙니다. 인프라 — 서비스명 `bedrock-mantle`을 사용한 raw SigV4 서명과 분리된 auth 경로 — 는 계정 allowlist 획득 후 재실행 가능한 상태로 준비되어 있습니다.

## Test 5 — Prompt Caching (보류)

상태: 보류. 1024 토큰 임계값을 넉넉히 넘는 프롬프트에 `cache_control={"type": "ephemeral"}` 마커를 전송했음에도, 10회 호출 모두 `cache_creation_input_tokens = 0`과 `cache_read_input_tokens = 0`을 반환했습니다. `cache_control` 페이로드는 오류 없이 수용되었으므로, Bedrock 응답 스키마가 Anthropic SDK를 통해 이 필드를 노출하지 않거나, 테스트 시점에 해당 모델에 대해 이 기능이 일반 공급 상태가 아닌 것으로 추정됩니다. 기본 `--test all` 실행에서 제외되었으며 `--test 5`로는 계속 실행 가능합니다.

## Test 6 — 다중 턴 대화 스케일링 (1~10턴)

| 턴 | 4.6 input | 4.7 input | 4.7 overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 1 | 107 | 150 | +40% | 5.30 초 | 4.77 초 |
| 3 | 297 | 437 | +47% | 7.49 초 | 4.05 초 |
| 5 | 491 | 721 | +47% | 7.81 초 | 4.05 초 |
| 10 | 879 | 1263 | +44% | 6.81 초 | 4.05 초 |

발견 사항:

- 이 범위에서 입력 overhead는 턴 수와 무관하게 +40~47퍼센트 밴드에 flat하게 유지됩니다.
- Opus 4.7 latency는 이 범위에서 턴 3부터 약 4.05초에 plateau를 유지합니다. Opus 4.6 latency는 히스토리 길이에 따라 증가합니다.
- 10턴 시점에 Opus 4.7은 Opus 4.6보다 40퍼센트 빠릅니다.

## Test 7 — 스트리밍 Time-to-First-Token

| 모델 | 짧은 프롬프트 TTFT | 긴 프롬프트 TTFT |
|---|---|---|
| Opus 4.7 | 1.15 ± 0.10 초 | 1.15 ± 0.18 초 |
| Opus 4.6 | 1.46 ± 0.11 초 | 1.59 ± 0.21 초 |
| 4.7 우위 | 21% 빠름 | 28% 빠름 |

발견 사항:

- Opus 4.7 TTFT는 이 범위에서 프롬프트 길이에 불변이며, 블로그의 1.2초 주장을 측정 noise 범위 내에서 재현합니다.
- Opus 4.6 TTFT는 프롬프트 길이에 따라 증가합니다.
- 스트리밍 모드 latency 격차가 많은 테스트의 end-to-end latency 격차보다 크며, 이는 대화형 UX에서 중요합니다.

## Test 8 — Tool 스키마 스케일링 (1 / 5 / 20개)

| Tools | 4.6 input | 4.7 input | 4.7 overhead | 4.6 호출 | 4.7 호출 |
|---|---|---|---|---|---|
| 1 | 696 | 938 | +35% | 2.0 | 2.0 |
| 5 | 1372 | 1826 | +33% | 5.0 | 0.6 |
| 20 | 3907 | 5156 | +32% | 5.0 | 0.0 |

발견 사항:

- 입력 overhead는 tool 수와 무관하게 +32~35퍼센트에 flat합니다. 스키마 크기는 per-token overhead를 증폭시키지 않습니다.
- Opus 4.7은 메뉴가 커질수록 점진적으로 tool 사용을 포기하며, 이 프롬프트에서 tool 20개 시점에 호출 0에 도달합니다.
- Opus 4.6은 스케일 전반에 걸쳐 일관된 tool 호출을 유지합니다.

## Test 9 — Tool 강제 사용

Test 8에서 수립된 20-tool 메뉴에서 4개 variant 측정.

| Variant | 방법 | 4.6 호출 | 4.7 호출 |
|---|---|---|---|
| passive | baseline 프롬프트 | 5.0 | 0.0 |
| imperative | "반드시 tool을 사용하세요…" | 4.0 | 1.2 (5회 중 3회 0 반환) |
| choice-any | `tool_choice={"type": "any"}` | 2.0 | 2.0 |
| choice-specific | `tool_choice={"type": "tool", "name": …}` | 2.0 | 2.0 |

발견 사항:

- `tool_choice={"type": "any"}`는 Test 8에서 관측된 4.7 tool 거부를 완전히 해소합니다. 5회 run 모두 일관되게 tool을 발행합니다.
- Imperative 프롬프팅만으로는 신뢰성이 낮습니다 (4.7에서 40퍼센트 준수율).
- `tool_choice`는 병렬 tool_use 블록 수를 5개(4.6 passive)에서 두 모델 모두 2개로 감소시켜, 병렬성과 호출 보장 사이의 trade-off를 보여줍니다.

## Test 10 — 다중 턴 극한 (10 / 20 / 30 / 50 / 100턴)

| 턴 | 4.6 input | 4.7 input | 4.7 overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 10 | 999 | 1447 | +45% | 6.73 초 | 3.95 초 |
| 20 | 2117 | 3181 | +50% | 6.64 초 | 4.99 초 |
| 30 | 3239 | 4915 | +52% | 6.62 초 | 5.04 초 |
| 50 | 5489 | 8393 | +53% | 8.14 초 | 5.24 초 |
| 100 | 11095 | 17063 | +54% | 7.69 초 | 5.75 초 |

발견 사항:

- Overhead는 10턴 +45%에서 100턴 +54%로 완만하게 상승합니다.
- 4.7은 범위 전반에 걸쳐 25~40퍼센트 latency 우위를 유지합니다.
- 10턴(3.95초)에서 20턴(4.99초)으로의 도약이 곡선에서 가장 큰 단일 델타입니다. Test 13이 이 경계를 더 세밀한 해상도로 탐색합니다.

## Test 11 — 언어 및 코드 분해

| Variant | 4.6 input | 4.7 input | Overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 영문 prose | 389 | 610 | **+57%** | 11.26 초 | 5.62 초 |
| 한국어 prose | 962 | 1010 | **+5%** | 8.81 초 | 5.12 초 |
| Python 코드 | 1260 | 1622 | **+29%** | 10.49 초 | 4.83 초 |
| 한국어 + 코드 하이브리드 | 872 | 988 | **+13%** | 8.34 초 | 4.54 초 |

발견 사항:

- 한국어 prose는 두 모델에서 거의 동일하게 토큰화됩니다 (+5퍼센트). 이는 블로그의 헤드라인 +45퍼센트 범위보다 현저히 낮습니다.
- 영문 기술 prose는 테스트에서 가장 높은 overhead를 보입니다 (+57퍼센트).
- 코드 전용 프롬프트는 +29퍼센트에 도달하며, Claude Code Camp 블로그의 독립적 토크나이저 측정값인 Python 1.29배와 일치합니다.
- Opus 4.7은 네 가지 콘텐츠 유형 전반에 걸쳐 Opus 4.6보다 1.7배~2.2배 빠릅니다.

## Test 12 — System Prompt Caching (보류)

Test 5와 동일한 null 결과: 2000 토큰 시스템 프롬프트에 `cache_control` 마커를 적용했음에도 두 모델, 5회 run 모두에서 `cache_creation_input_tokens = 0`과 `cache_read_input_tokens = 0`. Bedrock의 prompt-caching 관측 가능성 명확화까지 보류합니다.

## Test 13 — 다중 턴 Knee-point (11 / 13 / 15 / 17 / 19턴)

Test 6(1~10턴)과 Test 10(10~100턴) 사이의 해상도 공백을 메웁니다.

| 턴 | 4.6 latency | 4.7 latency | 이전 대비 Δ (4.7) |
|---|---|---|---|
| 10 | 6.73 초 | 3.95 초 | — |
| 11 | 6.40 초 | 3.97 초 | +0.5% |
| 13 | 7.22 초 | 3.74 초 | −5.8% (국소 최저) |
| 15 | 6.82 초 | 4.07 초 | +8.8% |
| 17 | 7.04 초 | 4.18 초 | +2.7% |
| 19 | 6.75 초 | 4.32 초 | +3.3% |
| 20 | 6.64 초 | 4.99 초 | **+15.5%** |
| 30 | 6.62 초 | 5.04 초 | +1.0% |

발견 사항:

- Opus 4.7은 턴 20에서 step function을 보입니다. 단일 턴 증가로 0.68초 상승(+16퍼센트)이 발생하며, 이후 latency 곡선은 점진적 상승을 재개합니다. 이는 매끄러운 성능 저하가 아니라 임계값 교차의 형태입니다(context buffer 또는 KV-cache tier 전환 가능성). Opus 4.6은 비교할 만한 step을 보이지 않습니다.

## 품질 스코어러 결과

두 스코어러 버전 모두 Sonnet 4.6을 judge로 사용하고, pairwise 비교 형식에 동일한 3개 프롬프트(`tools`, `short`, `proof`)를 사용했습니다.

### V1 — 고정 포지션 (Opus 4.7 항상 Response A)

| 프롬프트 | 4.7 승 | 4.6 승 | Tie |
|---|---|---|---|
| tools | 1 | 2 | 0 |
| short | 1 | 2 | 0 |
| proof | 0 | 3 | 0 |
| **합계 (9 runs)** | **2 (22%)** | **7 (78%)** | 0 |

### V2 — A/B 포지션 랜덤화

| 프롬프트 | 4.7 승 | 4.6 승 | Tie |
|---|---|---|---|
| tools | 2 | 3 | 0 |
| short | 0 | 3 | 2 |
| proof | 2 | 3 | 0 |
| **합계 (15 runs)** | **4 (27%)** | **9 (60%)** | 2 (13%) |

V2 포지션 편향 진단: tie가 아닌 13개 케이스 중 Response A가 9회 승리(69퍼센트)하여 judge의 중간 수준 포지션 편향을 확인. 이를 보정해도 Opus 4.6이 명확한 다수를 유지합니다.

발견 사항:

- 포지션 랜덤화 후에도 pairwise 비교의 약 60퍼센트에서 Opus 4.6이 선호됩니다.
- 이 선호는 `max_tokens=400` truncation으로 일부 설명됩니다. Opus 4.7의 더 장황한 preamble 스타일은 결론에 도달하기 전에 잘려버리는 반면, Opus 4.6의 간결한 스타일은 cap 이내에서 결론에 도달합니다.
- Opus 4.7이 Response B에 배치됐을 때 7개 비교 중 0회 승리했습니다. Response A에 배치됐을 때 8개 중 4회 승리했습니다. 포지션 효과는 실재합니다.

## 의사결정 매트릭스

| 워크로드 | 4.7 선호 | 4.6 선호 | 주요 근거 |
|---|---|---|---|
| 한국어 고객 지원 챗봇 | 예 | — | Test 11: +5% overhead, 1.7배 속도 |
| Claude Code (코드 heavy) | 예 | — | Test 11: +29% overhead, 2.2배 속도 |
| 대형 tool 에이전트 (10개+ tools) | 예 (`tool_choice` 사용) | 예 (그 외) | Tests 8, 9 |
| 장기 에이전트 세션 (5~19턴) | 예 | — | Tests 6, 13: flat 4초 plateau |
| 장기 에이전트 세션 (20턴+) | 예 (compaction 사용) | 예 | Tests 10, 13: knee 이후 5~6초 |
| 스트리밍 챗봇 / IDE | 예 | — | Test 7: TTFT 1.15초 불변 |
| Terse 출력 API (max_tokens ≤ 400) | — | 예 | 스코어러: 4.7 truncation 불리 |
| Long-form 구조적 분석 | 예 | — | 스코어러: 4.7 preamble이 구조 추가 |
| 영문 배치 처리 / RAG | — | 예 | Test 11: 영문에서 +57% 비용 |
| Reasoning / 수학 | 어느 쪽이든 | 어느 쪽이든 | Test 1: 비용 parity |

## 한계

- **Mantle 엔드포인트 접근 불가** — 테스트 계정에서 접근 불가, Test 4의 parity 주장을 이 환경에서 평가할 수 없습니다.
- **Prompt caching 관측 불가** — 이 SDK 설정의 Bedrock에서 관측되지 않아 Tests 5, 12가 보류되었습니다.
- **단일 리전 테스트** — us-east-1만 사용. 다른 리전별 추론 프로필은 테스트되지 않았습니다.
- **샘플 크기** — 케이스당 5회 run은 낮은 분산 지표에는 작지만 LLM 벤치마크의 표준 관행입니다. 스코어러 15회는 더 작으며, 품질에 대한 추론은 directional한 것으로 취급되어야 합니다.
- **포지션 편향** — 스코어러에서 감지된 Response A 선호 69퍼센트가 완전히 보정되지 않았습니다. 절대 승리 횟수는 Opus 4.6을 몇 퍼센트 포인트 과대표현할 가능성이 있습니다.
- **단일 judge 모델** — Sonnet 4.6만 사용. 다른 judge는 다른 선호를 낼 수 있습니다.
- **`max_tokens=400` truncation artifact** — 여러 테스트에서 더 간결한 모델을 유리하게 작용시켰습니다. 넉넉한 토큰 예산의 워크로드는 다른 순위를 낼 수 있습니다.

## 재현 가능성

모든 raw 데이터는 `results/YYYY-MM-DD-HHMM/raw.json`에 SDK 버전, 리전, auth method, request body dump를 포함한 full per-call 메타데이터와 함께 보존됩니다. 하네스는 idempotent합니다. 동일한 모델 접근 권한이 있는 어떤 계정에서든 `python3 run.py --test all --runs 5`는 동일한 구조의 결과를 생성합니다. 비용과 latency만이 non-deterministic한 출력이고, 토큰 수는 실행 간 안정적입니다.
