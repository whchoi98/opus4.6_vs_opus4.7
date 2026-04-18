"""TestCase dataclass — the pure data representation of a single benchmark case."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TestCase:
    name: str
    test_id: str
    backend: str
    model_id: str
    prompt: str
    prompt_label: str
    max_tokens: int = 1000
    effort: Optional[str] = None
    tools: Optional[list[dict]] = field(default=None)
    endpoint: Optional[str] = None
    auth_method: str = "iam_role"
