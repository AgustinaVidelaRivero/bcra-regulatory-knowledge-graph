#!/usr/bin/env python3
"""selftest_b63.py — El selftest de las funciones del runner de B6.3 que no lanzan sesiones (USD 0, sin datos reales): el orden, los
ids, la cuenta por fecha, la clasificación de una sesión, la entrada sellada y sus frenos, las preguntas, D-10, el id opaco, el pedido
del juez sin el brazo, la guarda del juez, la salida mal formada, el patrón de las guardas, la lectura del testigo, el enmascarado, la
agregación y el lanzador de una sesión. Todo sobre datos de juguete en una carpeta temporal.

Uso: [SELFTEST_B63_TMP=<carpeta>] <python del .venv del repo> -B data/experiment/banco_mcp/b63/selftest_b63.py
(SELFTEST_B63_TMP: dónde va su carpeta temporal; si no, la del sistema.)
"""
from __future__ import annotations

import json
import os
import random
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import correr_b63 as R                                       # noqa: E402  (el runner, de esta misma carpeta)
from seco import herramientas_seco as H                      # noqa: E402
import enmascarar_cwd_b63 as EN                              # noqa: E402

K, JB, LOTE, G = R.K, R.JB, R.LOTE, R.G
J, M = sys.modules["juez"], sys.modules["mapping"]
RES: list[tuple[bool, str]] = []
TMP = Path(tempfile.mkdtemp(prefix="selftest_b63_", dir=os.environ.get("SELFTEST_B63_TMP") or None))


def caso(nombre: str):
    def deco(f):
        try:
            ok, detalle = f()
        except Exception as ex:                              # un caso que levanta, falla con su tipo
            ok, detalle = False, f"{type(ex).__name__}: {str(ex)[:160]}"
        RES.append((bool(ok), f"{nombre}" + (f" — {detalle}" if detalle else "")))
        return f
    return deco


def frena(f, *a, **kw) -> str | None:
    try:
        f(*a, **kw)
    except K.FrenoB63 as ex:
        return str(ex)
    except SystemExit as ex:
        return str(ex)
    return None


BRAZOS = ["kg", "fragmentos_bm25", "fragmentos_denso"]


@caso("orden: determinista, con random.Random(f'B63:orden_corridas:v1:{id}:{r}').shuffle sobre los brazos ordenados, por pregunta y repetición")
def _():
    o = K.orden_bloques(["Q1", "Q2"], 3, BRAZOS)
    man = []
    for q in ("Q1", "Q2"):
        for r in (1, 2, 3):
            xs = sorted(BRAZOS)
            random.Random(f"B63:orden_corridas:v1:{q}:{r}").shuffle(xs)
            man.append(xs)
    return (o == K.orden_bloques(["Q1", "Q2"], 3, list(reversed(BRAZOS))) and [b["brazos"] for b in o] == man
            and [(b["qid"], b["r"]) for b in o] == [("Q1", 1), ("Q1", 2), ("Q1", 3), ("Q2", 1), ("Q2", 2), ("Q2", 3)]
            and all(sorted(b["brazos"]) == sorted(BRAZOS) for b in o)), f"{len(o)} bloques"


@caso("ids: terminan con el brazo; los reintentos llevan -i2 y -i3; todos los admite el lanzador del lote")
def _():
    xs = [K.id_sesion("B63-O1-L06-R2", 1, "kg"), K.id_sesion("Q1", 2, "fragmentos_denso", 2), K.id_sesion("Q1", 2, "kg", 3)]
    return (xs == ["B63-B63-O1-L06-R2-r1-kg", "B63-Q1-r2-fragmentos_denso-i2", "B63-Q1-r2-kg-i3"]
            and all(LOTE.ID_VALIDO.match(x) for x in xs)), None


