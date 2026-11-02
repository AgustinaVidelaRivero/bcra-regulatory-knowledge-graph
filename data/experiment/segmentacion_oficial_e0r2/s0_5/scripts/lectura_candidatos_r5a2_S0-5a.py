"""Los candidatos de R5-a′ (título de bloque), con su página y mi lectura (U-SEG-OFICIAL, S0-5a; USD 0, solo lectura).

Uso: python -B lectura_candidatos_r5a2_S0-5a.py --antes <candidatos sobre S0-4b> --despues <candidatos sobre S0-5a>
       --lectura-r5a <salida de lectura_r5a_S0-5a.py> --out-json <json> --out-md <md>

Junta la salida de `candidatos_r5a2_S0-5a.py` sobre la salida de S0-4b (la base de la decisión 3 de la autora) con la de
S0-5a, y les suma mi lectura (`LECTURA`), a la vista del texto de la salida, sin abrir la página, sin adjudicar:
- «título de bloque»: el renglón es el título de un bloque que no es del último ítem (formulario, parte, anexo, criterios);
- «bloque sin título»: lo que sigue es un bloque propio (un modelo de nota), pero el renglón no es su título;
- «falso positivo»: fila o encabezado de tabla, fórmula, ejemplo, artículo de un texto transcripto, renglón de prosa;
- «dudosa»: un subtítulo que puede ser del ítem.
Adónde iría con la regla: si el padre es una sección, la regla de ri_oc abre una unidad nueva después de la sección
(`<to>::Sbloque<k>`); si es un punto, la regla, como está, no lo alcanza. Y qué hace hoy R5-a con ese bloque (de
`lectura_r5a_S0-5a.py`): si lo lleva al cierre del padre.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

TANDA1 = ("ayccef", "expaef", "opefci", "adrei", "ri_ccna", "ri_pgn", "ri_rml", "ri_gerc", "snp_cheq", "ceninf",
          "cirmo3", "snp_tr", "lingeef", "depaho", "cajasc", "manori", "efemin", "nmcief", "ri_dcpc", "ri_oc")
T, S, F, D = "título de bloque", "bloque sin título", "falso positivo", "dudosa"
LECTURA = {
    "apnf::1.3.2.5": (T, "título del formulario «FÓRMULA I» (datos del proveedor)"),
    "convca::2.2.2": (F, "renglón de una lista de cuentas"),
    "cryl::12.2": (S, "modelo de nota: el renglón es el destinatario"),
    "efemin::1.3.7.2": (F, "encabezado de una tabla («Tasas en %»)"),
    "gescre::1.2.8.2": (T, "título del modelo «DECLARACION JURADA SOBRE LA CONDICION…», en dos renglones"),
    "inspag::1.3.1.6": (F, "renglón de un ejemplo de cálculo"),
    "inspag::1.3.2.4": (F, "renglón de un ejemplo de cálculo"),
    "inspag::3.3.2": (S, "modelo de nota: el renglón es «Lugar y fecha»"),
    "lingeef::5.4.2.3": (F, "fila de una tabla"),
    "manual::2.3.2": (F, "fórmula"),
    "ri_cc::R4::1.2.2": (D, "subtítulo «Depósitos a plazo» dentro del ítem"),
    "ri_cc::R5::2.2.1.2": (F, "definición de un código («LC = código 03»)"),
    "ri_laft::1.5": (D, "«Reporte de Transacciones en Efectivo de Alto Monto (RTE)»: puede ser otra sección; ri_laft "
                        "se lee sin raíz"),
    "ri_oc::C.11": (T, "«Criterios de validación»: el caso por lista de S0-5a"),
    "ri_ot::13.4": (T, "«Criterios de consistencia»"),
    "ri_pnp::5.7": (T, "«II – INSTRUCCIONES GENERALES»: otra parte del documento, de nivel mayor que la sección"),
    "ri_rml::1.2.3": (D, "«Plazos residuales»: subtítulo dentro del 1.2.3 de antes de R5-d"),
    "ri_spi::C.1.3": (T, "«Anexo I»"),
    "seggar::8.2": (F, "artículo de un texto transcripto («Artículo 16: (**)»)"),
    "snp_atm::2.3.3": (F, "encabezado de una tabla"),
    "snp_cheq::3.6.4.1.6": (F, "renglón de prosa partido"),
    "tasint::3.3.2": (F, "renglón de prosa («En las expresiones anteriores se entiende»)"),
    "tasint::5.1.3": (F, "fórmula"),
    "traval::2.5": (T, "título del formulario «FÓRMULA I»"),
    "manori::3.5.2": (T, "título del formulario «PLANILLA DE APROBACIÓN Y ANÁLISIS» (solo sobre S0-5a)"),
    "ri2_ae::14.3": (D, "subtítulo «Informes» dentro del ítem (solo sobre S0-5a)"),
}


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("antes", "despues", "lectura_r5a", "out_json", "out_md"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    antes = {f["item"]: f for f in jl(a.antes)["filas"]}
    despues = {f["item"]: f for f in jl(a.despues)["filas"]}
    r5a = {f["lista"]: f for f in jl(a.lectura_r5a)["filas"]}
    filas = []
    for item in sorted(set(antes) | set(despues)):
        f = antes.get(item) or despues[item]
        lec = LECTURA.get(item)
        if lec is None:
            raise SystemExit(f"candidato sin lectura: {item}")
        to = item.split("::")[0]
        filas.append({"item": item, "to": to, "tanda1": to in TANDA1, "sobre_S0-4b": item in antes,
                      "sobre_S0-5a": item in despues, "paginas_item": f["paginas_item"], "renglon": f["renglon"],
                      "siguen": f["siguen"], "abre_parrafo": f["abre_parrafo"],
                      "padre_es_seccion": f["padre_es_seccion"],
                      "con_la_regla": "unidad nueva después de la sección" if f["padre_es_seccion"]
                      else "la regla no lo alcanza (el padre es un punto)",
                      "R5-a_lo_lleva_al_cierre": item in r5a, "lectura_R5-a": (r5a.get(item) or {}).get("lectura"),
                      "lectura": lec[0], "nota": lec[1]})
    base = [f for f in filas if f["sobre_S0-4b"]]
    resumen = {"sobre_S0-4b": len(base), "fuera_de_ri_oc": sum(1 for f in base if f["to"] != "ri_oc"),
               "por_lectura_sobre_S0-4b": dict(collections.Counter(f["lectura"] for f in base)),
               "tanda1_sobre_S0-4b": {f["item"]: f["lectura"] for f in base if f["tanda1"]},
               "sobre_S0-5a": sum(f["sobre_S0-5a"] for f in filas),
               "solo_sobre_S0-5a": [f["item"] for f in filas if not f["sobre_S0-4b"]],
               "R5-a_lleva_al_cierre": [f["item"] for f in filas if f["R5-a_lo_lleva_al_cierre"]]}
    a.out_json.write_text(json.dumps({"resumen": resumen, "filas": filas}, ensure_ascii=False, indent=1) + "\n",
                          encoding="utf-8")
    md = ["# Candidatos de R5-a′ (título de bloque), con su página y mi lectura (S0-5a)", "",
          "Generado por `s0_5/scripts/lectura_candidatos_r5a2_S0-5a.py`. Criterio de `candidatos_r5a2_S0-5a.py`. La "
          "lectura es mía, a la vista del texto de la salida, sin abrir la página, y no está adjudicada.", "",
          f"Resumen: {json.dumps(resumen, ensure_ascii=False)}", "",
          "| ítem | tanda 1 | pp. | renglón | sigue | padre sección | con la regla | R5-a hoy | lectura | nota |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for f in filas:
        md.append(f"| `{f['item']}`{'' if f['sobre_S0-4b'] else ' (solo S0-5a)'} | {'sí' if f['tanda1'] else ''} | "
                  f"{','.join(map(str, f['paginas_item']))} | «{f['renglon'][:60]}» | «{(f['siguen'] or [''])[0][:50]}» | "
                  f"{'sí' if f['padre_es_seccion'] else 'no'} | {f['con_la_regla']} | "
                  f"{'al cierre (' + f['lectura_R5-a'] + ')' if f['R5-a_lo_lleva_al_cierre'] else ''} | "
                  f"{f['lectura']} | {f['nota']} |")
    a.out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
