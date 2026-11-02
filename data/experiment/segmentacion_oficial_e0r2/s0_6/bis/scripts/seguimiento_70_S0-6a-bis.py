"""Seguimiento de los 70 cambios en unidades leídas de la primera corrida de S0-6a (U-SEG-OFICIAL, S0-6a-bis; USD 0, sin
API; solo lectura): por unidad de la tabla de la mesa (`cambios_en_leidas_S0-6a_clasificados_mesa.md`, «Unidad por
unidad»), qué queda en la E0 de esta etapa: el cambio sigue (igual a la primera corrida), vuelve a lo de S1-ter (igual a
la E0 de S1-ter), o es otro. Se compara el corte (id, sha256 propio y páginas) y la herencia.

Uso: python -B seguimiento_70_S0-6a-bis.py --tabla <md de la mesa> --s1ter <E0 de S1-ter> --s06a <E0 de la primera
       corrida> --nueva <E0 de esta etapa> --out <json>

La aceptación (el «seguí», decisión 1): ninguna de las que empeoran sigue empeorando (no puede quedar «sigue») y las que
mejoran siguen mejorando (tienen que quedar «sigue»); las neutras no pueden pasar a empeorar. Un «otro» se juzga
aparte, contra la página. Solo ids, campos y estados: sin texto.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CAMPOS = ("sha256_propio", "paginas", "herencia")


def chunks(d: Path, to: str) -> dict:
    return {c["id"]: c for c in json.loads((d / f"chunks_{to}.json").read_text(encoding="utf-8"))}


def igual(a: dict | None, b: dict | None) -> bool:
    return a is not None and b is not None and all(a.get(k) == b.get(k) for k in CAMPOS)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("tabla", "s1ter", "s06a", "nueva", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    filas = []
    for l in a.tabla.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| `([^`]+)` \| (etapa_\d) \| (.*?) \| (.*?) \| (.*?) \| (G\w+) \| (\w+) \|$", l)
        if m:
            filas.append({"id": m.group(1), "etapa": m.group(2), "grupo": m.group(6), "veredicto": m.group(7)})
    out = []
    cache: dict = {}
    for f in filas:
        to = f["id"].split("::")[0]
        for k, d in (("s1ter", a.s1ter), ("s06a", a.s06a), ("nueva", a.nueva)):
            cache.setdefault((k, to), chunks(d, to))
        b, p, n = (cache[(k, to)].get(f["id"]) for k in ("s1ter", "s06a", "nueva"))
        if p is None and n is None:
            estado = "sigue"     # el id ya no estaba en la primera corrida y tampoco está ahora
        elif igual(n, p):
            estado = "sigue"
        elif igual(n, b):
            estado = "vuelve_a_S1ter"
        else:
            estado = "otro"
        campos_vs_s1ter = ["id"] if n is None else [k for k in CAMPOS if b is None or n.get(k) != b.get(k)]
        acepta = (estado != "sigue") if f["veredicto"] == "empeora" else \
            (estado == "sigue") if f["veredicto"] == "mejora" else True
        out.append({**f, "estado": estado, "campos_vs_S1ter": campos_vs_s1ter,
                    "aceptacion": "ok" if acepta else ("a_juzgar" if estado == "otro" else "falla")})
    res = {"filas": len(out),
           "por_veredicto_y_estado": {v: {e: sum(1 for x in out if x["veredicto"] == v and x["estado"] == e)
                                          for e in ("sigue", "vuelve_a_S1ter", "otro")}
                                      for v in ("mejora", "neutro", "empeora")},
           "aceptacion": {k: sum(1 for x in out if x["aceptacion"] == k) for k in ("ok", "a_juzgar", "falla")},
           "unidades": out}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "unidades"}, ensure_ascii=False, indent=1))
    for x in out:
        if x["aceptacion"] != "ok":
            print(x["aceptacion"], x["grupo"], x["veredicto"], x["estado"], x["id"], x["campos_vs_S1ter"])


if __name__ == "__main__":
    main()
