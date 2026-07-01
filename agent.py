from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .audit import AuditTrail
from .blockchain import build_agent_system_prompt
from .models import ModelGateway
from .security import LocalIdentity, LocalVault


@dataclass
class AnkerAgent:
    identity: LocalIdentity
    vault: LocalVault
    audit: AuditTrail
    model_gateway: ModelGateway | None = None
    last_event: dict[str, str] | None = field(default=None, init=False)

    def store_secret(self, name: str, value: str) -> dict[str, str]:
        self.vault.set_secret(name, value)
        self.last_event = self.audit.record(
            "store_secret",
            {
                "agent_id": self.identity.agent_id,
                "name": name,
                "signature": self.identity.sign(f"store_secret:{name}"),
            },
        )
        return self.last_event

    def reveal_secret(self, name: str) -> str:
        value = self.vault.get_secret(name)
        self.last_event = self.audit.record(
            "reveal_secret",
            {
                "agent_id": self.identity.agent_id,
                "name": name,
                "signature": self.identity.sign(f"reveal_secret:{name}"),
            },
        )
        return value

    def snapshot(self) -> dict[str, object]:
        return {
            "agent_id": self.identity.agent_id,
            "identity_fingerprint": self.identity.fingerprint(),
            "secrets": sorted(self.vault.items().keys()),
            "last_event": self.last_event,
        }

    def ask_model(self, prompt: str, system: str | None = None) -> str:
        if self.model_gateway is None:
            raise RuntimeError(
                "No model gateway configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY, "
                "or provide a ModelGateway explicitly."
            )

        system_prompt = system or build_agent_system_prompt()

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        response = self.model_gateway.generate(prompt=prompt, system=system_prompt)
        self.last_event = self.audit.record(
            "model_inference",
            {
                "agent_id": self.identity.agent_id,
                "provider": self.model_gateway.provider,
                "model": self.model_gateway.model,
                "prompt_hash": prompt_hash,
                "signature": self.identity.sign(f"model_inference:{prompt_hash}"),
            },
        )
        return response
