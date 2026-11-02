"""S0-4a-bis (U-SEG-OFICIAL), USD 0, solo lectura: los eventos de la regla sdmax son los mismos sobre la configuración
de S0-4a y sobre sd sola. Compara, TO por TO, los eventos (id nuevo, id que desaparece, unidad que cambia) de dos pares
de corridas, y para cada evento el contenido de la unidad después (texto, herencia, páginas y flags).
Uso: python -B eventos_sdmax.py <antes_1> <despues_1> <antes_2> <despues_2> <to,to,…> <salida.json>"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

a1, d1, a2, d2 = (Path(x) for x in sys.argv[1:5])
tos, salida = [t for t in sys.argv[5].split(",") if t], Path(sys.argv[6])
CAMPOS = ("texto", "herencia", "paginas", "flags", "tipo")


def leer(d, to):
    return {c["id"]: c for c in json.loads((d / f"chunks_{to}.json").read_text(encoding="utf-8"))}


def eventos(a, d):
    ev = {}
    for i in d:
        if i not in a:
            ev[("nuevo", i)] = {k: d[i].get(k) for k in CAMPOS}
        elif a[i] != d[i]:
            ev[("cambia", i)] = {k: d[i].get(k) for k in CAMPOS}
    for i in a:
        if i not in d:
            ev[("desaparece", i)] = None
    return ev


out = OrderedDict()
for to in tos:
    e1, e2 = eventos(leer(a1, to), leer(d1, to)), eventos(leer(a2, to), leer(d2, to))
    out[to] = OrderedDict([("eventos_par_1", len(e1)), ("eventos_par_2", len(e2)),
                           ("mismos_eventos", sorted(e1) == sorted(e2)),
                           ("mismo_contenido", e1 == e2),
                           ("eventos", [list(k) for k in sorted(e1)])])
salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print({to: (v["eventos_par_1"], v["eventos_par_2"], v["mismos_eventos"], v["mismo_contenido"]) for to, v in out.items()})
