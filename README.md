# opus-bedrock-benchmark

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-62%20passing-brightgreen)](#testing)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](#)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](#prerequisites)
[![English](https://img.shields.io/badge/language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/language-한국어-red)](#한국어)

A reproducible Python benchmark harness for comparing Claude Opus 4.7 vs Opus 4.6 on AWS Bedrock across 13 behavioral dimensions.

AWS Bedrock에서 Claude Opus 4.7과 4.6을 13개 행동 차원으로 비교 측정하는 재현 가능한 Python 벤치마크 하네스.

---

# English

## Overview

`opus-bedrock-benchmark` is a Python test harness that measures Claude Opus 4.7 versus Opus 4.6 on AWS Bedrock. It reproduces publicly reported findings about 4.7's tokenizer overhead and extends them with multi-turn scaling, tool-forcing, streaming TTFT, and LLM-judge quality comparison. Each test runs 5 times and produces JSON and Markdown reports suitable for internal reviews or public writeups.

The harness supports both Bedrock Runtime (via the `anthropic` SDK) and Bedrock Mantle (via raw SigV4 signing), with isolated authentication paths so `iam_role` and `bedrock_api_key` comparisons are meaningful.

## Features

- **13 benchmark dimensions** — effort level, prompt length, parallel tool use, multi-turn scaling (1 to 100 turns), streaming TTFT, tool schema scaling, language/code tokenization, endpoint parity, auth-method comparison, and quality judgement.
- **Dual-backend support** — Bedrock Runtime through the official SDK and Bedrock Mantle through hand-rolled HTTP + SigV4 with service name `bedrock-mantle`.
- **Auth isolation** — frozen IAM credentials and Bedrock API keys are routed through separate paths so auth-method comparisons produce genuinely different HTTP requests.
- **LLM-judge quality scorer** — pairwise 4.7 vs 4.6 comparison using Sonnet 4.6 as judge, with A/B position randomization to mitigate judge bias.
- **Reproducible reports** — per-run raw JSON, aggregated statistics (mean and standard deviation), and human-readable Markdown with per-call body dumps for forensic debugging.

## Prerequisites

- Python 3.9 or later
- AWS credentials with Bedrock access — either an IAM role / profile or a Bedrock API key
- Bedrock model access to `global.anthropic.claude-opus-4-7` and `global.anthropic.claude-opus-4-6-v1` in `us-east-1`
- `git` for cloning and version control
- Optional: Anthropic API key with credits if you want to enable 1P direct-API tests

## Installation

```bash
# Clone the repository
git clone https://github.com/whchoi98/opus-bedrock-benchmark.git
cd opus-bedrock-benchmark

# Install Python dependencies
pip install --user -r requirements.txt

# Create a local secrets file from the template
cp .env.local.example .env.local
chmod 600 .env.local

# Edit .env.local with your AWS credentials
# See the Configuration section below for variable details

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

# Run the full benchmark suite
python3 run.py --test all --runs 5

# Run only specific tests (comma-separated)
python3 run.py --test 6,7,8 --runs 3

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
├── docs/                  # Architecture, runbooks, findings
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
docs(findings): add Korean tokenization results
test(runner): verify retry behavior on 5xx responses
refactor(clients): extract parse_bedrock_response to base module
```

Run `python3 -m pytest tests/` before opening a PR. The pre-push hook enforces this automatically when `scripts/install-hooks.sh` has been run.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE) for details.

## Contact

- Maintainer: [@whchoi98](https://github.com/whchoi98)
- Issues and bug reports: [GitHub Issues](https://github.com/whchoi98/opus-bedrock-benchmark/issues)
- Email: whchoi98@gmail.com

---

# 한국어

## 개요

`opus-bedrock-benchmark`는 AWS Bedrock에서 Claude Opus 4.7과 Opus 4.6을 비교 측정하는 Python 테스트 하네스입니다. 4.7의 토크나이저 overhead에 대한 공개 주장을 재현하고, 이를 다중 턴 스케일링·tool-forcing·스트리밍 TTFT·LLM-judge 품질 비교로 확장합니다. 각 테스트는 5회 실행되며 내부 검토 또는 공개 글에 사용할 수 있는 JSON과 Markdown 리포트를 생성합니다.

본 하네스는 Bedrock Runtime(공식 `anthropic` SDK 경유)과 Bedrock Mantle(raw SigV4 서명 경유)을 모두 지원하며, `iam_role`과 `bedrock_api_key`가 서로 다른 HTTP 요청을 실제로 발행하도록 인증 경로를 격리합니다.

## 주요 기능

- **13개 벤치마크 차원** — effort 레벨, 프롬프트 길이, 병렬 tool 사용, 다중 턴 스케일링(1~100턴), 스트리밍 TTFT, tool 스키마 스케일링, 언어/코드 토큰화, 엔드포인트 parity, 인증 방식 비교, 품질 판정.
- **이중 백엔드 지원** — 공식 SDK를 통한 Bedrock Runtime과 서비스명 `bedrock-mantle`로 직접 서명하는 HTTP + SigV4 기반 Bedrock Mantle.
- **인증 격리** — frozen IAM 자격증명과 Bedrock API 키를 별도 경로로 라우팅하여, auth_method 비교가 실제로 다른 HTTP 요청을 생성하도록 보장합니다.
- **LLM-judge 품질 스코어러** — Sonnet 4.6을 judge로 사용하여 4.7과 4.6 응답을 pairwise 비교하며, A/B 포지션 랜덤화로 judge 편향을 완화합니다.
- **재현 가능한 리포트** — 실행별 raw JSON, 집계 통계(평균·표준편차), 사람이 읽을 수 있는 Markdown, 그리고 사후 디버깅용 per-call body 덤프를 함께 생성합니다.

## 사전 요구 사항

- Python 3.9 이상
- Bedrock 접근 권한이 있는 AWS 자격증명 — IAM role / profile 또는 Bedrock API 키
- `us-east-1`에서 `global.anthropic.claude-opus-4-7`과 `global.anthropic.claude-opus-4-6-v1` 모델 접근 권한
- Clone과 버전 관리를 위한 `git`
- 선택 사항: 1P direct-API 테스트를 활성화하려면 credit이 있는 Anthropic API 키

## 설치 방법

```bash
# 저장소 clone
git clone https://github.com/whchoi98/opus-bedrock-benchmark.git
cd opus-bedrock-benchmark

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

# Smoke 용도로 1개 테스트 1회만 실행 (~$0.10)
python3 run.py --test 1 --runs 1

# 전체 벤치마크 실행
python3 run.py --test all --runs 5

# 특정 테스트만 실행 (콤마로 구분)
python3 run.py --test 6,7,8 --runs 3

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

환경 변수는 `.env.local`에서 로드됩니다 (파일 권한은 반드시 `600`). 이 파일은 절대 commit하지 마십시오.

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
├── docs/                  # 아키텍처, runbook, findings
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
docs(findings): 한국어 토큰화 결과 추가
test(runner): 5xx 응답에 대한 재시도 동작 검증
refactor(clients): parse_bedrock_response를 base 모듈로 추출
```

PR을 열기 전에 반드시 `python3 -m pytest tests/`를 실행해 주십시오. `scripts/install-hooks.sh`를 실행한 경우 pre-push hook이 이를 자동으로 강제합니다.

## 라이선스

본 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE)를 참조하십시오.

## 연락처

- 메인테이너: [@whchoi98](https://github.com/whchoi98)
- 이슈와 버그 리포트: [GitHub Issues](https://github.com/whchoi98/opus-bedrock-benchmark/issues)
- 이메일: whchoi98@gmail.com
