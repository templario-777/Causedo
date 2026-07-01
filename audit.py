from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


class AuditTrail:
    def __init__(self, storage_path: str | Path) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._previous_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self.storage_path.exists():
            return "0" * 64
        last_line = ""
        for line in self.storage_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last_line = line
        if not last_line:
            return "0" * 64
        try:
            return json.loads(last_line).get("entry_hash", "0" * 64)
        except json.JSONDecodeError:
            return "0" * 64

    def record(self, action: str, detail: dict[str, object] | None = None) -> dict[str, object]:
        detail = detail or {}
        entry = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "action": action,
            "detail": detail,
            "previous_hash": self._previous_hash,
        }
        entry_hash = hashlib.sha256(json.dumps(entry, sort_keys=True).encode("utf-8")).hexdigest()
        entry["entry_hash"] = entry_hash
        with self.storage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._previous_hash = entry_hash
        return entry

    def verify(self) -> dict[str, object]:
        if not self.storage_path.exists():
            return {
                "ok": True,
                "entries": 0,
                "broken_at": None,
                "reason": None,
            }

        previous_hash = "0" * 64
        entries = 0

        for line_number, line in enumerate(self.storage_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return {
                    "ok": False,
                    "entries": entries,
                    "broken_at": line_number,
                    "reason": "invalid_json",
                }

            payload = {key: value for key, value in entry.items() if key != "entry_hash"}
            expected_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
            if entry.get("previous_hash") != previous_hash:
                return {
                    "ok": False,
                    "entries": entries,
                    "broken_at": line_number,
                    "reason": "broken_chain",
                }

            if entry.get("entry_hash") != expected_hash:
                return {
                    "ok": False,
                    "entries": entries,
                    "broken_at": line_number,
                    "reason": "hash_mismatch",
                }

            previous_hash = expected_hash
            entries += 1

        return {
            "ok": True,
            "entries": entries,
            "broken_at": None,
            "reason": None,
        }

    def tail(self, limit: int = 5) -> list[dict[str, object]]:
        if not self.storage_path.exists() or limit <= 0:
            return []

        entries: list[dict[str, object]] = []
        for line in self.storage_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        return entries[-limit:]
