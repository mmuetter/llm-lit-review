"""Model clients for the two screening arms, with identical schema enforcement.

Each arm is configured for its lowest-variance setting: temperature 0 on
Mistral, thinking disabled at low effort on Sonnet, which rejects temperature.
"""

import json
import os
import random
import threading
import time

import anthropic
import requests
from dotenv import load_dotenv
from pathlib import Path

def find_env_file():
    """Return the nearest .env found by walking up from this module."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return None


load_dotenv(find_env_file())

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-large-2512"
ANTHROPIC_MODEL = "claude-sonnet-5"
MAX_OUTPUT_TOKENS = 64
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 2.0
BACKOFF_CAP_SECONDS = 60.0
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 529}
MISTRAL_MIN_INTERVAL_SECONDS = 2.5


def backoff_delay(attempt):
    """Return an exponential backoff delay with jitter for one attempt."""
    delay = min(BACKOFF_BASE_SECONDS * 2**attempt, BACKOFF_CAP_SECONDS)
    return delay + random.uniform(0, 1)


class RateLimiter:
    """Enforce a minimum interval between calls across all threads."""

    def __init__(self, min_interval_seconds):
        self.min_interval = min_interval_seconds
        self.lock = threading.Lock()
        self.next_allowed = 0.0

    def wait(self):
        """Block until this thread's reserved slot is due."""
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_allowed - now)
            self.next_allowed = max(now, self.next_allowed) + self.min_interval
        time.sleep(delay)


class MistralClient:
    """Mistral chat-completions arm with strict JSON-schema output."""

    name = "mistral-large-2512"

    def __init__(self):
        self.limiter = RateLimiter(MISTRAL_MIN_INTERVAL_SECONDS)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}",
            "Content-Type": "application/json",
        })

    def _body(self, prompt, schema):
        """Build the request body for one classification call."""
        response_format = {"type": "json_schema", "json_schema": {
            "name": "classification", "strict": True, "schema": schema}}
        return {"model": MISTRAL_MODEL, "temperature": 0,
                "max_tokens": MAX_OUTPUT_TOKENS, "response_format": response_format,
                "messages": [{"role": "user", "content": prompt}]}

    def classify(self, prompt, schema):
        """Return the parsed classification for one prompt."""
        for attempt in range(MAX_ATTEMPTS):
            self.limiter.wait()
            response = self.session.post(MISTRAL_URL, json=self._body(prompt, schema), timeout=90)
            if response.status_code == 200:
                return json.loads(response.json()["choices"][0]["message"]["content"])
            if response.status_code not in RETRYABLE_STATUS:
                raise RuntimeError(f"mistral {response.status_code}: {response.text[:200]}")
            time.sleep(backoff_delay(attempt))
        raise RuntimeError(f"mistral failed after {MAX_ATTEMPTS} attempts")


def refusal_category(response):
    """Return the safety category a refused response reports, if any."""
    details = getattr(response, "stop_details", None)
    return getattr(details, "category", None) if details else None


class AnthropicClient:
    """Claude Sonnet arm with thinking disabled and enforced JSON schema."""

    name = "claude-sonnet-5"

    def __init__(self):
        self.client = anthropic.Anthropic(max_retries=MAX_ATTEMPTS)

    def classify(self, prompt, schema):
        """Return the parsed classification for one prompt."""
        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={"type": "disabled"},
            output_config={"effort": "low",
                           "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError(f"refusal:{refusal_category(response)}")
        return json.loads(response.content[0].text)


def build_clients():
    """Instantiate both screening arms."""
    return [MistralClient(), AnthropicClient()]
