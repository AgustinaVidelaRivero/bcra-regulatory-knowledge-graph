"""el_grafo_en_las_seis_carpetas_mesa.py — Mesa, §395 (01/11/2026): la búsqueda de la §393
(`el_grafo_en_las_sesiones_de_la_generacion_mesa.py`), extendida a las 6 carpetas de `la configuración del asistente de la carpeta personal/projects/` de `fuera_del_repo` que
nombran a B6.3 o a B6.4 y que la §393 no buscó. Mismo método: de cada transcripción, y de las de sus subagentes, lee solo
  - de los mensajes del usuario: cuántos son y cuántas veces nombran un archivo, una carpeta o una herramienta del grafo (la expresión
    `GRAFO` de la §393) o dicen «grafo»; nunca su texto;
  - de cada llamada a una herramienta: su nombre; las de un servidor MCP, por su nombre; si sus argumentos nombran algo del grafo;
  - las rutas que escribe: el archivo de cada Write, Edit o NotebookEdit, y las rutas de archivo (`*.json`, `.jsonl`, `.md`, `.csv`,
    `.tsv`, `.txt`) que un comando de Bash escribe con `>`, `>>` o `tee`. De esas, cuáles tienen nombre de preguntas o de criterios
    (`REDACTA`): eso es lo que dice si la sesión redactó preguntas o criterios;
  - la hora y el modelo.
Revisa también si su carpeta de trabajo trae archivos con nombre del grafo o de preguntas o criterios. Imprime solo ids, horas,
nombres de herramientas, rutas y cuentas; las rutas, con la carpeta personal cambiada por `~`. USD 0.
  python3 -I -B el_grafo_en_las_seis_carpetas_mesa.py <fuera_del_repo>
"""
import collections
import json
import re
import sys
from pathlib import Path

F = Path(sys.argv[1]).resolve()
SEIS = ("analisis_b64", "analisis_b64_corr", "b63_etapa1", "b63_p3", "control_36_b63", "runner_b64")
GRAFO = re.compile(r"kg\.json(?:\.gz)?|ens_[0-9a-z_]+/r2|reaplicacion_unica|r2b_sincola|grafo_v2|reensamblado_v3|kg_n7|mcp_kg|"
                   r"servidor_mcp_kg|buscar_nodos|ver_nodo|ver_vecinos|neo4j|\.graphml|nodes\.json|edges\.json", re.I)
PALABRA_GRAFO = re.compile(r"\bgrafo", re.I)
REDACTA = re.compile(r"pregunt|criteri|ola_\d|reemplaz|reubicad|aprobad|borrador|rubric", re.I)
ESCRIBE_BASH = re.compile(r"(?:>>?|\btee\b(?:\s+-a)?)\s*[\"']?([~\w./$-]+\.(?:json|jsonl|md|csv|tsv|txt))")
CASA = str(Path.home())


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
    horas, modelos, herr, mcp = [], collections.Counter(), collections.Counter(), collections.Counter()
    g_llamadas, g_desp, escritas = collections.Counter(), collections.Counter(), set()
    n_usuario = m_grafo = 0
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
            for s in [cont] if isinstance(cont, str) else [b.get("text", "") for b in cont or []
                                                           if isinstance(b, dict) and b.get("type") == "text"]:
                if s:
                    n_usuario += 1
                    for h in GRAFO.findall(s):
                        g_desp[h.lower()] += 1
                    m_grafo += len(PALABRA_GRAFO.findall(s))
        if m.get("type") != "assistant":
            continue
        modelos[msg.get("model")] += 1
        for b in msg.get("content") or []:
            if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                continue
            nombre, ent = b.get("name", ""), b.get("input") or {}
            herr[nombre] += 1
            if nombre.startswith("mcp__"):
                mcp[nombre] += 1
            for s in textos(ent):
                for h in GRAFO.findall(s):
                    g_llamadas[(nombre, h.lower())] += 1
            if nombre in ("Write", "Edit", "NotebookEdit"):
                escritas.add(str(ent.get("file_path") or ent.get("notebook_path") or ""))
            elif nombre == "Bash":
                escritas.update(ESCRIBE_BASH.findall(str(ent.get("command", ""))))
    escritas = sorted(e.replace(CASA, "~") for e in escritas if e)
    return {"horas": (min(horas), max(horas)) if horas else None, "modelos": dict(modelos), "herramientas": dict(herr),
            "mcp": dict(mcp), "grafo_en_llamadas": dict(g_llamadas), "grafo_en_mensajes_del_usuario": dict(g_desp),
            "mensajes_del_usuario": n_usuario, "veces_que_dicen_grafo": m_grafo, "escritas": escritas,
            "redacta": [e for e in escritas if REDACTA.search(Path(e).name)]}


for sub in SEIS:
    pr = proyecto(sub)
    ts = sorted(pr.glob("*.jsonl")) + sorted(pr.glob("*/subagents/*.jsonl"))
    print(f"== {sub}: la carpeta de proyecto existe {pr.is_dir()}; transcripciones {len(ts)} (con las de subagentes)")
    for t in ts:
        r = mirar(t)
        nombre = t.stem if t.parent == pr else f"{t.parent.parent.name[:8]}…/subagente {t.stem[:8]}…"
        print(f"- {nombre}: de {r['horas'][0] if r['horas'] else '-'} a {r['horas'][1] if r['horas'] else '-'} (UTC); modelos "
              f"{r['modelos']}; mensajes del usuario {r['mensajes_del_usuario']}")
        print(f"    en los mensajes del usuario: archivos o herramientas del grafo {r['grafo_en_mensajes_del_usuario'] or 'ninguno'}; la "
              f"palabra «grafo», {r['veces_que_dicen_grafo']} veces")
        print(f"    llamadas a herramientas: {sum(r['herramientas'].values())} ({r['herramientas']}); de un servidor MCP: "
              f"{r['mcp'] or 'ninguna'}")
        print(f"    llamadas que nombran algo del grafo: {r['grafo_en_llamadas'] or 'ninguna'}")
        print(f"    rutas que escribe: {len(r['escritas'])}; con nombre de preguntas o criterios: {r['redacta'] or 'ninguna'}")
    d = F / sub
    rel = [str(x.relative_to(d)) for x in d.rglob("*")]
    print(f"   en la carpeta {sub}/: {len(rel)} entradas; con nombre o ruta del grafo: {len([x for x in rel if GRAFO.search(x)])}; "
          f"con nombre de preguntas o criterios: {sorted(x for x in rel if REDACTA.search(Path(x).name))[:12] or 'ninguna'}"
          f"{' (y más)' if len([x for x in rel if REDACTA.search(Path(x).name)]) > 12 else ''}")
