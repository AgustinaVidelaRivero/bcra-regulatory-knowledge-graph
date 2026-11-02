"""Caché de las líneas de E0 (`e0_lib.extraer_lineas`) de los 152 PDFs, para los censos de S0-1. Solo lectura de
los PDFs de la copia; escribe un JSON por TO en <salida>.

Uso: python -B lineas_152.py <raíz de la copia> <salida> [--workers 6]
Carga: `cargar(salida, to)` devuelve list[list[Linea]].
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True


def _uno(args):
    raiz, to, sal = args
    sys.path.insert(0, str(Path(raiz) / "data/experiment/reextraccion_v2/e0_chunking"))
    import e0_lib as E0
    ps = E0.extraer_lineas(Path(raiz) / "data/experiment/escalado_prep/pdfs" / f"{to}.pdf")
    out = [[[l.pagina, l.top, l.x0, l.texto, l.ngaps, l.ultimo_numerico, l.primer_codigo] for l in p] for p in ps]
    (Path(sal) / f"{to}.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return to


def cargar(sal, to, E0):
    d = json.loads((Path(sal) / f"{to}.json").read_text(encoding="utf-8"))
    return [[E0.Linea(*x) for x in p] for p in d]


if __name__ == "__main__":
    raiz, sal = sys.argv[1], sys.argv[2]
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    Path(sal).mkdir(parents=True, exist_ok=True)
    c = json.loads((Path(raiz) / "data/experiment/segmentacion_84/b584_particion/conteos_b584.json").read_text())
    tos = sorted(t for t, v in c.items() if isinstance(v, dict) and not (Path(sal) / f"{t}.json").exists())
    with ProcessPoolExecutor(w) as ex:
        for t in ex.map(_uno, [(raiz, t, sal) for t in tos]):
            pass
    print("listo", len(tos))
