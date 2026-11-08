"""
cifras_600_cob_t.py — U-COB-T, vueltas b y c, punto 8: las cifras de la lectura de la autora, desde la hoja de importancia y la de
presencia, selladas, y el orden sellado del puntaje. USD 0, sin API. Imprime solo cuentas.

  - el orden (5.5; nota v3, punto 10), de la hoja de importancia: pasa si al menos 80 de las 100 primeras son esenciales o útiles
    y esa proporción supera a la de las 30 de control;
  - el recall@10, @50 y @100 (5.7; nota, punto 11), de la hoja de presencia, en las 100 primeras por su posición: presentes / k
    con Wilson al 95 % (z = 1,959964), las parciales aparte; crudo, y depurado (segunda nota, punto 4): sale del denominador SOLO
    una ausente de las 100 que la autora marca «no» según el pasaje (error del gold, 5.8), y se cuenta; las «no decidible» quedan
    y se cuentan. La presencia, con la regla del 5.6 (cob_v.presencia_regla);
  - si el orden no pasa, el recall sobre las que la autora marcó esenciales, sin el orden, crudo y depurado;
  - D-9 sobre las 30 (nota, punto 12): cifras_cob_t.cifras de la vuelta a, sin editarla, con los renglones de D-9 de la hoja de
    presencia.
  python3 -I -B cifras_600_cob_t.py [--lectura L] [--corridas C] [--salidas S]
  python3 -I -B cifras_600_cob_t.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_cob_t as T  # noqa: E402
import comun_600_cob_t as M  # noqa: E402
import cifras_cob_t as C0  # noqa: E402
import sellar_hojas_600_cob_t as SH  # noqa: E402

KS = (10, 50, 100)
ORDEN = "orden_cob_t.json"
SALIDA = "cifras_600_cob_t.json"


def error_del_gold(f: dict) -> bool:
    return f["veredicto"] == "ausente" and f.get("correcta") == "no"


def bloque(filas: list[dict], n: int | None = None) -> dict:
    """presentes / n y parciales aparte, crudo (n = las filas o el k pedido) y depurado (sin las ausentes marcadas «no»)."""
    n = len(filas) if n is None else n
    gold = [f for f in filas if error_del_gold(f)]
    c = Counter(f["veredicto"] for f in filas)
    nd = n - len(gold)
    return {"crudo": {"presentes": C0.proporcion(c["presente"], n), "parciales_aparte": C0.proporcion(c["parcial"], n),
                      "ausentes": c["ausente"]},
            "depurado": {"presentes": C0.proporcion(c["presente"], nd), "parciales_aparte": C0.proporcion(c["parcial"], nd),
                         "ausentes": c["ausente"] - len(gold)},
            "ausentes_incorrectas_errores_del_gold": len(gold),
            "no_decidibles": sum(f.get("correcta") == "no_decidible" for f in filas)}


def cifras(imp: list[dict], pres: list[dict], esp_pres: dict, orden: dict) -> dict:
    """imp: los renglones de la hoja de importancia sellada (ref S###); pres: los de la de presencia (ref CT## o S###, con sus
    refs); orden: {posiciones: ref S -> posición, primeras, control}."""
    importancia = {f["ref"]: f["importancia"] for f in imp}
    por_ref = {r: f for f in pres for r in f["refs"]}
    prim = sorted(orden["primeras"], key=lambda r: orden["posiciones"][r])
    f_prim = [por_ref[r] for r in prim]
    eu = lambda refs: sum(importancia[r] in ("esencial", "util") for r in refs)  # noqa: E731
    e100, e30 = eu(prim), eu(orden["control"])
    p100 = e100 / len(prim) if prim else 0.0
    p30 = e30 / len(orden["control"]) if orden["control"] else 0.0
    pasa = e100 >= 80 and p100 > p30
    out = {"orden": {"primeras": len(prim), "esenciales_o_utiles_en_las_primeras": e100, "control": len(orden["control"]),
                     "esenciales_o_utiles_en_el_control": e30, "proporcion_primeras": p100, "proporcion_control": p30,
                     "pasa": pasa, "regla": "al menos 80 de las 100 esenciales o útiles, y más que en las 30 de control (5.5)"},
           "recall": {f"@{k}": {"k": k, "posiciones": f"1 a {min(k, len(f_prim))}",
                                **bloque(f_prim[:k], min(k, len(f_prim)))} for k in KS},
           "importancia_de_las_primeras": dict(Counter(importancia[r] for r in prim)),
           "importancia_del_control": dict(Counter(importancia[r] for r in orden["control"]))}
    if not pasa:
        es = [por_ref[r] for r in prim if importancia[r] == "esencial"]
        out["recall_sobre_las_esenciales_sin_orden"] = {"n": len(es), **bloque(es)}
    d9 = [f for f in pres if "d9" in f["grupos"]]
    out["d9"] = C0.cifras([{"ref": f["ref"], "orden": f["renglon"], "correcta": f["correcta"],
                            "componentes": f["componentes"]} for f in d9],
                          esp_pres["d9"]["descartadas_en_la_extraccion"], esp_pres["d9"]["n_sorteadas"])
    out["declarado"] = ("El recall sale de la lectura de la autora (nota v3, puntos 3 y 11; segunda nota, punto 4); D-9 va como "
                        "la red (punto 12). " + C0.DECLARADO.split(";")[0] + ".")
    return out


def cargar_orden(corridas: Path) -> tuple[dict, str]:
    p = Path(corridas) / "puntaje" / ORDEN
    s = M.verificar_sello(p)
    return json.loads(p.read_text(encoding="utf-8")), s


def calcular(lectura: Path, corridas: Path, dir_acta: Path | None, consola=print) -> dict:
    _, imp, s_imp = SH.leer_sellada(lectura, "importancia", dir_acta)
    esp_p, pres, s_pres = SH.leer_sellada(lectura, "presencia", dir_acta)
    orden, s_orden = cargar_orden(corridas)
    out = cifras(imp, pres, esp_p, orden) | {"hora": T.hora(), "hoja_importancia_sha256": s_imp,
                                             "hoja_presencia_sha256": s_pres, "orden_sha256": s_orden}
    s = T.escribir_json(Path(lectura) / SALIDA, out)
    o = out["orden"]
    consola(f"orden: {o['esenciales_o_utiles_en_las_primeras']}/{o['primeras']} esenciales o útiles frente a "
            f"{o['esenciales_o_utiles_en_el_control']}/{o['control']} en el control: pasa {o['pasa']}")
    for k, b in out["recall"].items():
        consola(f"recall{k}: crudo {b['crudo']['presentes']['x']}/{b['crudo']['presentes']['n']}, parciales "
                f"{b['crudo']['parciales_aparte']['x']}; depurado {b['depurado']['presentes']['x']}/"
                f"{b['depurado']['presentes']['n']} (ausentes incorrectas {b['ausentes_incorrectas_errores_del_gold']}, "
                f"no decidibles {b['no_decidibles']})")
    d = out["d9"]["cruda"]["presentes"]
    consola(f"D-9: presentes {d['x']}/{d['n']} (descartadas {out['d9']['descartadas_en_la_extraccion']['n']}); {SALIDA}: {s}")
    return out


# --------------------------------------------------------------------------- #
# Selftest (valores calculados a mano)                                        #
# --------------------------------------------------------------------------- #
def _f(ref, refs, grupos, ver, cor=None):
    vals = {"presente": ("expresado",) * 3, "parcial": ("expresado", "parcial", "expresado"),
            "ausente": ("ausente", "ausente", "expresado")}
    return {"ref": ref, "refs": refs, "unidad": ref, "grupos": grupos, "renglon": 0, "veredicto": ver, "correcta": cor,
            "componentes": {c: {"valor": v, "nombrados": []} for c, v in zip(SH.COMPONENTES, vals[ver])}}


def selftest() -> bool:
    res = {}
    # 100 primeras: posiciones 1-10, 7 presentes (la 1 marcada «no»: no sale), 2 parciales, 1 ausente marcada «no» (sale);
    # 11-50: 20 presentes, 10 parciales, 10 ausentes (la 41 y la 42, «no»: salen); 51-100: 10 presentes, 40 ausentes (la 61,
    # «no decidible»: queda). Importancia: 85 esenciales o útiles (80 esenciales, 5 útiles); control: 20 de 30.
    ver = (["presente"] * 7 + ["parcial"] * 2 + ["ausente"]
           + ["presente"] * 20 + ["parcial"] * 10 + ["ausente"] * 10 + ["presente"] * 10 + ["ausente"] * 40)
    cor = [None] * 100
    cor[0], cor[9], cor[40], cor[41], cor[60] = "no", "no", "no", "no", "no_decidible"
    imp_v = ["esencial"] * 80 + ["util"] * 5 + ["accesoria"] * 15
    pres = [_f(f"S{i + 1:03d}", [f"S{i + 1:03d}"], ["primeras"], ver[i], cor[i]) for i in range(100)]
    imp = [{"ref": f"S{i + 1:03d}", "importancia": imp_v[i]} for i in range(100)]
    control = [f"S{101 + i * 3:03d}" for i in range(30)]
    imp += [{"ref": r, "importancia": "esencial" if i < 20 else "accesoria"} for i, r in enumerate(control)]
    pres += [_f(f"CT{i + 1:02d}", [f"CT{i + 1:02d}"], ["d9"], ["presente", "parcial", "ausente"][i], "si") for i in range(3)]
    esp = {"d9": {"n_sorteadas": 4, "descartadas_en_la_extraccion": {"CT04": "no"}}}
    orden = {"posiciones": {f"S{i + 1:03d}": i + 1 for i in range(100)}, "primeras": [f"S{i + 1:03d}" for i in range(100)],
             "control": control}
    c = cifras(imp, pres, esp, orden)
    r10, r50, r100 = c["recall"]["@10"], c["recall"]["@50"], c["recall"]["@100"]
    res["orden_85_frente_a_20_de_30_pasa"] = (c["orden"]["esenciales_o_utiles_en_las_primeras"] == 85
                                              and c["orden"]["esenciales_o_utiles_en_el_control"] == 20 and c["orden"]["pasa"])
    res["recall_10_crudo_7_de_10_depurado_7_de_9_la_presente_no_no_sale"] = (
        (r10["crudo"]["presentes"]["x"], r10["crudo"]["presentes"]["n"], r10["depurado"]["presentes"]["x"],
         r10["depurado"]["presentes"]["n"], r10["ausentes_incorrectas_errores_del_gold"]) == (7, 10, 7, 9, 1))
    res["recall_50_crudo_27_de_50_depurado_27_de_47"] = (
        (r50["crudo"]["presentes"]["x"], r50["crudo"]["presentes"]["n"], r50["crudo"]["parciales_aparte"]["x"],
         r50["depurado"]["presentes"]["x"], r50["depurado"]["presentes"]["n"]) == (27, 50, 12, 27, 47))
    res["recall_100_depurado_37_de_97_y_la_no_decidible_queda"] = (
        (r100["crudo"]["presentes"]["x"], r100["depurado"]["presentes"]["n"], r100["no_decidibles"],
         r100["ausentes_incorrectas_errores_del_gold"], r100["depurado"]["ausentes"]) == (37, 97, 1, 3, 48))
    res["wilson_7_de_9"] = [round(x, 4) for x in r10["depurado"]["presentes"]["wilson95"]] == [0.4526, 0.9368]
    res["d9_con_cifras_de_la_vuelta_a"] = (c["d9"]["cruda"]["presentes"]["x"], c["d9"]["cruda"]["presentes"]["n"],
                                           c["d9"]["descartadas_en_la_extraccion"]["n"]) == (1, 3, 1)
    for r in ("S080", "S081", "S082", "S083", "S084", "S085"):
        next(x for x in imp if x["ref"] == r)["importancia"] = "accesoria"
    c2 = cifras(imp, pres, esp, orden)
    es = c2["recall_sobre_las_esenciales_sin_orden"]
    res["orden_79_no_pasa_y_recall_sobre_las_esenciales"] = (not c2["orden"]["pasa"] and es["n"] == 79
                                                            and es["crudo"]["presentes"]["x"] == 37
                                                            and es["depurado"]["presentes"]["n"] == 76)
    ok = all(res.values())
    for k, v in res.items():
        print(f"  {k}: {v}")
    print("selftest cifras de la vuelta c:", "OK" if ok else "MAL", f"({sum(res.values())} de {len(res)})")
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lectura", type=Path, default=T.LECTURA)
    ap.add_argument("--corridas", type=Path, default=T.CORRIDAS)
    ap.add_argument("--salidas", type=Path, default=T.SALIDAS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if selftest() else 2
    calcular(a.lectura, a.corridas, a.salidas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
