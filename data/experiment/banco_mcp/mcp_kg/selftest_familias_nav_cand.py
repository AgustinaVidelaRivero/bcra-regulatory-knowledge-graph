#!/usr/bin/env python3
"""selftest_familias_nav_cand.py — U-CAND-DESC, etapa a: selftest de la candidata ver_descendientes
(familias_nav_cand.py), sin Neo4j, sin el denso y sin modelo de lenguaje (USD 0). Los navegadores se arman con el doble
de selftest_familias_nav.py (_DriverSinNeo4j y navegador_sin_neo4j), importado sin cambiarlo, sobre el índice por punto
de una config `config_mcp_kg_nav_*.json`; el denso de la config se apaga en memoria (la familia 1 queda en BM25).

Solo imprime cuentas, sha256 y tamaños: ningún texto de la norma, ninguna clave de punto, ninguna ruta.

Casos:
  C0  el arranque: el navegador de HEAD (navegador_sin_neo4j) y el candidato (NavegadorCand sobre _DriverSinNeo4j, con
      los argumentos de servidor_mcp_kg_nav.abrir_navegador) cargan el mismo índice; la definición de la herramienta y
      TOOLS_NAV_CAND, TOPES_CAND y FAMILIA_CAND son los de HEAD más los de ella; lo heredado no cambia; los módulos del
      proyecto se cargan de la copia;
  C1  en cada punto con hijos, con niveles 1, 2 y 3: el orden de _descendientes es el esperado (escrito aparte, desde
      indice_puntos.orden_canonico y los ancestros por `padre`); cada página es, carácter por carácter, la cabecera y
      los bloques esperados (el texto, el de _texto_propio) con el pie donde va; ninguna pasa el tope; una página corta
      solo si no entra todo, y donde el bloque siguiente ya no entra entero con su pie; juntando las páginas con desde
      salen todos, sin faltas ni repetidos;
  C2  el pie de desde: la forma de PIE_BUSCAR_PUNTOS; en cada página que lo lleva es la última línea, con n los que
      faltan y k la posición del primero que no entró, y la página de desde=k empieza en él;
  C3  el texto que no entra solo en el tope, en los casos de N5 y en dos sintéticos en memoria: va cortado con la marca
      de corte del texto de ver_punto, es un prefijo del texto propio, la cabecera dice dónde se cortó y el pie lo dice;
  C4  un punto que no existe y un TO: el aviso de ver_punto con el nombre de esta herramienta; el del TO remite a
      indice_to;
  C5  niveles y desde fuera de rango o de otro tipo: la salida es la del valor que da _entero (tabla escrita aparte y
      comparada con _entero); despachar_cand con argumentos que faltan usa los valores por defecto;
  C6  una estructura sintética en memoria, con una clave repetida entre los hijos, ciclos (uno que vuelve al punto), un
      autociclo y una clave que no está en el índice: termina, ningún descendiente sale dos veces y salen los esperados;
  C7  despachar_cand con cada una de las seis herramientas de HEAD da, byte a byte, lo mismo que familias_nav.despachar
      sobre el navegador de HEAD, con los mismos argumentos, en los primeros 20 puntos con hijos del orden canónico; con
      el doble, lo que lee aristas falla igual de los dos lados (misma excepción, mismo mensaje) y se cuenta aparte;
  C8  la medida, con niveles 1, 2 y 3: cuántos puntos con hijos entran en una sola llamada, la mediana y el máximo de
      caracteres de su salida completa (la cabecera y todos los bloques, sin tope) y cuántas llamadas hacen falta en el
      peor caso.
Uso (desde la raíz de la copia, nunca del repo; con el python del .venv del repo):
  python -B data/experiment/banco_mcp/mcp_kg/selftest_familias_nav_cand.py \\
      --config data/experiment/banco_mcp/mcp_kg/config_mcp_kg_nav_acumulado.json [--salida <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import selftest_familias_nav as STF  # noqa: E402  (el doble sin Neo4j, sin cambios; agrega banco y neo4j al path)
import familias_nav as FN  # noqa: E402
import familias_nav_cand as FC  # noqa: E402
import indice_puntos as IP  # noqa: E402
from comun_banco import cargar_config  # noqa: E402
from grafos import GRAFOS  # noqa: E402  (data/experiment/neo4j)

RAIZ_COPIA = AQUI.parents[3]
TOPE = 8000
NIVELES = (1, 2, 3)
HERRAMIENTAS_HEAD = ("buscar_puntos", "ver_punto", "ver_remisiones", "indice_to", "tipos_de_relacion",
                     "vecinos_por_relacion")
RE_PIE = re.compile(r"\((\d+) descendientes más no entran en el tope: pedí desde=(\d+), o leelos con ver_punto\)")
RE_FORMA_PIE = re.compile(r"\(\{n\} (\w+) más no entran en el tope: pedí desde=\{k\}, o [^{}]+\)")
RE_TEXTO_CORTADO = re.compile(r"Texto \((\d+) caracteres, cortado en (\d+)\):\n")
# La marca de corte del texto de ver_punto, tomada de su función (familias_nav._lineas_texto_cortado).
MARCA_CORTE = FN._lineas_texto_cortado("a " * 1000)[1][-1]
# C5: lo que da _entero, escrito aparte. niveles: defecto 2, de 1 a 3; desde: defecto 0, de 0 a 10**9.
NIVELES_RAROS = [(0, 1), (-1, 1), (4, 3), (99, 3), ("2", 2), ("3", 3), ("x", 2), (None, 2), (2.7, 2), ("1.5", 2),
                 ([], 2), (True, 1)]
DESDE_RAROS = [(-1, 0), (-100, 0), ("x", 0), (None, 0), ("3", 3), (2.9, 2), (10 ** 12, 10 ** 9), ([], 0), (True, 1)]


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class Resultado:
    def __init__(self):
        self.casos = []

    def caso(self, nombre: str, ok: bool, detalle: str = "") -> None:
        self.casos.append({"caso": nombre, "ok": bool(ok), "detalle": detalle})
        print(f"[{'OK' if ok else 'FALLA'}] {nombre}" + (f" · {detalle}" if detalle else ""), flush=True)


# --------------------------------------------------------------------------- #
# Lo esperado, escrito aparte de familias_nav_cand                             #
# --------------------------------------------------------------------------- #
class Esperado:
    """El orden sale del preorden de todo el índice (indice_puntos.orden_canonico) y de los ancestros por `padre`
    (indice_puntos.ancestros): los descendientes de k son los que siguen a k en ese orden mientras k sea su ancestro, y
    el nivel es la diferencia de ancestros. El texto, de _texto_propio. Solo para estructuras que son árboles."""

    def __init__(self, nav):
        self.nav = nav
        self.orden = IP.orden_canonico(nav.puntos)
        self.lugar = {k: i for i, k in enumerate(self.orden)}
        self.anc = {k: IP.ancestros(nav.puntos, k) for k in self.orden}

    def orden_de(self, k: str, niveles: int) -> list[str]:
        base, out = len(self.anc[k]), []
        for x in self.orden[self.lugar[k] + 1:]:
            if k not in self.anc[x]:
                break
            if len(self.anc[x]) - base <= niveles:
                out.append(x)
        return out

    @staticmethod
    def cabecera(k: str, niveles: int, n: int, desde: int) -> str:
        return (f"ver_descendientes {k} · {niveles} nivel{'es' if niveles > 1 else ''} · "
                + ("1 descendiente" if n == 1 else f"{n} descendientes") + (f" · desde={desde}" if desde else ""))

    def cabeza(self, pos: int, x: str) -> str:
        p = self.nav.puntos[x]
        return f"#{pos} · {p['unidad']} · {FN._celda(p['titulo'] or '—', 200)} · {FN._n_nodos(len(p['nodos']))}"

    def bloque(self, pos: int, x: str) -> str:
        t = self.nav._texto_propio(x)
        return self.cabeza(pos, x) + "\n" + (f"Texto ({len(t)} caracteres):\n{t}" if t else "Texto: — (sin texto propio)")

    @staticmethod
    def pie(n: int, k: int) -> str:
        return f"({n} descendientes más no entran en el tope: pedí desde={k}, o leelos con ver_punto)"

    @staticmethod
    def pie_cortado(x: str, m: int, n: int) -> str:
        return (f"(el texto de {x} no entra solo en el tope: va cortado en {m} de {n} caracteres; leelo entero con "
                "ver_punto)")


def revisar_paginas(nav, E: Esperado, k: str, niveles: int, c: Counter, fallas: Counter, h) -> dict:
    """Las páginas de (k, niveles), siguiendo el pie desde desde=0, contra lo esperado. Suma en `c` las cuentas y en
    `fallas` las fallas por tipo; devuelve el resumen de este (k, niveles)."""
    esperado = E.orden_de(k, niveles)
    n = len(esperado)
    bloques = [E.bloque(i + 1, x) for i, x in enumerate(esperado)]
    if nav._descendientes(k, niveles) != esperado:
        fallas["orden"] += 1
    completa = E.cabecera(k, niveles, n, 0) + "".join("\n" + b for b in bloques)
    vistos, desde, paginas, cortes, previo_pie = [], 0, 0, 0, None
    while True:
        out = nav.ver_descendientes(k, niveles, desde)
        h.update(out.encode("utf-8"))
        paginas += 1
        c["llamadas"] += 1
        c["max_largo"] = max(c["max_largo"], len(out))
        if len(out) > TOPE:
            fallas["tope"] += 1
        cab = E.cabecera(k, niveles, n, desde)
        no_entra_todo = len(cab) + sum(len(b) + 1 for b in bloques[desde:]) > TOPE
        cuerpo, e = cab, desde
        while e < n:
            cand = cuerpo + "\n" + bloques[e]
            if not (out.startswith(cand) and (len(out) == len(cand) or out[len(cand)] == "\n")):
                break
            cuerpo, e = cand, e + 1
        if previo_pie is not None:
            # La página de desde=k (el k del pie anterior) empieza en el bloque k, numerado k + 1.
            c["paginas_tras_pie"] += 1
            if e > desde or out.startswith(cab + "\n" + E.cabeza(desde + 1, esperado[desde]) + "\n"):
                c["empiezan_en_k"] += 1
        reserva = (lambda i: len(E.pie(n - i - 1, i + 1)) + 1 if i + 1 < n else 0)
        if e > desde:
            if out != cuerpo + ("\n" + E.pie(n - e, e) if e < n else ""):
                fallas["bytes"] += 1
                break
            if e < n and not (no_entra_todo and len(cuerpo) + 1 + len(bloques[e]) + reserva(e) > TOPE):
                fallas["corta_antes"] += 1
            vistos += range(desde, e)
            c["bloques_enteros"] += e - desde
        else:
            x, t_full = esperado[desde], nav._texto_propio(esperado[desde])
            if not (no_entra_todo and len(cab) + 1 + len(bloques[desde]) + reserva(desde) > TOPE):
                fallas["corte_sin_motivo"] += 1
            pre = cab + "\n" + E.cabeza(desde + 1, x) + "\n"
            mh = RE_TEXTO_CORTADO.match(out, len(pre)) if out.startswith(pre) else None
            if mh is None or int(mh.group(1)) != len(t_full):
                fallas["corte"] += 1
                break
            m = int(mh.group(2))
            t = t_full[:m]
            resto = out[mh.end():]
            esperado_resto = (t + MARCA_CORTE + "\n" + E.pie_cortado(x, m, len(t_full))
                              + ("\n" + E.pie(n - desde - 1, desde + 1) if desde + 1 < n else ""))
            if not (m < len(t_full) and t == t.rstrip() and resto == esperado_resto):
                fallas["corte"] += 1
                break
            if E.pie_cortado(x, m, len(t_full)) != FC.PIE_TEXTO_CORTADO.format(clave=x, m=m, n=len(t_full)):
                fallas["pie_cortado_def"] += 1
            vistos.append(desde)
            c["bloques_cortados"] += 1
            cortes += 1
            e = desde + 1
        if e < n:
            mp = RE_PIE.fullmatch(out.rpartition("\n")[2])
            if not mp or int(mp.group(1)) != n - e or int(mp.group(2)) != e:
                fallas["pie"] += 1
                break
            if E.pie(n - e, e) != FC.PIE_VER_DESCENDIENTES.format(n=n - e, k=e):
                fallas["pie_def"] += 1
            c["pies"] += 1
            desde = previo_pie = int(mp.group(2))
        else:
            if RE_PIE.search(out.rpartition("\n")[2]):
                fallas["pie_de_mas"] += 1
            break
        if paginas > n + 1:
            fallas["no_termina"] += 1
            break
    if vistos != list(range(n)):
        fallas["faltas_o_repetidos"] += 1
    return {"n": n, "paginas": paginas, "cortes": cortes, "largo_completa": len(completa)}


# --------------------------------------------------------------------------- #
# Estructuras sintéticas (C3 y C6)                                             #
# --------------------------------------------------------------------------- #
def nav_sintetico(puntos: dict) -> FC.NavegadorCand:
    """Un NavegadorCand con solo `puntos`, sin el constructor: ver_descendientes no lee otra cosa."""
    nav = object.__new__(FC.NavegadorCand)
    nav.puntos = puntos
    return nav


def _p(to: str, unidad: str | None, hijos: list, padre: str | None, textos=(), tipo: str = "punto") -> dict:
    return {"tipo": tipo, "to": to, "unidad": unidad or to, "titulo": f"Título sintético {unidad or to}",
            "hijos": list(hijos), "padre": padre, "textos": list(textos), "nodos": ["n_sint"] * 2}


def texto_sintetico(n_palabras: int) -> str:
    return "\n".join(" ".join(f"palabra{i}{j}" for j in range(10)) for i in range(n_palabras // 10))


def estructura_corte() -> dict:
    """Dos árboles: en sin::1 el descendiente del medio no entra solo; en sin::2 el único no entra solo."""
    return {
        "sin": _p("sin", None, ["sin::1", "sin::2"], None, tipo="to"),
        "sin::1": _p("sin", "1", ["sin::1.1", "sin::1.2", "sin::1.3"], "sin", ["texto del contenedor"]),
        "sin::1.1": _p("sin", "1.1", [], "sin::1", [texto_sintetico(60)]),
        "sin::1.2": _p("sin", "1.2", ["sin::1.2.1"], "sin::1", [texto_sintetico(1500), texto_sintetico(800)]),
        "sin::1.2.1": _p("sin", "1.2.1", [], "sin::1.2", ["corto"]),
        "sin::1.3": _p("sin", "1.3", [], "sin::1", []),
        "sin::2": _p("sin", "2", ["sin::2.1"], "sin"),
        "sin::2.1": _p("sin", "2.1", [], "sin::2", [texto_sintetico(3000)]),
    }


def estructura_ciclos() -> dict:
    """Una clave repetida entre los hijos de cic::1, un ciclo que vuelve al punto (cic::1.1 -> cic::1), otro más largo
    (cic::1.1.1 -> cic::1.1), un autociclo (cic::1.2) y una clave que no está en el índice."""
    return {
        "cic": _p("cic", None, ["cic::1"], None, tipo="to"),
        "cic::1": _p("cic", "1", ["cic::1.1", "cic::1.1", "cic::1.2", "cic::no_esta"], "cic", ["a"]),
        "cic::1.1": _p("cic", "1.1", ["cic::1", "cic::1.1.1"], "cic::1", ["b"]),
        "cic::1.1.1": _p("cic", "1.1.1", ["cic::1.1", "cic::1.2"], "cic::1.1", ["c"]),
        "cic::1.2": _p("cic", "1.2", ["cic::1.2", "cic::1.2.1"], "cic::1", ["d"]),
        "cic::1.2.1": _p("cic", "1.2.1", ["cic::1"], "cic::1.2", []),
    }


# Lo esperado en C6, escrito a mano: cada clave en el nivel de su distancia, en preorden, una vez.
ESPERADO_CICLOS = {
    ("cic::1", 1): ["cic::1.1", "cic::1.2"],
    ("cic::1", 2): ["cic::1.1", "cic::1.1.1", "cic::1.2", "cic::1.2.1"],
    ("cic::1", 3): ["cic::1.1", "cic::1.1.1", "cic::1.2", "cic::1.2.1"],
    ("cic::1.1.1", 1): ["cic::1.1", "cic::1.2"],
    ("cic::1.1.1", 2): ["cic::1.1", "cic::1", "cic::1.2", "cic::1.2.1"],
    ("cic::1.1.1", 3): ["cic::1.1", "cic::1", "cic::1.2", "cic::1.2.1"],
    ("cic::1.2", 3): ["cic::1.2.1", "cic::1", "cic::1.1"],
}
RE_CABEZA = re.compile(r"#(\d+) · (\S+) · ")


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--salida", type=Path)
    a = ap.parse_args()
    t_ini = time.time()
    R = Resultado()
    config, _ = cargar_config(a.config)
    config_sd = {**config, "denso": {**(config.get("denso") or {}), "requerido": False}}
    indice_dir = (STF.AQUI / config["indice_puntos"]).resolve()
    print(f"== selftest familias nav cand · {config['grafo']} · sin Neo4j y sin denso", flush=True)

    # C0 ------------------------------------------------------------------- #
    nav_head = STF.navegador_sin_neo4j(config_sd)
    nav = FC.NavegadorCand(STF._DriverSinNeo4j(indice_dir, config.get("kg_sha256_esperado")),
                           GRAFOS[config["grafo"]]["label"], indice_dir,
                           sha256_manifiesto=config["sha256_manifiesto_indice"], python_vector=None,
                           hubs_esperados=None)
    mismo = (type(nav_head) is FN.Navegador and isinstance(nav, FN.Navegador) and nav_head.denso is None
             and nav.denso is None and nav.label == nav_head.label and nav.dir == nav_head.dir
             and sha(json.dumps(nav.puntos, sort_keys=True)) == sha(json.dumps(nav_head.puntos, sort_keys=True))
             and nav.ids_docs == nav_head.ids_docs and len(nav.nodos) == len(nav_head.nodos)
             and not nav.grado and not nav_head.grado)
    sha_man = IP.sha256_file(indice_dir / "manifiesto.json")
    R.caso("C0a los dos navegadores, sobre el doble y sin denso, cargan el mismo índice", mismo and
           sha_man == config["sha256_manifiesto_indice"],
           f"puntos={len(nav.puntos)} nodos={len(nav.nodos)} documentos={len(nav.ids_docs)} "
           f"sha256 manifiesto={sha_man[:16]}… (el de la config: {sha_man == config['sha256_manifiesto_indice']})")
    defs_head = {t["name"]: t for t in FN.TOOLS_NAV}
    firmas_head = set(defs_head) == set(STF.FIRMAS_N2) and all(
        defs_head[x]["familia"] == f and list(defs_head[x]["input_schema"]["properties"]) == args
        and defs_head[x]["input_schema"]["required"] == req for x, (f, args, req) in STF.FIRMAS_N2.items())
    nueva = FC.TOOLS_NAV_CAND[-1]
    ok_defs = (firmas_head and len(FN.TOOLS_NAV) == 6 and len(FC.TOOLS_NAV_CAND) == 7
               and all(x is y for x, y in zip(FC.TOOLS_NAV_CAND[:6], FN.TOOLS_NAV))
               and nueva["name"] == "ver_descendientes" and nueva["familia"] == 2
               and list(nueva["input_schema"]["properties"]) == ["punto", "niveles", "desde"]
               and nueva["input_schema"]["required"] == ["punto"] and bool(nueva["description"])
               and FC.TOPES_CAND == {**FN.TOPES, "ver_descendientes": TOPE} and len(FN.TOPES) == 6
               and FC.FAMILIA_CAND == {**FN.FAMILIA, "ver_descendientes": 2} and len(FN.FAMILIA) == 6)
    R.caso("C0b TOOLS_NAV_CAND, TOPES_CAND y FAMILIA_CAND: los de HEAD (intactos) más ver_descendientes", ok_defs,
           f"herramientas {len(FN.TOOLS_NAV)}+1; tope {FC.TOPES_CAND['ver_descendientes']}; familia "
           f"{FC.FAMILIA_CAND['ver_descendientes']}")
    heredados = list(HERRAMIENTAS_HEAD) + ["_texto_propio", "resolver_punto", "resolver_to", "__init__"]
    R.caso("C0c NavegadorCand no redefine nada de Navegador", all(getattr(FC.NavegadorCand, x) is
                                                                   getattr(FN.Navegador, x) for x in heredados),
           f"{len(heredados)} atributos comparados")
    prefijos = {Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()}
    de_copia, de_entorno, otros = 0, 0, 0
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        p = Path(f).resolve()
        if RAIZ_COPIA in p.parents:
            de_copia += 1
        elif any(x in p.parents for x in prefijos):
            de_entorno += 1
        else:
            otros += 1
    shas = {Path(m.__file__).name: IP.sha256_file(Path(m.__file__)) for m in (FN, STF, FC)}
    R.caso("C0d los módulos del proyecto, de la copia; ninguno de otro lado", otros == 0 and de_copia > 0,
           f"de la copia {de_copia} · del entorno de python {de_entorno} · de otro lado {otros} · "
           + " · ".join(f"{x} {s[:16]}…" for x, s in shas.items()))

    # C1 y C2 --------------------------------------------------------------- #
    E = Esperado(nav)
    con_hijos = [k for k in E.orden if nav.puntos[k]["hijos"]]
    c, fallas, medidas = Counter(), Counter(), {n: {} for n in NIVELES}
    h = hashlib.sha256()
    for niveles in NIVELES:
        for k in con_hijos:
            medidas[niveles][k] = revisar_paginas(nav, E, k, niveles, c, fallas, h)
    combos = len(con_hijos) * len(NIVELES)
    R.caso("C1 cada punto con hijos, niveles 1 a 3: orden, bytes, tope, cortes y páginas sin faltas ni repetidos",
           not fallas and c["max_largo"] <= TOPE,
           f"puntos con hijos {len(con_hijos)} · combinaciones {combos} · llamadas {c['llamadas']} · bloques con el "
           f"texto entero {c['bloques_enteros']} · cortados {c['bloques_cortados']} · máximo {c['max_largo']}/{TOPE} · "
           f"fallas {dict(sorted(fallas.items())) or 0} · sha256 de las salidas {h.hexdigest()[:16]}…")
    forma = [RE_FORMA_PIE.fullmatch(x) for x in (FN.PIE_BUSCAR_PUNTOS, FC.PIE_VER_DESCENDIENTES)]
    ok_forma = all(forma) and forma[0].group(1) == "puntos" and forma[1].group(1) == "descendientes"
    R.caso("C2 el pie de desde: la forma de PIE_BUSCAR_PUNTOS; n y k donde van; la página de desde=k empieza en k",
           ok_forma and not (fallas["pie"] or fallas["pie_def"] or fallas["pie_de_mas"]) and c["pies"] > 0
           and c["empiezan_en_k"] == c["paginas_tras_pie"] == c["pies"],
           f"forma común «({{n}} … más no entran en el tope: pedí desde={{k}}, o …)»: {ok_forma} · pies revisados "
           f"{c['pies']} · páginas tras un pie {c['paginas_tras_pie']}, que empiezan en k {c['empiezan_en_k']}")

    # C3 -------------------------------------------------------------------- #
    cortes_n5 = {n: sum(1 for v in medidas[n].values() if v["cortes"]) for n in NIVELES}
    ns = nav_sintetico(estructura_corte())
    Es = Esperado(ns)
    cs, fs, hs = Counter(), Counter(), hashlib.sha256()
    for niveles in NIVELES:
        for k in ("sin::1", "sin::2"):
            revisar_paginas(ns, Es, k, niveles, cs, fs, hs)
    marca_ok = MARCA_CORTE == "…" and FN._lineas_texto_cortado("b " * 1000)[1].endswith(MARCA_CORTE)
    R.caso("C3 el texto que no entra solo: cortado con la marca de ver_punto, prefijo del texto propio, con su pie",
           marca_ok and c["bloques_cortados"] > 0 and not fallas["corte"] and not fallas["corte_sin_motivo"]
           and cs["bloques_cortados"] == 6 and not fs and cs["max_largo"] <= TOPE,
           f"marca de ver_punto U+{ord(MARCA_CORTE):04X} · N5: {c['bloques_cortados']} bloques cortados, combinaciones "
           f"con corte por niveles {cortes_n5} · sintético: {cs['llamadas']} llamadas, {cs['bloques_cortados']} "
           f"cortados (6 esperados), máximo {cs['max_largo']}/{TOPE}, fallas {dict(fs) or 0}")

    # C4 -------------------------------------------------------------------- #
    avisos = ["zzz::99.99", "no existe", "", None, 123, "ext::", nav.tos[0], nav.tos[0].upper(), f"  {nav.tos[-1]} "]
    ok4, con_to = 0, 0
    for p in avisos:
        x = nav.ver_descendientes(p)
        y = nav_head.ver_punto(p)
        t = nav.resolver_to(p)
        bien = (x == y.replace("ver_punto:", "ver_descendientes:", 1)
                and x.startswith("ver_descendientes: no existe el punto «") and len(x) <= TOPE
                and x == FC.despachar_cand(nav, "ver_descendientes", {"punto": p}))
        if t:
            con_to += 1
            bien = bien and f"indice_to(«{t}»)" in x
        ok4 += bien
    R.caso("C4 un punto que no existe y un TO: el aviso de ver_punto; el del TO remite a indice_to",
           ok4 == len(avisos) and con_to == 3, f"{ok4} de {len(avisos)} avisos · {con_to} con un TO")

    # C5 -------------------------------------------------------------------- #
    k5 = next(k for k in con_hijos if 4 <= len(E.orden_de(k, 1)) < len(E.orden_de(k, 2)) < len(E.orden_de(k, 3)))
    distintas = len({nav.ver_descendientes(k5, n) for n in NIVELES}) == 3 and len(
        {nav.ver_descendientes(k5, 1, d) for d in (0, 1, 2, 3)}) == 4
    ok_n = sum(FN._entero(v, 2, 1, 3) == esp and nav.ver_descendientes(k5, v) == nav.ver_descendientes(k5, esp)
               for v, esp in NIVELES_RAROS)
    ok_d = sum(FN._entero(v, 0, 0, 10 ** 9) == esp
               and nav.ver_descendientes(k5, 1, v) == nav.ver_descendientes(k5, 1, esp) for v, esp in DESDE_RAROS)
    fuera = nav.ver_descendientes(k5, 1, 10 ** 12)
    ok_fuera = fuera == (Esperado.cabecera(k5, 1, len(E.orden_de(k5, 1)), 10 ** 9)
                         + f"\nNo hay más descendientes: son {len(E.orden_de(k5, 1))} (desde={10 ** 9}).")
    defecto = (FC.despachar_cand(nav, "ver_descendientes", {"punto": k5}) == nav.ver_descendientes(k5, 2, 0)
               == FC.despachar_cand(nav, "ver_descendientes", {"punto": k5, "niveles": "x", "desde": None})
               and FC.despachar_cand(nav, "ver_descendientes", None) == nav.ver_descendientes("", 2, 0)
               and FC.despachar_cand(nav, "ver_descendientes", {"punto": k5, "niveles": 3, "desde": 2})
               == nav.ver_descendientes(k5, 3, 2))
    R.caso("C5 niveles y desde fuera de rango: la salida del valor de _entero; despachar_cand con los de defecto",
           ok_n == len(NIVELES_RAROS) and ok_d == len(DESDE_RAROS) and ok_fuera and defecto and distintas,
           f"niveles {ok_n} de {len(NIVELES_RAROS)} · desde {ok_d} de {len(DESDE_RAROS)} · desde=10**12 da el aviso "
           f"de desde=10**9: {ok_fuera} · defectos: {defecto} · salidas distintas por niveles y por desde: {distintas}")

    # C6 -------------------------------------------------------------------- #
    nc = nav_sintetico(estructura_ciclos())
    ok6, llamadas6 = 0, 0
    for (k, niveles), esp in ESPERADO_CICLOS.items():
        orden = nc._descendientes(k, niveles)
        esperadas = list(enumerate((nc.puntos[x]["unidad"] for x in esp), 1))
        bien = orden == esp and len(set(orden)) == len(orden) and k not in orden
        # Todo entra en una página: la de desde=d lista las posiciones d + 1 en adelante, y más allá del final, nada.
        for d in range(len(esp) + 2):
            out = nc.ver_descendientes(k, niveles, d)
            llamadas6 += 1
            bien = bien and [(int(m.group(1)), m.group(2)) for m in RE_CABEZA.finditer(out)] == esperadas[d:]
        ok6 += bien
    sin_tope = nc._descendientes("cic::1", 10 ** 6)
    ok_sin_tope = sin_tope == ESPERADO_CICLOS[("cic::1", 3)]
    R.caso("C6 clave repetida, ciclos, autociclo y clave ausente: termina, sin repetidos, los esperados",
           ok6 == len(ESPERADO_CICLOS) and ok_sin_tope,
           f"{ok6} de {len(ESPERADO_CICLOS)} casos · {llamadas6} llamadas · _descendientes con niveles=10**6 termina "
           f"y da {len(sin_tope)} claves, las esperadas: {ok_sin_tope}")

    # C7 -------------------------------------------------------------------- #
    def resultado(f, *args):
        try:
            return ("salida", f(*args))
        except Exception as e:  # noqa: BLE001  (con el doble, lo que lee aristas falla: se compara la excepción)
            return ("excepcion", type(e).__name__, str(e))

    primeros = con_hijos[:20]
    por_tool = {x: Counter() for x in HERRAMIENTAS_HEAD}
    h_cand, h_head = hashlib.sha256(), hashlib.sha256()
    for k in primeros + [None]:
        if k is None:
            llamadas = {x: [None, {}] for x in HERRAMIENTAS_HEAD}
        else:
            p = nav.puntos[k]
            nid = p["nodos"][0] if p["nodos"] else "—"
            llamadas = {
                "buscar_puntos": [{"consulta": "plazo", "punto": k}, {"consulta": k, "to": p["to"], "limite": 3,
                                                                       "desde": 1}],
                "ver_punto": [{"punto": k}, {"punto": k, "max_nodos": 1}],
                "ver_remisiones": [{"punto": k}, {"punto": k, "direccion": "cita", "saltos": 2}],
                "indice_to": [{"to": p["to"], "desde": k, "niveles": 3}, {"to": p["to"]}],
                "tipos_de_relacion": [{"id": nid}],
                "vecinos_por_relacion": [{"id": nid, "relacion": "remite_a", "direccion": "salientes"}],
            }
        for x, lista in llamadas.items():
            for args in lista:
                rc = resultado(FC.despachar_cand, nav, x, args)
                rh = resultado(FN.despachar, nav_head, x, args)
                h_cand.update(json.dumps(rc, ensure_ascii=False).encode("utf-8"))
                h_head.update(json.dumps(rh, ensure_ascii=False).encode("utf-8"))
                por_tool[x]["llamadas"] += 1
                por_tool[x]["iguales"] += rc == rh
                por_tool[x][rc[0]] += 1
    desconocida = FC.despachar_cand(nav, "no_existe", {}) == FN.despachar(nav_head, "no_existe", {})
    ok7 = all(v["llamadas"] == v["iguales"] for v in por_tool.values()) and desconocida \
        and h_cand.hexdigest() == h_head.hexdigest()
    R.caso("C7 despachar_cand = familias_nav.despachar en las seis de HEAD, 20 puntos más los argumentos vacíos",
           ok7, " · ".join(f"{x} {v['iguales']}/{v['llamadas']} (salidas {v['salida']}, excepciones {v['excepcion']})"
                           for x, v in por_tool.items())
           + f" · herramienta desconocida: {desconocida} · sha256 {h_cand.hexdigest()[:16]}… = {h_head.hexdigest()[:16]}…")

    # C8 -------------------------------------------------------------------- #
    medida = {}
    for n in NIVELES:
        v = list(medidas[n].values())
        una = [x for x in v if x["paginas"] == 1 and not x["cortes"]]
        consistente = all((x["largo_completa"] <= TOPE) == (x["paginas"] == 1 and not x["cortes"]) for x in v)
        medida[n] = {"puntos_con_hijos": len(v), "en_una_llamada": len(una),
                     "largo_completa_mediana": statistics.median(x["largo_completa"] for x in v),
                     "largo_completa_maximo": max(x["largo_completa"] for x in v),
                     "largo_completa_mediana_de_los_de_una_llamada": statistics.median(x["largo_completa"] for x in una),
                     "llamadas_peor_caso": max(x["paginas"] for x in v),
                     "llamadas_por_punto": dict(sorted(Counter(x["paginas"] for x in v).items())),
                     "descendientes_mediana": statistics.median(x["n"] for x in v),
                     "descendientes_maximo": max(x["n"] for x in v),
                     "una_llamada_sii_completa_entra": consistente}
        print(f"C8 niveles {n}: {len(una)} de {len(v)} en una llamada · salida completa mediana "
              f"{medida[n]['largo_completa_mediana']} máx {medida[n]['largo_completa_maximo']} caracteres · peor caso "
              f"{medida[n]['llamadas_peor_caso']} llamadas · llamadas por punto {medida[n]['llamadas_por_punto']}",
              flush=True)
    R.caso("C8 la medida (una llamada si y solo si la salida completa entra en el tope)",
           all(m["una_llamada_sii_completa_entra"] for m in medida.values()))

    n_fallas = sum(1 for x in R.casos if not x["ok"])
    resumen = {"grafo": config["grafo"], "sin_neo4j": True, "denso": False, "tope": TOPE, "casos": R.casos,
               "fallas": n_fallas, "c1": dict(sorted(c.items())), "c1_fallas": dict(sorted(fallas.items())),
               "c3_sintetico": dict(sorted(cs.items())), "c7": {x: dict(v) for x, v in por_tool.items()},
               "medida": {str(n): m for n, m in medida.items()}, "sha256_salidas_c1": h.hexdigest(),
               "sha256_modulos": shas, "segundos": round(time.time() - t_ini, 1)}
    if a.salida:
        a.salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSELFTEST familias nav cand ({config['grafo']}, sin Neo4j y sin denso): "
          f"{'OK' if n_fallas == 0 else f'{n_fallas} FALLAS'} · {len(R.casos)} casos · {resumen['segundos']} s")
    return 0 if n_fallas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
