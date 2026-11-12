"""
prompt_e1.py — Prompt del extractor E1 (re-extracción v2), fase A.

Estructura gobernada por las 5 decisiones de docs/decisiones_caching_extraccion.md
y por docs/diseno_reextraccion_v2.md §3-E1:

  - PREFIJO ESTABLE (Decisión 1): instrucciones + esquema v2 completo + sistema
    de sujetos + reglas anti-fusión / provenance / labels / contenido no-prosa.
    Va como `system` en lista de bloques con cache_control {"type": "ephemeral"}
    en el último bloque del prefijo. Los tools (contrato estructurado) también
    son estables y forman parte del prefijo cacheado (preceden al system en el
    orden de caching de la API).
  - NADA variable por chunk antes del breakpoint. Todo lo que cambia por chunk
    (texto, herencia, flags, alcance del TO, puntos admitidos) va en el mensaje
    de usuario, después del breakpoint.
  - El prompt es una función PURA del chunk: mismo chunk (dict) → mismo prompt
    byte a byte. Sin fechas, sin aleatoriedad, sin estado.

El esquema v2 se importa de su fuente única (grafo_v2/code/schema.py →
esquema_v2_clases.json v2.0): matriz de firmas DOMAIN_RANGE, catálogo de
sujetos (enum duro en el tool schema) y roles de alcance por TO.
"""

from __future__ import annotations

import copy
import hashlib
import json

import comun_e1  # noqa: F401  (inserta grafo_v2/code en sys.path)
from comun_e1 import chunk_flaggeado, es_mini_chunk, puntos_admitidos
from schema import (
    ENTITY_TYPES,
    PREDICATES,
    SUJETOS_CATALOGO,
    SUJETOS_PROMPT,
    ROL_POR_TO,
    CATALOGO_VERSION,
)

MAX_OUTPUT_TOKENS = 8192  # techo de salida por chunk (igual precedente v2)

NOMBRE_TOOL = "extraer_kg_e1"


# ========================================================================== #
# PREFIJO DE SISTEMA (estable, cacheado)                                     #
# ========================================================================== #

