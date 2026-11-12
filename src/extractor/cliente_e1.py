"""
cliente_e1.py — Cliente LLM inyectable para E1 (T2), patrón fase A/B de
sinteticas (cliente_faseB.py) + skill llm-capture.

FASE A (esta unidad): PROHIBICIÓN ABSOLUTA de llamadas a APIs de LLM. El
selftest usa SOLO StubClienteE1 (offline). ClienteE1Real existe como código
para la fase B pero exige construcción explícita con precios y tope
autorizados — no puede usarse "por accidente".

Cadena fase B:  ClienteE1Real ─▶ llm_cache.CachingClient ─▶ anthropic.Anthropic

Decisiones de dominio (checklist "dominio nuevo" de la skill llm-capture):
  - llm_cache se ENVUELVE, jamás se edita (cuarteto intocable).
  - .db PROPIA: cache/e1_extraccion.db bajo ESTE directorio (mandato: todo
    bajo e1_extractor/), misma capa SQLite del proyecto.
  - CODE_VER manual "e1-extractor-v1" + hash del prefijo estable en el
    namespace: cambiar el prompt o el tool schema invalida la caché aunque la
    key ya cubra el request íntegro (doble candado, precedente extract.py v2).
    BUMPEAR CODE_VER a mano si cambia la lógica sin cambiar el prompt.
  - Sin graph_fp: la extracción no consume ningún grafo en runtime — el chunk
    viaja íntegro en el prompt, la key del request captura toda variación.
  - thinking=False (no autorizado; el namespace lleva think=0).

Decisiones de caching de extracción (docs/decisiones_caching_extraccion.md):
  - D1: el request que construye prompt_e1.build_request_kwargs lleva el
    system como lista de bloques con cache_control ephemeral; este cliente lo
    pasa tal cual (jamás lo vuelve string).
  - D2: el gasto se computa con la fórmula de caching (input no cacheado ×
    P_in + cache write × P_cache_write + cache read × P_cache_read + output ×
    P_out) — nunca input+output a secas.
  - D3: todo response REAL de la API se loguea en logs/cache_usage.jsonl con
    component="reextraccion_v2_e1" y su doc (los hits de la caché local no se
    loguean: no son responses de la API).
  - D4: corridas con prefijo idéntico van SECUENCIALES (el runner de fase B
    debe respetarlo; este cliente es sincrónico, no abre concurrencia).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import comun_e1
from comun_e1 import BASE, REPO
import prompt_e1

import llm_cache as lc  # data/experiment/evaluacion/llm_cache.py — solo import

CODE_VER = "e1-extractor-v1"
DOMAIN = "e1_extraccion"
DB_PATH = BASE / "cache" / "e1_extraccion.db"
CACHE_USAGE_LOG = REPO / "logs" / "cache_usage.jsonl"  # gitignoreado (logs/)

# Techo de salida del reintento por corte (U-B5.3, cola entrada 1): ante una
# response con stop_reason == "max_tokens", UNA re-llamada en el mismo pase
# con este techo — el doble del techo de reintento vigente (16.384, el del
# ratchet E3) — y ninguna tercera. El techo del request base (8.192) y el del
# ratchet NO cambian: alterarlos cambiaría requests de unidades que no cortan.
MAX_TOKENS_REINTENTO_CORTE = 32768
# Techo del reintento por corte del PERFIL r2 (U-R2-CODIGO, R4.b; BKL-0030,
# laudo de r2 §1.1 (a)): el SDK rechaza antes de enviarlo un request sin
# streaming ni timeout explícito cuyo max_tokens estima más de 10 minutos
# (anthropic 0.100.0, _base_client._calculate_nonstreaming_timeout: 3.600 s ×
# max_tokens / 128.000 > 600 s), y 32.768 da 921,6 s. 16.384 da 460,8 s. Solo
# el runner con --perfil-r2 lo usa: max_tokens entra en la clave de caché, y
# los perfiles existentes siguen con MAX_TOKENS_REINTENTO_CORTE.
MAX_TOKENS_REINTENTO_CORTE_R2 = 16384
# Reintento ante una salida de E1 mal formada (U-R2-CODIGO-2, C2, punto b; solo
# el runner del perfil r2 lo usa): el MISMO request, en un namespace propio
# (sufijo del code_ver), porque con el mismo namespace la caché devolvería la
# misma salida; va a la misma db y su log de usage lleva un component propio
# (decisiones de caching D1 a D4). Con el perfil r2b (U-PROMPT-R2, P5), el
# request lleva además la temperatura del reintento: lo arma
# runner_corpus.kwargs_reintento_forma; este cliente lo pasa tal cual.
SUFIJO_REINTENTO_FORMA = "-rforma1"
# U-REEXT-T0, T2-bis (decisión 3 de la autora sobre el FRENO T2): si el reintento por forma también vuelve mal formado,
# el runner del perfil r2b hace UN segundo reintento, el mismo pedido, en este namespace; su log de usage lleva el
# component del reintento por forma.
SUFIJO_REINTENTO_FORMA_2 = "-rforma2"
COMPONENTE_E1 = "reextraccion_v2_e1"
COMPONENTE_REINTENTO_FORMA = "reextraccion_v2_e1_reintento_forma"
# Tercer escalón del reintento por corte (U-PROMPT-R2, P3c-2; decisión 6 de la autora sobre el FRENO P3c-1; solo el
# runner del perfil r2 lo usa): si el reintento de MAX_TOKENS_REINTENTO_CORTE_R2 también corta y la unidad no se puede
# partir, o si corta una parte, UNA llamada más con este techo. Por encima de LIMITE_SIN_TRANSMISION el SDK exige
# transmisión por partes (anthropic 0.100.0, _base_client._calculate_nonstreaming_timeout: 3.600 s × max_tokens /
# 128.000 > 600 s), así que el pedido va por AdaptadorTransmision, debajo del CachingClient sellado: la caché guarda
# el mensaje final como el de cualquier llamada, y la clave cambia solo por max_tokens. Máximo de salida de
# claude-haiku-4-5: 64.000 tokens (documentación de modelos de la API, consultada el 04/10/2026).
MAX_TOKENS_ESCALON_3_R2 = 40960
LIMITE_SIN_TRANSMISION = 21333
TIMEOUT_TRANSMISION_S = 1800.0
COMPONENTE_ESCALON_3 = "reextraccion_v2_e1_escalon3"


class _MensajesPorTransmision:
    def __init__(self, real, timeout: float):
        self._real, self._timeout = real, timeout

    def create(self, **kwargs):
        from anthropic.types import Message  # noqa: PLC0415 — solo con el cliente real
        with self._real.messages.stream(timeout=self._timeout, **kwargs) as flujo:
            final = flujo.get_final_message()
        crudo = final.model_dump(mode="json")
        # El SDK devuelve un ParsedMessage: su bloque de texto lleva `parsed_output`, que un mensaje de create no
        # trae. Se normaliza a Message para que el crudo que guarda la caché tenga la forma del de create.
        for b in crudo.get("content") or []:
            if isinstance(b, dict):
                b.pop("parsed_output", None)
        return Message.model_validate(crudo)


class AdaptadorTransmision:
    """Adaptador del cliente real con la interfaz que espera llm_cache.CachingClient (`messages.create(**kwargs)`):
    llama `messages.stream(**kwargs)` con un timeout explícito (opción del pedido, fuera de la clave) y devuelve el
    mensaje final, normalizado a anthropic.types.Message."""

    def __init__(self, real, timeout: float = TIMEOUT_TRANSMISION_S):
        self.messages = _MensajesPorTransmision(real, timeout)


def namespace_e1(canal_abierto: bool = False, prefijo_hash: str | None = None, sufijo: str = "") -> str:
    """Namespace de la caché local: dominio + code-version propio + hash del
    prefijo estable + flag de thinking. El hash del prefijo hace explícito el
    candado que la key del request ya da implícitamente. Con canal_abierto
    (experimental, explícito) el hash es el del prefijo con canal abierto:
    namespace DISTINTO → partición de caché; con los defaults el namespace es
    IDÉNTICO al de producción.

    prefijo_hash (U-CABLE-V3): hash del prefijo del PERFIL de la corrida
    (p. ej. el del prefijo v3 sellado). None = el de producción dev, byte a
    byte el namespace histórico. Un hash distinto particiona la caché con el
    MISMO patrón; las keys viejas de la db no se tocan (never-pay-twice).

    sufijo (U-R2-CODIGO-2): se agrega al code_ver; "" = el namespace de
    siempre. SUFIJO_REINTENTO_FORMA particiona el reintento por forma."""
    if prefijo_hash is None:
        prefijo_hash = prompt_e1.prefijo_hash(canal_abierto)
    return lc.make_namespace(
        DOMAIN,
        code_ver=f"{CODE_VER}-p{prefijo_hash}{sufijo}",
        thinking=False,
    )


class TopeExcedido(RuntimeError):
    pass


class StubClienteE1:
    """Cliente offline para el selftest: devuelve tool inputs enlatados, jamás
    toca la red. Registra cada request recibido para que el selftest pueda
    asertar sobre el prefijo (identidad entre chunks, breakpoint declarado)."""

    class _Bloque:
        def __init__(self, tool_input):
            self.type = "tool_use"
            self.name = prompt_e1.NOMBRE_TOOL
            self.input = tool_input

    class _Usage:
        input_tokens = 0
        output_tokens = 0
        cache_creation_input_tokens = 0
        cache_read_input_tokens = 0

    class _Respuesta:
        def __init__(self, tool_input):
            self.content = [StubClienteE1._Bloque(tool_input)]
            self.stop_reason = "tool_use"
            self.usage = StubClienteE1._Usage()

    def __init__(self, tool_inputs: list):
        """tool_inputs: cola de inputs a devolver, en orden de llamada."""
        self._cola = list(tool_inputs)
        self.requests_recibidos: list[dict] = []
        self.messages = self  # imita client.messages.create

    def create(self, **kwargs):
        self.requests_recibidos.append(kwargs)
        if not self._cola:
            raise RuntimeError("StubClienteE1: cola de respuestas agotada")
        return StubClienteE1._Respuesta(self._cola.pop(0))


class ClienteE1Real:
    """Cliente real con caché never-pay-twice, contabilidad D2 y tope duro.
    SOLO fase B: exige precios y tope explícitos (autorización con precios
    resueltos); sin ellos no se construye."""

    def __init__(
        self,
        *,
        precio_in_por_mtok: float,
        precio_out_por_mtok: float,
        precio_cache_write_por_mtok: float,
        precio_cache_read_por_mtok: float,
        tope_usd: float,
        run_label: str,
        db_path: Path = DB_PATH,
        canal_abierto: bool = False,
        guardian=None,
        prefijo_hash: str | None = None,
        transmision: bool = False,
    ):
        if min(precio_in_por_mtok, precio_out_por_mtok,
               precio_cache_write_por_mtok, precio_cache_read_por_mtok) <= 0 or tope_usd <= 0:
            raise ValueError("precios y tope deben ser positivos (autorización fase B)")
        import anthropic  # import local: la fase A jamás lo ejecuta
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._real = anthropic.Anthropic(max_retries=3)
        self._db_path, self._run_label = db_path, run_label
        self._canal_abierto, self._prefijo_hash = canal_abierto, prefijo_hash
        # caché del reintento por forma (U-R2-CODIGO-2): se abre en el primer reintento
        self.cache_reintento_forma = None
        # P3c-2: con transmision=True (solo el perfil r2), los pedidos con max_tokens por encima de
        # LIMITE_SIN_TRANSMISION van por AdaptadorTransmision, en cachés propias que se abren en el primer pedido así
        # (mismo db, mismo namespace que la caché de su camino).
        self._transmision = transmision
        self.cache_transmision = None
        self.cache_reintento_forma_transmision = None
        self.p_in = precio_in_por_mtok
        self.p_out = precio_out_por_mtok
        self.p_cw = precio_cache_write_por_mtok
        self.p_cr = precio_cache_read_por_mtok
        self.tope_usd = tope_usd
        self.cache = lc.CachingClient(
            self._real,
            domain=DOMAIN,
            db_path=db_path,
            namespace=namespace_e1(canal_abierto, prefijo_hash=prefijo_hash),
            thinking_enabled=False,
            run_label=run_label,
        )
        self.gasto_usd = 0.0  # solo misses (fórmula D2)
        self.llamadas = 0
        self.llamadas_hit = 0
        # Guardián de presupuesto COMPARTIDO entre los clientes de una corrida
        # (U-B5.3 decisión 8; duck-typed: .excedido(p)/.registrar(d)/.gasto_usd/
        # .tope_usd). None = solo el tope propio, comportamiento previo intacto.
        self.guardian = guardian
        # Proyección conservadora de una llamada fría para el chequeo de tope:
        # prefijo completo como cache write + variable mediana + salida máxima.
        self._proyeccion_usd = (
            6500 / 1e6 * self.p_cw
            + 1000 / 1e6 * self.p_in
            + prompt_e1.MAX_OUTPUT_TOKENS / 1e6 * self.p_out
        )

    def _log_usage(self, usage, doc: str | None, componente: str = COMPONENTE_E1) -> None:
        # Decisión 3: una línea JSON por response REAL de la API.
        CACHE_USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        line = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": componente,
            "doc": doc,
            "input_tokens": getattr(usage, "input_tokens", None),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }
        with CACHE_USAGE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def _transmite(self, kwargs: dict) -> bool:
        return self._transmision and (kwargs.get("max_tokens") or 0) > LIMITE_SIN_TRANSMISION

    def _cache_transmision(self, sufijo: str):
        """La caché sobre AdaptadorTransmision del camino (sufijo vacío: el de siempre; el de cada reintento por
        forma)."""
        attr = ("cache_transmision" if not sufijo else "cache_reintento_forma_transmision"
                if sufijo == SUFIJO_REINTENTO_FORMA else "cache_reintento_forma_2_transmision")
        if getattr(self, attr, None) is None:
            setattr(self, attr, lc.CachingClient(
                AdaptadorTransmision(self._real), domain=DOMAIN, db_path=self._db_path,
                namespace=namespace_e1(self._canal_abierto, prefijo_hash=self._prefijo_hash, sufijo=sufijo),
                thinking_enabled=False, run_label=self._run_label))
        return getattr(self, attr)

    def create(self, *, doc: str | None = None, **kwargs):
        if self._transmite(kwargs):
            return self._crear_en(self._cache_transmision(""), COMPONENTE_ESCALON_3, doc, kwargs)
        return self._crear_en(self.cache, COMPONENTE_E1, doc, kwargs)

    def crear_reintento_forma(self, *, doc: str | None = None, sufijo: str = SUFIJO_REINTENTO_FORMA, **kwargs):
        """U-R2-CODIGO-2, C2, punto b: el request que recibe, tal cual, en el
        namespace del reintento por forma (SUFIJO_REINTENTO_FORMA), con el
        mismo tope y la misma contabilidad D2 (con el perfil r2b, el runner lo
        arma con la temperatura del reintento; U-PROMPT-R2, P5). Con
        sufijo=SUFIJO_REINTENTO_FORMA_2, el segundo reintento (U-REEXT-T0,
        T2-bis), en su namespace."""
        if self._transmite(kwargs):
            return self._crear_en(self._cache_transmision(sufijo), COMPONENTE_REINTENTO_FORMA, doc, kwargs)
        attr = "cache_reintento_forma" if sufijo == SUFIJO_REINTENTO_FORMA else "cache_reintento_forma_2"
        if getattr(self, attr, None) is None:
            setattr(self, attr, lc.CachingClient(
                self._real, domain=DOMAIN, db_path=self._db_path,
                namespace=namespace_e1(self._canal_abierto, prefijo_hash=self._prefijo_hash, sufijo=sufijo),
                thinking_enabled=False, run_label=self._run_label))
        return self._crear_en(getattr(self, attr), COMPONENTE_REINTENTO_FORMA, doc, kwargs)

    def _crear_en(self, cache, componente: str, doc: str | None, kwargs: dict):
        proyeccion = self._proyeccion_usd
        if self._transmite(kwargs):
            # P3c-2: el pedido por transmisión se proyecta con su techo de salida, no con el del primer intento.
            proyeccion += (kwargs["max_tokens"] - prompt_e1.MAX_OUTPUT_TOKENS) / 1e6 * self.p_out
        if self.gasto_usd + proyeccion > self.tope_usd:
            raise TopeExcedido(
                f"gasto acumulado USD {self.gasto_usd:.4f} + proyección "
                f"{proyeccion:.4f} supera el tope {self.tope_usd:.2f}")
        if self.guardian is not None and self.guardian.excedido(proyeccion):
            raise TopeExcedido(
                f"presupuesto COMPARTIDO agotado: gasto combinado USD "
                f"{self.guardian.gasto_usd:.4f} + proyección "
                f"{proyeccion:.4f} supera el tope compartido "
                f"{self.guardian.tope_usd:.2f}")
        antes = dict(cache._stats)
        resp = cache.messages.create(**kwargs)
        despues = cache._stats
        fue_miss = despues["misses"] > antes["misses"]
        self.llamadas += 1
        if fue_miss:
            self._log_usage(resp.usage, doc, componente)
            d_in = despues["tokens_in"] - antes["tokens_in"]
            d_out = despues["tokens_out"] - antes["tokens_out"]
            d_cw = despues["cache_write"] - antes["cache_write"]
            d_cr = despues["cache_read"] - antes["cache_read"]
            delta_usd = (
                d_in * self.p_in + d_out * self.p_out
                + d_cw * self.p_cw + d_cr * self.p_cr
            ) / 1e6
            self.gasto_usd += delta_usd
            if self.guardian is not None:
                self.guardian.registrar(delta_usd)
        else:
            self.llamadas_hit += 1
        return resp

    def resumen(self) -> dict:
        d = {
            "llamadas": self.llamadas,
            "hits_cache_local": self.llamadas_hit,
            "gasto_usd_real": round(self.gasto_usd, 4),
            "tope_usd": self.tope_usd,
            "precios_por_mtok": {"in": self.p_in, "out": self.p_out,
                                 "cache_write": self.p_cw, "cache_read": self.p_cr},
            "cache_stats": self.cache.stats(),
        }
        if self.cache_reintento_forma is not None:
            d["cache_stats_reintento_forma"] = self.cache_reintento_forma.stats()
        if self.cache_transmision is not None:
            d["cache_stats_transmision"] = self.cache_transmision.stats()
        if self.cache_reintento_forma_transmision is not None:
            d["cache_stats_reintento_forma_transmision"] = self.cache_reintento_forma_transmision.stats()
        for attr in ("cache_reintento_forma_2", "cache_reintento_forma_2_transmision"):   # T2-bis
            if getattr(self, attr, None) is not None:
                d[f"cache_stats_{attr[len('cache_'):]}"] = getattr(self, attr).stats()
        if self.guardian is not None:
            d["presupuesto_compartido"] = {
                "tope_usd": self.guardian.tope_usd,
                "gasto_combinado_usd": round(self.guardian.gasto_usd, 4),
            }
        return d

    def close(self) -> None:
        self.cache.close()
        if self.cache_reintento_forma is not None:
            self.cache_reintento_forma.close()
        for c in (self.cache_transmision, self.cache_reintento_forma_transmision,
                  getattr(self, "cache_reintento_forma_2", None), getattr(self, "cache_reintento_forma_2_transmision", None)):
            if c is not None:
                c.close()


def extraer_chunk(cliente, chunk: dict, model: str, canal_abierto: bool = False) -> dict:
    """Camino común stub/real: construye el request determinístico del chunk,
    llama al cliente inyectado y devuelve el tool input crudo (la validación
    es de validador_e1, separada). El cliente real recibe además doc= para el
    log de usage (Decisión 3). canal_abierto debe coincidir con el del cliente
    real (mismo prefijo → mismo namespace); se pasa explícito, jamás se infiere."""
    kwargs = prompt_e1.build_request_kwargs(chunk, model=model, canal_abierto=canal_abierto)
    if isinstance(cliente, ClienteE1Real):
        resp = cliente.create(doc=chunk["archivo"], **kwargs)
    else:
        resp = cliente.messages.create(**kwargs)

    tool_use = None
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            tool_use = block
            break
    return {
        "chunk_id": chunk["id"],
        "stop_reason": getattr(resp, "stop_reason", None),
        "tool_input": tool_use.input if tool_use is not None else None,
        "error": None if tool_use is not None else "no_tool_use",
    }


# ------------------------------------------------------------------------- #
# Reintento por corte de max_tokens (U-B5.3, cola entrada 1)                 #
# ------------------------------------------------------------------------- #

def _crear(cliente, kwargs: dict, doc: str | None):
    """Despacho común stub/real (mismo criterio que extraer_chunk)."""
    if isinstance(cliente, ClienteE1Real):
        return cliente.create(doc=doc, **kwargs)
    return cliente.messages.create(**kwargs)


def crear_con_reintento_corte(cliente, kwargs: dict, doc: str | None = None,
                              max_tokens_reintento: int = MAX_TOKENS_REINTENTO_CORTE, escalon_3=None):
    """Una llamada y, SOLO si la response cortó por max_tokens (stop_reason ==
    "max_tokens"), UNA re-llamada con max_tokens duplicado a 32.768. Sin
    tercera llamada.

    - Camino sin corte: `kwargs` viaja TAL CUAL (mismo objeto, ningún byte
      cambia) — never-pay-twice intacto; la clave de caché es la histórica.
    - El reintento es una request NUEVA: copia superficial de `kwargs` con
      SOLO max_tokens cambiado → clave de caché propia (llm_cache.
      canonical_request hashea max_tokens). El intento cortado ya quedó
      persistido íntegro en la db por el write-through del CachingClient;
      se devuelve para que el runner lo persista además en su jsonl. No se
      sobreescribe ni descarta nada.

    Devuelve (resp_final, intento_cortado): intento_cortado es None si no
    hubo corte; si el reintento también corta, resp_final llega con
    stop_reason == "max_tokens" y el runner lo cuenta como error definitivo
    (un pase no cierra con reintentables pendientes).

    Tercer escalón (U-PROMPT-R2, P3c-2; solo el runner del perfil r2 pasa
    `escalon_3`, una función sin argumentos que dice si corresponde): si el
    reintento también corta y `escalon_3()` es verdadero, UNA llamada más, el
    mismo pedido con max_tokens = MAX_TOKENS_ESCALON_3_R2 (el cliente real la
    despacha por transmisión). Con `escalon_3`, devuelve (resp_final, cortados),
    con los intentos cortados en orden (ninguno, uno o dos). Sin `escalon_3`,
    el par de siempre: los perfiles existentes no cambian."""
    resp = _crear(cliente, kwargs, doc)
    if getattr(resp, "stop_reason", None) != "max_tokens":
        return (resp, None) if escalon_3 is None else (resp, ())
    kwargs_reintento = dict(kwargs)
    kwargs_reintento["max_tokens"] = max_tokens_reintento
    resp2 = _crear(cliente, kwargs_reintento, doc)
    if escalon_3 is None:
        return resp2, resp
    if getattr(resp2, "stop_reason", None) != "max_tokens" or not escalon_3():
        return resp2, (resp,)
    kwargs_3 = dict(kwargs)
    kwargs_3["max_tokens"] = MAX_TOKENS_ESCALON_3_R2
    return _crear(cliente, kwargs_3, doc), (resp, resp2)


def crear_reintento_forma(cliente, kwargs: dict, doc: str | None = None, sufijo: str = SUFIJO_REINTENTO_FORMA):
    """U-R2-CODIGO-2, C2, punto b: UNA re-llamada con el request que recibe
    (`kwargs` tal cual) ante una salida mal formada, en el namespace del
    reintento por forma: con los perfiles existentes, el mismo request; con
    el perfil r2b, el mismo con la temperatura del reintento
    (runner_corpus.kwargs_reintento_forma; U-PROMPT-R2, P5). Con un cliente
    que no tiene ese namespace (stubs), el mismo despacho que `_crear`. Con
    sufijo=SUFIJO_REINTENTO_FORMA_2, el segundo reintento (U-REEXT-T0,
    T2-bis); el primero se despacha como siempre, sin el argumento."""
    fn = getattr(cliente, "crear_reintento_forma", None)
    if fn is not None:
        if sufijo == SUFIJO_REINTENTO_FORMA:
            return fn(doc=doc, **kwargs)
        return fn(doc=doc, sufijo=sufijo, **kwargs)
    return cliente.messages.create(**kwargs)


def resumen_intento(resp) -> dict:
    """Proyección jsonl de una response (para persistir el intento cortado en
    el registro del runner): stop_reason + usage + tool input crudo."""
    u = getattr(resp, "usage", None)
    tool_input = None
    for b in getattr(resp, "content", None) or []:
        if getattr(b, "type", None) == "tool_use":
            tool_input = b.input
            break
    return {
        "stop_reason": getattr(resp, "stop_reason", None),
        "usage": {
            "input_tokens": getattr(u, "input_tokens", 0) or 0,
            "output_tokens": getattr(u, "output_tokens", 0) or 0,
            "cache_write_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
            "cache_read_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
        },
        "tool_input_crudo": tool_input,
    }
