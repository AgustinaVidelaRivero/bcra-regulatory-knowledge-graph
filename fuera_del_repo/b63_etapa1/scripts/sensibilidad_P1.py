"""Sensibilidad P1 (no reemplaza a proporciones_P1): cuánto pesa el criterio de lectura de la herencia.
Escenario B: las unidades cuyo «varios puntos» descansa solo en una cita de la herencia (lista fijada a mano
a partir de las notas de clasificacion_P1.csv) pasan a «dato directo»."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from proporciones_P1 import CLASES, cruda, fmt, ponderada  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
SOLO_HERENCIA = [
    "ri_dsf::2.2", "ri_laft::1.4", "ri_mmsef::2.2.4", "ri_ii_31_12_19::2.6.2", "ri_gerc::2.5.3",
    "ri_ii_31_12_19::2.6.1", "ri_laft::1.3", "ri_ii_31_12_19::2.6.3", "cescar::2.2.3", "autenf::3.2.9",
    "servco::2.3.2.1", "snp_tr::4.1",
]


def main():
    filas = list(csv.DictReader(open(BASE / "clasificacion_P1.csv", encoding="utf-8")))
    ids = {f["unidad"] for f in filas}
    assert set(SOLO_HERENCIA) <= ids
    assert all(f["tipo"] == "varios puntos" for f in filas if f["unidad"] in SOLO_HERENCIA)
    pob = json.loads((BASE / "poblacion_P1.json").read_text())
    N = {c: sum(1 for x in pob if x["clase"] == c) for c in CLASES}
    dec = [f for f in filas if f["tipo"] != "no decidible"]
    n_dec = {c: sum(1 for f in dec if f["clase"] == c) for c in CLASES}
    w = {c: N[c] / n_dec[c] for c in CLASES}
    vpA = lambda f: f["tipo"] == "varios puntos"
    vpB = lambda f: f["tipo"] == "varios puntos" and f["unidad"] not in SOLO_HERENCIA
    out = [f"unidades que pasan a dato directo en B: {len(SOLO_HERENCIA)}", ""]
    for c in CLASES:
        fc = [f for f in dec if f["clase"] == c]
        out.append(f"{c:20s} A (sellada) {fmt(cruda(fc, vpA))}")
        out.append(f"{'':20s} B           {fmt(cruda(fc, vpB))}")
    out.append(f"{'ponderada':20s} A (sellada) {fmt(ponderada(dec, vpA, w))}")
    out.append(f"{'':20s} B           {fmt(ponderada(dec, vpB, w))}")
    txt = "\n".join(out) + "\n"
    (BASE / "sensibilidad_P1_salida.txt").write_text(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
