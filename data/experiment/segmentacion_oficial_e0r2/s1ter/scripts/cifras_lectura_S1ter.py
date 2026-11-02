"""U-SEG-OFICIAL, S1-ter-b: cifras de la lectura de S1-ter, desde las planillas marcadas (USD 0). Fijado antes de leer.

Uso: python -B cifras_lectura_S1ter.py --orden <tramo_b/orden_lectura_S1ter.json> --sha-orden <sha256 sellado>
       --poblaciones-finales <tramo_b/poblaciones_finales_S1ter.json> --poblaciones <poblaciones_S1ter.json>
       --planilla-1 <planilla de la etapa 1> --planilla-2 <planilla de la etapa 2> --out <json>

Las planillas traen solo el id opaco de cada ficha; la población, el estrato y la unidad salen del orden sellado.
Criterio, el de la nota del mandato de `2faff14` (como `s1bis/scripts/cifras_lectura_S1bis.py`):
- error de corte: `marca` = error y `clase` = corte; de limpieza: `clase` = limpieza o columna `limpieza` con
  `restos_encabezado` o `restos_pie`; dudosa: `marca` = dudosa.
Etapa 1 (cortes):
- la cifra del piso: límite inferior de Wilson al 95 % de las unidades sin error de corte sobre las 90, sin ponderar,
  con las dudosas como correctas y como error; pasa con 0,90 o más (a lo sumo 3 errores de corte);
- por estrato, como fracción; la del corpus: Σ peso × fracción, con los pesos de las poblaciones finales, y Wilson sobre
  el tamaño efectivo 1 / Σ(peso² / leídas);
- la limpieza, los errores en TOs de la tanda 0 (aparte) y los límites declarados que caen en la muestra, con su marca:
  una unidad con límite declarado cuenta como error si lo es (decisión del 09/10/2026 sobre ri_secoexpo).
Etapa 2 (1.16):
- (a): los errores de corte sobre 30, con Wilson de la fracción con error;
- (b): por entrada; una lista con error de corte es candidata a revertirse por lista antes de S2, después de la
  adjudicación de la autora; en los dos mixtos, la autora atribuye el error al resto declarado (cuenta como error y no
  revierte) o a lo que movió R5-a (revierte) (decisión 4 sobre el FRENO S1-ter-a); `ri_oc::S2` y la unidad de la sección
  3 de ri_oc: un error, o una nota de la lectora sobre la herencia de esa unidad, es falla de la corrección (la nota la
  lee la autora);
- la regresión, sin cifra: solo la lista de sus marcas;
- las unidades que se califican en las dos etapas, con sus dos marcas.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

Z = 1.959963984540054
PISO = 0.90
TANDA0 = ("ctacte", "lingob", "polcre", "pagjub", "docvig")
MIXTOS = ("ri_spi::C.1.3", "ri2_ae::14.3")
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


def validar(filas: list[dict]) -> list[str]:
    err = []
    for f in filas:
        if f["marca"] not in ("correcta", "error", "dudosa"):
            err.append(f"{f['ficha']}: marca «{f['marca']}»")
        if f["marca"] == "error":
            if f["clase"] not in ("corte", "limpieza"):
                err.append(f"{f['ficha']}: error sin clase")
            subs = {s for s in (f["subclase"], f["subclase_adicional"]) if s}
            validas = SUBCLASES_CORTE if f["clase"] == "corte" else SUBCLASES_LIMPIEZA
            if not subs or not subs <= (SUBCLASES_CORTE | SUBCLASES_LIMPIEZA) or f["subclase"] not in validas:
                err.append(f"{f['ficha']}: subclase «{f['subclase']}»")
        if f["limpieza"] and f["limpieza"] not in SUBCLASES_LIMPIEZA:
            err.append(f"{f['ficha']}: limpieza «{f['limpieza']}»")
    return err


def es_corte(f: dict) -> bool:
    return f["marca"] == "error" and f["clase"] == "corte"


def es_limpieza(f: dict) -> bool:
    return (f["marca"] == "error" and f["clase"] == "limpieza") or bool(f["limpieza"])


def marca(f: dict) -> dict:
    return {k: f[k] for k in ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")}


def piso(filas: list[dict]) -> dict:
    n = len(filas)
    out = {}
    for nombre, dudosa_error in (("dudosas_como_correctas", False), ("dudosas_como_error", True)):
        e = sum(1 for f in filas if es_corte(f) or (dudosa_error and f["marca"] == "dudosa"))
        w = wilson(n - e, n)
        out[nombre] = {"leidas": n, "errores_de_corte": e, "sin_error_de_corte": n - e, "wilson95": w,
                       "llega_al_piso": bool(w and w[0] >= PISO)}
    return out


def calcular(orden: dict, finales: dict, limites: list[dict], p1: list[dict], p2: list[dict]) -> dict:
    f1 = {x["id_opaco"]: x for x in orden["etapa_1"]["fichas"]}
    f2 = {x["id_opaco"]: x for x in orden["etapa_2"]["fichas"]}
    assert sorted(f["ficha"] for f in p1) == sorted(f1) and sorted(f["ficha"] for f in p2) == sorted(f2), \
        "las planillas no traen las fichas del orden sellado"
    errores = validar(p1) + validar(p2)
    if errores:
        return {"planillas_validas": False, "errores": errores}
    # etapa 1
    por_estrato, est, sum_w2n = {}, 0.0, 0.0
    for e, g in finales["cortes"].items():
        fs = [f for f in p1 if f1[f["ficha"]]["estrato"] == e]
        ok = sum(1 for f in fs if not es_corte(f))
        por_estrato[e] = {"sin_error": ok, "leidas": len(fs), "fraccion": ok / len(fs), "peso": g["peso"]}
        est += g["peso"] * ok / len(fs)
        sum_w2n += g["peso"] ** 2 / len(fs)
    n_eff = 1 / sum_w2n
    lim = {d["id"]: d for d in limites}
    uid1 = {f["ficha"]: f1[f["ficha"]]["id"] for f in p1}
    # etapa 2
    a = [f for f in p2 if f2[f["ficha"]]["poblacion"] == "c116_a"]
    b = [f for f in p2 if f2[f["ficha"]]["poblacion"].startswith("c116_b")]
    reg = [f for f in p2 if f2[f["ficha"]]["poblacion"] == "regresion"]
    assert len(a) == 30 and len(b) == 36 and len(reg) == len(p2) - 66

    def destino_b(f: dict) -> str | None:
        uid = f2[f["ficha"]]["id"]
        pob = f2[f["ficha"]]["poblacion"]
        if pob == "c116_b:seccion_3_ri_oc" or uid == "ri_oc::S2":
            if es_corte(f):
                return "falla de la corrección de la sección 3 de ri_oc: se revierte por lista antes de S2"
            if pob == "c116_b:seccion_3_ri_oc" and f["nota"].strip():
                return "nota de la lectora: si es sobre la herencia, falla de la corrección (la lee la autora)"
            return None
        if not es_corte(f):
            return None
        if uid in MIXTOS:
            return "mixto: la autora atribuye el error al resto declarado (cuenta y no revierte) o a lo que movió R5-a (revierte)"
        return "lista con error de corte: se revierte por lista antes de S2, después de la adjudicación"

    cal1 = {uid1[f["ficha"]]: f for f in p1}
    dos = []
    for f in p2:
        for u in f2[f["ficha"]]["unidades_calificadas"]:
            if u in cal1:
                dos.append({"unidad": u, "etapa_1": marca(cal1[u]), "etapa_2": marca(f)})
    return {"planillas_validas": True,
            "etapa_1": {"cifra_del_piso": piso(p1), "por_estrato": por_estrato,
                        "cifra_del_corpus": {"estimacion": est, "n_efectivo": n_eff, "wilson95": wilson_p(est, n_eff),
                                             "nota": "aproximación: trata la muestra ponderada como simple de tamaño n_efectivo"},
                        "errores_de_corte": [marca(f) | {"unidad": uid1[f["ficha"]], "estrato": f1[f["ficha"]]["estrato"]}
                                             for f in p1 if es_corte(f)],
                        "errores_de_corte_por_subclase": dict(Counter(s for f in p1 if es_corte(f)
                                                                      for s in (f["subclase"], f["subclase_adicional"]) if s)),
                        "dudosas": [f["ficha"] for f in p1 if f["marca"] == "dudosa"],
                        "limpieza": sum(es_limpieza(f) for f in p1),
                        "tanda0_con_error_de_corte": [uid1[f["ficha"]] for f in p1
                                                      if uid1[f["ficha"]].split("::")[0] in TANDA0 and es_corte(f)],
                        "limites_declarados_en_la_muestra": [marca(f) | {"unidad": uid1[f["ficha"]],
                                                                         "fuentes": lim[uid1[f["ficha"]]]["fuentes"]}
                                                             for f in p1 if uid1[f["ficha"]] in lim]},
            "etapa_2": {"c116_a": {"leidas": len(a), "con_error_de_corte": sum(es_corte(f) for f in a),
                                   "dudosas": sum(f["marca"] == "dudosa" for f in a),
                                   "wilson95_de_la_fraccion_con_error": wilson(sum(es_corte(f) for f in a), len(a))},
                        "c116_b": {"leidas": len(b), "con_error_de_corte": sum(es_corte(f) for f in b),
                                   "dudosas": sum(f["marca"] == "dudosa" for f in b),
                                   "entradas_con_destino": [marca(f) | {"entrada": f2[f["ficha"]]["id"],
                                                                        "destino": destino_b(f)}
                                                            for f in b if destino_b(f)]},
                        "regresion_sin_cifra": [marca(f) | {"unidad": f2[f["ficha"]]["id"]} for f in reg],
                        "limpieza": sum(es_limpieza(f) for f in p2)},
            "unidades_en_las_dos_etapas": dos}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("orden", "sha_orden", "poblaciones_finales", "poblaciones", "planilla_1", "planilla_2", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    raw = Path(a.orden).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.sha_orden, "el orden no da su sha256 sellado"
    orden = json.loads(raw)
    finales = json.loads(Path(a.poblaciones_finales).read_text(encoding="utf-8"))
    limites = json.loads(Path(a.poblaciones).read_text(encoding="utf-8"))["cortes"]["limites_declarados"]["unidades"]
    res = calcular(orden, finales, limites, leer(Path(a.planilla_1)), leer(Path(a.planilla_2)))
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"planillas_validas": res["planillas_validas"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
