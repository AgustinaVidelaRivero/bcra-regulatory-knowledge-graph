"""
cifras_cob_t.py — U-COB-T, punto 6: la presencia con la regla del 5.6 y las cifras del §6 del documento firmado, desde la
hoja de la autora sellada. USD 0, sin API. No muestra ningún texto: solo refs, veredictos y cuentas.

  - el código es el del sello del código (sellar_hoja_cob_t.controlar_codigo) y la hoja da su sello;
  - la hoja se vuelve a controlar como al sellarla (sellar_hoja_cob_t.controlar: lo nombrado existe en el subgrafo);
  - la regla del 5.6, la de V (cob_v.presencia_regla) sin la marca de adjudicación, que la hoja de la autora no tiene:
      presente = los tres componentes expresados;
      parcial  = sujeto y objeto expresados con el predicado parcial, o dos expresados y uno parcial;
      ausente  = el resto;
  - §6: de las 30 sorteadas salen las descartadas en la extracción (las que no tienen fila); de las filas, las «no
    decidible» van al lado; las decididas son las otras.
      cruda     = presentes / decididas, con Wilson al 95 % (z = 1,959964); las parciales aparte, con su proporción;
      depurada  = sin las que la autora marcó incorrectas según el fragmento (errores del gold, 5.8): presentes /
                  (decididas − incorrectas), con Wilson; las parciales aparte;
      al lado   = las descartadas en la extracción, por causa, y las no decidibles, cada una con su cuenta;
      declarado = medición humana sobre 30, sin la cifra del juez (D-9); no corren los 600 ni el ranking.
Escribe --lectura/cifras_cob_t.json.
  python3 -I -B cifras_cob_t.py [--lectura L] [--salidas S]
  python3 -I -B cifras_cob_t.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_cob_t as T  # noqa: E402
import sellar_hoja_cob_t as S  # noqa: E402

K = T.importar_v(("comun_cob", "subgrafos_cob", "cob_v"))["cob_v"]
Z95 = 1.959964
SALIDA = "cifras_cob_t.json"
DECLARADO = ("Medición humana sobre 30 (la presencia que decide la autora en el control de 30), sin la cifra del juez "
             "(D-9); no corren los 600 fragmentos, el puntaje de importancia, la calibración del orden, el juez de "
             "presencia ni el recall@k (§1 del documento firmado).")


def wilson(x: int, n: int, z: float = Z95) -> list | None:
    if n == 0:
        return None
    p = x / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - m) / d, (c + m) / d]


def veredicto(fila: dict) -> str:
    return K.presencia_regla({c: fila["componentes"][c]["valor"] for c in S.COMPONENTES}, False)


def proporcion(x: int, n: int) -> dict:
    return {"x": x, "n": n, "proporcion": (x / n) if n else None, "wilson95": wilson(x, n)}


def cifras(filas: list[dict], descartadas: dict, n_sorteadas: int) -> dict:
    if len(filas) + len(descartadas) != n_sorteadas:
        raise SystemExit("FRENO: las filas y las descartadas no suman las sorteadas")
    ver = {f["ref"]: veredicto(f) for f in filas}
    no_dec = [f["ref"] for f in filas if f["correcta"] == "no_decidible"]
    decididas = [f for f in filas if f["correcta"] != "no_decidible"]
    incorrectas = [f["ref"] for f in decididas if f["correcta"] == "no"]
    depuradas = [f for f in decididas if f["correcta"] == "si"]

    def bloque(fs: list[dict]) -> dict:
        c = Counter(ver[f["ref"]] for f in fs)
        return {"presentes": proporcion(c["presente"], len(fs)), "parciales_aparte": proporcion(c["parcial"], len(fs)),
                "ausentes": c["ausente"], "n": len(fs)}

    return {"n_sorteadas": n_sorteadas,
            "descartadas_en_la_extraccion": {"n": len(descartadas), "por_causa": dict(Counter(descartadas.values())),
                                             "refs": sorted(descartadas)},
            "filas_de_la_hoja": len(filas),
            "no_decidibles": {"n": len(no_dec), "refs": no_dec},
            "decididas": len(decididas),
            "incorrectas_errores_del_gold": {"n": len(incorrectas), "refs": incorrectas},
            "cruda": bloque(decididas), "depurada": bloque(depuradas),
            "por_ref": {f["ref"]: {"veredicto": ver[f["ref"]], "correcta": f["correcta"],
                                   "componentes": {c: f["componentes"][c]["valor"] for c in S.COMPONENTES}}
                        for f in filas},
            "regla": "presente = los tres expresados; parcial = sujeto y objeto expresados con el predicado parcial, o dos "
                     "expresados y uno parcial; ausente = el resto (5.6; cob_v.presencia_regla)",
            "intervalo": f"Wilson al 95 % (z = {Z95})", "declarado": DECLARADO}


def calcular(lectura: Path, salidas: Path | None, acta_sha256: str | None = None, consola=print) -> dict:
    codigo = S.controlar_codigo(lectura)
    s_hoja = S.verificar_sello(lectura)
    acta = acta_sha256 or S.acta_sellada(salidas)
    esp, s_esp = S.cargar_esperado(lectura, salidas)
    prob, _, filas = S.controlar(S.leer_hoja(Path(lectura) / S.H.ARCHIVOS["hoja"]), esp, s_esp, acta)
    if prob:
        raise SystemExit(f"FRENO: la hoja sellada no pasa los controles: {prob}")
    out = cifras(filas, esp["descartadas_en_la_extraccion"], esp["n_sorteadas"])
    out.update({"hora": T.hora(), "hoja_sha256": s_hoja, "esperado_sha256": s_esp, "acta_sorteo_cob_t.json_sha256": acta,
                "codigo_sha256": codigo})
    s = T.escribir_json(Path(lectura) / SALIDA, out)
    for nombre in ("cruda", "depurada"):
        b = out[nombre]
        p, q = b["presentes"], b["parciales_aparte"]
        w = ", ".join(f"{x:.4f}" for x in p["wilson95"]) if p["wilson95"] else "—"
        consola(f"{nombre}: presentes {p['x']}/{p['n']} (Wilson 95 %: {w}); parciales aparte {q['x']}/{q['n']}; "
                f"ausentes {b['ausentes']}")
    consola(f"al lado: descartadas en la extracción {out['descartadas_en_la_extraccion']['n']} "
            f"{out['descartadas_en_la_extraccion']['por_causa']}; no decidibles {out['no_decidibles']['n']}; "
            f"incorrectas (errores del gold) {out['incorrectas_errores_del_gold']['n']}")
    consola(f"{SALIDA}: {s}")
    return out


# --------------------------------------------------------------------------- #
# Selftest                                                                     #
# --------------------------------------------------------------------------- #
def regla_del_texto(s: str, p: str, o: str) -> str:
    """La regla del 5.6 escrita de nuevo, a partir de su texto, para contrastar con cob_v.presencia_regla."""
    vs = [s, p, o]
    if vs.count("expresado") == 3:
        return "presente"
    if (s == "expresado" and o == "expresado" and p == "parcial") or (vs.count("expresado") == 2 and vs.count("parcial") == 1):
        return "parcial"
    return "ausente"


def fila(ref: str, s: str, p: str, o: str, correcta: str) -> dict:
    return {"ref": ref, "orden": 0, "correcta": correcta,
            "componentes": {"sujeto": {"valor": s, "nombrados": []}, "predicado": {"valor": p, "nombrados": []},
                            "objeto": {"valor": o, "nombrados": []}}}


def selftest(base: Path = T.RAIZ / "seco" / "selftest_cifras") -> bool:
    res = {}
    combos = list(itertools.product(S.VALORES, repeat=3))
    res["regla_27_combinaciones_igual_al_texto"] = all(
        veredicto(fila("x", s, p, o, "si")) == regla_del_texto(s, p, o) for s, p, o in combos)
    res["regla_cuenta"] = Counter(regla_del_texto(*c) for c in combos) == Counter(
        {"presente": 1, "parcial": 3, "ausente": 23})
    res["wilson_84_de_100"] = round(wilson(84, 100)[0], 4) == 0.7558
    res["wilson_26_de_30"] = round(wilson(26, 30)[0], 4) == 0.7032
    res["wilson_n_0"] = wilson(0, 0) is None
    E, P, A = S.VALORES
    fs = ([fila(f"CT{i:02d}", E, E, E, "si") for i in range(1, 11)]                  # 10 presentes correctas
          + [fila("CT11", E, E, E, "no"), fila("CT12", E, E, E, "no")]              # 2 presentes incorrectas
          + [fila("CT13", E, P, E, "si"), fila("CT14", P, E, E, "si")]              # 2 parciales
          + [fila(f"CT{i:02d}", A, E, E, "si") for i in range(15, 25)]              # 10 ausentes
          + [fila("CT25", E, E, E, "no_decidible"), fila("CT26", A, A, A, "no")])   # 1 no decidible, 1 ausente incorrecta
    desc = {"CT27": "no", "CT28": "en_heredado", "CT29": "sin_salida", "CT30": "no"}
    c = cifras(fs, desc, 30)
    res["denominadores"] = (c["filas_de_la_hoja"], c["decididas"], c["no_decidibles"]["n"],
                            c["incorrectas_errores_del_gold"]["n"], c["descartadas_en_la_extraccion"]["n"]) == (26, 25, 1, 3, 4)
    res["cruda"] = (c["cruda"]["presentes"]["x"], c["cruda"]["presentes"]["n"], c["cruda"]["parciales_aparte"]["x"],
                    c["cruda"]["ausentes"]) == (12, 25, 2, 11)
    res["depurada"] = (c["depurada"]["presentes"]["x"], c["depurada"]["presentes"]["n"],
                       c["depurada"]["parciales_aparte"]["x"], c["depurada"]["ausentes"]) == (10, 22, 2, 10)
    res["descartadas_por_causa"] = c["descartadas_en_la_extraccion"]["por_causa"] == {"no": 2, "en_heredado": 1,
                                                                                      "sin_salida": 1}
    try:
        cifras(fs, {}, 30)
        res["no_suman_30_frena"] = False
    except SystemExit:
        res["no_suman_30_frena"] = True
    # de punta a punta, con una hoja sellada por el sellador
    d = base / "lectura"
    S.escribir_prueba(d, S.FILAS_BUENAS, S.ESPERADO_PRUEBA, S.ACTA_PRUEBA)
    S.sellar(d, None, S.ACTA_PRUEBA, consola=lambda s: None)
    out = calcular(d, None, S.ACTA_PRUEBA, consola=lambda s: None)
    res["de_punta_a_punta"] = (out["por_ref"]["CT01"]["veredicto"] == "parcial" and out["no_decidibles"]["n"] == 1
                               and out["decididas"] == 1 and out["cruda"]["presentes"]["x"] == 0
                               and out["descartadas_en_la_extraccion"]["n"] == 1 and (d / SALIDA).exists())
    with open(d / S.H.ARCHIVOS["hoja"], "a", encoding="utf-8") as fh:
        fh.write("\n")
    try:
        calcular(d, None, S.ACTA_PRUEBA, consola=lambda s: None)
        res["hoja_cambiada_despues_del_sello_frena"] = False
    except SystemExit:
        res["hoja_cambiada_despues_del_sello_frena"] = True
    shutil.rmtree(base)
    ok = all(res.values())
    for k, v in res.items():
        print(f"  {k}: {v}")
    print("selftest cifras:", "OK" if ok else "MAL", f"({sum(res.values())} de {len(res)})")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lectura", type=Path, default=T.LECTURA)
    ap.add_argument("--salidas", type=Path, default=T.SALIDAS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return 0 if selftest() else 2
    calcular(a.lectura, a.salidas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
