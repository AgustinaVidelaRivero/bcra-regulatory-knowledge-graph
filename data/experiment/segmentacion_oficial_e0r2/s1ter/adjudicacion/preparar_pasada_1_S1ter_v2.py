"""U-SEG-OFICIAL, S1-ter: material de la pasada 1 de la adjudicación, versión 2 (mesa, 10/10/2026; USD 0). Fijado antes de armar la
pasada 1 nueva de la etapa 1. Reemplaza a la versión sellada a las 18:26:49 (archivada en los reemplazados del paquete de la mesa).

Decisión de la autora del 10/10/2026 (hoja de ruta de la mesa, §54): adjudica en dos pasadas sin ver primero la marca de la lectora.
En la pasada 1 ve, de cada etapa, las fichas de su lista mezcladas en un orden al azar, sin la marca, la clase, la subclase ni la nota
de la lectora, cada una con su ficha y sus imágenes, y una planilla vacía con las columnas del TSV de adjudicación.

- **Etapa 1 (decisión de la autora del 10/10/2026, hoja §56, tomada sin haber visto nada de la lectura): las 90 fichas, todas.** El
  tamaño de una lista armada con las marcas de la lectora dejaría ver si el piso está en riesgo; así, además, ninguna ficha que la
  lectora dio por correcta queda sin que la mire una persona, y el acuerdo se mide sobre las 90. La semilla de las 20 correctas de la
  etapa 1 (`U-SEG-OFICIAL:cortes:S1-ter:revision`) queda registrada y sin uso.
- **Etapa 2: la lista,** que sale de `lista_para_la_autora_S1ter.py`, commiteado, corrido sin cambios por su línea de comandos: los
  errores y las dudosas (y las fichas con la columna `limpieza`), las correctas con nota y las 5 correctas de control sorteadas con su
  semilla de revisión. El conjunto es la unión de esas secciones. Queda declarado que es casi toda de fichas señaladas por la lectora
  (solo 5 de control) y que su acuerdo se mide sobre una muestra elegida según esas marcas.
- Orden: `random.Random(f"U-SEG-OFICIAL:adjudicacion:S1-ter:{etapa}").sample(sorted(ids), len(ids))`, con `etapa` = `etapa_1` o
  `etapa_2`.
- Escribe dos cosas:
  - el material de la autora: por etapa, las fichas en ese orden (cada bloque, copiado tal cual de `fichas_etapa_N.md`), sus
    imágenes, la planilla vacía, un LEEME y un `manifest.txt` legible por `shasum -a 256 -c`;
  - el registro de la mesa: el orden (solo ids opacos), y aparte, con nombre `NO_ABRIR_…`, la lista con las marcas de la lectora y la
    salida del script de la lista, que la autora no abre antes de sellar su pasada 1.
- Controla que las planillas de la lectora den el sha256 de sus sellos, que el orden de lectura dé su sha256 sellado, y que en el
  material de la autora no aparezca ninguna nota de la lectora ni ningún valor de sus columnas de marca.

Uso: python3 -B preparar_pasada_1_S1ter.py --s1ter <carpeta s1ter> --carpeta-lectora <carpeta con etapa_1/ y etapa_2/>
       --sha-planilla-1 <sha256 sellado> --sha-planilla-2 <sha256 sellado> --sha-orden <sha256 sellado>
       --out-autora <carpeta nueva> --out-mesa <carpeta nueva>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
SEMILLA = "U-SEG-OFICIAL:adjudicacion:S1-ter:{etapa}"
LEEME = """# Adjudicación de la lectura de segmentación: {etapa}, pasada 1

Las fichas de `{fichas}` están en un orden al azar. Cada una es la misma ficha que vio la lectura, con sus imágenes en esta carpeta.
No se muestra ninguna marca de la lectura.

**Criterio** (mandato de la unidad, `docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md:284-292`):
- Una unidad es correcta si: (1) empieza donde empieza su punto; (2) termina donde termina; (3) no trae texto de otro punto ni restos de
  encabezados o pies de página; (4) no le falta texto propio; y (5) su número es el del punto.
- Tres reglas para los casos dudosos. Una parte de una unidad partida por tamaño es correcta si corta en un límite de ítem y está
  declarada. Los guiones de silabeo no son error. Un párrafo sin numerar es correcto si cubre exactamente ese párrafo.
- Dos clases de error; cada error lleva su clase y su subclase. De corte: empieza fuera de su punto, termina fuera de su punto, le falta
  texto propio, trae texto de otro punto, o su número no es el del punto. De limpieza: restos de encabezado o restos de pie de página.

