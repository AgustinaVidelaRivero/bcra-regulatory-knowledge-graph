#!/usr/bin/env python3
"""armar_config_agentes_b63.py (v2/b2, etapa b2) — La configuración de agentes de B6.3 (config_agentes_b63.json, de esta carpeta), armada
desde la configuración sellada de N7 (n7/n7_configuracion_sellada.json, `dd425094…`), que se controla por los sha256 que trae, antes de
escribir nada. USD 0: no llama a ningún modelo ni levanta nada; solo lee archivos del banco.

Los tres brazos, con sus roles (pre-registro de B6.3, §4, y la decisión de la autora del 26/10/2026, 19:00:06: «la del grafo de N7, la
principal de fragmentos y el denso»):
  · kg, el grafo: el JSON de MCP y la config del servidor de N7 (n7/), su bloque (n7/bloque_tools_kg_n7.txt) y sus herramientas
    esperadas (las del registro de N7); los archivos de su servidor, los de la configuración elegida en N6 (T-F6) en
    n6/config_agentes_n6.json;
  · fragmentos_hibrida, la principal de fragmentos: la híbrida, por el registro de N7 (F1), su config y su JSON de MCP del grafo evaluado
    (mcp_vector/), y el bloque de fragmentos de N7 (n7/bloque_tools_fragmentos_n7.txt, el de N6 byte a byte);
  · fragmentos_denso: su config y su JSON de MCP del grafo evaluado, por el registro de N7. Su bloque no lo nombra el registro de N7: es
    el del brazo denso de A2.1 (a2_1/config_agentes_a2_1.json, `agentes/bloque_tools_vector.txt`), porque el pre-registro de B6.3, §4,
    dice que el sistema por fragmentos es «el de A2.1». Se declara.
La plantilla de N7 (la de N6, byte a byte), el R5 del registro de N7 (30, 32 y 1,80) y la forma de paralelo/config_agentes_n6_prueba.json
(base, versión sellada del CLI, modelo, modo, brazos, prompt, corte_R5 y env_por_sesion). El servidor del grafo apunta a
bolt://127.0.0.1:47687 (decisión del 27/10/2026, 10:24:11) por la lista cerrada del entorno de la sesión (agentes/lanzar_agente.py,
ENTORNO_PERMITIDAS: NEO4J_URI pasa del runner, que la compara con la de la entrada).

Uso: python3 -I -B armar_config_agentes_b63.py [--verificar] [--controles <json>]
  sin argumentos, escribe config_agentes_b63.json (frena si existe y difiere); con --verificar, la rearma en memoria y la compara;
  con --controles, escribe además cada control de un sha256 contra el registro de N7 (ruta, el del registro, el que da).
Imprime solo nombres, cuentas y sha256.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b63/v2/b2
BANCO_DIR = AQUI.parents[2]
N7 = "n7/n7_configuracion_sellada.json"
N7_SHA256 = "dd425094a287491e628d839161a12a1b140eaeeea5843d68b573c8895df0a571"
N6_AGENTES = "n6/config_agentes_n6.json"
A21_AGENTES = "a2_1/config_agentes_a2_1.json"
SALIDA = AQUI / "config_agentes_b63.json"
URI_B63 = "bolt://127.0.0.1:47687"
R5_N7 = {"tope_tool_calls_prompt": 30, "max_turns": 32, "max_budget_usd": 1.8}


class Freno(Exception):
    pass


def sha(rel: str) -> str:
    return hashlib.sha256((BANCO_DIR / rel).read_bytes()).hexdigest()


def leer(rel: str) -> dict:
    return json.loads((BANCO_DIR / rel).read_text(encoding="utf-8"))


def controlar(rel: str, esperado: str, controles: list) -> dict:
    s = sha(rel) if (BANCO_DIR / rel).is_file() else None
    controles.append({"ruta": rel, "sha256_del_registro": esperado, "sha256": s, "ok": s == esperado})
    if s != esperado:
        raise Freno(f"{rel}: da {str(s)[:12]}…, no el sha256 del registro de N7 {esperado[:12]}…")
    return {"ruta": rel, "sha256": s}


def armar() -> tuple[dict, list]:
    controles: list = []
    controlar(N7, N7_SHA256, controles)
    n7 = leer(N7)
    if n7.get("pendiente"):
        raise Freno(f"el registro de N7 trae algo pendiente: {n7['pendiente']}")
    if n7["regla_N4_5"]["del_analisis"]["elegida"] != "T-F6" or not n7["regla_N4_5"]["iguales"]:
        raise Freno("el registro de N7 no elige T-F6 con la regla otra vez igual")
    if n7["R5"]["valores"] != R5_N7 or n7["R5"]["sube"]:
        raise Freno(f"el R5 del registro de N7 no es 30, 32 y 1,80: {n7['R5']['valores']}")
    if not (n7["F1"]["entra_la_hibrida"] and n7["F1"]["principal_de_fragmentos"] == "hibrida"):
        raise Freno("el registro de N7 no da la híbrida como principal de fragmentos")
    controlar(n7["analisis_n6"]["ruta"].replace("data/experiment/banco_mcp/", ""), n7["analisis_n6"]["sha256"], controles)
    g = n7["brazo_grafo"]
    for nombre, s in g["archivos"].items():
        controlar(f"n7/{nombre}", s, controles)
    if n7["plantilla"]["sha256"] != g["archivos"]["plantilla_prompt_n7.txt"]:
        raise Freno("la plantilla de N7 no es la del registro")
    if sha(n7["plantilla"]["de_N6"]) != n7["plantilla"]["sha256"]:
        raise Freno("la plantilla de N7 no es la de N6 byte a byte")
    cfg_kg = leer("n7/config_mcp_kg_n7_evaluado.json")
    if (cfg_kg["kg_sha256_esperado"] != g["kg_sha256"] or cfg_kg["grafo"] != g["grafo"]
            or cfg_kg["sha256_manifiesto_indice"] != g["indice_puntos"]["sha256_manifiesto"]
            or cfg_kg["hubs_esperados"] != g["hubs_esperados"] or cfg_kg["familias"] != g["familias"]):
        raise Freno("la config del servidor de N7 no da el grafo, el índice, los hubs o las familias del registro")
    controlar(f"mcp_kg/{g['indice_puntos']['ruta']}/manifiesto.json", g["indice_puntos"]["sha256_manifiesto"], controles)
    mcp_kg = leer("n7/mcp_kg_n7_evaluado.json")["mcpServers"]
    if list(mcp_kg) != ["kg"] or not mcp_kg["kg"]["args"][1].endswith(g["servidor"]) or \
            not mcp_kg["kg"]["args"][3].endswith("n7/config_mcp_kg_n7_evaluado.json"):
        raise Freno("el JSON de MCP de N7 no sirve el servidor del registro con su config")
    f = n7["brazo_fragmentos"]
    for clave in ("principal", "denso"):
        controlar(f[clave]["config"], f[clave]["sha256"], controles)
        controlar(f[clave]["mcp"], f[clave]["sha256_mcp"], controles)
    if leer(f["principal"]["config"])["afinidad"] != "hibrida" or leer(f["denso"]["config"])["afinidad"] != "denso":
        raise Freno("las configs de fragmentos no son la híbrida y el denso")
    for clave in ("principal", "denso"):
        if list(leer(f[clave]["mcp"])["mcpServers"]) != ["fragmentos"]:
            raise Freno(f"el JSON de MCP de {clave} no sirve el servidor «fragmentos»")
    if sha(f["bloque_tools_de_N6"]) != g["archivos"]["bloque_tools_fragmentos_n7.txt"]:
        raise Freno("el bloque de fragmentos de N7 no es el de N6 byte a byte")
    if sha(n7["bloques_de_N6"]["grafo"]) != g["archivos"]["bloque_tools_kg_n7.txt"]:
        raise Freno("el bloque del grafo de N7 no es el de N6 byte a byte")
    n6 = leer(N6_AGENTES)
    tf6, hib6 = n6["brazos"]["kg_T-F6"], n6["brazos"]["fragmentos_hibrida"]
    if tf6["tools_esperadas"] != g["herramientas_esperadas"] or tf6["allowed_tools"] != "mcp__kg__*":
        raise Freno("las herramientas esperadas de T-F6 en N6 no son las del registro de N7")
    a21 = leer(A21_AGENTES)
    den21 = a21["brazos"]["fragmentos_denso"]
    base = n6["base"]
    if sha(base["ruta"]) != base["sha256"]:
        raise Freno("la base de la configuración de agentes de N6 no es la declarada")
    fuentes = {"n7": {"ruta": N7, "sha256": N7_SHA256}, "n6_config_agentes": {"ruta": N6_AGENTES, "sha256": sha(N6_AGENTES)},
               "a2_1_config_agentes": {"ruta": A21_AGENTES, "sha256": sha(A21_AGENTES)},
               "forma": {"ruta": "paralelo/config_agentes_n6_prueba.json", "sha256": sha("paralelo/config_agentes_n6_prueba.json")}}
    cfg = {
        "unidad": "B6.3 — la configuración de agentes de los tres brazos de B6.3, armada desde la configuración sellada de N7 "
                  "(b63/v2/b2/armar_config_agentes_b63.py)",
        "por_que": ("El testigo de aislamiento corre con la configuración sellada de B6.3 (la del grafo de N7, la principal de fragmentos "
                    "y el denso) y no con la de prueba de N6 (decisión de la autora del 26/10/2026, 19:00:06). Tiene la forma de "
                    "paralelo/config_agentes_n6_prueba.json y los archivos que nombra el registro de N7, controlados por su sha256."),
        "base": {"ruta": base["ruta"], "sha256": base["sha256"],
                 "que_se_hereda": "modelo, modo del harness, versión sellada del CLI, flags y R5 (30, 32 y 1,80): los de A2.2 (N4, §1), "
                                  "como en N6. Lo que cambia: los brazos (los de B6.3) y la plantilla (la de N7)."},
        "fuentes": fuentes,
        "claude_code_version_sellada": n6["claude_code_version_sellada"], "modelo": n6["modelo"], "modo_harness": n6["modo_harness"],
        "brazos": {
            "kg": {"rol": "grafo", "configuracion_n7": n7["regla_N4_5"]["del_analisis"]["elegida"], "familias": g["familias"],
                   "carga_codificador": g["carga_el_codificador"], "mcp_config": "n7/mcp_kg_n7_evaluado.json", "servidor": "kg",
                   "bloque_tools": "n7/bloque_tools_kg_n7.txt", "allowed_tools": "mcp__kg__*",
                   "tools_esperadas": g["herramientas_esperadas"],
                   "tools_esperadas_nota": "en el orden en que las lista el CLI en system/init (alfabético), porque armar_meta compara las listas",
                   "config_servidor": "n7/config_mcp_kg_n7_evaluado.json", "archivos_servidor": tf6["archivos_servidor"],
                   "venv": tf6["venv"], "grafo": g["grafo"], "kg_sha256": g["kg_sha256"]},
            "fragmentos_hibrida": {"rol": "fragmentos_principal", "afinidad": "hibrida", "configuracion_n6": f["configuracion_n6"],
                                   "carga_codificador": hib6["carga_codificador"], "mcp_config": f["principal"]["mcp"],
                                   "servidor": "fragmentos", "bloque_tools": "n7/bloque_tools_fragmentos_n7.txt",
                                   "allowed_tools": "mcp__fragmentos__*", "tools_esperadas": hib6["tools_esperadas"],
                                   "config_servidor": f["principal"]["config"], "archivos_servidor": hib6["archivos_servidor"],
                                   "venv": "BANCO_VENV_VECTOR"},
            "fragmentos_denso": {"rol": "fragmentos_denso", "afinidad": "denso", "carga_codificador": True,
                                 "mcp_config": f["denso"]["mcp"], "servidor": "fragmentos", "bloque_tools": den21["bloque_tools"],
                                 "bloque_tools_nota": ("el registro de N7 no nombra el bloque del denso: es el del brazo denso de A2.1 "
                                                       "(a2_1/config_agentes_a2_1.json), por el pre-registro de B6.3, §4 («el de A2.1»)"),
                                 "allowed_tools": "mcp__fragmentos__*", "tools_esperadas": den21["tools_esperadas"],
                                 "config_servidor": f["denso"]["config"], "archivos_servidor": den21["archivos_servidor"],
                                 "venv": "BANCO_VENV_VECTOR"}},
        "prompt": {"plantilla": "n7/plantilla_prompt_n7.txt", "sha256": n7["plantilla"]["sha256"],
                   "como_se_pasa": "como en la base: argumento de `claude -p <prompt>`; el prompt de sistema de Claude Code no se toca.",
                   "diferencia_entre_brazos": "exclusivamente el bloque {{BLOQUE_TOOLS}}: la plantilla es la misma en los tres"},
        "corte_R5": {"max_turns": R5_N7["max_turns"], "tope_tool_calls_en_prompt": R5_N7["tope_tool_calls_prompt"],
                     "max_budget_usd_por_sesion": R5_N7["max_budget_usd"],
                     "nota": "el R5 del registro de N7 (R5.valores; no sube): 30, 32 y 1,80, igual en todas las sesiones de B6.3."},
        "env_por_sesion": {
            "BANCO_REPO": "raíz del repo (expansión en los JSON de MCP)",
            "BANCO_VENV_VECTOR": "venv 3.12 del servidor de fragmentos; en los tres brazos: el del grafo lo usa para su codificador de "
                                 "consultas (n7/config_mcp_kg_n7_evaluado.json, denso.python_env)",
            "BANCO_LOG_R1": "ruta del log R1 de ESA sesión (un archivo por sesión)",
            "BANCO_SESION_TAG": "id de la sesión (se copia a cada línea del log)",
            "NEO4J_URI": f"{URI_B63}: el Neo4j propio de los índices (decisión de la autora del 27/10/2026, 10:24:11); pasa por la lista "
                         "cerrada (agentes/lanzar_agente.py, ENTORNO_PERMITIDAS) desde el runner, que la compara con la de la entrada",
            "MCP_TIMEOUT": "180000"},
        "sha256_de_cada_archivo": {r: sha(r) for r in sorted({
            "n7/mcp_kg_n7_evaluado.json", "n7/config_mcp_kg_n7_evaluado.json", "n7/bloque_tools_kg_n7.txt",
            "n7/bloque_tools_fragmentos_n7.txt", "n7/plantilla_prompt_n7.txt", f["principal"]["mcp"], f["principal"]["config"],
            f["denso"]["mcp"], f["denso"]["config"], den21["bloque_tools"], *tf6["archivos_servidor"], *hib6["archivos_servidor"],
            *den21["archivos_servidor"]})}}
    return cfg, controles


def main(argv: list[str]) -> int:
    try:
        cfg, controles = armar()
    except Freno as ex:
        print(f"FRENO (USD 0): {ex}")
        return 10
    nuevo = json.dumps(cfg, ensure_ascii=False, indent=1) + "\n"
    if "--controles" in argv:
        Path(argv[argv.index("--controles") + 1]).write_text(json.dumps(controles, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if "--verificar" in argv:
        igual = SALIDA.is_file() and SALIDA.read_text(encoding="utf-8") == nuevo
        print(json.dumps({"controles_del_registro_de_N7": f"{sum(c['ok'] for c in controles)} de {len(controles)}",
                          "config_agentes_b63_igual_a_la_rearmada": igual}, ensure_ascii=False))
        return 0 if igual else 1
    if SALIDA.exists() and SALIDA.read_text(encoding="utf-8") != nuevo:
        print("FRENO (USD 0): config_agentes_b63.json ya existe y difiere de la rearmada")
        return 10
    SALIDA.write_text(nuevo, encoding="utf-8")
    print(json.dumps({"controles_del_registro_de_N7": f"{sum(c['ok'] for c in controles)} de {len(controles)}",
                      "brazos": {b: x["rol"] for b, x in cfg["brazos"].items()},
                      "config_agentes_b63": hashlib.sha256(nuevo.encode("utf-8")).hexdigest()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
