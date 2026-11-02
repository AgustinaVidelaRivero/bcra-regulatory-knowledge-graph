"""U-SEG-OFICIAL, S1-ter.6: las poblaciones de la lectura de S1-ter, SIN SORTEAR (USD 0, sin API).

Uso: python -B poblaciones_S1ter.py --e0 <salida de S1-ter (corrida 1)> --e0-s04b <salida de S0-4b (s1bis/e0)>
       --manifiesto <manifiesto de S1-ter> --detector <censos/detector_116_sobre_S0-5b.json>
       --s1bis-censo <s1bis/comparacion_censos_S1bis.json> --s1bis-planilla-116 <planilla del 1.16 de S1-bis>
       --s1bis-muestra <s1bis/muestra_cortes_S1bis.json> --lista-r5a <lista de R5-a por lista, v2, de la mesa>
       --limites-s05 <s0_5/bis/censos/limites_S0-5a-bis.json> --out <json>

No sortea, no lee y no marca: el sorteo, las fichas y el orden son del tramo b. Fija las poblaciones con el sha256 de la
lista de ids ordenados (`sorted` de Python) de cada una, para que el sorteo del tramo b se controle contra ellas.

1. Lectura de cortes (nota del mandato de `2faff14`, precisiones de `26c6502`; S1-ter, despacho del tramo a):
   - tres estratos del primer grupo, por el valor literal de `modo_lectura` de `conteos_b584.json` (en el manifiesto):
     `vigente`, `marcadores` y `sin_raiz`, con las unidades de los TOs reconocidos plenos (clase de
     `particion_152.json`, en el manifiesto) y, en `sin_raiz`, las de ri_spi (decisión 5 de la autora del 09/10/2026:
     reconocido pleno; su `modo_lectura` es `sin_raiz`); tamaños 40 / 10 / 40; peso = unidades del estrato / unidades
     de los tres; la semilla del tramo b es `U-SEG-OFICIAL:cortes:S1-ter:{estrato}` con el nombre literal del estrato;
   - el control de la condición de ri_spi (el título partido de su apartado C, corregido por S0-5): el chapeau de un
     renglón de SB y de SC en S0-4b y en S1-ter, y el título heredado por las unidades de cada apartado;
   - aparte, como información: los TOs de la tanda 0 de cada estrato, los límites declarados que caen en la
     población (FRENO de S0-4b y `limites_S0-5a-bis.json`) con las esperadas en la muestra, y las unidades de la
     muestra de S1-bis que están en la población (con su estrato y si su unidad cambió de S0-4b a S1-ter).
2. 1.16, población (a): los candidatos del detector corregido sobre la salida de S1-ter (unión del criterio original y
   la corrección), menos los 35 leídos en S1-bis (`s1bis/comparacion_censos_S1bis.json`, controlados contra los ids de
   la planilla del 1.16 de S1-bis, sin leer sus marcas) y los tres casos de diseño (`adfsp::1.1.10`, `ri_oc::B.2.4` y
   `ri_oc::B.3.4`).
3. 1.16, población (b), 36: las 34 listas que R5-a modificó por lista, menos los 9 casos (32 cierres confirmados y 2
   mixtos), de la lista v2 de la mesa (sha256 controlado acá), cada una como la dejó S0-5b (último ítem y cierre del
   padre); `ri_oc::S2`; y las 51 unidades de `ri_oc::3.1` a `ri_oc::3.51`, de las que el tramo b elige una.
   El id de cada entrada de (b) es el del último ítem de la lista (campo `lista` de la lista de la mesa), `ri_oc::S2`
   y el de la unidad elegida de la sección 3. Si el último ítem está partido por tamaño (no hay chunk con ese id), se
   registran sus partes (`<id>::parteN`), cada una con su cambio desde S0-4b.
4. Regresión: los 35 de S1-bis, como los dejó S0-5b, sin cifra.
5. Cruces, declarados: (a) con (b); (a) y (b) con los 35; la muestra de cortes de S1-bis con la población de cortes.
6. Fuera de la lectura de S1-ter (el despacho lee solo los tres estratos): los no segmentables salvo ri_spi y los
   parciales, con sus cinco archivos por TO comparados contra la salida de S0-4b.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

TAMANOS = {"vigente": 40, "marcadores": 10, "sin_raiz": 40}
TANDA0 = ("ctacte", "lingob", "polcre", "pagjub", "docvig")
TANDA1 = ("ayccef", "expaef", "opefci", "adrei", "ri_ccna", "ri_pgn", "ri_rml", "ri_gerc", "snp_cheq", "ceninf",
          "cirmo3", "snp_tr", "lingeef", "depaho", "cajasc", "manori", "efemin", "nmcief", "ri_dcpc", "ri_oc")
CASOS_DE_DISENO = ("adfsp::1.1.10", "ri_oc::B.2.4", "ri_oc::B.3.4")
SHA_LISTA_R5A = "5bec1dce51260844c9561b6201729736556bc1aa99efe1d068b2a139a84d24a8"
# límites declarados en el FRENO S0-4b, como los lista s1bis/scripts/poblacion_muestra_S1bis.py
LIMITES_CORTE_S04B = ("nmaeef::2.9", "ri_ccna::D1A3L2::S0", "ri_oc::A2::S0", "ri_oc::SA", "nmcief::A1P2::S0",
                      "nmcief::A1P4::S0", "ri_ccna::D2A1P1::S0", "ri_ccna::D2A1P2::S0", "ri_icpipsp::A1C1::S0",
                      "ri_icpipsp::A1C2::S0", "ri_icpipsp::A1C3::S0", "ri_ccna::D1A3L1::S0", "ri_oc::B.2::intro")
LIMITES_OTROS_S04B = ("ri_cc::RIP::S0", "ri_oc::SC::cierre", "nmcief::A6::S0", "manori::1.5.1")
LIMITES_CONOCIDOS_S1 = ("ri2_ae::3.3", "ri2_ae::5.3")
RE_SEC3_RI_OC = re.compile(r"^ri_oc::3\.(\d+)$")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def resumen(c: dict | None) -> dict | None:
    if c is None:
        return None
    return {"id": c["id"], "tipo": c["tipo"], "paginas": c["paginas"], "chars_propio": c["chars_propio"]}


def igual(a: dict | None, b: dict | None) -> bool:
    return bool(a and b and a["texto"] == b["texto"] and a["paginas"] == b["paginas"] and a["herencia"] == b["herencia"])


def cambio(a: dict | None, b: dict | None) -> bool | None:
    """None si la unidad no está en ninguna de las dos salidas."""
    return None if a is None and b is None else not igual(a, b)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0", "e0_s04b", "manifiesto", "detector", "s1bis_censo", "s1bis_planilla_116", "s1bis_muestra",
              "lista_r5a", "limites_s05", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    man = jl(a.manifiesto)
    tos_man = {t["id"]: t for t in man["tos"]}
    chunks = {to: jl(a.e0 / f"chunks_{to}.json") for to in tos_man}
    por_id = {c["id"]: c for ch in chunks.values() for c in ch}
    por_id_04b = {c["id"]: c for to in tos_man for c in jl(a.e0_s04b / f"chunks_{to}.json")}

    # 1. lectura de cortes ------------------------------------------------------------------------------------------
    plenos = [t for t in man["tos"] if t["clase"] == "reconocido_pleno"]
    assert tos_man["ri_spi"]["modo_lectura"] == "sin_raiz", "ri_spi no está en sin_raiz en conteos_b584"
    tos_estrato = {e: sorted([t["id"] for t in plenos if t["modo_lectura"] == e] + (["ri_spi"] if e == "sin_raiz"
                                                                                    else [])) for e in TAMANOS}
    ids_estrato = {e: sorted(c["id"] for to in tos_estrato[e] for c in chunks[to]) for e in TAMANOS}
    total = sum(len(v) for v in ids_estrato.values())
    estratos = {e: {"tos": len(tos_estrato[e]), "unidades": len(ids_estrato[e]), "n": TAMANOS[e],
                    "peso": len(ids_estrato[e]) / total,
                    "semilla_del_tramo_b": f"U-SEG-OFICIAL:cortes:S1-ter:{e}",
                    "sha256_ids_ordenados": sha_ids(ids_estrato[e]),
                    "tos_tanda0": [t for t in tos_estrato[e] if t in TANDA0],
                    "unidades_de_ri_spi": sum(1 for i in ids_estrato[e] if i.startswith("ri_spi::")),
                    "ids": ids_estrato[e]} for e in TAMANOS}
    estrato_de = {i: e for e in TAMANOS for i in ids_estrato[e]}
    sin_spi = {e: len([i for i in ids_estrato[e] if not i.startswith("ri_spi::")]) for e in TAMANOS}

    # ri_spi: el título partido de SB y SC
    def apartado(pool: dict, letra: str) -> dict:
        ch = sorted((c for i, c in pool.items() if i.startswith(f"ri_spi::S{letra}") or
                     re.match(rf"^ri_spi::{letra}\.", i)), key=lambda c: c["id"])
        chapeaux = [{"id": c["id"], "texto": c["texto"]} for c in ch if c["tipo"] == "mini_chunk"
                    and c.get("rol_bloque") == "chapeau_seccion"]
        primer = next((c for c in ch if c["tipo"] != "mini_chunk"), None)
        titulos = Counter(tuple(tr["texto"] for tr in c["herencia"] if tr["tipo"] in ("encabezado", "chapeau_seccion"))
                          [:2] for c in ch if c["tipo"] != "mini_chunk")
        return {"unidades": len(ch), "mini_chunks": [{"id": c["id"], "rol_bloque": c.get("rol_bloque"),
                                                      "texto": c["texto"][:200]} for c in ch
                                                     if c["tipo"] == "mini_chunk"],
                "chapeau_seccion": chapeaux,
                "herencia_de_la_primera_unidad": primer["herencia"] if primer else None,
                "dos_primeros_tramos_heredados_por_las_unidades": [{"tramos": list(k), "unidades": n}
                                                                   for k, n in titulos.items()]}
    pool_04b = {i: c for i, c in por_id_04b.items() if i.startswith("ri_spi::")}
    pool_ter = {i: c for i, c in por_id.items() if i.startswith("ri_spi::")}
    ri_spi = {"unidades_s04b": len(pool_04b), "unidades_s1ter": len(pool_ter),
              "ids_solo_en_s04b": sorted(set(pool_04b) - set(pool_ter)),
              "ids_solo_en_s1ter": sorted(set(pool_ter) - set(pool_04b)),
              "unidades_que_cambian": sorted(i for i in set(pool_04b) & set(pool_ter)
                                             if not igual(pool_04b[i], pool_ter[i])),
              "apartados": {L: {"s04b": apartado(pool_04b, L), "s1ter": apartado(pool_ter, L)} for L in ("B", "C")}}

    # límites declarados en la población de cortes
    lim_s05 = jl(a.limites_s05)
    lims: dict[str, dict] = {}
    for x in lim_s05["limites"]:
        d = lims.setdefault(x["unidad"], {"id": x["unidad"], "fuentes": [], "destinos": []})
        d["fuentes"].append(f"limites_S0-5a-bis: {x['grupo_de_fila']}")
        if x["destino"] not in d["destinos"]:
            d["destinos"].append(x["destino"])
    for grupo, ids in (("FRENO S0-4b, de corte", LIMITES_CORTE_S04B), ("FRENO S0-4b, tamaño o herencia",
                                                                        LIMITES_OTROS_S04B),
                       ("lectura de S1 (ri2_ae)", LIMITES_CONOCIDOS_S1)):
        for i in ids:
            lims.setdefault(i, {"id": i, "fuentes": [], "destinos": []})["fuentes"].append(grupo)
    for d in lims.values():
        e = estrato_de.get(d["id"])
        d["en_la_salida"] = d["id"] in por_id
        d["estrato"] = e
        d["probabilidad_de_salir"] = TAMANOS[e] / len(ids_estrato[e]) if e else None
    lims_l = sorted(lims.values(), key=lambda d: d["id"])
    en_pob = [d for d in lims_l if d["estrato"]]

    # la muestra de S1-bis en la población de S1-ter
    m1 = jl(a.s1bis_muestra)
    previas = [(u["id"], e) for e, v in m1["primer_grupo"]["estratos"].items() for u in v["muestra"]]
    previas += [(u["id"], "ri_spi") for u in m1["ri_spi"]["muestra"]]
    repite = []
    for i, e_prev in previas:
        e = estrato_de.get(i)
        repite.append({"id": i, "estrato_s1bis": e_prev, "estrato_s1ter": e, "en_la_poblacion": e is not None,
                       "unidad_igual_a_s0_4b": igual(por_id_04b.get(i), por_id.get(i)) if e else None})
    rep_pob = [r for r in repite if r["en_la_poblacion"]]
    esperadas_rep = sum(TAMANOS[r["estrato_s1ter"]] / len(ids_estrato[r["estrato_s1ter"]]) for r in rep_pob)

    # 2. 1.16 (a) ----------------------------------------------------------------------------------------------------
    det = jl(a.detector)
    cand = {c["id"]: c for c in det["candidatos"]}
    assert len(cand) == len(det["candidatos"]), "ids repetidos en el detector"
    ids35 = jl(a.s1bis_censo)["hallazgo_1_16"]["tanda1"]["ids_s1bis"]
    with open(a.s1bis_planilla_116, encoding="utf-8") as fh:
        ids_planilla = [r["id"] for r in csv.DictReader(fh, delimiter="\t")]
    assert len(ids35) == 35 and sorted(ids_planilla) == sorted(ids35), "los 35 no coinciden con la planilla"
    pob_a = sorted(set(cand) - set(ids35) - set(CASOS_DE_DISENO))
    pa = {"candidatos_del_detector": len(cand),
          "por_criterio": dict(Counter(c["criterio"] for c in cand.values())),
          "por_origen": dict(Counter(c["origen"] for c in cand.values())),
          "de_los_35_que_siguen_siendo_candidatos": sorted(set(ids35) & set(cand)),
          "de_los_3_de_diseno_que_siguen_siendo_candidatos": sorted(set(CASOS_DE_DISENO) & set(cand)),
          "poblacion": len(pob_a), "n": 30, "semilla_del_tramo_b": "U-SEG-OFICIAL:1_16:S1-ter",
          "sha256_ids_ordenados": sha_ids(pob_a),
          "tos": len({i.split("::")[0] for i in pob_a}),
          "de_la_tanda1": sum(1 for i in pob_a if i.split("::")[0] in TANDA1),
          "por_to": dict(sorted(Counter(i.split("::")[0] for i in pob_a).items())),
          "en_la_poblacion_de_cortes": dict(Counter(estrato_de.get(i) for i in pob_a)),
          "en_tos_de_la_tanda0": sorted(i for i in pob_a if i.split("::")[0] in TANDA0),
          "fuera_de_la_poblacion_de_cortes": [{"id": i, "clase": tos_man[i.split("::")[0]]["clase"],
                                               "via": tos_man[i.split("::")[0]]["via"]}
                                              for i in pob_a if i not in estrato_de],
          "ids": pob_a}

    # 3. 1.16 (b) ----------------------------------------------------------------------------------------------------
    raw = a.lista_r5a.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA_LISTA_R5A, "la lista de R5-a no da su sha256"
    lr = json.loads(raw)
    casos = [x["lista"] for x in lr["por_lista"] if x["clase_mesa"] == "caso"]
    b34 = [x for x in lr["por_lista"] if x["clase_mesa"] != "caso"]
    assert len(lr["por_lista"]) == 43 and len(casos) == 9 and len(b34) == 34
    listas_b = []
    for x in b34:
        ult, cie = por_id.get(x["lista"]), por_id.get(x["cierre"])
        ult0, cie0 = por_id_04b.get(x["lista"]), por_id_04b.get(x["cierre"])
        # un último ítem partido por tamaño no tiene chunk con el id de la lista: sus partes son <id>::parteN
        partes = sorted((i for i in por_id if i.startswith(x["lista"] + "::parte")),
                        key=lambda i: int(i.rsplit("parte", 1)[1])) if ult is None else []
        listas_b.append({"lista": x["lista"], "clase_mesa": x["clase_mesa"], "tanda1": x["lista"].split("::")[0] in
                         TANDA1, "ultimo_item": resumen(ult),
                         "ultimo_item_partido_por_tamano": [
                             {**resumen(por_id[i]), "cambio_desde_s04b": cambio(por_id_04b.get(i), por_id[i]),
                              "chars_propio_s04b": por_id_04b[i]["chars_propio"] if i in por_id_04b else None}
                             for i in partes],
                         "cierre": resumen(cie),
                         "cierre_id": x["cierre"], "cierre_existia_en_s04b": cie0 is not None,
                         "ultimo_item_cambio_desde_s04b": cambio(ult0, ult),
                         "cierre_cambio_desde_s04b": cambio(cie0, cie),
                         "chars_propio_ultimo_item_s04b_a_s1ter": [ult0["chars_propio"] if ult0 else None,
                                                                   ult["chars_propio"] if ult else None],
                         "chars_propio_cierre_s04b_a_s1ter": [cie0["chars_propio"] if cie0 else None,
                                                              cie["chars_propio"] if cie else None],
                         "estrato_de_cortes": estrato_de.get(x["lista"]) or (estrato_de.get(partes[0]) if partes
                                                                              else None)})
    s2, s2_0 = por_id.get("ri_oc::S2"), por_id_04b.get("ri_oc::S2")
    sec3 = sorted((i for i in por_id if RE_SEC3_RI_OC.match(i)), key=lambda i: int(RE_SEC3_RI_OC.match(i).group(1)))
    sec3_ord = sorted(sec3)
    her_sec3 = Counter(tuple(tr["texto"] for tr in por_id[i]["herencia"] if tr["tipo"] == "encabezado")[:1]
                       for i in sec3)
    her_sec3_04b = Counter(tuple(tr["texto"] for tr in por_id_04b[i]["herencia"] if tr["tipo"] == "encabezado")[:1]
                           for i in sec3 if i in por_id_04b)
    ri_oc = {"S2": {"s1ter": resumen(s2), "s04b": resumen(s2_0),
                    "ultimos_renglones_s04b": s2_0["texto"].split("\n")[-2:] if s2_0 else None,
                    "ultimos_renglones_s1ter": s2["texto"].split("\n")[-2:] if s2 else None,
                    "aclaraciones_en_el_texto_s04b": bool(s2_0 and "Aclaraciones" in s2_0["texto"]),
                    "aclaraciones_en_el_texto_s1ter": bool(s2 and "Aclaraciones" in s2["texto"])},
             "seccion_3": {"unidades": len(sec3), "primera": sec3[0] if sec3 else None,
                           "ultima": sec3[-1] if sec3 else None,
                           "numeros_consecutivos_1_a_51": [int(RE_SEC3_RI_OC.match(i).group(1)) for i in sec3]
                           == list(range(1, 52)),
                           "primer_tramo_heredado_s1ter": [{"tramo": list(k), "unidades": n}
                                                           for k, n in her_sec3.items()],
                           "primer_tramo_heredado_s04b": [{"tramo": list(k), "unidades": n}
                                                          for k, n in her_sec3_04b.items()],
                           "semilla_del_tramo_b": "U-SEG-OFICIAL:1_16:S1-ter:ri_oc",
                           "sha256_ids_ordenados": sha_ids(sec3_ord), "ids": sec3_ord},
             "seccion_3_titulo_en_otras_unidades": sorted(i for i, c in por_id.items() if i.startswith("ri_oc::")
                                                         and c["tipo"] == "mini_chunk"
                                                         and "Aclaraciones" in c["texto"])}
    ids_b_fijos = sorted([x["lista"] for x in b34] + ["ri_oc::S2"])
    pb = {"lista_r5a": {"sha256": SHA_LISTA_R5A, "por_lista": len(lr["por_lista"]), "casos": casos,
                        "cierres": sum(1 for x in b34 if x["clase_mesa"] == "cierre"),
                        "mixtos": [x["lista"] for x in b34 if x["clase_mesa"] != "cierre"]},
          "total": len(b34) + 2, "listas_r5a": listas_b, "ri_oc": ri_oc,
          "ids_fijos_35": ids_b_fijos, "sha256_ids_fijos_ordenados": sha_ids(ids_b_fijos),
          "id_de_cada_entrada": "el último ítem de la lista (campo `lista` de la lista de la mesa), ri_oc::S2 y la "
                                "unidad de la sección 3 que elija el tramo b"}

    # variante, para la decisión del FRENO: (a) sin las listas de (b) que siguen siendo candidatas
    pob_a_sin_b = sorted(set(pob_a) - set(ids_b_fijos))
    pa["variante_sin_las_listas_de_b"] = {"poblacion": len(pob_a_sin_b), "sha256_ids_ordenados": sha_ids(pob_a_sin_b),
                                          "salen": sorted(set(pob_a) & set(ids_b_fijos))}
    # y además sin los candidatos de TOs cuya E0 no alimenta el grafo (vía fuera o por página en el manifiesto)
    no_por_punto = sorted(i for i in pob_a_sin_b if tos_man[i.split("::")[0]]["via"] != "por_punto")
    pob_a_v2 = sorted(set(pob_a_sin_b) - set(no_por_punto))
    pa["variante_sin_b_ni_vias_fuera_o_por_pagina"] = {"poblacion": len(pob_a_v2),
                                                       "sha256_ids_ordenados": sha_ids(pob_a_v2),
                                                       "salen_ademas": no_por_punto}

    # 4. regresión ---------------------------------------------------------------------------------------------------
    reg = [{"id": i, "en_s1ter": i in por_id, "igual_a_s0_4b": igual(por_id_04b.get(i), por_id.get(i)),
            "candidato_del_detector_en_s1ter": i in cand, "es_caso_de_r5a": i in casos,
            "paginas_s1ter": por_id[i]["paginas"] if i in por_id else None} for i in sorted(ids35)]

    # 5. cruces ------------------------------------------------------------------------------------------------------
    cruces = {"a_con_b_listas_y_S2": sorted(set(pob_a) & set(ids_b_fijos)),
              "a_con_seccion_3_de_ri_oc": sorted(set(pob_a) & set(sec3)),
              "b_con_los_35": sorted(set(ids_b_fijos) & set(ids35)),
              "a_con_los_35": sorted(set(pob_a) & set(ids35)),
              "casos_de_r5a_en_los_35": sorted(set(casos) & set(ids35)),
              "muestra_de_cortes_s1bis": {
                  "unidades_leidas_en_s1bis": len(previas),
                  "en_la_poblacion_de_cortes_de_s1ter": len(rep_pob),
                  "por_estrato_s1ter": dict(Counter(r["estrato_s1ter"] for r in rep_pob)),
                  "de_ellas_con_la_unidad_igual_a_s0_4b": sum(1 for r in rep_pob if r["unidad_igual_a_s0_4b"]),
                  "esperadas_en_la_muestra_de_90": esperadas_rep,
                  "lista": repite}}

    # fuera de la lectura de S1-ter (el despacho lee solo los tres estratos): los no segmentables (salvo ri_spi) y
    # ri2_pm, con sus cinco archivos por TO contra la salida de S0-4b
    fuera = {}
    for t in man["tos"]:
        if t["clase"] == "reconocido_pleno" or t["id"] == "ri_spi":
            continue
        iguales = {f"{pre}_{t['id']}.json": (a.e0 / f"{pre}_{t['id']}.json").read_bytes()
                   == (a.e0_s04b / f"{pre}_{t['id']}.json").read_bytes()
                   for pre in ("chunks", "estructura", "indice", "pies", "tablas")}
        fuera[t["id"]] = {"clase": t["clase"], "via": t["via"], "unidades": len(chunks[t["id"]]),
                          "cinco_archivos_iguales_a_s0_4b": all(iguales.values())}

    res = {"criterio": "sin sorteo; despacho de S1-ter, tramo a, punto 6",
           "cortes": {"estratos": estratos, "unidades": total, "unidades_sin_ri_spi": sin_spi,
                      "ri_spi": ri_spi,
                      "limites_declarados": {"unidades": lims_l, "en_la_poblacion": len(en_pob),
                                             "esperadas_en_la_muestra": sum(d["probabilidad_de_salir"]
                                                                            for d in en_pob),
                                             "por_estrato": dict(Counter(d["estrato"] for d in en_pob))},
                      "candidatos_1_16_en_la_poblacion": dict(Counter(estrato_de.get(i) for i in cand)),
                      "candidatos_1_16_esperados_en_la_muestra": sum(TAMANOS[estrato_de[i]] /
                                                                     len(ids_estrato[estrato_de[i]])
                                                                     for i in cand if estrato_de.get(i))},
           "c116_a": pa, "c116_b": pb, "regresion": {"unidades": len(reg), "lista": reg}, "cruces": cruces,
           "fuera_de_la_lectura": {"tos": len(fuera), "iguales_a_s0_4b": sum(v["cinco_archivos_iguales_a_s0_4b"]
                                                                         for v in fuera.values()),
                                   "por_to": fuera}}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    vista = {"cortes": {e: {k: v for k, v in g.items() if k != "ids"} for e, g in estratos.items()},
             "cortes_total": total, "sin_ri_spi": sin_spi,
             "ri_spi": {k: (v if k != "apartados" else "…") for k, v in ri_spi.items()},
             "limites_en_la_poblacion": res["cortes"]["limites_declarados"]["en_la_poblacion"],
             "limites_esperados": res["cortes"]["limites_declarados"]["esperadas_en_la_muestra"],
             "c116_a": {k: v for k, v in pa.items() if k not in ("ids",)},
             "c116_b": {"total": pb["total"], "mixtos": pb["lista_r5a"]["mixtos"],
                        "cierres": pb["lista_r5a"]["cierres"],
                        "sin_ultimo_item": [x["lista"] for x in listas_b if not x["ultimo_item"]
                                            and not x["ultimo_item_partido_por_tamano"]],
                        "partidos": {x["lista"]: [p["id"] for p in x["ultimo_item_partido_por_tamano"]]
                                     for x in listas_b if x["ultimo_item_partido_por_tamano"]},
                        "sin_cierre": [x["lista"] for x in listas_b if not x["cierre"]],
                        "ri_oc_S2": ri_oc["S2"], "seccion_3": {k: v for k, v in ri_oc["seccion_3"].items()
                                                                if k != "ids"}},
             "regresion": {"en_s1ter": sum(r["en_s1ter"] for r in reg),
                           "iguales_a_s0_4b": sum(r["igual_a_s0_4b"] for r in reg),
                           "candidatos": sum(r["candidato_del_detector_en_s1ter"] for r in reg)},
             "cruces": {k: (v if k != "muestra_de_cortes_s1bis" else {kk: vv for kk, vv in v.items() if kk != "lista"})
                        for k, v in cruces.items()},
             "fuera_de_la_lectura": {k: v for k, v in res["fuera_de_la_lectura"].items() if k != "por_to"}}
    print(json.dumps(vista, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
