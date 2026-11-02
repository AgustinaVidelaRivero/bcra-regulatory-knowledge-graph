"""e0-r2 de los diez TOs de la tanda 0 con el código de una copia, en paralelo por TO (USD 0, sin API).

Uso: python -B correr_tanda0_par.py --codigo <raíz de una copia> --salida <dir> [--workers 10]

Es `correr_tanda0.py` (manifiesto tanda0_10tos.json, sha256 de los PDF controlados contra el manifiesto) repartido en
procesos como `correr_152.py`: cada TO corre solo en `<salida>/por_to/<to>/` y después se juntan los archivos por TO y
los agregados en el orden de los ids, que es el orden en que `correr_e0.correr` recorre el manifiesto. La salida tiene
que dar byte a byte la de `correr_tanda0.py` (control: la corrida de base contra `salida_tanda0_r2b/`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HIJO = r'''
import sys
from pathlib import Path
sys.dont_write_bytecode = True
raiz = Path(sys.argv[1]); to = sys.argv[2]; sal = Path(sys.argv[3]); archivo = sys.argv[4]; pdf = Path(sys.argv[5])
for p in (raiz / "data/experiment/reextraccion_v2/e0_chunking", raiz / "data/experiment/reextraccion_v2"):
    sys.path.insert(0, str(p))
import correr_e0 as CE
class M:
    tiene_oraculo = False
    mapa_territorio = None
    ids = [to]
    def archivo_de(self, t): return archivo
    def pdf_de(self, t): return pdf
CE.correr(sal, manifiesto=M(), version_e0="e0-r2")
'''

AGREGADOS = ("divergencias_indice_cuerpo.json", "conteos.json", "cobertura.json", "correcciones.json",
             "sub_chunking.json", "encabezados_conservados.json", "ids_desambiguados.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=10)
    a = ap.parse_args()
    raiz = a.codigo.resolve()
    d = json.loads((raiz / "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos.json").read_text())
    tos = {t["id"]: t for t in d["tos"]}
    for t in d["tos"]:
        if hashlib.sha256((raiz / t["pdf"]).read_bytes()).hexdigest() != t["sha256_pdf"]:
            raise SystemExit(f"sha256 del PDF distinto: {t['id']}")
    orden = sorted(tos)
    por_to = a.salida / "por_to"
    por_to.mkdir(parents=True, exist_ok=True)

    def uno(to: str) -> tuple[str, int, str]:
        dd = por_to / to
        if dd.exists():
            shutil.rmtree(dd)
        r = subprocess.run([sys.executable, "-B", "-c", HIJO, str(raiz), to, str(dd), tos[to]["archivo"],
                            str(raiz / tos[to]["pdf"])], capture_output=True, text=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return to, r.returncode, r.stderr[-2000:]

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(uno, orden))
    errores = [(t, rc, e) for t, rc, e in res if rc != 0]
    for t, rc, e in errores:
        print("ERROR", t, rc, e)
    agregados: dict[str, dict] = {n: {} for n in AGREGADOS}
    for to in orden:
        for p in sorted((por_to / to).glob("*.json")):
            if p.name in AGREGADOS:
                agregados[p.name].update(json.loads(p.read_text(encoding="utf-8")))
            else:
                shutil.copyfile(p, a.salida / p.name)
    for n, v in agregados.items():
        if v or n in ("divergencias_indice_cuerpo.json", "conteos.json", "cobertura.json", "correcciones.json"):
            (a.salida / n).write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    print("listo", len(orden), "TOs,", len(errores), "con error", a.salida)


if __name__ == "__main__":
    main()
