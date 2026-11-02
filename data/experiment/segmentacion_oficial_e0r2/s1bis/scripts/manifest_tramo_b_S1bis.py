"""U-SEG-OFICIAL, S1-bis-b: `manifest_salida_S1-bis-b.json` de los archivos que agrega el tramo b a `s1bis/` (USD 0).

Uso: python -B manifest_tramo_b_S1bis.py --s1bis <carpeta s1bis>

Controla que los archivos del tramo a sigan como los registró `manifest_salida.json` (y el FRENO S1-bis-a, fuera de ese
manifiesto, con el sha256 de su paquete), y escribe el sha256 y los bytes de cada archivo nuevo del tramo b, salvo el
FRENO S1-bis-b (que cita el sha256 de este manifiesto) y el propio manifiesto.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FRENO_A_SHA = "dcecf45e"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1bis", type=Path, required=True)
    a = ap.parse_args()
    r = a.s1bis
    ma = json.loads((r / "manifest_salida.json").read_text(encoding="utf-8"))["sha256"]
    tramo_a = {k: sha(r / k) == v["sha256"] for k, v in ma.items()}
    freno_a = sha(r / "FRENO_S1-bis-a.md")
    excluir = {"manifest_salida.json", "FRENO_S1-bis-a.md", "FRENO_S1-bis-b.md", "manifest_salida_S1-bis-b.json"}
    nuevos = {}
    for p in sorted(r.rglob("*")):
        rel = p.relative_to(r).as_posix()
        if p.is_file() and rel not in ma and rel not in excluir:
            nuevos[rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
    m = {"unidad": "U-SEG-OFICIAL, S1-bis-b (mandato firmado en e543cb2)",
         "tramo_a": {"manifest_salida.json": sha(r / "manifest_salida.json"), "archivos": len(ma),
                     "iguales": sum(tramo_a.values()), "distintos": sorted(k for k, v in tramo_a.items() if not v),
                     "freno_s1bis_a": freno_a, "freno_s1bis_a_igual_al_revisado": freno_a.startswith(FRENO_A_SHA)},
         "archivos_tramo_b": len(nuevos), "sha256": nuevos}
    (r / "manifest_salida_S1-bis-b.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k != "sha256"} | {"nuevos": sorted(nuevos)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
