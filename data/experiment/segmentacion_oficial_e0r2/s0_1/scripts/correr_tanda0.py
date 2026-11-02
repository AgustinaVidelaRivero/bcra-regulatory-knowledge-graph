"""e0-r2 de los diez TOs de la tanda 0 con el código de una copia (USD 0, sin API).

Uso: python -B correr_tanda0.py --codigo <raíz de una copia> --salida <dir>

Es `correr_e0.py --version-e0 e0-r2 --manifiesto data/experiment/reextraccion_v2/manifiestos/tanda0_10tos.json`
sin `manifiesto_corpus.cargar`: de un manifiesto, `correr_e0.correr` usa solo los ids, el archivo y la ruta del
PDF de cada TO y el oráculo (null en este manifiesto); el cargador además controla los sha256 de los PDF y los
candados del perfil de E1, que no tocan la salida de E0 y piden módulos de E1 que la copia no lleva. Los sha256 de
los PDF se controlan acá contra el manifiesto.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


class Man:
    def __init__(self, raiz: Path, d: dict):
        assert d["oraculo"]["mapa_territorio"] is None if "oraculo" in d else True
        self.raiz = raiz
        self._t = {t["id"]: t for t in d["tos"]}
        self.ids = [t["id"] for t in d["tos"]]
        self.tiene_oraculo = False
        self.mapa_territorio = None

    def archivo_de(self, t):
        return self._t[t]["archivo"]

    def pdf_de(self, t):
        return self.raiz / self._t[t]["pdf"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    raiz = a.codigo.resolve()
    for p in (raiz / "data/experiment/reextraccion_v2/e0_chunking", raiz / "data/experiment/reextraccion_v2"):
        sys.path.insert(0, str(p))
    import correr_e0 as CE  # noqa: PLC0415
    d = json.loads((raiz / "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos.json").read_text())
    m = Man(raiz, d)
    for t in d["tos"]:
        sha = hashlib.sha256(m.pdf_de(t["id"]).read_bytes()).hexdigest()
        if sha != t["sha256_pdf"]:
            raise SystemExit(f"sha256 del PDF distinto: {t['id']}")
    CE.correr(a.salida, manifiesto=m, version_e0="e0-r2")
    print("listo", len(m.ids), a.salida)


if __name__ == "__main__":
    main()