**Dónde marcás:** `{planilla}`, una fila por ficha, ya con `ficha`. No cambies esa columna, el orden ni el encabezado. Separador:
tabulación; en ninguna celda va una tabulación ni un salto de renglón.
- `marca`: `correcta`, `error` o `dudosa`.
- `clase` y `subclase`, solo si es `error`. De corte: `empieza_fuera`, `termina_fuera`, `falta_texto_propio`,
  `trae_texto_de_otro_punto` o `numero_equivocado`. De limpieza: `restos_encabezado` o `restos_pie`. `subclase_adicional`: una
  segunda, si hace falta. `limpieza`: `restos_encabezado` o `restos_pie`, si además del corte hay restos.
{extra}- `nota`: lo que quieras dejar dicho.

**Sello**, cuando todas las filas tengan `marca`:
`shasum -a 256 {planilla} > sello_{planilla_base}.txt` y `date '+%Y-%m-%d %H:%M:%S %z' >> sello_{planilla_base}.txt`.
"""
EXTRA_2 = """- `la_que_sigue`: `error` si la unidad que sigue no empieza o no termina donde corresponde según la imagen, con su
  `clase_que_sigue` y su `subclase_que_sigue` (los mismos valores que arriba); vacía si no.
- `herencia`: `error` si el texto heredado (los títulos arriba de la unidad) no corresponde a la página; vacía si no.
"""
EXTRA_1 = """- `la_que_sigue`, `clase_que_sigue`, `subclase_que_sigue` y `herencia` quedan vacías en esta etapa.
"""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bloques(md: str) -> dict[str, str]:
    """Cada bloque de ficha, desde su encabezado `## E…` hasta el siguiente, tal cual."""
    partes = re.split(r"(?m)^(?=## E\d-\d{3}$)", md)
    return {re.match(r"## (E\d-\d{3})", p).group(1): p for p in partes if p.startswith("## E")}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("s1ter", "carpeta_lectora", "sha_planilla_1", "sha_planilla_2", "sha_orden", "out_autora", "out_mesa"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    s1ter, lec, fin_a, fin_m = Path(a.s1ter), Path(a.carpeta_lectora), Path(a.out_autora), Path(a.out_mesa)
    if fin_a.exists() or fin_m.exists():
        sys.exit("FRENO: las carpetas de salida ya existen")
    # se escribe en carpetas «.parcial» y se renombran solo si todos los controles dan; si no, se borran
    out_a, out_m = fin_a.with_name(fin_a.name + ".parcial"), fin_m.with_name(fin_m.name + ".parcial")
    try:
        armar(a, s1ter, lec, out_a, out_m)
    except SystemExit:
        shutil.rmtree(out_a, ignore_errors=True)
        shutil.rmtree(out_m, ignore_errors=True)
        raise
    out_a.rename(fin_a)
    out_m.rename(fin_m)


def armar(a, s1ter: Path, lec: Path, out_a: Path, out_m: Path) -> None:
    if out_a.exists() or out_m.exists():
        sys.exit("FRENO: quedaron carpetas «.parcial» de una corrida anterior")
    plan = {1: lec / "etapa_1" / "planilla_etapa_1.tsv", 2: lec / "etapa_2" / "planilla_etapa_2.tsv"}
    for n, s in ((1, a.sha_planilla_1), (2, a.sha_planilla_2)):
        if sha(plan[n]) != s:
            sys.exit(f"FRENO: la planilla de la etapa {n} no da el sha256 de su sello")
    orden = s1ter / "tramo_b" / "orden_lectura_S1ter.json"
    if sha(orden) != a.sha_orden:
        sys.exit("FRENO: el orden de lectura no da su sha256 sellado")
    out_m.mkdir(parents=True)
    lista_md, lista_js = out_m / "NO_ABRIR_lista_para_la_autora_S1ter.md", out_m / "NO_ABRIR_lista_para_la_autora_S1ter.json"
    r = subprocess.run([sys.executable, "-B", str(s1ter / "scripts" / "lista_para_la_autora_S1ter.py"), "--orden", str(orden),
                        "--sha-orden", a.sha_orden, "--planilla-1", str(plan[1]), "--planilla-2", str(plan[2]),
                        "--out", str(lista_md), "--out-json", str(lista_js)], capture_output=True, text=True)
    (out_m / "NO_ABRIR_salida_lista_para_la_autora_S1ter.txt").write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode != 0:
        sys.exit("FRENO: falló lista_para_la_autora_S1ter.py (ver la salida NO_ABRIR)")
    js = json.loads(lista_js.read_text(encoding="utf-8"))
    lectora = {n: list(csv.DictReader(open(plan[n], encoding="utf-8"), delimiter="\t")) for n in (1, 2)}
    registro = {"version": 2, "semilla": SEMILLA, "planillas_sha256": {"etapa_1": a.sha_planilla_1, "etapa_2": a.sha_planilla_2},
                "orden_lectura_sha256": a.sha_orden,
                "etapa_1_todas": "las 90 fichas (hoja §56); la semilla U-SEG-OFICIAL:cortes:S1-ter:revision queda registrada y sin uso",
                "etapa_2_declarado": "la lista es casi toda de fichas señaladas por la lectora (solo 5 de control); su acuerdo se mide "
                                     "sobre una muestra elegida según esas marcas",
                "etapas": {}}
    out_a.mkdir(parents=True)
    for n in (1, 2):
        e = f"etapa_{n}"
        if n == 1:   # las 90, todas (hoja §56)
            ids = sorted(f["id_opaco"] for f in json.loads(orden.read_text(encoding="utf-8"))["etapa_1"]["fichas"])
            if ids != sorted(x["ficha"] for x in lectora[1]):
                sys.exit("FRENO: las fichas del orden de la etapa 1 no son las de la planilla de la lectora")
        else:
            ids = sorted(set(js[e]["errores_y_dudosas"]) | set(js[e]["correctas_con_nota"]) | set(js[e]["correctas_sorteadas"]))
        semilla = SEMILLA.format(etapa=e)
        orden_p1 = random.Random(semilla).sample(ids, len(ids))
        d = out_a / e
        d.mkdir()
        bl = bloques((lec / e / f"fichas_{e}.md").read_text(encoding="utf-8"))
        fichas = f"fichas_pasada_1_{e}.md"
        cab = f"# Adjudicación de la lectura de segmentación: {e}, pasada 1\n\nFichas en un orden al azar.\n\n"
        (d / fichas).write_text(cab + "".join(bl[i] if bl[i].endswith("\n") else bl[i] + "\n" for i in orden_p1), encoding="utf-8")
        for i in orden_p1:
            for img in sorted((lec / e).glob(f"{i}_p*.png")):
                shutil.copy2(img, d / img.name)
        planilla = f"adjudicacion_pasada_1_{e}.tsv"
        with open(d / planilla, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, delimiter="\t", lineterminator="\n")
            w.writerow(ADJ)
            for i in orden_p1:
                w.writerow([i] + [""] * (len(ADJ) - 1))
        (d / "LEEME.md").write_text(LEEME.format(etapa=e, fichas=fichas, planilla=planilla, planilla_base=planilla[:-4],
                                                 extra=EXTRA_2 if n == 2 else EXTRA_1), encoding="utf-8")
        archivos = sorted(p.name for p in d.iterdir() if p.name != "manifest.txt")
        (d / "manifest.txt").write_text("".join(f"{sha(d / f)}  {f}\n" for f in archivos), encoding="utf-8")
        # control: nada de la lectora en el material de la autora
        texto = "\n".join((d / f).read_text(encoding="utf-8") for f in archivos if not f.endswith(".png"))
        notas = [x["nota"].strip() for x in lectora[n] if len(x["nota"].strip()) >= 12]
        if any(t in texto for t in notas):
            sys.exit(f"FRENO: una nota de la lectora aparece en el material de la {e}")
        filas = list(csv.DictReader(open(d / planilla, encoding="utf-8"), delimiter="\t"))
        if any(any(f[c] for c in ADJ[1:]) for f in filas) or [f["ficha"] for f in filas] != orden_p1:
            sys.exit(f"FRENO: la planilla vacía de la {e} no es la esperada")
        if set(re.findall(r"(?m)^## (E\d-\d{3})$", (d / fichas).read_text(encoding="utf-8"))) != set(orden_p1):
            sys.exit(f"FRENO: las fichas de la {e} no son las de la lista")
        registro["etapas"][e] = {"semilla": semilla, "orden": orden_p1, "manifest_sha256": sha(d / "manifest.txt")}
    (out_m / "orden_pasada_1_S1ter.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({e: {"semilla": v["semilla"], "manifest_sha256": v["manifest_sha256"]} for e, v in registro["etapas"].items()},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
