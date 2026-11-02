"""
r1_referencias.py — B1.3: referencias cruzadas norma→norma, detector
DETERMINÍSTICO (regex) sobre label + properties de texto de cada nodo de
contenido, con resolución contra (a) el inventario de TOs del subset y (b)
las unidades estructurales de E0 (chunks_<to>.json ∪ estructura_<to>.json,
salida_enm01). Nada se inventa: remisión sin destino resoluble = registro
en `irresolubles`, no arista.

Patrones (castellano normativo BCRA):
  MENCIÓN DE NORMA: «normas sobre "Z"», «TO sobre Z», «Texto Ordenado de/sobre Z»,
     «de dicho ordenamiento» (no resuelve sola: exige punto previo) — Z se
     resuelve contra el inventario por palabras clave normalizadas:
        capitales mínimos → cap · clasificación de deudores → cla ·
        exterior y cambios → ext · protección de (los) usuarios → pro ·
        régimen informativo contable mensual → ric.
     Z fuera del inventario (garantías, previsiones mínimas, …) = irresoluble
     (fuera del subset), registrado con la norma nombrada.
  PUNTOS: «punto(s) N.N[.N]*», listas «, y» y rangos «a» (expansión solo
     cuando comparten prefijo y difieren en el último componente numérico).
  SECCIÓN: «Sección N» → unidad "S<N>" de E0.
  Alcance de la mención: los puntos/secciones que aparecen en los 120
     caracteres ANTERIORES a «… de las normas sobre Z» se atribuyen a esa
     norma; los puntos sin norma en su ventana posterior (90 chars) remiten
     al MISMO TO (remisión interna).
Destino de la arista `referencia` (source = nodo origen):
  - punto/sección resoluble en E0 y con nodos de contenido anclados
    (provenance.punto == destino, cualquier rol) → una arista por nodo
    destino (fan-out declarado), excluyendo el nodo origen;
  - punto existente en E0 sin nodos anclados → irresoluble
    `punto_sin_nodos` (frontera ancla/chunk: hallazgo_frontera_ancla_chunk.md);
  - solo la norma (sin punto) → arista al TextoOrdenado canónico del TO;
  - el punto propio del nodo origen nunca es destino (autorreferencia).
Provenance de la arista = la del nodo origen; `properties.evidencia` =
fragmento exacto; rol_fuente = referencia_cruzada. `referencia` nodo→nodo
NO está en schema.DOMAIN_RANGE (solo TextoOrdenado→Comunicacion); se
declara, no se edita el esquema.
"""

from __future__ import annotations

import json
import random
import re

import r1_comun as C

SEMILLA_MUESTRA = 20260823
TAM_MUESTRA = 30
VENTANA_ANTES = 120
VENTANA_DESPUES = 90
TIPOS_ORIGEN = ("Obligacion", "Restriccion", "Excepcion", "Operacion")
PROPS_TEXTO = ("descripcion", "condicion", "alcance", "umbral", "plazo", "detalle")

INVENTARIO_TOS = {
    "cap": ("capitales minimos",),
    "cla": ("clasificacion de deudores",),
    "ext": ("exterior y cambios",),
    "pro": ("proteccion de los usuarios de servicios financieros",
            "proteccion de usuarios de servicios financieros"),
    "ric": ("regimen informativo contable mensual",),
}

RE_NORMA = re.compile(
    r"(?:[Nn]ormas?\s+sobre|\bT\.?O\.?\s+(?:sobre|de)|[Tt]exto\s+[Oo]rdenado\s+(?:sobre|de))\s*"
    r"[\"“'«]?\s*([^\"”'»\.;\)]{3,90})")
RE_DICHO = re.compile(r"de\s+(?:dicho|ese|este)\s+(?:ordenamiento|texto\s+ordenado)", re.I)
RE_PUNTOS = re.compile(r"\bpuntos?\s+((?:\d+(?:\.\d+)+\.?)(?:\s*(?:,|y|al|a|e|ó|o|hasta)\s*\d+(?:\.\d+)+\.?)*)", re.I)
RE_NUM = re.compile(r"\d+(?:\.\d+)+")
RE_SECCION = re.compile(r"\bSecci(?:o|ó)n(?:es)?\s+(\d+)(?:\s*(?:,|y)\s*(\d+))?", re.I)
RE_PUNTOS_SUELTOS = re.compile(r"\bpuntos?\s+\d+(?:\.\d+)+", re.I)


def _texto(n: dict) -> str:
    partes = [n.get("label") or ""]
    for k in PROPS_TEXTO:
        v = (n.get("properties") or {}).get(k)
        if isinstance(v, str) and v:
            partes.append(v)
    return " | ".join(partes)


def resolver_norma(z: str) -> str | None:
    zn = C.norm(z)
    for to, claves in INVENTARIO_TOS.items():
        if any(k in zn for k in claves):
            return to
    return None


def _expandir_puntos(expr: str) -> list[str]:
    nums = [m.group(0).rstrip(".") for m in RE_NUM.finditer(expr)]
    if not nums:
        return []
    out: list[str] = []
    tokens = re.split(r"(\s*(?:,|\by\b|\bal\b|\ba\b|\bhasta\b|\be\b|\bó\b|\bo\b)\s*)", expr)
    # reconstruye: si el separador entre dos números es " a " → rango
    seq: list[tuple[str, str]] = []   # (sep_previo, num)
    sep = ""
    for t in tokens:
        m = RE_NUM.search(t)
        if m:
            seq.append((sep.strip().lower(), m.group(0).rstrip(".")))
            sep = ""
        else:
            sep = t
    for i, (s, num) in enumerate(seq):
        if s in ("a", "al", "hasta") and i > 0:
            a, b = seq[i - 1][1].split("."), num.split(".")
            if len(a) == len(b) and a[:-1] == b[:-1] and b[-1].isdigit() and a[-1].isdigit() \
                    and int(b[-1]) > int(a[-1]) and int(b[-1]) - int(a[-1]) <= 30:
                for k in range(int(a[-1]) + 1, int(b[-1]) + 1):
                    out.append(".".join(a[:-1] + [str(k)]))
                continue
        if num not in out:
            out.append(num)
    return out


def unidades_e0(to: str) -> set[str]:
    u: set[str] = set()
    for c in C.cargar_chunks_enm01(to):
        u.add(c["unidad"])
        for h in c.get("herencia", []):
            u.add(h["unidad_origen"])
    est = C.cargar_estructura_enm01(to)

    def rec(nodo: dict) -> None:
        if nodo.get("tipo") == "seccion":
            u.add(f"S{nodo['numero']}")
        elif nodo.get("numero"):
            u.add(str(nodo["numero"]))
        for h in nodo.get("hijos", []):
            rec(h)
    for s in est.get("secciones", []):
        rec(s)
    return u


def detectar_menciones(texto: str, to_origen: str) -> list[dict]:
    """Devuelve menciones {to_destino|norma, puntos, secciones, evidencia,
    clase}. Determinístico: recorre el texto en orden."""
    menciones: list[dict] = []
    consumidos: list[tuple[int, int]] = []
    for m in RE_NORMA.finditer(texto):
        z = m.group(1).strip()
        to_dest = resolver_norma(z)
        ini = max(0, m.start() - VENTANA_ANTES)
        ventana = texto[ini:m.start()]
        puntos, secciones = [], []
        spans: list[tuple[int, int]] = []
        for pm in RE_PUNTOS.finditer(ventana):
            puntos += _expandir_puntos(pm.group(1))
            spans.append((ini + pm.start(), ini + pm.end()))
        for sm in RE_SECCION.finditer(ventana):
            secciones += [x for x in sm.groups() if x]
            spans.append((ini + sm.start(), ini + sm.end()))
        consumidos += spans
        ev_ini = min([s[0] for s in spans] + [m.start()])
        menciones.append({"clase": "externa", "norma_nombrada": z, "to_destino": to_dest,
                          "puntos": puntos, "secciones": secciones,
                          "evidencia": texto[ev_ini:m.end()].strip()})
    # "de dicho ordenamiento": puntos previos que apuntan a la última norma citada
    for m in RE_DICHO.finditer(texto):
        prev = [x for x in menciones if x["clase"] == "externa" and x["to_destino"]]
        ini = max(0, m.start() - VENTANA_ANTES)
        ventana = texto[ini:m.start()]
        puntos = []
        for pm in RE_PUNTOS.finditer(ventana):
            puntos += _expandir_puntos(pm.group(1))
            consumidos.append((ini + pm.start(), ini + pm.end()))
        menciones.append({"clase": "externa_anaforica", "norma_nombrada": "dicho ordenamiento",
                          "to_destino": prev[-1]["to_destino"] if prev else None,
                          "puntos": puntos, "secciones": [],
                          "evidencia": texto[ini:m.end()].strip()[-160:]})

    def consumido(a: int, b: int) -> bool:
        return any(a >= x and b <= y for x, y in consumidos)

    for pm in RE_PUNTOS.finditer(texto):
        if consumido(pm.start(), pm.end()):
            continue
        despues = texto[pm.end():pm.end() + VENTANA_DESPUES]
        if RE_NORMA.search(despues) or RE_DICHO.search(despues):
            continue   # la ventana anterior de esa norma ya lo captura (o lo capturará)
        menciones.append({"clase": "interna", "norma_nombrada": None, "to_destino": to_origen,
                          "puntos": _expandir_puntos(pm.group(1)), "secciones": [],
                          "evidencia": texto[max(0, pm.start() - 60):pm.end() + 20].strip()})
    for sm in RE_SECCION.finditer(texto):
        if consumido(sm.start(), sm.end()):
            continue
        despues = texto[sm.end():sm.end() + VENTANA_DESPUES]
        if RE_NORMA.search(despues) or RE_DICHO.search(despues):
            continue
        menciones.append({"clase": "interna", "norma_nombrada": None, "to_destino": to_origen,
                          "puntos": [], "secciones": [x for x in sm.groups() if x],
                          "evidencia": texto[max(0, sm.start() - 60):sm.end() + 20].strip()})
    return menciones


