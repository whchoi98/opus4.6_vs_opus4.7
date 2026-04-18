# Knee-point + Quality Scorer Findings (2026-04-18 08:18 UTC)

Follow-up investigation combining Test 13 (multi-turn knee-point) + Quality
Scorer results on Tests 3, 6, 10.

Cost: Test 13 = $0.86, Scorer = $0.03. Cumulative project: ~$7.11.

---

## 🎯 Finding 1: 4.7 latency knee-point is at turn 19→20

Combining Tests 6 (1/3/5/10 turns), 13 (11/13/15/17/19 turns), and 10
(20/30/50/100 turns) gives a complete latency curve for 4.7:

| Turns | 4.7 Latency | Δ from prev |
|---|---|---|
| 1 | 4.77s | — |
| 3 | 4.05s | -15% (warmup) |
| 5 | 4.27s | +5% |
| 10 | 3.95s | -8% |
| 11 | 3.97s | +1% |
| 13 | 3.74s | -6% (local minimum) |
| 15 | 4.07s | +9% |
| 17 | 4.18s | +3% |
| 19 | 4.32s | +3% |
| **20** | **4.99s** | **+16%** ⚠️ |
| 30 | 5.04s | +1% |
| 50 | 5.24s | +4% |
| 100 | 5.75s | +10% |

**Pattern:**
- **3-19 turns: stable plateau** ~3.74-4.32s (noise-level fluctuation)
- **19→20 turns: sudden +16% step** (+0.68s in a single turn-count increment)
- **20-100 turns: slow climb** (+0.76s over 80 turns ~= +1% per turn)

**Interpretation — a step function, not smooth degradation:**
- 4.7 has some internal threshold (context buffer, attention window chunk,
  KV-cache tier?) that triggers a slower code path around 20 turns /
  ~3000 input tokens.
- Below threshold: fast stable ~4s path.
- Above threshold: slower but still linear ~5-6s path.

**Implications for agent design:**
- **Below 20 turns:** free lunch — 4.7 latency is essentially flat (3.7-4.3s).
- **Right above 20 turns:** you've paid the switching cost — you may as well
  run to 50+ turns before re-initializing.
- **For chatbots with typical 5-15 turn sessions:** 4.7 is consistently in the
  fast regime.
- **For long-running agents:** plan session compaction at turn 50-100 to keep
  costs down, latency will be ~5-6s regardless.

**Note:** 4.6 does NOT show the same step function — its latency oscillates
around 6-8s from turn 1 to turn 100 without a clear knee.

---

## 🎯 Finding 2: Quality scorer — 4.6 wins more often than expected

Ran Claude Sonnet 4.6 judge on 3 prompt types × 3 runs each = 9 pairwise
comparisons between Opus 4.7 and Opus 4.6 responses.

### Raw results

| Prompt | 4.7 better | 4.6 better | Tie |
|---|---|---|---|
| tools | 1 | 2 | 0 |
| short (CSS question) | 1 | 2 | 0 |
| proof (prime infinity) | 0 | 3 | 0 |
| **Total** | **2** | **7** | **0** |

### 4.6 wins reasoning (from judge rationales)

**tools prompt:**
- Runs 1 & 3: "Response B [4.6] directly attempts to answer with tool calls;
  Response A [4.7] unnecessarily asks for clarification."
- Run 2: "Response A [4.7] correctly identifies ambiguity and asks for
  clarification before wasting tool calls."
- **Split opinion** — judge values either "direct action" or "careful
  disambiguation" depending on the run.

**short prompt (CSS):**
- Similar split — judge prefers 4.6's concise answer on 2 runs, 4.7's
  thoroughness on 1.

**proof prompt:**
- All 3 runs: "Response B [4.6] gets further into the actual proof before
  being truncated; Response A [4.7] spends more time on preliminaries."
- **Systematic 4.6 win.** Both hit max_tokens=400. 4.6 truncated while
  discussing the core contradiction; 4.7 truncated while setting up lemmas.

### Important caveats

1. **Position bias.** The judge saw 4.7 = Response A and 4.6 = Response B in
   every comparison. LLM judges exhibit bias toward the second response
   (typically Response B) in some studies. A proper eval would randomize
   A/B assignment across runs. We did not do that here.

2. **max_tokens cap artifact.** With `max_tokens=400`, both models get
   truncated mid-output. 4.7's more verbose preamble style means its
   truncation happens during setup, while 4.6's terser style reaches the
   conclusion before cutoff. This isn't a quality difference — it's a style
   difference that interacts badly with token caps.

3. **Tools scorer has no real tool results.** In our setup, "tool_use" blocks
   are emitted but never actually executed. 4.6 emits tool_use blocks (judge
   sees them as "direct action"); 4.7 asks for clarification in plain text.
   The judge scores this as "4.6 took action." In production with real tool
   results, 4.7's clarification might be the better UX.

### Actual insight (despite the caveats)

**4.7 is more verbose and setup-oriented than 4.6.**

This is new information not present in the token/latency benchmarks.
Practical implications:

- **Keep `max_tokens` generous with 4.7** — it uses more preamble and will
  be truncated before reaching the answer if the cap is tight.
- **For terse-output requirements** (API responses, UI cards, short answers)
  4.6 may actually be better suited — no preamble, straight to the point.
- **For long-form responses** (research summaries, architecture reviews,
  teaching), 4.7's structured setup may be a feature, not a bug.

---

## Updated decision matrix (with quality considered)

| Workload | 4.7 | 4.6 | Why |
|---|---|---|---|
| Korean chatbot | ✅ | — | +5% overhead, 1.7x speed (Test 11) |
| Terse API responses (constrained max_tokens) | — | ✅ | 4.6 reaches conclusion faster (scorer) |
| Long-form technical writing | ✅ | — | 4.7's preamble adds structure (scorer) |
| Agent sessions 5-19 turns | ✅ | — | Below knee, 4s latency (Test 13) |
| Agent sessions 20+ turns | ✅ (w/ compaction) | ✅ | Post-knee, 5-6s latency steady |
| Decisive-action agent | — | ✅ | 4.7 over-asks clarification (scorer) |
| Large toolset (10+) agent | ✅ w/ tool_choice | ⚠️ | tool_choice required (Test 9) |

## Open questions still outstanding

1. **Why the turn 20 step function?** Architectural feature of 4.7?
   Regression? KV-cache sizing? Worth AWS Support investigation.
2. **Is the scorer position bias real?** Re-run with randomized A/B to confirm.
3. **4.7 preamble style — is this tunable via system prompt?** A system
   prompt saying "Be terse, no preambles" might flip the verbosity and
   change the scorer outcome.
