# opus4.6_vs_opus4.7

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-62%20passing-brightgreen)](#testing)
[![Benchmark runs](https://img.shields.io/badge/benchmark%20runs-4-blue)](docs/test-results.md)
[![API calls](https://img.shields.io/badge/API%20calls-409-blue)](docs/test-results.md)
[![Version](https://img.shields.io/badge/version-0.4.0-blue)](#)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](#prerequisites)
[![English](https://img.shields.io/badge/language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/language-한국어-red)](#한국어)

A reproducible Python benchmark harness comparing Claude Opus 4.7 versus Opus 4.6 on AWS Bedrock across 13 behavioral dimensions plus a quality scorer. Full results are documented in [`docs/test-results.md`](docs/test-results.md).

AWS Bedrock에서 Claude Opus 4.7과 4.6을 13개 행동 차원 + 품질 스코어러로 비교하는 재현 가능한 Python 벤치마크 하네스입니다. 전체 결과는 [`docs/test-results.md`](docs/test-results.md)에 상세히 정리되어 있습니다.

---

# English

## Overview

`opus4.6_vs_opus4.7` is a Python test harness that measures Opus 4.7 versus Opus 4.6 on AWS Bedrock. Each of the 13 tests is documented with its **Purpose**, **Method**, **Findings**, and **Implications** in [`docs/test-results.md`](docs/test-results.md). Every case runs 5 times and results are written to JSON plus Markdown reports suitable for internal review or public writeups.

The harness supports both Bedrock Runtime (via the `anthropic` SDK) and Bedrock Mantle (via raw SigV4 signing), with isolated authentication paths so `iam_role` and `bedrock_api_key` comparisons produce genuinely different HTTP requests.

## Features

- **13 benchmark dimensions** — effort level, prompt length, parallel tool use, multi-turn scaling (1 to 100 turns), streaming TTFT, tool schema scaling, language/code tokenization, endpoint parity, auth-method comparison, and quality judgement.
- **Dual-backend support** — Bedrock Runtime through the official SDK and Bedrock Mantle through hand-rolled HTTP + SigV4 with service name `bedrock-mantle`.
- **Auth isolation** — frozen IAM credentials and Bedrock API keys are routed through separate paths so auth-method comparisons produce genuinely different HTTP requests.
- **LLM-judge quality scorer** — pairwise 4.7 vs 4.6 comparison using Sonnet 4.6 as judge, with A/B position randomization to mitigate judge bias.
- **Reproducible reports** — per-run raw JSON, aggregated statistics (mean and standard deviation), and human-readable Markdown with per-call body dumps for forensic debugging.

## Key Findings

Eight takeaways synthesize the full test matrix. See [`docs/test-results.md`](docs/test-results.md) for the per-test Purpose / Method / Findings / Implications detail.

1. **Effort is not a cost dial.** The `effort` parameter controls output depth but leaves input tokens untouched (Test 1 — all four 4.7 variants consumed 32 input tokens, σ = 0).
2. **Korean tokenizes at parity; English and code pay the overhead.** Korean prose +5%, Python code +29%, English technical prose +57% (Test 11).
3. **Latency advantage grows with session length.** 4.7 is 10% faster at turn 1, 40% faster at turn 10, and still 25% faster at turn 100 (Tests 6, 10).
4. **TTFT is 4.7's strongest UX lever.** Streaming time-to-first-token holds at 1.15 seconds invariant to prompt length; 4.6 grows from 1.46 s to 1.59 s (Test 7).
5. **Large tool menus require `tool_choice`.** At 20 tools, 4.7 emits zero tool calls under passive prompting. `tool_choice={"type": "any"}` fixes it but caps parallelism at 2 (Tests 8, 9).
6. **Latency has a step at turn 20.** 4.7 latency is flat in a 3.7–4.3 s band up to turn 19, then jumps +16% to 4.99 s in a single increment (Test 13).
7. **Bedrock caching is unobservable in this SDK configuration.** Both user-prompt and system-prompt caching tests returned zero cache-creation and zero cache-read tokens (Tests 5, 12 — deferred).
8. **Quality scorer is directionally similar; verbosity artifacts favor 4.6 under tight token caps.** Position-randomized judge preferred 4.6 in 60% of comparisons, partly due to 4.7's more verbose preamble being truncated at `max_tokens=400` (Quality Scorer).

Observed cost across 4 benchmark runs and 2 scorer runs: **$7.14 for 409 calls** (Bedrock, us-east-1).

## Prerequisites

- Python 3.9 or later
- AWS credentials with Bedrock access — either an IAM role / profile or a Bedrock API key
- Bedrock model access to `global.anthropic.claude-opus-4-7` and `global.anthropic.claude-opus-4-6-v1` in `us-east-1`
- For the quality scorer: Bedrock access to `global.anthropic.claude-sonnet-4-6`
- `git` for cloning and version control
- Optional: Anthropic API key with credits to enable 1P direct-API tests (currently disabled by default)

## Installation

```bash
# Clone the repository
git clone https://github.com/whchoi98/opus4.6_vs_opus4.7.git
cd opus4.6_vs_opus4.7

# Install Python dependencies
pip install --user -r requirements.txt

# Create a local secrets file from the template
cp .env.local.example .env.local
chmod 600 .env.local

# Edit .env.local with your AWS credentials
# See the Configuration section for variable details

# Run the one-shot setup script (installs deps, verifies imports, runs tests)
bash scripts/setup.sh
```

## Usage

```bash
# Load credentials into the current shell
source .env.local && export $(cut -d= -f1 .env.local)

# Print the execution plan without making any API calls
python3 run.py --dry-run
# Expected output:
#   Plan: 69 cases × 5 runs = 345 calls
#   Estimated cost: ~$5.00
#   Estimated wall time: ~12–29 min

# Run a single test with one iteration as a smoke test (~$0.10)
python3 run.py --test 1 --runs 1

# Run the full benchmark suite (Test 5 and Test 12 deferred by default)
python3 run.py --test all --runs 5

# Run only specific tests (comma-separated)
python3 run.py --test 6,7,8 --runs 3

# Run a deferred test explicitly
python3 run.py --test 5 --runs 5

# Re-generate a Markdown report from an existing results directory
python3 run.py --report-only results/2026-04-18-0747

# Run the LLM-judge quality scorer on a specific prompt type
python3 score.py --prompt-label tools --runs 5
# Expected output:
#   Run 1/5 judging tools...
#     verdict=4.6_better  judge_cost=$0.0033
#   ...
#   Done — wrote results/scorer-2026-04-18-0807/scorer-report.md
```

## Configuration

Environment variables are loaded from `.env.local` (file permissions must be `600`). Never commit this file.

| Variable | Description | Default |
|---|---|---|
| `AWS_BEARER_TOKEN_BEDROCK` | Bedrock API key for bearer-token auth. Alternative to IAM credentials. | unset |
| `AWS_REGION` | AWS region for Bedrock calls. | `us-east-1` |
| `AWS_PROFILE` | Named AWS profile in `~/.aws/credentials`. Used if bearer token is unset. | unset |
| `AWS_ACCESS_KEY_ID` | AWS access key. Used if profile and bearer token are unset. | unset |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key. Paired with `AWS_ACCESS_KEY_ID`. | unset |
| `ANTHROPIC_API_KEY` | Anthropic direct API key. Required only when `--backend 1p` is enabled. | unset |

At least one of `AWS_BEARER_TOKEN_BEDROCK`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, or an attached EC2 instance role must resolve for the Bedrock backend to work.

## Project Structure

```
.
├── run.py                 # Benchmark CLI entry point
├── score.py               # Quality scorer CLI entry point
├── config.py              # Model IDs, pricing, endpoints, retry policy
├── stats.py               # CallResult aggregation (mean, stdev)
├── reporter.py            # JSON and Markdown report writers
├── clients/               # Backend API wrappers (invocation only)
│   ├── base.py            #   CallResult dataclass and response parser
│   ├── bedrock_runtime.py #   anthropic.AnthropicBedrock wrapper
│   ├── bedrock_mantle.py  #   Raw requests + SigV4 ('bedrock-mantle')
│   └── anthropic_1p.py    #   anthropic.Anthropic wrapper (off by default)
├── cases/                 # Benchmark test definitions (pure data)
│   ├── base.py            #   TestCase dataclass
│   ├── prompts.py         #   All prompts and tool schemas
│   └── ...                #   13 test modules (test_1 through test_13)
├── runner/                # Orchestration layer
│   ├── preflight.py       #   Auth environment validation
│   ├── dispatch.py        #   Test ID to case module mapping
│   └── execute.py         #   Retry loop and client selection
├── scorers/               # Quality evaluation
│   └── judge.py           #   Pairwise 4.7 vs 4.6 with A/B randomization
├── tests/                 # Pytest unit tests (62 tests)
├── docs/                  # Architecture, runbooks, test results
├── scripts/               # Setup and git hook installers
├── .claude/               # Claude Code integration (hooks, skills, commands)
└── results/               # Per-run output directories (gitignored)
```

## Testing

```bash
# Run the full pytest suite
python3 -m pytest tests/
# Expected: 62 passed

# Run a specific test file with verbose output
python3 -m pytest tests/test_stats.py -v

# Run the integration test suite (hooks, structure validation)
bash tests/run-all.sh

# Perform a dry-run of the benchmark to verify case registration
python3 run.py --dry-run --test all --runs 5
```

## Documentation

- [`docs/test-results.md`](docs/test-results.md) — Consolidated benchmark report across all 13 tests and the Quality Scorer. Each test is documented with Purpose, Method, Findings, and Implications (bilingual, ~1,400 lines).
- [`docs/architecture.md`](docs/architecture.md) — System architecture with layer-by-layer component map and design decisions (bilingual).
- [`docs/onboarding.md`](docs/onboarding.md) — 10-minute developer setup guide.
- [`docs/runbooks/run-benchmark.md`](docs/runbooks/run-benchmark.md) — Step-by-step full benchmark execution procedure.
- [`docs/runbooks/run-scorer.md`](docs/runbooks/run-scorer.md) — Quality scorer operation and interpretation guide.
- [`CHANGELOG.md`](CHANGELOG.md) — Version history following Keep a Changelog + Semantic Versioning (bilingual).

## Contributing

1. Fork the repository on GitHub
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes using the Conventional Commits format (`git commit -m "feat(scope): short description"`)
4. Push the branch to your fork (`git push origin feat/your-feature`)
5. Open a Pull Request with a clear description of the change, related issue numbers, and any benchmark run results

Commit message examples:

```text
feat(cases): add tool schema scaling benchmark
fix(mantle): separate auth paths per auth_method
docs(test-results): add Korean tokenization results
test(runner): verify retry behavior on 5xx responses
refactor(clients): extract parse_bedrock_response to base module
```

Run `python3 -m pytest tests/` before opening a PR. The pre-push hook enforces this automatically when `scripts/install-hooks.sh` has been run.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

- Maintainer: [@whchoi98](https://github.com/whchoi98)
- Issues and bug reports: [GitHub Issues](https://github.com/whchoi98/opus4.6_vs_opus4.7/issues)
- Email: whchoi98@gmail.com

---

# 한국어

## 개요

`opus4.6_vs_opus4.7`은 AWS Bedrock에서 Opus 4.7과 Opus 4.6을 비교 측정하는 Python 테스트 하네스(harness)입니다. 13개 각 테스트는 [`docs/test-results.md`](docs/test-results.md)에 **목적**, **테스트 방법**, **주요 발견**, **시사점** 네 섹션으로 정리되어 있습니다. 모든 케이스는 5회씩 실행되며, 결과는 내부 검토 또는 외부 공개 글에 쓸 수 있는 JSON과 Markdown 리포트로 기록됩니다.

본 하네스는 Bedrock Runtime(공식 `anthropic` SDK 경유)과 Bedrock Mantle(원시 SigV4 서명 경유)을 모두 지원하며, `iam_role`과 `bedrock_api_key` 비교가 실제로 다른 HTTP 요청을 생성하도록 인증 경로를 격리합니다.

## 주요 기능

- **13개 벤치마크 차원** — effort 레벨, 프롬프트 길이, 병렬 tool 사용, 다중 턴 스케일링(1~100턴), 스트리밍 TTFT, tool 스키마 스케일링, 언어/코드 토큰화, 엔드포인트 parity, 인증 방식 비교, 품질 판정.
- **이중 백엔드 지원** — 공식 SDK를 통한 Bedrock Runtime과 서비스명 `bedrock-mantle`로 직접 서명하는 HTTP + SigV4 기반 Bedrock Mantle.
- **인증 격리** — frozen IAM 자격증명과 Bedrock API 키를 별도 경로로 라우팅하여, auth_method 비교가 실제로 다른 HTTP 요청을 생성하도록 보장합니다.
- **LLM-judge 품질 스코어러** — Sonnet 4.6을 judge로 사용해 4.7과 4.6 응답을 pairwise 비교하며, A/B 포지션 랜덤화로 judge 편향을 완화합니다.
- **재현 가능한 리포트** — 실행별 raw JSON, 집계 통계(평균·표준편차), 사람이 읽을 수 있는 Markdown, 그리고 사후 디버깅용 per-call body 덤프를 함께 생성합니다.

## 핵심 발견 (Key Findings)

전체 테스트 매트릭스(matrix)에서 도출한 8가지 핵심 결론입니다. 테스트별 목적 / 테스트 방법 / 주요 발견 / 시사점 상세는 [`docs/test-results.md`](docs/test-results.md)를 참조하십시오.

1. **Effort는 비용 레버(lever)가 아닙니다.** `effort` 파라미터(parameter)는 출력 깊이(output depth)만 조절하고 입력 토큰은 건드리지 않습니다 (Test 1 — 4.7의 네 가지 variant 모두 32개 입력 토큰 소비, σ = 0).
2. **한국어는 동등하게 토큰화되며, 영어와 코드가 오버헤드(overhead)를 부담합니다.** 한국어 산문 +5%, Python 코드 +29%, 영어 기술 산문 +57% (Test 11).
3. **지연 시간(latency) 우위는 세션 길이에 비례해 커집니다.** 4.7은 턴 1에서 10% 빠르고, 턴 10에서 40% 빠르며, 턴 100에서도 25% 빠릅니다 (Test 6, 10).
4. **TTFT는 4.7의 가장 강력한 UX 레버입니다.** 스트리밍 첫 토큰 지연 시간이 프롬프트 길이에 불변으로 1.15초를 유지합니다. 4.6은 1.46초에서 1.59초로 증가 (Test 7).
5. **대규모 도구(tool) 메뉴에는 `tool_choice`가 필수입니다.** 20개 도구에서 4.7은 수동형 프롬프팅 시 도구 호출이 0이며, `tool_choice={"type": "any"}`로 해결되지만 병렬성이 2로 제한됩니다 (Test 8, 9).
6. **지연 시간은 턴 20에서 계단 함수(step function)를 그립니다.** 4.7 지연 시간은 턴 19까지 3.7~4.3초 대역에서 평탄하게 유지되다가, 단일 턴 증가로 +16%(4.99초) 도약합니다 (Test 13).
7. **이 SDK 구성에서 Bedrock 캐싱은 관측되지 않습니다.** 사용자 프롬프트·시스템 프롬프트 캐싱 테스트 모두에서 캐시 생성/읽기 토큰이 0으로 반환되었습니다 (Test 5, 12 — 보류).
8. **품질 스코어러는 방향성 면에서 유사하며, 장황성 아티팩트(verbosity artifact)가 엄격한 토큰 상한에서 4.6에 유리하게 작용합니다.** 위치 무작위화된 평가자(judge)가 비교의 60%에서 4.6을 선호했는데, 이는 4.7의 더 장황한 서론(preamble)이 `max_tokens=400`에서 절단된 영향이 있습니다 (Quality Scorer).

4회의 벤치마크 실행과 2회의 스코어러 실행을 통해 관측된 비용: **409회 호출에 $7.14** (Bedrock, us-east-1).

## 사전 요구 사항

- Python 3.9 이상
- Bedrock 접근 권한이 있는 AWS 자격증명 — IAM role / profile 또는 Bedrock API 키
- `us-east-1`에서 `global.anthropic.claude-opus-4-7`과 `global.anthropic.claude-opus-4-6-v1` 모델 접근 권한
- 품질 스코어러용 `global.anthropic.claude-sonnet-4-6` 모델 접근 권한
- Clone과 버전 관리를 위한 `git`
- 선택 사항: 1P direct-API 테스트(기본 비활성) 활성화를 위한 credit 있는 Anthropic API 키

## 설치 방법

```bash
# 저장소 clone
git clone https://github.com/whchoi98/opus4.6_vs_opus4.7.git
cd opus4.6_vs_opus4.7

# Python 의존성 설치
pip install --user -r requirements.txt

# 템플릿에서 로컬 시크릿 파일 생성
cp .env.local.example .env.local
chmod 600 .env.local

# .env.local을 열어 AWS 자격증명 입력
# 변수 상세는 아래 "환경 설정" 섹션 참고

# 원샷 셋업 스크립트 실행 (의존성 설치 + 임포트 확인 + 테스트 실행)
bash scripts/setup.sh
```

## 사용법

```bash
# 현재 셸에 자격증명 로드
source .env.local && export $(cut -d= -f1 .env.local)

# API 호출 없이 실행 계획만 출력
python3 run.py --dry-run
# 예상 출력:
#   Plan: 69 cases × 5 runs = 345 calls
#   Estimated cost: ~$5.00
#   Estimated wall time: ~12–29 min

# Smoke 용도로 1개 테스트 1회만 실행 (약 $0.10)
python3 run.py --test 1 --runs 1

# 전체 벤치마크 실행 (Test 5와 Test 12는 기본 제외)
python3 run.py --test all --runs 5

# 특정 테스트만 실행 (콤마로 구분)
python3 run.py --test 6,7,8 --runs 3

# 보류된 테스트를 명시적으로 실행
python3 run.py --test 5 --runs 5

# 기존 결과 디렉토리로부터 Markdown 리포트 재생성
python3 run.py --report-only results/2026-04-18-0747

# 특정 프롬프트 유형에 대해 LLM-judge 품질 스코어러 실행
python3 score.py --prompt-label tools --runs 5
# 예상 출력:
#   Run 1/5 judging tools...
#     verdict=4.6_better  judge_cost=$0.0033
#   ...
#   Done — wrote results/scorer-2026-04-18-0807/scorer-report.md
```

## 환경 설정

환경 변수는 `.env.local`에서 로드됩니다(파일 권한은 반드시 `600`). 이 파일은 절대 commit하지 마십시오.

| 변수명 | 설명 | 기본값 |
|---|---|---|
| `AWS_BEARER_TOKEN_BEDROCK` | Bearer 토큰 인증용 Bedrock API 키. IAM 자격증명의 대안. | 미설정 |
| `AWS_REGION` | Bedrock 호출에 사용할 AWS 리전. | `us-east-1` |
| `AWS_PROFILE` | `~/.aws/credentials`의 명명된 AWS 프로필. Bearer 토큰이 없을 때 사용. | 미설정 |
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키. Profile과 bearer 토큰이 없을 때 사용. | 미설정 |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 키. `AWS_ACCESS_KEY_ID`와 쌍으로 사용. | 미설정 |
| `ANTHROPIC_API_KEY` | Anthropic direct API 키. `--backend 1p` 활성화 시에만 필요. | 미설정 |

Bedrock 백엔드가 동작하려면 `AWS_BEARER_TOKEN_BEDROCK`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID` 중 하나 또는 EC2 인스턴스에 연결된 role이 반드시 해결되어야 합니다.

## 프로젝트 구조

```
.
├── run.py                 # 벤치마크 CLI 진입점
├── score.py               # 품질 스코어러 CLI 진입점
├── config.py              # 모델 ID, 가격, 엔드포인트, 재시도 정책
├── stats.py               # CallResult 집계 (평균, 표준편차)
├── reporter.py            # JSON 및 Markdown 리포트 작성
├── clients/               # 백엔드 API 래퍼 (호출만 담당)
│   ├── base.py            #   CallResult 데이터클래스와 응답 파서
│   ├── bedrock_runtime.py #   anthropic.AnthropicBedrock 래퍼
│   ├── bedrock_mantle.py  #   Raw requests + SigV4 ('bedrock-mantle')
│   └── anthropic_1p.py    #   anthropic.Anthropic 래퍼 (기본 비활성)
├── cases/                 # 벤치마크 테스트 정의 (순수 데이터)
│   ├── base.py            #   TestCase 데이터클래스
│   ├── prompts.py         #   모든 프롬프트와 tool 스키마
│   └── ...                #   13개 테스트 모듈 (test_1 ~ test_13)
├── runner/                # Orchestration 레이어
│   ├── preflight.py       #   인증 환경 검증
│   ├── dispatch.py        #   테스트 ID에서 case 모듈로 매핑
│   └── execute.py         #   재시도 루프와 클라이언트 선택
├── scorers/               # 품질 평가
│   └── judge.py           #   A/B 랜덤화 포함 4.7 vs 4.6 pairwise 비교
├── tests/                 # Pytest 유닛 테스트 (62개)
├── docs/                  # 아키텍처, runbook, 테스트 결과
├── scripts/               # 셋업과 git hook 설치 스크립트
├── .claude/               # Claude Code 연동 (hooks, skills, commands)
└── results/               # 실행별 결과 디렉토리 (gitignored)
```

## 테스트

```bash
# 전체 pytest 스위트 실행
python3 -m pytest tests/
# 예상: 62 passed

# 특정 테스트 파일만 verbose로 실행
python3 -m pytest tests/test_stats.py -v

# 통합 테스트 스위트 실행 (hook, 구조 검증)
bash tests/run-all.sh

# Case 등록이 정상인지 dry-run으로 확인
python3 run.py --dry-run --test all --runs 5
```

## 문서

- [`docs/test-results.md`](docs/test-results.md) — 13개 테스트와 Quality Scorer 전체 결과 통합 리포트. 각 테스트는 **목적 / 테스트 방법 / 주요 발견 / 시사점** 4개 섹션으로 정리되어 있습니다 (이중 언어, 약 1,400줄).
- [`docs/architecture.md`](docs/architecture.md) — 계층별 컴포넌트 맵(layer-by-layer component map)과 설계 결정이 담긴 시스템 아키텍처 (이중 언어).
- [`docs/onboarding.md`](docs/onboarding.md) — 10분 이내 개발자 셋업 가이드.
- [`docs/runbooks/run-benchmark.md`](docs/runbooks/run-benchmark.md) — 전체 벤치마크 실행 절차 단계별 안내.
- [`docs/runbooks/run-scorer.md`](docs/runbooks/run-scorer.md) — 품질 스코어러 운영 및 해석 가이드.
- [`CHANGELOG.md`](CHANGELOG.md) — Keep a Changelog + Semantic Versioning 규약을 따르는 버전 이력 (이중 언어).

## 기여 방법

1. GitHub에서 저장소를 Fork합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feat/your-feature`)
3. Conventional Commits 형식으로 변경사항을 커밋합니다 (`git commit -m "feat(scope): 짧은 설명"`)
4. 포크한 원격에 브랜치를 푸시합니다 (`git push origin feat/your-feature`)
5. 변경 설명, 관련 이슈 번호, 벤치마크 실행 결과를 포함한 Pull Request를 엽니다

커밋 메시지 예시:

```text
feat(cases): tool 스키마 스케일링 벤치마크 추가
fix(mantle): auth_method별로 인증 경로 분리
docs(test-results): 한국어 토큰화 결과 추가
test(runner): 5xx 응답에 대한 재시도 동작 검증
refactor(clients): parse_bedrock_response를 base 모듈로 추출
```

PR을 열기 전에 반드시 `python3 -m pytest tests/`를 실행해 주십시오. `scripts/install-hooks.sh`를 실행한 경우 pre-push hook이 이를 자동으로 강제합니다.

## 라이선스

본 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE)를 참조하십시오.

## 연락처

- 메인테이너: [@whchoi98](https://github.com/whchoi98)
- 이슈와 버그 리포트: [GitHub Issues](https://github.com/whchoi98/opus4.6_vs_opus4.7/issues)
- 이메일: whchoi98@gmail.com
