"""Proporciones P1 (regla_P1.md §6): Wilson al 95 % (z = 1,959964) y ponderación por clase con n efectivo de Kish."""
import collections
import csv
import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
Z = 1.959964
CLASES = ["RI", "NG_digerible", "NG_necesita_reglas"]
FORMAS = ["remisión", "excepción en un hijo", "condición en otro punto", "definición en otro punto"]


def wilson(p, n):
    if n <= 0:
        return (float("nan"), float("nan"))
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def cruda(filas, pred):
    n = len(filas)
    x = sum(1 for f in filas if pred(f))
    p = x / n if n else float("nan")
    lo, hi = wilson(p, n)
    return {"x": x, "n": n, "p": p, "lo": lo, "hi": hi}


def ponderada(filas, pred, w):
    sw = sum(w[f["clase"]] for f in filas)
    sw2 = sum(w[f["clase"]] ** 2 for f in filas)
    swy = sum(w[f["clase"]] for f in filas if pred(f))
    p = swy / sw if sw else float("nan")
    nef = sw * sw / sw2 if sw2 else 0.0
    lo, hi = wilson(p, nef)
    return {"p": p, "n_ef": nef, "lo": lo, "hi": hi, "n": len(filas)}


def fmt(r, pct=True):
    f = (lambda v: f"{100 * v:5.1f} %") if pct else (lambda v: f"{v:.4f}")
    base = f"{r['x']}/{r['n']}" if "x" in r else f"n={r['n']}, n_ef={r['n_ef']:.1f}"
    return f"{f(r['p'])}  [{f(r['lo'])} – {f(r['hi'])}]  ({base})"


def main():
    filas = list(csv.DictReader(open(BASE / "clasificacion_P1.csv", encoding="utf-8")))
    pob = json.loads((BASE / "poblacion_P1.json").read_text())
    N = collections.Counter(x["clase"] for x in pob)
    dec = [f for f in filas if f["tipo"] != "no decidible"]
    nd = [f for f in filas if f["tipo"] == "no decidible"]
    n_dec = collections.Counter(f["clase"] for f in dec)
    w = {c: N[c] / n_dec[c] for c in CLASES}
    vp = lambda f: f["tipo"] == "varios puntos"
    dd = lambda f: f["tipo"] == "dato directo"
    res = {"z": Z, "N_clase": dict(N), "n_decidibles_clase": dict(n_dec), "w": w}
    out = [f"z = {Z}", f"N (anclas) por clase: {dict(N)}", f"n decidibles por clase: {dict(n_dec)}",
           "w = N_clase / n_clase(decidibles): " + ", ".join(f"{c} {w[c]:.4f}" for c in CLASES), ""]

    out.append("## 1. Varios puntos y dato directo por clase (sobre decidibles; Wilson con n crudo)")
    res["por_clase"] = {}
    for c in CLASES:
        fc = [f for f in dec if f["clase"] == c]
        a, b = cruda(fc, vp), cruda(fc, dd)
        res["por_clase"][c] = {"varios_puntos": a, "dato_directo": b}
        out.append(f"{c:20s} varios puntos {fmt(a)}")
        out.append(f"{'':20s} dato directo  {fmt(b)}")
    out.append("")

    out.append("## 2. Por tanda (la tanda no es estrato del sorteo)")
    res["por_tanda"] = {}
    for t in ("1", "final"):
        ft = [f for f in dec if f["tanda"] == t]
        a, b = cruda(ft, vp), cruda(ft, dd)
        pw = ponderada(ft, vp, w)
        res["por_tanda"][t] = {"varios_puntos_cruda": a, "dato_directo_cruda": b, "varios_puntos_ponderada": pw}
        out.append(f"tanda {t:6s} varios puntos (cruda)      {fmt(a)}")
        out.append(f"{'':12s} dato directo  (cruda)      {fmt(b)}")
        out.append(f"{'':12s} varios puntos (ponderada)  {fmt(pw)}")
    out.append("")
    out.append("### 2.b Por clase y tanda (crudas)")
    res["por_clase_tanda"] = {}
    for c in CLASES:
        for t in ("1", "final"):
            fct = [f for f in dec if f["clase"] == c and f["tanda"] == t]
            if not fct:
                continue
            a = cruda(fct, vp)
            res["por_clase_tanda"][f"{c}|{t}"] = a
            out.append(f"{c:20s} tanda {t:6s} varios puntos {fmt(a)}")
    out.append("")

    out.append("## 3. Ponderada por las anclas de cada clase (Wilson con n efectivo de Kish)")
    a, b = ponderada(dec, vp, w), ponderada(dec, dd, w)
    res["ponderada"] = {"varios_puntos": a, "dato_directo": b}
    out.append(f"varios puntos {fmt(a)}")
    out.append(f"dato directo  {fmt(b)}")
    out.append(f"(cruda sin ponderar, como referencia: varios puntos {fmt(cruda(dec, vp))})")
    out.append("")

    out.append("## 4. Formas dentro de varios puntos")
    res["formas"] = {}
    vps = [f for f in dec if vp(f)]
    for c in CLASES + ["TOTAL (cruda)"]:
        fc = vps if c.startswith("TOTAL") else [f for f in vps if f["clase"] == c]
        res["formas"][c] = {}
        for fo in FORMAS:
            r = cruda(fc, lambda f, fo=fo: f["forma"] == fo)
            res["formas"][c][fo] = r
            out.append(f"{c:20s} {fo:26s} {fmt(r)}")
    for fo in FORMAS:
        r = ponderada(vps, lambda f, fo=fo: f["forma"] == fo, w)
        res["formas"].setdefault("ponderada", {})[fo] = r
        out.append(f"{'ponderada':20s} {fo:26s} {fmt(r)}")
    out.append("")

    out.append("## 5. No decidibles (fuera del denominador)")
    cnd = collections.Counter(f["clase"] for f in nd)
    res["no_decidibles"] = {"total": len(nd), "por_clase": dict(cnd),
                            "unidades": [{"unidad": f["unidad"], "clase": f["clase"], "motivo": f["nota"]} for f in nd]}
    out.append(f"total {len(nd)} de {len(filas)}; por clase {dict(cnd)}")
    for f in nd:
        out.append(f"  {f['unidad']} ({f['clase']}): {f['nota']}")
    out.append("")

    out.append("## 6. Marcas de tabular / fórmula en la muestra")
    tf = collections.Counter(f["tabular_o_formula"] for f in filas)
    ct = sum(1 for f in filas if f["contenido_tabular_fuera_patron"] == "sí")
    res["marcas"] = {"tabular_o_formula": dict(tf), "contenido_tabular_fuera_patron": ct}
    out.append(f"{dict(tf)}; contenido_tabular fuera del patrón sellado: {ct}")
    for etiqueta, pred in (("tabular o fórmula", lambda f: f["tabular_o_formula"] != "no"),
                           ("ni tabular ni fórmula", lambda f: f["tabular_o_formula"] == "no")):
        r = cruda([f for f in dec if pred(f)], vp)
        out.append(f"varios puntos entre {etiqueta:22s} {fmt(r)}")

    txt = "\n".join(out) + "\n"
    (BASE / "proporciones_P1_salida.txt").write_text(txt)
    (BASE / "proporciones_P1.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
