"""U-SEG-OFICIAL, S1-ter-b.2: el sorteo y el orden de lectura de S1-ter, desde las poblaciones finales selladas (USD 0).

Uso: python -B sorteo_S1ter.py --poblaciones-finales <tramo_b/poblaciones_finales_S1ter.json> --sha <sha256 sellado>
       --muestra <salida: muestra> --orden <salida: orden de lectura>

Semillas (cada una con su ancla; `docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md` = M, el de S0-5a = M5a):
- cortes, por estrato, `random.Random(cadena).sample(sorted(ids), n)` con las tres cadenas exactas
  `U-SEG-OFICIAL:cortes:S1-ter:vigente` (40), `…:marcadores` (10) y `…:sin_raiz` (40): cadena base M:845 (`1548843`),
  reparto por estrato M:295 y forma `random.Random(f"{semilla}:{estrato}")` M:300 (`2faff14`); punto 9 de las decisiones
  de la autora sobre el FRENO S1-ter-a;
- el orden de lectura de las 90 de cortes: `random.Random("U-SEG-OFICIAL:cortes:S1-ter:orden").sample(sorted(ids_90), 90)`
  (punto 9 de esas decisiones);
- 1.16 (a): `random.Random("U-SEG-OFICIAL:1_16:S1-ter").sample(sorted(ids), 30)`: semilla M:847 (`1548843`), que no cambia
  M:912 (`bbcfb45`) y M5a:208 y :394; la forma es la de las demás muestras (M:300);
- la unidad de la sección 3 de ri_oc: `random.Random("U-SEG-OFICIAL:1_16:S1-ter:ri_oc").choice(sorted(ids))`, M5a:473
  (`06110c5`);
- el orden de las 66 del 1.16: `random.Random("U-SEG-OFICIAL:1_16:S1-ter:R5-a").sample(sorted(ids_66), 66)`, M5a:477
  (`06110c5`); semilla sellada en M5a:399 (`32c71ca`);
- los 35 de regresión van después, en un bloque aparte, en el orden de sus ids (`sorted`), sin semilla.
El id opaco de cada ficha se asigna en el orden de lectura de su etapa (`E1-001`… y `E2-001`…) y no dice nada de la
población, el estrato ni la regla. El archivo del orden es la lista sellada: no va a la carpeta de la lectora.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import datetime
from pathlib import Path

S_CORTES = "U-SEG-OFICIAL:cortes:S1-ter"
S_ORDEN_CORTES = "U-SEG-OFICIAL:cortes:S1-ter:orden"
S_A = "U-SEG-OFICIAL:1_16:S1-ter"
S_RI_OC = "U-SEG-OFICIAL:1_16:S1-ter:ri_oc"
S_ORDEN_116 = "U-SEG-OFICIAL:1_16:S1-ter:R5-a"


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("poblaciones_finales", "sha", "muestra", "orden"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    raw = Path(a.poblaciones_finales).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.sha, "las poblaciones finales no dan su sha256 sellado"
    p = json.loads(raw)
    for nombre, g in list(p["cortes"].items()) + [("c116_a", p["c116_a"])]:
        assert sha_ids(g["ids"]) == g["sha256_ids_ordenados"] and g["ids"] == sorted(g["ids"]), nombre

    # cortes
    cortes = {}
    for e, g in p["cortes"].items():
        cadena = f"{S_CORTES}:{e}"
        assert cadena == g["semilla"]
        cortes[e] = {"semilla": cadena, "n": g["n"], "poblacion": g["unidades"],
                     "sha256_poblacion": g["sha256_ids_ordenados"],
                     "muestra": random.Random(cadena).sample(sorted(g["ids"]), g["n"])}
    ids_90 = [i for g in cortes.values() for i in g["muestra"]]
    assert len(ids_90) == 90 == len(set(ids_90))
    orden_90 = random.Random(S_ORDEN_CORTES).sample(sorted(ids_90), 90)
    estrato_de = {i: e for e, g in cortes.items() for i in g["muestra"]}
    # 1.16
    a30 = random.Random(S_A).sample(sorted(p["c116_a"]["ids"]), 30)
    sec3 = p["c116_b"]["seccion_3_ri_oc"]
    ri_oc_sec3 = random.Random(S_RI_OC).choice(sorted(sec3["ids"]))
    fijos = p["c116_b"]["fijos"]["ids"]
    ids_66 = a30 + fijos + [ri_oc_sec3]
    if len(set(ids_66)) != 66 or len(ids_66) != 66:
        raise SystemExit(f"FRENO: las 66 del 1.16 no son 66 ids distintos ({len(set(ids_66))})")
    orden_66 = random.Random(S_ORDEN_116).sample(sorted(ids_66), 66)
    reg = sorted(p["regresion"]["ids"])
    assert not set(reg) & set(ids_66)

    pob_116 = {i: "c116_a" for i in a30} | {i: "c116_b" for i in fijos} | {ri_oc_sec3: "c116_b:seccion_3_ri_oc"}
    listas = p["c116_b"]["listas"]

    def unidades_calificadas(i: str) -> list[str]:
        if i in listas:
            return listas[i]["unidades_del_ultimo_item"] + [listas[i]["cierre"]]
        return [i]

    etapa1 = [{"id_opaco": f"E1-{k:03d}", "id": i, "poblacion": "cortes", "estrato": estrato_de[i]}
              for k, i in enumerate(orden_90, 1)]
    etapa2 = [{"id_opaco": f"E2-{k:03d}", "id": i, "poblacion": pob_116[i],
               "unidades_calificadas": unidades_calificadas(i)} for k, i in enumerate(orden_66, 1)]
    etapa2 += [{"id_opaco": f"E2-{k:03d}", "id": i, "poblacion": "regresion", "unidades_calificadas": [i]}
               for k, i in enumerate(reg, len(orden_66) + 1)]
    cal2 = {u for x in etapa2 for u in x["unidades_calificadas"]}
    en_las_dos = sorted(set(orden_90) & cal2)
    hora = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    muestra = {"sellado": hora, "python": sys.version.split()[0], "poblaciones_finales_sha256": a.sha,
               "cortes": cortes, "cortes_ids_90_sha256_ordenados": sha_ids(sorted(ids_90)),
               "c116_a": {"semilla": S_A, "n": 30, "poblacion": p["c116_a"]["unidades"],
                          "sha256_poblacion": p["c116_a"]["sha256_ids_ordenados"], "muestra": a30},
               "c116_b": {"fijos": fijos, "seccion_3_ri_oc": {"semilla": S_RI_OC, "poblacion": sec3["unidades"],
                                                              "sha256_poblacion": sec3["sha256_ids_ordenados"],
                                                              "elegida": ri_oc_sec3}},
               "ids_66_sha256_ordenados": sha_ids(sorted(ids_66)), "ids_66_distintos": len(set(ids_66)),
               "regresion": {"unidades": len(reg), "sha256_ordenados": sha_ids(reg), "ids": reg}}
    orden = {"sellado": hora, "python": sys.version.split()[0],
             "nota": "lista sellada: id opaco de cada ficha y su unidad, población y estrato; NO va a la carpeta de la lectora",
             "etapa_1": {"semilla_del_orden": S_ORDEN_CORTES, "fichas": etapa1},
             "etapa_2": {"semilla_del_orden_de_las_66": S_ORDEN_116,
                         "bloque_de_regresion": f"E2-{len(orden_66) + 1:03d} a E2-{len(etapa2):03d}, en el orden de sus ids",
                         "fichas": etapa2},
             "unidades_calificadas_en_las_dos_etapas": en_las_dos}
    Path(a.muestra).write_text(json.dumps(muestra, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    Path(a.orden).write_text(json.dumps(orden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"sellado": hora, "python": muestra["python"], "etapa_1": len(etapa1), "etapa_2": len(etapa2),
                      "ids_66_distintos": len(set(ids_66)), "en_las_dos_etapas": len(en_las_dos)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
