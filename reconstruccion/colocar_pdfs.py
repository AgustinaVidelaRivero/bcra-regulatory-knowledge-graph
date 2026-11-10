#!/usr/bin/env python3
"""Coloca los 128 PDF de la versión usada en las rutas que nombran los manifiestos de corpus.

Recibe el ZIP de los 128 Textos Ordenados y su sha256 esperado. Comprueba el ZIP, lo abre en una
carpeta temporal, comprueba cada PDF contra `corpus/textos_ordenados.csv` y copia cada uno a la
ruta que nombra su manifiesto, comprobando de nuevo su sha256. Si algo no da, aborta.

Uso, desde la raíz del repositorio:
  python3 reconstruccion/colocar_pdfs.py ZIP SHA256_DEL_ZIP [--raiz RAIZ] [--tmp CARPETA]

Solo usa la biblioteca estándar. Solo imprime cuentas y sha256. Lo abierto queda en
CARPETA/textos_ordenados_bcra_128/, que se puede borrar al terminar.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

CSV_CORPUS = "corpus/textos_ordenados.csv"
DESTINO_CORPUS = "grafo_evaluado"
N_PDF = 128
MANIFIESTOS = (
    "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos_r2b.json",
    "data/experiment/reextraccion_v2/manifiestos/tanda1_20tos_r2b.json",
    "data/experiment/reextraccion_v2/manifiestos/tanda_final_98tos_r2b.json",
)
SUBCARPETA = "textos_ordenados_bcra_128"


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def abortar(mensaje: str) -> None:
    sys.exit(f"ABORTO: {mensaje}")


def leer_csv(raiz: Path) -> dict[str, str]:
    """Del CSV del corpus, id -> sha256 de las filas del grafo evaluado."""
    with open(raiz / CSV_CORPUS, newline="", encoding="utf-8") as f:
        filas = [fila for fila in csv.DictReader(f) if fila["destino"] == DESTINO_CORPUS]
    esperados = {fila["id"]: fila["sha256"].strip().lower() for fila in filas}
    if len(filas) != N_PDF or len(esperados) != N_PDF:
        abortar(f"{CSV_CORPUS} trae {len(filas)} filas de {DESTINO_CORPUS}, y se esperan {N_PDF}")
    return esperados


def leer_rutas(raiz: Path) -> dict[str, str]:
    """De los manifiestos de corpus, sha256 del PDF -> ruta del PDF relativa a la raíz.

    La unión con el CSV es por sha256 porque 5 Textos Ordenados llevan otro id en los manifiestos.
    """
    rutas: dict[str, str] = {}
    for manifiesto in MANIFIESTOS:
        datos = json.loads((raiz / manifiesto).read_text(encoding="utf-8"))
        for to in datos["tos"]:
            sha = to["sha256_pdf"].strip().lower()
            if sha in rutas:
                abortar(f"sha256 repetido entre los manifiestos: {sha}")
            rutas[sha] = to["pdf"]
    return rutas


def abrir_zip(ruta_zip: Path, carpeta: Path, esperados: dict[str, str]) -> None:
    """Abre solo los nombres esperados y comprueba cada uno contra el CSV."""
    nombres_esperados = {f"{id_}.pdf" for id_ in esperados}
    with zipfile.ZipFile(ruta_zip) as zf:
        nombres = zf.namelist()
        if len(nombres) != N_PDF or set(nombres) != nombres_esperados:
            abortar(f"el ZIP trae {len(nombres)} entradas, que no son los {N_PDF} PDF del CSV")
        carpeta.mkdir(parents=True)
        for nombre in nombres:
            with zf.open(nombre) as origen, open(carpeta / nombre, "wb") as destino:
                shutil.copyfileobj(origen, destino)
    coinciden = 0
    for id_, sha in esperados.items():
        if sha256_archivo(carpeta / f"{id_}.pdf") != sha:
            abortar(f"{id_}.pdf no coincide con {CSV_CORPUS}")
        coinciden += 1
    print(f"contra_el_csv={coinciden} de {N_PDF}")


def colocar(raiz: Path, carpeta: Path, esperados: dict[str, str], rutas: dict[str, str]) -> None:
    copiados = ya_estaban = 0
    for id_, sha in esperados.items():
        destino = raiz / rutas[sha]
        if destino.exists():
            if sha256_archivo(destino) != sha:
                abortar(f"{rutas[sha]} ya existe con otro sha256")
            ya_estaban += 1
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(carpeta / f"{id_}.pdf", destino)
        if sha256_archivo(destino) != sha:
            abortar(f"{rutas[sha]} dio otro sha256 después de copiarlo")
        copiados += 1
    print(f"copiados={copiados} ya_estaban={ya_estaban}")
    print(f"en_su_lugar={copiados + ya_estaban} de {N_PDF}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("zip", type=Path, help="ruta del ZIP de los 128 PDF")
    ap.add_argument("sha256", help="sha256 esperado del ZIP")
    ap.add_argument("--raiz", type=Path, default=Path("."), help="raíz del repositorio (por defecto, la carpeta actual)")
    ap.add_argument("--tmp", type=Path, default=None, help="dónde abrir el ZIP (por defecto, la carpeta temporal del sistema)")
    a = ap.parse_args()

    raiz = a.raiz.resolve()
    if not (raiz / CSV_CORPUS).is_file():
        abortar(f"no encuentro {CSV_CORPUS} en la raíz indicada")
    obtenido = sha256_archivo(a.zip)
    if obtenido != a.sha256.strip().lower():
        abortar(f"el sha256 del ZIP es {obtenido}, y se esperaba {a.sha256}")
    print(f"zip_sha256_ok={obtenido}")

    esperados = leer_csv(raiz)
    rutas = leer_rutas(raiz)
    if set(rutas) != set(esperados.values()):
        abortar(f"los manifiestos sellan {len(rutas)} PDF, que no son los {N_PDF} del CSV")
    carpeta = (a.tmp or Path(tempfile.gettempdir())).resolve() / SUBCARPETA
    if carpeta.exists():
        abortar(f"ya existe {SUBCARPETA} en la carpeta temporal")
    abrir_zip(a.zip, carpeta, esperados)
    colocar(raiz, carpeta, esperados, rutas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
