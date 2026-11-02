"""U-SEG-OFICIAL, S1-quater: prueba de `instalar_pasada_2_S1quater.py` (mesa, 14/10/2026; USD 0), con datos sintéticos: no usa nada de la
lectura de S1-quater ni de S1-ter. Arma una pasada 1 inventada (fichas, imágenes, planillas y manifest como los deja
`preparar_pasada_1_S1quater.py`), corre `pasada_2_S1quater.py seleccionar` (sellado) y después el instalador, en otro proceso, y
recalcula por su cuenta lo que tiene que dar. La salida trae solo «ok» o «MAL» por caso.

Uso: python3 -I -B prueba_instalar_pasada_2_S1quater.py --scripts <carpeta con los tres scripts> --trabajo <carpeta nueva>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import random
import shutil
import subprocess
import sys
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
COLS = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
LEC = COLS[2:]
res: list[tuple[bool, str]] = []


def ok(c, d):
    res.append((bool(c), d))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def plano(filas, cols) -> str:
    return "\n".join(["\t".join(cols)] + ["\t".join(f.get(c, "") for c in cols) for f in filas]) + "\n"


def con_csv(filas, cols) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(cols), delimiter="\t", lineterminator="\n")
    w.writeheader()
    for f in filas:
        w.writerow({c: f.get(c, "") for c in cols})
    return s.getvalue()


def correr(script: Path, args: list) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(script)] + [str(x) for x in args], capture_output=True, text=True)


def foto(d: Path) -> dict:
    return {str(p.relative_to(d)): (sha(p) if p.is_file() else "dir") for p in sorted(d.rglob("*"))} if d.exists() else {}


def armar_pasada_1(T: Path, rng: random.Random) -> tuple[dict, dict, dict]:
    """La pasada 1 inventada: por etapa, fichas, imágenes, la planilla marcada y el manifest con la planilla vacía, como el armado."""
    p1d = T / "pasada_1"
    planillas_lectora, filas_autora, mans = {}, {}, {}
    for n, k in ((1, 12), (2, 8)):
        d = p1d / f"etapa_{n}"
        d.mkdir(parents=True)
        ids = [f"E{n}-{j:03d}" for j in range(1, k + 1)]
        rng.shuffle(ids)
        bl = "".join(f"## {i}\n\n- texto propio de la unidad {i}: «uno; dos»\n- páginas: {j + 3}\n\n" for j, i in enumerate(ids))
        (d / f"fichas_pasada_1_etapa_{n}.md").write_text(f"# Adjudicación: etapa_{n}, pasada 1\n\nFichas en un orden al azar.\n\n" + bl,
                                                        encoding="utf-8")
        for j, i in enumerate(ids):
            for pag in ([j + 3] if j % 3 else [j + 3, j + 4]):
                (d / f"{i}_p{pag}.png").write_bytes(hashlib.sha256(f"{i}-{pag}".encode()).digest() * 8)
        (d / "LEEME.md").write_text("LEEME sintético\n", encoding="utf-8")
        planilla = d / f"adjudicacion_pasada_1_etapa_{n}.tsv"
        planilla.write_text(plano([{"ficha": i} for i in ids], ADJ), encoding="utf-8")
        nombres = sorted(p.name for p in d.iterdir())
        (d / "manifest.txt").write_text("".join(f"{sha(d / x)}  {x}\n" for x in nombres), encoding="utf-8")
        mans[n] = sha(d / "manifest.txt")
        lec, aut = [], []
        for j, i in enumerate(ids):
            l = {"ficha": i, "paginas": str(j + 3), "marca": "correcta", "clase": "", "subclase": "", "subclase_adicional": "",
                 "limpieza": "", "nota": ""}
            a = {"ficha": i, "marca": "correcta", "clase": "", "subclase": "", "subclase_adicional": "", "limpieza": "",
                 "la_que_sigue": "", "clase_que_sigue": "", "subclase_que_sigue": "", "herencia": "", "nota": ""}
            caso = j % 6
            if caso == 1:   # a: no coinciden
                a.update(marca="error", clase="corte", subclase="termina_fuera")
            elif caso == 2:   # b: las dos error, clases distintas
                a.update(marca="error", clase="corte", subclase="empieza_fuera")
                l.update(marca="error", clase="limpieza", subclase="restos_pie")
            elif caso == 3:   # c: nota de la lectora, con comillas
                l["nota"] = 'dice "otra cosa"'
            elif caso == 4 and n == 2:   # d: herencia
                a.update(herencia="error")
            elif caso == 5:   # nada; con nota de la autora
                a["nota"] = "vista con cuidado"
            lec.append(l)
            aut.append(a)
        rng.shuffle(lec)
        planilla.write_text(plano(aut, ADJ), encoding="utf-8")   # la autora marcó: la planilla ya no es la del manifest
        planillas_lectora[n] = lec
        filas_autora[n] = aut
    return planillas_lectora, filas_autora, mans


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    a = ap.parse_args()
    S, T = a.scripts, a.trabajo
    if T.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    T.mkdir(parents=True)
    P2S, INS = S / "pasada_2_S1quater.py", S / "instalar_pasada_2_S1quater.py"
    rng = random.Random("prueba-instalar-pasada-2-S1quater")
    lec, aut, mans = armar_pasada_1(T, rng)
    for n in (1, 2):
        (T / f"lectora_{n}.tsv").write_text(con_csv(lec[n], COLS), encoding="utf-8")
    p1d = T / "pasada_1"
    shp = {n: sha(p1d / f"etapa_{n}" / f"adjudicacion_pasada_1_etapa_{n}.tsv") for n in (1, 2)}
    shl = {n: sha(T / f"lectora_{n}.tsv") for n in (1, 2)}
    sel_args = ["--pasada-1-1", p1d / "etapa_1/adjudicacion_pasada_1_etapa_1.tsv", "--sha-pasada-1-1", shp[1],
                "--pasada-1-2", p1d / "etapa_2/adjudicacion_pasada_1_etapa_2.tsv", "--sha-pasada-1-2", shp[2],
                "--planilla-1", T / "lectora_1.tsv", "--sha-planilla-1", shl[1], "--planilla-2", T / "lectora_2.tsv",
                "--sha-planilla-2", shl[2], "--out", T / "sel"]
    r = correr(P2S, ["seleccionar"] + sel_args)
    ok(r.returncode == 0, "la selección sintética corre con el script sellado")
    shs = {n: sha(T / "sel" / f"adjudicacion_pasada_2_etapa_{n}.tsv") for n in (1, 2)}

    def args(**cambios):
        base = {"pasada-1": p1d, "sha-manifest-1": mans[1], "sha-manifest-2": mans[2], "sha-planilla-1": shp[1],
                "sha-planilla-2": shp[2], "seleccion": T / "sel", "sha-seleccion-1": shs[1], "sha-seleccion-2": shs[2],
                "out": T / "pasada_2"}
        base.update({k.replace("_", "-"): v for k, v in cambios.items()})
        return [x for k, v in base.items() for x in (f"--{k}", v)]

    antes_p1 = foto(p1d)
    # --- 1. el caso bueno
    r = correr(INS, args())
    ok(r.returncode == 0 and r.stdout.count("manifest.txt") == 2, "el instalador corre e imprime solo los dos manifest")
    ok(foto(p1d) == antes_p1, "la pasada 1 no cambia")
    for n in (1, 2):
        d = T / "pasada_2" / f"etapa_{n}"
        lp = {f["ficha"]: f for f in lec[n]}
        esperadas = [f["ficha"] for f in aut[n] if f["marca"] != lp[f["ficha"]]["marca"]
                     or (f["marca"] == "error" == lp[f["ficha"]]["marca"] and f["clase"] != lp[f["ficha"]]["clase"])
                     or lp[f["ficha"]]["nota"].strip() or (n == 2 and "error" in (f["la_que_sigue"], f["herencia"]))]
        ok((d / f"adjudicacion_pasada_2_etapa_{n}.tsv").read_bytes() == (T / "sel" / f"adjudicacion_pasada_2_etapa_{n}.tsv").read_bytes(),
           f"etapa {n}: la planilla es la selección, byte a byte")
        md = (d / f"fichas_pasada_2_etapa_{n}.md").read_text(encoding="utf-8")
        cab = [x[3:] for x in md.splitlines() if x.startswith("## E")]
        ok(cab == esperadas and len(esperadas) > 0, f"etapa {n}: las fichas, las de la regla a–d recalculada aparte, en su orden")
        orig = (p1d / f"etapa_{n}" / f"fichas_pasada_1_etapa_{n}.md").read_text(encoding="utf-8")
        ok(all(f"## {i}\n\n- texto propio de la unidad {i}: «uno; dos»\n" in md and f"## {i}\n" in orig for i in esperadas),
           f"etapa {n}: cada bloque, tal cual el de la pasada 1")
        imgs = sorted(p.name for p in d.glob("*.png"))
        ok(imgs == sorted(p.name for p in (p1d / f"etapa_{n}").glob("*.png") if p.name.split("_p")[0] in esperadas)
           and all(sha(d / x) == sha(p1d / f"etapa_{n}" / x) for x in imgs), f"etapa {n}: solo las imágenes de las seleccionadas, iguales")
        ok(subprocess.run(["shasum", "-a", "256", "-c", "manifest.txt"], cwd=d, capture_output=True).returncode == 0,
           f"etapa {n}: el manifest.txt verifica")
        perm = {p.name: p.stat().st_mode & 0o777 for p in d.iterdir()}
        ok(perm[f"adjudicacion_pasada_2_etapa_{n}.tsv"] == 0o644 and all(v == 0o444 for k, v in perm.items() if not k.endswith(".tsv")),
           f"etapa {n}: todo de solo lectura salvo la planilla")
        ok('- nota: dice "otra cosa"' in md and "- c: la lectora dejó una nota" in md, f"etapa {n}: la fila de la lectora y la condición c")
        if n == 2:
            ok("- d: marcaste la_que_sigue o herencia como error (etapa 2)" in md, "etapa 2: la condición d")
    ok(not (T / "pasada_2.parcial").exists(), "no queda ninguna carpeta .parcial")

    # --- 2. los frenos: no escriben nada y no dejan .parcial
    def frena(cambios: dict, que: str, msg: str, preparar=None, deshacer=None):
        if preparar:
            preparar()
        cambios = dict(cambios)
        out = cambios.pop("out", T / f"no_{len(res)}")
        antes = foto(out)
        r = correr(INS, args(out=out, **cambios))
        ok(r.returncode != 0 and r.stdout == "" and "FRENO" in r.stderr and msg in r.stderr and foto(out) == antes
           and not out.with_name(out.name + ".parcial").exists(), f"frena: {que}")
        if deshacer:
            deshacer()

    frena({"out": T / "pasada_2"}, "la carpeta de salida ya existe", "ya existe")
    frena({"sha_manifest_1": "0" * 64}, "el manifest de la etapa 1 no es el registrado", "manifest.txt de la etapa 1")
    frena({"sha_seleccion_2": "0" * 64}, "la selección de la etapa 2 no da su sha256", "la selección de la etapa 2 no da su sha256")
    frena({"sha_planilla_1": "0" * 64}, "la planilla de la pasada 1 no da el sha256 de su sello", "la pasada 1 de la etapa 1 no da su sha256")
    # una fila de la selección que no es la de la pasada 1, con su sha256 correcto
    alt = T / "sel_alterada"
    shutil.copytree(T / "sel", alt)
    pl = alt / "adjudicacion_pasada_2_etapa_1.tsv"
    reng = pl.read_text(encoding="utf-8").split("\n")
    v = reng[1].split("\t")
    v[1] = "dudosa" if v[1] != "dudosa" else "correcta"
    reng[1] = "\t".join(v)
    pl.write_text("\n".join(reng), encoding="utf-8")
    frena({"seleccion": alt, "sha_seleccion_1": sha(pl)}, "una fila de la selección no es la de la pasada 1", "una fila no es la de la pasada 1")
    # una ficha que no cumple ninguna condición, agregada a la selección, con su sha256 correcto
    alt2 = T / "sel_forjada"
    shutil.copytree(T / "sel", alt2)
    pl2 = alt2 / "adjudicacion_pasada_2_etapa_1.tsv"
    lp = {f["ficha"]: f for f in lec[1]}
    sin = next(f for f in aut[1] if not (f["marca"] != lp[f["ficha"]]["marca"] or lp[f["ficha"]]["nota"].strip()
                                        or (f["marca"] == "error" == lp[f["ficha"]]["marca"] and f["clase"] != lp[f["ficha"]]["clase"])))
    sel_ids = [x.split("\t")[0] for x in pl2.read_text(encoding="utf-8")[:-1].split("\n")[1:]]
    filas = [f for f in aut[1] if f["ficha"] in sel_ids or f["ficha"] == sin["ficha"]]
    p2cols = list(ADJ) + [f"lectora_{c}" for c in LEC]
    pl2.write_text(plano([f | {f"lectora_{c}": lp[f["ficha"]][c] for c in LEC} for f in filas], p2cols), encoding="utf-8")
    frena({"seleccion": alt2, "sha_seleccion_1": sha(pl2)}, "una ficha de la selección no cumple ninguna condición a–d", "no cumple ninguna condición")
    # una imagen cambiada
    img = sorted((p1d / "etapa_2").glob("*.png"))[0]
    viejo = img.read_bytes()
    frena({}, "una imagen no da el sha256 de su manifest", "una imagen de la etapa 2 no da", preparar=lambda: img.write_bytes(viejo + b"x"),
          deshacer=lambda: img.write_bytes(viejo))
    # el archivo de fichas cambiado
    fm = p1d / "etapa_1" / "fichas_pasada_1_etapa_1.md"
    viejo_fm = fm.read_bytes()
    frena({}, "el archivo de fichas no da el sha256 de su manifest", "el archivo de fichas de la etapa 1 no da", preparar=lambda: fm.write_bytes(viejo_fm + b"\n"),
          deshacer=lambda: fm.write_bytes(viejo_fm))
    ok(foto(p1d) == antes_p1, "después de los frenos, la pasada 1 sigue igual")
    for c, d in res:
        print(("ok   " if c else "MAL  ") + d)
    print(f"{sum(c for c, _ in res)} de {len(res)}")
    sys.exit(0 if all(c for c, _ in res) else 1)


if __name__ == "__main__":
    main()
