"""
analisis_gold_juez_v.py — U-TRIP-V-JUEZ v1.1: el acuerdo del juez con el gold de la autora (§4.6 del pre-registro de
tripletas), con la sensibilidad del piloto fijada antes de cualquier cifra (nota al pie del 20/10/2026; registro de
decisiones, §60): las cifras con las 100 y, aparte, sin las 10 del piloto (las de `sorteo.lotes.piloto` del acta, por
código). Si las dos dan otra decisión del §4.6, se declara y rige la de las 100.

Lo corre la autora cuando terminó el gold y la corrida --gold. Lee:
  - el agregado del juez (corridas/NO_ABRIR_agregado_gold_V.json);
  - las 10 hojas del gold de la autora (hoja_piloto.csv y hoja_lote_01…09.csv), cada una con su sello, desde la
    carpeta que se le pase; controla que sus filas sean las del lote del acta. No imprime ninguna nota;
  - el acta (los lotes, el orden y los pesos W_h de los estratos) y las fichas, de la copia del repo o del repo.

El §4.6, sobre las fichas que el juez decide (las que manda a adjudicación o quedan sin consenso se cuentan aparte):
  (i)   acuerdo en «correcta» (dos clases: la incorrecta por las dos vías del §4.2) en al menos 84 de 100; con otro
        número de decididas, la misma proporción (0,84), con el límite inferior de Wilson al lado (z = 1,959964);
  (ii)  la precisión según el juez y según la autora difieren en 0,05 o menos, cruda y ponderada, las dos sobre las
        mismas fichas: las que deciden los dos. La ponderada (p̂_w = Σ W_h p̂_h) va estrato por estrato sobre esas mismas
        fichas, con los estratos que tienen alguna; «otros» sin muestra suma lo mismo a los dos y no cambia la diferencia;
        v1.4d: las dos diferencias se redondean a 10 decimales y 0,05 exacto pasa (registro de decisiones, §84);
  (iii) de las que la autora marca incorrectas entre las que el juez decide, el juez marca incorrecta al menos la mitad
        (fracción cruda). Al lado, como información, la misma fracción sobre todas las que la autora marca incorrectas.
Las tres lecturas, sobre las fichas que el juez decide, como dice el texto firmado (decisión sobre el FRENO v1.2).
v1.4c: la importancia entra en la decisión (registro de decisiones, §81 y §83). El «pasa» del §4.6 (decision_46) pide
las tres lecturas y, a la vez, el acuerdo de importancia del texto firmado: «exacto en al menos 60 de 100 y a un nivel
de distancia en al menos 90 de 100», en proporción (0,60 y 0,90) sobre los pares con una importancia válida del juez;
sin ningún par, no pasa. La comparación de las 100 con las 90 sin el piloto sale de decision_46, así que la incluye.
Al lado: el kappa de Cohen de «correcta»; los kappa de la importancia de tres valores y lineal; cuántas van a
adjudicación (más de 15 de 100: el instrumento se declara con esa frontera); y las incorrectas del juez por vía. El
veredicto del juez es el modal de juez_v.agregar_veredicto: las dos vías de la incorrecta votan juntas, y la vía del
modal (contradicho, no_consta o mixta, que se cuenta aparte) va al lado.

v1.4b: las dos versiones del juez escriben el mismo agregado (corridas/NO_ABRIR_agregado_gold_V.json). Antes de analizar,
el análisis lee la regla del gold (corridas/recalibracion_v1_4/regla_del_gold.json, --regla) y frena si falta, o si el
agregado no es el de la versión que manda:
  - la version_prompt y el code_ver_base del agregado, y el prompt_sha256 de cada ficha, tienen que ser los de esa versión
    (v1_4: el prompt v1.4 y juez-tripletas-v1_4; v1_3: el prompt v1.1 y juez-tripletas-v1_1), tomados de las constantes
    de prompt_juez_v.py y juez_v.py, que se controlan contra lo decidido;
  - corridas/resumen_gold_V.json (--resumen) tiene que decir la misma version_prompt y el mismo prompt_sha256, y nombrar
    el agregado que se lee.
La salida suma la versión al gold, la version_prompt, el code_ver_base y el sha256 del agregado, del resumen y de la regla.

  .venv/bin/python -B analisis_gold_juez_v.py --hojas-gold <carpeta> [--agregado …] [--resumen …] [--regla …] [--repo …]
                                                [--salida …]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import juez_v as J  # noqa: E402
import prompt_juez_v as PJ  # noqa: E402
import regla_del_gold_v as RG  # noqa: E402

AGREGADO_DEFECTO = PJ.RAIZ / "corridas" / "NO_ABRIR_agregado_gold_V.json"
RESUMEN_DEFECTO = PJ.RAIZ / "corridas" / "resumen_gold_V.json"
SALIDA_DEFECTO = PJ.RAIZ / "corridas" / "analisis_gold_V.json"
# Lo decidido para el agregado de cada versión (version_prompt, code_ver_base, prompt del gold): solo para controlar las
# constantes del código, que son las que se usan.
DECIDIDO = {"v1_4": ("v1_4", "juez-tripletas-v1_4", "8f275224c3db92166eb2f9fc963eb5509b73f0fcd2b3bf6dba539a8f85e513d0"),
            "v1_3": ("v1_1", "juez-tripletas-v1_1", "4cf2e5372124fba652523efc1e86f5fe180b0eafd9628d435a22f66832615d9b")}
COLUMNAS_GOLD = ("orden", "ref", "predicado", "clave", "correcta", "importancia", "nota", "observacion_umbral")
CORRECTA = {"si": "correcta", "no": "incorrecta", "no decidible": None}
IMPORTANCIA = {"esencial": "esencial", "util": "util", "accesoria": "accesoria"}
NIVEL = {"accesoria": 0, "util": 1, "esencial": 2}
Z = 1.959964
UMBRAL_ACUERDO, UMBRAL_DIF, UMBRAL_INCORRECTAS = 0.84, 0.05, 0.5
UMBRAL_IMP_EXACTO, UMBRAL_IMP_NIVEL, UMBRAL_ADJUDICACION = 0.60, 0.90, 0.15


def wilson_inferior(k: int, n: int) -> float | None:
    if n == 0:
        return None
    p = k / n
    c = Z * Z / n
    return (p + c / 2 - Z * math.sqrt(p * (1 - p) / n + c / (4 * n))) / (1 + c)


def kappa(pares: list[tuple], categorias: list, pesos=None) -> float | None:
    """Cohen (pesos=None) o ponderado (pesos[i][j] = desacuerdo entre las categorías i y j)."""
    n = len(pares)
    if n == 0:
        return None
    idx = {c: i for i, c in enumerate(categorias)}
    k = len(categorias)
    w = pesos or [[0 if i == j else 1 for j in range(k)] for i in range(k)]
    obs = [[0] * k for _ in range(k)]
    for a, b in pares:
        obs[idx[a]][idx[b]] += 1
    fa = [sum(obs[i]) / n for i in range(k)]
    fb = [sum(obs[i][j] for i in range(k)) / n for j in range(k)]
    do = sum(w[i][j] * obs[i][j] / n for i in range(k) for j in range(k))
    de = sum(w[i][j] * fa[i] * fb[j] for i in range(k) for j in range(k))
    return None if de == 0 else 1 - do / de


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def esperado_de(version: str) -> dict:
    """La version_prompt, el code_ver_base y el prompt del gold de una versión, de las constantes de prompt_juez_v.py y
    juez_v.py; frena si no dan lo decidido."""
    if version not in RG.VERSIONES:
        raise SystemExit(f"FRENO: la versión {version!r} no es v1_3 ni v1_4")
    e = ({"version_prompt": PJ.PROMPT_VERSION_V1_4, "code_ver_base": J.CODE_VER_BASE_V1_4,
          "prompt_sha256": PJ.PROMPT_V1_4_SHA256} if version == "v1_4" else
         {"version_prompt": PJ.PROMPT_VERSION, "code_ver_base": J.CODE_VER_BASE, "prompt_sha256": PJ.PROMPT_V1_1_SHA256})
    if (e["version_prompt"], e["code_ver_base"], e["prompt_sha256"]) != DECIDIDO[version]:
        raise SystemExit(f"FRENO: las constantes del código para {version} no dan lo decidido")
    return e


def leer_regla(ruta: Path) -> tuple[str, str]:
    """(versión al gold, sha256) de regla_del_gold.json; frena si falta o si no manda v1_3 ni v1_4."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise SystemExit(f"FRENO: falta {ruta.name}: la escribe el análisis de la recalibración")
    b = ruta.read_bytes()
    version = json.loads(b).get("version_al_gold")
    if version not in RG.VERSIONES:
        raise SystemExit(f"FRENO: {ruta.name} manda {version!r}, no v1_3 ni v1_4")
    return version, sha256(b)


