"""El censo por regla de S0-5a en forma legible, con el antes y el después de cada unidad (U-SEG-OFICIAL; USD 0, solo
lectura de las salidas).

Uso: python -B antes_y_despues_S0-5a.py --censo <censo_por_regla_S0-5a.json> --claves <claves_S0-5a.json>
       --antes <E0 de S0-4b> --despues <E0 de S0-5a> --out-md <md> --out-jsonl <jsonl>

- `--out-md`: por regla (sola, contra todas apagadas), por TO, las unidades antes y después y las creadas, quitadas y
  cambiadas, y los archivos por TO que difieren; y la configuración final.
- `--out-jsonl`: una línea por clave de la lista declarada (`claves_S0-5a.json`): la regla, el evento, los campos que
  cambian, y del texto propio y de la herencia, lo de antes y lo de después (la herencia, como tramos tipo, unidad de
  origen y texto; solo los tramos que no están en los dos lados).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("censo", "claves", "antes", "despues", "out_md", "out_jsonl"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    c = jl(a.censo)
    md = ["# Censo por regla de S0-5a, por TO", "",
          "Generado por `s0_5/scripts/antes_y_despues_S0-5a.py` desde `censo_por_regla_S0-5a.json` (cada regla sola "
          "contra todas apagadas, que es la salida de S0-4b; y la configuración final). Unidades: las de "
          "`chunks_<to>.json`.", ""]
    bloques = [(f"Regla {r} sola", v) for r, v in c["por_regla"].items()] + [("Configuración final", c["final"])]
    for titulo, v in bloques:
        s = v["resumen"]
        md += [f"## {titulo}", "",
               f"{len(s['tos'])} TOs; unidades {s['unidades_antes']} → {s['unidades_despues']}; creadas {s['creadas']}, "
               f"quitadas {s['quitadas']}, cambiadas {s['cambiadas']}.", "",
               "| TO | unidades antes → después | creadas | quitadas | cambiadas | archivos que difieren |",
               "|---|---|---|---|---|---|"]
        for to, t in v["por_to"].items():
            md.append(f"| {to} | {t['unidades_antes']} → {t['unidades_despues']} | {len(t['creadas'])} | "
                      f"{len(t['quitadas'])} | {len(t['cambiadas'])} | {', '.join(t['archivos_distintos'])} |")
        md.append("")
    md += ["## Interacciones (eventos de la final que ninguna regla sola produce igual)", ""]
    md += [f"- `{x['id']}` ({x['evento']}): lo producen solas {', '.join(x['reglas_que_lo_producen_solas'])}"
           for x in c["interacciones"]]
    md += ["", f"Eventos de una regla sola que no están en la final: "
               f"{len(c['eventos_de_una_regla_sola_que_no_estan_en_la_final'])}."]
    a.out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    cache: dict = {}

    def ch(d: Path, to: str) -> dict:
        if (d, to) not in cache:
            cache[(d, to)] = {x["id"]: x for x in jl(d / f"chunks_{to}.json")}
        return cache[(d, to)]

    def tramos(u):
        return [(t["tipo"], t["unidad_origen"], t["texto"]) for t in u["herencia"]] if u else []

    n = 0
    with a.out_jsonl.open("w", encoding="utf-8") as fh:
        for f in jl(a.claves)["filas"]:
            an, de = ch(a.antes, f["to"]).get(f["clave"]), ch(a.despues, f["to"]).get(f["clave"])
            ta, td = tramos(an), tramos(de)
            fila = {"clave": f["clave"], "reglas": f["reglas"], "evento": f["evento"], "campos": f.get("campos"),
                    "texto_antes": an["texto"] if an else None,
                    "texto_despues": de["texto"] if de else None,
                    "herencia_solo_antes": [list(t) for t in ta if t not in td],
                    "herencia_solo_despues": [list(t) for t in td if t not in ta]}
            if an and de and an["texto"] == de["texto"]:
                fila["texto_antes"] = fila["texto_despues"] = "(igual)"
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
            n += 1
    print(f"{a.out_md.name}: {len(bloques)} bloques; {a.out_jsonl.name}: {n} claves")


if __name__ == "__main__":
    main()
