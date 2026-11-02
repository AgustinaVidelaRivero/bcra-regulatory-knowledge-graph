"""S0-1 bis, A: unidades que cambian de clase (o de partición, o de llegada al tercer escalón) entre dos censos de
`censo_clases_tercer_escalon.py`. Solo lectura. Uso: python -B comparar_clases.py <censo 1> <censo 2> <salida.json>"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

a, b, sal = (Path(x) for x in sys.argv[1:4])
da, db = (json.loads(p.read_text(encoding="utf-8")) for p in (a, b))
fa, fb = ({f["id"]: f for f in d["filas"]} for d in (da, db))
clave = lambda f: (f["clase"], f["tercer_escalon"], f["partes"])  # noqa: E731
cambian = [OrderedDict([("id", i), ("antes", OrderedDict((k, fa[i][k]) for k in ("clase", "tercer_escalon", "partes"))),
                        ("despues", OrderedDict((k, fb[i][k]) for k in ("clase", "tercer_escalon", "partes",
                                                                         "renglones_e1")))])
           for i in sorted(set(fa) & set(fb)) if clave(fa[i]) != clave(fb[i])]
out = OrderedDict([
    ("censo_1", a.name), ("censo_2", b.name), ("clases_1", da["clases"]), ("clases_2", db["clases"]),
    ("comunes", len(set(fa) & set(fb))),
    ("cambian", len(cambian)),
    ("cambian_de_clase", dict(Counter(f"{c['antes']['clase']}->{c['despues']['clase']}" for c in cambian
                                      if c["antes"]["clase"] != c["despues"]["clase"]))),
    ("solo_en_1", sorted(set(fa) - set(fb))), ("solo_en_2", sorted(set(fb) - set(fa))),
    ("detalle", cambian)])
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "detalle"}, ensure_ascii=False))
for c in cambian:
    print(" ", c["id"], c["antes"]["clase"], "->", c["despues"]["clase"], c["despues"]["tercer_escalon"],
          c["despues"]["renglones_e1"])
