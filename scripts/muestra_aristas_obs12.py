#!/usr/bin/env python3
"""Sorteo de la observación (12) del pre-registro de la tanda 0 (gate 8 de la fase 2 de B6.0).

Toma un kg.json, aplica el universo de aristas de extracción de la observación
(10) (pre-registro A4.1), ordena por la tripla (source, relation, target),
sortea k índices con random.Random(semilla).sample(range(n), k) y escribe la
muestra con origen, relación, destino, propiedades, provenance y el texto del
punto ancla resuelto en la salida de E0. Regla completa:
docs/enmienda_preregistro_tanda0_2026-09-27_observacion12.md §2.1 y §2.2.

Solo stdlib. Todo lo que lee (kg.json, chunks_<to>.json de E0) es SOLO
LECTURA: este script no modifica ninguna entrada. Escribe exactamente dos
archivos en --out: muestra_obs12.json (sin fecha ni hora: dos corridas con los
mismos argumentos son byte-idénticas) y muestra_obs12.md (legible, con fecha).

Uso:
    PYTHONDONTWRITEBYTECODE=1 python3 scripts/muestra_aristas_obs12.py \
        --kg RUTA --semilla ENTERO --out DIRECTORIO [--n 30] [--e0 DIRECTORIO]

Sin --out no escribe nada y frena con mensaje (código de salida 2).

Universo (A4.1): todas las aristas menos relation == 'referencia' y menos
rol_fuente == 'esqueleto', con rol_fuente leído como e.get('rol_fuente') o,
si no está, provenance.rol_fuente. Las aristas padre_sugerido
(rol_fuente cuarentena_flaggeada) quedan DENTRO del universo.

Remisión en sus dos formas (U-R2-CODIGO, R5.d; enmienda 2 de L-ESQ-R2): con
el perfil r2 la remisión entre puntos es la arista `remite_a`, que se resta
del universo igual que `referencia` (scripts/remisiones.py). Un grafo sin
`remite_a` (todos los existentes) da la misma salida que antes, byte a byte:
el campo `remite_a_restadas` y su nota en la regla se escriben solo cuando el
grafo tiene aristas `remite_a`.

Orden: tripla (source, relation, target) en orden lexicográfico de cadenas,
orden estable (las triplas duplicadas conservan el orden del kg.json y se
cuentan en el campo triplas_duplicadas).

Texto del punto ancla: <e0>/chunks_<to>.json, chunk cuyo campo id coincide
con provenance.chunk_id de la arista; <to> = provenance.to o, si falta, el
prefijo de chunk_id antes de '::'. Si el chunk o el archivo no existen,
texto_ancla = "NO ENCONTRADO: <chunk_id>", no frena, y la ausencia se cuenta
en textos_no_encontrados.
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import random
import sys

sys.dont_write_bytecode = True

import remisiones  # noqa: E402  (scripts/remisiones.py, solo stdlib)

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)

E0_DEFAULT = "data/experiment/reextraccion_v2/e0_chunking/salida_enm01"
K_DEFAULT = 30
NOMBRE_JSON = "muestra_obs12.json"
NOMBRE_MD = "muestra_obs12.md"
NO_ENCONTRADO = "NO ENCONTRADO"

REGLA = {
    "universo": "todas las aristas del kg.json menos relation == 'referencia' "
                "y menos rol_fuente == 'esqueleto' (rol_fuente = "
                "e.get('rol_fuente') or provenance.rol_fuente); pre-registro A4.1",
    "orden": "tripla (source, relation, target), orden lexicografico de "
             "cadenas, orden estable",
    "sorteo": "sorted(random.Random(semilla).sample(range(n), k))",
    "texto_ancla": "<e0>/chunks_<to>.json, chunk con id == provenance.chunk_id; "
                   "campo texto; herencia tal como esta",
    "fuente": "docs/enmienda_preregistro_tanda0_2026-09-27_observacion12.md "
              "§2.1 y §2.2",
}
NOTA_REMITE_A = ("con el perfil r2 la remision entre puntos es remite_a (enmienda 2 de "
                 "L-ESQ-R2) y se resta igual que referencia (U-R2-CODIGO, R5.d; "
                 "scripts/remisiones.py)")


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def rol_fuente(e):
    """rol_fuente tal como lo lee el comando de A4.1."""
    return e.get("rol_fuente") or (e.get("provenance") or {}).get("rol_fuente")


def tripla(e):
    return (str(e["source"]), str(e["relation"]), str(e["target"]))


# --------------------------------------------------------------------------- #
# Universo, orden y sorteo (decisiones 1-3 del mandato)
# --------------------------------------------------------------------------- #

def universo(edges):
    """Aristas de extracción según A4.1, en el orden del kg.json.

    Devuelve (lista, conteos) con conteos = total, referencia, esqueleto y el
    solapamiento entre ambos criterios (aristas que cumplen los dos; en A4.1
    se restan de forma independiente, así que n = total - referencia -
    esqueleto + solapamiento).
    """
    total = len(edges)
    ref = 0
    esq = 0
    sol = 0
    rem = 0
    ext = []
    for e in edges:
        es_ref = e.get("relation") == "referencia"
        # la otra forma de la remisión (remite_a); la de referencia ya se resta arriba
        es_rem = not es_ref and remisiones.es_remision(e)
        es_esq = rol_fuente(e) == "esqueleto"
        if es_ref:
            ref += 1
        if es_esq:
            esq += 1
        if es_ref and es_esq:
            sol += 1
        if es_rem and not es_esq:
            rem += 1
        if not es_ref and not es_rem and not es_esq:
            ext.append(e)
    conteos = {
        "total_aristas": total,
        "referencia_restadas": ref,
        "esqueleto_restadas": esq,
        "solapamiento_referencia_esqueleto": sol,
        "n": len(ext),
    }
    if rem:
        conteos["remite_a_restadas"] = rem
    assert conteos["n"] == total - ref - esq + sol - rem
    return ext, conteos


def ordenar(ext):
    """Orden estable por la tripla (source, relation, target)."""
    return sorted(ext, key=tripla)


def triplas_duplicadas(ext_ordenado):
    """Triplas que aparecen más de una vez: cuenta y detalle."""
    c = collections.Counter(tripla(e) for e in ext_ordenado)
    detalle = [
        {"source": s, "relation": r, "target": t, "veces": v}
        for (s, r, t), v in sorted(c.items()) if v > 1
    ]
    return len(detalle), detalle


def sortear(n, k, semilla):
    """Índices ordenados ascendentes de random.Random(semilla).sample(range(n), k)."""
    return sorted(random.Random(semilla).sample(range(n), k))


# --------------------------------------------------------------------------- #
# Texto del punto ancla (decisión 6)
# --------------------------------------------------------------------------- #

class ResolutorE0:
    """Lee <e0>/chunks_<to>.json una sola vez por TO y resuelve chunk_id -> chunk."""

    def __init__(self, e0_dir):
        self.e0_dir = e0_dir
        self._por_to = {}      # to -> dict id -> chunk, o None si el archivo no existe
        self.sha256 = {}       # to -> sha256 del archivo consultado (solo los que existen)

    def _cargar(self, to):
        if to in self._por_to:
            return self._por_to[to]
        ruta = os.path.join(self.e0_dir, "chunks_%s.json" % to)
        if not os.path.isfile(ruta):
            self._por_to[to] = None
            return None
        with open(ruta, encoding="utf-8") as f:
            chunks = json.load(f)
        self._por_to[to] = {c.get("id"): c for c in chunks}
        self.sha256[to] = sha256_archivo(ruta)
        return self._por_to[to]

    def resolver(self, provenance):
        """Devuelve (chunk_id, to, chunk o None)."""
        p = provenance or {}
        chunk_id = p.get("chunk_id")
        to = p.get("to")
        if not to and isinstance(chunk_id, str) and "::" in chunk_id:
            to = chunk_id.split("::", 1)[0]
        if not to or chunk_id is None:
            return chunk_id, to, None
        indice = self._cargar(to)
        if indice is None:
            return chunk_id, to, None
        return chunk_id, to, indice.get(chunk_id)


# --------------------------------------------------------------------------- #
# Armado de la muestra
# --------------------------------------------------------------------------- #

def nodo_resumen(nodes_by_id, nid):
    n = nodes_by_id.get(nid)
    if n is None:
        return {"id": nid, "type": None, "label": None, "properties": None,
                "nodo_no_encontrado": True}
    return {"id": n.get("id"), "type": n.get("type"), "label": n.get("label"),
            "properties": n.get("properties")}


def armar_muestra(kg, kg_ruta, kg_sha, semilla, k, e0_dir, e0_como_se_paso):
    nodes_by_id = {n["id"]: n for n in kg.get("nodes", [])}
    ext, conteos = universo(kg.get("edges", []))
    ext = ordenar(ext)
    n_dup, dup_detalle = triplas_duplicadas(ext)
    n = conteos["n"]
    if k > n:
        raise ValueError("k=%d mayor que el universo n=%d" % (k, n))
    indices = sortear(n, k, semilla)

    resolutor = ResolutorE0(e0_dir)
    aristas = []
    no_encontrados = 0
    rel_counter = collections.Counter()
    for i in indices:
        e = ext[i]
        chunk_id, to, chunk = resolutor.resolver(e.get("provenance"))
        if chunk is None:
            no_encontrados += 1
            texto = "%s: %s" % (NO_ENCONTRADO,
                                chunk_id if chunk_id is not None else "chunk_id ausente")
            herencia = None
        else:
            texto = chunk.get("texto")
            herencia = chunk.get("herencia")
        rel_counter[e.get("relation")] += 1
        aristas.append({
            "indice": i,
            "source": nodo_resumen(nodes_by_id, e["source"]),
            "relation": e.get("relation"),
            "target": nodo_resumen(nodes_by_id, e["target"]),
            "properties": e.get("properties"),
            "rol_fuente": rol_fuente(e),
            "provenance": e.get("provenance"),
            "provenances": e.get("provenances"),
            "chunk_id": chunk_id,
            "texto_ancla": texto,
            "herencia": herencia,
        })

    salida = {
        "kg_ruta": kg_ruta,
        "kg_sha256": kg_sha,
        "semilla": semilla,
        "k": k,
        "n": n,
        "total_aristas": conteos["total_aristas"],
        "referencia_restadas": conteos["referencia_restadas"],
        "esqueleto_restadas": conteos["esqueleto_restadas"],
        "solapamiento_referencia_esqueleto": conteos["solapamiento_referencia_esqueleto"],
        **({"remite_a_restadas": conteos["remite_a_restadas"]} if "remite_a_restadas" in conteos else {}),
        "triplas_duplicadas": n_dup,
        "triplas_duplicadas_detalle": dup_detalle,
        "e0": e0_como_se_paso,
        "e0_chunks_sha256": {to: resolutor.sha256[to] for to in sorted(resolutor.sha256)},
        "textos_no_encontrados": no_encontrados,
        "relaciones_en_muestra": dict(sorted(rel_counter.items(),
                                             key=lambda kv: (-kv[1], kv[0]))),
        "regla": dict(REGLA, remite_a=NOTA_REMITE_A) if "remite_a_restadas" in conteos else REGLA,
        "indices": indices,
        "aristas": aristas,
    }
    return salida


# --------------------------------------------------------------------------- #
# Salida legible
# --------------------------------------------------------------------------- #

def _json_inline(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=False)


def _bloque_cita(texto):
    if texto is None:
        return "> (sin texto)"
    return "\n".join("> " + linea for linea in str(texto).split("\n"))


def render_md(s, fecha):
    L = []
    L.append("# Muestra de la observación (12) — aristas de extracción contra el texto")
    L.append("")
    L.append("- Fecha del sorteo: %s" % fecha)
    L.append("- Grafo: `%s`" % s["kg_ruta"])
    L.append("- sha256 del grafo: `%s`" % s["kg_sha256"])
    L.append("- Semilla: %d" % s["semilla"])
    L.append("- n (universo de aristas de extracción, A4.1): %d "
             "(total %d − referencia %d − esqueleto %d + solapamiento %d)"
             % (s["n"], s["total_aristas"], s["referencia_restadas"],
                s["esqueleto_restadas"], s["solapamiento_referencia_esqueleto"]))
    if "remite_a_restadas" in s:
        L.append("- remite_a restadas (remisión del perfil r2, se resta igual que referencia): %d"
                 % s["remite_a_restadas"])
    L.append("- k: %d" % s["k"])
    L.append("- Triplas duplicadas en el universo: %d" % s["triplas_duplicadas"])
    L.append("- E0: `%s`" % s["e0"])
    for to, sha in s["e0_chunks_sha256"].items():
        L.append("  - chunks_%s.json: `%s`" % (to, sha))
    L.append("- Textos del punto ancla no encontrados: %d" % s["textos_no_encontrados"])
    L.append("- Relaciones en la muestra: " + ", ".join(
        "%s %d" % (r, c) for r, c in s["relaciones_en_muestra"].items()))
    L.append("- Índices: %s" % _json_inline(s["indices"]))
    L.append("")
    L.append("Regla: universo de A4.1; orden por la tripla (source, relation, target); "
             "`sorted(random.Random(semilla).sample(range(n), k))` "
             "(enmienda del 27/09/2026, §2.1 y §2.2).")
    L.append("")
    for num, a in enumerate(s["aristas"], 1):
        src, tgt = a["source"], a["target"]
        L.append("---")
        L.append("")
        L.append("## %d · índice %d · `%s`" % (num, a["indice"], a["relation"]))
        L.append("")
        L.append("- **Origen:** `%s` · tipo `%s` · label «%s»" % (src["id"], src["type"], src["label"]))
        L.append("  - propiedades: `%s`" % _json_inline(src["properties"]))
        L.append("- **Relación:** `%s`" % a["relation"])
        L.append("- **Destino:** `%s` · tipo `%s` · label «%s»" % (tgt["id"], tgt["type"], tgt["label"]))
        L.append("  - propiedades: `%s`" % _json_inline(tgt["properties"]))
        L.append("- **Propiedades de la arista:** `%s`" % _json_inline(a["properties"]))
        L.append("- **rol_fuente:** `%s`" % _json_inline(a["rol_fuente"]))
        L.append("- **Provenance:** `%s`" % _json_inline(a["provenance"]))
        provs = a["provenances"] or []
        L.append("- **Provenances (%d):**" % len(provs))
        for p in provs:
            L.append("  - `%s`" % _json_inline(p))
        L.append("- **Texto del punto ancla** (`%s`):" % a["chunk_id"])
        L.append("")
        L.append(_bloque_cita(a["texto_ancla"]))
        L.append("")
        her = a["herencia"]
        if her:
            L.append("- **Herencia (%d):**" % len(her))
            for h in her:
                L.append("  - [%s] %s (páginas %s):" % (h.get("tipo"), h.get("unidad_origen"),
                                                        _json_inline(h.get("paginas"))))
                L.append("")
                L.append("    " + _bloque_cita(h.get("texto")).replace("\n", "\n    "))
                L.append("")
        else:
            L.append("- **Herencia:** %s" % ("(vacía)" if her == [] else "(no disponible)"))
            L.append("")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def resolver_e0(e0_arg):
    """Devuelve la ruta usable del directorio de E0 (tal cual o relativa al repo)."""
    if os.path.isdir(e0_arg):
        return e0_arg
    alternativa = os.path.join(REPO, e0_arg)
    if os.path.isdir(alternativa):
        return alternativa
    return e0_arg  # no existe: cada chunk saldrá como NO ENCONTRADO


def construir_parser():
    p = argparse.ArgumentParser(
        prog="muestra_aristas_obs12.py",
        description="Sorteo de la observación (12): muestra de aristas de extracción "
                    "de un kg.json, ordenadas por (source, relation, target) y sorteadas "
                    "con random.Random(semilla).sample(range(n), k), con el texto del "
                    "punto ancla resuelto en la salida de E0.")
    p.add_argument("--kg", required=True, help="ruta del kg.json (solo lectura)")
    p.add_argument("--semilla", required=True, type=int,
                   help="semilla entera del sorteo (la observación (12) usa 20260927)")
    p.add_argument("--out", default=None,
                   help="directorio de salida; sin esta opción no se escribe nada")
    p.add_argument("--n", type=int, default=K_DEFAULT, dest="k", metavar="N",
                   help="tamaño de la muestra (default %d)" % K_DEFAULT)
    p.add_argument("--e0", default=E0_DEFAULT,
                   help="directorio de salida de E0 con chunks_<to>.json (default %s)" % E0_DEFAULT)
    return p


def main(argv=None):
    args = construir_parser().parse_args(argv)

    if not args.out:
        print("ERROR: falta --out. Sin directorio de salida no se escribe nada "
              "(muestra_obs12.json y muestra_obs12.md).", file=sys.stderr)
        return 2
    if not os.path.isfile(args.kg):
        print("ERROR: no existe el kg.json: %s" % args.kg, file=sys.stderr)
        return 2
    if args.k <= 0:
        print("ERROR: --n debe ser un entero positivo (recibido %d)" % args.k, file=sys.stderr)
        return 2

    kg_sha = sha256_archivo(args.kg)
    with open(args.kg, encoding="utf-8") as f:
        kg = json.load(f)

    e0_dir = resolver_e0(args.e0)
    try:
        salida = armar_muestra(kg, args.kg, kg_sha, args.semilla, args.k, e0_dir, args.e0)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    ruta_json = os.path.join(args.out, NOMBRE_JSON)
    ruta_md = os.path.join(args.out, NOMBRE_MD)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
        f.write("\n")
    fecha = datetime.date.today().isoformat()
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(render_md(salida, fecha))

    print("kg: %s" % args.kg)
    print("sha256 kg: %s" % kg_sha)
    print("semilla: %d  k: %d" % (args.semilla, args.k))
    print("total %d  referencia %d  esqueleto %d  solapamiento %d  n %d" % (
        salida["total_aristas"], salida["referencia_restadas"], salida["esqueleto_restadas"],
        salida["solapamiento_referencia_esqueleto"], salida["n"]))
    if "remite_a_restadas" in salida:
        print("remite_a restadas: %d" % salida["remite_a_restadas"])
    print("triplas_duplicadas: %d" % salida["triplas_duplicadas"])
    print("indices: %s" % salida["indices"])
    print("relaciones_en_muestra: %s" % salida["relaciones_en_muestra"])
    print("e0: %s (%s)" % (args.e0, e0_dir))
    print("textos_no_encontrados: %d" % salida["textos_no_encontrados"])
    if salida["textos_no_encontrados"]:
        print("AVISO: %d texto(s) del punto ancla no encontrados en E0; ver texto_ancla "
              "en el JSON" % salida["textos_no_encontrados"])
    print("escrito: %s" % ruta_json)
    print("escrito: %s" % ruta_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
