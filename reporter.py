"""JSON and Markdown report writers."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from clients.base import CallResult
from stats import CaseAggregate


def write_raw_json(results: list[CallResult], meta: dict[str, Any], path: Path) -> None:
    payload = {
        "meta": meta,
        "results": [asdict(r) for r in results],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def write_aggregated_json(agg: dict[tuple, CaseAggregate], path: Path) -> None:
    entries = [asdict(a) for a in agg.values()]
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False))


def write_markdown_report(
    results: list[CallResult],
    agg: dict[tuple, CaseAggregate],
    meta: dict[str, Any],
    path: Path,
) -> None:
    lines: list[str] = []
    lines.append("# Opus 4.7 vs 4.6 Benchmark Report")
    lines.append("")
    lines.append(f"- **Run at:** {meta.get('start_ts', 'unknown')}")
    lines.append(f"- **SDK version:** {meta.get('sdk_version', 'unknown')}")
    lines.append(f"- **Region:** {meta.get('region', 'unknown')}")
    lines.append(f"- **Backends:** {', '.join(meta.get('backends', []))}")
    lines.append(f"- **Total calls:** {meta.get('total_calls', 0)}")
    lines.append(f"- **Total cost:** ${meta.get('total_cost_usd', 0):.4f}")
    lines.append(f"- **Wall time:** {meta.get('wall_time_s', 0):.1f}s")
    lines.append("")

    for test_id, title in [
        ("test_1", "Test 1 — Effort level vs token consumption"),
        ("test_2", "Test 2 — Prompt length scaling"),
        ("test_3", "Test 3 — Parallel tool use"),
        ("test_4", "Test 4 — Mantle parity + auth-method comparison"),
    ]:
        lines.append(f"## {title}")
        lines.append("")
        rows = [a for a in agg.values() if a.test_id == test_id]
        if not rows:
            lines.append("_(no data)_")
            lines.append("")
            continue
        lines.append(
            "| Case | Model | Effort | Backend | Auth | Input (μ±σ) | Output (μ±σ) | "
            "Latency (μ±σ s) | Think chars | Tools | Cost (5 runs) |"
        )
        lines.append(
            "|---|---|---|---|---|---|---|---|---|---|---|"
        )
        for a in sorted(rows, key=lambda x: (x.backend, x.model_id, x.effort or "")):
            model_short = a.model_id.replace("global.anthropic.claude-", "")
            lines.append(
                f"| {a.prompt_label} | {model_short} | {a.effort or '—'} | "
                f"{a.backend} | {a.auth_method} | "
                f"{a.input_tokens_mean:.0f} ± {a.input_tokens_std:.1f} | "
                f"{a.output_tokens_mean:.0f} ± {a.output_tokens_std:.1f} | "
                f"{a.latency_mean:.2f} ± {a.latency_std:.2f} | "
                f"{a.thinking_chars_mean:.0f} | "
                f"{a.tool_calls_mean:.1f} | "
                f"${a.total_cost_usd:.4f} |"
            )
        lines.append("")

    lines.append("## Summary — key claim verification")
    lines.append("")
    lines.append(_render_blog_claims_section(agg))
    lines.append("")

    path.write_text("\n".join(lines))


def _render_blog_claims_section(agg: dict[tuple, CaseAggregate]) -> str:
    out_lines = [
        "| Claim | Expected | Measured | Status |",
        "|---|---|---|---|",
    ]

    t1_47 = [a for a in agg.values() if a.test_id == "test_1" and "opus-4-7" in a.model_id]
    if t1_47:
        inputs = {round(a.input_tokens_mean) for a in t1_47}
        status = "PASS" if len(inputs) == 1 else "FAIL"
        out_lines.append(
            f"| Effort does not affect input tokens | identical across variants | {sorted(inputs)} | {status} |"
        )

    t1_46 = [a for a in agg.values() if a.test_id == "test_1" and "opus-4-6" in a.model_id]
    if t1_47 and t1_46:
        avg_47 = sum(a.input_tokens_mean for a in t1_47) / len(t1_47)
        avg_46 = t1_46[0].input_tokens_mean
        if avg_46 > 0:
            overhead = (avg_47 - avg_46) / avg_46 * 100
            status = "PASS" if 55 <= overhead <= 70 else "CHECK"
            out_lines.append(
                f"| Proof prompt overhead (expected 55-70%) | 55-70% | +{overhead:.1f}% | {status} |"
            )

    return "\n".join(out_lines)
