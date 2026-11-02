"""S0-2 de U-SEG-OFICIAL: la corrida de S0-2 contra los ids que cambian de S0-1 y de S0-1 bis (censos commiteados).
1. Los ids de cada TO según los dos censos, compuestos sobre la base (`9f6361e`): base − desaparecen de S0-1 + nuevos
   de S0-1 − desaparecen de S0-1 bis + nuevos de S0-1 bis. Control: la corrida final de S0-1 bis tiene esos ids.
2. Diferencias de la corrida de S0-2 contra la de S0-1 bis, por TO (ids nuevos, ids que desaparecen, chunks con otro
   texto), cada una con su causa: la decisión 5 (objetivo de las partes por renglones, 10.886) si aparece en la corrida
   intermedia (código de S0-2 sin la ampliación de la regla 3), la decisión 8 (rol de índice) si aparece solo al
   sumarla. Lo que ninguna explique es «otra». Solo lectura.

Uso: python -B conciliar_ids.py <base> <S0-1.json> <S0-1bis.json> <final S0-1 bis> <intermedia sin r3i> <S0-2> <salida>"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

base, j1, j2, bis, inter, s02, sal = (Path(x) for x in sys.argv[1:8])


def chunks(d: Path, to: str) -> dict:
    p = d / f"chunks_{to}.json"
    if not p.exists():
        p = d / "por_to" / to / f"chunks_{to}.json"
    return {c["id"]: c for c in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else None


c1 = json.loads(j1.read_text(encoding="utf-8"))["por_to"]
c2 = json.loads(j2.read_text(encoding="utf-8"))["por_to"]
tos_s02 = sorted(p.name[7:-5] for p in s02.glob("chunks_*.json"))
reproduce, filas = OrderedDict(), OrderedDict()
cuenta = Counter()
for to in tos_s02:
    b, f, i, n = chunks(base, to), chunks(bis, to), chunks(inter, to), chunks(s02, to)
    esperado = set(b)
    for c in (c1, c2):
        if to in c:
            esperado = (esperado - set(c[to]["ids_que_desaparecen"])) | set(c[to]["ids_nuevos"])
    if to in c1 or to in c2:
        reproduce[to] = esperado == set(f)
    if n == f:
        continue
    if i is None:
        i = f
    eventos = []
    for tipo, ids in (("nuevo", set(n) - set(f)), ("desaparece", set(f) - set(n)),
                      ("cambia", {k for k in set(n) & set(f) if n[k]["sha256_completo"] != f[k]["sha256_completo"]})):
        for k in sorted(ids):
            if tipo == "nuevo":
                d5 = k in i and k not in f
            elif tipo == "desaparece":
                d5 = k not in i
            else:
                d5 = k in i and i[k]["sha256_completo"] != f[k]["sha256_completo"]
            if d5:
                causa = "decision_5"
            else:
                causa = "decision_8"
                if tipo == "cambia" and k in i and i[k]["sha256_completo"] == n[k]["sha256_completo"]:
                    causa = "otra"
            eventos.append([tipo, k, causa])
            cuenta[(tipo, causa)] += 1
    filas[to] = OrderedDict([("chunks", [len(f), len(n)]), ("eventos", eventos),
                             ("por_causa", dict(Counter(e[2] for e in eventos)))])
out = OrderedDict([
    ("control_las_corridas_reproducen_los_censos", {"tos": len(reproduce), "iguales": sum(reproduce.values()),
                                                     "distintos": [t for t, v in reproduce.items() if not v]}),
    ("tos_que_difieren_de_S0-1bis", list(filas)),
    ("eventos", {f"{t}|{c}": v for (t, c), v in sorted(cuenta.items())}),
    ("por_to", filas)])
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "por_to"}, ensure_ascii=False))
for t, r in filas.items():
    print(" ", t, r["chunks"], r["por_causa"])
