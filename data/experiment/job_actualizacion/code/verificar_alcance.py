"""Recomputa el alcance del job de actualización contra los artefactos sellados.

Es el primer paso obligatorio de la unidad: la cuenta del corpus a vigilar
(157 Textos Ordenados, 7.321 páginas) se re-deriva de los archivos commiteados
en lugar de arrastrarse de prosa. Todo número del documento de diseno sale de
acá.

SOLO LECTURA sobre todo lo que toca. El inventario sellado respalda números ya
impresos en el informe: este script lo lee y lo compara, jamás lo reescribe.

Entradas (solo lectura):
  data/experiment/escalado_prep/{manifest_pdfs.sha256, descarga_log.json,
      indice_oficial_raw.json, inventario_tos.csv, inventario_resumen.json,
      inventario_unidades.csv, referencia_subset.json}
  data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json
  data/experiment/subset/*.pdf                     (sha de verificación)
  data/raw/manifiesto.csv                          (fecha de adquisición)

Salida:
  ../verificacion_alcance.json

Uso (desde cualquier cwd):
  python3 data/experiment/job_actualizacion/code/verificar_alcance.py
Devuelve 0 si toda la cuenta cierra; 1 si alguna comprobación falla.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
UNIDAD = AQUI.parent
EXPERIMENT = UNIDAD.parent
REPO = EXPERIMENT.parent.parent
PREP = EXPERIMENT / "escalado_prep"
MANIF_DEV = EXPERIMENT / "reextraccion_v2" / "manifiestos" / "desarrollo_5tos.json"
MANIF_RAW = REPO / "data" / "raw" / "manifiesto.csv"

CATEGORIAS = [("normativa_general", "textos_ordenados"),
              ("regimen_informativo", "regimenes_informativos")]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    fallas: list[str] = []

    def check(nombre: str, ok: bool) -> bool:
        if not ok:
            fallas.append(nombre)
        return ok

    # --- los 152 inventariados -------------------------------------------
    manifiesto = {}
    for linea in (PREP / "manifest_pdfs.sha256").read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea:
            sha, archivo = linea.split(None, 1)
            manifiesto[archivo.strip().removesuffix(".pdf")] = sha
    log = json.loads((PREP / "descarga_log.json").read_text(encoding="utf-8"))
    inv_tos = list(csv.DictReader((PREP / "inventario_tos.csv").open(encoding="utf-8")))
    inv_unid = list(csv.DictReader((PREP / "inventario_unidades.csv").open(encoding="utf-8")))

    paginas_152 = sum(int(f["paginas"]) for f in inv_unid)
    sha_discrepantes = sorted(i for i in log if manifiesto.get(i) != log[i].get("sha256"))

    g152 = {
        "manifest_pdfs_sha256_lineas": len(manifiesto),
        "descarga_log_entradas": len(log),
        "descarga_log_con_sha256": sum(1 for v in log.values() if v.get("sha256")),
        "descarga_log_con_url": sum(1 for v in log.values() if v.get("url")),
        "inventario_tos_filas": len(inv_tos),
        "inventario_unidades_filas": len(inv_unid),
        "paginas": paginas_152,
        "sha_manifiesto_vs_log_discrepantes": sha_discrepantes,
    }
    check("152: manifiesto tiene 152 líneas", len(manifiesto) == 152)
    check("152: descarga_log tiene 152 entradas con sha y url",
          len(log) == 152 and g152["descarga_log_con_sha256"] == 152
          and g152["descarga_log_con_url"] == 152)
    check("152: páginas == 6.757", paginas_152 == 6757)
    check("152: sha de manifiesto y log coinciden", not sha_discrepantes)

    # --- los 5 de desarrollo ---------------------------------------------
    dev = json.loads(MANIF_DEV.read_text(encoding="utf-8"))["tos"]
    ref = json.loads((PREP / "referencia_subset.json").read_text(encoding="utf-8"))
    paginas_5 = sum(int(v["paginas"]) for v in ref.values())
    sha_dev_ok, sha_dev_detalle = True, {}
    for to in dev:
        pdf = REPO / to["pdf"]
        real = sha256(pdf) if pdf.exists() else None
        sha_dev_detalle[to["id"]] = {"declarado": to["sha256_pdf"], "en_disco": real,
                                     "coincide": real == to["sha256_pdf"]}
        sha_dev_ok &= (real == to["sha256_pdf"])

    g5 = {
        "manifiesto_tos": len(dev),
        "con_sha256_pdf": sum(1 for t in dev if t.get("sha256_pdf")),
        "con_url_en_el_manifiesto": sum(1 for t in dev if t.get("url")),
        "paginas": paginas_5,
        "sha_declarado_vs_disco": sha_dev_detalle,
    }
    check("5: el manifiesto trae 5 TOs con sha256_pdf",
          len(dev) == 5 and g5["con_sha256_pdf"] == 5)
    check("5: páginas == 564", paginas_5 == 564)
    check("5: sha declarado == sha en disco", sha_dev_ok)

    # --- el índice oficial y la regla de deduplicación --------------------
    crudo = json.loads((PREP / "indice_oficial_raw.json").read_text(encoding="utf-8"))
    entradas = [(cat, it) for cat, clave in CATEGORIAS for it in crudo[clave]]
    cnt_url = Counter(it["url"] for _, it in entradas)
    duplicadas = sorted(u for u, n in cnt_url.items() if n > 1)
    urls_indice = set(cnt_url)
    urls_inventario = {f["url_pdf"] for f in inv_tos}
    solo_indice = sorted(urls_indice - urls_inventario)

    # el hueco entre índice e inventario tiene que ser exactamente el subset
    resumen = json.loads((PREP / "inventario_resumen.json").read_text(encoding="utf-8"))
    titulo_de = {it["url"]: it["titulo"] for _, it in entradas}
    titulos_subset = {s["titulo"] for s in resumen["subset_excluido"]}
    dev_por_titulo = {titulo_de[u]: u for u in solo_indice}

    indice = {
        "entradas": len(entradas),
        "por_lista": {clave: len(crudo[clave]) for _, clave in CATEGORIAS},
        "urls_unicas": len(urls_indice),
        "urls_duplicadas": duplicadas,
        "urls_solo_en_indice": solo_indice,
        "coincide_con_subset_excluido": set(dev_por_titulo) == titulos_subset,
        "url_por_id_desarrollo": {
            s["id_interno"]: dev_por_titulo.get(s["titulo"])
            for s in resumen["subset_excluido"]},
    }
    check("índice: 158 entradas", len(entradas) == 158)
    check("índice: 157 URLs únicas con 1 duplicada",
          len(urls_indice) == 157 and len(duplicadas) == 1)
    check("índice: inventario + subset cubren el índice sin resto",
          not (urls_inventario - urls_indice) and len(solo_indice) == 5)
    check("índice: las 5 URLs sobrantes son las del conjunto de desarrollo",
          set(dev_por_titulo) == titulos_subset)

    # --- la cuenta total --------------------------------------------------
    total = {
        "tos": len(log) + len(dev),
        "paginas": paginas_152 + paginas_5,
        "bytes_declarados": sum(v.get("bytes", 0) for v in log.values())
        + sum(int(v["bytes"]) for v in ref.values()),
    }
    check("total: 157 TOs", total["tos"] == 157)
    check("total: 7.321 páginas", total["paginas"] == 7321)

    # --- fecha de adquisición (ancla del delta) ---------------------------
    archivos_dev = {t["archivo"]: t["id"] for t in dev}
    fechas = {}
    with MANIF_RAW.open(encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            nombre = fila.get("archivo_local", "").split("/")[-1]
            if nombre in archivos_dev:
                fechas[archivos_dev[nombre]] = {
                    "fecha_descarga": fila.get("fecha_descarga"),
                    "fecha_documento_extraida": fila.get("fecha_documento"),
                    "url_origen": fila.get("url_origen")}
    ancla = {
        "los_152": {
            "evidencia": "commit de alta de escalado_prep/descarga_log.json",
            "comando": "git log --diff-filter=A --format='%ad %h' --date=short "
                       "-- data/experiment/escalado_prep/descarga_log.json"},
        "los_5_desarrollo": fechas,
    }
    check("ancla: los 5 tienen fecha de descarga en el manifiesto crudo",
          len(fechas) == 5)

    salida = {
        "veredicto": "OK" if not fallas else "FALLA",
        "comprobaciones_fallidas": fallas,
        "inventariados_152": g152,
        "desarrollo_5": g5,
        "indice_oficial": indice,
        "total_157": total,
        "ancla_temporal": ancla,
    }
    (UNIDAD / "verificacion_alcance.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False, indent=1))
    return 0 if not fallas else 1


if __name__ == "__main__":
    sys.exit(main())
