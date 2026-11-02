"""
prompt_e3.py — Prompt del verificador de completitud intra-unidad E3 (T1).

Diseño vinculante (docs/diseno_reextraccion_v2.md §3-E3):
  - CONTEXTO FRESCO: el verificador recibe SOLO datos — el texto fuente
    íntegro de la unidad (punto propio + herencia, de E0) y lo extraído de
    ella (de E1, post-validación, en formato legible). Jamás el contexto del
    extractor (principio 2.c). El selftest verifica que ninguna instrucción
    del prompt de E1 aparezca en el request de E3.
  - Blanco: AMPUTACIONES — el punto está presente pero despojado de
    calificadores, excepciones, ítems de enumeración o modalidad.
  - Feedback ESTRUCTURADO por faltante: tipo, cita textual del fuente no
    representada, ubicación, severidad.
  - Calibración con EJEMPLOS RESUELTOS del backlog (hallazgo H12: los jueces
    honran ejemplos y circunvalan reglas), construidos en calibradores_e3.py.
  - El verificador JAMÁS corrige: detecta y documenta. Corregir es del
    extractor (mini-ratchet, ratchet_e3.py) o del humano.

Estructura de caching (mismas 5 decisiones de docs/decisiones_caching_extraccion.md
que gobiernan E1): PREFIJO ESTABLE (instrucciones + contrato + calibradores)
como `system` en lista de bloques con cache_control ephemeral en el último
bloque; los tools (contrato estructurado) son estables y forman parte del
prefijo cacheado. TODO lo variable por unidad (fuente + extracción) va en el
mensaje de usuario, después del breakpoint. El prompt es función PURA de
(chunk, validación): mismos datos → mismo request byte a byte.
"""

from __future__ import annotations

import hashlib
import json

import comun_e3
from comun_e3 import fuente_integro, render_extraccion
import calibradores_e3

MAX_OUTPUT_TOKENS = 4096  # el veredicto es corto; techo holgado para faltantes múltiples

NOMBRE_TOOL = "verificar_completitud_e3"

TIPOS_FALTANTE = (
    "enumeracion_incompleta",
    "calificador_despojado",
    "excepcion_ausente",
    "modalidad_perdida",
    "contenido_tabular_no_declarado",
    "otro",
)

SEVERIDADES = ("alta", "media", "baja")


# ========================================================================== #
# PREFIJO DE SISTEMA (estable, cacheado) — parte 1: instrucciones            #
# ========================================================================== #

