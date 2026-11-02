"""el_grafo_en_los_despachos_mesa.py — Mesa, §393 (01/11/2026): qué dicen del grafo los despachos de la generación. De los mensajes
del usuario de la sesión de la P2 de B6.3 (45ce58c6) y de los cinco despachos de la generación de B6.4 del paquete de la mesa, los
renglones que nombran el grafo («grafo», `kg.json`, `ens_`, `neo4j`, `mcp`), recortados a 200 caracteres. Son texto de la mesa (sus
instrucciones), no de preguntas ni de criterios; todo lo que va entre comillas angulares, y lo que queda abierto hasta el final del
renglón, va tapado. USD 0.
  python3 -I -B el_grafo_en_los_despachos_mesa.py <fuera_del_repo> <paquete de la mesa>
"""
import json
import re
import sys
from pathlib import Path

F, H = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
RE = re.compile(r"\bgrafo|kg\.json|ens_1|neo4j|\bmcp", re.I)
LIT = re.compile(r"(«[^»]*(»|$)|\"[^\"\n]{25,}\")")
pr = Path.home() / ".claude" / "projects" / ("-" + str(F / "b63_p2").strip("/").replace("/", "-").replace(" ", "-").replace("_", "-"))
n = 0
print("== la P2 de B6.3, los mensajes del usuario de 45ce58c6")
for ln in (pr / "45ce58c6-3c8f-4b1c-8fff-5540f396d0c7.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
    m = json.loads(ln) if ln.startswith("{") else {}
    if m.get("type") != "user" or m.get("isMeta"):
        continue
    c = (m.get("message") or {}).get("content")
    for s in [c] if isinstance(c, str) else [b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text"]:
        if not s:
            continue
        n += 1
        for r in s.splitlines():
            if RE.search(r):
                print(f"   mensaje {n}: {LIT.sub('«…»', ' '.join(r.split()))[:200]}")
for p in ("decisiones_352_mesa/b64/DESPACHO_GENERACION_B64_BLOQUE_1_PARA_PEGAR_v3_mesa.md",
          "decisiones_355_mesa/b64/DESPACHO_GENERACION_B64_BLOQUE_2_PARA_PEGAR_mesa.md",
          "decisiones_363_mesa/generacion/DESPACHO_GENERACION_B64_REUBICADOS_O6_L15_L16_PARA_PEGAR_mesa.md",
          "decisiones_367_mesa/reemplazos/DESPACHO_GENERACION_B64_REEMPLAZOS_R1_PARA_PEGAR_mesa.md",
          "decisiones_371_mesa/reemplazos_R2/DESPACHO_GENERACION_B64_REEMPLAZOS_R2_PARA_PEGAR_mesa.md"):
    print(f"== {p}")
    for i, r in enumerate((H / p).read_text(encoding="utf-8").splitlines(), 1):
        if RE.search(r):
            print(f"   {i}: {LIT.sub('«…»', ' '.join(r.split()))[:200]}")
