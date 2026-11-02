"""
harness.py — Agente respondedor KG-RAG (Fase 2.3).

Agente UNIFORME sobre los 5 grafos de la Fase 2.2: mismas tools, misma interfaz,
mismo modelo. La única variable entre corridas es el grafo (cargado vía loader.py).

Spec (decidida con la autora):
  - Modelo: claude-haiku-4-5-20251001, FIJO para los 5 grafos. Temperature 0.
  - Tools (operan sobre el modelo en memoria del loader):
      buscar_nodos(consulta, limite=10) — búsqueda léxica sobre label e id
          (normalizada: lowercase + sin acentos, por tokens, ranking por
          nº de tokens matcheados). Devuelve id, type, label y un resumen
          corto de properties. Sin embeddings (decisión explícita revisable).
      ver_nodo(id) — nodo completo: type, label, properties, provenances.
      ver_vecinos(id, direccion="ambas") — edges entrantes/salientes con
          relation, label del vecino y provenances del edge.
  - Contrato de respuesta (JSON): {respuesta, citas, respondible}.
      'citas' = lista de {source_doc, location} tomadas de provenances que el
      agente efectivamente vio en sus tool calls. 'respondible' = false si la
      info no está en el grafo (no inventar).
  - Límite: 15 tool calls por pregunta.
  - Provenance uniforme: source_doc + location (decisión 4).

Logging: una traza completa por pregunta (cada tool call con input + output
truncado, tokens in/out, latencia, costo estimado, JSON final). Un archivo por
corrida en evaluacion/trazas/.

NO evalúa el grafo (eso es fase posterior con LLM-judge). Solo responde + loguea.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from loader import load_graph, KnowledgeGraph, EVAL_DIR

# --------------------------------------------------------------------------- #
# Config                                                                       #
# --------------------------------------------------------------------------- #
MODEL = "claude-haiku-4-5-20251001"   # FIJO para los 5 grafos
TEMPERATURE = 0
MAX_TOKENS = 2048
MAX_TOOL_CALLS = 15

# Precios Haiku 4.5 (USD por millón de tokens) — referencia claude-api skill.
PRICE_IN_PER_M = 1.00
PRICE_OUT_PER_M = 5.00
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.10

TRAZAS_DIR = EVAL_DIR / "trazas"
TRUNC_TOOL_OUTPUT = 1200   # chars por output de tool en la traza loggeada

SYSTEM_PROMPT = """\
Sos un asistente que responde preguntas sobre regulación del BCRA usando \
EXCLUSIVAMENTE un Knowledge Graph, al que accedés mediante tres tools. No tenés \
otro conocimiento disponible: si algo no está en el grafo, no lo sabés.

Tools disponibles:
- buscar_nodos(consulta, limite): búsqueda léxica de nodos por label/id. Empezá \
siempre por acá para encontrar puntos de entrada.
- ver_nodo(id): devuelve type, label, properties y provenances de un nodo.
- ver_vecinos(id, direccion): devuelve los edges (relaciones) entrantes/salientes \
de un nodo, con el vecino y las provenances del edge.

Estrategia: buscá nodos relevantes, abrí los que parezcan pertinentes con \
ver_nodo, y explorá relaciones con ver_vecinos hasta tener evidencia suficiente. \
Tenés un máximo de 15 tool calls por pregunta: usalas con criterio.

REGLAS DURAS:
1. Solo afirmá lo que esté respaldado por lo que devolvieron las tools. No \
inventes obligaciones, plazos, montos ni entidades que no viste en el grafo.
2. Si la información necesaria no está en el grafo, respondé con \
"respondible": false y explicá brevemente en "respuesta" qué falta. No inventes.
3. Las citas deben salir de las provenances que viste en ver_nodo / ver_vecinos \
(campos source_doc y location). No cites provenances que no observaste.

