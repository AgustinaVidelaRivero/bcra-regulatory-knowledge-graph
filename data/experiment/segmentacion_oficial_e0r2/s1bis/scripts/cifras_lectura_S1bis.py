"""U-SEG-OFICIAL, S1-bis-b: cifras de la lectura de cortes, desde las planillas marcadas (USD 0). Fijado antes de leer.

Uso: python -B cifras_lectura_S1bis.py --muestra <muestra_cortes_S1bis.json> --planilla <planilla_marcas…tsv>
       --planilla-116 <planilla_1_16…tsv> --censo <censo_renglones_S1bis.json>
       --limites-t0 <s0_4/censos/censo_4ab_sobre_S0-3.json> --e0 <s1bis/e0> --out <json>

Cifras de la nota del mandato de `2faff14` y de `acta_sorteo_S1bis.md`, §5:
- error de corte: `marca` = error y `clase` = corte; de limpieza: `clase` = limpieza o columna `limpieza` con
  `restos_encabezado` o `restos_pie`; dudosa: `marca` = dudosa;
- la cifra del piso: límite inferior de Wilson al 95 % de las unidades sin error de corte sobre las 90 del primer grupo,
  sin ponderar, con las dudosas como correctas y como error; pasa con 0,90 o más;
- por modo de lectura, como fracción; la del corpus: Σ peso × fracción, con Wilson sobre el tamaño efectivo
  1 / Σ(peso² / leídas), sin redondear (aproximación: trata la muestra ponderada como simple de ese tamaño);
- ri_spi aparte; los juicios; la limpieza por grupo; los errores de un TO de la tanda 0, aparte;
- los límites declarados que caen en la muestra (las 13 de corte, las 4 de tamaño o herencia y las 21 intros de la
  tanda 0 cuentan según el criterio; `ri2_ae::3.3` y `5.3`, además, con la cifra del piso sin contarlos como error);
- el censo del 1.16 de la tanda 1, con su cifra aparte del piso, y los candidatos del 1.16 que caen en la muestra.
Las marcas de límite, de tanda 0 y de candidato se calculan acá, después de la lectura, desde sus listas de origen.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

Z = 1.959963984540054
TANDA0 = ("ctacte", "lingob", "polcre", "pagjub", "docvig")
PISO = 0.90
LIMITES_CORTE = ("nmaeef::2.9", "ri_ccna::D1A3L2::S0", "ri_oc::A2::S0", "ri_oc::SA", "nmcief::A1P2::S0", "nmcief::A1P4::S0",
                 "ri_ccna::D2A1P1::S0", "ri_ccna::D2A1P2::S0", "ri_icpipsp::A1C1::S0", "ri_icpipsp::A1C2::S0",
                 "ri_icpipsp::A1C3::S0", "ri_ccna::D1A3L1::S0", "ri_oc::B.2::intro")
LIMITES_TAMANO_O_HERENCIA = ("ri_cc::RIP::S0", "ri_oc::SC::cierre", "nmcief::A6::S0", "manori::1.5.1")
LIMITES_RI2_AE = ("ri2_ae::3.3", "ri2_ae::5.3")
SUBCLASES_CORTE = {"empieza_fuera", "termina_fuera", "falta_texto_propio", "trae_texto_de_otro_punto", "numero_equivocado"}
SUBCLASES_LIMPIEZA = {"restos_encabezado", "restos_pie"}


def wilson(k: int, n: float) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    c = 1 + Z * Z / n
    m = p + Z * Z / (2 * n)
    r = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return [(m - r) / c, (m + r) / c]


def wilson_p(p: float, n: float) -> list[float]:
    c = 1 + Z * Z / n
    m = p + Z * Z / (2 * n)
    r = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return [(m - r) / c, (m + r) / c]


def leer(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def validar(filas: list[dict], juicio: bool = False) -> list[str]:
    err = []
    for f in filas:
        ok = {"correcta", "error", "dudosa"} | ({"limite_declarado"} if juicio else set())
        if f["marca"] not in ok:
            err.append(f"fila {f['fila']}: marca «{f['marca']}»")
        if f["marca"] == "error" and not juicio:
            if f["clase"] not in ("corte", "limpieza"):
                err.append(f"fila {f['fila']}: error sin clase")
            subs = {s for s in (f["subclase"], f["subclase_adicional"]) if s}
            validas = SUBCLASES_CORTE if f["clase"] == "corte" else SUBCLASES_LIMPIEZA
            if not subs or not subs <= (SUBCLASES_CORTE | SUBCLASES_LIMPIEZA) or f["subclase"] not in validas:
                err.append(f"fila {f['fila']}: subclase «{f['subclase']}»")
        if f["limpieza"] and f["limpieza"] not in SUBCLASES_LIMPIEZA:
            err.append(f"fila {f['fila']}: limpieza «{f['limpieza']}»")
    return err


def es_corte(f: dict) -> bool:
    return f["marca"] == "error" and f["clase"] == "corte"


def es_limpieza(f: dict) -> bool:
    return (f["marca"] == "error" and f["clase"] == "limpieza") or bool(f["limpieza"])


def piso(filas: list[dict], excluir_como_error: set[str] = frozenset()) -> dict:
    n = len(filas)
    out = {}
    for nombre, dudosa_error in (("dudosas_como_correctas", False), ("dudosas_como_error", True)):
        e = sum(1 for f in filas if f["id"] not in excluir_como_error
                and (es_corte(f) or (dudosa_error and f["marca"] == "dudosa")))
        w = wilson(n - e, n)
        out[nombre] = {"leidas": n, "errores_de_corte": e, "sin_error_de_corte": n - e, "wilson95": w,
                       "llega_al_piso": bool(w and w[0] >= PISO)}
    return out


def calcular(muestra: dict, planilla: list[dict], planilla116: list[dict], ids_1_16: set[str],
             t0_21: set[str]) -> dict:
    estr = muestra["primer_grupo"]["estratos"]
    g1 = {u["id"]: e for e, g in estr.items() for u in g["muestra"]}
    spi = {u["id"] for u in muestra["ri_spi"]["muestra"]}
    filas_g1 = [f for f in planilla if f["id"] in g1 and f["grupo"].startswith("G1-")]
    filas_spi = [f for f in planilla if f["id"] in spi and f["grupo"] == "ri_spi"]
    filas_j = [f for f in planilla if f["grupo"] == "G3-juicio"]
    assert len(filas_g1) == sum(g["leidas"] for g in estr.values()), "faltan filas del primer grupo"
    assert len(filas_spi) == len(spi) and len(filas_j) == muestra["tercer_grupo"]["juicios"]
    assert len(planilla116) == muestra["censo_1_16_tanda1"]["candidatos"]
    errores = (validar(filas_g1) + validar(filas_spi) + validar(filas_j, juicio=True) + validar(planilla116))
    if errores:
        return {"planillas_validas": False, "errores": errores}

    por_modo, est, sum_w2n = {}, 0.0, 0.0
    for e, g in estr.items():
        fs = [f for f in filas_g1 if g1[f["id"]] == e]
        ok = sum(1 for f in fs if not es_corte(f))
        por_modo[e] = {"sin_error": ok, "leidas": len(fs), "fraccion": ok / len(fs), "peso": g["peso"]}
        est += g["peso"] * ok / len(fs)
        sum_w2n += g["peso"] ** 2 / len(fs)
    n_eff = 1 / sum_w2n

    def limites(lista, nombre):
        return [{"id": f["id"], "marca": f["marca"], "clase": f["clase"], "subclase": f["subclase"], "grupo": nombre}
                for f in filas_g1 + filas_spi if f["id"] in lista]
    lim = (limites(LIMITES_CORTE, "corte_S0-4b") + limites(LIMITES_TAMANO_O_HERENCIA, "tamano_o_herencia_S0-4b")
           + limites(LIMITES_RI2_AE, "ri2_ae_conocido") + limites(t0_21, "tanda0_fuera_de_4a_y_4b"))
    ri2_ae_en_muestra = {x["id"] for x in lim if x["grupo"] == "ri2_ae_conocido"}
    res = {"planillas_validas": True,
           "cifra_del_piso": piso(filas_g1),
           "cifra_del_piso_sin_contar_ri2_ae_como_error": piso(filas_g1, ri2_ae_en_muestra) if ri2_ae_en_muestra else None,
           "por_modo": por_modo,
           "cifra_del_corpus": {"estimacion": est, "n_efectivo": n_eff, "wilson95": wilson_p(est, n_eff),
                                "nota": "aproximación: trata la muestra ponderada como una simple de tamaño n_efectivo"},
           "errores_de_corte_por_subclase": dict(Counter(s for f in filas_g1 if es_corte(f)
                                                         for s in (f["subclase"], f["subclase_adicional"]) if s)),
           "errores_de_corte_lista": [{k: f[k] for k in ("fila", "id", "subclase", "subclase_adicional", "nota")}
                                      for f in filas_g1 if es_corte(f)],
           "dudosas_primer_grupo": [f["id"] for f in filas_g1 if f["marca"] == "dudosa"],
           "limpieza_por_grupo": {"primer_grupo": sum(es_limpieza(f) for f in filas_g1),
                                  "ri_spi": sum(es_limpieza(f) for f in filas_spi),
                                  "censo_1_16": sum(es_limpieza(f) for f in planilla116)},
           "ri_spi": {"sin_error_de_corte": sum(not es_corte(f) for f in filas_spi), "leidas": len(filas_spi),
                      "dudosas": sum(f["marca"] == "dudosa" for f in filas_spi), "fuera_del_piso": True},
           "juicios": dict(Counter(f["marca"] for f in filas_j)),
           "tanda0_con_error_de_corte": [f["id"] for f in filas_g1 if f["to"] in TANDA0 and es_corte(f)],
           "limites_declarados_en_la_muestra": lim,
           "censo_1_16_tanda1": {"candidatos": len(planilla116),
                                 "con_error_de_corte": sum(es_corte(f) for f in planilla116),
                                 "dudosos": sum(f["marca"] == "dudosa" for f in planilla116),
                                 "correctos": sum(f["marca"] == "correcta" for f in planilla116),
                                 "wilson95_de_la_fraccion_con_error": wilson(sum(es_corte(f) for f in planilla116),
                                                                            len(planilla116)),
                                 "nota": "cifra aparte del piso"},
           "candidatos_1_16_en_la_muestra": [{"id": f["id"], "marca": f["marca"], "grupo": f["grupo"]}
                                             for f in filas_g1 + filas_spi if f["id"] in ids_1_16]}
    return res


def t0_fuera_de_4ab(limites_t0: dict) -> set[str]:
    casos = limites_t0["tanda0_limite_declarado"]["casos"]
    return {f"{c['to']}::{c['unidad']}::intro" for c in casos if c["to"] in TANDA0}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("muestra", "planilla", "planilla_116", "censo", "limites_t0", "e0", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    m = json.loads(a.muestra.read_text(encoding="utf-8"))
    t0 = t0_fuera_de_4ab(json.loads(a.limites_t0.read_text(encoding="utf-8")))
    existen = {c["id"] for to in TANDA0 for c in json.loads((a.e0 / f"chunks_{to}.json").read_text(encoding="utf-8"))}
    assert len(t0) == 21 and t0 <= existen, "las 21 intros de la tanda 0 no están en la salida"
    ids116 = {c["id"] for c in json.loads(a.censo.read_text(encoding="utf-8"))["hallazgo_1_16"]["lista"]}
    res = calcular(m, leer(a.planilla), leer(a.planilla_116), ids116, t0)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
