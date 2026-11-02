"""U-SEG-OFICIAL, S1-quater (fichas), paso 3: control en cuentas de la carpeta de la lectora, el registro y las planillas vacías
(USD 0, sin API).

Uso: python -B control_fichas_S1quater_fichas.py --carpeta <carpeta de la lectora> --registro <registro_fichas_S1quater.json>
       --planillas <carpeta de las planillas vacías> --orden <orden de lectura sellado> --sha-orden <sha256 sellado>
       --out <json de cuentas>

Controla, sin imprimir ids ni texto de unidades ni números de ficha:
- el sha256 del orden sellado;
- por etapa, contra el orden: las fichas (renglones `## ` del archivo de fichas, fuera de los bloques de texto, en el orden de
  los ids opacos), los ids opacos
  seguidos (`E1-001`…, `E2-001`…), las imágenes (`<id opaco>_p<N>.png`, de un id opaco de la etapa, al menos una por ficha), los
  archivos que no son ficha, imagen ni manifest, y las filas del `manifest.txt`;
- el registro: fichas, imágenes, sha256 del `manifest.txt`, sha256 de cada archivo de la etapa (sin archivos de más ni de menos),
  sha256 de la planilla y cantidad de números por ficha (sin leer los números);
- la planilla vacía: el encabezado de S1-ter, una fila por ficha en el orden de los ids opacos, y vacías todas las columnas salvo
  `ficha` y `paginas`.
Escribe solo cuentas, sha256 y booleanos. Sale con código 1 si algo no da.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

COLUMNAS = ["ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("carpeta", "registro", "planillas", "orden", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    ap.add_argument("--sha-orden", required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit("FRENO: la salida ya existe")
    c: dict = {"control": "carpeta de la lectora, registro y planillas vacías de S1-quater, en cuentas",
               "hora": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")}
    raw = a.orden.read_bytes()
    c["orden_sha256_ok"] = hashlib.sha256(raw).hexdigest() == a.sha_orden
    if not c["orden_sha256_ok"]:
        raise SystemExit("FRENO: el orden no da el sha256 de su sello")
    orden = json.loads(raw)
    reg = json.loads(a.registro.read_text(encoding="utf-8"))
    c["registro_sha256"] = sha(a.registro)
    todo_ok = True
    for n, pref in ((1, "E1"), (2, "E2")):
        etapa = f"etapa_{n}"
        ops = [f["id_opaco"] for f in orden[etapa]["fichas"]]
        d = a.carpeta / etapa
        e: dict = {"fichas_en_el_orden": len(ops),
                   "ids_opacos_seguidos": ops == [f"{pref}-{k:03d}" for k in range(1, len(ops) + 1)]}
        md = d / f"fichas_{etapa}.md"
        cab, dentro = [], False
        for ln in md.read_text(encoding="utf-8").split("\n"):
            if ln.startswith("```"):
                dentro = not dentro
            elif not dentro and ln.startswith("## "):
                cab.append(ln[3:])
        e["fichas_en_el_archivo"] = len(cab)
        e["fichas_en_el_orden_de_los_ids_opacos"] = cab == ops
        archivos = sorted(p.name for p in d.iterdir() if p.is_file())
        pngs = [x for x in archivos if x.endswith(".png")]
        e["archivos"] = len(archivos)
        e["imagenes"] = len(pngs)
        re_img = re.compile(r"(E[12]-\d{3})_p(\d+)\.png")
        de_op = [re_img.fullmatch(x).group(1) if re_img.fullmatch(x) else None for x in pngs]
        e["imagenes_mal_nombradas"] = sum(1 for x in de_op if x is None)
        e["imagenes_de_un_id_opaco_ajeno"] = sum(1 for x in de_op if x is not None and x not in set(ops))
        e["fichas_sin_imagen"] = sum(1 for op in ops if op not in set(de_op))
        e["archivos_que_no_son_ficha_imagen_ni_manifest"] = sum(
            1 for x in archivos if x not in (md.name, "manifest.txt") and not x.endswith(".png"))
        filas_man = [ln for ln in (d / "manifest.txt").read_text(encoding="utf-8").splitlines()[2:] if ln.strip()]
        e["filas_del_manifest"] = len(filas_man)
        r = reg["etapas"][etapa]
        lista = sorted(x for x in archivos if x != "manifest.txt")
        e["registro_fichas_ok"] = r["fichas"] == len(ops)
        e["registro_imagenes_ok"] = r["imagenes"] == len(pngs)
        e["registro_manifest_sha256_ok"] = r["manifest_sha256"] == sha(d / "manifest.txt")
        e["registro_archivos_iguales"] = sorted(r["sha256"]) == lista and all(r["sha256"][x] == sha(d / x) for x in lista)
        e["registro_numeros_por_ficha"] = len(r["numero_por_ficha"])
        e["registro_numeros_de_las_fichas_del_orden"] = sorted(r["numero_por_ficha"]) == sorted(ops)
        pl = a.planillas / f"planilla_{etapa}_S1quater.tsv"
        e["planilla_sha256"] = sha(pl)
        e["registro_planilla_sha256_ok"] = r["planilla_sha256"] == e["planilla_sha256"]
        with open(pl, encoding="utf-8", newline="") as fh:
            filas = list(csv.DictReader(fh, delimiter="\t"))
            fh.seek(0)
            encabezado = fh.readline().rstrip("\n").split("\t")
        e["planilla_encabezado_ok"] = encabezado == COLUMNAS
        e["planilla_filas"] = len(filas)
        e["planilla_fichas_en_el_orden"] = [f["ficha"] for f in filas] == ops
        e["planilla_filas_sin_paginas"] = sum(1 for f in filas if not f["paginas"])
        e["planilla_columnas_llenas_fuera_de_ficha_y_paginas"] = sum(
            1 for f in filas for k in COLUMNAS[2:] if f.get(k))
        e["ok"] = (e["ids_opacos_seguidos"] and e["fichas_en_el_archivo"] == len(ops)
                   and e["fichas_en_el_orden_de_los_ids_opacos"] and e["imagenes_mal_nombradas"] == 0
                   and e["imagenes_de_un_id_opaco_ajeno"] == 0 and e["fichas_sin_imagen"] == 0
                   and e["archivos_que_no_son_ficha_imagen_ni_manifest"] == 0
                   and e["filas_del_manifest"] == len(lista) and e["registro_fichas_ok"] and e["registro_imagenes_ok"]
                   and e["registro_manifest_sha256_ok"] and e["registro_archivos_iguales"]
                   and e["registro_numeros_por_ficha"] == len(ops) and e["registro_numeros_de_las_fichas_del_orden"]
                   and e["registro_planilla_sha256_ok"] and e["planilla_encabezado_ok"] and e["planilla_filas"] == len(ops)
                   and e["planilla_fichas_en_el_orden"] and e["planilla_filas_sin_paginas"] == 0
                   and e["planilla_columnas_llenas_fuera_de_ficha_y_paginas"] == 0)
        todo_ok &= e["ok"]
        c[etapa] = e
    raiz = sorted(p.name for p in a.carpeta.iterdir() if p.name not in ("etapa_1", "etapa_2"))
    c["en_la_raiz_de_la_carpeta_fuera_de_las_etapas"] = len(raiz)
    c["ok"] = todo_ok and not raiz
    a.out.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(c, ensure_ascii=False, indent=1))
    sys.exit(0 if c["ok"] else 1)


if __name__ == "__main__":
    main()
