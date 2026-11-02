"""U-SEG-OFICIAL, S1-quater: prueba de `cifra_control_sin_vistas_S1quater.py` (mesa, 14/10/2026; USD 0), con datos sintéticos: no usa
nada de la lectura de S1-quater ni de S1-ter. Corre el script en otro proceso y recalcula aparte la cifra sin las excluidas. La salida
trae solo «ok» o «MAL» por caso.

Uso: python3 -I -B prueba_cifra_control_S1quater.py --scripts <carpeta con cifras_lectura y cifra_control> --trabajo <carpeta nueva>
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
from collections import Counter
from pathlib import Path

COLS = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
res: list[tuple[bool, str]] = []


def ok(c, d):
    res.append((bool(c), d))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def con_csv(filas) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(COLS), delimiter="\t", lineterminator="\n")
    w.writeheader()
    for f in filas:
        w.writerow({c: f.get(c, "") for c in COLS})
    return s.getvalue()


def wilson(k, n):
    z = 1.959963984540054
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(p + z * z / (2 * n) - c) / (1 + z * z / n), (p + z * z / (2 * n) + c) / (1 + z * z / n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripts", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    a = ap.parse_args()
    S, T = a.scripts, a.trabajo
    if T.exists():
        sys.exit("FRENO: la carpeta de trabajo ya existe")
    T.mkdir(parents=True)
    CTL = S / "cifra_control_sin_vistas_S1quater.py"
    rng = random.Random("prueba-cifra-control-S1quater")
    estr = ["vigente"] * 40 + ["marcadores"] * 10 + ["sin_raiz"] * 40
    rng.shuffle(estr)
    e1 = [{"id_opaco": f"E1-{k:03d}", "id": f"doc{k % 7}::{k}.1", "poblacion": "cortes", "estrato": estr[k - 1]} for k in range(1, 91)]
    e2 = [{"id_opaco": f"E2-{k:03d}", "id": f"reg{k}::1", "poblacion": "regresion", "unidades_calificadas": [f"reg{k}::1"]}
          for k in range(1, 9)]
    (T / "orden.json").write_text(json.dumps({"etapa_1": {"fichas": e1}, "etapa_2": {"fichas": e2}}), encoding="utf-8")
    (T / "pob.json").write_text(json.dumps({"cortes": {"vigente": {"peso": 0.55}, "marcadores": {"peso": 0.05},
                                                       "sin_raiz": {"peso": 0.40}}}), encoding="utf-8")
    (T / "lim.json").write_text(json.dumps({"cortes": {"limites_declarados": {"unidades": []}}}), encoding="utf-8")

    def marca():
        m = rng.choices(["correcta", "error", "dudosa"], [80, 15, 5])[0]
        f = {"marca": m, "clase": "", "subclase": "", "subclase_adicional": "", "limpieza": "", "nota": ""}
        if m == "error":
            f.update(clase="corte", subclase="termina_fuera") if rng.random() < 0.7 else f.update(clase="limpieza", subclase="restos_pie")
        return f

    p1 = [{"ficha": x["id_opaco"], "paginas": "1"} | marca() for x in e1]
    p2 = [{"ficha": x["id_opaco"], "paginas": "2"} | marca() for x in e2]
    (T / "p1.tsv").write_text(con_csv(p1), encoding="utf-8")
    (T / "p2.tsv").write_text(con_csv(p2), encoding="utf-8")
    excl = sorted(rng.sample([x["id_opaco"] for x in e1], 26))
    (T / "excl.json").write_text(json.dumps({"etapa_1": {"fichas": excl}}), encoding="utf-8")
    sh = {k: sha(T / k) for k in ("orden.json", "pob.json", "lim.json", "excl.json")}

    def args(**c):
        b = {"orden": T / "orden.json", "sha-orden": sh["orden.json"], "poblaciones": T / "pob.json",
             "sha-poblaciones": sh["pob.json"], "limites": T / "lim.json", "sha-limites": sh["lim.json"], "planilla-1": T / "p1.tsv",
             "planilla-2": T / "p2.tsv", "excluir": T / "excl.json", "sha-excluir": sh["excl.json"], "out": T / "control.json"}
        b.update({k.replace("_", "-"): v for k, v in c.items()})
        return [x for k, v in b.items() for x in (f"--{k}", v)]

    r = subprocess.run([sys.executable, "-I", "-B", str(CTL)] + [str(x) for x in args()], capture_output=True, text=True)
    ok(r.returncode == 0, "la cifra de control corre")
    d = json.loads((T / "control.json").read_text(encoding="utf-8"))
    quedan = [f for f in p1 if f["ficha"] not in set(excl)]
    ok(d["excluidas"]["cuantas"] == 26 and d["leidas_que_quedan"]["cuantas"] == 64, "salen 26 y quedan 64")
    ok(d["leidas_que_quedan"]["por_estrato"] == dict(sorted(Counter(e1[int(f["ficha"][3:]) - 1]["estrato"] for f in quedan).items())),
       "las que quedan, por estrato, recalculadas aparte")
    for modo, dud in (("dudosas_como_correctas", False), ("dudosas_como_error", True)):
        e = sum(1 for f in quedan if (f["marca"] == "error" and f["clase"] == "corte") or (dud and f["marca"] == "dudosa"))
        w = wilson(64 - e, 64)
        x = d["cifra_de_control"][modo]
        ok(x["leidas"] == 64 and x["errores_de_corte"] == e and all(abs(u - v) < 1e-12 for u, v in zip(x["wilson95"], w))
           and x["llega_al_piso"] == (w[0] >= 0.90), f"{modo}: la cifra sin las 26, recalculada aparte")
    ok(d["control_declarado"] is True and "90" in d["no_decide"], "la salida dice que es control y que no decide")

    def frena(c: dict, que: str, msg: str, antes=None):
        out = c.pop("out", T / f"no_{len(res)}.json")
        previo = out.read_bytes() if out.exists() else None
        if antes:
            antes()
        r = subprocess.run([sys.executable, "-I", "-B", str(CTL)] + [str(x) for x in args(out=out, **c)], capture_output=True, text=True)
        ok(r.returncode != 0 and "FRENO" in r.stderr and msg in r.stderr and (out.read_bytes() if out.exists() else None) == previo,
           f"frena: {que}")

    frena({"out": T / "control.json"}, "la salida ya existe", "ya existe")
    frena({"sha_excluir": "0" * 64}, "la lista de excluidas no da su sha256", "excluir: no da su sha256")
    frena({"sha_orden": "0" * 64}, "el orden no da su sha256", "orden: no da su sha256")
    for nombre, lista, que in (("excl_e2.json", excl[:-1] + ["E2-001"], "una excluida de la etapa 2"),
                               ("excl_dup.json", excl[:-1] + [excl[0]], "una excluida repetida"),
                               ("excl_fuera.json", excl[:-1] + ["E1-999"], "una excluida fuera del orden")):
        (T / nombre).write_text(json.dumps({"etapa_1": {"fichas": lista}}), encoding="utf-8")
        frena({"excluir": T / nombre, "sha_excluir": sha(T / nombre)}, que, "no son fichas distintas de la etapa 1")
    malo = [dict(f) for f in p1]
    malo[0]["marca"] = "quizas"
    (T / "p1_malo.tsv").write_text(con_csv(malo), encoding="utf-8")
    frena({"planilla_1": T / "p1_malo.tsv"}, "una planilla no válida", "no son válidas")
    for c, dsc in res:
        print(("ok   " if c else "MAL  ") + dsc)
    print(f"{sum(c for c, _ in res)} de {len(res)}")
    sys.exit(0 if all(c for c, _ in res) else 1)


if __name__ == "__main__":
    main()