INSTRUCCIONES = """Sos un verificador de completitud para la construcción de un Knowledge Graph regulatorio del BCRA (Banco Central de la República Argentina). Trabajás con CONTEXTO FRESCO: no viste la conversación del extractor ni el resto del corpus. Recibís exactamente dos cosas, como datos: (1) el texto fuente ÍNTEGRO de una unidad estructural (el punto numerado de un Texto Ordenado más su contexto estructural heredado — encabezados, párrafos introductorios, intersticiales y de cierre de la jerarquía que lo contiene, cada bloque con su unidad de origen), y (2) los elementos que un extractor independiente extrajo de esa unidad (entidades con propiedades y relaciones, ya validados estructuralmente).

# TU TAREA

Identificar contenido NORMATIVO del texto fuente que NO está representado en lo extraído. Tu blanco son las AMPUTACIONES: el punto está presente pero llegó despojado de calificadores, excepciones, ítems de enumeración o modalidad. La evidencia del proyecto muestra que estas amputaciones sobreviven a extractores que tienen el texto completo a la vista: por eso existís vos, en contexto separado.

VOS JAMÁS CORREGÍS. No propongas la extracción arreglada, no redactes entidades, no completes descripciones. Detectás y documentás; corregir es trabajo del extractor (que recibirá tu feedback) o de revisión humana.

# QUÉ CUENTA COMO "REPRESENTADO"

Un contenido del fuente está representado si su sustancia normativa aparece en lo extraído: en la descripcion u otra property de alguna entidad, en el label, o expresado estructuralmente por una relación (p. ej. una salvedad capturada como nodo Excepcion conectado a su norma). NO se exige copia verbatim: una paráfrasis que conserva quién / qué / cuánto / cuándo / salvo qué / con qué modalidad es representación válida. La representación puede estar anclada al punto propio o a la unidad de origen del bloque heredado.

# TIPOS DE FALTANTE (exactamente estos 6)

1. `enumeracion_incompleta` — el fuente enumera ítems, categorías, incisos o renglones y lo extraído omite alguno, o omite la cláusula que ordena la enumeración.
2. `calificador_despojado` — una norma está extraída pero perdió un calificador que restringe o precisa su alcance: temporal ("informada en el mes n"), cuantitativo ("hasta el 10 %"), condicional ("siempre que...", "en la medida en que..."), o de sujeto ("cuando el sujeto obligado así lo disponga").
3. `excepcion_ausente` — una salvedad del fuente ("salvo", "excepto", "no aplicará cuando", "quedan excluidas") no aparece ni en descripciones ni como nodo Excepcion.
4. `modalidad_perdida` — la modalidad deóntica del fuente (deber / prohibición / facultad "podrá") quedó invertida o borrada en lo extraído.
5. `contenido_tabular_no_declarado` — la unidad contiene contenido tabular o fórmulas con sustancia normativa que NO fue extraído NI declarado por el extractor en sus omisiones no-prosa. Si el extractor declaró la omisión, NO es faltante: es el tratamiento correcto del contenido no-confiable.
6. `otro` — contenido normativo no representado que no encaja en 1-5 (p. ej. una norma entera de un párrafo heredado sin ningún elemento que la porte).

# QUÉ NO ES FALTANTE (no lo marques)

- Paráfrasis, reordenamientos o recortes de redacción que conservan la sustancia normativa.
- Labels cortos: el label es un nombre canónico de pocas palabras; el contenido vive en descripcion.
- Encabezados puros, títulos, numeración, referencias de índice: jerarquía documental, no contenido normativo.
- La elección de granularidad de sujetos, tipos de entidad o predicados: eso lo controla otra capa (validación de esquema). Vos verificás CONTENIDO, no modelado.
- Contenido tabular o fórmulas cuya omisión el extractor DECLARÓ en sus omisiones no-prosa.
- Contenido de otras unidades del documento que no está en el fuente que recibiste.
- Prosa no normativa: aclaraciones históricas, notas editoriales, remisiones puras ("ver punto 2.4.") sin mandato propio.

# SEVERIDAD

- `alta`: el faltante cambia una respuesta regulatoria — quién está alcanzado, qué está permitido/prohibido, un umbral, un plazo, una excepción, un ítem de enumeración normativa.
- `media`: precisión secundaria cuya ausencia degrada la respuesta sin invertirla (un calificador redundante con otro ya representado, un detalle de procedimiento).
- `baja`: matiz menor, redacción, contenido de dudosa sustancia normativa. Ante la duda entre marcar con severidad baja y no marcar, marcá con severidad baja: la decisión de re-extraer usa la lista completa.

# CONTRATO DE SALIDA

Llamá SIEMPRE a la herramienta `verificar_completitud_e3`:

- Si todo el contenido normativo del fuente está representado: `veredicto = "completo_ok"` y `faltantes = []`.
- Si no: `veredicto = "faltantes_detectados"` y un elemento en `faltantes` por cada omisión, con:
  - `tipo`: uno de los 6 tipos.
  - `cita_textual_del_fuente`: la cita VERBATIM del fuente no representada (copiala del texto fuente, guiones de corte de línea incluidos si los tiene; NUNCA la parafrasees — se verifica automáticamente contra el fuente y una cita que no aparece invalida el faltante). Citá la cláusula mínima autocontenida: el renglón, la salvedad o el ítem completo.
  - `ubicacion`: la unidad estructural donde vive la cita (el punto propio, o la unidad de origen del bloque heredado tal como figura en el fuente).
  - `severidad`: alta | media | baja.
  - `nota` (opcional): una línea sobre qué se perdió respecto de lo extraído.

Un faltante por omisión: si un mismo renglón perdió dos calificadores distintos, son dos faltantes con dos citas. No agrupes.
"""


