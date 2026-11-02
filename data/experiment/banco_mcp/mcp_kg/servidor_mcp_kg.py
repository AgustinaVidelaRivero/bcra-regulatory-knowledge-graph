#!/usr/bin/env python3
"""servidor_mcp_kg.py — Servidor MCP (stdio) del brazo KG del banco (U-A2.0-banco, pieza i).

Expone las TRES tools del harness congelado con la FIRMA v1 (laudo R2, opción B):

    buscar_nodos(consulta, limite) / ver_nodo(id) / ver_vecinos(id, direccion)

Nada se reimplementa:
  · nombre, descripción e input_schema de cada tool se IMPORTAN de
    `harness.TOOLS` (cuarteto sellado; harness.py:242-284) tal cual;
  · el despacho replica línea por línea `GraphAgent._run_tool` del harness
    (mismos `args.get` y mismos defaults: limite 10, direccion "ambas");
  · el backend es `Neo4jIndex` (data/experiment/neo4j, A1.1) en el modo que
    fija la config sellada (`fulltext` = BM25/Lucene, consistente con la base
    C10 laudada), o `GraphIndex` del harness sobre un kg.json (`memoria`) —
    este último existe para repetir la demostración por clase del gate sobre
    el grafo de juguete A TRAVÉS del mismo servidor y el mismo transporte;
  · la respuesta es UN bloque de texto con `json.dumps(result, ensure_ascii=False)`
    (harness.py:512): la cadena que el agente recibe es byte-idéntica a la que
    recibía el agente del harness. Sin structuredContent, sin campos extra:
    cualquier agregado cambiaría `output_chars` y rompería el replay estándar.

Fuera del banco, por el laudo R2: paginación, filtro por relación, `contexto_de`.

R1: cada llamada se registra ÍNTEGRA (entrada y salida) en el log JSONL de
`comun_banco.LogR1`, con call_id, n, id JSON-RPC, timestamp y sha de config.
R7: el mapa n -> tool_use_id lo arma el adaptador sobre ese `n`.

Validación de entrada: DESACTIVADA a propósito (`validate_input=False`): el
harness no validaba y toleraba, p. ej., `limite` no entero (cae a 10 en
`Neo4jIndex._limite`, misma expresión que `GraphIndex`). Validar acá
introduciría un comportamiento que el harness no tenía.

Uso (lo lanza Claude Code según agentes/mcp_kg.json; también sirve a mano):
    python3 -B servidor_mcp_kg.py --config config_mcp_kg.json
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
EXPERIMENT_DIR = BANCO_DIR.parent
NEO4J_DIR = EXPERIMENT_DIR / "neo4j"
EVAL_DIR = EXPERIMENT_DIR / "evaluacion"
GATE_CODE = BANCO_DIR / "gate" / "code"
for _p in (str(BANCO_DIR), str(NEO4J_DIR), str(EVAL_DIR), str(GATE_CODE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from comun_banco import (LogR1, cargar_config, rel_repo, serializar_payload,  # noqa: E402
                         sha256_file, versiones_entorno)
from harness import TOOLS  # noqa: E402  (cuarteto sellado: solo import)

VERSION_SERVIDOR = "1.0"
NOMBRE_SERVIDOR = "mcp_kg"
CONFIG_DEFAULT = AQUI / "config_mcp_kg.json"
# Tope en caracteres del resultado de cada tool en Claude Code (D-6). Sin
# `_meta["anthropic/maxResultSizeChars"]`, el CLI sellado (2.1.241) guarda en
# disco todo resultado de más de 50.000 caracteres; con la anotación, el umbral
# es el valor anotado (hasta 500.000) y el CLI no le aplica a la tool el tope en
# tokens (MAX_MCP_OUTPUT_TOKENS). Mismo valor en todas las tools de los dos
# servidores del banco.
TOPE_CARACTERES_RESULTADO = 200000
TOOLS_V1 = {t["name"]: t for t in TOOLS}
assert set(TOOLS_V1) == {"buscar_nodos", "ver_nodo", "ver_vecinos"}


# --------------------------------------------------------------------------- #
# Backend                                                                      #
# --------------------------------------------------------------------------- #
def abrir_backend(config: dict) -> tuple[object, dict]:
    """Devuelve (index, descripción_de_la_fuente). Verifica el sha del grafo
    ANTES de exponer nada; aborta si difiere."""
    backend = config["backend"]
    if backend == "neo4j":
        from conexion import abrir_driver          # data/experiment/neo4j (import)
        from grafos import GRAFOS, verificar_sha
        from neo4j_index import Neo4jIndex
        grafo = config["grafo"]
        sha_archivo = verificar_sha(grafo)          # aborta si el kg.json no es el sellado
        driver = abrir_driver()
        with driver.session() as s:
            meta = s.run("MATCH (m:KG_Meta {grafo: $g}) RETURN m.kg_sha256 AS sha, "
                         "m.n_nodos AS n, m.n_aristas AS a", g=grafo).single()
        if meta is None or meta["sha"] != sha_archivo or meta["sha"] != config["kg_sha256_esperado"]:
            raise SystemExit(
                f"ABORTO: KG_Meta.kg_sha256 de {grafo} = {meta and meta['sha']} ; archivo = "
                f"{sha_archivo} ; esperado por config = {config['kg_sha256_esperado']}. "
                "El grafo cargado en Neo4j no es el sellado: no se expone nada.")
        idx = Neo4jIndex(driver, grafo=grafo, modo=config["modo"])
        fuente = {"backend": "neo4j", "grafo": grafo, "modo": config["modo"],
                  "indice_fulltext": idx.indice, "kg_path": rel_repo(GRAFOS[grafo]["path"]),
                  "kg_sha256": sha_archivo, "kg_meta_sha256": meta["sha"],
                  "n_nodos": meta["n"], "n_aristas": meta["a"],
                  "neo4j_index_sha256": sha256_file(NEO4J_DIR / "neo4j_index.py")}
        return idx, fuente
    if backend == "memoria":
        import tools_juguete as TJ                  # gate/code (sellado: solo import)
        kg_path = (BANCO_DIR.parents[2] / config["kg_path"]).resolve()
        sha = sha256_file(kg_path)
        if sha != config["kg_sha256_esperado"]:
            raise SystemExit(f"ABORTO: sha256({rel_repo(kg_path)}) = {sha} != esperado "
                             f"{config['kg_sha256_esperado']}")
        idx = TJ.cargar_index(kg_path)              # harness.GraphIndex sobre el kg.json
        fuente = {"backend": "memoria", "kg_path": rel_repo(kg_path), "kg_sha256": sha,
                  "n_nodos": len(idx.kg.nodes), "n_aristas": len(idx.kg.edges)}
        return idx, fuente
    raise SystemExit(f"backend desconocido: {backend!r}")


def despachar(index, name: str, args: dict):
    """Réplica exacta de `GraphAgent._run_tool` (harness.py)."""
    if name == "buscar_nodos":
        return index.buscar_nodos(args.get("consulta", ""), args.get("limite", 10))
    if name == "ver_nodo":
        return index.ver_nodo(args.get("id", ""))
    if name == "ver_vecinos":
        return index.ver_vecinos(args.get("id", ""), args.get("direccion", "ambas"))
    return {"error": f"tool desconocida: {name}"}


# --------------------------------------------------------------------------- #
# Servidor MCP                                                                 #
# --------------------------------------------------------------------------- #
def construir_servidor(config_path: Path):
    import mcp.types as types
    from mcp.server.lowlevel import Server

    config, config_sha = cargar_config(config_path)
    index, fuente = abrir_backend(config)
    log = LogR1(NOMBRE_SERVIDOR, VERSION_SERVIDOR, config, config_sha, fuente,
                versiones_entorno(["mcp", "neo4j"]) | {"config_path": rel_repo(config_path)})

    server = Server(NOMBRE_SERVIDOR, version=VERSION_SERVIDOR)

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        # Definiciones verbatim del harness (nombre, descripción, input_schema).
        return [types.Tool(name=t["name"], description=t["description"],
                           inputSchema=t["input_schema"],
                           _meta={"anthropic/maxResultSizeChars": TOPE_CARACTERES_RESULTADO}) for t in TOOLS]

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict):
        t0 = time.perf_counter()
        n, call_id = log.nuevo_call_id()
        try:
            rpc_id = server.request_context.request_id
        except LookupError:
            rpc_id = None
        try:
            out = serializar_payload(despachar(index, name, arguments or {}))
        except Exception as e:  # el error también se registra íntegro
            log.llamada(n, call_id, rpc_id, name, arguments or {}, None, t0,
                        error=f"{type(e).__name__}: {e}")
            raise
        log.llamada(n, call_id, rpc_id, name, arguments or {}, out, t0)
        return [types.TextContent(type="text", text=out)]

    return server, log


def _fin_ante_senal(log):
    """C2 (laudo fase B): Claude Code termina el proceso del servidor al cerrar la
    sesión (SIGTERM tras cerrar stdin). Sin esto el `finally` no corre y el log
    R1 queda sin línea `fin` (medido en la corrida 1: 6/6 sesiones del vectorial)."""
    import os
    import signal

    def _handler(signum, frame):
        try:
            log.fin()
        finally:
            os._exit(0)
    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)


async def servir(config_path: Path) -> None:
    from mcp.server.stdio import stdio_server
    server, log = construir_servidor(config_path)
    _fin_ante_senal(log)
    try:
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())
    finally:
        if not log.cerrado:
            log.fin()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    a = ap.parse_args()
    asyncio.run(servir(a.config.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
