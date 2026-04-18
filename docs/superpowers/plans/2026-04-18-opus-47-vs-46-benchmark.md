# Opus 4.7 vs 4.6 Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python benchmark harness that reproduces the Apr 17 blog's Opus 4.7 vs 4.6 comparison tests on AWS Bedrock (3P), with 5-run averaging, runtime vs Mantle comparison, and IAM vs Bedrock-API-key auth comparison. Produces JSON + Markdown reports.

**Architecture:** CLI runner (`run.py`) dispatches to case modules (`cases/*.py`) that return `TestCase` lists. Each case is executed N times via one of three client wrappers (`clients/bedrock_runtime.py`, `clients/bedrock_mantle.py`, `clients/anthropic_1p.py`), each returning a unified `CallResult`. Results aggregated via `stats.py` and written by `reporter.py`.

**Tech Stack:** Python 3.11+, `anthropic` SDK (0.96+), `boto3` / `botocore` (SigV4 for Mantle), `requests`, `rich` (progress), `python-dotenv`, `pytest` for unit tests.

**Reference spec:** `docs/superpowers/specs/2026-04-18-opus-47-vs-46-benchmark-design.md`

---

## Task 1: Project scaffold

**Files:**
- Create: `/home/ec2-user/my-project/Opus4.6vsOpus4.7/requirements.txt`
- Create: `/home/ec2-user/my-project/Opus4.6vsOpus4.7/.gitignore`
- Create: `/home/ec2-user/my-project/Opus4.6vsOpus4.7/.env.local.example`
- Create: `/home/ec2-user/my-project/Opus4.6vsOpus4.7/pyproject.toml`

- [ ] **Step 1: Create `requirements.txt`**

```
anthropic>=0.96.0
boto3>=1.34.0
botocore>=1.34.0
requests>=2.31.0
rich>=13.7.0
python-dotenv>=1.0.0
pytest>=7.4.0
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
.env.local
.env
results/
.pytest_cache/
*.egg-info/
.venv/
venv/
```

- [ ] **Step 3: Create `.env.local.example`**

```
# Copy this file to .env.local and fill in your values. Never commit .env.local.

# Required for 3P Bedrock tests (one of the two):
AWS_BEARER_TOKEN_BEDROCK=

# Or, leave AWS_BEARER_TOKEN_BEDROCK empty and use IAM credentials:
# AWS_PROFILE=
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=

AWS_REGION=us-east-1

# Optional, only required if --backend 1p is used:
ANTHROPIC_API_KEY=
```

- [ ] **Step 4: Create `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"

[tool.pytest.ini_options.env]
ANTHROPIC_API_KEY = "dummy-for-unit-tests"
AWS_REGION = "us-east-1"
```

- [ ] **Step 5: Initialize git and install dependencies**

```bash
cd /home/ec2-user/my-project/Opus4.6vsOpus4.7
git init
git add .gitignore requirements.txt .env.local.example pyproject.toml
pip install --user -r requirements.txt
```

- [ ] **Step 6: Verify install**

```bash
python3 -c "import anthropic, boto3, botocore, requests, rich, dotenv, pytest; print('all imports OK')"
```

Expected: `all imports OK`

- [ ] **Step 7: Commit**

```bash
git commit -m "chore: project scaffold with requirements and gitignore"
```

---

## Task 2: Config module

**Files:**
- Create: `/home/ec2-user/my-project/Opus4.6vsOpus4.7/config.py`
- Test: `/home/ec2-user/my-project/Opus4.6vsOpus4.7/tests/__init__.py`
- Test: `/home/ec2-user/my-project/Opus4.6vsOpus4.7/tests/test_config.py`

- [ ] **Step 1: Create empty `tests/__init__.py`**

```bash
mkdir -p tests
touch tests/__init__.py
```

- [ ] **Step 2: Write failing test `tests/test_config.py`**

```python
import config


def test_models_3p_has_both_models():
    assert config.MODELS_3P["opus-4.7"] == "global.anthropic.claude-opus-4-7"
    assert config.MODELS_3P["opus-4.6"] == "global.anthropic.claude-opus-4-6-v1"


def test_models_1p_has_both_models():
    assert config.MODELS_1P["opus-4.7"] == "claude-opus-4-7"
    assert config.MODELS_1P["opus-4.6"] == "claude-opus-4-6"


def test_pricing_matches_apr16_blog():
    for model in ("opus-4.7", "opus-4.6"):
        assert config.PRICING[model]["input"] == 5.00
        assert config.PRICING[model]["output"] == 25.00


def test_mantle_url_has_region():
    assert config.MANTLE_URL == "https://bedrock-mantle.us-east-1.api.aws/anthropic/v1/messages"


def test_defaults():
    assert config.DEFAULT_RUNS == 5
    assert config.BEDROCK_REGION == "us-east-1"
    assert config.INTER_CALL_DELAY_S == 0.2
    assert config.RETRY_MAX_ATTEMPTS == 3
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/ec2-user/my-project/Opus4.6vsOpus4.7 && pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: Create `config.py`**

```python
"""Central configuration — model IDs, endpoints, pricing, run parameters."""

MODELS_1P = {
    "opus-4.7": "claude-opus-4-7",
    "opus-4.6": "claude-opus-4-6",
}

MODELS_3P = {
    "opus-4.7": "global.anthropic.claude-opus-4-7",
    "opus-4.6": "global.anthropic.claude-opus-4-6-v1",
}

PRICING = {
    "opus-4.7": {"input": 5.00, "output": 25.00},
    "opus-4.6": {"input": 5.00, "output": 25.00},
}

BEDROCK_REGION = "us-east-1"
MANTLE_URL = "https://bedrock-mantle.us-east-1.api.aws/anthropic/v1/messages"

DEFAULT_RUNS = 5
DEFAULT_MAX_TOKENS = 1000
INTER_CALL_DELAY_S = 0.2
BACKEND_SWITCH_DELAY_S = 0.5
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_S = 2.0


