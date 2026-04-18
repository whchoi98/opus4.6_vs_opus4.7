"""All prompts and tool schemas — single source of truth."""

# Test 1: effort-level benchmark prompt
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

# Test 3: parallel tool-use prompt
TOOL_USE_PROMPT = "Look up pricing and limits for Bedrock in us-east-1 and eu-west-1."

# Tool schemas for Test 3
# --- Test 11 prompts: language/code decomposition ---

# Variant A: Pure English prose (~350 words). Technical architecture review.
DECOMP_ENGLISH_PROMPT = """Please review the following multi-region AWS architecture for a real-time customer support platform. The workload processes inbound customer inquiries through a combination of streaming pipelines and synchronous APIs, with specific reliability requirements. The primary region is us-east-1 and the disaster-recovery standby is us-west-2 in active-passive mode. Inbound traffic arrives via a global CloudFront distribution with origin failover, terminating at a regional Application Load Balancer in each region. Requests are routed to an ECS Fargate cluster running Python services behind service discovery. Stateful session data is kept in DynamoDB global tables with streams that fan out to SNS topics consumed by Lambda functions for audit logging and downstream analytics into an S3 data lake. Authentication uses Amazon Cognito user pools federated to the company's corporate identity provider, and authorization decisions are cached in Amazon ElastiCache for Redis at the service mesh edge. Observability is provided by CloudWatch Application Signals, X-Ray distributed tracing across all synchronous hops, and a custom Managed Prometheus deployment backing Grafana dashboards for business-level metrics. The team has noticed elevated tail latencies during peak hours, occasional cold starts when new ECS tasks are launched, and a recurring issue where session tokens appear to be validated twice on some paths. Please identify the three highest-risk issues in order of severity, propose one concrete change per risk with specific AWS service adjustments, and estimate the monthly cost impact of each proposed change. Consider applicable AWS Well-Architected pillars and note any assumptions you are making about traffic patterns, team size, or acceptable tradeoffs between latency and cost. The goal is a change set that can land within a two-week sprint without introducing new SaaS vendor dependencies."""

# Variant B: Pure Korean prose (~350 어절). Same technical topic in Korean.
DECOMP_KOREAN_PROMPT = """다음 AWS 기반 멀티 리전 실시간 고객 지원 플랫폼 아키텍처를 검토하고 주요 리스크와 개선 방안을 제시해 주세요. 대상 워크로드는 고객 문의를 스트리밍 파이프라인과 동기 API 조합으로 처리하며, 명확한 안정성 요구 사항이 있습니다. 기본 리전은 us-east-1이고 재해 복구용 웜 스탠바이는 us-west-2에 액티브 패시브 모드로 구성되어 있습니다. 인바운드 트래픽은 글로벌 CloudFront 배포를 통해 원본 장애 조치와 함께 도착하며 각 리전의 Application Load Balancer에서 종료됩니다. 요청은 서비스 디스커버리를 사용하는 ECS Fargate 클러스터의 파이썬 서비스로 라우팅됩니다. 상태가 있는 세션 데이터는 DynamoDB 글로벌 테이블에 저장되며 스트림은 SNS 토픽으로 팬 아웃되고 감사 로깅과 S3 데이터 레이크로의 다운스트림 분석을 담당하는 람다 함수가 이를 소비합니다. 인증은 Amazon Cognito 사용자 풀을 통해 이루어지고 회사 기업 아이덴티티 공급자와 연동되며, 권한 결정은 서비스 메시 엣지에서 Amazon ElastiCache for Redis에 캐싱됩니다. 관측성은 CloudWatch Application Signals, 모든 동기 홉에 걸친 X-Ray 분산 추적, 그리고 비즈니스 레벨 지표를 위한 Grafana 대시보드를 뒷받침하는 맞춤형 Managed Prometheus 배포로 제공됩니다. 팀에서 피크 시간대의 높은 꼬리 지연, 새 ECS 태스크가 시작될 때 발생하는 콜드 스타트, 그리고 일부 경로에서 세션 토큰이 두 번 검증되는 반복 문제를 관찰했습니다. 심각도 순으로 가장 위험한 세 가지 이슈를 식별하고 각 리스크에 대해 구체적인 AWS 서비스 조정과 함께 변경 제안 하나를 제시하고 제안된 변경의 월간 비용 영향을 추정해 주세요. 해당되는 AWS Well-Architected 기둥을 고려하고 트래픽 패턴, 팀 규모, 지연과 비용 사이의 허용 가능한 절충점에 대해 가정하는 모든 내용을 명시해 주세요. 목표는 새로운 SaaS 벤더 종속성을 도입하지 않고 2주 스프린트 내에 배포 가능한 변경 세트입니다."""

