"""Extractor de tripletas por chunk usando Claude Haiku 4.5 con schema cerrado — v2.

Cambios v2 (spec_extraccion_v2.md §4.2) sobre el extractor de run_3:
- El sujeto de aplica_a/ejecuta se ELIGE del catálogo (sujeto_id con enum duro
  en el tool schema); fuera de catálogo → sujeto_propuesto (cuarentena).
- SYSTEM_PROMPT con catálogo compacto interpolado; mensaje de usuario con la
  lista de alcance del TO del chunk (rol por-TO).
- Caché en cache_v2/ y key de chunk con sha256(SYSTEM_PROMPT)[:12] — doble
  candado contra hits del prompt viejo.
- Tracker: cache-hit no suma tokens ni costo (fix del double-count).

Aprendizajes Run 1 + Run 2 heredados:
- Concurrency=2 para evitar 429 en Haiku 4.5 tier 1.
- Backoff conservador; cache por chunk individual (reanudable, NO se cachea error).
- ProgressTracker imprime cada 5 chunks con flush=True + costo acumulado + ETA.

Uso:
    python extract.py smoke      # corre solo TO Protección al Usuario
    python extract.py full       # corre los 5 TOs completos
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic, APIStatusError, APIConnectionError, RateLimitError
from pydantic import ValidationError

from chunker import Chunk, SUBSET, chunk_pdf, chunk_all, save_chunks, load_chunks
from schema import (
    ENTITY_TYPES,
    PREDICATES,
    DOMAIN_RANGE,
    SUJETOS_CATALOGO,
    SUJETOS_PROMPT,
    ROL_POR_TO,
    CATALOGO_VERSION,
    ExtractionOut,
    filter_extraction,
    empty_metrics,
    merge_metrics,
)


# === CONFIG ===

MODEL = "claude-haiku-4-5-20251001"
CONCURRENCY = 2                  # bajado a 2 (Run 2 lección 4): TPM Haiku 4.5 tier 1
MAX_RETRIES = 6                  # subido a 6: overload 529 necesita esperas más largas que rate-limit 429
BACKOFF_BASE = 2.0               # Run 2 lección 4: base 2.0 para 429
OVERLOAD_BACKOFF_BASE = 3.0      # base más agresiva para 529 (Anthropic Overloaded)
MAX_OUTPUT_TOKENS = 8192  # Haiku 4.5 absolute max

# Precios Claude Haiku 4.5 con prompt caching (per MTok) — vigentes a fecha del experimento
PRICE_IN_PER_MTOK = 1.00
PRICE_CACHE_WRITE_PER_MTOK = 1.25
PRICE_CACHE_READ_PER_MTOK = 0.10
PRICE_OUT_PER_MTOK = 5.00

# Caché v2: SIEMPRE bajo grafo_v2/code/cache_v2/ — nunca el cache viejo de run_3
# (spec §4.2: doble candado; el otro candado es PROMPT_HASH en la key del chunk).
CACHE_ROOT_V2 = Path(__file__).resolve().parent / "cache_v2"

# Registro de usage por request (instrumentación de prompt caching de Anthropic).
# Una línea JSON por response real de la API; logs/ está ignorado por git.
REPO_ROOT = Path(__file__).resolve().parents[4]
CACHE_USAGE_LOG = REPO_ROOT / "logs" / "cache_usage.jsonl"


# === SYSTEM PROMPT ===
# Lecciones Run 1 + Run 2: incluir regla anti-jerarquía explícita + ejemplos.

SYSTEM_PROMPT = f"""Sos un extractor de tripletas para un Knowledge Graph regulatorio del BCRA (Banco Central de la República Argentina).

Trabajás con un schema CERRADO y RÍGIDO. NO inventes tipos. NO inventes predicados.

# TIPOS DE ENTIDAD VÁLIDOS (exactamente 6, ningún otro)

Los SUJETOS (entidades financieras, casas de cambio, clientes, organismos, etc.) NO son un tipo de entidad: NO crees entidades para ellos. El sujeto se elige de un CATÁLOGO CERRADO dentro de las relaciones aplica_a/ejecuta (ver sección SUJETOS).

1. **Comunicacion**: Una Comunicación A/B/C del BCRA citada en el texto. Ej.: "Com. A 7825", "Comunicación A 7000".
   Properties: codigo (string, ej. "A-7825"), tipo ("A"|"B"|"C"), numero (int).

