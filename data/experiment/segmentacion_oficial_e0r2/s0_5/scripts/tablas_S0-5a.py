"""Las tablas de e0_tablas antes y después de las reglas de S0-5a (U-SEG-OFICIAL; USD 0, solo lectura de las salidas).

Uso: python -B tablas_S0-5a.py --antes <E0 de S0-4b> --despues <E0 de S0-5a> --out <json>

Por TO: las tablas serializadas en el texto de las unidades («[TABLA <id> | …]»), las que dejan de serializarse, las
que cambian de unidad, y las entradas de `tablas_<to>.json` que cambian la lista de unidades que cubren (`chunks`). Una
tabla deja de serializarse cuando sus renglones quedan repartidos entre unidades: entonces van como renglones sueltos.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RE_TABLA = re.compile(r"\[TABLA (\S+) \|")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def serializadas(d: Path, to: str) -> dict[str, str]:
    return {m.group(1): c["id"] for c in jl(d / f"chunks_{to}.json") for m in RE_TABLA.finditer(c["texto"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("antes", "despues", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    tos = sorted(p.name[len("chunks_"):-5] for p in a.antes.glob("chunks_*.json"))
    por_to, tot = {}, [0, 0]
    for to in tos:
        sa, sb = serializadas(a.antes, to), serializadas(a.despues, to)
        tot[0] += len(sa)
        tot[1] += len(sb)
        ta, tb = jl(a.antes / f"tablas_{to}.json"), jl(a.despues / f"tablas_{to}.json")
        la = {t["id"]: t for t in (ta if isinstance(ta, list) else ta.get("tablas", []))}
        lb = {t["id"]: t for t in (tb if isinstance(tb, list) else tb.get("tablas", []))}
        cubren = {i: [la[i].get("chunks"), lb[i].get("chunks")] for i in sorted(set(la) & set(lb))
                  if la[i].get("chunks") != lb[i].get("chunks")}
        r = {"dejan_de_serializarse": sorted(set(sa) - set(sb)), "nuevas": sorted(set(sb) - set(sa)),
             "cambian_de_unidad": {i: [sa[i], sb[i]] for i in sorted(set(sa) & set(sb)) if sa[i] != sb[i]},
             "cambian_las_unidades_que_cubren": cubren}
        if any(r.values()):
            por_to[to] = r
    res = {"serializadas": {"antes": tot[0], "despues": tot[1]},
           "dejan_de_serializarse": sum(len(r["dejan_de_serializarse"]) for r in por_to.values()),
           "cambian_de_unidad": sum(len(r["cambian_de_unidad"]) for r in por_to.values()),
           "cambian_las_unidades_que_cubren": sum(len(r["cambian_las_unidades_que_cubren"]) for r in por_to.values()),
           "por_to": por_to}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_to"}, ensure_ascii=False))
    for to, r in por_to.items():
        print(to, {k: (v if not isinstance(v, dict) else list(v)) for k, v in r.items() if v})


if __name__ == "__main__":
    main()
