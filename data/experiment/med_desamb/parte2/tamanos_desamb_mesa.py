"""Mesa, §139 (17/10/2026), U-MED-DESAMB, parte 2: los tamaños de la desambiguación, sin modelo y sin muestras.

Tres cuentas sobre un grafo ensamblado (kg.json) y su registro de resolución (resolucion_sujetos.jsonl):
  A. por tipo, los nodos con la misma clave de texto en puntos distintos del mismo documento, los grupos y cuántos están
     conectados (remite_a entre sus puntos, o el mismo encabezado padre de E0), con 3 ejemplos de cada clase; para Operacion,
     también con la clave plegada de VERIF-UNION-OPERACIONES (tarea 3, reports/verif_union_ops/verif_union_ops.py:160-175);
  B. las relaciones de sujeto (aplica_a y ejecuta) por estrato de resolución, E1 a E10 y la cuarentena;
  C. las Comunicacion repetidas entre documentos, por la clave de E2 y por el código normalizado de C1, con todas las
     colisiones listadas para leerlas.
La clave de texto es la de entity_slug_r2 del código de HEAD (data/experiment/reextraccion_v2/e2_reduce/e2_lib.py:845-871), fase
r2b, con una procedencia fija por documento: así dos nodos tienen la misma clave de texto si y solo si su clave de fusión r2b
difiere solo en el punto. Trabaja por ocurrencia (nodo, punto): en el perfil r2a la Operacion se une entre puntos y un nodo puede
estar en varios.
No escribe en el repo ni en el clon: lee el kg y el registro y escribe en --salida.

Uso: python3 -I -B tamanos_desamb_mesa.py --e2lib <dir de e2_lib.py> --kg <kg.json> [--kg <otro kg.json> ...]
        --resolucion <resolucion_sujetos.jsonl> [--resolucion ...] --salida <dir> [--etiqueta <texto>]
Con más de un --kg (el acumulado de las tandas), A y B se cuentan sobre el primero y C sobre todos juntos.
"""
import argparse
import collections
import hashlib
import importlib.util
import itertools
import json
import re
import sys
import unicodedata
from pathlib import Path

TIPOS_CON_PUNTO = ("Restriccion", "Obligacion", "Excepcion", "Condicion", "Definicion", "Potestad", "Operacion")
EJEMPLOS = 3

# La clave plegada de VERIF-UNION-OPERACIONES, tarea 3: copia textual de reports/verif_union_ops/verif_union_ops.py:161-175.
STOP = {"de", "del", "la", "las", "el", "los", "y", "o", "u", "e", "a", "al", "en", "por", "para",
        "con", "sin", "que", "su", "sus", "un", "una", "unos", "unas", "se", "sobre", "entre",
        "segun", "como", "mas", "otro", "otros", "otra", "otras", "lo"}


def plegar(t):
    if len(t) > 4 and t.endswith("es") and t[-3] in "lnrdzj":
        return t[:-2]
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t


def cargar_e2lib(d):
    spec = importlib.util.spec_from_file_location("e2_lib_head", str(Path(d) / "e2_lib.py"))
    m = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(m)
    return m


def palabras(E, label):
    return frozenset(plegar(t) for t in E.slugify_full(label).split("_") if t and t not in STOP)


def ocurrencias(n):
    """(to, punto) de cada procedencia del nodo, sin repetir, en orden."""
    vistos = []
    for p in n.get("provenances") or [n.get("provenance") or {}]:
        k = (p.get("to"), p.get("punto"))
        if k[0] and k[1] and k not in vistos:
            vistos.append(k)
    return vistos


def padres(nodos):
    """(to, punto) → el último ancestro de E0 (el encabezado padre), de la primera procedencia que lo trae."""
    out = {}
    for n in nodos:
        for p in n.get("provenances") or []:
            k = (p.get("to"), p.get("punto"))
            if k not in out and p.get("ancestros") is not None:
                a = p.get("ancestros") or []
                out[k] = a[-1] if a else None
    return out


def remisiones(aristas):
    """(to, punto origen, punto destino) de las remite_a internas, desde cada procedencia de la arista."""
    R = set()
    for e in aristas:
        if e.get("relation") != "remite_a":
            continue
        pr = e.get("properties") or {}
        if pr.get("alcance") != "interna" or "::" not in str(pr.get("destino") or ""):
            continue
        to_d, p_d = str(pr["destino"]).split("::", 1)
        for p in e.get("provenances") or [e.get("provenance") or {}]:
            if p.get("to") == to_d and p.get("punto"):
                R.add((to_d, p["punto"], p_d))
    return R


