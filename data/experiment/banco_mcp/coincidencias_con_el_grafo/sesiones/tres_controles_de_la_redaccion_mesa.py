"""tres_controles_de_la_redaccion_mesa.py — Mesa, §393 (01/11/2026): tres controles de lo que el documento de la ronda dice de las
sesiones de la generación. USD 0.
  1. En la sesión de la P2 de B6.3 (45ce58c6), cada renglón de un mensaje del usuario que dice `kg.json`: su número de mensaje y de
     renglón, y si el mismo renglón trae una negación («no leés», «do not read» y parecidas). Sin su texto.
  2. En la misma sesión, cada renglón de los argumentos de una llamada a una herramienta que dice neo4j: la herramienta, la hora y si el
     renglón dice «sin API y sin Neo4j». Sin su texto.
  3. De los despachos de R1 y de R2 de B6.4 (paquete de la mesa), los renglones que limitan lo que se lee del repo, recortados a 200
     caracteres y con lo que va entre comillas angulares tapado: son texto de la mesa, no de preguntas ni de criterios.
  python3 -I -B tres_controles_de_la_redaccion_mesa.py <fuera_del_repo> <paquete de la mesa>
"""
import json
import re
import sys
from pathlib import Path

F, H = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
pr = Path.home() / ".claude" / "projects" / ("-" + str(F / "b63_p2").strip("/").replace("/", "-").replace(" ", "-").replace("_", "-"))
NEG = re.compile(r"no le[eé]s|do not read|no lee|sin leer|not read|don't read", re.I)
LIT = re.compile(r"(«[^»]*(»|$)|\"[^\"\n]{25,}\")")
LEE = re.compile(r"no le[eé]s|leés solo|solo le[eé]s|fuera de lo del punto|del repo", re.I)


def textos(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from textos(v)
    elif isinstance(x, list):
        for v in x:
            yield from textos(v)


print("1. La P2 de B6.3: los renglones de los mensajes del usuario que dicen kg.json")
n = 0
lineas = (pr / "45ce58c6-3c8f-4b1c-8fff-5540f396d0c7.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()
for ln in lineas:
    m = json.loads(ln) if ln.startswith("{") else {}
    if m.get("type") != "user" or m.get("isMeta"):
        continue
    c = (m.get("message") or {}).get("content")
    for s in [c] if isinstance(c, str) else [b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text"]:
        if not s:
            continue
        n += 1
        for i, r in enumerate(s.splitlines(), 1):
            if "kg.json" in r:
                print(f"   mensaje {n}, renglón {i}: kg.json {r.count('kg.json')} vez/veces; con una negación en el mismo renglón: "
                      f"{bool(NEG.search(r))}")
print("2. La P2 de B6.3: los renglones de las llamadas a herramientas que dicen neo4j")
for ln in lineas:
    m = json.loads(ln) if ln.startswith("{") else {}
    if m.get("type") != "assistant":
        continue
    for b in (m.get("message") or {}).get("content") or []:
        if isinstance(b, dict) and b.get("type") == "tool_use":
            for s in textos(b.get("input") or {}):
                for r in s.splitlines():
                    if "neo4j" in r.lower():
                        print(f"   {b['name']} ({m.get('timestamp')}): el renglón dice «sin API y sin Neo4j»: "
                              f"{'sin API y sin Neo4j' in r}")
print("3. Los despachos de R1 y de R2 de B6.4: lo que se lee del repo")
for p in ("decisiones_367_mesa/reemplazos/DESPACHO_GENERACION_B64_REEMPLAZOS_R1_PARA_PEGAR_mesa.md",
          "decisiones_371_mesa/reemplazos_R2/DESPACHO_GENERACION_B64_REEMPLAZOS_R2_PARA_PEGAR_mesa.md"):
    print(f"== {p}")
    for i, r in enumerate((H / p).read_text(encoding="utf-8").splitlines(), 1):
        if LEE.search(r):
            print(f"   {i}: {LIT.sub('«…»', ' '.join(r.split()))[:200]}")
