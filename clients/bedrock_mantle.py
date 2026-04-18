"""Raw HTTP client for the bedrock-mantle endpoint using manual SigV4.

The Anthropic SDK signs with service name 'bedrock' — Mantle rejects that.
We sign with service name 'bedrock-mantle' using botocore.auth.SigV4Auth.
"""
from __future__ import annotations

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
