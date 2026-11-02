"""R0, fase 2: los controles sobre r0/corrida/, antes de anexar (USD 0, sin red; solo lee).

Corre sobre una copia del repo hecha después de la corrida (CLAUDE.md §4.l). Controla:
  1. el E1 del intento 0 de las 20 acierta la caché de E1 (los controles previos de correr_r0, otra vez);
  2. las 20 verificaciones de E3 salen de las filas sembradas, iguales a las de O3, y el reparto con esas
     verificaciones es el de la enmienda 7, §1.2 (16 aceptadas con el intento 0, 3 que reintentan y 1 a la cola);
  3. la re-verificación de cada unidad que reintentó, contra la verificación de O3 de la misma unidad y contra la
     re-verificación de la tanda 0 (se declaran: E3 no fija la temperatura);
  4. hay reintentos solo donde el ratchet los manda;
  5. el costo real, con la fórmula de caching, desde las líneas nuevas de logs/cache_usage.jsonl (contra su respaldo),
     y contra el presupuesto compartido y el registro de llamadas de R0;
  6. las filas nuevas de las dos bases (contra sus respaldos) y los modelos.
Uso: PYTHONDONTWRITEBYTECODE=1 <python> -B r0_f2_controles.py --respaldos <dir> --salida <json>
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
R0 = AQUI.parent
sys.path.insert(0, str(R0))
import correr_r0 as C                                   # noqa: E402  (importa runner_corpus y lo que importa)

RC, ratchet_e3, cliente_e3, cliente_e1 = C.RC, C.ratchet_e3, C.cliente_e3, C.cliente_e1
TRABAJO = C.TRABAJO
LOG = C.REPO / "logs" / "cache_usage.jsonl"
PRECIOS = {"reextraccion_v2_e3": RC.P_E3, "reextraccion_v2_e1": RC.P_E1}


def jl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def filas(db: Path) -> dict[str, tuple]:
    con = sqlite3.connect(f"file:{urllib.parse.quote(str(db.resolve()))}?mode=ro&immutable=1", uri=True)
    try:
        q = "select key, namespace, model, created_at, raw_json from cache"
        return {r[0]: r[1:] for r in con.execute(q)}
    finally:
        con.close()


def usd(u: dict, p: dict) -> float:
    return ((u.get("input_tokens") or 0) * p["precio_in_por_mtok"] + (u.get("output_tokens") or 0)
            * p["precio_out_por_mtok"] + (u.get("cache_creation_input_tokens") or 0) * p["precio_cache_write_por_mtok"]
            + (u.get("cache_read_input_tokens") or 0) * p["precio_cache_read_por_mtok"]) / 1e6


def tool_input(raw_json: str):
    return next((b.get("input") for b in json.loads(raw_json).get("content") or []
                 if isinstance(b, dict) and b.get("type") == "tool_use"), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--respaldos", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    ctx = C.cargar_contexto(C.SALIDA_T0)
    esp = json.loads(C.ESPERADOS.read_text(encoding="utf-8"))
    res: dict = {}
    resumen = json.loads((TRABAJO / C.RESUMEN).read_text(encoding="utf-8"))
    llam = jl(TRABAJO / C.REGISTRO_LLAMADAS)
    res["corrida"] = {k: resumen[k] for k in ("inicio", "fin", "freno", "gasto_compartido_usd", "tope_usd", "reuso_o3")}

    # 1. E1 del intento 0
    previos = C.controles_previos(ctx, C.ESPERADOS)
    res["1_e1_intento0"] = {"en_la_corrida": resumen["controles_previos"]["e1_intento0_acierta_la_cache"],
                            "ahora": previos["e1_intento0_acierta_la_cache"],
                            "ok": resumen["controles_previos"]["e1_intento0_acierta_la_cache"] == 20
                            and previos["e1_intento0_acierta_la_cache"] == 20}

    # 2. verificaciones sembradas y reparto
    o3 = ctx["o3"]
    sem = resumen["sembrado_o3"]
    ver = [x for x in llam if x["paso"] == "verificacion"]
    veredictos = {to: jl(TRABAJO / to / "veredictos.jsonl") for to in ctx["por_to"]}
    v_ini = {r["chunk_id"]: r for to in veredictos for r in veredictos[to] if r["fase"] == "verificacion"}
    iguales_o3 = sorted(cid for cid, r in v_ini.items() if r["tool_input"] == o3[cid]["tool_input"])
    finales = {r["chunk_id"]: r for to in ctx["por_to"] for r in jl(TRABAJO / to / "finales.jsonl")}
    decision = {}
    for to, cids in ctx["por_to"].items():
        for cid in cids:
            ev = ratchet_e3.evaluar_veredicto(v_ini[cid]["tool_input"], ctx["chunks"][cid], ctx["unidades_corpus"][to],
                                              ctx["regs"][cid]["validacion"])
            decision[cid] = ("acepta" if ev["es_completo_ok"] or ev["aceptable"]
                             else "cola" if not ev["bloqueantes_utilizables"] else "reintenta")
    esperada = {cid: ("acepta" if d.startswith(("completo", "aceptado")) else "cola" if d.startswith("cola")
                      else "reintenta") for cid, d in esp["decision_con_o3"].items()}
    acepta_intento0 = sorted(cid for cid, f in finales.items() if f["n_reintentos"] == 0
                             and f["validacion_final"] is not None)
    res["2_verificaciones_y_reparto"] = {
        "sembrado": sem, "llamadas_de_verificacion": len(ver),
        "unidades_verificadas": len({x["chunk_id"] for x in ver}),
        "todas_aciertos_de_la_cache_local": all(x["hit_cache_local"] and x["fuente"] == "cache_local"
                                                and x["usd"] == 0 for x in ver),
        "veredicto_igual_a_o3": len(iguales_o3),
        "reparto": dict(Counter(decision.values())),
        "reparto_igual_al_esperado_por_unidad": decision == esperada,
        "aceptadas_con_el_intento0_en_finales": len(acepta_intento0),
        "estados_de_las_aceptadas": dict(Counter(finales[c]["estado"] for c in acepta_intento0)),
        "estado_de_cada_aceptada_igual_al_de_o3": all(finales[c]["estado"] == esp["decision_con_o3"][c]
                                                      for c in acepta_intento0)}
    r2 = res["2_verificaciones_y_reparto"]
    r2["ok"] = (sem["insertadas"] + sem["ya_presentes"] == 20 and sem["iguales_a_o3"] == 20
                and r2["unidades_verificadas"] == 20 and r2["todas_aciertos_de_la_cache_local"]
                and r2["veredicto_igual_a_o3"] == 20 and r2["reparto"] == {"acepta": 16, "reintenta": 3, "cola": 1}
                and r2["reparto_igual_al_esperado_por_unidad"] and len(acepta_intento0) == 16
                and r2["estado_de_cada_aceptada_igual_al_de_o3"])

    # 3. re-verificaciones de las que reintentan, contra O3 y contra la tanda 0
    t0_rever = {}
    for to in ctx["por_to"]:
        for r in jl(C.SALIDA_T0 / to / "veredictos.jsonl"):
            if r["fase"] == "re_verificacion" and r["chunk_id"] in ctx["unidades"]:
                t0_rever[r["chunk_id"]] = r

    def corto(r):
        if r is None:
            return None
        return {"veredicto": (r.get("tool_input") or {}).get("veredicto"), "faltantes": r.get("n_faltantes"),
                "bloqueantes": r.get("n_bloqueantes"), "residuales": r.get("n_residuales"),
                "aceptable": r.get("aceptable"),
                "tipos": [(f.get("tipo"), f.get("severidad"), f.get("cita_verificada"), f.get("bloqueante"))
                          for f in r.get("faltantes") or []]}
    o3_ev = {r["chunk_id"]: r["evaluacion"] for r in jl(C.O3A / "evaluacion_e3_o3.jsonl")}
    rever = {}
    for to in ctx["por_to"]:
        for r in veredictos[to]:
            if r["fase"] == "re_verificacion":
                rever[r["chunk_id"]] = r
    res["3_reverificaciones"] = {
        cid: {"estado_final_r0": finales[cid]["estado"], "n_reintentos": finales[cid]["n_reintentos"],
              "residuales_r0": len(finales[cid].get("residuales") or []),
              "reverificacion_r0": corto(rever.get(cid)),
              "verificacion_o3_intento0": {"veredicto": (o3[cid]["tool_input"] or {}).get("veredicto"),
                                           "faltantes": len(o3_ev[cid]["faltantes"]),
                                           "bloqueantes": len(o3_ev[cid]["faltantes_bloqueantes"])},
              "reverificacion_tanda0": corto(t0_rever.get(cid)),
              "estado_tanda0": json.loads([x for x in (C.SALIDA_T0 / to / "finales.jsonl").read_text(
                  encoding="utf-8").splitlines() if json.loads(x)["chunk_id"] == cid][-1])["estado"]}
        for to, cids in ctx["por_to"].items() for cid in cids if decision[cid] == "reintenta"}

    # 4. reintentos solo donde los manda el ratchet
    rein = {r["chunk_id"] for to in ctx["por_to"] for r in jl(TRABAJO / to / C.RC.REINTENTOS_E3)}
    e1r = Counter(x["chunk_id"] for x in llam if x["tipo"] == "e1r")
    con_n = {cid for cid, f in finales.items() if f["n_reintentos"]}
    manda = {cid for cid, d in decision.items() if d == "reintenta"}
    res["4_reintentos"] = {"mandados_por_el_ratchet": sorted(manda), "en_reintentos_e3": sorted(rein),
                           "con_n_reintentos_en_finales": sorted(con_n), "llamadas_e1r_por_unidad": dict(e1r),
                           "ok": rein == con_n == manda == set(e1r)}

    # 5. costo real desde el log de usage
    resp_log = (a.respaldos / "cache_usage.jsonl").read_bytes()
    log = LOG.read_bytes()
    nuevas = [json.loads(x) for x in log[len(resp_log):].decode("utf-8").splitlines() if x.strip()]
    por_comp = Counter(x["component"] for x in nuevas)
    costo_log = sum(usd(x, PRECIOS[x["component"]]) for x in nuevas)
    misses = [x for x in llam if not x["hit_cache_local"]]
    res["5_costo"] = {"log_es_el_respaldo_mas_lineas_nuevas": log.startswith(resp_log),
                      "lineas_nuevas": len(nuevas), "por_componente": dict(por_comp),
                      "usd_desde_el_log": round(costo_log, 6),
                      "usd_por_componente": {k: round(sum(usd(x, PRECIOS[k]) for x in nuevas if x["component"] == k), 6)
                                             for k in por_comp},
                      "presupuesto_compartido_usd": resumen["gasto_compartido_usd"],
                      "registro_de_llamadas_usd": round(sum(x["usd"] for x in llam), 6),
                      "llamadas_a_la_api_en_el_registro": len(misses),
                      "tokens_de_las_llamadas_nuevas": {k: sum((x.get(k) or 0) for x in nuevas) for k in (
                          "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}}
    r5 = res["5_costo"]
    r5["ok"] = (r5["log_es_el_respaldo_mas_lineas_nuevas"] and r5["lineas_nuevas"] == len(misses)
                and abs(r5["usd_desde_el_log"] - r5["presupuesto_compartido_usd"]) < 1e-6
                and abs(r5["usd_desde_el_log"] - r5["registro_de_llamadas_usd"]) < 1e-5
                and r5["usd_desde_el_log"] <= resumen["tope_usd"])

    # 6. filas nuevas de las bases y modelos
    out6 = {}
    for nombre, actual in (("e3_verificacion.db", cliente_e3.DB_PATH), ("e1_reintentos.db", RC.DB_REINTENTOS_E1)):
        antes, despues = filas(a.respaldos / nombre), filas(actual)
        nuevas_k = sorted(set(despues) - set(antes))
        out6[nombre] = {"filas_antes": len(antes), "filas_despues": len(despues), "nuevas": len(nuevas_k),
                        "borradas_o_cambiadas": sum(1 for k in antes if despues.get(k) != antes[k]),
                        "modelos_nuevas": dict(Counter(despues[k][1] for k in nuevas_k)),
                        "namespaces_nuevas": dict(Counter(despues[k][0] for k in nuevas_k)),
                        "claves_nuevas": nuevas_k}
    sembradas = {v["clave"] for v in esp["verificacion"].values()}
    e3n = set(out6["e3_verificacion.db"]["claves_nuevas"])
    out6["sembradas_entre_las_nuevas_de_e3"] = len(sembradas & e3n)
    out6["nuevas_de_e3_que_no_son_sembradas"] = len(e3n - sembradas)
    out6["modelos_en_el_registro"] = {f"{t}|{m}": n for (t, m), n in
                                      Counter((x["tipo"], x["modelo_respuesta"]) for x in llam).items()}
    e3_misses = sum(1 for x in misses if x["tipo"] == "e3")
    e1_misses = sum(1 for x in misses if x["tipo"] == "e1r")
    out6["ok"] = (out6["e3_verificacion.db"]["borradas_o_cambiadas"] == 0
                  and out6["e1_reintentos.db"]["borradas_o_cambiadas"] == 0
                  and out6["sembradas_entre_las_nuevas_de_e3"] == sem["insertadas"]
                  and out6["nuevas_de_e3_que_no_son_sembradas"] == e3_misses
                  and out6["e1_reintentos.db"]["nuevas"] == e1_misses
                  and all(m == C.MODELO_RESPUESTA[t] for t, m in ((x["tipo"], x["modelo_respuesta"]) for x in llam)))
    res["6_bases_y_modelos"] = out6

    # renglones de la carpeta de trabajo, todos de las 20
    ren = {}
    for to in ctx["por_to"]:
        for n in C.ARCHIVOS_ANEXO:
            p = TRABAJO / to / n
            if p.exists():
                ids = [json.loads(x)["chunk_id"] for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
                ren[f"{to}/{n}"] = {"renglones": len(ids), "todos_de_las_20": set(ids) <= ctx["unidades"]}
    res["renglones_de_la_carpeta_de_trabajo"] = ren
    res["estados_finales"] = dict(Counter(f["estado"] for f in finales.values()))
    res["estados_por_to"] = {to: dict(Counter(finales[c]["estado"] for c in cids)) for to, cids in ctx["por_to"].items()}
    res["ok"] = all(res[k]["ok"] for k in ("1_e1_intento0", "2_verificaciones_y_reparto", "4_reintentos", "5_costo",
                                           "6_bases_y_modelos")) and all(x["todos_de_las_20"] for x in ren.values())
    a.salida.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v.get("ok") if isinstance(v, dict) and "ok" in v else v) for k, v in res.items()
                      if k not in ("3_reverificaciones", "renglones_de_la_carpeta_de_trabajo")}, ensure_ascii=False))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
