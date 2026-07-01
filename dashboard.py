from __future__ import annotations

import shutil
import textwrap
from typing import Any


def _terminal_width() -> int:
    return max(96, shutil.get_terminal_size(fallback=(120, 30)).columns)


def _box(title: str, lines: list[str], width: int) -> str:
    inner_width = width - 4
    top = f"┏{'━' * (width - 2)}┓"
    header = f"┃ {title.ljust(width - 4)} ┃"
    separator = f"┣{'━' * (width - 2)}┫"
    body = []
    for line in lines:
        wrapped = textwrap.wrap(line, width=inner_width) or [""]
        for part in wrapped:
            body.append(f"┃ {part.ljust(inner_width)} ┃")
    bottom = f"┗{'━' * (width - 2)}┛"
    return "\n".join([top, header, separator, *body, bottom])


def _value_block(items: dict[str, Any]) -> list[str]:
    return [f"{key}: {value}" for key, value in items.items()]


def render_dashboard(*, agent_id: str, provider: str | None, model: str | None, audit_ok: bool, audit_entries: int, env_ready: dict[str, bool], chain_summary: dict[str, Any], paths: dict[str, str], mission: str, response: str | None = None) -> str:
    width = _terminal_width()
    accent = "CAUSEDO CONTROL CENTER".center(width - 2)
    status_line = f"Agent {agent_id} | Provider: {provider or 'offline'} | Model: {model or 'none'} | Audit: {'OK' if audit_ok else 'BROKEN'}"

    left = _box(
        "IDENTIDAD Y ESTADO",
        _value_block(
            {
                "Agent ID": agent_id,
                "Provider": provider or "offline",
                "Model": model or "none",
                "Audit OK": audit_ok,
                "Audit Entries": audit_entries,
            }
        ),
        width,
    )

    env_lines = [f"{key}: {'ready' if value else 'missing'}" for key, value in env_ready.items()]
    env_box = _box("SEÑALES DE ENTORNO", env_lines, width)

    chain_lines = [
        f"Supported networks: {chain_summary.get('supported_networks', 0)}",
        f"Families: {', '.join(chain_summary.get('families', [])) or 'none'}",
        f"Custom registry: {'yes' if chain_summary.get('custom_registry') else 'no'}",
        f"Probe mode: {'enabled' if chain_summary.get('probe_mode') else 'disabled'}",
        f"Primary targets: {', '.join(chain_summary.get('primary_targets', [])) or 'none'}",
    ]
    chain_box = _box("MULTI-CHAIN", chain_lines, width)

    paths_box = _box("RUTAS LOCALES", _value_block(paths), width)

    mission_box = _box(
        "MISIÓN",
        textwrap.wrap(mission, width=width - 4) or ["Sin misión definida."],
        width,
    )

    response_box = _box(
        "MENTE DEL MODELO",
        textwrap.wrap(response or "Sin respuesta generada todavía.", width=width - 4) or [""],
        width,
    )

    audit_lines = paths.get("audit_tail", []) if isinstance(paths.get("audit_tail", []), list) else []
    audit_box = _box(
        "AUDITORÍA RECIENTE",
        [
            f"{entry.get('timestamp', '')} | {entry.get('action', '')} | {entry.get('detail', {})}"
            for entry in audit_lines
        ] or ["Sin eventos recientes."],
        width,
    )

    session_prompt = paths.get("session_prompt")
    session_response = paths.get("session_response")
    session_box = _box(
        "SESION ACTUAL",
        [
            f"Prompt: {session_prompt or 'sin prompt guardado'}",
            f"Respuesta: {session_response or 'sin respuesta guardada'}",
        ],
        width,
    )

    return "\n".join([
        "═" * width,
        accent,
        "═" * width,
        status_line,
        "═" * width,
        left,
        "",
        env_box,
        "",
        chain_box,
        "",
        mission_box,
        "",
        session_box,
        "",
        response_box,
        "",
        audit_box,
        "",
        paths_box,
        "═" * width,
    ])
