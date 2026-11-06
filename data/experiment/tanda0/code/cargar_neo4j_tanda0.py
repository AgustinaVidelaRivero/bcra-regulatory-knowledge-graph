"""
cargar_neo4j_tanda0.py — U-TANDA0-2A E3.c (gate 5): carga en Neo4j, índice
full-text y verificación de los grafos r1 de la tanda 0 registrados en
data/experiment/neo4j/grafos.py (KG_Tanda0_Desarrollo_r1, KG_Tanda0_Diez_r1).

No reimplementa nada: importa y llama, sin editarlas, las funciones de
  - cargar_kg.py      verificar_sha (vía grafos), cargar_kg, cargar_en_neo4j,
                      huella_neo4j (idempotencia: dos cargas, misma huella de
                      estado), verificar_carga (conteos, KG_Meta.kg_sha256,
                      muestreo de 20 nodos, huella de contenido loader=Neo4j),
                      leer_meta;
  - indices.py        crear_indice (CAMPOS_FULLTEXT y analizador sin cambios),
                      los tres tests dirigidos (definidos sobre KG-Refinado:
                      en estos grafos se reportan como informativos) y
                      describir_indices;
  - test_equivalencia.py  correr_grafo(driver, clave, Registro()) — la interfaz
                      por grafo del selftest de paridad; su main() recorre
                      TODAS las claves del registro y escribe un JSON fijo junto
                      al script (test_equivalencia_resultados_A11.json), por eso
                      no se invoca main(): el detalle se escribe en --out-dir.

Importa comun_tanda0 antes que todo (registro en memoria de la vista runtime
de estos grafos). grafos.cargar_vista_runtime ya importa comun_tanda0 por el
campo requiere_registro_modulo de las entradas KG_Tanda0_*, así que este
import explícito del cargador queda redundante e inocuo.

U-NAV-DISENO, N5 (mandato firmado en c2ddf5f7, §4, N5; decisión 6):
  - acepta en --grafo toda clave de grafos.py (`CLAVES_CARGABLES`): antes
    filtraba las que empiezan con «KG_Tanda0_», y la tanda 1 y el acumulado se
    cargaban con un envoltorio en memoria (tanda1/t3/scripts/cargar_neo4j_t3f.py).
    `CLAVES_TANDA0` queda como alias de la misma lista, para esos envoltorios;
    «todos» son todas las claves del registro;
  - la carga exporta las propiedades de arista de la decisión 6
    (cargar_kg.PROPS_ARISTA_N5 y MARCAS_ARISTA_N5) y la salida suma, por grafo:
    el estado sin esas propiedades (comparable con el `estado` de antes de N5),
    la paridad loader = Neo4j de esas propiedades y la lista exportada. Las
    huellas de HEAD (`contenido` y `estado`) se calculan igual que antes.

Uso:
  .venv/bin/python cargar_neo4j_tanda0.py [--grafo CLAVE|todos] [--out-dir reports/tanda0]
                                          [--sin-equivalencia]
Salidas: <out-dir>/carga_neo4j_tanda0.json y <out-dir>/test_equivalencia_tanda0.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
EXP_DIR = CODE_DIR.parents[1]
REPO_DIR = EXP_DIR.parents[1]
NEO4J_DIR = EXP_DIR / "neo4j"
for _p in (str(CODE_DIR), str(NEO4J_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import comun_tanda0  # noqa: E402,F401  (registra la vista runtime ANTES de todo)
import grafos as G  # noqa: E402
import cargar_kg as CK  # noqa: E402
import indices as IX  # noqa: E402
import test_equivalencia as TE  # noqa: E402

CLAVES_CARGABLES = list(G.CLAVES)       # N5: sin el filtro por «KG_Tanda0_» (ver docstring)
CLAVES_TANDA0 = CLAVES_CARGABLES        # alias para los envoltorios que lo reemplazan en memoria


def cargar_y_verificar(driver, clave: str, con_equivalencia: bool, reg) -> dict:
    g = G.GRAFOS[clave]
    print(f"\n===== {clave} ({g['nombre_canonico']}, {g['sha256'][:12]}) =====", flush=True)
    sha = G.verificar_sha(clave)
    print(f"sha256 verificado: {sha} ✓", flush=True)
    kg = CK.cargar_kg(clave)
    print(f"loader (vista runtime): {len(kg.nodes)} nodos / {len(kg.edges)} aristas "
          f"(raw {kg.raw_node_count}/{kg.raw_edge_count}, merges={len(kg.merges)})", flush=True)
    r1 = CK.cargar_en_neo4j(driver, kg, clave)
    h1 = CK.huella_neo4j(driver, clave)
    r2 = CK.cargar_en_neo4j(driver, kg, clave)
    h2 = CK.huella_neo4j(driver, clave)
    print(f"carga 1: {r1} | carga 2: {r2}", flush=True)
    print(f"idempotencia: estado1={h1['estado']} estado2={h2['estado']} "
          f"{'✓ idéntica' if h1 == h2 else '✗ DIFIERE'}", flush=True)
    IX.crear_indice(driver, clave)
    ok_carga = CK.verificar_carga(driver, kg, clave)
    meta = CK.leer_meta(driver, clave)
    sha_archivo = G.sha256_de(g["path"])
    meta_ok = bool(meta) and meta.get("kg_sha256") == sha_archivo
    print(f"KG_Meta.kg_sha256 == sha256(archivo): {meta_ok} ({(meta or {}).get('kg_sha256')} vs {sha_archivo})",
          flush=True)
    print("\ntests dirigidos de indices.py (definidos sobre KG-Refinado; informativos acá):", flush=True)
    t_a = IX.test_bkl_0003(driver, clave)
    t_a2 = IX.test_bkl_0003_descripcion(driver, clave)
    t_b = IX.test_bkl_0027(driver, clave)
    res = {
        "clave": clave, "nombre_canonico": g["nombre_canonico"], "label": g["label"],
        "indice_fulltext": g["indice_fulltext"], "kg_path": G.rel_repo(g["path"]),
        "sha256_archivo": sha_archivo, "sha256_registro": g["sha256"],
        "commit_sellado": g["commit_sellado"],
        "loader": {"nodos": len(kg.nodes), "aristas": len(kg.edges),
                   "raw": [kg.raw_node_count, kg.raw_edge_count], "merges": len(kg.merges)},
        "carga_1": r1, "carga_2": r2,
        "huella_estado_1": h1["estado"], "huella_estado_2": h2["estado"],
        "idempotente": h1 == h2, "huella_contenido_neo4j": h2["contenido"],
        "huella_contenido_loader": CK.huella_loader(kg, clave),
        "verificar_carga_ok": ok_carga, "kg_meta": meta, "kg_meta_sha_igual_archivo": meta_ok,
        "tests_indices_informativos": {"BKL-0003": IX._fmt(t_a), "BKL-0003/desc": IX._fmt(t_a2),
                                       "BKL-0027": IX._fmt(t_b)},
        # N5 (decisión 6): el estado sin las propiedades nuevas de arista (comparable con el de antes de N5), la
        # paridad loader = Neo4j de esas propiedades (también dentro de verificar_carga) y la lista exportada.
        "huella_estado_sin_props_n5_1": h1["estado_sin_props_n5"],
        "huella_estado_sin_props_n5_2": h2["estado_sin_props_n5"],
        "huella_props_aristas_loader": CK.huella_props_aristas_loader(kg, clave),
        "huella_props_aristas_neo4j": CK.huella_props_aristas_neo4j(driver, clave),
        "props_aristas_exportadas": (meta or {}).get(CK.CLAVE_META_N5),
    }
    if con_equivalencia:
        res["equivalencia_detalle"] = TE.correr_grafo(driver, clave, reg)
    res["ok"] = (res["idempotente"] and ok_carga and meta_ok
                 and r1["aristas_colgantes"] == 0 and r2["aristas_colgantes"] == 0
                 and res["huella_props_aristas_loader"] == res["huella_props_aristas_neo4j"])
    return res


def resumen_equivalencia(reg) -> dict:
    """Mismo resumen que test_equivalencia.main (por grafo/modo/tool)."""
    resumen = collections.OrderedDict()
    for f in reg.filas:
        k = f"{f['grafo']}/{f['modo']}/{f['tool']}"
        r = resumen.setdefault(k, {"casos": 0, "iguales": 0, "rige_paridad": f["rige_paridad"]})
        r["casos"] += 1
        r["iguales"] += 1 if f.get("igual", f.get("identico")) else 0
    total_par = sum(r["casos"] for r in resumen.values() if r["rige_paridad"])
    ok_par = sum(r["iguales"] for r in resumen.values() if r["rige_paridad"])
    return {"resumen": resumen, "paridad_total": f"{ok_par}/{total_par}",
            "fallas_paridad": reg.fallas_paridad}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--grafo", choices=CLAVES_CARGABLES + ["todos"], default="todos")
    ap.add_argument("--out-dir", type=Path, default=REPO_DIR / "reports" / "tanda0")
    ap.add_argument("--sin-equivalencia", action="store_true")
    args = ap.parse_args()
    claves = CLAVES_CARGABLES if args.grafo == "todos" else [args.grafo]

    driver = CK.abrir_driver()
    reg = TE.Registro()
    salida = {"unidad": "U-TANDA0-2A E3.c", "revision_cargador": "U-NAV-DISENO N5 (decisión 6; sin el filtro «KG_Tanda0_»)",
              "claves": claves,
              "campos_fulltext": IX.CAMPOS_FULLTEXT, "analyzer": IX.ANALYZER, "grafos": {}}
    ok = True
    try:
        for clave in claves:
            r = cargar_y_verificar(driver, clave, not args.sin_equivalencia, reg)
            salida["grafos"][clave] = {k: v for k, v in r.items() if k != "equivalencia_detalle"}
            ok = ok and r["ok"]
        salida["indices_en_la_db"] = IX.describir_indices(driver)
    finally:
        driver.close()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if not args.sin_equivalencia:
        eq = resumen_equivalencia(reg)
        salida["equivalencia"] = {"paridad_total": eq["paridad_total"], "fallas_paridad": eq["fallas_paridad"]}
        (args.out_dir / "test_equivalencia_tanda0.json").write_text(json.dumps(
            {"criterio": "byte-identidad de json.dumps(x, ensure_ascii=False) (serialización del harness)",
             "origen": "test_equivalencia.correr_grafo por clave (sin main: su main recorre todas las claves y "
                       "escribe un JSON fijo junto al script)",
             **eq, "filas": reg.filas}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        ok = ok and eq["fallas_paridad"] == 0
        print(f"\nPARIDAD (tanda 0): {eq['paridad_total']} casos byte-idénticos; fallas={eq['fallas_paridad']}")
    salida["ok"] = ok
    (args.out_dir / "carga_neo4j_tanda0.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\nVERIFICACIÓN GATE 5:", "OK" if ok else "CON FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
