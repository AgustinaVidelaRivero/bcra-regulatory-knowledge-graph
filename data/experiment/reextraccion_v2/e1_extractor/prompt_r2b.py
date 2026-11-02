"""
prompt_r2b.py — U-PROMPT-R2, P2: prefijo de E1 del perfil «r2b» (forma de salida «r2»).

Qué es (mandato docs/mandatos/UPROMPT_R2_prefijo_nuevo.md, firma b901f6d, y sus notas fechadas; diseño
data/experiment/prompt_r2/diseno_prefijo_r2.md, aprobado en el FRENO P1 del 03/10/2026 con la variante B de la
regla de frecuencia):
  - el texto se arma al importar, sobre el prefijo sellado v3_b54 (prompt_v3_b54.PREFIJO_SISTEMA_V3, que no se
    edita), con los reemplazos anclados congelados en prompt_r2b_reemplazos.json (R0 a R26 y R28 a R30; cada
    `viejo` aparece una sola vez) y el bloque de catálogo r2 (R27) tal cual
    (catalogo_unico/generados_r2/bloque_catalogo_r2.txt, LN-8);
  - el tool schema es el generado por pyd_r2 desde modelos_r2.py con las decisiones 15 a 17
    (pyd_r2/generados/tool_schema_r2.json);
  - el mensaje de usuario es el del diseño (§4.1, §4.2 y §4.5): bloque de tablas de e0-r2, alcance con mención,
    rótulo del heredado de un ítem de lista, omisiones con categoría y cierre con tramo y mención.

CANDADOS (como el perfil v3_b54): el módulo recomputa el sha256 de cada insumo y del texto armado, y el hash
canónico system + tools (método de prompt_e1.py:415-419), y FRENA con RuntimeError si alguno no es el congelado.
Corre al importar, antes de toda llamada.

P3b (FRENO P3b-1 aprobado, 023f9a0): sobre el prefijo de P2 (14d6b63b508e) se aplica el parche congelado en
prompt_r2b_parche_p3b.json (puntos a a f: recomendación, consecuencia de un incumplimiento, Excepcion conectada,
definiciones de regula/condiciona/requiere, lista dentro de la unidad y listas de excepciones), con candado de sha;
el texto armado tiene candado propio. El mensaje suma la regla g (ítem con párrafos de cierre después del
encabezado), la h (mini-chunk que empieza a mitad de oración) y el aviso del recorte de herencia de E0 (C2 de
U-R2-CODIGO-2, punto h).

Lista de tablas forzadas a residual (diseño §4.2, regla 4): tablas_residuales_forzadas_r2b.json, versionado al
lado de este módulo, con la tabla, el motivo y la fecha de cada alta. Pasar una tabla a residual cambia el
mensaje de las unidades que la traen, no el prefijo.

P3c (FRENO P3c-1 aprobado, 438bbd5; decisiones 6633dc7 y 1873962): sobre el prefijo de P3b-2 (3817de475c93) se
aplica el parche congelado en prompt_r2b_parche_p3c.json (puntos a a e: la regla 9 de la enmienda 7 a L-ESQ-R2, las
listas que exceptúan, una Condicion por supuesto, la norma del encabezado que no se repite en el ítem y la mención
que el texto no trae). El mensaje cambia la línea «Alcance de este TO» (punto e). Candados nuevos, que solo
comparan (no entran al pedido ni cambian ninguna clave): la lista de tablas forzadas se lee con su sha256 (F04b) y,
al final del módulo, el sha256 del mensaje de un conjunto fijo de unidades (candado_mensaje_r2b.json) controla las
líneas fijas y condicionales del mensaje (F22 y F22b).

P5 (decisión de la autora del 05/10/2026, nota del mandato): el pedido lleva `temperature` 0
(TEMPERATURA_E1_R2B), y el reintento por salida mal formada, 1 (TEMPERATURA_REINTENTO_FORMA_R2B). No cambian el
prefijo, el mensaje, el tool schema ni el namespace; cambia la clave de E1 de todas las unidades (fila de la
temperatura en data/experiment/mantenimiento/tabla_reprocesamiento.md).

Caching (docs/decisiones_caching_extraccion.md): system como bloque único con cache_control en el último bloque
(decisión 1); el namespace de E1 se deriva del hash canónico con cliente_e1.namespace_e1.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

_BASE = Path(__file__).resolve().parent                  # e1_extractor/
_REPO = _BASE.parents[3]
_B54_CODE = _REPO / "data" / "experiment" / "b54_catalogo_v3" / "code"
_CAT_R2 = _REPO / "data" / "experiment" / "catalogo_unico" / "generados_r2"
_PYD_GEN = _REPO / "data" / "experiment" / "pyd_r2" / "generados"
if str(_B54_CODE) not in sys.path:
    sys.path.insert(0, str(_B54_CODE))

import prompt_v3_b54 as v3          # noqa: E402 — módulo SELLADO, solo import
from comun_e1 import es_mini_chunk, puntos_admitidos  # noqa: E402

REEMPLAZOS_JSON = _BASE / "prompt_r2b_reemplazos.json"
PARCHE_P3B_JSON = _BASE / "prompt_r2b_parche_p3b.json"
PARCHE_P3C_JSON = _BASE / "prompt_r2b_parche_p3c.json"
CANDADO_MENSAJE_JSON = _BASE / "candado_mensaje_r2b.json"
TABLAS_FORZADAS_JSON = _BASE / "tablas_residuales_forzadas_r2b.json"
BLOQUE_CATALOGO_R2 = _CAT_R2 / "bloque_catalogo_r2.txt"
ROL_POR_TO_R2_JSON = _CAT_R2 / "rol_por_to_r2.json"
LABELS_E2_R2_JSON = _CAT_R2 / "labels_e2_r2.json"
TOOL_SCHEMA_R2_JSON = _PYD_GEN / "tool_schema_r2.json"

# Candados (congelados en P2, 03/10/2026). Literales propios de este módulo.
PREFIJO_SHA256_V3_ESPERADO = "35e88c2dd0a2920302c29005b08ab9689405606d4bd5fcf8fb7ce807b1a3c512"
REEMPLAZOS_SHA256_ESPERADO = "810ad645148e49f05fc3a4bbee5a18d398a3b92ce4befab6de8bcbae7b80911d"
BLOQUE_CATALOGO_R2_SHA256_ESPERADO = "c40054853bd8682879832d72799664de91025eaea5a2acb68de16387197dfeb2"
ROL_POR_TO_R2_SHA256_ESPERADO = "07cdb7af51b8ae82b606e972e3ab81be5a52aa4279cfc9132561c8e49ef13bd1"
LABELS_E2_R2_SHA256_ESPERADO = "064167ab96cec8bf92bb89edd71f7a5193580d2617e714a5faffa536b6293b23"
TOOL_SCHEMA_R2_SHA256_ESPERADO = "0c391f2b23bb7c94ec2606bd0315f3e4589c16a3571eaaa210a27babaa0f8ba2"
# Prefijo de P2 (03/10/2026), base del parche de P3b.
PREFIJO_SHA256_R2B_P2 = "cdb374508523e7f2308b1e3dd9790cdcfbb4000f2f1616279504af9475c6e227"
PREFIJO_HASH_R2B_P2 = "14d6b63b508e"
# Re-congelado en P3b-2 (04/10/2026), con el parche aprobado en el FRENO P3b-1.
PARCHE_P3B_SHA256_ESPERADO = "8679ea124f1f2adf58d3c65c03861751b905224ae1784b83338e425c0aa1752b"
PREFIJO_SHA256_R2B_P3B = "8d84364fc3b6f6b586ff09e11833a2328408ae6f93b081c8ae64a059ea839c8b"
PREFIJO_HASH_R2B_P3B = "3817de475c93"
# Re-congelado en P3c-2 (04/10/2026), con el parche aprobado en el FRENO P3c-1.
PARCHE_P3C_SHA256_ESPERADO = "5e3761c16d13a83d2071cb05494aea04a2c862259d39c7333e40db490f11c678"
PREFIJO_SHA256_R2B_ESPERADO = "ccffa4e36ba26a4b63b5760a7657d4bb5f5357ccd2392fe2b67584e4c2efb775"
PREFIJO_HASH_R2B_ESPERADO = "322c5a23e9b7"
# Candados de P3c-2 (U-TABLA-REPROC, filas F04b, F22, F22b y F23); los dos del mensaje, recalculados en U-ALCANCE-E1.
TABLAS_FORZADAS_SHA256_ESPERADO = "98cc96b2fec4cd7febb1fba71df8490ea420c0c0419711a122daaf4f12c2bc67"
CANDADO_MENSAJE_JSON_SHA256_ESPERADO = "6b758517cee0f2e36c26c54f0f6738b3d49d11d0cf3141c26cff166ce6820325"
MENSAJE_R2B_SHA256_ESPERADO = "eeb11b9a3bf699d5535fcf2bbe79541ba746ae7bdae3341af962840990a97362"

ANCLA_INICIO_BLOQUE = "## Sujetos regulados"
ANCLA_FIN_BLOQUE = "\n# PROVENANCE OBLIGATORIA POR ELEMENTO"

MAX_OUTPUT_TOKENS = v3.MAX_OUTPUT_TOKENS      # primer intento a 8.192 (diseño §8.3)
NOMBRE_TOOL = v3.NOMBRE_TOOL                  # extraer_kg_e1
# Temperatura del pedido de E1 (P5; decisión de la autora del 05/10/2026, nota del mandato): 0 en el pedido que arma
# build_request_kwargs_r2b, del que salen el primer intento, el reintento por corte, el tercer escalón y el reintento
# del ratchet; 1 en el reintento por salida mal formada, para obtener una respuesta distinta
# (kwargs_reintento_forma_r2b). Entra en la clave de la caché local, no en el prefijo ni en el namespace.
TEMPERATURA_E1_R2B = 0
TEMPERATURA_REINTENTO_FORMA_R2B = 1


def _leer_con_candado(p: Path, esperado: str) -> bytes:
    b = p.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    if sha != esperado:
        raise RuntimeError(f"candado r2b: {p.name} con sha256 {sha[:12]}… (esperado {esperado[:12]}…) — se frena")
    return b


def _aplicar(t: str, reemplazos: list[dict]) -> str:
    for r in reemplazos:
        n = t.count(r["viejo"])
        if n != 1:
            raise RuntimeError(f"{r['id']}: el ancla aparece {n} veces (esperado 1) — se frena")
        t = t.replace(r["viejo"], r["nuevo"])
    return t


def _armar_prefijo() -> tuple[str, list[dict], str, list[dict], str, list[dict]]:
    if v3.PREFIJO_SHA256_V3 != PREFIJO_SHA256_V3_ESPERADO:
        raise RuntimeError("candado r2b: el prefijo sellado v3_b54 no es el de U-B5.4 — se frena")
    doc = json.loads(_leer_con_candado(REEMPLAZOS_JSON, REEMPLAZOS_SHA256_ESPERADO))
    if doc.get("variante_frecuencia") != "B":
        raise RuntimeError("candado r2b: los reemplazos no son los de la variante B — se frena")
    t = _aplicar(v3.PREFIJO_SISTEMA_V3, doc["reemplazos"])
    for a in (ANCLA_INICIO_BLOQUE, ANCLA_FIN_BLOQUE):
        if t.count(a) != 1:
            raise RuntimeError(f"R27: el ancla del bloque de catálogo {a!r} no es única — se frena")
    bloque = _leer_con_candado(BLOQUE_CATALOGO_R2, BLOQUE_CATALOGO_R2_SHA256_ESPERADO).decode("utf-8")
    i, k = t.index(ANCLA_INICIO_BLOQUE), t.index(ANCLA_FIN_BLOQUE)
    t_p2 = t[:i] + bloque + t[k:]
    if hashlib.sha256(t_p2.encode("utf-8")).hexdigest() != PREFIJO_SHA256_R2B_P2:
        raise RuntimeError("candado r2b: el prefijo de P2, base del parche de P3b, no es el congelado — se frena")
    parche = json.loads(_leer_con_candado(PARCHE_P3B_JSON, PARCHE_P3B_SHA256_ESPERADO))
    if parche.get("base_hash_canonico") != PREFIJO_HASH_R2B_P2:
        raise RuntimeError("candado r2b: el parche de P3b no declara la base de P2 — se frena")
    t_p3b = _aplicar(t_p2, parche["reemplazos"])
    if hashlib.sha256(t_p3b.encode("utf-8")).hexdigest() != PREFIJO_SHA256_R2B_P3B:
        raise RuntimeError("candado r2b: el prefijo de P3b-2, base del parche de P3c, no es el congelado — se frena")
    parche_c = json.loads(_leer_con_candado(PARCHE_P3C_JSON, PARCHE_P3C_SHA256_ESPERADO))
    if parche_c.get("base_hash_canonico") != PREFIJO_HASH_R2B_P3B:
        raise RuntimeError("candado r2b: el parche de P3c no declara la base de P3b-2 — se frena")
    return (_aplicar(t_p3b, parche_c["reemplazos"]), doc["reemplazos"], t_p2, parche["reemplazos"], t_p3b,
            parche_c["reemplazos"])


(PREFIJO_SISTEMA_R2B, REEMPLAZOS_R2B, PREFIJO_SISTEMA_R2B_P2, REEMPLAZOS_P3B, PREFIJO_SISTEMA_R2B_P3B,
 REEMPLAZOS_P3C) = _armar_prefijo()
TOOL_SCHEMA_R2B = json.loads(_leer_con_candado(TOOL_SCHEMA_R2_JSON, TOOL_SCHEMA_R2_SHA256_ESPERADO))
ROL_POR_TO_R2 = json.loads(_leer_con_candado(ROL_POR_TO_R2_JSON, ROL_POR_TO_R2_SHA256_ESPERADO))
LABELS_E2_R2 = json.loads(_leer_con_candado(LABELS_E2_R2_JSON, LABELS_E2_R2_SHA256_ESPERADO))


def bloques_sistema_r2b() -> list[dict]:
    """Decisión 1 de caching: system como bloque único con el breakpoint."""
    return [{"type": "text", "text": PREFIJO_SISTEMA_R2B, "cache_control": {"type": "ephemeral"}}]


PREFIJO_CANONICO_R2B = json.dumps({"system": bloques_sistema_r2b(), "tools": [TOOL_SCHEMA_R2B]},
                                  sort_keys=True, ensure_ascii=False, separators=(",", ":"))
PREFIJO_HASH_R2B = hashlib.sha256(PREFIJO_CANONICO_R2B.encode("utf-8")).hexdigest()[:12]
PREFIJO_SHA256_R2B = hashlib.sha256(PREFIJO_SISTEMA_R2B.encode("utf-8")).hexdigest()
if PREFIJO_SHA256_R2B != PREFIJO_SHA256_R2B_ESPERADO or PREFIJO_HASH_R2B != PREFIJO_HASH_R2B_ESPERADO:
    raise RuntimeError(
        f"candado r2b: el prefijo armado no es el congelado (sha {PREFIJO_SHA256_R2B[:12]}… esperado "
        f"{PREFIJO_SHA256_R2B_ESPERADO[:12]}…; hash {PREFIJO_HASH_R2B} esperado {PREFIJO_HASH_R2B_ESPERADO}) — se frena")


def _cargar_tablas_forzadas() -> frozenset:
    # P3c-2 (F04b): la lista se lee con su sha256; un alta o una baja frena hasta re-sellar.
    doc = json.loads(_leer_con_candado(TABLAS_FORZADAS_JSON, TABLAS_FORZADAS_SHA256_ESPERADO))
    for alta in doc["tablas"]:
        if not (alta.get("tabla") and alta.get("motivo") and alta.get("fecha")):
            raise RuntimeError(f"tablas forzadas a residual: alta incompleta {alta!r} — se frena")
    return frozenset(a["tabla"] for a in doc["tablas"])


TABLAS_RESIDUALES_FORZADAS: frozenset = _cargar_tablas_forzadas()


# ========================================================================== #
# Mensaje de usuario (diseño §4.1, §4.2 y §4.5)                              #
# ========================================================================== #
def _norm(s: str) -> str:
    s = s.replace("-\n", "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", s))


def _texto_completo(chunk: dict) -> str:
    return "\n".join([chunk.get("texto") or ""] + [h.get("texto") or "" for h in chunk.get("herencia") or []])


def residual(flags: dict) -> bool:
    """`contenido_tabular_residual` ausente se lee como igual a `contenido_tabular`."""
    return bool(flags.get("contenido_tabular_residual", flags.get("contenido_tabular")))


def _n(k: int, singular: str, plural: str) -> str:
    """Cantidad con concordancia: «1 fila», «3 filas»."""
    return f"{k} {singular if k == 1 else plural}"


def estado_tablas(flags: dict, forzadas: frozenset | None = None) -> tuple[list, list, list, bool]:
    """(serializadas confiables, serializadas forzadas a residual, no serializadas, residual efectivo)."""
    forzadas = TABLAS_RESIDUALES_FORZADAS if forzadas is None else forzadas
    tablas = flags.get("tablas_e0") or []
    ser = [t for t in tablas if t.get("serializada") and t["tabla"] not in forzadas]
    forz = [t for t in tablas if t.get("serializada") and t["tabla"] in forzadas]
    noser = [t for t in tablas if not t.get("serializada")]
    return ser, forz, noser, residual(flags) or bool(forz)


def evidencia_tabular_vigente(chunk: dict, forzadas: frozenset | None = None) -> list[str]:
    """Líneas de evidencia tabular que se imprimen: ninguna sin contenido tabular residual; con él, las que
    siguen en el texto propio o heredado del chunk."""
    f = chunk.get("flags") or {}
    if not estado_tablas(f, forzadas)[3]:
        return []
    t = _norm(_texto_completo(chunk))
    return [e for e in (f.get("evidencia_tabular") or []) if _norm(e) in t]


def tiene_riesgo(t: dict) -> bool:
    return bool(t.get("combinadas_sin_propagar") or t.get("filas_subtitulo"))


def _aviso_tabla(t: dict) -> str:
    """Una línea por tabla serializada confiable, graduada por sus metadatos, con el aviso por tipo de riesgo."""
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


def bloque_flags(chunk: dict, forzadas: frozenset | None = None) -> list[str]:
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


def bloque_lista(chunk: dict) -> int | None:
    """P3b, punto g (hallazgo 1.2): índice del bloque heredado que abre la lista de la que el chunk de punto es un
    ítem, o None. Es el último bloque que no es de cierre y termina en «:», y después de él solo hay bloques de
    cierre (`tipo` «cierre») o ninguno: E0 hereda también los párrafos de cierre del punto contenedor. Un cierre
    que termina en «:» (el que presenta una fórmula) no abre la lista. Da lo mismo con el recorte de herencia de
    C2 de U-R2-CODIGO-2: sin cierres, el bloque con «:» es el último."""
    if es_mini_chunk(chunk):
        return None
    her = chunk.get("herencia") or []
    idx = [i for i, h in enumerate(her) if h["tipo"] != "cierre"
           and " ".join(h["texto"].split()).endswith((":", "："))]
    if not idx:
        return None
    i = idx[-1]
    return i if all(h["tipo"] == "cierre" for h in her[i + 1:]) else None


def es_item(chunk: dict) -> bool:
    """Ítem de una lista (definición de U-DIAG-PROCESO, con la regla g de P3b): ver bloque_lista."""
    return bloque_lista(chunk) is not None


FIN_DE_ORACION = (".", ":", ";", "：")


def mini_a_mitad(chunk: dict) -> bool:
    """P3b, punto h (hallazgo 2.16): mini-chunk que empieza a mitad de la oración que arranca en su última línea de
    títulos (E0 tomó como título la primera línea del punto): el último bloque heredado es el `encabezado` de la
    misma unidad y no termina en «.», «:» ni «;», y el texto del bloque empieza en minúscula."""
    if not es_mini_chunk(chunk):
        return False
    her = chunk.get("herencia") or []
    if not her:
        return False
    h = her[-1]
    texto = (chunk.get("texto") or "").lstrip()
    return (h["tipo"] == "encabezado" and h["unidad_origen"] == chunk["unidad"]
            and not " ".join(h["texto"].split()).endswith(FIN_DE_ORACION) and bool(texto) and texto[0].islower())


LINEA_ITEM = ("Contexto estructural heredado (contexto y anclaje; NO extraigas contenido normativo de estos bloques, "
              "salvo un caso: el bloque [{tipo} | punto {unidad}] termina en «:» y abre la lista de la que este punto "
              "es un ítem{cierres}, así que la norma del ítem se compone con ese encabezado — ver COMPOSICIÓN CON EL "
              "ENCABEZADO DE UNA LISTA):")
CIERRES = "; los bloques que lo siguen son párrafos de cierre del punto que lo contiene, no parte del encabezado"
LINEA_MINI_MITAD = ("Cadena de títulos (ubica el bloque; NO es contenido a extraer, salvo su última línea: E0 la tomó "
                    "como título, pero es el comienzo de la oración que sigue en tu bloque. Leela con el bloque, "
                    "extraé la oración entera, y el `tramo` puede empezar en esa línea):")
# Líneas fijas del mensaje (P3c-2: constantes del módulo, para que el selftest de claves pueda variarlas; el mensaje
# no cambia un byte).
LINEA_TITULOS_MINI = "Cadena de títulos (ubica el bloque; NO es contenido a extraer):"
LINEA_HERENCIA_PUNTO = ("Contexto estructural heredado (SOLO contexto y anclaje: NO extraigas contenido normativo de estos "
                        "bloques — cada uno tiene su propia unidad de extracción; ver PROVENANCE):")
LINEA_CIERRE = ("Extraé las entidades y relaciones según el schema. Recordá: nodo TextoOrdenado con local_id='to'; todo "
                "elemento con `punto` de la lista admitida; toda entidad con su `tramo`; toda relación de sujeto con su "
                "`sujeto_mencion`; `omisiones` siempre (vacía si no omitiste nada).")
# Agregado 8 del «seguí» de P3b-2: solo en las unidades cuya herencia recorta E0 (C2 de U-R2-CODIGO-2, punto h;
# el chunk lleva `herencia_recortada` y el bloque, la línea del recorte en el lugar de lo omitido).
LINEA_RECORTE = ("La línea «[recorte de E0: …]» dentro de un bloque heredado no es texto de la norma: marca la parte "
                 "de ese bloque que E0 no transcribe por su largo. No la copies ni extraigas nada de ella.")


def es_encabezado_de_lista(chunk: dict) -> bool:
    """Unidad propia de un encabezado de lista: mini-chunk intro o chapeau_seccion cuyo texto termina en «:»."""
    return (chunk.get("tipo") == "mini_chunk" and chunk.get("rol_bloque") in ("intro", "chapeau_seccion")
            and " ".join((chunk.get("texto") or "").split()).endswith((":", "：")))


# P3c, punto e (texto aprobado en el FRENO P3c-1): la mención se copia del texto y, si el texto no nombra a ningún
# sujeto, no hay relación.
LINEA_ALCANCE = ("Cuando el texto (el de tu unidad o el heredado) nombre al colectivo del TO con una expresión genérica "
                 "('las entidades', 'los sujetos obligados'), {sug}, con esa expresión copiada del texto como "
                 "`sujeto_mencion`. Si el texto no nombra a ningún sujeto, no emitas la relación: este alcance no "
                 "reemplaza la mención. Es el sujeto de aplica_a cuando el texto se dirige al colectivo; NO es el "
                 "ejecutor por defecto en ejecuta.")


def linea_alcance(rol: dict | None) -> list[str]:
    if rol is None:
        return []
    miembros = ", ".join(rol["miembros_labels"])
    if rol.get("rol_id"):
        cab, sug = f"Alcance de este TO: {rol['rol_id']} = {{{miembros}}}. ", f"sugerí {rol['rol_id']} en `sujeto_id`"
    else:
        ids = " o ".join(rol["clase_ids"])
        cab, sug = f"Alcance de este TO: {{{miembros}}}. ", f"sugerí {ids} en `sujeto_id`, según corresponda"
    return [cab + LINEA_ALCANCE.format(sug=sug), ""]


def build_user_message_r2b(chunk: dict) -> str:
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
    partes.extend(linea_alcance(alcance_del_documento(chunk["archivo"])))
    herencia = chunk.get("herencia", [])
    if herencia:
        i = bloque_lista(chunk)
        if mini:
            partes.append(LINEA_MINI_MITAD if mini_a_mitad(chunk) else LINEA_TITULOS_MINI)
        elif i is not None:
            h = herencia[i]
            partes.append(LINEA_ITEM.format(tipo=h["tipo"], unidad=h["unidad_origen"],
                                            cierres=CIERRES if i < len(herencia) - 1 else ""))
        else:
            partes.append(LINEA_HERENCIA_PUNTO)
        if chunk.get("herencia_recortada"):
            partes.append(LINEA_RECORTE)
        for h in herencia:
            partes.append(f"[{h['tipo']} | punto {h['unidad_origen']}]")
            partes.append(h["texto"])
        partes.append("")
    partes.extend(bloque_flags(chunk))
    if mini:
        partes.append(f"Texto del bloque {chunk['rol_bloque']} del punto {chunk['unidad']} (TU unidad de extracción):")
    else:
        partes.append(f"Texto del punto {chunk['unidad']}:")
    partes.append("```")
    partes.append(chunk["texto"])
    partes.append("```")
    partes.append("")
    partes.append(LINEA_CIERRE)
    return "\n".join(partes)


def build_request_kwargs_r2b(chunk: dict, model: str, max_tokens: int = MAX_OUTPUT_TOKENS) -> dict:
    """Request completo con el prefijo r2b; lo variable, solo en messages (base de la clave de la caché)."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": TEMPERATURA_E1_R2B,
        "system": bloques_sistema_r2b(),
        "tools": [TOOL_SCHEMA_R2B],
        "tool_choice": {"type": "tool", "name": NOMBRE_TOOL},
        "messages": [{"role": "user", "content": build_user_message_r2b(chunk)}],
    }


