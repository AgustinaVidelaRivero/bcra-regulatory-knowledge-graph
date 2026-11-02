"""Versión sin texto de unidades de las salidas del control de continuidad (U-SEG-OFICIAL, S0-6a; solo lectura; mandato
de S0-6a, §5: de las unidades que no son las 40 filas ni las 286 leídas, ids y cuentas). Quita de los JSON los campos
`renglon` y `final_renglon_anterior`, y de la lista en markdown las citas entre «»; la versión completa va al paquete de
revisión con el prefijo `NO_ABRIR_`.

Uso: python -B sin_texto_S0-6a.py json <entrada.json> <salida.json>
     python -B sin_texto_S0-6a.py md <entrada.md> <salida.md>
"""
import json
import re
import sys
from pathlib import Path

modo, ent, sal = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
QUITAR = ("renglon", "final_renglon_anterior")


def limpiar(x):
    if isinstance(x, dict):
        return {k: limpiar(v) for k, v in x.items() if k not in QUITAR}
    if isinstance(x, list):
        return [limpiar(v) for v in x]
    return x


if modo == "json":
    sal.write_text(json.dumps(limpiar(json.loads(ent.read_text(encoding="utf-8"))), ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
else:
    t = re.sub(r"«[^»\n]*»", "«…»", ent.read_text(encoding="utf-8"))
    sal.write_text(t, encoding="utf-8")
print(sal.name, "escrito")
