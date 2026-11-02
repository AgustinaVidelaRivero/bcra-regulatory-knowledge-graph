"""Resumen en cuentas de las salidas de los selftests de S0-6b (U-SEG-OFICIAL; USD 0, solo lectura). Las salidas enteras
llevan el detalle de cada caso, con ids y texto de unidades: van al paquete como archivos NO_ABRIR_ y no se imprimen.
De cada una toma solo: los [PASS] y [FAIL] contados, los renglones de resumen («SELFTEST…: n/n PASS», «n/n checks OK»,
«VEREDICTO: …») y los rc.

Uso: python -B resumen_selftests_S0-6b.py --salida nombre=<txt> [--salida nombre=<txt> …] --out <json>
"""
import argparse
import json
import re
from pathlib import Path

RX = re.compile(r"^(SELFTEST[\w .]*: \d+/\d+ (PASS|FAIL)|\d+/\d+ checks OK|VEREDICTO: \w+|rc=\d+|== selftest_\w+ rc=\d+.*)$")
ap = argparse.ArgumentParser()
ap.add_argument("--salida", action="append", required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
res = {}
for x in a.salida:
    n, p = x.split("=", 1)
    lineas = Path(p).read_text(encoding="utf-8", errors="replace").splitlines()
    res[n] = {"pass": sum(1 for l in lineas if "[PASS]" in l), "fail": sum(1 for l in lineas if "[FAIL]" in l),
              "resumen": [re.sub(r" fin \d\d:\d\d:\d\d$", "", l.strip()) for l in lineas if RX.match(l.strip())]}
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