2. **TextoOrdenado**: El TO consolidado del cual sale el chunk. SIEMPRE incluir un único TextoOrdenado por chunk, derivado del documento fuente. Label = nombre conceptual del TO (ej. "Texto Ordenado de Protección de Usuarios").
   Properties: materia, archivo, version.

3. **Operacion**: Un acto regulado: financiación, depósito, transferencia, compra/venta de moneda extranjera, clasificación de deudor, presentación informativa, etc.
   Properties: tipo (string).

4. **Restriccion**: Una prohibición o límite cuantitativo/cualitativo. Patrones: "no podrá", "se prohíbe", "el monto no excederá", "el límite es".
   Properties: descripcion (corta, grounded), tipo ("prohibicion"|"limite_cuantitativo"|"limite_cualitativo"), opcional umbral.

5. **Excepcion**: Una condición que suspende/relaja una Restricción u Obligación. Patrones: "salvo", "excepto", "no aplicará cuando", "están exceptuadas".
   Properties: descripcion (corta).

6. **Obligacion**: Un deber positivo. "Deberán presentar", "calcularán", "asignarán", "informarán". Distinto de Restricción.
   Properties: descripcion (corta), tipo ("presentacion_informativa"|"calculo"|"asignacion"|"comunicacion_a_cliente"|"otra"), opcional plazo o frecuencia.

# PREDICADOS VÁLIDOS (exactamente 12, ningún otro)

Cada predicado tiene DOMINIO y RANGO estrictos. Si la dirección o los tipos no coinciden, la tripleta se DESCARTA.

| Predicado | Dominio → Rango |
|---|---|
| `establecida_en` | {{Restriccion, Obligacion, Excepcion, Operacion}} → TextoOrdenado |
| `referencia` | TextoOrdenado → Comunicacion |
| `modificada_por` | TextoOrdenado → Comunicacion |
| `aplica_a` | {{Restriccion, Obligacion}} → SUJETO del catálogo (source = local_id de la norma; el sujeto va en sujeto_id o sujeto_propuesto, SIN target) |
| `regula` | {{Restriccion, Obligacion}} → Operacion |
| `exceptua` | Excepcion → Restriccion |
| `exceptua_obligacion` | Excepcion → Obligacion |
| `prohibe` | Restriccion → Operacion (USAR cuando Restriccion.tipo = "prohibicion") |
| `limita` | Restriccion → Operacion (USAR cuando Restriccion.tipo = "limite_cuantitativo" o "limite_cualitativo") |
| `ejecuta` | SUJETO del catálogo → Operacion (target = local_id de la operación; el sujeto va en sujeto_id o sujeto_propuesto, SIN source) |
| `requiere` | Operacion → Obligacion |
| `condiciona` | Obligacion → Operacion |

# SUJETOS: CATÁLOGO CERRADO (para aplica_a y ejecuta)

El sujeto de una relación `aplica_a` o `ejecuta` se ELIGE del catálogo de abajo — NO se crea:

- Poné en `sujeto_id` el id EXACTO de la entrada del catálogo que el texto nombra (matcheá por label o por alias).
- Si el punto nombra uno o más sujetos ESPECÍFICOS, emití UNA relación por CADA sujeto nombrado, usando la clase del catálogo que corresponde a ese nombre.
  ✓ "Las entidades financieras, los PSPCP y las empresas emisoras deberán informar..." → 3 relaciones aplica_a, con sujeto_id "Sujeto_entidad_financiera", "Sujeto_pspcp" y "Sujeto_empresa_no_financiera_emisora_de_tarjetas".
  ✗ MAL: una única relación hacia el rol del TO cuando el texto enumera sujetos con nombre propio.
- Usá EXACTAMENTE la clase que el texto nombra: NUNCA una más específica ni una más general. La jerarquía del grafo se ocupa de la herencia; tu trabajo es fidelidad al texto.
  ✓ el texto dice "las entidades financieras" → sujeto_id "Sujeto_entidad_financiera".
  ✗ MAL: el texto dice "las entidades financieras" y emitís "Sujeto_banco" o "Sujeto_banco_comercial" (descenso de jerarquía sin licencia del texto).
  ✗ MAL: el texto dice "los bancos comerciales" y emitís "Sujeto_entidad_financiera" (ascenso: más general que lo que el texto nombra).
