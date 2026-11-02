"""Control del modelo para la clasificación por tipo bajo la regla v2 (U-EV2-TIPO-V2b).

Reutiliza sin modificar el script sellado scripts/ev2_tipo_control.py (v1): importa de
él el armado del prompt, el parseo de la respuesta, la carga de la hoja, la carga del
entorno y las constantes de modelo, temperatura, max_tokens y precios. Lo que en el v1
está cableado (ruta y sha de la regla, salida y base de captura) acá entra por argumento,
para que la regla v1, su control y su base de captura queden intactos.

Argumentos comunes (obligatorios):
  --regla PATH        regla a aplicar (la v2).
  --sha-regla SHA     sha256 esperado de --regla; si no coincide, FRENO.
  --out-dir DIR       subdirectorio de salida; recibe el JSON del control, el conteo de
                      tokens, la comparación y la base de captura control_tipo_ev2_v2.db.

Modos:
  --selfcheck  arma los 40 prompts y verifica su contenido (offline, sin API).
  --count      cuenta tokens de entrada de los 40 prompts (endpoint gratuito) y calcula
               la cota de costo; escribe <out-dir>/count_tokens_control_v2.json.
  --run        hace las 40 llamadas (temperatura 0, sin thinking, un reintento por
               pregunta) vía CachingClient y escribe <out-dir>/tipo_pregunta_control_v2.json,
               con tokens y costo calculado dentro del artefacto. Exige --tope-usd.
  --comparar   sin llamadas: compara el control v2 con el control v1 sellado y con el
               tipo final sellado; escribe <out-dir>/comparacion_control_v2.json.

La hoja es la misma del v1 (tipo_pregunta_hoja.csv) y su sha se verifica igual que allí.
"""
import argparse, hashlib, json, sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ev2_tipo_control import (armar_prompt, parsear, cargar_filas, cargar_env,
                              PRECIO_IN, PRECIO_OUT, MODELO, TEMPERATURE, MAX_TOKENS)

REPO = Path(__file__).resolve().parents[1]
EVAL_DIR = REPO / "data/experiment/evaluacion"
D = REPO / "data/experiment/exploracion/ev2_fidelidad"
HOJA = D / "tipo_pregunta_hoja.csv"
SHA_HOJA_ESPERADO = "30c1c02892e9ef68ff664b0728dd149cc96185280815d654d72c025689a199ed"

# Artefactos sellados contra los que compara --comparar (no se modifican).
CONTROL_V1 = D / "tipo_pregunta_control.json"
SHA_CONTROL_V1_ESPERADO = "b5cf3b267caec6ae49cb8bb7a0bc080c69ced4abff3dd3561b10dd825243e281"
TIPO_FINAL = D / "tipo_pregunta_ev2.json"
SHA_TIPO_FINAL_ESPERADO = "f96055e098d0b59afcbd22ecae2c160147ec97cb0c038b4f783be546a8f53803"

DOMAIN = "control_tipo_ev2_v2"
RUN_LABEL = "U-EV2-TIPO-V2b"
NOMBRE_CONTROL = "tipo_pregunta_control_v2.json"
NOMBRE_COUNT = "count_tokens_control_v2.json"
NOMBRE_COMPARACION = "comparacion_control_v2.json"
NOMBRE_DB = "control_tipo_ev2_v2.db"

# Esperado declarado por el mandato para --comparar.
ESPERADO_CAMBIOS_V1_V2 = {20: ("varios puntos", "dato directo"), 30: ("varios puntos", "dato directo")}
ESPERADO_ACUERDOS_FINAL = 40


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(REPO))


