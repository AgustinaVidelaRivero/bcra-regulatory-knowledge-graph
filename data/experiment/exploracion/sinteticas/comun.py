"""
comun.py — Infraestructura compartida del pipeline de queries sintéticas (issue #3).

Diseño vinculante: docs/diseno_queries_sinteticas.md. Fase A: todo offline,
cero llamadas LLM.

Provee:
  - Rutas y verificación de sha256 del grafo vigente.
  - Carga cruda del kg.json (provenances COMPLETAS) y carga runtime
    (loader con adaptador nulo — la vista que ven las tools del harness).
  - Parseo de location → ancla de provenance (TO + punto normativo).
  - Tokenización canónica (la del harness) + tokens de contenido (sin stopwords).
  - Índice de territorio quemado sobre el mapa de 5 sets, reutilizando las
    funciones de validar_anclas.py (misma regla laudada, sin reimplementar).

Decisión de censo: el gold y la resolución por-grafo usan las provenances
COMPLETAS del kg.json crudo (clave `provenances`, fallback `provenance`).
La vista runtime del harness (adaptador nulo, patrón run_escalon1b.py) expone
solo la provenance primaria; eso no afecta la métrica primaria, que se computa
por ids de nodo resueltos localmente, no por citas.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

SINTETICAS_DIR = Path(__file__).resolve().parent
EXPLORACION_DIR = SINTETICAS_DIR.parent
EXPERIMENT_DIR = EXPLORACION_DIR.parent
EVAL_DIR = EXPERIMENT_DIR / "evaluacion"

KG_VIGENTE = EXPERIMENT_DIR / "grafo_v2" / "reensamblado_v3" / "kg.json"
KG_VIGENTE_SHA256 = "26fac8b49f6c08c1aa364b47273d36958d831f240d4e6b4ee7700b6a0bff3571"
MAPA_5SETS = EXPLORACION_DIR / "mapa_territorio_quemado_5TOs_5sets.json"

for _p in (str(EVAL_DIR), str(EXPLORACION_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import validar_anclas  # noqa: E402  (patrón U6; se importa, no se copia)
from harness import GraphIndex, _tokens  # noqa: E402  (tools determinísticas)
from loader import load_graph_from_path  # noqa: E402

# --------------------------------------------------------------------------- #
# Mapeo documento ↔ TO (coincide con `archivo` de cada TO en el mapa de 5 sets)
# --------------------------------------------------------------------------- #
DOC2TO = {
    "TO_capitales_minimos_actual.pdf": "cap",
    "TO_clasificacion_deudores_actual.pdf": "cla",
    "TO_exterior_cambios_actual.pdf": "ext",
    "TO_proteccion_usuarios_servicios_financieros_actual.pdf": "pro",
    "TO_regimen_informativo_contable_mensual_actual.pdf": "ric",
}
TO2DOC = {v: k for k, v in DOC2TO.items()}


# --------------------------------------------------------------------------- #
# Carga del grafo                                                              #
# --------------------------------------------------------------------------- #
def sha256_de(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_kg_raw(path: Path = KG_VIGENTE, verificar_sha: bool = True) -> dict:
    """kg.json crudo: {'nodes': [...], 'edges': [...]}, provenances completas."""
    path = Path(path)
    if verificar_sha and path == KG_VIGENTE:
        got = sha256_de(path)
        if got != KG_VIGENTE_SHA256:
            raise RuntimeError(
                f"sha256 inesperado para {path}: {got} != {KG_VIGENTE_SHA256}"
            )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def index_runtime(path: Path = KG_VIGENTE) -> GraphIndex:
    """GraphIndex del harness sobre la vista runtime (adaptador nulo).

    Es la MISMA implementación de buscar_nodos / ver_nodo / ver_vecinos que
    corrió en las trazas posthoc de reensamblado_v3: re-ejecutarla sobre el
    mismo grafo reproduce los outputs de tool determinísticamente.
    """
    return GraphIndex(load_graph_from_path(path, adapter_key=None))


# --------------------------------------------------------------------------- #
# Parseo de location → ancla                                                   #
# --------------------------------------------------------------------------- #
# Cobertura medida sobre el grafo vigente: 6063/6081 provenances PDF parsean
# con PUNTO_RE (99,7 %); el resto son "Sección N" (cubiertas por SECCION_RE,
# ancla "SN" como en el mapa) o "Secciones N y M" (ambiguas: sin ancla).
PUNTO_RE = re.compile(r"Punto\s+(\d+(?:\.\d+)*)")
SECCION_RE = re.compile(r"^Secci[oó]n\s+(\d+)\b")


def parse_ancla(location: str) -> str | None:
    """'Punto 2.7. En el caso…' -> '2.7'; 'Sección 10' -> 'S10'; sino None."""
    if not location:
        return None
    m = PUNTO_RE.search(location)
    if m:
        return validar_anclas.normalizar(m.group(1))
    m = SECCION_RE.match(location.strip())
    if m:
        return "S" + m.group(1)
    return None


def anclas_de_nodo(raw_node: dict) -> tuple[list[dict], list[dict]]:
    """Anclas (TO + punto) de las provenances PDF de un nodo crudo.

    Devuelve (anclas, sin_parsear):
      anclas: [{'to', 'ancla', 'source_doc', 'location'}] deduplicadas por
              (to, ancla), preservando orden de aparición (la location guardada
              es la primera que produjo esa ancla, como referencia).
      sin_parsear: provenances PDF cuya location no produjo ancla.
    """
    provs = raw_node.get("provenances")
    if not provs:
        p = raw_node.get("provenance")
        provs = [p] if p else []
    anclas, sin_parsear, vistos = [], [], set()
    for p in provs:
        if not isinstance(p, dict):
            continue
        to = DOC2TO.get(p.get("source_doc") or "")
        if to is None:
            continue  # provenance no-PDF (esqueleto / diseño): no es ancla
        ancla = parse_ancla(p.get("location") or "")
        if ancla is None:
            sin_parsear.append({"source_doc": p.get("source_doc"),
                                "location": p.get("location")})
            continue
        key = (to, ancla)
        if key in vistos:
            continue
        vistos.add(key)
        anclas.append({"to": to, "ancla": ancla,
                       "source_doc": p.get("source_doc"),
                       "location": p.get("location")})
    return anclas, sin_parsear


# --------------------------------------------------------------------------- #
# Territorio quemado (mapa de 5 sets, regla laudada de validar_anclas.py)      #
# --------------------------------------------------------------------------- #
class Quemado:
    """Evalúa anclas contra el mapa de territorio quemado de 5 sets."""

    def __init__(self, mapa_path: Path = MAPA_5SETS):
        with open(mapa_path, encoding="utf-8") as f:
            self.mapa = json.load(f)
        if "U6" not in self.mapa.get("sets", {}):
            raise RuntimeError(
                f"El mapa {mapa_path} no incluye el set U6: no es el mapa de 5 sets."
            )
        self.indice = validar_anclas.indexar_mapa(self.mapa)

    def evaluar(self, to: str, ancla: str):
        """-> (veredicto 'apto'|'descartado', motivo, unidad_resuelta)."""
        return validar_anclas.validar_ancla(to, ancla, self.indice)

    def todas_aptas(self, anclas: list[dict]):
        """-> (bool, [detalle por ancla])."""
        detalle = []
        for a in anclas:
            veredicto, motivo, unidad = self.evaluar(a["to"], a["ancla"])
            detalle.append({"to": a["to"], "ancla": a["ancla"],
                            "unidad": unidad, "veredicto": veredicto,
                            "motivo": motivo})
        return all(d["veredicto"] == "apto" for d in detalle), detalle


# --------------------------------------------------------------------------- #
# Tokenización de contenido (para solape léxico y E-D)                         #
# --------------------------------------------------------------------------- #
# Stopwords castellano técnico-regulatorio: cierre chico y explícito — la meta
# es filtrar función gramatical, no señal normativa. Se comparan tokens ya
# normalizados por harness._tokens (lowercase, sin acentos).
STOPWORDS_ES = {
    "a", "al", "algo", "ante", "aquel", "aquella", "asi", "bajo", "cada",
    "como", "con", "contra", "cual", "cuales", "cuando", "cuya", "cuyo",
    "cuyos", "cuyas", "de", "del", "desde", "donde", "dos", "el", "ella",
    "ellas", "ellos", "en", "entre", "era", "es", "esa", "esas", "ese",
    "esos", "esta", "estas", "este", "estos", "fue", "ha", "hace", "hacia",
    "han", "hasta", "hay", "la", "las", "le", "les", "lo", "los", "mas",
    "mediante", "mismo", "misma", "mismos", "mismas", "muy", "ni", "no",
    "o", "otra", "otras", "otro", "otros", "para", "pero", "por", "que",
    "se", "sea", "sean", "segun", "ser", "si", "sin", "sobre", "son", "su",
    "sus", "tal", "tales", "tambien", "tanto", "tiene", "tienen", "toda",
    "todas", "todo", "todos", "tras", "un", "una", "uno", "unas", "unos",
    "y", "ya",
}


def tokens_contenido(texto: str) -> set:
    """Tokens normalizados sin stopwords ni restos de 1-2 letras.

    Los tokens numéricos ('20', '30', '2136') se CONSERVAN: en este corpus los
    valores (plazos, porcentajes, números de comunicación) son señal, no ruido.
    """
    out = set()
    for t in _tokens(texto or ""):
        if t in STOPWORDS_ES:
            continue
        if len(t) <= 2 and not t.isdigit():
            continue
        out.add(t)
    return out


def solape_lexico(pregunta: str, tokens_prohibidos: set) -> dict:
    """Métrica de solape léxico pregunta ↔ gold (§5 y puerta d del diseño).

    solape = |tokens_contenido(pregunta) ∩ prohibidos| / |tokens_contenido(pregunta)|

    Es la fracción del contenido de la pregunta que reutiliza vocabulario del
    gold (label + alta señal de descripcion). Se normaliza por la pregunta y no
    por el gold: mide cuánto de lo que el usuario ESCRIBIÓ delata la jerga del
    grafo, que es el mecanismo de clausura léxica documentado. Se reporta como
    variable continua por pregunta, además del corte binario de la puerta d.
    """
    q = tokens_contenido(pregunta)
    inter = q & tokens_prohibidos
    return {
        "solape": (len(inter) / len(q)) if q else 0.0,
        "tokens_pregunta": len(q),
        "tokens_en_comun": sorted(inter),
    }
