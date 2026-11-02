"""Evidencia de las 40 filas de S0-6a (U-SEG-OFICIAL; USD 0, sin API): por fila del TSV de errores confirmados de S1-ter,
la unidad de la E0 de S1-ter y lo que hay en la E0 corregida.

Uso: python -B filas_40_S0-6a.py <dir de comun_S1quater.py> <E0 de S1-ter> <E0 corregida> <tsv> <salida.json>
       --fichas <fichas de S1-ter (json: id_opaco, id)> [--md <salida.md>]

La unidad nueva es la del mismo id (o sus partes); si no existe, las que solapan su texto (`solapes_S0_6a.py`). Para «la que
sigue», la unidad de la ficha y la que le sigue en la E0 corregida; para «la herencia», sus tramos. La salida lleva texto
de las 40 filas (mandato, §5: el texto de unidades va solo para las 40 filas y las 286 leídas).
"""
import sys, json, csv, re
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import comun_S1quater as Q     # sin cambios: solo la clase E0 (lee la salida); el solape es propio (solapes_S0_6a.py)
sys.path.insert(0, str(Path(__file__).parent))
from solapes_S0_6a import solapes
vieja, nueva = Q.E0(Path(sys.argv[2])), Q.E0(Path(sys.argv[3]))
filas = list(csv.DictReader(open(sys.argv[4], encoding="utf-8"), delimiter="\t"))
fichas = {f["id_opaco"]: f for f in json.load(open(sys.argv[sys.argv.index("--fichas") + 1]))}
md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
alin = {}

def resumen(c, n=400):
    return {"id": c["id"], "paginas": c["paginas"], "renglones": len(c["texto"].split("\n")),
            "texto_inicio": c["texto"][:n], "texto_fin": c["texto"][-200:],
            "herencia": [{"tipo": t["tipo"], "origen": t["unidad_origen"], "texto": t["texto"][:300]} for t in c["herencia"]]}

out = []
for f in filas:
    uid, to = f["id_unidad_e0"], f["documento"]
    if to not in alin:
        alin[to] = solapes(vieja.chunks(to), nueva.chunks(to))
    viejas = vieja.partes(uid)
    ids_nuevos = [c["id"] for c in nueva.chunks(to)]
    exacto = [c for c in nueva.chunks(to) if c["id"] == uid or re.match(re.escape(uid) + r"::parte\d+$", c["id"])]
    if exacto:
        nuevas = exacto
        modo = "mismo_id"
    else:
        vid = {c["id"] for c in viejas}
        nuevas = [c for c in nueva.chunks(to) if set(alin[to][c["id"]]) & vid]
        modo = "solapa"
    fila = {"ficha": f["ficha"], "pregunta": f["pregunta"], "documento": to, "unidad_vieja": uid, "modo": modo,
            "vieja": [resumen(c, 200) for c in viejas], "nueva": [resumen(c) for c in nuevas]}
    if f["pregunta"] == "la_que_sigue":
        # la unidad de la ficha (orden de lectura de S1-ter) y la que le sigue en la E0 corregida
        fid = fichas[f["ficha"]]["id"]
        fila["unidad_ficha"] = fid
        L = nueva.chunks(to)
        prop = [c for c in L if c["id"] == fid or re.match(re.escape(fid) + r"::parte\d+$", c["id"])]
        if not prop:
            vids = {c["id"] for c in vieja.partes(fid)}
            prop = [c for c in L if set(alin[to][c["id"]]) & vids]
        fila["ficha_nueva"] = [resumen(c, 200) for c in prop]
        if prop:
            k = max(ids_nuevos.index(c["id"]) for c in prop)
            fila["sigue_nueva"] = resumen(L[k + 1]) if k + 1 < len(L) else None
    out.append(fila)
json.dump(out, open(sys.argv[5], "w"), ensure_ascii=False, indent=1)
if md:
    with open(md, "w") as fh:
        for x in out:
            fh.write(f"### {x['ficha']} · {x['pregunta']} · {x['unidad_vieja']} ({x['modo']})\n")
            for c in x["nueva"]:
                fh.write(f"- nueva `{c['id']}` págs {c['paginas']}, {c['renglones']} renglones\n")
                if x["pregunta"] in ("la_herencia",):
                    for t in c["herencia"]:
                        fh.write(f"    - [{t['tipo']}] {t['origen']}: {t['texto'][:140]!r}\n")
                else:
                    fh.write(f"    - inicio: {c['texto_inicio'][:160]!r}\n    - fin: {c['texto_fin'][-120:]!r}\n")
            for c in x.get("ficha_nueva", []):
                fh.write(f"- unidad de la ficha (nueva) `{c['id']}` págs {c['paginas']}, {c['renglones']} renglones\n")
            if x.get("sigue_nueva"):
                s = x["sigue_nueva"]
                fh.write(f"- la que sigue (nueva) `{s['id']}` págs {s['paginas']}, {s['renglones']} renglones: "
                         f"{s['texto_inicio'][:120]!r} … {s['texto_fin'][-100:]!r}\n")
            fh.write("\n")
print(len(out), "filas")
