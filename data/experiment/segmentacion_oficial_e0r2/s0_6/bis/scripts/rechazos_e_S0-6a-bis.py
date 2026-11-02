"""E de S0-6a y los rechazos por la columna (U-SEG-OFICIAL; USD 0, sin API; nota de decisiones, §3 E: «alcanza también los
87 rechazos, que se ven en el censo»).

Uso: python -B rechazos_e_S0-6a-bis.py --base <E0 de S0-5b> --regla-e <E0 con E sola> --final <E0 corregida> --out <json>
       [--out-detalle <json>]

S0-6a-bis: `--out` lleva solo cuentas por TO (sin páginas ni números); el detalle, rechazo por rechazo, va a
`--out-detalle` (un archivo NO_ABRIR_ del paquete).

Por TO, de `estructura_<to>.json`: los rechazos de raíz con motivo «raiz_en_columna_profunda_…» (`rechazos_header`) en
la E0 de S0-5b; cuántos se abren con E sola y en la corregida (el renglón —página, x0 y texto— ya no figura entre los
rechazos, con ningún motivo) y cuántos siguen rechazados, con el motivo que tienen ahora (un rechazo por la columna
puede pasar a rechazo por sucesión cuando E abre la raíz anterior). Solo página, número y motivo: sin texto.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RE_NUM = re.compile(r"^(\S+)")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def rechazos(d: Path, to: str) -> list[tuple]:
    e = jl(d / f"estructura_{to}.json")
    return [(r["pagina"], r["x0"], r["texto"], r["motivo"]) for r in e.get("rechazos_header", [])
            if str(r.get("motivo", "")).startswith("raiz_en_columna_profunda")]


def todos(d: Path, to: str) -> dict[tuple, str]:
    e = jl(d / f"estructura_{to}.json")
    return {(r["pagina"], r["x0"], r["texto"]): r["motivo"] for r in e.get("rechazos_header", [])}


def abiertas_e(d: Path, to: str) -> list[dict]:
    return [a for a in jl(d / f"estructura_{to}.json").get("avisos", []) if a.get("tipo") == "raiz_sucesora_e"]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("base", "regla_e", "final", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    ap.add_argument("--out-detalle", dest="out_detalle", type=Path)
    a = ap.parse_args()
    tos = sorted(p.name[len("estructura_"):-5] for p in a.base.glob("estructura_*.json"))
    por_to = {}
    for to in tos:
        b = rechazos(a.base, to)
        if not b:
            continue
        e, f = todos(a.regla_e, to), todos(a.final, to)
        por_to[to] = {"rechazos_S0-5b": len(b),
                      "se_abren_con_E_sola": sum(1 for r in b if r[:3] not in e),
                      "siguen_con_E_sola": sum(1 for r in b if r[:3] in e),
                      "siguen_en_la_corregida": sum(1 for r in b if r[:3] in f),
                      "avisos_raiz_sucesora_e": len(abiertas_e(a.regla_e, to)),
                      "rechazos": [{"pagina": r[0], "numero": (RE_NUM.match(r[2].strip()) or [None, None])[1],
                                    "motivo_S0-5b": r[3], "con_E_sola": e.get(r[:3], "abierta"),
                                    "en_la_corregida": f.get(r[:3], "abierta")} for r in b]}
    res = {"tos": len(por_to),
           "rechazos_S0-5b": sum(v["rechazos_S0-5b"] for v in por_to.values()),
           "se_abren_con_E_sola": sum(v["se_abren_con_E_sola"] for v in por_to.values()),
           "siguen_con_E_sola": sum(v["siguen_con_E_sola"] for v in por_to.values()),
           "siguen_en_la_corregida": sum(v["siguen_en_la_corregida"] for v in por_to.values()),
           "por_to": por_to}
    if a.out_detalle:
        a.out_detalle.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cuentas = {k: v for k, v in res.items() if k != "por_to"}
    cuentas["por_to"] = {t: {k: v for k, v in x.items() if k != "rechazos"} for t, x in res["por_to"].items()}
    a.out.write_text(json.dumps(cuentas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_to"}, ensure_ascii=False),
          {t: (v["rechazos_S0-5b"], v["se_abren_con_E_sola"], v["siguen_con_E_sola"], v["siguen_en_la_corregida"])
           for t, v in por_to.items()})


if __name__ == "__main__":
    main()
