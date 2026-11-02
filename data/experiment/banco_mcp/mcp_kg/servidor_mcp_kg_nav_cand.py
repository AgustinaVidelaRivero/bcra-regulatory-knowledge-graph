#!/usr/bin/env python3
"""servidor_mcp_kg_nav_cand.py — Servidor MCP (stdio) del brazo del grafo de N6 de U-NAV-DISENO (protocolo de N4, sellado
en f69e95ea, §2 y §9): el de la navegación de HEAD (servidor_mcp_kg_nav.py, importado sin editarlo) con la candidata de la
familia 2, `ver_descendientes` (familias_nav_cand.py: NavegadorCand, despachar_cand y TOOLS_NAV_CAND).

Las herramientas que sirve salen de las familias de su config (`familias`, de 1 a 5, como en HEAD): las tres de hoy
(harness.TOOLS, siempre) y, en el orden de TOOLS_NAV_CAND, las de las familias pedidas. `ver_descendientes` es de la
familia 2: va con `ver_punto`. Con `familias` vacía sirve solo las tres de hoy (la base, B) y no abre el navegador.

Lo que no cambia respecto del servidor de HEAD:
  · las tres de hoy: su definición (harness.TOOLS), su despacho y su serialización son los de servidor_mcp_kg.py
    (BASE.despachar y serializar_payload); la cadena que recibe el agente es la del servidor de hoy;
  · lo que se controla al arrancar: lo de servidor_mcp_kg.abrir_backend (sha256 del kg.json y KG_Meta) y los del navegador
    (cargador de N5, manifiesto del índice por punto y sus archivos, matriz densa y hubs contra la config), que hace el
    constructor de familias_nav.Navegador, del que NavegadorCand hereda; rrf_k y el denso, como abrir_navegador de HEAD;
  · la validación de las familias (servidor_mcp_kg_nav.tools_de: fuera de 1 a 5 aborta);
  · la anotación de tamaño del resultado (D-6), el log R1 (comun_banco.LogR1), el fin ante una señal y el cierre del
    codificador de consultas.
Lo que cambia: el navegador es NavegadorCand, el despacho de las de las familias es despachar_cand (que le pasa a
familias_nav.despachar, tal cual, las seis de HEAD) y la lista suma `ver_descendientes` si la config trae la familia 2.

Uso: python3 -B servidor_mcp_kg_nav_cand.py --config <config de N6>
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

import servidor_mcp_kg_nav as NAV  # noqa: E402  (HEAD, sin editar: trae servidor_mcp_kg como NAV.BASE y familias_nav)
import familias_nav_cand as FNC  # noqa: E402  (HEAD, sin editar)
from comun_banco import LogR1, cargar_config, rel_repo, serializar_payload, versiones_entorno  # noqa: E402

BASE = NAV.BASE
FN = NAV.FN
VERSION_SERVIDOR = "1.0-nav-cand"
NOMBRE_SERVIDOR = NAV.NOMBRE_SERVIDOR
CONFIG_DEFAULT = AQUI / "config_mcp_kg_nav_acumulado.json"


def tools_de(familias: list[int]) -> list[dict]:
    """Las de servidor_mcp_kg_nav.tools_de (las tres de hoy y las de las familias pedidas, con su validación) y, si la
    familia 2 está, `ver_descendientes`: la lista de TOOLS_NAV_CAND filtrada por familia, en su orden."""
    tools = NAV.tools_de(familias)
    if 2 in set(familias):
        tools.append(FNC.TOOL_VER_DESCENDIENTES)
    esperada = list(BASE.TOOLS) + [t for t in FNC.TOOLS_NAV_CAND if t["familia"] in set(familias)]
    if [t["name"] for t in tools] != [t["name"] for t in esperada]:
        raise SystemExit("ABORTO: la lista de herramientas no es la de TOOLS_NAV_CAND filtrada por familia")
    return tools


def abrir_navegador(config: dict, index) -> FNC.NavegadorCand:
    """Como servidor_mcp_kg_nav.abrir_navegador, con NavegadorCand en lugar de familias_nav.Navegador."""
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
    return FNC.NavegadorCand(index.driver, GRAFOS[config["grafo"]]["label"], (AQUI / config["indice_puntos"]).resolve(),
                             sha256_manifiesto=config["sha256_manifiesto_indice"], python_vector=python_vector,
                             hubs_esperados=config.get("hubs_esperados"))


def despachar(nav, index, nombres_nav: set, name: str, arguments: dict) -> str:
    """La cadena que recibe el agente: las de las familias por despachar_cand; las tres de hoy, como el servidor de hoy."""
    if name in nombres_nav:
        return FNC.despachar_cand(nav, name, arguments or {})
    return serializar_payload(BASE.despachar(index, name, arguments or {}))


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
        # La anotación de tamaño del resultado (D-6), la misma de los otros servidores del banco, con su valor.
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
            out = despachar(nav, index, nombres_nav, name, arguments)
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
