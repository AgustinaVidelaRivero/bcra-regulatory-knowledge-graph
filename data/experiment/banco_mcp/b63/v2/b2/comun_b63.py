#!/usr/bin/env python3
"""comun_b63.py (v2/b2, etapa b2) — Lo común del runner de B6.3 (pre-registro FIRMADO, `adf20f3b`, §5 y §6): rutas, semillas, la entrada
sellada y sus controles, la carga de las preguntas, el orden y la cuenta por brazo y por fecha. Es b63/v2/b1bis/comun_b63.py (etapa b1
bis) con lo de la etapa b2 (decisión de la autora del 28/10/2026, 07:27:21, sobre la del 26/10/2026, 21:58:48): el directorio del juez,
con su caché, fuera del repo, al lado de RESULTADOS (JUEZ_DIR); y el lanzador de la sesión, el de esta carpeta. La b1 bis era
b63/comun_b63.py (etapa a) con lo de la etapa b1: R5, el de la entrada y uno de los dos admitidos del pre-registro
(agentes/lanzar_lote_paralelo_r5.py; decisiones de la autora del 26/10/2026, 22:45:52); el sha256 del `pip freeze --all` del venv del
banco (§5, `24f4c064…`); el Neo4j de B6.3 (decisión del 27/10/2026, 10:24:11: NEO4J_URI y la huella de contenido); y P, 1 o 2, con el
pico de una sesión (decisiones del 27/10, 11:31:49 y 11:35:20). En la etapa b1 bis (decisiones de la autora del 27/10/2026, 21:52:30):
el código 16, la clave inválida, que frena el lote a la primera; las salidas de las sesiones, fuera del repo (RESULTADOS: la meta
completa trae texto y no se commitea; al lado va la meta sin texto, que es la que se commitea); y el lanzador de la sesión, el de esta
carpeta.

Las preguntas, sus criterios y sus citas los lee solo este código: ninguna función de este módulo imprime ni escribe su texto. Lo que
sale de acá hacia un archivo son ids, nombres de brazos, fechas, cuentas y sha256.

La entrada sellada (la arma la mesa; su sha256 lo da el comando que la usa) es un JSON con:
  preguntas        {ruta, sha256, ids_en_orden, esquema}: el archivo de las preguntas de B6.3 que entran por el N, en el orden de las
                   olas aprobadas (§6); `esquema` dice dónde está cada campo (por defecto, el de EV2: preguntas[*].{id, pregunta,
                   gold.criterios[*].{criterio, cita_textual}});
  k                las corridas por pregunta y por brazo (H-7);
  config_agentes   {ruta, sha256}: la configuración de agentes de los tres brazos (la forma de paralelo/config_agentes_n6_prueba.json:
                   base, versión sellada del CLI, modelo, modo, brazos, prompt, corte_R5 y env_por_sesion);
  brazos           {nombre: {rol, config_servidor: {ruta, sha256}}}: el grafo («grafo», con la configuración de N7), la principal de
                   fragmentos («fragmentos_principal») y el denso («fragmentos_denso»); opcional, `marcas_d10`, regex de más para D-10;
  R5               {max_turns, tope_tool_calls_prompt, max_budget_usd};
  tope_usd, freno_usd   el tope del §12 y su freno, para el agente y el juez juntos;
  banco_venv_vector     {ruta, python, pip_freeze_sha256}: el venv de BANCO_VENV_VECTOR, la versión de su Python
                   (`<ruta>/bin/python --version`) y el sha256 de su `pip freeze --all` (el del §5: `24f4c064…`);
  neo4j            {uri, huella_contenido}: el Neo4j de B6.3 (bolt://127.0.0.1:47687, el de los índices) y la huella de contenido del
                   grafo evaluado (`2645da6d…`), que el runner controla antes de lanzar;
  P, pico_sesion_gb     las sesiones a la vez, 1 o 2 (la regla de la decisión 10: 2 si lo fijo más dos picos queda en 14,5 GB o
                   menos), y el pico de una sesión (su CLI, su Node y su servidor), que mide el testigo;
  juez             {archivos: [{ruta, sha256}]}: el juez de EV2 (juez.py, mapping.py y su prompt), con el sha256 de HEAD.
Las rutas son relativas al repo o empiezan con «~/» (la carpeta personal).
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent                      # data/experiment/banco_mcp/b63/v2/b2
B63 = AQUI.parents[1]                                       # data/experiment/banco_mcp/b63
BANCO_DIR = B63.parent
for _p in (str(BANCO_DIR), str(BANCO_DIR / "agentes"), str(BANCO_DIR / "paralelo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from comun_banco import REPO_DIR, rel_repo, sha256_file     # noqa: E402

FUERA_DEL_REPO = Path.home() / "INGENIERIA IA" / "TESIS" / "fuera_del_repo"
RESULTADOS = FUERA_DEL_REPO / "banco_b63" / "resultados"      # b1 bis: fuera del repo (la meta completa trae texto; decisión 3)
JUEZ_DIR = FUERA_DEL_REPO / "banco_b63" / "juez"              # b2: fuera del repo, con su caché (decisión del 28/10/2026)
CACHE_JUEZ = JUEZ_DIR / "cache"
SESIONES = FUERA_DEL_REPO / "banco_b63" / "sesiones"         # su cwd/ y su config/ (fuera del repo y de git, §5)
ORIGINALES = FUERA_DEL_REPO / "banco_mcp_originales_B63"     # los streams y transcripciones sin enmascarar (§5)
LANZADOR_SESION = "b63/v2/b2/lanzar_agente_b63.py"           # relativo al banco, como lo pide el lanzador del lote

SEMILLA_ORDEN = "B63:orden_corridas:v1"                      # D-4 (§6)
ROLES = ("grafo", "fragmentos_principal", "fragmentos_denso")
INTENTOS_MAX = 3                                             # fallas de infraestructura: hasta 3 intentos en total (§6)
CORTES = ("error_max_turns", "error_max_budget_usd")         # las corridas cortadas (§6); el del presupuesto, el de gate/corrida_faseB
P_ADMITIDOS = (1, 2)                                         # decisión del 27/10/2026, 11:31:49 y 11:35:20
NEO4J_URI_B63 = "bolt://127.0.0.1:47687"                     # el Neo4j propio de los índices (decisión del 27/10/2026, 10:24:11)
# Los códigos: los del lanzador del lote tal cual (2 el gasto, 3 el lote inválido, 4 el cwd, 5 el aislamiento, 6 la versión del CLI,
# 7 otro paso pago) y el de la extracción de guardas_lote (9); el del juez es el 2, porque su gasto va en la misma guarda; y el 10, una
# precondición del runner (la entrada, el juez, el SDK, el patrón); el 11, el control del disco (el 3 de A2.1, que en el lanzador del
# lote es el del lote inválido); y, en la etapa b1: el 12, tres formas desconocidas (la opción (d)); el 13, la guarda de memoria; el
# 14, el control de Docker; el 15, el Neo4j de B6.3 (su NEO4J_URI o su huella); y, en la etapa b1 bis, el 16, la clave inválida (un
# 401 de la API: frena el lote a la primera, la sesión no cuenta y se corre al retomar).
PRECONDICION = 10
DISCO = 11
DESCONOCIDAS = 12
MEMORIA = 13
DOCKER = 14
NEO4J = 15
CLAVE_INVALIDA = 16
ESQUEMA_EV2 = {"lista": "preguntas", "id": "id", "pregunta": "pregunta", "criterios": "gold.criterios",
               "criterio": "criterio", "cita": "cita_textual"}
ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")      # el de agentes/lanzar_lote_paralelo.py


class FrenoB63(Exception):
    """Un freno del runner, con su código (PRECONDICION: una precondición del runner; los del lote, tal cual)."""

    def __init__(self, motivo: str, codigo: int | None = None):
        super().__init__(motivo)
        self.codigo = PRECONDICION if codigo is None else codigo


def frena(motivo: str, codigo: int | None = None):
    raise FrenoB63(motivo, codigo)


def ruta_de_rel(r: str) -> Path:
    """«~/x» es la carpeta personal; lo demás, relativo al repo (o absoluto)."""
    return Path.home() / r[2:] if r.startswith("~/") else (REPO_DIR / r)


def sello(d: dict, que: str) -> Path:
    """El archivo de un {ruta, sha256} de la entrada, controlado: frena si no existe o no da su sha256."""
    if not isinstance(d, dict) or not d.get("ruta") or not d.get("sha256"):
        frena(f"{que}: falta su ruta o su sha256 en la entrada sellada")
    p = ruta_de_rel(d["ruta"])
    if not p.is_file():
        frena(f"{que}: no existe {d['ruta']}")
    s = sha256_file(p)
    if s != d["sha256"]:
        frena(f"{que}: {d['ruta']} da {s[:12]}…, no el sha256 sellado {d['sha256'][:12]}…")
    return p


def version_python(venv: Path) -> str | None:
    py = venv / "bin" / "python"
    if not py.is_file():
        return None
    r = subprocess.run([str(py), "--version"], capture_output=True, text=True)
    return (r.stdout or r.stderr).strip().split()[-1] if r.returncode == 0 else None


def pip_freeze_sha256(venv: Path) -> str | None:
    """El sha256 del `pip freeze --all` del venv (la forma del §5: la que dio `24f4c064…`, 63 líneas), sin red y sin escribir nada."""
    py = venv / "bin" / "python"
    if not py.is_file():
        return None
    r = subprocess.run([str(py), "-I", "-B", "-m", "pip", "freeze", "--all"], capture_output=True,
                       env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                            "PIP_NO_INPUT": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    import hashlib
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def cargar_entrada(ruta: Path, sha_esperado: str) -> dict:
    """La entrada sellada, con todos sus controles, antes de lanzar nada. Devuelve la entrada más las rutas resueltas en «_rutas»."""
    ruta = Path(ruta)
    if not ruta.is_file():
        frena(f"no existe la entrada sellada {rel_repo(ruta)}")
    s = sha256_file(ruta)
    if s != sha_esperado:
        frena(f"la entrada sellada da {s[:12]}…, no el sha256 del comando {str(sha_esperado)[:12]}…")
    e = json.loads(ruta.read_text(encoding="utf-8"))
    faltan = [c for c in ("preguntas", "k", "config_agentes", "brazos", "R5", "tope_usd", "freno_usd", "banco_venv_vector", "juez",
                          "neo4j", "P", "pico_sesion_gb") if c not in e]
    if faltan:
        frena(f"a la entrada sellada le falta {faltan}")
    rutas = {"entrada": ruta}
    if not (isinstance(e["k"], int) and e["k"] >= 1):
        frena("k tiene que ser un entero de al menos 1")
    if not (0 <= float(e["freno_usd"]) <= float(e["tope_usd"])):
        frena(f"el freno ({e['freno_usd']}) tiene que estar entre 0 y el tope ({e['tope_usd']})")
    if e["P"] not in P_ADMITIDOS or isinstance(e["P"], bool):
        frena(f"P tiene que ser uno de {list(P_ADMITIDOS)}, no {e['P']!r}")
    if not isinstance(e["pico_sesion_gb"], (int, float)) or isinstance(e["pico_sesion_gb"], bool) or not e["pico_sesion_gb"] > 0:
        frena("pico_sesion_gb tiene que ser un número mayor que 0")
    n = e["neo4j"]
    if not isinstance(n, dict) or n.get("uri") != NEO4J_URI_B63 or not re.fullmatch(r"[0-9a-f]{64}", str(n.get("huella_contenido"))):
        frena(f"neo4j de la entrada: uri {NEO4J_URI_B63} y una huella_contenido de 64 hexadecimales")
    # la configuración de agentes y la de cada brazo
    rutas["config_agentes"] = sello(e["config_agentes"], "config_agentes")
    cfg = json.loads(rutas["config_agentes"].read_text(encoding="utf-8"))
    base = cfg.get("base") or {}
    if not base.get("ruta") or sha256_file(BANCO_DIR / base["ruta"]) != base.get("sha256"):
        frena("config_agentes: su base no es la declarada")
    if not rutas["config_agentes"].resolve().is_relative_to(BANCO_DIR.resolve()):
        frena("config_agentes: tiene que estar dentro del banco (el lanzador del lote la toma relativa a él)")
    brazos = e["brazos"]
    if set(brazos) != set(cfg.get("brazos") or {}):
        frena(f"los brazos de la entrada {sorted(brazos)} no son los de config_agentes {sorted(cfg.get('brazos') or {})}")
    roles = sorted(b.get("rol") for b in brazos.values())
    if roles != sorted(ROLES):
        frena(f"los roles de los brazos son {roles}, no {sorted(ROLES)}")
    for b, d in sorted(brazos.items()):
        if not ID_VALIDO.match(b):
            frena(f"nombre de brazo no admitido: {b!r}")
        rutas[f"config_servidor:{b}"] = sello(d.get("config_servidor"), f"config_servidor de {b}")
        if cfg["brazos"][b].get("config_servidor") != rel_banco(rutas[f"config_servidor:{b}"]):
            frena(f"config_servidor de {b}: no es la que nombra config_agentes")
        for clave in ("mcp_config", "bloque_tools"):
            if not (BANCO_DIR / cfg["brazos"][b][clave]).is_file():
                frena(f"{b}: no existe su {clave}")
        for r in cfg["brazos"][b].get("archivos_servidor") or []:
            if not (BANCO_DIR / r).is_file():
                frena(f"{b}: no existe {r}")
    if not (BANCO_DIR / cfg["prompt"]["plantilla"]).is_file():
        frena("no existe la plantilla del prompt")
    if not cfg.get("claude_code_version_sellada"):
        frena("config_agentes: sin claude_code_version_sellada")
    # R5: el de la entrada, el de la configuración y uno de los dos admitidos del lanzador del lote r5 (NOTA_lanzar_lote_paralelo_r5.md, §3)
    import lanzar_lote_paralelo_r5 as LOTE                  # noqa: E402  (solo admitido y R5_ADMITIDOS)
    r5 = e["R5"]
    c = cfg["corte_R5"]
    if {"max_turns": c["max_turns"], "tope_tool_calls_prompt": c["tope_tool_calls_en_prompt"],
            "max_budget_usd": c["max_budget_usd_por_sesion"]} != r5:
        frena(f"R5 de la entrada {r5} no es el de config_agentes")
    if not LOTE.admitido(r5):
        frena(f"R5 de la entrada {r5} no es uno de los admitidos {list(LOTE.R5_ADMITIDOS)}")
    # BANCO_VENV_VECTOR: de la entrada, nunca de la terminal
    v = e["banco_venv_vector"]
    if not isinstance(v, dict) or not v.get("ruta") or not v.get("python") or not v.get("pip_freeze_sha256"):
        frena("la entrada sellada no trae BANCO_VENV_VECTOR (su ruta, la versión de su Python y el sha256 de su pip freeze --all)")
    venv = ruta_de_rel(v["ruta"])
    if not venv.is_dir():
        frena(f"BANCO_VENV_VECTOR de la entrada no existe: {v['ruta']}")
    pv = version_python(venv)
    if pv != v["python"]:
        frena(f"el Python de BANCO_VENV_VECTOR da {pv!r}, no {v['python']!r}")
    pf = pip_freeze_sha256(venv)
    if pf != v["pip_freeze_sha256"]:
        frena(f"el pip freeze --all de BANCO_VENV_VECTOR da {str(pf)[:12]}…, no el sha256 sellado {str(v['pip_freeze_sha256'])[:12]}…")
    rutas["banco_venv_vector"] = venv
    # el juez y las preguntas
    for k, d in enumerate((e["juez"] or {}).get("archivos") or []):
        rutas[f"juez:{k}"] = sello(d, f"archivo {k + 1} del juez")
    if not (e["juez"] or {}).get("archivos"):
        frena("la entrada sellada no trae los archivos del juez con su sha256")
    rutas["preguntas"] = sello(e["preguntas"], "preguntas")
    e = dict(e)
    e["_ruta"] = ruta
    e["_rutas"] = rutas
    e["_cfg"] = cfg
    e["_sha256"] = s
    e["_sha256_sin_tope"] = sha_sin_tope(json.loads(ruta.read_text(encoding="utf-8")))
    return e


def sha_sin_tope(e: dict) -> str:
    """El sha256 de la entrada sin el tope ni el freno (su JSON canónico): retomar una corrida pide la misma entrada, salvo esos dos,
    que la autora puede subir después de un corte del juez o de la guarda del gasto."""
    import hashlib
    x = {k: v for k, v in e.items() if k not in ("tope_usd", "freno_usd") and not k.startswith("_")}
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def rel_banco(p: Path) -> str:
    return str(Path(p).resolve().relative_to(BANCO_DIR.resolve()))


def _campo(d: dict, punto: str):
    for k in punto.split("."):
        d = (d or {}).get(k)
    return d


def cargar_preguntas(e: dict) -> dict:
    """{qid: {"pregunta", "criterios": [{criterio, cita_textual}]}} de los ids_en_orden de la entrada. Solo por código."""
    esq = ESQUEMA_EV2 | (e["preguntas"].get("esquema") or {})
    d = json.loads(e["_rutas"]["preguntas"].read_text(encoding="utf-8"))
    lista = _campo(d, esq["lista"]) if isinstance(d, dict) else d
    if not isinstance(lista, list):
        frena("el archivo de preguntas no tiene la lista que dice su esquema")
    todas = {}
    for x in lista:
        q = _campo(x, esq["id"])
        if q in todas:
            frena("un id repetido en el archivo de preguntas")
        crits = _campo(x, esq["criterios"]) or []
        todas[q] = {"pregunta": _campo(x, esq["pregunta"]),
                    "criterios": [{"criterio": c.get(esq["criterio"]), "cita_textual": c.get(esq["cita"])} for c in crits]}
    ids = e["preguntas"].get("ids_en_orden") or []
    if not ids or len(set(ids)) != len(ids):
        frena("ids_en_orden vacío o con repetidos")
    out = {}
    for q in ids:
        if q not in todas:
            frena("un id de ids_en_orden no está en el archivo de preguntas")
        v = todas[q]
        if not ID_VALIDO.match(str(q)):
            frena("un id de pregunta con caracteres que el lanzador del lote no admite")
        if not isinstance(v["pregunta"], str) or not v["pregunta"].strip():
            frena("una pregunta sin texto")
        if not v["criterios"] or not all(isinstance(c["criterio"], str) and c["criterio"].strip()
                                         and isinstance(c["cita_textual"], str) and c["cita_textual"].strip()
                                         for c in v["criterios"]):
            frena("una pregunta sin criterios, o un criterio sin su texto o sin su cita")
        out[q] = v
    return out


# --------------------------------------------------------------------------------------------------------------------- #
# El orden (§6) y los ids                                                                                               #
# --------------------------------------------------------------------------------------------------------------------- #
def permutacion(qid: str, r: int, brazos, semilla: str = SEMILLA_ORDEN) -> list[str]:
    """La de los brazos de la pregunta qid en su repetición r: random.Random(f"{semilla}:{id}:{r}").shuffle sobre los nombres
    ordenados (D-4)."""
    xs = sorted(brazos)
    random.Random(f"{semilla}:{qid}:{r}").shuffle(xs)
    return xs


def orden_bloques(ids: list[str], k: int, brazos, semilla: str = SEMILLA_ORDEN) -> list[dict]:
    """Por pregunta (en el orden de las olas aprobadas) y por repetición, con los brazos de cada bloque seguidos y sorteados."""
    return [{"bloque": nombre_bloque(q, r), "qid": q, "r": r, "brazos": permutacion(q, r, brazos, semilla)}
            for q in ids for r in range(1, k + 1)]


def nombre_bloque(qid: str, r: int) -> str:
    return f"{qid}-r{r}"


def id_sesion(qid: str, r: int, brazo: str, intento: int = 1) -> str:
    """El id de la sesión: termina con el brazo en el primer intento; los reintentos de infraestructura llevan -i2 o -i3."""
    base = f"B63-{qid}-r{r}-{brazo}"
    return base if intento == 1 else f"{base}-i{intento}"


# --------------------------------------------------------------------------------------------------------------------- #
# La cuenta por brazo y por fecha (decisión de la autora del 26/10/2026, recibida a las 16:07:59)                       #
# --------------------------------------------------------------------------------------------------------------------- #
def cuenta_fechas(sesiones: list[dict]) -> dict:
    """De las sesiones lanzadas ({bloque, brazo, fecha, intento}): cuántas de cada brazo corrieron en cada fecha, y los bloques
    (una pregunta y una repetición) cuyas sesiones no corrieron todas en la misma fecha (registro, §88). Sin ningún texto."""
    lanzadas = [s for s in sesiones if s.get("fecha")]
    por_brazo: dict[str, Counter] = {}
    for s in lanzadas:
        por_brazo.setdefault(s["brazo"], Counter())[s["fecha"]] += 1
    bloques: dict[str, dict] = {}
    for s in lanzadas:
        bloques.setdefault(s["bloque"], {}).setdefault(s["brazo"], set()).add(s["fecha"])
    distintas = [{"bloque": b, "fechas_por_brazo": {br: sorted(f) for br, f in sorted(v.items())}}
                 for b, v in bloques.items() if len(set().union(*v.values())) > 1]
    return {"regla": "«En B6.3 se informa cuántas sesiones de cada brazo corrieron en cada fecha.» (decisión de la autora del "
                     "26/10/2026, recibida a las 16:07:59); la fecha es la del reloj del lanzador del lote al empezar cada sesión, en "
                     "hora local; cuentan todas las sesiones lanzadas, también los reintentos",
            "por_brazo_y_fecha": {b: dict(sorted(c.items())) for b, c in sorted(por_brazo.items())},
            "por_fecha": dict(sorted(Counter(s["fecha"] for s in lanzadas).items())),
            "n_sesiones": len(lanzadas), "n_bloques": len(bloques),
            "bloques_con_fechas_distintas": distintas, "n_bloques_con_fechas_distintas": len(distintas)}
