from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Optional

SENSITIVE_KEYS = {"api_key", "pin", "phrase", "token", "secret", "password"}


def _redact_text(text: str) -> str:
    if not text:
        return text
    redacted = text
    for key in SENSITIVE_KEYS:
        redacted = redacted.replace(key, "***")
    return redacted


def call_structured(
    schema: dict,
    instructions: str,
    input: dict,
    tags: Optional[list[str]] = None,
    timeout: Optional[int] = None,
    retries: Optional[int] = None,
) -> Optional[dict]:
    enabled = os.getenv("OPENAI_ENABLED", "0").strip() == "1"
    if not enabled:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.getLogger(__name__).warning("OpenAI disabled: OPENAI_API_KEY missing.")
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-5").strip() or "gpt-5"
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    timeout = timeout or int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
    retries = retries if retries is not None else int(os.getenv("OPENAI_MAX_RETRIES", "5"))
    from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError

    client = OpenAI(api_key=api_key, timeout=timeout)
    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": json.dumps(input, ensure_ascii=False)},
    ]
    attempt = 0
    while True:
        try:
            response = client.responses.create(
                model=model,
                input=messages,
                temperature=temperature,
                response_format={"type": "json_schema", "json_schema": schema},
                metadata={"tags": tags or []},
            )
            output_text = response.output_text
            if not output_text:
                return None
            return json.loads(output_text)
        except (RateLimitError, APIConnectionError, APITimeoutError, APIError) as exc:
            status = getattr(exc, "status_code", None)
            retryable = isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError)) or status in {
                429,
                500,
                502,
                503,
                504,
            }
            if retryable and attempt < retries:
                backoff = min(2**attempt, 30) + random.uniform(0, 1.0)
                logging.getLogger(__name__).warning(
                    "OpenAI retryable error (attempt %s/%s): %s",
                    attempt + 1,
                    retries,
                    _redact_text(str(exc)),
                )
                time.sleep(backoff)
                attempt += 1
                continue
            logging.getLogger(__name__).error("OpenAI call failed: %s", _redact_text(str(exc)))
            return None
        except json.JSONDecodeError as exc:
            logging.getLogger(__name__).error("OpenAI response JSON decode failed: %s", _redact_text(str(exc)))
            return None
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).error("OpenAI unexpected error: %s", _redact_text(str(exc)))
            return None