def detectar_y_resolver(kg: dict, perfil: str | None = None, **opciones_r2) -> dict:
    """Remisiones del ensamblado. Sin perfil (o con los perfiles existentes),
    la arista `referencia` con `rol_fuente = referencia_cruzada`, byte a byte
    como en los ensamblados sellados. Con el perfil r2, `remite_a`
    (`detectar_y_resolver_r2`; enmienda 2 de L-ESQ-R2, FIRMADA en 5f9a731)."""
    if perfil == PERFIL_R2:
        return detectar_y_resolver_r2(kg, **opciones_r2)
    if opciones_r2:
        raise TypeError(f"opciones del perfil r2 sin el perfil r2: {sorted(opciones_r2)}")
    nodes_by_id = {n["id"]: n for n in kg["nodes"]}
    unidades = {to: unidades_e0(to) for to in C.TOS_ORDEN}
    # índice (to, punto) → ids de nodos de contenido anclados
    anclados: dict[tuple[str, str], list[str]] = {}
    to_canon: dict[str, str] = {}
    for n in kg["nodes"]:
        if n["type"] == "TextoOrdenado":
            tos = {p["to"] for p in n["provenances"] if p.get("to")}
            for t in tos:
                to_canon[t] = n["id"]
            continue
        if n["type"] in ("Sujeto", "Comunicacion"):
            continue
        for p in n.get("provenances", []):
            if p.get("to") and p.get("punto"):
                anclados.setdefault((p["to"], p["punto"]), []).append(n["id"])
    for k in anclados:
        anclados[k] = sorted(set(anclados[k]))

    triplas = {(e["source"], e["relation"], e["target"]) for e in kg["edges"]}
    remisiones: list[dict] = []
    irresolubles: list[dict] = []
    nuevas: list[dict] = []
    por_to = {to: {"nodos_con_remision": 0, "menciones": 0, "resueltas": 0,
                   "irresolubles": 0, "aristas": 0} for to in C.TOS_ORDEN}

    def agregar(src: dict, tgt_id: str, men: dict, destino: str, via: str) -> None:
        k = (src["id"], "referencia", tgt_id)
        if k in triplas or tgt_id == src["id"]:
            return
        e = {"source": src["id"], "target": tgt_id, "relation": "referencia",
             "provenance": dict(src["provenance"]),
             "provenances": [dict(p) for p in src["provenances"]],
             "rol_fuente": "referencia_cruzada",
             "properties": {"evidencia": men["evidencia"], "clase": men["clase"],
                            "destino": destino, "via": via}}
        kg["edges"].append(e)
        nuevas.append(e)
        triplas.add(k)
        por_to[src["provenance"]["to"]]["aristas"] += 1

    for n in sorted(kg["nodes"], key=lambda x: x["id"]):
        if n["type"] not in TIPOS_ORIGEN:
            continue
        to_o = n["provenance"].get("to")
        if to_o not in C.TOS_ORDEN:
            continue
        texto = _texto(n)
        menciones = detectar_menciones(texto, to_o)
        if not menciones:
            continue
        por_to[to_o]["nodos_con_remision"] += 1
        propios = {p["punto"] for p in n["provenances"]}
        for men in menciones:
            por_to[to_o]["menciones"] += 1
            reg = {"nodo": n["id"], "to_origen": to_o, "punto_origen": n["provenance"]["punto"],
                   **{k: v for k, v in men.items()}}
            remisiones.append(reg)
            if men["to_destino"] is None:
                reg["estado"] = "irresoluble"
                reg["motivo"] = ("norma fuera del inventario del subset" if men["clase"] == "externa"
                                 else "anáfora sin norma previa resoluble")
                irresolubles.append(reg)
                por_to[to_o]["irresolubles"] += 1
                continue
            td = men["to_destino"]
            destinos = [(p, "punto") for p in men["puntos"]] + [(f"S{s}", "seccion") for s in men["secciones"]]
            if not destinos:
                if men["clase"] == "interna":
                    reg["estado"] = "irresoluble"; reg["motivo"] = "mención interna sin punto"
                    irresolubles.append(reg); por_to[to_o]["irresolubles"] += 1
                    continue
                agregar(n, to_canon[td], men, f"{td}::TO", "texto_ordenado")
                reg["estado"] = "resuelta"; reg["destinos"] = [f"{td}::TO"]
                por_to[to_o]["resueltas"] += 1
                continue
            res, irr = [], []
            for d, clase in destinos:
                if td == to_o and d in propios:
                    irr.append({"destino": d, "motivo": "autorreferencia al punto propio"})
                    continue
                if d not in unidades[td]:
                    irr.append({"destino": d, "motivo": f"{clase} inexistente en E0 de {td}"})
                    continue
                ids = [i for i in anclados.get((td, d), []) if i != n["id"]]
                if not ids:
                    irr.append({"destino": d, "motivo": "punto_sin_nodos (existe en E0; contenido "
                                                        "solo en descendientes/contenedor — frontera ancla/chunk)"})
                    continue
                for i in ids:
                    agregar(n, i, men, f"{td}::{d}", "nodos_del_punto")
                res.append({"destino": f"{td}::{d}", "n_nodos": len(ids)})
            reg["destinos"] = res
            reg["irresolubles_parciales"] = irr
            if res:
                reg["estado"] = "resuelta" if not irr else "parcial"
                por_to[to_o]["resueltas"] += 1
            else:
                reg["estado"] = "irresoluble"
                reg["motivo"] = "; ".join(sorted({x["motivo"] for x in irr}))
                irresolubles.append(reg)
                por_to[to_o]["irresolubles"] += 1

    rng = random.Random(SEMILLA_MUESTRA)
    muestra_idx = sorted(rng.sample(range(len(nuevas)), min(TAM_MUESTRA, len(nuevas))))
    muestra = []
    for k, i in enumerate(muestra_idx, 1):
        e = nuevas[i]
        s, t = nodes_by_id[e["source"]], nodes_by_id[e["target"]]
        muestra.append({
            "n": k, "indice_en_nuevas": i,
            "source": e["source"], "source_label": s["label"],
            "source_ancla": f"{s['provenance']['to']}::{s['provenance']['punto']}",
            "target": e["target"], "target_type": t["type"], "target_label": t["label"],
            "target_ancla": f"{t['provenance'].get('to')}::{t['provenance'].get('punto')}",
            "target_anclas_todas": sorted({f"{p.get('to')}::{p.get('punto')}" for p in t["provenances"]}),
            "destino": e["properties"]["destino"], "clase": e["properties"]["clase"],
            "evidencia_verbatim": e["properties"]["evidencia"],
            "texto_origen_completo": _texto(s),
        })
    fanout = C.conteo([{"d": e["properties"]["destino"]} for e in nuevas], "d")
    resumen = {
        "semilla_muestra": SEMILLA_MUESTRA,
        "nodos_con_remision": sum(v["nodos_con_remision"] for v in por_to.values()),
        "menciones": len(remisiones),
        "resueltas": sum(1 for r in remisiones if r["estado"] in ("resuelta", "parcial")),
        "parciales": sum(1 for r in remisiones if r["estado"] == "parcial"),
        "irresolubles": len(irresolubles),
        "aristas_referencia_nuevas": len(nuevas),
        "aristas_a_texto_ordenado": sum(1 for e in nuevas if e["properties"]["via"] == "texto_ordenado"),
        "aristas_cross_to": sum(1 for e in nuevas if e["properties"]["destino"].split("::")[0]
                                != e["provenance"]["to"]),
        "por_to": por_to,
        "por_clase": C.conteo([{"c": r["clase"]} for r in remisiones], "c"),
        "irresolubles_por_motivo": C.conteo([{"m": r.get("motivo", "")} for r in irresolubles], "m"),
        "normas_fuera_inventario": C.conteo(
            [{"z": C.norm(r["norma_nombrada"])} for r in irresolubles
             if r["clase"] == "externa" and r["to_destino"] is None], "z"),
        "fanout_max_destino": max(fanout.values()) if fanout else 0,
        "declaracion_esquema": "referencia nodo→nodo no está en schema.DOMAIN_RANGE "
                               "(solo TextoOrdenado→Comunicacion); aristas con rol_fuente="
                               "referencia_cruzada; no se edita schema.py.",
    }
    return {"resumen": resumen, "remisiones": remisiones, "irresolubles": irresolubles,
            "muestra": muestra, "nuevas": nuevas}


# ----------------------------------------------------------------------- #
# Perfil r2: `remite_a` (enmienda 2 de L-ESQ-R2, FIRMADA en 5f9a731;       #
# enmienda 1 al mandato de U-R2-CODIGO, R3.d; decisión 11 del mandato)    #
# ----------------------------------------------------------------------- #
PERFIL_R2 = "r2"
PREDICADO_R2 = "remite_a"
# §2: los siete tipos de contenido son origen y destino (H1: se suman
# Condicion, Potestad y Definicion a TIPOS_ORIGEN).
TIPOS_CONTENIDO_R2 = ("Operacion", "Restriccion", "Excepcion", "Obligacion", "Potestad",
                      "Condicion", "Definicion")
# H4: el resolvedor lee también `termino` (texto de los nodos para la
# atribución D1 y para la variante sobre la paráfrasis de los controles).
PROPS_TEXTO_R2 = PROPS_TEXTO + ("termino",)
ALCANCES_R2 = ("to_entero", "interna", "externa")
# Rótulo de unidad al comienzo de línea («6.1. …», «6.10.Declaración…»,
# «Sección 8. …»): insumo del criterio de texto de cuerpo de las variantes.
RE_ROTULO_UNIDAD = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.\s*\S|Secci(?:o|ó)n\s+\d+\b)")
# Cita a una Comunicación (decisión 7 de la enmienda 2): «Comunicación “A” 6847»,
# «Comunicaciones "A" 1234 y 5678», «Com. A 6847». Cada número es una cita.
RE_COMUNICACION = re.compile(
    r"\bCom(?:unicaci(?:o|ó)n(?:es)?|\.)\s*[\"“”'«»]?\s*((?-i:[ABC]))\s*[\"“”'«»]?\s*"
    r"(N[°º]\s*)?(\d{1,2}\.?\d{3}|\d{1,4})((?:\s*(?:,|y|e)\s*\d{1,2}\.?\d{3}|\s*(?:,|y|e)\s*\d{1,4})*)",
    re.I)
RE_NUM_COM = re.compile(r"\d{1,2}\.?\d{3}|\d{1,4}")
# Pie de página que E0 no recortó (caso conocido: ctacte::6.1.2.3): la línea
# de la cita tiene la forma del pie del BCRA.
RE_PIE_NO_RECORTADO = re.compile(r"Versi(?:o|ó)n:|Vigencia:|P(?:a|á)gina\s+\d+", re.I)