def model_key_from_id(model_id: str) -> str:
    """Map a backend model ID to our 'opus-4.7' / 'opus-4.6' key for pricing."""
    if "opus-4-7" in model_id:
        return "opus-4.7"
    if "opus-4-6" in model_id:
        return "opus-4.6"
    raise ValueError(f"Unknown model id: {model_id}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add config.py tests/__init__.py tests/test_config.py
git commit -m "feat(config): add central config with model ids, pricing, defaults"
```

---

## Task 3: CallResult dataclass + cost calculator

**Files:**
- Create: `clients/__init__.py`
- Create: `clients/base.py`
- Create: `tests/test_clients_base.py`

- [ ] **Step 1: Create empty `clients/__init__.py`**

```bash
mkdir -p clients
touch clients/__init__.py
```

- [ ] **Step 2: Write failing test `tests/test_clients_base.py`**

```python
from clients.base import CallResult, compute_cost_usd, parse_bedrock_response


def test_callresult_is_frozen():
    r = CallResult(
        input_tokens=10, output_tokens=20, latency_s=1.5,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=None, prompt_label="short",
        stop_reason="end_turn", cost_usd=0.0005,
        run_index=0, test_id="test_1",
    )
    try:
        r.input_tokens = 99
        assert False, "should be frozen"
    except Exception:
        pass


def test_compute_cost_opus_47():
    cost = compute_cost_usd("global.anthropic.claude-opus-4-7", input_tokens=1000, output_tokens=500)
    assert abs(cost - (1000 / 1_000_000 * 5.0 + 500 / 1_000_000 * 25.0)) < 1e-9


def test_compute_cost_opus_46():
    cost = compute_cost_usd("global.anthropic.claude-opus-4-6-v1", input_tokens=2000, output_tokens=0)
    assert abs(cost - (2000 / 1_000_000 * 5.0)) < 1e-9


def test_parse_bedrock_response_basic():
    resp = {
        "usage": {"input_tokens": 37, "output_tokens": 926},
        "content": [{"type": "text", "text": "hello"}],
        "stop_reason": "end_turn",
    }
    result = parse_bedrock_response(
        resp, latency_s=8.24, backend="bedrock_runtime",
        auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort="low", prompt_label="proof", run_index=0, test_id="test_1",
    )
    assert result.input_tokens == 37
    assert result.output_tokens == 926
    assert result.thinking_chars == 0
    assert result.tool_calls_count == 0


def test_parse_bedrock_response_with_thinking():
    resp = {
        "usage": {"input_tokens": 23, "output_tokens": 958},
        "content": [
            {"type": "thinking", "thinking": "x" * 856},
            {"type": "text", "text": "hello"},
        ],
        "stop_reason": "end_turn",
    }
    r = parse_bedrock_response(
        resp, latency_s=15.1, backend="bedrock_runtime",
        auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-6-v1",
        effort=None, prompt_label="proof", run_index=0, test_id="test_1",
    )
    assert r.thinking_chars == 856


def test_parse_bedrock_response_counts_tool_uses():
    resp = {
        "usage": {"input_tokens": 888, "output_tokens": 270},
        "content": [
            {"type": "tool_use", "id": "a", "name": "x", "input": {}},
            {"type": "tool_use", "id": "b", "name": "y", "input": {}},
            {"type": "tool_use", "id": "c", "name": "z", "input": {}},
            {"type": "tool_use", "id": "d", "name": "w", "input": {}},
        ],
        "stop_reason": "tool_use",
    }
    r = parse_bedrock_response(
        resp, latency_s=2.13, backend="bedrock_runtime",
        auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=None, prompt_label="tools", run_index=0, test_id="test_3",
    )
    assert r.tool_calls_count == 4
    assert r.stop_reason == "tool_use"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_clients_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clients.base'`

- [ ] **Step 4: Create `clients/base.py`**

```python
"""Shared types and helpers for client wrappers."""
from dataclasses import dataclass
from typing import Any, Optional

import config


@dataclass(frozen=True)
class CallResult:
    # Measurements
    input_tokens: int
    output_tokens: int
    latency_s: float
    thinking_chars: int
    tool_calls_count: int

    # Context for grouping
    backend: str
    auth_method: str
    model_id: str
    effort: Optional[str]
    prompt_label: str

    # Debugging / auditing
    stop_reason: str
    cost_usd: float
    run_index: int
    test_id: str
    error: Optional[str] = None


def compute_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost for one call using PRICING from config."""
    key = config.model_key_from_id(model_id)
    p = config.PRICING[key]
    return input_tokens / 1_000_000 * p["input"] + output_tokens / 1_000_000 * p["output"]


def parse_bedrock_response(
    resp: dict,
    *,
    latency_s: float,
    backend: str,
    auth_method: str,
    model_id: str,
    effort: Optional[str],
    prompt_label: str,
    run_index: int,
    test_id: str,
) -> CallResult:
    """Parse a Bedrock (or 1P — same shape) response JSON into a CallResult."""
    usage = resp.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    thinking_chars = 0
    tool_calls_count = 0
    for block in resp.get("content", []):
        btype = block.get("type")
        if btype == "thinking":
            thinking_chars += len(block.get("thinking", ""))
        elif btype == "tool_use":
            tool_calls_count += 1

    return CallResult(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_s=latency_s,
        thinking_chars=thinking_chars,
        tool_calls_count=tool_calls_count,
        backend=backend,
        auth_method=auth_method,
        model_id=model_id,
        effort=effort,
        prompt_label=prompt_label,
        stop_reason=resp.get("stop_reason", "unknown"),
        cost_usd=compute_cost_usd(model_id, input_tokens, output_tokens),
        run_index=run_index,
        test_id=test_id,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_clients_base.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add clients/__init__.py clients/base.py tests/test_clients_base.py
git commit -m "feat(clients): add CallResult dataclass, cost calculator, response parser"
```

---

## Task 4: Stats aggregation module

**Files:**
- Create: `stats.py`
- Test: `tests/test_stats.py`

- [ ] **Step 1: Write failing test `tests/test_stats.py`**

```python
from clients.base import CallResult
from stats import aggregate_results, CaseAggregate


def _make_result(run_index, input_tokens=37, output_tokens=100, latency=1.0, error=None):
    return CallResult(
        input_tokens=input_tokens, output_tokens=output_tokens,
        latency_s=latency, thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort="low", prompt_label="proof",
        stop_reason="end_turn", cost_usd=0.001,
        run_index=run_index, test_id="test_1", error=error,
    )


def test_aggregate_single_case_5_runs():
    results = [_make_result(i, latency=i + 1.0) for i in range(5)]
    agg = aggregate_results(results)
    assert len(agg) == 1
    key = ("test_1", "bedrock_runtime", "iam_role", "global.anthropic.claude-opus-4-7", "low", "proof")
    ca: CaseAggregate = agg[key]
    assert ca.n_runs == 5
    assert ca.n_success == 5
    assert ca.input_tokens_mean == 37.0
    assert ca.input_tokens_std == 0.0
    assert abs(ca.latency_mean - 3.0) < 1e-9
    assert ca.latency_std > 0


def test_aggregate_excludes_errors_from_stats():
    results = [_make_result(0, latency=1.0), _make_result(1, latency=2.0),
               _make_result(2, latency=999.0, error="ratelimit")]
    agg = aggregate_results(results)
    key = next(iter(agg))
    ca = agg[key]
    assert ca.n_runs == 3
    assert ca.n_success == 2
    assert abs(ca.latency_mean - 1.5) < 1e-9


def test_aggregate_groups_by_effort_and_prompt():
    # Two effort levels, same prompt → two separate groups
    r1 = _make_result(0)
    r2 = CallResult(
        input_tokens=37, output_tokens=100, latency_s=1.0,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort="max", prompt_label="proof",
        stop_reason="end_turn", cost_usd=0.01,
        run_index=0, test_id="test_1",
    )
    agg = aggregate_results([r1, r2])
    assert len(agg) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stats.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats'`

- [ ] **Step 3: Create `stats.py`**

```python
"""Aggregation of CallResult lists into per-case statistics."""
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from clients.base import CallResult


@dataclass(frozen=True)
class CaseAggregate:
    test_id: str
    backend: str
    auth_method: str
    model_id: str
    effort: str | None
    prompt_label: str
    n_runs: int
    n_success: int
    input_tokens_mean: float
    input_tokens_std: float
    output_tokens_mean: float
    output_tokens_std: float
    latency_mean: float
    latency_std: float
    thinking_chars_mean: float
    tool_calls_mean: float
    total_cost_usd: float


def _key(r: CallResult) -> tuple:
    return (r.test_id, r.backend, r.auth_method, r.model_id, r.effort, r.prompt_label)


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = statistics.fmean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return m, s


def aggregate_results(results: Iterable[CallResult]) -> dict[tuple, CaseAggregate]:
    groups: dict[tuple, list[CallResult]] = defaultdict(list)
    for r in results:
        groups[_key(r)].append(r)

    out: dict[tuple, CaseAggregate] = {}
    for key, runs in groups.items():
        successes = [r for r in runs if r.error is None]
        in_tok_m, in_tok_s = _mean_std([r.input_tokens for r in successes])
        out_tok_m, out_tok_s = _mean_std([r.output_tokens for r in successes])
        lat_m, lat_s = _mean_std([r.latency_s for r in successes])
        think_m, _ = _mean_std([r.thinking_chars for r in successes])
        tools_m, _ = _mean_std([r.tool_calls_count for r in successes])
        total_cost = sum(r.cost_usd for r in successes)
        test_id, backend, auth, model, effort, prompt = key
        out[key] = CaseAggregate(
            test_id=test_id, backend=backend, auth_method=auth,
            model_id=model, effort=effort, prompt_label=prompt,
            n_runs=len(runs), n_success=len(successes),
            input_tokens_mean=in_tok_m, input_tokens_std=in_tok_s,
            output_tokens_mean=out_tok_m, output_tokens_std=out_tok_s,
            latency_mean=lat_m, latency_std=lat_s,
            thinking_chars_mean=think_m, tool_calls_mean=tools_m,
            total_cost_usd=total_cost,
        )
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_stats.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add stats.py tests/test_stats.py
git commit -m "feat(stats): aggregate CallResults by (test, backend, auth, model, effort, prompt)"
```

---

## Task 5: TestCase dataclass + prompts module

**Files:**
- Create: `cases/__init__.py`
- Create: `cases/base.py`
- Create: `cases/prompts.py`

- [ ] **Step 1: Create `cases/__init__.py` and `cases/base.py`**

```bash
mkdir -p cases
touch cases/__init__.py
```

`cases/base.py`:

```python
"""TestCase dataclass — the pure data representation of a single benchmark case."""
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
```

- [ ] **Step 2: Create `cases/prompts.py` with Test 1, 2, 3 prompts and tool schemas**

```python
"""All prompts and tool schemas — single source of truth."""

# Test 1: effort-level benchmark prompt (exact, from Apr 17 blog)
PROOF_PROMPT = "Proof that there are infinitely many primes. Full reasoning."

# Test 2: prompt-length scaling
SHORT_PROMPT = "How do I center a div vertically and horizontally in CSS?"

LONG_PROMPT = """다음 Python 함수를 리뷰하고 개선 방안을 제시해 주세요. SQS 큐에서 메시지를 가져와 처리하고 실패를 다루는 백그라운드 작업 처리기를 만들고 있습니다. 테스트 환경에서는 동작하지만 프로덕션 엣지 케이스가 걱정됩니다.

```python
import boto3, json, time, logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
sqs = boto3.client("sqs")

def process_queue(queue_url, handler, max_messages=10, wait_time=20):
    while True:
        try:
            resp = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time,
                MessageAttributeNames=["All"],
            )
            messages = resp.get("Messages", [])
            if not messages:
                continue
            for msg in messages:
                try:
                    body = json.loads(msg["Body"])
                    handler(body)
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=msg["ReceiptHandle"],
                    )
                except Exception as e:
                    logger.error(f"failed: {e}")
        except ClientError as e:
            logger.error(f"sqs error: {e}")
            time.sleep(5)
