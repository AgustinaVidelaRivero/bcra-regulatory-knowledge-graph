"""U-SEG-OFICIAL, S1.3: `manifest_salida.json` de la carpeta `s1/` (sha256 de cada archivo, commit del código y comando).

Uso: python -B manifest_salida_S1.py --s1 <carpeta s1> --codigo <e0_chunking de la copia> --tiempos <corrida_1.tiempo>

Recorre `s1/` (salvo el propio `manifest_salida.json`) y escribe el sha256 y el tamaño de cada archivo, el sha256 del
código de E0 con que corrió (que es el de `26c6502`), el comando de la corrida y los de los controles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

COMANDO = ("cd data/experiment/reextraccion_v2/e0_chunking && PYTHONDONTWRITEBYTECODE=1 <repo>/.venv/bin/python -B "
           "correr_e0.py --version-e0 e0-r2 --manifiesto <copia>/data/experiment/segmentacion_oficial_e0r2/s1/"
           "manifiesto/segmentacion_oficial_e0r2_152.json --salida <dir>")
CONTROLES = [
    "scripts/armar_manifiesto_S1.py <copia> <manifiesto>",
    "scripts/lanzar_doble_corrida.sh <scratchpad> <python>",
    "../s0_1/scripts/lineas_152.py <copia> <caché de renglones> --workers 4",
    "scripts/controles_S1.py --copia <copia> --c1 <corrida 1> --c2 <corrida 2> --manifiesto <manifiesto> "
    "--lineas <caché> --out controles_S1.json",
    "scripts/censo_vigencia_S1.py --copia <copia> --e0 <corrida 1> --manifiesto <manifiesto> --lineas <caché> "
    "--out censo_vigencia_S1.json",
    "scripts/herencia_S1.py --copia <copia> --e0 <corrida 1> --manifiesto <manifiesto> --out herencia_S1.json",
    "scripts/muestra_cortes_S1.py --e0 <corrida 1> --manifiesto <manifiesto> --controles controles_S1.json "
    "--out muestra_cortes_S1.json",
    "scripts/censo_renglones_S1.py --e0 <corrida 1> --manifiesto <manifiesto> --lineas <caché> "
    "--regla regla_censo_renglones_S1.md --pro <copia>/data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b "
    "--out censo_renglones_S1.json",
    "scripts/explicar_censo_S1.py --e0 <corrida 1> --censo censo_renglones_S1.json --out explicacion_censo_S1.json",
    "scripts/renderizar_muestra_S1.py --muestra muestra_cortes_S1.json --pdfs <copia>/data/experiment/escalado_prep/pdfs "
    "--out <paquete>/paginas_muestra_S1 (imágenes en el paquete del freno, no en el repo)",
    "scripts/manifest_salida_S1.py --s1 <s1> --codigo <copia>/data/experiment/reextraccion_v2/e0_chunking "
    "--tiempos <corrida_3.tiempo>",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1", type=Path, required=True)
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--tiempos", type=Path, required=True)
    a = ap.parse_args()
    arch = {}
    total = 0
    for p in sorted(a.s1.rglob("*")):
        if p.is_file() and p.name != "manifest_salida.json":
            rel = p.relative_to(a.s1).as_posix()
            arch[rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
            total += p.stat().st_size
    m = {"unidad": "U-SEG-OFICIAL, S1 (mandato firmado en e543cb2)",
         "commit_codigo": "26c6502",
         "codigo_sha256": {n: sha(a.codigo / n) for n in ("e0_lib.py", "correr_e0.py", "e0_tablas.py")},
         "version_e0": "e0-r2",
         "comando_corrida": COMANDO,
         "corrida": a.tiempos.read_text(encoding="utf-8").strip().splitlines(),
         "doble_corrida": ("corridas 1 y 2, con la versión 1 del manifiesto (difiere solo en "
                           "unidades_por_pagina_u_cob_a): 768 y 768 archivos, 0 distintos; la corrida 3, con el "
                           "manifiesto de manifiesto/, igual a las dos (sellos_S1.txt); e0/ es la corrida 1"),
         "comandos_controles": CONTROLES,
         "archivos_e0": sum(1 for r in arch if r.startswith("e0/")),
         "archivos": len(arch), "bytes": total,
         "sha256": arch}
    (a.s1 / "manifest_salida.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k != "sha256"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
