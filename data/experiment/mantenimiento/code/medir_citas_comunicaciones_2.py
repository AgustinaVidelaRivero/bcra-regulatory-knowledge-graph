"""
medir_citas_comunicaciones_2.py — U-MANT, etapa M3: segunda medición de la
tercera fuente del empalme. USD 0, sin red.

Lee data/experiment/mantenimiento/declaracion_citas_comunicaciones_2.json,
escrita y sellada antes de este script, y la aplica sobre la misma ventana de
Comunicaciones «A» que la primera medición. Cambian solo dos cosas, las que
declara la segunda declaración:
  - las fórmulas: las cuatro de la primera más nueve verbos en infinitivo;
  - el nombre del texto ordenado: se une el guion de fin de línea y un título
    compuesto («… ) y …») se acepta por su primera parte si es inequívoca.
Todo lo demás (ventana, extracción de texto, segmento, punto, unidades,
categorías y caso de control) se importa sin cambios del script de la primera
medición, medir_citas_comunicaciones.py, que no se edita. La primera medición
(citas_comunicaciones.json) se lee para el informe al lado y no se toca.

Uso, desde la raíz del repo:
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
    data/experiment/mantenimiento/code/medir_citas_comunicaciones_2.py \\
    --out data/experiment/mantenimiento/citas_comunicaciones_2.json

Salida determinística: dos corridas dan el mismo JSON byte a byte.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import medir_citas_comunicaciones as M1  # noqa: E402 — primera medición, solo import

DECLARACION_2 = AQUI.parent / "declaracion_citas_comunicaciones_2.json"
MEDICION_1 = AQUI.parent / "citas_comunicaciones.json"


def desguionar(s: str, regex: str, reemplazo: str) -> str:
    return re.sub(regex, reemplazo, s)


def titulos_con_alias(decl2: dict) -> tuple[list[dict], list[dict]]:
    """Títulos completos (con la normalización de la segunda declaración) y
    primeras partes de los títulos compuestos; devuelve (candidatos, informe
    de primeras partes aceptadas y descartadas)."""
    g = decl2["nombre_del_texto_ordenado"]["guion_de_fin_de_linea"]
    base = M1.cargar_titulos()
    for t in base:
        t["norm"] = M1.normalizar(desguionar(t["titulo"], g["regex"], g["reemplazo"]))
        t["forma"] = "titulo"
    informe, alias = [], []
    for t in base:
        i = t["titulo"].find(") y ")
        if i < 0:
            continue
        parte = t["titulo"][:i + 1]
        n = M1.normalizar(desguionar(parte, g["regex"], g["reemplazo"]))
        conflictos = sorted(o["to"] for o in base if o is not t and (
            o["norm"] == n or n in o["norm"] or o["norm"] in n))
        reg = {"to": t["to"], "primera_parte": parte, "aceptada": not conflictos,
               "conflictos": conflictos}
        informe.append(reg)
        if not conflictos:
            alias.append({"to": t["to"], "titulo": parte, "grupo": t["grupo"], "norm": n,
                          "forma": "primera_parte"})
    return base + alias, informe


def identificar_to(seg: str, candidatos: list[dict], g: dict) -> tuple[list[dict], str]:
    n = " " + M1.normalizar(desguionar(seg, g["regex"], g["reemplazo"])) + " "
    hallados = [t for t in candidatos if t["norm"] and f" {t['norm']} " in n]
    hallados = [t for t in hallados
                if not any(o is not t and t["norm"] != o["norm"] and t["norm"] in o["norm"]
                           for o in hallados)]
    tos = {t["to"] for t in hallados}
    return hallados, ("uno" if len(tos) == 1 else "ninguno" if not tos else "varios")


def medir(decl1: dict, decl2: dict) -> dict:
    flags = re.IGNORECASE
    f1 = {k: re.compile(v, flags) for k, v in decl2["formulas"]["de_la_primera_declaracion"].items()}
    if decl2["formulas"]["de_la_primera_declaracion"] != decl1["formulas"]:
        raise RuntimeError("las fórmulas de la primera declaración no coinciden: FRENO")
    f2 = {k: re.compile(v, flags) for k, v in decl2["formulas"]["infinitivos_nuevos"].items()}
    re_fin = re.compile(r"\.\s+(?=[A-ZÁÉÍÓÚÑ]|\d+\.\s)")   # la de la primera medición
    re_lista = re.compile(decl1["punto"]["regex_lista"], flags)
    re_num = re.compile(r"\d+(?:\.\d+)*")
    re_secc = re.compile(decl1["punto"]["seccion"].split(":")[0], flags)
    g = decl2["nombre_del_texto_ordenado"]["guion_de_fin_de_linea"]
    candidatos, informe_alias = titulos_con_alias(decl2)
    filas, ref = M1.ventana(decl1)

    comunicaciones, citas = [], []
    for r in filas:
        pdf = M1.REPO / r["archivo_local"]
        reg = {"numero": r["numero"], "fecha_documento": r["fecha_documento"],
               "archivo": r["archivo_local"]}
        if not pdf.exists():
            reg["estado"] = "pdf_ausente"
            comunicaciones.append(reg)
            continue
        reg["sha256"] = M1.sha256_archivo(pdf)
        pags = M1.paginas_texto(pdf)
        reg["estado"] = "leida"
        reg["paginas"] = len(pags)
        n_citas = 0
        for pi, txt in enumerate(pags, start=1):
            ocurrencias = []                                   # (inicio, fin, fórmula, origen)
            for nombre, rx in f1.items():
                ocurrencias += [(m.start(), m.end(), nombre, "primera", m.group(0))
                                for m in rx.finditer(txt)]
            for nombre, rx in f2.items():
                for m in rx.finditer(txt):
                    if not any(a < m.end() and m.start() < b for a, b, _, o, _ in ocurrencias
                               if o == "primera"):
                        ocurrencias.append((m.start(), m.end(), nombre, "infinitivo", m.group(0)))
            for ini, _fin, nombre, origen, texto in sorted(ocurrencias):
                seg = M1.segmento(txt, ini, re_fin)
                numerales, rango = [], False
                ml = re_lista.search(seg)
                if ml:
                    rango = bool(re.search(r"\d\.?\s+a\s+\d", ml.group(1)))
                    numerales = re_num.findall(ml.group(1))
                secc = re_secc.search(seg)
                hallados, cuantos = identificar_to(seg, candidatos, g)
                cita = {"comunicacion": r["numero"], "pagina": pi, "formula": nombre,
                        "origen_formula": origen, "mayuscula_inicial": texto[:1].isupper(),
                        "segmento": seg[:400], "numerales": numerales, "rango": rango,
                        "seccion": secc.group(1) if secc else None}
                if cuantos == "varios":
                    cita["categoria"] = "no_decidible"
                    cita["motivo"] = "más de un TO posible: " + ", ".join(sorted({t["to"] for t in hallados}))
                elif cuantos == "ninguno":
                    cita["categoria"] = "no_mapeable"
                    cita["motivo"] = ("la oración nombra un texto ordenado o normas que no "
                                      "están entre los títulos del inventario"
                                      if re.search(r"texto ordenado|normas sobre", seg, flags)
                                      else "la oración no nombra un texto ordenado")
                else:
                    t = max(hallados, key=lambda h: len(h["norm"]))
                    cita["to"], cita["grupo"] = t["to"], t["grupo"]
                    cita["por_primera_parte"] = all(h["forma"] == "primera_parte" for h in hallados)
                    lista_u = M1.unidades_de(t["to"], t["grupo"])
                    if not numerales:
                        cita["categoria"] = "solo_a_to"
                        cita["motivo"] = "cita de sección" if secc else "sin numeral de punto"
                    elif lista_u is None:
                        cita["categoria"] = "solo_a_to"
                        cita["motivo"] = "el TO no tiene archivo de unidades"
                    else:
                        por_num = {p: M1.unidades_del_punto(lista_u, p) for p in numerales}
                        cita["unidades_por_punto"] = {p: len(u) for p, u in por_num.items()}
                        cita["unidades"] = sorted({u for us in por_num.values() for u in us})
                        if cita["unidades"]:
                            cita["categoria"] = "a_to_y_unidades"
                        else:
                            cita["categoria"] = "solo_a_to"
                            cita["motivo"] = "ningún numeral tiene unidades en la partición"
                citas.append(cita)
                n_citas += 1
        reg["citas"] = n_citas
        comunicaciones.append(reg)

    def resumen(cs: list[dict]) -> dict:
        cat = Counter(c["categoria"] for c in cs)
        return {
            "citas": len(cs),
            "citas_que_nombran_punto_y_to": sum(1 for c in cs if c["numerales"] and c.get("to")),
            "categorias": {k: cat.get(k, 0) for k in ("a_to_y_unidades", "solo_a_to",
                                                        "no_mapeable", "no_decidible")},
            "motivos": dict(sorted(Counter(f"{c['categoria']}: {c['motivo']}" for c in cs
                                           if c.get("motivo")).items())),
        }

    con_formula = [c for c in comunicaciones if c.get("citas")]
    control = [c for c in citas if c["comunicacion"] == decl1["caso_de_control"]["comunicacion"]
               and c["pagina"] == decl1["caso_de_control"]["pagina"]]
    esp = decl1["caso_de_control"]["esperado"]
    control_ok = any(c.get("to") == esp["to"] and esp["punto"] in c["numerales"]
                     and c.get("unidades_por_punto", {}).get(esp["punto"]) == esp["unidades"]
                     for c in control)
    m1 = json.loads(MEDICION_1.read_text(encoding="utf-8"))
    total = resumen(citas)
    return {
        "medicion": "U-MANT M3 — segunda medición de la tercera fuente",
        "declaracion_2": {"ruta": str(DECLARACION_2.relative_to(M1.REPO)),
                          "sha256": M1.sha256_archivo(DECLARACION_2)},
        "declaracion_1": {"ruta": str(M1.DECLARACION.relative_to(M1.REPO)),
                          "sha256": M1.sha256_archivo(M1.DECLARACION)},
        "medicion_1_leida": {"ruta": str(MEDICION_1.relative_to(M1.REPO)),
                             "sha256": M1.sha256_archivo(MEDICION_1)},
        "primeras_partes_de_titulos_compuestos": informe_alias,
        "ventana": {"referencia_recomputada": ref, "comunicaciones_en_ventana": len(filas),
                    "leidas": sum(1 for c in comunicaciones if c["estado"] == "leida")},
        "conteo": {
            "comunicaciones_con_al_menos_una_formula": len(con_formula),
            "citas_por_formula": dict(sorted(Counter(c["formula"] for c in citas).items())),
            "citas_por_origen_de_formula": dict(sorted(Counter(c["origen_formula"] for c in citas).items())),
        },
        "segunda_medicion": total,
        "segunda_medicion_solo_formulas_de_la_primera": resumen(
            [c for c in citas if c["origen_formula"] == "primera"]),
        "segunda_medicion_infinitivos_nuevos": resumen(
            [c for c in citas if c["origen_formula"] == "infinitivo"]),
        "desglose_mayuscula_inicial": {
            "mayuscula_inicial": resumen([c for c in citas if c["mayuscula_inicial"]]),
            "minuscula": resumen([c for c in citas if not c["mayuscula_inicial"]]),
        },
        "categorias_por_grupo": {g_: dict(sorted(Counter(c["categoria"] for c in citas
                                                         if c.get("grupo") == g_).items()))
                                 for g_ in ("corpus_152", "desarrollo_5")},
        "citas_mapeadas_por_primera_parte": sum(1 for c in citas if c.get("por_primera_parte")),
        "primera_medicion_al_lado": {
            "comunicaciones_con_al_menos_una_formula": m1["conteo"]["comunicaciones_con_al_menos_una_formula"],
            "citas": m1["conteo"]["citas"],
            "citas_que_nombran_punto_y_to": m1["conteo"]["citas_que_nombran_punto_y_to"],
            "categorias": m1["categorias"], "motivos": m1["motivos"]},
        "caso_de_control": {"esperado": decl1["caso_de_control"], "citas_de_esa_pagina": control,
                            "reproduce": control_ok},
        "comunicaciones": comunicaciones,
        "citas": citas,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    decl1 = json.loads(M1.DECLARACION.read_text(encoding="utf-8"))
    decl2 = json.loads(DECLARACION_2.read_text(encoding="utf-8"))
    res = medir(decl1, decl2)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("primeras_partes_de_titulos_compuestos", "ventana", "conteo",
                                           "segunda_medicion", "segunda_medicion_solo_formulas_de_la_primera",
                                           "segunda_medicion_infinitivos_nuevos", "desglose_mayuscula_inicial",
                                           "categorias_por_grupo", "citas_mapeadas_por_primera_parte",
                                           "primera_medicion_al_lado")},
                     ensure_ascii=False, indent=1))
    print("caso de control reproduce:", res["caso_de_control"]["reproduce"])
    return 0 if res["caso_de_control"]["reproduce"] else 1


if __name__ == "__main__":
    sys.exit(main())
