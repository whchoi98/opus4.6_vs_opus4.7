# scorers/

Response quality evaluation via LLM-as-judge.

## Purpose

Token/latency/cost metrics miss quality differences. The scorer runs the
same prompt through 4.7 and 4.6, then asks Claude Sonnet 4.6 (cheaper judge)
to compare responses pairwise.

## Rules

- **Judge model is Sonnet 4.6.** `global.anthropic.claude-sonnet-4-6`. Cheaper than Opus, adequate for pairwise.
- **A/B randomization is mandatory.** `score_pairwise` randomly places 4.7 in slot A or B per call. Fixed assignment produces biased results (position bias ~69% A preference observed).
- **Raw verdicts recorded.** `JudgementResult.raw_verdict` preserves the A/B answer; `position_of_47` preserves the randomization so downstream analysis can detect residual bias.

## Files

- `judge.py` — `JudgementResult` dataclass, `score_pairwise`, `write_scorer_report`.

## Known limitations

- **Position bias:** judge tends to prefer Position A even with randomization (~69% in our runs). Randomization averages this out over many runs.
- **Truncation artifact:** with `max_tokens=400`, verbose models (4.7) appear "incomplete" compared to terser models (4.6). This is a real signal about verbosity but not a pure quality metric.
- **Fixed sonnet judge:** results reflect Sonnet 4.6's preferences. A different judge may disagree.
- **Single-turn only:** no tool execution, no multi-turn. Good for prompt quality, not agent quality.

## CLI

`score.py` exposes three preset prompt labels: `tools`, `short`, `proof`. Extend `PROMPTS` dict in `score.py` to add more.