# Variant C: Pure code (~350 LOC equivalent Python — real-world async processor).
DECOMP_CODE_PROMPT = '''Please review the following Python code for quality issues, bugs, and production concerns.

```python
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    queue_url: str
    max_in_flight: int = 10
    visibility_timeout: int = 30
    batch_size: int = 10
    long_poll_seconds: int = 20
    retry_max_attempts: int = 3
    retry_backoff_base: float = 2.0
    shutdown_grace_seconds: int = 60
    observability_interval: int = 30


@dataclass
class WorkerStats:
    messages_received: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    messages_permanent_failures: int = 0
    last_error: Optional[str] = None
    started_at: float = field(default_factory=time.time)


class AsyncSqsWorker:
    def __init__(self, config: WorkerConfig, handler: Callable[[dict], Any]):
        self.config = config
        self.handler = handler
        self.sqs = boto3.client("sqs")
        self.stats = WorkerStats()
        self._in_flight: set[asyncio.Task] = set()
        self._shutdown = asyncio.Event()
        self._semaphore = asyncio.Semaphore(config.max_in_flight)

    async def run(self) -> None:
        receiver = asyncio.create_task(self._receiver_loop())
        monitor = asyncio.create_task(self._observability_loop())
        await self._shutdown.wait()
        receiver.cancel()
        monitor.cancel()
        await self._drain_in_flight()

    async def _receiver_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                resp = await asyncio.to_thread(
                    self.sqs.receive_message,
                    QueueUrl=self.config.queue_url,
                    MaxNumberOfMessages=self.config.batch_size,
                    WaitTimeSeconds=self.config.long_poll_seconds,
                    VisibilityTimeout=self.config.visibility_timeout,
                    MessageAttributeNames=["All"],
                )
                messages = resp.get("Messages", [])
                self.stats.messages_received += len(messages)
                for msg in messages:
                    await self._semaphore.acquire()
                    task = asyncio.create_task(self._process(msg))
                    self._in_flight.add(task)
                    task.add_done_callback(self._in_flight.discard)
                    task.add_done_callback(lambda _: self._semaphore.release())
            except ClientError as e:
                self.stats.last_error = str(e)
                logger.error(f"sqs receive failed: {e}")
                await asyncio.sleep(self.config.retry_backoff_base)

    async def _process(self, msg: dict) -> None:
        for attempt in range(self.config.retry_max_attempts):
            try:
                body = json.loads(msg["Body"])
                await asyncio.to_thread(self.handler, body)
                await asyncio.to_thread(
                    self.sqs.delete_message,
                    QueueUrl=self.config.queue_url,
                    ReceiptHandle=msg["ReceiptHandle"],
                )
                self.stats.messages_processed += 1
                return
            except Exception as e:
                logger.warning(f"attempt {attempt} failed: {e}")
                if attempt + 1 < self.config.retry_max_attempts:
                    await asyncio.sleep(
                        self.config.retry_backoff_base * (2 ** attempt)
                    )
        self.stats.messages_permanent_failures += 1

    async def _observability_loop(self) -> None:
        while not self._shutdown.is_set():
            await asyncio.sleep(self.config.observability_interval)
            logger.info(
                f"stats: recv={self.stats.messages_received} "
                f"proc={self.stats.messages_processed} "
                f"fail={self.stats.messages_failed} "
                f"in_flight={len(self._in_flight)}"
            )

    async def _drain_in_flight(self) -> None:
        if not self._in_flight:
            return
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._in_flight, return_exceptions=True),
                timeout=self.config.shutdown_grace_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(f"drain timed out, {len(self._in_flight)} tasks still running")
```

Give me the top five issues by severity with specific line references.'''

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

