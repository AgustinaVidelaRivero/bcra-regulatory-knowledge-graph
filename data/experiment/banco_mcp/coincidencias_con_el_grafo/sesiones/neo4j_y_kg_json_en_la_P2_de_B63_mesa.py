"""neo4j_y_kg_json_en_la_P2_de_B63_mesa.py — Mesa, §393 (01/11/2026): en la sesión de la P2 de B6.3 (45ce58c6), qué son las menciones
de `kg.json` y de `neo4j`. De los mensajes del usuario: el número del mensaje, su hora, las rutas que terminan en `kg.json` y si el
mismo mensaje dice docker, pgrep, bolt, MATCH o cypher (sin su texto). De las llamadas a herramientas que nombran neo4j: el comando de
Bash con todos sus literales de 20 caracteres o más tapados, y de cada Write el nombre del archivo y cuántas veces dice neo4j, bolt o
MATCH. Imprime solo eso. USD 0.
  python3 -I -B neo4j_y_kg_json_en_la_P2_de_B63_mesa.py <fuera_del_repo>
"""
import json
import re
import sys
from pathlib import Path

F = Path(sys.argv[1]).resolve()
pr = Path.home() / ".claude" / "projects" / ("-" + str(F / "b63_p2").strip("/").replace("/", "-").replace(" ", "-").replace("_", "-"))
t = pr / "45ce58c6-3c8f-4b1c-8fff-5540f396d0c7.jsonl"
RUTA = re.compile(r"[\w./~$-]*kg\.json(?:\.gz)?")
CLAVES = ("docker", "pgrep", "bolt", "MATCH", "cypher", "no ", "neo4j")
LIT = re.compile(r"([\"'])[^\"'\n]{20,}\1")
n = 0
for ln in t.read_text(encoding="utf-8", errors="replace").splitlines():
    try:
        m = json.loads(ln)
    except json.JSONDecodeError:
        continue
    msg = m.get("message") or {}
    if m.get("type") == "user" and not m.get("isMeta"):
        cont = msg.get("content")
        txt = [cont] if isinstance(cont, str) else [b.get("text", "") for b in cont or []
                                                    if isinstance(b, dict) and b.get("type") == "text"]
        for s in txt:
            if not s:
                continue
            n += 1
            if "kg.json" in s or "neo4j" in s.lower():
                print(f"mensaje del usuario {n} ({m.get('timestamp')}): rutas con kg.json {sorted(set(RUTA.findall(s)))}; neo4j "
                      f"{s.lower().count('neo4j')} veces; dice docker {'docker' in s.lower()}, pgrep {'pgrep' in s}, "
                      f"bolt {'bolt' in s.lower()}, "
                      f"MATCH {'MATCH' in s}, cypher {'cypher' in s.lower()}")
    if m.get("type") == "assistant":
        for b in msg.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                inp = b.get("input") or {}
                todo = json.dumps(inp, ensure_ascii=False)
                if "neo4j" not in todo.lower():
                    continue
                if b.get("name") == "Bash":
                    cmd = LIT.sub(lambda x: x.group(1) + "<literal>" + x.group(1), inp.get("command", ""))
                    print(f"Bash ({m.get('timestamp')}): {' '.join(cmd.split())[:300]}")
                else:
                    c = str(inp.get("content", "")) + str(inp.get("new_string", ""))
                    print(f"{b.get('name')} ({m.get('timestamp')}): {Path(str(inp.get('file_path', ''))).name}; "
                          f"neo4j {c.lower().count('neo4j')} veces, "
                          f"bolt {c.lower().count('bolt')}, MATCH {c.count('MATCH')}")
