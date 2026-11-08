"""
analisis_400_v3.py — el análisis de las 400 fichas de T con la v3 del juez de tripletas (etapa d, USD 0; lo corre la autora
después de la corrida paga de las 200). No llama a la API. La v3 no pasó la (ii) de la validación y se usa igual, como
desvío declarado: la nota fechada al pie del pre-registro de tripletas, decisiones 3, 5 y 6. Rigen, además, el §3.6, la
enmienda 3 (el intervalo) y los puntos 10 y 11 de la enmienda 5.

Qué calcula:
  1. la cifra principal (opción B): las 200 fichas que la autora leyó (calibración más validación) van con su marca de
     «correcta», de sus hojas selladas; las otras 200, con el veredicto modal de la v3, que en la validación no entra, salvo
     las que la v3 no decide: esas van con el veredicto que les dio la autora en su hoja de adjudicación. Con los
     estimadores de la v2 (estimadores de analisis_T_v2.py, importado sin editarlo): la cruda con Wilson y la ponderada
     por estrato con Wilson y el n efectivo de Kish (wilson_kish_tripletas_mesa.py del repo, con su sha256), con y sin la
     tanda 0, y por grupo. La v3 no juzga la importancia: en las 200 la importancia va vacía, y las esenciales de esta
     cifra son solo las de la autora;
  2. al lado: la misma cifra con la lectura de la autora sola, en sus 200 de calibración y validación (las adjudicadas no
     entran ahí); y la de las 400 sin la ficha de T que lleva la
     arista de V097 (la de la misma clave en fichas_V.jsonl de HEAD), que es un caso del prompt;
  3. la nota del desvío, al lado de cada cifra en la que entra la v3: el umbral de (ii) que no se cumplió, la diferencia
     medida entre la precisión de la v3 y la de la autora en la validación, con su signo (v3 menos autora), cruda y
     ponderada, y la precisión de la autora sobre esas mismas fichas, «k de n». Todo se lee del análisis de la validación
     (analisis_validacion_v3.json, con su sha256 contra el agregado y las hojas que leyó) y se recalcula de los pares;
  4. la sensibilidad (decisión 6), marcada como tal y fuera de la cifra principal: la corrección por doble muestreo. De
     los pares de la validación que deciden la v3 y la autora salen π₁ (la autora dice «correcta» cuando la v3 dice
     «correcta») y π₀ (la autora dice «correcta» cuando la v3 dice «incorrecta»), juntas, no por estrato. La corrección
     toca solo las fichas que decidió la v3: las adjudicadas cuentan como lectura de la autora. En esas fichas de la v3, q
     es la fracción que marca correcta, cruda y ponderada como la cifra principal (W_h = N_h / N, renormalizados sobre los
     estratos con fichas). La cifra corregida es π₁·q + π₀·(1 − q); al lado, la de las 400 con esa parte corregida (en
     cada estrato, las fichas de la v3 entran con su fracción corregida). El intervalo es de bootstrap, REPLICAS réplicas
     con la semilla SEMILLA y los percentiles 2,5 y 97,5. Cada réplica sortea, por un lado, los pares de la validación, y
     por otro, dentro de cada estrato, tantas fichas de las 400 como el estrato tiene, con reposición; cada ficha arrastra
     de dónde sale su marca (la autora, una adjudicación o la v3), así que también varía la parte de la autora. Una réplica
     que deja sin «correcta» o sin «incorrecta» de la v3 a los pares, o sin ninguna ficha de la v3, no define la cifra y se
     cuenta aparte. La cifra principal lleva el intervalo analítico (Wilson con el n efectivo de Kish); la sensibilidad, este.
Las adjudicaciones (punto 10): las fichas de las 200 que la v3 manda a adjudicación (o deja sin consenso) las decide la
autora, en una hoja que arma la mesa después de la corrida (adjudicacion_200.csv: UTF-8, encabezado `ref,veredicto` y un
renglón por ref, con correcta o incorrecta), leída solo después de su sello (--sello-adjudicacion-200, con su sha256): el
sello da su sha256, cada renglón da el de su archivo (la ruta, relativa a la carpeta del sello) y uno solo nombra la hoja.
Sus refs tienen que ser exactamente las que la v3 no decidió. Si hay pendientes y no viene el sello, frena sin escribir y
da solo cuántas son y sus refs (rc 2); si viene y no hay pendientes, frena porque sobra. Si las 200 no se completaron,
frena sin escribir.

Lo que reusa, importándolo sin editarlo: de analisis_T_v2.py, validar_entrada, estimadores, ponderada, _fila y
a_adjudicacion (medicion_400 no sirve: pone el juez en todas las fichas que decide, también en las de la autora); de
analisis_validacion_v3.py, cargar_at2, del_acta y leer_agregado; de correr_validacion_v3.py, leer_acta y
controlar_sello_lectura; de armar_200_v3.py, las 200 y su entrada sellada; de casos_v3.py, leer_hojas_T.
Antes de leer una hoja de la autora: el sello conjunto de cada lectura (calibración y validación), con su sha256 y el de
cada hoja y cada sello que nombra. La entrada de la mesa (el JSON de las 400 con sus estratos que validó la v2), con su
sha256. Escribe v3/corridas/analisis_400/analisis_400_v3.json (no pisa uno existente); la consola no da ninguna cifra.

  .venv/bin/python -B analisis_400_v3.py --entrada E [--entrada-sha256 S] [--corridas C] [--tt D] [--tt3 D] [--salida D]
      [--sello-adjudicacion-200 S --sello-adjudicacion-200-sha256 X] ...
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analisis_validacion_v3 as AV  # noqa: E402
import armar_200_v3 as A2  # noqa: E402
import casos_v3 as CV  # noqa: E402
import congelar_v3 as CG  # noqa: E402
import correr_200_v3 as C200  # noqa: E402
import correr_validacion_v3 as CVAL  # noqa: E402
import juez_v3 as J  # noqa: E402
from v1_importada import AG, PJ  # noqa: E402

CODE_VER = "analisis-400-v3.2"   # .2: las adjudicaciones de la autora y el bootstrap por estrato
ENTRADA_SHA256 = "d764a18b245609e3f1b047c1f49e4109a20c20c09915f03c0840873a34596e44"   # la del análisis de T de la v2
SALIDA_DIR, SALIDA_NOMBRE = "analisis_400", "analisis_400_v3.json"
SEMILLA = 20261030
REPLICAS = 10000
PERCENTILES = (2.5, 97.5)
REF_V097 = "V097"
CODE_VER_VALIDACION = "analisis-validacion-v3."
MARCA_SENSIBILIDAD = "análisis de sensibilidad (decisión 6): no es la cifra principal"
HOJA_ADJUDICACION = "adjudicacion_200.csv"
ENCABEZADO_ADJUDICACION = ["ref", "veredicto"]
VEREDICTOS_ADJUDICACION = ("correcta", "incorrecta")
FUENTES = ("autora", "adjudicada", "v3")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------- #
# Las entradas                                                                #
# --------------------------------------------------------------------------- #
def leer_agregado_200(d: dict, refs: set[str], prompt_sha: str) -> dict[str, dict]:
    """ref -> {veredicto, via} del agregado de las 200: AV.leer_agregado con el modo de las 200 en lugar del de la
    validación (los mismos controles: 0 cruces, el modelo, el esfuerzo, el prompt congelado en el agregado y en cada ficha)."""
    if not isinstance(d, dict) or d.get("modo") != C200.MODO:
        raise SystemExit(f"FRENO: el agregado de las 200 no es del modo {C200.MODO}")
    return AV.leer_agregado({**d, "modo": CVAL.MODO}, refs, prompt_sha)


def corrida_completa(d: Path, nombre: str) -> tuple[Path, Path]:
    """El agregado y el resumen de una corrida completa (su resumen la da completada y nombra su agregado)."""
    ag, res = Path(d) / "NO_ABRIR_agregado.json", Path(d) / "resumen.json"
    r = json.loads(res.read_text(encoding="utf-8")) if res.exists() else {}
    if not (r.get("corrida") or {}).get("completada") or r.get("agregado") != ag.name:
        raise SystemExit(f"FRENO: {nombre} no se completó o su resumen no nombra su agregado")
    return ag, res


def refs_de_V097(repo: Path, fichas_T: dict) -> list[str]:
    """Las refs de T cuya clave es la de V097 en fichas_V.jsonl de HEAD."""
    v = [json.loads(l) for l in CV.git_show(repo, f"HEAD:{CV.FICHAS_V_REL}").decode("utf-8").splitlines() if l.strip()]
    clave = [f["clave"] for f in v if f["ref"] == REF_V097]
    if len(clave) != 1:
        raise SystemExit(f"FRENO: fichas_V.jsonl de HEAD no trae una sola {REF_V097}")
    return sorted(r for r, f in fichas_T.items() if f["clave"] == clave[0])


def leer_adjudicacion(sello: Path, sello_sha: str, pendientes: list[str]) -> dict:
    """La hoja de adjudicación de la autora sobre las 200, después de su sello: ref -> correcta | incorrecta, con exactamente
    las refs que la v3 no decidió."""
    sello = Path(sello)
    if not sello.is_file() or sha(sello.read_bytes()) != sello_sha:
        raise SystemExit("FRENO: el sello de la adjudicación de las 200 no da su sha256")
    hojas = []
    for l in sello.read_text(encoding="utf-8").splitlines():
        if not l.strip() or l.startswith("#"):
            continue
        m = re.fullmatch(r"([0-9a-f]{64})  (\S.*)", l)
        rel = Path(m.group(2)) if m else None
        if not m or rel.is_absolute() or ".." in rel.parts or not (sello.parent / rel).is_file() \
                or sha((sello.parent / rel).read_bytes()) != m.group(1):
            raise SystemExit("FRENO: un renglón del sello de la adjudicación no da el sha256 de su archivo")
        if rel.name == HOJA_ADJUDICACION:
            hojas.append(sello.parent / rel)
    if len(hojas) != 1:
        raise SystemExit(f"FRENO: el sello de la adjudicación no nombra una sola {HOJA_ADJUDICACION}")
    b = hojas[0].read_bytes()
    try:
        filas = list(csv.reader(io.StringIO(b.decode("utf-8"), newline="")))
    except UnicodeDecodeError:
        raise SystemExit(f"FRENO: {HOJA_ADJUDICACION} no está en UTF-8")
    if not filas or filas[0] != ENCABEZADO_ADJUDICACION:
        raise SystemExit(f"FRENO: el encabezado de {HOJA_ADJUDICACION} no es «ref,veredicto»")
    out = {}
    for f in filas[1:]:
        if len(f) != 2 or f[1] not in VEREDICTOS_ADJUDICACION or f[0] in out:
            raise SystemExit(f"FRENO: un renglón de {HOJA_ADJUDICACION} no es «ref,correcta|incorrecta», o repite su ref")
        out[f[0]] = f[1]
    if set(out) != set(pendientes):
        raise SystemExit(f"FRENO: las refs de {HOJA_ADJUDICACION} no son exactamente las que la v3 manda a adjudicación")
    return {"veredictos": out, "sello_sha256": sello_sha, "hoja_sha256": sha(b), "adjudicadas": len(out)}


def nota_del_desvio(an_val: dict, pares: list[tuple[str, str]]) -> dict:
    """La nota de la decisión 3, con las cifras del análisis de la validación, recalculadas de los pares (v3, autora)."""
    if not str(an_val.get("code_ver", "")).startswith(CODE_VER_VALIDACION) or an_val.get("pasa") is not False:
        raise SystemExit("FRENO: el análisis de la validación no es el de la v3 o no da que no pasa")
    cond = an_val["condiciones"]
    if cond["ii_cruda"] and cond["ii_ponderada"]:
        raise SystemExit("FRENO: el análisis de la validación no da que la (ii) no pasa")
    ii = an_val["criterios"]["ii_precision"]
    n = ii["fichas"]
    k_a = round(ii["cruda"]["autora"] * n)
    k_j = round(ii["cruda"]["juez"] * n)
    if len(pares) != n or sum(a == "correcta" for _, a in pares) != k_a or sum(j == "correcta" for j, _ in pares) != k_j:
        raise SystemExit("FRENO: los pares de la validación no dan las cifras de su análisis")
    return {"desvio": "la v3 no pasó la (ii) de la validación y se usa igual (nota al pie del pre-registro, decisión 3)",
            "exigia": {"condicion": "(ii) la precisión de la v3 y la de la autora, sobre las fichas que deciden las dos, "
                                    "a 0,05 o menos, en la cruda y en la ponderada", "umbral": AG.UMBRAL_DIF},
            "no_paso": [k for k in ("ii_cruda", "ii_ponderada") if not cond[k]],
            "diferencia_v3_menos_autora": {"cruda": round(ii["cruda"]["juez"] - ii["cruda"]["autora"], 4),
                                           "ponderada": round(ii["ponderada"]["juez"] - ii["ponderada"]["autora"], 4)},
            "precision_de_la_autora_en_la_validacion": {"k": k_a, "n": n, "fraccion": f"{k_a} de {n}"},
            "fuente": "analisis_validacion_v3.json"}


# --------------------------------------------------------------------------- #
# La sensibilidad: la corrección por doble muestreo, con su bootstrap          #
# --------------------------------------------------------------------------- #
def pis(pares: list[tuple[str, str]]) -> tuple[float | None, float | None, dict]:
    """(π₁, π₀, cuentas) de los pares (v3, autora) que deciden las dos."""
    c = [a for j, a in pares if j == "correcta"]
    i = [a for j, a in pares if j == "incorrecta"]
    p1 = sum(a == "correcta" for a in c) / len(c) if c else None
    p0 = sum(a == "correcta" for a in i) / len(i) if i else None
    return p1, p0, {"pi_1": f"{sum(a == 'correcta' for a in c)} de {len(c)}", "pi_0": f"{sum(a == 'correcta' for a in i)} de {len(i)}"}


def q_de(v200: list[tuple[str, str]], W: dict[str, float]) -> tuple[float, float, dict[str, float]]:
    """(q cruda, q ponderada, q por estrato) de las 200: (estrato, veredicto de la v3)."""
    por = {}
    for h, v in v200:
        k, n = por.get(h, (0, 0))
        por[h] = (k + (v == "correcta"), n + 1)
    q_h = {h: k / n for h, (k, n) in por.items()}
    w = sum(W[h] for h in q_h)
    return (sum(v == "correcta" for _, v in v200) / len(v200), sum(W[h] * q for h, q in q_h.items()) / w, q_h)


def corregidas(p1: float, p0: float, v200: list[tuple[str, str]], autora: dict[str, tuple[int, int]],
               W: dict[str, float]) -> dict:
    """La cifra de la v3 corregida (cruda y ponderada) y la de las 400 con esa parte corregida. v200: (estrato, veredicto)
    de las fichas que decidió la v3; autora: estrato -> (k, n) de las decididas por la autora (sus 200 y las adjudicadas).
    p_h: la fracción de cada estrato en la de las 400."""
    qc, qw, q_h = q_de(v200, W)
    n_v = {}
    for h, _ in v200:
        n_v[h] = n_v.get(h, 0) + 1
    corr = lambda q: p1 * q + p0 * (1 - q)
    ka, na = sum(k for k, _ in autora.values()), sum(n for _, n in autora.values())
    p_h = {}
    for h in set(autora) | set(n_v):
        k, n = autora.get(h, (0, 0))
        nv = n_v.get(h, 0)
        if n + nv:
            p_h[h] = (k + nv * corr(q_h.get(h, 0.0))) / (n + nv)
    w = sum(W[h] for h in p_h)
    return {"v3_cruda": corr(qc), "v3_ponderada": corr(qw), "q_cruda": qc, "q_ponderada": qw,
            "las_400_cruda": (ka + len(v200) * corr(qc)) / (na + len(v200)),
            "las_400_ponderada": sum(W[h] * p for h, p in p_h.items()) / w, "p_h": p_h}


def percentil(xs: list[float], p: float) -> float:
    """El percentil p (de 0 a 100) con interpolación lineal entre los dos vecinos."""
    s = sorted(xs)
    pos = p / 100 * (len(s) - 1)
    i = int(pos)
    return s[i] if i + 1 >= len(s) else s[i] + (s[i + 1] - s[i]) * (pos - i)


def remuestrear(rng, por_estrato: dict[str, list[tuple[str, str | None]]]) -> dict[str, list[tuple[str, str | None]]]:
    """En cada estrato, en orden de nombre, tantas fichas como tiene, sorteadas con reposición (rng.randrange)."""
    return {h: [fs[rng.randrange(len(fs))] for _ in fs] for h, fs in sorted(por_estrato.items())}


def replica(rng, pares: list[tuple[str, str]], por_estrato: dict, W: dict) -> dict | None:
    """Una réplica: primero los pares (tantos como hay, con reposición), después los estratos (remuestrear). Las fichas son
    (fuente, veredicto); las de la v3 se corrigen y las de la autora y las adjudicadas cuentan tal cual (las no decidibles
    no cuentan). None si la réplica no define π₁, π₀ o q."""
    pb = [pares[rng.randrange(len(pares))] for _ in pares]
    est = remuestrear(rng, por_estrato)
    p1, p0, _c = pis(pb)
    vb = [(h, v) for h, fs in est.items() for fuente, v in fs if fuente == "v3"]
    if p1 is None or p0 is None or not vb:
        return None
    autora = {}
    for h, fs in est.items():
        dec = [v for fuente, v in fs if fuente != "v3" and v is not None]
        if dec:
            autora[h] = (sum(v == "correcta" for v in dec), len(dec))
    return corregidas(p1, p0, vb, autora, W) | {"tamanos": {h: len(fs) for h, fs in est.items()}}


def bootstrap(pares: list[tuple[str, str]], por_estrato: dict, W: dict, *, semilla: int = SEMILLA,
              replicas: int = REPLICAS) -> dict:
    rng = random.Random(semilla)
    claves = ("v3_cruda", "v3_ponderada", "las_400_cruda", "las_400_ponderada")
    vals, indef = {k: [] for k in claves}, 0
    for _ in range(replicas):
        c = replica(rng, pares, por_estrato, W)
        if c is None:
            indef += 1
            continue
        for k in claves:
            vals[k].append(c[k])
    return {"semilla": semilla, "replicas": replicas, "indefinidas": indef, "percentiles": list(PERCENTILES),
            "remuestreo": ("dos sorteos con reposición e independientes en cada réplica: los pares de la validación, para "
                           "π₁ y π₀, y, estrato por estrato, las fichas de las 400 con su tamaño de origen; cada ficha "
                           "conserva de dónde viene su marca (autora, adjudicación o v3), y solo las de la v3 se corrigen"),
            "intervalo_de_cada_cifra": {"cifra_principal": "analítico: Wilson con el n efectivo de Kish (enmienda 3)",
                                        "sensibilidad": "bootstrap (decisión 6), con estos percentiles"},
            "intervalos": {k: [percentil(v, PERCENTILES[0]), percentil(v, PERCENTILES[1])] if v else None
                           for k, v in vals.items()}}


# --------------------------------------------------------------------------- #
# La composición (pura: la usan main y las pruebas)                            #
# --------------------------------------------------------------------------- #
def analizar(*, entrada: dict, las_200: list[str], calibracion: dict, validacion: dict, juez_validacion: dict,
             juez_200: dict, an_validacion: dict, refs_v097: list[str], at2, wk, adjudicadas: dict[str, str] | None = None,
             semilla: int = SEMILLA, replicas: int = REPLICAS) -> dict:
    """entrada: la de validar_entrada; calibracion y validacion: ref -> {correcta, importancia} de la autora; juez_*: ref
    -> {veredicto, via} de la v3; adjudicadas: ref -> correcta | incorrecta, de la hoja de adjudicación de la autora, o
    None. Devuelve el JSON del análisis, o {"frena": ...} con las que van a adjudicación si faltan sus veredictos."""
    cal, val, d200 = set(calibracion), set(validacion), set(las_200)
    if cal & val or cal & d200 or val & d200 or cal | val | d200 != set(entrada["fichas"]):
        raise SystemExit("FRENO: calibración, validación y las 200 no son disjuntas o no dan las 400 de la entrada")
    if sorted(cal) != entrada["las_100"]:
        raise SystemExit("FRENO: las 100 de la autora de la entrada no son las de calibración")
    if set(juez_200) != d200 or set(juez_validacion) != val:
        raise SystemExit("FRENO: los agregados no traen exactamente las 200 y las 100 de la validación")
    pend = at2.a_adjudicacion(juez_200)
    if pend and adjudicadas is None:
        return {"frena": True, "a_adjudicacion": len(pend), "refs": pend}
    if adjudicadas is not None and not pend:
        raise SystemExit("FRENO: viene la hoja de adjudicación y la v3 no mandó ninguna de las 200 a adjudicación: sobra")
    adj = dict(adjudicadas or {})
    if set(adj) != set(pend) or any(v not in VEREDICTOS_ADJUDICACION for v in adj.values()):
        raise SystemExit("FRENO: las adjudicaciones no son exactamente las que la v3 manda a adjudicación")
    v3 = {r: J.dos_clases(juez_200[r]["veredicto"]) for r in sorted(d200 - set(adj))}
    de_la_autora = [at2._fila(entrada, r, x[r]["correcta"], x[r]["importancia"] == "esencial")
                    for x in (calibracion, validacion) for r in sorted(x)]
    de_las_adjudicadas = [at2._fila(entrada, r, adj[r], None) for r in sorted(adj)]
    de_la_v3 = [at2._fila(entrada, r, v3[r], None) for r in sorted(v3)]
    filas = de_la_autora + de_las_adjudicadas + de_la_v3
    pares = [(J.dos_clases(juez_validacion[r]["veredicto"]), validacion[r]["correcta"]) for r in sorted(val)]
    pares = [(j, a) for j, a in pares if j is not None and a is not None]
    nota = nota_del_desvio(an_validacion, pares)
    salen = set(refs_v097)
    W = entrada["W_h"]
    autora_h = {}
    for f in de_la_autora + de_las_adjudicadas:          # las adjudicadas cuentan como lectura de la autora
        if f["correcta"] is not None:
            k, n = autora_h.get(f["estrato"], (0, 0))
            autora_h[f["estrato"]] = (k + (f["correcta"] == "correcta"), n + 1)
    v200 = [(entrada["fichas"][r]["estrato"], v3[r]) for r in sorted(v3)]
    por_estrato = {}
    for fuente, fs in (("autora", de_la_autora), ("adjudicada", de_las_adjudicadas), ("v3", de_la_v3)):
        for f in fs:
            por_estrato.setdefault(f["estrato"], []).append((fuente, f["correcta"]))
    p1, p0, cuentas = pis(pares)
    if p1 is None or p0 is None:
        raise SystemExit("FRENO: los pares de la validación no traen «correcta» e «incorrecta» de la v3: no hay π₁ y π₀")
    punto = corregidas(p1, p0, v200, autora_h, W)
    sin = corregidas(1.0, 0.0, v200, autora_h, W)          # sin corregir: tiene que dar la cifra principal
    principal = at2.estimadores(filas, entrada, wk)
    q_w_v2 = at2.ponderada({h: (sum(v == "correcta" for hh, v in v200 if hh == h), sum(hh == h for hh, _ in v200))
                            for h in {h for h, _ in v200}}, entrada["N_h"], wk)["p_w"]
    if abs(sin["las_400_cruda"] - principal["todo"]["cruda"]["p"]) > 1e-12 or \
            abs(sin["las_400_ponderada"] - principal["todo"]["ponderada"]["p_w"]) > 1e-9 or abs(q_w_v2 - punto["q_ponderada"]) > 1e-9:
        raise SystemExit("FRENO: la cuenta de la sensibilidad sin corregir no da la cifra principal")
    return {
        "frena": False,
        "cifra_principal": {"opcion": "B (decisión 5)", "composicion": {
            "lectura_de_la_autora": {"calibracion": len(cal), "validacion": len(val)}, "v3": len(v3),
            "adjudicadas_por_la_autora": len(adj),
            "las_adjudicadas": "fichas de las 200 que la v3 no decidió: cuentan con el veredicto de la hoja de "
                               "adjudicación de la autora" if adj else None,
            "la_v3_no_cuenta_en_la_validacion": True,
            "esenciales": "solo las de la autora en sus 200: la v3 no juzga la importancia y la hoja de adjudicación "
                          "no la trae"},
            **principal, "intervalo": "analítico: Wilson con el n efectivo de Kish (enmienda 3)", "nota_del_desvio": nota},
        "al_lado": {
            "lectura_de_la_autora_en_sus_200": {
                "fichas": "sus 200 de calibración y validación; las adjudicadas no entran", "adjudicadas_que_no_entran": len(adj),
                **at2.estimadores(de_la_autora, entrada, wk)},
            "las_400_sin_la_arista_de_V097": {"refs_que_salen": sorted(salen), "fichas_que_salen": len(salen),
                                              **at2.estimadores([f for f in filas if f["ref"] not in salen], entrada, wk),
                                              "nota_del_desvio": nota}},
        "nota_del_desvio": nota,
        "sensibilidad": {"marca": MARCA_SENSIBILIDAD, "metodo": "doble muestreo (Tenenbein, 1970), π juntas, no por estrato",
                         "pares_de_la_validacion": len(pares), **cuentas, "pi_1_valor": p1, "pi_0_valor": p0,
                         "que_se_corrige": {"fichas_de_la_v3": len(v3), "adjudicadas_como_lectura_de_la_autora": len(adj)},
                         "q": {"cruda": punto["q_cruda"], "ponderada": punto["q_ponderada"]},
                         "v3_corregida": {"cruda": punto["v3_cruda"], "ponderada": punto["v3_ponderada"]},
                         "las_400_con_la_parte_de_la_v3_corregida": {"cruda": punto["las_400_cruda"],
                                                                     "ponderada": punto["las_400_ponderada"]},
                         "bootstrap": bootstrap(pares, por_estrato, W, semilla=semilla, replicas=replicas),
                         "nota_del_desvio": nota}}


def main(argv=None, consola=print) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, required=True, help="el JSON de las 400 de la mesa (el de la v2)")
    ap.add_argument("--entrada-sha256", default=ENTRADA_SHA256)
    ap.add_argument("--repo", type=Path, default=PJ.REPO_DEFECTO)
    ap.add_argument("--corridas", type=Path, default=CV.CORRIDAS)
    ap.add_argument("--tt", type=Path, default=CV.TT)
    ap.add_argument("--tt3", type=Path, default=CVAL.TT3)
    ap.add_argument("--refs", type=Path, default=CV.REFS_100)
    ap.add_argument("--fichas", type=Path, default=CV.FICHAS_T)
    ap.add_argument("--acta-sha256", default=CVAL.ACTA_SHA256)
    ap.add_argument("--entrada-200", type=Path, default=A2.DIR_ENTRADA)
    ap.add_argument("--sello-lectura-T", type=Path, default=CV.SELLO_LECTURA_T)
    ap.add_argument("--sello-lectura-T-sha256", default=CV.SELLO_LECTURA_T_SHA256)
    ap.add_argument("--sello-lectura-v3", type=Path, default=CVAL.SELLO_LECTURA_V3)
    ap.add_argument("--sello-lectura-v3-sha256", default=CVAL.SELLO_LECTURA_V3_SHA256)
    ap.add_argument("--registro", type=Path, default=CG.CONGELACION / CG.REGISTRO)
    ap.add_argument("--sello-adjudicacion-200", type=Path, help="el sello de la hoja de adjudicación de las 200")
    ap.add_argument("--sello-adjudicacion-200-sha256")
    ap.add_argument("--salida", type=Path)
    a = ap.parse_args(argv)
    if (a.sello_adjudicacion_200 is None) != (a.sello_adjudicacion_200_sha256 is None):
        raise SystemExit("FRENO: --sello-adjudicacion-200 va con --sello-adjudicacion-200-sha256")
    salida = a.salida or Path(a.corridas) / SALIDA_DIR
    ruta = Path(salida) / SALIDA_NOMBRE
    if ruta.exists():
        raise SystemExit(f"FRENO: {ruta.name} ya existe: no se pisa")
    at2 = AV.cargar_at2()
    wk = at2.cargar_wk(a.repo)
    eb = Path(a.entrada).read_bytes()
    if sha(eb) != a.entrada_sha256:
        raise SystemExit("FRENO: la entrada de las 400 no da su sha256")
    entrada = at2.validar_entrada(json.loads(eb))
    prompt_sha = json.loads(Path(a.registro).read_text(encoding="utf-8"))["prompt"]["sha256"]
    f = A2.fuentes(a.repo, a.tt, a.tt3, a.refs, a.fichas, a.acta_sha256)
    e200 = A2.leer_entrada(a.entrada_200, f["las_200"])
    d200, dval = Path(a.corridas) / C200.NOMBRE, Path(a.corridas) / CVAL.MODO
    if (Path(a.corridas) / f"declaracion_{C200.NOMBRE}_no_completado.json").exists():
        raise SystemExit("FRENO: las 200 no se completaron: no hay cifra de las 400")
    ag200, res200 = corrida_completa(d200, "las 200")
    agv, resv = corrida_completa(dval, "la validación")
    juez_200 = leer_agregado_200(json.loads(ag200.read_text(encoding="utf-8")), set(e200["refs"]), prompt_sha)
    pend = at2.a_adjudicacion(juez_200)
    adj = None
    if pend and a.sello_adjudicacion_200 is None:   # antes de leer ninguna hoja: la autora adjudica (punto 10)
        consola(f"FRENO: {len(pend)} de las 200 van a adjudicación (las adjudica la autora): {', '.join(pend)}")
        return 2
    if not pend and a.sello_adjudicacion_200 is not None:
        raise SystemExit("FRENO: viene el sello de la adjudicación y la v3 no mandó ninguna de las 200 a adjudicación: sobra")
    if pend:
        adj = leer_adjudicacion(a.sello_adjudicacion_200, a.sello_adjudicacion_200_sha256, pend)
    acta = CVAL.leer_acta(a.tt3, a.acta_sha256)
    da = AV.del_acta(acta["acta"])
    juez_val = AV.leer_agregado(json.loads(agv.read_text(encoding="utf-8")), set(da["predicado"]), prompt_sha)
    an_val_p = dval / AV.SALIDA_NOMBRE
    an_val_b = an_val_p.read_bytes()
    an_val = json.loads(an_val_b)
    s_cal = CVAL.controlar_sello_lectura(a.sello_lectura_T, a.sello_lectura_T_sha256, a.tt)       # antes de leer una hoja
    s_val = CVAL.controlar_sello_lectura(a.sello_lectura_v3, a.sello_lectura_v3_sha256, a.tt3)
    lect_cal, shas_cal = CV.leer_hojas_T(Path(a.tt) / "lectura", {r: f["fichas_T"][r]["predicado"] for r in f["calibracion"]},
                                         sha256_acta=CV.ACTA_T_SHA256)
    lect_val, shas_val = CV.leer_hojas_T(Path(a.tt3) / "lectura", da["predicado"], sha256_acta=acta["sha256"],
                                         campo_acta=AV.CAMPO_ACTA, lotes=AV.LOTES)
    ev = an_val.get("entradas_sha256") or {}
    if ev.get("agregado") != sha(agv.read_bytes()) or ev.get("hojas") != shas_val:
        raise SystemExit("FRENO: el análisis de la validación no es el del agregado y las hojas de la validación")
    out = analizar(entrada=entrada, las_200=e200["refs"],
                   calibracion={r: {"correcta": v["correcta"], "importancia": v["importancia"]} for r, v in lect_cal.items()},
                   validacion={r: {"correcta": v["correcta"], "importancia": v["importancia"]} for r, v in lect_val.items()},
                   juez_validacion=juez_val, juez_200=juez_200, an_validacion=an_val,
                   refs_v097=refs_de_V097(a.repo, f["fichas_T"]), at2=at2, wk=wk,
                   adjudicadas=adj["veredictos"] if adj else None)
    out = {"code_ver": CODE_VER, "decide": "las 400 de T con la v3, opción B (desvío declarado, decisiones 3, 5 y 6)",
           **{k: v for k, v in out.items() if k != "frena"},
           "sellos_de_las_lecturas": {"calibracion": s_cal, "validacion": s_val},
           "adjudicacion_200": {"sello_sha256": adj["sello_sha256"], "hoja_sha256": adj["hoja_sha256"],
                                "adjudicadas": adj["adjudicadas"]} if adj else {"sello_sha256": None, "adjudicadas": 0},
           "entradas_sha256": {"entrada_400": a.entrada_sha256, "entrada_200": e200["sha256"],
                               "agregado_200": sha(ag200.read_bytes()), "resumen_200": sha(res200.read_bytes()),
                               "agregado_validacion": sha(agv.read_bytes()), "resumen_validacion": sha(resv.read_bytes()),
                               "analisis_validacion": sha(an_val_b), "registro": sha(Path(a.registro).read_bytes()),
                               "hojas_calibracion": shas_cal, "hojas_validacion": shas_val},
           "codigo_sha256": {n: sha((Path(__file__).parent / n).read_bytes()) for n in
                             ("analisis_400_v3.py", "armar_200_v3.py", "analisis_validacion_v3.py")}
           | {"analisis_T_v2.py": AV.AT2_SHA256}}
    Path(salida).mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    consola(f"análisis de las 400 de la v3: escrito | {ruta.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
