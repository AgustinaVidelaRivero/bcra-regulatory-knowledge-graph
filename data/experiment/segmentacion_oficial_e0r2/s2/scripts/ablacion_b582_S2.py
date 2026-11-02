"""Ablación de las tres reglas de B5.8.2 sobre la E0 corregida (U-SEG-OFICIAL, S2, 4.d; USD 0, sin API).

Uso: python -B ablacion_b582_S2.py --codigo <raíz mínima> --e0 <salida de E0 de los 152> --trabajo <dir> --out <json>
       [--workers 6]

Repite la ablación del D3 legado (`reports/u_cap3_datos/u_cap3_datos.py:651-734`, `regla_anulada` y `ablacion`) con el
driver de e0-r2: en los TOs con `marcadores_b582` en la E0 corregida (`conteos.json`), corre `correr_e0.correr` por TO
con la regla anulada en e0_lib, igual que el legado:
- «indice»: `E0.RE_MARCA_INDICE_B582 = re.compile(r"(?!)")`;
- «seccion»: `E0._match_seccion_b582 = lambda texto: None`;
- «banner»: `E0.detectar_banners_texto = lambda paginas: set()`.
La regla «se usa» en el TO si con ella anulada cambia el modo de lectura o `chunks_<to>.json`. La corrida «base», sin
anular nada, tiene que dar el `chunks_<to>.json` de la E0 corregida byte a byte (control). Diferencia con el legado,
declarada: el legado corre su propia escalera (`escalera`, la de B5.8 sin las reglas de e0-r2); acá corre la de e0-r2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HIJO = r'''
import sys, re
from pathlib import Path
sys.dont_write_bytecode = True
raiz = Path(sys.argv[1]); to = sys.argv[2]; sal = Path(sys.argv[3]); cual = sys.argv[4]
for p in (raiz / "data/experiment/reextraccion_v2/e0_chunking", raiz / "data/experiment/reextraccion_v2"):
    sys.path.insert(0, str(p))
import e0_lib as E0
import correr_e0 as CE
if cual == "indice":
    E0.RE_MARCA_INDICE_B582 = re.compile(r"(?!)")
elif cual == "seccion":
    E0._match_seccion_b582 = lambda texto: None
elif cual == "banner":
    E0.detectar_banners_texto = lambda paginas: set()
PDFS = raiz / "data/experiment/escalado_prep/pdfs"
class M:
    tiene_oraculo = False
    mapa_territorio = None
    def __init__(self, ids): self.ids = list(ids)
    def archivo_de(self, t): return f"{t}.pdf"
    def pdf_de(self, t): return PDFS / f"{t}.pdf"
CE.correr(sal, manifiesto=M([to]), version_e0="e0-r2")
'''
VARIANTES = ("base", "indice", "seccion", "banner")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    conteos = json.loads((a.e0 / "conteos.json").read_text(encoding="utf-8"))
    tos = sorted(t for t, c in conteos.items() if c.get("marcadores_b582"))
    trabajos = [(t, v) for t in tos for v in VARIANTES]

    def uno(tv):
        t, v = tv
        d = a.trabajo / f"{t}__{v}"
        r = subprocess.run([sys.executable, "-B", "-c", HIJO, str(a.codigo.resolve()), t, str(d), v],
                           capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return t, v, r.returncode, r.stderr[-1500:]

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(uno, trabajos))
    errores = [(t, v, rc, e) for t, v, rc, e in res if rc]
    out = {"codigo_sha256": {n: sha(a.codigo / "data/experiment/reextraccion_v2/e0_chunking" / n)
                             for n in ("e0_lib.py", "correr_e0.py", "e0_tablas.py")},
           "tos": tos, "errores": [(t, v, rc) for t, v, rc, _ in errores], "por_to": {}}
    for t in tos:
        ref = (a.e0 / f"chunks_{t}.json").read_bytes()
        modo0 = conteos[t].get("modo_lectura")
        fila = {}
        for v in VARIANTES:
            d = a.trabajo / f"{t}__{v}"
            if not (d / f"chunks_{t}.json").exists():
                fila[v] = {"error": True}
                continue
            ch = (d / f"chunks_{t}.json").read_bytes()
            m = json.loads((d / "conteos.json").read_text(encoding="utf-8"))[t].get("modo_lectura")
            fila[v] = {"modo_lectura": m, "unidades": len(json.loads(ch)), "chunks_sha256": hashlib.sha256(ch).hexdigest(),
                       "igual_a_la_e0_corregida": ch == ref and m == modo0}
            if v != "base":
                fila[v]["cambia"] = not fila[v]["igual_a_la_e0_corregida"]
        out["por_to"][t] = fila
    out["control_base_reproduce"] = all(out["por_to"][t]["base"].get("igual_a_la_e0_corregida") for t in tos)
    out["usa"] = {v: [t for t in tos if out["por_to"][t][v].get("cambia")] for v in VARIANTES[1:]}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("tos", "errores", "control_base_reproduce", "usa")}, ensure_ascii=False))
    for t, v, rc, e in errores:
        print("ERROR", t, v, rc, e[-300:])


if __name__ == "__main__":
    main()