# ========================================================================== #
# PREFIJO — parte 2: calibradores (ejemplos resueltos)                       #
# ========================================================================== #

def _render_calibrador(cal: dict) -> str:
    veredicto_json = json.dumps(cal["veredicto"], ensure_ascii=False, indent=1)
    return "\n".join([
        f"## {cal['id']} — {cal['titulo']}",
        "",
        "TEXTO FUENTE ÍNTEGRO DE LA UNIDAD:",
        "```",
        cal["fuente"],
        "```",
        "",
        "ELEMENTOS EXTRAÍDOS DE ESTA UNIDAD:",
        "```",
        render_extraccion(cal["extraccion"]),
        "```",
        "",
        f"VEREDICTO CORRECTO (input de `{NOMBRE_TOOL}`):",
        "```json",
        veredicto_json,
        "```",
        "",
        f"PORQUÉ: {cal['porque']}",
    ])


CALIBRADORES = calibradores_e3.construir_calibradores()

BLOQUE_CALIBRADORES = "\n".join(
    ["# EJEMPLOS RESUELTOS (calibran tu criterio; casos reales del proyecto)", ""]
    + [_render_calibrador(c) + "\n" for c in CALIBRADORES]
)

PREFIJO_SISTEMA = INSTRUCCIONES + "\n" + BLOQUE_CALIBRADORES


# ========================================================================== #
# TOOL SCHEMA (contrato estructurado — estable, parte del prefijo cacheado)  #
# ========================================================================== #

TOOL_SCHEMA_E3 = {
    "name": NOMBRE_TOOL,
    "description": (
        "Reporta el veredicto de completitud de la unidad: completo_ok, o la "
        "lista de faltantes (contenido normativo del fuente no representado en "
        "lo extraído), cada uno con tipo, cita textual verbatim del fuente, "
        "ubicación y severidad."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "veredicto": {
                "type": "string",
                "enum": ["completo_ok", "faltantes_detectados"],
                "description": "completo_ok exige faltantes = []; faltantes_detectados exige al menos un faltante.",
            },
            "faltantes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tipo": {"type": "string", "enum": list(TIPOS_FALTANTE)},
                        "cita_textual_del_fuente": {
                            "type": "string",
                            "description": "Cita VERBATIM del texto fuente no representada. Se verifica automáticamente contra el fuente: no parafrasear.",
                        },
                        "ubicacion": {
                            "type": "string",
                            "description": "Unidad estructural donde vive la cita (punto propio o unidad de origen del bloque heredado).",
                        },
                        "severidad": {"type": "string", "enum": list(SEVERIDADES)},
                        "nota": {
                            "type": "string",
                            "description": "Opcional: una línea sobre qué se perdió respecto de lo extraído.",
                        },
                    },
                    "required": ["tipo", "cita_textual_del_fuente", "ubicacion", "severidad"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["veredicto", "faltantes"],
        "additionalProperties": False,
    },
}


def bloques_sistema() -> list[dict]:
    """`system` como lista de bloques con el breakpoint de caching declarado
    en el ÚLTIMO bloque del prefijo estable (Decisión 1). Nada variable por
    unidad entra acá."""
    return [
        {
            "type": "text",
            "text": PREFIJO_SISTEMA,
            "cache_control": {"type": "ephemeral"},
        }
    ]


# Huella del prefijo completo (system + tools): identifica el contrato estable.
PREFIJO_CANONICO = json.dumps(
    {"system": bloques_sistema(), "tools": [TOOL_SCHEMA_E3]},
    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
)
PREFIJO_HASH = hashlib.sha256(PREFIJO_CANONICO.encode("utf-8")).hexdigest()[:12]


