"""
comun_e3.py — Paths, carga de insumos y utilidades del verificador de
completitud intra-unidad E3 (pipeline de re-extracción v2, fase A offline).

Insumos SOLO LECTURA:
  - data/experiment/reextraccion_v2/e0_chunking/salida/chunks_{to}.json
    (texto fuente por unidad: punto propio + herencia estructural)
  - data/experiment/reextraccion_v2/e1_extractor/salida/faseB_pro/extracciones.jsonl
    (lo extraído por unidad en la calibración E1, con validación por elemento)
  - data/experiment/reextraccion_v2/e2_reduce/salida/reporte_e2_pro.json
    (fan-in: qué chunks quedaron aceptados para ensamblar)
  - los módulos de E1 (prompt_e1 / validador_e1 / comun_e1), importados para
    la mecánica del mini-ratchet — jamás editados.

Principio 2.c del diseño (contexto fresco): NADA del contexto conversacional
del extractor entra al verificador. Este módulo arma el mensaje de E3 solo
desde DATOS: el chunk de E0 y la extracción validada de E1. El selftest
verifica que ninguna instrucción del prompt de E1 aparezca en el request de E3.

Nada de este módulo llama a ninguna API.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent                  # e3_verificador/
REEXTRACCION = BASE.parents[0]                          # reextraccion_v2/
REPO = BASE.parents[3]                                  # raíz del repo

E0_SALIDA = REEXTRACCION / "e0_chunking" / "salida"              # calibración sellada
E0_SALIDA_ENM01 = REEXTRACCION / "e0_chunking" / "salida_enm01"  # enmienda 01 (con mini-chunks)
E1_DIR = REEXTRACCION / "e1_extractor"
E1_FASEB = E1_DIR / "salida" / "faseB_pro"
E2_SALIDA = REEXTRACCION / "e2_reduce" / "salida"

# Los módulos de E1 se IMPORTAN (solo lectura): el ratchet reusa su prompt,
# su validador y su capa de caché sin duplicarlos. comun_e1 agrega a su vez
# grafo_v2/code y evaluacion/ al sys.path (schema + llm_cache).
if str(E1_DIR) not in sys.path:
    sys.path.insert(0, str(E1_DIR))
import comun_e1  # noqa: E402,F401  (agrega grafo_v2/code y evaluacion/ al sys.path)

TOS = ("cap", "cla", "ext", "pro", "ric")


def cargar_chunks(tos: tuple[str, ...] = TOS, e0_dir: Path = E0_SALIDA) -> list[dict]:
    """Chunks de E0 en orden estable (mismo criterio que comun_e1). `e0_dir`
    selecciona la salida: la sellada (default) o la de la enmienda 01."""
    chunks: list[dict] = []
    for to in tos:
        with (e0_dir / f"chunks_{to}.json").open(encoding="utf-8") as f:
            chunks.extend(json.load(f))
    return chunks


def cargar_extracciones(path: Path) -> dict[str, dict]:
    """Registros de una corrida E1 (jsonl), por chunk_id."""
    regs: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            regs[r["chunk_id"]] = r
    return regs


def cargar_extracciones_faseB() -> dict[str, dict]:
    """Registros de la calibración E1 fase B SELLADA (pro), por chunk_id."""
    return cargar_extracciones(E1_FASEB / "extracciones.jsonl")


def chunk_aceptado(reg: dict) -> bool:
    """Aceptado para E3 = la llamada E1 terminó bien y la validación no
    rechazó el chunk entero (mismo criterio de fan-in que E2)."""
    if reg.get("error") is not None or reg.get("validacion") is None:
        return False
    return not any(r["nivel"] == "chunk" for r in reg["validacion"]["rechazos"])


def pares_calibracion() -> list[tuple[dict, dict]]:
    """(chunk E0, validación E1) de los chunks de pro aceptados — el universo
    de la calibración de E3 fase B SELLADA."""
    por_id = {c["id"]: c for c in cargar_chunks(("pro",))}
    regs = cargar_extracciones_faseB()
    pares = []
    for cid, reg in regs.items():
        if chunk_aceptado(reg):
            pares.append((por_id[cid], reg["validacion"]))
    return pares


def pares_de(chunks: list[dict], regs: dict[str, dict]) -> list[tuple[dict, dict]]:
    """(chunk E0, validación E1) de los chunks aceptados de una corrida
    arbitraria (mismo criterio de fan-in que pares_calibracion), en el orden
    documental de `chunks`."""
    pares = []
    for c in chunks:
        reg = regs.get(c["id"])
        if reg is not None and chunk_aceptado(reg):
            pares.append((c, reg["validacion"]))
    return pares


# ------------------------------------------------------------------------- #
# Texto fuente íntegro de la unidad                                          #
# ------------------------------------------------------------------------- #

def indices_bloque_lista(chunk: dict) -> list[int]:
    """U-E3-LISTAS, pieza 1: índices de los bloques heredados que abren la lista
    de la que la unidad es un ítem. El bloque es el que elige la regla que arma
    LINEA_ITEM en el mensaje de E1 (prompt_r2b.bloque_lista), así que E1 y E3
    ven el mismo encabezado; con él van los bloques contiguos que lo preceden
    con el mismo tipo y la misma unidad de origen, porque E0 parte a veces un
    párrafo en varios bloques con el mismo rótulo (decisión D2 de la autora,
    enmienda 1 al mandato). Vacía si la unidad no es un ítem o es un mini-chunk."""
    import prompt_r2b  # noqa: PLC0415 — solo en la forma r2 (e1_extractor en sys.path)
    i = prompt_r2b.bloque_lista(chunk)
    if i is None:
        return []
    her = chunk["herencia"]
    j = i
    while (j > 0 and her[j - 1]["tipo"] == her[i]["tipo"]
           and her[j - 1]["unidad_origen"] == her[i]["unidad_origen"]):
        j -= 1
    return list(range(j, i + 1))


def fuente_integro(chunk: dict, bloque_de_lista: bool = False) -> str:
    """El texto fuente de la unidad, como DATOS (sin instrucciones).

    Enmienda 01 §2.d — el blanco de completitud es el TEXTO PROPIO de la
    unidad: el del punto para un chunk hijo, el del bloque para un mini-chunk.
    Del contexto heredado solo viajan los tramos `encabezado` (títulos de la
    cadena): orientan la lectura y no son contenido normativo exigible (el
    prompt del verificador ya excluye títulos como faltante). Los bloques de
    prosa heredados NO entran: cada uno tiene su propio mini-chunk como unidad
    verificada — si su contenido falta, el veredicto cae sobre esa unidad, no
    sobre el hijo.

    U-E3-LISTAS, pieza 1 (solo con la forma r2: `bloque_de_lista`, que pasa
    prompt_e3.build_user_message): si la unidad es un ítem de una lista, el
    fuente suma el bloque heredado que la abre (indices_bloque_lista), con su
    rótulo, y no los cierres que lo siguen. Sin el parámetro, igual que
    siempre, byte a byte."""
    lista = set(indices_bloque_lista(chunk)) if bloque_de_lista else set()
    partes: list[str] = []
    for k, h in enumerate(chunk.get("herencia", [])):
        if h["tipo"] != "encabezado" and k not in lista:
            continue
        partes.append(f"[{h['tipo']} | punto {h['unidad_origen']}]")
        partes.append(h["texto"])
    if chunk.get("tipo") == "mini_chunk":
        partes.append(f"[bloque {chunk['rol_bloque']} | punto {chunk['unidad']}]")
    else:
        partes.append(f"[texto propio | punto {chunk['unidad']}]")
    partes.append(chunk["texto"])
    return "\n".join(partes)


# ------------------------------------------------------------------------- #
# Render legible de la extracción validada                                   #
# ------------------------------------------------------------------------- #

def render_extraccion(validacion: dict) -> str:
    """Los elementos extraídos de la unidad (post-validación E1) en formato
    legible para el verificador. Función pura del dict de validación."""
    lines: list[str] = []
    entidades = validacion.get("entidades", [])
    relaciones = validacion.get("relaciones", [])
    labels = {e["local_id"]: e["label"] for e in entidades}

    lines.append("Entidades:")
    if not entidades:
        lines.append("(ninguna)")
    for e in entidades:
        lines.append(
            f"- ({e['local_id']}) {e['type']} — «{e['label']}» "
            f"[punto {e['provenance']['punto']}]"
        )
        for k, v in (e.get("properties") or {}).items():
            lines.append(f"    {k}: {v}")

    lines.append("Relaciones:")
    if not relaciones:
        lines.append("(ninguna)")
    for r in relaciones:
        punto = r["provenance"]["punto"]
        pred = r["predicate"]
        if pred in ("aplica_a", "ejecuta"):
            suj = r.get("sujeto_id") or f"propuesto «{r.get('sujeto_propuesto')}»"
            if pred == "aplica_a":
                src = r.get("source")
                lines.append(
                    f"- ({src} «{labels.get(src, '?')}») --aplica_a--> "
                    f"[sujeto {suj}] [punto {punto}]"
                )
            else:
                tgt = r.get("target")
                lines.append(
                    f"- [sujeto {suj}] --ejecuta--> "
                    f"({tgt} «{labels.get(tgt, '?')}») [punto {punto}]"
                )
        else:
            src, tgt = r.get("source"), r.get("target")
            lines.append(
                f"- ({src} «{labels.get(src, '?')}») --{pred}--> "
                f"({tgt} «{labels.get(tgt, '?')}») [punto {punto}]"
            )

    omisiones = validacion.get("omisiones_no_prosa") or []
    if omisiones:
        lines.append("Omisiones no-prosa declaradas por el extractor:")
        for o in omisiones:
            lines.append(f"- {o}")

    return "\n".join(lines)


# ------------------------------------------------------------------------- #
# Normalización para verificar citas contra el fuente (capa determinística)  #
# ------------------------------------------------------------------------- #

def normalizar_para_cita(texto: str) -> str:
    """Normalización EXTENDIDA (laudo post-calibración fase B, sobre el
    precedente C7): sin acentos + casefold + eliminación de TODO espacio en
    blanco + DES-GUIONADO TOTAL (se eliminan todos los guiones: cubre el corte
    de línea del PDF '-\\n' y su transcripción como guion+espacio
    'presta- ciones') + comillas tipográficas normalizadas a rectas.
    Neutraliza artefactos de extracción/transcripción sin tolerar paráfrasis
    (el texto alfanumérico debe coincidir íntegro)."""
    t = unicodedata.normalize("NFD", texto)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    for a, b in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"),
                 ("«", '"'), ("»", '"')):
        t = t.replace(a, b)
    t = "".join(t.split())
    for guion in ("-", "‐", "‑", "–", "—"):
        t = t.replace(guion, "")
    return t.casefold()


def fuente_para_citas(chunk: dict, bloque_de_lista: bool = False) -> str:
    """Fuente contra el que se verifican las citas (laudo post-fase B): los
    MISMOS textos que fuente_integro pero SIN los rótulos de bloque. Los
    rótulos ('[bloque intro | punto X]') se insertan entre segmentos que E0
    puede haber cortado a mitad de palabra ('presta-' / 'ciones'): una cita
    fiel que cruza esa frontera jamás matchearía contra el render con rótulos.
    Enmienda 01: mismo alcance que fuente_integro — títulos heredados + texto
    propio de la unidad. U-E3-LISTAS: con `bloque_de_lista` (la forma r2, que
    pasa ratchet_e3.evaluar_veredicto), el mismo alcance que fuente_integro
    con el parámetro: suma el bloque que abre la lista."""
    lista = set(indices_bloque_lista(chunk)) if bloque_de_lista else set()
    partes = [h["texto"] for k, h in enumerate(chunk.get("herencia", []))
              if h["tipo"] == "encabezado" or k in lista]
    partes.append(chunk["texto"])
    return "\n".join(partes)


def cita_en_fuente(cita: str, chunk: dict, bloque_de_lista: bool = False) -> bool:
    """¿La cita textual reportada por el verificador existe en el fuente de la
    unidad? Chequeo determinístico: una cita que no verifica NO se inyecta al
    reintento (una cita fabricada envenenaría la re-extracción). Verifica
    contra el fuente SIN rótulos y con la normalización extendida."""
    if not cita or not cita.strip():
        return False
    return normalizar_para_cita(cita) in normalizar_para_cita(fuente_para_citas(chunk, bloque_de_lista))
