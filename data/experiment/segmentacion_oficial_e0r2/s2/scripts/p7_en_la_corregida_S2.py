"""Fila 1 de 4.g de S2 (U-SEG-OFICIAL): los párrafos sin numerar que empiezan con un número de punto, en la E0 corregida
(solo lectura).

Uso: python -B p7_en_la_corregida_S2.py --e0 <salida de E0 de los 152> --raiz <copia del repo> --trabajo <dir> --out <json>

- Corre, sin editarlos, `s0_1/scripts/censo_p7.py` (intersticiales cuya primera línea es un número de punto) y
  `s0_1/scripts/censo_p7_resto.py` (rótulos rechazados por «padre no abierto» cuyo padre existe) sobre --e0, con salida en
  --trabajo (las dos salidas traen una línea de texto por fila: no se copian).
- Cada uno de los 36 de la verificación del 03/10/2026 (`s0_1/censos/censo_p7_base.json`, `filas`) se busca en la E0
  corregida: «sigue» si su id sigue siendo un intersticial del censo; «subpunto» si `estructura_<to>.json` tiene un nodo
  de tipo punto con el número de la primera línea (terminal o contenedor); si no, «otro destino». El número se
  toma de la primera línea con la expresión del censo; la línea no se guarda.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

RE = re.compile(r"^(\d+(?:\.\d+)+)\.?(\s|$)")
S = "data/experiment/segmentacion_oficial_e0r2"


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("--e0", "--raiz", "--trabajo", "--out"):
        ap.add_argument(k, type=Path, required=True)
    a = ap.parse_args()
    a.trabajo.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    for script, sal in (("censo_p7.py", "censo_p7_corregida.json"), ("censo_p7_resto.py", "censo_p7_resto_corregida.json")):
        subprocess.run([sys.executable, "-B", str(a.raiz / S / "s0_1/scripts" / script), str(a.e0), str(a.trabajo / sal)],
                       check=True, capture_output=True, env=env)
    p7 = json.loads((a.trabajo / "censo_p7_corregida.json").read_text(encoding="utf-8"))
    resto = json.loads((a.trabajo / "censo_p7_resto_corregida.json").read_text(encoding="utf-8"))
    base = json.loads((a.raiz / S / "s0_1/censos/censo_p7_base.json").read_text(encoding="utf-8"))
    siguen = {(f["to"], f["id"]) for f in p7["filas"]}
    filas = []
    for f in base["filas"]:
        num = RE.match(f["primera_linea"].strip()).group(1)
        est = json.loads((a.e0 / f"estructura_{f['to']}.json").read_text(encoding="utf-8"))
        nodos = {}

        def rec(n: dict) -> None:
            if n.get("tipo") == "punto":
                nodos[n["numero"]] = "contenedor" if n.get("hijos") else "terminal"
            for h in n.get("hijos", []):
                rec(h)
        for s in est["secciones"]:
            rec(s)
        if (f["to"], f["id"]) in siguen:
            destino = "sigue como intersticial"
        elif num in nodos:
            destino = f"subpunto ({nodos[num]})"
        else:
            destino = "otro destino"
        filas.append({"to": f["to"], "id_base": f["id"], "numero": num, "destino": destino})
    out = {"censo_p7_corregida": {k: v for k, v in p7.items() if k != "filas"},
           "censo_p7_resto_corregida": {k: v for k, v in resto.items() if k != "filas"},
           "los_36": {"total": len(filas), "por_destino": dict(Counter(x["destino"] for x in filas)),
                      "por_to_y_destino": dict(sorted(Counter(f"{x['to']} | {x['destino']}" for x in filas).items())),
                      "filas": filas}}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "los_36"}, ensure_ascii=False))
    print({k: v for k, v in out["los_36"].items() if k != "filas"})


if __name__ == "__main__":
    main()
