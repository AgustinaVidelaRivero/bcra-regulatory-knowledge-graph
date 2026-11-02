#!/usr/bin/env python3
"""Validador de shapes v0 (capas 1 y 2) para los kg.json del experimento.

Reglas determinísticas (sin LLM) S1-S12 y S15 sobre la estructura del grafo.
El kg.json de entrada es SOLO LECTURA: este script no lo modifica jamás.
Lo único que escribe es el reporte Markdown indicado por --out, y solo si esa
opción se pasa.

Uso:
    python3 scripts/shapes_validator.py [--kg RUTA] [--out RUTA]
                                        [--excepciones RUTA]
                                        [--perfil congelado]

`--out` NO tiene default: sin esa opción el validador reporta por consola y no
escribe archivo alguno. Antes apuntaba a un reporte commiteado del repo y lo
sobrescribía en silencio (ver el comentario de DEFAULT_OUT).

S15 (U-ESQ-V3) es la guarda de la taxonomía de roles: un rol sin aristas
`miembro_de` entrantes es un nodo aislado del árbol, y las normas del TO que
lo declara dejan de ser alcanzables por navegación taxonómica — el mecanismo
que el capítulo del esquema presenta como aporte del grafo frente al
fragmento. Su tercera cláusula obliga a que la deuda quede VISIBLE Y CONTADA:
los roles sin miembro adjudicable se declaran en una lista, y el validador
compara la cuenta declarada contra la medida.

`--excepciones` apunta al artefacto que declara esa lista (el bloque
`excepciones_s15` de un esquema de clases, p. ej.
`data/experiment/esq_v3_miembros/esquema_v3_clases.json`). SIN esa opción la
lista declarada es vacía y cualquier rol huérfano es FAIL, que es el
comportamiento seguro por defecto.

S13, S14, S16 y S17 NO están implementadas y no se inventan: el orden de
reporte es la lista explícita S1..S12 + S15, sin huecos silenciosos.

PERFIL «CONGELADO» (U-B2.2 fase 2). Sin `--perfil`, el comportamiento es el
de siempre: mismo reporte, misma consola, mismo código de salida. Con
`--perfil congelado` el validador evalúa el grafo contra el esquema congelado
de la generación 3:

- El vocabulario (9 tipos, 13 predicados, matriz dominio/rango, enum de
  Obligacion.tipo y sus valores retirados) se LEE de
  `data/experiment/esq/code/prompt_congelado.py`; nada de eso se copia acá.
  El único dato propio es el candado: el sha256 del texto del prefijo
  congelado (`e69feaaa…`, laudo_esquema_congelado.md §4). Si el módulo no lo
  reproduce, el validador FRENA con código de salida 2 antes de evaluar nada.
- El catálogo de sujetos (ids de `clases` ∪ `roles`) se lee del mismo
  artefacto de `--excepciones` que S15.
- Severidad en dos secciones y veredicto global PASA / NO PASA:
  BLOQUEANTES = S1, S2, S3, S4, S5, S6, S15, S19 (catálogo) y S20 (enum);
  INFORMATIVAS con conteo = S7, S8, S9, S10, S11, S12, S21, S22 y S23.
  Código de salida 1 cuando el veredicto es NO PASA.
- Tolerancia: referencia nodo→nodo (rol_fuente=referencia_cruzada) y
  padre_sugerido se ADMITEN en S1/S3 y no se exigen; su coherencia interna se
  mide en S21 y S22 (informativas).
- Junto al reporte .md se escribe un .json con los conteos de cada shape y
  el veredicto, para comparar grafos sin parsear markdown.
- Numeración: S18 ya está declarado en docs/esquema_v2_diseño.md con otro
  enunciado (umbral de `limita`), así que las shapes nuevas del perfil se
  numeran desde S19 (ver NUMERACION_PERFIL). S9 (descripción canónica) se
  evalúa en el perfil como informativa, con el mismo cómputo que v0.

PERFIL «r2» (U-R2-CODIGO, R5.b; enmienda 1 a su mandato, R5.c; L-ESQ-R2 y su
enmienda 2). Con `--perfil r2`:

- El vocabulario se LEE de `data/experiment/pyd_r2/generados/enums_r2.json`
  (generado por U-PYD desde modelos_r2.py), con candado de sha256; las marcas
  de nodo (MARCAS_NODO) se leen del fuente de modelos_r2.py con `ast`, sin
  importarlo (Pydantic). El catálogo de sujetos es el único
  (`catalogo_unico/generados_r2/ids_s19_r2.json`) y la lista de S15 la de
  `entrada_esqueleto_r2.json`.
- La remisión entre puntos es `remite_a` (scripts/remisiones.py, solo stdlib):
  S3 controla su firma; una `referencia` con origen distinto de TextoOrdenado
  es violación, con o sin rol_fuente (la tolerancia de rol_fuente queda solo
  en el perfil congelado); S21 lee las remisiones con la función.
- Shapes nuevas: S18 reescrita, S24 a S29 (diseño de U-LISTAS-NOMAP, §g) y,
  después de S29, S30 (alcance de `remite_a`) y S31 (evidencia de `remite_a`
  dentro de un único tramo del texto de E0 de su chunk; sin `--e0` da «NO
  COMPUTABLE»). S27 es informativa con `--fase r2a` (default) y bloqueante con
  `--fase r2b`. S28 lee el registro de no mapeados (`--registro-dir`, default
  el directorio del kg.json; sin registro, «NO COMPUTABLE»).
- S32 (U-REEXT-T0, T1, punto 4.b), informativa: cuantía en la descripción =>
  elemento en la lista de umbrales, con el detector de cuantías del pipeline
  (pyd_r2/code/reglas_comparacion.py, solo stdlib, cargado del fuente).
- Veredicto: NO PASA si alguna bloqueante falla; INCOMPLETO si ninguna falla y
  alguna bloqueante es NO COMPUTABLE; PASA si no. Código de salida 0 / 1 / 3.

Solo stdlib (sin dependencias de terceros). El módulo de vocabulario se
importa con `sys.dont_write_bytecode = True` para no dejar __pycache__.
"""

import argparse
import ast
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remisiones  # noqa: E402  scripts/remisiones.py, solo stdlib (enmienda 1, R5.a)
del sys.path[0]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KG = os.path.join(
    REPO_ROOT,
    "data", "experiment", "run_3_ppf_core", "kg.json",
)
# SIN default de salida (U-ESQ-V3). Hasta acá el default era
# reports/shapes_run_3_v0.md, un reporte COMMITEADO: correr la herramienta sin
# --out sobrescribía un artefacto del repo en silencio. El incidente está
# registrado desde el 02/08/2026 (data/backlog/retests/C3_retest_2026-08-02.md
# §Incidente: «escritura fuera del mandato, revertida con git checkout») y
# volvió a dispararse sobre el mismo archivo durante U-ESQ-V3. El checklist de
# un gate obliga a quien lo lee; el default obliga a cualquiera que corra la
# herramienta, así que el arreglo va acá.
#
# Sin --out el validador NO escribe: reporta por consola y listo. Es el mismo
# criterio que ya había adoptado la adaptación v2 de esta herramienta
# (data/experiment/grafo_v2/code/shapes_v2.py: `--out default=None`).
DEFAULT_OUT = None

RELACIONES_12 = {
    "aplica_a", "regula", "prohibe", "limita", "exceptua",
    "exceptua_obligacion", "requiere", "condiciona", "ejecuta",
    "establecida_en", "referencia", "modificada_por",
}

# S3 — matriz de firmas: relación -> (dominios permitidos, rango)
FIRMAS = {
    "establecida_en": ({"Obligacion", "Restriccion", "Operacion", "Excepcion"}, "TextoOrdenado"),
    "aplica_a": ({"Obligacion", "Restriccion"}, "EntidadFinanciera"),
    "regula": ({"Obligacion", "Restriccion"}, "Operacion"),
    "limita": ({"Restriccion"}, "Operacion"),
    "prohibe": ({"Restriccion"}, "Operacion"),
    "condiciona": ({"Obligacion"}, "Operacion"),
    "requiere": ({"Operacion"}, "Obligacion"),
    "exceptua": ({"Excepcion"}, "Restriccion"),
    "exceptua_obligacion": ({"Excepcion"}, "Obligacion"),
    "ejecuta": ({"EntidadFinanciera"}, "Operacion"),
    "referencia": ({"TextoOrdenado"}, "Comunicacion"),
    "modificada_por": ({"TextoOrdenado"}, "Comunicacion"),
}

UNIDADES_REGULATORIAS = ("Obligacion", "Restriccion", "Excepcion")

# S15 — orden de reporte. S13, S14, S16 y S17 no están implementadas: la lista
# es explícita para que su ausencia se lea, en vez de esconderse en un range().
ORDEN_SHAPES = [f"S{i}" for i in range(1, 13)] + ["S15"]
SHAPES_NO_IMPLEMENTADAS = ("S13", "S14", "S16", "S17")

# ---------------------------------------------------------------------------
# Perfil «congelado» (U-B2.2 fase 2) — constantes
# ---------------------------------------------------------------------------
PERFILES = ("congelado", "r2")

# Módulo del que se LEE el vocabulario congelado. No se copia nada de su
# contenido acá: tipos, predicados, matriz y enum se leen al cargar.
RUTA_PROMPT_CONGELADO = os.path.join(
    REPO_ROOT, "data", "experiment", "esq", "code", "prompt_congelado.py")

# Candado: sha256 del TEXTO del prefijo congelado, tal como lo registra el
# laudo de esquema congelado §4 (data/experiment/esq/laudo_esquema_congelado.md,
# líneas 136-137). Es el único dato del vocabulario que vive en este archivo,
# y vive acá porque es lo que se verifica contra el módulo, no algo que se
# lea de él.
SHA256_PREFIJO_CONGELADO_ESPERADO = (
    "e69feaaa04779bd6347cc9e3974d2c1749519f1230e70a0459e66f46517cd720")

# Valor cuyo retiro del enum el laudo §4 materializó; el validador exige que
# el módulo lo declare entre los retirados (si no, el módulo no es el que el
# laudo describe y se frena).
VALOR_RETIRADO_OBLIGATORIO = "requisito_de_estructura"

RELACIONES_ESQUELETO = ("subclase_de", "miembro_de", "instancia_de", "parte_de")
RELACION_PADRE_SUGERIDO = "padre_sugerido"
ROL_FUENTE_REFERENCIA_CRUZADA = "referencia_cruzada"
ROL_DOCUMENTAL_ESQUELETO = "esqueleto"
CLAVES_PROVENANCE_G3 = ("to", "archivo", "punto", "rol_documental")
NIVELES_SUJETO = ("clase", "instancia", "rol", "propuesto")
NIVELES_PADRE = ("clase", "rol")

BLOQUEANTES_CONGELADO = ("S1", "S2", "S3", "S4", "S5", "S6", "S15", "S19", "S20")
INFORMATIVAS_CONGELADO = ("S7", "S8", "S9", "S10", "S11", "S12", "S21", "S22", "S23")
ORDEN_SHAPES_CONGELADO = list(BLOQUEANTES_CONGELADO) + list(INFORMATIVAS_CONGELADO)

# Tabla número -> enunciado de las shapes NUEVAS del perfil. Los números
# S13/S14/S16/S17 (no implementadas, docs/esquema_v2_diseño.md:318-322) y S18
# (docs/esquema_v2_diseño.md:325: «Si una Restricción tiene arista limita,
# tiene property umbral») están declarados con enunciados que NO coinciden
# con lo que este perfil implementa, así que no se reutilizan.
NUMERACION_PERFIL = {
    "S19": "Catálogo de sujetos (bloqueante): todo Sujeto tiene nivel válido; "
           "si no es propuesto, su id está en el catálogo; si es propuesto, "
           "tiene cuarentena y padre_sugerido.",
    "S20": "Enum de Obligacion.tipo (bloqueante): todo Obligacion.tipo está en "
           "el enum congelado; conteos separados de valores retirados y de "
           "otros valores fuera del enum.",
    "S21": "Coherencia de referencias nodo→nodo (informativa): destino sin "
           "prefijo <to>:: pertenece al conjunto de puntos del nodo destino; "
           "desglose por via.",
    "S22": "Coherencia de padre_sugerido (informativa): destino de la arista = "
           "properties.padre_sugerido del origen y el origen está en "
           "cuarentena.",
    "S23": "aplica_a hacia sujetos en cuarentena (informativa): aristas "
           "aplica_a cuyo destino es Sujeto de nivel propuesto.",
}

