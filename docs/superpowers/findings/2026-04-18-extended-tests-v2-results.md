# Extended Tests V2 — Tests 9-12 Results (2026-04-18 07:47 UTC)

Third benchmark run adding Tests 9-12 (tool forcing, multi-turn extreme,
language/code decomposition, system prompt caching). **140/140 calls, $3.75,
867s wall time.**

Results dir: `results/2026-04-18-0747/`

Cumulative project cost: ~$6.22 across three runs (Tests 1-12).

---

## Test 9 — Tool Forcing ⭐⭐⭐ (breakthrough finding)

4 variants × 2 models = 8 cases. All using the same 20-tool menu from Test 8.

| Variant | Method | 4.6 tool_calls | 4.7 tool_calls | 4.7 latency |
|---|---|---|---|---|
| **passive** | Normal prompt (Test 8 replication) | 5.0 | **0.0** | 3.88s |
| **imperative** | "You must use the tools..." | 4.0 | **1.2** (3 of 5 runs = 0) | 4.22s |
| **choice-any** | `tool_choice={"type": "any"}` | 2.0 | **2.0** ✅ | 2.38s |
| **choice-specific** | `tool_choice={"type": "tool", "name": ...}` | 2.0 | **2.0** ✅ | 2.32s |

### 🎯 핵심 발견: `tool_choice` API 파라미터가 해결책

Test 8에서 발견한 "4.7이 20개 tool에서 tool을 포기" 문제는:

1. **프롬프트로 해결 불가** — `"You MUST use tools"` 명시해도 5번 중 3번은 tool 안 씀 (60% 실패).
2. **`tool_choice={"type": "any"}`로 완벽 해결** — 5 runs 모두 2 tool_calls 일관 실행.
3. **`tool_choice={"type": "tool", "name": "X"}`도 동일 효과** — 특정 tool 강제 가능.

### ⚠️ 하지만 tool_choice의 숨은 비용

`tool_choice` 설정 시 **병렬 tool_use 블록 개수가 5→2로 감소**:

- Passive: 4.6 emits 5 parallel tool_uses, 4.7 emits 0
- With tool_choice: **둘 다 2만** emit

이는 tool_choice가 "어떤 tool이든 써라"고 강제하면서 모델이 보수적으로 최소 tool만 호출하게 만드는 현상. 즉 **병렬성 × 보장성 트레이드오프**:
- 최대 병렬성 원하면 → passive prompt + 4.6 (5 parallel calls)
- 확실한 tool 사용 원하면 → tool_choice + 4.7 가능 (2 calls)

### 실무 결론

- **4.7 + 대규모 tool 환경(10+)은 tool_choice 필수** — 없으면 tool 완전 미사용 리스크.
- **Agent 프레임워크(LangChain, Claude Code, MCP 등)는 반드시 tool_choice를 에이전트 루프에 integrate 해야 함.**
- Imperative prompting은 불안정한 보조 수단일 뿐.

---

## Test 10 — Multi-turn Extreme Stress (10/20/30/50/100 turns)

| Turns | 4.6 input | 4.7 input | overhead | 4.6 latency | 4.7 latency | 4.7 advantage |
|---|---|---|---|---|---|---|
| 10 | 999 | 1447 | +45% | 6.73s | 3.95s | 41% faster |
| 20 | 2117 | 3181 | +50% | 6.64s | 4.99s | 25% faster |
| 30 | 3239 | 4915 | +52% | 6.62s | 5.04s | 24% faster |
| 50 | 5489 | 8393 | +53% | 8.14s | 5.24s | 36% faster |
| 100 | 11095 | 17063 | +54% | 7.69s | 5.75s | 25% faster |

### Test 6 결론 수정

Test 6에서 "4.7 latency는 턴 수에 관계없이 ~4.05s 일정"이라고 결론 내렸는데, **부분적으로 틀렸습니다**:

- **10턴까지는 4.05s 유지** — Test 6과 일치
- **20턴부터 서서히 증가** — 4.99s (+25%), 5.04s, 5.24s, 5.75s
- **100턴에서도 5.75s로 유지** — 4.6의 7.69s 대비 여전히 25% 빠름

