"""Censo de la regla de sub-documento de S0-4 en los 152 TOs (USD 0, sin API, solo lectura): corre
`e0_lib.limites_subdocumento` sobre cada TO, con los roles de página de una corrida de E0 (`pies_<to>.json`), y lista
los límites que la regla abriría, por forma, también en los TOs donde no corre (la lista de TOs es
correr_e0.TOS_SUBDOCUMENTO_S0_4). Cruza con las raíces rechazadas por la guarda de columna (G3) que suceden a la
anterior (s0_3/censos/g3_raices_sucesoras_rechazadas.json).

Uso: python -B censo_sd_152.py --codigo <raíz con el código> --corrida <dir E0> --g3 <json> --salida <json> [--workers 6]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

E0 = None


def _iniciar(raiz: str) -> None:
    global E0
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(raiz) / "data/experiment/reextraccion_v2/e0_chunking"))
    import e0_lib  # noqa: PLC0415
    E0 = e0_lib


def uno(args):
    raiz, corrida, to = args
    pies = json.loads((Path(corrida) / f"pies_{to}.json").read_text(encoding="utf-8"))
    roles = [f["rol"] for f in sorted(pies["paginas_detalle"], key=lambda f: f["pagina"])]
    paginas = E0.extraer_lineas(Path(raiz) / "data/experiment/escalado_prep/pdfs" / f"{to}.pdf")
    if len(roles) != len(paginas):
        return to, {"error": f"{len(roles)} roles y {len(paginas)} páginas"}
    return to, E0.limites_subdocumento(paginas, roles)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", required=True)
    ap.add_argument("--corrida", required=True)
    ap.add_argument("--g3", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    raiz = str(Path(a.codigo).resolve())
    sys.path.insert(0, str(Path(raiz) / "data/experiment/reextraccion_v2/e0_chunking"))
    sys.dont_write_bytecode = True
    import correr_e0 as CE  # noqa: PLC0415
    lista = CE.TOS_SUBDOCUMENTO_S0_4
    tos = sorted(p.name[len("pies_"):-5] for p in Path(a.corrida).glob("pies_*.json"))
    with ProcessPoolExecutor(a.workers, initializer=_iniciar, initargs=(raiz,)) as ex:
        res = dict(ex.map(uno, [(raiz, a.corrida, t) for t in tos]))
    g3 = json.loads(Path(a.g3).read_text(encoding="utf-8"))
    g3_tos = Counter(d["to"] for d in g3["detalle"])
    por_to = OrderedDict((t, r) for t, r in res.items() if r)
    fuera = OrderedDict((t, r) for t, r in por_to.items() if t not in lista)
    out = OrderedDict([
        ("criterio", "e0_lib.limites_subdocumento con los roles de página de la corrida dada; la regla corre solo en "
                     "correr_e0.TOS_SUBDOCUMENTO_S0_4"),
        ("tos", len(tos)),
        ("lista", sorted(lista)),
        ("tos_con_limites", len(por_to)),
        ("limites_por_forma_en_la_lista", dict(Counter(d["forma"] for t in lista for d in por_to.get(t, [])))),
        ("limites_por_forma_fuera_de_la_lista", dict(Counter(d["forma"] for r in fuera.values() for d in r))),
        ("tos_fuera_de_la_lista_con_limites", OrderedDict((t, dict(Counter(d["forma"] for d in r)))
                                                          for t, r in fuera.items())),
        ("cruce_g3", OrderedDict((t, {"raices_g3": n, "limites": dict(Counter(d["forma"] for d in por_to.get(t, []))),
                                      "en_la_lista": t in lista}) for t, n in sorted(g3_tos.items()))),
        ("por_to", por_to)])
    Path(a.salida).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    r = dict(out)
    r.pop("por_to")
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
