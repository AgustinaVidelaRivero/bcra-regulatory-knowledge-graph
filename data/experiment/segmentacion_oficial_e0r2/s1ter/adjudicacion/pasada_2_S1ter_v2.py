"""U-SEG-OFICIAL, S1-ter: pasada 2 de la adjudicación y TSV final, versión 2 (mesa, 10/10/2026; USD 0). Fijado antes de armar la
pasada 1 nueva de la etapa 1. Reemplaza a la versión sellada a las 18:26:49 (archivada en los reemplazados del paquete de la mesa).

Decisión de la autora del 10/10/2026 (hoja de ruta de la mesa, §54).
- **Pasada 2:** solo en las fichas donde la marca de la autora, su `la_que_sigue` o su `herencia` no coinciden con la lectora, ve la
  marca y la nota de la lectora y decide la marca final. Una nota de la lectora sobre la unidad que sigue o sobre lo heredado cuenta
  como señal.
- El TSV de adjudicación es la pasada 1 corregida por la pasada 2. Lo lee `aplicar_adjudicacion_S1ter.py` sin cambios.
- El acuerdo entre la lectora y la pasada 1 se calcula después de la adjudicación, como dato para la tesis.

Regla de selección (decisión de la autora del 10/10/2026, hoja §56; reemplaza la propuesta de la mesa del §54). Va a la pasada 2 toda
ficha en la que se dé al menos una de estas condiciones:
- a. la marca de la autora (pasada 1) y la de la lectora no coinciden;
- b. las dos marcaron `error`, pero una lo clasificó como de corte y la otra como de limpieza;
- c. la lectora dejó una nota, en cualquiera de las dos etapas, aunque la marca coincida;
- d. en la etapa 2, la autora marcó `la_que_sigue` o `herencia` como `error`.
La subclase no se compara: queda la de la pasada 1. Las notas de la lectora no se clasifican: van a la pasada 2 tal cual.

Subcomandos:
- `seleccionar`: lee la pasada 1 sellada (con su sha256) y las planillas selladas de la lectora (con sus sha256). Escribe, por etapa,
  `adjudicacion_pasada_2_etapa_N.tsv`, con solo las fichas seleccionadas. Las columnas del TSV de adjudicación van con los valores de
  la pasada 1, para que la autora las corrija, y después van, solo para leer, `lectora_marca`, `lectora_clase`, `lectora_subclase`,
  `lectora_subclase_adicional`, `lectora_limpieza` y `lectora_nota`.
- `armar`: lee la pasada 1 y la pasada 2 selladas (con sus sha256) y las planillas de la lectora. Escribe, por etapa,
  `adjudicacion_etapa_N.tsv`, que es la pasada 1 con las filas de la pasada 2 en lugar de las suyas (solo las columnas del TSV de
  adjudicación), y `acuerdo_lectora_pasada_1_S1ter.json` con el acuerdo, que se calcula recién acá.

Uso:
  python3 -B pasada_2_S1ter.py seleccionar --pasada-1-1 <tsv> --sha-pasada-1-1 <sha> --pasada-1-2 <tsv> --sha-pasada-1-2 <sha>
      --planilla-1 <tsv> --sha-planilla-1 <sha> --planilla-2 <tsv> --sha-planilla-2 <sha> --out <carpeta nueva>
  python3 -B pasada_2_S1ter.py armar (lo mismo) --pasada-2-1 <tsv> --sha-pasada-2-1 <sha> --pasada-2-2 <tsv> --sha-pasada-2-2 <sha>
      --out <carpeta nueva>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
LEC = ("marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
MARCAS = ("correcta", "error", "dudosa")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def leer(p: Path, sh: str, cols: tuple, que: str) -> list[dict]:
    if sha(p) != sh:
        sys.exit(f"FRENO: {que} no da su sha256 sellado")
    with open(p, encoding="utf-8") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        if tuple(r.fieldnames or ()) [: len(cols)] != cols:
            sys.exit(f"FRENO: {que} no tiene las columnas esperadas")
        filas = list(r)
    ids = [f["ficha"] for f in filas]
    if len(ids) != len(set(ids)):
        sys.exit(f"FRENO: {que} repite fichas")
    return filas


def validar_adj(filas: list[dict], etapa: int, que: str) -> None:
    for f in filas:
        if f["marca"] not in MARCAS:
            sys.exit(f"FRENO: {que}: marca no válida en {f['ficha']}")
        if etapa == 1 and any(f[c] for c in ("la_que_sigue", "clase_que_sigue", "subclase_que_sigue", "herencia")):
            sys.exit(f"FRENO: {que}: la etapa 1 no lleva unidad que sigue ni herencia ({f['ficha']})")
        for c in ("la_que_sigue", "herencia"):
            if f[c] not in ("", "error"):
                sys.exit(f"FRENO: {que}: {c} no válida en {f['ficha']}")


def tsv(filas: list[dict], cols) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(cols), delimiter="\t", lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for f in filas:
        w.writerow({c: f.get(c, "") for c in cols})
    return s.getvalue()


def senal_autora(f: dict) -> bool:
    return f["la_que_sigue"] == "error" or f["herencia"] == "error"


def condiciones(f: dict, l: dict, etapa: int) -> list[str]:
    c = []
    if f["marca"] != l["marca"]:
        c.append("a")
    if f["marca"] == "error" and l["marca"] == "error" and f["clase"] != l["clase"]:
        c.append("b")
    if l["nota"].strip():
        c.append("c")
    if etapa == 2 and senal_autora(f):
        c.append("d")
    return c


def seleccion(p1: list[dict], lec: dict[str, dict], etapa: int) -> list[str]:
    return [f["ficha"] for f in p1 if condiciones(f, lec[f["ficha"]], etapa)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=("seleccionar", "armar"))
    for k in ("pasada_1_1", "sha_pasada_1_1", "pasada_1_2", "sha_pasada_1_2", "planilla_1", "sha_planilla_1", "planilla_2",
              "sha_planilla_2", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    for k in ("pasada_2_1", "sha_pasada_2_1", "pasada_2_2", "sha_pasada_2_2"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, default=None)
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        sys.exit("FRENO: la carpeta de salida ya existe")
    p1 = {1: leer(Path(a.pasada_1_1), a.sha_pasada_1_1, ADJ, "la pasada 1 de la etapa 1"),
          2: leer(Path(a.pasada_1_2), a.sha_pasada_1_2, ADJ, "la pasada 1 de la etapa 2")}
    lec = {1: {f["ficha"]: f for f in leer(Path(a.planilla_1), a.sha_planilla_1, ("ficha", "paginas") + LEC, "la planilla 1")},
           2: {f["ficha"]: f for f in leer(Path(a.planilla_2), a.sha_planilla_2, ("ficha", "paginas") + LEC, "la planilla 2")}}
    for n in (1, 2):
        validar_adj(p1[n], n, f"la pasada 1 de la etapa {n}")
        faltan = [f["ficha"] for f in p1[n] if f["ficha"] not in lec[n]]
        if faltan:
            sys.exit(f"FRENO: la pasada 1 de la etapa {n} trae fichas que no están en la planilla de la lectora")
    sel = {n: seleccion(p1[n], lec[n], n) for n in (1, 2)}
    if a.modo == "seleccionar":
        out.mkdir(parents=True)
        for n in (1, 2):
            filas = []
            for f in p1[n]:
                if f["ficha"] in sel[n]:
                    g = dict(f)
                    g.update({f"lectora_{c}": lec[n][f["ficha"]][c] for c in LEC})
                    filas.append(g)
            (out / f"adjudicacion_pasada_2_etapa_{n}.tsv").write_text(tsv(filas, ADJ + tuple(f"lectora_{c}" for c in LEC)),
                                                                     encoding="utf-8")
        print("pasada 2 escrita")
        return
    # armar
    if not all((a.pasada_2_1, a.sha_pasada_2_1, a.pasada_2_2, a.sha_pasada_2_2)):
        sys.exit("FRENO: armar necesita las dos pasadas 2 con su sha256")
    p2 = {1: leer(Path(a.pasada_2_1), a.sha_pasada_2_1, ADJ, "la pasada 2 de la etapa 1"),
          2: leer(Path(a.pasada_2_2), a.sha_pasada_2_2, ADJ, "la pasada 2 de la etapa 2")}
    for n in (1, 2):   # todo se valida antes de escribir nada
        validar_adj(p2[n], n, f"la pasada 2 de la etapa {n}")
        if [f["ficha"] for f in p2[n]] != sel[n]:
            sys.exit(f"FRENO: la pasada 2 de la etapa {n} no trae exactamente las fichas seleccionadas, en su orden")
    out.mkdir(parents=True)
    acuerdo = {"nota": "acuerdo entre la lectora y la pasada 1 de la autora, sobre las fichas de la lista (no es una muestra al azar: "
                       "la lista incluye todos los errores, las dudosas y las correctas con nota de la lectora)"}
    for n in (1, 2):
        reemplazo = {f["ficha"]: f for f in p2[n]}
        final = [reemplazo.get(f["ficha"], f) for f in p1[n]]
        (out / f"adjudicacion_etapa_{n}.tsv").write_text(tsv(final, ADJ), encoding="utf-8")
        pares = Counter((lec[n][f["ficha"]]["marca"], f["marca"]) for f in p1[n])
        a_n = {"fichas": len(p1[n]), "marca_igual": sum(v for (x, y), v in pares.items() if x == y),
               "pares_lectora_pasada_1": {f"{x}|{y}": v for (x, y), v in sorted(pares.items())},
               "a_la_pasada_2": len(sel[n]), "cambiadas_en_la_pasada_2": sum(1 for f in p2[n] if any(
                   f[c] != next(g for g in p1[n] if g["ficha"] == f["ficha"])[c] for c in ADJ[1:]))}
        a_n["por_condicion"] = dict(sorted(Counter(c for f in p1[n] for c in condiciones(f, lec[n][f["ficha"]], n)).items()))
        if n == 2:
            s = Counter((bool(lec[n][f["ficha"]]["nota"].strip()), senal_autora(f)) for f in p1[n])
            a_n["senal_nota_lectora_vs_autora"] = {f"nota_{x}|autora_{y}": v for (x, y), v in sorted(s.items())}
        acuerdo[f"etapa_{n}"] = a_n
    (out / "acuerdo_lectora_pasada_1_S1ter.json").write_text(json.dumps(acuerdo, ensure_ascii=False, indent=1) + "\n",
                                                            encoding="utf-8")
    print("adjudicación y acuerdo escritos")


if __name__ == "__main__":
    main()
