"""Compara las cuentas del control de continuidad de S0-6b con las de S0-6a-bis (U-SEG-OFICIAL, S0-6b; USD 0, solo
lectura): las dos salidas de `s0_6/bis/scripts/continuidad_cuentas_S0-6a-bis.py`, sin el campo de la primera corrida de
S0-6a (S0-6b no lo calcula). Solo cuentas por documento y clase.

Uso: python -B comparar_continuidad_S0-6b.py --a <cuentas de S0-6a-bis> --b <cuentas de S0-6b> --out <json>
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
for k in ("a", "b", "out"):
    ap.add_argument(f"--{k}", type=Path, required=True)
x = ap.parse_args()
A, B = (json.loads(p.read_text(encoding="utf-8")) for p in (x.a, x.b))
for d in (A, B):
    d.pop("primera_corrida_S0-6a", None)
res = {"iguales": A == B, "antes": B["antes"], "despues": B["despues"], "cerrados": B["cerrados"], "nuevos": B["nuevos"],
       "despues_por_clase": B["despues_por_clase"],
       "documentos_con_cuentas_distintas": sorted(t for t in set(A.get("por_to", {})) | set(B.get("por_to", {}))
                                                  if A.get("por_to", {}).get(t) != B.get("por_to", {}).get(t))}
x.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
