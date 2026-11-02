"""
juez.py — Juez de fidelidad EV2 (pre-registro docs/preregistro_evaluacion_fidelidad_ev2.md,
commit be8a84f): construcción del request, cliente cacheado y parseo del veredicto.

Unidad de juicio: el par (respuesta, criterio). Operativamente, UNA llamada por
(pregunta, respuesta) devuelve la clasificación de todos sus criterios más la
clasificación auxiliar abstencion/contenido; las N repeticiones del §4 repiten
la llamada completa bajo labels y dbs de caché separados (patrón rt_c6_n3), de
modo que cada repetición re-muestrea de verdad.

El input del juez es EXCLUSIVAMENTE: pregunta + respuesta final del agente +
criterios con su cita textual. Nada más (§1): ni grafo de origen, ni labels,
ni veredicto humano alguno. El veredicto por pregunta NO lo decide el LLM:
sale del mapping fijo de mapping.py (§2).

Caché: patrón obligatorio del repo (CachingClient de llm_cache.py, write-through,
never-pay-twice). CODE_VER manual incluye el sha256 del prompt: editar el prompt
(solo por laudo) invalida la caché solo.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

JUEZ_DIR = Path(__file__).resolve().parent
EVAL_DIR = JUEZ_DIR.parent / "evaluacion"
sys.path.insert(0, str(EVAL_DIR))

import llm_cache as lc  # noqa: E402  (capa sellada, solo se importa)

# --------------------------------------------------------------------------- #
# Instrumento (pre-registro §1)                                               #
# --------------------------------------------------------------------------- #
MODELO = "claude-sonnet-4-6"
TEMPERATURE = 0.0
MAX_TOKENS = 3000

# Versión del prompt: por defecto v1; JUEZ_PROMPT_VERSION=v1_1 selecciona
# prompt_juez_v1_1.md (v1 + calibrador 1, laudo post-calibración). Cada versión
# es un archivo propio; ninguna se edita.
import os
PROMPT_VERSION = os.environ.get("JUEZ_PROMPT_VERSION", "v1")
PROMPT_PATH = JUEZ_DIR / f"prompt_juez_{PROMPT_VERSION}.md"
PROMPT_JUEZ = PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_SHA256 = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()

# CODE_VER manual (checklist de dominio nuevo): bump del sufijo -v1 ante cambios
# de lógica de ESTE módulo; el hash del prompt entra solo, así un prompt nuevo
# (por laudo) jamás come hits de la versión anterior.
CODE_VER = f"juez-ev2-v1+prompt={PROMPT_SHA256[:12]}"

VEREDICTOS_VALIDOS = {"cumplido", "no_cumplido", "dudoso"}
CLASIFICACIONES_VALIDAS = {"abstencion", "contenido"}


# --------------------------------------------------------------------------- #
# Request                                                                     #
# --------------------------------------------------------------------------- #
def construir_mensaje_usuario(pregunta: str, respuesta: str,
                              criterios: list[dict]) -> str:
    """Mensaje de usuario del juez: pregunta + respuesta + criterios numerados
    con su cita textual. Es el ÚNICO material del caso que viaja al modelo."""
    if not criterios:
        raise ValueError("pregunta sin criterios")
    partes = ["PREGUNTA:", pregunta.strip(), "", "RESPUESTA:", respuesta.strip(), "",
              f"CRITERIOS ({len(criterios)}):"]
    for i, c in enumerate(criterios, start=1):
        partes.append(f"{i}. {c['criterio'].strip()}")
        partes.append(f"   Cita textual de la norma: «{c['cita_textual'].strip()}»")
    return "\n".join(partes)


def construir_kwargs(pregunta: str, respuesta: str, criterios: list[dict]) -> dict:
    return {
        "model": MODELO,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "system": PROMPT_JUEZ,
        "messages": [{"role": "user",
                      "content": construir_mensaje_usuario(pregunta, respuesta, criterios)}],
    }


# --------------------------------------------------------------------------- #
# Parseo y validación del veredicto                                           #
# --------------------------------------------------------------------------- #
def extraer_texto(resp) -> str:
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def parsear_veredicto(texto: str, n_criterios: int) -> dict:
    """Valida estructura completa: clasificación auxiliar + exactamente una
    entrada por criterio con índices 1..K en orden y veredictos del dominio.
    Cualquier desvío levanta ValueError (el driver lo registra, no lo tapa)."""
    ini, fin = texto.find("{"), texto.rfind("}")
    if ini < 0 or fin <= ini:
        raise ValueError("sin objeto JSON en la salida del juez")
    data = json.loads(texto[ini:fin + 1])

    clasif = data.get("clasificacion_respuesta")
    if clasif not in CLASIFICACIONES_VALIDAS:
        raise ValueError(f"clasificacion_respuesta inválida: {clasif!r}")

    crits = data.get("criterios")
    if not isinstance(crits, list) or len(crits) != n_criterios:
        raise ValueError(f"se esperaban {n_criterios} criterios, "
                         f"llegaron {len(crits) if isinstance(crits, list) else 'no-lista'}")
    limpio = []
    for i, c in enumerate(crits, start=1):
        if int(c.get("indice", -1)) != i:
            raise ValueError(f"índice fuera de orden en posición {i}: {c.get('indice')!r}")
        v = c.get("veredicto")
        if v not in VEREDICTOS_VALIDOS:
            raise ValueError(f"veredicto inválido en criterio {i}: {v!r}")
        frag = c.get("fragmento")
        if frag is not None and not isinstance(frag, str):
            raise ValueError(f"fragmento no-string en criterio {i}")
        limpio.append({"indice": i, "veredicto": v, "fragmento": frag,
                       "justificacion": str(c.get("justificacion", ""))})
    return {"clasificacion_respuesta": clasif, "criterios": limpio}


def juzgar(client, pregunta: str, respuesta: str, criterios: list[dict]) -> dict:
    """Una repetición del juicio de un caso. Devuelve el veredicto parseado más
    metadatos de la llamada (tokens, stop_reason, modelo, sha del prompt)."""
    kwargs = construir_kwargs(pregunta, respuesta, criterios)
    resp = client.messages.create(**kwargs)
    stop = getattr(resp, "stop_reason", None)
    if stop == "max_tokens":
        raise ValueError("respuesta del juez truncada por max_tokens")
    u = getattr(resp, "usage", None)
    return {
        "veredicto": parsear_veredicto(extraer_texto(resp), len(criterios)),
        "meta": {
            "modelo": getattr(resp, "model", MODELO),
            "stop_reason": stop,
            "input_tokens": int(getattr(u, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(u, "output_tokens", 0) or 0),
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": PROMPT_SHA256,
            "code_ver": CODE_VER,
        },
    }


# --------------------------------------------------------------------------- #
# Cliente real (uno por repetición: db y label propios, patrón rt_c6_n3)      #
# --------------------------------------------------------------------------- #
def db_path_rep(rep: int, cache_dir: Path | None = None,
                db_prefix: str = "juez_calibracion") -> Path:
    return (cache_dir or (JUEZ_DIR / "cache")) / f"{db_prefix}_r{rep}.db"


def construir_cliente_real(rep: int, *, run_label: str,
                           cache_dir: Path | None = None,
                           db_prefix: str = "juez_calibracion") -> lc.CachingClient:
    """CachingClient sobre el SDK real (retry nativo). El namespace incluye la
    repetición: las N cachés jamás se cruzan (0 cross-hits por construcción,
    verificado además empíricamente por el driver)."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(EVAL_DIR / ".env")
    real = anthropic.Anthropic(max_retries=3)
    return lc.CachingClient(
        real,
        domain="juez_ev2",
        db_path=db_path_rep(rep, cache_dir, db_prefix),
        namespace=lc.make_namespace(f"juez_ev2_r{rep}", code_ver=CODE_VER, thinking=False),
        thinking_enabled=False,
        run_label=run_label,
    )
