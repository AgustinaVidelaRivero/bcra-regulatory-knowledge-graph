#!/usr/bin/env python3
"""Corre la E0 de un manifiesto de corpus sin validar los roles del manifiesto.

`correr_e0.py --manifiesto` valida los roles contra el catálogo del perfil, y esa validación
necesita `candado_mensaje_r2b.json`, que no se publica. `correr()` no usa los roles: del manifiesto
toma solo los ids, los archivos, las rutas de los PDF, el mapa y el oráculo. Este programa carga el
manifiesto con `validar_roles=False` y llama a ese mismo `correr()`. El sha256 de cada PDF se sigue
comprobando, y `armar_e0_acumulada.py` controla el resultado: 640 de 640 contra el armado.

Corre con el Python 3.10.13 de `.venv`, el que declara `requirements.txt`. Con Python 3.12 la
E0 da 625 de 640, porque desde esa versión `sum()` suma los floats con compensación.

Uso, desde la raíz del repositorio:
  .venv/bin/python reconstruccion/correr_e0_sin_roles.py MANIFIESTO SALIDA [--raiz RAIZ]

Solo imprime cuántos archivos quedaron en SALIDA.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = "src"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("manifiesto", type=Path, help="ruta del manifiesto de corpus")
    ap.add_argument("salida", type=Path, help="carpeta de salida de la E0")
    ap.add_argument("--raiz", type=Path, default=Path("."), help="raíz del repositorio (por defecto, la carpeta actual)")
    a = ap.parse_args()

    carpeta = a.raiz.resolve() / SRC
    sys.path[:0] = [str(carpeta / "comun"), str(carpeta / "segmentacion")]
    import correr_e0
    import manifiesto_corpus

    manifiesto = manifiesto_corpus.cargar(a.manifiesto, validar_roles=False)
    correr_e0.correr(a.salida, manifiesto=manifiesto, version_e0=correr_e0.VERSION_E0_R2)
    print(f"archivos_en_la_salida={sum(1 for p in a.salida.iterdir() if p.is_file())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
