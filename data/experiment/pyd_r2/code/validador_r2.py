"""
validador_r2.py — U-PYD: validador de la salida de E1 en el perfil r2.

Aplica la política por campo (`data/experiment/pyd_r2/politica_campos_r2.json`,
cuyo sha256 queda en cada resultado) y devuelve los elementos aceptados como
modelos de `modelos_r2`, los rechazos con motivo, las omisiones, los
pendientes del registro de no mapeados y los contadores por campo y
tratamiento. Un valor fuera de lista nunca se descarta en silencio: se
normaliza con contador y original guardado, se registra con la marca
`fuera_de_lista`, o el elemento se rechaza con motivo (L-ESQ-R2 §2.3).

Incluye:
  - pasos de la política por campo (P-a0 a P-a10) y alias (decisión 4);
  - matriz r2: la congelada más condicion_de → Operacion y → Potestad; las
    relaciones que solo valen por la ampliación llevan `no_verificada_e3`
    (L-ESQ-R2 §6.4);
  - coherencia entre Restriccion.tipo y el predicado (`BKL-0038`), como marca;
  - verificación de la mención en dos niveles (P-b3, P-b4), sin rechazar.
    LÍMITE DECLARADO: prueba presencia de la mención en el texto del chunk, no
    pertenencia al chunk (6 de 63 menciones aparecen literalmente en un chunk
    ajeno del mismo TO; resultados/mediciones_p2.json, ventana);
  - omisiones: tramo verificado contra el texto propio (P-e2), tipos
    rechazados como `fuera_de_tipos` (P-e3), strings del crudo v3 (P-a10).

`desde_v3` lee el input de un tool call del perfil v3 (o del de desarrollo)
en la forma r2: `sujeto_propuesto` es la mención y cada string de
`omisiones_no_prosa` una omisión sin categoría ni tramo (L-ESQ-R2 §3.4, §5.4).

Forma «r2» (salida del prefijo r2b; U-PROMPT-R2, P3). Solo con esa forma:
  - el tramo de evidencia de cada entidad y el `termino` literal de la
    Definicion se verifican con la regla de la mención y su marca va a la
    procedencia (decisiones 15 y 16); el tramo de dos segmentos de la entidad
    compuesta de un ítem se parte en « […] » y cada segmento se verifica en
    su texto (diseño, §8.2);
  - `Comunicacion.tipo` y `numero` se derivan de `codigo` (decisión 16);
  - el tramo de umbral sin cuantía es un límite relativo: el elemento sin
    valor, con su comparación y su base (decisión 21, punto 5 del §10.1);
  - las `otras_propiedades` de la relación van a `properties_no_definidas` y
    la omisión `relacion_sin_predicado` admite `source` y `destino`
    (decisión 17);
  - con `vistos_e3` (los índices del crudo que validador_e1 pasó a E3), entra
    solo lo que pasó por E3 y `no_verificada_e3` se calcula por eso, no por la
    firma (nota del 04/10/2026 al mandato).
U-PROMPT-R2, P3b (diseño aprobado en el FRENO P3b-1, 023f9a0), solo con la forma r2:
  - h: en un mini-chunk que empieza a mitad de oración (prompt_r2b.mini_a_mitad), el tramo simple también se
    verifica contra la última línea de títulos y el texto en orden de lectura, y se cuenta aparte;
  - l: `Comunicacion.tipo` se deriva del tramo verificado, no del código ni de la etiqueta, que escribe el
    modelo: una Comunicación nombrada da su letra (también en una enumeración) y el número se controla contra el
    código; una norma externa da «externa»; sin sustento no se deriva y se cuenta;
  - la modalidad: `otras_propiedades.modalidad` y `.consecuencia` se clasifican con una lista cerrada
    (MODALIDAD_FORMAS) en `properties_no_definidas.modalidad_clasificada`;
  - las marcas del ratchet de E3 que trae `vistos_e3["marcas"]` (runner_corpus.vistos_por_e3 lleva la de la copia
    de la nota) van a `marcas_e3` de la validación, y la copia de la nota, además, a
    `properties_no_definidas.copia_nota_e3` de la entidad.
Con la forma v3 la salida es la de siempre, byte a byte.

No edita nada del pipeline: importa `comun_e1` (puntos admitidos y rol
documental) sin cambiarlo. Sin API, sin archivos escritos.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import modelos_r2 as M  # noqa: E402

_E1 = M.REPO / "data" / "experiment" / "reextraccion_v2" / "e1_extractor"
if str(_E1) not in sys.path:
    sys.path.insert(0, str(_E1))
from comun_e1 import chunk_flaggeado, puntos_admitidos, rol_documental_de_punto  # noqa: E402

POLITICA = M.PYD_R2 / "politica_campos_r2.json"
PERFIL = "r2"


# ------------------------------------------------------------------------- #
# Política                                                                    #
# ------------------------------------------------------------------------- #
class Politica:
    """La tabla de configuración versionada, con su sha256."""

    PASOS_CONOCIDOS = {
        "tipo_entidad": ("en_lista", "forma", "alias"),
        "predicado": ("en_lista", "forma", "alias"),
        "Obligacion.tipo": ("en_lista",),
        "Restriccion.tipo": ("en_lista",),
        "Comunicacion.tipo": ("en_lista", "derivar_de_codigo_o_label", "externa_por_lexico"),
        "Obligacion.frecuencia": ("en_lista", "desde_tramo"),
    }

    def __init__(self, ruta: Path = POLITICA):
        crudo = Path(ruta).read_bytes()
        self.ruta = Path(ruta)
        self.sha256 = hashlib.sha256(crudo).hexdigest()
        self.d = json.loads(crudo.decode("utf-8"))
        for campo, pasos in self.PASOS_CONOCIDOS.items():
            declarados = tuple(self.d["campos"][campo]["pasos"])
            for p in declarados:
                if p not in pasos:
                    raise RuntimeError(f"política: paso desconocido {p!r} en {campo}")
        self.alias_tipo = dict(self.d["alias"]["tipo_entidad"])
        self.alias_pred = dict(self.d["alias"]["predicado"])
        self.holgura = self.d["parametros"]["mencion_holgura_tokens"]["valor"]
        self.largo_min_omision = self.d["parametros"]["omision_largo_minimo_tokens"]["valor"]
        self.lexico_externa = frozenset(self.d["campos"]["Comunicacion.tipo"]["lexico_externa"])
        her = self.d["campos"]["claves"]["heredadas_v3"]
        if {t: tuple(v) for t, v in her.items()} != M.CLAVES_HEREDADAS_V3:
            raise RuntimeError("política: claves heredadas de v3 distintas de las del modelo")
        amp = tuple(tuple(x) for x in self.d["campos"]["firma"]["ampliacion"])
        if amp != M.AMPLIACION_R2:
            raise RuntimeError("política: ampliación de la matriz distinta de la del modelo")

    def pasos(self, campo: str) -> tuple[str, ...]:
        return tuple(self.d["campos"][campo]["pasos"])

    def modo(self, campo: str) -> str:
        return self.d["campos"][campo]["si_no_resuelve"]


_POLITICA_DEFAULT: Optional[Politica] = None


def politica_default() -> Politica:
    global _POLITICA_DEFAULT
    if _POLITICA_DEFAULT is None:
        _POLITICA_DEFAULT = Politica()
    return _POLITICA_DEFAULT


# ------------------------------------------------------------------------- #
# Texto: R-NORM (N1) con offsets, verificación de tramos                       #
# ------------------------------------------------------------------------- #
_GUION = re.compile(r"(\w)-\s*\n\s*(\w)")
_ALNUM = frozenset("0123456789abcdefghijklmnopqrstuvwxyz")


def fold(s: str) -> str:
    d = unicodedata.normalize("NFKD", s)
    return "".join(c for c in d if not unicodedata.combining(c)).lower()


def tokens_con_spans(texto: str) -> list[tuple[str, int, int]]:
    """Tokens de R-NORM (reports/u_listas_nomap/u_listas_n1.py:250-254: une los
    cortes por guion de fin de línea, NFKD sin diacríticos, minúsculas, no
    alfanumérico a espacio) con el span de cada token en el texto original."""
    saltar = set()
    for m in _GUION.finditer(texto):
        saltar.update(range(m.start() + 1, m.end() - 1))
    toks: list[tuple[str, int, int]] = []
    actual, ini, fin = [], -1, -1
    for i, ch in enumerate(texto):
        if i in saltar:
            continue
        for c in fold(ch):
            if c in _ALNUM:
                if not actual:
                    ini = i
                actual.append(c)
                fin = i + 1
            elif actual:
                toks.append(("".join(actual), ini, fin))
                actual = []
    if actual:
        toks.append(("".join(actual), ini, fin))
    return toks


def norm_tokens(s: str) -> list[str]:
    return [t for t, _, _ in tokens_con_spans(s)]


def _ventana_minima(texto_toks: list[str], necesarios: set[str]) -> Optional[tuple[int, int]]:
    """Ventana contigua más corta (índices de token, fin exclusivo) que contiene
    todos los tokens necesarios."""
    if not necesarios or not necesarios <= set(texto_toks):
        return None
    falta = len(necesarios)
    cuenta: Counter = Counter()
    mejor = None
    izq = 0
    for der, t in enumerate(texto_toks):
        if t in necesarios:
            cuenta[t] += 1
            if cuenta[t] == 1:
                falta -= 1
        while falta == 0:
            if mejor is None or der + 1 - izq < mejor[1] - mejor[0]:
                mejor = (izq, der + 1)
            u = texto_toks[izq]
            if u in necesarios:
                cuenta[u] -= 1
                if cuenta[u] == 0:
                    falta += 1
            izq += 1
    return mejor


# U-OMISIONES-COD, grupo B, ítem f: en la verificación de la mención de sujeto, «del» se lee «de el» y «al», «a el»,
# en la mención y en el texto («el cuentacorrentista» contra «Obligaciones del cuentacorrentista»). Solo ahí: las
# demás verificaciones (tramos, omisiones, umbrales, términos) no cambian.
CONTRACCIONES = {"del": ("de", "el"), "al": ("a", "el")}


def _expandir_contracciones(toks: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    return [(x, i, f) for t, i, f in toks for x in CONTRACCIONES.get(t, (t,))]


def verificar_tramo(aguja: str, texto: str, holgura: Optional[int],
                    contracciones: bool = False) -> tuple[str, Optional[str]]:
    """Nivel 1 («exacta»): la secuencia de tokens de la aguja aparece contigua
    en el texto (equivale a la subcadena normalizada entre límites de palabra
    de R-NORM). Nivel 2 («tokens»): todos sus tokens distintos aparecen en una
    ventana contigua de a lo sumo len(distintos) + holgura tokens (holgura
    None = sin tope); devuelve el tramo literal mínimo del texto. Si no, «no».
    Con `contracciones`, «del» y «al» se expanden en la aguja y en el texto
    (CONTRACCIONES); cada parte conserva el span de la contracción."""
    at = norm_tokens(aguja)
    if contracciones:
        at = [x for t in at for x in CONTRACCIONES.get(t, (t,))]
    if not at:
        return "no", None
    tt = tokens_con_spans(texto)
    if contracciones:
        tt = _expandir_contracciones(tt)
    tt_s = [t for t, _, _ in tt]
    n = len(at)
    for i in range(len(tt_s) - n + 1):
        if tt_s[i:i + n] == at:
            return "exacta", None
    v = _ventana_minima(tt_s, set(at))
    if v is None:
        return "no", None
    if holgura is not None and v[1] - v[0] > len(set(at)) + holgura:
        return "no", None
    return "tokens", texto[tt[v[0]][1]:tt[v[1] - 1][2]]


def texto_completo(chunk: dict) -> str:
    """Texto propio más el heredado, como en R-NORM de N1 (unidos por salto)."""
    partes = [chunk.get("texto") or ""] + [h.get("texto") or "" for h in chunk.get("herencia") or []]
    return "\n".join(partes)


def texto_heredado(chunk: dict) -> str:
    """Los bloques heredados unidos: un encabezado puede repartirse entre la línea de título y el párrafo que la
    continúa (diseño de U-PROMPT-R2, §8.2)."""
    return "\n".join(h.get("texto") or "" for h in chunk.get("herencia") or [])


# Tramo de la entidad compuesta con el encabezado de una lista (R11 y R30 del prefijo r2b): dos segmentos
# copiados tal cual, unidos por « […] »; se admite también «[...]».
SEPARADOR_TRAMO_COMPUESTO = " […] "
_RE_SEPARADOR_TRAMO = re.compile(r"\s*\[\s*(?:…|\.\.\.)\s*\]\s*")
_ORDEN_NIVEL = {"no": 0, "tokens": 1, "exacta": 2}


def _es_item(chunk: dict) -> bool:
    # La definición de ítem de lista del mensaje de E1 r2b (prompt_r2b.es_item), sin duplicarla.
    if str(_E1) not in sys.path:
        sys.path.insert(0, str(_E1))
    import prompt_r2b  # noqa: PLC0415 — solo en la forma r2
    return prompt_r2b.es_item(chunk)


def _mini_a_mitad(chunk: dict) -> bool:
    # P3b, h: la definición del mensaje de E1 r2b (prompt_r2b.mini_a_mitad), sin duplicarla.
    if str(_E1) not in sys.path:
        sys.path.insert(0, str(_E1))
    import prompt_r2b  # noqa: PLC0415 — solo en la forma r2
    return prompt_r2b.mini_a_mitad(chunk)


def texto_en_orden_de_lectura(chunk: dict) -> str:
    """P3b, h: la última línea de títulos y el texto del mini-chunk, en el orden en que se leen."""
    return ((chunk.get("herencia") or [{}])[-1].get("texto") or "") + "\n" + (chunk.get("texto") or "")


def verificar_tramo_omision(tramo: str, chunk: dict, holgura: Optional[int],
                            reg: "_Registro") -> tuple[str, Optional[str]]:
    """U-PROMPT-R2, P3c, punto g: el tramo de una omisión se verifica como el tramo simple de la entidad. Primero
    contra el texto propio, como antes: lo que verifica ahí no cambia. Si no verifica, contra el texto completo y, en
    un mini-chunk a mitad de oración, en el orden de lectura (P3b, h). El nivel conserva sus cuatro valores; lo que
    verifica solo fuera del texto propio va a los contadores `omisiones.tramo_solo_heredado` y
    `omisiones.tramo_orden_de_lectura`."""
    nivel, literal = verificar_tramo(tramo, chunk.get("texto") or "", holgura)
    if nivel != "no":
        return nivel, literal
    donde = None
    n_c, lit_c = verificar_tramo(tramo, texto_completo(chunk), holgura)
    if n_c != "no":
        nivel, literal, donde = n_c, lit_c, "tramo_solo_heredado"
    if nivel != "exacta" and _mini_a_mitad(chunk):
        n_l, lit_l = verificar_tramo(tramo, texto_en_orden_de_lectura(chunk), holgura)
        if _ORDEN_NIVEL[n_l] > _ORDEN_NIVEL[nivel]:
            nivel, literal, donde = n_l, lit_l, "tramo_orden_de_lectura"
    if donde is not None:
        reg.cuenta("omisiones", donde)
    return nivel, literal


# U-PROMPT-R2, P3c (decisión 2 de la autora sobre el FRENO P3c-1): marcas que, en el tramo de una omisión
# `meta_normativo`, señalan contenido que la regla 9 enmendada no admite ahí (enmienda 7 a L-ESQ-R2). Se buscan sobre
# el tramo normalizado (minúsculas, sin tildes, palabras enteras). Cuentan y no rechazan: el contador lo suma el
# reporte de U-REEXT-T0. Las siete clases son las de la enmienda 7, §1.2 (corrección del FRENO P3c-2): deber,
# prohibición, facultad, condición, excepción, alcance y modalidad.
# Un modal negado («no podrá», «no deberán», «no está facultada») dice una prohibición: cuenta en esa clase y no en
# deber ni en facultad. La aplicación negada («no será de aplicación», «no se aplica», «no rige») es una excepción y no
# un alcance. Deber, facultad y alcance se buscan sobre el tramo sin lo negado (_NEGADO).
_COPULA = r"(es|son|sea|sean|sera|seran|resulta|resultan|resulte|resulten|resultara|resultaran)"
_MODAL_NEGADO = (r"\b(no|ni|tampoco) (se )?((esta|estan|estara|estaran) )?(puede|pueden|podra|podran|podria|podrian|"
                 r"debe|deben|debera|deberan|deberia|deberian|facultad[oa]s?)\b")
_APLICACION_NEGADA = (r"\b(no|ni|tampoco) (se )?(" + _COPULA + r" )?(de aplicacion|aplica|aplican|aplicara|aplicaran|"
                      r"aplicables?|rige|rigen|regira|regiran)\b")
MARCAS_META_NORMATIVO = {
    "deber": re.compile(r"\b(debe|deben|debera|deberan|deberia|deberian|se requiere|se requerira|se requeriran|"
                        r"obligad[oa]s?|tendra que|tendran que)\b"),
    "prohibicion": re.compile(_MODAL_NEGADO + r"|\b(prohib\w*|vedad[oa]s?|en ningun caso|abst(ener|endr)\w*)\b"
                              r"|\bno (se )?((esta|estan|estara|estaran|sera|seran) )?(admit|permit|autoriz)\w*"),
    "facultad": re.compile(r"\b(puede|pueden|podra|podran|podria|podrian|facultad[oa]?s?)\b"),
    "condicion": re.compile(r"\b(cuando|siempre que|en tanto|en la medida en que|en caso de|a condicion de|"
                            r"condicion|condiciones)\b"),
    "excepcion": re.compile(r"\b(excepto|salvo|con excepcion de|exceptu\w*|exclu\w*)\b|" + _APLICACION_NEGADA),
    "alcance": re.compile(r"\b(abarca|abarcan|abarcara|abarcaran|comprende|comprenden|comprendera|comprenderan|"
                          r"comprendid[oa]s?|incluye|incluyen|incluira|incluiran|incluid[oa]s?|alcanzad[oa]s?|"
                          r"rige para|rigen para|regira para|regiran para|se aplica|se aplican|se aplicara|"
                          r"se aplicaran|aplicables? a|" + _COPULA + r" de aplicacion)\b"),
}
# La modalidad es la del prefijo r2b (prueba de la regla 9): «si algo se exige, se permite o se aconseja, o si basta una
# entre varias opciones» (decisión de la autora posterior al commit de P3c-2, 04/10/2026). Lo que se exige y lo que se
# permite ya lo cuentan deber y facultad. La modalidad tiene tres subclases, cada una con su contador:
#   - opcion: el cuantificador entre varias opciones, si basta una o se exigen todas;
#   - consejo: la recomendación del prefijo (la conducta que se aconseja, deseable, conveniente o práctica que se
#     espera);
#   - forma: el medio o la forma de un acto. Un requisito de forma también es contenido normativo, pero no es la
#     modalidad del prefijo: va aparte para que el reporte los distinga.
# La clase cuenta si marca alguna de las tres.
SUBCLASES_MODALIDAD = {
    "opcion": re.compile(r"\b(indistintamente|concurrentemente|cualquiera (de|del)|alguno (de|del)|alguna de|"
                         r"a opcion (de|del)|alternativas?|alternativamente)\b"),
    "consejo": re.compile(r"\b(se recomienda|se recomiendan|se aconseja|se aconsejan|buenas? practicas?|"
                          r"practicas? que se esperan?|" + _COPULA + r" (recomendables?|aconsejables?|deseables?|"
                          r"convenientes?))\b"),
    "forma": re.compile(r"\b(mediante|por medio de|a traves de|por intermedio de|por escrito|en forma|en soporte|"
                        r"por via|modalidad|modalidades)\b"),
}
MARCAS_META_NORMATIVO["modalidad"] = re.compile("|".join(rx.pattern for rx in SUBCLASES_MODALIDAD.values()))
_NEGADO = re.compile(_MODAL_NEGADO + "|" + _APLICACION_NEGADA)
_CLASES_SIN_NEGADO = ("deber", "facultad", "alcance")


def marcas_meta_normativo(tramo: str) -> list[str]:
    """Las clases de MARCAS_META_NORMATIVO presentes en el tramo, en el orden del diccionario."""
    t = " ".join(norm_tokens(tramo))
    sin_negado = _NEGADO.sub(" ", t)
    return [clase for clase, rx in MARCAS_META_NORMATIVO.items()
            if rx.search(sin_negado if clase in _CLASES_SIN_NEGADO else t)]


def subclases_modalidad(tramo: str) -> list[str]:
    """Las subclases de SUBCLASES_MODALIDAD presentes en el tramo, en el orden del diccionario."""
    t = " ".join(norm_tokens(tramo))
    return [sub for sub, rx in SUBCLASES_MODALIDAD.items() if rx.search(t)]


def verificar_tramo_entidad(tramo: str, chunk: dict, punto: str, holgura: Optional[int],
                            reg: "_Registro") -> tuple[str, str, Optional[str]]:
    """Decisión 15: verifica el tramo de evidencia de una entidad y devuelve (tramo, nivel, tramo_modelo).
    Tramo simple: la regla de la mención contra el texto propio y el heredado; con «tokens», el tramo guardado es
    el literal mínimo del texto y el del modelo va aparte. Tramo de dos segmentos (un « […] »): en un ítem, el
    primero contra el texto heredado y el segundo contra el propio; fuera de un ítem, los dos contra el texto
    completo; el nivel es el menor de los dos y el de cada segmento va al registro. Con dos o más separadores,
    «no». Un tramo simple que solo verifica en el heredado se cuenta según dónde se ancla la entidad."""
    partes = _RE_SEPARADOR_TRAMO.split(tramo)
    if len(partes) == 1:
        nivel, literal = verificar_tramo(tramo, texto_completo(chunk), holgura)
        lectura = False
        if nivel != "exacta" and _mini_a_mitad(chunk):
            # P3b, h: el tramo puede cruzar del título al cuerpo.
            n_l, lit_l = verificar_tramo(tramo, texto_en_orden_de_lectura(chunk), holgura)
            if _ORDEN_NIVEL[n_l] > _ORDEN_NIVEL[nivel]:
                nivel, literal, lectura = n_l, lit_l, True
                reg.cuenta("tramo_entidad", f"orden_de_lectura:{n_l}")
        guardado, modelo = (literal, tramo) if nivel == "tokens" and literal is not None else (tramo, None)
        reg.cuenta("tramo_entidad", nivel)
        if lectura:
            return guardado, nivel, modelo
        if nivel != "no" and verificar_tramo(guardado, chunk.get("texto") or "", holgura)[0] == "no":
            caso = ("entidad_anclada_en_ancestro" if punto != chunk.get("unidad")
                    else "heredado_compuesto" if _es_item(chunk) else "sin_ancla_fuera_de_item")
            reg.cuenta("tramo_entidad", f"solo_heredado:{caso}")
        return guardado, nivel, modelo
    if len(partes) > 2:
        reg.cuenta("tramo_compuesto", "dos_o_mas_separadores")
        reg.cuenta("tramo_entidad", "no")
        return tramo, "no", None
    encabezado, item = partes
    if _es_item(chunk):
        n_enc = verificar_tramo(encabezado, texto_heredado(chunk), holgura)[0]
        n_item = verificar_tramo(item, chunk.get("texto") or "", holgura)[0]
        reg.cuenta("tramo_compuesto", f"encabezado.{n_enc}")
        reg.cuenta("tramo_compuesto", f"item.{n_item}")
    else:
        n_enc = verificar_tramo(encabezado, texto_completo(chunk), holgura)[0]
        n_item = verificar_tramo(item, texto_completo(chunk), holgura)[0]
        reg.cuenta("tramo_compuesto", "fuera_de_item")
    nivel = min((n_enc, n_item), key=_ORDEN_NIVEL.__getitem__)
    reg.cuenta("tramo_entidad", nivel)
    return tramo, nivel, None


def elemento_umbral_relativo(tramo: str, nivel: str) -> Optional[dict]:
    """Decisión 21 (nota del 02/10/2026 a L-ESQ-R2 §1.5; punto 5 del §10.1 del diseño de U-PROMPT-R2): un tramo
    de umbral sin cuantía es un límite relativo, y el código arma el elemento sin `valor`, con su `comparacion` y
    su `base`. La comparación sale del primer marcador del tramo, con las reglas de U-PYD
    (reglas_comparacion.fijar_comparacion, negación incluida); la base, del texto que sigue al marcador hasta el
    fin de la cláusula. Sin marcador, `no_determinada` y sin base. Con cuantía devuelve None: ese tramo lo arma el
    ensamblado (par A)."""
    import reglas_comparacion as RCMP  # noqa: PLC0415 — pyd_r2/code, solo en la forma r2
    if RCMP.detectar_cuantias(tramo):
        return None
    pleg = RCMP.plegar(tramo)
    marcas = sorted((m.start(), m.end()) for _, _, pat in RCMP.COMPUESTAS + RCMP.SIMPLES for m in pat.finditer(pleg))
    comparacion, regla, base = "no_determinada", "sin_marcador", None
    if marcas:
        ini_m, fin_m = marcas[0]
        lims = RCMP.limites_de_clausula(tramo)
        ini_cl = max([p + 1 for p in lims if p < ini_m], default=0)
        fin_cl = min([p for p in lims if p >= fin_m], default=len(tramo))
        c = RCMP.Cuantia(inicio=fin_m, fin=fin_m, texto="", clase="limite_relativo")
        RCMP.fijar_comparacion(tramo, c, ini_cl, fin_cl, 0, len(tramo))
        comparacion, regla = c.comparacion, c.regla
        i = fin_m
        m = re.compile(r"\s*(?:(?:a|al|de|del)\s+)?").match(pleg, i, fin_cl)
        i = m.end() if m else i
        a = RCMP._RE_ARTICULO.match(pleg, i, fin_cl)
        i = a.end() if a else i
        fin = fin_cl
        coma = tramo.find(",", i, fin)
        if coma != -1:
            fin = coma
        b = tramo[i:fin]
        pal = RCMP._palabras(b)
        if len(pal) > RCMP.BASE_MAX_PALABRAS:
            b = b[:pal[RCMP.BASE_MAX_PALABRAS - 1].end()]
        base = RCMP._RE_COLA.sub("", " ".join(b.split())).strip() or None
    el = {"tramo": tramo, "comparacion": comparacion, "base": base, "regla_comparacion": f"limite_relativo:{regla}",
          "origen": "e1", "tramo_verificado": nivel}
    return M.ElementoUmbral.model_validate(el).model_dump(mode="json", exclude_defaults=True)


def numero_desde_codigo(codigo: Any, label: Any) -> Optional[int]:
    """Decisión 16: el número de una Comunicación A, B o C, desde `codigo` (o el label), con la regla de
    `derivar_comunicacion`."""
    for s in (codigo, label):
        if isinstance(s, str):
            m = _RE_COM.match(fold(s))
            if m:
                return int(m.group(2).replace(".", ""))
    return None


# ------------------------------------------------------------------------- #
# Pasos de la política                                                        #
# ------------------------------------------------------------------------- #
_FOLD_TIPOS = {fold(t): t for t in M.TIPOS_ENTIDAD}
_CAMEL = re.compile(r"(?<=[a-z0-9])([A-Z])")


def resolver_tipo(v: Any, pol: Politica) -> tuple[Optional[str], str]:
    if not isinstance(v, str):
        return None, "rechazado"
    for paso in pol.pasos("tipo_entidad"):
        if paso == "en_lista" and v in M.TIPOS_ENTIDAD:
            return v, "en_lista"
        if paso == "forma":
            f = _FOLD_TIPOS.get(fold(v.strip()))
            if f is not None:
                return f, "normalizado_forma"
        if paso == "alias":
            a = pol.alias_tipo.get(v.strip())
            if a is not None:
                return a, "normalizado_alias"
    return None, "rechazado"


def _forma_predicado(v: str) -> str:
    s = re.sub(r"\s+", "", v)
    s = _CAMEL.sub(r"_\1", s)
    return fold(s)


def resolver_predicado(v: Any, pol: Politica) -> tuple[Optional[str], str]:
    if not isinstance(v, str):
        return None, "rechazado"
    for paso in pol.pasos("predicado"):
        if paso == "en_lista" and v in M.PREDICADOS:
            return v, "en_lista"
        if paso == "forma":
            f = _forma_predicado(v)
            if f in M.PREDICADOS:
                return f, "normalizado_forma"
        if paso == "alias":
            for cand in (v.strip(), _forma_predicado(v)):
                a = pol.alias_pred.get(cand)
                if a is not None:
                    return a, "normalizado_alias"
    return None, "rechazado"


_RE_COM = re.compile(
    r"^\s*(?:com(?:unicacion)?\.?\s*)?[\"'“”«»]?\s*([abc])\s*[\"'“”«»]?\s*(?:-|–|\s)\s*(?:n[°ºo]\.?\s*)?(\d[\d.]*)\s*$")


def derivar_comunicacion(codigo: Any, label: Any) -> Optional[str]:
    for s in (codigo, label):
        if isinstance(s, str):
            m = _RE_COM.match(fold(s))
            if m:
                return m.group(1).upper()
    return None


def nombra_norma_externa(s: Any, lexico: frozenset) -> bool:
    return isinstance(s, str) and any(t in lexico for t in norm_tokens(s))


# U-OMISIONES-COD, grupo H: con la forma r2, si el tramo verificado no da el tipo (sin tramo, tramo no verificado o
# tramo sin norma), el tipo se deriva del código o de la etiqueta que escribió el modelo: A, B o C con
# `derivar_comunicacion`; «externa» con el léxico de la política más LEXICO_EXTERNA_CODIGO (abreviaturas y normas que
# el léxico de la política no cubre; la lista vive acá porque `politica_campos_r2.json` está sellada por su sha). Lo
# que tampoco se deriva así lleva la marca `tipo_no_derivable` en `properties_no_definidas`. El tramo sigue primero.
LEXICO_EXTERNA_CODIGO = frozenset(("dec", "codigo", "decision", "disposicion"))


# P3b, l: la mención de una Comunicación en el tramo, también en una enumeración («A 5867, 5926 y 5970»); la regla
# medida en p3b/comunicacion_p3b.py.
_RE_COM_EN_TRAMO = re.compile(r"\bcom(?:unicacion(?:es)?)?\b\.?\s*[\"'“”«»]?\s*([abc])\s*[\"'“”«»]?\s*(?:-|–|\s)\s*"
                              r"(?:n[°ºo]\.?\s*)?(\d[\d.]*(?:\s*(?:,|y|e)\s*\d[\d.]*)*)")


def derivar_comunicacion_tramo(tramo: Any, chunk: dict, holgura: Optional[int],
                               lexico: frozenset) -> tuple[Optional[str], list[int], str]:
    """P3b, l: (tipo, números mencionados, motivo) desde el tramo de la entidad, solo si verificó contra el texto de
    la unidad (cada segmento, si es de dos); con «tokens», sobre el literal del texto. Motivos: «sin_tramo»,
    «tramo_no_verificado», «comunicacion_en_tramo», «norma_externa_en_tramo» o «tramo_sin_norma»."""
    t = _str_o_none(tramo)
    if t is None:
        return None, [], "sin_tramo"
    textos = []
    for parte in _RE_SEPARADOR_TRAMO.split(t):
        nivel, literal = verificar_tramo(parte, texto_completo(chunk), holgura)
        if nivel == "no":
            return None, [], "tramo_no_verificado"
        textos.append(literal if nivel == "tokens" and literal is not None else parte)
    texto = "\n".join(textos)
    m = _RE_COM_EN_TRAMO.search(fold(texto))
    if m:
        return m.group(1).upper(), [int(x.replace(".", "")) for x in re.findall(r"\d[\d.]*", m.group(2))
                                    if x.replace(".", "")], "comunicacion_en_tramo"
    if nombra_norma_externa(texto, lexico):
        return "externa", [], "norma_externa_en_tramo"
    return None, [], "tramo_sin_norma"


# P3b, la modalidad copiada (diseño de P3b-1, §7): lista cerrada de formas, por prefijo de token de R-NORM o por
# par de tokens. Una forma nueva se agrega acá y se vuelve a aplicar sobre lo extraído, sin cambiar el prefijo.
MODALIDAD_FORMAS = {
    "recomendacion": {"prefijos": ("recomend", "recomi", "aconsej", "sugier", "suger", "convenien", "deseabl",
                                   "procur", "propend", "esperabl"),
                      "pares": (("buena", "practica"), ("buenas", "practicas"), ("se", "espera"))},
    "consecuencia_de_incumplimiento": {"prefijos": ("sancion", "multa", "cargo", "debit", "penal", "punitori",
                                                    "incumpl", "inobserv", "infraccion", "suspen", "revoc",
                                                    "inhabilit", "apercib", "baja"),
                                       "pares": (("dara", "lugar"), ("daran", "lugar"))},
}
CLAVE_MODALIDAD = {"modalidad": "recomendacion", "consecuencia": "consecuencia_de_incumplimiento"}


def clasificar_modalidad(clave: str, tramo: Any) -> str:
    """P3b: la clase del tramo copiado en `otras_propiedades.<clave>` (modalidad → recomendacion; consecuencia →
    consecuencia_de_incumplimiento) si tiene una forma de su lista; si no, «no_clasificada»."""
    clase = CLAVE_MODALIDAD[clave]
    if not isinstance(tramo, str):
        return "no_clasificada"
    toks = norm_tokens(tramo)
    formas = MODALIDAD_FORMAS[clase]
    if any(t.startswith(formas["prefijos"]) for t in toks) or any(
            tuple(toks[i:i + 2]) in formas["pares"] for i in range(len(toks) - 1)):
        return clase
    return "no_clasificada"


_FRECUENCIA_TOKENS = {}
for _base, _formas in (("diaria", ("diaria", "diario", "diarias", "diarios", "diariamente")),
                       ("semanal", ("semanal", "semanales", "semanalmente")),
                       ("mensual", ("mensual", "mensuales", "mensualmente")),
                       ("trimestral", ("trimestral", "trimestrales", "trimestralmente")),
                       ("semestral", ("semestral", "semestrales", "semestralmente")),
                       ("anual", ("anual", "anuales", "anualmente"))):
    for _f in _formas:
        _FRECUENCIA_TOKENS[_f] = _base


def frecuencia_desde_tramo(v: str) -> Optional[str]:
    hallados = {_FRECUENCIA_TOKENS[t] for t in norm_tokens(v) if t in _FRECUENCIA_TOKENS}
    return hallados.pop() if len(hallados) == 1 else None


def lista_json(s: str):
    """Lista decodificada si el string tiene forma de lista JSON; si no, None
    (calibración P3, decisión 8: como entities y relations)."""
    t = s.strip()
    if not (t.startswith("[") and t.endswith("]")):
        return None
    try:
        v = json.loads(t)
    except json.JSONDecodeError:
        return None
    return v if isinstance(v, list) else None


# ------------------------------------------------------------------------- #
# Adaptador del crudo v3                                                      #
# ------------------------------------------------------------------------- #
def desde_v3(tool_input: Any) -> tuple[Any, Counter]:
    """Input de un tool call v3 (o de desarrollo) leído en la forma r2. No muta
    el original. `sujeto_propuesto` pasa a `sujeto_mencion`; las cadenas de
    `omisiones_no_prosa` pasan a `omisiones` como omisiones sin categoría ni
    tramo, con la cadena como nota (P-a10 para la forma string)."""
    c: Counter = Counter()
    ti = tool_input
    if isinstance(ti, str):
        try:
            ti = json.loads(ti)
        except json.JSONDecodeError:
            return tool_input, c
    if not isinstance(ti, dict):
        return ti, c
    ti = copy.deepcopy(ti)
    rels = ti.get("relations")
    if isinstance(rels, str):
        try:
            rels = json.loads(rels)
            c["relations_como_string_json"] += 1
        except json.JSONDecodeError:
            pass
    if isinstance(rels, list):
        nuevas = []
        for r in rels:
            if isinstance(r, dict) and "sujeto_propuesto" in r:
                r = dict(r)
                if "sujeto_mencion" in r:
                    c["sujeto_mencion_y_propuesto"] += 1
                    r.setdefault("_campos_v3", {})["sujeto_propuesto"] = r.pop("sujeto_propuesto")
                else:
                    r["sujeto_mencion"] = r.pop("sujeto_propuesto")
                    c["sujeto_propuesto_como_mencion"] += 1
            nuevas.append(r)
        ti["relations"] = nuevas
    om = ti.pop("omisiones_no_prosa", None)
    items = []
    if isinstance(om, str):
        decodificada = lista_json(om) if om.strip() else None
        if decodificada is not None:
            c["omisiones_string_lista_json_decodificada"] += 1
            items = decodificada
        elif om.strip():
            c["omisiones_string_a_lista_de_uno"] += 1
            items = [om]
        else:
            c["omisiones_string_vacio"] += 1
    elif isinstance(om, list):
        items = om
    elif om is not None:
        c["omisiones_no_lista"] += 1
        items = [om]
    salida = []
    for o in items:
        if isinstance(o, str):
            if o.strip():
                salida.append({"nota": o, "_origen": "v3_omisiones_no_prosa"})
                c["omision_v3_leida"] += 1
            else:
                c["omision_v3_string_vacio"] += 1
        else:
            salida.append({"_v3_no_string": o, "_origen": "v3_omisiones_no_prosa"})
            c["omision_v3_no_string"] += 1
    if "omisiones" in ti:
        c["omisiones_r2_en_crudo_v3"] += 1
    else:
        ti["omisiones"] = salida
    return ti, c


# ------------------------------------------------------------------------- #
# Validación                                                                  #
# ------------------------------------------------------------------------- #
CAMPOS_ITEM_ENTIDAD = ("local_id", "type", "label", "punto", "properties", "umbrales",
                       "otras_propiedades")
CAMPOS_ITEM_RELACION = ("source", "target", "predicate", "punto", "sujeto_mencion", "sujeto_id",
                        "sujeto_propuesto_padre_sugerido")
# Forma r2 (decisiones 15 y 17): el tramo de evidencia de la entidad y las otras_propiedades de la relación.
CAMPOS_ITEM_ENTIDAD_R2 = CAMPOS_ITEM_ENTIDAD + ("tramo",)
CAMPOS_ITEM_RELACION_R2 = CAMPOS_ITEM_RELACION + ("otras_propiedades",)
CAMPOS_ITEM_OMISION = ("categoria", "tramo", "nota")
CAMPOS_ITEM_OMISION_R2 = CAMPOS_ITEM_OMISION + ("source", "destino")


def _dump(modelo, opcionales: tuple[str, ...]) -> dict:
    """model_dump sin los campos de la forma r2 que quedaron en su valor por defecto: con la forma v3 la salida es
    la de siempre, byte a byte."""
    d = modelo.model_dump(mode="json")
    for k in opcionales:
        if d.get(k) in (None, {}):
            d.pop(k, None)
    return d


def _str_o_none(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return None


def _coerce_lista(valor):
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except json.JSONDecodeError:
            return None
    return valor if isinstance(valor, list) else None


def _clave_valor(v: Any) -> str:
    if v is None:
        return "<ausente>"
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


_SIN = object()


class _Registro:
    def __init__(self):
        self.contadores: dict[str, Counter] = defaultdict(Counter)
        self.valores: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))

    def cuenta(self, campo: str, tratamiento: str, valor: Any = _SIN) -> None:
        self.contadores[campo][tratamiento] += 1
        if valor is not _SIN:
            self.valores[campo][_clave_valor(valor)][tratamiento] += 1

    def exportar(self) -> tuple[dict, dict]:
        cont = {k: dict(sorted(v.items())) for k, v in sorted(self.contadores.items())}
        vals = {k: {vv: dict(sorted(t.items())) for vv, t in sorted(d.items())}
                for k, d in sorted(self.valores.items())}
        return cont, vals


def _rechazo(nivel: str, motivo: str, detalle: str, elemento=None) -> dict:
    r = {"nivel": nivel, "motivo": motivo, "detalle": detalle}
    if elemento is not None:
        r["elemento"] = elemento
    return r


def validar(tool_input: Any, chunk: dict, politica: Optional[Politica] = None,
            forma: str = "r2", vistos_e3: Optional[dict] = None) -> dict:
    """Valida el input del tool call de un chunk con la política r2. `forma`
    es «r2» (salida del prompt nuevo) o «v3» (crudo guardado del perfil v3 o
    del de desarrollo, leído con `desde_v3`). `vistos_e3` (solo con «r2»):
    {"entidades": índices, "relaciones": índices} del crudo que validador_e1
    pasó a E3; lo demás no entra y queda en `no_vistos_e3`."""
    pol = politica or politica_default()
    reg = _Registro()
    if vistos_e3 is not None and forma != "r2":
        raise ValueError("vistos_e3 solo con la forma r2")
    r2 = forma == "r2"
    vistos_ent = None if vistos_e3 is None else set(vistos_e3["entidades"])
    vistos_rel = None if vistos_e3 is None else set(vistos_e3["relaciones"])
    # P3b: las marcas del ratchet de E3 (ratchet_e3.ciclo_ratchet, `marcas_e3`), si las hay.
    marcas_e3 = (vistos_e3 or {}).get("marcas") or {}
    copia_por_indice = {c.get("indice_crudo"): c.get("campos") for c in marcas_e3.get("copia_nota_e3") or []}
    res: dict[str, Any] = {
        "chunk_id": chunk["id"], "perfil": PERFIL, "forma_entrada": forma,
        "politica_sha256": pol.sha256, "entidades": [], "relaciones": [], "omisiones": [],
        "rechazos": [], "pendientes_no_mapeados": [], "advertencias": [],
        "adaptacion_v3": {}, "campos_no_definidos_salida": {},
    }
    if vistos_e3 is not None:
        res["no_vistos_e3"] = []
    if marcas_e3:
        res["marcas_e3"] = copy.deepcopy(marcas_e3)

    def fin(n_ent: int, n_rel: int) -> dict:
        cont, vals = reg.exportar()
        res["contadores"] = cont
        res["valores"] = vals
        por_motivo = Counter(r["motivo"] for r in res["rechazos"])
        res["metricas"] = {"entities_in": n_ent, "entities_out": len(res["entidades"]),
                           "relations_in": n_rel, "relations_out": len(res["relaciones"]),
                           "omisiones_out": len(res["omisiones"]),
                           "rechazos": len(res["rechazos"]),
                           "rechazos_por_motivo": dict(sorted(por_motivo.items()))}
        if vistos_e3 is not None:
            res["metricas"]["no_vistos_e3"] = len(res["no_vistos_e3"])
        return res

    if forma == "v3":
        tool_input, adapt = desde_v3(tool_input)
        res["adaptacion_v3"] = dict(sorted(adapt.items()))
    elif forma != "r2":
        raise ValueError(f"forma desconocida: {forma!r}")

    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError as e:
            res["rechazos"].append(_rechazo("chunk", "salida_no_parseable", f"JSON inválido: {e}"))
            return fin(0, 0)
    if not isinstance(tool_input, dict):
        res["rechazos"].append(_rechazo("chunk", "salida_no_dict", f"tipo {type(tool_input).__name__}"))
        return fin(0, 0)

    for k in tool_input:
        if k not in ("entities", "relations", "omisiones"):
            res["campos_no_definidos_salida"][k] = tool_input[k]
            reg.cuenta("campos_de_la_salida", "a_campos_no_definidos", k)

    entities = _coerce_lista(tool_input.get("entities"))
    relations = _coerce_lista(tool_input.get("relations"))
    if entities is None or relations is None:
        res["rechazos"].append(_rechazo("chunk", "entities_o_relations_invalidos",
                                        "entities/relations ausentes o no-lista (ni como string JSON)"))
        return fin(0, 0)
    for nombre in ("entities", "relations"):
        if isinstance(tool_input.get(nombre), str):
            reg.cuenta("estructura", f"{nombre}_como_string_json")

    admitidos = set(puntos_admitidos(chunk))
    texto_mencion = texto_completo(chunk)

    # ---------------- Entidades ----------------
    por_local: dict[str, dict] = {}
    for i, e in enumerate(entities):
        ref = f"entities[{i}]"
        if not isinstance(e, dict):
            res["rechazos"].append(_rechazo("entidad", "entidad_no_dict", ref, e))
            continue
        local_id = _str_o_none(e.get("local_id"))
        label = _str_o_none(e.get("label"))
        punto = _str_o_none(e.get("punto"))
        if local_id is None:
            res["rechazos"].append(_rechazo("entidad", "local_id_ausente", ref, e))
            continue
        if local_id in por_local:
            res["rechazos"].append(_rechazo("entidad", "local_id_duplicado", f"{ref}: '{local_id}'", e))
            continue
        tipo_crudo = e.get("type")
        tipo, trat = resolver_tipo(tipo_crudo, pol)
        reg.cuenta("tipo_entidad", trat, *(() if trat == "en_lista" else (tipo_crudo,)))
        if tipo is None:
            res["rechazos"].append(_rechazo("entidad", "type_invalido", f"{ref}: '{tipo_crudo}'", e))
            # P-e3: el tipo rechazado se registra como omisión fuera_de_tipos.
            nota = f"label: {label!r}; tipo propuesto: {tipo_crudo!r}"
            om = M.OmisionR2(categoria="fuera_de_tipos", tramo=None, nota=nota,
                             origen="validador_p_e3", tramo_verificado="ausente")
            res["omisiones"].append(_dump(om, ("source", "destino")))
            reg.cuenta("omisiones", "fuera_de_tipos_por_tipo_rechazado")
            continue
        if label is None:
            res["rechazos"].append(_rechazo("entidad", "label_vacio", ref, e))
            continue
        if punto is None:
            res["rechazos"].append(_rechazo("entidad", "punto_ausente", f"{ref} ({local_id})", e))
            continue
        if punto not in admitidos:
            res["rechazos"].append(_rechazo("entidad", "punto_fuera_de_admitidos",
                                            f"{ref} ({local_id}): '{punto}' ∉ {sorted(admitidos)}", e))
            continue

        originales: dict[str, Any] = {}
        if trat != "en_lista":
            originales["type"] = tipo_crudo
        campos_nd: dict[str, Any] = {}
        for k in e:
            if k not in (CAMPOS_ITEM_ENTIDAD_R2 if r2 else CAMPOS_ITEM_ENTIDAD):
                campos_nd[k] = e[k]
                reg.cuenta("campos_del_item_entidad", "a_campos_no_definidos", k)
        if r2 and tipo == "TextoOrdenado" and "tramo" in e:
            # Punto 1 del §10.1 del diseño: el TextoOrdenado no lleva tramo (se deriva en código).
            campos_nd["tramo"] = e["tramo"]
            reg.cuenta("campos_del_item_entidad", "tramo_en_texto_ordenado_a_campos_no_definidos")

        props_in = e.get("properties")
        if props_in is None:
            props_in = {}
        if not isinstance(props_in, dict):
            campos_nd["properties"] = props_in
            reg.cuenta("properties", "no_dict_a_campos_no_definidos")
            props_in = {}
        props: dict[str, Any] = {}
        no_def: dict[str, Any] = {}
        heredadas: dict[str, Any] = {}
        no_tipados: dict[str, Any] = {}
        fuera: list[str] = []
        definidas = M.CLAVES_R2[tipo]
        for k, v in props_in.items():
            if k in definidas and k != "umbrales":
                if v is None or (isinstance(v, str) and not v.strip()):
                    originales[k] = v
                    reg.cuenta("valores", "vacio_a_ausente", f"{tipo}.{k}")
                    continue
                if tipo == "Comunicacion" and k == "numero":
                    if isinstance(v, int) and not isinstance(v, bool):
                        props[k] = v
                    elif isinstance(v, str) and re.fullmatch(r"\s*(\d+|\d{1,3}(\.\d{3})+)\s*", v):
                        props[k] = int(v.strip().replace(".", ""))
                        originales[k] = v
                        reg.cuenta("valores", "numero_string_a_entero", f"{tipo}.{k}")
                    else:
                        no_tipados[k] = v
                        reg.cuenta("valores", "no_tipado_registrado", f"{tipo}.{k}")
                    continue
                if isinstance(v, str):
                    props[k] = v
                else:
                    no_tipados[k] = v
                    reg.cuenta("valores", "no_tipado_registrado", f"{tipo}.{k}")
            elif k in M.CLAVES_HEREDADAS_V3.get(tipo, ()):
                heredadas[k] = v
                reg.cuenta("claves", "heredada_v3", f"{tipo}.{k}")
            else:
                if k in definidas:      # «umbrales» dentro de properties: lugar equivocado
                    campos_nd[f"properties.{k}"] = v
                    reg.cuenta("claves", "umbrales_en_properties_a_campos_no_definidos", f"{tipo}.{k}")
                else:
                    no_def[k] = v
                    reg.cuenta("claves", "a_properties_no_definidas", f"{tipo}.{k}")

        # otras_propiedades (forma r2b): lo no previsto por la definición del
        # tipo va a properties_no_definidas, con contador; nunca se rechaza.
        if "otras_propiedades" in e:
            otras = e.get("otras_propiedades")
            if isinstance(otras, dict):
                for k, v in otras.items():
                    if k in definidas or k in no_def:
                        campos_nd[f"otras_propiedades.{k}"] = v
                        reg.cuenta("claves", "otras_propiedades_clave_repetida_a_campos_no_definidos",
                                   f"{tipo}.{k}")
                    else:
                        no_def[k] = v
                        reg.cuenta("claves", "otras_propiedades_a_properties_no_definidas", f"{tipo}.{k}")
                        if not isinstance(v, str):
                            reg.cuenta("valores", "otras_propiedades_valor_no_string", f"{tipo}.{k}")
            elif otras is not None:
                campos_nd["otras_propiedades"] = otras
                reg.cuenta("claves", "otras_propiedades_no_objeto_a_campos_no_definidos", tipo)
        if r2:
            # P3b: las claves que pone el código no se toman del modelo.
            for k in ("modalidad_clasificada", "copia_nota_e3", "tipo_no_derivable"):
                if k in no_def:
                    campos_nd[f"properties_no_definidas.{k}"] = no_def.pop(k)
                    reg.cuenta("claves", "clave_del_codigo_escrita_por_el_modelo_a_campos_no_definidos", k)
            # P3b, la modalidad copiada: el código la clasifica, junto al tramo.
            clases = [clasificar_modalidad(k, no_def[k]) for k in ("modalidad", "consecuencia") if k in no_def]
            if clases:
                no_def["modalidad_clasificada"] = next((c for c in clases if c != "no_clasificada"), "no_clasificada")
                reg.cuenta("modalidad_clasificada", no_def["modalidad_clasificada"], tipo)
                for k in ("modalidad", "consecuencia"):
                    if isinstance(no_def.get(k), str):
                        reg.cuenta("modalidad_tramo", verificar_tramo(no_def[k], texto_mencion, pol.holgura)[0], k)

        # Campos con lista cerrada.
        if tipo == "Obligacion":
            v = props.get("tipo")
            if v in M.OBLIGACION_TIPO:
                reg.cuenta("Obligacion.tipo", "en_lista")
            else:
                original = props_in.get("tipo")
                props["tipo"] = pol.d["campos"]["Obligacion.tipo"]["valor_normalizado"]
                originales["tipo"] = original
                no_tipados.pop("tipo", None)
                reg.cuenta("Obligacion.tipo",
                           "ausente_normalizado_a_otra" if v is None else "normalizado_a_otra", original)
        if tipo == "Restriccion":
            v = props.get("tipo")
            if v in M.RESTRICCION_TIPO:
                reg.cuenta("Restriccion.tipo", "en_lista")
            else:
                fuera.append("tipo")
                originales.setdefault("tipo", props_in.get("tipo"))
                reg.cuenta("Restriccion.tipo", "registrado_fuera_de_lista", props_in.get("tipo"))
        if tipo == "Comunicacion":
            v = props.get("tipo")
            if r2:
                # P3b, l: con la forma r2 el paso «derivar_de_codigo_o_label» de la política lee el tramo
                # verificado (texto de la unidad); el código y la etiqueta los escribe el modelo.
                der, nums_tramo, motivo_l = derivar_comunicacion_tramo(e.get("tramo"), chunk, pol.holgura,
                                                                       pol.lexico_externa)
                reg.cuenta("Comunicacion.tramo", motivo_l)
            else:
                der = derivar_comunicacion(props.get("codigo"), label)
            if v in M.COMUNICACION_TIPO:
                reg.cuenta("Comunicacion.tipo", "en_lista")
                if der is not None and v in ("A", "B", "C") and der != v:
                    reg.cuenta("Comunicacion.tipo", "en_lista_discrepa_del_codigo", v)
                    res["advertencias"].append({"tipo": "comunicacion_tipo_discrepa_codigo",
                                                "local_id": local_id,
                                                "detalle": f"tipo {v!r}, {'el tramo da' if r2 else 'código o label dan'} "
                                                           f"{der!r}"})
            else:
                original = props_in.get("tipo")
                # Decisión 16: en la forma r2 el tipo no se pide; sin valor del modelo, se deriva sin original.
                derivado = r2 and original is None and "tipo" not in no_tipados
                resuelto = None
                for paso in pol.pasos("Comunicacion.tipo"):
                    if paso == "derivar_de_codigo_o_label" and der is not None:
                        resuelto, trat_c = der, "derivado_del_tramo" if r2 else "derivado_de_codigo_o_label"
                        break
                    if paso == "externa_por_lexico":
                        if nombra_norma_externa(original, pol.lexico_externa):
                            resuelto, trat_c = "externa", "externa_por_valor"
                            break
                        if not r2 and (nombra_norma_externa(props.get("codigo"), pol.lexico_externa)
                                       or nombra_norma_externa(label, pol.lexico_externa)):
                            resuelto, trat_c = "externa", "externa_por_codigo_o_label"
                            break
                if r2 and resuelto is None and derivado:
                    der_c = derivar_comunicacion(props.get("codigo"), label)
                    lex = pol.lexico_externa | LEXICO_EXTERNA_CODIGO
                    if der_c is not None:
                        resuelto, trat_c = der_c, "derivado_del_codigo_sin_tramo"
                    elif nombra_norma_externa(props.get("codigo"), lex) or nombra_norma_externa(label, lex):
                        resuelto, trat_c = "externa", "externa_por_codigo_sin_tramo"
                    else:
                        no_def["tipo_no_derivable"] = True
                        reg.cuenta("Comunicacion.tipo", "tipo_no_derivable")
                if not derivado:
                    originales.setdefault("tipo", original)
                if resuelto is not None:
                    props["tipo"] = resuelto
                    reg.cuenta("Comunicacion.tipo", f"{trat_c}{':sin_valor_del_modelo' if derivado else ''}",
                               original)
                elif derivado:
                    reg.cuenta("Comunicacion.tipo", "sin_valor_del_modelo_no_derivado")
                else:
                    fuera.append("tipo")
                    reg.cuenta("Comunicacion.tipo", "registrado_fuera_de_lista", original)
            if r2 and "numero" not in props and "numero" not in no_tipados and props.get("tipo") in ("A", "B", "C"):
                num = numero_desde_codigo(props.get("codigo"), label)
                if num is not None:
                    props["numero"] = num
                    reg.cuenta("Comunicacion.numero", "derivado_de_codigo_o_label")
                else:
                    reg.cuenta("Comunicacion.numero", "sin_valor_del_modelo_no_derivado")
            if r2 and nums_tramo and props.get("tipo") in ("A", "B", "C"):
                # P3b, l: el número del tramo se controla contra el del código (o el de la etiqueta).
                num_c = props.get("numero") if isinstance(props.get("numero"), int) else numero_desde_codigo(
                    props.get("codigo"), label)
                reg.cuenta("Comunicacion.numero", "sin_numero_para_controlar" if num_c is None
                           else "tramo_coincide" if num_c in nums_tramo else "tramo_no_coincide")
        if tipo == "Obligacion" and ("frecuencia" in props or "frecuencia" in originales
                                     or "frecuencia" in no_tipados):
            v = props.get("frecuencia")
            if "frecuencia" in no_tipados:
                reg.cuenta("Obligacion.frecuencia", "no_tipado_registrado", no_tipados["frecuencia"])
            elif v is None:
                reg.cuenta("Obligacion.frecuencia", "vacio_a_ausente")
            elif v in M.FRECUENCIA:
                reg.cuenta("Obligacion.frecuencia", "en_lista")
            else:
                f = frecuencia_desde_tramo(v)
                originales["frecuencia"] = v
                if f is not None:
                    props["frecuencia"] = f
                    reg.cuenta("Obligacion.frecuencia", "normalizado_desde_tramo", v)
                else:
                    fuera.append("frecuencia")
                    reg.cuenta("Obligacion.frecuencia", "registrado_fuera_de_lista", v)

        # Umbrales del ítem (forma r2b): tramos literales.
        tramos: list[str] = []
        if "umbrales" in e:
            u = e.get("umbrales")
            if tipo not in M.TIPOS_CON_UMBRALES:
                campos_nd["umbrales"] = u
                reg.cuenta("umbrales", "tipo_sin_umbrales_a_campos_no_definidos", tipo)
            elif isinstance(u, list):
                invalidos = []
                for x in u:
                    t = _str_o_none(x.get("tramo")) if isinstance(x, dict) else None
                    if t is not None and set(x) == {"tramo"}:
                        tramos.append(x["tramo"])
                        reg.cuenta("umbrales", "tramo")
                    else:
                        invalidos.append(x)
                        reg.cuenta("umbrales", "item_invalido_a_campos_no_definidos")
                if invalidos:
                    campos_nd["umbrales_invalidos"] = invalidos
            elif u is not None:
                campos_nd["umbrales"] = u
                reg.cuenta("umbrales", "no_lista_a_campos_no_definidos")

        if vistos_ent is not None and i not in vistos_ent:
            # Nota del 04/10/2026, punto b: lo que E3 no vio no entra.
            res["no_vistos_e3"].append({"elemento": ref, "local_id": local_id, "type": tipo})
            reg.cuenta("paso_por_e3", "entidad_no_vista_excluida")
            continue
        if i in copia_por_indice and copia_por_indice[i]:
            # P3b, defensa 2: la marca del ratchet llega a la entidad (y, por e2_lib, al nodo).
            no_def["copia_nota_e3"] = copia_por_indice[i]
            reg.cuenta("marcas_e3", "copia_nota_e3", tipo)
        evidencia: dict[str, Any] = {}
        if r2:
            # Decisión 21: el tramo sin cuantía es un límite relativo y el elemento sin valor se arma acá. Los
            # tramos con cuantía los arma el ensamblado (par A); el tramo relativo queda también en
            # umbrales_tramos, para que el ensamblado no caiga a la descripción como fuente.
            relativos = []
            for t in tramos:
                el = elemento_umbral_relativo(t, verificar_tramo(t, texto_mencion, pol.holgura)[0])
                if el is not None:
                    relativos.append(el)
                    reg.cuenta("umbrales", "limite_relativo_sin_valor")
            if relativos:
                props["umbrales"] = relativos
                if len(relativos) < len(tramos):
                    # Límite declarado: llenar_umbrales_r2 (ensamblar_tanda0.py) reemplaza la lista cuando arma
                    # elementos con cuantía, y el elemento relativo de esta entidad no llega al nodo.
                    reg.cuenta("umbrales", "limite_relativo_con_cuantias_en_la_entidad")
            # Decisiones 15 y 16: el tramo de evidencia y el término literal, verificados, en la procedencia.
            if tipo != "TextoOrdenado":
                t = _str_o_none(e.get("tramo"))
                if t is None:
                    if e.get("tramo") is not None:
                        campos_nd["tramo"] = e.get("tramo")
                    evidencia = {"tramo_verificado": "ausente"}
                    reg.cuenta("tramo_entidad", "ausente")
                else:
                    guardado, nivel, modelo = verificar_tramo_entidad(t, chunk, punto, pol.holgura, reg)
                    evidencia = {"tramo": guardado, "tramo_verificado": nivel}
                    if modelo is not None:
                        evidencia["tramo_modelo"] = modelo
            if tipo == "Definicion":
                termino = props.get("termino")
                nivel_t = "ausente" if termino is None else verificar_tramo(termino, texto_mencion, pol.holgura)[0]
                evidencia["termino_verificado"] = nivel_t
                reg.cuenta("termino", nivel_t)

        ent = M.EntidadR2(
            local_id=local_id, type=tipo, label=label, punto=punto,
            provenance=M.Provenance(to=chunk["to"], archivo=chunk["archivo"], punto=punto,
                                    rol_documental=rol_documental_de_punto(chunk, punto), **evidencia),
            properties=props, umbrales_tramos=tramos, fuera_de_lista=fuera, originales=originales,
            properties_no_definidas=no_def, campos_heredados_v3=heredadas,
            valores_no_tipados=no_tipados, campos_no_definidos=campos_nd,
            paso_por_e3=None if vistos_ent is None else True)
        d = _dump(ent, ("paso_por_e3",))
        por_local[local_id] = d
        res["entidades"].append(d)
        if len(label.split()) > 12:
            res["advertencias"].append({"tipo": "label_largo", "local_id": local_id,
                                        "detalle": f"{len(label.split())} palabras"})

    # ---------------- Relaciones ----------------
    for i, r in enumerate(relations):
        ref = f"relations[{i}]"
        if not isinstance(r, dict):
            res["rechazos"].append(_rechazo("relacion", "relacion_no_dict", ref, r))
            continue
        pred_crudo = r.get("predicate")
        pred, trat = resolver_predicado(pred_crudo, pol)
        reg.cuenta("predicado", trat, *(() if trat == "en_lista" else (pred_crudo,)))
        if pred is None:
            res["rechazos"].append(_rechazo("relacion", "predicado_invalido", f"{ref}: '{pred_crudo}'", r))
            continue
        punto = _str_o_none(r.get("punto"))
        if punto is None:
            res["rechazos"].append(_rechazo("relacion", "punto_ausente", f"{ref} ({pred})", r))
            continue
        if punto not in admitidos:
            res["rechazos"].append(_rechazo("relacion", "punto_fuera_de_admitidos",
                                            f"{ref} ({pred}): '{punto}' ∉ {sorted(admitidos)}", r))
            continue
        originales = {} if trat == "en_lista" else {"predicate": pred_crudo}
        campos_nd = {}
        for k in r:
            if k not in (CAMPOS_ITEM_RELACION_R2 if r2 else CAMPOS_ITEM_RELACION):
                campos_nd[k] = r[k]
                reg.cuenta("campos_del_item_relacion", "a_campos_no_definidos", k)
        props_nd: dict[str, Any] = {}
        if r2 and "otras_propiedades" in r:
            # Decisión 17: a la arista como no definidas, como properties_no_definidas en el nodo.
            otras = r.get("otras_propiedades")
            if isinstance(otras, dict):
                props_nd = dict(otras)
                for k, v in otras.items():
                    reg.cuenta("claves_relacion", "otras_propiedades_a_properties_no_definidas", f"{pred_crudo}.{k}")
                    if not isinstance(v, str):
                        reg.cuenta("valores_relacion", "otras_propiedades_valor_no_string", f"{pred_crudo}.{k}")
            elif otras is not None:
                campos_nd["otras_propiedades"] = otras
                reg.cuenta("claves_relacion", "otras_propiedades_no_objeto_a_campos_no_definidos", pred_crudo)
        source = _str_o_none(r.get("source"))
        target = _str_o_none(r.get("target"))
        sujeto_id = _str_o_none(r.get("sujeto_id"))
        mencion = _str_o_none(r.get("sujeto_mencion"))
        padre = _str_o_none(r.get("sujeto_propuesto_padre_sugerido"))
        extra: dict[str, Any] = {}
        pendiente = None

        if pred in M.PREDICADOS_SUJETO:
            ignorado = "target" if pred == "aplica_a" else "source"
            if (target if pred == "aplica_a" else source) is not None:
                campos_nd[f"{ignorado}_ignorado"] = r.get(ignorado)
                reg.cuenta("campos_del_item_relacion", "extremo_sujeto_ignorado", ignorado)
            if pred == "aplica_a":
                target = None
            else:
                source = None
            if sujeto_id is None and mencion is None:
                res["rechazos"].append(_rechazo("relacion", "sujeto_extremo_ausente",
                                                f"{ref} ({pred}): sin sujeto_id ni mención", r))
                reg.cuenta("sujeto", "rechazada_sin_sujeto_id_ni_mencion")
                continue
            padre_descartado = None
            if padre is not None and mencion is None:
                # Decisión de la autora sobre P1: la relación se acepta con su
                # sujeto_id y el padre se descarta, con contador y original.
                padre_descartado, padre = padre, None
                reg.cuenta("padre_sugerido", "sin_mencion_descartado", padre_descartado)
            extremo = source if pred == "aplica_a" else target
            campo = "source" if pred == "aplica_a" else "target"
            if extremo is None:
                res["rechazos"].append(_rechazo("relacion", "extremo_chunk_ausente",
                                                f"{ref} ({pred}): falta {campo}", r))
                continue
            ent = por_local.get(extremo)
            if ent is None:
                res["rechazos"].append(_rechazo("relacion", "ref_colgante",
                                                f"{ref} ({pred}): {campo}='{extremo}'", r))
                continue
            src_t, tgt_t = ((ent["type"], M.TIPO_SUJETO) if pred == "aplica_a"
                            else (M.TIPO_SUJETO, ent["type"]))
            if not M.firma_r2(src_t, pred, tgt_t):
                res["rechazos"].append(_rechazo("relacion", "firma_invalida",
                                                f"{ref}: {src_t} --{pred}--> {tgt_t}", r))
                continue
            sid_modelo = None
            if sujeto_id is not None:
                if sujeto_id in M.SUJETOS_R2_SET:
                    sid_modelo = sujeto_id
                    reg.cuenta("sujeto_id", "en_catalogo")
                else:
                    originales["sujeto_id"] = sujeto_id
                    reg.cuenta("sujeto_id", "fuera_de_catalogo_a_no_mapeados", sujeto_id)
            if sujeto_id is not None and mencion is not None:
                reg.cuenta("sujeto", "ambos_campos")
            pad_ok = None
            pad_crudo = padre_descartado
            if padre is not None:
                if padre in M.SUJETOS_R2_SET:
                    pad_ok = padre
                    reg.cuenta("padre_sugerido", "en_catalogo")
                else:
                    pad_crudo = padre
                    reg.cuenta("padre_sugerido", "fuera_de_catalogo_anulado", padre)
            if mencion is None:
                nivel, literal = "ausente", None
            else:
                nivel, literal = verificar_tramo(mencion, texto_mencion, pol.holgura, contracciones=True)
            reg.cuenta("sujeto_mencion", nivel)
            mencion_final, mencion_modelo = mencion, None
            if nivel == "tokens" and literal is not None:
                mencion_final, mencion_modelo = literal, mencion
            extra = dict(sujeto_mencion=mencion_final, sujeto_mencion_modelo=mencion_modelo,
                         mencion_verificada=nivel, sujeto_id_modelo=sid_modelo,
                         padre_sugerido=pad_ok, padre_sugerido_crudo=pad_crudo)
            motivo = None
            if sujeto_id is not None and sid_modelo is None:
                motivo = "id_fuera_de_catalogo"
            elif nivel == "no" and sid_modelo is None:
                motivo = "mencion_no_verificada"
            if motivo:
                pendiente = {
                    "chunk_id": chunk["id"], "indice_relacion": i, "punto": punto, "predicado": pred,
                    "extremo_local_id": extremo, "extremo_tipo": ent["type"], "mencion": mencion,
                    "mencion_verificada": nivel, "sujeto_id_crudo": sujeto_id,
                    "padre_sugerido_crudo": padre, "motivo": motivo}
        else:
            if sujeto_id or mencion or padre:
                res["rechazos"].append(_rechazo("relacion", "sujeto_en_predicado_no_sujeto",
                                                f"{ref}: sujeto_* solo vale en {M.PREDICADOS_SUJETO}", r))
                continue
            if source is None or target is None:
                res["rechazos"].append(_rechazo("relacion", "extremo_chunk_ausente",
                                                f"{ref} ({pred}): requiere source y target", r))
                continue
            se, te = por_local.get(source), por_local.get(target)
            if se is None or te is None:
                res["rechazos"].append(_rechazo("relacion", "ref_colgante",
                                                f"{ref} ({pred}): source='{source}' target='{target}'", r))
                continue
            src_t, tgt_t = se["type"], te["type"]
            if not M.firma_r2(src_t, pred, tgt_t):
                res["rechazos"].append(_rechazo("relacion", "firma_invalida",
                                                f"{ref}: {src_t} --{pred}--> {tgt_t}", r))
                continue
            if pred in ("prohibe", "limita"):
                rt = se["properties"].get("tipo")
                if rt == "prohibicion" or (isinstance(rt, str) and rt.startswith("limite_")):
                    esperado = "prohibe" if rt == "prohibicion" else "limita"
                    coh = "coherente" if esperado == pred else "incoherente"
                else:
                    coh = "no_evaluable"
                extra["coherencia_tipo_predicado"] = coh
                reg.cuenta("coherencia_tipo_predicado", f"{pred}:{coh}", f"{rt}→{pred}")
                if coh == "incoherente":
                    res["advertencias"].append({"tipo": "bkl_0038_incoherencia_tipo_predicado",
                                                "detalle": f"{ref}: Restriccion.tipo {rt!r} con {pred}"})

        if vistos_rel is not None and i not in vistos_rel:
            # Nota del 04/10/2026, punto b: lo que E3 no vio no entra (ni al registro de no mapeados).
            res["no_vistos_e3"].append({"elemento": ref, "predicate": pred, "source": source, "target": target})
            reg.cuenta("paso_por_e3", "relacion_no_vista_excluida")
            continue
        if pendiente is not None:
            res["pendientes_no_mapeados"].append(pendiente)
            reg.cuenta("no_mapeados_pendientes", pendiente["motivo"])
        nueva = not M.firma_congelada(src_t, pred, tgt_t)
        if nueva:
            reg.cuenta("firma", f"nueva_r2:{src_t}-{pred}-{tgt_t}")
        else:
            reg.cuenta("firma", "congelada")
        # La marca: en la forma v3, por la firma; con vistos_e3, por lo que pasó por E3 (nota del 04/10/2026,
        # punto c): todo lo que entra pasó, y la marca queda como red de seguridad del modelo.
        paso = None if vistos_rel is None else True
        rel = M.RelacionR2(
            source=source, target=target, predicate=pred, punto=punto,
            provenance=M.Provenance(to=chunk["to"], archivo=chunk["archivo"], punto=punto,
                                    rol_documental=rol_documental_de_punto(chunk, punto)),
            tipo_source=src_t, tipo_target=tgt_t, no_verificada_e3=nueva if paso is None else not paso,
            indice_crudo=i, originales=originales, campos_no_definidos=campos_nd,
            properties_no_definidas=props_nd, paso_por_e3=paso, **extra)
        res["relaciones"].append(_dump(rel, ("properties_no_definidas", "paso_por_e3")))

    # ---------------- Omisiones ----------------
    oms = tool_input.get("omisiones")
    if isinstance(oms, str):
        decodificada = lista_json(oms) if oms.strip() else None
        if decodificada is not None:
            reg.cuenta("omisiones", "string_lista_json_decodificada")
            oms = decodificada
        elif oms.strip():
            reg.cuenta("omisiones", "string_a_lista_de_uno")
            oms = [oms]
        else:
            reg.cuenta("omisiones", "string_vacio_a_ausente")
            oms = []
    elif oms is None:
        oms = []
    elif not isinstance(oms, list):
        res["rechazos"].append(_rechazo("omision", "omisiones_no_lista", "omisiones", oms))
        oms = []
    flags = chunk.get("flags") or {}
    for j, o in enumerate(oms):
        origen = "e1"
        if isinstance(o, dict) and o.get("_origen") == "v3_omisiones_no_prosa":
            origen = "v3_omisiones_no_prosa"
            if "_v3_no_string" in o:
                res["rechazos"].append(_rechazo("omision", "omision_v3_no_string", f"omisiones[{j}]",
                                                o["_v3_no_string"]))
                continue
            om = M.OmisionR2(categoria=None, tramo=None, nota=o["nota"], origen=origen,
                             tramo_verificado="ausente")
            res["omisiones"].append(_dump(om, ("source", "destino")))
            reg.cuenta("omisiones", "v3_sin_categoria_ni_tramo")
            continue
        if isinstance(o, str):
            if not o.strip():
                reg.cuenta("omisiones", "item_string_vacio_a_ausente")
                continue
            o = {"nota": o}
            reg.cuenta("omisiones", "item_string_a_nota")
        if not isinstance(o, dict):
            res["rechazos"].append(_rechazo("omision", "omision_no_objeto", f"omisiones[{j}]", o))
            continue
        fuera, originales, campos_nd = [], {}, {}
        for k in o:
            if k not in (CAMPOS_ITEM_OMISION_R2 if r2 else CAMPOS_ITEM_OMISION):
                campos_nd[k] = o[k]
        cat = _str_o_none(o.get("categoria"))
        extremos: dict[str, Optional[str]] = {}
        if r2:
            # Decisión 17: source y destino, los local_id de la relación que el esquema no representa.
            for campo in ("source", "destino"):
                x = _str_o_none(o.get(campo))
                if x is None:
                    if o.get(campo) is not None:
                        campos_nd[campo] = o.get(campo)
                    continue
                if cat != "relacion_sin_predicado":
                    campos_nd[campo] = o.get(campo)
                    reg.cuenta("omisiones", f"{campo}_fuera_de_relacion_sin_predicado")
                    continue
                extremos[campo] = x
                reg.cuenta("omisiones", f"relacion_sin_predicado.{campo}:"
                                        + ("entidad_aceptada" if x in por_local else "sin_entidad_aceptada"))
            if cat in ("fuera_de_tipos", "relacion_sin_predicado"):
                # La instrucción pide en `nota` el tipo o el predicado que se habría usado.
                reg.cuenta("omisiones", f"{cat}.{'con' if _str_o_none(o.get('nota')) else 'sin'}_nota")
        if cat is None or cat not in M.CATEGORIA_OMISION:
            fuera.append("categoria")
            originales["categoria"] = o.get("categoria")
            reg.cuenta("omisiones", "categoria_registrada_fuera_de_lista", o.get("categoria"))
        else:
            reg.cuenta("omisiones", f"categoria:{cat}")
        tramo = _str_o_none(o.get("tramo"))
        tramo_modelo, corto = None, False
        if tramo is not None and cat == "meta_normativo":
            clases = marcas_meta_normativo(tramo)
            if clases:
                reg.cuenta("omisiones", "meta_normativo_con_marca")
                for clase in clases:
                    reg.cuenta("omisiones", f"meta_normativo_con_marca:{clase}")
                if "modalidad" in clases:
                    for sub in subclases_modalidad(tramo):
                        reg.cuenta("omisiones", f"meta_normativo_con_marca:modalidad.{sub}")
        if tramo is None:
            nivel = "ausente"
        else:
            nivel, literal = verificar_tramo_omision(tramo, chunk, pol.holgura, reg)
            if nivel == "tokens" and literal is not None:
                tramo, tramo_modelo = literal, o.get("tramo")
            corto = len(norm_tokens(tramo)) < pol.largo_min_omision
            if corto:
                reg.cuenta("omisiones", "tramo_corto")
        reg.cuenta("omisiones", f"tramo:{nivel}")
        senal = ((cat == "tabla" and not flags.get("contenido_tabular"))
                 or (cat == "formula" and not flags.get("formula")))
        if senal:
            reg.cuenta("omisiones", "senal_tabla_no_detectada")
        nota = o.get("nota") if isinstance(o.get("nota"), str) else None
        if o.get("nota") is not None and nota is None:
            campos_nd["nota"] = o.get("nota")
        om = M.OmisionR2(categoria=cat, tramo=tramo, nota=nota, origen=origen,
                         tramo_verificado=nivel, tramo_modelo=tramo_modelo, tramo_corto=corto,
                         senal_tabla_no_detectada=senal, fuera_de_lista=fuera, originales=originales,
                         campos_no_definidos=campos_nd, **extremos)
        res["omisiones"].append(_dump(om, ("source", "destino")))

    if chunk_flaggeado(chunk):
        extrajo = any(x["type"] != "TextoOrdenado" for x in res["entidades"])
        con_omision = any(x["origen"] != "validador_p_e3" for x in res["omisiones"])
        if extrajo and not con_omision:
            reg.cuenta("chunk_marcado", "con_extraccion_sin_omision")
            res["advertencias"].append({"tipo": "flag_sin_omisiones_declaradas",
                                        "detalle": "chunk marcado por E0 con extracción y sin omisiones"})
        elif not extrajo and not con_omision:
            reg.cuenta("chunk_marcado", "sin_extraccion_sin_omision")

    return fin(len(entities), len(relations))