def _lineas_sueltas(texto: str) -> list[tuple[int, int]]:
    """Regla (a): rangos [inicio, fin) de las líneas de uno o dos caracteres
    alfanuméricos que quedan entre una línea que termina en «punto(s)» o
    «apartado(s)» y una que empieza con un número. Es el subíndice que E0
    extrae como línea suelta (límite de E0, declarado y sin corregir)."""
    lineas, pos = [], 0
    for l in texto.split("\n"):
        lineas.append((pos, l))
        pos += len(l) + 1
    out = []
    for k in range(1, len(lineas) - 1):
        ini, l = lineas[k]
        if (RE_LINEA_SUELTA.match(l.strip()) and RE_ANTES_DE_LINEA_SUELTA.search(lineas[k - 1][1])
                and lineas[k + 1][1].lstrip()[:1].isdigit()):
            out.append((ini, ini + len(l) + 1))
    return out


def normalizar_e0(texto: str, tolerar_linea_suelta: bool = False) -> tuple[str, list[int]]:
    """Texto de E0 para la detección: el corte de palabra al final de línea
    («nor-\nmas») se une y todo otro salto de línea pasa a espacio. Devuelve
    el texto normalizado y, por cada carácter, su posición en el original,
    para que la evidencia sea un tramo literal del texto de E0. Con
    `tolerar_linea_suelta` (regla a del perfil r2), las líneas sueltas de
    `_lineas_sueltas` no pasan al texto normalizado (la evidencia, que se toma
    del original, las conserva)."""
    saltar = _lineas_sueltas(texto) if tolerar_linea_suelta else []
    out, mapa = [], []
    i, n = 0, len(texto)
    while i < n:
        fuera = next((b for a, b in saltar if a <= i < b), None)
        if fuera is not None:
            i = fuera
            continue
        c = texto[i]
        if (c == "-" and i + 1 < n and texto[i + 1] == "\n" and i > 0 and texto[i - 1].isalpha()
                and i + 2 < n and texto[i + 2].isalpha()):
            i += 2
            continue
        out.append(" " if c == "\n" else c)
        mapa.append(i)
        i += 1
    return "".join(out), mapa


def _dentro_de_palabra(t: str, i: int) -> bool:
    """Las posiciones i-1 e i son de la misma palabra: dos alfanuméricos, un
    punto o una coma entre dígitos («3.7.1», «1,5») o un corte de palabra al
    final de línea («nor-\nmas»)."""
    if i <= 0 or i >= len(t):
        return False
    a, b = t[i - 1], t[i]
    if a.isalnum() and b.isalnum():
        return True
    if b in ".," and a.isdigit() and i + 1 < len(t) and t[i + 1].isdigit():
        return True
    if a in ".," and b.isdigit() and i >= 2 and t[i - 2].isdigit():
        return True
    if b == "-" and i + 2 < len(t) and t[i + 1] == "\n" and a.isalpha() and t[i + 2].isalpha():
        return True
    if t[i - 1:i + 1] == "-\n" and i >= 2 and t[i - 2].isalpha() and i + 1 < len(t) and t[i + 1].isalpha():
        return True
    if a == "\n" and i >= 2 and t[i - 2] == "-" and i >= 3 and t[i - 3].isalpha() and b.isalpha():
        return True
    return False


def evidencia_literal(original: str, norm: str, mapa: list[int], evidencia: str) -> str:
    """Tramo del texto original que corresponde a `evidencia` (una subcadena
    del texto normalizado), extendido hacia afuera hasta el límite de palabra
    en los dos extremos (decisión 4 sobre el FRENO R3): sigue siendo literal
    del texto de E0 y no empieza ni termina en la mitad de una palabra."""
    i = norm.find(evidencia)
    if i == -1 or not evidencia:
        return evidencia
    a, b = mapa[i], mapa[i + len(evidencia) - 1] + 1
    while _dentro_de_palabra(original, a):
        a -= 1
    while _dentro_de_palabra(original, b):
        b += 1
    return original[a:b]


# ----------------------------------------------------------------------- #
# Detector del perfil r2 (decisiones de la autora sobre el freno posterior #
# a R3): reglas (a) a (i), cada una conmutable para medir su efecto, más   #
# la (j) de U-R2-CODIGO-2 (C2, punto a). Sin reglas,                       #
# `detectar_menciones_r2` da exactamente `detectar_menciones`.             #
# ----------------------------------------------------------------------- #
REGLAS_R2 = frozenset("abcdefghij")
RE_LINEA_SUELTA = re.compile(r"^[A-Za-z0-9]{1,2}$")
RE_ANTES_DE_LINEA_SUELTA = re.compile(r"\b(?:puntos?|apartados?)\s*$", re.I)
# (e) anáfora de la norma: las formas de RE_DICHO («de dicho ordenamiento»…),
# «de las citadas normas», «de las citadas disposiciones», «de dichas normas»,
# «del citado ordenamiento», «del citado TO», «dicho TO», «de la citada
# norma» y variantes («de las normas citadas», «de las mencionadas normas»…).
# «de este ordenamiento» y «de este texto ordenado» no son anáfora: nombran el
# propio TO (RE_PROPIO_TO).
RE_ANAFORA_NORMA = re.compile(
    r"de\s+(?:dicho|ese)\s+(?:ordenamiento|texto\s+ordenado)"
    r"|de\s+(?:las|los)\s+(?:citad|mencionad|referid|precitad|aludid)[ao]s\s+(?:normas|disposiciones|ordenamientos)"
    r"|de\s+(?:las|los)\s+(?:normas|disposiciones|ordenamientos)\s+(?:citad|mencionad|referid|precitad|aludid)[ao]s"
    r"|de\s+dich[ao]s\s+(?:normas|disposiciones|ordenamientos)"
    r"|del\s+citado\s+(?:ordenamiento|texto\s+ordenado|T\.?\s?O\b\.?)"
    r"|de\s+la\s+citada\s+(?:norma|disposici[oó]n)\b"
    r"|\bdicho\s+T\.?\s?O\b\.?", re.I)
# (e) el propio TO: una mención de puntos o de sección seguida de una de estas
# formas es interna aunque después se nombre otra norma («de las presentes
# normas», «de las presentes disposiciones», «del presente régimen», «de estas
# normas», «de estas disposiciones», «de esta norma», «de este régimen», «de
# este ordenamiento», «del presente ordenamiento», «de este texto ordenado»,
# «del presente texto ordenado»).
RE_PROPIO_TO = re.compile(
    r"\.?\s*(?:de\s+las\s+presentes\s+(?:normas|disposiciones)|del\s+presente\s+r[eé]gimen"
    r"|de\s+estas\s+(?:normas|disposiciones)|de\s+esta\s+norma\b|de\s+este\s+r[eé]gimen"
    r"|de\s+este\s+(?:ordenamiento|texto\s+ordenado)|del\s+presente\s+(?:ordenamiento|texto\s+ordenado))", re.I)
# Fin de la comilla de un nombre de norma citado entre comillas (regla g).
RE_CIERRE_COMILLA = re.compile(r"[\"”»’']")
LARGO_CAPTURA_G = 400
# (h) «este punto» sin número: no genera remisión; se cuenta en el registro.
RE_ESTE_PUNTO = re.compile(r"\b(?:este|el\s+presente|dicho)\s+punto\b(?!\s*\d)", re.I)
# (j) U-R2-CODIGO-2, C2, punto a: una mención de puntos que el detector leería
# como interna y a la que sigue el nombre de otra norma.
#  - Patrón 1: título intermedio opcional entre comillas; «de»/«del» y artículo
#    opcional; y «normas/disposiciones/reglamentación/texto ordenado/T.O.» con
#    «de/sobre» opcional y un nombre entre comillas, o un nombre entre comillas
#    solo, o «NIIF N», «NIC N», «Norma Internacional de Información Financiera
#    (NIIF) N» («del punto 5.5. de la NIIF 9», «de las normas de “Grandes
#    exposiciones…”», «de la “Reglamentación de la cuenta corriente
#    bancaria”»). Nunca es interna: es externa a la norma nombrada; el nombre
#    entre comillas se resuelve con la regla (g), y NIIF y NIC quedan «norma
#    fuera del inventario». Un nombre que empieza como división del documento
#    («Sección…», «Anexo…», «Capítulo…»; RE_NO_ES_NORMA) no es otra norma.
#  - Patrón 2: «del Anexo de la Comunicación A NNNN»: la mención queda
#    irresoluble con causa propia (CAUSA_ANEXO_COMUNICACION), sin arista, y la
#    cita va al registro de citas a Comunicaciones.
# Una cita sin norma nombrada a un punto que el TO no tiene sigue irresoluble
# (patrón 3; decisión 7 del mandato de U-R2-CODIGO-2: no se adivina la norma).
_ABRE_J, _CIERRA_J = "\"“«‘", "\"”»’"
RE_NORMA_TRAS_NUMERO = re.compile(
    r"\s*(?:[–—-]\s*)?"
    r"(?:(?P<titulo>[" + _ABRE_J + r"][^" + _CIERRA_J + r"]{1,120}[" + _CIERRA_J + r"])\s*,?\s*)?"
    r"(?:de|del)\s+(?:(?:la|las|los|el)\s+)?"
    r"(?:"
    r"(?:[Nn]ormas?|[Dd]isposiciones|[Rr]eglamentaci[oó]n|[Tt]exto\s+[Oo]rdenado|T\.?\s?O\.?)\s+"
    r"(?:(?:de|sobre)\s+(?:(?:la|las|los|el)\s+)?)?"
    r"(?P<q1>[" + _ABRE_J + r"])(?P<n1>[^" + _CIERRA_J + r"]{3,200})[" + _CIERRA_J + r"]"
    r"|(?P<q2>[" + _ABRE_J + r"])(?P<n2>[^" + _CIERRA_J + r"]{3,200})[" + _CIERRA_J + r"]"
    r"|(?P<n3>(?:NIIF|NIC)\s*\d+|Norma\s+Internacional\s+de\s+Informaci[oó]n\s+Financiera\s*(?:\(\s*NIIF\s*\)\s*)?\d+)"
    r")")
RE_ANEXO_COMUNICACION = re.compile(
    r"\s*(?:[–—-]\s*)?(?:del|de\s+la)\s+[Aa]nexo(?:\s+[IVX]+)?\s+(?:a\s+|de\s+)?la\s+Comunicaci[oó]n\s*"
    r"[\"“”'«»]?\s*(?P<letra>[ABC])\s*[\"“”'«»]?\s*(?:N[°º]\s*)?(?P<num>\d{1,2}\.?\d{3}|\d{1,4})")
