"""
mensaje_r2_borrador.py — U-PROMPT-R2, P1 (USD 0): BORRADOR del mensaje de
usuario de E1 del perfil r2b y de la NOTA del mensaje de E3, sobre la E0
e0-r2 versionada por la M1 de U-MED-R2A (f8dedd4).

No es el módulo del perfil (ese es de P2, en e1_extractor/): es la herramienta
de P1 para (1) fijar el texto que se aprueba en el FRENO P1, (2) medir los
caracteres del mensaje nuevo para el censo y (3) imprimir ejemplos.

El mensaje sigue la estructura de prompt_e1.build_user_message (:441-522), que
no se edita, con estos cambios:
  - línea de alcance: sugerencia con mención (decisión 4) y la guarda de
    `ejecuta` en todos los TOs;
  - bloque de tablas (decisión 6): el bloque serializado es confiable, salvo
    las tablas de la lista TABLAS_RESIDUALES_FORZADAS (en código); el
    residual conserva el tratamiento de hoy; la clave
    `contenido_tabular_residual` ausente se lee como igual a
    `contenido_tabular`; las líneas de `evidencia_tabular` se imprimen solo
    donde hay contenido tabular residual y solo si siguen en el texto (las que
    el bloque reemplazó no); los metadatos de `flags.tablas_e0` gradúan el
    aviso por tabla;
  - omisiones en `omisiones` con categoría (decisión 5);
  - cierre con `tramo`, `sujeto_mencion` y `omisiones` (decisiones 4, 5 y 15);
  - en un ítem de lista, el encabezado del contexto heredado anuncia la
    composición con el encabezado (F1-A, decisión de la autora del 03/10/2026).
"""
from __future__ import annotations

import re
import unicodedata


def _norm(s: str) -> str:
    s = s.replace("-\n", "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", s))


def _texto_completo(chunk: dict) -> str:
    return "\n".join([chunk.get("texto") or ""] + [h.get("texto") or "" for h in chunk.get("herencia") or []])


def residual(flags: dict) -> bool:
    """`contenido_tabular_residual` ausente se lee como igual a
    `contenido_tabular` (plan, fila 10, nota (i) del 02/10)."""
    return bool(flags.get("contenido_tabular_residual", flags.get("contenido_tabular")))


# Tablas que el pipeline trata como contenido no confiable aunque E0 las haya
# serializado (ids de `flags.tablas_e0[].tabla`). La lista se decide en código:
# pasar una tabla a residual cambia el mensaje de las unidades que la traen (y
# con él su clave de caché), no el prefijo, así que no abre la ventana. En P2
# la lista vive en un archivo versionado que lee el módulo del perfil; hoy está
# vacía.
TABLAS_RESIDUALES_FORZADAS: frozenset = frozenset()


def _n(k: int, singular: str, plural: str) -> str:
    """Cantidad con concordancia: «1 fila», «3 filas»."""
    return f"{k} {singular if k == 1 else plural}"


def estado_tablas(flags: dict, forzadas: frozenset = TABLAS_RESIDUALES_FORZADAS) -> tuple[list, list, list, bool]:
    """(serializadas confiables, serializadas forzadas a residual, no
    serializadas, residual efectivo)."""
    tablas = flags.get("tablas_e0") or []
    ser = [t for t in tablas if t.get("serializada") and t["tabla"] not in forzadas]
    forz = [t for t in tablas if t.get("serializada") and t["tabla"] in forzadas]
    noser = [t for t in tablas if not t.get("serializada")]
    return ser, forz, noser, residual(flags) or bool(forz)


def evidencia_tabular_vigente(chunk: dict, forzadas: frozenset = TABLAS_RESIDUALES_FORZADAS) -> list[str]:
    """Líneas de evidencia tabular que se imprimen: ninguna si no hay
    contenido tabular residual (las que había las reemplazó el bloque o no
    son tabulares para la heurística de E0 fuera de los bloques); si lo hay,
    las que siguen en el texto propio o heredado del chunk."""
    f = chunk.get("flags") or {}
    if not estado_tablas(f, forzadas)[3]:
        return []
    t = _norm(_texto_completo(chunk))
    return [e for e in (f.get("evidencia_tabular") or []) if _norm(e) in t]


def tiene_riesgo(t: dict) -> bool:
    return bool(t.get("combinadas_sin_propagar") or t.get("filas_subtitulo"))