```

특히 다음을 중점적으로 짚어 주세요: (1) handler()가 일시적 오류를 던질 때와 영구적 오류를 던질 때 — 둘을 다르게 취급해야 할까요? (2) 내부 try/except가 Exception을 광범위하게 잡는데 — 이게 워커를 중단시켜야 할 버그를 감추고 있지는 않을까요? (3) 백프레셔 처리가 없습니다; 하류 처리가 느려지면 메시지가 계속 당겨지고 visibility timeout이 처리 중간에 만료될 수 있습니다. 어떻게 고치시겠나요? (4) Graceful shutdown: SIGTERM을 받으면 (예: ECS가 컨테이너를 중지할 때) 루프가 계속 돌면서 메시지를 반쯤 처리한 상태로 남길 수 있습니다. (5) ClientError에 대한 `time.sleep(5)`는 무딘 도구입니다 — 더 견고한 재시도 전략은 무엇인가요? (6) 프로덕션에서 실제로 디버깅하려면 logging 외에 어떤 관측성을 추가해야 할까요? 구체적으로 설명하고, 상위 세 가지 권장사항에 대해 코드를 보여주세요. 전체 재작성보다 점진적 변경을 선호합니다."""

# Test 3: parallel tool-use prompt (exact wording from Apr 16 blog)
TOOL_USE_PROMPT = "Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."

# Tool schemas for Test 3
TOOLS_SCHEMA = [
    {
        "name": "get_bedrock_pricing",
        "description": "Get on-demand pricing for a Bedrock model in a specific AWS region.",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "The Bedrock model identifier, e.g. 'anthropic.claude-opus-4-7'.",
                },
                "region": {
                    "type": "string",
                    "description": "AWS region code, e.g. 'us-east-1'.",
                },
            },
            "required": ["model_id", "region"],
        },
    },
    {
        "name": "get_service_quota",
        "description": "Get the current service quota value for AWS Bedrock in a specific region.",
        "input_schema": {
            "type": "object",
            "properties": {
                "quota_name": {
                    "type": "string",
                    "description": "The name of the service quota, e.g. 'InvokeModel throughput'.",
                },
                "region": {
                    "type": "string",
                    "description": "AWS region code.",
                },
            },
            "required": ["quota_name", "region"],
        },
    },
]
```

- [ ] **Step 3: Verify imports work**

```bash
python3 -c "from cases.base import TestCase; from cases import prompts; print(len(prompts.LONG_PROMPT), 'chars'); print(len(prompts.TOOLS_SCHEMA), 'tools')"
```

Expected: prints character count (will be a few thousand) and "2 tools".

- [ ] **Step 4: Commit**

```bash
git add cases/__init__.py cases/base.py cases/prompts.py
git commit -m "feat(cases): add TestCase dataclass and all benchmark prompts + tool schemas"
```

---

## Task 6: Bedrock Runtime client wrapper

**Files:**
- Create: `clients/bedrock_runtime.py`
- Test: `tests/test_bedrock_runtime.py`

Note: we unit-test the kwargs-builder only (no real API). The actual API call is exercised in the smoke test (Task 12).

- [ ] **Step 1: Write failing test `tests/test_bedrock_runtime.py`**

```python
from clients.bedrock_runtime import build_kwargs


def test_build_kwargs_opus_47_with_effort():
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hello", max_tokens=100, effort="low", tools=None,
    )
    assert k["model"] == "global.anthropic.claude-opus-4-7"
    assert k["max_tokens"] == 100
    assert k["messages"] == [{"role": "user", "content": "hello"}]
    assert k["thinking"] == {"type": "adaptive"}
    assert k["extra_body"] == {"output_config": {"effort": "low"}}
    assert "tools" not in k


def test_build_kwargs_opus_47_no_effort():
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hello", max_tokens=100, effort=None, tools=None,
    )
    assert "thinking" not in k
    assert "extra_body" not in k


def test_build_kwargs_opus_46_no_thinking():
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-6-v1",
        prompt="hello", max_tokens=100, effort=None, tools=None,
    )
    assert "thinking" not in k


def test_build_kwargs_with_tools():
    tools = [{"name": "x", "description": "d", "input_schema": {"type": "object", "properties": {}}}]
    k = build_kwargs(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hello", max_tokens=100, effort=None, tools=tools,
    )
    assert k["tools"] == tools
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bedrock_runtime.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clients.bedrock_runtime'`

- [ ] **Step 3: Create `clients/bedrock_runtime.py`**

```python
"""Wrapper around anthropic.AnthropicBedrock for the bedrock-runtime endpoint."""
import time
from typing import Optional

import anthropic

import config
from clients.base import CallResult, parse_bedrock_response


def build_kwargs(
    *,
    model_id: str,
    prompt: str,
    max_tokens: int,
    effort: Optional[str],
    tools: Optional[list[dict]],
) -> dict:
    """Build the kwargs dict for anthropic.AnthropicBedrock.messages.create.

    Handles the API shape divergence between Opus 4.7 (thinking.adaptive +
    output_config.effort) and Opus 4.6 (no thinking kwarg by default).
    """
    kwargs: dict = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if tools:
        kwargs["tools"] = tools
    if "opus-4-7" in model_id and effort:
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["extra_body"] = {"output_config": {"effort": effort}}
    return kwargs


class BedrockRuntimeClient:
    def __init__(self, region: str = config.BEDROCK_REGION, auth_method: str = "iam_role"):
        self._client = anthropic.AnthropicBedrock(aws_region=region)
        self._region = region
        self._auth_method = auth_method

    def invoke(
        self,
        *,
        model_id: str,
        prompt: str,
        prompt_label: str,
        max_tokens: int,
        effort: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        run_index: int = 0,
        test_id: str = "",
    ) -> CallResult:
        kwargs = build_kwargs(
            model_id=model_id, prompt=prompt, max_tokens=max_tokens,
            effort=effort, tools=tools,
        )
        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        latency = time.perf_counter() - t0
        # Convert anthropic response object to dict shape matching parse_bedrock_response
        resp_dict = {
            "usage": {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
            "content": [_block_to_dict(b) for b in resp.content],
            "stop_reason": resp.stop_reason,
        }
        return parse_bedrock_response(
            resp_dict, latency_s=latency, backend="bedrock_runtime",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
            prompt_label=prompt_label, run_index=run_index, test_id=test_id,
        )


def _block_to_dict(block) -> dict:
    """Convert an anthropic content block to the dict shape parse_bedrock_response expects."""
    btype = getattr(block, "type", None)
    if btype == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if btype == "thinking":
        return {"type": "thinking", "thinking": getattr(block, "thinking", "")}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", ""),
            "name": getattr(block, "name", ""),
            "input": getattr(block, "input", {}),
        }
    return {"type": btype or "unknown"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bedrock_runtime.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add clients/bedrock_runtime.py tests/test_bedrock_runtime.py
git commit -m "feat(clients): bedrock runtime wrapper with 4.7/4.6 api shape handling"
```

