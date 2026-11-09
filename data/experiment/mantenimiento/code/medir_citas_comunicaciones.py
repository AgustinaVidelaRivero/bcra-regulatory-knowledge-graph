"""
medir_citas_comunicaciones.py — U-MANT, etapa M2 (e): medición de la tercera
fuente del empalme, las Comunicaciones «A» que citan el punto que modifican.

USD 0, sin red. Lee las Comunicaciones «A» guardadas en data/raw (filas
`comunicacion_A` de data/raw/manifiesto.csv; PDFs locales, no versionados) y
registra el sha256 de cada PDF que lee.

La ventana, las fórmulas, el segmento de cada cita, la extracción del punto, la
regla del nombre del texto ordenado y las categorías NO están en este código:
se leen de data/experiment/mantenimiento/declaracion_citas_comunicaciones.json,
escrita y sellada antes de este script. El sha256 de la declaración queda en la
salida.

Pasos (mandato U-MANT, M2 e):
  1. ventana: doce meses previos a la fecha_documento máxima del manifiesto;
  2. fórmulas declaradas; las de descubrimiento se reportan aparte, sin sumar;
  3. conteo: Comunicaciones con al menos una fórmula, citas, citas que nombran
     un punto y un texto ordenado;
  4. mapeo de cada cita a TO y a unidades, en cuatro categorías;
  5. caso de control: «A» 8432, página 1 → snp_psp, punto 1.3, 5 unidades.

Uso, desde la raíz del repo:
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \\
    data/experiment/mantenimiento/code/medir_citas_comunicaciones.py \\
    --out data/experiment/mantenimiento/citas_comunicaciones.json

Salida determinística (sin fechas de corrida): dos corridas dan el mismo JSON.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[3]
DECLARACION = AQUI.parent / "declaracion_citas_comunicaciones.json"
MANIFIESTO = REPO / "data" / "raw" / "manifiesto.csv"
INVENTARIO = REPO / "data" / "experiment" / "escalado_prep" / "inventario_tos.csv"
RESUMEN = REPO / "data" / "experiment" / "escalado_prep" / "inventario_resumen.json"
PARTICION = REPO / "data" / "experiment" / "segmentacion_84" / "b584_particion"
E0_TANDA0 = REPO / "data" / "experiment" / "reextraccion_v2" / "e0_chunking" / "salida_tanda0"


def sha256_archivo(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def cargar_titulos() -> list[dict]:
    out = []
    with INVENTARIO.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({"to": r["id"], "titulo": r["titulo_oficial"], "grupo": "corpus_152",
                        "norm": normalizar(r["titulo_oficial"])})
    for s in json.loads(RESUMEN.read_text(encoding="utf-8"))["subset_excluido"]:
        out.append({"to": s["id_interno"], "titulo": s["titulo"], "grupo": "desarrollo_5",
                    "norm": normalizar(s["titulo"])})
    return out


_UNIDADES: dict[str, list[tuple[str, str]] | None] = {}


def unidades_de(to: str, grupo: str) -> list[tuple[str, str]] | None:
    """(id, unidad) de cada unidad del TO: se cuentan ids, no valores de
    `unidad`, porque los mini-chunks de un punto comparten su `unidad`."""
    if to not in _UNIDADES:
        p = (PARTICION / to / f"chunks_{to}.json" if grupo == "corpus_152"
             else E0_TANDA0 / f"chunks_{to}.json")
        _UNIDADES[to] = ([(c["id"], c["unidad"]) for c in json.loads(p.read_text(encoding="utf-8"))]
                         if p.exists() else None)
    return _UNIDADES[to]


def unidades_del_punto(lista: list[tuple[str, str]], punto: str) -> list[str]:
    return sorted({i for i, u in lista if u == punto or u.startswith(punto + ".")})


def ventana(decl: dict) -> tuple[list[dict], str]:
    filas = [r for r in csv.DictReader(MANIFIESTO.open(encoding="utf-8"))
             if r["categoria"] == decl["fuente"]["categoria"]]
    ref = max(r["fecha_documento"] for r in filas if r["fecha_documento"])
    v = decl["ventana"]
    desde, hasta = date.fromisoformat(v["desde_exclusive"]), date.fromisoformat(v["hasta_inclusive"])
    if ref != v["hasta_inclusive"]:
        raise RuntimeError(f"la fecha de referencia recomputada ({ref}) no es la declarada "
                           f"({v['hasta_inclusive']}): FRENO, la declaración no se ajusta")
    sel = [r for r in filas if r["fecha_documento"]
           and desde < date.fromisoformat(r["fecha_documento"]) <= hasta]
    return sorted(sel, key=lambda r: (r["fecha_documento"], r["numero"])), ref


def paginas_texto(pdf: Path) -> list[str]:
    import pdfplumber
    with pdfplumber.open(str(pdf)) as d:
        return [" ".join((p.extract_text() or "").split()) for p in d.pages]


def segmento(texto: str, inicio: int, re_fin: re.Pattern) -> str:
    """Desde la fórmula hasta lo primero entre el primer ':' (incluido), el
    primer fin de oración de `re_fin` y 600 caracteres (declaración,
    segmento_de_la_cita)."""
    resto = texto[inicio:inicio + 600]
    cortes = []
    c = resto.find(":")
    if c >= 0:
        cortes.append(c + 1)
    m = re_fin.search(resto)
    if m:
        cortes.append(m.start())
    return resto[:min(cortes)] if cortes else resto


def identificar_to(seg: str, titulos: list[dict]) -> tuple[list[dict], str]:
    n = " " + normalizar(seg) + " "
    hallados = [t for t in titulos if t["norm"] and f" {t['norm']} " in n]
    # gana el más largo; se descartan los contenidos en otro hallado
    hallados = [t for t in hallados
                if not any(o is not t and t["norm"] != o["norm"] and t["norm"] in o["norm"]
                           for o in hallados)]
    distintos = {t["norm"] for t in hallados}
    return hallados, ("uno" if len(distintos) == 1 else "ninguno" if not distintos else "varios")


def medir(decl: dict) -> dict:
    flags = re.IGNORECASE
    formulas = {k: re.compile(v, flags) for k, v in decl["formulas"].items()}
    re_desc = re.compile(decl["descubrimiento"]["regex"], flags)
    re_fin = re.compile(r"\.\s+(?=[A-ZÁÉÍÓÚÑ]|\d+\.\s)")  # idéntica a la declarada (segmento_de_la_cita)
    re_lista = re.compile(decl["punto"]["regex_lista"], flags)
    re_num = re.compile(r"\d+(?:\.\d+)*")
    re_secc = re.compile(decl["punto"]["seccion"].split(":")[0], flags)
    titulos = cargar_titulos()
    filas, ref = ventana(decl)

    comunicaciones, citas, descubiertas = [], [], Counter()
    for r in filas:
        pdf = REPO / r["archivo_local"]
        reg = {"numero": r["numero"], "fecha_documento": r["fecha_documento"],
               "archivo": r["archivo_local"]}
        if not pdf.exists():
            reg["estado"] = "pdf_ausente"
            comunicaciones.append(reg)
            continue
        reg["sha256"] = sha256_archivo(pdf)
        try:
            pags = paginas_texto(pdf)
        except Exception as exc:  # noqa: BLE001 — se registra textual
            reg["estado"] = f"lectura_fallida: {type(exc).__name__}"
            comunicaciones.append(reg)
            continue
        reg["estado"] = "leida"
        reg["paginas"] = len(pags)
        n_citas = 0
        for pi, txt in enumerate(pags, start=1):
            ocupados = []
            for nombre, rx in formulas.items():
                for m in rx.finditer(txt):
                    ocupados.append((m.start(), m.end()))
                    seg = segmento(txt, m.start(), re_fin)
                    numerales, rango = [], False
                    ml = re_lista.search(seg)
                    if ml:
                        lista = ml.group(1)
                        rango = bool(re.search(r"\d\.?\s+a\s+\d", lista))
                        numerales = [x for x in re_num.findall(lista)]
                    secc = re_secc.search(seg)
                    hallados, cuantos = identificar_to(seg, titulos)
                    cita = {"comunicacion": r["numero"], "pagina": pi, "formula": nombre,
                            "segmento": seg[:400], "numerales": numerales, "rango": rango,
                            "seccion": secc.group(1) if secc else None}
                    if cuantos == "varios":
                        cita["categoria"] = "no_decidible"
                        cita["motivo"] = "más de un TO posible: " + ", ".join(
                            sorted({t["to"] for t in hallados}))
                    elif cuantos == "ninguno":
                        cita["categoria"] = "no_mapeable"
                        cita["motivo"] = ("la oración nombra un texto ordenado o normas que no "
                                          "están entre los títulos del inventario"
                                          if re.search(r"texto ordenado|normas sobre", seg, flags)
                                          else "la oración no nombra un texto ordenado")
                    else:
                        t = hallados[0]
                        cita["to"], cita["grupo"] = t["to"], t["grupo"]
                        lista_u = unidades_de(t["to"], t["grupo"])
                        if not numerales:
                            cita["categoria"] = "solo_a_to"
                            cita["motivo"] = ("cita de sección" if secc else "sin numeral de punto")
                        elif lista_u is None:
                            cita["categoria"] = "solo_a_to"
                            cita["motivo"] = "el TO no tiene archivo de unidades"
                        else:
                            por_num = {p: unidades_del_punto(lista_u, p) for p in numerales}
                            cita["unidades_por_punto"] = {p: len(u) for p, u in por_num.items()}
                            cita["unidades"] = sorted({u for us in por_num.values() for u in us})
                            if cita["unidades"]:
                                cita["categoria"] = "a_to_y_unidades"
                            else:
                                cita["categoria"] = "solo_a_to"
                                cita["motivo"] = "ningún numeral tiene unidades en la partición"
                    citas.append(cita)
                    n_citas += 1
            for m in re_desc.finditer(txt):
                if not any(a <= m.start() < b for a, b in ocupados):
                    descubiertas[normalizar(m.group(0))] += 1
        reg["citas"] = n_citas
        comunicaciones.append(reg)

    cat = Counter(c["categoria"] for c in citas)
    con_formula = [c for c in comunicaciones if c.get("citas")]
    nombran_punto_y_to = [c for c in citas if c["numerales"] and c.get("to")]
    control = [c for c in citas if c["comunicacion"] == decl["caso_de_control"]["comunicacion"]
               and c["pagina"] == decl["caso_de_control"]["pagina"]]
    esp = decl["caso_de_control"]["esperado"]
    control_ok = any(c.get("to") == esp["to"] and esp["punto"] in c["numerales"]
                     and c.get("unidades_por_punto", {}).get(esp["punto"]) == esp["unidades"]
                     for c in control)
    return {
        "medicion": "U-MANT M2 (e) — citas de Comunicaciones «A» a puntos de textos ordenados",
        "declaracion": {"ruta": str(DECLARACION.relative_to(REPO)),
                        "sha256": sha256_archivo(DECLARACION)},
        "ventana": {"referencia_recomputada": ref, "desde_exclusive": decl["ventana"]["desde_exclusive"],
                    "hasta_inclusive": decl["ventana"]["hasta_inclusive"],
                    "comunicaciones_en_ventana": len(filas),
                    "leidas": sum(1 for c in comunicaciones if c["estado"] == "leida"),
                    "no_leidas": sorted((c["numero"], c["estado"]) for c in comunicaciones
                                        if c["estado"] != "leida")},
        "conteo": {
            "comunicaciones_con_al_menos_una_formula": len(con_formula),
            "citas": len(citas),
            "citas_por_formula": dict(sorted(Counter(c["formula"] for c in citas).items())),
            "citas_que_nombran_punto_y_to": len(nombran_punto_y_to),
            "citas_que_nombran_punto_y_to_por_grupo": dict(sorted(
                Counter(c["grupo"] for c in nombran_punto_y_to).items())),
        },
        "categorias": {k: cat.get(k, 0) for k in ("a_to_y_unidades", "solo_a_to", "no_mapeable",
                                                    "no_decidible")},
        "categorias_por_grupo": {g: dict(sorted(Counter(c["categoria"] for c in citas
                                                        if c.get("grupo") == g).items()))
                                 for g in ("corpus_152", "desarrollo_5")},
        "motivos": dict(sorted(Counter(f"{c['categoria']}: {c['motivo']}" for c in citas
                                       if c.get("motivo")).items())),
        "citas_con_rango": sum(1 for c in citas if c["rango"]),
        "formulas_de_descubrimiento_no_sumadas": dict(sorted(descubiertas.items())),
        "caso_de_control": {"esperado": decl["caso_de_control"], "citas_de_esa_pagina": control,
                            "reproduce": control_ok},
        "comunicaciones": comunicaciones,
        "citas": citas,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    decl = json.loads(DECLARACION.read_text(encoding="utf-8"))
    res = medir(decl)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("ventana", "conteo", "categorias", "categorias_por_grupo",
                                           "citas_con_rango", "formulas_de_descubrimiento_no_sumadas")},
                     ensure_ascii=False, indent=1))
    print("caso de control reproduce:", res["caso_de_control"]["reproduce"])
    return 0 if res["caso_de_control"]["reproduce"] else 1


if __name__ == "__main__":
    sys.exit(main())
