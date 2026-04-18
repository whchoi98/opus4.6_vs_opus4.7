"""LLM-judge quality scorer for Bedrock benchmark responses.

Runs a selected prompt through both Opus 4.7 and Opus 4.6, then asks
Claude Sonnet 4.6 (cheaper judge model) to compare which response better
answers the prompt. Produces a judgement JSON and markdown summary.

Useful for detecting cases where token/latency gains came with quality
regressions — e.g. Test 3 where 4.7 answered without invoking tools.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import anthropic

import config
from clients.bedrock_runtime import BedrockRuntimeClient


JUDGE_MODEL = "global.anthropic.claude-sonnet-4-6-v1"


@dataclass(frozen=True)
class JudgementResult:
    prompt_label: str
    prompt: str
    response_47: str
    response_46: str
    verdict: str            # "4.7_better" | "4.6_better" | "tie"
    rationale: str
    judge_latency_s: float
    judge_cost_usd: float


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


def _parse_verdict(judge_text: str) -> tuple[str, str]:
    """Parse 'VERDICT: X\\nRATIONALE: Y' from judge output."""
    verdict = "tie"
    rationale = judge_text[:500]
    for line in judge_text.splitlines():
        if line.startswith("VERDICT:"):
            v = line.split(":", 1)[1].strip().lower()
            if "a" in v and "better" in v:
                verdict = "4.7_better"
            elif "b" in v and "better" in v:
                verdict = "4.6_better"
            elif "tie" in v:
                verdict = "tie"
        elif line.startswith("RATIONALE:"):
            rationale = line.split(":", 1)[1].strip()
    return verdict, rationale


def score_pairwise(
    prompt: str, prompt_label: str,
    client_47: BedrockRuntimeClient, client_46: BedrockRuntimeClient,
    judge: BedrockRuntimeClient, *, tools: Optional[list[dict]] = None,
    max_tokens: int = 400,
) -> JudgementResult:
    """Run the same prompt through 4.7 and 4.6, then ask the judge to compare."""
    # 4.7
    m47 = config.MODELS_3P["opus-4.7"]
    sdk_client = client_47._client
    resp_47 = sdk_client.messages.create(
        model=m47, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        **({"tools": tools} if tools else {}),
    )
    text_47 = _extract_text(resp_47.content)

    # 4.6
    m46 = config.MODELS_3P["opus-4.6"]
    sdk_client_46 = client_46._client
    resp_46 = sdk_client_46.messages.create(
        model=m46, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        **({"tools": tools} if tools else {}),
    )
    text_46 = _extract_text(resp_46.content)

    # Randomize A/B so we can check for position bias later if desired.
    # For now, A=4.7, B=4.6 (simple; document as a known limitation).
    judge_prompt = _JUDGE_PROMPT_TEMPLATE.format(
        prompt=prompt, response_a=text_47, response_b=text_46,
    )

    judge_sdk = judge._client
    t0 = time.perf_counter()
    j_resp = judge_sdk.messages.create(
        model=JUDGE_MODEL, max_tokens=500,
        system=_JUDGE_SYSTEM,
        messages=[{"role": "user", "content": judge_prompt}],
    )
    j_latency = time.perf_counter() - t0
    judge_text = _extract_text(j_resp.content)
    verdict, rationale = _parse_verdict(judge_text)

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
    lines.append("# Quality scorer report")
    lines.append("")
    lines.append(f"- **Run at:** {meta.get('start_ts', 'unknown')}")
    lines.append(f"- **Judge model:** {JUDGE_MODEL}")
    lines.append(f"- **Cases judged:** {len(results)}")
    total_cost = sum(r.judge_cost_usd for r in results)
    lines.append(f"- **Judge total cost:** ${total_cost:.4f}")
    lines.append("")
    lines.append("| # | Prompt label | Verdict | Rationale |")
    lines.append("|---|---|---|---|")
    for i, r in enumerate(results, 1):
        rat = r.rationale.replace("\n", " ").replace("|", "\\|")[:200]
        lines.append(f"| {i} | {r.prompt_label} | **{r.verdict}** | {rat} |")
    lines.append("")
    # Summary counts
    verdict_counts: dict[str, int] = {"4.7_better": 0, "4.6_better": 0, "tie": 0}
    for r in results:
        verdict_counts[r.verdict] = verdict_counts.get(r.verdict, 0) + 1
    lines.append("## Verdict summary")
    lines.append("")
    lines.append(f"- 4.7 better: {verdict_counts['4.7_better']}")
    lines.append(f"- 4.6 better: {verdict_counts['4.6_better']}")
    lines.append(f"- Tie: {verdict_counts['tie']}")

    out_path.write_text("\n".join(lines))
