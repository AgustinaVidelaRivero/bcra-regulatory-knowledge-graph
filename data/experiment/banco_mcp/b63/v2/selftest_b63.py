#!/usr/bin/env python3
"""selftest_b63.py (v2, etapa b1) — El selftest de la etapa b1 del runner de B6.3 (USD 0, sin datos reales, sin Neo4j, sin Docker y
sin ningún subproceso con un script del patrón de otro paso pago: importa el runner, no lo corre). Las ramas nuevas:
  los dos R5 y uno que no es; el pip freeze --all; el patrón con los dos nombres nuevos y su patrón de prueba; las formas reales y su
  clase; la ventana corrida (P = 1 y P = 2), los reintentos en el primer lugar libre y el tope de tres intentos; la opción (d) y su
  freno; el Neo4j de B6.3 (NEO4J_URI y la huella, con un doble); la memoria (la copia de memoria_maquina, la regla de la P y la guarda,
  con un vm_stat falso) y el control de Docker (con un docker falso), también como ganchos de la ventana; el juez de a tres (igual que
  de a una, y sin cruces entre las tres bases); y la atribución (el stream y el log R1 de una sesión, con el CLI falso).
Todo sobre datos de juguete, en una carpeta temporal dentro de SELFTEST_B63_TMP (obligatoria: nada en la carpeta temporal del
sistema). Lo que imprime no trae horas ni rutas: dos corridas dan lo mismo.
Uso: SELFTEST_B63_TMP=<carpeta> <python del .venv del repo> -B data/experiment/banco_mcp/b63/v2/selftest_b63.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import correr_b63 as R                                       # noqa: E402  (el runner v2, de esta misma carpeta: se importa)
from seco import herramientas_b1 as H                        # noqa: E402

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
if not os.environ.get("SELFTEST_B63_TMP"):
    raise SystemExit("falta SELFTEST_B63_TMP (la carpeta de trabajo del selftest; nada en la carpeta temporal del sistema)")
TMP = Path(tempfile.mkdtemp(prefix="selftest_b63_b1_", dir=os.environ["SELFTEST_B63_TMP"]))
RES: list[tuple[bool, str]] = []
PATH0 = os.environ.get("PATH", "")
TOKEN = "prueba_b1_zq7xk2m4"


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


# --------------------------------------------------------------------------------------------------------------------- #
@caso("R5: la entrada con el A (32, 30 y 1,80) y con el B (47, 45 y 3,30, con su configuración) pasan; con otro frena")
def _():
    a = K.cargar_entrada(*H.entrada_v2(TMP, "r5a", ["JUG01"]))
    b = K.cargar_entrada(*H.entrada_v2(TMP, "r5b", ["JUG01"], r5="B"))
    otro = frena(K.cargar_entrada, *H.entrada_v2(TMP, "r5c", ["JUG01"], mutar=lambda e: e["R5"].update(max_turns=40)))
    return a["R5"]["max_turns"] == 32 and b["R5"]["max_turns"] == 47 and otro == K.PRECONDICION, None


@caso("R5 en el lote: con un R5 que no es uno de los admitidos, la ventana frena con el 5 sin lanzar ninguna sesión")
def _():
    e = {"R5": {"max_turns": 40, "tope_tool_calls_prompt": 30, "max_budget_usd": 1.8}}
    p = TMP / "entrada_r5_no_admitido.json"
    p.write_text(json.dumps(e), encoding="utf-8")
    lote = TMP / "lote_r5_no_admitido.json"
    lote.write_text(json.dumps({"sesiones": [{"id": "X-kg", "brazo": "kg", "pregunta": "p"}]}), encoding="utf-8")
    from argparse import Namespace
    a = Namespace(lote=lote, out=TMP / "r5_no_admitido", sesiones=TMP / "ses_r5", paralelo=1, modo="real", via="api", tope=10, freno=5,
                  presupuesto_sesion=None, lanzador="b63/v2/seco/lanzador_falso_ventana.py", timeout_s=60,
                  config_agentes="b63/seco/config_agentes_b63_juguete.json", entrada=p, sha256_entrada=H.sha(p))
    L = V.LoteVentana(a)
    return L.correr() == LOTE.AISLAMIENTO and all(s["estado"] == "no lanzada" for s in L.sesiones), None


@caso("pip freeze --all: el de la entrada (24f4c064…) pasa; otro sha256 frena; la entrada sin él frena")
def _():
    ok = K.cargar_entrada(*H.entrada_v2(TMP, "pf_ok", ["JUG01"]))
    mal = frena(K.cargar_entrada, *H.entrada_v2(TMP, "pf_mal", ["JUG01"],
                                                 mutar=lambda e: e["banco_venv_vector"].update(pip_freeze_sha256="0" * 64)))
    sin = frena(K.cargar_entrada, *H.entrada_v2(TMP, "pf_sin", ["JUG01"], mutar=lambda e: e["banco_venv_vector"].pop("pip_freeze_sha256")))
    return (ok["banco_venv_vector"]["pip_freeze_sha256"] == H.PIP_FREEZE_SELLADO and mal == K.PRECONDICION and sin == K.PRECONDICION), None


@caso("la entrada: P 1 o 2 (3 frena), pico mayor que 0, y el Neo4j con bolt://127.0.0.1:47687 y una huella de 64 hexadecimales")
def _():
    malas = {"P3": dict(P=3), "pico0": dict(pico=0), "uri": dict(mutar=lambda e: e["neo4j"].update(uri="bolt://127.0.0.1:7687")),
             "huella": dict(mutar=lambda e: e["neo4j"].update(huella_contenido="x")), "sin_neo4j": dict(mutar=lambda e: e.pop("neo4j"))}
    r = {n: frena(K.cargar_entrada, *H.entrada_v2(TMP, f"e_{n}", ["JUG01"], **kw)) for n, kw in malas.items()}
    p2 = K.cargar_entrada(*H.entrada_v2(TMP, "e_p2", ["JUG01"], P=2))
    return all(v == K.PRECONDICION for v in r.values()) and p2["P"] == 2, f"frenan {sum(1 for v in r.values() if v)} de {len(r)}"


@caso("el patrón: el real de guardas_lote_r5 más lanzar_lote_paralelo_r5.py y correr_n6.py; el real solo no los ve; el de prueba, un token propio")
def _():
    p = R.control_patron()
    ve = all(re.search(R.PATRON_B1, n) for n in ("lanzar_lote_paralelo_r5.py", "correr_n6.py", "correr_b63.py"))
    no_ve = not any(re.search(R.PATRON_REAL, n) for n in ("lanzar_lote_paralelo_r5.py", "correr_n6.py"))
    viejo = LOTE.cli_del_path
    try:
        LOTE.cli_del_path = lambda: {"version": "2.1.241 (Claude Code)"}
        real = frena(R.fijar_patron_de_prueba, "prueba_b1_selftest1")
    finally:
        LOTE.cli_del_path = viejo
    return (all(p.values()) and ve and no_ve and real == K.PRECONDICION and G.PATRON_PAGO_REAL == R.PATRON_REAL), None


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
        ev.append({"type": "result", "subtype": f["subtype"], "is_error": f["is_error"]})
    return "".join(json.dumps(x) + "\n" for x in ev)


@caso("las formas reales: cada una de formas_reales_b63.json da su clase en el clasificador; una forma nueva, desconocida")
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
    """Una corrida del runner v2 con la ventana y el lanzador falso, el juez falso y los dobles de memoria, Docker y Neo4j."""
    ent, s = H.entrada_v2(TMP, nombre, ids, preguntas=AQUI / "seco" / "preguntas_ventana_b63.json", P=kw.pop("P", 1),
                          freno=kw.pop("freno", 40.0), tope=kw.pop("tope", 50.0))
    e = K.cargar_entrada(ent, s)
    preg = K.cargar_preguntas(e)
    base = TMP / nombre
    c = R.CorridaB63(e, preg, modo="real", out=base / "out", sesiones=base / "ses", juez_dir=base / "juez", lotes=base / "lotes",
                     client_factory=kw.pop("factory", None) or (lambda rep, label: H.ClienteJuez()),
                     medir_memoria=kw.pop("medir", lambda: {"en_uso_gb": 5.0, "swap_usado_gb": 0.1}),
                     control_docker=kw.pop("docker", lambda m=None: {"evento": "control de Docker", "ok": True, "motivo": None}),
                     control_neo4j=kw.pop("neo4j", lambda: {"ok": True, "motivo": None}))
    return c


def con_ventana(f):
    """Corre f con el lanzador falso de la ventana como lanzador de la sesión, el CLI falso en el PATH y el patrón de prueba."""
    viejo = K.LANZADOR_SESION
    con_path(H.bin_falso(TMP, "bin_ventana"))
    os.environ["NEO4J_URI"] = "bolt://127.0.0.1:47687"
    try:
        R.fijar_patron_de_prueba(TOKEN)
        K.LANZADOR_SESION = "b63/v2/seco/lanzador_falso_ventana.py"
        return f()
    finally:
        K.LANZADOR_SESION = viejo
        os.environ["PATH"] = PATH0


def lanzados(c: R.CorridaB63) -> list[str]:
    out = []
    for n in range(1, c.estado["pasadas"] + 1):
        reg = json.loads((c.out / f"pasada{n}" / "registro_lote.json").read_text(encoding="utf-8"))
        out += [e["id"] for e in reg["eventos"] if e["evento"] == "lanza"]
    return out


@caso("la ventana con P = 1: en el orden firmado, y cada reintento en el primer lugar libre (enseguida de su falla)")
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
        return (cod == 0 and ids == esperado and all(v == "completa" for st in fin.values() for v in st.values())
                and len(JB.leer_tabla(c.juez_dir)["filas"]) == 9), f"{len(ids)} sesiones lanzadas, {c.estado['pasadas']} pasada"
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
        return cod == 0 and maximo == 2 and ok_frente and n_ins == 3, f"máximo a la vez {maximo}; {n_ins} reintentos insertados"
    return con_ventana(f)


@caso("los reintentos: hasta 3 intentos por brazo; con la falla en los tres, falla_infra_sin_terminar y ningún cuarto")
def _():
    def f():
        c = corrida("infra3", ["VEN07"])
        cod = c.correr()
        st = c.estado["bloques"]["VEN07-r1"]
        return (cod == 0 and all(v["clasificacion"] == "falla_infra_sin_terminar" for v in st["final"].values())
                and all(n == 3 for n in st["intentos_por_brazo"].values()) and len(lanzados(c)) == 9), None
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
            and not JB.leer_tabla(c.juez_dir)["filas"]
        pedidos = []
        g = corrida("gasto", ["VEN01"], freno=1.85, tope=2.0, factory=H.juez_simulado(TMP / "gasto" / "juez" / "cache", pedidos))
        codg = g.correr()
        return (corte and codg == 2 and len(lanzados(g)) == 2 and len(pedidos) == 6), \
            f"lanza 2 (1,8 más lo del juez, 0,0288 por respuesta) y frena antes de la tercera"
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


@caso("el juez de a tres: da lo mismo que de a una con un cliente falso, y con la caché real cada base tiene solo su namespace")
def _():
    preg = {"Q1": {"pregunta": "p", "criterios": [{"criterio": "c1", "cita_textual": "t1"}, {"criterio": "c2", "cita_textual": "t2"}]}}
    casos = [JB.caso_ciego("Q1", b, 1, f"respuesta de juguete {b}", preg) for b in ("kg", "fragmentos_bm25")]
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
    return (igual and all(x["lanzadas"] == [1, 2, 3] for x in r) and sin_cruces and len(pedidos) == 6), \
        f"{len(pedidos)} pedidos al transporte; una base y un namespace por repetición"


@caso("el juez de a tres y la guarda: con el gasto al borde, lanza las que entran, espera las que están en vuelo y corta antes del freno")
def _():
    d = TMP / "juez_guarda3"
    preg = {"Q1": {"pregunta": "p", "criterios": [{"criterio": "c1", "cita_textual": "t1"}]}}
    c = JB.caso_ciego("Q1", "kg", 1, "respuesta", preg)
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


@caso("la atribución: una sesión con el CLI falso deja el stream y el log R1 en su carpeta; la meta trae la ruta y el sha256 del log R1")
def _():
    bin_ = AQUI.parent / "seco"
    falso = TMP / "bin_atrib"
    falso.mkdir(parents=True, exist_ok=True)
    (falso / "claude").write_text(f'#!/bin/sh\nexec "{sys.executable}" -B "{bin_ / "claude_falso_b63.py"}" "$@"\n', encoding="utf-8")
    (falso / "claude").chmod(0o755)
    cfg = K.B63 / "seco" / "config_agentes_b63_juguete.json"
    out = TMP / "atrib" / "B63-JUG01-r1-kg"
    env = {"PATH": f"{falso}:{PATH0}", "HOME": os.environ["HOME"], "ANTHROPIC_API_KEY": "sin-clave-selftest-b1",
           "BANCO_VENV_VECTOR": str(K.ruta_de_rel(H.VENV_VECTOR)), "B63_CONFIG_AGENTES": str(cfg), "B63_CONFIG_AGENTES_SHA256": H.sha(cfg),
           "B63_VENV_PYTHON": "3.12"}
    argv = [sys.executable, "-B", str(AQUI / "lanzar_agente_b63.py"), "--brazo", "kg", "--id", out.name, "--pregunta",
            "Pregunta de juguete de la atribución [[b63:normal]]", "--out", str(out), "--modo", "real", "--sesiones", str(TMP / "atrib_ses")]
    LINEAS.append(argv)
    r = subprocess.run(argv, env=env, capture_output=True, text=True)
    m = json.loads((out / f"meta_{out.name}.json").read_text(encoding="utf-8"))
    st, lg = out / f"stream_{out.name}.jsonl", out / f"log_r1_{out.name}.jsonl"
    log_en_meta = m["log_r1"].get("sha256") == H.sha(lg) and m["log_r1"]["ruta"].endswith(lg.name)
    stream_en_meta = any(isinstance(v, dict) and str(v.get("ruta", "")).endswith(st.name) for v in m.values())
    return (r.returncode == 0 and st.is_file() and lg.is_file() and log_en_meta), \
        f"stream en su carpeta: sí; log R1 en su carpeta: sí; en la meta, log R1 (ruta y sha256): sí; stream: {'sí' if stream_en_meta else 'no, falta'}"


@caso("las formas reales con el CLI falso v2: cada plan `forma_real` deja una sesión que el runner clasifica con la clase medida")
def _():
    falso = TMP / "bin_formas_v2"
    falso.mkdir(parents=True, exist_ok=True)
    (falso / "claude").write_text(f'#!/bin/sh\nexec "{sys.executable}" -B "{AQUI / "seco" / "claude_falso_b63.py"}" "$@"\n',
                                  encoding="utf-8")
    (falso / "claude").chmod(0o755)
    cfg = K.B63 / "seco" / "config_agentes_b63_juguete.json"
    env = {"PATH": f"{falso}:{PATH0}", "HOME": os.environ["HOME"], "ANTHROPIC_API_KEY": "sin-clave-selftest-b1",
           "BANCO_VENV_VECTOR": str(K.ruta_de_rel(H.VENV_VECTOR)), "B63_CONFIG_AGENTES": str(cfg), "B63_CONFIG_AGENTES_SHA256": H.sha(cfg),
           "B63_VENV_PYTHON": "3.12"}
    infra, obs = R.formas_de_infraestructura(), {}
    for f in FORMAS:
        out = TMP / "formas_cli" / f["caso"] / "B63-FOR01-r1-kg"
        argv = [sys.executable, "-B", str(AQUI / "lanzar_agente_b63.py"), "--brazo", "kg", "--id", out.name, "--pregunta",
                f"Pregunta de juguete de las formas [[b63:real_{f['caso']}]]", "--out", str(out), "--modo", "real",
                "--sesiones", str(TMP / "formas_cli_ses" / f["caso"])]
        LINEAS.append(argv)
        subprocess.run(argv, env=env, capture_output=True, text=True)
        clase, forma = R.clasificar({"id": out.name, "estado": "terminada"}, out.parent, "real", 1800.0, infra)
        obs[f["caso"]] = (clase == f["clase"] and forma["subtype"] == f["subtype"] and forma["is_error"] == f["is_error"]
                          and forma["api_retry_error_status"] == f["api_retry_error_status"], clase)
    return all(v[0] for v in obs.values()), ", ".join(f"{k}: {v[1]}" for k, v in obs.items())


@caso("ningún subproceso con un script del patrón (el de b1) ni ningún pgrep con él: solo el token propio")
def _():
    con = [l for l in LINEAS if re.search(R.PATRON_B1, " ".join(l))]
    pg = [l for l in LINEAS if l and Path(l[0]).name == "pgrep"]
    guiones = sorted({Path(x).name for l in LINEAS if l and Path(l[0]).name != "pgrep" for x in l if x.endswith(".py")})
    return (not con and pg and all(l[-1] == LOTE.patron_de_prueba(TOKEN) for l in pg)), \
        f"{len(LINEAS)} líneas, {len(pg)} pgrep con el token, guiones lanzados: {guiones}"


def main() -> int:
    for ok, t in RES:
        print(("PASS " if ok else "FAIL ") + t)
    n = sum(ok for ok, _ in RES)
    print(f"selftest B6.3-b1: {n} de {len(RES)} en PASS")
    return 0 if n == len(RES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
