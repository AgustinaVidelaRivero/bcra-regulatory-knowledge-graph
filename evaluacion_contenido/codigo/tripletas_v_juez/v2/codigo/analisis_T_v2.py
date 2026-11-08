"""
analisis_T_v2.py — U-TRIP-V-JUEZ-V2, etapas c a f: el análisis de la prueba de la v2 congelada sobre T (enmienda 4 al
pre-registro de tripletas, puntos 8 a 10), la cuarta pieza del punto 5. USD 0: no llama a la API.

Lee T solo por sus parámetros, todos obligatorios salvo los dos de la medición de las 400, y uno de --agregado-prueba o
--prueba-no-completada, y nada más de T:
  --entrada        el JSON que arma la mesa al correr: N y N_h del grafo evaluado de T, los estratos con sus predicados,
                   N y N_h sin la tanda 0, las 400 fichas de la muestra (ref, predicado, estrato, TO, si es de la tanda 0,
                   si es de las 100 de la autora y, desde la v2.2, su etapa, de E0 a E5, su chunk_id y su estado_e3, un
                   texto o null), las refs de las 100 que coinciden con un caso del prompt de la v2 y, desde la v2.3,
                   las de las 400 (refs_coincidentes_400: en las 100, exactamente las de refs_coincidentes);
  --agregado-prueba  el agregado de la v2 congelada sobre las 100 de la autora, con el formato que escribe
                   correr_juez_v2.agregar (el de corridas/iteracion_1/NO_ABRIR_agregado.json);
  --prueba-no-completada  desde la v2.3, en lugar de --agregado-prueba: la declaración que escribe el comando de la mesa
                   cuando la prueba no se completa (una repetición cortada por el tope o el freno, o por una falla de
                   infraestructura después de dos re-corridas; desde la v2.4, también antes, si otra repetición de la
                   misma corrida cortó por el tope o el freno). No se lee ningún agregado: rige el punto 10;
  --hojas, --sha256-acta  la carpeta de las hojas selladas de la autora sobre sus 100 y el sha256 del acta del sorteo de
                   T que trae su cabecera (en el campo `acta_sorteo_T.json_sha256`, --campo-acta); los lotes, por nombre
                   (--lotes, por defecto los de V: piloto y lote_01 a lote_09);
  --agregado-400   si la prueba pasa: el agregado de la v2 sobre las 300 restantes, o sobre las 400 (en las 100, igual
                   al de la prueba);
  --restantes-no-completadas  desde la v2.3, en lugar de --agregado-400, con el agregado de una prueba completa que pasa:
                   la declaración que escribe el comando de la mesa cuando las 300 restantes no se completan (la misma
                   regla de la corrida cortada que la prueba). No se lee ningún agregado de las 300: la prueba va como
                   siempre, la medición de las 400 en null y la precisión de T con las 100 de la autora;
  --adjudicaciones si la prueba pasa: {ref: {correcta: si | no | no decidible, importancia: esencial | util | accesoria}}
                   de lo que la v2 manda a adjudicación entre las 300 que no son de la autora. Sin ellas, la medición
                   frena y el JSON dice cuántas y cuáles faltan. En sus 100 no hay adjudicación nueva: cuenta la marca
                   de su hoja sellada, y una adjudicación de una de las 100 frena (decisión de la autora del 25/10/2026,
                   recibida a las 18:22:29; registro de decisiones, §116; cambio de la mesa, §274).

Qué calcula:
  1. la prueba, una sola vez (punto 8): el §4.6 tal cual sobre las 100, con criterios() de la v1
     (codigo/analisis_gold_juez_v.py, importada con su sha256 por v1_importada, sin copiarla ni cambiarla): las tres
     condiciones de «correcta» con el borde de (ii) redondeado a 10 decimales, la importancia en proporción sobre los
     pares válidos (registro de decisiones, §84), los kappa, cuántas van a adjudicación con su proporción y si son más
     de 15. criterios() estratifica la ponderada de (ii) por la clave `predicado` de cada par: acá lleva el estrato de la
     ficha y los W_h son los de T (N_h / N de la entrada). Con un predicado por estrato es lo mismo; en un estrato que
     agrupa varios predicados, como «otros», la ponderada va por estrato, como dice el §3.6;
  2. la misma prueba sin las fichas de refs_coincidentes, al lado (registro, §103). Decide la de las 100;
  3. si pasa, la medición de las 400 (punto 9): cuentan la «correcta» y la importancia de la v2, y en lo que manda a
     adjudicación, las de la autora (nota del 15/10/2026): en sus 100, las de su hoja sellada; en las otras 300, su
     adjudicación. Desde la v2.3, al lado, la misma medición sin las fichas de refs_coincidentes_400, como sensibilidad;
  4. si no pasa, o si no se completa, la precisión de T con las 100 de la autora (punto 10). Si pasa y las 300 no se
     completan, también, con la prueba al lado y la declaración de las 300, sin ninguna cifra de las fichas de las 300.
En 3 y en 4, los estimadores del §3.6 con el intervalo de la enmienda 3 (wilson_kish_tripletas_mesa.py del repo, importado
con su sha256 de HEAD, sin cambiarlo): la cruda con Wilson y la ponderada con Wilson y el n efectivo de Kish, de todo y de
las esenciales, con y sin la tanda 0 (los W_h sin la tanda 0, de N_h sin la tanda 0: enmienda 2, §2); `aplica_a` sola,
cruda, con y sin la tanda 0; por predicado y por TO, y desde la v2.2 por etapa E0–E5 y por la procedencia de la arista
(estado_e3 y chunk_id; §3.6), «k de n», con Wilson solo donde n ≥ 20; las no decidibles aparte, con las dos cotas. Un estrato sin muestra decidida (de todo o de las esenciales) sale de la suma: los W_h de los demás se
renormalizan, y se declara con su W_h y las dos cotas de la cifra (ese estrato todo correcto o todo incorrecto); los
estratos con n_h < 5 se agrupan en «otros» para el intervalo y se informan con su fracción cruda.

La salida es un JSON en la carpeta de --salida (analisis_T_v2.json; no pisa uno existente). La consola dice solo si corrió
y dónde escribió, sin ninguna cifra. rc 0: todo lo que corresponde está calculado; rc 2: la prueba pasa y la medición de
las 400 espera el agregado o las adjudicaciones; un FRENO (rc 1) no escribe nada.

  .venv/bin/python -B analisis_T_v2.py --entrada … --agregado-prueba … --hojas … --sha256-acta … --salida …
                                       [--agregado-400 …] [--adjudicaciones …] [--lotes …] [--campo-acta …] [--repo …]
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import importlib.util  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import juez_v2 as J  # noqa: E402
import prompt_juez_v2 as PV  # noqa: E402
from v1_importada import AG, PJ, V2  # noqa: E402

CODE_VER = "analisis-T-v2.4"   # .1: en las 100 de la autora, su hoja en lugar de una adjudicación (§274)
#                                .2: por etapa y por procedencia (§3.6), con esos tres campos en cada ficha de la entrada
#                                .3: la medición sin las coincidentes, al lado, y la prueba no completada (punto 10)
#                                .4: la infraestructura con menos de 3 intentos, si otra repetición cortó por el tope o el freno
# La v2 congelada (nota al pie del pre-registro del 25/10/2026; congelacion_juez_v2_sha256.txt): su prompt, el de la
# iteración 1, y el archivo de sus casos, del que salen las refs de los casos del prompt.
PROMPT_V2_SHA256 = "cf40964da9718181595a85b18485af02fb74c0dd255df9e9de28404acc82dfa5"
CASOS_V2 = V2 / "casos" / "casos_iteracion_1.json"
CASOS_V2_SHA256 = "7ce471bafa0048b40e2dea9625b115ef5d949a17867816e748a791c2647e13b7"
# El intervalo de la enmienda 3, del repo, sin cambiarlo: el sha256 de HEAD (el del commit de su firma, 7cbf3525).
WK_REL = Path("data") / "experiment" / "tripletas_v" / "analisis" / "wilson_kish_tripletas_mesa.py"
WK_SHA256 = "8b0440bcd3a7d6900a27da5c6c3cecd9bdb09d39e6c670733e6308e743a0f73e"
CAMPO_ACTA_T = "acta_sorteo_T.json_sha256"
LOTES_DEFECTO = ("piloto",) + tuple(f"lote_{i:02d}" for i in range(1, 10))
N_MUESTRA, N_AUTORA = 400, 100           # enmienda 4, punto 6
N_CON_WILSON = 20                        # §3.6: por predicado y por TO, «n de N» donde N < 20
SALIDA_NOMBRE = "analisis_T_v2.json"
CLAVES_ENTRADA = {"N", "N_h", "estratos", "N_sin_tanda0", "N_h_sin_tanda0", "fichas", "refs_coincidentes",
                  "refs_coincidentes_400"}
CLAVES_NO_COMPLETADA = {"modo", "completada", "repeticiones"}
MOTIVOS_DE_UNA_REPETICION = ("completa", "tope", "freno", "infraestructura")
INTENTOS_MAXIMOS = 3                     # la corrida y hasta dos re-corridas por una falla de infraestructura
CLAVES_FICHA = {"ref", "predicado", "estrato", "to", "tanda0", "en_las_100", "etapa", "chunk_id", "estado_e3"}
ETAPAS = ("E0", "E1", "E2", "E3", "E4", "E5")
SIN_ESTADO_E3 = "(null)"                 # el grupo de las fichas con estado_e3 null
ETIQUETA_400 = "la precisión de T medida por la v2 sobre las 400 (enmienda 4, punto 9)"
ETIQUETA_100 = "la precisión de T con las 100 de la autora (enmienda 4, punto 10)"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cargar_wk(repo: Path):
    """wilson_kish_tripletas_mesa.py del repo, importado por su ruta después de controlar su sha256."""
    p = Path(repo) / WK_REL
    if sha256(p.read_bytes()) != WK_SHA256:
        raise SystemExit(f"FRENO: {p.name} no es el de HEAD ({WK_SHA256[:8]}…)")
    spec = importlib.util.spec_from_file_location("wilson_kish_tripletas_mesa", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def refs_casos_v2() -> list[str]:
    """Las refs de los casos del prompt de la v2 congelada, de casos_iteracion_1.json, con su sha256."""
    b = CASOS_V2.read_bytes()
    if sha256(b) != CASOS_V2_SHA256:
        raise SystemExit("FRENO: casos_iteracion_1.json no es el de la congelación")
    return sorted(c["ref"] for c in json.loads(b)["casos"])


# --------------------------------------------------------------------------- #
# Las entradas                                                                #
# --------------------------------------------------------------------------- #
def _entero(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validar_entrada(d: dict) -> dict:
    """Controla el JSON de la mesa y devuelve lo que usa el análisis: los W_h, con y sin la tanda 0, y las fichas por ref."""
    if not isinstance(d, dict) or set(d) != CLAVES_ENTRADA:
        raise SystemExit("FRENO: la entrada no trae exactamente las claves del formato")
    n_h, est, n_h_s = d["N_h"], d["estratos"], d["N_h_sin_tanda0"]
    if not (_entero(d["N"]) and d["N"] > 0 and isinstance(n_h, dict) and n_h
            and all(isinstance(h, str) and _entero(v) and v >= 0 for h, v in n_h.items()) and sum(n_h.values()) == d["N"]):
        raise SystemExit("FRENO: N y N_h de la entrada no son enteros o N_h no suma N")
    if not (isinstance(est, dict) and set(est) == set(n_h)
            and all(isinstance(v, list) and v and all(isinstance(p, str) for p in v) for v in est.values())):
        raise SystemExit("FRENO: los estratos de la entrada no son los de N_h o no traen sus predicados")
    todos = [p for v in est.values() for p in v]
    if len(todos) != len(set(todos)):
        raise SystemExit("FRENO: un predicado está en dos estratos")
    if not (_entero(d["N_sin_tanda0"]) and isinstance(n_h_s, dict) and set(n_h_s) == set(n_h)
            and all(_entero(v) and 0 <= v <= n_h[h] for h, v in n_h_s.items()) and sum(n_h_s.values()) == d["N_sin_tanda0"]
            and d["N_sin_tanda0"] > 0):
        raise SystemExit("FRENO: N y N_h sin la tanda 0 no son enteros, pasan los de todo o no suman")
    fichas = d["fichas"]
    if not (isinstance(fichas, list) and all(isinstance(f, dict) and set(f) == CLAVES_FICHA for f in fichas)):
        raise SystemExit("FRENO: una ficha de la entrada no trae exactamente sus claves")
    for f in fichas:
        if not (all(isinstance(f[k], str) and f[k] for k in ("ref", "predicado", "estrato", "to"))
                and isinstance(f["tanda0"], bool) and isinstance(f["en_las_100"], bool)):
            raise SystemExit("FRENO: una ficha de la entrada tiene un campo de otro tipo")
        if f["etapa"] not in ETAPAS or not (isinstance(f["chunk_id"], str) and f["chunk_id"]) \
                or not (f["estado_e3"] is None or isinstance(f["estado_e3"], str)):
            raise SystemExit(f"FRENO: la ficha {f['ref']} no trae una etapa de E0 a E5, un chunk_id o un estado_e3 válido")
        if f["estrato"] not in est or f["predicado"] not in est[f["estrato"]]:
            raise SystemExit(f"FRENO: la ficha {f['ref']} no es de un predicado de su estrato")
    por_ref = {f["ref"]: f for f in fichas}
    if len(por_ref) != len(fichas) or len(fichas) != N_MUESTRA or sum(f["en_las_100"] for f in fichas) != N_AUTORA:
        raise SystemExit("FRENO: la entrada no trae las fichas de la muestra de T, sin repetir, con las de la autora")
    for h in n_h:
        if sum(f["estrato"] == h for f in fichas) > n_h[h] or \
                sum(f["estrato"] == h and not f["tanda0"] for f in fichas) > n_h_s[h]:
            raise SystemExit(f"FRENO: el estrato {h} tiene más fichas en la muestra que aristas en el grafo")
    coinc = d["refs_coincidentes"]
    if not (isinstance(coinc, list) and len(coinc) == len(set(coinc))
            and all(isinstance(r, str) and r in por_ref and por_ref[r]["en_las_100"] for r in coinc)):
        raise SystemExit("FRENO: refs_coincidentes no son refs de las 100 de la autora, sin repetir")
    c400 = d["refs_coincidentes_400"]
    if not (isinstance(c400, list) and len(c400) == len(set(c400)) and all(isinstance(r, str) and r in por_ref for r in c400)
            and {r for r in c400 if por_ref[r]["en_las_100"]} == set(coinc)):
        raise SystemExit("FRENO: refs_coincidentes_400 no son refs de las fichas, sin repetir, con exactamente las de "
                         "refs_coincidentes entre las 100")
    return {"N": d["N"], "N_h": dict(n_h), "estratos": {h: list(v) for h, v in est.items()},
            "N_sin_tanda0": d["N_sin_tanda0"], "N_h_sin_tanda0": dict(n_h_s),
            "W_h": {h: n_h[h] / d["N"] for h in n_h}, "fichas": por_ref,
            "las_100": sorted(r for r, f in por_ref.items() if f["en_las_100"]), "refs_coincidentes": sorted(coinc),
            "refs_coincidentes_400": sorted(c400)}


def validar_no_completada(d: dict, modo: str = "prueba_T") -> dict:
    """La declaración de una corrida no completada (la prueba, o las 300 restantes con modo restantes_400): el modo,
    completada false y las tres repeticiones, cada una con sus intentos (de 1 a 3) y su motivo; al menos una que no sea
    completa. Infraestructura va con sus 3 intentos o, desde la v2.4, con menos si otra repetición de la misma declaración
    trae tope o freno: en ese caso no se re-corre nada (la regla de la corrida cortada) y la corrida no se completa."""
    if not isinstance(d, dict) or set(d) != CLAVES_NO_COMPLETADA or d["modo"] != modo or d["completada"] is not False:
        raise SystemExit(f"FRENO: la declaración de la corrida no completada no trae modo {modo} y completada false")
    reps = d["repeticiones"]
    if not isinstance(reps, dict) or set(reps) != {"1", "2", "3"}:
        raise SystemExit("FRENO: la declaración no trae las repeticiones 1, 2 y 3")
    for k, v in reps.items():
        if not (isinstance(v, dict) and set(v) == {"intentos", "motivo"} and _entero(v["intentos"])
                and 1 <= v["intentos"] <= INTENTOS_MAXIMOS and v["motivo"] in MOTIVOS_DE_UNA_REPETICION):
            raise SystemExit(f"FRENO: la repetición {k} de la declaración no trae sus intentos (de 1 a 3) y un motivo válido")
    for k, v in reps.items():
        otra_corto_por_el_gasto = any(w["motivo"] in ("tope", "freno") for j, w in reps.items() if j != k)
        if v["motivo"] == "infraestructura" and v["intentos"] != INTENTOS_MAXIMOS and not otra_corto_por_el_gasto:
            raise SystemExit(f"FRENO: la repetición {k} declara una falla de infraestructura sin sus {INTENTOS_MAXIMOS} "
                             f"intentos, y ninguna otra cortó por el tope o el freno")
    if all(v["motivo"] == "completa" for v in reps.values()):
        raise SystemExit("FRENO: la declaración dice que las tres repeticiones se completaron")
    return d


def leer_agregado(d: dict, refs: set[str] | None, casos: list[str]) -> dict[str, dict]:
    """ref -> {veredicto, via, importancia} (los modales) del agregado de la v2 congelada. Controla los 0 cruces, el
    modelo, el esfuerzo, la versión del código y del prompt, el prompt congelado en el agregado y en cada ficha, las tres
    repeticiones y los casos del prompt; con `refs`, que traiga exactamente esas fichas."""
    if not isinstance(d, dict) or (d.get("verificacion_cross_hits") or {}).get("cross_hits") != 0:
        raise SystemExit("FRENO: el agregado no trae la verificación de 0 cruces entre las tres bases")
    esperado = {"modelo": J.MODELO, "esfuerzo": J.ESFUERZO, "code_ver_base": J.CODE_VER_BASE,
                "version_prompt": PV.VERSION, "prompt_sha256": PROMPT_V2_SHA256, "reps": J.REPS}
    for campo, v in esperado.items():
        if d.get(campo) != v:
            raise SystemExit(f"FRENO: el agregado trae {campo} {d.get(campo)!r}, no el de la v2 congelada")
    if sorted(d.get("refs_casos_del_prompt") or []) != casos:
        raise SystemExit("FRENO: los casos del prompt del agregado no son los de la v2 congelada")
    out = {}
    for x in d.get("fichas") or []:
        if x.get("prompt_sha256") != PROMPT_V2_SHA256:
            raise SystemExit(f"FRENO: la ficha {x.get('ref')} del agregado no trae el prompt congelado")
        if x["ref"] in out:
            raise SystemExit(f"FRENO: la ficha {x['ref']} está dos veces en el agregado")
        try:
            ag = x["agregado"]
            out[x["ref"]] = {"veredicto": ag["veredicto"]["modal"], "via": ag["veredicto"]["via"],
                             "importancia": ag["importancia"]["modal"]}
        except (KeyError, TypeError):
            raise SystemExit(f"FRENO: la ficha {x.get('ref')} del agregado no trae el veredicto y la importancia modales")
    if refs is not None and set(out) != set(refs):
        raise SystemExit("FRENO: el agregado no trae exactamente las fichas que se esperan")
    return out


def leer_hojas_T(carpeta: Path, fichas_100: dict[str, str], *, sha256_acta: str, campo_acta: str = CAMPO_ACTA_T,
                 lotes=LOTES_DEFECTO) -> tuple[dict[str, dict], dict[str, str]]:
    """(ref -> {correcta, importancia, lote}, hoja -> sha256) de las hojas selladas de la autora sobre sus 100 de T. Es el
    código de leer_hojas_gold de la v1 (el que usa gold_v2.py) con la carpeta, el campo del acta, su sha256 y los lotes
    como parámetros. Abre por nombre hoja_<lote>.csv y sello_hoja_<lote>.txt, sin listar la carpeta, y controla el sello,
    la cabecera, el encabezado y los valores permitidos. Las filas no se controlan contra el lote del acta, que no es una
    entrada: el orden va de 1 en adelante, cada ref es una de las 100 de la entrada con su predicado, la clave no está
    vacía y ninguna ref está en dos hojas; entre todas, las 100. Solo salen `correcta` e `importancia`: ni la nota ni la
    observación de umbral."""
    out, shas = {}, {}
    for lote in lotes:
        hoja = Path(carpeta) / f"hoja_{lote}.csv"
        if not hoja.exists():
            raise SystemExit(f"FRENO: falta {hoja.name}")
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
        if len(filas) < 5:
            raise SystemExit(f"FRENO: {hoja.name} no trae la cabecera y el encabezado")
        cab = {f[0]: (f[1] if len(f) > 1 else "") for f in filas[:4]}
        if cab.get("hoja") != lote or cab.get(campo_acta) != sha256_acta:
            raise SystemExit(f"FRENO: la cabecera de {hoja.name} no es la de su lote y el acta de T")
        if tuple(filas[4][:len(AG.COLUMNAS_GOLD)]) != AG.COLUMNAS_GOLD:
            raise SystemExit(f"FRENO: el encabezado de {hoja.name} no es el del gold")
        cuerpo = [dict(zip(AG.COLUMNAS_GOLD, f + [""] * (len(AG.COLUMNAS_GOLD) - len(f)))) for f in filas[5:]]
        for i, r in enumerate(cuerpo, 1):
            if r["orden"] != str(i) or fichas_100.get(r["ref"]) != r["predicado"] or not r["clave"] or r["ref"] in out:
                raise SystemExit(f"FRENO: la fila {i} de {hoja.name} no es una de las 100 de la entrada, en su orden")
            c, imp = PJ.plegar(r["correcta"]), PJ.plegar(r["importancia"])
            if c not in AG.CORRECTA or imp not in AG.IMPORTANCIA:
                raise SystemExit(f"FRENO: la fila {r['orden']} de {hoja.name} tiene un valor no permitido")
            out[r["ref"]] = {"correcta": AG.CORRECTA[c], "importancia": AG.IMPORTANCIA[imp], "lote": lote}
        shas[hoja.name] = sha256(datos)
    if set(out) != set(fichas_100):
        raise SystemExit("FRENO: las hojas de la autora no traen las 100 de la entrada")
    return out, shas


def validar_adjudicaciones(d: dict, a_adjudicar: list[str], todas: set[str]) -> tuple[dict, list[str]]:
    """(ref -> {correcta, importancia} con los valores del gold, refs que faltan). Frena si trae una ref que la v2 no
    mandó a adjudicación o un valor no permitido."""
    if not isinstance(d, dict):
        raise SystemExit("FRENO: las adjudicaciones no son un objeto {ref: {correcta, importancia}}")
    otras = sorted(set(d) - set(a_adjudicar))
    if otras:
        raise SystemExit("FRENO: las adjudicaciones traen fichas que la v2 no manda a adjudicación"
                         + ("" if set(otras) <= todas else ", o que no son de la muestra"))
    out = {}
    for r, v in d.items():
        if not isinstance(v, dict) or set(v) != {"correcta", "importancia"}:
            raise SystemExit(f"FRENO: la adjudicación de {r} no trae exactamente correcta e importancia")
        c, imp = PJ.plegar(v["correcta"]), PJ.plegar(v["importancia"])
        if c not in AG.CORRECTA or imp not in AG.IMPORTANCIA:
            raise SystemExit(f"FRENO: la adjudicación de {r} tiene un valor no permitido")
        out[r] = {"correcta": AG.CORRECTA[c], "importancia": AG.IMPORTANCIA[imp]}
    return out, [r for r in a_adjudicar if r not in out]


# --------------------------------------------------------------------------- #
# La prueba (enmienda 4, punto 8; registro, §103)                             #
# --------------------------------------------------------------------------- #
def pares_de_la_prueba(entrada: dict, juez: dict, gold: dict) -> list[dict]:
    """Los pares de criterios() de la v1, uno por ficha de las 100. La clave `predicado` lleva el estrato."""
    f = entrada["fichas"]
    return [{"ref": r, "predicado": f[r]["estrato"], "predicado_de_la_ficha": f[r]["predicado"],
             "juez_veredicto": juez[r]["veredicto"], "juez_via": juez[r]["via"], "juez_importancia": juez[r]["importancia"],
             "autora_correcta": gold[r]["correcta"], "autora_importancia": gold[r]["importancia"]}
            for r in entrada["las_100"]]


def prueba(entrada: dict, juez: dict, gold: dict) -> dict:
    """El §4.6 sobre las 100 y, al lado, sin las de refs_coincidentes. Decide la de las 100."""
    if set(juez) != set(entrada["las_100"]) or set(gold) != set(entrada["las_100"]):
        raise SystemExit("FRENO: el agregado de la prueba y las hojas no traen las 100 de la entrada")
    pares = pares_de_la_prueba(entrada, juez, gold)
    con = AG.criterios(pares, entrada["W_h"])
    coinc = set(entrada["refs_coincidentes"])
    sin = AG.criterios([p for p in pares if p["ref"] not in coinc], entrada["W_h"])
    return {"rige": "las 100", "pasa": con["decision_46"], "con_las_100": con,
            "sin_las_coincidentes": {"refs": sorted(coinc), "fichas_que_salen": len(coinc), **sin},
            "misma_decision": con["decision_46"] == sin["decision_46"],
            "declaracion": None if con["decision_46"] == sin["decision_46"] else
            "Sin las coincidentes, la prueba da otra decisión del §4.6: se declara, y rige la de las 100."}


# --------------------------------------------------------------------------- #
# Los estimadores (§3.6; enmienda 2, §2; enmienda 3)                          #
# --------------------------------------------------------------------------- #
def cruda(k: int, n: int, wk) -> dict:
    """Correctas / decididas, con su Wilson al 95 %."""
    if n == 0:
        return {"k": 0, "n": 0, "fraccion": "0 de 0", "p": None, "wilson": None}
    return {"k": k, "n": n, "fraccion": f"{k} de {n}", "p": k / n, "wilson": list(wk.wilson(k / n, n))}


def ponderada(cuentas: dict[str, tuple[int, int]], n_h_grafo: dict[str, int], wk) -> dict:
    """p̂_w = Σ W_h p̂_h con W_h = N_h / N, y el Wilson con el n efectivo de Kish (wk.ponderada: los estratos con n_h < 5,
    agrupados para el intervalo). cuentas: estrato -> (k_h, n_h), las correctas y las decididas de la cifra. Un estrato del
    grafo sin ninguna decidida sale de la suma, los W_h de los demás se renormalizan, y se declara con su W_h y las dos
    cotas de la cifra (ese estrato con p_h = 0 o p_h = 1)."""
    N = sum(n_h_grafo.values())
    estratos = {}
    for h, N_h in n_h_grafo.items():
        k_h, n_h = cuentas.get(h, (0, 0))
        estratos[h] = {"N_h": N_h, "W_h": N_h / N, "k_h": k_h, "n_h": n_h, "fraccion": f"{k_h} de {n_h}",
                       "sin_muestra": n_h == 0, "agrupado_en_otros_para_el_intervalo": 0 < n_h < 5}
    con = [h for h, e in estratos.items() if e["n_h"] > 0]
    sin = [h for h, e in estratos.items() if e["n_h"] == 0 and e["N_h"] > 0]
    if not con:
        return {"p_w": None, "n_ef": None, "wilson": None, "estratos": estratos, "estratos_sin_muestra": sin,
                "cubre": f"0 de {N}", "cotas_por_los_estratos_sin_muestra": [0.0, 1.0]}
    r = wk.ponderada([{"N_h": estratos[h]["N_h"], "n_h": estratos[h]["n_h"], "k_h": estratos[h]["k_h"]} for h in con])
    inf = sum(estratos[h]["W_h"] * estratos[h]["k_h"] / estratos[h]["n_h"] for h in con)
    return {"p_w": r["p_w"], "n_ef": r["n_ef"], "wilson": list(r["wilson"]), "estratos": estratos,
            "estratos_sin_muestra": sin, "renormalizada": bool(sin),
            "cubre": f"{sum(estratos[h]['N_h'] for h in con)} de {N}",
            "cotas_por_los_estratos_sin_muestra": [inf, inf + sum(estratos[h]["W_h"] for h in sin)] if sin else None}


def cifra(filas: list[dict], n_h_grafo: dict[str, int], wk) -> dict:
    """La cruda y la ponderada de un conjunto de fichas, con las no decidibles aparte y sus dos cotas (todas correctas,
    todas incorrectas). filas: {estrato, correcta}, con correcta en correcta / incorrecta / None (no decidible)."""
    def cuentas(nd_como: str | None) -> dict[str, tuple[int, int]]:
        c = {}
        for f in filas:
            v = f["correcta"] if f["correcta"] is not None else nd_como
            if v is None:
                continue
            k, n = c.get(f["estrato"], (0, 0))
            c[f["estrato"]] = (k + (v == "correcta"), n + 1)
        return c

    dec = [f for f in filas if f["correcta"] is not None]
    k = sum(f["correcta"] == "correcta" for f in dec)
    nd = len(filas) - len(dec)
    out = {"fichas": len(filas), "decididas": len(dec), "cruda": cruda(k, len(dec), wk),
           "ponderada": ponderada(cuentas(None), n_h_grafo, wk), "no_decidibles": nd}
    if nd:
        out["cotas_de_las_no_decidibles"] = {
            "cruda": [k / len(filas), (k + nd) / len(filas)],
            "ponderada": [ponderada(cuentas("incorrecta"), n_h_grafo, wk)["p_w"],
                          ponderada(cuentas("correcta"), n_h_grafo, wk)["p_w"]]}
    return out


def por_grupo(filas: list[dict], clave: str, wk) -> dict:
    """Por predicado, por TO, por etapa o por procedencia: «k de n» de las decididas, con su proporción y Wilson solo
    donde n ≥ 20, y las no decidibles aparte."""
    out = {}
    for g in sorted({f[clave] for f in filas}):
        fg = [f for f in filas if f[clave] == g]
        dec = [f for f in fg if f["correcta"] is not None]
        k = sum(f["correcta"] == "correcta" for f in dec)
        out[g] = {"fraccion": f"{k} de {len(dec)}", "k": k, "n": len(dec), "no_decidibles": len(fg) - len(dec),
                  "p": k / len(dec) if len(dec) >= N_CON_WILSON else None,
                  "wilson": list(wk.wilson(k / len(dec), len(dec))) if len(dec) >= N_CON_WILSON else None}
    return out


def estimadores(filas: list[dict], entrada: dict, wk) -> dict:
    """Todas las cifras de 3.6 para T. filas: {ref, estrato, predicado, to, tanda0, etapa, chunk_id, estado_e3, correcta,
    esencial}, con esencial en True / False, o None si no hay una importancia válida (no entra en las esenciales)."""
    sin_t0 = [f for f in filas if not f["tanda0"]]

    def esenciales(fs):
        return [f for f in fs if f["esencial"] is True]

    def aplica_a(fs):
        dec = [f for f in fs if f["predicado"] == "aplica_a" and f["correcta"] is not None]
        nd = sum(f["predicado"] == "aplica_a" and f["correcta"] is None for f in fs)
        return {**cruda(sum(f["correcta"] == "correcta" for f in dec), len(dec), wk), "no_decidibles": nd}

    return {"todo": cifra(filas, entrada["N_h"], wk),
            "esenciales": cifra(esenciales(filas), entrada["N_h"], wk),
            "sin_tanda0": cifra(sin_t0, entrada["N_h_sin_tanda0"], wk),
            "esenciales_sin_tanda0": cifra(esenciales(sin_t0), entrada["N_h_sin_tanda0"], wk),
            "aplica_a": {"con_tanda0": aplica_a(filas), "sin_tanda0": aplica_a(sin_t0)},
            "por_predicado": por_grupo(filas, "predicado", wk), "por_to": por_grupo(filas, "to", wk),
            "por_etapa": por_grupo(filas, "etapa", wk), "por_estado_e3": por_grupo(filas, "estado_e3", wk),
            "por_chunk_id": por_grupo(filas, "chunk_id", wk),
            "sin_importancia_valida": sum(f["esencial"] is None for f in filas)}


def _fila(entrada: dict, r: str, correcta, esencial) -> dict:
    f = entrada["fichas"][r]
    return {"ref": r, "estrato": f["estrato"], "predicado": f["predicado"], "to": f["to"], "tanda0": f["tanda0"],
            "etapa": f["etapa"], "chunk_id": f["chunk_id"],
            "estado_e3": SIN_ESTADO_E3 if f["estado_e3"] is None else f["estado_e3"],
            "correcta": correcta, "esencial": esencial}


def a_adjudicacion(juez: dict) -> list[str]:
    """Las fichas que la v2 no decide (adjudicación o sin consenso): las adjudica la autora."""
    return sorted(r for r, v in juez.items() if J.dos_clases(v["veredicto"]) is None)


def medicion_400(entrada: dict, juez: dict, adjudicaciones: dict | None, wk, gold: dict) -> dict:
    """Si la prueba pasa (punto 9): la «correcta» y la importancia de la v2 en las que decide; en las que manda a
    adjudicación, las de la autora: en sus 100, las de su hoja sellada (`gold`), sin una adjudicación nueva; en las otras,
    su adjudicación. Sin todas las adjudicaciones de las otras, frena y dice cuántas y cuáles faltan."""
    pend = a_adjudicacion(juez)
    las_100 = set(entrada["las_100"])
    pend_100 = [r for r in pend if r in las_100]
    if set(adjudicaciones or {}) & set(pend_100):   # las que la v2 decide frenan abajo, como antes
        raise SystemExit("FRENO: las adjudicaciones traen fichas de las 100 de la autora que la v2 manda a adjudicación: en "
                         "esas cuenta su hoja sellada, sin una adjudicación nueva")
    adj, faltan = validar_adjudicaciones(adjudicaciones or {}, [r for r in pend if r not in las_100], set(entrada["fichas"]))
    base = {"etiqueta": ETIQUETA_400, "a_adjudicacion": len(pend), "proporcion_a_adjudicacion": len(pend) / len(juez),
            "refs_a_adjudicacion": pend, "a_adjudicacion_de_las_100_con_la_hoja": len(pend_100),
            "refs_a_adjudicacion_de_las_100_con_la_hoja": pend_100}
    if faltan:
        return {**base, "frena": True, "motivo": "faltan adjudicaciones de la autora", "faltan": len(faltan),
                "refs_que_faltan": faltan}
    filas = []
    for r in sorted(juez):
        v = J.dos_clases(juez[r]["veredicto"])
        if v is not None:
            imp = juez[r]["importancia"]
            filas.append(_fila(entrada, r, v, (imp == "esencial") if imp in AG.NIVEL else None))
        elif r in las_100:
            filas.append(_fila(entrada, r, gold[r]["correcta"], gold[r]["importancia"] == "esencial"))
        else:
            filas.append(_fila(entrada, r, adj[r]["correcta"], adj[r]["importancia"] == "esencial"))
    coinc = entrada["refs_coincidentes_400"]
    sin = {"refs": coinc, "fichas_que_salen": len(coinc)}
    if coinc:
        salen = set(coinc)
        sin.update(estimadores([f for f in filas if f["ref"] not in salen], entrada, wk))
    return {**base, "frena": False, **estimadores(filas, entrada, wk), "sin_las_coincidentes": sin}


def precision_con_las_100(entrada: dict, gold: dict, wk) -> dict:
    """Si la prueba no pasa (punto 10): los mismos estimadores con las marcas de la autora sobre sus 100."""
    filas = [_fila(entrada, r, gold[r]["correcta"], gold[r]["importancia"] == "esencial") for r in entrada["las_100"]]
    return {"etiqueta": ETIQUETA_100, **estimadores(filas, entrada, wk)}


def juez_de_las_400(entrada: dict, juez_100: dict, agregado_400: dict, casos: list[str]) -> dict:
    """Las 400 de la v2: las 100 de la prueba y el agregado de las restantes (o de las 400, igual en las 100)."""
    resto = leer_agregado(agregado_400, None, casos)
    for r, v in resto.items():
        if r in juez_100 and v != juez_100[r]:
            raise SystemExit("FRENO: el agregado de las 400 no da en las 100 lo mismo que el de la prueba")
    juez = {**resto, **juez_100}
    if set(juez) != set(entrada["fichas"]):
        raise SystemExit("FRENO: los dos agregados no traen exactamente las fichas de la muestra de T")
    return juez


def analizar(entrada_d: dict, agregado_prueba: dict | None, gold: dict, wk, agregado_400: dict | None = None,
             adjudicaciones: dict | None = None, no_completada: dict | None = None,
             restantes_no_completadas: dict | None = None) -> dict:
    entrada = validar_entrada(entrada_d)
    if restantes_no_completadas is not None:
        if no_completada is not None or agregado_prueba is None:
            raise SystemExit("FRENO: las restantes no completadas van con el agregado de una prueba completa, sin la "
                             "declaración de la prueba no completada")
        if agregado_400 is not None:
            raise SystemExit("FRENO: las restantes no completadas van en lugar del agregado de las 400, no al lado")
        decl_r = validar_no_completada(restantes_no_completadas, "restantes_400")
    if (agregado_prueba is None) == (no_completada is None):
        raise SystemExit("FRENO: va el agregado de la prueba o la declaración de la prueba no completada: uno de los dos")
    if no_completada is not None:      # punto 10: sin ningún agregado, la precisión con las 100 de la autora
        decl = validar_no_completada(no_completada)
        if set(gold) != set(entrada["las_100"]):
            raise SystemExit("FRENO: las hojas no traen las 100 de la entrada")
        return {"code_ver": CODE_VER, "decide": "la prueba no completada (enmienda 4, punto 10)", "pasa": False,
                "prueba": None, "prueba_no_completada": {"declaracion": decl}, "medicion_400": None,
                "precision_con_las_100_de_la_autora": precision_con_las_100(entrada, gold, wk),
                "ignorado": [n for n, x in (("agregado_400", agregado_400), ("adjudicaciones", adjudicaciones))
                             if x is not None]}
    casos = refs_casos_v2()
    juez_100 = leer_agregado(agregado_prueba, set(entrada["las_100"]), casos)
    p = prueba(entrada, juez_100, gold)
    out = {"code_ver": CODE_VER, "decide": "la prueba sobre las 100", "pasa": p["pasa"], "prueba": p,
           "medicion_400": None, "precision_con_las_100_de_la_autora": None, "ignorado": []}
    if restantes_no_completadas is not None:   # la prueba pasó y las 300 no se completaron: la T con las 100 de la autora
        if not p["pasa"]:
            raise SystemExit("FRENO: la prueba no pasa: no hay restantes, y la declaración de las 300 no va")
        out.update({"restantes_no_completadas": {"declaracion": decl_r},
                    "precision_con_las_100_de_la_autora": precision_con_las_100(entrada, gold, wk),
                    "precision_T_con_las_100_por": "restantes_no_completadas",
                    "sin_las_coincidentes_400": None,
                    "motivo_sin_las_coincidentes_400": "las 300 restantes no se completaron: no hay medición de las 400",
                    "ignorado": ["adjudicaciones"] if adjudicaciones is not None else []})
        return out
    if p["pasa"]:
        if agregado_400 is None:
            out["medicion_400"] = {"etiqueta": ETIQUETA_400, "frena": True, "motivo": "falta el agregado de las 400"}
        else:
            out["medicion_400"] = medicion_400(entrada, juez_de_las_400(entrada, juez_100, agregado_400, casos),
                                               adjudicaciones, wk, gold)
    else:
        out["precision_con_las_100_de_la_autora"] = precision_con_las_100(entrada, gold, wk)
        out["ignorado"] = [n for n, x in (("agregado_400", agregado_400), ("adjudicaciones", adjudicaciones))
                           if x is not None]
    return out


# --------------------------------------------------------------------------- #
# La corrida                                                                  #
# --------------------------------------------------------------------------- #
def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, required=True)
    ap.add_argument("--agregado-prueba", type=Path)
    ap.add_argument("--prueba-no-completada", type=Path)
    ap.add_argument("--hojas", type=Path, required=True)
    ap.add_argument("--sha256-acta", required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--agregado-400", type=Path)
    ap.add_argument("--restantes-no-completadas", type=Path)
    ap.add_argument("--adjudicaciones", type=Path)
    ap.add_argument("--lotes", default=",".join(LOTES_DEFECTO))
    ap.add_argument("--campo-acta", default=CAMPO_ACTA_T)
    ap.add_argument("--repo", type=Path, default=PJ.REPO_DEFECTO)
    return ap


def main(argv=None, consola=print) -> int:
    a = parser().parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{64}", a.sha256_acta):
        raise SystemExit("FRENO: --sha256-acta no es un sha256")
    if a.restantes_no_completadas is not None and (a.agregado_prueba is None or a.prueba_no_completada is not None
                                                   or a.agregado_400 is not None):
        raise SystemExit("FRENO: --restantes-no-completadas va con --agregado-prueba, sin --prueba-no-completada ni "
                         "--agregado-400")
    if (a.agregado_prueba is None) == (a.prueba_no_completada is None):
        raise SystemExit("FRENO: va --agregado-prueba o --prueba-no-completada: uno de los dos")
    ruta = a.salida / SALIDA_NOMBRE
    if ruta.exists():
        raise SystemExit(f"FRENO: {ruta} ya existe: no se pisa")
    wk = cargar_wk(a.repo)
    leidos = {"entrada": a.entrada, "agregado_prueba": a.agregado_prueba, "prueba_no_completada": a.prueba_no_completada,
              "agregado_400": a.agregado_400, "restantes_no_completadas": a.restantes_no_completadas,
              "adjudicaciones": a.adjudicaciones}
    b = {n: p.read_bytes() for n, p in leidos.items() if p is not None}
    datos = {n: json.loads(x) for n, x in b.items()}
    entrada = validar_entrada(datos["entrada"])
    gold, shas_hojas = leer_hojas_T(a.hojas, {r: entrada["fichas"][r]["predicado"] for r in entrada["las_100"]},
                                    sha256_acta=a.sha256_acta, campo_acta=a.campo_acta,
                                    lotes=tuple(x for x in a.lotes.split(",") if x))
    out = analizar(datos["entrada"], datos.get("agregado_prueba"), gold, wk, datos.get("agregado_400"),
                   datos.get("adjudicaciones"), datos.get("prueba_no_completada"), datos.get("restantes_no_completadas"))
    for n in ("prueba_no_completada", "restantes_no_completadas"):
        if n in out:
            out[n]["sha256"] = sha256(b[n])
    out["entradas_sha256"] = {**{n: sha256(x) for n, x in b.items()}, "hojas": shas_hojas,
                              "sha256_acta_de_las_hojas": a.sha256_acta}
    out["codigo_sha256"] = {"analisis_T_v2.py": sha256(Path(__file__).read_bytes()),
                            "wilson_kish_tripletas_mesa.py": WK_SHA256, "analisis_gold_juez_v.py (v1)":
                            sha256((PJ.CODIGO / "analisis_gold_juez_v.py").read_bytes())}
    a.salida.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    consola(f"análisis de la prueba del juez congelado sobre T: corrió | escribió {ruta}")
    m = out["medicion_400"]
    if m is not None and m["frena"]:
        consola("la medición de T con el juez congelado frena: falta su agregado o faltan adjudicaciones de la autora "
                "(cuántas y cuáles, en el JSON)")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
