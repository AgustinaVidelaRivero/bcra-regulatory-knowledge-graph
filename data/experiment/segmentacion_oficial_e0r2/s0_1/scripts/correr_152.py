"""e0-r2 de los 152 TOs de la partición con el código de una copia, en paralelo por TO (USD 0, sin API).

Uso: python -B correr_152.py --codigo <raíz de una copia> --salida <dir> [--workers 8] [--tos a,b,c]
     [--cola-en-toda-pagina]

Es la corrida de `r2_codigo2/c2_e0_152.py` (PDFs de escalado_prep, TOs de conteos_b584.json) repartida en
procesos: cada TO corre solo en `<salida>/por_to/<to>/` y después se juntan los archivos por TO y los agregados
(cada agregado es un dict por TO; se juntan en orden de TO, como en la corrida secuencial). La salida tiene que
estar fuera del repo.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HIJO = r'''
import sys, json
from pathlib import Path
sys.dont_write_bytecode = True
raiz = Path(sys.argv[1]); to = sys.argv[2]; sal = Path(sys.argv[3]); cola = sys.argv[4] == "1"
for p in (raiz / "data/experiment/reextraccion_v2/e0_chunking", raiz / "data/experiment/reextraccion_v2"):
    sys.path.insert(0, str(p))
import correr_e0 as CE
PDFS = raiz / "data/experiment/escalado_prep/pdfs"
class M:
    tiene_oraculo = False
    mapa_territorio = None
    def __init__(self, ids): self.ids = list(ids)
    def archivo_de(self, t): return f"{t}.pdf"
    def pdf_de(self, t): return PDFS / f"{t}.pdf"
if cola:
    class _T(frozenset):
        def __contains__(self, x): return True
    class _C(dict):
        def get(self, k, default=None): return _T()
    CE.COLA_TITULO_ESTRICTA_E0_R2 = _C()
CE.correr(sal, manifiesto=M([to]), version_e0="e0-r2")
'''

AGREGADOS = ("divergencias_indice_cuerpo.json", "conteos.json", "cobertura.json", "correcciones.json",
             "sub_chunking.json", "encabezados_conservados.json", "ids_desambiguados.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--tos", default=None)
    ap.add_argument("--cola-en-toda-pagina", action="store_true")
    a = ap.parse_args()
    raiz = a.codigo.resolve()
    c = json.loads((raiz / "data/experiment/segmentacion_84/b584_particion/conteos_b584.json").read_text())
    tos = sorted(t for t, v in c.items() if isinstance(v, dict))
    if a.tos:
        pedidos = a.tos.split(",")
        tos = [t for t in tos if t in pedidos]
    por_to = a.salida / "por_to"
    por_to.mkdir(parents=True, exist_ok=True)

    def uno(to: str) -> tuple[str, int, str]:
        d = por_to / to
        if d.exists():
            shutil.rmtree(d)
        r = subprocess.run([sys.executable, "-B", "-c", HIJO, str(raiz), to, str(d),
                            "1" if a.cola_en_toda_pagina else "0"], capture_output=True, text=True,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return to, r.returncode, r.stderr[-2000:]

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(uno, tos))
    errores = [(t, rc, e) for t, rc, e in res if rc != 0]
    for t, rc, e in errores:
        print("ERROR", t, rc, e)
    agregados: dict[str, dict] = {n: {} for n in AGREGADOS}
    for to in tos:
        d = por_to / to
        for p in sorted(d.glob("*.json")):
            if p.name in AGREGADOS:
                agregados[p.name].update(json.loads(p.read_text(encoding="utf-8")))
            elif p.name != "version_e0.json":
                shutil.copyfile(p, a.salida / p.name)
            else:
                shutil.copyfile(p, a.salida / p.name)
    for n, v in agregados.items():
        if v:
            (a.salida / n).write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    print("listo", len(tos), "TOs,", len(errores), "con error", a.salida)


if __name__ == "__main__":
    main()
