"""Detector del hallazgo 1.16, corregido (U-SEG-OFICIAL, S0-5a, §2.6 del mandato; USD 0, solo lectura de la salida).

Uso: python -B detector_116.py --e0 <salida de E0> --out <json> [--tos a,b,c]

Lo usa S1-ter sobre la salida de S0-5b. Sobre la salida de E0 (`estructura_<to>.json` y `chunks_<to>.json`):
- original (el de S1-bis, `s1bis/scripts/censo_renglones_S1bis.py:57-95`, con el prefijo de sub-documento): una lista
  es un nodo con dos o más puntos hijos, todos hojas, con un chunk por ítem (`<to>::[<prefijo>::]<numero>`); es
  candidata si el último ítem tiene un corte de párrafo (renglón que empieza con mayúscula después de uno que termina
  en «.» o «:») y ninguno de los anteriores lo tiene;
- corrección (i): el renglón del título del ítem (el primero, si empieza con su número) cuenta como párrafo propio: el
  segundo renglón abre párrafo si empieza con mayúscula; la lista es candidata si el último ítem tiene más párrafos
  que cualquiera de los anteriores;
- corrección (ii): también se recorren como lista las secciones sin puntos consecutivas cuyo texto empieza con «N.»,
  con N consecutivos (campos numerados leídos como secciones);
- el detector final es la unión del original con la corrección (la corrección sola pierde algún candidato original).
Para cada candidato: id, páginas, padre, criterio (original, corregido o ambos), origen (puntos o secciones), párrafos
del último ítem y máximo de los anteriores, y el primer renglón del último párrafo que no es el primero.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

RE_MAYUS = re.compile(r"^[A-ZÁÉÍÓÚÑ]")
RE_N = re.compile(r"^(\d+)\.\s")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def cortes(texto: str) -> list[int]:
    ls = texto.split("\n")
    return [i for i in range(1, len(ls)) if RE_MAYUS.match(ls[i].strip()) and ls[i - 1].rstrip().endswith((".", ":"))]


def inicios(texto: str, numero: str | None) -> list[int]:
    ls = texto.split("\n")
    titulo = bool(numero) and ls[0].strip().startswith(str(numero))
    return [0] + [i for i in range(1, len(ls)) if RE_MAYUS.match(ls[i].strip())
                  and (ls[i - 1].rstrip().endswith((".", ":")) or (i == 1 and titulo))]


def casos_to(e0: Path, to: str) -> list[dict]:
    est = jl(e0 / f"estructura_{to}.json")
    lista_chunks = jl(e0 / f"chunks_{to}.json")
    ch = {c["id"]: c for c in lista_chunks}
    out: list[dict] = []

    def evaluar(ids: list[str], nums: list[str], padre, pref, origen: str) -> None:
        textos = [ch.get(i) for i in ids]
        if not all(textos):
            return
        ult = textos[-1]
        orig = origen == "puntos" and bool(cortes(ult["texto"])) and not any(cortes(t["texto"]) for t in textos[:-1])
        pu = inicios(ult["texto"], nums[-1])
        pa = max(len(inicios(t["texto"], n)) for t, n in zip(textos[:-1], nums[:-1]))
        corr = len(pu) > pa
        if orig or corr:
            ls = ult["texto"].split("\n")
            out.append({"id": ult["id"], "paginas": ult["paginas"], "padre": padre, "prefijo": pref,
                        "origen": origen, "criterio": "ambos" if orig and corr else "original" if orig else "corregido",
                        "items": len(ids), "parrafos_ultimo": len(pu), "parrafos_max_anteriores": pa,
                        "cierre_candidato": ls[pu[1]] if len(pu) > 1 else (ls[cortes(ult["texto"])[0]]
                                                                           if cortes(ult["texto"]) else "")})

    def visitar(nodo: dict, pref) -> None:
        hijos = [h for h in nodo.get("hijos", []) if h.get("tipo") == "punto"]
        if len(hijos) >= 2 and all(not h.get("hijos") for h in hijos):
            ids = [f"{to}::{pref}::{h['numero']}" if pref else f"{to}::{h['numero']}" for h in hijos]
            evaluar(ids, [h["numero"] for h in hijos], nodo.get("numero"), pref, "puntos")
        for h in nodo.get("hijos", []):
            visitar(h, pref)

    for s in est["secciones"]:
        visitar(s, s.get("prefijo"))
    secs = [c for c in lista_chunks if c.get("tipo") == "seccion_sin_puntos" and RE_N.match(c["texto"])]
    corrida: list[dict] = []
    for c in secs + [None]:
        if c is not None and (not corrida or int(RE_N.match(c["texto"]).group(1))
                              == int(RE_N.match(corrida[-1]["texto"]).group(1)) + 1):
            corrida.append(c)
            continue
        if len(corrida) >= 2:
            evaluar([x["id"] for x in corrida], [RE_N.match(x["texto"]).group(1) for x in corrida], "secciones",
                    None, "secciones")
        corrida = [c] if c is not None else []
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tos", default=None)
    a = ap.parse_args()
    tos = sorted(p.name[len("estructura_"):-5] for p in a.e0.glob("estructura_*.json"))
    if a.tos:
        tos = [t for t in tos if t in a.tos.split(",")]
    todos: list[dict] = []
    for to in tos:
        todos += casos_to(a.e0, to)
    orig = [c for c in todos if c["criterio"] in ("original", "ambos")]
    corr = [c for c in todos if c["criterio"] in ("corregido", "ambos")]
    res = {"tos_revisados": len(tos),
           "original": len(orig), "corregido": len(corr), "union": len(todos),
           "solo_original": len([c for c in todos if c["criterio"] == "original"]),
           "por_origen": dict(collections.Counter(c["origen"] for c in todos)),
           "tos": len({c["id"].split("::")[0] for c in todos}),
           "candidatos": todos}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "candidatos"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
