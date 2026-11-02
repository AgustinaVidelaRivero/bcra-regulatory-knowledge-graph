"""Control del modelo para la clasificación por tipo de las 20 preguntas de la tanda 0
bajo la regla v2 (U-EV2-TIPO-T0).

Reutiliza sin modificar los scripts sellados scripts/ev2_tipo_control.py (v1) y
scripts/ev2_tipo_control_v2.py (V2b): importa del v1 el armado del prompt, el parseo de
la respuesta, la carga del entorno y las constantes de modelo, temperatura, max_tokens y
precios. Lo que en el v1 y en el V2b está cableado (hoja y su sha, regla y su sha,
salidas, base de captura) acá entra por argumento. cargar_filas del v1 exige 40 filas,
por eso la carga de la hoja se reimplementa acá con --n.

Control CIEGO: en los modos --selfcheck, --count y --run el script lee únicamente la
hoja y la regla. El JSON de preguntas (que trae tipo_previsto) y la clasificación de la
autora entran solo en --comparar, que corre después y por separado. --run imprime
únicamente agregados (distribución de tipos); nunca el tipo ni la nota por pregunta.

Argumentos comunes (obligatorios en todos los modos):
  --hoja PATH         hoja a ciegas (csv: orden,id,to,pregunta,ancla,criterios,texto_ancla,tipo,nota).
  --sha-hoja SHA      sha256 esperado de --hoja; si no coincide, FRENO.
  --regla PATH        regla a aplicar (la v2).
  --sha-regla SHA     sha256 esperado de --regla; si no coincide, FRENO.
  --out-dir DIR       subdirectorio de salida.
  --n N               cantidad de filas esperada en la hoja (20).

Modos (exactamente uno):
  --selfcheck  arma los N prompts y verifica su contenido (offline, sin API). Para las
               filas con dos anclas verifica que el prompt lleve los dos textos tal como
               están en texto_ancla (separados por «=====»).
  --count      cuenta tokens de entrada de los N prompts (endpoint gratuito) y calcula la
               cota de costo; escribe <out-dir>/count_tokens_tanda0.json.
  --run        hace las N llamadas (temperatura 0, sin thinking, un reintento por
               pregunta) vía CachingClient y escribe <out-dir>/tipo_pregunta_control_tanda0.json
               con tokens y costo calculado dentro del artefacto. Exige --tope-usd.
  --comparar   sin llamadas: compara el control con la clasificación de la autora
               (--autora, --sha-autora; csv con columnas orden,id,tipo,nota o la hoja
               completa con tipo y nota rellenados) y con tipo_previsto del JSON de preguntas
               (--previsto, --sha-previsto); escribe <out-dir>/comparacion_tanda0.json con
               tres tablas (modelo vs autora, modelo vs previsto, autora vs previsto) y la
               lista de desacuerdos. No hay resultado esperado declarado: toda diferencia
               se reporta y nada se corrige.
"""
import argparse, csv, hashlib, json, sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ev2_tipo_control import (armar_prompt, parsear, cargar_env, TIPOS,
                              PRECIO_IN, PRECIO_OUT, MODELO, TEMPERATURE, MAX_TOKENS)

REPO = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO / "data/experiment/evaluacion"
T0_DIR = REPO / "data/experiment/ev2_tanda0/preguntas"

DOMAIN = "control_tipo_tanda0"
RUN_LABEL = "U-EV2-TIPO-T0"
NOMBRE_CONTROL = "tipo_pregunta_control_tanda0.json"
NOMBRE_COUNT = "count_tokens_tanda0.json"
NOMBRE_COMPARACION = "comparacion_tanda0.json"
NOMBRE_DB = "control_tipo_tanda0.db"

COLUMNAS_HOJA = ["orden", "id", "to", "pregunta", "ancla", "criterios", "texto_ancla", "tipo", "nota"]
COLUMNAS_AUTORA = ["orden", "id", "tipo", "nota"]
SEPARADOR_ANCLAS = " ; "       # columna ancla de la hoja (generar_hoja_tanda0.py)
SEPARADOR_TEXTOS = "====="     # columna texto_ancla de la hoja

