#!/usr/bin/env python3
"""servidor_mcp_juguete.py — El servidor MCP de juguete de la corrida en seco de B6.3 (stdio, el SDK `mcp` de bajo nivel, como los
servidores del banco). No lee ningún grafo ni ningún índice: sus herramientas devuelven un texto fijo de juguete. Escribe el log R1
del banco (comun_banco.LogR1), con su línea `fin` al cerrar, así la meta de cada sesión se arma igual que con un servidor real.

  --tipo kg          buscar_nodos, buscar_puntos y ver_nodo;
  --tipo fragmentos  buscar_pasajes.
Una herramienta que no es de su tipo da un resultado con error (y se registra), sin cortar la sesión.
"""
from __future__ import annotations

import argparse
import asyncio
import signal
import os
import time
from pathlib import Path
import sys

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent.parent
if str(BANCO_DIR) not in sys.path:
    sys.path.insert(0, str(BANCO_DIR))
from comun_banco import LogR1, cargar_config, rel_repo, serializar_payload, versiones_entorno  # noqa: E402

VERSION = "juguete-1"
ESQUEMA = {"type": "object", "properties": {"consulta": {"type": "string"}, "limite": {"type": "integer"}, "id": {"type": "string"}}}
TOOLS = {"kg": ("buscar_nodos", "buscar_puntos", "ver_nodo"), "fragmentos": ("buscar_pasajes",)}


def resultado(tipo: str, nombre: str, args: dict) -> dict:
    return {"juguete": True, "tool": nombre, "resultados": [{"id": f"juguete-{tipo}-{nombre}-1", "texto": "texto de juguete"}],
            "consulta": args.get("consulta")}


async def servir(tipo: str, config_path: Path) -> None:
    import mcp.types as types
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    config, config_sha = cargar_config(config_path)
    log = LogR1(f"juguete_{tipo}", VERSION, config, config_sha, {"juguete": True}, versiones_entorno(["mcp"])
                | {"config_path": rel_repo(config_path)})

    def al_terminar(signum, frame):
        try:
            log.fin()
        finally:
            os._exit(0)
    signal.signal(signal.SIGTERM, al_terminar)
    signal.signal(signal.SIGINT, al_terminar)
    server = Server(f"juguete_{tipo}", version=VERSION)

    @server.list_tools()
    async def _list_tools() -> list:
        return [types.Tool(name=n, description=f"herramienta de juguete {n}", inputSchema=ESQUEMA) for n in TOOLS[tipo]]

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict):
        t0 = time.perf_counter()
        n, call_id = log.nuevo_call_id()
        args = arguments or {}
        if name not in TOOLS[tipo]:
            out = serializar_payload({"error": f"tool desconocida: {name}"})
            log.llamada(n, call_id, None, name, args, out, t0, error="tool desconocida")
            return [types.TextContent(type="text", text=out)]
        out = serializar_payload(resultado(tipo, name, args))
        log.llamada(n, call_id, None, name, args, out, t0)
        return [types.TextContent(type="text", text=out)]

    try:
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())
    finally:
        if not log.cerrado:
            log.fin()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", choices=sorted(TOOLS), required=True)
    ap.add_argument("--config", type=Path, required=True)
    a = ap.parse_args()
    asyncio.run(servir(a.tipo, a.config.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
