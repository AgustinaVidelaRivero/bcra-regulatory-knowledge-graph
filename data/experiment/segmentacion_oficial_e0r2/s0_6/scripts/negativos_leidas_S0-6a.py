"""Los negativos del §4 de S0-6a para `selftest_e0` (U-SEG-OFICIAL; USD 0, sin API): las unidades leídas en S1-ter, de los
TOs del selftest, cuyo corte (y, si se juzgó, su herencia) era correcto y la E0 corregida conserva.

Uso: python -B negativos_leidas_S0-6a.py --comun <dir de comun_S1quater.py> --orden <orden_lectura_S1ter.json>
       --base <E0 de S0-5b> --final <E0 corregida> --regla a=<dir> … --tsv <errores_confirmados_S1ter.tsv>
       --tos <to,to,…> --out <json>

Por unidad: su origen (las fichas y preguntas de S1-ter), qué se fija (el corte —mismo id, sha256 propio y páginas— y,
si no cambió, la herencia) con un sha256 corto de esos campos en S0-5b, y las reglas que actúan en su documento (la
configuración de la regla sola cambia alguna unidad del TO): la unidad es un negativo de esas reglas. Solo ids, fichas
y sha256: sin texto.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


def digest(c: dict, campos: tuple) -> str:
    return hashlib.sha256(json.dumps([c[k] for k in campos], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("comun", "orden", "base", "final", "tsv", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    ap.add_argument("--regla", action="append", default=[])
    ap.add_argument("--tos", required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(a.comun))
    import comun_S1quater as Q
    orden = json.loads(Q.leer_sellado(a.orden, Q.SHA_ORDEN_S1TER, "el orden de S1-ter"))
    viejo, nuevo = Q.E0(a.base), Q.E0(a.final)
    leidas = Q.mostradas_S1ter(orden, viejo)
    con_fila = {(f["ficha"], f["pregunta"]) for f in csv.DictReader(a.tsv.open(encoding="utf-8"), delimiter="\t")}
    origen: dict[str, list[str]] = {}
    for f in orden["etapa_1"]["fichas"]:
        origen.setdefault(f["id"], []).append(f"{f['id_opaco']} la_unidad")
    for f in orden["etapa_2"]["fichas"]:
        for c in viejo.partes(f["id"]):
            origen.setdefault(c["id"], []).extend([f"{f['id_opaco']} la_unidad", f"{f['id_opaco']} la_herencia"])
        sig = viejo.siguiente(f["id"])
        if sig is not None:
            origen.setdefault(sig["id"], []).append(f"{f['id_opaco']} la_que_sigue")
    tos = a.tos.split(",")
    reglas = dict(x.split("=", 1) for x in a.regla)
    activas = {}
    for to in tos:
        base = {c["id"]: c for c in viejo.chunks(to)}
        activas[to] = [r for r, d in reglas.items()
                       if {c["id"]: c for c in json.loads((Path(d) / f"chunks_{to}.json").read_text(encoding="utf-8"))} != base]
    out = {}
    for uid in sorted(leidas):
        to = uid.split("::")[0]
        if to not in tos:
            continue
        b = viejo.por_id(uid)
        f = {c["id"]: c for c in nuevo.chunks(to)}.get(uid)
        if f is None:
            continue
        oris = origen[uid]
        con_error = any(tuple(o.split(" ")) in con_fila for o in oris)
        if con_error or any(b[k] != f[k] for k in ("sha256_propio", "paginas")):
            continue     # una fila del TSV, o un corte que cambia (va al FRENO): no es negativo
        campos = ("sha256_propio", "paginas") + (("herencia",) if b["herencia"] == f["herencia"] else ())
        out[uid] = {"origen": oris, "fija": "corte y herencia" if "herencia" in campos else "corte",
                    "sha16_S0-5b": digest(b, campos), "reglas_en_su_documento": activas[to]}
    res = {"tos": tos, "negativos": len(out),
           "por_regla": {r: sum(1 for v in out.values() if r in v["reglas_en_su_documento"]) for r in reglas},
           "solo_corte": sum(1 for v in out.values() if v["fija"] == "corte"), "unidades": out}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "unidades"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
