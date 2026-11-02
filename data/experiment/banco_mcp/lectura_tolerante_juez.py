"""lectura_tolerante_juez.py — La lectura tolerante de una salida del juez de EV2 que no se lee como JSON (decisión de la autora
del 27/10/2026, recibida a las 23:26:23: la opción B, antes de ver ninguna cifra; mesa, §312). Sirve para N6 y, si se firma su
nota al pie, para B6.3. No edita `ev2_juez/juez.py` ni su prompt: lee la misma salida que el juez ya devolvió, sin llamar al modelo.

Por qué: el prompt del juez pide copiar en «fragmento», textual, el pasaje de la respuesta (prompt_juez_v1.md:34-37). Cuando ese
pasaje trae comillas dobles rectas y el juez no las escapa, el JSON no se lee (`json.JSONDecodeError`) y la lectura estricta
(`juez.parsear_veredicto`) lo rechaza entero, aunque el índice y el veredicto de cada criterio estén bien.

Cuándo aplica (`aplica`): solo a una salida que terminó con `end_turn` y cuyo objeto JSON (del primer «{» al último «}», como la
lectura estricta) da `json.JSONDecodeError`. Una salida truncada, con otra cantidad de criterios, con un veredicto fuera del
dominio o sin objeto JSON no entra: queda como la deja la regla de su análisis.

Qué lee (`leer`), y nada más: la clasificación de la respuesta y, por criterio, su índice y su veredicto.
  · los índices: cada «"indice": k,» del texto, que tienen que ser 1..N en orden, con N la cantidad de criterios del pedido;
  · el veredicto de cada criterio: el primero va pegado a su índice («"indice": k, "veredicto": "…"»), y si el mismo criterio repite
    la clave, vale la última antes del índice siguiente, como `json.loads` con una clave repetida;
  · la clasificación: un solo «"clasificacion_respuesta": "abstencion"|"contenido"» en todo el texto.
Cualquier otra forma levanta ValueError: la salida queda sin lectura y rige la regla de su análisis. El fragmento y la
justificación no se leen: el agregado no los usa.
"""
from __future__ import annotations

import json
import re

VEREDICTOS = ("cumplido", "no_cumplido", "dudoso")
CLASIFICACIONES = ("abstencion", "contenido")
_INDICE = re.compile(r'"indice"\s*:\s*(\d+)\s*,')
_PEGADO = re.compile(r'\s*"veredicto"\s*:\s*"(cumplido|no_cumplido|dudoso)"')
_VEREDICTO = re.compile(r'"veredicto"\s*:\s*"(cumplido|no_cumplido|dudoso)"')
_CLASIFICACION = re.compile(r'"clasificacion_respuesta"\s*:\s*"(abstencion|contenido)"')


def objeto(texto: str) -> str | None:
    """El tramo que la lectura estricta pasa a json.loads: del primer «{» al último «}»."""
    i, f = texto.find("{"), texto.rfind("}")
    return None if i < 0 or f <= i else texto[i:f + 1]


def aplica(texto: str, stop_reason: str | None) -> bool:
    """Si la salida es de las que esta lectura cubre: terminó con end_turn y su objeto JSON no se lee como JSON."""
    o = objeto(texto)
    if stop_reason != "end_turn" or o is None:
        return False
    try:
        json.loads(o)
    except json.JSONDecodeError:
        return True
    return False


def leer(texto: str, n_criterios: int) -> dict:
    """{"clasificacion_respuesta": …, "criterios": [{"indice": k, "veredicto": …, "veredictos_en_el_criterio": m}]} o ValueError."""
    if n_criterios < 1:
        raise ValueError("sin criterios")
    ms = list(_INDICE.finditer(texto))
    if [int(m.group(1)) for m in ms] != list(range(1, n_criterios + 1)):
        raise ValueError(f"los índices no son 1..{n_criterios} en orden")
    criterios = []
    for k, m in enumerate(ms):
        if not _PEGADO.match(texto, m.end()):
            raise ValueError(f"el criterio {k + 1} no trae su veredicto pegado al índice")
        tramo = texto[m.end(): ms[k + 1].start() if k + 1 < len(ms) else len(texto)]
        vs = _VEREDICTO.findall(tramo)
        criterios.append({"indice": k + 1, "veredicto": vs[-1], "veredictos_en_el_criterio": len(vs)})
    cl = _CLASIFICACION.findall(texto)
    if len(cl) != 1:
        raise ValueError(f"se esperaba una clasificación de la respuesta, hay {len(cl)}")
    return {"clasificacion_respuesta": cl[0], "criterios": criterios}


def igual_a_la_estricta(tolerante: dict, estricta: dict) -> bool:
    """Si la lectura tolerante da la misma clasificación y los mismos (índice, veredicto) que la estricta de `juez.parsear_veredicto`."""
    return (tolerante["clasificacion_respuesta"] == estricta["clasificacion_respuesta"]
            and [(c["indice"], c["veredicto"]) for c in tolerante["criterios"]]
            == [(c["indice"], c["veredicto"]) for c in estricta["criterios"]])
