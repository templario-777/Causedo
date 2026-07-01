from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _xor_bytes(data: bytes, key_stream: bytes) -> bytes:
    return bytes(byte ^ key_stream[index] for index, byte in enumerate(data))


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        390_000,
        dklen=32,
    )


def _stream_bytes(key: bytes, length: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < length:
        counter_bytes = counter.to_bytes(8, byteorder="big", signed=False)
        chunks.append(hashlib.sha256(key + counter_bytes).digest())
        counter += 1
    return b"".join(chunks)[:length]


@dataclass(frozen=True)
class LocalIdentity:
    agent_id: str
    secret: bytes

    @classmethod
    def create(cls) -> "LocalIdentity":
        secret = secrets.token_bytes(32)
        agent_id = hashlib.sha256(secret).hexdigest()[:16]
        return cls(agent_id=agent_id, secret=secret)

    @classmethod
    def load_or_create(cls, storage_path: str | Path) -> "LocalIdentity":
        path = Path(storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                agent_id=payload["agent_id"],
                secret=base64.b64decode(payload["secret"]),
            )

        identity = cls.create()
        identity.save(path)
        return identity

    def save(self, storage_path: str | Path) -> None:
        path = Path(storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "agent_id": self.agent_id,
            "secret": base64.b64encode(self.secret).decode("ascii"),
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def fingerprint(self) -> str:
        return hashlib.sha256(self.secret).hexdigest()

    def sign(self, payload: str) -> str:
        signature = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256)
        return signature.hexdigest()


class LocalVault:
    def __init__(self, storage_path: str | Path, passphrase: str | None = None) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.passphrase = passphrase or os.environ.get("CAUSEDO_PASSPHRASE") or secrets.token_hex(16)
        self._salt = self._load_or_create_salt()
        self._derived_key = _derive_key(self.passphrase, self._salt)
        self._secrets = self._load_secrets()

    def _load_or_create_salt(self) -> bytes:
        if self.storage_path.exists():
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return base64.b64decode(payload["salt"])
        return secrets.token_bytes(16)

    def _load_secrets(self) -> dict[str, str]:
        if not self.storage_path.exists():
            return {}
        payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return dict(payload.get("secrets", {}))

    def _encrypt(self, value: str) -> str:
        raw = value.encode("utf-8")
        key_stream = _stream_bytes(self._derived_key, len(raw))
        encrypted = _xor_bytes(raw, key_stream)
        return base64.b64encode(encrypted).decode("ascii")

    def _decrypt(self, value: str) -> str:
        raw = base64.b64decode(value.encode("ascii"))
        key_stream = _stream_bytes(self._derived_key, len(raw))
        decrypted = _xor_bytes(raw, key_stream)
        return decrypted.decode("utf-8")

    def set_secret(self, name: str, value: str) -> None:
        self._secrets[name] = self._encrypt(value)
        self.save()

    def get_secret(self, name: str) -> str:
        if name not in self._secrets:
            raise KeyError(f"Secret '{name}' not found")
        return self._decrypt(self._secrets[name])

    def items(self) -> dict[str, str]:
        return {name: self._decrypt(value) for name, value in self._secrets.items()}

    def save(self) -> None:
        payload = {
            "salt": base64.b64encode(self._salt).decode("ascii"),
            "secrets": self._secrets,
        }
        self.storage_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