# ========================================================================== #
# MENSAJE DE USUARIO (variable por unidad — después del breakpoint)          #
# ========================================================================== #

def _nota_flags_e0(flags: dict) -> str | None:
    """La NOTA de los flags de E0 (tablas y fórmulas), la de siempre."""
    if not (flags.get("contenido_tabular") or flags.get("formula")):
        return None
    tipos_flag = []
    if flags.get("contenido_tabular"):
        tipos_flag.append("contenido tabular")
    if flags.get("formula"):
        tipos_flag.append("fórmulas")
    return (
        f"NOTA: esta unidad tiene {' y '.join(tipos_flag)} detectados "
        f"determinísticamente (flag de E0). El extractor tenía instrucción de "
        f"NO reconstruir ese contenido y declarar las omisiones. Evaluá el "
        f"tratamiento: contenido tabular/fórmula normativo ni extraído ni "
        f"declarado es faltante tipo contenido_tabular_no_declarado; declarado, no."
    )


# U-PROMPT-R2, P3b, punto i (hallazgo 3.4): NOTA de las omisiones que el esquema deja afuera a propósito. Va cuando
# la validación declara omisiones de esas categorías; en el mensaje aparecen como «[categoría] tramo — nota»
# (validador_e1.proyectar_r2). Texto de P3c, punto a (aprobado en el FRENO P3c-1, 438bbd5; enmienda 7 a L-ESQ-R2): el
# alcance sale de `meta_normativo` y la lista de lo que no puede declararse así es la de la regla 9.
NOTA_E3_OMISIONES = (
    "NOTA: el extractor declaró, en las omisiones, tramos que el esquema deja afuera a propósito: "
    "[meta_normativo] (contenido sobre el sentido, el objetivo o la entrada en vigencia de una norma, que no prescribe "
    "la conducta de nadie ni dice a quién o a qué se aplica), [fuera_de_tipos] (contenido normativo que ningún tipo del "
    "esquema representa) y [relacion_sin_predicado] (un vínculo que ningún predicado del esquema representa). Un tramo "
    "declarado así no es un faltante: no lo reclames. Sí es un faltante si lo declarado no es lo que dice su categoría: "
    "un deber, una prohibición, una facultad, una condición, una excepción, un alcance o una modalidad declarados como "
    "meta-normativos.")
# NOTA del encabezado de lista (nota del 03/10/2026 al mandato; P3c-2: constante del módulo, para que el selftest de
# claves pueda variarla). Su última oración es la de P3c, punto b (aprobada en el FRENO P3c-1).
NOTA_E3_ENCABEZADO_LISTA = (
    "NOTA: esta unidad es el encabezado de una lista (su texto termina en «:»); los ítems son los puntos "
    "que siguen, cada uno con su propia unidad. En esta extracción se componen en cada ítem el sujeto, la "
    "modalidad y el cuantificador del encabezado, y también lo que el encabezado fija para cada ítem (un "
    "plazo, un ámbito, una condición que vale para todos los ítems). Esta unidad no emite un nodo por el "
    "solo anuncio de la lista ni repite lo que se compone en los ítems: que falten aquí no es faltante. "
    "Sí es faltante, si no fue extraído, lo que el encabezado enuncia aparte de la lista: una norma propia, "
    "una excepción a la lista entera, la norma principal cuando los ítems son sus supuestos o condiciones, o la "
    "norma y su excepción cuando los ítems son las condiciones de esa excepción.")