RE_NO_ES_NORMA = re.compile(r"(?:Secci[oó]n|Anexo|Cap[ií]tulo|T[ií]tulo|Punto|Apartado)\b", re.I)
CAUSA_ANEXO_COMUNICACION = "punto del Anexo de una Comunicación"
# (i), contador de U-R2-CODIGO-2 (C2, punto d): la línea «Sección N.» de un
# encabezado heredado, leída como cita de la propia sección heredada, no es
# una cita (autocita de encabezado).
RE_SECCION_AUTOCITA = re.compile(r"^\s*Secci[oó]n\s+(\d+)\b", re.I)
# RE_NORMA con grupos con nombre (sin la regla g).
RE_NORMA_NOMBRADA = re.compile(
    r"(?:[Nn]ormas?\s+sobre|\bT\.?O\.?\s+(?:sobre|de)|[Tt]exto\s+[Oo]rdenado\s+(?:sobre|de))\s*"
    r"(?P<q>[\"“'«])?\s*(?P<z>[^\"”'»\.;\)]{3,90})")
# Con la regla (g): como RE_NORMA y, además, «texto ordenado de las normas
# sobre “X”» se lee como una sola cita a X (RE_NORMA toma «las normas sobre
# “X» como el nombre), y las comillas simples tipográficas (‘X’) cuentan como
# comillas. «del presente texto ordenado de: …» y «de este texto ordenado
# de …» nombran el propio TO (RE_PROPIO_TO), no otra norma (ri_niif::2.1:
# «la Sección 4. del presente texto ordenado de: - Estado de Situación…»).
RE_NORMA_R2 = re.compile(
    r"(?:[Nn]ormas?\s+sobre|(?<![Pp]resente\s)(?<!\b[Ee]ste\s)(?:\bT\.?O\.?|[Tt]exto\s+[Oo]rdenado)\s+(?:sobre|de)"
    r"(?:\s+las\s+[Nn]ormas\s+sobre)?)\s*"
    r"(?P<q>[\"“'«‘])?\s*(?P<z>[^\"”'»’\.;\)]{3,90})")
# (g) nombres de cada TO del ensamblado, normalizados: el título del inventario
# y los `nombres_remision` del manifiesto (los fija el ensamblado o el control;
# `titulos_de_inventario`). Se admite también un solo título por TO (str).
TITULOS_TOS: dict[str, tuple[str, ...] | str] | None = None
INVENTARIO_TITULOS = C.REPO / "data" / "experiment" / "escalado_prep" / "inventario_tos.csv"
INVENTARIO_RESUMEN = C.REPO / "data" / "experiment" / "escalado_prep" / "inventario_resumen.json"
_RE_PUNTOS_CACHE: dict[frozenset, re.Pattern] = {}


def titulos_de_inventario(tos: list[str], nombres_remision: dict[str, list[str]] | None = None
                          ) -> dict[str, tuple[str, ...]]:
    """Nombres normalizados de cada TO: el título oficial del índice del sitio
    del BCRA del inventario de la partición (`inventario_tos.csv`,
    `titulo_oficial`; para los cinco TOs de desarrollo que la partición
    excluye, `inventario_resumen.json`, `subset_excluido`) más, si se pasan,
    los `nombres_remision` del manifiesto. Frena si falta algún título."""
    import csv  # noqa: PLC0415
    tit = {r["id"]: r["titulo_oficial"] for r in csv.DictReader(INVENTARIO_TITULOS.open(encoding="utf-8"))}
    for x in json.loads(INVENTARIO_RESUMEN.read_text(encoding="utf-8"))["subset_excluido"]:
        tit[x["id_interno"]] = x["titulo"]
    faltan = [t for t in tos if t not in tit]
    if faltan:
        raise RuntimeError(f"TOs sin título en el inventario: {faltan}")
    out = {}
    for t in tos:
        ns = [C.norm(tit[t])] + [C.norm(x) for x in (nombres_remision or {}).get(t, [])]
        out[t] = tuple(dict.fromkeys(n for n in ns if n))
    return out


def _nombres(v) -> tuple[str, ...]:
    return (v,) if isinstance(v, str) else tuple(v)


def _limite(texto: str, n: str) -> bool:
    """`n` es prefijo de `texto` hasta un límite de palabra."""
    return texto.startswith(n) and (len(texto) == len(n) or not texto[len(n)].isalnum())


def resolver_norma_r2_via(z: str, entrecomillada: bool, reglas: frozenset = REGLAS_R2,
                          continuacion: str | None = None) -> tuple[str | None, str | None]:
    """Regla (g), en este orden, sobre los nombres de cada TO (título del
    inventario y `nombres_remision`, `TITULOS_TOS`), todo normalizado:
      1. «igualdad»: el nombre citado es igual a un nombre de un único TO;
      2. «prefijo»: un nombre de TO es prefijo del texto capturado, hasta un
         límite de palabra; si calzan varios, gana el más largo;
      3. «comienzo»: el nombre citado, de al menos dos palabras, es el
         comienzo de un nombre de un único TO, hasta un límite de palabra.
    El nombre citado es lo que está entre comillas o, sin comillas, lo que toma
    el patrón (`z`). El texto capturado (`continuacion`) sigue hasta la
    comilla de cierre o, sin comillas, `LARGO_CAPTURA_G` caracteres, sin
    cortarse en un punto («… técnicas. Criterios aplicables»). Un nombre que no
    está al comienzo no cuenta («Incumplimientos de capitales mínimos…» no es
    «Capitales mínimos…»). Devuelve (TO, vía) o (None, None). Sin la regla,
    `resolver_norma` (palabras clave contenidas en el nombre), vía None."""
    if "g" not in reglas:
        return resolver_norma(z), None
    if TITULOS_TOS is None:
        raise RuntimeError("regla (g) sin TITULOS_TOS: el ensamblado debe fijar los títulos del inventario")
    nombres = {to: _nombres(v) for to, v in TITULOS_TOS.items()}
    n = C.norm(z)
    largo = C.norm(continuacion) if continuacion else n
    iguales = {to for to, ns in nombres.items() if n and n in ns}
    if len(iguales) == 1:
        return iguales.pop(), "igualdad"
    calzan = sorted({(len(t), to) for to, ns in nombres.items() for t in ns if t and _limite(largo, t)}, reverse=True)
    if calzan and (len(calzan) == 1 or calzan[0][0] > calzan[1][0] or calzan[0][1] == calzan[1][1]):
        return calzan[0][1], "prefijo"
    if len(n.split()) >= 2:
        comienzo = {to for to, ns in nombres.items() for t in ns if _limite(t, n)}
        if len(comienzo) == 1:
            return comienzo.pop(), "comienzo"
    return None, None


def resolver_norma_r2(z: str, entrecomillada: bool, reglas: frozenset = REGLAS_R2,
                      continuacion: str | None = None) -> str | None:
    """`resolver_norma_r2_via` sin la vía."""
    return resolver_norma_r2_via(z, entrecomillada, reglas, continuacion)[0]


def _norma_de_match(texto: str, m: re.Match, reglas: frozenset) -> tuple[str, str | None, str | None]:
    """(nombre citado, TO, vía) de una mención de norma de RE_NORMA_R2 o
    RE_NORMA_NOMBRADA. Con la regla (g), el nombre entre comillas llega hasta
    la comilla de cierre y el texto capturado sigue más allá del patrón."""
    z = m.group("z").strip()
    if "g" not in reglas:
        return z, resolver_norma(z), None
    ini = m.start("z")
    if m.group("q") is not None:
        cierre = RE_CIERRE_COMILLA.search(texto, ini, ini + LARGO_CAPTURA_G)
        nombre = texto[ini:cierre.start()].strip() if cierre else z
        continuacion = nombre
    else:
        nombre, continuacion = z, texto[ini:ini + LARGO_CAPTURA_G]
    to, via = resolver_norma_r2_via(nombre, m.group("q") is not None, reglas, continuacion)
    return nombre, to, via


def _re_puntos_r2(reglas: frozenset) -> re.Pattern:
    """RE_PUNTOS con (f) «apartado» como forma de cita y (c) un paréntesis
    entre los elementos de una lista o de un rango."""
    clave = frozenset(reglas) & frozenset("cf")
    if clave not in _RE_PUNTOS_CACHE:
        palabra = r"(?:puntos?|apartados?)" if "f" in clave else r"puntos?"
        paren = r"(?:\([^()]{0,200}\)\s*)?" if "c" in clave else ""
        _RE_PUNTOS_CACHE[clave] = re.compile(
            r"\b" + palabra + r"\s+((?:\d+(?:\.\d+)+\.?)(?:\s*" + paren
            + r"(?:,|y|al|a|e|ó|o|hasta)\s*\d+(?:\.\d+)+\.?)*)", re.I)
    return _RE_PUNTOS_CACHE[clave]


def _expandir_puntos_r2(expr: str, reglas: frozenset) -> list[str]:
    if "c" in reglas:
        expr = re.sub(r"\([^()]*\)", " ", expr)
    return _expandir_puntos(expr)


def norma_tras_el_numero(texto: str, fin: int) -> dict | None:
    """Regla (j): el patrón 1 o 2 en el texto que sigue a una mención de
    puntos que termina en `fin`, o None."""
    m = RE_ANEXO_COMUNICACION.match(texto, fin)
    if m:
        return {"patron": "2", "norma_nombrada": f"Comunicación {m.group('letra')} {m.group('num').replace('.', '')}",
                "fin": m.end(), "entrecomillada": False}
    m = RE_NORMA_TRAS_NUMERO.match(texto, fin)
    if m:
        nombre = (m.group("n1") or m.group("n2") or m.group("n3")).strip()
        if m.group("n3") is None and RE_NO_ES_NORMA.match(nombre):
            return None
        return {"patron": "1", "norma_nombrada": " ".join(nombre.split()), "fin": m.end(),
                "entrecomillada": m.group("n3") is None}
    return None


def es_autocita_de_encabezado(men: dict, unidad_heredada: str) -> bool:
    """Contador de la regla (i) (U-R2-CODIGO-2, C2, punto d): la mención sin
    puntos cuya única sección es la propia sección heredada y cuya evidencia
    empieza con «Sección N» (la línea del encabezado)."""
    mt = RE_SECCION_AUTOCITA.match(men.get("evidencia") or "")
    return (mt is not None and not men["puntos"] and men["secciones"] == [mt.group(1)]
            and unidad_heredada == f"S{mt.group(1)}")


