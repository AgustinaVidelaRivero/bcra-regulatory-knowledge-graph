#!/usr/bin/env python3
"""analizar_b63.py — El análisis de B6.3 (etapa B del análisis: el código, probado con datos de juguete y sellado; corre sobre los datos
reales recién en la etapa C, después del sello de la planilla de la autora y de la revisión de la mesa). USD 0: no llama a ningún modelo,
no abre Neo4j ni el codificador y no escribe fuera de --salida.

Las reglas son las del pre-registro de B6.3 en HEAD (`docs/preregistro_B6_3_evaluacion_final.md`, `13440ecf…`), con sus notas al pie
firmadas: el §6 (las corridas cortadas y las fallas de infraestructura), el §8 (el análisis confirmatorio y lo de al lado) y el §9 (lo
exploratorio), más la nota de la lectura tolerante (`:886-913`, la regla 3 de las corridas sin veredicto) y las decisiones de la autora
del 29/10/2026 que cita el despacho de la etapa B.

Las entradas, cada una por argumento y controlada antes de leerla (su sha256 fijo abajo, o el de su sello o su manifiesto):
  - los veredictos de las 856: los agregados de la lectura tolerante aplicada (`969590df…`), que traen los de la estricta sin cambios y
    las 25 con sus tres lecturas; para lo declarado, las 25 salen de `agregados_de_las_que_no_se_leian_b63.json` (`6243d021…`) y las
    salidas leídas, de `veredictos_lectura_tolerante_b63.jsonl` (`e456ed14…`);
  - la adjudicación de la autora: la planilla, solo si da el sha256 y los bytes de su sello (`sello_adjudicacion_b63.txt`); su
    estructura (`f8265871…`); y la clave de la etapa A (`3628d5eb…`), que lleva cada ficha a su id opaco;
  - lo guardado de la corrida: el estado y las metas de `fuera_del_repo/banco_b63/`, cada archivo con el sha256 del manifiesto
    commiteado (`b63/real/manifiesto_fuera_resultados_y_juez_B63.json`, `9f609ddf…`); la entrada sellada (`32e2b18c…`) y sus preguntas
    (las de su sha256); el D-10 (`8422f3ba…`) y las fechas (`a47684f0…`) de `b63/real/`;
  - para el §8.2: la clasificación sellada de P1 (`23162803…`), su población y sus funciones (`b63_etapa1/`), la tabla sellada del
    cruce de los ext:: (`1147a2e0…`, con su sello) y la salida de la mesa con los pesos (`2838a6c1…`), que el código rehace y controla;
    y la lista de la cola del grafo evaluado, con el sha256 que se le pasa (PENDIENTE: no hay una lista sellada ubicada);
  - para el §9: la relevancia sellada (H-10, `a814b455…`), el kg.json del grafo evaluado (`576c9725…`) y su E0 (cada estructura con el
    sha256 de `armado_acumulado_128_tf.json`, `71a9a787…`), el material de los expertos (`b63_material_expertos/`, su manifest.txt
    `bc419ff3…`, y lo que haya en `devueltas/`) y el instrumento de la exactitud de cita (`scripts/ucita2_indicadores_banco.py`,
    `3a58e5be…`).

Lo que calcula (todo va al JSON de --salida, sin imprimirse):
  1. el veredicto de cada respuesta: el de los agregados; el de las adjudicadas, con los modales de los agregados y la marca de la autora
     en cada criterio que adjudicó («cumplido» da cumplido; «no cumplido» o «no_cumplido», no_cumplido), con mapping.veredicto_pregunta
     de HEAD, sin editarlo. Antes frena si los ids de la clave no son justo las requiere_adjudicacion de los agregados, si los criterios
     de la planilla no son justo los dudoso o sin_consenso de cada una, o si el modal de los demás criterios en la clave no es el de los
     agregados; después, si alguna sigue en requiere_adjudicacion. El brazo de cada respuesta sale del id opaco recalculado
     (juez_b63.caso_ciego), nunca de juez/desanonimizacion_SOLO_MESA/; el de la clave se controla contra ese;
  2. cada corrida: correcta si su veredicto de pregunta es «correcto». En el análisis principal, las cortadas y las 8 incompleta_otra
     cuentan como no correctas (§6 y la decisión de la autora); una falla de infraestructura sin terminar, también; una completa sin
     veredicto (la regla 3) sale. Las sensibilidades: sin las cortadas (y sin las incompleta_otra); con las sin veredicto como no
     correctas. Si una pregunta queda sin corridas en un brazo, sale de esa comparación;
  3. el §8.1: la métrica por pregunta (la proporción de sus corridas juzgadas correctas), d_q contra cada brazo de fragmentos, la prueba
     por permutación de signos (100.000, `B63:permutacion:v1`, p = (1 + las |media| mayores o iguales) / 100.001), Holm (0,025 y 0,05),
     el bootstrap percentil por pregunta (10.000, `B63:bootstrap:v1`) y la regla de la afirmación principal;
  4. el §8.2: el total ponderado (los pesos de P1 cruzados con el grafo evaluado, en su punto, en los extremos de su intervalo y con la
     herencia), por tipo (cada brazo y la comparación, con su intervalo) y los subtipos como casos; la hipótesis secundaria (la diferencia
     de d_q entre varios puntos y dato directo, de una cola, el percentil 5); la cifra aparte sin la cola y sin la unidad que falta, con
     cuántas salen por cada causa; y lo operativo por brazo y por tipo;
  5. el §8.3: la misma prueba con los signos por documento (`B63:permutacion:documento:v1`) y el intervalo de la secundaria con
     bootstrap por documento (`B63:bootstrap:documento:v1`);
  6. el §9: la relevancia por tercio (baja 1 y 2, media 3, alta 4 y 5: la decisión de la autora, registro §133) y ponderada por la nota;
     los nodos y las distancias; los expertos; y la exactitud de cita, en fracción cruda;
  7. lo declarado.

Las decisiones de implementación que el pre-registro no fija van declaradas en el JSON (`implementacion`).

  python3 -I -B analizar_b63.py --clon <b63/v2/b2 de una copia de HEAD> --entrada … (ver --help) --salida <carpeta nueva>
Imprime solo la ruta y el sha256 de la salida: ninguna cifra, ningún veredicto, ningún id de pregunta. Si algo inesperado falla,
imprime solo el tipo del error y su renglón en este archivo, sin su mensaje.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import io
import json
import math
import random
import re
import subprocess
import sys
import traceback
import unicodedata
from collections import Counter, deque
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BRAZO_GRAFO = "kg"
FRAGMENTOS = ("fragmentos_hibrida", "fragmentos_denso")
BRAZOS = (BRAZO_GRAFO,) + FRAGMENTOS
TIPOS = ("dato_directo", "varios_puntos")
UNIDAD_QUE_FALTA = "ri_transpa::Sbloque1::chapeau_seccion"
N_PERM, N_BOOT = 100_000, 10_000
SEMILLAS = {"permutacion": "B63:permutacion:v1", "bootstrap": "B63:bootstrap:v1",
            "permutacion_documento": "B63:permutacion:documento:v1", "bootstrap_documento": "B63:bootstrap:documento:v1"}
ALFA = (0.025, 0.05)
TERCIOS_RELEVANCIA = {1: "baja", 2: "baja", 3: "media", 4: "alta", 5: "alta"}

# Las entradas selladas (sha256 completos); la cola, PENDIENTE, va por argumento.
ESPERADO = {
    "agregados": "969590df059f88ffa22fefbbc1cc4a384d1dd0f0d0fcc97cb7adaaeb38a5e0e6",
    "agregados_tolerante": "6243d021984c7a580886042b6ae6173fe30f47eeeb05f1aa55fab0bce5882292",
    "veredictos_tolerante": "e456ed147584e5b5731967e3f0b6d1de21cfc4bd8edfdee516092118522ced38",
    "estructura_planilla": "f82658719537fd8f02d5bea492bf5fe3b0c8874a0c6d73b87272bcfb2b6de93f",
    "clave_adjudicacion": "3628d5eb0b8fbdcd54fd5004e3f551844399c17819c25310785417c4de46ea01",
    "entrada": "32e2b18cc2f5c96c67ed46d1f8b21af390d220a6f41b1102a47d3239c482bd54",
    "manifiesto_fuera": "9f609ddfa5bd457ba3db4de9a1dff0c6f4759b5cc410fe59b027ad533eadf1cf",
    "d10": "8422f3ba72e1218ef169111247b2031627fe9f382d3d5376d3777d4624adb800",
    "fechas": "a47684f05b395dbeb4c0abc69d528899c1b9cff303eb16f6b76676ab91194e7b",
    "clasificacion_P1": "23162803b04ed04c8a0191ee36fe827f8bc0a1da2a18b4d3874190d025f6a700",
    "poblacion_P1": "d43dff8ba62cabf392acb0770a249dd4194b871fdbc863e5aafb95687a8a72d6",
    "proporciones_P1": "9db5a4af13e72c0b275a4dac090b9057bcbcc4ad85ae8b56afc5516a6d7f6711",
    "sensibilidad_P1": "0bf82f60463730452ab522e7be2cf53f9e8419c99e9458b768030377fbe7937a",
    "tabla_cruce": "1147a2e07e0a8141d1a5a833feb4f81a2370fed12c0d54b6f2458d5ea3127d32",
    "sello_tabla": "f6e67f87d9a2969b9a8979e56c7139865c6b80db9a5c73b307c8408c9b7ef382",
    "pesos_mesa": "2838a6c1c16a43ab4a1677769b3fcf3eceb6cb2990c2d94686fcfa56df377eca",
    "relevancia": "a814b455e35a176c8d2fae5f303c578f59d56c704bdf1a48c58ca4b11b94875e",
    "kg": "576c97256185a0d5741cb2c35a2a85e91412f3e1119ad7a85d960b7d60c35ad3",
    "armado_e0": "71a9a78758b51f04b543dd14348b101e174abb4562ea3a37ebd0d86b9d791557",
    "manifiesto_expertos": "bc419ff30d007f7fbf0d1afc7e9bf27d146d2d45ef6b8c75708783a1e4b06893",
    "ucita": "3a58e5be33f2e7b1903c7c07ccfba00ef135f3b8da930f62490449577810e920",
    "mapping": "c905dd1a510925bad7a324722ff593ded09a95e77629e0a7e90fa13d5f3e6660",
    "juez_b63": "266dd6f0c3a4c6c0146a5d37657ff14826e93a4c5f2585711dd22f420ce094d2",
    "aplicar_lectura_tolerante_b63": "5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372",
}

DECLARADO = {
    "las_8_incompleta_otra": "Las 8 van como las cortadas del §6: en el análisis principal cuentan como no correctas, sin pasar por el "
                             "juez. La sensibilidad las saca, y si una pregunta queda sin corridas en un brazo, sale de esa comparación. "
                             "Se declaran por brazo y por motivo. (decisión de la autora del 29/10/2026, 09:54:22)",
    "la_llamada_que_falta": "La llamada que falta es la última de la sesión y pide mcp__kg, sin el nombre de ninguna herramienta: el agente "
                            "pidió una herramienta que no existe y el pedido no llegó al servidor. (decisión de la autora del 29/10/2026, "
                            "10:19:04)",
    "las_corridas_sin_veredicto": "Las que siguen sin veredicto después de la lectura tolerante van por la regla 3 de la nota al pie "
                                  "(docs/preregistro_B6_3_evaluacion_final.md:907-910): fuera del análisis principal; en la "
                                  "sensibilidad, como no correctas; listadas por brazo.",
    "el_cambio_de_P1_de_la_etapa_A": "Acepto el cambio de P1, hecho antes del sello y sin ninguna cifra: una fila de la caché por pedido "
                                     "distinto en lugar de una por respuesta, porque dos respuestas con el mismo pedido comparten fila. P1 "
                                     "sigue exigiendo que cada una de las 856 respuestas tenga la fila de su pedido. Se declara. (decisión "
                                     "de la autora del 29/10/2026, 11:23:04)",
    "la_numeracion_de_las_pruebas": "Acepto que conserve la numeración de las pruebas de N6: las que el despacho llamaba P2 y P3 son P4 y P6. "
                                    "(decisión de la autora del 29/10/2026, 11:23:04)",
}

IMPLEMENTACION = {
    "sorteos": "cada prueba y cada bootstrap empiezan un random.Random(semilla) propio; la permutación toma los signos de getrandbits(n), "
               "un bit por pregunta (o por documento) en su orden; el bootstrap toma n índices con randrange(n) por remuestreo sobre la "
               "lista de las preguntas en el orden de la entrada (o de los documentos, ordenados), y calcula todas sus cifras sobre el "
               "mismo remuestreo; los pesos del total ponderado quedan fijos en el bootstrap",
    "exactitud": "las proporciones van por seis veces su valor, en enteros (k = 3), para que la comparación de la permutación sea exacta",
    "percentil": "por rango: el valor de la posición ceil(q·B) de los B valores ordenados (q = 0,025 y 0,975; 0,05 en la secundaria); "
                 "un remuestreo sin preguntas para una cifra no entra en esa cifra, y se cuenta",
    "permutacion_por_documento": "el estadístico es la suma de los d_q de todas las preguntas; los signos se sortean por documento, sobre "
                                 "la suma de los d_q de sus preguntas",
    "subtipos": "los subtipos de varios puntos van como casos: por subtipo, cada pregunta con su proporción por brazo y su d_q, sin "
                "intervalos ni pruebas",
    "cola": "un ancla cae en la cola si su unidad está en la lista, o es una unidad de la lista con más precisión, o la contiene "
            "(su prefijo seguido de «.» o de «::»); lo mismo con la unidad que falta",
    "unidades_de_un_ancla": "un rango a..b son los hermanos de a a b en el árbol de la estructura de la E0 (si a y b tienen el mismo padre; "
                            "si no, a y b); una unidad con sufijo («::intro», «::rep1»…) es esa sola",
    "nodos_de_un_ancla": "los nodos del kg.json con alguna procedencia cuyo chunk_id, sin su sufijo, es la unidad o una de sus descendientes "
                         "en el árbol de la E0 (o empieza con la unidad seguida de «.»); para una unidad con sufijo, el chunk_id que es "
                         "esa unidad o empieza con ella seguida de «::»",
    "distancia_en_el_grafo": "el camino más corto, sin dirección, entre los nodos del ancla y los del otro punto: 0 si comparten un nodo; "
                             "«sin nodo» si alguna no tiene nodos; «sin camino» si no se tocan; las categorías: 0, 1, 2, «3 o más», "
                             "«sin nodo» y «sin camino»",
    "distancia_en_la_E0": "los pasos en el árbol de la estructura de la E0 del documento (secciones e hijos) entre las dos unidades; un "
                          "sufijo «::» o un nivel que la estructura no tiene suman un paso cada uno; con un rango, la menor de sus "
                          "unidades; «distinto documento» si no son del mismo; los tercios, por rango sobre las de varios puntos con "
                          "distancia: baja hasta el percentil 1/3, media hasta el 2/3, alta el resto",
    "relevancia_ponderada": "la media de la métrica (o de d_q) con la nota de P3 como peso",
    "expertos": "cada CSV de devueltas/ es un experto (su nombre de archivo); de cada columna de sí o no, la proporción de «sí» con su "
                "Wilson al 95 %, sobre las filas respondidas; el acuerdo con P3, la proporción de notas iguales y de puestos iguales; "
                "entre expertos, la proporción de respuestas iguales en cada par, por columna; «no respondible»: la mayoría de los "
                "que respondieron dice que no; con dos, los dos",
    "tope_de_llamadas": "más de 30 llamadas del log R1, y al tope (30 o más), las dos por brazo y por tipo",
    "contexto_maximo": "por sesión, el mayor input_tokens + cache_read_input_tokens + cache_creation_input_tokens de sus llamadas",
    "costo_por_pregunta": "la suma de tokens_R9.costo_recomputado.total_usd de las sesiones de la pregunta en el brazo",
    "exactitud_de_cita": "el instrumento corre aparte, con sus anclas, la E0 del grafo evaluado y el mapa de las sesiones, sobre copias de "
                         "meta_<id>.json y log_r1_<id>.jsonl de cada sesión (controladas contra el manifiesto), sin enlaces; su consola "
                         "va a un archivo; si no termina bien, el resto del análisis se escribe igual y la corrida sale con 11",
}


class Freno(Exception):
    pass


def frena(m: str):
    raise Freno(m)


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(p: Path) -> str:
    return sha_b(Path(p).read_bytes())


def controlado(p: Path, esperado: str | None, nombre: str) -> bytes:
    b = Path(p).read_bytes()
    if esperado is None or sha_b(b) != esperado:
        frena(f"{nombre} no da su sha256")
    return b


def veda(n: str) -> bool:
    return "_SOLO_MESA" in n or n.startswith("NO_ABRIR_")


def plegar(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").replace("_", " ").split())


def wilson(x: int, n: int, z: float = 1.959963984540054) -> dict:
    if n == 0:
        return {"x": 0, "n": 0, "p": None, "lo": None, "hi": None}
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"x": x, "n": n, "p": p, "lo": max(0.0, c - h), "hi": min(1.0, c + h)}


def percentil(vals: list, q: float):
    if not vals:
        return None
    s = sorted(vals)
    return s[max(0, math.ceil(q * len(s)) - 1)]


def por_clave(xs) -> dict:
    return dict(sorted(Counter(xs).items()))


# --------------------------------------------------------------------------------------------------------------------- #
# Las entradas                                                                                                          #
# --------------------------------------------------------------------------------------------------------------------- #
def importar(clon: Path, esperado: dict):
    clon = Path(clon).resolve()
    for p in (str(AQUI), str(clon), str(clon.parents[2])):
        if p not in sys.path:
            sys.path.insert(0, p)
    import aplicar_lectura_tolerante_b63 as AP   # noqa: PLC0415  (cargar_entrada y casos_de_b63, sellados en la etapa A)
    import juez_b63 as JB                        # noqa: PLC0415
    for nombre, mod in (("aplicar_lectura_tolerante_b63", AP), ("juez_b63", JB), ("mapping", JB.M)):
        if sha(Path(mod.__file__)) != esperado[nombre]:
            frena(f"{nombre}.py no es el de su sha256")
    return AP, JB


class Banco:
    """Los archivos de banco_b63/ que se leen, cada uno contra el manifiesto commiteado (sus rutas empiezan con banco_b63/)."""

    def __init__(self, b63: Path, manifiesto: Path, esperado: dict):
        self.b63 = Path(b63).resolve()
        m = json.loads(controlado(manifiesto, esperado["manifiesto_fuera"], "el manifiesto de banco_b63"))
        self.sha = {a["ruta"]: a["sha256"] for a in m["archivos"] if a.get("sha256")}
        self.raiz = self.b63.parent
        self.leidos: set = set()

    def sesion(self, c: dict) -> Path:
        return self.b63 / "resultados" / "real" / c["salida"].rsplit("/", 1)[0] / c["sesion"]

    def leer(self, p: Path) -> bytes:
        rel = str(Path(p).resolve().relative_to(self.raiz))
        if any(veda(x) for x in Path(rel).parts):
            frena("una ruta vedada por nombre")
        b = Path(p).read_bytes()
        if self.sha.get(rel) != sha_b(b):
            frena("un archivo de banco_b63 no da el sha256 de su manifiesto")
        self.leidos.add(rel)
        return b


def cargar_preguntas_crudas(e: dict) -> dict:
    d = json.loads(Path(e["_rutas"]["preguntas"]).read_bytes())
    return {q["id"]: q for q in d["preguntas"]}


def corridas_de(banco: Banco, e: dict, K, JB, AP) -> list[dict]:
    """Una por (pregunta, repetición, brazo), del estado: su clasificación final, su sesión, sus intentos y, si es completa, su id opaco
    (AP.casos_de_b63, el caso que vio el juez), con la meta de cada completa controlada antes contra el manifiesto."""
    st = json.loads(banco.leer(banco.b63 / "resultados" / "real" / "estado_b63.json"))
    for blq in st["bloques"].values():
        for f in blq["final"].values():
            if f.get("clasificacion") == "completa":
                banco.leer(banco.sesion({"salida": f["salida"], "sesion": f["id"]}) / f"meta_{f['id']}.json")
    casos = {(c["qid"], c["r"], c["brazo"]): c for c in AP.casos_de_b63(banco.b63, e, K, JB)}
    out = []
    for b in K.orden_bloques(e["preguntas"]["ids_en_orden"], e["k"], sorted(e["brazos"])):
        blq = st["bloques"][b["bloque"]]
        for x in sorted(e["brazos"]):
            f = blq["final"][x]
            c = casos.get((b["qid"], b["r"], x))
            if (c is not None) != (f.get("clasificacion") == "completa"):
                frena("los casos rehechos no son justo las corridas completas")
            out.append({"qid": b["qid"], "r": b["r"], "brazo": x, "sesion": f["id"], "clasificacion": f.get("clasificacion"),
                        "salida": f.get("salida"), "intentos": (blq.get("intentos_por_brazo") or {}).get(x),
                        "id_opaco": c["id_opaco"] if c else None})
    if len(out) != len(e["preguntas"]["ids_en_orden"]) * e["k"] * len(e["brazos"]):
        frena("las corridas no son las de la entrada")
    return out


# --------------------------------------------------------------------------------------------------------------------- #
# La adjudicación                                                                                                       #
# --------------------------------------------------------------------------------------------------------------------- #
def leer_csv(b: bytes) -> tuple[list[str], list[list[str]]]:
    """Como el sellador de la planilla: acepta «,» o «;» y el BOM."""
    t = b.decode("utf-8-sig")
    pr = t.splitlines()[0] if t else ""
    d = ";" if pr.count(";") > pr.count(",") else ","
    filas = [f for f in csv.reader(io.StringIO(t), delimiter=d) if any(x.strip() for x in f)]
    if not filas:
        frena("un CSV vacío")
    return [c.strip() for c in filas[0]], [[c.strip() for c in f] for f in filas[1:]]


def planilla_sellada(planilla: Path, sello: Path) -> bytes:
    """La planilla, solo si da el sha256 y los bytes que su sello registra (el renglón «sha256  bytes  hora  nombre»)."""
    b = Path(planilla).read_bytes()
    lineas = [l for l in Path(sello).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    reg = [l.split() for l in lineas if l.split()[-1] == Path(planilla).name]
    if len(reg) != 1 or reg[0][0] != sha_b(b) or reg[0][1] != str(len(b)):
        frena("la planilla no da el sha256 y los bytes de su sello")
    return b


def marca(v: str) -> str:
    p = plegar(v)
    if p == "cumplido":
        return "cumplido"
    if p == "no cumplido":
        return "no_cumplido"
    frena("una marca de la planilla no es cumplido ni no cumplido")


def adjudicar(agregados: dict, planilla_b: bytes, estructura_b: bytes, clave: dict, M, corrida_de: dict) -> dict:
    """{id_opaco: {veredicto_pregunta, modales, ficha}} de las adjudicadas, con los frenos de antes."""
    est = json.loads(estructura_b)
    cols, filas = leer_csv(planilla_b)
    if cols != est["columnas"] or [f[:2] for f in filas] != est["renglones"]:
        frena("la planilla no tiene las columnas y los renglones de su estructura")
    requiere = {i for i, a in agregados.items() if a["veredicto_pregunta"] == "requiere_adjudicacion"}
    por_ficha = {f["ficha"]: f for f in clave["fichas"]}
    ids_clave = [f["id_opaco"] for f in clave["fichas"]]
    if set(ids_clave) != requiere or len(set(ids_clave)) != len(ids_clave) or len(por_ficha) != len(clave["fichas"]):
        frena("los ids de la clave no son justo las requiere_adjudicacion de los agregados")
    for f in clave["fichas"]:
        c = corrida_de[f["id_opaco"]]
        if (f.get("brazo"), f.get("pregunta"), f.get("repeticion")) != (c["brazo"], c["qid"], c["r"]):
            frena("la clave no da el brazo, la pregunta o la repetición del id opaco recalculado")
    marcas: dict = {}
    for f in filas:
        r = dict(zip(cols, f + [""] * (len(cols) - len(f))))
        if r["ficha"] not in por_ficha:
            frena("una ficha de la planilla no está en la clave")
        marcas.setdefault(por_ficha[r["ficha"]]["id_opaco"], {})[int(r["criterio"])] = marca(r[cols[2]])
    out = {}
    for ficha, f in sorted(por_ficha.items()):
        a = agregados[f["id_opaco"]]
        dudosos = [k for k, m in enumerate(a["modales"], 1) if m in ("dudoso", "sin_consenso")]
        if sorted(marcas.get(f["id_opaco"], {})) != dudosos or sorted(f["criterios_que_se_adjudican"]) != dudosos:
            frena("los criterios de la planilla no son justo los dudoso o sin_consenso de cada una")
        demas = {str(k): m for k, m in enumerate(a["modales"], 1) if k not in dudosos}
        if f["modal_del_juez_de_los_demas"] != demas:
            frena("el modal de los demás criterios en la clave no es el de los agregados")
        modales = [marcas[f["id_opaco"]][k] if k in dudosos else m for k, m in enumerate(a["modales"], 1)]
        out[f["id_opaco"]] = {"veredicto_pregunta": M.veredicto_pregunta(modales), "modales": modales, "ficha": ficha}
    return out


def sin_requiere(veredictos: dict) -> None:
    if any(v["veredicto_pregunta"] == "requiere_adjudicacion" for v in veredictos.values()):
        frena("después de la adjudicación, una respuesta sigue en requiere_adjudicacion")


# --------------------------------------------------------------------------------------------------------------------- #
# Las corridas y la métrica                                                                                             #
# --------------------------------------------------------------------------------------------------------------------- #
def estado_de(c: dict, veredictos: dict) -> str:
    cl = c["clasificacion"]
    if cl == "completa":
        v = veredictos.get(c["id_opaco"])
        if v is None:
            return "sin_veredicto"
        return "correcta" if v["veredicto_pregunta"] == "correcto" else "no_correcta"
    if cl in ("cortada", "incompleta_otra"):
        return cl
    if cl == "falla_infra_sin_terminar":
        return "infra_sin_terminar"
    frena("una corrida con una clasificación final que el análisis no conoce")


ESCENARIOS = {
    # estado → (cuenta, correcta); None: sale
    "principal": {"correcta": (1, 1), "no_correcta": (1, 0), "cortada": (1, 0), "incompleta_otra": (1, 0),
                  "infra_sin_terminar": (1, 0), "sin_veredicto": None},
    "sin_las_cortadas": {"correcta": (1, 1), "no_correcta": (1, 0), "cortada": None, "incompleta_otra": None,
                         "infra_sin_terminar": (1, 0), "sin_veredicto": None},
    "sin_veredicto_como_no_correctas": {"correcta": (1, 1), "no_correcta": (1, 0), "cortada": (1, 0), "incompleta_otra": (1, 0),
                                        "infra_sin_terminar": (1, 0), "sin_veredicto": (1, 0)},
}


def metricas(corridas: list[dict], escenario: str) -> dict:
    """{(qid, brazo): (correctas, contadas)} con las reglas del escenario; sin la entrada si no quedó ninguna contada."""
    reg = ESCENARIOS[escenario]
    acc: dict = {}
    for c in corridas:
        v = reg[c["estado"]]
        if v is None:
            continue
        n, x = acc.get((c["qid"], c["brazo"]), (0, 0))
        acc[(c["qid"], c["brazo"])] = (n + v[0], x + v[1])
    return {k: (x, n) for k, (n, x) in acc.items() if n}


def seis(x: int, n: int) -> int:
    v = 6 * x
    if v % n:
        frena("una proporción que no es un múltiplo de 1/6")
    return v // n


def preguntas_de(qids: list[str], m: dict, brazos: tuple) -> list[str]:
    return [q for q in qids if all((q, b) in m for b in brazos)]


def d6(m: dict, q: str, f: str) -> int:
    return seis(*m[(q, BRAZO_GRAFO)]) - seis(*m[(q, f)])


def _media(v6: list[int]) -> dict:
    return {"n": len(v6), "media": (sum(v6) / 6 / len(v6)) if v6 else None}


def _pond(pares: list[tuple[int, int]]) -> dict:
    sw = sum(w for _, w in pares)
    return {"n": len(pares), "valor": (sum(v * w for v, w in pares) / 6 / sw) if sw else None}


# --------------------------------------------------------------------------------------------------------------------- #
# Las pruebas                                                                                                           #
# --------------------------------------------------------------------------------------------------------------------- #
def permutacion(valores: list[int], semilla: str, n_perm: int) -> dict:
    """La permutación de signos sobre la suma (en sextos) de los valores: p = (1 + las |suma| ≥ la observada) / (n_perm + 1)."""
    rng = random.Random(semilla)
    obs = abs(sum(valores))
    n = len(valores)
    ge = 0
    for _ in range(n_perm):
        bits = rng.getrandbits(n) if n else 0
        s = 0
        for i, v in enumerate(valores):
            s += v if (bits >> i) & 1 else -v
        ge += abs(s) >= obs
    return {"n": n, "media": (sum(valores) / 6 / n) if n else None, "mayores_o_iguales": ge, "p": (1 + ge) / (n_perm + 1)}


def holm(ps: dict) -> dict:
    orden = sorted(ps, key=lambda k: (ps[k], k))
    out, sigue = {}, True
    for k, a in zip(orden, ALFA):
        rech = sigue and ps[k] <= a
        out[k] = {"p": ps[k], "umbral": a, "rechaza": rech}
        sigue = rech
    return out


def afirmacion(h: dict, medias: dict) -> dict:
    a_favor = {f: h[f]["rechaza"] and (medias[f] or 0) > 0 for f in sorted(h)}
    if all(a_favor.values()):
        return {"el_grafo_supera_a_los_fragmentos": True, "por_configuracion": a_favor}
    return {"el_grafo_supera_a_los_fragmentos": False, "por_configuracion": a_favor,
            "regla": "supera a una sola o a ninguna: se informa por configuración, sin la afirmación general"}


class Estadisticas:
    """Las cifras de un remuestreo (o de la muestra): medias por brazo y por tipo, d por comparación y por tipo, el total ponderado y la
    secundaria."""

    def __init__(self, P: dict, pesos: dict):
        self.P, self.pesos = P, pesos

    def calcular(self, qs: list[str], m: dict) -> dict:
        out = {}
        tipos = {t: [q for q in qs if self.P[q]["tipo"] == t] for t in TIPOS}
        for b in BRAZOS:
            vs = [seis(*m[(q, b)]) for q in qs if (q, b) in m]
            out[f"media|{b}"] = sum(vs) / 6 / len(vs) if vs else None
            for t, tq in tipos.items():
                vt = [seis(*m[(q, b)]) for q in tq if (q, b) in m]
                out[f"media|{b}|{t}"] = sum(vt) / 6 / len(vt) if vt else None
            a, c = out[f"media|{b}|varios_puntos"], out[f"media|{b}|dato_directo"]
            for nombre, w in self.pesos.items():
                out[f"ponderado|{nombre}|{b}"] = None if a is None or c is None else w * a + (1 - w) * c
        for f in FRAGMENTOS:
            ds = [d6(m, q, f) for q in qs if (q, BRAZO_GRAFO) in m and (q, f) in m]
            out[f"d|{f}"] = sum(ds) / 6 / len(ds) if ds else None
            dt = {}
            for t, tq in tipos.items():
                v = [d6(m, q, f) for q in tq if (q, BRAZO_GRAFO) in m and (q, f) in m]
                dt[t] = sum(v) / 6 / len(v) if v else None
                out[f"d|{f}|{t}"] = dt[t]
            out[f"secundaria|{f}"] = None if None in dt.values() else dt["varios_puntos"] - dt["dato_directo"]
            for nombre, w in self.pesos.items():
                out[f"ponderado|{nombre}|d|{f}"] = None if None in dt.values() else w * dt["varios_puntos"] + (1 - w) * dt["dato_directo"]
        return out


def bootstrap(unidades: list, expandir_u, est: Estadisticas, m: dict, semilla: str, n_boot: int, cuantiles: dict) -> dict:
    """El bootstrap percentil: remuestrea las unidades (preguntas o documentos) con randrange; cada cifra, por rango."""
    rng = random.Random(semilla)
    n = len(unidades)
    acum: dict = {}
    for _ in range(n_boot):
        qs = [q for _ in range(n) for q in expandir_u(unidades[rng.randrange(n)])] if n else []
        for k, v in est.calcular(qs, m).items():
            acum.setdefault(k, []).append(v)
    out = {}
    for k, vs in acum.items():
        ok = [v for v in vs if v is not None]
        out[k] = {nombre: percentil(ok, q) for nombre, q in cuantiles.items()} | {"remuestreos_sin_cifra": len(vs) - len(ok)}
    return out


def intervalo(boot: dict, k: str) -> list:
    return [boot[k]["p2_5"], boot[k]["p97_5"]] if k in boot else [None, None]


def subtipos_como_casos(qids: list[str], m: dict, P: dict) -> dict:
    out: dict = {}
    for q in qids:
        if P[q]["tipo"] != "varios_puntos":
            continue
        caso = {"id": q, "por_brazo": {b: (seis(*m[(q, b)]) / 6 if (q, b) in m else None) for b in BRAZOS},
                "d": {f: (d6(m, q, f) / 6 if (q, BRAZO_GRAFO) in m and (q, f) in m else None) for f in FRAGMENTOS}}
        s = out.setdefault(str(P[q].get("subtipo")), {"preguntas": 0, "casos": []})
        s["preguntas"] += 1
        s["casos"].append(caso)
    return dict(sorted(out.items()))


def confirmatorio(qids: list[str], m: dict, P: dict, pesos: dict, n_perm: int, n_boot: int, por_documento: bool = True) -> dict:
    """El §8.1, el §8.2 (sin lo operativo ni la cifra aparte) y, con por_documento, el §8.3, sobre una métrica."""
    est = Estadisticas(P, pesos)
    puntual = est.calcular(qids, m)
    pruebas, medias = {}, {}
    for f in FRAGMENTOS:
        qs = preguntas_de(qids, m, (BRAZO_GRAFO, f))
        pruebas[f] = permutacion([d6(m, q, f) for q in qs], SEMILLAS["permutacion"], n_perm)
        medias[f] = pruebas[f]["media"]
    h = holm({f: pruebas[f]["p"] for f in FRAGMENTOS})
    boot = bootstrap(qids, lambda q: [q], est, m, SEMILLAS["bootstrap"], n_boot, {"p2_5": 0.025, "p97_5": 0.975, "p5": 0.05})
    out = {"preguntas": len(qids),
           "preguntas_que_salen_por_comparacion": {f: len(qids) - pruebas[f]["n"] for f in FRAGMENTOS},
           "por_comparacion": {f: {"preguntas": pruebas[f]["n"], "media_d": medias[f], "permutacion": pruebas[f], "holm": h[f],
                                   "intervalo_95": intervalo(boot, f"d|{f}")} for f in FRAGMENTOS},
           "afirmacion_principal": afirmacion(h, medias),
           "por_brazo": {b: {"media": puntual[f"media|{b}"], "intervalo_95": intervalo(boot, f"media|{b}")} for b in BRAZOS},
           "por_tipo": {t: {"preguntas": sum(1 for q in qids if P[q]["tipo"] == t),
                            "por_brazo": {b: {"media": puntual[f"media|{b}|{t}"], "intervalo_95": intervalo(boot, f"media|{b}|{t}")}
                                          for b in BRAZOS},
                            "por_comparacion": {f: {"media_d": puntual[f"d|{f}|{t}"], "intervalo_95": intervalo(boot, f"d|{f}|{t}")}
                                                for f in FRAGMENTOS}}
                        for t in TIPOS},
           "subtipos_como_casos": subtipos_como_casos(qids, m, P),
           "total_ponderado": {nombre: {"peso_varios_puntos": w,
                                        "por_brazo": {b: {"valor": puntual[f"ponderado|{nombre}|{b}"],
                                                          "intervalo_95": intervalo(boot, f"ponderado|{nombre}|{b}")} for b in BRAZOS},
                                        "por_comparacion": {f: {"valor": puntual[f"ponderado|{nombre}|d|{f}"],
                                                                "intervalo_95": intervalo(boot, f"ponderado|{nombre}|d|{f}")}
                                                            for f in FRAGMENTOS}}
                               for nombre, w in pesos.items()},
           "secundaria": {f: {"diferencia": puntual[f"secundaria|{f}"], "percentil_5": boot[f"secundaria|{f}"]["p5"],
                              "a_favor_del_grafo_en_varios_puntos": (boot[f"secundaria|{f}"]["p5"] or 0) > 0}
                          for f in FRAGMENTOS},
           "remuestreos_sin_cifra": {k: v["remuestreos_sin_cifra"] for k, v in sorted(boot.items()) if v["remuestreos_sin_cifra"]}}
    if por_documento:
        docs = sorted({P[q]["to"] for q in qids})
        de_doc = {d: [q for q in qids if P[q]["to"] == d] for d in docs}
        pd = {}
        for f in FRAGMENTOS:
            sumas = [sum(d6(m, q, f) for q in de_doc[d] if (q, BRAZO_GRAFO) in m and (q, f) in m) for d in docs]
            qs = preguntas_de(qids, m, (BRAZO_GRAFO, f))
            r = permutacion(sumas, SEMILLAS["permutacion_documento"], n_perm)
            r["media"] = (sum(sumas) / 6 / len(qs)) if qs else None
            r["documentos"], r["preguntas"] = len(docs), len(qs)
            pd[f] = r
        hd = holm({f: pd[f]["p"] for f in FRAGMENTOS})
        bd = bootstrap(docs, lambda d: de_doc[d], est, m, SEMILLAS["bootstrap_documento"], n_boot, {"p5": 0.05})
        sec = {f: {"percentil_5": bd[f"secundaria|{f}"]["p5"], "a_favor_del_grafo_en_varios_puntos": (bd[f"secundaria|{f}"]["p5"] or 0) > 0,
                   "remuestreos_sin_cifra": bd[f"secundaria|{f}"]["remuestreos_sin_cifra"]}
               for f in FRAGMENTOS}
        out["por_documento"] = {"documentos": len(docs),
                                "por_comparacion": {f: {"permutacion": pd[f], "holm": hd[f]} for f in FRAGMENTOS},
                                "afirmacion_principal": afirmacion(hd, {f: pd[f]["media"] for f in FRAGMENTOS}),
                                "secundaria": sec,
                                "la_misma_conclusion": {"principal": {f: hd[f]["rechaza"] == h[f]["rechaza"] for f in FRAGMENTOS},
                                                        "secundaria": {f: sec[f]["a_favor_del_grafo_en_varios_puntos"]
                                                                       == out["secundaria"][f]["a_favor_del_grafo_en_varios_puntos"]
                                                                       for f in FRAGMENTOS}}}
    return out


# --------------------------------------------------------------------------------------------------------------------- #
# Los pesos (el §8.2), rehechos desde P1 y la tabla sellada, y controlados contra la salida de la mesa                 #
# --------------------------------------------------------------------------------------------------------------------- #
def pesos_de_P1(etapa1: Path, tabla: Path, sello: Path, pesos_mesa: Path, esperado: dict) -> dict:
    etapa1 = Path(etapa1)
    cb = controlado(etapa1 / "clasificacion_P1.csv", esperado["clasificacion_P1"], "la clasificación de P1")
    pb = controlado(etapa1 / "poblacion_P1.json", esperado["poblacion_P1"], "la población de P1")
    controlado(etapa1 / "scripts" / "proporciones_P1.py", esperado["proporciones_P1"], "proporciones_P1.py")
    controlado(etapa1 / "scripts" / "sensibilidad_P1.py", esperado["sensibilidad_P1"], "sensibilidad_P1.py")
    tb = controlado(tabla, esperado["tabla_cruce"], "la tabla del cruce")
    sb = controlado(sello, esperado["sello_tabla"], "el sello de la tabla")
    if f"sha256: {sha_b(tb)}" not in sb.decode("utf-8"):
        frena("la tabla del cruce no es la de su sello")
    mesa = json.loads(controlado(pesos_mesa, esperado["pesos_mesa"], "la salida de los pesos de la mesa"))
    for n in ("proporciones_P1", "sensibilidad_P1"):
        sys.modules.pop(n, None)
    sys.path.insert(0, str(etapa1 / "scripts"))
    try:
        PR = importlib.import_module("proporciones_P1")
        SE = importlib.import_module("sensibilidad_P1")
    finally:
        for p in {str(etapa1 / "scripts"), str((etapa1 / "scripts").resolve())}:
            while p in sys.path:
                sys.path.remove(p)
        for n in ("proporciones_P1", "sensibilidad_P1"):
            sys.modules.pop(n, None)
    T = json.loads(tb)["normas"]
    filas = list(csv.DictReader(io.StringIO(cb.decode("utf-8"))))
    pob = json.loads(pb)
    N = {c: sum(1 for x in pob if x["clase"] == c) for c in PR.CLASES}

    def norma(v):            # la de decisiones_182_mesa/cruce/aplicar_cruce_ext_mesa.py, tal cual
        v = re.sub(r"\s*\(.*?\)\s*", " ", v)
        v = re.sub(r"\s+(Secci[oó]n\s+\d+|art\.\s*[\d\w ]+|\d+(\.\d+)*(\.\.\d+(\.\d+)*)?|\d+/\d+)\s*$", "", v.strip())
        return re.sub(r"\s+", " ", v).strip()

    def partes(op):
        return [p.strip() for p in re.split(r"[;|]", op or "") if p.strip()]

    for f in filas:
        for p in partes(f["otro_punto"]):
            if p.startswith("ext::") and norma(p[5:]) not in T:
                frena("un valor ext:: de P1 sin su norma en la tabla")

    def dentro(f):
        return any((not p.startswith("ext::")) or T[norma(p[5:])]["lado"] == "dentro" for p in partes(f["otro_punto"]))

    dec = [f for f in filas if f["tipo"] != "no decidible"]

    def vp(f):
        return f["tipo"] == "varios puntos"

    def esc(vp_in, vp_ext):
        n_dec = {c: sum(1 for f in dec if f["clase"] == c) for c in PR.CLASES}
        w = {c: N[c] / n_dec[c] for c in PR.CLASES}
        dos = [f for f in dec if not vp_ext(f)]
        n2 = {c: sum(1 for f in dos if f["clase"] == c) for c in PR.CLASES}
        w2 = {c: N[c] / n2[c] for c in PR.CLASES}
        return {"varios_puntos_dentro": PR.ponderada(dec, vp_in, w), "depende_de_fuera": PR.ponderada(dec, vp_ext, w),
                "peso_varios_puntos_sobre_las_dos_primeras": PR.ponderada(dos, vp_in, w2)}

    her = set(SE.SOLO_HERENCIA)
    sellada = esc(lambda f: vp(f) and dentro(f), lambda f: vp(f) and not dentro(f))
    herencia = esc(lambda f: vp(f) and dentro(f) and f["unidad"] not in her, lambda f: vp(f) and not dentro(f) and f["unidad"] not in her)
    for nombre, r in (("sellada", sellada), ("herencia", herencia)):
        for k, v in r.items():
            if any(abs(v[x] - mesa[nombre][k][x]) > 1e-12 for x in ("p", "lo", "hi", "n_ef")) or v["n"] != mesa[nombre][k]["n"]:
                frena("los pesos rehechos no dan los de la salida de la mesa")
    s = sellada["peso_varios_puntos_sobre_las_dos_primeras"]
    return {"pesos": {"sellada": s["p"], "extremo_bajo": s["lo"], "extremo_alto": s["hi"],
                      "herencia": herencia["peso_varios_puntos_sobre_las_dos_primeras"]["p"]},
            "detalle": {"sellada": sellada, "herencia": herencia}, "iguales_a_los_de_la_mesa": True}


# --------------------------------------------------------------------------------------------------------------------- #
# La cifra aparte, lo operativo y lo declarado                                                                          #
# --------------------------------------------------------------------------------------------------------------------- #
def relacionadas(u: str, v: str) -> bool:
    return u == v or u.startswith(v + ".") or u.startswith(v + "::") or v.startswith(u + ".") or v.startswith(u + "::")


def sin_la_cola(qids: list[str], P: dict, cola: set) -> dict:
    causas = {}
    for q in qids:
        us = [a["unidad"] for a in P[q]["anclas"]]
        c = {"cola": any(relacionadas(u, x) for u in us for x in cola), "unidad_que_falta": any(relacionadas(u, UNIDAD_QUE_FALTA) for u in us)}
        if any(c.values()):
            causas[q] = c
    return {"salen": sorted(causas), "por_causa": {"cola": sum(c["cola"] for c in causas.values()),
                                                   "unidad_que_falta": sum(c["unidad_que_falta"] for c in causas.values()),
                                                   "las_dos": sum(all(c.values()) for c in causas.values()), "total": len(causas)}}


def meta_sin_texto(banco: Banco, c: dict) -> dict | None:
    if not c["salida"]:
        return None
    p = banco.sesion(c) / f"meta_sin_texto_{c['sesion']}.json"
    return json.loads(banco.leer(p)) if p.is_file() else None


def operativo(corridas: list[dict], banco: Banco, P: dict) -> dict:
    filas = []
    for c in corridas:
        meta = meta_sin_texto(banco, c) or {}
        n = (meta.get("hb2") or {}).get("n_llamadas_log_r1")
        llam = (meta.get("tokens_R9") or {}).get("por_llamada_api") or []
        ctx = max((int(x.get("input_tokens") or 0) + int(x.get("cache_read_input_tokens") or 0) + int(x.get("cache_creation_input_tokens") or 0)
                   for x in llam), default=None)
        costo = ((meta.get("tokens_R9") or {}).get("costo_recomputado") or {}).get("total_usd")
        filas.append({"qid": c["qid"], "brazo": c["brazo"], "tipo": P[c["qid"]]["tipo"], "n_llamadas": n, "contexto_maximo": ctx,
                      "costo": costo, "clasificacion": c["clasificacion"], "intentos": c["intentos"]})

    def resumen(fs):
        ns = sorted(f["n_llamadas"] for f in fs if f["n_llamadas"] is not None)
        cs = sorted(f["contexto_maximo"] for f in fs if f["contexto_maximo"] is not None)
        por_q: dict = {}
        for f in fs:
            if f["costo"] is not None:
                por_q[f["qid"]] = por_q.get(f["qid"], 0.0) + f["costo"]
        return {"sesiones": len(fs), "sin_meta_sin_texto": sum(1 for f in fs if f["n_llamadas"] is None),
                "mas_de_30_llamadas": sum(1 for x in ns if x > 30), "al_tope_30_o_mas": sum(1 for x in ns if x >= 30),
                "cortadas": sum(1 for f in fs if f["clasificacion"] == "cortada"),
                "incompleta_otra": sum(1 for f in fs if f["clasificacion"] == "incompleta_otra"),
                "infra": {"sin_terminar": sum(1 for f in fs if f["clasificacion"] == "falla_infra_sin_terminar"),
                          "con_mas_de_un_intento": sum(1 for f in fs if (f["intentos"] or 1) > 1),
                          "intentos_de_mas": sum(max(0, (f["intentos"] or 1) - 1) for f in fs)},
                "llamadas_por_sesion": {"media": sum(ns) / len(ns) if ns else None, "mediana": percentil(ns, 0.5), "maximo": ns[-1] if ns else None},
                "costo_por_pregunta_usd": {"media": sum(por_q.values()) / len(por_q) if por_q else None, "total": sum(por_q.values())},
                "contexto_maximo": {"mediana": percentil(cs, 0.5), "maximo": cs[-1] if cs else None}}

    return {"por_brazo": {b: resumen([f for f in filas if f["brazo"] == b]) for b in BRAZOS},
            "por_brazo_y_tipo": {b: {t: resumen([f for f in filas if f["brazo"] == b and f["tipo"] == t]) for t in TIPOS} for b in BRAZOS}}


def declarado(corridas: list[dict], banco: Banco, veredictos_tol: list[dict], agregados_tol: dict, adjudicadas: dict, brazo_de: dict,
              d10: dict, fechas: dict) -> dict:
    inc = [c for c in corridas if c["clasificacion"] == "incompleta_otra"]
    motivos = []
    for c in inc:
        meta = meta_sin_texto(banco, c)
        if meta is None:
            frena("una incompleta_otra sin su meta sin texto")
        r7 = meta.get("mapa_R7") or []
        motivos.append({"brazo": c["brazo"],
                        "motivos": [re.sub(r"\b\d+\b", "n", m) for m in ((meta.get("completitud_R3") or {}).get("motivos_incompleta") or [])],
                        "la_llamada_que_falta": bool(r7) and r7[-1].get("tool") == "mcp__kg" and r7[-1].get("call_id_log") is None
                                                and sum(1 for x in r7 if x.get("call_id_log") is None) == 1})
    return {"textos": DECLARADO,
            "incompleta_otra": {"total": len(inc), "por_brazo": por_clave(c["brazo"] for c in inc),
                                "por_brazo_y_motivo": por_clave(f"{m['brazo']} | {'; '.join(m['motivos'])}" for m in motivos),
                                "con_la_llamada_que_falta_por_brazo": por_clave(m["brazo"] for m in motivos if m["la_llamada_que_falta"])},
            "sin_veredicto": {"por_brazo": por_clave(c["brazo"] for c in corridas if c["estado"] == "sin_veredicto")},
            "lectura_tolerante": {"salidas_por_brazo": por_clave(brazo_de[x["id_opaco"]] for x in veredictos_tol),
                                  "respuestas_por_brazo": por_clave(brazo_de[i] for i in agregados_tol)},
            "adjudicadas_por_brazo": por_clave(brazo_de[i] for i in adjudicadas),
            "D10_por_brazo": d10.get("por_brazo"),
            "bloques_con_fechas_distintas": fechas.get("n_bloques_con_fechas_distintas"),
            "sesiones_por_brazo_y_fecha": fechas.get("por_brazo_y_fecha")}


# --------------------------------------------------------------------------------------------------------------------- #
# El §9                                                                                                                 #
# --------------------------------------------------------------------------------------------------------------------- #
def relevancia(qids: list[str], m: dict, rel: dict) -> dict:
    nota = {x["id"]: x["nota"] for x in rel["preguntas"]}
    if any(q not in nota or nota[q] not in TERCIOS_RELEVANCIA for q in qids):
        frena("una pregunta sin su nota de relevancia, o con una nota fuera de 1 a 5")
    out = {"preguntas_por_tercio": por_clave(TERCIOS_RELEVANCIA[nota[q]] for q in qids), "por_tercio": {}}
    for t in ("baja", "media", "alta"):
        qs = [q for q in qids if TERCIOS_RELEVANCIA[nota[q]] == t]
        out["por_tercio"][t] = {"preguntas": len(qs),
                                "por_brazo": {b: _media([seis(*m[(q, b)]) for q in qs if (q, b) in m]) for b in BRAZOS},
                                "por_comparacion": {f: _media([d6(m, q, f) for q in preguntas_de(qs, m, (BRAZO_GRAFO, f))]) for f in FRAGMENTOS}}
    out["ponderado_por_la_nota"] = {
        "por_brazo": {b: _pond([(seis(*m[(q, b)]), nota[q]) for q in qids if (q, b) in m]) for b in BRAZOS},
        "por_comparacion": {f: _pond([(d6(m, q, f), nota[q]) for q in preguntas_de(qids, m, (BRAZO_GRAFO, f))]) for f in FRAGMENTOS}}
    return out


def arbol_e0(estructura: dict) -> dict:
    """El árbol de secciones e hijos de la estructura de la E0: padre, profundidad e hijos en orden; la raíz es el documento ("")."""
    padre, prof, hijos = {"": None}, {"": 0}, {"": []}

    def bajar(nodos, p):
        for n in nodos or []:
            k = ("S" + str(n["numero"])) if n.get("tipo") == "seccion" else str(n["numero"])
            if k not in padre:
                padre[k], prof[k], hijos[k] = p, prof[p] + 1, []
                hijos[p].append(k)
            bajar(n.get("hijos"), k)

    bajar(estructura.get("secciones"), "")
    return {"padre": padre, "prof": prof, "hijos": hijos}


def subarbol(A: dict, k: str) -> set:
    out, pila = set(), [k]
    while pila:
        x = pila.pop()
        out.add(x)
        pila.extend(A["hijos"].get(x, []))
    return out


def expandir(A: dict, u: str) -> list[str]:
    if ".." in u and "::" not in u:
        a, b = u.split("..", 1)
        if a in A["padre"] and b in A["padre"] and A["padre"][a] == A["padre"][b]:
            hs = A["hijos"][A["padre"][a]]
            i, j = hs.index(a), hs.index(b)
            if i <= j:
                return hs[i:j + 1]
        return [a, b]
    return [u]


def en_arbol(A: dict, v: str):
    base, extra = v, 0
    if "::" in base:
        base, extra = base.split("::", 1)[0], 1
    while base not in A["padre"] and "." in base:
        base, extra = base.rsplit(".", 1)[0], extra + 1
    return (base, extra) if base in A["padre"] else (None, None)


def pasos_e0(A: dict, a: str, b: str):
    (ka, ea), (kb, eb) = en_arbol(A, a), en_arbol(A, b)
    if ka is None or kb is None:
        return None
    anc, x = set(), ka
    while x is not None:
        anc.add(x)
        x = A["padre"][x]
    y = kb
    while y not in anc:
        y = A["padre"][y]
    return A["prof"][ka] + A["prof"][kb] - 2 * A["prof"][y] + ea + eb


def nodos_y_distancias(qids: list[str], m: dict, P: dict, kg: dict, e0_dir: Path, armado: dict) -> dict:
    resto: dict = {}                       # to → resto del chunk_id → nodos
    for n in kg["nodes"]:
        for p in n.get("provenances") or []:
            cid = p.get("chunk_id")
            if cid and "::" in cid:
                to, r = cid.split("::", 1)
                resto.setdefault(to, {}).setdefault(r, set()).add(n["id"])
    base_de: dict = {to: {} for to in resto}
    for to, rs in resto.items():
        for r in rs:
            base_de[to].setdefault(r.split("::", 1)[0], []).append(r)
    ady: dict = {}
    for e in kg["edges"]:
        ady.setdefault(e["source"], set()).add(e["target"])
        ady.setdefault(e["target"], set()).add(e["source"])

    sha_e0 = {x["to"]: x["sha256"] for x in armado["e0"] if x["archivo"] == f"estructura_{x['to']}.json"}
    arboles: dict = {}

    def arbol(to):
        if to not in arboles:
            p = Path(e0_dir) / f"estructura_{to}.json"
            arboles[to] = arbol_e0(json.loads(controlado(p, sha_e0.get(to), "una estructura de la E0")))
        return arboles[to]

    def nodos(unidad):
        to, u = unidad.split("::", 1)
        A, out = arbol(to), set()
        for v in expandir(A, u):
            if "::" in v:
                for r, ns in resto.get(to, {}).items():
                    if r == v or r.startswith(v + "::"):
                        out |= ns
            else:
                S = subarbol(A, v) if v in A["padre"] else {v}
                for b, rs in base_de.get(to, {}).items():
                    if b in S or b.startswith(v + "."):
                        for r in rs:
                            out |= resto[to][r]
        return out

    def distancia(na, nb):
        if not na or not nb:
            return "sin nodo"
        if na & nb:
            return 0
        vistos, cola = set(na), deque((x, 0) for x in sorted(na))
        while cola:
            x, d = cola.popleft()
            for y in ady.get(x, ()):
                if y in nb:
                    return d + 1
                if y not in vistos:
                    vistos.add(y)
                    cola.append((y, d + 1))
        return "sin camino"

    def e0(a, b):
        ta, ua = a.split("::", 1)
        tb, ub = b.split("::", 1)
        if ta != tb:
            return "distinto documento"
        A = arbol(ta)
        ds = [d for x in expandir(A, ua) for y in expandir(A, ub) if (d := pasos_e0(A, x, y)) is not None]
        return min(ds) if ds else "no ubicada"

    por_q = {}
    for q in qids:
        an = {a["rol"]: a["unidad"] for a in P[q]["anclas"]}
        na = nodos(an["ancla"])
        fila = {"nodos_ancla": len(na)}
        if "otro_punto" in an:
            nb = nodos(an["otro_punto"])
            fila |= {"nodos_otro_punto": len(nb), "distancia_grafo": distancia(na, nb), "distancia_e0": e0(an["ancla"], an["otro_punto"])}
        por_q[q] = fila
    dos = {q: v for q, v in por_q.items() if "distancia_grafo" in v}
    con = sorted(v["distancia_e0"] for v in dos.values() if isinstance(v["distancia_e0"], int))
    c1, c2 = percentil(con, 1 / 3), percentil(con, 2 / 3)
    for v in dos.values():
        d = v["distancia_e0"]
        v["tercio_e0"] = d if not isinstance(d, int) else ("baja" if d <= c1 else "media" if d <= c2 else "alta")
        g = v["distancia_grafo"]
        v["categoria_grafo"] = g if isinstance(g, str) else (str(g) if g <= 2 else "3 o más")

    def por_cat(clave):
        cats = sorted({v[clave] for v in dos.values()}, key=str)
        return {c: {"preguntas": sum(1 for v in dos.values() if v[clave] == c),
                    "por_comparacion": {f: _media([d6(m, q, f) for q, v in dos.items() if v[clave] == c and (q, BRAZO_GRAFO) in m and (q, f) in m])
                                        for f in FRAGMENTOS}} for c in cats}
    return {"preguntas": len(por_q), "preguntas_con_dos_anclas": len(dos),
            "anclas_sin_nodo": sum(1 for v in por_q.values() if v["nodos_ancla"] == 0)
            + sum(1 for v in dos.values() if v["nodos_otro_punto"] == 0),
            "cortes_tercios_e0": [c1, c2], "por_categoria_grafo": por_cat("categoria_grafo"), "por_tercio_e0": por_cat("tercio_e0"),
            "por_pregunta": por_q}


def expertos(dir_mat: Path, esperado: dict, rel: dict) -> dict:
    man_b = controlado(Path(dir_mat) / "manifest.txt", esperado["manifiesto_expertos"], "el manifest.txt del material de los expertos")
    dev = Path(dir_mat) / "devueltas"
    csvs = sorted(p for p in dev.iterdir() if p.is_file() and p.suffix == ".csv" and not veda(p.name)) if dev.is_dir() else []
    if not csvs:
        return {"datos": False, "declarado": "devueltas/ no existe o está vacía: el punto 3 del §9 se declara sin datos", "no_respondibles": []}
    man = {l.split("  ", 1)[1].strip(): l.split("  ", 1)[0] for l in man_b.decode("utf-8").splitlines() if "  " in l}
    clave = json.loads(controlado(Path(dir_mat) / "clave_codigos_experto.json", man.get("clave_codigos_experto.json"), "la clave de los códigos"))
    id_de = {f["codigo"]: f["id"] for f in clave["filas"]}
    nota = {x["id"]: x["nota"] for x in rel["preguntas"]}
    puesto = {x["id"]: x["puesto"] for x in rel["preguntas"]}
    resp: dict = {}
    for p in csvs:
        cols, filas = leer_csv(p.read_bytes())
        c = {}
        for k in ("codigo", "se_puede_responder", "la_respuesta_es_correcta", "relevancia_nota", "relevancia_puesto"):
            i = [j for j, x in enumerate(cols) if x.startswith(k)]
            if len(i) != 1:
                frena("una planilla devuelta sin sus columnas")
            c[k] = i[0]
        for f in filas:
            g = lambda k: (f[c[k]] if c[k] < len(f) else "").strip()  # noqa: E731
            if g("codigo") not in id_de:
                frena("un código de una planilla devuelta no está en la clave")
            resp.setdefault(p.stem, {})[id_de[g("codigo")]] = {"responde": plegar(g("se_puede_responder")), "correcta": plegar(g("la_respuesta_es_correcta")),
                                                                "nota": g("relevancia_nota"), "puesto": plegar(g("relevancia_puesto"))}

    def medidas(rs: dict) -> dict:
        r = [v for v in rs.values() if v["responde"] in ("si", "no")]
        k = [v for v in rs.values() if v["correcta"] in ("si", "parcial", "no")]
        n = [(q, v) for q, v in rs.items() if v["nota"].isdigit()]
        pu = [(q, v) for q, v in rs.items() if v["puesto"]]
        return {"filas": len(rs), "se_puede_responder_si": wilson(sum(v["responde"] == "si" for v in r), len(r)),
                "la_respuesta_es_correcta_si": wilson(sum(v["correcta"] == "si" for v in k), len(k)),
                "la_respuesta_es_correcta": por_clave(v["correcta"] for v in k),
                "acuerdo_con_P3_nota": wilson(sum(int(v["nota"]) == nota[q.split("|")[-1]] for q, v in n), len(n)),
                "acuerdo_con_P3_puesto": wilson(sum(v["puesto"] == plegar(puesto[q.split("|")[-1]]) for q, v in pu), len(pu))}
    es = sorted(resp)
    por = {e: medidas(resp[e]) for e in es}
    conj = medidas({f"{e}|{q}": v for e in es for q, v in resp[e].items()})
    pares = {}
    for i in range(len(es)):
        for j in range(i + 1, len(es)):
            qs = sorted(set(resp[es[i]]) & set(resp[es[j]]))
            pares[f"{es[i]} y {es[j]}"] = {k: wilson(sum(resp[es[i]][q][k] == resp[es[j]][q][k] for q in qs), len(qs))
                                           for k in ("responde", "correcta", "nota")}
    no_resp = []
    for q in sorted({q for rs in resp.values() for q in rs}):
        rs = [resp[e][q]["responde"] for e in es if q in resp[e] and resp[e][q]["responde"] in ("si", "no")]
        if rs and (all(x == "no" for x in rs) if len(rs) == 2 else sum(x == "no" for x in rs) > len(rs) / 2):
            no_resp.append(q)
    faltan = sorted(set(id_de.values()) - {q for rs in resp.values() for q in rs})
    return {"datos": True, "expertos": es, "por_experto": por, "en_conjunto": conj, "entre_expertos": pares, "no_respondibles": no_resp,
            "preguntas_del_material_sin_respuesta": faltan}


def exactitud_de_cita(corridas: list[dict], P: dict, banco: Banco, rutas: dict, esperado: dict, salida: Path, correr=None) -> dict:
    """El instrumento de HEAD sobre las sesiones de B6.3 (las completas y las incompletas), con sus anclas y la E0 del grafo evaluado,
    sobre copias de sus archivos (sin enlaces)."""
    controlado(rutas["ucita"], esperado["ucita"], "scripts/ucita2_indicadores_banco.py")
    trabajo = salida / "trabajo_exactitud_de_cita"
    ses = trabajo / "sesiones"
    ses.mkdir(parents=True)
    mapa = {}
    for c in corridas:
        if not c["salida"]:
            continue
        d = banco.sesion(c)
        destino = ses / c["sesion"]
        destino.mkdir()
        for n in (f"meta_{c['sesion']}.json", f"log_r1_{c['sesion']}.jsonl"):
            if (d / n).is_file():
                (destino / n).write_bytes(banco.leer(d / n))
        mapa[c["sesion"]] = c["qid"]
    (trabajo / "anclas.json").write_text(json.dumps({q: [a["unidad"] for a in P[q]["anclas"]] for q in sorted({c["qid"] for c in corridas})},
                                                    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (trabajo / "mapa_sesiones.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    argv = [sys.executable, "-I", "-B", str(rutas["ucita"]), "--sesiones"] + [str(ses / s) for s in sorted(mapa)] + [
        "--anclas", str(trabajo / "anclas.json"), "--e0", str(rutas["e0"]), "--mapa-sesiones", str(trabajo / "mapa_sesiones.json"),
        "--out-json", str(trabajo / "ucita_B63.json")]
    r = (correr or (lambda a: subprocess.run(a, capture_output=True, text=True)))(argv)
    (trabajo / "consola_ucita.txt").write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
    sale = trabajo / "ucita_B63.json"
    if r.returncode != 0 or not sale.is_file():
        return {"corrio": False, "codigo_de_salida": r.returncode, "sesiones": len(mapa),
                "declarado": "el instrumento no terminó bien: su consola queda en trabajo_exactitud_de_cita/consola_ucita.txt"}
    o = json.loads(sale.read_text(encoding="utf-8"))
    return {"corrio": True, "agregados": o["agregados"], "salida_sha256": sha(sale), "sesiones": len(mapa)}


# --------------------------------------------------------------------------------------------------------------------- #
# El análisis                                                                                                           #
# --------------------------------------------------------------------------------------------------------------------- #
def analizar(rutas: dict, esperado: dict, salida: Path, n_perm: int = N_PERM, n_boot: int = N_BOOT, ucita=None) -> dict:
    salida = Path(salida)
    if salida.exists():
        frena("--salida ya existe")
    if not esperado.get("cola"):
        frena("falta el sha256 de la lista de la cola")
    AP, JB = importar(rutas["clon"], esperado)
    K, M = JB.K, JB.M
    controlado(rutas["entrada"], esperado["entrada"], "la entrada sellada")
    e = AP.cargar_entrada(rutas["entrada"], K)
    P = cargar_preguntas_crudas(e)
    qids = list(e["preguntas"]["ids_en_orden"])
    if sorted(e["brazos"]) != sorted(BRAZOS) or any(P[q]["tipo"] not in TIPOS for q in qids):
        frena("los brazos o los tipos de la entrada no son los del pre-registro")
    banco = Banco(rutas["banco_b63"], rutas["manifiesto_fuera"], esperado)
    corridas = corridas_de(banco, e, K, JB, AP)
    corrida_de = {c["id_opaco"]: c for c in corridas if c["id_opaco"]}
    brazo_de = {i: c["brazo"] for i, c in corrida_de.items()}

    agg = json.loads(controlado(rutas["agregados"], esperado["agregados"], "los agregados de la lectura tolerante"))
    agregados = {x["id_opaco"]: x for x in agg["agregados"]}
    tol = {x["id_opaco"]: x for x in json.loads(controlado(rutas["agregados_tolerante"], esperado["agregados_tolerante"],
                                                           "los agregados de las que no se leían"))["agregados"]}
    if any(agregados.get(i) != x for i, x in tol.items()):
        frena("las que no se leían no están tal cual en los agregados")
    vtol = [json.loads(l) for l in controlado(rutas["veredictos_tolerante"], esperado["veredictos_tolerante"],
                                              "los veredictos de la lectura tolerante").decode("utf-8").splitlines() if l.strip()]
    if set(agregados) - set(corrida_de) or {x["id_opaco"] for x in vtol} - set(tol):
        frena("un id de los agregados no es una corrida completa")

    planilla_b = planilla_sellada(rutas["planilla"], rutas["sello_planilla"])
    estructura_b = controlado(rutas["estructura_planilla"], esperado["estructura_planilla"], "la estructura de la planilla")
    clave = json.loads(controlado(rutas["clave_adjudicacion"], esperado["clave_adjudicacion"], "la clave de la adjudicación"))
    adjudicadas = adjudicar(agregados, planilla_b, estructura_b, clave, M, corrida_de)
    veredictos = {i: {"veredicto_pregunta": (adjudicadas[i] if i in adjudicadas else a)["veredicto_pregunta"]} for i, a in agregados.items()}
    sin_requiere(veredictos)
    for c in corridas:
        c["estado"] = estado_de(c, veredictos)

    pesos = pesos_de_P1(rutas["etapa1"], rutas["tabla_cruce"], rutas["sello_tabla"], rutas["pesos_mesa"], esperado)
    cola = set(json.loads(controlado(rutas["cola"], esperado["cola"], "la lista de la cola"))["ids"])
    rel = json.loads(controlado(rutas["relevancia"], esperado["relevancia"], "la relevancia"))
    kg = json.loads(controlado(rutas["kg"], esperado["kg"], "el kg.json del grafo evaluado"))
    armado = json.loads(controlado(rutas["armado_e0"], esperado["armado_e0"], "el armado de la E0"))
    d10 = json.loads(controlado(rutas["d10"], esperado["d10"], "el D-10"))
    fechas = json.loads(controlado(rutas["fechas"], esperado["fechas"], "las fechas"))

    m = {nombre: metricas(corridas, nombre) for nombre in ESCENARIOS}
    out = {"que": "el análisis de B6.3 (§6, §8 y §9 del pre-registro, con sus notas al pie firmadas)",
           "parametros": {"permutaciones": n_perm, "remuestreos": n_boot, "semillas": SEMILLAS, "alfa_holm": list(ALFA)},
           "implementacion": IMPLEMENTACION, "pesos": pesos,
           "corridas_por_estado": por_clave(c["estado"] for c in corridas),
           "confirmatorio": {nombre: confirmatorio(qids, m[nombre], P, pesos["pesos"], n_perm, n_boot, por_documento=(nombre == "principal"))
                             for nombre in ESCENARIOS}}
    sc = sin_la_cola(qids, P, cola)
    resto = [q for q in qids if q not in set(sc["salen"])]
    out["cifra_aparte_sin_la_cola"] = {"salen": len(sc["salen"]), "por_causa": sc["por_causa"],
                                       "analisis": confirmatorio(resto, m["principal"], P, pesos["pesos"], n_perm, n_boot, por_documento=False)}
    out["operativo"] = operativo(corridas, banco, P)
    out["exploratorio"] = {"relevancia": relevancia(qids, m["principal"], rel),
                           "nodos_y_distancias": nodos_y_distancias(qids, m["principal"], P, kg, rutas["e0"], armado)}
    ex = expertos(rutas["expertos"], esperado, rel)
    if ex["datos"]:
        resto = [q for q in qids if q not in set(ex["no_respondibles"])]
        ex["sensibilidad_sin_las_no_respondibles"] = {"salen": len(qids) - len(resto),
                                                      "analisis": confirmatorio(resto, m["principal"], P, pesos["pesos"], n_perm, n_boot,
                                                                                por_documento=False)}
    out["exploratorio"]["expertos"] = ex
    salida.mkdir(parents=True)
    out["exploratorio"]["exactitud_de_cita"] = exactitud_de_cita(corridas, P, banco, rutas, esperado, salida, ucita)
    out["declarado"] = declarado(corridas, banco, vtol, tol, adjudicadas, brazo_de, d10, fechas)
    out["entradas"] = {k: (sha(v) if Path(v).is_file() else Path(v).name) for k, v in sorted(rutas.items()) if k != "clon"}
    out["archivos_de_banco_b63_controlados"] = len(banco.leidos)
    (salida / "analisis_B63.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out


ARGS = ("clon", "entrada", "manifiesto_fuera", "banco_b63", "agregados", "agregados_tolerante", "veredictos_tolerante", "planilla",
        "sello_planilla", "estructura_planilla", "clave_adjudicacion", "d10", "fechas", "relevancia", "etapa1", "tabla_cruce",
        "sello_tabla", "pesos_mesa", "cola", "kg", "e0", "armado_e0", "expertos", "ucita")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    for a in ARGS:
        ap.add_argument("--" + a.replace("_", "-"), type=Path, required=True)
    ap.add_argument("--sha256-cola", required=True, help="el sha256 de la lista sellada de la cola del grafo evaluado")
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args(argv)
    rutas = {k: getattr(a, k) for k in ARGS}
    try:
        out = analizar(rutas, ESPERADO | {"cola": a.sha256_cola}, a.salida)
    except Freno as ex:
        print(f"FRENO: {ex}")
        return 10
    except Exception as ex:  # noqa: BLE001  (sin el mensaje: puede traer un id de pregunta)
        renglon = next((f.lineno for f in reversed(traceback.extract_tb(ex.__traceback__)) if f.filename == __file__), None)
        print(f"ERROR: {type(ex).__name__} en analizar_b63.py:{renglon}")
        return 12
    print(f"salida: {a.salida.name}/analisis_B63.json ({sha(a.salida / 'analisis_B63.json')})")
    if not out["exploratorio"]["exactitud_de_cita"]["corrio"]:
        print("FRENO: el instrumento de la exactitud de cita no terminó bien; el resto del análisis está escrito")
        return 11
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
