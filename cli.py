from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from .agent import AnkerAgent
from .audit import AuditTrail
from .blockchain import build_agent_system_prompt
from .blockchains import BlockchainConnector
from .dashboard import render_dashboard
from .models import ModelGateway
from .session import SessionState
from .security import LocalIdentity, LocalVault


def build_agent(base_path: Path, model_gateway: ModelGateway | None = None) -> AnkerAgent:
    base_path.mkdir(parents=True, exist_ok=True)
    identity = LocalIdentity.load_or_create(base_path / "identity.json")
    passphrase_path = base_path / "passphrase.txt"
    if passphrase_path.exists():
        passphrase = passphrase_path.read_text(encoding="utf-8").strip()
    else:
        passphrase = secrets.token_hex(32)
        passphrase_path.write_text(passphrase, encoding="utf-8")
    vault = LocalVault(base_path / "vault.json", passphrase=passphrase)
    audit = AuditTrail(base_path / "audit.jsonl")
    return AnkerAgent(identity=identity, vault=vault, audit=audit, model_gateway=model_gateway)


def build_session_state(base_path: Path) -> SessionState:
    base_path.mkdir(parents=True, exist_ok=True)
    return SessionState(base_path / "session.json")


def build_chain_summary() -> dict[str, object]:
    chain_connector = BlockchainConnector()
    families: list[str] = []
    for target in chain_connector.targets:
        if target.family not in families:
            families.append(target.family)

    return {
        "supported_networks": len(chain_connector.targets),
        "families": families,
        "custom_registry": bool(os.environ.get("CAUSEDO_CHAIN_REGISTRY")),
        "probe_mode": bool(os.environ.get("CAUSEDO_CHAIN_PROBE")),
        "primary_targets": chain_connector.supported_networks()[:5],
    }


def build_dashboard_context(base_path: Path, agent: AnkerAgent, model_gateway: ModelGateway | None) -> dict[str, object]:
    audit_report = agent.audit.verify()
    session_state = build_session_state(base_path)
    session_payload = session_state.load()
    chain_summary = build_chain_summary()

    return {
        "agent_id": agent.identity.agent_id,
        "provider": None if model_gateway is None else model_gateway.provider,
        "model": None if model_gateway is None else model_gateway.model,
        "audit_ok": audit_report["ok"],
        "audit_entries": audit_report["entries"],
        "env_ready": {
            "NVIDIA_API_KEY": bool(os.environ.get("NVIDIA_API_KEY")),
            "NVIDIA_NIM_API_KEY": bool(os.environ.get("NVIDIA_NIM_API_KEY")),
            "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
            "OPENAI_KEY": bool(os.environ.get("OPENAI_KEY")),
            "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "CLAUDE_API_KEY": bool(os.environ.get("CLAUDE_API_KEY")),
            "CAUSEDO_API_KEY": bool(os.environ.get("CAUSEDO_API_KEY")),
            "API_KEY": bool(os.environ.get("API_KEY")),
        },
        "chain_summary": chain_summary,
        "paths": {
            "identity": str(base_path / "identity.json"),
            "vault": str(base_path / "vault.json"),
            "audit": str(base_path / "audit.jsonl"),
            "audit_tail": agent.audit.tail(limit=5),
            "session_prompt": session_payload.get("prompt"),
            "session_response": session_payload.get("response"),
        },
        "mission": session_payload.get("prompt") or "Sin misión guardada todavía.",
        "response": session_payload.get("response"),
    }


def print_dashboard_context(base_path: Path, agent: AnkerAgent, model_gateway: ModelGateway | None) -> None:
    context = build_dashboard_context(base_path, agent, model_gateway)
    print(
        render_dashboard(
            agent_id=context["agent_id"],
            provider=context["provider"],
            model=context["model"],
            audit_ok=context["audit_ok"],
            audit_entries=context["audit_entries"],
            env_ready=context["env_ready"],
            chain_summary=context["chain_summary"],
            paths=context["paths"],
            mission=context["mission"],
            response=context["response"],
        )
    )


def run_demo() -> int:
    base_path = Path.cwd() / ".causedo"
    agent = build_agent(base_path)

    agent.store_secret("demo_api_key", "demo-secret-value")
    recovered = agent.reveal_secret("demo_api_key")
    session_state = build_session_state(base_path)
    session_state.save(
        prompt="demo",
        response=f"Secret stored and recovered: {recovered}",
        provider=None,
        model=None,
    )

    print("Causedo demo listo")
    print(f"Agent ID: {agent.identity.agent_id}")
    print(f"Secretos guardados: {', '.join(agent.snapshot()['secrets'])}")
    print(f"Valor recuperado: {recovered}")
    print(f"Bitácora: {base_path / 'audit.jsonl'}")
    print(f"Bóveda: {base_path / 'vault.json'}")
    print_dashboard_context(base_path, agent, None)
    return 0


