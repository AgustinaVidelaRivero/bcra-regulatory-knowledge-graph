"""La lista de la tanda 1, el sucesor de ri_oc (D-1), U y el tope (U-SEG-OFICIAL, S2, tramo 1; USD 0, sin API).

Uso: python -B lista_tanda1_S2.py --e0 <salida de E0 de los 152> --raiz <copia del repo> --out <json>

Lee, sin escribir nada fuera de --out:
- de la E0 corregida (--e0): `chunks_<to>.json` (unidades de extracción e ids de chunk), `conteos.json`
  (`modo_lectura`) y `cobertura.json` (`cobertura_exacta`);
- de la copia del repo (--raiz): el inventario de los 152 (`categoria`), la partición legada (clase y modo de
  lectura legados), el manifiesto de S0-6b (`unidades_por_to`), el manifiesto de los 152 de S1-ter
  (`rol_alcance`) y el registro de alcance por tanda (filas por TO).

Reglas (despacho de S2, versión 2 del 15/10/2026; decisiones D-1 y D-2 de la autora):
- la lista de trabajo es el ejemplo del §7 del protocolo con ri_pgn en lugar de ri_cc; sale ri_oc
  (enmienda 8, decisión 1);
- el sucesor de ri_oc (estrato 6) es el elegible con modo `sin_raiz` en la E0 corregida con más unidades de
  extracción, con desempate por id, que no supere en más de 600 unidades a ri_oc; si el primero lo supera, va el
  siguiente de la lista ordenada que no lo supere;
- elegible: no está en la lista; no es de la tanda 0 ni del desarrollo; no es uno de los 14 de fuera ni ri_ao,
  ri_cc o ri2_pm; no es uno de los 15 de las decisiones 1 y 2 de la enmienda 8; cobertura exacta y ningún id de
  chunk repetido en la E0 corregida;
- U es la suma de las unidades de extracción de los 20; el tope es 1,45 × U × 0,021115.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

LISTA_TRABAJO = {
    1: ["ayccef", "expaef", "opefci", "adrei"],
    2: ["ri_ccna", "ri_rml", "ri_gerc", "ri_pgn"],
    3: ["snp_cheq", "ceninf", "cirmo3", "snp_tr"],
    4: ["lingeef", "depaho", "cajasc"],
    5: ["manori", "efemin", "nmcief"],
    6: ["ri_dcpc", "ri_oc"],
}
SALE = "ri_oc"
ESTRATO_SUCESOR = 6
MODO_SUCESOR = "sin_raiz"
MARGEN_TOPE_D1 = 600
TANDA0 = ["ctacte", "lingob", "polcre", "pagjub", "docvig"]
DESARROLLO = ["cap", "cla", "ext", "pro", "ric"]
# docs/protocolo_entre_tandas.md:163-166: los 12 no segmentables y los 2 parciales declarados
NO_SEGMENTABLES = ["optico", "plandecuentas", "ri_chr", "ri_con", "ri_fcem", "ri_itme", "ri_pfmipyme", "ri_pscpp",
                   "ri_pspii", "ri_rem", "ri_spi", "ri_tii"]
PARCIALES = ["manual", "ri2_pm"]
OTROS_FUERA = ["ri_ao", "ri_cc", "ri2_pm"]
# enmienda 8, decisiones 1 y 2 al firmar
ENMIENDA8_D1 = ["ri_oc", "ri_icpipsp", "ri_pnp", "ri_psprca", "gerc", "ri_spi"]
ENMIENDA8_D2 = ["dmrd", "ri2_cs", "ri_cc", "ri_ccpnp", "ri_con", "ri_niif", "ri_pnp", "nmaeef", "ri_saofe", "ri2_ae"]
TARIFA = 0.021115
FACTOR = 1.45

INVENTARIO = "data/experiment/escalado_prep/inventario_tos.csv"
PARTICION = "data/experiment/segmentacion_84/b584_particion/particion_152.json"
CONTEOS_LEGADOS = "data/experiment/segmentacion_84/b584_particion/conteos_b584.json"
MANIFIESTO_S06B = "data/experiment/segmentacion_oficial_e0r2/s0_6/b/manifiestos/manifest_salida_e0_152_S0-6b.json"
MANIFIESTO_152 = "data/experiment/segmentacion_oficial_e0r2/s1ter/manifiesto/segmentacion_oficial_e0r2_152.json"
REGISTRO = "data/experiment/catalogo_unico/registro_alcance_por_tanda.md"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def filas_registro(texto: str) -> dict[str, list[dict]]:
    """TO → filas del registro de alcance donde aparece en la primera columna de una tabla (o en la segunda, en la
    tabla de candidatos, que lista varios TOs por fila), con su sección y su línea."""
    out: dict[str, list[dict]] = {}
    seccion = None
    for n, linea in enumerate(texto.split("\n"), 1):
        if linea.startswith("## "):
            seccion = linea[3:].strip()
            continue
        if not linea.startswith("|") or set(linea.replace("|", "").strip()) <= set("-: "):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if celdas[0] in ("TO", "estado"):
            continue
        if seccion and seccion.startswith("Candidatos"):
            ids = re.findall(r"[a-z0-9_]+", re.sub(r"\(.*?\)", "", celdas[1]))
            tipo = "candidato (no decidido)" if not celdas[0].startswith("DECIDIDO") else "decidido"
        else:
            ids = [celdas[0]]
            tipo = "decisión"
        for t in ids:
            out.setdefault(t, []).append({"seccion": seccion, "linea": n, "tipo": tipo, "decision": celdas[2]
                                          if tipo == "decisión" else celdas[0][:60]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--raiz", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    e0, raiz = a.e0, a.raiz

    conteos = json.loads((e0 / "conteos.json").read_text(encoding="utf-8"))
    cobertura = json.loads((e0 / "cobertura.json").read_text(encoding="utf-8"))
    tos152 = sorted(p.name[len("chunks_"):-5] for p in e0.glob("chunks_*.json"))
    assert len(tos152) == 152, len(tos152)
    unidades, repetidos = {}, {}
    for to in tos152:
        ch = json.loads((e0 / f"chunks_{to}.json").read_text(encoding="utf-8"))
        unidades[to] = len(ch)
        c = Counter(x["id"] for x in ch)
        repetidos[to] = sum(v - 1 for v in c.values() if v > 1)
    modo = {to: conteos[to].get("modo_lectura") for to in tos152}
    cob = {to: cobertura[to]["cobertura_exacta"] for to in tos152}

    inv = {r["id"]: r for r in csv.DictReader(open(raiz / INVENTARIO, encoding="utf-8"))}
    part = json.loads((raiz / PARTICION).read_text(encoding="utf-8"))["por_to"]
    conteos_leg = json.loads((raiz / CONTEOS_LEGADOS).read_text(encoding="utf-8"))
    man = json.loads((raiz / MANIFIESTO_S06B).read_text(encoding="utf-8"))
    man152 = {t["id"]: t for t in json.loads((raiz / MANIFIESTO_152).read_text(encoding="utf-8"))["tos"]}
    registro = filas_registro((raiz / REGISTRO).read_text(encoding="utf-8"))

    # controles de las listas escritas contra los artefactos
    fuera14 = NO_SEGMENTABLES + PARCIALES
    assert sorted(t for t, v in part.items() if v["clase"] == "no_segmentable_declarado") == sorted(NO_SEGMENTABLES)
    assert sorted(t for t, v in part.items() if v["clase"] == "parcial_declarado") == sorted(PARCIALES)
    assert set(inv) == set(tos152) and all(t in tos152 for t in TANDA0) and not set(DESARROLLO) & set(tos152)
    quince = sorted(set(ENMIENDA8_D1) | set(ENMIENDA8_D2))
    assert len(quince) == 15, quince

    en_lista = [t for e in LISTA_TRABAJO.values() for t in e]
    assert len(en_lista) == 20 and len(set(en_lista)) == 20

    motivos = {}
    for t in tos152:
        m = []
        if t in en_lista:
            m.append("en la lista de trabajo")
        if t in TANDA0:
            m.append("tanda 0")
        if t in fuera14:
            m.append("de los 14 de fuera")
        if t in OTROS_FUERA:
            m.append("ri_ao, ri_cc o ri2_pm")
        if t in quince:
            m.append("enmienda 8, decisiones 1 y 2")
        if not cob[t]:
            m.append("cobertura no exacta")
        if repetidos[t]:
            m.append("ids de chunk repetidos")
        if modo[t] != MODO_SUCESOR:
            m.append(f"modo {modo[t]}")
        motivos[t] = m
    elegibles_sin_raiz = sorted((t for t in tos152 if not motivos[t]), key=lambda t: (-unidades[t], t))
    tope_d1 = unidades[SALE] + MARGEN_TOPE_D1
    candidatos = [{"orden": i, "to": t, "unidades": unidades[t], "modo_lectura": modo[t],
                   "supera_tope": unidades[t] > tope_d1} for i, t in enumerate(elegibles_sin_raiz, 1)]
    sucesor = next(c["to"] for c in candidatos if not c["supera_tope"])

    final = {e: [t for t in ts if t != SALE] for e, ts in LISTA_TRABAJO.items()}
    final[ESTRATO_SUCESOR].append(sucesor)
    filas = []
    for e, ts in final.items():
        for t in ts:
            filas.append({
                "to": t, "estrato": e, "categoria": inv[t]["categoria"],
                "modo_lectura_e0_corregida": modo[t],
                "modo_lectura_particion_legada": conteos_leg.get(t, {}).get("modo_lectura"),
                "unidades_extraccion": unidades[t],
                "unidades_por_to_manifiesto_S0-6b": man["unidades_por_to"][t],
                "chunks_conteos": conteos[t]["chunks"],
                "cobertura_exacta": cob[t], "ids_chunk_repetidos": repetidos[t],
                "fila_registro_alcance": registro.get(t, []),
                "rol_alcance_manifiesto_152": man152[t].get("rol_alcance"),
                "sucesor_de_ri_oc": t == sucesor,
            })
    U = sum(f["unidades_extraccion"] for f in filas)
    U_trabajo = sum(unidades[t] for t in en_lista)
    tope = FACTOR * U * TARIFA
    iguales = all(f["unidades_extraccion"] == f["unidades_por_to_manifiesto_S0-6b"] == f["chunks_conteos"]
                  for f in filas)

    excl = Counter()
    for t in tos152:
        for m in motivos[t]:
            excl[m] += 1

    # cascada disjunta: cada TO cuenta solo en el primer motivo que lo excluye, en el orden de las condiciones
    orden_motivos = ["en la lista de trabajo", "tanda 0", "de los 14 de fuera", "ri_ao, ri_cc o ri2_pm",
                     "enmienda 8, decisiones 1 y 2", "cobertura no exacta", "ids de chunk repetidos"]
    cascada, restantes = [], list(tos152)
    for mo in orden_motivos + ["modo distinto de sin_raiz"]:
        fuera = [t for t in restantes if (mo in motivos[t] if mo != "modo distinto de sin_raiz"
                                          else modo[t] != MODO_SUCESOR)]
        restantes = [t for t in restantes if t not in fuera]
        cascada.append({"motivo": mo, "excluidos": len(fuera), "quedan": len(restantes),
                        **({"lista": fuera} if len(fuera) <= 20 else {})})
    assert sorted(restantes) == sorted(elegibles_sin_raiz)

    def agrupar(clave: str) -> dict:
        g: dict[str, dict] = {}
        for f in filas:
            x = g.setdefault(f[clave], {"tos": 0, "unidades": 0, "lista": []})
            x["tos"] += 1
            x["unidades"] += f["unidades_extraccion"]
            x["lista"].append(f["to"])
        return dict(sorted(g.items()))
    por_categoria, por_modo = agrupar("categoria"), agrupar("modo_lectura_e0_corregida")
    assert sum(x["unidades"] for x in por_categoria.values()) == U == sum(x["unidades"] for x in por_modo.values())
    assert not [f["to"] for f in filas if not f["cobertura_exacta"] or f["ids_chunk_repetidos"]]
    out = {
        "unidad": "U-SEG-OFICIAL, S2, tramo 1: la lista de la tanda 1, el sucesor de ri_oc, U y el tope",
        "comando": "python -B lista_tanda1_S2.py --e0 <salida de E0 de los 152> --raiz <copia del repo> --out <json>",
        "fuentes": {
            "e0": {"conteos.json": sha(e0 / "conteos.json"), "cobertura.json": sha(e0 / "cobertura.json")},
            "repo": {r: sha(raiz / r) for r in (INVENTARIO, PARTICION, CONTEOS_LEGADOS, MANIFIESTO_S06B,
                                                 MANIFIESTO_152, REGISTRO)},
        },
        "lista_de_trabajo": LISTA_TRABAJO,
        "unidades_lista_de_trabajo": U_trabajo,
        "sale": {"to": SALE, "unidades_extraccion": unidades[SALE], "modo_lectura_e0_corregida": modo[SALE],
                 "razon": "enmienda 8, decisión 1 (error de corte confirmado en S1-quater)"},
        "d1": {
            "regla": ("el elegible con modo sin_raiz en la E0 corregida con más unidades de extracción, desempate por "
                      "id, que no supere en más de 600 unidades a ri_oc; si el primero lo supera, el siguiente de la "
                      "lista ordenada que no lo supere"),
            "unidades_ri_oc": unidades[SALE], "tope_unidades": tope_d1,
            "candidatos_ordenados": candidatos, "sucesor": sucesor,
            "exclusiones_sobre_los_152_no_disjuntas": dict(sorted(excl.items())),
            "cascada_disjunta_sobre_los_152": cascada,
            "ri_dcpc_modo_e0_corregida": modo["ri_dcpc"],
            "ri_dcpc_modo_particion_legada": conteos_leg["ri_dcpc"].get("modo_lectura"),
        },
        "d2": "ri_pgn queda en el estrato 2 (decisión de la autora del 07/10/2026, registro_alcance_por_tanda.md:37); "
              "el orden del §7 no se recomputó",
        "lista_final": final,
        "filas": filas,
        "U": U,
        "tope_usd": round(tope, 4),
        "tope_formula": f"{FACTOR} × {U} × {TARIFA}",
        "tope_usd_lista_de_trabajo": round(FACTOR * U_trabajo * TARIFA, 4),
        "por_categoria": por_categoria,
        "por_modo_lectura": por_modo,
        "unidades_extraccion_igual_a_unidades_por_to": iguales,
        "unidades_extraccion_definicion": (
            "las entradas de chunks_<to>.json de la E0 corregida (chunks terminales y mini-chunks): el runner de la "
            "extracción las carga todas (runner_corpus.py:616, comun_e1.py:40-49). Una unidad que E1 parta por corte "
            "en la corrida se reemplaza por sus partes (runner_corpus.py:569-579): esas partes no están en U"),
        "cobertura_no_exacta_en_los_152": sorted(t for t in tos152 if not cob[t]),
        "ids_repetidos_en_los_152": sorted(t for t in tos152 if repetidos[t]),
        "modos_en_los_152": dict(sorted(Counter(modo.values()).items())),
    }
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("lista_final", "U", "tope_usd", "unidades_lista_de_trabajo",
                                          "unidades_extraccion_igual_a_unidades_por_to")}, ensure_ascii=False))
    print("sale", out["sale"])
    print("d1", {k: v for k, v in out["d1"].items() if k != "candidatos_ordenados"})
    for c in candidatos:
        print(" ", c)


if __name__ == "__main__":
    main()