def controlar_version(version: str, agregado: dict, resumen: dict, nombre_agregado: str) -> dict:
    """Frena si el agregado o el resumen del gold no son de la versión que manda la regla. Devuelve lo esperado."""
    e = esperado_de(version)
    for campo in ("version_prompt", "code_ver_base"):
        if agregado.get(campo) != e[campo]:
            raise SystemExit(f"FRENO: el agregado trae {campo} {agregado.get(campo)!r}, y la regla manda {version} "
                             f"({e[campo]})")
    otras = [x["ref"] for x in agregado["fichas"] if x.get("prompt_sha256") != e["prompt_sha256"]]
    if otras:
        raise SystemExit(f"FRENO: {len(otras)} fichas del agregado no traen el prompt del gold de {version} "
                         f"({e['prompt_sha256'][:12]}…), por ejemplo {otras[:3]}")
    if resumen.get("version_prompt") != e["version_prompt"] or resumen.get("prompt_sha256") != e["prompt_sha256"]:
        raise SystemExit(f"FRENO: el resumen del gold no dice la version_prompt y el prompt de {version}")
    if resumen.get("agregado") != nombre_agregado:
        raise SystemExit(f"FRENO: el resumen del gold nombra el agregado {resumen.get('agregado')!r}, no "
                         f"{nombre_agregado}")
    return e


