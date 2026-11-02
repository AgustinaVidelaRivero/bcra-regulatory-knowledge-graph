#!/usr/bin/env python3
"""ucita2_indicadores.py — U-CITA-2: componente «exactitud de cita» (B6.3), validación en desarrollo.

Computa, por respuesta y sin juez ni API (USD 0), tres indicadores
determinísticos sobre las 112 trazas de KG-Reextraído-r1 en
data/experiment/ev2_r1/trazas/ (cuatro tandas: base 40, enc_r1 24, enc_r2 24,
enc_r3 24; se reporta POR TANDA, sin pool):

  1. cita fundada    — TODA cita de la respuesta es fiel a alguna entrada de
                       trace.seen_provenances de la MISMA traza, según
                       _cita_fiel / _norm_loc IMPORTADAS del harness congelado
                       (lectura normalizada, principal). Al lado, lectura
                       byte-exacta: tupla (source_doc, location) idéntica a
                       alguna entrada.
  2. cita existente  — TODA cita parseable resuelve a un nodo del índice E0 de
                       su TO (valores `numero` recorriendo `secciones` → `hijos`
                       hasta las hojas).
  3. cita al ancla   — ALGUNA cita tiene el TO del ancla de la clave y su punto
                       normalizado es el ancla o empieza con el ancla seguido
                       de «.». Los ancestros del ancla NO cuentan; van en una
                       columna informativa aparte.

Cita parseable (decisión 3): source_doc ~ ^TO_[a-z_]+_actual\\.pdf$ y location
~ ^Punto (\\d+(?:\\.\\d+)*)\\.?$ o ^Sección (\\d+)$; el punto normalizado es el
grupo capturado. El TO de una cita es el que el manifiesto asocia a su
source_doc. Toda cita no parseable se lista una por una y cuenta como «no» en
los indicadores 2 y 3 de su respuesta.

Valores por indicador: "si" | "no" | "sin_citas" (lista vacía o ausente; nunca
«sí» por vacuidad) | "sin_json" (parse_ok falso; conteo aparte). El indicador 2
admite además "fuera_de_indice": el punto tiene más niveles que la profundidad
máxima del índice de su TO y su prefijo a esa profundidad existe. Precedencia
del indicador 2 dentro de una respuesta: alguna cita inexistente o no
parseable → "no"; si no, alguna fuera_de_indice → "fuera_de_indice"; si no →
"si".

Control obligatorio del indicador 1: las citas que fallan se recomputan con la
misma regla del harness (harness.py:551-560) y deben coincidir exactamente con
trace.citations_unseen_normalized / trace.citations_unseen_raw persistidas.

Abstenciones: respondible == false. Por tanda se presentan tres tablas (todas /
solo contenido / solo abstención); los indicadores se computan igual en las
tres. Agregación: fracción cruda «n de N»; sin porcentajes, sin pool, sin
intervalos. Sin cruce con veredictos del juez ni con atribuciones.

Salidas (únicas escrituras): reports/ucita2_indicadores.json (una fila por
traza, ordenadas por (tanda, id)) y reports/ucita2_indicadores.md (derivado del
JSON ya escrito en disco, nunca al revés). Sin timestamps: dos corridas
consecutivas producen un JSON byte-idéntico.

Uso (desde la raíz del repo):
  PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ucita2_indicadores.py --selftest
  PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ucita2_indicadores.py

Parametrización (gate 6 de la fase 2 de B6.0; extensión aditiva). Sin
argumentos el comportamiento es idéntico al descripto arriba. Argumentos
nuevos, cada uno con default igual a la constante que reemplaza:
  --gold RUTA · --manifiesto RUTA · --e0 DIRECTORIO · --trazas DIRECTORIO ·
  --tandas T1 [T2 ...] · --out-json RUTA · --out-md RUTA
Los TOs se leen del manifiesto (ids ordenados alfabéticamente). Los candados
de sha de insumos (SHA_ESPERADOS) y de digest de tandas (DIGEST_ESPERADOS)
rigen solo cuando gold, manifiesto, e0, trazas y tandas son los defaults; con
argumentos distintos el JSON registra el sha256 de cada insumo y el digest de
cada tanda como «medido, sin esperado» y no frena por ellos (el harness
congelado se verifica siempre: no es un parámetro). La conciliación con las
cifras de U-CITA rige solo con las tandas default; con otras, la sección se
emite vacía y rotulada «sin conciliación», y los conteos descriptivos por
tanda van en `resumen_por_tanda`. En modo parametrizado el JSON suma la clave
`parametrizacion` (argumentos resueltos, sha256 del script, régimen de
candados y de conciliación); en modo default no se agrega ninguna clave.
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
EVAL_DIR = REPO / "data" / "experiment" / "evaluacion"
HARNESS_PATH = EVAL_DIR / "harness.py"
GOLD_PATH = REPO / "data/experiment/exploracion/ev2_fidelidad/preguntas_ev2_fidelidad.json"
MANIFIESTO_PATH = REPO / "data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json"
E0_DIR = REPO / "data/experiment/reextraccion_v2/e0_chunking/salida_enm01"
TRAZAS_DIR = REPO / "data/experiment/ev2_r1/trazas"
OUT_JSON = REPO / "reports/ucita2_indicadores.json"
OUT_MD = REPO / "reports/ucita2_indicadores.md"

TOS = ("cap", "cla", "ext", "pro", "ric")
TANDAS = ("ev2_r1_base", "ev2_r1_enc_r1", "ev2_r1_enc_r2", "ev2_r1_enc_r3")

# Decisión 2 del mandato: sha256 de insumos, verificados al inicio y al cierre.
SHA_ESPERADOS = {
    "gold": (GOLD_PATH, "1d58733699c325c90510e1ead5f18eac6c3cd970ee3b0ab7ff141da539162b40"),
    "harness": (HARNESS_PATH, "fd267e833866f86850e43130e627b08d78e05523b97484696de0ab0c8c9fba9e"),
    "manifiesto": (MANIFIESTO_PATH, "868b301fe800961804b58bf381e925ae76e442863aea8afb432ef4949e1f5ffc"),
    "e0_cap": (E0_DIR / "estructura_cap.json", "eae830c7640f132986327dd9a065535573bf1c343d804492d272154d700daf55"),
    "e0_cla": (E0_DIR / "estructura_cla.json", "3cd26083fee7355ef3d8027ac353a744c2f1cfa35830535fe1be2b9505eaf917"),
    "e0_ext": (E0_DIR / "estructura_ext.json", "0b0137d58decb66d66bbb6f60d0192071d2b2ee0c819ee95658f9f31881c6d53"),
    "e0_pro": (E0_DIR / "estructura_pro.json", "4126ec9e20b2d53094a1f77dd4d5676e117995c8338ce0883a5a9dd3b5d318ae"),
    "e0_ric": (E0_DIR / "estructura_ric.json", "64cbd27f277f75ab4919863ed3fcd98c93238a8d9e5f7c57dd80c40487230892"),
}
# Digest de tanda: sha256 sobre las líneas "<sha256 archivo>  <nombre>\n" de los
# EV2F-*.json ordenados por nombre.
DIGEST_ESPERADOS = {
    "ev2_r1_base": "d53316edd5082b562d542923d8c799c6355d5e2146f597741c77d5c035b5c25f",
    "ev2_r1_enc_r1": "4b9499e91bb0b1e186d39ee478e5df23d31d8259e8ec8fff2449c009aba1fadd",
    "ev2_r1_enc_r2": "de644c9295bd82918b1bd45b4e3c4e078e8c24503f779bee0031e154f984c437",
    "ev2_r1_enc_r3": "a80cc1fb907d5aaeb510dedde1eac707c6206423033cce408aba10073b772ce7",
}

# Cifras de U-CITA (reports/inventario_UCITA.md §4-§5) que el criterio de
# aceptación b/c pide conciliar. Las re-corridas no traen cifra previa para
# abstenciones: se reporta el conteo sin conciliar.
ESPERADO_UCITA = {
    "trazas": {"ev2_r1_base": 40, "ev2_r1_enc_r1": 24, "ev2_r1_enc_r2": 24, "ev2_r1_enc_r3": 24},
    "citas_parseables": {"ev2_r1_base": 98, "ev2_r1_enc_r1": 67, "ev2_r1_enc_r2": 63, "ev2_r1_enc_r3": 62},
    "respuestas_con_cita_parseable": {"ev2_r1_base": 40, "ev2_r1_enc_r1": 24, "ev2_r1_enc_r2": 23, "ev2_r1_enc_r3": 24},
    "abstenciones": {"ev2_r1_base": 9},
    "citas_no_fundadas_normalizada": {"ev2_r1_base": 3, "ev2_r1_enc_r1": 0, "ev2_r1_enc_r2": 0, "ev2_r1_enc_r3": 0},
    "trazas_con_citas_no_fundadas": {"ev2_r1_base": {"EV2F-014": 1, "EV2F-023": 2},
                                     "ev2_r1_enc_r1": {}, "ev2_r1_enc_r2": {}, "ev2_r1_enc_r3": {}},
}

RE_DOC = re.compile(r"^TO_[a-z_]+_actual\.pdf$")
RE_PUNTO = re.compile(r"^Punto (\d+(?:\.\d+)*)\.?$")
RE_SECCION = re.compile(r"^Sección (\d+)$")

SI, NO, SIN_CITAS, SIN_JSON, FUERA = "si", "no", "sin_citas", "sin_json", "fuera_de_indice"
VALORES = (SI, NO, FUERA, SIN_CITAS, SIN_JSON)
INDICADORES = (
    ("ind1_cita_fundada", "1 · cita fundada (normalizada, principal)"),
    ("ind1_byte_exacta", "1 · cita fundada (byte-exacta)"),
    ("ind2_cita_existente", "2 · cita existente (índice E0)"),
    ("ind3_cita_al_ancla", "3 · cita al punto de referencia"),
    ("info_cita_ancestro_del_ancla", "informativa · cita ancestro del ancla"),
)
GRUPOS = (("todas", "todas las respuestas"), ("contenido", "solo contenido (respondible true)"),
          ("abstencion", "solo abstención (respondible false)"))


# --------------------------------------------------------------------------- #
# Integridad de insumos                                                        #
# --------------------------------------------------------------------------- #
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def archivos_tanda(tanda: str, trazas_dir: Path = TRAZAS_DIR) -> list:
    return sorted((trazas_dir / tanda).glob("EV2F-*.json"), key=lambda p: p.name)


def digest_tanda(tanda: str, trazas_dir: Path = TRAZAS_DIR) -> str:
    h = hashlib.sha256()
    for p in archivos_tanda(tanda, trazas_dir):
        h.update(f"{sha256_file(p)}  {p.name}\n".encode("utf-8"))
    return h.hexdigest()


def _ruta_legible(p: Path) -> str:
    """Ruta relativa al repo cuando está adentro; absoluta si no (scratchpad)."""
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p.resolve())


def _tos_del_manifiesto(manifiesto_path: Path) -> tuple:
    m = json.loads(manifiesto_path.read_text(encoding="utf-8"))
    return tuple(sorted(t["id"] for t in m["tos"]))


def verificar_insumos(momento: str, cfg: dict | None = None) -> dict:
    """Recalcula los sha de la decisión 2; aborta ante cualquier diferencia.

    Con `cfg` en modo parametrizado (algún insumo o la lista de tandas distinta
    del default) los sha y digests se MIDEN y se registran sin esperado; solo
    el harness congelado conserva su candado (no es un parámetro)."""
    if cfg is None or cfg["modo_default"]:
        res, fallas = {}, []
        for clave, (ruta, esperado) in SHA_ESPERADOS.items():
            obtenido = sha256_file(ruta)
            res[clave] = {"ruta": str(ruta.relative_to(REPO)), "sha256_esperado": esperado, "sha256": obtenido}
            if obtenido != esperado:
                fallas.append(f"{clave} ({ruta.relative_to(REPO)}): esperado {esperado}, obtenido {obtenido}")
        for tanda, esperado in DIGEST_ESPERADOS.items():
            obtenido = digest_tanda(tanda)
            res[f"digest_{tanda}"] = {"ruta": str((TRAZAS_DIR / tanda).relative_to(REPO)),
                                      "sha256_esperado": esperado, "sha256": obtenido,
                                      "n_archivos": len(archivos_tanda(tanda))}
            if obtenido != esperado:
                fallas.append(f"digest {tanda}: esperado {esperado}, obtenido {obtenido}")
        if fallas:
            raise SystemExit(f"ABORTO ({momento}): sha de insumos distintos de la decisión 2:\n  "
                             + "\n  ".join(fallas))
        print(f"[sha {momento}] {len(res)} insumos (8 archivos + 4 digests de tanda) coinciden con la decisión 2: OK")
        return res

    # Modo parametrizado: medido, sin esperado (salvo el harness congelado).
    res = {}
    archivos = {"gold": cfg["gold"], "manifiesto": cfg["manifiesto"]}
    for to in cfg["tos"]:
        archivos[f"e0_{to}"] = cfg["e0"] / f"estructura_{to}.json"
    for clave, ruta in archivos.items():
        res[clave] = {"ruta": _ruta_legible(ruta), "sha256_esperado": None, "sha256": sha256_file(ruta),
                      "estado": "medido, sin esperado"}
    esperado_h = SHA_ESPERADOS["harness"][1]
    obtenido_h = sha256_file(HARNESS_PATH)
    res["harness"] = {"ruta": str(HARNESS_PATH.relative_to(REPO)), "sha256_esperado": esperado_h,
                      "sha256": obtenido_h, "estado": "candado vigente (harness congelado, no parametrizable)"}
    if obtenido_h != esperado_h:
        raise SystemExit(f"ABORTO ({momento}): harness congelado con sha256 distinto del esperado: {obtenido_h}")
    for tanda in cfg["tandas"]:
        n = len(archivos_tanda(tanda, cfg["trazas"]))
        if n == 0:
            raise SystemExit(f"ABORTO ({momento}): la tanda {tanda!r} no tiene archivos EV2F-*.json en {cfg['trazas']}")
        res[f"digest_{tanda}"] = {"ruta": _ruta_legible(cfg["trazas"] / tanda), "sha256_esperado": None,
                                  "sha256": digest_tanda(tanda, cfg["trazas"]), "n_archivos": n,
                                  "estado": "medido, sin esperado"}
    print(f"[sha {momento}] modo parametrizado: {len(archivos)} archivos + {len(cfg['tandas'])} digests de tanda "
          f"medidos sin esperado; harness congelado verificado: OK")
    return res


def importar_harness():
    """Importa _cita_fiel y _norm_loc del harness congelado, sin modificarlo.

    A nivel de módulo, harness.py solo define constantes, expresiones regulares,
    clases y funciones (harness.py:31-636): load_dotenv, la lectura de
    ANTHROPIC_API_KEY y argparse quedan bajo `if __name__ == "__main__"`
    (harness.py:639-660); el cliente de API se instancia dentro de
    GraphAgent.__init__ (harness.py:429-430) y el mkdir dentro de run_corrida
    (harness.py:605). loader.py (importado en harness.py:42) tampoco ejecuta
    nada a nivel de módulo. Se verifica que el módulo importado sea exactamente
    el archivo sellado (ruta y sha256).
    """
    sys.path.insert(0, str(EVAL_DIR))
    import harness  # noqa: E402  (módulo congelado, solo lectura)
    import loader   # noqa: E402

    real = Path(harness.__file__).resolve()
    if real != HARNESS_PATH.resolve():
        raise SystemExit(f"ABORTO: se importó otro harness: {real}")
    if sha256_file(real) != SHA_ESPERADOS["harness"][1]:
        raise SystemExit("ABORTO: el harness importado no tiene el sha256 esperado")
    if Path(loader.__file__).resolve().parent != EVAL_DIR.resolve():
        raise SystemExit(f"ABORTO: se importó otro loader: {loader.__file__}")
    return harness._cita_fiel, harness._norm_loc


# --------------------------------------------------------------------------- #
# Insumos estructurales                                                        #
# --------------------------------------------------------------------------- #
def cargar_indice(ruta: Path) -> dict:
    """Conjunto de `numero` del índice E0 recorriendo secciones → hijos (decisión 5)."""
    e = json.loads(ruta.read_text(encoding="utf-8"))
    numeros, n_nodos, prof = set(), 0, 0

    def rec(n):
        nonlocal n_nodos, prof
        num = str(n.get("numero"))
        numeros.add(num)
        n_nodos += 1
        prof = max(prof, len(num.split(".")))
        for h in n.get("hijos") or []:
            rec(h)

    for s in e.get("secciones") or []:
        rec(s)
    return {"numeros": numeros, "n_nodos": n_nodos, "n_numeros_distintos": len(numeros),
            "profundidad_max": prof, "archivo": e.get("archivo"), "to": e.get("to")}


def cargar_contexto(cita_fiel, norm_loc, cfg: dict | None = None) -> dict:
    manifiesto_path = MANIFIESTO_PATH if cfg is None else cfg["manifiesto"]
    e0_dir = E0_DIR if cfg is None else cfg["e0"]
    gold_path = GOLD_PATH if cfg is None else cfg["gold"]
    m = json.loads(manifiesto_path.read_text(encoding="utf-8"))
    doc2to = {t["archivo"]: t["id"] for t in m["tos"]}
    to2doc = {t["id"]: t["archivo"] for t in m["tos"]}
    # Los TOs se leen del manifiesto (ids ordenados alfabéticamente; con el
    # manifiesto default coincide con la tupla TOS).
    tos = tuple(sorted(to2doc))
    indices = {}
    for to in tos:
        idx = cargar_indice(e0_dir / f"estructura_{to}.json")
        if idx["archivo"] != to2doc.get(to) or idx["to"] != to:
            raise SystemExit(f"ABORTO: índice E0 de {to} no coincide con el manifiesto "
                             f"({idx['to']!r}, {idx['archivo']!r} vs {to2doc.get(to)!r})")
        indices[to] = idx
    g = json.loads(gold_path.read_text(encoding="utf-8"))
    gold = {}
    for p in g["preguntas"]:
        anclas = p["gold"]["ancla"]
        if len(anclas) != 1:
            raise SystemExit(f"ABORTO: {p['id']} tiene {len(anclas)} anclas; el instrumento asume una")
        to, punto = anclas[0].split(":", 1)
        if to != p["to"]:
            raise SystemExit(f"ABORTO: {p['id']} ancla {anclas[0]!r} no coincide con to={p['to']!r}")
        gold[p["id"]] = {"ancla": anclas[0], "to": to, "punto": punto}
    return {"manifiesto": doc2to, "indices": indices, "gold": gold,
            "cita_fiel": cita_fiel, "norm_loc": norm_loc, "tos": tos}


def verificar_anclas(ctx: dict) -> dict:
    """Criterio d: cada ancla del gold resuelve en el índice E0 de su TO."""
    no_resueltas = []
    for qid in sorted(ctx["gold"]):
        a = ctx["gold"][qid]
        if a["punto"] not in ctx["indices"][a["to"]]["numeros"]:
            no_resueltas.append({"id": qid, "ancla": a["ancla"]})
    total = len(ctx["gold"])
    return {"resueltas": total - len(no_resueltas), "total": total, "no_resueltas": no_resueltas}


# --------------------------------------------------------------------------- #
# Indicadores por traza                                                        #
# --------------------------------------------------------------------------- #
def parsear_cita(c, manifiesto: dict) -> dict:
    """Decisión 3. `to` queda None si el source_doc no está en el manifiesto."""
    if not isinstance(c, dict):
        return {"parseable": False, "to": None, "punto": None, "motivo": "cita_no_es_objeto"}
    doc, loc = c.get("source_doc"), c.get("location")
    if not isinstance(doc, str) or not RE_DOC.match(doc):
        return {"parseable": False, "to": None, "punto": None, "motivo": "source_doc_no_parseable"}
    if not isinstance(loc, str):
        return {"parseable": False, "to": None, "punto": None, "motivo": "location_no_parseable"}
    m = RE_PUNTO.match(loc) or RE_SECCION.match(loc)
    if not m:
        return {"parseable": False, "to": None, "punto": None, "motivo": "location_no_parseable"}
    to = manifiesto.get(doc)
    return {"parseable": True, "to": to, "punto": m.group(1),
            "motivo": None if to is not None else "source_doc_sin_to_en_manifiesto"}


def resolver_en_indice(to: str, punto: str, indices: dict):
    """(estado, prefijo) con estado en {si, no, fuera_de_indice}; decisión 5."""
    idx = indices[to]
    if punto in idx["numeros"]:
        return SI, punto
    partes = punto.split(".")
    prof = idx["profundidad_max"]
    if len(partes) > prof and ".".join(partes[:prof]) in idx["numeros"]:
        return FUERA, ".".join(partes[:prof])
    for k in range(len(partes) - 1, 0, -1):
        cand = ".".join(partes[:k])
        if cand in idx["numeros"]:
            return NO, cand
    return NO, ""


def es_ancla_o_descendiente(to, punto, ancla) -> bool:
    return to == ancla["to"] and (punto == ancla["punto"] or punto.startswith(ancla["punto"] + "."))


def es_ancestro_del_ancla(to, punto, ancla) -> bool:
    return to == ancla["to"] and ancla["punto"].startswith(punto + ".")


def _fila_base(tanda, tr, ancla) -> dict:
    return {"tanda": tanda, "id": tr.get("qid"), "ancla": ancla["ancla"],
            "parse_ok": bool(tr.get("parse_ok")), "respondible": None, "grupo": None,
            "n_citas": None, "n_parseables": None,
            "ind1_cita_fundada": None, "ind1_byte_exacta": None, "ind2_cita_existente": None,
            "ind3_cita_al_ancla": None, "info_cita_ancestro_del_ancla": None,
            "citas_no_fundadas": [], "citas_no_fundadas_byte_exacta": [],
            "citas_no_existentes": [], "citas_fuera_de_indice": [], "citas_no_parseables": [],
            "detalle_citas": [], "control_ind1": None}


def _set_todos(fila: dict, valor: str) -> None:
    for k, _ in INDICADORES:
        fila[k] = valor


def evaluar_traza(tanda: str, tr: dict, ctx: dict) -> dict:
    qid = tr.get("qid")
    ancla = ctx["gold"].get(qid)
    if ancla is None:
        raise SystemExit(f"ABORTO: traza {tanda}/{qid} sin clave en el gold")
    fila = _fila_base(tanda, tr, ancla)
    fj = tr.get("final_json")
    seen = tr.get("seen_provenances") or []
    seen_keys = {(p.get("source_doc"), p.get("location")) for p in seen}
    con_json = bool(tr.get("parse_ok")) and isinstance(fj, dict)

    # Control del indicador 1: réplica exacta de harness.py:551-560 (solo citas
    # que son objetos; parse_ok falso → listas vacías, como persiste el harness).
    rec_raw, rec_norm = [], []
    if con_json:
        citas_h = fj.get("citas") or []
        if not isinstance(citas_h, list):
            raise SystemExit(f"ABORTO: {tanda}/{qid}: final_json.citas no es una lista")
        for c in citas_h:
            if isinstance(c, dict):
                if (c.get("source_doc"), c.get("location")) not in seen_keys:
                    rec_raw.append(c)
                if not ctx["cita_fiel"](c, seen):
                    rec_norm.append(c)
    pers_raw = tr.get("citations_unseen_raw") or []
    pers_norm = tr.get("citations_unseen_normalized") or []
    control = {"ok": rec_raw == pers_raw and rec_norm == pers_norm,
               "n_recomputo_raw": len(rec_raw), "n_persistida_raw": len(pers_raw),
               "n_recomputo_normalizada": len(rec_norm), "n_persistida_normalizada": len(pers_norm)}
    if not control["ok"]:
        control["discrepancia"] = {"recomputo_raw": rec_raw, "persistida_raw": pers_raw,
                                   "recomputo_normalizada": rec_norm, "persistida_normalizada": pers_norm}
    fila["control_ind1"] = control

    if not con_json:
        fila["grupo"] = "sin_json"
        _set_todos(fila, SIN_JSON)
        return fila

    respondible = fj.get("respondible")
    fila["respondible"] = respondible
    fila["grupo"] = "abstencion" if respondible is False else "contenido"
    citas = fj.get("citas")
    citas = [] if citas is None else citas
    fila["n_citas"] = len(citas)
    if not citas:
        fila["n_parseables"] = 0
        _set_todos(fila, SIN_CITAS)
        return fila

    detalle = []
    for i, c in enumerate(citas):
        p = parsear_cita(c, ctx["manifiesto"])
        es_dict = isinstance(c, dict)
        d = {"i": i,
             "source_doc": c.get("source_doc") if es_dict else None,
             "location": c.get("location") if es_dict else None,
             "location_normalizada": ctx["norm_loc"](c.get("location")) if es_dict and isinstance(c.get("location"), str) else None,
             "parseable": p["parseable"], "to": p["to"], "punto": p["punto"],
             "motivo_no_parseable": p["motivo"],
             "fundada_normalizada": bool(es_dict and ctx["cita_fiel"](c, seen)),
             "fundada_byte_exacta": bool(es_dict and (c.get("source_doc"), c.get("location")) in seen_keys)}
        if p["parseable"] and p["to"] in ctx["indices"]:
            d["existe"], d["prefijo_existente"] = resolver_en_indice(p["to"], p["punto"], ctx["indices"])
        elif p["parseable"]:
            d["existe"], d["prefijo_existente"] = NO, None
        else:
            d["existe"], d["prefijo_existente"] = "no_parseable", None
        con_to = p["parseable"] and p["to"] is not None
        d["al_ancla"] = bool(con_to and es_ancla_o_descendiente(p["to"], p["punto"], ancla))
        d["ancestro_del_ancla"] = bool(con_to and es_ancestro_del_ancla(p["to"], p["punto"], ancla))
        detalle.append(d)

    fila["detalle_citas"] = detalle
    fila["n_parseables"] = sum(1 for d in detalle if d["parseable"])
    fila["ind1_cita_fundada"] = SI if all(d["fundada_normalizada"] for d in detalle) else NO
    fila["ind1_byte_exacta"] = SI if all(d["fundada_byte_exacta"] for d in detalle) else NO
    existes = [d["existe"] for d in detalle]
    if any(e in (NO, "no_parseable") for e in existes):
        fila["ind2_cita_existente"] = NO
    elif any(e == FUERA for e in existes):
        fila["ind2_cita_existente"] = FUERA
    else:
        fila["ind2_cita_existente"] = SI
    fila["ind3_cita_al_ancla"] = SI if any(d["al_ancla"] for d in detalle) else NO
    fila["info_cita_ancestro_del_ancla"] = SI if any(d["ancestro_del_ancla"] for d in detalle) else NO

    def cita(d, *extra):
        out = {"source_doc": d["source_doc"], "location": d["location"]}
        for k in extra:
            out[k] = d[k]
        return out

    fila["citas_no_fundadas"] = [cita(d) for d in detalle if not d["fundada_normalizada"]]
    fila["citas_no_fundadas_byte_exacta"] = [cita(d) for d in detalle if not d["fundada_byte_exacta"]]
    fila["citas_no_existentes"] = [cita(d, "to", "punto", "prefijo_existente", "motivo_no_parseable")
                                   for d in detalle if d["existe"] == NO]
    fila["citas_fuera_de_indice"] = [cita(d, "to", "punto", "prefijo_existente")
                                     for d in detalle if d["existe"] == FUERA]
    fila["citas_no_parseables"] = [cita(d, "motivo_no_parseable") for d in detalle if not d["parseable"]]
    return fila


# --------------------------------------------------------------------------- #
# Agregación y conciliación                                                    #
# --------------------------------------------------------------------------- #
def agregar(filas: list) -> dict:
    out = {}
    for tanda in sorted({f["tanda"] for f in filas}):
        ft = [f for f in filas if f["tanda"] == tanda]
        grupos = {"todas": ft,
                  "contenido": [f for f in ft if f["grupo"] == "contenido"],
                  "abstencion": [f for f in ft if f["grupo"] == "abstencion"]}
        out[tanda] = {"n_sin_json": sum(1 for f in ft if f["grupo"] == "sin_json")}
        for g, fs in grupos.items():
            tabla = {"N": len(fs)}
            for k, _ in INDICADORES:
                tabla[k] = {v: sum(1 for f in fs if f[k] == v) for v in VALORES}
            out[tanda][g] = tabla
    return out


def _contar_tanda(ft: list) -> dict:
    """Conteos descriptivos de una tanda (los mismos que concilia U-CITA)."""
    nf = {}
    for f in ft:
        if f["citas_no_fundadas"]:
            nf[f["id"]] = len(f["citas_no_fundadas"])
    return {"trazas": len(ft),
            "citas_totales": sum(f["n_citas"] or 0 for f in ft),
            "citas_parseables": sum(f["n_parseables"] or 0 for f in ft),
            "respuestas_con_cita_parseable": sum(1 for f in ft if (f["n_parseables"] or 0) > 0),
            "abstenciones": sum(1 for f in ft if f["grupo"] == "abstencion"),
            "contenido": sum(1 for f in ft if f["grupo"] == "contenido"),
            "sin_json": sum(1 for f in ft if f["grupo"] == "sin_json"),
            "sin_citas": sum(1 for f in ft if f["ind1_cita_fundada"] == SIN_CITAS),
            "citas_no_fundadas_normalizada": sum(len(f["citas_no_fundadas"]) for f in ft),
            "citas_no_fundadas_byte_exacta": sum(len(f["citas_no_fundadas_byte_exacta"]) for f in ft),
            "trazas_con_citas_no_fundadas": nf,
            "citas_no_existentes": sum(len(f["citas_no_existentes"]) for f in ft),
            "citas_fuera_de_indice": sum(len(f["citas_fuera_de_indice"]) for f in ft),
            "citas_no_parseables": sum(len(f["citas_no_parseables"]) for f in ft),
            "control_ind1_discrepancias": sum(1 for f in ft if not f["control_ind1"]["ok"]),
            "control_ind1_trazas_con_discrepancia": [f["id"] for f in ft if not f["control_ind1"]["ok"]]}


def conciliar(filas: list) -> dict:
    """Conciliación con las cifras de U-CITA: rige solo con las tandas default."""
    por_tanda, diferencias = {}, []
    for tanda in TANDAS:
        ft = [f for f in filas if f["tanda"] == tanda]
        c = _contar_tanda(ft)
        por_tanda[tanda] = c
        for clave, esperados in ESPERADO_UCITA.items():
            if tanda in esperados and c[clave] != esperados[tanda]:
                diferencias.append({"tanda": tanda, "medida": clave,
                                    "esperado": esperados[tanda], "computado": c[clave]})
    return {"por_tanda": por_tanda, "esperado_ucita": ESPERADO_UCITA, "diferencias": diferencias,
            "control_ind1_discrepancias_total": sum(c["control_ind1_discrepancias"] for c in por_tanda.values())}


SIN_CONCILIACION = "sin conciliación"


def sin_conciliacion(tandas: tuple) -> dict:
    """Sección de conciliación vacía y rotulada, para tandas distintas de las default."""
    return {"estado": SIN_CONCILIACION,
            "motivo": f"las cifras de U-CITA (reports/inventario_UCITA.md §4-§5) solo aplican a las tandas "
                      f"default {list(TANDAS)}; tandas de esta corrida: {list(tandas)}",
            "por_tanda": {}, "esperado_ucita": {}, "diferencias": []}


def resumen_por_tanda(filas: list, tandas: tuple) -> dict:
    """Conteos descriptivos por tanda (modo parametrizado; sin cifra esperada)."""
    por_tanda = {tanda: _contar_tanda([f for f in filas if f["tanda"] == tanda]) for tanda in tandas}
    return {"por_tanda": por_tanda,
            "control_ind1_discrepancias_total": sum(c["control_ind1_discrepancias"] for c in por_tanda.values())}


# --------------------------------------------------------------------------- #
# Reporte .md (derivado del JSON en disco)                                     #
# --------------------------------------------------------------------------- #
def _n_de(n: int, N: int) -> str:
    return f"{n} de {N}"


def _tabla_indicadores(t: dict) -> list:
    N = t["N"]
    lineas = ["| indicador | sí | no | fuera_de_indice | sin_citas | sin_json | N |",
              "|---|---|---|---|---|---|---|"]
    for k, nombre in INDICADORES:
        v = t[k]
        lineas.append(f"| {nombre} | {_n_de(v[SI], N)} | {v[NO]} | {v[FUERA]} | {v[SIN_CITAS]} | {v[SIN_JSON]} | {N} |")
    return lineas


def _fmt_cita(c: dict) -> str:
    return f"`{c.get('source_doc')}` / `{c.get('location')}`"


def render_md(datos: dict, sha_json: str, cfg: dict | None = None) -> str:
    parametrizado = "parametrizacion" in datos
    tos = sorted(datos["indice_e0"])            # = TOS con el manifiesto default
    tandas = list(datos["agregados"])           # el JSON en disco está con sort_keys
    out_json_legible = "reports/ucita2_indicadores.json" if cfg is None else _ruta_legible(cfg["out_json"])
    L = []
    if not parametrizado:
        L += ["# U-CITA-2 — indicadores de exactitud de cita sobre KG-Reextraído-r1",
              "",
              "Validación en desarrollo del componente «exactitud de cita» de B6.3: tres",
              "indicadores determinísticos por respuesta, sin juez ni API (USD 0), sobre las",
              "cuatro tandas de trazas de `data/experiment/ev2_r1/trazas/`. Se reporta por",
              "tanda, sin pool; la base es la tabla principal y las tres re-corridas son",
              "replicación. No es resultado de la tesis, no cruza con veredictos del juez ni",
              "con atribuciones. Este archivo se deriva de `reports/ucita2_indicadores.json`",
              "(generado por `scripts/ucita2_indicadores.py`), nunca al revés; los conteos se",
              "recomputan desde el JSON al renderizar."]
    else:
        p = datos["parametrizacion"]
        L += ["# Indicadores de exactitud de cita — corrida parametrizada",
              "",
              "Tres indicadores determinísticos por respuesta, sin juez ni API (USD 0), sobre",
              f"las tandas {', '.join(f'`{t}`' for t in tandas)} de `{p['argumentos']['trazas']}`.",
              "Se reporta por tanda, sin pool. No es resultado de la tesis, no cruza con",
              "veredictos del juez ni con atribuciones. Este archivo se deriva de",
              f"`{out_json_legible}` (generado por `scripts/ucita2_indicadores.py`, sha256",
              f"`{p['script_sha256']}`), nunca al revés; los conteos se recomputan desde el JSON.",
              "",
              f"Régimen de candados: {p['candados']}. Conciliación: {p['conciliacion']}."]
    L += ["",
          "## 1. Definiciones aplicadas",
          ""]
    for k, v in datos["definiciones"].items():
        L.append(f"- **{k}**: {v}")
    L += ["", "## 2. Insumos (sha256 verificados al inicio y al cierre de la corrida)", "",
          "| clave | ruta | sha256 | inicio = cierre |", "|---|---|---|---|"]
    for clave in sorted(datos["insumos"]):
        i = datos["insumos"][clave]
        if i.get("sha256_esperado") is None:
            igual = "sí (medido, sin esperado)" if i["sha256"] == i["sha256_cierre"] else "NO"
        else:
            igual = "sí" if i["sha256"] == i["sha256_cierre"] == i["sha256_esperado"] else "NO"
        extra = f" ({i['n_archivos']} archivos)" if "n_archivos" in i else ""
        L.append(f"| {clave} | `{i['ruta']}`{extra} | `{i['sha256']}` | {igual} |")
    L += ["", "Funciones `_cita_fiel` y `_norm_loc` importadas de `data/experiment/evaluacion/harness.py`",
          "(sin modificarlo; ruta y sha verificados en la importación).", "",
          "## 3. Índice E0 por TO (decisión 5)", "",
          "| TO | archivo | nodos | `numero` distintos | profundidad máxima |", "|---|---|---|---|---|"]
    for to in tos:
        i = datos["indice_e0"][to]
        L.append(f"| {to} | `{i['archivo']}` | {i['n_nodos']} | {i['n_numeros_distintos']} | {i['profundidad_max']} |")
    a = datos["anclas_en_indice"]
    L += ["", f"Anclas del gold que resuelven en el índice E0 de su TO: **{_n_de(a['resueltas'], a['total'])}**."]
    if a["no_resueltas"]:
        L += ["No resueltas: " + ", ".join(f"{x['id']} ({x['ancla']})" for x in a["no_resueltas"])]

    L += ["", "## 4. Resultados por tanda (decisión 8: tres tablas por tanda; la de contenido es la principal)"]
    for k_t, tanda in enumerate(tandas, start=1):
        ag = datos["agregados"][tanda]
        filas = [f for f in datos["filas"] if f["tanda"] == tanda]
        L += ["", f"### 4.{k_t} Tanda `{tanda}` — {len(filas)} trazas", ""]
        L += [f"Respuestas sin JSON final (`sin_json`, conteo aparte): {ag['n_sin_json']}. "
              f"Contenido {ag['contenido']['N']} + abstención {ag['abstencion']['N']} + sin_json "
              f"{ag['n_sin_json']} = {ag['contenido']['N'] + ag['abstencion']['N'] + ag['n_sin_json']} "
              f"(N todas = {ag['todas']['N']})."]
        for g, nombre in GRUPOS:
            L += ["", f"#### {tanda} · {nombre} (N = {ag[g]['N']})", ""]
            L += _tabla_indicadores(ag[g])
        # listas una por una
        nf = [(f["id"], c) for f in filas for c in f["citas_no_fundadas"]]
        nfb = [(f["id"], c) for f in filas for c in f["citas_no_fundadas_byte_exacta"]
               if c not in f["citas_no_fundadas"]]
        ne = [(f["id"], c) for f in filas for c in f["citas_no_existentes"]]
        fi = [(f["id"], c) for f in filas for c in f["citas_fuera_de_indice"]]
        np_ = [(f["id"], c) for f in filas for c in f["citas_no_parseables"]]
        sc = [f["id"] for f in filas if f["ind1_cita_fundada"] == SIN_CITAS]
        sj = [f["id"] for f in filas if f["grupo"] == "sin_json"]
        L += ["", f"#### {tanda} · listas una por una", ""]
        L.append(f"- Citas no fundadas (lectura normalizada, indicador 1): {len(nf)}" + ("" if nf else "."))
        for qid, c in nf:
            L.append(f"  - {qid}: {_fmt_cita(c)}")
        L.append(f"- Citas no fundadas solo en la lectura byte-exacta (fundadas bajo normalización): {len(nfb)}" + ("" if nfb else "."))
        for qid, c in nfb:
            L.append(f"  - {qid}: {_fmt_cita(c)}")
        L.append(f"- Citas no existentes en el índice E0 (indicador 2): {len(ne)}" + ("" if ne else "."))
        for qid, c in ne:
            L.append(f"  - {qid}: {_fmt_cita(c)} — TO `{c.get('to')}`, punto `{c.get('punto')}`, "
                     f"prefijo existente más largo `{c.get('prefijo_existente')}`"
                     + (f", motivo `{c['motivo_no_parseable']}`" if c.get("motivo_no_parseable") else ""))
        L.append(f"- Citas `fuera_de_indice` (más profundas que el índice de su TO): {len(fi)}" + ("" if fi else "."))
        for qid, c in fi:
            L.append(f"  - {qid}: {_fmt_cita(c)} — prefijo a la profundidad máxima `{c.get('prefijo_existente')}`")
        L.append(f"- Citas no parseables (decisión 3): {len(np_)}" + ("" if np_ else "."))
        for qid, c in np_:
            L.append(f"  - {qid}: {_fmt_cita(c)} — motivo `{c.get('motivo_no_parseable')}`")
        L.append(f"- Respuestas `sin_citas`: {len(sc)}" + (" — " + ", ".join(sc) if sc else "."))
        L.append(f"- Respuestas `sin_json`: {len(sj)}" + (" — " + ", ".join(sj) if sj else "."))

    conc = datos["conciliacion"]
    medidas = [("trazas", "trazas"), ("citas_totales", "citas totales"),
               ("citas_parseables", "citas parseables"),
               ("respuestas_con_cita_parseable", "respuestas con ≥ 1 cita parseable"),
               ("contenido", "contenido (respondible true)"), ("abstenciones", "abstenciones (respondible false)"),
               ("sin_json", "sin_json"), ("sin_citas", "sin_citas"),
               ("citas_no_fundadas_normalizada", "citas no fundadas (normalizada)"),
               ("citas_no_fundadas_byte_exacta", "citas no fundadas (byte-exacta)"),
               ("citas_no_existentes", "citas no existentes"), ("citas_fuera_de_indice", "citas fuera_de_indice"),
               ("citas_no_parseables", "citas no parseables"),
               ("control_ind1_discrepancias", "control indicador 1: trazas con discrepancia")]
    if conc.get("estado") != SIN_CONCILIACION:
        L += ["", "## 5. Conciliación con U-CITA (criterios b, c, d)", "",
              "Cifras previas: `reports/inventario_UCITA.md` §4 (trazas, citas parseables,",
              "respuestas con cita parseable, abstenciones de la base) y §5 (citas no vistas).",
              "Las re-corridas no traen cifra previa de abstenciones: se reporta el conteo.", "",
              "| medida | " + " | ".join(TANDAS) + " |",
              "|---|" + "---|" * len(TANDAS)]
        for k, nombre in medidas:
            celdas = []
            for tanda in TANDAS:
                v = conc["por_tanda"][tanda][k]
                esp = ESPERADO_UCITA.get(k, {}).get(tanda)
                celdas.append(f"{v}" + (f" (U-CITA: {esp})" if esp is not None and esp != v else (" ✓" if esp is not None else "")))
            L.append(f"| {nombre} | " + " | ".join(celdas) + " |")
        L += ["", "«✓» = coincide con la cifra de U-CITA; entre paréntesis, la cifra de U-CITA cuando difiere; sin marca, sin cifra previa.", ""]
        L.append("Trazas con citas no fundadas (normalizada), por tanda:")
        for tanda in TANDAS:
            nf = conc["por_tanda"][tanda]["trazas_con_citas_no_fundadas"]
            L.append(f"- {tanda}: " + (", ".join(f"{k} ({v})" for k, v in sorted(nf.items())) if nf else "ninguna"))
        L += ["", f"Diferencias con las cifras de U-CITA: {len(conc['diferencias'])}" + ("" if conc["diferencias"] else ".")]
        for d in conc["diferencias"]:
            L.append(f"- {d['tanda']} · {d['medida']}: U-CITA {d['esperado']}, computado {d['computado']}")
        L += ["", f"Control del indicador 1 (recómputo vs. `citations_unseen_normalized` / `citations_unseen_raw` persistidos): "
              f"**{conc['control_ind1_discrepancias_total']} discrepancias** en {sum(c['trazas'] for c in conc['por_tanda'].values())} trazas."]
    else:
        res = datos["resumen_por_tanda"]
        L += ["", "## 5. Conciliación con U-CITA: sin conciliación", "",
              f"{conc['motivo']}.", "",
              "### 5.1 Resumen descriptivo por tanda (sin cifra esperada)", "",
              "| medida | " + " | ".join(tandas) + " |",
              "|---|" + "---|" * len(tandas)]
        for k, nombre in medidas:
            L.append(f"| {nombre} | " + " | ".join(str(res["por_tanda"][tanda][k]) for tanda in tandas) + " |")
        L += ["", "Trazas con citas no fundadas (normalizada), por tanda:"]
        for tanda in tandas:
            nf = res["por_tanda"][tanda]["trazas_con_citas_no_fundadas"]
            L.append(f"- {tanda}: " + (", ".join(f"{k} ({v})" for k, v in sorted(nf.items())) if nf else "ninguna"))
        L += ["", f"Control del indicador 1 (recómputo vs. `citations_unseen_normalized` / `citations_unseen_raw` persistidos): "
              f"**{res['control_ind1_discrepancias_total']} discrepancias** en {sum(c['trazas'] for c in res['por_tanda'].values())} trazas."]
    if cfg is None or cfg["comando"] is None:
        comando = "PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ucita2_indicadores.py"
    else:
        comando = cfg["comando"]
    L += ["", "## 6. Salidas y reproducción", "",
          f"- `{out_json_legible}` — sha256 `{sha_json}` (este .md se renderiza desde ese archivo).",
          "- Comando (desde la raíz del repo):", "", "```",
          comando, "```", "",
          "- Selftest de respuesta conocida: `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ucita2_indicadores.py --selftest`.",
          "- Determinismo: el JSON no lleva timestamps; dos corridas consecutivas producen el mismo sha256.",
          ""]
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Selftest de respuesta conocida (trazas sintéticas en memoria)               #
# --------------------------------------------------------------------------- #
def _cita(doc, loc):
    return {"source_doc": doc, "location": loc}


def _traza_sintetica(qid, citas, respondible, parse_ok, seen, cita_fiel, adulterar=False):
    fj = {"respuesta": "sintética", "citas": citas, "respondible": respondible} if parse_ok else None
    seen_keys = {(p["source_doc"], p["location"]) for p in seen}
    raw, norm = [], []
    if parse_ok:
        for c in citas:
            if isinstance(c, dict):
                if (c.get("source_doc"), c.get("location")) not in seen_keys:
                    raw.append(c)
                if not cita_fiel(c, seen):
                    norm.append(c)
    if adulterar:
        raw = [_cita("TO_sintetico_actual.pdf", "Punto 9.9")]
    return {"qid": qid, "parse_ok": parse_ok, "final_json": fj, "seen_provenances": seen,
            "citations_unseen_raw": raw, "citations_unseen_normalized": norm}


def selftest(cita_fiel, norm_loc) -> int:
    DOC, DOC2, DOC3 = "TO_sintetico_actual.pdf", "TO_otro_actual.pdf", "TO_desconocido_actual.pdf"
    ctx = {"manifiesto": {DOC: "sin", DOC2: "otr"},
           "indices": {"sin": {"numeros": {"1", "1.1", "1.1.1", "1.1.1.1", "1.2", "2", "2.1"}, "profundidad_max": 4},
                       "otr": {"numeros": {"1", "1.1"}, "profundidad_max": 2}},
           "gold": {}, "cita_fiel": cita_fiel, "norm_loc": norm_loc}
    seen = [_cita(DOC, "Punto 1.1.1"), _cita(DOC, "Punto 1.1"), _cita(DOC, "Punto 1.1.1.1"),
            _cita(DOC, "Punto 1.2"), _cita(DOC, "Sección 1"), _cita(DOC, "Comunicación “A” 1234"),
            _cita(DOC2, "Punto 1.1"), _cita(DOC3, "Punto 1.1")]
    # (id, descripción, citas, respondible, parse_ok, esperado, adulterar_control)
    E = lambda i1, b, i2, i3, an, grupo="contenido", **kw: dict(ind1_cita_fundada=i1, ind1_byte_exacta=b,  # noqa: E731
                                                                ind2_cita_existente=i2, ind3_cita_al_ancla=i3,
                                                                info_cita_ancestro_del_ancla=an, grupo=grupo, **kw)
    casos = [
        ("ST-01", "cita exacta al ancla y vista", [_cita(DOC, "Punto 1.1.1")], True, True,
         E(SI, SI, SI, SI, NO, n_parseables=1), False),
        ("ST-02", "cita a descendiente del ancla, vista", [_cita(DOC, "Punto 1.1.1.1")], True, True,
         E(SI, SI, SI, SI, NO), False),
        ("ST-03", "cita a ancestro del ancla, vista (ind. 3 no, informativa sí)", [_cita(DOC, "Punto 1.1")], True, True,
         E(SI, SI, SI, NO, SI), False),
        ("ST-04", "cita no vista, existente (ind. 1 no en ambas lecturas)", [_cita(DOC, "Punto 2.1")], True, True,
         E(NO, NO, SI, NO, NO, n_no_fundadas=1, n_no_fundadas_byte=1), False),
        ("ST-05", "cita vista solo bajo normalización (punto final): normalizada sí, byte-exacta no",
         [_cita(DOC, "Punto 1.1.1.")], True, True, E(SI, NO, SI, SI, NO, n_no_fundadas=0, n_no_fundadas_byte=1), False),
        ("ST-06", "cita no parseable, vista solo bajo normalización de comillas y espacios",
         [_cita(DOC, 'Comunicación  "A"  1234')], True, True,
         E(SI, NO, NO, NO, NO, n_parseables=0, n_no_parseables=1), False),
        ("ST-07", "cita a punto inexistente (prefijo existente «1»)", [_cita(DOC, "Punto 1.3")], True, True,
         E(NO, NO, NO, NO, NO, n_no_existentes=1, prefijo="1"), False),
        ("ST-08", "cita más profunda que el índice (fuera_de_indice; descendiente del ancla)",
         [_cita(DOC, "Punto 1.1.1.1.1")], True, True, E(NO, NO, FUERA, SI, NO, n_fuera=1), False),
        ("ST-09", "sin citas", [], True, True, E(SIN_CITAS, SIN_CITAS, SIN_CITAS, SIN_CITAS, SIN_CITAS, n_parseables=0), False),
        ("ST-10", "abstención con citas (computa igual; tabla de abstención)", [_cita(DOC, "Punto 1.1.1")], False, True,
         E(SI, SI, SI, SI, NO, grupo="abstencion"), False),
        ("ST-11", "sin JSON final (parse_ok falso)", None, None, False,
         E(SIN_JSON, SIN_JSON, SIN_JSON, SIN_JSON, SIN_JSON, grupo="sin_json"), False),
        ("ST-12", "cita «Sección N» normalizada a la sección N (ancestro del ancla)", [_cita(DOC, "Sección 1")], True, True,
         E(SI, SI, SI, NO, SI), False),
        ("ST-13", "cita a otro TO, vista y existente (ind. 3 no por TO)", [_cita(DOC2, "Punto 1.1")], True, True,
         E(SI, SI, SI, NO, NO), False),
        ("ST-14", "mezcla: cita al ancla + cita inexistente no vista (TODA vs ALGUNA)",
         [_cita(DOC, "Punto 1.1.1"), _cita(DOC, "Punto 1.3")], True, True, E(NO, NO, NO, SI, NO, n_parseables=2), False),
        ("ST-15", "precedencia ind. 2: fuera_de_indice + inexistente → no",
         [_cita(DOC, "Punto 1.1.1.1.1"), _cita(DOC, "Punto 1.3")], True, True, E(NO, NO, NO, SI, NO), False),
        ("ST-16", "source_doc con forma válida pero sin TO en el manifiesto (ind. 2 no)", [_cita(DOC3, "Punto 1.1")], True, True,
         E(SI, SI, NO, NO, NO, n_no_existentes=1), False),
        ("ST-17", "control ind. 1: campos persistidos adulterados → discrepancia detectada", [_cita(DOC, "Punto 1.1.1")], True, True,
         E(SI, SI, SI, SI, NO, control_ok=False), True),
    ]
    for qid, *_ in casos:
        ctx["gold"][qid] = {"ancla": "sin:1.1.1", "to": "sin", "punto": "1.1.1"}

    print("SELFTEST U-CITA-2 — trazas sintéticas en memoria; ancla de todas las claves: sin:1.1.1")
    print(f"_norm_loc('Punto 1.1.1.') = {norm_loc('Punto 1.1.1.')!r}; "
          f"_norm_loc('Comunicación  \"A\"  1234') = {norm_loc('Comunicación  \"A\"  1234')!r}")
    fallas, filas = 0, []
    for qid, desc, citas, resp, pok, esperado, adulterar in casos:
        tr = _traza_sintetica(qid, citas, resp, pok, seen, cita_fiel, adulterar)
        f = evaluar_traza("selftest", tr, ctx)
        filas.append(f)
        obtenido = {k: f[k] for k, _ in INDICADORES}
        obtenido["grupo"] = f["grupo"]
        errores = [f"{k}: esperado {v!r}, obtenido {obtenido[k]!r}" for k, v in esperado.items()
                   if k in obtenido and obtenido[k] != v]
        extras = {"n_parseables": f["n_parseables"], "n_no_fundadas": len(f["citas_no_fundadas"]),
                  "n_no_fundadas_byte": len(f["citas_no_fundadas_byte_exacta"]),
                  "n_no_existentes": len(f["citas_no_existentes"]), "n_fuera": len(f["citas_fuera_de_indice"]),
                  "n_no_parseables": len(f["citas_no_parseables"]), "control_ok": f["control_ind1"]["ok"],
                  "prefijo": f["citas_no_existentes"][0]["prefijo_existente"] if f["citas_no_existentes"] else None}
        for k, v in esperado.items():
            if k in extras and extras[k] != v:
                errores.append(f"{k}: esperado {v!r}, obtenido {extras[k]!r}")
        if "control_ok" not in esperado and not f["control_ind1"]["ok"]:
            errores.append("control_ind1 no ok")
        estado = "PASS" if not errores else "FAIL"
        fallas += bool(errores)
        vals = " / ".join(str(obtenido[k]) for k, _ in INDICADORES)
        print(f"  [{estado}] {qid} {desc}\n         ind1 / ind1_byte / ind2 / ind3 / info_ancestro = {vals}; "
              f"grupo={f['grupo']}; control_ok={f['control_ind1']['ok']}"
              + ("".join(f"\n         ERROR {e}" for e in errores)))
    ag = agregar(filas)["selftest"]
    checks = [("N todas", ag["todas"]["N"], len(casos)), ("N contenido", ag["contenido"]["N"], 15),
              ("N abstención", ag["abstencion"]["N"], 1), ("n_sin_json", ag["n_sin_json"], 1),
              ("abstención · ind3 sí", ag["abstencion"]["ind3_cita_al_ancla"][SI], 1),
              ("todas · ind2 fuera_de_indice", ag["todas"]["ind2_cita_existente"][FUERA], 1),
              ("todas · ind1 sin_citas", ag["todas"]["ind1_cita_fundada"][SIN_CITAS], 1),
              ("todas · ind1 sin_json", ag["todas"]["ind1_cita_fundada"][SIN_JSON], 1)]
    for nombre, got, exp in checks:
        ok = got == exp
        fallas += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] agregación · {nombre}: {got} (esperado {exp})")
    print(f"SELFTEST: {len(casos)} casos + {len(checks)} chequeos de agregación; fallas = {fallas}")
    return 1 if fallas else 0


# --------------------------------------------------------------------------- #
# Corrida principal                                                            #
# --------------------------------------------------------------------------- #
DEFINICIONES = {
    "cita parseable": "source_doc ~ ^TO_[a-z_]+_actual\\.pdf$ y location ~ ^Punto (\\d+(?:\\.\\d+)*)\\.?$ o ^Sección (\\d+)$; "
                      "punto normalizado = grupo capturado; TO = el que el manifiesto asocia al source_doc. "
                      "Toda cita no parseable se lista y cuenta como «no» en los indicadores 2 y 3.",
    "indicador 1 · cita fundada": "«sí» si TODA cita de la respuesta es fiel a alguna entrada de trace.seen_provenances "
                                  "de la misma traza según _cita_fiel/_norm_loc del harness (normalizada, principal); "
                                  "lectura byte-exacta al lado: tupla (source_doc, location) idéntica a alguna entrada.",
    "indicador 2 · cita existente": "«sí» si TODA cita parseable resuelve a un `numero` del índice E0 de su TO; "
                                    "precedencia: alguna inexistente o no parseable → «no»; si no, alguna fuera_de_indice → "
                                    "«fuera_de_indice» (más niveles que la profundidad máxima del índice y prefijo a esa "
                                    "profundidad existente; se cuenta aparte); si no → «sí».",
    "indicador 3 · cita al punto de referencia": "«sí» si ALGUNA cita tiene el TO del ancla y su punto es el ancla o empieza "
                                                  "con el ancla seguido de «.»; los ancestros NO cuentan.",
    "columna informativa": "«sí» si alguna cita es ancestro del ancla (mismo TO y el ancla empieza con el punto citado seguido de «.»).",
    "sin_citas / sin_json": "lista de citas vacía o ausente → «sin_citas» en los tres indicadores (nunca «sí» por vacuidad); "
                            "parse_ok falso → «sin_json» en los tres y conteo aparte.",
    "grupos": "abstención = respondible == false; contenido = el resto con JSON; tres tablas por tanda (todas / contenido / abstención).",
    "agregación": "fracción cruda «n de N» por indicador; sin porcentajes, sin pool entre tandas, sin intervalos; "
                  "sin cruce con veredictos del juez ni con atribuciones.",
}


def correr(cfg: dict | None = None) -> int:
    modo_default = cfg is None or cfg["modo_default"]
    tandas = TANDAS if cfg is None else cfg["tandas"]
    trazas_dir = TRAZAS_DIR if cfg is None else cfg["trazas"]
    out_json = OUT_JSON if cfg is None else cfg["out_json"]
    out_md = OUT_MD if cfg is None else cfg["out_md"]

    insumos_inicio = verificar_insumos("inicio", cfg)
    cita_fiel, norm_loc = importar_harness()
    ctx = cargar_contexto(cita_fiel, norm_loc, cfg)
    anclas = verificar_anclas(ctx)
    print(f"[anclas] {anclas['resueltas']} de {anclas['total']} anclas del gold resuelven en el índice E0 de su TO")
    if anclas["no_resueltas"]:
        print("[anclas] NO RESUELTAS: " + ", ".join(f"{x['id']} {x['ancla']}" for x in anclas["no_resueltas"]))

    filas = []
    for tanda in tandas:
        for p in archivos_tanda(tanda, trazas_dir):
            doc = json.loads(p.read_text(encoding="utf-8"))
            tr = doc["trace"]
            meta = doc.get("meta") or {}
            if tr.get("qid") != p.stem or meta.get("caso_id") != p.stem or meta.get("label") != tanda:
                raise SystemExit(f"ABORTO: {tanda}/{p.name}: qid={tr.get('qid')!r}, caso_id={meta.get('caso_id')!r}, "
                                 f"label={meta.get('label')!r} no coinciden con archivo y tanda")
            filas.append(evaluar_traza(tanda, tr, ctx))
    filas.sort(key=lambda f: (f["tanda"], f["id"]))
    agregados = agregar(filas)
    concilia = tuple(tandas) == TANDAS          # la conciliación rige solo con las tandas default
    conc = conciliar(filas) if concilia else sin_conciliacion(tuple(tandas))
    insumos_cierre = verificar_insumos("cierre", cfg)

    insumos = {}
    for k, v in insumos_inicio.items():
        insumos[k] = dict(v)
        insumos[k]["sha256_cierre"] = insumos_cierre[k]["sha256"]
    if not modo_default:
        cambiados = [k for k in insumos if insumos[k]["sha256"] != insumos[k]["sha256_cierre"]]
        if cambiados:
            raise SystemExit(f"ABORTO: insumos modificados durante la corrida (inicio ≠ cierre): {cambiados}")
    if modo_default:
        descripcion = ("Indicadores determinísticos de exactitud de cita sobre las 112 trazas de KG-Reextraído-r1 "
                       "(ev2_r1: base 40, enc_r1 24, enc_r2 24, enc_r3 24), por tanda, sin juez ni API.")
    else:
        n_por_tanda = ", ".join(f"{t} {sum(1 for f in filas if f['tanda'] == t)}" for t in tandas)
        descripcion = (f"Indicadores determinísticos de exactitud de cita sobre {len(filas)} trazas "
                       f"({n_por_tanda}), por tanda, sin juez ni API. Corrida parametrizada: ver `parametrizacion`.")
    salida = {
        "unidad": "U-CITA-2",
        "descripcion": descripcion,
        "script": "scripts/ucita2_indicadores.py",
        "definiciones": DEFINICIONES,
        "insumos": insumos,
        "indice_e0": {to: {k: v for k, v in ctx["indices"][to].items() if k != "numeros"} for to in ctx["tos"]},
        "anclas_en_indice": anclas,
        "conciliacion": conc,
        "agregados": agregados,
        "filas": filas,
    }
    if not modo_default:
        salida["parametrizacion"] = {
            "modo": "parametrizado",
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "argumentos": {"gold": _ruta_legible(cfg["gold"]), "manifiesto": _ruta_legible(cfg["manifiesto"]),
                           "e0": _ruta_legible(cfg["e0"]), "trazas": _ruta_legible(cfg["trazas"]),
                           "tandas": list(tandas), "tos": list(ctx["tos"]),
                           "out_json": _ruta_legible(out_json), "out_md": _ruta_legible(out_md)},
            "candados": "medidos, sin esperado (argumentos distintos de los defaults); harness congelado verificado",
            "conciliacion": ("rige (tandas default)" if concilia
                             else f"{SIN_CONCILIACION} (tandas distintas de las default)"),
        }
    if not concilia:
        salida["resumen_por_tanda"] = resumen_por_tanda(filas, tuple(tandas))
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(salida, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    sha_json = sha256_file(out_json)
    datos = json.loads(out_json.read_text(encoding="utf-8"))   # el .md se deriva del JSON en disco
    out_md.write_text(render_md(datos, sha_json, cfg), encoding="utf-8")
    verificar_insumos("post-escritura", cfg)

    print(f"[salida] {_ruta_legible(out_json)} sha256 {sha_json}")
    print(f"[salida] {_ruta_legible(out_md)} sha256 {sha256_file(out_md)}")
    resumen = conc if concilia else salida["resumen_por_tanda"]
    for tanda in tandas:
        c = resumen["por_tanda"][tanda]
        ag = agregados[tanda]["contenido"]
        print(f"[{tanda}] trazas {c['trazas']} · citas {c['citas_totales']} (parseables {c['citas_parseables']}) · "
              f"resp. con cita parseable {c['respuestas_con_cita_parseable']} · contenido {c['contenido']} · "
              f"abstención {c['abstenciones']} · sin_json {c['sin_json']} · no fundadas {c['citas_no_fundadas_normalizada']} "
              f"en {sorted(c['trazas_con_citas_no_fundadas'])} · control ind.1 discrepancias {c['control_ind1_discrepancias']}")
        print(f"    contenido (N={ag['N']}): ind1 {ag['ind1_cita_fundada'][SI]} · ind1_byte {ag['ind1_byte_exacta'][SI]} · "
              f"ind2 {ag['ind2_cita_existente'][SI]} (fuera_de_indice {ag['ind2_cita_existente'][FUERA]}) · "
              f"ind3 {ag['ind3_cita_al_ancla'][SI]} · ancestro {ag['info_cita_ancestro_del_ancla'][SI]} · "
              f"sin_citas {ag['ind1_cita_fundada'][SIN_CITAS]}")
    if concilia:
        print(f"[conciliación] diferencias con U-CITA: {len(conc['diferencias'])}"
              + ("".join(f"\n    {d}" for d in conc["diferencias"])))
    else:
        print(f"[conciliación] {SIN_CONCILIACION}: {conc['motivo']}")
    print(f"[control ind.1] discrepancias totales: {resumen['control_ind1_discrepancias_total']}")
    return 0


def _config_desde_args(args, argv: list) -> dict | None:
    """Configuración de la corrida. Devuelve None cuando no se pasó ningún
    argumento (comportamiento idéntico al original). `modo_default` es True
    cuando gold, manifiesto, e0, trazas y tandas son los defaults (las salidas
    no cuentan): en ese modo rigen los candados y la conciliación."""
    if not argv:
        return None
    gold, manifiesto, e0, trazas = (Path(args.gold), Path(args.manifiesto), Path(args.e0), Path(args.trazas))
    tandas = tuple(args.tandas) if args.tandas else TANDAS
    modo_default = (gold.resolve() == GOLD_PATH.resolve() and manifiesto.resolve() == MANIFIESTO_PATH.resolve()
                    and e0.resolve() == E0_DIR.resolve() and trazas.resolve() == TRAZAS_DIR.resolve()
                    and tandas == TANDAS)
    for nombre, p in (("--gold", gold), ("--manifiesto", manifiesto)):
        if not p.is_file():
            raise SystemExit(f"ABORTO: {nombre} no es un archivo: {p}")
    for nombre, p in (("--e0", e0), ("--trazas", trazas)):
        if not p.is_dir():
            raise SystemExit(f"ABORTO: {nombre} no es un directorio: {p}")
    return {"gold": gold, "manifiesto": manifiesto, "e0": e0, "trazas": trazas, "tandas": tandas,
            "tos": _tos_del_manifiesto(manifiesto),
            "out_json": Path(args.out_json), "out_md": Path(args.out_md), "modo_default": modo_default,
            "comando": "PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/ucita2_indicadores.py " + " ".join(argv)}


def main() -> int:
    ap = argparse.ArgumentParser(description="U-CITA-2: indicadores de exactitud de cita (determinístico, USD 0).")
    ap.add_argument("--selftest", action="store_true", help="corre solo el selftest de respuesta conocida")
    ap.add_argument("--gold", default=str(GOLD_PATH), help="gold EV2 (default: el sellado de U-CITA-2)")
    ap.add_argument("--manifiesto", default=str(MANIFIESTO_PATH), help="manifiesto del corpus (TOs y archivos)")
    ap.add_argument("--e0", default=str(E0_DIR), help="directorio de salida de E0 con estructura_<to>.json")
    ap.add_argument("--trazas", default=str(TRAZAS_DIR), help="directorio con un subdirectorio por tanda")
    ap.add_argument("--tandas", nargs="+", default=None, metavar="TANDA",
                    help=f"tandas a evaluar (default: {' '.join(TANDAS)})")
    ap.add_argument("--out-json", default=str(OUT_JSON), help="ruta del JSON de salida")
    ap.add_argument("--out-md", default=str(OUT_MD), help="ruta del .md de salida (derivado del JSON)")
    args = ap.parse_args()
    if args.selftest:
        verificar_insumos("inicio")
        cita_fiel, norm_loc = importar_harness()
        rc = selftest(cita_fiel, norm_loc)
        verificar_insumos("cierre")
        return rc
    return correr(_config_desde_args(args, sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
