#!/usr/bin/env python3
"""Agrega al manifiesto del índice de puntos el bloque denso del manifiesto de referencia.

`indice_puntos_union.py`, en una carpeta sin manifiesto previo, escribe el manifiesto sin el bloque
denso, porque ese bloque lo agrega `construir_denso_puntos.py` cuando rehace la matriz. La matriz no
se rehace: se usa la publicada. Este programa comprueba el manifiesto y la matriz, agrega el bloque al
final, con la misma serialización que `construir_denso_puntos.py`, y comprueba el sha256 que piden las
configuraciones N7 y N7c+. Si algo no da, aborta sin escribir.

Uso, desde la raíz del repositorio:
  python3 reconstruccion/completar_manifiesto_puntos.py [--raiz RAIZ]

Solo usa la biblioteca estándar. Solo imprime sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

GRAFO = "KG_Acumulado_Tandas0y1yFinal_r2b_sincola"
CARPETA = f"data/experiment/banco_mcp/mcp_kg/indice_puntos/{GRAFO}"
REFERENCIA = f"data/experiment/banco_mcp/mcp_kg/manifiestos_indice_puntos/{GRAFO}.json"
SHA_SIN_DENSO = "eec47db5436dc78e562b11aad0a284f5d14f08ab83568079e2d93d43313ad9dc"
SHA_COMPLETO = "ef036b67032175f32996513a81198f65ed29850bc336ba35ae445f7f20c152d6"


def sha256_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def abortar(mensaje: str) -> None:
    sys.exit(f"ABORTO: {mensaje}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--raiz", type=Path, default=Path("."), help="raíz del repositorio (por defecto, la carpeta actual)")
    a = ap.parse_args()

    raiz = a.raiz.resolve()
    ruta = raiz / CARPETA / "manifiesto.json"
    previo = ruta.read_bytes()
    if sha256_bytes(previo) != SHA_SIN_DENSO:
        abortar(f"manifiesto.json da {sha256_bytes(previo)}, y se esperaba {SHA_SIN_DENSO}")
    print(f"manifiesto_sin_denso_ok={SHA_SIN_DENSO}")

    bloque = json.loads((raiz / REFERENCIA).read_text(encoding="utf-8"))["denso"]
    matriz = sha256_bytes((raiz / CARPETA / "embeddings_docs.npy").read_bytes())
    if matriz != bloque["sha256_archivo_npy"]:
        abortar(f"embeddings_docs.npy da {matriz}, y se esperaba {bloque['sha256_archivo_npy']}")
    print(f"matriz_ok={matriz}")

    manifiesto = json.loads(previo.decode("utf-8"))
    manifiesto["denso"] = bloque
    completo = json.dumps(manifiesto, ensure_ascii=False, indent=1).encode("utf-8")
    if sha256_bytes(completo) != SHA_COMPLETO:
        abortar(f"el manifiesto completo daría {sha256_bytes(completo)}, y se esperaba {SHA_COMPLETO}")
    ruta.write_bytes(completo)
    if sha256_bytes(ruta.read_bytes()) != SHA_COMPLETO:
        abortar("manifiesto.json dio otro sha256 después de escribirlo")
    print(f"manifiesto_completo_ok={SHA_COMPLETO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
