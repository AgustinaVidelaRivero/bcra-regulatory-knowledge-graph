#!/usr/bin/env python3
"""antecedente_HB2_faseB.py — El antecedente de H-B2, medido (USD 0: solo lee archivos).

Para las 12 sesiones de la corrida 2 de la fase B (smoke/resultados/faseB_corrida2/, CLI
2.1.241, --max-turns 12), cuenta con la misma función que usa el lanzador de A2.1
(lanzar_agente_a2_1.conteos_hb2) los mensajes del asistente, los tool_use, los
tool_result, el máximo de tool_use por mensaje y las llamadas del log R1, frente al
num_turns y el subtype del `result`.

Uso: .venv/bin/python -B antecedente_HB2_faseB.py   (escribe controles/antecedente_HB2_faseB.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BANCO_DIR = AQUI.parent
for _p in (str(AQUI), str(BANCO_DIR), str(BANCO_DIR / "agentes")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import lanzar_agente as LA                  # noqa: E402
import lanzar_agente_a2_1 as L21            # noqa: E402
from comun_banco import rel_repo            # noqa: E402

FASE_B = BANCO_DIR / "smoke" / "resultados" / "faseB_corrida2"


def metas_faseB() -> list[dict]:
    """Las 12 sesiones con la forma que evalúa correr_a2_1.evaluar_hb2 (pregunta_id, brazo, hb2)."""
    out = []
    for p in sorted(FASE_B.glob("meta_*.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        pid = m["pregunta_id"]
        lineas = (FASE_B / f"stream_{pid}.jsonl").read_text(encoding="utf-8").splitlines()
        res = LA.parsear_stream(lineas)["result"]
        log = LA.leer_log_r1(FASE_B / f"log_r1_{pid}.jsonl")
        out.append({"pregunta_id": f"faseB:{pid}", "brazo": f"faseB_{m['brazo']}",
                    "hb2": {"max_turns_efectivo": m["corte_R5"]["max_turns"]} | L21.conteos_hb2(lineas, res, log)})
    return out


def main() -> int:
    filas = [{"id": m["pregunta_id"].split(":", 1)[1], "max_turns": m["hb2"]["max_turns_efectivo"]} | m["hb2"]
             for m in metas_faseB()]
    out = {"unidad": "A2.1, tramo 1 — antecedente de H-B2 (fase B, corrida 2)",
           "comando": "python3 -B data/experiment/banco_mcp/a2_1/antecedente_HB2_faseB.py",
           "fuente": rel_repo(FASE_B), "n_sesiones": len(filas),
           "num_turns_igual_a_tool_result_mas_1": sum(f["num_turns"] == f["n_tool_result"] + 1 for f in filas),
           "num_turns_igual_a_mensajes_asistente": sum(f["num_turns"] == f["n_mensajes_asistente"] for f in filas),
           "sesiones_con_num_turns_mayor_que_max_turns": [f["id"] for f in filas if f["num_turns"] > f["max_turns"]],
           "sesiones_con_corte": [f["id"] for f in filas if f["corte_disparado"]],
           "sesiones_con_llamadas_paralelas": [f["id"] for f in filas if f["max_tool_use_por_mensaje"] > 1],
           "filas": filas}
    (AQUI / "controles").mkdir(exist_ok=True)
    (AQUI / "controles" / "antecedente_HB2_faseB.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                                                     encoding="utf-8")
    for f in filas:
        print(f["id"], "num_turns", f["num_turns"], "asistente", f["n_mensajes_asistente"], "tool_use", f["n_tool_use"],
              "tool_result", f["n_tool_result"], "max/msj", f["max_tool_use_por_mensaje"], "log_r1", f["n_llamadas_log_r1"],
              f["subtype"])
    print({k: v for k, v in out.items() if k not in ("filas", "unidad", "comando", "fuente")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
