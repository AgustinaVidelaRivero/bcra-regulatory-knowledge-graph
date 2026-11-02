#!/usr/bin/env python3
"""bm25_fragmentos.py — Medida de afinidad BM25 del servidor de fragmentos (A2.1, tramo 1).

Solo biblioteca estándar: en modo BM25 el servidor no importa numpy, torch,
sentence-transformers ni neo4j, y no carga ningún modelo.

El analizador replica, pieza por pieza, el `spanish` de Lucene que usa el índice
full-text del grafo (README del backend del grafo, decisión 4). La versión de
Lucene es la de la imagen neo4j:5.26.9-community de ese backend, cuyo pom.xml
(tag 5.26.9 de neo4j/neo4j) fija `lucene.version` = 9.11.1. Fuentes, todas de
Lucene 9.11.1 (tag releases/lucene/9.11.1 de apache/lucene):

  1. Cadena: `org.apache.lucene.analysis.es.SpanishAnalyzer.createComponents`
     = StandardTokenizer -> LowerCaseFilter -> StopFilter(stop por defecto)
     -> SpanishLightStemFilter (el SetKeywordMarkerFilter solo entra con un
     conjunto de exclusión, que el analizador por defecto no tiene).
  2. Tokenizador: `org.apache.lucene.analysis.standard.StandardTokenizer`,
     reglas de corte de palabra de UAX #29 (`%unicode 12.1` en
     StandardTokenizerImpl.jflex), largo máximo 255 (StandardAnalyzer
     .DEFAULT_MAX_TOKEN_LENGTH). Acá se implementa el subconjunto de UAX #29
     que el corpus usa (ver `tokenizar`); las diferencias van en el FRENO.
  3. Minúsculas: `LowerCaseFilter` = Character.toLowerCase por punto de
     código (mapeo simple 1 a 1).
  4. Palabras vacías: `SpanishAnalyzer.getDefaultStopSet()` =
     WordlistLoader.getSnowballWordSet sobre
     `org/apache/lucene/analysis/snowball/spanish_stop.txt` (lista del
     proyecto Snowball, licencia BSD): 308 palabras, en `STOP_ES`.
  5. Stemmer: `org.apache.lucene.analysis.es.SpanishLightStemmer.stem`
     (Savoy, «Report on CLEF-2001 Experiments»), en `stem`.

BM25: `org.apache.lucene.search.similarities.BM25Similarity` de Lucene 9.11.1,
constructor sin argumentos: k1 = 1,2, b = 0,75 (la doc de Neo4j sobre índices
full-text no fija otros: solo expone `fulltext.analyzer` y
`fulltext.eventually_consistent`).
  idf(t)  = ln(1 + (docCount - df + 0,5) / (df + 0,5))
  s(t, d) = idf(t) · tf / (tf + k1 · (1 - b + b · dl / avgdl))
  avgdl   = sumTotalTermFreq / docCount
  dl      = largo del documento en términos tras el analizador, codificado en
            un byte con SmallFloat.intToByte4 y decodificado con
            SmallFloat.byte4ToInt, como la norma de Lucene (con pérdida).
  score(q, d) = Σ s(t, d) sobre los términos de la consulta analizada, con su
            multiplicidad (las cláusulas SHOULD repetidas de Lucene suman).
Desempate del ranking: score desc, id asc (el mismo del servidor denso).
"""
from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections import Counter

FORMATO = "indice_bm25_fragmentos v1"
LUCENE_VERSION = "9.11.1"
ANALIZADOR = "spanish de Lucene 9.11.1 (StandardTokenizer UAX#29 subconjunto + LowerCaseFilter + StopFilter spanish_stop.txt + SpanishLightStemFilter)"
K1 = 1.2
B = 0.75
MAX_TOKEN = 255

