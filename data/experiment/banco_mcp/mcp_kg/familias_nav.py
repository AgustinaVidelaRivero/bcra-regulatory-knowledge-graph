#!/usr/bin/env python3
"""familias_nav.py — U-NAV-DISENO, N5 (mandato firmado en c2ddf5f7, §3 y §4, N5): las herramientas de navegación de
las familias 1 a 5 del brazo del grafo, con la firma, la salida y el tamaño máximo por llamada del diseño de N2. Las
sirve servidor_mcp_kg_nav.py junto con las tres herramientas de hoy, que no cambian (servidor_mcp_kg.py, harness.TOOLS).

Las salidas son tablas de texto compactas, no JSON (§3). Cada herramienta tiene un tope de caracteres (TOPES): la
salida se arma por secciones con presupuesto y, si algo no entra, lo dice al pie con cómo pedir el resto.

| familia | herramienta | tope (caracteres) |
|---|---|---|
| 1 entrada | buscar_puntos(consulta, to=None, punto=None, termino=None, limite=8, desde=0) | 4.500 |
| 2 vista de punto | ver_punto(punto, max_nodos=15) | 5.000 más el texto propio entero (tope_ver_punto) |
| 3 cierre de remisiones | ver_remisiones(punto, direccion="ambas", saltos=1, limite=10) | 3.000 |
| 4 índice del TO | indice_to(to, desde=None, niveles=2, limite=60) | 4.000 |
| 5 vecinos selectivos | tipos_de_relacion(id) | 1.500 |
| 5 vecinos selectivos | vecinos_por_relacion(id, relacion, direccion, to=None, punto=None, limite=20, desde=0) | 3.000 |

De dónde sale cada dato:
  - el índice por punto (indice_puntos.py, con su manifiesto y sus sha256 verificados al arrancar): los puntos de la
    E0 con su árbol, sus títulos, sus páginas y su texto; los nodos de cada punto con su tramo literal, su `termino` y
    sus umbrales, del kg.json sellado (la vista runtime no lleva el tramo a Neo4j); BM25 por punto y el denso;
  - Neo4j (el grafo que carga cargar_neo4j_tanda0.py, con las propiedades de arista de la decisión 6, exigidas en
    KG_Meta.props_aristas): las aristas, sus marcas, `alcance` y `destino` de las remite_a, y los grados.
Familia 1: BM25 (el analizador del brazo de fragmentos) y el denso del bake-off (harrier-oss-v1-0.6b, consultas con
`web_search_query`, en el proceso auxiliar codificador_consultas.py del venv del servidor de fragmentos), fusionados
con RRF, k = 60 (la propuesta de N2, fija antes de medir): s(p) = Σ 1 / (60 + rango_i(p)) sobre los dos rankings,
cada uno sobre todos los puntos que pasan los filtros (BM25, los de puntaje > 0); desempate por clave del punto.
`desde` (U-NAV-DESDE, como el de vecinos_por_relacion): las filas del ranking desde esa posición, con el mismo `limite`
y el mismo tope de caracteres, numeradas por su lugar en el ranking. Con `desde=0` (o sin pasarlo) la salida es la de
antes, byte a byte, salvo el pie; si `desde` pasa el largo del ranking, la salida dice que no hay más resultados. Cuando
el tope corta filas, el pie dice desde qué posición seguir (la primera fila que no entró); las filas que entran son las
mismas que con el pie de antes.
Familia 5: hub = nodo con grado (entrantes más salientes) en el 1 % más alto del grafo servido (regla de la medición 4
de N1): el umbral es el grado del nodo en la posición ⌈0,01·N⌉ en orden descendente, y es hub todo nodo con grado mayor
o igual. Se calcula al arrancar, desde Neo4j, y se verifica contra la config.
Marcas (decisión 6): una arista con `no_verificada_e3` va con «no verificada»; con la marca de la cola humana, con
«cola humana»; una aplica_a o ejecuta con `rol_fuente`, con «sujeto derivado» (si la parte B de la enmienda 6 a
L-ESQ-R2 llega a regir; hoy no rige y ninguna arista la trae). Un nodo de la cola, con «cola humana». `estado_e3` y
`properties_no_definidas.copia_nota_e3` no se muestran.
"""
from __future__ import annotations

import base64
import json
import math
import os
import re
import subprocess
import threading
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import sys  # noqa: E402
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import indice_puntos as IP  # noqa: E402  (agrega mcp_vector y neo4j al path)
import bm25_fragmentos as BM  # noqa: E402

RRF_K = 60
FRACCION_HUB = 0.01
CAR_POR_TOKEN_N2 = 2.78   # caracteres por token de las salidas de herramientas, estimado en N2 (no medido acá)
TOPES = {"buscar_puntos": 4500, "ver_punto": 5000, "ver_remisiones": 3000, "indice_to": 4000,
         "tipos_de_relacion": 1500, "vecinos_por_relacion": 3000}
FAMILIA = {"buscar_puntos": 1, "ver_punto": 2, "ver_remisiones": 3, "indice_to": 4, "tipos_de_relacion": 5,
           "vecinos_por_relacion": 5}
PREDICADOS_SUJETO = ("aplica_a", "ejecuta")
# Las propiedades de arista que leen las herramientas (decisión 6), sin traer provenances_json salvo donde hace falta.
PROPS_LEIDAS = "r {.alcance, .destino, .no_verificada_e3, .cola_humana, .rol_fuente}"
ROL_CORTO = {"bloque_intro": "intro", "bloque_cierre": "cierre", "bloque_chapeau_seccion": "chapeau",
             "bloque_intersticial": "intersticial", "herencia_intro": "herencia", "herencia_cierre": "herencia",
             "herencia_encabezado": "herencia", "herencia_chapeau_seccion": "herencia",
             "herencia_intersticial": "herencia", "esqueleto": "esqueleto"}
# U-NAV-DESDE: cómo explica `desde` la descripción de buscar_puntos; el mismo texto que el de buscar_pasajes
# (mcp_vector/servidor_mcp_vector.py, TEXTO_DESDE).
TEXTO_DESDE = ("desde: posición del ranking desde la que se listan los resultados (0 = los primeros). "
               "Sirve para ver los que no entraron.")
# El pie de buscar_puntos cuando el tope corta filas: k es la primera posición que no entró (desde + filas mostradas).
PIE_BUSCAR_PUNTOS = "({n} puntos más no entran en el tope: pedí desde={k}, o bajá limite o filtrá)"

