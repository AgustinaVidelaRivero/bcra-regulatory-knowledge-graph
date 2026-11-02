"""U-SEG-OFICIAL, S1-bis.6: la población de la muestra de la lectura de cortes, SIN SORTEAR (USD 0, sin API).

Uso: python -B poblacion_muestra_S1bis.py --e0 <salida de la corrida> --manifiesto <json> --controles <controles_S1bis.json>
       --s1-e0 <salida de E0 de S1> --s1-muestra <s1/muestra_cortes_S1.json> --s1-marcas <tsv de la lectura de S1>
       --out <json>

No sortea, no lee y no marca: el sorteo es del tramo b, con la población que fijen las decisiones de la autora sobre
el FRENO S1-bis-a. Criterio de la población, el de la nota del mandato de `2faff14` con las precisiones de `26c6502`,
como en `s1/scripts/muestra_cortes_S1.py`:
- primer grupo: las unidades de los TOs reconocidos plenos (clase de `particion_152.json`, en el manifiesto), por
  estrato = valor literal de `modo_lectura` de `conteos_b584.json` (en el manifiesto): vigente, marcadores, sin_raiz;
  `ids` = todos los chunks de los TOs del estrato, ordenados con `sorted`; peso = unidades del estrato / unidades del
  primer grupo; tamaños 40 / 10 / 40;
- segundo grupo: las unidades por punto de ri2_pm (regla de `no_segmentables_limite/l2_regla_parciales.md`, calculada
  en `controles_S1bis.json`);
- tercer grupo: un juicio por cada no segmentable declarado salvo ri_spi;
- ri_spi: hoy no segmentable declarado; sus unidades, aparte.
Variantes según las decisiones pendientes (cada una con su cifra):
- ri_spi reconocido pleno: sus unidades entran al estrato de su `modo_lectura` de `conteos_b584.json` y desaparece el
  grupo aparte;
- los 2 juicios dudosos de S1 (ri_pspii, ri_tii) y la unidad dudosa `ri2_pm::3.5.3`: si su E0 sale igual a la de S1
  (archivos de ri_pspii y ri_tii byte a byte; el chunk de 3.5.3, mismo texto y páginas), la lectura de S1-bis
  repetiría la duda;
- la vía de ri2_pm: las mismas 25 por punto de S1, o no.
Aparte, como insumo del tramo b: los TOs de la tanda 0 en cada estrato y las unidades declaradas como límite en el
FRENO S0-4b que están en la población, con su estrato.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

TAMANOS = {"vigente": 40, "marcadores": 10, "sin_raiz": 40}
TANDA0 = ("ctacte", "lingob", "polcre", "pagjub", "docvig")
JUICIOS_DUDOSOS_S1 = ("ri_pspii", "ri_tii")
UNIDAD_DUDOSA_RI2_PM = "ri2_pm::3.5.3"
# límites declarados con su cifra en el FRENO S0-4b (s0_4/FRENO_S0-4b.md, «Límites declarados»), por unidad. Las 13
# primeras son límites de corte (nmaeef::2.9, las 10 de solo rótulo, A.1 y A.2 dentro de D1A3L1::S0 y el resto del
# título de B.2): son las que, leídas con el criterio, pueden contar como error; las otras cuatro son límites de tamaño
# o de herencia (cierre heredado, condición 12)
LIMITES_CORTE_S04B = ("nmaeef::2.9", "ri_ccna::D1A3L2::S0", "ri_oc::A2::S0", "ri_oc::SA", "nmcief::A1P2::S0",
                      "nmcief::A1P4::S0", "ri_ccna::D2A1P1::S0", "ri_ccna::D2A1P2::S0", "ri_icpipsp::A1C1::S0",
                      "ri_icpipsp::A1C2::S0", "ri_icpipsp::A1C3::S0", "ri_ccna::D1A3L1::S0", "ri_oc::B.2::intro")
LIMITES_OTROS_S04B = ("ri_cc::RIP::S0", "ri_oc::SC::cierre", "nmcief::A6::S0", "manori::1.5.1")
LIMITES_S04B = LIMITES_CORTE_S04B + LIMITES_OTROS_S04B
LIMITES_CONOCIDOS_S1 = ("ri2_ae::3.3", "ri2_ae::5.3")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def estratos(plenos: list[dict], chunks: dict, extra: dict | None = None) -> dict:
    """Estratos del primer grupo; `extra` = {estrato: [ids]} que se suman (variante de ri_spi)."""
    out, total = {}, 0
    for e in TAMANOS:
        tos = sorted(t["id"] for t in plenos if t["modo_lectura"] == e)
        ids = sorted([c["id"] for to in tos for c in chunks[to]] + list((extra or {}).get(e, [])))
        out[e] = {"tos": len(tos) + (1 if (extra or {}).get(e) else 0), "unidades": len(ids), "n": TAMANOS[e],
                  "sha256_ids_ordenados": sha_ids(ids), "tos_tanda0": [t for t in tos if t in TANDA0]}
        total += len(ids)
    for e in out:
        out[e]["peso"] = out[e]["unidades"] / total
    return {"unidades": total, "estratos": out}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("e0", "manifiesto", "controles", "s1_e0", "s1_muestra", "s1_marcas", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    man = jl(a.manifiesto)
    ctl = jl(a.controles)
    chunks = {t["id"]: jl(a.e0 / f"chunks_{t['id']}.json") for t in man["tos"]}
    por_id = {c["id"]: c for ch in chunks.values() for c in ch}
    tos_man = {t["id"]: t for t in man["tos"]}
    plenos = [t for t in man["tos"] if t["clase"] == "reconocido_pleno"]

    base = estratos(plenos, chunks)
    ids_estrato = {e: sorted(c["id"] for t in plenos if t["modo_lectura"] == e for c in chunks[t["id"]])
                   for e in TAMANOS}
    for e in TAMANOS:
        base["estratos"][e]["ids"] = ids_estrato[e]

    # ri_spi
    spi = sorted(c["id"] for c in chunks["ri_spi"])
    spi_modo = tos_man["ri_spi"]["modo_lectura"]
    con_spi = estratos(plenos, chunks, {spi_modo: spi})
    # segundo grupo
    s1m = jl(a.s1_muestra)
    pm_s1 = [u["id"] for u in s1m["segundo_grupo"]["muestra"]]
    pm = ctl["ri2_pm"]["ids_por_punto"]
    # tercer grupo
    nos = [t for t in man["tos"] if t["clase"] == "no_segmentable_declarado" and t["id"] != "ri_spi"]
    juicios = {t["id"]: {"paginas_del_pdf": t["paginas"], "via": t["via"], "unidades_e0r2": len(chunks[t["id"]]),
                         "unidades_e0r2_en_s1": len(jl(a.s1_e0 / f"chunks_{t['id']}.json"))} for t in nos}

    # los dudosos de S1: ¿salen iguales?
    marcas = {}
    with open(a.s1_marcas, encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            if r["marca"] == "dudosa" or r["grupo"] == "G3-juicio" and r["marca"] != "correcta":
                marcas[r["to"] if r["grupo"] == "G3-juicio" else r["id"]] = {
                    "fila": r["fila"], "grupo": r["grupo"], "marca": r["marca"], "clase": r["clase"],
                    "subclase": r["subclase"], "nota": r["nota"]}
    dudosos = {}
    for to in JUICIOS_DUDOSOS_S1:
        iguales = {}
        for pre in ("chunks", "estructura", "indice", "pies", "tablas"):
            n = f"{pre}_{to}.json"
            iguales[n] = (a.e0 / n).read_bytes() == (a.s1_e0 / n).read_bytes()
        dudosos[to] = {"tipo": "juicio", "archivos_iguales_a_s1": iguales, "sale_igual": all(iguales.values()),
                       "unidades": [{"id": c["id"], "paginas": c["paginas"], "chars_propio": c["chars_propio"]}
                                    for c in chunks[to]],
                       "marca_s1": marcas.get(to)}
    c_bis = por_id.get(UNIDAD_DUDOSA_RI2_PM)
    c_s1 = {c["id"]: c for c in jl(a.s1_e0 / "chunks_ri2_pm.json")}.get(UNIDAD_DUDOSA_RI2_PM)
    dudosos[UNIDAD_DUDOSA_RI2_PM] = {
        "tipo": "unidad", "en_s1bis": c_bis is not None,
        "sale_igual": bool(c_bis and c_s1 and c_bis["texto"] == c_s1["texto"] and c_bis["paginas"] == c_s1["paginas"]
                           and c_bis["herencia"] == c_s1["herencia"]),
        "paginas": c_bis["paginas"] if c_bis else None, "chars_propio": c_bis["chars_propio"] if c_bis else None,
        "marca_s1": marcas.get(UNIDAD_DUDOSA_RI2_PM)}

    # límites declarados en la población, con su estrato
    estrato_de = {i: e for e in TAMANOS for i in ids_estrato[e]}
    limites = []
    for i in LIMITES_S04B + LIMITES_CONOCIDOS_S1:
        e = estrato_de.get(i)
        limites.append({"id": i, "en_la_corrida": i in por_id, "estrato": e,
                        "grupo": ("corte" if i in LIMITES_CORTE_S04B else "tamano_o_herencia" if i in LIMITES_OTROS_S04B
                                  else "conocido_de_s1"),
                        "fuente": "FRENO S0-4b" if i in LIMITES_S04B else "lectura de S1 (salvedad de ri2_ae)",
                        "probabilidad_de_salir": (TAMANOS[e] / len(ids_estrato[e])) if e else None})

    res = {"criterio": "nota del mandato de 2faff14 con las precisiones de 26c6502; sin sorteo",
           "semillas_selladas": {"muestra": "U-SEG-OFICIAL:cortes:S1-bis",
                                 "revision_correctas": "U-SEG-OFICIAL:cortes:S1-bis:revision",
                                 "revision_1_16": "U-SEG-OFICIAL:1_16:S1-bis:revision", "commit": "a757b32"},
           "primer_grupo": {"tos": len(plenos), **base},
           "segundo_grupo": {"to": "ri2_pm", "via": tos_man["ri2_pm"]["via"],
                             "alcance_via": tos_man["ri2_pm"].get("alcance_via"),
                             "unidades_por_punto": len(pm), "cruzan_fichas": ctl["ri2_pm"]["cruzan_fichas"],
                             "unidades_ri2_pm": ctl["ri2_pm"]["unidades"],
                             "iguales_a_las_25_de_s1": pm == pm_s1, "ids": pm},
           "tercer_grupo": {"juicios": len(juicios), "por_to": juicios},
           "ri_spi": {"clase": tos_man["ri_spi"]["clase"], "via": tos_man["ri_spi"]["via"],
                      "modo_lectura_b584": spi_modo, "unidades": len(spi), "unidades_s1": len(jl(a.s1_e0 /
                                                                                              "chunks_ri_spi.json")),
                      "grupo_aparte_si_sigue_no_segmentable": {"n": 10, "sha256_ids_ordenados": sha_ids(spi)},
                      "ids": spi},
           "variante_ri_spi_reconocido_pleno": {
               "estrato": spi_modo, "primer_grupo": {"tos": len(plenos) + 1, **con_spi},
               "efecto": "las unidades de ri_spi entran al estrato y desaparece el grupo aparte de 10"},
           "dudosos_de_s1": dudosos,
           "limites_declarados_en_la_poblacion": {
               "unidades": limites,
               "en_el_primer_grupo": sum(1 for x in limites if x["estrato"]),
               "por_grupo": {g: {"unidades": sum(1 for x in limites if x["grupo"] == g),
                                 "en_el_primer_grupo": sum(1 for x in limites if x["grupo"] == g and x["estrato"]),
                                 "esperadas_en_la_muestra": sum(x["probabilidad_de_salir"] or 0 for x in limites
                                                                if x["grupo"] == g)}
                             for g in ("corte", "tamano_o_herencia", "conocido_de_s1")}},
           "lecturas_por_variante": {
               "ri_spi_no_segmentable": {"primer_grupo": 90, "ri2_pm": len(pm), "juicios": len(juicios), "ri_spi": 10,
                                         "total": 90 + len(pm) + len(juicios) + 10},
               "ri_spi_reconocido_pleno": {"primer_grupo": 90, "ri2_pm": len(pm), "juicios": len(juicios),
                                           "total": 90 + len(pm) + len(juicios)}}}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    vista = {"primer_grupo": {e: {k: v for k, v in g.items() if k != "ids"} for e, g in base["estratos"].items()},
             "unidades_primer_grupo": base["unidades"],
             "con_ri_spi": {e: {k: g[k] for k in ("unidades", "peso")} for e, g in con_spi["estratos"].items()},
             "ri2_pm": {k: v for k, v in res["segundo_grupo"].items() if k != "ids"},
             "juicios": len(juicios), "ri_spi": {k: v for k, v in res["ri_spi"].items() if k != "ids"},
             "dudosos": {k: {kk: vv for kk, vv in v.items() if kk in ("sale_igual", "paginas", "chars_propio")}
                         for k, v in dudosos.items()},
             "limites": res["limites_declarados_en_la_poblacion"]["por_grupo"]}
    print(json.dumps(vista, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