# spanish_stop.txt de Lucene 9.11.1 (Snowball, BSD), en el orden del archivo.
STOP_ES = (
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un", "para", "con", "no",
    "una", "su", "al", "lo", "como", "más", "pero", "sus", "le", "ya", "o", "este", "sí", "porque",
    "esta", "entre", "cuando", "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde", "quien",
    "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso",
    "ante", "ellos", "e", "esto", "mí", "antes", "algunos", "qué", "unos", "yo", "otro", "otras",
    "otra", "él", "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual", "poco", "ella",
    "estar", "estas", "algunas", "algo", "nosotros",
    "mi", "mis", "tú", "te", "ti", "tu", "tus", "ellas", "nosotras", "vosotros", "vosotras", "os",
    "mío", "mía", "míos", "mías", "tuyo", "tuya", "tuyos", "tuyas", "suyo", "suya", "suyos", "suyas",
    "nuestro", "nuestra", "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras", "esos",
    "esas",
    "estoy", "estás", "está", "estamos", "estáis", "están", "esté", "estés", "estemos", "estéis",
    "estén", "estaré", "estarás", "estará", "estaremos", "estaréis", "estarán", "estaría", "estarías",
    "estaríamos", "estaríais", "estarían", "estaba", "estabas", "estábamos", "estabais", "estaban",
    "estuve", "estuviste", "estuvo", "estuvimos", "estuvisteis", "estuvieron", "estuviera",
    "estuvieras", "estuviéramos", "estuvierais", "estuvieran", "estuviese", "estuvieses",
    "estuviésemos", "estuvieseis", "estuviesen", "estando", "estado", "estada", "estados", "estadas",
    "estad",
    "he", "has", "ha", "hemos", "habéis", "han", "haya", "hayas", "hayamos", "hayáis", "hayan", "habré",
    "habrás", "habrá", "habremos", "habréis", "habrán", "habría", "habrías", "habríamos", "habríais",
    "habrían", "había", "habías", "habíamos", "habíais", "habían", "hube", "hubiste", "hubo", "hubimos",
    "hubisteis", "hubieron", "hubiera", "hubieras", "hubiéramos", "hubierais", "hubieran", "hubiese",
    "hubieses", "hubiésemos", "hubieseis", "hubiesen", "habiendo", "habido", "habida", "habidos",
    "habidas",
    "soy", "eres", "es", "somos", "sois", "son", "sea", "seas", "seamos", "seáis", "sean", "seré",
    "serás", "será", "seremos", "seréis", "serán", "sería", "serías", "seríamos", "seríais", "serían",
    "era", "eras", "éramos", "erais", "eran", "fui", "fuiste", "fue", "fuimos", "fuisteis", "fueron",
    "fuera", "fueras", "fuéramos", "fuerais", "fueran", "fuese", "fueses", "fuésemos", "fueseis",
    "fuesen", "siendo", "sido",
    "tengo", "tienes", "tiene", "tenemos", "tenéis", "tienen", "tenga", "tengas", "tengamos", "tengáis",
    "tengan", "tendré", "tendrás", "tendrá", "tendremos", "tendréis", "tendrán", "tendría", "tendrías",
    "tendríamos", "tendríais", "tendrían", "tenía", "tenías", "teníamos", "teníais", "tenían", "tuve",
    "tuviste", "tuvo", "tuvimos", "tuvisteis", "tuvieron", "tuviera", "tuvieras", "tuviéramos",
    "tuvierais", "tuvieran", "tuviese", "tuvieses", "tuviésemos", "tuvieseis", "tuviesen", "teniendo",
    "tenido", "tenida", "tenidos", "tenidas", "tened",
)
STOP = frozenset(STOP_ES)
SHA256_STOP = hashlib.sha256("\n".join(STOP_ES).encode("utf-8")).hexdigest()

# --------------------------------------------------------------------------- #
# Tokenizador: subconjunto de las reglas de corte de palabra de UAX #29        #
# --------------------------------------------------------------------------- #
_ALETTER, _NUM, _EXTNUMLET, _MIDLETTER, _MIDNUMLET, _SQ, _MIDNUM, _EXTEND, _OTRO = range(9)
# Propiedad Word_Break de UAX #29 (Unicode 12.1), solo los valores que usan las reglas WB6, WB7, WB11 y WB12.
_MID_LETTER = frozenset(":··՟״‧︓﹕：")
_MID_NUM_LET = frozenset(".‘’․﹒＇．")
_MID_NUM = frozenset(",;;։،؍٬߸⁄︐︔﹐﹔，；")
_CONTINUA = (_ALETTER, _NUM, _EXTNUMLET)


