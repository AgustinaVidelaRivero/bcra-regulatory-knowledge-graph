#!/usr/bin/env python3
"""familias_nav_cand.py — U-CAND-DESC, etapa a: la candidata `ver_descendientes` de la familia 2 (vista de punto), en
un archivo aparte. Importa familias_nav.py sin cambiarlo y le suma una herramienta; ningún servidor la sirve y ninguna
config la nombra.

| familia | herramienta | tope (caracteres) |
|---|---|---|
| 2 vista de punto | ver_descendientes(punto, niveles=2, desde=0) | 8.000 |

ver_descendientes da, en una sola llamada, el texto propio entero de cada descendiente del punto hasta `niveles` (de 1
a 3), en orden de lectura: el preorden del árbol del índice por punto (`hijos` de puntos.json), el mismo de
indice_puntos.orden_canonico. Con ver_punto, leer un subárbol lleva una llamada por punto. Cada descendiente va con su
posición, su unidad, su título y su cantidad de nodos; los nodos no se listan (para eso está ver_punto).
  - El texto propio es el de Navegador._texto_propio, sin cambios, con la cabecera de la sección del texto de ver_punto
    (familias_nav._lineas_texto).
  - `punto` se resuelve con Navegador.resolver_punto, como en ver_punto, y el aviso de un punto que no existe tiene su
    forma (con un TO, remite a indice_to). `niveles` y `desde` se normalizan con familias_nav._entero, como en
    indice_to y buscar_puntos: lo que no es un entero va al defecto y lo que está fuera de rango, a su borde.
  - Tope: si todo lo que falta desde `desde` entra, va todo. Si no, un descendiente que no entra entero no se corta:
    la llamada termina antes de él y el pie (PIE_VER_DESCENDIENTES, con la forma de familias_nav.PIE_BUSCAR_PUNTOS)
    dice desde qué posición seguir. El lugar del pie se reserva al sumar cada descendiente, así la salida nunca pasa el
    tope. Si el primero de la llamada no entra solo, va con su texto cortado con «…», la marca de corte del texto de
    ver_punto
    (familias_nav._lineas_texto_cortado); su cabecera dice dónde se cortó y lo dice también un pie (PIE_TEXTO_CORTADO).
  - Ningún descendiente se repite y el recorrido siempre termina, aunque `hijos` traiga una clave repetida, una que no
    está en el índice o un ciclo: cada clave sale una sola vez, en el nivel de su distancia al punto, y ni el punto ni
    una clave que no está en el índice salen. Sobre un árbol (el índice por punto lo es) es el preorden de `hijos`.
"""
from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import familias_nav as FN  # noqa: E402  (sin cambios)

TOPE_VER_DESCENDIENTES = 8000
# El pie cuando el tope corta descendientes: k es la posición (desde 0) del primero que no entró, como en el pie de
# buscar_puntos (familias_nav.PIE_BUSCAR_PUNTOS).
PIE_VER_DESCENDIENTES = "({n} descendientes más no entran en el tope: pedí desde={k}, o leelos con ver_punto)"
# El pie de un texto que no entra solo en el tope: m son los caracteres del texto propio que van, n los que tiene.
PIE_TEXTO_CORTADO = ("(el texto de {clave} no entra solo en el tope: va cortado en {m} de {n} caracteres; leelo entero "
                     "con ver_punto)")

TOOL_VER_DESCENDIENTES = {
    "name": "ver_descendientes", "familia": 2,
    "description": ("Lee de una vez los descendientes de un punto, hasta niveles, en orden de lectura: el texto entero "
                    "de cada uno, con su unidad, su título y su cantidad de nodos (los nodos se ven con ver_punto). "
                    "punto: «to::unidad», p. ej. «ext::5.13». Si el tope corta, el pie dice desde dónde seguir."),
    "input_schema": {"type": "object", "properties": {
        "punto": {"type": "string", "description": "Punto «to::unidad»."},
        "niveles": {"type": "integer", "description": "Niveles, de 1 a 3 (def. 2)."},
        "desde": {"type": "integer", "description": "Posición desde la que se lista (def. 0)."}},
        "required": ["punto"]}}
TOOLS_NAV_CAND = FN.TOOLS_NAV + [TOOL_VER_DESCENDIENTES]
TOPES_CAND = {**FN.TOPES, "ver_descendientes": TOPE_VER_DESCENDIENTES}
FAMILIA_CAND = {**FN.FAMILIA, "ver_descendientes": 2}


def _n_descendientes(n: int) -> str:
    return "1 descendiente" if n == 1 else f"{n} descendientes"


