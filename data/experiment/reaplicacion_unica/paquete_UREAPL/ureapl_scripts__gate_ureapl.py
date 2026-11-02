"""U-REAPL: shapes (perfil r2, fase r2b) y suite (perfil r2, con la fixture de la raíz) sobre el ensamblado de un paso, con los
argumentos de `tanda_final/t3/scripts/gate_tf.sh`. Corre desde la raíz de la COPIA del repo. USD 0, sin API.

  - shapes, con la API de `scripts/shapes_validator.py` (`evaluar_perfil_r2`, como `reresolucion_catalogo/reresolver_catalogo.py`
    `shapes`), dos veces: con la E0 del grafo y con la E0 con las partes por corte (la que rige para S30 y S31; registro, §62). Sin G,
    con los ids de S19 y la entrada del esqueleto por defecto (los de `catalogo_unico/generados_r2/`, los del CLI); con G (los pasos con
    las claves), con los de G;
  - suite, con `scripts/regression_kg.py` y los argumentos de `gate_tf.sh`; con G, además, el catálogo de la suite de G y
    `--generados-resolucion G` (como `reresolver_catalogo.suite`).
Escribe en <salida>/: `gate.json` (por regla: resultado, severidad, resumen y conteos; por ítem de la suite: estado; la regresión contra
la entrada de la fixture), y las salidas de la suite (`suite_perfil_r2.{md,json}` y su consola). Ningún detalle de las shapes.

Uso: <repo>/.venv/bin/python -B gate_ureapl.py --ensamblado <dir con r2/> --e0 <E0 del grafo> --e0-partes <E0 con partes>
       --salida <dir> [--generados-resolucion G]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
RAIZ = Path.cwd()
sys.path.insert(0, str(RAIZ / "scripts"))
import shapes_validator as SV  # noqa: E402

CAT_SUITE = Path("data/experiment/catalogo_unico/generados_r2/catalogo_suite_r2.json")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def shapes(g: dict, registro: Path, e0: Path, gen: Path | None) -> dict:
    vocab = SV.cargar_vocabulario_r2()
    kw = {} if gen is None else {"ids_s19_ruta": str(gen / "ids_s19_r2.json"),
                                  "excepciones_ruta": str(gen / "entrada_esqueleto_r2.json")}
    res, veredicto, meta = SV.evaluar_perfil_r2(g, vocab, "r2b", str(registro), str(e0), **kw)
    return {"veredicto": veredicto, "bloqueantes_en_fail": meta["bloqueantes_en_fail"],
            "bloqueantes_no_computables": meta["bloqueantes_no_computables"],
            "catalogo_s19_n_ids": meta["catalogo"]["n_ids"], "e0": str(e0),
            "reglas": {rid: {"severidad": "bloqueante" if rid in meta["bloqueantes"] else "informativa",
                             "result": r["result"], "resumen": r["resumen"], "conteos": r.get("conteos")}
                       for rid, r in res.items()}}


def suite(kg: Path, registro_dir: Path, gen: Path | None, salida: Path) -> dict:
    cat = (gen / "catalogo_suite_r2.json") if gen else CAT_SUITE
    cmd = [sys.executable, "-B", "scripts/regression_kg.py", "--kg", str(kg), "--perfil", "r2", "--generacion", "3",
           "--catalogo", str(cat), "--politica-cuarentena", "flaggeada", "--registro-dir", str(registro_dir),
           "--esperado", "scripts/regression_kg_esperado.json", "--out", str(salida / "suite_perfil_r2.md")]
    if gen is not None:
        cmd += ["--generados-resolucion", str(gen)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(cmd, cwd=RAIZ, env=env, capture_output=True, text=True)
    (salida / "consola_suite.txt").write_text(r.stdout + r.stderr + f"rc={r.returncode}\n", encoding="utf-8")
    out = json.loads((salida / "suite_perfil_r2.json").read_text(encoding="utf-8"))
    reg = out.get("regresion") or {}
    return {"rc": r.returncode, "resumen": out.get("resumen"),
            "items": {i["id"]: i["estado"] for i in out.get("items", [])},
            "regresion": {"entrada": reg.get("entrada"), "n_regresiones": reg.get("n_regresiones"),
                          "regresiones": [x.get("item") for x in reg.get("regresiones", [])],
                          "coinciden": reg.get("coinciden"), "no_verificadas": len(reg.get("no_verificadas", []))}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ensamblado", type=Path, required=True)
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--e0-partes", dest="e0_partes", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--generados-resolucion", dest="gen", type=Path, default=None)
    a = ap.parse_args()
    r2 = a.ensamblado / "r2"
    kg_path = r2 / "kg.json"
    a.salida.mkdir(parents=True, exist_ok=True)
    g = json.loads(kg_path.read_text(encoding="utf-8"))
    out = {"kg_sha256": sha(kg_path), "generados_resolucion": str(a.gen) if a.gen else None,
           "shapes_e0_del_grafo": shapes(g, r2 / "no_mapeados_sujetos.jsonl", a.e0, a.gen),
           "shapes_e0_con_partes": shapes(g, r2 / "no_mapeados_sujetos.jsonl", a.e0_partes, a.gen),
           "suite": suite(kg_path, r2, a.gen, a.salida)}
    (a.salida / "gate.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    s1, s2, su = out["shapes_e0_del_grafo"], out["shapes_e0_con_partes"], out["suite"]
    print(json.dumps({"shapes_e0_del_grafo": [s1["veredicto"], s1["bloqueantes_en_fail"]],
                      "shapes_e0_con_partes": [s2["veredicto"], s2["bloqueantes_en_fail"]],
                      "suite": [su["rc"], su["resumen"], su["regresion"]["n_regresiones"]]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