def leer_hojas_gold(carpeta: Path, acta: dict) -> dict[str, dict]:
    """ref -> {correcta, importancia} de las 10 hojas selladas. Controla el sello, la cabecera y las filas del lote."""
    s_acta = PJ.ACTA_SHA256
    refs = {k: f"V{i + 1:03d}" for i, k in enumerate(acta["sorteo"]["orden"])}
    pred = {f[0]: f[1] for f in acta["poblacion"]["filas"]}
    out = {}
    for lote, claves in acta["sorteo"]["lotes"].items():
        hoja = Path(carpeta) / f"hoja_{lote}.csv"
        datos = hoja.read_bytes()
        sello = hoja.parent / f"sello_hoja_{lote}.txt"
        if not sello.exists() or sello.read_text(encoding="utf-8").split()[:2] != [hashlib.sha256(datos).hexdigest(),
                                                                                    hoja.name]:
            raise SystemExit(f"FRENO: {hoja.name} no da el sha256 de su sello")
        texto = datos.decode("utf-8-sig")
        primera = texto.splitlines()[0] if texto else ""
        delim = ";" if primera.count(";") > primera.count(",") else ","
        filas = [[c.strip() for c in f] for f in csv.reader(io.StringIO(texto), delimiter=delim)]
        filas = [f for f in filas if any(f)]
        cab = {f[0]: (f[1] if len(f) > 1 else "") for f in filas[:4]}
        if cab.get("hoja") != lote or cab.get("acta_sorteo_V.json_sha256") != s_acta:
            raise SystemExit(f"FRENO: la cabecera de {hoja.name} no es la de su lote del acta")
        if tuple(filas[4][:len(COLUMNAS_GOLD)]) != COLUMNAS_GOLD:
            raise SystemExit(f"FRENO: el encabezado de {hoja.name} no es el del gold")
        cuerpo = [dict(zip(COLUMNAS_GOLD, f + [""] * (len(COLUMNAS_GOLD) - len(f)))) for f in filas[5:]]
        esperado = [(str(i), refs[k], pred[k], k) for i, k in enumerate(claves, 1)]
        if [(r["orden"], r["ref"], r["predicado"], r["clave"]) for r in cuerpo] != esperado:
            raise SystemExit(f"FRENO: las filas de {hoja.name} no son las de su lote del acta")
        for r in cuerpo:
            c, imp = PJ.plegar(r["correcta"]), PJ.plegar(r["importancia"])
            if c not in CORRECTA or imp not in IMPORTANCIA:
                raise SystemExit(f"FRENO: la fila {r['orden']} de {hoja.name} tiene un valor no permitido")
            out[r["ref"]] = {"correcta": CORRECTA[c], "importancia": IMPORTANCIA[imp], "lote": lote}
    if len(out) != 100:
        raise SystemExit(f"FRENO: las hojas del gold traen {len(out)} fichas, no 100")
    return out