PREFIJO_SISTEMA = f"""Sos un extractor de tripletas para un Knowledge Graph regulatorio del BCRA (Banco Central de la República Argentina). Trabajás sobre UNA unidad de extracción por vez. No ves el resto del corpus ni la salida de otros extractores. La unidad es de uno de dos tipos (el mensaje lo declara):

- **Chunk de punto**: un punto numerado de un Texto Ordenado, más su contexto estructural heredado (encabezados, chapeaux, párrafos introductorios y de cierre de la jerarquía que lo contiene). Extraés SOLO del texto del punto; el contexto heredado orienta y ancla, pero NO se extrae de él (cada bloque heredado tiene su propia unidad de extracción responsable — ver PROVENANCE).
- **Mini-chunk de bloque estructural**: un bloque de prosa de una unidad contenedora (chapeau de sección, párrafo introductorio, intersticial o de cierre), más la cadena de títulos que lo ubica. Ese bloque ES tu unidad: extraé TODO su contenido normativo, exactamente como harías con el texto de un punto.

Trabajás con un schema CERRADO y RÍGIDO (esquema v2, catálogo de sujetos v{CATALOGO_VERSION}). NO inventes tipos. NO inventes predicados. NO inventes sujetos.

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

# PROVENANCE OBLIGATORIA POR ELEMENTO (campo `punto`)

TODA entidad y TODA relación llevan el campo `punto`: la unidad estructural del documento que FUNDA ese elemento. El mensaje del chunk trae la lista cerrada "Puntos admitidos"; `punto` debe ser EXACTAMENTE uno de esos valores.

- Contenido extraído del texto de la unidad (el punto del chunk, o el bloque del mini-chunk) → `punto` = la unidad declarada en el mensaje.
- **EL CONTEXTO ANCLA, LA UNIDAD EXTRAE.** En un chunk de punto, NO extraigas contenido normativo de los bloques heredados (chapeaux, intros, intersticiales, cierres): cada uno de esos bloques es la unidad de extracción de OTRO extractor (su mini-chunk), y extraerlo acá duplicaría y anclaría mal. El contexto heredado sirve para: (i) interpretar el texto del punto (resolver "dichos sujetos", "esa operación", el alcance que el chapeau fija); (ii) anclar en un ancestro un elemento que el TÍTULO de ese ancestro nombra y el texto del punto desarrolla (p. ej. la Operacion que el encabezado del punto contenedor denomina) → ese elemento lleva `punto` = la unidad del ancestro.
- Para una relación, `punto` es la unidad cuyo texto enuncia la conexión (si la norma y su conexión están en el texto de la unidad, es la unidad).
- El nodo TextoOrdenado lleva `punto` = la unidad del chunk.
- Un elemento sin `punto`, o con un `punto` fuera de la lista admitida, se DESCARTA en validación. No inventes unidades.

# REGLAS NO NEGOCIABLES

1. **Los nodos NO son jerarquía documental.** NO crees entidades de tipo "Artículo", "Punto", "Sección", "Capítulo", "Inciso". Si el texto dice "Artículo 12. Las entidades financieras no podrán...", la entidad es la RESTRICCIÓN ("las entidades no podrán..."), no el "Artículo 12". El número de punto va en el campo `punto`, no en una entidad.

2. **Cada entidad debe tener un `local_id` único dentro del chunk** (ej. "e1", "e2", "e3"). Las relations usan esos local_ids como source/target.

3. **Las relations son SOLO entre entidades del MISMO chunk.** No referencies entidades externas.

4. **NO inventes tipos ni predicados fuera de las listas.** Si una idea no encaja en los 6 tipos de entidad o 12 predicados, NO la incluyas. Es preferible no extraer algo a forzarlo en una caja equivocada.

5. **ANTI-FUSIÓN: cláusulas parecidas NO se colapsan.** Si el chunk contiene dos o más cláusulas casi idénticas que difieren en valores, umbrales, calificadores, sujetos alcanzados o modalidad (deber/prohibición/excepción), cada una es una entidad SEPARADA con su propia description y su propio `punto`. NUNCA las resumas en una sola entidad "representativa". Tampoco omitas una cláusula porque "ya extrajiste una parecida": la deduplicación entre variantes es trabajo de una etapa posterior con más contexto; tu trabajo es extraer cada variante fiel y completa.

6. **Siempre incluí un nodo TextoOrdenado con local_id "to" en CADA chunk** (representando el TO del que sale el chunk). Luego conectá las Restriccion/Obligacion/Excepcion del chunk al nodo TextoOrdenado vía `establecida_en`. El label del TextoOrdenado debe ser corto (ver regla de labels).

7. **Enumeraciones de sujetos: UNA RELACIÓN POR SUJETO.** Si el texto enumera varios sujetos alcanzados (separados por comas, "y", "o", "u otros"), generá una relación `aplica_a` (o `ejecuta`) POR CADA sujeto, cada una con su propio sujeto_id del catálogo. NO metas la enumeración entera en un solo sujeto_propuesto.

8. **Completitud intra-chunk.** Extraé TODOS los calificadores, excepciones, salvedades e ítems de enumeración del chunk. Una norma extraída sin su "salvo...", sin sus incisos o sin sus calificadores es una extracción DEFECTUOSA aunque el resto esté bien.

# LABELS: CORTOS Y CON LO DISTINTIVO ADELANTE

Para Obligacion, Restriccion, Excepcion y Operacion:
- `label`: nombre CANÓNICO. Máximo **8 palabras**. NO copies la oración del corpus.
- `properties.descripcion`: la oración o cita textual del corpus (acá va el contenido largo, sin tope).
- **El contenido DISTINTIVO va AL PRINCIPIO del label.** Los labels se truncan al mostrarse: si varios elementos hermanos comparten el mismo prefijo y se diferencian recién al final, quedan indistinguibles. Poné primero lo que distingue, después lo común.
  ✓ "Tope USD 200 mensual — compra de moneda extranjera" / "Declaración jurada previa — compra de moneda extranjera" / "Excepción no residentes — compra de moneda extranjera"
  ✗ MAL (prefijo común, diferencia al final): "Compra de moneda extranjera por personas humanas: tope USD 200" / "Compra de moneda extranjera por personas humanas: declaración jurada" / "Compra de moneda extranjera por personas humanas: excepción no residentes"

Para Comunicacion: `label` es el código corto ("Com. A 7825"). Para TextoOrdenado: nombre conceptual corto (máximo 5 palabras).

# CONTENIDO NO-PROSA (chunks flaggeados por E0)

Si el mensaje del chunk trae un bloque "FLAGS E0" (contenido tabular y/o fórmulas detectados determinísticamente), ese contenido está DECLARADO NO-CONFIABLE en su forma extraída del PDF:

- NO reconstruyas tablas ni fórmulas: la estructura visual (columnas, alineación, sub/superíndices) pudo haberse destruido en la extracción del PDF, y una lectura "prolija" de texto destrozado fabrica contenido falso.
- Extraé SOLO lo que la prosa circundante sostiene por sí sola (el enunciado de que existe una exigencia, quién la cumple, a qué operación refiere).
- NO copies valores numéricos de celdas de tabla ni coeficientes de fórmulas a properties (umbral, plazo) salvo que la prosa los enuncie en una oración completa.
- Registrá en `omisiones_no_prosa` (lista de strings, uno por omisión) qué contenido quedó afuera y por qué (ej.: "tabla de ponderadores por grupo: estructura tabular no confiable, valores no extraídos").
- Si el chunk entero es tabla/fórmula y nada es extraíble con confianza, devolvé entities/relations con lo mínimo sostenible (puede ser solo el nodo TextoOrdenado) y registrá la omisión. Un chunk flaggeado SIN omisiones registradas y CON valores numéricos extraídos es una extracción sospechosa.

# EJEMPLOS NEGATIVOS (qué NO hacer)

- ❌ Entidad de tipo "Artículo" → usá Restriccion/Obligacion según corresponda. El número de punto va en `punto`.
- ❌ Predicado "regulado_por" o "contiene" o "se_aplica_si" → no están en la lista de 12.
- ❌ Restriccion --aplica_a--> Operacion → MAL, `aplica_a` requiere un SUJETO del catálogo como rango (sujeto_id). Usá `regula` o `prohibe`/`limita`.
- ❌ Restriccion --exceptua--> Operacion → MAL, `exceptua` requiere Excepcion como dominio y Restriccion como rango.
- ❌ Entidad de tipo "EntidadFinanciera" o "Sujeto" → los sujetos NO son entidades del chunk: van en sujeto_id/sujeto_propuesto de aplica_a/ejecuta.
- ❌ sujeto_id "Sujeto_entidad_financiera" para "empresas de seguros" → si el sujeto no matchea entrada ni alias del catálogo, usá sujeto_propuesto; NO fuerces el más parecido.
- ❌ Texto plano "Punto 3.2.1." como entidad → es jerarquía documental, va en `punto`.
- ❌ Fusionar "límite del 125 % para X" y "límite del 125 % para Y" en una sola Restricción → son cláusulas separadas con provenance separada (regla anti-fusión).

# REGLA `regula` / `prohibe` / `limita` (importante)

Tres predicados Restriccion→Operacion. NO son intercambiables. Elegí según `Restriccion.tipo`:

- Si `Restriccion.tipo = "prohibicion"` → usá `prohibe`. Patrón: "no podrá", "se prohíbe", "queda prohibido".
- Si `Restriccion.tipo = "limite_cuantitativo"` (hay umbral numérico: %, $, monto) → usá `limita`.
- Si `Restriccion.tipo = "limite_cualitativo"` (restricción cualitativa sin monto) → usá `limita`.
- `regula` queda RESERVADO para Obligacion→Operacion. Cuando una Obligacion regula cómo se hace una Operacion, usá `regula`.

✅ Restriccion(tipo=prohibicion) --prohibe--> Operacion
✅ Restriccion(tipo=limite_cuantitativo, umbral="10%") --limita--> Operacion
✅ Restriccion(tipo=limite_cualitativo) --limita--> Operacion
✅ Obligacion --regula--> Operacion
❌ Restriccion(tipo=limite_cuantitativo) --regula--> Operacion  ← MAL, usá `limita`
❌ Restriccion(tipo=prohibicion) --regula--> Operacion  ← MAL, usá `prohibe`

# FORMATO DE SALIDA

Llamá la herramienta `{NOMBRE_TOOL}` con el schema dado. Si el chunk no tiene contenido normativo extraíble (preámbulo vacío, lista de abreviaturas, etc.), devolvé entities y relations vacíos (el nodo TextoOrdenado igual va). Todo elemento lleva `punto`.
"""


