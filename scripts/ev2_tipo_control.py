"""Control del modelo para la clasificación por tipo del conjunto EV2.

Versión en scripts/ del script corrido en U-EV2-TIPO-2 desde el scratchpad; misma
lógica, con las rutas al scratchpad convertidas en --db y --count-out (defaults en
el repo) y un modo aditivo --verificar-control.

Modos:
  --selfcheck  arma los 40 prompts y verifica su contenido (offline, sin API).
  --count      cuenta tokens de entrada de los 40 prompts (endpoint gratuito) y
               calcula la cota de costo.
  --run        hace las 40 llamadas (temperatura 0) vía CachingClient con .db en
               el scratchpad y escribe tipo_pregunta_control.json. Nunca imprime
               tipo ni nota.
"""
import argparse, csv, hashlib, json, re, sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO / "data/experiment/evaluacion"
D = REPO / "data/experiment/exploracion/ev2_fidelidad"
REGLA = D / "regla_tipo_pregunta.md"
HOJA = D / "tipo_pregunta_hoja.csv"
OUT = D / "tipo_pregunta_control.json"
DB_PATH_DEFAULT = D / "control_tipo_ev2.db"
COUNT_OUT_DEFAULT = D / "count_tokens_control.json"

SHA_REGLA_ESPERADO = "35c8be102b68c8ef385686bd037c3e0b788f23f5a112380902fc2c2924b4a072"
SHA_HOJA_ESPERADO = "30c1c02892e9ef68ff664b0728dd149cc96185280815d654d72c025689a199ed"

MODELO = "claude-sonnet-4-6"      # data/experiment/ev2_juez/juez.py:37
TEMPERATURE = 0.0                 # data/experiment/ev2_juez/juez.py:38
MAX_TOKENS = 1024
TIPOS = {"dato directo", "varios puntos", "abstención", "dudoso"}
# Precios Sonnet 4.6 (USD por millón de tokens), tabla de la skill claude-api.
PRECIO_IN, PRECIO_OUT = 3.00, 15.00

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def cargar_filas():
    rows = list(csv.DictReader(open(HOJA, encoding="utf-8", newline="")))
    rows.sort(key=lambda r: int(r["orden"]))
    assert len(rows) == 40
    return rows

def armar_prompt(regla: str, r: dict) -> str:
    crit = "\n".join(f"{i}. {c}" for i, c in enumerate(r["criterios"].split(" | "), 1))
    return (
        f"{regla.rstrip()}\n\n---\n\n"
        "Aplicá la regla anterior a la pregunta siguiente, usando únicamente el material "
        "permitido que se transcribe a continuación.\n\n"
        f"Pregunta: {r['pregunta']}\n\n"
        f"Ancla: {r['ancla']}\n\n"
        f"Criterios:\n{crit}\n\n"
        f"Texto del ancla:\n\n{r['texto_ancla']}\n\n---\n\n"
        "Respondé únicamente con un objeto JSON con exactamente dos campos:\n"
        "- \"tipo\": exactamente uno de \"dato directo\", \"varios puntos\", \"abstención\", \"dudoso\".\n"
        "- \"nota\": una línea con el criterio que decidió.\n"
        "Sin texto fuera del JSON."
    )

def parsear(texto: str):
    t = texto.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    obj = json.loads(t)
    if not isinstance(obj, dict) or set(obj.keys()) != {"tipo", "nota"}:
        raise ValueError("campos distintos de {tipo, nota}")
    if obj["tipo"] not in TIPOS:
        raise ValueError("tipo fuera del conjunto")
    if not isinstance(obj["nota"], str):
        raise ValueError("nota no es string")
    return obj

def verificar_sellos():
    sr, sh = sha256(REGLA), sha256(HOJA)
    if sr != SHA_REGLA_ESPERADO or sh != SHA_HOJA_ESPERADO:
        sys.exit(f"FRENO: sha inesperado regla={sr} hoja={sh}")
    return sr, sh

