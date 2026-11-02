"""
seco_r0.py — R0: el transporte simulado de la corrida en seco (correr_r0.py --seco).

Reemplaza al cliente de la API debajo de llm_cache.CachingClient, en los clientes reales de E3 y de los reintentos de
E1: recibe solo los pedidos que la caché local no encontró y devuelve un anthropic.types.Message armado según el
escenario, o levanta un error como los de la API. Nunca toca la red. Qué pedido es (tipo, unidad y paso) lo dice la
guardia de correr_r0, que corre antes de cada llamada.

Respuestas:
  - verificación de E3 (solo sin reuso de O3, o si la caché no la tiene): el tool input de O3 de la unidad, con su usage;
  - reintento de E1: la extracción del intento 0 de la unidad (válida para el validador), modelo de la tanda 0;
  - re-verificación de E3: ext::3.6.4.1 completa; ext::3.16.2.1 con un faltante de severidad media (se acepta con
    residuales); ext::3.18.1.1 con un faltante alto con cita verbatim de la unidad (sigue bloqueante: cola).
Escenarios: base; tope (lo pone el tope de la línea de comandos); error_transitorio (dos errores en el reintento de
E1 de ext::3.6.4.1 y después bien); error_persistente (siempre error ahí); mal_formada (sin tool_use en la
verificación de ext::2.6.1.2, entidades que no son lista en el reintento de ext::3.16.2.1 y sin tool_use en la
re-verificación de ext::3.6.4.1); modelo_distinto (el reintento de E1 responde con otro id de modelo);
mensaje_distinto (el esperado lo altera correr_r0 con --seco-alterar-esperado).
"""
from __future__ import annotations

import copy
from collections import Counter

from anthropic.types import Message

import prompt_e1
import prompt_e3

ESCENARIOS = ("base", "tope", "error_transitorio", "error_persistente", "mal_formada", "modelo_distinto",
              "mensaje_distinto")
MODELO_E3 = "claude-sonnet-5"
MODELO_E1 = "claude-haiku-4-5-20251001"
PREFIJO_TOKENS = {"e3": 11637, "e1r": 27840}           # los de O3 y de los reintentos de la tanda 0 (r0_f1_costo)
OBJETIVO_ERROR = "ext::3.6.4.1"


class ErrorApiSimulado(RuntimeError):
    pass


def _cita(chunk: dict) -> str:
    """Un tramo verbatim del texto propio de la unidad (la primera línea no vacía, hasta 80 caracteres)."""
    linea = next(x.strip() for x in chunk["texto"].splitlines() if x.strip())
    return linea[:80]


class Transporte:
    def __init__(self, guardia, ctx: dict, escenario: str):
        if escenario not in ESCENARIOS:
            raise ValueError(f"escenario desconocido: {escenario}")
        self.messages = self
        self.g, self.ctx, self.esc = guardia, ctx, escenario
        self.llamadas: list[tuple[str, str, str]] = []
        self.errores = 0
        self.escrito: set[str] = set()

    def _usage(self, tipo: str, entrada: int, salida: int) -> dict:
        pref = PREFIJO_TOKENS[tipo]
        primera = tipo not in self.escrito
        self.escrito.add(tipo)
        return {"input_tokens": entrada, "output_tokens": salida,
                "cache_creation_input_tokens": pref if primera else 0,
                "cache_read_input_tokens": 0 if primera else pref}

    def _mensaje(self, modelo: str, contenido: list, usage: dict, stop: str) -> Message:
        return Message.model_validate({"id": f"msg_seco_{len(self.llamadas)}", "type": "message",
                                       "role": "assistant", "model": modelo, "content": contenido,
                                       "stop_reason": stop, "stop_sequence": None, "usage": usage})

    def _tool(self, nombre: str, entrada) -> list:
        return [{"type": "tool_use", "id": f"toolu_seco_{len(self.llamadas)}", "name": nombre, "input": entrada}]

    def create(self, **kwargs):
        u = self.g.ultimo
        tipo, cid, paso = u["tipo"], u["chunk_id"], u["paso"]
        self.llamadas.append((tipo, cid, paso))
        if tipo == "e1r" and cid == OBJETIVO_ERROR and (
                self.esc == "error_persistente" or (self.esc == "error_transitorio" and self.errores < 2)):
            self.errores += 1
            raise ErrorApiSimulado("529 overloaded_error (simulado)")
        if tipo == "e3" and paso == "verificacion":
            if self.esc == "mal_formada" and cid == "ext::2.6.1.2":
                return self._mensaje(MODELO_E3, [{"type": "text", "text": "sin veredicto (simulado)"}],
                                     self._usage("e3", 2400, 20), "end_turn")
            r = self.ctx["o3"][cid]
            d = r["usage_delta"]
            return self._mensaje(MODELO_E3, self._tool(prompt_e3.NOMBRE_TOOL, copy.deepcopy(r["tool_input"])),
                                 {"input_tokens": d["tokens_in"], "output_tokens": d["tokens_out"],
                                  "cache_creation_input_tokens": d["cache_write"],
                                  "cache_read_input_tokens": d["cache_read"]}, "tool_use")
        if tipo == "e1r":
            if self.esc == "mal_formada" and cid == "ext::3.16.2.1":
                ti = {"entities": "no es una lista"}
            else:
                # la extracción del intento 0 con la etiqueta de la primera entidad cambiada: si fuera idéntica, la
                # re-verificación armaría el mismo pedido que la verificación y acertaría su fila de la caché
                ti = copy.deepcopy(self.ctx["regs"][cid]["tool_input_crudo"])
                ti["entities"][0]["label"] = ti["entities"][0]["label"] + " (reintento simulado)"
            modelo = "claude-haiku-4-5-20991231" if self.esc == "modelo_distinto" else MODELO_E1
            return self._mensaje(modelo, self._tool(prompt_e1.NOMBRE_TOOL, ti), self._usage("e1r", 2000, 1500),
                                 "tool_use")
        # re-verificación de E3
        if self.esc == "mal_formada" and cid == "ext::3.6.4.1":
            return self._mensaje(MODELO_E3, [{"type": "text", "text": "sin veredicto (simulado)"}],
                                 self._usage("e3", 3000, 20), "end_turn")
        chunk = self.ctx["chunks"][cid]
        if cid == "ext::3.6.4.1":
            ti = {"veredicto": "completo_ok", "faltantes": []}
        else:
            sev = "media" if cid == "ext::3.16.2.1" else "alta"
            ti = {"veredicto": "faltantes_detectados",
                  "faltantes": [{"tipo": "otro", "cita_textual_del_fuente": _cita(chunk),
                                 "ubicacion": chunk["unidad"], "severidad": sev,
                                 "nota": "faltante simulado de la corrida en seco"}]}
        return self._mensaje(MODELO_E3, self._tool(prompt_e3.NOMBRE_TOOL, ti), self._usage("e3", 3000, 300),
                             "tool_use")

    def resumen(self) -> dict:
        return {"escenario": self.esc, "llamadas_al_transporte": len(self.llamadas),
                "por_tipo_y_paso": {f"{t}|{p}": n for (t, p), n in
                                    sorted(Counter((t, p) for t, _, p in self.llamadas).items())},
                "errores_simulados": self.errores, "detalle": [list(x) for x in self.llamadas]}
