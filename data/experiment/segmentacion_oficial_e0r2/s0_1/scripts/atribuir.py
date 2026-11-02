"""Atribución de los cambios de E0 a las reglas de S0 (USD 0). Compara la corrida con todas las reglas contra la
base y contra la corrida de cada regla sola: cada evento (id nuevo, id que desaparece, chunk que cambia) de la
combinada se atribuye a las reglas cuya corrida sola produce el mismo evento; si ninguna lo produce sola, es
«interaccion» (efecto de dos reglas juntas) y se lista para leer.

Uso: python -B atribuir.py --base <dir> --todas <dir> --regla r1=<dir>[,<dir>] ... [--resta T=<dir>[,<dir>]] --out <json>
Una regla puede leer de varias carpetas (la primera que tenga el TO). Con --resta, los eventos de la corrida con
todas las reglas que no están en la corrida sin esa regla (la carpeta dada) se atribuyen además a ella: sirve
para el acompañamiento, que no actúa solo.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_e0 as CMP  # noqa: E402


def leer(dirs, to):
    for d in (dirs if isinstance(dirs, list) else [dirs]):
        if (d / f"chunks_{to}.json").exists():
            return CMP.leer_chunks(d, to)
    raise SystemExit(f"sin chunks de {to} en {dirs}")


def eventos(base: Path, nueva, tos: list[str]) -> dict[str, set]:
    out = {}
    for to in tos:
        r = CMP.comparar_to(CMP.leer_chunks(base, to), leer(nueva, to))
        ev = {("nuevo", i) for i in r["ids_nuevos"]} | {("desaparece", i) for i in r["ids_que_desaparecen"]} \
            | {("cambia", i) for i in r["cambian"]}
        if not r["orden_igual_en_comunes"]:
            ev.add(("orden", to))
        out[to] = ev
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--todas", type=Path, required=True)
    ap.add_argument("--regla", action="append", default=[])
    ap.add_argument("--resta", action="append", default=[])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    reglas = OrderedDict((x.split("=", 1)[0], [Path(p) for p in x.split("=", 1)[1].split(",")]) for x in a.regla)
    restas = OrderedDict((x.split("=", 1)[0], [Path(p) for p in x.split("=", 1)[1].split(",")]) for x in a.resta)
    tos = sorted({p.name[len("chunks_"):-len(".json")] for p in a.todas.glob("chunks_*.json")})
    ev_todas = eventos(a.base, a.todas, tos)
    tos_cambio = [t for t in tos if ev_todas[t]]
    ev_regla = {r: eventos(a.base, d, tos_cambio) for r, d in reglas.items()}
    ev_sin = {r: eventos(a.base, d, tos_cambio) for r, d in restas.items()}
    por_to = OrderedDict()
    resumen_reglas = Counter()
    for to in tos_cambio:
        filas = Counter()
        detalle = []
        for e in sorted(ev_todas[to]):
            rs = [r for r in reglas if e in ev_regla[r].get(to, set())] + \
                 [r for r in restas if e not in ev_sin[r].get(to, set())]
            clave = "+".join(rs) if rs else "interaccion"
            filas[(e[0], clave)] += 1
            if not rs:
                detalle.append(list(e))
        reglas_to = sorted({k for (_, k) in filas})
        for k in reglas_to:
            resumen_reglas[k] += 1
        # eventos que una regla sola produce y la combinada no (otra regla los neutraliza)
        neutralizados = {r: sorted(list(e) for e in ev_regla[r].get(to, set()) - ev_todas[to]) for r in reglas
                         if ev_regla[r].get(to, set()) - ev_todas[to]}
        por_to[to] = OrderedDict([
            ("reglas", reglas_to),
            ("eventos", {f"{t}|{k}": n for (t, k), n in sorted(filas.items())}),
            ("interaccion", detalle),
            ("neutralizados_en_la_combinada", neutralizados)])
    out = OrderedDict([
        ("tos_que_cambian", len(tos_cambio)),
        ("tos_por_regla", {r: sorted(t for t in tos_cambio if any(r in k.split("+") for k in por_to[t]["reglas"]))
                           for r in list(reglas) + list(restas) + ["interaccion"]}),
        ("por_to", por_to)])
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"tos_que_cambian": out["tos_que_cambian"],
                      "tos_por_regla": {r: len(v) for r, v in out["tos_por_regla"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
