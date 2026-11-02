"""U-SEG-OFICIAL, S1-quater (sorteo): compara dos fotos sha256 del repo (USD 0, sin API).

Uso: python -B comparar_fotos_S1quater_sorteo.py --antes <foto> --despues <foto> --permitido <prefijo> --out <json de cuentas>

Cada foto es la salida de `find . -path ./.git -prune -o -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256`, corrida desde
la raíz del repo. Cuenta los archivos nuevos, borrados y cambiados, y separa los que caen bajo el prefijo permitido de los demás.
Escribe solo cuentas y las rutas bajo el prefijo permitido. Sale con código 1 si cambia algo fuera del prefijo.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def leer(p: Path) -> dict[str, str]:
    out = {}
    for linea in p.read_text(encoding="utf-8").splitlines():
        h, ruta = linea.split("  ", 1)
        out[ruta] = h
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", type=Path, required=True)
    ap.add_argument("--despues", type=Path, required=True)
    ap.add_argument("--permitido", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    antes, despues = leer(a.antes), leer(a.despues)
    nuevos = sorted(set(despues) - set(antes))
    borrados = sorted(set(antes) - set(despues))
    cambiados = sorted(r for r in set(antes) & set(despues) if antes[r] != despues[r])
    dentro = lambda rs: [r for r in rs if r.startswith(a.permitido)]  # noqa: E731
    fuera = lambda rs: [r for r in rs if not r.startswith(a.permitido)]  # noqa: E731
    c = {"control": "foto sha256 del repo (sin .git), antes y después",
         "hora": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
         "archivos_antes": len(antes), "archivos_despues": len(despues), "permitido": a.permitido,
         "nuevos_dentro": dentro(nuevos), "cambiados_dentro": dentro(cambiados), "borrados_dentro": dentro(borrados),
         "nuevos_fuera": len(fuera(nuevos)), "cambiados_fuera": len(fuera(cambiados)), "borrados_fuera": len(fuera(borrados))}
    c["ok"] = c["nuevos_fuera"] == c["cambiados_fuera"] == c["borrados_fuera"] == 0
    a.out.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(c, ensure_ascii=False, indent=1))
    sys.exit(0 if c["ok"] else 1)


if __name__ == "__main__":
    main()
