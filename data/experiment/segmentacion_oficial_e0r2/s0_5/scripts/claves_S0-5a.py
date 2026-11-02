"""Claves de S0-5a (U-SEG-OFICIAL; USD 0, sin API): la lista declarada de las claves creadas, quitadas y cambiadas, con
la regla que causa cada una, y su selftest.

Uso:
  python -B claves_S0-5a.py declarar --censo <censo_por_regla_S0-5a.json> --out <claves_S0-5a.json>
  python -B claves_S0-5a.py controlar --antes <E0 de S0-4b> --despues <E0 de S0-5a> --claves <claves_S0-5a.json>
       [--out <json>]

`declarar` arma la lista desde el censo por regla (la configuración final contra las reglas apagadas, que es la salida
de S0-4b, 768 de 768): por clave (`<to>::…`), si se crea, se quita o cambia, la regla que lo causa (la regla sola que
produce el mismo evento con la misma unidad final; si son varias, todas), y, de una cambiada, los campos que cambian.
`controlar` recalcula las diferencias de claves entre dos salidas de E0 y da VEREDICTO OK solo si las creadas, las
quitadas y las cambiadas son exactamente las declaradas (mismo conjunto en cada clase); si no, lista las que sobran y
las que faltan. Política de claves (mandato de S0-5a, §4): las de las unidades que ninguna regla toca no cambian; una
unión conserva la clave de la primera unidad y no renumera las siguientes; las nuevas siguen la convención de E0.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def diferencias(antes: Path, despues: Path) -> dict[str, set]:
    out = {"creadas": set(), "quitadas": set(), "cambiadas": set()}
    for p in sorted(antes.glob("chunks_*.json")):
        q = despues / p.name
        if p.read_bytes() == q.read_bytes():
            continue
        a = {c["id"]: c for c in jl(p)}
        b = {c["id"]: c for c in jl(q)}
        out["creadas"] |= set(b) - set(a)
        out["quitadas"] |= set(a) - set(b)
        out["cambiadas"] |= {i for i in set(a) & set(b) if a[i] != b[i]}
    return out


def declarar(censo: Path, out: Path) -> None:
    c = jl(censo)
    por_to = c["final"]["por_to"]
    filas = []
    for to, r in sorted(por_to.items()):
        for clase, ids in (("creada", r["creadas"]), ("quitada", r["quitadas"]), ("cambiada", sorted(r["cambiadas"]))):
            for i in ids:
                at = c["atribucion"][f"{to}|{i}"]
                filas.append({"clave": i, "to": to, "evento": clase,
                              "reglas": at["igual_a_la_regla_sola"] or at["reglas"],
                              "atribucion_exacta": bool(at["igual_a_la_regla_sola"]),
                              **({"campos": r["cambiadas"][i]} if clase == "cambiada" else {})})
    res = {"fuente": censo.name, "claves": len(filas),
           "por_evento": {e: sum(1 for f in filas if f["evento"] == e) for e in ("creada", "quitada", "cambiada")},
           "por_regla": {r: sum(1 for f in filas if r in f["reglas"])
                         for r in sorted({r for f in filas for r in f["reglas"]})},
           "sin_atribucion_exacta": [f["clave"] for f in filas if not f["atribucion_exacta"]],
           "filas": filas}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "filas"}, ensure_ascii=False, indent=1))


def controlar(antes: Path, despues: Path, claves: Path, out: Path | None) -> int:
    dec = jl(claves)["filas"]
    declaradas = {e: {f["clave"] for f in dec if f["evento"] == e[:-1]} for e in ("creadas", "quitadas", "cambiadas")}
    obs = diferencias(antes, despues)
    res = {e: {"declaradas": len(declaradas[e]), "observadas": len(obs[e]),
               "sobran": sorted(obs[e] - declaradas[e]), "faltan": sorted(declaradas[e] - obs[e])}
           for e in ("creadas", "quitadas", "cambiadas")}
    ok = all(not v["sobran"] and not v["faltan"] for v in res.values())
    res["VEREDICTO"] = "OK" if ok else "FALLA"
    if out is not None:
        out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("declarar")
    d.add_argument("--censo", type=Path, required=True)
    d.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("controlar")
    c.add_argument("--antes", type=Path, required=True)
    c.add_argument("--despues", type=Path, required=True)
    c.add_argument("--claves", type=Path, required=True)
    c.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    if a.cmd == "declarar":
        declarar(a.censo, a.out)
        return 0
    return controlar(a.antes, a.despues, a.claves, a.out)


if __name__ == "__main__":
    raise SystemExit(main())
