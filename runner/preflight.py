"""Pre-flight checks before running the benchmark."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """Load .env.local if it exists. Real env vars take precedence."""
    env_path = Path(".env.local")
    if env_path.exists():
        load_dotenv(env_path)


def check_auth_env(backends: set[str]) -> tuple[bool, str]:
    """Return (ok, message). Verifies required auth env vars for selected backends."""
    errors: list[str] = []

    if "1p" in backends:
        if not os.getenv("ANTHROPIC_API_KEY"):
            errors.append("1P backend selected but ANTHROPIC_API_KEY is not set.")

    if "bedrock" in backends:
        has_bearer = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))
        has_iam = bool(
            os.getenv("AWS_PROFILE")
            or os.getenv("AWS_ACCESS_KEY_ID")
            or _has_any_credential_source()
        )
        if not (has_bearer or has_iam):
            errors.append(
                "Bedrock backend selected but no AWS auth found. Set one of: "
                "AWS_BEARER_TOKEN_BEDROCK, AWS_PROFILE, AWS_ACCESS_KEY_ID, or run on "
                "an EC2 instance with an attached role."
            )

    if errors:
        return False, "\n".join(errors)
    return True, "OK"


def _has_any_credential_source() -> bool:
    """Return True if boto3 credential chain can find any credential."""
    try:
        from botocore.session import Session
        return Session().get_credentials() is not None
    except Exception:
        return False
