<p align="center">
  <kbd><a href="#한국어">한국어</a></kbd> · <kbd><a href="#english">English</a></kbd>
</p>

---

## 한국어

### 시스템 개요

Python으로 작성된 Claude Opus 4.7 vs 4.6 벤치마크 하네스. AWS Bedrock(Runtime + Mantle 엔드포인트) 대상으로 13개 테스트 차원 (토큰 overhead, latency, TTFT, tool 사용, 다중 턴, 언어별 토큰화, 인증 방식, 응답 품질)을 5회 평균으로 측정. Anthropic 1P API도 infrastructure만 준비(credit 필요 시 활성화).

### 레이어별 컴포넌트

**Ingestion (API 호출)**
- `clients/bedrock_runtime.py` — `anthropic.AnthropicBedrock`, IAM/bearer token 분리 인증
- `clients/bedrock_mantle.py` — raw requests + SigV4 (`bedrock-mantle` service name)
- `clients/anthropic_1p.py` — `anthropic.Anthropic` (기본 비활성)

**Storage (데이터 모델)**
- `clients/base.py::CallResult` — 불변 측정 결과 (18 필드)
- `cases/base.py::TestCase` — 불변 테스트 케이스 정의 (13 필드)

**Processing (벤치마크 orchestration)**
- `runner/preflight.py` — 인증 환경 검증 (IAM 또는 Bedrock API key)
- `runner/dispatch.py` — test ID → case 모듈 매핑 (13 테스트 등록됨)
- `runner/execute.py` — retry loop + client 선택 캐시
- `stats.py` — CallResult 집계 (mean/stdev, 실패 제외)

**Query (CLI 진입점)**
- `run.py` — 벤치마크 실행 CLI (`--test`, `--runs`, `--dry-run`, `--report-only`)
- `score.py` — LLM-judge 품질 평가 CLI (`--prompt-label`, `--runs`)

**Presentation (리포트 생성)**
- `reporter.py` — JSON (raw + aggregated) + Markdown 생성
- `scorers/judge.py` — Pairwise 품질 비교 + 포지션 편향 진단

**Observability**
- Console progress bar (rich)
- Per-call body dumps in `results/<ts>/calls/` (forensic debugging)
- Pytest 62 unit tests

**Security**
- `.env.local` (permissions 600, gitignored)
- PreToolUse hook: inline secret pattern 차단
- Runtime + Mantle auth_method 명시적 분리 (bearer token × IAM 혼용 방지)

