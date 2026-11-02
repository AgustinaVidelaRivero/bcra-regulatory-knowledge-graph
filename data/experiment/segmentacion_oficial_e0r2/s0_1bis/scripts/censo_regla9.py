"""S0-1 bis, C (regla 9): tablas con forma de catálogo (filas cuya primera celda es solo un número de punto, ver
`filas_de_catalogo_r9`) en los 152 TOs (PDFs de escalado_prep) y en los diez de la tanda 0, con sus filas por página
y cuántas tienen un renglón de número único en su banda. Usa las funciones del prototipo. Solo lectura.

Uso: python -B censo_regla9.py <raíz de la copia> <salida.json> [--workers N]"""
import json
import sys
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
RAIZ = Path(sys.argv[1])


def uno(args):
    to, pdf = args
    sys.path.insert(0, str(RAIZ / "data/experiment/reextraccion_v2/e0_chunking"))
    import correr_e0 as CE
    import e0_lib as E0
    paginas = E0.extraer_lineas(pdf)
    filas = CE.filas_de_catalogo_r9(pdf, CE.tablas_de_to_r2(pdf, to), paginas)
    return to, [{k: (list(v) if isinstance(v, tuple) else v) for k, v in f.items()} for f in filas]


def main():
    sal = Path(sys.argv[2])
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    c = json.loads((RAIZ / "data/experiment/segmentacion_84/b584_particion/conteos_b584.json").read_text())
    pdfs = RAIZ / "data/experiment/escalado_prep/pdfs"
    trabajos = [(t, pdfs / f"{t}.pdf") for t in sorted(t for t, v in c.items() if isinstance(v, dict))]
    man = json.loads((RAIZ / "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos.json").read_text())
    trabajos += [("tanda0:" + t["id"], RAIZ / t["pdf"]) for t in man["tos"]]
    with ProcessPoolExecutor(w) as ex:
        res = dict(ex.map(uno, [(t.split(":")[-1] if t.startswith("tanda0:") else t, p) for t, p in trabajos]))
    por_to = OrderedDict()
    for t, _ in trabajos:
        filas = res[t.split(":")[-1]]
        if filas:
            por_to[t] = OrderedDict([("filas", len(filas)), ("paginas", sorted({f["pagina"] for f in filas})),
                                     ("con_renglon_de_numero", sum(1 for f in filas if f["rotulo"])),
                                     ("numeros", [f["numero"] for f in filas])])
    out = OrderedDict([("tos_revisados", len(trabajos)), ("tos_con_filas_de_catalogo", list(por_to)),
                       ("filas_total", sum(v["filas"] for v in por_to.values())), ("por_to", por_to)])
    sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "por_to"}, ensure_ascii=False))
    for t, v in por_to.items():
        print(" ", t, v["filas"], "filas, pp.", v["paginas"], "con renglón de número", v["con_renglon_de_numero"])


if __name__ == "__main__":
    main()