@caso("fechas: la cuenta por brazo y por fecha, con los reintentos, y el bloque con dos fechas")
def _():
    s = [{"bloque": "Q1-r1", "brazo": "kg", "fecha": "2026-10-26"}, {"bloque": "Q1-r1", "brazo": "fragmentos_bm25", "fecha": "2026-10-26"},
         {"bloque": "Q1-r1", "brazo": "fragmentos_denso", "fecha": "2026-10-27"}, {"bloque": "Q2-r1", "brazo": "kg", "fecha": "2026-10-27"},
         {"bloque": "Q2-r1", "brazo": "kg", "fecha": "2026-10-27", "intento": 2}, {"bloque": "Q2-r1", "brazo": "fragmentos_bm25", "fecha": None}]
    c = K.cuenta_fechas(s)
    return (c["por_brazo_y_fecha"] == {"fragmentos_bm25": {"2026-10-26": 1}, "fragmentos_denso": {"2026-10-27": 1},
                                      "kg": {"2026-10-26": 1, "2026-10-27": 2}}
            and [x["bloque"] for x in c["bloques_con_fechas_distintas"]] == ["Q1-r1"] and c["n_sesiones"] == 5), None


def sesion_falsa(nombre: str, meta: dict | None, result: dict | None) -> Path:
    d = TMP / "clasificar" / nombre / "S"
    d.mkdir(parents=True, exist_ok=True)
    if meta is not None:
        (d / "meta_S.json").write_text(json.dumps(meta), encoding="utf-8")
    lineas = [json.dumps({"type": "system", "subtype": "init"})] + ([json.dumps(result)] if result else [])
    (d / "stream_S.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return d.parent


@caso("clasificación: completa, cortada (turnos y presupuesto), falla de infraestructura (sin result o is_error), otra, timeout, no lanzada e init")
def _():
    inc = {"completitud_R3": {"completa": False}, "duracion_s": 10}
    casos = {"completa": ({"completitud_R3": {"completa": True}}, {"type": "result", "subtype": "success"}),
             "turnos": (inc, {"type": "result", "subtype": "error_max_turns", "is_error": True}),
             "presupuesto": (inc, {"type": "result", "subtype": "error_max_budget_usd", "is_error": True}),
             "sin_result": (inc, None), "is_error": (inc, {"type": "result", "subtype": "error_during_execution", "is_error": True}),
             "success_incompleta": (inc, {"type": "result", "subtype": "success", "is_error": False}),
             "timeout": ({"completitud_R3": {"completa": False}, "duracion_s": 1800}, None), "sin_meta": (None, None)}
    obs = {k: R.clasificar({"id": "S", "estado": "terminada"}, sesion_falsa(k, m, r), "real", 1800.0) for k, (m, r) in casos.items()}
    esp = {"completa": "completa", "turnos": "cortada", "presupuesto": "cortada", "sin_result": "falla_infra", "is_error": "falla_infra",
           "success_incompleta": "incompleta_otra", "timeout": "incompleta_otra", "sin_meta": "incompleta_otra"}
    otros = (R.clasificar({"id": "S", "estado": "no lanzada"}, TMP, "real", 1800.0) == "no_lanzada"
             and R.clasificar({"id": "S", "estado": "terminada"}, TMP, "init", 1800.0) == "init")
    return obs == esp and otros, None


@caso("entrada: la de juguete pasa; frena con otro sha256 del comando, de config_agentes, de un config_servidor o de las preguntas")
def _():
    ent, s = H.entrada_de_juguete(TMP, "ok", ["JUG01"])
    e = K.cargar_entrada(ent, s)
    malas = {"comando": frena(K.cargar_entrada, ent, "0" * 64)}
    for n, mut in (("config", lambda e: e["config_agentes"].update(sha256="0" * 64)),
                   ("servidor", lambda e: e["brazos"]["kg"]["config_servidor"].update(sha256="0" * 64)),
                   ("preguntas", lambda e: e["preguntas"].update(sha256="0" * 64))):
        en, sn = H.entrada_de_juguete(TMP, n, ["JUG01"], mutar=mut)
        malas[n] = frena(K.cargar_entrada, en, sn)
    return e["_sha256"] == s and all(malas.values()), f"frena en {sum(1 for v in malas.values() if v)} de {len(malas)}"


@caso("entrada: frena sin BANCO_VENV_VECTOR, con uno que no existe, con otro Python, con otro R5, con otros roles y con el freno sobre el tope")
def _():
    casos = {"sin_venv": dict(venv=None), "venv_inexistente": dict(venv="venvs/no_existe_selftest_b63"),
             "otro_python": dict(python="3.11.0"),
             "otro_R5": dict(mutar=lambda e: e["R5"].update(max_turns=45)),
             "roles": dict(mutar=lambda e: e["brazos"]["kg"].update(rol="fragmentos_denso")),
             "freno": dict(freno=60.0, tope=50.0)}
    out = {}
    for n, kw in casos.items():
        en, sn = H.entrada_de_juguete(TMP, n, ["JUG01"], **kw)
        out[n] = frena(K.cargar_entrada, en, sn)
    return all(out.values()), f"frena en {sum(1 for v in out.values() if v)} de {len(out)}"


@caso("preguntas: el esquema de EV2 por defecto, cada criterio con solo su texto y su cita; un id que no está o un esquema distinto")
def _():
    ent, s = H.entrada_de_juguete(TMP, "preg", ["JUG01", "JUG02"])
    e = K.cargar_entrada(ent, s)
    p = K.cargar_preguntas(e)
    en, sn = H.entrada_de_juguete(TMP, "preg_mal", ["JUG01", "NO_ESTA"])
    no_esta = frena(K.cargar_preguntas, K.cargar_entrada(en, sn))
    en2, sn2 = H.entrada_de_juguete(TMP, "preg_esq", ["JUG01"], mutar=lambda e: e["preguntas"].update(esquema={"criterios": "otro.lado"}))
    sin_crit = frena(K.cargar_preguntas, K.cargar_entrada(en2, sn2))
    return (list(p) == ["JUG01", "JUG02"] and all(set(c) == {"criterio", "cita_textual"} for v in p.values() for c in v["criterios"])
            and bool(no_esta) and bool(sin_crit)), None


@caso("D-10: las marcas del brazo (sus herramientas, con y sin prefijo, y la forma de su cita), sin editar la respuesta; la cifra por brazo")
def _():
    ent, s = H.entrada_de_juguete(TMP, "d10", ["JUG01"])
    e = K.cargar_entrada(ent, s)
    mk, mf = JB.marcas_d10(e, "kg"), JB.marcas_d10(e, "fragmentos_bm25")
    r1 = "Según buscar_nodos, el nodo dice que sí."
    r2 = "Según el pasaje que trajo mcp__fragmentos__buscar_pasajes."
    r3 = "Una respuesta sin marcas (la palabra nodos_x no cuenta)."
    a, b, c = JB.contar_d10(r1, mk), JB.contar_d10(r2, mf), JB.contar_d10(r3, mk)
    tabla = {"filas": {"x1": {"brazo": "kg", "d10": a}, "x2": {"brazo": "fragmentos_bm25", "d10": b}, "x3": {"brazo": "kg", "d10": c}}}
    rs = JB.resumen_d10(tabla, e)
    return (a["con_alguna"] and a["marcas"]["buscar_nodos"] and a["marcas"]["cita:\\bnodos?\\b"] and b["con_alguna"]
            and b["marcas"]["mcp__fragmentos__buscar_pasajes"] and not c["con_alguna"]
            and all(x["sha256_antes"] == x["sha256_despues"] for x in (a, b, c))
            and rs["por_brazo"]["kg"] == {"n_respuestas": 2, "con_alguna_marca": 1, "respuestas_editadas": 0,
                                          "por_marca": rs["por_brazo"]["kg"]["por_marca"]}
            and rs["por_brazo"]["fragmentos_bm25"]["con_alguna_marca"] == 1), f"{len(mk)} marcas del grafo, {len(mf)} de BM25"


@caso("id opaco: B63J- y 10 hexadecimales, determinista, distinto por brazo, repetición y respuesta")
def _():
    a = JB.id_opaco("Q1", "kg", 1, "s")
    return (a.startswith("B63J-") and len(a) == 15 and a == JB.id_opaco("Q1", "kg", 1, "s")
            and len({a, JB.id_opaco("Q1", "fragmentos_bm25", 1, "s"), JB.id_opaco("Q1", "kg", 2, "s"), JB.id_opaco("Q1", "kg", 1, "t")}) == 4), a


@caso("el pedido del juez sin el brazo: el de construir_kwargs con la pregunta, la respuesta y los criterios; frena con el brazo o una clave de más")
def _():
    preg = {"Q1": {"pregunta": "¿Pregunta de juguete?", "criterios": [{"criterio": "C1", "cita_textual": "Cita 1"}]}}
    c = JB.caso_ciego("Q1", "kg", 1, "Respuesta de juguete.", preg)
    bien = JB.verificar_pedido(c, BRAZOS)
    con_brazo = JB.verificar_pedido(JB.caso_ciego("Q1", "kg", 1, "r", {"Q1": {**preg["Q1"], "pregunta": "¿Qué dice fragmentos_bm25?"}}), BRAZOS)
    de_mas = JB.verificar_pedido(c | {"brazo": "kg"}, BRAZOS)
    crit = JB.verificar_pedido({**c, "criterios": [{"criterio": "C1", "cita_textual": "Cita 1", "brazo": "kg"}]}, BRAZOS)
    kw = J.construir_kwargs(c["pregunta"], c["respuesta"], c["criterios"])
    return (not bien and bool(con_brazo) and bool(de_mas) and bool(crit) and set(kw) == {"model", "max_tokens", "temperature", "system", "messages"}
            and "kg" not in json.dumps(kw["messages"]).replace("Respuesta de juguete.", "")), f"{len(con_brazo) + len(de_mas) + len(crit)} fugas en las pruebas en contra"


class ClientePrueba:
    """Un cliente del juez de prueba: cuenta sus llamadas y contesta un JSON válido o uno mal formado."""

    def __init__(self, mal=False):
        self.n, self.mal = 0, mal
        self.messages = self

    def create(self, **kw):
        self.n += 1
        n = int(kw["messages"][0]["content"].split("CRITERIOS (")[1].split(")")[0])
        texto = "sin objeto" if self.mal else json.dumps({"clasificacion_respuesta": "contenido", "criterios": [
            {"indice": i, "veredicto": "cumplido", "fragmento": None, "justificacion": "prueba"} for i in range(1, n + 1)]})

        class B:
            type, text = "text", texto

        class U:
            input_tokens, output_tokens = 1000, 300

        class Resp:
            content, stop_reason, usage, model = [B()], "end_turn", U(), "claude-sonnet-4-6"
        return Resp()


@caso("la guarda del juez: con lo gastado más el costo mayor sobre el freno, levanta FrenoJuez sin llamar")
def _():
    d = TMP / "juez_guarda"
    cl = {rep: ClientePrueba() for rep in JB.REPS}
    c = JB.caso_ciego("Q1", "kg", 1, "r", {"Q1": {"pregunta": "p", "criterios": [{"criterio": "c", "cita_textual": "t"}]}})
    try:
        JB.juzgar(c, cl, d, d / "cache", 9.98, 10.0, 12.0)
        corto = False
    except JB.FrenoJuez:
        corto = True
    r = JB.juzgar(c, cl, d, d / "cache", 0.0, 10.0, 12.0)
    return corto and r["llamadas"] == 3 and sum(x.n for x in cl.values()) == 3, "0,0378 mientras no hay ninguna juzgada"


@caso("una salida mal formada del juez: va a errores_r{rep}.jsonl y no se reintenta")
def _():
    d = TMP / "juez_mal"
    cl = {rep: ClientePrueba(mal=True) for rep in JB.REPS}
    c = JB.caso_ciego("Q1", "kg", 1, "r", {"Q1": {"pregunta": "p", "criterios": [{"criterio": "c", "cita_textual": "t"}]}})
    a = JB.juzgar(c, cl, d, d / "cache", 0.0, 10.0, 12.0)
    b = JB.juzgar(c, cl, d, d / "cache", 0.0, 10.0, 12.0)
    return a["errores"] == 3 and b["ya_estaba"] and sum(x.n for x in cl.values()) == 3, None


@caso("la agregación: modal por criterio y el mapping de EV2; una respuesta sin sus tres repeticiones, incompleta")
def _():
    d = TMP / "agregar"
    d.mkdir(parents=True, exist_ok=True)
    vs = {1: ["cumplido", "no_cumplido"], 2: ["cumplido", "no_cumplido"], 3: ["cumplido", "cumplido"]}
    for rep in JB.REPS:
        filas = [{"id_opaco": "A", "rep": rep, "clasificacion_respuesta": "contenido",
                  "criterios": [{"indice": i + 1, "veredicto": v} for i, v in enumerate(vs[rep])], "meta": {"input_tokens": 1, "output_tokens": 1}}]
        if rep != 3:
            filas.append({"id_opaco": "B", "rep": rep, "clasificacion_respuesta": "contenido", "criterios": [{"indice": 1, "veredicto": "cumplido"}],
                          "meta": {"input_tokens": 1, "output_tokens": 1}})
        (d / f"veredictos_r{rep}.jsonl").write_text("\n".join(json.dumps(x) for x in filas) + "\n", encoding="utf-8")
    ag = JB.agregar(d, {"A": 2, "B": 1})
    a = ag["agregados"][0]
    return (a["modales"] == ["cumplido", "no_cumplido"] and a["veredicto_pregunta"] == M.veredicto_pregunta(["cumplido", "no_cumplido"])
            and ag["incompletas"] == [{"id_opaco": "B", "reps_faltantes": [3]}]), a["veredicto_pregunta"]


@caso("el patrón: el de guardas_lote trae el renglón 16 de a2_2/guardas_a2_2.zsh y correr_prueba_T_v2.py; el de prueba no corre con el CLI real ni con un nombre de un paso pago")
def _():
    p = R.control_patron()
    viejo = R.LOTE.cli_del_path
    try:
        R.LOTE.cli_del_path = lambda: {"version": "2.1.241 (Claude Code)"}
        real = frena(R.fijar_patron_de_prueba, "prueba_b63_selftest1")
        R.LOTE.cli_del_path = lambda: {"version": "2.1.241 (CLI falso de prueba)"}
        nombre = frena(R.fijar_patron_de_prueba, "correr_tanda_selftest")
        corto = frena(R.fijar_patron_de_prueba, "corto")
    finally:
        R.LOTE.cli_del_path = viejo
    return (p["trae_el_renglon_16"] and p["trae_correr_prueba_T_v2"] and p["patron_igual_al_renglon_16_mas_T"]
            and bool(real) and bool(nombre) and bool(corto) and G.PATRON_PAGO == R.PATRON_REAL), None


@caso("el testigo, leído para B6.3: los renglones de la fecha del día se cuentan y no frenan; cualquier otro, sí")
def _():
    ps = {"TESTIGO-T1-1-kg": {"tools_PASS": True, "comparacion_con_init": {"PASS": True}, "cwd_vacio": True}}
    base = {"por_sesion": ps, "testigos_despues": {"iguales": True, "plantados_borrados": True}, "cwd_al_final": {"vacio": True},
            "ningun_pedido_al_modelo_sale_de_la_maquina": True, "PASS": False,
            "FRENO": ["TESTIGO-T1-1-kg, pedido 2 (turno), `system`: la fecha del día (1 apariciones)",
                      "TESTIGO-T1-1-kg, pedido 2 (turno), `messages`: la fecha del día (1 apariciones)"]}
    a = R.leer_testigo(base)
    b = R.leer_testigo(base | {"FRENO": base["FRENO"] + ["TESTIGO-T1-1-kg: llega un testigo (3 trechos o tokens; ver por pedido, campo y testigo)"]})
    return (a["PASS_de_B63"] and a["renglones_de_la_fecha"] == 2 and a["fecha_por_tipo_y_campo"] == {"turno|messages": 1, "turno|system": 1}
            and not b["PASS_de_B63"] and len(b["otros_FRENO"]) == 1), None


@caso("el enmascarado: calcular, probar y aplicar sobre copias de juguete; la carpeta personal pasa a $HOME y el original queda afuera")
def _():
    raiz = TMP / "enm"
    casa = TMP / "casa_de_juguete"
    d = raiz / "data/experiment/banco_mcp/b63/resultados/real/Q1-r1/lote1/S1"
    d.mkdir(parents=True, exist_ok=True)
    cwd = f"{casa}{EN.SUFIJO}"
    (d / "stream_S1.jsonl").write_text(json.dumps({"type": "system", "subtype": "init", "cwd": cwd}) + "\n"
                                      + json.dumps({"type": "result", "cwd": cwd + "/x"}) + "\n", encoding="utf-8")
    (d / "sesion_S1.jsonl").write_text(json.dumps({"cwd": cwd}) + "\n", encoding="utf-8")
    js, orig = TMP / "enm.json", TMP / "enm_originales"
    EN.main(["--calcular", str(raiz), str(js)])
    EN.main(["--probar", str(raiz), str(js)])
    EN.main(["--aplicar", str(raiz), str(js), "--originales", str(orig)])
    x = json.loads(js.read_text(encoding="utf-8"))
    otra = frena(EN.main, ["--probar", str(raiz), str(js)])
    return (x["n_archivos"] == 2 and x["n_reemplazos"] == 3 and casa.name not in (d / "stream_S1.jsonl").read_text(encoding="utf-8")
            and "$HOME" in (d / "sesion_S1.jsonl").read_text(encoding="utf-8")
            and all((orig / f["ruta"]).is_file() and H.sha(orig / f["ruta"]) == f["sha256_original"] for f in x["archivos"])
            and bool(otra)), "después de aplicar, probar frena"


@caso("retomar: el sha256 de la entrada sin el tope ni el freno es el mismo si solo cambian esos dos, y otro si cambia otra cosa")
def _():
    a, b = H.entrada_de_juguete(TMP, "st_a", ["JUG01"], freno=10.0, tope=12.0), H.entrada_de_juguete(TMP, "st_b", ["JUG01"], freno=20.0, tope=22.0)
    c = H.entrada_de_juguete(TMP, "st_c", ["JUG01", "JUG02"])
    ea, eb, ec = (K.cargar_entrada(*x) for x in (a, b, c))
    return ea["_sha256"] != eb["_sha256"] and ea["_sha256_sin_tope"] == eb["_sha256_sin_tope"] != ec["_sha256_sin_tope"], None


@caso("el lanzador de una sesión: frena sin B63_CONFIG_AGENTES o con un sha256 que no da; la cadena de archivos del lanzador, con su sha256")
def _():
    import lanzar_agente_b63 as LB
    viejo = {k: os.environ.get(k) for k in ("B63_CONFIG_AGENTES", "B63_CONFIG_AGENTES_SHA256")}
    try:
        for k in viejo:
            os.environ.pop(k, None)
        sin = frena(LB.config_de_la_entrada)
        os.environ["B63_CONFIG_AGENTES"] = str(AQUI / "seco" / "config_agentes_b63_juguete.json")
        os.environ["B63_CONFIG_AGENTES_SHA256"] = "0" * 64
        mal = frena(LB.config_de_la_entrada)
    finally:
        for k, v in viejo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    cadena = [x["ruta"].rsplit("/", 1)[-1] for x in LB.archivos_del_lanzador()]
    return (bool(sin) and bool(mal) and cadena == ["correr_b63.py", "comun_b63.py", "juez_b63.py", "lanzar_lote_paralelo.py", "guardas_lote.py",
                                                     "lanzar_agente_b63.py", "lanzar_agente_n6_prueba.py", "lanzar_agente.py"]), None


@caso("el juez de EV2 sin editar: prompt v1 fd446f8e…, claude-sonnet-4-6, temperatura 0, y los sellos de la entrada")
def _():
    ent, s = H.entrada_de_juguete(TMP, "juez", ["JUG01"])
    e = K.cargar_entrada(ent, s)
    ins = JB.controlar_instrumento(e)
    mal = H.entrada_de_juguete(TMP, "juez_mal", ["JUG01"], mutar=lambda e: e["juez"]["archivos"][0].update(sha256="0" * 64))
    return ins["prompt_sha256"] == JB.PROMPT_SHA256 and len(ins["sellos"]) == 3 and bool(frena(K.cargar_entrada, *mal)), None


def main() -> int:
    for ok, t in RES:
        print(("PASS " if ok else "FAIL ") + t)
    n = sum(ok for ok, _ in RES)
    print(f"selftest B6.3: {n} de {len(RES)} en PASS")
    return 0 if n == len(RES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
