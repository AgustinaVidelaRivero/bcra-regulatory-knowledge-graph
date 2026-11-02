#!/usr/bin/env python3
"""selftest_b64.py (b64/v1, B6.4) — El selftest del runner de B6.4 (USD 0, sin datos reales, sin Neo4j, sin Docker y sin ningún
subproceso con un script del patrón de otro paso pago: importa el runner, no lo corre). Es el de B6.3 (b63/v2/b2/selftest_b63.py),
sobre el runner de esta carpeta y con cuatro brazos (la configuración de juguete de seco/: kg, kg_n7, fragmentos_bm25 y
fragmentos_denso, con los roles de B6.4, y las preguntas de juguete de B6.3 con el esquema de las aprobadas de B6.4), con estas
diferencias:
  · R5: B6.4 corre con el A (32, 30 y 1,80, el de B6.3); el B de B6.3 tenía su configuración de juguete de tres brazos, así que acá la
    entrada con el B, sobre la de cuatro, frena como cualquier otro R5 que no es el de su configuración;
  · las cuentas, las de cuatro brazos;
  · el de la configuración de agentes es el de B6.4 (armar_config_agentes_b64.py): sus controles de sha256 (la lista del 241 y HEAD),
    la rearmada igual a la del archivo, sus cuatro brazos (kg_n7 igual al kg_N7 de B2), un sha256 esperado distinto que frena, y una
    entrada de juguete armada con armar_entrada_B64.py sobre ella que pasa los controles del runner;
  · sin el de la memoria del testigo: B6.4 no corre el testigo (reusa P y el pico de una sesión de la entrada de B6.3, decisión 3.4);
  · los de B6.4: los roles de los cuatro brazos en el runner y en el juez; las constantes del armador de la entrada, las del runner y del
    juez; y la decisión 3 (ninguna salida en el repo: --sesiones y --lotes dentro del repo frenan con el 10 sin escribir).
Todo sobre datos de juguete, en una carpeta temporal dentro de SELFTEST_B64_TMP (obligatoria: nada en la carpeta temporal del sistema).
Lo que imprime no trae horas ni rutas: dos corridas dan lo mismo.
Uso: SELFTEST_B64_TMP=<carpeta> <python del .venv del repo> -B data/experiment/banco_mcp/b64/v1/selftest_b64.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import correr_b63 as R                                       # noqa: E402  (el runner de B6.4, de esta misma carpeta: se importa)
from seco import herramientas_b64 as H                       # noqa: E402
import lanzar_agente_b63 as LZ                               # noqa: E402  (el lanzador de la sesión de B6.4: sus listas de campos)
import armar_config_agentes_b64 as AC                        # noqa: E402  (la configuración de agentes de B6.4)
import armar_entrada_B64 as AE                               # noqa: E402  (el armador de la entrada de B6.4)

K, JB, LOTE, G, V, MEM, DK, N4 = R.K, R.JB, R.LOTE, R.G, R.V, R.MEM, R.DK, R.N4
J = sys.modules["juez"]
LINEAS: list[list[str]] = []                                 # cada línea de comandos que lanzan las guardas, el lote y los controles


class Registrador:
    """En lugar del módulo subprocess de un módulo: anota la línea de comandos de cada run y Popen, y delega."""

    def __getattr__(self, n):
        return getattr(subprocess, n)

    def run(self, argv, *a, **kw):
        LINEAS.append(list(map(str, argv)))
        return subprocess.run(argv, *a, **kw)

    def Popen(self, argv, *a, **kw):                     # noqa: N802
        LINEAS.append(list(map(str, argv)))
        return subprocess.Popen(argv, *a, **kw)


for _m in (G, LOTE.BASE, K, MEM, DK, sys.modules["guardas_lote"]):
    _m.subprocess = Registrador()
if not os.environ.get("SELFTEST_B64_TMP"):
    raise SystemExit("falta SELFTEST_B64_TMP (la carpeta de trabajo del selftest; nada en la carpeta temporal del sistema)")
TMP = Path(tempfile.mkdtemp(prefix="selftest_b64_", dir=os.environ["SELFTEST_B64_TMP"]))
RES: list[tuple[bool, str]] = []
PATH0 = os.environ.get("PATH", "")
TOKEN = "prueba_b64_zq8rk4n2"
FALSO_VENTANA = "b63/v2/b2/seco/lanzador_falso_ventana.py"
B2 = H.B63 / "v2" / "b2"
PREG_VENTANA = H.a_esquema_b64(H.B63 / "v2" / "seco" / "preguntas_ventana_b63.json", TMP / "preguntas" / "preguntas_ventana_b64.json")
PREG_SECO = H.a_esquema_b64(B2 / "seco" / "preguntas_seco_b2.json", TMP / "preguntas" / "preguntas_seco_b64.json")
PREG_META = H.a_esquema_b64(B2 / "seco" / "preguntas_meta_b63.json", TMP / "preguntas" / "preguntas_meta_b64.json")
CUATRO = sorted(H.BRAZOS_JUGUETE)


def caso(nombre: str):
    def deco(f):
        try:
            ok, detalle = f()
        except Exception as ex:
            ok, detalle = False, f"{type(ex).__name__}: {str(ex)[:160]}"
        RES.append((bool(ok), nombre + (f" — {detalle}" if detalle else "")))
        return f
    return deco


def frena(f, *a, **kw):
    try:
        f(*a, **kw)
    except K.FrenoB63 as ex:
        return ex.codigo
    except SystemExit as ex:
        return str(ex)[:40] or True
    return None


def con_path(d: Path):
    os.environ["PATH"] = f"{d}:{PATH0}"


def bin_claude_falso(nombre: str) -> Path:
    """Una carpeta para el PATH con el `claude` falso de B6.3 (un guion que corre b63/v2/b2/seco/claude_falso_b63.py)."""
    d = TMP / nombre
    d.mkdir(parents=True, exist_ok=True)
    (d / "claude").write_text(f'#!/bin/sh\nexec "{sys.executable}" -B "{B2 / "seco" / "claude_falso_b63.py"}" "$@"\n', encoding="utf-8")
    (d / "claude").chmod(0o755)
    return d


def entrada(nombre: str, ids: list[str], **kw) -> tuple[Path, str]:
    return H.entrada_b64(TMP, nombre, ids, preguntas=kw.pop("preguntas", PREG_VENTANA), **kw)


# --------------------------------------------------------------------------------------------------------------------- #
@caso("R5: la entrada con el A (32, 30 y 1,80) pasa; con el B (47, 45 y 3,30) sobre la configuración de cuatro brazos, o con otro, frena")
def _():
    a = K.cargar_entrada(*entrada("r5a", ["VEN01"]))
    b = frena(K.cargar_entrada, *entrada("r5b", ["VEN01"], mutar=lambda e: e["R5"].update(max_turns=47, tope_tool_calls_prompt=45,
                                                                                            max_budget_usd=3.3)))
    otro = frena(K.cargar_entrada, *entrada("r5c", ["VEN01"], mutar=lambda e: e["R5"].update(max_turns=40)))
    return a["R5"]["max_turns"] == 32 and b == K.PRECONDICION and otro == K.PRECONDICION, None


@caso("R5 en el lote: con un R5 que no es uno de los admitidos, la ventana frena con el 5 sin lanzar ninguna sesión")
def _():
    e = {"R5": {"max_turns": 40, "tope_tool_calls_prompt": 30, "max_budget_usd": 1.8}}
    p = TMP / "entrada_r5_no_admitido.json"
    p.write_text(json.dumps(e), encoding="utf-8")
    lote = TMP / "lote_r5_no_admitido.json"
    lote.write_text(json.dumps({"sesiones": [{"id": "X-kg_n7", "brazo": "kg_n7", "pregunta": "p"}]}), encoding="utf-8")
    from argparse import Namespace
    a = Namespace(lote=lote, out=TMP / "r5_no_admitido", sesiones=TMP / "ses_r5", paralelo=1, modo="real", via="api", tope=10, freno=5,
                  presupuesto_sesion=None, lanzador=FALSO_VENTANA, timeout_s=60,
                  config_agentes="b64/v1/seco/config_agentes_b64_juguete.json", entrada=p, sha256_entrada=H.sha(p))
    L = V.LoteVentana(a)
    return L.correr() == LOTE.AISLAMIENTO and all(s["estado"] == "no lanzada" for s in L.sesiones), None


@caso("pip freeze --all: el de la entrada (24f4c064…) pasa; otro sha256 frena; la entrada sin él frena")
def _():
    ok = K.cargar_entrada(*entrada("pf_ok", ["VEN01"]))
    mal = frena(K.cargar_entrada, *entrada("pf_mal", ["VEN01"], mutar=lambda e: e["banco_venv_vector"].update(pip_freeze_sha256="0" * 64)))
    sin = frena(K.cargar_entrada, *entrada("pf_sin", ["VEN01"], mutar=lambda e: e["banco_venv_vector"].pop("pip_freeze_sha256")))
    return (ok["banco_venv_vector"]["pip_freeze_sha256"] == H.PIP_FREEZE_SELLADO and mal == K.PRECONDICION and sin == K.PRECONDICION), None


@caso("la entrada: P 1 o 2 (3 frena), pico mayor que 0, y el Neo4j con bolt://127.0.0.1:47687 y una huella de 64 hexadecimales")
def _():
    malas = {"P3": dict(P=3), "pico0": dict(pico=0), "uri": dict(mutar=lambda e: e["neo4j"].update(uri="bolt://127.0.0.1:7687")),
             "huella": dict(mutar=lambda e: e["neo4j"].update(huella_contenido="x")), "sin_neo4j": dict(mutar=lambda e: e.pop("neo4j"))}
    r = {n: frena(K.cargar_entrada, *entrada(f"e_{n}", ["VEN01"], **kw)) for n, kw in malas.items()}
    p2 = K.cargar_entrada(*entrada("e_p2", ["VEN01"], P=2))
    return all(v == K.PRECONDICION for v in r.values()) and p2["P"] == 2, f"frenan {sum(1 for v in r.values() if v)} de {len(r)}"


@caso("los roles de B6.4: el runner admite los cuatro (el grafo, el grafo sin corregir y los dos de fragmentos) y frena con tres, con un rol repetido o con uno que no es de B6.4; el juez trae los cuatro")
def _():
    ok = K.cargar_entrada(*entrada("roles_ok", ["VEN01"]))
    repetido = frena(K.cargar_entrada, *entrada("roles_rep", ["VEN01"], mutar=lambda e: e["brazos"]["kg_n7"].update(rol="grafo")))
    otro = frena(K.cargar_entrada, *entrada("roles_otro", ["VEN01"], mutar=lambda e: e["brazos"]["kg_n7"].update(rol="grafo_n7")))
    tres = frena(K.cargar_entrada, *H.H2.entrada_v2(TMP, "roles_tres", ["SEC01"], preguntas=B2 / "seco" / "preguntas_seco_b2.json"))
    roles = {b: x["rol"] for b, x in ok["brazos"].items()}
    return (sorted(K.ROLES) == sorted(roles.values()) == sorted(JB.CITAS_POR_ROL) and len(K.ROLES) == 4 and JB.CITAS_POR_ROL["grafo_sin_corregir"] == ()
            and repetido == otro == tres == K.PRECONDICION), f"roles {sorted(roles.values())}; con tres brazos frena: {tres == K.PRECONDICION}"


@caso("el patrón: el real de guardas_lote_r5, los dos nombres de la b1 y los seis de la b1 bis; el real solo no los ve; el de prueba, un token propio")
def _():
    p = R.control_patron()
    ve = all(re.search(R.PATRON_B1, n) for n in ("lanzar_lote_paralelo_r5.py", "correr_n6.py", "correr_b63.py") + R.NOMBRES_B1BIS)
    no_ve = not any(re.search(R.PATRON_REAL, n) for n in ("lanzar_lote_paralelo_r5.py", "correr_n6.py") + R.NOMBRES_B1BIS)
    viejo = LOTE.cli_del_path
    try:
        LOTE.cli_del_path = lambda: {"version": "2.1.241 (Claude Code)"}
        real = frena(R.fijar_patron_de_prueba, "prueba_b64_selftest1")
    finally:
        LOTE.cli_del_path = viejo
    return (all(p.values()) and ve and no_ve and real == K.PRECONDICION and G.PATRON_PAGO_REAL == R.PATRON_REAL
            and R.PATRON_B1 == R.PATRON_B1_V2 + R.SUFIJO_B1BIS), None


@caso("el patrón de la b1 bis: el nuevo ve un proceso de prueba propio con cada uno de los seis nombres (en una ruta con un token propio) y el de la b1 no; ninguna guarda lo cuenta")
def _():
    carpeta = TMP / "procesos_b1bis" / TOKEN
    obs = {}
    for n in R.NOMBRES_B1BIS:
        pr = H.ProcesoConNombre(carpeta, n)
        LINEAS.append(pr.argv)
        try:
            linea = pr.linea()
        finally:
            pr.cerrar()
        guion = f"python3 -B {carpeta / n}"                    # la línea de un Python con ese guion, solo como texto
        nombre = G.script_python(guion).rsplit("/", 1)[-1]
        obs[n] = (TOKEN in linea and n in linea and bool(re.search(R.PATRON_B1, linea)) and not re.search(R.PATRON_B1_V2, linea)
                  and G.script_python(linea) is None
                  and bool(re.search(R.PATRON_B1, nombre)) and not re.search(R.PATRON_B1_V2, nombre))
    return all(obs.values()), f"{sum(obs.values())} de {len(obs)} nombres"


@caso("el patrón de prueba: con el CLI falso, la guarda busca el token; pgrep ve un proceso de prueba propio vivo y no al cerrarlo")
def _():
    con_path(H.bin_falso(TMP, "bin_patron"))
    try:
        R.fijar_patron_de_prueba(TOKEN)
        g = TMP / "procesos" / f"{TOKEN}.py"
        g.parent.mkdir(parents=True, exist_ok=True)
        g.write_text("import sys\nsys.stdin.read()\n", encoding="utf-8")
        pr = H.Prueba(["python3", str(g)])
        LINEAS.append(pr.argv)
        vivo = pr.p.pid in G.pgrep()
        nombre = bool(re.search(G.PATRON_PAGO, G.script_python(f"python3 {g}").rsplit("/", 1)[-1]))
        pr.cerrar()
        despues = pr.p.pid not in G.pgrep()
        sin_real = not re.search(R.PATRON_B1, f"{TOKEN}.py")
    finally:
        os.environ["PATH"] = PATH0
    return vivo and nombre and despues and sin_real and G.PATRON_PAGO == LOTE.patron_de_prueba(TOKEN), None


FORMAS = json.loads(R.FORMAS.read_text(encoding="utf-8"))["formas"]


def stream_de(f: dict) -> str:
    ev = [{"type": "system", "subtype": "init"}]
    ev += [{"type": "system", "subtype": "api_retry", "error_status": int(s) if s.isdigit() else None}
           for s in f["api_retry_error_status"]]
    if f["hay_result"]:
        r = {"type": "result", "subtype": f["subtype"], "is_error": f["is_error"]}
        if isinstance(f.get("api_error_status"), int):
            r["api_error_status"] = f["api_error_status"]
        ev.append(r)
    return "".join(json.dumps(x) + "\n" for x in ev)


@caso("las formas reales: cada una de formas_reales_b63.json da su clase en el clasificador; la clave inválida, la suya; una forma nueva, desconocida")
def _():
    infra = R.formas_de_infraestructura()
    obs = {}
    for f in FORMAS + [{"caso": "inventada", "hay_result": True, "subtype": "error_x", "is_error": True, "api_retry_error_status": [],
                        "clase": "desconocida"}]:
        d = TMP / "formas" / f["caso"] / "S"
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta_S.json").write_text(json.dumps({"completitud_R3": {"completa": False}, "duracion_s": 5}), encoding="utf-8")
        (d / "stream_S.jsonl").write_text(stream_de(f), encoding="utf-8")
        obs[f["caso"]] = R.clasificar({"id": "S", "estado": "terminada"}, d.parent, "real", 1800.0, infra)[0] == f["clase"]
    return all(obs.values()), ", ".join(f"{f['caso']}: {f['clase']}" for f in FORMAS)


def corrida(nombre: str, ids: list[str], **kw) -> R.CorridaB63:
    """Una corrida del runner de B6.4 con la ventana, el juez falso y los dobles de memoria, Docker y Neo4j (con su `out`, su `juez_dir`,
    sus `sesiones` y sus `lotes`, si se pasan)."""
    ent, s = entrada(nombre, ids, preguntas=kw.pop("preguntas", PREG_VENTANA), P=kw.pop("P", 1), freno=kw.pop("freno", 40.0),
                     tope=kw.pop("tope", 50.0))
    e = K.cargar_entrada(ent, s)
    preg = K.cargar_preguntas(e)
    R.preparar_entorno(e)
    base = TMP / nombre
    c = R.CorridaB63(e, preg, modo="real", out=kw.pop("out", base / "out"), sesiones=kw.pop("sesiones", base / "ses"),
                     juez_dir=kw.pop("juez_dir", base / "juez"), lotes=kw.pop("lotes", base / "lotes"),
                     client_factory=kw.pop("factory", None) or (lambda rep, label: H.ClienteJuez()),
                     medir_memoria=kw.pop("medir", lambda: {"en_uso_gb": 5.0, "swap_usado_gb": 0.1}),
                     control_docker=kw.pop("docker", lambda m=None: {"evento": "control de Docker", "ok": True, "motivo": None}),
                     control_neo4j=kw.pop("neo4j", lambda: {"ok": True, "motivo": None}))
    return c


def con_ventana(f, lanzador: str = FALSO_VENTANA, cli: Path | None = None):
    """Corre f con un lanzador de la sesión (por defecto el falso de la ventana), un CLI falso en el PATH y el patrón de prueba."""
    viejo = K.LANZADOR_SESION
    con_path(cli or H.bin_falso(TMP, "bin_ventana"))
    os.environ["NEO4J_URI"] = "bolt://127.0.0.1:47687"
    os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_DE_RELLENO
    try:
        R.fijar_patron_de_prueba(TOKEN)
        K.LANZADOR_SESION = lanzador
        return f()
    finally:
        K.LANZADOR_SESION = viejo
        os.environ["PATH"] = PATH0
        os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_DE_RELLENO


def lanzados(c: R.CorridaB63, pasada: int | None = None) -> list[str]:
    out = []
    for n in ([pasada] if pasada else range(1, c.estado["pasadas"] + 1)):
        reg = json.loads((c.out / f"pasada{n}" / "registro_lote.json").read_text(encoding="utf-8"))
        out += [e["id"] for e in reg["eventos"] if e["evento"] == "lanza"]
    return out


@caso("la ventana con P = 1: en el orden firmado, con los cuatro brazos de cada bloque seguidos, y cada reintento en el primer lugar libre")
def _():
    def f():
        c = corrida("ventana_p1", ["VEN01", "VEN02", "VEN03"])
        cod = c.correr()
        ids = lanzados(c)
        esperado = []
        for b in c.orden:
            for x in b["brazos"]:
                esperado.append(K.id_sesion(b["qid"], 1, x))
                if b["qid"] == "VEN02":
                    esperado.append(K.id_sesion(b["qid"], 1, x, 2))
        fin = {b: {x: f["clasificacion"] for x, f in st["final"].items()} for b, st in c.estado["bloques"].items()}
        cuatro = all(sorted(b["brazos"]) == CUATRO for b in c.orden)
        return (cod == 0 and ids == esperado and len(ids) == 16 and cuatro and all(v == "completa" for st in fin.values() for v in st.values())
                and len(JB.leer_tabla(c.juez_dir)["filas"]) == 12), f"{len(ids)} sesiones lanzadas, {c.estado['pasadas']} pasada"
    return con_ventana(f)


@caso("la ventana con P = 2: nunca más de 2 a la vez, y el reintento es la sesión que se lanza enseguida de que su falla terminó")
def _():
    def f():
        c = corrida("ventana_p2", ["VEN01", "VEN02", "VEN03"], P=2)
        cod = c.correr()
        reg = json.loads((c.out / "pasada1" / "registro_lote.json").read_text(encoding="utf-8"))
        ev = reg["eventos"]
        maximo = max(e["corriendo_con_ella"] for e in ev if e["evento"] == "lanza")
        ok_frente = True
        for i, e in enumerate(ev):
            if e["evento"] == "inserta":
                siguiente = next(x for x in ev[i + 1:] if x["evento"] == "lanza")
                ok_frente &= siguiente["id"] == e["ids"][0]
        n_ins = sum(1 for e in ev if e["evento"] == "inserta")
        return cod == 0 and maximo == 2 and ok_frente and n_ins == 4, f"máximo a la vez {maximo}; {n_ins} reintentos insertados"
    return con_ventana(f)


@caso("los reintentos: hasta 3 intentos por brazo; con la falla en los tres, falla_infra_sin_terminar y ningún cuarto")
def _():
    def f():
        c = corrida("infra3", ["VEN07"])
        cod = c.correr()
        st = c.estado["bloques"]["VEN07-r1"]
        return (cod == 0 and all(v["clasificacion"] == "falla_infra_sin_terminar" for v in st["final"].values()) and len(st["final"]) == 4
                and all(n == 3 for n in st["intentos_por_brazo"].values()) and len(lanzados(c)) == 12), None
    return con_ventana(f)


@caso("la opción (d): cada forma desconocida deja la sesión incompleta y se declara; con la tercera, el lote frena con el 12")
def _():
    def f():
        c = corrida("opcion_d", ["VEN04", "VEN05", "VEN06"])
        cod = c.correr()
        n_lanz = len(lanzados(c))
        return (cod == K.DESCONOCIDAS and len(c.estado["desconocidas"]) == 3 and n_lanz == 3
                and "tres formas desconocidas" in (c.estado["freno"] or "")), f"{n_lanz} lanzadas antes del freno"
    return con_ventana(f)


@caso("la corrida cortada no va al juez; la guarda del gasto del agente y el juez juntos frena antes del freno")
def _():
    def f():
        c = corrida("corte", ["VEN08"])
        cod = c.correr()
        corte = cod == 0 and all(v["clasificacion"] == "cortada" for v in c.estado["bloques"]["VEN08-r1"]["final"].values()) \
            and len(c.estado["bloques"]["VEN08-r1"]["final"]) == 4 and not JB.leer_tabla(c.juez_dir)["filas"]
        pedidos = []
        g = corrida("gasto", ["VEN01"], freno=1.85, tope=2.0, factory=H.juez_simulado(TMP / "gasto" / "juez" / "cache", pedidos))
        codg = g.correr()
        return (corte and codg == 2 and len(lanzados(g)) == 2 and len(pedidos) == 6), \
            "lanza 2 (1,8 más lo del juez, 0,0288 por respuesta) y frena antes de la tercera"
    return con_ventana(f)


@caso("los ganchos de la ventana: la memoria (13), Docker (14) y el Neo4j (15) frenan sin lanzar, cada uno con su código")
def _():
    def f():
        m = corrida("gancho_mem", ["VEN01"], medir=lambda: {"en_uso_gb": 13.0, "swap_usado_gb": 0.1})
        d = corrida("gancho_docker", ["VEN01"], docker=lambda mm=None: {"evento": "control de Docker", "ok": False, "motivo": "doble"})
        n = corrida("gancho_neo4j", ["VEN01"], neo4j=lambda: {"ok": False, "motivo": "doble"})
        cods = (m.correr(), d.correr(), n.correr())
        return cods == (K.MEMORIA, K.DOCKER, K.NEO4J) and not any(lanzados(x) for x in (m, d)), f"códigos {cods}"
    return con_ventana(f)


def clave_invalida_antes_de(c: R.CorridaB63, n: int) -> None:
    """La clave pasa a la de relleno inválida justo antes de lanzar la sesión n del lote (solo en la prueba)."""
    gancho, cuenta = c.antes_de_lanzar, {"n": 0}

    def antes(L, s, corriendo):
        r = gancho(L, s, corriendo)
        if r is None:
            cuenta["n"] += 1
            if cuenta["n"] == n:
                os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_INVALIDA_DE_RELLENO
        return r
    c.antes_de_lanzar = antes


def retomar(nombre: str, ids: list[str], P: int) -> R.CorridaB63:
    """La misma corrida otra vez, con la clave buena: el runner retoma desde su estado."""
    os.environ["ANTHROPIC_API_KEY"] = H.CLAVE_DE_RELLENO
    return corrida(nombre, ids, P=P, preguntas=PREG_SECO)


def prueba_clave(nombre: str, P: int, antes_de: int) -> tuple[bool, str]:
    """La clave pasa a la inválida antes de la sesión `antes_de` del lote: con P = 1, antes de la cuarta; con P = 2, antes de la primera."""
    ids = ["SEC01", "SEC03", "SEC08"]
    c = corrida(nombre, ids, P=P, preguntas=PREG_SECO)
    clave_invalida_antes_de(c, antes_de)
    cod = c.correr()
    p1 = lanzados(c, 1)
    reg = json.loads((c.out / "pasada1" / "registro_lote.json").read_text(encoding="utf-8"))
    malas = [x["id"] for x in c.estado["clave_invalida"]]
    contadas = {s["id"] for s in c.estado["sesiones"]}
    finales = {f["id"] for st in c.estado["bloques"].values() for f in st["final"].values()}
    juzgadas = {f["id_sesion"] for f in JB.leer_tabla(c.juez_dir)["filas"].values()}
    no_cuenta = [s["id"] for s in reg["sesiones"] if s.get("no_cuenta")]
    terminadas_1 = {s["id"] for s in c.estado["sesiones"] if s["clasificacion"] != "no_lanzada"}
    ev = reg["eventos"]
    i_freno = next(i for i, e in enumerate(ev) if e["evento"] == "freno")
    tras_freno = [e["id"] for e in ev[i_freno + 1:] if e["evento"] == "termina"]
    lanza_tras_freno = [e["id"] for e in ev[i_freno + 1:] if e["evento"] == "lanza"]
    esperadas = (4, 1, 0) if P == 1 else (2, 2, 1)             # lanzadas, de la clave inválida, terminadas después del freno
    primera = (cod == K.CLAVE_INVALIDA and (len(p1), len(malas), len(tras_freno)) == esperadas and sorted(malas) == sorted(no_cuenta)
               and not lanza_tras_freno and not set(malas) & (contadas | finales | juzgadas) and c.estado["codigo"] == K.CLAVE_INVALIDA
               and set(tras_freno) <= contadas | set(malas))
    r = retomar(nombre, ids, P)
    cod2 = r.correr()
    p2 = lanzados(r, 2)
    n_final = sum(len(st["final"]) for st in r.estado["bloques"].values())
    todas = all(f["clasificacion"] == "completa" for st in r.estado["bloques"].values() for f in st["final"].values())
    segunda = (cod2 == 0 and set(malas) <= set(p2) and not set(p2) & terminadas_1 and len(p1) + len(p2) == 12 + len(malas) and todas
               and n_final == 12 and len(JB.leer_tabla(r.juez_dir)["filas"]) == 12 and len(r.estado["clave_invalida"]) == len(malas))
    return primera and segunda, (f"pasada 1: {len(p1)} lanzadas, {len(malas)} con la clave inválida (fuera de las cuentas), "
                                 f"{len(terminadas_1)} terminadas que cuentan, {len(tras_freno)} terminada después del freno y ninguna "
                                 f"lanzada; al retomar: {len(p2)} lanzadas, ninguna repetida; {n_final} finales completas y juzgadas")


@caso("la clave inválida con P = 1: con el lanzador de la sesión y el CLI falso (la forma real del 401), el lote frena a la primera con el 16 sin lanzar otra; la sesión no cuenta ni va al juez; retomar con la clave buena la corre y no repite ninguna terminada")
def _():
    return con_ventana(lambda: prueba_clave("clave_p1", 1, 4), lanzador=K.LANZADOR_SESION, cli=bin_claude_falso("bin_clave_p1"))


@caso("la clave inválida con P = 2: la sesión que corría a la vez termina después del freno, queda registrada (también con el 401) y al retomar se corre una vez, sin repetir ninguna terminada")
def _():
    return con_ventana(lambda: prueba_clave("clave_p2", 2, 1), lanzador=K.LANZADOR_SESION, cli=bin_claude_falso("bin_clave_p2"))


class LoteDoble:
    """Lo que `al_terminar` lee del lote: su carpeta y lo acumulado de la guarda."""

    def __init__(self, out: Path):
        self.out, self.acumulado_guarda = out, 0.0


@caso("después de un freno (frenado): una sesión completa se registra y su juez queda para el retomar; una falla de infraestructura, sin insertar su reintento, que queda para el retomar")
def _():
    c = corrida("frenado", ["VEN01"])
    L = LoteDoble(TMP / "frenado" / "out" / "pasada1")
    b = c.orden[0]
    x, y = b["brazos"][0], b["brazos"][1]
    sc, sf = c.sesion(b, x, 1), c.sesion(b, y, 1)
    c._info = {sc["id"]: sc, sf["id"]: sf}
    for s, f in ((sc, None), (sf, next(z for z in FORMAS if z["caso"] == "http_429"))):
        d = L.out / s["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / f"meta_{s['id']}.json").write_text(json.dumps({"completitud_R3": {"completa": f is None}, "duracion_s": 5,
                                                             "final_json_R4": {"respuesta": "r", "citas": [], "respondible": True}}),
                                                 encoding="utf-8")
        ok_stream = '{"type": "result", "subtype": "success", "is_error": false}\n'
        (d / f"stream_{s['id']}.jsonl").write_text(ok_stream if f is None else stream_de(f), encoding="utf-8")
    rc = c.al_terminar(L, sc | {"estado": "terminada", "posicion": 1}, frenado=True)
    rf = c.al_terminar(L, sf | {"estado": "terminada", "posicion": 2}, frenado=True)
    st = c.estado["bloques"][b["bloque"]]
    ok = (not rc and not rf and st["final"][x]["clasificacion"] == "completa" and st["juez_pendiente"] == [x]
          and not JB.leer_tabla(c.juez_dir)["filas"] and st["final"][y]["clasificacion"] == "falla_infra"
          and c.falta(b, x) is None and c.falta(b, y) == 2 and len(c.estado["sesiones"]) == 2)
    return ok, "la completa registrada con su juez pendiente; la falla, con su reintento para el retomar (intento 2)"


@caso("el Neo4j de B6.3: con el doble, la huella de la entrada pasa; otra huella, otro KG_Meta, otro NEO4J_URI o sin respuesta frenan")
def _():
    cfg = json.loads(N4.CONFIG_GRAFO.read_text(encoding="utf-8"))
    os.environ["NEO4J_URI"] = N4.URI_B63
    try:
        bien = H.Neo4jDoble(H.HUELLA_B63, cfg["kg_sha256_esperado"])
        ok = N4.estado(H.HUELLA_B63, ck=bien, abrir=bien.abrir)["ok"]
        otra = H.Neo4jDoble("0" * 64, cfg["kg_sha256_esperado"])
        meta = H.Neo4jDoble(H.HUELLA_B63, "0" * 64)
        cae = H.Neo4jDoble(H.HUELLA_B63, cfg["kg_sha256_esperado"], falla=True)
        malos = [N4.estado(H.HUELLA_B63, ck=x, abrir=x.abrir)["ok"] for x in (otra, meta, cae)]
        os.environ["NEO4J_URI"] = "bolt://127.0.0.1:7687"
        uri = N4.estado(H.HUELLA_B63, ck=bien, abrir=bien.abrir)["ok"]
    finally:
        os.environ["NEO4J_URI"] = N4.URI_B63
    return ok and not any(malos) and not uri and cfg["grafo"] == "KG_Acumulado_Tandas0y1yFinal_r2b_sincola", None


@caso("la memoria: la copia de memoria_maquina da lo mismo que la de N6 sobre un vm_stat falso")
def _():
    sys.path.insert(0, str(K.BANCO_DIR / "n6"))
    import memoria_n6                                         # noqa: PLC0415  (HEAD: solo import, para comparar)
    sys.path.remove(str(K.BANCO_DIR / "n6"))
    con_path(H.bin_falso(TMP, "bin_mem"))
    try:
        a, b = MEM.memoria_maquina(), memoria_n6.memoria_maquina()
    finally:
        os.environ["PATH"] = PATH0
    return a == b and a["en_uso_gb"] == round((300000 + 150000 + 50000) * 16384 / 1e9, 3), f"en uso {a['en_uso_gb']} GB"


@caso("la regla y la guarda de memoria: entra P = 2; entra solo P = 1 (con P = 2 en la entrada, frena); no entra ninguna")
def _():
    def medir(gb):
        return lambda: {"en_uso_gb": gb, "swap_usado_gb": 0.2}
    dos = MEM.guarda(2, 4.0, medir(5.4))
    uno = MEM.guarda(1, 4.0, medir(8.0))
    uno_con_2 = MEM.guarda(2, 4.0, medir(8.0))
    ninguna = MEM.guarda(1, 4.0, medir(11.0))
    reglas = (MEM.regla_P(5.4, 4.0), MEM.regla_P(8.0, 4.0), MEM.regla_P(11.0, 4.0))
    return (dos["ok"] and uno["ok"] and not uno_con_2["ok"] and not ninguna["ok"] and reglas == (2, 1, 0)
            and uno_con_2["P_que_entra"] == 1), f"P por la regla {reglas}"


@caso("el comando con env -i: con LANG=es_AR.UTF-8 en el entorno padre, `comando_b64.zsh medir` mide bien y pasa solo PATH, HOME y NEO4J_URI; sin el comando, la medición corta (el control positivo) y el runner frena con el 10")
def _():
    ent, s = entrada("comando", ["VEN01"])
    padre = {"PATH": f"{PATH0}:/usr/sbin" if ":/usr/sbin" not in f":{PATH0}" else PATH0, "HOME": os.environ["HOME"],
             "LANG": "es_AR.UTF-8", "VARIABLE_DE_LA_TERMINAL_B64": "x", "ANTHROPIC_API_KEY": H.CLAVE_DE_RELLENO,
             "B63_PYTHON": sys.executable}
    argv = ["zsh", str(AQUI / "comando_b64.zsh"), "medir", str(ent)]
    LINEAS.append(argv)
    r = subprocess.run(argv, env=padre, capture_output=True, text=True)
    salida = json.loads(r.stdout.splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else {}
    linea = r.stdout.splitlines()[0] if r.stdout.strip() else ""
    mide = r.returncode == 0 and isinstance((salida.get("memoria") or {}).get("en_uso_gb"), float)
    nombres = salida.get("entorno_nombres")
    directo = [sys.executable, "-B", str(B2 / "memoria_b63.py")]
    LINEAS.append(directo)
    d = subprocess.run(directo, env=padre, capture_output=True, text=True)
    corta = d.returncode != 0 and "AttributeError" in d.stderr
    viejo = os.environ.get("LANG")
    os.environ["LANG"] = "es_AR.UTF-8"
    try:
        cod = frena(R.controles, ent, s, "init")
    finally:
        if viejo is None:
            os.environ.pop("LANG", None)
        else:
            os.environ["LANG"] = viejo
    coercion = "LC_CTYPE" not in (nombres or []) or salida.get("LC_CTYPE") in ("UTF-8", "C.UTF-8", "C.utf8")
    return (mide and set(nombres or []) <= {"PATH", "HOME", "NEO4J_URI", "LC_CTYPE", "__CF_USER_TEXT_ENCODING"}
            and {"PATH", "HOME", "NEO4J_URI"} <= set(nombres or []) and coercion and corta and cod == K.PRECONDICION
            and linea == "comando_b64: env -i con PATH, HOME, NEO4J_URI"), \
        (f"el comando dice que pasa: {linea.split(' con ', 1)[-1]}; "
         f"nombres del entorno con el comando: {sorted(set(nombres or []) - {'__CF_USER_TEXT_ENCODING'})} (LC_CTYPE: "
         f"{salida.get('LC_CTYPE')}, del intérprete); sin el comando corta: {corta}; el runner: {cod}")


@caso("Docker: con la VM en 2,5 GiB y el contenedor sano pasa y registra su memoria; con la VM más grande o sin salud, frena")
def _():
    out = {}
    for n, kw in (("ok", {}), ("vm", {"vm_bytes": 4_294_967_296}), ("salud", {"salud": "unhealthy"})):
        con_path(H.bin_falso(TMP, f"bin_docker_{n}", **kw))
        try:
            out[n] = DK.control(MEM.memoria_maquina)
        finally:
            os.environ["PATH"] = PATH0
    return (out["ok"]["ok"] and out["ok"]["memoria_del_contenedor"] == "512MiB / 2.5GiB" and "maquina_swap_usado_gb" in out["ok"]
            and not out["vm"]["ok"] and not out["salud"]["ok"]), None


@caso("el juez de a tres: da lo mismo que de a una con un cliente falso, en las respuestas de los cuatro brazos, y con la caché real cada base tiene solo su namespace")
def _():
    preg = {"Q1": {"pregunta": "p", "criterios": [{"criterio": "c1", "cita_textual": "t1"}, {"criterio": "c2", "cita_textual": "t2"}]}}
    casos = [JB.caso_ciego("Q1", b, 1, f"respuesta de juguete {b}", preg) for b in CUATRO]
    d1, d3 = TMP / "juez_uno", TMP / "juez_tres"
    cl = {rep: H.ClienteJuez() for rep in JB.REPS}
    for c in casos:
        JB.juzgar(c, cl, d1, d1 / "cache", 0.0, 10.0, 12.0)
    tres = JB.TresJueces(lambda rep, label: H.ClienteJuez(), d3, d3 / "cache")
    try:
        r = [tres.juzgar(c, 0.0, 10.0, 12.0) for c in casos]
    finally:
        tres.cerrar()

    def norm(d):
        return {rep: sorted(json.dumps({k: v for k, v in x.items()}, sort_keys=True) for x in JB.leer(d / f"veredictos_r{rep}.jsonl"))
                for rep in JB.REPS}
    igual = norm(d1) == norm(d3) and JB.agregar(d1, {c["id_opaco"]: 2 for c in casos}) == JB.agregar(d3, {c["id_opaco"]: 2 for c in casos})
    ds = TMP / "juez_cache"
    pedidos = []
    t2 = JB.TresJueces(H.juez_simulado(ds / "cache", pedidos), ds, ds / "cache")
    try:
        for c in casos:
            t2.juzgar(c, 0.0, 10.0, 12.0)
    finally:
        t2.cerrar()
    ns = {}
    for rep in JB.REPS:
        con = sqlite3.connect(str(JB.db_path(rep, ds / "cache")))
        ns[rep] = sorted({x[0] for x in con.execute("SELECT namespace FROM cache")})
        con.close()
    sin_cruces = all(ns[rep] == [J.lc.make_namespace(f"juez_ev2_r{rep}", code_ver=J.CODE_VER, thinking=False)] for rep in JB.REPS)
    return (igual and all(x["lanzadas"] == [1, 2, 3] for x in r) and sin_cruces and len(pedidos) == 12), \
        f"{len(pedidos)} pedidos al transporte; una base y un namespace por repetición"


@caso("el juez de a tres y la guarda: con el gasto al borde, lanza las que entran, espera las que están en vuelo y corta antes del freno")
def _():
    d = TMP / "juez_guarda3"
    preg = {"Q1": {"pregunta": "p", "criterios": [{"criterio": "c1", "cita_textual": "t1"}]}}
    c = JB.caso_ciego("Q1", "kg_n7", 1, "respuesta", preg)
    tres = JB.TresJueces(lambda rep, label: H.ClienteJuez(), d, d / "cache")
    try:
        try:
            tres.juzgar(c, 9.97, 10.0, 12.0)              # entran dos de 0,0126 (9,97 + 0,0252 ≤ 10), no la tercera
            corto = False
        except JB.FrenoJuez:
            corto = True
        hechas = JB.hechas(d)
    finally:
        tres.cerrar()
    return corto and [c["id_opaco"] in hechas[rep] for rep in JB.REPS] == [True, True, False], None


def sesion_del_lanzador(nombre: str, pregunta: str, cli: Path) -> tuple[subprocess.CompletedProcess, Path]:
    """Una sesión del lanzador de B6.4, en modo real, en el cuarto brazo de juguete, con el CLI falso de B6.3 y una clave de relleno."""
    cfg = H.CONFIG_JUGUETE
    out = TMP / nombre / "B63-MET01-r1-kg_n7"
    env = {"PATH": f"{cli}:{PATH0}", "HOME": os.environ["HOME"], "ANTHROPIC_API_KEY": H.CLAVE_DE_RELLENO,
           "BANCO_VENV_VECTOR": str(K.ruta_de_rel(H.VENV_VECTOR)), "B63_CONFIG_AGENTES": str(cfg), "B63_CONFIG_AGENTES_SHA256": H.sha(cfg),
           "B63_VENV_PYTHON": "3.12"}
    argv = [sys.executable, "-B", str(AQUI / "lanzar_agente_b63.py"), "--brazo", "kg_n7", "--id", out.name, "--pregunta", pregunta,
            "--out", str(out), "--modo", "real", "--sesiones", str(TMP / f"{nombre}_ses")]
    LINEAS.append(argv)
    return subprocess.run(argv, env=env, capture_output=True, text=True), out


@caso("la atribución y el stream en la meta: una sesión del cuarto brazo deja el stream y el log R1 en su carpeta; la meta trae los dos, con su ruta y su sha256, y la cadena del lanzador de B6.4")
def _():
    r, out = sesion_del_lanzador("atrib", "Pregunta de juguete de la atribución [[b63:normal]]", bin_claude_falso("bin_atrib"))
    m = json.loads((out / f"meta_{out.name}.json").read_text(encoding="utf-8"))
    st, lg = out / f"stream_{out.name}.jsonl", out / f"log_r1_{out.name}.jsonl"
    log_en_meta = m["log_r1"].get("sha256") == H.sha(lg) and m["log_r1"]["ruta"].endswith(lg.name)
    stream_en_meta = (m.get("stream") or {}).get("sha256") == H.sha(st) and m["stream"]["ruta"].endswith(st.name)
    cadena = [x["ruta"].rsplit("/", 2)[-2] + "/" + x["ruta"].rsplit("/", 1)[-1] for x in m["harness_R10"]["lanzador"][:7]]
    cadena_ok = cadena == ["v1/correr_b63.py", "v1/comun_b63.py", "v1/juez_b63.py", "b2/ventana_b63.py", "b2/memoria_b63.py",
                           "b2/docker_b63.py", "b2/control_neo4j_b63.py"]
    return (r.returncode == 0 and st.is_file() and lg.is_file() and log_en_meta and stream_en_meta and cadena_ok
            and m["unidad"] == LZ.UNIDAD and m["brazo"] == "kg_n7"), \
        f"stream y log R1 en su carpeta; en la meta, los dos con su ruta y su sha256; la cadena de B6.4: {cadena_ok}"


@caso("la meta sin texto: trae exactamente las claves de la lista cerrada; ninguna ventana de 30 caracteres de la pregunta, del criterio ni de la respuesta de juguete en ella, y sí en la completa; y el sha256 de la meta completa que trae es el de la completa")
def _():
    pr = json.loads(PREG_META.read_text(encoding="utf-8"))["preguntas"][0]
    r, out = sesion_del_lanzador("meta", pr["pregunta"], bin_claude_falso("bin_meta"))
    mc, ms = out / f"meta_{out.name}.json", out / f"meta_sin_texto_{out.name}.json"
    completa, sin = mc.read_text(encoding="utf-8"), ms.read_text(encoding="utf-8")
    m, s = json.loads(completa), json.loads(sin)
    respuesta = (m.get("final_json_R4") or {}).get("respuesta") or ""
    fuentes = {"pregunta": pr["pregunta"], "criterio": pr["criterios"][0]["criterio"], "respuesta": respuesta}
    en_sin = {k: sum(w in sin for w in H.ventanas(t)) for k, t in fuentes.items()}
    en_completa = {k: sum(w in completa for w in H.ventanas(t)) for k, t in fuentes.items()}
    claves = tuple(s) == LZ.CLAVES_SIN_TEXTO
    mapa = (len(s["mapa_R7"]) == len(m["mapa_R7"]) == 1
            and all(set(x) == {"n", "tool_use_id", "tool", "call_id_log", "coincide_tool_input", "input_sha256"} for x in s["mapa_R7"])
            and s["mapa_R7"][0]["input_sha256"] == LZ.sha256_canonico(m["mapa_R7"][0]["input"]))
    fj = s["final_json_R4"] == {"sha256": LZ.sha256_canonico(m["final_json_R4"]), "n_citas": 2}
    sha = s["meta_completa"]["sha256"] == H.sha(mc) and s["stream"] == m["stream"]
    tal_cual = all(s[k] == m.get(k) for k in LZ.CAMPOS_TAL_CUAL + LZ.CAMPOS_DEL_LANZADOR)
    return (r.returncode == 0 and claves and not any(en_sin.values()) and all(en_completa.values()) and mapa and fj and sha
            and tal_cual and s["permission_denials"] == 0), \
        (f"{len(s)} claves; ventanas en la sin texto: {en_sin}; en la completa: "
         f"{ {k: v > 0 for k, v in en_completa.items()} }")


@caso("las formas reales con el CLI falso de B6.3: cada plan `forma_real` deja una sesión del cuarto brazo que el runner clasifica con la clase medida")
def _():
    falso = bin_claude_falso("bin_formas")
    cfg = H.CONFIG_JUGUETE
    env = {"PATH": f"{falso}:{PATH0}", "HOME": os.environ["HOME"], "ANTHROPIC_API_KEY": H.CLAVE_DE_RELLENO,
           "BANCO_VENV_VECTOR": str(K.ruta_de_rel(H.VENV_VECTOR)), "B63_CONFIG_AGENTES": str(cfg), "B63_CONFIG_AGENTES_SHA256": H.sha(cfg),
           "B63_VENV_PYTHON": "3.12"}
    planes = {"http_429": "real_http_429", "http_500": "real_http_500", "http_529": "real_http_529",
              "puerto_cerrado": "real_puerto_cerrado", "clave_invalida": "clave_invalida"}
    infra, obs = R.formas_de_infraestructura(), {}
    for f in FORMAS:
        out = TMP / "formas_cli" / f["caso"] / "B63-FOR01-r1-kg_n7"
        argv = [sys.executable, "-B", str(AQUI / "lanzar_agente_b63.py"), "--brazo", "kg_n7", "--id", out.name, "--pregunta",
                f"Pregunta de juguete de las formas [[b63:{planes[f['caso']]}]]", "--out", str(out), "--modo", "real",
                "--sesiones", str(TMP / "formas_cli_ses" / f["caso"])]
        LINEAS.append(argv)
        subprocess.run(argv, env=env, capture_output=True, text=True)
        clase, forma = R.clasificar({"id": out.name, "estado": "terminada"}, out.parent, "real", 1800.0, infra)
        obs[f["caso"]] = (clase == f["clase"] and forma["subtype"] == f["subtype"] and forma["is_error"] == f["is_error"]
                          and forma["api_retry_error_status"] == f["api_retry_error_status"], clase)
    return all(v[0] for v in obs.values()), ", ".join(f"{k}: {v[1]}" for k, v in obs.items())

# --------------------------------------------------------------------------------------------------------------------- #
# La configuración, el juez fuera del repo, el manifiesto y la salida que no se lee (b2 de B6.3), y lo de B6.4             #
# --------------------------------------------------------------------------------------------------------------------- #
import lectura_tolerante_juez as LT                          # noqa: E402  (HEAD, sin editar)


def por_nombre(n: str) -> bool:
    return "_SOLO_MESA" in n or n.startswith("NO_ABRIR_")


def foto_de_la_copia() -> dict:
    """Los archivos de la copia del repo, por su ruta, su tamaño y su fecha (sin leerlos; una carpeta *_SOLO_MESA* o NO_ABRIR_*, solo
    por su nombre)."""
    out = {}
    for d, subs, nombres in os.walk(K.REPO_DIR, followlinks=False):
        out.update({os.path.relpath(os.path.join(d, s), K.REPO_DIR): "carpeta por nombre" for s in subs if por_nombre(s)})
        subs[:] = [s for s in subs if s != "__pycache__" and not por_nombre(s)]
        for n in nombres:
            st = os.lstat(os.path.join(d, n))
            out[os.path.relpath(os.path.join(d, n), K.REPO_DIR)] = (st.st_size, st.st_mtime_ns)
    return out


@caso("la configuración de agentes de B6.4: sus sha256 dan (la lista del 241 y HEAD); la rearmada es la del archivo; sus cuatro brazos, kg_n7 igual al kg_N7 de B2; con otro sha256 esperado, frena; y una entrada armada con armar_entrada_B64.py sobre ella pasa los controles del runner")
def _():
    cfg, controles, resumen = AC.armar()
    igual = (AQUI / "config_agentes_b64.json").read_text(encoding="utf-8") == json.dumps(cfg, ensure_ascii=False, indent=1) + "\n"
    viejo = dict(AC.SHA256_HEAD)
    AC.SHA256_HEAD["n7/bloque_tools_kg_n7.txt"] = "0" * 64
    try:
        AC.armar()
        frena_otro = False
    except AC.Freno:
        frena_otro = True
    finally:
        AC.SHA256_HEAD.clear()
        AC.SHA256_HEAD.update(viejo)
    aprob, sha = H.aprobadas_de_juguete(TMP / "config_aprobadas" / "aprobadas.json")
    sal = TMP / "config_entrada" / "entrada_B64.json"
    with contextlib.redirect_stdout(io.StringIO()):          # su consola trae la ruta de la carpeta temporal: no se imprime
        rc = AE.main(["--preguntas", str(aprob), "--sha256-preguntas", sha, "--salida", str(sal)])
    os.environ["NEO4J_URI"] = "bolt://127.0.0.1:47687"
    e, preg, reg = R.controles(sal, H.sha(sal), "init")
    r5 = (cfg["corte_R5"]["tope_tool_calls_en_prompt"], cfg["corte_R5"]["max_turns"], cfg["corte_R5"]["max_budget_usd_por_sesion"])
    ok = (all(c["ok"] for c in controles) and resumen["de_la_lista_del_241"] >= 7 and igual and frena_otro and r5 == (30, 32, 1.8)
          and sorted(cfg["brazos"]) == sorted(AE.ROLES) and resumen["kg_n7_igual_al_kg_N7_de_B2"]
          and resumen["kg_difiere_del_kg_de_B63_solo_en"] == ["archivos_servidor", "config_servidor", "mcp_config"]
          and rc == 0 and len(preg) == 96 and reg["brazos"] == sorted(AE.ROLES) and sorted(e["brazos"]) == sorted(cfg["brazos"]))
    return ok, (f"{resumen['controles']} sha256 ({resumen['de_la_lista_del_241']} de la lista del 241, {resumen['de_HEAD']} de HEAD); "
                f"brazos {sorted(cfg['brazos'])}; R5 {r5}; la entrada armada: {len(preg)} preguntas")


@caso("el armador de la entrada: sus constantes son las del runner y del juez (el id admitido, la forma de cita del grafo, el esquema y los roles)")
def _():
    cfg = json.loads((AQUI / "config_agentes_b64.json").read_text(encoding="utf-8"))
    ok = (AE.ID_VALIDO.pattern == K.ID_VALIDO.pattern and AE.MARCAS_D10_KG_N7 == list(JB.CITAS_POR_ROL["grafo"])
          and AE.ESQUEMA == H.ESQUEMA_B64 and set(AE.ESQUEMA) == set(K.ESQUEMA_EV2) and sorted(AE.ROLES.values()) == sorted(K.ROLES)
          and set(AE.ROLES) == set(cfg["brazos"]) and AE.MARCAS_D10_KG_N7 == H.MARCAS_D10_GRAFO and AE.K == 3
          and (AE.TOPE_USD, AE.FRENO_USD) == (144.0, 115.0))
    return ok, None


@caso("el juez fuera del repo: su directorio por defecto está fuera del repo y de git, al lado de las salidas (fuera_del_repo/banco_b64/); con él (la misma forma, en una carpeta de prueba), una corrida de juguete no escribe nada en el repo")
def _():
    real = K.JUEZ_DIR.resolve()
    fuera = (not real.is_relative_to(K.REPO_DIR.resolve()) and real.is_relative_to(K.FUERA_DEL_REPO.resolve())
             and real.parent == K.RESULTADOS.resolve().parent and real.parent.name == "banco_b64"
             and LOTE.LA.dentro_de_git(real.parent.parent) is None)
    raiz = TMP / "fuera_del_repo_de_prueba"

    def f():
        antes = foto_de_la_copia()
        c = corrida("juez_por_defecto", ["VEN01"], out=raiz / "banco_b64" / "resultados" / "real", juez_dir=raiz / "banco_b64" / "juez")
        cod = c.correr()
        despues = foto_de_la_copia()
        escritos = [p for p in (raiz / "banco_b64" / "juez").rglob("*.jsonl")]
        return cod == 0 and antes == despues and len(escritos) == 3, cod, len(escritos)
    ok, cod, n = con_ventana(f)
    return fuera and ok, f"el por defecto, fuera: {fuera}; la corrida: código {cod}, {n} archivos de veredictos fuera; el repo, igual"


@caso("el juez fuera del repo: con un --juez-dir dentro del repo, el modo real frena con el 10 antes de lanzar o escribir nada")
def _():
    def f():
        dentro = K.AQUI / "juez_de_prueba_b64"
        c = corrida("juez_en_el_repo", ["VEN01"], juez_dir=dentro)
        cod = frena(c.correr)
        return cod == K.PRECONDICION and not dentro.exists() and not c.out.exists(), cod
    ok, cod = con_ventana(f)
    return ok, f"código {cod}"


@caso("la decisión 3 de B6.4: con --sesiones o --lotes dentro del repo, el modo real frena con el 10 antes de escribir nada (en B6.3 el runner escribía el lote de la pasada antes de que el lote frenara); y con --solo-controles y --out en el repo, también")
def _():
    def f():
        obs = {}
        for que in ("sesiones", "lotes"):
            dentro = K.AQUI / f"{que}_de_prueba_b64"
            c = corrida(f"{que}_en_el_repo", ["VEN01"], **{que: dentro})
            obs[que] = (frena(c.correr), dentro.exists() or c.out.exists())
        ent, s = entrada("solo_controles_en_el_repo", ["VEN01"])
        dentro = K.AQUI / "out_de_prueba_b64_solo_controles"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):                 # la consola del runner trae rutas: no se imprime
            cod = R.main(["--entrada", str(ent), "--sha256-entrada", s, "--modo", "real", "--solo-controles", "--out", str(dentro),
                          "--sesiones", str(TMP / "solo_controles_ses"), "--juez-dir", str(TMP / "solo_controles_juez"),
                          "--patron-de-prueba", TOKEN])
        obs["solo_controles_out"] = (cod if "(decisión 3): --out" in buf.getvalue() else None, dentro.exists())
        return all(v == (K.PRECONDICION, False) for v in obs.values()), obs
    ok, obs = con_ventana(f)
    return ok, f"{ {k: v[0] for k, v in obs.items()} }"


@caso("el manifiesto sin texto de lo que queda fuera: cada archivo del juez y de las salidas con su sha256, la tabla *_SOLO_MESA* solo por su nombre, y ninguna ventana de 30 caracteres de la pregunta, el criterio o la respuesta de juguete; el control positivo, en los archivos mismos")
def _():
    raiz = TMP / "fuera_del_repo_manifiesto"
    pedidos: list = []

    def f():
        c = corrida("manifiesto", ["MET01"], preguntas=PREG_META, out=raiz / "banco_b64" / "resultados" / "real",
                    juez_dir=raiz / "banco_b64" / "juez", factory=H.juez_simulado(raiz / "banco_b64" / "juez" / "cache", pedidos))
        return c, c.correr()
    c, cod = con_ventana(f, lanzador=K.LANZADOR_SESION, cli=bin_claude_falso("bin_manifiesto"))
    m = R.manifiesto_fuera([c.out, c.juez_dir], raiz=raiz)
    texto = json.dumps(m, ensure_ascii=False)
    por_ruta = {x["ruta"]: x for x in m["archivos"]}
    juez = [p for p in c.juez_dir.rglob("*") if p.is_file() and not any("_SOLO_MESA" in q for q in p.relative_to(raiz).parts)]
    sha_bien = all(por_ruta.get(str(p.relative_to(raiz)), {}).get("sha256") == H.sha(p) for p in juez)
    solo_mesa = [x for x in m["carpetas_por_nombre"] if "_SOLO_MESA" in x]
    pr = json.loads(PREG_META.read_text(encoding="utf-8"))["preguntas"][0]
    s0 = c.estado["sesiones"][0]
    meta = json.loads((c.out / f"pasada{s0['pasada']}" / s0["id"] / f"meta_{s0['id']}.json").read_text(encoding="utf-8"))
    fuentes = {"pregunta": pr["pregunta"], "criterio": pr["criterios"][0]["criterio"], "respuesta": meta["final_json_R4"]["respuesta"]}
    en_manifiesto = {k: sum(w in texto for w in H.ventanas(v)) for k, v in fuentes.items()}
    crudo = "".join(p.read_bytes().decode("utf-8", errors="ignore") for p in list(c.juez_dir.rglob("*.db")) + list(c.out.rglob("meta_*.json")))
    en_archivos = {k: sum(w in crudo for w in H.ventanas(v)) > 0 for k, v in fuentes.items()}
    return (cod == 0 and len(juez) >= 6 and sha_bien and len(solo_mesa) == 1 and not any(en_manifiesto.values())
            and all(en_archivos.values())), \
        (f"{m['n_archivos']} archivos en el manifiesto ({len(juez)} del juez, con su sha256); carpetas por nombre: {len(solo_mesa)}; "
         f"ventanas en el manifiesto: {en_manifiesto}; en los archivos: {en_archivos}")


@caso("la salida del juez que no se lee: queda en errores_r{rep}.jsonl con su id opaco y su repetición y no se reintenta; su salida cruda está en la caché, que se abre en solo lectura y se encuentra por la clave del pedido; la lectura tolerante de HEAD da un veredicto por criterio, sin escribir ninguno en las salidas del juez")
def _():
    d = TMP / "juez_que_no_se_lee"
    pedidos: list = []
    preg = {"Q1": {"pregunta": "Pregunta de juguete de la salida que no se lee",
                   "criterios": [{"criterio": f"criterio {i}", "cita_textual": f"cita {i}"} for i in (1, 2, 3)]}}
    c = JB.caso_ciego("Q1", "kg_n7", 1, f"Respuesta de juguete {H.MARCA_COMILLAS} de la salida que no se lee.", preg)
    tres = JB.TresJueces(H.juez_simulado(d / "cache", pedidos), d, d / "cache")
    try:
        r1 = tres.juzgar(c, 0.0, 10.0, 12.0)
        n1 = len(pedidos)
        r2 = tres.juzgar(c, 0.0, 10.0, 12.0)
    finally:
        tres.cerrar()
    errores = {rep: JB.leer(d / f"errores_r{rep}.jsonl") for rep in JB.REPS}
    registrada = all(len(v) == 1 and v[0]["id_opaco"] == c["id_opaco"] and v[0]["rep"] == rep for rep, v in errores.items())
    sin_veredicto = all(not JB.leer(d / f"veredictos_r{rep}.jsonl") for rep in JB.REPS)
    kw = J.construir_kwargs(c["pregunta"], c["respuesta"], c["criterios"])
    lecturas, solo_lectura = {}, True
    for rep in JB.REPS:
        ns = J.lc.make_namespace(f"juez_ev2_r{rep}", code_ver=J.CODE_VER, thinking=False)
        clave = J.lc.compute_key(ns, J.lc.canonical_request(kw))
        con = sqlite3.connect(f"file:{JB.db_path(rep, d / 'cache')}?mode=ro", uri=True)
        try:
            fila = con.execute("SELECT raw_json, stop_reason FROM cache WHERE key = ?", (clave,)).fetchone()
            try:
                con.execute("UPDATE cache SET stop_reason = stop_reason WHERE key = ?", (clave,))
                solo_lectura = False
            except sqlite3.OperationalError:
                pass
        finally:
            con.close()
        texto = "".join(b["text"] for b in json.loads(fila[0])["content"] if b.get("type") == "text")
        estricta = True
        try:
            J.parsear_veredicto(texto, len(c["criterios"]))
        except ValueError:
            estricta = False
        tol = LT.leer(texto, len(c["criterios"]))
        lecturas[rep] = {"stop_reason": fila[1], "aplica": LT.aplica(texto, fila[1]), "estricta_la_lee": estricta,
                         "veredictos": [x["veredicto"] for x in tol["criterios"]]}
    todas = all(x["aplica"] and not x["estricta_la_lee"] and x["stop_reason"] == "end_turn"
                and x["veredictos"] == ["cumplido", "cumplido", "no_cumplido"] for x in lecturas.values())
    sigue_sin = all(not JB.leer(d / f"veredictos_r{rep}.jsonl") for rep in JB.REPS)
    return (r1["errores"] == 3 and registrada and sin_veredicto and n1 == 3 and len(pedidos) == 3 and r2.get("ya_estaba")
            and solo_lectura and todas and sigue_sin), \
        (f"{r1['errores']} errores registrados (uno por repetición), {len(pedidos)} pedidos y ninguno al reintentar; en la caché, por la "
         f"clave y en solo lectura: {len(lecturas)}; la lectura tolerante: {lecturas[1]['veredictos']}")


@caso("ningún subproceso de Python con un guion del patrón de la b1 bis (la noción de la guarda) ni ningún pgrep con él: solo el token propio")
def _():
    con = [l for l in LINEAS if (g := G.script_python(" ".join(l))) and re.search(R.PATRON_B1, g.rsplit("/", 1)[-1])]
    pg = [l for l in LINEAS if l and Path(l[0]).name == "pgrep"]
    sh = [l for l in LINEAS if l and l[0] == "/bin/sh"]
    guiones = sorted({Path(x).name for l in LINEAS if l and Path(l[0]).name not in ("pgrep", "sh") for x in l if x.endswith(".py")})
    return (not con and pg and all(l[-1] == LOTE.patron_de_prueba(TOKEN) for l in pg) and len(sh) == len(R.NOMBRES_B1BIS)), \
        (f"{len(LINEAS)} líneas, {len(pg)} pgrep con el token, {len(sh)} procesos /bin/sh con un nombre de la b1 bis, guiones de "
         f"Python lanzados: {guiones}")


def main() -> int:
    for ok, t in RES:
        print(("PASS " if ok else "FAIL ") + t)
    n = sum(ok for ok, _ in RES)
    print(f"selftest B6.4: {n} de {len(RES)} en PASS")
    return 0 if n == len(RES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
