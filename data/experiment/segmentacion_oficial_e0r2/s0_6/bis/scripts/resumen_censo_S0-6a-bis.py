"""El censo por regla de S0-6a-bis en cuentas (U-SEG-OFICIAL; USD 0, solo lectura; el «seguí» de S0-6a-bis: de las unidades
que no son las 40 filas ni las 286 leídas, solo cuentas por regla y por documento, sin ids, en todo lo que queda en
s0_6/bis/; los ids, en los archivos NO_ABRIR_ del paquete).

Uso: python -B resumen_censo_S0-6a-bis.py --censo <censo_por_regla> --claves <claves> --generalidad <json>
       --out-json <json> --out-md <md>

Por regla (sola, contra todas apagadas) y por documento: unidades antes y después, creadas, quitadas y cambiadas; la
generalidad; y la configuración final, con las claves por regla y por documento y por evento.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("censo", "claves", "generalidad", "out_json", "out_md"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    c = json.loads(a.censo.read_text(encoding="utf-8"))
    cl = json.loads(a.claves.read_text(encoding="utf-8"))
    g = json.loads(a.generalidad.read_text(encoding="utf-8"))

    def cuentas(por_to: dict) -> dict:
        return {to: {"unidades_antes": v["unidades_antes"], "unidades_despues": v["unidades_despues"],
                     "creadas": len(v["creadas"]), "quitadas": len(v["quitadas"]), "cambiadas": len(v["cambiadas"]),
                     "archivos_distintos": v["archivos_distintos"]} for to, v in sorted(por_to.items())}
    claves_doc = collections.defaultdict(lambda: collections.Counter())
    claves_regla_doc = collections.defaultdict(lambda: collections.Counter())
    for f in cl["filas"]:
        claves_doc[f["to"]][f["evento"]] += 1
        for r in f["reglas"]:
            claves_regla_doc[r][f["to"]] += 1
    res = {"final": {"resumen": c["final"]["resumen"] | {"tos": len(c["final"]["resumen"]["tos"])},
                     "por_to": cuentas(c["final"]["por_to"])},
           "eventos_final": c["eventos_final"],
           "atribucion_exacta": sum(1 for v in c["atribucion"].values() if v["igual_a_la_regla_sola"]),
           "con_regla_sola_y_unidad_final_distinta": sum(1 for v in c["atribucion"].values()
                                                        if v["reglas"] and not v["igual_a_la_regla_sola"]),
           "sin_ninguna_regla_sola": sum(1 for v in c["atribucion"].values() if not v["reglas"]),
           "eventos_de_una_regla_sola_que_no_estan_en_la_final":
               dict(collections.Counter(x["regla"] for x in c["eventos_de_una_regla_sola_que_no_estan_en_la_final"])),
           "claves": {"total": cl["claves"], "por_evento": cl["por_evento"], "por_regla": cl["por_regla"],
                      "sin_atribucion_exacta": len(cl["sin_atribucion_exacta"]),
                      "por_documento": {to: dict(v) for to, v in sorted(claves_doc.items())},
                      "por_regla_y_documento": {r: dict(sorted(v.items())) for r, v in sorted(claves_regla_doc.items())}},
           "por_regla": {r: {"resumen": v["resumen"] | {"tos": len(v["resumen"]["tos"])}, "por_to": cuentas(v["por_to"]),
                             "generalidad": {k: g[r][k] for k in ("filas", "documentos_donde_se_vio", "documentos_que_cambia",
                                                                  "documentos_que_cambia_donde_no_se_vio",
                                                                  "lista_donde_no_se_vio", "unidades_que_cambia",
                                                                  "general", "salen_de_la_bolsa")}}
                         for r, v in c["por_regla"].items()}}
    a.out_json.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = ["# Censo por regla de S0-6a-bis (cuentas, sin ids ni texto)", "",
          f"Generado por `s0_6/bis/scripts/resumen_censo_S0-6a-bis.py`. Los ids, en los archivos `NO_ABRIR_` del paquete.", "",
          "| regla | TOs con archivos distintos | TOs con unidades que cambian | de esos, donde no se vio | unidades (creadas / "
          "quitadas / cambiadas) | general | salen de la bolsa |", "|---|---|---|---|---|---|---|"]
    for r, v in res["por_regla"].items():
        s, ge = v["resumen"], v["generalidad"]
        md.append(f"| {r} | {s['tos']} | {ge['documentos_que_cambia']} | {ge['documentos_que_cambia_donde_no_se_vio']} | "
                  f"{s['creadas']} / {s['quitadas']} / {s['cambiadas']} | {'sí' if ge['general'] else 'no'} | "
                  f"{', '.join(ge['salen_de_la_bolsa']) or '—'} |")
    f = res["final"]["resumen"]
    md += ["", f"Final contra todas apagadas: {f['tos']} TOs con archivos distintos; unidades de esos TOs {f['unidades_antes']} → "
           f"{f['unidades_despues']}; creadas {f['creadas']}, quitadas {f['quitadas']}, cambiadas {f['cambiadas']}; "
           f"{res['eventos_final']} eventos: {res['atribucion_exacta']} iguales a una regla sola, "
           f"{res['con_regla_sola_y_unidad_final_distinta']} de una regla sola con la unidad final distinta, "
           f"{res['sin_ninguna_regla_sola']} sin ninguna regla sola.", "",
           "## Claves por documento (creadas / quitadas / cambiadas)", ""]
    for to, v in res["claves"]["por_documento"].items():
        md.append(f"- {to}: {v.get('creada', 0)} / {v.get('quitada', 0)} / {v.get('cambiada', 0)}")
    md += ["", "## Unidades que cambia cada regla sola, por documento (creadas / quitadas / cambiadas)", ""]
    for r, v in res["por_regla"].items():
        filas = [f"{to} {x['creadas']}/{x['quitadas']}/{x['cambiadas']}" for to, x in v["por_to"].items()
                 if x["creadas"] or x["quitadas"] or x["cambiadas"]]
        md.append(f"- **{r}** ({len(filas)} documentos): " + "; ".join(filas))
    a.out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(len(md), "renglones")


if __name__ == "__main__":
    main()