# ========================================================================== #
# CANAL ABIERTO EXPERIMENTAL (flag explícito, apagado por defecto)           #
# ========================================================================== #
# Bloque ADITIVO para corridas con canal abierto (ESQ-1): se APPENDEA al
# final del prefijo estable, sin tocar una letra del prefijo de producción.
# Con canal_abierto=False (default en todo call site) el prefijo, el tool
# schema y el hash son byte-idénticos a los de producción. Sin ejemplos de
# valores propuestos: un ejemplo inventado sembraría cadenas en la medición.

BLOQUE_CANAL_ABIERTO = """
# CANAL ABIERTO EXPERIMENTAL: tipo_propuesto / predicado_propuesto

Esta corrida habilita un canal de escape declarado, análogo a `sujeto_propuesto`. El esquema cerrado sigue vigente: los 6 tipos y los 12 predicados se usan SIEMPRE que el contenido encaje, con todas las reglas de arriba.

- Si el chunk contiene contenido normativo CLARO que no encaja en NINGUNO de los 6 tipos de entidad, en lugar de omitirlo (regla 4), emití la entidad con `tipo_propuesto` (texto libre: nombre corto y canónico del tipo que proponés) y SIN `type`. `type` y `tipo_propuesto` son MUTUAMENTE EXCLUYENTES: exactamente uno de los dos. El resto de la entidad va igual (local_id, label, punto, properties).
- Si una conexión normativa CLARA entre elementos del chunk no encaja en NINGÚN predicado de la lista de 12 (por vocabulario o por dominio/rango), en lugar de omitirla, emití la relación con `predicado_propuesto` (texto libre: nombre corto del predicado que proponés) y SIN `predicate`. `predicate` y `predicado_propuesto` son MUTUAMENTE EXCLUYENTES: exactamente uno de los dos. La relación lleva igual su `punto` y sus extremos.
- NO uses el canal para variantes léxicas de lo que el esquema ya nombra: si encaja en el enum, va en el enum. NO fuerces una caja equivocada: ante la duda entre forzar y proponer, proponé.
"""


