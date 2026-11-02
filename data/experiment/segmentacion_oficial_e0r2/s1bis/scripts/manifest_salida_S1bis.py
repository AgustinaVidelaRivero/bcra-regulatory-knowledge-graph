"""U-SEG-OFICIAL, S1-bis: `manifest_salida.json` de la carpeta `s1bis/` (sha256 de cada archivo, commit del código y
comandos).

Uso: python -B manifest_salida_S1bis.py --s1bis <carpeta s1bis> --codigo <e0_chunking de la copia>
       --tiempos <corrida_1.tiempo> [--tiempos2 <corrida_2.tiempo>]

Copia de `s1/scripts/manifest_salida_S1.py` con el commit del código (`18d9e05`), los comandos de S1-bis y las dos
corridas. Recorre `s1bis/` (salvo el propio `manifest_salida.json`) y escribe el sha256 y el tamaño de cada archivo, el
sha256 del código de E0 con que corrió, el comando de la corrida y los de los controles. El FRENO de la etapa
(`FRENO_S1-bis-a.md`) queda fuera, porque cita el sha256 de este manifiesto (en S1 estaba fuera de `s1/`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

D = "data/experiment/segmentacion_oficial_e0r2"
COMANDO = ("cd data/experiment/reextraccion_v2/e0_chunking && PYTHONDONTWRITEBYTECODE=1 <repo>/.venv/bin/python -B "
           f"correr_e0.py --version-e0 e0-r2 --manifiesto <copia>/{D}/s1bis/manifiesto/segmentacion_oficial_e0r2_152.json "
           "--salida <dir>")
CONTROLES = [
    "scripts/armar_manifiesto_S1bis.py <copia> <manifiesto>",
    "scripts/comparar_manifiestos_S1bis.py --s1 ../s1/manifiesto/segmentacion_oficial_e0r2_152.json --s1bis <manifiesto> "
    "--copia <copia> --out comparacion_manifiestos_S1bis.json",
    "scripts/lanzar_doble_corrida_S1bis.sh <scratchpad> <python>",
    "../s0_1/scripts/lineas_152.py <copia> <caché de renglones> --workers 4",
    "scripts/controles_S1bis.py --copia <copia> --c1 <corrida 1> --c2 <corrida 2> --manifiesto <manifiesto> "
    "--lineas <caché> --s04b <manifiesto_salida_e0_152_S0-4b.json del paquete de S0-4b> --out controles_S1bis.json",
    "../s1/scripts/censo_vigencia_S1.py --copia <copia> --e0 <corrida 1> --manifiesto <manifiesto> --lineas <caché> "
    "--out censo_vigencia_S1bis.json",
    "scripts/herencia_S1bis.py --copia <copia> --e0 <corrida 1> --manifiesto <manifiesto> --s1 ../s1/herencia_S1.json "
    "--out herencia_S1bis.json",
    "scripts/censo_renglones_S1bis.py --e0 <corrida 1> --manifiesto <manifiesto> --lineas <caché> "
    "--regla ../s1/regla_censo_renglones_S1.md --cambio regla_censo_renglones_S1bis.md "
    "--pro <copia>/data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b --out censo_renglones_S1bis.json",
    "../s1/scripts/explicar_censo_S1.py --e0 <corrida 1> --censo censo_renglones_S1bis.json "
    "--out explicacion_censo_S1bis.json",
    "scripts/comparar_censos_S1bis.py --censo censo_renglones_S1bis.json --explicacion explicacion_censo_S1bis.json "
    "--s1-censo ../s1/censo_renglones_S1.json --s1-explicacion ../s1/explicacion_censo_S1.json --e0 <corrida 1> "
    "--out comparacion_censos_S1bis.json",
    "scripts/poblacion_muestra_S1bis.py --e0 <corrida 1> --manifiesto <manifiesto> --controles controles_S1bis.json "
    "--s1-e0 <salida de E0 de S1> --s1-muestra ../s1/muestra_cortes_S1.json "
    "--s1-marcas ../s1/lectura_cortes/marcas_lectura_cortes_S1_mesa_136_filas.tsv --out poblacion_muestra_S1bis.json",
    "scripts/manifest_salida_S1bis.py --s1bis <s1bis> --codigo <copia>/data/experiment/reextraccion_v2/e0_chunking "
    "--tiempos <corrida_1.tiempo> --tiempos2 <corrida_2.tiempo>",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1bis", type=Path, required=True)
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--tiempos", type=Path, required=True)
    ap.add_argument("--tiempos2", type=Path, default=None)
    a = ap.parse_args()
    arch = {}
    total = 0
    for p in sorted(a.s1bis.rglob("*")):
        if p.is_file() and p.name != "manifest_salida.json" and not p.name.startswith("FRENO_"):
            rel = p.relative_to(a.s1bis).as_posix()
            arch[rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
            total += p.stat().st_size
    m = {"unidad": "U-SEG-OFICIAL, S1-bis (mandato firmado en e543cb2)",
         "commit_codigo": "18d9e05",
         "codigo_sha256": {n: sha(a.codigo / n) for n in ("e0_lib.py", "correr_e0.py", "e0_tablas.py")},
         "version_e0": "e0-r2",
         "comando_corrida": COMANDO,
         "corrida_1": a.tiempos.read_text(encoding="utf-8").strip().splitlines(),
         "corrida_2": a.tiempos2.read_text(encoding="utf-8").strip().splitlines() if a.tiempos2 else None,
         "doble_corrida": "corridas 1 y 2 a la vez, en directorios distintos, con el manifiesto de manifiesto/; e0/ es la "
                          "corrida 1 (controles_S1bis.json, doble_corrida)",
         "comandos_controles": CONTROLES,
         "archivos_e0": sum(1 for r in arch if r.startswith("e0/")),
         "archivos": len(arch), "bytes": total,
         "sha256": arch}
    (a.s1bis / "manifest_salida.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k != "sha256"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
