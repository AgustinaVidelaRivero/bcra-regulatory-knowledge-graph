"""Rol documental de cada chunk: cuerpo | indice | tabla_norma_origen.

Motivación (auditoría del re-ensamblado v3): los TOs del BCRA repiten la misma
numeración de punto en tres regiones distintas del PDF — el índice del
principio, el articulado, y la tabla "norma de origen" del final. El chunker
corta en cada aparición, así que `{doc}::{numbering}` NO identifica un pasaje:
identifica hasta tres. Sin un discriminador documental, cualquier desempate
posterior es una heurística ciega (y la que estaba en uso —"gana el que más
entidades extrajo"— premia sistemáticamente a la tabla de referencias
cruzadas, que es una lista de códigos de Comunicación, por encima del
articulado, que es prosa normativa).

Este módulo aporta el discriminador por evidencia del propio documento: la
página de la que sale cada chunk. Las páginas del índice llevan el pie
"-Índice -"; las de la tabla de correspondencias llevan el encabezado
"NORMA DE ORIGEN". El resto es articulado.

No re-chunkea ni altera el texto: reproduce la segmentación de `chunker.py`
llevando el offset de cada chunk, y verifica contra el chunks_all.json ya
existente que la reproducción es idéntica. Si no lo fuera, falla ruidosamente
en vez de devolver roles mal atribuidos.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

import chunker as CH


ROL_CUERPO = "cuerpo"
ROL_INDICE = "indice"
ROL_TABLA = "tabla_norma_origen"

PIE_INDICE = re.compile(r"^\s*-\s*[ÍI]ndice\s*-\s*$", re.MULTILINE | re.IGNORECASE)
ENCABEZADO_TABLA = "NORMA DE ORIGEN"


@dataclass
class PaginaRol:
    inicio: int      # offset del primer char de la página en el texto completo
    fin: int         # offset exclusivo
    rol: str


def roles_de_pagina(pdf_path: Path) -> list[PaginaRol]:
    """Clasifica cada página y devuelve sus rangos de offset en el texto que
    arma `chunker._extract_text` (páginas unidas por '\\n')."""
    paginas: list[PaginaRol] = []
    offset = 0
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if ENCABEZADO_TABLA in t.upper():
                rol = ROL_TABLA
            elif PIE_INDICE.search(t):
                rol = ROL_INDICE
            else:
                rol = ROL_CUERPO
            paginas.append(PaginaRol(inicio=offset, fin=offset + len(t), rol=rol))
            offset += len(t) + 1  # el '\n' de join entre páginas
    return paginas


def _rol_en_offset(paginas: list[PaginaRol], offset: int) -> str:
    for p in paginas:
        if p.inicio <= offset < p.fin:
            return p.rol
    return ROL_CUERPO  # offset en un separador entre páginas: irrelevante


def roles_por_chunk(pdf_path: Path) -> dict[tuple[str, str], str]:
    """Reproduce la segmentación de chunker.chunk_pdf llevando el offset de
    origen, y devuelve {(chunk_id, text): rol}.

    La clave incluye el texto porque `chunk_id` colisiona por diseño: es
    exactamente el problema que este módulo resuelve.
    """
    doc = pdf_path.name
    text = CH._extract_text(pdf_path)
    paginas = roles_de_pagina(pdf_path)
    cuts = CH._find_cut_points(text)

    # Chunks base, con su offset de inicio (mismo recorrido que chunk_pdf).
    base: list[tuple[str, str, int]] = []  # (chunk_id, text, offset)
    if cuts and cuts[0][0] > 0:
        preamble = text[: cuts[0][0]].strip()
        if preamble and len(preamble) >= CH.MIN_CHUNK_CHARS:
            base.append((f"{doc}::preamble", preamble, 0))
    for i, (start, numbering, _title) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        base.append((f"{doc}::{numbering}", body, start))

    # Coalescing de chunks chicos (conserva id y offset del primero).
    merged: list[tuple[str, str, int]] = []
    buf: tuple[str, str, int] | None = None
    for c in base:
        if buf is None:
            buf = c
            continue
        if len(buf[1]) < CH.MIN_CHUNK_CHARS:
            buf = (buf[0], buf[1] + "\n\n" + c[1], buf[2])
        else:
            merged.append(buf)
            buf = c
    if buf is not None:
        merged.append(buf)

    # Split de oversized: los sub-chunks heredan el offset del padre.
    salida: dict[tuple[str, str], str] = {}
    for cid, txt, off in merged:
        rol = _rol_en_offset(paginas, off)
        if len(txt) <= CH.HARD_CAP_CHARS:
            salida[(cid, txt)] = rol
            continue
        padre = CH.Chunk(chunk_id=cid, doc=doc, location="", text=txt, char_count=len(txt))
        for sub in CH._split_oversized(padre):
            salida[(sub.chunk_id, sub.text)] = rol
    return salida


def clave_chunk(chunk_id: str, text: str) -> str:
    return f"{chunk_id}|{hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]}"


def roles_para_chunks_all(chunks_all: list[dict], subset_dir: Path) -> dict[str, str]:
    """Asigna rol a cada entrada de chunks_all.json → {clave_chunk: rol}.

    Lanza RuntimeError si algún chunk del archivo no se reproduce — señal de que
    la segmentación cambió y los roles no serían atribuibles.
    """
    por_doc: dict[str, dict[tuple[str, str], str]] = {}
    out: dict[str, str] = {}
    faltantes: list[str] = []
    for c in chunks_all:
        doc = c["doc"]
        if doc not in por_doc:
            por_doc[doc] = roles_por_chunk(subset_dir / doc)
        rol = por_doc[doc].get((c["chunk_id"], c["text"]))
        if rol is None:
            faltantes.append(f"{c['chunk_id']} ({c['char_count']} chars)")
            continue
        out[clave_chunk(c["chunk_id"], c["text"])] = rol
    if faltantes:
        raise RuntimeError(
            f"{len(faltantes)} chunks de chunks_all.json no se reprodujeron; "
            f"la segmentación cambió. Primeros: {faltantes[:5]}"
        )
    return out


if __name__ == "__main__":
    from collections import Counter

    chunks_all = json.loads(
        (CH.RUN_DIR / "code" / "cache_v2" / "chunks_all.json").read_text(encoding="utf-8")
    )
    roles = roles_para_chunks_all(chunks_all, CH.SUBSET)
    print(f"chunks clasificados: {len(roles)} de {len(chunks_all)}")
    print(Counter(roles.values()))
    por_doc: dict[str, Counter] = {}
    for c in chunks_all:
        por_doc.setdefault(c["doc"], Counter())[roles[clave_chunk(c["chunk_id"], c["text"])]] += 1
    for d, cnt in sorted(por_doc.items()):
        print(f"  {d:<58} {dict(cnt)}")
