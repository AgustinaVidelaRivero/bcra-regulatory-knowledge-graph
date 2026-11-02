#!/usr/bin/env python3
"""claude_falso.py — El CLI falso de la corrida en seco del lanzador en paralelo (U-BANCO-PARALELO). Ningún modelo y
ninguna petición a la API: costo USD 0.

Lo pone en el PATH la corrida en seco (paralelo/cli_falso/claude), en lugar de `claude`, así el lote corre el mismo
camino que el real (lanzar_lote_paralelo.py -> el lanzador de una sesión -> `claude`). Hace lo que el lote necesita del
CLI, con la interfaz que usa el lanzador:
  · `--version`: la versión sellada seguida de la marca de falso («2.1.241 (CLI falso …)»), así pasa la guarda de la
    versión del lote y la meta la registra como falsa;
  · lanza el servidor MCP de la sesión desde su JSON (--mcp-config), con la misma expansión de variables, por el cliente
    falso del banco (cliente_falso.py), con su entorno (el de la sesión) más el bloque `env` del JSON;
  · emite el stream como `claude -p --output-format stream-json --verbose`: system/init con las tools y el servidor
    `connected`, un tool_use y su tool_result por llamada real al servidor, el mensaje final con el JSON del contrato y
    el `result` con un modelUsage sintético;
  · sin --no-session-persistence, escribe la transcripción en <CLAUDE_CONFIG_DIR>/projects/<slug del cwd>/<session>.jsonl,
    de donde la copia el lanzador (sin ninguna fecha: el CLI real no la escribe ahí). En el cwd no escribe nada.
El plan de cada sesión (sus llamadas, su uso de tokens, si falla a mitad, la versión que da su system/init y si vuelve a
apuntar el enlace `claude` del PATH) sale de planes_seco.json, por la marca [[seco:<plan>]] de la pregunta. Una sesión que
falla mata su servidor con SIGKILL después de sus primeras llamadas y sale con 1, sin `result`. Una con
`repuntar_claude` cambia el destino del enlace `claude` del PATH, si es un enlace, por el de la carpeta hermana `<carpeta>_alt`:
así la corrida en seco prueba que el lote lo ve.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PARALELO = AQUI.parent
BANCO_DIR = PARALELO.parent
for _p in (str(BANCO_DIR), str(PARALELO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from cliente_falso import ClienteFalso   # noqa: E402
import guardas_lote as G                 # noqa: E402  (solo la tabla de procesos)

VERSION_SELLADA = "2.1.241"
VERSION = f"{VERSION_SELLADA} (CLI falso de la corrida en seco de U-BANCO-PARALELO: ninguna petición sale)"
PLANES = AQUI / "planes_seco.json"
MARCA = re.compile(r"\[\[seco:([A-Za-z0-9_-]+)\]\]")
CON_VALOR = {"-p", "--model", "--output-format", "--tools", "--mcp-config", "--permission-mode", "--allowedTools",
             "--disallowedTools", "--max-turns", "--max-budget-usd", "--session-id"}
PRECIO = {"input": 2.0, "cache_write_5m": 2.5, "cache_read": 0.2, "output": 10.0}   # agentes/precios_sellados.json


def leer_args(argv: list[str]) -> dict:
    a, i = {"flags": set()}, 0
    while i < len(argv):
        t = argv[i]
        if t in CON_VALOR:
            a[t] = argv[i + 1]
            i += 2
        else:
            a["flags"].add(t)
            i += 1
    return a


def expandir(s: str, env: dict) -> str:
    def rep(m):
        var, default = m.group(1), m.group(2)
        return env.get(var, default if default is not None else "")
    return re.sub(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}", rep, s)


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def main(argv: list[str]) -> int:
    a = leer_args(argv)
    if "--version" in a["flags"]:
        print(VERSION)
        return 0
    prompt, sid, model = a["-p"], a["--session-id"], a["--model"]
    m = MARCA.search(prompt)
    plan = json.loads(PLANES.read_text(encoding="utf-8"))["planes"][m.group(1)] if m else {"llamadas": []}
    (srv, s), = json.loads(Path(a["--mcp-config"]).read_text(encoding="utf-8"))["mcpServers"].items()
    env = dict(os.environ)
    cmd = [expandir(s["command"], env)] + [expandir(x, env) for x in s.get("args", [])]
    e = {k: expandir(v, env) for k, v in (s.get("env") or {}).items()}
    transcripcion, cwd = [], Path.cwd()

    def emitir(ev: dict, a_la_transcripcion: bool = True) -> None:
        print(json.dumps(ev, ensure_ascii=False), flush=True)
        if a_la_transcripcion:
            transcripcion.append(ev | {"sessionId": sid, "timestamp": ahora()})

    def guardar_transcripcion() -> None:
        if "--no-session-persistence" in a["flags"]:
            return
        slug = str(cwd).replace("/", "-").replace(" ", "-").replace("_", "-")
        d = Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects" / slug
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"{sid}.jsonl", "w", encoding="utf-8") as f:
            for ev in transcripcion:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    transcripcion.append({"type": "user", "sessionId": sid, "timestamp": ahora(), "version": VERSION,
                          "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}})
    if plan.get("repuntar_claude"):
        w = shutil.which("claude")
        if w and os.path.islink(w):
            alt = Path(w).parent.with_name(Path(w).parent.name + "_alt") / "claude"
            nuevo = w + ".nuevo"
            os.symlink(alt, nuevo)
            os.replace(nuevo, w)
    cli = ClienteFalso(cmd, env=e, timeout_s=600)
    cli.__enter__()
    nombres = sorted(f"mcp__{srv}__{t['name']}" for t in cli.listar_tools())
    emitir({"type": "system", "subtype": "init", "cwd": str(cwd), "session_id": sid, "tools": nombres,
            "mcp_servers": [{"name": srv, "status": "connected"}], "model": model,
            "permissionMode": a.get("--permission-mode"), "apiKeySource": "ANTHROPIC_API_KEY",
            "claude_code_version": plan.get("version_init", VERSION_SELLADA)}, a_la_transcripcion=False)
    for k, ll in enumerate(plan["llamadas"], 1):
        if plan.get("falla_tras") is not None and k > plan["falla_tras"]:
            tabla = G.tabla_procesos()
            for q in G.descendientes(os.getpid(), tabla):
                if q in tabla and tabla[q][0] == os.getpid() and "servidor_mcp" in tabla[q][1]:
                    os.kill(q, signal.SIGKILL)          # el servidor muere sin escribir su línea `fin`
            guardar_transcripcion()
            sys.stderr.write("CLI falso: la sesión falla a mitad, por su plan\n")
            os._exit(1)
        tid = f"toolu_falso_{sid[:8]}_{k}"
        emitir({"type": "assistant", "uuid": f"{sid[:8]}-a{k}",
                "message": {"id": f"msg_falso_{sid[:8]}_{k}", "model": model, "role": "assistant", "stop_reason": "tool_use",
                            "content": [{"type": "tool_use", "id": tid, "name": f"mcp__{srv}__{ll['tool']}", "input": ll["input"]}],
                            "usage": {"input_tokens": 10, "output_tokens": 50}}})
        r = cli.llamar_crudo(ll["tool"], ll["input"])
        texto = "".join(getattr(c, "text", "") for c in r.content)
        emitir({"type": "user", "uuid": f"{sid[:8]}-u{k}",
                "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "is_error": bool(r.isError),
                                                         "content": [{"type": "text", "text": texto}]}]}})
    cli.__exit__(None, None, None)                       # el servidor escribe su línea `fin`
    final = json.dumps({"respuesta": "respuesta de la corrida en seco (CLI falso, sin modelo)", "citas": [],
                        "respondible": False}, ensure_ascii=False)
    n = len(plan["llamadas"])
    emitir({"type": "assistant", "uuid": f"{sid[:8]}-a{n + 1}",
            "message": {"id": f"msg_falso_{sid[:8]}_{n + 1}", "model": model, "role": "assistant", "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": final}], "usage": {"input_tokens": 10, "output_tokens": 50}}})
    u = plan.get("uso") or {"inputTokens": 0, "outputTokens": 0, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}
    costo = (u["inputTokens"] * PRECIO["input"] + u["cacheCreationInputTokens"] * PRECIO["cache_write_5m"]
             + u["cacheReadInputTokens"] * PRECIO["cache_read"] + u["outputTokens"] * PRECIO["output"]) / 1e6
    emitir({"type": "result", "subtype": "success", "is_error": False, "num_turns": n + 1, "result": final,
            "session_id": sid, "total_cost_usd": round(costo, 6), "permission_denials": [],
            "modelUsage": {model: u | {"costUSD": round(costo, 6)}}}, a_la_transcripcion=False)
    guardar_transcripcion()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
