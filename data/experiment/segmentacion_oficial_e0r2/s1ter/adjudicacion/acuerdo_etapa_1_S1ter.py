"""U-SEG-OFICIAL, S1-ter: acuerdo de la etapa 1 entre la lectora y la pasada 1 de la autora (mesa, 10/10/2026; USD 0). Fijado antes
de que la autora abra la pasada 1. No toca `preparar_pasada_1_S1ter_v2.py` ni `pasada_2_S1ter_v2.py`.

Decisión de la autora del 10/10/2026 (hoja de ruta de la mesa, §58), tomada sin haber abierto nada de la pasada 1 ni de la lectura:
el acuerdo de la etapa 1 se informa sobre las 90 fichas y, además, sin las 19 primeras del orden de la lectura de la etapa 1
(`E1-001` a `E1-019`). El motivo es el incidente declarado de las imágenes (`s1ter/lectura/incidentes_lectura_S1ter.md`). Ninguna de
las dos cifras decide nada. Se corre después de la adjudicación.

Mide, en cada conjunto: cuántas fichas tienen la misma `marca` en la planilla de la lectora y en la pasada 1 de la autora, con los pares
(lectora, autora); y, entre las que las dos marcaron `error`, en cuántas coincide la `clase`.

Uso: python3 -B acuerdo_etapa_1_S1ter.py --planilla-1 <planilla sellada de la lectora> --sha-planilla-1 <sha256 de su sello>
       --pasada-1-1 <pasada 1 de la autora, etapa 1> --sha-pasada-1-1 <sha256 de su sello> --out <json nuevo>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

PRIMERAS = [f"E1-{k:03d}" for k in range(1, 20)]   # las 19 primeras del orden de la lectura de la etapa 1
MARCAS = ("correcta", "error", "dudosa")


def leer(p: Path, sh: str, cols: tuple, que: str) -> dict[str, dict]:
    if hashlib.sha256(p.read_bytes()).hexdigest() != sh:
        sys.exit(f"FRENO: {que} no da el sha256 de su sello")
    with open(p, encoding="utf-8") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        if not set(cols) <= set(r.fieldnames or ()):
            sys.exit(f"FRENO: {que} no tiene las columnas esperadas")
        filas = list(r)
    ids = [f["ficha"] for f in filas]
    if len(ids) != len(set(ids)):
        sys.exit(f"FRENO: {que} repite fichas")
    if any(f["marca"] not in MARCAS for f in filas):
        sys.exit(f"FRENO: {que} tiene una marca no válida")
    return {f["ficha"]: f for f in filas}


def medir(ids: list[str], lec: dict, aut: dict) -> dict:
    pares = Counter((lec[i]["marca"], aut[i]["marca"]) for i in ids)
    errores = [i for i in ids if lec[i]["marca"] == "error" and aut[i]["marca"] == "error"]
    return {"fichas": len(ids), "marca_igual": sum(v for (x, y), v in pares.items() if x == y),
            "pares_lectora_autora": {f"{x}|{y}": v for (x, y), v in sorted(pares.items())},
            "las_dos_error": len(errores), "clase_igual_entre_las_dos_error": sum(1 for i in errores if lec[i]["clase"] == aut[i]["clase"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("planilla_1", "sha_planilla_1", "pasada_1_1", "sha_pasada_1_1", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        sys.exit("FRENO: la salida ya existe")
    lec = leer(Path(a.planilla_1), a.sha_planilla_1, ("ficha", "marca", "clase"), "la planilla de la lectora")
    aut = leer(Path(a.pasada_1_1), a.sha_pasada_1_1, ("ficha", "marca", "clase"), "la pasada 1 de la autora")
    if set(lec) != set(aut) or len(lec) != 90:
        sys.exit("FRENO: la pasada 1 de la etapa 1 y la planilla de la lectora no tienen las mismas 90 fichas")
    if not set(PRIMERAS) <= set(lec):
        sys.exit("FRENO: faltan fichas entre E1-001 y E1-019")
    todas = sorted(lec)
    sin = [i for i in todas if i not in PRIMERAS]
    res = {"nota": "acuerdo de la etapa 1 entre la lectora y la pasada 1 de la autora; no decide nada (hoja §58)",
           "sha256": {"planilla_lectora": a.sha_planilla_1, "pasada_1_autora": a.sha_pasada_1_1},
           "las_90": medir(todas, lec, aut),
           "sin_las_19_primeras": {"excluidas": PRIMERAS, **medir(sin, lec, aut)}}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("acuerdo escrito")


if __name__ == "__main__":
    main()
