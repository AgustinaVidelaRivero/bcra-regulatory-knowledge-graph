"""
estimacion_e3.py — Estimación de tokens y costo de E3 (T5). Código puro: mide
los prompts REALES del verificador (prefijo con calibradores una vez + mensaje
variable por unidad: fuente íntegro + extracción), no llama a ninguna API y NO
fija precios — las fórmulas quedan parametrizadas y se resuelven en la
autorización de fase B. El verificador corre con MODELO FUERTE (D3 del
diseño): sus precios (P*_E3) son los del modelo fuerte; los del reintento de
extracción (P*_E1) son los del modelo chico de E1.

Dos estimaciones SEPARADAS:
  (a) CALIBRACIÓN (fase B) = verificar las 87 unidades de pro ACEPTADAS por la
      calibración E1 (fan-in de E2: 88 recibidas − 1 rechazada; el chunk
      rechazado va por el carril del fan-in, no por E3) + presupuesto de
      reintentos del mini-ratchet con tasa supuesta explícita.
  (b) CORPUS completo = 1.477 unidades de E0 (supone todas aceptadas).

Supuestos explícitos numerados (impresos y persistidos):

  V1. RATIO prosa chars→tokens: r del ancla empírica de E1 (ajuste
      in = A + B·chars sobre los 508 pares reales sellados de la extracción
      v2; ver estimacion_e1.anclas_empiricas). Se aplica al texto fuente.
  V2. RATIO del render de la extracción: 2,5 chars/token — el render legible
      mezcla prosa (descripciones) con estructura (ids, tipos, flechas), entre
      prosa (~3,5) y JSON (~2,0). Elección conservadora (sobreestima tokens).
  V3. PREFIJO E3 en tokens: chars/2,5 (misma elección conservadora: el
      prefijo mezcla instrucciones en prosa, tool schema JSON y calibradores
      mixtos). El número exacto se mide en la primera llamada real de la
      calibración (cache_creation_input_tokens).
  V4. OUTPUT por veredicto: completo_ok ≈ 200 tokens; con faltantes ≈ 700
      (tool JSON con citas). Sin ancla propia: se mide en calibración.
  V5. TASA de unidades con faltantes: 15 % (supuesto SIN base empírica
      propia — fijarla es precisamente el objetivo de la calibración).
      Sensibilidad a 5 % / 15 % / 30 % incluida.
  V6. COSTO de un reintento = re-extracción E1 (tokens REALES medios de la
      calibración fase B: cache_read del prefijo E1 + input variable medio +
      ~300 tokens de bloque de feedback + output medio real, todo a precios
      E1) + re-verificación E3 (cache_read del prefijo E3 + variable de la
      unidad + output completo_ok, a precios E3). Tope 1 reintento.
  V7. UNA escritura de caché de prefijo por corrida (secuencial, Decisión 4);
      re-verificaciones intercaladas refrescan el TTL de ambos prefijos.
  V8. CORPUS: el render de extracción de los TOs aún no extraídos se estima
      con el ratio real render_chars/fuente_chars medido sobre los 87 pares
      de pro.

Uso:  python3 estimacion_e3.py    (escribe salida/estimacion_e3.json)
"""

from __future__ import annotations

import json
import statistics

import comun_e3
from comun_e3 import (BASE, cargar_chunks, cargar_extracciones_faseB,
                      chunk_aceptado, fuente_integro, render_extraccion,
                      pares_calibracion)
import prompt_e3
import estimacion_e1  # módulo de E1 (solo import): ancla empírica V1

R_RENDER = 2.5            # V2
R_PREFIJO = 2.5           # V3
OUT_OK = 200              # V4
OUT_FALTANTES = 700       # V4
TASA_FALTANTES = 0.15     # V5
TOKENS_FEEDBACK = 300     # V6
MULT_CACHE_WRITE = 1.25   # cuenta tokens-equivalentes (precedente E1/S7)
MULT_CACHE_READ = 0.10


def _e1_reales_por_chunk() -> dict:
    """Medias REALES por llamada de la calibración E1 fase B (88 llamadas)."""
    regs = list(cargar_extracciones_faseB().values())
    var_in = [r["usage"]["input_tokens"] for r in regs]
    outs = [r["usage"]["output_tokens"] for r in regs]
    reads = [r["usage"]["cache_read_tokens"] for r in regs if r["usage"]["cache_read_tokens"]]
    return {
        "n_llamadas": len(regs),
        "input_variable_medio": round(statistics.mean(var_in)),
        "output_medio": round(statistics.mean(outs)),
        "cache_read_prefijo": round(statistics.mean(reads)) if reads else 0,
    }