def kwargs_reintento_forma_r2b(kwargs: dict) -> dict:
    """P5: el pedido del reintento por salida mal formada, el que produjo la salida (con su techo) con la temperatura
    del reintento; el pedido recibido no se toca. Lo usa runner_corpus.kwargs_reintento_forma con el perfil r2b."""
    return dict(kwargs, temperature=TEMPERATURA_REINTENTO_FORMA_R2B)


def labels_catalogo_r2() -> dict[str, dict]:
    """id → {label, nivel} del catálogo r2 (labels_e2_r2.json), para el E2 del perfil de E1."""
    return {sid: {"label": x["label"], "nivel": x["nivel"]} for sid, x in LABELS_E2_R2.items()}


# Registro de alcance por tanda en el mensaje (U-ALCANCE-E1; mandato docs/mandatos/UALCANCE_E1_cableado_registro_alcance.md,
# firmado el 07/10/2026; enmienda 4 al protocolo entre tandas, §7, punto 1). La línea «Alcance de este TO» de
# build_user_message_r2b sale de la tabla de la release (rol_por_to_r2.json) y, si el documento no tiene entrada ahí, del
# derivado del registro de alcance por tanda: catalogo_unico/registro_alcance_r2b.json, que escribe
# catalogo_unico/code/derivar_registro_alcance_r2b.py desde registro_alcance_por_tanda.md con el lector de R2-2 de
# U-RERESOL-CAT (fuera de generados_r2/, cuyo contenido cierra K2 de selftest_catalogo_unico). El derivado se lee al importar,
# con su candado (decisión 1 de la autora al firmar), antes del candado del mensaje. No cambia el prefijo, el tool schema ni
# el namespace; cambian el mensaje, y la clave de E1, solo las unidades de los documentos con entrada en el derivado.
# A2 (15/10/2026): el derivado sale de `--tandas 1` sobre el registro final de la tanda 1 (06b8267a3004…; 10 entradas, con
# ri_mmsef); en A1 había salido de ce402aad7c84… (9 entradas). Los dos valores del candado del mensaje cubren la fixture
# de 17 unidades (los de P3c-2, con 13, eran 4d69f7f4c8a5… y a9cb702c0d24…). Un cambio del registro entre tandas regenera
# el derivado y su sha (fila F13c de la tabla de reprocesamiento).
# A3 (18/10/2026): el derivado sale de `--tandas 1,final` sobre el registro con la tanda final (a4b52cd2fdbb…; 43 entradas).
REGISTRO_ALCANCE_R2B_JSON = _CAT_R2.parent / "registro_alcance_r2b.json"
REGISTRO_ALCANCE_R2B_SHA256_ESPERADO = "c8dea08a2ffe2eeb401855f952cc80f26542da8ea2489eac7a6f83530b6857ca"
REGISTRO_ALCANCE_R2B = json.loads(_leer_con_candado(REGISTRO_ALCANCE_R2B_JSON, REGISTRO_ALCANCE_R2B_SHA256_ESPERADO))


