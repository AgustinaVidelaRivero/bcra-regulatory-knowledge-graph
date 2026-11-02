#!/usr/bin/env python3
"""test_fragmentos_a2_1.py — Tests del servidor de fragmentos para A2.1 (tramo 1, §3, punto 4).
Costo USD 0, sin API. Grupos (--grupo, se pueden repetir; default: todos):

  bm25_determinismo  dos construcciones del índice BM25 (construir_indice.py en dos
                     directorios temporales): mismo sha que el índice servido y los
                     mismos rankings para una lista fija de consultas.
  bm25_analizador    el analizador sobre una lista fija de palabras, con lo esperado
                     derivado a mano de cada pieza de Lucene 9.11.1 y su fuente.
  bm25_transporte    consultas propias por MCP (cliente falso) byte a byte contra el
                     cálculo directo; definición de la tool; `limite` > 5 devuelve 5;
                     todo pasaje cita `to` y `unidad`; log R1 consistente.
  denso_r2b          el índice denso r2b servido: sha del manifiesto == config, los
                     mismos pasajes que el BM25 (sha de pasajes.json), transporte por
                     MCP byte a byte y `limite` > 5 devuelve 5. Necesita el modelo.
  denso_r2b_dos      dos construcciones de la matriz densa r2b en directorios
                     temporales: iguales byte a byte, y == la servida. Necesita el modelo.
  denso_e0_vieja     construcción con el manifiesto de la E0 vieja: la matriz da el sha
                     sellado 12d284d5… (si no da, el test falla). Necesita el modelo.
  regresion_denso    el test (d) de test_mcp_vector.py con el índice viejo
                     (--sin-reconstruir): PASS y los 10 outputs con el mismo sha256 que
                     los de la corrida sellada (resultados/tests_mcp_vector.json).
  config_grafo       las dos configuraciones del brazo del grafo para A2 contra
                     data/experiment/neo4j/grafos.py y el sha del kg.json, sin Neo4j.

Uso (venv del servidor vectorial, requirements_vector.txt):
    python3 -B test_fragmentos_a2_1.py --out <json> [--grupo bm25_transporte ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
EXPERIMENT_DIR = BANCO_DIR.parent
REPO_DIR = EXPERIMENT_DIR.parents[1]
for _p in (str(BANCO_DIR), str(AQUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import bm25_fragmentos as BM                                              # noqa: E402
from cliente_falso import ClienteFalso                                   # noqa: E402
from comun_banco import cargar_config, rel_repo, serializar_payload, sha256_bytes, sha256_file  # noqa: E402
from servidor_mcp_vector import construir_indice_de, definicion_tool    # noqa: E402

CONFIG_BM25 = AQUI / "config_fragmentos_bm25_r2b.json"
CONFIG_DENSO = AQUI / "config_fragmentos_denso_r2b.json"
CONFIG_VIEJA = AQUI / "config_mcp_vector.json"
MAN_R2B = AQUI / "manifiestos_e0" / "e0_tanda0_r2b_desarrollo.json"
MAN_VIEJA = AQUI / "manifiestos_e0" / "e0_enm01.json"
SHA_MATRIZ_VIEJA = "12d284d5bce0d1d58f1e4437c47f2177b3145813586069ca72f9103309b28b65"
CORRIDA_SELLADA = AQUI / "resultados" / "tests_mcp_vector.json"
CONFIGS_GRAFO = [BANCO_DIR / "mcp_kg" / "config_mcp_kg_a2_desarrollo_r2b.json",
                 BANCO_DIR / "mcp_kg" / "config_mcp_kg_a2_desarrollo_r2b_rs1.json"]

# Consultas propias: las 10 del test (d) del denso (test_mcp_vector.py) y variantes de `limite`.
CONSULTAS = [
    {"consulta": "¿qué requisitos debe cumplir una asociación mutual para operar con entidades financieras?"},
    {"consulta": "exigencia de efectivo mínimo en pesos", "limite": 5},
    {"consulta": "capital mínimo básico según la categoría de la entidad"},
    {"consulta": "cómo se clasifica a un deudor en situación 3", "limite": 3},
    {"consulta": "previsiones mínimas por riesgo de incobrabilidad"},
    {"consulta": "garantías preferidas A y B", "limite": 50},
    {"consulta": "acceso al mercado de cambios para pago de importaciones", "limite": "7"},
    {"consulta": "tope a la tasa de interés de financiaciones con tarjeta de crédito", "limite": 0},
    {"consulta": "   "},                                             # consulta vacía
    {"consulta": "plazo para informar incumplimientos de relaciones técnicas"},
    {"consulta": "de la que el en y a los del se", "limite": 5},       # solo palabras vacías
    {"consulta": "responsabilidad patrimonial computable", "limite": 6},
    {"consulta": "régimen informativo contable mensual", "limite": "abc"},
]
# `limite` pedido -> cantidad esperada con limite_max = 5 (cuando la consulta tiene al menos 5 aciertos).
LIMITES_ESPERADOS = [(None, 5), (3, 3), (5, 5), (6, 5), (10, 5), (50, 5), ("7", 5), (0, 1), ("abc", 5)]

# Analizador: entrada, salida esperada y la pieza de Lucene 9.11.1 que la fija.
LT, LC, SF, ST = ("StandardTokenizer (UAX #29)", "LowerCaseFilter", "StopFilter (spanish_stop.txt)",
                  "SpanishLightStemmer.stem")
ANALIZADOR_ESPERADO = [
    ("Capitales", ["capital"], f"{LC}; {ST}: termina en s con e en len-2 -> quita 2 (regla 3)"),
    ("mínimo", ["minim"], f"{ST}: tabla de acentos (í -> i) y termina en o -> quita 1"),
    ("días", ["días"], f"{ST}: menos de 5 caracteres -> sin cambios (ni acentos)"),
    ("años", ["años"], f"{ST}: menos de 5 caracteres -> sin cambios; la ñ no está en la tabla"),
    ("entidades", ["entidad"], f"{ST}: regla 3 (e en len-2)"),
    ("veces", ["vez"], f"{ST}: regla 2 (ces -> z, quita 2)"),
    ("luces", ["luz"], f"{ST}: regla 2 (ces -> z, quita 2)"),
    ("intereses", ["interes"], f"{ST}: regla 1 (eses -> quita 2)"),
    ("meses", ["mes"], f"{ST}: regla 1 (eses -> quita 2)"),
    ("clases", ["clas"], f"{ST}: no es regla 1 (len-4 = a) ni 2 (len-3 = s): regla 3"),
    ("interés", ["inter"], f"{ST}: tabla de acentos y después regla 3 sobre 'interes'"),
    ("señores", ["señor"], f"{ST}: regla 3; la ñ no cambia"),
    ("Pingüino", ["pinguin"], f"{LC}; {ST}: tabla de acentos (ü -> u) y o final"),
    ("Ñandú", ["ñandu"], f"{LC}; {ST}: tabla (ú -> u); termina en u: sin regla de sufijo"),
    ("créditos", ["credit"], f"{ST}: tabla y regla 3 (o en len-2)"),
    ("garantía", ["garanti"], f"{ST}: tabla y a final"),
    ("tasa tasas", ["tasa", "tas"], f"{ST}: 'tasa' tiene 4 caracteres; 'tasas', regla 3"),
    ("deudor", ["deudor"], f"{ST}: termina en r: sin regla"),
    ("más MÁS mas", ["mas"], f"{LC} antes de {SF}: 'más' es palabra vacía en las dos grafías; 'mas' sin tilde no"),
    ("también", [], f"{SF}"),
    ("si sí", ["si"], f"{SF}: solo 'sí' (con tilde) es palabra vacía"),
    ("el a e o y", [], f"{SF}"),
    ("u", ["u"], f"{SF}: 'u' no está en la lista"),
    ("co-deudores", ["co", "deudor"], f"{LT}: el guion corta; {ST}: 'co' tiene 2 caracteres, 'deudores' regla 3"),
    ("1.234,56", ["1.234,56"], f"{LT}: dígito (MidNum|MidNumLet) dígito no corta (WB11, WB12)"),
    ("1.4.2.1.", ["1.4.2.1"], f"{LT}: el punto final no va seguido de dígito: corta"),
    ("A.1", ["1"], f"{LT}: letra . dígito corta (WB6 pide letra a los dos lados); 'a' es palabra vacía"),
    ("S.A.", ["s.a"], f"{LT}: letra (MidNumLet) letra no corta (WB6, WB7)"),
    ("art:5", ["art", "5"], f"{LT}: letra : dígito corta"),
    ("S:t", ["s:t"], f"{LT}: letra (MidLetter) letra no corta (WB6, WB7)"),
    ("l'avion", ["l'avion"], f"{LT}: letra ' letra no corta (WB6, WB7); termina en n"),
    ("3er A1", ["3er", "a1"], f"{LT}: letras y dígitos no cortan (WB9, WB10)"),
    ("cta_cte", ["cta_ct"], f"{LT}: el guion bajo (ExtendNumLet) no corta (WB13a, WB13b); {ST}: e final"),
    ("U$S", ["u", "s"], f"{LT}: '$' corta"),
    ("pagos/cobros", ["pag", "cobr"], f"{LT}: '/' corta; {ST}: regla 3"),
    ("5%", ["5"], f"{LT}: '%' corta"),
    ("Comunicación «A» 6938", ["comunicacion", "6938"], f"{LT}: comillas cortan; {SF}: 'a'; {ST}: tabla, termina en n"),
    ("(BCRA)", ["bcra"], f"{LT}; {LC}"),
    ("İSTANBUL", ["istanbul"], f"{LC}: Character.toLowerCase(U+0130) = 'i' (mapeo simple)"),
    ("efectivo mínimo en pesos", ["efectiv", "minim", "pes"], f"cadena completa: {SF} saca 'en'; {ST} regla 3 en 'pesos'"),
    ("a" * 300, ["a" * 254, "a" * 44], f"{LT}: un token de más de 255 se parte en trozos de 255 "
                                        f"(Javadoc de setMaxTokenLength); {ST}: a final en cada trozo"),
]


def sha_arr(a) -> str:
    return hashlib.sha256(a.astype("float32").tobytes(order="C")).hexdigest()


def construir(manifiesto: Path, afinidad: str, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(AQUI / "construir_indice.py"), "--manifiesto", str(manifiesto),
                           "--afinidad", afinidad, "--out", str(out)], capture_output=True, text=True)


def rankings(buscador: BM.Buscador, consultas: list[str]) -> list:
    return [[[buscador.ids[i], s] for i, s in buscador.buscar(q, 10)] for q in consultas]


# --------------------------------------------------------------------------- #
def t_bm25_determinismo() -> dict:
    config, _ = cargar_config(CONFIG_BM25)
    servido = (AQUI / config["indice_dir"]).resolve()
    sha_servido = sha256_file(servido / "indice_bm25.json")
    consultas = [c["consulta"] for c in CONSULTAS if c["consulta"].strip()]
    con = {}
    with tempfile.TemporaryDirectory() as td:
        for k in ("1", "2"):
            out = Path(td) / f"c{k}"
            r = construir(MAN_R2B, "bm25", out)
            if r.returncode != 0:
                return {"PASS": False, "error": f"construcción {k}: rc {r.returncode}: {r.stderr[-400:]}"}
            idx = json.loads((out / "indice_bm25.json").read_text(encoding="utf-8"))
            con[k] = {"sha256_indice": sha256_file(out / "indice_bm25.json"),
                      "sha256_pasajes_json": sha256_file(out / "pasajes.json"),
                      "rankings": rankings(BM.Buscador(idx), consultas)}
    mismos_rankings = con["1"]["rankings"] == con["2"]["rankings"]
    sha_rk = sha256_bytes(json.dumps(con["1"]["rankings"], ensure_ascii=False).encode())
    return {"sha_construccion_1": con["1"]["sha256_indice"], "sha_construccion_2": con["2"]["sha256_indice"],
            "sha_servido": sha_servido, "sha_config": config["sha256_indice_esperado"],
            "pasajes_iguales": con["1"]["sha256_pasajes_json"] == con["2"]["sha256_pasajes_json"]
                               == sha256_file(servido / "pasajes.json"),
            "n_consultas_ranking": len(consultas), "mismos_rankings": mismos_rankings, "sha256_rankings": sha_rk,
            "PASS": (con["1"]["sha256_indice"] == con["2"]["sha256_indice"] == sha_servido
                     == config["sha256_indice_esperado"] and mismos_rankings)}


def t_bm25_analizador() -> dict:
    filas = []
    for entrada, esperado, fuente in ANALIZADOR_ESPERADO:
        obtenido = BM.analizar(entrada)
        filas.append({"entrada": entrada if len(entrada) < 60 else f"'a' x {len(entrada)}",
                      "esperado": esperado if all(len(t) < 60 for t in esperado) else [f"'a' x {len(t)}" for t in esperado],
                      "obtenido_igual": obtenido == esperado, "fuente": fuente})
    stop_ok = len(BM.STOP_ES) == 308 and len(BM.STOP) == 308
    return {"n": len(filas), "n_iguales": sum(f["obtenido_igual"] for f in filas), "filas": filas,
            "stop": {"n_lista": len(BM.STOP_ES), "n_conjunto": len(BM.STOP), "sha256_stop": BM.SHA256_STOP},
            "PASS": all(f["obtenido_igual"] for f in filas) and stop_ok}


def transporte(config_path: Path, consultas: list[dict], log_path: Path, tag: str) -> dict:
    config, config_sha = cargar_config(config_path)
    idx = construir_indice_de(config)
    filas = []
    with ClienteFalso([sys.executable, "-B", str(AQUI / "servidor_mcp_vector.py"), "--config", str(config_path)],
                      env={"BANCO_LOG_R1": str(log_path), "BANCO_SESION_TAG": tag, "HF_HUB_OFFLINE": "1"},
                      timeout_s=900) as cli:
        tools = cli.listar_tools()
        for k, c in enumerate(consultas, 1):
            via = cli.llamar("buscar_pasajes", c)
            directo = serializar_payload(idx.buscar_pasajes(c.get("consulta", ""), c.get("limite", 10)))
            obj = json.loads(via)
            filas.append({"k": k, "input": c, "chars_mcp": len(via), "n_resultados": len(obj["resultados"]),
                          "sha256_mcp": sha256_bytes(via.encode()), "igual": via == directo,
                          "todos_citan_to_y_unidad": all(r.get("to") and r.get("unidad") for r in obj["resultados"]),
                          "top1": (obj["resultados"][0]["id"] if obj["resultados"] else None)})
    lineas = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    llam = [l for l in lineas if l["evento"] == "llamada"]
    log_ok = (len(llam) == len(filas) and lineas[0]["evento"] == "inicio" and lineas[-1]["evento"] == "fin"
              and all(l["n"] == f["k"] and l["input"] == f["input"] and l["output_sha256"] == f["sha256_mcp"]
                      and l["config_sha256"] == config_sha for l, f in zip(llam, filas)))
    esperada = definicion_tool(config.get("afinidad", "denso"), int(config.get("limite_max", 50)))
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


def limites(idx, consulta: str) -> dict:
    filas = []
    for pedido, esperado in LIMITES_ESPERADOS:
        n = len(idx.buscar_pasajes(consulta, 10 if pedido is None else pedido)["resultados"])
        filas.append({"limite_pedido": pedido, "esperado": esperado, "devuelto": n, "ok": n == esperado})
    return {"consulta": consulta, "filas": filas, "PASS": all(f["ok"] for f in filas)}


def t_bm25_transporte(logs: Path) -> dict:
    r = transporte(CONFIG_BM25, CONSULTAS, logs / f"log_r1_test_bm25_transporte_{datetime.now().strftime('%Y%m%dT%H%M%S')}.jsonl",
                   "test_a2_1_bm25")
    idx = r.pop("_idx")
    r["limite"] = limites(idx, "capital mínimo básico según la categoría de la entidad")
    r["limite_por_mcp"] = {"mayores_que_5_devuelven_5": all(f["n_resultados"] == 5 for f in r["llamadas"]
                                                            if f["input"].get("limite") in (50, "7", 6, "abc"))}
    r["PASS"] = r["PASS"] and r["limite"]["PASS"] and r["limite_por_mcp"]["mayores_que_5_devuelven_5"]
    return r


def t_denso_r2b(logs: Path) -> dict:
    config, _ = cargar_config(CONFIG_DENSO)
    dir_d = (AQUI / config["indice_dir"]).resolve()
    cfg_b, _ = cargar_config(CONFIG_BM25)
    dir_b = (AQUI / cfg_b["indice_dir"]).resolve()
    man = json.loads((dir_d / "manifiesto_indice.json").read_text(encoding="utf-8"))
    r = transporte(CONFIG_DENSO, CONSULTAS, logs / f"log_r1_test_denso_r2b_transporte_{datetime.now().strftime('%Y%m%dT%H%M%S')}.jsonl",
                   "test_a2_1_denso_r2b")
    idx = r.pop("_idx")
    r["indice"] = {"sha256_matriz_manifiesto": man["matriz"]["sha256_matriz"],
                   "sha256_matriz_config": config["sha256_matriz_esperado"],
                   "manifiesto_e0": man.get("manifiesto_e0"),
                   "mismos_pasajes_que_bm25": sha256_file(dir_d / "pasajes.json") == sha256_file(dir_b / "pasajes.json"),
                   "n_pasajes": len(idx.ids)}
    r["limite"] = limites(idx, "capital mínimo básico según la categoría de la entidad")
    r["PASS"] = (r["PASS"] and r["limite"]["PASS"] and r["indice"]["mismos_pasajes_que_bm25"]
                 and man["matriz"]["sha256_matriz"] == config["sha256_matriz_esperado"] and len(idx.ids) == 1768)
    return r


def t_denso_r2b_dos() -> dict:
    config, _ = cargar_config(CONFIG_DENSO)
    servido = json.loads(((AQUI / config["indice_dir"]).resolve() / "manifiesto_indice.json").read_text(encoding="utf-8"))
    shas = {}
    with tempfile.TemporaryDirectory() as td:
        for k in ("1", "2"):
            out = Path(td) / f"c{k}"
            r = construir(MAN_R2B, "denso", out)
            if r.returncode != 0:
                return {"PASS": False, "error": f"construcción {k}: rc {r.returncode}: {r.stderr[-400:]}"}
            m = json.loads((out / "manifiesto_indice.json").read_text(encoding="utf-8"))
            shas[k] = {"sha256_matriz": m["matriz"]["sha256_matriz"], "sha256_archivo_npy": sha256_file(out / "embeddings_docs.npy"),
                       "n_truncados": m["agrupacion"]["n_truncados"], "n_grupos": m["agrupacion"]["n_grupos"]}
        iguales = (Path(td) / "c1" / "embeddings_docs.npy").read_bytes() == (Path(td) / "c2" / "embeddings_docs.npy").read_bytes()
    return {"construccion_1": shas["1"], "construccion_2": shas["2"], "npy_byte_a_byte": iguales,
            "sha_servido": servido["matriz"]["sha256_matriz"],
            "PASS": iguales and shas["1"]["sha256_matriz"] == shas["2"]["sha256_matriz"] == servido["matriz"]["sha256_matriz"]}


def t_denso_e0_vieja() -> dict:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "vieja"
        r = construir(MAN_VIEJA, "denso", out)
        m = json.loads((out / "manifiesto_indice.json").read_text(encoding="utf-8")) if r.returncode in (0, 2) else None
    sha = m["matriz"]["sha256_matriz"] if m else None
    return {"returncode": r.returncode, "sha256_matriz": sha, "esperado": SHA_MATRIZ_VIEJA,
            "stdout_tail": r.stdout[-300:], "stderr_tail": r.stderr[-300:] if r.returncode not in (0, 2) else None,
            "PASS": r.returncode == 0 and sha == SHA_MATRIZ_VIEJA}


def t_regresion_denso(out_dir: Path) -> dict:
    out = out_dir / "regresion_test_mcp_vector.json"
    r = subprocess.run([sys.executable, "-B", str(AQUI / "test_mcp_vector.py"), "--config", str(CONFIG_VIEJA),
                        "--out", str(out), "--sin-reconstruir"], capture_output=True, text=True)
    if not out.exists():
        return {"PASS": False, "returncode": r.returncode, "stderr_tail": r.stderr[-600:]}
    nuevo = json.loads(out.read_text(encoding="utf-8"))
    sellado = json.loads(CORRIDA_SELLADA.read_text(encoding="utf-8"))
    pares = [{"k": a["k"], "input": a["input"], "sha_sellado": a["sha256_mcp"], "sha_nuevo": b["sha256_mcp"],
              "igual": a["sha256_mcp"] == b["sha256_mcp"] and a["input"] == b["input"]}
             for a, b in zip(sellado["d_transporte"]["llamadas"], nuevo["d_transporte"]["llamadas"])]
    return {"returncode": r.returncode, "stdout": r.stdout.strip().splitlines(),
            "salida": rel_repo(out), "corrida_sellada": rel_repo(CORRIDA_SELLADA),
            "d_PASS": nuevo["d_transporte"]["PASS"], "a_PASS": nuevo["a_asimetria"]["PASS"],
            "c_PASS": nuevo["c_coincidencia_bakeoff"]["PASS"],
            "n_llamadas": len(pares), "n_iguales_a_la_sellada": sum(p["igual"] for p in pares), "llamadas": pares,
            "PASS": (nuevo["d_transporte"]["PASS"] and len(pares) == len(sellado["d_transporte"]["llamadas"]) == 10
                     and all(p["igual"] for p in pares))}


def t_config_grafo() -> dict:
    sys.path.insert(0, str(EXPERIMENT_DIR / "neo4j"))
    import grafos                                                         # registro, solo lectura
    filas = []
    for p in CONFIGS_GRAFO:
        c, sha_cfg = cargar_config(p)
        g = grafos.GRAFOS.get(c["grafo"])
        sha_kg = sha256_file(g["path"]) if g else None
        filas.append({"config": rel_repo(p), "config_sha256": sha_cfg, "grafo": c["grafo"],
                      "en_grafos_py": g is not None, "kg_sha256_esperado": c["kg_sha256_esperado"],
                      "sha256_grafos_py": g and g["sha256"], "commit_sellado": g and g["commit_sellado"],
                      "sha256_kg_json": sha_kg, "kg_path": g and rel_repo(g["path"]),
                      "backend_modo": [c["backend"], c["modo"]],
                      "ok": bool(g) and c["kg_sha256_esperado"] == g["sha256"] == sha_kg
                            and c["backend"] == "neo4j" and c["modo"] == "fulltext"})
    return {"filas": filas, "nota": "sin Neo4j: la carga y el test positivo del brazo del grafo son de A2.2",
            "PASS": all(f["ok"] for f in filas)}


GRUPOS = ["bm25_analizador", "bm25_determinismo", "bm25_transporte", "config_grafo",
          "regresion_denso", "denso_e0_vieja", "denso_r2b", "denso_r2b_dos"]


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
    res = {"generado": datetime.now().isoformat(timespec="seconds"), "unidad": "A2.1, tramo 1 — tests del servidor de fragmentos",
           "python": sys.version.split()[0], "platform": platform.platform(), "unicodedata": unicodedata.unidata_version,
           "grupos": grupos}
    fn = {"bm25_analizador": t_bm25_analizador, "bm25_determinismo": t_bm25_determinismo,
          "bm25_transporte": lambda: t_bm25_transporte(logs), "config_grafo": t_config_grafo,
          "regresion_denso": lambda: t_regresion_denso(a.out.parent), "denso_e0_vieja": t_denso_e0_vieja,
          "denso_r2b": lambda: t_denso_r2b(logs), "denso_r2b_dos": t_denso_r2b_dos}
    for g in grupos:
        res[g] = fn[g]()
        print(f"{g}: {'PASS' if res[g]['PASS'] else 'FAIL'}", flush=True)
    res["PASS"] = all(res[g]["PASS"] for g in grupos)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TOTAL:", "PASS" if res["PASS"] else "FAIL", "->", rel_repo(a.out))
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
