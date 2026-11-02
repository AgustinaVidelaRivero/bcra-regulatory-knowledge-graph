"""
prompt_esq3b_v2.py — FASE (a) de U-ESQ-3b-v2: prefijo V2 del extractor E1
(retoques REVISADOS de la vuelta 2).

Gobernado por el pre-registro de la vuelta 2 (`40493c9`,
data/experiment/esq/prerregistro_esq3b_v2.md, §1) sobre la tabla de resultados
de la vuelta 1 (`0c19dc8`) y el pre-registro v1 (`01bf046` + Adenda 1
`f1fe0d8`).

REGLA DURA: ni `prompt_e1.py` ni `prompt_esq3b.py` se editan. Este módulo
IMPORTA el prefijo v1 sellado (`f0a421fb9466`) y lo transforma con reemplazos
declarados, cada uno asertado como ÚNICO (mismo mecanismo que la vuelta 1
sobre producción). El texto v1 no cambia una letra: el retoque v2 vive acá y
solo acá.

Cambios implementados (lista cerrada del §1 del pre-registro v2; ninguno se
re-decide en este módulo — los TEXTOS son los EXACTOS sellados en §1, bajo su
regla de redacción vinculante: describen patrones, sin citar texto de ninguna
unidad de predicción ni de la selección):

  R1  Potestad: guía de POLARIDAD al final de su definición (la supresión de
      un requisito no es potestad; dispara la modalidad, no el léxico; el
      contenido habilitante SÍ se extrae).
  R3  Definicion: cláusula anti-encabezado + prohibición de duplicar entre
      cajas, al final de su delimitación.
  R2  Condicion: el supuesto enunciado por el ENCABEZADO HEREDADO entra a su
      delimitación.
  R4  Regla 9: (i) descripción explícita de las cláusulas interpretativas;
      (ii) el contenido HABILITANTE no es meta-normativo (cierre de la regla).
  RE  `requisito_de_estructura`: su descripción en el enum se REEMPLAZA por la
      versión con delimitación negativa explícita.
  R6a RECHAZADO (laudo ejecutado por el pre-registro v2): `exceptua_operacion`
      SALE de la matriz, del catálogo de predicados y del conteo del título
      (14 → 13). El residuo queda documentado junto a R6b, promovible en r2.

REGLA DE NO-FILTRACIÓN (pre-registro v2 §5, DOS niveles): ninguna ventana de
5 palabras del texto de NINGUNA unidad seleccionada (objetivo Y regresión
fresca) aparece en el texto agregado/modificado por estos reemplazos; y
ninguna delimitación nueva contiene bigramas ni trigramas distintivos de las
unidades de P1–P14 (palabras funcionales excluidas). Coincidencias
preexistentes del prefijo v1/producción se declaran y no bloquean (son
simétricas en el pareo). Lo verifica mecánicamente el selftest de la vuelta
(no_filtracion_v2.py vía selftest_esq3b_v2.py) ANTES del freno 1.

Caching (docs/decisiones_caching_extraccion.md, vinculantes): D1 prefijo v2
como bloque único de system con cache_control ephemeral; el mensaje de usuario
es el de producción sin tocar (build_user_message). El hash del prefijo v2 es
DISTINTO por construcción del de producción, del de ESQ-2 y del de la vuelta 1
→ particiona el namespace de caché: jamás pisa keys ajenas.
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

import prompt_esq3b as pr1     # noqa: E402  — prefijo v1: se IMPORTA, jamás se edita
from prompt_esq3b import (     # noqa: E402
    MAX_OUTPUT_TOKENS,
    NOMBRE_TOOL,
)
import prompt_e1               # noqa: E402  (vía path que armó prompt_esq3b)
from prompt_e1 import build_user_message  # noqa: E402
from schema import SUJETOS_CATALOGO       # noqa: E402

# Candados: el prefijo v1 sobre el que se aplica esta revisión debe ser el
# sellado en la Adenda 1 (`f0a421fb9466`), construido a su vez sobre el prefijo
# de producción de ESQ-2 (`4793d6152608`). Si cualquiera cambió, el selftest
# FRENA: la revisión se estaría aplicando sobre otro texto base.
PREFIJO_HASH_PRODUCCION_ESPERADO = pr1.PREFIJO_HASH_PRODUCCION_ESPERADO
PREFIJO_HASH_V1_ESPERADO = "f0a421fb9466"


# ========================================================================== #
# Vocabulario v2                                                             #
# ========================================================================== #

# Los 9 tipos de la vuelta 1 (sin cambio de tipos en la vuelta 2).
ENTITY_TYPES_V2 = tuple(pr1.ENTITY_TYPES_RETOCADO)

# 13 predicados: los 14 de la vuelta 1 MENOS exceptua_operacion (R6a
# RECHAZADO, pre-registro v2 preámbulo y §1).
PREDICATES_V2 = tuple(p for p in pr1.PREDICATES_RETOCADO
                      if p != "exceptua_operacion")

SUJETO_PREDICATES = pr1.SUJETO_PREDICATES

# Enum de Obligacion.tipo: sin cambio de VALORES en la vuelta 2 (la revisión
# de RE es de texto de descripción, no de lista).
OBLIGACION_TIPO_V2 = tuple(pr1.OBLIGACION_TIPO_RETOCADO)

# Matriz dominio/rango v2 = la de la vuelta 1 sin la fila exceptua_operacion.
DOMAIN_RANGE_V2: dict[str, tuple[set[str], set[str]]] = {
    p: (set(d), set(r)) for p, (d, r) in pr1.DOMAIN_RANGE_RETOCADO.items()
    if p != "exceptua_operacion"
}


def firma_valida(source_type: str, predicate: str, target_type: str) -> bool:
    """is_valid_triple contra la matriz V2 (el extremo sujeto de
    aplica_a/ejecuta se pasa como el pseudo-tipo 'Sujeto', igual que en
    producción)."""
    if predicate not in DOMAIN_RANGE_V2:
        return False
    dom, ran = DOMAIN_RANGE_V2[predicate]
    return source_type in dom and target_type in ran


# ========================================================================== #
# Textos EXACTOS sellados del §1 (no se re-redactan acá)                     #
# ========================================================================== #

TEXTO_POLARIDAD_POTESTAD = (
    "POLARIDAD (no la confundas): la SUPRESIÓN o exención de un requisito NO "
    "es una potestad — un enunciado cuyo efecto es negar la exigibilidad de "
    "algo dice que un deber no aplica, no que alguien quede habilitado; ese "
    "contenido va a la caja que corresponda (Excepcion si suspende una regla) "
    "y NUNCA a Potestad. El disparador de Potestad es la MODALIDAD deóntica "
    "de habilitación (las marcas listadas arriba), no el léxico: la mera "
    "presencia de vocabulario de autorización o permiso no hace Potestad. El "
    "contenido HABILITANTE —una norma cuyo efecto es que un sujeto PUEDA "
    "realizar algo— es Potestad y SÍ se extrae: no es contenido "
    "meta-normativo."
)

TEXTO_ANTI_ENCABEZADO_DEFINICION = (
    "QUE EL CUERPO DEFINA, NO QUE EL ENCABEZADO LO SUGIERA: un encabezado o "
    "título que nombra un término o anuncia contenido conceptual no vuelve "
    "definitoria a la unidad si el cuerpo prescribe, aplica o delimita "
    "alcance en vez de definir. Y si el definiendum es un ACTO regulado, va "
    "SOLO en Operacion: NO emitas un nodo Definicion además de la Operacion — "
    "el mismo contenido no se duplica en dos cajas."
)

TEXTO_ENCABEZADO_HEREDADO_CONDICION = (
    "El supuesto puede estar enunciado por el ENCABEZADO HEREDADO: si el "
    "contexto heredado termina anunciando las condiciones o supuestos que "
    "los ítems siguientes enumeran, la unidad entera es una Condicion de la "
    "norma de ese encabezado — NO una Obligacion autónoma, aunque su verbo "
    "esté en subjuntivo con forma de deber."
)

TEXTO_INTERPRETATIVAS_R4 = (
    "(típicamente, construcciones que niegan que un acto o una participación "
    "tenga determinado significado o efecto jurídico)"
)

TEXTO_HABILITANTE_R4 = (
    "NO es meta-normativo el contenido HABILITANTE: una norma cuyo efecto es "
    "que un sujeto pueda realizar algo PRESCRIBE (es Potestad) y SÍ se "
    "extrae — esta regla prohíbe fabricar prescripciones falsas, no omitir "
    "permisos reales."
)

TEXTO_RE_NUEVO = (
    "`requisito_de_estructura` es el deber de DISPONER de algo con carácter "
    "permanente: políticas, procedimientos, manuales, sistemas, órganos, "
    "personal designado, forma jurídica, sede. NO son requisito_de_estructura: "
    "las constancias documentales, las condiciones de elegibilidad, las "
    "aprobaciones puntuales de un órgano, las autorizaciones previas — eso va "
    "a su clase o a \"otra\"."
)


# ========================================================================== #
# Reemplazos declarados sobre el prefijo v1                                  #
# ========================================================================== #
# Cada par (viejo, nuevo) se aplica UNA vez y se asserta que el `viejo` aparece
# EXACTAMENTE una vez en el texto v1. Orden irrelevante: los anclas son
# disjuntos.

# R1 · Potestad — «se agrega al final de su definición»: la guía de POLARIDAD
# entra como último párrafo del ítem 7, después de Properties y antes del ítem
# 8 (Condicion). Ancla: el cierre único del bloque Potestad.
_POTESTAD_VIEJO = (
    "eso es Restriccion, tipo prohibicion).\n"
    "   Properties: descripcion (corta, grounded).\n\n"
    "8. **Condicion**"
)
_POTESTAD_NUEVO = (
    "eso es Restriccion, tipo prohibicion).\n"
    "   Properties: descripcion (corta, grounded).\n"
    "   " + TEXTO_POLARIDAD_POTESTAD + "\n\n"
    "8. **Condicion**"
)

# R2 · Condicion — «se agrega a su delimitación»: al final del párrafo
# DELIMITACIÓN del ítem 8. Ancla: el cierre único de ese párrafo.
_CONDICION_VIEJO = (
    "mismo chunk cuando el texto de la unidad enuncie ese vínculo.\n"
)
_CONDICION_NUEVO = (
    "mismo chunk cuando el texto de la unidad enuncie ese vínculo. "
    + TEXTO_ENCABEZADO_HEREDADO_CONDICION + "\n"
)

# R3 · Definicion — «se agrega al final de su delimitación»: al final del
# párrafo DELIMITACIÓN ESTRICTA del ítem 9. Ancla: su cierre único.
_DEFINICION_VIEJO = (
    "va en el tipo deóntico que corresponda, no acá.\n"
)
_DEFINICION_NUEVO = (
    "va en el tipo deóntico que corresponda, no acá. "
    + TEXTO_ANTI_ENCABEZADO_DEFINICION + "\n"
)

# R4 · regla 9, retoque (i): tras «cláusulas interpretativas» entra la
# descripción explícita, antes del paréntesis de marcas ya presente en v1.
_R4_INTERPRETATIVAS_VIEJO = (
    "cláusulas interpretativas (\"lo dispuesto no "
)
_R4_INTERPRETATIVAS_NUEVO = (
    "cláusulas interpretativas " + TEXTO_INTERPRETATIVAS_R4
    + " (\"lo dispuesto no "
)

# R4 · regla 9, retoque (ii): al final de la regla.
_R4_CIERRE_VIEJO = (
    "no una afirmación falsa.\n\n"
)
_R4_CIERRE_NUEVO = (
    "no una afirmación falsa. " + TEXTO_HABILITANTE_R4 + "\n\n"
)

# RE · la descripción de requisito_de_estructura en el enum SE REEMPLAZA.
_RE_VIEJO = (
    "`requisito_de_estructura` "
    "es el deber de DISPONER de algo con carácter permanente (políticas, "
    "procedimientos, manuales, sistemas, órganos, autorización previa, personal "
    "designado), distinto de ejecutar un acto puntual."
)
_RE_NUEVO = TEXTO_RE_NUEVO

# R6a RECHAZADO · remoción completa de exceptua_operacion:
#   (i) fila fuera de la matriz del prefijo;
_R6A_FILA_VIEJO = "| `exceptua_operacion` | Excepcion → Operacion |\n"
_R6A_FILA_NUEVO = ""
#   (ii) el título de predicados vuelve a su conteo (14 → 13);
_R6A_TITULO_VIEJO = "# PREDICADOS VÁLIDOS (exactamente 14, ningún otro)"
_R6A_TITULO_NUEVO = "# PREDICADOS VÁLIDOS (exactamente 13, ningún otro)"
#   (iii) la mención del conteo en las reglas, fuera.
_R6A_REGLA4_VIEJO = "los 9 tipos de entidad o 14 predicados"
_R6A_REGLA4_NUEVO = "los 9 tipos de entidad o 13 predicados"

# Orden de aplicación (documentado; los anclas son disjuntos).
REEMPLAZOS_V2: tuple[tuple[str, str, str], ...] = (
    ("R1-polaridad-potestad", _POTESTAD_VIEJO, _POTESTAD_NUEVO),
    ("R2-encabezado-heredado-condicion", _CONDICION_VIEJO, _CONDICION_NUEVO),
    ("R3-anti-encabezado-definicion", _DEFINICION_VIEJO, _DEFINICION_NUEVO),
    ("R4-interpretativas-descripcion", _R4_INTERPRETATIVAS_VIEJO,
     _R4_INTERPRETATIVAS_NUEVO),
    ("R4-habilitante-cierre", _R4_CIERRE_VIEJO, _R4_CIERRE_NUEVO),
    ("RE-delimitacion-negativa", _RE_VIEJO, _RE_NUEVO),
    ("R6a-fila-matriz-fuera", _R6A_FILA_VIEJO, _R6A_FILA_NUEVO),
    ("R6a-titulo-predicados-14a13", _R6A_TITULO_VIEJO, _R6A_TITULO_NUEVO),
    ("R6a-regla4-conteo-14a13", _R6A_REGLA4_VIEJO, _R6A_REGLA4_NUEVO),
)

# Texto AGREGADO o MODIFICADO por la vuelta 2 (insumo del selftest de
# no-filtración de dos niveles): los fragmentos NUEVOS de cada reemplazo. Las
# remociones de R6a no agregan texto; los retoques de conteo no agregan
# palabras de contenido pero se incluyen igual por completitud.
TEXTOS_AGREGADOS_V2: dict[str, str] = {
    "R1-polaridad-potestad": TEXTO_POLARIDAD_POTESTAD,
    "R2-encabezado-heredado-condicion": TEXTO_ENCABEZADO_HEREDADO_CONDICION,
    "R3-anti-encabezado-definicion": TEXTO_ANTI_ENCABEZADO_DEFINICION,
    "R4-interpretativas-descripcion": TEXTO_INTERPRETATIVAS_R4,
    "R4-habilitante-cierre": TEXTO_HABILITANTE_R4,
    "RE-delimitacion-negativa": TEXTO_RE_NUEVO,
    "R6a-titulo-predicados-14a13": _R6A_TITULO_NUEVO,
    "R6a-regla4-conteo-14a13": _R6A_REGLA4_NUEVO,
}

# Las delimitaciones NUEVAS del §1 (objeto del nivel 2 de no-filtración:
# bigramas/trigramas distintivos de las unidades de P1–P14).
DELIMITACIONES_NUEVAS_V2: dict[str, str] = {
    "Potestad-polaridad": TEXTO_POLARIDAD_POTESTAD,
    "Definicion-anti-encabezado": TEXTO_ANTI_ENCABEZADO_DEFINICION,
    "Condicion-encabezado-heredado": TEXTO_ENCABEZADO_HEREDADO_CONDICION,
    "R4-interpretativas": TEXTO_INTERPRETATIVAS_R4,
    "R4-habilitante": TEXTO_HABILITANTE_R4,
    "RE-delimitacion-negativa": TEXTO_RE_NUEVO,
}


def prefijo_sistema_v2() -> str:
    """Prefijo v1 con los cambios del §1 aplicados. Función PURA y
    determinística: sin fechas, sin aleatoriedad, sin estado. Cada ancla se
    asserta única antes de reemplazar (si prompt_esq3b cambiara, revienta acá
    y no en la API). Al final se asserta la remoción COMPLETA de
    exceptua_operacion."""
    texto = pr1.PREFIJO_SISTEMA_RETOCADO
    for nombre, viejo, nuevo in REEMPLAZOS_V2:
        n = texto.count(viejo)
        if n != 1:
            raise RuntimeError(
                f"reemplazo {nombre}: el ancla aparece {n} veces en el prefijo "
                f"v1 (esperado 1) — el texto base cambió, se frena")
        texto = texto.replace(viejo, nuevo)
    if "exceptua_operacion" in texto:
        raise RuntimeError(
            "la remoción de exceptua_operacion NO fue completa: queda al menos "
            "una mención en el prefijo v2 — se frena")
    return texto


PREFIJO_SISTEMA_V2 = prefijo_sistema_v2()


# ========================================================================== #
# TOOL SCHEMA v2                                                             #
# ========================================================================== #

def _tool_schema_v2() -> dict:
    """El tool schema de la vuelta 1 con el enum de predicados SIN
    exceptua_operacion (13) y la description con el conteo nuevo. NADA más se
    toca: additionalProperties sigue False, los required son los de
    producción, el enum de sujetos no se toca y no se agregan campos.

    El enum de Obligacion.tipo sigue SIN vivir en el tool schema (properties
    es texto libre); la revisión de RE es un cambio de texto del prefijo — el
    endurecimiento del validador sigue siendo territorio B5."""
    schema = copy.deepcopy(pr1.TOOL_SCHEMA_RETOCADO)
    schema["description"] = (
        "Extrae entidades y relaciones del chunk según el schema cerrado v2 "
        "retocado (9 tipos de entidad, 13 predicados, catálogo cerrado de "
        "sujetos). Todo elemento lleva `punto` (provenance a nivel unidad "
        "estructural, de la lista admitida del chunk)."
    )
    ent = schema["input_schema"]["properties"]["entities"]["items"]["properties"]
    ent["type"]["enum"] = list(ENTITY_TYPES_V2)
    rel = schema["input_schema"]["properties"]["relations"]["items"]["properties"]
    rel["predicate"]["enum"] = list(PREDICATES_V2)
    return schema


TOOL_SCHEMA_V2 = _tool_schema_v2()


def bloques_sistema_v2() -> list[dict]:
    """D1: system como lista de bloques con el breakpoint de caching en el
    último (y único) bloque del prefijo estable."""
    return [
        {
            "type": "text",
            "text": PREFIJO_SISTEMA_V2,
            "cache_control": {"type": "ephemeral"},
        }
    ]


PREFIJO_CANONICO_V2 = json.dumps(
    {"system": bloques_sistema_v2(), "tools": [TOOL_SCHEMA_V2]},
    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
)
PREFIJO_HASH_V2 = hashlib.sha256(
    PREFIJO_CANONICO_V2.encode("utf-8")).hexdigest()[:12]

# sha256 completo del TEXTO del prefijo v2 (el que va al manifiesto del freno
# 1; el hash corto de arriba es la huella prefijo+tools que particiona el
# namespace, distinta cosa).
PREFIJO_SHA256_V2 = hashlib.sha256(
    PREFIJO_SISTEMA_V2.encode("utf-8")).hexdigest()


def build_request_kwargs_v2(chunk: dict, model: str,
                            max_tokens: int = MAX_OUTPUT_TOKENS) -> dict:
    """Request completo con el prefijo V2. El mensaje de usuario es el de
    producción sin tocar (prompt_e1.build_user_message): lo único que cambia
    entre brazos es el prefijo. Este dict es también la base de la key de
    caché local (llm_cache.canonical_request)."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": bloques_sistema_v2(),
        "tools": [TOOL_SCHEMA_V2],
        "tool_choice": {"type": "tool", "name": NOMBRE_TOOL},
        "messages": [{"role": "user", "content": build_user_message(chunk)}],
    }


__all__ = [
    "ENTITY_TYPES_V2", "PREDICATES_V2", "OBLIGACION_TIPO_V2",
    "DOMAIN_RANGE_V2", "SUJETO_PREDICATES", "SUJETOS_CATALOGO",
    "firma_valida", "PREFIJO_SISTEMA_V2", "TOOL_SCHEMA_V2",
    "bloques_sistema_v2", "build_request_kwargs_v2",
    "PREFIJO_HASH_V2", "PREFIJO_SHA256_V2",
    "PREFIJO_HASH_PRODUCCION_ESPERADO", "PREFIJO_HASH_V1_ESPERADO",
    "REEMPLAZOS_V2", "TEXTOS_AGREGADOS_V2", "DELIMITACIONES_NUEVAS_V2",
    "MAX_OUTPUT_TOKENS", "NOMBRE_TOOL",
]
