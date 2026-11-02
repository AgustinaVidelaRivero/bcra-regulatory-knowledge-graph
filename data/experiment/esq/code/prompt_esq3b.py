"""
prompt_esq3b.py — FASE (a) de U-ESQ-3b: prefijo RETOCADO del extractor E1.

Gobernado por el laudo ESQ-3a (`0a76549`, data/experiment/esq/laudo_ESQ-3a_retoques.md)
y el pre-registro de ESQ-3b (`01bf046`, data/experiment/esq/prerregistro_esq3b.md).

REGLA DURA: `prompt_e1.py` NO se edita. Este módulo IMPORTA el prefijo de
producción y lo transforma con reemplazos declarados, cada uno asertado como
ÚNICO (patrón de `prompt_e1.prefijo_sistema(canal_abierto=True)`, que hace lo
mismo para el modo abierto). El texto de producción no cambia una letra: el
retoque vive acá y solo acá.

Retoques implementados (lista cerrada del laudo §3, firmada; ninguno se
re-decide en este módulo):

  R1  tipo nuevo `Potestad` (facultad/permiso, incluida la facultad
      discrecional de la autoridad); entra al dominio de `establecida_en` y
      `aplica_a`.
  R2  tipo nuevo `Condicion` + predicado `condicion_de`
      (Condicion → {Excepcion, Obligacion, Restriccion}).
  R3  tipo nuevo `Definicion` con la DELIMITACIÓN de la f. 37: solo clases,
      conjuntos, conceptos y parámetros; los actos definidos SIGUEN en
      Operacion.
  R4  regla de omisión declarada de contenido meta-normativo (NO es un tipo:
      es una instrucción de extracción, regla 9 del prefijo).
  R5  SIN cambio de esquema. La partición declarada (consecuencia
      prohibitiva → Restriccion; consecuencia discrecional de la autoridad →
      Potestad) queda cubierta por la definición de Potestad de R1; agregar
      texto propio de R5 sería un cambio que el laudo NO aprobó.
  R6a predicado nuevo `exceptua_operacion` (Excepcion → Operacion).
  R7  campo `descripcion` en las properties de Operacion.
  R8  dominio de `aplica_a` ampliado con {Operacion, Excepcion}.
  R9  enum de `Obligacion.tipo`: se agregan EXACTAMENTE dos valores,
      `reporte_al_supervisor` y `requisito_de_estructura` (pre-registro §0).

DOMINIO DE `establecida_en` — DECISIÓN DE AUTORA (Adenda 1 §1, `f1fe0d8`):
el laudo ESQ-3a dice explícitamente que Potestad entra al dominio de
`establecida_en` (R1) y calla sobre Condicion y Definicion. La Adenda 1 §1
laudó que las tres entran, con el fundamento del freno 1: analogía con el
dominio de producción (todo tipo de contenido ancla al TextoOrdenado) y no
fabricar huérfanos por construcción (defecto medido en la f. 40). Deja de ser
decisión declarada del ejecutor.

REGLA DE NO-FILTRACIÓN (anti-rigging): ningún ejemplo ni patrón AGREGADO por
el retoque reproduce texto de las unidades de NINGUNO de los dos brazos
—objetivo y regresión— (extensión laudada en el freno 1, punto 6). El selftest
lo verifica mecánicamente con ventanas de 5 palabras de cada unidad; las
coincidencias que ya existían en el prefijo de PRODUCCIÓN se listan aparte,
porque son idénticas en los dos brazos del pareo y no pueden sesgar la
comparación. Los MARCADORES genéricos de cada categoría (el lema «facultado»,
el modo subjuntivo, «se entiende por») sí se nombran: son la definición del
tipo, no la frase de una unidad.

Caching (docs/decisiones_caching_extraccion.md, vinculantes):
  D1 el prefijo retocado va como bloque único de `system` con cache_control
     ephemeral; nada variable por chunk entra antes del breakpoint (el mensaje
     de usuario es el de producción, sin tocar: build_user_message).
  D4 el prefijo nuevo es estable dentro de la corrida y la corrida es
     secuencial (lo respeta el runner).
El hash del prefijo retocado es DISTINTO por construcción del de producción →
particiona el namespace de caché: jamás pisa keys de producción.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
EXP_DIR = CODE_DIR.parent.parent                      # data/experiment
E1_DIR = EXP_DIR / "reextraccion_v2" / "e1_extractor"
if str(E1_DIR) not in sys.path:
    sys.path.insert(0, str(E1_DIR))

import comun_e1        # noqa: E402,F401  (agrega grafo_v2/code al path)
import prompt_e1       # noqa: E402  — se IMPORTA, jamás se edita
from prompt_e1 import (  # noqa: E402
    MAX_OUTPUT_TOKENS,
    NOMBRE_TOOL,
    build_user_message,
)
from schema import SUJETOS_CATALOGO  # noqa: E402

# Candado del prefijo de producción vigente al sellar esta unidad (mismo valor
# que el candado de U-ESQ-2, comun_cobertura_esq2.PREFIJO_HASH_CERRADO_ESPERADO).
# Si prompt_e1 cambia, el hash cambia y el selftest FRENA: el retoque se estaría
# aplicando sobre un texto base distinto del medido en ESQ-2.
PREFIJO_HASH_PRODUCCION_ESPERADO = "4793d6152608"

DECISIONES_DECLARADAS = {
    "condicion_definicion_en_establecida_en": (
        "Condicion y Definicion entran al dominio de establecida_en junto con "
        "Potestad. DECISIÓN DE AUTORA, sellada en la Adenda 1 §1 del "
        "pre-registro (f1fe0d8): el laudo ESQ-3a solo lo decía de Potestad "
        "(R1) y callaba sobre los otros dos tipos nuevos. Fundamento: "
        "analogía con el dominio de producción (todo tipo de contenido ancla "
        "al TextoOrdenado) y no fabricar huérfanos por construcción (defecto "
        "medido en la f. 40)."
    ),
}


# ========================================================================== #
# Vocabulario retocado                                                       #
# ========================================================================== #

# 6 tipos de producción + 3 del laudo (R1, R2, R3).
ENTITY_TYPES_RETOCADO = (
    "Comunicacion",
    "TextoOrdenado",
    "Operacion",
    "Restriccion",
    "Excepcion",
    "Obligacion",
    "Potestad",
    "Condicion",
    "Definicion",
)

# 12 predicados de producción + 2 del laudo (R2, R6a).
PREDICATES_RETOCADO = (
    "establecida_en",
    "referencia",
    "modificada_por",
    "aplica_a",
    "regula",
    "exceptua",
    "exceptua_obligacion",
    "prohibe",
    "limita",
    "ejecuta",
    "requiere",
    "condiciona",
    "condicion_de",
    "exceptua_operacion",
)

SUJETO_PREDICATES = ("aplica_a", "ejecuta")

# Enum de Obligacion.tipo: los 5 de producción + los DOS de R9 (pre-registro §0;
# el laudo fija un TECHO de 3, la lista final de la autora tiene 2).
OBLIGACION_TIPO_RETOCADO = (
    "presentacion_informativa",
    "calculo",
    "asignacion",
    "comunicacion_a_cliente",
    "reporte_al_supervisor",     # R9 — anclado en la f. 67
    "requisito_de_estructura",   # R9 — grupo `cont` de U-R9-FREQ
    "otra",
)

# Matriz dominio/rango retocada. Cambios respecto de schema.DOMAIN_RANGE:
#   establecida_en  + Potestad (R1) + Condicion, Definicion (decisión declarada)
#   aplica_a        + Operacion, Excepcion (R8) + Potestad (R1)
#   condicion_de    predicado nuevo (R2)
#   exceptua_operacion  predicado nuevo (R6a)
DOMAIN_RANGE_RETOCADO: dict[str, tuple[set[str], set[str]]] = {
    "establecida_en":      ({"Restriccion", "Obligacion", "Excepcion", "Operacion",
                             "Potestad", "Condicion", "Definicion"}, {"TextoOrdenado"}),
    "referencia":          ({"TextoOrdenado"}, {"Comunicacion"}),
    "modificada_por":      ({"TextoOrdenado"}, {"Comunicacion"}),
    "aplica_a":            ({"Restriccion", "Obligacion", "Operacion", "Excepcion",
                             "Potestad"}, {"Sujeto"}),
    "regula":              ({"Restriccion", "Obligacion"}, {"Operacion"}),
    "exceptua":            ({"Excepcion"}, {"Restriccion"}),
    "exceptua_obligacion": ({"Excepcion"}, {"Obligacion"}),
    "exceptua_operacion":  ({"Excepcion"}, {"Operacion"}),
    "prohibe":             ({"Restriccion"}, {"Operacion"}),
    "limita":              ({"Restriccion"}, {"Operacion"}),
    "ejecuta":             ({"Sujeto"}, {"Operacion"}),
    "requiere":            ({"Operacion"}, {"Obligacion"}),
    "condiciona":          ({"Obligacion"}, {"Operacion"}),
    "condicion_de":        ({"Condicion"}, {"Excepcion", "Obligacion", "Restriccion"}),
}


def firma_valida(source_type: str, predicate: str, target_type: str) -> bool:
    """is_valid_triple contra la matriz RETOCADA (el extremo sujeto de
    aplica_a/ejecuta se pasa como el pseudo-tipo 'Sujeto', igual que en
    producción)."""
    if predicate not in DOMAIN_RANGE_RETOCADO:
        return False
    dom, ran = DOMAIN_RANGE_RETOCADO[predicate]
    return source_type in dom and target_type in ran


# ========================================================================== #
# Reemplazos declarados sobre el prefijo de producción                       #
# ========================================================================== #
# Cada par (viejo, nuevo) se aplica UNA vez y se asserta que el `viejo` aparece
# EXACTAMENTE una vez en el texto de producción. Orden irrelevante: los anclas
# son disjuntos.

_R7_OPERACION_VIEJO = (
    "3. **Operacion**: Un acto regulado: financiación, depósito, transferencia, "
    "compra/venta de moneda extranjera, clasificación de deudor, presentación "
    "informativa, etc.\n   Properties: tipo (string)."
)
_R7_OPERACION_NUEVO = (
    "3. **Operacion**: Un acto regulado: financiación, depósito, transferencia, "
    "compra/venta de moneda extranjera, clasificación de deudor, presentación "
    "informativa, etc.\n"
    "   Properties: tipo (string), descripcion (string, corta y grounded: los "
    "atributos, medios y calificadores con que el texto delimita el acto — "
    "quién lo lleva a cabo, con qué medios, sobre qué soporte, con qué "
    "alcance — cuando no tienen otro campo donde alojarse)."
)

_R9_OBLIGACION_VIEJO = (
    '6. **Obligacion**: Un deber positivo. "Deberán presentar", "calcularán", '
    '"asignarán", "informarán". Distinto de Restricción.\n'
    '   Properties: descripcion (corta), tipo ("presentacion_informativa"|'
    '"calculo"|"asignacion"|"comunicacion_a_cliente"|"otra"), opcional plazo o '
    'frecuencia.\n\n'
)
_R9_OBLIGACION_NUEVO = (
    '6. **Obligacion**: Un deber positivo. "Deberán presentar", "calcularán", '
    '"asignarán", "informarán". Distinto de Restricción.\n'
    '   Properties: descripcion (corta), tipo ("presentacion_informativa"|'
    '"calculo"|"asignacion"|"comunicacion_a_cliente"|"reporte_al_supervisor"|'
    '"requisito_de_estructura"|"otra"), opcional plazo o frecuencia.\n'
    '   Sobre `tipo`: `reporte_al_supervisor` es el deber de informar al BCRA, '
    'a la Superintendencia o a otro organismo de control — NO se etiqueta '
    '`comunicacion_a_cliente`, que es el deber de informar al usuario o cliente; '
    'son destinatarios distintos y no se confunden. `requisito_de_estructura` '
    'es el deber de DISPONER de algo con carácter permanente (políticas, '
    'procedimientos, manuales, sistemas, órganos, autorización previa, personal '
    'designado), distinto de ejecutar un acto puntual. `otra` es el residuo: '
    'usalo cuando el deber no cae en ninguno de los anteriores, no como caja '
    'por defecto.\n\n'
    # --- R1 / R2 / R3: tipos nuevos ---
    "7. **Potestad**: Una facultad o un permiso: contenido deóntico de "
    "HABILITACIÓN. El texto autoriza a hacer algo sin mandarlo ni prohibirlo, "
    "y su titular puede no ejercerlo. Patrones: \"podrá(n)\", \"queda(n) "
    "autorizada(s) a\", \"está(n) facultada(s) para\", \"tendrá(n) la opción "
    "de\", \"a su elección\".\n"
    "   Incluye la facultad DISCRECIONAL de la autoridad (BCRA, "
    "Superintendencia, UIF, organismo de control): autorizar, denegar, dejar "
    "sin efecto una autorización, exigir información adicional, prorrogar un "
    "plazo, resolver \"a su juicio\" o \"según su criterio\". Esa facultad es "
    "una Potestad del organismo, no un deber ni una prohibición de la entidad "
    "alcanzada.\n"
    "   NO uses Potestad para un deber redactado en futuro (\"presentarán\", "
    "\"informarán\": eso es Obligacion) ni para una prohibición (\"no "
    "podrán\": eso es Restriccion, tipo prohibicion).\n"
    "   Properties: descripcion (corta, grounded).\n\n"
    "8. **Condicion**: El ANTECEDENTE de otra norma: el supuesto que debe "
    "verificarse para que una excepción, una obligación o una restricción se "
    "active, se relaje o deje de aplicar. Por sí sola NO manda nada.\n"
    "   Marcas: \"siempre que\", \"a condición de que\", \"cuando se "
    "verifique\", \"en tanto\", \"si\"; y el modo SUBJUNTIVO del verbo, que es "
    "el modo de la condición y no el del mandato.\n"
    "   DELIMITACIÓN: si la unidad ENTERA enuncia el supuesto de una salvedad "
    "de la que depende otra norma, es una Condicion y NO una Obligacion — un "
    "sujeto que no invoque la norma condicionada no tiene ese deber. "
    "Conectala con `condicion_de` a la Excepcion, Obligacion o Restriccion del "
    "mismo chunk cuando el texto de la unidad enuncie ese vínculo.\n"
    "   Properties: descripcion (corta, grounded).\n\n"
    "9. **Definicion**: Un término que la norma define, con su definiens. "
    "Patrones: \"se entiende por X\", \"a los fines de estas normas, X es/"
    "comprende\", \"se denominarán X\", \"X: ...\".\n"
    "   DELIMITACIÓN ESTRICTA (no la relajes): Definicion es SOLO para "
    "definienda que no son actos ni prescripciones — clases, conjuntos, "
    "conceptos y parámetros. Si el definiendum es un ACTO REGULADO (una "
    "operación que alguien lleva a cabo), va en **Operacion** aunque el texto "
    "lo enuncie con forma de definición y aunque la unidad entera sea esa "
    "definición. Si el contenido prescribe conducta (deber, prohibición, "
    "permiso), va en el tipo deóntico que corresponda, no acá.\n"
    "   Properties: termino (el término definido, tal como lo nombra el texto), "
    "descripcion (el definiens: cita o paráfrasis fiel).\n\n"
)

_TITULO_TIPOS_VIEJO = "# TIPOS DE ENTIDAD VÁLIDOS (exactamente 6, ningún otro)"
_TITULO_TIPOS_NUEVO = "# TIPOS DE ENTIDAD VÁLIDOS (exactamente 9, ningún otro)"

_TITULO_PREDS_VIEJO = "# PREDICADOS VÁLIDOS (exactamente 12, ningún otro)"
_TITULO_PREDS_NUEVO = "# PREDICADOS VÁLIDOS (exactamente 14, ningún otro)"

_FILA_ESTABLECIDA_VIEJO = (
    "| `establecida_en` | {Restriccion, Obligacion, Excepcion, Operacion} → "
    "TextoOrdenado |"
)
_FILA_ESTABLECIDA_NUEVO = (
    "| `establecida_en` | {Restriccion, Obligacion, Excepcion, Operacion, "
    "Potestad, Condicion, Definicion} → TextoOrdenado |"
)

_FILA_APLICA_VIEJO = (
    "| `aplica_a` | {Restriccion, Obligacion} → SUJETO del catálogo (source = "
    "local_id de la norma; el sujeto va en sujeto_id o sujeto_propuesto, SIN "
    "target) |"
)
_FILA_APLICA_NUEVO = (
    "| `aplica_a` | {Restriccion, Obligacion, Operacion, Excepcion, Potestad} → "
    "SUJETO del catálogo (source = local_id del elemento alcanzado; el sujeto "
    "va en sujeto_id o sujeto_propuesto, SIN target) |"
)

_FILA_CONDICIONA_VIEJO = "| `condiciona` | Obligacion → Operacion |\n"
_FILA_CONDICIONA_NUEVO = (
    "| `condiciona` | Obligacion → Operacion |\n"
    "| `condicion_de` | Condicion → {Excepcion, Obligacion, Restriccion} |\n"
    "| `exceptua_operacion` | Excepcion → Operacion |\n"
)

_REGLA4_VIEJO = (
    "4. **NO inventes tipos ni predicados fuera de las listas.** Si una idea no "
    "encaja en los 6 tipos de entidad o 12 predicados, NO la incluyas. Es "
    "preferible no extraer algo a forzarlo en una caja equivocada."
)
_REGLA4_NUEVO = (
    "4. **NO inventes tipos ni predicados fuera de las listas.** Si una idea no "
    "encaja en los 9 tipos de entidad o 14 predicados, NO la incluyas. Es "
    "preferible no extraer algo a forzarlo en una caja equivocada."
)

_REGLA6_VIEJO = (
    "Luego conectá las Restriccion/Obligacion/Excepcion del chunk al nodo "
    "TextoOrdenado vía `establecida_en`."
)
_REGLA6_NUEVO = (
    "Luego conectá las Restriccion/Obligacion/Excepcion/Potestad/Condicion/"
    "Definicion del chunk al nodo TextoOrdenado vía `establecida_en`."
)

# R4 — regla de omisión declarada de contenido meta-normativo. Se agrega como
# regla 9 al final de REGLAS NO NEGOCIABLES (ancla: la regla 8, que hoy cierra
# la sección).
_REGLA8_VIEJO = (
    '8. **Completitud intra-chunk.** Extraé TODOS los calificadores, '
    'excepciones, salvedades e ítems de enumeración del chunk. Una norma '
    'extraída sin su "salvo...", sin sus incisos o sin sus calificadores es una '
    'extracción DEFECTUOSA aunque el resto esté bien.\n\n'
)
_REGLA8_NUEVO = (
    _REGLA8_VIEJO
    + "9. **CONTENIDO META-NORMATIVO: NO SE EXTRAE.** El contenido que predica "
      "sobre el SIGNIFICADO o el ALCANCE JURÍDICO de un acto o de una norma —y "
      "no sobre la conducta de nadie— NO tiene tipo en este esquema y NO se "
      "extrae en ninguna caja: cláusulas interpretativas (\"lo dispuesto no "
      "implica / no debe entenderse como / no importará\"), declaraciones de "
      "objetivo, finalidad u objeto de las normas, y reglas de vigencia o de "
      "aplicabilidad temporal. No lo fuerces en Restriccion, Obligacion, "
      "Potestad ni Definicion: simplemente no lo extraigas. Justificación: "
      "tiparlo fabrica prohibiciones y deberes que la norma no enuncia y los "
      "ancla en nodos reales del grafo, mientras que no extraerlo produce una "
      "omisión — una pérdida visible y contabilizable, no una afirmación "
      "falsa.\n\n"
)

_LABELS_VIEJO = "Para Obligacion, Restriccion, Excepcion y Operacion:"
_LABELS_NUEVO = ("Para Obligacion, Restriccion, Excepcion, Operacion, Potestad, "
                 "Condicion y Definicion:")

# Orden de aplicación (documentado; los anclas son disjuntos).
REEMPLAZOS: tuple[tuple[str, str, str], ...] = (
    ("R7-operacion-descripcion", _R7_OPERACION_VIEJO, _R7_OPERACION_NUEVO),
    ("R9+R1+R2+R3-tipos", _R9_OBLIGACION_VIEJO, _R9_OBLIGACION_NUEVO),
    ("titulo-tipos-6a9", _TITULO_TIPOS_VIEJO, _TITULO_TIPOS_NUEVO),
    ("titulo-predicados-12a14", _TITULO_PREDS_VIEJO, _TITULO_PREDS_NUEVO),
    ("R1-establecida_en", _FILA_ESTABLECIDA_VIEJO, _FILA_ESTABLECIDA_NUEVO),
    ("R8-aplica_a", _FILA_APLICA_VIEJO, _FILA_APLICA_NUEVO),
    ("R2+R6a-predicados-nuevos", _FILA_CONDICIONA_VIEJO, _FILA_CONDICIONA_NUEVO),
    ("regla4-conteos", _REGLA4_VIEJO, _REGLA4_NUEVO),
    ("regla6-establecida_en", _REGLA6_VIEJO, _REGLA6_NUEVO),
    ("R4-omision-metanormativo", _REGLA8_VIEJO, _REGLA8_NUEVO),
    ("labels-tipos-nuevos", _LABELS_VIEJO, _LABELS_NUEVO),
)


def prefijo_sistema_retocado() -> str:
    """Prefijo de producción con los 9 retoques aplicados. Función PURA y
    determinística: sin fechas, sin aleatoriedad, sin estado. Cada ancla se
    asserta única antes de reemplazar (si prompt_e1 cambiara, revienta acá y no
    en la API)."""
    texto = prompt_e1.PREFIJO_SISTEMA
    for nombre, viejo, nuevo in REEMPLAZOS:
        n = texto.count(viejo)
        if n != 1:
            raise RuntimeError(
                f"reemplazo {nombre}: el ancla aparece {n} veces en el prefijo "
                f"de producción (esperado 1) — prompt_e1 cambió, se frena")
        texto = texto.replace(viejo, nuevo)
    return texto


PREFIJO_SISTEMA_RETOCADO = prefijo_sistema_retocado()


# ========================================================================== #
# TOOL SCHEMA retocado                                                       #
# ========================================================================== #

def _tool_schema_retocado() -> dict:
    """El tool schema de producción con los enums ampliados (9 tipos, 14
    predicados) y la description actualizada a los conteos nuevos. NADA más se
    toca: `additionalProperties` sigue False, los required son los de
    producción, el enum de sujetos no se toca y no se agregan campos.

    El enum de `Obligacion.tipo` NO vive en el tool schema (properties es
    `additionalProperties: {"type": "string"}`, texto libre) — R9 es un cambio
    de texto del prefijo, y el endurecimiento del validador es territorio B5
    (pre-registro §0, dato de registro sobre `registro_contable`)."""
    schema = copy.deepcopy(prompt_e1.TOOL_SCHEMA_E1)
    schema["description"] = (
        "Extrae entidades y relaciones del chunk según el schema cerrado v2 "
        "retocado (9 tipos de entidad, 14 predicados, catálogo cerrado de "
        "sujetos). Todo elemento lleva `punto` (provenance a nivel unidad "
        "estructural, de la lista admitida del chunk)."
    )
    ent = schema["input_schema"]["properties"]["entities"]["items"]["properties"]
    ent["type"]["enum"] = list(ENTITY_TYPES_RETOCADO)
    rel = schema["input_schema"]["properties"]["relations"]["items"]["properties"]
    rel["predicate"]["enum"] = list(PREDICATES_RETOCADO)
    return schema


TOOL_SCHEMA_RETOCADO = _tool_schema_retocado()


def bloques_sistema_retocado() -> list[dict]:
    """D1: `system` como lista de bloques con el breakpoint de caching en el
    último (y único) bloque del prefijo estable."""
    return [
        {
            "type": "text",
            "text": PREFIJO_SISTEMA_RETOCADO,
            "cache_control": {"type": "ephemeral"},
        }
    ]


PREFIJO_CANONICO_RETOCADO = json.dumps(
    {"system": bloques_sistema_retocado(), "tools": [TOOL_SCHEMA_RETOCADO]},
    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
)
PREFIJO_HASH_RETOCADO = hashlib.sha256(
    PREFIJO_CANONICO_RETOCADO.encode("utf-8")).hexdigest()[:12]

# sha256 completo del TEXTO del prefijo retocado (el que va al manifiesto del
# freno 1; el hash corto de arriba es la huella prefijo+tools que particiona el
# namespace, distinta cosa).
PREFIJO_SHA256_RETOCADO = hashlib.sha256(
    PREFIJO_SISTEMA_RETOCADO.encode("utf-8")).hexdigest()


def build_request_kwargs_retocado(chunk: dict, model: str,
                                  max_tokens: int = MAX_OUTPUT_TOKENS) -> dict:
    """Request completo con el prefijo RETOCADO. El mensaje de usuario es el de
    producción sin tocar (`prompt_e1.build_user_message`): lo único que cambia
    entre brazos es el prefijo. Este dict es también la base de la key de caché
    local (llm_cache.canonical_request)."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": bloques_sistema_retocado(),
        "tools": [TOOL_SCHEMA_RETOCADO],
        "tool_choice": {"type": "tool", "name": NOMBRE_TOOL},
        "messages": [{"role": "user", "content": build_user_message(chunk)}],
    }


__all__ = [
    "ENTITY_TYPES_RETOCADO", "PREDICATES_RETOCADO", "OBLIGACION_TIPO_RETOCADO",
    "DOMAIN_RANGE_RETOCADO", "SUJETO_PREDICATES", "SUJETOS_CATALOGO",
    "firma_valida", "PREFIJO_SISTEMA_RETOCADO", "TOOL_SCHEMA_RETOCADO",
    "bloques_sistema_retocado", "build_request_kwargs_retocado",
    "PREFIJO_HASH_RETOCADO", "PREFIJO_SHA256_RETOCADO",
    "PREFIJO_HASH_PRODUCCION_ESPERADO", "REEMPLAZOS", "DECISIONES_DECLARADAS",
    "MAX_OUTPUT_TOKENS", "NOMBRE_TOOL",
]
