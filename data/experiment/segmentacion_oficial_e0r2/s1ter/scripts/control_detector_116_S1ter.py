"""U-SEG-OFICIAL, S1-ter.4: control del detector corregido del 1.16 sobre la salida de S0-4b contra la evidencia de la
mesa (USD 0, sin API).

Uso: python -B control_detector_116_S1ter.py --propio <detector_116 sobre la salida de S0-4b> --mesa <evidencia de la
       mesa> --out <json>

El despacho de S1-ter pide que `s0_5/scripts/detector_116.py`, sobre la salida de S0-4b, dé los 317 candidatos de la
mesa antes de usarlo sobre la salida de S0-5b; si no, frena. La evidencia de la mesa
(`S0-5_evidencia_detector_116_corregido_salida.json`, fuera del repo) trae los ids del criterio original (`orig`, 121) y
los del corregido con sus campos (`corr`, 316); su sha256 se controla acá antes de leerla. Compara los dos conjuntos
de ids, la unión y, para los corregidos, los campos padre, origen, párrafos del último ítem, máximo de los anteriores,
ítems y páginas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SHA_MESA = "a81ebf65ba5e1825c74bd33d59ced690bb2fa62844d3984da69b51efc7229734"
CAMPOS = ("padre", "origen", "parrafos_ultimo", "parrafos_max_anteriores", "items", "paginas")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("propio", "mesa", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    raw = a.mesa.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SHA_MESA:
        raise SystemExit(f"la evidencia de la mesa no da su sha256: {sha}")
    m = json.loads(raw)
    p = json.loads(a.propio.read_text(encoding="utf-8"))
    pc = {c["id"]: c for c in p["candidatos"]}
    o = {i for i, c in pc.items() if c["criterio"] in ("original", "ambos")}
    co = {i for i, c in pc.items() if c["criterio"] in ("corregido", "ambos")}
    mo = set(m["orig"])
    mc = {c["id"]: c for c in m["corr"]}
    campos_distintos = sorted(i for i in set(mc) & co if any(mc[i][k] != pc[i][k] for k in CAMPOS))
    res = {"sha256_mesa": sha,
           "propio": {"original": len(o), "corregido": len(co), "union": len(o | co),
                      "ids_repetidos": len(p["candidatos"]) - len(pc)},
           "mesa": {"original": len(mo), "corregido": len(mc), "union": len(mo | set(mc))},
           "original_igual": o == mo, "corregido_igual": co == set(mc), "union_igual": (o | co) == (mo | set(mc)),
           "solo_propio": sorted((o | co) - (mo | set(mc))), "solo_mesa": sorted((mo | set(mc)) - (o | co)),
           "corregidos_con_campos_distintos": campos_distintos,
           "da_317": len(o | co) == 317 and (o | co) == (mo | set(mc))}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not res["da_317"]:
        raise SystemExit("el detector no da los 317 de la mesa: FRENO")


if __name__ == "__main__":
    main()
