"""Selftest del control de continuidad de la numeración (U-SEG-OFICIAL, S0-5a; USD 0, sin API, solo lectura).

Uso: python -B selftest_control_continuidad.py --antes <E0 de S0-4b> --despues <E0 de S0-5a> --lineas <caché de
       renglones> [--out <txt>]

Los casos de la nota del 09/10/2026 al pie del mandato de S0-5a, sobre las dos salidas medidas, y un caso sintético:
- antes de las reglas, como (ii), en la unidad que hoy los tiene: `ri_rml::1.2.4` en `ri_rml::1.3`; en snp_tr, 1.3.4,
  1.3.5, 1.3.6, 1.4 y 1.5 en `snp_tr::1.6::intro`, con sus descendientes (1.3.4.1, 1.3.4.2, 1.3.5.1 a 1.3.5.3, 1.3.6.1,
  1.3.6.2, 1.4.1 a 1.4.4, 1.5.1, 1.5.2, 1.5.2.1 y 1.5.2.2);
- después de las reglas, ninguno es un salto;
- un (i): pimf, donde el PDF salta de 2.1.3 a 2.1.3.5 (2.1.3.1 a 2.1.3.4), antes y después;
- una remisión con `posible_referencia`: 1.3.1.9 de ctacte, en `ctacte::1.5.2.8`, antes y después (la tanda 0 no cambia);
- sintético: un hueco tragado por el hermano anterior (ii), un rótulo pegado al título («1.5.Código 11») que cuenta como
  rótulo, un hueco que no aparece en ninguna unidad (i, sin renglones del PDF), una cola con `posible_referencia` y un
  descendiente tragado.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import control_continuidad_numeracion as C  # noqa: E402

DESC_SNP_TR = {"1.3.4": ["1.3.4.1", "1.3.4.2"], "1.3.5": ["1.3.5.1", "1.3.5.2", "1.3.5.3"],
               "1.3.6": ["1.3.6.1", "1.3.6.2"], "1.4": ["1.4.1", "1.4.2", "1.4.3", "1.4.4"],
               "1.5": ["1.5.1", "1.5.2", "1.5.2.1", "1.5.2.2"]}

resultados: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> None:
    resultados.append((ok, msg))
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def saltos(e0: Path, lineas: Path | None, to: str) -> dict:
    return {f["rotulo"]: f for f in C.control_to(e0, lineas, to)["saltos"]}


def medidos(antes: Path, despues: Path, lineas: Path) -> None:
    print("== casos medidos (S0-4b y S0-5a)")
    a, d = saltos(antes, lineas, "ri_rml"), saltos(despues, lineas, "ri_rml")
    f = a.get("1.2.4", {})
    check(f.get("clase") == "ii" and f.get("unidad") == "ri_rml::1.3" and f.get("forma") == "cola",
          f"antes: ri_rml 1.2.4 es (ii), cola, en ri_rml::1.3 — {f.get('clase')}, {f.get('forma')}, {f.get('unidad')}")
    check(not d, f"después: ri_rml sin saltos — {sorted(d)}")
    a, d = saltos(antes, lineas, "snp_tr"), saltos(despues, lineas, "snp_tr")
    ok = all(a.get(r, {}).get("clase") == "ii" and a[r].get("unidad") == "snp_tr::1.6::intro" for r in DESC_SNP_TR)
    check(ok, "antes: snp_tr 1.3.4, 1.3.5, 1.3.6, 1.4 y 1.5 son (ii) en snp_tr::1.6::intro — "
              f"{[(r, a.get(r, {}).get('clase'), a.get(r, {}).get('unidad')) for r in DESC_SNP_TR]}")
    ok = all(sorted(x["rotulo"] for x in a.get(r, {}).get("descendientes_tragados", [])) == sorted(ds)
             and all(x["unidad"] == "snp_tr::1.6::intro" for x in a[r]["descendientes_tragados"])
             for r, ds in DESC_SNP_TR.items())
    check(ok, "antes: con sus descendientes, todos en snp_tr::1.6::intro (19)")
    check(not d, f"después: snp_tr sin saltos — {sorted(d)}")
    for e0, cuando in ((antes, "antes"), (despues, "después")):
        p = saltos(e0, lineas, "pimf")
        ok = all(p.get(f"2.1.3.{k}", {}).get("clase") == "i" for k in range(1, 5)) and "2.1.3.5" not in p
        check(ok, f"{cuando}: pimf 2.1.3.1 a 2.1.3.4 son (i), el PDF salta a 2.1.3.5 — "
                  f"{[(r, x['clase']) for r, x in p.items() if r.startswith('2.1.3.')]}")
        c = saltos(e0, lineas, "ctacte").get("1.3.1.9", {})
        check(c.get("clase") == "ii" and c.get("unidad") == "ctacte::1.5.2.8" and c.get("posible_referencia") is True,
              f"{cuando}: ctacte 1.3.1.9 es (ii) con posible_referencia, en ctacte::1.5.2.8 — "
              f"{c.get('clase')}, {c.get('unidad')}, «{c.get('final_renglon_anterior')}»")


def sintetico() -> None:
    print("== caso sintético")
    def p(n, hijos=()):
        return {"tipo": "punto", "numero": n, "hijos": list(hijos)}
    est = {"modo_lectura": "vigente", "subdocumentos": [],
           "secciones": [{"tipo": "seccion", "numero": "1", "prefijo": None,
                          "hijos": [p("1.1"), p("1.2", [p("1.2.1"), p("1.2.2")]), p("1.4"), p("1.7")]}]}
    chunks = [{"id": "x::1.1", "texto": "1.1. Primero."},
              {"id": "x::1.2::intro", "texto": "1.2. Segundo."},
              {"id": "x::1.2.1", "texto": "1.2.1. Uno."},
              {"id": "x::1.2.2", "texto": "1.2.2. Dos.\n1.3. Tragado por el anterior.\n1.3.1. Su hijo."},
              {"id": "x::1.4", "texto": "1.4. Cuarto, que remite al punto\n1.2.3. de esta sección.\n1.5.Código 11"},
              {"id": "x::1.7", "texto": "1.7. Séptimo."}]
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "estructura_x.json").write_text(json.dumps(est), encoding="utf-8")
        (d / "chunks_x.json").write_text(json.dumps(chunks), encoding="utf-8")
        s = saltos(d, None, "x")
    f = s.get("1.3", {})
    check(f.get("clase") == "ii" and f.get("forma") == "hueco" and f.get("unidad") == "x::1.2.2"
          and not f.get("posible_referencia") and [x["rotulo"] for x in f.get("descendientes_tragados", [])] == ["1.3.1"],
          f"hueco 1.3: (ii) en x::1.2.2, sin posible_referencia, con 1.3.1 tragado — {f.get('clase')}, {f.get('unidad')}")
    f = s.get("1.5", {})
    check(f.get("clase") == "ii" and f.get("unidad") == "x::1.4", f"«1.5.Código 11» cuenta como rótulo: (ii) en x::1.4 — "
                                                                   f"{f.get('clase')}, {f.get('unidad')}")
    f = s.get("1.6", {})
    check(f.get("clase") == "i", f"hueco 1.6, que no aparece en ninguna unidad ni hay renglones del PDF: (i) — "
                                 f"{f.get('clase')}")
    f = s.get("1.2.3", {})
    check(f.get("clase") == "ii" and f.get("forma") == "cola" and f.get("posible_referencia") is True,
          f"cola 1.2.3 tras «…al punto»: (ii) con posible_referencia — {f.get('clase')}, {f.get('forma')}")
    check(sorted(s) == ["1.2.3", "1.3", "1.5", "1.6"], f"ningún otro salto — {sorted(s)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", type=Path, required=True)
    ap.add_argument("--despues", type=Path, required=True)
    ap.add_argument("--lineas", type=Path, required=True)
    a = ap.parse_args()
    medidos(a.antes, a.despues, a.lineas)
    sintetico()
    n = sum(ok for ok, _ in resultados)
    print(f"\nSELFTEST CONTROL DE CONTINUIDAD: {n}/{len(resultados)} PASS")
    return 0 if n == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
