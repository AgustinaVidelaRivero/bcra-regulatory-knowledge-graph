"""U-SEG-OFICIAL, S1-ter-b: reproducción del sorteo con código aparte de `sorteo_S1ter.py` (USD 0).

Uso: python -B reproducir_sorteo_S1ter.py <directorio tramo_b>

Vuelve a sortear desde `poblaciones_finales_S1ter.json`, con las mismas cadenas y formas, y compara con
`muestra_S1ter.json` y `orden_lectura_S1ter.json`.
"""
import json
import random
import sys
from pathlib import Path

E = Path(sys.argv[1])
p = json.load(open(E / "poblaciones_finales_S1ter.json"))
m = json.load(open(E / "muestra_S1ter.json"))
o = json.load(open(E / "orden_lectura_S1ter.json"))
print("# reproducción del sorteo de S1-ter-b con código aparte (Python", sys.version.split()[0] + ")")
ok = True
s90 = []
for e, n in (("vigente", 40), ("marcadores", 10), ("sin_raiz", 40)):
    s = random.Random("U-SEG-OFICIAL:cortes:S1-ter:" + e).sample(sorted(p["cortes"][e]["ids"]), n)
    s90 += s
    r = s == m["cortes"][e]["muestra"]
    ok &= r
    print("cortes", e, n, "igual" if r else "DISTINTO")
o90 = random.Random("U-SEG-OFICIAL:cortes:S1-ter:orden").sample(sorted(s90), 90)
r = o90 == [f["id"] for f in o["etapa_1"]["fichas"]]
ok &= r
print("orden de las 90", "igual" if r else "DISTINTO")
a = random.Random("U-SEG-OFICIAL:1_16:S1-ter").sample(sorted(p["c116_a"]["ids"]), 30)
r = a == m["c116_a"]["muestra"]
ok &= r
print("(a) 30", "igual" if r else "DISTINTO")
c = random.Random("U-SEG-OFICIAL:1_16:S1-ter:ri_oc").choice(sorted(p["c116_b"]["seccion_3_ri_oc"]["ids"]))
r = c == m["c116_b"]["seccion_3_ri_oc"]["elegida"]
ok &= r
print("sección 3 de ri_oc", "igual" if r else "DISTINTO")
i66 = a + p["c116_b"]["fijos"]["ids"] + [c]
print("ids_66 distintos", len(set(i66)))
o66 = random.Random("U-SEG-OFICIAL:1_16:S1-ter:R5-a").sample(sorted(i66), 66)
r = o66 == [f["id"] for f in o["etapa_2"]["fichas"][:66]]
ok &= r
print("orden de las 66", "igual" if r else "DISTINTO")
r = sorted(p["regresion"]["ids"]) == [f["id"] for f in o["etapa_2"]["fichas"][66:]]
ok &= r
print("bloque de regresión (35, sorted)", "igual" if r else "DISTINTO")
print("TODO IGUAL" if ok else "HAY DIFERENCIAS")
sys.exit(0 if ok else 1)
