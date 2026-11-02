#!/usr/bin/env python3
"""analizar_b64.py — El análisis confirmatorio de B6.4 (H-6: el código, probado con datos de juguete y sellado antes de la corrida; corre
sobre los datos reales recién después de la corrida, la lectura tolerante y la adjudicación). USD 0: no llama a ningún modelo, no abre
Neo4j ni el codificador y no escribe fuera de --salida.

Las reglas son las del pre-registro de B6.4 (`docs/preregistro_B6_4_evaluacion_confirmatoria_varios_puntos.md`, el texto firmado en
`55ee1a5a` y sus notas al pie en HEAD): el §5 (el juez, la lectura tolerante y la adjudicación), el §7 (lo que se cuenta antes de la
corrida), el §8 (el análisis confirmatorio y su código, §8.4), el §10 (lo que se declara) y la nota al pie de la revisión de expertos, con
su sensibilidad. Donde dice «como en B6.3», rige el pre-registro de B6.3: su §6 (las corridas cortadas y las fallas de infraestructura),
su §8.2 (lo operativo), su §8.3 (la robustez por documento) y la regla 3 de su nota al pie de la lectura tolerante.

§8.4: importa sin editar, con su sha256 controlado antes de ejecutarlo (SELLADO), el código sellado de B6.3, `analizar_b63.py`
(`9a9d0491…`): las métricas (estado_de, ESCENARIOS, metricas, seis, preguntas_de), la permutación (permutacion), Holm (holm), la
afirmación (afirmacion) y el bootstrap (bootstrap, percentil, intervalo); y, como en B6.3, las entradas (importar, Banco, corridas_de,
controlado, cargar_preguntas_crudas), la adjudicación (planilla_sellada, adjudicar, sin_requiere), lo operativo (operativo) y lo declarado
(declarado). Por importar, también `aplicar_lectura_tolerante_b63.py` (`5f608a58…`) y, del clon de HEAD, juez_b63.py, comun_b63.py y
mapping.py, con los sha256 de analizar_b63.ESPERADO. Cambian solo:
  - los tipos: agregacion, remision y condicion_excepcion (§3.2);
  - los brazos: kg, el del grafo adoptado (N7c+); fragmentos_hibrida y fragmentos_denso, las dos comparaciones principales; y kg_n7, el
    cuarto brazo, exploratorio (D-10);
  - las semillas: B64:permutacion:v1, B64:bootstrap:v1, B64:bootstrap:correccion:v1, B64:permutacion:documento:v1 y
    B64:bootstrap:documento:v1;
  - las entradas: cada una por argumento, con su sha256 en el JSON de --esperado (la plantilla, esperado_b64_plantilla.json, se llena
    cuando existan).

Lo que calcula (todo va al JSON de --salida, sin imprimirse):
  1. el veredicto de cada respuesta y cada corrida, como en B6.3 (analizar_b63.adjudicar y estado_de; los tres escenarios del §6 y de la
     regla 3);
  2. el §8.1: la métrica por pregunta, d_q contra cada brazo de fragmentos, la permutación de signos (100.000), Holm (0,025 y 0,05), el
     bootstrap percentil por pregunta (10.000) y la regla de la afirmación principal;
  3. el §8.2, al lado y fuera de Holm: por tipo, cada brazo y cada comparación con su intervalo; lo operativo por brazo y por tipo; y el
     cuarto brazo (kg contra kg_n7, y kg_n7 contra cada brazo de fragmentos), con sus intervalos, sin prueba. Sin total ponderado y sin
     hipótesis secundaria;
  4. el §8.3: la misma prueba con los signos por documento, y el bootstrap por documento;
  5. la sensibilidad de la revisión de expertos (la nota al pie): las comparaciones del §8.1 sin las preguntas que los expertos marquen
     como incorrectas, fuera de Holm y descriptiva; si no llegó la devolución, se declara y no se calcula;
  6. lo declarado: las marcas del brazo (§7), las anclas fuera de los 46 por clase (§10, punto 4), los lugares que cambiaron de unidad, de
     documento o de clase, y, por brazo, cuántos veredictos salen de la lectura tolerante y cuántas respuestas van a la adjudicación
     porque una salida del juez no se lee.

Frena (sale con 10) sin escribir nada si una entrada no da el sha256 del JSON de --esperado (o no lo tiene), o si falta un brazo.
Las decisiones de implementación que el pre-registro no fija van declaradas en el JSON (`implementacion`).

La corrección del H-6 (decisiones de la autora del 30/10/2026, en DECLARADO, tal cual): las cuatro elecciones del H-6 que el pre-registro
no fija, declaradas (decisión 1); y una salida del juez que no leen ni la lectura estricta ni la tolerante lleva su respuesta a la
adjudicación de la autora, entera (decisión 3): esas respuestas llegan en --agregados-sin-lectura (aplicar_lectura_tolerante_b64.py), con
todos sus criterios para la autora, y se cuentan por brazo.

  B64_CODIGO_B63=<b63/analisis/codigo de una copia de HEAD> python3 -I -B analizar_b64.py --clon <b63/v2/b2 de esa copia> … (ver --help)
      --esperado <JSON de sha256> --salida <carpeta nueva>
Sin B64_CODIGO_B63, el código de B6.3 se toma del repo. Imprime solo la ruta y el sha256 de la salida: ninguna cifra, ningún veredicto,
ningún id de pregunta. Si algo inesperado falla, imprime solo el tipo del error y su renglón en este archivo, sin su mensaje.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import traceback
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[6]
CODIGO_B63 = Path(os.environ.get("B64_CODIGO_B63") or REPO / "data" / "experiment" / "banco_mcp" / "b63" / "analisis" / "codigo")
# El código sellado de B6.3 que se importa (sha256 de HEAD 80085175; los dos primeros, los de sus sellos de B6.3)
SELLADO = {
    "analizar_b63.py": "9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb",
    "aplicar_lectura_tolerante_b63.py": "5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372",
    "exactitud_de_cita_9_4_b63.py": "5207941b4a54dd2e7071e5d1438fe0b664c0cfd2df56794614ab56de4e6f272a",
    "armar_adjudicacion_b63.py": "32daed5cbe1608097592d3cdb6301713df18258ca8bcc98d4d55429b43962aba",
}


def importar_sellado(nombre: str):
    """Un módulo del código sellado de B6.3, de su ruta y sin editarlo: se controla el sha256 de sus bytes y se ejecutan esos mismos
    bytes. Si ya está importado, se controla el de su archivo."""
    mod = nombre[:-3]
    if mod in sys.modules:
        if hashlib.sha256(Path(sys.modules[mod].__file__).read_bytes()).hexdigest() != SELLADO[nombre]:
            raise SystemExit(f"ABORTO: el {nombre} importado no es el sellado de B6.3")
        return sys.modules[mod]
    ruta = CODIGO_B63 / nombre
    b = ruta.read_bytes()
    if hashlib.sha256(b).hexdigest() != SELLADO[nombre]:
        raise SystemExit(f"ABORTO: {nombre} no es el sellado de B6.3 (su sha256)")
    spec = importlib.util.spec_from_file_location(mod, ruta)
    m = importlib.util.module_from_spec(spec)
    sys.modules[mod] = m
    exec(compile(b, str(ruta), "exec"), m.__dict__)  # noqa: S102  (los bytes controlados, tal cual)
    return m


A = importar_sellado("analizar_b63.py")
AP_SELLADO = importar_sellado("aplicar_lectura_tolerante_b63.py")    # el que analizar_b63.importar toma de sys.modules

BRAZO_GRAFO = A.BRAZO_GRAFO                     # «kg»: el del grafo adoptado por la regla de B2 (N7c+)
FRAGMENTOS = A.FRAGMENTOS                       # las dos comparaciones principales
CUARTO = "kg_n7"                                # el grafo sin corregir (N7), D-10
BRAZOS = (BRAZO_GRAFO,) + FRAGMENTOS + (CUARTO,)
TIPOS = ("agregacion", "remision", "condicion_excepcion")
N_PERM, N_BOOT = A.N_PERM, A.N_BOOT             # las cantidades de B6.3 (§8.1)
SEMILLAS = {"permutacion": "B64:permutacion:v1", "bootstrap": "B64:bootstrap:v1", "bootstrap_correccion": "B64:bootstrap:correccion:v1",
            "permutacion_documento": "B64:permutacion:documento:v1", "bootstrap_documento": "B64:bootstrap:documento:v1"}
COMPARACIONES = {f: (BRAZO_GRAFO, f) for f in FRAGMENTOS}                       # las de Holm y la afirmación
CUARTO_BRAZO = {f"{BRAZO_GRAFO}-{CUARTO}": (BRAZO_GRAFO, CUARTO)} | {f"{CUARTO}-{f}": (CUARTO, f) for f in FRAGMENTOS}
CUANTILES = {"p2_5": 0.025, "p97_5": 0.975}
AFIRMACION = "el grafo supera a los fragmentos en preguntas que juntan varios puntos"
if A.ALFA != (0.025, 0.05):
    raise SystemExit("ABORTO: el Holm importado no es el de 0,025 y 0,05")

# Los sha256 del código que se importa por analizar_b63.importar (los de B6.3); los de los datos vienen de --esperado
ESPERADO_CODIGO = {k: A.ESPERADO[k] for k in ("mapping", "juez_b63", "aplicar_lectura_tolerante_b63")}
ENTRADAS = ("entrada", "manifiesto_fuera", "agregados", "agregados_tolerante", "veredictos_tolerante", "agregados_sin_lectura",
            "sello_planilla", "estructura_planilla", "clave_adjudicacion", "d10", "fechas", "clases_documentos", "lugares")
MODAL_A_LA_AUTORA = "sin_consenso"              # el que analizar_b63.adjudicar y el armado llevan a la autora (como «dudoso»)
# §3.1: los 46 elegibles y las clases de los documentos donde puede caer el otro punto (D-1), con su tamaño
TAMANO_DE_CLASE = {"anclas_de_las_96_de_B63": 37, "N3": 14, "evaluacion_final": 15, "tanda_0": 5}
N_ELEGIBLES = 46

DECLARADO = {
    "el_diseno": "B6.4 se diseñó después de ver el resultado de B6.3. Se informa junto con él, sea cual sea su resultado, como otra "
                 "familia. (§10, punto 1)",
    "las_corridas_cortadas_y_las_fallas": "Como en B6.3 (su §6): en el análisis principal, las cortadas y las incompleta_otra cuentan "
                                          "como no correctas, sin pasar por el juez; la sensibilidad las saca; una falla de "
                                          "infraestructura sin terminar cuenta como no correcta. Si una pregunta queda sin corridas en "
                                          "un brazo, sale de esa comparación.",
    "las_corridas_sin_veredicto": "Una corrida completa que queda sin veredicto va por los escenarios de B6.3 (su §6 y la regla 3 de su "
                                  "nota al pie): fuera del análisis principal; en la sensibilidad, como no correcta; listada por brazo. Por "
                                  "la decisión del 30/10/2026 (las_salidas_del_juez_que_no_se_leen), una salida del juez que no se lee ya "
                                  "no deja su corrida sin veredicto. (§5)",
    "las_salidas_del_juez_que_no_se_leen": "«Una salida del juez que no leen ni la lectura estricta ni la tolerante no puede dejar el "
                                           "análisis sin escribir: va al destino que fija el §5 del pre-registro, con un envoltorio "
                                           "declarado.» (decisión de la autora del 30/10/2026) El §5: «Lo que la lectura no resuelve va "
                                           "a la adjudicación de la autora, como en B6.3» (55ee1a5a, renglones 197 a 199). Una salida así "
                                           "lleva su respuesta a la adjudicación: si a una respuesta le falta una de sus tres lecturas por "
                                           "esa salida, va entera, con todos sus criterios para que los marque la autora. Va con un "
                                           "envoltorio de aplicar_lectura_tolerante_b63.py que no lo edita (aplicar_lectura_tolerante_b64.py) "
                                           "y con el armado de la adjudicación de B6.4. Difiere de la regla 3 de la nota al pie de B6.3 "
                                           "(docs/preregistro_B6_3_evaluacion_final.md:907-910, en HEAD), que dejaba esa corrida sin "
                                           "veredicto; en B6.3 no hubo ninguna. Se cuentan por brazo (sin_lectura_a_la_adjudicacion).",
    "las_cuatro_elecciones_del_H6": "«Acepto, declaradas, las cuatro elecciones que hizo el H-6 y que el pre-registro no fija: la semilla "
                                    "B64:adjudicacion:v1, el intervalo de d en el bootstrap por documento, la semilla de la corrección "
                                    "para los intervalos del cuarto brazo y la forma de clases_documentos y de lugares.» (decisión de la "
                                    "autora del 30/10/2026) Las cuatro, en el código: la semilla del orden de las fichas de la "
                                    "adjudicación, B64:adjudicacion:v1 (armar_adjudicacion_b64.SEMILLA); el bootstrap por documento "
                                    "(B64:bootstrap:documento:v1) da el intervalo al 95 % de d de cada comparación principal; todos los "
                                    "intervalos del cuarto brazo (kg − kg_n7 y kg_n7 − cada brazo de fragmentos, en total y por tipo) van "
                                    "con B64:bootstrap:correccion:v1; y la forma de clases_documentos ({elegibles, clases}: los 46 y las "
                                    "cuatro clases del §3.1 con su tamaño) y la de lugares ({lugares: [{lugar, id, sorteado, final}]}, "
                                    "cada uno con su documento, su unidad y su clase).",
    "el_juez_de_la_corrida_y_el_del_analisis": "La corrida usa b64/v1/juez_b63.py (4fa09501…, H-4); el análisis importa el juez_b63.py "
                                               "de B6.3 de HEAD (266dd6f0…, por analizar_b63.importar y ESPERADO_CODIGO[\"juez_b63\"]). "
                                               "Cada función de juez_b63 que usa el código del análisis, con lo que ella usa del módulo, "
                                               "es igual en los dos, y también lo que usa de comun_b63 (controlar_juez_b64.py, por su árbol "
                                               "sintáctico). El diff de H-4 toca solo la cabecera, BANCO_DIR y CITAS_POR_ROL.",
    "el_cuarto_brazo": "«D-10, sí: el grafo sin corregir (N7) corre en B6.4 como cuarto brazo, fuera de Holm, para medir en preguntas "
                       "nuevas qué aporta la corrección.» Se informa al lado, nunca como afirmación principal. (§4 y §8.2)",
    "sin_total_ponderado_ni_secundaria": "Sin total ponderado: las 96 no representan al corpus. Sin hipótesis secundaria. (§8.2)",
    "las_etiquetas_del_runner": "D-4 (a): la semilla del orden, el prefijo del id de sesión y la sal del id opaco del juez de B6.3 se "
                                "reusan tal cual, declaradas. (§4)",
    "la_sensibilidad_de_los_expertos": "Las comparaciones del §8.1, repetidas sin las preguntas que los expertos marquen como "
                                       "incorrectas, fuera de Holm y como descriptiva. Una pregunta es incorrecta si tiene «no» en si la "
                                       "respuesta es correcta; con más de un experto, si la marca así la mayoría de los que la "
                                       "respondieron (con dos, los dos). (nota al pie del 30/10/2026)",
}

IMPLEMENTACION = {
    "lo_importado": "las métricas, la permutación, Holm, la afirmación y el bootstrap de analizar_b63.py, llamados tal cual con los tipos, "
                    "los brazos y las semillas de B6.4; las cifras de un remuestreo, con la clase Estadisticas de este archivo, que da "
                    "las mismas claves que analizar_b63.Estadisticas sin el total ponderado ni la secundaria",
    "sorteos": A.IMPLEMENTACION["sorteos"] + "; el bootstrap del cuarto brazo es otro remuestreo, con su semilla, sobre las mismas "
                                             "preguntas y en el mismo orden",
    "exactitud": A.IMPLEMENTACION["exactitud"],
    "percentil": "por rango: el valor de la posición ceil(q·B) de los B valores ordenados (q = 0,025 y 0,975); un remuestreo sin "
                 "preguntas para una cifra no entra en esa cifra, y se cuenta",
    "permutacion_por_documento": A.IMPLEMENTACION["permutacion_por_documento"],
    "el_documento_de_una_pregunta": "su campo «to», que tiene que ser el TO de su única ancla con rol «ancla» (la unidad del lugar)",
    "bootstrap_por_documento": "B6.4 no tiene hipótesis secundaria: el bootstrap por documento (B64:bootstrap:documento:v1) da el "
                               "intervalo al 95 % de d de cada comparación principal, con los documentos ordenados",
    "el_cuarto_brazo": "kg − kg_n7 y kg_n7 − cada brazo de fragmentos, en total y por tipo, con el bootstrap de B64:bootstrap:correccion:v1; "
                       "sin permutación, sin Holm y fuera de la afirmación. La media de kg_n7 por brazo y por tipo va con el bootstrap del "
                       "§8.1, como la de los otros tres brazos (el remuestreo es el mismo: agregar una cifra no lo cambia)",
    "lo_operativo": "analizar_b63.operativo, sin editar, agrupa por los brazos y los tipos de B6.3; se lo llama sobre vistas: kg_n7, "
                    "renombrado «kg», en una llamada aparte de los otros tres; y cada tipo de B6.4 como «varios_puntos» frente a los "
                    "otros dos como «dato_directo». De cada vista se toma solo el brazo y el tipo que le corresponden",
    "las_sensibilidades": "las de B6.3 (sin las cortadas; con las sin veredicto como no correctas) y la de los expertos, con las mismas "
                          "semillas y cantidades que el análisis principal, sin la versión por documento",
    "expertos": "cada CSV de devueltas/ es un experto (su nombre de archivo), con su sha256 en el JSON de --esperado; de cada fila, el "
                "código (la columna que empieza con «codigo») y si la respuesta es correcta (la que empieza con "
                "«la_respuesta_es_correcta»), plegado: «si», «parcial» o «no»; incorrecta: más «no» que la mitad de los que respondieron "
                "esa columna (con uno, ese; con dos, los dos)",
    "anclas_fuera_de_los_46": "cada ancla de cada pregunta (todas sus unidades, con cualquier rol) cuyo TO no está entre los 46; por "
                              "clase, un documento cuenta en cada clase que lo lista, y aparte las que no caen en ninguna",
    "lugares": "de cada lugar, lo sorteado y lo final (documento, unidad y clase); cambia de unidad, de documento o de clase si ese campo "
               "difiere; se controla que lo final sea el ancla y el documento de su pregunta; por clase, la sorteada",
    "las_que_no_se_leen": "las respuestas de --agregados-sin-lectura (aplicar_lectura_tolerante_b64.py) se suman a los agregados de la "
                          "lectura tolerante antes de la adjudicación: cada una con su veredicto «requiere_adjudicacion» y todos sus "
                          "criterios con «sin_consenso», la marca con que analizar_b63.adjudicar y el armado llevan un criterio a la "
                          "autora (no es un modal del juez: a la respuesta le falta una de sus tres lecturas); el veredicto lo dan las "
                          "marcas de la autora, con el mapping de EV2. Se controla que sean corridas completas, que no estén en los "
                          "agregados de la lectura tolerante y que sean justo las de sus salidas",
    "los_roles": "el análisis reconoce los brazos por su nombre (kg, fragmentos_hibrida, fragmentos_denso y kg_n7) y no lee sus roles: que "
                 "la entrada le dé a kg_n7 el rol grafo_sin_corregir y la configuración, grafo, no cambia nada",
}


# --------------------------------------------------------------------------------------------------------------------- #
# Las entradas                                                                                                          #
# --------------------------------------------------------------------------------------------------------------------- #
def esperados(datos: dict) -> dict:
    """Los sha256 de los datos (el JSON de --esperado, sin sus claves «_…») más los del código, que no se pueden pisar."""
    d = {k: v for k, v in datos.items() if not k.startswith("_")}
    if any(k in d and d[k] != v for k, v in ESPERADO_CODIGO.items()):
        A.frena("el JSON de los esperados trae otro sha256 para el código importado")
    return d | ESPERADO_CODIGO


def controlar_entradas(rutas: dict, esp: dict, claves) -> None:
    """Cada entrada con su sha256, antes de leer ninguna: frena si no lo tiene, si no existe o si no lo da."""
    for k in claves:
        if not esp.get(k):
            A.frena(f"{k}: sin su sha256 en el JSON de los esperados")
        if not Path(rutas[k]).is_file():
            A.frena(f"{k}: no existe")
        A.controlado(rutas[k], esp[k], k)


def controlar_brazos_y_tipos(e: dict, P: dict, qids: list[str]) -> None:
    faltan, sobran = sorted(set(BRAZOS) - set(e["brazos"])), sorted(set(e["brazos"]) - set(BRAZOS))
    if faltan or sobran:
        A.frena(f"los brazos de la entrada no son los cuatro de B6.4: falta {faltan}, sobra {sobran}")
    if any(P[q].get("tipo") not in TIPOS for q in qids):
        A.frena("una pregunta con un tipo que no es de B6.4")
    for q in qids:
        anclas = [a for a in P[q].get("anclas") or [] if a.get("rol") == "ancla"]
        if len(anclas) != 1 or anclas[0]["unidad"].split("::", 1)[0] != P[q].get("to"):
            A.frena("una pregunta sin una sola ancla con rol «ancla» en su documento")


def d6(m: dict, q: str, x: str, y: str) -> int:
    """d_q en sextos entre dos brazos (con x = kg es analizar_b63.d6)."""
    return A.seis(*m[(q, x)]) - A.seis(*m[(q, y)])


# --------------------------------------------------------------------------------------------------------------------- #
# El §8.1, el §8.2 y el §8.3                                                                                            #
# --------------------------------------------------------------------------------------------------------------------- #
class Estadisticas:
    """Las cifras de un remuestreo (o de la muestra): la media de cada brazo, en total y por tipo, y la media de d de cada comparación,
    en total y por tipo. Son las claves de analizar_b63.Estadisticas («media|b», «media|b|t», «d|nombre», «d|nombre|t») sin el total
    ponderado ni la secundaria, con los tipos, los brazos y las comparaciones que se le pasan."""

    def __init__(self, P: dict, tipos=TIPOS, brazos=BRAZOS, comparaciones=None):
        self.P, self.tipos, self.brazos = P, tuple(tipos), tuple(brazos)
        self.comparaciones = COMPARACIONES if comparaciones is None else comparaciones

    def calcular(self, qs: list[str], m: dict) -> dict:
        out = {}
        tipos = {t: [q for q in qs if self.P[q]["tipo"] == t] for t in self.tipos}
        for b in self.brazos:
            vs = [A.seis(*m[(q, b)]) for q in qs if (q, b) in m]
            out[f"media|{b}"] = sum(vs) / 6 / len(vs) if vs else None
            for t, tq in tipos.items():
                vt = [A.seis(*m[(q, b)]) for q in tq if (q, b) in m]
                out[f"media|{b}|{t}"] = sum(vt) / 6 / len(vt) if vt else None
        for nombre, (x, y) in self.comparaciones.items():
            ds = [d6(m, q, x, y) for q in qs if (q, x) in m and (q, y) in m]
            out[f"d|{nombre}"] = sum(ds) / 6 / len(ds) if ds else None
            for t, tq in tipos.items():
                v = [d6(m, q, x, y) for q in tq if (q, x) in m and (q, y) in m]
                out[f"d|{nombre}|{t}"] = sum(v) / 6 / len(v) if v else None
        return out


def confirmatorio(qids: list[str], m: dict, P: dict, n_perm: int = N_PERM, n_boot: int = N_BOOT, por_documento: bool = True,
                  semillas: dict = SEMILLAS, tipos=TIPOS, brazos=BRAZOS, cuarto: bool = True) -> dict:
    """El §8.1, el §8.2 (por tipo y el cuarto brazo; sin lo operativo) y, con por_documento, el §8.3, sobre una métrica. Holm y la
    afirmación van solo sobre las dos comparaciones principales."""
    est = Estadisticas(P, tipos, brazos)
    puntual = est.calcular(qids, m)
    pruebas, medias = {}, {}
    for f, (x, y) in COMPARACIONES.items():
        qs = A.preguntas_de(qids, m, (x, y))
        pruebas[f] = A.permutacion([d6(m, q, x, y) for q in qs], semillas["permutacion"], n_perm)
        medias[f] = pruebas[f]["media"]
    h = A.holm({f: pruebas[f]["p"] for f in COMPARACIONES})
    boot = A.bootstrap(qids, lambda q: [q], est, m, semillas["bootstrap"], n_boot, CUANTILES)
    out = {"preguntas": len(qids),
           "preguntas_que_salen_por_comparacion": {f: len(qids) - pruebas[f]["n"] for f in COMPARACIONES},
           "por_comparacion": {f: {"preguntas": pruebas[f]["n"], "media_d": medias[f], "permutacion": pruebas[f], "holm": h[f],
                                   "intervalo_95": A.intervalo(boot, f"d|{f}")} for f in COMPARACIONES},
           "afirmacion_principal": A.afirmacion(h, medias) | {"afirmacion": AFIRMACION},
           "por_brazo": {b: {"media": puntual[f"media|{b}"], "intervalo_95": A.intervalo(boot, f"media|{b}")} for b in brazos},
           "por_tipo": {t: {"preguntas": sum(1 for q in qids if P[q]["tipo"] == t),
                            "por_brazo": {b: {"media": puntual[f"media|{b}|{t}"], "intervalo_95": A.intervalo(boot, f"media|{b}|{t}")}
                                          for b in brazos},
                            "por_comparacion": {f: {"media_d": puntual[f"d|{f}|{t}"], "intervalo_95": A.intervalo(boot, f"d|{f}|{t}")}
                                                for f in COMPARACIONES}}
                        for t in tipos},
           "remuestreos_sin_cifra": {k: v["remuestreos_sin_cifra"] for k, v in sorted(boot.items()) if v["remuestreos_sin_cifra"]}}
    if cuarto:
        ec = Estadisticas(P, tipos, (), CUARTO_BRAZO)
        pc = ec.calcular(qids, m)
        bc = A.bootstrap(qids, lambda q: [q], ec, m, semillas["bootstrap_correccion"], n_boot, CUANTILES)
        out["cuarto_brazo"] = {
            "fuera_de_holm_y_de_la_afirmacion": True, "sin_prueba": True,
            "por_comparacion": {n: {"preguntas": len(A.preguntas_de(qids, m, xy)), "media_d": pc[f"d|{n}"],
                                    "intervalo_95": A.intervalo(bc, f"d|{n}"),
                                    "por_tipo": {t: {"media_d": pc[f"d|{n}|{t}"], "intervalo_95": A.intervalo(bc, f"d|{n}|{t}")}
                                                 for t in tipos}}
                                for n, xy in CUARTO_BRAZO.items()},
            "remuestreos_sin_cifra": {k: v["remuestreos_sin_cifra"] for k, v in sorted(bc.items()) if v["remuestreos_sin_cifra"]}}
    if por_documento:
        docs = sorted({P[q]["to"] for q in qids})
        de_doc = {d: [q for q in qids if P[q]["to"] == d] for d in docs}
        pd = {}
        for f, (x, y) in COMPARACIONES.items():
            sumas = [sum(d6(m, q, x, y) for q in de_doc[d] if (q, x) in m and (q, y) in m) for d in docs]
            qs = A.preguntas_de(qids, m, (x, y))
            r = A.permutacion(sumas, semillas["permutacion_documento"], n_perm)
            r["media"] = (sum(sumas) / 6 / len(qs)) if qs else None
            r["documentos"], r["preguntas"] = len(docs), len(qs)
            pd[f] = r
        hd = A.holm({f: pd[f]["p"] for f in COMPARACIONES})
        bd = A.bootstrap(docs, lambda d: de_doc[d], est, m, semillas["bootstrap_documento"], n_boot, CUANTILES)
        ad = A.afirmacion(hd, {f: pd[f]["media"] for f in COMPARACIONES})
        out["por_documento"] = {
            "documentos": len(docs),
            "por_comparacion": {f: {"permutacion": pd[f], "holm": hd[f], "intervalo_95": A.intervalo(bd, f"d|{f}"),
                                    "remuestreos_sin_cifra": bd[f"d|{f}"]["remuestreos_sin_cifra"]} for f in COMPARACIONES},
            "afirmacion_principal": ad,
            "la_misma_conclusion": {"principal": {f: hd[f]["rechaza"] == h[f]["rechaza"] for f in COMPARACIONES},
                                    "afirmacion": ad["el_grafo_supera_a_los_fragmentos"]
                                    == out["afirmacion_principal"]["el_grafo_supera_a_los_fragmentos"]}}
    return out


def agregados_sin_lectura(datos: dict, agregados: dict, corrida_de: dict) -> tuple[dict, list[dict]]:
    """Las respuestas que van enteras a la adjudicación porque una de sus tres salidas del juez no la lee ni la estricta ni la tolerante
    (la decisión 3; aplicar_lectura_tolerante_b64.py): {id_opaco: agregado} y esas salidas, controladas."""
    sl = {x["id_opaco"]: x for x in datos.get("agregados") or []}
    salidas = list(datos.get("salidas") or [])
    if len(sl) != len(datos.get("agregados") or []) or set(sl) & set(agregados) or set(sl) - set(corrida_de) \
            or {x["id_opaco"] for x in salidas} != set(sl):
        A.frena("las respuestas sin lectura no son corridas completas fuera de los agregados, con sus salidas")
    if any(x["veredicto_pregunta"] != "requiere_adjudicacion" or not x["modales"]
           or x["modales"] != [MODAL_A_LA_AUTORA] * x["n_criterios"] for x in sl.values()):
        A.frena("una respuesta sin lectura no va entera a la adjudicación")
    return sl, salidas


def operativo(corridas: list[dict], banco, P: dict) -> dict:
    """Lo operativo por brazo y por tipo (§8.2, como en B6.3), con analizar_b63.operativo sin editar, sobre vistas (IMPLEMENTACION)."""
    out = {"por_brazo": {}, "por_brazo_y_tipo": {b: {} for b in BRAZOS}}
    for renombre in ({b: b for b in A.BRAZOS}, {CUARTO: BRAZO_GRAFO}):
        vista = [dict(c, brazo=renombre[c["brazo"]]) for c in corridas if c["brazo"] in renombre]
        for t in TIPOS:
            Pt = {q: {"tipo": "varios_puntos" if P[q]["tipo"] == t else "dato_directo"} for q in P}
            o = A.operativo(vista, banco, Pt)
            for b, v in renombre.items():
                if out["por_brazo"].setdefault(b, o["por_brazo"][v]) != o["por_brazo"][v]:
                    A.frena("lo operativo de un brazo cambia entre sus vistas")
                out["por_brazo_y_tipo"][b][t] = o["por_brazo_y_tipo"][v]["varios_puntos"]
    return out


# --------------------------------------------------------------------------------------------------------------------- #
# La sensibilidad de los expertos y lo declarado                                                                        #
# --------------------------------------------------------------------------------------------------------------------- #
def expertos(dir_mat: Path, esp: dict, qids: list[str]) -> dict:
    """Las preguntas que los expertos marcan como incorrectas (la nota al pie), en «n de N»; sin devueltas/, se declara."""
    dir_mat = Path(dir_mat)
    controlar_entradas({"manifiesto_expertos": dir_mat / "manifest.txt"}, esp, ("manifiesto_expertos",))
    dev = dir_mat / "devueltas"
    csvs = sorted(p for p in dev.iterdir() if p.is_file() and p.suffix == ".csv" and not A.veda(p.name)) if dev.is_dir() else []
    esp_dev = esp.get("devueltas") or {}
    if sorted(p.name for p in csvs) != sorted(esp_dev):
        A.frena("las planillas devueltas no son las del JSON de los esperados")
    if not csvs:
        return {"datos": False, "incorrectas": [],
                "declarado": "no llegó la devolución de los expertos (devueltas/ no existe o está vacía): la sensibilidad se declara y "
                             "no se calcula"}
    man_b = (dir_mat / "manifest.txt").read_bytes()
    man = {l.split("  ", 1)[1].strip(): l.split("  ", 1)[0] for l in man_b.decode("utf-8").splitlines() if "  " in l}
    clave = json.loads(A.controlado(dir_mat / "clave_codigos_experto.json", man.get("clave_codigos_experto.json"),
                                    "la clave de los códigos de los expertos"))
    id_de = {f["codigo"]: f["id"] for f in clave["filas"]}
    if len(set(id_de.values())) != len(id_de) or any(i not in set(qids) for i in id_de.values()):
        A.frena("la clave de los expertos trae una pregunta que no está en la entrada, o repetida")
    resp: dict = {}
    for p in csvs:
        cols, filas = A.leer_csv(A.controlado(p, esp_dev[p.name], "una planilla devuelta"))
        ic = [j for j, x in enumerate(cols) if x.startswith("codigo")]
        ik = [j for j, x in enumerate(cols) if x.startswith("la_respuesta_es_correcta")]
        if len(ic) != 1 or len(ik) != 1:
            A.frena("una planilla devuelta sin sus columnas")
        for f in filas:
            cod = (f[ic[0]] if ic[0] < len(f) else "").strip()
            if cod not in id_de:
                A.frena("un código de una planilla devuelta no está en la clave")
            resp.setdefault(p.stem, {})[id_de[cod]] = A.plegar(f[ik[0]] if ik[0] < len(f) else "")
    es = sorted(resp)
    incorrectas = []
    for q in sorted(set(id_de.values())):
        rs = [resp[e][q] for e in es if resp[e].get(q) in ("si", "parcial", "no")]
        if rs and sum(x == "no" for x in rs) > len(rs) / 2:
            incorrectas.append(q)

    def n_de(rs: dict) -> dict:
        r = [v for v in rs.values() if v in ("si", "parcial", "no")]
        return {"filas": len(rs), "la_respuesta_es_correcta": {v: f"{sum(x == v for x in r)} de {len(r)}" for v in ("si", "parcial", "no")}}
    return {"datos": True, "expertos": es, "preguntas_del_material": len(id_de), "por_experto": {e: n_de(resp[e]) for e in es},
            "incorrectas": incorrectas, "incorrectas_n_de_N": f"{len(incorrectas)} de {len(id_de)}",
            "preguntas_del_material_sin_respuesta": len(set(id_de.values()) - {q for r in resp.values() for q in r})}


def controlar_clases(clases: dict) -> None:
    eleg = clases.get("elegibles") or []
    c = clases.get("clases") or {}
    if len(set(eleg)) != N_ELEGIBLES or sorted(c) != sorted(TAMANO_DE_CLASE) or any(len(set(c[k])) != n for k, n in TAMANO_DE_CLASE.items()):
        A.frena("las clases de los documentos no son los 46 elegibles y las cuatro clases del §3.1 con su tamaño")


def anclas_fuera_de_los_46(qids: list[str], P: dict, clases: dict) -> dict:
    """§10, punto 4 (D-1): las anclas que caen fuera de los 46, contadas por clase de documento (§3.1)."""
    eleg, cls = set(clases["elegibles"]), {k: set(v) for k, v in clases["clases"].items()}
    total, fuera, ninguna, con = 0, 0, 0, Counter()
    por_clase, por_tipo = Counter(), Counter()
    for q in qids:
        for a in P[q]["anclas"]:
            to = a["unidad"].split("::", 1)[0]
            total += 1
            if to in eleg:
                continue
            fuera += 1
            por_tipo[P[q]["tipo"]] += 1
            con[q] += 1
            ks = [k for k in sorted(cls) if to in cls[k]]
            por_clase.update(ks)
            ninguna += not ks
    return {"anclas": total, "fuera_de_los_46": fuera, "preguntas_con_alguna_fuera": len(con),
            "por_clase": {k: por_clase.get(k, 0) for k in sorted(TAMANO_DE_CLASE)}, "en_ninguna_de_esas_clases": ninguna,
            "por_tipo": {t: por_tipo.get(t, 0) for t in TIPOS}}


def lugares_que_cambiaron(qids: list[str], P: dict, lugares: dict) -> dict:
    """§10, punto 4, y la nota al pie del 30/10/2026: los lugares que cambiaron de unidad, de documento o de clase, con su cuenta."""
    filas = {x["id"]: x for x in lugares.get("lugares") or []}
    if sorted(filas) != sorted(qids) or len(filas) != len(lugares.get("lugares") or []):
        A.frena("los lugares no son justo las preguntas de la entrada")
    cuenta = {k: Counter() for k in ("unidad", "documento", "clase")}
    por_clase = {}
    for q in qids:
        s, f = filas[q]["sorteado"], filas[q]["final"]
        ancla = next(a["unidad"] for a in P[q]["anclas"] if a["rol"] == "ancla")
        if f["unidad"] != ancla or f["documento"] != P[q]["to"]:
            A.frena("lo final de un lugar no es el ancla y el documento de su pregunta")
        c = por_clase.setdefault(s["clase"], {"lugares": 0, "cambian_de_unidad": 0, "cambian_de_documento": 0, "cambian_de_clase": 0})
        c["lugares"] += 1
        for k in ("unidad", "documento", "clase"):
            if s[k] != f[k]:
                cuenta[k]["total"] += 1
                cuenta[k][P[q]["tipo"]] += 1
                c[f"cambian_de_{k}"] += 1
    return {"lugares": len(qids),
            **{f"cambian_de_{k}": {"total": v.get("total", 0), "por_tipo": {t: v.get(t, 0) for t in TIPOS}} for k, v in cuenta.items()},
            "por_clase_sorteada": dict(sorted(por_clase.items()))}


def declarado(corridas: list[dict], banco, vtol: list[dict], tol: dict, adjudicadas: dict, brazo_de: dict, d10: dict, fechas: dict,
              qids: list[str], P: dict, clases: dict, lugares: dict, sin_lectura: tuple[dict, list[dict]] = ({}, [])) -> dict:
    """analizar_b63.declarado, sin editar (con los textos de B6.4), más lo que declara B6.4."""
    d = A.declarado(corridas, banco, vtol, tol, adjudicadas, brazo_de, d10, fechas)
    d["textos"] = DECLARADO
    d["lectura_tolerante_por_brazo"] = {k: {b: d["lectura_tolerante"][k].get(b, 0) for b in BRAZOS} for k in d["lectura_tolerante"]}
    sl, salidas = sin_lectura
    d["sin_lectura_a_la_adjudicacion"] = {
        "respuestas_por_brazo": {b: sum(1 for i in sl if brazo_de[i] == b) for b in BRAZOS},
        "salidas_por_brazo": {b: sum(1 for x in salidas if brazo_de[x["id_opaco"]] == b) for b in BRAZOS},
        "salidas_por_motivo": A.por_clave(x["motivo"] for x in salidas),
        "adjudicadas": sum(1 for i in sl if i in adjudicadas)}
    d["anclas_fuera_de_los_46"] = anclas_fuera_de_los_46(qids, P, clases)
    d["lugares_que_cambiaron"] = lugares_que_cambiaron(qids, P, lugares)
    return d


# --------------------------------------------------------------------------------------------------------------------- #
# El análisis                                                                                                           #
# --------------------------------------------------------------------------------------------------------------------- #
def analizar(rutas: dict, esperado: dict, salida: Path, n_perm: int = N_PERM, n_boot: int = N_BOOT) -> dict:
    salida = Path(salida)
    if salida.exists():
        A.frena("--salida ya existe")
    esp = esperados(esperado)
    controlar_entradas(rutas, esp, ENTRADAS)
    AP, JB = A.importar(rutas["clon"], esp)
    K, M = JB.K, JB.M
    e = AP.cargar_entrada(rutas["entrada"], K)
    P = A.cargar_preguntas_crudas(e)
    qids = list(e["preguntas"]["ids_en_orden"])
    controlar_brazos_y_tipos(e, P, qids)
    d10 = json.loads(A.controlado(rutas["d10"], esp["d10"], "el D-10"))
    fechas = json.loads(A.controlado(rutas["fechas"], esp["fechas"], "las fechas"))
    for nombre, por in (("el D-10", d10.get("por_brazo")), ("las fechas", fechas.get("por_brazo_y_fecha"))):
        if sorted(por or {}) != sorted(BRAZOS):
            A.frena(f"{nombre} no trae justo los cuatro brazos de B6.4: falta un brazo o sobra uno")
    clases = json.loads(A.controlado(rutas["clases_documentos"], esp["clases_documentos"], "las clases de los documentos"))
    controlar_clases(clases)
    lugares = json.loads(A.controlado(rutas["lugares"], esp["lugares"], "los lugares"))
    banco = A.Banco(rutas["banco_b64"], rutas["manifiesto_fuera"], esp)
    corridas = A.corridas_de(banco, e, K, JB, AP)
    corrida_de = {c["id_opaco"]: c for c in corridas if c["id_opaco"]}
    brazo_de = {i: c["brazo"] for i, c in corrida_de.items()}

    agg = json.loads(A.controlado(rutas["agregados"], esp["agregados"], "los agregados de la lectura tolerante"))
    agregados = {x["id_opaco"]: x for x in agg["agregados"]}
    tol = {x["id_opaco"]: x for x in json.loads(A.controlado(rutas["agregados_tolerante"], esp["agregados_tolerante"],
                                                             "los agregados de las que no se leían"))["agregados"]}
    if any(agregados.get(i) != x for i, x in tol.items()):
        A.frena("las que no se leían no están tal cual en los agregados")
    vtol = [json.loads(l) for l in A.controlado(rutas["veredictos_tolerante"], esp["veredictos_tolerante"],
                                                "los veredictos de la lectura tolerante").decode("utf-8").splitlines() if l.strip()]
    if set(agregados) - set(corrida_de) or {x["id_opaco"] for x in vtol} - set(tol):
        A.frena("un id de los agregados no es una corrida completa")
    sin_lectura = agregados_sin_lectura(json.loads(A.controlado(rutas["agregados_sin_lectura"], esp["agregados_sin_lectura"],
                                                                "las respuestas sin lectura")), agregados, corrida_de)
    agregados |= sin_lectura[0]                 # la decisión 3: a la adjudicación, enteras

    planilla_b = A.planilla_sellada(rutas["planilla"], rutas["sello_planilla"])
    estructura_b = A.controlado(rutas["estructura_planilla"], esp["estructura_planilla"], "la estructura de la planilla")
    clave = json.loads(A.controlado(rutas["clave_adjudicacion"], esp["clave_adjudicacion"], "la clave de la adjudicación"))
    adjudicadas = A.adjudicar(agregados, planilla_b, estructura_b, clave, M, corrida_de)
    veredictos = {i: {"veredicto_pregunta": (adjudicadas[i] if i in adjudicadas else a)["veredicto_pregunta"]} for i, a in agregados.items()}
    A.sin_requiere(veredictos)
    for c in corridas:
        c["estado"] = A.estado_de(c, veredictos)
    ex = expertos(rutas["expertos"], esp, qids)

    m = {nombre: A.metricas(corridas, nombre) for nombre in A.ESCENARIOS}
    out = {"que": "el análisis confirmatorio de B6.4 (§5, §7, §8 y §10 del pre-registro, con su nota al pie de la revisión de expertos)",
           "parametros": {"permutaciones": n_perm, "remuestreos": n_boot, "semillas": SEMILLAS, "alfa_holm": list(A.ALFA),
                          "brazos": list(BRAZOS), "tipos": list(TIPOS), "comparaciones_principales": {f: list(v) for f, v in COMPARACIONES.items()},
                          "cuarto_brazo": {n: list(v) for n, v in CUARTO_BRAZO.items()}},
           "implementacion": IMPLEMENTACION,
           "preguntas_por_tipo": {t: sum(1 for q in qids if P[q]["tipo"] == t) for t in TIPOS},
           "corridas_por_estado": A.por_clave(c["estado"] for c in corridas),
           "corridas_por_brazo_y_estado": A.por_clave(f"{c['brazo']} | {c['estado']}" for c in corridas),
           "confirmatorio": {nombre: confirmatorio(qids, m[nombre], P, n_perm, n_boot, por_documento=(nombre == "principal"))
                             for nombre in A.ESCENARIOS}}
    out["operativo"] = operativo(corridas, banco, P)
    if ex["datos"]:
        resto = [q for q in qids if q not in set(ex["incorrectas"])]
        ex["sensibilidad_sin_las_incorrectas"] = {"fuera_de_holm": True, "descriptiva": True, "salen": len(qids) - len(resto),
                                                  "analisis": confirmatorio(resto, m["principal"], P, n_perm, n_boot, por_documento=False)}
    out["expertos"] = ex
    out["declarado"] = declarado(corridas, banco, vtol, tol, adjudicadas, brazo_de, d10, fechas, qids, P, clases, lugares, sin_lectura)
    out["entradas"] = {k: (A.sha(v) if Path(v).is_file() else Path(v).name) for k, v in sorted(rutas.items()) if k != "clon"}
    out["esperado"] = {k: v for k, v in sorted(esp.items())}
    out["archivos_de_banco_controlados"] = len(banco.leidos)
    salida.mkdir(parents=True)
    (salida / "analisis_B64.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out


ARGS = ("clon", "entrada", "manifiesto_fuera", "banco_b64", "agregados", "agregados_tolerante", "veredictos_tolerante",
        "agregados_sin_lectura", "planilla", "sello_planilla", "estructura_planilla", "clave_adjudicacion", "d10", "fechas",
        "clases_documentos", "lugares", "expertos")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    for a in ARGS:
        ap.add_argument("--" + a.replace("_", "-"), type=Path, required=True)
    ap.add_argument("--esperado", type=Path, required=True, help="el JSON de los sha256 esperados de las entradas, lleno")
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args(argv)
    rutas = {k: getattr(a, k) for k in ARGS}
    try:
        out = analizar(rutas, json.loads(a.esperado.read_text(encoding="utf-8")), a.salida)
    except A.Freno as ex:
        print(f"FRENO: {ex}")
        return 10
    except Exception as ex:  # noqa: BLE001  (sin el mensaje: puede traer un id de pregunta)
        renglon = next((f.lineno for f in reversed(traceback.extract_tb(ex.__traceback__)) if f.filename == __file__), None)
        print(f"ERROR: {type(ex).__name__} en analizar_b64.py:{renglon}")
        return 12
    print(f"salida: {a.salida.name}/analisis_B64.json ({A.sha(a.salida / 'analisis_B64.json')})")
    return 0 if out["preguntas_por_tipo"] else 12


if __name__ == "__main__":
    raise SystemExit(main())
