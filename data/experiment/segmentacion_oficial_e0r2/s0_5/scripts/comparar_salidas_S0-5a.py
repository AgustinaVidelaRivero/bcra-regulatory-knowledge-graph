"""Compara dos salidas de E0, todos los archivos de primer nivel (768: 5 por TO y 8 agregados), byte a byte por sha256:
contra el manifiesto de la salida de S0-4b (`sha256`) o contra otra salida.
Uso: comparar_salidas.py <dir> (--manifiesto <json> | --otra <dir>)"""
import hashlib, json, sys
from pathlib import Path
d = Path(sys.argv[1])
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def todos(x): return {p.name: h(p) for p in x.iterdir() if p.is_file()}
a = todos(d)
if sys.argv[2] == "--manifiesto":
    m = json.load(open(sys.argv[3])); ref = {k: (v["sha256"] if isinstance(v, dict) else v) for k, v in m["sha256"].items()}
    print("unidades del manifiesto:", m["unidades"])
else:
    ref = todos(Path(sys.argv[3]))
dist = sorted(k for k in set(a) | set(ref) if a.get(k) != ref.get(k))
print(f"{len(a)} y {len(ref)} archivos; distintos {len(dist)}; iguales {len(set(a) & set(ref)) - sum(1 for k in dist if k in a and k in ref)}")
print("distintos:", dist[:30], "…" if len(dist) > 30 else "")
u = sum(len(json.load(open(d / f))) for f in a if f.startswith("chunks_"))
print("unidades en", d.name, ":", u)
