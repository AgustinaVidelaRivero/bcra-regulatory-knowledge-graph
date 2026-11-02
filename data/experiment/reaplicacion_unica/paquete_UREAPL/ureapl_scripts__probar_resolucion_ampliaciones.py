"""U-REAPL, las claves: control en memoria de cuántas ampliaciones re-resuelven sus filas de evidencia al id de la
ampliación, con la regla de E4 sobre la mención (r1_e4.resolver_mencion_r2, sin sujeto por defecto del TO) y el índice del
catálogo de resolución compuesto G. Solo cuentas; ninguna clave, forma ni texto.

Uso, desde la raíz de la copia del repo:
  <repo>/.venv/bin/python -B probar_resolucion_ampliaciones.py <ampliaciones.json> <G> <registro.jsonl>
"""
import collections
import json
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "data/experiment/tanda0/code")
import ensamblar_tanda0 as ENS  # noqa: E402

E4 = ENS.E4
ampl = json.load(open(sys.argv[1], encoding="utf-8"))["ampliaciones"]
cat = E4.catalogo_resolucion_r2(sys.argv[2])
idx = cat["indice"]
pref = E4._prefijos(idx)
reg = {(r["to"], r["chunk_id"], r["indice_relacion"]): r for r in
       (json.loads(x) for x in open(sys.argv[3], encoding="utf-8") if x.strip())}
por_amp = collections.Counter()
filas = collections.Counter()
for a in ampl:
    resueltas = 0
    for e in a["evidencia"]:
        r = reg[(e["to"], e["chunk_id"], e["indice_relacion"])]
        out = E4.resolver_mencion_r2(r["mencion"], r.get("padre_sugerido"), idx, pref, None)
        ok = out["id"] == a["id"]
        resueltas += ok
        filas[(a["operacion"], "al_id" if ok else ("a_otro" if out["id"] else (out["motivo"] or "sin_id")))] += 1
    por_amp[(a["operacion"], "todas" if resueltas == len(a["evidencia"]) else ("ninguna" if resueltas == 0 else "algunas"))] += 1
print(json.dumps({"catalogo_sha256": cat["catalogo_sha256"],
                  "ampliaciones_por_resultado": {f"{k[0]}:{k[1]}": v for k, v in sorted(por_amp.items())},
                  "filas_de_evidencia_por_resultado": {f"{k[0]}:{k[1]}": v for k, v in sorted(filas.items())}},
                 ensure_ascii=False))
