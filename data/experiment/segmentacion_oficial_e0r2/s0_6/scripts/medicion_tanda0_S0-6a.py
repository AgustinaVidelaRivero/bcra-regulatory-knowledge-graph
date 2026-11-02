"""Lo que las reglas de S0-6a cambiarían en la tanda 0 si corrieran ahí (U-SEG-OFICIAL; USD 0, solo lectura): la salida
del prototipo con `S0_6_TANDA0=1` contra `salida_tanda0_r2b/`, por TO, en ids y cuentas. Es una medición: la exclusión
rige, y la salida de la tanda 0 no cambia (límite declarado).

Uso: python -B medicion_tanda0_S0-6a.py <salida sin la exclusión> <salida_tanda0_r2b> <out.json>
"""
import json
import sys
from pathlib import Path

a, b, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
res = {}
for f in sorted(b.glob("chunks_*.json")):
    to = f.name[len("chunks_"):-5]
    A = {c["id"]: c for c in json.loads((a / f.name).read_text(encoding="utf-8"))}
    B = {c["id"]: c for c in json.loads(f.read_text(encoding="utf-8"))}
    cam = {i: sorted(k for k in set(A[i]) | set(B[i]) if A[i].get(k) != B[i].get(k)
                     and k not in ("chars_propio", "chars_completo", "sha256_propio", "sha256_completo"))
           for i in sorted(set(A) & set(B)) if A[i] != B[i]}
    res[to] = {"creadas": sorted(set(A) - set(B)), "quitadas": sorted(set(B) - set(A)), "cambiadas": cam}
tot = {k: sum(len(v[k]) for v in res.values()) for k in ("creadas", "quitadas", "cambiadas")}
out.write_text(json.dumps({"total": tot, "por_to_cuentas": {t: {k: len(v[k]) for k in v} for t, v in res.items()},
                           "por_to": res}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(tot), {t: {k: len(v[k]) for k in v} for t, v in res.items()})
