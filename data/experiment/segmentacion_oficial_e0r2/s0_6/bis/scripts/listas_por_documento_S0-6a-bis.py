"""En qué listas por documento del código de E0 está cada documento dado (U-SEG-OFICIAL, S0-6a-bis; USD 0, solo lectura).
Sirve para la bolsa (`docs/plan_tesis.md:782`, punto 4: se excluyen del sorteo los documentos que recibieron una
corrección hecha para ellos): recorre las constantes en mayúsculas de `correr_e0.py` que son conjuntos o diccionarios
de TOs, salvo las de la tanda 0.

Uso: python -B listas_por_documento_S0-6a-bis.py --codigo <dir de correr_e0.py> --tos <to,to,…> --out <json>
(importa correr_e0: corre con el .venv del repo)
"""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--codigo", type=Path, required=True)
ap.add_argument("--tos", required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
sys.path.insert(0, str(a.codigo))
import correr_e0 as C     # noqa: E402

tos = a.tos.split(",")
res = {to: [] for to in tos}
for nombre in sorted(dir(C)):
    v = getattr(C, nombre)
    if not nombre.isupper() or "TANDA0" in nombre or not isinstance(v, (frozenset, set, dict)) or not v:
        continue
    if not all(isinstance(k, str) for k in v):
        continue
    for to in tos:
        if to in v:
            res[to].append(nombre)
a.out.write_text(json.dumps({"codigo": str(a.codigo.name), "listas_por_documento": res}, ensure_ascii=False, indent=1)
                 + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
