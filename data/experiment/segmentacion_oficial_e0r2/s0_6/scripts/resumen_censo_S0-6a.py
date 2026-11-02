"""El censo por regla de S0-6a en forma legible, sin texto de unidades (U-SEG-OFICIAL; USD 0, solo lectura; mandato de
S0-6a, §5: de las unidades que no son las 40 filas ni las 286 leídas, ids y cuentas por documento y por regla).

Uso: python -B resumen_censo_S0-6a.py --censo <censo_por_regla> --claves <claves> --generalidad <json> --out <md>

Por regla (sola, contra todas apagadas): los documentos que cambia y, por documento, las claves creadas, quitadas y
cambiadas (con los campos); la generalidad; y la configuración final, con la atribución de cada clave.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("censo", "claves", "generalidad", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    c = json.loads(a.censo.read_text(encoding="utf-8"))
    cl = json.loads(a.claves.read_text(encoding="utf-8"))
    g = json.loads(a.generalidad.read_text(encoding="utf-8"))
    out = ["# Censo por regla de S0-6a (ids y cuentas, sin texto)", "",
           f"Generado por `s0_6/scripts/resumen_censo_S0-6a.py` desde `{a.censo.name}`, `{a.claves.name}` y "
           f"`{a.generalidad.name}`.", ""]
    rf = c["final"]["resumen"]
    out += ["## Configuración final contra todas apagadas", "",
            f"- TOs que cambian: {len(rf['tos'])}; unidades antes {rf['unidades_antes']}, después {rf['unidades_despues']}; "
            f"creadas {rf['creadas']}, quitadas {rf['quitadas']}, cambiadas {rf['cambiadas']}.",
            f"- Eventos: {c['eventos_final']}; atribuidos exactamente a una regla sola o a varias: "
            f"{sum(1 for v in c['atribucion'].values() if v['igual_a_la_regla_sola'])}; interacciones: "
            f"{len(c['interacciones'])}; eventos de una regla sola que no están en la final: "
            f"{len(c['eventos_de_una_regla_sola_que_no_estan_en_la_final'])}.",
            f"- Claves: {cl['claves']} ({json.dumps(cl['por_evento'], ensure_ascii=False)}); por regla: "
            f"{json.dumps(cl['por_regla'], ensure_ascii=False)}; sin atribución exacta: {len(cl['sin_atribucion_exacta'])}.", ""]
    out += ["## Por regla", "",
            "| regla | TOs con archivos distintos | TOs con unidades que cambian | de esos, donde no se vio | unidades "
            "(creadas / quitadas / cambiadas) | general | salen de la bolsa |", "|---|---|---|---|---|---|---|"]
    for r, v in c["por_regla"].items():
        s = v["resumen"]
        out.append(f"| {r} | {len(s['tos'])} | {g[r]['documentos_que_cambia']} | {g[r]['documentos_que_cambia_donde_no_se_vio']} | "
                   f"{s['creadas']} / {s['quitadas']} / {s['cambiadas']} | {'sí' if g[r]['general'] else 'no'} | "
                   f"{', '.join(g[r]['salen_de_la_bolsa']) or '—'} |")
    out.append("")
    for r, v in c["por_regla"].items():
        out += [f"### Regla {r}", "",
                f"Filas: {', '.join(g[r]['filas'])}. Documentos donde se vio: {', '.join(g[r]['documentos_donde_se_vio'])}.", ""]
        for to, d in sorted(v["por_to"].items()):
            if not (d["creadas"] or d["quitadas"] or d["cambiadas"]):
                out.append(f"- `{to}`: archivos distintos {d['archivos_distintos']}, sin unidades que cambien")
                continue
            cam = "; ".join(f"`{i}` ({', '.join(f)})" for i, f in sorted(d["cambiadas"].items()))
            out.append(f"- `{to}` ({d['unidades_antes']} → {d['unidades_despues']}): creadas {len(d['creadas'])}"
                       f"{': ' + ', '.join(f'`{i}`' for i in d['creadas']) if d['creadas'] else ''}; quitadas "
                       f"{len(d['quitadas'])}{': ' + ', '.join(f'`{i}`' for i in d['quitadas']) if d['quitadas'] else ''}; "
                       f"cambiadas {len(d['cambiadas'])}{': ' + cam if cam else ''}")
        out.append("")
    if c["interacciones"]:
        out += ["## Interacciones (ninguna regla sola da la unidad final)", ""]
        out += [f"- `{x['id']}` ({x['evento']}; solas: {', '.join(x['reglas_que_lo_producen_solas']) or 'ninguna'})"
                for x in c["interacciones"]]
        out.append("")
    a.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(len(out), "renglones")


if __name__ == "__main__":
    main()
