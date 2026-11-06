"""Piezas compartidas del job de actualización: rutas, línea base y procedencia.

Vive aparte para que el runner (que toca red) y el adjudicador (que no) usen
exactamente las mismas definiciones de identidad, línea base y procedencia. Si
divergieran, la tabla de deltas compararía peras con manzanas.

SOLO LECTURA sobre todo lo sellado. Ver §0 del diseno.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
UNIDAD = AQUI.parent
EXPERIMENT = UNIDAD.parent
REPO = EXPERIMENT.parent.parent
PREP = EXPERIMENT / "escalado_prep"
MANIF_DEV = EXPERIMENT / "reextraccion_v2" / "manifiestos" / "desarrollo_5tos.json"
MANIF_RAW = REPO / "data" / "raw" / "manifiesto.csv"
CORRIDAS = UNIDAD / "corridas"

CATEGORIAS = [("normativa_general", "textos_ordenados"),
              ("regimen_informativo", "regimenes_informativos")]

# Fechas de adquisición ancladas en artefactos, no inferidas. Ver la fe de
# erratas docs/fe_erratas_fecha_corpus_congelado.md: la fecha que circulaba
# ("marzo de 2026") no tenía respaldo. Estas dos SÍ lo tienen y son distintas
# por corpus, razón por la cual el delta se reporta desglosado.
ADQUISICION = {
    "inventariado_152": {
        "fecha": "2026-08-13",
        "fuente": "commit de alta 111ed19 de data/experiment/escalado_prep/descarga_log.json",
    },
    "desarrollo_5": {
        "fecha": "2026-05-07/2026-05-10",
        "fuente": "campo fecha_descarga de data/raw/manifiesto.csv (categoría TO_actual)",
    },
}


def fechas_desarrollo() -> dict[str, str]:
    """Fecha exacta de descarga por TO del conjunto de desarrollo.

    El rango 2026-05-07/10 de ADQUISICION es el agregado; acá se lee la fecha
    de cada archivo, que es el dato que la tabla necesita por fila.
    """
    dev = json.loads(MANIF_DEV.read_text(encoding="utf-8"))["tos"]
    por_archivo = {t["archivo"]: t["id"] for t in dev}
    fechas: dict[str, str] = {}
    with MANIF_RAW.open(encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            nombre = (fila.get("archivo_local") or "").split("/")[-1]
            if nombre in por_archivo and fila.get("fecha_descarga"):
                fechas[por_archivo[nombre]] = fila["fecha_descarga"][:10]
    return fechas

# Procedencia documental: las dos formas que la fuente imprime en el PDF.
# Cobertura medida sobre los 157 en sonda_procedencia.json (153/157).
RE_PORTADA = re.compile(
    r"[Úú]ltima\s+comunicaci[óo]n\s+incorporada\s*:\s*[\"“”']?\s*([A-Z])\s*"
    r"[\"“”']?\s*(\d{3,5})", re.IGNORECASE)
RE_TEXTO_ORDENADO = re.compile(
    r"[Tt]exto\s+ordenado\s+al\s+(\d{1,2}/\d{1,2}/\d{2,4})")
RE_PIE = re.compile(
    r"Versi[óo]n\s*:\s*(\d+)\s*[ºa°]?\s*\.?\s*COMUNICACI[ÓO]N\s*[\"“”']?\s*"
    r"([A-Z])\s*[\"“”']?\s*(\d{3,5})", re.IGNORECASE)
RE_PORTADA_PRESENTE = re.compile(
    r"[Úú]ltima\s+comunicaci[óo]n\s+incorporada", re.IGNORECASE)
RE_CID = re.compile(r"\(cid:\d+\)")

PAGS_CABECERA = 3
PAGS_MUESTRA = 5


def sha256_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def id_corto(archivo: str) -> str:
    """Misma regla que escalado_prep/code/construir_inventario.py, para que un
    alta nueva reciba un id construido igual que los 152 ya inventariados."""
    stem = archivo.rsplit(".", 1)[0].lower()
    stem = re.sub(r"^t-", "", stem)
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_")


def leer_indice(ruta: Path) -> list[dict]:
    """Entradas del índice con su categoría, deduplicadas por URL.

    La regla de dedup es la del inventario sellado: primera aparición gana. El
    índice publica al menos un archivo en las dos listas.
    """
    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    filas, vistas, duplicadas = [], set(), []
    for categoria, clave in CATEGORIAS:
        for it in crudo.get(clave) or []:
            if it["url"] in vistas:
                duplicadas.append({"url": it["url"], "titulo": it["titulo"],
                                   "categoria": categoria})
                continue
            vistas.add(it["url"])
            filas.append({"id": id_corto(it["archivo"]), "categoria": categoria,
                          "titulo": it["titulo"], "archivo": it["archivo"],
                          "url": it["url"]})
    return filas, duplicadas


def linea_base() -> dict:
    """La línea base, SOLO LECTURA. Una entrada por TO con su huella original.

    Los 152 salen del inventario de escalado; los 5 del conjunto de desarrollo
    salen de su manifiesto, y su URL —que ese manifiesto no trae— se resuelve
    por título exacto contra el índice sellado.

    IDENTIDAD: la clave es SIEMPRE el id derivado del archivo publicado
    (`id_corto`), que es el espacio de identificadores del índice y de los 152.
    El conjunto de desarrollo usa OTRO espacio en su manifiesto y en el grafo
    (`cap`, `cla`, `ext`, `pro`, `ric` en vez de `capmin`, `cladeu`, `excbio`,
    `pusf`, `ri_cm`), y ese identificador viaja en el campo `id_interno`. Sin
    esa distinción, los 5 se clasificarían como cinco altas y cinco bajas
    simultáneas, y el mapeo al grafo —que indexa por `id_interno`— no
    encontraría nada.
    """
    base: dict[str, dict] = {}

    log = json.loads((PREP / "descarga_log.json").read_text(encoding="utf-8"))
    inv = {f["id"]: f for f in csv.DictReader(
        (PREP / "inventario_tos.csv").open(encoding="utf-8"))}
    paginas = {f["id"]: int(f["paginas"]) for f in csv.DictReader(
        (PREP / "inventario_unidades.csv").open(encoding="utf-8"))}
    for ident, reg in log.items():
        base[ident] = {
            "id": ident, "id_interno": ident, "grupo": "inventariado_152",
            "categoria": inv[ident]["categoria"],
            "titulo": inv[ident]["titulo_oficial"],
            "archivo": inv[ident]["archivo_oficial"],
            "url": inv[ident]["url_pdf"],
            "sha256": reg["sha256"], "bytes": reg.get("bytes"),
            "paginas": paginas.get(ident),
            "pdf": PREP / "pdfs" / f"{ident}.pdf",
            "adquisicion": ADQUISICION["inventariado_152"]["fecha"],
        }

    # Los 5: identidad y sha del manifiesto; URL y título del índice sellado.
    idx_filas, _ = leer_indice(PREP / "indice_oficial_raw.json")
    resumen = json.loads((PREP / "inventario_resumen.json").read_text(encoding="utf-8"))
    por_titulo = {f["titulo"]: f for f in idx_filas}
    titulo_de_id = {s["id_interno"]: s["titulo"] for s in resumen["subset_excluido"]}
    ref = json.loads((PREP / "referencia_subset.json").read_text(encoding="utf-8"))
    dev = json.loads(MANIF_DEV.read_text(encoding="utf-8"))["tos"]
    fechas_dev = fechas_desarrollo()
    for to in dev:
        entrada = por_titulo[titulo_de_id[to["id"]]]
        ident = entrada["id"]                     # id del índice, no el del manifiesto
        base[ident] = {
            "id": ident, "id_interno": to["id"], "grupo": "desarrollo_5",
            "categoria": entrada["categoria"],
            "titulo": entrada["titulo"], "archivo": entrada["archivo"],
            "url": entrada["url"],
            "sha256": to["sha256_pdf"], "bytes": int(ref[to["id"]]["bytes"]),
            "paginas": int(ref[to["id"]]["paginas"]),
            "pdf": REPO / to["pdf"],
            "adquisicion": fechas_dev.get(to["id"],
                                          ADQUISICION["desarrollo_5"]["fecha"]),
        }
    return base


def texto_paginas(pdf: Path, indices: list[int] | None = None) -> tuple[int, dict]:
    """(cantidad de páginas, {indice_0based: texto}). Con indices=None lee todas."""
    import pdfplumber
    with pdfplumber.open(str(pdf)) as doc:
        total = len(doc.pages)
        idxs = list(range(total)) if indices is None else [
            i for i in indices if 0 <= i < total]
        return total, {i: (doc.pages[i].extract_text() or "") for i in idxs}


def paginas_de_sondeo(total: int) -> list[int]:
    cab = list(range(min(PAGS_CABECERA, total)))
    if total <= PAGS_CABECERA:
        return cab
    paso = max(1, total // (PAGS_MUESTRA + 1))
    return sorted(set(cab) | {min(total - 1, paso * k)
                              for k in range(1, PAGS_MUESTRA + 1)})


def procedencia(pdf: Path) -> dict:
    """Procedencia documental leída del PDF. No se infiere: si la fuente no la
    imprime o no se extrae, el campo queda en null con su límite declarado."""
    # Se abre el PDF UNA vez y se extraen SOLO las páginas de sondeo: extraer las
    # 2.037 de un régimen informativo para leer ocho sería absurdo sobre 157
    # documentos por corrida.
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf)) as doc:
            idxs = paginas_de_sondeo(len(doc.pages))
            textos = {i: (doc.pages[i].extract_text() or "") for i in idxs}
    except Exception as exc:                      # noqa: BLE001 — se reporta textual
        return {"limite_declarado": f"lectura_fallida: {type(exc).__name__}: {exc}"}

    cabecera = "\n".join(textos[i] for i in sorted(textos) if i < PAGS_CABECERA)
    mp, mt = RE_PORTADA.search(cabecera), RE_TEXTO_ORDENADO.search(cabecera)
    pies = {}
    for i in sorted(textos):
        m = RE_PIE.search(textos[i])
        if m:
            pies[str(i + 1)] = {"version": m.group(1), "letra": m.group(2).upper(),
                                "numero": m.group(3)}

    limite = None
    if not mp and not pies:
        limite = ("portada_presente_pero_digitos_no_extraidos"
                  if RE_PORTADA_PRESENTE.search(cabecera) and RE_CID.search(cabecera)
                  else "el_documento_no_imprime_procedencia")
    elif not mp and RE_PORTADA_PRESENTE.search(cabecera) and RE_CID.search(cabecera):
        limite = "portada_presente_pero_digitos_no_extraidos"

    return {
        "portada_comunicacion": f"{mp.group(1).upper()} {mp.group(2)}" if mp else None,
        "texto_ordenado_al": mt.group(1) if mt else None,
        "pie_comunicaciones": sorted({f"{v['letra']} {v['numero']}"
                                      for v in pies.values()}),
        "pie_por_pagina": pies,
        "limite_declarado": limite,
    }