def clase_de_grupo(puntos, enlace):
    """conectado: todos los puntos en una sola componente con los enlaces; parcial: hay enlaces pero más de una
    componente; sin_conexion: ningún enlace."""
    padre = {p: p for p in puntos}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x
    hay = False
    for a, b in itertools.combinations(sorted(puntos), 2):
        if enlace(a, b):
            hay = True
            padre[raiz(a)] = raiz(b)
    comps = len({raiz(p) for p in puntos})
    return "conectado" if comps == 1 else ("parcial" if hay else "sin_conexion")


def cuenta_A(E, g, clave_de):
    nodos = g["nodes"]
    R = remisiones(g["edges"])
    PAD = padres(nodos)
    por_tipo = collections.Counter(n["type"] for n in nodos)
    grupos = collections.defaultdict(lambda: collections.defaultdict(set))   # (tipo, to, clave) -> punto -> {ids}
    for n in nodos:
        if n["type"] not in clave_de:
            continue
        for to, punto in ocurrencias(n):
            k = clave_de[n["type"]](n, to)
            if k is not None:
                grupos[(n["type"], to, k)][punto].add(n["id"])

    def rem(to, a, b):
        return (to, a, b) in R or (to, b, a) in R

    def mismo_padre(to, a, b):
        pa, pb = PAD.get((to, a)), PAD.get((to, b))
        return pa is not None and pa == pb
    res = {}
    for t in clave_de:
        gs = {k: v for k, v in grupos.items() if k[0] == t and len(v) >= 2}
        ids = {i for v in gs.values() for s in v.values() for i in s}
        occ = sum(len(s) for v in gs.values() for s in v.values())
        clases, ejemplos = collections.Counter(), collections.defaultdict(list)
        pares = collections.Counter()
        for (tt, to, k), v in sorted(gs.items(), key=lambda x: (x[0][1], x[0][2])):
            c = clase_de_grupo(set(v), lambda a, b: rem(to, a, b) or mismo_padre(to, a, b))
            clases[c] += 1
            for a, b in itertools.combinations(sorted(v), 2):
                r, m = rem(to, a, b), mismo_padre(to, a, b)
                pares["remite_a_y_padre" if r and m else "remite_a" if r else "mismo_padre" if m else "ninguno"] += 1
            if len(ejemplos[c]) < EJEMPLOS:
                ejemplos[c].append({"to": to, "puntos": sorted(v), "ids": sorted({i for s in v.values() for i in s})[:6],
                                    "padres": {p: PAD.get((to, p)) for p in sorted(v)}})
        res[t] = {"nodos_del_tipo": por_tipo[t], "grupos": len(gs), "nodos_en_grupos": len(ids),
                  "ocurrencias_en_grupos": occ,
                  "porcentaje_de_nodos": round(100 * len(ids) / por_tipo[t], 2) if por_tipo[t] else None,
                  "clases_de_grupo": dict(clases), "pares_de_puntos": dict(pares),
                  "vinculos_candidatos_O1": pares["remite_a"] + pares["mismo_padre"] + pares["remite_a_y_padre"],
                  "ejemplos": dict(ejemplos)}
    return res


def estrato(r):
    """Los estratos de la lectura (pedido de la §139): E1 R1 sin desacuerdo, E2 R1 con desacuerdo, E3 R4 con regla del texto que da
    el mismo id, E4 R4 con regla que da otro id, E5 R4 sin regla con mención verificada, E6 R4 con mención no verificada, E7 R2,
    E8 calificador, E9 R3; E10 R4 sin mención (el perfil r2a no la traía). La regla de decisión de r1_e4.py:425-438."""
    m = r["metodo_resolucion"]
    if m.startswith("R1_"):
        return "E2" if r["desacuerdo_regla_modelo"] else "E1"
    if m == "R4_sugerencia_modelo":
        v = r.get("mencion_verificada")
        if v == "no":
            return "E6"
        if v not in ("exacta", "tokens"):
            return "E10"
        if r.get("regla_texto") is None:
            return "E5"
        return "E3" if r.get("id_regla_texto") == r.get("sujeto_id_modelo") else "E4"
    if m == "R2_calificador":
        return "E8"
    if m.startswith("R2_"):
        return "E7"
    if m == "R3":
        return "E9"
    if m == "cuarentena":
        return "cuarentena"
    return "otro:" + m


