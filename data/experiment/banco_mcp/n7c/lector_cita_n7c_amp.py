#!/usr/bin/env python3
"""lector_cita_n7c_amp.py — N7c+, etapa C2-bis: la línea de la cita que suma ver_punto, leída por el instrumento de la
cita (scripts/ucita2_indicadores_banco.py, sin editarlo). Corre con un Python 3.12 o más nuevo, porque el instrumento no
compila con el 3.10 del .venv del repo (como en n6/analizar_n6.py), y recibe todo por la entrada estándar: ninguna
salida de ver_punto se escribe en disco.

Entrada (JSON por la entrada estándar):
  {"tos": [{"id", "archivo"}], "secciones": {to: [números de sección]}, "casos": [{"clave": "to::unidad", "salida": "..."}]}
Por caso, con el manifiesto que arma el instrumento (armar_manifiesto):
  - lee: la última línea de la salida empieza con «Para citar este punto: » y partir_cita del resto es parseable, con el
    TO y el punto que el mismo instrumento le da a la clave (_clave_a_par y normalizar_punto, como a un ancla
    «to::unidad»);
  - pdf: el documento de la cita está en la forma «PDF» (el nombre del archivo, no el id del TO);
  - fundada: la cita es fiel (_cita_fiel del harness congelado, por importar_harness_y_lector_v1) a alguno de los pares
    que leer_vista_nav lee de la misma salida de ver_punto.
Salida (JSON por la salida estándar): las tres cuentas, el total y las posiciones de los casos que no dan; ninguna
clave, ningún texto.
Uso: <python 3.12> -I -B data/experiment/banco_mcp/n7c/lector_cita_n7c_amp.py < entrada.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "scripts"))

import ucita2_indicadores_banco as UB  # noqa: E402  (sin editar)

PREFIJO = "Para citar este punto: "


def main() -> int:
    if sys.version_info < (3, 12):
        raise SystemExit("ABORTO: el instrumento de citas necesita Python 3.12 o más nuevo")
    e = json.loads(sys.stdin.read())
    cita_fiel, _, _, _ = UB.importar_harness_y_lector_v1()
    man = UB.armar_manifiesto(e["tos"], {to: frozenset(v) for to, v in (e.get("secciones") or {}).items()})
    cuenta = {"casos": 0, "lee": 0, "pdf": 0, "fundada": 0}
    no = {"lee": [], "pdf": [], "fundada": []}
    for i, c in enumerate(e["casos"]):
        cuenta["casos"] += 1
        linea = c["salida"].split("\n")[-1]
        p = UB.partir_cita(linea[len(PREFIJO):], man)
        to, unidad = UB._clave_a_par(c["clave"], man)
        esperado = (to, UB.normalizar_punto(unidad, UB.secciones_del(man, to))[0])
        ok = {"lee": linea.startswith(PREFIJO) and p["parseable"] and (p["to"], p["punto"]) == esperado,
              "pdf": p["forma_doc"] == UB.PDF}
        vistas = UB.claves_vistas(UB.leer_vista_nav("ver_punto", c["salida"], man), man)
        ok["fundada"] = any(cita_fiel(x, vistas) for x in UB.claves_cita(p))
        for clave, v in ok.items():
            cuenta[clave] += v
            if not v:
                no[clave].append(i)
    print(json.dumps({"cuentas": cuenta, "no_dan": no, "instrumento_sha256": UB.sha256_file(Path(UB.__file__))},
                     ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
