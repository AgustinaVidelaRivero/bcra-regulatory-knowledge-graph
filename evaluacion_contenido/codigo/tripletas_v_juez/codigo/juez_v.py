"""
juez_v.py — U-TRIP-V-JUEZ: el juez de precisión de la etapa V. Rige el pre-registro de la evaluación por tripletas,
FIRMADO (§4; firma en 4afbe511, con sus notas al pie y sus enmiendas 1 y 2).

Qué hay acá (el driver es correr_juez_v.py; el prompt, prompt_juez_v.py):
  - el pedido: el prompt v1.1 congelado como system, en dos bloques con su marca de caché del prompt cada uno (el fijo
    y el de los casos), y la ficha sin ref, lote, posicion ni clave como único mensaje (§4.1: ciego al grafo de origen y
    a las etiquetas de la autora);
  - el cliente: CachingClient de evaluacion/llm_cache.py (del cuarteto sellado: se importa por ruta y con su sha256,
    no se edita), uno por repetición, con su base y su namespace (juez_tripletas_r1, _r2 y _r3, con la versión de
    código y la marca de thinking), como data/experiment/ev2_juez/juez.py:150-171. La clave de la caché es
    sha256(namespace + request): el mismo pedido en tres namespaces son tres llamadas;
  - el parseo de la salida (un JSON por ficha) y su validación;
  - la regla del §4.2 y la de la importancia, en funciones puras (veredicto_regla, importancia_regla);
  - el agregado por veredicto modal: mayoría de 2 de las 3 repeticiones; si no la hay, `sin_consenso` (§4.4). En el
    veredicto (v1.2) las dos vías de la incorrecta votan juntas, como incorrecta, y el modal lleva su vía
    (agregar_veredicto);
  - el control de 0 cruces entre las tres bases antes de agregar;
  - la marca de los Sujetos sin definición en el bloque del catálogo (decisión del §53): es del código, no del juez,
    y no entra en el pedido;
  - la guarda del gasto: el costo por llamada con los precios que llegan por la línea de comandos (nunca escritos en
    el código, como correr_calibracion.py:5 y :59-60), el tope por corrida y el freno por proyección (por llamada en el
    gold, por caso en la calibración); corta antes de llamar.

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

import hashlib
import importlib.util
import json
import math
import re
import sqlite3
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prompt_juez_v as PJ  # noqa: E402

# --------------------------------------------------------------------------- #
# Instrumento (pre-registro §4.1)                                             #
# --------------------------------------------------------------------------- #
MODELO = "claude-sonnet-4-6"
TEMPERATURE = 0.0
MAX_TOKENS = 2000
MAX_TOKENS_REINTENTO_CORTE = 4000      # el reintento de una salida cortada por max_tokens
THINKING = False
CODE_VER_BASE = "juez-tripletas-v1_1"  # bump del sufijo ante un cambio de lógica de este módulo
CODE_VER_BASE_V1_4 = "juez-tripletas-v1_4"   # con la bandera --modalidad-por-codigo (otro namespace)
REPS = 3

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


def code_ver(prompt_sha256: str, modalidad_por_codigo: bool = False) -> str:
    """CODE_VER con el sha256 del prompt (patrón de ev2_juez/juez.py:53): otro prompt nunca come hits de este. Con la
    bandera del v1.4, la base es CODE_VER_BASE_V1_4."""
    return f"{CODE_VER_BASE_V1_4 if modalidad_por_codigo else CODE_VER_BASE}+prompt={prompt_sha256[:12]}"


# --------------------------------------------------------------------------- #
# v1.4: la modalidad la computa el código (bandera --modalidad-por-codigo)    #
# --------------------------------------------------------------------------- #
# La recalibración única del §4.7 (decisión escrita de la autora del 20/10/2026, recibida a las 16:27:56). El juez cita,
# por cada nodo normativo de la arista, la marca de su fuerza y su clase; el código controla que la marca esté literal en
# la evidencia y la compara con el tipo del nodo con esta tabla fija, decidida antes de correr. «La Restriccion de tipo
# límite admite prohibición o deber» (la misma decisión). La justificación es del texto: el componente ya estaba
# definido como «deber, prohibición, permiso, condición», y el prefijo decide los tipos por las marcas del texto
# (sección 2 del prompt, 6dddd215…).
TABLA_MODALIDAD = {
    "Obligacion": ("deber",),
    "Restriccion:prohibicion": ("prohibicion",),
    "Restriccion:limite_cuantitativo": ("prohibicion", "deber"),
    "Restriccion:limite_cualitativo": ("prohibicion", "deber"),
    "Potestad": ("permiso",),
    "Condicion": ("condicion",),
}
TABLA_MODALIDAD_SHA256 = "8490d5c46c02cb94106f79294b416253acd710300ca82ffbff46dc8a7d0bbe6a"   # json canónico de la tabla
TIPOS_CON_MODALIDAD = ("Obligacion", "Restriccion", "Potestad", "Condicion")
CLASES_MODALIDAD = ("deber", "prohibicion", "permiso", "condicion", "sin_marca")
EXTREMOS = ("origen", "destino")
# «Literal» es la condición de los tramos de las fichas: verificar_tramo de validador_r2.py:219, nivel exacta o tokens,
# con la holgura con que el validador verifica el tramo de un nodo (pol.holgura, el parámetro mencion_holgura_tokens
# de la política; :296-304 y verificar_tramo_entidad, contra el texto propio más el heredado). Se importa del repo por
# ruta, con su sha256, sin escribir en él.
VALIDADOR_REL = "data/experiment/pyd_r2/code/validador_r2.py"
VALIDADOR_SHA256 = "f60be782acf2758d19fc32ed047e2bb592001e4762f43e18980322d01b5dc86b"
POLITICA_R2_REL = "data/experiment/pyd_r2/politica_campos_r2.json"
POLITICA_R2_SHA256 = "82e8752aea1d6ad869d6023d303c0af45182dd9333753681787d7a581ef6d00b"
HOLGURA_TRAMO_NODO = 2
NIVELES_LITERALES = ("exacta", "tokens")


def sha_tabla_modalidad(tabla: dict = TABLA_MODALIDAD) -> str:
    return hashlib.sha256(json.dumps({k: list(v) for k, v in tabla.items()}, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


if sha_tabla_modalidad() != TABLA_MODALIDAD_SHA256:
    raise SystemExit("FRENO: TABLA_MODALIDAD no es la fijada antes de correr")


def cargar_verificador(repo: Path):
    """verificar(marca, texto) -> nivel («exacta», «tokens» o «no»), con verificar_tramo del validador del repo y la
    holgura de la política (2). Controla el sha256 del validador y de la política."""
    repo = Path(repo).resolve()
    p = repo / VALIDADOR_REL
    if hashlib.sha256(p.read_bytes()).hexdigest() != VALIDADOR_SHA256:
        raise SystemExit("FRENO: validador_r2.py no es el esperado (f60be782…)")
    if hashlib.sha256((repo / POLITICA_R2_REL).read_bytes()).hexdigest() != POLITICA_R2_SHA256:
        raise SystemExit("FRENO: politica_campos_r2.json no es la esperada (82e8752a…)")
    previo = sys.modules.get("validador_r2")
    if previo is not None and Path(previo.__file__).resolve() != p:
        raise SystemExit(f"FRENO: validador_r2 ya importado desde {previo.__file__}")
    if previo is None:
        spec = importlib.util.spec_from_file_location("validador_r2", p)
        previo = importlib.util.module_from_spec(spec)
        sys.modules["validador_r2"] = previo
        spec.loader.exec_module(previo)
    holgura = previo.politica_default().holgura
    if holgura != HOLGURA_TRAMO_NODO:
        raise SystemExit(f"FRENO: la holgura de la política es {holgura}, no {HOLGURA_TRAMO_NODO}")
    return lambda marca, texto: previo.verificar_tramo(marca, texto, holgura)[0]


def _parsear_modalidad(x) -> dict:
    """La modalidad del v1.4: `nodos` (una lista) y `motivo`; cada nodo con `extremo` (origen o destino), `clase` (las
    cinco) y `marca` vacía si y solo si la clase es sin_marca. Un extremo repetido también es mal formada."""
    if not isinstance(x, dict) or not isinstance(x.get("nodos"), list) or not isinstance(x.get("motivo"), str):
        raise SalidaMalFormada("modalidad: faltan los nodos o el motivo")
    nodos, vistos = [], set()
    for n in x["nodos"]:
        if not isinstance(n, dict) or n.get("extremo") not in EXTREMOS or n.get("clase") not in CLASES_MODALIDAD \
                or not isinstance(n.get("marca"), str):
            raise SalidaMalFormada("modalidad: un nodo sin extremo, clase o marca válidos")
        if (n["marca"].strip() == "") != (n["clase"] == "sin_marca"):
            raise SalidaMalFormada("modalidad: la marca va vacía si y solo si la clase es sin_marca")
        if n["extremo"] in vistos:
            raise SalidaMalFormada("modalidad: un extremo repetido")
        vistos.add(n["extremo"])
        nodos.append({"extremo": n["extremo"], "marca": n["marca"], "clase": n["clase"]})
    return {"nodos": nodos, "motivo": x["motivo"]}


def _fila_de_la_tabla(nodo: dict) -> tuple:
    """(clave de la fila, estado): «comparado», «tipo_no_previsto» (una Restriccion con otro tipo o sin él) o
    «no_es_de_esos_tipos»."""
    tipo = nodo.get("tipo")
    if tipo == "Restriccion":
        k = f"Restriccion:{(nodo.get('propiedades') or {}).get('tipo')}"
        return (k, "comparado") if k in TABLA_MODALIDAD else (None, "tipo_no_previsto")
    if tipo in TABLA_MODALIDAD:
        return tipo, "comparado"
    return None, "no_es_de_esos_tipos"


def computar_modalidad(salida: dict, ficha: dict, verificar) -> dict:
    """El valor de la modalidad, computado (v1.4), en salida["componentes"]["modalidad"]["valor"], con el detalle por
    nodo en ["computo"]. `ficha` es la ficha del pedido; `verificar(marca, texto)` da el nivel del tramo.
      - Por cada nodo de la ficha de tipo Obligacion, Restriccion (de un tipo de la tabla), Potestad o Condicion: si el
        juez no lo nombra, o su marca no está literal en la evidencia (el texto propio más el heredado de una procedencia),
        cuenta como sin_marca;
      - contradicho si algún nodo comparado tiene una clase (distinta de sin_marca) que su fila no admite; si no,
        no_consta si a alguno le falta la marca; si no, sostenido. Sin ningún nodo comparado, no_consta;
      - una Restriccion de otro tipo no se compara, y un nodo que el juez nombra y no es de esos tipos se ignora: los dos
        se declaran."""
    mod = salida["componentes"]["modalidad"]
    textos = ["\n".join([ev.get("texto_propio") or ""] + [h.get("texto") or "" for h in ev.get("heredado") or []])
              for ev in ficha.get("evidencia") or []]
    nombrados = {n["extremo"]: n for n in mod["nodos"]}
    nodos, declarados = [], []
    for ext in EXTREMOS:
        nodo = ficha.get(ext) or {}
        k, estado = _fila_de_la_tabla(nodo)
        if estado == "no_es_de_esos_tipos":
            if ext in nombrados:
                declarados.append({"extremo": ext, "tipo": nodo.get("tipo"), "motivo": "ignorado_no_es_de_esos_tipos"})
            continue
        if estado == "tipo_no_previsto":
            declarados.append({"extremo": ext, "tipo": "Restriccion",
                               "tipo_restriccion": (nodo.get("propiedades") or {}).get("tipo"),
                               "motivo": "tipo_no_previsto", "nombrado": ext in nombrados})
            continue
        n = nombrados.get(ext)
        literal = None
        if n is None:
            marca, dada, clase = "", None, "sin_marca"
        else:
            marca, dada = n["marca"], n["clase"]
            if dada == "sin_marca":
                clase = "sin_marca"
            else:
                niveles = [verificar(marca, tx) for tx in textos]
                literal = next((nv for nv in NIVELES_LITERALES if nv in niveles), "no")
                clase = dada if literal in NIVELES_LITERALES else "sin_marca"
        admitidas = TABLA_MODALIDAD[k]
        resultado = "sin_marca" if clase == "sin_marca" else ("coincide" if clase in admitidas else "no_coincide")
        nodos.append({"extremo": ext, "tipo": nodo.get("tipo"), "fila": k, "marca": marca, "clase_del_juez": dada,
                      "literal": literal, "clase": clase, "clases_admitidas": list(admitidas),
                      "resultado": resultado, "nombrado": n is not None})
    if any(x["resultado"] == "no_coincide" for x in nodos):
        valor = "contradicho"
    elif any(x["resultado"] == "sin_marca" for x in nodos) or not nodos:
        valor = "no_consta"
    else:
        valor = "sostenido"
    mod["valor"] = valor
    mod["computo"] = {"nodos": nodos, "declarados": declarados, "tabla_sha256": TABLA_MODALIDAD_SHA256}
    return salida


# --------------------------------------------------------------------------- #
# Pedido                                                                      #
# --------------------------------------------------------------------------- #
def mensaje_usuario(ficha: dict) -> str:
    return f"{PJ.ENCABEZADO_MENSAJE}\n\n{PJ.texto_ficha(ficha)}"


def construir_kwargs(bloques: tuple[str, str], ficha: dict, max_tokens: int = MAX_TOKENS) -> dict:
    """El system en dos bloques (el fijo y el de los casos), cada uno con su marca de caché del prompt."""
    return {
        "model": MODELO,
        "max_tokens": max_tokens,
        "temperature": TEMPERATURE,
        "system": [{"type": "text", "text": b, "cache_control": {"type": "ephemeral"}} for b in bloques],
        "messages": [{"role": "user", "content": mensaje_usuario(ficha)}],
    }


def texto_del_pedido(kwargs: dict) -> tuple[str, str]:
    """(system, mensaje) de un pedido, para los controles y la cota de tokens."""
    return ("".join(b["text"] for b in kwargs["system"]), kwargs["messages"][0]["content"])


COLUMNAS_HOJA_JUICIO = tuple(c for c in PJ.COLUMNAS_POOL if c not in ("orden", "ref", "predicado", "clave"))
_PATRON_CAMPO_FUERA = re.compile(r'"(ref|lote|posicion|clave)"\s*:')
_PATRON_REF = re.compile(r'"(V\d{3}|P\d{2}|PR\d|R\d)"')
_PATRON_COLUMNA_HOJA = re.compile(r"\b(" + "|".join(c for c in COLUMNAS_HOJA_JUICIO if c != "nota")
                                  + r"|clasificacion_de_la_autora)\b")


def controlar_pedido(kwargs: dict, *, claves: set, notas_que_entran: list, notas_que_no_entran: list) -> list[str]:
    """Problemas de un pedido (lista vacía si no hay): ningún `ref`, `lote`, `posicion` ni `clave`, ni como campo ni
    como valor; las notas que entran, solo dentro de los casos resueltos; las que no entran (la de P16 y el original de
    cada reescrita), en ningún lado; ningún campo de la hoja de la autora fuera de los casos. Compara textos enteros y
    nunca los muestra."""
    sistema, mensaje = texto_del_pedido(kwargs)
    prob = []
    cuerpo = mensaje[len(PJ.ENCABEZADO_MENSAJE):]
    try:
        ficha = json.loads(cuerpo)
        if set(ficha) & set(PJ.CAMPOS_FUERA_DEL_PEDIDO):
            prob.append(f"mensaje: campos {sorted(set(ficha) & set(PJ.CAMPOS_FUERA_DEL_PEDIDO))}")
    except json.JSONDecodeError:
        prob.append("mensaje: la ficha no es JSON")
    i, j = sistema.find("<casos_resueltos>"), sistema.find("</casos_resueltos>")
    fuera_casos = sistema[:i] + sistema[j:] if 0 <= i < j else sistema
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
        if any(n.strip() and n.strip() in texto for n in notas_que_entran):
            prob.append(f"{nombre}: el texto de una nota fuera de los casos resueltos")
    return prob


# --------------------------------------------------------------------------- #
# Parseo                                                                      #
# --------------------------------------------------------------------------- #
def extraer_texto(resp) -> str:
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def parsear_salida(texto: str, modalidad_por_codigo: bool = False) -> dict:
    """Valida la salida entera; cualquier desvío levanta SalidaMalFormada (el driver reintenta una vez). Con la bandera
    del v1.4, la modalidad trae `nodos` y `motivo` en lugar de `valor` (_parsear_modalidad); su valor lo pone después
    computar_modalidad."""
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
        if modalidad_por_codigo and c == "modalidad":
            limpio[c] = _parsear_modalidad(x)
            continue
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


def nombre_namespace(rep: int, reintento: bool = False) -> str:
    return f"juez_tripletas_r{rep}" + ("_reintento" if reintento else "")


def namespace_rep(lc, rep: int, prompt_sha256: str, reintento: bool = False, modalidad_por_codigo: bool = False) -> str:
    return lc.make_namespace(nombre_namespace(rep, reintento), code_ver=code_ver(prompt_sha256, modalidad_por_codigo),
                             thinking=THINKING)


def db_path_rep(cache_dir: Path, db_prefix: str, rep: int) -> Path:
    return Path(cache_dir) / f"{db_prefix}_r{rep}.db"


def construir_cliente(lc, real_client, rep: int, *, db_path: Path, prompt_sha256: str, run_label: str,
                      reintento: bool = False, modalidad_por_codigo: bool = False):
    return lc.CachingClient(real_client, domain="juez_tripletas", db_path=db_path,
                            namespace=namespace_rep(lc, rep, prompt_sha256, reintento, modalidad_por_codigo),
                            thinking_enabled=THINKING, run_label=run_label)


def cliente_anthropic_real():
    """El SDK real, con su reintento nativo. La clave la toma del entorno (ANTHROPIC_API_KEY): este código no lee
    ningún .env ni tiene la clave escrita."""
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


def costo_usd(usage: dict, pr: Precios) -> float:
    return (usage.get("input_tokens", 0) * pr.entrada + usage.get("output_tokens", 0) * pr.salida
            + usage.get("cache_write_tokens", 0) * pr.escritura_cache
            + usage.get("cache_read_tokens", 0) * pr.lectura_cache) / 1e6


def tokens_por_caracteres(texto: str) -> int:
    return math.ceil(len(texto) / CARACTERES_POR_TOKEN)


def cota_llamada_por_caracteres(kwargs: dict, pr: Precios) -> float:
    """Cota de una llamada sin haberla hecho: el system a la tarifa mayor entre escritura y entrada, el mensaje a la
    de entrada y la salida entera (max_tokens), con el margen COTA_FACTOR sobre los tokens por caracteres."""
    sistema, mensaje = texto_del_pedido(kwargs)
    t_sis, t_msj = tokens_por_caracteres(sistema), tokens_por_caracteres(mensaje)
    return (COTA_FACTOR * (t_sis * max(pr.escritura_cache, pr.entrada) + t_msj * pr.entrada)
            + kwargs["max_tokens"] * pr.salida) / 1e6


def costos_por_prompt(db_paths: list, pr: Precios) -> dict[str, float]:
    """El gasto por prompt: cada fila pagada lleva su namespace, y el namespace lleva el sha256 del prompt (code_ver).
    En la calibración cada caso tiene su prompt, así que es el costo de cada caso (con sus reintentos)."""
    out: dict[str, float] = {}
    for p in db_paths:
        if not Path(p).exists():
            continue
        conn = sqlite3.connect(str(p))
        for ns, i, o, cr, cw in conn.execute("SELECT namespace, input_tokens, output_tokens, cache_read_tokens, "
                                             "cache_write_tokens FROM cache"):
            m = re.search(r"\+prompt=([0-9a-f]{12})", ns)
            k = m.group(1) if m else "?"
            out[k] = out.get(k, 0.0) + costo_usd({"input_tokens": i, "output_tokens": o, "cache_read_tokens": cr,
                                                  "cache_write_tokens": cw}, pr)
        conn.close()
    return out


def filas_pagadas(db_paths: list) -> list[dict]:
    """Una fila por llamada pagada (cada miss guarda su crudo en la tabla cache), con sus cuatro campos de tokens."""
    out = []
    for p in db_paths:
        if not Path(p).exists():
            continue
        conn = sqlite3.connect(str(p))
        for r in conn.execute("SELECT input_tokens, output_tokens, cache_read_tokens, cache_write_tokens FROM cache"):
            out.append({"input_tokens": r[0], "output_tokens": r[1], "cache_read_tokens": r[2],
                        "cache_write_tokens": r[3]})
        conn.close()
    return out


class GuardaGasto:
    """El gasto real sale de las bases de la corrida (tokens por fila × precios), no de contadores en memoria. Antes
    de cada llamada:
      - tope: si gasto + cota de la llamada > tope, corta (la cota es la mayor entre la de caracteres y la llamada más
        cara observada);
      - freno por llamada (el gold): con 3 llamadas pagadas o más, si gasto + restantes × mediana del costo por llamada
        > freno, corta (la mediana no se deja llevar por la escritura única del prompt en la caché);
      - freno por caso (la calibración, `casos`): después de dos casos completos, si gasto + casos que faltan × mediana
        del costo de un caso (sus tres llamadas, con sus reintentos) > freno, corta."""

    def __init__(self, precios: Precios, tope: float, freno: float, db_paths: list):
        if not (0 < freno <= tope):
            raise SystemExit("FRENO: hace falta 0 < freno <= tope")
        self.pr, self.tope, self.freno, self.db_paths = precios, tope, freno, list(db_paths)

    def estado(self) -> dict:
        filas = filas_pagadas(self.db_paths)
        costos = [costo_usd(f, self.pr) for f in filas]
        return {"pagadas": len(filas), "gasto_usd": sum(costos),
                "mediana_usd": statistics.median(costos) if costos else 0.0,
                "max_usd": max(costos) if costos else 0.0,
                "tokens": {k: sum(f[k] for f in filas) for k in ("input_tokens", "output_tokens",
                                                                  "cache_read_tokens", "cache_write_tokens")}}

    def permitir(self, kwargs: dict, restantes: int, casos: dict | None = None) -> tuple[bool, dict]:
        """casos (solo en la calibración): {"completos": [sha256 de 12 del prompt de cada caso completo],
        "faltan": casos que faltan, el actual incluido}."""
        e = self.estado()
        cota = max(cota_llamada_por_caracteres(kwargs, self.pr), e["max_usd"])
        if e["gasto_usd"] + cota > self.tope:
            return False, {"motivo": "tope", "gasto_usd": round(e["gasto_usd"], 4), "cota_llamada_usd": round(cota, 4),
                           "tope_usd": self.tope, "pagadas": e["pagadas"]}
        if casos is not None:
            if len(casos["completos"]) >= 2:
                cp = costos_por_prompt(self.db_paths, self.pr)
                med = statistics.median(cp.get(c, 0.0) for c in casos["completos"])
                proy = e["gasto_usd"] + casos["faltan"] * med
                if proy > self.freno:
                    return False, {"motivo": "freno", "por": "caso", "gasto_usd": round(e["gasto_usd"], 4),
                                   "proyeccion_usd": round(proy, 4), "mediana_por_caso_usd": round(med, 4),
                                   "freno_usd": self.freno, "casos_completos": len(casos["completos"]),
                                   "casos_que_faltan": casos["faltan"]}
            return True, {}
        if e["pagadas"] >= 3:
            proy = e["gasto_usd"] + restantes * e["mediana_usd"]
            if proy > self.freno:
                return False, {"motivo": "freno", "gasto_usd": round(e["gasto_usd"], 4),
                               "proyeccion_usd": round(proy, 4), "freno_usd": self.freno,
                               "pagadas": e["pagadas"], "restantes": restantes}
        return True, {}
