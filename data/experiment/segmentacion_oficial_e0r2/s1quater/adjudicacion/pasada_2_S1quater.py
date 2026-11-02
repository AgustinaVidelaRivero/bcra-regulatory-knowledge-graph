"""U-SEG-OFICIAL, S1-quater: selección de la pasada 2 de la adjudicación y TSV final (mesa, 13/10/2026; USD 0). Sellado antes de que
la autora abra la pasada 1 (`sello_scripts_adjudicacion_S1quater_mesa.txt`).

Adaptado de `s1ter/adjudicacion/pasada_2_S1ter_v2.py`, con la misma regla de selección (decisión de la autora del 10/10/2026, hoja de
ruta de la mesa, §56). Va a la pasada 2 toda ficha en la que se dé al menos una de estas condiciones:
- a. la marca de la autora (pasada 1) y la de la lectora no coinciden;
- b. las dos marcaron `error`, pero una lo clasificó como de corte y la otra como de limpieza;
- c. la lectora dejó una nota, en cualquiera de las dos etapas, aunque la marca coincida;
- d. en la etapa 2, la autora marcó `la_que_sigue` o `herencia` como `error`.
La subclase no se compara: queda la de la pasada 1. Las notas de la lectora no se clasifican: van a la pasada 2 tal cual.

Lo que cambia respecto de S1-ter:
- **El control de forma va adentro** (en S1-ter fue un control aparte, agregado antes de `armar`; hoja de la mesa §66). Las planillas de
  la autora se leen por renglones y tabulaciones, sin el módulo csv: sin retorno de carro, con salto final, cada renglón con las
  columnas del encabezado y sin comillas dobles en las columnas de la autora (de `marca` a `nota`). Las planillas de la lectora se leen
  con el módulo csv, como en S1-ter, y frenan si un renglón no da las columnas del encabezado.
- **La planilla de la pasada 2 se escribe sin comillas** (tabulaciones, tal cual): si un valor de la lectora trae una tabulación o un
  salto de renglón, frena antes de escribir.
- **Los nombres son de S1-quater,** y el acuerdo va a `acuerdo_lectora_pasada_1_S1quater.json`.

Subcomandos:
- `seleccionar`: lee las pasadas 1 y las planillas de la lectora, con sus sha256. Escribe, por etapa,
  `adjudicacion_pasada_2_etapa_N.tsv`, con solo las fichas seleccionadas: las columnas del TSV de adjudicación con los valores de la
  pasada 1, para que la autora las corrija, y después, solo para leer, `lectora_marca`, `lectora_clase`, `lectora_subclase`,
  `lectora_subclase_adicional`, `lectora_limpieza` y `lectora_nota`.
- `armar`: además lee las dos pasadas 2 selladas. Escribe, por etapa, `adjudicacion_etapa_N.tsv` (la pasada 1 con las filas de la
  pasada 2 en lugar de las suyas, solo las columnas del TSV de adjudicación), y el acuerdo, que se calcula recién acá.
Todo se valida antes de escribir nada; la carpeta de salida no puede existir.

Uso:
  python3 -B pasada_2_S1quater.py seleccionar --pasada-1-1 <tsv> --sha-pasada-1-1 <sha> --pasada-1-2 <tsv> --sha-pasada-1-2 <sha>
      --planilla-1 <tsv> --sha-planilla-1 <sha> --planilla-2 <tsv> --sha-planilla-2 <sha> --out <carpeta nueva>
  python3 -B pasada_2_S1quater.py armar (lo mismo) --pasada-2-1 <tsv> --sha-pasada-2-1 <sha> --pasada-2-2 <tsv> --sha-pasada-2-2 <sha>
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
DE_LA_AUTORA = ADJ[1:]
LEC = ("marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
P2 = ADJ + tuple(f"lectora_{c}" for c in LEC)
MARCAS = ("correcta", "error", "dudosa")


def freno(m: str) -> None:
    sys.exit(f"FRENO: {m}")


def bytes_con_sha(p: Path, sh: str, que: str) -> bytes:
    datos = p.read_bytes()
    if hashlib.sha256(datos).hexdigest() != sh:
        freno(f"{que} no da su sha256 sellado")
    return datos


def leer_autora(p: Path, sh: str, cab: tuple, que: str) -> list[dict]:
    texto = bytes_con_sha(p, sh, que).decode("utf-8")
    if "\r" in texto or not texto.endswith("\n"):
        freno(f"{que}: fin de renglón inesperado")
    renglones = texto[:-1].split("\n")
    if tuple(renglones[0].split("\t")) != cab:
        freno(f"{que} no tiene el encabezado esperado")
    filas = []
    for k, r in enumerate(renglones[1:], 2):
        v = r.split("\t")
        if len(v) != len(cab):
            freno(f"{que}: el renglón {k} no tiene las {len(cab)} columnas del encabezado")
        f = dict(zip(cab, v))
        if any('"' in f[c] for c in DE_LA_AUTORA):
            freno(f"{que}: el renglón {k} trae comillas dobles en una columna de la autora")
        filas.append(f)
    ids = [f["ficha"] for f in filas]
    if len(ids) != len(set(ids)):
        freno(f"{que} repite fichas")
    return filas


def leer_lectora(p: Path, sh: str, que: str) -> dict[str, dict]:
    texto = bytes_con_sha(p, sh, que).decode("utf-8")
    r = csv.DictReader(io.StringIO(texto, newline=""), delimiter="\t")
    if tuple(r.fieldnames or ())[:2 + len(LEC)] != ("ficha", "paginas") + LEC:
        freno(f"{que} no tiene las columnas esperadas")
    filas = list(r)
    if any(None in f or any(v is None for v in f.values()) for f in filas) or len(filas) != texto.count("\n") - 1:
        freno(f"{que}: un renglón no da las columnas del encabezado")
    ids = [f["ficha"] for f in filas]
    if len(ids) != len(set(ids)):
        freno(f"{que} repite fichas")
    return {f["ficha"]: f for f in filas}


def validar_adj(filas: list[dict], etapa: int, que: str) -> None:
    for f in filas:
        if f["marca"] not in MARCAS:
            freno(f"{que}: marca no válida en {f['ficha']}")
        if etapa == 1 and any(f[c] for c in ("la_que_sigue", "clase_que_sigue", "subclase_que_sigue", "herencia")):
            freno(f"{que}: la etapa 1 no lleva unidad que sigue ni herencia ({f['ficha']})")
        for c in ("la_que_sigue", "herencia"):
            if f[c] not in ("", "error"):
                freno(f"{que}: {c} no válida en {f['ficha']}")


def tsv_sin_comillas(filas: list[dict], cols: tuple) -> str:
    renglones = ["\t".join(cols)]
    for f in filas:
        v = [f.get(c, "") for c in cols]
        if any(ch in x for x in v for ch in "\t\n\r"):
            freno(f"un valor de {f['ficha']} trae una tabulación o un salto de renglón")
        renglones.append("\t".join(v))
    return "\n".join(renglones) + "\n"


def tsv(filas: list[dict], cols: tuple) -> str:
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
        freno("la carpeta de salida ya existe")
    p1 = {n: leer_autora(Path(getattr(a, f"pasada_1_{n}")), getattr(a, f"sha_pasada_1_{n}"), ADJ, f"la pasada 1 de la etapa {n}")
          for n in (1, 2)}
    lec = {n: leer_lectora(Path(getattr(a, f"planilla_{n}")), getattr(a, f"sha_planilla_{n}"), f"la planilla {n}") for n in (1, 2)}
    for n in (1, 2):
        validar_adj(p1[n], n, f"la pasada 1 de la etapa {n}")
        if sorted(f["ficha"] for f in p1[n]) != sorted(lec[n]):
            freno(f"la pasada 1 de la etapa {n} no trae las mismas fichas que la planilla de la lectora")
    sel = {n: seleccion(p1[n], lec[n], n) for n in (1, 2)}
    if a.modo == "seleccionar":
        textos = {}
        for n in (1, 2):
            filas = [dict(f) | {f"lectora_{c}": lec[n][f["ficha"]][c] for c in LEC} for f in p1[n] if f["ficha"] in sel[n]]
            textos[n] = tsv_sin_comillas(filas, P2)
        out.mkdir(parents=True)
        for n in (1, 2):
            (out / f"adjudicacion_pasada_2_etapa_{n}.tsv").write_text(textos[n], encoding="utf-8")
        print("pasada 2 escrita")
        return
    if not all((a.pasada_2_1, a.sha_pasada_2_1, a.pasada_2_2, a.sha_pasada_2_2)):
        freno("armar necesita las dos pasadas 2 con su sha256")
    p2 = {n: leer_autora(Path(getattr(a, f"pasada_2_{n}")), getattr(a, f"sha_pasada_2_{n}"), P2, f"la pasada 2 de la etapa {n}")
          for n in (1, 2)}
    for n in (1, 2):   # todo se valida antes de escribir nada
        validar_adj(p2[n], n, f"la pasada 2 de la etapa {n}")
        if [f["ficha"] for f in p2[n]] != sel[n]:
            freno(f"la pasada 2 de la etapa {n} no trae exactamente las fichas seleccionadas, en su orden")
    textos, acuerdo = {}, {"nota": "acuerdo entre la lectora y la pasada 1 de la autora, sobre todas las fichas de cada etapa"}
    for n in (1, 2):
        reemplazo = {f["ficha"]: f for f in p2[n]}
        textos[n] = tsv([reemplazo.get(f["ficha"], f) for f in p1[n]], ADJ)
        pares = Counter((lec[n][f["ficha"]]["marca"], f["marca"]) for f in p1[n])
        p1_de = {f["ficha"]: f for f in p1[n]}
        a_n = {"fichas": len(p1[n]), "marca_igual": sum(v for (x, y), v in pares.items() if x == y),
               "pares_lectora_pasada_1": {f"{x}|{y}": v for (x, y), v in sorted(pares.items())},
               "a_la_pasada_2": len(sel[n]),
               "cambiadas_en_la_pasada_2": sum(1 for f in p2[n] if any(f[c] != p1_de[f["ficha"]][c] for c in ADJ[1:])),
               "por_condicion": dict(sorted(Counter(c for f in p1[n] for c in condiciones(f, lec[n][f["ficha"]], n)).items()))}
        if n == 2:
            s = Counter((bool(lec[n][f["ficha"]]["nota"].strip()), senal_autora(f)) for f in p1[n])
            a_n["senal_nota_lectora_vs_autora"] = {f"nota_{x}|autora_{y}": v for (x, y), v in sorted(s.items())}
        acuerdo[f"etapa_{n}"] = a_n
    out.mkdir(parents=True)
    for n in (1, 2):
        (out / f"adjudicacion_etapa_{n}.tsv").write_text(textos[n], encoding="utf-8")
    (out / "acuerdo_lectora_pasada_1_S1quater.json").write_text(json.dumps(acuerdo, ensure_ascii=False, indent=1) + "\n",
                                                               encoding="utf-8")
    print("adjudicación y acuerdo escritos")


if __name__ == "__main__":
    main()
