"""U-SEG-OFICIAL, S1, punto 7: renderiza las páginas de la muestra de la lectura de cortes (USD 0).

Uso: python -B renderizar_muestra_S1.py --muestra <muestra_cortes_S1.json> --pdfs <escalado_prep/pdfs> --out <dir>
       [--workers 6]

Una imagen por página, `pdftoppm -r 110 -png -f p -l p -singlefile`, con el nombre `<to>_p<página>.png`: las páginas
de cada unidad de la muestra (primer y segundo grupo, ri_spi) y todas las páginas de los no segmentables del tercer
grupo. Escribe `renders.json` con el sha256 de cada imagen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=Path, required=True)
    ap.add_argument("--pdfs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    m = json.loads(a.muestra.read_text(encoding="utf-8"))
    trabajos = [(to, p) for to, ps in m["paginas_a_renderizar"].items() for p in ps]

    def uno(tp):
        to, p = tp
        dest = a.out / f"{to}_p{p}"
        r = subprocess.run(["pdftoppm", "-r", "110", "-png", "-f", str(p), "-l", str(p), "-singlefile",
                            str(a.pdfs / f"{to}.pdf"), str(dest)], capture_output=True, text=True)
        return to, p, r.returncode, r.stderr[-300:]

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(uno, trabajos))
    errores = [r for r in res if r[2] != 0 or not (a.out / f"{r[0]}_p{r[1]}.png").exists()]
    shas = {f"{to}_p{p}.png": hashlib.sha256((a.out / f"{to}_p{p}.png").read_bytes()).hexdigest()
            for to, p, rc, _ in res if rc == 0 and (a.out / f"{to}_p{p}.png").exists()}
    (a.out / "renders.json").write_text(json.dumps({"comando": "pdftoppm -r 110 -png -f p -l p -singlefile",
                                                    "imagenes": len(shas), "errores": errores, "sha256": shas},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("imágenes", len(shas), "de", len(trabajos), "errores", len(errores))


if __name__ == "__main__":
    main()
