"""U-SEG-OFICIAL, S1-ter-b: prueba de `cifras_lectura_S1ter.py` y `lista_para_la_autora_S1ter.py` con planillas
SINTÉTICAS (USD 0). No es una lectura: las marcas las pone este script, y la salida da solo conteos, sin ids.

Uso: python -B prueba_cifras_S1ter.py --orden <orden sellado> --sha-orden <sha> --poblaciones-finales <json>
       --poblaciones <poblaciones_S1ter.json> --trabajo <directorio del scratchpad>

Escenarios de la etapa 1: 0, 3 y 4 errores de corte (las primeras fichas del orden), y 3 errores más 1 dudosa. En la
etapa 2, en todos: 2 errores en (a), 1 error en una lista de (b) que no es mixta, 1 en un mixto, una nota en la unidad
de la sección 3 de ri_oc y 1 error en la regresión. Esperado: piso 0,9591 / 0,9065 / 0,8912 (pasa, pasa, no pasa) y,
con la dudosa como error, 4 errores.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cifras_lectura_S1ter as C  # noqa: E402
import lista_para_la_autora_S1ter as LA  # noqa: E402

COLS = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")


def fila(op: str, marca: str = "correcta", nota: str = "") -> dict:
    d = {c: "" for c in COLS}
    d.update({"ficha": op, "marca": marca, "nota": nota})
    if marca == "error":
        d.update({"clase": "corte", "subclase": "termina_fuera"})
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("orden", "sha_orden", "poblaciones_finales", "poblaciones", "trabajo"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    raw = Path(a.orden).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.sha_orden
    orden = json.loads(raw)
    fin = json.loads(Path(a.poblaciones_finales).read_text(encoding="utf-8"))
    lim = json.loads(Path(a.poblaciones).read_text(encoding="utf-8"))["cortes"]["limites_declarados"]["unidades"]
    e1 = [x["id_opaco"] for x in orden["etapa_1"]["fichas"]]
    f2 = orden["etapa_2"]["fichas"]
    a_ = [x["id_opaco"] for x in f2 if x["poblacion"] == "c116_a"]
    b_normal = [x["id_opaco"] for x in f2 if x["poblacion"] == "c116_b" and x["id"] not in C.MIXTOS and x["id"] != "ri_oc::S2"]
    b_mixto = [x["id_opaco"] for x in f2 if x["id"] in C.MIXTOS]
    sec3 = [x["id_opaco"] for x in f2 if x["poblacion"] == "c116_b:seccion_3_ri_oc"]
    reg = [x["id_opaco"] for x in f2 if x["poblacion"] == "regresion"]
    marcas2 = {a_[0]: "error", a_[1]: "error", b_normal[0]: "error", b_mixto[0]: "error", reg[0]: "error"}
    p2 = [fila(x["id_opaco"], marcas2.get(x["id_opaco"], "correcta"),
               "nota sintética" if x["id_opaco"] == sec3[0] else "") for x in f2]
    out = []
    for nombre, k, dudosa in (("0 errores", 0, False), ("3 errores", 3, False), ("4 errores", 4, False),
                              ("3 errores y 1 dudosa", 3, True)):
        p1 = [fila(op, "error" if i < k else ("dudosa" if dudosa and i == k else "correcta")) for i, op in enumerate(e1)]
        r = C.calcular(orden, fin, lim, p1, p2)
        assert r["planillas_validas"], r
        pi = r["etapa_1"]["cifra_del_piso"]
        L, js = LA.armar(orden, p1, p2)
        out.append({"escenario": nombre,
                    "piso_dudosas_correctas": [pi["dudosas_como_correctas"]["errores_de_corte"],
                                               round(pi["dudosas_como_correctas"]["wilson95"][0], 4),
                                               pi["dudosas_como_correctas"]["llega_al_piso"]],
                    "piso_dudosas_error": [pi["dudosas_como_error"]["errores_de_corte"],
                                           round(pi["dudosas_como_error"]["wilson95"][0], 4),
                                           pi["dudosas_como_error"]["llega_al_piso"]],
                    "corpus": round(r["etapa_1"]["cifra_del_corpus"]["estimacion"], 4),
                    "a": [r["etapa_2"]["c116_a"]["con_error_de_corte"], r["etapa_2"]["c116_a"]["leidas"]],
                    "b_destinos": sorted(d["destino"].split(":")[0] for d in r["etapa_2"]["c116_b"]["entradas_con_destino"]),
                    "regresion_filas": len(r["etapa_2"]["regresion_sin_cifra"]),
                    "lista": {"e1_errores_y_dudosas": len(js["etapa_1"]["errores_y_dudosas"]),
                              "e1_correctas": len(js["etapa_1"]["correctas_sorteadas"]),
                              "e2_errores_y_dudosas": len(js["etapa_2"]["errores_y_dudosas"]),
                              "e2_correctas_con_nota": len(js["etapa_2"]["correctas_con_nota"]),
                              "e2_correctas": len(js["etapa_2"]["correctas_sorteadas"])},
                    "lista_sin_ids_de_unidad": all("::" not in x for x in L)})
    # una planilla mal formada se rechaza
    malo = [fila(op) for op in e1]
    malo[0]["marca"] = "quizas"
    rechazo = C.calcular(orden, fin, lim, malo, p2)
    print(json.dumps({"escenarios": out, "planilla_mal_formada_rechazada": not rechazo["planillas_validas"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
