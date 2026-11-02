"""
recompute_politica_enm01.py — Recomputo DERIVADO de la mini-recalibración
enm01 bajo los laudos A (solo 'alta' bloquea; media/baja son residuales
declarados) y B (guardia estructural de bloques ordenadores). Código puro:
re-evalúa los tool_input PERSISTIDOS de salida/faseB_pro_enm01/veredictos.jsonl
con la capa determinística nueva (ratchet_e3.evaluar_veredicto) — sin ninguna
llamada a API.

El número que produce es DERIVADO de la política sobre los veredictos ya
pagados: la P2 medida de la corrida (21,8 %) queda como está — refutada
contra el <10 % pre-declarado. Este recomputo responde qué cola habría
dejado el MISMO material bajo la política laudada.

Caveat declarado: para las unidades que la corrida real reintentó, el
feedback inyectado fue el de la política vieja (todos los faltantes con cita
verificada — un SUPERSET del que la política nueva inyectaría, que lleva solo
los bloqueantes). La re-verificación persistida es la evidencia disponible y
se usa tal cual; un reintento con feedback más chico podría diferir. Las
unidades que la política nueva acepta EN BASE no dependen del caveat.

Derivación por unidad (trayectoria):
  1. ev_base = evaluar_veredicto(tool_input base, chunk, unidades_corpus)
     - es_completo_ok            → completo_ok_directo
     - aceptable (sin bloqueantes) → aceptado_con_residuales
  2. con bloqueantes:
     - sin bloqueante con cita verificada → cola_humana_veredicto_inutilizable
     - con re-verificación persistida: ev_re aceptable/ok →
       aceptado_tras_reintento; si no → cola_humana (alta persistente)
     - la corrida vieja reintentó siempre que hubiera ALGÚN faltante
       utilizable (⊇ condición nueva), así que la re-verificación existe para
       toda unidad que la política nueva reintentaría; se asertá.

Uso:  .venv/bin/python3 recompute_politica_enm01.py
      (escribe salida/faseB_pro_enm01/recompute_politica_laudos.json)
"""

from __future__ import annotations

import json
from collections import Counter

import comun_e3
from comun_e3 import BASE, E0_SALIDA_ENM01, cargar_chunks
import ratchet_e3
import prompt_e3

OUT_DIR = BASE / "salida" / "faseB_pro_enm01"

# Las 15 unidades que ENTRARON nuevas a la cola medida (no estaban en la cola
# real sellada de 26; analisis_enm01 §P2, reproducible desde
# salida/remedicion_citas/resumen_remedicion.json → cola_real_chunk_ids).
COLA_NUEVAS_MEDIDAS = [
    "pro::1.1.2.3", "pro::2.2.2", "pro::2.2.4.1", "pro::2.3.3", "pro::2.3.14",
    "pro::2.7::intro", "pro::2.7::cierre", "pro::3.2.1.2", "pro::3.2.3::intro",
    "pro::3.2.3.2", "pro::3.2.3.7", "pro::4.2.1.1", "pro::4.2.1.2",
    "pro::4.2.1.6", "pro::4.2.2",
]


