#!/usr/bin/env python3
"""selftest_analizar_b63.py — La prueba de analizar_b63.py con datos de juguete (etapa B del análisis de B6.3). USD 0, sin la API, sin
ningún dato real de B6.3: arma en --trabajo (que no puede existir) un mundo de juguete con la forma de las entradas reales (12
preguntas, 4 documentos, k = 3, los tres brazos: 108 corridas) y corre el análisis sobre él, rama por rama. Los valores esperados los
calcula la prueba por su cuenta, desde su diseño, sin el código del análisis.

Del código de HEAD y de la etapa A usa solo el import (el clon de b63/v2/b2: juez_b63, comun_b63 y mapping; y
aplicar_lectura_tolerante_b63.py de codigo/), con sus sha256. Copia al mundo de juguete dos programas para correrlos sobre él: la
función de proporciones de P1 (`b63_etapa1/scripts/proporciones_P1.py`, tal cual) y el script de la mesa que calcula los pesos
(`decisiones_182_mesa/cruce/aplicar_cruce_ext_mesa.py`, tal cual), que da la salida contra la que el análisis controla sus pesos.

Las ramas:
  - Holm y la regla de la afirmación: el mundo A (supera a una configuración y no a la otra) y el B (supera a las dos); la p de cada
    prueba contra la p exacta de la permutación, enumerada;
  - una pregunta que queda sin corridas en un brazo (en la sensibilidad sin las cortadas);
  - las sensibilidades de las cortadas y de las corridas sin veredicto, contra las métricas esperadas;
  - la adjudicación con «cumplido», «Cumplido», «no cumplido» y «no_cumplido»; los frenos de antes (los ids de la clave, los criterios,
    el modal de los demás y, además, el brazo de la clave y una marca que no es ninguna de las dos), el de después (por la función,
    porque con la planilla sellada y la clave completa ninguna respuesta puede quedar en requiere_adjudicacion) y una planilla que no
    da su sello;
  - el total ponderado (con los pesos que da el script de la mesa) y la versión por documento;
  - el §9: la relevancia por tercio y ponderada, los nodos y las distancias (cada categoría), los expertos sin devueltas/, con dos y
    con tres, y la exactitud de cita (el instrumento simulado: que termina bien y que no);
  - lo operativo y lo declarado; los frenos del manifiesto, de los pesos y de una clasificación que el análisis no conoce;
  - que el análisis no imprime nada, y que dos corridas sobre el mismo mundo dan el mismo JSON, byte a byte.

Imprime solo el nombre de cada control con PASS o FAIL y el sha256 del informe (sin rutas, para que dos corridas den lo mismo).

  python3 -I -B selftest_analizar_b63.py --clon <b63/v2/b2 de una copia de HEAD> --proporciones <proporciones_P1.py>
      --mesa-cruce <aplicar_cruce_ext_mesa.py> --trabajo <carpeta nueva> --informe <json nuevo>
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import analizar_b63 as A  # noqa: E402

SHA_PROPORCIONES = A.ESPERADO["proporciones_P1"]
QIDS = [f"JUG-P{i:02d}" for i in range(1, 13)]
DOC = {"JUG-P01": "doca", "JUG-P02": "docb", "JUG-P03": "docc", "JUG-P04": "ri_transpa", "JUG-P05": "doca", "JUG-P06": "docb",
       "JUG-P07": "doca", "JUG-P08": "doca", "JUG-P09": "docb", "JUG-P10": "docc", "JUG-P11": "docc", "JUG-P12": "ri_transpa"}
SUBTIPO = {"JUG-P07": "condicion", "JUG-P08": "condicion", "JUG-P09": "definicion", "JUG-P10": "definicion", "JUG-P11": "remision",
           "JUG-P12": "remision"}
ANCLAS = {"JUG-P01": ["doca::1.1.1"], "JUG-P02": ["docb::2.1"], "JUG-P03": ["docc::1.2"],
          "JUG-P04": ["ri_transpa::Sbloque1::chapeau_seccion"], "JUG-P05": ["doca::2.2"], "JUG-P06": ["docb::1.1"],
          "JUG-P07": ["doca::1.1.1", "doca::1.1.2"], "JUG-P08": ["doca::1.1..1.2", "doca::2.1"], "JUG-P09": ["docb::1.2::intro", "docb::1.2.5"],
          "JUG-P10": ["docc::S2", "ri_transpa::1.1"], "JUG-P11": ["docc::Sbloque1", "docc::1.1"], "JUG-P12": ["ri_transpa::2.2", "ri_transpa::2.1"]}
NOTA = {"JUG-P01": 1, "JUG-P02": 2, "JUG-P03": 3, "JUG-P04": 4, "JUG-P05": 5, "JUG-P06": 1, "JUG-P07": 2, "JUG-P08": 3, "JUG-P09": 4,
        "JUG-P10": 5, "JUG-P11": 3, "JUG-P12": 4}
PUESTOS = ["riesgo de crédito", "auditoría interna", "cumplimiento normativo"]
COLA = ["docb::1.2", "ri_transpa::Sbloque1"]
# Lo que se espera de los nodos y las distancias (el diseño del kg y de la E0 de juguete)
DISTANCIAS = {"JUG-P07": (1, 2), "JUG-P08": (0, 4), "JUG-P09": (2, 2), "JUG-P10": ("3 o más", "distinto documento"),
              "JUG-P11": ("sin nodo", 3), "JUG-P12": ("sin camino", 2)}
TERCIO_E0 = {"JUG-P07": "baja", "JUG-P08": "alta", "JUG-P09": "baja", "JUG-P10": "distinto documento", "JUG-P11": "media",
             "JUG-P12": "baja"}
COLUMNAS_PLANILLA = ["ficha", "criterio", "veredicto (cumplido / no_cumplido)", "comentario"]
COLUMNAS_EXPERTO = ["codigo", "pregunta", "respuesta_de_referencia", "texto_del_ancla", "se_puede_responder_desde_el_texto (sí / no)",
                    "la_respuesta_es_correcta (sí / parcial / no)", "relevancia_nota (1 a 5)", "relevancia_puesto", "comentario"]


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def escribir(p: Path, contenido) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    b = contenido if isinstance(contenido, bytes) else (contenido if isinstance(contenido, str) else
                                                        json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    b = b.encode("utf-8") if isinstance(b, str) else b
    p.write_bytes(b)
    return sha_b(b)


def csv_bytes(filas: list[list[str]], delim: str = ";", bom: bool = True, todas_entre_comillas: bool = False) -> bytes:
    s = io.StringIO()
    w = csv.writer(s, delimiter=delim, quoting=csv.QUOTE_ALL if todas_entre_comillas else csv.QUOTE_MINIMAL, lineterminator="\r\n")
    w.writerows(filas)
    return (("﻿" if bom else "") + s.getvalue()).encode("utf-8")


# --------------------------------------------------------------------------------------------------------------------- #
# El diseño de las corridas                                                                                             #
# --------------------------------------------------------------------------------------------------------------------- #
def diseno(op: dict) -> dict:
    """{(qid, r, brazo): {"clase", "modales" (si es completa con agregado), "ficha" (si se adjudica), "final" (lo que vale después de la
    adjudicación: C correcta, N no correcta, SV sin veredicto, o la clase si no es completa)}}."""
    d = {}
    for q in QIDS:
        for r in (1, 2, 3):
            for b in A.BRAZOS:
                if b == "kg":
                    bueno = True
                elif b == "fragmentos_hibrida":
                    bueno = False
                elif op.get("denso_malo"):
                    bueno = q == "JUG-P05"
                else:
                    bueno = q not in ("JUG-P10", "JUG-P11", "JUG-P12")
                d[(q, r, b)] = {"clase": "completa", "modales": ["cumplido", "cumplido"] if bueno else ["no_cumplido", "no_cumplido"]}
    especiales = {
        ("JUG-P05", 1, "kg"): {"clase": "incompleta_otra", "motivo": "log R1 11 llamadas vs sesión 12 tool_use MCP", "falta_la_llamada": True},
        ("JUG-P05", 2, "kg"): {"clase": "incompleta_otra", "motivo": "JSON final sin las tres claves del contrato"},
        ("JUG-P05", 3, "kg"): {"clase": "cortada"},
        ("JUG-P02", 1, "fragmentos_denso"): {"clase": "cortada"},
        ("JUG-P06", 3, "fragmentos_hibrida"): {"clase": "falla_infra_sin_terminar", "intentos": 3},
        ("JUG-P03", 2, "fragmentos_denso"): {"clase": "completa", "modales": None},                     # sin veredicto (la regla 3)
        ("JUG-P07", 2, "kg"): {"clase": "completa", "modales": ["cumplido", "dudoso"], "ficha": "A1"},
        ("JUG-P08", 1, "fragmentos_hibrida"): {"clase": "completa", "modales": ["sin_consenso", "cumplido"], "ficha": "A2"},
        ("JUG-P10", 1, "fragmentos_hibrida"): {"clase": "completa", "modales": ["cumplido", "no_cumplido"]},
    }
    especiales[("JUG-P11", 3, "fragmentos_denso")] = {"clase": "completa", "modales": ["dudoso", "dudoso"], "ficha": "A3"}
    if op.get("clasificacion_desconocida"):
        especiales[("JUG-P02", 1, "fragmentos_denso")] = {"clase": "desconocida"}
    d.update(especiales)
    adjudicado = {"A1": ["cumplido", "cumplido"], "A2": ["no_cumplido", "cumplido"], "A3": ["no_cumplido", "cumplido"]}
    for v in d.values():
        if v["clase"] != "completa":
            v["final"] = v["clase"]
        elif v["modales"] is None:
            v["final"] = "SV"
        else:
            ms = adjudicado[v["ficha"]] if "ficha" in v else v["modales"]
            v["final"] = "C" if all(x == "cumplido" for x in ms) else "N"
    return d


def esperadas(d: dict, escenario: str) -> dict:
    """{(qid, brazo): Fraction} con las reglas del §6 y de la regla 3, escritas aparte del análisis."""
    acc: dict = {}
    for (q, r, b), v in d.items():
        f = v["final"]
        if f == "SV" and escenario != "sin_veredicto_como_no_correctas":
            continue
        if f in ("cortada", "incompleta_otra") and escenario == "sin_las_cortadas":
            continue
        n, x = acc.get((q, b), (0, 0))
        acc[(q, b)] = (n + 1, x + (f == "C"))
    return {k: Fraction(x, n) for k, (n, x) in acc.items()}


def media(vs):
    vs = list(vs)
    return float(sum(vs) / len(vs)) if vs else None


def p_exacta(vals: list) -> float:
    obs, n, ge = abs(sum(vals)), len(vals), 0
    for bits in range(2 ** n):
        ge += abs(sum(v if (bits >> i) & 1 else -v for i, v in enumerate(vals))) >= obs
    return ge / 2 ** n


# --------------------------------------------------------------------------------------------------------------------- #
# El mundo de juguete                                                                                                   #
# --------------------------------------------------------------------------------------------------------------------- #
def mundo(W: Path, JB, K, op: dict, proporciones: Path, mesa_cruce: Path) -> tuple[dict, dict, dict]:
    W.mkdir(parents=True)
    esp = {k: A.ESPERADO[k] for k in ("mapping", "juez_b63", "aplicar_lectura_tolerante_b63", "proporciones_P1")}
    d = diseno(op)

    # Las preguntas y la entrada (la ruta de las preguntas, relativa a la carpeta del mundo: la prueba corre el análisis desde ahí)
    preguntas = {"preguntas": [{"id": q, "pregunta": f"Pregunta de juguete {q[-2:]}", "tipo": "varios_puntos" if q in SUBTIPO else "dato_directo",
                                "subtipo": SUBTIPO.get(q), "to": DOC[q],
                                "anclas": [{"rol": rol, "unidad": u} for rol, u in zip(("ancla", "otro_punto"), ANCLAS[q])],
                                "criterios": [{"criterio": f"criterio de juguete {k}", "cita_textual": f"cita de juguete {k}", "unidad": ANCLAS[q][0]}
                                              for k in (1, 2)]} for q in QIDS]}
    sp = escribir(W / "preguntas_juguete.json", preguntas)
    entrada = {"unidad": "juguete", "preguntas": {"ruta": "preguntas_juguete.json", "sha256": sp, "ids_en_orden": QIDS,
                                                  "esquema": {"lista": "preguntas", "id": "id", "pregunta": "pregunta", "criterios": "criterios",
                                                              "criterio": "criterio", "cita": "cita_textual"}},
               "k": 3, "brazos": {b: {"rol": b} for b in A.BRAZOS}}
    esp["entrada"] = escribir(W / "entrada_juguete.json", entrada)
    PQ = {q: {"pregunta": x["pregunta"], "criterios": x["criterios"]} for q, x in zip(QIDS, preguntas["preguntas"])}

    # banco_b63/ con el estado y las sesiones
    R = W / "banco_b63" / "resultados" / "real"
    st = {"bloques": {}}
    ids = {}
    for b in K.orden_bloques(QIDS, 3, sorted(A.BRAZOS)):
        blq = {"final": {}, "intentos_por_brazo": {}, "juez_pendiente": []}
        for x in sorted(A.BRAZOS):
            v = d[(b["qid"], b["r"], x)]
            it = v.get("intentos", 1)
            sid = K.id_sesion(b["qid"], b["r"], x, it)
            blq["final"][x] = {"clasificacion": v["clase"], "id": sid, "intento": it, "salida": f"pasada1/{sid}"}
            blq["intentos_por_brazo"][x] = it
            S = R / "pasada1" / sid
            resp = f"Respuesta de juguete {b['qid'][-2:]} r{b['r']} {x}"
            if v["clase"] != "falla_infra_sin_terminar":
                escribir(S / f"meta_{sid}.json", {"brazo": x, "final_json_R4": {"respuesta": resp, "citas": []}})
                escribir(S / f"log_r1_{sid}.jsonl", "".join(json.dumps({"n": i}) + "\n" for i in range(3)))
            n_ll = 31 if (b["qid"], b["r"], x) == ("JUG-P01", 1, "kg") else 30 if (b["qid"], b["r"], x) == ("JUG-P01", 2, "kg") else 5
            r7 = [{"n": 1, "tool": "mcp__kg__ver_punto", "call_id_log": "c1"}, {"n": 2, "tool": "mcp__kg__buscar_nodos", "call_id_log": "c2"}]
            if v.get("falta_la_llamada"):
                r7.append({"n": 3, "tool": "mcp__kg", "call_id_log": None})
            escribir(S / f"meta_sin_texto_{sid}.json",
                     {"brazo": x, "hb2": {"n_llamadas_log_r1": n_ll}, "mapa_R7": r7,
                      "completitud_R3": {"motivos_incompleta": [v["motivo"]] if "motivo" in v else []},
                      "tokens_R9": {"costo_recomputado": {"total_usd": 0.01},
                                    "por_llamada_api": [{"input_tokens": 100, "cache_read_input_tokens": 50 * k, "cache_creation_input_tokens": 10,
                                                         "output_tokens": 5} for k in (1, 2)]}})
            escribir(S / f"stream_{sid}.jsonl", "{}\n")
            if v["clase"] == "completa":
                ids[(b["qid"], b["r"], x)] = JB.caso_ciego(b["qid"], x, b["r"], resp, PQ)["id_opaco"]
        st["bloques"][b["bloque"]] = blq
    escribir(R / "estado_b63.json", st)
    archivos = sorted(p for p in (W / "banco_b63").rglob("*") if p.is_file())
    man = {"que": "juguete", "archivos": [{"ruta": str(p.relative_to(W)), "sha256": sha_b(p.read_bytes()), "bytes": p.stat().st_size}
                                          for p in archivos]}
    esp["manifiesto_fuera"] = escribir(W / "manifiesto_juguete.json", man)
    if op.get("banco_tocado"):              # el estado cambia después del manifiesto
        p = R / "estado_b63.json"
        p.write_bytes(p.read_bytes() + b" ")

    # Los agregados, la lectura tolerante y la adjudicación
    agregados = []
    for k, v in sorted(d.items()):
        if v["clase"] == "completa" and v["modales"] is not None:
            agregados.append({"id_opaco": ids[k], "n_criterios": 2, "veredicto_pregunta": JB.M.veredicto_pregunta(v["modales"]),
                              "modales": v["modales"], "clasificacion_respuesta_modal": "contenido"})
    agregados.sort(key=lambda x: x["id_opaco"])
    esp["agregados"] = escribir(W / "agregados_juguete.json", {"agregados": agregados, "incompletas": [], "n_agregados": len(agregados)})
    tol_ids = [ids[("JUG-P02", 1, "kg")], ids[("JUG-P04", 2, "fragmentos_denso")]]
    esp["agregados_tolerante"] = escribir(W / "agregados_tolerante_juguete.json",
                                          {"agregados": [x for x in agregados if x["id_opaco"] in tol_ids]})
    esp["veredictos_tolerante"] = escribir(W / "veredictos_tolerante_juguete.jsonl",
                                           "".join(json.dumps({"id_opaco": i, "rep": r}) + "\n" for i, r in
                                                   ((tol_ids[0], 1), (tol_ids[0], 3), (tol_ids[1], 2))))
    fichas = {"A1": ("JUG-P07", 2, "kg"), "A2": ("JUG-P08", 1, "fragmentos_hibrida"), "A3": ("JUG-P11", 3, "fragmentos_denso")}
    clave = {"fichas": []}
    for f, k in fichas.items():
        mods = d[k]["modales"]
        adj = [n for n, m in enumerate(mods, 1) if m in ("dudoso", "sin_consenso")]
        clave["fichas"].append({"ficha": f, "id_opaco": ids[k], "pregunta": k[0], "brazo": k[2], "repeticion": k[1],
                                "criterios_que_se_adjudican": adj,
                                "modal_del_juez_de_los_demas": {str(n): m for n, m in enumerate(mods, 1) if n not in adj}})
    renglones = [["A1", "2"], ["A2", "1"], ["A3", "1"], ["A3", "2"]]
    marcas = {("A1", "2"): "cumplido", ("A2", "1"): "no cumplido", ("A3", "1"): "no_cumplido", ("A3", "2"): "Cumplido"}
    cv = op.get("clave")
    if cv == "falta_una":
        clave["fichas"] = [f for f in clave["fichas"] if f["ficha"] != "A3"]
        renglones = renglones[:2]
    elif cv == "brazo_cambiado":
        clave["fichas"][1]["brazo"] = "kg"
    elif cv == "modal_cambiado":
        clave["fichas"][0]["modal_del_juez_de_los_demas"] = {"1": "no_cumplido"}
    elif cv == "criterio_de_mas":
        clave["fichas"][0]["criterios_que_se_adjudican"] = [1, 2]
        clave["fichas"][0]["modal_del_juez_de_los_demas"] = {}
        renglones = [["A1", "1"]] + renglones
        marcas[("A1", "1")] = "cumplido"
    if op.get("planilla") == "marca_invalida":
        marcas[("A2", "1")] = "parcial"
    esp["clave_adjudicacion"] = escribir(W / "clave_adjudicacion_juguete.json", clave)
    esp["estructura_planilla"] = escribir(W / "estructura_planilla_juguete.json", {"columnas": COLUMNAS_PLANILLA, "renglones": renglones})
    pl = W / "planilla_adjudicacion_b63.csv"
    pb = csv_bytes([COLUMNAS_PLANILLA] + [[f, n, marcas[(f, n)], ""] for f, n in renglones])
    escribir(pl, pb)
    escribir(W / "sello_adjudicacion_juguete.txt", "# sello de juguete: sha256, bytes, hora de modificación y nombre\n"
             "# sellado: 2026-10-29 12:00:00 -0300\n" f"{sha_b(pb)}  {len(pb)}  2026-10-29 11:59:00 -0300  {pl.name}\n")
    if op.get("planilla") == "tocada_despues_del_sello":
        pl.write_bytes(pb.replace(b"no cumplido", b"no cumplido "))

    # D-10, las fechas, la cola, la relevancia
    esp["d10"] = escribir(W / "d10_juguete.json", {"por_brazo": {b: {"con_alguna_marca": i, "n_respuestas": 36} for i, b in enumerate(A.BRAZOS)}})
    esp["fechas"] = escribir(W / "fechas_juguete.json", {"n_bloques_con_fechas_distintas": 0, "bloques_con_fechas_distintas": [],
                                                         "por_brazo_y_fecha": {b: {"2026-10-28": 36} for b in A.BRAZOS}})
    esp["cola"] = escribir(W / "cola_juguete.json", {"ids": COLA})
    esp["relevancia"] = escribir(W / "relevancia_juguete.json",
                                 {"preguntas": [{"id": q, "nota": NOTA[q], "puesto": PUESTOS[i % 3]} for i, q in enumerate(QIDS)]})

    # P1, la tabla del cruce, su sello y la salida de la mesa (el script de la mesa, copiado tal cual, sobre el mundo)
    E1 = W / "b63_etapa1"
    clases = ["RI", "NG_digerible", "NG_necesita_reglas"]
    filas = [["orden", "lote", "unidad", "documento", "clase", "tanda", "tipo", "forma", "otro_punto", "tabular_o_formula",
              "contenido_tabular_fuera_patron", "nota"]]
    for i in range(16):
        tipo, op_ = [("varios puntos", "doca::1.1"), ("varios puntos", "ext::Norma Alfa (juguete)"),
                     ("varios puntos", "ext::Norma Beta Sección 3"), ("dato directo", "")][i % 4]
        if i == 15:
            tipo, op_ = "no decidible", ""
        filas.append([str(i), "1", f"doca::9.{i}", "doca", clases[i % 3], "final", tipo, "", op_, "no", "no", ""])
    s = io.StringIO()
    csv.writer(s, lineterminator="\n").writerows(filas)
    esp["clasificacion_P1"] = escribir(E1 / "clasificacion_P1.csv", s.getvalue())
    esp["poblacion_P1"] = escribir(E1 / "poblacion_P1.json", [{"id": f"x{i}", "clase": c} for i, c in
                                                              enumerate(["RI"] * 10 + ["NG_digerible"] * 7 + ["NG_necesita_reglas"] * 5)])
    (E1 / "scripts").mkdir(parents=True)
    shutil.copyfile(proporciones, E1 / "scripts" / "proporciones_P1.py")
    esp["sensibilidad_P1"] = escribir(E1 / "scripts" / "sensibilidad_P1.py",
                                      '"""Sensibilidad de juguete."""\nimport sys\nfrom pathlib import Path\n\n'
                                      'sys.path.insert(0, str(Path(__file__).resolve().parent))\n'
                                      'from proporciones_P1 import CLASES, ponderada  # noqa: E402,F401\n\n'
                                      'SOLO_HERENCIA = ["doca::9.0", "doca::9.4"]\n')
    C = W / "cruce"
    esp["tabla_cruce"] = escribir(C / "tabla_cruce_juguete.json", {"normas": {"Norma Alfa": {"lado": "dentro", "motivo": "juguete", "to": "x"},
                                                                              "Norma Beta": {"lado": "fuera", "motivo": "juguete", "to": "y"}}})
    esp["sello_tabla"] = escribir(C / "sello_tabla_juguete.txt", f"# sello de juguete\nsha256: {esp['tabla_cruce']}\n")
    shutil.copyfile(mesa_cruce, C / "aplicar_cruce_ext_mesa.py")
    r = subprocess.run([sys.executable, "-I", "-B", str(C / "aplicar_cruce_ext_mesa.py"), str(C / "tabla_cruce_juguete.json"),
                        str(C / "sello_tabla_juguete.txt"), str(E1)], capture_output=True, text=True)
    escribir(C / "consola_de_la_mesa.txt", r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit("la prueba no pudo correr el script de la mesa sobre el mundo de juguete")
    sm = C / "salida_aplicar_cruce_ext_mesa.json"
    if op.get("pesos_mesa_tocados"):
        x = json.loads(sm.read_text(encoding="utf-8"))
        x["sellada"]["peso_varios_puntos_sobre_las_dos_primeras"]["p"] += 0.001
        sm.write_text(json.dumps(x, ensure_ascii=False, indent=1), encoding="utf-8")
    esp["pesos_mesa"] = sha_b(sm.read_bytes())
    pesos_mesa = json.loads(sm.read_text(encoding="utf-8"))

    # El kg y la E0 de juguete
    E0 = W / "e0"
    secciones = [{"tipo": "seccion", "numero": "1", "hijos": [
                     {"tipo": "punto", "numero": "1.1", "hijos": [{"tipo": "punto", "numero": f"1.1.{i}", "hijos": []} for i in (1, 2, 3)]},
                     {"tipo": "punto", "numero": "1.2", "hijos": []}]},
                 {"tipo": "seccion", "numero": "2", "hijos": [{"tipo": "punto", "numero": "2.1", "hijos": []},
                                                              {"tipo": "punto", "numero": "2.2", "hijos": []}]},
                 {"tipo": "seccion", "numero": "bloque1", "hijos": []}]
    armado = {"e0": []}
    for to in ("doca", "docb", "docc", "ri_transpa"):
        armado["e0"].append({"archivo": f"estructura_{to}.json", "to": to, "sha256": escribir(E0 / f"estructura_{to}.json",
                                                                                                  {"to": to, "secciones": secciones})})
        armado["e0"].append({"archivo": f"chunks_{to}.json", "to": to, "sha256": escribir(E0 / f"chunks_{to}.json", [])})
    esp["armado_e0"] = escribir(W / "armado_e0_juguete.json", armado)
    nodo = lambda i, *cs: {"id": i, "label": i, "type": "X", "provenances": [{"chunk_id": c} for c in cs]}  # noqa: E731
    kg = {"nodes": [nodo("n_a111", "doca::1.1.1"), nodo("n_a112", "doca::1.1.2"), nodo("n_comp", "doca::1.2", "doca::2.1"),
                    nodo("n_a22", "doca::2.2"), nodo("n_b12i", "docb::1.2::intro"), nodo("n_b125", "docb::1.2.5"), nodo("n_mid", "docb::2.2"),
                    nodo("n_b21", "docb::2.1"), nodo("n_b11", "docb::1.1"), nodo("n_c21", "docc::2.1"), nodo("x1", None), nodo("x2"),
                    nodo("n_r11", "ri_transpa::1.1"), nodo("n_c11", "docc::1.1"), nodo("n_c12", "docc::1.2"), nodo("n_r22", "ri_transpa::2.2"),
                    nodo("n_r21", "ri_transpa::2.1")],
          "edges": [{"source": a, "target": b, "relation": "r"} for a, b in
                    (("n_a111", "n_a112"), ("n_b12i", "n_mid"), ("n_mid", "n_b125"), ("n_c21", "x1"), ("x1", "x2"), ("x2", "n_r11"))]}
    esp["kg"] = escribir(W / "kg_juguete.json", kg)

    # Los expertos
    X = W / "expertos"
    clave_x = {"filas": [{"codigo": f"E{i:02d}", "id": q, "tipo": "dato_directo"} for i, q in enumerate(QIDS[:6], 1)]}
    sx = escribir(X / "clave_codigos_experto.json", clave_x)
    si = escribir(X / "instrucciones_experto.md", "instrucciones de juguete\n")
    esp["manifiesto_expertos"] = escribir(X / "manifest.txt", f"{sx}  clave_codigos_experto.json\n{si}  instrucciones_experto.md\n")
    respuestas = {1: {"E01": "no", "E02": "no", "E03": "sí"}, 2: {"E01": "no", "E02": "sí", "E03": "sí"}, 3: {"E01": "sí", "E02": "no", "E03": "sí"}}
    for k in range(1, (op.get("devueltas") or 0) + 1):
        filas = [COLUMNAS_EXPERTO] + [[c, "", "", "", respuestas[k].get(c, "sí"), "sí" if c != "E02" else "parcial", str(NOTA[q]),
                                       PUESTOS[(QIDS.index(q) + k) % 3], ""] for c, q in ((f["codigo"], f["id"]) for f in clave_x["filas"])]
        escribir(X / "devueltas" / f"planilla_experto_{k}.csv", csv_bytes(filas, todas_entre_comillas=True))

    # El instrumento de la exactitud de cita: un archivo de juguete (el que corre es el simulado de la prueba)
    esp["ucita"] = escribir(W / "ucita_de_juguete.py", "# instrumento de juguete: la prueba lo simula\n")
    rutas = {"clon": None, "entrada": W / "entrada_juguete.json", "manifiesto_fuera": W / "manifiesto_juguete.json", "banco_b63": W / "banco_b63",
             "agregados": W / "agregados_juguete.json", "agregados_tolerante": W / "agregados_tolerante_juguete.json",
             "veredictos_tolerante": W / "veredictos_tolerante_juguete.jsonl", "planilla": pl, "sello_planilla": W / "sello_adjudicacion_juguete.txt",
             "estructura_planilla": W / "estructura_planilla_juguete.json", "clave_adjudicacion": W / "clave_adjudicacion_juguete.json",
             "d10": W / "d10_juguete.json", "fechas": W / "fechas_juguete.json", "relevancia": W / "relevancia_juguete.json", "etapa1": E1,
             "tabla_cruce": C / "tabla_cruce_juguete.json", "sello_tabla": C / "sello_tabla_juguete.txt", "pesos_mesa": sm,
             "cola": W / "cola_juguete.json", "kg": W / "kg_juguete.json", "e0": E0, "armado_e0": W / "armado_e0_juguete.json",
             "expertos": X, "ucita": W / "ucita_de_juguete.py"}
    return rutas, esp, {"diseno": d, "ids": ids, "pesos_mesa": pesos_mesa}


class Ucita:
    """El instrumento simulado: controla lo que recibe (copias, sin enlaces, solo meta_ y log_r1_ por sesión, el mapa) y escribe su salida."""

    def __init__(self, codigo: int = 0):
        self.codigo, self.control = codigo, None

    def __call__(self, argv):
        ses = argv[argv.index("--sesiones") + 1: argv.index("--anclas")]
        mapa = json.loads(Path(argv[argv.index("--mapa-sesiones") + 1]).read_text(encoding="utf-8"))
        anclas = json.loads(Path(argv[argv.index("--anclas") + 1]).read_text(encoding="utf-8"))
        ok = argv[1:3] == ["-I", "-B"] and len(ses) == len(mapa) and sorted(Path(s).name for s in ses) == sorted(mapa)
        for s in map(Path, ses):
            ok &= s.is_dir() and not s.is_symlink()
            for p in s.iterdir():
                ok &= p.is_file() and not p.is_symlink() and p.name in (f"meta_{s.name}.json", f"log_r1_{s.name}.jsonl")
        ok &= anclas == ANCLAS and all(mapa[s] in QIDS for s in mapa)
        self.control = ok
        if self.codigo == 0:
            Path(argv[argv.index("--out-json") + 1]).write_text(json.dumps({"agregados": {"kg": {"todas": {"cita_al_ancla": {"si_n_de_N": "1 de 1"}}}}}),
                                                               encoding="utf-8")
        return SimpleNamespace(returncode=self.codigo, stdout="consola de juguete\n", stderr="")


def correr(rutas: dict, esp: dict, W: Path, salida: Path, clon: Path, n_perm=A.N_PERM, n_boot=A.N_BOOT, ucita=None):
    """El análisis sobre un mundo, desde la carpeta del mundo; devuelve (salida, freno, lo impreso)."""
    rutas = rutas | {"clon": clon}
    buf = io.StringIO()
    previo = os.getcwd()
    os.chdir(W)
    try:
        with contextlib.redirect_stdout(buf):
            out = A.analizar(rutas, esp, salida, n_perm=n_perm, n_boot=n_boot, ucita=ucita or Ucita())
        return out, None, buf.getvalue()
    except A.Freno as ex:
        return None, str(ex), buf.getvalue()
    finally:
        os.chdir(previo)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clon", type=Path, required=True)
    ap.add_argument("--proporciones", type=Path, required=True)
    ap.add_argument("--mesa-cruce", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--informe", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.trabajo.exists() or a.informe.exists():
        raise SystemExit("--trabajo y --informe no pueden existir")
    if sha_b(a.proporciones.read_bytes()) != SHA_PROPORCIONES:
        raise SystemExit("proporciones_P1.py no es el de su sha256")
    T = a.trabajo.resolve()
    T.mkdir(parents=True)
    AP, JB = A.importar(a.clon, A.ESPERADO)
    K = JB.K
    R: dict = {}
    frenos: dict = {}

    def control(nombre, cond):
        R[nombre] = "PASS" if cond else "FAIL"

    def nuevo(nombre, **op):
        return mundo(T / nombre, JB, K, op, a.proporciones, a.mesa_cruce)

    # --- El mundo A, con los parámetros del pre-registro, dos veces --------------------------------------------------- #
    rA, eA, dA = nuevo("mundo_A")
    uA = Ucita()
    oA, fA, impA = correr(rA, eA, T / "mundo_A", T / "salida_A", a.clon, ucita=uA)
    oA2, fA2, impA2 = correr(rA, eA, T / "mundo_A", T / "salida_A_bis", a.clon, ucita=Ucita())
    control("A_corre_sin_freno", fA is None and fA2 is None)
    if fA is not None:
        frenos["A"] = fA
        R["sha256_salida_A"] = None
    else:
        bA = (T / "salida_A" / "analisis_B63.json").read_bytes()
        control("A_dos_corridas_iguales_byte_a_byte", bA == (T / "salida_A_bis" / "analisis_B63.json").read_bytes())
        control("A_no_imprime_nada", impA == "" and impA2 == "")
        control("A_parametros_del_preregistro", oA["parametros"]["permutaciones"] == 100_000 and oA["parametros"]["remuestreos"] == 10_000
                and oA["parametros"]["semillas"] == {"permutacion": "B63:permutacion:v1", "bootstrap": "B63:bootstrap:v1",
                                                     "permutacion_documento": "B63:permutacion:documento:v1",
                                                     "bootstrap_documento": "B63:bootstrap:documento:v1"})
        R["sha256_salida_A"] = sha_b(bA)
        d = dA["diseno"]
        P = oA["confirmatorio"]["principal"]
        # Holm y la afirmación (A: supera a la híbrida y no a la densa)
        h, n = P["por_comparacion"]["fragmentos_hibrida"], P["por_comparacion"]["fragmentos_denso"]
        control("A_holm_la_menor_con_0_025_y_rechaza", h["holm"]["umbral"] == 0.025 and h["holm"]["rechaza"] is True)
        control("A_holm_la_segunda_con_0_05_y_no_rechaza", n["holm"]["umbral"] == 0.05 and n["holm"]["rechaza"] is False)
        control("A_afirmacion_por_configuracion", P["afirmacion_principal"]["el_grafo_supera_a_los_fragmentos"] is False
                and P["afirmacion_principal"]["por_configuracion"] == {"fragmentos_denso": False, "fragmentos_hibrida": True})
        # Las métricas de cada escenario contra las esperadas, y la p contra la exacta
        for esc in A.ESCENARIOS:
            m = esperadas(d, esc)
            C = oA["confirmatorio"][esc]
            ok = all(abs((C["por_brazo"][b]["media"] or 0) - media(m[(q, b)] for q in QIDS if (q, b) in m)) < 1e-12 for b in A.BRAZOS)
            for f in A.FRAGMENTOS:
                qs = [q for q in QIDS if (q, "kg") in m and (q, f) in m]
                ds = [m[(q, "kg")] - m[(q, f)] for q in qs]
                ok &= C["por_comparacion"][f]["preguntas"] == len(qs) and abs(C["por_comparacion"][f]["media_d"] - media(ds)) < 1e-12
                ok &= abs(C["por_comparacion"][f]["permutacion"]["p"] - p_exacta([int(6 * x) for x in ds])) < 0.01
            control(f"A_{esc}_metricas_y_p_como_las_esperadas", ok)
        control("A_una_pregunta_sin_corridas_en_un_brazo_sale_de_la_comparacion",
                oA["confirmatorio"]["sin_las_cortadas"]["preguntas_que_salen_por_comparacion"] == {"fragmentos_denso": 1, "fragmentos_hibrida": 1}
                and P["preguntas_que_salen_por_comparacion"] == {"fragmentos_denso": 0, "fragmentos_hibrida": 0})
        control("A_sensibilidades_distintas_del_principal",
                oA["confirmatorio"]["sin_las_cortadas"]["por_brazo"]["kg"]["media"] != P["por_brazo"]["kg"]["media"]
                and oA["confirmatorio"]["sin_veredicto_como_no_correctas"]["por_brazo"]["fragmentos_denso"]["media"]
                < P["por_brazo"]["fragmentos_denso"]["media"])
        nombre_de = {"C": "correcta", "N": "no_correcta", "SV": "sin_veredicto", "falla_infra_sin_terminar": "infra_sin_terminar"}
        esperado_estados = {}
        for v in d.values():
            esperado_estados[nombre_de.get(v["final"], v["final"])] = esperado_estados.get(nombre_de.get(v["final"], v["final"]), 0) + 1
        control("A_estados", oA["corridas_por_estado"] == dict(sorted(esperado_estados.items())) and sum(esperado_estados.values()) == 108)
        # La adjudicación (A1 da correcta; A2 y A3, no correctas)
        m = esperadas(d, "principal")
        caso = {c["id"]: c for s in P["subtipos_como_casos"].values() for c in s["casos"]}
        control("A_adjudicacion_en_las_metricas", caso["JUG-P07"]["por_brazo"]["kg"] == 1 and caso["JUG-P08"]["por_brazo"]["fragmentos_hibrida"] == 0
                and caso["JUG-P11"]["por_brazo"]["fragmentos_denso"] == 0 and oA["declarado"]["adjudicadas_por_brazo"]
                == {"fragmentos_denso": 1, "fragmentos_hibrida": 1, "kg": 1})
        # El total ponderado, con los pesos que da el script de la mesa
        pm = dA["pesos_mesa"]
        w = oA["pesos"]["pesos"]
        control("A_pesos_los_de_la_mesa", w == {"sellada": pm["sellada"]["peso_varios_puntos_sobre_las_dos_primeras"]["p"],
                                                "extremo_bajo": pm["sellada"]["peso_varios_puntos_sobre_las_dos_primeras"]["lo"],
                                                "extremo_alto": pm["sellada"]["peso_varios_puntos_sobre_las_dos_primeras"]["hi"],
                                                "herencia": pm["herencia"]["peso_varios_puntos_sobre_las_dos_primeras"]["p"]}
                and w["sellada"] != w["herencia"])
        ok = True
        for nombre, wi in w.items():
            for b in A.BRAZOS:
                vp = media(m[(q, b)] for q in SUBTIPO if (q, b) in m)
                dd = media(m[(q, b)] for q in QIDS if q not in SUBTIPO and (q, b) in m)
                ok &= abs(P["total_ponderado"][nombre]["por_brazo"][b]["valor"] - (wi * vp + (1 - wi) * dd)) < 1e-12
                ok &= None not in P["total_ponderado"][nombre]["por_brazo"][b]["intervalo_95"]
        control("A_total_ponderado_por_brazo", ok)
        ok = True
        for f in A.FRAGMENTOS:
            dv = media(m[(q, "kg")] - m[(q, f)] for q in SUBTIPO)
            dd = media(m[(q, "kg")] - m[(q, f)] for q in QIDS if q not in SUBTIPO)
            ok &= abs(P["secundaria"][f]["diferencia"] - (dv - dd)) < 1e-12 and P["secundaria"][f]["percentil_5"] is not None
            ok &= abs(P["por_tipo"]["varios_puntos"]["por_comparacion"][f]["media_d"] - dv) < 1e-12
        control("A_secundaria_y_por_tipo", ok)
        control("A_subtipos_como_casos", {s: v["preguntas"] for s, v in P["subtipos_como_casos"].items()}
                == {"condicion": 2, "definicion": 2, "remision": 2})
        # Por documento: la p contra la exacta, con los signos por documento
        D = P["por_documento"]
        ok = D["documentos"] == 4
        for f in A.FRAGMENTOS:
            sumas = [int(6 * sum((m[(q, "kg")] - m[(q, f)]) for q in QIDS if DOC[q] == to and (q, "kg") in m and (q, f) in m))
                     for to in sorted(set(DOC.values()))]
            ok &= abs(D["por_comparacion"][f]["permutacion"]["p"] - p_exacta(sumas)) < 0.01
            ok &= D["secundaria"][f]["percentil_5"] is not None or D["secundaria"][f]["remuestreos_sin_cifra"] > 0
        control("A_por_documento", ok and set(D["la_misma_conclusion"]) == {"principal", "secundaria"})
        # La cifra aparte
        control("A_cifra_aparte_sin_la_cola", oA["cifra_aparte_sin_la_cola"]["salen"] == 2 and oA["cifra_aparte_sin_la_cola"]["por_causa"]
                == {"cola": 2, "unidad_que_falta": 1, "las_dos": 1, "total": 2} and oA["cifra_aparte_sin_la_cola"]["analisis"]["preguntas"] == 10)
        # Lo operativo
        o = oA["operativo"]["por_brazo"]
        control("A_operativo", o["kg"]["mas_de_30_llamadas"] == 1 and o["kg"]["al_tope_30_o_mas"] == 2 and o["kg"]["cortadas"] == 1
                and o["kg"]["incompleta_otra"] == 2 and o["fragmentos_denso"]["cortadas"] == 1
                and o["fragmentos_hibrida"]["infra"] == {"sin_terminar": 1, "con_mas_de_un_intento": 1, "intentos_de_mas": 2}
                and o["kg"]["contexto_maximo"]["maximo"] == 210 and abs(o["kg"]["costo_por_pregunta_usd"]["total"] - 0.36) < 1e-9
                and oA["operativo"]["por_brazo_y_tipo"]["kg"]["varios_puntos"]["sesiones"] == 18)
        # Lo declarado
        dc = oA["declarado"]
        control("A_declarado", dc["incompleta_otra"]["total"] == 2 and dc["incompleta_otra"]["con_la_llamada_que_falta_por_brazo"] == {"kg": 1}
                and dc["incompleta_otra"]["por_brazo_y_motivo"] == {"kg | JSON final sin las tres claves del contrato": 1,
                                                                   "kg | log R1 n llamadas vs sesión n tool_use MCP": 1}
                and dc["sin_veredicto"]["por_brazo"] == {"fragmentos_denso": 1}
                and dc["lectura_tolerante"] == {"salidas_por_brazo": {"fragmentos_denso": 1, "kg": 2},
                                                "respuestas_por_brazo": {"fragmentos_denso": 1, "kg": 1}}
                and dc["bloques_con_fechas_distintas"] == 0 and set(dc["D10_por_brazo"]) == set(A.BRAZOS)
                and set(dc["textos"]) == set(A.DECLARADO))
        # El §9: la relevancia
        rv = oA["exploratorio"]["relevancia"]
        ok = rv["preguntas_por_tercio"] == {"alta": 5, "baja": 4, "media": 3}
        for b in A.BRAZOS:
            pares = [(m[(q, b)], NOTA[q]) for q in QIDS if (q, b) in m]
            ok &= abs(rv["ponderado_por_la_nota"]["por_brazo"][b]["valor"] - float(sum(x * w for x, w in pares) / sum(w for _, w in pares))) < 1e-12
        control("A_relevancia_por_tercio_y_ponderada", ok)
        # Los nodos y las distancias
        nd = oA["exploratorio"]["nodos_y_distancias"]
        ok = nd["preguntas_con_dos_anclas"] == 6 and nd["anclas_sin_nodo"] == 2 and nd["cortes_tercios_e0"] == [2, 3]
        for q, (g, e) in DISTANCIAS.items():
            v = nd["por_pregunta"][q]
            ok &= v["distancia_grafo"] == g if not isinstance(g, str) or g != "3 o más" else v["categoria_grafo"] == "3 o más"
            ok &= v["distancia_e0"] == e and v["tercio_e0"] == TERCIO_E0[q]
        ok &= set(nd["por_categoria_grafo"]) == {"0", "1", "2", "3 o más", "sin camino", "sin nodo"}
        control("A_nodos_y_distancias", ok)
        # Los expertos sin devueltas/ y la exactitud de cita
        control("A_expertos_sin_devueltas_se_declara_sin_datos", oA["exploratorio"]["expertos"]["datos"] is False
                and "sensibilidad_sin_las_no_respondibles" not in oA["exploratorio"]["expertos"])
        ec = oA["exploratorio"]["exactitud_de_cita"]
        control("A_exactitud_de_cita_sobre_copias", ec["corrio"] is True and uA.control is True and ec["sesiones"] == 108
                and ec["agregados"] == {"kg": {"todas": {"cita_al_ancla": {"si_n_de_N": "1 de 1"}}}})
        control("A_las_copias_no_son_enlaces", not any(p.is_symlink() for p in (T / "salida_A").rglob("*")))

    # --- El mundo B: supera a las dos configuraciones ------------------------------------------------------------------ #
    rB, eB, dB = nuevo("mundo_B", denso_malo=True)
    oB, fB, _ = correr(rB, eB, T / "mundo_B", T / "salida_B", a.clon)
    control("B_afirmacion_principal", fB is None and oB["confirmatorio"]["principal"]["afirmacion_principal"]
            == {"el_grafo_supera_a_los_fragmentos": True, "por_configuracion": {"fragmentos_denso": True, "fragmentos_hibrida": True}})
    if fB is None:
        mB = esperadas(dB["diseno"], "principal")
        ds = [int(6 * (mB[(q, "kg")] - mB[(q, "fragmentos_denso")])) for q in QIDS]
        control("B_p_de_la_densa_como_la_exacta", abs(oB["confirmatorio"]["principal"]["por_comparacion"]["fragmentos_denso"]["permutacion"]["p"]
                                                      - p_exacta(ds)) < 0.01)
    else:
        frenos["B"] = fB

    # --- Los expertos con dos y con tres planillas devueltas; el instrumento que no termina bien ------------------------ #
    chico = {"n_perm": 2000, "n_boot": 200}
    r2, e2, _ = nuevo("mundo_expertos_2", devueltas=2)
    o2, f2, _ = correr(r2, e2, T / "mundo_expertos_2", T / "salida_expertos_2", a.clon, **chico)
    control("expertos_2_con_dos_los_dos", f2 is None and o2["exploratorio"]["expertos"]["datos"] is True
            and o2["exploratorio"]["expertos"]["no_respondibles"] == ["JUG-P01"]
            and o2["exploratorio"]["expertos"]["sensibilidad_sin_las_no_respondibles"]["salen"] == 1
            and o2["exploratorio"]["expertos"]["en_conjunto"]["se_puede_responder_si"]["n"] == 12
            and o2["exploratorio"]["expertos"]["en_conjunto"]["acuerdo_con_P3_nota"]["x"] == 12
            and list(o2["exploratorio"]["expertos"]["entre_expertos"]) == ["planilla_experto_1 y planilla_experto_2"]
            and o2["exploratorio"]["expertos"]["preguntas_del_material_sin_respuesta"] == [])
    r3, e3, _ = nuevo("mundo_expertos_3", devueltas=3)
    o3, f3, _ = correr(r3, e3, T / "mundo_expertos_3", T / "salida_expertos_3", a.clon, **chico, ucita=Ucita(codigo=2))
    control("expertos_3_por_mayoria", f3 is None and o3["exploratorio"]["expertos"]["no_respondibles"] == ["JUG-P01", "JUG-P02"]
            and o3["exploratorio"]["expertos"]["sensibilidad_sin_las_no_respondibles"]["analisis"]["preguntas"] == 10
            and len(o3["exploratorio"]["expertos"]["entre_expertos"]) == 3)
    control("exactitud_de_cita_que_no_termina_bien_se_declara", f3 is None and o3["exploratorio"]["exactitud_de_cita"]["corrio"] is False
            and o3["exploratorio"]["exactitud_de_cita"]["codigo_de_salida"] == 2 and (T / "salida_expertos_3" / "analisis_B63.json").is_file())

    # --- Los frenos ---------------------------------------------------------------------------------------------------- #
    casos = {"clave_sin_una_de_las_que_requieren": ({"clave": "falta_una"}, "los ids de la clave no son justo las requiere_adjudicacion"),
             "planilla_con_un_criterio_que_no_es_dudoso": ({"clave": "criterio_de_mas"}, "los criterios de la planilla no son justo"),
             "clave_con_otro_modal_en_los_demas": ({"clave": "modal_cambiado"}, "el modal de los demás criterios en la clave"),
             "clave_con_otro_brazo": ({"clave": "brazo_cambiado"}, "la clave no da el brazo"),
             "planilla_con_una_marca_que_no_es_ninguna": ({"planilla": "marca_invalida"}, "una marca de la planilla no es cumplido"),
             "planilla_que_no_da_su_sello": ({"planilla": "tocada_despues_del_sello"}, "la planilla no da el sha256 y los bytes de su sello"),
             "pesos_de_la_mesa_distintos": ({"pesos_mesa_tocados": True}, "los pesos rehechos no dan los de la salida de la mesa"),
             "clasificacion_que_no_se_conoce": ({"clasificacion_desconocida": True}, "una corrida con una clasificación final"),
             "un_archivo_que_no_da_el_manifiesto": ({"banco_tocado": True}, "un archivo de banco_b63 no da el sha256 de su manifiesto")}
    for nombre, (op, texto) in casos.items():
        rf, ef, _ = nuevo(f"mundo_freno_{nombre}", **op)
        of, ff, imp = correr(rf, ef, T / f"mundo_freno_{nombre}", T / f"salida_freno_{nombre}", a.clon, **chico)
        frenos[nombre] = ff
        control(f"freno_{nombre}", of is None and ff is not None and ff.startswith(texto) and imp == ""
                and not (T / f"salida_freno_{nombre}" / "analisis_B63.json").exists())
    try:
        A.sin_requiere({"x": {"veredicto_pregunta": "correcto"}})
        A.sin_requiere({"x": {"veredicto_pregunta": "requiere_adjudicacion"}})
        control("freno_despues_una_que_sigue_en_requiere_adjudicacion", False)
    except A.Freno as ex:
        frenos["una_que_sigue_en_requiere_adjudicacion"] = str(ex)
        control("freno_despues_una_que_sigue_en_requiere_adjudicacion", str(ex).startswith("después de la adjudicación"))
    rs, es_, _ = nuevo("mundo_freno_sin_sha_de_la_cola")
    o_, f_, _ = correr(rs, es_ | {"cola": None}, T / "mundo_freno_sin_sha_de_la_cola", T / "salida_freno_sin_sha_de_la_cola", a.clon, **chico)
    frenos["sin_el_sha256_de_la_cola"] = f_
    control("freno_sin_el_sha256_de_la_cola", o_ is None and f_ == "falta el sha256 de la lista de la cola")

    informe = {"que": "la prueba de analizar_b63.py con datos de juguete (etapa B del análisis de B6.3)",
               "codigo": {"analizar_b63.py": sha_b((AQUI / "analizar_b63.py").read_bytes()),
                          "selftest_analizar_b63.py": sha_b(Path(__file__).read_bytes()),
                          "proporciones_P1.py": sha_b(a.proporciones.read_bytes()), "aplicar_cruce_ext_mesa.py": sha_b(a.mesa_cruce.read_bytes())},
               "controles": R, "frenos": frenos,
               "da": all(v == "PASS" for k, v in R.items() if not k.startswith("sha256_"))}
    a.informe.parent.mkdir(parents=True, exist_ok=True)
    a.informe.write_text(json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in R.items():
        if not k.startswith("sha256_"):
            print(f"{v}  {k}")
    print(f"prueba: {'PASS' if informe['da'] else 'FAIL'} ({sum(v == 'PASS' for v in R.values())} de "
          f"{sum(1 for k in R if not k.startswith('sha256_'))}); informe sha256 {sha_b(a.informe.read_bytes())}")
    return 0 if informe["da"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
