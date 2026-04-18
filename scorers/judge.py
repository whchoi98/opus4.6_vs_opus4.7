"""LLM-judge quality scorer for Bedrock benchmark responses.

Runs a selected prompt through both Opus 4.7 and Opus 4.6, then asks
Claude Sonnet 4.6 (cheaper judge model) to compare which response better
answers the prompt. Produces a judgement JSON and markdown summary.

**Position bias mitigation:** A/B assignment is randomized per call so that
4.7 and 4.6 each appear as Response A roughly half the time. The randomized
position is recorded in `position_of_47` so downstream analysis can detect
any residual bias.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import config
from clients.bedrock_runtime import BedrockRuntimeClient


JUDGE_MODEL = "global.anthropic.claude-sonnet-4-6"


@dataclass(frozen=True)
class JudgementResult:
    prompt_label: str
    prompt: str
    response_47: str
    response_46: str
    verdict: str                  # "4.7_better" | "4.6_better" | "tie"
    rationale: str
    judge_latency_s: float
    judge_cost_usd: float
    position_of_47: str           # "A" or "B" — which slot 4.7 was placed in
    raw_verdict: str              # "A_better" | "B_better" | "tie" — before remap


_JUDGE_SYSTEM = """You are an expert evaluator comparing two AI model responses to the same user prompt. Your job is to decide which response better answers the user's question. You must be impartial, concise, and specific about the reasoning."""


_JUDGE_PROMPT_TEMPLATE = """A user asked the following question:

<prompt>
{prompt}
</prompt>

Response A:
<response_a>
{response_a}
</response_a>

Response B:
<response_b>
{response_b}
</response_b>

Which response better answers the user's question? Respond in this exact format:

VERDICT: <A_better | B_better | tie>
RATIONALE: <1-3 sentences explaining your reasoning. Be specific about what each response did well or poorly.>

Consider: correctness, completeness, specificity, appropriate use of tools or code examples when relevant, and whether the response actually addresses the user's question."""


def _extract_text(content_blocks: list) -> str:
    """Concatenate text from anthropic response content blocks."""
    parts = []
    for b in content_blocks:
        btype = getattr(b, "type", None)
        if btype == "text":
            parts.append(getattr(b, "text", ""))
        elif btype == "tool_use":
            name = getattr(b, "name", "?")
            inp = getattr(b, "input", {})
            parts.append(f"[tool_use: {name}({inp})]")
    return "\n".join(parts).strip()


def _parse_raw_verdict(judge_text: str) -> tuple[str, str]:
    """Parse 'VERDICT: X\\nRATIONALE: Y'. Returns (raw_verdict, rationale)
    where raw_verdict ∈ {A_better, B_better, tie}."""
    raw = "tie"
    rationale = judge_text[:500]
    for line in judge_text.splitlines():
        if line.startswith("VERDICT:"):
            v = line.split(":", 1)[1].strip().lower()
            if "a" in v and "better" in v:
                raw = "A_better"
            elif "b" in v and "better" in v:
                raw = "B_better"
            elif "tie" in v:
                raw = "tie"
        elif line.startswith("RATIONALE:"):
            rationale = line.split(":", 1)[1].strip()
    return raw, rationale


def _remap_verdict(raw: str, position_of_47: str) -> str:
    """Map the A/B verdict back to 4.7/4.6 based on which slot 4.7 occupied."""
    if raw == "tie":
        return "tie"
    a_was = "4.7_better" if position_of_47 == "A" else "4.6_better"
    b_was = "4.6_better" if position_of_47 == "A" else "4.7_better"
    return a_was if raw == "A_better" else b_was


# Kept for backward compat with existing unit tests (tests/test_scorer.py).
def _parse_verdict(judge_text: str) -> tuple[str, str]:
    """Legacy: assumes 4.7=A, 4.6=B. New code should use _parse_raw_verdict
    + _remap_verdict for position-randomized results."""
    raw, rationale = _parse_raw_verdict(judge_text)
    if raw == "A_better":
        return "4.7_better", rationale
    if raw == "B_better":
        return "4.6_better", rationale
    return "tie", rationale


