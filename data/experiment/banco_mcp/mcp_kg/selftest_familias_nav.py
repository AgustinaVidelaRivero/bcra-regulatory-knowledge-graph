#!/usr/bin/env python3
"""selftest_familias_nav.py — U-NAV-DISENO, N5: selftest de las herramientas de las familias 1 a 5 (familias_nav.py) y
de su servidor (servidor_mcp_kg_nav.py), sin modelo de lenguaje (USD 0). Corre sobre el grafo y el índice de una config
`config_mcp_kg_nav_*.json`, con el grafo cargado en Neo4j por cargar_neo4j_tanda0.py.

Dos modos (el cegamiento del mandato, §7, regla 5):
  --contenido  imprime salidas de ejemplo (solo para grafos de la tanda 0);
  --cuentas    solo pasa/falla, cuentas, largos y sha256 (para el acumulado, que trae la tanda 1).

Casos:
  T0  el índice por punto: re-derivado desde el kg.json y la E0, da los mismos bytes (y la matriz densa su sha256);
  T1  las firmas: nombres, familias y argumentos de las seis herramientas, los de N2;
  T2  los topes de N2 en cada herramienta, sobre todos los puntos (ver_punto, ver_remisiones), todos los TOs y
      contenedores (indice_to), los hubs y una muestra de nodos (familia 5) y una batería de consultas con filtros y
      límites de borde (buscar_puntos); ver_punto, contra el tope de su punto (U-VERPUNTO: familias_nav.tope_ver_punto,
      5.000 más lo que la sección del texto entero usa de más que la cortada);
  T3  buscar_puntos: los filtros se respetan, a lo sumo 3 nodos por fila, la misma llamada da la misma salida y el
      orden es el de la fusión RRF con k = 60 de los dos rankings;
  T4  ver_punto: «::intro» da lo mismo que el punto; un punto inexistente da su aviso;
  T5  ver_remisiones: una fila por punto y dirección (sin repetidos);
  T6  familia 5: un hub sin filtro no lista; con filtro, sí; la paginación sigue donde termina la página anterior;
  T7  las marcas de las aristas (no verificada, cola humana, sujeto derivado), sobre propiedades sintéticas;
  T8  el caso obligatorio de la jerarquía (N4, §5): desde la Definicion de cla::5.1.1 se llega a la Excepcion de
      cla::5.1.1.1 en 2 llamadas (ver_punto del contenedor, que lista el hijo, y ver_punto del hijo);
  T9  el hallazgo 2.7: docvig::2.1.1.1, 2.1.2.1 y 2.2.1.1 se distinguen por los títulos de sus ancestros;
  T10 el servidor, por stdio (banco_mcp/cliente_falso.py): lista las tres herramientas de hoy con la definición de
      harness.TOOLS y las de las familias de la config; las tres de hoy dan, byte a byte, la cadena del servidor de
      hoy, y las nuevas, la del Navegador directo;
  T11 `desde` en buscar_puntos (U-NAV-DESDE): con desde=0, cada llamada de T2/T3 da la misma salida que sin desde;
      el caso del borrador, con su pie, también; con desde=k, las filas son las posiciones k a k + limite - 1 de la
      fusión entera (escrita aparte, como en T3), numeradas por su lugar, sin repetir las de desde=0 cuando k >= limite,
      y pedir desde = las filas ya mostradas recorre el ranking sin saltos; con to=cla y desde=8 aparecen
      cla::6.5.5.4 y cla::6.5.5.5; desde más allá del final lo dice y no falla; lo que no es un entero de 0 o más vale
      0; la definición de la herramienta; el pie, cuando el tope corta filas, dice desde = la primera fila que no entró
      y con ese desde la página siguiente empieza ahí, sin saltos ni repetidos; el pie nuevo no es más largo que el de N5
      y el grafo servido tiene menos de 100.000 puntos. Sus salidas no entran en el sha256 de las salidas ni en las
      cuentas de T2. El resumen suma el sha256 de las salidas con el pie nuevo cambiado por el de N5 (mismo n), para
      compararlo con el de N5, y cuántas salidas llevan el pie nuevo.
  T12 el texto propio entero en ver_punto (U-VERPUNTO), en cada punto con max_nodos 15 y 25: en los puntos de más de
      1.500 caracteres, la cabecera es «Texto (N caracteres):», con N el largo del texto propio, y lo que sigue hasta
      la sección siguiente es el texto propio entero; en todos, la salida trae la sección del texto donde va, y la del
      texto de hoy (escrita aparte: juntado en una línea y cortado en 1.499 más «…», con «, cortado en 1.500» en la
      cabecera) se le puede restituir; el tope del punto es 5.000 más lo que la sección nueva usa de más que la de hoy, y
      la salida no lo pasa. Sus salidas no entran en el sha256 de las salidas ni en las cuentas de T2. El resumen suma el
      sha256 de las salidas de T2 con la sección del texto de los puntos largos cambiada por la de hoy (el de U-NAV-DESDE)
      y, además, con el pie de N5 (el de N5), y cuenta las salidas de ver_punto de T2 que cambian, por max_nodos.
Modo --sin-neo4j (U-NAV-DESDE): T0, T1, la parte de buscar_puntos de T2 y T3, y T11, con el Navegador armado sobre el
índice por punto sin conectarse a Neo4j (_DriverSinNeo4j); no corren T2 de las otras herramientas ni T4 a T10, que
leen aristas o el servidor, y el sha256 de las salidas es solo el de buscar_puntos.
Uso (desde la raíz del repo, con NEO4J_URI y, si la config pide el denso, BANCO_VENV_VECTOR):
  .venv/bin/python -B data/experiment/banco_mcp/mcp_kg/selftest_familias_nav.py --config <config> --contenido|--cuentas
                   [--sin-neo4j] [--salida <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import servidor_mcp_kg as BASE  # noqa: E402
import servidor_mcp_kg_nav as SN  # noqa: E402
import familias_nav as FN  # noqa: E402
import indice_puntos as IP  # noqa: E402
from comun_banco import cargar_config, serializar_payload  # noqa: E402

# Las de N2; buscar_puntos lleva además `desde` (U-NAV-DESDE).
FIRMAS_N2 = {"buscar_puntos": (1, ["consulta", "to", "punto", "termino", "limite", "desde"], ["consulta"]),
             "ver_punto": (2, ["punto", "max_nodos"], ["punto"]),
             "ver_remisiones": (3, ["punto", "direccion", "saltos", "limite"], ["punto"]),
             "indice_to": (4, ["to", "desde", "niveles", "limite"], ["to"]),
             "tipos_de_relacion": (5, ["id"], ["id"]),
             "vecinos_por_relacion": (5, ["id", "relacion", "direccion", "to", "punto", "limite", "desde"],
                                      ["id", "relacion", "direccion"])}
CONSULTAS_FIJAS = ["plazo máximo", "excepción", "entidades financieras", "", "de la que", "123", "5.1.1",
                   "Clasificación en categoría Irrecuperable", "x" * 600, "¿qué pasa si no se cumple el requisito?"]
# T11 (U-NAV-DESDE). El texto de `desde` en la descripción, el mismo en buscar_pasajes (servidor_mcp_vector.py).
TEXTO_DESDE = ("desde: posición del ranking desde la que se listan los resultados (0 = los primeros). "
               "Sirve para ver los que no entraron.")
PROPIEDAD_DESDE = {"type": "integer", "description": "Posición desde la que se lista (def. 0)."}
CASO_BORRADOR = "Clasificación en categoría Irrecuperable"
# El caso del borrador como lo midió N5 (caso_irrecuperable_rangos): con to=cla, sin filtro y con punto=cla::6.5.5 y
# limite 10 (la que lleva el pie) y 6.
LLAMADAS_BORRADOR = [{"consulta": CASO_BORRADOR, "to": "cla"}, {"consulta": CASO_BORRADOR},
                     {"consulta": CASO_BORRADOR, "punto": "cla::6.5.5", "limite": 10},
                     {"consulta": CASO_BORRADOR, "punto": "cla::6.5.5", "limite": 6}]
CONSULTAS_DESDE = ["plazo máximo de exportación", "excepción a la prohibición", CASO_BORRADOR]
# El pie de buscar_puntos de N5 y el de U-NAV-DESDE, que dice desde dónde seguir. Para comparar con N5, el sha256 de las
# salidas se calcula también con el pie nuevo cambiado por el de N5, con el mismo n.
PIE_N5 = "({n} puntos más no entran en el tope de esta herramienta: bajá limite o filtrá)"
RE_PIE_NUEVO = re.compile(r"\((\d+) puntos más no entran en el tope: pedí desde=(\d+), o bajá limite o filtrá\)")


def con_el_pie_de_n5(out: str) -> tuple[str, bool]:
    """La salida con el pie nuevo de buscar_puntos (su última línea) cambiado por el de N5, con el mismo n."""
    cab, sep, ultima = out.rpartition("\n")
    m = RE_PIE_NUEVO.fullmatch(ultima) if sep else None
    return (cab + sep + PIE_N5.format(n=m.group(1)), True) if m else (out, False)


def texto_de_hoy(texto: str) -> list[str]:
    """U-VERPUNTO: la sección del texto de ver_punto como la daba antes (la cabecera y el texto), escrita aparte de
    familias_nav: el texto de más de 1.500 caracteres, juntado en una línea y cortado en 1.499 más «…», con «, cortado
    en 1.500» en la cabecera; el de 1.500 o menos, tal cual."""
    if len(texto) <= 1500:
        return [f"Texto ({len(texto)} caracteres):", texto]
    t = " ".join(texto.split())
    return [f"Texto ({len(texto)} caracteres, cortado en 1.500):", t if len(t) <= 1500 else t[:1499].rstrip() + "…"]


def con_el_texto_de_hoy(nav, k: str, out: str) -> str | None:
    """U-VERPUNTO: la salida de ver_punto del punto k con su sección del texto (después de las tres líneas de la
    cabecera) cambiada por la de hoy (texto_de_hoy), o None si la salida no la trae donde va."""
    texto = nav._texto_propio(k)
    if not texto:
        return out
    lineas = out.split("\n", 3)
    nueva = f"Texto ({len(texto)} caracteres):\n{texto}\n"
    if len(lineas) < 4 or not lineas[3].startswith(nueva):
        return None
    return "\n".join(lineas[:3] + texto_de_hoy(texto)) + "\n" + lineas[3][len(nueva):]


def _desde_del_pie(out: str) -> int | None:
    """El `desde` que dice el pie nuevo (la última línea), o None si no hay pie."""
    m = RE_PIE_NUEVO.fullmatch(out.rpartition("\n")[2])
    return int(m.group(2)) if m else None


class Resultado:
    def __init__(self, contenido: bool):
        self.contenido, self.casos, self.largos, self.h = contenido, [], {}, hashlib.sha256()
        self.h_n5, self.n_pie = hashlib.sha256(), 0      # U-NAV-DESDE: con el pie de N5, y cuántas llevan el nuevo
        # U-VERPUNTO: con el texto de hoy (y además con el pie de N5), y cuántas salidas de ver_punto cambian
        self.h_hoy, self.h_hoy_n5, self.cambian = hashlib.sha256(), hashlib.sha256(), {}

    def caso(self, nombre: str, ok: bool, detalle: str = "") -> None:
        self.casos.append({"caso": nombre, "ok": bool(ok), "detalle": detalle})
        print(f"  {'✓' if ok else '✗'} {nombre}{(' — ' + detalle) if detalle else ''}", flush=True)

    def salida(self, tool: str, out: str, hoy: str | None = None, max_nodos: int | None = None) -> str:
        """`hoy`: la salida con el texto de hoy (U-VERPUNTO, solo ver_punto); sin ella, la misma salida."""
        self.largos.setdefault(tool, []).append(len(out))
        self.h.update(out.encode("utf-8"))
        n5, con_pie = con_el_pie_de_n5(out)
        self.h_n5.update(n5.encode("utf-8"))
        self.n_pie += con_pie
        hoy = out if hoy is None else hoy
        self.h_hoy.update(hoy.encode("utf-8"))
        self.h_hoy_n5.update(con_el_pie_de_n5(hoy)[0].encode("utf-8"))
        if hoy != out:
            self.cambian[f"max_nodos_{max_nodos}"] = self.cambian.get(f"max_nodos_{max_nodos}", 0) + 1
        return out


def casos_buscar_puntos(nav, R: "Resultado", medir, puntos: list[str]) -> list[tuple[dict, str]]:
    """La parte de buscar_puntos de T2 y T3, tal como estaba en main(); devuelve cada llamada con su salida
    (U-NAV-DESDE: T11 las repite con desde=0). La usan main() y main_sin_neo4j()."""
    llamadas = []

    def bp(args: dict) -> str:
        out = FN.despachar(nav, "buscar_puntos", args)
        llamadas.append((args, out))
        return out

    # buscar_puntos
    terminos = [str(nav.nodos[n]["termino"]) for k in puntos for n in nav.puntos[k]["nodos"] if nav.nodos[n].get("termino")]
    consultas = CONSULTAS_FIJAS + [nav.puntos[k]["titulo"] for k in puntos[::97]]
    filtros_ok, nodos_ok, determinista, rrf_ok = True, True, True, True
    for q in consultas:
        for extra in ({}, {"limite": 10}, {"limite": 0}, {"limite": "x"}, {"limite": None}, {"limite": 11}):
            medir("buscar_puntos", bp({"consulta": q, **extra}), q)
    for to in nav.tos:
        q = consultas[len(to) % len(consultas)]
        out = medir("buscar_puntos", bp({"consulta": q or "plazo", "to": to}), to)
        filas = [l for l in out.splitlines()[2:] if re.match(r"^\d+ \| ", l)]
        filtros_ok &= all(l.split(" | ")[1].split("::", 1)[0] == to for l in filas)
        nodos_ok &= all(l.split(" | ")[4].count(" · ") <= 3 for l in filas)
        secc = nav.puntos[to]["hijos"][0]
        out = medir("buscar_puntos", bp({"consulta": "plazo", "punto": secc}), secc)
        sub = nav._subarbol(secc)
        filtros_ok &= all(l.split(" | ")[1] in sub for l in out.splitlines()[2:] if re.match(r"^\d+ \| ", l))
    for t in terminos[::max(1, len(terminos) // 25)]:
        out = medir("buscar_puntos", bp({"consulta": t, "termino": t}), t)
        qt = set(FN.BM.analizar(t))
        filtros_ok &= all(any(qt <= s for s in nav.terminos.get(l.split(" | ")[1], []))
                          for l in out.splitlines()[2:] if re.match(r"^\d+ \| ", l))
    for q in ("plazo máximo de exportación", "excepción a la prohibición"):
        determinista &= bp({"consulta": q}) == bp({"consulta": q})
        # el orden es el de la fusión RRF con k = 60
        terms = FN.BM.analizar(q)
        bm = nav.buscador.puntajes(terms)
        cand = list(range(len(nav.ids_docs)))
        rb = sorted((i for i in cand if bm.get(i, 0) > 0), key=lambda i: (-bm[i], nav.ids_docs[i]))
        rd = []
        if nav.denso is not None:
            S = nav.denso.puntajes(q)
            rd = sorted(cand, key=lambda i: (-float(S[i]), nav.ids_docs[i]))
        s = {}
        for rk in (rb, rd):
            for r, i in enumerate(rk, 1):
                s[i] = s.get(i, 0.0) + 1.0 / (60 + r)
        esperado = [nav.ids_docs[i] for i in sorted(s, key=lambda i: (-s[i], nav.ids_docs[i]))[:8]]
        obtenido = [l.split(" | ")[1] for l in bp({"consulta": q}).splitlines()[2:]
                    if re.match(r"^\d+ \| ", l)]
        rrf_ok &= obtenido == esperado[:len(obtenido)] and len(obtenido) > 0
    R.caso("T3 buscar_puntos: filtros por TO, punto y termino respetados", filtros_ok)
    R.caso("T3 buscar_puntos: a lo sumo 3 nodos por fila", nodos_ok)
    R.caso("T3 buscar_puntos: misma llamada, misma salida", determinista)
    R.caso(f"T3 buscar_puntos: orden de la fusión RRF k={FN.RRF_K} "
           f"({'BM25 + denso' if nav.denso is not None else 'solo BM25'})", rrf_ok and FN.RRF_K == 60)
    return llamadas


# --------------------------------------------------------------------------- #
# T11: `desde` en buscar_puntos (U-NAV-DESDE)                                  #
# --------------------------------------------------------------------------- #
def _filas(out: str) -> list[tuple[int, str]]:
    """(número, punto) de cada fila de una salida de buscar_puntos."""
    return [(int(l.split(" | ")[0]), l.split(" | ")[1]) for l in out.splitlines()[2:] if re.match(r"^\d+ \| ", l)]


def _pie(out: str) -> int:
    """Los puntos que, según el pie, no entraron en el tope (0 si no hay pie)."""
    m = re.search(r"^\((\d+) puntos más no entran en el tope", out, flags=re.M)
    return int(m.group(1)) if m else 0


def _fusion_entera(nav, consulta: str, to: str | None = None) -> list[str]:
    """La fusión RRF (k = 60) entera sobre los puntos del TO (o todos), escrita aparte como la de T3."""
    cand = [i for i in range(len(nav.ids_docs)) if to is None or nav.ids_docs[i].split("::", 1)[0] == to]
    terms = FN.BM.analizar(consulta)
    bm = nav.buscador.puntajes(terms) if terms else {}
    rb = sorted((i for i in cand if bm.get(i, 0) > 0), key=lambda i: (-bm[i], nav.ids_docs[i]))
    rd = []
    if nav.denso is not None and consulta.strip() and cand:
        S = nav.denso.puntajes(consulta)
        rd = sorted(cand, key=lambda i: (-float(S[i]), nav.ids_docs[i]))
    s = {}
    for rk in (rb, rd):
        for r, i in enumerate(rk, 1):
            s[i] = s.get(i, 0.0) + 1.0 / (60 + r)
    return [nav.ids_docs[i] for i in sorted(s, key=lambda i: (-s[i], nav.ids_docs[i]))]


def casos_desde(nav, R: "Resultado", llamadas_bp: list[tuple[dict, str]]) -> None:
    """T11. Sus salidas no pasan por medir(): no cambian el sha256 de las salidas ni las cuentas de T2; el tope de
    buscar_puntos se controla acá, sobre todas."""
    tope, largos = FN.TOPES["buscar_puntos"], []

    def bp(args: dict) -> str:
        out = FN.despachar(nav, "buscar_puntos", args)
        largos.append(len(out))
        return out
    hay_cla = all(k in nav.puntos for k in ("cla::6.5.5", "cla::6.5.5.4", "cla::6.5.5.5"))
    # desde=0: la salida sin desde, byte a byte, en cada llamada de T2/T3 y en el caso del borrador (con su pie)
    iguales = sum(bp({**args, "desde": 0}) == out for args, out in llamadas_bp)
    R.caso("T11 desde=0: la salida sin desde, byte a byte, en cada llamada de T2/T3", iguales == len(llamadas_bp),
           f"{iguales}/{len(llamadas_bp)}")
    if hay_cla:
        sin = [bp(args) for args in LLAMADAS_BORRADOR]
        con = [bp({**args, "desde": 0}) for args in LLAMADAS_BORRADOR]
        R.caso("T11 caso del borrador (sus 4 llamadas, la de limite=10 con su pie): desde=0 = sin desde",
               sin == con and _pie(sin[2]) > 0, f"pie con limite=10: «{sin[2].rpartition(chr(10))[2]}»")
    else:
        R.caso("T11 caso del borrador", False, "no están los puntos del caso en este grafo")
    # desde=k: las posiciones k a k + limite - 1 de la fusión entera
    tos_desde = (None, "cla") if hay_cla else (None,)
    pos_ok, num_ok, disj_ok, pag_ok, n = True, True, True, True, 0
    for q in CONSULTAS_DESDE:
        for to in tos_desde:
            esp = _fusion_entera(nav, q, to)
            base = {"consulta": q, **({"to": to} if to else {})}
            for lim in (3, 8, 10):
                p0 = {p for _, p in _filas(bp({**base, "limite": lim}))}
                for k in (1, 5, lim, 16):
                    out = bp({**base, "limite": lim, "desde": k})
                    f = _filas(out)
                    n += 1
                    pos_ok &= ([p for _, p in f] == esp[k:k + len(f)]
                               and len(f) + _pie(out) == min(lim, max(0, len(esp) - k)))
                    num_ok &= [x for x, _ in f] == list(range(k + 1, k + 1 + len(f))) and f" desde={k} · " in out.split("\n")[0]
                    if k >= lim:
                        disj_ok &= not ({p for _, p in f} & p0)
                # pedir desde = las filas ya mostradas recorre el ranking sin saltos (aunque el tope corte filas)
                vistos, d = [], 0
                while len(vistos) < 30:
                    out = bp({**base, "limite": lim, "desde": d})
                    f = _filas(out)
                    if not f:
                        break
                    vistos += [p for _, p in f]
                    d += len(f)
                    pag_ok &= _desde_del_pie(out) in (None, d)     # el pie, si está, dice desde = d
                pag_ok &= vistos == esp[:len(vistos)] and len(vistos) >= min(30, len(esp))
    R.caso("T11 desde=k: las posiciones k a k + limite - 1 de la fusión entera (las que no entran, en el pie)", pos_ok,
           f"{n} llamadas")
    R.caso("T11 desde=k: filas numeradas por su lugar en el ranking y desde=k en el encabezado", num_ok)
    R.caso("T11 desde=k con k >= limite: ninguna fila de desde=0", disj_ok)
    R.caso("T11 desde = las filas ya mostradas: recorre el ranking sin saltos ni repetidos", pag_ok)
    # el pie: dice desde = la primera fila que no entró, y con ese desde la página siguiente empieza ahí
    con_pie, sigue_ok, viejo_ok = 0, True, True
    for args, out in llamadas_bp:
        k = _desde_del_pie(out)
        if k is None:
            continue
        con_pie += 1
        f0 = _filas(out)
        f1 = _filas(bp({**args, "desde": k}))
        sigue_ok &= (k == (f0[-1][0] if f0 else 0) and bool(f1) and f1[0][0] == k + 1
                     and not {p for _, p in f0} & {p for _, p in f1})
        viejo_ok &= len(con_el_pie_de_n5(out)[0]) >= len(out)
    R.caso("T11 el pie: con el desde que dice se ve la fila siguiente, sin saltos ni repetidos", sigue_ok and con_pie > 0,
           f"{con_pie} salidas de T2/T3 con el pie")
    R.caso("T11 el pie nuevo no es más largo que el de N5, y el grafo servido tiene menos de 100.000 puntos",
           viejo_ok and len(nav.ids_docs) < 100_000, f"{len(nav.ids_docs)} puntos")
    if hay_cla:
        esp = _fusion_entera(nav, CASO_BORRADOR, "cla")
        f8 = {p: x for x, p in _filas(bp({"consulta": CASO_BORRADOR, "to": "cla", "desde": 8}))}
        f0 = {p for _, p in _filas(bp({"consulta": CASO_BORRADOR, "to": "cla"}))}
        buscados = ["cla::6.5.5.4", "cla::6.5.5.5"]
        R.caso("T11 caso del borrador: con to=cla y desde=8 aparecen cla::6.5.5.4 y cla::6.5.5.5",
               all(u in f8 and f8[u] == esp.index(u) + 1 for u in buscados) and not set(buscados) & f0,
               "lugar en la fusión: " + ", ".join(f"{u} {f8.get(u)}" for u in buscados))
    # desde más allá del final
    q_fin = {"consulta": CASO_BORRADOR, **({"to": "cla"} if hay_cla else {})}
    n_fin = len(_fusion_entera(nav, CASO_BORRADOR, "cla" if hay_cla else None))
    fin_ok = True
    for d in (n_fin, n_fin + 50, 10 ** 12):
        out = bp({**q_fin, "desde": d})
        fin_ok &= not _filas(out) and out.split("\n")[-1] == (
            f"No hay más resultados: el ranking tiene {n_fin} puntos (desde={min(d, 10 ** 9)}).")
    ultima = _filas(bp({**q_fin, "desde": n_fin - 1}))
    vacia = bp({"consulta": "", "desde": 3})
    fin_ok &= ([x for x, _ in ultima] == [n_fin]
               and vacia.split("\n")[-1] == "No hay más resultados: el ranking tiene 0 puntos (desde=3).")
    R.caso("T11 desde más allá del final: lo dice, con el largo del ranking, y no falla", fin_ok, f"ranking de {n_fin} puntos")
    # validación: un entero de 0 o más
    base = {"consulta": CONSULTAS_DESDE[0]}
    ref = bp(base)
    val_ok = (all(bp({**base, "desde": v}) == ref for v in (-1, -100, "x", "", None, [], {}))
              and bp({**base, "desde": 2.9}) == bp({**base, "desde": 2})
              and bp({**base, "desde": "3"}) == bp({**base, "desde": 3}))
    R.caso("T11 desde inválido o negativo vale 0; 2.9 vale 2 y «3», 3", val_ok)
    d = FN.TOOLS_NAV_POR_NOMBRE["buscar_puntos"]
    R.caso("T11 definición: desde en el esquema (entero, opcional) y su texto en la descripción",
           d["input_schema"]["properties"].get("desde") == PROPIEDAD_DESDE and "desde" not in d["input_schema"]["required"]
           and d["description"].endswith(" " + TEXTO_DESDE) and FN.TEXTO_DESDE == TEXTO_DESDE)
    R.caso("T11 tope de buscar_puntos en todas sus salidas", max(largos) <= tope,
           f"{len(largos)} llamadas; máximo {max(largos)}/{tope}")


# --------------------------------------------------------------------------- #
# Modo --sin-neo4j (U-NAV-DESDE)                                               #
# --------------------------------------------------------------------------- #
class _DriverSinNeo4j:
    """En lugar del driver de Neo4j: responde solo las tres consultas del constructor del Navegador, desde el índice
    por punto: KG_Meta (el kg_sha256 del manifiesto, que T0 compara con el kg.json; props_aristas vacío), la cuenta
    de nodos (la del manifiesto) y los grados (ninguno: sin aristas no hay hubs). Cualquier otra consulta falla, así
    ninguna herramienta que lee aristas corre en este modo."""

    class _Resultado:
        def __init__(self, fila=None, filas=None):
            self._fila, self._filas = fila, filas or []

        def single(self):
            return self._fila

        def data(self):
            return self._filas

    def __init__(self, indice_dir: Path, kg_sha256_esperado: str | None):
        man = json.loads((indice_dir / "manifiesto.json").read_text(encoding="utf-8"))
        if kg_sha256_esperado is not None and man["kg_sha256"] != kg_sha256_esperado:
            raise SystemExit("ABORTO: el índice por punto no es el del grafo de la config (kg_sha256)")
        self.meta = {"props_aristas": [], "kg_sha256": man["kg_sha256"]}
        self.n_nodos = man["n_nodos"]

    def session(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, cypher: str, **params):
        if cypher.startswith("MATCH (m:KG_Meta"):
            return self._Resultado({"p": self.meta})
        if "RETURN count(n) AS c" in cypher:
            return self._Resultado({"c": self.n_nodos})
        if "COUNT {" in cypher:
            return self._Resultado(filas=[])
        raise RuntimeError("selftest --sin-neo4j: esta consulta necesita Neo4j")


def navegador_sin_neo4j(config: dict) -> FN.Navegador:
    """El Navegador de la config, con sus controles del índice por punto, del denso y de rrf_k
    (servidor_mcp_kg_nav.abrir_navegador), sobre _DriverSinNeo4j y sin hubs_esperados."""
    driver = _DriverSinNeo4j((AQUI / config["indice_puntos"]).resolve(), config.get("kg_sha256_esperado"))
    return SN.abrir_navegador({**config, "hubs_esperados": None}, SimpleNamespace(driver=driver))


def main_sin_neo4j(a, config: dict, R: "Resultado", t_ini: float) -> int:
    """T0, T1, la parte de buscar_puntos de T2 y T3, y T11; lo demás lee Neo4j o el servidor y no corre."""
    nav = navegador_sin_neo4j(config)
    indice_dir = (AQUI / config["indice_puntos"]).resolve()
    print(f"== selftest familias nav · {config['grafo']} · modo {'contenido' if a.contenido else 'cuentas'} · "
          "sin Neo4j (T0, T1, buscar_puntos y T11)")
    v = IP.verificar(indice_dir)
    R.caso("T0 índice por punto re-derivado: mismos bytes", all(v.values()), json.dumps(v))
    defs = {t["name"]: t for t in FN.TOOLS_NAV}
    ok = set(defs) == set(FIRMAS_N2) and all(
        defs[n]["familia"] == f and list(defs[n]["input_schema"]["properties"]) == args
        and defs[n]["input_schema"]["required"] == req for n, (f, args, req) in FIRMAS_N2.items())
    R.caso("T1 firmas de N2 (nombre, familia, argumentos, requeridos)", ok)
    puntos = [k for k, p in nav.puntos.items() if p["tipo"] != "to"]
    excedidos = []

    def medir(tool: str, out: str, args) -> str:
        R.salida(tool, out)
        if len(out) > FN.TOPES[tool]:
            excedidos.append((tool, len(out), args if a.contenido else "—"))
        return out
    llamadas_bp = casos_buscar_puntos(nav, R, medir, puntos)
    R.caso("T2 topes de N2 en las salidas de buscar_puntos", not excedidos,
           f"llamadas={sum(len(v) for v in R.largos.values())}; máximo buscar_puntos "
           f"{max(R.largos['buscar_puntos'])}/{FN.TOPES['buscar_puntos']}"
           + (f"; excedidos={excedidos[:3]}" if excedidos else ""))
    casos_desde(nav, R, llamadas_bp)
    if nav.denso is not None:
        nav.denso.cerrar()
    n_fallas = sum(1 for x in R.casos if not x["ok"])
    resumen = {"grafo": config["grafo"], "modo": "contenido" if a.contenido else "cuentas", "sin_neo4j": True,
               "no_corren": "T2 de ver_punto, ver_remisiones, indice_to y la familia 5; T4 a T10 (leen Neo4j o el servidor)",
               "casos": R.casos, "fallas": n_fallas,
               "llamadas_por_herramienta": {t: len(v) for t, v in sorted(R.largos.items())},
               "maximo_por_herramienta": {t: max(v) for t, v in sorted(R.largos.items())},
               "topes": FN.TOPES, "sha256_salidas": R.h.hexdigest(), "sha256_salidas_de": "buscar_puntos (T2/T3)",
               "sha256_salidas_con_el_pie_de_n5": R.h_n5.hexdigest(), "salidas_con_el_pie_nuevo": R.n_pie,
               "segundos": round(time.time() - t_ini, 1), "denso": nav.denso is not None}
    if a.salida:
        a.salida.parent.mkdir(parents=True, exist_ok=True)
        a.salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSELFTEST familias nav ({config['grafo']}, sin Neo4j): {'OK' if n_fallas == 0 else f'{n_fallas} FALLAS'} · "
          f"{sum(len(v) for v in R.largos.values())} salidas medidas · sha256 {R.h.hexdigest()[:16]} · "
          f"{resumen['segundos']} s · con el pie de N5: sha256 {R.h_n5.hexdigest()[:16]} · {R.n_pie} con el pie nuevo")
    return 0 if n_fallas == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--contenido", action="store_true")
    g.add_argument("--cuentas", action="store_true")
    ap.add_argument("--salida", type=Path)
    ap.add_argument("--sin-neo4j", action="store_true")
    a = ap.parse_args()
    R = Resultado(a.contenido)
    t_ini = time.time()
    config, _ = cargar_config(a.config.resolve())
    if a.sin_neo4j:
        return main_sin_neo4j(a, config, R, t_ini)
    index, _fuente = BASE.abrir_backend(config)
    nav = SN.abrir_navegador(config, index)
    indice_dir = (AQUI / config["indice_puntos"]).resolve()
    print(f"== selftest familias nav · {config['grafo']} · modo {'contenido' if a.contenido else 'cuentas'}")

    # T0
    v = IP.verificar(indice_dir)
    R.caso("T0 índice por punto re-derivado: mismos bytes", all(v.values()), json.dumps(v))
    # T1
    defs = {t["name"]: t for t in FN.TOOLS_NAV}
    ok = set(defs) == set(FIRMAS_N2) and all(
        defs[n]["familia"] == f and list(defs[n]["input_schema"]["properties"]) == args
        and defs[n]["input_schema"]["required"] == req for n, (f, args, req) in FIRMAS_N2.items())
    R.caso("T1 firmas de N2 (nombre, familia, argumentos, requeridos)", ok)

    puntos = [k for k, p in nav.puntos.items() if p["tipo"] != "to"]
    excedidos = []

    def medir(tool: str, out: str, args, max_nodos: int = 15) -> str:
        tope, hoy = FN.TOPES[tool], None
        if tool == "ver_punto":   # U-VERPUNTO: el tope de su punto, y la salida con el texto de hoy (args es el punto)
            tope, hoy = FN.tope_ver_punto(nav._texto_propio(args)), con_el_texto_de_hoy(nav, args, out)
        R.salida(tool, out, hoy, max_nodos)
        if len(out) > tope:
            excedidos.append((tool, len(out), args if a.contenido else "—"))
        return out

    # T2 + T4 + T5: ver_punto y ver_remisiones sobre todos los puntos
    intro_ok, repetidos = True, 0
    for k in puntos:
        out = medir("ver_punto", FN.despachar(nav, "ver_punto", {"punto": k}), k)
        if nav.puntos[k]["intro"] and FN.despachar(nav, "ver_punto", {"punto": k + "::intro"}) != out:
            intro_ok = False
        if len(nav.puntos[k]["nodos"]) > 15:
            medir("ver_punto", FN.despachar(nav, "ver_punto", {"punto": k, "max_nodos": 25}), k, 25)
        r = medir("ver_remisiones", FN.despachar(nav, "ver_remisiones", {"punto": k}), k)
        filas = [tuple(l.split(" | ")[:2]) for l in r.splitlines() if l.startswith(("cita | ", "lo_citan | "))]
        repetidos += len(filas) - len(set(filas))
    for k in puntos[::10]:
        medir("ver_remisiones", FN.despachar(nav, "ver_remisiones", {"punto": k, "saltos": 2, "limite": 20}), k)
    inexistente = FN.despachar(nav, "ver_punto", {"punto": "zz::9.9.9"})
    R.caso("T4 ver_punto: «::intro» = el punto, en todos los puntos con intro", intro_ok)
    R.caso("T4 ver_punto: aviso de punto inexistente", inexistente.startswith("ver_punto: no existe el punto"))
    R.caso("T5 ver_remisiones: una fila por punto y dirección", repetidos == 0, f"repetidos={repetidos}")
    # indice_to
    for to in nav.tos:
        medir("indice_to", FN.despachar(nav, "indice_to", {"to": to}), to)
        medir("indice_to", FN.despachar(nav, "indice_to", {"to": to, "niveles": 3, "limite": 150}), to)
    for k in puntos:
        if nav.puntos[k]["hijos"]:
            for niv in (1, 2, 3):
                medir("indice_to", FN.despachar(nav, "indice_to", {"to": nav.puntos[k]["to"], "desde": k,
                                                                   "niveles": niv}), k)
    # familia 5
    ids = sorted(nav.grado)
    muestra = sorted(nav.hubs) + ids[::25]
    pag_ok, hub_ok, hub_filtro_ok = True, True, True
    for nid in muestra:
        medir("tipos_de_relacion", FN.despachar(nav, "tipos_de_relacion", {"id": nid}), nid)
        for d in ("salientes", "entrantes"):
            rels = sorted({f["rel"] for f in nav._vecinos(nid, None, d)})
            for rel in rels[:3]:
                out = medir("vecinos_por_relacion", FN.despachar(nav, "vecinos_por_relacion",
                                                                  {"id": nid, "relacion": rel, "direccion": d}), nid)
                if nid in nav.hubs:
                    hub_ok &= "no se listan sus vecinos sin filtro" in out
                    to0 = nav._to_de(nav._vecinos(nid, rel, d)[0]["v"])
                    if to0 in nav.tos:
                        o2 = medir("vecinos_por_relacion", FN.despachar(nav, "vecinos_por_relacion", {
                            "id": nid, "relacion": rel, "direccion": d, "to": to0}), nid)
                        hub_filtro_ok &= "no se listan" not in o2 and any(
                            " | " in l and not l.startswith("(") for l in o2.splitlines()[2:])
                else:
                    tot = len(nav._vecinos(nid, rel, d))
                    if tot > 3:
                        p1 = FN.despachar(nav, "vecinos_por_relacion", {"id": nid, "relacion": rel, "direccion": d,
                                                                        "limite": 3})
                        p2 = FN.despachar(nav, "vecinos_por_relacion", {"id": nid, "relacion": rel, "direccion": d,
                                                                        "limite": 3, "desde": 3})
                        f1 = [l for l in p1.splitlines()[2:] if not l.startswith("(")]
                        f2 = [l for l in p2.splitlines()[2:] if not l.startswith("(")]
                        todos = [l for l in FN.despachar(nav, "vecinos_por_relacion", {
                            "id": nid, "relacion": rel, "direccion": d, "limite": 6}).splitlines()[2:]
                            if not l.startswith("(")]
                        pag_ok &= (f1 + f2)[:len(todos)] == todos[:len(f1 + f2)]
    R.caso("T6 hub sin filtro: no lista", hub_ok, f"hubs={len(nav.hubs)} umbral={nav.umbral_hub}")
    R.caso("T6 hub con filtro de TO: lista", hub_filtro_ok)
    R.caso("T6 paginación con desde", pag_ok)
    llamadas_bp = casos_buscar_puntos(nav, R, medir, puntos)
    R.caso("T2 topes de N2 en todas las salidas (ver_punto, el de su punto)", not excedidos,
           f"llamadas={sum(len(v) for v in R.largos.values())}; máximo por herramienta: "
           + ", ".join(f"{t} {max(v)}/{FN.TOPES[t]}" if t != "ver_punto" else
                       f"{t} {max(v)} (tope de su punto, base {FN.TOPES[t]})" for t, v in sorted(R.largos.items()))
           + (f"; excedidos={excedidos[:3]}" if excedidos else ""))
    # T7
    m = FN.marcas_arista
    ok7 = (m("remite_a", {"no_verificada_e3": True}) == ["no verificada"]
           and m("limita", {"cola_humana": "true", "estado_e3": "x"}) == ["cola humana"]
           and m("aplica_a", {"rol_fuente": "derivada_del_alcance"}) == ["sujeto derivado"]
           and m("establecida_en", {"rol_fuente": "derivada_de_procedencia"}) == []
           and m("aplica_a", {}) == [])
    R.caso("T7 marcas de las aristas", ok7)
    # T8
    defi = [n for n in nav.puntos.get("cla::5.1.1", {}).get("nodos", []) if nav.nodos[n]["type"] == "Definicion"]
    exc = [n for n in nav.puntos.get("cla::5.1.1.1", {}).get("nodos", []) if nav.nodos[n]["type"] == "Excepcion"]
    if defi and exc:
        o1 = FN.despachar(nav, "ver_punto", {"punto": nav.nodos[defi[0]]["puntos"][0]})
        hijo = "5.1.1.1 · " in o1
        o2 = FN.despachar(nav, "ver_punto", {"punto": "cla::5.1.1.1"})
        R.caso("T8 caso de la jerarquía: Definicion de cla::5.1.1 -> Excepcion de cla::5.1.1.1 en 2 llamadas",
               defi[0] in o1 and hijo and all(e in o2 for e in exc), f"excepciones={len(exc)}")
    else:
        R.caso("T8 caso de la jerarquía", False, "no están los nodos del caso en este grafo")
    # T9
    claves9 = ["docvig::2.1.1.1", "docvig::2.1.2.1", "docvig::2.2.1.1"]
    if all(k in nav.puntos for k in claves9):
        anc = [FN.despachar(nav, "ver_punto", {"punto": k}).splitlines()[1] for k in claves9]
        R.caso("T9 hallazgo 2.7: tres puntos con el mismo texto se distinguen por sus ancestros", len(set(anc)) == 3)
    # T10
    from cliente_falso import ClienteFalso
    env = {k: v for k, v in os.environ.items() if k in ("NEO4J_URI", "BANCO_VENV_VECTOR")}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "BANCO_LOG_R1": os.environ.get("BANCO_LOG_R1", os.devnull)})
    cmd = [sys.executable, "-B", str(AQUI / "servidor_mcp_kg_nav.py"), "--config", str(a.config.resolve())]
    llamadas = [("buscar_nodos", {"consulta": "plazo"}), ("buscar_nodos", {"consulta": "excepción", "limite": 3}),
                ("ver_nodo", {"id": ids[0]}), ("ver_vecinos", {"id": ids[0]}),
                ("ver_vecinos", {"id": sorted(nav.hubs)[0], "direccion": "entrantes"}), ("ver_nodo", {"id": "x"})]
    nuevas = [("buscar_puntos", {"consulta": "plazo", "limite": 3}), ("ver_punto", {"punto": puntos[0]}),
              ("ver_remisiones", {"punto": puntos[0]}), ("indice_to", {"to": nav.tos[0]}),
              ("tipos_de_relacion", {"id": ids[0]}),
              ("vecinos_por_relacion", {"id": ids[0], "relacion": "x", "direccion": "salientes"})]
    with ClienteFalso(cmd=cmd, env=env, cwd=AQUI.parents[3]) as c:
        tools = c.listar_tools()
        nombres = [t["name"] for t in tools]
        esperadas = [t["name"] for t in SN.tools_de(config.get("familias", []))]
        defs_ok = nombres == esperadas and all(
            (t["description"], t["input_schema"]) == (BASE.TOOLS_V1[t["name"]]["description"],
                                                      BASE.TOOLS_V1[t["name"]]["input_schema"])
            for t in tools if t["name"] in BASE.TOOLS_V1)
        base_ok = all(c.llamar(n, args) == serializar_payload(BASE.despachar(index, n, args)) for n, args in llamadas)
        nav_ok = all(c.llamar(n, args) == FN.despachar(nav, n, args) for n, args in nuevas)
    R.caso("T10 servidor: herramientas listadas (las 3 de hoy, como harness.TOOLS, y las de la config)", defs_ok,
           f"{len(nombres)} herramientas")
    R.caso("T10 servidor: las 3 de hoy, byte a byte iguales al servidor de hoy", base_ok)
    R.caso("T10 servidor: las nuevas, iguales al Navegador directo", nav_ok)
    casos_desde(nav, R, llamadas_bp)
    # T12 (U-VERPUNTO): el texto propio entero en ver_punto, en cada punto con max_nodos 15 y 25
    uso = lambda lineas: sum(len(x) + 1 for x in lineas)  # noqa: E731
    n12, largos12, cambian12 = 0, 0, {15: 0, 25: 0}
    texto_ok, hoy_ok, tope_ok = True, True, True
    for k in puntos:
        texto = nav._texto_propio(k)
        tope_k = FN.tope_ver_punto(texto)
        tope_ok &= tope_k == (FN.TOPES["ver_punto"] + uso([f"Texto ({len(texto)} caracteres):", texto])
                              - uso(texto_de_hoy(texto)) if texto else FN.TOPES["ver_punto"])
        for mn in (15, 25):
            out = FN.despachar(nav, "ver_punto", {"punto": k, "max_nodos": mn})
            n12 += 1
            if len(texto) > 1500:
                largos12 += 1
                lineas = out.split("\n", 4)
                texto_ok &= (len(lineas) == 5 and lineas[3] == f"Texto ({len(texto)} caracteres):"
                             and lineas[4][:len(texto)] == texto and lineas[4][len(texto):].startswith("\nNodos"))
            hoy = con_el_texto_de_hoy(nav, k, out)
            hoy_ok &= hoy is not None and (hoy != out) == (len(texto) > 1500)
            tope_ok &= len(out) <= tope_k
            cambian12[mn] += hoy is not None and hoy != out
    R.caso("T12 ver_punto: en los puntos de más de 1.500 caracteres, «Texto (N caracteres):» y el texto propio entero "
           "hasta la sección siguiente", texto_ok, f"{largos12} salidas de {n12}")
    R.caso("T12 ver_punto: la sección del texto de hoy se restituye en todas las salidas y cambia solo en los puntos "
           "largos", hoy_ok, f"cambian con max_nodos 15: {cambian12[15]}; con 25: {cambian12[25]}")
    R.caso("T12 ver_punto: el tope de cada punto es 5.000 más lo que la sección nueva usa de más que la de hoy, y "
           "ninguna salida lo pasa", tope_ok, f"{len(puntos)} puntos")

    if nav.denso is not None:
        nav.denso.cerrar()
    n_fallas = sum(1 for x in R.casos if not x["ok"])
    modo = "contenido" if a.contenido else "cuentas"
    resumen = {"grafo": config["grafo"], "modo": modo,
               "casos": R.casos, "fallas": n_fallas,
               "llamadas_por_herramienta": {t: len(v) for t, v in sorted(R.largos.items())},
               "maximo_por_herramienta": {t: max(v) for t, v in sorted(R.largos.items())},
               "topes": FN.TOPES, "sha256_salidas": R.h.hexdigest(), "segundos": round(time.time() - t_ini, 1),
               "sha256_salidas_con_el_pie_de_n5": R.h_n5.hexdigest(), "salidas_con_el_pie_nuevo": R.n_pie,
               "sha256_salidas_con_el_texto_de_hoy": R.h_hoy.hexdigest(),
               "sha256_salidas_con_el_texto_de_hoy_y_el_pie_de_n5": R.h_hoy_n5.hexdigest(),
               "salidas_de_ver_punto_que_cambian": {modo: dict(sorted(R.cambian.items()))},
               "denso": nav.denso is not None}
    if a.salida:
        a.salida.parent.mkdir(parents=True, exist_ok=True)
        a.salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSELFTEST familias nav ({config['grafo']}): {'OK' if n_fallas == 0 else f'{n_fallas} FALLAS'} · "
          f"{sum(len(v) for v in R.largos.values())} salidas medidas · sha256 {R.h.hexdigest()[:16]} · "
          f"{resumen['segundos']} s · con el pie de N5: sha256 {R.h_n5.hexdigest()[:16]} · {R.n_pie} con el pie nuevo"
          f" · con el texto de hoy: sha256 {R.h_hoy.hexdigest()[:16]}, y con el pie de N5 {R.h_hoy_n5.hexdigest()[:16]}"
          f" · cambian {dict(sorted(R.cambian.items()))}")
    return 0 if n_fallas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