- Si la norma se dirige al colectivo del TO ("las entidades", "los sujetos obligados"), usá el rol de alcance indicado en el mensaje del chunk.
- Si el texto nombra un sujeto que NO matchea ninguna entrada del catálogo ni sus alias, usá `sujeto_propuesto` (texto libre con el nombre del sujeto tal como aparece) y, si podés, `sujeto_propuesto_padre_sugerido` con el id del catálogo más cercano como padre. NO fuerces el id más parecido: ante la duda, proponé.
- `sujeto_id` y `sujeto_propuesto` son MUTUAMENTE EXCLUYENTES: exactamente uno de los dos.
- Los sujetos "del exterior" NO son entradas propias: usá la clase local correspondiente (la jurisdicción es un atributo, ya contemplado en los alias).

{SUJETOS_PROMPT}

# REGLAS NO NEGOCIABLES

1. **Los nodos NO son jerarquía documental.** NO crees entidades de tipo "Artículo", "Punto", "Sección", "Capítulo", "Inciso". Si el texto dice "Artículo 12. Las entidades financieras no podrán...", la entidad es la RESTRICCIÓN ("las entidades no podrán..."), no el "Artículo 12". El "Artículo 12" va a `provenance.location` (manejado fuera del LLM).

2. **Cada entidad debe tener un `local_id` único dentro del chunk** (ej. "e1", "e2", "e3"). Las relations usan esos local_ids como source/target.

3. **Las relations son SOLO entre entidades del MISMO chunk.** No referencies entidades externas.

4. **NO inventes tipos ni predicados fuera de las listas.** Si una idea no encaja en los 6 tipos de entidad o 12 predicados, NO la incluyas. Es preferible no extraer algo a forzarlo en una caja equivocada.

5. **`label` corto y canónico; la oración del texto va en `properties.description`.** ESTA REGLA ES CRÍTICA — leer con atención.

   Para Obligacion, Restriccion, Excepcion y Operacion:
   - `label`: nombre CANÓNICO de la entidad. Máximo **8 palabras**. Verbo + objeto directo, o sustantivo + modificador. NO copies la oración del corpus.
   - `properties.description`: la oración o cita textual del corpus (acá va el contenido largo, sin tope de palabras).
   - Si dudás entre dos formulaciones para el label, elegí la **más nominal** y la **más corta**.

   Para Comunicacion: `label` es el código corto ("Com. A 7825"). NUNCA copies texto de la comunicación al label.

   Para TextoOrdenado: `label` es el nombre conceptual corto ("Protección al Usuario", "Capitales Mínimos", "Exterior y Cambios"). Máximo 5 palabras.

   Ejemplos correctos:
   ✓ Obligacion label: "Informar comisiones al BCRA" / description: "El sujeto obligado deberá informar mensualmente al BCRA todas las comisiones cobradas por cuenta de terceros..."
   ✓ Restriccion label: "Prohibición de cobro diferencial por discapacidad" / description: "No se podrán cobrar comisiones y/o cargos diferenciales a usuarios con dificultades visuales por prestaciones especiales"
   ✓ Operacion label: "Solicitud de financiación" / description: "Solicitud de financiación presentada por un usuario al sujeto obligado"

   Ejemplos INCORRECTOS (NO hacer):
   ✗ Obligacion label: "La Gerencia Principal brindará respuesta a consultas del público sobre normativa e información institucional" (108 chars — copia la oración)
   ✗ Restriccion label: "no se podrá reflejar o promover visiones estereotipadas y jerarquizantes de los géneros, androcentrismo, lenguaje sexista..." (>180 chars — copia textual)

6. **Siempre incluí un nodo TextoOrdenado con local_id "to" en CADA chunk** (representando el TO del que sale el chunk). Luego conectá las Restriccion/Obligacion/Excepcion del chunk al nodo TextoOrdenado vía `establecida_en`. El label del TextoOrdenado debe ser corto (ver regla 5).

7. **Enumeraciones de sujetos: UNA RELACIÓN POR SUJETO.** Si el texto enumera varios sujetos alcanzados (separados por comas, "y", "o", "u otros"), generá una relación `aplica_a` (o `ejecuta`) POR CADA sujeto, cada una con su propio sujeto_id del catálogo. NO metas la enumeración entera en un solo sujeto_propuesto.

   Ejemplo del corpus: "...aplica a entidades financieras, PSPCP y PSI..."
   - Generar 3 relaciones aplica_a independientes desde la misma norma:
     * sujeto_id: "Sujeto_entidad_financiera"
     * sujeto_id: "Sujeto_pspcp"
     * sujeto_id: "Sujeto_psi_billetera_digital"

   ✗ NO: 1 relación con sujeto_propuesto "Entidades financieras, PSPCP y PSI"
   ✓ SÍ: 3 relaciones separadas, cada una con su sujeto_id.

