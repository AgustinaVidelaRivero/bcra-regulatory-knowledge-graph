"""Control de la E0 corregida de S2 contra el manifiesto de S0-6b (U-SEG-OFICIAL, S2, tramo 1; solo lectura).

Uso: python -B control_e0_contra_manifiesto_S2.py --e0 <salida de E0 de los 152> --manifiesto <json> --out <json>

Por cada entrada `e0/<archivo>` del manifiesto: que <salida>/<archivo> exista y dé su sha256 y sus bytes. Además,
los archivos de primer nivel de la salida que el manifiesto no tiene (los de `por_to/` no cuentan: son la corrida
por TO antes de juntarla) y las unidades, como suma de los `chunks_<to>.json`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--manifiesto", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    m = json.loads(a.manifiesto.read_text(encoding="utf-8"))
    esperados = {k[len("e0/"):]: v for k, v in m["sha256"].items() if k.startswith("e0/")}
    presentes = {p.name for p in a.e0.iterdir() if p.is_file()}
    faltan = sorted(set(esperados) - presentes)
    sobran = sorted(presentes - set(esperados))
    distintos = sorted(n for n in set(esperados) & presentes
                       if sha(a.e0 / n) != esperados[n]["sha256"] or (a.e0 / n).stat().st_size != esperados[n]["bytes"])
    iguales = len(set(esperados) & presentes) - len(distintos)
    unidades_por_to = {p.name[len("chunks_"):-5]: len(json.loads(p.read_text(encoding="utf-8")))
                       for p in sorted(a.e0.glob("chunks_*.json"))}
    out = {"manifiesto_sha256": sha(a.manifiesto), "esperados": len(esperados), "presentes": len(presentes),
           "iguales": iguales, "distintos": distintos, "faltan": faltan, "sobran": sobran,
           "tos": len(unidades_por_to), "unidades": sum(unidades_por_to.values()),
           "unidades_manifiesto": m["unidades"],
           "unidades_por_to_iguales": unidades_por_to == m["unidades_por_to"],
           "veredicto": "OK" if (iguales == len(esperados) == 768 and not faltan and not sobran
                                 and sum(unidades_por_to.values()) == 10478 == m["unidades"]) else "FALLA"}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
