"""U-SEG-OFICIAL, S1-quater: acuerdo de la etapa 1 entre la lectora y la pasada 1 de la autora (mesa, 13/10/2026; USD 0). Sellado
antes de que la autora abra la pasada 1 (`sello_scripts_adjudicacion_S1quater_mesa.txt`). No decide nada; se corre después de la
adjudicación.

Adaptado de `s1ter/adjudicacion/acuerdo_etapa_1_S1ter.py`, sin el recorte de las 19 primeras fichas: respondía a un incidente de la
lectura de S1-ter (`s1ter/lectura/incidentes_lectura_S1ter.md`) que S1-quater no tiene (regla de la autora del 13/10/2026, hoja de ruta
de la mesa, §92). Mide, sobre las 90 fichas: cuántas tienen la misma `marca` en la planilla de la lectora y en la pasada 1 de la
autora, con los pares (lectora, autora); y, entre las que las dos marcaron `error`, en cuántas coincide la `clase`. Lee la pasada 1 con
el mismo control de forma que `pasada_2_S1quater.py`.

Uso: python3 -B acuerdo_etapa_1_S1quater.py --planilla-1 <planilla sellada de la lectora> --sha-planilla-1 <sha256 de su sello>
       --pasada-1-1 <pasada 1 de la autora, etapa 1> --sha-pasada-1-1 <sha256 de su sello> --out <json nuevo>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pasada_2_S1quater as P  # noqa: E402


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
        P.freno("la salida ya existe")
    lec = P.leer_lectora(Path(a.planilla_1), a.sha_planilla_1, "la planilla de la lectora")
    filas = P.leer_autora(Path(a.pasada_1_1), a.sha_pasada_1_1, P.ADJ, "la pasada 1 de la autora")
    P.validar_adj(filas, 1, "la pasada 1 de la autora")
    aut = {f["ficha"]: f for f in filas}
    if any(f["marca"] not in P.MARCAS for f in lec.values()):
        P.freno("la planilla de la lectora tiene una marca no válida")
    if set(lec) != set(aut) or len(lec) != 90:
        P.freno("la pasada 1 de la etapa 1 y la planilla de la lectora no tienen las mismas 90 fichas")
    res = {"nota": "acuerdo de la etapa 1 entre la lectora y la pasada 1 de la autora; no decide nada",
           "sha256": {"planilla_lectora": a.sha_planilla_1, "pasada_1_autora": a.sha_pasada_1_1},
           "las_90": medir(sorted(lec), lec, aut)}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("acuerdo escrito")


if __name__ == "__main__":
    main()