# EJEMPLOS NEGATIVOS (qué NO hacer)

- ❌ Entidad de tipo "Artículo" → usá Restriccion/Obligacion según corresponda. El número de artículo va en provenance.
- ❌ Predicado "regulado_por" o "contiene" o "se_aplica_si" → no están en la lista de 12.
- ❌ Restriccion --aplica_a--> Operacion → MAL, `aplica_a` requiere un SUJETO del catálogo como rango (sujeto_id). Usá `regula` o `prohibe`/`limita`.
- ❌ Restriccion --exceptua--> Operacion → MAL, `exceptua` requiere Excepcion como dominio y Restriccion como rango.
- ❌ Entidad de tipo "EntidadFinanciera" o "Sujeto" → los sujetos NO son entidades del chunk: van en sujeto_id/sujeto_propuesto de aplica_a/ejecuta.
- ❌ sujeto_id "Sujeto_entidad_financiera" para "empresas de seguros" → si el sujeto no matchea entrada ni alias del catálogo, usá sujeto_propuesto; NO fuerces el más parecido.
- ❌ Texto plano "Punto 3.2.1." como entidad → es jerarquía documental, va en provenance.

# REGLA `regula` / `prohibe` / `limita` (importante)

Tres predicados Restriccion→Operacion. NO son intercambiables. Elegí según `Restriccion.tipo`:

- Si `Restriccion.tipo = "prohibicion"` → usá `prohibe`. Patrón: "no podrá", "se prohíbe", "queda prohibido". Ejemplo: una restricción que dice "no se podrá cobrar comisiones por X" prohíbe la operación "cobrar comisiones".
- Si `Restriccion.tipo = "limite_cuantitativo"` (hay umbral numérico: %, $, monto) → usá `limita`. Ejemplo: una restricción "alcanzar cobertura mínima del 10%" limita la operación "cobertura de cajeros" con umbral 10%.
- Si `Restriccion.tipo = "limite_cualitativo"` (hay restricción cualitativa sin monto) → usá `limita`. Ejemplo: "deberán operar exclusivamente con entidades autorizadas" limita la operación.
- `regula` queda RESERVADO para Obligacion→Operacion (NO para Restriccion→Operacion). Cuando una Obligacion regula cómo se hace una Operacion, usá `regula`.

✅ Restriccion(tipo=prohibicion) --prohibe--> Operacion
✅ Restriccion(tipo=limite_cuantitativo, umbral="10%") --limita--> Operacion
✅ Restriccion(tipo=limite_cualitativo) --limita--> Operacion
✅ Obligacion --regula--> Operacion
❌ Restriccion(tipo=limite_cuantitativo) --regula--> Operacion  ← MAL, usá `limita`
❌ Restriccion(tipo=prohibicion) --regula--> Operacion  ← MAL, usá `prohibe`

# FORMATO DE SALIDA

