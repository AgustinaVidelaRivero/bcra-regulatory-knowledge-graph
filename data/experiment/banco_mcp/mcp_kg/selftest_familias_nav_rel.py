#!/usr/bin/env python3
"""selftest_familias_nav_rel.py — N7c, etapa C1: las pruebas de NavegadorRel (familias_nav_rel.py) y de su servidor
(servidor_mcp_kg_nav_rel.py), con un grafo de juguete y un doble del driver, sin Neo4j, sin el denso y sin modelo de
lenguaje (USD 0). El índice por punto de juguete se escribe en <trabajo> con el formato y los sha256 que controla el
constructor de familias_nav.Navegador; el doble responde las consultas que hacen el constructor, ver_punto,
ver_remisiones, tipos_de_relacion, vecinos_por_relacion y la sección nueva, y cualquier otra la hace fallar.

Casos:
  C1  cada grupo y cada dirección: las filas de `relacionados` y el texto de la sección, renglón por renglón, contra lo
      escrito a mano; un ancestro y un descendiente entran; un nodo de dos puntos une a los dos; aplica_a no entra;
  C2  fuera: un contenedor de más de 10 claves y un TextoOrdenado (en las dos puntas), el hub (en las dos puntas: como
      vecino y como nodo propio del punto) y el mismo punto (una arista interna);
  C3  el tope: 12 relacionados dan 10 renglones y el pie con 2; 10 dan 10 sin pie; «ninguno» con un nodo sin aristas
      de esos tipos y con un punto sin nodos;
  C4  la salida anterior como prefijo exacto: en todos los puntos del juguete, con max_nodos 1, 15 y 25, la salida de
      NavegadorRel es la de NavegadorCand, un salto de línea y la sección; un punto que no existe y un TO dan lo mismo;
  C5  el servidor: tools_de([1..5]) de servidor_mcp_kg_nav_rel y de servidor_mcp_kg_nav_cand dan las mismas diez
      herramientas, con las mismas descripciones y esquemas (y las mismas herramientas de MCP); las familias de las
      configs de N7 y de N7c, iguales; la versión; abrir_navegador da un NavegadorRel; despachar da lo mismo en las
      otras seis herramientas de las familias y, en ver_punto, la salida de N7 como prefijo.
Imprime y escribe solo cuentas, booleanos y sha256: sin rutas ni horas, así dos corridas dan el mismo archivo.
Uso (con el python del .venv del repo, desde una copia, nunca del repo):
  python -B data/experiment/banco_mcp/mcp_kg/selftest_familias_nav_rel.py --trabajo <carpeta nueva> --salida <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import familias_nav_rel as FNR  # noqa: E402
import servidor_mcp_kg_nav_cand as SC  # noqa: E402  (HEAD, sin editar)
import servidor_mcp_kg_nav_rel as SR  # noqa: E402

FNC, FN, IP = FNR.FNC, FNR.FN, FNR.IP
BM = FN.BM
TO = "jug"
LABEL = "KG_Juguete_N7c"
GRAFO = "KG_Acumulado_Tandas0y1yFinal_r2b_sincola"   # solo para la etiqueta de GRAFOS en abrir_navegador
KG_SHA = "0" * 64


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# El juguete                                                                  #
# --------------------------------------------------------------------------- #
# Los puntos (unidad -> título) y los nodos (id -> (tipo, puntos)). jug::1 tiene dos hijos; jug::40 y jug::90 son los
# del tope; jug::70 y jug::71, los de «ninguno»; jug::80, el relleno que le da grado al hub.
TITULOS = {"1": "Uno", "1.1": "Uno uno", "1.2": "Uno dos", "2": "Dos", "3": "Tres", "4": "Cuatro", "5": "Cinco",
           "6": "Seis", "7": "Siete", "8": "Ocho", "9": "Nueve", "10": "Diez", "11": "Once", "40": "Cuarenta",
           "70": "Setenta", "71": "Setenta y uno", "80": "Relleno", "90": "Noventa"}
TITULOS |= {str(i): f"Destino {i}" for i in list(range(20, 31)) + list(range(41, 53)) + list(range(91, 100)) + [89]}
NODOS = {"a1": ("Obligacion", ["1"]), "a2": ("Obligacion", ["1"]), "g1": ("Definicion", ["1.1"]),
         "g2": ("Definicion", ["1.2"]), "b1": ("Obligacion", ["2"]), "c1": ("Condicion", ["3"]),
         "d1": ("Excepcion", ["4"]), "e1": ("Condicion", ["5"]), "f1": ("Sujeto", ["6"]),
         "b2": ("Obligacion", ["7", "8"]), "T": ("TextoOrdenado", ["9"]),
         "C": ("Sujeto", [str(i) for i in range(20, 31)]), "H": ("Sujeto", ["10"]), "h2": ("Obligacion", ["10"]),
         "b3": ("Obligacion", ["11"]), "t0": ("Obligacion", ["40"]), "n70": ("Obligacion", ["70"]),
         "w0": ("Obligacion", ["90"])}
NODOS |= {f"u{i}": ("Obligacion", [str(40 + i)]) for i in range(1, 13)}
NODOS |= {f"x{i}": ("Obligacion", [str(u)]) for i, u in enumerate(list(range(91, 100)) + [89], 1)}
NODOS |= {f"r{i}": ("Sujeto", ["80"]) for i in range(1, 16)}
ARISTAS = [("a1", "remite_a", "b1"),                                     # jug::2: remisión, sale
           ("c1", "condicion_de", "a1"),                                 # jug::3: condición, entra
           ("a2", "exceptua", "d1"), ("d1", "limita", "a2"),             # jug::4: condición y excepción, las dos, 2
           ("a1", "requiere", "e1"), ("a1", "condiciona", "e1"),
           ("e1", "exceptua_obligacion", "a2"),                          # jug::5: condición y excepción, las dos, 3
           ("a1", "aplica_a", "f1"),                                     # jug::6: otro tipo, no entra
           ("a1", "remite_a", "a2"),                                     # interna: el mismo punto, no entra
           ("a1", "remite_a", "g1"),                                     # jug::1.1, el hijo: entra
           ("g2", "requiere", "a2"),                                     # jug::1.2, el hijo: entra
           ("a2", "remite_a", "b2"),                                     # jug::7 y jug::8: un nodo de dos puntos
           ("a1", "remite_a", "C"), ("C", "remite_a", "a1"),             # el contenedor de 11 claves, en las dos puntas
           ("a2", "condiciona", "T"), ("T", "remite_a", "a2"),           # el TextoOrdenado, en las dos puntas
           ("a1", "remite_a", "H"),                                      # el hub como vecino
           ("H", "remite_a", "b3"), ("h2", "remite_a", "b1")]            # jug::10: el hub como nodo propio
ARISTAS += [("t0", "remite_a", f"u{i}") for i in range(1, 13)]           # jug::40: 12 relacionados
ARISTAS += [("w0", "remite_a", f"x{i}") for i in range(1, 11)]           # jug::90: 10 relacionados
ARISTAS += [("H", "aplica_a", f"r{i}") for i in range(1, 16)]            # el grado del hub
ARISTAS += [("n70", "aplica_a", "f1")]                                   # jug::70: solo otro tipo

# Lo esperado, escrito a mano: (clave, grupos, dirección, aristas), en el orden de la sección.
ESPERADO = {
    "jug::1": [("jug::5", ["condición", "excepción"], "las dos", 3), ("jug::4", ["condición", "excepción"], "las dos", 2),
               ("jug::1.1", ["remisión"], "sale", 1), ("jug::1.2", ["condición"], "entra", 1),
               ("jug::2", ["remisión"], "sale", 1), ("jug::3", ["condición"], "entra", 1),
               ("jug::7", ["remisión"], "sale", 1), ("jug::8", ["remisión"], "sale", 1)],
    "jug::1.1": [("jug::1", ["remisión"], "entra", 1)],
    "jug::1.2": [("jug::1", ["condición"], "sale", 1)],
    "jug::2": [("jug::1", ["remisión"], "entra", 1), ("jug::10", ["remisión"], "entra", 1)],
    "jug::7": [("jug::1", ["remisión"], "entra", 1)],
    "jug::10": [("jug::2", ["remisión"], "sale", 1)],
    "jug::11": [],
    "jug::40": [(f"jug::{40 + i}", ["remisión"], "sale", 1) for i in range(1, 13)],
    "jug::90": sorted([(f"jug::{u}", ["remisión"], "sale", 1) for u in list(range(91, 100)) + [89]]),
    "jug::70": [], "jug::71": [], "jug::9": [], "jug::20": [],
}
SECCION_JUG_1 = [
    "Puntos relacionados (8 de 8; punto | título | relación | dirección | aristas):",
    "jug::5 | Cinco | condición, excepción | las dos | 3",
    "jug::4 | Cuatro | condición, excepción | las dos | 2",
    "jug::1.1 | Uno uno | remisión | sale | 1",
    "jug::1.2 | Uno dos | condición | entra | 1",
    "jug::2 | Dos | remisión | sale | 1",
    "jug::3 | Tres | condición | entra | 1",
    "jug::7 | Siete | remisión | sale | 1",
    "jug::8 | Ocho | remisión | sale | 1"]


def indice_juguete(dirp: Path) -> str:
    """Escribe el índice por punto de juguete y devuelve el sha256 de su manifiesto."""
    hijos = {"1": ["1.1", "1.2"]}
    padre = {"1.1": "1", "1.2": "1"}
    puntos = {TO: {"bloques": [], "clave": TO, "en_estructura": True, "herencia": [], "hijos": [], "intro": False,
                   "nodos": [], "padre": None, "pagina": None, "paginas": [], "textos": [], "tipo": "to",
                   "titulo": "Juguete", "to": TO, "unidad": None}}
    for u in sorted(TITULOS, key=lambda x: [int(y) for y in x.split(".")]):
        k = f"{TO}::{u}"
        puntos[k] = {"bloques": [], "clave": k, "en_estructura": True, "herencia": [],
                     "hijos": [f"{TO}::{h}" for h in hijos.get(u, [])], "intro": False, "nodos": [],
                     "padre": f"{TO}::{padre[u]}" if u in padre else TO, "pagina": 1, "paginas": [1],
                     "textos": [f"Texto del punto {u}."], "tipo": "punto", "titulo": TITULOS[u], "to": TO, "unidad": u}
        if u not in padre:
            puntos[TO]["hijos"].append(k)
    nodos = {}
    for nid, (tipo, us) in NODOS.items():
        ks = [f"{TO}::{u}" for u in us]
        nodos[nid] = {"cola": False, "descripcion": None, "label": f"Nodo {nid}", "puntos": ks, "rol": "bloque",
                      "rol_por_punto": {}, "termino": None, "tramo": f"tramo de {nid}", "tramo_por_punto": {},
                      "type": tipo, "umbrales": None}
        for k in ks:
            puntos[k]["nodos"].append(nid)
    claves = [k for k in puntos if puntos[k]["tipo"] != "to"]
    docs = [{"id": k, "texto": f"{puntos[k]['titulo']}\n{puntos[k]['textos'][0]}"} for k in claves]
    archivos = {"puntos.json": IP.serializar(puntos), "nodos.json": IP.serializar(nodos),
                "documentos.json": IP.serializar(docs), "indice_bm25.json": BM.serializar(BM.construir(docs))}
    dirp.mkdir(parents=True)
    for n, b in archivos.items():
        (dirp / n).write_bytes(b)
    man = {"formato": "indice_puntos_nav v1 (juguete de N7c)", "grafo": LABEL, "kg_sha256": KG_SHA,
           "archivo_a_to": {"juguete.pdf": TO}, "archivos": {n: IP.sha256_bytes(b) for n, b in archivos.items()}}
    (dirp / "manifiesto.json").write_bytes(json.dumps(man, ensure_ascii=False, indent=1).encode("utf-8"))
    return IP.sha256_file(dirp / "manifiesto.json")


class _Resultado:
    def __init__(self, filas):
        self.filas = filas

    def data(self):
        return [dict(f) for f in self.filas]

    def single(self):
        return self.filas[0] if self.filas else None


class DriverJuguete:
    """El doble del driver: responde, sobre ARISTAS, las consultas que se esperan; cualquier otra falla."""

    def __init__(self):
        self.aristas = [{"a": a, "rel": r, "b": b, "orden": i, "eid": f"e{i}",
                         "p": {"alcance": None, "destino": None, "no_verificada_e3": None, "cola_humana": None,
                               "rol_fuente": None, "provenances_json": None}} for i, (a, r, b) in enumerate(ARISTAS)]
        self.consultas = {}

    def session(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def _anotar(self, k):
        self.consultas[k] = self.consultas.get(k, 0) + 1

    def run(self, cypher: str, **params):
        A = self.aristas
        if cypher.startswith("MATCH (m:KG_Meta"):
            self._anotar("kg_meta")
            return _Resultado([{"p": {"kg_sha256": KG_SHA, "props_aristas": ["alcance", "destino"]}}])
        if "RETURN count(n) AS c" in cypher:
            self._anotar("n_nodos")
            return _Resultado([{"c": len(NODOS)}])
        if "COUNT {" in cypher:
            self._anotar("grados")
            return _Resultado([{"id": n, "sal": sum(e["a"] == n for e in A), "ent": sum(e["b"] == n for e in A)}
                               for n in NODOS])
        if "type(r) IN $tipos" in cypher:
            ids, tipos = set(params["ids"]), set(params["tipos"])
            if cypher.startswith("MATCH (a:"):
                self._anotar("relacionados_sale")
                return _Resultado([{"r": e["eid"], "rel": e["rel"], "v": e["b"]} for e in A
                                   if e["a"] in ids and e["rel"] in tipos])
            if cypher.startswith("MATCH (b:"):
                self._anotar("relacionados_entra")
                return _Resultado([{"r": e["eid"], "rel": e["rel"], "v": e["a"]} for e in A
                                   if e["b"] in ids and e["rel"] in tipos])
        if "WHERE a.id IN $ids AND b.id IN $ids" in cypher:
            self._anotar("relaciones_ver_punto")
            ids = set(params["ids"])
            return _Resultado([{"a": e["a"], "rel": e["rel"], "b": e["b"], "p": e["p"]} for e in A
                               if e["a"] in ids and e["b"] in ids])
        if "[r:remite_a]" in cypher:
            self._anotar("remisiones")
            return _Resultado([{"a": e["a"], "b": e["b"], "destino": None, "o": e["orden"], "p": e["p"]} for e in A
                               if e["rel"] == "remite_a"])
        if "{id: $id}" in cypher:
            nid = params["id"]
            rel = cypher.split("[r:`", 1)[1].split("`", 1)[0] if "[r:`" in cypher else None
            sal = "]->(v:" in cypher
            self._anotar("vecinos")
            filas = [e for e in A if (e["a"] == nid if sal else e["b"] == nid) and (rel is None or e["rel"] == rel)]
            return _Resultado([{"rel": e["rel"], "v": e["b"] if sal else e["a"], "tipo": NODOS[e["b"] if sal else e["a"]][0],
                                "label": f"Nodo {e['b'] if sal else e['a']}", "p": e["p"]} for e in filas])
        raise AssertionError("consulta no prevista por el doble")


# --------------------------------------------------------------------------- #
class Casos:
    def __init__(self):
        self.res, self.fallos = {}, []

    def ver(self, caso: str, nombre: str, ok: bool, **extra):
        self.res.setdefault(caso, {})[nombre] = {"ok": bool(ok), **extra}
        if not ok:
            self.fallos.append(f"{caso}:{nombre}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trabajo", type=Path, required=True, help="carpeta nueva para el índice de juguete")
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    if a.trabajo.exists():
        raise SystemExit("ABORTO: --trabajo tiene que ser una carpeta nueva")
    sha_man = indice_juguete(a.trabajo / "indice_juguete")
    drv = DriverJuguete()
    nav = FNR.NavegadorRel(drv, LABEL, a.trabajo / "indice_juguete", sha256_manifiesto=sha_man)
    cand = FNC.NavegadorCand(drv, LABEL, a.trabajo / "indice_juguete", sha256_manifiesto=sha_man)
    K = Casos()
    K.ver("C0", "hubs", nav.hubs == {"H"} and nav.umbral_hub == 17, n=len(nav.hubs), umbral=nav.umbral_hub)
    K.ver("C0", "contenedores", nav.contenedores == {"C", "T"}, n=len(nav.contenedores))
    K.ver("C0", "constantes", FNR.TIPOS_RELACIONADOS == ("remite_a", "condicion_de", "condiciona", "limita", "requiere",
                                                        "exceptua", "exceptua_obligacion")
          and FNR.TOPE_RELACIONADOS == 10 and FNR.CONTENEDOR_MAX_ANCLAS == 10
          and FNR.IP.TIPOS_FUERA_DE_PUNTO == ("TextoOrdenado",) and "aplica_a" not in FNR.GRUPO_DE)

    # C1 y C2: las filas, contra lo escrito a mano
    for k, esp in ESPERADO.items():
        obs = nav.relacionados(k)
        caso = "C2" if k in ("jug::10", "jug::11", "jug::9", "jug::20") else "C1" if k not in ("jug::40", "jug::90",
                                                                                            "jug::70", "jug::71") else "C3"
        K.ver(caso, f"filas {k}", obs == esp, n=len(obs))
    out1 = nav.ver_punto("jug::1")
    K.ver("C1", "texto de la sección de jug::1", out1.split("\n")[-len(SECCION_JUG_1):] == SECCION_JUG_1)
    claves1 = [f[0] for f in nav.relacionados("jug::1")]
    K.ver("C2", "fuera de jug::1", not {"jug::1", "jug::6", "jug::9", "jug::10"} & set(claves1)
          and not any(c in claves1 for c in (f"jug::{i}" for i in range(20, 31))))
    K.ver("C2", "el hub como nodo propio", [f[0] for f in nav.relacionados("jug::10")] == ["jug::2"])
    K.ver("C1", "direcciones y grupos vistos",
          {f[2] for v in ESPERADO.values() for f in v} == {"sale", "entra", "las dos"}
          and {g for v in ESPERADO.values() for f in v for g in f[1]} == {"remisión", "condición", "excepción"})

    # C3: el tope y su pie, y «ninguno»
    s40 = nav.seccion_relacionados("jug::40")
    K.ver("C3", "tope de 12", len(s40) == 12 and s40[0].startswith("Puntos relacionados (10 de 12;")
          and s40[-1] == "y 2 puntos más: ver_remisiones o vecinos_por_relacion"
          and [x.split(" | ")[0] for x in s40[1:11]] == [f"jug::{40 + i}" for i in range(1, 11)])
    s90 = nav.seccion_relacionados("jug::90")
    K.ver("C3", "diez sin pie", len(s90) == 11 and s90[0].startswith("Puntos relacionados (10 de 10;")
          and not s90[-1].startswith("y "))
    for k in ("jug::70", "jug::71", "jug::11"):
        K.ver("C3", f"ninguno {k}", nav.seccion_relacionados(k) == ["Puntos relacionados: ninguno"]
              and nav.ver_punto(k).endswith("\nPuntos relacionados: ninguno"))

    # C4: la salida anterior como prefijo exacto
    n_pref = n_tot = 0
    shas = {}
    for k in sorted(nav.puntos):
        if nav.puntos[k]["tipo"] == "to":
            continue
        for m in (1, 15, 25):
            viejo, nuevo = cand.ver_punto(k, m), nav.ver_punto(k, m)
            n_tot += 1
            ok = nuevo.startswith(viejo) and nuevo[len(viejo):] == "\n" + "\n".join(nav.seccion_relacionados(k))
            n_pref += ok
            shas[f"{k}|{m}"] = sha(nuevo)
    K.ver("C4", "prefijo exacto", n_pref == n_tot, prefijo=n_pref, de=n_tot)
    K.ver("C4", "punto que no existe y TO", all(nav.ver_punto(x) == cand.ver_punto(x) for x in ("jug::999", "jug", "")))
    K.ver("C4", "descripción de ver_punto", FN.TOOLS_NAV_POR_NOMBRE["ver_punto"] is next(
        t for t in FNC.TOOLS_NAV_CAND if t["name"] == "ver_punto"))

    # C5: el servidor
    t_rel, t_cand = SR.tools_de([1, 2, 3, 4, 5]), SC.tools_de([1, 2, 3, 4, 5])
    K.ver("C5", "diez herramientas iguales", len(t_rel) == 10 and json.dumps(t_rel, ensure_ascii=False, sort_keys=True)
          == json.dumps(t_cand, ensure_ascii=False, sort_keys=True), n=len(t_rel),
          sha256_herramientas=sha(json.dumps(t_rel, ensure_ascii=False, sort_keys=True)))
    try:
        import mcp.types as types
        mk = lambda ts: [types.Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"],  # noqa: E731
                                    _meta={"anthropic/maxResultSizeChars": SR.BASE.TOPE_CARACTERES_RESULTADO}).model_dump()
                         for t in ts]
        K.ver("C5", "herramientas de MCP iguales", mk(t_rel) == mk(t_cand))
    except ImportError:
        K.ver("C5", "herramientas de MCP iguales", False, motivo="sin el paquete mcp")
    banco = AQUI.parent
    fam = [json.loads((banco / p).read_text(encoding="utf-8"))["familias"]
           for p in ("n7/config_mcp_kg_n7_evaluado.json", "n7c/config_mcp_kg_n7c_evaluado.json")]
    K.ver("C5", "familias de N7 y N7c", fam[0] == fam[1] == [1, 2, 3, 4, 5])
    K.ver("C5", "versión", SR.VERSION_SERVIDOR == "1.0-nav-rel" and SC.VERSION_SERVIDOR == "1.0-nav-cand")

    class _Index:
        driver = drv
    cfg = {"grafo": GRAFO, "indice_puntos": str((a.trabajo / "indice_juguete").resolve()), "rrf_k": 60,
           "sha256_manifiesto_indice": sha_man, "denso": {"requerido": False}}
    nr, nc = SR.abrir_navegador(cfg, _Index()), SC.abrir_navegador(cfg, _Index())
    K.ver("C5", "abrir_navegador", type(nr) is FNR.NavegadorRel and type(nc) is FNC.NavegadorCand)
    nombres = {t["name"] for t in t_rel if "familia" in t}
    iguales = prefijo = 0
    llamadas = [("buscar_puntos", {"consulta": "punto"}), ("indice_to", {"to": TO}), ("ver_remisiones", {"punto": "jug::1"}),
                ("tipos_de_relacion", {"id": "a1"}), ("vecinos_por_relacion", {"id": "a1", "relacion": "remite_a",
                                                                              "direccion": "salientes"}),
                ("ver_descendientes", {"punto": "jug::1"})]
    for name, args in llamadas:
        iguales += SR.despachar(nr, _Index(), nombres, name, args) == SC.despachar(nc, _Index(), nombres, name, args)
    for k in ("jug::1", "jug::40", "jug::71"):
        r, c = SR.despachar(nr, _Index(), nombres, "ver_punto", {"punto": k}), SC.despachar(nc, _Index(), nombres,
                                                                                            "ver_punto", {"punto": k})
        prefijo += r.startswith(c) and len(r) > len(c)
    K.ver("C5", "despachar: las otras seis iguales", iguales == len(llamadas), iguales=iguales, de=len(llamadas))
    K.ver("C5", "despachar: ver_punto con la salida de N7 como prefijo", prefijo == 3, prefijo=prefijo)

    out = {"unidad": "N7c, C1: selftest_familias_nav_rel.py", "casos": K.res, "fallos": K.fallos,
           "consultas_del_doble": dict(sorted(drv.consultas.items())), "sha256_salidas_ver_punto": shas,
           "sha256_modulos": {p: IP.sha256_file(AQUI / p) for p in ("familias_nav_rel.py", "servidor_mcp_kg_nav_rel.py",
                                                                    "familias_nav_cand.py", "familias_nav.py",
                                                                    "servidor_mcp_kg_nav_cand.py")}}
    a.salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_ok = sum(v["ok"] for c in K.res.values() for v in c.values())
    n = sum(len(c) for c in K.res.values())
    print(f"selftest_familias_nav_rel: {n_ok} de {n} en verde; fallos: {K.fallos or 'ninguno'}")
    return 0 if not K.fallos else 1


if __name__ == "__main__":
    raise SystemExit(main())
