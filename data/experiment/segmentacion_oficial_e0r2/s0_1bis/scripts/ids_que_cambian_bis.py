"""S0-1 bis: ids que cambian por TO entre la corrida final de S0-1 y la de S0-1 bis, con la regla de cada TO. La
atribución sale de una corrida intermedia con el código final y la regla 8 sin la 9: un TO cambia por la regla 8 si
la intermedia difiere de la final de S0-1, y por la 9 si la de S0-1 bis difiere de la intermedia. Solo lectura.

Uso: python -B ids_que_cambian_bis.py <final S0-1> <intermedia, sin r9> <final S0-1 bis> <tos,coma> <salida.json>"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

base, inter, nueva = (Path(x) for x in sys.argv[1:4])
tos, sal = sys.argv[4].split(","), Path(sys.argv[5])


def leer(d: Path, to: str) -> list:
    p = d / f"chunks_{to}.json"
    if not p.exists():
        p = d / "por_to" / to / f"chunks_{to}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def cambia(a: Path, b: Path, to: str) -> bool:
    return any((a / f"{k}_{to}.json").read_bytes() != (b / f"{k}_{to}.json").read_bytes()
               for k in ("chunks", "estructura", "tablas") if (a / f"{k}_{to}.json").exists())


out = OrderedDict()
for to in tos:
    cb, cn = leer(base, to), leer(nueva, to)
    db, dn = {c["id"]: c for c in cb}, {c["id"]: c for c in cn}
    reglas = [r for r, (x, y) in (("r8", (base, inter)), ("r9", (inter, nueva))) if cambia(x, y, to)]
    out[to] = OrderedDict([
        ("reglas", reglas), ("chunks", [len(cb), len(cn)]),
        ("ids_nuevos", [i for i in dn if i not in db]),
        ("ids_que_desaparecen", [i for i in db if i not in dn]),
        ("cambian", [i for i in dn if i in db and dn[i]["sha256_completo"] != db[i]["sha256_completo"]])])
res = OrderedDict([
    ("tos", len(out)),
    ("por_regla", {r: [t for t, v in out.items() if r in v["reglas"]] for r in ("r8", "r9")}),
    ("ids_nuevos", sum(len(v["ids_nuevos"]) for v in out.values())),
    ("ids_que_desaparecen", sum(len(v["ids_que_desaparecen"]) for v in out.values())),
    ("chunks_que_cambian", sum(len(v["cambian"]) for v in out.values())),
    ("chunks", [sum(v["chunks"][0] for v in out.values()), sum(v["chunks"][1] for v in out.values())]),
    ("por_to", out)])
sal.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "por_to"}, ensure_ascii=False))
for t, v in out.items():
    print(f"  {t:8} {v['reglas']} chunks {v['chunks']} nuevos {len(v['ids_nuevos'])} "
          f"desaparecen {len(v['ids_que_desaparecen'])} cambian {len(v['cambian'])}")
