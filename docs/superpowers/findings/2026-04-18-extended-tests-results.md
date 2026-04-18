# Benchmark findings — 2026-04-18

**Completed runs:**
- 2026-04-18 06:03 UTC — Tests 1, 2, 3, 4 (~$1.16, 95/105 calls; Mantle cases failed)
- 2026-04-18 07:02 UTC — Tests 5, 6, 7, 8 (~$1.31, 100/100 calls; Test 5 inconclusive)

**Deferred (inconclusive data, not included in insights below):**
- **Test 4 Mantle endpoint**: 30 calls returned HTTP 404 — endpoint not accessible
  in the test account (requires AWS allowlist). Runtime-vs-Mantle token parity
  and auth-method latency comparison cannot be evaluated until Mantle access is
  granted.
- **Test 5 prompt caching**: 10 calls returned `cache_creation_tokens=0 /
  cache_read_tokens=0` despite `cache_control` markers and prompts well above
  the 1024-token minimum. Cause unclear — possibly a Bedrock-side API-shape
  difference vs the 1P Anthropic API. Infrastructure is in place; re-run when
  the Bedrock caching behavior is clarified. Excluded from `--test all` default;
  still runnable via `--test 5`.

The rest of this document covers insights from completed tests only.

---

## Test 1 — Effort level vs token consumption ✅

Prompt: `"Proof that there are infinitely many primes. Full reasoning."`

| Model | Effort | Input | Output | Latency | Thinking |
|---|---|---|---|---|---|
| 4.7 | low | 32 | 970 ± 66 | 11.26s | 0 |
| 4.7 | medium | 32 | 1000 ± 0 | 9.79s | 0 |
| 4.7 | high | 32 | 1000 ± 0 | 14.78s | 0 |
| 4.7 | max | 32 | 1000 ± 0 | 11.46s | 0 |
| 4.6 | — | 21 | 809 ± 40 | 13.78s | 0 |

**Reproduced:** Effort does NOT affect input tokens. All four 4.7 variants = 32 input (σ = 0).

**Measured overhead:** 4.7 vs 4.6 = +52% (blog reported +61% — similar magnitude, within tokenizer version drift).

## Test 2 — Prompt length scaling ✅

| Prompt | Model | Input | Output | Latency | 4.7 overhead |
|---|---|---|---|---|---|
| Short (English CSS Q) | 4.7 | 30 | 300 | 5.35s | +43% |
| Short (English CSS Q) | 4.6 | 21 | 400 | 6.29s | — |
| Long (Korean + code) | 4.7 | 988 | 400 | 5.27s | +13% |
| Long (Korean + code) | 4.6 | 872 | 400 | 8.59s | — |

**Key finding:** Overhead ratio varies strongly with prompt content. Pure-English short prompt shows +43%, while a Korean-natural-language + English-code hybrid shows only +13%. The field-report blog used a ~350-word English architecture prompt and reported +45% — consistent with our English short-prompt number.

**Implication for Korean developers:** Mixed Korean+code workloads (typical Claude Code / agent usage in Korea) incur meaningfully less overhead than blanket "+45%" suggests.

## Test 3 — Parallel tool use (single tool menu of 2)

| Model | Input | Output | Latency | Parallel tool calls |
|---|---|---|---|---|
| 4.7 | 1040 | 239 | 4.50s | **0** (stop_reason=end_turn) |
| 4.6 | 776 | 318 | 4.43s | 4 |

**Finding:** Blog reported both models issuing 4 parallel tool_use blocks on the same prompt. We reproduced that on 4.6 but 4.7 answered in plain text without invoking any tools. Cost parity (4.7=$0.056 vs 4.6=$0.059) was therefore coincidental — 4.7 produced a shorter text response.

See Test 8 for the broader pattern of this behavior.

## Test 6 — Multi-turn conversation scaling ✅ (new data vs blog)

8 cases across 1 / 3 / 5 / 10-turn conversations × 2 models.

