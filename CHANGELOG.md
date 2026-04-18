# Changelog

[![English](https://img.shields.io/badge/language-English-blue)](#english)
[![한국어](https://img.shields.io/badge/language-한국어-red)](#한국어)

---

# English

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add Claude Code project scaffold including top-level and per-module `CLAUDE.md` files, settings, hooks, skills, commands, and agents
- Add bilingual `README.md` and `docs/architecture.md` with identical English and Korean sections
- Add runbooks for full benchmark execution and quality scorer operation
- Add `scripts/setup.sh` and `scripts/install-hooks.sh` for one-shot developer setup and git-hook installation
- Add TAP-style integration test suite under `tests/run-all.sh` covering hook existence, secret patterns, and project structure

## [0.4.0] - 2026-04-18

### Added

- Add Test 13 multi-turn knee-point benchmark covering 11, 13, 15, 17, and 19 turns to fill the resolution gap between Test 6 and Test 10
- Add results documentation for the turn-20 latency step function discovery
- Add results cross-reference table correlating Test 11 tokenizer measurements with public tokenizer data

### Changed

- Randomize judge A/B position in `scorers/judge.py` to mitigate systematic position bias; record `position_of_47` and `raw_verdict` fields per result

### Fixed

- Fix judge model identifier from `global.anthropic.claude-sonnet-4-6-v1` to `global.anthropic.claude-sonnet-4-6` after Bedrock returned `invalid model identifier`

## [0.3.0] - 2026-04-18

### Added

- Add Test 9 tool-forcing benchmark comparing passive prompt, imperative prompt, `tool_choice={"type": "any"}`, and `tool_choice={"type": "tool", "name": ...}` variants at 20-tool scale
- Add Test 10 multi-turn extreme stress benchmark covering 10, 20, 30, 50, and 100 turn conversations
- Add Test 11 language and code decomposition benchmark separating English prose, Korean prose, Python code, and Korean-plus-code hybrid
- Add Test 12 system prompt caching benchmark with `cache_control` markers on long system prompts
- Add LLM-judge quality scorer module (`scorers/judge.py`) and CLI entry point (`score.py`) for pairwise 4.7 vs 4.6 response comparison using Sonnet 4.6 as judge
- Add `tool_choice`, `messages_override`, `system_prompt`, `system_cached`, and `streaming` fields to `TestCase`

### Changed

- **BREAKING:** Separate authentication paths in `BedrockRuntimeClient` so `iam_role` and `bedrock_api_key` produce genuinely different HTTP requests; existing callers must ensure the correct auth method is selected per case
- **BREAKING:** Separate authentication paths in `BedrockMantleClient` following the same pattern; callers must choose between SigV4 with IAM credentials or Bearer token authentication
- Rename benchmark case directory from `tests/` to `cases/` to avoid collision with pytest unit tests

### Deprecated

- Deprecate Test 5 user prompt caching in the default `--test all` run because Bedrock does not surface `cache_creation_input_tokens` or `cache_read_input_tokens` in responses; the test remains runnable via explicit `--test 5`

### Fixed

- Fix Mantle client credential refresh so long-running processes do not fail after STS or IMDS token expiry (resolve cached-credentials issue flagged in code review)
- Fix Mantle client request body mismatch by sending `aws_req.body` (the signed body) rather than the original unsigned `data` string
- Fix Mantle client auth_method handling so bearer token and IAM paths produce different Authorization headers instead of silently sharing the boto3 credential chain
- Fix Runtime client auth_method handling using the same pattern as the Mantle client fix

## [0.2.0] - 2026-04-18

### Added

- Add Test 5 prompt caching benchmark with `cache_control={"type": "ephemeral"}` markers
- Add Test 6 multi-turn conversation benchmark covering 1, 3, 5, and 10 turn conversations
- Add Test 7 streaming TTFT benchmark using `messages.stream()` with first-token latency measurement
- Add Test 8 tool schema scaling benchmark covering 1, 5, and 20 tool schemas
- Add `cache_creation_tokens`, `cache_read_tokens`, and `ttft_s` fields to `CallResult` with cost calculation at 1.25x write rate and 0.10x read rate
- Add `invoke_streaming()` method to `BedrockRuntimeClient` for TTFT measurement
- Add results documentation for Tests 5–8
- Add results documentation for Tests 9–12

### Changed

- Extend run plan from 87 to 108 calls to accommodate new test cases and auth-method matrix

## [0.1.0] - 2026-04-18

### Added

- Add initial benchmark harness for Opus 4.7 vs 4.6 comparison on Bedrock
- Add Test 1 effort level vs token consumption benchmark across `low`, `medium`, `high`, and `max` variants
- Add Test 2 prompt length scaling benchmark comparing short and long prompts
- Add Test 3 parallel tool use benchmark
- Add Test 4 Bedrock Runtime vs Mantle endpoint parity benchmark with IAM vs Bedrock API key auth comparison
- Add `BedrockRuntimeClient` wrapper around `anthropic.AnthropicBedrock` with per-model API shape handling (`thinking.adaptive + output_config.effort` for 4.7, native mode for 4.6)
- Add `BedrockMantleClient` using raw `requests` with `botocore.auth.SigV4Auth` and service name `bedrock-mantle`
- Add `AnthropicOnePClient` for Anthropic direct API (disabled by default at runtime)
- Add `runner/` orchestration layer with preflight auth checks, case dispatch, retry loop with exponential backoff
- Add `stats.py` aggregation with mean and standard deviation per case
- Add `reporter.py` producing `raw.json`, `aggregated.json`, and Markdown report
- Add `run.py` CLI entry point with `--test`, `--runs`, `--backend`, `--dry-run`, and `--report-only` options
- Add `.env.local` secret file loading with 600 permissions requirement
- Add pytest suite of 43 initial unit tests covering client wrappers, case modules, stats aggregation, reporter writers, and runner dispatch
- Add initial design specification
- Add TDD-style implementation plan
- Add first-run results documentation

[Unreleased]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/whchoi98/opus-bedrock-benchmark/releases/tag/v0.1.0

---

# 한국어

이 프로젝트의 모든 주요 변경 사항은 이 파일에 기록됩니다.

이 문서는 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)를 기반으로 하며, [Semantic Versioning](https://semver.org/spec/v2.0.0.html)을 따릅니다.

## [Unreleased]

### Added

- Claude Code 프로젝트 스캐폴드 추가 — 최상위 및 모듈별 `CLAUDE.md`, settings, hooks, skills, commands, agents 포함
- 이중 언어 `README.md` 및 `docs/architecture.md` 추가 — 영어와 한국어 섹션이 동일 구조로 구성
- 전체 벤치마크 실행과 품질 스코어러 운영을 위한 runbook 추가
- `scripts/setup.sh` 및 `scripts/install-hooks.sh` 추가 — 개발자용 원샷 셋업과 git hook 설치
- `tests/run-all.sh` 하에 TAP 스타일 통합 테스트 스위트 추가 — hook 존재성, 시크릿 패턴, 프로젝트 구조 검증

## [0.4.0] - 2026-04-18

### Added

- Test 13 다중 턴 knee-point 벤치마크 추가 — 11, 13, 15, 17, 19턴을 커버하여 Test 6과 Test 10 사이 해상도 공백 보완
- 턴 20에서의 지연 시간 계단 함수 발견을 기록한 결과 문서 추가
- Test 11 토큰화 측정값과 공개 토큰화 데이터를 상호 참조하는 결과 테이블 추가

### Changed

- `scorers/judge.py`에서 judge A/B 포지션 랜덤화 — 체계적 포지션 편향 완화, 결과별 `position_of_47`와 `raw_verdict` 필드 기록

### Fixed

- Judge 모델 식별자를 `global.anthropic.claude-sonnet-4-6-v1`에서 `global.anthropic.claude-sonnet-4-6`으로 수정 — Bedrock이 `invalid model identifier` 에러 반환

## [0.3.0] - 2026-04-18

### Added

- Test 9 tool-forcing 벤치마크 추가 — 20개 tool 환경에서 passive 프롬프트, imperative 프롬프트, `tool_choice={"type": "any"}`, `tool_choice={"type": "tool", "name": ...}` 4종 variant 비교
- Test 10 다중 턴 극한 스트레스 벤치마크 추가 — 10, 20, 30, 50, 100턴 대화 커버
- Test 11 언어 및 코드 분해 벤치마크 추가 — 영어 prose, 한국어 prose, Python 코드, 한국어+코드 하이브리드 분리 측정
- Test 12 시스템 프롬프트 캐싱 벤치마크 추가 — 긴 시스템 프롬프트에 `cache_control` 마커 적용
- LLM-judge 품질 스코어러 모듈(`scorers/judge.py`) 및 CLI 진입점(`score.py`) 추가 — Sonnet 4.6을 judge로 4.7과 4.6 응답 pairwise 비교
- `TestCase`에 `tool_choice`, `messages_override`, `system_prompt`, `system_cached`, `streaming` 필드 추가

### Changed

- **BREAKING:** `BedrockRuntimeClient` 인증 경로 분리 — `iam_role`과 `bedrock_api_key`가 실제로 다른 HTTP 요청을 생성하도록 보장, 기존 호출자는 case별로 올바른 auth method 선택 필요
- **BREAKING:** `BedrockMantleClient` 인증 경로 분리 — 동일 패턴 적용, 호출자는 IAM 자격증명을 사용한 SigV4 또는 Bearer 토큰 인증 중 선택 필요
- 벤치마크 case 디렉토리를 `tests/`에서 `cases/`로 개명 — pytest 유닛 테스트와의 충돌 방지

### Deprecated

- 기본 `--test all` 실행에서 Test 5 사용자 프롬프트 캐싱 deprecate — Bedrock이 응답에서 `cache_creation_input_tokens`와 `cache_read_input_tokens`를 제공하지 않음, 명시적 `--test 5`로는 계속 실행 가능

### Fixed

- Mantle 클라이언트 자격증명 refresh 수정 — 장기 실행 프로세스가 STS 또는 IMDS 토큰 만료 후 실패하지 않도록 보장 (코드 리뷰 지적 사항 해결)
- Mantle 클라이언트 요청 body 불일치 수정 — 원본 `data` 문자열 대신 서명된 `aws_req.body` 전송
- Mantle 클라이언트 auth_method 처리 수정 — bearer 토큰과 IAM 경로가 boto3 credential chain을 암묵 공유하지 않고 서로 다른 Authorization 헤더 생성
- Runtime 클라이언트 auth_method 처리 수정 — Mantle 수정과 동일 패턴 적용

## [0.2.0] - 2026-04-18

### Added

- Test 5 프롬프트 캐싱 벤치마크 추가 — `cache_control={"type": "ephemeral"}` 마커 적용
- Test 6 다중 턴 대화 벤치마크 추가 — 1, 3, 5, 10턴 대화 커버
- Test 7 스트리밍 TTFT 벤치마크 추가 — `messages.stream()`으로 첫 토큰 latency 측정
- Test 8 tool 스키마 스케일링 벤치마크 추가 — 1, 5, 20개 tool 스키마 커버
- `CallResult`에 `cache_creation_tokens`, `cache_read_tokens`, `ttft_s` 필드 추가 — write 1.25배, read 0.10배 비용 계산 포함
- `BedrockRuntimeClient.invoke_streaming()` 메서드 추가 — TTFT 측정용
- Tests 5~8 결과 문서 추가
- Tests 9~12 결과 문서 추가

### Changed

- 실행 계획 호출 수를 87개에서 108개로 확장 — 신규 테스트 케이스와 auth-method 매트릭스 수용

## [0.1.0] - 2026-04-18

### Added

- Opus 4.7 대 4.6 비교를 위한 초기 Bedrock 벤치마크 하네스 추가
- Test 1 effort 레벨 vs 토큰 소비 벤치마크 추가 — `low`, `medium`, `high`, `max` variant 커버
- Test 2 프롬프트 길이 스케일링 벤치마크 추가 — 짧은 프롬프트와 긴 프롬프트 비교
- Test 3 병렬 tool use 벤치마크 추가
- Test 4 Bedrock Runtime vs Mantle 엔드포인트 parity 벤치마크 추가 — IAM vs Bedrock API key 인증 비교 포함
- `anthropic.AnthropicBedrock`을 감싸는 `BedrockRuntimeClient` 추가 — 모델별 API shape 처리 (4.7은 `thinking.adaptive + output_config.effort`, 4.6은 native 모드)
- `BedrockMantleClient` 추가 — 서비스명 `bedrock-mantle`과 함께 `botocore.auth.SigV4Auth`를 사용한 raw `requests` 경로
- Anthropic direct API용 `AnthropicOnePClient` 추가 (런타임에서 기본 비활성)
- `runner/` orchestration 레이어 추가 — preflight 인증 체크, case dispatch, 지수 백오프 재시도 루프
- `stats.py` 집계 모듈 추가 — case별 평균과 표준편차
- `reporter.py` 추가 — `raw.json`, `aggregated.json`, Markdown 리포트 생성
- `run.py` CLI 진입점 추가 — `--test`, `--runs`, `--backend`, `--dry-run`, `--report-only` 옵션 지원
- `.env.local` 시크릿 파일 로딩 추가 — 600 권한 요구
- 초기 43개 pytest 유닛 테스트 스위트 추가 — 클라이언트 래퍼, case 모듈, stats 집계, reporter writer, runner dispatch 커버
- 초기 설계 명세 추가
- TDD 방식 구현 계획 추가
- 첫 실행 결과 문서 추가

[Unreleased]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/whchoi98/opus-bedrock-benchmark/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/whchoi98/opus-bedrock-benchmark/releases/tag/v0.1.0
