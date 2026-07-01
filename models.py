from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _normalize_provider_name(provider: str | None) -> str | None:
    if provider is None:
        return None

    normalized = provider.strip().lower()
    alias_map = {
        "openai-compatible": "compatible",
        "openai_compatible": "compatible",
        "generic": "compatible",
        "openrouter": "compatible",
        "azure-openai": "compatible",
        "azure_openai": "compatible",
        "gpt": "openai",
        "claude": "anthropic",
        "anthropic-claude": "anthropic",
        "nvidia-nim": "nvidia",
        "nvidia_nim": "nvidia",
    }
    return alias_map.get(normalized, normalized)


@dataclass(frozen=True)
class ModelGateway:
    provider: str
    model: str
    api_key: str
    base_url: str | None = None

    @classmethod
    def from_env(cls) -> "ModelGateway | None":
        provider = _normalize_provider_name(os.environ.get("CAUSEDO_MODEL_PROVIDER"))

        if provider in {"compatible", "openai-compatible", "generic"} or (
            provider is None and _first_env("CAUSEDO_API_KEY", "API_KEY", "OPENAI_API_KEY", "OPENAI_KEY", "OPENROUTER_API_KEY")
        ):
            api_key = _first_env("CAUSEDO_API_KEY", "API_KEY", "OPENAI_API_KEY", "OPENAI_KEY", "OPENROUTER_API_KEY")
            if not api_key:
                return None
            return cls(
                provider="compatible",
                model=os.environ.get("CAUSEDO_MODEL", "gpt-4o-mini"),
                api_key=api_key,
                base_url=_first_env("CAUSEDO_BASE_URL", "OPENAI_BASE_URL", "OPENROUTER_BASE_URL", "AZURE_OPENAI_ENDPOINT")
                or "https://api.openai.com",
            )

        if provider == "nvidia" or (provider is None and _first_env("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY", "NVIDIA_KEY")):
            api_key = _first_env("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY", "NVIDIA_KEY")
            if not api_key:
                return None
            return cls(
                provider="nvidia",
                model=os.environ.get("CAUSEDO_NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
                api_key=api_key,
                base_url=_first_env("CAUSEDO_NVIDIA_BASE_URL", "NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1",
            )

        if provider == "openai" or (provider is None and _first_env("OPENAI_API_KEY", "OPENAI_KEY")):
            api_key = _first_env("OPENAI_API_KEY", "OPENAI_KEY", "CAUSEDO_API_KEY", "API_KEY")
            if not api_key:
                return None
            return cls(
                provider="openai",
                model=os.environ.get("CAUSEDO_OPENAI_MODEL", "gpt-4o-mini"),
                api_key=api_key,
                base_url=_first_env("CAUSEDO_OPENAI_BASE_URL", "OPENAI_BASE_URL") or "https://api.openai.com/v1",
            )

        if provider == "anthropic" or (provider is None and _first_env("ANTHROPIC_API_KEY", "ANTHROPIC_KEY", "CLAUDE_API_KEY")):
            api_key = _first_env("ANTHROPIC_API_KEY", "ANTHROPIC_KEY", "CLAUDE_API_KEY")
            if not api_key:
                return None
            return cls(
                provider="anthropic",
                model=os.environ.get("CAUSEDO_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
                api_key=api_key,
                base_url=_first_env("CAUSEDO_ANTHROPIC_BASE_URL", "ANTHROPIC_BASE_URL", "CLAUDE_BASE_URL") or "https://api.anthropic.com",
            )

        return None

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> str:
        if self.provider in {"nvidia", "openai", "compatible"}:
            api_path = "/chat/completions"
            if self.provider == "compatible":
                api_path = os.environ.get("CAUSEDO_CHAT_PATH", "/v1/chat/completions")
            return self._generate_openai_like(prompt=prompt, system=system, temperature=temperature, api_path=api_path)
        if self.provider == "anthropic":
            return self._generate_anthropic(prompt=prompt, system=system, temperature=temperature)
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _request_json(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Model request failed ({error.code}): {body}") from error

    def _generate_openai_like(self, prompt: str, system: str | None, temperature: float, api_path: str) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        data = self._request_json(
            f"{self.base_url}{api_path}",
            payload,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        return data["choices"][0]["message"]["content"].strip()

    def _generate_anthropic(self, prompt: str, system: str | None, temperature: float) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        data = self._request_json(
            f"{self.base_url}/v1/messages",
            payload,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        content = data.get("content", [])
        text_chunks = [item.get("text", "") for item in content if isinstance(item, dict)]
        return "".join(text_chunks).strip()
