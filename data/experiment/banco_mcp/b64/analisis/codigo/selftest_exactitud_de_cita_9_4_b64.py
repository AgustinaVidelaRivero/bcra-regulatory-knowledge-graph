#!/usr/bin/env python3
"""selftest_exactitud_de_cita_9_4_b64.py — La prueba de exactitud_de_cita_9_4_b64.py con datos de juguete (B6.4, §9; H-6). USD 0, sin la
API, sin ningún dato real: arma en --trabajo (que no puede existir) mundos de juguete con la forma de las entradas de B6.4 (la entrada,
sus preguntas de los tres tipos con sus anclas, el estado y las sesiones de los cuatro brazos con su manifiesto, la E0 de dos TO y su
armado) y corre la exactitud de cita sobre ellos. Los valores esperados los calcula la prueba por su cuenta, con la normalización de
juguete de selftest_exactitud_de_cita_9_4_b63.py (importada sin editarla, con su sha256).

El instrumento corre de verdad en un mundo (el de HEAD, --ucita, con su sha256); en los demás lo simula la prueba, que controla lo que
recibe y escribe su salida.

Las ramas:
  - una cita que da en una unidad del ancla (también en un hermano del medio de un rango), una que no da, y una pregunta cuyas anclas no
    se pueden leer (un sufijo y un subdocumento), que sale con sus sesiones, declarada por posición, por tipo y por brazo;
  - los indicadores por brazo y por tipo, en fracción cruda, con los cuatro brazos; la columna informativa rearmada por ancla original;
  - la cita fundada de kg al lado de la de kg_n7, sin prueba ni intervalo;
  - el instrumento que no termina bien, y la corrida real del instrumento de HEAD sobre cuatro sesiones de juguete;
  - los frenos: --salida que ya existe, un instrumento que no da su sha256, una entrada con otro sha256 y un brazo que falta;
  - que no imprime nada y que dos corridas sobre el mismo mundo dan el mismo JSON, byte a byte.
La corrección del H-6, decisión 2 (las ramas d2_): con la principal y la informativa, las ramas de arriba dan lo mismo en las dos (sus
logs no traen ver_punto); y, con el código de HEAD de la copia (mcp_kg/familias_nav_rel_amp.py, con familias_nav_rel, familias_nav_cand
y familias_nav, sobre un índice por punto de juguete con la E0 de juguete y un Neo4j simulado; y mcp_vector/servidor_mcp_vector.py), cinco
salidas de juguete: una de N7c+ con las dos secciones, una con «ninguno» en cada una, una de N7c sin la línea de la cita, una de N7 sin
secciones y una de fragmentos. El recorte, contra lo que da ese mismo código sin las secciones; los literales que lee la exactitud, contra
los del código importado; y, con el instrumento de HEAD de verdad, sesiones con esas salidas en su log_r1: una cita a un punto solo
listado no es fundada en la principal y sí en la informativa, los otros brazos dan igual con y sin el recorte, y los originales no se
tocan.

Imprime solo el nombre de cada control con PASS o FAIL y el sha256 del informe (sin rutas, para que dos corridas den lo mismo).

  B64_CODIGO_B63=<b63/analisis/codigo de una copia de HEAD> python3 -I -B selftest_exactitud_de_cita_9_4_b64.py --clon <b63/v2/b2 de
      esa copia> --ucita <scripts/ucita2_indicadores_banco.py> --trabajo <carpeta nueva> --informe <json nuevo>
  (la copia trae también banco_mcp/mcp_kg, banco_mcp/mcp_vector, exploracion y evaluacion: el código de N7c+ y lo que importa)
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import exactitud_de_cita_9_4_b64 as E  # noqa: E402

B, A, D = E.B, E.A, E.D
SHA_SELFTEST_B63 = "36744c73a9d36f68771b7fb3403b5d99a7384048fd9f041bb288f1b433f9ca50"   # selftest_exactitud_de_cita_9_4_b63.py, HEAD 80085175
ARCHIVO = {"cla": "cla.pdf", "dos": "dos.pdf"}
SECCIONES = [{"tipo": "seccion", "numero": "1", "hijos": [
                 {"tipo": "punto", "numero": "1.1", "hijos": [{"tipo": "punto", "numero": f"1.1.{i}", "hijos": []} for i in (1, 2, 3)]},
                 {"tipo": "punto", "numero": "1.2", "hijos": [{"tipo": "punto", "numero": "1.2.1", "hijos": []}]}]},
             {"tipo": "seccion", "numero": "2", "hijos": [{"tipo": "punto", "numero": "2.1", "hijos": []},
                                                          {"tipo": "punto", "numero": "2.2", "hijos": []}]},
             {"tipo": "seccion", "numero": "bloque1", "hijos": []}]
# Las preguntas de juguete: su tipo, sus anclas y, por brazo, la clasificación y las citas de su única corrida (k = 1)
PREGUNTAS = {
    "JUG-C1": {"tipo": "agregacion", "anclas": ["cla::1.1.1", "cla::1.1.2", "cla::1.2"],
               "kg": ("completa", ["cla.pdf | 1.1.2"]), "kg_n7": ("completa", ["cla.pdf | 2.2"]),
               "fragmentos_hibrida": ("completa", ["cla.pdf | 1.2"]), "fragmentos_denso": ("completa", [])},
    "JUG-C2": {"tipo": "remision", "anclas": ["cla::1.1.1..1.1.3", "dos::2.1"],
               "kg": ("completa", ["cla.pdf | 1.1.2"]), "kg_n7": ("completa", ["cla.pdf | 1.1.3", "dos.pdf | 2.1"]),
               "fragmentos_hibrida": ("incompleta_otra", None), "fragmentos_denso": ("completa", ["cla.pdf | 2.2"])},
    "JUG-C3": {"tipo": "condicion_excepcion", "anclas": ["cla::1.2::intro", "cla::1.2.1"],
               "kg": ("completa", ["cla.pdf | 1.2"]), "kg_n7": ("completa", ["cla.pdf | 1.2"]),
               "fragmentos_hibrida": ("completa", ["cla.pdf | 1.2"]), "fragmentos_denso": ("completa", ["cla.pdf | 1.2"])},
    "JUG-C4": {"tipo": "condicion_excepcion", "anclas": ["dos::2.1", "dos::2.2"],
               "kg": ("completa", ["dos.pdf | 2.2"]), "kg_n7": ("completa", ["dos.pdf | 1.1"]),
               "fragmentos_hibrida": ("completa", ["dos.pdf | 2.1"]), "fragmentos_denso": ("completa", ["dos.pdf | 2.1", "dos.pdf | Punto 2.2"])},
    "JUG-C5": {"tipo": "remision", "anclas": ["dos::S1", "cla::Sbloque1"],
               "kg": ("completa", ["dos.pdf | Sección 1"]), "kg_n7": ("completa", ["dos.pdf | Sección 1", "cla.pdf | Sección bloque1"]),
               "fragmentos_hibrida": ("completa", []), "fragmentos_denso": ("completa", ["dos.pdf | 2.1"])},
    "JUG-C6": {"tipo": "agregacion", "anclas": ["dos::SD::rep1", "dos::2.1", "dos::2.2"],
               "kg": ("completa", ["dos.pdf | 2.1"]), "kg_n7": ("completa", ["dos.pdf | 2.1"]),
               "fragmentos_hibrida": ("completa", ["dos.pdf | 2.1"]), "fragmentos_denso": ("completa", ["dos.pdf | 2.1"])},
}
UNIDADES = {"JUG-C1": [["cla::1.1.1"], ["cla::1.1.2"], ["cla::1.2"]], "JUG-C2": [["cla::1.1.1", "cla::1.1.2", "cla::1.1.3"], ["dos::2.1"]],
            "JUG-C3": [["cla::1.2::intro"], ["cla::1.2.1"]], "JUG-C4": [["dos::2.1"], ["dos::2.2"]],
            "JUG-C5": [["dos::S1"], ["cla::Sbloque1"]], "JUG-C6": [["dos::SD::rep1"], ["dos::2.1"], ["dos::2.2"]]}
SALEN = ["JUG-C3", "JUG-C6"]
FUNDADA = {"kg": "si", "kg_n7": "no", "fragmentos_hibrida": "si", "fragmentos_denso": "si"}     # el indicador 1 del simulado
# La decisión 2: las preguntas del mundo del recorte, con sus citas, y las llamadas del log_r1 de cada sesión, por nombre de salida de
# juguete (salidas_de_juguete); la cita a un punto solo listado: dos::2.1 (en «Puntos relacionados») en las dos de kg
PREGUNTAS_RECORTE = {
    "JUG-R1": {"tipo": "agregacion", "anclas": ["cla::1.1.2", "dos::2.1"],
               "kg": ("completa", ["cla.pdf | 1.1.2", "dos.pdf | 2.1"]), "kg_n7": ("completa", ["cla.pdf | 1.1.2"]),
               "fragmentos_hibrida": ("completa", ["cla.pdf | 1.2"]), "fragmentos_denso": ("completa", ["cla.pdf | 1.1.3"])},
    "JUG-R2": {"tipo": "remision", "anclas": ["cla::S2", "dos::2.2"],
               "kg": ("completa", ["cla.pdf | Sección 2", "dos.pdf | 2.1"]), "kg_n7": ("completa", ["cla.pdf | 2.1"]),
               "fragmentos_hibrida": ("completa", []), "fragmentos_denso": ("completa", ["cla.pdf | 1.2"])},
}
LLAMADAS_RECORTE = {("JUG-R1", "kg"): ["n7c_mas_las_dos"], ("JUG-R1", "kg_n7"): ["n7"], ("JUG-R1", "fragmentos_hibrida"): ["fragmentos"],
                    ("JUG-R1", "fragmentos_denso"): ["fragmentos"], ("JUG-R2", "kg"): ["n7c_mas_ninguno", "n7c_sin_cita"],
                    ("JUG-R2", "kg_n7"): ["n7", "n7_seccion"], ("JUG-R2", "fragmentos_denso"): ["fragmentos"]}
FUNDADA_RECORTE = {("JUG-R1", "kg"): ("no", "si"), ("JUG-R2", "kg"): ("no", "si")}     # (principal, informativa)
# La decisión 2 de la autora del 30/10/2026, tal cual, escrita aparte del código que la declara
DECISION_2 = ("«En la exactitud de cita, un punto cuenta como visto solo si la herramienta mostró su texto. Un punto que aparece solo listado "
              "en «Puntos relacionados» o en «Puntos de la misma familia», sin su texto, no cuenta como visto. Así la cita fundada de B6.4 "
              "mide lo mismo que en B6.3. La otra cuenta, con los puntos listados como vistos, va al lado como informativa.»")


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def escribir(p: Path, contenido) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    b = contenido if isinstance(contenido, (bytes, str)) else json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    b = b.encode("utf-8") if isinstance(b, str) else b
    p.write_bytes(b)
    return sha_b(b)


def importar_selftest_b63():
    ruta = B.CODIGO_B63 / "selftest_exactitud_de_cita_9_4_b63.py"
    b = ruta.read_bytes()
    if sha_b(b) != SHA_SELFTEST_B63:
        raise SystemExit("ABORTO: selftest_exactitud_de_cita_9_4_b63.py no es el de HEAD")
    spec = importlib.util.spec_from_file_location("selftest_exactitud_de_cita_9_4_b63", ruta)
    m = importlib.util.module_from_spec(spec)
    exec(compile(b, str(ruta), "exec"), m.__dict__)  # noqa: S102
    return m


S63 = importar_selftest_b63()


# --------------------------------------------------------------------------------------------------------------------- #
# La decisión 2: las salidas de juguete, armadas con el código de HEAD de la copia                                      #
# --------------------------------------------------------------------------------------------------------------------- #
ARISTAS = [("N_cla_1_1_2", "remite_a", "N_dos_2_1", "arista_juguete_1")]      # (origen, tipo, destino, id): cla::1.1.2 remite a dos::2.1


def importar_formato(banco_mcp: Path) -> dict:
    """El código de HEAD de la copia que arma las salidas de juguete: familias_nav_rel_amp (N7c+) y, por él, familias_nav_rel (N7c),
    familias_nav_cand (N7) y familias_nav; y servidor_mcp_vector (fragmentos), con comun_banco. Antes que el instrumento, que importa
    familias_nav_cand e indice_puntos del repo."""
    for p in (str(banco_mcp / "mcp_kg"), str(banco_mcp / "mcp_vector")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import familias_nav_rel_amp as FNRA  # noqa: PLC0415
    import servidor_mcp_vector as SV  # noqa: PLC0415
    return {"FNRA": FNRA, "FNR": FNRA.FNR, "FNC": FNRA.FNC, "FN": FNRA.FN, "IP": FNRA.IP, "SV": SV, "CB": sys.modules["comun_banco"]}


def indice_de_juguete() -> tuple[dict, dict]:
    """El índice por punto de juguete, con la forma de puntos.json y nodos.json de indice_puntos, sobre la E0 de juguete (SECCIONES) de
    cla y dos: cada punto con su texto propio y un nodo propio."""
    puntos, nodos = {}, {}

    def agregar(to: str, n: dict, padre: str) -> None:
        u = f"S{n['numero']}" if n["tipo"] == "seccion" else n["numero"]
        k, nid = f"{to}::{u}", f"N_{to}_{u.replace('.', '_')}"
        puntos[k] = {"tipo": n["tipo"], "to": to, "unidad": u, "titulo": f"Título de juguete {u}", "textos": [f"Texto de juguete del punto {u}."],
                     "nodos": [nid], "hijos": [], "padre": padre, "paginas": [1], "pagina": 1}
        nodos[nid] = {"type": "Obligacion", "label": f"nodo de juguete {u}", "puntos": [k], "rol_por_punto": {}, "rol": None, "cola": False,
                      "tramo_por_punto": {k: f"tramo de juguete {u}"}, "tramo": None, "umbrales": []}
        puntos[padre]["hijos"].append(k)
        for h in n["hijos"]:
            agregar(to, h, k)

    for to in ARCHIVO:
        puntos[to] = {"tipo": "to", "to": to, "unidad": to, "titulo": f"Documento de juguete {to}", "textos": [], "nodos": [], "hijos": [],
                      "padre": None, "paginas": [], "pagina": None}
        for s in SECCIONES:
            agregar(to, s, to)
    return puntos, nodos


class DriverDeJuguete:
    """El Neo4j de juguete de las dos consultas de NavegadorRel.relacionados («sale» y «entra»), sobre ARISTAS."""

    def __init__(self, aristas: list):
        self.aristas = aristas

    def session(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def run(self, consulta: str, ids=(), tipos=(), **_):
        sale = consulta.startswith("MATCH (a:")
        filas = [{"r": e, "rel": t, "v": b if sale else a} for a, t, b, e in self.aristas if (a if sale else b) in ids and t in tipos]
        return SimpleNamespace(data=lambda: filas)


def navegadores(F: dict, puntos: dict, nodos: dict) -> dict:
    """N7c+, N7c y N7 de HEAD sobre el índice de juguete: las clases de familias_nav_rel_amp, familias_nav_rel y familias_nav_cand, con un
    Navegador de juguete debajo que solo reemplaza el __init__ de familias_nav.Navegador (que abre el índice y Neo4j); ver_punto, las
    secciones y la línea de la cita son las de HEAD."""
    class Base(F["FNC"].NavegadorCand):
        def __init__(self):  # noqa: D107
            self.puntos, self.nodos = puntos, nodos
            self.archivo_a_to = {arch: to for to, arch in ARCHIVO.items()}
            self.driver, self.label, self.hubs = DriverDeJuguete(ARISTAS), "Juguete", set()

    class N7cMas(F["FNRA"].NavegadorRelAmp, Base):
        pass

    class N7c(F["FNR"].NavegadorRel, Base):
        pass

    class N7(Base):
        pass

    return {"n7c_mas": N7cMas(), "n7c": N7c(), "n7": N7()}


def salidas_de_juguete(F: dict, nav: dict) -> dict:
    """Las salidas de juguete, por nombre: (herramienta, output_str), armadas con el código de HEAD."""
    pasaje = {"id": "cla::1.2", "to": "cla", "unidad": "1.2", "archivo": "cla.pdf", "titulo": "Título de juguete 1.2", "tipo": "punto",
              "paginas": [1], "texto": "Texto de juguete del punto 1.2."}
    fr = F["SV"]._pagina(F["SV"]._encabezado("consulta de juguete", 4, 0), [F["SV"]._fila(1, pasaje, 0.5)], 0, 1)
    return {"n7c_mas_las_dos": ("ver_punto", nav["n7c_mas"].ver_punto("cla::1.1.2")),
            "n7c_mas_ninguno": ("ver_punto", nav["n7c_mas"].ver_punto("cla::S2")),
            "n7c_sin_cita": ("ver_punto", nav["n7c"].ver_punto("cla::1.1.2")),
            "n7": ("ver_punto", nav["n7"].ver_punto("cla::1.1.2")),
            "n7_seccion": ("ver_punto", nav["n7"].ver_punto("cla::S2")),
            "fragmentos": ("buscar_pasajes", F["CB"].serializar_payload(fr))}


def esperado_de_sesion(q: str, brazo: str) -> dict:
    """La fila que daría el instrumento sobre las unidades, y la columna informativa por ancla original (la normalización de juguete
    de selftest_exactitud_de_cita_9_4_b63: citas_a_pares y da)."""
    clase, citas = PREGUNTAS[q][brazo]
    unidades = D.sin_repetir([u for anc in UNIDADES[q] for u in anc])
    if clase != "completa":
        return {"grupo": "sin_json", "ind1": "sin_json", "ind3": "sin_json", "n_con": None, "info_instrumento": "sin_json", "info_rearmada": "sin_json"}
    if not citas:
        return {"grupo": "contenido", "ind1": "sin_citas", "ind3": "sin_citas", "n_con": None, "info_instrumento": "sin_citas",
                "info_rearmada": "sin_citas"}
    pares = S63.citas_a_pares(citas)
    con = {j for j, u in enumerate(unidades) if any(S63.da(p, u) for p in pares)}
    return {"grupo": "contenido", "ind1": FUNDADA[brazo], "ind3": "si" if con else "no", "n_con": len(con),
            "info_instrumento": "si" if len(con) == len(unidades) else "no",
            "info_rearmada": "si" if all(any(S63.da(p, u) for p in pares for u in anc) for anc in UNIDADES[q]) else "no"}


def mundo(W: Path, K, qids: list, brazos: list, ucita: Path, PREGUNTAS: dict = PREGUNTAS, llamadas: dict | None = None,
          salidas: dict | None = None) -> tuple[dict, dict]:
    """Con llamadas ({(qid, brazo): [nombre de una salida de juguete]}), el log_r1 de cada sesión lleva esas llamadas, con la forma de
    comun_banco.LogR1; sin ellas, solo su evento de inicio (como en H-6)."""
    W.mkdir(parents=True)
    E0 = W / "e0"
    armado = {"e0": []}
    for to, arch in ARCHIVO.items():
        armado["e0"].append({"archivo": f"estructura_{to}.json", "to": to,
                             "sha256": escribir(E0 / f"estructura_{to}.json", {"to": to, "archivo": arch, "secciones": SECCIONES})})
    esp = {"armado_e0": escribir(W / "armado_e0_juguete.json", armado)}
    preguntas = {"preguntas": [{"id": q, "pregunta": f"Pregunta de juguete {q[-1]}", "tipo": PREGUNTAS[q]["tipo"],
                                "to": PREGUNTAS[q]["anclas"][0].split("::")[0],
                                "anclas": [{"rol": "ancla" if i == 0 else "otro_punto", "unidad": u} for i, u in enumerate(PREGUNTAS[q]["anclas"])],
                                "criterios": [{"criterio": "criterio de juguete", "cita_textual": "cita de juguete"}]} for q in qids]}
    sp = escribir(W / "preguntas_juguete.json", preguntas)
    entrada = {"preguntas": {"ruta": "preguntas_juguete.json", "sha256": sp, "ids_en_orden": qids,
                             "esquema": {"lista": "preguntas", "id": "id", "pregunta": "pregunta", "criterios": "criterios",
                                         "criterio": "criterio", "cita": "cita_textual"}},
               "k": 1, "brazos": {b: {} for b in brazos}}
    esp["entrada"] = escribir(W / "entrada_juguete.json", entrada)
    R = W / "banco_b64" / "resultados" / "real"
    st = {"bloques": {}}
    for b in K.orden_bloques(qids, 1, sorted(brazos)):
        blq = {"final": {}, "intentos_por_brazo": {}}
        for x in sorted(brazos):
            clase, citas = PREGUNTAS[b["qid"]][x]
            sid = K.id_sesion(b["qid"], b["r"], x)
            blq["final"][x] = {"clasificacion": clase, "id": sid, "intento": 1, "salida": f"pasada1/{sid}"}
            blq["intentos_por_brazo"][x] = 1
            S = R / "pasada1" / sid
            meta = {"brazo": x, "completitud_R3": {"completa": clase == "completa"}}
            if clase == "completa":
                meta["final_json_R4"] = {"respondible": True, "respuesta": f"Respuesta de juguete {b['qid'][-1]} {len(x)}", "citas": citas}
            escribir(S / f"meta_{sid}.json", meta)
            if llamadas is None:
                escribir(S / f"log_r1_{sid}.jsonl", json.dumps({"evento": "inicio"}) + "\n")
            else:
                ev = [{"evento": "inicio", "servidor": "juguete"}]
                for n, nombre in enumerate(llamadas.get((b["qid"], x), []), 1):
                    tool, s = salidas[nombre]
                    ev.append({"evento": "llamada", "call_id": f"juguete-{n}", "n": n, "tool": tool, "input": {}, "output_str": s,
                               "output_chars": len(s), "output_sha256": sha_b(s.encode("utf-8")), "error": None})
                ev.append({"evento": "fin", "n_llamadas": len(ev) - 1})
                escribir(S / f"log_r1_{sid}.jsonl", "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in ev))
            escribir(S / f"meta_sin_texto_{sid}.json", {"brazo": x})
        st["bloques"][b["bloque"]] = blq
    escribir(R / "estado_b63.json", st)
    archivos = sorted(p for p in (W / "banco_b64").rglob("*") if p.is_file())
    esp["manifiesto_fuera"] = escribir(W / "manifiesto_juguete.json", {"archivos": [{"ruta": str(p.relative_to(W)), "sha256": sha_b(p.read_bytes())}
                                                                                    for p in archivos]})
    tres = dict(entrada, brazos={b: {} for b in brazos if b != B.CUARTO})
    esp["_entrada_tres_brazos"] = escribir(W / "entrada_tres_brazos.json", tres)
    rutas = {"clon": None, "entrada": W / "entrada_juguete.json", "manifiesto_fuera": W / "manifiesto_juguete.json",
             "banco_b64": W / "banco_b64", "e0": E0, "armado_e0": W / "armado_e0_juguete.json", "ucita": ucita}
    return rutas, esp


class Simulado:
    """El instrumento simulado: controla lo que recibe y escribe su salida con las filas que da la prueba (o una fila tocada)."""

    def __init__(self, UC, codigo: int = 0, tocar: str | None = None):
        self.UC, self.codigo, self.tocar, self.recibido, self.recibidos = UC, codigo, tocar, None, []

    def __call__(self, argv):
        ses = argv[argv.index("--sesiones") + 1: argv.index("--anclas")]
        mapa = json.loads(Path(argv[argv.index("--mapa-sesiones") + 1]).read_text(encoding="utf-8"))
        anclas = json.loads(Path(argv[argv.index("--anclas") + 1]).read_text(encoding="utf-8"))
        sin_enlaces = all(not Path(s).is_symlink() and all(not p.is_symlink() for p in Path(s).iterdir()) for s in ses)
        self.recibido = {"anclas": anclas, "preguntas_del_mapa": sorted(set(mapa.values())), "sesiones": len(ses), "sin_enlaces": sin_enlaces,
                         "python": argv[0] == sys.executable and argv[1:3] == ["-I", "-B"]}
        self.recibidos.append(self.recibido)        # la corrección del H-6: la principal y la informativa
        if self.codigo != 0:
            return SimpleNamespace(returncode=self.codigo, stdout="", stderr="simulado: no termina bien\n")
        dir_de = {Path(s).name: Path(s) for s in ses}
        filas = []
        for sid, q in sorted(mapa.items()):
            brazo = json.loads((dir_de[sid] / f"meta_{sid}.json").read_text(encoding="utf-8"))["brazo"]
            x = esperado_de_sesion(q, brazo)
            f = {"sesion": sid, "pregunta": q, "brazo": brazo, "grupo": x["grupo"], "n_anclas_con_cita": x["n_con"],
                 "ind1_cita_fundada": x["ind1"], "ind2_cita_existente": "si" if x["ind3"] in ("si", "no") else x["ind3"],
                 "ind3_cita_al_ancla": x["ind3"], "info_cada_ancla_con_cita": x["info_instrumento"]}
            if self.tocar == sid:
                f["n_anclas_con_cita"] = (f["n_anclas_con_cita"] or 0) + 1
            filas.append(f)
        Path(argv[argv.index("--out-json") + 1]).write_text(json.dumps({"agregados": self.UC.agregar(filas), "filas": filas,
                                                                        "anclas_en_indice": {"resueltas": 0, "total": 0, "no_resueltas": []}},
                                                                       ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="simulado\n", stderr="")


def correr(rutas, esp, W: Path, salida: Path, clon: Path, simulado=None):
    rutas = rutas | {"clon": clon}
    esp = {k: v for k, v in esp.items() if not k.startswith("_")}
    buf, previo = io.StringIO(), os.getcwd()
    os.chdir(W)
    try:
        with contextlib.redirect_stdout(buf):
            return E.punto4(rutas, esp, salida, simulado), None, buf.getvalue()
    except A.Freno as ex:
        return None, str(ex), buf.getvalue()
    finally:
        os.chdir(previo)


def n_de(fs: list, clave: str) -> str:
    return f"{sum(x[clave] == 'si' for x in fs)} de {len(fs)}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clon", type=Path, required=True)
    ap.add_argument("--ucita", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--informe", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.trabajo.exists() or a.informe.exists():
        raise SystemExit("--trabajo y --informe no pueden existir")
    T = a.trabajo.resolve()
    T.mkdir(parents=True)
    clon = a.clon.resolve()
    AP, JB = A.importar(clon, B.ESPERADO_CODIGO)
    K = JB.K
    F = importar_formato(clon.parents[2])                   # la decisión 2: el código de N7c+ de la copia, antes que el instrumento
    UC = D.importar_instrumento(a.ucita, {"ucita": E.SHA_UCITA})
    importados = [B.CODIGO_B63 / n for n in ("analizar_b63.py", "exactitud_de_cita_9_4_b63.py", "selftest_exactitud_de_cita_9_4_b63.py")] + [a.ucita] \
        + [Path(F[m].__file__) for m in ("FNR", "FNRA")]
    antes = {p.name: sha_b(p.read_bytes()) for p in importados}
    R: dict = {}
    frenos: dict = {}

    def control(nombre, cond):
        R[nombre] = "PASS" if cond else "FAIL"

    control("importado_byte_a_byte_lo_sellado", sha_b((B.CODIGO_B63 / "exactitud_de_cita_9_4_b63.py").read_bytes()) == B.SELLADO["exactitud_de_cita_9_4_b63.py"]
            and Path(D.__file__).resolve() == (B.CODIGO_B63 / "exactitud_de_cita_9_4_b63.py").resolve() and antes[a.ucita.name] == E.SHA_UCITA
            and not any(hasattr(E, n) for n in ("rearmar", "unidades_de_las_anclas", "leible", "importar_instrumento", "exactitud_de_cita")))

    # --- El mundo de las ramas, con el instrumento simulado ----------------------------------------------------------- #
    qids, brazos = list(PREGUNTAS), list(B.BRAZOS)
    rS, eS = mundo(T / "mundo_ramas", K, qids, brazos, a.ucita)
    sim = Simulado(UC)
    oS, fS, impS = correr(rS, eS, T / "mundo_ramas", T / "salida_ramas", clon, sim)
    oS2, fS2, _ = correr(rS, eS, T / "mundo_ramas", T / "salida_ramas_bis", clon, Simulado(UC))
    control("ramas_corre_sin_freno", fS is None and fS2 is None)
    if fS is None and fS2 is None:
        bS = (T / "salida_ramas" / "exactitud_de_cita_B64.json").read_bytes()
        control("ramas_dos_corridas_iguales_byte_a_byte", bS == (T / "salida_ramas_bis" / "exactitud_de_cita_B64.json").read_bytes())
        control("ramas_no_imprime_nada", impS == "")
        R["sha256_salida_ramas"] = sha_b(bS)
        pos = {p["posicion"]: p for p in oS["anclas"]["por_posicion"]}
        control("un_rango_que_se_expande_a_sus_hermanos", pos[2]["unidades_por_ancla"] == [3, 1] and pos[2]["con_un_rango"]
                and pos[1]["unidades_por_ancla"] == [1, 1, 1])
        quedan = [q for q in qids if q not in SALEN]
        control("una_pregunta_cuyas_anclas_no_se_pueden_leer_sale_declarada",
                oS["salen"] == {"preguntas": 2, "posiciones": [3, 6], "por_tipo": {"agregacion": 1, "remision": 0, "condicion_excepcion": 1},
                                "sesiones_por_brazo": {b: 2 for b in B.BRAZOS}}
                and pos[3]["unidades_que_el_instrumento_no_lee"] == 1 and pos[6]["unidades_que_el_instrumento_no_lee"] == 1
                and oS["sesiones_que_entran"] == 16 and oS["sesiones_que_entran_por_brazo"] == {b: 4 for b in B.BRAZOS}
                and sim.recibido["preguntas_del_mapa"] == quedan and sim.recibido["sin_enlaces"] and sim.recibido["python"])
        control("el_archivo_de_anclas_lleva_las_unidades_de_todas_sus_anclas",
                sim.recibido["anclas"] == {q: D.sin_repetir([u for anc in UNIDADES[q] for u in anc]) for q in quedan})
        esperadas = {(q, b): esperado_de_sesion(q, b) for q in quedan for b in brazos}
        control("una_cita_que_da_en_una_unidad_del_ancla_y_una_que_no",
                esperadas[("JUG-C1", "kg")]["ind3"] == "si" and esperadas[("JUG-C1", "kg_n7")]["ind3"] == "no"
                and esperadas[("JUG-C2", "kg")]["ind3"] == "si" and esperadas[("JUG-C4", "kg_n7")]["ind3"] == "no"
                and oS["principal"]["indicadores"]["del_instrumento"]["por_tipo"]["agregacion"]["kg"]["todas"]["ind3_cita_al_ancla"]["si_n_de_N"] == "1 de 1"
                and oS["principal"]["indicadores"]["del_instrumento"]["por_tipo"]["agregacion"]["kg_n7"]["todas"]["ind3_cita_al_ancla"]["si_n_de_N"] == "0 de 1")
        ok = True
        I = oS["principal"]["indicadores"]
        for b in brazos:
            fs = [x for (q, bb), x in esperadas.items() if bb == b]
            ok &= I["del_instrumento"]["todas_las_preguntas"][b]["todas"]["ind3_cita_al_ancla"]["si_n_de_N"] == n_de(fs, "ind3")
            ok &= I["del_instrumento"]["todas_las_preguntas"][b]["todas"]["ind1_cita_fundada"]["si_n_de_N"] == n_de(fs, "ind1")
            ok &= I["la_columna_informativa_por_ancla_original"]["todas_las_preguntas"]["agregados"][b]["todas"]["info_cada_ancla_con_cita"]["si_n_de_N"] \
                == n_de(fs, "info_rearmada")
            for t in B.TIPOS:
                ft = [x for (q, bb), x in esperadas.items() if bb == b and PREGUNTAS[q]["tipo"] == t]
                ag = I["del_instrumento"]["por_tipo"][t].get(b)
                ok &= (ag is None and not ft) or (ag is not None and ag["todas"]["ind3_cita_al_ancla"]["si_n_de_N"] == n_de(ft, "ind3")
                                                   and ag["todas"]["N"] == len(ft))
                cr = I["la_columna_informativa_por_ancla_original"]["por_tipo"][t]
                ok &= cr["calculada"] is True and (not ft or cr["agregados"][b]["todas"]["info_cada_ancla_con_cita"]["si_n_de_N"] == n_de(ft, "info_rearmada"))
        control("los_indicadores_por_brazo_y_por_tipo_en_fraccion_cruda", ok and sorted(I["del_instrumento"]["todas_las_preguntas"]) == sorted(brazos))
        ci = I["la_columna_informativa_por_ancla_original"]["todas_las_preguntas"]
        cambian = sum(1 for (q, b), x in esperadas.items() if x["info_rearmada"] != x["info_instrumento"])
        control("la_columna_informativa_rearmada", ci["calculada"] is True and ci["control"]["sesiones"] == 16
                and ci["control"]["dan_el_indicador_3_y_las_unidades_con_cita"] == 16 and ci["control"]["cambian_por_el_rearmado"] == cambian
                and cambian >= 1)
        lado = I["la_cita_fundada_de_kg_al_lado_de_la_de_kg_n7"]
        fk = [x for (q, b), x in esperadas.items() if b == "kg"]
        fn = [x for (q, b), x in esperadas.items() if b == "kg_n7"]
        control("la_cita_fundada_de_kg_al_lado_de_la_de_kg_n7", lado["sin_prueba_ni_intervalo"] is True
                and lado["total"]["kg"]["todas"] == n_de(fk, "ind1") and lado["total"]["kg_n7"]["todas"] == n_de(fn, "ind1")
                and lado["total"]["kg"]["todas"] != lado["total"]["kg_n7"]["todas"]
                and lado["por_tipo"]["remision"]["kg"]["todas"] == "2 de 2" and lado["por_tipo"]["remision"]["kg_n7"]["todas"] == "0 de 2"
                and not any(k in json.dumps(lado) for k in ("intervalo_95", "permutacion")))
        control("d2_sin_ver_punto_en_los_logs_la_principal_y_la_informativa_dan_lo_mismo",
                oS["principal"]["indicadores"] == oS["informativa"]["indicadores"] and len(sim.recibidos) == 2
                and sim.recibidos[0] == sim.recibidos[1] and oS["principal"]["que"] == E.CUENTAS["principal"]
                and oS["informativa"]["que"] == E.CUENTAS["informativa"]
                and all(v["salidas_recortadas"] == 0 and v["sesiones"] == 4 for v in oS["recorte"]["por_brazo"].values())
                and oS["decisiones"]["lo_visto_en_la_cita_fundada"].startswith(DECISION_2))
    else:
        frenos["ramas"] = fS or fS2

    # --- Un rearmado que no reproduce al instrumento, y el instrumento que no termina bien ----------------------------- #
    r2, e2 = mundo(T / "mundo_fila_tocada", K, qids, brazos, a.ucita)
    o2, f2, _ = correr(r2, e2, T / "mundo_fila_tocada", T / "salida_fila_tocada", clon, Simulado(UC, tocar=K.id_sesion("JUG-C2", 1, "kg")))
    control("un_rearmado_que_no_reproduce_deja_la_columna_sin_calcular_para_las_de_un_rango", f2 is None
            and o2["principal"]["indicadores"]["la_columna_informativa_por_ancla_original"]["todas_las_preguntas"]["calculada"] is False
            and o2["principal"]["indicadores"]["la_columna_informativa_por_ancla_original"]["por_tipo"]["remision"]["calculada"] is False
            and o2["principal"]["indicadores"]["la_columna_informativa_por_ancla_original"]["por_tipo"]["agregacion"]["calculada"] is True)
    r3, e3 = mundo(T / "mundo_no_termina", K, qids, brazos, a.ucita)
    o3, f3, _ = correr(r3, e3, T / "mundo_no_termina", T / "salida_no_termina", clon, Simulado(UC, codigo=2))
    control("el_instrumento_que_no_termina_bien_se_declara", f3 is None
            and all(o3[c]["instrumento"]["corrio"] is False and o3[c]["instrumento"]["codigo_de_salida"] == 2
                    and "declarado" in o3[c]["indicadores"] for c in ("principal", "informativa"))
            and (T / "salida_no_termina" / "exactitud_de_cita_B64.json").is_file())

    # --- La corrida real del instrumento de HEAD, sobre cuatro sesiones ------------------------------------------------ #
    rR, eR = mundo(T / "mundo_real", K, ["JUG-C1", "JUG-C3"], brazos, a.ucita)
    oR, fR, impR = correr(rR, eR, T / "mundo_real", T / "salida_real", clon)
    if fR is None and oR["principal"]["instrumento"]["corrio"]:
        o = json.loads((T / "salida_real" / "trabajo_exactitud_de_cita" / "ucita_B63.json").read_text(encoding="utf-8"))
        fila = {f["brazo"]: f for f in o["filas"]}
        control("la_corrida_real_sobre_cuatro_sesiones_con_los_cuatro_brazos", oR["sesiones_que_entran"] == 4 and sorted(fila) == sorted(brazos)
                and oR["salen"]["posiciones"] == [2] and impR == ""
                and all(fila[b]["ind3_cita_al_ancla"] == esperado_de_sesion("JUG-C1", b)["ind3"]
                        and fila[b]["n_anclas_con_cita"] == esperado_de_sesion("JUG-C1", b)["n_con"] for b in brazos))
        control("la_corrida_real_una_cita_que_da_y_una_que_no", fila["kg"]["ind3_cita_al_ancla"] == "si" and fila["kg_n7"]["ind3_cita_al_ancla"] == "no"
                and fila["fragmentos_denso"]["ind3_cita_al_ancla"] == "sin_citas"
                and oR["principal"]["indicadores"]["del_instrumento"]["por_tipo"]["agregacion"]["kg"]["todas"]["ind3_cita_al_ancla"]["si_n_de_N"] == "1 de 1"
                and oR["principal"]["indicadores"]["la_columna_informativa_por_ancla_original"]["todas_las_preguntas"]["calculada"] is True)
    else:
        frenos["real"] = fR or f"el instrumento salió con {oR['principal']['instrumento'].get('codigo_de_salida')}"
        for n in ("la_corrida_real_sobre_cuatro_sesiones_con_los_cuatro_brazos", "la_corrida_real_una_cita_que_da_y_una_que_no"):
            control(n, False)

    # --- La corrección del H-6, decisión 2: el recorte de las dos secciones de N7c+ ----------------------------------- #
    lit = E.literales_n7c_mas(clon.parents[2] / "mcp_kg")
    control("d2_los_literales_son_los_del_codigo_de_N7c_mas_de_la_copia",
            lit == {k: getattr(F["FNR"], k) for k in ("TITULO_RELACIONADOS", "SIN_RELACIONADOS")}
            | {k: getattr(F["FNRA"], k) for k in ("TITULO_FAMILIA", "SIN_FAMILIA", "LINEA_CITA")}
            and all(sha_b(Path(F[m].__file__).read_bytes()) == E.FORMATO_N7C_MAS[n][0]
                    for m, n in (("FNR", "familias_nav_rel.py"), ("FNRA", "familias_nav_rel_amp.py")))
            and all(Path(m.__file__).resolve().is_relative_to(clon.parents[5]) for m in F.values()))
    puntos, nodos = indice_de_juguete()
    nav = navegadores(F, puntos, nodos)
    sal = salidas_de_juguete(F, nav)
    Rc = E.Recorte(lit)
    amp, k1, s2 = nav["n7c_mas"], "cla::1.1.2", "cla::S2"
    cuerpo, cuerpo_s2 = sal["n7"][1], sal["n7_seccion"][1]
    sr, sf, sr_n7c = amp.seccion_relacionados(k1), amp.seccion_familia(k1), nav["n7c"].seccion_relacionados(k1)
    esperado_recorte = {"n7c_mas_las_dos": (cuerpo + "\n" + amp.linea_cita(k1), len(sr) + len(sf)),
                        "n7c_mas_ninguno": (cuerpo_s2 + "\n" + amp.linea_cita(s2), 2), "n7c_sin_cita": (cuerpo, len(sr_n7c)),
                        "n7": (cuerpo, 0), "n7_seccion": (cuerpo_s2, 0), "fragmentos": (sal["fragmentos"][1], 0)}
    hecho = {n: Rc.salida(sal[n][1]) for n in esperado_recorte}
    control("d2_las_salidas_de_juguete_con_el_codigo_de_HEAD",
            sal["n7c_mas_las_dos"][1] == cuerpo + "\n" + "\n".join(sr) + "\n" + "\n".join(sf + [amp.linea_cita(k1)])
            and sal["n7c_mas_ninguno"][1] == cuerpo_s2 + "\n" + "\n".join([lit["SIN_RELACIONADOS"], lit["SIN_FAMILIA"], amp.linea_cita(s2)])
            and sal["n7c_sin_cita"][1] == cuerpo + "\n" + "\n".join(sr_n7c) and sr_n7c == sr and "Para citar" not in sal["n7c_sin_cita"][1]
            and len(sr) == 2 and sr[1].startswith("dos::2.1 | ") and len(sf) == 5
            and [x.split(" | ")[0] for x in sf[1:]] == ["cla::1.1.1", "cla::1.1.3", "cla::1.2", "cla::1.2.1"]
            and cuerpo.startswith("ver_punto cla::1.1.2 — cla.pdf") and cuerpo.split("\n")[3].startswith("Texto (")
            and json.loads(sal["fragmentos"][1])["resultados"][0]["unidad"] == "1.2")
    control("d2_el_recorte_en_las_cinco_salidas", hecho == esperado_recorte
            and "dos::2.1" not in hecho["n7c_mas_las_dos"][0] + hecho["n7c_sin_cita"][0] and "cla::1.1.3" not in hecho["n7c_mas_las_dos"][0])
    # con el instrumento de HEAD de verdad, sobre sesiones con esas salidas en su log_r1
    qr = list(PREGUNTAS_RECORTE)
    rC, eC = mundo(T / "mundo_recorte", K, qr, brazos, a.ucita, PREGUNTAS=PREGUNTAS_RECORTE, llamadas=LLAMADAS_RECORTE, salidas=sal)
    oC, fC, impC = correr(rC, eC, T / "mundo_recorte", T / "salida_recorte", clon)
    nombres_d2 = ("d2_una_cita_a_un_punto_solo_listado_no_es_fundada_en_la_principal_y_si_en_la_informativa",
                  "d2_los_otros_brazos_dan_igual_con_y_sin_el_recorte", "d2_el_recorte_por_brazo",
                  "d2_los_originales_no_se_tocan_y_en_las_copias_cambia_solo_ver_punto")
    if fC is None and oC["principal"]["instrumento"]["corrio"] and oC["informativa"]["instrumento"]["corrio"]:
        SP_, SI_ = T / "salida_recorte" / "trabajo_exactitud_de_cita", T / "salida_recorte" / "informativa" / "trabajo_exactitud_de_cita"
        fp = {f["sesion"]: f for f in json.loads((SP_ / "ucita_B63.json").read_text(encoding="utf-8"))["filas"]}
        fi = {f["sesion"]: f for f in json.loads((SI_ / "ucita_B63.json").read_text(encoding="utf-8"))["filas"]}
        sid = {(q, b): K.id_sesion(q, 1, b) for q in qr for b in brazos}
        otros = [s for (q, b), s in sid.items() if b != "kg"]
        ip, ii = (oC[c]["indicadores"]["del_instrumento"]["todas_las_preguntas"] for c in ("principal", "informativa"))
        control(nombres_d2[0], impC == "" and all((fp[sid[x]]["ind1_cita_fundada"], fi[sid[x]]["ind1_cita_fundada"]) == v
                                                  for x, v in FUNDADA_RECORTE.items())
                and ip["kg"]["todas"]["ind1_cita_fundada"]["si_n_de_N"] == "0 de 2" and ii["kg"]["todas"]["ind1_cita_fundada"]["si_n_de_N"] == "2 de 2"
                and oC["principal"]["indicadores"]["la_cita_fundada_de_kg_al_lado_de_la_de_kg_n7"]["total"]["kg"]["todas"] == "0 de 2"
                and oC["informativa"]["indicadores"]["la_cita_fundada_de_kg_al_lado_de_la_de_kg_n7"]["total"]["kg"]["todas"] == "2 de 2")
        control(nombres_d2[1], all(fp[s] == fi[s] for s in otros) and all(ip[b] == ii[b] for b in brazos if b != "kg")
                and fp[sid[("JUG-R1", "kg_n7")]]["ind1_cita_fundada"] == "si" and fp[sid[("JUG-R1", "fragmentos_hibrida")]]["ind1_cita_fundada"] == "si"
                and fp[sid[("JUG-R1", "fragmentos_denso")]]["ind1_cita_fundada"] == "no")
        cero = {"sesiones": 2, "llamadas_a_ver_punto": 0, "salidas_recortadas": 0, "renglones_sacados": 0}
        control(nombres_d2[2], oC["recorte"]["por_brazo"] == {
            "kg": {"sesiones": 2, "llamadas_a_ver_punto": 3, "salidas_recortadas": 3, "renglones_sacados": len(sr) + len(sf) + 2 + len(sr_n7c)},
            "kg_n7": cero | {"llamadas_a_ver_punto": 3}, "fragmentos_hibrida": cero, "fragmentos_denso": cero}
            and oC["recorte"]["literales"] == lit)

        def solo_ver_punto(orig: bytes, copia: bytes) -> bool:
            lo, lc = orig.decode("utf-8").split("\n"), copia.decode("utf-8").split("\n")
            if len(lo) != len(lc):
                return False
            for x, y in zip(lo, lc):
                if x == y:
                    continue
                jx, jy = json.loads(x), json.loads(y)
                if jx.get("tool") != "ver_punto" or Rc.salida(jx["output_str"])[0] != jy["output_str"] \
                        or {k: v for k, v in jx.items() if k != "output_str"} != {k: v for k, v in jy.items() if k != "output_str"}:
                    return False
            return True
        log = lambda base, s: (base / s / f"log_r1_{s}.jsonl").read_bytes()  # noqa: E731
        orig = {s: log(rC["banco_b64"] / "resultados" / "real" / "pasada1", s) for s in sid.values()}
        man = json.loads(rC["manifiesto_fuera"].read_text(encoding="utf-8"))
        control(nombres_d2[3], all(sha_b((T / "mundo_recorte" / x["ruta"]).read_bytes()) == x["sha256"] for x in man["archivos"])
                and all(log(SI_ / "sesiones", s) == orig[s] for s in sid.values())
                and all(log(SP_ / "sesiones", s) == orig[s] for s in otros)
                and all(log(SP_ / "sesiones", sid[x]) != orig[sid[x]] and solo_ver_punto(orig[sid[x]], log(SP_ / "sesiones", sid[x]))
                        for x in FUNDADA_RECORTE))
        # la salida del instrumento trae las rutas de su carpeta de trabajo: el registro va sin ellas (indicadores y recorte)
        R["sha256_indicadores_y_recorte"] = sha_b(json.dumps({c: oC[c]["indicadores"] for c in ("principal", "informativa")}
                                                             | {"recorte": oC["recorte"]}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    else:
        frenos["recorte"] = fC or "el instrumento no terminó bien en la principal o en la informativa"
        for n in nombres_d2:
            control(n, False)

    # --- Los frenos ---------------------------------------------------------------------------------------------------- #
    casos = {"salida_que_ya_existe": ({}, {}, T / "salida_ramas", "--salida ya existe"),
             "un_instrumento_que_no_da_su_sha256": ({"ucita": T / "mundo_ramas" / "preguntas_juguete.json"}, {}, T / "salida_ucita_otro",
                                                    "scripts/ucita2_indicadores_banco.py no da su sha256"),
             "una_entrada_con_otro_sha256": ({}, {"entrada": "0" * 64}, T / "salida_entrada_otra", "entrada no da su sha256"),
             "un_brazo_que_falta": ({"entrada": T / "mundo_ramas" / "entrada_tres_brazos.json"}, {"entrada": eS["_entrada_tres_brazos"]},
                                    T / "salida_tres_brazos", "los brazos de la entrada no son los cuatro de B6.4: falta ['kg_n7']")}
    for nombre, (cr, ce, sal, texto) in casos.items():
        existia = sal.exists()
        of, ff, imp = correr(rS | cr, eS | ce, T / "mundo_ramas", sal, clon, Simulado(UC))
        frenos[nombre] = ff
        control(f"freno_{nombre}", of is None and ff is not None and ff.startswith(texto) and imp == "" and sal.exists() == existia)

    control("nada_se_edito_en_lo_importado", {p.name: sha_b(p.read_bytes()) for p in importados} == antes)
    informe = {"que": "la prueba de exactitud_de_cita_9_4_b64.py con datos de juguete (B6.4, §9; H-6 y su corrección)",
               "codigo": {**{n: sha_b((AQUI / n).read_bytes()) for n in ("exactitud_de_cita_9_4_b64.py", "analizar_b64.py",
                                                                          "selftest_exactitud_de_cita_9_4_b64.py")},
                          **{f"importado/{k}": v for k, v in antes.items()},
                          **{f"formato/{Path(m.__file__).name}": sha_b(Path(m.__file__).read_bytes()) for m in F.values()}},
               "controles": R, "frenos": frenos, "da": all(v == "PASS" for k, v in R.items() if not k.startswith("sha256_"))}
    a.informe.parent.mkdir(parents=True, exist_ok=True)
    a.informe.write_text(json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in R.items():
        if not k.startswith("sha256_"):
            print(f"{v}  {k}")
    print(f"prueba: {'PASS' if informe['da'] else 'FAIL'} ({sum(v == 'PASS' for v in R.values())} de "
          f"{sum(1 for k in R if not k.startswith('sha256_'))}); informe sha256 {sha_b(a.informe.read_bytes())}")
    return 0 if informe["da"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
