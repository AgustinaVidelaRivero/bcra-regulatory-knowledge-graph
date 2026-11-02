"""
estimacion_enm01.py — Estimación de la FASE B de la mini-recalibración de la
enmienda 01 (corrida E0→E3 completa sobre pro con la arquitectura enmendada),
con PRECIOS RESUELTOS. Código puro: mide los prompts REALES de la salida E0
enm01 (101 unidades de pro: 88 chunks + 13 mini-chunks) y ancla en los usage
reales de la calibración sellada. No llama a ninguna API.

Precios autorizados (USD/MTok):
  E1 (extractor, claude-haiku-4-5):  in 1,00 / out 5,00 / cw 1,25 / cr 0,10
  E3 (verificador, claude-sonnet-5): in 2,00 / out 10,00 / cw 2,50 / cr 0,20

Supuestos explícitos (W*, numerados; impresos y persistidos):

  W1. El namespace E1 ROTÓ (hash de prefijo nuevo): la re-extracción de pro se
      paga COMPLETA — 101 llamadas frías (88 chunks + 13 minis), 1 write del
      prefijo nuevo, (n−1) reads. No hay hits de la caché local.
  W2. Ratio prosa chars→token y ajuste de output: anclas selladas de
      estimacion_e1.anclas_empiricas() (S1/S3, 508 pares reales).
  W3. Prefijo E1 nuevo en tokens: cache_write REAL de la primera llamada de la
      calibración sellada × (chars prefijo nuevo / chars prefijo sellado).
      El prefijo sellado no es reconstruible desde el código vigente (el
      prompt cambió), así que sus chars se toman del registro de la
      estimación sellada (salida/estimacion_e1.json → prefijo_chars).
  W4. E3: prefijo INTACTO (hash idéntico al sellado) — tokens de prefijo =
      cache_write REAL de la corrida sellada (logs/cache_usage.jsonl,
      component reextraccion_v2_e3). 1 write + (n_llamadas−1) reads (la caché
      de API expira entre corridas; la local no aplica: las keys cambian con
      el fuente nuevo y las extracciones nuevas).
  W5. Variable E3 por unidad: (chars del fuente_integro NUEVO + 400 de
      encabezado)/r + render/2,5, con render = ratio_render_sobre_fuente
      sellado (V8) × chars del fuente VIEJO-equivalente ≈ para hijos, el
      render se estima con el ratio sellado aplicado al fuente sellado de la
      unidad (la extracción no cambia de escala); para minis, con el mismo
      ratio sobre su fuente nuevo (bloque corto → render corto).
  W6. Output E3 por veredicto: media REAL sellada (323 tok/response, mezcla
      completo_ok/faltantes de la calibración) — conservadora si la enmienda
      reduce faltantes.
  W7. TASA DE REINTENTOS declarada: 32/87 ≈ 36,8 %. Base: en el veredicto
      base sellado, 54/87 unidades tuvieron faltantes; 22 de ellas SOLO con
      faltantes que verifican exclusivamente en herencia (la familia que la
      enmienda elimina por construcción — predicción §3.1); las 32 restantes
      (27 solo-propio + 5 mixtas) retienen faltantes de texto propio y se
      asumen re-intentadas. La misma tasa se aplica a los 13 minis (sin ancla
      propia; conservador: los bloques son cortos).
      Comando que reproduce el 22/5/27: ver INFORME (anclaje de citas base
      contra herencia vs propio, normalización C7).
  W8. Costo de un reintento: E1 (read prefijo nuevo + variable + 300 de
      feedback + output S3) + E3 re-verificación (read prefijo + variable de
      la unidad + output W6).
  W9. Los 101 se asumen todos aceptados por el fan-in (la calibración sellada
      tuvo 1 rechazo/88; margen dentro del techo).

Uso:  .venv/bin/python3 estimacion_enm01.py   (escribe salida/estimacion_enm01.json)
"""

from __future__ import annotations

