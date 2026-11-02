#!/usr/bin/env python3
"""selftest_familias_nav_rel_amp.py — N7c+, etapa C2-bis: las pruebas de NavegadorRelAmp (familias_nav_rel_amp.py) y de
su servidor (servidor_mcp_kg_nav_rel_amp.py), con un grafo de juguete y un doble del driver, sin Neo4j, sin el denso y
sin modelo de lenguaje (USD 0). El índice por punto de juguete se escribe en <trabajo> con el formato y los sha256 que
controla el constructor de familias_nav.Navegador; el doble responde las consultas que hacen el constructor y las
herramientas, y cualquier otra la hace fallar.

El árbol de juguete (TO `jug`, archivo `juguete.pdf`): las secciones S1, S2, S3, S9 y SA cuelgan del TO; S1 tiene 1, 2 y 3,
con 1.1 › 1.1.1, 1.2 › 1.2.1, 2.1 › 2.1.1, 2.2 y 3.1; S2 tiene 4 › 4.1 › 4.1.1; S3 tiene 5 a 18; S9 tiene 90 (el hub y su
relleno) y SA tiene 20. Las aristas de la sección de N7c: 1.1 → 2.2, 1 → 3 y 5 → 6 a 17 (doce).

Casos:
  F1  la raíz de la familia: el abuelo (1.1 y 1.1.1, tres niveles), el padre cuando el abuelo es el TO (1, dos niveles) y
      ninguna cuando el padre es el TO (las cinco secciones);
  F2  cada exclusión: el punto, sus ancestros, sus hijos y los que la sección de N7c lista dentro de su tope (2.2 para
      1.1, 3 para 1, 6 a 7 y 10 a 17 para 5), y los que la sección deja fuera del tope sí entran (8 y 9 para 5);
  F3  el orden (por pasos y después por la clave) y los parentescos (hermano, sobrino, tío, primo y «a 5 pasos»),
      renglón por renglón contra lo escrito a mano;
  F4  el tope y su pie (18: 13 de la familia, 10 renglones y «y 3 puntos más»); «ninguno» (4, 4.1, las secciones);
  F5  la línea de la cita: el texto exacto para un punto y para una sección; leída por scripts/ucita2_indicadores_banco.py
      (sin editarlo, por n7c/lector_cita_n7c_amp.py con un Python 3.12) da el TO y el punto que el mismo instrumento le
      da a la clave, con el documento en la forma «PDF», y es fundada (`_cita_fiel` del harness) contra lo que el
      lector del instrumento ve en la misma salida; una línea con el id del TO en lugar del PDF no pasa la forma «PDF»;
  F6  el prefijo exacto: en todos los puntos, con max_nodos 1, 15 y 25, la salida de N7c+ es la de N7c, un salto de
      línea, la familia y la cita; un punto que no existe y un TO dan la salida de N7c sin nada más;
  F7  el servidor: tools_de([1..5]) de servidor_mcp_kg_nav_rel_amp, de servidor_mcp_kg_nav_rel y de
      servidor_mcp_kg_nav_cand (el de N7) dan las mismas diez herramientas, con las mismas descripciones y esquemas (y las
      mismas herramientas de MCP); las familias de las configs de N7, N7c y N7c+, iguales; la versión; abrir_navegador da
      un NavegadorRelAmp; despachar da lo mismo que el de N7c en las otras seis herramientas de las familias y, en
      ver_punto, la salida de N7c como prefijo exacto.
Imprime y escribe solo cuentas, booleanos y sha256: sin rutas ni horas, así dos corridas dan el mismo archivo.
Uso (con el python del .venv del repo, desde una copia, nunca del repo):
  python -B data/experiment/banco_mcp/mcp_kg/selftest_familias_nav_rel_amp.py --trabajo <carpeta nueva> --salida <json>
      [--python-citas <python 3.12>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
LECTOR = AQUI.parent / "n7c" / "lector_cita_n7c_amp.py"
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import familias_nav_rel_amp as FNRA  # noqa: E402
import servidor_mcp_kg_nav_cand as SC  # noqa: E402  (HEAD, sin editar: el servidor de N7)
import servidor_mcp_kg_nav_rel as SR  # noqa: E402  (N7c)
import servidor_mcp_kg_nav_rel_amp as SRA  # noqa: E402  (N7c+)

FNR, FNC, FN, IP = FNRA.FNR, FNRA.FNC, FNRA.FN, FNRA.IP
BM = FN.BM
TO, PDF = "jug", "juguete.pdf"
LABEL = "KG_Juguete_N7c_amp"
GRAFO = "KG_Acumulado_Tandas0y1yFinal_r2b_sincola"   # solo para la etiqueta de GRAFOS en abrir_navegador
KG_SHA = "0" * 64


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# El juguete                                                                  #
# --------------------------------------------------------------------------- #
# unidad -> unidad del padre (None: el TO). El orden de los hijos es el de esta lista.
PADRE = {"S1": None, "1": "S1", "1.1": "1", "1.1.1": "1.1", "1.2": "1", "1.2.1": "1.2", "2": "S1", "2.1": "2",
         "2.1.1": "2.1", "2.2": "2", "3": "S1", "3.1": "3", "S2": None, "4": "S2", "4.1": "4", "4.1.1": "4.1",
         "S3": None, **{str(i): "S3" for i in range(5, 19)}, "S9": None, "90": "S9", "SA": None, "20": "SA"}
NODOS = {f"n{u}": ("Obligacion", [u]) for u in PADRE}
NODOS |= {"H": ("Sujeto", ["90"])} | {f"r{i}": ("Sujeto", ["90"]) for i in range(1, 21)}
ARISTAS = [("n1.1", "remite_a", "n2.2"), ("n1", "condicion_de", "n3")]
ARISTAS += [("n5", "remite_a", f"n{i}") for i in range(6, 18)]
ARISTAS += [("H", "aplica_a", f"r{i}") for i in range(1, 21)]          # el grado del hub (20 > 12)


def k(u: str) -> str:
    return f"{TO}::{u}"


def titulo(u: str) -> str:
    return f"Título {u}"


# Lo esperado, escrito a mano: los renglones de la familia (sin la cabecera) y su cabecera.
FAMILIA = {
    "1.1": [("1.2", "hermano"), ("1.2.1", "sobrino"), ("2", "tío"), ("3", "tío"), ("2.1", "primo"), ("3.1", "primo"),
            ("2.1.1", "a 5 pasos")],
    "1.1.1": [("1.2", "tío"), ("1.2.1", "primo")],
    "1": [("2", "hermano"), ("2.1", "sobrino"), ("2.2", "sobrino"), ("3.1", "sobrino")],
    "2.2": [("2.1", "hermano"), ("1", "tío"), ("2.1.1", "sobrino"), ("3", "tío"), ("1.2", "primo"), ("3.1", "primo"),
            ("1.1.1", "a 5 pasos"), ("1.2.1", "a 5 pasos")],
    "5": [("18", "hermano"), ("8", "hermano"), ("9", "hermano")],
    "4": [], "4.1": [], "4.1.1": [], "20": [], "90": [],
    "S1": [], "S2": [], "S3": [], "S9": [], "SA": [],
}
FAMILIA_18 = [str(i) for i in range(10, 18)] + ["5", "6"]
CITA = {"1.1": f"Para citar este punto: {PDF} | Punto 1.1", "S1": f"Para citar este punto: {PDF} | Sección 1",
        "SA": f"Para citar este punto: {PDF} | Sección A"}


def indice_juguete(dirp: Path) -> str:
    """Escribe el índice por punto de juguete y devuelve el sha256 de su manifiesto."""
    puntos = {TO: {"bloques": [], "clave": TO, "en_estructura": True, "herencia": [], "hijos": [], "intro": False,
                   "nodos": [], "padre": None, "pagina": None, "paginas": [], "textos": [], "tipo": "to",
                   "titulo": "Juguete", "to": TO, "unidad": None}}
    for u, pu in PADRE.items():
        puntos[k(u)] = {"bloques": [], "clave": k(u), "en_estructura": True, "herencia": [], "hijos": [], "intro": False,
                        "nodos": [], "padre": k(pu) if pu else TO, "pagina": 1, "paginas": [1],
                        "textos": [f"Texto del punto {u}."], "tipo": "seccion" if u.startswith("S") else "punto",
                        "titulo": titulo(u), "to": TO, "unidad": u}
        puntos[k(pu) if pu else TO]["hijos"].append(k(u))
    nodos = {}
    for nid, (tipo, us) in NODOS.items():
        ks = [k(u) for u in us]
        nodos[nid] = {"cola": False, "descripcion": None, "label": f"Nodo {nid}", "puntos": ks, "rol": "bloque",
                      "rol_por_punto": {}, "termino": None, "tramo": f"tramo de {nid}", "tramo_por_punto": {},
                      "type": tipo, "umbrales": None}
        for c in ks:
            puntos[c]["nodos"].append(nid)
    claves = [c for c in puntos if puntos[c]["tipo"] != "to"]
    docs = [{"id": c, "texto": f"{puntos[c]['titulo']}\n{puntos[c]['textos'][0]}"} for c in claves]
    archivos = {"puntos.json": IP.serializar(puntos), "nodos.json": IP.serializar(nodos),
                "documentos.json": IP.serializar(docs), "indice_bm25.json": BM.serializar(BM.construir(docs))}
    dirp.mkdir(parents=True)
    for n, b in archivos.items():
        (dirp / n).write_bytes(b)
    man = {"formato": "indice_puntos_nav v1 (juguete de N7c+)", "grafo": LABEL, "kg_sha256": KG_SHA,
           "archivo_a_to": {PDF: TO}, "archivos": {n: IP.sha256_bytes(b) for n, b in archivos.items()}}
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

    def _anotar(self, c):
        self.consultas[c] = self.consultas.get(c, 0) + 1

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


def python_para_citas(python: str | None) -> str:
    """Un intérprete 3.12 o más nuevo para el lector de la cita (como n6/analizar_n6.python_para_citas)."""
    cand = python or (sys.executable if sys.version_info >= (3, 12) else shutil.which("python3"))
    v = subprocess.run([cand, "-I", "-c", "import sys; print(sys.version_info >= (3, 12))"], capture_output=True, text=True)
    if v.stdout.strip() != "True":
        raise SystemExit("ABORTO: el instrumento de citas necesita Python 3.12 o más nuevo")
    return cand


def renglones(u: str) -> list[str]:
    filas = FAMILIA[u]
    if not filas:
        return [FNRA.SIN_FAMILIA]
    return ([f"Puntos de la misma familia ({len(filas)} de {len(filas)}; punto | título | parentesco):"]
            + [f"{k(x)} | {titulo(x)} | {p}" for x, p in filas])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trabajo", type=Path, required=True, help="carpeta nueva para el índice de juguete")
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--python-citas", default=None, help="Python 3.12 o más nuevo para el lector de la cita")
    a = ap.parse_args()
    if a.trabajo.exists():
        raise SystemExit("ABORTO: --trabajo tiene que ser una carpeta nueva")
    idx = a.trabajo / "indice_juguete"
    sha_man = indice_juguete(idx)
    drv = DriverJuguete()
    amp = FNRA.NavegadorRelAmp(drv, LABEL, idx, sha256_manifiesto=sha_man)
    rel = FNR.NavegadorRel(drv, LABEL, idx, sha256_manifiesto=sha_man)
    K = Casos()
    K.ver("F0", "hub", amp.hubs == {"H"}, n=len(amp.hubs), umbral=amp.umbral_hub)
    K.ver("F0", "constantes", FNRA.TOPE_FAMILIA == 10 and FNR.TOPE_RELACIONADOS == 10
          and FNRA.PARENTESCOS == {(1, 1): "hermano", (1, 2): "sobrino", (2, 1): "tío", (2, 2): "primo"})

    # F1: la raíz
    K.ver("F1", "abuelo", amp.raiz_familia(k("1.1")) == (k("S1"), 3) and amp.raiz_familia(k("1.1.1")) == (k("1"), 3))
    K.ver("F1", "padre si el abuelo es el TO", amp.raiz_familia(k("1")) == (k("S1"), 2)
          and amp.raiz_familia(k("5")) == (k("S3"), 2))
    K.ver("F1", "ninguna si el padre es el TO", all(amp.raiz_familia(k(s)) is None for s in ("S1", "S2", "S3", "S9", "SA")))

    # F2 y F3: las exclusiones, el orden y los parentescos, contra lo escrito a mano
    for u in FAMILIA:
        K.ver("F3", f"renglones {u}", amp.seccion_familia(k(u)) == renglones(u))
    rel11 = [f[0] for f in amp.relacionados(k("1.1"))]
    fam11 = [f[0] for f in amp.familia(k("1.1"))]
    K.ver("F2", "el punto, sus ancestros y sus hijos", not {k("1.1"), k("1"), k("1.1.1")} & set(fam11)
          and k("1.1") in amp._descendientes(k("S1"), 3) and k("1.1.1") in amp._descendientes(k("S1"), 3))
    K.ver("F2", "la sección de N7c dentro del tope", rel11 == [k("2.2")] and k("2.2") not in fam11
          and k("3") not in [f[0] for f in amp.familia(k("1"))])
    rel5 = [f[0] for f in amp.relacionados(k("5"))]
    fam5 = [f[0] for f in amp.familia(k("5"))]
    K.ver("F2", "fuera del tope de N7c sí entra", len(rel5) == 12 and rel5[10:] == [k("8"), k("9")]
          and fam5 == [k("18"), k("8"), k("9")])
    K.ver("F3", "parentescos vistos", {p for v in FAMILIA.values() for _, p in v}
          == {"hermano", "sobrino", "tío", "primo", "a 5 pasos"})

    # F4: el tope y su pie; «ninguno»
    s18 = amp.seccion_familia(k("18"))
    K.ver("F4", "tope de 13", len(s18) == 12 and s18[0] == "Puntos de la misma familia (10 de 13; punto | título | parentesco):"
          and [x.split(" | ")[0] for x in s18[1:11]] == [k(x) for x in FAMILIA_18]
          and all(x.endswith(" | hermano") for x in s18[1:11]) and s18[-1] == "y 3 puntos más: indice_to o ver_descendientes")
    for u in ("4", "4.1", "S1", "S3"):
        K.ver("F4", f"ninguno {u}", amp.seccion_familia(k(u)) == ["Puntos de la misma familia: ninguno"])

    # F5: la línea de la cita, leída por el instrumento
    for u, linea in CITA.items():
        K.ver("F5", f"texto {u}", amp.linea_cita(k(u)) == linea and amp.ver_punto(k(u)).endswith("\n" + linea))
    casos = [{"clave": c, "salida": amp.ver_punto(c)} for c in sorted(amp.puntos) if amp.puntos[c]["tipo"] != "to"]
    malo = casos[0]["salida"].rsplit("\n", 1)[0] + "\n" + amp.linea_cita(casos[0]["clave"]).replace(PDF, TO)
    entrada = {"tos": [{"id": TO, "archivo": PDF}], "secciones": {TO: ["1", "2", "3", "9", "A"]},
               "casos": casos + [{"clave": casos[0]["clave"], "salida": malo}]}
    r = subprocess.run([python_para_citas(a.python_citas), "-I", "-B", str(LECTOR)], input=json.dumps(entrada),
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    lc = json.loads(r.stdout) if r.returncode == 0 else {"cuentas": {}, "no_dan": {}}
    n = len(casos)
    K.ver("F5", "el lector corre (Python 3.12)", r.returncode == 0)
    K.ver("F5", "el instrumento la lee como el punto mismo", lc["cuentas"].get("lee") == n + 1, lee=lc["cuentas"].get("lee"),
          de=n + 1)
    K.ver("F5", "el documento, en la forma PDF", lc["cuentas"].get("pdf") == n and lc["no_dan"].get("pdf") == [n],
          pdf=lc["cuentas"].get("pdf"), de=n)
    K.ver("F5", "fundada con lo que el lector ve en la misma salida", lc["cuentas"].get("fundada") == n + 1,
          fundada=lc["cuentas"].get("fundada"), de=n + 1)

    # F6: el prefijo exacto
    n_pref = n_tot = 0
    shas = {}
    for c in sorted(amp.puntos):
        if amp.puntos[c]["tipo"] == "to":
            continue
        for m in (1, 15, 25):
            viejo, nuevo = rel.ver_punto(c, m), amp.ver_punto(c, m)
            n_tot += 1
            n_pref += nuevo == viejo + "\n" + "\n".join(amp.seccion_familia(c) + [amp.linea_cita(c)])
            shas[f"{c}|{m}"] = sha(nuevo)
    K.ver("F6", "prefijo exacto", n_pref == n_tot, prefijo=n_pref, de=n_tot)
    K.ver("F6", "punto que no existe y TO", all(amp.ver_punto(x) == rel.ver_punto(x) for x in ("jug::999", "jug", "")))
    o11 = amp.ver_punto(k("1.1"))
    K.ver("F6", "orden: N7c, la familia, la cita",
          o11.index("Puntos relacionados") < o11.index("Puntos de la misma familia") < o11.index("Para citar este punto:"))

    # F7: el servidor
    t_amp, t_rel, t_n7 = SRA.tools_de([1, 2, 3, 4, 5]), SR.tools_de([1, 2, 3, 4, 5]), SC.tools_de([1, 2, 3, 4, 5])
    dump = lambda ts: json.dumps(ts, ensure_ascii=False, sort_keys=True)  # noqa: E731
    K.ver("F7", "diez herramientas iguales a las de N7 y N7c", len(t_amp) == 10 and dump(t_amp) == dump(t_rel) == dump(t_n7),
          n=len(t_amp), sha256_herramientas=sha(dump(t_amp)))
    K.ver("F7", "la descripción de ver_punto", next(t for t in t_amp if t["name"] == "ver_punto")
          is FN.TOOLS_NAV_POR_NOMBRE["ver_punto"])
    try:
        import mcp.types as types
        mk = lambda ts: [types.Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"],  # noqa: E731
                                    _meta={"anthropic/maxResultSizeChars": SRA.BASE.TOPE_CARACTERES_RESULTADO}).model_dump()
                         for t in ts]
        K.ver("F7", "herramientas de MCP iguales", mk(t_amp) == mk(t_rel) == mk(t_n7))
    except ImportError:
        K.ver("F7", "herramientas de MCP iguales", False, motivo="sin el paquete mcp")
    banco = AQUI.parent
    fam = [json.loads((banco / p).read_text(encoding="utf-8"))["familias"]
           for p in ("n7/config_mcp_kg_n7_evaluado.json", "n7c/config_mcp_kg_n7c_evaluado.json",
                     "n7c/config_mcp_kg_n7c_amp_evaluado.json")]
    K.ver("F7", "familias de N7, N7c y N7c+", fam[0] == fam[1] == fam[2] == [1, 2, 3, 4, 5])
    K.ver("F7", "versión", SRA.VERSION_SERVIDOR == "1.0-nav-rel-amp" and SR.VERSION_SERVIDOR == "1.0-nav-rel"
          and json.loads((banco / "n7c/config_mcp_kg_n7c_amp_evaluado.json").read_text(encoding="utf-8"))["version"]
          == "1.0-nav-rel-amp")

    class _Index:
        driver = drv
    cfg = {"grafo": GRAFO, "indice_puntos": str(idx.resolve()), "rrf_k": 60, "sha256_manifiesto_indice": sha_man,
           "denso": {"requerido": False}}
    na, nr = SRA.abrir_navegador(cfg, _Index()), SR.abrir_navegador(cfg, _Index())
    K.ver("F7", "abrir_navegador", type(na) is FNRA.NavegadorRelAmp and type(nr) is FNR.NavegadorRel)
    nombres = {t["name"] for t in t_amp if "familia" in t}
    iguales = prefijo = 0
    llamadas = [("buscar_puntos", {"consulta": "punto"}), ("indice_to", {"to": TO}), ("ver_remisiones", {"punto": "jug::5"}),
                ("tipos_de_relacion", {"id": "n5"}), ("vecinos_por_relacion", {"id": "n5", "relacion": "remite_a",
                                                                              "direccion": "salientes"}),
                ("ver_descendientes", {"punto": "jug::S1", "niveles": 3})]
    for name, args in llamadas:
        iguales += SRA.despachar(na, _Index(), nombres, name, args) == SR.despachar(nr, _Index(), nombres, name, args)
    for c in ("jug::1.1", "jug::5", "jug::18", "jug::4"):
        x = SRA.despachar(na, _Index(), nombres, "ver_punto", {"punto": c})
        y = SR.despachar(nr, _Index(), nombres, "ver_punto", {"punto": c})
        prefijo += x.startswith(y + "\n") and x.endswith(na.linea_cita(c))
    K.ver("F7", "despachar: las otras seis iguales", iguales == len(llamadas), iguales=iguales, de=len(llamadas))
    K.ver("F7", "despachar: ver_punto con la salida de N7c como prefijo", prefijo == 4, prefijo=prefijo)

    out = {"unidad": "N7c+, C2-bis: selftest_familias_nav_rel_amp.py", "casos": K.res, "fallos": K.fallos,
           "consultas_del_doble": dict(sorted(drv.consultas.items())), "sha256_salidas_ver_punto": shas,
           "sha256_modulos": {p: IP.sha256_file(AQUI / p) for p in ("familias_nav_rel_amp.py", "servidor_mcp_kg_nav_rel_amp.py",
                                                                    "familias_nav_rel.py", "familias_nav_cand.py",
                                                                    "familias_nav.py", "servidor_mcp_kg_nav_rel.py",
                                                                    "servidor_mcp_kg_nav_cand.py")}
           | {"n7c/lector_cita_n7c_amp.py": IP.sha256_file(LECTOR), "instrumento": lc.get("instrumento_sha256")}}
    a.salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n_ok = sum(v["ok"] for c in K.res.values() for v in c.values())
    n = sum(len(c) for c in K.res.values())
    print(f"selftest_familias_nav_rel_amp: {n_ok} de {n} en verde; fallos: {K.fallos or 'ninguno'}")
    return 0 if not K.fallos else 1


if __name__ == "__main__":
    raise SystemExit(main())
