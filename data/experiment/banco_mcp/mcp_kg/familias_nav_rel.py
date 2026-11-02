#!/usr/bin/env python3
"""familias_nav_rel.py — N7c, etapa C1: la sección «Puntos relacionados» al final de la salida de ver_punto (familia 2),
en un archivo aparte. Importa familias_nav_cand.py sin cambiarlo: NavegadorRel hereda de NavegadorCand y redefine solo
ver_punto, que devuelve la salida de NavegadorCand.ver_punto tal cual y, al final, la sección. La descripción de
ver_punto, su esquema de entrada y las otras nueve herramientas no cambian (decisión C-1, opción (a)): la salida
anterior es un prefijo exacto de la nueva.

La sección:
  - los puntos: los otros puntos del índice por punto (no el mismo; sí sus ancestros y sus descendientes) unidos al
    punto por una arista de los tipos de GRUPOS_RELACION (decisión C-2: remisión, condición y excepción, sin
    aplica_a). Un punto p está unido al punto k si una arista de esos tipos sale de un nodo de k y llega a un nodo de p
    («sale») o sale de un nodo de p y llega a un nodo de k («entra»). Los nodos de un punto son los de `nodos` en
    puntos.json, los que lista ver_punto; los puntos de un nodo, los puntos que lo listan;
  - lo que no entra: ningún otro tipo de relación, y dos clases de nodos, en cualquiera de las dos puntas de la arista:
      - los contenedores, con la regla del §2 de la enmienda 1 de la atribución
        (ev2_reporte/enmienda1_regla_atribucion_navegacion.md): los nodos que portan más de CONTENEDOR_MAX_ANCLAS claves
        distintas (resolucion.py) y los de los tipos de indice_puntos.TIPOS_FUERA_DE_PUNTO (`TextoOrdenado`), importados
        como en atribucion_fallas_nav.py. Las claves de un nodo son las de `puntos` en nodos.json:
        indice_puntos.cargar_nodos las arma con la misma regla que AnclaIndexBanco (base_punto de cada procedencia con
        `to` y `punto`, sin repetir);
      - los hubs: los que calcula familias_nav.Navegador al arrancar (`self.hubs`, la regla de la familia 5: el grado
        en el 1 % más alto del grafo servido), heredados por NavegadorCand;
  - por punto, un renglón: «to::punto | título | relación | dirección | aristas», con el grupo o los grupos (en el orden
    de GRUPOS_RELACION), la dirección («sale», «entra» o «las dos») y cuántas aristas distintas lo unen. Ningún texto
    del punto;
  - el orden: por la cantidad de aristas, de mayor a menor, y después por la clave `to::punto`;
  - el tope: hasta TOPE_RELACIONADOS puntos (decisión C-3). Si hay más, el pie PIE_RELACIONADOS; si no hay ninguno, la
    sección es SIN_RELACIONADOS;
  - un punto que no existe: la salida de NavegadorCand.ver_punto (su aviso), sin sección.
Las aristas se leen de Neo4j en cada llamada (dos consultas de solo lectura, una por dirección).
"""
from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SINTETICAS_DIR = AQUI.parents[1] / "exploracion" / "sinteticas"
for _p in (str(AQUI), str(SINTETICAS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import familias_nav_cand as FNC  # noqa: E402  (sin cambios)
from resolucion import CONTENEDOR_MAX_ANCLAS  # noqa: E402  (sintéticas, sin editar: el umbral del §2, como en atribucion_fallas_nav.py)

FN = FNC.FN
IP = FN.IP

# Decisión C-2: los tipos de relación de la sección, en tres grupos y en este orden.
GRUPOS_RELACION = (("remisión", ("remite_a",)),
                   ("condición", ("condicion_de", "condiciona", "limita", "requiere")),
                   ("excepción", ("exceptua", "exceptua_obligacion")))
GRUPO_DE = {t: g for g, ts in GRUPOS_RELACION for t in ts}
TIPOS_RELACIONADOS = tuple(GRUPO_DE)
TOPE_RELACIONADOS = 10   # decisión C-3
TITULO_RELACIONADOS = "Puntos relacionados ({m} de {n}; punto | título | relación | dirección | aristas):"
PIE_RELACIONADOS = "y {n} puntos más: ver_remisiones o vecinos_por_relacion"
SIN_RELACIONADOS = "Puntos relacionados: ninguno"
DIRECCIONES = {frozenset({"sale"}): "sale", frozenset({"entra"}): "entra", frozenset({"sale", "entra"}): "las dos"}


class NavegadorRel(FNC.NavegadorCand):
    """El NavegadorCand con la sección «Puntos relacionados» al final de ver_punto; lo demás, heredado sin cambios."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contenedores = {nid for nid, nd in self.nodos.items()
                             if len(nd["puntos"]) > CONTENEDOR_MAX_ANCLAS or nd["type"] in IP.TIPOS_FUERA_DE_PUNTO}
        self.puntos_del_nodo: dict[str, list[str]] = {}
        for clave, p in self.puntos.items():
            if p["tipo"] == "to":
                continue
            for nid in p["nodos"]:
                self.puntos_del_nodo.setdefault(nid, []).append(clave)

    def _fuera(self, nid: str) -> bool:
        return nid in self.contenedores or nid in self.hubs

    def relacionados(self, k: str) -> list[tuple[str, list[str], str, int]]:
        """Todos los puntos unidos a k, sin tope, en el orden de la sección: (clave, grupos, dirección, aristas)."""
        propios = [nid for nid in self.puntos[k]["nodos"] if not self._fuera(nid)]
        if not propios:
            return []
        L = self.label
        with self.driver.session() as s:
            sale = s.run(f"MATCH (a:`{L}`)-[r]->(b:`{L}`) WHERE a.id IN $ids AND type(r) IN $tipos "
                         "RETURN elementId(r) AS r, type(r) AS rel, b.id AS v", ids=propios,
                         tipos=list(TIPOS_RELACIONADOS)).data()
            entra = s.run(f"MATCH (b:`{L}`)-[r]->(a:`{L}`) WHERE a.id IN $ids AND type(r) IN $tipos "
                          "RETURN elementId(r) AS r, type(r) AS rel, b.id AS v", ids=propios,
                          tipos=list(TIPOS_RELACIONADOS)).data()
        por: dict[str, dict] = {}
        for sentido, filas in (("sale", sale), ("entra", entra)):
            for f in filas:
                if self._fuera(f["v"]):
                    continue
                for p in self.puntos_del_nodo.get(f["v"], []):
                    if p == k:
                        continue
                    g = por.setdefault(p, {"aristas": set(), "grupos": set(), "sentidos": set()})
                    g["aristas"].add(f["r"])
                    g["grupos"].add(GRUPO_DE[f["rel"]])
                    g["sentidos"].add(sentido)
        filas = [(p, [x for x, _ in GRUPOS_RELACION if x in g["grupos"]], DIRECCIONES[frozenset(g["sentidos"])],
                  len(g["aristas"])) for p, g in por.items()]
        return sorted(filas, key=lambda x: (-x[3], x[0]))

    def renglon_relacionado(self, fila: tuple[str, list[str], str, int]) -> str:
        p, grupos, direccion, n = fila
        return f"{p} | {FN._celda(self.puntos[p]['titulo'] or '—', 60)} | {', '.join(grupos)} | {direccion} | {n}"

    def seccion_relacionados(self, k: str) -> list[str]:
        filas = self.relacionados(k)
        if not filas:
            return [SIN_RELACIONADOS]
        lineas = [TITULO_RELACIONADOS.format(m=min(len(filas), TOPE_RELACIONADOS), n=len(filas))]
        lineas += [self.renglon_relacionado(f) for f in filas[:TOPE_RELACIONADOS]]
        if len(filas) > TOPE_RELACIONADOS:
            lineas.append(PIE_RELACIONADOS.format(n=len(filas) - TOPE_RELACIONADOS))
        return lineas

    def ver_punto(self, punto, max_nodos=15) -> str:
        out = super().ver_punto(punto, max_nodos)
        k = self.resolver_punto(punto)
        if k is None:
            return out
        return out + "\n" + "\n".join(self.seccion_relacionados(k))
