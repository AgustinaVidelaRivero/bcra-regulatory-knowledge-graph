"""4.f de S2 (U-SEG-OFICIAL): el resultado de la lectura de cortes de S1-quater, del registro de su cierre (solo lectura).

Uso: python -B cifras_s1quater_S2.py --raiz <copia del repo> --out <json>

Lee las salidas del cierre (`s1quater/adjudicacion/cierre/corrida/salida/`): `cifras/cifras_lectura_S1quater_adjudicada.json`
(las cifras), `control/cifra_control_sin_vistas_S1quater.json` (la de control) y
`aplicar/registro_aplicar_adjudicacion_S1quater.json` (los errores en la unidad que sigue). Solo ids, fichas, clases y
cuentas: no copia las notas. Separa lo medido, que puede ir a la tesis, del piso y su declaración, que van marcados como
procedimiento interno (decisión de la autora del 15/10/2026, despacho de S2, versión 2).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

Q = "data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/cierre"
CIFRAS = f"{Q}/corrida/salida/cifras/cifras_lectura_S1quater_adjudicada.json"
CONTROL = f"{Q}/corrida/salida/control/cifra_control_sin_vistas_S1quater.json"
APLICAR = f"{Q}/corrida/salida/aplicar/registro_aplicar_adjudicacion_S1quater.json"
REGISTRO = f"{Q}/registro_cierre_adjudicacion_S1quater_mesa.md"


def f4(x: float) -> str:
    return f"{x:.4f}".replace(".", ",")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    d = json.loads((a.raiz / CIFRAS).read_text(encoding="utf-8"))
    c = json.loads((a.raiz / CONTROL).read_text(encoding="utf-8"))
    ap_ = json.loads((a.raiz / APLICAR).read_text(encoding="utf-8"))
    e1 = d["etapa_1"]
    piso = e1["cifra_del_piso"][e1["cifra_del_piso"]["decide"]]
    corp = e1["cifra_del_corpus"]
    est = e1["por_estrato"]
    err1 = [{k: x[k] for k in ("ficha", "unidad", "estrato", "clase", "subclase", "subclase_adicional")} for x in e1["errores_de_corte"]]
    r2 = d["etapa_2"]["regresion_sin_cifra"]
    unidad_de = {x["ficha"]: x["unidad"] for x in r2}
    err2 = [{k: x[k] for k in ("ficha", "unidad", "clase", "subclase", "subclase_adicional")} for x in r2 if x["clase"] == "corte"]
    sigue = [{"ficha": x["ficha"], "unidad_de_la_fila": unidad_de.get(x["ficha"]), "clase_de_la_fila": x["clase_de_la_fila"],
              "clase_que_sigue": x["clase_que_sigue"], "subclase_que_sigue": x["subclase_que_sigue"]}
             for x in ap_["cierres_confirmados"]]
    ctl = c["cifra_de_control"][c["cifra_de_control"]["decide"]]
    out = {"fuentes": {k: hashlib.sha256((a.raiz / k).read_bytes()).hexdigest() for k in (CIFRAS, CONTROL, APLICAR, REGISTRO)},
           "etapa_1": {"leidas": piso["leidas"], "sin_error_de_corte": piso["sin_error_de_corte"], "errores_de_corte": piso["errores_de_corte"],
                       "wilson95": piso["wilson95"], "por_estrato": est, "ponderada": corp, "errores": err1,
                       "por_subclase": e1["errores_de_corte_por_subclase"], "dudosas": len(e1["dudosas"]), "limpieza": e1["limpieza"]},
           "etapa_2": {"leidas": len(r2), "correctas": sum(1 for x in r2 if x["marca"] == "correcta"), "errores_de_corte": err2,
                       "errores_en_la_unidad_que_sigue": sigue, "limpieza": d["etapa_2"]["limpieza"]},
           "procedimiento_interno": {"piso": 0.90, "llega_al_piso": piso["llega_al_piso"],
                                     "cifra_de_control": {"leidas": ctl["leidas"], "sin_error_de_corte": ctl["sin_error_de_corte"],
                                                          "wilson95": ctl["wilson95"], "llega_al_piso": ctl["llega_al_piso"]}}}
    md = []
    md.append("Fuente: el registro del cierre de la adjudicación (`s1quater/adjudicacion/cierre/registro_cierre_adjudicacion_S1quater_mesa.md`, "
              "§4 a §7) y sus salidas en `cierre/corrida/salida/` (`s1quater_S2b.json`, con el sha256 de cada fuente). La lectura es "
              "de la E0 corregida.")
    md.append("")
    md.append("**Lo medido** (puede ir a la tesis):")
    md.append(f"- **Etapa 1, las 90 fichas sorteadas** (`etapa_1`): {piso['sin_error_de_corte']} de {piso['leidas']} unidades sin error "
              f"de corte, {piso['errores_de_corte']} con error, {len(e1['dudosas'])} dudosas; sin ponderar, intervalo de Wilson al 95 % "
              f"[{f4(piso['wilson95'][0])}; {f4(piso['wilson95'][1])}].")
    md.append("  - Por estrato: " + "; ".join(f"{k} {v['sin_error']} de {v['leidas']}" for k, v in est.items()) + ".")
    md.append(f"  - **La cifra ponderada por estrato** (la del corpus): {f4(corp['estimacion'])}, tamaño efectivo "
              f"{f4(corp['n_efectivo'])[:-2]}, Wilson [{f4(corp['wilson95'][0])}; {f4(corp['wilson95'][1])}]; es una aproximación "
              "que trata la muestra ponderada como una simple de ese tamaño.")
    md.append("  - Errores de corte por subclase, con la adicional: " + ", ".join(f"{k} {v}" for k, v in e1["errores_de_corte_por_subclase"].items())
              + f" ({sum(e1['errores_de_corte_por_subclase'].values())} subclases en {len(err1)} errores). Limpieza, aparte: {e1['limpieza']}.")
    md.append("  - Los casos: " + "; ".join(f"{x['ficha']} `{x['unidad']}` ({x['estrato']}; {x['subclase']}"
                                            + (f" + {x['subclase_adicional']}" if x["subclase_adicional"] else "") + ")" for x in err1) + ".")
    md.append(f"- **Etapa 2, la regresión** (`etapa_2`; sin cifra, por diseño): {out['etapa_2']['correctas']} de {len(r2)} correctas y "
              f"{len(err2)} errores de corte: " + "; ".join(f"{x['ficha']} `{x['unidad']}` ({x['subclase']}"
                                                          + (f" + {x['subclase_adicional']}" if x["subclase_adicional"] else "") + ")" for x in err2)
              + f". Limpieza: {d['etapa_2']['limpieza']}.")
    md.append("  - Errores confirmados en la unidad que sigue (cuentan como errores de corte del documento, decisión de la autora del "
              "15/10/2026; mandato `:965-968`): " + "; ".join(f"{x['ficha']} (fila `{x['unidad_de_la_fila']}`, {x['clase_que_sigue']}"
                                                              f" {x['subclase_que_sigue']})" for x in sigue) + ".")
    md.append("  - Los documentos con un error de corte confirmado: ri_icpipsp, ri_pnp, ri_psprca y ri_oc por la marca de la fila, y "
              "gerc y ri_spi¹ por la unidad que sigue (mandato `:965-968`); la herencia no cuenta.")
    md.append("")
    md.append("**Procedimiento interno, no para la tesis** (decisión de la autora del 15/10/2026): el piso y su declaración.")
    md.append(f"- El piso es 0,90 sobre el límite inferior de Wilson de la etapa 1 (`docs/checklist_pre_escalado.md:81`, condición 7): "
              f"{f4(piso['wilson95'][0])}, **no llega** (`procedimiento_interno.llega_al_piso`: {piso['llega_al_piso']}). Rige la rama 2 "
              "del plan B: la salida de S1-quater se commitea con su cifra, declarada debajo del piso, S2 se despacha igual, la "
              "condición 7 queda declarada, no cumplida, y no hay otra vuelta a S0 antes de la tanda 1 (mandato, nota del 15/10/2026, "
              "`:950-959`).")
    md.append(f"- La cifra de control, sin las 26 fichas cuyo texto vio un modelo en la pasada 1: {ctl['sin_error_de_corte']} de "
              f"{ctl['leidas']}, Wilson [{f4(ctl['wilson95'][0])}; {f4(ctl['wilson95'][1])}], tampoco llega y no decide. La pongo en "
              "este bloque porque es un control del procedimiento de la lectura a ciegas; es una lectura mía de la decisión.")
    out["texto_md"] = "\n".join(md)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out["texto_md"])


if __name__ == "__main__":
    main()
