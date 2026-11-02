#!/usr/bin/env python3
"""selftest_analizar_b64.py — La prueba de analizar_b64.py y de armar_adjudicacion_b64.py, y de aplicar_lectura_tolerante_b63.py sin
cambios sobre salidas con la forma de B6.4, con datos de juguete (H-6). USD 0, sin la API, sin ningún dato real: arma en --trabajo (que
no puede existir) un mundo de juguete con la forma de las salidas del runner de B6.3 con los cuatro brazos de B6.4 (12 preguntas, 4 por
tipo, en 4 documentos, k = 3: 144 corridas), con las cachés, los veredictos y los errores del juez, y corre sobre él la lectura tolerante
sellada, el armado de la adjudicación y el análisis. Los valores esperados los calcula la prueba por su cuenta, desde su diseño.

Del código de B6.3 usa solo el import, con sus sha256: analizar_b63.py y los demás de analizar_b64.SELLADO; selftest_analizar_b63.py
(sus datos de juguete y su p exacta); y, del clon de HEAD, juez_b63, comun_b63, mapping, el juez de EV2 y llm_cache (su esquema y su
_store, para escribir las cachés de juguete como las escribe el juez).

Las ramas:
  - lo importado de B6.3 es byte a byte lo sellado, analizar_b64 no tiene copias propias de las funciones importadas, y nada se edita
    (los sha256 al principio y al final, y las constantes del módulo importado);
  - la permutación, Holm y el bootstrap contra B6.3: con los datos de juguete de selftest_analizar_b63.py (sus mundos A y B), con las
    semillas de B6.3 analizar_b64.confirmatorio da lo mismo que analizar_b63.confirmatorio; con las de B6.4, lo mismo que las funciones
    de B6.3 llamadas con esas semillas;
  - la afirmación principal en sus tres casos (supera a las dos, a una sola, a ninguna) y con Holm a favor de los fragmentos;
  - el cuarto brazo no entra en Holm ni en la afirmación (dos métricas que difieren solo en kg_n7 dan lo mismo), con su intervalo;
  - la robustez por documento: su p contra la exacta y su intervalo;
  - la lectura tolerante y la adjudicación: una salida del juez que la estricta no lee y la tolerante sí (aplicar_lectura_tolerante_b63
    sin cambios, P1 a P8), y dos respuestas que van a la adjudicación (el armado de B6.4, la planilla, su sello y su sellador);
  - las métricas de los tres escenarios, lo operativo por brazo y por tipo, y lo declarado (la lectura tolerante por brazo, las anclas
    fuera de los 46 y los lugares que cambiaron);
  - la sensibilidad de los expertos: sin devolución, con uno, con dos y con tres;
  - los frenos: entradas con otro sha256 o sin él, un brazo que falta (en la entrada y en el D-10), --salida que ya existe, una devuelta
    sin su sha256 y otro sha256 para el código en el JSON;
  - que el análisis no imprime nada, y que dos corridas sobre el mismo mundo dan el mismo JSON, byte a byte.
La corrección del H-6 (las ramas d1_ y d3_; la lectura tolerante corre, en todos los mundos, por su envoltorio aplicar_lectura_tolerante_b64):
  - la decisión 1: las cuatro elecciones del H-6, en lo declarado, con la decisión tal cual, y en el código;
  - la decisión 3, en otro mundo con dos salidas del juez que no lee ninguna lectura (una cortada por max_tokens y una que la tolerante
    rechaza): sin el envoltorio, el sellado no escribe; con él, las encuentra, el sellado da P1 a P8 sobre la vista, dos veces igual, y
    lo original no se toca; las dos respuestas van enteras a la adjudicación por el armado de B6.4, con todos sus criterios; el análisis
    termina y escribe, con el veredicto que dan las marcas de la autora, y lo declara por brazo;
  - en el mundo de H-6, sin ninguna, el envoltorio corre el sellado sobre banco_b64 tal cual.

Imprime solo el nombre de cada control con PASS o FAIL y el sha256 del informe (sin rutas, para que dos corridas den lo mismo).

  B64_CODIGO_B63=<b63/analisis/codigo de una copia de HEAD> python3 -I -B selftest_analizar_b64.py --clon <b63/v2/b2 de esa copia>
      --trabajo <carpeta nueva> --informe <json nuevo>
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import analizar_b64 as B  # noqa: E402
import aplicar_lectura_tolerante_b64 as ENV  # noqa: E402
import armar_adjudicacion_b64 as Z  # noqa: E402

A = B.A
SHA_SELFTEST_B63 = "e1c37aa300c1954e8cdda8cbac76425e3cbbcc1e1a77449d3bb8d420b85b70ed"     # selftest_analizar_b63.py en HEAD 80085175
CHICO = {"n_perm": 2000, "n_boot": 200}
QIDS = [f"JUG-B{i:02d}" for i in range(1, 13)]
TIPO = {q: B.TIPOS[(i - 1) // 4] for i, q in enumerate(QIDS, 1)}
DOC = {q: ("juga", "jugb", "jugc", "jugd")[(i - 1) % 4] for i, q in enumerate(QIDS, 1)}
CLASE_DOC = {"juga": "RI", "jugb": "NG_digerible", "jugc": "NG_digerible", "jugd": "NG_necesita_reglas"}
ANCLAS = {"JUG-B01": ["juga::1.1", "juga::1.2", "juga::2.1"], "JUG-B02": ["jugb::1.1", "jugb::1.2", "jugb::2.2"],
          "JUG-B03": ["jugc::1.1", "jugc::2.1", "jugc::2.2"], "JUG-B04": ["jugd::1.1", "jugd::1.2", "jugd::2.1"],
          "JUG-B05": ["juga::2.2", "jugz::1.1"], "JUG-B06": ["jugb::2.1", "jugy::3.1"], "JUG-B07": ["jugc::1.2", "juga::1.1"],
          "JUG-B08": ["jugd::2.2", "jugx::1.1"], "JUG-B09": ["juga::3.1", "juga::3.2"], "JUG-B10": ["jugb::3.1", "jugb::3.2"],
          "JUG-B11": ["jugc::3.1", "jugc::3.2"], "JUG-B12": ["jugd::3.1", "jugd::3.2"]}
LETRA = {"kg": "uno", "fragmentos_hibrida": "dos", "fragmentos_denso": "tres", "kg_n7": "cuatro"}
# Las corridas especiales del diseño: la de la lectura tolerante (su repetición 2), las dos que van a la adjudicación, y las demás
TOLERANTE = ("JUG-B09", 1, "kg_n7")
ADJUDICADAS = {("JUG-B10", 2, "kg"): (2, "Cumplido"), ("JUG-B05", 1, "fragmentos_hibrida"): (1, "no cumplido")}
COLUMNAS_EXPERTO = ["codigo", "pregunta", "respuesta_de_referencia", "texto_del_ancla", "se_puede_responder_desde_el_texto (sí / no)",
                    "la_respuesta_es_correcta (sí / parcial / no)", "relevancia_nota (1 a 5)", "relevancia_puesto", "comentario"]
FINAL_A_ESTADO = {"C": "correcta", "N": "no_correcta", "SV": "sin_veredicto", "falla_infra_sin_terminar": "infra_sin_terminar",
                  "cortada": "cortada", "incompleta_otra": "incompleta_otra"}
# La corrección del H-6 (decisión 3): en el mundo sin lectura, dos salidas del juez que no lee ninguna lectura, en una repetición de dos
# respuestas; la autora marca todos sus criterios, al revés de lo que daban las otras lecturas del juez
SIN_LECTURA = {("JUG-B11", 2, "fragmentos_denso"): {"rep": 2, "como": "max_tokens", "marca": "no cumplido"},
               ("JUG-B07", 3, "kg_n7"): {"rep": 1, "como": "la_tolerante_la_rechaza", "marca": "Cumplido"}}
# Las decisiones de la autora del 30/10/2026, tal cual, escritas aparte del código que las declara
DECISION_1 = ("«Acepto, declaradas, las cuatro elecciones que hizo el H-6 y que el pre-registro no fija: la semilla B64:adjudicacion:v1, el "
              "intervalo de d en el bootstrap por documento, la semilla de la corrección para los intervalos del cuarto brazo y la forma "
              "de clases_documentos y de lugares.»")
DECISION_3 = ("«Una salida del juez que no leen ni la lectura estricta ni la tolerante no puede dejar el análisis sin escribir: va al "
              "destino que fija el §5 del pre-registro, con un envoltorio declarado.»")


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(p: Path) -> str:
    return sha_b(Path(p).read_bytes())


def escribir(p: Path, contenido) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    b = contenido if isinstance(contenido, (bytes, str)) else json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    b = b.encode("utf-8") if isinstance(b, str) else b
    p.write_bytes(b)
    return sha_b(b)


def importar_selftest_b63():
    """selftest_analizar_b63.py, de la carpeta del código sellado, sin editarlo: sus datos de juguete y su p exacta."""
    ruta = B.CODIGO_B63 / "selftest_analizar_b63.py"
    b = ruta.read_bytes()
    if sha_b(b) != SHA_SELFTEST_B63:
        raise SystemExit("ABORTO: selftest_analizar_b63.py no es el de HEAD")
    spec = importlib.util.spec_from_file_location("selftest_analizar_b63", ruta)
    m = importlib.util.module_from_spec(spec)
    exec(compile(b, str(ruta), "exec"), m.__dict__)  # noqa: S102
    return m


def media(vs):
    vs = list(vs)
    return float(sum(vs) / len(vs)) if vs else None


class DLocal:
    """Las d de unos pares de brazos, con fracciones: lo esperado del bootstrap, calculado aparte del código del análisis."""

    def __init__(self, pares: dict):
        self.pares = pares

    def calcular(self, qs, m):
        out = {}
        for n, (x, y) in self.pares.items():
            v = [Fraction(*m[(q, x)]) - Fraction(*m[(q, y)]) for q in qs if (q, x) in m and (q, y) in m]
            out[f"d|{n}"] = float(sum(v) / len(v)) if v else None
        return out


def cerca(a, b, tol=1e-12) -> bool:
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(cerca(x, y, tol) for x, y in zip(a, b))
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tol


# --------------------------------------------------------------------------------------------------------------------- #
# El diseño de las corridas de B6.4                                                                                     #
# --------------------------------------------------------------------------------------------------------------------- #
def n_criterios(q: str) -> int:
    return 3 if TIPO[q] == "agregacion" else 2


def diseno(sin_lectura: dict | None = None) -> dict:
    """{(qid, r, brazo): {"clase", "reps" (los veredictos de las tres repeticiones del juez, si es completa), "final"}}: kg acierta en
    todas; la híbrida, en ninguna; la densa, en todas salvo B03 y B07; kg_n7, en B01 a B06 y B09. Con sin_lectura, el final de esas
    corridas es el de las marcas de la autora."""
    d = {}
    for q in QIDS:
        n = n_criterios(q)
        for r in (1, 2, 3):
            for b in B.BRAZOS:
                bueno = {"kg": True, "fragmentos_hibrida": False, "fragmentos_denso": q not in ("JUG-B03", "JUG-B07"),
                         "kg_n7": q in ("JUG-B01", "JUG-B02", "JUG-B03", "JUG-B04", "JUG-B05", "JUG-B06", "JUG-B09")}[b]
                v = "cumplido" if bueno else "no_cumplido"
                d[(q, r, b)] = {"clase": "completa", "reps": [[v] * n for _ in range(3)]}
    d[("JUG-B02", 1, "kg_n7")] = {"clase": "cortada"}
    d[("JUG-B04", 2, "fragmentos_denso")] = {"clase": "incompleta_otra", "motivo": "log R1 11 llamadas vs sesión 12 tool_use MCP"}
    d[("JUG-B06", 3, "fragmentos_hibrida")] = {"clase": "falla_infra_sin_terminar", "intentos": 3}
    d[("JUG-B10", 2, "kg")]["reps"] = [["cumplido", "dudoso"]] * 3                                  # modal dudoso
    d[("JUG-B05", 1, "fragmentos_hibrida")]["reps"] = [["cumplido", "no_cumplido"], ["no_cumplido", "no_cumplido"],
                                                       ["dudoso", "no_cumplido"]]                    # modal sin_consenso
    for k, v in d.items():
        if v["clase"] != "completa":
            v["final"] = v["clase"]
        elif k in (sin_lectura or {}):
            v["final"] = "C" if A.plegar(sin_lectura[k]["marca"]) == "cumplido" else "N"
        elif k in ADJUDICADAS:
            cr, marca = ADJUDICADAS[k]
            mods = [A.plegar(marca).replace(" ", "_") if i == cr else v["reps"][0][i - 1] for i in range(1, n_criterios(k[0]) + 1)]
            v["final"] = "C" if all(x == "cumplido" for x in mods) else "N"
        else:
            v["final"] = "C" if all(x == "cumplido" for x in v["reps"][0]) else "N"
    return d


def esperadas(d: dict, escenario: str) -> dict:
    """{(qid, brazo): Fraction} con las reglas del §6 de B6.3, escritas aparte del análisis."""
    acc: dict = {}
    for (q, r, b), v in d.items():
        f = v["final"]
        if f in ("cortada", "incompleta_otra") and escenario == "sin_las_cortadas":
            continue
        n, x = acc.get((q, b), (0, 0))
        acc[(q, b)] = (n + 1, x + (f == "C"))
    return {k: Fraction(x, n) for k, (n, x) in acc.items()}


def salida_del_juez(vs: list[str], rota: bool = False) -> str:
    """La salida de una repetición del juez: el JSON del prompt de EV2; rota, con comillas dobles sin escapar en un fragmento."""
    if rota:
        crits = [f'{{"indice": {k}, "veredicto": "{v}", "fragmento": "dice "tal cosa" en el punto", "justificacion": "x"}}'
                 for k, v in enumerate(vs, 1)]
        return '{"clasificacion_respuesta": "contenido", "criterios": [' + ", ".join(crits) + "]}"
    return json.dumps({"clasificacion_respuesta": "contenido",
                       "criterios": [{"indice": k, "veredicto": v, "fragmento": None, "justificacion": "x"} for k, v in enumerate(vs, 1)]},
                      ensure_ascii=False)


def salida_sin_lectura(vs: list[str], como: str) -> tuple[str, str]:
    """(texto, stop_reason) de una salida del juez que no lee ni la estricta ni la tolerante: cortada por max_tokens, o con comillas sin
    escapar y un índice de menos (la tolerante aplica y la rechaza)."""
    if como == "max_tokens":
        return salida_del_juez(vs)[:60], "max_tokens"
    return salida_del_juez(vs[:-1], rota=True), "end_turn"


# --------------------------------------------------------------------------------------------------------------------- #
# El mundo de juguete                                                                                                   #
# --------------------------------------------------------------------------------------------------------------------- #
def mundo(W: Path, JB, K, clon: Path, sin_lectura: dict | None = None) -> tuple[dict, dict, dict]:
    W.mkdir(parents=True)
    J = JB.J
    sin_lectura = sin_lectura or {}
    d = diseno(sin_lectura)
    preguntas = {"preguntas": [{"id": q, "pregunta": f"Pregunta de juguete {q[-2:]}", "tipo": TIPO[q], "to": DOC[q],
                                "anclas": [{"rol": "ancla" if i == 0 else "otro_punto", "unidad": u} for i, u in enumerate(ANCLAS[q])],
                                "criterios": [{"criterio": f"criterio de juguete {k}", "cita_textual": f"cita de juguete {k}"}
                                              for k in range(1, n_criterios(q) + 1)]} for q in QIDS]}
    sp = escribir(W / "preguntas_juguete.json", preguntas)
    esquema = {"lista": "preguntas", "id": "id", "pregunta": "pregunta", "criterios": "criterios", "criterio": "criterio",
               "cita": "cita_textual"}
    entrada = {"unidad": "juguete", "preguntas": {"ruta": "preguntas_juguete.json", "sha256": sp, "ids_en_orden": QIDS, "esquema": esquema},
               "k": 3, "brazos": {b: {"rol": "grafo" if b.startswith("kg") else b} for b in B.BRAZOS}}
    esp = {"entrada": escribir(W / "entrada_juguete.json", entrada)}
    tres = dict(entrada, brazos={b: v for b, v in entrada["brazos"].items() if b != B.CUARTO})
    otros = {"entrada_tres_brazos": escribir(W / "entrada_tres_brazos.json", tres)}
    PQ = {x["id"]: {"pregunta": x["pregunta"], "criterios": x["criterios"]} for x in preguntas["preguntas"]}

    # banco_b64/: el estado y las sesiones, con los nombres del runner de B6.3
    R = W / "banco_b64" / "resultados" / "real"
    st = {"bloques": {}}
    casos = []
    for b in K.orden_bloques(QIDS, 3, sorted(B.BRAZOS)):
        blq = {"final": {}, "intentos_por_brazo": {}, "juez_pendiente": []}
        for x in sorted(B.BRAZOS):
            v = d[(b["qid"], b["r"], x)]
            it = v.get("intentos", 1)
            sid = K.id_sesion(b["qid"], b["r"], x, it)
            blq["final"][x] = {"clasificacion": v["clase"], "id": sid, "intento": it, "salida": f"pasada1/{sid}"}
            blq["intentos_por_brazo"][x] = it
            S = R / "pasada1" / sid
            resp = f"Respuesta de juguete {b['qid'][-2:]} r{b['r']} {LETRA[x]}"
            if v["clase"] != "falla_infra_sin_terminar":
                meta = {"brazo": x}
                if v["clase"] == "completa":
                    meta["final_json_R4"] = {"respondible": True, "respuesta": resp, "citas": []}
                escribir(S / f"meta_{sid}.json", meta)
                escribir(S / f"log_r1_{sid}.jsonl", "".join(json.dumps({"n": i}) + "\n" for i in range(3)))
            n_ll = {(QIDS[0], 1, "kg_n7"): 31, (QIDS[0], 2, "kg_n7"): 30}.get((b["qid"], b["r"], x), 5)
            escribir(S / f"meta_sin_texto_{sid}.json",
                     {"brazo": x, "hb2": {"n_llamadas_log_r1": n_ll}, "mapa_R7": [{"n": 1, "tool": "mcp__kg__ver_punto", "call_id_log": "c1"}],
                      "completitud_R3": {"motivos_incompleta": [v["motivo"]] if "motivo" in v else []},
                      "tokens_R9": {"costo_recomputado": {"total_usd": 0.01},
                                    "por_llamada_api": [{"input_tokens": 100, "cache_read_input_tokens": 50 * k, "cache_creation_input_tokens": 10,
                                                         "output_tokens": 5} for k in (1, 2)]}})
            if v["clase"] == "completa":
                casos.append(((b["qid"], b["r"], x), JB.caso_ciego(b["qid"], x, b["r"], resp, PQ)))
        st["bloques"][b["bloque"]] = blq
    escribir(R / "estado_b63.json", st)

    # juez/: las tres cachés, los veredictos y los errores registrados y los agregados de la estricta, como los deja el juez de B6.3
    JD = W / "banco_b64" / "juez"
    (JD / "cache").mkdir(parents=True)
    ns = {r: J.lc.make_namespace(f"juez_ev2_r{r}", code_ver=J.CODE_VER, thinking=False) for r in (1, 2, 3)}
    t0, i = datetime(2026, 11, 5, 10, 0, 0), 0
    ids = {}
    for r in (1, 2, 3):
        con = sqlite3.connect(str(JD / "cache" / JB.db_path(r, Path(".")).name))
        con.executescript(J.lc._SCHEMA)
        ver, err = [], []
        for k, c in casos:
            ids[k] = c["id_opaco"]
            if k in sin_lectura and sin_lectura[k]["rep"] == r:
                texto, stop = salida_sin_lectura(d[k]["reps"][r - 1], sin_lectura[k]["como"])
            else:
                texto, stop = salida_del_juez(d[k]["reps"][r - 1], rota=(k == TOLERANTE and r == 2)), "end_turn"
            req = J.lc.canonical_request(J.construir_kwargs(c["pregunta"], c["respuesta"], c["criterios"]))
            i += 1
            uso = {"input_tokens": 1000 + i, "output_tokens": 100 + i}
            J.lc._store(con, key=J.lc.compute_key(ns[r], req), namespace=ns[r], domain="juez_ev2",
                        created_at=(t0 + timedelta(seconds=i)).isoformat(), model=J.MODELO, usage=uso, stop_reason=stop,
                        thinking_enabled=False, request_json=req,
                        raw_json=json.dumps({"content": [{"type": "text", "text": texto}], "model": J.MODELO, "stop_reason": stop},
                                            ensure_ascii=False))
            try:
                if stop == "max_tokens":                 # como juez.juzgar: la registra como error, sin leerla
                    raise ValueError("respuesta del juez truncada por max_tokens")
                v = J.parsear_veredicto(texto, len(c["criterios"]))
                ver.append({"id_opaco": c["id_opaco"], "rep": r, "clasificacion_respuesta": v["clasificacion_respuesta"],
                            "criterios": v["criterios"], "meta": {"modelo": J.MODELO, "stop_reason": "end_turn", **uso,
                                                                  "prompt_version": J.PROMPT_VERSION, "prompt_sha256": J.PROMPT_SHA256,
                                                                  "code_ver": J.CODE_VER}})
            except ValueError as ex:
                err.append({"id_opaco": c["id_opaco"], "rep": r, "error": str(ex)[:200], "ts": "2026-11-05T12:00:00"})
        con.close()
        escribir(JD / f"veredictos_r{r}.jsonl", "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ver))
        escribir(JD / f"errores_r{r}.jsonl", "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in err))
    escribir(JD / "agregados_b63_ciego.json",
             json.dumps(JB.agregar(JD, {c["id_opaco"]: len(c["criterios"]) for _, c in casos}), ensure_ascii=False, indent=1) + "\n")
    archivos = sorted(p for p in (W / "banco_b64").rglob("*") if p.is_file())
    esp["manifiesto_fuera"] = escribir(W / "manifiesto_juguete.json", {"que": "juguete", "archivos": [
        {"ruta": str(p.relative_to(W)), "sha256": sha(p), "bytes": p.stat().st_size} for p in archivos]})

    # D-10, las fechas, las clases de los documentos, los lugares y el material de los expertos
    esp["d10"] = escribir(W / "d10_juguete.json", {"por_brazo": {b: {"con_alguna_marca": i, "n_respuestas": 36} for i, b in enumerate(B.BRAZOS)}})
    otros["d10_tres_brazos"] = escribir(W / "d10_tres_brazos.json", {"por_brazo": {b: {"con_alguna_marca": 0, "n_respuestas": 36}
                                                                                   for b in B.BRAZOS if b != B.CUARTO}})
    esp["fechas"] = escribir(W / "fechas_juguete.json", {"n_bloques_con_fechas_distintas": 0, "bloques_con_fechas_distintas": [],
                                                         "por_brazo_y_fecha": {b: {"2026-11-05": 36} for b in B.BRAZOS}})
    relleno = lambda p, n: [f"{p}{k:02d}" for k in range(1, n + 1)]  # noqa: E731
    clases = {"elegibles": ["juga", "jugb", "jugc", "jugd"] + relleno("elegible_juguete_", 42),
              "clases": {"anclas_de_las_96_de_B63": ["jugy"] + relleno("anclas_juguete_", 36), "N3": ["jugz"] + relleno("n3_juguete_", 13),
                         "evaluacion_final": ["jugy"] + relleno("final_juguete_", 14), "tanda_0": relleno("tanda0_juguete_", 5)}}
    esp["clases_documentos"] = escribir(W / "clases_documentos_juguete.json", clases)
    lugares = []
    for n, q in enumerate(QIDS, 1):
        final = {"documento": DOC[q], "unidad": ANCLAS[q][0], "clase": CLASE_DOC[DOC[q]]}
        sorteado = dict(final)
        if q == "JUG-B01":
            sorteado["unidad"] = "juga::9.9"
        elif q == "JUG-B02":
            sorteado |= {"documento": "jugq", "unidad": "jugq::1.1"}
        elif q == "JUG-B03":
            sorteado |= {"documento": "jugr", "unidad": "jugr::1.1", "clase": "NG_necesita_reglas"}
        lugares.append({"lugar": f"B64-O1-L{n:02d}", "id": q, "sorteado": sorteado, "final": final})
    esp["lugares"] = escribir(W / "lugares_juguete.json", {"lugares": lugares})
    esp["manifiesto_expertos"], _ = material_expertos(W / "expertos", {})

    # La lectura tolerante sellada, sin cambios, por su envoltorio de B6.4; el armado de la adjudicación de B6.4; la planilla de la autora
    # y su sello
    info = {"diseno": d, "ids": ids}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), en(W):
        try:
            info["aplicar_codigo"] = ENV.main(["--salida-b63", str(W / "banco_b64"), "--entrada", "entrada_juguete.json", "--clon", str(clon),
                                             "--tmp", str(W / "tmp_aplicacion"), "--salida", str(W / "aplicacion"),
                                             "--informe-b64", str(W / "informe_envoltorio_aplicacion.json")])
        except SystemExit as ex:
            info["aplicar_codigo"] = f"SystemExit: {ex}"
    info["aplicar_consola"] = buf.getvalue()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), en(W):
        try:
            info["armar_codigo"] = Z.main(["--salida-b64", str(W / "banco_b64"), "--entrada", "entrada_juguete.json", "--clon", str(clon),
                                          "--aplicacion", str(W / "aplicacion"), "--para-leer", str(W / "adjudicacion" / "para_leer"),
                                          "--clave", str(W / "adjudicacion" / "clave"), "--informe", str(W / "adjudicacion" / "informe.json")])
        except SystemExit as ex:
            info["armar_codigo"] = f"SystemExit: {ex}"
    info["armar_consola"] = buf.getvalue()
    PL = W / "adjudicacion" / "para_leer"
    clave = json.loads((W / "adjudicacion" / "clave" / "clave_adjudicacion_b64.json").read_text(encoding="utf-8"))
    info["clave"] = clave
    de_ficha = {f["ficha"]: (f["pregunta"], f["repeticion"], f["brazo"]) for f in clave["fichas"]}
    est = json.loads((PL / Z.ESTRUCTURA).read_text(encoding="utf-8"))
    filas = [[f, n, ADJUDICADAS[de_ficha[f]][1] if de_ficha[f] in ADJUDICADAS else sin_lectura[de_ficha[f]]["marca"], ""]
             for f, n in est["renglones"]]
    s = io.StringIO()
    csv.writer(s, lineterminator="\r\n").writerows([Z.AA.COLUMNAS] + filas)
    pb = ("﻿" + s.getvalue()).encode("utf-8")
    pl = W / "autora" / Z.PLANILLA
    escribir(pl, pb)
    esp["sello_planilla"] = escribir(W / "autora" / "sello_adjudicacion_b64.txt",
                                     "# sello de juguete: sha256, bytes, hora de modificación y nombre\n# sellado: 2026-11-05 12:00:00 -0300\n"
                                     f"{sha_b(pb)}  {len(pb)}  2026-11-05 11:59:00 -0300  {pl.name}\n")
    # el sellador que armó el armado, corrido aparte sobre una copia (su sello lleva la hora: no entra en el informe)
    SS = W / "autora_con_el_sellador"
    SS.mkdir()
    for n in (Z.ESTRUCTURA, Z.SELLADOR_NOMBRE):
        shutil.copyfile(PL / n, SS / n)
    escribir(SS / Z.PLANILLA, pb)
    rs = subprocess.run([sys.executable, "-I", "-B", Z.SELLADOR_NOMBRE], cwd=SS, capture_output=True, text=True)
    info["sellador"] = {"codigo": rs.returncode, "sello": (SS / "sello_adjudicacion_b64.txt").is_file()}
    try:
        A.planilla_sellada(SS / Z.PLANILLA, SS / "sello_adjudicacion_b64.txt")
        info["sellador"]["lo_acepta_el_analisis"] = True
    except A.Freno:
        info["sellador"]["lo_acepta_el_analisis"] = False

    AQ = W / "aplicacion"
    for k, p in (("agregados", AQ / "juez_con_lectura_tolerante" / "agregados_b63_ciego.json"),
                 ("agregados_tolerante", AQ / "agregados_de_las_que_no_se_leian_b63.json"),
                 ("veredictos_tolerante", AQ / "veredictos_lectura_tolerante_b63.jsonl"), ("agregados_sin_lectura", AQ / ENV.SIN_LECTURA),
                 ("estructura_planilla", PL / Z.ESTRUCTURA), ("clave_adjudicacion", W / "adjudicacion" / "clave" / "clave_adjudicacion_b64.json")):
        esp[k] = sha(p) if p.is_file() else None
    esp["devueltas"] = None
    rutas = {"clon": clon, "entrada": W / "entrada_juguete.json", "manifiesto_fuera": W / "manifiesto_juguete.json", "banco_b64": W / "banco_b64",
             "agregados": AQ / "juez_con_lectura_tolerante" / "agregados_b63_ciego.json",
             "agregados_tolerante": AQ / "agregados_de_las_que_no_se_leian_b63.json",
             "veredictos_tolerante": AQ / "veredictos_lectura_tolerante_b63.jsonl", "agregados_sin_lectura": AQ / ENV.SIN_LECTURA,
             "planilla": pl,
             "sello_planilla": W / "autora" / "sello_adjudicacion_b64.txt", "estructura_planilla": PL / Z.ESTRUCTURA,
             "clave_adjudicacion": W / "adjudicacion" / "clave" / "clave_adjudicacion_b64.json", "d10": W / "d10_juguete.json",
             "fechas": W / "fechas_juguete.json", "clases_documentos": W / "clases_documentos_juguete.json", "lugares": W / "lugares_juguete.json",
             "expertos": W / "expertos"}
    info["otros"] = otros
    return rutas, esp, info


def material_expertos(X: Path, devueltas: dict) -> tuple[str, dict]:
    """El material de juguete de los expertos (la forma del de B6.3: su manifest.txt, la clave de los códigos y devueltas/): 6 preguntas;
    devueltas = {experto: {código: «sí»|«parcial»|«no»|«»}}. Devuelve el sha256 del manifest y {nombre del CSV: sha256}."""
    clave = {"filas": [{"codigo": f"E{i:02d}", "id": q, "tipo": TIPO[q]} for i, q in enumerate(QIDS[:6], 1)]}
    sx = escribir(X / "clave_codigos_experto.json", clave)
    si = escribir(X / "instrucciones_experto.md", "instrucciones de juguete\n")
    sm = escribir(X / "manifest.txt", f"{sx}  clave_codigos_experto.json\n{si}  instrucciones_experto.md\n")
    shas = {}
    for e, rs in devueltas.items():
        s = io.StringIO()
        csv.writer(s, quoting=csv.QUOTE_ALL, lineterminator="\r\n").writerows(
            [COLUMNAS_EXPERTO] + [[f["codigo"], "", "", "", "sí", rs.get(f["codigo"], "sí"), "3", "", ""] for f in clave["filas"]])
        shas[f"{e}.csv"] = escribir(X / "devueltas" / f"{e}.csv", ("﻿" + s.getvalue()).encode("utf-8"))
    return sm, shas


@contextlib.contextmanager
def en(W: Path):
    previo = os.getcwd()
    os.chdir(W)
    try:
        yield
    finally:
        os.chdir(previo)


def correr(rutas: dict, esp: dict, W: Path, salida: Path, n_perm=B.N_PERM, n_boot=B.N_BOOT):
    """El análisis sobre un mundo, desde la carpeta del mundo; devuelve (salida, freno, lo impreso)."""
    buf = io.StringIO()
    with en(W):
        try:
            with contextlib.redirect_stdout(buf):
                out = B.analizar(rutas, esp, salida, n_perm=n_perm, n_boot=n_boot)
            return out, None, buf.getvalue()
        except A.Freno as ex:
            return None, str(ex), buf.getvalue()


def m_de(f) -> dict:
    """Una métrica de juguete: {(qid, brazo): (correctas, 3)} con f(qid, brazo) correctas."""
    return {(q, b): (f(q, b), 3) for q in QIDS for b in B.BRAZOS}


P64 = {q: {"tipo": TIPO[q], "to": DOC[q]} for q in QIDS}


def huellas(rutas_codigo: list[Path]) -> dict:
    return {p.name: sha(p) for p in rutas_codigo}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clon", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--informe", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.trabajo.exists() or a.informe.exists():
        raise SystemExit("--trabajo y --informe no pueden existir")
    T = a.trabajo.resolve()
    T.mkdir(parents=True)
    clon = a.clon.resolve()
    AP, JB = A.importar(clon, B.ESPERADO_CODIGO)
    K = JB.K
    S63 = importar_selftest_b63()
    importados = [B.CODIGO_B63 / n for n in B.SELLADO] + [B.CODIGO_B63 / "selftest_analizar_b63.py"] + [
        Path(m.__file__) for m in (JB, K, JB.M, JB.J, JB.J.lc)] + [clon.parents[2] / "lectura_tolerante_juez.py"]
    antes = huellas(importados)
    constantes = json.dumps({k: getattr(A, k) for k in ("SEMILLAS", "BRAZOS", "TIPOS", "FRAGMENTOS", "ALFA", "N_PERM", "N_BOOT")}
                            | {"ESCENARIOS": {k: {e: list(v) if v else v for e, v in x.items()} for k, x in A.ESCENARIOS.items()}},
                            sort_keys=True)
    R: dict = {}
    frenos: dict = {}

    def control(nombre, cond):
        R[nombre] = "PASS" if cond else "FAIL"

    # --- Lo importado de B6.3 ------------------------------------------------------------------------------------------ #
    control("importado_byte_a_byte_lo_sellado",
            all(sha(B.CODIGO_B63 / n) == s for n, s in B.SELLADO.items())
            and all(Path(sys.modules[n].__file__).resolve() == (B.CODIGO_B63 / f"{n}.py").resolve()
                    for n in ("analizar_b63", "aplicar_lectura_tolerante_b63", "armar_adjudicacion_b63"))
            and sha(Path(JB.__file__)) == A.ESPERADO["juez_b63"] and sha(Path(JB.M.__file__)) == A.ESPERADO["mapping"]
            and AP is B.AP_SELLADO and A.importar.__module__ == "analizar_b63")
    control("analizar_b64_sin_copias_de_lo_importado",
            not any(hasattr(B, n) for n in ("permutacion", "holm", "afirmacion", "bootstrap", "metricas", "percentil", "seis",
                                            "estado_de", "adjudicar", "planilla_sellada", "corridas_de", "Banco")))

    # --- La permutación, Holm y el bootstrap contra B6.3, con sus datos de juguete ----------------------------------- #
    P63 = {q: {"tipo": "varios_puntos" if q in S63.SUBTIPO else "dato_directo", "subtipo": S63.SUBTIPO.get(q), "to": S63.DOC[q]}
           for q in S63.QIDS}
    sem63 = dict(A.SEMILLAS, bootstrap_correccion="B63:no_se_usa")
    otro_sorteo = []
    for nombre, op in (("A", {}), ("B", {"denso_malo": True})):
        corridas63 = [{"qid": q, "r": r, "brazo": b, "estado": FINAL_A_ESTADO[v["final"]]} for (q, r, b), v in S63.diseno(op).items()]
        m63 = A.metricas(corridas63, "principal")
        r63 = A.confirmatorio(S63.QIDS, m63, P63, {}, B.N_PERM, B.N_BOOT, por_documento=True)
        r64 = B.confirmatorio(S63.QIDS, m63, P63, B.N_PERM, B.N_BOOT, por_documento=True, semillas=sem63, tipos=A.TIPOS,
                              brazos=A.BRAZOS, cuarto=False)
        sin = lambda x: {k: v for k, v in x.items() if k != "afirmacion"}  # noqa: E731
        claves_boot = {k: v for k, v in r63["remuestreos_sin_cifra"].items() if not k.startswith(("secundaria", "ponderado"))}
        control(f"contra_B63_{nombre}_con_sus_semillas_da_lo_mismo",
                r64["por_comparacion"] == r63["por_comparacion"] and sin(r64["afirmacion_principal"]) == r63["afirmacion_principal"]
                and r64["por_brazo"] == r63["por_brazo"] and r64["por_tipo"] == r63["por_tipo"] and r64["preguntas"] == r63["preguntas"]
                and r64["preguntas_que_salen_por_comparacion"] == r63["preguntas_que_salen_por_comparacion"]
                and r64["remuestreos_sin_cifra"] == claves_boot
                and all(r64["por_documento"]["por_comparacion"][f][k] == r63["por_documento"]["por_comparacion"][f][k]
                        for f in A.FRAGMENTOS for k in ("permutacion", "holm"))
                and r64["por_documento"]["afirmacion_principal"] == r63["por_documento"]["afirmacion_principal"]
                and r64["por_documento"]["la_misma_conclusion"]["principal"] == r63["por_documento"]["la_misma_conclusion"]["principal"])
        b64 = B.confirmatorio(S63.QIDS, m63, P63, B.N_PERM, B.N_BOOT, por_documento=True, tipos=A.TIPOS, brazos=A.BRAZOS, cuarto=False)
        ok = b64["afirmacion_principal"]["el_grafo_supera_a_los_fragmentos"] == r63["afirmacion_principal"]["el_grafo_supera_a_los_fragmentos"]
        boot = A.bootstrap(S63.QIDS, lambda q: [q], A.Estadisticas(P63, {}), m63, "B64:bootstrap:v1", B.N_BOOT, B.CUANTILES)
        docs = sorted(set(S63.DOC.values()))
        de_doc = {x: [q for q in S63.QIDS if S63.DOC[q] == x] for x in docs}
        bdoc = A.bootstrap(docs, lambda x: de_doc[x], A.Estadisticas(P63, {}), m63, "B64:bootstrap:documento:v1", B.N_BOOT, B.CUANTILES)
        ps = {}
        for f in A.FRAGMENTOS:
            qs = A.preguntas_de(S63.QIDS, m63, ("kg", f))
            pr = A.permutacion([A.d6(m63, q, f) for q in qs], "B64:permutacion:v1", B.N_PERM)
            ps[f] = pr["p"]
            ok &= b64["por_comparacion"][f]["permutacion"] == pr and b64["por_comparacion"][f]["intervalo_95"] == A.intervalo(boot, f"d|{f}")
            sumas = [sum(A.d6(m63, q, f) for q in de_doc[x] if (q, "kg") in m63 and (q, f) in m63) for x in docs]
            pd = A.permutacion(sumas, "B64:permutacion:documento:v1", B.N_PERM)
            ok &= b64["por_documento"]["por_comparacion"][f]["permutacion"]["mayores_o_iguales"] == pd["mayores_o_iguales"]
            ok &= b64["por_documento"]["por_comparacion"][f]["intervalo_95"] == A.intervalo(bdoc, f"d|{f}")
            for t in A.TIPOS:
                ok &= b64["por_tipo"][t]["por_comparacion"][f]["intervalo_95"] == A.intervalo(boot, f"d|{f}|{t}")
            otro_sorteo.append(b64["por_comparacion"][f]["permutacion"]["mayores_o_iguales"] != r63["por_comparacion"][f]["permutacion"]["mayores_o_iguales"])
            otro_sorteo.append(b64["por_documento"]["por_comparacion"][f]["permutacion"]["mayores_o_iguales"]
                               != r63["por_documento"]["por_comparacion"][f]["permutacion"]["mayores_o_iguales"])
        ok &= b64["por_comparacion"]["fragmentos_hibrida"]["holm"] == A.holm(ps)["fragmentos_hibrida"]
        ok &= all(b64["por_brazo"][b]["intervalo_95"] == A.intervalo(boot, f"media|{b}") for b in A.BRAZOS)
        control(f"contra_B63_{nombre}_con_las_semillas_de_B64_son_las_funciones_de_B63", ok)
    control("contra_B63_las_semillas_de_B64_dan_otro_sorteo", any(otro_sorteo))

    # --- La afirmación principal en sus casos, y el cuarto brazo fuera de Holm y de la afirmación ------------------- #
    casos = {"supera_a_las_dos": m_de(lambda q, b: {"kg": 3, "fragmentos_hibrida": 0, "fragmentos_denso": 0, "kg_n7": 1}[b]),
             "no_supera_a_ninguna": m_de(lambda q, b: 2),
             "holm_a_favor_de_los_fragmentos": m_de(lambda q, b: {"kg": 0, "fragmentos_hibrida": 3, "fragmentos_denso": 3, "kg_n7": 1}[b])}
    o = {k: B.confirmatorio(QIDS, m, P64, **CHICO) for k, m in casos.items()}
    control("afirmacion_supera_a_las_dos", o["supera_a_las_dos"]["afirmacion_principal"]["el_grafo_supera_a_los_fragmentos"] is True
            and o["supera_a_las_dos"]["afirmacion_principal"]["por_configuracion"] == {"fragmentos_denso": True, "fragmentos_hibrida": True}
            and all(o["supera_a_las_dos"]["por_comparacion"][f]["holm"]["rechaza"] for f in B.FRAGMENTOS))
    control("afirmacion_no_supera_a_ninguna", o["no_supera_a_ninguna"]["afirmacion_principal"]["el_grafo_supera_a_los_fragmentos"] is False
            and o["no_supera_a_ninguna"]["afirmacion_principal"]["por_configuracion"] == {"fragmentos_denso": False, "fragmentos_hibrida": False}
            and "regla" in o["no_supera_a_ninguna"]["afirmacion_principal"])
    control("afirmacion_holm_a_favor_de_los_fragmentos_no_cuenta",
            all(o["holm_a_favor_de_los_fragmentos"]["por_comparacion"][f]["holm"]["rechaza"] for f in B.FRAGMENTOS)
            and o["holm_a_favor_de_los_fragmentos"]["afirmacion_principal"]["por_configuracion"] == {"fragmentos_denso": False,
                                                                                                     "fragmentos_hibrida": False})
    m1 = m_de(lambda q, b: {"kg": 3, "fragmentos_hibrida": 0, "fragmentos_denso": 0, "kg_n7": 3}[b])
    m2 = m_de(lambda q, b: {"kg": 3, "fragmentos_hibrida": 0, "fragmentos_denso": 0, "kg_n7": 0}[b])
    o1, o2 = B.confirmatorio(QIDS, m1, P64, **CHICO), B.confirmatorio(QIDS, m2, P64, **CHICO)
    partes = ("por_comparacion", "afirmacion_principal", "por_documento", "preguntas_que_salen_por_comparacion")
    bc = A.bootstrap(QIDS, lambda q: [q], DLocal(B.CUARTO_BRAZO), m2, "B64:bootstrap:correccion:v1", CHICO["n_boot"], B.CUANTILES)
    control("el_cuarto_brazo_no_entra_en_holm_ni_en_la_afirmacion",
            all(json.dumps(o1[k], sort_keys=True) == json.dumps(o2[k], sort_keys=True) for k in partes)
            and sorted(o1["por_comparacion"]) == sorted(B.FRAGMENTOS) and sorted(o1["por_documento"]["por_comparacion"]) == sorted(B.FRAGMENTOS)
            and o1["cuarto_brazo"]["por_comparacion"]["kg-kg_n7"]["media_d"] == 0 and o2["cuarto_brazo"]["por_comparacion"]["kg-kg_n7"]["media_d"] == 1
            and o2["cuarto_brazo"]["fuera_de_holm_y_de_la_afirmacion"] is True and "permutacion" not in o2["cuarto_brazo"]["por_comparacion"]["kg-kg_n7"])
    control("el_cuarto_brazo_con_su_intervalo_y_su_semilla",
            all(cerca(o2["cuarto_brazo"]["por_comparacion"][n]["intervalo_95"], A.intervalo(bc, f"d|{n}")) for n in B.CUARTO_BRAZO))

    # --- El mundo de B6.4: la lectura tolerante, la adjudicación y el análisis ----------------------------------------- #
    W = T / "mundo"
    rutas, esp, info = mundo(W, JB, K, clon)
    d = info["diseno"]
    lt = json.loads(info["aplicar_consola"].splitlines()[0]) if info["aplicar_consola"] else {}
    control("lectura_tolerante_b63_corre_sin_cambios_con_cuatro_brazos", info["aplicar_codigo"] == 0 and lt.get("prueba_da") is True
            and lt.get("prueba") == {f"P{i}": "PASS" for i in range(1, 9)})
    inf_lt = json.loads((W / "aplicacion" / "informe_lectura_tolerante_b63.json").read_text(encoding="utf-8")) if info["aplicar_codigo"] == 0 else {}
    control("una_salida_que_la_estricta_no_lee_y_la_tolerante_si", inf_lt.get("las_que_no_se_leian") == [[info["ids"][TOLERANTE], 2]]
            and inf_lt.get("prueba", {}).get("P5", {}).get("leidas") == 1 and inf_lt["prueba"]["P5"]["no_leidas"] == 0)
    clave = info["clave"]["fichas"]
    control("dos_van_a_la_adjudicacion_con_el_armado_de_B64", info["armar_codigo"] == 0 and len(clave) == 2
            and sorted((f["pregunta"], f["repeticion"], f["brazo"]) for f in clave) == sorted(ADJUDICADAS)
            and all(f["criterios_que_se_adjudican"] == [ADJUDICADAS[(f["pregunta"], f["repeticion"], f["brazo"])][0]] for f in clave)
            and json.loads(info["armar_consola"]) == {"respuestas_a_la_adjudicacion": 2, "criterios_que_marca_la_autora": 2})
    PL = W / "adjudicacion" / "para_leer"
    textos = "".join(p.read_text(encoding="utf-8") for p in sorted(PL.rglob("*")) if p.suffix in (".md", ".py"))
    control("el_material_de_la_adjudicacion_es_de_B64", "B6.4" in textos and "B6.3" not in textos.replace("como en B6.3", "")
            .replace("la de B6.3", "") and "b63" not in textos and (PL / Z.SELLADOR_NOMBRE).is_file())
    control("el_sellador_de_B64_sella_y_el_analisis_lo_acepta", info["sellador"] == {"codigo": 0, "sello": True, "lo_acepta_el_analisis": True})

    oP, fP, impP = correr(rutas, esp, W, T / "salida_principal")
    oP2, fP2, impP2 = correr(rutas, esp, W, T / "salida_principal_bis")
    control("analisis_corre_sin_freno", fP is None and fP2 is None)
    if fP is not None or fP2 is not None:
        frenos["principal"] = fP or fP2
    else:
        bP = (T / "salida_principal" / "analisis_B64.json").read_bytes()
        R["sha256_salida_principal"] = sha_b(bP)
        control("analisis_dos_corridas_iguales_byte_a_byte", bP == (T / "salida_principal_bis" / "analisis_B64.json").read_bytes())
        control("analisis_no_imprime_nada", impP == "" and impP2 == "")
        control("analisis_parametros_del_preregistro", oP["parametros"]["permutaciones"] == 100_000 and oP["parametros"]["remuestreos"] == 10_000
                and oP["parametros"]["semillas"] == {"permutacion": "B64:permutacion:v1", "bootstrap": "B64:bootstrap:v1",
                                                     "bootstrap_correccion": "B64:bootstrap:correccion:v1",
                                                     "permutacion_documento": "B64:permutacion:documento:v1",
                                                     "bootstrap_documento": "B64:bootstrap:documento:v1"}
                and oP["parametros"]["alfa_holm"] == [0.025, 0.05] and oP["parametros"]["brazos"] == list(B.BRAZOS)
                and oP["parametros"]["tipos"] == list(B.TIPOS))
        # los estados de las corridas
        esperado_estados = {}
        for (q, r, b), v in d.items():
            k = f"{b} | {FINAL_A_ESTADO[v['final']]}"
            esperado_estados[k] = esperado_estados.get(k, 0) + 1
        control("estados_por_brazo_con_la_tolerante_y_la_adjudicacion", oP["corridas_por_brazo_y_estado"] == dict(sorted(esperado_estados.items()))
                and sum(esperado_estados.values()) == 144)
        # las métricas de cada escenario contra las esperadas, y la p contra la exacta
        for esc in A.ESCENARIOS:
            m = esperadas(d, esc)
            C = oP["confirmatorio"][esc]
            ok = all(cerca(C["por_brazo"][b]["media"], media(m[(q, b)] for q in QIDS if (q, b) in m)) for b in B.BRAZOS)
            for t in B.TIPOS:
                ok &= all(cerca(C["por_tipo"][t]["por_brazo"][b]["media"], media(m[(q, b)] for q in QIDS if TIPO[q] == t and (q, b) in m))
                          for b in B.BRAZOS)
            for f in B.FRAGMENTOS:
                ds = [m[(q, "kg")] - m[(q, f)] for q in QIDS if (q, "kg") in m and (q, f) in m]
                ok &= C["por_comparacion"][f]["preguntas"] == len(ds) and cerca(C["por_comparacion"][f]["media_d"], media(ds))
                ok &= abs(C["por_comparacion"][f]["permutacion"]["p"] - S63.p_exacta([int(6 * x) for x in ds])) < 0.01
            for n, (x, y) in B.CUARTO_BRAZO.items():
                ok &= cerca(C["cuarto_brazo"]["por_comparacion"][n]["media_d"], media(m[(q, x)] - m[(q, y)] for q in QIDS))
            control(f"metricas_y_p_como_las_esperadas_{esc}", ok)
        Pr = oP["confirmatorio"]["principal"]
        control("afirmacion_supera_a_una_sola", Pr["afirmacion_principal"]["el_grafo_supera_a_los_fragmentos"] is False
                and Pr["afirmacion_principal"]["por_configuracion"] == {"fragmentos_denso": False, "fragmentos_hibrida": True}
                and Pr["por_comparacion"]["fragmentos_hibrida"]["holm"] == {"p": Pr["por_comparacion"]["fragmentos_hibrida"]["permutacion"]["p"],
                                                                            "umbral": 0.025, "rechaza": True}
                and Pr["por_comparacion"]["fragmentos_denso"]["holm"]["umbral"] == 0.05
                and Pr["afirmacion_principal"]["afirmacion"] == B.AFIRMACION)
        control("las_sensibilidades_sin_la_version_por_documento", "por_documento" in Pr
                and all("por_documento" not in oP["confirmatorio"][e] for e in ("sin_las_cortadas", "sin_veredicto_como_no_correctas")))
        # la robustez por documento
        mP = esperadas(d, "principal")
        D = Pr["por_documento"]
        docs = sorted(set(DOC.values()))
        ok = D["documentos"] == 4
        bdl = A.bootstrap(docs, lambda x: [q for q in QIDS if DOC[q] == x], DLocal(B.COMPARACIONES),
                          {k: (v.numerator, v.denominator) for k, v in mP.items()}, "B64:bootstrap:documento:v1", B.N_BOOT, B.CUANTILES)
        for f in B.FRAGMENTOS:
            sumas = [int(6 * sum(mP[(q, "kg")] - mP[(q, f)] for q in QIDS if DOC[q] == x)) for x in docs]
            ok &= abs(D["por_comparacion"][f]["permutacion"]["p"] - S63.p_exacta(sumas)) < 0.01
            ok &= cerca(D["por_comparacion"][f]["intervalo_95"], A.intervalo(bdl, f"d|{f}"))
        control("por_documento_p_contra_la_exacta_y_su_intervalo", ok and set(D["la_misma_conclusion"]) == {"principal", "afirmacion"}
                and D["la_misma_conclusion"]["principal"] == {"fragmentos_denso": True, "fragmentos_hibrida": False})
        # lo operativo
        op_ = oP["operativo"]
        control("operativo_por_brazo_y_por_tipo", op_["por_brazo"]["kg_n7"]["mas_de_30_llamadas"] == 1
                and op_["por_brazo"]["kg_n7"]["al_tope_30_o_mas"] == 2 and op_["por_brazo"]["kg_n7"]["cortadas"] == 1
                and op_["por_brazo"]["kg"]["mas_de_30_llamadas"] == 0 and op_["por_brazo"]["kg"]["cortadas"] == 0
                and op_["por_brazo_y_tipo"]["kg_n7"]["agregacion"]["al_tope_30_o_mas"] == 2
                and op_["por_brazo_y_tipo"]["kg_n7"]["remision"]["al_tope_30_o_mas"] == 0
                and op_["por_brazo_y_tipo"]["fragmentos_denso"]["agregacion"]["incompleta_otra"] == 1
                and op_["por_brazo"]["fragmentos_hibrida"]["infra"] == {"sin_terminar": 1, "con_mas_de_un_intento": 1, "intentos_de_mas": 2}
                and op_["por_brazo_y_tipo"]["fragmentos_hibrida"]["remision"]["infra"]["sin_terminar"] == 1
                and all(op_["por_brazo"][b]["sesiones"] == 36 for b in B.BRAZOS)
                and all(op_["por_brazo_y_tipo"][b][t]["sesiones"] == 12 for b in B.BRAZOS for t in B.TIPOS)
                and op_["por_brazo"]["kg"]["contexto_maximo"]["maximo"] == 210)
        # lo declarado
        dc = oP["declarado"]
        cero = {b: 0 for b in B.BRAZOS}
        control("declarado_lectura_tolerante_por_brazo", dc["lectura_tolerante_por_brazo"] == {"salidas_por_brazo": cero | {"kg_n7": 1},
                                                                                              "respuestas_por_brazo": cero | {"kg_n7": 1}}
                and dc["adjudicadas_por_brazo"] == {"fragmentos_hibrida": 1, "kg": 1})
        control("declarado_marcas_del_brazo_y_fechas", set(dc["D10_por_brazo"]) == set(B.BRAZOS) and dc["bloques_con_fechas_distintas"] == 0
                and set(dc["textos"]) == set(B.DECLARADO) and dc["incompleta_otra"]["por_brazo"] == {"fragmentos_denso": 1})
        control("declarado_anclas_fuera_de_los_46", dc["anclas_fuera_de_los_46"] == {
            "anclas": 28, "fuera_de_los_46": 3, "preguntas_con_alguna_fuera": 3, "en_ninguna_de_esas_clases": 1,
            "por_clase": {"N3": 1, "anclas_de_las_96_de_B63": 1, "evaluacion_final": 1, "tanda_0": 0},
            "por_tipo": {"agregacion": 0, "remision": 3, "condicion_excepcion": 0}})
        lc = dc["lugares_que_cambiaron"]
        control("declarado_lugares_que_cambiaron", lc["lugares"] == 12
                and lc["cambian_de_unidad"] == {"total": 3, "por_tipo": {"agregacion": 3, "remision": 0, "condicion_excepcion": 0}}
                and lc["cambian_de_documento"]["total"] == 2 and lc["cambian_de_clase"]["total"] == 1
                and lc["por_clase_sorteada"]["NG_necesita_reglas"] == {"lugares": 4, "cambian_de_unidad": 1, "cambian_de_documento": 1,
                                                                       "cambian_de_clase": 1}
                and lc["por_clase_sorteada"]["NG_digerible"]["cambian_de_documento"] == 1 and lc["por_clase_sorteada"]["RI"]["lugares"] == 3)
        control("expertos_sin_devolucion_se_declara", oP["expertos"]["datos"] is False and "sensibilidad_sin_las_incorrectas" not in oP["expertos"])
        # la corrección del H-6: la decisión 1, en lo declarado y en el código; y, sin salidas sin lectura, el sellado tal cual
        tx = dc["textos"]["las_cuatro_elecciones_del_H6"]
        control("d1_las_cuatro_elecciones_en_lo_declarado_con_la_decision_tal_cual", tx.startswith(DECISION_1)
                and all(x in tx for x in ("B64:adjudicacion:v1", "B64:bootstrap:documento:v1", "B64:bootstrap:correccion:v1",
                                          "clases_documentos", "lugares"))
                and Z.SEMILLA == "B64:adjudicacion:v1" and info["clave"]["semilla"] == "B64:adjudicacion:v1"
                and oP["parametros"]["semillas"]["bootstrap_documento"] == "B64:bootstrap:documento:v1"
                and oP["parametros"]["semillas"]["bootstrap_correccion"] == "B64:bootstrap:correccion:v1"
                and set(Pr["por_documento"]["por_comparacion"]["fragmentos_hibrida"]) >= {"intervalo_95"}
                and set(Pr["cuarto_brazo"]["por_comparacion"]) == set(B.CUARTO_BRAZO)
                and oP["entradas"]["clases_documentos"] == esp["clases_documentos"] and oP["entradas"]["lugares"] == esp["lugares"])
        env = json.loads((W / "informe_envoltorio_aplicacion.json").read_text(encoding="utf-8"))
        sl = json.loads((W / "aplicacion" / ENV.SIN_LECTURA).read_text(encoding="utf-8"))
        control("d3_sin_salidas_sin_lectura_el_sellado_corre_sobre_banco_b64_tal_cual",
                env["sin_lectura"]["salidas"] == 0 and env["vista"] is None and all(env["controles"].values())
                and env["sellado"] == {"modo": "salida", "codigo_de_salida": 0} and sl["agregados"] == [] and sl["salidas"] == []
                and inf_lt["entradas"]["resultados/real/estado_b63.json"] == sha(W / "banco_b64" / "resultados" / "real" / "estado_b63.json")
                and dc["sin_lectura_a_la_adjudicacion"] == {"respuestas_por_brazo": cero, "salidas_por_brazo": cero,
                                                            "salidas_por_motivo": {}, "adjudicadas": 0})

    # --- La sensibilidad de los expertos, con devolución -------------------------------------------------------------- #
    X2 = W / "expertos_dos"
    sm2, dv2 = material_expertos(X2, {"experto_1": {"E01": "no", "E02": "no"}, "experto_2": {"E01": "no", "E02": "sí"}})
    o2_, f2_, _ = correr(rutas | {"expertos": X2}, esp | {"manifiesto_expertos": sm2, "devueltas": dv2}, W, T / "salida_expertos_dos", **CHICO)
    control("expertos_con_dos_los_dos", f2_ is None and o2_["expertos"]["datos"] is True and o2_["expertos"]["incorrectas"] == [QIDS[0]]
            and o2_["expertos"]["incorrectas_n_de_N"] == "1 de 6"
            and o2_["expertos"]["sensibilidad_sin_las_incorrectas"]["salen"] == 1
            and o2_["expertos"]["sensibilidad_sin_las_incorrectas"]["analisis"]["preguntas"] == 11
            and o2_["expertos"]["sensibilidad_sin_las_incorrectas"]["fuera_de_holm"] is True
            and "por_documento" not in o2_["expertos"]["sensibilidad_sin_las_incorrectas"]["analisis"]
            and o2_["confirmatorio"]["principal"]["afirmacion_principal"] == oP["confirmatorio"]["principal"]["afirmacion_principal"]
            if f2_ is None and oP else False)
    if f2_ is not None:
        frenos["expertos_dos"] = f2_
    X1, X3 = T / "expertos_uno", T / "expertos_tres"
    sm1, dv1 = material_expertos(X1, {"experto_1": {"E01": "no", "E02": "parcial"}})
    sm3, dv3 = material_expertos(X3, {"experto_1": {"E01": "no", "E02": "no", "E03": "no"}, "experto_2": {"E01": "no", "E02": "sí", "E03": "no", "E04": ""},
                                      "experto_3": {"E01": "sí", "E02": "sí", "E03": "no", "E04": ""}})
    e1 = B.expertos(X1, {"manifiesto_expertos": sm1, "devueltas": dv1}, QIDS)
    e3 = B.expertos(X3, {"manifiesto_expertos": sm3, "devueltas": dv3}, QIDS)
    control("expertos_con_uno_su_no", e1["incorrectas"] == [QIDS[0]] and e1["por_experto"]["experto_1"]["la_respuesta_es_correcta"]
            == {"si": "4 de 6", "parcial": "1 de 6", "no": "1 de 6"})
    control("expertos_con_tres_por_mayoria", e3["incorrectas"] == [QIDS[0], QIDS[2]] and e3["incorrectas_n_de_N"] == "2 de 6"
            and e3["por_experto"]["experto_2"]["la_respuesta_es_correcta"]["no"] == "2 de 5")

    # --- La corrección del H-6, decisión 3: salidas del juez que no lee ninguna lectura -------------------------------- #
    W3 = T / "mundo_sin_lectura"
    rutas3, esp3, info3 = mundo(W3, JB, K, clon, sin_lectura=SIN_LECTURA)
    d3, ids3 = info3["diseno"], {k: info3["ids"][k] for k in SIN_LECTURA}
    argv3 = ["--salida-b63", str(W3 / "banco_b64"), "--entrada", "entrada_juguete.json", "--clon", str(clon), "--tmp", str(W3 / "tmp_pruebas")]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), en(W3):
        try:
            rc_s = B.AP_SELLADO.main(argv3 + ["--salida", str(W3 / "aplicacion_sin_envoltorio")])
        except SystemExit as ex:
            rc_s = f"SystemExit: {ex}"
    sale_s = json.loads(buf.getvalue().splitlines()[0]) if buf.getvalue() else {}
    control("d3_sin_el_envoltorio_el_sellado_no_escribe", rc_s == 1 and "P5" in sale_s.get("fallan", [])
            and not (W3 / "aplicacion_sin_envoltorio").exists())
    pruebas3 = []
    for n in (1, 2):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), en(W3):
            rc = ENV.main(argv3 + ["--informe", str(W3 / f"prueba_{n}.json"), "--informe-b64", str(W3 / f"prueba_envoltorio_{n}.json")])
        pruebas3.append((rc, (W3 / f"prueba_{n}.json").read_bytes(), (W3 / f"prueba_envoltorio_{n}.json").read_bytes()))
    inf3, env3 = json.loads(pruebas3[0][1]), json.loads(pruebas3[0][2])
    control("d3_el_envoltorio_las_encuentra_y_el_sellado_da_P1_a_P8_sobre_la_vista_dos_veces_igual",
            all(p[0] == 0 for p in pruebas3) and pruebas3[0][1:] == pruebas3[1][1:]
            and inf3["prueba_da"] is True and inf3["fallan"] == [] and inf3["las_que_no_se_leian"] == [[info3["ids"][TOLERANTE], 2]]
            and all(env3["controles"].values()) and env3["sin_lectura"]["salidas"] == 2 and env3["sin_lectura"]["respuestas"] == 2
            and env3["sin_lectura"]["por_motivo"] == {"la_tolerante_la_rechaza": 1, "max_tokens": 1}
            and sorted(map(tuple, env3["sin_lectura"]["las_salidas"])) == sorted((ids3[k], v["rep"], v["como"]) for k, v in SIN_LECTURA.items())
            and env3["vista"]["corridas_marcadas"] == 2 and env3["sellado"] == {"modo": "informe", "codigo_de_salida": 0})
    man3 = json.loads((W3 / "manifiesto_juguete.json").read_text(encoding="utf-8"))
    control("d3_lo_original_no_se_toca", all(sha(W3 / x["ruta"]) == x["sha256"] for x in man3["archivos"])
            and len(man3["archivos"]) == sum(1 for p in (W3 / "banco_b64").rglob("*") if p.is_file()))
    sl3 = json.loads((W3 / "aplicacion" / ENV.SIN_LECTURA).read_text(encoding="utf-8"))
    fichas3 = {(f["pregunta"], f["repeticion"], f["brazo"]): f for f in info3["clave"]["fichas"]}
    control("d3_van_enteras_a_la_adjudicacion_por_el_armado_de_B64", info3["aplicar_codigo"] == 0 and info3["armar_codigo"] == 0
            and sorted(x["id_opaco"] for x in sl3["agregados"]) == sorted(ids3.values())
            and all(x["veredicto_pregunta"] == "requiere_adjudicacion" and x["modales"] == ["sin_consenso"] * n_criterios(k[0])
                    for k in SIN_LECTURA for x in sl3["agregados"] if x["id_opaco"] == ids3[k])
            and sorted(fichas3) == sorted(list(ADJUDICADAS) + list(SIN_LECTURA))
            and all(fichas3[k]["lectura"] == "sin_lectura" and fichas3[k]["criterios_que_se_adjudican"] == list(range(1, n_criterios(k[0]) + 1))
                    and fichas3[k]["modal_del_juez_de_los_demas"] == {} for k in SIN_LECTURA)
            and json.loads(info3["armar_consola"]) == {"respuestas_a_la_adjudicacion": 4, "criterios_que_marca_la_autora": 6}
            and info3["sellador"] == {"codigo": 0, "sello": True, "lo_acepta_el_analisis": True})
    o3, f3, imp3 = correr(rutas3, esp3, W3, T / "salida_sin_lectura", **CHICO)
    control("d3_el_analisis_termina_y_escribe", f3 is None and imp3 == "" and (T / "salida_sin_lectura" / "analisis_B64.json").is_file())
    if f3 is None:
        est3 = {}
        for (q, r, b), v in d3.items():
            est3[f"{b} | {FINAL_A_ESTADO[v['final']]}"] = est3.get(f"{b} | {FINAL_A_ESTADO[v['final']]}", 0) + 1
        m3 = esperadas(d3, "principal")
        C3 = o3["confirmatorio"]["principal"]
        control("d3_su_veredicto_es_el_de_las_marcas_de_la_autora", o3["corridas_por_brazo_y_estado"] == dict(sorted(est3.items()))
                and not any("sin_veredicto" in k for k in o3["corridas_por_brazo_y_estado"])
                and d3[("JUG-B11", 2, "fragmentos_denso")]["final"] == "N" and d3[("JUG-B07", 3, "kg_n7")]["final"] == "C"
                and all(cerca(C3["por_brazo"][b]["media"], media(m3[(q, b)] for q in QIDS if (q, b) in m3)) for b in B.BRAZOS))
        cero3 = {b: 0 for b in B.BRAZOS}
        dc3 = o3["declarado"]
        control("d3_lo_declara_por_brazo", dc3["sin_lectura_a_la_adjudicacion"] == {
                    "respuestas_por_brazo": cero3 | {"fragmentos_denso": 1, "kg_n7": 1}, "salidas_por_brazo": cero3 | {"fragmentos_denso": 1, "kg_n7": 1},
                    "salidas_por_motivo": {"la_tolerante_la_rechaza": 1, "max_tokens": 1}, "adjudicadas": 2}
                and dc3["adjudicadas_por_brazo"] == {"fragmentos_denso": 1, "fragmentos_hibrida": 1, "kg": 1, "kg_n7": 1}
                and dc3["sin_veredicto"]["por_brazo"] == {}
                and dc3["textos"]["las_salidas_del_juez_que_no_se_leen"].startswith(DECISION_3)
                and "docs/preregistro_B6_3_evaluacion_final.md:907-910" in dc3["textos"]["las_salidas_del_juez_que_no_se_leen"]
                and ENV.DECISION.startswith(DECISION_3))
    else:
        frenos["sin_lectura"] = f3

    # --- Los frenos ---------------------------------------------------------------------------------------------------- #
    X4 = T / "expertos_sin_sha"
    sm4, _ = material_expertos(X4, {"experto_1": {"E01": "no"}})
    otros = info["otros"]
    casos_f = {
        "una_entrada_con_otro_sha256": ({}, {"agregados": "0" * 64}, "agregados no da su sha256"),
        "la_entrada_con_otro_sha256": ({}, {"entrada": "0" * 64}, "entrada no da su sha256"),
        "una_entrada_sin_su_sha256": ({}, {"lugares": None}, "lugares: sin su sha256"),
        "falta_un_brazo_en_la_entrada": ({"entrada": W / "entrada_tres_brazos.json"}, {"entrada": otros["entrada_tres_brazos"]},
                                         "los brazos de la entrada no son los cuatro de B6.4: falta ['kg_n7']"),
        "falta_un_brazo_en_el_D10": ({"d10": W / "d10_tres_brazos.json"}, {"d10": otros["d10_tres_brazos"]},
                                     "el D-10 no trae justo los cuatro brazos"),
        "una_devuelta_sin_su_sha256": ({"expertos": X4}, {"manifiesto_expertos": sm4}, "las planillas devueltas no son las del JSON"),
        "otro_sha256_para_el_codigo": ({}, {"mapping": "0" * 64}, "el JSON de los esperados trae otro sha256 para el código"),
        "las_sin_lectura_con_otro_sha256": ({}, {"agregados_sin_lectura": "0" * 64}, "agregados_sin_lectura no da su sha256"),
        "salida_que_ya_existe": ({}, {}, "--salida ya existe"),
    }
    for nombre, (cr, ce, texto) in casos_f.items():
        sal = T / ("salida_principal" if nombre == "salida_que_ya_existe" else f"salida_freno_{nombre}")
        antes_sal = sal.exists()
        of, ff, imp = correr(rutas | cr, esp | ce, W, sal, **CHICO)
        frenos[nombre] = ff
        control(f"freno_{nombre}", of is None and ff is not None and ff.startswith(texto) and imp == "" and sal.exists() == antes_sal)

    # --- El comando: main imprime solo la salida y su sha256 --------------------------------------------------------- #
    escribir(W / "esperado_juguete.json", esp)
    buf = io.StringIO()
    argv = []
    for k in B.ARGS:
        argv += ["--" + k.replace("_", "-"), str(rutas[k])]
    with en(W), contextlib.redirect_stdout(buf):
        rc = B.main(argv + ["--esperado", str(W / "esperado_juguete.json"), "--salida", str(T / "salida_por_main")])
    sale = buf.getvalue().strip()
    control("main_imprime_solo_la_salida_y_su_sha256", rc == 0 and sale == f"salida: salida_por_main/analisis_B64.json "
            f"({sha(T / 'salida_por_main' / 'analisis_B64.json')})" and "\n" not in sale)

    # --- Nada se editó --------------------------------------------------------------------------------------------- #
    control("nada_se_edito_en_lo_importado", huellas(importados) == antes and constantes == json.dumps(
        {k: getattr(A, k) for k in ("SEMILLAS", "BRAZOS", "TIPOS", "FRAGMENTOS", "ALFA", "N_PERM", "N_BOOT")}
        | {"ESCENARIOS": {k: {e: list(v) if v else v for e, v in x.items()} for k, x in A.ESCENARIOS.items()}}, sort_keys=True))

    informe = {"que": "la prueba de analizar_b64.py y armar_adjudicacion_b64.py, y de aplicar_lectura_tolerante_b63.py sin cambios por su "
                      "envoltorio aplicar_lectura_tolerante_b64.py, con datos de juguete (H-6 y su corrección)",
               "codigo": {**{n: sha(AQUI / n) for n in ("analizar_b64.py", "aplicar_lectura_tolerante_b64.py", "armar_adjudicacion_b64.py",
                                                        "selftest_analizar_b64.py")},
                          **{f"B6.3/{p.name}": s for p, s in zip(importados, antes.values())}},
               "controles": R, "frenos": frenos,
               "da": all(v == "PASS" for k, v in R.items() if not k.startswith("sha256_"))}
    a.informe.parent.mkdir(parents=True, exist_ok=True)
    a.informe.write_text(json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in R.items():
        if not k.startswith("sha256_"):
            print(f"{v}  {k}")
    print(f"prueba: {'PASS' if informe['da'] else 'FAIL'} ({sum(v == 'PASS' for v in R.values())} de "
          f"{sum(1 for k in R if not k.startswith('sha256_'))}); informe sha256 {sha_b(a.informe.read_bytes())}")
    return 0 if informe["da"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
