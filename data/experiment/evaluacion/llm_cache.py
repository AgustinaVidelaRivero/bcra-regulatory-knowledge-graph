"""
llm_cache.py — Caché persistente de llamadas a la API + captura del crudo (Fase 2.3+).

Capa de instrumentación para la corrida NUEVA (post-hoc / escalado). NO toca el
dataset congelado ni los módulos congelados (harness.py, judge.py, run_frozen.py):
es un wrapper que IMITA la interfaz del cliente Anthropic (`.messages.create(**kwargs)`),
así es drop-in y compone con el RetryingClient existente sin modificarlo.

Qué resuelve (las tres necesidades de la tarea):
  1. Guarda el OBJETO CRUDO COMPLETO de cada llamada (`resp.model_dump()`), sin dropear
     nada: usage (los 4 campos de tokens), stop_reason, content[] (incluidos thinking
     blocks con su signature), model, id, role. Se captura en el punto más bajo, ANTES
     de que cualquier código aguas arriba recorte.
  2. Caché persistente en disco (SQLite). La KEY es un hash determinístico del request
     REAL canónico, namespaced por (dominio, versión de código, huella del grafo, flag
     de thinking). El VALUE es el crudo íntegro. Nunca se paga dos veces la misma llamada.
  3. Métricas agregadas: tokens por llamada en columnas tipadas + log de accesos para
     hit rate (incluido cross-corrida).

Decisiones firmadas con la autora:
  - thinking como FLAG por corrida → entra en el namespace (think=0/1); las cachés
    thinking-ON y thinking-OFF nunca se cruzan.
  - access_log persistente (hit rate cross-corrida + fase de escalado).
  - code_version = hash automático de los fuentes relevantes (harness/judge/loader):
    se prefiere re-pagar ante un cambio cosmético antes que comer un hit stale.
  - una sola .db, segmentada por la columna `domain` ('agent' | 'judge').
  - key sobre el payload REAL canónico (serialización determinística del request).

NOTA (a confirmar al implementar la corrida, no acá): el detalle exacto de `temperature`
con thinking en Haiku 4.5 se valida con un request de prueba real; este módulo es agnóstico
a eso (hashea lo que reciba en kwargs, sea cual sea el valor de temperature/thinking).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Tag de versión del loader: bumpear si cambia la normalización en memoria del grafo
# (merges run5, descarte de chunk_id, etc.). Forma parte de la huella del grafo porque
# el agente consume el grafo NORMALIZADO, no el kg.json crudo.
LOADER_VERSION = "loader-v1"

# Archivos fuente que definen el comportamiento de las llamadas. Su hash compone
# code_version: cualquier edición invalida la caché (decisión: hash automático).
_SOURCE_FILES = ("harness.py", "judge.py", "loader.py")

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = EVAL_DIR / "cache" / "calls.db"


# --------------------------------------------------------------------------- #
# Versionado / namespace (puro, testeable sin API)                            #
# --------------------------------------------------------------------------- #
def code_version(source_dir: Path | None = None) -> str:
    """Hash corto de los fuentes relevantes (harness/judge/loader). Cambia si cambia
    cualquiera → invalida la caché. Si falta un archivo, se omite (no rompe)."""
    base = source_dir or EVAL_DIR
    h = hashlib.sha256()
    for name in _SOURCE_FILES:
        p = base / name
        if p.exists():
            h.update(name.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


def graph_fingerprint(kg) -> str:
    """Huella del grafo que consume el agente: sha256(kg.json) + tag del loader.
    `kg` es el KnowledgeGraph del loader; usa kg.path (el .json congelado en disco).
    El tag del loader cubre el hecho de que el agente ve el grafo NORMALIZADO en memoria,
    no el kg.json crudo."""
    h = hashlib.sha256()
    h.update(LOADER_VERSION.encode("utf-8"))
    path = getattr(kg, "path", None)
    if path is not None and Path(path).exists():
        h.update(Path(path).read_bytes())
    return h.hexdigest()[:16]


def make_namespace(domain: str, *, code_ver: str,
                   graph_fp: str | None = None, thinking: bool = False) -> str:
    """Namespace que prefija (y particiona) la key. graph_fp solo aplica al agente;
    el juez no consume grafo. thinking entra siempre (think=0/1)."""
    parts = [domain, f"cv={code_ver}", f"think={1 if thinking else 0}"]
    if graph_fp is not None:
        parts.insert(1, f"gfp={graph_fp}")
    return "|".join(parts)


# --------------------------------------------------------------------------- #
# Serialización canónica del request + key                                    #
# --------------------------------------------------------------------------- #
def _jsonable(obj):
    """default= para json.dumps: baja objetos del SDK (ContentBlock, Usage, …) a dict.
    Los turnos de assistant del historial son objetos Pydantic (con .model_dump);
    los turnos de user que construye el harness son dicts planos."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    raise TypeError(f"no serializable: {type(obj).__name__}")


