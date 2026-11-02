#!/usr/bin/env python3
"""servidor_mcp_kg_nav.py — Servidor MCP (stdio) del brazo del grafo con las herramientas de navegación de U-NAV-DISENO,
N5 (mandato firmado en c2ddf5f7, §3 y §4, N5): las tres herramientas de hoy MÁS las de las familias que declara la
config (`familias`: una lista con números de 1 a 5; las configuraciones de N6 «todas» y «todas menos una familia»).

Las tres herramientas de hoy no cambian: su definición es la de `harness.TOOLS` y su despacho y su serialización son
los de servidor_mcp_kg.py (abrir_backend, despachar, serializar_payload), importados sin editar; la cadena que recibe
el agente es byte a byte la del servidor de hoy (lo prueba selftest_familias_nav.py). Las de las familias 1 a 5
(familias_nav.py) devuelven tablas de texto, no JSON.

Además de lo que verifica servidor_mcp_kg.abrir_backend (sha256 del kg.json y KG_Meta), al arrancar verifica: que el
grafo se haya cargado con el cargador de N5 (KG_Meta.props_aristas); el sha256 del manifiesto del índice por punto y de
cada archivo que declara; la matriz densa; y los hubs (umbral, cantidad y sha256 de sus ids) contra la config. Si algo
no coincide, no expone nada.

La familia 1 necesita el venv del servidor de fragmentos para codificar las consultas (codificador_consultas.py): su
python sale de la variable de entorno que nombra la config (`denso.python_env`, BANCO_VENV_VECTOR) más /bin/python.

R1: el mismo log íntegro por llamada que servidor_mcp_kg.py (comun_banco.LogR1).
Uso: python3 -B servidor_mcp_kg_nav.py --config config_mcp_kg_nav_<grafo>.json
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import servidor_mcp_kg as BASE  # noqa: E402  (agrega banco, neo4j, evaluacion y gate al path; sin editar)
from comun_banco import LogR1, cargar_config, rel_repo, serializar_payload, versiones_entorno  # noqa: E402
import familias_nav as FN  # noqa: E402

VERSION_SERVIDOR = "1.0-nav"
NOMBRE_SERVIDOR = "mcp_kg"
CONFIG_DEFAULT = AQUI / "config_mcp_kg_nav_acumulado.json"


def tools_de(familias: list[int]) -> list[dict]:
    """Las tres de hoy (harness.TOOLS, tal cual) y, en el orden de TOOLS_NAV, las de las familias pedidas."""
    fams = set(familias)
    if not fams <= {1, 2, 3, 4, 5}:
        raise SystemExit(f"ABORTO: familias fuera de 1 a 5 en la config: {sorted(fams)}")
    return list(BASE.TOOLS) + [t for t in FN.TOOLS_NAV if t["familia"] in fams]


def abrir_navegador(config: dict, index) -> FN.Navegador:
    from grafos import GRAFOS  # noqa: E402  (data/experiment/neo4j)
    if config.get("rrf_k", FN.RRF_K) != FN.RRF_K:
        raise SystemExit(f"ABORTO: la config declara rrf_k={config['rrf_k']} y la familia 1 usa k={FN.RRF_K} (fijo)")
    den = config.get("denso") or {}
    python_vector = None
    if den.get("requerido"):
        base = os.environ.get(den["python_env"], "")
        if not base:
            raise SystemExit(f"ABORTO: la config pide el denso y {den['python_env']} no está definido")
        python_vector = str(Path(base) / "bin" / "python")
    return FN.Navegador(index.driver, GRAFOS[config["grafo"]]["label"], (AQUI / config["indice_puntos"]).resolve(),
                        sha256_manifiesto=config["sha256_manifiesto_indice"], python_vector=python_vector,
                        hubs_esperados=config.get("hubs_esperados"))


def construir_servidor(config_path: Path):
    import mcp.types as types
    from mcp.server.lowlevel import Server

    config, config_sha = cargar_config(config_path)
    index, fuente = BASE.abrir_backend(config)
    tools = tools_de(config.get("familias", []))
    nombres_nav = {t["name"] for t in tools if "familia" in t}
    nav = abrir_navegador(config, index) if nombres_nav else None
    fuente = fuente | {"familias": sorted(set(config.get("familias", []))), "tools": [t["name"] for t in tools]}
    if nav is not None:
        fuente["navegacion"] = nav.descripcion_fuente()
    log = LogR1(NOMBRE_SERVIDOR, VERSION_SERVIDOR, config, config_sha, fuente,
                versiones_entorno(["mcp", "neo4j", "numpy"]) | {"config_path": rel_repo(config_path)})
    server = Server(NOMBRE_SERVIDOR, version=VERSION_SERVIDOR)

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        # La anotación de tamaño del resultado (D-6), la misma de los otros dos servidores del banco, con su valor.
        return [types.Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"],
                           _meta={"anthropic/maxResultSizeChars": BASE.TOPE_CARACTERES_RESULTADO}) for t in tools]

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict):
        t0 = time.perf_counter()
        n, call_id = log.nuevo_call_id()
        try:
            rpc_id = server.request_context.request_id
        except LookupError:
            rpc_id = None
        try:
            if name in nombres_nav:
                out = FN.despachar(nav, name, arguments or {})
            else:
                out = serializar_payload(BASE.despachar(index, name, arguments or {}))
        except Exception as e:
            log.llamada(n, call_id, rpc_id, name, arguments or {}, None, t0, error=f"{type(e).__name__}: {e}")
            raise
        log.llamada(n, call_id, rpc_id, name, arguments or {}, out, t0)
        return [types.TextContent(type="text", text=out)]

    return server, log, nav


async def servir(config_path: Path) -> None:
    from mcp.server.stdio import stdio_server
    server, log, nav = construir_servidor(config_path)
    BASE._fin_ante_senal(log)
    try:
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())
    finally:
        if nav is not None and nav.denso is not None:
            nav.denso.cerrar()
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