# ---------------------------------------------------------------------------
# Perfil «r2» (U-R2-CODIGO, R5.b) — constantes
# ---------------------------------------------------------------------------
RUTA_ENUMS_R2 = os.path.join(REPO_ROOT, "data", "experiment", "pyd_r2", "generados", "enums_r2.json")
RUTA_MODELOS_R2 = os.path.join(REPO_ROOT, "data", "experiment", "pyd_r2", "code", "modelos_r2.py")
# S32 (U-REEXT-T0, T1, punto 4.b): el detector de cuantías del pipeline (reglas_comparacion.detectar_cuantias, solo
# stdlib), cargado del fuente; no se copia nada acá.
RUTA_REGLAS_COMPARACION = os.path.join(REPO_ROOT, "data", "experiment", "pyd_r2", "code", "reglas_comparacion.py")
RUTA_GENERADOS_R2 = os.path.join(REPO_ROOT, "data", "experiment", "catalogo_unico", "generados_r2")
RUTA_IDS_S19_R2 = os.path.join(RUTA_GENERADOS_R2, "ids_s19_r2.json")
RUTA_EXCEPCIONES_S15_R2 = os.path.join(RUTA_GENERADOS_R2, "entrada_esqueleto_r2.json")
# Candado: sha256 de enums_r2.json en el commit de cierre de U-PYD (57a8dd2) y
# en HEAD al escribir el perfil (`git show HEAD:data/experiment/pyd_r2/generados/enums_r2.json | shasum -a 256`).
SHA256_ENUMS_R2_ESPERADO = "abd197ac8bbb818f680dc80d1b9c9df3e1f1f733fce3fd46b35e7440e7ce4241"
FASES_R2 = ("r2a", "r2b")
REGISTRO_NO_MAPEADOS = "no_mapeados_sujetos.jsonl"
NO_COMPUTABLE = "NO COMPUTABLE"

BLOQUEANTES_R2 = ("S1", "S2", "S3", "S4", "S5", "S6", "S15", "S18", "S19", "S20", "S24", "S25", "S26",
                  "S28", "S29", "S30", "S31")
INFORMATIVAS_R2 = ("S7", "S8", "S9", "S10", "S11", "S12", "S21", "S22", "S23", "S32")

NUMERACION_PERFIL_R2 = {
    "S18": "Reescrita (L-ESQ-R2 §1.5): Restriccion de tipo limite_cuantitativo => lista de umbrales "
           "no vacía o marca (el umbral guardado sin lista: campos_heredados_v3.umbral o "
           "properties_no_definidas.umbral; en r2b, también la marca properties_no_definidas."
           "umbral_no_cuantificable del ensamblado). El enunciado de docs/esquema_v2_diseño.md:325 no rige en el perfil r2.",
    "S24": "Enum de Restriccion.tipo (bloqueante salvo la marca fuera_de_lista).",
    "S25": "Enum de Comunicacion.tipo, con «externa» (bloqueante salvo la marca fuera_de_lista).",
    "S26": "Claves cerradas por tipo (bloqueante).",
    "S27": "Arista de sujeto con mención y método (informativa en r2a, bloqueante desde r2b).",
    "S28": "Sujeto propuesto con fila en el registro de no mapeados (bloqueante).",
    "S29": "Destino de padre_sugerido en el catálogo único (bloqueante: U-CAT-UNICO está cerrada).",
    "S30": "alcance de remite_a en la lista cerrada y coherente con los extremos (bloqueante).",
    "S31": "evidencia de remite_a: tramo literal de un único tramo del texto de E0 de su chunk_id "
           "(bloqueante; sin --e0, NO COMPUTABLE).",
    "S32": "Cuantía en la descripción => elemento en la lista (informativa; L-ESQ-R2 §1.5 y "
           "reports/u_umbral/reporte_u_umbral.md §2): en los tipos con lista de umbrales, un nodo cuya descripción "
           "trae una cuantía (reglas_comparacion.detectar_cuantias) tiene la lista no vacía o el umbral guardado "
           "(marca); aparte, las cuantías de la descripción sin un elemento de igual valor y unidad.",
}

# Shapes de v0 que quedan FUERA del perfil, declaradas para que el hueco se
# lea (mismo criterio que SHAPES_NO_IMPLEMENTADAS). Hoy ninguna: S9 entró al
# perfil como informativa al cierre de la unidad. El mecanismo se conserva.
FUERA_DEL_PERFIL = {}


class VocabularioCongeladoError(RuntimeError):
    """El módulo de vocabulario no es el que el laudo describe: se frena."""


class CandadoShaError(VocabularioCongeladoError):
    """El sha del prefijo congelado no coincide con el esperado."""


def cargar_excepciones_s15(ruta):
    """Lee el bloque `excepciones_s15` del artefacto indicado.

    Devuelve (ids_declarados, total_declarado, por_causa, defecto). `defecto`
    describe un problema del propio artefacto (ilegible, sin bloque, cuenta
    interna inconsistente) y hace fallar S15: una lista de excepciones que no
    se puede leer no es una deuda declarada."""
    if not ruta:
        return set(), 0, {}, None
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return set(), 0, {}, f"no se pudo leer {ruta}: {e}"
    bloque = d.get("excepciones_s15")
    if not isinstance(bloque, dict):
        return set(), 0, {}, f"{ruta} no declara un bloque 'excepciones_s15'"
    filas = bloque.get("roles") or []
    ids = {r.get("rol_id") for r in filas if r.get("rol_id")}
    total = bloque.get("total")
    por_causa = bloque.get("por_causa") or {}
    if total != len(filas):
        return ids, total, por_causa, (
            f"el artefacto se contradice: declara total={total} y lista {len(filas)} roles")
    if por_causa and sum(por_causa.values()) != len(filas):
        return ids, total, por_causa, (
            f"el artefacto se contradice: la suma por causa ({sum(por_causa.values())}) "
            f"no reproduce el total listado ({len(filas)})")
    return ids, total, por_causa, None


def cargar_catalogo_sujetos(ruta):
    """Lee el catálogo de sujetos del artefacto de --excepciones: los ids de
    `clases` ∪ `roles` (esquema_v3_clases.json). Devuelve
    (ids, n_clases, n_roles, defecto). Sin ruta el catálogo es vacío y el
    defecto lo dice: todo Sujeto no propuesto queda fuera del catálogo, que
    es el comportamiento seguro por defecto (mismo criterio que S15)."""
    if not ruta:
        return set(), 0, 0, "no se pasó --excepciones: el catálogo de sujetos es vacío"
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        return set(), 0, 0, f"no se pudo leer {ruta}: {e}"
    clases = d.get("clases")
    roles = d.get("roles")
    if not isinstance(clases, list) or not isinstance(roles, list):
        return set(), 0, 0, f"{ruta} no declara las listas 'clases' y 'roles'"
    ids = {c.get("id") for c in clases if isinstance(c, dict) and c.get("id")}
    ids |= {r.get("id") for r in roles if isinstance(r, dict) and r.get("id")}
    return ids, len(clases), len(roles), None


