#!/usr/bin/env python3
"""test_aislamiento.py — Aislamiento POR CAPACIDAD entre brazos (U-A2.0-banco,
entregable 4; R6). Un comando, costo USD 0 (modo init: ninguna petición llega a
la API; ver agentes/lanzar_agente.py).

  (a) inventario de tools efectivamente disponibles por brazo, leído del evento
      `system/init` de `claude -p` con la configuración sellada: las del KG no
      figuran en el vectorial y viceversa; ninguna tool built-in.
  (b) denegación de acceso a los artefactos del grafo desde el brazo vectorial:
      el agente no tiene NINGUNA tool de archivos ni de shell (Read/Glob/Grep/
      Bash/Edit/Write ausentes del inventario ⇒ no hay capacidad de leer
      kg.json, data/experiment/neo4j ni agente_v2); y el proceso del servidor
      vectorial no importa ningún módulo del grafo (verificación estática del
      código + `import neo4j` falla en su venv).
  (c) denegación de acceso al puerto de Neo4j desde el brazo vectorial: el
      agente no tiene tools de red ni shell; el venv del servidor vectorial no
      tiene driver bolt (`import neo4j` falla); intento de handshake bolt
      desde ese venv con la stdlib NO se realiza (no hay código que lo haga:
      se verifica que el servidor no abre sockets salientes — grep estático).
  (d) test positivo por brazo: el servidor figura `connected` con sus tools en
      `system/init`, y una llamada real por el MISMO JSON de MCP (expansión de
      variables idéntica) devuelve datos de su propia fuente (cliente falso).

La denegación en runtime (el agente INTENTA leer un archivo o abrir el puerto
y Claude Code lo rechaza) requiere un modelo: se ejercita end-to-end en fase B
y se registra en `permission_denials` de la traza.

Uso:
  BANCO_VENV_VECTOR=<venv 3.12> .venv/bin/python -B test_aislamiento.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
REPO_DIR = BANCO_DIR.parents[2]
if str(BANCO_DIR) not in sys.path:
    sys.path.insert(0, str(BANCO_DIR))
from cliente_falso import ClienteFalso          # noqa: E402
from comun_banco import rel_repo, sha256_file   # noqa: E402

LANZADOR = BANCO_DIR / "agentes" / "lanzar_agente.py"
CFG = json.loads((BANCO_DIR / "agentes" / "config_agentes.json").read_text(encoding="utf-8"))
TOOLS_ARCHIVOS_SHELL_RED = {"Read", "Glob", "Grep", "Bash", "Edit", "Write", "MultiEdit", "NotebookEdit",
                            "WebFetch", "WebSearch", "Agent", "Task", "LS"}
ARTEFACTOS_GRAFO = ["data/experiment/grafo_v2/reensamblado_v3/kg.json", "data/experiment/neo4j", "agente_v2"]


def expandir(s: str, env: dict) -> str:
    def rep(m):
        var, default = m.group(1), m.group(2)
        return env.get(var, default if default is not None else "")
    return re.sub(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}", rep, s)


def cmd_desde_mcp_json(p: Path, env: dict) -> tuple[list[str], dict]:
    d = json.loads(p.read_text(encoding="utf-8"))["mcpServers"]
    (nombre, s), = d.items()
    cmd = [expandir(s["command"], env)] + [expandir(a, env) for a in s.get("args", [])]
    e = {k: expandir(v, env) for k, v in (s.get("env") or {}).items()}
    return cmd, e


def inventario(brazo: str, out: Path) -> dict:
    r = subprocess.run([sys.executable, "-B", str(LANZADOR), "--brazo", brazo, "--id", f"AISL-{brazo}",
                        "--pregunta", "pregunta de prueba (modo init, sin modelo)", "--out", str(out), "--modo", "init"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"lanzador falló para {brazo}: {r.stderr[-800:]}")
    return json.loads((out / f"meta_AISL-{brazo}.json").read_text(encoding="utf-8"))


def main() -> int:
    out = AQUI / "resultados"
    out.mkdir(parents=True, exist_ok=True)
    venv_vec = os.environ.get("BANCO_VENV_VECTOR")
    if not venv_vec:
        raise SystemExit("BANCO_VENV_VECTOR no definido")
    env = dict(os.environ, BANCO_REPO=str(REPO_DIR), BANCO_VENV_VECTOR=venv_vec)

    # (a) inventario por brazo
    metas = {b: inventario(b, out / "init") for b in ("kg", "vector")}
    tools = {b: set(m["inventario_tools_R6"]["tools_en_init"] or []) for b, m in metas.items()}
    esperadas = {b: set(CFG["brazos"][b]["tools_esperadas"]) for b in tools}
    a_res = {
        "tools_kg": sorted(tools["kg"]), "tools_vector": sorted(tools["vector"]),
        "kg_sin_tools_del_vectorial": not (tools["kg"] & esperadas["vector"]),
        "vector_sin_tools_del_kg": not (tools["vector"] & esperadas["kg"]),
        "sin_builtin_kg": not (tools["kg"] & TOOLS_ARCHIVOS_SHELL_RED) and all(t.startswith("mcp__") for t in tools["kg"]),
        "sin_builtin_vector": not (tools["vector"] & TOOLS_ARCHIVOS_SHELL_RED) and all(t.startswith("mcp__") for t in tools["vector"]),
        "coincide_con_esperadas": {b: tools[b] == esperadas[b] for b in tools},
        "permission_mode": {b: metas[b]["harness_R10"]["permission_mode"] for b in metas},
        "tools_denegadas_por_flag": metas["kg"]["harness_R10"]["tools_denegadas"],
    }
    a_res["PASS"] = all([a_res["kg_sin_tools_del_vectorial"], a_res["vector_sin_tools_del_kg"], a_res["sin_builtin_kg"],
                         a_res["sin_builtin_vector"], all(a_res["coincide_con_esperadas"].values()),
                         all(v == "dontAsk" for v in a_res["permission_mode"].values())])

    # (b) artefactos del grafo inaccesibles desde el brazo vectorial
    srv_vec = (BANCO_DIR / "mcp_vector" / "servidor_mcp_vector.py").read_text(encoding="utf-8")
    imports_vec = sorted(set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", srv_vec, flags=re.M)))
    modulos_grafo = {"neo4j", "neo4j_index", "grafos", "conexion", "harness", "loader", "tools_juguete", "agente_v2", "tools_v2"}
    r_imp = subprocess.run([f"{venv_vec}/bin/python", "-c", "import neo4j"], capture_output=True, text=True)
    menciona_artefactos = [x for x in ARTEFACTOS_GRAFO if x in srv_vec or x in
                           (BANCO_DIR / "mcp_vector" / "construir_indice.py").read_text(encoding="utf-8")]
    b_res = {
        "agente_vector_tools_de_archivo_o_shell": sorted(tools["vector"] & TOOLS_ARCHIVOS_SHELL_RED),
        "servidor_vector_imports": imports_vec,
        "servidor_vector_importa_modulos_del_grafo": sorted(set(i.split(".")[0] for i in imports_vec) & modulos_grafo),
        "servidor_vector_menciona_artefactos_del_grafo": menciona_artefactos,
        "import_neo4j_en_venv_vector": {"returncode": r_imp.returncode, "stderr_tail": r_imp.stderr.strip()[-120:]},
        "artefactos_protegidos": ARTEFACTOS_GRAFO,
        "nota": "por capacidad: el agente del brazo vectorial no dispone de ninguna tool que lea archivos ni ejecute comandos; el servidor vectorial solo lee su propio índice. La denegación en runtime (intento real) se ejercita en fase B.",
    }
    b_res["PASS"] = (not b_res["agente_vector_tools_de_archivo_o_shell"] and not b_res["servidor_vector_importa_modulos_del_grafo"]
                     and not menciona_artefactos and r_imp.returncode != 0)

    # (c) puerto de Neo4j inaccesible desde el brazo vectorial
    abre_sockets = bool(re.search(r"\bsocket\b|GraphDatabase|bolt://|:7687|requests\.|urllib|httpx", srv_vec))
    c_res = {
        "agente_vector_tools_de_red_o_shell": sorted(tools["vector"] & {"Bash", "WebFetch", "WebSearch"}),
        "servidor_vector_codigo_abre_sockets_o_bolt": abre_sockets,
        "venv_vector_tiene_driver_neo4j": r_imp.returncode == 0,
        "puerto": "127.0.0.1:7687 (docker-compose.yml de data/experiment/neo4j)",
        "nota": "el agente no tiene capacidad de red ni shell; el único proceso del brazo vectorial (su servidor MCP) no tiene driver bolt ni código de sockets. La prueba dinámica (el agente pide abrir el puerto) es de fase B.",
    }
    c_res["PASS"] = not c_res["agente_vector_tools_de_red_o_shell"] and not abre_sockets and not c_res["venv_vector_tiene_driver_neo4j"]

    # (d) positivo por brazo: connected + llamada real por el mismo JSON
    d_res = {}
    for b, tool, args in (("kg", "buscar_nodos", {"consulta": "efectivo mínimo", "limite": 3}),
                          ("vector", "buscar_pasajes", {"consulta": "efectivo mínimo", "limite": 3})):
        mcp_json = BANCO_DIR / CFG["brazos"][b]["mcp_config"]
        cmd, e = cmd_desde_mcp_json(mcp_json, dict(env, BANCO_LOG_R1=str(out / f"log_r1_positivo_{b}.jsonl"),
                                                    BANCO_SESION_TAG=f"aislamiento_positivo_{b}"))
        with ClienteFalso(cmd, env=e, timeout_s=600) as cli:
            lista = [t["name"] for t in cli.listar_tools()]
            texto = cli.llamar(tool, args)
        obj = json.loads(texto)
        n = len(obj.get("resultados", []))
        d_res[b] = {"mcp_status_en_init": metas[b]["servidores_mcp"]["en_init"],
                    "tools_servidor": lista, "llamada": {"tool": tool, "input": args},
                    "n_resultados": n, "chars": len(texto),
                    "primer_resultado": (obj["resultados"][0].get("id") if n else None),
                    "fuente_segun_log": metas[b]["servidores_mcp"]["fuente"],
                    "PASS": n > 0 and any(s.get("status") == "connected" for s in metas[b]["servidores_mcp"]["en_init"] or [])}
    d_res["PASS"] = all(d_res[b]["PASS"] for b in ("kg", "vector"))

    res = {"generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "unidad": "U-A2.0-banco — entregable 4 (aislamiento por capacidad)",
           "modo": "init (USD 0) + cliente falso", "config_agentes_sha256": sha256_file(BANCO_DIR / "agentes" / "config_agentes.json"),
           "a_inventario": a_res, "b_artefactos_grafo": b_res, "c_puerto_neo4j": c_res, "d_positivo": d_res,
           "inventario_persistido_por_traza": {b: rel_repo(out / "init" / f"meta_AISL-{b}.json") for b in metas},
           "PASS": a_res["PASS"] and b_res["PASS"] and c_res["PASS"] and d_res["PASS"]}
    (out / "aislamiento.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for k in ("a_inventario", "b_artefactos_grafo", "c_puerto_neo4j", "d_positivo"):
        print(f"{k}: {'PASS' if res[k]['PASS'] else 'FAIL'}")
    print("TOTAL:", "PASS" if res["PASS"] else "FAIL", "->", rel_repo(out / "aislamiento.json"))
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