TOOLS_NAV = [
    {"name": "buscar_puntos", "familia": 1,
     "description": ("Búsqueda híbrida (léxica BM25 + semántica) de puntos de los Textos Ordenados, sobre el texto de "
                     "cada punto y la descripción, el término definido y el tramo literal de sus nodos. Devuelve una "
                     "tabla de puntos con su título, el fragmento que coincide y hasta 3 de sus nodos (tipo · id). "
                     "Filtros opcionales: to (id del TO, p. ej. «ext»), punto (un punto y sus subpuntos, p. ej. «6.5» "
                     "o «cla::6.5») y termino (solo puntos con un nodo de ese término definido)."),
     "input_schema": {"type": "object", "properties": {
         "consulta": {"type": "string", "description": "Consulta en lenguaje natural."},
         "to": {"type": "string", "description": "Id del Texto Ordenado (opcional)."},
         "punto": {"type": "string", "description": "Punto, con sus subpuntos (opcional)."},
         "termino": {"type": "string", "description": "Término definido (opcional)."},
         "limite": {"type": "integer", "description": "Máximo de puntos, de 1 a 10 (def. 8)."},
         "desde": {"type": "integer", "description": "Posición desde la que se lista (def. 0)."}},
         "required": ["consulta"]}},
    {"name": "ver_punto", "familia": 2,
     "description": ("Lee un punto entero en una sola llamada: los títulos de sus ancestros, su título, su texto "
                     "entero, sus nodos (tipo, id, label, tramo literal y umbrales), las relaciones "
                     "entre esos nodos con sus marcas y sus hijos con su cantidad de nodos. punto: «to::unidad», p. ej. "
                     "«ext::5.13»; «::intro» y las partes se leen con el punto."),
     "input_schema": {"type": "object", "properties": {
         "punto": {"type": "string", "description": "Punto «to::unidad»."},
         "max_nodos": {"type": "integer", "description": "Máximo de nodos listados, de 1 a 25 (def. 15)."}},
         "required": ["punto"]}},
    {"name": "ver_remisiones", "familia": 3,
     "description": ("Las remisiones de un punto, resueltas y agrupadas por punto (no por arista): los puntos que cita "
                     "y los que lo citan, cada uno con su título, el comienzo de su texto, cuántos nodos tiene, el "
                     "alcance de la cita y el salto (1 o 2)."),
     "input_schema": {"type": "object", "properties": {
         "punto": {"type": "string", "description": "Punto «to::unidad»."},
         "direccion": {"type": "string", "description": "«cita», «lo_citan» o «ambas» (def. «ambas»)."},
         "saltos": {"type": "integer", "description": "1 o 2 (def. 1)."},
         "limite": {"type": "integer", "description": "Máximo de puntos por dirección, de 1 a 20 (def. 10)."}},
         "required": ["punto"]}},
    {"name": "indice_to", "familia": 4,
     "description": ("El árbol de puntos de un Texto Ordenado, una línea por punto con su título y su cantidad de "
                     "nodos propios; marca los puntos sin nodos propios y los que tienen bloque de introducción. Con "
                     "desde, el subárbol de ese punto."),
     "input_schema": {"type": "object", "properties": {
         "to": {"type": "string", "description": "Id del Texto Ordenado."},
         "desde": {"type": "string", "description": "Punto desde el que se baja (opcional)."},
         "niveles": {"type": "integer", "description": "Niveles, de 1 a 3 (def. 2)."},
         "limite": {"type": "integer", "description": "Máximo de líneas, de 1 a 150 (def. 60)."}},
         "required": ["to"]}},
    {"name": "tipos_de_relacion", "familia": 5,
     "description": ("Los tipos de relación de un nodo con su cuenta, por dirección y por tipo de vecino. Indica si el "
                     "nodo es un hub (grado en el 1 % más alto del grafo) y, si lo es, la cuenta por TO del vecino."),
     "input_schema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "Id exacto del nodo."}}, "required": ["id"]}},
    {"name": "vecinos_por_relacion", "familia": 5,
     "description": ("Los vecinos de un nodo por una sola relación y una dirección, con su tipo, label, punto y la "
                     "marca de la arista. Paginado con desde. En un hub, sin filtro de to o de punto no lista: "
                     "devuelve la cuenta e indica filtrar."),
     "input_schema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "Id exacto del nodo."},
         "relacion": {"type": "string", "description": "Tipo de relación (ver tipos_de_relacion)."},
         "direccion": {"type": "string", "description": "«salientes» o «entrantes»."},
         "to": {"type": "string", "description": "Solo vecinos de ese TO (opcional)."},
         "punto": {"type": "string", "description": "Solo vecinos de ese punto o sus subpuntos (opcional)."},
         "limite": {"type": "integer", "description": "Máximo de vecinos, de 1 a 40 (def. 20)."},
         "desde": {"type": "integer", "description": "Posición desde la que se lista (def. 0)."}},
         "required": ["id", "relacion", "direccion"]}},
]
TOOLS_NAV_POR_NOMBRE = {t["name"]: t for t in TOOLS_NAV}
TOOLS_NAV_POR_NOMBRE["buscar_puntos"]["description"] += " " + TEXTO_DESDE   # U-NAV-DESDE: `desde`, al final


# --------------------------------------------------------------------------- #
# Formato                                                                      #
# --------------------------------------------------------------------------- #
def _celda(x, n: int) -> str:
    s = " ".join(str(x if x is not None else "").split()).replace("|", "¦")
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _entero(v, defecto: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(v), hi))
    except (TypeError, ValueError):
        return defecto