### Overhead 증가 패턴

- 10턴: +45%
- 100턴: +54%

대화가 길어질수록 **overhead가 약간 증가** (+9%p). 이는 4.7 토크나이저가 누적 컨텍스트에 대해 약간 더 많은 토큰을 써서 나타나는 현상.

### 실무 결론

- **50턴 이상의 장기 에이전트 세션에서 4.7은 여전히 빠르지만** 비용은 4.6 대비 **~54% 비싸짐**.
- 100턴 시점의 call당 비용: 4.6 = $0.0618 vs 4.7 = $0.0928 (50% 차이).
- 장기 세션 운영자는 **주기적 summary compaction**으로 컨텍스트를 줄이는 게 더 경제적일 수 있음.

---

## Test 11 — Language/Code Decomposition ⭐⭐⭐ (큰 발견)

4 variants × 2 models. 동일 분량 (~350 "단위"), 컨텐츠 유형만 다름.

| Variant | 4.6 input | 4.7 input | **Overhead %** | 4.6 latency | 4.7 latency |
|---|---|---|---|---|---|
| English prose | 389 | 610 | **+57%** | 11.26s | 5.62s |
| **Korean prose** | 962 | 1010 | **+5%** ⭐ | 8.81s | 5.12s |
| Code (Python) | 1260 | 1622 | **+29%** | 10.49s | 4.83s |
| Korean + code hybrid | 872 | 988 | **+13%** | 8.34s | 4.54s |

### 🎯 핵심 발견: Korean은 4.7 overhead가 거의 없다

**한국어 텍스트는 두 모델이 거의 동일하게 토큰화**:
- 4.6 → 962 tokens
- 4.7 → 1010 tokens
- Overhead: **+5%만** (블로그 "+45%" 주장과 거리 먼 수치)

원인 추정:
- 4.6과 4.7의 tokenizer 차이는 **영문·코드 처리 로직에 집중**
- 한글(CJK) 문자는 두 모델 모두 유사한 UTF-8 기반 서브워드 처리
- 영문은 4.7이 더 많이 "쪼개서" 토큰 수 증가 (+57%)

### 운영 함의

**한국 Claude 사용자 비용 예상 공식:**

프롬프트 토큰 비중 × overhead 가중평균

| 워크로드 | 한국어 비중 | 코드 비중 | 영문 비중 | 예상 overhead |
|---|---|---|---|---|
| 한국 기업 AWS 컨설팅 에이전트 | 70% | 20% | 10% | ~+14% |
| Claude Code 한국 개발자 | 20% | 70% | 10% | ~+29% |
| 한국 고객 지원 챗봇 | 90% | 5% | 5% | ~+8% |
| 영문 기술 문서 생성 | 5% | 10% | 85% | ~+51% |

→ **Korean-native 워크로드는 4.7 전환이 거의 무료** (5% 증가).
→ **영문 heavy는 재검토 필요** (50%+ 증가).

### 흥미로운 secondary 발견: 4.7이 Korean에서 훨씬 빠름

| Variant | 4.7 latency | 4.6 latency | 4.7 advantage |
|---|---|---|---|
| English | 5.62s | 11.26s | **2.0x 빠름** |
| Korean | 5.12s | 8.81s | 1.7x |
| Code | 4.83s | 10.49s | **2.2x 빠름** |
| Korean+code | 4.54s | 8.34s | 1.8x |

→ **4.7은 모든 언어에서 2배 가까이 빠름**. Test 6·Test 10 latency 우위의 언어 독립성 확인.

---

## Test 12 — System Prompt Caching ❌ (Test 5와 동일한 결과)

| Model | cache_create | cache_read | Input | Latency |
|---|---|---|---|---|
| 4.7 | **0** | **0** | 1404 | 5.74s |
| 4.6 | **0** | **0** | 915 | 11.20s |

**결론:** System prompt caching도 Bedrock에서 **동일하게 작동 안 함**:
- `cache_control={"type": "ephemeral"}`를 system 프롬프트 블록에 붙여도
- 5 runs 전부에서 `cache_creation_input_tokens=0, cache_read_input_tokens=0`

