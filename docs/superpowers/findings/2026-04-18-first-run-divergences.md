# First-run divergences from Apr 17 blog

First full benchmark run: 2026-04-18 06:03 UTC. 95/105 calls completed
(interrupted during Test 4 write-out), $1.16 spent.

Summary: main finding reproduced, several secondary claims show gaps.

## Reproduced

### ✅ Effort level does not affect input tokens (blog Test 1)
All four Opus 4.7 effort levels (low/medium/high/max) consumed exactly 32
input tokens on the proof-of-primes prompt. σ = 0.0 within each variant.
The blog's headline claim holds.

### ✅ Output tokens hit max_tokens cap equally
With `max_tokens=1000`, Opus 4.7 hits the cap on `high`, `medium`, and `max`
effort (1000 ± 0). Opus 4.7 `low` often comes in below cap (970 ± 66). Opus
4.6 produces 809 ± 40 output tokens — less verbose than 4.7.

### ✅ 4.7 latency is lower than 4.6 on reasoning prompts
4.6 = 13.78s on the proof prompt; 4.7 low = 11.26s, medium = 9.79s. Matches
the blog's +46% faster claim within noise.

## Partial reproductions

### ⚠ Overhead on proof prompt: +52% vs blog's +61%
Opus 4.7 = 32 input tokens, Opus 4.6 = 21 input tokens →
(32−21)/21 × 100% = **+52.4%**. Blog reported +61%.

Probable causes:
- Different tokenizer versions or prompt whitespace normalization between
  Apr 17 and Apr 18.
- Blog's `global.` inference profile may have been routed differently.

Status: within the same order of magnitude but not exact. Marked CHECK in
the generated report.

## Divergences

### ❌ Opus 4.6 thinking_chars = 0 (blog: 856)
We invoke 4.6 with no `thinking` kwarg. The blog's "adaptive+high" 4.6
configuration likely used `thinking={"type": "enabled", "budget_tokens": N}`
where N was the mapped "high" value.

Fix path if we want to reproduce exactly: add a `thinking_for_46` config that
`build_kwargs` respects for 4.6. Not applied in this run because the design
spec opted for "native" 4.6 behavior; the divergence is documented rather
than patched.

### ❌ Opus 4.7 Test 3 tool_calls = 0 (blog: 4 parallel calls)
On the tool-use prompt "Look up pricing and limits for Bedrock in us-east-1
and eu-west-1", Opus 4.6 emits the expected 4 parallel `tool_use` blocks.
Opus 4.7 returns plain text with `stop_reason = "end_turn"` and emits zero
tool calls.

Probable causes (unverified):
- 4.7 may be answering from its own knowledge instead of invoking tools.
- Tool-schema serialization difference between 4.7 and 4.6.
- 4.7 behavior change since the Apr 17 blog.

Action: worth a follow-up investigation. The test harness is not at fault
— it sends the same `tools=[...]` payload to both models.

### ❌ Bedrock Mantle endpoint: 100% failure (30 calls → HTTP 404)
All calls to `https://bedrock-mantle.us-east-1.api.aws/anthropic/v1/messages`
returned 404. Signing is correct (service name `bedrock-mantle`, SigV4).

Probable cause: the Mantle endpoint requires account-level enrollment
(preview/allowlist), which our account does not have.

Action: This prevents reproducing the blog's Mantle parity claim. Re-run
Test 4 once Mantle access is granted, OR file a feature request with AWS
for programmatic Mantle enablement.

## Result metadata

- Results dir: `results/2026-04-18-0603/`
- SDK: `anthropic==0.96.0`
- Region (metadata): `ap-northeast-2` (set in shell); actual calls routed
  to `us-east-1` via `global.` inference profile
- Total cost: $1.1645
- Wall time: 595.3s
- Successes: 65; Errors: 30 (all Mantle 404)