# U-E3-LISTAS, pieza 2: NOTA del ítem de una lista, en espejo de NOTA_E3_ENCABEZADO_LISTA (solo con la forma r2).
# Texto aprobado por la autora (versión 2, 07/10/2026; nota al pie del mandato). Cada cláusula corresponde a una regla
# del prefijo de E1 r2b y no agrega criterios que E1 no tenga (tabla cláusula → regla del FRENO O2 de U-E3-LISTAS):
# R28, R29, R30 y R16 (e1_extractor/prompt_r2b_reemplazos.json:12, :108, :114, :120) y P3C-b1, b2, b3, c1, c2, d1 y d2
# (e1_extractor/prompt_r2b_parche_p3c.json:48 a :90). El tipo de lista no lo decide el código (E1 lo decide leyendo);
# el tipo del bloque sí (R30 distingue la línea de título de un punto, sin unidad propia, del párrafo con unidad propia)
# y elige las dos partes que cambian: NOTA_E3_ITEM_COMPUESTA y NOTA_E3_ITEM_UNIDAD.
NOTA_E3_ITEM_LISTA = (
    "NOTA: esta unidad es un ítem de la lista que abre el bloque [{tipo} | punto {punto}] del texto fuente, que "
    "termina en «:». En esta extracción la norma del ítem se compone con ese encabezado, según lo que sean los "
    "ítems:\n"
    "- contenidos (lo que hay que hacer, informar, incluir o cumplir, o los miembros de una clase que el encabezado "
    "nombra): el ítem lleva la norma entera, con el sujeto, la modalidad y el cuantificador del encabezado (si se "
    "exigen todos los ítems o basta cualquiera) y con lo que el encabezado fija para cada ítem (un plazo, un ámbito, "
    "una condición común a todos);\n"
    "- supuestos, condiciones o requisitos de una norma que el encabezado enuncia: el ítem es una Condicion por cada "
    "supuesto;\n"
    "- lo que queda afuera: el encabezado nombra una clase o un conjunto y anuncia los miembros que se excluyen, y "
    "cada ítem nombra uno de esos miembros (una clase de operaciones, de sujetos o de bienes): el ítem es una "
    "Excepcion que dice qué miembro queda afuera y de qué norma; si agrega una salvedad que devuelve a la norma una "
    "parte de ese miembro, esa parte va en el mismo ítem como la norma que vuelve a regir, con una Condicion por "
    "condición;\n"
    "- las condiciones de una sola excepción: el encabezado enuncia la norma y una única salvedad, y cada ítem "
    "describe un supuesto de esa salvedad, no un miembro: el ítem es una Condicion de esa excepción, con su "
    "cuantificador (si basta uno o se exigen todos){compuesta}. Si no queda claro si los ítems son miembros que "
    "quedan afuera o supuestos de una sola salvedad, cualquiera de las dos formas vale y no es faltante.\n"
    "Lo que el ítem toma del encabezado no es contenido agregado. La norma del encabezado no se emite como entidad "
    "aparte en el ítem: con contenidos es la norma compuesta; en los demás casos va nombrada en la descripción. "
    "{unidad_del_bloque} Que esa norma falte aquí como entidad aparte, o que el ítem no tenga relación hacia ella, no "
    "es faltante.\n"
    "Sí es faltante lo compuesto que no coincide con el encabezado: otro sujeto, otra modalidad u otro cuantificador; "
    "lo que el encabezado fija para cada ítem y el ítem no lleva; una Excepcion que no dice qué queda afuera y de qué "
    "norma; una Condicion que habla de un supuesto en su etiqueta y de otro en su descripción o en sus umbrales.")
NOTA_E3_ITEM_COMPUESTA = {
    "propia": "",
    "linea_de_titulo": ("; como el encabezado es la línea de título, con supuestos alternativos el ítem lleva la "
                        "excepción compuesta con su supuesto"),
}
NOTA_E3_ITEM_UNIDAD = {
    "propia": ("Ese bloque tiene unidad propia: allí se extrae lo que el encabezado enuncia aparte de la lista (la "
               "norma principal, la norma y su salvedad, o lo que abarca la clase)."),
    "linea_de_titulo": ("Ese bloque es la línea de título del punto, sin unidad propia: con supuestos alternativos "
                        "(basta cualquiera), el ítem lleva la norma compuesta con su supuesto; si se exigen juntos o no "
                        "queda claro, el ítem es solo una Condicion y esa norma no se extrae en ningún ítem."),
}


