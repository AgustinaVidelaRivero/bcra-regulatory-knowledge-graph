"""R0, fase 1 (USD 0, sin API): el costo estimado de R0, con la fórmula de caching (decisión 2 de caching).

1. Las tarifas medidas de la enmienda 7, §1.4, recomputadas desde sus fuentes:
   - E3 por llamada: el gasto de O3 entre sus 20 llamadas (e3_listas/o3/a/presupuesto.json);
   - E1 de reintento: el gasto de los reintentos de E1 del ratchet de la tanda 0 entre sus llamadas pagas
     (resumen_e3.json de los diez TOs, cliente_e1_reintentos);
   - E1 del intento 0, para el escenario sin la caché de E1: el gasto de E1 de la tanda 0 entre sus llamadas pagas
     (resumen_e1.json de los diez TOs).
2. Los escenarios A (reusando las 20 verificaciones de O3), B (sin reusarlas) y C (el peor caso: las 20 reintentan),
   y C sin la caché de E1, con esas tarifas.
3. Una estimación propia de la corrida con reuso: los tokens del reintento de E1 y de la re-verificación de E3 de la
   tanda 0 de las 3 unidades que reintentan (las filas de las bases del pipeline, por la clave que reconstruye el código
   del pipeline), más la escritura de los dos prefijos en la caché de la API (la primera llamada de E1 y la primera de
   E3 de la corrida los escriben; las siguientes los leen).
Solo lee (bases en modo inmutable). Escribe un JSON en --salida.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.parse
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REX = AQUI.parents[1]
REPO = REX.parents[2]
sys.path.insert(0, str(REX / "corpus_v2"))
import runner_corpus as RC                             # noqa: E402
import manifiesto_corpus                               # noqa: E402
import comun_e3                                        # noqa: E402
import cliente_e3                                      # noqa: E402
import prompt_e3                                       # noqa: E402
import llm_cache as lc                                 # noqa: E402

SALIDA_R2B = REX / "corpus_tanda0/salida_r2b"

REINTENTAN = ("ext::3.6.4.1", "ext::3.16.2.1", "ext::3.18.1.1")
TOPE = 1.50


def usd(tok: dict, p: dict) -> float:
    """Fórmula de caching: entrada no cacheada, salida, escritura y lectura de la caché de la API."""
    return (tok["in"] * p["precio_in_por_mtok"] + tok["out"] * p["precio_out_por_mtok"]
            + tok["cw"] * p["precio_cache_write_por_mtok"] + tok["cr"] * p["precio_cache_read_por_mtok"]) / 1e6


def abrir_ro(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{urllib.parse.quote(str(db.resolve()))}?mode=ro&immutable=1", uri=True)


def fila(con, key: str) -> dict | None:
    r = con.execute("select input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, model "
                    "from cache where key = ?", (key,)).fetchone()
    return None if r is None else {"in": r[0], "out": r[1], "cw": r[2], "cr": r[3], "model": r[4]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    RC.configurar(manifiesto_corpus.cargar(REX / "manifiestos/tanda0_10tos_r2b.json"))
    RC.PERFIL_R2 = RC.perfil_forma_r2(RC.PERFIL)

    # 1. tarifas medidas
    pres_o3 = json.loads((REPO / "data/experiment/e3_listas/o3/a/presupuesto.json").read_text(encoding="utf-8"))
    n_o3 = len(pres_o3["llamadas"])
    t_e3 = pres_o3["gasto_usd"] / n_o3
    # los resumen_e*.json por TO no sirven: en las fases reabiertas cuentan solo el último proceso. Las fuentes son
    # los contadores de T2 de U-REEXT-T0 (gasto y llamadas pagas de E1) y las filas de la base de reintentos.
    ct2 = json.loads((REPO / "data/experiment/reext_t0/salida/contadores_t2.json").read_text(encoding="utf-8"))
    g_e1 = ct2["b_gasto"]["total_e1_usd"]
    n_e1 = ct2["c_modelos_y_usage"]["bases"]["e1_extraccion.db"]["llamadas_pagadas_registradas"]
    ns_e1 = RC.cliente_e1.namespace_e1(prefijo_hash=RC.PERFIL.prefijo_hash_para_namespace)
    con_r0 = abrir_ro(RC.DB_REINTENTOS_E1)
    todas = [{"creada": t_, "in": a_, "out": b_, "cw": c_, "cr": d_} for t_, a_, b_, c_, d_ in con_r0.execute(
        "select created_at, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens from cache "
        "where namespace = ?", (ns_e1,))]
    con_r0.close()
    # la corrida T2 de U-REEXT-T0: del 05/10/2026 a las 14:38:15 a las 22:39 (−03), reext_t0/freno_t2.md, «Corrida»
    filas_rei = [f for f in todas if "2026-10-05T14:38:15" <= f["creada"] < "2026-10-05T22:40"]
    fuera_t2 = [{**f, "usd": round(usd(f, RC.P_E1), 6)} for f in todas if f not in filas_rei]
    n_rei = len(filas_rei)
    g_rei = sum(usd(f, RC.P_E1) for f in filas_rei)
    t_rei, t_e1 = g_rei / n_rei, g_e1 / n_e1
    tarifas = {"e3_por_llamada_o3": {"usd": round(t_e3, 6), "gasto": pres_o3["gasto_usd"], "llamadas": n_o3},
               "e1_reintento_tanda0": {"usd": round(t_rei, 6), "gasto": round(g_rei, 6), "llamadas_pagas": n_rei,
                                       "fuente": "filas de e1_reintentos.db en el namespace r2b creadas durante la "
                                                 "corrida T2, con la fórmula",
                                       "filas_del_namespace_fuera_de_t2": fuera_t2},
               "e1_intento0_tanda0": {"usd": round(t_e1, 6), "gasto": g_e1, "llamadas_pagas": n_e1,
                                      "fuente": "reext_t0/salida/contadores_t2.json (b_gasto y c_modelos_y_usage)"}}

    # 2. escenarios de la mesa, con estas tarifas
    par = t_rei + t_e3                                   # un reintento: E1 nuevo y E3 nuevo
    esc = {"A_reusando_o3": 3 * par,
           "B_sin_reusar_o3": 20 * t_e3 + 3 * par,
           "C_peor_caso_las_20_reintentan": 20 * t_e3 + 20 * par,
           "C_sin_la_cache_de_e1": 20 * t_e3 + 20 * par + 20 * t_e1}
    esc = {k: round(v, 4) for k, v in esc.items()}

    # 3. estimación propia de la corrida con reuso (las 3 que reintentan), por sus fichas de la tanda 0
    perfil = RC.PERFIL
    con_r, con_3, con_1 = abrir_ro(RC.DB_REINTENTOS_E1), abrir_ro(cliente_e3.DB_PATH), abrir_ro(
        REX / "e1_extractor/cache/e1_extraccion.db")
    tdir = SALIDA_R2B / "ext"
    chunks = RC.chunks_con_partes(RC.chunks_sin_ids_repetidos(
        comun_e3.cargar_chunks(("ext",), e0_dir=RC.E0_DIR), "ext"), tdir)
    por_id = {c["id"]: c for c in chunks}
    finales = RC.cargar_jsonl_last_wins(tdir / "finales.jsonl")
    claves_rei = {r["chunk_id"]: r["clave"] for r in RC.claves_reintentos_cache(tdir, chunks, perfil,
                                                                                 solo=set(REINTENTAN))}
    ns_e3 = cliente_e3.namespace_e3()
    fichas = {}
    for cid in REINTENTAN:
        fe1 = fila(con_r, claves_rei[cid]) if cid in claves_rei else None
        vf = finales[cid].get("validacion_final")
        # la re-verificación de la tanda 0: la extracción final si se aceptó tras el reintento; si fue a la cola,
        # no hay validación final guardada y se usa la verificación de O3 de la unidad como aproximación
        fe3 = fila(con_3, lc.compute_key(ns_e3, lc.canonical_request(
            prompt_e3.build_request_kwargs(por_id[cid], {k: v for k, v in vf.items() if k != "marcas_e3"},
                                           model=RC.MODEL_E3)))) if vf else None
        fichas[cid] = {"estado_tanda0": finales[cid]["estado"], "reintento_e1_tanda0": fe1,
                       "usd_reintento_e1": round(usd(fe1, RC.P_E1), 6) if fe1 else None,
                       "reverificacion_e3_tanda0": fe3,
                       "usd_reverificacion_e3": round(usd(fe3, RC.P_E3), 6) if fe3 else None}
    o3 = {json.loads(x)["chunk_id"]: json.loads(x) for x in
          (REPO / "data/experiment/e3_listas/o3/a/respuestas_e3_o3.jsonl").read_text(encoding="utf-8").splitlines()}
    for cid, f in fichas.items():
        if f["usd_reverificacion_e3"] is None:
            f["usd_reverificacion_e3"] = o3[cid]["usd"]
            f["reverificacion_e3_aproximada_con_o3"] = True
    # tamaño de los prefijos: lo que leyó de la caché de la API una llamada típica
    pref_e3 = max(o3[c]["usage_delta"]["cache_read"] for c in o3)
    pref_e1 = max(f["reintento_e1_tanda0"]["cr"] + f["reintento_e1_tanda0"]["cw"] for f in fichas.values()
                  if f["reintento_e1_tanda0"])
    # las fichas se pasan a «prefijo leído» y se suma una escritura de cada prefijo
    base = 0.0
    for f in fichas.values():
        e1 = f["reintento_e1_tanda0"]
        e1_leido = dict(e1, cw=0, cr=e1["cr"] + e1["cw"])
        base += usd(e1_leido, RC.P_E1) + f["usd_reverificacion_e3"]
    escritura = (pref_e1 * (RC.P_E1["precio_cache_write_por_mtok"] - RC.P_E1["precio_cache_read_por_mtok"])
                 + pref_e3 * (RC.P_E3["precio_cache_write_por_mtok"] - RC.P_E3["precio_cache_read_por_mtok"])) / 1e6
    propia = {"tres_reintentos_con_prefijo_leido": round(base, 4),
              "escritura_de_los_dos_prefijos": round(escritura, 4),
              "prefijo_e1_tokens": pref_e1, "prefijo_e3_tokens": pref_e3,
              "total_con_reuso": round(base + escritura, 4),
              "total_sin_reuso": round(base + escritura + pres_o3["gasto_usd"], 4)}
    # 4. proyección por llamada de los clientes (lo que mira el tope antes de cada llamada)
    proy = {"e3": round((22000 * RC.P_E3["precio_cache_write_por_mtok"] + 4000 * RC.P_E3["precio_in_por_mtok"]
                         + prompt_e3.MAX_OUTPUT_TOKENS * RC.P_E3["precio_out_por_mtok"]) / 1e6, 6),
            "e1": round((6500 * RC.P_E1["precio_cache_write_por_mtok"] + 1000 * RC.P_E1["precio_in_por_mtok"]
                         + 8192 * RC.P_E1["precio_out_por_mtok"]) / 1e6, 6),
            "salida_maxima_del_reintento_e1_usd": round(RC.MAX_TOKENS_REINTENTO * RC.P_E1["precio_out_por_mtok"]
                                                        / 1e6, 6)}
    for con in (con_r, con_3, con_1):
        con.close()
    res = {"tarifas": tarifas, "escenarios_usd": esc, "estimacion_propia_usd": propia, "fichas": fichas,
           "proyeccion_por_llamada_usd": proy, "tope_usd": TOPE,
           "todos_debajo_del_tope": all(v < TOPE for v in esc.values()),
           "precios_por_mtok": {"e1": RC.P_E1, "e3": RC.P_E3}}
    a.salida.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("tarifas", "escenarios_usd", "estimacion_propia_usd",
                                          "proyeccion_por_llamada_usd", "todos_debajo_del_tope")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
