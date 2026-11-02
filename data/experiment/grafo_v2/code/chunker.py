"""PDF → texto → chunks por punto numerado con MAX_CUT_DEPTH=2.

Estrategia: cortar SOLO en puntos de profundidad ≤ MAX_CUT_DEPTH (típicamente 2,
ej. "1.", "1.2."). Los subpuntos más profundos (1.2.3., 1.2.3.1.) quedan
agrupados dentro del chunk del padre. Resultado: chunks medianos (~2-3K chars)
que preservan contexto suficiente para extracción del LLM.

Aprendizajes Run 2: cortar a cualquier profundidad da chunks demasiado chicos
y dispara el costo de inferencia fuera del presupuesto.

Salida: lista de dicts {chunk_id, doc, location, text, char_count}.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pdfplumber


MAX_CUT_DEPTH = 2
MIN_CHUNK_CHARS = 300       # acumular chunks muy chicos con el siguiente
TARGET_CHUNK_CHARS = 3500   # tope blando — referencia
HARD_CAP_CHARS = 7000       # tope DURO: chunks más grandes se parten para no hit max_tokens


SUBSET = Path(__file__).resolve().parents[3] / "experiment" / "subset"
RUN_DIR = Path(__file__).resolve().parents[1]
CHUNKS_DIR = RUN_DIR / "code" / "cache"
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)


# Patrón: línea que empieza con "N.", "N.N.", "N.N.N." (hasta profundidad arbitraria),
# seguido de espacio y al menos una letra. Se permite hasta 6 niveles para detección;
# el filtro de profundidad se aplica después.
NUMBERED_HEADER = re.compile(r"^(\d+(?:\.\d+){0,5})\.\s+(\S.*)$", re.MULTILINE)


@dataclass
class Chunk:
    chunk_id: str
    doc: str
    location: str
    text: str
    char_count: int


def _extract_text(pdf_path: Path) -> str:
    """Extrae texto plano del PDF (preservando saltos de línea entre páginas)."""
    pages: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            pages.append(t)
    return "\n".join(pages)


def _depth(numbering: str) -> int:
    """Profundidad de un numbering tipo '1.2.3' (sin punto final) → 3."""
    return numbering.count(".") + 1


MAX_ROOT_NUMBER = 30  # secciones BCRA rara vez exceden 30 en el nivel raíz


def _find_cut_points(text: str) -> list[tuple[int, str, str]]:
    """Devuelve lista de (start_index, numbering, header_title) para cada punto
    de profundidad ≤ MAX_CUT_DEPTH y número raíz ≤ MAX_ROOT_NUMBER.

    NO dedup por numbering en el chunker. Si el mismo numbering aparece varias
    veces (referencias cruzadas, citas), cada match genera un chunk distinto.
    La dedup posterior se hace en el assembler eligiendo el chunk con mejor
    extracción para cada chunk_id.

    El filtro de root ≤ MAX_ROOT_NUMBER evita capturar números altos como
    "6664. ..." que son citas de Comunicaciones, no headers de sección.
    """
    cuts: list[tuple[int, str, str]] = []
    for m in NUMBERED_HEADER.finditer(text):
        numbering = m.group(1)
        title = m.group(2).strip()
        if _depth(numbering) > MAX_CUT_DEPTH:
            continue
        try:
            root = int(numbering.split(".")[0])
        except ValueError:
            continue
        if root > MAX_ROOT_NUMBER:
            continue
        cuts.append((m.start(), numbering, title))
    return cuts


def chunk_pdf(pdf_path: Path) -> list[Chunk]:
    """Chunkea un PDF en una lista de Chunks numerados."""
    doc = pdf_path.name
    text = _extract_text(pdf_path)

    cuts = _find_cut_points(text)
    chunks: list[Chunk] = []

    if not cuts:
        # PDF sin numeración detectable: un único chunk.
        text_clean = text.strip()
        if text_clean:
            chunks.append(Chunk(
                chunk_id=f"{doc}::full",
                doc=doc,
                location="full",
                text=text_clean,
                char_count=len(text_clean),
            ))
        return chunks

    # Encabezado preámbulo (antes del primer corte)
    if cuts[0][0] > 0:
        preamble = text[:cuts[0][0]].strip()
        if preamble and len(preamble) >= MIN_CHUNK_CHARS:
            chunks.append(Chunk(
                chunk_id=f"{doc}::preamble",
                doc=doc,
                location="Preámbulo",
                text=preamble,
                char_count=len(preamble),
            ))

    for i, (start, numbering, title) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        location = f"Punto {numbering}. {title[:80]}".strip()
        chunks.append(Chunk(
            chunk_id=f"{doc}::{numbering}",
            doc=doc,
            location=location,
            text=body,
            char_count=len(body),
        ))

    # Coalescer chunks muy chicos (< MIN_CHUNK_CHARS) con el siguiente.
    merged: list[Chunk] = []
    buffer: Chunk | None = None
    for c in chunks:
        if buffer is None:
            buffer = c
            continue
        if buffer.char_count < MIN_CHUNK_CHARS:
            buffer = Chunk(
                chunk_id=buffer.chunk_id,  # conservamos el ID del primero
                doc=buffer.doc,
                location=buffer.location,
                text=buffer.text + "\n\n" + c.text,
                char_count=buffer.char_count + 2 + c.char_count,
            )
        else:
            merged.append(buffer)
            buffer = c
    if buffer is not None:
        merged.append(buffer)

    # Split de oversized chunks (> HARD_CAP_CHARS).
    # Estrategia: partir por sub-puntos numerados internos (depth 3+). Si no
    # hay sub-puntos, partir por párrafos balanceados.
    final: list[Chunk] = []
    for c in merged:
        if c.char_count <= HARD_CAP_CHARS:
            final.append(c)
            continue
        final.extend(_split_oversized(c))
    return final


def _split_oversized(c: Chunk) -> list[Chunk]:
    """Parte un chunk grande en sub-chunks balanceados por párrafos.

    No usa sub-puntos numerados (recursión depth>2) porque explota el count
    de chunks y dispara el costo. Solo paragraph-split simple, que produce
    2-3 sub-chunks por oversize (no 10+).
    """
    return _split_by_paragraphs(c)


def _split_by_paragraphs(c: Chunk) -> list[Chunk]:
    """Parte un chunk en sub-chunks balanceados por párrafos (\\n\\n).
    Si un párrafo individual sigue siendo > HARD_CAP_CHARS, lo parte por
    oraciones, y si eso aún no alcanza, por chars fijos."""
    paragraphs = re.split(r"\n\s*\n", c.text)
    sub_chunks: list[Chunk] = []
    buf_text = ""
    part_idx = 0

    def _emit_buf():
        nonlocal buf_text, part_idx
        if not buf_text:
            return
        if len(buf_text) <= HARD_CAP_CHARS:
            sub_chunks.append(Chunk(
                chunk_id=f"{c.chunk_id}__p{part_idx}",
                doc=c.doc,
                location=f"{c.location} (parte {part_idx + 1})",
                text=buf_text,
                char_count=len(buf_text),
            ))
            part_idx += 1
        else:
            # Fallback: partir el buf por oraciones / chars
            for sub in _split_by_chars(buf_text, HARD_CAP_CHARS):
                sub_chunks.append(Chunk(
                    chunk_id=f"{c.chunk_id}__p{part_idx}",
                    doc=c.doc,
                    location=f"{c.location} (parte {part_idx + 1})",
                    text=sub,
                    char_count=len(sub),
                ))
                part_idx += 1
        buf_text = ""

    for para in paragraphs:
        if not para.strip():
            continue
        candidate = (buf_text + "\n\n" + para) if buf_text else para
        if len(candidate) > HARD_CAP_CHARS and buf_text:
            _emit_buf()
            buf_text = para
        else:
            buf_text = candidate
    _emit_buf()
    return sub_chunks if sub_chunks else [c]


def _split_by_chars(text: str, cap: int) -> list[str]:
    """Último recurso: parte un string por oraciones aprox; si una oración
    supera el cap, parte por chars fijos."""
    sentences = re.split(r"(?<=[\.\!\?])\s+", text)
    out: list[str] = []
    buf = ""
    for s in sentences:
        candidate = (buf + " " + s) if buf else s
        if len(candidate) > cap and buf:
            out.append(buf)
            buf = s
        else:
            buf = candidate
        # Si una oración individual ya supera cap, partir por chars
        while len(buf) > cap:
            out.append(buf[:cap])
            buf = buf[cap:]
    if buf:
        out.append(buf)
    return out


def chunk_all(pdfs: list[Path]) -> list[Chunk]:
    out: list[Chunk] = []
    for p in pdfs:
        out.extend(chunk_pdf(p))
    return out


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in chunks], f, ensure_ascii=False, indent=2)


def load_chunks(path: Path) -> list[Chunk]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Chunk(**r) for r in raw]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        smoke_pdf = SUBSET / "TO_proteccion_usuarios_servicios_financieros_actual.pdf"
        chunks = chunk_pdf(smoke_pdf)
        out = CHUNKS_DIR / "chunks_smoke.json"
        save_chunks(chunks, out)
        print(f"Smoke: {smoke_pdf.name} → {len(chunks)} chunks → {out}")
        total_chars = sum(c.char_count for c in chunks)
        avg = total_chars / max(len(chunks), 1)
        print(f"Total chars: {total_chars:,} | avg/chunk: {avg:,.0f}")
        for c in chunks[:3]:
            print(f"  {c.chunk_id} ({c.char_count}): {c.location[:60]}")
        return_code = 0
    elif len(sys.argv) > 1 and sys.argv[1] == "all":
        pdfs = sorted(SUBSET.glob("*.pdf"))
        chunks = chunk_all(pdfs)
        out = CHUNKS_DIR / "chunks_all.json"
        save_chunks(chunks, out)
        per_doc: dict[str, int] = {}
        for c in chunks:
            per_doc[c.doc] = per_doc.get(c.doc, 0) + 1
        print(f"All: {len(pdfs)} PDFs → {len(chunks)} chunks total → {out}")
        for d, n in sorted(per_doc.items()):
            print(f"  {d}: {n} chunks")
        return_code = 0
    else:
        print("Uso: python chunk.py {smoke|all}")
        return_code = 1
    sys.exit(return_code)
