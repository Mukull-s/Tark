import os
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Resolve .env relative to project workspace root
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_project_root, ".env"))

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("MERGE_GATEWAY_API_KEY") or os.getenv("MERGE_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api-gateway.merge.dev/v1")
        self.model = os.getenv("LLM_MODEL", "deepseek/deepseek-v4-flash")
        # Observability: callers/UI can distinguish live synthesis from fallback.
        self.last_call_status = "NOT_CALLED"

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, max_tokens: int = 1500) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        try:
            r = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=45)
            r.raise_for_status()
            data = r.json()
            choice = data["choices"][0]["message"]
            content = choice.get("content")
            if content and len(content.strip()) > 0:
                self.last_call_status = "LIVE"
                return content.strip()
        except Exception as e:
            logger.warning("LLM API warning (%s); LLM synthesis unavailable.", e)

        # Honest, non-fabricating fallback. This text intentionally makes NO claims
        # about the case: it is a short marker so callers fall back to their
        # deterministic, grounded narrative rather than an ungrounded template.
        self.last_call_status = "FALLBACK_DETERMINISTIC"
        return (
            "LLM synthesis unavailable; a deterministic, evidence-grounded narrative is used "
            "instead of an unverified generated template."
        )
