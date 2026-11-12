"""
r1_invariantes.py — B1.5: invariantes del ensamblado + GUARDA de merge
cross-TO, como módulo que ENVUELVE ensamblar_corpus.merge_grafos (no lo
edita).

Invariantes (verificar_invariantes):
  I1 conservación de nodos:   Σ nodos pre-merge − merges_nodo = nodos finales
  I2 conservación de aristas: Σ aristas pre-merge − merges_arista = aristas finales
  I3 unicidad de ids de nodo y de triplas (source, relation, target)
  I4 cero aristas colgantes
  I5 cero nodos/aristas sin provenance (campo `provenances` no vacío y
     `provenance` presente)

Guarda cross-TO (merge_grafos_guardado): solo los nodos Sujeto del catálogo
cerrado (schema.SUJETOS_CATALOGO_SET: 65 clases/instancias + 5 roles) se
fusionan silenciosamente entre TOs. Cualquier otra colisión de id entre TOs
distintos (hoy: 4 Operacion + 1 Obligacion) NO se fusiona: el nodo del TO
posterior (orden documental pro→cla→ric→cap→ext) conserva id + sufijo
`__<to>` y toda su provenance; sus aristas se re-apuntan al id sufijado; la
colisión va a `adjudicacion_cross_to` (lista para adjudicación humana o para
un E4-LLM futuro). Es aditivo y reversible: fusionar después = quitar el
sufijo y volver a correr el merge sellado.

Uso:  .venv/bin/python3 r1_invariantes.py   → selftest sobre la verdad
      conocida (reproduce el kg sellado 8e2eadee byte a byte con el
      ensamblador actual y corre I1-I5 sobre él; luego corre la guarda y
      verifica I1-I5 + que la única diferencia con el sellado sean las 5
      colisiones no-Sujeto).
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy

import r1_comun as C

import ensamblar_corpus as EC                      # noqa: E402  (se importa, no se edita)
from schema import SUJETOS_CATALOGO_SET            # noqa: E402


class InvarianteError(AssertionError):
    pass


def _check(cond: bool, msg: str, fallos: list[str]) -> None:
    if not cond:
        fallos.append(msg)


def verificar_invariantes(kg: dict, grafos_pre: dict[str, dict] | None = None,
                          merges_nodo: int | None = None,
                          merges_arista: int | None = None,
                          relaciones_sin_provenance_ok: tuple[str, ...] = ()) -> dict:
    """Corre I1-I5. Devuelve dict con conteos y lista `fallos` (vacía = OK).
    Si `grafos_pre` es None, I1/I2 se omiten (no hay pre-merge que conservar)."""
    nodes, edges = kg["nodes"], kg["edges"]
    fallos: list[str] = []
    res: dict = {"nodes": len(nodes), "edges": len(edges)}

    if grafos_pre is not None:
        pre_n = sum(len(g["nodes"]) for g in grafos_pre.values())
        pre_e = sum(len(g["edges"]) for g in grafos_pre.values())
        res.update({"nodes_pre_merge": pre_n, "edges_pre_merge": pre_e,
                    "merges_nodo": merges_nodo, "merges_arista": merges_arista})
        _check(pre_n - (merges_nodo or 0) == len(nodes),
               f"I1 conservación nodos: {pre_n} - {merges_nodo} != {len(nodes)}", fallos)
        _check(pre_e - (merges_arista or 0) == len(edges),
               f"I2 conservación aristas: {pre_e} - {merges_arista} != {len(edges)}", fallos)

    ids = [n["id"] for n in nodes]
    idset = set(ids)
    _check(len(ids) == len(idset), f"I3 ids de nodo duplicados: {len(ids) - len(idset)}", fallos)
    triplas = [(e["source"], e["relation"], e["target"]) for e in edges]
    _check(len(triplas) == len(set(triplas)),
           f"I3 triplas duplicadas: {len(triplas) - len(set(triplas))}", fallos)

    colgantes = [t for t in triplas if t[0] not in idset or t[2] not in idset]
    res["aristas_colgantes"] = len(colgantes)
    _check(not colgantes, f"I4 aristas colgantes: {len(colgantes)} p.ej. {colgantes[:3]}", fallos)

    sin_prov_n = [n["id"] for n in nodes if not n.get("provenances") or "provenance" not in n]
    sin_prov_e = [t for t, e in zip(triplas, edges)
                  if (not e.get("provenances") or "provenance" not in e)
                  and e["relation"] not in relaciones_sin_provenance_ok]
    res["nodos_sin_provenance"] = len(sin_prov_n)
    res["aristas_sin_provenance"] = len(sin_prov_e)
    _check(not sin_prov_n, f"I5 nodos sin provenance: {sin_prov_n[:5]}", fallos)
    _check(not sin_prov_e, f"I5 aristas sin provenance: {sin_prov_e[:5]}", fallos)

    res["fallos"] = fallos
    res["ok"] = not fallos
    return res


# ----------------------------------------------------------------------- #
# Guarda cross-TO                                                         #
# ----------------------------------------------------------------------- #
def _es_sujeto_catalogo(n: dict) -> bool:
    return n.get("type") == "Sujeto" and n["id"] in SUJETOS_CATALOGO_SET


def colisiones_cross_to(grafos: dict[str, dict]) -> dict[str, list[str]]:
    """id → lista de TOs (orden documental) en los que aparece, solo ids en >1 TO."""
    visto: dict[str, list[str]] = {}
    for to in C.TOS_ORDEN:
        for n in grafos[to]["nodes"]:
            visto.setdefault(n["id"], []).append(to)
    return {i: tos for i, tos in visto.items() if len(tos) > 1}


def merge_grafos_guardado(grafos: dict[str, dict], codigo_comunicacion=None) -> dict:
    """Envuelve EC.merge_grafos: renombra (sufijo __<to>) las colisiones
    cross-TO que NO son Sujeto del catálogo en los TOs posteriores al primero,
    re-apunta sus aristas, y recién entonces corre el merge sellado. Devuelve
    el dict de merge_grafos más `adjudicacion_cross_to` y `renombres`."""
    # Regla C1, la unión de las Comunicacion (cadena r2, con --union-comunicaciones de ensamblar_tanda0.py): con
    # `codigo_comunicacion` (una función nodo -> código normalizado o None), las Comunicacion de TOs distintos con el mismo
    # código se unen en el id de la primera, en el orden de los TOs, y lo registra `uniones_c1`; la colisión no va a la
    # adjudicación. Con None (el defecto), la guarda de siempre.
    uniones_c1: list[dict] = []
    if codigo_comunicacion is not None:
        grafos, uniones_c1 = _unir_comunicaciones_c1(grafos, codigo_comunicacion)
    colis = colisiones_cross_to(grafos)
    nodo_por_to_id = {to: {n["id"]: n for n in grafos[to]["nodes"]} for to in C.TOS_ORDEN}
    adjudicacion: list[dict] = []
    renombres: dict[str, dict[str, str]] = {to: {} for to in C.TOS_ORDEN}
    for nid, tos in sorted(colis.items()):
        primero = nodo_por_to_id[tos[0]][nid]
        if _es_sujeto_catalogo(primero):
            continue
        if codigo_comunicacion is not None and primero.get("type") == "Comunicacion" and nid in {u["id"] for u in uniones_c1}:
            continue                    # C1: la unión la hace el merge sellado, con sus conflictos registrados
        entrada = {"id": nid, "type": primero["type"], "tos": tos, "nodos": []}
        for k, to in enumerate(tos):
            n = nodo_por_to_id[to][nid]
            nuevo_id = nid if k == 0 else f"{nid}__{to}"
            if k > 0:
                renombres[to][nid] = nuevo_id
            entrada["nodos"].append({
                "to": to, "id_en_r1": nuevo_id, "label": n.get("label"),
                "properties": n.get("properties"), "provenances": n.get("provenances"),
            })
        entrada["motivo"] = ("colisión de id cross-TO en nodo no-Sujeto-de-catálogo: "
                             "se conservan ambos sin fusionar (guarda B1.5); "
                             "pendiente de adjudicación")
        adjudicacion.append(entrada)

    grafos_ren: dict[str, dict] = {}
    for to in C.TOS_ORDEN:
        g = deepcopy(grafos[to])
        ren = renombres[to]
        if ren:
            for n in g["nodes"]:
                if n["id"] in ren:
                    n["id"] = ren[n["id"]]
                    n.setdefault("properties", {})["colision_cross_to"] = "true"
            for e in g["edges"]:
                if e["source"] in ren:
                    e["source"] = ren[e["source"]]
                if e["target"] in ren:
                    e["target"] = ren[e["target"]]
        grafos_ren[to] = g
    m = EC.merge_grafos(grafos_ren)
    m["adjudicacion_cross_to"] = adjudicacion
    if codigo_comunicacion is not None:
        m["uniones_c1"] = uniones_c1
    m["renombres"] = {to: r for to, r in renombres.items() if r}
    m["grafos_pre_merge"] = grafos_ren
    return m


def _unir_comunicaciones_c1(grafos: dict[str, dict], codigo_comunicacion) -> tuple[dict, list]:
    """C1: en cada código normalizado que aparece en más de un TO, renombra sus Comunicacion al id de la primera (en el orden
    de C.TOS_ORDEN) y re-apunta sus aristas; dentro de ese código, también se unen las variantes de un mismo TO. Un código de
    un solo TO, o una Comunicacion sin código normalizado (None), no se toca."""
    grupos: dict[str, dict] = {}
    for to in C.TOS_ORDEN:
        for n in grafos[to]["nodes"]:
            if n.get("type") == "Comunicacion":
                c = codigo_comunicacion(n)
                if c is not None:
                    g = grupos.setdefault(c, {"id": n["id"], "codigo_normalizado": c, "nodos": []})
                    g["nodos"].append({"to": to, "id_antes": n["id"], "codigo": (n.get("properties") or {}).get("codigo"),
                                       "label": n.get("label")})
    uniones = [g for g in grupos.values() if len({x["to"] for x in g["nodos"]}) > 1]
    canon = {x["id_antes"]: g["id"] for g in uniones for x in g["nodos"] if x["id_antes"] != g["id"]}
    salida: dict[str, dict] = {}
    for to in C.TOS_ORDEN:
        g = deepcopy(grafos[to])
        ids_c1 = {n["id"] for n in g["nodes"] if n.get("type") == "Comunicacion" and n["id"] in canon}
        for n in g["nodes"]:
            if n["id"] in ids_c1:
                n["id"] = canon[n["id"]]
        for e in g["edges"]:
            if e["source"] in ids_c1:
                e["source"] = canon[e["source"]]
            if e["target"] in ids_c1:
                e["target"] = canon[e["target"]]
        salida[to] = g
    return salida, uniones


def merges_arista_de(grafos_pre: dict[str, dict], edges_out: list[dict]) -> int:
    pre = sum(len(g["edges"]) for g in grafos_pre.values())
    return pre - len(edges_out)


# ----------------------------------------------------------------------- #
# Selftest sobre la verdad conocida                                        #
# ----------------------------------------------------------------------- #
def main() -> int:
    grafos = C.cargar_grafos_sellados()
    oks, fails = [], []

    def t(nombre: str, cond: bool, detalle: str = "") -> None:
        (oks if cond else fails).append(f"{nombre} {detalle}".strip())

    # S0 — el ensamblador actual reproduce el kg sellado byte a byte
    m0 = EC.merge_grafos(grafos)
    kg0 = {"nodes": m0["nodes"], "edges": m0["edges"]}
    s0 = C.dumps_kg(kg0)
    sha0 = C.sha256_bytes(s0.encode("utf-8"))
    t("S0 reproduce sellado byte a byte", sha0 == C.SHA_KG_SELLADO
      and s0 == (C.SALIDA / "kg.json").read_text(encoding="utf-8"), sha0)

    # I1-I5 sobre la verdad conocida
    inv0 = verificar_invariantes(kg0, grafos, merges_nodo=len(m0["merges_cross_to"]),
                                 merges_arista=merges_arista_de(grafos, kg0["edges"]))
    t("I1-I5 sobre kg sellado", inv0["ok"], json.dumps(inv0, ensure_ascii=False))
    t("merges cross-TO sellados = 27", len(m0["merges_cross_to"]) == 27)

    # Guarda cross-TO
    m1 = merge_grafos_guardado(grafos)
    kg1 = {"nodes": m1["nodes"], "edges": m1["edges"]}
    inv1 = verificar_invariantes(kg1, m1["grafos_pre_merge"],
                                 merges_nodo=len(m1["merges_cross_to"]),
                                 merges_arista=merges_arista_de(m1["grafos_pre_merge"], kg1["edges"]))
    t("I1-I5 con guarda", inv1["ok"], json.dumps(inv1, ensure_ascii=False))
    adj = m1["adjudicacion_cross_to"]
    tipos = C.conteo([{"type": a["type"]} for a in adj], "type")
    t("guarda: colisiones no-Sujeto registradas = 5 (4 Operacion + 1 Obligacion)",
      tipos == {"Operacion": 4, "Obligacion": 1}, str(tipos))
    t("guarda: todo merge restante es Sujeto del catálogo",
      all(x["type"] == "Sujeto" and x["id"] in SUJETOS_CATALOGO_SET for x in m1["merges_cross_to"]),
      str(len(m1["merges_cross_to"])))
    t("guarda: nodos = sellado + 5", len(kg1["nodes"]) == len(kg0["nodes"]) + 5,
      f"{len(kg1['nodes'])} vs {len(kg0['nodes'])}")
    t("guarda: aristas conservadas", len(kg1["edges"]) == len(kg0["edges"]),
      f"{len(kg1['edges'])} vs {len(kg0['edges'])}")
    t("guarda: sin conflictos de properties cross-TO no-Sujeto",
      all(c["id"] not in {a["id"] for a in adj} for c in m1["conflictos"]),
      str(len(m1["conflictos"])))
    # El conflicto Obligacion del sellado (ric 5.1.3.3 + cap 12.3) figura en adjudicación
    t("guarda: Obligacion_se_considerara_la_ultima_calificacion…_2f96fc en adjudicación",
      any(a["id"].startswith("Obligacion_se_considerara_la_ultima_calificacion") for a in adj))

    for o in oks:
        print("  OK ", o)
    for f in fails:
        print("  FAIL ", f)
    print(f"\n{len(oks)}/{len(oks) + len(fails)} checks OK")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