# Cierres del system neutralizados SOLO en modo abierto (adenda P1″,
# data/experiment/esq/adenda_prerregistro_esq1_P1ter.md §3, sellada por
# commit): los dos textos de producción se reemplazan por los sellados
# verbatim en la adenda ÚNICAMENTE cuando canal_abierto=True. El texto de
# producción (PREFIJO_SISTEMA y la rama con el flag apagado) no cambia una
# letra. Las líneas envueltas del blockquote de la adenda se unen con espacio
# (semántica markdown de soft-wrap); el selftest verifica la igualdad contra
# el texto extraído de la adenda misma.
CIERRE_CATALOGO_PROD = "TIPOS DE ENTIDAD VÁLIDOS (exactamente 6, ningún otro)"
CIERRE_CATALOGO_ABIERTO = (
    "TIPOS DE ENTIDAD DEL CATÁLOGO (6) — si un contenido normativo claro no "
    "encaja en ninguno, NO lo fuerces: emitilo por el canal abierto "
    "(`tipo_propuesto`)."
)
CIERRE_REGLA4_PROD = (
    "**NO inventes tipos ni predicados fuera de las listas.** Si una idea no "
    "encaja en los 6 tipos de entidad o 12 predicados, NO la incluyas. Es "
    "preferible no extraer algo a forzarlo en una caja equivocada."
)
CIERRE_REGLA4_ABIERTO = (
    "**NO fuerces contenido en cajas equivocadas.** Si una idea no encaja en "
    "los 6 tipos de entidad o en los 12 predicados, NO la fuerces en el tipo "
    "o predicado más parecido NI la omitas: emitila por el canal abierto "
    "(`tipo_propuesto` para entidades, `predicado_propuesto` para "
    "relaciones). Forzar una caja equivocada es peor que proponer."
)