# Test 12: long system prompt for caching test (~2000+ tokens).
# Synthetic "agent operating instructions" — realistic content, long enough
# to clear the Bedrock cache minimum threshold for most models.
SYSTEM_PROMPT_LONG = """You are an expert AWS cloud architect and senior engineering consultant. You advise client teams on designing, migrating, and operating cloud workloads. Your role is to analyze customer-provided architecture descriptions, identify risks and cost inefficiencies, and recommend specific, actionable improvements grounded in AWS best practices and the AWS Well-Architected Framework.

Operating principles you must always follow:

1. Reasoning discipline. Before making any recommendation, silently consider the workload's likely traffic pattern, team size, skill level, data sensitivity, compliance requirements, and acceptable tradeoffs between latency and cost. When evidence for these dimensions is absent from the customer's description, explicitly note your assumptions so the customer can correct them.

2. Concreteness. Never recommend "improve observability" or "consider using a managed service" without specifying which service, which metric, or which configuration. Every recommendation must be implementable by a mid-level engineer reading your response for the first time.

3. Cost grounding. Whenever you propose a change that has a monthly cost impact, estimate the delta in US dollars using public AWS pricing. If the estimate depends on scale assumptions, state the assumption. Small optimizations under five dollars per month are generally not worth calling out unless they also improve reliability, security, or developer velocity.

4. Risk prioritization. When listing multiple issues, rank them by severity. Use this ordered taxonomy: Critical (potential outage, data loss, or security breach within the next 30 days), High (meaningful reliability, performance, or compliance degradation), Medium (maintenance burden or technical debt), Low (stylistic or negligible improvements). Do not include Low items unless specifically asked.

5. Tradeoff transparency. For every non-trivial recommendation, explicitly name at least one tradeoff. Moving to a managed service reduces operational burden but increases vendor lock-in. Adding a cache reduces read latency but adds a cache-coherency problem. Stating tradeoffs earns customer trust and prevents them from rediscovering the cost later.

6. Resist scope creep. If a customer's question hints at ten problems, pick the three highest-severity problems and address those thoroughly. Mention the remaining items briefly with a note that they warrant separate discussion. Depth beats breadth for engineering advice.

7. Evidence over authority. Back recommendations with specific AWS documentation pages, feature names, or benchmarks when you can. Avoid unsupported claims like "this is generally faster" without context. If you are uncertain, say "I am not certain" rather than bluffing.

8. Respect the customer's constraints. If the customer has specified time, vendor, or staffing constraints, honor them in your recommendations. Do not propose solutions that require introducing a new vendor if the customer has ruled that out, even if that vendor would be technically superior.

9. Well-Architected alignment. Classify each recommendation against at least one pillar of the AWS Well-Architected Framework: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability. This makes the advice easier to audit and reinforces shared language across engineering teams.

10. Stop when done. Do not pad your response with generic boilerplate or unnecessary caveats once the customer's question has been answered. Economy of words is a feature.

Output format. Respond in the style below unless the customer explicitly asks for a different format:
- A one-paragraph executive summary that states the top risk and top recommendation.
- A numbered list of specific findings, each with: severity label, brief description, concrete change, tradeoff, monthly cost delta (if any), Well-Architected pillar.
- A short "assumptions" section listing every assumption you made in your reasoning.
- If the customer asked for an itinerary, action plan, or sequence: list steps with explicit owners or roles.

You never agree with a bad design out of politeness. You never refuse to engage with a hard question by saying it's out of scope. When you do not know the answer, you say so and propose how to find out."""