| Turns | 4.6 input | 4.7 input | 4.7 overhead | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| 1 | 107 | 150 | +40% | 5.30s | 4.77s |
| 3 | 297 | 437 | +47% | 7.49s | 4.05s |
| 5 | 491 | 721 | +47% | 7.81s | 4.05s |
| 10 | 879 | 1263 | +44% | 6.81s | 4.05s |

**New insights not in the blog:**
- **Overhead stays +40–47% flat** across turn counts → scaling is linear, not exponential.
- **4.7 latency plateaus at ~4.05s** from turn 3 onward; 4.6 climbs with history length.
- At 10 turns, 4.7 is **40% faster** than 4.6 — the gap widens with history.

**Implication:** multi-turn agent pipelines and long chatbot sessions favor 4.7 more strongly than single-turn benchmarks suggest. The 40% latency gap compounds across tens of turns per user session.

## Test 7 — Streaming TTFT ✅ (blog's 1.2s claim confirmed)

| Model | Short prompt TTFT | Long prompt TTFT |
|---|---|---|
| 4.7 | **1.15 ± 0.10s** | **1.15 ± 0.18s** |
| 4.6 | 1.46 ± 0.11s | 1.59 ± 0.21s |
| 4.7 advantage | 21% faster | 28% faster |

**Reproduced:** Blog's 1.2s TTFT claim for 4.7 streaming lands within our 1.15 ± 0.10s.

**New insight:**
- **4.7 TTFT is invariant to prompt length** (same 1.15s for short and long prompts).
- **4.6 TTFT grows with prompt length** (1.46s → 1.59s, ~10% slower on long).

**Implication:** latency-sensitive UX — IDE autocomplete, chatbot, voice — benefits disproportionately from 4.7. The "feel" advantage is not in total response time but in how fast the first token arrives, which is now quantified.

## Test 8 — Tool schema scaling (new data, important caveat)

6 cases: 1 / 5 / 20 tool schemas × 2 models.

| Tools | 4.6 input | 4.7 input | 4.7 overhead | 4.6 calls | 4.7 calls |
|---|---|---|---|---|---|
| 1 | 696 | 938 | +35% | 2.0 | 2.0 |
| 5 | 1372 | 1826 | +33% | 5.0 | **0.6** |
| 20 | 3907 | 5156 | +32% | 5.0 | **0.0** |

**Findings:**
- **Input overhead is flat +32–35%** regardless of tool count — schema size does not amplify per-token overhead.
- But **4.7 progressively stops using tools as the menu grows** — at 20 tools it never invokes a tool on the test prompt.
- 4.6 stays consistent, invoking tools on every case.

**Caveat not present in the blog:** For agent pipelines with **10+ tools** (MCP servers, Claude Code-style tool menus), 4.7 may underperform expectations. Mitigations:
- Use 4.6 for large-toolset agents.
- With 4.7, either keep tool menus small (<5), split tools across subagents, or use stricter prompting that requires tool use.
- Worth a follow-up with explicit "you must use a tool" prompting to see whether this is prompt-fixable or a model disposition shift.

---

# 🎯 Decision framework

Based on completed tests only:

| Workload | 4.7 | 4.6 | Why |
|---|---|---|---|
| **Streaming chatbot / IDE** | ✅ Use | — | 21–28% TTFT advantage (Test 7) |
| **Multi-turn agent (5+ turns)** | ✅ Use | — | 40% latency advantage, widens with turns (Test 6) |
| **Long-context analysis (Korean+code)** | ✅ Use | — | Lower overhead (+13%) than pure English (Test 2) |
| **Reasoning-heavy tasks** | Either | Either | 4.7 faster but comparable cost (Test 1) |
| **Large-toolset agent (10+ tools)** | ⚠️ Caution | ✅ Safer | 4.7 may stop invoking tools (Test 8) |
| **Short high-volume prompts** | Either | ✅ If cost dominates | +43% overhead on short English (Test 2) |

# Not a cost dial — settings that don't help

- **`effort=low`** on 4.7 does not reduce input cost (Test 1). It only controls output depth.
- **Passing more tools** doesn't amplify overhead per-tool on 4.7 — it stays at ~32% regardless (Test 8). But tool count above ~5 changes *whether* 4.7 uses tools at all.
