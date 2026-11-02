"""U-REAPL, las claves: las ampliaciones que re-resuelven solo algunas de sus filas de evidencia con el catálogo G (la regla
de probar_resolucion_ampliaciones.py), por su clave y su código del veredicto, con las filas que resuelven y las que no
(cuentas). Sin texto de unidades ni menciones. Uso, desde la raíz de la copia:
  <python> -B alias_que_resuelven_a_medias.py <ampliaciones.json> <G> <registro.jsonl> <veredictos.json>"""
import json
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "data/experiment/tanda0/code")
import ensamblar_tanda0 as ENS  # noqa: E402

E4 = ENS.E4
ampl = json.load(open(sys.argv[1], encoding="utf-8"))["ampliaciones"]
cat = E4.catalogo_resolucion_r2(sys.argv[2])
idx, pref = cat["indice"], E4._prefijos(cat["indice"])
reg = {(r["to"], r["chunk_id"], r["indice_relacion"]): r for r in
       (json.loads(x) for x in open(sys.argv[3], encoding="utf-8") if x.strip())}
cod = {v["clave"]: v["codigo"] for v in json.load(open(sys.argv[4], encoding="utf-8"))["veredictos"]}


def clave(m):
    return E4._norm_sing(E4._sin_parentesis(E4.RE_ARTICULO_INICIAL.sub("", m or "")))


for a in ampl:
    filas = [reg[(e["to"], e["chunk_id"], e["indice_relacion"])] for e in a["evidencia"]]
    ok = [E4.resolver_mencion_r2(r["mencion"], r.get("padre_sugerido"), idx, pref, None)["id"] == a["id"] for r in filas]
    if 0 < sum(ok) < len(ok):
        k = {clave(r["mencion"]) for r in filas}
        assert len(k) == 1
        k = k.pop()
        print(json.dumps({"clave": k, "codigo": cod[k], "filas_que_resuelven": sum(ok), "filas_que_no": len(ok) - sum(ok)},
                         ensure_ascii=False))