def prefijo_sistema(canal_abierto: bool = False) -> str:
    """Texto del system. Flag apagado: el de producción tal cual (byte-idéntico,
    sin transformación alguna). Canal abierto (adenda P1″): el de producción
    con los DOS cierres reemplazados por los textos sellados de la adenda §3,
    MÁS el bloque experimental appendeado. Desde P1″ el modo abierto ya NO es
    aditivo (adenda §5.b: se rompe la aditividad y ESQ-1 mide bajo un prompt
    de medición distinto del de producción)."""
    if not canal_abierto:
        return PREFIJO_SISTEMA
    assert PREFIJO_SISTEMA.count(CIERRE_CATALOGO_PROD) == 1
    assert PREFIJO_SISTEMA.count(CIERRE_REGLA4_PROD) == 1
    neutralizado = (PREFIJO_SISTEMA
                    .replace(CIERRE_CATALOGO_PROD, CIERRE_CATALOGO_ABIERTO)
                    .replace(CIERRE_REGLA4_PROD, CIERRE_REGLA4_ABIERTO))
    return neutralizado + BLOQUE_CANAL_ABIERTO


# ========================================================================== #
# TOOL SCHEMA (contrato estructurado — estable, parte del prefijo cacheado)  #
# ========================================================================== #

TOOL_SCHEMA_E1 = {
    "name": NOMBRE_TOOL,
    "description": (
        "Extrae entidades y relaciones del chunk según el schema cerrado v2 "
        "(6 entidades, 12 predicados, catálogo cerrado de sujetos). Todo "
        "elemento lleva `punto` (provenance a nivel unidad estructural, de la "
        "lista admitida del chunk)."
    ),
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
                        "label": {"type": "string", "description": "Etiqueta corta y canónica, contenido distintivo al principio."},
                        "punto": {"type": "string", "description": "Unidad estructural que funda la entidad. Uno de los 'Puntos admitidos' del mensaje del chunk."},
                        "properties": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Properties de la entidad. Ver definición de cada tipo.",
                        },
                    },
                    "required": ["local_id", "type", "label", "punto"],
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
                        "punto": {"type": "string", "description": "Unidad estructural cuyo texto enuncia la conexión. Uno de los 'Puntos admitidos' del mensaje del chunk."},
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
                    "required": ["predicate", "punto"],
                    "additionalProperties": False,
                },
            },
            "omisiones_no_prosa": {
                "type": "array",
                "items": {"type": "string"},
                "description": "SOLO chunks con FLAGS E0: qué contenido tabular/fórmula quedó sin extraer y por qué. Vacío u omitido en chunks sin flags.",
            },
        },
        "required": ["entities", "relations"],
        "additionalProperties": False,
    },
}


