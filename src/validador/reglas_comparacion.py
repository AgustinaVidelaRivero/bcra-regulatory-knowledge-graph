"""
reglas_comparacion.py — U-PYD: reglas en código que fijan `comparacion` de un
elemento de umbral a partir de su tramo (L-ESQ-R2, versión firmada en 4ef7650,
§1.3, punto 3), más la detección de la cuantía (valor, unidad) y de la base.

El laudo fija el SENTIDO de cada forma; este módulo es la implementación.
Precedencia (§1.3.3, con la enmienda 5 a L-ESQ-R2): coeficiente, salvo que un
comparador esté pegado a la cuantía → negación → compuestas (con la adyacencia
de «mínimo»/«máximo») → simples → igual → sin marcador.

  - Coeficiente: «pondera…», «ponderador», «ponderación», «coeficiente»,
    «factor». Es el único marcador que puede venir también de la descripción
    o del título del punto; «factor», solo del tramo o del título
    (calibración P3, decisión 4).
  - Simples: mínimo estricto = las raíces «super-» y «exced-» (toda forma,
    salvo «superintend-», «supervis-», «superfic-», «superávit» y
    «excedente»; «superior(es)» cuenta con o sin «a»), «más de», «mayor(es)
    a»; máximo estricto = «inferior(es) a», «menos de», «menor(es) a».
    «Más del» y «menos del» valen como «más de» y «menos de» (enmienda 5 a
    L-ESQ-R2, punto 3.b).
    «Mayor», «menor» e «inferior» cuentan solo seguidos de «a» o de «al»
    (notas del 01/10 a L-ESQ-R2 §1.3; calibración P3, decisiones 1 y 3).
  - Negación general: «no» o «sin» delante de una simple, con cero a tres
    palabras en el medio, invierte el sentido (¬ mínimo estricto = máximo
    inclusivo; ¬ máximo estricto = mínimo inclusivo). DECLARADO: la misma
    inversión se aplica a los comparativos compuestos «igual o superior/
    mayor/inferior/menor» y «menor/inferior/mayor/superior o igual»
    (¬ mínimo inclusivo = máximo estricto y viceversa). Alcance de la
    negación (enmienda 5 a L-ESQ-R2, punto 1; C2 de U-R2-CODIGO-2, punto i):
    «ningún»/«ninguna» también niegan; la negación de un verbo («no» con una
    forma de haber, poder o deber, AUXILIARES_NEGADOS; «sin» con un
    infinitivo; «ningún»/«ninguna» siempre) alcanza al marcador más allá de
    las tres palabras mientras no medie, dentro de la cláusula, una coma,
    otra forma de comparación o una palabra de NEGACION_BARRERAS («no ha
    utilizado este mecanismo por un monto superior a…», «sin haber incurrido
    en atrasos superiores a…»); un «no» que no niega un verbo («sector
    privado no financiero») no alcanza más allá de las tres palabras; y «o
    no» («sea o no», «represente o no», también entre comas) no es una
    negación, a ninguna distancia (`_no_de_o_no`).
  - Compuestas: «igual o superior/mayor», «mayor/superior o igual», «al
    menos», «por lo menos», «como mínimo», «un mínimo de» → mínimo
    inclusivo; «igual o inferior/menor», «menor/inferior o igual», «como
    máximo», «hasta», «dentro de» → máximo inclusivo. «Igual o superior» vale
    también con «equivalente(s)» y con las formas verbales («igualen o
    superen», «iguale o exceda»); lo mismo hacia abajo (enmienda 5 a
    L-ESQ-R2, punto 3.a). «Mínimo»/«máximo» en cualquier género y número
    seguidos inmediatamente de la cuantía, con o sin «de» (o «del»), tienen
    el mismo nivel. «Como máximo», «como mínimo»,
    «al menos» y «por lo menos» valen también pospuestos a la cuantía; «o
    más» y «o menos», solo pospuestos y pegados a ella (mínimo / máximo
    inclusivo). Calibración P3, decisión 2.
  - Igual (calibración P3, decisión 5): «igual(es) a/al» o «equivalente(s)
    a/al» pegados a la cuantía, con la precedencia más baja de las formas
    con marcador (después de las simples), salvo que haya otro comparativo
    en la cláusula. DECLARADO: «comparativo» es la palabra comparativa
    (raíces «super-»/«exced-», «mayor», «menor», «superior», «inferior»,
    «más», «menos»; COMPARATIVO_EN_CLAUSULA); además, como en la propuesta
    de P2, «máximo», «mínimo», «tope» o «límite» en la ventana anterior
    excluyen (TOPE_EN_VENTANA). «Hasta» temporal o «capital mínimo» lejos de
    la cuantía no excluyen.
  - Comparador pegado a la cuantía (enmienda 5 a L-ESQ-R2, punto 2; C2 de
    U-R2-CODIGO-2, punto j): si una forma simple, compuesta o de adyacencia
    termina justo antes de la cuantía (solo artículos o «de», «del», «a»,
    «al», «en» en el medio) o una pospuesta va pegada después, el marcador de
    coeficiente no se aplica a esa cuantía, venga del tramo, de la
    descripción o del título: el valor acota, no multiplica («no superarán el
    1,25 % de los activos ponderados»).
  - Sin marcador: `no_determinada` en toda cuantía; el plazo (unidad temporal)
    conserva su regla propia, `sin_marcador_plazo`, sin `comparacion_asumida`
    (enmienda 3 a L-ESQ-R2, firmada en 8d01b04; rige desde r2b). Con
    `plazo_sin_marcador="maximo_asumido"`, la regla anterior (máximo inclusivo
    con `comparacion_asumida`), que solo usa el ensamblado de la fase r2a para
    reproducir los grafos sellados. «Límite», «tope», «entre» y «máximo» no
    adyacente no son marcadores (calibración P3, decisión 9).
  - Tramo compuesto (U-R2-CODIGO-2, C2, punto k): en un tramo de dos segmentos
    unidos por « […] » (encabezado de la lista y su ítem), una cuantía del
    ítem sin marcador propio toma el del final del encabezado, leído sin su
    «:» como si precediera a la cuantía («…los siguientes límites mínimos:
    […] 6% por los APR» → mínimo inclusivo); la regla lleva el prefijo
    `encabezado:`.

Adyacencia: los marcadores se buscan en una ventana junto a cada cuantía, no
en todo el texto: hasta VENTANA_ANTES palabras antes y VENTANA_DESPUES después,
sin cruzar un límite de cláusula («;», «:», punto final) ni otra cuantía. La
negación se busca hacia atrás desde el marcador, dentro de la cláusula.

Cuantías: adaptación de las regex D-P6 del prototipo de U-UMBRAL
(reports/u_umbral/u_umbral_u1.py:563-590), con dos cambios declarados: el
paréntesis después del número admite texto («365 (trescientos sesenta y cinco)
días») y una cuantía repetida entre paréntesis junto a otra igual («30%
(treinta por ciento)») se cuenta una vez. U-R2-CODIGO-2, C2, punto c: «hs.» y
«hrs.» son horas; «hábil» y «corrido» en singular fijan `dias_tipo`; «o más»
entre el paréntesis y la unidad («180 (ciento ochenta) o más días») es parte
de la cuantía y la marca como mínimo inclusivo; un ordinal con unidad temporal
(«el quinto día hábil», «trigésimo sexto mes») es una cuantía solo después de
«hasta el», «dentro del» o «a más tardar», y ese marcador fija su comparación
(máximo inclusivo).

Sin API, sin archivos: funciones puras.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

VENTANA_ANTES = 10
VENTANA_DESPUES = 3
NEGACION_MAX_MEDIO = 3
BASE_MAX_PALABRAS = 20

# ------------------------------------------------------------------------- #
# Plegado: minúsculas y sin diacríticos, con el mismo largo que el original   #
# ------------------------------------------------------------------------- #


def _plegar_char(c: str) -> str:
    d = unicodedata.normalize("NFKD", c)
    base = "".join(x for x in d if not unicodedata.combining(x))
    base = base.lower()
    return base if len(base) == 1 else c.lower()[:1] or c


def plegar(texto: str) -> str:
    """Minúsculas y sin diacríticos, carácter por carácter (los offsets del
    texto plegado son los del original)."""
    return "".join(_plegar_char(c) for c in texto)


# ------------------------------------------------------------------------- #
# Cuantías                                                                    #
# ------------------------------------------------------------------------- #
LETRAS_VALOR = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
                "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
                "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
                "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintiun": 21,
                "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
                "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
                "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
                "ochenta": 80, "noventa": 90, "cien": 100}
_ALT_LV = "|".join(sorted(LETRAS_VALOR, key=len, reverse=True))
_NUM = r"(\d+(?:[.,]\d+)?|" + _ALT_LV + r")"
_PAREN = r"(?:\s*\([^()]{1,60}\))?"
_CIFRA = r"(\d[\d.,]*\d|\d)"

# Los patrones corren sobre el texto plegado (sin tildes, minúsculas).
PATRONES = (
    ("porcentaje", re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*%")),
    ("porcentaje", re.compile(r"(?<![\w.,])" + _NUM + _PAREN + r"\s+por\s+ciento\b")),
    ("veces", re.compile(r"(?<![\w.,])" + _NUM + _PAREN + r"\s+veces\b")),
    ("plazo", re.compile(r"(?<![\w.,])(\d+|" + _ALT_LV + r")" + _PAREN + r"(?P<o_mas>\s+o\s+mas)?"
                         + r"\s*(dias?|mes(?:es)?|anos?|horas?|semanas?)\b"
                         r"(?:\s+(habil(?:es)?|corridos?))?")),
    ("plazo_hs", re.compile(r"(?<![\w.,])(\d+|" + _ALT_LV + r")" + _PAREN + r"\s*(?:hs|hrs?)\b\.?")),
    ("monto_pref", re.compile(r"(us\$|u\$s|usd|eur|€|\$)\s*" + _CIFRA
                              + r"(?:\s*(mil\s+millones|millones|mil)\b)?")),
    ("monto_suf", re.compile(r"(?<![\d.,])" + _CIFRA
                             + r"\s*(?:(mil\s+millones\s+de|millones\s+de|mil)\s+)?"
                             r"(pesos|dolares(?:\s+estadounidenses)?|usd|uva|euros)\b")),
)
_RE_COMPUESTO_ANTES = re.compile(r"(?:\b(?:" + _ALT_LV + r"|ciento|mil|cientos)\s+(?:y\s+)?)$")
MONEDA_CODIGO = {"$": "ARS", "pesos": "ARS", "us$": "USD", "u$s": "USD", "usd": "USD",
                 "dolares": "USD", "dolares estadounidenses": "USD", "eur": "EUR", "€": "EUR",
                 "euros": "EUR"}
MULT = {None: 1, "mil": 10 ** 3, "millones": 10 ** 6, "mil millones": 10 ** 9,
        "millones de": 10 ** 6, "mil millones de": 10 ** 9}
UNIDAD_TEMPORAL = (("dia", "dias"), ("mes", "meses"), ("ano", "anios"),
                   ("hora", "horas"), ("semana", "semanas"))
# Ordinales con unidad temporal (U-R2-CODIGO-2, C2, punto c): cuantía solo
# después de uno de los marcadores de MARCADOR_ORDINAL, que fija la comparación.
ORDINALES = {"primer": 1, "primero": 1, "primera": 1, "segundo": 2, "segunda": 2, "tercer": 3, "tercero": 3,
             "tercera": 3, "cuarto": 4, "cuarta": 4, "quinto": 5, "quinta": 5, "sexto": 6, "sexta": 6,
             "septimo": 7, "septima": 7, "octavo": 8, "octava": 8, "noveno": 9, "novena": 9, "decimo": 10,
             "decima": 10, "undecimo": 11, "undecima": 11, "duodecimo": 12, "duodecima": 12, "vigesimo": 20,
             "vigesima": 20, "trigesimo": 30, "trigesima": 30}
_DECENAS_ORD = ("decimo", "decima", "vigesimo", "vigesima", "trigesimo", "trigesima")
_UNIDADES_ORD = "|".join(sorted((k for k, v in ORDINALES.items() if v < 10), key=len, reverse=True))
_ALT_ORD = "|".join(sorted(ORDINALES, key=len, reverse=True))
RE_ORDINAL = re.compile(
    r"(?<![\w.,])(?P<ord>(?:" + "|".join(_DECENAS_ORD) + r")\s+(?:" + _UNIDADES_ORD + r")|" + _ALT_ORD
    + r"|\d+\s*[°º]|\d+[°ºo](?=\s))\s+(?P<u>dias?|mes(?:es)?|anos?|semanas?)\b"
    r"(?:\s+(?P<cal>habil(?:es)?|corridos?))?")
MARCADOR_ORDINAL = (("hasta", re.compile(r"\b(hasta)\s+el\s+$")),
                    ("dentro_de", re.compile(r"\b(dentro\s+del)\s+$")),
                    ("a_mas_tardar", re.compile(r"\b(a\s+mas\s+tardar)\s+(?:(?:el|al)\s+)?$")))


def parse_num(s: str) -> Optional[Decimal]:
    s = s.strip()
    if s in LETRAS_VALOR:
        return Decimal(LETRAS_VALOR[s])
    s = s.rstrip(".,")
    if "," in s:
        s2 = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s2 = s.replace(".", "")
    else:
        s2 = s
    try:
        return Decimal(s2)
    except InvalidOperation:
        return None


def dec_str(d: Decimal) -> str:
    t = format(d.normalize(), "f")
    return t


@dataclass
class Cuantia:
    inicio: int
    fin: int
    texto: str
    clase: str
    valor: Optional[str] = None
    unidad: Optional[str] = None
    moneda: Optional[str] = None
    dias_tipo: Optional[str] = None
    fuera_de_lista: list = field(default_factory=list)
    comparacion: str = "no_determinada"
    regla: str = "sin_marcador"
    marcador: Optional[str] = None
    fuente_marcador: Optional[str] = None
    comparacion_asumida: bool = False
    base: Optional[str] = None
    ventana: str = ""
    # U-R2-CODIGO-2, C2, punto c: marcador que la detección exige o incluye
    # (forma, inicio, fin en el texto): el de un ordinal («hasta el», «dentro
    # del», «a más tardar») o «o más» entre el paréntesis y la unidad.
    marcador_de_la_cuantia: Optional[tuple] = None

    def como_dict(self) -> dict:
        return asdict(self)


def _compuesto(pleg: str, inicio: int, grupo: str) -> bool:
    if grupo not in LETRAS_VALOR:
        return False
    return bool(_RE_COMPUESTO_ANTES.search(pleg[max(0, inicio - 30):inicio]))


def detectar_cuantias(texto: str) -> list[Cuantia]:
    """Cuantías del texto, en orden, sin solapamientos."""
    pleg = plegar(texto)
    crudos: list[Cuantia] = []
    for clase, pat in PATRONES:
        for m in pat.finditer(pleg):
            c = Cuantia(inicio=m.start(), fin=m.end(), texto=texto[m.start():m.end()], clase=clase)
            if clase in ("porcentaje", "veces"):
                g = m.group(1)
                if _compuesto(pleg, m.start(1), g):
                    continue
                v = parse_num(g)
                c.valor = dec_str(v) if v is not None else None
                c.unidad = "porcentaje" if clase == "porcentaje" else "veces"
            elif clase == "plazo":
                g, u, cal = m.group(1), m.group(3), m.group(4)
                if _compuesto(pleg, m.start(1), g):
                    continue
                v = parse_num(g)
                c.valor = dec_str(v) if v is not None else None
                c.unidad = next(n for pref, n in UNIDAD_TEMPORAL if u.startswith(pref))
                if c.unidad == "dias" and cal:
                    c.dias_tipo = "habiles" if cal.startswith("habil") else "corridos"
                if c.unidad not in ("dias", "meses", "anios"):
                    c.fuera_de_lista.append("unidad")
                if m.group("o_mas"):
                    c.marcador_de_la_cuantia = ("o_mas", m.start("o_mas") + len(m.group("o_mas"))
                                                - len(m.group("o_mas").lstrip()), m.end("o_mas"))
                c.clase = "plazo"
            elif clase == "plazo_hs":
                g = m.group(1)
                if _compuesto(pleg, m.start(1), g):
                    continue
                v = parse_num(g)
                c.valor = dec_str(v) if v is not None else None
                c.unidad, c.clase = "horas", "plazo"
                c.fuera_de_lista.append("unidad")
            elif clase == "monto_pref":
                mon = MONEDA_CODIGO[m.group(1)]
                v = parse_num(m.group(2))
                mult = MULT[re.sub(r"\s+", " ", m.group(3)) if m.group(3) else None]
                c.valor = dec_str(v * mult) if v is not None else None
                c.unidad, c.moneda, c.clase = "moneda", mon, "monto"
            else:
                v = parse_num(m.group(1))
                mult = MULT[re.sub(r"\s+", " ", m.group(2)) if m.group(2) else None]
                nombre = re.sub(r"\s+", " ", m.group(3))
                c.valor = dec_str(v * mult) if v is not None else None
                if nombre == "uva":
                    c.unidad = "uva"
                else:
                    c.unidad, c.moneda = "moneda", MONEDA_CODIGO[nombre]
                c.clase = "monto"
            crudos.append(c)
    for m in RE_ORDINAL.finditer(pleg):
        previo = pleg[max(0, m.start() - 40):m.start()]
        marca = next(((forma, mk) for forma, pat in MARCADOR_ORDINAL for mk in [pat.search(previo)] if mk), None)
        if marca is None:
            continue
        forma, mk = marca
        o = " ".join(m.group("ord").split())
        valor = int(re.match(r"\d+", o).group(0)) if o[0].isdigit() else sum(ORDINALES[x] for x in o.split())
        u = next(n for pref, n in UNIDAD_TEMPORAL if m.group("u").startswith(pref))
        base_previo = m.start() - len(previo)
        c = Cuantia(inicio=m.start(), fin=m.end(), texto=texto[m.start():m.end()], clase="plazo", valor=str(valor),
                    unidad=u, dias_tipo=(("habiles" if m.group("cal").startswith("habil") else "corridos")
                                         if u == "dias" and m.group("cal") else None),
                    marcador_de_la_cuantia=(forma, base_previo + mk.start(1), base_previo + mk.end(1)))
        if u not in ("dias", "meses", "anios"):
            c.fuera_de_lista.append("unidad")
        crudos.append(c)
    crudos.sort(key=lambda c: (c.inicio, -(c.fin - c.inicio)))
    out: list[Cuantia] = []
    for c in crudos:
        if out and c.inicio < out[-1].fin:
            continue
        if out and _repetida_entre_parentesis(texto, out[-1], c):
            continue
        out.append(c)
    return out


def _repetida_entre_parentesis(texto: str, a: Cuantia, b: Cuantia) -> bool:
    """«30% (treinta por ciento)» o «treinta por ciento (30%)»: la segunda es
    la misma cuantía escrita de nuevo entre paréntesis."""
    if (a.valor, a.unidad) != (b.valor, b.unidad):
        return False
    return bool(re.fullmatch(r"\s*\(\s*", texto[a.fin:b.inicio])) and \
        bool(re.match(r"\s*\)", texto[b.fin:]))


# ------------------------------------------------------------------------- #
# Cláusulas y ventanas                                                        #
# ------------------------------------------------------------------------- #
_ABREV = frozenset({"com", "art", "arts", "inc", "res", "nro", "n", "pto", "ptos", "ap", "cfr",
                    "etc", "dec", "gral", "ej", "pag", "sr", "sres", "dr", "dra", "lic", "sec",
                    "num", "cap", "tit", "pt", "aprox"})
_RE_LIMITE = re.compile(r"[;:]|\.(?=\s|$)")


def limites_de_clausula(texto: str) -> list[int]:
    out = []
    for m in _RE_LIMITE.finditer(texto):
        if m.group() == ".":
            prev = re.search(r"(\w+)$", texto[:m.start()])
            if prev and plegar(prev.group(1)) in _ABREV:
                continue
        out.append(m.start())
    return out


def _palabras(s: str) -> list[re.Match]:
    return list(re.finditer(r"\S+", s))


# ------------------------------------------------------------------------- #
# Marcadores (sobre texto plegado)                                            #
# ------------------------------------------------------------------------- #
# Raíces (calibración P3, decisión 1): toda forma, con las exclusiones listadas.
_SUPER = r"super(?!intend|vis|fic|avit)\w*"
_EXCED = r"exced(?!ente)\w*"
SIMPLES = (
    ("minimo_estricto", "raiz_super", re.compile(r"\b" + _SUPER)),
    ("minimo_estricto", "raiz_exced", re.compile(r"\b" + _EXCED)),
    ("minimo_estricto", "mas_de", re.compile(r"\bmas\s+del?\b")),
    ("minimo_estricto", "mayor", re.compile(r"\bmayor(?:es)?\s+al?\b")),
    ("maximo_estricto", "inferior", re.compile(r"\binferior(?:es)?\s+al?\b")),
    ("maximo_estricto", "menos_de", re.compile(r"\bmenos\s+del?\b")),
    ("maximo_estricto", "menor", re.compile(r"\bmenor(?:es)?\s+al?\b")),
)
# «Igual o superior/inferior» con «equivalente(s)» y con las formas verbales («igualen o superen»): punto i de C2
# de U-R2-CODIGO-2.
_IGUAL_O = r"\b(?:igual(?:es|a|an|e|en)?|equivalentes?)\s+o\s+"
COMPUESTAS = (
    ("minimo_inclusivo", "igual_o_superior",
     re.compile(_IGUAL_O + r"(?:mayor(?:es)?\b|" + _SUPER + r"|" + _EXCED + r")")),
    ("maximo_inclusivo", "igual_o_inferior",
     re.compile(_IGUAL_O + r"(?:inferior(?:es)?|menor(?:es)?)\b")),
    ("maximo_inclusivo", "menor_o_igual",
     re.compile(r"\b(?:menor|inferior)(?:es)?\s+o\s+iguale?s?\b")),
    ("minimo_inclusivo", "mayor_o_igual",
     re.compile(r"\b(?:mayor|superior)(?:es)?\s+o\s+iguale?s?\b")),
    ("maximo_inclusivo", "como_maximo", re.compile(r"\bcomo\s+maximo\b")),
    ("maximo_inclusivo", "hasta", re.compile(r"\bhasta\b")),
    ("maximo_inclusivo", "dentro_de", re.compile(r"\bdentro\s+de\b")),
    ("minimo_inclusivo", "al_menos", re.compile(r"\bal\s+menos\b")),
    ("minimo_inclusivo", "como_minimo", re.compile(r"\bcomo\s+minimo\b")),
    ("minimo_inclusivo", "un_minimo_de", re.compile(r"\bun\s+minimo\s+de\b")),
    ("minimo_inclusivo", "por_lo_menos", re.compile(r"\bpor\s+lo\s+menos\b")),
)
POSPUESTAS = ("como_maximo", "como_minimo", "al_menos", "por_lo_menos")
COMPARATIVOS_COMPUESTOS = ("igual_o_superior", "igual_o_inferior", "menor_o_igual", "mayor_o_igual")
# «o más» / «o menos»: solo pospuestos y pegados a la cuantía (admite un paréntesis).
SOLO_POSPUESTAS = re.compile(r"\s*(?:\([^()]{0,60}\)\s*)?o\s+(mas|menos)\b")
ADYACENCIA = (
    ("minimo_inclusivo", "adyacencia_minimo", re.compile(r"\bminim[oa]s?\s+(?:del?\s+)?$")),
    ("maximo_inclusivo", "adyacencia_maximo", re.compile(r"\bmaxim[oa]s?\s+(?:del?\s+)?$")),
)
COEFICIENTE = re.compile(r"\bponder\w*|\bcoeficientes?\b|\bfactor(?:es)?\b")
# Desde la descripción, «factor» no cuenta (calibración P3, decisión 4).
COEFICIENTE_DESCRIPCION = re.compile(r"\bponder\w*|\bcoeficientes?\b")
# «igual» (calibración P3, decisión 5): pegado a la cuantía.
RE_IGUAL_PEGADO = re.compile(r"\b(iguale?s?|equivalentes?)\s+al?\s+$")
# Otro comparativo en la cláusula excluye «igual»: la palabra comparativa,
# con o sin «a» («superior» entra por la raíz «super-»).
COMPARATIVO_EN_CLAUSULA = re.compile(
    r"\b" + _SUPER + r"|\b" + _EXCED + r"|\b(?:mayor|menor|inferior)(?:es)?\b|\bmas\b|\bmenos\b")
# Y, como en la propuesta de P2 (A-IGUAL), estas palabras en la ventana anterior.
TOPE_EN_VENTANA = re.compile(r"\b(?:maxim[oa]s?|minim[oa]s?|topes?|limites?)\b")
NEGADORES = ("no", "sin", "ningun", "ninguna")
# Punto i de C2 de U-R2-CODIGO-2: más allá de NEGACION_MAX_MEDIO palabras, la negación alcanza al marcador si
# niega un verbo (`_niega_un_verbo`: «no» seguido de una forma de haber, poder o deber; «sin» seguido de un
# infinitivo; «ningún»/«ninguna» siempre) y entre los dos no hay una coma, otra forma de comparación ni una de
# estas palabras. Un «no» adjetival («sector privado no financiero», «no residentes») no alcanza.
NEGACION_BARRERAS = frozenset({"y", "e", "o", "u", "ni", "cuando", "si", "cuyo", "cuya", "cuyos", "cuyas", "donde",
                               "aunque", "pero", "salvo", "excepto", "mientras", "siempre"})
AUXILIARES_NEGADOS = frozenset({"ha", "han", "haya", "hayan", "habia", "habian", "hubiera", "hubieran", "hubiese",
                                "hubiesen", "habra", "habran", "podra", "podran", "puede", "pueden", "pueda",
                                "puedan", "podria", "podrian", "debera", "deberan", "debe", "deben", "deba",
                                "deban"})


def _no_de_o_no(toks: list, j: int) -> bool:
    """«O no» no es una negación (enmienda 5 a L-ESQ-R2, punto 1.d): el «no»
    de la posición `j` de `toks` va precedido por «o», con o sin coma en el
    medio («sea o no», «represente o no», «sea, o no,»)."""
    if toks[j].group(0) != "no":
        return False
    previo = next((t.group(0) for t in reversed(toks[:j]) if t.group(0) != ","), None)
    return previo == "o"


def _niega_un_verbo(negador: str, siguiente: str | None) -> bool:
    """Negador que alcanza más allá de NEGACION_MAX_MEDIO palabras (punto i)."""
    if negador in ("ningun", "ninguna"):
        return True
    if siguiente is None:
        return False
    if negador == "no":
        return siguiente in AUXILIARES_NEGADOS
    return negador == "sin" and siguiente.endswith(("ar", "er", "ir"))
INVERSION = {"minimo_estricto": "maximo_inclusivo", "maximo_estricto": "minimo_inclusivo",
             "minimo_inclusivo": "maximo_estricto", "maximo_inclusivo": "minimo_estricto"}

# Formas candidatas para «igual» que mide mediciones_p2.py entre las cuantías
# sin marcador; no se aplican (la regla es RE_IGUAL_PEGADO).
CANDIDATAS_IGUAL = (
    ("igual_a", re.compile(r"\biguale?s?\s+(?:a|al)\b")),
    ("equivalente_a", re.compile(r"\bequivalentes?\s+(?:a|al)\b")),
    ("sera_de", re.compile(r"\bser(?:a|an)\s+(?:de|del)\s*$")),
    ("fijado_en", re.compile(r"\bfijad[oa]s?\s+en\b")),
    ("de_a_secas", re.compile(r"\b(?:de|del)\s+$")),
)


def _negada(pleg: str, inicio_clausula: int, inicio_marcador: int,
            otros_marcadores: tuple = ()) -> Optional[str]:
    """Negador («no», «sin», «ningún», «ninguna») con cero a NEGACION_MAX_MEDIO
    palabras entre él y el marcador, dentro de la cláusula; más lejos (punto
    i), el negador que niega un verbo (`_niega_un_verbo`), si entre él y el
    marcador no hay una coma, una palabra de NEGACION_BARRERAS ni el comienzo
    de otra forma de comparación (`otros_marcadores`, posiciones de inicio).
    Devuelve el negador o None."""
    toks = list(re.finditer(r"[a-z0-9ñ]+|,", pleg[inicio_clausula:inicio_marcador]))
    palabras, barrera = 0, False
    for j in range(len(toks) - 1, -1, -1):
        w = toks[j].group(0)
        if w == ",":
            barrera = True
            continue
        if w in NEGADORES and not _no_de_o_no(toks, j):
            if palabras <= NEGACION_MAX_MEDIO:
                return w
            siguiente = next((t.group(0) for t in toks[j + 1:] if t.group(0) != ","), None)
            if not barrera and _niega_un_verbo(w, siguiente):
                return w
        if w in NEGACION_BARRERAS or any(inicio_clausula + toks[j].start() == x for x in otros_marcadores):
            barrera = True
        palabras += 1
        if barrera and palabras > NEGACION_MAX_MEDIO:
            return None
    return None


def _en(rango: tuple[int, int], m_ini: int) -> bool:
    return rango[0] <= m_ini < rango[1]


# Lo que puede mediar entre un comparador y la cuantía para que esté pegado a ella (punto j).
_RE_RELLENO = re.compile(r"\s*(?:(?:el|la|los|las|lo|un|una|unos|unas|de|del|al|a|en)\s+)*")
# Comparación de una cuantía con el marcador que exige o incluye su detección (punto c).
SENTIDO_MARCADOR_DE_LA_CUANTIA = {"hasta": "maximo_inclusivo", "dentro_de": "maximo_inclusivo",
                                  "a_mas_tardar": "maximo_inclusivo", "o_mas": "minimo_inclusivo"}
PLAZO_SIN_MARCADOR = ("no_determinada", "maximo_asumido")


def fijar_comparacion(texto: str, c: Cuantia, inicio_clausula: int, fin_clausula: int,
                      fin_previa: int, inicio_siguiente: int,
                      descripcion: Optional[str] = None, titulo: Optional[str] = None,
                      plazo_sin_marcador: str = "no_determinada") -> None:
    """Fija comparacion, regla, marcador y ventana de la cuantía `c`.
    `plazo_sin_marcador`: «no_determinada» (enmienda 3 a L-ESQ-R2, r2b) o
    «maximo_asumido» (la regla anterior, para reproducir la fase r2a)."""
    if plazo_sin_marcador not in PLAZO_SIN_MARCADOR:
        raise ValueError(f"plazo_sin_marcador desconocido: {plazo_sin_marcador!r}")
    pleg = plegar(texto)
    ini_antes = max(inicio_clausula, fin_previa)
    pal = _palabras(texto[ini_antes:c.inicio])
    if len(pal) > VENTANA_ANTES:
        ini_antes = ini_antes + pal[-VENTANA_ANTES].start()
    fin_desp = min(fin_clausula, inicio_siguiente)
    pal_d = _palabras(texto[c.fin:fin_desp])
    if len(pal_d) > VENTANA_DESPUES:
        fin_desp = c.fin + pal_d[VENTANA_DESPUES - 1].end()
    antes = (ini_antes, c.inicio)
    despues = (c.fin, fin_desp)
    c.ventana = texto[ini_antes:fin_desp]

    compuestas = []
    for sentido, forma, pat in COMPUESTAS:
        for m in pat.finditer(pleg, antes[0], antes[1]):
            compuestas.append((m.start(), m.end(), sentido, forma, texto[m.start():m.end()]))
        if forma in POSPUESTAS:
            for m in pat.finditer(pleg, despues[0], despues[1]):
                compuestas.append((m.start(), m.end(), sentido, forma, texto[m.start():m.end()]))
    for sentido, forma, pat in ADYACENCIA:
        m = pat.search(pleg[antes[0]:antes[1]])
        if m:
            a0 = antes[0] + m.start()
            # Si la adyacencia cae dentro de una compuesta listada («como máximo»,
            # «un mínimo de»), cuenta la compuesta: mismo nivel, forma más específica.
            if not any(x[0] <= a0 < x[1] for x in compuestas):
                compuestas.append((a0, antes[1], sentido, forma, texto[a0:antes[1]].strip()))
    m = SOLO_POSPUESTAS.match(pleg, c.fin, min(fin_clausula, inicio_siguiente))
    if m:
        sentido, forma = (("minimo_inclusivo", "o_mas") if m.group(1) == "mas"
                          else ("maximo_inclusivo", "o_menos"))
        compuestas.append((m.start(1) - 2, m.end(), sentido, forma, texto[m.start(1) - 2:m.end()]))
    if c.marcador_de_la_cuantia is not None:
        forma, a, b = c.marcador_de_la_cuantia
        compuestas.append((a, b, SENTIDO_MARCADOR_DE_LA_CUANTIA[forma], forma, texto[a:b]))
    dentro_de_igual = [(a, b) for a, b, _, f, _ in compuestas if f in COMPARATIVOS_COMPUESTOS]

    simples = []
    for sentido, forma, pat in SIMPLES:
        for m in pat.finditer(pleg, antes[0], antes[1]):
            if any(a <= m.start() < b for a, b in dentro_de_igual):
                continue
            simples.append((m.start(), m.end(), sentido, forma, texto[m.start():m.end()]))

    def distancia(x):
        return c.inicio - x[1] if x[0] < c.inicio else x[0] - c.fin

    def pegado(x) -> bool:
        if x[3] in ("o_mas", "o_menos") or c.inicio <= x[0] < c.fin:
            return True
        if x[1] <= c.inicio:
            return _RE_RELLENO.fullmatch(pleg, x[1], c.inicio) is not None
        return x[3] in POSPUESTAS and not pleg[c.fin:x[0]].strip()

    # 1. Coeficiente: en la ventana, en la descripción o en el título, salvo que un comparador esté pegado a la
    #    cuantía (punto j).
    if not any(pegado(x) for x in compuestas + simples):
        for fuente, s in (("tramo", pleg[antes[0]:despues[1]]), ("descripcion", plegar(descripcion or "")),
                          ("titulo", plegar(titulo or ""))):
            m = (COEFICIENTE_DESCRIPCION if fuente == "descripcion" else COEFICIENTE).search(s)
            if m:
                original = {"tramo": texto[antes[0]:despues[1]], "descripcion": descripcion or "",
                            "titulo": titulo or ""}[fuente]
                c.comparacion, c.regla, c.marcador, c.fuente_marcador = (
                    "coeficiente", "coeficiente", original[m.start():m.end()], fuente)
                return

    # 2. Negación de una simple o de «igual o …».
    marcas_clausula = sorted({m.start() for _, _, pat in COMPUESTAS + SIMPLES
                              for m in pat.finditer(pleg, inicio_clausula, c.inicio)})
    negadas = []
    for x in simples + [y for y in compuestas if y[3] in COMPARATIVOS_COMPUESTOS]:
        neg = _negada(pleg, inicio_clausula, x[0], tuple(p for p in marcas_clausula if p != x[0]))
        if neg:
            negadas.append((x, neg))
    if negadas:
        (x, neg) = min(negadas, key=lambda t: distancia(t[0]))
        c.comparacion = INVERSION[x[2]]
        c.regla, c.marcador, c.fuente_marcador = f"negacion:{x[3]}", f"{neg} … {x[4]}", "tramo"
        return
    # 3. Compuestas y adyacencia.
    if compuestas:
        x = min(compuestas, key=distancia)
        c.comparacion, c.regla, c.marcador, c.fuente_marcador = x[2], f"compuesta:{x[3]}", x[4], "tramo"
        return
    # 4. Simples.
    if simples:
        x = min(simples, key=distancia)
        c.comparacion, c.regla, c.marcador, c.fuente_marcador = x[2], f"simple:{x[3]}", x[4], "tramo"
        return
    # 5. Igual: pegado a la cuantía y sin otro comparativo en la cláusula.
    m = RE_IGUAL_PEGADO.search(pleg[antes[0]:antes[1]])
    if m:
        mi = antes[0] + m.start()
        clausula = (pleg[inicio_clausula:mi] + " " * (c.fin - mi) + pleg[c.fin:fin_clausula])
        if not COMPARATIVO_EN_CLAUSULA.search(clausula) and not TOPE_EN_VENTANA.search(pleg[antes[0]:mi]):
            forma = "equivalente_a" if m.group(1).startswith("equivalente") else "igual_a"
            c.comparacion, c.regla, c.marcador, c.fuente_marcador = (
                "igual", f"igual:{forma}", texto[mi:antes[1]].strip(), "tramo")
            return
    # 6. Sin marcador (enmienda 3 a L-ESQ-R2: el plazo también queda no_determinada, con su regla propia).
    if c.clase == "plazo" and plazo_sin_marcador == "maximo_asumido":
        c.comparacion, c.regla, c.comparacion_asumida = "maximo_inclusivo", "sin_marcador_plazo", True
    elif c.clase == "plazo":
        c.comparacion, c.regla = "no_determinada", "sin_marcador_plazo"
    else:
        c.comparacion, c.regla = "no_determinada", "sin_marcador"


# ------------------------------------------------------------------------- #
# Base (umbral relacional)                                                    #
# ------------------------------------------------------------------------- #
_RE_CONECTOR_PORC = re.compile(r"\s*(?:\([^()]{0,60}\)\s*)?(?:de|del|sobre)\s+")
_RE_CONECTOR_VECES = re.compile(r"\s*(?:\([^()]{0,60}\)\s*)?(?:(?:de|del|sobre)\s+|(?=(?:el|la|los|las|su|sus)\s))")
_RE_ARTICULO = re.compile(r"(?:el|la|los|las|lo)\s+")
_RE_COLA = re.compile(r"(?:\s+(?:y/o|y|o|e|u))+\s*$")


def fijar_base(texto: str, c: Cuantia, fin_clausula: int) -> None:
    if c.unidad not in ("porcentaje", "veces"):
        return
    pleg = plegar(texto)
    pat = _RE_CONECTOR_PORC if c.unidad == "porcentaje" else _RE_CONECTOR_VECES
    m = pat.match(pleg, c.fin, fin_clausula)
    if not m:
        return
    ini = m.end()
    a = _RE_ARTICULO.match(pleg, ini, fin_clausula)
    if a:
        ini = a.end()
    fin = fin_clausula
    coma = texto.find(",", ini, fin)
    if coma != -1:
        fin = coma
    base = texto[ini:fin]
    pal = _palabras(base)
    if len(pal) > BASE_MAX_PALABRAS:
        base = base[:pal[BASE_MAX_PALABRAS - 1].end()]
    base = _RE_COLA.sub("", " ".join(base.split())).strip()
    c.base = base or None


# ------------------------------------------------------------------------- #
# Entrada                                                                     #
# ------------------------------------------------------------------------- #
# Separador de los dos segmentos de un tramo compuesto (validador_r2.SEPARADOR_TRAMO_COMPUESTO, « […] »).
_RE_SEPARADOR_TRAMO = re.compile(r"\s*\[\s*(?:…|\.\.\.)\s*\]\s*")
_RE_FIN_ENCABEZADO = re.compile(r"[\s:：]+$")


def _marcador_del_encabezado(tramo: str, c: Cuantia, cs: list[Cuantia], descripcion: Optional[str],
                             titulo: Optional[str], plazo_sin_marcador: str) -> None:
    """Punto k: la cuantía `c`, del ítem de un tramo compuesto y sin marcador
    propio, toma el marcador del final del encabezado. El encabezado, sin su
    «:» final, se lee como si precediera inmediatamente a la cuantía."""
    seps = list(_RE_SEPARADOR_TRAMO.finditer(tramo))
    if len(seps) != 1 or c.inicio < seps[0].end():
        return
    enc = _RE_FIN_ENCABEZADO.sub("", tramo[:seps[0].start()])
    if not enc:
        return
    virtual = enc + " " + tramo[c.inicio:]
    off = len(enc) + 1 - c.inicio
    c2 = Cuantia(**{**asdict(c), "inicio": c.inicio + off, "fin": c.fin + off, "fuera_de_lista": list(c.fuera_de_lista),
                    "marcador_de_la_cuantia": None, "comparacion": "no_determinada", "regla": "sin_marcador",
                    "marcador": None, "fuente_marcador": None, "comparacion_asumida": False})
    lims = limites_de_clausula(virtual)
    ini_cl = max([p + 1 for p in lims if p < c2.inicio], default=0)
    fin_cl = min([p for p in lims if p >= c2.fin], default=len(virtual))
    fin_prev = max([x.fin for x in cs if x.fin <= seps[0].start()], default=0)
    sig = [x.inicio + off for x in cs if x.inicio > c.inicio]
    fijar_comparacion(virtual, c2, ini_cl, fin_cl, fin_prev, min(sig, default=len(virtual)), descripcion, titulo,
                      plazo_sin_marcador)
    if c2.regla in ("sin_marcador", "sin_marcador_plazo"):
        return
    c.comparacion, c.regla, c.marcador = c2.comparacion, f"encabezado:{c2.regla}", c2.marcador
    c.fuente_marcador, c.comparacion_asumida, c.ventana = "encabezado", False, c2.ventana


def analizar(tramo: str, descripcion: Optional[str] = None,
             titulo: Optional[str] = None, plazo_sin_marcador: str = "no_determinada") -> list[Cuantia]:
    """Cuantías del tramo, cada una con valor, unidad, base y comparación.
    `descripcion` y `titulo` solo aportan el marcador de coeficiente.
    `plazo_sin_marcador`: ver `fijar_comparacion`."""
    cs = detectar_cuantias(tramo)
    lims = limites_de_clausula(tramo)
    for i, c in enumerate(cs):
        ini_cl = max([p + 1 for p in lims if p < c.inicio], default=0)
        fin_cl = min([p for p in lims if p >= c.fin], default=len(tramo))
        fin_prev = cs[i - 1].fin if i > 0 else 0
        ini_sig = cs[i + 1].inicio if i + 1 < len(cs) else len(tramo)
        fijar_comparacion(tramo, c, ini_cl, fin_cl, fin_prev, ini_sig, descripcion, titulo, plazo_sin_marcador)
        if c.regla in ("sin_marcador", "sin_marcador_plazo"):
            _marcador_del_encabezado(tramo, c, cs, descripcion, titulo, plazo_sin_marcador)
        fijar_base(tramo, c, min(fin_cl, ini_sig))
    return cs


def elemento_umbral(c: Cuantia, tramo: str, origen: Optional[str] = None) -> dict:
    """Diccionario con la forma de modelos_r2.ElementoUmbral."""
    fuera = list(c.fuera_de_lista)
    d = {"tramo": tramo, "valor": c.valor, "unidad": c.unidad, "moneda": c.moneda,
         "dias_tipo": c.dias_tipo, "comparacion": c.comparacion, "base": c.base,
         "comparacion_asumida": c.comparacion_asumida, "regla_comparacion": c.regla,
         "origen": origen, "fuera_de_lista": fuera}
    return d