# Insumos de --comparar (defaults: los reales del repo; el dry run los reemplaza por sintéticos).
AUTORA_DEFAULT = T0_DIR / "tipo_pregunta_autora_tanda0.csv"
PREVISTO_DEFAULT = T0_DIR / "preguntas_tanda0.json"
SHA_PREVISTO_DEFAULT = "b36e0662170004a5e1adfcf7ea26e91ba45a469dbbda058aac3a47f4c0cc3743"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def verificar_sello(nombre: str, p: Path, esperado: str) -> str:
    if not p.exists():
        sys.exit(f"FRENO: falta {nombre}: {p}")
    s = sha256(p)
    if s != esperado:
        sys.exit(f"FRENO: sha inesperado en {nombre} {rel(p)}: {s} (esperado {esperado})")
    return s


def cargar_hoja(hoja: Path, n: int):
    with open(hoja, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames != COLUMNAS_HOJA:
            sys.exit(f"FRENO: columnas de la hoja {rd.fieldnames} distintas de {COLUMNAS_HOJA}")
        rows = list(rd)
    rows.sort(key=lambda r: int(r["orden"]))
    if len(rows) != n:
        sys.exit(f"FRENO: la hoja tiene {len(rows)} filas; --n {n}")
    if [int(r["orden"]) for r in rows] != list(range(1, n + 1)):
        sys.exit("FRENO: la columna orden no es 1..n")
    if len({r["id"] for r in rows}) != n:
        sys.exit("FRENO: ids repetidos en la hoja")
    return rows


def anclas_de(r: dict):
    return r["ancla"].split(SEPARADOR_ANCLAS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoja", required=True, help="hoja a ciegas (csv)")
    ap.add_argument("--sha-hoja", required=True, help="sha256 esperado de --hoja")
    ap.add_argument("--regla", required=True, help="regla a aplicar (archivo .md)")
    ap.add_argument("--sha-regla", required=True, help="sha256 esperado de --regla")
    ap.add_argument("--out-dir", required=True, help="subdirectorio de salida")
    ap.add_argument("--n", type=int, default=20, help="filas esperadas en la hoja")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--comparar", action="store_true")
    ap.add_argument("--tope-usd", type=float, default=None,
                    help="tope de gasto autorizado; --run aborta si el gasto acumulado lo supera")
    ap.add_argument("--control", default=None,
                    help="(--comparar) JSON del control; default <out-dir>/" + NOMBRE_CONTROL)
    ap.add_argument("--autora", default=str(AUTORA_DEFAULT),
                    help="(--comparar) csv de la autora: orden,id,tipo,nota")
    ap.add_argument("--sha-autora", default=None,
                    help="(--comparar) sha256 declarado del csv de la autora; obligatorio")
    ap.add_argument("--previsto", default=str(PREVISTO_DEFAULT),
                    help="(--comparar) JSON de preguntas con tipo_previsto")
    ap.add_argument("--sha-previsto", default=SHA_PREVISTO_DEFAULT,
                    help="(--comparar) sha256 esperado de --previsto")
    a = ap.parse_args()
    if sum(bool(x) for x in (a.selfcheck, a.count, a.run, a.comparar)) != 1:
        sys.exit("FRENO: elegir exactamente un modo entre --selfcheck, --count, --run, --comparar")

    hoja_path, regla_path, out_dir = Path(a.hoja), Path(a.regla), Path(a.out_dir)
    sh = verificar_sello("hoja", hoja_path, a.sha_hoja)
    sr = verificar_sello("regla", regla_path, a.sha_regla)
    regla = regla_path.read_text(encoding="utf-8")
    rows = cargar_hoja(hoja_path, a.n)
    prompts = [(r, armar_prompt(regla, r)) for r in rows]
    OUT = Path(a.control) if a.control else out_dir / NOMBRE_CONTROL

    if a.selfcheck:
        ok = True
        dos_anclas = []
        for r, p in prompts:
            for pieza in (regla.rstrip(), r["pregunta"], r["ancla"], r["texto_ancla"]):
                ok &= pieza in p
            for c in r["criterios"].split(" | "):
                ok &= c in p
            anclas = anclas_de(r)
            # el texto de cada ancla va tal cual está en texto_ancla; k anclas => k-1 separadores
            ok &= r["texto_ancla"].count(SEPARADOR_TEXTOS) == len(anclas) - 1
            for anc in anclas:
                ok &= anc in p
            if len(anclas) > 1:
                dos_anclas.append((int(r["orden"]), r["id"], anclas))
        v2_en_todos = all(p.startswith("# Regla de clasificación por tipo — versión 2")
                          and "## Interpretación v2" in p for _, p in prompts)
        print("hoja:", rel(hoja_path), "sha256:", sh, "| filas:", len(rows))
        print("regla:", rel(regla_path), "sha256:", sr)
        print("prompts armados:", len(prompts))
        print("cada prompt contiene regla + pregunta + ancla(s) + criterios + texto_ancla:", ok)
        print("cada prompt empieza con la v2 e incluye la sección 'Interpretación v2':", v2_en_todos)
        print("filas con dos anclas (orden, id, anclas):", len(dos_anclas))
        for o, i, anc in dos_anclas:
            print(f"  {o:>2} {i} {anc}")
        tam = sorted(len(p.encode()) for _, p in prompts)
        print("bytes por prompt: min/median/max =", tam[0], tam[len(tam) // 2], tam[-1])
        print("bytes de la regla:", len(regla.encode()))
        print("\n===== prompt de orden 1 (íntegro) =====\n" + prompts[0][1] + "\n===== fin =====")
        return

    if a.comparar:
        if a.sha_autora is None:
            sys.exit("FRENO: --comparar exige --sha-autora (sha declarado del csv de la autora)")
        autora_path, previsto_path = Path(a.autora), Path(a.previsto)
        if not OUT.exists():
            sys.exit(f"FRENO: falta el control {OUT}")
        sa = verificar_sello("csv de la autora", autora_path, a.sha_autora)
        sp = verificar_sello("JSON de preguntas", previsto_path, a.sha_previsto)
        ctl = json.loads(OUT.read_text(encoding="utf-8"))
        if ctl.get("sha256_hoja") != sh or ctl.get("sha256_regla") != sr:
            sys.exit("FRENO: el control declara sha256_hoja/sha256_regla distintos de los esperados")
        em = {int(e["orden"]): e for e in ctl["entradas"]}
        esperado_ordenes = {int(r["orden"]): r["id"] for r in rows}
        if {o: e["id"] for o, e in em.items()} != esperado_ordenes:
            sys.exit("FRENO: (orden, id) del control no coinciden con la hoja")

        with open(autora_path, encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            if rd.fieldnames not in (COLUMNAS_AUTORA, COLUMNAS_HOJA):
                sys.exit(f"FRENO: columnas del csv de la autora {rd.fieldnames} distintas de {COLUMNAS_AUTORA} "
                         f"y de la hoja {COLUMNAS_HOJA}")
            formato_autora = "hoja completa con tipo y nota" if rd.fieldnames == COLUMNAS_HOJA else "orden,id,tipo,nota"
            au_rows = list(rd)
        if len(au_rows) != a.n:
            sys.exit(f"FRENO: el csv de la autora tiene {len(au_rows)} filas; --n {a.n}")
        ea = {int(r["orden"]): r for r in au_rows}
        if {o: r["id"] for o, r in ea.items()} != esperado_ordenes:
            sys.exit("FRENO: (orden, id) del csv de la autora no coinciden con la hoja")
        if rd.fieldnames == COLUMNAS_HOJA:
            # la hoja rellenada debe ser la hoja: toda columna salvo tipo y nota coincide fila a fila
            hoja_por_orden = {int(r["orden"]): r for r in rows}
            for o, r in ea.items():
                for col in COLUMNAS_HOJA[:-2]:
                    if r[col] != hoja_por_orden[o][col]:
                        sys.exit(f"FRENO: columna {col!r} del csv de la autora difiere de la hoja en orden {o}")

        qs = json.loads(previsto_path.read_text(encoding="utf-8"))["preguntas"]
        prev = {q["id"]: q["tipo_previsto"] for q in qs}
        if set(prev) != set(esperado_ordenes.values()):
            sys.exit("FRENO: ids del JSON de preguntas no coinciden con la hoja")

        avisos = []
        for o in sorted(em):
            for fuente, t in (("modelo", em[o]["tipo"]), ("autora", ea[o]["tipo"].strip()),
                              ("previsto", prev[em[o]["id"]])):
                if t not in TIPOS:
                    avisos.append({"orden": o, "id": em[o]["id"], "fuente": fuente, "tipo": t,
                                   "aviso": "tipo fuera del conjunto de la regla"})

        def tabla(nombre_a, nombre_b, get_a, get_b):
            filas = []
            for o in sorted(em):
                ta, tb = get_a(o), get_b(o)
                filas.append({"orden": o, "id": em[o]["id"], f"tipo_{nombre_a}": ta, f"tipo_{nombre_b}": tb,
                              "acuerdo": ta == tb})
            return {
                "acuerdos": sum(1 for f in filas if f["acuerdo"]),
                "sobre": len(filas),
                "ordenes_sin_acuerdo": [f["orden"] for f in filas if not f["acuerdo"]],
                f"distribucion_{nombre_a}": dict(Counter(f[f"tipo_{nombre_a}"] for f in filas)),
                f"distribucion_{nombre_b}": dict(Counter(f[f"tipo_{nombre_b}"] for f in filas)),
                "filas": filas,
            }

        t_modelo = lambda o: em[o]["tipo"]
        t_autora = lambda o: ea[o]["tipo"].strip()
        t_previsto = lambda o: prev[em[o]["id"]]
        t1 = tabla("modelo", "autora", t_modelo, t_autora)
        t2 = tabla("modelo", "previsto", t_modelo, t_previsto)
        t3 = tabla("autora", "previsto", t_autora, t_previsto)
        desacuerdos = []
        for o in sorted(em):
            tm, ta, tp = t_modelo(o), t_autora(o), t_previsto(o)
            pares = [n for n, cond in (("modelo_vs_autora", tm != ta), ("modelo_vs_previsto", tm != tp),
                                       ("autora_vs_previsto", ta != tp)) if cond]
            if pares:
                desacuerdos.append({"orden": o, "id": em[o]["id"], "tipo_modelo": tm, "tipo_autora": ta,
                                    "tipo_previsto": tp, "nota_modelo": em[o]["nota"],
                                    "nota_autora": ea[o]["nota"], "desacuerdo_en": pares})
        salida = {
            "fecha": date.today().isoformat(),
            "resultado_esperado": "no declarado: toda diferencia se reporta, nada se corrige; la adjudicación es de la autora",
            "n": a.n,
            "insumos": {
                "control": {"ruta": rel(OUT), "sha256": sha256(OUT)},
                "autora": {"ruta": rel(autora_path), "sha256": sa, "formato": formato_autora},
                "previsto": {"ruta": rel(previsto_path), "sha256": sp},
                "hoja": {"ruta": rel(hoja_path), "sha256": sh},
                "regla": {"ruta": rel(regla_path), "sha256": sr},
            },
            "tabla_1_modelo_vs_autora": t1,
            "tabla_2_modelo_vs_previsto": t2,
            "tabla_3_autora_vs_previsto": t3,
            "desacuerdos": desacuerdos,
            "avisos": avisos,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        comp = out_dir / NOMBRE_COMPARACION
        comp.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("comparación escrita en:", rel(comp))
        print("insumos:", json.dumps(salida["insumos"], indent=1, ensure_ascii=False))
        for titulo, t, na, nb in (("[Tabla 1] modelo vs autora", t1, "modelo", "autora"),
                                  ("[Tabla 2] modelo vs previsto", t2, "modelo", "previsto"),
                                  ("[Tabla 3] autora vs previsto", t3, "autora", "previsto")):
            print(f"\n{titulo}")
            print(f"  distribución {na}:", t[f"distribucion_{na}"])
            print(f"  distribución {nb}:", t[f"distribucion_{nb}"])
            print(f"  acuerdos: {t['acuerdos']} / {t['sobre']} | órdenes sin acuerdo: {t['ordenes_sin_acuerdo']}")
        print("\n[Desacuerdos] preguntas con al menos un par en desacuerdo:", len(desacuerdos))
        for d in desacuerdos:
            print(f"  orden {d['orden']:>2} {d['id']}: modelo={d['tipo_modelo']!r} autora={d['tipo_autora']!r} "
                  f"previsto={d['tipo_previsto']!r} | {', '.join(d['desacuerdo_en'])}")
            print(f"    nota del modelo: {d['nota_modelo']}")
            print(f"    nota de la autora: {d['nota_autora']}")
        print("\n[Avisos] tipos fuera del conjunto de la regla:", len(avisos))
        for av in avisos:
            print(f"  orden {av['orden']:>2} {av['id']} {av['fuente']}: {av['tipo']!r}")
        return

    cargar_env()
    import anthropic
    real = anthropic.Anthropic(max_retries=3)

    if a.count:
        tot = 0; por_fila = []
        for r, p in prompts:
            n_tok = real.messages.count_tokens(model=MODELO, messages=[{"role": "user", "content": p}]).input_tokens
            tot += n_tok; por_fila.append((int(r["orden"]), r["id"], n_tok))
        print("tokens de entrada por fila (orden, id, tokens):")
        for o, i, n_tok in por_fila: print(f"  {o:>2} {i} {n_tok:>6}")
        print(f"TOTAL tokens de entrada ({a.n} prompts):", tot)
        cin = tot / 1e6 * PRECIO_IN
        cout = a.n * MAX_TOKENS / 1e6 * PRECIO_OUT
        print(f"cota de costo {a.n} llamadas: entrada USD {cin:.4f} + salida (peor caso {MAX_TOKENS} tok/llamada) USD {cout:.4f} = USD {cin+cout:.4f}")
        print(f"cota peor caso con {a.n} reintentos ({2*a.n} llamadas): USD {2*(cin+cout):.4f}")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / NOMBRE_COUNT).write_text(json.dumps({
            "modelo": MODELO, "hoja": rel(hoja_path), "regla": rel(regla_path),
            "sha256_regla": sr, "sha256_hoja": sh, "n": a.n,
            "total_input_tokens": tot, "por_fila": por_fila,
            "precios_usd_por_millon": {"entrada": PRECIO_IN, "salida": PRECIO_OUT},
            "max_tokens": MAX_TOKENS,
            f"cota_usd_{a.n}_llamadas": {"entrada": round(cin, 6), "salida_peor_caso": round(cout, 6), "total": round(cin + cout, 6)},
            f"cota_usd_{2*a.n}_llamadas_peor_caso": round(2 * (cin + cout), 6),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("conteo escrito en:", rel(out_dir / NOMBRE_COUNT))
        return

    if a.run:
        if OUT.exists():
            sys.exit(f"FRENO: {OUT} ya existe")
        if a.tope_usd is None:
            sys.exit("FRENO: --run exige --tope-usd autorizado por mandato")
        out_dir.mkdir(parents=True, exist_ok=True)
        sys.path.insert(0, str(EVAL_DIR))
        import llm_cache as lc
        code_ver = f"control-tipo-tanda0+regla={sr[:12]}"
        db_path = out_dir / NOMBRE_DB
        client = lc.CachingClient(
            real, domain=DOMAIN, db_path=db_path,
            namespace=lc.make_namespace(DOMAIN, code_ver=code_ver, thinking=False),
            thinking_enabled=False, run_label=RUN_LABEL)
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
        distribucion = dict(Counter(e["tipo"] for e in entradas))
        salida = {
            "modelo": MODELO,
            "modelo_segun_api": sorted(modelos_api.keys()),
            "temperatura": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "thinking": False,
            "hoja": rel(hoja_path),
            "regla": rel(regla_path),
            "sha256_regla": sr,
            "sha256_hoja": sh,
            "n": a.n,
            "fecha": date.today().isoformat(),
            "reintentos": {
                "maximo_por_pregunta": 1,
                "mecanismo": "mismo prompt; metadata.user_id='reintento-1' para que la clave de cache difiera",
                "ordenes_reintentados": ordenes_reintentados,
            },
            "sin_respuesta": n_sin,
            "stop_reason": {str(k): v for k, v in stops.items()},
            "tokens_entrada": tok_in,
            "tokens_salida": tok_out,
            "precios_usd_por_millon": {"entrada": PRECIO_IN, "salida": PRECIO_OUT},
            "costo_usd_calculado": round(gasto, 6),
            "distribucion_tipos": distribucion,
            "captura": {"db": rel(db_path), "domain": DOMAIN, "code_ver": code_ver, "run_label": RUN_LABEL,
                        "namespace": client.namespace},
            "entradas": entradas,
        }
        OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stats = client.stats()
        client.close()
        # Solo agregados: nada de tipo/nota por pregunta (el desglose sale por --comparar).
        print("control escrito en:", rel(OUT))
        print("entradas escritas:", len(entradas))
        print("sin_respuesta:", n_sin, "| reintentos:", n_reint, "| órdenes reintentados:", ordenes_reintentados)
        print("modelo según API:", dict(modelos_api))
        print("temperatura:", TEMPERATURE, "| thinking: False | max_tokens:", MAX_TOKENS)
        print("stop_reason:", dict(stops))
        print(f"tokens entrada={tok_in} salida={tok_out}")
        print(f"costo calculado (USD {PRECIO_IN}/{PRECIO_OUT} por M): USD {gasto:.4f} (tope USD {a.tope_usd})")
        print("distribución de tipos del modelo (agregado, sin detalle por pregunta):", distribucion)
        print("stats caché:", stats)


if __name__ == "__main__":
    main()