def criterios(pares: list[dict], w_estrato: dict[str, float]) -> dict:
    """El §4.6 sobre una lista de pares {ref, predicado, juez_veredicto, juez_via, juez_importancia, autora_correcta,
    autora_importancia}."""
    n_total = len(pares)
    juez = [J.dos_clases(p["juez_veredicto"]) for p in pares]
    autora = [p["autora_correcta"] for p in pares]
    ambos = [(j, a) for j, a in zip(juez, autora) if j is not None and a is not None]
    n, acu = len(ambos), sum(j == a for j, a in ambos)
    adjud = sum(j is None for j in juez)

    def prec(pares_dec: list, lado: int):
        """La precisión de un lado (0: juez, 1: autora) sobre pares que deciden los dos."""
        return (sum(x[lado] == "correcta" for x in pares_dec) / len(pares_dec)) if pares_dec else None

    pj, pa = prec(ambos, 0), prec(ambos, 1)
    por_estrato, sin_dec = {}, []
    for h in sorted({p["predicado"] for p in pares}):
        amb_h = [(j, a) for j, a, p in zip(juez, autora, pares)
                 if p["predicado"] == h and j is not None and a is not None]
        if not amb_h:
            sin_dec.append(h)
            continue
        por_estrato[h] = (prec(amb_h, 0), prec(amb_h, 1))
    pwj = sum(w_estrato[h] * v[0] for h, v in por_estrato.items())
    pwa = sum(w_estrato[h] * v[1] for h, v in por_estrato.items())
    inc_a = [(j, a) for j, a in zip(juez, autora) if a == "incorrecta" and j is not None]
    k_inc = sum(j == "incorrecta" for j, _ in inc_a)
    inc_todas = [(j, a) for j, a in zip(juez, autora) if a == "incorrecta"]
    k_inc_todas = sum(j == "incorrecta" for j, _ in inc_todas)
    imp = [(p["juez_importancia"], p["autora_importancia"]) for p in pares if p["juez_importancia"] in NIVEL]
    exacto = sum(a == b for a, b in imp)
    a_un_nivel = sum(abs(NIVEL[a] - NIVEL[b]) <= 1 for a, b in imp)
    cat = ["accesoria", "util", "esencial"]
    lineal = [[abs(i - j) / 2 for j in range(3)] for i in range(3)]
    c_i = n > 0 and acu / n >= UMBRAL_ACUERDO
    c_ii_c = pj is not None and pa is not None and round(abs(pj - pa), 10) <= UMBRAL_DIF
    c_ii_w = round(abs(pwj - pwa), 10) <= UMBRAL_DIF
    c_iii = (k_inc / len(inc_a) >= UMBRAL_INCORRECTAS) if inc_a else None
    c_imp_exacto = bool(imp) and exacto / len(imp) >= UMBRAL_IMP_EXACTO
    c_imp_nivel = bool(imp) and a_un_nivel / len(imp) >= UMBRAL_IMP_NIVEL
    vias = Counter(p["juez_via"] for p in pares if p["juez_via"])
    return {
        "fichas": n_total, "juez_no_decide": adjud, "proporcion_a_adjudicacion": round(adjud / n_total, 4),
        "frontera_declarada": adjud > UMBRAL_ADJUDICACION * n_total,
        "i_acuerdo": {"acuerdo": acu, "decididas_por_los_dos": n, "proporcion": round(acu / n, 4) if n else None,
                      "wilson_inferior": round(wilson_inferior(acu, n), 4) if n else None, "pasa": c_i},
        "ii_precision": {"sobre": "las que deciden los dos", "fichas": n,
                         "cruda": {"juez": pj, "autora": pa, "diferencia": None if pj is None or pa is None
                                   else round(abs(pj - pa), 4), "pasa": c_ii_c},
                         "ponderada": {"juez": round(pwj, 4), "autora": round(pwa, 4),
                                       "diferencia": round(abs(pwj - pwa), 4), "pasa": c_ii_w,
                                       "estratos_sin_fichas_que_decidan_los_dos": sin_dec}},
        "iii_incorrectas": {"sobre": "las que la autora marca incorrectas entre las que el juez decide",
                            "autora_incorrectas": len(inc_a), "juez_incorrecta_entre_ellas": k_inc,
                            "fraccion": f"{k_inc} de {len(inc_a)}", "pasa": c_iii,
                            "informativo_sobre_todas_las_incorrectas_de_la_autora": {
                                "autora_incorrectas": len(inc_todas), "juez_incorrecta_entre_ellas": k_inc_todas,
                                "fraccion": f"{k_inc_todas} de {len(inc_todas)}",
                                "llegaria_a_la_mitad": (k_inc_todas / len(inc_todas) >= UMBRAL_INCORRECTAS)
                                if inc_todas else None}},
        "kappa_correcta": kappa(ambos, ["correcta", "incorrecta"]),
        "importancia": {"pares": len(imp), "exacto": exacto, "a_un_nivel": a_un_nivel,
                        "pasa_exacto": c_imp_exacto, "pasa_a_un_nivel": c_imp_nivel,
                        "kappa": kappa(imp, cat), "kappa_lineal": kappa(imp, cat, lineal)},
        "incorrectas_del_juez_por_via": dict(vias),
        "decision_46": bool(c_i and c_ii_c and c_ii_w and c_iii and c_imp_exacto and c_imp_nivel)}


