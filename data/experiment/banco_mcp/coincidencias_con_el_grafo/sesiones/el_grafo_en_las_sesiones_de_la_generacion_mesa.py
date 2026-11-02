"""el_grafo_en_las_sesiones_de_la_generacion_mesa.py — Mesa, §393 (01/11/2026): si alguna sesión que redactó preguntas o criterios de
B6.3 (P2) o de B6.4 pudo leer el grafo. Recorre las transcripciones de los proyectos de `fuera_del_repo/b63_p2` y `fuera_del_repo/b64_p2`
en `la configuración del asistente de la carpeta personal/projects/`, con las de sus subagentes, y de cada renglón lee solo:
  - de los mensajes del usuario (el despacho y los «seguí»): si nombran un archivo, una carpeta o una herramienta del grafo (la
    expresión `GRAFO`), y cuántas veces dicen «grafo»; nunca su texto;
  - de cada llamada a una herramienta: su nombre y, de sus argumentos, solo si nombran algo del grafo (lo que da la expresión `GRAFO`);
    las herramientas de un servidor MCP, por su nombre;
  - la hora, el modelo y los nombres de los archivos de la generación que escribe (para saber qué etapa es).
Revisa también si las carpetas `b63_p2/` y `b64_p2/` traen algún archivo cuyo nombre o ruta es del grafo. Imprime solo ids, horas,
nombres de herramientas, rutas y cuentas. USD 0.
  python3 -I -B el_grafo_en_las_sesiones_de_la_generacion_mesa.py <fuera_del_repo>
"""
import collections
import json
import re
import sys
from pathlib import Path

F = Path(sys.argv[1]).resolve()
GRAFO = re.compile(r"kg\.json(?:\.gz)?|ens_[0-9a-z_]+/r2|reaplicacion_unica|r2b_sincola|grafo_v2|reensamblado_v3|kg_n7|mcp_kg|"
                   r"servidor_mcp_kg|buscar_nodos|ver_nodo|ver_vecinos|neo4j|\.graphml|nodes\.json|edges\.json", re.I)
PALABRA_GRAFO = re.compile(r"\bgrafo", re.I)
ESCRIBE = re.compile(r"(FRENO|registro_generacion|checkpoint|ola_|reemplazos|reubicados|config_B6|plan_tipos|preguntas)[^/]*$")


def proyecto(sub):
    return Path.home() / ".claude" / "projects" / ("-" + str(F / sub).strip("/").replace("/", "-").replace(" ", "-").replace("_", "-"))


def textos(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from textos(v)
    elif isinstance(x, list):
        for v in x:
            yield from textos(v)


def mirar(t: Path):
    horas, modelos, herr, mcp, escribe = [], collections.Counter(), collections.Counter(), collections.Counter(), set()
    g_llamadas, g_desp = collections.Counter(), collections.Counter()
    n_usuario = m_grafo = 0
    primero = None
    for ln in t.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            m = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if m.get("timestamp"):
            horas.append(m["timestamp"])
        msg = m.get("message") or {}
        if m.get("type") == "user" and not m.get("isMeta"):
            cont = msg.get("content")
            txt = [cont] if isinstance(cont, str) else [b.get("text", "") for b in cont or []
                                                        if isinstance(b, dict) and b.get("type") == "text"]
            for s in txt:
                if not s:
                    continue
                n_usuario += 1
                primero = primero if primero is not None else n_usuario
                for h in GRAFO.findall(s):
                    g_desp[h.lower()] += 1
                m_grafo += len(PALABRA_GRAFO.findall(s))
        if m.get("type") != "assistant":
            continue
        modelos[msg.get("model")] += 1
        for b in msg.get("content") or []:
            if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                continue
            nombre = b.get("name", "")
            herr[nombre] += 1
            if nombre.startswith("mcp__"):
                mcp[nombre] += 1
            for s in textos(b.get("input") or {}):
                for h in GRAFO.findall(s):
                    g_llamadas[(nombre, h.lower())] += 1
            if nombre in ("Write", "Edit"):
                n = Path(str((b.get("input") or {}).get("file_path", ""))).name
                if ESCRIBE.search(n):
                    escribe.add(n)
    return {"horas": (min(horas), max(horas)) if horas else None, "modelos": dict(modelos), "herramientas": dict(herr), "mcp": dict(mcp),
            "grafo_en_llamadas": dict(g_llamadas), "grafo_en_mensajes_del_usuario": dict(g_desp), "mensajes_del_usuario": n_usuario,
            "veces_que_dicen_grafo": m_grafo, "escribe": sorted(escribe)}


for sub in ("b63_p2", "b64_p2"):
    pr = proyecto(sub)
    ts = sorted(pr.glob("*.jsonl")) + sorted(pr.glob("*/subagents/*.jsonl"))
    print(f"== {sub}: el proyecto existe {pr.is_dir()}; transcripciones {len(ts)} (con las de subagentes)")
    for t in ts:
        r = mirar(t)
        nombre = t.stem if t.parent == pr else f"{t.parent.parent.name[:8]}…/subagente {t.stem[:8]}…"
        print(f"- {nombre}: de {r['horas'][0] if r['horas'] else '-'} a {r['horas'][1] if r['horas'] else '-'} (UTC); modelos "
              f"{r['modelos']}; mensajes del usuario {r['mensajes_del_usuario']}")
        print(f"    en los mensajes del usuario: archivos o herramientas del grafo {r['grafo_en_mensajes_del_usuario'] or 'ninguno'}; la "
              f"palabra «grafo», {r['veces_que_dicen_grafo']} veces")
        print(f"    llamadas a herramientas: {sum(r['herramientas'].values())} ({r['herramientas']}); "
              f"de un servidor MCP: {r['mcp'] or 'ninguna'}")
        print(f"    llamadas que nombran algo del grafo: {r['grafo_en_llamadas'] or 'ninguna'}")
        print(f"    escribe: {r['escribe']}")
    d = F / sub
    del_grafo = [str(x.relative_to(d)) for x in d.rglob("*") if GRAFO.search(str(x.relative_to(d)))]
    print(f"   en la carpeta {sub}/: {sum(1 for _ in d.rglob('*'))} entradas; con nombre o ruta del grafo: {del_grafo or 'ninguna'}")
