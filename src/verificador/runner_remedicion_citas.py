"""
runner_remedicion_citas.py — RE-RATCHET DE MEDICIÓN sobre los 27 chunks que
la calibración fase B dejó en cola humana, con la capa de citas CORREGIDA
(laudo: normalización extendida + verificación contra fuente sin rótulos).

ETIQUETA EXPLÍCITA: esta re-corrida es MEDICIÓN para el presupuesto del
corpus. Las extracciones finales de pro siguen siendo las de la corrida
sellada (salida/faseB_pro/, que NO se toca): acá solo se mide cuántas colas
eran artefacto de la capa de citas y cuántas son cola real.

Mecánica:
  - Chunks viejos TAL CUAL (E0 sellado) + validación E1 original sellada.
  - Veredicto base: el request es byte-idéntico al de fase B (mismo prompt,
    mismo namespace) → se sirve de la CACHÉ local (se verifica el hit; cero
    API). La capa determinística corregida re-evalúa ese mismo crudo: ahora
    más faltantes tienen cita verificada y entran al feedback.
  - Reintento E1 (feedback más completo → request nuevo, pagado) →
    re-validación → re-verificación E3 (pagada).
  - Tope duro USD 1,50 (solo gasto nuevo), freno por proyección.

Salida: salida/remedicion_citas/ (veredictos.jsonl, cola_humana.jsonl,
desenlaces.jsonl, resumen_remedicion.json). Nada de faseB_pro se modifica.

Uso:  .venv/bin/python3 runner_remedicion_citas.py
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

TOPE_USD = 1.50
MARGEN_UNIDAD_USD = 0.25
MAX_TOKENS_REINTENTO = 16384

RUN_LABEL_E3 = "e3_remedicion_citas"
RUN_LABEL_E1 = "e3_remedicion_citas_reintentos_e1"
DB_REINTENTOS_E1 = BASE / "cache" / "e1_reintentos.db"

FASEB_DIR = BASE / "salida" / "faseB_pro"       # SOLO LECTURA (sellada)
OUT_DIR = BASE / "salida" / "remedicion_citas"

EVAL_DIR = comun_e3.REPO / "data" / "experiment" / "evaluacion"


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(EVAL_DIR / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("ANTHROPIC_API_KEY ausente")
        return 1

    # Universo: los chunks en cola de la corrida sellada, en su orden.
    cola_ids = []
    with (FASEB_DIR / "cola_humana.jsonl").open(encoding="utf-8") as f:
        for line in f:
            cid = json.loads(line)["chunk_id"]
            if cid not in cola_ids:
                cola_ids.append(cid)
    assert len(cola_ids) == 27, f"esperados 27 chunks en cola, hay {len(cola_ids)}"
    estados_sellados = {}
    with (FASEB_DIR / "extracciones_finales.jsonl").open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            estados_sellados[d["chunk_id"]] = d["estado"]

    pares = {c["id"]: (c, v) for c, v in pares_calibracion()}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registro = ratchet_e3.RegistroE3(OUT_DIR)

    cli_e3 = cliente_e3.ClienteE3Real(**P_E3, tope_usd=TOPE_USD, run_label=RUN_LABEL_E3)
    cli_e1 = cliente_e1.ClienteE1Real(**P_E1, tope_usd=TOPE_USD,
                                      run_label=RUN_LABEL_E1,
                                      db_path=DB_REINTENTOS_E1)
    print("RE-MEDICIÓN (capa de citas corregida) — no altera la corrida sellada", flush=True)
    print(f"tope=USD {TOPE_USD:.2f} | ns E3={cliente_e3.namespace_e3()}", flush=True)

    desenlaces = []
    freno = None
    t0 = time.time()
    with (OUT_DIR / "desenlaces.jsonl").open("w", encoding="utf-8") as ff:
        for i, cid in enumerate(cola_ids, 1):
            gasto = cli_e3.gasto_usd + cli_e1.gasto_usd
            if gasto + MARGEN_UNIDAD_USD > TOPE_USD:
                freno = f"freno por tope antes de {cid}: gasto USD {gasto:.4f}"
                print(freno, flush=True)
                break
            chunk, val = pares[cid]
            hits_antes = cli_e3.llamadas_hit
            try:
                exp = ratchet_e3.ciclo_ratchet(
                    chunk, val,
                    cliente_verificador=cli_e3, cliente_extractor=cli_e1,
                    model_e3=MODEL_E3, model_e1=MODEL_E1,
                    registro=registro, max_tokens_reintento=MAX_TOKENS_REINTENTO)
            except (cliente_e3.TopeExcedido, cliente_e1.TopeExcedido) as e:
                freno = f"freno por tope de cliente en {cid}: {e}"
                print(freno, flush=True)
                break
            base_fue_hit = cli_e3.llamadas_hit > hits_antes  # la 1ª llamada del ciclo
            ev1 = exp["veredictos"][0]
            d = {
                "orden_remedicion": i,
                "chunk_id": cid,
                "estado_sellado_faseB": estados_sellados[cid],
                "estado_remedicion": exp["estado"],
                "veredicto_base_desde_cache": base_fue_hit,
                "faltantes_base": len(ev1["faltantes"]),
                "faltantes_base_utilizables": len(ev1["faltantes_utilizables"]),
                "n_reintentos": len(exp["reintentos"]),
            }
            desenlaces.append(d)
            ff.write(json.dumps(d, ensure_ascii=False) + "\n")
            ff.flush()
            print(f"[{i:2d}/27] {cid:<16s} sellado={d['estado_sellado_faseB']:<30s} "
                  f"→ {d['estado_remedicion']:<28s} cache_base={base_fue_hit} "
                  f"utilizables={d['faltantes_base_utilizables']}/{d['faltantes_base']} "
                  f"gasto=USD {cli_e3.gasto_usd + cli_e1.gasto_usd:.4f}", flush=True)

    estados = Counter(d["estado_remedicion"] for d in desenlaces)
    hits_base = sum(1 for d in desenlaces if d["veredicto_base_desde_cache"])
    # tasa de cola REAL sobre los 87: sellado 33 ok + 27 aceptado_tras_reintento;
    # de los 27 en cola, los que ahora aceptan dejan de ser cola.
    cola_real = [d["chunk_id"] for d in desenlaces
                 if d["estado_remedicion"] != "aceptado_tras_reintento"]
    resumen = {
        "etiqueta": ("MEDICIÓN para presupuesto del corpus con la capa de citas "
                     "corregida; las extracciones finales de pro siguen siendo las "
                     "de la corrida sellada (salida/faseB_pro/)"),
        "modelos": {"e3": MODEL_E3, "e1_reintentos": MODEL_E1},
        "prefijo_hash_e3": prompt_e3.PREFIJO_HASH,
        "n_unidades": len(desenlaces),
        "freno": freno,
        "veredictos_base_desde_cache": f"{hits_base}/{len(desenlaces)}",
        "estados_remedicion": dict(estados),
        "cola_real_chunk_ids": cola_real,
        "tasa_cola_real_sobre_87": round(len(cola_real) / 87, 4),
        "cliente_e3": cli_e3.resumen(),
        "cliente_e1_reintentos": cli_e1.resumen(),
        "gasto_total_usd": round(cli_e3.gasto_usd + cli_e1.gasto_usd, 4),
        "tope_usd": TOPE_USD,
        "wall_time_min": round((time.time() - t0) / 60, 1),
    }
    with (OUT_DIR / "resumen_remedicion.json").open("w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)

    cli_e3.close()
    cli_e1.close()
    print(json.dumps({k: resumen[k] for k in
                      ("n_unidades", "veredictos_base_desde_cache",
                       "estados_remedicion", "tasa_cola_real_sobre_87",
                       "gasto_total_usd", "wall_time_min")},
                     ensure_ascii=False, indent=1), flush=True)
    print(f"-> {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