### 전체 아키텍처 다이어그램

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                           CLI Layer                             │
 │   run.py (benchmark)            score.py (quality scorer)       │
 └────────┬──────────────────────────────────┬─────────────────────┘
          │                                  │
          ▼                                  ▼
 ┌──────────────────┐              ┌─────────────────────┐
 │  runner/*        │              │  scorers/judge.py   │
 │   preflight      │              │   pairwise 4.7 vs   │
 │   dispatch       │              │   4.6 + A/B random  │
 │   execute(retry) │              │                     │
 └────────┬─────────┘              └──────────┬──────────┘
          │                                   │
          ▼                                   │
 ┌──────────────────────────────────────────┐ │
 │  cases/ (pure data — 13 test modules)    │ │
 │   base.py, prompts.py                    │ │
 │   effort, length, tools, mantle,         │ │
 │   caching*, multiturn, streaming,        │ │
 │   tools_scaling, tool_forcing,           │ │
 │   multiturn_extreme, language_code,      │ │
 │   system_caching*, multiturn_knee        │ │
 │   (* = deferred)                         │ │
 └────────┬─────────────────────────────────┘ │
          │                                   │
          ▼                                   ▼
 ┌─────────────────────────────────────────────────┐
 │  clients/ (API wrappers)                        │
 │   base.py (CallResult, parse_bedrock_response)  │
 │   bedrock_runtime.py  bedrock_mantle.py         │
 │   anthropic_1p.py                               │
 └────────┬────────────────────────┬───────────────┘
          │                        │
          ▼                        ▼
 ┌────────────────┐       ┌────────────────────────┐
 │ AWS Bedrock    │       │ AWS Bedrock Mantle     │
 │   Runtime      │       │  (raw SigV4)           │
 │   (SDK path)   │       │                        │
 └────────────────┘       └────────────────────────┘
          │                        │
          └────────┬───────────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ stats.py        │
          │  aggregate      │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ reporter.py     │
          │  raw.json       │
          │  aggregated.json│
          │  report.md      │
          └────────┬────────┘
                   │
                   ▼
          results/YYYY-MM-DD-HHMM/
```

### Data flow

CLI args → preflight → dispatch(test_ids) → [for case in cases] → execute_case_with_retry → client.invoke → CallResult → aggregate → reporter → results/

### 핵심 설계 결정

1. **TestCase가 순수 데이터인 이유**: 실행 로직 없음 → 케이스 조합·필터링·재실행 모두 무부작용
2. **retry는 runner/execute.py에만**: 클라이언트 래퍼는 단일 책임(호출만) 유지
3. **Mantle은 raw HTTP**: 블로그가 지적한 대로 SDK가 `bedrock` 서비스명으로 서명 → Mantle은 `bedrock-mantle` 요구
4. **auth_method 명시적 분리**: boto3 credential chain이 bearer token을 자동 우선 → 두 auth path 비교 무의미해질 위험 차단
5. **Frozen dataclass 전면 사용**: 병렬·재집계·JSON 직렬화 모두 안전
6. **prompts.py 단일 진실 소스**: 프롬프트 변경 → 한 파일 한 곳

### 운영

- 벤치마크 실행: [docs/runbooks/run-benchmark.md](./runbooks/run-benchmark.md)
- Quality scorer: [docs/runbooks/run-scorer.md](./runbooks/run-scorer.md)
- 결과 해석: [docs/superpowers/findings/](./superpowers/findings/)

---

## English

### System Overview

Python benchmark harness for Claude Opus 4.7 vs 4.6 on AWS Bedrock (Runtime + Mantle endpoints). Measures 13 test dimensions (token overhead, latency, TTFT, tool use, multi-turn, language-specific tokenization, auth methods, response quality) averaged over 5 runs. Infrastructure also supports Anthropic 1P API (off by default, requires credits).

### Components by Layer

**Ingestion (API calls)**
- `clients/bedrock_runtime.py` — `anthropic.AnthropicBedrock`, separated IAM/bearer token auth paths
- `clients/bedrock_mantle.py` — raw requests + SigV4 (`bedrock-mantle` service name)
- `clients/anthropic_1p.py` — `anthropic.Anthropic` (disabled by default)

**Storage (data types)**
- `clients/base.py::CallResult` — frozen measurement result (18 fields)
- `cases/base.py::TestCase` — frozen test-case definition (13 fields)

**Processing (benchmark orchestration)**
- `runner/preflight.py` — validate auth env (IAM or Bedrock API key)
- `runner/dispatch.py` — test ID → case module mapping (13 tests registered)
- `runner/execute.py` — retry loop + client-selection cache
- `stats.py` — CallResult aggregation (mean/stdev, excludes failures)

**Query (CLI entry points)**
- `run.py` — benchmark CLI
- `score.py` — LLM-judge quality scorer CLI

**Presentation (report generation)**
- `reporter.py` — raw + aggregated JSON + Markdown
- `scorers/judge.py` — pairwise quality comparison + position-bias diagnostic

**Observability**
- Rich console progress bar
- Per-call body dumps in `results/<ts>/calls/` (forensic debugging)
- pytest 62 unit tests

**Security**
- `.env.local` (permissions 600, gitignored)
- PreToolUse hook blocks inline secret patterns
- Explicit `auth_method` separation (no bearer × IAM mixing)

### Key design decisions

1. **TestCase is pure data**: no execution logic → cases can be combined/filtered/rerun with zero side effects
2. **Retry lives only in runner/execute.py**: client wrappers keep single responsibility (invoke)
3. **Mantle uses raw HTTP**: SDK signs with service name `bedrock`, Mantle requires `bedrock-mantle`
4. **Explicit auth_method separation**: boto3 silently prefers bearer token, making auth-comparison meaningless unless the two paths are isolated
5. **Frozen dataclasses throughout**: safe for parallelism, aggregation, and JSON serialization
6. **prompts.py single source of truth**: change a prompt in one place

### Operations

- Run benchmark: [docs/runbooks/run-benchmark.md](./runbooks/run-benchmark.md)
- Run quality scorer: [docs/runbooks/run-scorer.md](./runbooks/run-scorer.md)
- Findings: [docs/superpowers/findings/](./superpowers/findings/)
