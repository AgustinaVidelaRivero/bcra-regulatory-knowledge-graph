#!/usr/bin/env python3
"""test_fragmentos_f1.py — Tests de las dos configuraciones de F1 del servidor de fragmentos
(U-NAV-DISENO, N5-F; mandato, §6 bis): la base (BM25 de A2.2 sobre el índice del acumulado) y la
híbrida (BM25 más el denso, fusionados con RRF, con los filtros por TO y por punto). Costo USD 0,
sin API. Grupos (--grupo, se pueden repetir; default: todos):

  rrf_a_mano       fusion_rrf contra fracciones calculadas a mano en casos chicos: el orden, un
                   empate exacto entre rangos distintos (que la suma en coma flotante no ve), la
                   profundidad y el corte por `limite`. Sin modelo.
  filtros_unidad   coincide_punto y la normalización de las entradas de filtro, en una tabla fija.
                   Sin modelo.
  indices          los dos índices del acumulado: sha del índice == manifiesto == config, el mismo
                   pasajes.json y el mismo manifiesto de E0 (por sha). Sin modelo.
  base_bm25        la config base contra la de A2.2: difieren solo en el índice; la misma tool;
                   transporte por MCP byte a byte, `limite` > 5 devuelve 5, log R1 consistente. Sin modelo.
  aislamiento_bm25 el código del servidor con la híbrida: sin imports ni rutas del grafo, sin
                   sockets; en modo BM25 el proceso no importa numpy, torch ni el modelo. Sin modelo.
  bm25_dos         la segunda construcción del índice BM25 del acumulado (construir_indice.py en un
                   directorio temporal) contra la servida: mismo sha y mismos rankings en una batería
                   fija (las consultas de A2.1 y tres por TO de la tanda 0). Sin modelo.
  denso_dos        lo mismo con la matriz densa: iguales byte a byte y mismos rankings. Necesita el
                   modelo (la construcción tarda del orden de media hora).
  hibrida_fusion   en el índice del acumulado, la salida híbrida == una RRF independiente sobre el
                   ranking BM25 y el denso enteros; los cinco primeros de cada ranking == los de su
                   modo propio (los de A2.2). Necesita el modelo.
  hibrida_filtros  `to`, `punto` y los dos juntos: todo resultado cumple el filtro, la salida ==
                   la RRF independiente sobre los pasajes que lo cumplen, la cuenta de filtrados, los
                   avisos y la normalización (mayúsculas, espacios, punto final). Necesita el modelo.
  hibrida_tope     el tope de `limite` (5) y el camino sin filtros (la misma forma de salida que
                   BM25, y lo mismo con filtros vacíos). Necesita el modelo.
  hibrida_transporte  la tool expuesta, el transporte por MCP byte a byte contra el cálculo
                   directo, el log R1 y el determinismo entre dos procesos. Necesita el modelo.
  tokens           tamaño por llamada, en caracteres y en tokens estimados como en el diseño de N2
                   (caracteres / 2,78, la mediana del tokenizador de Haiku 4.5 en las salidas de
                   herramientas; rango 2,56 a 2,98), sobre consultas de los TOs de la tanda 0; solo
                   cuentan las llamadas cuyos resultados son todos de la tanda 0. Necesita el modelo.

Grupos de `desde` (U-NAV-DESDE), sobre los índices de A2.1 (la tanda 0), no sobre los del acumulado,
con configuraciones de prueba en el directorio temporal (las de A2.1 con `parametro_desde: true`, y la
híbrida sobre esos dos índices, con y sin él):
  desde_definicion la tool sin `desde` es la de los controles sellados de A2.1; con `desde`, la misma más
                   la propiedad y el texto al final de la descripción; _desde; qué configuraciones lo
                   declaran (solo la híbrida de F1). Sin modelo.
  desde_bm25       desde=0 = sin desde en cada consulta; desde=k = las posiciones k a k + limite - 1 del
                   ranking entero (escrito aparte), con su `rank`, sin repetir las de desde=0 si k >= limite;
                   pedir desde = los ya vistos recorre el ranking; más allá del final, `aviso` y sin fallar;
                   los inválidos valen 0. Por MCP, con la config con parametro_desde y con la de A2.1: sin
                   desde y con desde=0, el sha256 del control sellado de A2.1; sin parametro_desde, `desde`
                   no se lee. Sin modelo.
  desde_denso      lo mismo en el modo denso. Necesita el modelo.
  desde_hibrida    lo mismo en la híbrida, con las consultas con filtros, contra la híbrida sin
                   parametro_desde; con filtros que no dejan pasajes, el aviso de los filtros queda; y,
                   informativo, el lugar de los pasajes de cla::6.5.5.4 y 6.5.5.5 en la fusión con to=cla.
                   Necesita el modelo.

Cegamiento (mandato, §7, regla 5): en la salida de estos tests, el id de un pasaje de un TO de la
tanda 1 va solo con los 12 primeros caracteres del sha256 de su id.

Uso (venv del servidor de fragmentos, requirements_vector.txt):
    python3 -B test_fragmentos_f1.py --out <json> [--grupo rrf_a_mano ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime
from fractions import Fraction
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
EXPERIMENT_DIR = BANCO_DIR.parent
REPO_DIR = EXPERIMENT_DIR.parents[1]
for _p in (str(BANCO_DIR), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import bm25_fragmentos as BM                                              # noqa: E402
import servidor_mcp_vector as SV                                          # noqa: E402
from cliente_falso import ClienteFalso                                   # noqa: E402
from comun_banco import cargar_config, rel_repo, serializar_payload, sha256_bytes, sha256_file  # noqa: E402

CONFIG_BASE = AQUI / "config_fragmentos_bm25_acumulado_r2b.json"
CONFIG_HIBRIDA = AQUI / "config_fragmentos_hibrida_acumulado_r2b.json"
CONFIG_BM25_A2 = AQUI / "config_fragmentos_bm25_r2b.json"
MCP_BASE, MCP_BM25_A2 = AQUI / "mcp_fragmentos_bm25_acumulado.json", AQUI / "mcp_fragmentos_bm25.json"
MCP_HIBRIDA, MCP_DENSO_A2 = AQUI / "mcp_fragmentos_hibrida_acumulado.json", AQUI / "mcp_fragmentos_denso.json"
MAN_E0 = AQUI / "manifiestos_e0" / "e0_acumulado_30tos_r2b.json"
MAN_ACUM = EXPERIMENT_DIR / "tanda1" / "t3" / "acumulado" / "manifiestos" / "acumulado_30tos_r2b.json"
N_PASAJES = 5729
CARACTERES_POR_TOKEN = (2.78, 2.56, 2.98)      # mediana, mínimo y máximo del diseño de N2 (Haiku 4.5)

# Las consultas propias de los tests de A2.1 (test_fragmentos_a2_1.CONSULTAS), tal cual.
CONSULTAS = [
    {"consulta": "¿qué requisitos debe cumplir una asociación mutual para operar con entidades financieras?"},
    {"consulta": "exigencia de efectivo mínimo en pesos", "limite": 5},
    {"consulta": "capital mínimo básico según la categoría de la entidad"},
    {"consulta": "cómo se clasifica a un deudor en situación 3", "limite": 3},
    {"consulta": "previsiones mínimas por riesgo de incobrabilidad"},
    {"consulta": "garantías preferidas A y B", "limite": 50},
    {"consulta": "acceso al mercado de cambios para pago de importaciones", "limite": "7"},
    {"consulta": "tope a la tasa de interés de financiaciones con tarjeta de crédito", "limite": 0},
    {"consulta": "   "},
    {"consulta": "plazo para informar incumplimientos de relaciones técnicas"},
    {"consulta": "de la que el en y a los del se", "limite": 5},
    {"consulta": "responsabilidad patrimonial computable", "limite": 6},
    {"consulta": "régimen informativo contable mensual", "limite": "abc"},
]
# Con filtros (solo la híbrida): TOs de la tanda 0, normalización, avisos y filtros vacíos.
CONSULTAS_FILTROS = [
    {"consulta": "capital mínimo básico según la categoría de la entidad", "to": "cap"},
    {"consulta": "cómo se clasifica a un deudor en situación 3", "to": "cla"},
    {"consulta": "acceso al mercado de cambios para pago de importaciones", "to": "ext", "limite": 50},
    {"consulta": "información que se debe dar al usuario antes de contratar", "to": "pro"},
    {"consulta": "capital mínimo", "to": "cap", "punto": "1"},
    {"consulta": "capital mínimo", "to": "cap", "punto": "1.1."},
    {"consulta": "capital mínimo", "to": " CAP ", "punto": " 1.1 "},
    {"consulta": "cuenta corriente bancaria", "punto": "1"},
    {"consulta": "capital mínimo", "to": "xyz"},
    {"consulta": "capital mínimo", "to": "cap", "punto": "999"},
    {"consulta": "   ", "to": "cap"},
    {"consulta": "capital mínimo", "to": "", "punto": "  "},
    {"consulta": "capital mínimo", "to": None, "punto": None},
]
LIMITES_ESPERADOS = [(None, 5), (3, 3), (5, 5), (6, 5), (10, 5), (50, 5), ("7", 5), (0, 1), ("abc", 5)]


# --------------------------------------------------------------------------- #
# Auxiliares                                                                  #
# --------------------------------------------------------------------------- #
def tos_tanda0() -> set[str]:
    """Los TOs de la tanda 0: los que tienen su chunks_<to>.json en la E0 de la tanda 0 que declara el
    manifiesto del acumulado (sellos.tanda0.e0.ruta)."""
    acum = json.loads(MAN_ACUM.read_text(encoding="utf-8"))
    d = REPO_DIR / acum["sellos"]["tanda0"]["e0"]["ruta"]
    return {t["id"] for t in acum["tos"] if (d / f"chunks_{t['id']}.json").exists()}


TANDA0 = tos_tanda0()


def mostrar_id(pid: str | None) -> str | None:
    """Cegamiento: el id de un pasaje de la tanda 1 va con los 12 primeros caracteres de su sha256."""
    if pid is None or pid.split("::")[0] in TANDA0:
        return pid
    return "t1:" + hashlib.sha256(pid.encode()).hexdigest()[:12]


def rrf_independiente(rankings: list[list[int]], ids: list[str], k: int = 60) -> list[tuple[int, Fraction]]:
    """Otra escritura de RRF para contrastar: un diccionario de rangos por ranking."""
    rangos = [{d: r for r, d in enumerate(rk, 1)} for rk in rankings]
    docs = set().union(*rangos) if rangos else set()
    puntaje = {d: sum((Fraction(1, k + rg[d]) for rg in rangos if d in rg), Fraction(0)) for d in docs}
    return sorted(puntaje.items(), key=lambda kv: (-kv[1], ids[kv[0]]))


def cargar_hibrida():
    config, config_sha = cargar_config(CONFIG_HIBRIDA)
    return SV.construir_indice_de(config), config, config_sha


def rankings_independientes(idx, consulta: str) -> tuple[list[int], list[int]]:
    """BM25: un Buscador nuevo desde el archivo del índice; denso: el orden por (-score, posición) con
    numpy (los pasajes están en orden canónico por id, así que la posición desempata como el id)."""
    import numpy as np
    if not hasattr(rankings_independientes, "_bus"):
        crudo = (idx.bm25.dir / "indice_bm25.json").read_text(encoding="utf-8")
        rankings_independientes._bus = BM.Buscador(json.loads(crudo))
    bus = rankings_independientes._bus
    s = bus.puntajes(BM.analizar(consulta))
    rb = [i for i, _ in sorted(s.items(), key=lambda kv: (-kv[1], bus.ids[kv[0]]))]
    S = idx.denso.E @ idx.denso.embed_consulta(consulta, con_prompt=True)
    rd = [int(i) for i in np.lexsort((np.arange(len(S)), -S))]
    return rb, rd


def esperado_hibrida(idx, consulta: str, limite: int, perm: set[int] | None) -> list[tuple[str, float]]:
    rb, rd = rankings_independientes(idx, consulta)
    if perm is not None:
        rb, rd = [i for i in rb if i in perm], [i for i in rd if i in perm]
    return [(idx.ids[i], round(float(s), 6)) for i, s in rrf_independiente([rb, rd], idx.ids)[:limite]]


def obtenido(obj: dict) -> list[tuple[str, float]]:
    return [(r["id"], r["score"]) for r in obj["resultados"]]


def patron_punto(p: str):
    return re.compile(r"^" + re.escape(p.casefold()) + r"(\.|::|$)")


# --------------------------------------------------------------------------- #
# Grupos sin modelo                                                           #
# --------------------------------------------------------------------------- #
def t_rrf_a_mano() -> dict:
    casos = []
    # A: dos rankings de cuatro documentos. d3: 1/61 + 1/62 = 123/3782; d2: 1/63 + 1/61 = 124/3843;
    #    d1: 1/62; d4: 1/63. 123/3782 > 124/3843 (123·3843 = 472.689 > 124·3782 = 468.968).
    ids = ["d1", "d2", "d3", "d4"]
    rk = [[2, 0, 1], [1, 2, 3]]
    esp = [(2, Fraction(123, 3782)), (1, Fraction(124, 3843)), (0, Fraction(1, 62)), (3, Fraction(1, 63))]
    casos.append({"caso": "A: orden", "esperado": [(ids[i], str(f)) for i, f in esp],
                  "ok": SV.fusion_rrf(rk, ids) == esp})
    # B: empate exacto entre rangos distintos: 1/66 + 1/99 = 1/72 + 1/88 = 5/198 (rangos 6 y 39 contra 12 y 28).
    #    Desempata el id: "b" (12 y 28) va antes que "c" (6 y 39). Los demás documentos son relleno, cada uno en
    #    un solo ranking (r1 usa x00..x36 y r2 x37..x73), así ninguno empata con 5/198 ni pasa por encima sin
    #    que se vea en el puntaje esperado.
    idsB = ["a", "b", "c"] + [f"x{j:02d}" for j in range(74)]
    r1, r2 = [None] * 40, [None] * 40
    r1[0], r2[0] = 0, 0          # a: rango 1 en los dos (2/61)
    r1[5], r2[38] = 2, 2         # c: rangos 6 y 39
    r1[11], r2[27] = 1, 1        # b: rangos 12 y 28
    relleno = iter(range(3, 3 + 74))
    r1 = [x if x is not None else next(relleno) for x in r1]
    r2 = [x if x is not None else next(relleno) for x in r2]
    fus = SV.fusion_rrf([r1, r2], idsB)
    pb = dict(fus)
    orden = [idsB[i] for i, _ in fus]
    flot_b, flot_c = 1 / 72 + 1 / 88, 1 / 66 + 1 / 99
    casos.append({"caso": "B: empate exacto 5/198", "puntaje_a": str(pb[0]), "puntaje_b": str(pb[1]),
                  "puntaje_c": str(pb[2]), "posiciones_a_b_c": [orden.index(x) + 1 for x in "abc"],
                  "en_coma_flotante_difieren": flot_b != flot_c, "coma_flotante_b_c": [repr(flot_b), repr(flot_c)],
                  "ok": (pb[0] == Fraction(2, 61) and pb[1] == pb[2] == Fraction(5, 198) and orden[0] == "a"
                         and orden.index("c") == orden.index("b") + 1)})
    # C: profundidad 2 sobre A: entran d3 y d1 de BM25 y d2 y d3 del denso. d3: 123/3782; d2: 1/61; d1: 1/62.
    esp = [(2, Fraction(123, 3782)), (1, Fraction(1, 61)), (0, Fraction(1, 62))]
    casos.append({"caso": "C: profundidad 2", "esperado": [(ids[i], str(f)) for i, f in esp],
                  "ok": SV.fusion_rrf(rk, ids, profundidad=2) == esp})
    # D: el corte por `limite` (heapq.nsmallest) == sorted(...)[:limite], en B y en A.
    cortes = [SV.fusion_rrf([r1, r2], idsB, limite=m) == fus[:m] for m in (1, 2, 3, 5, 10, 43, 60)]
    cortes += [SV.fusion_rrf(rk, ids, limite=m) == SV.fusion_rrf(rk, ids)[:m] for m in (1, 2, 4, 9)]
    casos.append({"caso": "D: limite", "n": len(cortes), "ok": all(cortes)})
    # E: un ranking vacío (BM25 sin términos) deja solo el otro; los dos vacíos, nada.
    casos.append({"caso": "E: rankings vacíos",
                  "ok": (SV.fusion_rrf([[], [3, 1]], ids) == [(3, Fraction(1, 61)), (1, Fraction(1, 62))]
                         and SV.fusion_rrf([[], []], ids) == [])})
    # F: la independiente da lo mismo en A, B y C.
    casos.append({"caso": "F: contra la escritura independiente",
                  "ok": (rrf_independiente(rk, ids) == SV.fusion_rrf(rk, ids)
                         and rrf_independiente([r1, r2], idsB) == fus)})
    cfg = json.loads(CONFIG_HIBRIDA.read_text(encoding="utf-8"))
    constantes = {"RRF_K": SV.RRF_K, "PROFUNDIDAD_RRF": SV.PROFUNDIDAD_RRF,
                  "config_rrf_k": cfg.get("rrf_k"), "config_profundidad_rrf": cfg.get("profundidad_rrf")}
    ok_c = SV.RRF_K == 60 == cfg.get("rrf_k") and SV.PROFUNDIDAD_RRF is None and cfg.get("profundidad_rrf", 0) is None
    return {"casos": casos, "constantes": constantes, "PASS": all(c["ok"] for c in casos) and ok_c}


def t_filtros_unidad() -> dict:
    tabla = [("1.1", "1.1", True), ("1.1.2", "1.1", True), ("1.10", "1.1", False), ("11.1", "1.1", False),
             ("1.1", "1.1.2", False), ("S2", "s2", True), ("S2", "S", False), ("A1B2::1.2", "A1B2", True),
             ("A1B2::1.2", "A1B2::1", True), ("A1B2::1.2", "A1B", False), ("1.4.2.1", "1", True), ("1", "1.", True)]
    filas = []
    for u, p, esp in tabla:
        pn = SV._filtro(p, punto=True)
        filas.append({"unidad": u, "punto": p, "esperado": esp, "ok": SV.coincide_punto(u, pn) == esp})
    norm = [(None, False, None), ("", False, None), ("   ", False, None), (" cap ", False, "cap"),
            ("6.5.", True, "6.5"), (" 6.5. ", True, "6.5"), (".", True, None), (6.5, True, "6.5"), ("CAP", False, "CAP")]
    filas_n = [{"entrada": repr(x), "punto": pt, "esperado": e, "ok": SV._filtro(x, punto=pt) == e} for x, pt, e in norm]
    return {"coincide_punto": filas, "normalizacion": filas_n,
            "PASS": all(f["ok"] for f in filas) and all(f["ok"] for f in filas_n)}


def t_indices() -> dict:
    cb, _ = cargar_config(CONFIG_BASE)
    ch, _ = cargar_config(CONFIG_HIBRIDA)
    dir_b, dir_d = (AQUI / ch["indice_dir_bm25"]).resolve(), (AQUI / ch["indice_dir_denso"]).resolve()
    mb = json.loads((dir_b / "manifiesto_indice.json").read_text(encoding="utf-8"))
    md = json.loads((dir_d / "manifiesto_indice.json").read_text(encoding="utf-8"))
    import numpy as np
    sha_m = hashlib.sha256(np.load(dir_d / "embeddings_docs.npy").astype("float32").tobytes(order="C")).hexdigest()
    sha_man_e0 = sha256_file(MAN_E0)
    r = {"bm25": {"dir": rel_repo(dir_b), "sha256_indice": sha256_file(dir_b / "indice_bm25.json"),
                  "manifiesto": mb["bm25"]["sha256_indice"], "config_base": cb["sha256_indice_esperado"],
                  "config_hibrida": ch["sha256_indice_esperado"], "misma_dir_base_e_hibrida":
                  (AQUI / cb["indice_dir"]).resolve() == dir_b, "n_docs": mb["bm25"]["n_docs"]},
         "denso": {"dir": rel_repo(dir_d), "sha256_matriz": sha_m, "manifiesto": md["matriz"]["sha256_matriz"],
                   "config_hibrida": ch["sha256_matriz_esperado"], "shape": md["matriz"]["shape"],
                   "n_truncados": md["agrupacion"]["n_truncados"], "modelo": md["modelo"]["repo"],
                   "revision": md["modelo"]["revision"]},
         "pasajes_json": {"bm25": sha256_file(dir_b / "pasajes.json"), "denso": sha256_file(dir_d / "pasajes.json")},
         "manifiesto_e0": {"archivo": sha_man_e0, "en_bm25": mb["manifiesto_e0"]["sha256"],
                           "en_denso": md["manifiesto_e0"]["sha256"], "n_pasajes": mb["corpus"]["n_pasajes"]}}
    r["PASS"] = (r["bm25"]["sha256_indice"] == r["bm25"]["manifiesto"] == r["bm25"]["config_base"]
                 == r["bm25"]["config_hibrida"] and r["bm25"]["misma_dir_base_e_hibrida"]
                 and r["denso"]["sha256_matriz"] == r["denso"]["manifiesto"] == r["denso"]["config_hibrida"]
                 and r["pasajes_json"]["bm25"] == r["pasajes_json"]["denso"]
                 and sha_man_e0 == r["manifiesto_e0"]["en_bm25"] == r["manifiesto_e0"]["en_denso"]
                 and r["manifiesto_e0"]["n_pasajes"] == md["corpus"]["n_pasajes"] == N_PASAJES
                 and md["matriz"]["shape"][0] == N_PASAJES and md["agrupacion"]["n_truncados"] == 0)
    return r


def transporte(config_path: Path, consultas: list[dict], log_path: Path, tag: str, idx=None) -> dict:
    config, config_sha = cargar_config(config_path)
    afinidad = config.get("afinidad", "denso")
    con_desde = config.get("parametro_desde", False)     # U-NAV-DESDE: el servidor solo lee `desde` si la config lo declara
    desde = lambda c: {"desde": c.get("desde", 0)} if con_desde else {}  # noqa: E731
    if idx is None:
        idx = SV.construir_indice_de(config)
    filas = []
    with ClienteFalso([sys.executable, "-B", str(AQUI / "servidor_mcp_vector.py"), "--config", str(config_path)],
                      env={"BANCO_LOG_R1": str(log_path), "BANCO_SESION_TAG": tag, "HF_HUB_OFFLINE": "1",
                           "TRANSFORMERS_OFFLINE": "1"}, timeout_s=900) as cli:
        tools = cli.listar_tools()
        for k, c in enumerate(consultas, 1):
            via = cli.llamar("buscar_pasajes", c)
            if afinidad == "hibrida":
                directo = serializar_payload(idx.buscar_pasajes(c.get("consulta", ""), c.get("limite", 10),
                                                                to=c.get("to"), punto=c.get("punto"), **desde(c)))
            else:
                directo = serializar_payload(idx.buscar_pasajes(c.get("consulta", ""), c.get("limite", 10), **desde(c)))
            obj = json.loads(via)
            filas.append({"k": k, "input": c, "chars_mcp": len(via), "n_resultados": len(obj["resultados"]),
                          "sha256_mcp": sha256_bytes(via.encode()), "igual": via == directo,
                          "todos_citan_to_y_unidad": all(r.get("to") and r.get("unidad") for r in obj["resultados"]),
                          "top1": mostrar_id(obj["resultados"][0]["id"] if obj["resultados"] else None),
                          "aviso": "aviso" in obj})
    lineas = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    llam = [l for l in lineas if l["evento"] == "llamada"]
    log_ok = (len(llam) == len(filas) and lineas[0]["evento"] == "inicio" and lineas[-1]["evento"] == "fin"
              and all(l["n"] == f["k"] and l["input"] == f["input"] and l["output_sha256"] == f["sha256_mcp"]
                      and l["config_sha256"] == config_sha for l, f in zip(llam, filas)))
    esperada = SV.definicion_tool(afinidad, int(config.get("limite_max", 50)), desde=con_desde)
    tool_ok = (len(tools) == 1 and tools[0]["name"] == esperada["name"] and tools[0]["description"] == esperada["description"]
               and tools[0]["input_schema"] == esperada["input_schema"])
    return {"config": rel_repo(config_path), "config_sha256": config_sha, "tools_expuestas": tools,
            "definicion_tool_esperada": tool_ok, "n": len(filas), "n_iguales": sum(f["igual"] for f in filas),
            "todos_citan": all(f["todos_citan_to_y_unidad"] for f in filas),
            "max_chars_resultado": max(f["chars_mcp"] for f in filas),
            "log_r1": {"ruta": rel_repo(log_path), "n_lineas": len(lineas), "consistente": log_ok,
                       "sha256_log": sha256_file(log_path), "fuente_inicio": lineas[0].get("fuente")},
            "llamadas": filas, "_idx": idx,
            "PASS": tool_ok and all(f["igual"] for f in filas) and all(f["todos_citan_to_y_unidad"] for f in filas) and log_ok}


def limites(idx, consulta: str, **filtros) -> dict:
    filas = []
    for pedido, esperado in LIMITES_ESPERADOS:
        n = len(idx.buscar_pasajes(consulta, 10 if pedido is None else pedido, **filtros)["resultados"])
        filas.append({"limite_pedido": pedido, "esperado": esperado, "devuelto": n, "ok": n == esperado})
    return {"consulta": consulta, "filtros": filtros, "filas": filas, "PASS": all(f["ok"] for f in filas)}


def t_base_bm25(logs: Path) -> dict:
    a, b = json.loads(CONFIG_BM25_A2.read_text(encoding="utf-8")), json.loads(CONFIG_BASE.read_text(encoding="utf-8"))
    distintas = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    mcp_a, mcp_b = MCP_BM25_A2.read_text(encoding="utf-8"), MCP_BASE.read_text(encoding="utf-8")
    mcp_solo_ruta = mcp_a.replace("config_fragmentos_bm25_r2b.json", "config_fragmentos_bm25_acumulado_r2b.json") == mcp_b
    mcp_h = MCP_DENSO_A2.read_text(encoding="utf-8").replace(
        "config_fragmentos_denso_r2b.json", "config_fragmentos_hibrida_acumulado_r2b.json") == MCP_HIBRIDA.read_text(encoding="utf-8")
    r = transporte(CONFIG_BASE, CONSULTAS, logs / "log_r1_test_f1_base_bm25.jsonl", "test_f1_base_bm25")
    idx = r.pop("_idx")
    r["limite"] = limites(idx, "capital mínimo básico según la categoría de la entidad")
    r["config"] = {"claves_distintas_de_A2_2": distintas,
                   "esperadas": ["corpus", "indice_dir", "nota", "sha256_indice_esperado"]}
    r["mcp_json"] = {"base_solo_cambia_la_config": mcp_solo_ruta, "hibrida_solo_cambia_la_config_del_denso": mcp_h}
    # La tool que expone la base == la que expuso la config BM25 de A2.1/A2.2 en sus controles sellados.
    sellado = json.loads((BANCO_DIR / "a2_1" / "controles" / "tests_fragmentos_a2_1.json").read_text(encoding="utf-8"))
    r["misma_tool_que_A2_2"] = (r["tools_expuestas"] == sellado["bm25_transporte"]["tools_expuestas"]
                                and a.get("afinidad") == b.get("afinidad") == "bm25" and a["limite_max"] == b["limite_max"])
    r["PASS"] = (r["PASS"] and r["limite"]["PASS"] and distintas == r["config"]["esperadas"]
                 and mcp_solo_ruta and mcp_h and r["misma_tool_que_A2_2"])
    return r


def t_aislamiento_bm25() -> dict:
    """Las comprobaciones estáticas de a2_1/test_aislamiento_a2_1.py sobre el servidor con la híbrida, y
    los módulos que importa el proceso en modo BM25 (base de F1), en un subproceso."""
    src = (AQUI / "servidor_mcp_vector.py").read_text(encoding="utf-8")
    imports = sorted(set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", src, flags=re.M)))
    modulos_grafo = {"neo4j", "neo4j_index", "grafos", "conexion", "harness", "loader", "tools_juguete", "agente_v2", "tools_v2"}
    artefactos = ["data/experiment/grafo_v2/reensamblado_v3/kg.json", "data/experiment/neo4j", "agente_v2"]
    re_sockets = r"\bsocket\b|GraphDatabase|bolt://|:7687|requests\.|urllib|httpx"
    prohibidos = sorted({"neo4j", "numpy", "torch", "transformers", "sentence_transformers", "huggingface_hub",
                         "safetensors", "tokenizers"} | modulos_grafo)
    codigo = ("import json, sys\n"
              f"sys.path.insert(0, {str(AQUI)!r})\n"
              "import servidor_mcp_vector as SV\n"
              "from comun_banco import cargar_config\n"
              f"cfg, _ = cargar_config(SV.Path({str(CONFIG_BASE)!r}))\n"
              "idx = SV.construir_indice_de(cfg)\n"
              "n = [len(idx.buscar_pasajes(q, 5)['resultados']) for q in ('capital mínimo', 'clasificación de deudores')]\n"
              f"print(json.dumps({{'n': n, 'importados': sorted(m for m in {prohibidos!r} if m in sys.modules)}}))\n")
    r = subprocess.run([sys.executable, "-B", "-c", codigo], capture_output=True, text=True)
    din = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {"error": r.stderr[-400:]}
    res = {"imports": imports, "importa_modulos_del_grafo": sorted({i.split(".")[0] for i in imports} & modulos_grafo),
           "menciona_artefactos_del_grafo": [x for x in artefactos if x in src],
           "codigo_abre_sockets_o_bolt": bool(re.search(re_sockets, src)),
           "modo_bm25_base": din}
    res["PASS"] = (not res["importa_modulos_del_grafo"] and not res["menciona_artefactos_del_grafo"]
                   and not res["codigo_abre_sockets_o_bolt"] and r.returncode == 0
                   and din.get("importados") == [] and all(n > 0 for n in din.get("n", [0])))
    return res


def construir(afinidad: str, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(AQUI / "construir_indice.py"), "--manifiesto", str(MAN_E0),
                           "--afinidad", afinidad, "--out", str(out)], capture_output=True, text=True)


def bateria(pasajes: list[dict]) -> list[str]:
    """La batería fija de los índices: las consultas no vacías de A2.1 y tres por TO de la tanda 0."""
    return [c["consulta"] for c in CONSULTAS if c["consulta"].strip()] + [c["consulta"] for c in consultas_tanda0(pasajes)]


def sha_json(obj) -> str:
    return sha256_bytes(json.dumps(obj, ensure_ascii=False).encode())


def t_bm25_dos(td: Path) -> dict:
    """La segunda construcción del índice BM25 del acumulado, en un directorio temporal, contra la servida:
    mismo sha del índice y de pasajes.json, y los mismos rankings (10 primeros) en la batería fija."""
    config, _ = cargar_config(CONFIG_BASE)
    servido = (AQUI / config["indice_dir"]).resolve()
    out = td / "bm25_c2"
    r = construir("bm25", out)
    if r.returncode != 0:
        return {"PASS": False, "error": f"rc {r.returncode}: {r.stderr[-400:]}"}
    consultas = bateria(json.loads((servido / "pasajes.json").read_text(encoding="utf-8")))
    rk, shas = {}, {}
    for k, d in (("servida", servido), ("segunda", out)):
        bus = BM.Buscador(json.loads((d / "indice_bm25.json").read_text(encoding="utf-8")))
        rk[k] = [[[bus.ids[i], s] for i, s in bus.buscar(q, 10)] for q in consultas]
        shas[k] = {"indice_bm25": sha256_file(d / "indice_bm25.json"), "pasajes_json": sha256_file(d / "pasajes.json")}
    return {"construccion_servida": shas["servida"], "construccion_2": shas["segunda"],
            "sha_config": config["sha256_indice_esperado"], "stdout": r.stdout.strip().splitlines(),
            "n_consultas": len(consultas), "sha256_consultas": sha_json(consultas),
            "n_consultas_con_resultados": sum(1 for x in rk["servida"] if x),
            "sha256_rankings_servida": sha_json(rk["servida"]), "sha256_rankings_2": sha_json(rk["segunda"]),
            "mismos_rankings": rk["servida"] == rk["segunda"],
            "PASS": (shas["servida"] == shas["segunda"] and rk["servida"] == rk["segunda"]
                     and shas["servida"]["indice_bm25"] == config["sha256_indice_esperado"])}


# --------------------------------------------------------------------------- #
# Grupos con el modelo                                                        #
# --------------------------------------------------------------------------- #
def t_denso_dos(idx, td: Path) -> dict:
    """La segunda construcción de la matriz densa del acumulado, en un directorio temporal, contra la servida:
    iguales byte a byte (sha de la matriz y del .npy), el mismo pasajes.json y los mismos rankings (10 primeros,
    consulta con el prompt `web_search_query`) en la batería fija. La construcción corre antes de cargar el
    modelo en este proceso."""
    import numpy as np
    servido = idx.denso.dir
    out = td / "denso_c2"
    r = construir("denso", out)
    if r.returncode != 0:
        return {"PASS": False, "error": f"rc {r.returncode}: {r.stderr[-400:]}"}
    m2 = json.loads((out / "manifiesto_indice.json").read_text(encoding="utf-8"))
    consultas = bateria(idx.pasajes)
    Q = np.stack([idx.denso.embed_consulta(q, con_prompt=True) for q in consultas])
    rk, shas = {}, {}
    for k, d in (("servida", servido), ("segunda", out)):
        E = np.load(d / "embeddings_docs.npy")
        ids = [p["id"] for p in json.loads((d / "pasajes.json").read_text(encoding="utf-8"))]
        S = (Q @ E.T).tolist()
        rk[k] = [[[ids[i], s[i]] for i in sorted(range(len(ids)), key=lambda i: (-s[i], ids[i]))[:10]] for s in S]
        shas[k] = {"matriz": hashlib.sha256(E.astype("float32").tobytes(order="C")).hexdigest(),
                   "npy": sha256_file(d / "embeddings_docs.npy"), "pasajes_json": sha256_file(d / "pasajes.json")}
    byte_a_byte = (servido / "embeddings_docs.npy").read_bytes() == (out / "embeddings_docs.npy").read_bytes()
    return {"construccion_servida": shas["servida"], "construccion_2": shas["segunda"],
            "sha_config": idx.denso.sha_matriz, "npy_byte_a_byte": byte_a_byte,
            "agrupacion_2": m2["agrupacion"], "tiempos_2": m2["tiempos_s"],
            "n_consultas": len(consultas), "sha256_consultas": sha_json(consultas),
            "sha256_rankings_servida": sha_json(rk["servida"]), "sha256_rankings_2": sha_json(rk["segunda"]),
            "mismos_rankings": rk["servida"] == rk["segunda"],
            "PASS": shas["servida"] == shas["segunda"] and byte_a_byte and rk["servida"] == rk["segunda"]}


def t_hibrida_fusion(idx) -> dict:
    base, _ = cargar_config(CONFIG_BASE)
    idx_b = SV.construir_indice_de(base)
    filas = []
    for c in CONSULTAS:
        q, lim = c["consulta"], SV._limite(c.get("limite", 10), idx.limite_max)
        obj = idx.buscar_pasajes(q, c.get("limite", 10))
        if not q.strip():
            filas.append({"consulta": q, "n": len(obj["resultados"]), "ok": obj["resultados"] == []})
            continue
        esp = esperado_hibrida(idx, q, lim, None)
        rb, rd = idx.ranking_bm25(q), idx.ranking_denso(q)
        rbi, rdi = rankings_independientes(idx, q)
        top_b = [r["id"] for r in idx_b.buscar_pasajes(q, 5)["resultados"]]
        top_d = [r["id"] for r in idx.denso.buscar_pasajes(q, 5)["resultados"]]
        filas.append({"consulta": q, "limite": lim, "n": len(obj["resultados"]),
                      "igual_a_rrf_independiente": obtenido(obj) == esp,
                      "rankings_iguales_a_los_independientes": rb == rbi and rd == rdi,
                      "n_bm25": len(rb), "n_denso": len(rd),
                      "top5_bm25_igual_al_de_la_base": [idx.ids[i] for i in rb[:5]] == top_b,
                      "top5_denso_igual_al_del_modo_denso": [idx.ids[i] for i in rd[:5]] == top_d,
                      "top": [mostrar_id(i) for i, _ in obtenido(obj)]})
        filas[-1]["ok"] = all(filas[-1][k] for k in ("igual_a_rrf_independiente", "rankings_iguales_a_los_independientes",
                                                     "top5_bm25_igual_al_de_la_base", "top5_denso_igual_al_del_modo_denso"))
    canonico = idx.ids == sorted(idx.ids)        # la posición desempata como el id (rankings_independientes)
    return {"n": len(filas), "n_ok": sum(f["ok"] for f in filas), "ids_en_orden_canonico": canonico, "filas": filas,
            "PASS": canonico and all(f["ok"] for f in filas)}


def t_hibrida_filtros(idx) -> dict:
    filas = []
    for c in CONSULTAS_FILTROS:
        q, to, punto = c["consulta"], SV._filtro(c.get("to")), SV._filtro(c.get("punto"), punto=True)
        lim = SV._limite(c.get("limite", 10), idx.limite_max)
        obj = idx.buscar_pasajes(q, c.get("limite", 10), to=c.get("to"), punto=c.get("punto"))
        hay = to is not None or punto is not None
        perm = None
        if hay:
            pat = patron_punto(punto) if punto else None
            perm = {i for i, p in enumerate(idx.pasajes) if (to is None or p["to"].casefold() == to.casefold())
                    and (pat is None or pat.match(p["unidad"].casefold()))}
        f = {"input": c, "n": len(obj["resultados"]), "claves": list(obj), "n_pasajes_filtrados": obj.get("n_pasajes_filtrados"),
             "aviso": obj.get("aviso"), "top": [mostrar_id(i) for i, _ in obtenido(obj)]}
        checks = {"forma": (("filtros" in obj and obj["n_pasajes_filtrados"] == len(perm)) if hay
                            else list(obj) == ["consulta", "total_pasajes", "resultados"])}
        if hay:
            checks["cumplen_filtro"] = all(i in {idx.ids[j] for j in perm} for i, _ in obtenido(obj))
            checks["aviso_si_vacio"] = ("aviso" in obj) == (len(perm) == 0)
        if q.strip() and (perm is None or perm):
            checks["igual_a_rrf_independiente"] = obtenido(obj) == esperado_hibrida(idx, q, lim, perm)
        else:
            checks["vacio"] = obj["resultados"] == []
        f["checks"], f["ok"] = checks, all(checks.values())
        filas.append(f)
    # Normalización: " CAP " y "1.1 " dan lo mismo que "cap" y "1.1"; "1.1." lo mismo que "1.1".
    a = idx.buscar_pasajes("capital mínimo", 5, to=" CAP ", punto=" 1.1 ")
    b = idx.buscar_pasajes("capital mínimo", 5, to="cap", punto="1.1")
    d = idx.buscar_pasajes("capital mínimo", 5, to="cap", punto="1.1.")
    norm_ok = obtenido(a) == obtenido(b) == obtenido(d) and a["n_pasajes_filtrados"] == b["n_pasajes_filtrados"]
    return {"n": len(filas), "n_ok": sum(f["ok"] for f in filas), "filas": filas, "normalizacion": norm_ok,
            "PASS": all(f["ok"] for f in filas) and norm_ok}


def t_hibrida_tope(idx) -> dict:
    q = "capital mínimo básico según la categoría de la entidad"
    lim = {"sin_filtros": limites(idx, q), "con_to": limites(idx, q, to="cap")}
    sin = [idx.buscar_pasajes(q, 5), idx.buscar_pasajes(q, 5, to=None, punto=None),
           idx.buscar_pasajes(q, 5, to="", punto="  "), idx.buscar_pasajes(q, 5, to="   ")]
    forma = [list(o) for o in sin]
    iguales = all(serializar_payload(o) == serializar_payload(sin[0]) for o in sin)
    return {"limite": lim, "sin_filtros": {"claves": forma[0], "iguales_con_filtros_vacios": iguales,
                                           "misma_forma_que_bm25": forma[0] == ["consulta", "total_pasajes", "resultados"]},
            "PASS": lim["sin_filtros"]["PASS"] and lim["con_to"]["PASS"] and iguales
                    and forma[0] == ["consulta", "total_pasajes", "resultados"]}


def t_hibrida_transporte(idx, logs: Path) -> dict:
    consultas = CONSULTAS + CONSULTAS_FILTROS
    r1 = transporte(CONFIG_HIBRIDA, consultas, logs / "log_r1_test_f1_hibrida_1.jsonl", "test_f1_hibrida_1", idx=idx)
    r2 = transporte(CONFIG_HIBRIDA, consultas, logs / "log_r1_test_f1_hibrida_2.jsonl", "test_f1_hibrida_2", idx=idx)
    r1.pop("_idx"), r2.pop("_idx")
    entre_procesos = [a["sha256_mcp"] == b["sha256_mcp"] for a, b in zip(r1["llamadas"], r2["llamadas"])]
    repetidas = all(serializar_payload(idx.buscar_pasajes(c.get("consulta", ""), c.get("limite", 10), to=c.get("to"),
                                                          punto=c.get("punto"))) ==
                    serializar_payload(idx.buscar_pasajes(c.get("consulta", ""), c.get("limite", 10), to=c.get("to"),
                                                          punto=c.get("punto"))) for c in consultas)
    r2_resumen = {k: r2[k] for k in ("n", "n_iguales", "definicion_tool_esperada", "log_r1")}
    return {"proceso_1": r1, "proceso_2": r2_resumen, "n_iguales_entre_procesos": sum(entre_procesos),
            "repetidas_en_el_mismo_proceso_iguales": repetidas,
            "PASS": r1["PASS"] and r2["PASS"] and all(entre_procesos) and repetidas}


def consultas_tanda0(pasajes: list[dict]) -> list[dict]:
    """Tres consultas por TO de la tanda 0: el título de los pasajes en las posiciones n/4, n/2 y 3n/4 del
    TO (orden canónico por id; si el título está vacío, los primeros 120 caracteres del texto), con el TO y
    el primer nivel de su punto para las variantes con filtro."""
    out = []
    for to in sorted(TANDA0):
        ps = [p for p in pasajes if p["to"] == to]
        for j in (1, 2, 3):
            p = ps[(len(ps) * j) // 4]
            q = p["titulo"].strip() or p["texto"][:120]
            out.append({"consulta": q, "to": to, "punto": re.split(r"\.|::", p["unidad"])[0], "de": p["id"]})
    return out


def t_tokens(idx) -> dict:
    base, _ = cargar_config(CONFIG_BASE)
    idx_b = SV.construir_indice_de(base)
    cq = consultas_tanda0(idx.pasajes)
    modos = {"base_bm25": lambda c: idx_b.buscar_pasajes(c["consulta"], 5),
             "hibrida_sin_filtros": lambda c: idx.buscar_pasajes(c["consulta"], 5),
             "hibrida_con_to": lambda c: idx.buscar_pasajes(c["consulta"], 5, to=c["to"]),
             "hibrida_con_to_y_punto": lambda c: idx.buscar_pasajes(c["consulta"], 5, to=c["to"], punto=c["punto"])}
    med, mediana_cpt, min_cpt, max_cpt = {}, *CARACTERES_POR_TOKEN
    for m, fn in modos.items():
        chars, excl, vacias = [], 0, 0
        for c in cq:
            obj = fn(c)
            if any(r["to"] not in TANDA0 for r in obj["resultados"]):
                excl += 1
                continue
            vacias += not obj["resultados"]
            chars.append(len(serializar_payload(obj)))
        tok = [x / mediana_cpt for x in chars]
        med[m] = {"n_consultas": len(cq), "n_medidas": len(chars), "n_excluidas_por_tener_pasajes_de_la_tanda_1": excl,
                  "n_sin_resultados": vacias,
                  "chars": {"media": round(statistics.mean(chars), 1) if chars else None,
                            "mediana": statistics.median(chars) if chars else None,
                            "max": max(chars) if chars else None, "min": min(chars) if chars else None},
                  "tokens_estimados": {"media": round(statistics.mean(tok), 1) if tok else None,
                                       "mediana": round(statistics.median(tok), 1) if tok else None,
                                       "max": round(max(tok), 1) if tok else None,
                                       "rango_de_la_media": ([round(statistics.mean(chars) / max_cpt, 1),
                                                              round(statistics.mean(chars) / min_cpt, 1)] if chars else None)}}
    defs = {}
    for nombre, afin, bloque, cfg in (
            ("base_bm25", "bm25", BANCO_DIR / "a2_1" / "bloque_tools_fragmentos_bm25.txt", CONFIG_BASE),
            ("hibrida", "hibrida", BANCO_DIR / "a2_1" / "bloque_tools_fragmentos_hibrida.txt", CONFIG_HIBRIDA)):
        con_desde = json.loads(cfg.read_text(encoding="utf-8")).get("parametro_desde", False)   # U-NAV-DESDE
        d = json.dumps(SV.definicion_tool(afin, 5, desde=con_desde), ensure_ascii=False)
        b = bloque.read_text(encoding="utf-8").rstrip("\n")
        defs[nombre] = {"definicion_tool_chars": len(d), "definicion_tool_tokens_estimados": round(len(d) / mediana_cpt, 1),
                        "bloque_tools": rel_repo(bloque), "bloque_tools_chars": len(b),
                        "bloque_tools_tokens_estimados": round(len(b) / mediana_cpt, 1)}
    return {"tanda0": sorted(TANDA0), "consultas": [{k: c[k] for k in ("consulta", "to", "punto", "de")} for c in cq],
            "caracteres_por_token": {"mediana": mediana_cpt, "min": min_cpt, "max": max_cpt,
                                     "fuente": "diseño de N2 (U-NAV-DISENO, parte 1): tokenizador de Haiku 4.5 sobre las "
                                               "salidas de herramientas de las 80 trazas base de C2 y C4; estimación, no "
                                               "tokenización de estas salidas"},
            "por_modo": med, "definiciones": defs,
            "PASS": all(v["n_medidas"] > 0 for v in med.values())}


# --------------------------------------------------------------------------- #
# `desde` (U-NAV-DESDE), en los tres modos, sobre la tanda 0                  #
# --------------------------------------------------------------------------- #
# Corren sobre los índices de fragmentos de A2.1 (la tanda 0, e0_r2b_desarrollo), no sobre los del acumulado, con
# configuraciones de prueba escritas en el directorio temporal del test: las de A2.1 de cada modo con
# parametro_desde, y la híbrida sobre esos dos índices, con parametro_desde y sin él. No suman configuraciones.
CONFIG_DENSO_A2 = AQUI / "config_fragmentos_denso_r2b.json"
CONTROL_A2_1 = BANCO_DIR / "a2_1" / "controles" / "tests_fragmentos_a2_1.json"
TEXTO_DESDE = ("desde: posición del ranking desde la que se listan los resultados (0 = los primeros). "
               "Sirve para ver los que no entraron.")
PROPIEDAD_DESDE = {"type": "integer", "description": "Posición desde la que se lista (def. 0)."}
DESDE_INVALIDOS = [-1, -100, "x", "", None, [], {}]
CASO_BORRADOR = "Clasificación en categoría Irrecuperable"
# Consultas con rankings largos, para desde=k; en la híbrida, también con filtros.
CONSULTAS_K = [{"consulta": "capital mínimo básico según la categoría de la entidad"},
               {"consulta": "previsiones mínimas por riesgo de incobrabilidad"}, {"consulta": CASO_BORRADOR}]
CONSULTAS_K_FILTROS = [{"consulta": "capital mínimo", "to": "cap"}, {"consulta": CASO_BORRADOR, "to": "cla"},
                       {"consulta": "capital mínimo", "to": "cap", "punto": "1"}]
_T0: dict = {}


def configs_desde(td: Path) -> dict[str, Path]:
    b = json.loads(CONFIG_BM25_A2.read_text(encoding="utf-8"))
    d = json.loads(CONFIG_DENSO_A2.read_text(encoding="utf-8"))
    h = {"servidor": "mcp_vector", "version": "1.0", "afinidad": "hibrida", "indice_dir_bm25": b["indice_dir"],
         "sha256_indice_esperado": b["sha256_indice_esperado"], "indice_dir_denso": d["indice_dir"],
         "sha256_matriz_esperado": d["sha256_matriz_esperado"], "limite_max": b["limite_max"], "rrf_k": SV.RRF_K,
         "profundidad_rrf": SV.PROFUNDIDAD_RRF, "device": d.get("device", "mps"),
         "nota": "U-NAV-DESDE: configuración de prueba, la híbrida sobre los índices de A2.1 (tanda 0)"}
    out = {}
    for nombre, cfg in (("bm25", {**b, "parametro_desde": True}), ("denso", {**d, "parametro_desde": True}),
                        ("hibrida", {**h, "parametro_desde": True}), ("hibrida_sin_parametro", h)):
        out[nombre] = td / f"config_desde_{nombre}.json"
        out[nombre].write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def indices_t0(td: Path, hibrida: bool = False) -> dict:
    """Las configuraciones de prueba y los índices de la tanda 0. El denso es el de la híbrida (mismo directorio y
    mismo sha256 que la config densa de A2.1), así el modelo se carga una sola vez en este proceso."""
    if "cfg" not in _T0:
        _T0["cfg"] = configs_desde(td)
        _T0["bm25"] = SV.construir_indice_de(cargar_config(_T0["cfg"]["bm25"])[0])
    if hibrida and "hibrida" not in _T0:
        _T0["hibrida"] = SV.construir_indice_de(cargar_config(_T0["cfg"]["hibrida"])[0])
    return _T0


def llamar(idx, c: dict) -> dict:
    """La llamada directa con los argumentos de una consulta de prueba (`desde`, solo si la consulta lo trae)."""
    kw = {"desde": c["desde"]} if "desde" in c else {}
    if isinstance(idx, SV.IndiceHibrido):
        kw |= {"to": c.get("to"), "punto": c.get("punto")}
    return idx.buscar_pasajes(c.get("consulta", ""), c.get("limite", 10), **kw)


def ranking_entero(idx, c: dict) -> list[tuple[int, float]]:
    """El ranking entero de una consulta, escrito aparte del servidor: BM25 con un Buscador nuevo desde el archivo
    del índice; el denso por (-score, id), el desempate del servidor; la híbrida, la RRF independiente sobre esos dos
    rankings, con los filtros aplicados antes (patron_punto, no coincide_punto)."""
    q = c.get("consulta", "")
    if not isinstance(q, str) or not q.strip():
        return []

    def bm25(i_b):
        clave = ("buscador", str(i_b.dir))
        if clave not in _T0:
            _T0[clave] = BM.Buscador(json.loads((i_b.dir / "indice_bm25.json").read_text(encoding="utf-8")))
        bus = _T0[clave]
        s = bus.puntajes(BM.analizar(q))
        return sorted(s.items(), key=lambda kv: (-kv[1], bus.ids[kv[0]]))

    def denso(i_d):
        S = [float(x) for x in i_d.E @ i_d.embed_consulta(q, con_prompt=True)]
        return [(i, S[i]) for i in sorted(range(len(S)), key=lambda i: (-S[i], i_d.ids[i]))]
    if isinstance(idx, SV.IndiceBM25):
        return bm25(idx)
    if isinstance(idx, SV.IndiceVectorial):
        return denso(idx)
    to, punto = SV._filtro(c.get("to")), SV._filtro(c.get("punto"), punto=True)
    rb, rd = [i for i, _ in bm25(idx.bm25)], [i for i, _ in denso(idx.denso)]
    if to is not None or punto is not None:
        pat = patron_punto(punto) if punto else None
        perm = {i for i, p in enumerate(idx.pasajes) if (to is None or p["to"].casefold() == to.casefold())
                and (pat is None or pat.match(p["unidad"].casefold()))}
        rb, rd = [i for i in rb if i in perm], [i for i in rd if i in perm]
    return [(i, float(s)) for i, s in rrf_independiente([rb, rd], idx.ids)]


def casos_desde(idx, consultas: list[dict], consultas_k: list[dict]) -> dict:
    """Las ramas de `desde` en un modo, con llamadas directas."""
    ser = serializar_payload
    cero = [ser(llamar(idx, c)) == ser(llamar(idx, {**c, "desde": 0})) for c in consultas]
    filas_k, pag = [], []
    for c in consultas_k:
        rk = ranking_entero(idx, c)
        for lim in (3, 5):
            p0 = {x["id"] for x in llamar(idx, {**c, "limite": lim})["resultados"]}
            for k in (1, 3, 5, 7):
                obj = llamar(idx, {**c, "limite": lim, "desde": k})
                esp = [(r, idx.ids[i], round(s, 6)) for r, (i, s) in enumerate(rk[k:k + lim], k + 1)]
                got = [(x["rank"], x["id"], x["score"]) for x in obj["resultados"]]
                aviso = (f"no hay más resultados: el ranking tiene {len(rk)} pasajes (desde={k})"
                         if k >= len(rk) else None)       # con filtros, el ranking puede ser más corto que k
                ok = (got == esp and obj.get("desde") == k and obj.get("aviso") == aviso
                      and (k < lim or not {x["id"] for x in obj["resultados"]} & p0))
                filas_k.append({"input": {**c, "limite": lim, "desde": k}, "ranks": [g[0] for g in got],
                                "ids": [mostrar_id(g[1]) for g in got], "ok": ok})
            # pedir desde = los ya vistos recorre el ranking sin saltos ni repetidos
            vistos, d = [], 0
            while len(vistos) < 20:
                res = llamar(idx, {**c, "limite": lim, "desde": d})["resultados"]
                if not res:
                    break
                vistos, d = vistos + [x["id"] for x in res], d + len(res)
            pag.append(vistos == [idx.ids[i] for i, _ in rk[:len(vistos)]] and len(vistos) >= min(20, len(rk)))
    # más allá del final: `aviso` con el largo del ranking, sin resultados y sin fallar; desde = largo - 1, el último
    fin = []
    for c in consultas_k[:2] + consultas_k[-1:] + [{"consulta": "de la que el en y a los del se"}]:
        n = len(ranking_entero(idx, c))
        for d in (max(n, 1), n + 10, 10 ** 12):
            obj = llamar(idx, {**c, "desde": d})
            dd = min(d, 10 ** 9)
            aviso = f"no hay más resultados: el ranking tiene {n} pasajes (desde={dd})"
            fin.append({"input": {**c, "desde": d}, "n_ranking": n,
                        "ok": obj["resultados"] == [] and obj.get("desde") == dd and obj.get("aviso") == aviso})
        if n:
            ult = llamar(idx, {**c, "desde": n - 1})["resultados"]
            fin.append({"input": {**c, "desde": n - 1}, "n_ranking": n, "ok": [x["rank"] for x in ult] == [n]})
    # validación: lo que no es un entero de 0 o más vale 0; 2.9 vale 2 y "3", 3
    c0 = consultas_k[0]
    ref = ser(llamar(idx, c0))
    val = (all(ser(llamar(idx, {**c0, "desde": v})) == ref for v in DESDE_INVALIDOS)
           and ser(llamar(idx, {**c0, "desde": 2.9})) == ser(llamar(idx, {**c0, "desde": 2}))
           and ser(llamar(idx, {**c0, "desde": "3"})) == ser(llamar(idx, {**c0, "desde": 3})))
    forma = list(llamar(idx, {**c0, "desde": 1}))
    forma_ok = forma == ["consulta", "total_pasajes", "desde", "resultados"]
    return {"desde_0_igual_a_sin_desde": {"n": len(cero), "n_iguales": sum(cero)},
            "desde_k": {"n": len(filas_k), "n_ok": sum(f["ok"] for f in filas_k), "filas": filas_k},
            "paginacion_por_vistos": {"n": len(pag), "n_ok": sum(pag)},
            "mas_alla_del_final": {"n": len(fin), "n_ok": sum(f["ok"] for f in fin), "filas": fin},
            "validacion": val, "forma_con_desde": forma,
            "PASS": all(cero) and all(f["ok"] for f in filas_k) and all(pag) and all(f["ok"] for f in fin) and val
                    and forma_ok}


def grupo_desde(idx, modo: str, cfg_desde: Path, cfg_sin: Path, consultas: list[dict], consultas_k: list[dict],
                logs: Path, control: str | None) -> dict:
    """Un modo: las ramas directas y, por MCP, las mismas llamadas con la config con parametro_desde y con la que no
    lo declara (la de A2.1/A2.2, o la híbrida sin él): sin desde y con desde=0 dan lo mismo en las dos y, con un
    control sellado de A2.1, el mismo sha256 que en él; sin parametro_desde, `desde` no se lee."""
    r = casos_desde(idx, consultas, consultas_k)
    c0 = consultas_k[0]
    extra = ([{**c0, "desde": k} for k in (1, 3, 5)] + [{**c0, "desde": 10 ** 12}]
             + [{**c0, "desde": v} for v in ("x", -1, None)])
    mcp = list(consultas) + [{**c, "desde": 0} for c in consultas] + extra
    a = transporte(cfg_desde, mcp, logs / f"log_r1_test_desde_{modo}.jsonl", f"test_desde_{modo}", idx=idx)
    b = transporte(cfg_sin, mcp, logs / f"log_r1_test_desde_{modo}_sin_parametro.jsonl", f"test_desde_{modo}_sin",
                   idx=idx)
    a.pop("_idx"), b.pop("_idx")
    n = len(consultas)
    sa, sb = [f["sha256_mcp"] for f in a["llamadas"]], [f["sha256_mcp"] for f in b["llamadas"]]
    sha_c0 = sha256_bytes(serializar_payload(llamar(idx, c0)).encode())

    def resumen(t: dict) -> dict:
        return ({k: t[k] for k in ("config", "tools_expuestas", "definicion_tool_esperada", "n", "n_iguales", "PASS")}
                | {"fuente_parametro_desde": t["log_r1"]["fuente_inicio"].get("parametro_desde")})
    m = r["mcp"] = {"con_parametro": resumen(a), "sin_parametro": resumen(b),
                    "sin_desde_igual_a_desde_0_en_las_dos": sa[:n] == sa[n:2 * n] == sb[:n] == sb[n:2 * n],
                    "sin_parametro_no_lee_desde": all(x == sha_c0 for x in sb[2 * n:]),
                    "llamadas_con_parametro": a["llamadas"]}
    ok = (a["PASS"] and b["PASS"] and m["sin_desde_igual_a_desde_0_en_las_dos"] and m["sin_parametro_no_lee_desde"]
          and m["con_parametro"]["fuente_parametro_desde"] is True and m["sin_parametro"]["fuente_parametro_desde"] is None)
    if control:
        sellado = json.loads(CONTROL_A2_1.read_text(encoding="utf-8"))[control]["llamadas"]
        cs = m["control_sellado"] = {"archivo": rel_repo(CONTROL_A2_1), "grupo": control,
                                     "mismas_entradas": [l["input"] for l in sellado] == list(consultas),
                                     "sin_desde_y_desde_0_igual_sha256":
                                         sa[:n] == sa[n:2 * n] == [l["sha256_mcp"] for l in sellado]}
        ok &= cs["mismas_entradas"] and cs["sin_desde_y_desde_0_igual_sha256"]
    r["PASS"] = r["PASS"] and ok
    return r


def t_desde_definicion() -> dict:
    """Sin modelo. La tool sin `desde` es la de hoy (la de los controles sellados de A2.1); con `desde`, la misma más
    la propiedad y el texto al final de la descripción; _desde; y qué configuraciones lo declaran."""
    control = json.loads(CONTROL_A2_1.read_text(encoding="utf-8"))
    sin = {a: SV.definicion_tool(a, 5) for a in ("bm25", "denso", "hibrida")}
    con = {a: SV.definicion_tool(a, 5, desde=True) for a in ("bm25", "denso", "hibrida")}
    hoy_ok = (sin["bm25"] == control["bm25_transporte"]["tools_expuestas"][0]
              and sin["denso"] == control["denso_r2b"]["tools_expuestas"][0])
    con_ok = all(con[a]["description"] == sin[a]["description"] + " " + TEXTO_DESDE
                 and con[a]["input_schema"]["properties"].get("desde") == PROPIEDAD_DESDE
                 and {k: v for k, v in con[a]["input_schema"]["properties"].items() if k != "desde"}
                 == sin[a]["input_schema"]["properties"]
                 and con[a]["input_schema"]["required"] == sin[a]["input_schema"]["required"] == ["consulta"] for a in con)
    tabla = [(0, 0), (3, 3), ("3", 3), (2.9, 2), (-1, 0), ("x", 0), ("", 0), (None, 0), ([], 0), ({}, 0), (10 ** 12, 10 ** 9)]
    val = [{"entrada": repr(v), "esperado": e, "ok": SV._desde(v) == e} for v, e in tabla]
    configs = {rel_repo(p): json.loads(p.read_text(encoding="utf-8")).get("parametro_desde", False)
               for p in (CONFIG_BM25_A2, CONFIG_DENSO_A2, AQUI / "config_mcp_vector.json", CONFIG_BASE, CONFIG_HIBRIDA)}
    cfg_ok = list(configs.values()) == [False, False, False, False, True]
    return {"sin_desde_igual_a_los_controles_sellados": hoy_ok, "con_desde": con_ok, "texto": SV.TEXTO_DESDE,
            "texto_igual_al_esperado": SV.TEXTO_DESDE == TEXTO_DESDE, "validacion": val,
            "parametro_desde_por_config": configs,
            "PASS": hoy_ok and con_ok and SV.TEXTO_DESDE == TEXTO_DESDE and all(v["ok"] for v in val) and cfg_ok}


def t_desde_bm25(td: Path, logs: Path) -> dict:
    t = indices_t0(td)
    return grupo_desde(t["bm25"], "bm25", t["cfg"]["bm25"], CONFIG_BM25_A2, CONSULTAS, CONSULTAS_K, logs,
                       "bm25_transporte")


def t_desde_denso(td: Path, logs: Path) -> dict:
    t = indices_t0(td, hibrida=True)
    return grupo_desde(t["hibrida"].denso, "denso", t["cfg"]["denso"], CONFIG_DENSO_A2, CONSULTAS, CONSULTAS_K, logs,
                       "denso_r2b")


def t_desde_hibrida(td: Path, logs: Path) -> dict:
    t = indices_t0(td, hibrida=True)
    idx = t["hibrida"]
    r = grupo_desde(idx, "hibrida", t["cfg"]["hibrida"], t["cfg"]["hibrida_sin_parametro"], CONSULTAS + CONSULTAS_FILTROS,
                    CONSULTAS_K + CONSULTAS_K_FILTROS, logs, None)
    # con filtros y desde > 0: el aviso de los filtros queda y no se suma el de desde
    sin_pasajes = [{"consulta": "capital mínimo", "to": "xyz"}, {"consulta": "capital mínimo", "to": "cap", "punto": "999"}]
    avisos_ok = all(v["aviso"] == s["aviso"] and v["resultados"] == [] and v["desde"] == 2
                    for v, s in ((llamar(idx, {**c, "desde": 2}), llamar(idx, c)) for c in sin_pasajes))
    forma = list(llamar(idx, {"consulta": "capital mínimo", "to": "cap", "desde": 1}))
    forma_ok = forma == ["consulta", "total_pasajes", "desde", "filtros", "n_pasajes_filtrados", "resultados"]
    # informativo: el caso del borrador en fragmentos (los pasajes de cla::6.5.5.4 y 6.5.5.5 en la fusión con to=cla)
    q = {"consulta": CASO_BORRADOR, "to": "cla"}
    lugares = {idx.ids[i]: r_ for r_, (i, _) in enumerate(ranking_entero(idx, q), 1)
               if any(SV.coincide_punto(idx.pasajes[i]["unidad"], u) for u in ("6.5.5.4", "6.5.5.5"))}
    r["filtros_con_desde"] = {"avisos_de_los_filtros_quedan": avisos_ok, "forma": forma}
    r["caso_borrador_informativo"] = {"consulta": q, "lugar_en_la_fusion": lugares,
                                      "en_la_pagina_desde_5": [x["id"] for x in llamar(idx, {**q, "desde": 5})["resultados"]
                                                               if x["id"] in lugares]}
    r["PASS"] = r["PASS"] and avisos_ok and forma_ok
    return r


GRUPOS_DESDE = ["desde_definicion", "desde_bm25", "desde_denso", "desde_hibrida"]
GRUPOS_SIN_MODELO = ["rrf_a_mano", "filtros_unidad", "indices", "base_bm25", "aislamiento_bm25", "bm25_dos",
                     "desde_definicion", "desde_bm25"]
GRUPOS_CON_MODELO = ["denso_dos", "hibrida_fusion", "hibrida_filtros", "hibrida_tope", "hibrida_transporte", "tokens",
                     "desde_denso", "desde_hibrida"]
GRUPOS = GRUPOS_SIN_MODELO + GRUPOS_CON_MODELO


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--grupo", action="append", choices=GRUPOS)
    a = ap.parse_args()
    grupos = a.grupo or GRUPOS
    a.out.parent.mkdir(parents=True, exist_ok=True)
    logs = a.out.parent / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    import platform
    import unicodedata
    res = {"generado": datetime.now().isoformat(timespec="seconds"),
           "unidad": "U-NAV-DISENO, N5-F — tests de las configuraciones de F1 del servidor de fragmentos",
           "python": sys.version.split()[0], "platform": platform.platform(), "unicodedata": unicodedata.unidata_version,
           "codigo": {k: sha256_file(AQUI / k) for k in ("servidor_mcp_vector.py", "bm25_fragmentos.py",
                                                         "construir_indice.py", "test_fragmentos_f1.py")},
           "grupos": grupos}
    idx = None
    grupos = [g for g in GRUPOS if g in grupos]          # el orden de GRUPOS: denso_dos antes de cargar el modelo
    with tempfile.TemporaryDirectory() as td:
        for g in grupos:
            if g in GRUPOS_CON_MODELO and g not in GRUPOS_DESDE and idx is None:
                idx, _, _ = cargar_hibrida()                # el modelo se carga en la primera consulta
            fn = {"rrf_a_mano": t_rrf_a_mano, "filtros_unidad": t_filtros_unidad, "indices": t_indices,
                  "base_bm25": lambda: t_base_bm25(logs), "aislamiento_bm25": t_aislamiento_bm25,
                  "bm25_dos": lambda: t_bm25_dos(Path(td)), "denso_dos": lambda: t_denso_dos(idx, Path(td)),
                  "hibrida_fusion": lambda: t_hibrida_fusion(idx), "hibrida_filtros": lambda: t_hibrida_filtros(idx),
                  "hibrida_tope": lambda: t_hibrida_tope(idx), "hibrida_transporte": lambda: t_hibrida_transporte(idx, logs),
                  "tokens": lambda: t_tokens(idx), "desde_definicion": t_desde_definicion,
                  "desde_bm25": lambda: t_desde_bm25(Path(td), logs), "desde_denso": lambda: t_desde_denso(Path(td), logs),
                  "desde_hibrida": lambda: t_desde_hibrida(Path(td), logs)}[g]
            res[g] = fn()
            print(f"{g}: {'PASS' if res[g]['PASS'] else 'FAIL'}", flush=True)
    res["PASS"] = all(res[g]["PASS"] for g in grupos)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TOTAL:", "PASS" if res["PASS"] else "FAIL", "->", rel_repo(a.out))
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
