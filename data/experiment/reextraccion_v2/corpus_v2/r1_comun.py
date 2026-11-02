"""
r1_comun.py — Utilidades compartidas del pipeline r1 (U-B1a: E4/E5
determinísticos → KG-Reextraído-r1). Código puro, sin LLM, sin escrituras
bajo salida/ (sellada: es ENTRADA, no salida).

Rutas, carga de insumos sellados (grafos por TO, reportes E2, E0 enm01,
catálogo, extracciones finales y compactas, finales/veredictos/cola humana) y
helpers de serialización canónica (mismo json.dumps que ensamblar_corpus.py
para que los shas sean comparables).

Principio de no-edición: ensamblar_corpus.py, e2_lib.py, assemble.py y
ratchet_e3.py se IMPORTAN; nada de ellos se reescribe acá.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent                  # corpus_v2/
REX = AQUI.parent                                       # reextraccion_v2/
REPO = REX.parents[2]                                   # raíz del repo
SALIDA = AQUI / "salida"                                # SELLADA (entrada)
SALIDA_R1 = AQUI / "salida_r1"                          # producto de esta unidad
E0_ENM01 = REX / "e0_chunking" / "salida_enm01"
GRAFO_V2 = REPO / "data" / "experiment" / "grafo_v2"
GRAFO_V2_CODE = GRAFO_V2 / "code"
CATALOGO_PATH = GRAFO_V2 / "esquema_v2_clases.json"
KG_REFINADO = GRAFO_V2 / "reensamblado_v3" / "kg.json"

SHA_KG_SELLADO = "8e2eadee57b48e00ccb51ade9a953ba1469001fe089c45d97c4307ccf2725581"
SHA_REPORTE_SELLADO = "98ee43e59c1e74bd6f83ac2aacf2531d2914e672a979ace4fc453830bff343ae"

TOS_ORDEN = ("pro", "cla", "ric", "cap", "ext")

for p in (str(AQUI), str(GRAFO_V2_CODE), str(REX / "e2_reduce"),
          str(REX / "e1_extractor"), str(REX / "e3_verificador")):
    if p not in sys.path:
        sys.path.insert(0, p)


# ----------------------------- helpers ---------------------------------- #
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def dumps_kg(kg: dict) -> str:
    """Serialización canónica idéntica a ensamblar_corpus.main (indent=2)."""
    return json.dumps(kg, ensure_ascii=False, indent=2)


def dumps_reporte(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)


def norm(s: str) -> str:
    """Normalización para comparar labels: NFD sin diacríticos, minúsculas,
    espacios colapsados, sin puntuación periférica."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[\s]+", " ", s)
    s = s.strip(" .;:,")
    return s


def prov_key(p: dict) -> str:
    return json.dumps(p, ensure_ascii=False, sort_keys=True)


def leer_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                out.append(json.loads(linea))
    return out


def jsonl_last_wins(path: Path, clave: str = "chunk_id") -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in leer_jsonl(path):
        out[r[clave]] = r
    return out


# ----------------------------- cargas ----------------------------------- #
def cargar_grafos_sellados() -> dict[str, dict]:
    return {to: json.loads((SALIDA / to / f"grafo_{to}.json").read_text(encoding="utf-8"))
            for to in TOS_ORDEN}


def cargar_reporte_e2(to: str) -> dict:
    return json.loads((SALIDA / to / f"reporte_e2_{to}.json").read_text(encoding="utf-8"))


def cargar_catalogo() -> dict:
    return json.loads(CATALOGO_PATH.read_text(encoding="utf-8"))


def cargar_chunks_enm01(to: str) -> list[dict]:
    return json.loads((E0_ENM01 / f"chunks_{to}.json").read_text(encoding="utf-8"))


def cargar_estructura_enm01(to: str) -> dict:
    return json.loads((E0_ENM01 / f"estructura_{to}.json").read_text(encoding="utf-8"))


def cargar_extracciones_finales(to: str) -> list[dict]:
    return leer_jsonl(SALIDA / to / f"extracciones_finales_{to}.jsonl")


def cargar_e1_compact(to: str) -> dict[str, dict]:
    return jsonl_last_wins(SALIDA / to / "extracciones_e1_compact.jsonl")


def cargar_finales(to: str) -> dict[str, dict]:
    return jsonl_last_wins(SALIDA / to / "finales.jsonl")


def cargar_veredictos(to: str) -> list[dict]:
    return leer_jsonl(SALIDA / to / "veredictos.jsonl")


def cargar_cola_humana(to: str) -> list[dict]:
    return leer_jsonl(SALIDA / to / "cola_humana.jsonl")


def archivo_de_to(to: str) -> str:
    """Archivo PDF del TO según E0 (única fuente: los chunks)."""
    return cargar_chunks_enm01(to)[0]["archivo"]


def conteo(objs: list[dict], campo: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for o in objs:
        out[o[campo]] = out.get(o[campo], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