def _prefijo_e3_tokens() -> tuple[int, int]:
    p_chars = len(prompt_e3.PREFIJO_SISTEMA) + len(
        json.dumps([prompt_e3.TOOL_SCHEMA_E3], ensure_ascii=False))
    return round(p_chars / R_PREFIJO), p_chars


def _variable_tokens(chunk: dict, render_chars: float, r_prosa: float) -> float:
    """Tokens variables de una llamada E3: encabezado+fuente (prosa) + render
    de la extracción (V2). El encabezado fijo del mensaje es marginal y queda
    dentro de la parte prosa."""
    fuente_chars = len(fuente_integro(chunk))
    encabezado_chars = 400  # líneas fijas del mensaje (documento, unidad, rótulos)
    return (fuente_chars + encabezado_chars) / r_prosa + render_chars / R_RENDER


def estimar() -> dict:
    anc = estimacion_e1.anclas_empiricas()
    r_prosa = anc["ratio_chars_por_token"]                       # V1
    p_tok, p_chars = _prefijo_e3_tokens()                        # V3
    e1_real = _e1_reales_por_chunk()                             # V6

    # ---------------- (a) calibración: 87 unidades reales ---------------- #
    pares = pares_calibracion()
    n_cal = len(pares)
    var_cal, ratios_render = [], []
    for chunk, val in pares:
        render_chars = len(render_extraccion(val))
        var_cal.append(_variable_tokens(chunk, render_chars, r_prosa))
        ratios_render.append(render_chars / max(len(fuente_integro(chunk)), 1))
    ratio_render_fuente = statistics.mean(ratios_render)         # V8

    # ---------------- (b) corpus: 1.477 unidades ------------------------- #
    todos = cargar_chunks()
    var_cor = []
    por_to: dict[str, dict] = {}
    for to in comun_e3.TOS:
        sub = [c for c in todos if c["to"] == to]
        vs = [_variable_tokens(c, ratio_render_fuente * len(fuente_integro(c)), r_prosa)
              for c in sub]
        var_cor.extend(vs)
        por_to[to] = {"n_chunks": len(sub), "variable_tokens_total": round(sum(vs))}

    def _conjunto(nombre: str, n: int, var_toks: list[float], tasa: float) -> dict:
        v_total = round(sum(var_toks))
        v_medio = round(statistics.mean(var_toks))
        n_reint = round(n * tasa)
        # verificaciones: n iniciales + n_reint re-verificaciones
        n_verif = n + n_reint
        out_inicial = round(n * ((1 - tasa) * OUT_OK + tasa * OUT_FALTANTES))
        out_reverif = n_reint * OUT_OK  # supuesto: el reintento re-verifica a ok
        out_total = out_inicial + out_reverif
        var_reverif = round(n_reint * v_medio)
        cache_write = p_tok                                       # V7
        cache_read = p_tok * (n_verif - 1)
        in_no_cacheado = v_total + var_reverif
        in_sin_caching = n_verif * p_tok + in_no_cacheado
        in_equiv = round(in_no_cacheado + MULT_CACHE_WRITE * cache_write
                         + MULT_CACHE_READ * cache_read)
        # reintentos E1 (modelo chico, prefijo E1 caliente):
        reint_e1 = {
            "n_reintentos": n_reint,
            "input_no_cacheado": n_reint * (e1_real["input_variable_medio"] + TOKENS_FEEDBACK),
            "cache_read": n_reint * e1_real["cache_read_prefijo"],
            "output": n_reint * e1_real["output_medio"],
        }
        return {
            "conjunto": nombre,
            "n_unidades": n,
            "tasa_faltantes_supuesta": tasa,
            "verificaciones_e3": {
                "n_llamadas": n_verif,
                "prefijo_tokens": p_tok,
                "variable_tokens_total": v_total,
                "variable_tokens_medio": v_medio,
                "variable_re_verificaciones": var_reverif,
                "output_tokens_total": out_total,
                "sin_caching": {"input_tokens_facturables": in_sin_caching},
                "con_caching": {
                    "input_tokens_no_cacheados": in_no_cacheado,
                    "cache_write_tokens": cache_write,
                    "cache_read_tokens": cache_read,
                    "input_equivalente_tokens": in_equiv,
                },
                "ahorro_componente_input_pct": round(
                    100 * (1 - in_equiv / in_sin_caching), 1),
                "formula_usd_e3": (
                    f"costo_E3 = {in_no_cacheado}/1e6 × P_in_E3 "
                    f"+ {cache_write}/1e6 × P_cache_write_E3 "
                    f"+ {cache_read}/1e6 × P_cache_read_E3 "
                    f"+ {out_total}/1e6 × P_out_E3"
                ),
            },
            "reintentos_e1": {
                **reint_e1,
                "formula_usd_e1": (
                    f"costo_reintentos_E1 = {reint_e1['input_no_cacheado']}/1e6 × P_in_E1 "
                    f"+ {reint_e1['cache_read']}/1e6 × P_cache_read_E1 "
                    f"+ {reint_e1['output']}/1e6 × P_out_E1"
                ),
            },
            "formula_total": "costo = costo_E3 + costo_reintentos_E1",
        }

    calibracion = _conjunto("calibracion_pro_aceptados", n_cal, var_cal, TASA_FALTANTES)
    corpus = _conjunto("corpus_5TOs", len(todos), var_cor, TASA_FALTANTES)
    sensibilidad = {
        f"tasa_{int(t*100)}pct": {
            "calibracion": _conjunto("calibracion", n_cal, var_cal, t),
            "corpus": _conjunto("corpus", len(todos), var_cor, t),
        }
        for t in (0.05, 0.15, 0.30)
    }

    # -------- comparación por llamada: E3 (fuerte) vs E1 (chico) ---------- #
    comparacion = {
        "e1_real_fase_b": {
            "input_variable_medio": e1_real["input_variable_medio"],
            "cache_read_prefijo": e1_real["cache_read_prefijo"],
            "output_medio": e1_real["output_medio"],
            "modelo": "chico (calibración fase B)",
        },
        "e3_estimado": {
            "input_variable_medio": calibracion["verificaciones_e3"]["variable_tokens_medio"],
            "cache_read_prefijo": p_tok,
            "output_medio": round((1 - TASA_FALTANTES) * OUT_OK + TASA_FALTANTES * OUT_FALTANTES),
            "modelo": "FUERTE (D3 del diseño)",
        },
        "nota": (
            "E3 es más caro por llamada por dos vías multiplicativas: (i) más "
            "input variable por unidad — el mensaje lleva el fuente ÍNTEGRO "
            "(propio + herencia, más largo que el texto que factura E1) MÁS la "
            "extracción completa renderizada; (ii) precios de modelo fuerte "
            "(P_in_E3/P_out_E3 > P_in_E1/P_out_E1). El output, en cambio, es "
            "menor (veredicto corto vs extracción completa)."
        ),
    }

    return {
        "prefijo_hash": prompt_e3.PREFIJO_HASH,
        "supuestos": {
            "V1_ratio_prosa_chars_por_token": round(r_prosa, 3),
            "V1_base": f"ancla empírica de E1 ({anc['n_pares']} pares reales sellados)",
            "V2_ratio_render_extraccion": R_RENDER,
            "V3_prefijo_e3": {"chars": p_chars, "tokens_estimados": p_tok,
                              "ratio": R_PREFIJO,
                              "nota": "se mide exacto en la primera llamada real"},
            "V4_output_por_veredicto": {"completo_ok": OUT_OK, "con_faltantes": OUT_FALTANTES},
            "V5_tasa_faltantes": TASA_FALTANTES,
            "V5_nota": ("supuesto SIN base empírica propia; fijar la tasa real es "
                        "objetivo de la calibración. Sensibilidad 5/15/30 % incluida."),
            "V6_reintento": {"feedback_tokens": TOKENS_FEEDBACK,
                             "e1_reales_por_llamada": e1_real},
            "V7_writes_de_prefijo_por_corrida": 1,
            "V8_ratio_render_sobre_fuente": round(ratio_render_fuente, 3),
        },
        "calibracion": calibracion,
        "corpus": corpus,
        "corpus_por_to": por_to,
        "sensibilidad_tasa": {
            k: {
                "calibracion_input_equiv": v["calibracion"]["verificaciones_e3"]["con_caching"]["input_equivalente_tokens"],
                "calibracion_reintentos_e1_output": v["calibracion"]["reintentos_e1"]["output"],
                "corpus_input_equiv": v["corpus"]["verificaciones_e3"]["con_caching"]["input_equivalente_tokens"],
                "corpus_reintentos_e1_output": v["corpus"]["reintentos_e1"]["output"],
            }
            for k, v in sensibilidad.items()
        },
        "comparacion_por_llamada": comparacion,
        "precios": ("NO consultados: P_in_E3, P_out_E3, P_cache_write_E3, "
                    "P_cache_read_E3 (modelo fuerte) y P_*_E1 (modelo chico) se "
                    "resuelven en la autorización de fase B contra la "
                    "documentación oficial vigente."),
        "nota_never_pay_twice": (
            "si la fase B se relanza con el mismo prompt y namespace, cada "
            "veredicto ya pagado es hit de la caché local (cache/e3_verificacion.db)."
        ),
    }