**Test 5 (user prompt caching)과 Test 12 (system prompt caching) 모두 실패 확정.**

Bedrock의 prompt caching은:
- API-level로는 `cache_control` 마커를 accept하지만
- Response usage에 caching fields를 **아예 내놓지 않음**
- 또는 silent하게 무시함

**Action:** Bedrock docs 업데이트를 기다리거나 AWS Support 문의 필요. 지금 당장은 "Bedrock 환경에서 prompt caching 측정 불가" 확정 상태.

---

## 종합: Tests 9-12가 추가한 인사이트

| 발견 | 실무 임팩트 |
|---|---|
| **tool_choice API로 4.7 tool 사용 강제 가능** (Test 9) | MCP·Claude Code·agent framework에 필수. Prompting만으로는 불안정 |
| **tool_choice는 병렬성 5→2로 감소** (Test 9) | 최대 병렬화 vs 신뢰성 트레이드오프 설계 필요 |
| **4.7 latency는 턴 수 따라 느려지지만 여전히 4.6 대비 빠름** (Test 10) | 100턴까지 4.7 유리 |
| **Overhead는 100턴에서 +54%로 증가** (Test 10) | 장기 세션은 summary compaction 고려 |
| **Korean prose는 4.7 overhead +5%뿐** (Test 11) ⭐ | 한국 사용자 비용 충격 크게 완화 |
| **영문 +57%가 블로그 주장 (+45%)보다 높음** (Test 11) | 영문 heavy는 4.6 유지 고려 |
| **Code +29%** (Test 11) | Claude Code 환경에서 중간 수준 증가 |
| **Bedrock prompt caching 완전 불가** (Test 5+12) | AWS Support 티켓 필요 |

---

## 결정 매트릭스 (최종 업데이트)

| 워크로드 | 4.7 | 4.6 | 근거 |
|---|---|---|---|
| 한국어 고객지원 챗봇 | ✅ | — | Overhead +5%, 속도 1.7x (Test 11) |
| 한국어 + 코드 agent | ✅ | — | Overhead +13%, 속도 1.8x (Test 11) |
| Claude Code (코드 heavy) | ✅ | — | Overhead +29%, 속도 2.2x (Test 11) |
| **대형 toolset agent (20+ tools)** | ✅ w/ tool_choice | ⚠️ | tool_choice 필수 (Test 9) |
| **대형 toolset agent (tool_choice 미지원 환경)** | ❌ | ✅ | 4.7 tool 미사용 (Test 9) |
| 장기 세션 agent (50+ turns) | ✅ | — | 속도 25%+ 우위 (Test 10) |
| 영문 RAG / 문서 생성 (배치) | — | ✅ | +57% 비용 (Test 11) |
| Streaming chatbot | ✅ | — | TTFT 21-28% (Test 7) |
| Reasoning-heavy | 동일 | 동일 | Cost parity (Test 1) |

---

## 아직 남은 의문 (후속 조사 대상)

1. **품질 평가 (Quality scorer)** — Test 9 `choice-any`에서 4.7과 4.6이 같은 2 tool을 부르지만 **실제 응답 품질은 누가 나은가**? `score.py` 인프라 준비됨, 실행만 남음.

2. **tool_choice와 parallel count** — `tool_choice={"type": "any"}`가 왜 병렬 tool_use를 5→2로 줄이나? 모델 내부 정책? API-level 제약?

3. **Bedrock cache silent drop** — 왜 Bedrock은 `cache_control` 마커를 accept하면서도 response에 cache 필드를 내놓지 않는가? AWS Support 티켓 가치 있음.

4. **10턴 vs 20턴 사이 knee** — Test 6(10턴 유지)과 Test 10(20턴부터 증가) 사이에서 **4.7 latency가 언제 꺾이나**? 11~19턴 해상도 탐색 가치 있음.

5. **100턴 이상 극한** — 500턴/1000턴에서도 4.7 vs 4.6 latency 격차 유지되나? 실제 long-context limit 탐색.
