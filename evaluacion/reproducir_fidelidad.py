#!/usr/bin/env python3
"""Reproduce la fidelidad de cada configuración y las 2 comparaciones de la sección 5.7 desde los archivos de esta carpeta. Sin API, sin red y solo con la
biblioteca estándar: importa, sin editarlas, las funciones del análisis sellado (`analizar_b63.py` y `analizar_b64.py`) y compara todo con los resultados
publicados (`analisis_B63.json` y `analisis_B64.json`). Sale con 0 si da igual, y con 1 si algo difiere. Tarda unos 20 segundos por comparación.

  python3 evaluacion/reproducir_fidelidad.py
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
D = RAIZ / "data/experiment/banco_mcp"
COD63, COD64 = D / "b63/analisis/codigo", D / "b64/analisis/codigo"
os.environ["B64_CODIGO_B63"] = str(COD63)
ESTADO = {"correcta": "correcta", "parcial": "no_correcta", "incorrecta": "no_correcta", "incompleta": "incompleta_otra"}


def importar(ruta, nombre):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = m
    spec.loader.exec_module(m)
    return m


RENGLONES = {"preguntas_B6_3.jsonl": 96, "preguntas_B6_4.jsonl": 96, "corridas_B6_3.jsonl": 864, "corridas_B6_4.jsonl": 1152,
             "celdas_B6_3.jsonl": 288, "celdas_B6_4.jsonl": 384}


def leer(nombre):
    marca = (AQUI / "MARCA.txt").read_text(encoding="utf-8").splitlines()[0]
    filas = [json.loads(x) for x in (AQUI / nombre).read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(filas) != RENGLONES[nombre]:
        raise SystemExit(f"FRENO: {nombre} no trae sus {RENGLONES[nombre]} renglones")
    if any(f.get("marca") != marca for f in filas):
        raise SystemExit(f"FRENO: un renglón de {nombre} no trae la marca")
    return filas


def metricas(A, nom, corridas):
    """{escenario: {(pregunta, configuración): (correctas, contadas)}}, con las reglas del análisis; desde las celdas si las hay."""
    cel = AQUI / f"celdas_{nom}.jsonl"
    if cel.exists():
        filas = leer(cel.name)
        return {e: {(f["id_pregunta"], f["configuracion"]): (f["correctas"], 3 - (f["incompletas"] if e == "sin_las_cortadas" else 0))
                    for f in filas if 3 - (f["incompletas"] if e == "sin_las_cortadas" else 0)} for e in A.ESCENARIOS}
    c = [{"qid": f["id_pregunta"], "brazo": f["configuracion"], "estado": ESTADO[f["veredicto"]]} for f in corridas]
    return {e: A.metricas(c, e) for e in A.ESCENARIOS}


def igual(x, y):
    return json.loads(json.dumps(x, sort_keys=True)) == json.loads(json.dumps(y, sort_keys=True))


def pc(x):
    return f"{100 * x:5.1f}"


def informe(titulo, pub, nombres):
    print(f"\n{titulo}: {pub['preguntas']} preguntas, 3 corridas por pregunta y configuración")
    for b, r in pub["por_brazo"].items():
        i = r["intervalo_95"]
        print(f"  {nombres[b]:<34} {pc(r['media'])} %  [{pc(i[0])}, {pc(i[1])}]")
    for f, r in pub["por_comparacion"].items():
        i, h = r["intervalo_95"], r["holm"]
        print(f"  el grafo menos {nombres[f]:<19} {pc(r['media_d'])} p.p. [{pc(i[0])}, {pc(i[1])}]  p = {h['p']:.5f}, rechaza con Holm: {h['rechaza']}")


def main():
    A = importar(COD63 / "analizar_b63.py", "analizar_b63")
    B = importar(COD64 / "analizar_b64.py", "analizar_b64")
    bien = True
    # B6.3
    pub = json.loads((D / "b63/analisis/c/analisis_B63.json").read_text(encoding="utf-8"))
    pre = leer("preguntas_B6_3.jsonl")
    P, qids = {q["id"]: q for q in pre}, [q["id"] for q in pre]
    m = metricas(A, "B6_3", leer("corridas_B6_3.jsonl"))
    n_p, n_b = pub["parametros"]["permutaciones"], pub["parametros"]["remuestreos"]
    pesos = pub["pesos"]["pesos"]
    r = {e: A.confirmatorio(qids, m[e], P, pesos, n_p, n_b, por_documento=(e == "principal")) for e in A.ESCENARIOS}
    cola = set(json.loads((D / "b63/analisis/cola/cola_grafo_evaluado_b63_CANDIDATA_mesa.json").read_text(encoding="utf-8"))["ids"])
    sc = A.sin_la_cola(qids, P, cola)
    resto = [q for q in qids if q not in set(sc["salen"])]
    aparte = {"salen": len(sc["salen"]), "por_causa": sc["por_causa"],
              "analisis": A.confirmatorio(resto, m["principal"], P, pesos, n_p, n_b, por_documento=False)}
    ok = igual(r, pub["confirmatorio"]) and igual(aparte, pub["cifra_aparte_sin_la_cola"])
    bien &= ok
    informe("B6.3", r["principal"], {"kg": "el grafo", "fragmentos_hibrida": "la combinada", "fragmentos_denso": "la densa"})
    print("  igual a analisis_B63.json:", "sí" if ok else "NO")
    # B6.4
    pub = json.loads((D / "b64/analisis/salidas/a/analisis/analisis_B64.json").read_text(encoding="utf-8"))
    pre = leer("preguntas_B6_4.jsonl")
    P, qids = {q["id"]: q for q in pre}, [q["id"] for q in pre]
    m = metricas(A, "B6_4", leer("corridas_B6_4.jsonl"))
    n_p, n_b = pub["parametros"]["permutaciones"], pub["parametros"]["remuestreos"]
    r = {e: B.confirmatorio(qids, m[e], P, n_p, n_b, por_documento=(e == "principal")) for e in A.ESCENARIOS}
    ok = igual(r, pub["confirmatorio"])
    bien &= ok
    informe("B6.4", r["principal"], {"kg": "el grafo con el cambio", "kg_n7": "el grafo sin el cambio (exploratorio)",
                                     "fragmentos_hibrida": "la combinada", "fragmentos_denso": "la densa"})
    print("  igual a analisis_B64.json:", "sí" if ok else "NO")
    return 0 if bien else 1


if __name__ == "__main__":
    sys.exit(main())
