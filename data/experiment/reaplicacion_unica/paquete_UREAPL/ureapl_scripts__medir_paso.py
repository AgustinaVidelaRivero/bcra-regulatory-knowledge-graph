"""U-REAPL: la medición de un paso contra el anterior, en un grafo (mandato U-REAPL, §3 y §4; U-REMISIONES-SUBPUNTOS, §4). USD 0.

Lee los dos ensamblados (`<dir>/r2/`) y escribe, en --salida:
  - `medicion.json`: solo cuentas y códigos (sha256(id)[:12]): nodos por tipo y aristas por predicado; la tabla de ids del paso
    (cuántos pares, sin par, por tipo); las triplas de cada predicado con la tabla aplicada (cuántas entran y salen, y cuántas sin un
    extremo en un nodo de la pieza); los nodos que cambian por tipo y por qué campo; el aislamiento (cada pieza toca solo lo suyo); lo
    propio de la pieza; y el cegamiento (cuántas filas no se listan por la muestra).
  - `remite_a_que_cambian.json`: cada `remite_a` que entra o sale, por código, con su causa.
  - `tabla_ids_<pieza>_por_codigo.json`: la tabla del paso, código viejo → código nuevo (si la pieza cambia ids).
  - lo propio de la pieza, por código y unidad (sin label, descripción ni tramo).
  - `NO_ABRIR_tabla_ids_<pieza>.json` (los ids tal cual; no se vuelve a abrir) y `NO_ABRIR_casos_en_espera.json` si una fila es de
    una unidad de la muestra (su contenido no se lista).
  - en --trabajo, `<etiqueta>.json`: la tabla con los ids y las `remite_a` que cambian, para componer la tabla del grafo evaluado y el
    control de la precisión 2 de la firma (fuera del paquete).
Las piezas y lo suyo:
  - D (`--procedencia-heredada`): C1 cambia el id (el punto va en el id) solo de entidades de TIPOS_G_R; C2 marca la procedencia de
    todo tipo (mandato de U-PROC-HERENCIA, §9, decisión 1); los nodos, `establecida_en` y `aplica_a` quedan iguales con la tabla, y cada
    `remite_a` que cambia tiene un extremo en un nodo de C1 (registro, §49). La tabla: par único por tipo, label y chunk_id.
  - las claves (`--catalogo-resolucion`): solo Sujetos. La tabla: el Sujeto propuesto que sale → el Sujeto del catálogo al que van todas
    sus relaciones (de `resolucion_sujetos.jsonl` y del registro).
  - C1 (`--union-comunicaciones`): solo Comunicacion. La tabla: la Comunicacion → el nodo de su código (`uniones_c1.json`).
  - las remisiones (`--remisiones-a-subpuntos`): solo `remite_a` que se agregan, cada una de una cita de la opción B.
La consola lleva solo cuentas y sha256.

Uso, desde la raíz de la copia: <python del repo> -B medir_paso.py --anterior A --nuevo B --pieza D|claves|C1|remisiones
       --grafo con_cola|sin_cola --salida S --trabajo T --etiqueta E [--veredictos V] [--remite-a-de-d T/<etiqueta del paso 2>.json
       --tablas-hasta-el-paso T/<paso 3>.json,T/<paso 4>.json]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import muestra_memoria as MM  # noqa: E402

TIPOS_G_R = ("Operacion", "Restriccion", "Excepcion", "Obligacion", "Potestad", "Condicion", "Definicion")
TIPOS_PIEZA = {"D": set(TIPOS_G_R), "claves": {"Sujeto"}, "C1": {"Comunicacion"}, "remisiones": set()}
MANIFIESTOS = {"tanda0": "data/experiment/reextraccion_v2/manifiestos/tanda0_10tos_r2b.json",
               "tanda1": "data/experiment/reextraccion_v2/manifiestos/tanda1_20tos_r2b.json",
               "tanda_final": "data/experiment/reextraccion_v2/manifiestos/tanda_final_98tos_r2b.json"}
CAMPOS_C2 = {"tramo_fuera_del_texto_de_e3"}
CAMPOS_C1 = {"punto", "rol_documental", "punto_declarado_e1", "rol_declarado_e1", "ancestros", "paginas"}


def cod(i: str) -> str:
    return hashlib.sha256(i.encode("utf-8")).hexdigest()[:12]


CEGADOS: set = set()      # los nodos con alguna procedencia en una unidad de la muestra (de los dos grafos), en memoria


def codv(i: str) -> str:
    """El código de un nodo para una lista: «cegado» si tiene alguna procedencia en una unidad de la muestra."""
    return "cegado" if i in CEGADOS else cod(i)


def jsonl(p: Path) -> list:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def escribir(p: Path, obj) -> str:
    t = json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    p.write_text(t, encoding="utf-8")
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def tanda_de_to() -> dict:
    out = {}
    for t, p in MANIFIESTOS.items():
        for to in json.loads(Path(p).read_text(encoding="utf-8"))["orden_corrida"]:
            out[to] = t
    return out


def clave_par(n: dict) -> tuple:
    return (n["type"], n.get("label"), tuple(sorted({(p or {}).get("chunk_id") or "" for p in n.get("provenances") or []})))


def sin_id(n: dict) -> str:
    return json.dumps({k: v for k, v in n.items() if k != "id"}, ensure_ascii=False, sort_keys=True)


def campos_que_cambian(a: dict, b: dict) -> set:
    """Los campos que difieren entre dos nodos; en las procedencias, las claves que difieren (con «procedencia.» adelante)."""
    out = set()
    for k in set(a) | set(b):
        if k in ("id", "provenance", "provenances"):
            continue
        if a.get(k) != b.get(k):
            out.add(k)
    pa = [a.get("provenance") or {}] + list(a.get("provenances") or [])
    pb = [b.get("provenance") or {}] + list(b.get("provenances") or [])
    if len(pa) != len(pb):
        out.add("procedencia.cantidad")
    for x, y in zip(pa, pb):
        for k in set(x) | set(y):
            if x.get(k) != y.get(k):
                out.add("procedencia." + k)
    return out


def grados(kg: dict) -> collections.Counter:
    g = collections.Counter()
    for e in kg["edges"]:
        g[e["source"]] += 1
        g[e["target"]] += 1
    return g


def hubs(kg: dict) -> tuple[int, set]:
    """La regla de la familia 5 (familias_nav.py del 142, no versionado en el repo): grado (entrantes más salientes) en el 1 % más
    alto del grafo servido. Umbral: el grado del nodo en el puesto ⌈1 % de los nodos⌉ (de mayor a menor); hub: grado ≥ umbral.
    Calibrada contra el registro, §62: el acumulado de las tandas 0 y 1 da 38 y 216 sin cola, y 42 y 226 con cola."""
    g = grados(kg)
    gs = sorted((g.get(n["id"], 0) for n in kg["nodes"]), reverse=True)
    umbral = gs[math.ceil(0.01 * len(gs)) - 1]
    return umbral, {n["id"] for n in kg["nodes"] if g.get(n["id"], 0) >= umbral}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anterior", type=Path, required=True)
    ap.add_argument("--nuevo", type=Path, required=True)
    ap.add_argument("--pieza", choices=("D", "claves", "C1", "remisiones"), required=True)
    ap.add_argument("--grafo", choices=("con_cola", "sin_cola"), required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--veredictos", type=Path, default=None)
    ap.add_argument("--remite-a-de-d", dest="remite_a_de_d", type=Path, default=None)
    ap.add_argument("--tablas-hasta-el-paso", dest="tablas", default=None)
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)
    a.trabajo.mkdir(parents=True, exist_ok=True)
    rA, rB = a.anterior / "r2", a.nuevo / "r2"
    A = json.loads((rA / "kg.json").read_text(encoding="utf-8"))
    B = json.loads((rB / "kg.json").read_text(encoding="utf-8"))
    repB = json.loads((rB / "reporte_ensamblado_r2.json").read_text(encoding="utf-8"))
    NA, NB = {n["id"]: n for n in A["nodes"]}, {n["id"]: n for n in B["nodes"]}
    m = MM.muestra()
    ciegos_A, ciegos_B = MM.nodos_cegados(A, m), MM.nodos_cegados(B, m)
    CEGADOS.update(ciegos_A | ciegos_B)
    t_de = tanda_de_to()
    med: dict = {"pieza": a.pieza, "grafo": a.grafo,
                 "kg_anterior_sha256": hashlib.sha256((rA / "kg.json").read_bytes()).hexdigest(),
                 "kg_nuevo_sha256": hashlib.sha256((rB / "kg.json").read_bytes()).hexdigest()}
    ocultas = collections.Counter()
    en_espera: list = []

    # 1. nodos por tipo y aristas por predicado
    ta, tb = collections.Counter(n["type"] for n in A["nodes"]), collections.Counter(n["type"] for n in B["nodes"])
    pa, pb = collections.Counter(e["relation"] for e in A["edges"]), collections.Counter(e["relation"] for e in B["edges"])
    med["nodos"] = {"anterior": len(A["nodes"]), "nuevo": len(B["nodes"]),
                    "por_tipo": {t: [ta[t], tb[t], tb[t] - ta[t]] for t in sorted(set(ta) | set(tb))}}
    med["aristas"] = {"anterior": len(A["edges"]), "nuevo": len(B["edges"]),
                      "por_predicado": {p: [pa[p], pb[p], pb[p] - pa[p]] for p in sorted(set(pa) | set(pb))}}

    # 2. la tabla de ids del paso
    salen, entran = set(NA) - set(NB), set(NB) - set(NA)
    tabla: dict[str, str] = {}
    tocados: set = set()          # nodos de la pieza, en los dos espacios de ids
    c1_nodos = {n["id"] for n in B["nodes"] if any("punto_declarado_e1" in (p or {}) for p in n.get("provenances") or [])}
    c1_nodos_A = {n["id"] for n in A["nodes"] if any("punto_declarado_e1" in (p or {}) for p in n.get("provenances") or [])}
    if a.pieza == "D":
        c1_nodos = c1_nodos - c1_nodos_A
    detalle_tabla: dict = {}
    if a.pieza == "D":
        ks = collections.Counter(clave_par(NA[i]) for i in salen)
        ke = collections.Counter(clave_par(NB[i]) for i in entran)
        por_s = {clave_par(NA[i]): i for i in salen if ks[clave_par(NA[i])] == 1}
        por_e = {clave_par(NB[i]): i for i in entran if ke[clave_par(NB[i])] == 1}
        tabla = {por_s[k]: por_e[k] for k in por_s if k in por_e}
        tocados = set(tabla) | set(tabla.values()) | c1_nodos | {i for i, j in tabla.items()}
        detalle_tabla = {"pares": len(tabla), "pares_por_tipo": dict(collections.Counter(NB[j]["type"] for j in tabla.values())),
                         "nodos_con_procedencia_de_c1": len(c1_nodos),
                         "nodos_con_procedencia_de_c1_por_tipo": dict(collections.Counter(NB[i]["type"] for i in c1_nodos)),
                         "renombrados_sin_procedencia_de_c1": sum(1 for j in tabla.values() if j not in c1_nodos)}
    elif a.pieza == "claves":
        def destinos(r: Path) -> dict:
            res = {(x["to"], x["chunk_id"], x["indice_relacion"]): x for x in jsonl(r / "resolucion_sujetos.jsonl")}
            reg = {(x["to"], x["chunk_id"], x["indice_relacion"]): x for x in jsonl(r / "no_mapeados_sujetos.jsonl")}
            return {k: (x["resuelto_a"] or (reg.get(k) or {}).get("id_nodo"), x["metodo_resolucion"], x.get("mencion"))
                    for k, x in res.items()}
        dA, dB = destinos(rA), destinos(rB)
        if set(dA) != set(dB):
            raise SystemExit("FRENO: las relaciones de sujeto no son las mismas en los dos pasos")
        cambian = {k: (dA[k], dB[k]) for k in dA if dA[k][:2] != dB[k][:2]}
        va_a = collections.defaultdict(set)
        for k, (x, y) in cambian.items():
            if x[0]:
                va_a[x[0]].add(y[0])
        tabla = {i: next(iter(v)) for i, v in va_a.items() if i in salen and len(v) == 1 and next(iter(v))}
        tocados = {i for k, (x, y) in cambian.items() for i in (x[0], y[0]) if i} | {i for i in salen | entran if
                                                                                      (NA.get(i) or NB.get(i))["type"] == "Sujeto"}
        sys.path.insert(0, "data/experiment/tanda0/code")
        import ensamblar_tanda0 as ENS  # noqa: PLC0415
        E4 = ENS.E4

        def clave(mn: str) -> str:
            return E4._norm_sing(E4._sin_parentesis(E4.RE_ARTICULO_INICIAL.sub("", mn or "")))
        indice = {}
        if a.veredictos:
            indice = {v["clave"]: (k, v["codigo"]) for k, v in enumerate(json.loads(a.veredictos.read_text(encoding="utf-8"))
                                                                         ["veredictos"], 1)}
        por_clave = collections.defaultdict(lambda: {"relaciones": 0, "de": collections.Counter(), "a": collections.Counter(),
                                                     "metodo": collections.Counter()})
        for k, (x, y) in cambian.items():
            c = clave(x[2])
            ent = por_clave[c]
            ent["relaciones"] += 1
            ent["de"][codv(x[0]) if x[0] else "ninguno"] += 1
            ent["a"][codv(y[0]) if y[0] else "ninguno"] += 1
            ent["metodo"][f"{x[1]}→{y[1]}"] += 1
            ent["de_destino"] = ent.get("de_destino", 0) + (x[0] != y[0])
        filas = []
        for c, ent in por_clave.items():
            k, codigo = indice.get(c, (None, None))
            filas.append({"veredicto": k, "codigo_del_veredicto": codigo, "codigo_de_la_clave": cod(c),
                          "relaciones_que_cambian": ent["relaciones"], "de_destino": ent.get("de_destino", 0),
                          "de": dict(ent["de"]), "a": dict(ent["a"]),
                          "metodo": dict(ent["metodo"])})
        filas.sort(key=lambda f: (f["veredicto"] is None, f["veredicto"] or 0, f["codigo_de_la_clave"]))
        med["claves"] = {"relaciones_que_cambian": len(cambian),
                         "relaciones_que_cambian_de_destino": sum(1 for x, y in cambian.values() if x[0] != y[0]),
                         "relaciones_que_cambian_solo_de_metodo": sum(1 for x, y in cambian.values() if x[0] == y[0]),
                         "relaciones_de_claves_no_entra": sum(1 for x, y in cambian.values()
                                                              if (indice.get(clave(x[2])) or (0, ""))[1] == "no entra"),
                         "claves_con_cambios": len(filas),
                         "claves_de_un_veredicto": sum(1 for f in filas if f["veredicto"]),
                         "claves_fuera_de_los_veredictos": sum(1 for f in filas if not f["veredicto"]),
                         "por_metodo": dict(collections.Counter(f"{x[1]}→{y[1]}" for x, y in cambian.values())),
                         "propuestos_que_salen": sum(1 for i in salen if NA[i]["type"] == "Sujeto"),
                         "sujetos_que_entran": sum(1 for i in entran if NB[i]["type"] == "Sujeto"),
                         "propuestos_que_salen_con_un_solo_destino": len(tabla)}
        med["claves"]["sha256_por_clave"] = escribir(a.salida / "claves_sujetos_re_resueltos_por_clave.json", filas)
        detalle_tabla = {"pares": len(tabla)}
    elif a.pieza == "C1":
        un = json.loads((rB / "uniones_c1.json").read_text(encoding="utf-8"))
        for u in un:
            destino = u.get("id")
            for x in u["nodos"]:
                if x.get("id_con_la_guarda") != destino:
                    tabla[x["id_con_la_guarda"]] = destino
        tocados = {x["id_con_la_guarda"] for u in un for x in u["nodos"]} | {u.get("id") for u in un} | {
            i for i in salen | entran}
        filas = [{"codigo_normalizado_sha12": cod(str(u.get("codigo_normalizado") or u.get("codigo"))), "nodos": len(u["nodos"]),
                  "documentos": len({x.get("to") for x in u["nodos"]}), "nodo_unido": codv(u.get("id")),
                  "nodos_que_se_unen": sorted(codv(x["id_con_la_guarda"]) for x in u["nodos"])} for u in un]
        med["c1"] = {"uniones": len(un), "nodos_en_uniones": sum(len(u["nodos"]) for u in un),
                     "uniones_cuyo_id_no_esta_en_el_grafo_nuevo": sum(1 for u in un if u.get("id") not in NB),
                     "nodos_que_se_unen_que_no_estaban_en_el_anterior": sum(1 for u in un for x in u["nodos"]
                                                                           if x["id_con_la_guarda"] not in NA),
                     "resumen_del_ensamblado": repB.get("union_comunicaciones"),
                     "sha256_por_codigo": escribir(a.salida / "c1_uniones_por_codigo.json", filas)}
        detalle_tabla = {"pares": len(tabla)}
    med["tabla"] = detalle_tabla
    if tabla:
        med["tabla"]["sha256_por_codigo"] = escribir(a.salida / f"tabla_ids_{a.pieza}_por_codigo.json",
                                                     sorted([codv(i), codv(j)] for i, j in tabla.items()))
        med["tabla"]["filas_con_un_nodo_cegado"] = sum(1 for i, j in tabla.items() if i in CEGADOS or j in CEGADOS)
        escribir(a.salida / f"NO_ABRIR_tabla_ids_{a.pieza}.json", {"pieza": a.pieza, "grafo": a.grafo, "tabla": tabla})
        # cegamiento: un nodo de una unidad de la muestra que la pieza renombra sigue cegado con su id nuevo
        med["tabla"]["renombrados_cegados_que_siguen_cegados"] = all(j in ciegos_B for i, j in tabla.items() if i in ciegos_A)
        med["tabla"]["renombrados_cegados"] = "sí" if any(i in ciegos_A for i in tabla) else "no"
    sin_par_s = {i for i in salen if i not in tabla}
    sin_par_e = {j for j in entran if j not in set(tabla.values())}
    med["tabla"]["salen_sin_par_por_tipo"] = dict(collections.Counter(NA[i]["type"] for i in sin_par_s))
    med["tabla"]["entran_sin_par_por_tipo"] = dict(collections.Counter(NB[i]["type"] for i in sin_par_e))

    # 3. los nodos que cambian (con la tabla), por tipo y campo
    cambio_nodo = collections.Counter()
    nodos_cambian: set = set()
    for i, n in NA.items():
        # con D, el par renombrado; con las claves y C1, la tabla junta nodos distintos en uno: se compara solo el mismo id
        j = tabla.get(i, i) if a.pieza == "D" else i
        if j not in NB:
            continue
        if sin_id(n) != sin_id(NB[j]):
            nodos_cambian.add(j)
            for c in campos_que_cambian(n, NB[j]):
                cambio_nodo[(n["type"], c)] += 1
    med["nodos_que_cambian"] = {"total": len(nodos_cambian),
                                "por_tipo": dict(collections.Counter(NB[j]["type"] for j in nodos_cambian)),
                                "por_tipo_y_campo": {f"{t}|{c}": v for (t, c), v in sorted(cambio_nodo.items())}}
    solo_c2: set = set()
    if a.pieza == "D":
        # C1 cambia el punto y el rol solo en TIPOS_G_R; C2 marca la procedencia de todo tipo (U-PROC-HERENCIA, §9, decisión 1)
        inv = {v: k for k, v in tabla.items()}
        marca = {"procedencia." + x for x in CAMPOS_C2}
        for j in nodos_cambian:
            if j in c1_nodos:
                continue
            if campos_que_cambian(NA[inv.get(j, j)], NB[j]) <= marca:
                solo_c2.add(j)
        otro = [j for j in nodos_cambian if j not in c1_nodos and j not in solo_c2]
        med["nodos_que_cambian"]["de_C1_por_tipo"] = dict(collections.Counter(NB[j]["type"] for j in nodos_cambian if j in c1_nodos))
        med["nodos_que_cambian"]["solo_con_la_marca_C2_por_tipo"] = dict(collections.Counter(NB[j]["type"] for j in solo_c2))
        med["nodos_que_cambian"]["con_otro_cambio"] = len(otro)
        med["nodos_que_cambian"]["de_C1_fuera_de_TIPOS_G_R"] = sum(1 for j in c1_nodos if NB[j]["type"] not in TIPOS_G_R)
    else:
        tocados |= nodos_cambian

    # 4. las triplas por predicado, con la tabla
    def triplas(kg: dict, mapa: dict) -> dict:
        out = collections.defaultdict(set)
        for e in kg["edges"]:
            out[e["relation"]].add((mapa.get(e["source"], e["source"]), mapa.get(e["target"], e["target"])))
        return out
    TA, TB = triplas(A, tabla), triplas(B, {})
    tipo = {**{tabla.get(i, i): n["type"] for i, n in NA.items()}, **{i: n["type"] for i, n in NB.items()}}
    por_pred, sin_extremo = {}, collections.Counter()
    remite = []
    tocados_mapeados = tocados | {tabla.get(i, i) for i in tocados}
    for p in sorted(set(TA) | set(TB)):
        ent, sal = TB[p] - TA[p], TA[p] - TB[p]
        se = [t for t in ent | sal if t[0] not in tocados_mapeados and t[1] not in tocados_mapeados]
        por_pred[p] = {"entran": len(ent), "salen": len(sal), "sin_extremo_en_un_nodo_de_la_pieza": len(se)}
        sin_extremo[p] = len(se)
        if p == "remite_a":
            for signo, conj in (("+", ent), ("-", sal)):
                for s, t in sorted(conj):
                    causa = ("origen" if s in tocados_mapeados else "") + ("+" if s in tocados_mapeados and t in tocados_mapeados
                                                                          else "") + ("destino" if t in tocados_mapeados else "")
                    if a.pieza == "remisiones":
                        causa = "opción B"
                    remite.append((signo, s, t, causa or "sin extremo de la pieza"))
    med["triplas_por_predicado"] = por_pred
    med["aristas_con_un_extremo_que_la_tabla_cambia_por_predicado"] = dict(collections.Counter(
        e["relation"] for e in A["edges"] if e["source"] in tabla or e["target"] in tabla))
    # las aristas de tripla igual con otros atributos
    def por_tripla(kg: dict, mapa: dict) -> dict:
        out, dup = {}, set()
        for e in kg["edges"]:
            k = (mapa.get(e["source"], e["source"]), e["relation"], mapa.get(e["target"], e["target"]))
            if k in out:
                dup.add(k)
            out[k] = json.dumps({x: y for x, y in e.items() if x not in ("source", "target")}, ensure_ascii=False, sort_keys=True)
        return out, dup
    EA, dupA = por_tripla(A, tabla)
    EB, dupB = por_tripla(B, {})
    attr = collections.Counter()
    attr_c2 = collections.Counter()
    attr_sin = collections.Counter()
    marca_arista = {"provenance.tramo_fuera_del_texto_de_e3", "provenances.tramo_fuera_del_texto_de_e3"}

    def campos_arista(x: dict, y: dict) -> set:
        out = set()
        for f in set(x) | set(y):
            if f in ("provenance", "properties"):
                for kk in set(x.get(f) or {}) | set(y.get(f) or {}):
                    if (x.get(f) or {}).get(kk) != (y.get(f) or {}).get(kk):
                        out.add(f"{f}.{kk}")
            elif f == "provenances":
                if len(x.get(f) or []) != len(y.get(f) or []):
                    out.add("provenances.cantidad")
                for u, v in zip(x.get(f) or [], y.get(f) or []):
                    for kk in set(u) | set(v):
                        if u.get(kk) != v.get(kk):
                            out.add("provenances." + kk)
            elif x.get(f) != y.get(f):
                out.add(f)
        return out
    for k in set(EA) & set(EB):
        if k in dupA or k in dupB:
            continue
        if EA[k] != EB[k]:
            attr[k[1]] += 1
            if k[0] in tocados_mapeados or k[2] in tocados_mapeados:
                continue
            if (k[0] in solo_c2 or k[2] in solo_c2) and campos_arista(json.loads(EA[k]), json.loads(EB[k])) <= marca_arista:
                attr_c2[k[1]] += 1
                continue
            attr_sin[k[1]] += 1
    med["aristas_de_tripla_igual_con_otros_atributos"] = {"por_predicado": dict(attr),
                                                         "solo_la_marca_C2_en_un_extremo_marcado": dict(attr_c2),
                                                         "sin_explicar": dict(attr_sin),
                                                         "triplas_que_juntan_dos_aristas": [len(dupA), len(dupB)]}

    # 5. el aislamiento
    tipos_tocados = collections.Counter(tipo.get(i) for i in tocados_mapeados if tipo.get(i))
    propios = TIPOS_PIEZA[a.pieza]
    ajenos = {t: v for t, v in tipos_tocados.items() if t not in propios}
    if a.pieza == "D":
        ajenos = {t: v for t, v in ajenos.items() if False}   # fuera de TIPOS_G_R, solo la marca C2 (contada arriba)
        renombrados_fuera = sum(1 for j in tabla.values() if NB[j]["type"] not in TIPOS_G_R)
        predicados_ajenos = {p: v for p, v in por_pred.items() if p != "remite_a" and (v["entran"] or v["salen"])}
        aisl = {"renombrados_fuera_de_TIPOS_G_R": renombrados_fuera,
                "nodos_de_C1_fuera_de_TIPOS_G_R": med["nodos_que_cambian"]["de_C1_fuera_de_TIPOS_G_R"],
                "nodos_con_otro_cambio_que_C1_o_la_marca_C2": med["nodos_que_cambian"]["con_otro_cambio"],
                "predicados_que_cambian_fuera_de_remite_a": predicados_ajenos,
                "remite_a_sin_extremo_en_un_nodo_de_C1": sin_extremo["remite_a"],
                "aristas_con_otros_atributos_sin_explicar": dict(attr_sin),
                "nodos_que_salen_o_entran_sin_par": [len(sin_par_s), len(sin_par_e)]}
        aisl["ok"] = (not renombrados_fuera and not aisl["nodos_de_C1_fuera_de_TIPOS_G_R"]
                      and not aisl["nodos_con_otro_cambio_que_C1_o_la_marca_C2"] and not predicados_ajenos
                      and not sin_extremo["remite_a"] and not attr_sin and not sin_par_s and not sin_par_e)
    elif a.pieza == "remisiones":
        otros = {p: v for p, v in por_pred.items() if p != "remite_a" and (v["entran"] or v["salen"])}
        aisl = {"nodos_que_cambian": len(nodos_cambian), "nodos_que_salen_o_entran": [len(salen), len(entran)],
                "predicados_que_cambian_fuera_de_remite_a": otros, "remite_a_que_salen": por_pred.get("remite_a", {}).get("salen"),
                "aristas_existentes_con_otros_atributos": sum(attr.values())}
        aisl["ok"] = not nodos_cambian and not salen and not entran and not otros and not aisl["remite_a_que_salen"] \
            and not aisl["aristas_existentes_con_otros_atributos"]
    else:
        sp_ajenos = dict(collections.Counter(t for t in [NA[i]["type"] for i in sin_par_s] + [NB[i]["type"] for i in sin_par_e]
                                             if t not in propios))
        aisl = {"tipos_de_los_nodos_tocados": dict(tipos_tocados), "tipos_ajenos": ajenos,
                "nodos_que_salen_o_entran_sin_par_de_otros_tipos": sp_ajenos,
                "triplas_sin_extremo_en_un_nodo_de_la_pieza": {p: v for p, v in sin_extremo.items() if v},
                "aristas_de_tripla_igual_con_otros_atributos_sin_extremo": dict(attr_sin)}
        aisl["ok"] = not ajenos and not sp_ajenos and not any(sin_extremo.values()) and not attr_sin
    med["aislamiento"] = aisl

    # 6. las remite_a que cambian, por código (las de un nodo cegado no se listan)
    lista = []
    for signo, s, t, causa in remite:
        if s in ciegos_A | ciegos_B or t in ciegos_A | ciegos_B:
            ocultas["remite_a_con_un_extremo_cegado"] += 1
            continue
        lista.append({"cambio": signo, "origen": cod(s), "destino": cod(t), "causa": causa})
    med["remite_a_que_cambian"] = {"entran": sum(1 for x in remite if x[0] == "+"), "salen": sum(1 for x in remite if x[0] == "-"),
                                   "por_causa": dict(collections.Counter(f"{x[0]}{x[3]}" for x in remite)),
                                   "sha256_de_la_lista": escribir(a.salida / "remite_a_que_cambian.json", lista)}

    # 7. lo propio de la pieza
    if a.pieza == "D":
        h = json.loads((rB / "procedencia_heredada.json").read_text(encoding="utf-8"))
        med["d"] = {k: v for k, v in repB["procedencia_heredada"].items()}
        med["d"]["por_tanda"] = {k: dict(collections.Counter(t_de.get(x["to"], "?") for x in h[k])) for k in h}
        # cada procedencia que tocó C1: unidad, código del nodo, punto y rol de antes y de después
        filas = []
        for x in h["c1"]:
            cands = [n["id"] for n in B["nodes"] if n["type"] == x["type"] and n.get("label") == x["label"]
                     and any((p or {}).get("chunk_id") == x["chunk_id"] and (p or {}).get("punto_declarado_e1") == x["punto"]
                             for p in n.get("provenances") or [])]
            fila = {"tanda": t_de.get(x["to"]), "unidad": x["chunk_id"], "tipo": x["type"],
                    "nodo": codv(cands[0]) if len(cands) == 1 else None, "nodos_candidatos": len(cands),
                    "punto_antes": x["punto"], "rol_antes": x["rol"], "punto_despues": x["punto_c1"], "rol_despues": x["rol_c1"]}
            if MM.en_muestra(x["chunk_id"], m):
                en_espera.append({"caso": "c1", **fila, "nodo_id": cands})
                continue
            filas.append(fila)
        ev = []
        for x in h["uniones_evitadas"]:
            fila = {"tanda": t_de.get(x["to"]), "unidad": x["chunk_id"], "tipo": x["type"], "causa": x["con"],
                    "nodo": codv(x["id"]), "nodo_con_el_que_se_uniria": codv(x["id_c1"]), "punto_antes": x["punto"],
                    "punto_c1": x["punto_c1"]}
            if MM.en_muestra(x["chunk_id"], m):
                en_espera.append({"caso": "union_evitada", **fila})
                continue
            ev.append(fila)
        med["d"]["c1_procedencias_listadas"] = len(filas)
        med["d"]["c1_con_un_solo_nodo"] = sum(1 for f in filas if f["nodos_candidatos"] == 1)
        med["d"]["sha256_c1"] = escribir(a.salida / "d_c1_procedencias.json", filas)
        med["d"]["sha256_uniones_evitadas"] = escribir(a.salida / "d_uniones_evitadas.json", ev)
    if a.pieza == "remisiones":
        regA = json.loads((rA / "remisiones_registro.json").read_text(encoding="utf-8"))
        regB = json.loads((rB / "remisiones_registro.json").read_text(encoding="utf-8"))

        def kc(c: dict) -> tuple:
            return (c.get("chunk_id"), json.dumps(c.get("procedencia"), sort_keys=True), c["evidencia"])

        def kc_codigo(c: dict) -> tuple:
            # la clave con que cuenta las citas el detector (r1_referencias.py:1397)
            return (c.get("chunk_id") or json.dumps(c.get("procedencia"), ensure_ascii=False, sort_keys=True), c["evidencia"])
        psn = {(kc(c), x["destino"]) for c in regA for x in c["irresolubles"] if x["causa"] == "punto_sin_nodos"}
        pares, citas, celdas_c, celdas_a, no_eran = set(), set(), collections.Counter(), collections.Counter(), 0
        citas_codigo: dict = {}
        for c in regB:
            for d in c["destinos"]:
                if d.get("remision_a_subpuntos") != "B":
                    continue
                k = (kc(c), d["destino"])
                citas.add(k)
                no_eran += k not in psn
                to_o = (c.get("procedencia") or {}).get("to")
                celda = f"{t_de.get(to_o, '?')}→{t_de.get(d['destino'].split('::')[0], '?')}"
                citas_codigo.setdefault((kc_codigo(c), d["destino"]), celda)
                for o in c["origenes"]:
                    for i in d["nodos"]:
                        if i != o:
                            pares.add((o, i, celda))
        for celda in citas_codigo.values():
            celdas_c[celda] += 1
        nuevas = TB["remite_a"] - TA["remite_a"]
        par_celda = collections.defaultdict(set)
        for o, i, celda in pares:
            par_celda[(o, i)].add(celda)
        for t in nuevas:
            for celda in sorted(par_celda.get(t, {"sin cita B"}))[:1]:
                celdas_a[celda] += 1
        med["remisiones"] = {"resumen_del_ensamblado": (repB.get("remite_a") or {}).get("remisiones_a_subpuntos"),
                             "citas_con_destino_B_clave_del_detector": len(citas_codigo),
                             "citas_con_destino_B_por_procedencia": len(citas), "citas_B_que_no_eran_punto_sin_nodos": no_eran,
                             "remite_a_nuevas": len(nuevas), "remite_a_nuevas_sin_cita_B": sum(1 for t in nuevas if t not in par_celda),
                             "citas_por_tanda_origen_destino": dict(celdas_c), "remite_a_nuevas_por_tanda_origen_destino": dict(celdas_a)}
        # las que D ya cambió (paso 2), aparte; una arista que cambien las dos piezas frena
        if a.remite_a_de_d and a.tablas:
            d2 = json.loads(a.remite_a_de_d.read_text(encoding="utf-8"))
            mapa: dict = {}
            for t in a.tablas.split(","):
                tb = json.loads(Path(t).read_text(encoding="utf-8"))["tabla"]
                mapa = {k: tb.get(v, v) for k, v in mapa.items()}
                for k, v in tb.items():
                    mapa.setdefault(k, v)
            d_tr = {(mapa.get(s, s), mapa.get(t, t)) for _, s, t, _ in d2["remite_a"]}
            d_nodos = {mapa.get(i, i) for i in d2["nodos_de_c1"]}
            med["remisiones"]["nuevas_que_D_ya_cambio_en_el_paso_2"] = len(nuevas & d_tr)
            med["remisiones"]["nuevas_con_un_extremo_en_un_nodo_de_D"] = sum(1 for s, t in nuevas if s in d_nodos or t in d_nodos)
            med["aislamiento"]["aristas_que_cambian_por_las_dos_piezas"] = len(nuevas & d_tr)
            med["aislamiento"]["ok"] = med["aislamiento"]["ok"] and not (nuevas & d_tr)
        # los hubs, con la regla de la familia 5
        uA, hA = hubs(A)
        uB, hB = hubs(B)
        orig_nuevas = {s for s, _ in nuevas}
        dest_nuevas = {t for _, t in nuevas}
        med["hubs"] = {"umbral": [uA, uB], "hubs": [len(hA), len(hB)], "entran": len(hB - hA), "salen": len(hA - hB),
                       "entran_por_tipo": dict(collections.Counter(NB[i]["type"] for i in hB - hA)),
                       "salen_por_tipo": dict(collections.Counter(NA[i]["type"] for i in hA - hB)),
                       "entran_solo_como_origen_de_las_nuevas": sum(1 for i in hB - hA if i in orig_nuevas and i not in dest_nuevas),
                       "entran_como_destino_de_las_nuevas": sum(1 for i in hB - hA if i in dest_nuevas),
                       "sha256_ids_hubs": [hashlib.sha256("\n".join(sorted(h)).encode()).hexdigest() for h in (hA, hB)]}
    if a.pieza == "C1":
        uA, hA = hubs(A)
        uB, hB = hubs(B)
        med["hubs_informativo"] = {"umbral": [uA, uB], "hubs": [len(hA), len(hB)]}

    # 8. el cegamiento y lo que queda para componer
    med["cegamiento"] = {"filas_no_listadas_por_la_muestra": dict(ocultas), "casos_en_espera": "sí" if en_espera else "no"}
    if en_espera:
        escribir(a.salida / "NO_ABRIR_casos_en_espera.json", en_espera)
    trabajo = {"pieza": a.pieza, "grafo": a.grafo, "tabla": tabla,
               "remite_a": [list(x) for x in remite],
               "nodos_de_c1": sorted({n["id"] for n in B["nodes"] if any("punto_declarado_e1" in (p or {})
                                                                          for p in n.get("provenances") or [])})}
    escribir(a.trabajo / f"{a.etiqueta}.json", trabajo)
    sha_med = escribir(a.salida / "medicion.json", med)
    print(json.dumps({"etiqueta": a.etiqueta, "aislamiento_ok": med["aislamiento"]["ok"], "tabla_pares": med["tabla"].get("pares"),
                      "nodos": [med["nodos"]["anterior"], med["nodos"]["nuevo"]],
                      "aristas": [med["aristas"]["anterior"], med["aristas"]["nuevo"]],
                      "remite_a": [med["remite_a_que_cambian"]["entran"], med["remite_a_que_cambian"]["salen"]],
                      "casos_en_espera": med["cegamiento"]["casos_en_espera"], "medicion_sha256": sha_med}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
