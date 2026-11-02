#!/usr/bin/env python3
"""ucita2_indicadores_banco.py — U-CITA-BANCO: el instrumento de exactitud de cita de U-CITA-2
(scripts/ucita2_indicadores.py) sobre las sesiones del banco MCP y sobre preguntas de una o dos anclas.

Lo que mide no cambia: los tres indicadores determinísticos por respuesta de U-CITA-2, sin juez ni API (USD 0). Cambia
solo la entrada. El script IMPORTA el instrumento de HEAD (candado de sha256) y, a través de él, `_cita_fiel` y
`_norm_loc` del harness congelado (ruta y sha256 verificados por `importar_harness`), sin editarlos.

Entrada:
  · por sesión, su meta (`meta_<id>.json`: `brazo`, `final_json_R4` con `citas`, `respondible`) y su log R1
    (`log_r1_<id>.jsonl`, en la misma carpeta: la salida íntegra, `output_str`, de cada llamada que recibió el agente);
  · las anclas por parámetro (`--anclas`: JSON {pregunta: ["to::punto", ...]}); la pregunta de una sesión sale de su
    id (`<etapa>-<pregunta>-<brazo>`, el esquema de a2_2/comun_a2_2.id_sesion) o de `--mapa-sesiones` ({sesión: pregunta});
  · la E0 de un grafo (`--e0`, con un `estructura_<to>.json` por TO) y su manifiesto de TOs (`--manifiesto`, con
    {"tos": [{"id", "archivo"}]}; sin él, se arma desde los campos `to` y `archivo` de los `estructura_<to>.json`).

La cita (texto «documento | punto», o el objeto {source_doc, location} del harness de EV2):
  · se parte en dos piezas por «|» (el texto, con las piezas sin blancos en los bordes; el objeto, tal cual);
  · el documento (el nombre del PDF o el id del TO) va a su TO por el manifiesto;
  · el punto se normaliza con la regla de HEAD (RE_PUNTO y RE_SECCION) más sus dos formas cortas: «Punto n», «n» y
    «n.» dan n; «Sección n» y «Sn» dan n (la E0 numera las secciones sin la «S»);
  · una sección cuyo número no es solo cifras (de letras, como «A», o «bloqueN») va con las mismas dos formas,
    «Sección A» y «SA», y se acepta solo si es una sección de ese mismo TO en la E0; si no, la cita es no parseable
    (así ninguna palabra que empiece con «S» se lee como sección). Las de cifras, como siempre;
  · lo que no se parte así es una cita no parseable: cuenta «no» en los indicadores 2 y 3, como hoy.

Lo visto: los pares (TO, punto) de cada salida del log R1, con un lector por formato, sacado del código de HEAD:
  · fragmentos (`buscar_pasajes`, mcp_vector/servidor_mcp_vector.py, `_fila`): los campos `to` y `unidad` de cada
    pasaje de `resultados`;
  · firma v1 (`buscar_nodos`, `ver_nodo`, `ver_vecinos`: harness.TOOLS, que sirve mcp_kg/servidor_mcp_kg.py): las
    procedencias {source_doc, location} que junta `GraphAgent._collect_provs` del harness, con el documento a su TO;
  · vistas del grafo (familias 1 a 5 de mcp_kg/familias_nav.py y `ver_descendientes` de familias_nav_cand.py): cada
    clave `to::unidad` que la salida muestra, llevada a su punto con `indice_puntos.base_punto`, salvo la que aparece
    solo en la cabecera (la primera línea, que repite lo que pidió el agente: el punto pedido, el id o los filtros).
    La clave de una sección que no es solo cifras («to::SA», «to::Sbloque2») cuenta solo si es una sección de ese TO
    en la E0. El punto pedido de `ver_punto` cuenta cuando la salida muestra su texto. En `ver_descendientes`, la
    clave de cada descendiente, que el formato imprime partida (el TO en la cabecera, la unidad en el bloque, con su
    texto). Las salidas de error de una herramienta («<herramienta>: no existe…», «herramienta desconocida: …») no
    muestran ningún punto: no aportan pares.
  Todo punto visto se normaliza con la misma regla que la cita; el que no se normaliza se conserva tal cual.

Indicadores (valores "si" | "no" | "sin_citas" | "sin_json", y "fuera_de_indice" en el 2, con la precedencia de HEAD):
  1. cita fundada: TODA cita de la respuesta es fiel a algún par visto con `_cita_fiel` tal cual (mismo TO y punto
     igual bajo `_norm_loc`, con la regla del prefijo de 40 caracteres). Cada cita se compara con su punto normalizado
     y con su ubicación tal cual; cada par visto entra con las dos formas. La comparación tal cual conserva la de HEAD
     para las citas no parseables (comillas, blancos, «(parte N)», vista truncada).
  2. cita existente: igual que hoy, contra la E0 (`resolver_en_indice` de HEAD).
  3. cita al ancla: principal, ALGUNA cita va a ALGUNA de las anclas (su TO, y su punto o uno que
     empieza con él seguido de «.»: `es_ancla_o_descendiente` de HEAD); informativa, CADA ancla tiene al menos una
     cita, en una columna aparte que no entra en ninguna comparación. Con un ancla las dos dan lo mismo que el
     indicador de hoy. Cada ancla trae su TO: el script no aborta si son de TOs distintos.

Agregación: fracción cruda «n de N», por brazo (todas / contenido / abstención), sin porcentajes ni intervalos.
Salida: un JSON por corrida (`--out-json`), sin texto de citas ni de preguntas, sin timestamps.

Uso (desde la raíz del repo o de una copia):
  PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ucita2_indicadores_banco.py --selftest
  PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ucita2_indicadores_banco.py --sesiones DIR [DIR ...] \\
      --anclas anclas.json --e0 DIR [--manifiesto RUTA] [--mapa-sesiones RUTA] --out-json RUTA
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO / "scripts"
BANCO_DIR = REPO / "data" / "experiment" / "banco_mcp"
MCP_KG_DIR = BANCO_DIR / "mcp_kg"
MCP_VECTOR_DIR = BANCO_DIR / "mcp_vector"
for _p in (str(SCRIPTS_DIR), str(BANCO_DIR), str(MCP_KG_DIR), str(MCP_VECTOR_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ucita2_indicadores as U2  # noqa: E402  (instrumento de HEAD: solo import)
import indice_puntos as IP  # noqa: E402  (base_punto: solo import)
import familias_nav_cand as FNC  # noqa: E402  (nombres de las herramientas de navegación: solo import)

# Candado del instrumento de HEAD (scripts/ucita2_indicadores.py en 43b4df8f). El del harness lo verifica
# U2.importar_harness.
SHA_UCITA2_HEAD = "5379c2f201643947777be5a061e270bf3a2528b82b900dc5f4041747b9d53572"

SI, NO, SIN_CITAS, SIN_JSON, FUERA = U2.SI, U2.NO, U2.SIN_CITAS, U2.SIN_JSON, U2.FUERA
VALORES = U2.VALORES
INDICADORES = (
    ("ind1_cita_fundada", "1 · cita fundada"),
    ("ind2_cita_existente", "2 · cita existente (índice E0)"),
    ("ind3_cita_al_ancla", "3 · cita al ancla (principal: alguna cita a alguna ancla)"),
    ("info_cada_ancla_con_cita", "informativa · cada ancla con al menos una cita (no entra en comparaciones)"),
)
GRUPOS = U2.GRUPOS

# Formas del punto: las dos de HEAD y sus formas cortas.
RE_NUMERO = re.compile(r"^(\d+(?:\.\d+)*)\.?$")
RE_S = re.compile(r"^S(\d+)$")
FORMAS_PUNTO = (("Punto n", U2.RE_PUNTO), ("Sección n", U2.RE_SECCION), ("n", RE_NUMERO), ("Sn", RE_S))
# Las mismas dos formas de sección con un número que no es solo cifras («Sección A», «SA», «Sbloque2»): el número
# vale solo si es una sección de ese mismo TO en la E0.
FORMAS_SECCION_E0 = (("Sección n", re.compile(r"^Sección (\S+)$")), ("Sn", re.compile(r"^S(\S+)$")))
PDF, ID_TO, OTRA = "PDF", "id del TO", "otra forma"

# Lectores.
TOOLS_FRAGMENTOS = ("buscar_pasajes",)
TOOLS_NAV = tuple(t["name"] for t in FNC.TOOLS_NAV_CAND)
# Una clave de punto como la imprimen las vistas: `to::unidad`, con la unidad como la numera la E0 (`5.12`, `S5`,
# `SA` o `Sbloque2` para una sección, `A2::3.1` dentro de un subdocumento) y, opcional, un bloque del punto
# (`::intro`, `::parteN`, …), que indice_puntos.base_punto quita. El grupo 1 es el TO; el 2, el número de una sección
# que no es solo cifras (vale solo si es una sección de ese TO en la E0).
RE_CLAVE_PUNTO = re.compile(r"(?<![\w:])([a-z][a-z0-9_]*)::(?:[A-Z][A-Za-z0-9]*::)?"
                            r"(?:S?\d+(?:\.\d+)*|S([A-Za-z]\w*(?:\.\d+)*))"
                            r"(?:::(?:" + "|".join(IP.BLOQUES) + r"|parte\d+))?(?![\w:])")
RE_CABEZA_VP = re.compile(r"^ver_punto (\S+) — ")
RE_TEXTO_VP = re.compile(r"^Texto \(\d+ caracteres\):$")
RE_CABEZA_DESC = re.compile(r"^ver_descendientes (\S+) · ")
RE_BLOQUE_DESC = re.compile(r"^#\d+ · (\S+) · ")


# --------------------------------------------------------------------------- #
# Integridad                                                                   #
# --------------------------------------------------------------------------- #
def sha256_file(p: Path) -> str:
    return U2.sha256_file(p)


def sha256_texto(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def ruta_legible(p: Path) -> str:
    """Relativa al repo cuando está adentro; si no, bajo la carpeta del usuario como «~/…»; si no, absoluta."""
    r = Path(p).resolve()
    for base, pre in ((REPO, ""), (Path.home().resolve(), "~/")):
        try:
            return pre + str(r.relative_to(base))
        except ValueError:
            pass
    return str(r)


def verificar_instrumento_head() -> dict:
    real = Path(U2.__file__).resolve()
    if real != (SCRIPTS_DIR / "ucita2_indicadores.py").resolve():
        raise SystemExit(f"ABORTO: se importó otro instrumento: {real}")
    obtenido = sha256_file(real)
    if obtenido != SHA_UCITA2_HEAD:
        raise SystemExit(f"ABORTO: scripts/ucita2_indicadores.py no es el de HEAD (sha256 {obtenido})")
    return {"ruta": "scripts/ucita2_indicadores.py", "sha256": obtenido, "sha256_esperado": SHA_UCITA2_HEAD}


def importar_harness_y_lector_v1():
    """_cita_fiel y _norm_loc por el instrumento de HEAD (verifica ruta y sha256 del harness); del mismo módulo,
    ya importado, `GraphAgent._collect_provs` y los nombres de harness.TOOLS."""
    cita_fiel, norm_loc = U2.importar_harness()
    harness = sys.modules["harness"]
    return cita_fiel, norm_loc, harness.GraphAgent._collect_provs, tuple(t["name"] for t in harness.TOOLS)


# --------------------------------------------------------------------------- #
# Manifiesto, E0 y anclas                                                      #
# --------------------------------------------------------------------------- #
def armar_manifiesto(tos: list, secciones: dict | None = None) -> dict:
    """tos = [{"id", "archivo"}]. El documento de una cita va a su TO por el archivo o por el id. `secciones`:
    {to: números de sus secciones en la E0}, para las secciones que no son solo cifras."""
    ids = {t["id"] for t in tos}
    archivos = {t["archivo"] for t in tos}
    if len(ids) != len(tos) or len(archivos) != len(tos) or ids & archivos:
        raise SystemExit("ABORTO: manifiesto con ids o archivos repetidos, o con un archivo igual a un id")
    doc2to = {t["archivo"]: t["id"] for t in tos} | {t["id"]: t["id"] for t in tos}
    return {"tos": tuple(sorted(ids)), "ids": ids, "archivos": archivos, "doc2to": doc2to,
            "to2doc": {t["id"]: t["archivo"] for t in tos},
            "secciones": {to: frozenset((secciones or {}).get(to, ())) for to in sorted(ids)}}


def secciones_de_estructura(e: dict) -> frozenset:
    """Los `numero` de los nodos de tipo «seccion» de un estructura_<to>.json (secciones → hijos, como
    U2.cargar_indice), tal como los numera la E0."""
    out = set()

    def rec(n):
        if n.get("tipo") == "seccion":
            out.add(str(n.get("numero")))
        for h in n.get("hijos") or []:
            rec(h)

    for s in e.get("secciones") or []:
        rec(s)
    return frozenset(out)


def secciones_e0(e0_dir: Path, tos) -> dict:
    """{to: números de sus secciones}, de los estructura_<to>.json de una E0."""
    return {to: secciones_de_estructura(json.loads((e0_dir / f"estructura_{to}.json").read_text(encoding="utf-8")))
            for to in tos}


def secciones_del(man: dict, to) -> frozenset:
    return man["secciones"].get(to, frozenset())


def manifiesto_desde(manifiesto_path: Path | None, e0_dir: Path) -> dict:
    if manifiesto_path is not None:
        m = json.loads(manifiesto_path.read_text(encoding="utf-8"))
        tos = [{"id": t["id"], "archivo": t["archivo"]} for t in m["tos"]]
        return armar_manifiesto(tos, secciones_e0(e0_dir, [t["id"] for t in tos]))
    tos, secciones = [], {}
    for p in sorted(e0_dir.glob("estructura_*.json")):
        e = json.loads(p.read_text(encoding="utf-8"))
        if p.stem != f"estructura_{e.get('to')}":
            raise SystemExit(f"ABORTO: {p.name} declara to={e.get('to')!r}")
        tos.append({"id": e["to"], "archivo": e["archivo"]})
        secciones[e["to"]] = secciones_de_estructura(e)
    if not tos:
        raise SystemExit(f"ABORTO: {e0_dir} no tiene estructura_<to>.json")
    return armar_manifiesto(tos, secciones)


def cargar_indices(man: dict, e0_dir: Path) -> dict:
    indices = {}
    for to in man["tos"]:
        idx = U2.cargar_indice(e0_dir / f"estructura_{to}.json")
        if idx["archivo"] != man["to2doc"][to] or idx["to"] != to:
            raise SystemExit(f"ABORTO: índice E0 de {to} no coincide con el manifiesto")
        indices[to] = idx
    return indices


def normalizar_punto(s, secciones: frozenset = frozenset()) -> tuple:
    """(punto normalizado o None, forma). La regla de HEAD (RE_PUNTO, RE_SECCION) más «n», «n.» y «Sn»; una sección
    que no es solo cifras («Sección A», «SA», «Sbloque2») da su número solo si está en `secciones` (las de su TO en la
    E0)."""
    if not isinstance(s, str):
        return None, OTRA
    for forma, rx in FORMAS_PUNTO:
        m = rx.match(s)
        if m:
            return m.group(1), forma
    for forma, rx in FORMAS_SECCION_E0:
        m = rx.match(s)
        if m and m.group(1) in secciones:
            return m.group(1), forma
    return None, OTRA


def parsear_anclas(crudas: dict, man: dict) -> dict:
    """{pregunta: [{"ancla", "to", "punto"}]}: cada «to::punto», con el punto normalizado como el de una cita."""
    out = {}
    for q, lista in crudas.items():
        if not isinstance(lista, list) or not lista:
            raise SystemExit(f"ABORTO: la pregunta {q} no trae una lista de anclas")
        anclas = []
        for i, a in enumerate(lista):
            to, sep, punto = a.partition("::") if isinstance(a, str) else ("", "", "")
            norm, _ = normalizar_punto(punto, secciones_del(man, to))
            if not sep or to not in man["ids"] or norm is None:
                raise SystemExit(f"ABORTO: la pregunta {q}, ancla {i}, no tiene la forma «to::punto» con un TO "
                                 "del manifiesto y un punto normalizable")
            anclas.append({"ancla": a, "to": to, "punto": norm})
        out[q] = anclas
    return out


def verificar_anclas(anclas: dict, indices: dict) -> dict:
    """Cuántas anclas resuelven en el índice E0 de su TO; las que no, por (pregunta, posición), sin su texto."""
    no, total = [], 0
    for q in sorted(anclas):
        for i, a in enumerate(anclas[q]):
            total += 1
            if a["punto"] not in indices[a["to"]]["numeros"]:
                no.append({"pregunta": q, "posicion": i})
    return {"resueltas": total - len(no), "total": total, "no_resueltas": no}


# --------------------------------------------------------------------------- #
# La cita                                                                      #
# --------------------------------------------------------------------------- #
def partir_cita(c, man: dict) -> dict:
    if isinstance(c, str):
        piezas = c.split("|")
        if len(piezas) != 2:
            return {"forma_cita": "texto", "doc": None, "loc": None, "forma_doc": None, "forma_punto": None,
                    "to": None, "punto": None, "parseable": False, "motivo": "no_se_parte_en_dos_piezas"}
        doc, loc = piezas[0].strip(), piezas[1].strip()
        forma_cita = "texto"
    elif isinstance(c, dict):
        doc, loc = c.get("source_doc"), c.get("location")
        forma_cita = "objeto"
        if not isinstance(doc, str) or not isinstance(loc, str):
            return {"forma_cita": forma_cita, "doc": None, "loc": None, "forma_doc": None, "forma_punto": None,
                    "to": None, "punto": None, "parseable": False, "motivo": "objeto_sin_source_doc_o_location"}
    else:
        return {"forma_cita": "otra", "doc": None, "loc": None, "forma_doc": None, "forma_punto": None,
                "to": None, "punto": None, "parseable": False, "motivo": "cita_no_es_texto_ni_objeto"}
    forma_doc = PDF if doc in man["archivos"] else ID_TO if doc in man["ids"] else OTRA
    to = man["doc2to"].get(doc)
    punto, forma_punto = normalizar_punto(loc, secciones_del(man, to))
    parseable = to is not None and punto is not None
    motivo = None if parseable else ("documento_sin_to_en_manifiesto" if to is None else "punto_no_normalizable")
    return {"forma_cita": forma_cita, "doc": doc, "loc": loc, "forma_doc": forma_doc, "forma_punto": forma_punto,
            "to": to, "punto": punto, "parseable": parseable, "motivo": motivo}


def etiqueta_forma(p: dict) -> str:
    if p["forma_doc"] is None:
        return f"{p['forma_cita']}: {OTRA}"
    pre = "" if p["forma_cita"] == "texto" else f"{p['forma_cita']}: "
    return f"{pre}{p['forma_doc']} | {p['forma_punto']}"


def claves_cita(p: dict) -> list:
    """Las claves {source_doc, location} con que la cita se compara: su TO (o el documento tal cual, si no va a
    ningún TO) con su punto normalizado y con su ubicación tal cual."""
    if p["doc"] is None:
        return []
    doc = p["to"] if p["to"] is not None else p["doc"]
    out = [{"source_doc": doc, "location": p["punto"]}] if p["punto"] is not None else []
    return out + [{"source_doc": doc, "location": p["loc"]}]


def claves_vistas(pares: list, man: dict) -> list:
    """Cada par visto (TO o documento, ubicación tal cual) entra con su punto normalizado y tal cual."""
    out, ya = [], set()
    for doc, loc in pares:
        norm, _ = normalizar_punto(loc, secciones_del(man, doc))
        for k in ((doc, norm), (doc, loc)):
            if k[1] is not None and k not in ya:
                ya.add(k)
                out.append({"source_doc": k[0], "location": k[1]})
    return out


def pares_normalizados(pares: list, man: dict) -> list:
    """Los pares vistos con el punto normalizado (o tal cual), sin repetir, ordenados: lo que comparan los controles."""
    return sorted({(doc, normalizar_punto(loc, secciones_del(man, doc))[0] or loc) for doc, loc in pares})


# --------------------------------------------------------------------------- #
# Lo visto: un lector por formato                                              #
# --------------------------------------------------------------------------- #
def pares_de_procedencias(provs: list, man: dict) -> list:
    """Procedencias {source_doc, location} (firma v1 y seen_provenances de EV2) -> (TO o documento, ubicación)."""
    out = []
    for p in provs:
        doc, loc = p.get("source_doc"), p.get("location")
        if isinstance(doc, str) and isinstance(loc, str):
            out.append((man["doc2to"].get(doc, doc), loc))
    return out


def leer_fragmentos(output_str: str, man: dict) -> list:
    obj = json.loads(output_str)
    out = []
    for r in (obj.get("resultados") or []) if isinstance(obj, dict) else []:
        if isinstance(r, dict) and isinstance(r.get("to"), str) and isinstance(r.get("unidad"), str):
            out.append((man["doc2to"].get(r["to"], r["to"]), r["unidad"]))
    return out


def leer_v1(output_str: str, man: dict, collect_provs) -> list:
    obj = json.loads(output_str)
    sink, ordenadas = set(), []
    collect_provs(obj, sink, ordenadas)
    return pares_de_procedencias(ordenadas, man)


def _clave_a_par(clave: str, man: dict) -> tuple:
    to, _, unidad = IP.base_punto(clave).partition("::")
    return man["doc2to"].get(to, to), unidad


def claves_en(texto: str, man: dict) -> list:
    """Los pares de las claves `to::unidad` de un texto; la de una sección que no es solo cifras, solo si es una
    sección de ese TO en la E0."""
    out = []
    for m in RE_CLAVE_PUNTO.finditer(texto):
        if m.group(2) is not None and m.group(2) not in secciones_del(man, man["doc2to"].get(m.group(1), m.group(1))):
            continue
        out.append(_clave_a_par(m.group(0), man))
    return out


def leer_vista_nav(tool: str, output_str: str, man: dict) -> list:
    """Las claves que la salida muestra fuera de su cabecera. La cabecera es la primera línea de toda vista del grafo
    y repite lo que pidió el agente (el punto, el id, el TO o los filtros); una clave que aparece solo ahí no cuenta.
    El punto pedido de ver_punto cuenta cuando la salida muestra su texto («Texto (n caracteres):», de
    familias_nav._lineas_texto); en ver_descendientes cuentan los descendientes, con el TO de la cabecera."""
    if output_str.startswith(f"{tool}:") or output_str.startswith("herramienta desconocida:"):
        return []
    cabecera, _, cuerpo = output_str.partition("\n")
    out = claves_en(cuerpo, man)
    lineas = cuerpo.split("\n")
    if tool == "ver_punto":
        m = RE_CABEZA_VP.match(cabecera)
        if m and len(lineas) > 2 and RE_TEXTO_VP.match(lineas[2]):
            out.append(_clave_a_par(m.group(1), man))
    if tool == "ver_descendientes":
        m = RE_CABEZA_DESC.match(cabecera)
        if m:
            to = IP.base_punto(m.group(1)).partition("::")[0]
            for linea in lineas:
                b = RE_BLOQUE_DESC.match(linea)
                if b:
                    out.append(_clave_a_par(f"{to}::{b.group(1)}", man))
    return out


def leer_salida(tool: str, output_str: str, man: dict, lect: dict) -> list:
    if tool in TOOLS_FRAGMENTOS:
        return leer_fragmentos(output_str, man)
    if tool in lect["tools_v1"]:
        return leer_v1(output_str, man, lect["collect_provs"])
    if tool in TOOLS_NAV:
        return leer_vista_nav(tool, output_str, man)
    raise SystemExit(f"ABORTO: herramienta sin lector: {tool!r}")


def leer_log_r1(path: Path) -> list:
    lineas = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [x for x in lineas if x.get("evento") == "llamada"]


def vistos_de_llamadas(llamadas: list, man: dict, lect: dict) -> tuple:
    """(pares vistos, llamadas leídas): las llamadas con salida (`output_str` no nulo) de cualquier herramienta."""
    pares, leidas = [], 0
    for ll in llamadas:
        if ll.get("output_str") is None:
            continue
        leidas += 1
        pares += leer_salida(ll.get("tool"), ll["output_str"], man, lect)
    return pares, leidas


# --------------------------------------------------------------------------- #
# Indicadores por sesión                                                       #
# --------------------------------------------------------------------------- #
def _fila_base(sesion, pregunta, brazo, n_anclas) -> dict:
    return {"sesion": sesion, "pregunta": pregunta, "brazo": brazo, "n_anclas": n_anclas,
            "grupo": None, "respondible": None, "n_citas": None, "n_parseables": None,
            "no_parseables_por_motivo": {}, "formas": {}, "n_no_fundadas": None, "n_no_existentes": None,
            "n_fuera_de_indice": None, "n_anclas_con_cita": None,
            "ind1_cita_fundada": None, "ind2_cita_existente": None, "ind3_cita_al_ancla": None,
            "info_cada_ancla_con_cita": None}


def _set_todos(fila: dict, valor: str) -> None:
    for k, _ in INDICADORES:
        fila[k] = valor


def evaluar(sesion: str, pregunta: str, brazo: str, fj, pares_vistos: list, anclas: list, ctx: dict) -> dict:
    """Los indicadores de una respuesta. `fj` es el JSON final (None si no hay); `anclas`, las de su pregunta."""
    fila = _fila_base(sesion, pregunta, brazo, len(anclas))
    if not isinstance(fj, dict):
        fila["grupo"] = "sin_json"
        _set_todos(fila, SIN_JSON)
        return fila
    respondible = fj.get("respondible")
    fila["respondible"] = respondible
    fila["grupo"] = "abstencion" if respondible is False else "contenido"
    citas = fj.get("citas")
    citas = [] if citas is None else citas
    if not isinstance(citas, list):
        raise SystemExit(f"ABORTO: {sesion}: las citas del JSON final no son una lista")
    fila["n_citas"] = len(citas)
    if not citas:
        fila["n_parseables"] = 0
        _set_todos(fila, SIN_CITAS)
        return fila

    vistas = claves_vistas(pares_vistos, ctx["man"])
    det = []
    for c in citas:
        p = partir_cita(c, ctx["man"])
        p["fundada"] = any(ctx["cita_fiel"](k, vistas) for k in claves_cita(p))
        if p["parseable"] and p["to"] in ctx["indices"]:
            p["existe"], _ = U2.resolver_en_indice(p["to"], p["punto"], ctx["indices"])
        elif p["parseable"]:
            p["existe"] = NO
        else:
            p["existe"] = "no_parseable"
        p["anclas"] = [j for j, a in enumerate(anclas)
                       if p["parseable"] and U2.es_ancla_o_descendiente(p["to"], p["punto"], a)]
        det.append(p)

    fila["n_parseables"] = sum(1 for p in det if p["parseable"])
    for p in det:
        if not p["parseable"]:
            fila["no_parseables_por_motivo"][p["motivo"]] = fila["no_parseables_por_motivo"].get(p["motivo"], 0) + 1
        e = etiqueta_forma(p)
        fila["formas"][e] = fila["formas"].get(e, 0) + 1
    fila["n_no_fundadas"] = sum(1 for p in det if not p["fundada"])
    fila["n_no_existentes"] = sum(1 for p in det if p["existe"] == NO)
    fila["n_fuera_de_indice"] = sum(1 for p in det if p["existe"] == FUERA)
    fila["ind1_cita_fundada"] = SI if all(p["fundada"] for p in det) else NO
    existes = [p["existe"] for p in det]
    if any(e in (NO, "no_parseable") for e in existes):
        fila["ind2_cita_existente"] = NO
    elif any(e == FUERA for e in existes):
        fila["ind2_cita_existente"] = FUERA
    else:
        fila["ind2_cita_existente"] = SI
    con_cita = {j for p in det for j in p["anclas"]}
    fila["n_anclas_con_cita"] = len(con_cita)
    fila["ind3_cita_al_ancla"] = SI if con_cita else NO
    fila["info_cada_ancla_con_cita"] = SI if anclas and len(con_cita) == len(anclas) else NO
    return fila


# --------------------------------------------------------------------------- #
# Sesiones y corrida                                                           #
# --------------------------------------------------------------------------- #
def sesiones_de(dirs: list) -> list:
    out = []
    for d in dirs:
        for m in sorted(Path(d).glob("meta_*.json"), key=lambda p: p.name):
            sid = m.stem[len("meta_"):]
            out.append({"sesion": sid, "meta": m, "log": m.parent / f"log_r1_{sid}.jsonl", "dir": Path(d)})
    ids = [s["sesion"] for s in out]
    if len(set(ids)) != len(ids):
        raise SystemExit("ABORTO: ids de sesión repetidos entre las carpetas")
    return out


def pregunta_de_sesion(sid: str, brazo: str, mapa: dict | None) -> str | None:
    if mapa is not None and sid in mapa:
        return mapa[sid]
    suf = f"-{brazo}"
    if not isinstance(brazo, str) or not sid.endswith(suf):
        return None
    nucleo = sid[: -len(suf)]
    etapa, sep, pregunta = nucleo.partition("-")
    return pregunta if sep and pregunta else None


def digest_dir(d: Path) -> dict:
    """sha256 sobre las líneas «<sha256>  <nombre>» de los meta_*.json y log_r1_*.jsonl, ordenados por nombre."""
    archivos = sorted([*d.glob("meta_*.json"), *d.glob("log_r1_*.jsonl")], key=lambda p: p.name)
    h = hashlib.sha256()
    for p in archivos:
        h.update(f"{sha256_file(p)}  {p.name}\n".encode("utf-8"))
    return {"ruta": ruta_legible(d), "sha256": h.hexdigest(), "n_archivos": len(archivos)}


def medir_insumos(cfg: dict, man_tos: tuple) -> dict:
    res = {"instrumento_head": verificar_instrumento_head(),
           "harness": {"ruta": "data/experiment/evaluacion/harness.py", "sha256": sha256_file(U2.HARNESS_PATH),
                       "sha256_esperado": U2.SHA_ESPERADOS["harness"][1]},
           "anclas": {"ruta": ruta_legible(cfg["anclas"]), "sha256": sha256_file(cfg["anclas"])}}
    if res["harness"]["sha256"] != res["harness"]["sha256_esperado"]:
        raise SystemExit("ABORTO: harness congelado con sha256 distinto del esperado")
    if cfg["manifiesto"] is not None:
        res["manifiesto"] = {"ruta": ruta_legible(cfg["manifiesto"]), "sha256": sha256_file(cfg["manifiesto"])}
    if cfg["mapa_sesiones"] is not None:
        res["mapa_sesiones"] = {"ruta": ruta_legible(cfg["mapa_sesiones"]),
                                "sha256": sha256_file(cfg["mapa_sesiones"])}
    for to in man_tos:
        p = cfg["e0"] / f"estructura_{to}.json"
        res[f"e0_{to}"] = {"ruta": ruta_legible(p), "sha256": sha256_file(p)}
    for i, d in enumerate(cfg["sesiones"]):
        res[f"sesiones_{i}"] = digest_dir(d)
    return res


def agregar(filas: list) -> dict:
    out = {}
    for brazo in sorted({f["brazo"] for f in filas}):
        fb = [f for f in filas if f["brazo"] == brazo]
        grupos = {"todas": fb, "contenido": [f for f in fb if f["grupo"] == "contenido"],
                  "abstencion": [f for f in fb if f["grupo"] == "abstencion"]}
        out[brazo] = {"n_sin_json": sum(1 for f in fb if f["grupo"] == "sin_json")}
        for g, fs in grupos.items():
            tabla = {"N": len(fs)}
            for k, _ in INDICADORES:
                cuenta = {v: sum(1 for f in fs if f[k] == v) for v in VALORES}
                tabla[k] = cuenta | {"si_n_de_N": f"{cuenta[SI]} de {len(fs)}"}
            out[brazo][g] = tabla
    return out


DEFINICIONES = {
    "cita": "texto «documento | punto» (dos piezas por «|», sin blancos en los bordes) u objeto {source_doc, location}; "
            "el documento (nombre del PDF o id del TO) va a su TO por el manifiesto; el punto se normaliza con "
            "RE_PUNTO/RE_SECCION de HEAD y sus formas cortas («n», «n.», «Sn»); una sección que no es solo cifras "
            "(«Sección A», «SA», «Sbloque2») vale solo si es una sección de ese TO en la E0. Lo que no se parte así es "
            "no parseable y cuenta «no» en los indicadores 2 y 3.",
    "lo visto": "pares (TO, punto) de cada salida del log R1 con output_str: fragmentos por `to` y `unidad`; firma v1 "
                "por las procedencias de harness.GraphAgent._collect_provs; vistas del grafo por las claves "
                "`to::unidad` que la salida muestra fuera de su cabecera (la primera línea, que repite lo pedido), "
                "el punto pedido de ver_punto cuando la salida muestra su texto y los descendientes de "
                "ver_descendientes; la clave de una sección que no es solo cifras, solo si es una sección de ese TO "
                "en la E0; las salidas de error no aportan.",
    "indicador 1 · cita fundada": "«sí» si TODA cita es fiel a algún par visto con _cita_fiel del harness, con su punto "
                                  "normalizado y con su ubicación tal cual, contra cada par en las dos formas.",
    "indicador 2 · cita existente": "como en HEAD: TODA cita parseable resuelve en el índice E0 de su TO; alguna "
                                    "inexistente o no parseable → «no»; si no, alguna fuera_de_indice → "
                                    "«fuera_de_indice»; si no → «sí».",
    "indicador 3 · cita al ancla": "«sí» si ALGUNA cita parseable tiene el TO de ALGUNA ancla y su punto es el del ancla "
                                   "o empieza con él seguido de «.».",
    "informativa · cada ancla con cita": "«sí» si CADA ancla de la pregunta tiene al menos una cita como la del "
                                         "indicador 3; columna aparte, fuera de toda comparación.",
    "sin_citas / sin_json": "lista de citas vacía o ausente → «sin_citas»; meta sin JSON final → «sin_json».",
    "grupos": "abstención = respondible == false; contenido = el resto con JSON; por brazo (todas / contenido / abstención).",
    "agregación": "fracción cruda «n de N» por indicador y brazo; sin porcentajes, sin intervalos.",
}


def correr(cfg: dict) -> int:
    cita_fiel, norm_loc, collect_provs, tools_v1 = importar_harness_y_lector_v1()
    man = manifiesto_desde(cfg["manifiesto"], cfg["e0"])
    insumos_inicio = medir_insumos(cfg, man["tos"])
    indices = cargar_indices(man, cfg["e0"])
    anclas = parsear_anclas(json.loads(cfg["anclas"].read_text(encoding="utf-8")), man)
    res_anclas = verificar_anclas(anclas, indices)
    mapa = None if cfg["mapa_sesiones"] is None else json.loads(cfg["mapa_sesiones"].read_text(encoding="utf-8"))
    ctx = {"man": man, "indices": indices, "cita_fiel": cita_fiel}
    lect = {"tools_v1": tools_v1, "collect_provs": collect_provs}

    filas = []
    for s in sesiones_de(cfg["sesiones"]):
        meta = json.loads(s["meta"].read_text(encoding="utf-8"))
        brazo = meta.get("brazo")
        pregunta = pregunta_de_sesion(s["sesion"], brazo, mapa)
        if pregunta is None or pregunta not in anclas:
            raise SystemExit(f"ABORTO: la sesión {s['sesion']} no tiene pregunta con anclas")
        if s["log"].is_file():
            llamadas = leer_log_r1(s["log"])
            pares, leidas = vistos_de_llamadas(llamadas, man, lect)
            n_log = len(llamadas)
        else:
            pares, leidas, n_log = [], 0, None
        f = evaluar(s["sesion"], pregunta, brazo, meta.get("final_json_R4"), pares, anclas[pregunta], ctx)
        f["completa_R3"] = (meta.get("completitud_R3") or {}).get("completa")
        f["log_r1_presente"] = s["log"].is_file()
        f["n_llamadas_log"], f["n_llamadas_leidas"] = n_log, leidas
        f["n_pares_vistos"] = len(pares_normalizados(pares, man))
        filas.append(f)
    filas.sort(key=lambda f: (f["brazo"], f["sesion"]))
    insumos_cierre = medir_insumos(cfg, man["tos"])
    cambiados = [k for k in insumos_inicio if insumos_inicio[k]["sha256"] != insumos_cierre[k]["sha256"]]
    if cambiados:
        raise SystemExit(f"ABORTO: insumos modificados durante la corrida (inicio ≠ cierre): {cambiados}")
    insumos = {k: v | {"sha256_cierre": insumos_cierre[k]["sha256"]} for k, v in insumos_inicio.items()}

    salida = {
        "unidad": "U-CITA-BANCO",
        "script": "scripts/ucita2_indicadores_banco.py",
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "definiciones": DEFINICIONES,
        "insumos": insumos,
        "tos": list(man["tos"]),
        "indice_e0": {to: {k: v for k, v in indices[to].items() if k != "numeros"} for to in man["tos"]},
        "anclas_en_indice": res_anclas,
        "resumen": {"sesiones": len(filas),
                    "por_brazo": {b: sum(1 for f in filas if f["brazo"] == b) for b in sorted({f["brazo"] for f in filas})},
                    "sesiones_sin_log": [f["sesion"] for f in filas if not f["log_r1_presente"]],
                    "sesiones_incompletas_R3": [f["sesion"] for f in filas if f["completa_R3"] is False]},
        "agregados": agregar(filas),
        "filas": filas,
    }
    out = cfg["out_json"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[salida] {ruta_legible(out)} sha256 {sha256_file(out)}")
    print(f"[anclas] {res_anclas['resueltas']} de {res_anclas['total']} resuelven en el índice E0 de su TO")
    for brazo, ag in salida["agregados"].items():
        t = ag["contenido"]
        print(f"[{brazo}] contenido N={t['N']}: " + " · ".join(f"{k} {t[k]['si_n_de_N']}" for k, _ in INDICADORES))
    return 0


# --------------------------------------------------------------------------- #
# Selftest                                                                     #
# --------------------------------------------------------------------------- #
INDICE_NAV_DEFAULT = (Path.home() / "INGENIERIA IA" / "TESIS" / "fuera_del_repo" / "indices_banco"
                      / "KG_Acumulado_Tandas0y1_r2b_sincola")
CONFIG_NAV = MCP_KG_DIR / "config_mcp_kg_nav_acumulado.json"
CONFIG_BM25 = MCP_VECTOR_DIR / "config_fragmentos_bm25_r2b.json"
METAS_A2_2 = BANCO_DIR / "a2_2" / "resultados"
E0_A2_2 = REPO / "data" / "experiment" / "reextraccion_v2" / "e0_chunking" / "salida_tanda0_r2b"
E0_EVALUADA = REPO / "data" / "experiment" / "tanda_final" / "t3" / "acumulado" / "e0_acumulado_128_r2b"
# Cuentas de forma esperadas en las 231 metas de A2.2 (1.124 citas), por grupo de brazos.
FORMAS_ESPERADAS_A2_2 = {
    "grafo": {"PDF | Punto n": 416, "PDF | Sección n": 1, "otra forma": 2},
    "fragmentos": {"PDF | n": 244, "id del TO | n": 432, "id del TO | Sn": 5, "id del TO | otra forma": 5,
                   "otra forma | n": 19},
}
TOTAL_ESPERADO_A2_2 = 1124
METAS_ESPERADAS_A2_2 = 231
GRUPO_DE_BRAZO = {"kg": "grafo", "fragmentos_bm25": "fragmentos", "fragmentos_denso": "fragmentos"}
NOMBRE_GRUPO = {"grafo": "del grafo", "fragmentos": "de los fragmentos"}


class Registro:
    def __init__(self):
        self.fallas = 0
        self.lineas = []
        self.casos = []   # los casos de lector: nombre, salidas y manifiesto (para contar pares fuera del selftest)

    def chequeo(self, nombre: str, ok: bool, detalle: str = "") -> None:
        self.fallas += not ok
        self.lineas.append(f"  [{'PASS' if ok else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""))
        print(self.lineas[-1])

    def info(self, texto: str) -> None:
        self.lineas.append(f"  [INFO] {texto}")
        print(self.lineas[-1])


def _huella(pares) -> str:
    return sha256_texto(json.dumps([list(p) for p in pares], ensure_ascii=False))[:16]


# ---- control 1: lo que mide no cambia ------------------------------------- #
def _casos_ev2():
    """Las 17 trazas sintéticas del selftest de HEAD (scripts/ucita2_indicadores.py:772-819), con su `seen`, más
    cuatro en el mismo formato, cada una con su `seen`."""
    DOC, DOC2, DOC3 = "TO_sintetico_actual.pdf", "TO_otro_actual.pdf", "TO_desconocido_actual.pdf"
    c = U2._cita
    seen = [c(DOC, "Punto 1.1.1"), c(DOC, "Punto 1.1"), c(DOC, "Punto 1.1.1.1"), c(DOC, "Punto 1.2"),
            c(DOC, "Sección 1"), c(DOC, "Comunicación “A” 1234"), c(DOC2, "Punto 1.1"), c(DOC3, "Punto 1.1")]
    largo = "Comunicación “A” 1234, Anexo I, régimen de excep"           # 40 caracteres o más, normalizada
    corto = "Comunicación “A” 1234, Anexo I, régim"                       # menos de 40, normalizada
    casos = [
        ("ST-01", [c(DOC, "Punto 1.1.1")], True, True, seen, False),
        ("ST-02", [c(DOC, "Punto 1.1.1.1")], True, True, seen, False),
        ("ST-03", [c(DOC, "Punto 1.1")], True, True, seen, False),
        ("ST-04", [c(DOC, "Punto 2.1")], True, True, seen, False),
        ("ST-05", [c(DOC, "Punto 1.1.1.")], True, True, seen, False),
        ("ST-06", [c(DOC, 'Comunicación  "A"  1234')], True, True, seen, False),
        ("ST-07", [c(DOC, "Punto 1.3")], True, True, seen, False),
        ("ST-08", [c(DOC, "Punto 1.1.1.1.1")], True, True, seen, False),
        ("ST-09", [], True, True, seen, False),
        ("ST-10", [c(DOC, "Punto 1.1.1")], False, True, seen, False),
        ("ST-11", None, None, False, seen, False),
        ("ST-12", [c(DOC, "Sección 1")], True, True, seen, False),
        ("ST-13", [c(DOC2, "Punto 1.1")], True, True, seen, False),
        ("ST-14", [c(DOC, "Punto 1.1.1"), c(DOC, "Punto 1.3")], True, True, seen, False),
        ("ST-15", [c(DOC, "Punto 1.1.1.1.1"), c(DOC, "Punto 1.3")], True, True, seen, False),
        ("ST-16", [c(DOC3, "Punto 1.1")], True, True, seen, False),
        ("ST-17", [c(DOC, "Punto 1.1.1")], True, True, seen, True),
        ("EX-18", [c(DOC, "Punto 1.1.1"), c(DOC2, "Punto 1.1")], True, True, seen, False),
        ("EX-19", [c(DOC, "Punto 1.1.1 (parte 2)")], True, True, seen, False),
        ("EX-20", [c(DOC, largo + "ciones generales")], True, True, [c(DOC, largo)], False),
        ("EX-21", [c(DOC, corto + "en de excepciones")], True, True, [c(DOC, corto)], False),
    ]
    divergencia = ("DV-01", [c(DOC, "Punto 1")], True, True, seen, False)
    ctx_head = {"manifiesto": {DOC: "sin", DOC2: "otr"},
                "indices": {"sin": {"numeros": {"1", "1.1", "1.1.1", "1.1.1.1", "1.2", "2", "2.1"}, "profundidad_max": 4},
                            "otr": {"numeros": {"1", "1.1"}, "profundidad_max": 2}},
                "gold": {}}
    man = armar_manifiesto([{"id": "sin", "archivo": DOC}, {"id": "otr", "archivo": DOC2}])
    return casos, divergencia, ctx_head, man


def _a_texto(citas):
    if citas is None:
        return None
    return [f"{x['source_doc']} | {x['location']}"
            if isinstance(x, dict) and isinstance(x.get("source_doc"), str) and isinstance(x.get("location"), str)
            and "|" not in x["source_doc"] + x["location"] else x for x in citas]


def control_1(R: Registro, cita_fiel, norm_loc) -> None:
    print("CONTROL 1 · lo que mide no cambia: trazas sintéticas en el formato del harness de EV2, un ancla (sin:1.1.1)")
    casos, divergencia, ctx_head, man = _casos_ev2()
    ctx_head = ctx_head | {"cita_fiel": cita_fiel, "norm_loc": norm_loc}
    ctx = {"man": man, "indices": ctx_head["indices"], "cita_fiel": cita_fiel}
    ancla = [{"ancla": "sin::1.1.1", "to": "sin", "punto": "1.1.1"}]
    pares_k = (("ind1_cita_fundada", "ind1_cita_fundada"), ("ind2_cita_existente", "ind2_cita_existente"),
               ("ind3_cita_al_ancla", "ind3_cita_al_ancla"), ("info_cada_ancla_con_cita", "ind3_cita_al_ancla"),
               ("grupo", "grupo"))

    def correr_caso(caso):
        qid, citas, resp, pok, seen, adulterar = caso
        tr = U2._traza_sintetica(qid, citas, resp, pok, seen, cita_fiel, adulterar)
        ctx_head["gold"][qid] = {"ancla": "sin:1.1.1", "to": "sin", "punto": "1.1.1"}
        fh = U2.evaluar_traza("selftest", tr, ctx_head)
        pares = pares_de_procedencias(tr["seen_provenances"], man)
        fj = tr["final_json"] if tr["parse_ok"] and isinstance(tr["final_json"], dict) else None
        fn = evaluar(qid, qid, "selftest", fj, pares, ancla, ctx)
        fjt = None if fj is None else fj | {"citas": _a_texto(fj["citas"])}
        ft = evaluar(qid, qid, "selftest", fjt, pares, ancla, ctx)
        return fh, fn, ft

    iguales = 0
    for caso in casos:
        fh, fn, ft = correr_caso(caso)
        dif = [f"{kn}: HEAD {fh[kh]!r}, objeto {fn[kn]!r}, texto {ft[kn]!r}" for kn, kh in pares_k
               if not (fh[kh] == fn[kn] == ft[kn])]
        iguales += not dif
        vals = " / ".join(str(fh[k]) for k in ("ind1_cita_fundada", "ind2_cita_existente", "ind3_cita_al_ancla"))
        R.chequeo(f"control 1 · {caso[0]}: HEAD = nuevo (objeto y texto)", not dif,
                  f"ind1 / ind2 / ind3 = {vals}; grupo={fh['grupo']}" + ("; " + "; ".join(dif) if dif else ""))
    R.chequeo("control 1 · trazas iguales a HEAD, traza por traza", iguales == len(casos), f"{iguales} de {len(casos)}")
    fh, fn, ft = correr_caso(divergencia)
    R.info(f"control 1 · divergencia declarada {divergencia[0]} (fuera de la cuenta): cita «Punto 1» con la vista "
           f"«Sección 1» del mismo TO: ind1 HEAD {fh['ind1_cita_fundada']!r}, nuevo {fn['ind1_cita_fundada']!r} "
           "(las dos ubicaciones normalizan al punto 1, que la E0 numera igual para la sección)")


# ---- control 2: los lectores ---------------------------------------------- #
def _verificar_respaldo(d: Path) -> tuple:
    esperado = {}
    for linea in (d / "manifest_respaldo.txt").read_text(encoding="utf-8").splitlines():
        if linea.strip():
            sha, nombre = linea.split(None, 1)
            esperado[nombre.strip()] = sha
    malos = [n for n, sha in sorted(esperado.items()) if sha256_file(d / n) != sha]
    return len(esperado), malos


CAMBIA_B = " · cambia en b: la clave de la cabecera no cuenta"


def _caso_lector(R: Registro, nombre: str, salidas: list, man: dict, lect: dict, esperados: list,
                 control: str = "control 2") -> None:
    """Un caso de lector: las salidas [(herramienta, output_str)], leídas como las llamadas de un log R1, contra sus
    pares esperados; los dos lados con el punto normalizado."""
    obtenidos, _ = vistos_de_llamadas([{"tool": t, "output_str": o} for t, o in salidas], man, lect)
    R.casos.append({"nombre": f"{control} · {nombre}", "salidas": salidas, "man": man})
    o, e = pares_normalizados(obtenidos, man), pares_normalizados(esperados, man)
    R.chequeo(f"{control} · {nombre}", o == e,
              f"pares esperados {len(e)}, obtenidos {len(o)}, huella {_huella(o)}"
              + ("" if o == e else f"; faltan {len(set(e) - set(o))}, sobran {len(set(o) - set(e))}"))


def _filas_buscar(out: str) -> list:
    return [x.split(" | ")[1] for x in out.split("\n") if re.match(r"^\d+ \| ", x)]


def control_2(R: Registro, lect: dict, indice_nav: Path) -> None:
    print("CONTROL 2 · los lectores: salidas reales donde se arman por código sin Neo4j ni el denso; si no, sintéticas")
    from comun_banco import serializar_payload

    # -- fragmentos: el BM25 del brazo de A2.2 (salidas reales) --
    import servidor_mcp_vector as SV
    cfg_bm25 = json.loads(CONFIG_BM25.read_text(encoding="utf-8"))
    idx = SV.IndiceBM25(cfg_bm25)
    man_frag = armar_manifiesto([{"id": t, "archivo": a} for t, a in sorted({(p["to"], p["archivo"]) for p in idx.pasajes})])
    for consulta, limite in (("plazo máximo para la exportación de servicios", 5), ("previsiones por riesgo de incobrabilidad", 5),
                             ("sección del texto ordenado", 3), ("", 5)):
        obj = idx.buscar_pasajes(consulta, limite)
        out = serializar_payload(obj)
        top = idx.buscador.buscar(consulta, SV._limite(limite, idx.limite_max)) if consulta.strip() else []
        esperados = [(idx.pasajes[i]["to"], normalizar_punto(idx.pasajes[i]["unidad"])[0] or idx.pasajes[i]["unidad"])
                     for i, _ in top]
        _caso_lector(R, f"fragmentos BM25 real (consulta {len(consulta)} caracteres, límite {limite})",
                     [("buscar_pasajes", out)], man_frag, lect, esperados)
    secciones = sum(1 for p in idx.pasajes if RE_S.match(p["unidad"]))
    R.info(f"control 2 · fragmentos: pasajes del índice BM25 de A2.2 {len(idx.pasajes)}, de ellos de sección («Sn») {secciones}")
    sint = {"consulta": "x", "total_pasajes": 3, "filtros": {"to": "cla", "punto": "cla::9"}, "n_pasajes_filtrados": 0,
            "aviso": "ningún pasaje pasa los filtros", "resultados": []}
    _caso_lector(R, "fragmentos híbrida sintética (filtros, sin pasajes)", [("buscar_pasajes", serializar_payload(sint))],
                 man_frag, lect, [])
    sint2 = {"consulta": "x", "total_pasajes": 3, "resultados": [
        {"rank": 1, "id": "p1", "to": "cla", "unidad": "S2", "archivo": "a.pdf", "titulo": "t", "tipo": "seccion",
         "paginas": [1], "score": 1.0, "texto": "t"},
        {"rank": 2, "id": "p2", "to": "ext", "unidad": "4.1.2", "archivo": "b.pdf", "titulo": "t", "tipo": "punto",
         "paginas": [2], "score": 0.5, "texto": "t"}]}
    _caso_lector(R, "fragmentos sintética (una sección «S2» y un punto)", [("buscar_pasajes", serializar_payload(sint2))],
                 man_frag, lect, [("cla", "2"), ("ext", "4.1.2")])

    # -- firma v1: harness.GraphIndex (salidas reales) --
    gate_code = str(BANCO_DIR / "gate" / "code")
    if gate_code not in sys.path:
        sys.path.insert(0, gate_code)
    import tools_juguete as TJ
    import servidor_mcp_kg as BASE          # su `despachar`: la réplica de GraphAgent._run_tool del harness
    from harness import GraphIndex
    from loader import Edge, KnowledgeGraph, Node
    man_v1 = armar_manifiesto([{"id": "ext", "archivo": "TO_exterior_cambios_actual.pdf"},
                               {"id": "cla", "archivo": "TO_clasificacion_deudores_actual.pdf"}])
    raw = TJ.cargar_raw()
    gi = TJ.cargar_index()
    por_id = {n["id"]: n for n in raw["nodes"]}
    for n in raw["nodes"][:4]:
        out = serializar_payload(BASE.despachar(gi, "ver_nodo", {"id": n["id"]}))
        esperados = [(man_v1["doc2to"].get(p["source_doc"], p["source_doc"]), p["location"]) for p in n["provenances"]]
        _caso_lector(R, "firma v1 real ver_nodo (grafo del gate)", [("ver_nodo", out)], man_v1, lect, esperados)
    for nid in sorted({e["source"] for e in raw["edges"]} | {e["target"] for e in raw["edges"]}):
        out = serializar_payload(BASE.despachar(gi, "ver_vecinos", {"id": nid}))
        esperados = [(man_v1["doc2to"].get(p["source_doc"], p["source_doc"]), p["location"])
                     for e in raw["edges"] if nid in (e["source"], e["target"]) for p in e["provenances"]]
        _caso_lector(R, "firma v1 real ver_vecinos (grafo del gate)", [("ver_vecinos", out)], man_v1, lect, esperados)
    out = serializar_payload(BASE.despachar(gi, "buscar_nodos", {"consulta": por_id[raw["nodes"][0]["id"]]["label"]}))
    _caso_lector(R, "firma v1 real buscar_nodos (sin procedencias)", [("buscar_nodos", out)], man_v1, lect, [])
    out = serializar_payload(BASE.despachar(gi, "ver_nodo", {"id": "no_existe"}))
    _caso_lector(R, "firma v1 real ver_nodo de un id inexistente (error)", [("ver_nodo", out)], man_v1, lect, [])
    # La vista del grafo de A2.2 (source_doc = PDF, location = «Punto n» | «Sección n»), por GraphIndex.
    P1, P2 = "TO_clasificacion_deudores_actual.pdf", "TO_exterior_cambios_actual.pdf"
    kg = KnowledgeGraph(run_key="selftest_banco", path=Path("selftest_banco"),
                        nodes=[Node("A", "Obligacion", "a", {}, [{"source_doc": P1, "location": "Punto 6.5.5"}]),
                               Node("B", "Definicion", "b", {}, [{"source_doc": P1, "location": "Sección 3"},
                                                                  {"source_doc": P2, "location": "Punto 2.1.1"}]),
                               Node("C", "Excepcion", "c", {}, [{"source_doc": P2, "location": "Punto 4"}])],
                        edges=[Edge("A", "B", "remite_a", {}, [{"source_doc": P1, "location": "Punto 6.5.5."}]),
                               Edge("C", "A", "exceptua", {}, [{"source_doc": P2, "location": "Punto 4.1"}])])
    gi2 = GraphIndex(kg)
    _caso_lector(R, "firma v1 ver_nodo, vista de A2.2 por GraphIndex (datos sintéticos)",
                 [("ver_nodo", serializar_payload(gi2.ver_nodo("B")))], man_v1, lect, [("cla", "3"), ("ext", "2.1.1")])
    _caso_lector(R, "firma v1 ver_vecinos, vista de A2.2 por GraphIndex (datos sintéticos)",
                 [("ver_vecinos", serializar_payload(gi2.ver_vecinos("A")))], man_v1, lect,
                 [("cla", "6.5.5"), ("ext", "4.1")])

    # -- vistas del grafo: el Navegador sobre el índice por punto de N5, con el doble sin Neo4j (salidas reales) --
    n_resp, malos = _verificar_respaldo(indice_nav)
    R.chequeo("control 2 · índice por punto de N5 verificado contra manifest_respaldo.txt", not malos,
              f"{n_resp - len(malos)} de {n_resp} archivos")
    import selftest_familias_nav as STN
    from grafos import GRAFOS
    cfg_nav = json.loads(CONFIG_NAV.read_text(encoding="utf-8"))
    driver = STN._DriverSinNeo4j(indice_nav, cfg_nav.get("kg_sha256_esperado"))
    nav = FNC.NavegadorCand(driver, GRAFOS[cfg_nav["grafo"]]["label"], indice_nav,
                            sha256_manifiesto=cfg_nav["sha256_manifiesto_indice"], python_vector=None,
                            hubs_esperados=None)
    R.chequeo("control 2 · Navegador sin Neo4j y sin denso", nav.denso is None, f"{len(nav.ids_docs)} puntos")
    # Las secciones de la E0 del índice (la que nombra su manifiesto.json), verificada contra los sha256 del mismo.
    man_idx = json.loads((indice_nav / "manifiesto.json").read_text(encoding="utf-8"))
    e0_nav = REPO / man_idx["e0_dir"]
    est_idx = {n: sha for n, sha in man_idx["insumos_e0"].items() if n.startswith("estructura_")}
    malos_e0 = [n for n, sha in sorted(est_idx.items()) if sha256_file(e0_nav / n) != sha]
    R.chequeo("control 2 · E0 del índice de N5 en la copia = la de su manifiesto (estructura_<to>.json)", not malos_e0,
              f"{len(est_idx) - len(malos_e0)} de {len(est_idx)} archivos")
    tos_nav = sorted(set(nav.archivo_a_to.values()))
    man_nav = armar_manifiesto([{"id": t, "archivo": a} for a, t in sorted(nav.archivo_a_to.items())],
                               secciones_e0(e0_nav, tos_nav))

    def base_par(k):
        return _clave_a_par(k, man_nav)

    def esperado_buscar(consulta, to=None, punto=None, limite=8):
        cand = range(len(nav.ids_docs))
        if to:
            cand = [i for i in cand if nav.ids_docs[i].split("::", 1)[0] == to]
        if punto:
            sub = nav._subarbol(nav.resolver_punto(punto, to=to))
            cand = [i for i in cand if nav.ids_docs[i] in sub]
        bm = nav.buscador.puntajes(IP.BM.analizar(consulta))
        rank = sorted((i for i in cand if bm.get(i, 0) > 0), key=lambda i: (-bm[i], nav.ids_docs[i]))
        return [nav.ids_docs[i] for i in rank[:limite]]

    for consulta, to, punto, limite in (("plazo máximo", None, None, 8), ("entidades financieras", "cla", None, 10),
                                        ("excepción", "cla", "cla::6.5", 6), ("Clasificación en categoría Irrecuperable", "cla", None, 10)):
        out = nav.buscar_puntos(consulta, to=to, punto=punto, limite=limite)
        filas = _filas_buscar(out)
        esperados = [base_par(k) for k in esperado_buscar(consulta, to, punto, limite)[:len(filas)]]
        nota = ""
        if punto:   # en la vuelta a la clave del filtro contaba por la cabecera; ahora, solo si está en las filas
            nota = (" · en b: la clave del filtro cuenta por su fila" if nav.resolver_punto(punto, to=to) in filas
                    else CAMBIA_B)
        _caso_lector(R, f"vista real buscar_puntos (filtros: to={'sí' if to else 'no'}, punto={'sí' if punto else 'no'}, "
                        f"filas {len(filas)}){nota}", [("buscar_puntos", out)], man_nav, lect, esperados)
    out = nav.buscar_puntos("zzzzqqqq inexistente", to="cla")
    _caso_lector(R, "vista real buscar_puntos sin resultados", [("buscar_puntos", out)], man_nav, lect, [])
    claves_todas = sorted(k for k, p in nav.puntos.items() if p.get("tipo") != "to")
    claves_cla = [k for k in claves_todas if nav.puntos[k].get("to") == "cla"]
    k_uno = next(k for k in claves_cla if len(nav.puntos[k]["nodos"]) <= 1 and nav._texto_propio(k))
    _caso_lector(R, "vista real ver_punto (punto de cla con a lo sumo un nodo: no consulta aristas)",
                 [("ver_punto", nav.ver_punto(k_uno))], man_nav, lect, [base_par(k_uno)])
    _caso_lector(R, "vista real ver_punto de un punto inexistente (error con el ejemplo «ext::5.13»)",
                 [("ver_punto", nav.ver_punto("cla::999.999"))], man_nav, lect, [])
    _caso_lector(R, "vista real indice_to (cla, 2 niveles: solo unidades y títulos)",
                 [("indice_to", nav.indice_to("cla"))], man_nav, lect, [])
    _caso_lector(R, "vista real tipos_de_relacion sin grados (error)",
                 [("tipos_de_relacion", nav.tipos_de_relacion("no_existe"))], man_nav, lect, [])
    k_desc = next(k for k in claves_cla if len(nav._descendientes(k, 2)) >= 3)
    for niveles, desde in ((2, 0), (2, 1)):
        out = nav.ver_descendientes(k_desc, niveles=niveles, desde=desde)
        desc = nav._descendientes(k_desc, niveles)
        n_bloques = sum(1 for x in out.split("\n") if RE_BLOQUE_DESC.match(x))
        esperados = [base_par(k) for k in desc[desde:desde + n_bloques]]
        _caso_lector(R, f"vista real ver_descendientes (niveles {niveles}, desde {desde}, bloques {n_bloques}){CAMBIA_B}",
                     [("ver_descendientes", out)], man_nav, lect, esperados)
    _caso_lector(R, "vista real ver_descendientes de un punto inexistente (error)",
                 [("ver_descendientes", nav.ver_descendientes("cla::999.999"))], man_nav, lect, [])

    # -- cabeceras que repiten la entrada: una por herramienta. Reales donde el doble sin Neo4j las arma; las que leen
    # aristas, con el código de HEAD sobre el mismo Navegador y aristas sintéticas (un doble de `_remisiones` y de
    # `_vecinos`, que es lo único que va a Neo4j) --
    k_filtro, out_f = None, None
    for k in claves_cla:
        if len(nav._subarbol(k)) < 4:
            continue
        out_f = nav.buscar_puntos(f"{k} excepción", to="cla", punto=k, limite=6)
        if _filas_buscar(out_f) and k not in _filas_buscar(out_f):
            k_filtro = k
            break
    filas = _filas_buscar(out_f)
    _caso_lector(R, f"cabecera · buscar_puntos real: la clave en la consulta y en el filtro punto=, fuera de las filas, "
                    f"no cuenta (filas {len(filas)})", [("buscar_puntos", out_f)], man_nav, lect,
                 [base_par(k) for k in esperado_buscar(f"{k_filtro} excepción", "cla", k_filtro, 6)[:len(filas)]])
    k_sin = next(k for k in claves_cla if not nav._texto_propio(k) and not nav.puntos[k]["nodos"])
    _caso_lector(R, "cabecera · ver_punto real de un punto sin texto propio ni nodos: el punto pedido no cuenta",
                 [("ver_punto", nav.ver_punto(k_sin))], man_nav, lect, [])
    con_nodos = [k for k in claves_cla if nav.puntos[k]["nodos"]]
    k_r, c_r = con_nodos[0], con_nodos[1]
    n_k, n_c = nav.puntos[k_r]["nodos"][0], nav.puntos[c_r]["nodos"][0]
    n_d = next(n for k in con_nodos[2:] for n in nav.puntos[k]["nodos"] if nav._punto_de(n) not in (k_r, c_r))
    nav._rem = {"origen": {n_k: [{"a": n_k, "b": n_c, "destino": c_r, "o": 1, "p": {"alcance": "punto"}}]},
                "target": {n_k: [{"a": n_d, "b": n_k, "destino": None, "o": 2, "p": {}}]}, "destino": {}}
    try:
        out = nav.ver_remisiones(k_r)
    finally:
        del nav._rem
    _caso_lector(R, "cabecera · ver_remisiones (código de HEAD, aristas sintéticas): el punto pedido no cuenta",
                 [("ver_remisiones", out)], man_nav, lect, [base_par(c_r), base_par(nav._punto_de(n_d))])
    _caso_lector(R, "cabecera · indice_to real con desde: el TO y la unidad de la cabecera no son claves",
                 [("indice_to", nav.indice_to("cla", desde=k_desc))], man_nav, lect, [])
    # El grado de cada nodo también sale de Neo4j (Navegador._hubs): el doble lo da para el nodo pedido.
    grado_doble = nav.grado
    vec = [{"rel": "remite_a", "v": n_c, "tipo": nav.nodos[n_c]["type"], "label": nav.nodos[n_c]["label"], "p": {}}]
    nav._vecinos = lambda nid, rel, sentido: [f for f in vec if rel in (None, f["rel"])] if sentido == "salientes" else []
    nav.grado = {**grado_doble, n_k: len(vec)}
    try:
        out = nav.tipos_de_relacion(n_k)
    finally:
        del nav._vecinos
        nav.grado = grado_doble
    _caso_lector(R, "cabecera · tipos_de_relacion (código de HEAD, vecinos sintéticos): el id pedido no es clave; el punto "
                    "del nodo, en la línea siguiente, cuenta", [("tipos_de_relacion", out)], man_nav, lect,
                 [base_par(nav._punto_de(n_k))])
    k_v = next(k for k in claves_cla
               if len({n for d in nav._descendientes(k, 2) for n in nav.puntos[d]["nodos"] if nav._punto_de(n) != k}) >= 2)
    vs = list(dict.fromkeys(n for d in nav._descendientes(k_v, 2) for n in nav.puntos[d]["nodos"]
                            if nav._punto_de(n) != k_v))[:2]
    vec2 = [{"rel": "remite_a", "v": n, "tipo": nav.nodos[n]["type"], "label": nav.nodos[n]["label"],
             "p": {"alcance": "punto"}} for n in vs]
    nav._vecinos = lambda nid, rel, sentido: list(vec2) if sentido == "salientes" else []
    nav.grado = {**grado_doble, n_k: len(vec2)}
    try:
        out = nav.vecinos_por_relacion(n_k, "remite_a", "salientes", to="cla", punto=k_v)
    finally:
        del nav._vecinos
        nav.grado = grado_doble
    _caso_lector(R, "cabecera · vecinos_por_relacion (código de HEAD, vecinos sintéticos): el filtro punto= no cuenta",
                 [("vecinos_por_relacion", out)], man_nav, lect, [base_par(nav._punto_de(n)) for n in vs])

    # -- secciones que no son solo cifras, en el índice de N5 (salidas reales) --
    no_cifras = [k for k in claves_todas if nav.puntos[k].get("tipo") == "seccion"
                 and not re.fullmatch(r"S\d+", nav.puntos[k]["unidad"].rpartition("::")[2])]
    set_nc = set(no_cifras)
    R.info(f"control 2 · secciones del índice de N5 que no son solo cifras: {len(no_cifras)}, en "
           f"{len({nav.puntos[k]['to'] for k in no_cifras})} TOs")
    enteras = sum(1 for k in claves_todas if claves_en(k, man_nav) == [base_par(k)])
    R.chequeo("control 2 · el lector toma entera cada clave del índice de N5, también las de secciones que no son solo "
              "cifras", enteras == len(claves_todas), f"{enteras} de {len(claves_todas)}")
    k_nt = next(k for k in no_cifras if nav._texto_propio(k) and len(nav.puntos[k]["nodos"]) <= 1)
    _caso_lector(R, "sección que no es solo cifras · ver_punto real con texto: cuenta",
                 [("ver_punto", nav.ver_punto(k_nt))], man_nav, lect, [base_par(k_nt)])
    to_nt = nav.puntos[k_nt]["to"]
    consulta = nav.puntos[k_nt]["titulo"]
    out = nav.buscar_puntos(consulta, to=to_nt, limite=10)
    filas = _filas_buscar(out)
    _caso_lector(R, f"sección que no es solo cifras · buscar_puntos real (filas {len(filas)}, de esas secciones "
                    f"{sum(1 for k in filas if k in set_nc)})", [("buscar_puntos", out)], man_nav, lect,
                 [base_par(k) for k in esperado_buscar(consulta, to_nt, None, 10)[:len(filas)]])
    k_dn = next(k for k in claves_todas if any(d in set_nc for d in nav._descendientes(k, 2)))
    out = nav.ver_descendientes(k_dn, niveles=2)
    desc = nav._descendientes(k_dn, 2)
    n_bloques = sum(1 for x in out.split("\n") if RE_BLOQUE_DESC.match(x))
    _caso_lector(R, f"sección que no es solo cifras · ver_descendientes real (bloques {n_bloques}, de esas secciones "
                    f"{sum(1 for k in desc[:n_bloques] if k in set_nc)})", [("ver_descendientes", out)], man_nav, lect,
                 [base_par(k) for k in desc[:n_bloques]])
    k_nh = next(k for k in no_cifras if nav._descendientes(k, 2))
    out = nav.ver_descendientes(k_nh, niveles=2)
    desc = nav._descendientes(k_nh, 2)
    n_bloques = sum(1 for x in out.split("\n") if RE_BLOQUE_DESC.match(x))
    _caso_lector(R, f"sección que no es solo cifras · ver_descendientes real de una de ellas: la cabecera no cuenta "
                    f"(bloques {n_bloques})", [("ver_descendientes", out)], man_nav, lect,
                 [base_par(k) for k in desc[:n_bloques]])

    # Sintéticas, con el formato del código (las que leen aristas de Neo4j).
    man_s = armar_manifiesto([{"id": "cla", "archivo": "c.pdf"}, {"id": "ext", "archivo": "e.pdf"},
                              {"id": "cap", "archivo": "k.pdf"}, {"id": "ric", "archivo": "r.pdf"},
                              {"id": "pro", "archivo": "p.pdf"}])
    sint_vp = "\n".join([
        "ver_punto ext::5.13 — e.pdf · páginas 3, 4", "Ancestros: S5 Título de la sección › 5.1 Título",
        "Título: Título del punto", "Texto (20 caracteres):", "texto del punto 5.13",
        "Nodos (2 de 2; # | tipo | id | label | tramo literal | umbrales):",
        "n1 | Obligacion | Obligacion_5_13 | label | «tramo» | —", "n2 | Excepcion (intro) | Excepcion_5_13 | label | «tramo» | —",
        "Relaciones entre los nodos listados (1 de 1):", "n2 —exceptua→ n1 [no verificada]",
        "Hijos (2; unidad · título · nodos):", "5.13.1 · Título · 2 nodos", "5.13.2 · Título · 1 nodo"])
    _caso_lector(R, "vista sintética ver_punto con nodos, relaciones e hijos", [("ver_punto", sint_vp)], man_s, lect,
                 [("ext", "5.13")])
    sint_vr = "\n".join([
        "ver_remisiones cla::5.1 · saltos 1", "cita: 2 puntos a 1 salto (2 aristas remite_a)",
        "lo_citan: 1 puntos a 1 salto (1 aristas remite_a)", "dir | punto | título | comienzo del texto | n nodos | alcance | salto",
        "cita | cla::6.5.5 | Título | Comienzo | 3 | punto | 1", "cita | ext::S3 | Título | Comienzo | 0 | — | 1",
        "lo_citan | cap::4.2.1.2::parte2 | Título | Comienzo | 2 | punto [no verificada] | 1"])
    _caso_lector(R, f"vista sintética ver_remisiones (sección «S3» y bloque «::parte2»){CAMBIA_B}",
                 [("ver_remisiones", sint_vr)], man_s, lect, [("cla", "6.5.5"), ("ext", "3"), ("cap", "4.2.1.2")])
    sint_vpr = "\n".join([
        "vecinos_por_relacion Obligacion_x · remite_a · salientes · to=cla · 2 vecinos",
        "vecino | tipo | label | punto | marca (de 0 a 2 de 2)", "Definicion_y | Definicion | label | cla::5.1.1 | alcance punto",
        "Excepcion_z | Excepcion | label | ric::A2::3.1::intro"])
    _caso_lector(R, "vista sintética vecinos_por_relacion (subdocumento «A2::3.1» y bloque «::intro»)",
                 [("vecinos_por_relacion", sint_vpr)], man_s, lect, [("cla", "5.1.1"), ("ric", "A2::3.1")])
    sint_tr = "\n".join([
        "tipos_de_relacion Obligacion_x", "Nodo: Obligacion «label» · punto pro::2.3 · grado 4 (salientes 3 · entrantes 1) · "
        "hub del 1 %: no (umbral 38)", "relación | dirección | cuenta | por tipo de vecino", "remite_a | saliente | 3 | Definicion 3"])
    _caso_lector(R, "vista sintética tipos_de_relacion", [("tipos_de_relacion", sint_tr)], man_s, lect, [("pro", "2.3")])
    sint_err = "buscar_puntos: no existe el punto «cla::77». Usá «to::unidad» (p. ej. «ext::5.13») o indice_to."
    _caso_lector(R, "vista sintética de error de buscar_puntos (eco de la entrada y ejemplo)",
                 [("buscar_puntos", sint_err)], man_s, lect, [])

    # -- el log R1 entero: despacho por herramienta, salidas nulas, herramienta sin lector --
    log = [{"evento": "inicio"},
           {"evento": "llamada", "tool": "buscar_pasajes", "output_str": serializar_payload(sint2)},
           {"evento": "llamada", "tool": "ver_nodo", "output_str": serializar_payload(gi2.ver_nodo("C"))},
           {"evento": "llamada", "tool": "ver_remisiones", "output_str": sint_vr},
           {"evento": "llamada", "tool": "ver_vecinos", "output_str": None, "error": "x"},
           {"evento": "fin"}]
    man_log = armar_manifiesto([{"id": "cla", "archivo": P1}, {"id": "ext", "archivo": P2}, {"id": "cap", "archivo": "k.pdf"}])
    llamadas = [x for x in log if x.get("evento") == "llamada"]
    _, leidas = vistos_de_llamadas(llamadas, man_log, lect)
    _caso_lector(R, f"log R1 sintético de tres herramientas (llamadas {len(llamadas)}, leídas {leidas}){CAMBIA_B}",
                 [(x["tool"], x["output_str"]) for x in llamadas], man_log, lect,
                 [("cla", "2"), ("ext", "4.1.2"), ("ext", "4"), ("cla", "6.5.5"), ("ext", "3"), ("cap", "4.2.1.2")])
    try:
        vistos_de_llamadas([{"evento": "llamada", "tool": "otra_herramienta", "output_str": "{}"}], man_log, lect)
        abortado = False
    except SystemExit:
        abortado = True
    R.chequeo("control 2 · una herramienta sin lector aborta la corrida", abortado)


# ---- controles 3 y 4: las citas y las dos anclas --------------------------- #
def _ctx_sintetico(cita_fiel):
    man = armar_manifiesto([{"id": "cla", "archivo": "TO_clasificacion_deudores_actual.pdf"},
                            {"id": "ext", "archivo": "TO_exterior_cambios_actual.pdf"}])
    indices = {"cla": {"numeros": {"1", "1.1", "1.1.1", "1.1.1.1", "2", "2.1", "3"}, "profundidad_max": 4},
               "ext": {"numeros": {"1", "1.1", "2", "2.1", "2.1.1"}, "profundidad_max": 3}}
    return {"man": man, "indices": indices, "cita_fiel": cita_fiel}


LARGO = "Comunicación “A” 5000, Anexo I, régimen de excep"     # 40 caracteres o más, normalizada
CORTO = "Comunicación “A” 5000, Anexo I, rég"                   # menos de 40, normalizada


def control_3(R: Registro, cita_fiel, norm_loc) -> None:
    print("CONTROL 3 · las citas: cada forma de A2.2, no parseables, vista truncada y punto fuera de la E0 (ancla cla::1.1)")
    ctx = _ctx_sintetico(cita_fiel)
    n_largo, n_corto = len(norm_loc(LARGO)), len(norm_loc(CORTO))
    R.chequeo("control 3 · largos de las vistas truncadas (normalizadas con _norm_loc)", n_largo >= 40 > n_corto,
              f"{n_largo} y {n_corto} caracteres")
    PC, PE = "TO_clasificacion_deudores_actual.pdf", "TO_exterior_cambios_actual.pdf"
    vistos = [(PC, "Punto 1.1"), (PC, "Sección 3"), ("cla", "2.1"), ("cla", "S2"), ("cla", "1.1.1"), ("cla", "9.9"),
              (PE, LARGO), (PE, CORTO)]
    pares = [(ctx["man"]["doc2to"].get(d, d), loc) for d, loc in vistos]
    ancla = [{"ancla": "cla::1.1", "to": "cla", "punto": "1.1"}]
    # (descripción, cita, forma esperada, parseable, (TO, punto), ind1, ind2, ind3)
    casos = [
        ("PDF | Punto n", f"{PC} | Punto 1.1", "PDF | Punto n", True, ("cla", "1.1"), SI, SI, SI),
        ("PDF | Sección n", f"{PC} | Sección 3", "PDF | Sección n", True, ("cla", "3"), SI, SI, NO),
        ("PDF | n", f"{PC} | 2.1", "PDF | n", True, ("cla", "2.1"), SI, SI, NO),
        ("id del TO | n.", "cla | 2.1.", "id del TO | n", True, ("cla", "2.1"), SI, SI, NO),
        ("id del TO | Sn", "cla | S2", "id del TO | Sn", True, ("cla", "2"), SI, SI, NO),
        ("id del TO | otra forma (no parseable)", "cla | Anexo B", "id del TO | otra forma", False, ("cla", None), NO, NO, NO),
        ("otra forma | n (no parseable)", "Clasificación de deudores | 1.1", "otra forma | n", False, (None, "1.1"), NO, NO, NO),
        ("sin separador (no parseable)", f"{PC}, Punto 1.1", "texto: otra forma", False, (None, None), NO, NO, NO),
        ("tres piezas (no parseable)", f"{PC} | Punto 1.1 | Punto 2.1", "texto: otra forma", False, (None, None), NO, NO, NO),
        ("objeto {source_doc, location}", {"source_doc": PC, "location": "Punto 1.1.1"}, "objeto: PDF | Punto n", True,
         ("cla", "1.1.1"), SI, SI, SI),
        (f"vista truncada de {n_largo} caracteres: prefijo admitido", f"{PE} | {LARGO}ciones generales", "PDF | otra forma",
         False, ("ext", None), SI, NO, NO),
        (f"vista truncada de {n_corto} caracteres: prefijo no admitido", f"{PE} | {CORTO}imen general de excepciones",
         "PDF | otra forma", False, ("ext", None), NO, NO, NO),
        ("punto vista que no está en la E0", "cla | 9.9", "id del TO | n", True, ("cla", "9.9"), SI, NO, NO),
        ("punto más profundo que la E0 (fuera_de_indice), descendiente del ancla", "cla | 1.1.1.1.1", "id del TO | n", True,
         ("cla", "1.1.1.1.1"), NO, FUERA, SI),
    ]
    for desc, cita, forma, parseable, (to, punto), e1, e2, e3 in casos:
        p = partir_cita(cita, ctx["man"])
        f = evaluar("C3", "C3", "selftest", {"citas": [cita], "respondible": True}, pares, ancla, ctx)
        obt = (etiqueta_forma(p), p["parseable"], p["to"], p["punto"], f["ind1_cita_fundada"], f["ind2_cita_existente"],
               f["ind3_cita_al_ancla"])
        esp = (forma, parseable, to, punto, e1, e2, e3)
        R.chequeo(f"control 3 · {desc}", obt == esp,
                  f"forma «{obt[0]}», parseable {obt[1]}, ind1 / ind2 / ind3 = {obt[4]} / {obt[5]} / {obt[6]}"
                  + ("" if obt == esp else f"; esperado {esp}"))
    sesiones = [
        ("mezcla: una al ancla y una no parseable (TODA vs ALGUNA)", {"citas": [f"{PC} | Punto 1.1", "cla | Anexo B"],
                                                                     "respondible": True}, (NO, NO, SI, "contenido")),
        ("sin citas", {"citas": [], "respondible": True}, (SIN_CITAS, SIN_CITAS, SIN_CITAS, "contenido")),
        ("citas ausentes", {"respondible": True}, (SIN_CITAS, SIN_CITAS, SIN_CITAS, "contenido")),
        ("sin JSON final", None, (SIN_JSON, SIN_JSON, SIN_JSON, "sin_json")),
        ("abstención con cita al ancla", {"citas": [f"{PC} | Punto 1.1"], "respondible": False}, (SI, SI, SI, "abstencion")),
    ]
    for desc, fj, esp in sesiones:
        f = evaluar("C3", "C3", "selftest", fj, pares, ancla, ctx)
        obt = (f["ind1_cita_fundada"], f["ind2_cita_existente"], f["ind3_cita_al_ancla"], f["grupo"])
        R.chequeo(f"control 3 · {desc}", obt == esp, f"ind1 / ind2 / ind3 / grupo = {' / '.join(map(str, obt))}")


def control_4(R: Registro, cita_fiel) -> None:
    print("CONTROL 4 · las dos anclas: cla::1.1 y ext::S2 (TOs distintos)")
    ctx = _ctx_sintetico(cita_fiel)
    anclas = parsear_anclas({"Q2": ["cla::1.1", "ext::S2"]}, ctx["man"])["Q2"]
    R.chequeo("control 4 · dos anclas de TOs distintos se cargan sin abortar",
              [(a["to"], a["punto"]) for a in anclas] == [("cla", "1.1"), ("ext", "2")],
              f"anclas normalizadas {[(a['to'], a['punto']) for a in anclas]}")
    res = verificar_anclas({"Q2": anclas}, ctx["indices"])
    R.chequeo("control 4 · las dos anclas resuelven en la E0", res["resueltas"] == 2 and res["total"] == 2,
              f"{res['resueltas']} de {res['total']}")
    pares = [("cla", "1.1.1"), ("cla", "1.1"), ("ext", "2.1"), ("cla", "2.1"), ("ext", "1.1")]
    casos = [("citas solo a la primera", ["cla | 1.1.1"], SI, NO),
             ("citas a las dos", ["cla | 1.1", "ext | 2.1"], SI, SI),
             ("citas a ninguna", ["cla | 2.1", "ext | 1.1"], NO, NO)]
    for desc, citas, e_p, e_i in casos:
        f = evaluar("C4", "Q2", "selftest", {"citas": citas, "respondible": True}, pares, anclas, ctx)
        obt = (f["ind3_cita_al_ancla"], f["info_cada_ancla_con_cita"])
        R.chequeo(f"control 4 · {desc}", obt == (e_p, e_i),
                  f"principal {obt[0]!r}, informativa {obt[1]!r}, anclas con cita {f['n_anclas_con_cita']} de {f['n_anclas']}")
    try:
        parsear_anclas({"Q3": ["cla::Anexo"]}, ctx["man"])
        abortado = False
    except SystemExit:
        abortado = True
    R.chequeo("control 4 · un ancla con punto no normalizable aborta", abortado)


# ---- control 5: formas en A2.2 --------------------------------------------- #
def control_5(R: Registro, metas_dir: Path, e0_dir: Path) -> None:
    print("CONTROL 5 · formas en A2.2: cuántas citas se parten por forma y por brazo (sin indicadores ni citas)")
    man = manifiesto_desde(None, e0_dir)
    R.info(f"control 5 · manifiesto armado desde {len(man['tos'])} estructura_<to>.json de "
           f"{ruta_legible(e0_dir)}")
    metas = sorted(metas_dir.glob("*/meta_*.json"), key=lambda p: (p.parent.name, p.name))
    R.chequeo("control 5 · metas de A2.2 en el repo", len(metas) == METAS_ESPERADAS_A2_2,
              f"{len(metas)} (esperado {METAS_ESPERADAS_A2_2})")
    por_brazo, sin_json, parseables = {}, {}, {}
    for m in metas:
        meta = json.loads(m.read_text(encoding="utf-8"))
        brazo = meta.get("brazo")
        fj = meta.get("final_json_R4")
        cuenta = por_brazo.setdefault(brazo, {})
        if not isinstance(fj, dict):
            sin_json[brazo] = sin_json.get(brazo, 0) + 1
            continue
        citas = fj.get("citas") or []
        if not isinstance(citas, list):
            R.chequeo(f"control 5 · citas en lista ({brazo})", False)
            continue
        for c in citas:
            p = partir_cita(c, man)
            e = etiqueta_forma(p)
            cuenta[e] = cuenta.get(e, 0) + 1
            parseables[brazo] = parseables.get(brazo, 0) + p["parseable"]
    for brazo in sorted(por_brazo):
        n = sum(por_brazo[brazo].values())
        R.info(f"control 5 · brazo {brazo}: metas {sum(1 for m in metas if m.stem.endswith('-' + brazo))}, "
               f"sin JSON final {sin_json.get(brazo, 0)}, citas {n}, parseables {parseables.get(brazo, 0)}; por forma: "
               + "; ".join(f"«{k}» {v}" for k, v in sorted(por_brazo[brazo].items())))
    por_grupo = {}
    for brazo, cuenta in por_brazo.items():
        g = por_grupo.setdefault(GRUPO_DE_BRAZO.get(brazo, f"otro:{brazo}"), {})
        for k, v in cuenta.items():
            g[k] = g.get(k, 0) + v
    for grupo, esperado in FORMAS_ESPERADAS_A2_2.items():
        obt = por_grupo.get(grupo, {})
        listadas = {k: v for k, v in esperado.items() if k != "otra forma"}
        resto = sum(v for k, v in obt.items() if k not in listadas)
        ok = all(obt.get(k, 0) == v for k, v in listadas.items()) and resto == esperado.get("otra forma", 0)
        R.chequeo(f"control 5 · formas {NOMBRE_GRUPO[grupo]} = las esperadas", ok,
                  "; ".join(f"«{k}» {obt.get(k, 0)} (esperado {v})" for k, v in listadas.items())
                  + f"; de otra forma {resto} (esperado {esperado.get('otra forma', 0)})")
    otros = [g for g in por_grupo if g not in FORMAS_ESPERADAS_A2_2]
    R.chequeo("control 5 · sin brazos fuera de grafo y fragmentos", not otros, f"otros: {otros}")
    total = sum(sum(c.values()) for c in por_brazo.values())
    R.chequeo("control 5 · total de citas = el esperado", total == TOTAL_ESPERADO_A2_2,
              f"{total} (esperado {TOTAL_ESPERADO_A2_2})")
    R.info(f"control 5 · parseables {sum(parseables.values())}, no parseables {total - sum(parseables.values())}")


# ---- controles 6 y 7: las secciones cuyo número no es solo cifras ---------- #
class _EnMemoria:
    """Un estructura_<to>.json en memoria para U2.cargar_indice, que lo lee con read_text: la E0 sintética no se
    escribe a disco."""

    def __init__(self, obj: dict):
        self.texto = json.dumps(obj, ensure_ascii=False)

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.texto


def _ctx_secciones(cita_fiel):
    """Una E0 sintética: en rgl, secciones de cifras («1»), de letras («A», «B», «C» anidada en «B», «E.1») y
    «bloque2»; en otr, la sección «D»."""
    n = lambda num, tipo="punto", hijos=(): {"numero": num, "tipo": tipo, "hijos": list(hijos)}  # noqa: E731
    PR, PO = "TO_reglamento_sintetico_actual.pdf", "TO_otro_sintetico_actual.pdf"
    est = {"rgl": {"to": "rgl", "archivo": PR, "secciones": [
               n("1", "seccion", [n("1.1"), n("1.2")]), n("A", "seccion", [n("2.1")]),
               n("bloque2", "seccion", [n("3.1")]), n("B", "seccion", [n("C", "seccion", [n("4.1")])]),
               n("E.1", "seccion")]},
           "otr": {"to": "otr", "archivo": PO, "secciones": [n("D", "seccion", [n("1.1")])]}}
    man = armar_manifiesto([{"id": t, "archivo": e["archivo"]} for t, e in est.items()],
                           {t: secciones_de_estructura(e) for t, e in est.items()})
    indices = {t: U2.cargar_indice(_EnMemoria(e)) for t, e in est.items()}
    return {"man": man, "indices": indices, "cita_fiel": cita_fiel}, PR, PO


def _aborta(f) -> bool:
    try:
        f()
        return False
    except SystemExit:
        return True


def control_6(R: Registro, cita_fiel, lect: dict) -> None:
    print("CONTROL 6 · secciones que no son solo cifras, sobre una E0 sintética: el lector, la cita, la existente y "
          "el ancla (ancla rgl::SA)")
    ctx, PR, PO = _ctx_secciones(cita_fiel)
    man = ctx["man"]
    R.chequeo("control 6 · secciones de la E0 sintética, leídas de su estructura (secciones → hijos)",
              man["secciones"] == {"rgl": frozenset({"1", "A", "B", "C", "E.1", "bloque2"}), "otr": frozenset({"D"})},
              f"rgl {len(man['secciones']['rgl'])}, otr {len(man['secciones']['otr'])}")
    # El lector.
    vista = "\n".join([
        "vecinos_por_relacion Obligacion_x · remite_a · salientes · punto=rgl::SB · 5 vecinos",
        "vecino | tipo | label | punto | marca (de 0 a 5 de 5)",
        "N1 | Definicion | label | rgl::SC", "N2 | Excepcion | label | rgl::Sbloque2::intro",
        "N3 | Obligacion | label | rgl::SD", "N4 | Obligacion | label | otr::SD", "N5 | Obligacion | label | rgl::Sobre"])
    _caso_lector(R, "vista con secciones de letras y «bloqueN»: cuentan las de ese TO en la E0; «rgl::SD» (sección de "
                    "otro TO), «rgl::Sobre» y la cabecera, no", [("vecinos_por_relacion", vista)], man, lect,
                 [("rgl", "C"), ("rgl", "bloque2"), ("otr", "D")], control="control 6")
    remis = "\n".join(["ver_remisiones rgl::1.1 · saltos 1", "cita: 1 puntos a 1 salto (1 aristas remite_a)",
                       "dir | punto | título | comienzo del texto | n nodos | alcance | salto",
                       "cita | rgl::SE.1 | Título | Comienzo | 0 | — | 1"])
    _caso_lector(R, "vista con la sección «E.1» (letra, punto y cifra)", [("ver_remisiones", remis)], man, lect,
                 [("rgl", "E.1")], control="control 6")
    frag = json.dumps({"consulta": "x", "total_pasajes": 2, "resultados": [
        {"rank": 1, "id": "p1", "to": "rgl", "unidad": "SA", "archivo": PR, "titulo": "t", "tipo": "seccion",
         "paginas": [1], "score": 1.0, "texto": "t"},
        {"rank": 2, "id": "p2", "to": "rgl", "unidad": "SD", "archivo": PR, "titulo": "t", "tipo": "seccion",
         "paginas": [2], "score": 0.5, "texto": "t"}]}, ensure_ascii=False)
    _caso_lector(R, "fragmentos con «SA» (normaliza a A) y «SD» (no es sección de rgl: queda tal cual)",
                 [("buscar_pasajes", frag)], man, lect, [("rgl", "A"), ("rgl", "SD")], control="control 6")
    v1 = json.dumps({"id": "A", "type": "Obligacion", "label": "a", "properties": {}, "provenances": [
        {"source_doc": PR, "location": "Sección A"}, {"source_doc": PR, "location": "Sección bloque2"},
        {"source_doc": PO, "location": "Sección Z"}]}, ensure_ascii=False)
    _caso_lector(R, "firma v1 con «Sección A», «Sección bloque2» y «Sección Z» (no es sección: tal cual)",
                 [("ver_nodo", v1)], man, lect, [("rgl", "A"), ("rgl", "bloque2"), ("otr", "Sección Z")],
                 control="control 6")
    # La cita, la existente y el ancla, contra lo que vieron la vista y la firma v1.
    pares, _ = vistos_de_llamadas([{"tool": "vecinos_por_relacion", "output_str": vista},
                                   {"tool": "ver_nodo", "output_str": v1}], man, lect)
    ancla = parsear_anclas({"Q6": ["rgl::SA"]}, man)["Q6"]
    # (descripción, cita, forma esperada, parseable, (TO, punto), ind1, ind2, ind3)
    casos = [
        ("id del TO | SA", "rgl | SA", "id del TO | Sn", True, ("rgl", "A"), SI, SI, SI),
        ("id del TO | Sbloque2", "rgl | Sbloque2", "id del TO | Sn", True, ("rgl", "bloque2"), SI, SI, NO),
        ("PDF | Sección A", f"{PR} | Sección A", "PDF | Sección n", True, ("rgl", "A"), SI, SI, SI),
        ("id del TO | Sección bloque2", "rgl | Sección bloque2", "id del TO | Sección n", True, ("rgl", "bloque2"),
         SI, SI, NO),
        ("sección anidada «SC»", "rgl | SC", "id del TO | Sn", True, ("rgl", "C"), SI, SI, NO),
        ("sección «SE.1», no vista", "rgl | SE.1", "id del TO | Sn", True, ("rgl", "E.1"), NO, SI, NO),
        ("de cifras «S1», como hoy", "rgl | S1", "id del TO | Sn", True, ("rgl", "1"), NO, SI, NO),
        ("de cifras «S7», fuera de la E0: parseable como hoy", "rgl | S7", "id del TO | Sn", True, ("rgl", "7"),
         NO, NO, NO),
        ("«SD» en otr, su TO", "otr | SD", "id del TO | Sn", True, ("otr", "D"), SI, SI, NO),
        ("«SD» en rgl, que no la tiene (no parseable)", "rgl | SD", "id del TO | otra forma", False, ("rgl", None),
         NO, NO, NO),
        ("«Sobre», palabra con S (no parseable)", "rgl | Sobre", "id del TO | otra forma", False, ("rgl", None),
         NO, NO, NO),
        ("«Sección Única» (no parseable)", "rgl | Sección Única", "id del TO | otra forma", False, ("rgl", None),
         NO, NO, NO),
        ("«A» sin la S (no parseable; ind1 «sí» por la ubicación tal cual, fiel a la vista «Sección A»)", "rgl | A",
         "id del TO | otra forma", False, ("rgl", None), SI, NO, NO),
        ("objeto con «Sección bloque2»", {"source_doc": PR, "location": "Sección bloque2"},
         "objeto: PDF | Sección n", True, ("rgl", "bloque2"), SI, SI, NO),
    ]
    for desc, cita, forma, parseable, (to, punto), e1, e2, e3 in casos:
        p = partir_cita(cita, man)
        f = evaluar("C6", "Q6", "selftest", {"citas": [cita], "respondible": True}, pares, ancla, ctx)
        obt = (etiqueta_forma(p), p["parseable"], p["to"], p["punto"], f["ind1_cita_fundada"], f["ind2_cita_existente"],
               f["ind3_cita_al_ancla"])
        esp = (forma, parseable, to, punto, e1, e2, e3)
        R.chequeo(f"control 6 · {desc}", obt == esp,
                  f"forma «{obt[0]}», parseable {obt[1]}, ind1 / ind2 / ind3 = {obt[4]} / {obt[5]} / {obt[6]}"
                  + ("" if obt == esp else f"; esperado {esp}"))
    anclas = parsear_anclas({"Q7": ["rgl::SA", "rgl::Sbloque2", "rgl::SC", "otr::SD", "rgl::S1"]}, man)["Q7"]
    R.chequeo("control 6 · anclas en secciones de letras, «bloqueN», anidada, de otro TO y de cifras se cargan",
              [(a["to"], a["punto"]) for a in anclas]
              == [("rgl", "A"), ("rgl", "bloque2"), ("rgl", "C"), ("otr", "D"), ("rgl", "1")],
              f"anclas normalizadas {[(a['to'], a['punto']) for a in anclas]}")
    res = verificar_anclas({"Q7": anclas}, ctx["indices"])
    R.chequeo("control 6 · esas anclas resuelven en la E0", res["resueltas"] == res["total"] == 5,
              f"{res['resueltas']} de {res['total']}")
    for mala in ("rgl::SD", "rgl::Sobre", "rgl::A"):
        R.chequeo(f"control 6 · el ancla «{mala}» aborta (no es una «S» seguida de una sección de ese TO)",
                  _aborta(lambda: parsear_anclas({"Q8": [mala]}, man)))
    dos = parsear_anclas({"Q9": ["rgl::SA", "rgl::Sbloque2"]}, man)["Q9"]
    for desc, citas, e_p, e_i in (("citas a una de dos anclas de secciones", ["rgl | Sección A"], SI, NO),
                                  ("citas a las dos", ["rgl | SA", "rgl | Sbloque2"], SI, SI)):
        f = evaluar("C6", "Q9", "selftest", {"citas": citas, "respondible": True}, pares, dos, ctx)
        obt = (f["ind3_cita_al_ancla"], f["info_cada_ancla_con_cita"])
        R.chequeo(f"control 6 · {desc}", obt == (e_p, e_i), f"principal {obt[0]!r}, informativa {obt[1]!r}")


NO_CIFRAS_ESPERADAS_E0_EVALUADA = 211


def control_7(R: Registro, e0_dir: Path) -> None:
    print("CONTROL 7 · la E0 del grafo evaluado: las secciones que no son solo cifras normalizan todas (solo cuentas)")
    man = manifiesto_desde(None, e0_dir)
    indices = cargar_indices(man, e0_dir)
    nodos = []   # (TO, número) de cada nodo de tipo «seccion», con repetición

    def rec(to, n):
        if n.get("tipo") == "seccion":
            nodos.append((to, str(n.get("numero"))))
        for h in n.get("hijos") or []:
            rec(to, h)

    for to in man["tos"]:
        for s in json.loads((e0_dir / f"estructura_{to}.json").read_text(encoding="utf-8")).get("secciones") or []:
            rec(to, s)
    no = [(t, x) for t, x in nodos if not re.fullmatch(r"\d+", x)]
    cif = [(t, x) for t, x in nodos if re.fullmatch(r"\d+", x)]
    R.info(f"control 7 · {ruta_legible(e0_dir)}: {len(man['tos'])} TOs; secciones {len(nodos)}; no solo cifras "
           f"{len(no)}, en {len({t for t, _ in no})} TOs; de cifras {len(cif)}")
    R.chequeo("control 7 · secciones que no son solo cifras = las contadas", len(no) == NO_CIFRAS_ESPERADAS_E0_EVALUADA,
              f"{len(no)} (esperado {NO_CIFRAS_ESPERADAS_E0_EVALUADA})")

    def todas(nombre, pares, f):
        bien = sum(1 for t, x in pares if f(t, x))
        R.chequeo(f"control 7 · {nombre}", bien == len(pares), f"{bien} de {len(pares)}")

    def secs(t):
        return secciones_del(man, t)

    def cita_ok(t, x):
        p = partir_cita(f"{t} | S{x}", man)
        return (p["parseable"], p["to"], p["punto"], p["forma_punto"]) == (True, t, x, "Sn")

    todas("«Sn»: cada una normaliza a su número", no, lambda t, x: normalizar_punto("S" + x, secs(t)) == (x, "Sn"))
    todas("«Sección n»: cada una normaliza a su número", no,
          lambda t, x: normalizar_punto("Sección " + x, secs(t)) == (x, "Sección n"))
    todas("la cita «to | Sn» es parseable, con su TO y su número", no, cita_ok)
    todas("cita existente: cada una resuelve en el índice E0 (cargar_indice de HEAD)", no,
          lambda t, x: U2.resolver_en_indice(t, x, indices)[0] == SI)
    todas("la clave del lector «to::Sn» cuenta, con su número", no,
          lambda t, x: pares_normalizados(claves_en(f"{t}::S{x}", man), man) == [(t, x)])
    todas("el ancla «to::Sn» se carga con su número", no,
          lambda t, x: [(a["to"], a["punto"]) for a in parsear_anclas({"q": [f"{t}::S{x}"]}, man)["q"]] == [(t, x)])
    todas("las de cifras dan lo mismo que sin la E0 («Sn» y «Sección n»)", cif,
          lambda t, x: normalizar_punto("S" + x, secs(t)) == normalizar_punto("S" + x) == (x, "Sn")
          and normalizar_punto("Sección " + x, secs(t)) == normalizar_punto("Sección " + x) == (x, "Sección n"))


def correr_controles(indice_nav: Path, metas_dir: Path, e0_dir: Path, e0_evaluado: Path) -> Registro:
    print("SELFTEST U-CITA-BANCO — sin red, sin API, sin Neo4j, sin el modelo denso")
    ih = verificar_instrumento_head()
    print(f"[candado] scripts/ucita2_indicadores.py sha256 {ih['sha256']} = el de HEAD: OK")
    cita_fiel, norm_loc, collect_provs, tools_v1 = importar_harness_y_lector_v1()
    print(f"[candado] harness importado por U2.importar_harness (ruta y sha256 {U2.SHA_ESPERADOS['harness'][1]}): OK")
    print(f"[lectores] fragmentos {list(TOOLS_FRAGMENTOS)}; firma v1 {list(tools_v1)}; vistas {list(TOOLS_NAV)}")
    R = Registro()
    lect = {"tools_v1": tools_v1, "collect_provs": collect_provs}
    control_1(R, cita_fiel, norm_loc)
    control_2(R, lect, indice_nav)
    control_3(R, cita_fiel, norm_loc)
    control_4(R, cita_fiel)
    control_5(R, metas_dir, e0_dir)
    control_6(R, cita_fiel, lect)
    control_7(R, e0_evaluado)
    return R


def selftest(indice_nav: Path, metas_dir: Path, e0_dir: Path, e0_evaluado: Path) -> int:
    R = correr_controles(indice_nav, metas_dir, e0_dir, e0_evaluado)
    n = sum(1 for x in R.lineas if "[PASS]" in x or "[FAIL]" in x)
    print(f"SELFTEST U-CITA-BANCO: {n} chequeos; fallas = {R.fallas}")
    return 1 if R.fallas else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="U-CITA-BANCO: exactitud de cita sobre sesiones del banco (USD 0).")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--indice-nav", type=Path, default=INDICE_NAV_DEFAULT,
                    help="índice por punto de N5 para el control 2 del selftest")
    ap.add_argument("--metas-a2-2", type=Path, default=METAS_A2_2, help="resultados de A2.2 para el control 5")
    ap.add_argument("--e0-a2-2", type=Path, default=E0_A2_2, help="E0 del grafo de A2.2 para el control 5")
    ap.add_argument("--e0-evaluado", type=Path, default=E0_EVALUADA, help="E0 del grafo evaluado para el control 7")
    ap.add_argument("--sesiones", type=Path, nargs="+", help="carpetas con meta_<id>.json y log_r1_<id>.jsonl")
    ap.add_argument("--anclas", type=Path, help="JSON {pregunta: [\"to::punto\", ...]}")
    ap.add_argument("--e0", type=Path, help="carpeta de la E0 con estructura_<to>.json")
    ap.add_argument("--manifiesto", type=Path, default=None, help="manifiesto {tos: [{id, archivo}]} (opcional)")
    ap.add_argument("--mapa-sesiones", type=Path, default=None, help="JSON {sesión: pregunta} (opcional)")
    ap.add_argument("--out-json", type=Path, help="ruta del JSON de salida")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.indice_nav, a.metas_a2_2, a.e0_a2_2, a.e0_evaluado)
    faltan = [n for n, v in (("--sesiones", a.sesiones), ("--anclas", a.anclas), ("--e0", a.e0),
                             ("--out-json", a.out_json)) if not v]
    if faltan:
        ap.error("faltan " + ", ".join(faltan))
    for nombre, p in (("--anclas", a.anclas), ("--manifiesto", a.manifiesto), ("--mapa-sesiones", a.mapa_sesiones)):
        if p is not None and not p.is_file():
            raise SystemExit(f"ABORTO: {nombre} no es un archivo: {p}")
    for p in [a.e0, *a.sesiones]:
        if not p.is_dir():
            raise SystemExit(f"ABORTO: no es una carpeta: {p}")
    return correr({"sesiones": a.sesiones, "anclas": a.anclas, "e0": a.e0, "manifiesto": a.manifiesto,
                   "mapa_sesiones": a.mapa_sesiones, "out_json": a.out_json})


if __name__ == "__main__":
    sys.exit(main())