def canonical_request(kwargs: dict) -> str:
    """Serialización determinística del request REAL (el payload que se manda por el
    cable). sort_keys ordena claves de dict; el orden de las LISTAS (messages, content,
    tools) se preserva tal cual (es significativo). Se hashea TODO lo que va en kwargs
    —model, system, messages, tools, tool_choice, temperature, max_tokens, thinking,
    stop_sequences, cache_control, etc.— para máxima fidelidad al request real."""
    return json.dumps(kwargs, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=_jsonable)


def compute_key(namespace: str, canonical: str) -> str:
    """sha256(namespace + '\\n' + request canónico)."""
    h = hashlib.sha256()
    h.update(namespace.encode("utf-8"))
    h.update(b"\n")
    h.update(canonical.encode("utf-8"))
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# Almacenamiento SQLite (caché + access_log)                                  #
# --------------------------------------------------------------------------- #
_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache (
    key                TEXT PRIMARY KEY,
    namespace          TEXT NOT NULL,
    domain             TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    model              TEXT NOT NULL,
    input_tokens       INTEGER NOT NULL,
    output_tokens      INTEGER NOT NULL,
    cache_read_tokens  INTEGER NOT NULL,
    cache_write_tokens INTEGER NOT NULL,
    stop_reason        TEXT,
    thinking_enabled   INTEGER NOT NULL,
    request_json       TEXT NOT NULL,
    raw_json           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_ns     ON cache(namespace);
CREATE INDEX IF NOT EXISTS idx_cache_domain ON cache(domain);

CREATE TABLE IF NOT EXISTS access_log (
    ts        TEXT NOT NULL,
    key       TEXT NOT NULL,
    domain    TEXT NOT NULL,
    hit       INTEGER NOT NULL,
    run_label TEXT
);
CREATE INDEX IF NOT EXISTS idx_access_key ON access_log(key);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")      # múltiples conexiones (agente+juez) OK
    conn.execute("PRAGMA busy_timeout=5000;")     # tolera contención breve
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def _lookup(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM cache WHERE key = ?", (key,))
    return cur.fetchone()


def _store(conn: sqlite3.Connection, *, key, namespace, domain, created_at, model,
           usage: dict, stop_reason, thinking_enabled, request_json, raw_json) -> None:
    # INSERT OR IGNORE: idempotente ante un doble-miss concurrente con la misma key.
    conn.execute(
        """INSERT OR IGNORE INTO cache
           (key, namespace, domain, created_at, model, input_tokens, output_tokens,
            cache_read_tokens, cache_write_tokens, stop_reason, thinking_enabled,
            request_json, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (key, namespace, domain, created_at, model,
         int(usage.get("input_tokens", 0) or 0),
         int(usage.get("output_tokens", 0) or 0),
         int(usage.get("cache_read_tokens", 0) or 0),
         int(usage.get("cache_write_tokens", 0) or 0),
         stop_reason, 1 if thinking_enabled else 0, request_json, raw_json),
    )
    conn.commit()


def _log_access(conn, *, ts, key, domain, hit, run_label) -> None:
    conn.execute(
        "INSERT INTO access_log (ts, key, domain, hit, run_label) VALUES (?,?,?,?,?)",
        (ts, key, domain, 1 if hit else 0, run_label),
    )
    conn.commit()


def _reconstruct(raw_json: str):
    """Reconstruye el objeto SDK real desde el crudo guardado. Devolver el MISMO tipo
    (anthropic.types.Message) que un miss es lo que hace que hit y miss tengan idéntica
    forma e idéntico acceso por atributo aguas arriba (resp.usage.x, resp.content[i].y).
    Importado adentro para no exigir anthropic salvo cuando hay un hit que reconstruir."""
    from anthropic.types import Message
    return Message.model_validate(json.loads(raw_json))


def _usage_fields(resp) -> dict:
    """Extrae los 4 campos de tokens del usage crudo, robusto a ausencias/None."""
    u = getattr(resp, "usage", None)
    g = lambda name: int(getattr(u, name, 0) or 0) if u is not None else 0
    return {
        "input_tokens": g("input_tokens"),
        "output_tokens": g("output_tokens"),
        "cache_read_tokens": g("cache_read_input_tokens"),
        "cache_write_tokens": g("cache_creation_input_tokens"),
    }


# --------------------------------------------------------------------------- #
# Cliente cacheante (imita .messages.create del SDK)                          #
# --------------------------------------------------------------------------- #
class CachingClient:
    """Wrapper drop-in alrededor de un cliente Anthropic (o de un RetryingClient).
    La caché va POR FUERA del retry: un hit ni siquiera entra a la red.

    Uso:
        real     = anthropic.Anthropic()
        retrying = RetryingClient(real, log=...)        # clase existente, intacta
        cache    = CachingClient(retrying, domain="agent",
                                 namespace=make_namespace("agent", code_ver=cv,
                                                          graph_fp=gfp, thinking=THINK),
                                 db_path=DEFAULT_DB_PATH, run_label="posthoc_off")
        agent    = GraphAgent(kg, client=cache)         # drop-in: tiene .messages.create
    """

    def __init__(self, real_client, *, namespace: str, db_path: Path = DEFAULT_DB_PATH,
                 domain: str = "", thinking_enabled: bool = False,
                 run_label: str | None = None, record_access: bool = True):
        self._real = real_client
        self.namespace = namespace
        self.domain = domain
        self.thinking_enabled = thinking_enabled
        self.run_label = run_label
        self.record_access = record_access
        self._conn = _connect(Path(db_path))
        self.messages = _CachingMessages(self)
        # contadores en memoria de ESTA corrida (complemento al access_log persistente)
        self._stats = {
            "hits": 0, "misses": 0,
            "tokens_in": 0, "tokens_out": 0,
            "cache_read": 0, "cache_write": 0,
        }

    # --- contabilidad ---
    def _count(self, *, hit: bool, usage: dict) -> None:
        self._stats["hits" if hit else "misses"] += 1
        self._stats["tokens_in"] += usage.get("input_tokens", 0)
        self._stats["tokens_out"] += usage.get("output_tokens", 0)
        self._stats["cache_read"] += usage.get("cache_read_tokens", 0)
        self._stats["cache_write"] += usage.get("cache_write_tokens", 0)

    def stats(self) -> dict:
        s = dict(self._stats)
        total = s["hits"] + s["misses"]
        s["accesses"] = total
        s["hit_rate"] = round(s["hits"] / total, 4) if total else 0.0
        s["domain"] = self.domain
        s["namespace"] = self.namespace
        return s

    def close(self) -> None:
        self._conn.close()


class _CachingMessages:
    """Espeja client.messages: solo expone create(**kwargs)."""

    def __init__(self, owner: CachingClient):
        self._o = owner

    def create(self, **kwargs):
        o = self._o
        canonical = canonical_request(kwargs)
        key = compute_key(o.namespace, canonical)

        row = _lookup(o._conn, key)
        if row is not None:
            # --- HIT: reconstruir y devolver; no toca la red ni el retry ---
            resp = _reconstruct(row["raw_json"])
            usage = {
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "cache_read_tokens": row["cache_read_tokens"],
                "cache_write_tokens": row["cache_write_tokens"],
            }
            o._count(hit=True, usage=usage)
            if o.record_access:
                _log_access(o._conn, ts=datetime.now().isoformat(), key=key,
                            domain=o.domain, hit=True, run_label=o.run_label)
            return resp

        # --- MISS: llamar al cliente real (que reintenta infra), capturar y guardar ---
        resp = o._real.messages.create(**kwargs)   # si falla, propaga: NO se cachea el error
        raw = resp.model_dump(mode="json")          # crudo íntegro ANTES de cualquier recorte
        usage = _usage_fields(resp)
        # WRITE-THROUGH: persistir antes de devolver, para que un kill no pierda lo pagado.
        _store(o._conn, key=key, namespace=o.namespace, domain=o.domain,
               created_at=datetime.now().isoformat(),
               model=getattr(resp, "model", kwargs.get("model", "")),
               usage=usage, stop_reason=getattr(resp, "stop_reason", None),
               thinking_enabled=o.thinking_enabled,
               request_json=canonical,
               raw_json=json.dumps(raw, ensure_ascii=False))
        o._count(hit=False, usage=usage)
        if o.record_access:
            _log_access(o._conn, ts=datetime.now().isoformat(), key=key,
                        domain=o.domain, hit=False, run_label=o.run_label)
        return resp
