"""
prompt_congelado.py — U-CONGELA: materialización del PREFIJO CONGELADO del
extractor E1 (esquema congelado del gate ESQ-3).

Gobernado por el laudo de esquema congelado §4
(data/experiment/esq/laudo_esquema_congelado.md) sobre el prefijo v2 sellado
(`2c1b76d1685d`, prompt_esq3b_v2.py). Unidad mecánica $0: construcción de
texto, sin ninguna llamada LLM.

REGLA DURA: ni `prompt_e1.py`, ni `prompt_esq3b.py`, ni `prompt_esq3b_v2.py`
se editan. Este módulo IMPORTA el prefijo v2 sellado y lo transforma con DOS
reemplazos declarados, cada uno asertado como ÚNICO (mismo mecanismo que las
dos vueltas de ESQ-3b). El texto v2 no cambia una letra: el congelado vive acá
y solo acá.

Materialización del retiro de `requisito_de_estructura` (laudo §4; el valor
falló su regla sellada en material fresco — 3/5 objetadas — y por el principio
§1 SE RETIRA, con destino r2):

  (1) RE-enum-6-valores: el literal del enum de Obligacion.tipo pasa de 7 a
      6 valores — "presentacion_informativa"|"calculo"|"asignacion"|
      "comunicacion_a_cliente"|"reporte_al_supervisor"|"otra" —.
  (2) RE-delimitacion-fuera: el pasaje descriptivo del valor (la delimitación
      negativa v2 COMPLETA, TEXTO_RE_NUEVO de prompt_esq3b_v2) se elimina,
      conservando INTACTAS la oración de `reporte_al_supervisor` y la de
      «otra».

La materialización toca SOLO el texto del prefijo: el enum de Obligacion.tipo
NO vive en el tool schema (`properties` es texto libre — verificado en el
selftest v2; el endurecimiento del validador es territorio B5), de modo que el
tool schema queda BYTE-IDÉNTICO al v2 (lo asserta selftest_congelado.py con
igualdad estricta del canónico).

Este prefijo es el de PRODUCCIÓN del escalado: B5.4 lo integra tal cual, y
cualquier diferencia entre lo integrado y el sha registrado en el laudo §4
invalida la corrida que la contenga.

Caching (docs/decisiones_caching_extraccion.md, vinculantes): D1 prefijo
congelado como bloque único de system con cache_control ephemeral; el mensaje
de usuario es el de producción sin tocar (build_user_message). El hash del
prefijo congelado es DISTINTO por construcción del de producción, del de
ESQ-2, del v1 y del v2 → particiona el namespace de caché: jamás pisa keys
ajenas.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import prompt_esq3b_v2 as pr2  # noqa: E402 — prefijo v2: se IMPORTA, jamás se edita
from prompt_esq3b_v2 import (  # noqa: E402
    MAX_OUTPUT_TOKENS,
    NOMBRE_TOOL,
)
from prompt_e1 import build_user_message  # noqa: E402  (vía path de la cadena)
from schema import SUJETOS_CATALOGO       # noqa: E402

# Candados de la CADENA completa: producción (ESQ-2) → v1 (Adenda 1) → v2
# (pre-registro v2). El candado operativo de esta unidad es el del v2: si el
# prefijo v2 no es el sellado `2c1b76d1685d` (laudo §4), la construcción FRENA
# — el congelado se estaría materializando sobre otro texto base.
PREFIJO_HASH_PRODUCCION_ESPERADO = pr2.PREFIJO_HASH_PRODUCCION_ESPERADO
PREFIJO_HASH_V1_ESPERADO = pr2.PREFIJO_HASH_V1_ESPERADO
PREFIJO_HASH_V2_ESPERADO = "2c1b76d1685d"


# ========================================================================== #
# Vocabulario congelado                                                      #
# ========================================================================== #

# 9 tipos de entidad: los 6 de producción + Potestad, Condicion, Definicion
# (sin cambio respecto del v2).
ENTITY_TYPES_CONGELADO = tuple(pr2.ENTITY_TYPES_V2)

# 13 predicados: los 12 de producción + condicion_de (sin cambio respecto del
# v2; exceptua_operacion ya había salido en la vuelta 2).
PREDICATES_CONGELADO = tuple(pr2.PREDICATES_V2)

SUJETO_PREDICATES = pr2.SUJETO_PREDICATES

# Enum de Obligacion.tipo con 6 VALORES (laudo §4): los 7 del v2 MENOS
# requisito_de_estructura (retirado — falsedad en campo estructurado en
# material fresco; sus emisiones vuelven a "otra").
OBLIGACION_TIPO_CONGELADO = tuple(
    v for v in pr2.OBLIGACION_TIPO_V2 if v != "requisito_de_estructura"
)

# Matriz dominio/rango: la del v2 sin cambio alguno.
DOMAIN_RANGE_CONGELADO: dict[str, tuple[set[str], set[str]]] = {
    p: (set(d), set(r)) for p, (d, r) in pr2.DOMAIN_RANGE_V2.items()
}


def firma_valida(source_type: str, predicate: str, target_type: str) -> bool:
    """is_valid_triple contra la matriz CONGELADA (el extremo sujeto de
    aplica_a/ejecuta se pasa como el pseudo-tipo 'Sujeto', igual que en
    producción)."""
    if predicate not in DOMAIN_RANGE_CONGELADO:
        return False
    dom, ran = DOMAIN_RANGE_CONGELADO[predicate]
    return source_type in dom and target_type in ran


# ========================================================================== #
# Los DOS reemplazos declarados sobre el prefijo v2 (laudo §4)               #
# ========================================================================== #
# Cada par (viejo, nuevo) se aplica UNA vez y se asserta que el `viejo`
# aparece EXACTAMENTE una vez en el texto v2. Los anclas son disjuntos (viven
# en líneas distintas del ítem 6 del prefijo).

# (1) El literal del enum pasa de 7 a 6 valores.
_ENUM_VIEJO = (
    '("presentacion_informativa"|"calculo"|"asignacion"|'
    '"comunicacion_a_cliente"|"reporte_al_supervisor"|'
    '"requisito_de_estructura"|"otra")'
)
_ENUM_NUEVO = (
    '("presentacion_informativa"|"calculo"|"asignacion"|'
    '"comunicacion_a_cliente"|"reporte_al_supervisor"|"otra")'
)

# (2) La delimitación negativa v2 COMPLETA (TEXTO_RE_NUEVO, referida por su
# constante sellada — no se retranscribe) se elimina del pasaje «Sobre
# `tipo`». El ancla incluye el cierre de la oración de reporte_al_supervisor
# y el arranque de la de «otra» para que el reemplazo mismo documente que
# ambas quedan INTACTAS (solo cae el pasaje del medio y su espacio).
_RE_FUERA_VIEJO = (
    "son destinatarios distintos y no se confunden. "
    + pr2.TEXTO_RE_NUEVO
    + " `otra` es el residuo"
)
_RE_FUERA_NUEVO = (
    "son destinatarios distintos y no se confunden. `otra` es el residuo"
)

REEMPLAZOS_CONGELADO: tuple[tuple[str, str, str], ...] = (
    ("RE-enum-6-valores", _ENUM_VIEJO, _ENUM_NUEVO),
    ("RE-delimitacion-fuera", _RE_FUERA_VIEJO, _RE_FUERA_NUEVO),
)


def prefijo_sistema_congelado() -> str:
    """Prefijo v2 con el retiro de requisito_de_estructura aplicado. Función
    PURA y determinística: sin fechas, sin aleatoriedad, sin estado. ANTES de
    construir verifica el candado del v2 (laudo §4); cada ancla se asserta
    única antes de reemplazar; al final se asserta la remoción COMPLETA de
    requisito_de_estructura."""
    if pr2.PREFIJO_HASH_V2 != PREFIJO_HASH_V2_ESPERADO:
        raise RuntimeError(
            f"candado v2: el prefijo v2 tiene hash {pr2.PREFIJO_HASH_V2}, "
            f"esperado {PREFIJO_HASH_V2_ESPERADO} — el texto base no es el "
            f"sellado, se frena")
    texto = pr2.PREFIJO_SISTEMA_V2
    for nombre, viejo, nuevo in REEMPLAZOS_CONGELADO:
        n = texto.count(viejo)
        if n != 1:
            raise RuntimeError(
                f"reemplazo {nombre}: el ancla aparece {n} veces en el "
                f"prefijo v2 (esperado 1) — el texto base cambió, se frena")
        texto = texto.replace(viejo, nuevo)
    if "requisito_de_estructura" in texto:
        raise RuntimeError(
            "la remoción de requisito_de_estructura NO fue completa: queda "
            "al menos una mención en el prefijo congelado — se frena")
    return texto


PREFIJO_SISTEMA_CONGELADO = prefijo_sistema_congelado()


# ========================================================================== #
# TOOL SCHEMA congelado — BYTE-IDÉNTICO al v2                                #
# ========================================================================== #

# El laudo §4 manda que la materialización toque SOLO el texto del prefijo:
# el enum de Obligacion.tipo no vive en el tool schema (properties es texto
# libre). Copia profunda SIN ninguna modificación; la igualdad estricta con
# el v2 la asserta el selftest.
TOOL_SCHEMA_CONGELADO = copy.deepcopy(pr2.TOOL_SCHEMA_V2)


def bloques_sistema_congelado() -> list[dict]:
    """D1: system como lista de bloques con el breakpoint de caching en el
    último (y único) bloque del prefijo estable."""
    return [
        {
            "type": "text",
            "text": PREFIJO_SISTEMA_CONGELADO,
            "cache_control": {"type": "ephemeral"},
        }
    ]


PREFIJO_CANONICO_CONGELADO = json.dumps(
    {"system": bloques_sistema_congelado(), "tools": [TOOL_SCHEMA_CONGELADO]},
    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
)
PREFIJO_HASH_CONGELADO = hashlib.sha256(
    PREFIJO_CANONICO_CONGELADO.encode("utf-8")).hexdigest()[:12]

# sha256 completo del TEXTO del prefijo congelado (el que entra al laudo §4;
# el hash corto de arriba es la huella system+tools que particiona el
# namespace, distinta cosa).
PREFIJO_SHA256_CONGELADO = hashlib.sha256(
    PREFIJO_SISTEMA_CONGELADO.encode("utf-8")).hexdigest()


def build_request_kwargs_congelado(chunk: dict, model: str,
                                   max_tokens: int = MAX_OUTPUT_TOKENS) -> dict:
    """Request completo con el prefijo CONGELADO. El mensaje de usuario es el
    de producción sin tocar (prompt_e1.build_user_message). Este dict es
    también la base de la key de caché local (llm_cache.canonical_request)."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": bloques_sistema_congelado(),
        "tools": [TOOL_SCHEMA_CONGELADO],
        "tool_choice": {"type": "tool", "name": NOMBRE_TOOL},
        "messages": [{"role": "user", "content": build_user_message(chunk)}],
    }


__all__ = [
    "ENTITY_TYPES_CONGELADO", "PREDICATES_CONGELADO",
    "OBLIGACION_TIPO_CONGELADO", "DOMAIN_RANGE_CONGELADO",
    "SUJETO_PREDICATES", "SUJETOS_CATALOGO", "firma_valida",
    "PREFIJO_SISTEMA_CONGELADO", "TOOL_SCHEMA_CONGELADO",
    "bloques_sistema_congelado", "build_request_kwargs_congelado",
    "PREFIJO_HASH_CONGELADO", "PREFIJO_SHA256_CONGELADO",
    "PREFIJO_HASH_PRODUCCION_ESPERADO", "PREFIJO_HASH_V1_ESPERADO",
    "PREFIJO_HASH_V2_ESPERADO", "REEMPLAZOS_CONGELADO",
    "MAX_OUTPUT_TOKENS", "NOMBRE_TOOL",
]