def _texto(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _seccion(lineas: list[str], presupuesto: int, pie: str) -> tuple[list[str], int]:
    """Las líneas que entran en el presupuesto (cada una con su salto de línea) y, si se recorta, el pie con {n} = las
    que no entraron. Devuelve (líneas, caracteres usados)."""
    out, usado = [], 0
    for i, l in enumerate(lineas):
        resto = len(lineas) - i - 1
        reserva = len(pie.format(n=len(lineas) - i)) + 1 if resto else 0
        if usado + len(l) + 1 + reserva > presupuesto:
            p = pie.format(n=len(lineas) - i)
            if usado + len(p) + 1 <= presupuesto:
                out.append(p)
                usado += len(p) + 1
            return out, usado
        out.append(l)
        usado += len(l) + 1
    return out, usado


def _n_nodos(n: int) -> str:
    return "1 nodo" if n == 1 else f"{n} nodos"


def tokens_estimados(texto: str) -> int:
    return round(len(texto) / CAR_POR_TOKEN_N2)


def _lineas_texto(texto: str) -> list[str]:
    """La sección del texto de ver_punto (U-VERPUNTO, D-1 y D-2): la cabecera y el texto propio entero, con sus saltos
    de línea, sin juntarlo ni cortarlo."""
    return [f"Texto ({len(texto)} caracteres):", texto]


def _lineas_texto_cortado(texto: str) -> list[str]:
    """La sección del texto como la daba ver_punto antes de U-VERPUNTO: el texto de más de 1.500 caracteres, juntado
    en una línea y cortado en 1.499 más «…», con «, cortado en 1.500» en la cabecera. Solo para tope_ver_punto."""
    largo = len(texto) > 1500
    t = " ".join(texto.split()) if largo else texto
    return [f"Texto ({len(texto)} caracteres{', cortado en 1.500' if largo else ''}):",
            t if len(t) <= 1500 else t[:1499].rstrip() + "…"]


def tope_ver_punto(texto: str) -> int:
    """El tope de ver_punto para un punto con ese texto propio (U-VERPUNTO, D-1): TOPES["ver_punto"] más lo que la
    sección del texto entero usa de más que la cortada. Así a los nodos, las relaciones y los hijos les queda el mismo
    presupuesto que con el texto cortado, carácter por carácter, y el corte final cae en el mismo lugar de esas
    secciones. Sin texto, o con 1.500 caracteres o menos, es TOPES["ver_punto"]."""
    if not texto:
        return TOPES["ver_punto"]
    usado = lambda lineas: sum(len(x) + 1 for x in lineas)  # noqa: E731  (como `usado` en ver_punto)
    return TOPES["ver_punto"] + usado(_lineas_texto(texto)) - usado(_lineas_texto_cortado(texto))


def marcas_arista(rel: str, p: dict) -> list[str]:
    m = []
    if p.get("no_verificada_e3") in (True, "true", "True"):
        m.append("no verificada")
    if str(p.get("cola_humana")).lower() == "true":
        m.append("cola humana")
    if p.get("rol_fuente") and rel in PREDICADOS_SUJETO:
        m.append("sujeto derivado")
    return m


# --------------------------------------------------------------------------- #
# Denso (proceso auxiliar)                                                     #
# --------------------------------------------------------------------------- #
class Denso:
    """La matriz de los documentos (verificada por sha256 contra el manifiesto) y el codificador de consultas, que se
    lanza al crear el objeto y carga el modelo en segundo plano; la primera consulta espera a que esté listo."""

    def __init__(self, indice_dir: Path, man: dict, python_vector: str):
        import numpy as np
        self.np = np
        den = man["denso"]
        self.E = np.load(indice_dir / "embeddings_docs.npy")
        sha_m = IP.sha256_bytes(self.E.astype("float32").tobytes(order="C"))
        if sha_m != den["sha256_matriz"] or IP.sha256_file(indice_dir / "embeddings_docs.npy") != den["sha256_archivo_npy"]:
            raise SystemExit("ABORTO: la matriz densa del índice por punto no es la del manifiesto")
        if list(self.E.shape) != den["shape"] or den["sha256_documentos"] != man["archivos"]["documentos.json"]:
            raise SystemExit("ABORTO: la matriz densa no corresponde a los documentos del índice")
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
        self.proc = subprocess.Popen([python_vector, "-B", str(AQUI / "codificador_consultas.py"),
                                      str(indice_dir / "manifiesto.json")], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
        self.listo = None
        self.lock = threading.Lock()
        self.dim = den["dim"]

    def _leer(self) -> dict:
        linea = self.proc.stdout.readline()
        if not linea:
            raise RuntimeError("el codificador de consultas terminó sin responder")
        return json.loads(linea)

    def puntajes(self, consulta: str):
        with self.lock:
            if self.listo is None:
                self.listo = self._leer()
            if "error" in self.listo:
                raise RuntimeError(f"codificador de consultas: {self.listo['error']}")
            self.proc.stdin.write(json.dumps({"consulta": consulta}, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            r = self._leer()
        if "error" in r:
            raise RuntimeError(f"codificador de consultas: {r['error']}")
        q = self.np.frombuffer(base64.b64decode(r["v"]), dtype="float32")
        if q.shape != (self.dim,) or not self.np.isfinite(q).all():
            raise RuntimeError("codificador de consultas: vector no finito o de otra dimensión")
        # numpy 2.x con el BLAS de macOS (Accelerate) levanta avisos de división por cero, overflow e inválido en este
        # matmul aunque el resultado sea correcto (medido en N5: la diferencia con el producto en float64 es < 1e-7 y el
        # orden, el mismo); se silencian solo acá y se verifica que los puntajes sean finitos.
        with self.np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            S = self.E @ q
        if not self.np.isfinite(S).all():
            raise RuntimeError("puntajes densos no finitos")
        return S

    def cerrar(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.terminate()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Navegador                                                                    #
# --------------------------------------------------------------------------- #
class Navegador:
    """Las seis herramientas de las familias 1 a 5 sobre un grafo cargado en Neo4j y su índice por punto."""

    def __init__(self, driver, label: str, indice_dir: Path, sha256_manifiesto: str | None = None,
                 python_vector: str | None = None, hubs_esperados: dict | None = None):
        self.driver, self.label, self.dir = driver, label, Path(indice_dir)
        man_p = self.dir / "manifiesto.json"
        if sha256_manifiesto is not None and IP.sha256_file(man_p) != sha256_manifiesto:
            raise SystemExit(f"ABORTO: sha256 de {man_p.name} != el de la config")
        self.man = json.loads(man_p.read_text(encoding="utf-8"))
        for nombre in IP.ARCHIVOS:
            if IP.sha256_file(self.dir / nombre) != self.man["archivos"][nombre]:
                raise SystemExit(f"ABORTO: sha256 de {nombre} != el del manifiesto del índice por punto")
        lee = lambda n: json.loads((self.dir / n).read_text(encoding="utf-8"))  # noqa: E731
        self.puntos, self.nodos, docs = lee("puntos.json"), lee("nodos.json"), lee("documentos.json")
        self.buscador = BM.Buscador(lee("indice_bm25.json"))
        self.ids_docs = [d["id"] for d in docs]
        self.textos_docs = [d["texto"] for d in docs]
        if self.buscador.ids != self.ids_docs:
            raise SystemExit("ABORTO: el índice BM25 y los documentos no coinciden")
        self.archivo_a_to = self.man["archivo_a_to"]
        self.tos = sorted(k for k, p in self.puntos.items() if p["tipo"] == "to")
        self.terminos = {k: [set(BM.analizar(str(self.nodos[n]["termino"]))) for n in p["nodos"]
                             if self.nodos[n].get("termino")] for k, p in self.puntos.items()}
        with self.driver.session() as s:
            meta = s.run("MATCH (m:KG_Meta {grafo: $g}) RETURN properties(m) AS p", g=label).single()
            n_neo = s.run(f"MATCH (n:`{label}`) RETURN count(n) AS c").single()["c"]
        if meta is None or "props_aristas" not in meta["p"]:
            raise SystemExit("ABORTO: el grafo no se cargó con el cargador de N5 (KG_Meta sin props_aristas)")
        if meta["p"].get("kg_sha256") != self.man["kg_sha256"] or n_neo != len(self.nodos):
            raise SystemExit("ABORTO: el grafo de Neo4j no es el del índice por punto (sha256 o cantidad de nodos)")
        self.grado, self.hubs, self.umbral_hub = self._hubs()
        if hubs_esperados:
            sha = IP.sha256_bytes("\n".join(sorted(self.hubs)).encode("utf-8"))
            obs = {"umbral": self.umbral_hub, "n": len(self.hubs), "sha256": sha}
            if any(obs[k] != hubs_esperados[k] for k in hubs_esperados):
                raise SystemExit(f"ABORTO: los hubs calculados no son los esperados por la config: {obs}")
        self.denso = None
        if python_vector:
            if "denso" not in self.man:
                raise SystemExit("ABORTO: la config pide el denso y el índice por punto no lo tiene")
            self.denso = Denso(self.dir, self.man, python_vector)

    def descripcion_fuente(self) -> dict:
        return {"indice_puntos": IP.rel_repo(self.dir), "sha256_manifiesto": IP.sha256_file(self.dir / "manifiesto.json"),
                "n_puntos": len(self.ids_docs), "hubs": {"fraccion": FRACCION_HUB, "umbral": self.umbral_hub,
                                                         "n": len(self.hubs)},
                "denso": None if self.denso is None else self.man["denso"]["modelo"], "rrf_k": RRF_K}

    def _hubs(self):
        L = self.label
        with self.driver.session() as s:
            filas = s.run(f"MATCH (n:`{L}`) RETURN n.id AS id, COUNT {{ (n)-->(:`{L}`) }} AS sal, "
                          f"COUNT {{ (n)<--(:`{L}`) }} AS ent").data()
        grado = {f["id"]: f["sal"] + f["ent"] for f in filas}
        orden = sorted(grado.values(), reverse=True)
        umbral = orden[math.ceil(FRACCION_HUB * len(orden)) - 1] if orden else 0
        return grado, {i for i, g in grado.items() if g >= umbral}, umbral

    # ------------------------------------------------------------------ #
    def resolver_to(self, to) -> str | None:
        t = _texto(to).lower()
        return t if t in self.puntos and self.puntos[t]["tipo"] == "to" else None

    def resolver_punto(self, punto, to=None) -> str | None:
        s = _texto(punto)
        if not s:
            return None
        s = re.sub(r"\s*::\s*", "::", s)
        s = re.sub(r"(?i)\b(punto|secci[oó]n)\s+", lambda m: "S" if m.group(1).lower().startswith("secc") else "", s)
        if "::" not in s and to:
            s = f"{_texto(to).lower()}::{s}"
        to_p, _, resto = s.partition("::")
        s = IP.base_punto(f"{to_p.lower()}::{resto}") if resto else s
        s = re.sub(r"\.+$", "", s)
        s = re.sub(r"\.(::|$)", r"\1", s)
        p = self.puntos.get(s)
        return s if p is not None and p["tipo"] != "to" else None

    def _subarbol(self, clave: str) -> set:
        out, pila = set(), [clave]
        while pila:
            k = pila.pop()
            out.add(k)
            pila.extend(self.puntos[k]["hijos"])
        return out

    def _punto_de(self, nid: str) -> str:
        nd = self.nodos.get(nid) or {}
        return (nd.get("puntos") or ["—"])[0]

    def _to_de(self, nid: str) -> str:
        return self._punto_de(nid).split("::", 1)[0]

    def _ancestros(self, clave: str) -> list[str]:
        return IP.ancestros(self.puntos, clave)

    def _texto_propio(self, clave: str) -> str:
        return "\n".join(t for t in self.puntos[clave]["textos"] if t.strip())

    def _comienzo(self, clave: str, n: int) -> str:
        p = self.puntos.get(clave)
        if p is None:
            return ""
        return _celda(self._texto_propio(clave) or p["titulo"], n)

    def _punto_de_prov(self, provs_json: str | None) -> str | None:
        try:
            pv = (json.loads(provs_json or "[]") or [{}])[0]
        except (TypeError, ValueError):
            return None
        to = self.archivo_a_to.get(pv.get("source_doc"))
        loc = str(pv.get("location") or "")
        if not to or not loc:
            return None
        u = ("S" + loc[len("Sección "):]) if loc.startswith("Sección ") else loc[len("Punto "):] if loc.startswith("Punto ") else loc
        return IP.base_punto(f"{to}::{u}")

    # ================================================================== #
    # Familia 1                                                           #
    # ================================================================== #
    def _fragmento(self, clave: str, terminos: set, n: int = 200) -> str:
        p = self.puntos[clave]
        fuentes = [self._texto_propio(clave)] + [str(x) for nid in p["nodos"] for x in
                                                 (self.nodos[nid]["descripcion"], self.nodos[nid]["tramo_por_punto"].get(clave)) if x]
        mejor = None
        for txt in fuentes:
            pal = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\w+", txt)]
            if not pal:
                continue
            marcas = [1 if (w := BM.minusculas(t)) not in BM.STOP and BM.stem(w) in terminos else 0 for *_, t in pal]
            W = 28
            sumas = [sum(marcas[i:i + W]) for i in range(max(1, len(pal) - W + 1))]
            i = max(range(len(sumas)), key=lambda j: (sumas[j], -j))
            if mejor is None or sumas[i] > mejor[0]:
                mejor = (sumas[i], txt, pal, i, W)
            if sumas[i] and txt is fuentes[0]:
                break
        if mejor is None:
            return _celda(p["titulo"], n)
        _, txt, pal, i, W = mejor
        ini, fin = pal[i][0], pal[min(i + W, len(pal)) - 1][1]
        frag = " ".join(txt[ini:fin].split())
        pre = "…" if ini > 0 else ""
        suf = "…" if fin < len(txt) else ""
        if len(pre) + len(frag) + len(suf) > n:
            frag = frag[: n - len(pre) - 1].rsplit(" ", 1)[0]
            suf = "…"
        return (pre + frag + suf).replace("|", "¦")

    def _nodos_de_fila(self, clave: str, terminos: set) -> str:
        ids = self.puntos[clave]["nodos"]
        if not ids:
            return "—"

        def puntaje(nid):
            nd = self.nodos[nid]
            t = " ".join(str(x) for x in (nd["label"], nd["descripcion"], nd["termino"], nd["tramo_por_punto"].get(clave)) if x)
            return len(set(BM.analizar(t)) & terminos)
        orden = sorted(range(len(ids)), key=lambda i: (-puntaje(ids[i]), i))[:3]
        s = "; ".join(f"{self.nodos[ids[i]]['type']} · {ids[i]}" for i in orden)
        return s + (f"; +{len(ids) - 3} más" if len(ids) > 3 else "")

    def buscar_puntos(self, consulta, to=None, punto=None, termino=None, limite=8, desde=0) -> str:
        tope = TOPES["buscar_puntos"]
        consulta = consulta if isinstance(consulta, str) else ""
        limite, desde = _entero(limite, 8, 1, 10), _entero(desde, 0, 0, 10 ** 9)
        filtros = []
        cand = range(len(self.ids_docs))
        if _texto(to):
            t = self.resolver_to(to)
            if t is None:
                return _celda(f"buscar_puntos: no existe el TO «{to}». TOs: {', '.join(self.tos)}", tope)
            cand = [i for i in cand if self.ids_docs[i].split("::", 1)[0] == t]
            filtros.append(f"to={t}")
        if _texto(punto):
            k = self.resolver_punto(punto, to=self.resolver_to(to))
            if k is None:
                return _celda(f"buscar_puntos: no existe el punto «{punto}». Usá «to::unidad» (p. ej. «ext::5.13») "
                              "o indice_to.", tope)
            sub = self._subarbol(k)
            cand = [i for i in cand if self.ids_docs[i] in sub]
            filtros.append(f"punto={k}")
        if _texto(termino):
            q_t = set(BM.analizar(termino))
            cand = [i for i in cand if q_t and any(q_t <= s for s in self.terminos.get(self.ids_docs[i], []))]
            filtros.append(f"termino={_celda(termino, 40)}")
        cand = list(cand)
        terminos = set(BM.analizar(consulta))
        bm = self.buscador.puntajes(BM.analizar(consulta)) if terminos else {}
        rank_bm = sorted((i for i in cand if bm.get(i, 0) > 0), key=lambda i: (-bm[i], self.ids_docs[i]))
        rank_de = []
        if self.denso is not None and consulta.strip() and cand:
            S = self.denso.puntajes(consulta)
            rank_de = sorted(cand, key=lambda i: (-float(S[i]), self.ids_docs[i]))
        rrf = {}
        for rank in (rank_bm, rank_de):
            for r, i in enumerate(rank, 1):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (RRF_K + r)
        top = sorted(rrf, key=lambda i: (-rrf[i], self.ids_docs[i]))[desde:desde + limite]
        if desde:
            filtros.append(f"desde={desde}")
        modo = "fusión RRF (k=60) de BM25 y denso" if self.denso is not None else "BM25 (sin denso)"
        cab = [f"buscar_puntos «{_celda(consulta, 80)}»{(' ' + ' '.join(filtros)) if filtros else ''} · "
               f"candidatos: {len(cand)} · con coincidencia léxica: {len(rank_bm)} · {modo}"]
        if not top:
            cab.append(f"No hay más resultados: el ranking tiene {len(rrf)} puntos (desde={desde})." if desde else
                       "Sin resultados. Probá otra consulta, sacá filtros o usá indice_to.")
            return "\n".join(cab)
        cab.append("# | punto | título | fragmento | nodos")
        filas = [f"{r} | {self.ids_docs[i]} | {_celda(self.puntos[self.ids_docs[i]]['titulo'], 70)} | "
                 f"{self._fragmento(self.ids_docs[i], terminos)} | {self._nodos_de_fila(self.ids_docs[i], terminos)}"
                 for r, i in enumerate(top, desde + 1)]
        texto_cab = "\n".join(cab)
        cuerpo, _ = _seccion(filas, tope - len(texto_cab) - 1,
                             "({n} puntos más no entran en el tope de esta herramienta: bajá limite o filtrá)")
        # U-NAV-DESDE: el lugar del pie se reserva con el de arriba, así las filas que entran no cambian, y se emite
        # PIE_BUSCAR_PUNTOS, que dice desde dónde seguir y no es más largo mientras desde + filas < 100.000.
        mostradas = len(cuerpo) - (1 if cuerpo and cuerpo[-1] != filas[len(cuerpo) - 1] else 0)
        if mostradas < len(cuerpo):
            cuerpo[-1] = PIE_BUSCAR_PUNTOS.format(n=len(filas) - mostradas, k=desde + mostradas)
        return texto_cab + "\n" + "\n".join(cuerpo)

    # ================================================================== #
    # Familia 2                                                           #
    # ================================================================== #
    def _umbrales(self, nd: dict, n: int) -> str:
        us = nd.get("umbrales") or []
        partes = []
        for u in us:
            if not isinstance(u, dict):
                continue
            v = " ".join(str(u.get(k)) for k in ("valor", "unidad") if u.get(k) not in (None, ""))
            comp = u.get("comparacion")
            partes.append(f"{v}{f' ({comp})' if comp else ''}: «{u.get('tramo') or ''}»")
        return _celda("; ".join(partes), n) if partes else "—"

    def ver_punto(self, punto, max_nodos=15) -> str:
        tope = TOPES["ver_punto"]
        k = self.resolver_punto(punto)
        if k is None:
            t = self.resolver_to(punto)
            return _celda(f"ver_punto: no existe el punto «{punto}». Usá «to::unidad» (p. ej. «ext::5.13»)"
                          + (f"; para ver el TO entero usá indice_to(«{t}»)." if t else "; o buscalo con indice_to."),
                          tope)
        max_nodos = _entero(max_nodos, 15, 1, 25)
        p = self.puntos[k]
        archivo = next((a for a, t in self.archivo_a_to.items() if t == p["to"]), p["to"])
        pags = ", ".join(str(x) for x in (p["paginas"] or ([p["pagina"]] if p["pagina"] else []))) or "—"
        anc = " › ".join(f"{self.puntos[a]['unidad']} {_celda(self.puntos[a]['titulo'], 70)}" for a in self._ancestros(k))
        cab = [_celda(f"ver_punto {k} — {archivo} · páginas {pags}", 200),
               _celda(f"Ancestros: {anc or '—'}", 400),
               _celda(f"Título: {p['titulo'] or '—'}", 300)]
        texto = self._texto_propio(k)
        tope = tope_ver_punto(texto)   # U-VERPUNTO: crece solo por el texto que antes se cortaba
        partes = cab[:]
        if texto:
            partes += _lineas_texto(texto)
        else:
            partes.append("Texto: — (el punto no tiene texto propio; mirá sus hijos)")
        usado = sum(len(x) + 1 for x in partes)
        ids = p["nodos"]
        listados = ids[:max_nodos]
        num = {nid: i for i, nid in enumerate(listados, 1)}
        filas_n = []
        for i, nid in enumerate(listados, 1):
            nd = self.nodos[nid]
            rol = ROL_CORTO.get(nd["rol_por_punto"].get(k) or nd.get("rol") or "", "")
            marca = " [cola humana]" if nd.get("cola") else ""
            filas_n.append(f"n{i} | {nd['type']}{f' ({rol})' if rol else ''} | {nid} | {_celda(nd['label'], 60)} | "
                           f"{_celda(nd['tramo_por_punto'].get(k) or nd.get('tramo') or '—', 140)} | {self._umbrales(nd, 140)}{marca}")
        rels = []
        if len(listados) > 1:
            with self.driver.session() as s:
                rels = s.run(f"MATCH (a:`{self.label}`)-[r]->(b:`{self.label}`) WHERE a.id IN $ids AND b.id IN $ids "
                             f"RETURN a.id AS a, type(r) AS rel, b.id AS b, {PROPS_LEIDAS} AS p ORDER BY r.orden",
                             ids=listados).data()
        filas_r = [f"n{num[r['a']]} —{r['rel']}→ n{num[r['b']]}"
                   + (f" [{', '.join(m)}]" if (m := marcas_arista(r["rel"], r["p"])) else "") for r in rels]
        filas_h = [f"{self.puntos[h]['unidad']} · {_celda(self.puntos[h]['titulo'], 60)} · "
                   f"{_n_nodos(len(self.puntos[h]['nodos']))}" for h in p["hijos"]]
        # Presupuesto: cada sección se lleva lo que queda, menos lo que las siguientes necesitan hasta su máximo
        # (relaciones 450 caracteres, hijos 700): así los nodos usan lo que el texto no usó.
        resto = tope - usado
        secciones = [
            (f"Nodos ({len(listados)} de {len(ids)}; # | tipo | id | label | tramo literal | umbrales):"
             if ids else "Nodos: — (sin nodos propios)", filas_n, None,
             "({n} nodos más no entran en el tope: pedí menos con max_nodos o abrilos con ver_nodo)"),
            (f"Relaciones entre los nodos listados ({min(len(filas_r), 15)} de {len(filas_r)}):" if filas_r else None,
             filas_r[:15], 450, "({n} relaciones más: usá tipos_de_relacion)"),
            (f"Hijos ({len(filas_h)}; unidad · título · nodos):" if filas_h else "Hijos: —", filas_h, 700,
             "({n} hijos más: usá indice_to)"),
        ]
        necesita = [0 if t is None else len(t) + 1 + min(sum(len(x) + 1 for x in f), m or 10 ** 9)
                    for t, f, m, _ in secciones]
        for j, (titulo, filas, maximo, pie) in enumerate(secciones):
            if titulo is None:
                continue
            partes.append(titulo)
            resto -= len(titulo) + 1
            pres = resto - sum(necesita[j + 1:])
            if maximo is not None:
                pres = min(pres, maximo)
            lineas, u = _seccion(filas, max(pres, 0), pie)
            partes += lineas
            resto -= u
        out = "\n".join(partes)
        return out if len(out) <= tope else out[: tope - 1] + "…"

    # ================================================================== #
    # Familia 3                                                           #
    # ================================================================== #
    def _remisiones(self) -> dict:
        """Todas las remite_a del grafo, leídas de Neo4j una vez (con su destino, su alcance, sus marcas y su
        procedencia) e indexadas por nodo de origen, por nodo de destino y por punto de destino."""
        if getattr(self, "_rem", None) is None:
            with self.driver.session() as s:
                filas = s.run(f"MATCH (a:`{self.label}`)-[r:remite_a]->(b:`{self.label}`) RETURN a.id AS a, b.id AS b, "
                              "r.destino AS destino, r.orden AS o, "
                              "r {.alcance, .destino, .no_verificada_e3, .cola_humana, .rol_fuente, .provenances_json} AS p "
                              "ORDER BY r.orden").data()
            rem = {"origen": {}, "target": {}, "destino": {}}
            for f in filas:
                rem["origen"].setdefault(f["a"], []).append(f)
                rem["target"].setdefault(f["b"], []).append(f)
                if f["destino"]:
                    rem["destino"].setdefault(IP.base_punto(f["destino"]), []).append(f)
            self._rem = rem
        return self._rem

    def _citas(self, k: str) -> list[dict]:
        """remite_a desde los nodos del punto k, en orden de arista."""
        rem = self._remisiones()
        return sorted((f for n in self.puntos[k]["nodos"] for f in rem["origen"].get(n, [])), key=lambda f: f["o"])

    def _lo_citan(self, k: str) -> list[dict]:
        """remite_a con destino k o hacia un nodo de k, en orden de arista, sin repetir."""
        rem = self._remisiones()
        filas = {f["o"]: f for f in rem["destino"].get(k, [])}
        for n in self.puntos[k]["nodos"]:
            for f in rem["target"].get(n, []):
                filas[f["o"]] = f
        return [filas[o] for o in sorted(filas)]

    def _agrupar(self, filas: list[dict], clave_de) -> list[tuple[str, dict]]:
        grupos = {}
        for f in filas:
            c = clave_de(f)
            if c is None:
                continue
            g = grupos.setdefault(c, {"aristas": 0, "alcance": [], "marcas": []})
            g["aristas"] += 1
            a = f["p"].get("alcance")
            if a and a not in g["alcance"]:
                g["alcance"].append(a)
            for m in marcas_arista("remite_a", f["p"]):
                if m not in g["marcas"]:
                    g["marcas"].append(m)
        return list(grupos.items())

    def ver_remisiones(self, punto, direccion="ambas", saltos=1, limite=10) -> str:
        tope = TOPES["ver_remisiones"]
        k = self.resolver_punto(punto)
        if k is None:
            return _celda(f"ver_remisiones: no existe el punto «{punto}». Usá «to::unidad» (p. ej. «ext::5.13»).", tope)
        d = _texto(direccion).lower() or "ambas"
        d = d if d in ("cita", "lo_citan", "ambas") else "ambas"
        saltos = _entero(saltos, 1, 1, 2)
        limite = _entero(limite, 10, 1, 20)
        dest = lambda f: IP.base_punto(f["destino"]) if f.get("destino") else self._punto_de(f["b"])  # noqa: E731
        origen = lambda f: self._punto_de_prov(f["p"].get("provenances_json")) or self._punto_de(f["a"])  # noqa: E731
        filas, cuentas = [], {}
        for sentido, buscar, clave_de in (("cita", self._citas, dest), ("lo_citan", self._lo_citan, origen)):
            if d not in (sentido, "ambas"):
                continue
            vistos, nivel, salida = {k}, [k], []
            n_ar = 0
            for salto in range(1, saltos + 1):
                siguiente = []
                for x in nivel:
                    crudas = buscar(x)
                    if salto == 1:
                        n_ar = len(crudas)
                    for c, g in self._agrupar(crudas, clave_de):
                        if c in vistos:
                            continue
                        vistos.add(c)
                        siguiente.append(c)
                        salida.append((salto, c, g))
                nivel = [c for c in siguiente if c in self.puntos]
            cuentas[sentido] = (sum(1 for s_, *_ in salida if s_ == 1), n_ar, len(salida))
            for salto, c, g in salida[:limite]:
                p = self.puntos.get(c)
                alc = "/".join(g["alcance"]) or "—"
                if g["marcas"]:
                    alc += f" [{', '.join(g['marcas'])}]"
                filas.append(f"{sentido} | {c} | {_celda(p['titulo'] if p else '(punto fuera del grafo)', 50)} | "
                             f"{self._comienzo(c, 140) or '—'} | {len(p['nodos']) if p else 0} | {alc} | {salto}")
            if len(salida) > limite:
                filas.append(f"({len(salida) - limite} puntos más en «{sentido}»: subí limite, hasta 20)")
        partes = [f"ver_remisiones {k} · saltos {saltos}"]
        for s_, (n1, n_ar, tot) in cuentas.items():
            partes.append(f"{s_}: {n1} puntos a 1 salto ({n_ar} aristas remite_a)"
                          + (f", {tot - n1} a 2 saltos" if saltos == 2 else ""))
        if not filas:
            partes.append("Sin remisiones resueltas en esta dirección.")
            return "\n".join(partes)
        partes.append("dir | punto | título | comienzo del texto | n nodos | alcance | salto")
        cab = "\n".join(partes)
        cuerpo, _ = _seccion(filas, tope - len(cab) - 1, "({n} filas más no entran en el tope: bajá limite o saltos)")
        return cab + "\n" + "\n".join(cuerpo)

    # ================================================================== #
    # Familia 4                                                           #
    # ================================================================== #
    def indice_to(self, to, desde=None, niveles=2, limite=60) -> str:
        tope = TOPES["indice_to"]
        t = self.resolver_to(to)
        if t is None:
            return _celda(f"indice_to: no existe el TO «{to}». TOs: {', '.join(self.tos)}", tope)
        niveles = _entero(niveles, 2, 1, 3)
        limite = _entero(limite, 60, 1, 150)
        raiz = t
        if _texto(desde):
            raiz = self.resolver_punto(desde, to=t)
            if raiz is None or self.puntos[raiz]["to"] != t:
                return _celda(f"indice_to: no existe el punto «{desde}» en «{t}».", tope)
        lineas = []

        def bajar(c, prof):
            for h in self.puntos[c]["hijos"]:
                p = self.puntos[h]
                n = len(p["nodos"])
                marca = _n_nodos(n) if n else "0 nodos propios"
                if p["intro"]:
                    marca += " · intro"
                lineas.append(f"{'  ' * prof}{p['unidad']} {_celda(p['titulo'], 70)} [{marca}]")
                if prof + 1 < niveles:
                    bajar(h, prof + 1)
        bajar(raiz, 0)
        cab = f"indice_to {t}{(' desde ' + self.puntos[raiz]['unidad']) if raiz != t else ''} · {niveles} nivel{'es' if niveles > 1 else ''} · " \
              f"{len(lineas)} puntos"
        if not lineas:
            return cab + "\nSin hijos."
        cuerpo, _ = _seccion(lineas[:limite], tope - len(cab) - 1 - 90,
                             "({n} líneas más no entran en el tope: usá desde o menos niveles)")
        if len(lineas) > limite and not cuerpo[-1].startswith("("):
            cuerpo.append(f"({len(lineas) - limite} líneas más: subí limite o usá desde)")
        return cab + "\n" + "\n".join(cuerpo)

    # ================================================================== #
    # Familia 5                                                           #
    # ================================================================== #
    def _vecinos(self, nid: str, rel: str | None, sentido: str) -> list[dict]:
        L = self.label
        tipo = f":`{rel}`" if rel else ""
        patron = f"(n)-[r{tipo}]->(v:`{L}`)" if sentido == "salientes" else f"(n)<-[r{tipo}]-(v:`{L}`)"
        with self.driver.session() as s:
            return s.run(f"MATCH (n:`{L}` {{id: $id}}) MATCH {patron} RETURN type(r) AS rel, v.id AS v, "
                         f"v.type AS tipo, v.label AS label, {PROPS_LEIDAS} AS p ORDER BY r.orden", id=nid).data()

    def _existe(self, nid) -> bool:
        return isinstance(nid, str) and nid in self.grado

    def tipos_de_relacion(self, id) -> str:
        tope = TOPES["tipos_de_relacion"]
        if not self._existe(id):
            return _celda(f"tipos_de_relacion: no existe un nodo con id «{id}». Usá buscar_puntos o buscar_nodos.", tope)
        nd = self.nodos.get(id, {})
        sal, ent = self._vecinos(id, None, "salientes"), self._vecinos(id, None, "entrantes")
        es_hub = id in self.hubs
        cab = [_celda(f"tipos_de_relacion {id}", 200),
               _celda(f"Nodo: {nd.get('type')} «{nd.get('label', '')}» · punto {self._punto_de(id)} · grado "
                      f"{self.grado[id]} (salientes {len(sal)} · entrantes {len(ent)}) · hub del 1 %: "
                      f"{'sí' if es_hub else 'no'} (umbral {self.umbral_hub})", 300),
               "relación | dirección | cuenta | por tipo de vecino" + (" | por TO del vecino" if es_hub else "")]
        filas = []
        for sentido, filas_v in (("salientes", sal), ("entrantes", ent)):
            por_rel = {}
            for f in filas_v:
                por_rel.setdefault(f["rel"], []).append(f)
            for rel in sorted(por_rel):
                fs = por_rel[rel]
                tipos = Counter(f["tipo"] for f in fs).most_common()
                fila = (f"{rel} | {sentido[:-1]} | {len(fs)} | "
                        f"{_celda(', '.join(f'{t} {c}' for t, c in tipos), 60)}")
                if es_hub:
                    tos = Counter(self._to_de(f["v"]) for f in fs).most_common()
                    fila += " | " + _celda(", ".join(f"{t} {c}" for t, c in tos[:5])
                                           + (f", +{len(tos) - 5} TOs" if len(tos) > 5 else ""), 70)
                filas.append(fila)
        if not filas:
            filas = ["— | — | 0 | —"]
        texto_cab = "\n".join(cab)
        cuerpo, _ = _seccion(filas, tope - len(texto_cab) - 1, "({n} filas más no entran en el tope)")
        return texto_cab + "\n" + "\n".join(cuerpo)

    def vecinos_por_relacion(self, id, relacion, direccion, to=None, punto=None, limite=20, desde=0) -> str:
        tope = TOPES["vecinos_por_relacion"]
        if not self._existe(id):
            return _celda(f"vecinos_por_relacion: no existe un nodo con id «{id}». Usá buscar_puntos o buscar_nodos.", tope)
        d = _texto(direccion).lower()
        d = {"saliente": "salientes", "entrante": "entrantes"}.get(d, d)
        if d not in ("salientes", "entrantes"):
            return "vecinos_por_relacion: direccion tiene que ser «salientes» o «entrantes»."
        rel = _texto(relacion)
        todas = self._vecinos(id, None, d)
        rels = sorted({f["rel"] for f in todas})
        if rel not in rels:
            return _celda(f"vecinos_por_relacion: el nodo no tiene relaciones «{rel}» {d}. Las que tiene {d}: "
                          f"{', '.join(rels) or '—'} (ver tipos_de_relacion).", tope)
        filas_v = [f for f in todas if f["rel"] == rel]
        limite, desde = _entero(limite, 20, 1, 40), _entero(desde, 0, 0, 10 ** 9)
        filtros = []
        t = None
        if _texto(to):
            t = self.resolver_to(to)
            if t is None:
                return _celda(f"vecinos_por_relacion: no existe el TO «{to}». TOs: {', '.join(self.tos)}", tope)
            filas_v = [f for f in filas_v if any(x.split("::", 1)[0] == t for x in (self.nodos.get(f["v"]) or {}).get("puntos", []))]
            filtros.append(f"to={t}")
        if _texto(punto):
            k = self.resolver_punto(punto, to=t)
            if k is None:
                return _celda(f"vecinos_por_relacion: no existe el punto «{punto}».", tope)
            sub = self._subarbol(k)
            filas_v = [f for f in filas_v if set((self.nodos.get(f["v"]) or {}).get("puntos", [])) & sub]
            filtros.append(f"punto={k}")
        nd = self.nodos.get(id, {})
        cab = _celda(f"vecinos_por_relacion {id} · {rel} · {d}{(' · ' + ' '.join(filtros)) if filtros else ''} · "
                     f"{len(filas_v)} vecinos", 300)
        if id in self.hubs and not filtros:
            tos = Counter(self._to_de(f["v"]) for f in filas_v).most_common()
            return "\n".join([cab, _celda(f"Nodo muy conectado (hub del 1 %, grado {self.grado[id]}): no se listan sus "
                                          f"vecinos sin filtro. Filtrá por to o por punto. Por TO del vecino: "
                                          + ", ".join(f"{x} {c}" for x, c in tos[:12])
                                          + (f", +{len(tos) - 12} TOs" if len(tos) > 12 else ""), tope - len(cab) - 1)])
        pagina = filas_v[desde:desde + limite]
        lineas = []
        for f in pagina:
            m = marcas_arista(rel, f["p"])
            if rel == "remite_a" and f["p"].get("alcance"):
                m = [f"alcance {f['p']['alcance']}"] + m
            if (self.nodos.get(f["v"]) or {}).get("cola"):
                m.append("nodo de la cola humana")
            lineas.append(f"{f['v']} | {f['tipo']} | {_celda(f['label'], 60)} | {self._punto_de(f['v'])}"
                          + (f" | {', '.join(m)}" if m else ""))
        partes = [cab, f"vecino | tipo | label | punto | marca (de {desde} a {desde + len(pagina)} de {len(filas_v)})"]
        texto_cab = "\n".join(partes)
        pie_mas = (f"(siguen {len(filas_v) - desde - len(pagina)} vecinos: pedí desde={desde + len(pagina)})"
                   if desde + len(pagina) < len(filas_v) else "")
        cuerpo, usado = _seccion(lineas, tope - len(texto_cab) - 1 - (len(pie_mas) + 1 if pie_mas else 0),
                                 "({n} vecinos de esta página no entran en el tope: bajá limite)")
        out = texto_cab + ("\n" + "\n".join(cuerpo) if cuerpo else "\nSin vecinos con esos filtros.")
        return out + ("\n" + pie_mas if pie_mas else "")


def despachar(nav: Navegador, name: str, args: dict) -> str:
    """Despacho de las herramientas de las familias 1 a 5, sin validación de esquema (como el del harness): los
    argumentos que faltan o no son del tipo van a su valor por defecto."""
    a = args or {}
    if name == "buscar_puntos":
        return nav.buscar_puntos(a.get("consulta", ""), a.get("to"), a.get("punto"), a.get("termino"), a.get("limite", 8),
                                 a.get("desde", 0))
    if name == "ver_punto":
        return nav.ver_punto(a.get("punto", ""), a.get("max_nodos", 15))
    if name == "ver_remisiones":
        return nav.ver_remisiones(a.get("punto", ""), a.get("direccion", "ambas"), a.get("saltos", 1), a.get("limite", 10))
    if name == "indice_to":
        return nav.indice_to(a.get("to", ""), a.get("desde"), a.get("niveles", 2), a.get("limite", 60))
    if name == "tipos_de_relacion":
        return nav.tipos_de_relacion(a.get("id", ""))
    if name == "vecinos_por_relacion":
        return nav.vecinos_por_relacion(a.get("id", ""), a.get("relacion", ""), a.get("direccion", ""), a.get("to"),
                                        a.get("punto"), a.get("limite", 20), a.get("desde", 0))
    return f"herramienta desconocida: {name}"