def analizar(agregado: dict, gold: dict, acta: dict, fichas: list[dict]) -> dict:
    if agregado.get("modo") != "gold" or agregado["verificacion_cross_hits"]["cross_hits"] != 0:
        raise SystemExit("FRENO: el agregado no es el del gold o tiene cruces")
    pred = {f["ref"]: f["predicado"] for f in fichas if f["lote"] != "pool"}
    w = {}
    for h, e in acta["asignacion"]["estratos"].items():
        for p in e["predicados"]:
            w[p] = e["W_h"]
    refs = {k: f"V{i + 1:03d}" for i, k in enumerate(acta["sorteo"]["orden"])}
    piloto = sorted(refs[k] for k in acta["sorteo"]["lotes"]["piloto"])
    juez = {x["ref"]: x["agregado"] for x in agregado["fichas"]}
    if set(juez) != set(gold) or len(juez) != 100:
        raise SystemExit("FRENO: el agregado y el gold no traen las mismas 100 fichas")
    pares = [{"ref": r, "predicado": pred[r], "juez_veredicto": juez[r]["veredicto"]["modal"],
              "juez_via": juez[r]["veredicto"]["via"],
              "juez_importancia": juez[r]["importancia"]["modal"], "autora_correcta": gold[r]["correcta"],
              "autora_importancia": gold[r]["importancia"]} for r in sorted(gold)]
    con_100 = criterios(pares, w)
    sin_piloto = criterios([p for p in pares if p["ref"] not in piloto], w)
    return {"rige": "las 100", "piloto_por_codigo": piloto, "con_las_100": con_100, "sin_las_10_del_piloto": sin_piloto,
            "misma_decision": con_100["decision_46"] == sin_piloto["decision_46"],
            "declaracion": None if con_100["decision_46"] == sin_piloto["decision_46"] else
            "Las dos cifras dan otra decisión del §4.6: se declara, y rige la de las 100."}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hojas-gold", type=Path, required=True)
    ap.add_argument("--agregado", type=Path, default=AGREGADO_DEFECTO)
    ap.add_argument("--resumen", type=Path, default=RESUMEN_DEFECTO)
    ap.add_argument("--regla", type=Path, default=RG.REGLA_DEFECTO)
    ap.add_argument("--repo", type=Path, default=PJ.REPO_DEFECTO)
    ap.add_argument("--salida", type=Path, default=SALIDA_DEFECTO)
    a = ap.parse_args()
    version, sha_regla = leer_regla(a.regla)
    if not a.resumen.exists():
        raise SystemExit(f"FRENO: falta {a.resumen.name}")
    agregado_b, resumen_b = a.agregado.read_bytes(), a.resumen.read_bytes()
    agregado = json.loads(agregado_b)
    e = controlar_version(version, agregado, json.loads(resumen_b), a.agregado.name)
    acta_b = (a.repo / PJ.ACTA_REL).read_bytes()
    if hashlib.sha256(acta_b).hexdigest() != PJ.ACTA_SHA256:
        raise SystemExit("FRENO: el acta no es la sellada")
    acta = json.loads(acta_b)
    fichas = PJ.cargar_fichas(a.repo / PJ.FICHAS_REL)
    out = {"version_al_gold": version, "version_prompt": e["version_prompt"], "code_ver_base": e["code_ver_base"],
           "agregado_sha256": sha256(agregado_b), "resumen_sha256": sha256(resumen_b), "regla_sha256": sha_regla,
           **analizar(agregado, leer_hojas_gold(a.hojas_gold, acta), acta, fichas)}
    a.salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"versión al gold: {version} ({a.regla.name}, sha256 {sha_regla})")
    print(f"agregado {a.agregado.name}: version_prompt {e['version_prompt']} | code_ver_base {e['code_ver_base']} | "
          f"prompt del gold {e['prompt_sha256'][:12]}… en sus {len(agregado['fichas'])} fichas | sha256 "
          f"{out['agregado_sha256']}")
    print(f"resumen {a.resumen.name}: la misma version_prompt y el mismo prompt, nombra {a.agregado.name} | sha256 "
          f"{out['resumen_sha256']}")
    for nombre in ("con_las_100", "sin_las_10_del_piloto"):
        c = out[nombre]
        print(f"[{nombre}] decisión del §4.6: {'pasa' if c['decision_46'] else 'no pasa'} | (i) {c['i_acuerdo']['acuerdo']} "
              f"de {c['i_acuerdo']['decididas_por_los_dos']} | (ii) cruda {c['ii_precision']['cruda']['diferencia']} "
              f"ponderada {c['ii_precision']['ponderada']['diferencia']} | (iii) {c['iii_incorrectas']['fraccion']} | "
              f"a adjudicación {c['juez_no_decide']} | incorrectas por vía {c['incorrectas_del_juez_por_via']} | "
              f"importancia: exacto {c['importancia']['exacto']} de {c['importancia']['pares']}, a un nivel "
              f"{c['importancia']['a_un_nivel']} de {c['importancia']['pares']}")
    print(out["declaracion"] or "Las dos cifras dan la misma decisión del §4.6.")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