def detectar_menciones_r2(texto: str, to_origen: str, reglas: frozenset = REGLAS_R2,
                          normas_previas: list[str | None] | None = None) -> list[dict]:
    """Detector del perfil r2. Con `reglas` vacío, el mismo resultado que
    `detectar_menciones`. Reglas: (c) paréntesis en listas y rangos; (d) a una
    norma solo se le atribuye la mención de puntos más cercana de su ventana,
    y una mención seguida de otra mención de puntos no queda tomada por la
    norma que viene después; (e) anáfora de la norma resuelta a la última norma
    nombrada antes en el mismo texto, o irresoluble con causa «anáfora sin
    antecedente», y una mención de puntos o de sección seguida de una forma
    de RE_PROPIO_TO («de las presentes normas», «del presente régimen», «de
    este ordenamiento», «del presente texto ordenado»…) es interna; (f) «apartado»; (g) inventario por título; (h) «este punto» sin
    número, registrado sin remisión; (j) una mención de puntos seguida del
    nombre de otra norma no es interna (`norma_tras_el_numero`): externa a la
    norma nombrada (patrón 1) o, tras «del Anexo de la Comunicación A NNNN»,
    irresoluble con causa propia (patrón 2). (a), (b) e (i) actúan fuera de
    este detector (normalización, texto de e0-r2 y texto heredado).

    `normas_previas`: TOs (o None) de las normas nombradas en los tramos
    anteriores del mismo punto, en orden; con (e), antecedentes de una anáfora
    que no tiene norma antes dentro del tramo."""
    reglas = frozenset(reglas)
    re_puntos = _re_puntos_r2(reglas) if reglas & frozenset("cf") else RE_PUNTOS
    re_anafora = RE_ANAFORA_NORMA if "e" in reglas else RE_DICHO
    menciones: list[dict] = []
    consumidos: list[tuple[int, int]] = []
    normas: list[tuple[int, str | None]] = []
    # (e): fin de las menciones de puntos que nombran el propio TO
    fines_propios = ({pm.end() for pm in re_puntos.finditer(texto)
                      if RE_PROPIO_TO.match(texto, pm.end())} if "e" in reglas else set())
    fines_secc_propios = ({sm.end() for sm in RE_SECCION.finditer(texto)
                           if RE_PROPIO_TO.match(texto, sm.end())} if "e" in reglas else set())

    def puntos_de_ventana(ini: int, fin: int) -> tuple[list, list, list]:
        ventana = texto[ini:fin]
        pms = [pm for pm in re_puntos.finditer(ventana) if ini + pm.end() not in fines_propios]
        if "d" in reglas:
            pms = pms[-1:]
        puntos, secciones, spans = [], [], []
        for pm in pms:
            puntos += _expandir_puntos_r2(pm.group(1), reglas)
            spans.append((ini + pm.start(), ini + pm.end()))
        return puntos, secciones, spans

    for m in (RE_NORMA_R2 if "g" in reglas else RE_NORMA_NOMBRADA).finditer(texto):
        z, to_dest, via = _norma_de_match(texto, m, reglas)
        ini = max(0, m.start() - VENTANA_ANTES)
        puntos, secciones, spans = puntos_de_ventana(ini, m.start())
        for sm in RE_SECCION.finditer(texto[ini:m.start()]):
            if ini + sm.end() in fines_secc_propios:
                continue
            secciones += [x for x in sm.groups() if x]
            spans.append((ini + sm.start(), ini + sm.end()))
        consumidos += spans
        ev_ini = min([x[0] for x in spans] + [m.start()])
        men = {"clase": "externa", "norma_nombrada": z, "to_destino": to_dest,
               "puntos": puntos, "secciones": secciones,
               "evidencia": texto[ev_ini:m.end()].strip()}
        if via:
            men["via_norma"] = via
        menciones.append(men)
        normas.append((m.start(), to_dest))
    for m in re_anafora.finditer(texto):
        if "e" in reglas:
            antes = [x[1] for x in normas if x[0] < m.start()] or list(normas_previas or [])
            to_dest = antes[-1] if antes else None
            causa = None if to_dest else ("norma fuera del inventario" if antes else "anáfora sin antecedente")
        else:
            prev = [x for x in menciones if x["clase"] == "externa" and x["to_destino"]]
            to_dest = prev[-1]["to_destino"] if prev else None
            causa = None
        ini = max(0, m.start() - VENTANA_ANTES)
        puntos, secciones, spans = puntos_de_ventana(ini, m.start())
        if "e" in reglas:
            # (e): la anáfora toma también las secciones de su ventana, como
            # una norma nombrada («la Sección 4. de dichas normas»)
            for sm in RE_SECCION.finditer(texto[ini:m.start()]):
                if ini + sm.end() in fines_secc_propios:
                    continue
                secciones += [x for x in sm.groups() if x]
                spans.append((ini + sm.start(), ini + sm.end()))
        consumidos += spans
        men = {"clase": "externa_anaforica", "norma_nombrada": "dicho ordenamiento",
               "to_destino": to_dest, "puntos": puntos, "secciones": secciones,
               "evidencia": texto[ini:m.end()].strip()[-160:]}
        if causa:
            men["causa_irresoluble"] = causa
        if "e" in reglas:
            men["forma_anafora"] = " ".join(m.group(0).lower().split())
        menciones.append(men)

    def consumido(a: int, b: int) -> bool:
        return any(a >= x and b <= y for x, y in consumidos)

    def norma_despues(fin: int) -> bool:
        despues = texto[fin:fin + VENTANA_DESPUES]
        if "d" in reglas:
            sig = re_puntos.search(despues)
            if sig:
                despues = despues[:sig.start()]
        return bool(RE_NORMA.search(despues) or re_anafora.search(despues))

    for pm in re_puntos.finditer(texto):
        propio = pm.end() in fines_propios
        if consumido(pm.start(), pm.end()) or (not propio and norma_despues(pm.end())):
            continue
        k = norma_tras_el_numero(texto, pm.end()) if "j" in reglas and not propio else None
        if k is not None:
            men = {"clase": "externa" if k["patron"] == "1" else "comunicacion_anexo",
                   "norma_nombrada": k["norma_nombrada"], "to_destino": None,
                   "puntos": _expandir_puntos_r2(pm.group(1), reglas), "secciones": [],
                   "evidencia": texto[pm.start():k["fin"]].strip(), "norma_tras_el_numero": k["patron"]}
            if k["patron"] == "1" and k["entrecomillada"]:
                men["to_destino"], via = resolver_norma_r2_via(k["norma_nombrada"], True, reglas, k["norma_nombrada"])
                if via:
                    men["via_norma"] = via
            elif k["patron"] == "2":
                men["causa_irresoluble"] = CAUSA_ANEXO_COMUNICACION
            menciones.append(men)
            continue
        men = {"clase": "interna", "norma_nombrada": None, "to_destino": to_origen,
               "puntos": _expandir_puntos_r2(pm.group(1), reglas), "secciones": [],
               "evidencia": texto[max(0, pm.start() - 60):pm.end() + 20].strip()}
        if propio:
            men["marca_propio_to"] = " ".join(RE_PROPIO_TO.match(texto, pm.end()).group(0).lower().split())
        menciones.append(men)
    for sm in RE_SECCION.finditer(texto):
        if consumido(sm.start(), sm.end()):
            continue
        propio = sm.end() in fines_secc_propios
        despues = texto[sm.end():sm.end() + VENTANA_DESPUES]
        if not propio and (RE_NORMA.search(despues) or re_anafora.search(despues)):
            continue
        men = {"clase": "interna", "norma_nombrada": None, "to_destino": to_origen,
               "puntos": [], "secciones": [x for x in sm.groups() if x],
               "evidencia": texto[max(0, sm.start() - 60):sm.end() + 20].strip()}
        if propio:
            men["marca_propio_to"] = " ".join(RE_PROPIO_TO.match(texto, sm.end()).group(0).lower().split())
        menciones.append(men)
    if "h" in reglas:
        for m in RE_ESTE_PUNTO.finditer(texto):
            menciones.append({"clase": "anafora_sin_numero", "norma_nombrada": None, "to_destino": None,
                              "puntos": [], "secciones": [],
                              "evidencia": texto[max(0, m.start() - 60):m.end() + 20].strip(),
                              "causa_irresoluble": "anáfora sin número"})
    return menciones


def _texto_r2(n: dict, leer_termino: bool = True) -> str:
    """Texto guardado del nodo: label y las claves de PROPS_TEXTO(_R2), donde
    estén en el nodo r2 (properties, campos_heredados_v3 o
    properties_no_definidas)."""
    claves = PROPS_TEXTO_R2 if leer_termino else PROPS_TEXTO
    partes = [n.get("label") or ""]
    fuentes = [n.get("properties") or {}, n.get("campos_heredados_v3") or {},
               n.get("properties_no_definidas") or {}]
    for k in claves:
        for f in fuentes:
            v = f.get(k)
            if isinstance(v, str) and v:
                partes.append(v)
                break
    return " | ".join(partes)


def tiene_texto_de_cuerpo(texto: str) -> bool:
    """Criterio declarado para las variantes `::rep<k>` (regla L): un chunk
    tiene texto de cuerpo si, quitando cada línea que es un rótulo de unidad y
    la línea que sigue a cada rótulo (la cola de un título partido), queda
    alguna línea con texto. Una línea de índice («6.1. Solicitud de
    participación.», con o sin su cola) no tiene texto de cuerpo."""
    lineas = (texto or "").split("\n")
    quitar = set()
    for i, l in enumerate(lineas):
        if RE_ROTULO_UNIDAD.match(l):
            quitar.add(i)
            if i + 1 < len(lineas) and not RE_ROTULO_UNIDAD.match(lineas[i + 1]):
                quitar.add(i + 1)
    return any(l.strip() for i, l in enumerate(lineas) if i not in quitar)


def _variantes(chunks: list[dict]) -> dict[str, dict]:
    """id canónico → {canonico, variantes (ids en orden documental),
    con_cuerpo (ids con texto de cuerpo)}, solo para ids con variantes."""
    grupos: dict[str, list[dict]] = {}
    for c in chunks:
        grupos.setdefault(c.get("id_e0_original") or c["id"], []).append(c)
    out = {}
    for base, g in grupos.items():
        if len(g) > 1:
            out[base] = {"canonico": base, "variantes": [c["id"] for c in g],
                         "con_cuerpo": [c["id"] for c in g if tiene_texto_de_cuerpo(c["texto"])]}
    return out