def _tool_schema_canal_abierto() -> dict:
    """Tool schema de la corrida con canal abierto: el de producción MÁS los
    dos campos propuestos, calcados de sujeto_propuesto. Los enums NO se
    tocan (el canal convive con el catálogo, igual que sujeto_propuesto);
    additionalProperties sigue False (los campos se DECLARAN, el schema no se
    abre). `type`/`predicate` dejan de ser required SOLO acá: la exclusión
    mutua exacta (uno de los dos) la exige el validador, como con
    sujeto_id/sujeto_propuesto.

    La `description` del tool se REEMPLAZA solo en este modo (adenda P1′,
    entrada 4.ii de la cola de mejoras): la de producción anuncia «schema
    cerrado v2» y contradecía al bloque del canal abierto del system. La
    nueva describe los dos campos propuestos y su exclusión mutua, sin
    ejemplos de valores de tipos ni de predicados (no sembrar)."""
    schema = copy.deepcopy(TOOL_SCHEMA_E1)
    schema["description"] = (
        "Extrae entidades y relaciones del chunk según el esquema v2 (6 tipos "
        "de entidad, 12 predicados, catálogo cerrado de sujetos), con canal "
        "abierto declarado: una entidad cuyo contenido normativo no encaja en "
        "ningún type del enum lleva `tipo_propuesto` (texto libre) y SIN "
        "`type`; una relación que no encaja en ningún predicate del enum "
        "lleva `predicado_propuesto` (texto libre) y SIN `predicate`. "
        "`type`/`tipo_propuesto` y `predicate`/`predicado_propuesto` son "
        "mutuamente excluyentes: exactamente uno de cada par. Todo elemento "
        "lleva `punto` (provenance a nivel unidad estructural, de la lista "
        "admitida del chunk)."
    )
    ent = schema["input_schema"]["properties"]["entities"]["items"]
    ent["properties"]["tipo_propuesto"] = {
        "type": "string",
        "description": (
            "SOLO canal abierto: nombre corto y canónico del tipo de entidad "
            "que proponés, cuando el contenido normativo NO encaja en ninguno "
            "de los 6 tipos del enum. Mutuamente excluyente con type: "
            "exactamente uno de los dos."
        ),
    }
    ent["required"] = ["local_id", "label", "punto"]
    rel = schema["input_schema"]["properties"]["relations"]["items"]
    rel["properties"]["predicado_propuesto"] = {
        "type": "string",
        "description": (
            "SOLO canal abierto: nombre corto del predicado que proponés, "
            "cuando la conexión normativa NO encaja en ningún predicado del "
            "enum (por vocabulario o por dominio/rango). Mutuamente "
            "excluyente con predicate: exactamente uno de los dos."
        ),
    }
    rel["required"] = ["punto"]
    return schema


TOOL_SCHEMA_E1_CANAL_ABIERTO = _tool_schema_canal_abierto()


def tool_schema_e1(canal_abierto: bool = False) -> dict:
    """Tool schema según el flag. Con el flag apagado devuelve EL MISMO objeto
    de producción (byte-idéntico por construcción)."""
    return TOOL_SCHEMA_E1_CANAL_ABIERTO if canal_abierto else TOOL_SCHEMA_E1


def bloques_sistema(canal_abierto: bool = False) -> list[dict]:
    """`system` como lista de bloques con el breakpoint de caching declarado en
    el ÚLTIMO bloque del prefijo estable (Decisión 1). Nada variable por chunk
    entra acá — el flag canal_abierto no varía por chunk: es un prefijo
    distinto, estable dentro de su corrida, con su propio namespace."""
    return [
        {
            "type": "text",
            "text": prefijo_sistema(canal_abierto),
            "cache_control": {"type": "ephemeral"},
        }
    ]


# Huella del prefijo completo (system + tools): identifica el contrato estable.
# Cambia el prefijo → cambia el hash → el selftest y el namespace lo detectan.
PREFIJO_CANONICO = json.dumps(
    {"system": bloques_sistema(), "tools": [TOOL_SCHEMA_E1]},
    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
)
PREFIJO_HASH = hashlib.sha256(PREFIJO_CANONICO.encode("utf-8")).hexdigest()[:12]

# Huella del prefijo con canal abierto: DISTINTA por construcción → particiona
# el namespace de caché (candado U-ESQ-0: prefijo nuevo, corrida se paga
# completa; jamás pisa las keys de producción).
PREFIJO_CANONICO_CANAL_ABIERTO = json.dumps(
    {"system": bloques_sistema(canal_abierto=True),
     "tools": [TOOL_SCHEMA_E1_CANAL_ABIERTO]},
    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
)
PREFIJO_HASH_CANAL_ABIERTO = hashlib.sha256(
    PREFIJO_CANONICO_CANAL_ABIERTO.encode("utf-8")).hexdigest()[:12]


def prefijo_hash(canal_abierto: bool = False) -> str:
    return PREFIJO_HASH_CANAL_ABIERTO if canal_abierto else PREFIJO_HASH


# ========================================================================== #
# MENSAJE DE USUARIO (variable por chunk — después del breakpoint)           #
# ========================================================================== #

