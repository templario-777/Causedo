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


@dataclass(frozen=True)
class BlockchainTarget:
    name: str
    family: str
    rpc_url: str
    env_hint: str | None = None


@dataclass(frozen=True)
class BlockchainProbeResult:
    name: str
    family: str
    rpc_url: str
    reachable: bool
    summary: dict[str, Any]
    error: str | None = None


class BlockchainConnector:
    def __init__(self, targets: list[BlockchainTarget] | None = None) -> None:
        self.targets = targets or self._default_targets()

    def _default_targets(self) -> list[BlockchainTarget]:
        targets = [
            BlockchainTarget("Ethereum", "evm", _first_env("ETHEREUM_RPC_URL", "ETH_RPC_URL") or "https://cloudflare-eth.com", "ETHEREUM_RPC_URL"),
            BlockchainTarget("Base", "evm", _first_env("BASE_RPC_URL") or "https://mainnet.base.org", "BASE_RPC_URL"),
            BlockchainTarget("Arbitrum", "evm", _first_env("ARBITRUM_RPC_URL") or "https://arb1.arbitrum.io/rpc", "ARBITRUM_RPC_URL"),
            BlockchainTarget("Optimism", "evm", _first_env("OPTIMISM_RPC_URL") or "https://mainnet.optimism.io", "OPTIMISM_RPC_URL"),
            BlockchainTarget("Polygon", "evm", _first_env("POLYGON_RPC_URL") or "https://polygon-rpc.com", "POLYGON_RPC_URL"),
            BlockchainTarget("Avalanche C-Chain", "evm", _first_env("AVALANCHE_RPC_URL") or "https://api.avax.network/ext/bc/C/rpc", "AVALANCHE_RPC_URL"),
            BlockchainTarget("BNB Chain", "evm", _first_env("BSC_RPC_URL") or "https://bsc-dataseed.binance.org", "BSC_RPC_URL"),
            BlockchainTarget("Solana", "solana", _first_env("SOLANA_RPC_URL") or "https://api.mainnet-beta.solana.com", "SOLANA_RPC_URL"),
        ]

        extra_registry = os.environ.get("CAUSEDO_CHAIN_REGISTRY")
        if extra_registry:
            try:
                parsed = json.loads(extra_registry)
                for item in parsed:
                    targets.append(
                        BlockchainTarget(
                            name=item["name"],
                            family=item.get("family", "evm"),
                            rpc_url=item["rpc_url"],
                            env_hint=item.get("env_hint"),
                        )
                    )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        return targets

    def supported_networks(self) -> list[str]:
        return [target.name for target in self.targets]

    def plan(self) -> list[dict[str, str]]:
        return [
            {
                "name": target.name,
                "family": target.family,
                "rpc_url": target.rpc_url,
                "env_hint": target.env_hint or "custom",
            }
            for target in self.targets
        ]

    def probe_all(self, timeout: int = 10) -> list[BlockchainProbeResult]:
        return [self.probe(target, timeout=timeout) for target in self.targets]

    def probe(self, target: BlockchainTarget, timeout: int = 10) -> BlockchainProbeResult:
        try:
            if target.family == "solana":
                summary = self._probe_solana(target.rpc_url, timeout=timeout)
            else:
                summary = self._probe_evm(target.rpc_url, timeout=timeout)
            return BlockchainProbeResult(
                name=target.name,
                family=target.family,
                rpc_url=target.rpc_url,
                reachable=True,
                summary=summary,
            )
        except Exception as error:  # pragma: no cover - error details are returned to the user
            return BlockchainProbeResult(
                name=target.name,
                family=target.family,
                rpc_url=target.rpc_url,
                reachable=False,
                summary={},
                error=str(error),
            )

    def _request_json(self, url: str, payload: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"RPC request failed ({error.code}): {body}") from error

    def _probe_evm(self, rpc_url: str, timeout: int = 10) -> dict[str, Any]:
        chain_id = self._request_json(rpc_url, {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}, timeout=timeout)
        client_version = self._request_json(rpc_url, {"jsonrpc": "2.0", "id": 2, "method": "web3_clientVersion", "params": []}, timeout=timeout)
        block_number = self._request_json(rpc_url, {"jsonrpc": "2.0", "id": 3, "method": "eth_blockNumber", "params": []}, timeout=timeout)
        return {
            "chain_id": chain_id.get("result"),
            "client_version": client_version.get("result"),
            "block_number": block_number.get("result"),
        }

    def _probe_solana(self, rpc_url: str, timeout: int = 10) -> dict[str, Any]:
        version = self._request_json(rpc_url, {"jsonrpc": "2.0", "id": 1, "method": "getVersion", "params": []}, timeout=timeout)
        genesis_hash = self._request_json(rpc_url, {"jsonrpc": "2.0", "id": 2, "method": "getGenesisHash", "params": []}, timeout=timeout)
        slot = self._request_json(rpc_url, {"jsonrpc": "2.0", "id": 3, "method": "getSlot", "params": []}, timeout=timeout)
        return {
            "version": version.get("result"),
            "genesis_hash": genesis_hash.get("result"),
            "slot": slot.get("result"),
        }
