"""CLI for running the quality scorer on specific prompts.

Usage:
    python score.py --prompt-label tools --runs 3
    python score.py --prompt-label proof --runs 5
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from rich.console import Console

import config
from clients.bedrock_runtime import BedrockRuntimeClient
from runner.preflight import load_env, check_auth_env
from scorers.judge import score_pairwise, write_scorer_report
from cases.prompts import TOOL_USE_PROMPT, TOOLS_SCHEMA, PROOF_PROMPT, SHORT_PROMPT


console = Console()


PROMPTS = {
    "proof": (PROOF_PROMPT, None),
    "short": (SHORT_PROMPT, None),
    "tools": (TOOL_USE_PROMPT, TOOLS_SCHEMA),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Quality scorer for Bedrock benchmark")
    p.add_argument("--prompt-label", choices=list(PROMPTS.keys()),
                   default="tools", help="Which prompt to judge")
    p.add_argument("--runs", type=int, default=3,
                   help="Number of judgement rounds per prompt")
    p.add_argument("--output", default=None,
                   help="Output dir (default: results/scorer-YYYY-MM-DD-HHMM/)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    ok, msg = check_auth_env(backends={"bedrock"})
    if not ok:
        console.print(f"[red]{msg}[/red]")
        return 2

    if args.output:
        out_dir = Path(args.output)
    else:
        ts = dt.datetime.utcnow().strftime("%Y-%m-%d-%H%M")
        out_dir = Path("results") / f"scorer-{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    client_47 = BedrockRuntimeClient(auth_method="iam_role")
    client_46 = client_47  # same SDK instance, different model at call time
    judge = client_47

    prompt, tools = PROMPTS[args.prompt_label]

    results = []
    for i in range(args.runs):
        console.print(f"[cyan]Run {i+1}/{args.runs}[/cyan] judging {args.prompt_label}...")
        r = score_pairwise(
            prompt=prompt, prompt_label=args.prompt_label,
            client_47=client_47, client_46=client_46, judge=judge,
            tools=tools, max_tokens=400,
        )
        console.print(f"  verdict={r.verdict}  judge_cost=${r.judge_cost_usd:.4f}")
        results.append(r)

    meta = {
        "start_ts": dt.datetime.utcnow().isoformat(),
        "prompt_label": args.prompt_label,
        "runs": args.runs,
    }
    out_md = out_dir / "scorer-report.md"
    write_scorer_report(results, meta, out_md)
    console.print(f"[green]Done[/green] — wrote {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