def main() -> None:
    chunks = {c["id"]: c for c in cargar_chunks(("pro",), e0_dir=E0_SALIDA_ENM01)}
    unidades_corpus = {c["unidad"] for c in chunks.values()}

    veredictos = [json.loads(l) for l in
                  (OUT_DIR / "veredictos.jsonl").open(encoding="utf-8")]
    finales = [json.loads(l) for l in
               (OUT_DIR / "extracciones_finales.jsonl").open(encoding="utf-8")]
    estado_medido = {r["chunk_id"]: r["estado"] for r in finales}

    base = {v["chunk_id"]: v for v in veredictos
            if v["fase"] == "verificacion" and v["intento"] == 0}
    rever = {v["chunk_id"]: v for v in veredictos
             if v["fase"] == "re_verificacion"}
    assert len(base) == 101, f"esperados 101 veredictos base, hay {len(base)}"

    derivado: dict[str, dict] = {}
    for cid, v in base.items():
        chunk = chunks[cid]
        ev = ratchet_e3.evaluar_veredicto(v["tool_input"], chunk, unidades_corpus)
        reg = {"clase": "mini" if chunk["tipo"] == "mini_chunk" else "punto",
               "residuales": 0, "estructurales": 0, "reintento_usado": False}
        if ev["es_completo_ok"]:
            reg["estado"] = "completo_ok_directo"
        elif ev["aceptable"]:
            reg["estado"] = "aceptado_con_residuales"
            reg["residuales"] = len(ev["residuales"])
            reg["estructurales"] = sum(
                1 for f in ev["residuales"] if f["estructural_no_bloqueante"])
        elif not ev["bloqueantes_utilizables"]:
            reg["estado"] = "cola_humana_veredicto_inutilizable"
        else:
            reg["reintento_usado"] = True
            v_re = rever.get(cid)
            assert v_re is not None, (
                f"{cid}: la política nueva reintentaría pero la corrida no "
                f"persistió re-verificación (estado medido: {estado_medido[cid]})")
            ev_re = ratchet_e3.evaluar_veredicto(v_re["tool_input"], chunk,
                                                 unidades_corpus)
            if ev_re["es_completo_ok"]:
                reg["estado"] = "aceptado_tras_reintento"
            elif ev_re["aceptable"]:
                reg["estado"] = "aceptado_tras_reintento"
                reg["residuales"] = len(ev_re["residuales"])
                reg["estructurales"] = sum(
                    1 for f in ev_re["residuales"] if f["estructural_no_bloqueante"])
            elif not ev_re["bloqueantes_utilizables"]:
                reg["estado"] = "cola_humana_veredicto_inutilizable"
            else:
                reg["estado"] = "cola_humana"
        derivado[cid] = reg

    estados = Counter(r["estado"] for r in derivado.values())
    por_clase = {"punto": Counter(), "mini": Counter()}
    for r in derivado.values():
        por_clase[r["clase"]][r["estado"]] += 1

    cola_ids = sorted(cid for cid, r in derivado.items()
                      if r["estado"].startswith("cola_humana"))
    n = len(derivado)
    aceptadas_residuales = [cid for cid, r in derivado.items()
                            if r["estado"] == "aceptado_con_residuales"]
    residuales_total = sum(r["residuales"] for r in derivado.values())
    estructurales_total = sum(r["estructurales"] for r in derivado.values())
    reintentos_necesarios = sum(1 for r in derivado.values() if r["reintento_usado"])

    nuevas_que_quedan = [cid for cid in COLA_NUEVAS_MEDIDAS
                         if derivado[cid]["estado"].startswith("cola_humana")]
    medida_cola = [cid for cid, e in estado_medido.items()
                   if e.startswith("cola_humana")]
    de_la_cola_medida_quedan = [cid for cid in medida_cola
                                if derivado[cid]["estado"].startswith("cola_humana")]

    res = {
        "politica": "LAUDO A (solo 'alta' bloquea; media/baja residuales) + "
                    "LAUDO B (guardia estructural de bloques ordenadores)",
        "caracter": "DERIVADO de los veredictos persistidos de la corrida "
                    "enm01 — la P2 MEDIDA (21,8 %) no se re-escribe: sigue "
                    "refutada contra el <10 % pre-declarado",
        "caveat_feedback": "los reintentos persistidos usaron feedback de la "
                           "política vieja (superset del nuevo)",
        "n_unidades": n,
        "estados_derivados": dict(estados),
        "estados_derivados_por_clase": {k: dict(v) for k, v in por_clase.items()},
        "cola_derivada": {
            "n": len(cola_ids),
            "tasa_sobre_total": round(len(cola_ids) / n, 4),
            "ids": cola_ids,
            "desglose": {
                "cola_por_alta_persistente": estados.get("cola_humana", 0),
                "inutilizables": estados.get("cola_humana_veredicto_inutilizable", 0),
            },
        },
        "aceptadas_con_residuales": {
            "n_base": len(aceptadas_residuales),
            "ids_base": sorted(aceptadas_residuales),
            "residuales_declarados_total": residuales_total,
            "de_los_cuales_estructural_no_bloqueante": estructurales_total,
        },
        "reintentos_bajo_politica_nueva": {
            "necesarios": reintentos_necesarios,
            "medidos_en_corrida": 41,
        },
        "contra_la_cola_medida": {
            "cola_medida_n": len(medida_cola),
            "quedan_en_cola": len(de_la_cola_medida_quedan),
            "ids_quedan": sorted(de_la_cola_medida_quedan),
            "de_las_15_nuevas_medidas_quedan": len(nuevas_que_quedan),
            "ids_nuevas_que_quedan": sorted(nuevas_que_quedan),
        },
        "referencias": {
            "tasa_cola_medida_enm01": 0.2178,
            "tasa_cola_sellada": 0.2989,
            "prediccion_p2_predeclarada": "< 0.10 (REFUTADA en la medición)",
        },
        "prefijo_hash_e3": prompt_e3.PREFIJO_HASH,
        "derivado_por_unidad": derivado,
    }
    out = OUT_DIR / "recompute_politica_laudos.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in
                      ("estados_derivados", "estados_derivados_por_clase",
                       "cola_derivada", "aceptadas_con_residuales",
                       "reintentos_bajo_politica_nueva", "contra_la_cola_medida",
                       "prefijo_hash_e3")},
                     ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