FORMATO DE SALIDA: cuando tengas la respuesta final, respondé con UN ÚNICO objeto \
JSON válido, sin texto adicional ni markdown, con exactamente estas claves:
{
  "respuesta": "<texto de la respuesta en español>",
  "citas": [{"source_doc": "<archivo>", "location": "<ubicación>"}, ...],
  "respondible": true|false
}
Si "respondible" es false, "citas" puede ser una lista vacía."""


# --------------------------------------------------------------------------- #
# Normalización léxica (para buscar_nodos)                                     #
# --------------------------------------------------------------------------- #
def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> list:
    return _TOKEN_RE.findall(_strip_accents((s or "").lower()))


def _short_props(props: dict, max_len: int = 160) -> str:
    """Resumen corto de properties para buscar_nodos."""
    if not props:
        return ""
    for k in ("description", "descripcion"):
        if props.get(k):
            v = str(props[k])
            return (v[:max_len] + "…") if len(v) > max_len else v
    parts = []
    for k, v in props.items():
        parts.append(f"{k}: {v}")
        if sum(len(p) for p in parts) > max_len:
            break
    s = "; ".join(parts)
    return (s[:max_len] + "…") if len(s) > max_len else s


# --------------------------------------------------------------------------- #
# Índice del grafo + tools                                                     #
# --------------------------------------------------------------------------- #
class GraphIndex:
    """Índices en memoria sobre el KnowledgeGraph del loader para las 3 tools."""

    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.by_id = {n.id: n for n in kg.nodes}
        # tokens por nodo (label + id)
        self._node_tokens = {
            n.id: set(_tokens(n.label) + _tokens(n.id)) for n in kg.nodes
        }
        # adyacencia
        self.out_edges = {}
        self.in_edges = {}
        for e in kg.edges:
            self.out_edges.setdefault(e.source, []).append(e)
            self.in_edges.setdefault(e.target, []).append(e)

    # --- tool 1 ---
    def buscar_nodos(self, consulta: str, limite: int = 10) -> dict:
        q = set(_tokens(consulta))
        if not q:
            return {"consulta": consulta, "resultados": [], "total": 0}
        scored = []
        for n in self.kg.nodes:
            score = len(q & self._node_tokens[n.id])
            if score:
                scored.append((score, len(n.label or ""), n))
        scored.sort(key=lambda t: (-t[0], t[1], t[2].id))
        try:
            limite = max(1, min(int(limite), 50))
        except (TypeError, ValueError):
            limite = 10
        top = scored[:limite]
        return {
            "consulta": consulta,
            "total_con_match": len(scored),
            "resultados": [
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "tokens_matcheados": score,
                    "resumen_propiedades": _short_props(n.properties),
                }
                for score, _, n in top
            ],
        }

    # --- tool 2 ---
    def ver_nodo(self, id: str) -> dict:
        n = self.by_id.get(id)
        if n is None:
            return {"error": f"No existe un nodo con id '{id}'.",
                    "sugerencia": "Usá buscar_nodos para encontrar el id correcto."}
        return {
            "id": n.id,
            "type": n.type,
            "label": n.label,
            "properties": n.properties,
            "provenances": n.provenances,
        }

    # --- tool 3 ---
    # DECISIÓN PENDIENTE (no implementar todavía): si el cap de 40 vecinos por
    # dirección resulta un cuello de botella en los hubs durante el loop manual,
    # evaluar agregar un parámetro `filtro_relacion` y/o paginación a ver_vecinos.
    # Se decide DESPUÉS del loop manual y SIEMPRE antes de la corrida congelada.
    def ver_vecinos(self, id: str, direccion: str = "ambas", limite: int = 40) -> dict:
        n = self.by_id.get(id)
        if n is None:
            return {"error": f"No existe un nodo con id '{id}'.",
                    "sugerencia": "Usá buscar_nodos para encontrar el id correcto."}
        direccion = (direccion or "ambas").lower()
        if direccion not in ("ambas", "salientes", "entrantes"):
            direccion = "ambas"
        out, inn = [], []
        if direccion in ("ambas", "salientes"):
            for e in self.out_edges.get(id, []):
                vecino = self.by_id.get(e.target)
                out.append({
                    "relation": e.relation,
                    "vecino_id": e.target,
                    "vecino_label": vecino.label if vecino else None,
                    "provenances": e.provenances,
                })
        if direccion in ("ambas", "entrantes"):
            for e in self.in_edges.get(id, []):
                vecino = self.by_id.get(e.source)
                inn.append({
                    "relation": e.relation,
                    "vecino_id": e.source,
                    "vecino_label": vecino.label if vecino else None,
                    "provenances": e.provenances,
                })
        res = {
            "id": id,
            "label": n.label,
            "n_salientes_total": len(self.out_edges.get(id, [])),
            "n_entrantes_total": len(self.in_edges.get(id, [])),
        }
        if direccion in ("ambas", "salientes"):
            res["salientes"] = out[:limite]
            res["salientes_truncado"] = len(out) > limite
        if direccion in ("ambas", "entrantes"):
            res["entrantes"] = inn[:limite]
            res["entrantes_truncado"] = len(inn) > limite
        return res


# Definición de tools para la API (idéntica para los 5 grafos).
TOOLS = [
    {
        "name": "buscar_nodos",
        "description": ("Búsqueda léxica de nodos del grafo por coincidencia de "
                        "palabras en su label o id (normalizada, sin acentos). "
                        "Devuelve id, type, label y un resumen corto de "
                        "propiedades. Es el punto de entrada habitual."),
        "input_schema": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string",
                             "description": "Palabras clave a buscar."},
                "limite": {"type": "integer",
                           "description": "Máximo de resultados (def. 10)."},
            },
            "required": ["consulta"],
        },
    },
    {
        "name": "ver_nodo",
        "description": ("Devuelve un nodo completo por su id exacto: type, label, "
                        "properties y provenances (source_doc + location)."),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "id exacto del nodo."},
            },
            "required": ["id"],
        },
    },
    {
        "name": "ver_vecinos",
        "description": ("Devuelve las relaciones (edges) de un nodo: relation, "
                        "vecino y provenances del edge. 'direccion' puede ser "
                        "'salientes', 'entrantes' o 'ambas'."),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "id exacto del nodo."},
                "direccion": {"type": "string",
                              "enum": ["ambas", "salientes", "entrantes"],
                              "description": "Dirección de los edges (def. ambas)."},
            },
            "required": ["id"],
        },
    },
]


# --------------------------------------------------------------------------- #
# Agente (manual agentic loop)                                                 #
# --------------------------------------------------------------------------- #
@dataclass
class QuestionTrace:
    qid: str
    question: str
    steps: list = field(default_factory=list)   # tool calls + io
    api_calls: list = field(default_factory=list)  # usage/latencia por call
    final_json: dict = None
    final_raw: str = None
    final_stop_reason: str = None
    truncated_max_tokens: bool = False
    parse_ok: bool = False
    parse_error: str = None
    tool_calls_used: int = 0
    hit_tool_limit: bool = False
    seen_provenances: list = field(default_factory=list)
    citations_unseen_raw: list = field(default_factory=list)
    citations_unseen_normalized: list = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    error: str = None


def _truncate(s: str, n: int = TRUNC_TOOL_OUTPUT) -> str:
    return s if len(s) <= n else s[:n] + f"… [+{len(s)-n} chars]"


# --------------------------------------------------------------------------- #
# Fidelidad de citas — definición CONGELADA de "cita fiel"                     #
# --------------------------------------------------------------------------- #
# Una cita {source_doc, location} emitida por el agente se considera FIEL si
# existe una provenance que el agente efectivamente vio en sus tool calls
# (ver_nodo / ver_vecinos) tal que:
#   (1) source_doc coincide EXACTO (byte a byte), y
#   (2) location coincide tras NORMALIZACIÓN, donde normalizar significa, en orden:
#        a. Unificar TODAS las comillas (rectas y tipográficas, simples y dobles:
#           " ' “ ” „ ‟ ‘ ’ ‚ ‛) a un único carácter canónico ("). La distinción
#           simple/doble en estas location del BCRA es ruido cosmético — son las
#           comillas de Comunicación "A"/'A', que el modelo y el grafo renderizan
#           de forma inconsistente.
#        b. Colapsar todo whitespace a un único espacio y hacer strip.
#        c. Quitar el sufijo de chunk-split  "(parte N)"  al final (N entero).
#        d. Quitar punto(s) y espacios finales.
# Además, SOLO para locations truncadas en el grafo (el valor almacenado quedó
# cortado durante la extracción), se admite PREFIX-MATCH: si la location vista
# (la del grafo) es prefijo de la location citada y mide >= 40 chars normalizados,
# la cita es fiel (el modelo completó un texto que el grafo guardó truncado).
# No se admite el prefijo en la dirección inversa ni umbrales < 40 chars.
#
# La traza conserva AMBAS lecturas: citations_unseen_raw (match byte-exacto,
# estricto) y citations_unseen_normalized (bajo estas reglas). Esta es la
# definición operativa de "cita fiel" para la Fase 2.3.
_PARTE_RE = re.compile(r"\s*\(parte\s+\d+\)\s*$", re.IGNORECASE)
_QUOTES_ALL = "\"'“”„‟‘’‚‛"   # todas las comillas → canónico único


def _norm_loc(s: str) -> str:
    s = s or ""
    for q in _QUOTES_ALL:
        s = s.replace(q, '"')
    s = re.sub(r"\s+", " ", s).strip()
    s = _PARTE_RE.sub("", s)
    s = s.rstrip(" .")
    return s


def _cita_fiel(cited: dict, seen_provs: list) -> bool:
    """True si la cita es fiel a alguna provenance vista (reglas congeladas)."""
    cdoc = cited.get("source_doc")
    cloc = _norm_loc(cited.get("location"))
    for p in seen_provs:
        if p.get("source_doc") != cdoc:
            continue
        sloc = _norm_loc(p.get("location"))
        if cloc == sloc:
            return True
        # prefix-match SOLO si la location del grafo (vista) está truncada:
        # la vista es prefijo de la citada y mide >= 40 chars normalizados.
        if len(sloc) >= 40 and cloc.startswith(sloc):
            return True
    return False


def _extract_json(text: str):
    """Parsea el JSON final; tolera fences ```json y texto alrededor."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE).strip()
    try:
        return json.loads(t), None
    except json.JSONDecodeError as e1:
        m = re.search(r"\{.*\}", t, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0)), None
            except json.JSONDecodeError as e2:
                return None, f"{e1}; fallback: {e2}"
        return None, str(e1)


def _apply_cache_breakpoint(messages):
    """Caching multi-turn: coloca UN cache_control móvil en el último bloque del
    último mensaje de usuario. La entrada de cache escrita en la llamada N se lee
    como prefijo en la llamada N+1 (que agrega ~1 ronda de bloques, muy por debajo
    del lookback de 20). El contenido del prompt NO cambia: cache_control es un
    directivo, no texto. Solo se marca en mensajes de usuario (que construimos como
    dicts); los turnos de assistant (objetos del SDK) se dejan intactos.

    Ámbito del beneficio: INTRA-pregunta. El prefijo compartido entre preguntas
    distintas (system+tools, ~1.433 tok) está por debajo del mínimo cacheable de
    Haiku 4.5 (4.096 tok), así que el cache NO se comparte entre preguntas."""
    last_user_blocks = None
    for m in messages:
        if m.get("role") != "user":
            continue
        if isinstance(m["content"], str):
            m["content"] = [{"type": "text", "text": m["content"]}]
        if isinstance(m["content"], list):
            for b in m["content"]:
                if isinstance(b, dict):
                    b.pop("cache_control", None)
            last_user_blocks = m["content"]
    if last_user_blocks:
        for b in reversed(last_user_blocks):
            if isinstance(b, dict):
                b["cache_control"] = {"type": "ephemeral"}
                break


class GraphAgent:
    def __init__(self, kg: KnowledgeGraph, client=None, cache_conversation=False):
        self.kg = kg
        self.index = GraphIndex(kg)
        self.cache_conversation = cache_conversation
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client

    def _run_tool(self, name: str, args: dict):
        if name == "buscar_nodos":
            return self.index.buscar_nodos(args.get("consulta", ""),
                                           args.get("limite", 10))
        if name == "ver_nodo":
            return self.index.ver_nodo(args.get("id", ""))
        if name == "ver_vecinos":
            return self.index.ver_vecinos(args.get("id", ""),
                                          args.get("direccion", "ambas"))
        return {"error": f"tool desconocida: {name}"}

    @staticmethod
    def _collect_provs(result, sink: set, ordered: list):
        """Acumula provenances vistas en un output de tool."""
        def add(p):
            if isinstance(p, dict) and ("source_doc" in p or "location" in p):
                key = (p.get("source_doc"), p.get("location"))
                if key not in sink:
                    sink.add(key)
                    ordered.append({"source_doc": key[0], "location": key[1]})
        if isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            for p in item.get("provenances", []) or []:
                                add(p)
                        else:
                            add(item)
                elif isinstance(v, dict):
                    pass
            for p in result.get("provenances", []) or []:
                add(p)

    def ask(self, qid: str, question: str) -> QuestionTrace:
        tr = QuestionTrace(qid=qid, question=question)
        seen = set()
        messages = [{"role": "user", "content": question}]
        t0 = time.monotonic()
        force_final = False
        try:
            while True:
                if self.cache_conversation:
                    _apply_cache_breakpoint(messages)
                kwargs = dict(model=MODEL, max_tokens=MAX_TOKENS,
                              temperature=TEMPERATURE, system=SYSTEM_PROMPT,
                              messages=messages, tools=TOOLS)
                if force_final:
                    # Mantener `tools` en el request (el historial tiene bloques
                    # tool_use; omitir tools haría que la API lo rechace) pero
                    # prohibir nuevas tool calls para forzar la respuesta final.
                    kwargs["tool_choice"] = {"type": "none"}
                c0 = time.monotonic()
                resp = self.client.messages.create(**kwargs)
                dt = time.monotonic() - c0

                u = resp.usage
                cin = getattr(u, "cache_read_input_tokens", 0) or 0
                cwr = getattr(u, "cache_creation_input_tokens", 0) or 0
                tr.tokens_in += u.input_tokens
                tr.tokens_out += u.output_tokens
                tr.cache_read += cin
                tr.cache_write += cwr
                tr.api_calls.append({
                    "stop_reason": resp.stop_reason,
                    "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                    "cache_read": cin, "cache_write": cwr,
                    "latency_s": round(dt, 3),
                })

                if resp.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": resp.content})
                    tool_results = []
                    for block in resp.content:
                        if block.type != "tool_use":
                            continue
                        tr.tool_calls_used += 1
                        result = self._run_tool(block.name, block.input or {})
                        self._collect_provs(result, seen, tr.seen_provenances)
                        result_str = json.dumps(result, ensure_ascii=False)
                        tr.steps.append({
                            "n": tr.tool_calls_used,
                            "tool": block.name,
                            "input": block.input,
                            "output_truncado": _truncate(result_str),
                            "output_chars": len(result_str),
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                    messages.append({"role": "user", "content": tool_results})

                    if tr.tool_calls_used >= MAX_TOOL_CALLS:
                        tr.hit_tool_limit = True
                        force_final = True
                        messages.append({
                            "role": "user",
                            "content": ("Alcanzaste el límite de 15 tool calls. "
                                        "Respondé AHORA con el JSON final según el "
                                        "formato indicado, usando solo la evidencia "
                                        "ya recolectada."),
                        })
                    continue

                # end_turn / max_tokens / forced final: respuesta final
                tr.final_stop_reason = resp.stop_reason
                if resp.stop_reason == "max_tokens":
                    tr.truncated_max_tokens = True
                final_text = "".join(
                    b.text for b in resp.content if getattr(b, "type", "") == "text"
                )
                tr.final_raw = final_text
                parsed, err = _extract_json(final_text)
                if parsed is not None:
                    tr.final_json = parsed
                    tr.parse_ok = True
                    # validar citas contra provenances vistas (raw + normalizado)
                    seen_keys = {(p["source_doc"], p["location"])
                                 for p in tr.seen_provenances}
                    for c in (parsed.get("citas") or []):
                        if isinstance(c, dict):
                            key = (c.get("source_doc"), c.get("location"))
                            if key not in seen_keys:
                                tr.citations_unseen_raw.append(c)
                            if not _cita_fiel(c, tr.seen_provenances):
                                tr.citations_unseen_normalized.append(c)
                elif tr.truncated_max_tokens:
                    # No es un parse error genuino: el JSON quedó cortado porque
                    # la respuesta alcanzó max_tokens. Se distingue explícitamente.
                    tr.parse_error = (
                        f"JSON truncado por max_tokens ({MAX_TOKENS}); "
                        f"NO es un parse error genuino. Detalle del parser: {err}"
                    )
                else:
                    tr.parse_error = err
                break
        except Exception as e:  # noqa: BLE001 — loguear cualquier fallo de API/parse
            tr.error = f"{type(e).__name__}: {e}"

        tr.latency_s = round(time.monotonic() - t0, 3)
        tr.cost_usd = round(
            (tr.tokens_in * PRICE_IN_PER_M
             + tr.cache_write * PRICE_IN_PER_M * CACHE_WRITE_MULT
             + tr.cache_read * PRICE_IN_PER_M * CACHE_READ_MULT) / 1e6
            + (tr.tokens_out * PRICE_OUT_PER_M) / 1e6,
            6,
        )
        return tr


# --------------------------------------------------------------------------- #
# Runner de corrida + persistencia de trazas                                   #
# --------------------------------------------------------------------------- #
def run_corrida(run_key: str, queries: list, label: str = "") -> Path:
    """Corre el agente sobre una lista de queries [{id, pregunta}] para un grafo.
    Escribe una traza por corrida en evaluacion/trazas/ y devuelve su ruta."""
    kg = load_graph(run_key)
    agent = GraphAgent(kg)
    traces = []
    print(f"== Corrida {run_key} ({len(queries)} preguntas) ==", flush=True)
    for q in queries:
        qid = q.get("id", "?")
        print(f"  [{qid}] {q.get('pregunta','')[:70]}…", flush=True)
        tr = agent.ask(qid, q.get("pregunta", ""))
        print(f"      tools={tr.tool_calls_used} parse_ok={tr.parse_ok} "
              f"respondible={(tr.final_json or {}).get('respondible')} "
              f"costo=${tr.cost_usd:.5f} {tr.latency_s}s"
              + (f"  ERROR={tr.error}" if tr.error else ""), flush=True)
        traces.append(tr)

    TRAZAS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    out_path = TRAZAS_DIR / f"{stamp}_{run_key}{suffix}.json"

    payload = {
        "corrida": {
            "run_key": run_key,
            "label": label,
            "timestamp": stamp,
            "model": MODEL,
            "temperature": TEMPERATURE,
            "max_tool_calls": MAX_TOOL_CALLS,
            "source_kg": str(kg.path),
            "n_preguntas": len(traces),
        },
        "totales": {
            "tokens_in": sum(t.tokens_in for t in traces),
            "tokens_out": sum(t.tokens_out for t in traces),
            "cache_read": sum(t.cache_read for t in traces),
            "cache_write": sum(t.cache_write for t in traces),
            "costo_usd": round(sum(t.cost_usd for t in traces), 6),
            "latencia_total_s": round(sum(t.latency_s for t in traces), 3),
        },
        "trazas": [vars(t) for t in traces],
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nTraza escrita en: {out_path}", flush=True)
    print(f"Costo total de la corrida: ${payload['totales']['costo_usd']:.5f}",
          flush=True)
    return out_path


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    load_dotenv(EVAL_DIR / ".env")

    ap = argparse.ArgumentParser(description="Corre el harness KG-RAG sobre un grafo.")
    ap.add_argument("--run", default="run_3", help="run_1..run_5 (def. run_3)")
    ap.add_argument("--queries", default=str(EVAL_DIR / "queries" / "dev.json"),
                    help="JSON con [{id, pregunta}] (def. queries/dev.json)")
    ap.add_argument("--label", default="dev", help="etiqueta de la corrida")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise SystemExit(
            "ERROR: ANTHROPIC_API_KEY no está seteada. Completá "
            f"{EVAL_DIR / '.env'} con: ANTHROPIC_API_KEY=sk-ant-..."
        )

    with open(args.queries, encoding="utf-8") as f:
        queries = json.load(f)
    run_corrida(args.run, queries, label=args.label)
