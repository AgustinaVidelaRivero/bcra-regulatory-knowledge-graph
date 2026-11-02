"""Manifiesto de una salida de E0 de los 152 (U-SEG-OFICIAL, S0-5a; solo lectura): con la forma del de S0-4b
(`manifiesto_salida_e0_152_S0-4b.json`): el sha256 del código, archivos, TOs, unidades (total y por TO) y el sha256 y
los bytes de cada archivo.
Uso: python -B manifiesto_salida_S0-5a.py <salida> <dir del código> <unidad> <out>"""
import hashlib
import json
import sys
from pathlib import Path

d, cod, unidad, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
arch = sorted(p for p in d.iterdir() if p.is_file())
por_to = {p.name[len("chunks_"):-5]: len(json.loads(p.read_text(encoding="utf-8")))
          for p in arch if p.name.startswith("chunks_")}
m = {"unidad": unidad, "codigo_sha256": {f: h(cod / f) for f in ("e0_lib.py", "correr_e0.py", "selftest_e0.py")},
     "archivos": len(arch), "tos": len(por_to), "unidades": sum(por_to.values()), "unidades_por_to": por_to,
     "sha256": {p.name: {"sha256": h(p), "bytes": p.stat().st_size} for p in arch}}
out.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in m.items() if k in ("archivos", "tos", "unidades", "codigo_sha256")}, ensure_ascii=False))