---

## Task 7: Bedrock Mantle client (raw SigV4)

**Files:**
- Create: `clients/bedrock_mantle.py`
- Test: `tests/test_bedrock_mantle.py`

The Anthropic SDK signs with service name `bedrock`; Mantle requires service name `bedrock-mantle`. We hand-roll the HTTP call using `botocore.auth.SigV4Auth`.

- [ ] **Step 1: Write failing test `tests/test_bedrock_mantle.py`**

```python
from clients.bedrock_mantle import build_body


def test_build_body_basic():
    b = build_body(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hi", max_tokens=100, effort=None, tools=None,
    )
    assert b["anthropic_version"] == "bedrock-2023-05-31"
    assert b["model"] == "global.anthropic.claude-opus-4-7"
    assert b["max_tokens"] == 100
    assert b["messages"] == [{"role": "user", "content": "hi"}]
    assert "thinking" not in b


def test_build_body_opus47_with_effort():
    b = build_body(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hi", max_tokens=100, effort="max", tools=None,
    )
    assert b["thinking"] == {"type": "adaptive"}
    assert b["output_config"] == {"effort": "max"}


def test_build_body_with_tools():
    tools = [{"name": "x", "description": "d",
              "input_schema": {"type": "object", "properties": {}}}]
    b = build_body(
        model_id="global.anthropic.claude-opus-4-7",
        prompt="hi", max_tokens=100, effort=None, tools=tools,
    )
    assert b["tools"] == tools
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bedrock_mantle.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `clients/bedrock_mantle.py`**

```python
"""Raw HTTP client for the bedrock-mantle endpoint using manual SigV4.

The Anthropic SDK signs with service name 'bedrock' — Mantle rejects that.
We sign with service name 'bedrock-mantle' using botocore.auth.SigV4Auth.
"""
import json
import time
from typing import Optional

import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session

import config
from clients.base import CallResult, parse_bedrock_response


