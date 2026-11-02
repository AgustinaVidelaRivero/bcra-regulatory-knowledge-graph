"""El tamaño de la herencia (U-SEG-OFICIAL, S0-6a-bis, decisión 4; USD 0, solo lectura): la suma, sobre todas las unidades,
de los caracteres de los textos de su `herencia`, en los 152 y por documento, en una o más salidas de E0.

Uso: python -B tamano_herencia_S0-6a-bis.py --salida nombre=<dir E0> [--salida nombre=<dir E0> …] --out <json>

Solo cuentas: sin ids ni texto. El efecto en el costo de E1 y en el tope de la tanda 1 no se calcula acá.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def medir(d: Path) -> dict:
    por_to = {}
    for p in sorted(d.glob("chunks_*.json")):
        ch = json.loads(p.read_text(encoding="utf-8"))
        por_to[p.name[len("chunks_"):-5]] = {"unidades": len(ch),
                                            "caracteres_herencia": sum(len(t["texto"]) for c in ch for t in c["herencia"])}
    return {"tos": len(por_to), "unidades": sum(v["unidades"] for v in por_to.values()),
            "caracteres_herencia": sum(v["caracteres_herencia"] for v in por_to.values()), "por_to": por_to}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = {n: medir(Path(d)) for n, d in (x.split("=", 1) for x in a.salida)}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({n: {k: v[k] for k in ("tos", "unidades", "caracteres_herencia")} for n, v in res.items()},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
