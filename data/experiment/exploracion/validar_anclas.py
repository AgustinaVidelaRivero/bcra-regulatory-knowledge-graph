#!/usr/bin/env python3
"""Validador mecánico de anclas para la exploración dirigida (U6).

Recibe preguntas candidatas con ancla declarada y las valida contra el mapa
de territorio quemado (`mapa_territorio_quemado_5TOs_4sets.json`). Emite un
veredicto `apto` / `descartado` por pregunta, con motivo por ancla.

Regla laudada (protocolo `docs/protocolo_u6.md`, decisión 1): territorio
quemado = punto normativo exacto anclado, con sus subpuntos. Las unidades
parcialmente quemadas están disponibles con precaución: una pregunta puede
apuntar a subpuntos no quemados; si su ancla cae en un subpunto quemado o su
descendencia, se descarta. Lectura mecánica de esa regla implementada acá:

- unidad quemada entera .............................. DESCARTADO
- ancla igual a un subpunto quemado o descendiente .... DESCARTADO
- ancla que ABARCA un subpunto quemado (la propia
  unidad parcial, o un ancestro del subpunto quemado):
  su territorio contiene material quemado, no es un
  "subpunto no quemado" ............................... DESCARTADO
- ancla en subpunto no quemado de unidad parcial ...... APTO (unidad_parcial)
- unidad disponible ................................... APTO
- ancla que no resuelve a ninguna unidad del mapa ..... DESCARTADO (no apta
  para uso: sin unidad de referencia no hay validación posible)

Una pregunta con varias anclas es APTO solo si TODAS sus anclas son aptas.

Formato de entrada (JSON, lista de objetos):
    {"id": "X-001", "to": "cap", "anclas": ["2.3.2"], "pregunta": "..."}
  - `to` ∈ {cap, cla, ext, pro, ric}; también se acepta `ancla` (string).
  - una ancla puede venir prefijada con su TO ("cla:6.5.1"), en cuyo caso
    ese prefijo manda sobre el campo `to` (preguntas multi-TO).

Uso:
    python3 validar_anclas.py <mapa.json> <candidatas.json> [--salida out.json]
"""

import argparse
import json
import sys

TOS_VALIDOS = {"cap", "cla", "ext", "pro", "ric"}


def normalizar(ancla):
    """'2.3.1.' -> '2.3.1'; conserva 'S5' tal cual."""
    return ancla.strip().rstrip(".")


def indexar_mapa(mapa):
    """por TO: {unidad: {"grupo": ..., "puntos_quemados": [...]}}"""
    indice = {}
    for to, d in mapa["por_to"].items():
        unidades = {}
        for u in d["quemadas_enteras"]:
            unidades[u["unidad"]] = {"grupo": "quemada_entera", "puntos_quemados": []}
        for u in d["quemadas_parcialmente"]:
            unidades[u["unidad"]] = {
                "grupo": "parcialmente_quemada",
                "puntos_quemados": sorted(u["puntos_quemados"].keys()),
            }
        for u in d["disponibles"]:
            unidades[u["unidad"]] = {"grupo": "disponible", "puntos_quemados": []}
        indice[to] = unidades
    return indice


def resolver_unidad(ancla, unidades):
    """Ancla -> unidad del mapa que la contiene, o None.

    1. Coincidencia exacta con una unidad ('2.3', 'S5').
    2. Prefijo con puntos más largo entre las unidades x.y ('2.12.2.2' -> '2.12',
       nunca '2.1': la comparación agrega '.' para no cruzar segmentos).
    3. Sección S<n> del primer segmento ('10.2.2.1' -> 'S10' si existe).
    """
    if ancla in unidades:
        return ancla
    candidatas = [
        u for u in unidades
        if not u.startswith("S") and (ancla + ".").startswith(u + ".")
    ]
    if candidatas:
        return max(candidatas, key=len)
    seccion = "S" + ancla.split(".")[0]
    if seccion in unidades:
        return seccion
    return None


def validar_ancla(to, ancla, indice):
    """-> (veredicto, motivo, unidad_resuelta)"""
    if to not in indice:
        return "descartado", "to_desconocido: %r" % to, None
    unidades = indice[to]
    unidad = resolver_unidad(ancla, unidades)
    if unidad is None:
        return "descartado", "ancla_no_resuelta: sin unidad en el mapa", None
    info = unidades[unidad]
    if info["grupo"] == "quemada_entera":
        return "descartado", "unidad_quemada_entera", unidad
    if info["grupo"] == "disponible":
        return "apto", "unidad_disponible", unidad
    # parcialmente quemada
    if ancla == unidad:
        return ("descartado",
                "ancla_a_nivel_de_unidad_parcial: abarca subpuntos quemados",
                unidad)
    for q in info["puntos_quemados"]:
        if ancla == q or ancla.startswith(q + "."):
            return ("descartado",
                    "subpunto_quemado_o_descendencia: cae en %s" % q,
                    unidad)
        if q.startswith(ancla + "."):
            return ("descartado",
                    "ancla_abarca_subpunto_quemado: contiene a %s" % q,
                    unidad)
    return "apto", "unidad_parcial_subpunto_no_quemado", unidad


def validar_pregunta(cand, indice):
    to_defecto = cand.get("to", "")
    anclas = cand.get("anclas")
    if anclas is None:
        anclas = [cand["ancla"]] if "ancla" in cand else []
    detalle = []
    for cruda in anclas:
        if ":" in cruda:
            to, ancla = cruda.split(":", 1)
        else:
            to, ancla = to_defecto, cruda
        to = to.strip()
        ancla = normalizar(ancla)
        veredicto, motivo, unidad = validar_ancla(to, ancla, indice)
        detalle.append({
            "to": to, "ancla": ancla, "unidad": unidad,
            "veredicto": veredicto, "motivo": motivo,
        })
    if not detalle:
        veredicto_final = "descartado"
        motivo_final = "sin_ancla_declarada"
    elif all(d["veredicto"] == "apto" for d in detalle):
        veredicto_final = "apto"
        motivo_final = "; ".join("%s:%s %s" % (d["to"], d["ancla"], d["motivo"])
                                 for d in detalle)
    else:
        veredicto_final = "descartado"
        motivo_final = "; ".join("%s:%s %s" % (d["to"], d["ancla"], d["motivo"])
                                 for d in detalle if d["veredicto"] == "descartado")
    return {
        "id": cand.get("id", "?"),
        "veredicto": veredicto_final,
        "motivo": motivo_final,
        "anclas": detalle,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mapa", help="mapa_territorio_quemado_5TOs_4sets.json")
    ap.add_argument("candidatas", help="JSON con la lista de preguntas candidatas")
    ap.add_argument("--salida", help="ruta para el JSON detallado (opcional)")
    args = ap.parse_args()

    with open(args.mapa, encoding="utf-8") as f:
        mapa = json.load(f)
    with open(args.candidatas, encoding="utf-8") as f:
        candidatas = json.load(f)
    if not isinstance(candidatas, list):
        sys.exit("candidatas debe ser una lista JSON de objetos")

    indice = indexar_mapa(mapa)
    resultados = [validar_pregunta(c, indice) for c in candidatas]

    for r in resultados:
        print("%-12s %-10s %s" % (r["id"], r["veredicto"].upper(), r["motivo"]))
    aptos = sum(1 for r in resultados if r["veredicto"] == "apto")
    print("-- %d candidatas: %d aptas, %d descartadas" %
          (len(resultados), aptos, len(resultados) - aptos))

    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=1)
        print("-- detalle en %s" % args.salida)


if __name__ == "__main__":
    main()
