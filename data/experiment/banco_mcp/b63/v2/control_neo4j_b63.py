#!/usr/bin/env python3
"""control_neo4j_b63.py — El Neo4j de B6.3 antes de lanzar (etapa b1; decisión de la autora del 27/10/2026, 10:24:11: «B6.3 usa el
Neo4j propio de los índices (proyecto neo4j_indices_eval, puertos 47474 y 47687), que ya tiene el grafo evaluado cargado y verificado:
huella de contenido 2645da6d01795d520f3c4ab5e237050c530238061f849cd7d1e0170be9223463 y paridad 147 de 147. […] La etapa b del runner
fija cómo se levanta, que el servidor del grafo apunte a 47687 y que el testigo controle esa huella antes de lanzar.»).

Es paralelo/control_neo4j_propio.py (`estado`, con --huella) en una versión nueva, para la configuración del grafo evaluado
(mcp_kg/config_mcp_kg_nav_evaluado.json; su grafo y su `kg_sha256_esperado`), con dos controles más:
  · NEO4J_URI del entorno tiene que ser el de la entrada sellada (bolt://127.0.0.1:47687);
  · la huella de contenido (`cargar_kg.huella_neo4j`, la que usa control_neo4j_propio.py --huella) tiene que ser la de la entrada.
Imprime la dirección (NEO4J_URI, que no es una credencial: registro de decisiones, §88), el sha256 de KG_Meta, las cuentas y las
huellas; el usuario y la contraseña son los de conexion.py y no se imprimen. Código 15 (el del runner) si algo no da.
`estado` recibe el módulo de cargar_kg y la función que abre el driver: el selftest le pasa un doble.
Uso: NEO4J_URI=bolt://127.0.0.1:47687 control_neo4j_b63.py --huella-esperada <hex> [--uri-esperada bolt://127.0.0.1:47687]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent.parent
NEO4J_DIR = BANCO_DIR.parent / "neo4j"
CONFIG_GRAFO = BANCO_DIR / "mcp_kg" / "config_mcp_kg_nav_evaluado.json"
URI_B63 = "bolt://127.0.0.1:47687"
NO_DA = 15


def estado(huella_esperada: str, uri_esperada: str = URI_B63, ck=None, abrir=None, config: Path = CONFIG_GRAFO) -> dict:
    cfg = json.loads(Path(config).read_text(encoding="utf-8"))
    uri = os.environ.get("NEO4J_URI")
    out = {"NEO4J_URI": uri, "uri_esperada": uri_esperada, "grafo": cfg["grafo"], "kg_sha256_esperado": cfg["kg_sha256_esperado"],
           "huella_contenido_esperada": huella_esperada}
    if uri != uri_esperada:
        return out | {"ok": False, "motivo": f"NEO4J_URI del entorno ({uri!r}) no es el de la entrada ({uri_esperada})"}
    if ck is None or abrir is None:
        if str(NEO4J_DIR) not in sys.path:
            sys.path.insert(0, str(NEO4J_DIR))
        import cargar_kg as ck_real              # noqa: PLC0415  (data/experiment/neo4j)
        from conexion import abrir_driver        # noqa: PLC0415
        ck, abrir = ck or ck_real, abrir or abrir_driver
    try:
        driver = abrir()
        driver.verify_connectivity()
    except Exception as e:                       # solo el tipo: el mensaje no se imprime
        return out | {"ok": False, "motivo": f"no responde ({type(e).__name__})"}
    try:
        meta = ck.leer_meta(driver, cfg["grafo"]) or {}
        h = ck.huella_neo4j(driver, cfg["grafo"])
        out |= {"kg_meta_sha256": meta.get("kg_sha256"), "n_nodos": h["n_nodos"], "n_aristas": h["n_aristas"],
                "huella_estado": h["estado"], "huella_contenido": h["contenido"]}
    finally:
        driver.close()
    problemas = []
    if out["kg_meta_sha256"] != cfg["kg_sha256_esperado"]:
        problemas.append("KG_Meta no da el sha256 del grafo evaluado")
    if out["huella_contenido"] != huella_esperada:
        problemas.append("la huella de contenido no es la de la entrada")
    out["ok"] = not problemas
    out["motivo"] = "; ".join(problemas) or None
    return out


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--huella-esperada", required=True)
    ap.add_argument("--uri-esperada", default=URI_B63)
    a = ap.parse_args(argv)
    e = estado(a.huella_esperada, a.uri_esperada)
    print(json.dumps(e, ensure_ascii=False))
    if not e["ok"]:
        print(f"FRENO (USD 0): {e['motivo']}")
        return NO_DA
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
