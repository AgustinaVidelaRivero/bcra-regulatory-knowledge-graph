"""U-SEG-OFICIAL, S1-quater: prueba de los scripts de cierre de la adjudicación (mesa, 13/10/2026; USD 0), con datos sintéticos: no
usa nada de la lectura de S1-quater ni de S1-ter. Corre cada script como lo correrá la mesa (`python3 -B <script>`, en otro proceso) y
recalcula por su cuenta lo que tiene que dar. La salida trae solo «ok» o «MAL» por caso.

Uso: python3 -B prueba_cierre_S1quater.py --scripts <carpeta con los cuatro scripts> --trabajo <carpeta nueva>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import subprocess
import sys
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
COLS = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
LEC = COLS[2:]
CORTE = ["empieza_fuera", "termina_fuera", "falta_texto_propio", "trae_texto_de_otro_punto", "numero_equivocado"]
LIMP = ["restos_encabezado", "restos_pie"]
res: list[tuple[bool, str]] = []


def ok(c, d):
    res.append((bool(c), d))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tsv_csv(filas, cols) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(cols), delimiter="\t", lineterminator="\n")
    w.writeheader()
    for f in filas:
        w.writerow({c: f.get(c, "") for c in cols})
    return s.getvalue()


def tsv_plano(filas, cols) -> str:
    return "\n".join(["\t".join(cols)] + ["\t".join(f.get(c, "") for c in cols) for f in filas]) + "\n"


def leer(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def correr(script: Path, args: list) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(script)] + [str(x) for x in args], capture_output=True, text=True)


def marca_al_azar(rng: random.Random, con_nota: bool = False) -> dict:
    m = rng.choices(["correcta", "error", "dudosa"], [70, 22, 8])[0]
    f = {"marca": m, "clase": "", "subclase": "", "subclase_adicional": "", "limpieza": "", "nota": ""}
    if m == "error":
        if rng.random() < 0.75:
            f.update(clase="corte", subclase=rng.choice(CORTE))
        else:
            f.update(clase="limpieza", subclase=rng.choice(LIMP))
    if con_nota and rng.random() < 0.15:
        f["nota"] = rng.choice(['dice "otra cosa"', "ver la página", "corta antes"])
    return f


def wilson_inf(k, n):
    z = 1.959963984540054
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    a = ap.parse_args()
    S, T = a.scripts, a.trabajo
    if T.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    T.mkdir(parents=True)
    P2S, ACU, APL, CIF = (S / n for n in ("pasada_2_S1quater.py", "acuerdo_etapa_1_S1quater.py", "aplicar_adjudicacion_S1quater.py",
                                          "cifras_lectura_S1quater.py"))
    rng = random.Random("prueba-cierre-S1quater")
    # --- datos sintéticos
    estr = ["vigente"] * 40 + ["marcadores"] * 10 + ["sin_raiz"] * 40
    rng.shuffle(estr)
    e1 = [{"id_opaco": f"E1-{k:03d}", "id": f"doc{k % 7}::{k}.1", "poblacion": "cortes", "estrato": estr[k - 1]} for k in range(1, 91)]
    e1[4]["id"] = "ctacte::9.9"   # un TO de la tanda 0, para el reporte aparte
    e2 = [{"id_opaco": f"E2-{k:03d}", "id": f"reg{k}::1", "poblacion": "regresion", "unidades_calificadas": [f"reg{k}::1"]}
          for k in range(1, 13)]
    orden = {"etapa_1": {"fichas": e1}, "etapa_2": {"fichas": e2}}
    (T / "orden.json").write_text(json.dumps(orden), encoding="utf-8")
    pob = {"cortes": {"vigente": {"peso": 0.55}, "marcadores": {"peso": 0.05}, "sin_raiz": {"peso": 0.40}}, "cortes_total": 1}
    (T / "pob.json").write_text(json.dumps(pob), encoding="utf-8")
    lim = {"cortes": {"limites_declarados": {"unidades": [{"id": e1[9]["id"], "fuentes": ["sintética"]},
                                                         {"id": "fuera::1", "fuentes": ["sintética"]}]}}}
    (T / "lim.json").write_text(json.dumps(lim), encoding="utf-8")
    lec = {1: [{"ficha": f["id_opaco"], "paginas": "1"} | marca_al_azar(rng, True) for f in e1],
           2: [{"ficha": f["id_opaco"], "paginas": "2"} | marca_al_azar(rng, True) for f in e2]}
    for n in (1, 2):
        (T / f"planilla_{n}.tsv").write_text(tsv_csv(lec[n], COLS), encoding="utf-8")
    p1 = {}
    for n in (1, 2):
        filas = []
        for f in lec[n]:
            g = {"ficha": f["ficha"]} | ({k: f[k] for k in LEC[:-1]} if rng.random() < 0.8 else
                                         {k: v for k, v in marca_al_azar(rng).items() if k != "nota"})
            g |= {"la_que_sigue": "", "clase_que_sigue": "", "subclase_que_sigue": "", "herencia": "", "nota": ""}
            if n == 2 and rng.random() < 0.25:
                g |= {"la_que_sigue": "error", "clase_que_sigue": "corte", "subclase_que_sigue": "empieza_fuera"}
            if n == 2 and rng.random() < 0.15:
                g["herencia"] = "error"
            filas.append(g)
        rng.shuffle(filas)   # la pasada 1 va en otro orden que la planilla
        p1[n] = filas
        (T / f"p1_{n}.tsv").write_text(tsv_plano(filas, ADJ), encoding="utf-8")
    sh = {k: sha(T / k) for k in ("p1_1.tsv", "p1_2.tsv", "planilla_1.tsv", "planilla_2.tsv", "orden.json", "pob.json", "lim.json")}
    base = ["--pasada-1-1", T / "p1_1.tsv", "--sha-pasada-1-1", sh["p1_1.tsv"], "--pasada-1-2", T / "p1_2.tsv",
            "--sha-pasada-1-2", sh["p1_2.tsv"], "--planilla-1", T / "planilla_1.tsv", "--sha-planilla-1", sh["planilla_1.tsv"],
            "--planilla-2", T / "planilla_2.tsv", "--sha-planilla-2", sh["planilla_2.tsv"]]

    # --- 1. seleccionar
    r = correr(P2S, ["seleccionar"] + base + ["--out", T / "sel"])
    ok(r.returncode == 0, "seleccionar: corre")
    esperada = {}
    for n in (1, 2):
        lp = {f["ficha"]: f for f in lec[n]}
        esperada[n] = [f["ficha"] for f in p1[n] if f["marca"] != lp[f["ficha"]]["marca"]
                       or (f["marca"] == "error" == lp[f["ficha"]]["marca"] and f["clase"] != lp[f["ficha"]]["clase"])
                       or lp[f["ficha"]]["nota"].strip() or (n == 2 and "error" in (f["la_que_sigue"], f["herencia"]))]
        txt = (T / "sel" / f"adjudicacion_pasada_2_etapa_{n}.tsv").read_text(encoding="utf-8")
        reng = txt[:-1].split("\n")
        ok([x.split("\t")[0] for x in reng[1:]] == esperada[n] and len(esperada[n]) > 0,
           f"seleccionar, etapa {n}: las fichas de la regla a–d, recalculadas aparte, en el orden de la pasada 1")
        ok(reng[0].split("\t") == list(ADJ) + [f"lectora_{c}" for c in LEC] and all(len(x.split("\t")) == 17 for x in reng),
           f"seleccionar, etapa {n}: encabezado y 17 columnas por renglón, sin comillas agregadas")
    ok(any('"otra cosa"' in (T / "sel" / f"adjudicacion_pasada_2_etapa_{n}.tsv").read_text(encoding="utf-8") for n in (1, 2)),
       "seleccionar: una nota de la lectora con comillas pasa tal cual, sin comillas de csv")

    # --- 2. la pasada 2 de la autora y armar
    p2 = {}
    for n in (1, 2):
        filas = [dict(zip(list(ADJ) + [f"lectora_{c}" for c in LEC], x.split("\t")))
                 for x in (T / "sel" / f"adjudicacion_pasada_2_etapa_{n}.tsv").read_text(encoding="utf-8")[:-1].split("\n")[1:]]
        for f in filas[::2]:   # la autora cambia la mitad
            f.update(marca="error", clase="corte", subclase="termina_fuera", subclase_adicional="", limpieza="", nota="lo vi otra vez")
        p2[n] = filas
        (T / f"p2_{n}.tsv").write_text(tsv_plano(filas, tuple(filas[0])), encoding="utf-8")
    shp2 = {n: sha(T / f"p2_{n}.tsv") for n in (1, 2)}
    arm = base + ["--pasada-2-1", T / "p2_1.tsv", "--sha-pasada-2-1", shp2[1], "--pasada-2-2", T / "p2_2.tsv", "--sha-pasada-2-2", shp2[2]]
    r = correr(P2S, ["armar"] + arm + ["--out", T / "arm"])
    ok(r.returncode == 0, "armar: corre")
    for n in (1, 2):
        rep = {f["ficha"]: f for f in p2[n]}
        final = leer(T / "arm" / f"adjudicacion_etapa_{n}.tsv")
        ok([f["ficha"] for f in final] == [f["ficha"] for f in p1[n]]
           and all(all(g[c] == (rep.get(g["ficha"]) or next(x for x in p1[n] if x["ficha"] == g["ficha"]))[c] for c in ADJ) for g in final),
           f"armar, etapa {n}: la pasada 1 con las filas de la pasada 2 en su lugar")
    acu = json.loads((T / "arm" / "acuerdo_lectora_pasada_1_S1quater.json").read_text(encoding="utf-8"))
    lp1 = {f["ficha"]: f for f in lec[1]}
    ok(acu["etapa_1"]["fichas"] == 90 and acu["etapa_1"]["marca_igual"] == sum(lp1[f["ficha"]]["marca"] == f["marca"] for f in p1[1])
       and acu["etapa_1"]["a_la_pasada_2"] == len(esperada[1]), "armar: el acuerdo, recalculado aparte")

    # --- 3. los frenos de pasada_2
    def frena(args, out, que, d):
        r = correr(P2S, args + ["--out", out])
        ok(r.returncode != 0 and "FRENO" in r.stderr + r.stdout and que in r.stderr + r.stdout and not Path(out).exists(), d)

    def variante(nombre, texto):
        (T / nombre).write_text(texto, encoding="utf-8")
        return T / nombre, sha(T / nombre)

    def con(arg, p, s, args):
        args = list(args)
        i = args.index(arg)
        args[i + 1], args[i + 3] = p, s
        return args

    antes = {x.name: sha(x) for x in (T / "arm").iterdir()}
    r = correr(P2S, ["armar"] + arm + ["--out", T / "arm"])
    ok(r.returncode != 0 and "ya existe" in r.stderr + r.stdout and {x.name: sha(x) for x in (T / "arm").iterdir()} == antes,
       "frena si la carpeta de salida ya existe, sin tocarla")
    frena(["seleccionar"] + con("--pasada-1-1", T / "p1_1.tsv", "0" * 64, base), T / "x1", "sha256", "frena si la pasada 1 no da su sha256")
    t = (T / "p2_1.tsv").read_text(encoding="utf-8").split("\n")
    v = t[1].split("\t"); v[10] = "una\tnota partida"; t2 = t[:1] + ["\t".join(v)] + t[2:]
    p, s = variante("p2_tab.tsv", "\n".join(t2))
    frena(["armar"] + con("--pasada-2-1", p, s, arm), T / "x2", "columnas", "frena si una nota de la autora trae una tabulación")
    v = t[1].split("\t"); v[10] = 'dice "algo"'
    p, s = variante("p2_comillas.tsv", "\n".join(t[:1] + ["\t".join(v)] + t[2:]))
    frena(["armar"] + con("--pasada-2-1", p, s, arm), T / "x3", "comillas", "frena si una columna de la autora trae comillas dobles")
    p, s = variante("p2_cr.tsv", (T / "p2_1.tsv").read_text(encoding="utf-8").replace("\n", "\r\n"))
    frena(["armar"] + con("--pasada-2-1", p, s, arm), T / "x4", "fin de renglón", "frena si la planilla trae retornos de carro")
    p, s = variante("p2_orden.tsv", "\n".join(t[:1] + [t[2], t[1]] + t[3:]))
    frena(["armar"] + con("--pasada-2-1", p, s, arm), T / "x5", "seleccionadas", "frena si la pasada 2 trae las fichas en otro orden")
    p, s = variante("p2_falta.tsv", "\n".join(t[:1] + t[2:]))
    frena(["armar"] + con("--pasada-2-1", p, s, arm), T / "x6", "seleccionadas", "frena si a la pasada 2 le falta una ficha")
    q = (T / "p1_1.tsv").read_text(encoding="utf-8").split("\n")
    v = q[1].split("\t"); v[6] = "error"
    p, s = variante("p1_sigue.tsv", "\n".join(q[:1] + ["\t".join(v)] + q[2:]))
    frena(["seleccionar"] + con("--pasada-1-1", p, s, base), T / "x7", "etapa 1", "frena si la etapa 1 trae unidad que sigue")
    v = q[1].split("\t"); v[1] = "quizas"
    p, s = variante("p1_marca.tsv", "\n".join(q[:1] + ["\t".join(v)] + q[2:]))
    frena(["seleccionar"] + con("--pasada-1-1", p, s, base), T / "x8", "marca no válida", "frena si una marca no es válida")
    l1 = (T / "planilla_1.tsv").read_text(encoding="utf-8").split("\n")
    v = l1[3].split("\t"); v[-1] = '"nota\nen dos renglones"'
    p, s = variante("planilla_partida.tsv", "\n".join(l1[:3] + ["\t".join(v)] + l1[4:]))
    frena(["seleccionar"] + con("--planilla-1", p, s, base), T / "x9", "columnas del encabezado",
          "frena si la planilla de la lectora trae una celda partida en dos renglones")
    v = l1[3].split("\t"); v[-1] = '"nota\tcon tabulación"'
    p, s = variante("planilla_tab.tsv", "\n".join(l1[:3] + ["\t".join(v)] + l1[4:]))
    frena(["seleccionar"] + con("--planilla-1", p, s, base), T / "x10", "tabulación",
          "frena antes de escribir si un valor de la lectora trae una tabulación")

    # --- 4. acuerdo de la etapa 1
    r = correr(ACU, ["--planilla-1", T / "planilla_1.tsv", "--sha-planilla-1", sh["planilla_1.tsv"], "--pasada-1-1", T / "p1_1.tsv",
                     "--sha-pasada-1-1", sh["p1_1.tsv"], "--out", T / "acuerdo.json"])
    ac = json.loads((T / "acuerdo.json").read_text(encoding="utf-8")) if r.returncode == 0 else {}
    dos_error = [f for f in p1[1] if f["marca"] == "error" == lp1[f["ficha"]]["marca"]]
    ok(r.returncode == 0 and set(ac) == {"nota", "sha256", "las_90"} and ac["las_90"]["fichas"] == 90
       and ac["las_90"]["marca_igual"] == sum(lp1[f["ficha"]]["marca"] == f["marca"] for f in p1[1])
       and ac["las_90"]["clase_igual_entre_las_dos_error"] == sum(lp1[f["ficha"]]["clase"] == f["clase"] for f in dos_error),
       "acuerdo: las 90, recalculado aparte, sin el recorte de las 19 primeras")
    r = correr(ACU, ["--planilla-1", T / "planilla_1.tsv", "--sha-planilla-1", sh["planilla_1.tsv"], "--pasada-1-1", T / "p1_2.tsv",
                     "--sha-pasada-1-1", sh["p1_2.tsv"], "--out", T / "acuerdo_mal.json"])
    ok(r.returncode != 0 and not (T / "acuerdo_mal.json").exists(), "acuerdo: frena si las fichas no son las mismas 90")

    # --- 5. aplicar
    apl = ["--planilla-1", T / "planilla_1.tsv", "--sha-planilla-1", sh["planilla_1.tsv"], "--planilla-2", T / "planilla_2.tsv",
           "--sha-planilla-2", sh["planilla_2.tsv"], "--orden", T / "orden.json", "--sha-orden", sh["orden.json"],
           "--adjudicacion-1", T / "arm" / "adjudicacion_etapa_1.tsv", "--adjudicacion-2", T / "arm" / "adjudicacion_etapa_2.tsv"]
    r = correr(APL, apl + ["--out-planilla-1", T / "adj_1.tsv", "--out-planilla-2", T / "adj_2.tsv", "--out-json", T / "adj.json"])
    ok(r.returncode == 0, "aplicar: corre")
    reg = json.loads((T / "adj.json").read_text(encoding="utf-8"))
    for n in (1, 2):
        fin = {f["ficha"]: f for f in leer(T / "arm" / f"adjudicacion_etapa_{n}.tsv")}
        sal = leer(T / f"adj_{n}.tsv")
        ok([f["ficha"] for f in sal] == [f["ficha"] for f in lec[n]]
           and all(all(g[c] == fin[g["ficha"]][c] for c in LEC[:-1]) for g in sal)
           and all(g["nota"] == (fin[g["ficha"]]["nota"] if fin[g["ficha"]]["nota"].strip() else
                                 next(x for x in lec[n] if x["ficha"] == g["ficha"])["nota"]) for g in sal),
           f"aplicar, etapa {n}: la marca de la autora en cada ficha, la nota de la autora si trae una, el orden de la planilla")
    fin2 = leer(T / "arm" / "adjudicacion_etapa_2.tsv")
    ok(len(reg["cierres_confirmados"]) == sum(f["la_que_sigue"] == "error" for f in fin2) > 0
       and not any(x["cuenta"] for x in reg["cierres_confirmados"] + reg["herencias_confirmadas"])
       and len(reg["herencias_confirmadas"]) == sum(f["herencia"] == "error" for f in fin2) > 0,
       "aplicar: la unidad que sigue y la herencia se registran y no cuentan")
    ok("revierte_por_lista" not in json.dumps(reg) and "ri_oc" not in json.dumps(reg), "aplicar: sin listas de (b) ni reglas de ri_oc")
    r = correr(APL, apl + ["--out-planilla-1", T / "adj_1.tsv", "--out-planilla-2", T / "y2.tsv", "--out-json", T / "y.json"])
    ok(r.returncode != 0 and not (T / "y2.tsv").exists(), "aplicar: frena si una salida ya existe")
    bad = list(apl); bad[bad.index("--sha-planilla-1") + 1] = "0" * 64
    r = correr(APL, bad + ["--out-planilla-1", T / "z1.tsv", "--out-planilla-2", T / "z2.tsv", "--out-json", T / "z.json"])
    ok(r.returncode != 0 and not (T / "z1.tsv").exists(), "aplicar: frena si la planilla no da el sha256 de su sello")
    a1 = leer(T / "arm" / "adjudicacion_etapa_1.tsv")
    for caso, cambio in (("unidad que sigue en la etapa 1", {"la_que_sigue": "error", "clase_que_sigue": "corte",
                                                              "subclase_que_sigue": "empieza_fuera"}),
                         ("herencia en la etapa 1", {"herencia": "error"}),
                         ("subclase no válida", {"marca": "error", "clase": "corte", "subclase": "inventada"})):
        g = [dict(f) for f in a1]; g[0].update(cambio)
        (T / "a1_mal.tsv").write_text(tsv_csv(g, ADJ), encoding="utf-8")
        b2 = list(apl); b2[b2.index("--adjudicacion-1") + 1] = T / "a1_mal.tsv"
        r = correr(APL, b2 + ["--out-planilla-1", T / "w1.tsv", "--out-planilla-2", T / "w2.tsv", "--out-json", T / "w.json"])
        ok(r.returncode != 0 and "RECHAZADO" in r.stderr + r.stdout and not (T / "w1.tsv").exists(), f"aplicar: rechaza {caso}")

    # --- 6. cifras
    cif = ["--orden", T / "orden.json", "--sha-orden", sh["orden.json"], "--poblaciones", T / "pob.json", "--sha-poblaciones",
           sh["pob.json"], "--limites", T / "lim.json", "--sha-limites", sh["lim.json"], "--planilla-1", T / "adj_1.tsv",
           "--planilla-2", T / "adj_2.tsv"]
    r = correr(CIF, cif + ["--out", T / "cifras.json"])
    ok(r.returncode == 0, "cifras: corre")
    c = json.loads((T / "cifras.json").read_text(encoding="utf-8"))
    s1 = leer(T / "adj_1.tsv")
    corte = lambda f: f["marca"] == "error" and f["clase"] == "corte"  # noqa: E731
    e_cor = sum(corte(f) for f in s1)
    e_dud = sum(corte(f) or f["marca"] == "dudosa" for f in s1)
    pz = c["etapa_1"]["cifra_del_piso"]
    ok(pz["dudosas_como_correctas"]["errores_de_corte"] == e_cor and pz["dudosas_como_error"]["errores_de_corte"] == e_dud
       and abs(pz["dudosas_como_error"]["wilson95"][0] - wilson_inf(90 - e_dud, 90)) < 1e-12 and pz["decide"] == "dudosas_como_error",
       "cifras: el piso con las dudosas de los dos modos, recalculado aparte; decide el de las dudosas como error")
    de = {f["id_opaco"]: f["estrato"] for f in e1}
    est = sum(pob["cortes"][e]["peso"] * sum(not corte(f) for f in s1 if de[f["ficha"]] == e) / n
              for e, n in (("vigente", 40), ("marcadores", 10), ("sin_raiz", 40)))
    ok(abs(c["etapa_1"]["cifra_del_corpus"]["estimacion"] - est) < 1e-12, "cifras: la del corpus, con los pesos de las poblaciones")
    ok(c["etapa_1"]["limites_declarados_en_la_muestra"]["lista_de_S1ter"] == 2
       and [x["unidad"] for x in c["etapa_1"]["limites_declarados_en_la_muestra"]["en_la_muestra"]] == [e1[9]["id"]],
       "cifras: el límite declarado de la muestra, por id")
    ok(c["etapa_1"]["tanda0_con_error_de_corte"] == (["ctacte::9.9"] if corte(next(f for f in s1 if f["ficha"] == "E1-005")) else []),
       "cifras: un error de corte en un TO de la tanda 0 se reporta aparte")
    ok(len(c["etapa_2"]["regresion_sin_cifra"]) == 12 and c["unidades_en_las_dos_etapas"] == []
       and not any(k in json.dumps(c) for k in ("c116", "mixto", "ri_oc")), "cifras: la regresión sin cifra, y nada de la 1.16")
    r = correr(CIF, cif + ["--out", T / "cifras.json"])
    ok(r.returncode != 0 and "ya existe" in r.stderr + r.stdout, "cifras: frena si la salida ya existe")
    o2 = json.loads(json.dumps(orden)); o2["etapa_1"]["fichas"][0]["estrato"] = "marcadores"
    (T / "orden_mal.json").write_text(json.dumps(o2), encoding="utf-8")
    b = list(cif); b[1], b[3] = T / "orden_mal.json", sha(T / "orden_mal.json")
    r = correr(CIF, b + ["--out", T / "cifras_mal.json"])
    ok(r.returncode != 0 and "40 / 10 / 40" in r.stderr + r.stdout and not (T / "cifras_mal.json").exists(),
       "cifras: frena si los estratos no son 40 / 10 / 40")
    b = list(cif); b[3] = "0" * 64
    r = correr(CIF, b + ["--out", T / "cifras_mal2.json"])
    ok(r.returncode != 0 and not (T / "cifras_mal2.json").exists(), "cifras: frena si el orden no da su sha256")
    g = [dict(f) for f in s1]; g[0].update(marca="error", clase="corte", subclase="")
    (T / "adj_1_mal.tsv").write_text(tsv_csv(g, COLS), encoding="utf-8")
    b = list(cif); b[b.index("--planilla-1") + 1] = T / "adj_1_mal.tsv"
    r = correr(CIF, b + ["--out", T / "cifras_inval.json"])
    ok(r.returncode == 0 and json.loads((T / "cifras_inval.json").read_text(encoding="utf-8"))["planillas_validas"] is False,
       "cifras: una marca inválida da planillas_validas = false, sin cifra")

    for cc, d in res:
        print(("ok   " if cc else "MAL  ") + d)
    print(f"{sum(cc for cc, _ in res)} de {len(res)} casos ok")


if __name__ == "__main__":
    main()
