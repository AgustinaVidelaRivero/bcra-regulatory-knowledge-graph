"""
comun_e1.py — Paths, carga de la salida de E0 y wiring de imports para E1
(extractor por chunk del pipeline de re-extracción v2, fase A offline).

Insumos SOLO LECTURA:
  - data/experiment/reextraccion_v2/e0_chunking/salida/chunks_{to}.json
  - data/experiment/grafo_v2/code/schema.py  (esquema v2 vigente: 6 entity
    types + 12 predicados + matriz DOMAIN_RANGE + catálogo de sujetos v2.0)
  - data/experiment/evaluacion/llm_cache.py  (capa never-pay-twice; se
    envuelve, jamás se edita)

Nada de este módulo llama a ninguna API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent                 # e1_extractor/
REEXTRACCION = BASE.parents[0]                          # reextraccion_v2/
REPO = BASE.parents[3]                                  # raíz del repo

E0_SALIDA = REEXTRACCION / "e0_chunking" / "salida"            # calibración sellada
E0_SALIDA_ENM01 = REEXTRACCION / "e0_chunking" / "salida_enm01"  # enmienda 01 (con mini-chunks)
GRAFO_V2_CODE = REPO / "data" / "experiment" / "grafo_v2" / "code"
EVAL_DIR = REPO / "data" / "experiment" / "evaluacion"

# El esquema v2 vigente se IMPORTA de su fuente única (grafo_v2/code/schema.py,
# que a su vez carga esquema_v2_clases.json v2.0). No se duplica acá: cualquier
# copia divergiría del contrato real.
for p in (str(GRAFO_V2_CODE), str(EVAL_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

TOS = ("cap", "cla", "ext", "pro", "ric")


def cargar_chunks(tos: tuple[str, ...] = TOS, e0_dir: Path = E0_SALIDA) -> list[dict]:
    """Carga los chunks de E0 en orden estable (por TO en el orden de TOS,
    dentro de cada TO en el orden del archivo). `e0_dir` selecciona la salida
    de E0: la sellada (default) o la de la enmienda 01 (con mini-chunks)."""
    chunks: list[dict] = []
    for to in tos:
        path = e0_dir / f"chunks_{to}.json"
        with path.open(encoding="utf-8") as f:
            chunks.extend(json.load(f))
    return chunks


def chunk_flaggeado(chunk: dict) -> bool:
    f = chunk.get("flags") or {}
    return bool(f.get("contenido_tabular") or f.get("formula"))


def es_mini_chunk(chunk: dict) -> bool:
    """Mini-chunk (enmienda 01 §2.a): un bloque estructural emitido por E0
    como unidad de extracción de primera clase."""
    return chunk.get("tipo") == "mini_chunk"


def puntos_admitidos(chunk: dict) -> list[str]:
    """Conjunto cerrado de valores admitidos para el campo `punto` de la
    provenance de los elementos extraídos de este chunk. Orden estable, sin
    duplicados.

    - Mini-chunk (enmienda 01 §2.b, endurecimiento adoptado): SOLO su unidad
      de origen — el bloque es la unidad; no ancla en ancestros.
    - Chunk hijo: el punto propio más las unidades de origen de su cadena de
      herencia. La extensión del conjunto NO cambia con la enmienda: todo
      ancestro heredado aporta su línea de título (tramo `encabezado`), que
      sigue siendo ancla legítima (caso pro 2.7.x → 2.7 de la calibración).
      La restricción "solo encabezados de título" es un no-op a granularidad
      de punto — el valor `punto` no distingue de qué tramo del ancestro
      proviene el contenido —, así que la división de responsabilidad del
      hijo la garantizan la instrucción del prompt (el contexto ancla, la
      unidad extrae) y el blanco propio de E3, no este conjunto.
    """
    if es_mini_chunk(chunk):
        return [chunk["unidad"]]
    vistos: list[str] = [chunk["unidad"]]
    for h in chunk.get("herencia", []):
        u = h["unidad_origen"]
        if u not in vistos:
            vistos.append(u)
    return vistos


def rol_documental_de_punto(chunk: dict, punto: str) -> str:
    """Rol documental del segmento que funda un elemento con provenance
    `punto` (principio 2.e del diseño: documento + punto + rol documental).
    Determinístico desde la estructura de E0. Para un mini-chunk el rol es el
    del bloque mismo (`bloque_<rol>`): su contenido ES el bloque."""
    if punto == chunk["unidad"]:
        if es_mini_chunk(chunk):
            return f"bloque_{chunk['rol_bloque']}"
        return "punto_propio"
    for h in chunk.get("herencia", []):
        if h["unidad_origen"] == punto:
            return f"herencia_{h['tipo']}"
    return "desconocido"  # el validador rechaza antes de llegar acá
