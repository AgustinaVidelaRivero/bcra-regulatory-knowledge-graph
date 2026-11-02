"""Resumen de los censos de S2 (U-SEG-OFICIAL) sobre la E0 corregida: renglones (4.f), hallazgo 1.16 y límites de
sub-documento, con las detecciones de la tanda 1 (agregado 3 del «seguí»). Solo lectura; sin texto en la salida.

Uso: python -B resumen_censos_S2.py --lote <dir de lote_tramo2_S2b.sh> --e0 <E0 corregida> --raiz <copia del repo>
       --lista <s2/lista_tanda1_S2.json> --out <json>

Lee del lote `censo_renglones_S2b.json` (de `s1bis/scripts/censo_renglones_S1bis.py`, sin editar), `detector_116_S2b.json`
(de `s0_5/scripts/detector_116.py`) y `censo_sd_152_S2b.json` (de `s0_4/scripts/censo_sd_152.py`), y sus logs. Toma de
cada uno solo cuentas, ids y páginas: los tres traen texto del PDF (renglones, títulos, cierres) que no se copia.
Al lado, las cifras de antes que da el mandato (`docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md:665-672`) y las de S1-bis
(`s1bis/censo_renglones_S1bis.json`), como referencia: no reemplazan a las de la E0 corregida.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

S = "data/experiment/segmentacion_oficial_e0r2"
ANTES_SD_T1 = {"manori": 8, "ri_oc": 3, "ri_rml": 3, "ri_gerc": 1, "ri_pgn": 1, "snp_tr": 1}
ANTES_116_T1 = {"depaho": 8, "lingeef": 8, "ayccef": 5, "cajasc": 4, "adrei": 2, "manori": 2, "cirmo3": 1, "efemin": 1,
                "ri_rml": 1, "snp_tr": 1}


def miles(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("--lote", "--e0", "--raiz", "--lista", "--out"):
        ap.add_argument(k, type=Path, required=True)
    a = ap.parse_args()
    cr = cargar(a.lote / "censo_renglones_S2b.json")
    de = cargar(a.lote / "detector_116_S2b.json")
    sd = cargar(a.lote / "censo_sd_152_S2b.json")
    s1b = cargar(a.raiz / S / "s1bis/censo_renglones_S1bis.json")
    t1 = [f["to"] for f in cargar(a.lista)["filas"]]
    assert len(t1) == 20
    # renglones
    h = cr["hallazgo_1_16"]
    reng = {"renglones_pdf": cr["renglones_pdf"], "censo_total": cr["censo_total"], "censo_por_clase": cr["censo_por_clase"],
            "paginas": cr["paginas_con_renglones_en_el_censo"], "tos_con_renglones": sum(1 for v in cr["censo_por_to"].values() if v),
            "censo_por_to": {t: v for t, v in sorted(cr["censo_por_to"].items()) if v},
            "renglones_de_unidades_sin_par_en_el_pdf": cr["renglones_de_unidades_sin_par_en_el_pdf"],
            "calibracion_pro": h.get("calibracion_pro"), "listas_con_items_sin_chunk": h.get("listas_con_items_sin_chunk", {}).get("listas"),
            "s1bis": {"censo_total": s1b["censo_total"], "censo_por_clase": s1b["censo_por_clase"],
                      "paginas": s1b["paginas_con_renglones_en_el_censo"],
                      "tos_con_renglones": sum(1 for v in s1b["censo_por_to"].values() if v)}}
    por_to_116 = Counter(x["id"].split("::")[0] for x in h["lista"])
    c116 = {"casos": h["casos"], "tos": h["tos"], "por_to": dict(sorted(por_to_116.items())),
            "tanda1": {t: por_to_116.get(t, 0) for t in t1 if por_to_116.get(t)},
            "tanda1_lista": [{"id": x["id"], "paginas": x["paginas"]} for x in h["lista"] if x["id"].split("::")[0] in t1]}
    c116["tanda1_casos"] = sum(c116["tanda1"].values())
    det = {k: de[k] for k in ("tos_revisados", "original", "corregido", "union", "solo_original") if k in de}
    det_t1 = Counter(x["id"].split("::")[0] for x in de["candidatos"] if x["id"].split("::")[0] in t1)
    det["tanda1"] = dict(sorted(det_t1.items()))
    det["tanda1_lista"] = [{"id": x["id"], "paginas": x["paginas"], "criterio": x.get("criterio"), "origen": x.get("origen")}
                           for x in de["candidatos"] if x["id"].split("::")[0] in t1]
    # sub-documentos
    lista = set(sd["lista"])
    limites = {t: [{"pagina": x["pagina"], "forma": x["forma"], "prefijo": x.get("prefijo")} for x in v] for t, v in sd["por_to"].items()
               if isinstance(v, list)}
    errores = {t: v for t, v in sd["por_to"].items() if isinstance(v, dict) and v.get("error")}
    # ¿la regla A de S0-6a ya abre algo en la página del límite? (avisos de A en estructura)
    abre_a = {}
    for t, v in limites.items():
        est = cargar(a.e0 / f"estructura_{t}.json")
        pags = {x.get("pagina") for x in est["avisos"] if x["tipo"] in ("division_a", "adoptado_a") and x.get("pagina") is not None}
        abre_a[t] = sum(1 for x in v if x["pagina"] in pags)
    fuera = {t: v for t, v in limites.items() if t not in lista}
    sdr = {"tos_con_limites": len(limites), "limites": sum(len(v) for v in limites.values()),
           "lista_de_la_regla": sorted(lista), "errores": sorted(errores),
           "fuera_de_la_lista": {"tos": len(fuera), "limites": sum(len(v) for v in fuera.values()),
                                 "por_forma": dict(Counter(x["forma"] for v in fuera.values() for x in v)),
                                 "por_to": {t: dict(Counter(x["forma"] for x in v)) for t, v in sorted(fuera.items())},
                                 "en_pagina_donde_A_ya_abre": sum(abre_a[t] for t in fuera)},
           "en_la_lista": {"tos": sum(1 for t in limites if t in lista), "limites": sum(len(v) for t, v in limites.items() if t in lista),
                           "por_forma": dict(Counter(x["forma"] for t, v in limites.items() if t in lista for x in v))},
           "tanda1": {t: {"limites": len(limites[t]), "por_forma": dict(Counter(x["forma"] for x in limites[t])),
                          "paginas": sorted({x["pagina"] for x in limites[t]}), "en_la_lista": t in lista,
                          "en_pagina_donde_A_ya_abre": abre_a[t]} for t in t1 if limites.get(t)},
           "nota_g3": "cruce_g3 del censo se calcula contra s0_3/censos/g3_raices_sucesoras_rechazadas.json, de S0-3, anterior a "
                      "la regla E de S0-6a: no lo uso"}
    sdr["tanda1_fuera_de_la_lista"] = {"tos": sum(1 for t, v in sdr["tanda1"].items() if not v["en_la_lista"]),
                                       "limites": sum(v["limites"] for v in sdr["tanda1"].values() if not v["en_la_lista"])}
    out = {"fuentes": {n: sha(a.lote / n) for n in ("censo_renglones_S2b.json", "detector_116_S2b.json", "censo_sd_152_S2b.json")},
           "e0_conteos_sha256": sha(a.e0 / "conteos.json"), "renglones": reng, "hallazgo_1_16": c116, "detector_116": det,
           "subdocumentos": sdr}
    # texto
    m = []
    m.append(f"**El censo de renglones** (`censos_S2b.json`, `renglones`), con `s1bis/scripts/censo_renglones_S1bis.py` sin editar y su "
             "regla (`s1bis/regla_censo_renglones_S1bis.md`), sobre la E0 corregida y un caché de renglones regenerado con su "
             "`e0_lib` (`s0_1/scripts/lineas_152.py`). Corre igual: los mismos insumos que en S1-bis (la E0 plana, el manifiesto de "
             "los 152, el caché, las dos reglas y `salida_tanda0_r2b` para la calibración), rc 0.")
    cp = reng["calibracion_pro"] or {}
    m.append(f"- {reng['censo_total']} renglones del PDF que no están en ninguna unidad ni en un rol declarado, en {reng['paginas']} "
             f"páginas de {reng['tos_con_renglones']} TOs (de {miles(reng['renglones_pdf'])} renglones del PDF): "
             + ", ".join(f"{k} {v}" for k, v in reng["censo_por_clase"].items())
             + f" (`censo_por_clase`). Calibración con `pro::1.1.2.7`: {cp.get('encuentra_pro_1.1.2.7')}.")
    m.append(f"- Al lado, S1-bis, sobre la E0 de S0-4b: {reng['s1bis']['censo_total']} renglones en {reng['s1bis']['paginas']} páginas de "
             f"{reng['s1bis']['tos_con_renglones']} TOs (" + ", ".join(f"{k} {v}" for k, v in reng["s1bis"]["censo_por_clase"].items())
             + "). Referencia; no reemplaza la cifra de la E0 corregida.")
    m.append("- Por TO (`censo_por_to`): " + ", ".join(f"{t} {v}" for t, v in reng["censo_por_to"].items()) + ".")
    m.append(f"- Lo que no tiene explicación (clase `sin_unidad_ni_rol`, {reng['censo_por_clase'].get('sin_unidad_ni_rol', 0)}) "
             "se lee según la regla del censo (mandato, S1, punto 8); S2 no lo lee: el despacho pide la cifra.")
    out["texto_md_renglones"] = "\n".join(m)
    t = []
    t.append("Con el código de la E0 corregida, sobre su salida (`censos_S2b.json`). Son detecciones, no lecturas, con falsos positivos "
             "conocidos (mandato, `:670`). Al lado, las cifras de antes de la corrección de E0 que da el mandato para la tanda 1 "
             "(`:665-672`, con la lista de trabajo, que tenía a ri_oc y no a ri_mmsef).")
    t.append("")
    t.append("| TO | límites de sub-documento (antes) | formas | ¿en la lista de la regla? | en página donde A ya abre | candidatos 1.16, censo (antes) | candidatos 1.16, detector corregido |")
    t.append("|---|---|---|---|--:|---|--:|")
    for to in t1:
        s = sdr["tanda1"].get(to)
        antes = "en la lista: la regla los aplica" if s and s["en_la_lista"] else ANTES_SD_T1.get(to, 0)
        t.append(f"| {to}{' (sucesor)' if to == 'ri_mmsef' else ''} | {s['limites'] if s else 0} ({antes}) | "
                 f"{', '.join(f'{k} {v}' for k, v in s['por_forma'].items()) if s else '—'} | "
                 f"{('sí' if s['en_la_lista'] else 'no') if s else '—'} | {s['en_pagina_donde_A_ya_abre'] if s else 0} | "
                 f"{c116['tanda1'].get(to, 0)} ({ANTES_116_T1.get(to, 0)}) | {det['tanda1'].get(to, 0)} |")
    t.append(f"| ri_oc (salió) | — ({ANTES_SD_T1['ri_oc']}) | | | | — (0) | |")
    tf = sdr["tanda1_fuera_de_la_lista"]
    t.append("")
    t.append(f"- **Límites de sub-documento** (`subdocumentos`, de `s0_4/scripts/censo_sd_152.py`): en la tanda 1, "
             f"{sum(v['limites'] for v in sdr['tanda1'].values())} en {len(sdr['tanda1'])} TOs; fuera de la lista de la regla, que son los "
             f"que quedan como detección, {tf['limites']} en {tf['tos']} TOs. Antes: 17 en 6 TOs, todos fuera de la lista. En los 152: "
             f"{sdr['limites']} límites en {sdr['tos_con_limites']} TOs; fuera de la lista, {sdr['fuera_de_la_lista']['limites']} en "
             f"{sdr['fuera_de_la_lista']['tos']} (" + ", ".join(f"{k} {v}" for k, v in sdr["fuera_de_la_lista"]["por_forma"].items())
             + f"), {sdr['fuera_de_la_lista']['en_pagina_donde_A_ya_abre']} de ellos en una página donde la regla A de S0-6a ya abre una "
             "división. " + sdr["nota_g3"] + ".")
    t.append(f"- **Candidatos del hallazgo 1.16** con el criterio del censo de renglones (`hallazgo_1_16`, el original): en la tanda 1, "
             f"{c116['tanda1_casos']} en {len(c116['tanda1'])} TOs; antes, 33 en 10. En los 152: {c116['casos']} en {c116['tos']} TOs. Con el "
             f"detector corregido de S0-5a (`detector_116`, el que usó S1-ter): {sum(det['tanda1'].values())} en {len(det['tanda1'])} TOs de "
             f"la tanda 1; en los 152, " + ", ".join(f"{k} {v}" for k, v in det.items() if k in ("original", "corregido", "union")) + ".")
    t.append(f"- **ri_mmsef, el sucesor:** {sdr['tanda1'].get('ri_mmsef', {}).get('limites', 0)} límites de sub-documento y "
             f"{c116['tanda1'].get('ri_mmsef', 0)} candidatos del 1.16 por el censo ({det['tanda1'].get('ri_mmsef', 0)} por el detector "
             "corregido). Las listas, con ids y páginas, en `hallazgo_1_16.tanda1_lista`, `detector_116.tanda1_lista` y "
             "`subdocumentos.tanda1`.")
    out["texto_md_tanda1"] = "\n".join(t)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out["texto_md_renglones"])
    print(out["texto_md_tanda1"])


if __name__ == "__main__":
    main()
