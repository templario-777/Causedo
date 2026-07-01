from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class SessionState:
    def __init__(self, storage_path: str | Path) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, object]:
        if not self.storage_path.exists():
            return {}
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def save(self, *, prompt: str, response: str, provider: str | None, model: str | None) -> dict[str, object]:
        payload = {
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "prompt": prompt,
            "response": response,
            "provider": provider,
            "model": model,
        }
        self.storage_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return payload