def _clase(ch: str) -> int:
    if ch in _MID_LETTER:
        return _MIDLETTER
    if ch in _MID_NUM_LET:
        return _MIDNUMLET
    if ch == "'":
        return _SQ
    if ch in _MID_NUM:
        return _MIDNUM
    cat = unicodedata.category(ch)
    if cat == "Nd":
        return _NUM
    if cat in ("Mn", "Me", "Mc") or ch in ("‌", "‍") or (cat == "Cf" and ch != "​"):
        return _EXTEND                      # Extend, Format y ZWJ (WB4)
    if cat == "Pc" or ch == " ":
        return _EXTNUMLET
    if ch.isalpha():
        return _ALETTER
    return _OTRO


def tokenizar(texto: str) -> list[str]:
    """Palabras de UAX #29 con al menos una letra o un dígito (los tipos ALPHANUM y NUM de
    StandardTokenizer). Reglas: WB4 (Extend/Format se pegan al carácter anterior), WB5,
    WB8-WB10 y WB13a-b (letras, dígitos y ExtendNumLet se unen), WB6-WB7 (letra
    (MidLetter|MidNumLet|') letra) y WB11-WB12 (dígito (MidNum|MidNumLet|') dígito);
    todo lo demás corta. Un token de más de 255 caracteres se parte en trozos de 255."""
    celdas: list[list] = []
    for ch in texto:
        c = _clase(ch)
        if c == _EXTEND and celdas and celdas[-1][1][-1] not in "\r\n\x0b\x0c\x85  ":
            celdas[-1][1] += ch
            continue
        celdas.append([c, ch])
    toks: list[str] = []
    i, n = 0, len(celdas)
    while i < n:
        if celdas[i][0] not in _CONTINUA:
            i += 1
            continue
        j = i
        partes = [celdas[i][1]]
        alnum = celdas[i][0] != _EXTNUMLET
        while True:
            if j + 1 < n and celdas[j + 1][0] in _CONTINUA:
                j += 1
                partes.append(celdas[j][1])
                alnum = alnum or celdas[j][0] != _EXTNUMLET
                continue
            if j + 2 < n:
                ult, med, sig = celdas[j][0], celdas[j + 1][0], celdas[j + 2][0]
                if ((ult == _ALETTER and sig == _ALETTER and med in (_MIDLETTER, _MIDNUMLET, _SQ))
                        or (ult == _NUM and sig == _NUM and med in (_MIDNUM, _MIDNUMLET, _SQ))):
                    partes += [celdas[j + 1][1], celdas[j + 2][1]]
                    j += 2
                    continue
            break
        if alnum:
            t = "".join(partes)
            toks.extend(t[k:k + MAX_TOKEN] for k in range(0, len(t), MAX_TOKEN))
        i = j + 1
    return toks


def minusculas(t: str) -> str:
    """Character.toLowerCase por punto de código (mapeo simple): la única letra cuyo
    mapeo completo de Python difiere del simple al pasar a minúscula es U+0130."""
    return "".join("i" if ch == "İ" else ch.lower() for ch in t)


_ACENTOS = str.maketrans({"à": "a", "á": "a", "â": "a", "ä": "a", "ò": "o", "ó": "o", "ô": "o", "ö": "o",
                          "è": "e", "é": "e", "ê": "e", "ë": "e", "ù": "u", "ú": "u", "û": "u", "ü": "u",
                          "ì": "i", "í": "i", "î": "i", "ï": "i"})


def stem(t: str) -> str:
    """SpanishLightStemmer.stem de Lucene 9.11.1: con menos de 5 caracteres no cambia
    nada; si no, quita los acentos de la tabla y aplica una sola regla de sufijo."""
    if len(t) < 5:
        return t
    s = t.translate(_ACENTOS)
    u = s[-1]
    if u in "oae":
        return s[:-1]
    if u == "s":
        if s[-2] == "e" and s[-3] == "s" and s[-4] == "e":
            return s[:-2]
        if s[-2] == "e" and s[-3] == "c":
            return s[:-3] + "z"
        if s[-2] in "oae":
            return s[:-2]
    return s


