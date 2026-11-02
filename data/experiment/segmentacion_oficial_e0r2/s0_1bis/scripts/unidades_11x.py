"""S0-1 bis, C: las unidades terminales 11.x de rdbcra en dos salidas de E0 (antes y después de la regla 9), con su
relación con las filas del catálogo (censo de `censo_filas_catalogo.py`): fila con unidad, encabezado de grupo que
quedó terminal porque se rechazaron los números de todas sus filas, o fila sin unidad. Solo lectura.

Uso: python -B unidades_11x.py <censo de filas> <E0 antes> <E0 después> <salida.json>"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

censo, antes, despues, sal = (Path(x) for x in sys.argv[1:5])
filas = [f["numero"] for f in json.loads(censo.read_text(encoding="utf-8"))["filas"] if f["numero"]]


def terminales(d: Path) -> list:
    return [c for c in json.loads((d / "chunks_rdbcra.json").read_text(encoding="utf-8"))
            if c["tipo"] == "punto_terminal" and c["unidad"].startswith("11.")]


def clase(u: str) -> str:
    return "fila" if u in filas else ("encabezado_terminal" if any(f.startswith(u + ".") for f in filas) else "otra")


out = OrderedDict()
for nombre, d in (("antes", antes), ("despues", despues)):
    t = terminales(d)
    unidades = {c["unidad"] for c in t}
    out[nombre] = OrderedDict([
        ("e0", d.name), ("terminales_11x", len(t)),
        ("por_clase", dict(Counter(clase(c["unidad"]) for c in t))),
        ("filas_sin_unidad", [f for f in filas if f not in unidades]),
        ("unidades", [OrderedDict([("id", c["id"]), ("clase", clase(c["unidad"])), ("paginas", c["paginas"]),
                                   ("chars_propio", c["chars_propio"])]) for c in t])])
out["filas_de_catalogo"] = len(filas)
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for k in ("antes", "despues"):
    print(k, out[k]["terminales_11x"], out[k]["por_clase"], "filas sin unidad:", len(out[k]["filas_sin_unidad"]))
