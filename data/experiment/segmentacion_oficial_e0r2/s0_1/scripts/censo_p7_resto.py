"""Punto 7, lo que la regla no alcanza (solo lectura): rótulos con título en mayúscula rechazados por «padre no
abierto» cuyo padre existe como nodo del TO, en una salida de E0. Uso: python -B censo_p7_resto.py <dir> <salida>"""
import json, re, sys
from collections import Counter
from pathlib import Path
d, sal = Path(sys.argv[1]), Path(sys.argv[2])
filas = []
for p in sorted(d.glob("por_to/*/estructura_*.json")) or sorted(d.glob("estructura_*.json")):
    e = json.loads(p.read_text(encoding="utf-8"))
    nums = set()
    def rec(n):
        nums.add(n["numero"])
        for h in n["hijos"]:
            rec(h)
    for s in e["secciones"]:
        rec(s)
    for r in e["rechazos_header"]:
        m = re.match(r"padre_(.+)_no_abierto", r["motivo"])
        t = r["texto"].split(None, 1)
        if m and m.group(1) in nums and len(t) > 1 and re.match(r'^[A-ZÁÉÍÓÚÜÑ"“\'(«]', t[1]):
            filas.append({"to": e["to"], "pagina": r["pagina"], "padre": m.group(1), "linea": r["texto"][:90]})
out = {"e0": d.name, "total": len(filas), "por_to": dict(Counter(f["to"] for f in filas)), "filas": filas}
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "filas"}, ensure_ascii=False))