Llamá la herramienta `extract_kg_triples` con el schema dado. Si el chunk no tiene contenido normativo extraíble (preámbulo vacío, lista de abreviaturas, etc.), devolvé entities y relations vacíos.
"""


# === TOOL DEFINITION (extract_kg_triples) ===

TOOL_SCHEMA = {
    "name": "extract_kg_triples",
    "description": "Extrae entidades y relaciones del chunk según el schema cerrado de 6 entidades y 12 predicados. El sujeto de aplica_a/ejecuta se elige del catálogo cerrado (sujeto_id) o se propone para cuarentena (sujeto_propuesto).",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "local_id": {"type": "string", "description": "Identificador local único dentro del chunk."},
                        "type": {"type": "string", "enum": list(ENTITY_TYPES)},
                        "label": {"type": "string", "description": "Etiqueta legible humana, grounded en el texto."},
                        "properties": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Properties de la entidad. Ver definición de cada tipo.",
                        },
                    },
                    "required": ["local_id", "type", "label"],
                    "additionalProperties": False,
                },
            },
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "local_id de la entidad source. En aplica_a: la norma (Restriccion/Obligacion). NO usar en ejecuta (el sujeto va en sujeto_id/sujeto_propuesto)."},
                        "target": {"type": "string", "description": "local_id de la entidad target. En ejecuta: la Operacion. NO usar en aplica_a (el sujeto va en sujeto_id/sujeto_propuesto)."},
                        "predicate": {"type": "string", "enum": list(PREDICATES)},
                        "sujeto_id": {
                            "type": "string",
                            "enum": list(SUJETOS_CATALOGO),
                            "description": "SOLO aplica_a/ejecuta: id exacto del catálogo de sujetos. Mutuamente excluyente con sujeto_propuesto.",
                        },
                        "sujeto_propuesto": {
                            "type": "string",
                            "description": "SOLO aplica_a/ejecuta: nombre del sujeto tal como aparece en el texto, cuando NO matchea ninguna entrada del catálogo ni sus alias. Mutuamente excluyente con sujeto_id.",
                        },
                        "sujeto_propuesto_padre_sugerido": {
                            "type": "string",
                            "enum": list(SUJETOS_CATALOGO),
                            "description": "Opcional junto a sujeto_propuesto: id del catálogo sugerido como padre del sujeto propuesto.",
                        },
                    },
                    "required": ["predicate"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["entities", "relations"],
        "additionalProperties": False,
    },
}


# === PROGRESS TRACKER ===

@dataclass
class ProgressTracker:
    total: int
    completed: int = 0
    failed: int = 0
    throttled: int = 0
    total_in_tokens: int = 0
    total_out_tokens: int = 0
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0
    t_start: float = 0.0
    last_window_t: float = 0.0
    last_window_completed: int = 0
    print_every: int = 5

    def start(self) -> None:
        self.t_start = time.time()
        self.last_window_t = self.t_start

    @property
    def cost_usd(self) -> float:
        # Costo real con prompt caching: input_tokens excluye los tokens
        # cacheados, que se cobran aparte (write 1.25x, read 0.10x).
        return (
            self.total_in_tokens / 1_000_000 * PRICE_IN_PER_MTOK
            + self.total_cache_write_tokens / 1_000_000 * PRICE_CACHE_WRITE_PER_MTOK
            + self.total_cache_read_tokens / 1_000_000 * PRICE_CACHE_READ_PER_MTOK
            + self.total_out_tokens / 1_000_000 * PRICE_OUT_PER_MTOK
        )

    def tick(
        self,
        in_tok: int,
        out_tok: int,
        fail: bool,
        throttled: int,
        cache_write_tok: int = 0,
        cache_read_tok: int = 0,
    ) -> None:
        self.completed += 1
        self.total_in_tokens += in_tok
        self.total_out_tokens += out_tok
        self.total_cache_write_tokens += cache_write_tok
        self.total_cache_read_tokens += cache_read_tok
        if fail:
            self.failed += 1
        self.throttled += throttled

        if self.completed % self.print_every == 0 or self.completed == self.total:
            now = time.time()
            dt = now - self.last_window_t
            window_n = self.completed - self.last_window_completed
            rate = window_n / dt if dt > 0 else 0.0
            elapsed = now - self.t_start
            remaining = self.total - self.completed
            eta_sec = remaining / rate if rate > 0 else float("inf")
            eta_min = eta_sec / 60.0
            pct = self.completed / self.total * 100
            print(
                f"[{self.completed:4d}/{self.total}] {pct:5.1f}% | "
                f"in={self.total_in_tokens:>9,} out={self.total_out_tokens:>8,} | "
                f"${self.cost_usd:6.3f} | "
                f"{rate*60:5.1f}/min | "
                f"throt={self.throttled} fail={self.failed} | "
                f"ETA {eta_min:5.1f}min",
                flush=True,
            )
            self.last_window_t = now
            self.last_window_completed = self.completed


# === EXTRACTOR ===

# Candado 2 del caché (spec §4.2): la key del chunk incorpora el hash del
# SYSTEM_PROMPT. Cambia el prompt → cambian TODAS las keys → cero hits stale.
# (Trampa documentada del caché v1: se indexaba por chunk_id|texto sin prompt.)
PROMPT_HASH = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]


def chunk_cache_path(chunk: Chunk, cache_root: Path, prompt_hash: str | None = None) -> Path:
    """Path de cache para un chunk individual. Hash determinístico de
    id+texto+hash(SYSTEM_PROMPT)."""
    ph = prompt_hash if prompt_hash is not None else PROMPT_HASH
    h = hashlib.sha1(f"{chunk.chunk_id}|{chunk.text}|{ph}".encode("utf-8")).hexdigest()[:12]
    safe = chunk.chunk_id.replace("/", "_").replace("::", "__")[:80]
    return cache_root / f"{safe}__{h}.json"


def log_cache_usage(usage: Any, component: str, doc: str | None = None) -> None:
    """Appendea a logs/cache_usage.jsonl los campos de usage de una response,
    identificando componente y (si aplica) documento."""
    CACHE_USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "doc": doc,
        "input_tokens": getattr(usage, "input_tokens", None),
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
    with CACHE_USAGE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def build_user_message(chunk: Chunk) -> str:
    """Mensaje de usuario por chunk. v2: interpola la lista de alcance del TO
    del chunk (rol por-TO del catálogo) — mata la contaminación de vocabulario
    de raíz (spec §4.2)."""
    rol = ROL_POR_TO.get(chunk.doc)
    if rol is not None:
        miembros = ", ".join(rol["miembros_labels"])
        alcance = (
            f"Alcance de este TO: {rol['rol_id']} = {{{miembros}}}. "
            f"Cuando la norma se dirija genéricamente a 'las entidades' / 'los sujetos obligados' / "
            f"el colectivo del TO, usá {rol['rol_id']} como sujeto.\n\n"
        )
    else:
        # No debería ocurrir con los 5 TOs del subset; se degrada sin romper.
        alcance = ""
    return (
        f"Documento fuente: {chunk.doc}\n"
        f"Ubicación: {chunk.location}\n\n"
        f"{alcance}"
        f"Texto del chunk:\n```\n{chunk.text}\n```\n\n"
        f"Extraé las entidades y relaciones según el schema. Recordá incluir el nodo TextoOrdenado con local_id='to'."
    )


async def extract_one(
    client: AsyncAnthropic,
    chunk: Chunk,
    cache_root: Path,
    semaphore: asyncio.Semaphore,
    progress: ProgressTracker,
    model: str = MODEL,
) -> dict[str, Any]:
    """Extrae un chunk, con cache + retry. Devuelve el dict del resultado."""
    cache_path = chunk_cache_path(chunk, cache_root)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("error") is None:
                # Cache hit válido. NO sumar tokens ni costo (spec §4.2: fix
                # del double-count — los tokens cacheados no se re-pagan).
                progress.tick(in_tok=0, out_tok=0, fail=False, throttled=0)
                return cached
            # Error cacheado: re-intentar (Run 2 lección 5)
        except Exception:
            pass  # cache corrupto, re-extraer

    user_message = build_user_message(chunk)

    last_err: str | None = None
    in_tok = 0
    out_tok = 0
    cache_write_tok = 0
    cache_read_tok = 0
    throttle_events = 0

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.messages.create(
                    model=model,
                    max_tokens=MAX_OUTPUT_TOKENS,
                    # Prompt caching de Anthropic: breakpoint explícito en el último
                    # bloque del prefijo estático (tools + system quedan cacheados;
                    # todo lo variable por chunk va en el mensaje de usuario, después
                    # del breakpoint). TTL default de 5 min (sin campo ttl): cada hit
                    # refresca el TTL sin costo en corridas continuas.
                    system=[
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    tools=[TOOL_SCHEMA],
                    tool_choice={"type": "tool", "name": "extract_kg_triples"},
                    messages=[{"role": "user", "content": user_message}],
                )
                log_cache_usage(resp.usage, component="extraccion_v2", doc=chunk.doc)
                in_tok = resp.usage.input_tokens
                out_tok = resp.usage.output_tokens
                # None cuenta como 0 (responses sin caching siguen costeando bien).
                cache_write_tok = getattr(resp.usage, "cache_creation_input_tokens", None) or 0
                cache_read_tok = getattr(resp.usage, "cache_read_input_tokens", None) or 0

                tool_use = None
                text_blocks: list[str] = []
                for block in resp.content:
                    btype = getattr(block, "type", None)
                    if btype == "tool_use":
                        tool_use = block
                        break
                    if btype == "text":
                        text_blocks.append(getattr(block, "text", ""))

                stop_reason = getattr(resp, "stop_reason", None)
                if stop_reason == "max_tokens":
                    last_err = f"max_tokens_hit in={in_tok} out={out_tok} chunk_chars={len(chunk.text)}"
                    print(f"  [MAX_TOKENS_HIT] {chunk.chunk_id}: in={in_tok} out={out_tok} chars={len(chunk.text)} → CHUNK DEMASIADO GRANDE", flush=True)
                    break

                if tool_use is None:
                    text_preview = (" | ".join(text_blocks))[:300]
                    last_err = f"no_tool_use stop_reason={stop_reason} text={text_preview!r}"
                    print(f"  [no_tool_use] {chunk.chunk_id}: stop_reason={stop_reason} | text_preview={text_preview!r}", flush=True)
                    break  # no es recuperable con retry

                try:
                    parsed = ExtractionOut.model_validate(tool_use.input)
                except ValidationError as ve:
                    last_err = f"pydantic_validation: {str(ve)[:200]}"
                    print(f"  [pydantic_invalid] {chunk.chunk_id}: {str(ve)[:200]}", flush=True)
                    break

                filtered, val_metrics = filter_extraction(parsed)

                result = {
                    "chunk_id": chunk.chunk_id,
                    "doc": chunk.doc,
                    "location": chunk.location,
                    "entities": [e.model_dump() for e in filtered.entities],
                    "relations": [r.model_dump() for r in filtered.relations],
                    "in_tokens": in_tok,
                    "out_tokens": out_tok,
                    "validation": val_metrics,
                    "error": None,
                }
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                progress.tick(
                    in_tok=in_tok,
                    out_tok=out_tok,
                    fail=False,
                    throttled=throttle_events,
                    cache_write_tok=cache_write_tok,
                    cache_read_tok=cache_read_tok,
                )
                return result

            except RateLimitError as e:
                throttle_events += 1
                wait = (BACKOFF_BASE ** attempt) + 0.5
                print(f"  [throttle] {chunk.chunk_id} attempt {attempt+1}/{MAX_RETRIES}: 429, waiting {wait:.1f}s", flush=True)
                await asyncio.sleep(wait)
                last_err = f"rate_limit: {e}"
            except APIStatusError as e:
                if e.status_code == 529:
                    # Anthropic Overloaded — backoff agresivo con jitter, capeado a 60s
                    throttle_events += 1
                    wait = min(60.0, (OVERLOAD_BACKOFF_BASE ** attempt) + random.uniform(0.5, 2.5))
                    print(f"  [529 overloaded] {chunk.chunk_id} attempt {attempt+1}/{MAX_RETRIES}: waiting {wait:.1f}s", flush=True)
                    await asyncio.sleep(wait)
                    last_err = f"api_529_overloaded: {e}"
                elif e.status_code and e.status_code >= 500:
                    wait = (BACKOFF_BASE ** attempt) + 0.5
                    print(f"  [{e.status_code}] {chunk.chunk_id} attempt {attempt+1}: waiting {wait:.1f}s", flush=True)
                    await asyncio.sleep(wait)
                    last_err = f"api_{e.status_code}: {e}"
                else:
                    last_err = f"api_{e.status_code}: {e}"
                    break
            except APIConnectionError as e:
                wait = (BACKOFF_BASE ** attempt) + 0.5
                print(f"  [conn] {chunk.chunk_id} attempt {attempt+1}: waiting {wait:.1f}s", flush=True)
                await asyncio.sleep(wait)
                last_err = f"connection: {e}"
            except Exception as e:
                last_err = f"unexpected: {type(e).__name__}: {e}"
                print(f"  [unexpected] {chunk.chunk_id}: {last_err}", flush=True)
                break

    # Si llegó acá: falló. NO cachear (Run 2 lección 5).
    progress.tick(
        in_tok=in_tok,
        out_tok=out_tok,
        fail=True,
        throttled=throttle_events,
        cache_write_tok=cache_write_tok,
        cache_read_tok=cache_read_tok,
    )
    return {
        "chunk_id": chunk.chunk_id,
        "doc": chunk.doc,
        "location": chunk.location,
        "entities": [],
        "relations": [],
        "in_tokens": in_tok,
        "out_tokens": out_tok,
        "validation": empty_metrics(),
        "error": last_err or "unknown",
    }


async def extract_chunks(chunks: list[Chunk], cache_root: Path, model: str = MODEL) -> list[dict[str, Any]]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no está set en el environment.")

    client = AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    cached_ok = 0
    for c in chunks:
        cp = chunk_cache_path(c, cache_root)
        if cp.exists():
            try:
                d = json.loads(cp.read_text(encoding="utf-8"))
                if d.get("error") is None:
                    cached_ok += 1
            except Exception:
                pass
    if cached_ok > 0:
        print(f"Cache: {cached_ok}/{len(chunks)} chunks ya cacheados (skipping).", flush=True)

    progress = ProgressTracker(total=len(chunks))
    progress.start()

    tasks = [
        extract_one(client, c, cache_root, semaphore, progress, model=model)
        for c in chunks
    ]
    results = await asyncio.gather(*tasks)

    elapsed_min = (time.time() - progress.t_start) / 60.0
    print(
        f"\nDONE — completed={progress.completed} failed={progress.failed} "
        f"throttled={progress.throttled} in_tok={progress.total_in_tokens:,} "
        f"out_tok={progress.total_out_tokens:,} cost=${progress.cost_usd:.3f} "
        f"elapsed={elapsed_min:.1f}min",
        flush=True,
    )
    return results


def main() -> int:
    # --model <id> opcional (B1a): el modelo pasa a ser parámetro; default el actual.
    argv = list(sys.argv[1:])
    model = MODEL
    if "--model" in argv:
        i = argv.index("--model")
        if i + 1 >= len(argv):
            print("Uso: --model requiere un id de modelo")
            return 1
        model = argv[i + 1]
        del argv[i:i + 2]

    valid_modes = ("smoke", "full", "one")
    if len(argv) < 1 or argv[0] not in valid_modes:
        print("Uso: python extract.py {smoke | full | one <doc_substring>} [--model <id>]")
        return 1

    mode = argv[0]

    if mode == "smoke":
        pdf = SUBSET / "TO_proteccion_usuarios_servicios_financieros_actual.pdf"
        chunks = chunk_pdf(pdf)
        cache_root = CACHE_ROOT_V2 / "smoke"
        save_chunks(chunks, CACHE_ROOT_V2 / "chunks_smoke.json")
    elif mode == "one":
        if len(argv) < 2:
            print("Uso: python extract.py one <doc_substring> [--model <id>]")
            return 1
        substr = argv[1]
        pdfs = sorted(p for p in SUBSET.glob("*.pdf") if substr in p.name)
        if len(pdfs) != 1:
            print(f"Match ambiguo o nulo para '{substr}': {[p.name for p in pdfs]}")
            return 1
        chunks = chunk_pdf(pdfs[0])
        cache_root = CACHE_ROOT_V2 / "full"  # comparte cache con full (acumulativo)
        # No sobreescribimos chunks_all.json acá; usamos uno temporal por TO
        save_chunks(chunks, CACHE_ROOT_V2 / f"chunks_one_{pdfs[0].stem}.json")
        print(f"Modo one: procesando solo {pdfs[0].name} ({len(chunks)} chunks)", flush=True)
    else:  # full
        pdfs = sorted(SUBSET.glob("*.pdf"))
        chunks = chunk_all(pdfs)
        cache_root = CACHE_ROOT_V2 / "full"
        save_chunks(chunks, CACHE_ROOT_V2 / "chunks_all.json")

    if model != MODEL:
        # La key de caché NO incluye el modelo: correr smoke/full/one con otro
        # modelo contaminaría cache_v2/{smoke,full}. Las corridas multi-modelo
        # van por correr_piloto.py, que namespacea cache_v2/piloto/<modelo>/.
        print(f"ERROR: {mode} con modelo no-default ({model}) contaminaría {cache_root}. Usá correr_piloto.py.")
        return 1

    cache_root.mkdir(parents=True, exist_ok=True)
    print(
        f"Mode: {mode} | model: {model} | chunks: {len(chunks)} | cache_root: {cache_root} | "
        f"catalogo v{CATALOGO_VERSION} ({len(SUJETOS_CATALOGO)} sujetos) | prompt_hash={PROMPT_HASH}",
        flush=True,
    )

    results = asyncio.run(extract_chunks(chunks, cache_root, model=model))

    # Volcar resumen
    summary = {
        "mode": mode,
        "n_chunks": len(chunks),
        "n_results": len(results),
        "n_failed": sum(1 for r in results if r.get("error")),
        "n_entities_total": sum(len(r["entities"]) for r in results),
        "n_relations_total": sum(len(r["relations"]) for r in results),
    }
    print("\nResumen:", json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
