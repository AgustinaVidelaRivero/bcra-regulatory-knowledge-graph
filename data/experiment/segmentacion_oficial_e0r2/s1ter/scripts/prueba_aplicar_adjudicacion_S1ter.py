"""U-SEG-OFICIAL, S1-ter-b2: prueba de `aplicar_adjudicacion_S1ter.py` con datos SINTÉTICOS (USD 0). No es una lectura ni
una adjudicación: las marcas las pone este script, y la salida no lleva ids.

Uso: python -B prueba_aplicar_adjudicacion_S1ter.py --s1ter <carpeta s1ter> --trabajo <directorio del scratchpad>
       --sha-orden <sha256 sellado> --sha-poblaciones-finales <sha256 sellado>

Corre el script por su línea de comandos (el mismo camino que la corrida real), con planillas de la lectora sintéticas
(todas `correcta`, armadas desde las planillas vacías de `tramo_b/`), y controla los casos del punto 7 de las
decisiones de la autora sobre el FRENO S1-ter-b. Al final, `cifras_lectura_S1ter.calcular` lee las planillas
adjudicadas.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")


def tsv(filas: list[dict], cols) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=cols, delimiter="\t", lineterminator="\n")
    w.writeheader()
    for f in filas:
        w.writerow({c: f.get(c, "") for c in cols})
    return s.getvalue()


def adj(op: str, **kw) -> dict:
    d = {c: "" for c in ADJ}
    d.update({"ficha": op, "marca": "correcta"})
    d.update(kw)
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("s1ter", "trabajo", "sha_orden", "sha_poblaciones_finales"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    s1ter, W = Path(a.s1ter), Path(a.trabajo)
    W.mkdir(parents=True, exist_ok=True)
    script = s1ter / "scripts" / "aplicar_adjudicacion_S1ter.py"
    orden_p, fin_p = s1ter / "tramo_b" / "orden_lectura_S1ter.json", s1ter / "tramo_b" / "poblaciones_finales_S1ter.json"
    orden, fin = json.loads(orden_p.read_text(encoding="utf-8")), json.loads(fin_p.read_text(encoding="utf-8"))
    # planillas de la lectora, sintéticas
    lect = {}
    for e in (1, 2):
        with open(s1ter / "tramo_b" / f"planilla_etapa_{e}_S1ter.tsv", encoding="utf-8") as fh:
            filas = list(csv.DictReader(fh, delimiter="\t"))
        cols = tuple(filas[0].keys())
        for f in filas:
            f["marca"] = "correcta"
        lect[e] = W / f"planilla_lectora_sintetica_etapa_{e}.tsv"
        lect[e].write_text(tsv(filas, cols), encoding="utf-8")
    f1, f2 = orden["etapa_1"]["fichas"], orden["etapa_2"]["fichas"]
    listas = set(fin["c116_b"]["listas"])
    L = [x["id_opaco"] for x in f2 if x["id"] in listas]
    A = [x["id_opaco"] for x in f2 if x["poblacion"] == "c116_a"]
    REG = [x["id_opaco"] for x in f2 if x["poblacion"] == "regresion"][0]
    S2 = [x["id_opaco"] for x in f2 if x["id"] == "ri_oc::S2"][0]
    SEC3 = [x["id_opaco"] for x in f2 if x["poblacion"] == "c116_b:seccion_3_ri_oc"][0]
    E1 = f1[0]["id_opaco"]
    E1b = f1[1]["id_opaco"]

    def correr(nombre: str, a1: list[dict], a2: list[dict], extra: list[str] | None = None,
               crudo1: str | None = None) -> tuple[int, Path]:
        d = W / nombre
        d.mkdir(exist_ok=True)
        (d / "adj1.tsv").write_text(crudo1 if crudo1 is not None else tsv(a1, ADJ), encoding="utf-8")
        (d / "adj2.tsv").write_text(tsv(a2, ADJ), encoding="utf-8")
        for n in ("p1.tsv", "p2.tsv", "reg.json"):
            (d / n).unlink(missing_ok=True)
        cmd = [sys.executable, "-B", str(script), "--planilla-1", str(lect[1]), "--planilla-2", str(lect[2]),
               "--orden", str(orden_p), "--sha-orden", a.sha_orden, "--poblaciones-finales", str(fin_p),
               "--sha-poblaciones-finales", a.sha_poblaciones_finales,
               "--adjudicacion-1", str(d / "adj1.tsv"), "--adjudicacion-2", str(d / "adj2.tsv"),
               "--out-planilla-1", str(d / "p1.tsv"), "--out-planilla-2", str(d / "p2.tsv"), "--out-json", str(d / "reg.json")]
        r = subprocess.run(cmd + (extra or []), capture_output=True, text=True,
                           env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"})
        return r.returncode, d

    res = []

    def chk(nombre: str, cond: bool) -> None:
        res.append((nombre, bool(cond)))

    # A: los casos del punto 7
    a2 = [adj(L[0], la_que_sigue="error", clase_que_sigue="corte", subclase_que_sigue="empieza_fuera"),
          adj(L[1], la_que_sigue="error", clase_que_sigue="limpieza", subclase_que_sigue="restos_pie"),
          adj(L[2], marca="error", clase="limpieza", subclase="restos_encabezado", la_que_sigue="error",
              clase_que_sigue="corte", subclase_que_sigue="termina_fuera"),
          adj(A[0], la_que_sigue="error", clase_que_sigue="corte", subclase_que_sigue="empieza_fuera"),
          adj(REG, la_que_sigue="error", clase_que_sigue="corte", subclase_que_sigue="empieza_fuera"),
          adj(S2, la_que_sigue="error", clase_que_sigue="corte", subclase_que_sigue="empieza_fuera"),
          adj(SEC3, la_que_sigue="error", clase_que_sigue="corte", subclase_que_sigue="empieza_fuera", herencia="error"),
          adj(A[1], herencia="error")]
    a1 = [adj(E1, marca="error", clase="corte", subclase="falta_texto_propio", nota="nota sintética de la autora"),
          adj(E1b, herencia="error")]
    rc, d = correr("A_casos", a1, a2)
    chk("A corre (rc 0)", rc == 0)
    p1 = {f["ficha"]: f for f in csv.DictReader(open(d / "p1.tsv", encoding="utf-8"), delimiter="\t")}
    p2 = {f["ficha"]: f for f in csv.DictReader(open(d / "p2.tsv", encoding="utf-8"), delimiter="\t")}
    reg = json.loads((d / "reg.json").read_text(encoding="utf-8"))
    cier = {x["ficha"]: x for x in reg["cierres_confirmados"]}
    her = {x["ficha"]: x for x in reg["herencias_confirmadas"]}
    chk("cierre con error de corte en una lista de (b): la fila queda error de corte",
        (p2[L[0]]["marca"], p2[L[0]]["clase"], p2[L[0]]["subclase"]) == ("error", "corte", "empieza_fuera"))
    chk("  … cuenta y revierte", cier[L[0]]["cuenta"] and cier[L[0]]["revierte_por_lista"])
    chk("cierre con error de limpieza en una lista de (b): la fila queda error de limpieza",
        (p2[L[1]]["marca"], p2[L[1]]["clase"], p2[L[1]]["subclase"]) == ("error", "limpieza", "restos_pie"))
    chk("  … cuenta y no revierte", cier[L[1]]["cuenta"] and not cier[L[1]]["revierte_por_lista"])
    chk("fila con error de limpieza y cierre con error de corte: queda corte (la limpieza pasa a su columna)",
        (p2[L[2]]["clase"], p2[L[2]]["subclase"], p2[L[2]]["limpieza"]) == ("corte", "termina_fuera", "restos_encabezado"))
    chk("  … el JSON registra las dos clases y revierte",
        cier[L[2]]["clase_de_la_fila_de_la_autora"] == "limpieza" and cier[L[2]]["clase_que_sigue"] == "corte"
        and cier[L[2]]["revierte_por_lista"])
    for nombre, op in (("(a)", A[0]), ("regresión", REG), ("ri_oc::S2", S2), ("sección 3 de ri_oc", SEC3)):
        chk(f"error confirmado en la unidad que sigue en una ficha de {nombre}: no cuenta y la fila no cambia",
            not cier[op]["cuenta"] and not cier[op]["revierte_por_lista"] and p2[op]["marca"] == "correcta")
    chk("herencia confirmada en la unidad de la sección 3: cuenta como falla de la corrección y la marca no cambia",
        her[SEC3]["cuenta_como_falla_de_la_correccion_de_ri_oc"] and p2[SEC3]["marca"] == "correcta")
    chk("herencia confirmada en otra ficha (etapa 2): se registra y no cuenta",
        not her[A[1]]["cuenta_como_falla_de_la_correccion_de_ri_oc"] and p2[A[1]]["marca"] == "correcta")
    chk("herencia confirmada en una ficha de la etapa 1: se registra y no cuenta",
        not her[E1b]["cuenta_como_falla_de_la_correccion_de_ri_oc"] and p1[E1b]["marca"] == "correcta")
    chk("la marca de la autora reemplaza a la de la lectora (y su nota queda)",
        (p1[E1]["marca"], p1[E1]["clase"], p1[E1]["subclase"], p1[E1]["nota"])
        == ("error", "corte", "falta_texto_propio", "nota sintética de la autora"))
    sin_adj = [k for k in p2 if k not in {x["ficha"] for x in a2}]
    lect2 = {f["ficha"]: f for f in csv.DictReader(open(lect[2], encoding="utf-8"), delimiter="\t")}
    chk("las fichas sin adjudicar quedan como las dejó la lectora", all(p2[k] == lect2[k] for k in sin_adj))
    sys.path.insert(0, str(s1ter / "scripts"))
    import cifras_lectura_S1ter as C
    lim = json.loads((s1ter / "poblaciones_S1ter.json").read_text(encoding="utf-8"))["cortes"]["limites_declarados"]["unidades"]
    r = C.calcular(orden, fin, lim, list(p1.values()), list(p2.values()))
    chk("cifras_lectura_S1ter lee las planillas adjudicadas, sin cambios", r["planillas_validas"])
    # B: sin adjudicación
    rc, d = correr("B_sin_adjudicacion", [], [])
    chk("sin adjudicación, las planillas quedan byte a byte iguales a las de la lectora",
        rc == 0 and (d / "p1.tsv").read_bytes() == lect[1].read_bytes() and (d / "p2.tsv").read_bytes() == lect[2].read_bytes())
    # C: mal formados
    malos = {"columnas equivocadas": ("C1", None, "ficha\tmarca\n" + f"{E1}\tcorrecta\n", None),
             "ficha desconocida": ("C2", [adj("E9-999")], None, None),
             "la_que_sigue con otro valor": ("C3", None, None, [adj(L[0], la_que_sigue="quizas")]),
             "la_que_sigue en la etapa 1": ("C4", [adj(E1, la_que_sigue="error", clase_que_sigue="corte",
                                                     subclase_que_sigue="empieza_fuera")], None, None),
             "ficha repetida": ("C5", [adj(E1), adj(E1)], None, None),
             "clase de la que sigue sin error": ("C6", None, None, [adj(L[0], clase_que_sigue="corte")]),
             "marca de la autora no válida": ("C7", [adj(E1, marca="error")], None, None)}
    for nombre, (dn, x1, crudo, x2) in malos.items():
        rc, d = correr(dn, x1 or [], x2 or [], crudo1=crudo)
        chk(f"mal formado ({nombre}): se rechaza sin escribir nada",
            rc != 0 and not any((d / n).exists() for n in ("p1.tsv", "p2.tsv", "reg.json")))
    rc, d = correr("C8", [], [], extra=["--sha-planilla-1", "0" * 64])
    chk("mal formado (planilla que no da su sha256): se rechaza sin escribir nada",
        rc != 0 and not any((d / n).exists() for n in ("p1.tsv", "p2.tsv", "reg.json")))
    for n, ok in res:
        print(("ok    " if ok else "FALLA ") + n)
    print(f"{sum(ok for _, ok in res)} de {len(res)} controles ok")
    sys.exit(0 if all(ok for _, ok in res) else 1)


if __name__ == "__main__":
    main()
