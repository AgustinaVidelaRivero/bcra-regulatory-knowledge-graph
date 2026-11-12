"""
estimacion_e1.py — Estimación de tokens y costo de E1 (T5). Código puro: mide
los prompts REALES (prefijo estable una vez + mensaje variable por chunk sobre
los 1.477 chunks de E0), no llama a ninguna API y NO fija precios — la fórmula
queda parametrizada en P_in / P_out / P_cache_write / P_cache_read y se
resuelve en la autorización de fase B.

Dos estimaciones SEPARADAS:
  (a) CALIBRACIÓN (fase B) = el TO pro completo: sus 88 chunks de E0.
  (b) CORPUS completo      = los 1.477 chunks de E0 (los 5 TOs).

ANCLA EMPÍRICA (S1): los 508 resultados reales de la extracción v2 sellada
(grafo_v2/code/cache_v2/full/, SOLO LECTURA) guardan in_tokens/out_tokens por
chunk; el mensaje de usuario de esa corrida es reconstruible byte a byte
(formato de extract.py + chunks_all.json). El ajuste lineal
    in_tokens = A + B × chars_mensaje
separa el costo fijo por request (A ≈ prefijo v2 + overhead: en esa corrida el
prefijo se facturó como input en cada request) de la tarifa variable
(1/B ≈ chars/token de la prosa regulatoria). Nota: el ancla alternativa del
harness (2.872 chars / 1.433 tok ≈ 2,0 chars/token) se DESCARTA para la parte
variable: ese prefijo es mayormente JSON de tools, que tokeniza ~2 chars/token,
no prosa (~3,5).

Supuestos explícitos numerados (impresos y persistidos):

  S1. RATIO variable chars→tokens: r = 1/B del ajuste sobre los 508 pares
      reales (mensaje reconstruido exacto, in_tokens medidos). Prosa del mismo
      corpus, mismo formato de mensaje.
  S2. PREFIJO E1 en tokens: escala del intercepto real del ajuste:
      P_E1 = A × (chars_prefijo_E1 / chars_prefijo_v2). Misma composición
      (instrucciones en prosa + tool schema JSON con los mismos enums de
      sujetos, dos veces); el intercepto captura además el overhead fijo de
      request que un ratio de chars puro omite.
  S3. OUTPUT por chunk: ajuste lineal sobre los mismos 508 resultados reales:
      out_i = A_out + B_out × var_i (la salida JSON copia las citas textuales
      en descripcion, por eso B_out > 1 sobre los tokens variables).
  S4. UNA escritura de caché de prefijo por corrida: corridas secuenciales con
      prefijo idéntico (Decisión 4 de docs/decisiones_caching_extraccion.md);
      con TTL de 5 min y llamadas continuas, cada hit refresca el TTL. Si la
      corrida se relanza en frío, cada relanzamiento agrega un write de
      prefijo (marginal: P_E1 × P_cache_write).
  S5. SIN descuento de Batch API: la acumulación batch+caching es adopción
      condicional (D4 del diseño) pendiente de verificación; no se asume.
  S6. Cero reintentos y cero re-extracciones del ratchet E3: solo la primera
      pasada de E1. Un reintento con prefijo caliente paga solo la parte
      variable + read del prefijo.
  S7. Multiplicadores de caching para la cuenta "con vs sin": cache write =
      1,25 × P_in la primera vez, cache read = 0,10 × P_in después (fórmula de
      la Decisión 2, anclada en extract.py:303-312). La tabla muestra ambas
      cuentas en tokens-equivalentes de input (independiente del precio).

Uso:  python3 estimacion_e1.py    (escribe salida/estimacion_e1.json)
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

import comun_e1
from comun_e1 import BASE, GRAFO_V2_CODE, cargar_chunks
import prompt_e1

CACHE_V2_FULL = GRAFO_V2_CODE / "cache_v2" / "full"          # SOLO LECTURA (sellado)
CHUNKS_V2 = GRAFO_V2_CODE / "cache_v2" / "chunks_all.json"   # SOLO LECTURA (sellado)
EXTRACT_V2 = GRAFO_V2_CODE / "extract.py"                    # SOLO LECTURA

MULT_CACHE_WRITE = 1.25         # S7
MULT_CACHE_READ = 0.10          # S7


# ------------------------------------------------------------------------- #
# Reconstrucción del request v2 (para el ancla S1/S2/S3)                    #
# ------------------------------------------------------------------------- #

def _prefijo_v2_chars() -> int:
    """Chars del prefijo (SYSTEM_PROMPT + [TOOL_SCHEMA]) de la corrida v2,
    reconstruidos del fuente sin importar extract.py (que exige anthropic)."""
    from schema import SUJETOS_PROMPT, ENTITY_TYPES, PREDICATES, SUJETOS_CATALOGO
    src = EXTRACT_V2.read_text(encoding="utf-8")
    m = re.search(r'SYSTEM_PROMPT = f"""(.*?)"""', src, re.S)
    sp = (m.group(1)
          .replace("{SUJETOS_PROMPT}", SUJETOS_PROMPT)
          .replace("{{", "{").replace("}}", "}"))
    m2 = re.search(r"TOOL_SCHEMA = (\{.*?\n\})\n\n\n", src, re.S)
    ts = eval(m2.group(1), {  # literal del fuente sellado, globals restringidos
        "ENTITY_TYPES": ENTITY_TYPES, "PREDICATES": PREDICATES,
        "SUJETOS_CATALOGO": SUJETOS_CATALOGO, "list": list})
    return len(sp) + len(json.dumps([ts], ensure_ascii=False))


def _user_msg_v2_chars(c: dict) -> int:
    """Mensaje de usuario de la corrida v2, byte a byte (extract.py
    build_user_message)."""
    from schema import ROL_POR_TO
    rol = ROL_POR_TO.get(c["doc"])
    if rol is not None:
        miembros = ", ".join(rol["miembros_labels"])
        alcance = (
            f"Alcance de este TO: {rol['rol_id']} = {{{miembros}}}. "
            f"Cuando la norma se dirija genéricamente a 'las entidades' / 'los sujetos obligados' / "
            f"el colectivo del TO, usá {rol['rol_id']} como sujeto.\n\n"
        )
    else:
        alcance = ""
    msg = (
        f"Documento fuente: {c['doc']}\n"
        f"Ubicación: {c['location']}\n\n"
        f"{alcance}"
        f"Texto del chunk:\n```\n{c['text']}\n```\n\n"
        f"Extraé las entidades y relaciones según el schema. Recordá incluir el nodo TextoOrdenado con local_id='to'."
    )
    return len(msg)


def _fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Cuadrados mínimos y = a + b·x."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


def anclas_empiricas() -> dict:
    """S1/S2/S3 desde los 508 resultados reales sellados."""
    with CHUNKS_V2.open(encoding="utf-8") as f:
        by_id = {c["chunk_id"]: c for c in json.load(f)}

    chars_msg, in_tok, out_tok = [], [], []
    for p in sorted(CACHE_V2_FULL.glob("*.json")):
        with p.open(encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("error") is None and d.get("in_tokens") and d["chunk_id"] in by_id:
            chars_msg.append(_user_msg_v2_chars(by_id[d["chunk_id"]]))
            in_tok.append(d["in_tokens"])
            out_tok.append(d["out_tokens"])
    if len(chars_msg) < 100:
        raise RuntimeError(f"ancla insuficiente: {len(chars_msg)} pares en {CACHE_V2_FULL}")

    a_in, b_in = _fit(chars_msg, in_tok)          # in = A + B·chars
    var_tok = [b_in * x for x in chars_msg]
    a_out, b_out = _fit(var_tok, out_tok)          # out = A_out + B_out·var

    return {
        "n_pares": len(chars_msg),
        "ratio_chars_por_token": 1 / b_in,         # S1
        "intercepto_por_request_tokens": a_in,     # S2 (prefijo v2 + overhead fijo)
        "prefijo_v2_chars": _prefijo_v2_chars(),   # S2
        "out_piso_tokens": a_out,                  # S3
        "out_por_token_variable": b_out,           # S3
    }


# ------------------------------------------------------------------------- #
# Estimación                                                                 #
# ------------------------------------------------------------------------- #

def _estimar_conjunto(chunks: list[dict], nombre: str, anc: dict) -> dict:
    r = anc["ratio_chars_por_token"]

    p_chars = len(prompt_e1.PREFIJO_SISTEMA) + len(
        json.dumps([prompt_e1.TOOL_SCHEMA_E1], ensure_ascii=False))
    # S2: escala del intercepto real por tamaño relativo del prefijo.
    p_tok = round(anc["intercepto_por_request_tokens"] * p_chars / anc["prefijo_v2_chars"])

    var_toks = [len(prompt_e1.build_user_message(c)) / r for c in chunks]
    n = len(chunks)
    v_total = round(sum(var_toks))
    out_total = round(sum(
        anc["out_piso_tokens"] + anc["out_por_token_variable"] * v for v in var_toks))

    # --- cuentas de input, en tokens (S7) ---
    in_sin_caching = n * p_tok + v_total                      # prefijo repetido n veces
    cache_write = p_tok                                       # S4: 1 write por corrida
    cache_read = p_tok * (n - 1)
    in_no_cacheado = v_total
    in_equiv_con_caching = round(
        in_no_cacheado + MULT_CACHE_WRITE * cache_write + MULT_CACHE_READ * cache_read)
    ahorro_input_pct = round(100 * (1 - in_equiv_con_caching / in_sin_caching), 1)

    return {
        "conjunto": nombre,
        "n_chunks": n,
        "prefijo_tokens": p_tok,
        "prefijo_chars": p_chars,
        "variable_tokens_total": v_total,
        "variable_tokens_mediana": round(statistics.median(var_toks)),
        "output_tokens_total": out_total,
        "sin_caching": {
            "input_tokens_facturables": in_sin_caching,
            "formula_usd": (
                f"costo = {in_sin_caching}/1e6 × P_in + {out_total}/1e6 × P_out"
            ),
        },
        "con_caching": {
            "input_tokens_no_cacheados": in_no_cacheado,
            "cache_write_tokens": cache_write,
            "cache_read_tokens": cache_read,
            "input_equivalente_tokens": in_equiv_con_caching,
            "formula_usd": (
                f"costo = {in_no_cacheado}/1e6 × P_in + {cache_write}/1e6 × P_cache_write "
                f"+ {cache_read}/1e6 × P_cache_read + {out_total}/1e6 × P_out"
            ),
            "cuenta_equivalente_input": (
                f"{in_no_cacheado} + 1,25×{cache_write} + 0,10×{cache_read} "
                f"= {in_equiv_con_caching} tokens-equivalentes de input "
                f"(vs {in_sin_caching} sin caching)"
            ),
        },
        "ahorro_componente_input_pct": ahorro_input_pct,
    }


def estimar() -> dict:
    anc = anclas_empiricas()
    todos = cargar_chunks()
    pro = [c for c in todos if c["to"] == "pro"]

    calibracion = _estimar_conjunto(pro, "calibracion_pro", anc)
    corpus = _estimar_conjunto(todos, "corpus_5TOs", anc)

    r = anc["ratio_chars_por_token"]
    por_to = {}
    for to in comun_e1.TOS:
        sub = [c for c in todos if c["to"] == to]
        por_to[to] = {
            "n_chunks": len(sub),
            "variable_tokens_total": round(
                sum(len(prompt_e1.build_user_message(c)) for c in sub) / r),
        }

    return {
        "prefijo_hash": prompt_e1.PREFIJO_HASH,
        "supuestos": {
            "S1_ratio_chars_por_token": round(r, 3),
            "S1_base": f"ajuste in=A+B·chars sobre {anc['n_pares']} pares reales de "
                       "grafo_v2/code/cache_v2/full/ (mensaje v2 reconstruido byte a byte)",
            "S2_prefijo_e1_tokens": None,  # se completa abajo (depende del conjunto, es igual en ambos)
            "S2_base": f"intercepto real {round(anc['intercepto_por_request_tokens'])} tok "
                       f"× (chars prefijo E1 / {anc['prefijo_v2_chars']} chars prefijo v2)",
            "S3_out": f"out_i = {round(anc['out_piso_tokens'])} + "
                      f"{round(anc['out_por_token_variable'], 3)} × var_i "
                      f"(ajuste sobre los mismos {anc['n_pares']} resultados reales)",
            "S4_writes_de_prefijo_por_corrida": 1,
            "S5_descuento_batch": "no asumido (D4 condicional)",
            "S6_reintentos_y_ratchet": "no incluidos (solo primera pasada E1)",
            "S7_multiplicadores": {"cache_write": MULT_CACHE_WRITE, "cache_read": MULT_CACHE_READ},
            "nota_ancla_descartada": "el ancla harness (2.872 chars/1.433 tok ≈ 2,0 chars/token) "
                                     "se descartó para la parte variable: es JSON de tools, no prosa",
        },
        "calibracion": calibracion,
        "corpus": corpus,
        "corpus_por_to": por_to,
        "nota_never_pay_twice": (
            "si el corpus corre después de la calibración con el mismo prefijo y "
            "namespace, los 88 chunks de pro son hits de la caché local "
            "(never-pay-twice): el incremental real del corpus es 1.389 chunks. "
            "La tabla estima el corpus completo (1.477) sin ese descuento."
        ),
        "precios": "NO consultados: P_in, P_out, P_cache_write, P_cache_read se "
                   "resuelven en la autorización de fase B contra la documentación "
                   "oficial vigente.",
    }


def _tabla(res: dict) -> str:
    filas = []
    filas.append(f"{'':38s} {'calibración (pro)':>20s} {'corpus (5 TOs)':>20s}")
    c, k = res["calibracion"], res["corpus"]
    def fila(label, key, sub=None):
        gv = lambda d: d[sub][key] if sub else d[key]
        filas.append(f"{label:38s} {gv(c):>20,} {gv(k):>20,}")
    fila("chunks", "n_chunks")
    fila("prefijo (tokens, una vez)", "prefijo_tokens")
    fila("variable total (tokens)", "variable_tokens_total")
    fila("output total (tokens)", "output_tokens_total")
    fila("input SIN caching (tokens)", "input_tokens_facturables", "sin_caching")
    fila("input no cacheado (tokens)", "input_tokens_no_cacheados", "con_caching")
    fila("cache write (tokens)", "cache_write_tokens", "con_caching")
    fila("cache read (tokens)", "cache_read_tokens", "con_caching")
    fila("input equivalente CON caching", "input_equivalente_tokens", "con_caching")
    filas.append(f"{'ahorro componente input':38s} {c['ahorro_componente_input_pct']:>19.1f}% {k['ahorro_componente_input_pct']:>19.1f}%")
    return "\n".join(filas)


def main():
    res = estimar()
    res["supuestos"]["S2_prefijo_e1_tokens"] = res["corpus"]["prefijo_tokens"]
    out = BASE / "salida" / "estimacion_e1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res["supuestos"], ensure_ascii=False, indent=1))
    print()
    print(_tabla(res))
    print()
    print("calibración:", res["calibracion"]["con_caching"]["formula_usd"])
    print("corpus:     ", res["corpus"]["con_caching"]["formula_usd"])
    print(f"-> {out}")


if __name__ == "__main__":
    main()
