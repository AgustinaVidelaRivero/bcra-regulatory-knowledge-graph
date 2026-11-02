"""S0-4a-ter (U-SEG-OFICIAL), USD 0, solo lectura: efecto de cada regla dentro de la configuración final. Para cada
regla, compara la corrida final con la corrida con todas menos esa regla (en los seis TOs de las reglas de
sub-documento) y cuenta, por TO, los ids nuevos, los que desaparecen y las unidades que cambian, por campo.
Uso: python -B marginal_ter.py <final> <dir con ter_sin_<r>> <reglas,coma> <tos,coma> <salida.json>"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

final, base, reglas, tos, salida = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3].split(","), \
    sys.argv[4].split(","), Path(sys.argv[5])


def leer(d, to):
    return {c["id"]: c for c in json.loads((d / f"chunks_{to}.json").read_text(encoding="utf-8"))}


out = OrderedDict()
for r in reglas:
    fila = OrderedDict()
    for to in tos:
        a, b = leer(base / f"ter_sin_{r}", to), leer(final, to)
        nuevos = [i for i in b if i not in a]
        idos = [i for i in a if i not in b]
        campos = Counter()
        cambian = []
        for i in a:
            if i in b and a[i] != b[i]:
                cambian.append(i)
                campos[",".join(k for k in sorted(set(a[i]) | set(b[i])) if a[i].get(k) != b[i].get(k)
                                if k not in ("sha256_propio", "sha256_completo", "chars_propio", "chars_completo"))] += 1
        if nuevos or idos or cambian:
            fila[to] = OrderedDict([("unidades", [len(a), len(b)]), ("nuevos", nuevos), ("desaparecen", idos),
                                    ("cambian", cambian), ("campos_que_cambian", dict(campos))])
    out[r] = fila
salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for r, f in out.items():
    print(r, {to: (len(v["nuevos"]), len(v["desaparecen"]), len(v["cambian"]), v["campos_que_cambian"])
              for to, v in f.items()})
