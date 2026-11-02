import json, csv, random, sys
from pathlib import Path

BASE = Path("data/experiment/reextraccion_v2/e0_chunking/salida_enm01")
QPATH = Path("data/experiment/exploracion/ev2_fidelidad/preguntas_ev2_fidelidad.json")
OUT = Path("data/experiment/exploracion/ev2_fidelidad/tipo_pregunta_hoja.csv")
if OUT.exists():
    sys.exit("FRENO: la hoja ya existe")

qs = json.load(open(QPATH, encoding="utf-8"))["preguntas"]
byid = {q["id"]: q for q in qs}
ids = sorted(byid)
rng = random.Random(20260920)
rng.shuffle(ids)
orden = {id_: i + 1 for i, id_ in enumerate(ids)}

E0 = {to: json.load(open(BASE / f"estructura_{to}.json", encoding="utf-8"))
      for to in ["ext", "cap", "cla", "ric", "pro"]}

def flat(nodes, acc):
    for n in nodes:
        acc.append(n); flat(n.get("hijos", []), acc)
    return acc

def in_scope(num, ancla):
    return num == ancla or num.startswith(ancla + ".")

def numkey(num):
    return tuple(int(x) for x in num.split("."))

def faltantes_por_saltos(d, ancla):
    miss = []
    for s in d.get("saltos_numeracion", []):
        if s.get("tipo") != "salto_hermano":
            continue
        for k in range(s["de"] + 1, s["a"]):
            num = f"{s['padre']}.{k}"
            if in_scope(num, ancla):
                miss.append(num)
    return miss

def render(n, faltantes, blocks, no_enc):
    num = n["numero"]
    tit = (n.get("titulo") or "").strip()
    segs = n.get("segmentos", [])
    lead = [s for s in segs if s["rol"] != "cierre"]
    cierre = [s for s in segs if s["rol"] == "cierre"]
    if not segs and not tit and not n.get("hijos"):
        blocks.append(f"[{num}] NO ENCONTRADO"); no_enc.append(num)
    else:
        parts = [f"[{num}] {tit}".rstrip()]
        for s in lead:
            t = s["texto"]
            if s["rol"] == "intersticial":
                t = "(intersticial) " + t
            parts.append(t)
        blocks.append("\n".join(parts))
    # hijos reales + faltantes directos, en orden numérico
    items = [(numkey(h["numero"]), "nodo", h) for h in n.get("hijos", [])]
    items += [(numkey(m), "falta", m) for m in faltantes if m.rsplit(".", 1)[0] == num]
    for _, kind, obj in sorted(items, key=lambda x: x[0]):
        if kind == "nodo":
            render(obj, faltantes, blocks, no_enc)
        else:
            blocks.append(f"[{obj}] NO ENCONTRADO"); no_enc.append(obj)
    if cierre:
        blocks.append("\n".join([f"[{num}] (cierre)"] + [s["texto"] for s in cierre]))

rows, no_enc_ids, pipes = [], [], []
for id_ in ids:
    q = byid[id_]
    anclas = q["gold"]["ancla"]
    assert len(anclas) == 1, (id_, anclas)
    to, num = anclas[0].split(":")
    assert to == q["to"], (id_, to, q["to"])
    d = E0[to]
    nodes = flat(d["secciones"], [])
    pref = [n for n in nodes if in_scope(n["numero"], num)]
    anc = next((n for n in nodes if n["numero"] == num), None)
    no_enc = []
    if anc is None:
        texto = "NO ENCONTRADO"; no_enc.append(num)
    else:
        sub = []
        def _sub(n):
            sub.append(n)
            for h in n.get("hijos", []): _sub(h)
        _sub(anc)
        assert [n["numero"] for n in pref] == [n["numero"] for n in sub], (id_, num)
        blocks = []
        render(anc, faltantes_por_saltos(d, num), blocks, no_enc)
        texto = "\n\n".join(blocks)
    if no_enc:
        no_enc_ids.append((id_, anclas[0], "total" if anc is None else "parcial", no_enc))
    crits = [c["criterio"] for c in q["gold"]["criterios"]]
    if any("|" in c for c in crits):
        pipes.append(id_)
    rows.append({
        "orden": orden[id_], "id": id_, "to": to, "pregunta": q["pregunta"],
        "ancla": anclas[0], "criterios": " | ".join(crits), "texto_ancla": texto,
        "tipo": "", "nota": "",
    })

cols = ["orden", "id", "to", "pregunta", "ancla", "criterios", "texto_ancla", "tipo", "nota"]
with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)

print("orden de lectura (semilla 20260920):", ids)
print("ids con NO ENCONTRADO total o parcial:", no_enc_ids if no_enc_ids else "ninguno")
print("criterios que contienen '|':", pipes if pipes else "ninguno")
print("\nwc -c (bytes UTF-8) de texto_ancla por fila:")
print(f"{'orden':>5}  {'id':<9} {'ancla':<12} {'bytes':>7}")
tot = 0
for r in rows:
    b = len(r["texto_ancla"].encode("utf-8")); tot += b
    print(f"{r['orden']:>5}  {r['id']:<9} {r['ancla']:<12} {b:>7}")
print(f"{'':>5}  {'TOTAL':<9} {'':<12} {tot:>7}")
