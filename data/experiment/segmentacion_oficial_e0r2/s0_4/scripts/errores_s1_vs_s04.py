"""Las unidades marcadas error o dudosa en la lectura de cortes de S1 (s1/lectura_cortes/, marcas de la revisión)
frente a una corrida de S0-4: si la unidad sigue existiendo, si cambia su texto, el comienzo y el final de su texto
antes y después y, si desaparece, en qué unidades de la corrida nueva están su primer y su último renglón. No lee el
PDF ni marca: es el insumo para leer (proyección, no lectura). Extiende `s0_3/scripts/errores_s1_vs_s03.py`.
Uso: python -B errores_s1_vs_s04.py <tsv de marcas> <dir base> <dir nueva> <salida.json>"""
import csv, json, sys
from pathlib import Path
sys.dont_write_bytecode = True
tsv, base, nueva, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
cache = {}


def chunks(d, to):
    k = (str(d), to)
    if k not in cache:
        p = d / f"chunks_{to}.json"
        cache[k] = {c["id"]: c for c in json.loads(p.read_text())} if p.exists() else {}
    return cache[k]


def donde(to, renglon):
    return [i for i, c in chunks(nueva, to).items() if renglon in c["texto"].split("\n")]


out = []
for f in csv.DictReader(open(tsv, encoding="utf-8"), delimiter="\t"):
    if f["marca"] not in ("error", "dudosa") or f["id"].startswith("("):
        continue
    to, uid = f["to"], f["id"]
    b, n = chunks(base, to).get(uid), chunks(nueva, to).get(uid)
    fila = {"fila": f["fila"], "grupo": f["grupo"], "id": uid, "marca": f["marca"], "clase": f["clase"],
            "subclase": f["subclase"], "existe_en_nueva": n is not None,
            "texto_cambia": (n is not None and b is not None and n["texto"] != b["texto"]),
            "chars": [b["chars_propio"] if b else None, n["chars_propio"] if n else None],
            "paginas": [b["paginas"] if b else None, n["paginas"] if n else None],
            "antes": {"inicio": b["texto"][:90], "fin": b["texto"][-90:]} if b else None,
            "despues": {"inicio": n["texto"][:90], "fin": n["texto"][-90:]} if n else None}
    if b is not None:
        ls = [x for x in b["texto"].split("\n") if x.strip()]
        fila["primer_renglon_en"] = donde(to, ls[0]) if ls else []
        fila["ultimo_renglon_en"] = donde(to, ls[-1]) if ls else []
    out.append(fila)
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for x in out:
    print(f"{x['fila']:>4} {x['marca']:7} {x['id']:42} existe={x['existe_en_nueva']!s:5} cambia={x['texto_cambia']!s:5} "
          f"{x['chars']} primer->{x.get('primer_renglon_en', [])[:3]} ultimo->{x.get('ultimo_renglon_en', [])[:3]}")