class NavegadorCand(FN.Navegador):
    """El Navegador de familias_nav con ver_descendientes; las seis herramientas de HEAD, heredadas sin cambios."""

    def _descendientes(self, clave: str, niveles: int) -> list[str]:
        """Los descendientes de clave hasta niveles, en preorden. Primero, por niveles, la distancia de cada clave al
        punto (la primera vez que aparece); después, el preorden de `hijos`, donde cada clave sale una vez y solo en
        el nivel de esa distancia. Así una clave repetida o un ciclo no repiten nada ni dejan de terminar, y una clave
        alcanzable no se pierde por haber aparecido antes más abajo."""
        prof, frente = {clave: 0}, [clave]
        for d in range(1, niveles + 1):
            siguiente = []
            for c in frente:
                for h in self.puntos[c]["hijos"]:
                    if h in self.puntos and h not in prof:
                        prof[h] = d
                        siguiente.append(h)
            if not siguiente:
                break
            frente = siguiente
        out, emitidos = [], set()
        pila = [(h, 1) for h in reversed(self.puntos[clave]["hijos"])]
        while pila:
            k, d = pila.pop()
            if prof.get(k) != d or k in emitidos:
                continue
            emitidos.add(k)
            out.append(k)
            if d < niveles:
                pila.extend((h, d + 1) for h in reversed(self.puntos[k]["hijos"]))
        return out

    def _cabeza_descendiente(self, pos: int, k: str) -> str:
        p = self.puntos[k]
        return f"#{pos} · {p['unidad']} · {FN._celda(p['titulo'] or '—', 200)} · {FN._n_nodos(len(p['nodos']))}"

    def _bloque_descendiente(self, pos: int, k: str) -> str:
        texto = self._texto_propio(k)
        lineas = FN._lineas_texto(texto) if texto else ["Texto: — (sin texto propio)"]
        return "\n".join([self._cabeza_descendiente(pos, k)] + lineas)

    def _bloque_cortado(self, pos: int, k: str, disponible: int) -> str:
        """El bloque del descendiente k con su texto cortado y el pie que lo dice, en `disponible` caracteres."""
        texto = self._texto_propio(k)
        m = len(texto)
        while True:
            t = texto[:m].rstrip()
            bloque = "\n".join([self._cabeza_descendiente(pos, k),
                                f"Texto ({len(texto)} caracteres, cortado en {len(t)}):", t + "…",
                                PIE_TEXTO_CORTADO.format(clave=k, m=len(t), n=len(texto))])
            exceso = len(bloque) - disponible
            if exceso <= 0 or m == 0:
                return bloque
            m = max(0, m - exceso)

    def ver_descendientes(self, punto, niveles=2, desde=0) -> str:
        tope = TOPES_CAND["ver_descendientes"]
        k = self.resolver_punto(punto)
        if k is None:
            t = self.resolver_to(punto)
            return FN._celda(f"ver_descendientes: no existe el punto «{punto}». Usá «to::unidad» (p. ej. «ext::5.13»)"
                             + (f"; para ver el TO entero usá indice_to(«{t}»)." if t else "; o buscalo con indice_to."),
                             tope)
        niveles = FN._entero(niveles, 2, 1, 3)
        desde = FN._entero(desde, 0, 0, 10 ** 9)
        desc = self._descendientes(k, niveles)
        n = len(desc)
        cab = (f"ver_descendientes {k} · {niveles} nivel{'es' if niveles > 1 else ''} · {_n_descendientes(n)}"
               + (f" · desde={desde}" if desde else ""))
        if not desc:
            return cab + "\nSin hijos."
        if desde >= n:
            return cab + f"\nNo hay más descendientes: son {n} (desde={desde})."
        bloques = [self._bloque_descendiente(i + 1, desc[i]) for i in range(desde, n)]
        if len(cab) + sum(len(b) + 1 for b in bloques) <= tope:
            return "\n".join([cab] + bloques)
        # No entra todo: hace falta el pie, y su lugar se reserva al sumar cada bloque.
        partes, usado, pos = [cab], len(cab), desde
        reserva = 0
        while pos < n:
            bloque = bloques[pos - desde]
            reserva = len(PIE_VER_DESCENDIENTES.format(n=n - pos - 1, k=pos + 1)) + 1 if pos + 1 < n else 0
            if usado + 1 + len(bloque) + reserva > tope:
                break
            partes.append(bloque)
            usado += 1 + len(bloque)
            pos += 1
        if pos == desde:
            # El primero de la llamada no entra solo: va cortado, con el lugar del pie de desde reservado.
            partes.append(self._bloque_cortado(pos + 1, desc[pos], tope - usado - 1 - reserva))
            pos += 1
        if pos < n:
            partes.append(PIE_VER_DESCENDIENTES.format(n=n - pos, k=pos))
        return "\n".join(partes)


def despachar_cand(nav: NavegadorCand, name: str, args: dict) -> str:
    """ver_descendientes, con el mismo criterio de argumentos que familias_nav.despachar (los que faltan o no son del
    tipo van a su valor por defecto); cualquier otra herramienta va a familias_nav.despachar, tal cual."""
    if name == "ver_descendientes":
        a = args or {}
        return nav.ver_descendientes(a.get("punto", ""), a.get("niveles", 2), a.get("desde", 0))
    return FN.despachar(nav, name, args)
