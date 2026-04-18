"""CLI entry point for the Opus 4.7 vs 4.6 benchmark."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

import anthropic
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

import config
from cases.base import TestCase
from clients.base import CallResult
from reporter import write_raw_json, write_aggregated_json, write_markdown_report
from runner.dispatch import collect_cases
from runner.execute import execute_case_with_retry, select_client
from runner.preflight import load_env, check_auth_env
from stats import aggregate_results


console = Console()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Opus 4.7 vs 4.6 Bedrock benchmark")
    p.add_argument("--test", default="all",
                   help="Comma-separated test ids: 1,2,3,4 or 'all'")
    p.add_argument("--runs", type=int, default=config.DEFAULT_RUNS,
                   help="Number of runs per case")
    p.add_argument("--backend", choices=["bedrock", "1p", "both"], default="bedrock",
                   help="Which backend to run (default: bedrock)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print plan and estimated cost, don't call the API")
    p.add_argument("--no-save-bodies", action="store_true",
                   help="Disable per-call body dumps (default: bodies are saved)")
    p.add_argument("--report-only", default=None,
                   help="Regenerate report.md from an existing results dir")
    return p.parse_args()


def resolve_tests(test_arg: str) -> list[str]:
    # Test 5 (prompt caching) is deferred — Bedrock does not surface cache token
    # fields via the anthropic SDK in our current setup (all runs observed
    # cache_creation_tokens=0, cache_read_tokens=0). Excluded from 'all' until
    # the Bedrock cache API shape is clarified. Runnable explicitly with
    # `--test 5` for investigation.
    if test_arg == "all":
        return ["1","2","3","4","6","7","8","9","10","11","12","13"]
    ids = [t.strip() for t in test_arg.split(",")]
    valid = ("1","2","3","4","5","6","7","8","9","10","11","12","13")
    for t in ids:
        if t not in valid:
            console.print(f"[red]Unknown test id: {t}. Valid: 1..13 or all[/red]")
            sys.exit(2)
    return ids


def resolve_backends(backend_arg: str, cases: list[TestCase]) -> set[str]:
    case_backends = {c.backend for c in cases}
    out: set[str] = set()
    if any(b.startswith("bedrock") for b in case_backends):
        out.add("bedrock")
    if "1p" in case_backends:
        out.add("1p")
    return out


def print_plan(cases: list[TestCase], runs: int) -> float:
    total_calls = len(cases) * runs
    est_cost = 0.0
    for c in cases:
        per_call = 0.025 if c.effort == "max" else 0.005
        est_cost += per_call * runs

    console.print(f"[cyan]Plan:[/cyan] {len(cases)} cases × {runs} runs = {total_calls} calls")
    console.print(f"[cyan]Estimated cost:[/cyan] ~${est_cost:.2f}")
    console.print(f"[cyan]Estimated wall time:[/cyan] ~{total_calls * 2 // 60 + 1}–{total_calls * 5 // 60 + 1} min")
    console.print()
    return est_cost


def ensure_results_dir() -> Path:
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d-%H%M")
    d = Path("results") / ts
    d.mkdir(parents=True, exist_ok=True)
    (d / "calls").mkdir(exist_ok=True)
    return d


def save_call_body(results_dir: Path, case: TestCase, run_index: int,
                   result: CallResult) -> None:
    path = results_dir / "calls" / f"{case.test_id}_{case.name}_run{run_index}.json"
    path.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False))


def run_smoke_tests() -> None:
    client = select_client("bedrock_runtime", "iam_role")
    console.print("[cyan]Smoke:[/cyan] calling Opus 4.6 via runtime with 'ping'…")
    r = client.invoke(
        model_id=config.MODELS_3P["opus-4.6"], prompt="ping",
        prompt_label="smoke", max_tokens=20,
        run_index=0, test_id="smoke",
    )
    console.print(f"[green]Smoke OK[/green] — {r.input_tokens}/{r.output_tokens} tokens, {r.latency_s:.2f}s")


def main() -> int:
    args = parse_args()
    load_env()

    if args.report_only:
        return regenerate_report(Path(args.report_only))

    test_ids = resolve_tests(args.test)
    all_cases = collect_cases(test_ids)

    if args.backend == "1p":
        console.print("[red]--backend 1p not supported yet (ANTHROPIC_API_KEY lacks credits)[/red]")
        return 2

    backends_needed = resolve_backends(args.backend, all_cases)
    ok, msg = check_auth_env(backends_needed)
    if not ok:
        console.print(f"[red]{msg}[/red]")
        return 2

    est_cost = print_plan(all_cases, args.runs)
    if args.dry_run:
        console.print("[yellow]Dry run — exiting without calling the API[/yellow]")
        return 0

    results_dir = ensure_results_dir()
    console.print(f"[cyan]Results dir:[/cyan] {results_dir}")

    run_smoke_tests()

    results: list[CallResult] = []
    start_ts = dt.datetime.utcnow().isoformat()
    t0 = time.perf_counter()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("Running benchmark…", total=len(all_cases) * args.runs)
            for case in all_cases:
                client = select_client(case.backend, case.auth_method)
                for i in range(args.runs):
                    r = execute_case_with_retry(client, case, run_index=i)
                    results.append(r)
                    if not args.no_save_bodies:
                        save_call_body(results_dir, case, i, r)
                    progress.update(task, advance=1)
                    time.sleep(config.INTER_CALL_DELAY_S)
                time.sleep(config.BACKEND_SWITCH_DELAY_S)
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted — saving partial results…[/yellow]")

    wall = time.perf_counter() - t0
    meta = {
        "start_ts": start_ts,
        "end_ts": dt.datetime.utcnow().isoformat(),
        "sdk_version": anthropic.__version__,
        "region": os.getenv("AWS_REGION", config.BEDROCK_REGION),
        "backends": sorted({r.backend for r in results}),
        "auth_methods": sorted({r.auth_method for r in results}),
        "total_calls": len(results),
        "total_cost_usd": sum(r.cost_usd for r in results),
        "wall_time_s": wall,
    }

    agg = aggregate_results(results)
    write_raw_json(results, meta, results_dir / "raw.json")
    write_aggregated_json(agg, results_dir / "aggregated.json")
    write_markdown_report(results, agg, meta, results_dir / "report.md")

    console.print(f"[green]Done.[/green] Wrote {results_dir}/report.md "
                  f"({len(results)} runs, ${meta['total_cost_usd']:.4f})")
    return 0


def regenerate_report(results_dir: Path) -> int:
    raw = json.loads((results_dir / "raw.json").read_text())
    results = [CallResult(**r) for r in raw["results"]]
    meta = raw["meta"]
    agg = aggregate_results(results)
    write_aggregated_json(agg, results_dir / "aggregated.json")
    write_markdown_report(results, agg, meta, results_dir / "report.md")
    console.print(f"[green]Report regenerated:[/green] {results_dir}/report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