def build_user_message(chunk: dict) -> str:
    """Único contenido variable del request. Función pura del dict del chunk:
    mismo chunk → mismo mensaje byte a byte."""
    partes: list[str] = []
    mini = es_mini_chunk(chunk)

    partes.append(f"Documento fuente: {chunk['archivo']}")
    partes.append(f"TO: {chunk['to']}")
    if mini:
        partes.append(
            f"Tipo de unidad: MINI-CHUNK de bloque estructural "
            f"({chunk['rol_bloque']} del punto {chunk['unidad']})"
        )
        partes.append(f"Unidad de origen: {chunk['unidad']} — {chunk['titulo']}")
    else:
        partes.append("Tipo de unidad: chunk de punto")
        partes.append(f"Punto del chunk: {chunk['unidad']} — {chunk['titulo']}")
    partes.append(
        "Puntos admitidos para `punto`: " + ", ".join(puntos_admitidos(chunk))
    )
    partes.append("")

    rol = ROL_POR_TO.get(chunk["archivo"])
    if rol is not None:
        miembros = ", ".join(rol["miembros_labels"])
        partes.append(
            f"Alcance de este TO: {rol['rol_id']} = {{{miembros}}}. "
            f"Cuando la norma se dirija genéricamente a 'las entidades' / 'los sujetos obligados' / "
            f"el colectivo del TO, usá {rol['rol_id']} como sujeto."
        )
        partes.append("")

    herencia = chunk.get("herencia", [])
    if herencia:
        if mini:
            partes.append("Cadena de títulos (ubica el bloque; NO es contenido a extraer):")
        else:
            partes.append(
                "Contexto estructural heredado (SOLO contexto y anclaje: NO extraigas "
                "contenido normativo de estos bloques — cada uno tiene su propia unidad "
                "de extracción; ver PROVENANCE):"
            )
        for h in herencia:
            partes.append(f"[{h['tipo']} | punto {h['unidad_origen']}]")
            partes.append(h["texto"])
        partes.append("")

    if chunk_flaggeado(chunk):
        flags = chunk["flags"]
        tipos_flag = []
        if flags.get("contenido_tabular"):
            tipos_flag.append("contenido tabular")
        if flags.get("formula"):
            tipos_flag.append("fórmulas")
        partes.append(
            f"FLAGS E0: este chunk contiene {' y '.join(tipos_flag)} "
            f"(detección determinística). Ese contenido está declarado NO-CONFIABLE: "
            f"aplicá la sección CONTENIDO NO-PROSA del sistema (no reconstruir, no forzar "
            f"extracción, registrar omisiones en `omisiones_no_prosa`)."
        )
        evidencia = (flags.get("evidencia_tabular") or []) + (flags.get("evidencia_formula") or [])
        for ev in evidencia:
            partes.append(f"  evidencia: {ev}")
        partes.append("")

    if mini:
        partes.append(
            f"Texto del bloque {chunk['rol_bloque']} del punto {chunk['unidad']} "
            f"(TU unidad de extracción):"
        )
    else:
        partes.append(f"Texto del punto {chunk['unidad']}:")
    partes.append("```")
    partes.append(chunk["texto"])
    partes.append("```")
    partes.append("")
    partes.append(
        "Extraé las entidades y relaciones según el schema. Recordá: nodo TextoOrdenado "
        "con local_id='to', todo elemento con `punto` de la lista admitida."
    )

    return "\n".join(partes)


def build_request_kwargs(chunk: dict, model: str, max_tokens: int = MAX_OUTPUT_TOKENS,
                         canal_abierto: bool = False) -> dict:
    """Request completo para client.messages.create(**kwargs). Prefijo estable
    (system + tools + tool_choice) idéntico entre chunks; lo variable, solo en
    messages. Este dict es también la base de la key de caché local
    (llm_cache.canonical_request). canal_abierto se pasa EXPLÍCITO por el call
    site (default False = producción, byte-idéntico): no se infiere ni se
    hereda de entorno."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": bloques_sistema(canal_abierto),
        "tools": [tool_schema_e1(canal_abierto)],
        "tool_choice": {"type": "tool", "name": NOMBRE_TOOL},
        "messages": [{"role": "user", "content": build_user_message(chunk)}],
    }
