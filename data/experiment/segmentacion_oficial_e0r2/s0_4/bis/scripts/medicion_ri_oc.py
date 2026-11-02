"""S0-4a-bis (U-SEG-OFICIAL), USD 0, solo lectura: qué daría sumar ri_oc a la lista de sub-documento, con la guarda
del régimen de la página 1 (variante de medición `S0_4_SD_MEDICION`, no aplicada). Compara la corrida de ri_oc con la
variante contra la referencia (el código final con todas las reglas): ids nuevos, ids que desaparecen, unidades que
cambian (con sus caracteres y páginas), los sub-documentos abiertos y dónde quedan los renglones del Apartado B
(pp. 16 a 21) y de los Anexos I y II (pp. 22 y 23). Uso: python -B medicion_ri_oc.py <ref> <medición> <salida.json>"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

ref, med, salida = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
to = "ri_oc"
a = {c["id"]: c for c in json.loads((ref / f"chunks_{to}.json").read_text(encoding="utf-8"))}
b = {c["id"]: c for c in json.loads((med / f"chunks_{to}.json").read_text(encoding="utf-8"))}
est_b = json.loads((med / f"estructura_{to}.json").read_text(encoding="utf-8"))


def fila(c):
    return OrderedDict([("id", c["id"]), ("chars_propio", len(c["texto"])), ("paginas", c["paginas"]),
                        ("inicio", c["texto"][:90]), ("fin", c["texto"][-60:]),
                        ("herencia", [h["texto"][:60] for h in c["herencia"]])])


def donde(chs, pagina_min, pagina_max):
    """Unidades con texto en el rango de páginas, con sus caracteres."""
    return [OrderedDict([("id", c["id"]), ("chars_propio", len(c["texto"])), ("paginas", c["paginas"])])
            for c in chs.values() if any(pagina_min <= p <= pagina_max for p in c["paginas"])]


out = OrderedDict([
    ("criterio", __doc__.split("Uso:")[0].strip()),
    ("unidades", [len(a), len(b)]),
    ("ids_nuevos", [fila(b[i]) for i in b if i not in a]),
    ("ids_que_desaparecen", [fila(a[i]) for i in a if i not in b]),
    ("cambian", [OrderedDict([("antes", fila(a[i])), ("despues", fila(b[i]))]) for i in a if i in b and a[i] != b[i]]),
    ("subdocumentos", est_b.get("subdocumentos")),
    ("apartado_b_pp_16_21", {"referencia": donde(a, 16, 21), "medicion": donde(b, 16, 21)}),
    ("anexos_pp_22_23", {"referencia": donde(a, 22, 23), "medicion": donde(b, 22, 23)}),
])
salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"ri_oc {len(a)} -> {len(b)}: nuevos {len(out['ids_nuevos'])}, desaparecen {len(out['ids_que_desaparecen'])}, "
      f"cambian {len(out['cambian'])}")