def score_pairwise(
    prompt: str, prompt_label: str,
    client_47: BedrockRuntimeClient, client_46: BedrockRuntimeClient,
    judge: BedrockRuntimeClient, *, tools: Optional[list[dict]] = None,
    max_tokens: int = 400, rng: Optional[random.Random] = None,
) -> JudgementResult:
    """Run the prompt through 4.7 and 4.6, randomize A/B, ask the judge to compare."""
    rng = rng or random.Random()

    # Generate both responses first (models called unchanged)
    m47 = config.MODELS_3P["opus-4.7"]
    resp_47 = client_47._client.messages.create(
        model=m47, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        **({"tools": tools} if tools else {}),
    )
    text_47 = _extract_text(resp_47.content)

    m46 = config.MODELS_3P["opus-4.6"]
    resp_46 = client_46._client.messages.create(
        model=m46, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        **({"tools": tools} if tools else {}),
    )
    text_46 = _extract_text(resp_46.content)

    # Randomize which slot 4.7 goes into
    position_of_47 = "A" if rng.random() < 0.5 else "B"
    if position_of_47 == "A":
        response_a, response_b = text_47, text_46
    else:
        response_a, response_b = text_46, text_47

    judge_prompt = _JUDGE_PROMPT_TEMPLATE.format(
        prompt=prompt, response_a=response_a, response_b=response_b,
    )

    t0 = time.perf_counter()
    j_resp = judge._client.messages.create(
        model=JUDGE_MODEL, max_tokens=500,
        system=_JUDGE_SYSTEM,
        messages=[{"role": "user", "content": judge_prompt}],
    )
    j_latency = time.perf_counter() - t0
    judge_text = _extract_text(j_resp.content)
    raw_verdict, rationale = _parse_raw_verdict(judge_text)
    verdict = _remap_verdict(raw_verdict, position_of_47)

    # Sonnet 4.6 pricing: $3/MTok input, $15/MTok output
    j_cost = (
        j_resp.usage.input_tokens / 1_000_000 * 3.0
        + j_resp.usage.output_tokens / 1_000_000 * 15.0
    )

    return JudgementResult(
        prompt_label=prompt_label, prompt=prompt,
        response_47=text_47, response_46=text_46,
        verdict=verdict, rationale=rationale,
        judge_latency_s=j_latency, judge_cost_usd=j_cost,
        position_of_47=position_of_47, raw_verdict=raw_verdict,
    )


def write_scorer_report(
    results: list[JudgementResult], meta: dict, out_path: Path,
) -> None:
    """Write a markdown quality report alongside JSON."""
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps({
        "meta": meta,
        "results": [asdict(r) for r in results],
    }, indent=2, ensure_ascii=False))

    lines: list[str] = []
    lines.append("# Quality scorer report (position-randomized)")
    lines.append("")
    lines.append(f"- **Run at:** {meta.get('start_ts', 'unknown')}")
    lines.append(f"- **Judge model:** {JUDGE_MODEL}")
    lines.append(f"- **Cases judged:** {len(results)}")
    total_cost = sum(r.judge_cost_usd for r in results)
    lines.append(f"- **Judge total cost:** ${total_cost:.4f}")
    lines.append("")
    lines.append("| # | Prompt | 4.7 slot | Raw (A/B) | Final verdict | Rationale |")
    lines.append("|---|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        rat = r.rationale.replace("\n", " ").replace("|", "\\|")[:160]
        lines.append(
            f"| {i} | {r.prompt_label} | {r.position_of_47} | {r.raw_verdict} | "
            f"**{r.verdict}** | {rat} |"
        )
    lines.append("")

    # Verdict summary
    verdict_counts: dict[str, int] = {"4.7_better": 0, "4.6_better": 0, "tie": 0}
    for r in results:
        verdict_counts[r.verdict] = verdict_counts.get(r.verdict, 0) + 1
    lines.append("## Verdict summary (model-labelled)")
    lines.append("")
    lines.append(f"- 4.7 better: {verdict_counts['4.7_better']}")
    lines.append(f"- 4.6 better: {verdict_counts['4.6_better']}")
    lines.append(f"- Tie: {verdict_counts['tie']}")
    lines.append("")

    # Position-bias diagnostic
    a_wins = sum(1 for r in results if r.raw_verdict == "A_better")
    b_wins = sum(1 for r in results if r.raw_verdict == "B_better")
    ties = sum(1 for r in results if r.raw_verdict == "tie")
    lines.append("## Position-bias diagnostic (raw A/B)")
    lines.append("")
    lines.append(f"- Position A won: {a_wins}")
    lines.append(f"- Position B won: {b_wins}")
    lines.append(f"- Tie: {ties}")
    lines.append("")
    if a_wins + b_wins > 0:
        a_rate = a_wins / (a_wins + b_wins) * 100
        lines.append(
            f"_Raw A-win rate: {a_rate:.0f}%. Unbiased judge expects ~50%. "
            f"Large deviations (<35% or >65%) suggest position bias._"
        )

    out_path.write_text("\n".join(lines))
