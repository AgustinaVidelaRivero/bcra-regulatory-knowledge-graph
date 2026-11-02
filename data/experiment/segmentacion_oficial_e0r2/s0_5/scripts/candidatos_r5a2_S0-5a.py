"""Candidatos de R5-a′ (título de bloque) fuera de ri_oc (U-SEG-OFICIAL, S0-5a; USD 0, solo lectura de la salida).

Uso: python -B candidatos_r5a2_S0-5a.py --e0 <salida de E0 con las reglas apagadas> --out <json>

S0-5a no aplica R5-a′ fuera de ri_oc: lista los candidatos, con su página, para la lectura y la decisión de la autora
(qué entra por lista en S0-5b). Criterio: en el último ítem de una lista del detector del 1.16 (`detector_116.py`,
unión), el primer renglón desde el segundo párrafo con la forma de título de bloque de la regla
(`e0_lib._es_titulo_bloque`, sobre el texto de la salida): MAX_CHARS caracteres o menos, mayúscula inicial, sin
puntuación final («.», «,», «;», «:»), que no es un número de punto ni un renglón de tabla serializada, y al que sigue
más texto en el ítem. `abre_parrafo` dice si el renglón abre un párrafo (es lo que mira la regla de ri_oc); los que no
lo abren se listan igual, porque la heurística de la mesa (27, no versionada) miraba cualquier renglón. De cada uno:
el ítem, la página, el renglón, los dos que siguen, si el padre es una sección (la regla abriría una sección nueva) o
un punto (la regla, como está, no aplica), y el cierre del padre.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import detector_116 as D  # noqa: E402

MAX_CHARS = 60
RE_NUM = re.compile(r"^(?:\d+|[A-Z])(?:\.\d+)*\.?$")


def es_titulo(t: str) -> bool:
    t = t.strip()
    tok = t.split()[0] if t.split() else ""
    return (0 < len(t) <= MAX_CHARS and bool(D.RE_MAYUS.match(t)) and not t.endswith((".", ",", ";", ":"))
            and not RE_NUM.match(tok) and not t.startswith("[") and "|" not in t)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    tos = sorted(p.name[len("estructura_"):-5] for p in a.e0.glob("estructura_*.json"))
    filas = []
    for to in tos:
        ch = {c["id"]: c for c in D.jl(a.e0 / f"chunks_{to}.json")}
        for c in D.casos_to(a.e0, to):
            if c["origen"] != "puntos":
                continue
            ult = ch[c["id"]]
            ls = ult["texto"].split("\n")
            num = c["id"].split("::")[-1]
            pref = c["prefijo"]
            padre = c["padre"]
            base = f"{to}::{pref}::" if pref else f"{to}::"
            es_seccion = "." not in str(padre)     # el padre de un punto de un componente después de la sección
            id_cierre = f"{base}{padre}::cierre" if "." in str(padre) else f"{base}S{padre}::cierre"
            cierre = ch.get(id_cierre)
            ini = D.inicios(ult["texto"], num)
            for k in (range(ini[1], len(ls)) if len(ini) > 1 else []):
                if es_titulo(ls[k]) and k + 1 < len(ls):
                    filas.append({"to": to, "item": c["id"], "lista_padre": padre, "padre_es_seccion": es_seccion,
                                  "paginas_item": ult["paginas"], "renglon_en_el_item": k, "abre_parrafo": k in ini,
                                  "renglon": ls[k], "siguen": ls[k + 1:k + 3],
                                  "renglones_que_siguen_en_el_item": len(ls) - k - 1,
                                  "cierre_del_padre": id_cierre if cierre else None,
                                  "cierre_del_padre_inicio": cierre["texto"][:80] if cierre else None,
                                  "ri_oc": to == "ri_oc"})
                    break
    res = {"criterio": "forma de título de bloque (e0_lib._es_titulo_bloque) sobre el texto de la salida, primer "
                       "renglón desde el segundo párrafo del último ítem de las listas del detector del 1.16 (unión)",
           "candidatos": len(filas), "fuera_de_ri_oc": sum(1 for f in filas if not f["ri_oc"]),
           "abren_parrafo": sum(1 for f in filas if f["abre_parrafo"]),
           "tos": len({f["to"] for f in filas}), "filas": filas}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "filas"}, ensure_ascii=False))
    for f in filas:
        print(f"{f['item']} p{f['paginas_item']} sec={f['padre_es_seccion']} | {f['renglon']!r} -> {f['siguen'][:1]}")


if __name__ == "__main__":
    main()
