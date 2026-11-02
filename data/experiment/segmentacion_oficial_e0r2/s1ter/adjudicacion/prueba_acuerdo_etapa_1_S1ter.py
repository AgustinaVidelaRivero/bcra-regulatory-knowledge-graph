"""Prueba con datos SINTÉTICOS de `acuerdo_etapa_1_S1ter.py` (mesa, 10/10/2026; USD 0). Las marcas las pone este script; la salida no
lleva ids ni marcas reales. Usa solo los ids de la planilla vacía de la etapa 1 (`s1ter/tramo_b/planilla_etapa_1_S1ter.tsv`).

Uso: python3 -B prueba_acuerdo_etapa_1_S1ter.py --planilla-vacia <planilla vacía de la etapa 1> --script <acuerdo_etapa_1_S1ter.py>
       --trabajo <carpeta nueva del scratchpad>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

res: list[tuple[bool, str]] = []
LEC = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")


def ok(c: bool, q: str) -> None:
    res.append((bool(c), q))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def escribir(p: Path, filas: list[dict], cols) -> None:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(cols), delimiter="\t", lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for f in filas:
        w.writerow({c: f.get(c, "") for c in cols})
    p.write_text(s.getvalue(), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("planilla_vacia", "script", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    T = Path(a.trabajo)
    if T.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    T.mkdir(parents=True)
    vacia = list(csv.DictReader(open(a.planilla_vacia, encoding="utf-8"), delimiter="\t"))
    ids = [f["ficha"] for f in vacia]
    ok(len(ids) == 90 and ids[:19] == [f"E1-{k:03d}" for k in range(1, 20)], "la planilla vacía tiene 90 ids y empieza en E1-001")
    lec = {i: {"ficha": i, "marca": "correcta"} for i in ids}
    aut = {i: {"ficha": i, "marca": "correcta"} for i in ids}
    # dentro de las 19 primeras: 2 marcas distintas y 1 «las dos error» con clase igual
    lec["E1-002"]["marca"] = "error"; lec["E1-002"]["clase"] = "corte"
    aut["E1-005"]["marca"] = "dudosa"
    for i in ("E1-010",):
        lec[i].update(marca="error", clase="corte"); aut[i].update(marca="error", clase="corte")
    # fuera de las 19: 3 marcas distintas y 2 «las dos error», una con clase distinta
    lec["E1-030"]["marca"] = "dudosa"
    aut["E1-040"].update(marca="error", clase="limpieza")
    lec["E1-050"].update(marca="error", clase="limpieza")
    lec["E1-060"].update(marca="error", clase="corte"); aut["E1-060"].update(marca="error", clase="corte")
    lec["E1-070"].update(marca="error", clase="corte"); aut["E1-070"].update(marca="error", clase="limpieza")
    escribir(T / "lectora.tsv", [lec[i] for i in ids], LEC)
    escribir(T / "autora.tsv", [aut[i] for i in ids], ADJ)
    base = [sys.executable, "-B", a.script, "--planilla-1", T / "lectora.tsv", "--sha-planilla-1", sha(T / "lectora.tsv"),
            "--pasada-1-1", T / "autora.tsv", "--sha-pasada-1-1", sha(T / "autora.tsv")]
    corr = lambda args: subprocess.run([str(x) for x in args], capture_output=True, text=True)
    r = corr(base + ["--out", T / "acuerdo.json"])
    ok(r.returncode == 0, "el script corre")
    j = json.loads((T / "acuerdo.json").read_text(encoding="utf-8"))
    ok(j["las_90"]["fichas"] == 90 and j["las_90"]["marca_igual"] == 85, "las 90: 5 marcas distintas, 85 iguales")
    ok(j["sin_las_19_primeras"]["fichas"] == 71 and j["sin_las_19_primeras"]["marca_igual"] == 68,
       "sin las 19 primeras: 71 fichas, 3 marcas distintas, 68 iguales")
    ok(j["sin_las_19_primeras"]["excluidas"] == [f"E1-{k:03d}" for k in range(1, 20)], "las excluidas son E1-001 a E1-019")
    ok(j["las_90"]["las_dos_error"] == 3 and j["las_90"]["clase_igual_entre_las_dos_error"] == 2,
       "las 90: 3 con las dos error, 2 con la misma clase")
    ok(j["sin_las_19_primeras"]["las_dos_error"] == 2 and j["sin_las_19_primeras"]["clase_igual_entre_las_dos_error"] == 1,
       "sin las 19: 2 con las dos error, 1 con la misma clase")
    ok(j["las_90"]["pares_lectora_autora"].get("error|correcta") == 2 and j["las_90"]["pares_lectora_autora"].get("correcta|error") == 1,
       "los pares (lectora, autora) se cuentan bien")
    # rechazos, sin escribir nada
    r = corr(base[:10] + ["0" * 64] + ["--out", T / "malo1.json"])
    ok(r.returncode != 0 and not (T / "malo1.json").exists(), "una pasada 1 que no da su sello se rechaza sin escribir nada")
    escribir(T / "autora_89.tsv", [aut[i] for i in ids[:-1]], ADJ)
    r = corr(base[:8] + [T / "autora_89.tsv", "--sha-pasada-1-1", sha(T / "autora_89.tsv"), "--out", T / "malo2.json"])
    ok(r.returncode != 0 and not (T / "malo2.json").exists(), "una pasada 1 sin las 90 fichas se rechaza sin escribir nada")
    rep = [aut[i] for i in ids]; rep[1] = dict(rep[0])
    escribir(T / "autora_rep.tsv", rep, ADJ)
    r = corr(base[:8] + [T / "autora_rep.tsv", "--sha-pasada-1-1", sha(T / "autora_rep.tsv"), "--out", T / "malo3.json"])
    ok(r.returncode != 0 and not (T / "malo3.json").exists(), "una ficha repetida se rechaza sin escribir nada")
    mala = [dict(aut[i]) for i in ids]; mala[0]["marca"] = "quizas"
    escribir(T / "autora_mala.tsv", mala, ADJ)
    r = corr(base[:8] + [T / "autora_mala.tsv", "--sha-pasada-1-1", sha(T / "autora_mala.tsv"), "--out", T / "malo4.json"])
    ok(r.returncode != 0 and not (T / "malo4.json").exists(), "una marca no válida se rechaza sin escribir nada")
    r = corr(base + ["--out", T / "acuerdo.json"])
    ok(r.returncode != 0, "no pisa una salida que ya existe")
    for b, q in res:
        print(("ok   " if b else "MAL  ") + q)
    print(f"{sum(b for b, _ in res)} de {len(res)} controles ok")
    sys.exit(0 if all(b for b, _ in res) else 1)


if __name__ == "__main__":
    main()