def build_body(
    *,
    model_id: str,
    prompt: str,
    max_tokens: int,
    effort: Optional[str],
    tools: Optional[list[dict]],
) -> dict:
    body: dict = {
        "anthropic_version": "bedrock-2023-05-31",
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if tools:
        body["tools"] = tools
    if "opus-4-7" in model_id and effort:
        body["thinking"] = {"type": "adaptive"}
        body["output_config"] = {"effort": effort}
    return body


class BedrockMantleClient:
    def __init__(self, region: str = config.BEDROCK_REGION, auth_method: str = "iam_role"):
        self._region = region
        self._auth_method = auth_method
        self._url = config.MANTLE_URL
        self._credentials = Session().get_credentials()
        if self._credentials is None:
            raise RuntimeError(
                "No AWS credentials found for Mantle client. "
                "Set AWS_PROFILE / AWS_ACCESS_KEY_ID / AWS_BEARER_TOKEN_BEDROCK."
            )

    def invoke(
        self,
        *,
        model_id: str,
        prompt: str,
        prompt_label: str,
        max_tokens: int,
        effort: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        run_index: int = 0,
        test_id: str = "",
    ) -> CallResult:
        body = build_body(
            model_id=model_id, prompt=prompt, max_tokens=max_tokens,
            effort=effort, tools=tools,
        )
        data = json.dumps(body)

        aws_req = AWSRequest(
            method="POST", url=self._url, data=data,
            headers={"Content-Type": "application/json"},
        )
        SigV4Auth(self._credentials, "bedrock-mantle", self._region).add_auth(aws_req)

        t0 = time.perf_counter()
        resp = requests.post(self._url, data=data, headers=dict(aws_req.headers), timeout=60)
        latency = time.perf_counter() - t0
        resp.raise_for_status()

        return parse_bedrock_response(
            resp.json(), latency_s=latency, backend="bedrock_mantle",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
            prompt_label=prompt_label, run_index=run_index, test_id=test_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bedrock_mantle.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add clients/bedrock_mantle.py tests/test_bedrock_mantle.py
git commit -m "feat(clients): bedrock mantle client via raw requests + sigv4"
```

---

## Task 8: Anthropic 1P client wrapper

**Files:**
- Create: `clients/anthropic_1p.py`
- Test: `tests/test_anthropic_1p.py`

Disabled by default at runtime (requires `ANTHROPIC_API_KEY` with credits) but implemented for future use.

- [ ] **Step 1: Write failing test `tests/test_anthropic_1p.py`**

```python
from clients.anthropic_1p import build_kwargs_1p


def test_build_kwargs_1p_opus_47_effort():
    k = build_kwargs_1p(
        model_id="claude-opus-4-7", prompt="hi", max_tokens=200,
        effort="medium", tools=None,
    )
    assert k["model"] == "claude-opus-4-7"
    assert k["max_tokens"] == 200
    assert k["thinking"] == {"type": "adaptive"}
    assert k["extra_body"] == {"output_config": {"effort": "medium"}}


def test_build_kwargs_1p_opus_46_default():
    k = build_kwargs_1p(
        model_id="claude-opus-4-6", prompt="hi", max_tokens=200,
        effort=None, tools=None,
    )
    assert "thinking" not in k
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_anthropic_1p.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `clients/anthropic_1p.py`**

```python
"""Wrapper around anthropic.Anthropic for the 1P (Anthropic direct) API."""
import time
from typing import Optional

import anthropic

from clients.base import CallResult, parse_bedrock_response


def build_kwargs_1p(
    *,
    model_id: str,
    prompt: str,
    max_tokens: int,
    effort: Optional[str],
    tools: Optional[list[dict]],
) -> dict:
    kwargs: dict = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if tools:
        kwargs["tools"] = tools
    if "opus-4-7" in model_id and effort:
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["extra_body"] = {"output_config": {"effort": effort}}
    return kwargs


class AnthropicOnePClient:
    def __init__(self, auth_method: str = "api_key"):
        self._client = anthropic.Anthropic()
        self._auth_method = auth_method

    def invoke(
        self,
        *,
        model_id: str,
        prompt: str,
        prompt_label: str,
        max_tokens: int,
        effort: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        run_index: int = 0,
        test_id: str = "",
    ) -> CallResult:
        kwargs = build_kwargs_1p(
            model_id=model_id, prompt=prompt, max_tokens=max_tokens,
            effort=effort, tools=tools,
        )
        t0 = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        latency = time.perf_counter() - t0
        resp_dict = {
            "usage": {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
            "content": [_block_to_dict(b) for b in resp.content],
            "stop_reason": resp.stop_reason,
        }
        return parse_bedrock_response(
            resp_dict, latency_s=latency, backend="1p",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
            prompt_label=prompt_label, run_index=run_index, test_id=test_id,
        )


def _block_to_dict(block) -> dict:
    btype = getattr(block, "type", None)
    if btype == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if btype == "thinking":
        return {"type": "thinking", "thinking": getattr(block, "thinking", "")}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", ""),
            "name": getattr(block, "name", ""),
            "input": getattr(block, "input", {}),
        }
    return {"type": btype or "unknown"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_anthropic_1p.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add clients/anthropic_1p.py tests/test_anthropic_1p.py
git commit -m "feat(clients): anthropic 1p wrapper (disabled by default at runtime)"
```

---

## Task 9: Benchmark case modules for Tests 1, 2, 3

**Files:**
- Create: `cases/effort.py`
- Create: `cases/length.py`
- Create: `cases/tools.py`
- Test: `tests/test_cases.py`

- [ ] **Step 1: Write failing test `tests/test_cases.py`**

```python
from cases.effort import cases as effort_cases
from cases.length import cases as length_cases
from cases.tools import cases as tool_cases


def test_effort_cases_count_and_ids():
    cs = effort_cases()
    assert len(cs) == 5  # 4.7 × 4 effort + 4.6 × 1
    # All same test_id
    assert {c.test_id for c in cs} == {"test_1"}
    # 4.7 has four effort levels
    efforts = {c.effort for c in cs if "opus-4-7" in c.model_id}
    assert efforts == {"low", "medium", "high", "max"}


def test_length_cases_count_and_prompts():
    cs = length_cases()
    assert len(cs) == 4
    assert {c.test_id for c in cs} == {"test_2"}
    labels = {c.prompt_label for c in cs}
    assert labels == {"short", "long"}


def test_tools_cases_count_and_tools():
    cs = tool_cases()
    assert len(cs) == 2
    assert {c.test_id for c in cs} == {"test_3"}
    for c in cs:
        assert c.tools is not None
        assert len(c.tools) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cases.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `cases/effort.py`**

```python
"""Test 1: effort level vs token consumption."""
from cases.base import TestCase
from cases.prompts import PROOF_PROMPT
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    out: list[TestCase] = []
    for effort in ("low", "medium", "high", "max"):
        out.append(TestCase(
            name=f"opus-4.7-effort-{effort}",
            test_id="test_1",
            backend="bedrock_runtime",
            model_id=m47,
            prompt=PROOF_PROMPT,
            prompt_label="proof",
            max_tokens=1000,
            effort=effort,
        ))
    out.append(TestCase(
        name="opus-4.6-native-adaptive",
        test_id="test_1",
        backend="bedrock_runtime",
        model_id=m46,
        prompt=PROOF_PROMPT,
        prompt_label="proof",
        max_tokens=1000,
    ))
    return out
```

- [ ] **Step 4: Create `cases/length.py`**

```python
"""Test 2: prompt length scaling."""
from cases.base import TestCase
from cases.prompts import SHORT_PROMPT, LONG_PROMPT
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    return [
        TestCase(name="opus-4.7-short", test_id="test_2",
                 backend="bedrock_runtime", model_id=m47,
                 prompt=SHORT_PROMPT, prompt_label="short", max_tokens=400),
        TestCase(name="opus-4.7-long", test_id="test_2",
                 backend="bedrock_runtime", model_id=m47,
                 prompt=LONG_PROMPT, prompt_label="long", max_tokens=400),
        TestCase(name="opus-4.6-short", test_id="test_2",
                 backend="bedrock_runtime", model_id=m46,
                 prompt=SHORT_PROMPT, prompt_label="short", max_tokens=400),
        TestCase(name="opus-4.6-long", test_id="test_2",
                 backend="bedrock_runtime", model_id=m46,
                 prompt=LONG_PROMPT, prompt_label="long", max_tokens=400),
    ]
```

- [ ] **Step 5: Create `cases/tools.py`**

```python
"""Test 3: parallel tool use."""
from cases.base import TestCase
from cases.prompts import TOOL_USE_PROMPT, TOOLS_SCHEMA
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    return [
        TestCase(name="opus-4.7-tools", test_id="test_3",
                 backend="bedrock_runtime", model_id=m47,
                 prompt=TOOL_USE_PROMPT, prompt_label="tools",
                 max_tokens=400, tools=TOOLS_SCHEMA),
        TestCase(name="opus-4.6-tools", test_id="test_3",
                 backend="bedrock_runtime", model_id=m46,
                 prompt=TOOL_USE_PROMPT, prompt_label="tools",
                 max_tokens=400, tools=TOOLS_SCHEMA),
    ]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_cases.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add cases/effort.py cases/length.py cases/tools.py tests/test_cases.py
git commit -m "feat(cases): test 1/2/3 case definitions"
```

---

## Task 10: Benchmark case module for Test 4 (Mantle + auth comparison)

**Files:**
- Create: `cases/mantle.py`
- Test: extend `tests/test_cases.py`

- [ ] **Step 1: Extend test file — append to `tests/test_cases.py`**

```python
from cases.mantle import cases as mantle_cases


def test_mantle_cases_count_and_structure():
    cs = mantle_cases()
    assert len(cs) == 10
    # Cases 1-4: mantle + iam_role
    iam_mantle = [c for c in cs if c.backend == "bedrock_mantle" and c.auth_method == "iam_role"]
    assert len(iam_mantle) == 4
    # Cases 5-10: bedrock_api_key (3 runtime + 3 mantle)
    api_key_cases = [c for c in cs if c.auth_method == "bedrock_api_key"]
    assert len(api_key_cases) == 6
    # All use 4.7 model only
    for c in cs:
        assert "opus-4-7" in c.model_id


def test_mantle_cases_cover_all_prompts():
    cs = mantle_cases()
    prompt_labels = {c.prompt_label for c in cs}
    assert "proof" in prompt_labels
    assert "long" in prompt_labels
    assert "tools" in prompt_labels
    assert "short" in prompt_labels
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cases.py -v`
Expected: 2 new failing tests (import error for `cases.mantle`).

- [ ] **Step 3: Create `cases/mantle.py`**

```python
"""Test 4: Mantle endpoint cross-check + IAM vs Bedrock-API-key auth comparison.

Cases 1-4 (mantle / iam_role): parity check — Mantle should produce identical
token counts to runtime; latency may differ slightly.

Cases 5-10 (bedrock_api_key on both endpoints): isolate the auth-method
latency effect by pairing each auth_key case with an iam_role baseline.
"""
from cases.base import TestCase
from cases.prompts import PROOF_PROMPT, SHORT_PROMPT, LONG_PROMPT, TOOL_USE_PROMPT, TOOLS_SCHEMA
import config


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    out: list[TestCase] = []

    # 1-4: Mantle parity check with iam_role
    out.append(TestCase(name="mantle-iam-short", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=SHORT_PROMPT, prompt_label="short", max_tokens=400,
                       auth_method="iam_role"))
    out.append(TestCase(name="mantle-iam-long", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=LONG_PROMPT, prompt_label="long", max_tokens=400,
                       auth_method="iam_role"))
    out.append(TestCase(name="mantle-iam-proof-max", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=PROOF_PROMPT, prompt_label="proof", max_tokens=1000,
                       effort="max", auth_method="iam_role"))
    out.append(TestCase(name="mantle-iam-tools", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=TOOL_USE_PROMPT, prompt_label="tools", max_tokens=400,
                       tools=TOOLS_SCHEMA, auth_method="iam_role"))

    # 5-10: bedrock_api_key auth on both endpoints, paired with main-run baselines
    out.append(TestCase(name="runtime-apikey-long", test_id="test_4",
                       backend="bedrock_runtime", model_id=m47,
                       prompt=LONG_PROMPT, prompt_label="long", max_tokens=400,
                       auth_method="bedrock_api_key"))
    out.append(TestCase(name="mantle-apikey-long", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=LONG_PROMPT, prompt_label="long", max_tokens=400,
                       auth_method="bedrock_api_key"))
    out.append(TestCase(name="runtime-apikey-proof-max", test_id="test_4",
                       backend="bedrock_runtime", model_id=m47,
                       prompt=PROOF_PROMPT, prompt_label="proof", max_tokens=1000,
                       effort="max", auth_method="bedrock_api_key"))
    out.append(TestCase(name="mantle-apikey-proof-max", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=PROOF_PROMPT, prompt_label="proof", max_tokens=1000,
                       effort="max", auth_method="bedrock_api_key"))
    out.append(TestCase(name="runtime-apikey-tools", test_id="test_4",
                       backend="bedrock_runtime", model_id=m47,
                       prompt=TOOL_USE_PROMPT, prompt_label="tools", max_tokens=400,
                       tools=TOOLS_SCHEMA, auth_method="bedrock_api_key"))
    out.append(TestCase(name="mantle-apikey-tools", test_id="test_4",
                       backend="bedrock_mantle", model_id=m47,
                       prompt=TOOL_USE_PROMPT, prompt_label="tools", max_tokens=400,
                       tools=TOOLS_SCHEMA, auth_method="bedrock_api_key"))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cases.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add cases/mantle.py tests/test_cases.py
git commit -m "feat(cases): test 4 - mantle parity + iam/api_key auth comparison"
```

---

## Task 11: Reporter — JSON writers

**Files:**
- Create: `reporter.py`
- Test: `tests/test_reporter.py`

- [ ] **Step 1: Write failing test `tests/test_reporter.py`**

```python
import json
from pathlib import Path

from clients.base import CallResult
from stats import aggregate_results
from reporter import write_raw_json, write_aggregated_json


def _make_result(run_index=0, test_id="test_1", effort="low"):
    return CallResult(
        input_tokens=37, output_tokens=100, latency_s=1.5,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=effort, prompt_label="proof",
        stop_reason="end_turn", cost_usd=0.005,
        run_index=run_index, test_id=test_id,
    )


def test_write_raw_json(tmp_path: Path):
    results = [_make_result(i) for i in range(3)]
    meta = {"sdk_version": "0.96.0", "region": "us-east-1"}
    out = tmp_path / "raw.json"
    write_raw_json(results, meta, out)
    data = json.loads(out.read_text())
    assert data["meta"]["sdk_version"] == "0.96.0"
    assert len(data["results"]) == 3
    assert data["results"][0]["input_tokens"] == 37


def test_write_aggregated_json(tmp_path: Path):
    results = [_make_result(i) for i in range(5)]
    agg = aggregate_results(results)
    out = tmp_path / "aggregated.json"
    write_aggregated_json(agg, out)
    data = json.loads(out.read_text())
    assert len(data) == 1
    entry = data[0]
    assert entry["test_id"] == "test_1"
    assert entry["n_runs"] == 5
    assert entry["n_success"] == 5
    assert entry["input_tokens_mean"] == 37.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'reporter'`

- [ ] **Step 3: Create `reporter.py` (JSON writers only for now)**

```python
"""JSON and Markdown report writers."""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporter.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add reporter.py tests/test_reporter.py
git commit -m "feat(reporter): raw.json and aggregated.json writers"
```

---

## Task 12: Reporter — Markdown report generator

**Files:**
- Modify: `reporter.py` (append)
- Test: extend `tests/test_reporter.py`

- [ ] **Step 1: Append to `tests/test_reporter.py`**

```python
from reporter import write_markdown_report


def test_write_markdown_report(tmp_path: Path):
    results = [_make_result(i) for i in range(5)]
    agg = aggregate_results(results)
    out = tmp_path / "report.md"
    meta = {
        "sdk_version": "0.96.0", "region": "us-east-1",
        "backends": ["bedrock_runtime"],
        "total_calls": 5, "total_cost_usd": 0.025,
        "wall_time_s": 15.2, "start_ts": "2026-04-18T12:00:00",
    }
    write_markdown_report(results, agg, meta, out)
    text = out.read_text()
    # Header present
    assert "Opus 4.7 vs 4.6 Benchmark Report" in text
    assert "sdk_version" in text or "SDK" in text
    # Each test section present (only test_1 here; others empty is fine)
    assert "Test 1" in text
    # Aggregate data present
    assert "37" in text  # input tokens mean
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporter.py::test_write_markdown_report -v`
Expected: FAIL — `ImportError: cannot import name 'write_markdown_report'`

- [ ] **Step 3: Append to `reporter.py`**

```python
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

    lines.append("## Summary — blog claims verification")
    lines.append("")
    lines.append(_render_blog_claims_section(agg))
    lines.append("")

    path.write_text("\n".join(lines))


def _render_blog_claims_section(agg: dict[tuple, CaseAggregate]) -> str:
    """Produce the side-by-side blog-vs-measured comparison table."""
    out_lines = [
        "| Claim | Blog value | Measured | Status |",
        "|---|---|---|---|",
    ]

    # Effort level does not affect input tokens (Test 1, 4.7)
    t1_47 = [a for a in agg.values() if a.test_id == "test_1" and "opus-4-7" in a.model_id]
    if t1_47:
        inputs = {round(a.input_tokens_mean) for a in t1_47}
        status = "✅" if len(inputs) == 1 else "❌"
        out_lines.append(
            f"| Effort does not affect input tokens | identical | {sorted(inputs)} | {status} |"
        )

    # 4.7 vs 4.6 overhead on proof prompt
    t1_46 = [a for a in agg.values() if a.test_id == "test_1" and "opus-4-6" in a.model_id]
    if t1_47 and t1_46:
        avg_47 = sum(a.input_tokens_mean for a in t1_47) / len(t1_47)
        avg_46 = t1_46[0].input_tokens_mean
        if avg_46 > 0:
            overhead = (avg_47 - avg_46) / avg_46 * 100
            status = "✅" if 55 <= overhead <= 70 else "⚠"
            out_lines.append(
                f"| Proof prompt overhead: +61% | +61% | +{overhead:.1f}% | {status} |"
            )

    return "\n".join(out_lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporter.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add reporter.py tests/test_reporter.py
git commit -m "feat(reporter): markdown report generator with blog-claims verification"
```

---

## Task 13: Runner — CLI, preflight, case collection

**Files:**
- Create: `run.py`
- Create: `runner/__init__.py`
- Create: `runner/preflight.py`
- Create: `runner/dispatch.py`
- Test: `tests/test_runner.py`

We split `run.py` (thin CLI entry) from `runner/` modules (the actual loop logic) so each piece is unit-testable.

- [ ] **Step 1: Create `runner/__init__.py`**

```bash
mkdir -p runner
touch runner/__init__.py
```

- [ ] **Step 2: Write failing test `tests/test_runner.py`**

```python
from runner.dispatch import collect_cases
from runner.preflight import check_auth_env


def test_collect_cases_all():
    cs = collect_cases(selected=["1", "2", "3", "4"])
    # 5 + 4 + 2 + 10 = 21 cases
    assert len(cs) == 21


def test_collect_cases_subset():
    cs = collect_cases(selected=["1", "3"])
    assert len(cs) == 7  # 5 + 2


def test_check_auth_env_bedrock_with_key(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "x")
    ok, msg = check_auth_env(backends={"bedrock"})
    assert ok, msg


def test_check_auth_env_bedrock_missing(monkeypatch):
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    # Depending on the env this may still find credentials (instance role, etc.)
    # So we only assert the function returns a (bool, str) tuple.
    result = check_auth_env(backends={"bedrock"})
    assert isinstance(result, tuple) and len(result) == 2


def test_check_auth_env_1p_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ok, msg = check_auth_env(backends={"1p"})
    assert not ok
    assert "ANTHROPIC_API_KEY" in msg
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Create `runner/dispatch.py`**

```python
"""Collect test cases from case modules based on CLI selection."""
from cases import effort, length, tools, mantle
from cases.base import TestCase


TEST_MODULES = {
    "1": effort,
    "2": length,
    "3": tools,
    "4": mantle,
}


def collect_cases(selected: list[str]) -> list[TestCase]:
    """selected is a list of test ids like ['1', '2', '3', '4'] or subset."""
    out: list[TestCase] = []
    for tid in selected:
        module = TEST_MODULES.get(tid)
        if module is None:
            raise ValueError(f"Unknown test id: {tid}")
        out.extend(module.cases())
    return out
```

- [ ] **Step 5: Create `runner/preflight.py`**

```python
"""Pre-flight checks before running the benchmark."""
import os
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """Load .env.local if it exists. Real env vars take precedence."""
    env_path = Path(".env.local")
    if env_path.exists():
        load_dotenv(env_path)


def check_auth_env(backends: set[str]) -> tuple[bool, str]:
    """Return (ok, message). Verifies required auth env vars for selected backends."""
    errors: list[str] = []

    if "1p" in backends:
        if not os.getenv("ANTHROPIC_API_KEY"):
            errors.append("1P backend selected but ANTHROPIC_API_KEY is not set.")

    if "bedrock" in backends:
        has_bearer = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))
        has_iam = bool(
            os.getenv("AWS_PROFILE")
            or os.getenv("AWS_ACCESS_KEY_ID")
            or _has_any_credential_source()
        )
        if not (has_bearer or has_iam):
            errors.append(
                "Bedrock backend selected but no AWS auth found. Set one of: "
                "AWS_BEARER_TOKEN_BEDROCK, AWS_PROFILE, AWS_ACCESS_KEY_ID, or run on "
                "an EC2 instance with an attached role."
            )

    if errors:
        return False, "\n".join(errors)
    return True, "OK"


def _has_any_credential_source() -> bool:
    """Return True if boto3 credential chain can find any credential."""
    try:
        from botocore.session import Session
        return Session().get_credentials() is not None
    except Exception:
        return False
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_runner.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add runner/__init__.py runner/dispatch.py runner/preflight.py tests/test_runner.py
git commit -m "feat(runner): case collection and preflight auth checks"
```

---

## Task 14: Runner — execution loop with retry and client selection

**Files:**
- Create: `runner/execute.py`
- Test: `tests/test_runner_execute.py`

- [ ] **Step 1: Write failing test `tests/test_runner_execute.py`**

```python
from unittest.mock import MagicMock

from clients.base import CallResult
from runner.execute import execute_case_with_retry, select_client


def test_select_client_bedrock_runtime():
    from clients.bedrock_runtime import BedrockRuntimeClient
    c = select_client("bedrock_runtime", "iam_role")
    assert isinstance(c, BedrockRuntimeClient)


def test_select_client_bedrock_mantle():
    from clients.bedrock_mantle import BedrockMantleClient
    c = select_client("bedrock_mantle", "iam_role")
    assert isinstance(c, BedrockMantleClient)


def _fake_result(run_index=0, error=None):
    return CallResult(
        input_tokens=10, output_tokens=10, latency_s=0.1,
        thinking_chars=0, tool_calls_count=0,
        backend="bedrock_runtime", auth_method="iam_role",
        model_id="global.anthropic.claude-opus-4-7",
        effort=None, prompt_label="test",
        stop_reason="end_turn", cost_usd=0.0,
        run_index=run_index, test_id="test_x", error=error,
    )


def test_execute_case_with_retry_success_first_try():
    client = MagicMock()
    client.invoke.return_value = _fake_result()
    from cases.base import TestCase
    case = TestCase(name="n", test_id="t", backend="bedrock_runtime",
                    model_id="global.anthropic.claude-opus-4-7",
                    prompt="hi", prompt_label="p")
    r = execute_case_with_retry(client, case, run_index=0, max_attempts=3)
    assert r.error is None
    assert client.invoke.call_count == 1


def test_execute_case_with_retry_retries_on_5xx(monkeypatch):
    import anthropic
    client = MagicMock()
    # First call raises, second call succeeds
    client.invoke.side_effect = [
        anthropic.APIStatusError("server error", response=MagicMock(status_code=503), body=None),
        _fake_result(),
    ]
    from cases.base import TestCase
    case = TestCase(name="n", test_id="t", backend="bedrock_runtime",
                    model_id="global.anthropic.claude-opus-4-7",
                    prompt="hi", prompt_label="p")
    # Speed up backoff for the test
    monkeypatch.setattr("runner.execute._backoff_seconds", lambda attempt: 0.01)
    r = execute_case_with_retry(client, case, run_index=0, max_attempts=3)
    assert r.error is None
    assert client.invoke.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_runner_execute.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `runner/execute.py`**

```python
"""Execute a single TestCase, with retry handling and client dispatch."""
import time
from dataclasses import replace
from typing import Protocol

import anthropic
import requests

import config
from cases.base import TestCase
from clients.anthropic_1p import AnthropicOnePClient
from clients.base import CallResult
from clients.bedrock_mantle import BedrockMantleClient
from clients.bedrock_runtime import BedrockRuntimeClient


class _Client(Protocol):
    def invoke(self, *, model_id: str, prompt: str, prompt_label: str,
               max_tokens: int, effort: str | None = None,
               tools: list[dict] | None = None,
               run_index: int = 0, test_id: str = "") -> CallResult: ...


_CLIENT_CACHE: dict[tuple[str, str], _Client] = {}


def select_client(backend: str, auth_method: str) -> _Client:
    """Return a client instance for the given backend + auth method.

    Instances are cached per (backend, auth_method) to avoid rebuilding for every call.
    Note: switching auth_method for bedrock_api_key requires AWS_BEARER_TOKEN_BEDROCK to
    be set in the environment. boto3's credential chain picks it up transparently.
    """
    key = (backend, auth_method)
    if key in _CLIENT_CACHE:
        return _CLIENT_CACHE[key]

    if backend == "bedrock_runtime":
        client = BedrockRuntimeClient(auth_method=auth_method)
    elif backend == "bedrock_mantle":
        client = BedrockMantleClient(auth_method=auth_method)
    elif backend == "1p":
        client = AnthropicOnePClient(auth_method=auth_method)
    else:
        raise ValueError(f"Unknown backend: {backend}")

    _CLIENT_CACHE[key] = client
    return client


def _backoff_seconds(attempt: int) -> float:
    return config.RETRY_BACKOFF_BASE_S * (2 ** attempt)


def execute_case_with_retry(
    client: _Client,
    case: TestCase,
    *,
    run_index: int,
    max_attempts: int = config.RETRY_MAX_ATTEMPTS,
) -> CallResult:
    """Execute one run of a TestCase, retrying on throttle and 5xx errors.

    Returns a CallResult with error set if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return client.invoke(
                model_id=case.model_id,
                prompt=case.prompt,
                prompt_label=case.prompt_label,
                max_tokens=case.max_tokens,
                effort=case.effort,
                tools=case.tools,
                run_index=run_index,
                test_id=case.test_id,
            )
        except anthropic.RateLimitError as e:
            last_exc = e
        except anthropic.APIStatusError as e:
            last_exc = e
            status = getattr(e, "status_code", None) or getattr(
                getattr(e, "response", None), "status_code", 0
            )
            if status and status < 500:
                break
        except requests.HTTPError as e:
            last_exc = e
            if e.response is not None and e.response.status_code < 500:
                break
        except Exception as e:
            # Treat other unexpected errors as terminal (no retry)
            last_exc = e
            break

        if attempt + 1 < max_attempts:
            time.sleep(_backoff_seconds(attempt))

    # All attempts failed — return a failure CallResult
    return CallResult(
        input_tokens=0, output_tokens=0, latency_s=0.0,
        thinking_chars=0, tool_calls_count=0,
        backend=case.backend, auth_method=case.auth_method,
        model_id=case.model_id, effort=case.effort,
        prompt_label=case.prompt_label,
        stop_reason="error", cost_usd=0.0,
        run_index=run_index, test_id=case.test_id,
        error=f"{type(last_exc).__name__}: {str(last_exc)[:200]}",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_runner_execute.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add runner/execute.py tests/test_runner_execute.py
git commit -m "feat(runner): execution loop with retry and client selection"
```

---

## Task 15: CLI entry — `run.py` with dry-run, progress, main loop

**Files:**
- Create: `run.py`
- Test: smoke test via CLI in Step 6

- [ ] **Step 1: Create `run.py`**

```python
"""CLI entry point for the Opus 4.7 vs 4.6 benchmark."""
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
    if test_arg == "all":
        return ["1", "2", "3", "4"]
    ids = [t.strip() for t in test_arg.split(",")]
    for t in ids:
        if t not in ("1", "2", "3", "4"):
            console.print(f"[red]Unknown test id: {t}. Valid: 1,2,3,4 or all[/red]")
            sys.exit(2)
    return ids


def resolve_backends(backend_arg: str, cases: list[TestCase]) -> set[str]:
    """Convert case backends to the set used by check_auth_env.

    'bedrock_runtime' and 'bedrock_mantle' both map to 'bedrock' for auth purposes.
    """
    case_backends = {c.backend for c in cases}
    out: set[str] = set()
    if any(b.startswith("bedrock") for b in case_backends):
        out.add("bedrock")
    if "1p" in case_backends:
        out.add("1p")
    return out


def print_plan(cases: list[TestCase], runs: int) -> float:
    """Print the execution plan. Returns an estimated cost in USD."""
    total_calls = len(cases) * runs
    # Rough cost estimate assuming average case costs ~$0.005 (will vary)
    # effort=max cases cost ~$0.025 each
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
    """Dump a single call's result JSON for forensic debugging."""
    path = results_dir / "calls" / f"{case.test_id}_{case.name}_run{run_index}.json"
    path.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False))


def run_smoke_tests() -> None:
    """One small call per active backend to fail fast before the main run."""
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

    # Filter by --backend choice for 1P (skip bedrock cases if --backend 1p)
    if args.backend == "1p":
        # For now, 1P cases are not pre-defined separately; skip if 1P requested
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
```

- [ ] **Step 2: Verify module imports**

Run: `cd /home/ec2-user/my-project/Opus4.6vsOpus4.7 && python3 -c "import run; print('run.py imports OK')"`
Expected: `run.py imports OK`

- [ ] **Step 3: Test `--dry-run` (no API calls)**

Run: `cd /home/ec2-user/my-project/Opus4.6vsOpus4.7 && python3 run.py --dry-run --test all --runs 5`
Expected output (approximately):
```
Plan: 21 cases × 5 runs = 105 calls
Estimated cost: ~$1.00–$2.00
Estimated wall time: ~3–8 min
Dry run — exiting without calling the API
```

(Note: the spec lists 108 including smoke+preflight; the runner prints 105 from cases alone + smoke adds ~2 more at runtime.)

- [ ] **Step 4: Test `--test 1 --dry-run`**

Run: `python3 run.py --test 1 --dry-run --runs 5`
Expected: `Plan: 5 cases × 5 runs = 25 calls`

- [ ] **Step 5: Run unit tests to ensure nothing regressed**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add run.py
git commit -m "feat(run): cli entry with dry-run, progress, smoke, and report output"
```

---

## Task 16: Integration — smoke run with `--runs 1 --test 1`

The first real API call. Verifies end-to-end wiring before committing to the full run.

- [ ] **Step 1: Ensure `.env.local` is loaded**

Check it exists (created in earlier session):

```bash
ls -la /home/ec2-user/my-project/Opus4.6vsOpus4.7/.env.local
```

Expected: file exists, 600 permissions.

- [ ] **Step 2: Run a 1-run Test-1-only**

```bash
cd /home/ec2-user/my-project/Opus4.6vsOpus4.7
python3 run.py --test 1 --runs 1
```

Expected:
- Smoke call reports OK with ~8 input / 19 output tokens.
- 5 Test 1 cases run (4× 4.7 effort levels + 1× 4.6).
- Results directory created under `results/YYYY-MM-DD-HHMM/`.
- `report.md` is generated and includes Test 1 table.

- [ ] **Step 3: Inspect results**

```bash
ls -la results/
cat $(ls -td results/*/ | head -1)report.md
```

Verify:
- Input tokens identical across all 4 effort cases (expected ~24 or ~37).
- 4.6 case has thinking_chars > 0.
- 4.7 cases have thinking_chars == 0.

- [ ] **Step 4: Commit (if git index has any generated files — should be none due to .gitignore)**

```bash
git status
# results/ should be ignored; if anything else appears, decide whether to commit
```

---

## Task 17: Integration — full run

- [ ] **Step 1: Run the full benchmark**

```bash
cd /home/ec2-user/my-project/Opus4.6vsOpus4.7
python3 run.py --test all --runs 5 2>&1 | tee run.log
```

Expected: progress bar shows 105/105 + 2 smoke = ~107 calls. Completes in 15–30 min. Final line reports total cost ($1–$2).

- [ ] **Step 2: Spot-check the report**

```bash
RESULTS=$(ls -td results/*/ | head -1)
cat "$RESULTS/report.md" | head -80
```

Check:
- Header metadata populated (SDK version, region, backends, auth methods, total cost, wall time).
- Test 1 table: all 4.7 effort cases have identical input_tokens_mean; 4.6 differs.
- Test 2 table: short vs long prompts have different token counts; overhead grows with length.
- Test 3 table: both models show tool_calls_mean close to 4.0.
- Test 4 table: runtime vs mantle rows with matching token counts; latency delta visible.
- Summary section: blog-claim verification lines populated with ✅ / ⚠.

- [ ] **Step 3: Check for errors in raw.json**

```bash
python3 -c "
import json, sys
from pathlib import Path
d = sorted(Path('results').iterdir())[-1]
raw = json.loads((d/'raw.json').read_text())
errs = [r for r in raw['results'] if r.get('error')]
print(f'Errors: {len(errs)}/{len(raw[\"results\"])}')
for e in errs[:5]:
    print(' ', e['test_id'], e['model_id'][-20:], e['error'][:80])
"
```

Expected: 0 errors, or a small number with Mantle if auth_method differences cause issues (document in divergence log).

- [ ] **Step 4: If Test 4 Mantle cases failed with auth errors**

This is a known risk area. Diagnose:

```bash
python3 -c "
from botocore.session import Session
creds = Session().get_credentials()
print('Credentials:', creds.__class__.__name__ if creds else 'NONE')
print('Method:', getattr(creds, 'method', 'unknown') if creds else 'NONE')
"
```

If `AWS_BEARER_TOKEN_BEDROCK` isn't being used for Mantle SigV4 signing, the expected behavior: the test captures the auth error in `CallResult.error` and continues. Verify via the error string in `raw.json`.

- [ ] **Step 5: Verify acceptance criteria from spec**

Check each acceptance criterion from the spec's "Acceptance criteria" section:
- [ ] `--dry-run` prints 108-call plan (close to 105 main + smoke/preflight).
- [ ] `--test all` completed without unhandled exceptions.
- [ ] Report includes measured values next to blog expected values.
- [ ] Divergences documented in the report's summary section.

---

## Task 18: Docs and cleanup

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# Opus 4.7 vs 4.6 Benchmark

Reproduces the Apr 17, 2026 field-report comparison of Opus 4.7 and Opus 4.6
on AWS Bedrock. Measures token overhead, latency, thinking-block visibility,
parallel tool-use cost, and Mantle endpoint parity.

## Quick start

```bash
cp .env.local.example .env.local
# Fill in ANTHROPIC_API_KEY (optional) and AWS_BEARER_TOKEN_BEDROCK or AWS_PROFILE

pip install -r requirements.txt

python run.py --dry-run              # see the plan
python run.py --test all --runs 5    # run everything (~15–30 min, ~$1–2)
```

## CLI options

- `--test` — `all` or comma-separated subset (`1,2,3,4`)
- `--runs` — number of runs per case (default 5)
- `--backend` — `bedrock` (default) or `1p` (requires Anthropic credits)
- `--dry-run` — print plan only, no API calls
- `--no-save-bodies` — disable per-call body dumps (default on)
- `--report-only <dir>` — regenerate `report.md` from existing `raw.json`

## Results

Each run writes:
- `results/YYYY-MM-DD-HHMM/raw.json` — every CallResult with full metadata
- `results/YYYY-MM-DD-HHMM/aggregated.json` — mean/stdev per case
- `results/YYYY-MM-DD-HHMM/report.md` — human-readable report
- `results/YYYY-MM-DD-HHMM/calls/*.json` — per-call body dumps

## Spec and plan

- Design spec: `docs/superpowers/specs/2026-04-18-opus-47-vs-46-benchmark-design.md`
- Implementation plan: `docs/superpowers/plans/2026-04-18-opus-47-vs-46-benchmark.md`
```

- [ ] **Step 2: Run full test suite one more time**

```bash
pytest tests/ -v
```

Expected: all unit tests pass.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with quick-start and CLI reference"
```

---

## Self-review summary

All tasks map to spec requirements:
- Tasks 1-5 → spec: project scaffold, config, CallResult, TestCase, prompts
- Tasks 6-8 → spec: three client wrappers (bedrock_runtime, bedrock_mantle with raw SigV4, 1p)
- Tasks 9-10 → spec: 4 benchmark case modules
- Tasks 11-12 → spec: reporter (JSON + Markdown with blog-claim verification)
- Tasks 13-15 → spec: runner (CLI, preflight, execution loop, retry)
- Tasks 16-18 → spec: integration (smoke, full run, docs)

Known risk areas (addressed in plan):
- Mantle SigV4 service-name quirk — Task 7 hand-rolls the signing
- 4.7 vs 4.6 thinking/effort API divergence — Task 6 branches on model ID
- 1P credits unavailable — Task 15 gracefully rejects `--backend 1p`
- Auth_method `bedrock_api_key` requires env var set when the Mantle case runs — preflight (Task 13) validates presence

No TBD / placeholder markers in the plan. All code blocks are complete and runnable.