def cargar_vocabulario_congelado(ruta=RUTA_PROMPT_CONGELADO,
                                 sha_esperado=SHA256_PREFIJO_CONGELADO_ESPERADO):
    """Importa prompt_congelado.py y devuelve su vocabulario como dict.

    FRENA (CandadoShaError) si el sha256 del texto del prefijo congelado que
    el módulo calcula no es el esperado, y (VocabularioCongeladoError) si el
    módulo no declara `requisito_de_estructura` entre los valores retirados
    del enum. Los valores retirados se derivan del propio módulo: los del
    enum v2 que importa (`pr2.OBLIGACION_TIPO_V2`) que no están en
    `OBLIGACION_TIPO_CONGELADO`."""
    sys.dont_write_bytecode = True  # el import no debe dejar __pycache__
    if not os.path.isfile(ruta):
        raise VocabularioCongeladoError(f"no existe el módulo de vocabulario {ruta}")
    spec = importlib.util.spec_from_file_location("prompt_congelado", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sha = getattr(mod, "PREFIJO_SHA256_CONGELADO", None)
    if sha != sha_esperado:
        raise CandadoShaError(
            f"candado del sha: el módulo {ruta} declara PREFIJO_SHA256_CONGELADO="
            f"{sha}, esperado {sha_esperado} — el vocabulario no es el sellado, se frena")
    enum = tuple(mod.OBLIGACION_TIPO_CONGELADO)
    retirados = tuple(v for v in mod.pr2.OBLIGACION_TIPO_V2 if v not in enum)
    if VALOR_RETIRADO_OBLIGATORIO not in retirados:
        raise VocabularioCongeladoError(
            f"el módulo no declara '{VALOR_RETIRADO_OBLIGATORIO}' entre los valores "
            f"retirados del enum (retirados={retirados}) — se frena")
    return {
        "modulo": ruta,
        "sha256_prefijo": sha,
        "hash_prefijo": getattr(mod, "PREFIJO_HASH_CONGELADO", None),
        "entity_types": tuple(mod.ENTITY_TYPES_CONGELADO),
        "predicates": tuple(mod.PREDICATES_CONGELADO),
        "domain_range": {p: (set(d), set(r)) for p, (d, r) in mod.DOMAIN_RANGE_CONGELADO.items()},
        "obligacion_tipo": enum,
        "retirados": retirados,
    }


def norm(s):
    """NFD + remoción de diacríticos + lowercase (normalización de los censos)."""
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def check_provenance(prov):
    """Devuelve lista de defectos de un dict de provenance según S4."""
    defectos = []
    if not isinstance(prov, dict):
        return [f"provenance no es dict (es {type(prov).__name__})"]
    keys = set(prov.keys())
    if keys != {"source_doc", "location"}:
        defectos.append(f"keys {sorted(keys)} != ['location', 'source_doc']")
    for k in ("source_doc", "location"):
        v = prov.get(k)
        if not isinstance(v, str) or not v.strip():
            defectos.append(f"{k} vacío o no-string")
    return defectos


def check_provenance_g3(prov, provs):
    """Defectos de provenance de la generación 3 (S4 del perfil congelado):
    dict con al menos {to, archivo, punto, rol_documental}; `provenances` lista
    no vacía con provenance == provenances[0]; para rol_documental distinto de
    esqueleto, `to` y `archivo` strings no vacíos (para esqueleto se admiten
    to nulo, chunk_id nulo y paginas vacía)."""
    if not isinstance(prov, dict):
        return [f"provenance no es dict (es {type(prov).__name__})"]
    defectos = []
    faltan = [k for k in CLAVES_PROVENANCE_G3 if k not in prov]
    if faltan:
        defectos.append(f"faltan claves {faltan}")
    rol = prov.get("rol_documental")
    if rol != ROL_DOCUMENTAL_ESQUELETO:
        for k in ("to", "archivo"):
            v = prov.get(k)
            if not isinstance(v, str) or not v.strip():
                defectos.append(f"{k} vacío o no-string (rol_documental={rol!r})")
    if not isinstance(provs, list) or not provs:
        defectos.append("provenances vacía o no-lista")
    elif provs[0] != prov:
        defectos.append("provenance != provenances[0]")
    return defectos


def _res(rid, enunciado, result, resumen, detalle_md, detalle_consola=None, conteos=None):
    """Registro de resultado de una shape (mismo contrato que `registrar` de
    main; `conteos` es la vista numérica que va al .json del perfil)."""
    return {
        "rid": rid,
        "enunciado": enunciado,
        "result": result,
        "resumen": resumen,
        "detalle_md": detalle_md,
        "detalle_consola": detalle_consola if detalle_consola is not None else detalle_md,
        "conteos": conteos or {},
    }


def lista_consola(items, limite=50):
    if len(items) <= limite:
        return items
    return items[:limite] + [f"... ({len(items)} en total; lista completa en el reporte)"]


def nivel_de(n):
    return ((n or {}).get("properties") or {}).get("nivel")


def en_cuarentena(props):
    """`cuarentena` verdadera: True o la string 'true' (es lo que emite r1)."""
    v = (props or {}).get("cuarentena")
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


def destino_sin_prefijo(destino):
    """`cap::4.1` -> `4.1` (el prefijo es el código del TO seguido de `::`)."""
    if not isinstance(destino, str):
        return destino
    return destino.split("::", 1)[1] if "::" in destino else destino


# ---------------------------------------------------------------------------
# Shapes compartidas por v0 y por el perfil (mismo cómputo, extraídas de main)
# ---------------------------------------------------------------------------
def shape_s2(edges, node_by_id):
    viol = []
    for i, e in enumerate(edges):
        faltan = [x for x in ("source", "target") if e[x] not in node_by_id]
        if faltan:
            viol.append(f"idx {i}: {e['relation']} {e['source']} -> {e['target']} (inexistente: {', '.join(faltan)})")
    return _res(
        "S2", "Integridad referencial: origen y destino de toda arista existen como nodos.",
        "PASS" if not viol else "FAIL",
        f"{len(viol)} aristas colgantes sobre {len(edges)}.",
        viol,
        conteos={"aristas": len(edges), "colgantes": len(viol)},
    )


def shape_s7(nodes):
    grupos = defaultdict(list)
    for n in nodes:
        grupos[(n["type"], norm(n["label"]))].append(n)
    dups = {k: v for k, v in grupos.items() if len(v) > 1}
    detalle = []
    for (t, l), ns in sorted(dups.items()):
        detalle.append(f"[{t}] '{l}' ({len(ns)} nodos):")
        for n in ns:
            detalle.append(f"    - {n['id']}  (label: '{n['label']}')")
    return _res(
        "S7", "ERROR — Unicidad exacta: no puede haber dos nodos con el mismo (type, label normalizado).",
        "PASS" if not dups else "FAIL",
        f"{len(dups)} grupos violatorios ({sum(len(v) for v in dups.values())} nodos involucrados).",
        detalle,
        conteos={"grupos": len(dups), "nodos_involucrados": sum(len(v) for v in dups.values())},
    )


def shape_s8(nodes):
    grupos2 = defaultdict(list)
    for n in nodes:
        grupos2[norm(n["label"])].append(n)
    cross = {l: ns for l, ns in grupos2.items()
             if len(ns) > 1 and len({n["type"] for n in ns}) > 1}
    detalle = []
    for l, ns in sorted(cross.items()):
        detalle.append(f"'{l}' ({len(ns)} nodos):")
        for n in ns:
            detalle.append(f"    - [{n['type']}] {n['id']}")
    return _res(
        "S8", "WARN — Colisión de label normalizado entre types distintos.",
        "PASS" if not cross else "WARN",
        f"{len(cross)} grupos con el mismo label normalizado en types distintos.",
        detalle,
        conteos={"grupos": len(cross)},
    )


def shape_s9(nodes):
    ambas = [n for n in nodes
             if "descripcion" in (n.get("properties") or {}) and "description" in (n.get("properties") or {})]
    tabla = []
    for t in sorted({n["type"] for n in nodes}):
        ns = [n for n in nodes if n["type"] == t]
        c_desc = sum(1 for n in ns if "descripcion" in (n.get("properties") or {}))
        c_engl = sum(1 for n in ns if "description" in (n.get("properties") or {}))
        c_ambas = sum(1 for n in ns
                      if "descripcion" in (n.get("properties") or {}) and "description" in (n.get("properties") or {}))
        c_ninguna = sum(1 for n in ns
                        if "descripcion" not in (n.get("properties") or {}) and "description" not in (n.get("properties") or {}))
        tabla.append(f"{t}: descripcion={c_desc}, description={c_engl}, ambas={c_ambas}, ninguna={c_ninguna} (total {len(ns)})")
    detalle = ["Tabla por type (usa cada key / ambas / ninguna):"] + [f"  {r}" for r in tabla] + \
              ["", f"Nodos con AMBAS keys ({len(ambas)}):"] + [f"    - [{n['type']}] {n['id']}" for n in ambas]
    return _res(
        "S9", "ERROR — Descripción canónica: ningún nodo tiene a la vez 'descripcion' y 'description'.",
        "PASS" if not ambas else "FAIL",
        f"{len(ambas)} nodos con ambas keys.",
        detalle,
        conteos={"nodos_con_ambas_keys": len(ambas)},
    )


def shape_s10(nodes, out_edges, tipos=UNIDADES_REGULATORIAS, enunciado=None):
    sin_est = defaultdict(list)
    for n in nodes:
        if n["type"] in tipos:
            if not any(norm(e["relation"]) == "establecida_en" for e in out_edges[n["id"]]):
                sin_est[n["type"]].append(n["id"])
    total_sin = sum(len(v) for v in sin_est.values())
    detalle = []
    for t in tipos:
        detalle.append(f"{t}: {len(sin_est[t])} sin establecida_en")
        for i in sin_est[t]:
            detalle.append(f"    - {i}")
    return _res(
        "S10",
        enunciado or f"ERROR — Toda unidad regulatoria ({'/'.join(tipos)}) tiene >=1 arista saliente establecida_en.",
        "PASS" if total_sin == 0 else "FAIL",
        "Sin establecida_en: " + ", ".join(f"{t}={len(sin_est[t])}" for t in tipos) + f" (total {total_sin}).",
        detalle,
        conteos={"total_sin_establecida_en": total_sin, "por_tipo": {t: len(sin_est[t]) for t in tipos}},
    )


def shape_s11(nodes, out_edges, tipos=("Obligacion", "Restriccion"), enunciado=None):
    sin_apl = defaultdict(list)
    for n in nodes:
        if n["type"] in tipos:
            if not any(norm(e["relation"]) == "aplica_a" for e in out_edges[n["id"]]):
                sin_apl[n["type"]].append(n["id"])
    total_sin = sum(len(v) for v in sin_apl.values())
    detalle = []
    for t in tipos:
        detalle.append(f"{t}: {len(sin_apl[t])} sin aplica_a")
        for i in sin_apl[t]:
            detalle.append(f"    - {i}")
    return _res(
        "S11",
        enunciado or f"WARN — Toda {' y '.join(tipos)} tiene >=1 arista saliente aplica_a.",
        "PASS" if total_sin == 0 else "WARN",
        "Sin aplica_a: " + ", ".join(f"{t}={len(sin_apl[t])}" for t in tipos) + f" (total {total_sin}).",
        detalle,
        detalle_consola=[f"{t}: {len(sin_apl[t])} sin aplica_a" for t in tipos]
        + [f"(ids completos en el reporte; total {total_sin})"],
        conteos={"total_sin_aplica_a": total_sin, "por_tipo": {t: len(sin_apl[t]) for t in tipos}},
    )


def shape_s12(nodes, out_edges):
    sin_exc = []
    for n in nodes:
        if n["type"] == "Excepcion":
            if not any(norm(e["relation"]) in ("exceptua", "exceptua_obligacion") for e in out_edges[n["id"]]):
                sin_exc.append(n["id"])
    return _res(
        "S12", "ERROR — Toda Excepcion tiene >=1 arista saliente exceptua o exceptua_obligacion.",
        "PASS" if not sin_exc else "FAIL",
        f"{len(sin_exc)} Excepciones sin salida exceptua/exceptua_obligacion.",
        [f"    - {i}" for i in sin_exc],
        conteos={"excepciones_sin_salida": len(sin_exc)},
    )


def shape_s15(nodes, edges, node_by_id, excepciones_ruta):
    # Todo rol tiene miembro_de no vacío O figura en la lista declarada de
    # roles sin miembro adjudicable; los miembros son clases del árbol; y el
    # validador REPORTA la lista con su cuenta.
    decl_ids, decl_total, decl_causa, decl_defecto = cargar_excepciones_s15(excepciones_ruta)

    roles = [n for n in nodes if (n.get("properties") or {}).get("nivel") == "rol"]
    miembros_de = defaultdict(list)
    for e in edges:
        if norm(e["relation"]) == "miembro_de":
            miembros_de[e["target"]].append(e["source"])

    huerfanos = sorted(r["id"] for r in roles if not miembros_de.get(r["id"]))
    no_declarados = [r for r in huerfanos if r not in decl_ids]
    declarados_con_miembro = sorted(i for i in decl_ids if miembros_de.get(i))

    # Segunda cláusula: el miembro es una clase del árbol. Sobre el grafo
    # vigente los 17 miembros son de nivel 'clase' (medido), y la adjudicación
    # de U-ESQ-V3 rechazó por laudo los candidatos de nivel instancia, así que
    # la regla describe lo que el grafo efectivamente tiene.
    miembros_no_clase = []
    for rol_id, ms in sorted(miembros_de.items()):
        for m in ms:
            n = node_by_id.get(m)
            niv = (n.get("properties") or {}).get("nivel") if n else None
            if niv != "clase":
                miembros_no_clase.append(
                    f"{m} --miembro_de--> {rol_id} (nivel del miembro: {niv or 'inexistente'})")

    cuenta_ok = (decl_total == len(huerfanos)) if excepciones_ruta else True

    viol_s15 = []
    if decl_defecto:
        viol_s15.append(f"lista de excepciones inválida: {decl_defecto}")
    viol_s15 += [f"rol huérfano NO declarado: {i}" for i in no_declarados]
    viol_s15 += [f"miembro que no es clase del árbol: {x}" for x in miembros_no_clase]
    if not cuenta_ok:
        viol_s15.append(
            f"la cuenta declarada ({decl_total}) no coincide con la medida "
            f"({len(huerfanos)} roles huérfanos en el grafo)")

    detalle_s15 = list(viol_s15)
    if decl_ids:
        detalle_s15.append("")
        detalle_s15.append(f"Lista declarada ({decl_total} roles"
                           + (f"; por causa: {decl_causa}" if decl_causa else "") + "):")
        detalle_s15 += [f"    - {i}" + ("  [YA TIENE MIEMBRO: declaración obsoleta]"
                                        if i in declarados_con_miembro else "")
                        for i in sorted(decl_ids)]

    return _res(
        "S15",
        "ERROR — Todo rol tiene miembro_de no vacío O figura en la lista declarada de roles sin "
        "miembro adjudicable; los miembros son clases del árbol; la cuenta declarada coincide "
        "con la medida.",
        "PASS" if not viol_s15 else "FAIL",
        f"{len(roles)} roles, {sum(len(v) for v in miembros_de.values())} aristas miembro_de; "
        f"{len(huerfanos)} huérfanos ({len(huerfanos) - len(no_declarados)} declarados, "
        f"{len(no_declarados)} sin declarar); {len(miembros_no_clase)} miembros que no son clase."
        + (f" Lista declarada: {decl_total}" + (f" ({decl_causa})" if decl_causa else "") + "."
           if excepciones_ruta else " Sin lista declarada (--excepciones no fue pasada)."),
        detalle_s15,
        conteos={
            "roles": len(roles),
            "aristas_miembro_de": sum(len(v) for v in miembros_de.values()),
            "huerfanos": len(huerfanos),
            "huerfanos_declarados": len(huerfanos) - len(no_declarados),
            "huerfanos_sin_declarar": len(no_declarados),
            "miembros_no_clase": len(miembros_no_clase),
            "lista_declarada_total": decl_total if excepciones_ruta else None,
            "cuenta_coincide": cuenta_ok,
            "lista_defecto": decl_defecto,
        },
    )


# ---------------------------------------------------------------------------
# Shapes propias del perfil congelado
# ---------------------------------------------------------------------------
def shape_s1_congelado(edges, vocab):
    admitidas = set(vocab["predicates"]) | set(RELACIONES_ESQUELETO) | {RELACION_PADRE_SUGERIDO}
    viol = [f"idx {i}: relation='{e['relation']}'"
            for i, e in enumerate(edges) if norm(e["relation"]) not in admitidas]
    return _res(
        "S1",
        f"Toda arista usa una relación admitida por el perfil congelado: los "
        f"{len(vocab['predicates'])} predicados de PREDICATES_CONGELADO ∪ las "
        f"{len(RELACIONES_ESQUELETO)} de esqueleto ({'/'.join(RELACIONES_ESQUELETO)}) ∪ "
        f"{RELACION_PADRE_SUGERIDO} (nombre normalizado).",
        "PASS" if not viol else "FAIL",
        f"{len(edges) - len(viol)}/{len(edges)} aristas con relación admitida ({len(admitidas)} "
        f"relaciones admitidas); {len(viol)} violaciones.",
        viol,
        conteos={"aristas": len(edges), "violaciones": len(viol),
                 "relaciones_admitidas": len(admitidas)},
    )


def shape_s3_congelado(edges, node_by_id, vocab):
    dr = vocab["domain_range"]
    viol = []
    n_ref_cruzada = n_esq = n_padre = n_matriz = 0
    for i, e in enumerate(edges):
        rel = norm(e["relation"])
        if e["source"] not in node_by_id or e["target"] not in node_by_id:
            continue  # capturado por S2
        sn, tn = node_by_id[e["source"]], node_by_id[e["target"]]
        st, dt = sn["type"], tn["type"]
        if rel in dr:
            if rel == "referencia" and e.get("rol_fuente") == ROL_FUENTE_REFERENCIA_CRUZADA:
                n_ref_cruzada += 1
                continue  # referencia nodo→nodo admitida por rol_fuente
            n_matriz += 1
            dominios, rangos = dr[rel]
            ok = st in dominios and dt in rangos
            etiqueta = "matriz congelada"
        elif rel in RELACIONES_ESQUELETO:
            n_esq += 1
            ok = st == "Sujeto" and dt == "Sujeto"
            etiqueta = "esqueleto solo Sujeto->Sujeto"
        elif rel == RELACION_PADRE_SUGERIDO:
            n_padre += 1
            ok = (st == "Sujeto" and dt == "Sujeto"
                  and nivel_de(sn) == "propuesto" and nivel_de(tn) in NIVELES_PADRE)
            etiqueta = "padre_sugerido solo propuesto->clase|rol"
        else:
            continue  # capturado por S1
        if not ok:
            viol.append(
                f"idx {i}: {rel} {st}[{nivel_de(sn) or '-'}] -> {dt}[{nivel_de(tn) or '-'}] "
                f"({e['source']} -> {e['target']}; rol_fuente={e.get('rol_fuente')!r}; {etiqueta})")
    return _res(
        "S3",
        "Toda arista respeta las firmas del perfil congelado: DOMAIN_RANGE_CONGELADO (Sujeto como "
        "pseudo-tipo) ∪ esqueleto solo Sujeto->Sujeto ∪ referencia nodo->nodo solo si "
        "rol_fuente=referencia_cruzada ∪ padre_sugerido solo de Sujeto propuesto a Sujeto "
        "clase|rol. La referencia TextoOrdenado->Comunicacion sigue por la matriz.",
        "PASS" if not viol else "FAIL",
        f"{len(edges) - len(viol)}/{len(edges)} aristas conformes a firma; {len(viol)} violaciones. "
        f"Evaluadas: {n_matriz} por matriz, {n_esq} de esqueleto, {n_padre} padre_sugerido; "
        f"{n_ref_cruzada} referencias nodo->nodo admitidas por rol_fuente.",
        viol,
        conteos={"aristas": len(edges), "violaciones": len(viol),
                 "evaluadas_matriz": n_matriz, "evaluadas_esqueleto": n_esq,
                 "evaluadas_padre_sugerido": n_padre,
                 "referencias_cruzadas_admitidas": n_ref_cruzada},
    )


def shape_s4_congelado(nodes, edges):
    viol = []
    nodos_ok = 0
    for n in nodes:
        d = check_provenance_g3(n.get("provenance"), n.get("provenances"))
        if d:
            viol.append(f"nodo {n['id']}: {'; '.join(d)}")
        else:
            nodos_ok += 1
    aristas_ok = 0
    for i, e in enumerate(edges):
        d = check_provenance_g3(e.get("provenance"), e.get("provenances"))
        if d:
            viol.append(f"arista idx {i} ({e['relation']} {e['source']} -> {e['target']}): {'; '.join(d)}")
        else:
            aristas_ok += 1
    return _res(
        "S4",
        "Todo nodo y toda arista tienen provenance dict con al menos {to, archivo, punto, "
        "rol_documental}, provenances lista no vacía con provenance == provenances[0]; para "
        "rol_documental distinto de esqueleto, to y archivo no vacíos (para esqueleto se "
        "admiten to nulo, chunk_id nulo y paginas vacía).",
        "PASS" if not viol else "FAIL",
        f"Nodos OK: {nodos_ok}/{len(nodes)}. Aristas OK: {aristas_ok}/{len(edges)}. Violaciones: {len(viol)}.",
        viol,
        conteos={"nodos_ok": nodos_ok, "nodos": len(nodes), "aristas_ok": aristas_ok,
                 "aristas": len(edges), "violaciones": len(viol)},
    )


def _punto_ok(prov):
    if not isinstance(prov, dict):
        return False
    p = prov.get("punto")
    return isinstance(p, str) and bool(p.strip())


def shape_s5_congelado(nodes, edges):
    viol = []
    n_nodos = n_aristas = 0
    for n in nodes:
        if _punto_ok(n.get("provenance")):
            n_nodos += 1
        else:
            viol.append(f"nodo {n['id']}: punto={(n.get('provenance') or {}).get('punto') if isinstance(n.get('provenance'), dict) else None!r}")
    for i, e in enumerate(edges):
        if _punto_ok(e.get("provenance")):
            n_aristas += 1
        else:
            viol.append(f"arista idx {i} ({e['relation']}): punto={(e.get('provenance') or {}).get('punto') if isinstance(e.get('provenance'), dict) else None!r}")
    return _res(
        "S5", "Todo provenance.punto (de nodo y de arista) es una string no vacía.",
        "PASS" if not viol else "FAIL",
        f"Nodos con punto: {n_nodos}/{len(nodes)}. Aristas: {n_aristas}/{len(edges)}. Violaciones: {len(viol)}.",
        viol,
        conteos={"nodos_con_punto": n_nodos, "nodos": len(nodes),
                 "aristas_con_punto": n_aristas, "aristas": len(edges), "violaciones": len(viol)},
    )


def shape_s6_congelado(nodes, edges):
    archivos_to = {(n.get("properties") or {}).get("archivo") for n in nodes if n["type"] == "TextoOrdenado"}
    archivos_to = {a for a in archivos_to if isinstance(a, str) and a}
    archivos_esq = set()
    for x in list(nodes) + list(edges):
        for p in (x.get("provenances") or []):
            if isinstance(p, dict) and p.get("rol_documental") == ROL_DOCUMENTAL_ESQUELETO:
                a = p.get("archivo")
                if isinstance(a, str) and a:
                    archivos_esq.add(a)
    archivos = archivos_to | archivos_esq
    viol = []
    for n in nodes:
        prov = n.get("provenance")
        a = prov.get("archivo") if isinstance(prov, dict) else None
        if a not in archivos:
            viol.append(f"nodo {n['id']}: archivo={a!r}")
    for i, e in enumerate(edges):
        prov = e.get("provenance")
        a = prov.get("archivo") if isinstance(prov, dict) else None
        if a not in archivos:
            viol.append(f"arista idx {i} ({e['relation']}): archivo={a!r}")
    return _res(
        "S6",
        "Todo provenance.archivo pertenece a {properties.archivo de los nodos TextoOrdenado} ∪ "
        "{archivo de las provenances con rol_documental=esqueleto}; nada codificado a mano.",
        "PASS" if not viol else "FAIL",
        f"Archivos válidos ({len(archivos)}): TextoOrdenado {sorted(archivos_to)} ∪ esqueleto "
        f"{sorted(archivos_esq - archivos_to)}. Violaciones: {len(viol)}.",
        viol,
        conteos={"archivos_validos": len(archivos), "archivos_texto_ordenado": len(archivos_to),
                 "archivos_esqueleto_adicionales": len(archivos_esq - archivos_to),
                 "violaciones": len(viol)},
    )


def shape_s19_catalogo(nodes, catalogo_ids, defecto_catalogo):
    sujetos = [n for n in nodes if n["type"] == "Sujeto"]
    por_nivel = Counter()
    viol = []
    fuera = nivel_invalido = incompletos = 0
    if defecto_catalogo:
        viol.append(f"catálogo inválido: {defecto_catalogo}")
    for n in sujetos:
        props = n.get("properties") or {}
        niv = props.get("nivel")
        por_nivel[niv if niv in NIVELES_SUJETO else "invalido"] += 1
        if niv not in NIVELES_SUJETO:
            nivel_invalido += 1
            viol.append(f"{n['id']}: nivel={niv!r} no está en {list(NIVELES_SUJETO)}")
            continue
        if niv != "propuesto":
            if n["id"] not in catalogo_ids:
                fuera += 1
                viol.append(f"{n['id']} (nivel {niv}): id fuera del catálogo")
        else:
            faltan = [k for k in ("cuarentena", "padre_sugerido") if not props.get(k)]
            if faltan:
                incompletos += 1
                viol.append(f"{n['id']} (propuesto): sin properties.{' ni properties.'.join(faltan)}")
    return _res(
        "S19",
        "ERROR — Catálogo de sujetos: todo Sujeto tiene nivel ∈ {clase, instancia, rol, propuesto}; "
        "si nivel ≠ propuesto, su id está en el catálogo (clases ∪ roles) del artefacto de "
        "--excepciones; si nivel = propuesto, tiene properties.cuarentena y properties.padre_sugerido.",
        "PASS" if not viol else "FAIL",
        f"{len(sujetos)} Sujetos ({dict(sorted(por_nivel.items(), key=lambda kv: str(kv[0])))}); "
        f"catálogo de {len(catalogo_ids)} ids; {fuera} fuera del catálogo, {nivel_invalido} con nivel "
        f"inválido, {incompletos} propuestos incompletos"
        + (f"; catálogo inválido: {defecto_catalogo}" if defecto_catalogo else "") + ".",
        viol,
        conteos={"sujetos": len(sujetos), "por_nivel": dict(por_nivel), "catalogo_ids": len(catalogo_ids),
                 "fuera_de_catalogo": fuera, "nivel_invalido": nivel_invalido,
                 "propuestos_incompletos": incompletos, "catalogo_defecto": defecto_catalogo},
    )


def shape_s20_enum(nodes, vocab):
    enum = tuple(vocab["obligacion_tipo"])
    retirados = set(vocab["retirados"])
    c_ret, c_otros = Counter(), Counter()
    viol = []
    obligaciones = [n for n in nodes if n["type"] == "Obligacion"]
    for n in obligaciones:
        tipo = (n.get("properties") or {}).get("tipo")
        if tipo in enum:
            continue
        if tipo in retirados:
            c_ret[tipo] += 1
            viol.append(f"nodo {n['id']}: tipo={tipo!r} (valor RETIRADO del enum)")
        else:
            # clave como str plano (None -> 'None'): sin comillas anidadas al
            # imprimir el Counter en el resumen y en el .json.
            c_otros[str(tipo)] += 1
            viol.append(f"nodo {n['id']}: tipo={tipo!r} (fuera del enum)")
    n_ret, n_otros = sum(c_ret.values()), sum(c_otros.values())
    return _res(
        "S20",
        f"ERROR — Enum de Obligacion.tipo: para todo nodo Obligacion, properties.tipo ∈ "
        f"{{{'|'.join(enum)}}}. Valores retirados ({', '.join(sorted(retirados))}) y otros valores "
        f"fuera del enum se cuentan por separado; bloqueante si cualquiera de los dos es distinto de 0.",
        "PASS" if not viol else "FAIL",
        f"{len(obligaciones) - len(viol)}/{len(obligaciones)} Obligaciones con tipo en el enum. "
        f"Valores retirados: {n_ret} ({dict(c_ret)}). Otros valores fuera del enum: {n_otros} ({dict(c_otros)}).",
        viol,
        conteos={"obligaciones": len(obligaciones), "en_enum": len(obligaciones) - len(viol),
                 "retirados": {"total": n_ret, "por_valor": dict(c_ret)},
                 "otros_fuera_del_enum": {"total": n_otros, "por_valor": dict(c_otros)}},
    )


def shape_s21_referencias(edges, node_by_id, perfil="congelado"):
    total_via, incoh_via = Counter(), Counter()
    n_refs = 0
    viol = []
    for i, e in enumerate(edges):
        # remisión en cualquiera de sus dos formas (enmienda 1, R5.c); en los
        # grafos del perfil congelado solo existe la de referencia_cruzada
        if not remisiones.es_remision(e):
            continue
        n_refs += 1
        props = e.get("properties") or {}
        via = props.get("via") if perfil == "congelado" else props.get("alcance")
        destino = props.get("destino")
        total_via[via] += 1
        punto = destino_sin_prefijo(destino)
        tn = node_by_id.get(e["target"])
        puntos = {p.get("punto") for p in ((tn or {}).get("provenances") or []) if isinstance(p, dict)}
        if punto not in puntos:
            incoh_via[via] += 1
            muestra = sorted(str(p) for p in puntos)
            viol.append(
                f"idx {i}: {e['source']} -> {e['target']} destino={destino!r} via={via!r}: "
                f"punto {punto!r} ∉ puntos del destino {muestra[:5]}{'...' if len(muestra) > 5 else ''}")
    n_incoh = sum(incoh_via.values())
    if perfil == "r2":
        return _res(
            "S21",
            "INFORMATIVA — Coherencia de remisiones entre puntos (remite_a o referencia con "
            "rol_fuente=referencia_cruzada; scripts/remisiones.py): properties.destino sin el prefijo "
            "<to>:: pertenece al CONJUNTO {p.punto for p in provenances} del nodo destino; desglose por "
            "properties.alcance (las de alcance to_entero apuntan al TextoOrdenado y se cuentan como incoherentes "
            "por construcción del enunciado).",
            "PASS" if not viol else "WARN",
            f"{n_refs} remisiones ({dict(total_via)}); {n_incoh} incoherentes (por alcance: {dict(incoh_via)}).",
            viol,
            conteos={"remisiones": n_refs, "por_alcance": dict(total_via),
                     "incoherentes": n_incoh, "incoherentes_por_alcance": dict(incoh_via)},
        )
    return _res(
        "S21",
        "INFORMATIVA — Coherencia de referencias nodo->nodo (rol_fuente=referencia_cruzada): "
        "properties.destino sin el prefijo <to>:: pertenece al CONJUNTO {p.punto for p in provenances} "
        "del nodo destino (nunca solo provenance[0]); desglose por properties.via.",
        "PASS" if not viol else "WARN",
        f"{n_refs} referencias nodo->nodo ({dict(total_via)}); {n_incoh} incoherentes "
        f"(por via: {dict(incoh_via)}).",
        viol,
        conteos={"referencias_cruzadas": n_refs, "por_via": dict(total_via),
                 "incoherentes": n_incoh, "incoherentes_por_via": dict(incoh_via)},
    )


def shape_s22_padre_sugerido(edges, node_by_id):
    n_ps = destino_distinto = sin_cuarentena = 0
    viol = []
    for i, e in enumerate(edges):
        if norm(e["relation"]) != RELACION_PADRE_SUGERIDO:
            continue
        n_ps += 1
        sn = node_by_id.get(e["source"])
        props = (sn or {}).get("properties") or {}
        problemas = []
        if e["target"] != props.get("padre_sugerido"):
            destino_distinto += 1
            problemas.append(f"destino ≠ properties.padre_sugerido del origen ({props.get('padre_sugerido')!r})")
        if not en_cuarentena(props):
            sin_cuarentena += 1
            problemas.append(f"origen no está en cuarentena (cuarentena={props.get('cuarentena')!r})")
        if problemas:
            viol.append(f"idx {i}: {e['source']} -> {e['target']}: {'; '.join(problemas)}")
    return _res(
        "S22",
        "INFORMATIVA — Coherencia de padre_sugerido: el destino de la arista es "
        "properties.padre_sugerido del origen y el origen está en cuarentena.",
        "PASS" if not viol else "WARN",
        f"{n_ps} aristas padre_sugerido; {len(viol)} incoherentes ({destino_distinto} con destino "
        f"distinto, {sin_cuarentena} con origen fuera de cuarentena).",
        viol,
        conteos={"aristas_padre_sugerido": n_ps, "incoherentes": len(viol),
                 "destino_distinto": destino_distinto, "origen_sin_cuarentena": sin_cuarentena},
    )


def shape_s23_aplica_a_cuarentena(edges, node_by_id):
    n_aplica = 0
    hacia = []
    destinos = Counter()
    for i, e in enumerate(edges):
        if norm(e["relation"]) != "aplica_a":
            continue
        n_aplica += 1
        tn = node_by_id.get(e["target"])
        if tn and tn["type"] == "Sujeto" and nivel_de(tn) == "propuesto":
            destinos[e["target"]] += 1
            hacia.append(f"idx {i}: {e['source']} -> {e['target']}")
    return _res(
        "S23",
        "INFORMATIVA — aplica_a hacia sujetos en cuarentena: aristas aplica_a cuyo destino es un "
        "Sujeto de nivel propuesto (conteo; nunca bloqueante).",
        "PASS" if not hacia else "WARN",
        f"{n_aplica} aristas aplica_a; {len(hacia)} hacia Sujetos propuestos "
        f"({len(destinos)} destinos distintos).",
        hacia,
        conteos={"aplica_a": n_aplica, "hacia_propuestos": len(hacia),
                 "destinos_distintos": len(destinos)},
    )


def evaluar_perfil_congelado(g, vocab, excepciones_ruta):
    """Evalúa el grafo `g` bajo el perfil congelado. Devuelve
    (resultados ordenados por ORDEN_SHAPES_CONGELADO, veredicto, meta)."""
    nodes, edges = g["nodes"], g["edges"]
    node_by_id = {n["id"]: n for n in nodes}
    out_edges = defaultdict(list)
    for e in edges:
        out_edges[e["source"]].append(e)

    catalogo_ids, n_clases, n_roles, defecto_cat = cargar_catalogo_sujetos(excepciones_ruta)
    dom_est = tuple(sorted(vocab["domain_range"]["establecida_en"][0]))
    dom_apl = tuple(sorted(vocab["domain_range"]["aplica_a"][0]))

    lista = [
        shape_s1_congelado(edges, vocab),
        shape_s2(edges, node_by_id),
        shape_s3_congelado(edges, node_by_id, vocab),
        shape_s4_congelado(nodes, edges),
        shape_s5_congelado(nodes, edges),
        shape_s6_congelado(nodes, edges),
        shape_s15(nodes, edges, node_by_id, excepciones_ruta),
        shape_s19_catalogo(nodes, catalogo_ids, defecto_cat),
        shape_s20_enum(nodes, vocab),
        shape_s7(nodes),
        shape_s8(nodes),
        shape_s9(nodes),
        shape_s10(nodes, out_edges, tipos=dom_est,
                  enunciado=f"ERROR — Todo nodo del dominio congelado de establecida_en "
                            f"({'/'.join(dom_est)}) tiene >=1 arista saliente establecida_en."),
        shape_s11(nodes, out_edges, tipos=dom_apl,
                  enunciado=f"WARN — Todo nodo del dominio congelado de aplica_a "
                            f"({'/'.join(dom_apl)}) tiene >=1 arista saliente aplica_a."),
        shape_s12(nodes, out_edges),
        shape_s21_referencias(edges, node_by_id),
        shape_s22_padre_sugerido(edges, node_by_id),
        shape_s23_aplica_a_cuarentena(edges, node_by_id),
    ]
    resultados = {r["rid"]: r for r in lista}
    assert list(resultados) == ORDEN_SHAPES_CONGELADO, "orden de shapes del perfil roto"
    bloqueantes_fail = [rid for rid in BLOQUEANTES_CONGELADO if resultados[rid]["result"] != "PASS"]
    veredicto = "PASA" if not bloqueantes_fail else "NO PASA"
    meta = {
        "catalogo": {"ruta": excepciones_ruta, "n_ids": len(catalogo_ids),
                     "n_clases": n_clases, "n_roles": n_roles, "defecto": defecto_cat},
        "bloqueantes_en_fail": bloqueantes_fail,
    }
    return resultados, veredicto, meta


def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Perfil «r2» (U-R2-CODIGO, R5.b; enmienda 1, R5.c)
# ---------------------------------------------------------------------------
def _marcas_nodo_r2(ruta=RUTA_MODELOS_R2):
    """MARCAS_NODO de modelos_r2.py, leída del fuente con ast (sin importar
    Pydantic): tupla literal asignada al nombre MARCAS_NODO."""
    with open(ruta, encoding="utf-8") as f:
        arbol = ast.parse(f.read())
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MARCAS_NODO" for t in nodo.targets):
            return tuple(ast.literal_eval(nodo.value))
    raise VocabularioCongeladoError(f"{ruta} no declara MARCAS_NODO como literal")


def cargar_vocabulario_r2(ruta=RUTA_ENUMS_R2, sha_esperado=SHA256_ENUMS_R2_ESPERADO):
    """Lee enums_r2.json con candado de sha256 (FRENA con CandadoShaError si no
    coincide) y devuelve el vocabulario del perfil r2."""
    if not os.path.isfile(ruta):
        raise VocabularioCongeladoError(f"no existe {ruta}")
    sha = sha256_archivo(ruta)
    if sha != sha_esperado:
        raise CandadoShaError(f"candado del sha: {ruta} tiene sha256 {sha}, esperado {sha_esperado} — se frena")
    with open(ruta, encoding="utf-8") as f:
        d = json.load(f)
    if d.get("perfil") != "r2":
        raise VocabularioCongeladoError(f"{ruta} no es del perfil r2 (perfil={d.get('perfil')!r})")
    firmas = {p: (set(dr[0]), set(dr[1])) for p, dr in d["firmas_r2"].items()}
    return {
        "modulo": ruta, "sha256": sha,
        "entity_types": tuple(d["tipo_entidad"]), "predicates": tuple(d["predicado"]),
        "domain_range": firmas, "ampliacion": [tuple(x) for x in d.get("ampliacion_r2") or []],
        "claves_por_tipo": {t: tuple(v) for t, v in d["claves_por_tipo"].items()},
        "marcas_nodo": _marcas_nodo_r2(),
        "predicados_sujeto": tuple(d["predicados_sujeto"]),
        "tipos_con_umbrales": tuple(d["tipos_con_umbrales"]),     # S32 (U-REEXT-T0, T1, punto 4.b)
        # listas cerradas de valores: «Tipo.campo», «umbral.campo», «omision.campo» y las marcas
        # (mencion_verificada, tramo_verificado, coherencia_tipo_predicado)
        "enums": {k: tuple(v) for k, v in d.items() if isinstance(v, list) and k not in (
            "tipo_entidad", "predicado", "predicados_sujeto", "ampliacion_r2", "tipos_con_umbrales",
            "sujeto_id", "sujeto_lapidas")},
        "catalogo_r2": d.get("catalogo_r2"),
    }


def cargar_ids_s19_r2(ruta=RUTA_IDS_S19_R2):
    try:
        with open(ruta, encoding="utf-8") as f:
            ids = json.load(f)
    except Exception as e:  # noqa: BLE001
        return set(), f"no se pudo leer {ruta}: {e}"
    if not isinstance(ids, list):
        return set(), f"{ruta} no es una lista de ids"
    return set(ids), None


def shape_s1_r2(edges, vocab):
    admitidas = (set(vocab["predicates"]) | {remisiones.PREDICADO_REMISION} | set(RELACIONES_ESQUELETO)
                 | {RELACION_PADRE_SUGERIDO})
    viol = [f"idx {i}: relation='{e['relation']}'" for i, e in enumerate(edges) if norm(e["relation"]) not in admitidas]
    return _res(
        "S1",
        f"Toda arista usa una relación admitida por el perfil r2: los {len(vocab['predicates'])} predicados de "
        f"enums_r2.json ∪ remite_a (enmienda 2 de L-ESQ-R2) ∪ las {len(RELACIONES_ESQUELETO)} de esqueleto ∪ "
        f"{RELACION_PADRE_SUGERIDO}.",
        "PASS" if not viol else "FAIL",
        f"{len(edges) - len(viol)}/{len(edges)} aristas con relación admitida ({len(admitidas)} relaciones "
        f"admitidas); {len(viol)} violaciones.",
        viol, conteos={"aristas": len(edges), "violaciones": len(viol), "relaciones_admitidas": len(admitidas)})


def shape_s3_r2(edges, node_by_id, vocab):
    dr = vocab["domain_range"]
    viol = []
    c = Counter()
    for i, e in enumerate(edges):
        rel = norm(e["relation"])
        if e["source"] not in node_by_id or e["target"] not in node_by_id:
            continue  # capturado por S2
        sn, tn = node_by_id[e["source"]], node_by_id[e["target"]]
        st, dt = sn["type"], tn["type"]
        if rel == remisiones.PREDICADO_REMISION:
            c["remite_a"] += 1
            ok, etiqueta = remisiones.firma_remite_a_ok(st, dt), "firma de remite_a (enmienda 2, §2)"
        elif rel in dr:
            c["matriz"] += 1
            dominios, rangos = dr[rel]
            ok, etiqueta = st in dominios and dt in rangos, "matriz r2"
            if rel == "referencia" and not ok:
                etiqueta = "referencia solo TextoOrdenado->Comunicacion (con o sin rol_fuente)"
        elif rel in RELACIONES_ESQUELETO:
            c["esqueleto"] += 1
            ok, etiqueta = st == "Sujeto" and dt == "Sujeto", "esqueleto solo Sujeto->Sujeto"
        elif rel == RELACION_PADRE_SUGERIDO:
            c["padre_sugerido"] += 1
            ok = (st == "Sujeto" and dt == "Sujeto" and nivel_de(sn) == "propuesto" and nivel_de(tn) in NIVELES_PADRE)
            etiqueta = "padre_sugerido solo propuesto->clase|rol"
        else:
            continue  # capturado por S1
        if not ok:
            c["violaciones_" + ("remite_a" if rel == remisiones.PREDICADO_REMISION else rel)] += 1
            viol.append(f"idx {i}: {rel} {st}[{nivel_de(sn) or '-'}] -> {dt}[{nivel_de(tn) or '-'}] "
                        f"({e['source']} -> {e['target']}; rol_fuente={e.get('rol_fuente')!r}; {etiqueta})")
    return _res(
        "S3",
        "Toda arista respeta las firmas del perfil r2: matriz ampliada de enums_r2.json (firmas_r2, con "
        "condicion_de -> Operacion|Potestad) ∪ remite_a con origen en los siete tipos de contenido y destino en "
        "esos siete o TextoOrdenado ∪ esqueleto solo Sujeto->Sujeto ∪ padre_sugerido solo de Sujeto propuesto a "
        "Sujeto clase|rol. Una referencia con origen distinto de TextoOrdenado es violación, con o sin rol_fuente.",
        "PASS" if not viol else "FAIL",
        f"{len(edges) - len(viol)}/{len(edges)} aristas conformes a firma; {len(viol)} violaciones. Evaluadas: "
        f"{c['matriz']} por matriz, {c['remite_a']} remite_a, {c['esqueleto']} de esqueleto, "
        f"{c['padre_sugerido']} padre_sugerido.",
        viol, conteos=dict(c, aristas=len(edges), violaciones=len(viol)))


def _shape_enum(rid, tipo, campo, nodes, vocab, enunciado):
    lista = vocab["enums"].get(f"{tipo}.{campo}") or ()
    viol, marcados, sin_valor = [], Counter(), 0
    evaluados = [n for n in nodes if n["type"] == tipo]
    for n in evaluados:
        v = (n.get("properties") or {}).get(campo)
        fl = n.get("fuera_de_lista") or []
        if v is None:
            sin_valor += 1
            continue
        if v in lista and campo in fl:
            viol.append(f"nodo {n['id']}: {campo}={v!r} está en la lista y lleva la marca fuera_de_lista")
        elif v not in lista and campo not in fl:
            viol.append(f"nodo {n['id']}: {campo}={v!r} fuera de la lista y sin la marca fuera_de_lista")
        elif v not in lista:
            marcados[str(v)] += 1
    return _res(
        rid, enunciado + f" Lista: {{{'|'.join(lista)}}}.",
        "PASS" if not viol else "FAIL",
        f"{len(evaluados)} nodos {tipo}; {len(viol)} violaciones; fuera de lista con marca: "
        f"{sum(marcados.values())} {dict(marcados)}; sin valor: {sin_valor}.",
        viol, conteos={"nodos": len(evaluados), "violaciones": len(viol), "marcados": dict(marcados),
                       "sin_valor": sin_valor, "lista": list(lista)})


def shape_s18_r2(nodes):
    viol, con_lista, con_marca, no_cuantificable = [], 0, 0, []
    lq = [n for n in nodes if n["type"] == "Restriccion" and (n.get("properties") or {}).get("tipo") == "limite_cuantitativo"]
    for n in lq:
        lista = (n.get("properties") or {}).get("umbrales")
        nd = n.get("properties_no_definidas") or {}
        if isinstance(lista, list) and lista:
            con_lista += 1
        elif "umbral" in (n.get("campos_heredados_v3") or {}) or "umbral" in nd:
            con_marca += 1
        elif nd.get("umbral_no_cuantificable") is True:
            # T3-bis de U-REEXT-T0, decisión 3: la marca r2b del ensamblado cuenta como umbral guardado sin lista.
            con_marca += 1
            no_cuantificable.append(f"{n['id']} ({nd.get('umbral_no_cuantificable_motivo')})")
        else:
            viol.append(f"nodo {n['id']}: limite_cuantitativo sin lista de umbrales ni umbral guardado "
                        f"(descripcion={((n.get('properties') or {}).get('descripcion') or '')[:90]!r})")
    return _res(
        "S18", "ERROR — " + NUMERACION_PERFIL_R2["S18"],
        "PASS" if not viol else "FAIL",
        f"{len(lq)} Restricciones limite_cuantitativo: {con_lista} con lista, {con_marca} con el umbral guardado "
        f"sin lista (marca), {len(viol)} sin ninguna.",
        viol, conteos={"limite_cuantitativo": len(lq), "con_lista": con_lista, "con_marca": con_marca,
                       "sin_lista_ni_marca": len(viol), "con_marca_umbral_no_cuantificable": len(no_cuantificable),
                       "marcados_umbral_no_cuantificable": no_cuantificable})


def shape_s26_claves(nodes, vocab):
    claves = {t: set(v) | set(vocab["marcas_nodo"]) for t, v in vocab["claves_por_tipo"].items()}
    viol, n_eval, por_clave = [], 0, Counter()
    for n in nodes:
        t = n["type"]
        if t not in claves:
            continue
        n_eval += 1
        for k in (n.get("properties") or {}):
            if k not in claves[t]:
                por_clave[f"{t}.{k}"] += 1
                viol.append(f"nodo {n['id']}: clave {k!r} fuera de la definición de {t}")
        for k in (n.get("properties_no_definidas") or {}):
            if k in claves[t]:
                por_clave[f"{t}.{k} (definida como no definida)"] += 1
                viol.append(f"nodo {n['id']}: clave definida {k!r} figura en properties_no_definidas")
    return _res(
        "S26", "ERROR — Claves cerradas por tipo: las properties de cada nodo de los nueve tipos están en "
               "claves_por_tipo de enums_r2.json o en MARCAS_NODO de modelos_r2.py; lo demás vive en "
               "properties_no_definidas.",
        "PASS" if not viol else "FAIL",
        f"{n_eval} nodos evaluados; {len(viol)} violaciones {dict(por_clave)}; marcas de nodo admitidas: "
        f"{list(vocab['marcas_nodo'])}.",
        viol, conteos={"nodos": n_eval, "violaciones": len(viol), "por_clave": dict(por_clave)})


def shape_s27_mencion(edges, vocab, fase):
    preds = set(vocab["predicados_sujeto"])
    lista = vocab["enums"].get("mencion_verificada") or ()
    es = [e for e in edges if norm(e["relation"]) in preds and e.get("rol_fuente") != ROL_DOCUMENTAL_ESQUELETO]
    viol = []
    c = Counter()
    for i, e in enumerate(edges):
        if not (norm(e["relation"]) in preds and e.get("rol_fuente") != ROL_DOCUMENTAL_ESQUELETO):
            continue
        falta = []
        if not (e.get("sujeto_mencion") or "").strip():
            falta.append("mención")
            c["sin_mencion"] += 1
        if e.get("mencion_verificada") not in lista:
            falta.append("mencion_verificada")
            c["sin_mencion_verificada"] += 1
        if not e.get("metodo_resolucion"):
            falta.append("metodo_resolucion")
            c["sin_metodo"] += 1
        if falta:
            viol.append(f"idx {i}: {e['relation']} {e['source']} -> {e['target']}: sin {', '.join(falta)}")
    bloqueante = fase == "r2b"
    return _res(
        "S27", ("ERROR — " if bloqueante else "INFORMATIVA — ") + NUMERACION_PERFIL_R2["S27"]
        + f" Fase: {fase}.",
        "PASS" if not viol else ("FAIL" if bloqueante else "WARN"),
        f"{len(es)} aristas de sujeto fuera del esqueleto; {len(viol)} sin mención, verificación o método "
        f"({dict(c)}).",
        viol, conteos=dict(c, aristas_de_sujeto=len(es), con_defecto=len(viol), fase=fase))


def shape_s28_registro(nodes, registro_ruta):
    propuestos = [n["id"] for n in nodes if n["type"] == "Sujeto" and nivel_de(n) == "propuesto"]
    if not registro_ruta or not os.path.isfile(registro_ruta):
        return _res("S28", "ERROR — " + NUMERACION_PERFIL_R2["S28"], NO_COMPUTABLE,
                    f"sin registro ({registro_ruta}): {len(propuestos)} Sujetos propuestos sin cotejar.", [],
                    conteos={"propuestos": len(propuestos), "registro": registro_ruta})
    with open(registro_ruta, encoding="utf-8") as f:
        filas = [json.loads(x) for x in f if x.strip()]
    con_fila = {r.get("id_nodo") for r in filas}
    viol = [f"{i}: Sujeto propuesto sin fila en {os.path.basename(registro_ruta)}" for i in propuestos if i not in con_fila]
    return _res(
        "S28", "ERROR — " + NUMERACION_PERFIL_R2["S28"],
        "PASS" if not viol else "FAIL",
        f"{len(propuestos)} Sujetos propuestos; {len(filas)} filas en el registro; {len(viol)} propuestos sin fila.",
        viol, conteos={"propuestos": len(propuestos), "filas": len(filas), "sin_fila": len(viol), "registro": registro_ruta})


def shape_s29_padre(edges, ids_cat, defecto):
    viol = [] if not defecto else [f"catálogo único inválido: {defecto}"]
    n = 0
    for i, e in enumerate(edges):
        if norm(e["relation"]) != RELACION_PADRE_SUGERIDO:
            continue
        n += 1
        if e["target"] not in ids_cat:
            viol.append(f"idx {i}: {e['source']} -> {e['target']}: destino fuera del catálogo único")
    return _res("S29", "ERROR — " + NUMERACION_PERFIL_R2["S29"], "PASS" if not viol else "FAIL",
                f"{n} aristas padre_sugerido; {len(viol)} con destino fuera del catálogo único ({len(ids_cat)} ids).",
                viol, conteos={"padre_sugerido": n, "violaciones": len(viol), "catalogo_ids": len(ids_cat)})


def shape_s30_alcance(edges, node_by_id):
    viol, c = [], Counter()
    for i, e in enumerate(edges):
        if norm(e["relation"]) != remisiones.PREDICADO_REMISION:
            continue
        p = e.get("properties") or {}
        alc, dest = p.get("alcance"), p.get("destino")
        c[str(alc)] += 1
        tn = node_by_id.get(e["target"]) or {}
        es_to = tn.get("type") == remisiones.TIPO_TEXTO_ORDENADO
        esperado = remisiones.alcance_esperado(dest, (e.get("provenance") or {}).get("to"), es_to)
        problemas = []
        if alc not in remisiones.ALCANCES:
            problemas.append(f"alcance={alc!r} fuera de {list(remisiones.ALCANCES)}")
        elif alc != esperado:
            problemas.append(f"alcance={alc!r} y los extremos dan {esperado!r}")
        if (alc == "to_entero") != (isinstance(dest, str) and dest.endswith("::TO")):
            problemas.append(f"to_entero sin destino <to>::TO (o al revés): destino={dest!r}")
        if problemas:
            viol.append(f"idx {i}: {e['source']} -> {e['target']}: {'; '.join(problemas)}")
    return _res("S30", "ERROR — " + NUMERACION_PERFIL_R2["S30"]
                + " Coherencia: to_entero si el destino es un TextoOrdenado (destino <to>::TO); si no, interna "
                  "cuando el TO de la unidad citada es el de la procedencia de la arista y externa cuando es otro "
                  "(enmienda 2 de L-ESQ-R2, §3).",
                "PASS" if not viol else "FAIL",
                f"{sum(c.values())} aristas remite_a ({dict(sorted(c.items()))}); {len(viol)} violaciones.",
                viol, conteos={"remite_a": sum(c.values()), "por_alcance": dict(sorted(c.items())), "violaciones": len(viol)})


def _tramos_de_chunk(ch):
    return [ch.get("texto") or ""] + [h.get("texto") or "" for h in (ch.get("herencia") or [])]


def shape_s31_evidencia(edges, e0_dir):
    rem = [(i, e) for i, e in enumerate(edges) if norm(e["relation"]) == remisiones.PREDICADO_REMISION]
    if not e0_dir or not os.path.isdir(e0_dir):
        return _res("S31", "ERROR — " + NUMERACION_PERFIL_R2["S31"], NO_COMPUTABLE,
                    f"sin directorio de E0 ({e0_dir}): {len(rem)} aristas remite_a sin cotejar.", [],
                    conteos={"remite_a": len(rem), "e0": e0_dir})
    cache = {}

    def chunk(pv):
        cid = (pv or {}).get("chunk_id")
        to = (pv or {}).get("to") or (cid.split("::", 1)[0] if isinstance(cid, str) and "::" in cid else None)
        if not to or not cid:
            return None
        if to not in cache:
            ruta = os.path.join(e0_dir, f"chunks_{to}.json")
            if os.path.isfile(ruta):
                with open(ruta, encoding="utf-8") as f:
                    d = json.load(f)
                cache[to] = {c.get("id"): c for c in (d["chunks"] if isinstance(d, dict) else d)}
            else:
                cache[to] = None
        return (cache[to] or {}).get(cid)

    viol, c = [], Counter()
    for i, e in rem:
        ev = (e.get("properties") or {}).get("evidencia") or ""
        pvs = [e.get("provenance")] + [p for p in (e.get("provenances") or []) if p != e.get("provenance")]
        ch0 = chunk(e.get("provenance"))
        if ch0 is not None and any(ev in t for t in _tramos_de_chunk(ch0)):
            c["en_un_tramo_del_chunk_de_la_arista"] += 1
            continue
        otra = next((p for p in pvs[1:] if (lambda ch: ch is not None and any(ev in t for t in _tramos_de_chunk(ch)))(chunk(p))), None)
        if otra is not None:
            c["en_un_tramo_de_otra_procedencia_de_la_arista"] += 1
            continue
        if ch0 is None:
            c["chunk_no_encontrado"] += 1
            viol.append(f"idx {i}: chunk {((e.get('provenance') or {}).get('chunk_id'))!r} no está en {e0_dir}")
        else:
            junto = "\n".join(_tramos_de_chunk(ch0))
            c["solo_en_la_union_de_tramos" if ev in junto else "fuera_del_texto"] += 1
            viol.append(f"idx {i}: evidencia {ev[:80]!r} no es subcadena de un único tramo de {ch0.get('id')!r}"
                        + (" (sí de la unión de tramos)" if ev in junto else ""))
    return _res("S31", "ERROR — " + NUMERACION_PERFIL_R2["S31"]
                + " Tramo = el texto propio del chunk o uno de sus tramos heredados, cada uno por separado; nunca la "
                  "concatenación. Si la evidencia no está en el chunk de provenance, se busca en las otras procedencias "
                  "de la arista (fusión).",
                "PASS" if not viol else "FAIL",
                f"{len(rem)} aristas remite_a: {dict(sorted(c.items()))}; {len(viol)} violaciones.",
                viol, conteos={"remite_a": len(rem), **dict(sorted(c.items())), "violaciones": len(viol), "e0": e0_dir})


def _reglas_comparacion(ruta=RUTA_REGLAS_COMPARACION):
    """reglas_comparacion.py del pipeline (pyd_r2/code), cargado del fuente sin bytecode (solo stdlib)."""
    nombre = "reglas_comparacion_s32"
    if nombre in sys.modules:
        return sys.modules[nombre]
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod      # dataclasses lo busca en sys.modules al definir Cuantia
    spec.loader.exec_module(mod)
    return mod


def shape_s32_cuantia(nodes, vocab, rc=None):
    """S32 (informativa): cuantía en la descripción => elemento en la lista de umbrales (o el umbral guardado como
    marca, como en S18). Por nodo, en los tipos de `tipos_con_umbrales`; aparte, por cuantía: las de la descripción
    sin un elemento de igual (valor, unidad) en la lista."""
    rc = rc or _reglas_comparacion()
    tipos = tuple(vocab["tipos_con_umbrales"])
    viol, por_tipo = [], Counter()
    con_cuantia = con_lista = con_marca = cuantias = sin_elemento = 0
    for n in nodes:
        if n["type"] not in tipos:
            continue
        props = n.get("properties") or {}
        cs = rc.detectar_cuantias(str(props.get("descripcion") or ""))
        if not cs:
            continue
        con_cuantia += 1
        lista = props.get("umbrales")
        valores = {(str(u.get("valor")), u.get("unidad")) for u in lista if isinstance(u, dict)} \
            if isinstance(lista, list) else set()
        cuantias += len(cs)
        sin_elemento += sum(1 for c in cs if (str(c.valor), c.unidad) not in valores)
        if isinstance(lista, list) and lista:
            con_lista += 1
        elif "umbral" in (n.get("campos_heredados_v3") or {}) or "umbral" in (n.get("properties_no_definidas") or {}):
            con_marca += 1
        else:
            por_tipo[n["type"]] += 1
            viol.append(f"nodo {n['id']}: {len(cs)} cuantía(s) en la descripción ({', '.join(c.texto for c in cs[:3])}) "
                        f"y lista vacía")
    return _res(
        "S32", "INFORMATIVA — " + NUMERACION_PERFIL_R2["S32"],
        "PASS" if not viol else "FAIL",
        f"{con_cuantia} nodos con cuantía en la descripción: {con_lista} con lista, {con_marca} con el umbral guardado "
        f"(marca), {len(viol)} sin ninguna {dict(sorted(por_tipo.items()))}; cuantías de la descripción {cuantias}, "
        f"sin elemento de igual valor y unidad {sin_elemento}.",
        viol, conteos={"nodos_con_cuantia": con_cuantia, "con_lista": con_lista, "con_marca": con_marca,
                       "sin_lista_ni_marca": len(viol), "sin_lista_por_tipo": dict(sorted(por_tipo.items())),
                       "cuantias_en_la_descripcion": cuantias, "cuantias_sin_elemento": sin_elemento,
                       "detector_sha256": sha256_archivo(RUTA_REGLAS_COMPARACION)})


def evaluar_perfil_r2(g, vocab, fase, registro_ruta, e0_dir, ids_s19_ruta=RUTA_IDS_S19_R2,
                      excepciones_ruta=RUTA_EXCEPCIONES_S15_R2):
    nodes, edges = g["nodes"], g["edges"]
    node_by_id = {n["id"]: n for n in nodes}
    out_edges = defaultdict(list)
    for e in edges:
        out_edges[e["source"]].append(e)
    ids_cat, defecto_cat = cargar_ids_s19_r2(ids_s19_ruta)
    dom_est = tuple(sorted(vocab["domain_range"]["establecida_en"][0]))
    dom_apl = tuple(sorted(vocab["domain_range"]["aplica_a"][0]))
    lista = [
        shape_s1_r2(edges, vocab),
        shape_s2(edges, node_by_id),
        shape_s3_r2(edges, node_by_id, vocab),
        shape_s4_congelado(nodes, edges),
        shape_s5_congelado(nodes, edges),
        shape_s6_congelado(nodes, edges),
        shape_s15(nodes, edges, node_by_id, excepciones_ruta),
        shape_s18_r2(nodes),
        shape_s19_catalogo(nodes, ids_cat, defecto_cat),
        _shape_enum("S20", "Obligacion", "tipo", nodes, vocab,
                    "ERROR — Enum de Obligacion.tipo del perfil r2: en la lista o con la marca fuera_de_lista."),
        _shape_enum("S24", "Restriccion", "tipo", nodes, vocab, "ERROR — " + NUMERACION_PERFIL_R2["S24"]),
        _shape_enum("S25", "Comunicacion", "tipo", nodes, vocab, "ERROR — " + NUMERACION_PERFIL_R2["S25"]),
        shape_s26_claves(nodes, vocab),
        shape_s27_mencion(edges, vocab, fase),
        shape_s28_registro(nodes, registro_ruta),
        shape_s29_padre(edges, ids_cat, defecto_cat),
        shape_s30_alcance(edges, node_by_id),
        shape_s31_evidencia(edges, e0_dir),
        shape_s7(nodes),
        shape_s8(nodes),
        shape_s9(nodes),
        shape_s10(nodes, out_edges, tipos=dom_est,
                  enunciado=f"Todo nodo del dominio r2 de establecida_en ({'/'.join(dom_est)}) tiene >=1 arista "
                            f"saliente establecida_en."),
        shape_s11(nodes, out_edges, tipos=dom_apl,
                  enunciado=f"Todo nodo del dominio r2 de aplica_a ({'/'.join(dom_apl)}) tiene >=1 arista saliente aplica_a."),
        shape_s12(nodes, out_edges),
        shape_s21_referencias(edges, node_by_id, perfil="r2"),
        shape_s22_padre_sugerido(edges, node_by_id),
        shape_s23_aplica_a_cuarentena(edges, node_by_id),
        shape_s32_cuantia(nodes, vocab),
    ]
    resultados = {r["rid"]: r for r in lista}
    bloq = list(BLOQUEANTES_R2) + (["S27"] if fase == "r2b" else [])
    info = list(INFORMATIVAS_R2) + (["S27"] if fase == "r2a" else [])
    fail = [rid for rid in bloq if resultados[rid]["result"] == "FAIL"]
    nc = [rid for rid in bloq if resultados[rid]["result"] == NO_COMPUTABLE]
    veredicto = "NO PASA" if fail else ("INCOMPLETO" if nc else "PASA")
    meta = {"bloqueantes": bloq, "informativas": info, "bloqueantes_en_fail": fail,
            "bloqueantes_no_computables": nc,
            "catalogo": {"ruta": ids_s19_ruta, "n_ids": len(ids_cat), "defecto": defecto_cat},
            "excepciones_s15": excepciones_ruta}
    return resultados, veredicto, meta


def correr_perfil_r2(args, g):
    """Camino del perfil r2: carga el vocabulario (FRENA si el candado no
    cierra), evalúa, escribe .md + .json si hay --out y devuelve el código de
    salida (0 PASA, 1 NO PASA, 3 INCOMPLETO, 2 freno del candado)."""
    try:
        vocab = cargar_vocabulario_r2()
    except VocabularioCongeladoError as e:
        print(f"FRENO — perfil r2: {e}", file=sys.stderr)
        return 2
    registro = os.path.join(args.registro_dir or os.path.dirname(os.path.abspath(args.kg)), REGISTRO_NO_MAPEADOS)
    resultados, veredicto, meta = evaluar_perfil_r2(g, vocab, args.fase, registro, args.e0)
    fecha = datetime.date.today().isoformat()
    sha_grafo = sha256_archivo(args.kg)
    nodes, edges = g["nodes"], g["edges"]
    bloq, info = meta["bloqueantes"], meta["informativas"]
    orden = bloq + info
    cab = [f"- **Grafo:** `{args.kg}`", f"- **sha256 del grafo:** `{sha_grafo}`", f"- **Fecha:** {fecha}",
           f"- **Nodos:** {len(nodes)}", f"- **Aristas:** {len(edges)}", f"- **Perfil:** r2 (fase {args.fase})",
           f"- **Vocabulario:** `{vocab['modulo']}` (sha256 `{vocab['sha256']}`); marcas de nodo de "
           f"`{RUTA_MODELOS_R2}`: {list(vocab['marcas_nodo'])}",
           f"- **Catálogo único (S19, S29):** `{meta['catalogo']['ruta']}` — {meta['catalogo']['n_ids']} ids"
           + (f"; DEFECTO: {meta['catalogo']['defecto']}" if meta["catalogo"]["defecto"] else ""),
           f"- **Lista de S15:** `{meta['excepciones_s15']}`", f"- **Registro (S28):** `{registro}`",
           f"- **E0 (S31):** `{args.e0}`",
           f"- **Veredicto global: {veredicto}**"
           + (f" — bloqueantes en FAIL: {', '.join(meta['bloqueantes_en_fail'])}" if meta["bloqueantes_en_fail"] else "")
           + (f" — bloqueantes NO COMPUTABLES: {', '.join(meta['bloqueantes_no_computables'])}"
              if meta["bloqueantes_no_computables"] else "")]
    lineas = ["# Validador de shapes — perfil r2", ""] + cab + [""]
    for titulo, rids in (("Bloqueantes", bloq), ("Informativas", info)):
        lineas += [f"## {titulo}", ""]
        for rid in rids:
            r = resultados[rid]
            lineas += [f"### {rid} — {r['result']}", "", r["enunciado"], "", f"**Resultado:** {r['resumen']}", ""]
            lineas += (["```"] + r["detalle_md"] + ["```", ""]) if r["detalle_md"] else ["Sin violaciones.", ""]
    lineas += ["## Tabla resumen", "", "| Severidad | Regla | Resultado | Resumen |", "|---|---|---|---|"]
    for rid in orden:
        r = resultados[rid]
        lineas.append(f"| {'bloqueante' if rid in bloq else 'informativa'} | {rid} | {r['result']} | {r['resumen']} |")
    lineas += ["", f"**Veredicto global: {veredicto}**", "", "## Numeración de las shapes del perfil r2", ""]
    lineas += [f"- {rid}: {enun}" for rid, enun in NUMERACION_PERFIL_R2.items()] + [""]
    salida_json = {
        "perfil": "r2", "fase": args.fase, "grafo": args.kg, "sha256_grafo": sha_grafo, "fecha": fecha,
        "nodos": len(nodes), "aristas": len(edges),
        "vocabulario": {"modulo": vocab["modulo"], "sha256": vocab["sha256"], "marcas_nodo": list(vocab["marcas_nodo"])},
        "catalogo": meta["catalogo"], "excepciones_s15": meta["excepciones_s15"], "registro": registro, "e0": args.e0,
        "veredicto": veredicto, "bloqueantes_en_fail": meta["bloqueantes_en_fail"],
        "bloqueantes_no_computables": meta["bloqueantes_no_computables"],
        "shapes": {rid: {"severidad": "bloqueante" if rid in bloq else "informativa", "result": resultados[rid]["result"],
                         "resumen": resultados[rid]["resumen"], "conteos": resultados[rid]["conteos"]} for rid in orden},
        "numeracion_perfil_r2": NUMERACION_PERFIL_R2,
    }
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))
        with open(os.path.splitext(args.out)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump(salida_json, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(f"Grafo: {args.kg}\nNodos: {len(nodes)} | Aristas: {len(edges)} | Perfil: r2 (fase {args.fase})")
    for rid in orden:
        r = resultados[rid]
        print(f"{'bloqueante' if rid in bloq else 'informativa':12s} {rid:4s} {r['result']:14s} {r['resumen']}")
    print(f"\nVEREDICTO GLOBAL: {veredicto}")
    return {"PASA": 0, "NO PASA": 1, "INCOMPLETO": 3}[veredicto]


def correr_perfil_congelado(args, g):
    """Camino completo del perfil: carga el vocabulario (FRENA si el candado
    no cierra), evalúa, escribe .md + .json si hay --out, imprime por consola
    y devuelve el código de salida (0 PASA, 1 NO PASA, 2 freno del candado)."""
    try:
        vocab = cargar_vocabulario_congelado()
    except VocabularioCongeladoError as e:
        print(f"FRENO — perfil congelado: {e}", file=sys.stderr)
        return 2

    nodes, edges = g["nodes"], g["edges"]
    resultados, veredicto, meta = evaluar_perfil_congelado(g, vocab, args.excepciones)
    fecha = datetime.date.today().isoformat()
    sha_grafo = sha256_archivo(args.kg)
    cat = meta["catalogo"]

    cabecera = [
        f"- **Grafo:** `{args.kg}`",
        f"- **sha256 del grafo:** `{sha_grafo}`",
        f"- **Fecha:** {fecha}",
        f"- **Nodos:** {len(nodes)}",
        f"- **Aristas:** {len(edges)}",
        "- **Perfil:** congelado",
        f"- **Vocabulario:** `{vocab['modulo']}` — sha256 del prefijo `{vocab['sha256_prefijo']}` "
        f"(hash system+tools `{vocab['hash_prefijo']}`); {len(vocab['entity_types'])} tipos, "
        f"{len(vocab['predicates'])} predicados, enum Obligacion.tipo de {len(vocab['obligacion_tipo'])} "
        f"(retirados: {', '.join(vocab['retirados'])})",
        f"- **Catálogo de sujetos:** `{cat['ruta']}` — {cat['n_ids']} ids ({cat['n_clases']} clases, "
        f"{cat['n_roles']} roles)" + (f"; DEFECTO: {cat['defecto']}" if cat["defecto"] else ""),
        f"- **Veredicto global: {veredicto}**"
        + (f" — bloqueantes en FAIL: {', '.join(meta['bloqueantes_en_fail'])}"
           if meta["bloqueantes_en_fail"] else " — todas las bloqueantes en PASS"),
    ]

    def seccion(titulo, rids):
        out = [f"## {titulo}", ""]
        for rid in rids:
            r = resultados[rid]
            out += [f"### {rid} — {r['result']}", "", r["enunciado"], "", f"**Resultado:** {r['resumen']}", ""]
            if r["detalle_md"]:
                out += ["```"] + r["detalle_md"] + ["```", ""]
            else:
                out += ["Sin violaciones.", ""]
        return out

    lineas = ["# Validador de shapes — perfil congelado", ""] + cabecera + [""]
    lineas += seccion("Bloqueantes", BLOQUEANTES_CONGELADO)
    lineas += seccion("Informativas", INFORMATIVAS_CONGELADO)
    lineas += ["## Tabla resumen", "", "| Severidad | Regla | Resultado | Resumen |", "|---|---|---|---|"]
    for rid in ORDEN_SHAPES_CONGELADO:
        r = resultados[rid]
        sev = "bloqueante" if rid in BLOQUEANTES_CONGELADO else "informativa"
        lineas.append(f"| {sev} | {rid} | {r['result']} | {r['resumen']} |")
    lineas += ["", f"**Veredicto global: {veredicto}**", ""]
    lineas += ["## Numeración de las shapes nuevas del perfil", ""]
    lineas += [f"- {rid}: {enun}" for rid, enun in NUMERACION_PERFIL.items()]
    lineas += ["", "## Fuera del perfil", ""]
    lineas += [f"- {rid}: {motivo}" for rid, motivo in FUERA_DEL_PERFIL.items()]
    lineas += [f"- {', '.join(SHAPES_NO_IMPLEMENTADAS)}: no implementadas (se declaran para que su "
               "ausencia se lea; no se inventan).",
               "- S18: número ya declarado en docs/esquema_v2_diseño.md con otro enunciado "
               "(umbral de limita); no se reutiliza.", ""]

    salida_json = {
        "perfil": "congelado",
        "grafo": args.kg,
        "sha256_grafo": sha_grafo,
        "fecha": fecha,
        "nodos": len(nodes),
        "aristas": len(edges),
        "vocabulario": {
            "modulo": vocab["modulo"],
            "sha256_prefijo": vocab["sha256_prefijo"],
            "hash_prefijo": vocab["hash_prefijo"],
            "n_tipos": len(vocab["entity_types"]),
            "n_predicados": len(vocab["predicates"]),
            "enum_obligacion_tipo": list(vocab["obligacion_tipo"]),
            "retirados": list(vocab["retirados"]),
        },
        "catalogo": cat,
        "veredicto": veredicto,
        "bloqueantes_en_fail": meta["bloqueantes_en_fail"],
        "shapes": {
            rid: {
                "severidad": "bloqueante" if rid in BLOQUEANTES_CONGELADO else "informativa",
                "result": resultados[rid]["result"],
                "resumen": resultados[rid]["resumen"],
                "conteos": resultados[rid]["conteos"],
            } for rid in ORDEN_SHAPES_CONGELADO
        },
        "numeracion_perfil": NUMERACION_PERFIL,
        "fuera_del_perfil": dict(FUERA_DEL_PERFIL, **{s: "no implementada" for s in SHAPES_NO_IMPLEMENTADAS}),
    }

    ruta_json = None
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))
        ruta_json = os.path.splitext(args.out)[0] + ".json"
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(salida_json, f, ensure_ascii=False, indent=2)
            f.write("\n")

    # ---------- Consola ----------
    print(f"Grafo: {args.kg}")
    print(f"Nodos: {len(nodes)} | Aristas: {len(edges)} | Perfil: congelado")
    print(f"Vocabulario: {vocab['modulo']} (sha256 prefijo {vocab['sha256_prefijo'][:12]}…)")
    print(f"Catálogo: {cat['ruta']} ({cat['n_ids']} ids)\n")
    for titulo, rids in (("BLOQUEANTES", BLOQUEANTES_CONGELADO), ("INFORMATIVAS", INFORMATIVAS_CONGELADO)):
        print(f"=== {titulo} ===")
        for rid in rids:
            r = resultados[rid]
            print(f"[{r['result']:4s}] {rid} — {r['resumen']}")
            for linea in lista_consola(r["detalle_consola"]):
                print(f"        {linea}")
        print()
    print("=== TABLA RESUMEN ===")
    print(f"{'Sever.':12s} {'Regla':6s} {'Resultado':10s} Resumen")
    for rid in ORDEN_SHAPES_CONGELADO:
        r = resultados[rid]
        sev = "bloqueante" if rid in BLOQUEANTES_CONGELADO else "informativa"
        print(f"{sev:12s} {rid:6s} {r['result']:10s} {r['resumen']}")
    print(f"\nVEREDICTO GLOBAL: {veredicto}"
          + (f" (bloqueantes en FAIL: {', '.join(meta['bloqueantes_en_fail'])})"
             if meta["bloqueantes_en_fail"] else ""))
    if args.out:
        print(f"\nReporte escrito en: {os.path.abspath(args.out)}")
        print(f"Conteos escritos en: {os.path.abspath(ruta_json)}")
    else:
        print("\n(sin --out: no se escribió ningún archivo)")
    return 0 if veredicto == "PASA" else 1


