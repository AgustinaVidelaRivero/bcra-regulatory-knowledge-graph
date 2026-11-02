"""Compara la clasificación por tipo de la autora con el control del modelo (EV2).

Lee tipo_pregunta_hoja.csv, tipo_pregunta_autora.csv y tipo_pregunta_control.json
y escribe tipo_pregunta_ev2.json: sha256 de los cinco archivos de entrada, modelo /
temperatura / fecha del control, 40 entradas por orden y un resumen con acuerdo
simple. Determinista, sin red.

Con --adjudicacion <csv> (columnas orden,id,tipo_final,fundamento) resuelve las
entradas sin acuerdo con el tipo_final adjudicado por la autora, agrega los campos
`adjudicada` y `fundamento_adjudicacion`, y suma al resumen el sha256 del CSV, la
distribución de tipo_final y el número de entradas adjudicadas. Sin el flag, la
salida es idéntica a la de la versión anterior.
"""
import argparse, csv, hashlib, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
D = REPO / "data/experiment/exploracion/ev2_fidelidad"
TIPOS = ["dato directo", "varios puntos", "abstención", "dudoso"]
REQ = "requiere_adjudicacion"
COLS_ADJ = ["orden", "id", "tipo_final", "fundamento"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cargar_adjudicacion(path: Path, entradas: list, hoja: list) -> dict:
    """Valida el CSV de adjudicación contra la hoja y las entradas; aborta con mensaje."""
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != COLS_ADJ:
            sys.exit(f"ERROR adjudicación: encabezado {rd.fieldnames}, esperado {COLS_ADJ}")
        rows = list(rd)
    ids_hoja = {int(h["orden"]): h["id"] for h in hoja}
    por_orden = {}
    for r in rows:
        try:
            o = int(r["orden"])
        except (TypeError, ValueError):
            sys.exit(f"ERROR adjudicación: orden no entero {r['orden']!r}")
        if o in por_orden:
            sys.exit(f"ERROR adjudicación: orden {o} repetido")
        if o not in ids_hoja or ids_hoja[o] != r["id"]:
            sys.exit(f"ERROR adjudicación: orden {o} e id {r['id']!r} no coinciden con la hoja")
        if r["tipo_final"] not in TIPOS:
            sys.exit(f"ERROR adjudicación: tipo_final {r['tipo_final']!r} en orden {o} no es uno de {TIPOS}")
        por_orden[o] = r
    con_acuerdo = {e["orden"] for e in entradas if e["acuerdo"]}
    sin_acuerdo = {e["orden"] for e in entradas if not e["acuerdo"]}
    sobran = sorted(set(por_orden) & con_acuerdo)
    if sobran:
        sys.exit(f"ERROR adjudicación: filas para entradas con acuerdo: {sobran}")
    faltan = sorted(sin_acuerdo - set(por_orden))
    if faltan:
        sys.exit(f"ERROR adjudicación: faltan filas para entradas sin acuerdo: {faltan}")
    return por_orden


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(D))
    ap.add_argument("--out", default=None, help="por defecto <dir>/tipo_pregunta_ev2.json")
    ap.add_argument("--adjudicacion", default=None,
                    help="CSV orden,id,tipo_final,fundamento con la adjudicación de la autora")
    a = ap.parse_args()
    d = Path(a.dir)
    out = Path(a.out) if a.out else d / "tipo_pregunta_ev2.json"
    f_hoja, f_regla, f_lect = d / "tipo_pregunta_hoja.csv", d / "regla_tipo_pregunta.md", d / "tipo_pregunta_lectura.md"
    f_ctl, f_aut = d / "tipo_pregunta_control.json", d / "tipo_pregunta_autora.csv"

    hoja = sorted(csv.DictReader(open(f_hoja, encoding="utf-8", newline="")), key=lambda r: int(r["orden"]))
    aut = sorted(csv.DictReader(open(f_aut, encoding="utf-8", newline="")), key=lambda r: int(r["orden"]))
    ctl = json.loads(f_ctl.read_text(encoding="utf-8"))
    mod = sorted(ctl["entradas"], key=lambda e: int(e["orden"]))
    assert len(hoja) == len(aut) == len(mod) == 40
    assert [r["id"] for r in hoja] == [r["id"] for r in aut] == [e["id"] for e in mod]

    entradas = []
    for h, u, m in zip(hoja, aut, mod):
        ta, tm = u["tipo"], m["tipo"]
        acuerdo = ta == tm
        entradas.append({
            "orden": int(h["orden"]), "id": h["id"], "to": h["to"],
            "tipo_autora": ta, "nota_autora": u["nota"],
            "tipo_modelo": tm, "nota_modelo": m["nota"],
            "acuerdo": acuerdo,
            "tipo_final": ta if acuerdo else REQ,
        })
    dist = lambda campo: {t: sum(1 for e in entradas if e[campo] == t) for t in TIPOS}
    n_ac = sum(1 for e in entradas if e["acuerdo"])

    n_adj = 0
    if a.adjudicacion:
        adj = cargar_adjudicacion(Path(a.adjudicacion), entradas, hoja)
        for e in entradas:
            if e["acuerdo"]:
                e["adjudicada"] = False
            else:
                r = adj[e["orden"]]
                e["tipo_final"] = r["tipo_final"]
                e["adjudicada"] = True
                e["fundamento_adjudicacion"] = r["fundamento"]
                n_adj += 1

    resumen = {
        "distribucion_autora": dist("tipo_autora"),
        "distribucion_modelo": dist("tipo_modelo"),
        "acuerdos": n_ac,
        "sobre": len(entradas),
        "ordenes_sin_acuerdo": [e["orden"] for e in entradas if not e["acuerdo"]],
    }
    if a.adjudicacion:
        resumen["sha256_adjudicacion"] = sha256(Path(a.adjudicacion))
        resumen["distribucion_tipo_final"] = {t: sum(1 for e in entradas if e["tipo_final"] == t)
                                              for t in TIPOS + [REQ]}
        resumen["entradas_adjudicadas"] = n_adj

    salida = {
        "entradas_sha256": {
            "tipo_pregunta_hoja.csv": sha256(f_hoja),
            "regla_tipo_pregunta.md": sha256(f_regla),
            "tipo_pregunta_lectura.md": sha256(f_lect),
            "tipo_pregunta_control.json": sha256(f_ctl),
            "tipo_pregunta_autora.csv": sha256(f_aut),
        },
        "modelo": ctl["modelo"],
        "temperatura": ctl["temperatura"],
        "fecha_control": ctl["fecha"],
        "entradas": entradas,
        "resumen": resumen,
    }
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("escrito:", out, "| entradas:", len(entradas), "| acuerdos:", n_ac, "/", len(entradas),
          "| adjudicadas:", n_adj)


if __name__ == "__main__":
    main()
