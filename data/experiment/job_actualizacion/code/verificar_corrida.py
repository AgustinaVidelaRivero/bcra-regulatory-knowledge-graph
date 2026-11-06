"""Verificador independiente de una corrida. SIN RED.

Recomputa los agregados de la corrida DESDE LOS PDFs EN DISCO y desde la línea
base sellada, sin pasar por tabla_deltas.json, y los compara contra lo que esa
tabla afirma. Es la regla de recomputo aplicada a la corrida: un total que la
tabla declara y el disco no respalda es un defecto, no una diferencia de
criterio.

Uso (desde cualquier cwd):
  python3 data/experiment/job_actualizacion/code/verificar_corrida.py [--fecha AAAA-MM-DD]
Devuelve 0 si todo cierra; 1 si alguna comprobación falla.

Salida:
  ../corridas/<fecha>/verificacion_corrida.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_job as L                                              # noqa: E402

CLASES = ("sin_cambio", "contenido_modificado", "nuevo_en_indice",
          "desaparecido_del_indice", "no_verificable")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fecha", default=date.today().isoformat())
    args = ap.parse_args(argv)
    d = L.CORRIDAS / args.fecha
    t = json.loads((d / "tabla_deltas.json").read_text(encoding="utf-8"))
    obs = json.loads((d / "observaciones.json").read_text(encoding="utf-8"))
    tabla = t["tabla"]
    base = L.linea_base()
    filas_idx, duplicadas = L.leer_indice(d / "indice_crudo.json")
    idx = {f["id"]: f for f in filas_idx}

    fallas: list[str] = []

    def check(nombre: str, ok: bool, detalle: str = "") -> None:
        if not ok:
            fallas.append(f"{nombre}{': ' + detalle if detalle else ''}")

    # 1. el alcance de la corrida
    check("la tabla cubre índice UNION línea base",
          set(tabla) == set(idx) | set(base),
          f"tabla={len(tabla)} union={len(set(idx) | set(base))}")
    check("línea base = 157 (152 + 5)", len(base) == 157)
    check("índice de hoy = 157 URLs únicas", len(idx) == 157)

    # 2. las clases suman
    c = Counter(f["clasificacion"] for f in tabla.values())
    check("las clases suman el total de la tabla",
          sum(c.values()) == len(tabla), f"{dict(c)}")
    for grupo in ("desarrollo_5", "inventariado_152", "alta_posterior"):
        dec = t["delta_inicial_vs_descarga_original"]["desglosado_por_corpus"][grupo]
        real = Counter(f["clasificacion"] for f in tabla.values()
                       if f["grupo"] == grupo)
        check(f"desglose de {grupo} coincide con la tabla",
              all(dec[k] == real.get(k, 0) for k in CLASES)
              and dec["total"] == sum(real.values()),
              f"declarado={dec} real={dict(real)}")

    # 3. cada sha declarado se recomputa desde el PDF en disco
    sha_mal, sha_ok = [], 0
    for ident, o in obs.items():
        if o.get("estado") != "descargado":
            continue
        pdf = d / "pdfs" / f"{ident}.pdf"
        if not pdf.exists():
            sha_mal.append(f"{ident}: pdf ausente")
            continue
        real = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if real != o["sha256"]:
            sha_mal.append(f"{ident}: disco={real[:12]} obs={o['sha256'][:12]}")
        else:
            sha_ok += 1
    check("todo sha declarado se recomputa desde el PDF en disco",
          not sha_mal, "; ".join(sha_mal[:5]))

    # 4. cada clasificación se re-deriva de los sha
    mal = []
    for ident, f in tabla.items():
        sa, sn = f["sha_anterior"], f["sha_actual"]
        if ident not in idx:
            esperada = "desaparecido_del_indice"
        elif obs.get(ident, {}).get("estado") != "descargado":
            esperada = "no_verificable"
        elif sa is None:
            esperada = "nuevo_en_indice"
        else:
            esperada = "sin_cambio" if sa == sn else "contenido_modificado"
        if f["clasificacion"] != esperada:
            mal.append(f"{ident}: tabla={f['clasificacion']} re-derivada={esperada}")
    check("toda clasificación se re-deriva de los sha y del índice",
          not mal, "; ".join(mal[:5]))

    # 5. el sha anterior de la tabla es el del artefacto sellado
    mal_base = [ident for ident, f in tabla.items()
                if f["sha_anterior"] and ident in base
                and f["sha_anterior"] != base[ident]["sha256"]]
    check("el sha anterior sale de la línea base sellada", not mal_base,
          ", ".join(mal_base[:5]))

    # 6. los modificados traen páginas y procedencia de ambos lados
    modificados = [i for i, f in tabla.items()
                   if f["clasificacion"] == "contenido_modificado"]
    sin_proc = [i for i in modificados
                if not tabla[i].get("procedencia_anterior")
                or not tabla[i].get("procedencia_actual")]
    check("todo modificado trae procedencia anterior y actual", not sin_proc,
          ", ".join(sin_proc[:5]))

    # La bitácora cruda (corrida.log) NO se versiona: el .gitignore raíz del
    # repositorio excluye *.log y esta unidad no lo edita. Sus estadísticas se
    # derivan acá para que sobrevivan en un artefacto que sí se versiona.
    log = (d / "corrida.log").read_text(encoding="utf-8").splitlines() \
        if (d / "corrida.log").exists() else []
    arranques = sum(1 for x in log if "inicio ===" in x)
    cortesia = {
        "arranques_del_runner": arranques,
        "pedidos_al_indice_registrados": sum(1 for x in log if "[indice] OK" in x),
        "pedidos_a_pdfs_registrados": sum(1 for x in log if " descargado " in x),
        "pedidos_en_vuelo_sin_registro": max(0, arranques - 2),
        "reintentos_por_error_de_red": sum(1 for x in log if "[reintento]" in x),
        "activaciones_modo_lento_503": sum(1 for x in log if "[modo-lento]" in x),
        "cierres_de_segmento": [x.split(" ", 1)[1] for x in log if "— fin ===" in x],
        "nota": "La bitácora cruda no se versiona (*.log del .gitignore raíz); "
                "estas estadísticas son su derivado persistido.",
    }

    salida = {
        "veredicto": "OK" if not fallas else "FALLA",
        "cortesia_con_la_fuente": cortesia,
        "comprobaciones_fallidas": fallas,
        "fecha_corrida": args.fecha,
        "alcance": {"linea_base": len(base), "indice_hoy": len(idx),
                    "tabla": len(tabla), "duplicadas_del_indice": len(duplicadas)},
        "clases_recomputadas": dict(c),
        "sha_recomputados_ok": sha_ok,
        "modificados": sorted(modificados),
        "paginas_linea_base": sum(int(v["paginas"]) for v in base.values()),
    }
    (d / "verificacion_corrida.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False, indent=1))
    return 0 if not fallas else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
