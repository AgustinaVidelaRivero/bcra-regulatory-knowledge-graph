"""U-SEG-OFICIAL, S0-1, punto 6 — censo de las unidades que no entran en una llamada de E1 (USD 0, sin API).

Lee una salida de e0-r2 de los 152 TOs de la partición (`chunks_<to>.json` y `sub_chunking.json`) y simula la
partición por corte de E1 (`correr_e0.particionar_por_corte`, perfil r2) con el código de una copia. Escribe un JSON.

Definiciones (mandato de U-SEG-OFICIAL, S0, punto 6, firmado en e543cb2):
  - U = 13.091 caracteres (`correr_e0.OBJETIVO_CHARS_PARTE`); umbral de la partición por tamaño de E0 = 26.182
    (`correr_e0.UMBRAL_CHARS_SUBCHUNK`), estricto.
  - Capacidad de E1 por texto propio: tokens de salida por carácter (cota de P4 de U-PROMPT-R2: mediana 1,175 y
    máximo 1,498 sobre 6 unidades; `prompt_r2/p4/salida/analisis_p4.json`, `medicion_e`) contra 8.192 tokens del
    primer intento y 16.384 del reintento: una unidad entra si chars_propio × razón ≤ tokens.
  - Clases, sobre las unidades cuyo texto propio pasa la capacidad del reintento con la razón máxima:
      A  no se pueden partir (sin ítems, o es una parte que ya hizo E0: una parte no se vuelve a partir) y su texto
         propio pasa la capacidad del reintento con la mediana;
      B  se parten, y la parte mayor pasa esa capacidad;
      C  quedan en el borde: entre las dos capacidades, sin partir o con su parte mayor;
      D  se parten y la parte mayor entra con la razón máxima.
Uso: python -B censo_unidades_grandes.py --e0 <dir> --codigo <raíz de una copia> --out <json>
     [--razon-mediana 1.175 --razon-max 1.498]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.dont_write_bytecode = True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--codigo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--razon-mediana", type=float, default=1.175)
    ap.add_argument("--razon-max", type=float, default=1.498)
    a = ap.parse_args()
    for p in (a.codigo / "data/experiment/reextraccion_v2/e0_chunking",):
        sys.path.insert(0, str(p))
    import correr_e0 as CE  # noqa: PLC0415

    U, UMBRAL = CE.OBJETIVO_CHARS_PARTE, CE.UMBRAL_CHARS_SUBCHUNK
    T1, T2 = 8192, 16384
    cap_med, cap_max = T2 / a.razon_mediana, T2 / a.razon_max
    cap1_med, cap1_max = T1 / a.razon_mediana, T1 / a.razon_max
    chunks: list[dict] = []
    for p in sorted(a.e0.glob("chunks_*.json")):
        chunks.extend(json.loads(p.read_text(encoding="utf-8")))
    sub = json.loads((a.e0 / "sub_chunking.json").read_text(encoding="utf-8")) \
        if (a.e0 / "sub_chunking.json").exists() else {}

    def tipo(c: dict) -> str:
        if c.get("sub_chunk"):
            return "parte"
        return c.get("rol_bloque") if c["tipo"] == "mini_chunk" else c["tipo"]

    total = len(chunks)
    por_completo = [c for c in chunks if c["chars_completo"] > U]
    por_propio = [c for c in por_completo if c["chars_propio"] > U]
    particiones = [p for to in sub for p in sub[to]["particiones"]]
    no_part = [p for to in sub for p in sub[to]["no_particionables"]]
    sobre_umbral = [c for c in chunks if c["chars_propio"] > UMBRAL and not c.get("sub_chunk")]
    ids_part = {p["id"] for p in particiones}
    ids_no_part = {p["id"] for p in no_part}
    salteadas = [c for c in sobre_umbral if c["id"] not in ids_part and c["id"] not in ids_no_part]
    entre = [c for c in chunks if U < c["chars_propio"] <= UMBRAL and not c.get("sub_chunk")]

    def simular(c: dict) -> dict:
        if c.get("sub_chunk"):
            return {"partible": False, "motivo": "parte_de_E0", "parte_mayor": c["chars_propio"], "partes": None}
        partes, info = CE.particionar_por_corte(c)
        if partes is None:
            return {"partible": False, "motivo": info.get("motivo"), "parte_mayor": c["chars_propio"], "partes": None}
        return {"partible": True, "motivo": None, "parte_mayor": max(s["chars_propio"] for s in partes),
                "partes": [s["chars_propio"] for s in partes]}

    # simulación sobre las unidades de más de U con su herencia que no son partes (como en el mandato)
    no_partes = [c for c in por_completo if not c.get("sub_chunk")]
    sim_57 = {c["id"]: simular(c) for c in no_partes}
    partibles = [i for i, s in sim_57.items() if s["partible"]]
    # clases
    censo = [c for c in chunks if c["chars_propio"] > cap_max]
    filas = []
    for c in censo:
        s = simular(c)
        m = s["parte_mayor"]
        if not s["partible"]:
            clase = "A" if c["chars_propio"] > cap_med else "C"
        elif m > cap_med:
            clase = "B"
        elif m > cap_max:
            clase = "C"
        else:
            clase = "D"
        filas.append(OrderedDict([("id", c["id"]), ("to", c["to"]), ("tipo", tipo(c)),
                                  ("chars_propio", c["chars_propio"]), ("chars_completo", c["chars_completo"]),
                                  ("partible", s["partible"]), ("motivo", s["motivo"]), ("parte_mayor", m),
                                  ("partes", s["partes"]), ("clase", clase)]))
    clases = Counter(f["clase"] for f in filas)
    c_detalle = Counter(("parte_de_E0" if f["motivo"] == "parte_de_E0" else
                         "partida" if f["partible"] else "sin_partir") for f in filas if f["clase"] == "C")
    out = OrderedDict([
        ("e0", str(a.e0.name)),
        ("unidades_totales", total),
        ("U", U), ("umbral_particion_por_tamano", UMBRAL),
        ("capacidad", {"razon_mediana": a.razon_mediana, "razon_max": a.razon_max,
                       "reintento_16384_mediana": round(cap_med, 1), "reintento_16384_max": round(cap_max, 1),
                       "primer_intento_8192_mediana": round(cap1_med, 1),
                       "primer_intento_8192_max": round(cap1_max, 1)}),
        ("sobre_U_con_herencia", {"unidades": len(por_completo), "tos": len({c["to"] for c in por_completo}),
                                  "por_texto_propio": len(por_propio),
                                  "por_propio_mas_herencia": len(por_completo) - len(por_propio),
                                  "por_tipo": dict(sorted(Counter(tipo(c) for c in por_completo).items()))}),
        ("particion_por_tamano_de_E0", {
            "unidades_partidas": len(particiones), "partes": sum(p["n_partes"] for p in particiones),
            "partidas": [{"id": p["id"], "chars_propio": p["chars_propio"], "n_partes": p["n_partes"]}
                         for p in particiones],
            "entre_U_y_umbral_sin_partir": len(entre),
            "sobre_umbral_declaradas_sin_partir": len(no_part),
            "declaradas_por_motivo": dict(sorted(Counter(p["motivo"] for p in no_part).items())),
            "declaradas": no_part,
            "salteadas_sin_declarar": [{"id": c["id"], "chars_propio": c["chars_propio"], "tipo": tipo(c)}
                                       for c in salteadas]}),
        ("simulacion_particion_por_corte_sobre_no_partes", {
            "unidades": len(no_partes), "partibles": len(partibles), "no_partibles": len(no_partes) - len(partibles),
            "parte_mayor_sobre_U": sum(1 for i in partibles if sim_57[i]["parte_mayor"] > U),
            "parte_mayor_sobre_umbral": sum(1 for i in partibles if sim_57[i]["parte_mayor"] > UMBRAL)}),
        ("censo_por_capacidad", {
            "sobre_capacidad_max": {"unidades": len(censo), "tos": len({c["to"] for c in censo})},
            "sobre_capacidad_mediana": {"unidades": sum(1 for c in censo if c["chars_propio"] > cap_med),
                                        "tos": len({c["to"] for c in censo if c["chars_propio"] > cap_med})},
            "clases": dict(sorted(clases.items())), "clase_C_detalle": dict(sorted(c_detalle.items())),
            "clase_A": [f["id"] for f in filas if f["clase"] == "A"]}),
        ("filas", filas)])
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "filas"}, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
