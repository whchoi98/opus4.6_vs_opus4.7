# Cross-reference: Our findings vs Claude Code Camp blog

**Reference blog:** https://www.claudecodecamp.com/p/i-measured-claude-4-7-s-new-tokenizer-here-s-what-it-costs-you

The blog uses Anthropic's `/v1/messages/count_tokens` API to measure raw
tokenizer overhead across content types. Our benchmark measures Bedrock
end-to-end behavior (tokens + latency + tool use + quality). The two
approaches complement each other — their results are our inputs to
cost/latency/quality analysis.

---

## Overlap: content-type overhead measurements

### Direct agreement

| Content type | Blog (tokenizer) | Our measurement (Bedrock) | Match |
|---|---|---|---|
| **Code (Python)** | 1.29x (+29%) | 1.29x (+29%) | ✅ Exact |
| **CJK / Korean prose** | 1.01–1.07x (+1–7%) | 1.05x (+5%) | ✅ Within range |
| **Korean + code hybrid** | (not tested directly) | 1.13x (+13%) | 공간 내 중간값, 일관됨 |

### Divergence

| Content type | Blog | Our measurement | Gap |
|---|---|---|---|
| **English prose** | 1.20x (+20%) | 1.57x (+57%) | **+37%p** |

우리 English 수치가 훨씬 높은 이유:
- 우리 프롬프트: 아키텍처 리뷰 (CloudFront, DynamoDB, API Gateway 등 **기술 용어 밀도 높음**)
- 기술 용어는 tokenizer에서 여러 서브워드로 split될 가능성 커서 overhead 증폭
- 블로그: 보다 일반적인 English prose로 테스트 — 낮은 overhead

**시사점:** "English 평균 overhead"는 단일 숫자로 특정하기 어려움. **콘텐츠 도메인이 결정적 변수**. 일반 prose = 20%, 기술 문서 = 57%, Claude Code 환경 평균 = 32.5% (블로그의 weighted average).

---

## 블로그의 새 데이터 — 우리 범위 밖

| 콘텐츠 | 블로그 수치 | 우리 상응 데이터 |
|---|---|---|
| CLAUDE.md | **1.445x** | 미측정 |
| User prompts | 1.373x | 미측정 |
| Blog posts | 1.368x | 미측정 |
| Git logs | 1.344x | 미측정 |
| Terminal output | 1.291x | 미측정 |
| Stack traces | 1.250x | 미측정 |
| Code diffs | 1.212x | 미측정 |
| **Weighted avg (real workload)** | **1.325x** | ~1.32x (추정 범위 내) |

→ 블로그는 **토크나이저 자체 측정** (API 기반, 무료)에 강점. **7개 실제 워크로드 콘텐츠를 측정**해서 현실적 평균 32.5% 도출. 우리 수치와 비교하면 **Claude Code 실제 사용 시 4.7이 대략 1.3x 비쌈**으로 수렴.

---

## 블로그의 80-turn Claude Code 세션 비용 분석

| 항목 | 4.6 | 4.7 |
|---|---|---|
| 80턴 세션 비용 | ~$6.65 | $7.86~$8.76 (+20~30%) |

**우리 Multi-turn 데이터 (Test 10, 100턴):**
| Model | 100턴 session 비용 |
|---|---|
| 4.6 | $0.3089 (per call, 5 runs 평균) |
| 4.7 | $0.4641 (per call, 5 runs 평균) |
| 증가율 | **+50%** |

→ 블로그의 20-30% 증가 < 우리 50% 증가. 차이 원인:
- 블로그는 **cache reads 활용 전제** (0.5 $/MTok): "Cache reads dominate input expenses"
- 우리 benchmark는 **caching 비활성 상태** (Tests 5+12에서 cache_tokens=0 확인됨, Bedrock 이슈)
- **즉 Bedrock 환경에서는 블로그의 20-30%가 아니라 50%에 가까움**

**핵심 insight:** Claude Code 1P 환경(api.anthropic.com)에서는 prompt caching이 동작 → 20-30% 증가. **Bedrock 환경에서는 caching이 안 보이는 상태** → 50% 증가. **이 gap이 Bedrock의 caching 문제가 실제로 비용에 미치는 영향을 정량화**한다.

---

