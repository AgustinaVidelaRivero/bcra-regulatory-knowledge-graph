"""U-SEG-OFICIAL, S1-quater: material de la pasada 1 de la adjudicación (mesa, 13/10/2026; USD 0). Adaptado de
`s1ter/adjudicacion/preparar_pasada_1_S1ter_v2.py`.

Lo arma la autora, con un comando que la mesa le prepara y que ella revisa antes de correrlo (decisión de la autora del §91). Reglas de
la autora para S1-quater: `reglas_adjudicacion_S1quater.md` (`5e96a764…`), fuera del repo.

- **De dónde sale:** del tar sellado de la carpeta de la lectora (`NO_ABRIR_carpeta_lectora_S1quater.tar`, armado antes de la lectura,
  `86275bfd…`), controlado contra los dos `manifest.txt` sellados. No lee nada de la carpeta de la lectora: ni su planilla, ni su sello,
  ni sus archivos de trabajo. Así, el material no lleva nada de la lectora, por construcción.
- **Qué etapas:** las que pida `--etapas`. Cada una va entera, porque ninguna sale de las marcas: la etapa 1, las 90 de la muestra; la
  etapa 2, las de la regresión.
- **El orden:** `random.Random(f"U-SEG-OFICIAL:adjudicacion:S1-quater:{etapa}").sample(sorted(ids), len(ids))`.
- **Qué escribe:**
  - el material de la autora: por etapa, las fichas en ese orden (cada bloque, copiado tal cual de `fichas_etapa_N.md`), sus imágenes,
    la planilla vacía con las columnas del TSV de adjudicación de S1-ter, un LEEME y un `manifest.txt` legible por `shasum -a 256 -c`;
  - el registro de la mesa: el orden (solo ids opacos), las semillas y el sha256 de cada `manifest.txt`, sin marcas.
- **Cómo escribe:** en carpetas «.parcial», que se renombran solo si todos los controles dan; si no, se borran.

Uso: python3 -B preparar_pasada_1_S1quater.py --tar <NO_ABRIR_carpeta_lectora_S1quater.tar> --sha-tar <sha256 sellado>
       --orden <NO_ABRIR_orden_lectura_S1quater.json> --sha-orden <sha256 sellado> --sha-manifest-1 <sha256> --sha-manifest-2 <sha256>
       --etapas <1 | 1,2> --out-autora <carpeta nueva> --out-mesa <carpeta nueva>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import sys
import tarfile
from pathlib import Path

ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
SEMILLA = "U-SEG-OFICIAL:adjudicacion:S1-quater:{etapa}"
# ---- el LEEME de S1-ter (`preparar_pasada_1_S1ter_v2.py:46-73`), con una sola línea agregada: la del criterio final ----
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
- Rige el criterio final de S1-ter, en las dos etapas (nota de reglas de la autora, puntos 6 y 7).

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
# ---- fin de lo copiado ----


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bloques(md: str) -> dict[str, str]:
    """Cada bloque de ficha, desde su encabezado `## E…` hasta el siguiente, tal cual (`preparar_pasada_1_S1ter_v2.py:82-85`)."""
    partes = re.split(r"(?m)^(?=## E\d-\d{3}$)", md)
    return {re.match(r"## (E\d-\d{3})", p).group(1): p for p in partes if p.startswith("## E")}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("tar", "sha_tar", "orden", "sha_orden", "sha_manifest_1", "sha_manifest_2", "etapas", "out_autora", "out_mesa"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    if a.etapas not in ("1", "1,2"):
        sys.exit("FRENO: --etapas tiene que ser 1 o 1,2")
    fin_a, fin_m = Path(a.out_autora), Path(a.out_mesa)
    if fin_a.exists() or fin_m.exists():
        sys.exit("FRENO: las carpetas de salida ya existen")
    out_a, out_m = fin_a.with_name(fin_a.name + ".parcial"), fin_m.with_name(fin_m.name + ".parcial")
    try:
        armar(a, out_a, out_m)
    except SystemExit:
        shutil.rmtree(out_a, ignore_errors=True)
        shutil.rmtree(out_m, ignore_errors=True)
        raise
    out_a.rename(fin_a)
    out_m.rename(fin_m)


def armar(a, out_a: Path, out_m: Path) -> None:
    if out_a.exists() or out_m.exists():
        sys.exit("FRENO: quedaron carpetas «.parcial» de una corrida anterior")
    tar, orden_p = Path(a.tar), Path(a.orden)
    if sha(tar) != a.sha_tar:
        sys.exit("FRENO: el tar no da su sha256 sellado")
    if sha(orden_p) != a.sha_orden:
        sys.exit("FRENO: el orden de lectura no da su sha256 sellado")
    orden = json.loads(orden_p.read_text(encoding="utf-8"))
    out_m.mkdir(parents=True)
    fuente = out_m / "NO_ABRIR_fuente_tar"
    with tarfile.open(tar) as t:
        miembros = t.getmembers()
        if any(m.issym() or m.islnk() or m.name.startswith("/") or ".." in Path(m.name).parts for m in miembros):
            sys.exit("FRENO: el tar trae enlaces o rutas fuera de su carpeta")
        if any(not re.fullmatch(r"etapa_[12](/[^/]+)?", m.name.rstrip("/")) for m in miembros):
            sys.exit("FRENO: el tar trae algo fuera de etapa_1/ y etapa_2/")
        t.extractall(fuente, filter="data") if hasattr(tarfile, "data_filter") else t.extractall(fuente)
    for n, s in ((1, a.sha_manifest_1), (2, a.sha_manifest_2)):
        d = fuente / f"etapa_{n}"
        if sha(d / "manifest.txt") != s:
            sys.exit(f"FRENO: el manifest.txt de la etapa {n} no da el sha256 sellado")
        filas = [l for l in (d / "manifest.txt").read_text(encoding="utf-8").splitlines()[2:] if l.strip()]
        listados = {}
        for l in filas:
            h, _nb, resto = l.split("  ", 2)
            listados[resto.split(" — ", 1)[0]] = h
        if set(listados) | {"manifest.txt"} != {p.name for p in d.iterdir()}:
            sys.exit(f"FRENO: la etapa {n} del tar no tiene exactamente los archivos de su manifest.txt")
        if any(sha(d / f) != h for f, h in listados.items()):
            sys.exit(f"FRENO: un archivo de la etapa {n} del tar no da su sha256")
    etapas = [int(x) for x in a.etapas.split(",")]
    registro = {"version": 1, "semilla": SEMILLA, "tar_sha256": a.sha_tar, "orden_lectura_sha256": a.sha_orden,
                "manifest_sha256": {"etapa_1": a.sha_manifest_1, "etapa_2": a.sha_manifest_2}, "etapas_pedidas": a.etapas, "etapas": {}}
    out_a.mkdir(parents=True)
    for n in etapas:
        e = f"etapa_{n}"
        ids = sorted(f["id_opaco"] for f in orden[e]["fichas"])
        semilla = SEMILLA.format(etapa=e)
        orden_p1 = random.Random(semilla).sample(ids, len(ids))
        d = out_a / e
        d.mkdir()
        bl = bloques((fuente / e / f"fichas_{e}.md").read_text(encoding="utf-8"))
        if set(bl) != set(ids):
            sys.exit(f"FRENO: las fichas del tar de la {e} no son las del orden sellado")
        fichas = f"fichas_pasada_1_{e}.md"
        cab = f"# Adjudicación de la lectura de segmentación: {e}, pasada 1\n\nFichas en un orden al azar.\n\n"
        (d / fichas).write_text(cab + "".join(bl[i] if bl[i].endswith("\n") else bl[i] + "\n" for i in orden_p1), encoding="utf-8")
        for i in orden_p1:
            for img in sorted((fuente / e).glob(f"{i}_p*.png")):
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
        # controles: la planilla vacía, las fichas y las imágenes son las esperadas, y no hay nada más
        filas = list(csv.DictReader(open(d / planilla, encoding="utf-8"), delimiter="\t"))
        if any(any(f[c] for c in ADJ[1:]) for f in filas) or [f["ficha"] for f in filas] != orden_p1:
            sys.exit(f"FRENO: la planilla vacía de la {e} no es la esperada")
        if re.findall(r"(?m)^## (E\d-\d{3})$", (d / fichas).read_text(encoding="utf-8")) != orden_p1:
            sys.exit(f"FRENO: las fichas de la {e} no están en el orden de la adjudicación")
        imgs_tar = sorted(p.name for p in (fuente / e).glob("*.png"))
        imgs_aut = sorted(p.name for p in d.glob("*.png"))
        if imgs_tar != imgs_aut or any(sha(d / i) != sha(fuente / e / i) for i in imgs_aut):
            sys.exit(f"FRENO: las imágenes de la {e} no son las del tar")
        if {p.name for p in d.iterdir()} != set(imgs_aut) | {fichas, planilla, "LEEME.md", "manifest.txt"}:
            sys.exit(f"FRENO: la carpeta de la {e} trae archivos de más")
        registro["etapas"][e] = {"semilla": semilla, "fichas": len(orden_p1), "imagenes": len(imgs_aut), "orden": orden_p1,
                                 "manifest_sha256": sha(d / "manifest.txt")}
    shutil.rmtree(fuente)
    (out_m / "orden_pasada_1_S1quater.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({e: {"fichas": v["fichas"], "imagenes": v["imagenes"], "manifest_sha256": v["manifest_sha256"]}
                      for e, v in registro["etapas"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
