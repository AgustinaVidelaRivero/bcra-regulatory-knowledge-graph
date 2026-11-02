"""U-REAPL: la suite y las shapes, regla por regla (sin los campos de ruta de los conteos), de cada paso contra el anterior (mandato U-REAPL, §4 y §5). USD 0, sin API.

Lee los `gate.json` y `suite_perfil_r2.json` de `gate_ureapl.py`. Por grafo:
  - el paso 1 contra el gate sellado de T3 (`tanda_final/t3/gate/e0_del_grafo/<grafo>/` y la E0 con partes, cuyo JSON no está
    versionado: se compara solo la E0 del grafo y la suite);
  - cada paso contra el anterior: las reglas de shapes cuyo resultado o conteos cambian (con las dos E0), con su severidad, y si cambia
    alguna bloqueante; los ítems de la suite cuyo estado cambia;
  - la regresión de la suite contra la entrada del grafo sellado en la fixture (`computar_regresion` de `scripts/regression_kg.py`,
    el método del registro, §62 y §75): la suite solo la computa sola cuando el sha256 del grafo es el de una entrada.
Escribe --salida (JSON); la consola, solo cuentas.

Uso, desde la raíz de la copia: <python> -B comparar_gates.py --gates <dir con paso1..paso5> --salida <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "scripts")
import regression_kg as RK  # noqa: E402

PASOS = ("paso1", "paso2", "paso3", "paso4", "paso5")
GRAFOS = {"con_cola": ("ens_128_r2b", "acum128"), "sin_cola": ("ens_128_r2b_sincola", "acum128_sincola")}
T3 = Path("data/experiment/tanda_final/t3/gate/e0_del_grafo")
SELLO = {"con_cola": "c43d66e503c2b27477cd17a5ffc2c64b6334d9525f0524d82ff248f04e7d96ac",
         "sin_cola": "398459a853590c584398243b543548d5634124d5577b3cfffe4332f0a61ac0fd"}


RUTAS = ("registro", "e0")      # los conteos de S28 y S31 llevan la ruta de su entrada: no cuentan


def sin_rutas(c):
    return {k: v for k, v in c.items() if k not in RUTAS} if isinstance(c, dict) else c


def reglas_cambian(a: dict, b: dict) -> dict:
    out = {}
    for rid in sorted(set(a) | set(b)):
        x, y = a.get(rid) or {}, b.get(rid) or {}
        cx, cy = sin_rutas(x.get("conteos")), sin_rutas(y.get("conteos"))
        if x.get("result") != y.get("result") or cx != cy:
            out[rid] = {"severidad": y.get("severidad") or x.get("severidad"), "resultado": [x.get("result"), y.get("result")],
                        "cambian_los_conteos": cx != cy,
                        "conteos": {k: [cx.get(k), cy.get(k)] for k in sorted(set(cx or {}) | set(cy or {}))
                                    if (cx or {}).get(k) != (cy or {}).get(k)} if isinstance(cx, dict) and isinstance(cy, dict) else None}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gates", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    fixture = json.loads(Path("scripts/regression_kg_esperado.json").read_text(encoding="utf-8"))
    out = {}
    for g, (carpeta, t3) in GRAFOS.items():
        sel = RK.seleccionar_esperado(fixture, SELLO[g])
        if sel is None:
            raise SystemExit(f"FRENO: la fixture no tiene la entrada del sello {g}")
        _, nombre, entrada = sel
        res = {"entrada_de_la_fixture": nombre, "pasos": {}}
        prev = None
        for p in PASOS:
            d = a.gates / p / carpeta
            if not (d / "gate.json").exists():
                continue
            gt = json.loads((d / "gate.json").read_text(encoding="utf-8"))
            su = json.loads((d / "suite_perfil_r2.json").read_text(encoding="utf-8"))
            reg = RK.computar_regresion(su["items"], entrada)
            fila = {"kg_sha256": gt["kg_sha256"],
                    "shapes_e0_del_grafo": [gt["shapes_e0_del_grafo"]["veredicto"], gt["shapes_e0_del_grafo"]["bloqueantes_en_fail"]],
                    "shapes_e0_con_partes": [gt["shapes_e0_con_partes"]["veredicto"], gt["shapes_e0_con_partes"]["bloqueantes_en_fail"]],
                    "suite_resumen": gt["suite"]["resumen"],
                    "regresion_contra_el_sello": {"n": reg["n_regresiones"], "items": sorted(x["item"] for x in reg["regresiones"]),
                                                  "coinciden": reg["coinciden"], "no_verificadas": len(reg["no_verificadas"])}}
            if p == "paso1":
                sh3 = json.loads((T3 / t3 / "shapes_perfil_r2_fase_r2b.json").read_text(encoding="utf-8"))["shapes"]
                su3 = json.loads((T3 / t3 / "suite_perfil_r2.json").read_text(encoding="utf-8"))
                fila["contra_el_gate_sellado_de_T3"] = {
                    "shapes_e0_del_grafo_reglas_que_cambian": reglas_cambian(sh3, gt["shapes_e0_del_grafo"]["reglas"]),
                    "suite_items_que_cambian": sorted(i["id"] for i in su3["items"] if gt["suite"]["items"].get(i["id"]) != i["estado"]),
                    "regresiones_de_T3": sorted(x["item"] for x in (su3.get("regresion") or {}).get("regresiones", []))}
            if prev is not None:
                fila["contra_el_paso_anterior"] = {
                    "shapes_e0_del_grafo": reglas_cambian(prev["shapes_e0_del_grafo"]["reglas"], gt["shapes_e0_del_grafo"]["reglas"]),
                    "shapes_e0_con_partes": reglas_cambian(prev["shapes_e0_con_partes"]["reglas"], gt["shapes_e0_con_partes"]["reglas"]),
                    "suite_items_que_cambian_de_estado": {i: [prev["suite"]["items"].get(i), e] for i, e in gt["suite"]["items"].items()
                                                          if prev["suite"]["items"].get(i) != e},
                    "regresiones_nuevas": sorted(set(fila["regresion_contra_el_sello"]["items"]) - set(res["pasos"][pp]["regresion_contra_el_sello"]["items"]))}
                cb = [r for x in ("shapes_e0_del_grafo", "shapes_e0_con_partes")
                      for r, v in fila["contra_el_paso_anterior"][x].items() if v["severidad"] == "bloqueante"
                      and v["resultado"][0] != v["resultado"][1]]
                fila["contra_el_paso_anterior"]["bloqueantes_que_cambian_de_resultado"] = sorted(set(cb))
            res["pasos"][p] = fila
            prev, pp = gt, p
        out[g] = res
    t = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(t, encoding="utf-8")
    for g, res in out.items():
        for p, f in res["pasos"].items():
            c = f.get("contra_el_paso_anterior") or {}
            print(g, p, f["shapes_e0_del_grafo"][0], f["shapes_e0_con_partes"][0], "regresiones", f["regresion_contra_el_sello"]["n"],
                  "| reglas que cambian:", sorted(set(c.get("shapes_e0_del_grafo", {})) | set(c.get("shapes_e0_con_partes", {}))),
                  "| ítems:", sorted(c.get("suite_items_que_cambian_de_estado", {})), "| bloqueantes:",
                  c.get("bloqueantes_que_cambian_de_resultado"),
                  "| T3:" if "contra_el_gate_sellado_de_T3" in f else "",
                  {k: (len(v) if not isinstance(v, list) else v) for k, v in (f.get("contra_el_gate_sellado_de_T3") or {}).items()})
    print("sha256:", hashlib.sha256(t.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
