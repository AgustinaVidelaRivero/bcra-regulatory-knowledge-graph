#!/usr/bin/env python3
"""test_paridad_mcp_kg.py — Paridad byte a byte del servidor MCP del KG contra
Neo4jIndex directo (U-A2.0-banco, entregable 1).

Para cada tool, 10 llamadas a TRAVÉS del transporte MCP (subproceso stdio,
cliente falso) y las mismas 10 contra `Neo4jIndex` en el mismo modo, sin MCP.
Criterio: el texto que recibe el cliente == `json.dumps(obj, ensure_ascii=False)`
del resultado directo, byte a byte (comparación de la cadena y de su sha256).
Además: las definiciones de tools listadas por el servidor == `harness.TOOLS`
(nombre, descripción, input_schema), y el log R1 del servidor contiene las 30
llamadas con `output_str` idéntico.

Las consultas son PROPIAS (vocabulario del corpus normativo), nunca EV2.

Uso:
    .venv/bin/python -B test_paridad_mcp_kg.py [--config config_mcp_kg.json]
                                               [--out resultados/paridad_mcp_kg.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
EXPERIMENT_DIR = BANCO_DIR.parent
for _p in (str(BANCO_DIR), str(EXPERIMENT_DIR / "neo4j"), str(EXPERIMENT_DIR / "evaluacion")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cliente_falso import ClienteFalso                      # noqa: E402
from comun_banco import rel_repo, serializar_payload, sha256_bytes  # noqa: E402
from harness import TOOLS                                    # noqa: E402
from servidor_mcp_kg import abrir_backend, despachar         # noqa: E402
from comun_banco import cargar_config                        # noqa: E402

CONSULTAS = [
    {"consulta": "asociación mutual"},
    {"consulta": "efectivo mínimo", "limite": 5},
    {"consulta": "capitales mínimos de las entidades financieras"},
    {"consulta": "clasificación de deudores", "limite": 3},
    {"consulta": "previsiones por riesgo de incobrabilidad"},
    {"consulta": "garantías preferidas", "limite": 50},
    {"consulta": "operaciones de cambio exterior", "limite": "7"},   # limite no entero-string: tolerancia del harness
    {"consulta": "tasa de interés", "limite": 0},                    # clamp a 1
    {"consulta": "de la que se"},                                     # solo stopwords
    {"consulta": "sociedad de garantía recíproca"},
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=AQUI / "config_mcp_kg.json")
    ap.add_argument("--out", type=Path, default=AQUI / "resultados" / "paridad_mcp_kg.json")
    a = ap.parse_args()

    config, config_sha = cargar_config(a.config)
    index, fuente = abrir_backend(config)

    # ids para ver_nodo / ver_vecinos: los primeros resultados de las búsquedas
    # directas (determinístico) + un id inexistente (camino de error).
    ids = []
    for c in CONSULTAS:
        r = despachar(index, "buscar_nodos", c)
        for x in r.get("resultados", [])[:2]:
            if x["id"] not in ids:
                ids.append(x["id"])
    # grafos chicos (demostración sobre el mini-grafo): completar con ids del índice
    for i in sorted(getattr(index, "by_id", {})):
        if len(ids) >= 9:
            break
        if i not in ids:
            ids.append(i)
    ids = ids[:9] + ["__no_existe__"]
    assert len(ids) == 10, ids
    direcciones = ["ambas", "salientes", "entrantes", None, "AMBAS", "otra",
                   "ambas", "salientes", "entrantes", "ambas"]
    plan = ([("buscar_nodos", c) for c in CONSULTAS]
            + [("ver_nodo", {"id": i}) for i in ids]
            + [("ver_vecinos", {"id": i} | ({"direccion": d} if d is not None else {}))
               for i, d in zip(ids, direcciones)])

    log_path = BANCO_DIR / "logs" / f"test_paridad_mcp_kg_{datetime.now().strftime('%Y%m%dT%H%M%S')}.jsonl"
    filas = []
    with ClienteFalso([sys.executable, "-B", str(AQUI / "servidor_mcp_kg.py"),
                       "--config", str(a.config)],
                      env={"BANCO_LOG_R1": str(log_path), "BANCO_SESION_TAG": "test_paridad"}) as cli:
        tools_mcp = cli.listar_tools()
        tools_harness = [{"name": t["name"], "description": t["description"],
                          "input_schema": t["input_schema"]} for t in TOOLS]
        paridad_defs = tools_mcp == tools_harness
        for k, (tool, args) in enumerate(plan, 1):
            via_mcp = cli.llamar(tool, args)
            directo = serializar_payload(despachar(index, tool, args))
            filas.append({"k": k, "tool": tool, "input": args,
                          "chars_mcp": len(via_mcp), "chars_directo": len(directo),
                          "sha256_mcp": sha256_bytes(via_mcp.encode("utf-8")),
                          "sha256_directo": sha256_bytes(directo.encode("utf-8")),
                          "igual": via_mcp == directo})
    # log R1: 30 llamadas, output_str idéntico al que vio el cliente
    lineas = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    llamadas = [l for l in lineas if l["evento"] == "llamada"]
    log_ok = (len(llamadas) == len(plan)
              and all(l["n"] == f["k"] and l["tool"] == f["tool"] and l["input"] == f["input"]
                      and l["output_sha256"] == f["sha256_mcp"] and l["config_sha256"] == config_sha
                      for l, f in zip(llamadas, filas))
              and lineas[0]["evento"] == "inicio" and lineas[-1]["evento"] == "fin")

    res = {"generado": datetime.now().isoformat(timespec="seconds"),
           "unidad": "U-A2.0-banco — entregable 1 (paridad MCP del KG)",
           "config": rel_repo(a.config), "config_sha256": config_sha, "fuente": fuente,
           "definiciones_tools_identicas_a_harness_TOOLS": paridad_defs,
           "n_llamadas": len(filas), "n_iguales": sum(f["igual"] for f in filas),
           "por_tool": {t: {"n": sum(1 for f in filas if f["tool"] == t),
                            "iguales": sum(1 for f in filas if f["tool"] == t and f["igual"])}
                        for t in ("buscar_nodos", "ver_nodo", "ver_vecinos")},
           "log_r1": {"ruta": rel_repo(log_path), "n_lineas": len(lineas),
                      "n_llamadas": len(llamadas), "consistente_con_cliente": log_ok,
                      "sha256_log": sha256_bytes(log_path.read_bytes())},
           "max_chars_resultado": max(f["chars_mcp"] for f in filas),
           "PASS": paridad_defs and all(f["igual"] for f in filas) and log_ok,
           "llamadas": filas}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "llamadas"}, ensure_ascii=False, indent=1))
    for f in filas:
        print(f"  {f['k']:2d} {f['tool']:13s} {json.dumps(f['input'], ensure_ascii=False):70s} "
              f"{f['chars_mcp']:7d} {'OK' if f['igual'] else 'DIFIERE'}")
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
