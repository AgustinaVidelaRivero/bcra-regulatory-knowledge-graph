"""
juez_v3.py — el juez de precisión v3 de tripletas: copia de juez_v2.py (v2/codigo/, sha256 2c798a6d…) con lo que cambia la
enmienda 5 del pre-registro de tripletas, FIRMADA (commit 6d9fbf10):
  - el modelo y el esfuerzo no cambian (punto 4): claude-opus-5-5, con el esfuerzo medium;
  - lo que juzga es solo «correcta» (punto 3): la regla del §4.2, el parseo y el agregado son los de la v2, que siguen
    devolviendo la importancia; el análisis de la v3 no la usa;
  - los nombres de la versión: el code_ver (juez-tripletas-v3), los namespaces (juez_tripletas_v3_rN) y el dominio de
    la caché;
  - los topes del punto 14 (TOPES_DECIDIDOS): el humo, cada iteración, la validación y las 200 que faltan de las 400;
  - el control de los pedidos: las refs de T (T001 a T400) tampoco van, ni como valor, y el bloque de los casos nuevos
    de la enmienda (casos_resueltos_por_componente, punto 6) es, como los otros dos, un bloque de casos.

Lo de la v2 (juez_v2.py), tal cual:
  el juez de precisión v2 de la etapa V, copia de juez_v.py de la v1 con los cambios de la
v2 (registro de decisiones, §87 a §89, y la enmienda 4 del pre-registro de tripletas, con su firma PENDIENTE: sus seis
puntos están en la §89). Rige el pre-registro de la evaluación por tripletas, FIRMADO (§4), con sus notas al pie.

Qué cambia contra la v1 (el diff está en v2/diff/):
  - el modelo: claude-opus-5-5. El pedido no lleva `temperature` (la API no la acepta en ese modelo) ni `thinking` (con
    `disabled` o con presupuesto da 400; el razonamiento es adaptativo). El esfuerzo va fijo: output_config.effort =
    "medium". max_tokens 16000, que deja lugar al razonamiento, y el reintento por corte con el mismo valor: más alto,
    el SDK pide streaming (por encima de 21.333 tokens en este modelo) y el cliente de la caché no lo captura;
  - la respuesta trae bloques de razonamiento antes del texto: el análisis toma solo los bloques de texto (como la
    v1) y la caché guarda la respuesta entera; un pedido que la API rechaza (stop_reason `refusal`) no se analiza:
    deja la repetición sin voto, y se cuenta (sin respaldo en otro modelo);
  - el code_ver y los namespaces son de la v2, con el modelo y el esfuerzo en la marca (juez-tripletas-v2, y
    juez_tripletas_v2_r1, _r2 y _r3); la marca de thinking va en 1;
  - la guarda del gasto, con los precios de Opus 5.5 y los topes de la §89 (PRECIOS_DECIDIDOS y TOPES_DECIDIDOS,
    contra los que el driver controla lo que recibe por la línea de comandos). Suma el gasto de las tres bases y
    proyecta con lo que les falta a las tres; con las tres repeticiones en paralelo (un proceso por repetición, cada
    uno con su base), cada llamada reserva su cota bajo un cerrojo, y el tope cuenta las reservas en vuelo de los
    otros procesos;
  - sale la v1.4 (la modalidad por código): la v2 parte del prompt v1.1, y la regla del gold la corrió con la v1_3.

Lo que no cambia (la regla del §4.2, la importancia, el parseo de la salida, el agregado modal de la v1.2, los
Sujetos sin definición y el control de 0 cruces) va igual que en juez_v.py; el selftest de la v2 lo compara contra
la v1 sobre todo su dominio.

La regla del §4.2, completa (nota al pie del pre-registro del 19/10/2026; registro de decisiones, §56), en este orden:
  incorrecta               = al menos un componente contradicho (aunque haya marca de adjudicación);
  adjudicacion             = la marca «requiere adjudicación humana» sin ningún contradicho;
  correcta                 = los cinco componentes sostenidos o no_consta, sin ningún contradicho, con sujeto y
                             predicado sostenidos (y sin marca de adjudicación);
  incorrecta_por_no_consta = sin ningún contradicho, sin marca y con el sujeto o el predicado en no_consta: no es
                             correcta. En el acuerdo de dos clases del §4.6 cuenta como incorrecta (dos_clases), y el
                             informe separa las incorrectas por vía (contradicho y no_consta).
Importancia: esencial = conducta exigible y (valor concreto o relación principal); accesoria = ni conducta exigible
ni valor concreto; útil = el resto.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import fcntl  # noqa: E402
import hashlib  # noqa: E402
import importlib.util  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import sqlite3  # noqa: E402
import statistics  # noqa: E402
from collections import Counter  # noqa: E402
from contextlib import contextmanager  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v1_importada import PJ  # noqa: E402

# --------------------------------------------------------------------------- #
# Instrumento (enmienda 4, puntos 1 y 2; §89)                                 #
# --------------------------------------------------------------------------- #
MODELO = "claude-opus-5-5"
ESFUERZO = "medium"                    # output_config.effort, fijo; no se comparan esfuerzos sobre el material
MAX_TOKENS = 16000                     # deja lugar al razonamiento, sin streaming
MAX_TOKENS_REINTENTO_CORTE = MAX_TOKENS   # el mismo valor: más alto pide streaming, y la caché no lo captura
THINKING = True                        # el razonamiento no se apaga: es adaptativo, y el pedido no lleva `thinking`
CODE_VER_BASE = "juez-tripletas-v3"    # bump del sufijo ante un cambio de lógica de este módulo
REPS = 3
CLAVES_DEL_PEDIDO = ("model", "max_tokens", "output_config", "system", "messages")
RECHAZO = "refusal"                    # stop_reason de un pedido que la API rechaza: sin voto, contado

LLM_CACHE_REL = "data/experiment/evaluacion/llm_cache.py"
LLM_CACHE_SHA256 = "fc86b0e48df464d01d87aa1d8067168d2d522f66ead53f594092a16484c22752"

CARACTERES_POR_TOKEN = 3.06            # razón del §8 del pre-registro (no es el tokenizador de la API)
COTA_FACTOR = 1.3                      # margen de la cota por caracteres de una llamada (guarda del tope)

COMPONENTES = PJ.COMPONENTES
RASGOS = PJ.RASGOS
VALORES_COMPONENTE = ("sostenido", "contradicho", "no_consta")
VEREDICTOS = ("correcta", "incorrecta", "incorrecta_por_no_consta", "adjudicacion")
VIA_DE_LA_INCORRECTA = {"incorrecta": "contradicho", "incorrecta_por_no_consta": "no_consta"}
VIA_MIXTA = "mixta"
IMPORTANCIAS = ("esencial", "util", "accesoria")
SIN_CONSENSO = "sin_consenso"
CLAVES_SALIDA = ("componentes", "requiere_adjudicacion_humana", "adjudicacion", "rasgos")


class SalidaMalFormada(ValueError):
    pass


def code_ver(prompt_sha256: str) -> str:
    """CODE_VER con el modelo, el esfuerzo y el sha256 del prompt: otro prompt, otro modelo u otro esfuerzo nunca comen
    hits de este."""
    return f"{CODE_VER_BASE}+modelo={MODELO}+esfuerzo={ESFUERZO}+prompt={prompt_sha256[:12]}"


# --------------------------------------------------------------------------- #
# Pedido                                                                      #
# --------------------------------------------------------------------------- #
def mensaje_usuario(ficha: dict) -> str:
    return f"{PJ.ENCABEZADO_MENSAJE}\n\n{PJ.texto_ficha(ficha)}"


def construir_kwargs(bloques: tuple[str, str], ficha: dict, max_tokens: int = MAX_TOKENS) -> dict:
    """El system en dos bloques (el fijo y el de los casos), cada uno con su marca de caché del prompt. Sin
    `temperature` ni `thinking`; el esfuerzo, en output_config."""
    return {
        "model": MODELO,
        "max_tokens": max_tokens,
        "output_config": {"effort": ESFUERZO},
        "system": [{"type": "text", "text": b, "cache_control": {"type": "ephemeral"}} for b in bloques],
        "messages": [{"role": "user", "content": mensaje_usuario(ficha)}],
    }


def texto_del_pedido(kwargs: dict) -> tuple[str, str]:
    """(system, mensaje) de un pedido, para los controles y la cota de tokens."""
    return ("".join(b["text"] for b in kwargs["system"]), kwargs["messages"][0]["content"])


COLUMNAS_HOJA_JUICIO = tuple(c for c in PJ.COLUMNAS_POOL if c not in ("orden", "ref", "predicado", "clave"))
_PATRON_CAMPO_FUERA = re.compile(r'"(ref|lote|posicion|clave)"\s*:')
_PATRON_REF = re.compile(r'"(V\d{3}|T\d{3}|P\d{2}|PR\d|R\d)"')   # v3: también las refs de T
_PATRON_COLUMNA_HOJA = re.compile(r"\b(" + "|".join(c for c in COLUMNAS_HOJA_JUICIO if c != "nota")
                                  + r"|clasificacion_de_la_autora)\b")
CASOS_V1_1 = ("<casos_resueltos>", "</casos_resueltos>")
CASOS_DEL_GOLD = ("<casos_resueltos_del_gold>", "</casos_resueltos_del_gold>")
CASOS_POR_COMPONENTE = ("<casos_resueltos_por_componente>", "</casos_resueltos_por_componente>")   # v3: los de la enmienda 5
_PATRON_MARCA_GOLD = re.compile(r"\b(marca_de_la_autora|porque_del_texto|cita_del_texto)\b")


def _region(texto: str, etiquetas: tuple[str, str]) -> tuple[int, int] | None:
    i, j = texto.find(etiquetas[0]), texto.find(etiquetas[1])
    return (i, j + len(etiquetas[1])) if 0 <= i < j else None


def controlar_pedido(kwargs: dict, *, claves: set, notas_que_entran: list, notas_que_no_entran: list) -> list[str]:
    """Problemas de un pedido (lista vacía si no hay):
      - el pedido de Opus 5.5: sus claves, el modelo, el esfuerzo y max_tokens; ni `temperature` ni `thinking`;
      - ningún `ref`, `lote`, `posicion` ni `clave`, ni como campo ni como valor;
      - las notas que entran, solo dentro de los casos resueltos de la v1.1; las que no entran (la de P16 y el original
        de cada reescrita), en ningún lado;
      - ningún campo de la hoja de la autora fuera de los casos de la v1.1, y ninguna marca de los casos del gold fuera
        de su bloque;
      - v3: el bloque de los casos por componente (enmienda 5, punto 6) cuenta como bloque de casos, como el del gold: ni
        una nota del pool ni un campo de la hoja de la autora adentro.
    Compara textos enteros y nunca los muestra."""
    prob = []
    if tuple(sorted(kwargs)) != tuple(sorted(CLAVES_DEL_PEDIDO)):
        prob.append(f"pedido: claves {sorted(kwargs)}")
    if kwargs.get("model") != MODELO or kwargs.get("output_config") != {"effort": ESFUERZO} \
            or kwargs.get("max_tokens") != MAX_TOKENS:
        prob.append("pedido: el modelo, el esfuerzo o max_tokens no son los decididos")
    sistema, mensaje = texto_del_pedido(kwargs)
    cuerpo = mensaje[len(PJ.ENCABEZADO_MENSAJE):]
    try:
        ficha = json.loads(cuerpo)
        if set(ficha) & set(PJ.CAMPOS_FUERA_DEL_PEDIDO):
            prob.append(f"mensaje: campos {sorted(set(ficha) & set(PJ.CAMPOS_FUERA_DEL_PEDIDO))}")
    except json.JSONDecodeError:
        prob.append("mensaje: la ficha no es JSON")
    r11, rg = _region(sistema, CASOS_V1_1), _region(sistema, CASOS_DEL_GOLD)
    rc = _region(sistema, CASOS_POR_COMPONENTE)
    if r11 is None:
        prob.append("system: sin los casos resueltos de la v1.1")
    cortes = sorted(r for r in (r11, rg, rc) if r)
    fuera_casos, desde = "", 0
    for a, b in cortes:
        fuera_casos += sistema[desde:a]
        desde = b
    fuera_casos += sistema[desde:]
    casos_gold = sistema[rg[0]:rg[1]] if rg else ""
    casos_comp = sistema[rc[0]:rc[1]] if rc else ""
    for nombre, texto in (("mensaje", mensaje), ("system", sistema)):
        if _PATRON_CAMPO_FUERA.search(texto):
            prob.append(f"{nombre}: un campo ref/lote/posicion/clave")
        if _PATRON_REF.search(texto):
            prob.append(f"{nombre}: una ref de ficha como valor")
        if any(k in texto for k in claves):
            prob.append(f"{nombre}: una clave de arista")
        if any(n.strip() and n.strip() in texto for n in notas_que_no_entran):
            prob.append(f"{nombre}: el texto de una nota que no entra")
    for nombre, texto in (("mensaje", mensaje), ("system fuera de los casos", fuera_casos)):
        if _PATRON_COLUMNA_HOJA.search(texto):
            prob.append(f"{nombre}: un campo de la hoja de la autora")
        if _PATRON_MARCA_GOLD.search(texto):
            prob.append(f"{nombre}: una marca de los casos del gold fuera de su bloque")
        if any(n.strip() and n.strip() in texto for n in notas_que_entran):
            prob.append(f"{nombre}: el texto de una nota fuera de los casos resueltos")
    if any(n.strip() and n.strip() in casos_gold for n in notas_que_entran):
        prob.append("system: el texto de una nota del pool dentro de los casos del gold")
    if _PATRON_COLUMNA_HOJA.search(casos_gold):
        prob.append("system: un campo de la hoja del pool dentro de los casos del gold")
    if any(n.strip() and n.strip() in casos_comp for n in notas_que_entran):
        prob.append("system: el texto de una nota del pool dentro de los casos por componente")
    if _PATRON_COLUMNA_HOJA.search(casos_comp):
        prob.append("system: un campo de la hoja del pool dentro de los casos por componente")
    return prob


# --------------------------------------------------------------------------- #
# Parseo                                                                      #
# --------------------------------------------------------------------------- #
def extraer_texto(resp) -> str:
    """Solo los bloques de texto: los de razonamiento que vienen antes no se analizan."""
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def bloques_de_la_respuesta(resp) -> dict:
    """Cuántos bloques de cada tipo trae la respuesta y los caracteres de texto (para el humo y los registros)."""
    tipos = Counter(getattr(b, "type", "?") for b in resp.content)
    return {"tipos": dict(sorted(tipos.items())), "caracteres_de_texto": len(extraer_texto(resp)),
            "texto_despues_del_razonamiento": _texto_despues_del_razonamiento(resp)}


def _texto_despues_del_razonamiento(resp) -> bool | None:
    """True si todos los bloques de razonamiento van antes del primer bloque de texto; None si no hay razonamiento."""
    tipos = [getattr(b, "type", "") for b in resp.content]
    razon = [i for i, t in enumerate(tipos) if t in ("thinking", "redacted_thinking")]
    texto = [i for i, t in enumerate(tipos) if t == "text"]
    if not razon:
        return None
    return bool(texto) and max(razon) < min(texto)


def es_rechazo(resp) -> bool:
    return getattr(resp, "stop_reason", None) == RECHAZO


def categoria_del_rechazo(resp) -> str | None:
    d = getattr(resp, "stop_details", None)
    return getattr(d, "category", None) if d is not None else None


def parsear_salida(texto: str) -> dict:
    """Valida la salida entera; cualquier desvío levanta SalidaMalFormada (el driver reintenta una vez)."""
    ini, fin = texto.find("{"), texto.rfind("}")
    if ini < 0 or fin <= ini:
        raise SalidaMalFormada("sin objeto JSON")
    try:
        d = json.loads(texto[ini:fin + 1])
    except json.JSONDecodeError as e:
        raise SalidaMalFormada(f"JSON inválido: {e.msg}")
    if not isinstance(d, dict) or set(d) != set(CLAVES_SALIDA):
        raise SalidaMalFormada(f"claves {sorted(d) if isinstance(d, dict) else type(d).__name__}")
    comps = d["componentes"]
    if not isinstance(comps, dict) or set(comps) != set(COMPONENTES):
        raise SalidaMalFormada("componentes: no son los cinco")
    limpio = {}
    for c in COMPONENTES:
        x = comps[c]
        if not isinstance(x, dict) or x.get("valor") not in VALORES_COMPONENTE:
            raise SalidaMalFormada(f"componente {c}: valor inválido")
        if not isinstance(x.get("motivo", ""), str):
            raise SalidaMalFormada(f"componente {c}: motivo no es texto")
        limpio[c] = {"valor": x["valor"], "motivo": x.get("motivo", "")}
    req = d["requiere_adjudicacion_humana"]
    if not isinstance(req, bool):
        raise SalidaMalFormada("requiere_adjudicacion_humana no es booleano")
    adj = d["adjudicacion"]
    if req:
        if (not isinstance(adj, dict) or not isinstance(adj.get("componentes"), list) or not adj["componentes"]
                or any(c not in COMPONENTES for c in adj["componentes"])
                or not isinstance(adj.get("motivo"), str) or not adj["motivo"].strip()):
            raise SalidaMalFormada("adjudicacion: falta la lista de componentes o el motivo")
        adj = {"componentes": list(adj["componentes"]), "motivo": adj["motivo"]}
    elif adj is not None:
        raise SalidaMalFormada("adjudicacion no es null sin la marca")
    ras = d["rasgos"]
    if not isinstance(ras, dict) or set(ras) != set(RASGOS) or any(not isinstance(ras[g], bool) for g in RASGOS):
        raise SalidaMalFormada("rasgos: no son los tres booleanos")
    return {"componentes": limpio, "requiere_adjudicacion_humana": req, "adjudicacion": adj,
            "rasgos": {g: ras[g] for g in RASGOS}}


# --------------------------------------------------------------------------- #
# Regla del §4.2 e importancia (puras)                                        #
# --------------------------------------------------------------------------- #
def veredicto_regla(valores: dict, requiere_adjudicacion: bool) -> str:
    """valores: {componente: sostenido|contradicho|no_consta}. La regla del §4.2, tal cual (ver el docstring)."""
    if set(valores) != set(COMPONENTES) or any(v not in VALORES_COMPONENTE for v in valores.values()):
        raise ValueError("valores fuera del dominio")
    if any(v == "contradicho" for v in valores.values()):
        return "incorrecta"
    if requiere_adjudicacion:
        return "adjudicacion"
    if valores["sujeto"] == "sostenido" and valores["predicado"] == "sostenido":
        return "correcta"
    return "incorrecta_por_no_consta"


def dos_clases(veredicto) -> str | None:
    """La clase del acuerdo del §4.6: correcta o incorrecta (por las dos vías); None si el juez no decide (adjudicación
    o sin consenso)."""
    if veredicto == "correcta":
        return "correcta"
    if veredicto in VIA_DE_LA_INCORRECTA:
        return "incorrecta"
    return None


def importancia_regla(rasgos: dict) -> str:
    c, v, p = (bool(rasgos[g]) for g in RASGOS)
    if c and (v or p):
        return "esencial"
    if not c and not v:
        return "accesoria"
    return "util"


def computar(salida: dict) -> dict:
    vals = {c: salida["componentes"][c]["valor"] for c in COMPONENTES}
    return {"veredicto": veredicto_regla(vals, salida["requiere_adjudicacion_humana"]),
            "importancia": importancia_regla(salida["rasgos"])}


# --------------------------------------------------------------------------- #
# Agregado modal (§4.4)                                                       #
# --------------------------------------------------------------------------- #
def agregar_modal(votos: list, reps: int = REPS) -> dict:
    """votos: un valor por repetición (None si la repetición no dio salida válida). Modal = el valor con al menos 2
    de las 3 repeticiones; si no hay, sin_consenso. Un error no vota."""
    validos = [v for v in votos if v is not None]
    clave = lambda v: v if isinstance(v, str) else json.dumps(v)
    cuenta = Counter(clave(v) for v in validos)
    top_k, top_n = (cuenta.most_common(1)[0] if cuenta else (None, 0))
    mayoria = reps // 2 + 1
    modal = next(v for v in validos if clave(v) == top_k) if top_n >= mayoria else SIN_CONSENSO
    if top_n == reps:
        dist = "unanimidad"
    elif top_n >= mayoria and len(validos) == reps:
        dist = "2_a_1"
    elif top_n >= mayoria:
        dist = "mayoria_con_error"
    else:
        dist = "sin_consenso"
    return {"modal": modal, "distribucion": dist, "n_validos": len(validos),
            "votos": {k: n for k, n in sorted(cuenta.items())}}


def clase_del_veredicto(veredicto):
    """La clase con que vota un veredicto en el modal: las dos vías de la incorrecta votan como incorrecta."""
    return "incorrecta" if veredicto in VIA_DE_LA_INCORRECTA else veredicto


def agregar_veredicto(veredictos: list, reps: int = REPS) -> dict:
    """El modal del veredicto (decisión del FRENO v1.1, para el v1.2): las dos vías de la incorrecta (incorrecta e
    incorrecta_por_no_consta) votan juntas, como incorrecta, igual que en el acuerdo de dos clases del §4.6. El modal
    sale de correcta, incorrecta y adjudicacion con el agregado de siempre (mayoría de 2 de 3; si no, sin_consenso; un
    error no vota). Si el modal es incorrecta, su vía es la que junta al menos 2 de esos votos; con una y una, «mixta».
    `votos_por_veredicto` guarda los veredictos computados, sin juntar."""
    a = agregar_modal([clase_del_veredicto(v) if v is not None else None for v in veredictos], reps)
    via = None
    if a["modal"] == "incorrecta":
        c = Counter(VIA_DE_LA_INCORRECTA[v] for v in veredictos if v in VIA_DE_LA_INCORRECTA)
        via = next((k for k, n in c.items() if n >= 2), VIA_MIXTA)
    a["via"] = via
    a["votos_por_veredicto"] = {k: n for k, n in sorted(Counter(v for v in veredictos if v is not None).items())}
    return a


def agregar_ficha(salidas: list) -> dict:
    """salidas: la salida parseada de cada repetición (None si falló). Por dimensión: veredicto (agregar_veredicto),
    importancia, cada componente, la marca de adjudicación y cada rasgo (agregar_modal)."""
    comp = [computar(s) if s else None for s in salidas]
    dims = {"veredicto": [c["veredicto"] if c else None for c in comp],
            "importancia": [c["importancia"] if c else None for c in comp],
            "requiere_adjudicacion_humana": [s["requiere_adjudicacion_humana"] if s else None for s in salidas]}
    for c in COMPONENTES:
        dims[f"comp_{c}"] = [s["componentes"][c]["valor"] if s else None for s in salidas]
    for g in RASGOS:
        dims[f"rasgo_{g}"] = [s["rasgos"][g] if s else None for s in salidas]
    out = {d: agregar_modal(v) for d, v in dims.items() if d != "veredicto"}
    return {"veredicto": agregar_veredicto(dims["veredicto"]), **out}


# --------------------------------------------------------------------------- #
# Sujetos sin definición (decisión del §53)                                   #
# --------------------------------------------------------------------------- #
def sujetos_sin_definicion(ficha: dict, ids_bloque) -> list[str]:
    """Los nodos Sujeto de la ficha (origen o destino) cuyo id no aparece en el bloque del catálogo con el patrón
    Sujeto_[A-Za-z0-9_]+. La marca es del código: no entra en el pedido."""
    ids = {ficha[l]["id"] for l in ("origen", "destino") if ficha[l]["tipo"] == "Sujeto"}
    return sorted(i for i in ids if i not in ids_bloque)


# --------------------------------------------------------------------------- #
# Cliente (uno por repetición; base y namespace propios)                      #
# --------------------------------------------------------------------------- #
def cargar_llm_cache(repo: Path):
    """Importa llm_cache.py del repo por ruta, con su sha256 congelado (se importa, no se edita)."""
    p = Path(repo).resolve() / LLM_CACHE_REL
    if hashlib.sha256(p.read_bytes()).hexdigest() != LLM_CACHE_SHA256:
        raise SystemExit("FRENO: llm_cache.py no es el sellado")
    previo = sys.modules.get("llm_cache")
    if previo is not None:
        if Path(previo.__file__).resolve() != p:
            raise SystemExit(f"FRENO: llm_cache ya importado desde {previo.__file__}")
        return previo
    spec = importlib.util.spec_from_file_location("llm_cache", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["llm_cache"] = mod
    spec.loader.exec_module(mod)
    return mod


def control_del_cliente_de_la_cache(lc) -> dict:
    """Lo que el cliente de la caché captura, leído en su código (sin ninguna llamada): solo `messages.create`, sin
    streaming, y la llamada real con los mismos kwargs. Por eso el reintento por corte no puede subir max_tokens: por
    encima del límite sin streaming, el SDK frena el pedido antes de mandarlo y la caché no tiene cómo capturarlo."""
    fuente = inspect.getsource(lc._CachingMessages)
    metodos = sorted(n for n, v in vars(lc._CachingMessages).items() if callable(v) and not n.startswith("__"))
    return {"metodos_de_messages": metodos, "tiene_stream": "stream" in metodos,
            "llama_a_create_real": "o._real.messages.create(**kwargs)" in fuente,
            "pide_stream": "stream=" in fuente or ".stream(" in fuente,
            "guarda_la_respuesta_entera": "resp.model_dump(mode=\"json\")" in inspect.getsource(lc._CachingMessages.create)}


def limite_sin_streaming(anthropic_mod=None) -> dict:
    """El límite de max_tokens sin streaming del SDK para MODELO, de su propio código (_calculate_nonstreaming_timeout y
    MODEL_NONSTREAMING_TOKENS), sin red: si 16000 pasa y si el doble pediría streaming."""
    import anthropic as _a
    a = anthropic_mod or _a
    from anthropic._constants import MODEL_NONSTREAMING_TOKENS
    tope_modelo = MODEL_NONSTREAMING_TOKENS.get(MODELO)

    def pasa(mt: int) -> bool:
        try:     # el método no usa el cliente: se llama sin construir ninguno (sin clave)
            a.Anthropic._calculate_nonstreaming_timeout(None, mt, tope_modelo)
            return True
        except ValueError:
            return False
    lo, hi = MAX_TOKENS, 8 * MAX_TOKENS          # el mayor max_tokens que pasa, por bisección
    if not pasa(lo) or pasa(hi):
        mayor = None
    else:
        while hi - lo > 1:
            mid = (lo + hi) // 2
            lo, hi = (mid, hi) if pasa(mid) else (lo, mid)
        mayor = lo
    return {"sdk": a.__version__, "tope_del_modelo_en_el_sdk": tope_modelo, "max_tokens": MAX_TOKENS,
            "pasa_sin_streaming": pasa(MAX_TOKENS), "pasa_el_doble": pasa(2 * MAX_TOKENS), "mayor_que_pasa": mayor}


def nombre_namespace(rep: int, reintento: bool = False) -> str:
    return f"juez_tripletas_v3_r{rep}" + ("_reintento" if reintento else "")


def namespace_rep(lc, rep: int, prompt_sha256: str, reintento: bool = False) -> str:
    return lc.make_namespace(nombre_namespace(rep, reintento), code_ver=code_ver(prompt_sha256), thinking=THINKING)


def db_path_rep(cache_dir: Path, db_prefix: str, rep: int) -> Path:
    return Path(cache_dir) / f"{db_prefix}_r{rep}.db"


def construir_cliente(lc, real_client, rep: int, *, db_path: Path, prompt_sha256: str, run_label: str,
                      reintento: bool = False):
    return lc.CachingClient(real_client, domain="juez_tripletas_v3", db_path=db_path,
                            namespace=namespace_rep(lc, rep, prompt_sha256, reintento),
                            thinking_enabled=THINKING, run_label=run_label)


def cliente_anthropic_real():
    """El SDK real, con su reintento nativo y su timeout por defecto (con el que controla el límite sin streaming). La
    clave la toma del entorno (ANTHROPIC_API_KEY): este código no lee ningún .env ni tiene la clave escrita."""
    import anthropic
    return anthropic.Anthropic(max_retries=3)


def verificar_cross_hits(db_paths: list) -> dict:
    """Como ev2_juez/driver_calibracion.py:260-277: (1) las claves de cada base son disjuntas de a pares; (2) los hits
    por run_label dentro de cada base."""
    keys, hits = {}, {}
    for p in db_paths:
        conn = sqlite3.connect(str(p))
        keys[Path(p).name] = {r[0] for r in conn.execute("SELECT key FROM cache")}
        hits[Path(p).name] = dict(conn.execute("SELECT run_label, SUM(hit) FROM access_log GROUP BY run_label"))
        conn.close()
    nombres = sorted(keys)
    inter = {f"{a}∩{b}": len(keys[a] & keys[b]) for i, a in enumerate(nombres) for b in nombres[i + 1:]}
    return {"keys_por_db": {n: len(keys[n]) for n in nombres}, "intersecciones": inter,
            "cross_hits": sum(inter.values()), "hits_por_label": hits}


# --------------------------------------------------------------------------- #
# Guarda del gasto                                                            #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Precios:
    """USD por millón de tokens: entrada, salida, escritura y lectura de caché (llegan por la línea de comandos)."""
    entrada: float
    salida: float
    escritura_cache: float
    lectura_cache: float


# Lo decidido (los precios, los de la v2: §89 y la tabla de la API para claude-opus-5-5; los topes, la enmienda 5, punto 14):
# el driver frena si lo que recibe por la línea de comandos no es esto.
PRECIOS_DECIDIDOS = Precios(entrada=4.00, salida=20.00, escritura_cache=5.00, lectura_cache=0.20)
TOPES_DECIDIDOS = {"humo": (2.0, 1.70), "iteracion": (42.0, 35.70), "validacion": (42.0, 35.70),
                   "restantes_200": (83.33, 70.83)}
MIN_PAGADAS_POR_PROCESO = 3            # el freno proyecta con al menos 3 pagadas por proceso (la v1: 3 en total)


def costo_usd(usage: dict, pr: Precios) -> float:
    return (usage.get("input_tokens", 0) * pr.entrada + usage.get("output_tokens", 0) * pr.salida
            + usage.get("cache_write_tokens", 0) * pr.escritura_cache
            + usage.get("cache_read_tokens", 0) * pr.lectura_cache) / 1e6


def tokens_por_caracteres(texto: str) -> int:
    return math.ceil(len(texto) / CARACTERES_POR_TOKEN)


def cota_llamada_por_caracteres(kwargs: dict, pr: Precios) -> float:
    """Cota de una llamada sin haberla hecho: el system a la tarifa mayor entre escritura y entrada, el mensaje a la
    de entrada y la salida entera (max_tokens, con el razonamiento), con el margen COTA_FACTOR sobre los tokens por
    caracteres."""
    sistema, mensaje = texto_del_pedido(kwargs)
    t_sis, t_msj = tokens_por_caracteres(sistema), tokens_por_caracteres(mensaje)
    return (COTA_FACTOR * (t_sis * max(pr.escritura_cache, pr.entrada) + t_msj * pr.entrada)
            + kwargs["max_tokens"] * pr.salida) / 1e6


def filas_pagadas(db_paths: list) -> list[dict]:
    """Una fila por llamada pagada (cada miss guarda su crudo en la tabla cache), con sus cuatro campos de tokens. Con
    las repeticiones en paralelo, la base de otro proceso puede existir sin su tabla todavía (la está creando): cuenta
    como vacía."""
    out = []
    for p in db_paths:
        if not Path(p).exists():
            continue
        conn = sqlite3.connect(str(p), timeout=30)
        try:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cache'").fetchone() is None:
                continue
            for r in conn.execute("SELECT input_tokens, output_tokens, cache_read_tokens, cache_write_tokens FROM cache"):
                out.append({"input_tokens": r[0], "output_tokens": r[1], "cache_read_tokens": r[2],
                            "cache_write_tokens": r[3]})
        finally:
            conn.close()
    return out


def estado_de_las_bases(db_paths: list, pr: Precios) -> dict:
    """El gasto de las bases (todas, las escriba quien las escriba): pagadas, gasto, mediana y máximo por llamada y
    tokens."""
    filas = filas_pagadas(db_paths)
    costos = [costo_usd(f, pr) for f in filas]
    return {"pagadas": len(filas), "gasto_usd": sum(costos),
            "mediana_usd": statistics.median(costos) if costos else 0.0,
            "max_usd": max(costos) if costos else 0.0,
            "tokens": {k: sum(f[k] for f in filas) for k in ("input_tokens", "output_tokens",
                                                              "cache_read_tokens", "cache_write_tokens")}}


class GuardaGasto:
    """El gasto real sale de las bases de la corrida (tokens por fila × precios), no de contadores en memoria: las tres
    bases, también cuando cada una la escribe otro proceso. Antes de cada llamada, bajo un cerrojo (fcntl.flock sobre
    guarda.lock, en la carpeta de las bases):
      - tope: si gasto + reservas en vuelo de los otros procesos + cota de la llamada > tope, corta (la cota es la
        mayor entre la de caracteres y la llamada más cara observada);
      - freno: con MIN_PAGADAS_POR_PROCESO × `paralelo` llamadas pagadas o más, si gasto + restantes × mediana del costo
        por llamada > freno, corta. `restantes` son las llamadas que les faltan a las tres repeticiones (las da el
        driver). La mediana no se deja llevar por la escritura del prompt en la caché, que en paralelo puede pasar una
        vez por proceso;
      - si deja llamar, deja escrita su reserva (la cota) en en_vuelo_<proceso>.json, y `liberar` la borra cuando la
        llamada vuelve (la caché ya escribió su fila). Una reserva que quedó de un proceso cortado de golpe hace más
        prudente al resto, nunca menos; el mismo proceso la borra al arrancar."""

    def __init__(self, precios: Precios, tope: float, freno: float, db_paths: list, *, paralelo: int = 1,
                 proceso: str = "unico", reservas_dir: Path | None = None):
        if not (0 < freno <= tope):
            raise SystemExit("FRENO: hace falta 0 < freno <= tope")
        if paralelo < 1:
            raise SystemExit("FRENO: paralelo es la cantidad de procesos que comparten las bases (1 o más)")
        self.pr, self.tope, self.freno, self.db_paths = precios, tope, freno, list(db_paths)
        self.paralelo, self.proceso = paralelo, proceso
        self.dir = Path(reservas_dir) if reservas_dir else Path(self.db_paths[0]).parent
        self.dir.mkdir(parents=True, exist_ok=True)
        self._cerrojo_p = self.dir / "guarda.lock"
        self._mia = self.dir / f"en_vuelo_{proceso}.json"
        self.liberar()

    @contextmanager
    def _cerrojo(self):
        with self._cerrojo_p.open("a") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def reservas_de_los_otros(self) -> float:
        total = 0.0
        for p in sorted(self.dir.glob("en_vuelo_*.json")):
            if p.name == self._mia.name:
                continue
            try:
                total += float(json.loads(p.read_text(encoding="utf-8"))["usd"])
            except (ValueError, KeyError, OSError):
                total += self.tope          # una reserva ilegible no se adivina: frena
        return total

    def estado(self) -> dict:
        return estado_de_las_bases(self.db_paths, self.pr)

    def permitir(self, kwargs: dict, restantes: int) -> tuple[bool, dict]:
        with self._cerrojo():
            e = self.estado()
            cota = max(cota_llamada_por_caracteres(kwargs, self.pr), e["max_usd"])
            otros = self.reservas_de_los_otros()
            if e["gasto_usd"] + otros + cota > self.tope:
                return False, {"motivo": "tope", "gasto_usd": round(e["gasto_usd"], 4), "cota_llamada_usd": round(cota, 4),
                               "reservas_de_los_otros_usd": round(otros, 4), "tope_usd": self.tope,
                               "pagadas": e["pagadas"]}
            if e["pagadas"] >= MIN_PAGADAS_POR_PROCESO * self.paralelo:
                proy = e["gasto_usd"] + restantes * e["mediana_usd"]
                if proy > self.freno:
                    return False, {"motivo": "freno", "gasto_usd": round(e["gasto_usd"], 4),
                                   "proyeccion_usd": round(proy, 4), "freno_usd": self.freno,
                                   "pagadas": e["pagadas"], "restantes": restantes}
            self._mia.write_text(json.dumps({"usd": cota, "proceso": self.proceso,
                                             "hora": datetime.now().astimezone().isoformat(timespec="seconds")}),
                                 encoding="utf-8")
            return True, {"cota_usd": round(cota, 4), "reservas_de_los_otros_usd": round(otros, 4)}

    def liberar(self) -> None:
        with self._cerrojo():
            self._mia.unlink(missing_ok=True)