def _aviso_tabla(t: dict) -> str:
    """Una línea por tabla serializada confiable, graduada por sus metadatos
    (marca H de e0-r2: modo, celdas propagadas, con alcance, combinadas sin
    propagar, filas de subtítulo), con el aviso redactado por tipo de riesgo."""
    detalles = []
    if t["modo"] == "posicional":
        detalles.append("sin encabezado de columnas reconocido: las claves son colN y el nombre de cada "
                        "columna está en las primeras filas del bloque")
    if t.get("celdas_propagadas"):
        detalles.append(_n(t["celdas_propagadas"], "celda con un valor propagado desde otra fila",
                           "celdas con un valor propagado desde otra fila") + " (⟨combinada con fila n⟩)")
    if t.get("celdas_con_alcance"):
        detalles.append(_n(t["celdas_con_alcance"], "celda que abarca varias columnas",
                           "celdas que abarcan varias columnas") + " (⟨abarca hasta c⟩)")
    linea = f"- `{t['bloque']}` ({t['modo']})" + (": " + "; ".join(detalles) if detalles else
                                                  ": confiable, sin celdas combinadas") + "."
    k = t.get("filas_subtitulo") or 0
    if k:
        linea += (" ATENCIÓN, " + _n(k, "fila de subtítulo", "filas de subtítulo")
                  + (": no es un dato; califica a las filas que la siguen." if k == 1 else
                     ": no son datos; cada una califica a las filas que la siguen."))
    k = t.get("combinadas_sin_propagar") or 0
    if k:
        linea += (" ATENCIÓN, " + _n(k, "celda combinada que E0 no asignó a sus filas",
                                    "celdas combinadas que E0 no asignó a sus filas")
                  + (": su valor puede valer para varias filas" if k == 1 else
                     ": el valor de cada una puede valer para varias filas")
                  + " y el bloque no indica cuáles. Si el texto no lo aclara, no lo asocies a ninguna fila: "
                    "registrá la omisión `tabla` con su tramo.")
    return linea


def bloque_flags(chunk: dict, forzadas: frozenset = TABLAS_RESIDUALES_FORZADAS) -> list[str]:
    f = chunk.get("flags") or {}
    if not (f.get("contenido_tabular") or f.get("formula")):
        return []
    out: list[str] = []
    ser, forz, noser, hay_res = estado_tablas(f, forzadas)
    if ser:
        out.append("TABLAS SERIALIZADAS POR E0 en el texto (CONFIABLES: leelas y copiá sus valores, ver "
                   "CONTENIDO NO-PROSA del sistema):")
        out.extend(_aviso_tabla(t) for t in ser)
    hay_form = bool(f.get("formula"))
    if hay_res or hay_form:
        tipos = []
        if hay_res:
            tipos.append("contenido tabular fuera de los bloques confiables" if ser else "contenido tabular")
        if hay_form:
            tipos.append("fórmulas")
        cats = " o ".join(c for c, s in (("`tabla`", hay_res), ("`formula`", hay_form)) if s)
        out.append(
            f"FLAGS E0: este chunk contiene {' y '.join(tipos)} (detección determinística). Ese contenido está "
            f"declarado NO-CONFIABLE: aplicá la sección CONTENIDO NO-PROSA del sistema (no reconstruir, no forzar "
            f"extracción, registrar en `omisiones` con categoría {cats}).")
        if noser:
            out.append("E0 detectó tablas que no pudo serializar ("
                       + ", ".join(f"`{t['tabla']}`" for t in noser)
                       + "): su contenido quedó como texto linealizado, no confiable.")
        if forz:
            out.append("Tablas serializadas por E0 que se tratan como contenido NO-CONFIABLE ("
                       + ", ".join(f"`{t['bloque']}`" for t in forz)
                       + "): no copies sus valores; registrá la omisión `tabla` con su tramo.")
        for ev in evidencia_tabular_vigente(chunk, forzadas) + (f.get("evidencia_formula") or []):
            out.append(f"  evidencia: {ev}")
    out.append("")
    return out


def es_item(chunk: dict, es_mini_chunk) -> bool:
    """Ítem de una lista (definición de U-DIAG-PROCESO, censo_estructural.py):
    chunk de punto cuyo último bloque heredado termina en «:»."""
    her = chunk.get("herencia") or []
    return (not es_mini_chunk(chunk)) and bool(her) and " ".join(her[-1]["texto"].split()).endswith((":", "："))


