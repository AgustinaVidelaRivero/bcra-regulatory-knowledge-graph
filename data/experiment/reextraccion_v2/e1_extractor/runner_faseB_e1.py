"""
runner_faseB_e1.py — FASE B de E1: calibración sobre el TO pro completo
(88 chunks de E0), AUTORIZADA con precios resueltos.

Autorización vigente:
  - modelo claude-haiku-4-5
  - P_in=1,00 / P_out=5,00 / P_cache_write=1,25 / P_cache_read=0,10 USD/MTok
  - estimación por la fórmula sellada ≈ USD 0,92 — TOPE DURO USD 2,00
  - gasto real por tokens de cada response; freno por proyección (ClienteE1Real)

Ejecución SECUENCIAL (Decisión 4: prefijo idéntico → jamás en paralelo frío).
Persiste TODO en salida/faseB_pro/:
  - extracciones.jsonl : una línea por chunk — tool_input CRUDO, stop_reason,
    usage de la response (input/output/cache_write/cache_read), resultado del
    validador (aceptados normalizados + rechazos con motivo + advertencias).
  - resumen_faseB.json : agregados para el reporte (a)–(g).
El crudo íntegro de cada response (thinking/content/usage completos) queda
además en cache/e1_extraccion.db vía llm_cache (write-through), y el log de
usage por response real en logs/cache_usage.jsonl (Decisión 3).

NO ensambla nada: E2 no existe todavía.

Uso:  .venv/bin/python3 runner_faseB_e1.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import comun_e1
from comun_e1 import BASE, EVAL_DIR, cargar_chunks
import prompt_e1
import cliente_e1
import validador_e1

MODEL = "claude-haiku-4-5"
P_IN, P_OUT, P_CW, P_CR = 1.00, 5.00, 1.25, 0.10   # USD/MTok, autorización fase B
TOPE_USD = 2.00
ESTIMADO_USD = 0.92                                 # fórmula sellada (estimacion_e1)
RUN_LABEL = "e1_faseB_calibracion_pro"

OUT_DIR = BASE / "salida" / "faseB_pro"


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(EVAL_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(f"ANTHROPIC_API_KEY ausente (esperada en {EVAL_DIR / '.env'})")
        return 1

    chunks = [c for c in cargar_chunks(("pro",))]
    assert len(chunks) == 88, f"esperados 88 chunks de pro, hay {len(chunks)}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUT_DIR / "extracciones.jsonl"

    cliente = cliente_e1.ClienteE1Real(
        precio_in_por_mtok=P_IN,
        precio_out_por_mtok=P_OUT,
        precio_cache_write_por_mtok=P_CW,
        precio_cache_read_por_mtok=P_CR,
        tope_usd=TOPE_USD,
        run_label=RUN_LABEL,
    )
    print(f"modelo={MODEL} | tope=USD {TOPE_USD:.2f} | estimado=USD {ESTIMADO_USD:.2f} | "
          f"namespace={cliente_e1.namespace_e1()}", flush=True)

    registros: list[dict] = []
    t0 = time.time()
    with jsonl_path.open("w", encoding="utf-8") as jf:
        for i, chunk in enumerate(chunks, 1):
            kwargs = prompt_e1.build_request_kwargs(chunk, model=MODEL)
            err = None
            cortado = None
            try:
                # U-B5.3 decisión 1: ante corte por max_tokens, UNA re-llamada
                # con 32k en el mismo pase; sin corte, kwargs viaja tal cual.
                resp, cortado = cliente_e1.crear_con_reintento_corte(
                    cliente, kwargs, doc=chunk["archivo"])
            except cliente_e1.TopeExcedido as e:
                print(f"FRENO POR TOPE en chunk {chunk['id']}: {e}", flush=True)
                err = f"tope_excedido: {e}"
                resp = None
            except Exception as e:
                # error de API tras los retries del SDK: se registra, NO se
                # cachea (llm_cache no persiste errores), se sigue.
                err = f"{type(e).__name__}: {e}"
                resp = None

            if resp is not None:
                u = resp.usage
                usage = {
                    "input_tokens": getattr(u, "input_tokens", 0) or 0,
                    "output_tokens": getattr(u, "output_tokens", 0) or 0,
                    "cache_write_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
                    "cache_read_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
                }
                stop_reason = getattr(resp, "stop_reason", None)
                tool_input = None
                for b in resp.content:
                    if getattr(b, "type", None) == "tool_use":
                        tool_input = b.input
                        break
                if stop_reason == "max_tokens":
                    # el reintento también cortó: error definitivo (decisión 5)
                    err = "max_tokens_hit_tras_reintento"
                elif tool_input is None:
                    err = f"no_tool_use stop_reason={stop_reason}"
            else:
                usage = {"input_tokens": 0, "output_tokens": 0,
                         "cache_write_tokens": 0, "cache_read_tokens": 0}
                stop_reason, tool_input = None, None

            val = (validador_e1.validar_salida(tool_input, chunk).as_dict()
                   if tool_input is not None else None)

            reg = {
                "orden": i,
                "chunk_id": chunk["id"],
                "unidad": chunk["unidad"],
                "titulo": chunk["titulo"],
                "stop_reason": stop_reason,
                "error": err,
                "usage": usage,
                "tool_input_crudo": tool_input,
                "validacion": val,
            }
            if cortado is not None:
                # decisión 2: ambos intentos persistidos (el crudo íntegro del
                # intento 1 ya está en la db por write-through).
                reg["reintento_corte"] = {
                    "max_tokens_reintento": cliente_e1.MAX_TOKENS_REINTENTO_CORTE,
                    "intento_1": cliente_e1.resumen_intento(cortado),
                }
            registros.append(reg)
            jf.write(json.dumps(reg, ensure_ascii=False) + "\n")
            jf.flush()

            if i % 5 == 0 or i == 88 or err:
                print(f"[{i:2d}/88] {chunk['id']:<14s} gasto=USD {cliente.gasto_usd:.4f} "
                      f"| in={usage['input_tokens']} out={usage['output_tokens']} "
                      f"cw={usage['cache_write_tokens']} cr={usage['cache_read_tokens']}"
                      + (f" | ERROR {err}" if err else ""), flush=True)

            if err and err.startswith("tope_excedido"):
                break

    # ---------------- agregados para el reporte ----------------
    ok = [r for r in registros if r["error"] is None and r["validacion"] is not None]
    tot_u = {k: sum(r["usage"][k] for r in registros) for k in
             ("input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens")}
    for r in registros:
        rc = r.get("reintento_corte")
        if rc:  # el intento cortado también se pagó: entra al usage total (D2)
            for k in tot_u:
                tot_u[k] += rc["intento_1"]["usage"][k]
    gasto = {
        "input_usd": tot_u["input_tokens"] / 1e6 * P_IN,
        "output_usd": tot_u["output_tokens"] / 1e6 * P_OUT,
        "cache_write_usd": tot_u["cache_write_tokens"] / 1e6 * P_CW,
        "cache_read_usd": tot_u["cache_read_tokens"] / 1e6 * P_CR,
    }
    gasto["total_usd"] = sum(gasto.values())

    tipos, preds, motivos = Counter(), Counter(), Counter()
    sujeto_id_usos, propuestos, omisiones, advertencias = Counter(), [], [], Counter()
    n_ent = n_rel = n_rech = 0
    for r in ok:
        v = r["validacion"]
        n_ent += len(v["entidades"])
        n_rel += len(v["relaciones"])
        n_rech += len(v["rechazos"])
        for e in v["entidades"]:
            tipos[e["type"]] += 1
        for rel in v["relaciones"]:
            preds[rel["predicate"]] += 1
            if rel["sujeto_id"]:
                sujeto_id_usos[rel["sujeto_id"]] += 1
            if rel["sujeto_propuesto"]:
                propuestos.append({
                    "chunk_id": r["chunk_id"],
                    "sujeto_propuesto": rel["sujeto_propuesto"],
                    "padre_sugerido": rel["sujeto_propuesto_padre_sugerido"],
                    "predicate": rel["predicate"],
                })
        for m, c in v["metricas"]["rechazos_por_motivo"].items():
            motivos[m] += c
        for a in v["advertencias"]:
            advertencias[a["tipo"]] += 1
        if v["omisiones_no_prosa"]:
            omisiones.append({"chunk_id": r["chunk_id"], "omisiones": v["omisiones_no_prosa"]})

    # (f) caching real: cache_read por llamada 2..88
    reads_2_88 = [r["usage"]["cache_read_tokens"] for r in registros[1:]]
    caching = {
        "llamada_1": registros[0]["usage"] if registros else None,
        "llamadas_2_en_adelante": {
            "n": len(reads_2_88),
            "cache_read_min": min(reads_2_88) if reads_2_88 else None,
            "cache_read_max": max(reads_2_88) if reads_2_88 else None,
            "con_cache_read_cero": sum(1 for x in reads_2_88 if x == 0),
        },
    }

    resumen = {
        "modelo": MODEL,
        "run_label": RUN_LABEL,
        "prefijo_hash": prompt_e1.PREFIJO_HASH,
        "n_chunks": len(registros),
        "n_ok": len(ok),
        "errores": [{"chunk_id": r["chunk_id"], "error": r["error"]}
                    for r in registros if r["error"]],
        "elementos": {
            "entidades_aceptadas": n_ent,
            "relaciones_aceptadas": n_rel,
            "rechazos": n_rech,
            "rechazos_por_motivo": dict(motivos),
            "advertencias_por_tipo": dict(advertencias),
            "entidades_por_tipo": dict(tipos.most_common()),
            "relaciones_por_predicado": dict(preds.most_common()),
        },
        "sujetos": {
            "usos_sujeto_id_total": sum(sujeto_id_usos.values()),
            "sujeto_id_distintos": len(sujeto_id_usos),
            "usos_por_sujeto_id": dict(sujeto_id_usos.most_common()),
            "propuestos_cuarentena": propuestos,
        },
        "omisiones_no_prosa": omisiones,
        "usage_total": tot_u,
        "caching": caching,
        "gasto": {k: round(v, 4) for k, v in gasto.items()},
        "estimado_usd": ESTIMADO_USD,
        "tope_usd": TOPE_USD,
        "cliente": cliente.resumen(),
        "wall_time_min": round((time.time() - t0) / 60, 1),
    }
    with (OUT_DIR / "resumen_faseB.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)

    cliente.close()
    print(json.dumps({k: resumen[k] for k in
                      ("n_chunks", "n_ok", "gasto", "wall_time_min")},
                     ensure_ascii=False, indent=1), flush=True)
    print(f"-> {jsonl_path}\n-> {OUT_DIR / 'resumen_faseB.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