def run_ask(prompt: str) -> int:
    base_path = Path.cwd() / ".causedo"
    model_gateway = ModelGateway.from_env()
    if model_gateway is None:
        raise SystemExit(
            "Falta configurar un proveedor. Define NVIDIA_API_KEY, OPENAI_API_KEY o ANTHROPIC_API_KEY, "
            "y opcionalmente CAUSEDO_MODEL_PROVIDER / CAUSEDO_*_MODEL."
        )

    agent = build_agent(base_path, model_gateway=model_gateway)
    answer = agent.ask_model(prompt=prompt, system=build_agent_system_prompt())
    session_state = build_session_state(base_path)
    session_state.save(
        prompt=prompt,
        response=answer,
        provider=model_gateway.provider,
        model=model_gateway.model,
    )
    print("=== CAUSEDO MODEL PROOF ===")
    print(f"Provider: {model_gateway.provider}")
    print(f"Model: {model_gateway.model}")
    print(f"Prompt: {prompt}")
    print("--- Response ---")
    print(answer)
    print("===========================")
    print_dashboard_context(base_path, agent, model_gateway)
    return 0


def run_status() -> int:
    base_path = Path.cwd() / ".causedo"
    agent = build_agent(base_path)
    model_gateway = ModelGateway.from_env()
    audit_report = agent.audit.verify()

    status = {
        "agent_id": agent.identity.agent_id,
        "provider": None if model_gateway is None else model_gateway.provider,
        "model": None if model_gateway is None else model_gateway.model,
        "audit_ok": audit_report["ok"],
        "audit_entries": audit_report["entries"],
        "audit_broken_at": audit_report["broken_at"],
        "audit_reason": audit_report["reason"],
        "paths": {
            "identity": str(base_path / "identity.json"),
            "vault": str(base_path / "vault.json"),
            "audit": str(base_path / "audit.jsonl"),
        },
    }

    print(json.dumps(status, indent=2, ensure_ascii=False))
    print_dashboard_context(base_path, agent, model_gateway)
    return 0


