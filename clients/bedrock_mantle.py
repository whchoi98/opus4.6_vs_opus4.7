"""Raw HTTP client for the bedrock-mantle endpoint.

Supports two auth paths, selected via auth_method:

- "iam_role": SigV4 signing with service name 'bedrock-mantle' using IAM
  credentials. The Anthropic SDK can't be used because it signs with service
  name 'bedrock'. We also explicitly hide AWS_BEARER_TOKEN_BEDROCK during
  Session creation so boto3 falls through to the IAM/role chain.

- "bedrock_api_key": Authorization: Bearer <token>, no SigV4. The token comes
  from AWS_BEARER_TOKEN_BEDROCK. No IAM signing is applied.

Without this separation, both auth_methods would produce identical wire-level
requests (boto3 prefers bearer token when present), making the benchmark's
auth-method comparison meaningless.
"""
from __future__ import annotations

import json
import os
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


def _iam_only_session() -> Session:
    """Build a Session that uses the IAM/role/profile credential chain,
    explicitly ignoring AWS_BEARER_TOKEN_BEDROCK.

    We temporarily remove the bearer-token env var while constructing the
    Session so boto3 resolves credentials via the IAM chain (env vars,
    profile, role, IMDS). The env var is restored immediately.
    """
    saved = os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
    try:
        session = Session()
        # Force credential resolution now, while the bearer var is hidden
        _ = session.get_credentials()
        return session
    finally:
        if saved is not None:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = saved


class BedrockMantleClient:
    def __init__(self, region: str = config.BEDROCK_REGION, auth_method: str = "iam_role"):
        if auth_method not in ("iam_role", "bedrock_api_key"):
            raise ValueError(
                f"Mantle client auth_method must be 'iam_role' or 'bedrock_api_key'; "
                f"got {auth_method!r}"
            )
        self._region = region
        self._auth_method = auth_method
        self._url = config.MANTLE_URL

        if auth_method == "iam_role":
            self._session = _iam_only_session()
            if self._session.get_credentials() is None:
                raise RuntimeError(
                    "auth_method='iam_role' requires IAM credentials "
                    "(AWS_PROFILE / AWS_ACCESS_KEY_ID / instance role) — none found."
                )
            self._bearer_token: Optional[str] = None
        else:  # bedrock_api_key
            self._session = None
            self._bearer_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
            if not self._bearer_token:
                raise RuntimeError(
                    "auth_method='bedrock_api_key' requires AWS_BEARER_TOKEN_BEDROCK "
                    "to be set in the environment."
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

        if self._auth_method == "iam_role":
            headers, send_body = self._sign_iam(data)
        else:
            headers, send_body = self._auth_bearer(data)

        t0 = time.perf_counter()
        resp = requests.post(self._url, data=send_body, headers=headers, timeout=60)
        latency = time.perf_counter() - t0
        resp.raise_for_status()

        return parse_bedrock_response(
            resp.json(), latency_s=latency, backend="bedrock_mantle",
            auth_method=self._auth_method, model_id=model_id, effort=effort,
            prompt_label=prompt_label, run_index=run_index, test_id=test_id,
        )

    def _sign_iam(self, data: str) -> tuple[dict, object]:
        """Sign with SigV4 using IAM credentials. Returns (headers, body_to_send)."""
        aws_req = AWSRequest(
            method="POST", url=self._url, data=data,
            headers={"Content-Type": "application/json"},
        )
        # Fetch fresh credentials per-invoke — triggers auto-refresh on
        # RefreshableCredentials objects (IMDS, STS, AssumeRole).
        credentials = self._session.get_credentials()
        SigV4Auth(credentials, "bedrock-mantle", self._region).add_auth(aws_req)
        # Send what was signed, not the original data (safe against body mutation).
        send_body = aws_req.body if aws_req.body is not None else data
        return dict(aws_req.headers), send_body

    def _auth_bearer(self, data: str) -> tuple[dict, str]:
        """Authenticate with Bearer token header. No SigV4 signing."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._bearer_token}",
        }
        return headers, data
