"""
selftest_clave_cache.py — qué cambio mueve la clave de la caché local de E1 y
de E3, verificado sin llamar a la API. U-MANT, etapa M1 (b), con el perfil
sellado de la tanda 0 (`v3_b54`); U-TABLA-REPROC lo extiende al perfil `r2b`.

La clave es sha256(namespace + "\\n" + request canónico)
(data/experiment/evaluacion/llm_cache.py:110-126). Este selftest arma los
requests con el código real del pipeline —el `build_request_kwargs` de cada
perfil de E1 (`perfil_e1.perfil`: data/experiment/b54_catalogo_v3/code/
prompt_v3_b54.py:524 en `v3_b54`, data/experiment/reextraccion_v2/
e1_extractor/prompt_r2b.py:440 en `r2b`) y `prompt_e3.build_request_kwargs`
para E3 (data/experiment/reextraccion_v2/e3_verificador/prompt_e3.py:352)— y
calcula la clave con `compute_key`, sin importar ni construir ningún cliente
de la API.

Perfil sellado (`v3_b54`), los bloques de M1, sin cambios:

  A. Anclaje. Las claves recalculadas para las 2.434 unidades de E0 de la
     tanda 0 se buscan en la caché de E1, y las de la primera verificación de
     E3 en la caché de E3. Las dbs se abren en solo lectura
     (`mode=ro&immutable=1`): no se escribe nada en ellas. Si una db no está en
     disco (no se versionan), el bloque queda NO_VERIFICABLE y el resto corre.
  B. Variaciones V01 a V24, una entrada por vez, sobre una muestra fija de
     diez unidades de la tanda 0 (una por TO). Cada variación declara qué
     unidades deberían cambiar de clave en E1 y en E3; el selftest compara
     contra lo observado. Las variaciones de los catálogos JSON corren en un
     proceso hijo que redirige la lectura del JSON a una versión alterada EN
     MEMORIA (ningún archivo se escribe ni se modifica).

Perfil r2b (U-TABLA-REPROC):

  A'. Anclaje sobre las dbs de U-REEXT-T0 (`--salida-r2b`, por defecto
      corpus_tanda0/salida_r2b). Si esa salida no existe, el bloque queda
      NO_VERIFICABLE y rige, declarado, el anclaje del perfil sellado
      (decisión 3 de la autora al firmar el mandato de U-TABLA-REPROC): se
      corre de nuevo cuando existan las dbs de U-REEXT-T0.
  B'. Variaciones R00 a R34 sobre una muestra fija de trece unidades de la E0
      e0-r2 de la tanda 0 (`salida_tanda0_r2b/`): las diez de M1 más tres con
      tablas serializadas, una de ellas con la herencia recortada. La clave de
      E3 del perfil r2b necesita una salida de E1 en la forma r2, que todavía
      no existe: se arma una salida sintética mínima por unidad y se valida con
      validador_e1 y el esquema del perfil (`validacion_sintetica_r2`). Las
      variaciones de archivos de datos corren en un proceso hijo que los sirve
      alterados EN MEMORIA, como en M1. Con los candados de U-PROMPT-R2,
      P3c-2 (filas F04b, F22, F22b y F23), R29, R29b y R30 editan un literal
      del módulo en una copia en memoria de su fuente, que el proceso hijo
      importa en lugar del archivo, y frenan, como R32; R13c varía el techo del
      tercer escalón del reintento por corte (fila F08d). Con la temperatura de
      U-PROMPT-R2, P5 (el pedido del perfil r2b lleva `temperature` 0, y el
      reintento por salida mal formada, 1), R14 varía la temperatura del pedido
      (fila F08e) y R25 arma el reintento con prompt_r2b.kwargs_reintento_forma_r2b
      (fila F08c). Con U-E3-LISTAS (fila F23b), R33 y R33b editan la NOTA del ítem
      de una lista y la regla de los bloques contiguos (D2), y frenan como R30;
      R03 y R27 esperan el cambio de la clave de E3 en los ítems cuyo bloque que
      abre la lista tocan, y A3r exige las claves de los no ítems presentes y
      las de los ítems ausentes, exactamente (D5, enmienda 1 al mandato). Desde
      R0 (enmienda 7 al protocolo entre tandas, §1.5), A3r exige ausentes,
      exactamente, los ítems que no son de R0, y presentes los no ítems y las 20
      claves de verificación de r0/esperados_r0.json (controlado por su sha256),
      con dos variaciones de control que tienen que dar DISCREPANCIA. Con
      U-ALCANCE-E1 (fila F13c), R34 da en memoria una entrada del derivado del
      registro de alcance por tanda a docvig, que no tiene entrada en la tabla
      de la release: cambia la clave de E1 de sus unidades, como R11 (F12).
  C. Contraste fila por fila con la tabla de
     data/experiment/mantenimiento/tabla_reprocesamiento.md: cada fila declara
     el comportamiento de la clave de E1 y de E3 del perfil r2b y las
     variaciones que la prueban; una discrepancia es FRENO. Las variaciones del
     perfil sellado no tienen fila: se comparan con lo que esperan, que es lo
     de M1 (`e18d616`).

Uso (desde la raíz del repo, o de una copia del repo):
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
      data/experiment/mantenimiento/code/selftest_clave_cache.py \\
      --out data/experiment/mantenimiento/selftest_clave_cache.json

Salida determinística (sin fechas): dos corridas dan el mismo JSON byte a byte.
Costo de API: USD 0. Sin red.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import copy
import dataclasses
import hashlib
import io
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                    # mantenimiento/code
REPO = AQUI.parents[3]
EXP = REPO / "data" / "experiment"
REX = EXP / "reextraccion_v2"
E0_TANDA0 = REX / "e0_chunking" / "salida_tanda0"
SALIDA_DIRIGIDA = REX / "corpus_tanda0" / "salida_dirigida"
DB_E1 = REX / "e1_extractor" / "cache" / "e1_extraccion.db"
DB_E3 = REX / "e3_verificador" / "cache" / "e3_verificacion.db"
RUNNER = REX / "corpus_v2" / "runner_corpus.py"
DIRIGIDA = SALIDA_DIRIGIDA / "reextraccion_dirigida.json"
PARTICION = EXP / "segmentacion_84" / "b584_particion"
JSON_V2 = EXP / "grafo_v2" / "esquema_v2_clases.json"
JSON_V3 = EXP / "esq_v3_miembros" / "esquema_v3_clases.json"
TABLA_MD = AQUI.parent / "tabla_reprocesamiento.md"

PERFIL = "v3_b54"          # perfil de la tanda 0 (manifiestos/tanda0_10tos.json)
TOS_TANDA0 = ("pro", "cla", "ric", "cap", "ext",
              "ctacte", "lingob", "polcre", "pagjub", "docvig")

# Muestra fija: una unidad por TO de la tanda 0, elegida para cubrir los tipos
# de unidad y de herencia de E0 (salida_tanda0/chunks_<to>.json).
MUESTRA = (
    "pro::2.3.1.1",        # punto terminal con herencia de prosa (intro)
    "cla::2.2.4::intro",   # mini-chunk
    "ric::3.1.4",          # marcado como contenido tabular por E0
    "cap::4.3.3.1",        # una de las tres unidades de la re-extracción dirigida
    "ext::7.1.1.3",        # tabular, con herencia intro y cierre
    "ctacte::1.3.1.1",     # TO nuevo de la tanda 0, con rol de alcance v3
    "lingob::1.1",         # TO nuevo, punto sin herencia de prosa
    "polcre::2.1.1",       # TO nuevo, herencia con diez bloques de cierre
    "pagjub::2.7::intro",  # mini-chunk de un TO nuevo
    "docvig::3.3.1",       # TO sin rol de alcance (hueco F1.2)
)
TO_ROL_VARIADO = "cla"     # TO cuya línea de alcance se altera (variaciones V11 y V21)
TO_NUEVO = "gerc"          # TO de la partición fuera de las tres tandas, con unidad punto_terminal (V23 y R23)
UNIDAD_TO_NUEVO = "gerc::1.1"
RENUMERACION = {"to": "pro", "insertar_antes_de": "2.3"}   # V24

# Módulos que corren DESPUÉS de E3 o que no arman requests: un cambio en ellos
# es «solo código». V19 verifica que ninguno se carga al armar los requests.
MODULOS_SOLO_CODIGO = ("e2_lib", "validador_e1", "ensamblar_corpus",
                       "ensamblar_r1", "ensamblar_tanda0", "r1_e4",
                       "r1_e5_esqueleto", "r1_referencias", "r1_provenance",
                       "r1_invariantes", "assemble", "manifiesto_corpus")

# ------------------------------------------------------------------------- #
# Perfil r2b (U-TABLA-REPROC)                                                #
# ------------------------------------------------------------------------- #
PERFIL_R2B = "r2b"         # perfil de U-REEXT-T0 y de las tandas (manifiestos/tanda0_10tos_r2b.json)
# E0 e0-r2 de la tanda 0 con C2 de U-R2-CODIGO-2 (9f6361e); U-REEXT-T0 pasa el
# manifiesto r2b a este directorio (borrador de su mandato, T1, punto 1).
E0_TANDA0_R2B = REX / "e0_chunking" / "salida_tanda0_r2b"
SALIDA_R2B = REX / "corpus_tanda0" / "salida_r2b"   # salida de U-REEXT-T0
# La muestra de M1 más tres unidades con tablas serializadas por e0-r2: una
# confiable, una con estructura sin resolver y la única con la herencia
# recortada en la tanda 0.
MUESTRA_R2B = MUESTRA + ("ric::3.1.5", "ric::4.4.1", "ric::11.2.3")
# Las unidades en posición par de la muestra declaran una omisión
# `meta_normativo` en su salida sintética (variación R30).
CON_OMISION_R2B = {cid: i % 2 == 0 for i, cid in enumerate(MUESTRA_R2B)}
SUJETO_SINTETICO = "Sujeto_entidad_financiera"
UNIDAD_PARTICION = "cap::4.2.1.2"       # la única de la tanda 0 que se puede partir por ítems (R26)
UNIDAD_TABLA_FORZADA = "ric::3.1.5"     # su primera tabla serializada pasa a residual (R32)
UNIDAD_CALIBRADOR = "ric::7.1"          # unidad del calibrador CAL-1 de E3 (R22d)
REEMPLAZOS_R2B = REX / "e1_extractor" / "prompt_r2b_reemplazos.json"
TABLAS_FORZADAS_R2B = REX / "e1_extractor" / "tablas_residuales_forzadas_r2b.json"
GENERADOS_R2 = EXP / "catalogo_unico" / "generados_r2"
ROL_POR_TO_R2 = GENERADOS_R2 / "rol_por_to_r2.json"
INDICE_E4_R2 = GENERADOS_R2 / "indice_e4_r2.json"
CATALOGO_R2 = EXP / "catalogo_unico" / "catalogo_sujetos_r2.json"
CHUNKS_CALIBRADOR = REX / "e0_chunking" / "salida" / "chunks_ric.json"
PIES_R2B = E0_TANDA0_R2B / "pies_cap.json"
ARCHIVO_TO_ROL_VARIADO = "TO_clasificacion_deudores_actual.pdf"
# R34 (U-ALCANCE-E1): el documento de la muestra sin entrada en la tabla de la release recibe, en memoria, una entrada
# del derivado del registro de alcance por tanda (la de una clase).
ARCHIVO_SIN_ROL_R34 = "docvig.pdf"
ENTRADA_DERIVADO_R34 = "ri_ccna.pdf"
# Además de los de M1: el validador r2 y su política, las reglas de las
# cuantías, el runner y la normalización de la regla C1 (la carga
# ensamblar_tanda0 con --union-comunicaciones). validador_e1 toma de
# validador_r2 las correcciones de tipo y predicado al VALIDAR la salida de
# E1, no al armar los requests.
MODULOS_SOLO_CODIGO_R2 = MODULOS_SOLO_CODIGO + ("validador_r2", "reglas_comparacion", "runner_corpus",
                                                "tamanos_desamb_mesa")


# ------------------------------------------------------------------------- #
# Utilidades                                                                 #
# ------------------------------------------------------------------------- #

def _rutas_import() -> None:
    for p in (REX / "e1_extractor", REX / "e3_verificador", REX / "e2_reduce", REX,
              EXP / "evaluacion"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _ruta_e0() -> None:
    p = REX / "e0_chunking"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def sha256_archivo(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO.resolve()))
    except ValueError:
        return str(p)


def constantes_runner() -> dict:
    """MODEL_E1, MODEL_E3 y MAX_TOKENS_REINTENTO leídos del runner por AST, sin
    importarlo (importarlo carga el manifiesto y los clientes)."""
    arbol = ast.parse(RUNNER.read_text(encoding="utf-8"))
    out = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 \
                and isinstance(nodo.targets[0], ast.Name) \
                and nodo.targets[0].id in ("MODEL_E1", "MODEL_E3", "MAX_TOKENS_REINTENTO"):
            out[nodo.targets[0].id] = ast.literal_eval(nodo.value)
            out[nodo.targets[0].id + "_linea"] = nodo.lineno
    return out


def cargar_chunks(to: str, e0_dir: Path = E0_TANDA0) -> list[dict]:
    return json.loads((e0_dir / f"chunks_{to}.json").read_text(encoding="utf-8"))


def cargar_validaciones(to: str) -> dict[str, dict]:
    """Validación de E1 por unidad (salida_dirigida: igual a salida/ salvo las
    tres unidades de cap re-extraídas), con el criterio de aceptación de E3."""
    import comun_e3
    regs = comun_e3.cargar_extracciones(SALIDA_DIRIGIDA / to / "extracciones_e1_compact.jsonl")
    return {cid: r["validacion"] for cid, r in regs.items() if comun_e3.chunk_aceptado(r)}


def claves_db(db: Path, namespace: str) -> set[str] | None:
    if not db.exists():
        return None
    uri = "file:" + str(db.resolve()) + "?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    try:
        return {k for (k,) in con.execute(
            "SELECT key FROM cache WHERE namespace = ?", (namespace,))}
    finally:
        con.close()


class Armado:
    """Arma requests y claves de E1 y E3 con el código del pipeline. `perfil`:
    el de E1 (por defecto el sellado de la tanda 0). Con `con_e3=False` no
    importa los módulos de E3 (`cargar_e3` los importa después): así el proceso
    hijo distingue un candado del prefijo de E3 de uno del perfil de E1."""

    def __init__(self, perfil: str = PERFIL, con_e3: bool = True):
        _rutas_import()
        import llm_cache as lc
        import perfil_e1
        import cliente_e1
        self.lc = lc
        self.perfil_e1 = perfil_e1
        self.cliente_e1 = cliente_e1
        if con_e3:
            self.cargar_e3()
        self.pf = perfil_e1.perfil(perfil)
        k = constantes_runner()
        self.model_e1, self.model_e3 = k["MODEL_E1"], k["MODEL_E3"]
        self.constantes = k
        self.ns_e1 = cliente_e1.namespace_e1(prefijo_hash=self.pf.prefijo_hash_para_namespace)

    def cargar_e3(self) -> None:
        import prompt_e3
        import cliente_e3
        self.prompt_e3 = prompt_e3
        self.cliente_e3 = cliente_e3
        self.ns_e3 = cliente_e3.namespace_e3()

    def kw_e1(self, chunk: dict, **extra) -> dict:
        return self.pf.build_request_kwargs(chunk, model=self.model_e1, **extra)

    def kw_e3(self, chunk: dict, val: dict) -> dict:
        return self.prompt_e3.build_request_kwargs(chunk, val, model=self.model_e3)

    def clave(self, ns: str, kw: dict) -> str:
        return self.lc.compute_key(ns, self.lc.canonical_request(kw))

    def k_e1(self, chunk: dict, **extra) -> str:
        return self.clave(self.ns_e1, self.kw_e1(chunk, **extra))

    def k_e3(self, chunk: dict, val: dict) -> str:
        return self.clave(self.ns_e3, self.kw_e3(chunk, val))

    @staticmethod
    def hash_prefijo(kw: dict) -> str:
        """Mismo cálculo que PREFIJO_CANONICO_V3 / PREFIJO_HASH_V3
        (prompt_v3_b54.py:516-520), PREFIJO_HASH_R2B (prompt_r2b.py:133-135)
        y prompt_e3.PREFIJO_HASH (prompt_e3.py:213-217)."""
        canon = json.dumps({"system": kw["system"], "tools": kw["tools"]},
                           sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12]


def cargar_muestra() -> tuple[dict, dict]:
    chunks, vals = {}, {}
    for cid in MUESTRA:
        to = cid.split("::", 1)[0]
        por_id = {c["id"]: c for c in cargar_chunks(to)}
        chunks[cid] = por_id[cid]
        vals[cid] = cargar_validaciones(to).get(cid)
    return chunks, vals


# ------------------------------------------------------------------------- #
# Perfil r2b: muestra y salida sintética de E1 en la forma r2                #
# ------------------------------------------------------------------------- #

def cargar_chunks_muestra_r2b() -> dict[str, dict]:
    chunks, por_to = {}, {}
    for cid in MUESTRA_R2B:
        to = cid.split("::", 1)[0]
        if to not in por_to:
            por_to[to] = {c["id"]: c for c in cargar_chunks(to, E0_TANDA0_R2B)}
        chunks[cid] = por_to[to][cid]
    return chunks


def crudo_sintetico_r2(c: dict, con_omision: bool) -> dict:
    """Salida mínima de E1 en la forma r2 para una unidad: el TextoOrdenado,
    una Obligacion con su tramo (la primera línea del texto propio, hasta 80
    caracteres), su `establecida_en` y un `aplica_a` con id del catálogo y
    mención; con `con_omision`, una omisión `meta_normativo`. Es un insumo del
    armado del request de E3, no una extracción: solo tiene que pasar
    validador_e1 y ser función de la unidad."""
    tramo = (c["texto"].split("\n")[0] or c["texto"])[:80]
    ents = [{"local_id": "to", "type": "TextoOrdenado", "label": c["to"], "punto": c["unidad"], "tramo": tramo},
            {"local_id": "o", "type": "Obligacion", "label": "Obligación del selftest", "punto": c["unidad"],
             "tramo": tramo, "properties": {"descripcion": "Descripción del selftest.", "tipo": "otra"}}]
    rels = [{"source": "o", "predicate": "establecida_en", "target": "to", "punto": c["unidad"]},
            {"source": "o", "predicate": "aplica_a", "sujeto_id": SUJETO_SINTETICO,
             "sujeto_mencion": "las entidades", "punto": c["unidad"]}]
    oms = [{"categoria": "meta_normativo", "tramo": tramo, "nota": "omisión del selftest"}] if con_omision else []
    return {"entities": ents, "relations": rels, "omisiones": oms}


def validacion_sintetica_r2(ar: Armado, c: dict, con_omision: bool) -> dict | None:
    """La salida sintética validada con validador_e1 y el esquema del perfil
    (forma r2: correcciones de validador_r2, traducción a la forma que leen E3
    y el ratchet, `indice_crudo`). None si la validación rechaza la unidad."""
    import validador_e1
    v = validador_e1.validar_salida(crudo_sintetico_r2(c, con_omision), c, esquema=ar.pf.esquema).as_dict()
    return None if any(r["nivel"] == "chunk" for r in v["rechazos"]) else v


def validaciones_muestra_r2b(ar: Armado, chunks: dict[str, dict]) -> dict[str, dict | None]:
    return {cid: validacion_sintetica_r2(ar, chunks[cid], CON_OMISION_R2B[cid]) for cid in MUESTRA_R2B}


# ------------------------------------------------------------------------- #
# A. Anclaje contra la caché guardada                                        #
# ------------------------------------------------------------------------- #

def bloque_anclaje(ar: Armado) -> dict:
    out: dict = {"namespace_e1": ar.ns_e1, "namespace_e3": ar.ns_e3,
                 "prefijo_hash_e1": ar.pf.prefijo_hash,
                 "prefijo_hash_e3": ar.prompt_e3.PREFIJO_HASH,
                 "model_e1": ar.model_e1, "model_e3": ar.model_e3,
                 "constantes_runner": {k: v for k, v in ar.constantes.items()}}
    calc_e1: dict[str, str] = {}
    n_unidades = 0
    for to in TOS_TANDA0:
        for c in cargar_chunks(to):
            n_unidades += 1
            calc_e1[ar.k_e1(c)] = c["id"]
    out["unidades_e0_tanda0"] = n_unidades
    db1 = claves_db(DB_E1, ar.ns_e1)
    if db1 is None:
        out["e1"] = {"estado": "NO_VERIFICABLE", "motivo": "db de E1 ausente"}
    else:
        en_db = sum(1 for k in calc_e1 if k in db1)
        extra = db1 - set(calc_e1)
        # Las claves de la db que no salen del request base: se prueban contra
        # el request de la re-extracción dirigida (mismo request con max_tokens
        # de la dirigida; reextraccion_dirigida.json).
        dirigida = json.loads(DIRIGIDA.read_text(encoding="utf-8"))
        cap = {c["id"]: c for c in cargar_chunks("cap")}
        k_dir = {ar.k_e1(cap[cid], max_tokens=dirigida["max_tokens"]): cid
                 for cid in sorted(dirigida["casos"])}
        explicadas = sorted(k_dir[k] for k in extra if k in k_dir)
        out["e1"] = {
            "estado": "OK" if (en_db == n_unidades and len(extra) == len(explicadas))
            else "DISCREPANCIA",
            "claves_calculadas": len(calc_e1),
            "calculadas_presentes_en_db": en_db,
            "claves_db_en_namespace": len(db1),
            "claves_db_no_calculadas": len(extra),
            "explicadas_por_dirigida_max_tokens": {
                "max_tokens": dirigida["max_tokens"], "unidades": explicadas},
        }
    # E3: primera verificación de cada unidad aceptada por E1.
    import comun_e3
    calc_e3 = set()
    n_pares = 0
    for to in TOS_TANDA0:
        chunks = cargar_chunks(to)
        regs = comun_e3.cargar_extracciones(SALIDA_DIRIGIDA / to / "extracciones_e1_compact.jsonl")
        for c, v in comun_e3.pares_de(chunks, regs):
            n_pares += 1
            calc_e3.add(ar.k_e3(c, v))
    db3 = claves_db(DB_E3, ar.ns_e3)
    if db3 is None:
        out["e3"] = {"estado": "NO_VERIFICABLE", "motivo": "db de E3 ausente"}
    else:
        en_db3 = sum(1 for k in calc_e3 if k in db3)
        out["e3"] = {
            "estado": "OK" if en_db3 == n_pares == len(calc_e3) else "DISCREPANCIA",
            "pares_aceptados_e1": n_pares,
            "claves_calculadas": len(calc_e3),
            "calculadas_presentes_en_db": en_db3,
            "claves_db_en_namespace": len(db3),
            "nota": ("la db de E3 guarda también re-verificaciones del ratchet y "
                     "las corridas previas con el mismo namespace; solo se exige "
                     "que las claves calculadas estén"),
        }
    return out


def _jsonl_last_wins(p: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if p.exists():
        for linea in p.read_text(encoding="utf-8").splitlines():
            if linea.strip():
                r = json.loads(linea)
                out[r["chunk_id"]] = r
    return out


# R0 (enmienda 7 al protocolo entre tandas, §1.5): las 20 unidades de E3-01 recibieron en R0 su primera verificación con
# el E3 corregido (las filas de O3, sembradas en la db de E3). Sus claves salen de r0/esperados_r0.json, controlado por
# su sha256.
ESPERADOS_R0 = REX / "r0" / "esperados_r0.json"
ESPERADOS_R0_SHA256 = "81598c9704a1e66b53c501c7fff34ce1d9b71d20ae0b5a91548ecbf4aba8bfa6"


def claves_verificacion_r0() -> tuple[set[str], str | None]:
    """Las claves de `verificacion` de r0/esperados_r0.json y el sha256 del archivo (vacías y None si no está)."""
    if not ESPERADOS_R0.exists():
        return set(), None
    b = ESPERADOS_R0.read_bytes()
    return {v["clave"] for v in json.loads(b)["verificacion"].values()}, hashlib.sha256(b).hexdigest()


def regla_a3r(por_par: list[tuple[str, bool, str]], en_db: set[str], claves_r0: set[str]) -> dict:
    """La regla de A3r desde R0, sobre (unidad, es ítem, clave de E3) de cada par y las claves de la db: las 20 claves
    de R0 son de ítems de la tanda 0 y están en la db; las ausentes son, exactamente, los ítems que no son de R0.
    Cualquier otra ausencia o presencia es DISCREPANCIA."""
    items = sorted(cid for cid, es, _ in por_par if es)
    r0 = sorted(cid for cid, _, k in por_par if k in claves_r0)
    ausentes = sorted(cid for cid, _, k in por_par if k not in en_db)
    items_no_r0 = sorted(set(items) - set(r0))
    ok = (len(claves_r0) == 20 and len(r0) == 20 and set(r0) <= set(items) and claves_r0 <= en_db
          and ausentes == items_no_r0)
    return {"ok": ok, "items": items, "unidades_r0": r0, "ausentes": ausentes, "items_no_r0": items_no_r0,
            "no_items_ausentes": sorted(set(ausentes) - set(items)),
            "items_presentes": sorted(set(items) - set(ausentes)),
            "r0_ausentes": sorted(set(r0) & set(ausentes)),
            "items_no_r0_presentes": sorted(set(items_no_r0) - set(ausentes))}


def bloque_anclaje_r2b(ar: Armado, salida_r2b: Path) -> dict:
    """A1r y A3r. E1: la clave de cada unidad de la E0 r2b (con las partes por
    corte de la salida, si las hay) más las de los reintentos por corte, en el
    namespace del perfil, y las de los reintentos por forma, con el pedido del
    reintento (temperatura 1), en el suyo y, si hubo segundo, en -rforma2. E3: la
    primera verificación de cada unidad aceptada por E1. Sin la salida de
    U-REEXT-T0 el bloque queda NO_VERIFICABLE (decisión 3 de la autora): se
    informa igual cuántas claves tiene hoy el namespace r2b en la db."""
    import comun_e3
    import prompt_r2b
    ns_forma = ar.cliente_e1.namespace_e1(prefijo_hash=ar.pf.prefijo_hash_para_namespace,
                                          sufijo=ar.cliente_e1.SUFIJO_REINTENTO_FORMA)
    ns_forma2 = ar.cliente_e1.namespace_e1(prefijo_hash=ar.pf.prefijo_hash_para_namespace,
                                           sufijo=ar.cliente_e1.SUFIJO_REINTENTO_FORMA_2)
    out: dict = {"namespace_e1": ar.ns_e1, "namespace_e1_reintento_forma": ns_forma,
                 "namespace_e1_segundo_reintento_forma": ns_forma2,
                 "namespace_e3": ar.ns_e3, "prefijo_hash_e1": ar.pf.prefijo_hash,
                 "prefijo_hash_e3": ar.prompt_e3.PREFIJO_HASH,
                 "e0": _rel(E0_TANDA0_R2B), "salida_u_reext_t0": _rel(salida_r2b)}
    db1 = claves_db(DB_E1, ar.ns_e1)
    db1f = claves_db(DB_E1, ns_forma)
    db1f2 = claves_db(DB_E1, ns_forma2)
    out["claves_db_e1_en_namespace_r2b"] = None if db1 is None else len(db1)
    out["claves_db_e1_en_namespace_reintento_forma"] = None if db1f is None else len(db1f)
    out["claves_db_e1_en_namespace_segundo_reintento_forma"] = None if db1f2 is None else len(db1f2)
    if not salida_r2b.exists():
        motivo = ("no existe la salida de U-REEXT-T0: el anclaje del perfil r2b se corre cuando exista; "
                  "rige el del perfil sellado sobre las dbs de la tanda 0 (decisión 3 de la autora)")
        out["e1"] = {"estado": "NO_VERIFICABLE", "motivo": motivo}
        out["e3"] = {"estado": "NO_VERIFICABLE", "motivo": motivo}
        return out
    calc, calc_forma, calc_forma2, pares = set(), set(), set(), []
    n_unidades = 0
    for to in TOS_TANDA0:
        tdir = salida_r2b / to
        partes_p = tdir / "particiones_por_corte.json"
        partes = json.loads(partes_p.read_text(encoding="utf-8")) if partes_p.exists() else {}
        base = cargar_chunks(to, E0_TANDA0_R2B)
        con_partes = []
        for c in base:
            con_partes.extend(partes[c["id"]]["partes"] if c["id"] in partes else [c])
        por_id = {c["id"]: c for c in base + con_partes}
        regs = _jsonl_last_wins(tdir / "extracciones_e1.jsonl")
        for cid, r in regs.items():
            c = por_id.get(cid)
            if c is None:
                continue
            n_unidades += 1
            kw = ar.kw_e1(c)
            calc.add(ar.clave(ar.ns_e1, kw))
            techo = (r.get("reintento_corte") or {}).get("max_tokens_reintento")
            if techo:
                calc.add(ar.clave(ar.ns_e1, dict(kw, max_tokens=techo)))
            if "reintento_forma" in r:
                # U-REEXT-T0, T2-ter: el pedido del reintento como lo arma el runner (kwargs_reintento_forma): el que
                # produjo la salida, con su techo, y la temperatura del reintento de P5 (como R25); el segundo
                # reintento, el mismo pedido en el namespace -rforma2
                techo_f = (ar.cliente_e1.MAX_TOKENS_ESCALON_3_R2 if r.get("escalon_3") else techo)
                kwf = prompt_r2b.kwargs_reintento_forma_r2b(dict(kw, max_tokens=techo_f) if techo_f else kw)
                calc_forma.add(ar.clave(ns_forma, kwf))
                if "reintento_2" in r["reintento_forma"]:
                    calc_forma2.add(ar.clave(ns_forma2, kwf))
        compact = comun_e3.cargar_extracciones(tdir / "extracciones_e1_compact.jsonl") \
            if (tdir / "extracciones_e1_compact.jsonl").exists() else {}
        pares += comun_e3.pares_de(con_partes, compact)
    out["e1"] = {"estado": "OK" if db1 is not None and calc <= db1 and calc_forma <= (db1f or set())
                 and calc_forma2 <= (db1f2 or set()) else "DISCREPANCIA",
                 "registros_e1": n_unidades, "claves_calculadas": len(calc),
                 "calculadas_presentes_en_db": len(calc & (db1 or set())),
                 "claves_reintento_forma_calculadas": len(calc_forma),
                 "reintento_forma_presentes_en_db": len(calc_forma & (db1f or set())),
                 "claves_segundo_reintento_forma_calculadas": len(calc_forma2),
                 "segundo_reintento_forma_presentes_en_db": len(calc_forma2 & (db1f2 or set()))}
    db3 = claves_db(DB_E3, ar.ns_e3)
    # U-E3-LISTAS (D5, enmienda 1 al mandato): con la forma r2, el mensaje de E3 de un ítem de lista lleva el
    # bloque que abre la lista y la NOTA del ítem, así que su clave ya no es la de la tanda 0. A3r recomputa las
    # claves con el código vigente y exige que las de los no ítems estén en la db y que las ausentes sean
    # exactamente las de los ítems (prompt_r2b.es_item); cualquier otra ausencia o presencia es DISCREPANCIA.
    # R0 (enmienda 7 al protocolo entre tandas, §1.5): las 20 claves de R0 pasan a presentes (regla_a3r). Dos
    # variaciones de control sobre el conjunto de claves de la db tienen que dar DISCREPANCIA: una de las 20 ausente y
    # un ítem que no es de R0 presente (el primero de cada lista, en orden).
    por_par = [(c["id"], prompt_r2b.es_item(c), ar.k_e3(c, v)) for c, v in pares]
    calc3 = {k for _, _, k in por_par}
    en_db = db3 or set()
    claves_r0, sha_r0 = claves_verificacion_r0()
    a3r = regla_a3r(por_par, en_db, claves_r0)
    clave_de = {cid: k for cid, _, k in por_par}
    variaciones_a3r = []
    for vid, desc, cid, alterar in (
            ("A3r_v1", "una de las 20 claves de R0 ausente de la db", (a3r["unidades_r0"] or [None])[0],
             lambda db, k: db - {k}),
            ("A3r_v2", "la clave de un ítem que no es de R0 presente en la db", (a3r["items_no_r0"] or [None])[0],
             lambda db, k: db | {k})):
        obs = None if cid is None else ("OK" if regla_a3r(por_par, alterar(en_db, clave_de[cid]), claves_r0)["ok"]
                                        else "DISCREPANCIA")
        variaciones_a3r.append({"id": vid, "descripcion": desc, "unidad": cid, "esperado": "DISCREPANCIA",
                                "observado": obs, "ok": obs == "DISCREPANCIA"})
    ok3 = (db3 is not None and len(calc3) == len(pares) and sha_r0 == ESPERADOS_R0_SHA256 and a3r["ok"]
           and all(v["ok"] for v in variaciones_a3r))
    out["e3"] = {"estado": "OK" if ok3 else "DISCREPANCIA",
                 "regla": ("R0 (enmienda 7 al protocolo entre tandas, §1.5): presentes en la db las claves de E3 de "
                           "los no ítems y las 20 de R0 (verificacion de r0/esperados_r0.json); ausentes, exactamente, "
                           "las de los ítems (prompt_r2b.es_item) que no son de R0. Antes de R0, la de U-E3-LISTAS "
                           "(D5): ausentes, exactamente, los ítems"),
                 "pares_aceptados_e1": len(pares), "claves_calculadas": len(calc3),
                 "calculadas_presentes_en_db": len(calc3 & en_db),
                 "no_items": len(pares) - len(a3r["items"]), "items": len(a3r["items"]),
                 "esperados_r0": _rel(ESPERADOS_R0), "esperados_r0_sha256": sha_r0,
                 "esperados_r0_sha256_ok": sha_r0 == ESPERADOS_R0_SHA256,
                 "unidades_r0": a3r["unidades_r0"], "items_no_r0": len(a3r["items_no_r0"]),
                 "ausentes": len(a3r["ausentes"]), "no_items_ausentes": a3r["no_items_ausentes"],
                 "items_presentes": a3r["items_presentes"], "r0_ausentes": a3r["r0_ausentes"],
                 "items_no_r0_presentes": a3r["items_no_r0_presentes"],
                 "ausentes_listadas": a3r["ausentes"], "variaciones_de_control": variaciones_a3r}
    return out


# ------------------------------------------------------------------------- #
# B. Variaciones                                                             #
# ------------------------------------------------------------------------- #

def _primero(herencia: list[dict], prosa: bool) -> int | None:
    for i, h in enumerate(herencia):
        if (h["tipo"] != "encabezado") == prosa:
            return i
    return None


def _var_texto(c, v):
    c = copy.deepcopy(c)
    c["texto"] = c["texto"] + " [variación]"
    return c, v


def _var_herencia(prosa: bool):
    def f(c, v):
        i = _primero(c.get("herencia", []), prosa)
        if i is None:
            return None
        c = copy.deepcopy(c)
        c["herencia"][i]["texto"] = c["herencia"][i]["texto"] + " [variación]"
        return c, v
    return f


def _var_flags(c, v):
    c = copy.deepcopy(c)
    f = dict(c.get("flags") or {})
    f["contenido_tabular"] = not f.get("contenido_tabular")
    c["flags"] = f
    return c, v


def _var_paginas(c, v):
    c = copy.deepcopy(c)
    c["paginas"] = [p + 1 for p in c.get("paginas", [])]
    for h in c.get("herencia", []):
        h["paginas"] = [p + 1 for p in h.get("paginas", [])]
    return c, v


def _var_metadatos(c, v):
    c = copy.deepcopy(c)
    c["id"] = c["id"] + "__2"
    for k in ("sha256_propio", "sha256_completo"):
        if k in c:
            c[k] = "0" * 64
    for k in ("chars_propio", "chars_completo"):
        if k in c:
            c[k] = c[k] + 1
    return c, v


def _var_unidad(c, v):
    c = copy.deepcopy(c)
    vieja = c["unidad"]
    nueva = vieja + "9"
    c["unidad"] = nueva
    if c["texto"].startswith(vieja):
        c["texto"] = nueva + c["texto"][len(vieja):]
    return c, v


def _var_validacion(c, v):
    """Lo que haría una política por campo del validador: normalizar el valor
    de `tipo` de la primera entidad que lo tenga, o, si ninguna lo tiene,
    descartar la última relación."""
    if v is None:
        return None
    v = copy.deepcopy(v)
    for e in v.get("entidades", []):
        props = e.get("properties") or {}
        if "tipo" in props:
            props["tipo"] = "otra" if props["tipo"] != "otra" else "otra_2"
            return c, v
    if v.get("relaciones"):
        v["relaciones"] = v["relaciones"][:-1]
        return c, v
    return None


VARIACIONES_CHUNK = {
    # id: (descripción, transformación, E1 esperado, E3 esperado)
    "V01": ("texto propio de la unidad", _var_texto, True, True),
    "V02": ("texto de un bloque heredado de tipo encabezado", _var_herencia(False), True, True),
    "V03": ("texto de un bloque heredado de prosa (intro, cierre, chapeau, intersticial)",
            _var_herencia(True), True, False),
    "V04": ("marca de contenido tabular de E0 invertida, mismo texto", _var_flags, True, True),
    "V05": ("páginas de la unidad y de su herencia, mismo texto", _var_paginas, False, False),
    "V06": ("id, sha256 y conteos de caracteres de la unidad", _var_metadatos, False, False),
    "V07": ("número de la unidad (unidad y numeral del texto)", _var_unidad, True, True),
    "V18": ("salida validada de E1 alterada como lo haría una política por campo",
            _var_validacion, False, True),
}


def _toca_el_bloque_de_lista(c: dict, c2: dict, v: dict | None) -> bool:
    """U-E3-LISTAS: con la forma r2, la variación cambia el texto de algún bloque que abre la lista del ítem
    (comun_e3.indices_bloque_lista), que entra al fuente de E3."""
    if (v or {}).get("forma_salida") != "r2":
        return False
    her, her2 = c.get("herencia") or [], c2.get("herencia") or []
    return any(k >= len(her2) or her[k]["texto"] != her2[k]["texto"]
               for k in sys.modules["comun_e3"].indices_bloque_lista(c))


def correr_variaciones_chunk(ar: Armado, chunks, vals, base_e1, base_e3,
                             muestra: tuple = MUESTRA, variaciones: dict = VARIACIONES_CHUNK) -> list[dict]:
    res = []
    for vid, (desc, fn, esp1, esp3) in variaciones.items():
        aplica, cambia1, cambia3, esperadas3 = [], [], [], []
        for cid in muestra:
            r = fn(chunks[cid], vals[cid])
            if r is None:
                continue
            c2, v2 = r
            aplica.append(cid)
            if esp3 == "bloque_de_lista" and vals[cid] is not None and _toca_el_bloque_de_lista(chunks[cid], c2, v2):
                esperadas3.append(cid)
            if ar.k_e1(c2) != base_e1[cid]:
                cambia1.append(cid)
            if vals[cid] is not None and ar.k_e3(c2, v2) != base_e3[cid]:
                cambia3.append(cid)
        con_e3 = [c for c in aplica if vals[c] is not None]
        res.append(_registro(vid, desc, aplica,
                             esperado_e1=aplica if esp1 else [], cambia_e1=cambia1,
                             esperado_e3=(esperadas3 if esp3 == "bloque_de_lista" else con_e3 if esp3 else []),
                             cambia_e3=cambia3, universo_e3=con_e3))
    return res


def _registro(vid, desc, aplica, *, esperado_e1, cambia_e1, esperado_e3, cambia_e3,
              universo_e3=None, extra=None, e3_aplica=True) -> dict:
    ok1 = sorted(esperado_e1) == sorted(cambia_e1)
    ok3 = (sorted(esperado_e3) == sorted(cambia_e3)) if e3_aplica else True
    reg = {
        "id": vid, "descripcion": desc, "unidades_aplicables": sorted(aplica),
        "e1": {"esperadas_que_cambian": sorted(esperado_e1),
               "observadas_que_cambian": sorted(cambia_e1),
               "token": _token(esperado_e1, cambia_e1, ok1), "ok": ok1},
        "e3": ({"esperadas_que_cambian": sorted(esperado_e3),
                "observadas_que_cambian": sorted(cambia_e3),
                "universo": sorted(universo_e3 if universo_e3 is not None else aplica),
                "token": _token(esperado_e3, cambia_e3, ok3), "ok": ok3}
               if e3_aplica else {"token": "no aplica", "ok": True}),
    }
    if extra:
        reg["detalle"] = extra
    reg["ok"] = ok1 and ok3
    return reg


def _token(esperado, observado, ok) -> str:
    if not ok:
        return "DISCREPANCIA"
    return "cambia" if observado else "no cambia"


def variaciones_request(ar: Armado, chunks, vals, base_e1, base_e3) -> list[dict]:
    """Variaciones del request completo: prefijo, tool schema, catálogo en el
    bloque, modelo y parámetros, versión de código del namespace, prompt y
    modelo de E3, tabla TO→rol en memoria y cambio de solo código."""
    res = []
    todas = list(MUESTRA)
    con_e3 = [c for c in MUESTRA if vals[c] is not None]
    v3 = sys.modules["prompt_v3_b54"]

    def e1_con(mod_kw, ns_fn=None):
        cambia = []
        hashes = set()
        for cid in MUESTRA:
            kw = copy.deepcopy(ar.kw_e1(chunks[cid]))
            mod_kw(kw)
            ns = ns_fn(kw) if ns_fn else ar.ns_e1
            hashes.add(ns)
            if ar.clave(ns, kw) != base_e1[cid]:
                cambia.append(cid)
        return cambia, sorted(hashes)

    def ns_por_prefijo(kw):
        return ar.lc.make_namespace(ar.cliente_e1.DOMAIN,
                                    code_ver=f"{ar.cliente_e1.CODE_VER}-p{ar.hash_prefijo(kw)}",
                                    thinking=False)

    # V08 prefijo de E1 (texto del sistema), con el namespace recalculado.
    def m08(kw):
        kw["system"][0]["text"] = kw["system"][0]["text"] + "\n"
    c, ns = e1_con(m08, ns_por_prefijo)
    res.append(_registro("V08", "prefijo de E1: un salto de línea al final del texto de sistema",
                         todas, esperado_e1=todas, cambia_e1=c, esperado_e3=[], cambia_e3=[],
                         universo_e3=con_e3,
                         extra={"namespace_nuevo": ns, "namespace_base": ar.ns_e1}))

    # V09 tool schema de E1.
    def m09(kw):
        kw["tools"][0]["description"] = kw["tools"][0].get("description", "") + " "
    c, ns = e1_con(m09, ns_por_prefijo)
    res.append(_registro("V09", "tool schema de E1: un espacio al final de la descripción",
                         todas, esperado_e1=todas, cambia_e1=c, esperado_e3=[], cambia_e3=[],
                         universo_e3=con_e3, extra={"namespace_nuevo": ns}))

    # V10 catálogo en el bloque del prompt (texto) y en el enum del tool schema.
    def m10(kw):
        t = kw["system"][0]["text"]
        i = t.index(v3.ANCLA_FIN_BLOQUE)
        kw["system"][0]["text"] = t[:i] + "\nSujeto_variacion_selftest — Variación" + t[i:]
    c, ns = e1_con(m10, ns_por_prefijo)
    res.append(_registro("V10", "catálogo en el bloque del prompt: una línea de sujeto más",
                         todas, esperado_e1=todas, cambia_e1=c, esperado_e3=[], cambia_e3=[],
                         universo_e3=con_e3, extra={"namespace_nuevo": ns}))

    def m10b(kw):
        props = kw["tools"][0]["input_schema"]["properties"]["relations"]["items"]["properties"]
        props["sujeto_id"]["enum"] = props["sujeto_id"]["enum"] + ["Sujeto_variacion_selftest"]
    c, ns = e1_con(m10b, ns_por_prefijo)
    res.append(_registro("V10b", "catálogo en el enum `sujeto_id` del tool schema: un id más",
                         todas, esperado_e1=todas, cambia_e1=c, esperado_e3=[], cambia_e3=[],
                         universo_e3=con_e3, extra={"namespace_nuevo": ns}))

    # V11 tabla TO→rol (línea de alcance del mensaje de usuario), en memoria.
    import prompt_e1
    archivo = next(chunks[c]["archivo"] for c in MUESTRA if chunks[c]["to"] == TO_ROL_VARIADO)
    tablas = [prompt_e1.ROL_POR_TO, v3.ROL_POR_TO_V3]
    guardado = [copy.deepcopy(t.get(archivo)) for t in tablas]
    try:
        for t in tablas:
            if t.get(archivo) is not None:
                t[archivo]["miembros_labels"] = t[archivo]["miembros_labels"][:-1]
        c11 = [cid for cid in MUESTRA if ar.k_e1(chunks[cid]) != base_e1[cid]]
        c11_e3 = [cid for cid in con_e3 if ar.k_e3(chunks[cid], vals[cid]) != base_e3[cid]]
    finally:
        for t, g in zip(tablas, guardado):
            if g is not None:
                t[archivo] = g
    esperadas = [c for c in MUESTRA if chunks[c]["to"] == TO_ROL_VARIADO]
    res.append(_registro("V11", f"tabla TO→rol en memoria: un miembro menos en el rol de {TO_ROL_VARIADO}",
                         todas, esperado_e1=esperadas, cambia_e1=c11,
                         esperado_e3=[], cambia_e3=c11_e3, universo_e3=con_e3))

    # V12 modelo de E1; V13 max_tokens; V14 temperature.
    for vid, desc, mod in (
            ("V12", "modelo de E1", lambda kw: kw.__setitem__("model", kw["model"] + "-otro")),
            ("V13", "max_tokens de E1", lambda kw: kw.__setitem__("max_tokens", kw["max_tokens"] * 2)),
            ("V14", "temperature agregada al request de E1", lambda kw: kw.__setitem__("temperature", 0.0))):
        c, _ = e1_con(mod)
        res.append(_registro(vid, desc, todas, esperado_e1=todas, cambia_e1=c,
                             esperado_e3=[], cambia_e3=[], universo_e3=con_e3))

    # V15 versión de código del cliente (CODE_VER del namespace), request idéntico.
    ns15 = ar.lc.make_namespace(ar.cliente_e1.DOMAIN,
                                code_ver=f"{ar.cliente_e1.CODE_VER}-x-p{ar.pf.prefijo_hash}",
                                thinking=False)
    c = [cid for cid in MUESTRA if ar.clave(ns15, ar.kw_e1(chunks[cid])) != base_e1[cid]]
    res.append(_registro("V15", "CODE_VER del namespace de E1, mismo request", todas,
                         esperado_e1=todas, cambia_e1=c, esperado_e3=[], cambia_e3=[],
                         universo_e3=con_e3))

    # V16 prompt de E3 (con namespace recalculado); V17 modelo de E3.
    def e3_con(mod_kw, ns_fn=None):
        cambia = []
        for cid in con_e3:
            kw = copy.deepcopy(ar.kw_e3(chunks[cid], vals[cid]))
            mod_kw(kw)
            ns = ns_fn(kw) if ns_fn else ar.ns_e3
            if ar.clave(ns, kw) != base_e3[cid]:
                cambia.append(cid)
        return cambia

    def ns3(kw):
        return ar.lc.make_namespace(ar.cliente_e3.DOMAIN,
                                    code_ver=f"{ar.cliente_e3.CODE_VER}-p{ar.hash_prefijo(kw)}",
                                    thinking=False)

    def m16(kw):
        kw["system"][0]["text"] = kw["system"][0]["text"] + "\n"
    c3 = e3_con(m16, ns3)
    res.append(_registro("V16", "prompt de E3: un salto de línea al final del texto de sistema",
                         todas, esperado_e1=[], cambia_e1=[], esperado_e3=con_e3,
                         cambia_e3=c3, universo_e3=con_e3))
    c3 = e3_con(lambda kw: kw.__setitem__("model", kw["model"] + "-otro"))
    res.append(_registro("V17", "modelo de E3", todas, esperado_e1=[], cambia_e1=[],
                         esperado_e3=con_e3, cambia_e3=c3, universo_e3=con_e3))

    # V19 solo código: perfil sin vocabulario de validación ni labels de E2, y
    # los módulos posteriores a E3 reemplazados por funciones que fallan.
    pf_mod = dataclasses.replace(ar.pf, esquema=None, labels_catalogo={})
    sabotaje = {}
    for nombre in MODULOS_SOLO_CODIGO:
        mod = sys.modules.get(nombre)
        if mod is not None:
            sabotaje[nombre] = mod
        sys.modules[nombre] = None          # un import posterior fallaría
    try:
        c19 = [cid for cid in MUESTRA
               if ar.clave(ar.ns_e1, pf_mod.build_request_kwargs(chunks[cid], model=ar.model_e1))
               != base_e1[cid]]
        c19_e3 = [cid for cid in con_e3 if ar.k_e3(chunks[cid], vals[cid]) != base_e3[cid]]
    finally:
        for nombre in MODULOS_SOLO_CODIGO:
            if nombre in sabotaje:
                sys.modules[nombre] = sabotaje[nombre]
            else:
                sys.modules.pop(nombre, None)
    res.append(_registro("V19", "solo código: perfil sin vocabulario del validador ni labels de E2, "
                         "y módulos de validación, E2, ensamblado, E4 y esqueleto bloqueados",
                         todas, esperado_e1=[], cambia_e1=c19, esperado_e3=[], cambia_e3=c19_e3,
                         universo_e3=con_e3,
                         extra={"modulos_bloqueados": list(MODULOS_SOLO_CODIGO)}))
    return res


def variacion_to_nuevo(ar: Armado, vid: str = "V23") -> dict:
    """V23 (R23 con el perfil r2b): una unidad de un TO que la tanda 0 no
    tiene, armada con el mismo perfil, no está en la caché (miss); las claves
    de la muestra no dependen de qué otros TOs existan (cada request es función
    de una sola unidad)."""
    ch = {c["id"]: c for c in cargar_chunks(TO_NUEVO, PARTICION / TO_NUEVO)}
    c = ch[UNIDAD_TO_NUEVO]
    k = ar.k_e1(c)
    db1 = claves_db(DB_E1, ar.ns_e1)
    presente = None if db1 is None else (k in db1)
    reg = _registro(vid, f"unidad de un TO nuevo ({UNIDAD_TO_NUEVO}, partición b584)",
                    [UNIDAD_TO_NUEVO],
                    esperado_e1=[UNIDAD_TO_NUEVO],
                    cambia_e1=[UNIDAD_TO_NUEVO] if presente is False else [],
                    esperado_e3=[], cambia_e3=[], e3_aplica=False,
                    extra={"clave_en_cache_e1": presente,
                           "lectura": "cambia = la clave no está en la caché (miss)"})
    if presente is None:
        reg["e1"]["token"] = "NO_VERIFICABLE"
    return reg


def _renombrar_unidad(u: str, mapa: dict[str, str]) -> str:
    for viejo, nuevo in mapa.items():
        if u == viejo or u.startswith(viejo + "."):
            return nuevo + u[len(viejo):]
    return u


RE_NUMERAL = re.compile(r"^(\d+(?:\.\d+)*)")


def _renombrar_texto(t: str, mapa: dict[str, str]) -> str:
    m = RE_NUMERAL.match(t)
    if not m:
        return t
    return _renombrar_unidad(m.group(1), mapa) + t[m.end():]


def variacion_renumeracion(ar: Armado, vid: str = "V24", e0_dir: Path = E0_TANDA0, vals_de=None) -> dict:
    """V24 (R24 con el perfil r2b y su E0): se incorpora un punto nuevo antes de
    `insertar_antes_de` en un TO de la tanda 0; los hermanos siguientes y sus
    descendientes se renumeran (unidad, numeral del texto, unidad de origen y
    numeral de la herencia). Se cuentan las claves de E1 y E3 que cambian en
    todo el TO. `vals_de(chunks)`: validaciones por unidad (por defecto, las de
    E1 de la tanda 0)."""
    to, antes = RENUMERACION["to"], RENUMERACION["insertar_antes_de"]
    chunks = cargar_chunks(to, e0_dir)
    vals = cargar_validaciones(to) if vals_de is None else vals_de(chunks)
    padre, ultimo = antes.rsplit(".", 1)
    nivel = antes.count(".")
    hermanos = set()
    for c in chunks:
        for u in [c["unidad"]] + [h["unidad_origen"] for h in c.get("herencia", [])]:
            partes = u.split(".")
            if len(partes) > nivel and ".".join(partes[:nivel]) == padre:
                hermanos.add(".".join(partes[:nivel + 1]))
    renum = sorted((h for h in hermanos if int(h.rsplit(".", 1)[1]) >= int(ultimo)),
                   key=lambda h: int(h.rsplit(".", 1)[1]))
    mapa = {h: f"{padre}.{int(h.rsplit('.', 1)[1]) + 1}" for h in renum}

    def afectado(c):
        us = [c["unidad"]] + [h["unidad_origen"] for h in c.get("herencia", [])]
        return any(_renombrar_unidad(u, mapa) != u for u in us)

    cambia1, cambia3, esperado, esperado3 = [], [], [], []
    for c in chunks:
        c2 = copy.deepcopy(c)
        c2["unidad"] = _renombrar_unidad(c["unidad"], mapa)
        c2["texto"] = _renombrar_texto(c["texto"], mapa)
        for h in c2.get("herencia", []):
            h["unidad_origen"] = _renombrar_unidad(h["unidad_origen"], mapa)
            h["texto"] = _renombrar_texto(h["texto"], mapa)
        if afectado(c):
            esperado.append(c["id"])
            if c["id"] in vals:
                esperado3.append(c["id"])
        if ar.k_e1(c2) != ar.k_e1(c):
            cambia1.append(c["id"])
        if c["id"] in vals and ar.k_e3(c2, vals[c["id"]]) != ar.k_e3(c, vals[c["id"]]):
            cambia3.append(c["id"])
    return _registro(
        vid, f"punto nuevo antes de {to}::{antes}: renumeración de los hermanos siguientes "
             "y de sus descendientes", [c["id"] for c in chunks],
        esperado_e1=esperado, cambia_e1=cambia1, esperado_e3=esperado3, cambia_e3=cambia3,
        universo_e3=sorted(vals),
        extra={"to": to, "unidades_del_to": len(chunks), "puntos_renumerados": mapa,
               "unidades_afectadas_e1": len(esperado), "unidades_afectadas_e3": len(esperado3),
               "unidad_nueva": "1 (sin clave previa: miss)"})


# ------------------------------------------------------------------------- #
# B'. Variaciones del perfil r2b                                             #
# ------------------------------------------------------------------------- #

def _var_flags_r2(c, v):
    """Las marcas de contenido tabular de E0 invertidas: `contenido_tabular` y,
    si la unidad la trae, `contenido_tabular_residual` (prompt_r2b.residual)."""
    c = copy.deepcopy(c)
    f = dict(c.get("flags") or {})
    f["contenido_tabular"] = not f.get("contenido_tabular")
    if "contenido_tabular_residual" in f:
        f["contenido_tabular_residual"] = not f["contenido_tabular_residual"]
    c["flags"] = f
    return c, v


def _var_tabla_meta(c, v):
    """Metadatos de la primera tabla serializada de e0-r2: una fila de subtítulo más."""
    ts = (c.get("flags") or {}).get("tablas_e0") or []
    i = next((k for k, t in enumerate(ts) if t.get("serializada")), None)
    if i is None:
        return None
    c = copy.deepcopy(c)
    t = c["flags"]["tablas_e0"][i]
    t["filas_subtitulo"] = (t.get("filas_subtitulo") or 0) + 1
    return c, v


def _var_recorte(c, v):
    """El recorte de la herencia de e0-r2 (e0_lib.recortar_herencia) con un tope
    menor que el de TOPE_HERENCIA_E0_R2: U = 1 y B = 40 caracteres. Los
    encabezados quedan enteros (es la regla del recorte)."""
    her = c.get("herencia") or []
    if not any(h["tipo"] != "encabezado" for h in her):
        return None
    _ruta_e0()
    import e0_lib as E0
    nueva, decl = E0.recortar_herencia(copy.deepcopy(her), E0.lados_por_pagina(her, c.get("paginas") or []), 1, 40)
    if not decl:
        return None
    c = copy.deepcopy(c)
    c["herencia"] = nueva
    c["herencia_recortada"] = list(c.get("herencia_recortada") or []) + decl
    return c, v


VARIACIONES_CHUNK_R2B = {
    # id: (descripción, transformación, E1 esperado, E3 esperado)
    "R01": ("texto propio de la unidad", _var_texto, True, True),
    "R02": ("texto de un bloque heredado de tipo encabezado", _var_herencia(False), True, True),
    "R03": ("texto de un bloque heredado de prosa (intro, cierre, chapeau, intersticial)",
            _var_herencia(True), True, "bloque_de_lista"),
    "R04": ("marcas de contenido tabular de E0 invertidas (contenido_tabular y, si está, "
            "contenido_tabular_residual), mismo texto", _var_flags_r2, True, True),
    "R04b": ("metadatos de una tabla serializada por e0-r2: una fila de subtítulo más, mismo texto",
             _var_tabla_meta, True, True),
    "R05": ("páginas de la unidad y de su herencia, mismo texto", _var_paginas, False, False),
    "R06": ("id, sha256 y conteos de caracteres de la unidad", _var_metadatos, False, False),
    "R07": ("número de la unidad (unidad y numeral del texto)", _var_unidad, True, True),
    "R18": ("salida validada de E1 alterada como lo haría una política por campo",
            _var_validacion, False, True),
    "R27": ("recorte de la herencia de e0-r2 con un tope menor (U = 1, B = 40); encabezados enteros",
            _var_recorte, True, "bloque_de_lista"),
}


def variaciones_request_r2b(ar: Armado, chunks, vals, base_e1, base_e3) -> list[dict]:
    """Variaciones del request completo con el perfil r2b: prefijo, tool
    schema, catálogo en el bloque y en el enum, tabla TO→rol y derivado del
    registro de alcance por tanda en memoria, modelo y parámetros, techo del
    reintento por corte, versión de código del namespace, prompt y modelo de
    E3, solo código, reintento por forma, plantilla del mensaje de E1, NOTA del
    mensaje de E3 y aviso del reintento del ratchet."""
    res = []
    M = MUESTRA_R2B
    todas = list(M)
    con_e3 = [c for c in M if vals[c] is not None]
    R = sys.modules["prompt_r2b"]

    def e1_con(mod_kw, ns_fn=None):
        cambia, hashes = [], set()
        for cid in M:
            kw = copy.deepcopy(ar.kw_e1(chunks[cid]))
            mod_kw(kw)
            ns = ns_fn(kw) if ns_fn else ar.ns_e1
            hashes.add(ns)
            if ar.clave(ns, kw) != base_e1[cid]:
                cambia.append(cid)
        return cambia, sorted(hashes)

    def ns_por_prefijo(kw):
        return ar.lc.make_namespace(ar.cliente_e1.DOMAIN,
                                    code_ver=f"{ar.cliente_e1.CODE_VER}-p{ar.hash_prefijo(kw)}",
                                    thinking=False)

    def solo_e1(vid, desc, cambia, esperado=None, extra=None):
        return _registro(vid, desc, todas, esperado_e1=todas if esperado is None else esperado,
                         cambia_e1=cambia, esperado_e3=[], cambia_e3=[], universo_e3=con_e3, extra=extra)

    # R08 prefijo de E1 r2b (texto del sistema), con el namespace recalculado.
    def m08(kw):
        kw["system"][0]["text"] = kw["system"][0]["text"] + "\n"
    c, ns = e1_con(m08, ns_por_prefijo)
    res.append(solo_e1("R08", "prefijo de E1 r2b: un salto de línea al final del texto de sistema", c,
                       extra={"namespace_nuevo": ns, "namespace_base": ar.ns_e1}))

    # R09 tool schema de E1 r2b.
    def m09(kw):
        kw["tools"][0]["description"] = kw["tools"][0].get("description", "") + " "
    c, ns = e1_con(m09, ns_por_prefijo)
    res.append(solo_e1("R09", "tool schema de E1 r2b: un espacio al final de la descripción", c,
                       extra={"namespace_nuevo": ns}))

    # R10 catálogo en el bloque del prefijo r2b; R10b en el enum `sujeto_id`.
    def m10(kw):
        t = kw["system"][0]["text"]
        i = t.index(R.ANCLA_FIN_BLOQUE)
        kw["system"][0]["text"] = t[:i] + "\nSujeto_variacion_selftest — Variación" + t[i:]
    c, ns = e1_con(m10, ns_por_prefijo)
    res.append(solo_e1("R10", "catálogo en el bloque del prefijo r2b: una línea de sujeto más", c,
                       extra={"namespace_nuevo": ns}))

    def m10b(kw):
        props = kw["tools"][0]["input_schema"]["properties"]["relations"]["items"]["properties"]
        props["sujeto_id"]["enum"] = props["sujeto_id"]["enum"] + ["Sujeto_variacion_selftest"]
    c, ns = e1_con(m10b, ns_por_prefijo)
    res.append(solo_e1("R10b", "catálogo en el enum `sujeto_id` del tool schema r2b: un id más", c,
                       extra={"namespace_nuevo": ns}))

    # R11 tabla TO→rol del perfil (rol_por_to_r2.json ya cargado), en memoria:
    # sin pasar por su candado, que prueba R21.
    archivo = ARCHIVO_TO_ROL_VARIADO
    guardado = copy.deepcopy(R.ROL_POR_TO_R2[archivo])
    try:
        R.ROL_POR_TO_R2[archivo]["miembros_labels"] = R.ROL_POR_TO_R2[archivo]["miembros_labels"][:-1]
        c11 = [cid for cid in M if ar.k_e1(chunks[cid]) != base_e1[cid]]
        c11_e3 = [cid for cid in con_e3 if ar.k_e3(chunks[cid], vals[cid]) != base_e3[cid]]
    finally:
        R.ROL_POR_TO_R2[archivo] = guardado
    esperadas = [c for c in M if chunks[c]["archivo"] == archivo]
    res.append(_registro("R11", f"tabla TO→rol del perfil r2b en memoria: un miembro menos en el rol de "
                                f"{TO_ROL_VARIADO}", todas, esperado_e1=esperadas, cambia_e1=c11,
                         esperado_e3=[], cambia_e3=c11_e3, universo_e3=con_e3))

    # R34 derivado del registro de alcance por tanda (U-ALCANCE-E1, fila F13c; registro_alcance_r2b.json ya cargado), en
    # memoria y sin pasar por su candado: una entrada para el documento de la muestra que no tiene entrada en la tabla
    # de la release (docvig) le da la línea de alcance al mensaje de E1 de sus unidades, como F12.
    archivo34 = ARCHIVO_SIN_ROL_R34
    guardado34 = R.REGISTRO_ALCANCE_R2B
    sin_entrada = archivo34 not in R.ROL_POR_TO_R2 and archivo34 not in guardado34
    try:
        R.REGISTRO_ALCANCE_R2B = {**guardado34, archivo34: copy.deepcopy(guardado34[ENTRADA_DERIVADO_R34])}
        c34 = [cid for cid in M if ar.k_e1(chunks[cid]) != base_e1[cid]]
        c34_e3 = [cid for cid in con_e3 if ar.k_e3(chunks[cid], vals[cid]) != base_e3[cid]]
    finally:
        R.REGISTRO_ALCANCE_R2B = guardado34
    reg = _registro("R34", f"derivado del registro de alcance por tanda en memoria: una entrada (la de "
                           f"{ENTRADA_DERIVADO_R34}) para {archivo34}, sin entrada en la tabla de la release", todas,
                    esperado_e1=[c for c in M if chunks[c]["archivo"] == archivo34], cambia_e1=c34,
                    esperado_e3=[], cambia_e3=c34_e3, universo_e3=con_e3,
                    extra={"sin_entrada_en_la_release_ni_en_el_derivado": sin_entrada})
    reg["ok"] = reg["ok"] and sin_entrada
    res.append(reg)

    # R12 modelo de E1; R13 max_tokens del primer intento.
    for vid, desc, mod in (
            ("R12", "modelo de E1", lambda kw: kw.__setitem__("model", kw["model"] + "-otro")),
            ("R13", "max_tokens del primer intento de E1", lambda kw: kw.__setitem__("max_tokens", kw["max_tokens"] * 2))):
        c, _ = e1_con(mod)
        res.append(solo_e1(vid, desc, c))

    # R14 temperatura del pedido de E1 del perfil r2b (U-PROMPT-R2, P5; fila F08e): el pedido lleva
    # TEMPERATURA_E1_R2B; cambiarla mueve la clave de todas las unidades, y el pedido sin temperatura (el de P4 y P4b)
    # tiene otra clave.
    t0 = R.TEMPERATURA_E1_R2B
    c14, _ = e1_con(lambda kw: kw.__setitem__("temperature", t0 + 1))
    lleva = all(ar.kw_e1(chunks[cid]).get("temperature") == t0 for cid in M)
    sin_t = [cid for cid in M if ar.clave(ar.ns_e1, {k: v for k, v in ar.kw_e1(chunks[cid]).items()
                                                     if k != "temperature"}) != base_e1[cid]]
    reg = solo_e1("R14", f"temperatura del pedido de E1 del perfil r2b: {t0} → {t0 + 1}", c14,
                  extra={"temperatura_del_pedido": t0, "el_pedido_lleva_la_temperatura": lleva,
                         "sin_temperatura_cambia_la_clave": sorted(sin_t) == sorted(M)})
    reg["ok"] = reg["ok"] and lleva and sorted(sin_t) == sorted(M)
    res.append(reg)

    # R13b techo del reintento por corte del perfil r2 (cliente_e1.py:68): el
    # request del reintento cambia de clave con el techo; el del primer intento no.
    t_r2 = ar.cliente_e1.MAX_TOKENS_REINTENTO_CORTE_R2
    t_otro = ar.cliente_e1.MAX_TOKENS_REINTENTO_CORTE
    c13b, base_igual, distinto_del_base = [], True, True
    for cid in M:
        kw = ar.kw_e1(chunks[cid])
        k_r2 = ar.clave(ar.ns_e1, dict(kw, max_tokens=t_r2))
        if k_r2 != ar.clave(ar.ns_e1, dict(kw, max_tokens=t_otro)):
            c13b.append(cid)
        base_igual &= ar.clave(ar.ns_e1, kw) == base_e1[cid]
        distinto_del_base &= k_r2 != base_e1[cid]
    reg = solo_e1("R13b", f"techo del reintento por corte del perfil r2: {t_r2} → {t_otro}", c13b,
                  extra={"lectura": "cambia = la clave del request del reintento",
                         "clave_del_primer_intento_sin_cambio": base_igual,
                         "reintento_con_clave_distinta_del_primer_intento": distinto_del_base})
    reg["ok"] = reg["ok"] and base_igual and distinto_del_base
    res.append(reg)

    # R13c techo del tercer escalón del reintento por corte del perfil r2 (U-PROMPT-R2, P3c-2; cliente_e1,
    # MAX_TOKENS_ESCALON_3_R2): el request del tercer escalón cambia de clave con el techo; el del primer intento y el del
    # reintento, no.
    t3 = ar.cliente_e1.MAX_TOKENS_ESCALON_3_R2
    c13c, base_igual3, distinto3 = [], True, True
    for cid in M:
        kw = ar.kw_e1(chunks[cid])
        k3 = ar.clave(ar.ns_e1, dict(kw, max_tokens=t3))
        if k3 != ar.clave(ar.ns_e1, dict(kw, max_tokens=t3 + 1)):
            c13c.append(cid)
        base_igual3 &= ar.clave(ar.ns_e1, kw) == base_e1[cid]
        distinto3 &= k3 not in (base_e1[cid], ar.clave(ar.ns_e1, dict(kw, max_tokens=t_r2)))
    reg = solo_e1("R13c", f"techo del tercer escalón del reintento por corte del perfil r2: {t3} → {t3 + 1}", c13c,
                  extra={"lectura": "cambia = la clave del request del tercer escalón",
                         "clave_del_primer_intento_sin_cambio": base_igual3,
                         "tercer_escalon_con_clave_distinta_del_primer_intento_y_del_reintento": distinto3})
    reg["ok"] = reg["ok"] and base_igual3 and distinto3
    res.append(reg)

    # R15 versión de código del cliente (CODE_VER del namespace), request idéntico.
    ns15 = ar.lc.make_namespace(ar.cliente_e1.DOMAIN,
                                code_ver=f"{ar.cliente_e1.CODE_VER}-x-p{ar.pf.prefijo_hash}",
                                thinking=False)
    c = [cid for cid in M if ar.clave(ns15, ar.kw_e1(chunks[cid])) != base_e1[cid]]
    res.append(solo_e1("R15", "CODE_VER del namespace de E1, mismo request", c))

    # R16 prompt de E3 (con namespace recalculado); R17 modelo de E3.
    def e3_con(mod_kw, ns_fn=None):
        cambia = []
        for cid in con_e3:
            kw = copy.deepcopy(ar.kw_e3(chunks[cid], vals[cid]))
            mod_kw(kw)
            ns = ns_fn(kw) if ns_fn else ar.ns_e3
            if ar.clave(ns, kw) != base_e3[cid]:
                cambia.append(cid)
        return cambia

    def ns3(kw):
        return ar.lc.make_namespace(ar.cliente_e3.DOMAIN,
                                    code_ver=f"{ar.cliente_e3.CODE_VER}-p{ar.hash_prefijo(kw)}",
                                    thinking=False)

    def m16(kw):
        kw["system"][0]["text"] = kw["system"][0]["text"] + "\n"
    c3 = e3_con(m16, ns3)
    res.append(_registro("R16", "prompt de E3: un salto de línea al final del texto de sistema",
                         todas, esperado_e1=[], cambia_e1=[], esperado_e3=con_e3,
                         cambia_e3=c3, universo_e3=con_e3))
    c3 = e3_con(lambda kw: kw.__setitem__("model", kw["model"] + "-otro"))
    res.append(_registro("R17", "modelo de E3", todas, esperado_e1=[], cambia_e1=[],
                         esperado_e3=con_e3, cambia_e3=c3, universo_e3=con_e3))

    # R19 solo código: perfil sin vocabulario de validación ni labels de E2, y
    # los módulos posteriores al armado de los requests bloqueados.
    pf_mod = dataclasses.replace(ar.pf, esquema=None, labels_catalogo={})
    sabotaje = {}
    for nombre in MODULOS_SOLO_CODIGO_R2:
        mod = sys.modules.get(nombre)
        if mod is not None:
            sabotaje[nombre] = mod
        sys.modules[nombre] = None
    try:
        c19 = [cid for cid in M
               if ar.clave(ar.ns_e1, pf_mod.build_request_kwargs(chunks[cid], model=ar.model_e1)) != base_e1[cid]]
        c19_e3 = [cid for cid in con_e3 if ar.k_e3(chunks[cid], vals[cid]) != base_e3[cid]]
    finally:
        for nombre in MODULOS_SOLO_CODIGO_R2:
            if nombre in sabotaje:
                sys.modules[nombre] = sabotaje[nombre]
            else:
                sys.modules.pop(nombre, None)
    res.append(_registro("R19", "solo código: perfil sin vocabulario del validador ni labels de E2, y módulos "
                                "de validación, E2, ensamblado, umbrales, remisiones, E4 y esqueleto bloqueados",
                         todas, esperado_e1=[], cambia_e1=c19, esperado_e3=[], cambia_e3=c19_e3,
                         universo_e3=con_e3, extra={"modulos_bloqueados": list(MODULOS_SOLO_CODIGO_R2)}))

    # R25 reintento por salida mal formada (cliente_e1.py:76): el pedido del primer intento con la temperatura del
    # reintento (U-PROMPT-R2, P5: prompt_r2b.kwargs_reintento_forma_r2b), en el namespace con sufijo; con sufijo
    # vacío, el namespace de siempre.
    ns_f = ar.cliente_e1.namespace_e1(prefijo_hash=ar.pf.prefijo_hash_para_namespace,
                                      sufijo=ar.cliente_e1.SUFIJO_REINTENTO_FORMA)
    ns_0 = ar.cliente_e1.namespace_e1(prefijo_hash=ar.pf.prefijo_hash_para_namespace, sufijo="")
    c25, solo_temp, otra_que_mismo_pedido = [], True, True
    for cid in M:
        kw = ar.kw_e1(chunks[cid])
        kf = R.kwargs_reintento_forma_r2b(kw)
        if ar.clave(ns_f, kf) != base_e1[cid]:
            c25.append(cid)
        solo_temp &= (kf.get("temperature") == R.TEMPERATURA_REINTENTO_FORMA_R2B
                      and {k: v for k, v in kf.items() if k != "temperature"}
                      == {k: v for k, v in kw.items() if k != "temperature"}
                      and ar.clave(ar.ns_e1, kw) == base_e1[cid])
        otra_que_mismo_pedido &= ar.clave(ns_f, kf) != ar.clave(ns_f, kw)
    reg = solo_e1("R25", "reintento por salida mal formada: el pedido del primer intento con temperature "
                         f"{R.TEMPERATURA_REINTENTO_FORMA_R2B}, en el namespace del reintento", c25,
                  extra={"namespace_reintento_forma": ns_f,
                         "namespace_con_sufijo_vacio_igual_al_base": ns_0 == ar.ns_e1,
                         "difiere_del_primer_intento_solo_en_la_temperatura": solo_temp,
                         "clave_distinta_de_la_del_mismo_pedido_en_su_namespace": otra_que_mismo_pedido,
                         "lectura": "cambia = la clave del reintento no es la del primer intento"})
    reg["ok"] = reg["ok"] and ns_0 == ar.ns_e1 and solo_temp and otra_que_mismo_pedido
    res.append(reg)

    # R25b segundo reintento por salida mal formada (U-REEXT-T0, T2-bis; cliente_e1.SUFIJO_REINTENTO_FORMA_2): el
    # mismo pedido del reintento, en el namespace -rforma2; su clave no es la del primer intento ni la del reintento.
    ns_f2 = ar.cliente_e1.namespace_e1(prefijo_hash=ar.pf.prefijo_hash_para_namespace,
                                       sufijo=ar.cliente_e1.SUFIJO_REINTENTO_FORMA_2)
    c25b, distinta_del_reintento = [], True
    for cid in M:
        kf = R.kwargs_reintento_forma_r2b(ar.kw_e1(chunks[cid]))
        if ar.clave(ns_f2, kf) != base_e1[cid]:
            c25b.append(cid)
        distinta_del_reintento &= ar.clave(ns_f2, kf) != ar.clave(ns_f, kf)
    reg = solo_e1("R25b", "segundo reintento por salida mal formada: el pedido del reintento en el namespace "
                          "-rforma2", c25b,
                  extra={"namespace_segundo_reintento_forma": ns_f2,
                         "clave_distinta_de_la_del_reintento": distinta_del_reintento,
                         "lectura": "cambia = la clave del segundo reintento no es la del primer intento"})
    reg["ok"] = reg["ok"] and distinta_del_reintento and ns_f2 not in (ns_f, ar.ns_e1)
    res.append(reg)

    # R29, R29b y R30 (U-PROMPT-R2, P3c-2): con los candados de F22, F22b y F23, la línea del ítem, la de cierre y
    # la NOTA de las omisiones se varían editando el literal en una copia en memoria del módulo antes de
    # importarlo, en un proceso hijo (variaciones_json_r2b, EDICIONES_FUENTE_R2B): frenan.

    # R31 lazo de E3: el aviso del feedback del reintento (P3b, defensa 1). El
    # request del reintento del ratchet cambia; el primer intento de E1 y la
    # primera verificación de E3, no.
    import ratchet_e3
    aviso = ratchet_e3.AVISO_NOTA_REINTENTO

    def k_reintento(cid):
        c = chunks[cid]
        falt = [{"tipo": "otro", "cita_textual_del_fuente": c["texto"][:40], "ubicacion": c["unidad"],
                 "severidad": "alta", "nota": "faltante del selftest"}]
        kw = ratchet_e3.build_reextraccion_kwargs(c, falt, model=ar.model_e1, intento=1,
                                                  max_tokens_reintento=ar.constantes["MAX_TOKENS_REINTENTO"],
                                                  perfil=ar.pf)
        return ar.clave(ar.ns_e1, kw)
    antes = {cid: k_reintento(cid) for cid in M}
    try:
        ratchet_e3.AVISO_NOTA_REINTENTO = aviso + " "
        c31 = [cid for cid in M if k_reintento(cid) != antes[cid]]
        base31 = all(ar.k_e1(chunks[cid]) == base_e1[cid] for cid in M)
        c31_e3 = [cid for cid in con_e3 if ar.k_e3(chunks[cid], vals[cid]) != base_e3[cid]]
    finally:
        ratchet_e3.AVISO_NOTA_REINTENTO = aviso
    reg = _registro("R31", "lazo de E3: un espacio al final del aviso del feedback del reintento",
                    todas, esperado_e1=todas, cambia_e1=c31, esperado_e3=[], cambia_e3=c31_e3,
                    universo_e3=con_e3,
                    extra={"lectura": "cambia = la clave del request de re-extracción del ratchet",
                           "clave_del_primer_intento_sin_cambio": base31})
    reg["ok"] = reg["ok"] and base31
    res.append(reg)
    return res


def variacion_particion_r2b(ar: Armado) -> dict:
    """R26: la partición por corte (correr_e0.particionar_por_corte, perfil r2)
    de la unidad grande de la tanda 0 que se puede partir por ítems. Cada parte
    tiene su propia clave de E1 y de E3, distinta de la de la unidad entera y de
    las demás partes; la unidad entera conserva la suya."""
    _ruta_e0()
    import correr_e0
    c = {x["id"]: x for x in cargar_chunks(UNIDAD_PARTICION.split("::")[0], E0_TANDA0_R2B)}[UNIDAD_PARTICION]
    partes, info = correr_e0.particionar_por_corte(c)
    if not partes:
        reg = _registro("R26", f"partición por corte de {UNIDAD_PARTICION}", [UNIDAD_PARTICION],
                        esperado_e1=[], cambia_e1=[], esperado_e3=[], cambia_e3=[], extra={"informe": info})
        reg["e1"]["token"] = reg["e3"]["token"] = "NO_VERIFICABLE"
        return reg
    k_entera = ar.k_e1(c)
    v_entera = validacion_sintetica_r2(ar, c, False)
    k3_entera = ar.k_e3(c, v_entera) if v_entera is not None else None
    k1 = {p["id"]: ar.k_e1(p) for p in partes}
    vals = {p["id"]: validacion_sintetica_r2(ar, p, False) for p in partes}
    k3 = {pid: ar.k_e3(p, vals[pid]) for p in partes for pid in [p["id"]] if vals[pid] is not None}
    ids = [p["id"] for p in partes]
    cambia1 = [pid for pid in ids if k1[pid] != k_entera and list(k1.values()).count(k1[pid]) == 1]
    cambia3 = [pid for pid in k3 if k3[pid] != k3_entera and list(k3.values()).count(k3[pid]) == 1]
    return _registro("R26", f"partición por corte de {UNIDAD_PARTICION} en {len(partes)} partes", ids,
                     esperado_e1=ids, cambia_e1=cambia1, esperado_e3=sorted(k3), cambia_e3=cambia3,
                     universo_e3=sorted(k3),
                     extra={"informe": info, "lectura": "cambia = cada parte tiene clave propia (miss)",
                            "clave_de_la_unidad_entera_sin_cambio": ar.k_e1(c) == k_entera})


def _vals_sinteticas_to(ar: Armado):
    def f(chunks):
        out = {}
        for c in chunks:
            v = validacion_sintetica_r2(ar, c, False)
            if v is not None:
                out[c["id"]] = v
        return out
    return f


# ------------------------------------------------------------------------- #
# Proceso hijo: catálogos JSON alterados en memoria e inventario de insumos   #
# ------------------------------------------------------------------------- #

def _instalar_redireccion(redir: dict[str, str], leidos: set[str]) -> None:
    """Redirige la lectura de los JSON de `redir` a un contenido alterado en
    memoria y registra todo archivo abierto. No escribe nada."""
    abrir_orig = builtins.open
    path_open_orig = pathlib.Path.open

    def _servir(rp, mode):
        if "b" in mode:
            return io.BytesIO(redir[rp].encode("utf-8"))
        return io.StringIO(redir[rp])

    def _open(file, mode="r", *a, **k):
        try:
            rp = str(Path(os.fspath(file)).resolve())
        except TypeError:
            return abrir_orig(file, mode, *a, **k)
        leidos.add(rp)
        if rp in redir and "r" in mode:
            return _servir(rp, mode)
        return abrir_orig(file, mode, *a, **k)

    def _path_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        rp = str(self.resolve())
        leidos.add(rp)
        if rp in redir and "r" in mode:
            return _servir(rp, mode)
        return path_open_orig(self, mode, buffering, encoding, errors, newline)

    builtins.open = _open
    io.open = _open
    pathlib.Path.open = _path_open


def _alterar(variante: str) -> dict[str, str]:
    if variante == "V20":          # JSON del esqueleto y de E4: una clase más
        d = json.loads(JSON_V3.read_text(encoding="utf-8"))
        d["clases"].append({"id": "Sujeto_variacion_selftest", "label": "Variación",
                            "nivel": "clase", "padre": "Sujeto_sujeto", "disjunta_con": [],
                            "alias": [], "provenance": {"source_doc": "selftest",
                                                        "location": "selftest"}})
        return {str(JSON_V3.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante == "V21":          # JSON v2: un miembro menos en el rol de un TO de desarrollo
        d = json.loads(JSON_V2.read_text(encoding="utf-8"))
        cambiados = 0
        for r in d["roles"]:
            if r["to"].startswith("TO_clasificacion_deudores"):
                r["miembros"] = r["miembros"][:-1]
                cambiados += 1
        assert cambiados == 1, cambiados
        return {str(JSON_V2.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante in ("V22", "R22"):  # JSON v2: un alias más en una clase
        d = json.loads(JSON_V2.read_text(encoding="utf-8"))
        cl = next(c for c in d["clases"] if c["id"] == "Sujeto_entidad_financiera")
        cl["alias"] = list(cl.get("alias") or []) + ["variación del selftest"]
        return {str(JSON_V2.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante in ("inventario", "inventario_r2b", "R29", "R29b", "R30", "R33", "R33b"):  # editan una fuente, no un JSON
        return {}
    if variante == "R20":          # catálogo de resolución que lee el código: una entrada más en el índice de E4
        d = json.loads(INDICE_E4_R2.read_text(encoding="utf-8"))
        d.append(["alias_exacto", "variacion del selftest", "Sujeto_entidad_financiera"])
        return {str(INDICE_E4_R2.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante == "R21":          # rol_por_to_r2.json: un miembro menos en el rol de cla
        d = json.loads(ROL_POR_TO_R2.read_text(encoding="utf-8"))
        d[ARCHIVO_TO_ROL_VARIADO]["miembros_labels"] = d[ARCHIVO_TO_ROL_VARIADO]["miembros_labels"][:-1]
        return {str(ROL_POR_TO_R2.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante == "R22b":         # reemplazos anclados del prefijo r2b: una clave más
        d = json.loads(REEMPLAZOS_R2B.read_text(encoding="utf-8"))
        d["variacion_selftest"] = True
        return {str(REEMPLAZOS_R2B.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante == "R22c":         # catálogo de sujetos r2: un id más
        d = json.loads(CATALOGO_R2.read_text(encoding="utf-8"))
        nuevo = copy.deepcopy(d["sujetos"][0])
        nuevo["id"] = "Sujeto_variacion_selftest"
        d["sujetos"].append(nuevo)
        return {str(CATALOGO_R2.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante == "R22d":         # calibrador CAL-1 de E3: un espacio al final del texto de su unidad
        d = json.loads(CHUNKS_CALIBRADOR.read_text(encoding="utf-8"))
        n = 0
        for c in d:
            if c["id"] == UNIDAD_CALIBRADOR:
                c["texto"] = c["texto"] + " "
                n += 1
        assert n == 1, n
        return {str(CHUNKS_CALIBRADOR.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante == "R28":          # pies de cap: otra versión vigente
        d = json.loads(PIES_R2B.read_text(encoding="utf-8"))
        d["version_vigente"]["valor"] = d["version_vigente"]["valor"] + " (variación del selftest)"
        return {str(PIES_R2B.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    if variante == "R32":          # lista de tablas forzadas a residual: un alta
        d = json.loads(TABLAS_FORZADAS_R2B.read_text(encoding="utf-8"))
        d["tablas"].append({"tabla": tabla_forzada_r2b(), "motivo": "variación del selftest",
                            "fecha": "variación en memoria"})
        return {str(TABLAS_FORZADAS_R2B.resolve()): json.dumps(d, ensure_ascii=False, indent=1)}
    raise ValueError(variante)


def tabla_forzada_r2b() -> str:
    """Id de la primera tabla serializada de UNIDAD_TABLA_FORZADA en la E0 r2b."""
    c = {x["id"]: x for x in cargar_chunks(UNIDAD_TABLA_FORZADA.split("::")[0], E0_TANDA0_R2B)}[UNIDAD_TABLA_FORZADA]
    return next(t["tabla"] for t in c["flags"]["tablas_e0"] if t.get("serializada"))


VARIANTES_HIJO_R2B = ("inventario_r2b", "R20", "R21", "R22", "R22b", "R22c", "R22d", "R28", "R29", "R29b", "R30",
                      "R32", "R33", "R33b")
# U-PROMPT-R2, P3c-2: R29, R29b y R30 editan un literal del módulo (un espacio al final) en una copia en memoria de su
# fuente, que el proceso hijo importa en lugar del archivo: el candado del mensaje corre al importar y frena. No escribe.
EDICIONES_FUENTE_R2B = {
    "R29": ("prompt_r2b", REPO / "data/experiment/reextraccion_v2/e1_extractor/prompt_r2b.py",
            '"ENCABEZADO DE UNA LISTA):")', '"ENCABEZADO DE UNA LISTA): ")'),
    "R29b": ("prompt_r2b", REPO / "data/experiment/reextraccion_v2/e1_extractor/prompt_r2b.py",
             '(vacía si no omitiste nada).")', '(vacía si no omitiste nada). ")'),
    "R30": ("prompt_e3", REPO / "data/experiment/reextraccion_v2/e3_verificador/prompt_e3.py",
            '"meta-normativos.")', '"meta-normativos. ")'),
    # U-E3-LISTAS (fila F23b): la NOTA del ítem de una lista y la regla de los bloques contiguos (D2) del bloque que
    # abre la lista; con ítems en la fixture del candado del mensaje de E3, frenan.
    "R33": ("prompt_e3", REPO / "data/experiment/reextraccion_v2/e3_verificador/prompt_e3.py",
            'o en sus umbrales.")', 'o en sus umbrales. ")'),
    "R33b": ("comun_e3", REPO / "data/experiment/reextraccion_v2/e3_verificador/comun_e3.py",
             '    while (j > 0 and her[j - 1]["tipo"]', '    while (False and her[j - 1]["tipo"]'),
}


def _instalar_fuente_editada(variante: str) -> None:
    """Registra un buscador de módulos que sirve la fuente editada de EDICIONES_FUENTE_R2B[variante] en lugar del
    archivo: todo import de ese módulo ejecuta la copia editada (y su candado)."""
    import importlib.abc  # noqa: PLC0415
    import importlib.util  # noqa: PLC0415
    nombre, ruta, viejo, nuevo = EDICIONES_FUENTE_R2B[variante]
    src = ruta.read_text(encoding="utf-8")
    if src.count(viejo) != 1:
        raise SystemExit(f"{variante}: el literal a editar aparece {src.count(viejo)} veces en {ruta.name}")
    src = src.replace(viejo, nuevo)

    class _Fuente(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, fullname, path, target=None):
            return importlib.util.spec_from_loader(fullname, self, origin=str(ruta)) if fullname == nombre else None

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            module.__file__ = str(ruta)
            exec(compile(src, str(ruta), "exec"), module.__dict__)
    sys.meta_path.insert(0, _Fuente())


def _datos_del_repo(conj: set[str]) -> list[str]:
    repo = str(REPO.resolve())
    return sorted(os.path.relpath(p, repo) for p in conj
                  if p.startswith(repo) and "__pycache__" not in p
                  and "/.venv/" not in p and not p.endswith(".py"))


def _modulos_del_repo() -> set[str]:
    repo = str(REPO.resolve())
    return {os.path.relpath(str(Path(m.__file__).resolve()), repo)
            for m in list(sys.modules.values())
            if getattr(m, "__file__", None) and str(Path(m.__file__).resolve()).startswith(repo)
            and ".venv" not in m.__file__}


def main_hijo(variante: str) -> int:
    if variante in VARIANTES_HIJO_R2B:
        return main_hijo_r2b(variante)
    redir = _alterar(variante)
    leidos: set[str] = set()
    _instalar_redireccion(redir, leidos)
    out: dict = {"variante": variante}
    try:
        ar = Armado()
    except Exception as exc:  # noqa: BLE001 — se reporta: el candado frena
        out["estado"] = "frena"
        out["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
        return 0
    repo = str(REPO.resolve())

    def _datos(conj):
        return sorted(os.path.relpath(p, repo) for p in conj
                      if p.startswith(repo) and "__pycache__" not in p
                      and "/.venv/" not in p and not p.endswith(".py"))

    # Lo leído hasta acá es lo que construye los prefijos y el perfil (al
    # importar); lo que sigue es lo que se lee por unidad.
    al_construir = set(leidos)
    chunks, vals = cargar_muestra()
    out["estado"] = "armado"
    out["e1"] = {cid: ar.k_e1(chunks[cid]) for cid in MUESTRA}
    out["e3"] = {cid: ar.k_e3(chunks[cid], vals[cid]) for cid in MUESTRA if vals[cid] is not None}
    out["datos_leidos_al_construir_prefijos_y_perfil"] = _datos(al_construir)
    out["datos_leidos_por_unidad"] = _datos(leidos - al_construir)
    out["json_redirigido_leido"] = {os.path.relpath(p, repo): (p in leidos) for p in redir}
    modulos = sorted(
        os.path.relpath(str(Path(m.__file__).resolve()), repo)
        for m in list(sys.modules.values())
        if getattr(m, "__file__", None) and str(Path(m.__file__).resolve()).startswith(repo)
        and ".venv" not in m.__file__)
    out["modulos_del_repo_cargados"] = modulos
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


def main_hijo_r2b(variante: str) -> int:
    """Proceso hijo del perfil r2b: arma E1 y, aparte, E3, para distinguir un
    candado del perfil de E1 de uno del prefijo de E3. Registra los archivos
    de datos leídos en cada fase (muestra, perfil de E1, módulos de E3,
    validación de la salida sintética y armado de los requests) y los módulos
    del repo cargados al armar y al validar."""
    redir = _alterar(variante)
    leidos: set[str] = set()
    _instalar_redireccion(redir, leidos)
    if variante in EDICIONES_FUENTE_R2B:
        _instalar_fuente_editada(variante)
    out: dict = {"variante": variante}
    chunks = cargar_chunks_muestra_r2b()
    f_muestra = set(leidos)
    ar = None
    try:
        ar = Armado(PERFIL_R2B, con_e3=False)
        out["estado_e1"] = "armado"
        out["e1"] = {cid: ar.k_e1(chunks[cid]) for cid in MUESTRA_R2B}
    except Exception as exc:  # noqa: BLE001 — se reporta: el candado frena
        out["estado_e1"] = "frena"
        out["error_e1"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    f_e1 = set(leidos)
    mods_e1 = _modulos_del_repo()
    f_e3mod = f_val = f_req = f_e1
    mods_val = mods_req = mods_e1
    if ar is None:
        out["estado_e3"] = "frena"
        out["error_e3"] = "sin el perfil de E1 no hay salida validada de E1 en la forma r2"
    else:
        try:
            ar.cargar_e3()
            f_e3mod = set(leidos)
            mods_e3mod = _modulos_del_repo()
            vals = validaciones_muestra_r2b(ar, chunks)
            f_val = set(leidos)
            mods_val = _modulos_del_repo()
            out["e3"] = {cid: ar.k_e3(chunks[cid], vals[cid]) for cid in MUESTRA_R2B if vals[cid] is not None}
            f_req = set(leidos)
            mods_req = _modulos_del_repo()
            out["estado_e3"] = "armado"
            out["modulos_cargados_al_armar"] = sorted(mods_e3mod | (mods_req - mods_val))
            out["modulos_cargados_al_validar"] = sorted(mods_val - mods_e3mod)
        except Exception as exc:  # noqa: BLE001 — se reporta: el candado frena
            out["estado_e3"] = "frena"
            out["error_e3"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    repo = str(REPO.resolve())
    out["datos_leidos"] = {
        "al_cargar_la_muestra": _datos_del_repo(f_muestra),
        "al_construir_el_perfil_de_e1": _datos_del_repo(f_e1 - f_muestra),
        "al_importar_e3": _datos_del_repo(f_e3mod - f_e1),
        "al_validar_la_salida_de_e1": _datos_del_repo(f_val - f_e3mod),
        "al_armar_los_requests_de_e3": _datos_del_repo(f_req - f_val),
    }
    out["json_redirigido_leido"] = {os.path.relpath(p, repo): (p in leidos) for p in redir}
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    return 0


def correr_hijo(variante: str) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
                        "--hijo", variante], cwd=str(REPO), env=env,
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:
        return {"estado": "error_hijo", "stderr": r.stderr[-800:]}
    return json.loads(r.stdout.strip().splitlines()[-1])


def variaciones_json(base_e1, base_e3, vals) -> tuple[list[dict], dict]:
    res = []
    con_e3 = [c for c in MUESTRA if vals[c] is not None]
    inv = correr_hijo("inventario")
    # Control del hijo: sin alteración reproduce las claves del padre.
    ok_inv = inv.get("e1") == base_e1 and inv.get("e3") == {c: base_e3[c] for c in con_e3}
    for vid, desc, esp1, esp3 in (
            ("V20", "JSON del esqueleto y de E4 (esquema_v3_clases.json): una clase más",
             [], []),
            ("V21", "JSON v2 (esquema_v2_clases.json): un miembro menos en el rol de cla",
             [c for c in MUESTRA if c.startswith("cla::")], []),
            ("V22", "JSON v2 (esquema_v2_clases.json): un alias más en Sujeto_entidad_financiera",
             None, None)):
        h = correr_hijo(vid)
        if h.get("estado") == "frena":
            reg = {"id": vid, "descripcion": desc, "unidades_aplicables": list(MUESTRA),
                   "e1": {"token": "frena", "ok": esp1 is None, "error": h["error"]},
                   "e3": {"token": "no aplica", "ok": True}, "ok": esp1 is None}
        elif h.get("estado") == "armado":
            c1 = [c for c in MUESTRA if h["e1"][c] != base_e1[c]]
            c3 = [c for c in con_e3 if h["e3"][c] != base_e3[c]]
            reg = _registro(vid, desc, list(MUESTRA),
                            esperado_e1=esp1 if esp1 is not None else ["<frena>"],
                            cambia_e1=c1, esperado_e3=esp3 if esp3 is not None else [],
                            cambia_e3=c3, universo_e3=con_e3,
                            extra={"json_redirigido_leido": h["json_redirigido_leido"]})
        else:
            reg = {"id": vid, "descripcion": desc, "e1": {"token": "DISCREPANCIA", "ok": False},
                   "e3": {"token": "DISCREPANCIA", "ok": False}, "ok": False,
                   "detalle": h}
        res.append(reg)
    inventario = {
        "control_reproduce_claves_del_padre": ok_inv,
        "datos_leidos_al_construir_prefijos_y_perfil":
            inv.get("datos_leidos_al_construir_prefijos_y_perfil"),
        "datos_leidos_por_unidad": inv.get("datos_leidos_por_unidad"),
        "modulos_del_repo_cargados": inv.get("modulos_del_repo_cargados"),
    }
    # V19 (complemento): ningún módulo posterior a E3 se carga al armar.
    cargados = {Path(m).stem for m in inv.get("modulos_del_repo_cargados") or []}
    inventario["modulos_solo_codigo_cargados"] = sorted(cargados & set(MODULOS_SOLO_CODIGO))
    return res, inventario


def _lado(esperado, estado: str | None, base: dict, observado: dict | None, universo: list) -> dict:
    """Token de un lado (E1 o E3) de una variación del hijo r2b. `esperado`:
    "frena" o la lista de unidades que deben cambiar de clave."""
    if estado == "frena":
        ok = esperado == "frena"
        return {"esperado": esperado, "observado": "frena", "token": "frena" if ok else "DISCREPANCIA", "ok": ok}
    if estado != "armado" or observado is None:
        return {"esperado": esperado, "observado": estado, "token": "DISCREPANCIA", "ok": False}
    cambia = sorted(c for c in universo if observado.get(c) != base.get(c))
    if esperado == "frena":
        return {"esperado": "frena", "observadas_que_cambian": cambia, "token": "DISCREPANCIA", "ok": False}
    ok = sorted(esperado) == cambia
    return {"esperadas_que_cambian": sorted(esperado), "observadas_que_cambian": cambia,
            "universo": sorted(universo), "token": _token(esperado, cambia, ok), "ok": ok}


def variaciones_json_r2b(base_e1, base_e3, vals, chunks) -> tuple[list[dict], dict]:
    """R00 (control del hijo), R20, R21, R22, R22b, R22c, R22d, R28, R29, R29b, R30, R32, R33 y R33b."""
    M = list(MUESTRA_R2B)
    con_e3 = [c for c in M if vals[c] is not None]
    tabla = tabla_forzada_r2b()
    con_tabla = [c for c in M if any(t.get("tabla") == tabla and t.get("serializada")
                                     for t in (chunks[c].get("flags") or {}).get("tablas_e0") or [])]
    especificaciones = (
        ("R00", "control: sin alteración, otro proceso arma la misma clave", [], []),
        ("R20", "catálogo de resolución que lee solo el código (indice_e4_r2.json): una entrada más", [], []),
        ("R21", "rol_por_to_r2.json: un miembro menos en el rol de cla", "frena", "frena"),
        ("R22", "JSON v2 (esquema_v2_clases.json): un alias más en Sujeto_entidad_financiera", "frena", "frena"),
        ("R22b", "reemplazos anclados del prefijo r2b (prompt_r2b_reemplazos.json): una clave más", "frena", "frena"),
        ("R22c", "catálogo de sujetos r2 (catalogo_sujetos_r2.json): un id más", "frena", "frena"),
        ("R22d", f"calibrador CAL-1 de E3: un espacio al final del texto de {UNIDAD_CALIBRADOR} "
                 "(e0_chunking/salida/chunks_ric.json)", [], "frena"),
        ("R28", "pies de cap (pies_cap.json de la E0 r2b): otra versión vigente", [], []),
        ("R29", "mensaje de E1 r2b: un espacio al final de la línea del ítem de una lista (literal del módulo)",
         "frena", "frena"),
        ("R29b", "mensaje de E1 r2b: un espacio al final de la línea de cierre (literal del módulo)", "frena", "frena"),
        ("R30", "NOTA del mensaje de E3 de las omisiones de esquema: un espacio al final (literal del módulo)",
         [], "frena"),
        ("R32", f"lista de tablas forzadas a residual: alta de la tabla {tabla}", "frena", "frena"),
        ("R33", "NOTA del ítem de una lista en el mensaje de E3: un espacio al final (literal del módulo)", [],
         "frena"),
        ("R33b", "bloque que abre la lista en el fuente de E3: sin los bloques contiguos del mismo tipo y unidad "
                  "de origen (D2; literal de comun_e3)", [], "frena"),
    )
    res, inv = [], None
    for vid, desc, esp1, esp3 in especificaciones:
        h = correr_hijo("inventario_r2b" if vid == "R00" else vid)
        if vid == "R00":
            inv = h
        if h.get("estado") == "error_hijo":
            res.append({"id": vid, "descripcion": desc, "e1": {"token": "DISCREPANCIA", "ok": False},
                        "e3": {"token": "DISCREPANCIA", "ok": False}, "ok": False, "detalle": h})
            continue
        l1 = _lado(esp1, h.get("estado_e1"), base_e1, h.get("e1"), M)
        l3 = _lado(esp3, h.get("estado_e3"), base_e3, h.get("e3"), con_e3)
        reg = {"id": vid, "descripcion": desc, "unidades_aplicables": M, "e1": l1, "e3": l3,
               "ok": l1["ok"] and l3["ok"]}
        detalle = {k: h[k] for k in ("error_e1", "error_e3") if k in h}
        if h.get("json_redirigido_leido"):
            detalle["json_redirigido_leido"] = h["json_redirigido_leido"]
        if vid == "R32":
            detalle["tabla"] = tabla
        if detalle:
            reg["detalle"] = detalle
        res.append(reg)
    inv = inv or {}
    cargados = {Path(m).stem for m in inv.get("modulos_cargados_al_armar") or []}
    inventario = {
        "control_reproduce_claves_del_padre": inv.get("e1") == base_e1 and inv.get("e3") == base_e3,
        "datos_leidos": inv.get("datos_leidos"),
        "modulos_cargados_al_armar": inv.get("modulos_cargados_al_armar"),
        "modulos_cargados_al_validar": inv.get("modulos_cargados_al_validar"),
        "modulos_solo_codigo_cargados_al_armar": sorted(cargados & set(MODULOS_SOLO_CODIGO_R2)),
    }
    return res, inventario


# ------------------------------------------------------------------------- #
# C. Contraste con la tabla                                                  #
# ------------------------------------------------------------------------- #

COLUMNAS = ("fila", "cambio", "entra", "recomputa", "e1", "e3", "clase",
            "principio", "ancla", "variaciones")
# Ids que cita la columna de variaciones: las del perfil r2b (R..), y los
# anclajes del perfil sellado (A1, A3) y del perfil r2b (A1r, A3r).
RE_IDS_TABLA = re.compile(r"\bR\d{2}[a-z]?\b|\bA[13]r?\b")


def leer_tabla(md: Path) -> list[dict]:
    filas = []
    for linea in md.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\|\s*F\d{2}[a-z]?\s*\|", linea):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) != len(COLUMNAS):
            filas.append({"fila": celdas[0], "error": f"{len(celdas)} columnas"})
            continue
        filas.append(dict(zip(COLUMNAS, celdas)))
    return filas


def contraste(md: Path, variaciones: list[dict], anclajes: dict[str, dict]) -> dict:
    """Cada fila con sus variaciones del perfil r2b: el primer token de las
    celdas «Clave E1» y «Clave E3» tiene que coincidir con el de la variación.
    `anclajes`: id → bloque con «estado» (A1, A3 del perfil sellado; A1r, A3r
    del perfil r2b). Toda variación del perfil r2b tiene que tener fila."""
    if not md.exists():
        return {"estado": "PENDIENTE", "motivo": "tabla aún no escrita"}
    por_id = {v["id"]: v for v in variaciones}
    usados, filas_out, discrepancias = set(), [], []
    for f in leer_tabla(md):
        if "error" in f:
            discrepancias.append(f)
            continue
        ids = RE_IDS_TABLA.findall(f["variaciones"])
        if not ids:
            discrepancias.append({"fila": f["fila"], "motivo": "sin variación del selftest"})
        obs = []
        for i in ids:
            usados.add(i)
            if i in anclajes:
                est = anclajes[i]["estado"]
                obs.append({"variacion": i, "anclaje": est})
                if est == "DISCREPANCIA":
                    discrepancias.append({"fila": f["fila"], "variacion": i, "anclaje": est})
                continue
            v = por_id.get(i)
            if v is None:
                discrepancias.append({"fila": f["fila"], "variacion": i, "motivo": "no existe"})
                continue
            t1, t3 = v["e1"]["token"], v["e3"]["token"]
            # E3 «no aplica»: la variación no puede armar el request de E3 (no
            # hay salida de E1 previa); la fila se contrasta solo en E1.
            coincide = _norm(f["e1"]) == t1 and (t3 == "no aplica" or _norm(f["e3"]) == t3)
            obs.append({"variacion": i, "e1": t1, "e3": t3, "coincide": coincide})
            if not coincide or not v["ok"]:
                discrepancias.append({"fila": f["fila"], "variacion": i,
                                      "tabla": [f["e1"], f["e3"]], "selftest": [t1, t3]})
        filas_out.append({"fila": f["fila"], "tabla_e1": f["e1"], "tabla_e3": f["e3"],
                          "clase": f["clase"], "observado": obs})
    sin_fila = sorted(set(por_id) - usados)
    for i in sin_fila:
        discrepancias.append({"variacion": i, "motivo": "variación sin fila en la tabla"})
    return {"estado": "OK" if not discrepancias else "FRENO",
            "filas": filas_out, "discrepancias": discrepancias}


def _norm(celda: str) -> str:
    """Primer token de la celda de la tabla: `cambia`, `no cambia`, `frena`
    o `no aplica` (lo que sigue, entre paréntesis, es el alcance)."""
    c = celda.split("(")[0].strip().strip("*").strip().lower()
    return c


# ------------------------------------------------------------------------- #
# main                                                                       #
# ------------------------------------------------------------------------- #

def _imprimir(variaciones: list[dict]) -> None:
    for v in variaciones:
        print(f"{v['id']:5s} e1={v['e1']['token']:<14s} e3={v['e3']['token']:<14s} "
              f"{'OK ' if v['ok'] else 'MAL'} {v['descripcion']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hijo", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--salida-r2b", type=Path, default=SALIDA_R2B,
                    help="salida de U-REEXT-T0 para el anclaje del perfil r2b (por defecto corpus_tanda0/salida_r2b)")
    a = ap.parse_args()
    if a.hijo:
        return main_hijo(a.hijo)

    # Perfil sellado (v3_b54): los bloques de M1, sin cambios.
    ar = Armado()
    chunks, vals = cargar_muestra()
    base_e1 = {cid: ar.k_e1(chunks[cid]) for cid in MUESTRA}
    base_e3 = {cid: ar.k_e3(chunks[cid], vals[cid]) for cid in MUESTRA if vals[cid] is not None}

    anclaje = bloque_anclaje(ar)
    variaciones = correr_variaciones_chunk(ar, chunks, vals, base_e1, base_e3)
    variaciones += variaciones_request(ar, chunks, vals, base_e1, base_e3)
    vj, inventario = variaciones_json(base_e1, base_e3, vals)
    variaciones += vj
    variaciones.append(variacion_to_nuevo(ar))
    variaciones.append(variacion_renumeracion(ar))
    variaciones.sort(key=lambda v: v["id"])
    ok_inv = inventario["control_reproduce_claves_del_padre"] \
        and not inventario["modulos_solo_codigo_cargados"]

    # Perfil r2b.
    ar2 = Armado(PERFIL_R2B)
    chunks2 = cargar_chunks_muestra_r2b()
    vals2 = validaciones_muestra_r2b(ar2, chunks2)
    base2_e1 = {cid: ar2.k_e1(chunks2[cid]) for cid in MUESTRA_R2B}
    base2_e3 = {cid: ar2.k_e3(chunks2[cid], vals2[cid]) for cid in MUESTRA_R2B if vals2[cid] is not None}
    anclaje2 = bloque_anclaje_r2b(ar2, a.salida_r2b)
    var2 = correr_variaciones_chunk(ar2, chunks2, vals2, base2_e1, base2_e3,
                                    muestra=MUESTRA_R2B, variaciones=VARIACIONES_CHUNK_R2B)
    var2 += variaciones_request_r2b(ar2, chunks2, vals2, base2_e1, base2_e3)
    vj2, inventario2 = variaciones_json_r2b(base2_e1, base2_e3, vals2, chunks2)
    var2 += vj2
    var2.append(variacion_to_nuevo(ar2, vid="R23"))
    var2.append(variacion_renumeracion(ar2, vid="R24", e0_dir=E0_TANDA0_R2B, vals_de=_vals_sinteticas_to(ar2)))
    var2.append(variacion_particion_r2b(ar2))
    var2.sort(key=lambda v: (int(re.match(r"R(\d+)", v["id"]).group(1)), v["id"]))
    ok_inv2 = inventario2["control_reproduce_claves_del_padre"] \
        and not inventario2["modulos_solo_codigo_cargados_al_armar"]

    resultado = {
        "selftest": "U-MANT M1 y U-TABLA-REPROC — clave de caché de E1 y E3",
        "perfil_e1": PERFIL,
        "insumos": {
            "e0_tanda0": {to: sha256_archivo(E0_TANDA0 / f"chunks_{to}.json")
                          for to in TOS_TANDA0},
            "tabla_md_presente": TABLA_MD.exists(),
        },
        "muestra": {cid: {"tipo": chunks[cid]["tipo"],
                          "herencia": [h["tipo"] for h in chunks[cid].get("herencia", [])],
                          "flags_tabular": bool((chunks[cid].get("flags") or {}).get("contenido_tabular")),
                          "con_validacion_e1": vals[cid] is not None,
                          "clave_e1": base_e1[cid], "clave_e3": base_e3.get(cid)}
                    for cid in MUESTRA},
        "anclaje": anclaje,
        "inventario_del_armado": inventario,
        "variaciones": variaciones,
        "perfil_r2b": {
            "perfil_e1": PERFIL_R2B,
            "anclaje_declarado": ("el del perfil sellado (v3_b54) sobre las dbs de la tanda 0; el del perfil r2b "
                                  "queda NO_VERIFICABLE hasta que existan las dbs de U-REEXT-T0 (decisión 3 de la "
                                  "autora al firmar el mandato de U-TABLA-REPROC)"),
            "insumos": {"e0_tanda0_r2b": {to: sha256_archivo(E0_TANDA0_R2B / f"chunks_{to}.json")
                                          for to in TOS_TANDA0}},
            "muestra": {cid: {"tipo": chunks2[cid]["tipo"],
                              "herencia": [h["tipo"] for h in chunks2[cid].get("herencia", [])],
                              "tablas_serializadas": [t["tabla"] for t in (chunks2[cid].get("flags") or {}).get(
                                  "tablas_e0") or [] if t.get("serializada")],
                              "herencia_recortada": bool(chunks2[cid].get("herencia_recortada")),
                              "omision_sintetica": CON_OMISION_R2B[cid],
                              "con_validacion_sintetica": vals2[cid] is not None,
                              "clave_e1": base2_e1[cid], "clave_e3": base2_e3.get(cid)}
                        for cid in MUESTRA_R2B},
            "anclaje": anclaje2,
            "inventario_del_armado": inventario2,
            "variaciones": var2,
        },
    }
    anclajes = {"A1": anclaje["e1"], "A3": anclaje["e3"], "A1r": anclaje2["e1"], "A3r": anclaje2["e3"]}
    resultado["contraste_tabla"] = contraste(TABLA_MD, var2, anclajes)
    fallas = [v["id"] for v in variaciones + var2 if not v["ok"]]
    anclaje_ok = all(x["estado"] in ("OK", "NO_VERIFICABLE") for x in anclajes.values())
    resultado["veredicto"] = (
        "OK" if not fallas and anclaje_ok and ok_inv and ok_inv2
        and resultado["contraste_tabla"]["estado"] in ("OK", "PENDIENTE") else "FRENO")
    resultado["variaciones_con_discrepancia"] = fallas

    texto = json.dumps(resultado, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if a.out:
        Path(a.out).write_text(texto, encoding="utf-8")
    print("perfil sellado (v3_b54):")
    _imprimir(variaciones)
    print("anclaje e1:", anclaje["e1"].get("estado"), "| e3:", anclaje["e3"].get("estado"))
    print("inventario: hijo reproduce =", inventario["control_reproduce_claves_del_padre"],
          "| módulos solo-código cargados =", inventario["modulos_solo_codigo_cargados"])
    print("perfil r2b:")
    _imprimir(var2)
    print("anclaje r2b e1:", anclaje2["e1"].get("estado"), "| e3:", anclaje2["e3"].get("estado"),
          "| claves r2b en la db de E1:", anclaje2.get("claves_db_e1_en_namespace_r2b"))
    print("inventario r2b: hijo reproduce =", inventario2["control_reproduce_claves_del_padre"],
          "| módulos solo-código cargados al armar =", inventario2["modulos_solo_codigo_cargados_al_armar"])
    print("contraste con la tabla:", resultado["contraste_tabla"]["estado"])
    print("VEREDICTO:", resultado["veredicto"])
    return 0 if resultado["veredicto"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
