"""U-SEG-OFICIAL, S1-ter: `manifest_salida.json` de la carpeta `s1ter/` (sha256 de cada archivo, commit del código y
comandos).

Uso: python -B manifest_salida_S1ter.py --s1ter <carpeta s1ter> --codigo <e0_chunking de la copia>
       --tiempos <corrida_1.tiempo> [--tiempos2 <corrida_2.tiempo>]

Copia de `s1bis/scripts/manifest_salida_S1bis.py` con el commit del código (`af7ffdd`, S0-5b), los comandos de S1-ter
y las dos corridas. Recorre `s1ter/` (salvo el propio `manifest_salida.json` y los `FRENO_*`) y escribe el sha256 y el
tamaño de cada archivo, el sha256 del código de E0 con que corrió, el comando de la corrida y los de los controles. El
FRENO de la etapa queda fuera, porque cita el sha256 de este manifiesto.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

D = "data/experiment/segmentacion_oficial_e0r2"
COMANDO = ("cd data/experiment/reextraccion_v2/e0_chunking && PYTHONDONTWRITEBYTECODE=1 <repo>/.venv/bin/python -B "
           f"correr_e0.py --version-e0 e0-r2 --manifiesto <copia>/{D}/s1ter/manifiesto/segmentacion_oficial_e0r2_152.json "
           "--salida <dir>")
CONTROLES = [
    "scripts/armar_manifiesto_S1ter.py <copia> <manifiesto>",
    "scripts/comparar_manifiestos_S1ter.py --s1bis ../s1bis/manifiesto/segmentacion_oficial_e0r2_152.json "
    "--s1ter <manifiesto> --copia <copia> --out comparacion_manifiestos_S1ter.json",
    "scripts/lanzar_doble_corrida_S1ter.sh <scratchpad> <python>",
    "../s0_1/scripts/lineas_152.py <copia> <caché de renglones> --workers 4",
    "scripts/controles_S1ter.py --copia <copia> --c1 <corrida 1> --c2 <corrida 2> --manifiesto <manifiesto> "
    "--lineas <caché> --ref ../s0_5/bis/censos/manifiesto_salida_e0_152_S0-5a-bis.json "
    "--ref2 ../s0_5/b/manifiestos/manifiesto_salida_e0_152_S0-5b.json --out controles_S1ter.json",
    "../s1/scripts/censo_vigencia_S1.py --copia <copia> --e0 <corrida 1> --manifiesto <manifiesto> --lineas <caché> "
    "--out censo_vigencia_S1ter.json",
    "scripts/herencia_S1ter.py --copia <copia> --e0 <corrida 1> --manifiesto <manifiesto> "
    "--s1bis ../s1bis/herencia_S1bis.json --out herencia_S1ter.json",
    "scripts/censo_renglones_S1ter.py --e0 <corrida 1> --manifiesto <manifiesto> --lineas <caché> "
    "--regla ../s1/regla_censo_renglones_S1.md --cambio ../s1bis/regla_censo_renglones_S1bis.md "
    "--pro <copia>/data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b --out censo_renglones_S1ter.json",
    "../s1/scripts/explicar_censo_S1.py --e0 <corrida 1> --censo censo_renglones_S1ter.json "
    "--out explicacion_censo_S1ter.json",
    "scripts/comparar_censos_S1ter.py --censo censo_renglones_S1ter.json --explicacion explicacion_censo_S1ter.json "
    "--s1bis-censo ../s1bis/censo_renglones_S1bis.json --s1bis-explicacion ../s1bis/explicacion_censo_S1bis.json "
    "--e0 <corrida 1> --out comparacion_censos_S1ter.json",
    "../s0_5/scripts/detector_116.py --e0 ../s1bis/e0 --out censos/detector_116_sobre_S0-4b.json",
    "../s0_5/scripts/detector_116.py --e0 <corrida 1> --out censos/detector_116_sobre_S0-5b.json",
    "scripts/control_detector_116_S1ter.py --propio censos/detector_116_sobre_S0-4b.json "
    "--mesa <S0-5_evidencia_detector_116_corregido_salida.json de la mesa> --out censos/control_detector_116_S0-4b.json",
    "scripts/poblaciones_S1ter.py --e0 <corrida 1> --e0-s04b ../s1bis/e0 --manifiesto <manifiesto> "
    "--detector censos/detector_116_sobre_S0-5b.json --s1bis-censo ../s1bis/comparacion_censos_S1bis.json "
    "--s1bis-planilla-116 ../s1bis/lectura_cortes/planilla_1_16_S1-bis-b_mesa.tsv "
    "--s1bis-muestra ../s1bis/muestra_cortes_S1bis.json "
    "--lista-r5a <lista_R5a_por_lista_v2_decision4_mesa.json de la mesa> "
    "--limites-s05 ../s0_5/bis/censos/limites_S0-5a-bis.json --out poblaciones_S1ter.json",
    "scripts/manifest_salida_S1ter.py --s1ter <s1ter> --codigo <copia>/data/experiment/reextraccion_v2/e0_chunking "
    "--tiempos <corrida_1.tiempo> --tiempos2 <corrida_2.tiempo>",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--s1ter", type=Path, required=True)
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--tiempos", type=Path, required=True)
    ap.add_argument("--tiempos2", type=Path, default=None)
    a = ap.parse_args()
    arch = {}
    total = 0
    for p in sorted(a.s1ter.rglob("*")):
        if p.is_file() and p.name != "manifest_salida.json" and not p.name.startswith("FRENO_"):
            rel = p.relative_to(a.s1ter).as_posix()
            arch[rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
            total += p.stat().st_size
    m = {"unidad": "U-SEG-OFICIAL, S1-ter (mandato firmado en e543cb2)",
         "commit_codigo": "af7ffdd",
         "codigo_sha256": {n: sha(a.codigo / n) for n in ("e0_lib.py", "correr_e0.py", "e0_tablas.py")},
         "version_e0": "e0-r2",
         "comando_corrida": COMANDO,
         "corrida_1": a.tiempos.read_text(encoding="utf-8").strip().splitlines(),
         "corrida_2": a.tiempos2.read_text(encoding="utf-8").strip().splitlines() if a.tiempos2 else None,
         "doble_corrida": "corridas 1 y 2 a la vez, en directorios distintos, con el manifiesto de manifiesto/; e0/ es la "
                          "corrida 1 (controles_S1ter.json, doble_corrida)",
         "comandos_controles": CONTROLES,
         "archivos_e0": sum(1 for r in arch if r.startswith("e0/")),
         "archivos": len(arch), "bytes": total,
         "sha256": arch}
    (a.s1ter / "manifest_salida.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k != "sha256"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