def verificar_sellos(regla: Path, sha_regla_esperado: str):
    sr, sh = sha256(regla), sha256(HOJA)
    if sr != sha_regla_esperado or sh != SHA_HOJA_ESPERADO:
        sys.exit(f"FRENO: sha inesperado regla={sr} hoja={sh}")
    return sr, sh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regla", required=True, help="regla a aplicar (archivo .md)")
    ap.add_argument("--sha-regla", required=True, help="sha256 esperado de --regla")
    ap.add_argument("--out-dir", required=True, help="subdirectorio de salida")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--comparar", action="store_true")
    ap.add_argument("--tope-usd", type=float, default=None,
                    help="tope de gasto autorizado; --run aborta si el gasto acumulado lo supera")
    a = ap.parse_args()
    if sum(bool(x) for x in (a.selfcheck, a.count, a.run, a.comparar)) != 1:
        sys.exit("FRENO: elegir exactamente un modo entre --selfcheck, --count, --run, --comparar")

    regla_path = Path(a.regla)
    out_dir = Path(a.out_dir)
    sr, sh = verificar_sellos(regla_path, a.sha_regla)
    regla = regla_path.read_text(encoding="utf-8")
    rows = cargar_filas()
    prompts = [(r, armar_prompt(regla, r)) for r in rows]
    OUT = out_dir / NOMBRE_CONTROL

    if a.selfcheck:
        ok = True
        for r, p in prompts:
            for pieza in (regla.rstrip(), r["pregunta"], r["ancla"], r["texto_ancla"]):
                ok &= pieza in p
            for c in r["criterios"].split(" | "):
                ok &= c in p
        v2_en_todos = all(p.startswith("# Regla de clasificación por tipo — versión 2")
                          and "## Interpretación v2" in p for _, p in prompts)
        print("regla:", rel(regla_path), "sha256:", sr)
        print("hoja:", rel(HOJA), "sha256:", sh)
        print("prompts armados:", len(prompts))
        print("cada prompt contiene regla + pregunta + ancla + criterios + texto_ancla:", ok)
        print("cada prompt empieza con la v2 e incluye la sección 'Interpretación v2':", v2_en_todos)
        tam = sorted(len(p.encode()) for _, p in prompts)
        print("bytes por prompt: min/median/max =", tam[0], tam[20], tam[-1])
        print("bytes de la regla:", len(regla.encode()))
        print("\n===== prompt de orden 1 (íntegro) =====\n" + prompts[0][1] + "\n===== fin =====")
        return

    if a.comparar:
        for p, esperado in ((OUT, None), (CONTROL_V1, SHA_CONTROL_V1_ESPERADO), (TIPO_FINAL, SHA_TIPO_FINAL_ESPERADO)):
            if not p.exists():
                sys.exit(f"FRENO: falta {p}")
            if esperado is not None and sha256(p) != esperado:
                sys.exit(f"FRENO: sha inesperado en {p}: {sha256(p)}")
        c2 = json.loads(OUT.read_text(encoding="utf-8"))
        c1 = json.loads(CONTROL_V1.read_text(encoding="utf-8"))
        fin = json.loads(TIPO_FINAL.read_text(encoding="utf-8"))
        por_orden = lambda lst: {int(e["orden"]): e for e in lst}
        e2, e1, ef = por_orden(c2["entradas"]), por_orden(c1["entradas"]), por_orden(fin["entradas"])
        assert set(e2) == set(e1) == set(ef) == set(range(1, 41)), "órdenes no coinciden"
        for o in range(1, 41):
            assert e2[o]["id"] == e1[o]["id"] == ef[o]["id"], f"id distinto en orden {o}"

        tabla1, tabla2, fuera = [], [], []
        for o in range(1, 41):
            t1, t2, tf = e1[o]["tipo"], e2[o]["tipo"], ef[o]["tipo_final"]
            cambio = t1 != t2
            tabla1.append({"orden": o, "id": e2[o]["id"], "tipo_v1": t1, "tipo_v2": t2, "cambio": cambio})
            acuerdo = t2 == tf
            tabla2.append({"orden": o, "id": e2[o]["id"], "tipo_v2": t2, "tipo_final": tf, "acuerdo": acuerdo})
            esperado = ESPERADO_CAMBIOS_V1_V2.get(o)
            cambio_ok = (esperado is not None and (t1, t2) == esperado) if cambio else (esperado is None)
            if not cambio_ok or not acuerdo:
                fuera.append({"orden": o, "id": e2[o]["id"], "tipo_v1": t1, "tipo_v2": t2,
                              "tipo_final": tf, "nota_modelo_v2": e2[o]["nota"],
                              "motivo": [m for m, cond in (("cambio v1->v2 fuera de lo esperado", not cambio_ok),
                                                          ("desacuerdo v2 vs tipo final", not acuerdo)) if cond]})
        cambios = [f for f in tabla1 if f["cambio"]]
        acuerdos = sum(1 for f in tabla2 if f["acuerdo"])
        cumple1 = ({f["orden"]: (f["tipo_v1"], f["tipo_v2"]) for f in cambios} == ESPERADO_CAMBIOS_V1_V2)
        cumple2 = (acuerdos == ESPERADO_ACUERDOS_FINAL)
        salida = {
            "fecha": date.today().isoformat(),
            "insumos": {
                rel(OUT): sha256(OUT),
                rel(CONTROL_V1): sha256(CONTROL_V1),
                rel(TIPO_FINAL): sha256(TIPO_FINAL),
            },
            "tabla_1_control_v2_vs_control_v1": {
                "esperado": {"cambios": 2, "detalle": {str(k): {"de": v[0], "a": v[1]} for k, v in ESPERADO_CAMBIOS_V1_V2.items()}},
                "cambios": len(cambios),
                "ordenes_cambiados": [f["orden"] for f in cambios],
                "cumple_esperado": cumple1,
                "distribucion_v1": dict(Counter(f["tipo_v1"] for f in tabla1)),
                "distribucion_v2": dict(Counter(f["tipo_v2"] for f in tabla1)),
                "filas": tabla1,
            },
            "tabla_2_control_v2_vs_tipo_final": {
                "esperado": {"acuerdos": ESPERADO_ACUERDOS_FINAL, "sobre": 40},
                "acuerdos": acuerdos,
                "sobre": 40,
                "ordenes_sin_acuerdo": [f["orden"] for f in tabla2 if not f["acuerdo"]],
                "cumple_esperado": cumple2,
                "distribucion_tipo_final": dict(Counter(f["tipo_final"] for f in tabla2)),
                "filas": tabla2,
            },
            "diferencias_fuera_de_lo_esperado": fuera,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        comp = out_dir / NOMBRE_COMPARACION
        comp.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("comparación escrita en:", rel(comp))
        print("insumos:", json.dumps(salida["insumos"], indent=1))
        print("\n[Tabla 1] control v2 vs control v1")
        print("  distribución v1:", salida["tabla_1_control_v2_vs_control_v1"]["distribucion_v1"])
        print("  distribución v2:", salida["tabla_1_control_v2_vs_control_v1"]["distribucion_v2"])
        print("  cambios:", len(cambios), "| órdenes:", [f["orden"] for f in cambios])
        for f in cambios:
            print(f"    orden {f['orden']:>2} {f['id']}: {f['tipo_v1']!r} -> {f['tipo_v2']!r}")
        print("  esperado: 2 cambios, órdenes [20, 30], 'varios puntos' -> 'dato directo' | cumple:", cumple1)
        print("\n[Tabla 2] control v2 vs tipo final")
        print("  acuerdos:", acuerdos, "/ 40 | órdenes sin acuerdo:", [f["orden"] for f in tabla2 if not f["acuerdo"]])
        print("  esperado: 40 acuerdos | cumple:", cumple2)
        print("\n[Diferencias fuera de lo esperado]:", len(fuera))
        for f in fuera:
            print(f"  orden {f['orden']:>2} {f['id']}: v1={f['tipo_v1']!r} v2={f['tipo_v2']!r} final={f['tipo_final']!r} | {'; '.join(f['motivo'])}")
            print(f"    nota del modelo (v2): {f['nota_modelo_v2']}")
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
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / NOMBRE_COUNT).write_text(json.dumps({
            "modelo": MODELO, "regla": rel(regla_path), "sha256_regla": sr, "sha256_hoja": sh,
            "total_input_tokens": tot, "por_fila": por_fila,
            "precios_usd_por_millon": {"entrada": PRECIO_IN, "salida": PRECIO_OUT},
            "max_tokens": MAX_TOKENS,
            "cota_usd_40_llamadas": {"entrada": round(cin, 6), "salida_peor_caso": round(cout, 6), "total": round(cin + cout, 6)},
            "cota_usd_80_llamadas_peor_caso": round(2 * (cin + cout), 6),
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
        code_ver = f"control-tipo-ev2-v2+regla={sr[:12]}"
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
        salida = {
            "modelo": MODELO,
            "modelo_segun_api": sorted(modelos_api.keys()),
            "temperatura": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "thinking": False,
            "regla": rel(regla_path),
            "sha256_regla": sr,
            "sha256_hoja": sh,
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
            "captura": {"db": rel(db_path), "domain": DOMAIN, "code_ver": code_ver, "run_label": RUN_LABEL,
                        "namespace": client.namespace},
            "entradas": entradas,
        }
        OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stats = client.stats()
        client.close()
        # Solo estadísticas: nada de tipo/nota (el desglose sale por --comparar).
        print("control escrito en:", rel(OUT))
        print("entradas escritas:", len(entradas))
        print("sin_respuesta:", n_sin, "| reintentos:", n_reint, "| órdenes reintentados:", ordenes_reintentados)
        print("modelo según API:", dict(modelos_api))
        print("stop_reason:", dict(stops))
        print(f"tokens entrada={tok_in} salida={tok_out}")
        print(f"costo calculado (USD {PRECIO_IN}/{PRECIO_OUT} por M): USD {gasto:.4f} (tope USD {a.tope_usd})")
        print("stats caché:", stats)


if __name__ == "__main__":
    main()