def cargar_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(EVAL_DIR / ".env")
    except ImportError:
        for line in (EVAL_DIR / ".env").read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                import os; os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("FRENO: ANTHROPIC_API_KEY ausente")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--verificar-control", action="store_true",
                    help="sin llamadas: compara los 40 prompts armados con los guardados en el control")
    ap.add_argument("--db", default=str(DB_PATH_DEFAULT), help="base de captura (CachingClient)")
    ap.add_argument("--count-out", default=str(COUNT_OUT_DEFAULT), help="salida de --count")
    ap.add_argument("--tope-usd", type=float, default=None,
                    help="tope de gasto autorizado; --run aborta si la cota lo supera")
    a = ap.parse_args()
    sr, sh = verificar_sellos()
    regla = REGLA.read_text(encoding="utf-8")
    rows = cargar_filas()
    prompts = [(r, armar_prompt(regla, r)) for r in rows]

    if a.selfcheck:
        ok = True
        for r, p in prompts:
            for pieza in (regla.rstrip(), r["pregunta"], r["ancla"], r["texto_ancla"]):
                ok &= pieza in p
            for c in r["criterios"].split(" | "):
                ok &= c in p
        print("prompts armados:", len(prompts))
        print("cada prompt contiene regla + pregunta + ancla + criterios + texto_ancla:", ok)
        print("bytes por prompt: min/median/max =", min(len(p.encode()) for _, p in prompts),
              sorted(len(p.encode()) for _, p in prompts)[20], max(len(p.encode()) for _, p in prompts))
        print("bytes de la regla:", len(regla.encode()))
        print("\n===== prompt de orden 1 (íntegro) =====\n" + prompts[0][1] + "\n===== fin =====")
        return

    if a.verificar_control:
        c = json.loads(OUT.read_text(encoding="utf-8"))
        por_orden = {int(r["orden"]): p for r, p in prompts}
        iguales = sum(1 for e in c["entradas"] if por_orden[e["orden"]] == e["prompt"])
        print("prompts del control idénticos a los armados:", iguales, "/", len(c["entradas"]))
        return

    cargar_env()
    import anthropic
    real = anthropic.Anthropic(max_retries=3)

    if a.count:
        tot = 0; por_fila = []
        for r, p in prompts:
            n = real.messages.count_tokens(model=MODELO, messages=[{"role": "user", "content": p}]).input_tokens
            tot += n; por_fila.append((int(r["orden"]), r["id"], n))
        print("tokens de entrada por fila (orden, id, tokens):")
        for o, i, n in por_fila: print(f"  {o:>2} {i} {n:>6}")
        print("TOTAL tokens de entrada (40 prompts):", tot)
        cin = tot / 1e6 * PRECIO_IN
        cout = 40 * MAX_TOKENS / 1e6 * PRECIO_OUT
        print(f"cota de costo 40 llamadas: entrada USD {cin:.4f} + salida (peor caso {MAX_TOKENS} tok/llamada) USD {cout:.4f} = USD {cin+cout:.4f}")
        print(f"cota peor caso con 40 reintentos (80 llamadas): USD {2*(cin+cout):.4f}")
        Path(a.count_out).write_text(json.dumps({"total_input_tokens": tot, "por_fila": por_fila}))
        return

    if a.run:
        if OUT.exists():
            sys.exit("FRENO: tipo_pregunta_control.json ya existe")
        if a.tope_usd is None:
            sys.exit("FRENO: --run exige --tope-usd autorizado por mandato")
        sys.path.insert(0, str(EVAL_DIR))
        import llm_cache as lc
        client = lc.CachingClient(
            real, domain="control_tipo_ev2", db_path=Path(a.db),
            namespace=lc.make_namespace("control_tipo_ev2",
                                        code_ver=f"control-tipo-ev2-v1+regla={sr[:12]}",
                                        thinking=False),
            thinking_enabled=False, run_label="U-EV2-TIPO-2")
        entradas, modelos_api, stops = [], Counter(), Counter()
        n_reint = n_sin = 0
        ordenes_reintentados = []
        tok_in = tok_out = 0
        gasto = 0.0
        for r, p in prompts:
            raw_txt = None; obj = None
            for intento in (0, 1):
                kw = dict(model=MODELO, max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
                          messages=[{"role": "user", "content": p}])
                if intento == 1:
                    kw["metadata"] = {"user_id": "reintento-1"}   # cambia la clave de caché; el prompt no cambia
                    n_reint += 1
                    ordenes_reintentados.append(int(r["orden"]))
                resp = client.messages.create(**kw)
                modelos_api[getattr(resp, "model", "")] += 1
                stops[getattr(resp, "stop_reason", None)] += 1
                u = resp.usage
                tok_in += u.input_tokens; tok_out += u.output_tokens
                gasto = tok_in / 1e6 * PRECIO_IN + tok_out / 1e6 * PRECIO_OUT
                if gasto > a.tope_usd:
                    sys.exit(f"FRENO: gasto acumulado USD {gasto:.4f} supera el tope USD {a.tope_usd}")
                raw_txt = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                try:
                    obj = parsear(raw_txt); break
                except Exception:
                    obj = None
            if obj is None:
                n_sin += 1
                obj = {"tipo": "sin_respuesta", "nota": raw_txt if raw_txt is not None else ""}
            entradas.append({"orden": int(r["orden"]), "id": r["id"],
                             "tipo": obj["tipo"], "nota": obj["nota"], "prompt": p})
        salida = {
            "modelo": MODELO,
            "modelo_segun_api": sorted(modelos_api.keys()),
            "temperatura": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "sha256_regla": sr,
            "sha256_hoja": sh,
            "fecha": date.today().isoformat(),
            "reintentos": {
                "maximo_por_pregunta": 1,
                "mecanismo": "mismo prompt; metadata.user_id='reintento-1' para que la clave de cache difiera",
                "ordenes_reintentados": ordenes_reintentados,
            },
            "entradas": entradas,
        }
        OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        client.close()
        # Solo estadísticas selladas: nada de tipo/nota.
        print("entradas escritas:", len(entradas))
        print("sin_respuesta:", n_sin, "| reintentos:", n_reint)
        print("modelo según API:", dict(modelos_api))
        print("stop_reason:", dict(stops))
        print(f"tokens entrada={tok_in} salida={tok_out}")
        print(f"costo calculado (precios Sonnet 4.6 USD 3/15 por M): USD {gasto:.4f}")
        print("stats caché:", client.stats())

if __name__ == "__main__":
    main()
