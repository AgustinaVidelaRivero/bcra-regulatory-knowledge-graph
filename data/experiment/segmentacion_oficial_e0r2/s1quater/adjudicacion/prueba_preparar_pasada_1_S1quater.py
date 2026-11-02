"""U-SEG-OFICIAL, S1-quater: prueba de `preparar_pasada_1_S1quater.py` (mesa, 13/10/2026; USD 0). No usa nada de S1-quater.

Usa como datos la carpeta de la lectora de S1-ter regenerada por `prueba_S1quater.py` (unidades leídas en S1-ter) y el orden sellado
de S1-ter. Arma con ella un tar como el de S1-quater y corre los casos. La salida trae solo «ok» o «MAL» por caso.

Uso: python3 -B prueba_preparar_pasada_1_S1quater.py --script <preparar_pasada_1_S1quater.py> --carpeta <carpeta con etapa_1/ y etapa_2/>
       --orden <orden de lectura de S1-ter> --trabajo <carpeta nueva>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

res: list[tuple[bool, str]] = []


def ok(c: bool, d: str) -> None:
    res.append((bool(c), d))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hacer_tar(src: Path, dst: Path, extra: dict[str, bytes] | None = None, cambiar: str | None = None) -> None:
    with tarfile.open(dst, "w") as t:
        for e in ("etapa_1", "etapa_2"):
            t.add(src / e, arcname=e, recursive=False)
            for p in sorted((src / e).iterdir()):
                if cambiar and p.name == cambiar:
                    b = p.read_bytes() + b"\n"
                    ti = tarfile.TarInfo(f"{e}/{p.name}"); ti.size = len(b); t.addfile(ti, io.BytesIO(b))
                else:
                    t.add(p, arcname=f"{e}/{p.name}")
        for n, b in (extra or {}).items():
            ti = tarfile.TarInfo(n); ti.size = len(b); t.addfile(ti, io.BytesIO(b))


def correr(script: Path, args: list) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(script)] + [str(x) for x in args], capture_output=True, text=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("script", "carpeta", "orden", "trabajo"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    T = a.trabajo
    if T.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    T.mkdir(parents=True)
    tar = T / "NO_ABRIR_tar_bueno.tar"
    hacer_tar(a.carpeta, tar)
    m1, m2 = sha(a.carpeta / "etapa_1" / "manifest.txt"), sha(a.carpeta / "etapa_2" / "manifest.txt")
    so = sha(a.orden)
    base = lambda t=tar, s=None, o=a.orden, so_=so, e="1,2", out="aut", mesa="mesa", sm1=m1: [  # noqa: E731
        "--tar", t, "--sha-tar", s or sha(t), "--orden", o, "--sha-orden", so_, "--sha-manifest-1", sm1, "--sha-manifest-2", m2,
        "--etapas", e, "--out-autora", T / out, "--out-mesa", T / mesa]
    orden = json.loads(a.orden.read_text(encoding="utf-8"))

    # 1. las dos etapas
    r = correr(a.script, base())
    ok(r.returncode == 0, "dos etapas: corre sin frenar")
    for n in (1, 2):
        e = f"etapa_{n}"; d = T / "aut" / e
        ids = sorted(f["id_opaco"] for f in orden[e]["fichas"])
        fichas = (d / f"fichas_pasada_1_{e}.md").read_text(encoding="utf-8")
        orden_p1 = re.findall(r"(?m)^## (E\d-\d{3})$", fichas)
        ok(sorted(orden_p1) == ids and orden_p1 != ids, f"{e}: todas las fichas del orden, en otro orden")
        import random
        ok(orden_p1 == random.Random(f"U-SEG-OFICIAL:adjudicacion:S1-quater:{e}").sample(ids, len(ids)), f"{e}: el orden sale de su semilla")
        fuente = (a.carpeta / e / f"fichas_{e}.md").read_text(encoding="utf-8")
        bl = {m.group(1): m.group(0) for m in re.finditer(r"(?ms)^## (E\d-\d{3})$.*?(?=^## E\d-\d{3}$|\Z)", fuente)}
        ok(all(bl[i].rstrip("\n") in fichas for i in ids), f"{e}: cada bloque de ficha, tal cual")
        imgs = sorted(p.name for p in (a.carpeta / e).glob("*.png"))
        ok(sorted(p.name for p in d.glob("*.png")) == imgs and all(sha(d / i) == sha(a.carpeta / e / i) for i in imgs), f"{e}: las imágenes, iguales")
        filas = list(csv.DictReader(open(d / f"adjudicacion_pasada_1_{e}.tsv", encoding="utf-8"), delimiter="\t"))
        ok([f["ficha"] for f in filas] == orden_p1 and all(not any(f[c] for c in list(f)[1:]) for f in filas), f"{e}: la planilla vacía, en el orden")
        ok({p.name for p in d.iterdir()} == set(imgs) | {f"fichas_pasada_1_{e}.md", f"adjudicacion_pasada_1_{e}.tsv", "LEEME.md", "manifest.txt"},
           f"{e}: nada de más en la carpeta")
        man = [l.split("  ", 1) for l in (d / "manifest.txt").read_text(encoding="utf-8").splitlines()]
        ok(all(sha(d / f) == h for h, f in man) and len(man) == len(list(d.iterdir())) - 1, f"{e}: el manifest.txt verifica")
        leeme = (d / "LEEME.md").read_text(encoding="utf-8")
        ok("Rige el criterio final de S1-ter" in leeme and ("la_que_sigue`: `error`" in leeme) == (n == 2), f"{e}: el LEEME de su etapa")
    reg = json.loads((T / "mesa" / "orden_pasada_1_S1quater.json").read_text(encoding="utf-8"))
    ok(set(reg["etapas"]) == {"etapa_1", "etapa_2"} and not (T / "mesa" / "NO_ABRIR_fuente_tar").exists(), "el registro de la mesa, sin la fuente")
    ok(not any(k in json.dumps(reg) for k in ("correcta", "\"error\"", "dudosa", "marca")), "el registro de la mesa no trae marcas")

    # 2. solo la etapa 1
    r = correr(a.script, base(e="1", out="aut1", mesa="mesa1"))
    ok(r.returncode == 0 and sorted(p.name for p in (T / "aut1").iterdir()) == ["etapa_1"], "solo la etapa 1: arma solo esa")

    # 3. a 9: frena, y no deja nada a medias
    def frena(args, out, mesa, d):
        r = correr(a.script, args)
        ok(r.returncode != 0 and "FRENO" in (r.stdout + r.stderr) and not (T / out).exists() and not (T / mesa).exists()
           and not (T / (out + ".parcial")).exists() and not (T / (mesa + ".parcial")).exists(), d)
    r = correr(a.script, base()); ok(r.returncode != 0 and "ya existen" in r.stdout + r.stderr, "frena si la salida ya existe")
    frena(base(s="0" * 64, out="x3", mesa="y3"), "x3", "y3", "frena si el tar no da su sha256")
    frena(base(so_="0" * 64, out="x4", mesa="y4"), "x4", "y4", "frena si el orden no da su sha256")
    frena(base(sm1="0" * 64, out="x5", mesa="y5"), "x5", "y5", "frena si un manifest.txt no da su sha256")
    t6 = T / "NO_ABRIR_tar_de_mas.tar"; hacer_tar(a.carpeta, t6, extra={"etapa_1/planilla_etapa_1.tsv": b"ficha\n"})
    frena(base(t=t6, out="x6", mesa="y6"), "x6", "y6", "frena si el tar trae un archivo de más (la planilla de la lectora)")
    una = sorted(p.name for p in (a.carpeta / "etapa_1").glob("*.png"))[0]
    t7 = T / "NO_ABRIR_tar_cambiado.tar"; hacer_tar(a.carpeta, t7, cambiar=una)
    frena(base(t=t7, out="x7", mesa="y7"), "x7", "y7", "frena si una imagen del tar cambió")
    frena(base(e="2", out="x8", mesa="y8"), "x8", "y8", "frena si --etapas no es 1 ni 1,2")
    t9 = T / "NO_ABRIR_tar_fuera.tar"; hacer_tar(a.carpeta, t9, extra={"otra/cosa.txt": b"x"})
    frena(base(t=t9, out="x9", mesa="y9"), "x9", "y9", "frena si el tar trae algo fuera de etapa_1/ y etapa_2/")
    o10 = T / "orden_otro.json"; o = json.loads(a.orden.read_text(encoding="utf-8")); o["etapa_1"]["fichas"] = o["etapa_1"]["fichas"][1:]
    o10.write_text(json.dumps(o), encoding="utf-8")
    frena(base(o=o10, so_=sha(o10), out="x10", mesa="y10"), "x10", "y10", "frena si las fichas del tar no son las del orden")

    for c, d in res:
        print(("ok   " if c else "MAL  ") + d)
    print(f"{sum(c for c, _ in res)} de {len(res)} casos ok")


if __name__ == "__main__":
    main()
