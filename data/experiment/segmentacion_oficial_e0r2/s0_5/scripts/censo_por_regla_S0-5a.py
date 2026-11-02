"""Censo por regla de S0-5a (U-SEG-OFICIAL; USD 0, sin API): cada regla sola contra todas apagadas, y la atribución de
cada cambio de la configuración final a una regla.

Uso: python -B censo_por_regla_S0-5a.py --base <E0 con todas apagadas> --final <E0 con todas prendidas>
       --regla r5a=<dir> --regla r5a2=<dir> … --out <json>

Por configuración y por TO, sobre `chunks_<to>.json` (unidad por unidad, por id): las unidades creadas, las quitadas y
las cambiadas, con los campos que cambian (texto propio, herencia, páginas, título, banderas, sha256); y los archivos
por TO que difieren byte a byte (chunks, estructura, índice, pies, tablas). Atribución: un evento de la configuración
final (creada, quitada o cambiada, por id) se atribuye a las reglas que, solas, producen el mismo evento sobre la misma
unidad; si la unidad final es igual a la de una regla sola, la atribución es exacta; si ninguna regla sola produce el
evento, o la unidad final no es igual a la de ninguna, es una interacción, y se lista.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

POR_TO = ("chunks", "estructura", "indice", "pies", "tablas")
CAMPOS = ("texto", "herencia", "paginas", "titulo", "flags", "tipo", "rol_bloque", "herencia_recortada")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def tos_de(d: Path) -> list[str]:
    return sorted(p.name[len("chunks_"):-5] for p in d.glob("chunks_*.json"))


def comparar(base: Path, otro: Path, tos: list[str]) -> dict:
    out = {}
    for to in tos:
        difieren = [p for p in POR_TO if (base / f"{p}_{to}.json").exists() and
                    (base / f"{p}_{to}.json").read_bytes() != (otro / f"{p}_{to}.json").read_bytes()]
        if not difieren:
            continue
        a = {c["id"]: c for c in jl(base / f"chunks_{to}.json")}
        b = {c["id"]: c for c in jl(otro / f"chunks_{to}.json")}
        cambiadas = {}
        for i in sorted(set(a) & set(b)):
            if a[i] != b[i]:
                cambiadas[i] = sorted(k for k in set(a[i]) | set(b[i]) if a[i].get(k) != b[i].get(k)
                                      and k not in ("chars_propio", "chars_completo", "sha256_propio", "sha256_completo"))
        out[to] = {"archivos_distintos": difieren, "unidades_antes": len(a), "unidades_despues": len(b),
                   "creadas": sorted(set(b) - set(a)), "quitadas": sorted(set(a) - set(b)),
                   "cambiadas": cambiadas}
    return out


def eventos(comp: dict) -> dict[tuple, str]:
    ev = {}
    for to, r in comp.items():
        for i in r["creadas"]:
            ev[(to, i)] = "creada"
        for i in r["quitadas"]:
            ev[(to, i)] = "quitada"
        for i in r["cambiadas"]:
            ev[(to, i)] = "cambiada"
    return ev


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--final", type=Path, required=True)
    ap.add_argument("--regla", action="append", default=[])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    reglas = dict(x.split("=", 1) for x in a.regla)
    tos = tos_de(a.base)
    por_regla = {r: comparar(a.base, Path(d), tos) for r, d in reglas.items()}
    final = comparar(a.base, a.final, tos)
    ev_final = eventos(final)
    ev_regla = {r: eventos(c) for r, c in por_regla.items()}
    chunks_regla = {}
    atrib, interacciones = {}, []
    for (to, i), tipo in sorted(ev_final.items()):
        quienes = [r for r in reglas if ev_regla[r].get((to, i)) == tipo]
        exacta = []
        if tipo != "quitada":
            fin = {c["id"]: c for c in jl(a.final / f"chunks_{to}.json")}[i]
            for r in quienes:
                k = (r, to)
                if k not in chunks_regla:
                    chunks_regla[k] = {c["id"]: c for c in jl(Path(reglas[r]) / f"chunks_{to}.json")}
                if chunks_regla[k].get(i) == fin:
                    exacta.append(r)
        else:
            exacta = quienes
        atrib[f"{to}|{i}"] = {"evento": tipo, "reglas": quienes, "igual_a_la_regla_sola": exacta}
        if not exacta:
            interacciones.append({"to": to, "id": i, "evento": tipo, "reglas_que_lo_producen_solas": quienes})
    # eventos de reglas solas que no están en la final (una regla deshace lo de otra)
    perdidos = [{"regla": r, "to": to, "id": i, "evento": t} for r, ev in ev_regla.items()
                for (to, i), t in ev.items() if (to, i) not in ev_final]

    def resumen(comp: dict) -> dict:
        return {"tos": sorted(comp), "creadas": sum(len(r["creadas"]) for r in comp.values()),
                "quitadas": sum(len(r["quitadas"]) for r in comp.values()),
                "cambiadas": sum(len(r["cambiadas"]) for r in comp.values()),
                "unidades_antes": sum(r["unidades_antes"] for r in comp.values()),
                "unidades_despues": sum(r["unidades_despues"] for r in comp.values())}

    res = {"base": str(a.base.name), "final": str(a.final.name),
           "por_regla": {r: {"resumen": resumen(c), "por_to": c} for r, c in por_regla.items()},
           "final": {"resumen": resumen(final), "por_to": final},
           "atribucion": atrib,
           "eventos_final": len(ev_final),
           "eventos_por_regla_en_la_final": dict(collections.Counter(r for v in atrib.values()
                                                                     for r in v["igual_a_la_regla_sola"])),
           "interacciones": interacciones,
           "eventos_de_una_regla_sola_que_no_estan_en_la_final": perdidos}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"por_regla": {r: v["resumen"] for r, v in res["por_regla"].items()},
                      "final": res["final"]["resumen"], "eventos_final": len(ev_final),
                      "eventos_por_regla_en_la_final": res["eventos_por_regla_en_la_final"],
                      "interacciones": len(interacciones), "perdidos": len(perdidos)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