def _chunk_de_procedencia(p: dict, emisores: dict | None) -> str | None:
    """chunk_id de una procedencia: el que trae (E2 del perfil r2) o el que
    asigna la regla de r1_provenance (punto propio, bloque, primer emisor de
    la herencia)."""
    if p.get("chunk_id"):
        return p["chunk_id"]
    to, punto, rol = p.get("to"), p.get("punto"), p.get("rol_documental") or ""
    if rol == "punto_propio":
        return f"{to}::{punto}"
    if rol.startswith("bloque_"):
        return f"{to}::{punto}::{rol[len('bloque_'):]}"
    em = (emisores or {}).get((to, punto, rol)) or []
    return em[0] if em else None


def _texto_e0_de(p: dict, chunk: dict) -> str:
    """Texto de E0 del punto de la procedencia dentro de su chunk: todos los
    tramos de esa unidad que el chunk trae en su herencia (el encabezado del
    punto en sus mini-chunks; el texto entero del punto cuando la procedencia
    es de herencia) y, si la procedencia es el punto propio o un bloque, el
    texto propio del chunk. El rol `herencia_<tipo>` nombra solo el primer
    tramo de la unidad (comun_e1.rol_documental_de_punto): se toman todos."""
    partes = [h["texto"] for h in chunk.get("herencia", []) if h["unidad_origen"] == p.get("punto")]
    if not (p.get("rol_documental") or "").startswith("herencia_"):
        partes.append(chunk.get("texto") or "")
    return "\n".join(partes)


def _tramos_e0_de(p: dict, chunk: dict) -> list[str]:
    """Los tramos de `_texto_e0_de`, por separado: cada tramo heredado de la
    unidad de la procedencia y, si corresponde, el texto propio del chunk."""
    partes = [h["texto"] for h in chunk.get("herencia", []) if h["unidad_origen"] == p.get("punto")]
    if not (p.get("rol_documental") or "").startswith("herencia_"):
        partes.append(chunk.get("texto") or "")
    return partes


def menciones_por_tramo(tramos: list[str], to_origen: str, reglas: frozenset) -> list[dict]:
    """Menciones de un punto con la evidencia literal. Con las reglas del
    perfil r2, cada tramo se lee por separado y la evidencia queda dentro de
    un solo tramo (no cruza la unión entre el texto heredado y el propio, ni
    entre dos tramos heredados); para la anáfora (e), las normas nombradas en
    los tramos anteriores del punto siguen siendo antecedentes. Sin reglas, la
    concatenación de los tramos, como en R3."""
    if not reglas:
        tramos = ["\n".join(tramos)]
    previas: list[str | None] = []
    out: list[dict] = []
    for t in tramos:
        texto, mapa = normalizar_e0(t, tolerar_linea_suelta="a" in reglas)
        ms = detectar_menciones_r2(texto, to_origen, reglas, normas_previas=previas)
        for men in ms:
            men["evidencia"] = evidencia_literal(t, texto, mapa, men["evidencia"])
        previas = previas + [m["to_destino"] for m in ms if m["clase"] == "externa"]
        out += ms
    return out


def _contiene_unidad(texto: str, men: dict, reglas: frozenset | None = None) -> bool:
    """D1: el texto guardado del nodo contiene la unidad citada (un punto o
    una sección de la cita, o la norma nombrada si la cita nombra solo la
    norma; con `reglas`, la norma se resuelve con `resolver_norma_r2`)."""
    for d in men["puntos"]:
        if re.search(r"(?<![\d.])" + re.escape(d) + r"(?![\d])", texto):
            return True
    for s_ in men["secciones"]:
        if re.search(r"\bSecci(?:o|ó)n(?:es)?\s+(?:\d+\s*(?:,|y)\s*)*" + re.escape(s_) + r"\b", texto, re.I):
            return True
    if not men["puntos"] and not men["secciones"] and men.get("to_destino"):
        if reglas is not None:
            re_n = RE_NORMA_R2 if "g" in reglas else RE_NORMA_NOMBRADA
            return any(_norma_de_match(texto, m, reglas)[1] == men["to_destino"] for m in re_n.finditer(texto))
        return any(resolver_norma(m.group(1)) == men["to_destino"] for m in RE_NORMA.finditer(texto))
    return False


def nombra_unidad(texto: str, punto: str | None = None, seccion: str | None = None) -> bool:
    """Regla (i): el texto guardado del nodo nombra el punto o la sección,
    con límite estricto del número: «3.5» no se nombra en «3.5.1.6» (en
    `_contiene_unidad`, la atribución D1, sí)."""
    if punto is not None:
        return bool(re.search(r"(?<![\d.])" + re.escape(punto) + r"(?!\.?\d)", texto))
    return bool(re.search(r"\bSecci(?:o|ó)n(?:es)?\s+(?:\d+\.?\s*(?:,|y)\s*)*" + re.escape(seccion)
                          + r"(?!\.?\d)", texto, re.I))


def alcance_remision(td: str, to_procedencia: str, a_texto_ordenado: bool) -> str:
    """§3: to_entero si el destino es un TextoOrdenado; si no, interna cuando
    la unidad citada es del mismo TO que la procedencia de resolución y
    externa cuando es de otro. No se copia la clase de la mención."""
    if a_texto_ordenado:
        return "to_entero"
    return "interna" if td == to_procedencia else "externa"


def registro_comunicaciones(chunks_por_to: dict[str, list[dict]]) -> dict:
    """Decisión 7: citas a Comunicaciones en el texto propio de los chunks de
    E0, sin arista. Por TO y por ensamblado: citas, chunks y Comunicaciones
    distintas; aparte, las citas cuya línea tiene la forma de un pie de página
    que E0 no recortó."""
    filas, por_to = [], {}
    for to in sorted(chunks_por_to):
        for c in chunks_por_to[to]:
            original = c.get("texto") or ""
            texto, mapa = normalizar_e0(original)
            for m in RE_COMUNICACION.finditer(texto):
                letra = m.group(1)
                nums = [m.group(3)] + RE_NUM_COM.findall(m.group(4) or "")
                o_ini, o_fin = mapa[m.start()], mapa[m.end() - 1] + 1
                ini = original.rfind("\n", 0, o_ini) + 1
                fin = original.find("\n", o_fin)
                linea = original[ini:fin if fin != -1 else len(original)]
                pie = bool(RE_PIE_NO_RECORTADO.search(linea))
                for x in nums:
                    filas.append({"to": to, "chunk_id": c["id"], "comunicacion": f"{letra} {x.replace('.', '')}",
                                  "tramo": original[o_ini:o_fin], "pie_no_recortado": pie})
    for to in sorted(chunks_por_to):
        fs = [f for f in filas if f["to"] == to]
        por_to[to] = {"citas": len(fs), "chunks": len({f["chunk_id"] for f in fs}),
                      "comunicaciones_distintas": len({f["comunicacion"] for f in fs}),
                      "citas_en_pie_no_recortado": sum(f["pie_no_recortado"] for f in fs)}
    return {"criterio": "RE_COMUNICACION sobre el texto propio de cada chunk de E0 (normalizar_e0); "
                        "un número = una cita",
            "total": {"citas": len(filas), "chunks": len({f["chunk_id"] for f in filas}),
                      "comunicaciones_distintas": len({f["comunicacion"] for f in filas}),
                      "citas_en_pie_no_recortado": sum(f["pie_no_recortado"] for f in filas)},
            "por_to": por_to,
            "pies_no_recortados": [f for f in filas if f["pie_no_recortado"]],
            "filas": filas}


