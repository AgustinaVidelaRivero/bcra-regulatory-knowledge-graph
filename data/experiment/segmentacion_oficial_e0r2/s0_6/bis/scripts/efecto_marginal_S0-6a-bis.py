"""El efecto de L y de M en la configuración final (U-SEG-OFICIAL, S0-6a-bis; USD 0, solo lectura). L y M solo actúan
dentro de los sub-documentos que abre A (L, en la numeración que vuelve a empezar después de un índice; M, en la raíz 0
de esos sub-documentos): solas, contra todas apagadas, no cambian ningún documento, y el censo por regla no mide su
generalidad. Se mide entonces su efecto marginal: la configuración final contra la final sin esa regla (el prototipo
con todas las demás). Un documento cambia si se crea, se quita o cambia (corte o herencia) al menos una unidad.

Uso: python -B efecto_marginal_S0-6a-bis.py --final <E0 final> --sin l=<E0 sin L> --sin m=<E0 sin M>
       --tsv <TSV de las 40 filas> --out <json>

Solo cuentas, sin ids: por regla y por documento, unidades creadas, quitadas y cambiadas (y de las cambiadas, cuántas
solo en la herencia); el documento de las filas de cada regla (L: E1-008; M: E2-002); si es general (cambia algún
documento donde no se vio su error); y los documentos que saldrían de la bolsa si no lo es.
"""
import argparse
import csv
import json
from pathlib import Path

FILAS = {"l": ("E1-008",), "m": ("E2-002",)}
ap = argparse.ArgumentParser()
ap.add_argument("--final", type=Path, required=True)
ap.add_argument("--sin", action="append", required=True)
ap.add_argument("--tsv", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()
doc_fila = {f["ficha"]: f["documento"] for f in csv.DictReader(a.tsv.open(encoding="utf-8"), delimiter="\t")}


def chunks(d: Path, to: str) -> dict:
    return {c["id"]: c for c in json.loads((d / f"chunks_{to}.json").read_text(encoding="utf-8"))}


res = {}
for x in a.sin:
    r, d = x.split("=", 1)
    d = Path(d)
    por_to = {}
    for p in sorted(a.final.glob("chunks_*.json")):
        to = p.name[len("chunks_"):-5]
        F, S = chunks(a.final, to), chunks(d, to)
        cr, qu = set(F) - set(S), set(S) - set(F)
        corte = {i for i in set(F) & set(S) if (F[i]["sha256_propio"], F[i]["paginas"]) != (S[i]["sha256_propio"], S[i]["paginas"])}
        her = {i for i in set(F) & set(S) - corte if F[i]["herencia"] != S[i]["herencia"]}
        if cr or qu or corte or her:
            por_to[to] = {"creadas": len(cr), "quitadas": len(qu), "cambiadas": len(corte) + len(her),
                          "solo_herencia": len(her)}
    vistos = sorted({doc_fila[f] for f in FILAS[r]})
    donde_no = sorted(set(por_to) - set(vistos))
    res[r] = {"filas": list(FILAS[r]), "documentos_donde_se_vio": vistos, "documentos_que_cambia": len(por_to),
              "documentos_que_cambia_donde_no_se_vio": len(donde_no), "general": bool(donde_no),
              "salen_de_la_bolsa": [] if donde_no else sorted(por_to),
              "unidades": {k: sum(v[k] for v in por_to.values()) for k in ("creadas", "quitadas", "cambiadas",
                                                                             "solo_herencia")},
              "por_to": por_to}
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({r: {k: v for k, v in x.items() if k != "por_to"} for r, x in res.items()}, ensure_ascii=False))
