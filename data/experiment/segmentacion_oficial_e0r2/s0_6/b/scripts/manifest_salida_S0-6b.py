"""El manifiesto de la salida de E0 de los 152 de S0-6b (U-SEG-OFICIAL; solo lectura), con el formato de
`s1ter/manifest_salida.json`: un `sha256` con una entrada `e0/<archivo>` por archivo (lo pide el diseño sellado de
S1-quater, §2).

Uso: python -B manifest_salida_S0-6b.py --e0 <salida de E0> --codigo <dir del código final> --tiempos <txt>
       [--tiempos2 <txt>] --out <json>

Recorre los archivos de primer nivel de la salida (los de `por_to/` no: son la corrida por TO antes de juntarla) y
escribe el sha256 y los bytes de cada uno como `e0/<archivo>`, el sha256 del código de E0 con que corrió y los comandos.
La salida misma no entra al repo: tiene el texto de todas las unidades (el despacho de S0-6b); va al paquete de
revisión.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

COMANDO = ("s0_6/b/scripts/lote_controles_S0-6b.sh <trabajo> <copia> <raíz final> <python>: dos veces "
           "s0_1/scripts/correr_152.py --codigo <raíz final> --salida <dir> --workers 9 (la raíz la arma "
           "s0_4/scripts/raiz_minima.sh desde una copia del repo, con el código del repo); la corrida 1 es la del manifiesto")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--tiempos", type=Path, required=True)
    ap.add_argument("--tiempos2", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    arch, total = {}, 0
    for p in sorted(a.e0.iterdir()):
        if p.is_file():
            arch[f"e0/{p.name}"] = {"sha256": sha(p), "bytes": p.stat().st_size}
            total += p.stat().st_size
    unidades = {p.name[len("chunks_"):-5]: len(json.loads(p.read_text(encoding="utf-8")))
                for p in sorted(a.e0.glob("chunks_*.json"))}
    m = {"unidad": "U-SEG-OFICIAL, S0-6b (código de E0 del repo, con el parche de S0-6a-bis aplicado)",
         "commit_codigo": "PENDIENTE (lo fija el commit de la autora)",
         "codigo_sha256": {n: sha(a.codigo / n) for n in ("e0_lib.py", "correr_e0.py", "e0_tablas.py")},
         "version_e0": "e0-r2",
         "comando_corrida": COMANDO,
         "corrida_1": a.tiempos.read_text(encoding="utf-8").strip().splitlines(),
         "corrida_2": a.tiempos2.read_text(encoding="utf-8").strip().splitlines() if a.tiempos2 else None,
         "tos": len(unidades), "unidades": sum(unidades.values()), "unidades_por_to": unidades,
         "archivos_e0": sum(1 for r in arch if r.startswith("e0/")),
         "archivos": len(arch), "bytes": total,
         "sha256": arch}
    a.out.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in m.items() if k not in ("sha256", "unidades_por_to")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