def linea_alcance(rol: dict | None) -> list[str]:
    if rol is None:
        return []
    miembros = ", ".join(rol["miembros_labels"])
    if rol.get("rol_id"):
        cab, sug = f"Alcance de este TO: {rol['rol_id']} = {{{miembros}}}. ", f"sugerí {rol['rol_id']} en `sujeto_id`"
    else:
        ids = " o ".join(rol["clase_ids"])
        cab, sug = f"Alcance de este TO: {{{miembros}}}. ", f"sugerí {ids} en `sujeto_id`, según corresponda"
    return [cab + "Cuando la norma se dirija genéricamente a 'las entidades' / 'los sujetos obligados' / "
            f"el colectivo del TO, {sug}, con la expresión del texto como `sujeto_mencion`. Es el sujeto de "
            "aplica_a cuando la norma se dirige al colectivo; NO es el ejecutor por defecto en ejecuta.", ""]


def build_user_message_r2(chunk: dict, rol_por_to: dict, puntos_admitidos, es_mini_chunk,
                          forzadas: frozenset = TABLAS_RESIDUALES_FORZADAS) -> str:
    """Función pura del chunk: mismo chunk → mismo mensaje byte a byte."""
    partes: list[str] = []
    mini = es_mini_chunk(chunk)
    partes.append(f"Documento fuente: {chunk['archivo']}")
    partes.append(f"TO: {chunk['to']}")
    if mini:
        partes.append(f"Tipo de unidad: MINI-CHUNK de bloque estructural ({chunk['rol_bloque']} del punto {chunk['unidad']})")
        partes.append(f"Unidad de origen: {chunk['unidad']} — {chunk['titulo']}")
    else:
        partes.append("Tipo de unidad: chunk de punto")
        partes.append(f"Punto del chunk: {chunk['unidad']} — {chunk['titulo']}")
    partes.append("Puntos admitidos para `punto`: " + ", ".join(puntos_admitidos(chunk)))
    partes.append("")
    partes.extend(linea_alcance(rol_por_to.get(chunk["archivo"])))
    herencia = chunk.get("herencia", [])
    if herencia:
        if mini:
            partes.append("Cadena de títulos (ubica el bloque; NO es contenido a extraer):")
        elif es_item(chunk, es_mini_chunk):
            # F1-A (decisión de la autora, 03/10/2026): el ítem compone su norma con el encabezado.
            partes.append("Contexto estructural heredado (contexto y anclaje; NO extraigas contenido normativo de "
                          "estos bloques, salvo un caso: el último bloque abre la lista de la que este punto es un "
                          "ítem, así que la norma del ítem se compone con ese encabezado — ver COMPOSICIÓN CON EL "
                          "ENCABEZADO DE UNA LISTA):")
        else:
            partes.append("Contexto estructural heredado (SOLO contexto y anclaje: NO extraigas contenido normativo "
                          "de estos bloques — cada uno tiene su propia unidad de extracción; ver PROVENANCE):")
        for h in herencia:
            partes.append(f"[{h['tipo']} | punto {h['unidad_origen']}]")
            partes.append(h["texto"])
        partes.append("")
    partes.extend(bloque_flags(chunk, forzadas))
    if mini:
        partes.append(f"Texto del bloque {chunk['rol_bloque']} del punto {chunk['unidad']} (TU unidad de extracción):")
    else:
        partes.append(f"Texto del punto {chunk['unidad']}:")
    partes.append("```")
    partes.append(chunk["texto"])
    partes.append("```")
    partes.append("")
    partes.append("Extraé las entidades y relaciones según el schema. Recordá: nodo TextoOrdenado con local_id='to'; "
                  "todo elemento con `punto` de la lista admitida; toda entidad con su `tramo`; toda relación de "
                  "sujeto con su `sujeto_mencion`; `omisiones` siempre (vacía si no omitiste nada).")
    return "\n".join(partes)