def analizar(texto: str) -> list[str]:
    """La cadena del analizador: tokenizar -> minúsculas -> palabras vacías -> stem."""
    out = []
    for t in tokenizar(texto):
        t = minusculas(t)
        if t in STOP:
            continue
        out.append(stem(t))
    return out


# --------------------------------------------------------------------------- #
# Norma de largo de Lucene (org.apache.lucene.util.SmallFloat, 9.11.1)         #
# --------------------------------------------------------------------------- #
def _long_to_int4(i: int) -> int:
    nbits = i.bit_length()
    if nbits < 4:
        return i
    shift = nbits - 4
    return ((i >> shift) & 0x07) | ((shift + 1) << 3)


def _int4_to_long(i: int) -> int:
    bits, shift = i & 0x07, (i >> 3) - 1
    return bits if shift == -1 else (bits | 0x08) << shift


_NUM_FREE_VALUES = 255 - _long_to_int4(2 ** 31 - 1)       # 24


def int_to_byte4(i: int) -> int:
    return i if i < _NUM_FREE_VALUES else _NUM_FREE_VALUES + _long_to_int4(i - _NUM_FREE_VALUES)


def byte4_to_int(b: int) -> int:
    return b if b < _NUM_FREE_VALUES else _NUM_FREE_VALUES + _int4_to_long(b - _NUM_FREE_VALUES)


# --------------------------------------------------------------------------- #
# Índice                                                                       #
# --------------------------------------------------------------------------- #
def construir(pasajes: list[dict]) -> dict:
    """Índice BM25 de los pasajes, en el orden dado (el canónico por id)."""
    ids, dl, tf, df = [], [], [], Counter()
    for p in pasajes:
        c = Counter(analizar(p["texto"]))
        ids.append(p["id"])
        dl.append(sum(c.values()))
        tf.append(sorted(c.items()))
        df.update(c.keys())
    doc_count = sum(1 for x in dl if x > 0)
    return {"formato": FORMATO, "analizador": ANALIZADOR, "lucene_version": LUCENE_VERSION,
            "sha256_stop": SHA256_STOP, "n_stop": len(STOP), "max_token": MAX_TOKEN,
            "k1": K1, "b": B, "n_docs": len(ids), "doc_count": doc_count,
            "sum_total_term_freq": sum(dl), "ids": ids, "dl": dl,
            "norma_byte": [int_to_byte4(x) for x in dl], "df": dict(sorted(df.items())), "tf": tf}


def serializar(indice: dict) -> bytes:
    """Bytes canónicos del índice (los que se persisten y se hashean)."""
    return json.dumps(indice, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_indice(indice: dict) -> str:
    return hashlib.sha256(serializar(indice)).hexdigest()


class Buscador:
    def __init__(self, indice: dict):
        if indice.get("formato") != FORMATO:
            raise ValueError(f"formato de índice desconocido: {indice.get('formato')!r}")
        self.ids = indice["ids"]
        self.k1, self.b = indice["k1"], indice["b"]
        self.doc_count = indice["doc_count"]
        self.avgdl = indice["sum_total_term_freq"] / self.doc_count
        self.df = indice["df"]
        self.largo = [byte4_to_int(x) for x in indice["norma_byte"]]
        self.post: dict[str, list[tuple[int, int]]] = {}
        for d, lista in enumerate(indice["tf"]):
            for t, f in lista:
                self.post.setdefault(t, []).append((d, f))

    def idf(self, t: str) -> float:
        df = self.df[t]
        return math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))

    def puntajes(self, terminos: list[str]) -> dict[int, float]:
        s: dict[int, float] = {}
        for t in terminos:
            if t not in self.post:
                continue
            w = self.idf(t)
            for d, f in self.post[t]:
                s[d] = s.get(d, 0.0) + w * f / (f + self.k1 * (1 - self.b + self.b * self.largo[d] / self.avgdl))
        return s

    def buscar(self, consulta: str, limite: int) -> list[tuple[int, float]]:
        s = self.puntajes(analizar(consulta))
        return sorted(s.items(), key=lambda kv: (-kv[1], self.ids[kv[0]]))[:limite]
