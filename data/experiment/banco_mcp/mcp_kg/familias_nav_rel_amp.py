#!/usr/bin/env python3
"""familias_nav_rel_amp.py — N7c+, etapa C2-bis: dos agregados más al final de la salida de ver_punto (familia 2), en
un archivo aparte. Importa familias_nav_rel.py sin cambiarlo: NavegadorRelAmp hereda de NavegadorRel y redefine solo
ver_punto, que devuelve la salida de NavegadorRel.ver_punto tal cual y, al final, en este orden, la sección de la familia
y la línea de la cita. La descripción de ver_punto, su esquema de entrada y las otras nueve herramientas no cambian
(decisión C-1, opción (a)): la salida de N7c es un prefijo exacto de la de N7c+.

La sección de la familia:
  - los puntos: los descendientes, hasta 3 niveles, del abuelo del punto en el árbol del índice por punto (`padre` e
    `hijos` de puntos.json, el árbol de la E0); si el abuelo es el TO, los de su padre, hasta 2 niveles; si el padre es
    el TO, ninguno. El recorrido es NavegadorCand._descendientes, el de ver_descendientes;
  - lo que no entra: el punto, sus ancestros, sus hijos y los puntos que la sección de puntos relacionados (N7c) lista
    dentro de su tope (familias_nav_rel.TOPE_RELACIONADOS);
  - el orden: por los pasos por el árbol a través del ancestro común más cercano (los que sube el punto más los que
    baja el otro), de menos a más, y después por la clave `to::punto`;
  - por punto, un renglón: «to::punto | título | parentesco», con el parentesco «hermano» (1 y 1 pasos), «sobrino»
    (1 y 2), «tío» (2 y 1), «primo» (2 y 2) o «a k pasos». Ningún texto del punto;
  - el tope: hasta TOPE_FAMILIA puntos. Si hay más, el pie PIE_FAMILIA; si no hay ninguno, SIN_FAMILIA.
La línea de la cita: LINEA_CITA, con el nombre del PDF de la cabecera de ver_punto (el archivo del TO en `archivo_a_to`
del manifiesto, con la misma regla que familias_nav.Navegador.ver_punto) y la unidad en la forma de la ubicación del
harness: «Punto n» para un punto numerado y «Sección n» para una sección (`Sn` en el índice), que
scripts/ucita2_indicadores_banco.py (partir_cita y normalizar_punto) lee como el mismo punto que la clave.
Un punto que no existe: la salida de NavegadorRel.ver_punto (su aviso), sin nada más.
La familia sale solo del índice por punto; los puntos de la sección de N7c se leen de Neo4j como en esa sección.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import familias_nav_rel as FNR  # noqa: E402  (N7c, sin cambios)

FNC, FN, IP = FNR.FNC, FNR.FN, FNR.IP

TOPE_FAMILIA = 10
TITULO_FAMILIA = "Puntos de la misma familia ({m} de {n}; punto | título | parentesco):"
PIE_FAMILIA = "y {n} puntos más: indice_to o ver_descendientes"
SIN_FAMILIA = "Puntos de la misma familia: ninguno"
LINEA_CITA = "Para citar este punto: {archivo} | {unidad}"
# (pasos que sube el punto, pasos que baja el otro) -> parentesco; lo demás, «a k pasos».
PARENTESCOS = {(1, 1): "hermano", (1, 2): "sobrino", (2, 1): "tío", (2, 2): "primo"}
_NUMERO = re.compile(r"\d+(?:\.\d+)*")
_SECCION = re.compile(r"S(\S+)")


def unidad_para_citar(unidad: str) -> str:
    """«Punto n» (U2.RE_PUNTO) para una unidad numerada y «Sección n» (U2.RE_SECCION, o la forma «Sección A» de
    ucita2_indicadores_banco para una sección que no es solo cifras) para `Sn`; otra unidad, tal cual."""
    if _NUMERO.fullmatch(unidad):
        return f"Punto {unidad}"
    m = _SECCION.fullmatch(unidad)
    return f"Sección {m.group(1)}" if m else unidad


class NavegadorRelAmp(FNR.NavegadorRel):
    """El NavegadorRel con la sección de la familia y la línea de la cita al final de ver_punto; lo demás, heredado."""

    def raiz_familia(self, k: str) -> tuple[str, int] | None:
        """(raíz, niveles) de la familia de k: (abuelo, 3), (padre, 2) si el abuelo es el TO, o None si el padre lo es."""
        padre = self.puntos[k]["padre"]
        if padre is None or self.puntos[padre]["tipo"] == "to":
            return None
        abuelo = self.puntos[padre]["padre"]
        if abuelo is None or self.puntos[abuelo]["tipo"] == "to":
            return padre, 2
        return abuelo, 3

    def _hacia_arriba(self, k: str, hasta: str) -> list[str]:
        """k y sus ancestros por `padre`, desde k, hasta `hasta` (incluido); a lo sumo cuatro pasos."""
        out = [k]
        while out[-1] != hasta and len(out) <= 4:
            padre = self.puntos[out[-1]]["padre"]
            if padre is None or padre not in self.puntos:
                break
            out.append(padre)
        return out

    def parentesco(self, k: str, c: str, raiz: str) -> tuple[int, str]:
        """(pasos, parentesco) de c respecto de k, por el ancestro común más cercano dentro de la familia."""
        sube = {x: i for i, x in enumerate(self._hacia_arriba(k, raiz))}
        baja = self._hacia_arriba(c, raiz)
        j = next((i for i, x in enumerate(baja) if x in sube), None)
        s, b = (sube[baja[j]], j) if j is not None else (len(sube) - 1, len(baja) - 1)
        return s + b, PARENTESCOS.get((s, b), f"a {s + b} pasos")

    def familia(self, k: str) -> list[tuple[str, int, str]]:
        """Todos los puntos de la familia de k, sin tope, en el orden de la sección: (clave, pasos, parentesco)."""
        r = self.raiz_familia(k)
        if r is None:
            return []
        raiz, niveles = r
        fuera = {k, *self._ancestros(k), *self.puntos[k]["hijos"]}
        fuera |= {f[0] for f in self.relacionados(k)[:FNR.TOPE_RELACIONADOS]}
        filas = [(c, *self.parentesco(k, c, raiz)) for c in self._descendientes(raiz, niveles) if c not in fuera]
        return sorted(filas, key=lambda f: (f[1], f[0]))

    def renglon_familia(self, fila: tuple[str, int, str]) -> str:
        c, _, parentesco = fila
        return f"{c} | {FN._celda(self.puntos[c]['titulo'] or '—', 60)} | {parentesco}"

    def seccion_familia(self, k: str) -> list[str]:
        filas = self.familia(k)
        if not filas:
            return [SIN_FAMILIA]
        lineas = [TITULO_FAMILIA.format(m=min(len(filas), TOPE_FAMILIA), n=len(filas))]
        lineas += [self.renglon_familia(f) for f in filas[:TOPE_FAMILIA]]
        if len(filas) > TOPE_FAMILIA:
            lineas.append(PIE_FAMILIA.format(n=len(filas) - TOPE_FAMILIA))
        return lineas

    def archivo_de(self, k: str) -> str:
        """El nombre del PDF de la cabecera de ver_punto (familias_nav.Navegador.ver_punto, la misma regla)."""
        to = self.puntos[k]["to"]
        return next((a for a, t in self.archivo_a_to.items() if t == to), to)

    def linea_cita(self, k: str) -> str:
        return LINEA_CITA.format(archivo=self.archivo_de(k), unidad=unidad_para_citar(self.puntos[k]["unidad"]))

    def ver_punto(self, punto, max_nodos=15) -> str:
        out = super().ver_punto(punto, max_nodos)
        k = self.resolver_punto(punto)
        if k is None:
            return out
        return out + "\n" + "\n".join(self.seccion_familia(k) + [self.linea_cita(k)])
