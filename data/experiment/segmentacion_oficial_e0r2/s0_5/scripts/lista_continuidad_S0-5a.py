"""Lista para la autora del control de continuidad de la numeración (U-SEG-OFICIAL, S0-5a; USD 0, solo lectura).

Uso: python -B lista_continuidad_S0-5a.py --antes <control sobre S0-4b> --despues <control sobre S0-5a> --out <md>

Lo que el control da antes y después de las reglas (totales, por clase, por TO), los saltos que las reglas cierran y,
después de las reglas, los (ii) y (iii), y los (i) con descendientes tragados, que van a la decisión de la autora con el
criterio de la nota del 09/10/2026: en un TO de la tanda 1, regla por lista en S0-5; fuera de la tanda 1, límite
declarado y grupo 2 (la tanda 0 está fuera de S0-5). Los demás (i) van como información.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def key(f: dict) -> tuple:
    return (f["to"], f.get("subdocumento") or "", f["rotulo"])


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("antes", "despues", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    A, B = jl(a.antes), jl(a.despues)
    fa, fb = {key(f): f for f in A["filas"]}, {key(f): f for f in B["filas"]}
    resumen = lambda r: {k: r[k] for k in ("saltos", "por_clase", "ii_posible_referencia", "tos_con_saltos", "por_modo",
                                            "tanda1")}
    md = ["# Control de continuidad de la numeración: antes y después de las reglas de S0-5a", "",
          "Generado por `s0_5/scripts/lista_continuidad_S0-5a.py` desde las dos salidas de "
          "`control_continuidad_numeracion.py` (sobre S0-4b y sobre S0-5a, con los renglones de `extraer_lineas`).", "",
          f"- **Antes:** {json.dumps(resumen(A), ensure_ascii=False)}",
          f"- **Después:** {json.dumps(resumen(B), ensure_ascii=False)}",
          f"- **Por TO, después:** {json.dumps(B['por_to'], ensure_ascii=False)}", "",
          "## Saltos que las reglas cierran", ""]
    for k in sorted(set(fa) - set(fb)):
        f = fa[k]
        md.append(f"- `{f['to']}` {f['rotulo']} ({f['clase']}, {f['forma']}), antes en `{f.get('unidad')}`, con "
                  f"{len(f['descendientes_tragados'])} descendientes tragados")
    nuevos = sorted(set(fb) - set(fa))
    md += ["", f"Saltos nuevos después de las reglas: {len(nuevos)}."]
    cambian = [k for k in sorted(set(fa) & set(fb)) if fa[k] != fb[k]]
    md += [f"Saltos que siguen y cambian de unidad: {len(cambian)}."]
    for k in cambian:
        md.append(f"- `{k[0]}` {k[2]}: de `{fa[k].get('unidad')}` a `{fb[k].get('unidad')}`")
    p = B["para_la_autora"]
    grupos = collections.OrderedDict([("tanda 1: regla por lista en S0-5", [f for f in p if f["tanda"] == 1]),
                                      ("fuera de la tanda 1: límite declarado y grupo 2",
                                       [f for f in p if f["tanda"] is None]),
                                      ("tanda 0 (fuera de S0-5)", [f for f in p if f["tanda"] == 0])])
    md += ["", "## Lista para la autora (después de las reglas)", "",
           f"{len(p)} saltos: {json.dumps(dict(collections.Counter(f['clase'] for f in p)), ensure_ascii=False)}."]
    for g, fs in grupos.items():
        md += ["", f"### {g}: {len(fs)} ({json.dumps(dict(collections.Counter(f['to'] for f in fs)), ensure_ascii=False)})",
               "", "| TO | subdoc. | rótulo | clase | forma | en la unidad | renglón | fin del anterior | posible ref. | "
                   "descendientes tragados |", "|---|---|---|---|---|---|---|---|---|---|"]
        for f in fs:
            md.append(f"| {f['to']} | {f.get('subdocumento') or ''} | {f['rotulo']} | {f['clase']} | {f['forma']} | "
                      f"`{f.get('unidad') or ''}` | «{(f.get('renglon') or '')[:60]}» | "
                      f"«{(f.get('final_renglon_anterior') or '')[-40:]}» | "
                      f"{'sí' if f.get('posible_referencia') else ''} | "
                      f"{', '.join(d['rotulo'] + ' en `' + d['unidad'] + '`' for d in f['descendientes_tragados'])} |")
    a.out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(set(fa) - set(fb))} cerrados, {len(nuevos)} nuevos, {len(cambian)} cambian de unidad; para la autora "
          f"{len(p)}: " + ", ".join(f"{g.split(':')[0]} {len(fs)}" for g, fs in grupos.items()))


if __name__ == "__main__":
    main()
