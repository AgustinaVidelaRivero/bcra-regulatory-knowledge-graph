"""Tramo 3 de S2 (U-SEG-OFICIAL): la tanda final, su cobertura y sus ids por TO, el health-check y el re-censo de la release
de E0 (límites de sub-documento y candidatos del hallazgo 1.16), sobre la E0 corregida. Solo lectura; sin texto.

Uso: python -B tanda_final_S2.py --e0 <E0 corregida> --raiz <copia del repo> --censos <dir con censo_sd_152_S2b.json,
       censo_renglones_S2b.json y detector_116_S2b.json> [--hc <resumen del health-check de la tanda final>] --out <json>

La tanda final (enmienda 8, §1, y agregados 1 y 6 del «seguí» de los tramos 2 y 3): los candidatos del §5 del protocolo que
quedan después de la tanda 1 del tramo 1 (`s2/lista_tanda1_S2.json`), sin los de fuera, sin ri2_pm, sin los 15 de las
decisiones 1 y 2 de la enmienda 8 y sin rdbcra. En cascada disjunta sobre los 152 (cada TO cuenta en el primer motivo):
1. la tanda 0; 2. la tanda 1; 3. los de fuera del §5 (`docs/protocolo_entre_tandas.md:163-166`) que no tienen razón vigente
propia: los 10 no segmentables que siguen siéndolo, manual y ri2_pm (que además va con el bloque B, nota del 15/10/2026 al pie
de las enmiendas a las adendas del laudo B5.5); 4. ri_ao, derogado, que sale de los candidatos (nota del 04/10/2026,
`docs/protocolo_entre_tandas.md:432-438`); 5. los 15 de la enmienda 8 (ri_spi y ri_con cuentan acá, por su razón vigente;
en la partición legada eran no segmentables); 6. rdbcra (agregado 1).
Por TO: modo, unidades (`unidades_por_to`), cobertura exacta y ids de chunk repetidos en la E0 corregida; límites de
sub-documento (censo de S0-4a sobre la E0 corregida), candidatos del 1.16 por el censo de renglones (el principal) y por el
detector corregido de S0-5a (al lado), y, si se pasa --hc, las señales del health-check. Frena solo la cobertura no exacta o un
id repetido en la E0 corregida (agregado 4 del «seguí» del tramo 3).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

S = "data/experiment/segmentacion_oficial_e0r2"
TANDA0 = ["ctacte", "lingob", "polcre", "pagjub", "docvig"]
NO_SEG_LEG = ["optico", "plandecuentas", "ri_chr", "ri_con", "ri_fcem", "ri_itme", "ri_pfmipyme", "ri_pscpp", "ri_pspii",
              "ri_rem", "ri_spi", "ri_tii"]
PARCIALES = ["manual", "ri2_pm"]
ENMIENDA8 = ["ri_oc", "ri_icpipsp", "ri_pnp", "ri_psprca", "gerc", "ri_spi", "dmrd", "ri2_cs", "ri_cc", "ri_ccpnp", "ri_con",
             "ri_niif", "nmaeef", "ri_saofe", "ri2_ae"]
RAZON_VIGENTE = ("ri_spi", "ri_con")
ANTES = {"subdocumento": {"tanda_2": (19, 6), "tanda_3": (37, 18), "fuente": "docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md:665-669"},
         "hallazgo_1_16": {"tanda_2": (68, 37), "tanda_3": (5, 4), "fuente": "docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md:670-672"}}
MESA = {"tos": 98, "unidades": 4951, "fuente": "docs/enmienda8_protocolo_entre_tandas_2026-10-15_calendario_hacia_B6.3.md:178"}


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("--e0", "--raiz", "--censos", "--out"):
        ap.add_argument(k, type=Path, required=True)
    ap.add_argument("--hc", type=Path, default=None)
    a = ap.parse_args()
    e0, r = a.e0, a.raiz
    man = cargar(r / S / "s0_6/b/manifiestos/manifest_salida_e0_152_S0-6b.json")
    upt = man["unidades_por_to"]
    conteos = cargar(e0 / "conteos.json")
    cob = cargar(e0 / "cobertura.json")
    lista1 = [f["to"] for f in cargar(r / S / "s2/lista_tanda1_S2.json")["filas"]]
    part = cargar(r / "data/experiment/segmentacion_84/b584_particion/particion_152.json")["por_to"]
    cat = {x["id"]: x["categoria"] for x in csv.DictReader(open(r / "data/experiment/escalado_prep/inventario_tos.csv", encoding="utf-8"))}
    tos152 = sorted(upt)
    assert len(tos152) == 152 and len(lista1) == 20 and len(set(ENMIENDA8)) == 15
    assert sorted(t for t, v in part.items() if v["clase"] == "no_segmentable_declarado") == sorted(NO_SEG_LEG)
    fuera12 = [t for t in NO_SEG_LEG + PARCIALES if t not in RAZON_VIGENTE]
    pasos = [("tanda 0", TANDA0), ("tanda 1 (tramo 1)", lista1),
             ("de fuera del §5 sin razón vigente propia (10 no segmentables, manual y ri2_pm)", fuera12),
             ("ri_ao, derogado (nota del 04/10/2026 al protocolo, :432-438)", ["ri_ao"]),
             ("los 15 de la enmienda 8, decisiones 1 y 2 (ri_spi y ri_con por su razón vigente)", ENMIENDA8),
             ("rdbcra, cobertura no exacta (agregado 1)", ["rdbcra"])]
    restantes, cascada = list(tos152), []
    for motivo, ts in pasos:
        fuera = [t for t in restantes if t in ts]
        restantes = [t for t in restantes if t not in fuera]
        cascada.append({"motivo": motivo, "excluidos": len(fuera), "unidades": sum(upt[t] for t in fuera), "quedan": len(restantes),
                        "lista": sorted(fuera)})
    final = sorted(restantes)
    # censos crudos (solo cuentas e ids)
    sd = cargar(a.censos / "censo_sd_152_S2b.json")
    cr = cargar(a.censos / "censo_renglones_S2b.json")
    de = cargar(a.censos / "detector_116_S2b.json")
    lista_sd = set(sd["lista"])
    limites = {t: v for t, v in sd["por_to"].items() if isinstance(v, list)}
    c116 = Counter(x["id"].split("::")[0] for x in cr["hallazgo_1_16"]["lista"])
    d116 = Counter(x["id"].split("::")[0] for x in de["candidatos"])
    hc = cargar(a.hc)["filas"] if a.hc else {}
    filas = {}
    for t in final:
        ch = cargar(e0 / f"chunks_{t}.json")
        rep = sum(v - 1 for v in Counter(c["id"] for c in ch).values() if v > 1)
        est = cargar(e0 / f"estructura_{t}.json")
        pags_a = {x.get("pagina") for x in est["avisos"] if x["tipo"] in ("division_a", "adoptado_a") and x.get("pagina") is not None}
        lim = limites.get(t, [])
        f = {"categoria": cat[t], "modo_lectura": conteos[t].get("modo_lectura"), "unidades": upt[t],
             "cobertura_exacta": cob[t]["cobertura_exacta"], "ids_chunk_repetidos": rep,
             "subdocumento": {"limites": len(lim), "por_forma": dict(Counter(x["forma"] for x in lim)),
                              "paginas": sorted({x["pagina"] for x in lim}), "en_la_lista_de_la_regla": t in lista_sd,
                              "en_pagina_donde_A_ya_abre": sum(1 for x in lim if x["pagina"] in pags_a)},
             "hallazgo_1_16_censo": c116.get(t, 0), "hallazgo_1_16_detector": d116.get(t, 0)}
        if hc:
            h = hc[t]
            f["healthcheck"] = {k: h[k] for k in ("veredicto_hc", "modo_lectura_hc", "unidades_hc", "unidades_iguales", "cid_lineas",
                                                  "avisos_pagina_cuerpo_sin_seccion", "sin_pagina_de_cuerpo", "unidades_grandes",
                                                  "cobertura_exacta_hc", "e0_avisos_pagina_cuerpo_sin_seccion", "e0_unidades_grandes")}
            f["healthcheck"]["unidades_grandes_ids"] = [u for u, _ in h["unidades_grandes_ids"]]
            f["healthcheck"]["e0_unidades_grandes_ids"] = [u for u, _ in h["e0_unidades_grandes_ids"]]
        filas[t] = f
    det = [t for t in final if not filas[t]["subdocumento"]["en_la_lista_de_la_regla"] and filas[t]["subdocumento"]["limites"]]
    apl = [t for t in final if filas[t]["subdocumento"]["en_la_lista_de_la_regla"] and filas[t]["subdocumento"]["limites"]]
    out = {"fuentes": {"manifiesto_S0-6b": sha(r / S / "s0_6/b/manifiestos/manifest_salida_e0_152_S0-6b.json"),
                       "lista_tanda1_S2.json": sha(r / S / "s2/lista_tanda1_S2.json"),
                       "censo_sd_152_S2b.json (claves ordenadas)": hashlib.sha256(json.dumps(sd, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
                       "censo_renglones_S2b.json": sha(a.censos / "censo_renglones_S2b.json"),
                       "detector_116_S2b.json": sha(a.censos / "detector_116_S2b.json"),
                       **({"healthcheck_resumen": sha(a.hc)} if a.hc else {})},
           "cascada_disjunta_sobre_los_152": cascada,
           "tanda_final": {"tos": len(final), "unidades": sum(upt[t] for t in final),
                           "por_categoria": {k: {"tos": sum(1 for t in final if cat[t] == k), "unidades": sum(upt[t] for t in final if cat[t] == k)}
                                             for k in ("normativa_general", "regimen_informativo")},
                           "por_modo": dict(Counter(conteos[t].get("modo_lectura") for t in final)), "lista": final},
           "mesa": MESA, "igual_a_la_mesa": len(final) == MESA["tos"] and sum(upt[t] for t in final) == MESA["unidades"],
           "frena": {"cobertura_no_exacta": [t for t in final if not filas[t]["cobertura_exacta"]],
                     "ids_repetidos": [t for t in final if filas[t]["ids_chunk_repetidos"]]},
           "subdocumento": {"detecciones": {"limites": sum(filas[t]["subdocumento"]["limites"] for t in det), "tos": len(det),
                                            "por_forma": dict(sum((Counter(filas[t]["subdocumento"]["por_forma"]) for t in det), Counter())),
                                            "en_pagina_donde_A_ya_abre": sum(filas[t]["subdocumento"]["en_pagina_donde_A_ya_abre"] for t in det),
                                            "por_to": {t: filas[t]["subdocumento"]["limites"] for t in det}},
                            "en_la_lista_de_la_regla": {"limites": sum(filas[t]["subdocumento"]["limites"] for t in apl), "tos": apl},
                            "antes": ANTES["subdocumento"]},
           "hallazgo_1_16": {"censo": {"casos": sum(filas[t]["hallazgo_1_16_censo"] for t in final),
                                       "tos": sum(1 for t in final if filas[t]["hallazgo_1_16_censo"]),
                                       "por_to": {t: filas[t]["hallazgo_1_16_censo"] for t in final if filas[t]["hallazgo_1_16_censo"]},
                                       "lista": [{"id": x["id"], "paginas": x["paginas"]} for x in cr["hallazgo_1_16"]["lista"]
                                                 if x["id"].split("::")[0] in final]},
                             "detector": {"casos": sum(filas[t]["hallazgo_1_16_detector"] for t in final),
                                          "tos": sum(1 for t in final if filas[t]["hallazgo_1_16_detector"]),
                                          "por_to": {t: filas[t]["hallazgo_1_16_detector"] for t in final if filas[t]["hallazgo_1_16_detector"]},
                                          "lista": [{"id": x["id"], "paginas": x["paginas"], "criterio": x.get("criterio"), "origen": x.get("origen")}
                                                    for x in de["candidatos"] if x["id"].split("::")[0] in final]},
                             "antes": ANTES["hallazgo_1_16"]},
           "filas": filas}
    if hc:
        out["healthcheck"] = {"tos": len(hc), "no_reproduce_correr_e0": sorted(t for t in final if not hc[t]["unidades_iguales"]),
                              "cobertura_no_exacta_hc": sorted(t for t in final if not hc[t]["cobertura_exacta_hc"]),
                              "veredictos": dict(Counter("sano" if hc[t]["veredicto_hc"] == "sano" else "+".join(hc[t]["veredicto_hc"])
                                                         for t in final))}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("tanda_final", "igual_a_la_mesa", "frena")}, ensure_ascii=False)[:1500])
    for c in cascada:
        print(" ", c["motivo"][:60], c["excluidos"], c["unidades"], c["quedan"])
    print("sd", {k: v for k, v in out["subdocumento"].items() if k != "antes"})
    print("1.16", {k: {kk: vv for kk, vv in v.items() if kk in ("casos", "tos")} for k, v in out["hallazgo_1_16"].items() if k != "antes"})
    if hc:
        print("hc", {k: (v if not isinstance(v, list) else (len(v), v[:30])) for k, v in out["healthcheck"].items()})


if __name__ == "__main__":
    main()