def nota_item_lista(chunk: dict) -> str | None:
    """U-E3-LISTAS, pieza 2: la NOTA del ítem, con el rótulo del bloque que abre la lista (prompt_r2b.bloque_lista, la
    regla de LINEA_ITEM en E1); None si la unidad no es un ítem. El bloque `encabezado` es la línea de título del
    punto (sin unidad propia); los demás tienen unidad propia."""
    import prompt_r2b as R  # noqa: PLC0415 — solo en la forma r2
    i = R.bloque_lista(chunk)
    if i is None:
        return None
    h = chunk["herencia"][i]
    clave = "linea_de_titulo" if h["tipo"] == "encabezado" else "propia"
    return NOTA_E3_ITEM_LISTA.format(tipo=h["tipo"], punto=h["unidad_origen"], compuesta=NOTA_E3_ITEM_COMPUESTA[clave],
                                     unidad_del_bloque=NOTA_E3_ITEM_UNIDAD[clave])
CATEGORIAS_NOTA_OMISIONES = ("meta_normativo", "fuera_de_tipos", "relacion_sin_predicado")


def _declara_omisiones_de_esquema(validacion: dict | None) -> bool:
    cats = {o.split("]", 1)[0].lstrip("[") for o in (validacion or {}).get("omisiones_no_prosa") or []
            if isinstance(o, str) and o.startswith("[")}
    return bool(cats & set(CATEGORIAS_NOTA_OMISIONES))


def notas_r2(chunk: dict, validacion: dict | None = None) -> list[str]:
    """NOTAS del mensaje en la forma de salida «r2» (perfil r2b de U-PROMPT-R2; mandato, decisión 6, y nota del
    03/10/2026; diseño §4.3 y §4.5). Solo se usan cuando la validación trae la marca forma_salida = "r2":
      - tablas: con alguna tabla serializada confiable (e0-r2), la NOTA de tablas confiables, el aviso de las
        tablas con estructura sin resolver y, si hay residual o fórmulas, la NOTA de los flags; sin tabla
        serializada confiable, la NOTA de siempre;
      - encabezado de lista: la unidad no emite nodo por el solo anuncio ni lo que se compone en los ítems;
      - ítem de lista (U-E3-LISTAS): la NOTA del ítem, con el bloque que abre la lista;
      - omisiones declaradas de las categorías que el esquema deja afuera (P3b, punto i)."""
    import prompt_r2b as R  # noqa: PLC0415 — solo en la forma r2 (e1_extractor en sys.path vía comun_e3)
    notas: list[str] = []
    f = chunk.get("flags") or {}
    ser, _forz, _noser, res = R.estado_tablas(f)
    if not ser:
        n = _nota_flags_e0(f)
        if n:
            notas.append(n)
    else:
        partes = ["NOTA: esta unidad tiene tablas serializadas por E0 (bloques [TABLA …] … [FIN TABLA …] del texto "
                  "fuente, verificados contra el documento): su contenido es texto confiable y su omisión se evalúa "
                  "como la de cualquier otro contenido."]
        riesgo = [t for t in ser if R.tiene_riesgo(t)]
        if riesgo:
            def detalle(t: dict) -> str:
                d = []
                if t.get("combinadas_sin_propagar"):
                    d.append(R._n(t["combinadas_sin_propagar"], "celda combinada sin asignar a sus filas",
                                  "celdas combinadas sin asignar a sus filas"))
                if t.get("filas_subtitulo"):
                    d.append(R._n(t["filas_subtitulo"], "fila de subtítulo", "filas de subtítulo"))
                return f"{t['bloque']} ({' y '.join(d)})"
            partes.append("E0 dejó sin resolver parte de la estructura de " + ", ".join(detalle(t) for t in riesgo)
                          + ": la omisión `tabla` que el extractor declare sobre "
                          + ("esa tabla" if len(riesgo) == 1 else "esas tablas") + " no es faltante.")
        tipos = [t for t, s in (("contenido tabular fuera de los bloques confiables", res),
                                ("fórmulas", f.get("formula"))) if s]
        if tipos:
            partes.append(f"Además, E0 detectó en esta unidad {' y '.join(tipos)} (flag determinístico): el "
                          f"extractor tenía instrucción de NO reconstruir ese contenido y declarar las omisiones; ese "
                          f"contenido normativo ni extraído ni declarado es faltante tipo "
                          f"contenido_tabular_no_declarado; declarado, no.")
        notas.append(" ".join(partes))
    if R.es_encabezado_de_lista(chunk):
        notas.append(NOTA_E3_ENCABEZADO_LISTA)
    elif R.es_item(chunk):
        notas.append(nota_item_lista(chunk))
    if _declara_omisiones_de_esquema(validacion):
        notas.append(NOTA_E3_OMISIONES)
    return notas


