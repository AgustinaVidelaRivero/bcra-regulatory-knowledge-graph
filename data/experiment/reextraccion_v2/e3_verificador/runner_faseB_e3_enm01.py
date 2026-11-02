"""
runner_faseB_e3_enm01.py — FASE B de la mini-recalibración de la ENMIENDA 01:
verificación E3 completa de las unidades de pro (chunks + mini-chunks)
aceptadas por el fan-in de la re-extracción enm01, con el blanco de
completitud enmendado (fuente del hijo = texto propio; fuente del mini = su
bloque) y mini-ratchet con tope 1 (§2.e de la enmienda).

Autorización vigente (freno condicional cumplido, estimación total USD 2,60):
  - E3 (verificador): claude-sonnet-5 — 2,00/10,00/2,50/0,20 USD/MTok.
  - Reintentos E1: claude-haiku-4-5 — 1,00/5,00/1,25/0,10.
  - TOPE DURO COMBINADO de la fase B: USD 5,00. Este runner toma como tope
    propio (5,00 − gasto real de la corrida E1 enm01), leído del resumen.
  - Prefijo E3 INTACTO (hash sellado 21a836c7de6d, calibradores congelados);
    las keys locales igual rotan (fuente y extracciones nuevos) — se paga la
    verificación completa; el prefijo de API se escribe 1 vez por corrida.
  - Techo de salida de reintentos: 16.384 (precedente de la corrida sellada).

La corrida sellada (salida/faseB_pro/) queda INTACTA: todo persiste en
salida/faseB_pro_enm01/ (veredictos.jsonl, cola_humana.jsonl,
extracciones_finales.jsonl, resumen_faseB_e3.json).

Ejecución SECUENCIAL (Decisión 4). Uso:  .venv/bin/python3 runner_faseB_e3_enm01.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import comun_e3
from comun_e3 import BASE, E0_SALIDA_ENM01, cargar_chunks, cargar_extracciones, pares_de
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

TOPE_COMBINADO_USD = 5.00
MARGEN_UNIDAD_USD = 0.35
MAX_TOKENS_REINTENTO = 16384

RUN_LABEL_E3 = "e3_faseB_pro_enm01"
RUN_LABEL_E1 = "e3_faseB_reintentos_e1_enm01"
DB_REINTENTOS_E1 = BASE / "cache" / "e1_reintentos.db"

E1_ENM01 = comun_e3.E1_DIR / "salida" / "faseB_pro_enm01"
OUT_DIR = BASE / "salida" / "faseB_pro_enm01"

EVAL_DIR = comun_e3.REPO / "data" / "experiment" / "evaluacion"


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(EVAL_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(f"ANTHROPIC_API_KEY ausente (esperada en {EVAL_DIR / '.env'})")
        return 1

    resumen_e1 = json.loads((E1_ENM01 / "resumen_faseB.json").read_text(encoding="utf-8"))
    gasto_e1 = resumen_e1["cliente"]["gasto_usd_real"]
    tope_usd = round(TOPE_COMBINADO_USD - gasto_e1, 4)
    assert tope_usd > 0.5, f"remanente de tope insuficiente: {tope_usd}"

    chunks = cargar_chunks(("pro",), e0_dir=E0_SALIDA_ENM01)
    regs = cargar_extracciones(E1_ENM01 / "extracciones.jsonl")
    pares = pares_de(chunks, regs)
    print(f"unidades aceptadas para E3: {len(pares)} de {len(chunks)}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registro = ratchet_e3.RegistroE3(OUT_DIR)

    cli_e3 = cliente_e3.ClienteE3Real(**P_E3, tope_usd=tope_usd, run_label=RUN_LABEL_E3)
    cli_e1 = cliente_e1.ClienteE1Real(**P_E1, tope_usd=tope_usd,
                                      run_label=RUN_LABEL_E1,
                                      db_path=DB_REINTENTOS_E1)
    print(f"E3 modelo={MODEL_E3} ns={cliente_e3.namespace_e3()}", flush=True)
    print(f"E1 reintentos modelo={MODEL_E1} ns={cliente_e1.namespace_e1()} "
          f"max_tokens_reintento={MAX_TOKENS_REINTENTO}", flush=True)
    print(f"tope combinado=USD {TOPE_COMBINADO_USD:.2f} | gasto E1 previo=USD "
          f"{gasto_e1:.4f} | tope de este runner=USD {tope_usd:.4f}", flush=True)

    expedientes: list[dict] = []
    freno = None
    t0 = time.time()
    n_tot = len(pares)
    fin_path = OUT_DIR / "extracciones_finales.jsonl"
    with fin_path.open("w", encoding="utf-8") as ff:
        for i, (chunk, val) in enumerate(pares, 1):
            gasto_total = cli_e3.gasto_usd + cli_e1.gasto_usd
            if gasto_total + MARGEN_UNIDAD_USD > tope_usd:
                freno = (f"freno por tope antes de {chunk['id']}: gasto USD "
                         f"{gasto_total:.4f} + margen {MARGEN_UNIDAD_USD} > {tope_usd}")
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
                "orden": i,
                "chunk_id": chunk["id"],
                "tipo_unidad": chunk["tipo"],
                "estado": exp["estado"],
                "n_reintentos": len(exp["reintentos"]),
                "validacion_final": exp["validacion_final"],
            }, ensure_ascii=False) + "\n")
            ff.flush()

            ev1 = exp["veredictos"][0]
            print(f"[{i:3d}/{n_tot}] {chunk['id']:<28s} {exp['estado']:<32s} "
                  f"faltantes={len(ev1['faltantes'])} "
                  f"gasto=USD {cli_e3.gasto_usd + cli_e1.gasto_usd:.4f}", flush=True)

    # ---------------- agregados para el reporte ---------------- #
    tipo_por_id = {c["id"]: ("mini" if c["tipo"] == "mini_chunk" else "punto")
                   for c in chunks}
    estados = Counter(e["estado"] for e in expedientes)
    estados_por_clase = {"punto": Counter(), "mini": Counter()}
    tipos, sev = Counter(), Counter()
    n_faltantes_base = 0
    citas_total = citas_no_verif = 0
    con_faltantes_base = []
    for e in expedientes:
        clase = tipo_por_id[e["chunk_id"]]
        estados_por_clase[clase][e["estado"]] += 1
        ev1 = e["veredictos"][0]
        if ev1["faltantes"]:
            con_faltantes_base.append({"chunk_id": e["chunk_id"], "clase": clase,
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
        "estados_por_clase": {k: dict(v) for k, v in estados_por_clase.items()},
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
        "gasto_e3_runner_usd": round(cli_e3.gasto_usd + cli_e1.gasto_usd, 4),
        "gasto_e1_previo_usd": gasto_e1,
        "gasto_fase_b_total_usd": round(cli_e3.gasto_usd + cli_e1.gasto_usd + gasto_e1, 4),
        "tope_combinado_usd": TOPE_COMBINADO_USD,
        "wall_time_min": round((time.time() - t0) / 60, 1),
    }
    with (OUT_DIR / "resumen_faseB_e3.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)

    cli_e3.close()
    cli_e1.close()
    print(json.dumps({k: resumen[k] for k in
                      ("n_unidades_procesadas", "estados", "estados_por_clase",
                       "gasto_fase_b_total_usd", "wall_time_min")},
                     ensure_ascii=False, indent=1), flush=True)
    print(f"-> {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