def alcance_del_documento(archivo: str) -> dict | None:
    """La entrada de alcance de un documento: primero la tabla de la release (ROL_POR_TO_R2); si el documento no tiene
    entrada ahí, el derivado del registro de alcance por tanda (REGISTRO_ALCANCE_R2B); si no figura en ninguno, o el
    registro lo declara sin alcance (sin entrada en el derivado), None: el mensaje va sin línea de alcance."""
    if archivo in ROL_POR_TO_R2:
        return ROL_POR_TO_R2[archivo]
    return REGISTRO_ALCANCE_R2B.get(archivo)


# Candado del mensaje de E1 (P3c-2; U-TABLA-REPROC, filas F22 y F22b). El mensaje no entra al hash del prefijo ni al
# namespace: un cambio en una línea fija o condicional, o en la regla que la dispara, movería las claves sin que nada
# frene. El candado arma el mensaje de un conjunto fijo de unidades que ejercita cada rama de build_user_message_r2b y
# de bloque_flags (candado_mensaje_r2b.json: 12 unidades de salida_tanda0_r2b, elegidas por cobertura en
# data/experiment/prompt_r2/p3c/candados_p3c.py, más una copia sintética para la rama del alcance por clase y, desde
# U-ALCANCE-E1, cuatro copias sintéticas con documentos del registro de alcance: una clase, dos clases, un rol reutilizado
# y uno declarado sin alcance) y compara su sha256 con el sellado. Solo compara: no entra al pedido ni cambia ninguna
# clave. Va al final del módulo.
def sha256_mensajes(chunks: list[dict]) -> str:
    """sha256 de los mensajes de E1 de `chunks`, unidos por un salto, el separador de registro (U+001E) y otro salto."""
    return hashlib.sha256("\n\x1e\n".join(build_user_message_r2b(c) for c in chunks).encode("utf-8")).hexdigest()


