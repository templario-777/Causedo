# Causedo

Causedo es la base de un agente local-first orientado a automatización asistida, auditoría y manejo seguro de secretos.

La idea del proyecto es simple: un agente que pueda trabajar sobre tareas web o locales sin convertir las credenciales en texto plano, dejando una huella verificable de cada acción y permitiendo intervención humana cuando haga falta.

El objetivo de diseño es que Causedo piense como un experto en blockchain y como un agente de ingeniería muy fuerte: serio con la seguridad, claro con los riesgos y útil para ejecutar tareas reales.

## Estado actual

Este repositorio ya incluye un esqueleto funcional para validar el flujo básico.

- Identidad local del agente.
- Bóveda de secretos en disco.
- Registro de auditoría con hash encadenado.
- CLI de demostración.

## Qué resuelve

- Separar secretos del código fuente.
- Tener trazabilidad de lo que hace el agente.
- Dejar preparado el camino para navegación web, sandbox y human-in-the-loop.
- Usar modelos externos de OpenAI o Anthropic sin acoplar el proyecto a un SDK concreto.
- Usar también NVIDIA como proveedor de prueba sin cambiar el código del agente.
- Pensar como un especialista en blockchain, wallets, auditoría y seguridad operacional.

## Estructura

```text
Causedo/
├── README.md
├── LICENSE
├── pyproject.toml
└── causedo/
    ├── __init__.py
    ├── agent.py
    ├── audit.py
    ├── cli.py
    └── security.py
```

## Uso

Puedes ejecutarlo de estas tres formas:

```bash
python -m causedo
python -m causedo.cli demo
causedo demo
```

La ruta recomendada para ver todo conectado es:

```bash
python -m causedo.cli run "Resume Causedo"
```

En Windows también puedes usar:

```bash
py -3 -m causedo.cli demo
```

La demo crea una identidad local, guarda un secreto de ejemplo, registra la acción en una bitácora y muestra el resultado final dentro de `.causedo/`.

### Consultar un modelo externo

Para pruebas, usa `NVIDIA_API_KEY` y luego ejecuta:

```bash
python -m causedo.cli ask "Diseña un plan de trabajo para este agente"
```

Si quieres fijar proveedor y modelo para NVIDIA:

```bash
$env:CAUSEDO_MODEL_PROVIDER = "nvidia"
$env:CAUSEDO_NVIDIA_MODEL = "meta/llama-3.1-70b-instruct"
```

En `cmd.exe` usa `set CAUSEDO_MODEL_PROVIDER=nvidia` y `set CAUSEDO_NVIDIA_MODEL=meta/llama-3.1-70b-instruct`.

OpenAI y Anthropic siguen disponibles con `OPENAI_API_KEY` y `ANTHROPIC_API_KEY`.

También se aceptan alias comunes: `OPENAI_KEY`, `API_KEY`, `CLAUDE_API_KEY` y `NVIDIA_NIM_API_KEY`.

También puedes usar un proveedor compatible OpenAI con:

```bash
$env:CAUSEDO_MODEL_PROVIDER = "compatible"
$env:CAUSEDO_API_KEY = "..."
$env:CAUSEDO_BASE_URL = "https://tu-endpoint/v1"
```

### Estado y auditoría

```bash
python -m causedo.cli status
```

Ese comando muestra el agente actual, el proveedor activo y el estado de la cadena de auditoría.

### Diagnóstico rápido

```bash
python -m causedo.cli doctor
```

Ese comando imprime un reporte legible con el agente, el proveedor activo, las variables de entorno detectadas y el estado general de preparación.

### Panel gigante

```bash
python -m causedo.cli dashboard
```

Ese panel unifica identidad, auditoría, proveedor, misión y la respuesta del modelo en una sola vista amplia de consola.

La vista también conserva la última sesión consultada y enseña los últimos eventos del ledger local.

Además, enseña un resumen multi-chain con las redes soportadas y el estado del registro de cadenas.

Además, `demo`, `ask`, `status` y `doctor` terminan reimprimiendo el panel para que siempre veas el estado actualizado.

### Flujo completo

```bash
python -m causedo.cli run "Resume cómo Causedo puede convertirse en un agente superior"
```

Ese comando conecta todo: toma la misión, consulta el modelo si existe, guarda la sesión y termina mostrando el dashboard con el resultado.

### Conector Multi-chain

```bash
python -m causedo.cli chains --no-probe
python -m causedo.cli chains
```

El primer comando lista las redes soportadas. El segundo intenta conectar y reporta el estado de cada una.

El dashboard y el diagnóstico también muestran el resumen multi-chain para que todo quede conectado.

Si quieres añadir redes propias, define `CAUSEDO_CHAIN_REGISTRY` con un JSON como este:

```json
[
    {"name": "Mi Red", "family": "evm", "rpc_url": "https://mi-rpc/v1"}
]
```

## Filosofía técnica

El proyecto no trata la blockchain como un sustituto automático de la seguridad. Primero valida un flujo local fiable; luego, si aporta valor real, se puede conectar un ledger externo o una capa Web3.

Causedo está diseñado para razonar bien sobre Ethereum, Solana, L2s, DID, custodia, auditoría y límites de gasto. No asume que blockchain siempre sea la respuesta; la usa cuando realmente resuelve confianza, trazabilidad o control.

La capa de blockchain ahora también incluye un conector universal multi-chain que autodetecta redes soportadas y puede probarlas una a una.

## Próximos pasos

- Integrar navegación web real.
- Añadir sandbox con Docker o WASM.
- Sustituir el cifrado demo por una implementación criptográfica de producción.
- Conectar un UI de supervisión para Human-in-the-Loop.
- Añadir comandos específicos por proveedor y flujos de agente más largos.
- Construir una interfaz visual más avanzada sobre este panel base.
- Hacer que el flujo completo ejecute tareas web o locales reales.
- Expandir el registro de redes con más blockchains según el endpoint RPC que quieras usar.

## Nota

La versión actual está pensada como base técnica y punto de partida, no como producto terminado.