import json
import statistics

import comun_e3
from comun_e3 import BASE, E0_SALIDA_ENM01, cargar_chunks, fuente_integro
import prompt_e3
import estimacion_e1
import prompt_e1

REPO = comun_e3.REPO
E1_SALIDA = comun_e3.E1_DIR / "salida"

P_E1 = {"in": 1.00, "out": 5.00, "cw": 1.25, "cr": 0.10}
P_E3 = {"in": 2.00, "out": 10.00, "cw": 2.50, "cr": 0.20}

R_RENDER = 2.5
ENCABEZADO_E3_CHARS = 400
TOKENS_FEEDBACK = 300
OUT_E3_REAL = None  # se mide abajo (W6)

TASA_REINTENTOS = 32 / 87   # W7


def _prefijo_e1_tokens() -> tuple[int, dict]:
    """W3: escala del cache_write real sellado por chars de prefijo."""
    resumen = json.loads((E1_SALIDA / "faseB_pro" / "resumen_faseB.json")
                         .read_text(encoding="utf-8"))
    cw_real = resumen["caching"]["llamada_1"]["cache_write_tokens"]
    est_sellada = json.loads((E1_SALIDA / "estimacion_e1.json")
                             .read_text(encoding="utf-8"))
    chars_sellado = est_sellada["calibracion"]["prefijo_chars"]
    chars_nuevo = len(prompt_e1.PREFIJO_SISTEMA) + len(
        json.dumps([prompt_e1.TOOL_SCHEMA_E1], ensure_ascii=False))
    tok = round(cw_real * chars_nuevo / chars_sellado)
    return tok, {"cw_real_sellado": cw_real, "chars_sellado": chars_sellado,
                 "chars_nuevo": chars_nuevo}


def _prefijo_e3_tokens() -> int:
    """W4: cache_write real de la corrida E3 sellada."""
    cws = []
    with (REPO / "logs" / "cache_usage.jsonl").open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("component") == "reextraccion_v2_e3" and \
                    d.get("cache_creation_input_tokens"):
                cws.append(d["cache_creation_input_tokens"])
    return max(cws)


def _out_e3_real() -> int:
    outs = []
    with (REPO / "logs" / "cache_usage.jsonl").open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("component") == "reextraccion_v2_e3":
                outs.append(d["output_tokens"])
    return round(statistics.mean(outs))