def detectar_y_resolver_r2(kg: dict, emisores: dict | None = None, fuente: str = "e0",
                           tipos_origen: tuple = TIPOS_CONTENIDO_R2, leer_termino: bool = True,
                           por_procedencia: bool = True, propios: str = "procedencia",
                           predicado: str = PREDICADO_R2, reglas: frozenset = REGLAS_R2,
                           chunks_e0_r2: dict[str, dict] | None = None,
                           chunks_partes: dict[str, dict] | None = None,
                           procedencia_propia: bool = False, agrupar_sin_rol: bool = False,
                           punto_declarado_e1: bool = False) -> dict:
    """Remisiones del perfil r2. Por defecto, la regla firmada: detección sobre
    el texto de E0 del punto de origen (por chunk_id), desde cada procedencia
    de los siete tipos de contenido, con atribución D1, `alcance`, `destino` y
    `evidencia` en la arista y sin `rol_fuente`, `clase` ni `via`.

    Las opciones existen solo para los controles de la unidad (r2_codigo/
    r3d_remisiones.py): `fuente="parafrasis"` lee el texto guardado de cada
    nodo, como la cadena r1; `por_procedencia=False` resuelve desde la
    procedencia primaria; `propios="nodo"` excluye, como la cadena r1, todo
    punto de las procedencias del nodo de origen. Con (parafrasis, False,
    "nodo", sin termino) y los cuatro tipos de la cadena r1, los pares origen →
    destino son los de las aristas `referencia` de la cadena r1.

    `reglas` (subconjunto de REGLAS_R2; todas por defecto) son las reglas del
    detector decididas tras el freno posterior a R3 (`detectar_menciones_r2`):
    (a) línea suelta tolerada en `normalizar_e0`; (b) texto de e0-r2 cuando se
    pasa `chunks_e0_r2` (chunk_id → chunk de `correr_e0.py --version-e0
    e0-r2`); (i) citas del texto que el chunk hereda de otras unidades, para
    los nodos cuyo texto guardado nombra la unidad citada, con la procedencia
    del bloque heredado. Sin reglas, el detector es el de la cadena r1.

    `chunks_partes` (chunk_id → parte): las partes de las unidades que E1 del
    perfil r2 partió por corte (R4.b), cuyo texto no está en la E0.

    `punto_declarado_e1` (U-PROC-HERENCIA, opción D; la cadena r2 lo pasa con
    --procedencia-heredada; solo con `fuente="e0"`): una procedencia que
    corrigió C1 (la que trae `punto_declarado_e1`) se agrupa, se lee y se
    resuelve con el punto y el rol que declaró E1 (`punto_declarado_e1` y
    `rol_declarado_e1`), como sin la corrección: el bloque del ancestro vuelve
    a entrar como texto heredado, con la regla (i). La arista lleva la
    procedencia del nodo, y los destinos de una cita son los nodos anclados en
    el punto de su procedencia, el de C1. Con False (default), la salida de
    siempre."""
    if fuente not in ("e0", "parafrasis") or propios not in ("procedencia", "nodo"):
        raise ValueError(f"opción desconocida: fuente={fuente!r} propios={propios!r}")
    if punto_declarado_e1 and fuente != "e0":
        raise ValueError("punto_declarado_e1 es de la detección sobre el texto de E0 (fuente='e0')")
    reglas = frozenset(reglas)
    if not reglas <= REGLAS_R2:
        raise ValueError(f"reglas desconocidas: {sorted(reglas - REGLAS_R2)}")
    nodes_by_id = {n["id"]: n for n in kg["nodes"]}
    unidades = {to: unidades_e0(to) for to in C.TOS_ORDEN}
    chunks_por_to = {to: C.cargar_chunks_enm01(to) for to in C.TOS_ORDEN}
    chunk_por_id = {c["id"]: c for cs in chunks_por_to.values() for c in cs}
    chunk_por_id.update(chunks_partes or {})
    variantes = {k: v for cs in chunks_por_to.values() for k, v in _variantes(cs).items()}

    anclados: dict[tuple[str, str], list[str]] = {}
    anclados_chunk: dict[tuple[str, str, str], list[str]] = {}
    to_canon: dict[str, str] = {}
    for n in kg["nodes"]:
        if n["type"] == "TextoOrdenado":
            for t in sorted({p["to"] for p in n["provenances"] if p.get("to")}):
                to_canon[t] = n["id"]
            continue
        if n["type"] not in TIPOS_CONTENIDO_R2:
            continue
        for p in n.get("provenances", []):
            if p.get("to") and p.get("punto"):
                anclados.setdefault((p["to"], p["punto"]), []).append(n["id"])
                if p.get("chunk_id"):
                    anclados_chunk.setdefault((p["to"], p["punto"], p["chunk_id"]), []).append(n["id"])
    for d_ in (anclados, anclados_chunk):
        for k in d_:
            d_[k] = sorted(set(d_[k]))

    aristas: dict[tuple[str, str, str], dict] = {}
    registro: list[dict] = []
    conteo = {"procedencias_con_texto": 0, "procedencias_sin_texto_e0": 0,
              "atribucion_d1": {"nodos_que_contienen_la_unidad": 0, "todos_los_nodos_del_punto": 0},
              "aristas_con_varias_procedencias": 0, "citas_a_unidad_con_variantes": 0,
              "procedencias_sin_texto_e0_detalle": [],
              "texto_de_e0": {"e0-r2": 0, "e0_legada": 0},
              "texto_heredado": {"menciones": 0, "con_nodos_que_nombran_la_unidad": 0,
                                 "sin_nodos_que_nombran_la_unidad": 0, "autocitas_de_encabezado": 0},
              "d1_con_limite_estricto_distinto": {"menciones": 0, "ejemplos": []}}

    # U-OMISIONES-COD, grupo J (TRAMO-REMITE-A; con `procedencia_propia`, que el ensamblado pasa en r2b): cada arista
    # lleva la procedencia de su propio origen, la de la misma clave (to, punto, rol, chunk) con su tramo, y no la del
    # primer nodo del punto. La cita del texto heredado lleva la procedencia del bloque heredado, sin tramo, con la
    # marca explícita `tramo_verificado = ausente`. La detección, la atribución D1 y los destinos no cambian.
    # U-OMISIONES-COD, nota del 10/10/2026 al pie de la v7 (G-r y `remite_a`; con `agrupar_sin_rol`, que el ensamblado
    # pasa en r2b): los orígenes de una cita se agrupan por (to, punto, chunk), sin el rol. Las procedencias heredadas de
    # un mismo punto y chunk leen los mismos bloques de E0 (`_tramos_e0_de` usa el rol solo para sumar el texto propio),
    # y la corrección de rol de G-r no debe partir el grupo: la cita se atribuye una vez, con la regla D1, a todo el punto.
    clave_grupo = (("to", "punto", "chunk_id") if agrupar_sin_rol else ("to", "punto", "rol_documental", "chunk_id"))
    prov_del_nodo: dict[tuple[str, str], dict] = {}

    def de_su_origen(o: str, procedencia: dict) -> dict:
        if not procedencia_propia:
            return procedencia
        k = C.prov_key({kk: procedencia.get(kk) for kk in clave_grupo})
        propia = prov_del_nodo.get((k, o))
        if propia is not None:
            return propia
        if procedencia.get("tramo") is None and "tramo_verificado" not in procedencia:
            return {**procedencia, "tramo_verificado": "ausente"}
        return procedencia

    def agregar(src: str, tgt: str, procedencia: dict, men: dict, destino: str, alcance: str) -> bool:
        procedencia = de_su_origen(src, procedencia)
        k = (src, predicado, tgt)
        if tgt == src:
            return False
        e = aristas.get(k)
        if e is not None:
            if procedencia not in e["provenances"]:
                e["provenances"].append(dict(procedencia))
                if len(e["provenances"]) == 2:
                    conteo["aristas_con_varias_procedencias"] += 1
            return False
        aristas[k] = {"source": src, "target": tgt, "relation": predicado,
                      "provenance": dict(procedencia), "provenances": [dict(procedencia)],
                      "properties": {"alcance": alcance, "destino": destino,
                                     "evidencia": men["evidencia"]}}
        return True

    def resolver(origenes: list[str], procedencia: dict, propios_set: set, men: dict) -> dict:
        to_o = procedencia["to"]
        cita = {"origenes": origenes, "procedencia": {k: procedencia.get(k) for k in
                                                     ("to", "punto", "rol_documental", "chunk_id")},
                "clase": men["clase"], "norma_nombrada": men["norma_nombrada"],
                "to_destino": men["to_destino"], "puntos": men["puntos"],
                "secciones": men["secciones"], "evidencia": men["evidencia"],
                "destinos": [], "irresolubles": [], "aristas_nuevas": 0}
        for k in ("forma_anafora", "marca_propio_to", "via_norma", "norma_tras_el_numero"):
            if men.get(k):
                cita[k] = men[k]
        if men.get("causa_irresoluble"):
            cita["irresolubles"].append({"destino": None, "causa": men["causa_irresoluble"]})
            return cita
        if men["to_destino"] is None:
            cita["irresolubles"].append({"destino": None, "causa": (
                "norma fuera del inventario" if men["clase"] == "externa"
                else "anáfora sin norma previa resoluble")})
            return cita
        td = men["to_destino"]
        destinos = [(p_, "punto") for p_ in men["puntos"]] + [(f"S{s_}", "seccion") for s_ in men["secciones"]]
        if not destinos:
            if men["clase"] == "interna":
                cita["irresolubles"].append({"destino": None, "causa": "mención interna sin punto"})
                return cita
            if td not in to_canon:
                cita["irresolubles"].append({"destino": f"{td}::TO", "causa": "texto ordenado sin nodo"})
                return cita
            n_new = sum(agregar(o, to_canon[td], procedencia, men, f"{td}::TO", "to_entero") for o in origenes)
            cita["destinos"].append({"destino": f"{td}::TO", "alcance": "to_entero", "nodos": [to_canon[td]]})
            cita["aristas_nuevas"] += n_new
            return cita
        for d, clase in destinos:
            if td == to_o and d in propios_set:
                cita["irresolubles"].append({"destino": f"{td}::{d}", "causa": "autorreferencia al punto propio"})
                continue
            if d not in unidades[td]:
                cita["irresolubles"].append({"destino": f"{td}::{d}", "causa": f"{clase} inexistente en E0"})
                continue
            ids = anclados.get((td, d), [])
            var = variantes.get(f"{td}::{d}")
            if var is not None:
                conteo["citas_a_unidad_con_variantes"] += 1
                if len(var["con_cuerpo"]) > 1:
                    cita["irresolubles"].append({"destino": f"{td}::{d}", "causa": "destino ambiguo",
                                                 "variantes_con_cuerpo": var["con_cuerpo"]})
                    continue
                con_chunk = anclados_chunk.get((td, d, var["canonico"]))
                if con_chunk is not None or any(anclados_chunk.get((td, d, v)) for v in var["variantes"]):
                    ids = con_chunk or []
            if not any(i != o for o in origenes for i in ids):
                cita["irresolubles"].append({"destino": f"{td}::{d}", "causa": "punto_sin_nodos"})
                continue
            alc = alcance_remision(td, to_o, False)
            n_new = 0
            for o in origenes:
                for i in ids:
                    n_new += agregar(o, i, procedencia, men, f"{td}::{d}", alc)
            cita["destinos"].append({"destino": f"{td}::{d}", "alcance": alc, "nodos": ids})
            cita["aristas_nuevas"] += n_new
        return cita

    origen_nodos = sorted((n for n in kg["nodes"] if n["type"] in tipos_origen and n["type"] in TIPOS_CONTENIDO_R2),
                          key=lambda x: x["id"])
    if fuente == "parafrasis":
        for n in origen_nodos:
            procs = n["provenances"] if por_procedencia else [n["provenance"]]
            vistas = []
            for p in procs:
                if p in vistas or p.get("to") not in C.TOS_ORDEN:
                    continue
                vistas.append(p)
                texto = _texto(n) if not leer_termino else _texto_r2(n, True)
                propios_set = ({q["punto"] for q in n["provenances"]} if propios == "nodo" else {p["punto"]})
                for men in detectar_menciones(texto, p["to"]):
                    registro.append(resolver([n["id"]], p, propios_set, men))
    else:
        por_proc: dict[str, tuple[dict, list[str]]] = {}
        for n in origen_nodos:
            procs = n["provenances"] if por_procedencia else [n["provenance"]]
            for p in procs:
                if p.get("to") not in C.TOS_ORDEN or p.get("rol_documental") == "esqueleto":
                    continue
                cid = _chunk_de_procedencia(p, emisores)
                prov_canonica = dict(p)
                if cid and not p.get("chunk_id"):
                    prov_canonica = {**p, "chunk_id": cid}
                lectura = prov_canonica
                if punto_declarado_e1 and "punto_declarado_e1" in p:
                    # U-PROC-HERENCIA, opción D: la procedencia de C1 se lee y se resuelve con lo que declaró E1
                    lectura = {**prov_canonica, "punto": p["punto_declarado_e1"],
                               "rol_documental": p["rol_declarado_e1"]}
                k = C.prov_key({kk: lectura.get(kk) for kk in clave_grupo})
                prov_del_nodo.setdefault((k, n["id"]), prov_canonica)
                if k not in por_proc:
                    por_proc[k] = (lectura, [])
                if n["id"] not in por_proc[k][1]:
                    por_proc[k][1].append(n["id"])
        usar_r2 = "b" in reglas and chunks_e0_r2 is not None
        for k in sorted(por_proc):
            p, nodos = por_proc[k]
            cid = p.get("chunk_id")
            chunk = chunk_por_id.get(cid) if cid else None
            if chunk is not None and usar_r2:
                if cid in chunks_e0_r2:
                    chunk = chunks_e0_r2[cid]
                    conteo["texto_de_e0"]["e0-r2"] += 1
                else:
                    conteo["texto_de_e0"]["e0_legada"] += 1
            elif chunk is not None:
                conteo["texto_de_e0"]["e0_legada"] += 1
            if chunk is None:
                conteo["procedencias_sin_texto_e0"] += 1
                conteo["procedencias_sin_texto_e0_detalle"].append({kk: p.get(kk) for kk in
                                                                    ("to", "punto", "rol_documental", "chunk_id")})
                continue
            conteo["procedencias_con_texto"] += 1
            propios_set = ({q["punto"] for i in nodos for q in nodes_by_id[i]["provenances"]}
                           if propios == "nodo" else {p["punto"]})
            reglas_d1 = reglas or None
            for men in menciones_por_tramo(_tramos_e0_de(p, chunk), p["to"], reglas):
                if men["clase"] == "anafora_sin_numero":
                    cita = resolver(list(nodos), p, propios_set, men)
                    cita["atribucion"] = "sin_destino"
                    cita["chunk_id"] = cid
                    registro.append(cita)
                    continue
                contienen = [i for i in nodos
                             if _contiene_unidad(_texto_r2(nodes_by_id[i], leer_termino), men, reglas_d1)]
                if reglas and (men["puntos"] or men["secciones"]):
                    # informativo: la atribución D1 con el límite estricto de
                    # `nombra_unidad` (la regla firmada usa `_contiene_unidad`)
                    estrictos = [i for i in nodos if any(
                        nombra_unidad(_texto_r2(nodes_by_id[i], leer_termino), punto=d) for d in men["puntos"]) or any(
                        nombra_unidad(_texto_r2(nodes_by_id[i], leer_termino), seccion=s_) for s_ in men["secciones"])]
                    if estrictos != contienen:
                        x = conteo["d1_con_limite_estricto_distinto"]
                        x["menciones"] += 1
                        if len(x["ejemplos"]) < 10:
                            x["ejemplos"].append({"chunk_id": cid, "puntos": men["puntos"], "secciones": men["secciones"],
                                                  "contienen": len(contienen), "estrictos": len(estrictos)})
                if contienen:
                    conteo["atribucion_d1"]["nodos_que_contienen_la_unidad"] += 1
                else:
                    conteo["atribucion_d1"]["todos_los_nodos_del_punto"] += 1
                cita = resolver(contienen or list(nodos), p, propios_set, men)
                cita["atribucion"] = "contiene_la_unidad" if contienen else "todos_los_nodos_del_punto"
                cita["chunk_id"] = cid
                registro.append(cita)
            if "i" not in reglas:
                continue
            # (i) citas del texto que el chunk hereda de otras unidades: cada
            # unidad citada va solo a los nodos cuyo texto guardado la nombra
            # (`nombra_unidad`), con la procedencia del bloque heredado.
            heredadas = []
            for h in chunk.get("herencia", []):
                if h["unidad_origen"] != p["punto"] and h["unidad_origen"] not in heredadas:
                    heredadas.append(h["unidad_origen"])
            for u in heredadas:
                tipo_h = next(h["tipo"] for h in chunk["herencia"] if h["unidad_origen"] == u)
                # procedencia del bloque heredado con la forma de las de E2
                # (archivo, páginas del bloque y ancestros de la unidad heredada)
                anc = p.get("ancestros") or []
                p_h = {"to": p["to"], "archivo": p.get("archivo"), "punto": u, "rol_documental": f"herencia_{tipo_h}",
                       "chunk_id": cid,
                       "paginas": sorted({pg for h in chunk["herencia"] if h["unidad_origen"] == u
                                          for pg in (h.get("paginas") or [])}),
                       "ancestros": anc[:anc.index(u)] if u in anc else []}
                for men in menciones_por_tramo(_tramos_e0_de(p_h, chunk), p["to"], reglas):
                    if men["clase"] == "anafora_sin_numero":
                        continue
                    if es_autocita_de_encabezado(men, u):
                        # U-R2-CODIGO-2, C2, punto d: no es una cita; se cuenta aparte y no va al registro
                        conteo["texto_heredado"]["autocitas_de_encabezado"] += 1
                        continue
                    conteo["texto_heredado"]["menciones"] += 1
                    unidades_men = ([{**men, "puntos": [d], "secciones": []} for d in men["puntos"]]
                                    + [{**men, "puntos": [], "secciones": [s_]} for s_ in men["secciones"]])
                    if not unidades_men:
                        unidades_men = [men]
                    alguna = False
                    for mu in unidades_men:
                        if mu["puntos"]:
                            nombran = [i for i in nodos if nombra_unidad(_texto_r2(nodes_by_id[i], leer_termino),
                                                                       punto=mu["puntos"][0])]
                        elif mu["secciones"]:
                            nombran = [i for i in nodos if nombra_unidad(_texto_r2(nodes_by_id[i], leer_termino),
                                                                       seccion=mu["secciones"][0])]
                        else:
                            nombran = [i for i in nodos
                                       if _contiene_unidad(_texto_r2(nodes_by_id[i], leer_termino), mu, reglas_d1)]
                        if not nombran:
                            continue
                        alguna = True
                        cita = resolver(nombran, p_h, propios_set | {u}, mu)
                        cita["atribucion"] = "texto_heredado"
                        cita["chunk_id"] = cid
                        cita["procedencia_de_los_nodos"] = {kk: p.get(kk) for kk in
                                                            ("to", "punto", "rol_documental", "chunk_id")}
                        registro.append(cita)
                    conteo["texto_heredado"]["con_nodos_que_nombran_la_unidad" if alguna
                                             else "sin_nodos_que_nombran_la_unidad"] += 1

    nuevas = [aristas[k] for k in sorted(aristas)]
    tipo = {n["id"]: n["type"] for n in kg["nodes"]}
    triplas = {(e["source"], e["relation"], e["target"]) for e in kg["edges"]}
    agregadas = [e for e in nuevas if (e["source"], e["relation"], e["target"]) not in triplas]
    kg["edges"].extend(agregadas)

    def por(objs, f):
        out: dict[str, int] = {}
        for o in objs:
            k = f(o)
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    # Unidad de conteo de §5 de la enmienda 2: la cita = (chunk de origen,
    # tramo, unidad citada). Una cita cuenta en cada firma (tipo de origen →
    # tipo de destino) de sus pares; la suma por firma puede superar el total.
    def clave_origen(c: dict) -> str:
        return c.get("chunk_id") or C.prov_key(c["procedencia"])

    citas_res: dict[tuple, dict] = {}
    citas_irr: dict[tuple, str] = {}
    for c in registro:
        for d in c["destinos"]:
            k = (clave_origen(c), c["evidencia"], d["destino"])
            x = citas_res.setdefault(k, {"alcance": d["alcance"], "firmas": set()})
            x["firmas"] |= {f"{tipo[o]}->{tipo[t]}" for o in c["origenes"] for t in d["nodos"] if o != t}
        for x in c["irresolubles"]:
            citas_irr.setdefault((clave_origen(c), c["evidencia"], x["destino"]), x["causa"])
    citas_firma: dict[str, int] = {}
    for x in citas_res.values():
        for f in x["firmas"]:
            citas_firma[f] = citas_firma.get(f, 0) + 1
    resumen = {
        "perfil": PERFIL_R2, "predicado": predicado,
        "opciones": {"fuente": fuente, "tipos_origen": list(tipos_origen), "leer_termino": leer_termino,
                     "por_procedencia": por_procedencia, "propios": propios},
        "unidad_de_cita": "(chunk de origen, tramo, unidad citada)",
        "menciones_detectadas": len(registro),
        "citas_resueltas": len(citas_res),
        "citas_resueltas_por_alcance": por(citas_res.values(), lambda x: x["alcance"]),
        "citas_resueltas_por_firma": dict(sorted(citas_firma.items())),
        "citas_irresolubles": len(citas_irr),
        "irresolubles_por_causa": por(citas_irr.values(), lambda x: x),
        "aristas": len(nuevas),
        "aristas_agregadas": len(agregadas),
        "aristas_por_alcance": por(nuevas, lambda e: e["properties"]["alcance"]),
        "aristas_por_firma": por(nuevas, lambda e: f"{tipo[e['source']]}->{tipo[e['target']]}"),
        "atribucion_d1": conteo["atribucion_d1"] if fuente == "e0" else None,
        "procedencias_con_texto": conteo["procedencias_con_texto"],
        "procedencias_sin_texto_e0": conteo["procedencias_sin_texto_e0"],
        "aristas_con_varias_procedencias": conteo["aristas_con_varias_procedencias"],
        "citas_a_unidad_con_variantes": conteo["citas_a_unidad_con_variantes"],
        "reglas": "".join(sorted(reglas)),
        "texto_de_e0": conteo["texto_de_e0"] if fuente == "e0" else None,
        "texto_heredado": conteo["texto_heredado"] if fuente == "e0" else None,
        "d1_con_limite_estricto_distinto_informativo": (conteo["d1_con_limite_estricto_distinto"]
                                                        if fuente == "e0" and reglas else None),
        "citas_texto_heredado": len({k for c in registro if c.get("atribucion") == "texto_heredado"
                                     for k in [(clave_origen(c), c["evidencia"], d["destino"]) for d in c["destinos"]]}),
    }
    comunicaciones = registro_comunicaciones(chunks_por_to)
    if "j" in reglas:
        # (j), patrón 2: la cita a un punto del Anexo de una Comunicación, en el registro de Comunicaciones
        anexo = {(c.get("chunk_id"), c["evidencia"], tuple(c["puntos"])): c for c in registro
                 if c["clase"] == "comunicacion_anexo"}
        comunicaciones["citas_a_puntos_de_anexo"] = [
            {"to": c["procedencia"]["to"], "chunk_id": c.get("chunk_id"), "comunicacion": c["norma_nombrada"],
             "puntos": c["puntos"], "tramo": c["evidencia"]} for _, c in sorted(anexo.items(), key=lambda kv: (
                 kv[0][0] or "", kv[0][1], kv[0][2]))]
    return {"resumen": resumen, "registro": registro, "nuevas": nuevas,
            "procedencias_sin_texto_e0": conteo["procedencias_sin_texto_e0_detalle"],
            "comunicaciones": comunicaciones}