def cuenta_B(g, filas):
    por = collections.defaultdict(collections.Counter)
    for r in filas:
        por[r["predicado"]][estrato(r)] += 1
    aristas = collections.Counter(e["relation"] for e in g["edges"] if e["relation"] in ("aplica_a", "ejecuta"))
    llega = collections.defaultdict(set)   # estrato -> aristas del grafo (fuente, destino, procedencia) a las que llega una fila
    idx = collections.defaultdict(list)
    for e in g["edges"]:
        if e["relation"] in ("aplica_a", "ejecuta"):
            for p in e.get("provenances") or [e.get("provenance") or {}]:
                idx[(e["relation"], p.get("chunk_id"), e["target"] if e["relation"] == "aplica_a" else e["source"])].append(
                    (e["source"], e["target"]))
    for r in filas:
        if r.get("resuelto_a"):
            for x in idx.get((r["predicado"], r["chunk_id"], r["resuelto_a"]), []):
                llega[estrato(r)].add((r["predicado"],) + x)
    return {"filas_por_predicado_y_estrato": {k: dict(sorted(v.items())) for k, v in por.items()},
            "total_filas": len(filas), "aristas_del_grafo": dict(aristas),
            "aristas_alcanzadas_por_estrato": {k: len(v) for k, v in sorted(llega.items())},
            "nota": "una arista del grafo junta las relaciones de igual fuente, destino y predicado: una fila del registro llega a "
                    "las aristas de su chunk con su sujeto resuelto; las cuentas por estrato pueden solaparse"}


RE_BCRA = re.compile(r"^(?:com(?:unicacion)?\s*)?([abcp])\s*[-.]?\s*(\d{3,5})$")


def codigo_normalizado(n):
    """La normalización de C1 (propuesta, se sella antes de medir): la Comunicación del BCRA por letra y número
    («A-6847», «Com. A 6847», «Comunicación A 6847» → «A 6847»); lo demás, por su código en minúsculas, sin acentos y sin
    puntuación. None (no se une nunca) si no hay número o es un marcador: «sin especificar», número 0, o tipo
    «referencia» o «TO» (remisiones internas, no comunicaciones)."""
    p = n.get("properties") or {}
    tipo = str(p.get("tipo") or "").strip().lower()
    cod = str(p.get("codigo") or "").strip()
    if not cod or "sin especificar" in cod.lower() or tipo in ("referencia", "to"):
        return None
    s = unicodedata.normalize("NFKD", cod)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\s+", " ", s).strip()
    m = RE_BCRA.match(s.replace("comunicacion", "com").replace("com.", "com"))
    if m:
        return f"{m.group(1).upper()} {int(m.group(2))}"
    if not re.search(r"\d", s) and tipo != "externa":
        return None
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def cuenta_C(E, gs):
    por_e2 = collections.defaultdict(list)
    por_c1 = collections.defaultdict(list)
    for etiqueta, g in gs:
        for n in g["nodes"]:
            if n["type"] != "Comunicacion":
                continue
            tos = sorted({p.get("to") for p in n.get("provenances") or [] if p.get("to")})
            fila = {"grafo": etiqueta, "id": n["id"], "label": n.get("label"), "codigo": (n.get("properties") or {}).get("codigo"),
                    "tipo": (n.get("properties") or {}).get("tipo"), "tos": tos}
            por_e2[E.entity_slug_v3(n)].append(fila)
            c = codigo_normalizado(n)
            if c:
                por_c1[c].append(fila)
    rep = lambda d: {k: v for k, v in d.items() if len({t for f in v for t in f["tos"]}) >= 2}  # noqa: E731
    r_e2, r_c1 = rep(por_e2), rep(por_c1)
    colisiones = []
    for k, v in sorted(r_c1.items()):
        crudos = sorted({str(f["codigo"]) for f in v})
        colisiones.append({"codigo_normalizado": k, "nodos": len(v), "tos": sorted({t for f in v for t in f["tos"]}),
                           "codigos_crudos": crudos, "codigos_crudos_distintos": len(crudos) > 1, "filas": v})
    nodos_c = sum(1 for _, g in gs for n in g["nodes"] if n["type"] == "Comunicacion")
    return {"nodos_comunicacion": nodos_c,
            "repetidas_por_clave_e2": {"grupos": len(r_e2), "nodos": sum(len(v) for v in r_e2.values())},
            "repetidas_por_codigo_c1": {"grupos": len(r_c1), "nodos": sum(len(v) for v in r_c1.values()),
                                        "con_codigos_crudos_distintos": sum(c["codigos_crudos_distintos"] for c in colisiones)},
            "sin_unir_nunca_por_c1": sum(1 for _, g in gs for n in g["nodes"] if n["type"] == "Comunicacion" and codigo_normalizado(n) is None),
            "colisiones_para_leer": colisiones}


