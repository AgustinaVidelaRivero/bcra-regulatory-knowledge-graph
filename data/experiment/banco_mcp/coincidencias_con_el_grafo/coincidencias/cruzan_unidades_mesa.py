"""cruzan_unidades_mesa.py — Mesa, §393 (01/11/2026): de las 15 coincidencias, cuáles están enteras en el texto de un archivo de la E0
leído en orden (sus unidades seguidas, una detrás de otra), aunque no lo estén en una sola unidad: si cruzan el límite entre unidades.
Por palabras (`\\w+` en minúsculas). Imprime solo ids y cuentas. USD 0.
  python3 -I -B cruzan_unidades_mesa.py <repo> <fuera_del_repo> <las_15_coincidencias.json>
"""
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

R, F, J = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
C = "c190505c3ac63bf9d7cf51b94e3be04358cd7832"
E0 = "data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b/"
B63 = F / ("hoja_de_ruta_tanda1_mesa/decisiones_317_mesa/entrada/"
           "salida/preguntas_96_B63.json")
W = re.compile(r"\w+")
toks = lambda s: W.findall(unicodedata.normalize("NFC", s).casefold())  # noqa: E731
git = lambda *a: subprocess.run(["git", "--no-optional-locks", "-C", str(R), *a], capture_output=True, check=True).stdout  # noqa: E731
crit = {}
for fu, b in (("B6.3", B63.read_bytes()), ("B6.4", git("show", f"{C}:data/experiment/banco_mcp/b64/preguntas/aprobadas_B64.json"))):
    for q in json.loads(b)["preguntas"]:
        for i, c in enumerate(q.get("criterios", []), 1):
            crit[(fu, q["id"], i)] = c["criterio"] if isinstance(c, dict) else c
for q in json.loads(git("show", f"{C}:data/experiment/exploracion/u6_fidelidad/criterios_u6.json"))["preguntas"]:
    for i, c in enumerate((q.get("gold") or {}).get("criterios", []), 1):
        crit[("EV2 (U6)", q["id"], i)] = c["criterio"] if isinstance(c, dict) else c
filas = json.loads(J.read_text(encoding="utf-8"))["coincidencias"]
T = {(r["fuente"], r["pregunta"], r["criterio"]): toks(crit[(r["fuente"], r["pregunta"], r["criterio"])]) for r in filas}


def textos_en_orden(x, out):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("texto", "texto_propio", "text", "contenido", "titulo") and isinstance(v, str):
                out.append(v)
            else:
                textos_en_orden(v, out)
    elif isinstance(x, list):
        for v in x:
            textos_en_orden(v, out)
    return out


cruza = {k: 0 for k in T}
for ln in git("ls-tree", "-r", "--name-only", C, "--", E0).decode().splitlines():
    if not ln.endswith(".json"):
        continue
    t = toks(" ".join(textos_en_orden(json.loads(git("show", f"{C}:{ln}")), [])))
    for k, c in T.items():
        n = len(c)
        if any(t[i:i + n] == c for i in range(len(t) - n + 1) if t[i] == c[0]):
            cruza[k] += 1
for r in filas:
    k = (r["fuente"], r["pregunta"], r["criterio"])
    print(f"{r['pregunta']} criterio {r['criterio']} ({r['sha256']}): entero en una unidad {r['entero_en_unidades_de_la_E0']}; entero en "
          f"el texto de un archivo de la E0 leído en orden: {cruza[k]}; en un tramo: {any('tramo' in x for x in r['campos'])}")
