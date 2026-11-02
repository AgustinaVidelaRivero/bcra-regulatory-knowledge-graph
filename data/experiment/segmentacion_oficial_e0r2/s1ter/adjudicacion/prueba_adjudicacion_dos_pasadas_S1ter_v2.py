"""Prueba con datos SINTÉTICOS de `preparar_pasada_1_S1ter_v2.py` y `pasada_2_S1ter_v2.py` (mesa, 10/10/2026; USD 0). No es una
lectura ni una adjudicación: las marcas las pone este script, y la salida no lleva ids ni marcas reales.

Cubre la decisión de la autora del 10/10/2026 (hoja §56):
- la pasada 1 de la etapa 1 son las 90 fichas, en el orden de su semilla, y el TSV de 90 filas lo lee `aplicar_adjudicacion_S1ter.py`
  sin cambios;
- un caso de cada condición de la pasada 2 (a, b, c y d) y casos que no van.

Usa copias: el orden de lectura sellado, las poblaciones finales, `lista_para_la_autora_S1ter.py`,
`aplicar_adjudicacion_S1ter.py` y `cifras_lectura_S1ter.py` de `s1ter/`, y los archivos de fichas de la carpeta de la lectora. Las
imágenes se reemplazan por archivos vacíos con el mismo nombre. Las planillas de la lectora son sintéticas, armadas desde la planilla
vacía.

Uso: python3 -B prueba_adjudicacion_dos_pasadas_S1ter_v2.py --s1ter <carpeta s1ter> --carpeta-lectora <carpeta> --scripts <carpeta
       de estos scripts> --trabajo <carpeta nueva del scratchpad>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
SHA_ORDEN = "acd57e37c039bd17a027fbd73cd0579f9f7460f054edf8d06be4fda2144e9681"
SHA_FINALES = "b47aee40f443d14cb4a39549f776aa61e5e8935c47bf3ac3d6fef70f7e9f8f25"
PREP, P2 = "preparar_pasada_1_S1ter_v2.py", "pasada_2_S1ter_v2.py"
res: list[tuple[bool, str]] = []


def ok(c: bool, que: str) -> None:
    res.append((bool(c), que))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def leer(p: Path) -> list[dict]:
    return list(csv.DictReader(open(p, encoding="utf-8"), delimiter="\t"))


def escribir(p: Path, filas: list[dict], cols) -> None:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(cols), delimiter="\t", lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for f in filas:
        w.writerow({c: f.get(c, "") for c in cols})
    p.write_text(s.getvalue(), encoding="utf-8")


def correr(args: list) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B"] + [str(x) for x in args], capture_output=True, text=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("s1ter", "carpeta_lectora", "scripts", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    T = Path(a.trabajo)
    if T.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    S, L, SC = Path(a.s1ter), Path(a.carpeta_lectora), Path(a.scripts)
    s1 = T / "s1ter"
    (s1 / "scripts").mkdir(parents=True)
    (s1 / "tramo_b").mkdir()
    for f in ("lista_para_la_autora_S1ter.py", "aplicar_adjudicacion_S1ter.py", "cifras_lectura_S1ter.py"):
        shutil.copy2(S / "scripts" / f, s1 / "scripts" / f)
    for f in ("orden_lectura_S1ter.json", "poblaciones_finales_S1ter.json"):
        shutil.copy2(S / "tramo_b" / f, s1 / "tramo_b" / f)
    ok(sha(s1 / "tramo_b" / "orden_lectura_S1ter.json") == SHA_ORDEN, "la copia del orden da su sha256 sellado")
    lec = T / "lectora"
    planillas, shas = {}, {}
    for n in (1, 2):
        e = f"etapa_{n}"
        (lec / e).mkdir(parents=True)
        shutil.copy2(L / e / f"fichas_{e}.md", lec / e / f"fichas_{e}.md")
        for img in (L / e).glob("*.png"):
            (lec / e / img.name).write_bytes(b"")
        vacia = leer(L / e / f"planilla_{e}.tsv")
        planillas[n] = [{"ficha": f["ficha"], "paginas": f["paginas"], "marca": "correcta"} for f in vacia]
    p1, p2 = planillas[1], planillas[2]
    # marcas sintéticas de la «lectora»
    p1[0].update(marca="dudosa")                                                  # etapa 1, caso a (la autora: correcta)
    p1[1].update(marca="error", clase="corte", subclase="termina_fuera")          # etapa 1, caso b (la autora: limpieza)
    p1[2].update(nota="NOTA_SINTETICA_ETAPA_1 con nota y marca igual")            # etapa 1, caso c
    p1[3].update(marca="error", clase="corte", subclase="empieza_fuera")          # etapa 1, no va: las dos, corte (subclase distinta)
    p2[0].update(marca="error", clase="limpieza", subclase="restos_pie")          # etapa 2, no va: igual, sin nota ni señal
    p2[1].update(nota="NOTA_SINTETICA_ETAPA_2 sobre la unidad que sigue")         # etapa 2, caso c
    cols = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
    for n in (1, 2):
        escribir(lec / f"etapa_{n}" / f"planilla_etapa_{n}.tsv", planillas[n], cols)
        shas[n] = sha(lec / f"etapa_{n}" / f"planilla_etapa_{n}.tsv")
    prep = [SC / PREP, "--s1ter", s1, "--carpeta-lectora", lec, "--sha-planilla-1", shas[1], "--sha-planilla-2", shas[2],
            "--sha-orden", SHA_ORDEN]
    r = correr(prep[:6] + ["0" * 64] + prep[7:] + ["--out-autora", T / "malo_a", "--out-mesa", T / "malo_m"])
    ok(r.returncode != 0 and not (T / "malo_a").exists() and not (T / "malo_m").exists()
       and not (T / "malo_a.parcial").exists(), "pasada 1: una planilla que no da su sello se rechaza sin escribir nada")
    r = correr(prep + ["--out-autora", T / "autora", "--out-mesa", T / "mesa"])
    ok(r.returncode == 0, "pasada 1: el script corre")
    js = json.loads((T / "mesa" / "NO_ABRIR_lista_para_la_autora_S1ter.json").read_text(encoding="utf-8"))
    reg = json.loads((T / "mesa" / "orden_pasada_1_S1ter.json").read_text(encoding="utf-8"))
    ids90 = sorted(f["ficha"] for f in p1)
    ok(len(ids90) == 90 and reg["etapas"]["etapa_1"]["orden"] == random.Random("U-SEG-OFICIAL:adjudicacion:S1-ter:etapa_1").sample(
        ids90, 90), "pasada 1, etapa 1: son las 90 fichas, en el orden de su semilla")
    ids2 = sorted(set(js["etapa_2"]["errores_y_dudosas"]) | set(js["etapa_2"]["correctas_con_nota"])
                  | set(js["etapa_2"]["correctas_sorteadas"]))
    ok(reg["etapas"]["etapa_2"]["orden"] == random.Random("U-SEG-OFICIAL:adjudicacion:S1-ter:etapa_2").sample(ids2, len(ids2)),
       "pasada 1, etapa 2: la lista, en el orden de su semilla (como la versión 1)")
    for n in (1, 2):
        e = f"etapa_{n}"
        d = T / "autora" / e
        texto = "\n".join(p.read_text(encoding="utf-8") for p in d.iterdir() if p.suffix in (".md", ".tsv", ".txt"))
        ok("NOTA_SINTETICA" not in texto, f"pasada 1, {e}: ninguna nota de la lectora en el material")
        man = [l.split("  ") for l in (d / "manifest.txt").read_text(encoding="utf-8").splitlines()]
        ok(all(sha(d / f) == h for h, f in man) and {f for _, f in man} == {p.name for p in d.iterdir()} - {"manifest.txt"},
           f"pasada 1, {e}: el manifest verifica y lista todo")
        ok({p.name.split("_p")[0] for p in d.glob("*.png")} == set(reg["etapas"][e]["orden"]),
           f"pasada 1, {e}: están las imágenes de cada ficha y de ninguna otra")
    ok(not any(x in json.dumps(reg) for x in ('"error"', "dudosa", "NOTA")), "pasada 1: el registro del orden no trae marcas")
    # pasada 1 sintética de la «autora»
    p1a = {n: leer(T / "autora" / f"etapa_{n}" / f"adjudicacion_pasada_1_etapa_{n}.tsv") for n in (1, 2)}
    lecm = {n: {f["ficha"]: f for f in planillas[n]} for n in (1, 2)}
    for n in (1, 2):
        for f in p1a[n]:
            f.update({c: lecm[n][f["ficha"]].get(c, "") for c in ("marca", "clase", "subclase")})
    a1 = {f["ficha"]: f for f in p1a[1]}
    a2 = {f["ficha"]: f for f in p1a[2]}
    a1[p1[0]["ficha"]].update(marca="correcta")                                                    # a
    a1[p1[1]["ficha"]].update(clase="limpieza", subclase="restos_encabezado")                     # b
    a1[p1[3]["ficha"]].update(subclase="termina_fuera")                                            # no va: solo la subclase difiere
    control = [i for i in js["etapa_2"]["correctas_sorteadas"] if i not in (p2[0]["ficha"], p2[1]["ficha"])]
    a2[control[0]].update(la_que_sigue="error", clase_que_sigue="corte", subclase_que_sigue="empieza_fuera")   # d (la que sigue)
    a2[control[1]].update(herencia="error")                                                                       # d (herencia)
    esperado = {1: {p1[0]["ficha"], p1[1]["ficha"], p1[2]["ficha"]}, 2: {p2[1]["ficha"], control[0], control[1]}}
    for n in (1, 2):
        escribir(T / f"p1_{n}.tsv", p1a[n], ADJ)
    base = ["--pasada-1-1", T / "p1_1.tsv", "--sha-pasada-1-1", sha(T / "p1_1.tsv"), "--pasada-1-2", T / "p1_2.tsv",
            "--sha-pasada-1-2", sha(T / "p1_2.tsv"), "--planilla-1", lec / "etapa_1" / "planilla_etapa_1.tsv", "--sha-planilla-1",
            shas[1], "--planilla-2", lec / "etapa_2" / "planilla_etapa_2.tsv", "--sha-planilla-2", shas[2]]
    r = correr([SC / P2, "seleccionar"] + base + ["--out", T / "p2"])
    ok(r.returncode == 0, "pasada 2: seleccionar corre")
    sel = {n: {f["ficha"] for f in leer(T / "p2" / f"adjudicacion_pasada_2_etapa_{n}.tsv")} for n in (1, 2)}
    ok(p1[0]["ficha"] in sel[1], "condición a: la marca no coincide → va")
    ok(p1[1]["ficha"] in sel[1], "condición b: las dos error, una corte y la otra limpieza → va")
    ok(p1[2]["ficha"] in sel[1], "condición c: nota de la lectora en la etapa 1 con la marca igual → va")
    ok(p2[1]["ficha"] in sel[2], "condición c: nota de la lectora en la etapa 2 → va")
    ok(control[0] in sel[2], "condición d: la autora marcó la unidad que sigue → va")
    ok(control[1] in sel[2], "condición d: la autora marcó la herencia → va")
    ok(p1[3]["ficha"] not in sel[1], "no va: las dos error de corte, solo la subclase difiere")
    ok(p2[0]["ficha"] not in sel[2] and p1[4]["ficha"] not in sel[1], "no va: marca igual, sin nota y sin señal de la autora")
    ok(sel == esperado, "pasada 2: se seleccionan exactamente las fichas esperadas, en las dos etapas")
    ok(all("lectora_marca" in f and "lectora_nota" in f for f in leer(T / "p2" / "adjudicacion_pasada_2_etapa_1.tsv")),
       "pasada 2: muestra la marca y la nota de la lectora")
    # pasada 2 sintética y armado
    p2a = {n: leer(T / "p2" / f"adjudicacion_pasada_2_etapa_{n}.tsv") for n in (1, 2)}
    p2a[1][0]["marca"] = "dudosa" if p2a[1][0]["marca"] != "dudosa" else "correcta"
    for n in (1, 2):
        escribir(T / f"p2_{n}.tsv", p2a[n], ADJ)
    arm = ([SC / P2, "armar"] + base + ["--pasada-2-1", T / "p2_1.tsv", "--sha-pasada-2-1", sha(T / "p2_1.tsv"),
           "--pasada-2-2", T / "p2_2.tsv", "--sha-pasada-2-2", sha(T / "p2_2.tsv")])
    extra = p2a[2] + [dict(next(f for f in p1a[2] if f["ficha"] not in esperado[2]))]
    escribir(T / "p2_extra.tsv", extra, ADJ)
    r = correr(arm[:-4] + ["--pasada-2-2", T / "p2_extra.tsv", "--sha-pasada-2-2", sha(T / "p2_extra.tsv"), "--out", T / "fin_malo"])
    ok(r.returncode != 0 and not (T / "fin_malo").exists(), "armar: una pasada 2 con fichas de más se rechaza sin escribir nada")
    r = correr(arm + ["--out", T / "fin"])
    ok(r.returncode == 0, "armar corre")
    fin1 = leer(T / "fin" / "adjudicacion_etapa_1.tsv")
    ok(len(fin1) == 90, "armar: el TSV final de la etapa 1 tiene 90 filas")
    for n in (1, 2):
        fin = leer(T / "fin" / f"adjudicacion_etapa_{n}.tsv")
        rep = {f["ficha"]: f for f in p2a[n]}
        ok([f["ficha"] for f in fin] == [f["ficha"] for f in p1a[n]] and all(
            all(f[c] == (rep.get(f["ficha"]) or g)[c] for c in ADJ) for f, g in zip(fin, p1a[n])),
           f"armar, etapa {n}: es la pasada 1 con las filas de la pasada 2 en su lugar")
    ac = json.loads((T / "fin" / "acuerdo_lectora_pasada_1_S1ter.json").read_text(encoding="utf-8"))
    ok(ac["etapa_1"]["fichas"] == 90 and ac["etapa_1"]["por_condicion"] == {"a": 1, "b": 1, "c": 1},
       "acuerdo: sobre las 90 de la etapa 1, con un caso de a, b y c")
    r = correr([s1 / "scripts" / "aplicar_adjudicacion_S1ter.py", "--planilla-1", lec / "etapa_1" / "planilla_etapa_1.tsv",
                "--planilla-2", lec / "etapa_2" / "planilla_etapa_2.tsv", "--sha-planilla-1", shas[1], "--sha-planilla-2", shas[2],
                "--orden", s1 / "tramo_b" / "orden_lectura_S1ter.json", "--sha-orden", SHA_ORDEN,
                "--poblaciones-finales", s1 / "tramo_b" / "poblaciones_finales_S1ter.json", "--sha-poblaciones-finales",
                SHA_FINALES, "--adjudicacion-1", T / "fin" / "adjudicacion_etapa_1.tsv", "--adjudicacion-2",
                T / "fin" / "adjudicacion_etapa_2.tsv", "--out-planilla-1", T / "adj_1.tsv", "--out-planilla-2", T / "adj_2.tsv",
                "--out-json", T / "adj.json"])
    ok(r.returncode == 0 and len(leer(T / "adj_1.tsv")) == 90,
       "aplicar_adjudicacion_S1ter.py lee el TSV de 90 filas sin cambios y da la planilla adjudicada de 90")
    for b, q in res:
        print(("ok   " if b else "MAL  ") + q)
    print(f"{sum(b for b, _ in res)} de {len(res)} controles ok")
    sys.exit(0 if all(b for b, _ in res) else 1)


if __name__ == "__main__":
    main()
