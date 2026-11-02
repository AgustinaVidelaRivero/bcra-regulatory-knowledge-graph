#!/usr/bin/env python3
"""juez_b63.py (v2, etapa b1) — El juez de B6.3 (pre-registro FIRMADO, `adf20f3b`, §7.1), encadenado a las corridas por el runner
(decisión de la autora del 25/10/2026; registro, §116). Es b63/juez_b63.py (etapa a) con las tres repeticiones de cada respuesta a la
vez (decisión de la autora del 27/10/2026, 11:31:49: «el juez de B6.3 con sus tres repeticiones a la vez, cada una con su base. Se
declara igual.»): `TresJueces`, un hilo por repetición con su cliente, su base y su namespace (el cliente nace en su hilo); una
repetición se lanza cuando la anterior pasó su guarda del gasto, y el gasto de las tres va en la misma guarda; el veredicto modal no
cambia. `juzgar`, el de la etapa a, de a una, queda para comparar. Lo demás, tal cual: el de EV2 tal cual, `data/experiment/ev2_juez/juez.py` con su prompt v1 (`fd446f8e…`) y el
veredicto por pregunta de `mapping.py`, importados sin editarlos, con su sha256 de la entrada sellada. N = 3 por respuesta, cada
repetición con su caché propia de B6.3 (b63/juez/cache/b63_juez_r{1,2,3}.db) y su etiqueta (`construir_cliente_real`).

  · Lo que recibe, tal cual (decisión 13): «el juez recibe solo la pregunta, sus criterios y la respuesta, sin el brazo». Cada
    respuesta viaja con un id opaco (`B63J-` + sha256(sal|pregunta|brazo|repetición|sha256 de la respuesta)[:10], con la sal
    propia de B6.3, como en A2.2); la tabla que lo desanonimiza va a desanonimizacion_SOLO_MESA/.
  · D-10, tal cual (§7.1): «Antes del juez, un script cuenta por brazo las respuestas con marcas de su brazo, la cifra se declara y
    no se edita ninguna respuesta.» Las marcas: los nombres de las herramientas del brazo (con y sin su prefijo mcp__) y la forma de
    sus citas (un nodo en el grafo; un pasaje o un fragmento en los de fragmentos), más las que selle la entrada. Cada respuesta se
    cuenta antes de juzgarla; la cifra va por brazo, sin ningún texto, a d10_b63.json, y lo de cada respuesta, a la tabla de la mesa.
  · Una salida mal formada del juez se registra en errores_r{rep}.jsonl y no se reintenta (como en A2.2). Si el juez se corta, la
    respuesta queda guardada y sigue desde su caché sin volver a pagar (`ev2_juez/juez.py:16-18`): las repeticiones ya escritas
    no se vuelven a pedir, y las pedidas y no escritas salen de la caché.
  · El control del SDK (`scripts/control_sdk_anthropic_juez_y_banco.py`, el 165) es el primer control del paso pago del juez.
Nada de lo que imprime o escribe fuera de la tabla de la mesa trae un texto de una pregunta, un criterio, una cita o una respuesta, ni
el brazo junto al id opaco.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b63/v2
BANCO_DIR = AQUI.parent.parent
EV2_JUEZ = BANCO_DIR.parent / "ev2_juez"
for _p in (str(AQUI), str(EV2_JUEZ)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import comun_b63 as K                        # noqa: E402
import juez as J                             # noqa: E402  (EV2, congelado: solo import)
import mapping as M                          # noqa: E402  (EV2, congelado: solo import)

PROMPT_SHA256 = "fd446f8e61f46033d7de9b862121c698b2c52dcc2696b7f10993f44e509f5455"
MODELO = "claude-sonnet-4-6"
SAL_ID_OPACO = "B63:id_opaco_juez:v1"
PREFIJO_ID = "B63J-"
DB_PREFIX = "b63_juez"
REPS = (1, 2, 3)
CONTROL_SDK = K.REPO_DIR / "scripts" / "control_sdk_anthropic_juez_y_banco.py"
# Precios del juez (claude-sonnet-4-6), USD por millón de tokens: 3,00 de entrada y 15,00 de salida
# (`data/experiment/run_1_cookbook/code/common.py:207`, como en a2_2/comun_a2_2.py:57-59); y el costo de una respuesta con sus tres
# repeticiones mientras no haya ninguna juzgada, el de A2.2 (a2_2/comun_a2_2.py:56).
PRECIO_IN, PRECIO_OUT, COSTO_RESPUESTA_INICIAL = 3.00, 15.00, 0.0378
COSTO_REPETICION_INICIAL = COSTO_RESPUESTA_INICIAL / 3          # 0,0126: el costo por llamada de U-NAV (a2_2/comun_a2_2.py:58)
CITAS_POR_ROL = {"grafo": (r"\bnodos?\b",), "fragmentos_principal": (r"\bpasajes?\b", r"\bfragmentos?\b"),
                 "fragmentos_denso": (r"\bpasajes?\b", r"\bfragmentos?\b")}
TABLA = "tabla_id_opaco_b63_SOLO_MESA.json"


class FrenoJuez(Exception):
    """El corte del juez (código 2): la guarda del gasto, la misma que la de las sesiones."""


# --------------------------------------------------------------------------------------------------------------------- #
# El instrumento                                                                                                        #
# --------------------------------------------------------------------------------------------------------------------- #
def controlar_instrumento(e: dict | None = None) -> dict:
    if os.environ.get("JUEZ_PROMPT_VERSION") is not None:
        K.frena("JUEZ_PROMPT_VERSION está fijada: el juez de B6.3 corre sin esa variable (§7.1)")
    if J.PROMPT_VERSION != "v1" or J.PROMPT_SHA256 != PROMPT_SHA256 or J.MODELO != MODELO or J.TEMPERATURE != 0.0:
        K.frena("el juez no es el de EV2 tal cual (prompt v1, claude-sonnet-4-6, temperatura 0)")
    sellos = {}
    if e is not None:
        sellados = {K.ruta_de_rel(d["ruta"]).resolve(): d["sha256"] for d in e["juez"]["archivos"]}
        for p in (Path(J.__file__), Path(M.__file__), J.PROMPT_PATH):
            p = p.resolve()
            if p not in sellados:
                K.frena(f"la entrada sellada no trae el sha256 de {K.rel_repo(p)}")
            if K.sha256_file(p) != sellados[p]:
                K.frena(f"{K.rel_repo(p)} no da el sha256 de la entrada sellada")
            sellos[K.rel_repo(p)] = sellados[p]
    return {"prompt_version": J.PROMPT_VERSION, "prompt_sha256": J.PROMPT_SHA256, "modelo": J.MODELO,
            "temperatura": J.TEMPERATURE, "code_ver": J.CODE_VER, "sellos": sellos}


def control_sdk(python: str | None = None) -> dict:
    """El control de la §93 (el 165), con el intérprete con que corre el juez, sin red y sin leer ningún .env."""
    r = subprocess.run([python or sys.executable, "-I", "-B", str(CONTROL_SDK)], capture_output=True, text=True)
    if r.returncode != 0:
        K.frena("el control del SDK y de la versión de la API frenó: "
                + " | ".join(l for l in r.stdout.splitlines() if l.startswith("FRENO")))
    return {"control_sdk": "OK", "lineas": [l for l in r.stdout.splitlines() if l.startswith(("OK", "control"))]}


# --------------------------------------------------------------------------------------------------------------------- #
# El caso ciego y su control                                                                                            #
# --------------------------------------------------------------------------------------------------------------------- #
def sha256_texto(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def id_opaco(qid: str, brazo: str, r: int, sha_respuesta: str) -> str:
    return PREFIJO_ID + sha256_texto(f"{SAL_ID_OPACO}|{qid}|{brazo}|{r}|{sha_respuesta}")[:10]


def caso_ciego(qid: str, brazo: str, r: int, respuesta: str, preguntas: dict) -> dict:
    """Lo único que viaja al juez: la pregunta, la respuesta y los criterios con su cita (cada criterio, solo esas dos claves)."""
    p = preguntas[qid]
    return {"id_opaco": id_opaco(qid, brazo, r, sha256_texto(respuesta)), "pregunta": p["pregunta"], "respuesta": respuesta,
            "criterios": [{"criterio": c["criterio"], "cita_textual": c["cita_textual"]} for c in p["criterios"]]}


def verificar_pedido(c: dict, brazos, prefijos_de_sesion=("B63-",)) -> list[str]:
    """El pedido es el prompt del juez más el mensaje armado con la pregunta, la respuesta y los criterios, y nada más. Sin el texto
    de la respuesta (que no se edita), el mensaje no trae ningún brazo, id de sesión ni id opaco. Devuelve las fugas (vacío = OK)."""
    fugas = []
    if set(c) != {"id_opaco", "pregunta", "respuesta", "criterios"}:
        fugas.append("el caso trae más que la pregunta, la respuesta y los criterios")
    if any(set(x) != {"criterio", "cita_textual"} for x in c["criterios"]):
        fugas.append("un criterio trae otra clave que su texto y su cita")
    kw = J.construir_kwargs(c["pregunta"], c["respuesta"], c["criterios"])
    if set(kw) != {"model", "max_tokens", "temperature", "system", "messages"} or kw["system"] != J.PROMPT_JUEZ:
        fugas.append("la estructura del pedido")
    if kw["messages"] != [{"role": "user", "content": J.construir_mensaje_usuario(c["pregunta"], c["respuesta"], c["criterios"])}]:
        fugas.append("el mensaje no es el de construir_mensaje_usuario")
    sin_resp = J.construir_mensaje_usuario(c["pregunta"], "<respuesta>", c["criterios"])
    for marca in (PREFIJO_ID, c["id_opaco"], "id_opaco", *prefijos_de_sesion, *sorted(brazos)):
        if marca.lower() in sin_resp.lower():
            fugas.append(f"una marca de brazo, de sesión o de id fuera de la respuesta ({'brazo' if marca in brazos else 'id'})")
    return fugas


# --------------------------------------------------------------------------------------------------------------------- #
# D-10                                                                                                                  #
# --------------------------------------------------------------------------------------------------------------------- #
def marcas_d10(e: dict, brazo: str) -> list[tuple[str, str]]:
    """(nombre, regex) de las marcas del brazo: sus herramientas (de tools_esperadas de su configuración), con y sin el prefijo, y la
    forma de sus citas; más las de `marcas_d10` del brazo en la entrada sellada."""
    out = []
    for t in e["_cfg"]["brazos"][brazo]["tools_esperadas"]:
        corta = t.rsplit("__", 1)[-1]
        out += [(t, re.escape(t)), (corta, r"(?<![A-Za-z0-9_])" + re.escape(corta) + r"(?![A-Za-z0-9_])")]
    rol = e["brazos"][brazo]["rol"]
    out += [(f"cita:{x}", x) for x in CITAS_POR_ROL[rol]]
    out += [(f"entrada:{x}", x) for x in e["brazos"][brazo].get("marcas_d10") or []]
    vistos, uniq = set(), []
    for n, x in out:
        if n not in vistos:
            vistos.add(n)
            uniq.append((n, x))
    return uniq


def contar_d10(respuesta: str, marcas: list[tuple[str, str]]) -> dict:
    """Qué marcas del brazo trae la respuesta. No la edita: devuelve el sha256 de la respuesta antes y después de contar."""
    antes = sha256_texto(respuesta)
    hallados = {n: bool(re.search(x, respuesta, re.IGNORECASE)) for n, x in marcas}
    return {"marcas": hallados, "con_alguna": any(hallados.values()), "sha256_antes": antes, "sha256_despues": sha256_texto(respuesta)}


def resumen_d10(tabla: dict, e: dict) -> dict:
    """La cifra de D-10 por brazo, desde la tabla de la mesa, sin ningún texto ni id."""
    por = {}
    for b in sorted(e["brazos"]):
        filas = [f for f in tabla.get("filas", {}).values() if f["brazo"] == b and f.get("d10")]
        nombres = [n for n, _ in marcas_d10(e, b)]
        por[b] = {"n_respuestas": len(filas), "con_alguna_marca": sum(1 for f in filas if f["d10"]["con_alguna"]),
                  "por_marca": {n: sum(1 for f in filas if f["d10"]["marcas"].get(n)) for n in nombres},
                  "respuestas_editadas": sum(1 for f in filas if f["d10"]["sha256_antes"] != f["d10"]["sha256_despues"])}
    return {"regla": "«Antes del juez, un script cuenta por brazo las respuestas con marcas de su brazo, la cifra se declara y no se "
                     "edita ninguna respuesta.» (D-10, §7.1)",
            "marcas": {b: [n for n, _ in marcas_d10(e, b)] for b in sorted(e["brazos"])}, "por_brazo": por}


# --------------------------------------------------------------------------------------------------------------------- #
# Gasto, caché y corte                                                                                                  #
# --------------------------------------------------------------------------------------------------------------------- #
def db_path(rep: int, cache_dir: Path) -> Path:
    return J.db_path_rep(rep, cache_dir, DB_PREFIX)


def gasto(cache_dir: Path) -> dict:
    """El acumulado del juez de B6.3: una fila por llamada pagada (miss) en sus tres cachés, con los precios de arriba."""
    tin = tout = filas = 0
    for rep in REPS:
        p = db_path(rep, cache_dir)
        if not p.exists():
            continue
        conn = sqlite3.connect(str(p))
        try:
            n, i, o = conn.execute("SELECT COUNT(*), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0) "
                                   "FROM cache").fetchone()
        except sqlite3.OperationalError:
            n, i, o = 0, 0, 0
        conn.close()
        filas += n; tin += i; tout += o
    return {"filas": filas, "input_tokens": tin, "output_tokens": tout,
            "usd": round(tin / 1e6 * PRECIO_IN + tout / 1e6 * PRECIO_OUT, 6)}


def leer(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def costo_mayor_juzgada(juez_dir: Path) -> float:
    """El costo mayor de una respuesta ya juzgada con sus tres repeticiones; COSTO_RESPUESTA_INICIAL si no hay ninguna."""
    por_id: dict[str, dict] = {}
    for rep in REPS:
        for reg in leer(juez_dir / f"veredictos_r{rep}.jsonl"):
            m = reg["meta"]
            por_id.setdefault(reg["id_opaco"], {})[rep] = m["input_tokens"] / 1e6 * PRECIO_IN + m["output_tokens"] / 1e6 * PRECIO_OUT
    completas = [sum(v.values()) for v in por_id.values() if len(v) == len(REPS)]
    return max(completas) if completas else COSTO_RESPUESTA_INICIAL


def factory_real(cache_dir: Path):
    def f(rep: int, label: str):
        return J.construir_cliente_real(rep, run_label=label, cache_dir=cache_dir, db_prefix=DB_PREFIX)
    return f


def hechas(juez_dir: Path) -> dict[int, set]:
    return {rep: {r["id_opaco"] for r in leer(juez_dir / f"veredictos_r{rep}.jsonl")}
            | {r["id_opaco"] for r in leer(juez_dir / f"errores_r{rep}.jsonl")} for rep in REPS}


def juzgar(c: dict, clientes: dict, juez_dir: Path, cache_dir: Path, gastado_agente: float, freno: float, tope: float) -> dict:
    """Las repeticiones que le faltan a una respuesta, seguidas. Antes, la guarda: si lo gastado (el agente más el juez) más el costo
    mayor de una respuesta juzgada pasa el freno o el tope, levanta FrenoJuez sin llamar."""
    juez_dir.mkdir(parents=True, exist_ok=True)
    h = hechas(juez_dir)
    pend = [rep for rep in REPS if c["id_opaco"] not in h[rep]]
    if not pend:
        return {"llamadas": 0, "errores": 0, "ya_estaba": True}
    g = gasto(cache_dir)["usd"]
    mayor = costo_mayor_juzgada(juez_dir)
    total = gastado_agente + g
    if total + mayor > freno or total + mayor > tope:
        raise FrenoJuez(f"lo gastado ({gastado_agente:.4f} del agente + {g:.4f} del juez) + {mayor:.4f} pasa el freno {freno} "
                        f"o el tope {tope}")
    llamadas = errores = 0
    for rep in pend:
        try:
            r = J.juzgar(clientes[rep], c["pregunta"], c["respuesta"], c["criterios"])
        except ValueError as ex:
            with (juez_dir / f"errores_r{rep}.jsonl").open("a", encoding="utf-8") as fe:
                fe.write(json.dumps({"id_opaco": c["id_opaco"], "rep": rep, "error": str(ex)[:200],
                                     "ts": datetime.now().isoformat()}, ensure_ascii=False) + "\n")
            errores += 1
            continue
        with (juez_dir / f"veredictos_r{rep}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id_opaco": c["id_opaco"], "rep": rep,
                                 "clasificacion_respuesta": r["veredicto"]["clasificacion_respuesta"],
                                 "criterios": r["veredicto"]["criterios"], "meta": r["meta"]}, ensure_ascii=False) + "\n")
        llamadas += 1
    return {"llamadas": llamadas, "errores": errores, "ya_estaba": False}


def agregar(juez_dir: Path, casos: dict[str, int]) -> dict:
    """Agregados ciegos por id opaco ({id_opaco: n_criterios}): el veredicto modal de cada criterio (mapping.veredicto_modal) y el
    de la pregunta (mapping.veredicto_pregunta), con las tres repeticiones; sin brazo."""
    por_rep = {rep: {r["id_opaco"]: r for r in leer(juez_dir / f"veredictos_r{rep}.jsonl")} for rep in REPS}
    agregados, incompletas = [], []
    for i, n in sorted(casos.items()):
        regs = [por_rep[rep].get(i) for rep in REPS]
        if any(r is None for r in regs):
            incompletas.append({"id_opaco": i, "reps_faltantes": [rep for rep, r in zip(REPS, regs) if r is None]})
            continue
        modales = [M.veredicto_modal([r["criterios"][k]["veredicto"] for r in regs]) for k in range(n)]
        clas = [r["clasificacion_respuesta"] for r in regs]
        v, cnt = Counter(clas).most_common(1)[0]
        agregados.append({"id_opaco": i, "n_criterios": n, "veredicto_pregunta": M.veredicto_pregunta(modales), "modales": modales,
                          "clasificacion_respuesta_modal": v if cnt > len(clas) / 2 else "sin_consenso"})
    return {"reps": len(REPS), "n_casos": len(casos), "n_agregados": len(agregados), "incompletas": incompletas,
            "agregados": agregados}


# --------------------------------------------------------------------------------------------------------------------- #
# La tabla de la mesa                                                                                                   #
# --------------------------------------------------------------------------------------------------------------------- #
def ruta_tabla(juez_dir: Path) -> Path:
    return juez_dir / "desanonimizacion_SOLO_MESA" / TABLA


def leer_tabla(juez_dir: Path) -> dict:
    p = ruta_tabla(juez_dir)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {
        "SOLO_MESA": True, "sal_id_opaco": SAL_ID_OPACO, "prefijo": PREFIJO_ID,
        "regla": "id_opaco = prefijo + sha256(sal|pregunta|brazo|repetición|sha256(respuesta))[:10]", "filas": {}}


def escribir_tabla(juez_dir: Path, tabla: dict) -> None:
    p = ruta_tabla(juez_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(tabla, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(p)


# --------------------------------------------------------------------------------------------------------------------- #
# Las tres repeticiones a la vez (etapa b1)                                                                             #
# --------------------------------------------------------------------------------------------------------------------- #
def costo_mayor_repeticion(juez_dir: Path) -> float:
    """El costo mayor de una repetición ya escrita; COSTO_REPETICION_INICIAL si no hay ninguna."""
    cs = [r["meta"]["input_tokens"] / 1e6 * PRECIO_IN + r["meta"]["output_tokens"] / 1e6 * PRECIO_OUT
          for rep in REPS for r in leer(juez_dir / f"veredictos_r{rep}.jsonl")]
    return max(cs) if cs else COSTO_REPETICION_INICIAL


class TresJueces:
    """Un hilo por repetición, cada uno con su cliente (creado en su hilo por factory(rep, etiqueta): su base b63_juez_r{rep}.db y su
    namespace juez_ev2_r{rep}) y su cola. `juzgar` lanza las repeticiones que le faltan a una respuesta, una tras otra, cada una cuando
    pasó la guarda del gasto (lo gastado, el agente más el juez, más lo reservado por las que están en vuelo y una repetición más, contra
    el freno y el tope), y espera las tres. Cada hilo escribe solo en su veredictos_r{rep}.jsonl y su errores_r{rep}.jsonl."""

    def __init__(self, factory, juez_dir: Path, cache_dir: Path):
        import queue
        import threading
        self.juez_dir, self.cache_dir = Path(juez_dir), Path(cache_dir)
        self.juez_dir.mkdir(parents=True, exist_ok=True)
        self.colas = {rep: queue.Queue() for rep in REPS}
        self.hilos = {rep: threading.Thread(target=self._trabajar, args=(rep, factory), daemon=True) for rep in REPS}
        self.lock = threading.Lock()
        for h in self.hilos.values():
            h.start()

    def _trabajar(self, rep: int, factory) -> None:
        import queue as _q
        cliente = None
        try:
            while True:
                tarea = self.colas[rep].get()
                if tarea is None:
                    return
                c, hecho = tarea
                try:
                    if cliente is None:
                        cliente = factory(rep, f"b63_juez_r{rep}")
                    r = J.juzgar(cliente, c["pregunta"], c["respuesta"], c["criterios"])
                    with (self.juez_dir / f"veredictos_r{rep}.jsonl").open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"id_opaco": c["id_opaco"], "rep": rep,
                                             "clasificacion_respuesta": r["veredicto"]["clasificacion_respuesta"],
                                             "criterios": r["veredicto"]["criterios"], "meta": r["meta"]}, ensure_ascii=False) + "\n")
                    hecho.put((rep, "veredicto", None))
                except ValueError as ex:
                    with (self.juez_dir / f"errores_r{rep}.jsonl").open("a", encoding="utf-8") as fe:
                        fe.write(json.dumps({"id_opaco": c["id_opaco"], "rep": rep, "error": str(ex)[:200],
                                             "ts": datetime.now().isoformat()}, ensure_ascii=False) + "\n")
                    hecho.put((rep, "error", None))
                except Exception as ex:                       # otro error del cliente: lo lleva al hilo principal
                    hecho.put((rep, "excepcion", f"{type(ex).__name__}"))
        finally:
            if cliente is not None and hasattr(cliente, "close"):
                cliente.close()

    def juzgar(self, c: dict, gastado_agente: float, freno: float, tope: float) -> dict:
        import queue
        h = hechas(self.juez_dir)
        pend = [rep for rep in REPS if c["id_opaco"] not in h[rep]]
        if not pend:
            return {"llamadas": 0, "errores": 0, "ya_estaba": True, "lanzadas": []}
        hecho, lanzadas, corte = queue.Queue(), [], None
        g = gasto(self.cache_dir)["usd"]                      # al empezar la respuesta; lo de las que lanza va reservado abajo
        una = costo_mayor_repeticion(self.juez_dir)
        for rep in pend:
            total = gastado_agente + g + una * (len(lanzadas) + 1)
            if total > freno or total > tope:
                corte = (f"lo gastado ({gastado_agente:.4f} del agente + {g:.4f} del juez) + {len(lanzadas)} repeticiones en vuelo y una "
                         f"más de {una:.4f} pasa el freno {freno} o el tope {tope}")
                break
            self.colas[rep].put((c, hecho))
            lanzadas.append(rep)
        llamadas = errores = 0
        excepciones = []
        for _ in lanzadas:
            rep, que, detalle = hecho.get()                  # la espera de cada repetición en vuelo, sin plazo
            llamadas += que == "veredicto"
            errores += que == "error"
            if que == "excepcion":
                excepciones.append((rep, detalle))
        if excepciones:
            raise RuntimeError(f"el cliente del juez levantó en {excepciones}")
        if corte:
            raise FrenoJuez(corte)
        return {"llamadas": llamadas, "errores": errores, "ya_estaba": False, "lanzadas": lanzadas}

    def cerrar(self) -> None:
        for rep in REPS:
            self.colas[rep].put(None)
        for h in self.hilos.values():
            h.join()