def _candado_mensaje() -> None:
    doc = json.loads(_leer_con_candado(CANDADO_MENSAJE_JSON, CANDADO_MENSAJE_JSON_SHA256_ESPERADO))
    sha = sha256_mensajes(doc["chunks"])
    if sha != MENSAJE_R2B_SHA256_ESPERADO:
        raise RuntimeError(f"candado r2b: el mensaje de E1 de las unidades fijas tiene sha256 {sha[:12]}… (sellado "
                           f"{MENSAJE_R2B_SHA256_ESPERADO[:12]}…): cambió una línea del mensaje, la regla que la "
                           f"dispara, la línea de alcance o la lista de tablas forzadas — se frena")


_candado_mensaje()


__all__ = [
    "PREFIJO_SISTEMA_R2B", "TOOL_SCHEMA_R2B", "ROL_POR_TO_R2", "REGISTRO_ALCANCE_R2B", "REEMPLAZOS_R2B",
    "TABLAS_RESIDUALES_FORZADAS", "alcance_del_documento",
    "PREFIJO_HASH_R2B", "PREFIJO_SHA256_R2B", "PREFIJO_CANONICO_R2B", "MAX_OUTPUT_TOKENS", "NOMBRE_TOOL",
    "TEMPERATURA_E1_R2B", "TEMPERATURA_REINTENTO_FORMA_R2B",
    "bloques_sistema_r2b", "build_user_message_r2b", "build_request_kwargs_r2b", "kwargs_reintento_forma_r2b",
    "estado_tablas", "tiene_riesgo",
    "es_item", "es_encabezado_de_lista", "labels_catalogo_r2",
]
