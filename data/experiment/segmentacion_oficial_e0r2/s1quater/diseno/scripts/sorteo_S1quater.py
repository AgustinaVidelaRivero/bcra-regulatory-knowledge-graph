"""U-SEG-OFICIAL, S1-quater: el sorteo y el orden de lectura, desde las poblaciones y la lista de regresión selladas (mesa,
11/10/2026; USD 0, sin API). Fijado y sellado antes de que exista la E0 corregida (`../diseno_S1quater.md`, §4). Se corre sobre la
E0 corregida, nunca antes.

Uso: python3 -B sorteo_S1quater.py --poblaciones <poblaciones_S1quater.json> --sha-poblaciones <sha256 sellado>
       --regresion <regresion_S1quater.json> --sha-regresion <sha256 sellado> --muestra <json nuevo> --orden <json nuevo>

- Cada estrato: `random.Random(f"U-SEG-OFICIAL:cortes:S1-quater:{estrato}").sample(sorted(ids), n)`, con n = 40 / 10 / 40, como S1-ter
  (`s1ter/scripts/sorteo_S1ter.py`); la cadena base está sellada en 521e220a.
- El orden de lectura de las 90: `random.Random("U-SEG-OFICIAL:cortes:S1-quater:orden").sample(sorted(ids_90), 90)`, sin agrupar por
  estrato, como S1-ter; la semilla la sella este diseño.
- Etapa 2, la regresión: las unidades de la lista de regresión, en el orden de sus ids, sin semilla, como el bloque de regresión de
  S1-ter. No entra en la cifra.
- El id opaco sigue el orden de lectura de cada etapa (`E1-001`… y `E2-001`…) y no dice nada del estrato ni de la población. El orden
  es la lista sellada: no va a la carpeta de la lectora.
- `U-SEG-OFICIAL:cortes:S1-quater:revision` (521e220a) queda registrada; si la adjudicación es la de S1-ter, no se usa.
La salida estándar no trae cifras.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_S1quater as Q  # noqa: E402


def sortear(pob: dict) -> tuple[dict, list[str], dict]:
    cortes = {}
    for e, n in Q.ESTRATOS.items():
        g = pob["cortes"][e]
        if g["semilla"] != f"{Q.SEMILLA}:{e}" or g["n"] != n or g["ids"] != sorted(g["ids"]) \
                or Q.sha_ids(g["ids"]) != g["sha256_ids_ordenados"]:
            raise SystemExit(f"FRENO: la población del estrato {e} no es la sellada")
        cortes[e] = {"semilla": g["semilla"], "n": n, "poblacion": g["unidades"], "sha256_poblacion": g["sha256_ids_ordenados"],
                     "muestra": random.Random(g["semilla"]).sample(sorted(g["ids"]), n)}
    ids_90 = [i for g in cortes.values() for i in g["muestra"]]
    if len(ids_90) != sum(Q.ESTRATOS.values()) or len(set(ids_90)) != len(ids_90):
        raise SystemExit("FRENO: la muestra no da 90 unidades distintas")
    orden_90 = random.Random(Q.SEMILLA_ORDEN).sample(sorted(ids_90), len(ids_90))
    estrato_de = {i: e for e, g in cortes.items() for i in g["muestra"]}
    return cortes, orden_90, estrato_de


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("poblaciones", "sha_poblaciones", "regresion", "sha_regresion", "muestra", "orden"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    if Path(a.muestra).exists() or Path(a.orden).exists():
        raise SystemExit("FRENO: la salida ya existe")
    pob = json.loads(Q.leer_sellado(Path(a.poblaciones), a.sha_poblaciones, "las poblaciones"))
    reg = json.loads(Q.leer_sellado(Path(a.regresion), a.sha_regresion, "la lista de regresión"))
    if reg["ids"] != sorted(reg["ids"]) or Q.sha_ids(reg["ids"]) != reg["sha256_ids_ordenados"]:
        raise SystemExit("FRENO: la lista de regresión no es la sellada")
    cortes, orden_90, estrato_de = sortear(pob)
    if set(orden_90) & set(reg["ids"]):
        raise SystemExit("FRENO: una unidad de la regresión salió en la muestra")
    hora = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    etapa1 = [{"id_opaco": f"E1-{k:03d}", "id": i, "poblacion": "cortes", "estrato": estrato_de[i]}
              for k, i in enumerate(orden_90, 1)]
    etapa2 = [{"id_opaco": f"E2-{k:03d}", "id": i, "poblacion": "regresion", "unidades_calificadas": [i]}
              for k, i in enumerate(reg["ids"], 1)]
    muestra = {"sellado": hora, "python": sys.version.split()[0], "poblaciones_sha256": a.sha_poblaciones,
               "regresion_sha256": a.sha_regresion, "cortes": cortes,
               "cortes_ids_90_sha256_ordenados": Q.sha_ids(sorted(orden_90)),
               "semilla_revision": Q.SEMILLA_REVISION}
    orden = {"sellado": hora, "python": muestra["python"],
             "nota": "lista sellada: id opaco de cada ficha y su unidad, población y estrato; NO va a la carpeta de la lectora",
             "etapa_1": {"semilla_del_orden": Q.SEMILLA_ORDEN, "fichas": etapa1},
             "etapa_2": {"semilla_del_orden": None, "bloque_de_regresion": "toda la etapa, en el orden de sus ids",
                         "fichas": etapa2}}
    Path(a.muestra).write_text(json.dumps(muestra, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    Path(a.orden).write_text(json.dumps(orden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"muestra y orden escritos; sha256 {Q.sha(Path(a.muestra))} y {Q.sha(Path(a.orden))}")


if __name__ == "__main__":
    main()
