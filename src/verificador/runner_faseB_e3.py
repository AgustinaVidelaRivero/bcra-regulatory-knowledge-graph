"""
runner_faseB_e3.py — FASE B de E3: calibración del verificador de completitud
sobre los 87 chunks de pro ACEPTADOS por E1 (fan-in de E2), AUTORIZADA con
precios resueltos.

Autorización vigente:
  - E3 (verificador, modelo fuerte): claude-sonnet-5 —
    P_in=2,00 / P_out=10,00 / P_cw=2,50 / P_cr=0,20 USD/MTok
    (precio introductorio vigente hasta el 31/08/2026).
  - Reintentos E1 (extractor, congelado): claude-haiku-4-5 —
    P_in=1,00 / P_out=5,00 / P_cw=1,25 / P_cr=0,10.
  - Estimación por fórmula sellada ≈ USD 0,93 — TOPE DURO USD 2,50
    (combinado E3+E1), freno por proyección antes de cada unidad.
  - Techo de salida de los REQUESTS DE REINTENTO: 16.384 tokens (el request
    base de E1 conserva su 8.192 sellado; verificación previa del mandato:
    la extracción incompleta de pro::2.3.1.1 emitió 4.932 tokens — un
    reintento que la complete necesita techo mayor).
  - E1 CONGELADO: su prompt, validador y calibración no se tocan. La caché
    de los reintentos va a una db PROPIA (cache/e1_reintentos.db) para no
    escribir en la db sellada de la calibración E1.

Ejecución SECUENCIAL (Decisión 4), por orden documental (campo `orden` de la
calibración E1). Persiste TODO en salida/faseB_pro/:
  - veredictos.jsonl        : TODOS los veredictos (verificaciones y
                              re-verificaciones), con capa determinística.
  - cola_humana.jsonl       : chunks flaggeados con flag + TODO.
  - extracciones_finales.jsonl : estado final por chunk + validación final.
  - resumen_faseB_e3.json   : agregados para el reporte (a)-(h).

Uso:  .venv/bin/python3 runner_faseB_e3.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import comun_e3
from comun_e3 import BASE, pares_calibracion
import prompt_e3
import cliente_e3
import ratchet_e3
import cliente_e1

MODEL_E3 = "claude-sonnet-5"
P_E3 = dict(precio_in_por_mtok=2.00, precio_out_por_mtok=10.00,
            precio_cache_write_por_mtok=2.50, precio_cache_read_por_mtok=0.20)
MODEL_E1 = "claude-haiku-4-5"
P_E1 = dict(precio_in_por_mtok=1.00, precio_out_por_mtok=5.00,
            precio_cache_write_por_mtok=1.25, precio_cache_read_por_mtok=0.10)

TOPE_USD = 2.50            # tope combinado E3 + reintentos E1
ESTIMADO_USD = 0.93        # fórmula sellada (estimacion_e3, precios resueltos)
MARGEN_UNIDAD_USD = 0.35   # peor caso por unidad: 2 llamadas E3 + 1 reintento E1
MAX_TOKENS_REINTENTO = 16384

RUN_LABEL_E3 = "e3_faseB_calibracion_pro"
RUN_LABEL_E1 = "e3_faseB_reintentos_e1"
DB_REINTENTOS_E1 = BASE / "cache" / "e1_reintentos.db"

OUT_DIR = BASE / "salida" / "faseB_pro"

EVAL_DIR = comun_e3.REPO / "data" / "experiment" / "evaluacion"


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(EVAL_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(f"ANTHROPIC_API_KEY ausente (esperada en {EVAL_DIR / '.env'})")
        return 1

    # Universo: los 87 aceptados, por orden documental (orden de la corrida E1).
    regs = comun_e3.cargar_extracciones_faseB()
    orden = {cid: r["orden"] for cid, r in regs.items()}
    pares = sorted(pares_calibracion(), key=lambda cv: orden[cv[0]["id"]])
    assert len(pares) == 87, f"esperados 87 aceptados, hay {len(pares)}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registro = ratchet_e3.RegistroE3(OUT_DIR)

    cli_e3 = cliente_e3.ClienteE3Real(**P_E3, tope_usd=TOPE_USD, run_label=RUN_LABEL_E3)
    cli_e1 = cliente_e1.ClienteE1Real(**P_E1, tope_usd=TOPE_USD,
                                      run_label=RUN_LABEL_E1,
                                      db_path=DB_REINTENTOS_E1)
    print(f"E3 modelo={MODEL_E3} ns={cliente_e3.namespace_e3()}", flush=True)
    print(f"E1 reintentos modelo={MODEL_E1} db={DB_REINTENTOS_E1.name} "
          f"max_tokens_reintento={MAX_TOKENS_REINTENTO}", flush=True)
    print(f"tope combinado=USD {TOPE_USD:.2f} | estimado=USD {ESTIMADO_USD:.2f}", flush=True)

    expedientes: list[dict] = []
    freno = None
    t0 = time.time()
    fin_path = OUT_DIR / "extracciones_finales.jsonl"
    with fin_path.open("w", encoding="utf-8") as ff:
        for i, (chunk, val) in enumerate(pares, 1):
            gasto_total = cli_e3.gasto_usd + cli_e1.gasto_usd
            if gasto_total + MARGEN_UNIDAD_USD > TOPE_USD:
                freno = (f"freno por tope combinado antes de {chunk['id']}: "
                         f"gasto USD {gasto_total:.4f} + margen {MARGEN_UNIDAD_USD} > {TOPE_USD}")
                print(freno, flush=True)
                break
            try:
                exp = ratchet_e3.ciclo_ratchet(
                    chunk, val,
                    cliente_verificador=cli_e3, cliente_extractor=cli_e1,
                    model_e3=MODEL_E3, model_e1=MODEL_E1,
                    registro=registro, max_tokens_reintento=MAX_TOKENS_REINTENTO)
            except (cliente_e3.TopeExcedido, cliente_e1.TopeExcedido) as e:
                freno = f"freno por tope de cliente en {chunk['id']}: {e}"
                print(freno, flush=True)
                break
            expedientes.append(exp)
            ff.write(json.dumps({
                "orden": orden[chunk["id"]],
                "chunk_id": chunk["id"],
                "estado": exp["estado"],
                "n_reintentos": len(exp["reintentos"]),
                "validacion_final": exp["validacion_final"],
            }, ensure_ascii=False) + "\n")
            ff.flush()

            ev1 = exp["veredictos"][0]
            print(f"[{i:2d}/87] {chunk['id']:<16s} {exp['estado']:<28s} "
                  f"faltantes={len(ev1['faltantes'])} "
                  f"gasto=USD {cli_e3.gasto_usd + cli_e1.gasto_usd:.4f}", flush=True)

    # ---------------- agregados para el reporte ---------------- #
    estados = Counter(e["estado"] for e in expedientes)
    tipos, sev = Counter(), Counter()
    n_faltantes_base = 0
    citas_total = citas_no_verif = 0
    con_faltantes_base = []
    for e in expedientes:
        ev1 = e["veredictos"][0]
        if ev1["faltantes"]:
            con_faltantes_base.append({"chunk_id": e["chunk_id"],
                                       "n": len(ev1["faltantes"])})
        n_faltantes_base += len(ev1["faltantes"])
        for f in ev1["faltantes"]:
            tipos[f.get("tipo", "?")] += 1
            sev[f.get("severidad", "?")] += 1
        for ev in e["veredictos"]:
            for f in ev["faltantes"]:
                citas_total += 1
                if not f.get("cita_verificada"):
                    citas_no_verif += 1

    resumen = {
        "modelos": {"e3": MODEL_E3, "e1_reintentos": MODEL_E1},
        "prefijo_hash_e3": prompt_e3.PREFIJO_HASH,
        "max_tokens_reintento": MAX_TOKENS_REINTENTO,
        "n_unidades_procesadas": len(expedientes),
        "freno": freno,
        "estados": dict(estados),
        "veredicto_base": {
            "completo_ok": estados.get("completo_ok_directo", 0),
            "con_faltantes": len(con_faltantes_base),
            "faltantes_total": n_faltantes_base,
            "faltantes_por_tipo": dict(tipos.most_common()),
            "faltantes_por_severidad": dict(sev.most_common()),
            "chunks_con_faltantes": con_faltantes_base,
        },
        "citas": {"total_reportadas": citas_total,
                  "no_verificadas": citas_no_verif,
                  "tasa_fabricacion": round(citas_no_verif / citas_total, 4) if citas_total else 0.0},
        "cliente_e3": cli_e3.resumen(),
        "cliente_e1_reintentos": cli_e1.resumen(),
        "gasto_total_usd": round(cli_e3.gasto_usd + cli_e1.gasto_usd, 4),
        "estimado_usd": ESTIMADO_USD,
        "tope_usd": TOPE_USD,
        "wall_time_min": round((time.time() - t0) / 60, 1),
    }
    with (OUT_DIR / "resumen_faseB_e3.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)

    cli_e3.close()
    cli_e1.close()
    print(json.dumps({k: resumen[k] for k in
                      ("n_unidades_procesadas", "estados", "gasto_total_usd",
                       "wall_time_min")}, ensure_ascii=False, indent=1), flush=True)
    print(f"-> {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
