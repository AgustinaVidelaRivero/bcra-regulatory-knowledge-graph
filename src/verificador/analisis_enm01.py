"""
analisis_enm01.py — Análisis de la mini-recalibración de la enmienda 01
contra las predicciones refutables de §3 de la enmienda. Código puro, solo
lectura de las salidas _enm01 y de la corrida sellada (referencias).

Reporta (en orden del mandato):
  P1 — destino de la familia: faltantes base de HIJOS cuya cita verifica SOLO
       en la prosa heredada (esperado ~0 por construcción: esa prosa ya no
       está en el fuente del hijo) + qué encontró E3 en los MINI-CHUNKS.
  P2 — cola real nueva sobre el total de unidades vs <10 % pre-declarado y
       29,9 % de referencia.
  P3 — costo real vs corrida sellada (0,73 + 2,14) y vs estimación (2,60).
  (4) distribución de veredictos por tipo de unidad · reintentos ·
      verificación de citas · caching por namespace.

Uso:  .venv/bin/python3 analisis_enm01.py   (escribe salida/faseB_pro_enm01/analisis_enm01.json)
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter

import comun_e3
from comun_e3 import BASE, E0_SALIDA_ENM01, cargar_chunks

E1_ENM01 = comun_e3.E1_DIR / "salida" / "faseB_pro_enm01"
OUT_DIR = BASE / "salida" / "faseB_pro_enm01"


def _norm(s: str) -> str:
    s = s.replace("-\n", "")
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return "".join(s.lower().split())


def main() -> None:
    chunks = {c["id"]: c for c in cargar_chunks(("pro",), e0_dir=E0_SALIDA_ENM01)}
    veredictos = [json.loads(l) for l in
                  (OUT_DIR / "veredictos.jsonl").open(encoding="utf-8")]
    finales = [json.loads(l) for l in
               (OUT_DIR / "extracciones_finales.jsonl").open(encoding="utf-8")]
    resumen_e3 = json.loads((OUT_DIR / "resumen_faseB_e3.json").read_text(encoding="utf-8"))
    resumen_e1 = json.loads((E1_ENM01 / "resumen_faseB.json").read_text(encoding="utf-8"))

    clase = {cid: ("mini" if c["tipo"] == "mini_chunk" else "punto")
             for cid, c in chunks.items()}

    # ---------------- P1: destino de la familia ---------------- #
    fam_hijos = []      # faltantes base de hijos que verifican SOLO en prosa heredada
    faltantes_minis = []
    base = [v for v in veredictos if v["fase"] == "verificacion" and v["intento"] == 0]
    for v in base:
        c = chunks[v["chunk_id"]]
        if clase[v["chunk_id"]] == "mini":
            for f in v["faltantes"]:
                faltantes_minis.append({
                    "chunk_id": v["chunk_id"], "tipo": f.get("tipo"),
                    "severidad": f.get("severidad"),
                    "cita_verificada": f.get("cita_verificada"),
                    "cita": (f.get("cita_textual_del_fuente") or "")[:120],
                })
            continue
        prosa_her = _norm("\n".join(b["texto"] for b in c["herencia"]
                                    if b["tipo"] != "encabezado"))
        propio = _norm(c["texto"])
        for f in v["faltantes"]:
            q = _norm(f.get("cita_textual_del_fuente") or "")
            if q and prosa_her and q in prosa_her and q not in propio:
                fam_hijos.append({"chunk_id": v["chunk_id"],
                                  "tipo": f.get("tipo"),
                                  "cita_verificada": f.get("cita_verificada"),
                                  "cita": (f.get("cita_textual_del_fuente") or "")[:120]})

    # ---------------- P2: cola real ---------------- #
    estados = Counter(r["estado"] for r in finales)
    n = len(finales)
    cola = sum(v for k, v in estados.items() if k.startswith("cola_humana"))
    # rechazados de fan-in E1 (unidades que no llegaron a E3) también son cola
    n_unidades_e0 = len(chunks)
    no_llegaron = n_unidades_e0 - n

    # ---------------- (4) distribución / reintentos / citas ---------------- #
    dist = {"punto": Counter(), "mini": Counter()}
    reintentos = Counter()
    for r in finales:
        dist[clase[r["chunk_id"]]][r["estado"]] += 1
        reintentos[r["n_reintentos"]] += 1

    faltantes_base_por_clase = {"punto": 0, "mini": 0}
    unidades_con_faltantes = {"punto": 0, "mini": 0}
    for v in base:
        cl = clase[v["chunk_id"]]
        faltantes_base_por_clase[cl] += len(v["faltantes"])
        if v["faltantes"]:
            unidades_con_faltantes[cl] += 1

    citas = resumen_e3["citas"]

    res = {
        "P1_familia": {
            "faltantes_base_hijos_solo_en_prosa_heredada": len(fam_hijos),
            "detalle_hijos": fam_hijos,
            "referencia_sellada": "60/117 en 27 unidades",
            "faltantes_base_en_minis": len(faltantes_minis),
            "minis_con_faltantes": unidades_con_faltantes["mini"],
            "detalle_minis": faltantes_minis,
        },
        "P2_cola": {
            "unidades_e0": n_unidades_e0,
            "verificadas_e3": n,
            "no_llegaron_a_e3_fanin": no_llegaron,
            "cola_humana_total": cola,
            "estados": dict(estados),
            "tasa_cola_sobre_verificadas": round(cola / n, 4) if n else None,
            "tasa_cola_sobre_total_unidades": round((cola + no_llegaron) / n_unidades_e0, 4),
            "prediccion_predeclarada": "< 0.10",
            "referencia_sellada": 0.2989,
        },
        "P3_costo": {
            "e1_reextraccion_usd": resumen_e1["cliente"]["gasto_usd_real"],
            "e3_mas_reintentos_usd": resumen_e3["gasto_e3_runner_usd"],
            "total_usd": resumen_e3["gasto_fase_b_total_usd"],
            "referencia_sellada": {"e1": 0.73, "e3_mas_reintentos": 2.14, "total": 2.87},
            "estimacion_previa_usd": 2.60,
        },
        "distribucion_por_tipo_unidad": {
            "estados": {k: dict(v) for k, v in dist.items()},
            "veredicto_base_faltantes": faltantes_base_por_clase,
            "veredicto_base_unidades_con_faltantes": unidades_con_faltantes,
        },
        "reintentos": {"por_n": dict(reintentos),
                       "llamadas_e1_reintento": resumen_e3["cliente_e1_reintentos"]["llamadas"]},
        "citas": citas,
        "caching": {
            "e1_reextraccion": {
                "namespace": resumen_e1["cliente"]["cache_stats"],
                "llamada_1": resumen_e1["caching"]["llamada_1"],
                "llamadas_2_en_adelante": resumen_e1["caching"]["llamadas_2_en_adelante"],
            },
            "e3": resumen_e3["cliente_e3"]["cache_stats"],
            "e1_reintentos": resumen_e3["cliente_e1_reintentos"]["cache_stats"],
        },
    }
    out = OUT_DIR / "analisis_enm01.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
