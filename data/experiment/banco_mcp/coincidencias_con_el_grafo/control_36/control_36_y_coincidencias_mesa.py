"""control_36_y_coincidencias_mesa.py — Mesa, §393 (01/11/2026): cuáles de las preguntas de B6.3 y de B6.4 con alguna coincidencia del
grafo con un criterio están entre las 36 respuestas de la muestra de control del juez de cada una. Lee, de `C`, las claves de la
muestra (`control_36/clave/clave_control_36_B63.json` y `..._B64.json`), y de ellas solo el id de la pregunta, el brazo, la repetición,
la clase y el número de la ficha (si es un id corto). Las coincidencias, de `las_15_coincidencias.json`. Imprime solo ids y cuentas.
  python3 -I -B control_36_y_coincidencias_mesa.py <repo> <las_15_coincidencias.json>
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

R, J = Path(sys.argv[1]), Path(sys.argv[2])
C = "c190505c3ac63bf9d7cf51b94e3be04358cd7832"
fil = json.loads(J.read_text(encoding="utf-8"))["coincidencias"]
for fuente, ruta in (("B6.3", "data/experiment/banco_mcp/b63/control_36/clave/clave_control_36_B63.json"),
                     ("B6.4", "data/experiment/banco_mcp/b64/control_36/clave/clave_control_36_B64.json")):
    b = subprocess.run(["git", "--no-optional-locks", "-C", str(R), "show", f"{C}:{ruta}"], capture_output=True, check=True).stdout
    fichas = json.loads(b)["fichas"]
    con = sorted({r["pregunta"] for r in fil if r["fuente"] == fuente})
    dentro = [f for f in fichas if f["id_pregunta"] in set(con)]
    print(f"{fuente}: la clave {ruta.rsplit('/', 1)[1]} de C (sha256 {hashlib.sha256(b).hexdigest()[:12]}…): {len(fichas)} fichas, "
          f"{len({f['id_pregunta'] for f in fichas})} preguntas distintas; de las {len(con)} con alguna coincidencia, en la muestra: "
          f"{len({f['id_pregunta'] for f in dentro})} preguntas, en {len(dentro)} fichas")
    for f in sorted(dentro, key=lambda f: (f["id_pregunta"], f["brazo"], f["repeticion"])):
        fic = f["ficha"] if isinstance(f["ficha"], (int, str)) and re.fullmatch(r"[A-Za-z_-]*\d+", str(f["ficha"])) else "<no es un id>"
        clases = sorted({r["clase"] for r in fil if r["pregunta"] == f["id_pregunta"]})
        print(f"   ficha {fic}: {f['id_pregunta']} ({', '.join(clases)}) | brazo {f['brazo']} | repetición {f['repeticion']} "
              f"| {f['clase']}")