def _tabla(res: dict) -> str:
    c = res["calibracion"]["verificaciones_e3"]
    k = res["corpus"]["verificaciones_e3"]
    rc = res["calibracion"]["reintentos_e1"]
    rk = res["corpus"]["reintentos_e1"]
    filas = [f"{'':44s} {'calibración (pro)':>20s} {'corpus (5 TOs)':>20s}"]
    def fila(label, cv, kv):
        filas.append(f"{label:44s} {cv:>20,} {kv:>20,}")
    fila("unidades a verificar", res["calibracion"]["n_unidades"], res["corpus"]["n_unidades"])
    fila("llamadas E3 (incl. re-verificaciones)", c["n_llamadas"], k["n_llamadas"])
    fila("prefijo E3 (tokens, una vez)", c["prefijo_tokens"], k["prefijo_tokens"])
    fila("variable E3 total (tokens)", c["variable_tokens_total"] + c["variable_re_verificaciones"],
         k["variable_tokens_total"] + k["variable_re_verificaciones"])
    fila("variable E3 medio por llamada (tokens)", c["variable_tokens_medio"], k["variable_tokens_medio"])
    fila("output E3 total (tokens)", c["output_tokens_total"], k["output_tokens_total"])
    fila("input E3 SIN caching (tokens)", c["sin_caching"]["input_tokens_facturables"],
         k["sin_caching"]["input_tokens_facturables"])
    fila("input E3 no cacheado (tokens)", c["con_caching"]["input_tokens_no_cacheados"],
         k["con_caching"]["input_tokens_no_cacheados"])
    fila("cache write (tokens)", c["con_caching"]["cache_write_tokens"], k["con_caching"]["cache_write_tokens"])
    fila("cache read (tokens)", c["con_caching"]["cache_read_tokens"], k["con_caching"]["cache_read_tokens"])
    fila("input E3 equivalente CON caching", c["con_caching"]["input_equivalente_tokens"],
         k["con_caching"]["input_equivalente_tokens"])
    filas.append(f"{'ahorro componente input':44s} {c['ahorro_componente_input_pct']:>19.1f}% {k['ahorro_componente_input_pct']:>19.1f}%")
    fila("reintentos E1 (n, tasa supuesta 15 %)", rc["n_reintentos"], rk["n_reintentos"])
    fila("reintentos E1 input no cacheado (tokens)", rc["input_no_cacheado"], rk["input_no_cacheado"])
    fila("reintentos E1 output (tokens)", rc["output"], rk["output"])
    return "\n".join(filas)


def main():
    res = estimar()
    out = BASE / "salida" / "estimacion_e3.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res["supuestos"], ensure_ascii=False, indent=1))
    print()
    print(_tabla(res))
    print()
    print("calibración:", res["calibracion"]["verificaciones_e3"]["formula_usd_e3"])
    print("            ", res["calibracion"]["reintentos_e1"]["formula_usd_e1"])
    print("corpus:     ", res["corpus"]["verificaciones_e3"]["formula_usd_e3"])
    print("            ", res["corpus"]["reintentos_e1"]["formula_usd_e1"])
    print()
    print(json.dumps(res["comparacion_por_llamada"], ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