# ------------------------------------------------------------------------- #
# NOTA del mensaje de E3 (prompt_e3.py:241, fuera del prefijo de E3)         #
# ------------------------------------------------------------------------- #
def nota_e3_sellada(chunk: dict) -> str | None:
    """La NOTA de hoy (prompt_e3.build_user_message), reproducida para comparar."""
    f = chunk.get("flags") or {}
    if not (f.get("contenido_tabular") or f.get("formula")):
        return None
    tipos = [t for t, s in (("contenido tabular", f.get("contenido_tabular")), ("fórmulas", f.get("formula"))) if s]
    return (f"NOTA: esta unidad tiene {' y '.join(tipos)} detectados determinísticamente (flag de E0). El extractor "
            f"tenía instrucción de NO reconstruir ese contenido y declarar las omisiones. Evaluá el tratamiento: "
            f"contenido tabular/fórmula normativo ni extraído ni declarado es faltante tipo "
            f"contenido_tabular_no_declarado; declarado, no.")


def nota_e3_r2(chunk: dict, forzadas: frozenset = TABLAS_RESIDUALES_FORZADAS) -> str | None:
    f = chunk.get("flags") or {}
    ser, forz, noser, res = estado_tablas(f, forzadas)
    if not ser:
        return nota_e3_sellada(chunk)   # sin tabla serializada confiable: la NOTA de hoy, sin cambios
    partes = ["NOTA: esta unidad tiene tablas serializadas por E0 (bloques [TABLA …] … [FIN TABLA …] del texto "
              "fuente, verificados contra el documento): su contenido es texto confiable y su omisión se evalúa "
              "como la de cualquier otro contenido."]
    riesgo = [t for t in ser if tiene_riesgo(t)]
    if riesgo:
        def detalle(t: dict) -> str:
            d = []
            if t.get("combinadas_sin_propagar"):
                d.append(_n(t["combinadas_sin_propagar"], "celda combinada sin asignar a sus filas",
                            "celdas combinadas sin asignar a sus filas"))
            if t.get("filas_subtitulo"):
                d.append(_n(t["filas_subtitulo"], "fila de subtítulo", "filas de subtítulo"))
            return f"{t['bloque']} ({' y '.join(d)})"
        partes.append("E0 dejó sin resolver parte de la estructura de " + ", ".join(detalle(t) for t in riesgo)
                      + ": la omisión `tabla` que el extractor declare sobre "
                      + ("esa tabla" if len(riesgo) == 1 else "esas tablas") + " no es faltante.")
    tipos = [t for t, s in (("contenido tabular fuera de los bloques confiables", res), ("fórmulas", f.get("formula")))
             if s]
    if tipos:
        partes.append(f"Además, E0 detectó en esta unidad {' y '.join(tipos)} (flag determinístico): el extractor "
                      f"tenía instrucción de NO reconstruir ese contenido y declarar las omisiones; ese contenido "
                      f"normativo ni extraído ni declarado es faltante tipo contenido_tabular_no_declarado; "
                      f"declarado, no.")
    return " ".join(partes)


def es_encabezado_de_lista(chunk: dict) -> bool:
    """Unidad propia de un encabezado de lista (MINI ORDENADOR de U-DIAG-PROCESO, censo_estructural.py):
    mini-chunk intro o chapeau_seccion cuyo texto termina en «:»."""
    return (chunk.get("tipo") == "mini_chunk" and chunk.get("rol_bloque") in ("intro", "chapeau_seccion")
            and " ".join((chunk.get("texto") or "").split()).endswith((":", "：")))


def nota_e3_encabezado_r2(chunk: dict) -> str | None:
    """Salida (a) del §4.5 del diseño: NOTA del mensaje de E3 para la unidad de un encabezado de lista, solo
    en la forma de salida «r2» (en P2, con la validación proyectada que lo declara). Se suma a la de tablas."""
    if not es_encabezado_de_lista(chunk):
        return None
    return ("NOTA: esta unidad es el encabezado de una lista (su texto termina en «:»); los ítems son los puntos "
            "que siguen, cada uno con su propia unidad. En esta extracción se componen en cada ítem el sujeto, la "
            "modalidad y el cuantificador del encabezado, y también lo que el encabezado fija para cada ítem (un "
            "plazo, un ámbito, una condición que vale para todos los ítems). Esta unidad no emite un nodo por el "
            "solo anuncio de la lista ni repite lo que se compone en los ítems: que falten aquí no es faltante. "
            "Sí es faltante, si no fue extraído, lo que el encabezado enuncia aparte de la lista: una norma propia, "
            "una excepción a la lista entera, o la norma principal cuando los ítems son sus supuestos o "
            "condiciones.")
