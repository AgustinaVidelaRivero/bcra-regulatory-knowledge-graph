#!/usr/bin/env python3
"""exactitud_de_cita_9_4_b63.py — El punto 4 del §9 de B6.3: la exactitud de cita, con la regla de la autora para las anclas que el
instrumento de citas no lee (etapa D1: el código, probado con datos de juguete y sellado; corre sobre los datos reales recién en la D2).
USD 0: no llama a ningún modelo, no abre Neo4j ni el codificador y no escribe fuera de --salida.

La regla (decisiones de la autora del 29/10/2026, 13:45:28 y 14:01:46, en DECISIONES): las anclas se leen con la misma lectura de anclas
que usa el código sellado de la etapa B para el §9.2, y una cita da en el punto de referencia si da en cualquiera de las unidades del
ancla; una pregunta cuyas anclas no se pueden leer sale del punto 4, declarada.

Lo que hace:
  1. las anclas: cada ancla de cada pregunta, por analizar_b63.expandir sobre analizar_b63.arbol_e0 de la estructura de la E0 de su TO
     (la lectura de IMPLEMENTACION["unidades_de_un_ancla"], analizar_b63.py:148-149), importadas del código sellado sin editarlo; cada
     unidad que resulta, controlada con parsear_anclas del instrumento, importado sin editarlo, de a una. Una pregunta con alguna unidad
     que el instrumento no lee sale del punto 4 y se declara por su posición en la entrada y por brazo, sin su id ni su texto. El
     archivo --anclas del instrumento lleva, por pregunta, las unidades de todas sus anclas, en su orden y sin repetir;
  2. el instrumento: analizar_b63.exactitud_de_cita, llamada tal cual con esas preguntas (copias de meta_<id>.json y log_r1_<id>.jsonl de
     cada sesión, controladas contra el manifiesto; el instrumento corre con sys.executable), sin las sesiones de las preguntas que salen;
  3. los indicadores: el 1, el 2 y el 3, del instrumento tal cual (el 3 ya es «alguna cita en alguna unidad»,
     ucita2_indicadores_banco.py:486-510); la columna informativa «cada ancla con cita», rearmada por ancla original (un ancla cuenta si
     alguna cita da en alguna de sus unidades), con partir_cita y U2.es_ancla_o_descendiente del instrumento sobre las citas del JSON
     final de cada sesión. El rearmado se controla contra el instrumento en cada sesión: tiene que dar su mismo indicador 3 y su misma
     cuenta de unidades con cita y, en las preguntas sin rango, su misma columna informativa. Si no, la columna se declara sin calcular
     para las preguntas con un rango. Todo por brazo, en fracción cruda, con agregar del instrumento.

  python3 -I -B exactitud_de_cita_9_4_b63.py --clon <b63/v2/b2 de una copia de HEAD> --entrada … --manifiesto-fuera … --banco-b63 …
      --e0 <la E0 del grafo evaluado> --armado-e0 … --ucita <scripts/ucita2_indicadores_banco.py> --salida <carpeta nueva>
Imprime solo la salida y su sha256, o «FRENO: …» (sale con 10), o el FRENO del instrumento (sale con 11), o el tipo de un error
inesperado y su renglón en este archivo, sin su mensaje (sale con 12): ninguna cifra, ningún id, ninguna ancla.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import analizar_b63 as A  # noqa: E402  (el código sellado de la etapa B: solo import)

SHA_ANALIZAR_B63 = "9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb"     # salidas/b/sello_analisis_B63.txt
ESPERADO = {k: A.ESPERADO[k] for k in ("entrada", "manifiesto_fuera", "armado_e0", "ucita", "mapping", "juez_b63",
                                       "aplicar_lectura_tolerante_b63")}
DECISIONES = {
    "la_regla_de_las_anclas": "Las 11 anclas que el instrumento de citas no lee se tratan así cuando se corra el punto 4: se leen con la "
                              "misma lectura de anclas que usa el código sellado de la B para el §9.2, y una cita da en el punto de "
                              "referencia si da en cualquiera de las unidades del ancla. Si esa lectura no se puede aplicar a alguna, esa "
                              "pregunta sale del punto 4, declarada. (decisión de la autora del 29/10/2026, 13:45:28)",
    "las_que_salen": "Acepto tu propuesta para el punto 4 del §9: después de las 18:00, como primera unidad, en la sesión del runner, con la "
                     "regla de mi decisión 4. Las 3 preguntas cuyas anclas no se pueden leer salen del punto 4, declaradas. (decisión de "
                     "la autora del 29/10/2026, 14:01:46)",
}
IMPLEMENTACION = {
    "unidades": "cada ancla, por analizar_b63.expandir sobre analizar_b63.arbol_e0 de la estructura de su TO (su sha256, el del armado de "
                "la E0); cada unidad que resulta va como «to::unidad» y se controla con parsear_anclas del instrumento, de a una",
    "el_archivo_de_anclas": "por pregunta, las unidades de todas sus anclas, en el orden de sus anclas y sin repetir",
    "las_que_salen": "una pregunta con alguna unidad que el instrumento no lee sale entera, con todas sus sesiones; se declara por su "
                     "posición en ids_en_orden de la entrada (desde 1) y por brazo (sus sesiones)",
    "el_instrumento": "analizar_b63.exactitud_de_cita del código sellado, llamada tal cual con las preguntas de la regla y sin las sesiones "
                      "de las que salen",
    "la_columna_informativa": "por sesión: sin JSON final o sin citas, el valor del instrumento; si no, «si» si cada ancla original tiene "
                              "alguna cita parseable (partir_cita) que da en alguna de sus unidades (U2.es_ancla_o_descendiente sobre "
                              "las unidades leídas por parsear_anclas), y «no» si no; los agregados, con agregar del instrumento",
    "el_control_del_rearmado": "en cada sesión, el rearmado tiene que dar el indicador 3 y la cuenta de unidades con cita del instrumento; "
                               "en las preguntas sin rango, además, su columna informativa. Si alguna no da, la columna informativa se "
                               "declara sin calcular para las preguntas con un rango, y se informa la del instrumento para las demás",
    "rango": "una pregunta tiene un rango si alguna de sus anclas trae «..» en su unidad",
}


def importar_instrumento(ruta: Path, esperado: dict):
    """El instrumento de HEAD, importado de su ruta sin editarlo (su sha256 primero)."""
    A.controlado(ruta, esperado["ucita"], "scripts/ucita2_indicadores_banco.py")
    if "ucita2_indicadores_banco" in sys.modules:
        UC = sys.modules["ucita2_indicadores_banco"]
        if A.sha(Path(UC.__file__)) != esperado["ucita"]:
            A.frena("el instrumento importado no es el de su sha256")
        return UC
    spec = importlib.util.spec_from_file_location("ucita2_indicadores_banco", ruta)
    UC = importlib.util.module_from_spec(spec)
    sys.modules["ucita2_indicadores_banco"] = UC
    spec.loader.exec_module(UC)
    return UC


def leible(UC, man: dict, unidad: str) -> bool:
    try:
        UC.parsear_anclas({"_": [unidad]}, man)
        return True
    except SystemExit:
        return False


def unidades_de_las_anclas(qids: list, P: dict, e0_dir: Path, armado: dict) -> dict:
    """{qid: [[unidades del ancla 1], [unidades del ancla 2]]}, con la lectura del código sellado de la B."""
    sha_e0 = {x["to"]: x["sha256"] for x in armado["e0"] if x["archivo"] == f"estructura_{x['to']}.json"}
    arboles: dict = {}
    out = {}
    for q in qids:
        lista = []
        for a in P[q]["anclas"]:
            to, u = a["unidad"].split("::", 1)
            if to not in arboles:
                b = A.controlado(Path(e0_dir) / f"estructura_{to}.json", sha_e0.get(to), "una estructura de la E0")
                arboles[to] = A.arbol_e0(json.loads(b))
            lista.append([f"{to}::{v}" for v in A.expandir(arboles[to], u)])
        out[q] = lista
    return out


def sin_repetir(xs: list) -> list:
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def rearmar(filas: list, por_q: dict, banco, corrida_de_sesion: dict, UC, man: dict) -> dict:
    """La columna informativa rearmada por ancla original, sesión por sesión, con su control contra el instrumento."""
    U2 = UC.U2
    control = {"sesiones": 0, "dan_el_indicador_3_y_las_unidades_con_cita": 0, "sin_rango": 0, "sin_rango_iguales_al_instrumento": 0,
               "con_rango": 0, "cambian_por_el_rearmado": 0}
    nuevas = []
    for f in filas:
        q = f["pregunta"]
        unidades = sin_repetir([u for anc in por_q[q]["unidades"] for u in anc])
        grupos = [[unidades.index(u) for u in anc] for anc in por_q[q]["unidades"]]
        leidas = UC.parsear_anclas({q: unidades}, man)[q]
        c = corrida_de_sesion[f["sesion"]]
        meta = json.loads(banco.leer(banco.sesion(c) / f"meta_{c['sesion']}.json"))
        fj = meta.get("final_json_R4")
        citas = (fj.get("citas") or []) if isinstance(fj, dict) else None
        g = dict(f)
        control["sesiones"] += 1
        if not isinstance(fj, dict) or not citas:
            esperado = UC.SIN_JSON if not isinstance(fj, dict) else UC.SIN_CITAS
            bien = f["info_cada_ancla_con_cita"] == esperado and f["ind3_cita_al_ancla"] == esperado
            g["info_cada_ancla_con_cita"] = esperado
        else:
            det = [UC.partir_cita(x, man) for x in citas]
            con = {j for p in det if p["parseable"] for j, a in enumerate(leidas) if U2.es_ancla_o_descendiente(p["to"], p["punto"], a)}
            bien = len(con) == f["n_anclas_con_cita"] and (UC.SI if con else UC.NO) == f["ind3_cita_al_ancla"]
            g["info_cada_ancla_con_cita"] = UC.SI if all(any(j in con for j in gr) for gr in grupos) else UC.NO
        control["dan_el_indicador_3_y_las_unidades_con_cita"] += bien
        if por_q[q]["rango"]:
            control["con_rango"] += 1
            control["cambian_por_el_rearmado"] += g["info_cada_ancla_con_cita"] != f["info_cada_ancla_con_cita"]
        else:
            control["sin_rango"] += 1
            control["sin_rango_iguales_al_instrumento"] += g["info_cada_ancla_con_cita"] == f["info_cada_ancla_con_cita"]
        nuevas.append(g)
    da = (control["dan_el_indicador_3_y_las_unidades_con_cita"] == control["sesiones"]
          and control["sin_rango_iguales_al_instrumento"] == control["sin_rango"])
    if da:
        return {"calculada": True, "control": control, "agregados": UC.agregar(nuevas)}
    sin_rango = [f for f in filas if not por_q[f["pregunta"]]["rango"]]
    return {"calculada": False, "control": control,
            "declarado": "el rearmado no reproduce al instrumento en alguna sesión: la columna informativa queda sin calcular para las "
                         "preguntas con un rango; para las demás, la del instrumento",
            "agregados_de_las_preguntas_sin_rango": UC.agregar(sin_rango) if sin_rango else {}}


def punto4(rutas: dict, esperado: dict, salida: Path, correr=None) -> dict:
    salida = Path(salida)
    if salida.exists():
        A.frena("--salida ya existe")
    if A.sha(Path(A.__file__)) != SHA_ANALIZAR_B63:
        A.frena("analizar_b63.py no es el del sello de la etapa B")
    AP, JB = A.importar(rutas["clon"], esperado)
    K = JB.K
    A.controlado(rutas["entrada"], esperado["entrada"], "la entrada sellada")
    e = AP.cargar_entrada(rutas["entrada"], K)
    P = A.cargar_preguntas_crudas(e)
    qids = list(e["preguntas"]["ids_en_orden"])
    banco = A.Banco(rutas["banco_b63"], rutas["manifiesto_fuera"], esperado)
    corridas = A.corridas_de(banco, e, K, JB, AP)
    armado = json.loads(A.controlado(rutas["armado_e0"], esperado["armado_e0"], "el armado de la E0"))
    UC = importar_instrumento(Path(rutas["ucita"]), esperado)
    man = UC.manifiesto_desde(None, Path(rutas["e0"]))

    por_ancla = unidades_de_las_anclas(qids, P, rutas["e0"], armado)
    por_q, posiciones = {}, []
    for i, q in enumerate(qids, 1):
        us = por_ancla[q]
        no = [u for anc in us for u in anc if not leible(UC, man, u)]
        rango = any(".." in a["unidad"].split("::", 1)[1] for a in P[q]["anclas"])
        por_q[q] = {"unidades": us, "rango": rango, "sale": bool(no)}
        posiciones.append({"posicion": i, "unidades_por_ancla": [len(anc) for anc in us], "con_un_rango": rango,
                           "unidades_que_el_instrumento_no_lee": len(no), "sale": bool(no)})
    salen = [q for q in qids if por_q[q]["sale"]]
    quedan = [q for q in qids if not por_q[q]["sale"]]
    con_salida = [c for c in corridas if c["salida"]]
    entran = [c for c in con_salida if c["qid"] in set(quedan)]
    P2 = {q: {"anclas": [{"unidad": u} for u in sin_repetir([u for anc in por_q[q]["unidades"] for u in anc])]} for q in quedan}

    salida.mkdir(parents=True)
    r = A.exactitud_de_cita(entran, P2, banco, rutas, esperado, salida, correr)
    out = {"que": "el punto 4 del §9 de B6.3: la exactitud de cita, con la regla de la autora para las anclas que el instrumento no lee",
           "decisiones": DECISIONES, "implementacion": IMPLEMENTACION,
           "anclas": {"preguntas": len(qids), "con_un_rango": sum(1 for q in qids if por_q[q]["rango"]),
                      "por_posicion": posiciones},
           "salen": {"preguntas": len(salen), "posiciones": [i for i, q in enumerate(qids, 1) if por_q[q]["sale"]],
                     "sesiones_por_brazo": A.por_clave(c["brazo"] for c in con_salida if c["qid"] in set(salen))},
           "sesiones_que_entran": len(entran),
           "instrumento": {k: v for k, v in r.items() if k != "agregados"}}
    if r["corrio"]:
        o = json.loads((salida / "trabajo_exactitud_de_cita" / "ucita_B63.json").read_text(encoding="utf-8"))
        de_sesion = {c["sesion"]: c for c in entran}
        if sorted(f["sesion"] for f in o["filas"]) != sorted(de_sesion):
            A.frena("las filas del instrumento no son justo las sesiones que entran")
        out["indicadores"] = {"del_instrumento": r["agregados"],
                              "la_columna_informativa_por_ancla_original": rearmar(o["filas"], por_q, banco, de_sesion, UC, man),
                              "anclas_en_el_indice_de_la_E0": {k: v for k, v in o.get("anclas_en_indice", {}).items() if k != "no_resueltas"}}
    else:
        out["indicadores"] = {"declarado": "el instrumento no terminó bien: el punto 4 queda sin correr y se declara"}
    out["entradas"] = {k: (A.sha(v) if Path(v).is_file() else Path(v).name) for k, v in sorted(rutas.items()) if k != "clon"}
    (salida / "punto4_B63.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out


ARGS = ("clon", "entrada", "manifiesto_fuera", "banco_b63", "e0", "armado_e0", "ucita")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    for a in ARGS:
        ap.add_argument("--" + a.replace("_", "-"), type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args(argv)
    rutas = {k: getattr(a, k) for k in ARGS}
    try:
        out = punto4(rutas, ESPERADO, a.salida)
    except A.Freno as ex:
        print(f"FRENO: {ex}")
        return 10
    except Exception as ex:  # noqa: BLE001  (sin el mensaje: puede traer un id de pregunta o un ancla)
        renglon = next((f.lineno for f in reversed(traceback.extract_tb(ex.__traceback__)) if f.filename == __file__), None)
        print(f"ERROR: {type(ex).__name__} en exactitud_de_cita_9_4_b63.py:{renglon}")
        return 12
    print(f"salida: {a.salida.name}/punto4_B63.json ({hashlib.sha256((a.salida / 'punto4_B63.json').read_bytes()).hexdigest()})")
    if not out["instrumento"]["corrio"]:
        print("FRENO: el instrumento de la exactitud de cita no terminó bien; el resto está escrito")
        return 11
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