def build_user_message(chunk: dict, validacion: dict) -> str:
    """Único contenido variable del request: la unidad como DATOS. Función
    pura de (chunk, validación): mismos datos → mismo mensaje byte a byte.
    U-PROMPT-R2: con la marca forma_salida = "r2" en la validación, las NOTAS
    son las de notas_r2; sin la marca, la NOTA de siempre (byte a byte).
    U-E3-LISTAS: con la marca, el fuente de un ítem suma el bloque que abre la
    lista (comun_e3.indices_bloque_lista); sin la marca, el de siempre."""
    partes: list[str] = []
    partes.append(f"Documento fuente: {chunk['archivo']}")
    partes.append(f"TO: {chunk['to']}")
    partes.append(f"Unidad bajo verificación: {chunk['unidad']} — {chunk['titulo']}")
    partes.append("")

    flags = chunk.get("flags") or {}
    forma_r2 = (validacion or {}).get("forma_salida") == "r2"
    notas = (notas_r2(chunk, validacion) if forma_r2
             else [n for n in (_nota_flags_e0(flags),) if n])
    for nota in notas:
        partes.append(nota)
        partes.append("")

    partes.append("TEXTO FUENTE ÍNTEGRO DE LA UNIDAD (contexto heredado + punto propio):")
    partes.append("```")
    partes.append(fuente_integro(chunk, bloque_de_lista=forma_r2))
    partes.append("```")
    partes.append("")
    partes.append("ELEMENTOS EXTRAÍDOS DE ESTA UNIDAD (post-validación estructural):")
    partes.append("```")
    partes.append(render_extraccion(validacion))
    partes.append("```")
    partes.append("")
    partes.append(
        f"Verificá la completitud y reportá el veredicto con `{NOMBRE_TOOL}`. "
        "Recordá: citas VERBATIM del fuente, un faltante por omisión, jamás corregir."
    )
    return "\n".join(partes)


