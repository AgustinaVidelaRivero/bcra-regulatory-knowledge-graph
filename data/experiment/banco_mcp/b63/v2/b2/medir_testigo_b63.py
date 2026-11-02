#!/usr/bin/env python3
"""medir_testigo_b63.py (v2/b2, etapa b2) — El testigo de B6.3 con su configuración sellada, y lo fijo y el pico de una sesión para la P
(decisiones de la autora del 26/10/2026, 19:00:06, y del 27/10/2026, 10:24:11, 11:31:49 y 11:35:20). USD 0: ninguna sesión llega al
modelo (el init apunta a un puerto cerrado; el testigo, a su servidor de captura local).

En orden; si algo no da, frena con su código y no sigue:
  1. la guarda de otro paso pago, con el patrón de B6.3 (correr_b63.PATRON_B1, el real): si corre uno, no lanza nada (7);
  2. el control de Docker de B6.3 (docker_b63.control, sobre neo4j-bcra-kg-indices-eval: docker info, inspect y stats, solo de ese
     contenedor) y el de la huella del Neo4j de los índices (control_neo4j_b63.estado, en bolt://127.0.0.1:47687): 14 y 15;
  3. lo fijo: la memoria en uso de la máquina (memoria_maquina) antes de lanzar el init, por el comando de B6.3 con `env -i`
     (comando_b63.zsh medir), y el swap;
  4. el lote init del runner (correr_b63.lote_init) con la configuración de agentes de B6.3 (config_agentes_b63.json) y una entrada DE
     TESTIGO (no es la sellada: preguntas de juguete, que el modo init no usa, y P = 1), una sesión por brazo con PREGUNTA_INIT, de a
     una;
  5. el testigo (aislamiento/testigo_aislamiento_b63.py) sobre ese init, con la misma configuración, de a una sesión, y leer_testigo
     (la fecha del día en un pedido, declarada; PASS_de_B63 y PASS_del_testigo_tal_cual);
  6. el control negativo de la comparación con el init, sobre el init real: una sesión con otro mcp_config y otra con una variable
     más en su entorno no dan la comparación (armar_sesion y comparar_con_init del testigo; no se lanza ninguna);
  7. durante el init y el testigo, el muestreo: la huella física (`footprint -p`, phys_footprint) del árbol de procesos de la sesión
     que corre (los descendientes del proceso que la lanza: su lanzador en el init, su CLI con su Node y su servidor con lo que
     cargue), con las funciones de n6/memoria_n6.py (importadas sin editar), y la memoria de la máquina en cada muestra. El muestreo
     es un hilo que toma una muestra detrás de otra, sin ninguna espera con plazo; el principal espera a sus hijos (subprocess);
  8. el pico de cada sesión, por la ventana de cada una (en el init, la del registro del lote; en el testigo, la de su stream: su
     nacimiento y su última escritura), y por brazo el mayor; la regla (memoria_b63.regla_P): P = 2 si lo fijo más dos veces el pico
     mayor queda en 14,5 GB o menos, P = 1 si lo fijo más el pico mayor, y si no, ninguna, y frena (13).
Escribe un JSON con todo eso, sin ningún texto: cuentas, sha256, banderas y memoria.

Uso (desde la raíz del repo, con env -i, PATH, HOME y NEO4J_URI=bolt://127.0.0.1:47687; sin ANTHROPIC_API_KEY):
  <python del .venv del repo> -B data/experiment/banco_mcp/b63/v2/b2/medir_testigo_b63.py --tmp <carpeta> --resultado <json>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # b63/v2/b2
BANCO_DIR = AQUI.parents[2]
for _p in (str(AQUI), str(BANCO_DIR / "n6"), str(BANCO_DIR / "aislamiento")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import correr_b63 as R                                       # noqa: E402  (el runner de la b2)
import memoria_n6 as MN6                                     # noqa: E402  (HEAD, solo import: tabla_rss, arbol, huella)

K, MEM, DK, N4, G = R.K, R.MEM, R.DK, R.N4, R.G
GB = 1e9
CONFIG = AQUI / "config_agentes_b63.json"
TESTIGO = BANCO_DIR / "aislamiento" / "testigo_aislamiento_b63.py"
HUELLA_B63 = "2645da6d01795d520f3c4ab5e237050c530238061f849cd7d1e0170be9223463"
PICO_DE_TESTIGO_GB = 4.0                                     # el de la entrada DE TESTIGO; el modo init no lo usa


# --------------------------------------------------------------------------------------------------------------------- #
# El muestreo y su lectura (funciones puras, que prueba el selftest)                                                    #
# --------------------------------------------------------------------------------------------------------------------- #
class Muestreo:
    """Un hilo que toma, una detrás de otra y sin esperas con plazo, la huella del árbol de descendientes de `raiz` y la memoria de la
    máquina. `raiz` puede cambiar entre etapas (el proceso que lanza las sesiones)."""

    def __init__(self, raiz: int, tomar_arbol=None, tomar_huella=None, tomar_maquina=None):
        self.raiz, self.etapa = raiz, "antes"
        self.muestras: list[dict] = []
        self.fin = threading.Event()
        self.tabla = tomar_arbol or MN6.tabla_rss
        self.huella = tomar_huella or MN6.huella
        self.maquina = tomar_maquina or MEM.memoria_maquina
        self.hilo = threading.Thread(target=self.correr, daemon=True)

    def tomar(self) -> None:
        t0 = time.time()
        pids = MN6.arbol(self.raiz, self.tabla())
        hf = self.huella(pids)
        m = self.maquina()
        self.muestras.append({"t": round((t0 + time.time()) / 2, 3), "etapa": self.etapa, "procesos": len(pids),
                              "huella_arbol_gb": round(hf / GB, 3), "en_uso_gb": m["en_uso_gb"], "swap_usado_gb": m["swap_usado_gb"]})

    def correr(self) -> None:
        while not self.fin.is_set():
            self.tomar()

    def empezar(self) -> None:
        self.hilo.start()

    def parar(self) -> None:
        self.fin.set()
        self.hilo.join()


def ventanas_init(registro: dict) -> list[dict]:
    return [{"id": s["id"], "brazo": s["brazo"], "etapa": "init", "t0": s["t_inicio"], "t1": s["t_fin"]}
            for s in registro["sesiones"] if s.get("t_inicio") is not None and s.get("t_fin") is not None]


def ventanas_testigo(out_dir: Path, res: dict) -> list[dict]:
    """La ventana de cada sesión del testigo: el nacimiento y la última escritura de su stream (el testigo abre el stream al lanzar la
    sesión y lo cierra al terminar)."""
    ventanas = []
    ids = [(i, r["brazo"]) for i, r in (res.get("por_sesion") or {}).items()] + \
          [(i, v["brazo"]) for i, v in (res.get("negativo") or {}).items()]
    for i, b in ids:
        p = Path(out_dir) / i / f"stream_{i}.jsonl"
        if not p.is_file():
            continue
        st = p.stat()
        ventanas.append({"id": i, "brazo": b, "etapa": "testigo", "t0": getattr(st, "st_birthtime", st.st_mtime), "t1": st.st_mtime})
    return ventanas


def picos(muestras: list[dict], ventanas: list[dict]) -> dict:
    """El pico de la huella del árbol en la ventana de cada sesión, y por brazo el mayor (con cuántas muestras lo vieron)."""
    por_sesion = []
    for v in ventanas:
        dentro = [m for m in muestras if v["t0"] <= m["t"] <= v["t1"]]
        por_sesion.append({"id": v["id"], "brazo": v["brazo"], "etapa": v["etapa"], "muestras": len(dentro),
                           "pico_gb": max((m["huella_arbol_gb"] for m in dentro), default=None),
                           "duracion_s": round(v["t1"] - v["t0"], 1)})
    por_brazo: dict = {}
    for s in por_sesion:
        if s["pico_gb"] is None:
            continue
        b = por_brazo.setdefault(s["brazo"], {"pico_gb": 0.0, "sesiones_con_muestras": 0})
        b["pico_gb"] = max(b["pico_gb"], s["pico_gb"])
        b["sesiones_con_muestras"] += 1
    return {"por_sesion": por_sesion, "por_brazo": dict(sorted(por_brazo.items())),
            "sesiones_sin_muestras": [s["id"] for s in por_sesion if not s["muestras"]]}


def regla(fijo_gb: float, por_brazo: dict) -> dict:
    mayor = max((b["pico_gb"] for b in por_brazo.values()), default=None)
    if mayor is None:
        return {"fijo_gb": fijo_gb, "pico_mayor_gb": None, "P": 0, "por_que": "sin picos medidos"}
    P = MEM.regla_P(fijo_gb, mayor)
    return {"fijo_gb": fijo_gb, "pico_mayor_gb": mayor, "brazo_del_pico_mayor": max(por_brazo, key=lambda b: por_brazo[b]["pico_gb"]),
            "fijo_mas_dos_picos_gb": round(fijo_gb + 2 * mayor, 3), "fijo_mas_un_pico_gb": round(fijo_gb + mayor, 3),
            "limite_gb": MEM.LIMITE_GB, "P": P}


# --------------------------------------------------------------------------------------------------------------------- #
# La entrada DE TESTIGO y lo que corre de verdad                                                                        #
# --------------------------------------------------------------------------------------------------------------------- #
def entrada_testigo(tmp: Path) -> tuple[Path, str]:
    """Una entrada DE TESTIGO con la configuración de B6.3: no es la sellada (la arma la mesa). Preguntas de juguete (el modo init no
    las usa: lanza PREGUNTA_INIT), P = 1 y un pico de testigo; los brazos y sus configs, los de config_agentes_b63.json."""
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    pr = BANCO_DIR / "b63" / "seco" / "preguntas_juguete_b63.json"
    ev2 = BANCO_DIR.parent / "ev2_juez"
    rel = lambda p: str(Path(p).resolve().relative_to(K.REPO_DIR.resolve()))           # noqa: E731
    e = {"unidad": "B6.3-b2: entrada DE TESTIGO (no es la sellada; la arma la mesa): el lote init del testigo, con la configuración de B6.3",
         "preguntas": {"ruta": rel(pr), "sha256": K.sha256_file(pr), "ids_en_orden": ["JUG01"]}, "k": 1,
         "config_agentes": {"ruta": rel(CONFIG), "sha256": K.sha256_file(CONFIG)},
         "brazos": {b: {"rol": x["rol"], "config_servidor": {"ruta": rel(BANCO_DIR / x["config_servidor"]),
                                                             "sha256": K.sha256_file(BANCO_DIR / x["config_servidor"])}}
                    for b, x in cfg["brazos"].items()},
         "R5": {"max_turns": cfg["corte_R5"]["max_turns"], "tope_tool_calls_prompt": cfg["corte_R5"]["tope_tool_calls_en_prompt"],
                "max_budget_usd": cfg["corte_R5"]["max_budget_usd_por_sesion"]},
         "tope_usd": 1.0, "freno_usd": 1.0, "P": 1, "pico_sesion_gb": PICO_DE_TESTIGO_GB,
         "neo4j": {"uri": K.NEO4J_URI_B63, "huella_contenido": HUELLA_B63},
         "banco_venv_vector": {"ruta": "venvs/banco_vector_py312",
                               "python": K.version_python(K.ruta_de_rel("venvs/banco_vector_py312")),
                               "pip_freeze_sha256": "24f4c0644699e4ffcd952a27ea572d6ccbae88e63382e5b1441fdae0479fb4cb"},
         "juez": {"archivos": [{"ruta": rel(ev2 / f), "sha256": K.sha256_file(ev2 / f)} for f in ("juez.py", "mapping.py", "prompt_juez_v1.md")]}}
    p = tmp / "entrada_testigo_b63.json"
    p.write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p, K.sha256_file(p)


def fijo_por_el_comando(entrada: Path) -> dict:
    r = subprocess.run(["zsh", str(AQUI / "comando_b63.zsh"), "medir", str(entrada)], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]})
    lineas = r.stdout.splitlines()
    d = json.loads(lineas[-1]) if r.returncode == 0 and lineas else {}
    return {"rc": r.returncode, "linea_del_comando": lineas[0] if lineas else None, "memoria": d.get("memoria"),
            "entorno_nombres": d.get("entorno_nombres"), "LC_CTYPE": d.get("LC_CTYPE")}


def negativos_de_la_comparacion(T, cfg: dict, init_dir: Path, tmp: Path) -> dict:
    """Sobre el init real: una sesión armada como la del testigo (sin lanzarla) da la comparación; con otro mcp_config o con una variable
    más en su entorno, no."""
    out = {}
    raiz = tmp / "negativos_comparacion_ses"
    for b in cfg["brazos"]:
        s = T.armar_sesion(cfg, b, f"COMPARACION-{b}", "Pregunta de prueba de la comparación: sin modelo.", tmp / "neg_cmp" / b, raiz,
                           "http://127.0.0.1:9/captura/x")
        bien = T.comparar_con_init(s, init_dir)["PASS"]
        otro = dict(s)
        otro_b = next(x for x in cfg["brazos"] if x != b)
        otro_mcp = str(BANCO_DIR / cfg["brazos"][otro_b]["mcp_config"])
        otro["cmd"] = [otro_mcp if x == s["mcp_json"] else x for x in s["cmd"]]
        otro["mcp_json"] = otro_mcp
        con_otro_mcp = T.comparar_con_init(otro, init_dir)["PASS"]
        mas = dict(s)
        mas["env"] = s["env"] | {"VARIABLE_DE_MAS_B63": "x"}
        con_variable = T.comparar_con_init(mas, init_dir)["PASS"]
        out[b] = {"sin_cambios_PASS": bien, "con_otro_mcp_config_PASS": con_otro_mcp, "con_una_variable_mas_PASS": con_variable,
                  "los_negativos_frenan": bien and not con_otro_mcp and not con_variable}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp", type=Path, required=True)
    ap.add_argument("--resultado", type=Path, required=True)
    a = ap.parse_args(argv)
    tmp = a.tmp.resolve()
    if tmp.is_relative_to(K.REPO_DIR.resolve()) or R.LA.dentro_de_git(tmp) is not None:
        raise SystemExit("ABORTO: --tmp dentro del repo o de git")
    if os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ABORTO: hay una ANTHROPIC_API_KEY en el entorno; el testigo corre sin ninguna clave (env -i)")
    if os.environ.get("NEO4J_URI") != K.NEO4J_URI_B63:
        raise SystemExit(f"ABORTO: NEO4J_URI tiene que ser {K.NEO4J_URI_B63}")
    tmp.mkdir(parents=True, exist_ok=True)
    res: dict = {"que": "el testigo de B6.3 con su configuración sellada, lo fijo y el pico de una sesión, y la P (USD 0)"}

    def terminar(codigo: int, motivo: str | None = None) -> int:
        res["codigo"], res["freno"] = codigo, motivo
        a.resultado.write_text(json.dumps(res, ensure_ascii=False, indent=1).replace(str(tmp), "<tmp>")
                               .replace(str(Path.home()), "$HOME") + "\n", encoding="utf-8")
        print(json.dumps({"codigo": codigo, "freno": motivo, "P": (res.get("regla") or {}).get("P"),
                          "PASS_de_B63": (res.get("leer_testigo") or {}).get("PASS_de_B63")}, ensure_ascii=False), flush=True)
        return codigo

    # 1. la guarda
    h = G.otro_paso_pago(raiz_lote=os.getpid(), patron=R.PATRON_B1)
    res["guarda"] = {"patron": "correr_b63.PATRON_B1 (b1 bis, igual en la b2)", "hallados": [{"script": x["script"]} for x in h]}
    if h:
        return terminar(G.CODIGO_PAGO, "otro paso pago corriendo")
    # 2. Docker y la huella
    d = DK.control(MEM.memoria_maquina)
    res["docker"] = d
    if not d["ok"]:
        return terminar(K.DOCKER, d["motivo"])
    n = N4.estado(HUELLA_B63, K.NEO4J_URI_B63)
    res["neo4j"] = {k: n.get(k) for k in ("NEO4J_URI", "grafo", "kg_meta_sha256", "kg_sha256_esperado", "n_nodos", "n_aristas",
                                          "huella_contenido", "ok", "motivo")}
    if not n["ok"]:
        return terminar(K.NEO4J, n["motivo"])
    # 3. lo fijo, por el comando con env -i
    entrada, sha_e = entrada_testigo(tmp)
    res["entrada_de_testigo"] = {"sha256": sha_e, "config_agentes_sha256": K.sha256_file(CONFIG)}
    f = fijo_por_el_comando(entrada)
    res["fijo"] = f
    if f["rc"] != 0 or not f["memoria"]:
        return terminar(K.PRECONDICION, "el comando no midió lo fijo")
    fijo = f["memoria"]["en_uso_gb"]
    e = K.cargar_entrada(entrada, sha_e)
    mu = Muestreo(os.getpid())
    mu.empezar()
    try:
        # 4. el init, de a una sesión (P = 1 en la entrada de testigo)
        mu.etapa = "init"
        init = R.lote_init(e, tmp / "init", tmp / "init_ses", lotes=tmp / "init_lotes", n=1)
        res["init"] = {"codigo": init["codigo"], "motivo": init["motivo"], "ids": init["ids"]}
        reg = json.loads((Path(init["salida"]) / "registro_lote.json").read_text(encoding="utf-8"))
        res["init"]["sesiones"] = [{"id": s["id"], "brazo": s["brazo"], "estado": s["estado"], "rc_lanzador": s.get("rc_lanzador"),
                                    "version_cli_init": s.get("version_cli_init")} for s in reg["sesiones"]]
        if init["codigo"]:
            return terminar(init["codigo"], f"el lote init: {init['motivo']}")
        # 5. el testigo, de a una sesión, sobre ese init
        mu.etapa = "testigo"
        out_t = tmp / "testigo"
        argv_t = [sys.executable, "-B", str(TESTIGO), "--out", str(out_t), "--sesiones", str(tmp / "testigo_ses"),
                  "--tmp", str(tmp / "testigo_tmp"), "--privado", str(tmp / "testigo_privado_captura"),
                  "--banco-paralelo", str(tmp / "testigo_banco_paralelo"), "--init", init["salida"],
                  "--resultado", str(tmp / "testigo_resultado.json"), "--config-agentes", str(CONFIG),
                  "--sha256-config", K.sha256_file(CONFIG)]
        (tmp / "testigo_banco_paralelo").mkdir(parents=True, exist_ok=True)
        env_t = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "NEO4J_URI": K.NEO4J_URI_B63,
                 "BANCO_VENV_VECTOR": os.environ["BANCO_VENV_VECTOR"]}
        p = subprocess.Popen(argv_t, env=env_t, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        mu.raiz = p.pid
        so, se = p.communicate()
        mu.raiz = os.getpid()
        res["testigo_rc"] = p.returncode
        res["testigo_consola"] = so.strip().splitlines()[-1:] if so else []
        tr = json.loads((tmp / "testigo_resultado.json").read_text(encoding="utf-8")) if (tmp / "testigo_resultado.json").is_file() else {}
    finally:
        mu.parar()
    res["testigo"] = {"PASS": tr.get("PASS"), "FRENO_n": len(tr.get("FRENO") or []), "configuracion": tr.get("configuracion"),
                      "plan": tr.get("plan"), "sesiones": sorted(tr.get("por_sesion") or {}), "negativo": tr.get("negativo"),
                      "otras_conexiones_de_los_cli_declaradas": tr.get("otras_conexiones_de_los_cli_declaradas"),
                      "claves_distintas_de_la_invalida": tr.get("claves_distintas_de_la_invalida"),
                      "ningun_pedido_al_modelo_sale_de_la_maquina": tr.get("ningun_pedido_al_modelo_sale_de_la_maquina")}
    res["leer_testigo"] = R.leer_testigo(tr) if tr else None
    # 6. los negativos de la comparación, sobre el init real
    T = __import__("testigo_aislamiento_b63")
    cfg = T.cargar_configuracion(CONFIG, K.sha256_file(CONFIG))
    res["negativos_de_la_comparacion"] = negativos_de_la_comparacion(T, cfg, Path(init["salida"]), tmp)
    # 7 y 8. los picos y la regla
    vent = ventanas_init(reg) + ventanas_testigo(out_t, tr)
    pk = picos(mu.muestras, vent)
    res["memoria"] = {"muestras": len(mu.muestras), "swap_antes_gb": f["memoria"]["swap_usado_gb"],
                      "swap_despues_gb": MEM.memoria_maquina()["swap_usado_gb"],
                      "swap_mayor_en_las_muestras_gb": max((m["swap_usado_gb"] for m in mu.muestras), default=None),
                      "en_uso_mayor_en_las_muestras_gb": max((m["en_uso_gb"] for m in mu.muestras), default=None), **pk}
    (tmp / "muestras_memoria_b63.json").write_text(json.dumps(mu.muestras, ensure_ascii=False) + "\n", encoding="utf-8")
    res["regla"] = regla(fijo, pk["por_brazo"])
    if res["regla"]["P"] == 0:
        return terminar(K.MEMORIA, "la regla no da ninguna P: lo fijo más el pico mayor pasa 14,5 GB")
    return terminar(0)


if __name__ == "__main__":
    raise SystemExit(main())