def estimar() -> dict:
    anc = estimacion_e1.anclas_empiricas()
    r = anc["ratio_chars_por_token"]

    chunks = cargar_chunks(("pro",), e0_dir=E0_SALIDA_ENM01)
    n = len(chunks)
    minis = [c for c in chunks if c.get("tipo") == "mini_chunk"]
    hijos = [c for c in chunks if c.get("tipo") != "mini_chunk"]

    # ---------------- E1: re-extracción completa (W1) --------------------- #
    p1_tok, p1_det = _prefijo_e1_tokens()
    var1 = [len(prompt_e1.build_user_message(c)) / r for c in chunks]
    out1 = [anc["out_piso_tokens"] + anc["out_por_token_variable"] * v for v in var1]
    e1 = {
        "n_llamadas": n,
        "prefijo_tokens": p1_tok,
        "in_no_cacheado": round(sum(var1)),
        "cache_write": p1_tok,
        "cache_read": p1_tok * (n - 1),
        "output": round(sum(out1)),
    }
    e1_usd = (e1["in_no_cacheado"] * P_E1["in"] + e1["cache_write"] * P_E1["cw"]
              + e1["cache_read"] * P_E1["cr"] + e1["output"] * P_E1["out"]) / 1e6

    # ---------------- E3: verificación completa (W4-W6) ------------------- #
    p3_tok = _prefijo_e3_tokens()
    out3_medio = _out_e3_real()

    # render estimado por unidad (W5): ratio sellado render/fuente
    pares_sellados = comun_e3.pares_calibracion()
    from comun_e3 import render_extraccion
    ratio_render = statistics.mean(
        len(render_extraccion(v)) / max(len(fuente_integro(c)), 1)
        for c, v in pares_sellados)

    var3 = []
    for c in chunks:
        fch = len(fuente_integro(c))
        var3.append((fch + ENCABEZADO_E3_CHARS) / r + (ratio_render * fch) / R_RENDER)
    n_reint = round(n * TASA_REINTENTOS)
    var3_medio = statistics.mean(var3)
    n_llam3 = n + n_reint
    e3 = {
        "n_llamadas": n_llam3,
        "n_reintentos": n_reint,
        "prefijo_tokens": p3_tok,
        "in_no_cacheado": round(sum(var3) + n_reint * var3_medio),
        "cache_write": p3_tok,
        "cache_read": p3_tok * (n_llam3 - 1),
        "output": out3_medio * n_llam3,
        "output_medio_real_sellado": out3_medio,
    }
    e3_usd = (e3["in_no_cacheado"] * P_E3["in"] + e3["cache_write"] * P_E3["cw"]
              + e3["cache_read"] * P_E3["cr"] + e3["output"] * P_E3["out"]) / 1e6

    # ---------------- reintentos E1 (W7-W8) ------------------------------- #
    var1_medio = statistics.mean(var1)
    out1_medio = statistics.mean(out1)
    re1 = {
        "n_reintentos": n_reint,
        "in_no_cacheado": round(n_reint * (var1_medio + TOKENS_FEEDBACK)),
        "cache_read": p1_tok * n_reint,
        "output": round(n_reint * out1_medio),
    }
    re1_usd = (re1["in_no_cacheado"] * P_E1["in"] + re1["cache_read"] * P_E1["cr"]
               + re1["output"] * P_E1["out"]) / 1e6

    total = e1_usd + e3_usd + re1_usd
    return {
        "prefijo_hash_e1_nuevo": prompt_e1.PREFIJO_HASH,
        "prefijo_hash_e3": prompt_e3.PREFIJO_HASH,
        "unidades": {"total": n, "chunks": len(hijos), "mini_chunks": len(minis)},
        "supuestos": {
            "W1_namespace_e1_rotado": "todo se paga (0 hits)",
            "W2_anclas": {"ratio_chars_por_token": round(r, 3),
                          "out_fit": f"{round(anc['out_piso_tokens'])} + "
                                     f"{round(anc['out_por_token_variable'], 3)}·var"},
            "W3_prefijo_e1": p1_det | {"tokens": p1_tok},
            "W4_prefijo_e3_tokens_real": p3_tok,
            "W5_ratio_render_sobre_fuente": round(ratio_render, 3),
            "W6_out_e3_medio_real": out3_medio,
            "W7_tasa_reintentos": {"valor": round(TASA_REINTENTOS, 4),
                                   "base": "32/87: 54 unidades con faltantes base "
                                           "− 22 SOLO-herencia (eliminadas por "
                                           "construcción); 27 solo-propio + 5 mixtas"},
            "W8_feedback_tokens": TOKENS_FEEDBACK,
            "W9_fanin": "101/101 aceptadas (sellada: 87/88)",
        },
        "e1_reextraccion": e1 | {"usd": round(e1_usd, 4)},
        "e3_verificacion": e3 | {"usd": round(e3_usd, 4)},
        "e1_reintentos": re1 | {"usd": round(re1_usd, 4)},
        "total_usd": round(total, 4),
        "referencias": {
            "corrida_sellada_e1_usd": 0.73,
            "corrida_sellada_e3_mas_reintentos_usd": 2.14,
            "freno_condicional_usd": 4.50,
            "tope_duro_usd": 5.00,
        },
        "precios_usd_por_mtok": {"e1_haiku_4_5": P_E1, "e3_sonnet_5": P_E3},
    }


def main():
    res = estimar()
    out = BASE / "salida" / "estimacion_enm01.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
