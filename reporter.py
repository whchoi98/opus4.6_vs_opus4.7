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
