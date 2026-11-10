#!/usr/bin/env python3
"""Arma la E0 acumulada de los 128 Textos Ordenados con las 3 salidas de correr_e0.py.

Junta por código todos los valores de 64 caracteres hexadecimales del armado, elige de las 3 salidas
los archivos cuyo sha256 está entre ellos y los copia a la carpeta que nombra el manifiesto publicado
de la E0, comprobando cada sha256. No necesita conocer la estructura del armado.

Después coteja los sha256 de PDF del manifiesto de la E0 acumulada contra los 128 PDF que dejó
`colocar_pdfs.py`, porque ese manifiesto sella los PDF y no los archivos de la E0. Sale con 0 solo si
dan los 640 archivos y los 128 PDF.

Uso, desde la raíz del repositorio:
  python3 reconstruccion/armar_e0_acumulada.py SALIDA_TANDA0 SALIDA_TANDA1 SALIDA_TANDA_FINAL [--raiz RAIZ]

Solo usa la biblioteca estándar. No imprime claves ni valores del armado, solo cuentas y el sha256 de
los PDF que no coinciden. El texto de la E0 no se muestra.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ACUMULADO = "data/experiment/tanda_final/t3/acumulado"
ARMADO = f"{ACUMULADO}/armado_acumulado_128_tf.json"
MANIFIESTO = f"{ACUMULADO}/manifiestos/acumulado_128tos_r2b.json"
DESTINO = f"{ACUMULADO}/e0_acumulado_128_r2b"
MANIFIESTOS_DE_TANDA = (
    "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos_r2b.json",
    "data/experiment/reextraccion_v2/manifiestos/tanda1_20tos_r2b.json",
    "data/experiment/reextraccion_v2/manifiestos/tanda_final_98tos_r2b.json",
)
N_ARCHIVOS = 640
N_PDF = 128
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def valores_hex(valor, salida: set[str]) -> set[str]:
    """Todos los valores de 64 caracteres hexadecimales, a cualquier profundidad."""
    if isinstance(valor, dict):
        for v in valor.values():
            valores_hex(v, salida)
    elif isinstance(valor, list):
        for v in valor:
            valores_hex(v, salida)
    elif isinstance(valor, str) and HEX64.match(valor):
        salida.add(valor)
    return salida


def elegir(salidas: list[Path], del_armado: set[str]) -> dict[str, tuple[Path, str]]:
    """De las 3 salidas, nombre -> (ruta, sha256) de los archivos que el armado sella."""
    elegidos: dict[str, tuple[Path, str]] = {}
    leidos = 0
    for salida in salidas:
        for ruta in sorted(salida.iterdir()):
            if not ruta.is_file():
                continue
            leidos += 1
            sha = sha256_archivo(ruta)
            if sha not in del_armado:
                continue
            if ruta.name in elegidos and elegidos[ruta.name][1] != sha:
                sys.exit(f"ABORTO: {ruta.name} aparece en 2 salidas con otro sha256 y los 2 están en el armado")
            elegidos.setdefault(ruta.name, (ruta, sha))
    print(f"archivos_leidos_de_las_salidas={leidos}")
    return elegidos


def copiar(elegidos: dict[str, tuple[Path, str]], destino: Path) -> dict[str, str]:
    destino.mkdir(parents=True, exist_ok=True)
    sellos: dict[str, str] = {}
    for nombre, (ruta, sha) in sorted(elegidos.items()):
        salida = destino / nombre
        if salida.exists() and sha256_archivo(salida) != sha:
            sys.exit(f"ABORTO: {nombre} ya existe en el destino con otro sha256")
        if not salida.exists():
            shutil.copyfile(ruta, salida)
        if sha256_archivo(salida) != sha:
            sys.exit(f"ABORTO: {nombre} dio otro sha256 después de copiarlo")
        sellos[nombre] = sha
    return sellos


def pdfs_colocados(raiz: Path) -> set[str]:
    """El sha256 de los PDF que están en las rutas que nombran los manifiestos de las 3 tandas."""
    colocados: set[str] = set()
    for manifiesto in MANIFIESTOS_DE_TANDA:
        for to in json.loads((raiz / manifiesto).read_text(encoding="utf-8"))["tos"]:
            ruta = raiz / to["pdf"]
            if ruta.is_file():
                colocados.add(sha256_archivo(ruta))
    return colocados


def comparar_manifiesto(ruta: Path, colocados: set[str]) -> int:
    """Cuántos sha256 de PDF del manifiesto están entre los colocados, y los que no."""
    sellados = {to["sha256_pdf"] for to in json.loads(ruta.read_text(encoding="utf-8"))["tos"]}
    no_coinciden = sorted(sellados - colocados)
    print(f"pdf_colocados={len(colocados)}")
    print(f"manifiesto_pdf_coinciden={len(sellados & colocados)} de {len(sellados)}")
    print(f"manifiesto_pdf_no_coinciden={len(no_coinciden)}")
    for sha in no_coinciden:
        print(f"  no_coincide_sha256={sha}")
    return len(sellados & colocados)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("salidas", type=Path, nargs=3, help="las 3 carpetas de salida de correr_e0.py")
    ap.add_argument("--raiz", type=Path, default=Path("."), help="raíz del repositorio (por defecto, la carpeta actual)")
    a = ap.parse_args()

    raiz = a.raiz.resolve()
    del_armado = valores_hex(json.loads((raiz / ARMADO).read_text(encoding="utf-8")), set())
    print(f"armado_valores_hex={len(del_armado)}")
    elegidos = elegir(a.salidas, del_armado)
    sellos = copiar(elegidos, raiz / DESTINO)
    sin_archivo = len(del_armado - set(sellos.values()))
    print(f"copiados_y_cotejados={len(sellos)} de {N_ARCHIVOS}")
    print(f"valores_del_armado_sin_archivo={sin_archivo}")
    coinciden = comparar_manifiesto(raiz / MANIFIESTO, pdfs_colocados(raiz))
    return 0 if len(sellos) == N_ARCHIVOS and coinciden == N_PDF else 1


if __name__ == "__main__":
    raise SystemExit(main())
