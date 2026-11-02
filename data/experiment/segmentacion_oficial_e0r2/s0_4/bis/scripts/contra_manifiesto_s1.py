"""S0-4a-bis (U-SEG-OFICIAL), USD 0, solo lectura: compara los archivos del primer nivel de una corrida de E0 con los
sha256 de los 768 archivos `e0/` de `s1/manifest_salida.json` (la salida sellada de S1, `ee7c07c`).
Uso: python -B contra_manifiesto_s1.py <corrida> <manifest_salida.json>"""
import hashlib
import json
import sys
from pathlib import Path

d, man = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
e0 = {k[len("e0/"):]: v["sha256"] for k, v in man["sha256"].items() if k.startswith("e0/")}
propios = {p.name for p in d.glob("*.json")}
dist = [n for n in sorted(set(e0) | propios)
        if n not in e0 or n not in propios or hashlib.sha256((d / n).read_bytes()).hexdigest() != e0[n]]
print(f"{len(set(e0) | propios)} archivos comparados ({len(e0)} en el manifiesto); "
      f"{len(set(e0) | propios) - len(dist)} iguales; {len(dist)} distintos" + (f": {dist[:10]}" if dist else ""))