def run_doctor() -> int:
    base_path = Path.cwd() / ".causedo"
    agent = build_agent(base_path)
    model_gateway = ModelGateway.from_env()
    audit_report = agent.audit.verify()

    env_flags = {
        "NVIDIA_API_KEY": bool(os.environ.get("NVIDIA_API_KEY")),
        "NVIDIA_NIM_API_KEY": bool(os.environ.get("NVIDIA_NIM_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "OPENAI_KEY": bool(os.environ.get("OPENAI_KEY")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "CLAUDE_API_KEY": bool(os.environ.get("CLAUDE_API_KEY")),
        "CAUSEDO_API_KEY": bool(os.environ.get("CAUSEDO_API_KEY")),
        "API_KEY": bool(os.environ.get("API_KEY")),
    }

    report = {
        "ok": audit_report["ok"] and model_gateway is not None,
        "agent_id": agent.identity.agent_id,
        "active_provider": None if model_gateway is None else model_gateway.provider,
        "active_model": None if model_gateway is None else model_gateway.model,
        "env": env_flags,
        "audit": audit_report,
        "paths": {
            "identity": str(base_path / "identity.json"),
            "vault": str(base_path / "vault.json"),
            "audit": str(base_path / "audit.jsonl"),
        },
    }

    print("=== CAUSEDO DOCTOR ===")
    print(f"Agent ID: {report['agent_id']}")
    print(f"Provider: {report['active_provider']}")
    print(f"Model: {report['active_model']}")
    print(f"Audit OK: {report['audit']['ok']}")
    print(f"Audit entries: {report['audit']['entries']}")
    print(f"Ready: {report['ok']}")
    print("--- Env flags ---")
    for key, value in env_flags.items():
        print(f"{key}: {value}")
    print("--- Paths ---")
    for key, value in report["paths"].items():
        print(f"{key}: {value}")
    print("=====================")
    print_dashboard_context(base_path, agent, model_gateway)
    return 0


def run_dashboard() -> int:
    base_path = Path.cwd() / ".causedo"
    agent = build_agent(base_path)
    model_gateway = ModelGateway.from_env()
    audit_report = agent.audit.verify()
    session_state = build_session_state(base_path)
    session_payload = session_state.load()
    audit_tail = agent.audit.tail(limit=5)
    chain_summary = build_chain_summary()

    env_ready = {
        "NVIDIA_API_KEY": bool(os.environ.get("NVIDIA_API_KEY")),
        "NVIDIA_NIM_API_KEY": bool(os.environ.get("NVIDIA_NIM_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "OPENAI_KEY": bool(os.environ.get("OPENAI_KEY")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "CLAUDE_API_KEY": bool(os.environ.get("CLAUDE_API_KEY")),
        "CAUSEDO_API_KEY": bool(os.environ.get("CAUSEDO_API_KEY")),
        "API_KEY": bool(os.environ.get("API_KEY")),
    }

    mission = (
        "Unificar automatización local, navegación web futura, auditoría encadenada, "
        "seguridad de secretos y capacidad de razonar como un agente especialista en blockchain."
    )

    response = None
    if model_gateway is not None:
        response = agent.ask_model(
            prompt=(
                "Resume en 5 líneas cómo Causedo puede convertirse en un agente superior: "
                "unifica blockchain, seguridad, auditoría, control humano y ejecución real."
            ),
            system=build_agent_system_prompt(),
        )

    dashboard = render_dashboard(
        agent_id=agent.identity.agent_id,
        provider=None if model_gateway is None else model_gateway.provider,
        model=None if model_gateway is None else model_gateway.model,
        audit_ok=audit_report["ok"],
        audit_entries=audit_report["entries"],
        env_ready=env_ready,
        chain_summary=chain_summary,
        paths={
            "identity": str(base_path / "identity.json"),
            "vault": str(base_path / "vault.json"),
            "audit": str(base_path / "audit.jsonl"),
            "audit_tail": audit_tail,
            "session_prompt": session_payload.get("prompt"),
            "session_response": session_payload.get("response"),
        },
        mission=mission,
        response=response or session_payload.get("response"),
    )
    print(dashboard)
    return 0


def run_flow(prompt: str | None = None) -> int:
    base_path = Path.cwd() / ".causedo"
    agent = build_agent(base_path)
    model_gateway = ModelGateway.from_env()
    audit_report = agent.audit.verify()
    session_state = build_session_state(base_path)
    session_payload = session_state.load()

    mission_prompt = (
        prompt
        or session_payload.get("prompt")
        or "Resume cómo Causedo puede convertirse en un agente superior uniendo blockchain, seguridad y auditoría."
    )

    response = session_payload.get("response")
    if model_gateway is not None:
        agent.model_gateway = model_gateway
        response = agent.ask_model(prompt=mission_prompt, system=build_agent_system_prompt())
        session_payload = session_state.save(
            prompt=mission_prompt,
            response=response,
            provider=model_gateway.provider,
            model=model_gateway.model,
        )
    else:
        response = (
            "Modo offline: no hay proveedor configurado. "
            "Define NVIDIA_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY o CAUSEDO_API_KEY para activar el cerebro."
        )
        session_payload = session_state.save(
            prompt=mission_prompt,
            response=response,
            provider=None,
            model=None,
        )

    env_ready = {
        "NVIDIA_API_KEY": bool(os.environ.get("NVIDIA_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "CAUSEDO_API_KEY": bool(os.environ.get("CAUSEDO_API_KEY")),
    }

    dashboard = render_dashboard(
        agent_id=agent.identity.agent_id,
        provider=None if model_gateway is None else model_gateway.provider,
        model=None if model_gateway is None else model_gateway.model,
        audit_ok=audit_report["ok"],
        audit_entries=audit_report["entries"],
        env_ready=env_ready,
        paths={
            "identity": str(base_path / "identity.json"),
            "vault": str(base_path / "vault.json"),
            "audit": str(base_path / "audit.jsonl"),
            "audit_tail": agent.audit.tail(limit=5),
            "session_prompt": session_payload.get("prompt"),
            "session_response": session_payload.get("response"),
        },
        mission=mission_prompt,
        response=response,
    )
    print(dashboard)
    return 0


def run_chains(probe: bool = True) -> int:
    connector = BlockchainConnector()
    print("=== CAUSEDO BLOCKCHAIN CONNECTOR ===")
    print(f"Supported networks: {len(connector.targets)}")
    for target in connector.plan():
        print(f"- {target['name']} [{target['family']}] -> {target['rpc_url']}")

    if not probe:
        print("Probing disabled. Use --probe to connect and inspect live networks.")
        print("====================================")
        return 0

    print("--- Probe results ---")
    results = connector.probe_all()
    for result in results:
        status = "connected" if result.reachable else "offline"
        print(f"{result.name}: {status}")
        if result.reachable:
            print(f"  summary: {json.dumps(result.summary, ensure_ascii=False)}")
        else:
            print(f"  error: {result.error}")
    print("====================================")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="causedo")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("demo", help="Ejecuta la demostración local")
    ask_command = subcommands.add_parser("ask", help="Consulta un modelo externo configurado por entorno")
    ask_command.add_argument("prompt", help="Mensaje que se enviará al modelo")
    subcommands.add_parser("status", help="Muestra el estado del agente y verifica la auditoría")
    subcommands.add_parser("doctor", help="Diagnóstico humano-legible de la instalación y del proveedor")
    subcommands.add_parser("dashboard", help="Muestra un panel grande unificado del agente")
    run_command = subcommands.add_parser("run", help="Ejecuta el flujo completo y muestra el dashboard conectado")
    run_command.add_argument("prompt", nargs="?", help="Misión o prompt para el cerebro del agente")
    chains_command = subcommands.add_parser("chains", help="Escanea y conecta redes blockchain compatibles")
    chains_command.add_argument("--no-probe", action="store_true", help="Solo muestra el plan sin conectar")
    arguments = parser.parse_args()

    if arguments.command == "demo":
        return run_demo()
    if arguments.command == "ask":
        return run_ask(arguments.prompt)
    if arguments.command == "status":
        return run_status()
    if arguments.command == "doctor":
        return run_doctor()
    if arguments.command == "dashboard":
        return run_dashboard()
    if arguments.command == "run":
        return run_flow(arguments.prompt)
    if arguments.command == "chains":
        return run_chains(probe=not arguments.no_probe)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