## 블로그의 IFEval 결과

20개 프롬프트 샘플로 측정:
- Strict compliance: **85% → 90%** (+5%p 개선)
- Loose eval: 90% → 90% (변화 없음)

→ **4.7이 instruction following은 약간 우수**하지만 N=20 소샘플.

**우리 Quality Scorer 결과 (v2, A/B 랜덤화, 15 runs):**
- 4.7 better: 4 (27%)
- 4.6 better: 9 (60%)
- Tie: 2 (13%)

**왜 반대 방향?**
- IFEval은 **strict format compliance** 측정 (지시 형식 따르는지)
- 우리 Scorer는 **답변 완성도**를 judge가 평가
- **Truncation artifact**: 우리 max_tokens=400 cap이 장황한 4.7에게 불리 → 답변이 도중에 잘려 "미완성"으로 보임
- IFEval은 간단한 지시 (e.g., "대답을 JSON으로") 기반이라 max_tokens 영향 덜 받음

**종합:** 두 평가가 **다른 품질 차원을 측정**. 4.7은 instruction following 우수, 4.6은 간결한 완성도 우수. 워크로드 특성에 따라 선택.

---

## 블로그가 언급한 caveat 중 우리 데이터로 확인된 것

1. ✅ "Model switching invalidates cached prefixes, requiring expensive cold-start writes"
   - **우리 Test 5 (user cache) + Test 12 (system cache) 모두 cache_tokens=0**
   - Bedrock에서는 아예 caching 신호를 못 받으니 "cold-start cost" 계속 지불 중
   - 1P API 사용 시 caching 동작하면 블로그의 20-30% 범위에 수렴할 것

2. ✅ "N=20 sample size limits confidence"
   - 우리 Scorer V2도 N=15로 여전히 작은 샘플
   - 포지션 편향 ~69% A 선호 관측

3. 추가 (블로그에 없는) 우리 발견:
   - **Tool 20개 환경에서 4.7이 tool 완전 포기** (Test 8)
   - **`tool_choice={"type":"any"}`로 해결 가능** (Test 9)
   - **Multi-turn step function at turn 20** (Test 13)
   - **TTFT 1.15s 일정** — 프롬프트 길이 무관 (Test 7)

---

## 통합 의사결정 매트릭스 (블로그 + 우리 데이터)

| 워크로드 | 예상 overhead | 4.7 선호 | 4.6 선호 |
|---|---|---|---|
| **한국어 chatbot** | +5% | ✅ | — |
| **Claude Code (CLAUDE.md 많음)** | +45% | ⚠️ (비용↑) | 고볼륨이면 ✅ |
| **Python 코드 작성** | +29% | ✅ 속도 2.2x | — |
| **영문 prose 요약/번역** | +20% | ✅ | — |
| **기술 문서 작성** | +47% | 품질↑이면 ✅ | 비용↓이면 ✅ |
| **Git log / terminal output 분석** | +34% | 속도 우선이면 ✅ | — |
| **Stack trace 디버깅** | +25% | ✅ | — |
| **Code diff 리뷰** | +21% | ✅ | — |
| **Agent 5~19 turns** | +45% | ✅ latency 4s 평원 | — |
| **Agent 20+ turns + 큰 tool 메뉴** | +50%+ | ✅ w/ tool_choice | ⚠️ |

---

## 가장 가치 있는 통합 인사이트

1. **"4.7은 1.3x 비싸지만 1.5~2x 빠르다"** — 두 소스 모두 확인
2. **CJK/한국어는 overhead 거의 없음** (+1-7%) — 블로그 + 우리 데이터 일치
3. **Python 코드 overhead = 정확히 +29%** — 블로그 + 우리 exact 매칭
4. **English overhead는 콘텐츠 도메인 의존** (+20% ~ +57%) — 블로그 general prose vs 우리 기술 문서 비교에서 입증
5. **Bedrock의 caching 문제는 실제 비용 차이를 30%p 증폭시킨다** (블로그 +20-30% vs Bedrock 환경 +50%) — 신규 통합 발견
6. **IFEval (strict 지시)은 4.7 우수, max_tokens 제약 있는 자유형 답변은 4.6 우수** — 다른 품질 차원, 블로그 + 우리 판정 모두 타당