def cuenta_D(E, g, registro):
    """Dos controles del mapa (§139): (1) ids de propuesto que juntan menciones distintas por el corte del slug en 80 caracteres
    (e2_lib.py:830-832); (2) Comunicacion con el mismo código normalizado en más de un nodo dentro de un documento (fuera de C1)."""
    por_id = collections.defaultdict(set)
    for f in registro:
        base = E.slugify_full(str(f.get("mencion") or f.get("sujeto_id_crudo") or "").strip())
        por_id[f"Sujeto_propuesto_{base[:80]}"].add(base)
    intra = collections.defaultdict(set)
    for n in g["nodes"]:
        c = codigo_normalizado(n) if n["type"] == "Comunicacion" else None
        for to in {p.get("to") for p in n.get("provenances") or []} if c else ():
            intra[(to, c)].add(n["id"])
    return {"propuestos_con_slug_de_mas_de_80": sum(1 for v in por_id.values() if any(len(s) > 80 for s in v)),
            "propuestos_que_juntan_menciones_por_el_corte": sorted([k, sorted(v)] for k, v in por_id.items() if len(v) > 1),
            "comunicacion_variantes_dentro_de_un_documento": sorted([list(k), sorted(v)] for k, v in intra.items() if len(v) > 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2lib", required=True)
    ap.add_argument("--kg", action="append", required=True)
    ap.add_argument("--resolucion", action="append", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--etiqueta", default="")
    ap.add_argument("--registro", help="no_mapeados_sujetos.jsonl, para los controles D")
    a = ap.parse_args()
    E = cargar_e2lib(a.e2lib)
    gs = []
    for p in a.kg:
        b = Path(p).read_bytes()
        gs.append((hashlib.sha256(b).hexdigest()[:8], json.loads(b)))
    filas = [json.loads(l) for p in a.resolucion[:1] for l in open(p, encoding="utf-8") if l.strip()]
    prov_fija = lambda to: {"to": to, "punto": ""}  # noqa: E731
    clave_r2 = {t: (lambda n, to: E.entity_slug_r2(n, prov_fija(to), fase="r2b")) for t in TIPOS_CON_PUNTO}
    clave_plegada = {"Operacion": (lambda n, to: (tuple(sorted(palabras(E, n.get("label") or ""))) or None))}
    out = {"etiqueta": a.etiqueta, "kg_sha256_8": [h for h, _ in gs],
           "resolucion_sha256_8": hashlib.sha256(Path(a.resolucion[0]).read_bytes()).hexdigest()[:8],
           "A_misma_clave_de_texto_en_puntos_distintos": cuenta_A(E, gs[0][1], clave_r2),
           "A_operacion_clave_plegada_tarea_3": cuenta_A(E, gs[0][1], clave_plegada)["Operacion"],
           "A_tipos_sin_punto_en_la_clave": {t: "la clave no lleva el punto: un nodo por clave en el documento (y entre "
                                             "documentos, salvo la guarda)" for t in ("Sujeto", "Comunicacion", "TextoOrdenado")},
           "B_relaciones_de_sujeto_por_estrato": cuenta_B(gs[0][1], filas),
           "C_comunicacion_entre_documentos": cuenta_C(E, gs),
           "D_controles": cuenta_D(E, gs[0][1], [json.loads(l) for l in open(a.registro, encoding="utf-8") if l.strip()] if a.registro else [])}
    S = Path(a.salida)
    S.mkdir(parents=True, exist_ok=True)
    (S / "tamanos_desamb.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    A = out["A_misma_clave_de_texto_en_puntos_distintos"]
    print(f"[{a.etiqueta}] kg {out['kg_sha256_8']} | resolución {out['resolucion_sha256_8']}")
    for t, v in A.items():
        print(f"  A {t:<11} nodos {v['nodos_del_tipo']:>5} | grupos {v['grupos']:>4} | nodos en grupos {v['nodos_en_grupos']:>4} "
              f"({v['porcentaje_de_nodos']} %) | clases {v['clases_de_grupo']} | pares {v['pares_de_puntos']}")
    v = out["A_operacion_clave_plegada_tarea_3"]
    print(f"  A Operacion, plegada: grupos {v['grupos']} | nodos en grupos {v['nodos_en_grupos']} | clases {v['clases_de_grupo']}")
    b = out["B_relaciones_de_sujeto_por_estrato"]
    print("  B", b["filas_por_predicado_y_estrato"], "| aristas", b["aristas_del_grafo"])
    c = out["C_comunicacion_entre_documentos"]
    print("  C", {k: c[k] for k in ("nodos_comunicacion", "repetidas_por_clave_e2", "repetidas_por_codigo_c1", "sin_unir_nunca_por_c1")})
    dd = out["D_controles"]
    print("  D", {"propuestos_con_slug_de_mas_de_80": dd["propuestos_con_slug_de_mas_de_80"],
                 "propuestos_que_juntan_menciones_por_el_corte": len(dd["propuestos_que_juntan_menciones_por_el_corte"]),
                 "comunicacion_variantes_dentro_de_un_documento": len(dd["comunicacion_variantes_dentro_de_un_documento"])})


if __name__ == "__main__":
    main()