def build_request_kwargs(chunk: dict, validacion: dict, model: str,
                         max_tokens: int = MAX_OUTPUT_TOKENS) -> dict:
    """Request completo para client.messages.create(**kwargs). Prefijo estable
    idéntico entre unidades; lo variable, solo en messages. Base de la key de
    la caché local (llm_cache.canonical_request)."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        # thinking NO autorizado (namespace think=0). En los modelos actuales
        # de la familia Sonnet el thinking adaptativo viene activado por
        # defecto al omitir el parámetro: se deshabilita EXPLÍCITAMENTE (los
        # tokens de thinking facturarían como output fuera de la estimación).
        "thinking": {"type": "disabled"},
        "system": bloques_sistema(),
        "tools": [TOOL_SCHEMA_E3],
        "tool_choice": {"type": "tool", "name": NOMBRE_TOOL},
        "messages": [{"role": "user", "content": build_user_message(chunk, validacion)}],
    }


# Candado del prefijo de E3 (U-R2-CODIGO, R2; agregado autorizado por la
# autora, plan, fila 8). El prefijo se arma al importar: el texto de sistema
# incluye los calibradores (calibradores_e3.py), que salen de cuatro archivos
# de datos (e0_chunking/salida/chunks_{cla,pro,ric}.json y
# e1_extractor/salida/faseB_pro/extracciones.jsonl). Si alguno cambia, cambia
# PREFIJO_HASH (:217) y, con él, el namespace de la caché de E3: la
# importación frena antes de toda llamada. Solo compara: el prefijo no cambia.
# Va al final del módulo para no mover las líneas que citan otros documentos.
PREFIJO_HASH_SELLADO = "21a836c7de6d"
if PREFIJO_HASH != PREFIJO_HASH_SELLADO:
    raise RuntimeError(
        f"candado E3: el prefijo armado tiene hash {PREFIJO_HASH} y el sellado es "
        f"{PREFIJO_HASH_SELLADO} (namespace e3_verificacion|cv=e3-verificador-v1-p"
        f"{PREFIJO_HASH_SELLADO}|think=0): cambió un archivo de datos de los "
        f"calibradores o el texto del prompt de E3 — se frena")


# Candado del mensaje de E3 (U-PROMPT-R2, P3c-2; U-TABLA-REPROC, fila F23). Las NOTAS del mensaje no entran al
# prefijo de E3 ni a su namespace: un cambio en una NOTA movería las claves sin que nada frene. Este candado arma el
# mensaje de un conjunto fijo de casos (candado_mensaje_e3.json: 6 unidades de salida_tanda0_r2b, elegidas por
# cobertura en data/experiment/prompt_r2/p3c/candados_p3c.py, cada una con la marca de la forma r2 y sin ella, más
# un caso sintético para la NOTA de las omisiones; U-E3-LISTAS suma tres ítems de lista, con el bloque que la abre
# de tipo intro, encabezado e intro partido en fragmentos, cada uno con la marca y sin ella) y compara su sha256 con
# el sellado. Solo compara: el prefijo, su
# candado y las claves no cambian. Corre entero al importar (opción i, decisión de la autora): con la marca r2 las
# NOTAS importan prompt_r2b, así que importar este módulo importa también prompt_r2b y corre sus candados, aun en el
# perfil sellado (acoplamiento declarado en el FRENO P3c-2).
from pathlib import Path as _Path  # noqa: E402 — solo para este candado; el encabezado del módulo no cambia

CANDADO_MENSAJE_E3_JSON = _Path(__file__).resolve().parent / "candado_mensaje_e3.json"
CANDADO_MENSAJE_E3_JSON_SHA256_ESPERADO = "079d2489f37c4485920e932f8cb2bfd60992ecc68bbb80ba504d04e5a5f8065b"
MENSAJE_E3_SHA256_ESPERADO = "66bc865645e99be13cc284f7733f22080612a1342bb2210add71cb122dd15a13"


def sha256_mensajes_e3(casos: list[dict]) -> str:
    """sha256 de los mensajes de E3 de `casos` ({chunk, validacion}), unidos como en prompt_r2b.sha256_mensajes."""
    return hashlib.sha256("\n\x1e\n".join(build_user_message(c["chunk"], c["validacion"]) for c in casos)
                          .encode("utf-8")).hexdigest()


def _candado_mensaje_e3() -> None:
    b = CANDADO_MENSAJE_E3_JSON.read_bytes()
    sha_f = hashlib.sha256(b).hexdigest()
    if sha_f != CANDADO_MENSAJE_E3_JSON_SHA256_ESPERADO:
        raise RuntimeError(f"candado E3: la fixture del mensaje tiene sha256 {sha_f[:12]}… (sellada "
                           f"{CANDADO_MENSAJE_E3_JSON_SHA256_ESPERADO[:12]}…) — se frena")
    sha = sha256_mensajes_e3(json.loads(b)["casos"])
    if sha != MENSAJE_E3_SHA256_ESPERADO:
        raise RuntimeError(f"candado E3: el mensaje de los casos fijos tiene sha256 {sha[:12]}… (sellado "
                           f"{MENSAJE_E3_SHA256_ESPERADO[:12]}…): cambió una NOTA, la regla que la dispara o el "
                           f"render de la unidad o de la extracción — se frena")


_candado_mensaje_e3()
