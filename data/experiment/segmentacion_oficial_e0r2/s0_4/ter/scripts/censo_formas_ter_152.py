"""S0-4a-ter (U-SEG-OFICIAL), USD 0, solo lectura: dónde actuarían las formas nuevas fuera de sus listas, en los 152.
Por TO, con los roles de página de una corrida de E0 (`pies_<to>.json`) y el código de la raíz dada:
- forma de letra (sdl): los límites de letra de `limites_subdocumento(letras=True)` (con la guarda de mayúsculas y la
  serie desde la A), y los rótulos «<letra>. <título>» que la guarda de mayúsculas deja afuera;
- régimen de la página 1 (sdr1): si hay un régimen en la página 1 (lo que la guarda dejaría sin abrir);
- apartados de letra (apl): los renglones «APARTADO X: …» de las páginas de cuerpo (la regla pide al menos
  MIN_APARTADOS_R4).
Uso: python -B censo_formas_ter_152.py --codigo <raíz> --corrida <dir E0> --salida <json> [--workers 3]"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
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
    con_l = E0.limites_subdocumento(paginas, roles, letras=True)
    letras = [{"pagina": d["pagina"], "prefijo": d["prefijo"], "titulo": d["titulo"]} for d in con_l
              if d["forma"] == "letra"]
    sin_mayus = []
    for pi, (ls, rol) in enumerate(zip(paginas, roles), start=1):
        if rol != E0.ROL_CUERPO:
            continue
        for l in ls:
            m = E0.RE_LETRA_SD.match(l.texto.strip())
            if m and not E0._es_titulo_mayusculas(m.group("t")) and m.group("t")[:1].isupper():
                sin_mayus.append(pi)
    sin = E0.limites_subdocumento(paginas, roles)
    reg_p1 = [d["prefijo"] for d in sin if d["forma"] == "regimen" and d["pagina"] == 1]
    apart = sum(1 for ls, rol in zip(paginas, roles) if rol == E0.ROL_CUERPO
                for l in ls if E0.RE_APARTADO_R2.match(l.texto.strip()))
    return to, {"letra": letras, "letra_mayuscula_inicial_sin_guarda": len(sin_mayus), "regimen_pagina_1": reg_p1,
                "apartados": apart}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", required=True)
    ap.add_argument("--corrida", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    raiz = str(Path(a.codigo).resolve())
    tos = sorted(p.name[len("pies_"):-5] for p in Path(a.corrida).glob("pies_*.json"))
    with ProcessPoolExecutor(a.workers, initializer=_iniciar, initargs=(raiz,)) as ex:
        res = dict(ex.map(uno, [(raiz, a.corrida, t) for t in tos]))
    out = OrderedDict([
        ("criterio", __doc__.split("Uso:")[0].strip()),
        ("tos", len(res)),
        ("letra_tos", OrderedDict((t, r["letra"]) for t, r in res.items() if r.get("letra"))),
        ("letra_mayuscula_inicial_sin_guarda_tos", OrderedDict((t, r["letra_mayuscula_inicial_sin_guarda"])
                                                               for t, r in res.items()
                                                               if r.get("letra_mayuscula_inicial_sin_guarda"))),
        ("regimen_pagina_1_tos", OrderedDict((t, r["regimen_pagina_1"]) for t, r in res.items()
                                             if r.get("regimen_pagina_1"))),
        ("apartados_tos", OrderedDict((t, r["apartados"]) for t, r in res.items() if r.get("apartados"))),
        ("errores", OrderedDict((t, r["error"]) for t, r in res.items() if "error" in r)),
    ])
    Path(a.salida).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, dict) else v) for k, v in out.items() if k != "criterio"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