def main():
    ap = argparse.ArgumentParser(description="Validador de shapes v0 (capas 1 y 2)")
    ap.add_argument("--kg", default=DEFAULT_KG, help="Ruta al kg.json (solo lectura)")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="Ruta del reporte Markdown. SIN default: si no se pasa, el "
                         "validador reporta por consola y no escribe ningún archivo.")
    ap.add_argument("--excepciones", default=None,
                    help="Artefacto con el bloque 'excepciones_s15' (S15). Sin esta opción "
                         "la lista declarada es vacía y todo rol huérfano es FAIL.")
    ap.add_argument("--perfil", default=None, choices=PERFILES,
                    help="Perfil de validación. Sin esta opción el comportamiento es el de "
                         "siempre (v0). 'congelado': esquema congelado de la generación 3, "
                         "vocabulario leído de prompt_congelado.py, catálogo de sujetos "
                         "leído de --excepciones, veredicto PASA/NO PASA y .json de conteos. "
                         "'r2': perfil r2 (U-R2-CODIGO), vocabulario de pyd_r2/generados/enums_r2.json.")
    ap.add_argument("--fase", default="r2a", choices=FASES_R2,
                    help="Solo con --perfil r2: r2a (S27 informativa, default) o r2b (S27 bloqueante).")
    ap.add_argument("--registro-dir", default=None, dest="registro_dir",
                    help="Solo con --perfil r2: directorio con no_mapeados_sujetos.jsonl (S28); default el del --kg.")
    ap.add_argument("--e0", default=None,
                    help="Solo con --perfil r2: directorio de E0 (chunks_<to>.json) con que se ensambló el grafo (S31).")
    args = ap.parse_args()

    with open(args.kg, encoding="utf-8") as f:
        g = json.load(f)

    if args.perfil == "congelado":
        sys.exit(correr_perfil_congelado(args, g))
    if args.perfil == "r2":
        sys.exit(correr_perfil_r2(args, g))

    nodes, edges = g["nodes"], g["edges"]
    node_by_id = {n["id"]: n for n in nodes}
    out_edges = defaultdict(list)
    for e in edges:
        out_edges[e["source"]].append(e)

    resultados = {}   # regla -> dict(result, resumen, detalle_md, detalle_consola)

    def registrar(rid, enunciado, result, resumen, detalle_md, detalle_consola=None):
        resultados[rid] = {
            "enunciado": enunciado,
            "result": result,
            "resumen": resumen,
            "detalle_md": detalle_md,
            "detalle_consola": detalle_consola if detalle_consola is not None else detalle_md,
        }

    def registrar_res(r):
        resultados[r["rid"]] = r

    # ---------- S1 ----------
    viol = [f"idx {i}: relation='{e['relation']}'"
            for i, e in enumerate(edges) if norm(e["relation"]) not in RELACIONES_12]
    registrar(
        "S1", "Toda arista usa una de las 12 relaciones del esquema (nombre normalizado).",
        "PASS" if not viol else "FAIL",
        f"{len(edges) - len(viol)}/{len(edges)} aristas con relación válida; {len(viol)} violaciones.",
        viol,
    )

    # ---------- S2 ----------
    registrar_res(shape_s2(edges, node_by_id))

    # ---------- S3 ----------
    viol = []
    for i, e in enumerate(edges):
        rel = norm(e["relation"])
        if rel not in FIRMAS or e["source"] not in node_by_id or e["target"] not in node_by_id:
            continue  # capturado por S1/S2
        dominios, rango = FIRMAS[rel]
        st = node_by_id[e["source"]]["type"]
        dt = node_by_id[e["target"]]["type"]
        if st not in dominios or dt != rango:
            viol.append(f"idx {i}: {rel} {st} -> {dt} ({e['source']} -> {e['target']})")
    registrar(
        "S3", "Toda arista respeta la matriz de firmas dominio -> rango declarada en FIRMAS.",
        "PASS" if not viol else "FAIL",
        f"{len(edges) - len(viol)}/{len(edges)} aristas conformes a firma; {len(viol)} violaciones.",
        viol,
    )

    # ---------- S4 ----------
    viol = []
    nodos_ok = 0
    for n in nodes:
        d = check_provenance(n.get("provenance"))
        if d:
            viol.append(f"nodo {n['id']}: {'; '.join(d)}")
        else:
            nodos_ok += 1
    aristas_ok = 0
    for i, e in enumerate(edges):
        d = check_provenance(e.get("provenance"))
        if d:
            viol.append(f"arista idx {i} ({e['relation']} {e['source']} -> {e['target']}): {'; '.join(d)}")
        else:
            aristas_ok += 1
    registrar(
        "S4", "Todo nodo y toda arista tienen provenance dict con exactamente source_doc y location, strings no vacías.",
        "PASS" if not viol else "FAIL",
        f"Nodos OK: {nodos_ok}/{len(nodes)}. Aristas OK: {aristas_ok}/{len(edges)}. Violaciones: {len(viol)}.",
        viol,
    )

    # ---------- S5 ----------
    viol = []
    n_loc_nodos = n_loc_aristas = 0
    for n in nodes:
        loc = (n.get("provenance") or {}).get("location", "")
        if "punto" in norm(loc):
            n_loc_nodos += 1
        else:
            viol.append(f"nodo {n['id']}: location='{loc[:80]}'")
    for i, e in enumerate(edges):
        loc = (e.get("provenance") or {}).get("location", "")
        if "punto" in norm(loc):
            n_loc_aristas += 1
        else:
            viol.append(f"arista idx {i} ({e['relation']}): location='{loc[:80]}'")
    registrar(
        "S5", "Todo location (de nodo y de arista) contiene 'punto' (normalizado).",
        "PASS" if not viol else "FAIL",
        f"Nodos con 'punto': {n_loc_nodos}/{len(nodes)}. Aristas: {n_loc_aristas}/{len(edges)}. Violaciones: {len(viol)}.",
        viol,
    )

    # ---------- S6 ----------
    archivos = {n["properties"].get("archivo") for n in nodes if n["type"] == "TextoOrdenado"}
    archivos.discard(None)
    viol = []
    for n in nodes:
        sd = (n.get("provenance") or {}).get("source_doc")
        if sd not in archivos:
            viol.append(f"nodo {n['id']}: source_doc='{sd}'")
    for i, e in enumerate(edges):
        sd = (e.get("provenance") or {}).get("source_doc")
        if sd not in archivos:
            viol.append(f"arista idx {i} ({e['relation']}): source_doc='{sd}'")
    registrar(
        "S6", "Todo source_doc pertenece al conjunto de valores de 'archivo' de los nodos TextoOrdenado.",
        "PASS" if not viol else "FAIL",
        f"Archivos válidos ({len(archivos)}): {sorted(archivos)}. Violaciones: {len(viol)}.",
        viol,
    )

    # ---------- S7 ----------
    registrar_res(shape_s7(nodes))

    # ---------- S8 ----------
    registrar_res(shape_s8(nodes))

    # ---------- S9 ----------
    registrar_res(shape_s9(nodes))

    # ---------- S10 ----------
    registrar_res(shape_s10(nodes, out_edges))

    # ---------- S11 ----------
    registrar_res(shape_s11(nodes, out_edges))

    # ---------- S12 ----------
    registrar_res(shape_s12(nodes, out_edges))

    # ---------- S15 (U-ESQ-V3) ----------
    registrar_res(shape_s15(nodes, edges, node_by_id, args.excepciones))

    # ---------- Reporte ----------
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fecha = datetime.date.today().isoformat()
    orden = list(ORDEN_SHAPES)
    lineas = [
        "# Validador de shapes v0 — capas 1 y 2",
        "",
        f"- **Grafo:** `{args.kg}`",
        f"- **Fecha:** {fecha}",
        f"- **Nodos:** {len(nodes)}",
        f"- **Aristas:** {len(edges)}",
        "",
    ]
    for rid in orden:
        r = resultados[rid]
        lineas += [f"## {rid} — {r['result']}", "", r["enunciado"], "", f"**Resultado:** {r['resumen']}", ""]
        if r["detalle_md"]:
            lineas += ["```"] + r["detalle_md"] + ["```", ""]
        else:
            lineas += ["Sin violaciones.", ""]
    lineas += ["## Tabla resumen", "", "| Regla | Resultado | Resumen |", "|---|---|---|"]
    for rid in orden:
        r = resultados[rid]
        lineas.append(f"| {rid} | {r['result']} | {r['resumen']} |")
    lineas.append("")
    lineas += [
        f"## Shapes no implementadas: {', '.join(SHAPES_NO_IMPLEMENTADAS)}",
        "",
        "Se declaran para que su ausencia se lea. No se inventan: implementarlas es otra unidad.",
        "",
    ]
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))

    # ---------- Consola ----------
    print(f"Grafo: {args.kg}")
    print(f"Nodos: {len(nodes)} | Aristas: {len(edges)}\n")
    for rid in orden:
        r = resultados[rid]
        print(f"[{r['result']:4s}] {rid} — {r['resumen']}")
        for linea in lista_consola(r["detalle_consola"]):
            print(f"        {linea}")
    print("\n=== TABLA RESUMEN ===")
    print(f"{'Regla':6s} {'Resultado':10s} Resumen")
    for rid in orden:
        r = resultados[rid]
        print(f"{rid:6s} {r['result']:10s} {r['resumen']}")
    if args.out:
        print(f"\nReporte escrito en: {os.path.abspath(args.out)}")
    else:
        print("\n(sin --out: no se escribió ningún archivo)")


if __name__ == "__main__":
    main()
