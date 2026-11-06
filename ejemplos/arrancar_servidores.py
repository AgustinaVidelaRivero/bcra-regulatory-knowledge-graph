#!/usr/bin/env python3
"""Arranca cada servidor del agente sin llamar a ninguna herramienta.

Lanza cada servidor por stdio, con el comando, los argumentos y el env de su mcp_*.json, negocia la inicialización y lista
las herramientas. Al arrancar, cada servidor comprueba las huellas de todo lo que usa. Si una no da, aborta y la
inicialización no llega. No imprime el texto de ningún índice.

Hace falta el grafo cargado en Neo4j, los índices en las carpetas que nombran las configuraciones y BANCO_VENV_VECTOR, el
entorno de data/experiment/banco_mcp/requirements_vector.txt. El .venv lo da --python si no está en la raíz.

  python ejemplos/arrancar_servidores.py --salida <carpeta fuera del árbol> [--python <python del .venv>] [--solo NOMBRE]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "data/experiment/banco_mcp"
SERVIDORES = {
    "n7": "n7/mcp_kg_n7_evaluado.json",
    "n7c_mas": "n7c/mcp_kg_n7c_amp_evaluado.json",
    "la_combinada": "mcp_vector/mcp_fragmentos_hibrida_evaluado.json",
    "la_densa": "mcp_vector/mcp_fragmentos_denso_evaluado.json",
}


def expandir(s, env):
    def rep(m):
        return env.get(m.group(1), "") or (m.group(3) or "")
    return re.sub(r"\$\{([A-Z0-9_]+)(:-([^}]*))?\}", rep, s)


def arrancar(nombre, rel, a):
    sys.path.insert(0, str(BANCO))
    from cliente_falso import ClienteFalso
    (_, s), = json.loads((BANCO / rel).read_text(encoding="utf-8"))["mcpServers"].items()
    log = a.salida / f"log_{nombre}.jsonl"
    base = dict(os.environ, BANCO_REPO=str(RAIZ), BANCO_LOG_R1=str(log), BANCO_SESION_TAG="arranque")
    env = {k: expandir(v, base) for k, v in s["env"].items()}
    if a.neo4j_uri:
        env["NEO4J_URI"] = a.neo4j_uri
    cmd = [expandir(s["command"], base)] + [expandir(x, base) for x in s["args"]]
    if a.python and cmd[0].endswith("/.venv/bin/python"):
        cmd[0] = a.python
    r = {"mcp_json": f"data/experiment/banco_mcp/{rel}"}
    try:
        with ClienteFalso(cmd=cmd, env=env, cwd=RAIZ, timeout_s=600) as c:
            r["herramientas"] = sorted(t["name"] for t in c.listar_tools())
        r["arranco"] = True
    except Exception as e:  # el servidor abortó: se informa el tipo, no su salida
        r["arranco"], r["error"] = False, type(e).__name__
    if log.exists():
        r["eventos"] = [json.loads(x)["evento"] for x in log.read_text(encoding="utf-8").splitlines()]
    return r


def main():
    ap = argparse.ArgumentParser(description="Arranca los servidores, sin llamar a ninguna herramienta.")
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--python")
    ap.add_argument("--neo4j-uri")
    ap.add_argument("--solo", choices=sorted(SERVIDORES))
    a = ap.parse_args()
    a.salida = a.salida.resolve()
    if a.salida == RAIZ or RAIZ in a.salida.parents:
        raise SystemExit("La carpeta de salida tiene que estar fuera del árbol.")
    a.salida.mkdir(parents=True, exist_ok=True)
    ok = True
    for nombre, rel in SERVIDORES.items():
        if a.solo and a.solo != nombre:
            continue
        r = arrancar(nombre, rel, a)
        print(json.dumps({nombre: r}, ensure_ascii=False), flush=True)
        ok = ok and r["arranco"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
