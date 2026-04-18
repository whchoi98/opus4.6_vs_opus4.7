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
