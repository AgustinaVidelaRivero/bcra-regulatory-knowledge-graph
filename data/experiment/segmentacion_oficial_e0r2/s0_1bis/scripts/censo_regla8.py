"""S0-1 bis, B (regla 8): censo de las corridas candidatas a lista de puntos leída como cuerpo, con sus medidas y la
guarda que descarta cada una, sobre los 152 TOs (caché de líneas) y los diez PDFs de la tanda 0. Usa la función de
detección del prototipo (`lineas_de_listas_r8`, con `informe`) sobre los roles finales de la escalera. Solo lectura.

Uso: S0_REGLAS=... python -B censo_regla8.py <raíz de la copia> <caché de líneas> <salida.json>"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.dont_write_bytecode = True
raiz, cache, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(raiz / "data/experiment/reextraccion_v2/e0_chunking"))
import correr_e0 as CE  # noqa: E402
import e0_lib as E0  # noqa: E402


def main():
    tos = json.loads((raiz / "data/experiment/segmentacion_84/b584_particion/conteos_b584.json").read_text())
    fuentes = [(t, cache / f"{t}.json") for t in sorted(t for t, v in tos.items() if isinstance(v, dict))]
    man = json.loads((raiz / "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos.json").read_text())
    fuentes += [("tanda0:" + t["id"], raiz / t["pdf"]) for t in man["tos"]]
    filas = []
    for to, fuente in fuentes:
        if fuente.suffix == ".pdf":
            paginas = E0.extraer_lineas(fuente)
        else:
            paginas = [[E0.Linea(*x) for x in p] for p in json.loads(fuente.read_text(encoding="utf-8"))]
        roles = E0.clasificar_paginas(paginas)
        _res, roles, _rep, modo, _marc = CE.escalera_e0_r2(to.split(":")[-1], f"{to}.pdf", paginas, roles)
        inf: list = []
        E0.lineas_de_listas_r8(paginas, roles, informe=inf)
        for f in inf:
            filas.append(OrderedDict([("to", to), ("modo", modo)] + list(f.items())))
    detectadas = [f for f in filas if f.get("descarte") is None]
    out = OrderedDict([
        ("corridas_candidatas", len(filas)),
        ("por_descarte", dict(Counter(f.get("descarte") or "detectada" for f in filas))),
        ("detectadas", [OrderedDict([("to", f["to"]), ("pagina", f["pagina"]), ("rotulos", f["rotulos"])])
                        for f in detectadas]),
        ("rotulos_detectados", sum(f["rotulos"] for f in detectadas)),
        ("descartadas_con_todos_los_numeros_repetidos", [f for f in filas if f.get("reaparecen") == f["rotulos"]
                                                        and f.get("descarte")]),
        ("filas", filas)])
    sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("filas", "descartadas_con_todos_los_numeros_repetidos")},
                     ensure_ascii=False))
    for f in out["descartadas_con_todos_los_numeros_repetidos"]:
        print("  descartada", f["to"], "p", f["pagina"], f["rotulos"], f["descarte"], f.get("con_titulo"),
              f.get("con_corte"), f.get("brecha_mediana"), "|", f["primera"][:50])


if __name__ == "__main__":
    main()
