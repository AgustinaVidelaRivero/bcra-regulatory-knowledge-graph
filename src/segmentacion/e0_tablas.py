"""E0-tablas — parser de tablas del corpus (unidad B5.8.3; ejecuta la pieza 2
del scoping B5.6, `escalado_prep/scoping_b5_6_tabular_reginf.md` §4.2).

Módulo STANDALONE: no importa e0_lib ni toca ningún camino del chunker de
prosa. Produce la SEGMENTACIÓN tabular como hecho verificable (adenda B5.5
§2.2: segmentable ≠ extraíble); la extracción de este material no es de esta
etapa. La unidad tabular preserva estructura (filas/columnas): nunca se
linealiza a prosa — la linealización es exactamente el defecto RX-10
(`docs/backlog_reextraccion.md` §RX-10: los montos de capmin 1.2 quedaron
invertidos en el grafo porque el texto del chunk traía encabezados en un
orden y valores en otro).

Motor: pdfplumber `find_tables()` con settings por defecto (los mismos del
censo B5.8.0 y del scoping). Cada tabla lleva PROVENANCE completa: TO, página
(1-based), índice de tabla en la página (orden de `find_tables`), bbox.

REGLAS (cada una con su caso medido y sus contraejemplos):

R-TC — tabla de contenido (regla IDÉNTICA a la declarada y sellada por el
  censo B5.8.0 / scoping §1.4): ≥3 filas, ≥2 columnas, y bbox NO contenido
  íntegramente en el 12 % superior ni en el 10 % inferior de la página.
  Excluye el banner B.C.R.A. (1-2 filas en zona de título; capmin p.4 t0,
  ri_acsf p.1 t0) y el pie Versión/Comunicación/Vigencia/Página (1 fila,
  zona inferior). Retiene la tabla de montos de capmin p.4 (3×2) y las
  grillas 10-col de ri_acsf p.2-3. AGREGADO de esta unidad (medido en la
  corrida): una grilla cuyas celdas no contienen NINGÚN carácter es una
  caja de formulario/carátula, no una tabla de contenido — descarte
  `sin_contenido` (casos: manual p.2, ri2_pm p.1; sin esta regla ri2_pm
  «rendiría» con una caja vacía cuando su material real es ficha).

R-COL — guarda de alineación (lección RX-10; scoping §2.4: «el módulo debe
  detectar cuándo la geometría no determina la fila y negarse a emitir en
  vez de emitir mal»). Señal medida del colapso (ric p.8 t1: los 19
  ponderadores de la columna 3 en UNA celda con 18 saltos internos, el resto
  de la columna en None): una celda con ≥ MIN_FRAGMENTOS_COLAPSO fragmentos
  internos, ≥80 % de ellos numéricos cortos, en una columna con ≥50 % de sus
  restantes filas de datos vacías → la tabla se DECLARA
  `alineacion_no_confiable` y no se emite como parseada. Contraejemplos que
  NO disparan: 'Vigencia:\\n01/07/2021' (2 fragmentos), las 311 celdas de
  descripción envuelta de ri_laft (fragmentos largos no numéricos), el
  '3%\\n6%' de manual p.256 (2 fragmentos: fusión de filas lógicas, se
  DECLARA como celda multilínea numérica, no se rechaza).

R-COSTURA — grilla partida entre páginas (scoping §2.2: 38/43 tablas de
  ri_laft tocan borde). Dos segmentos consecutivos se cosen en UNA tabla
  lógica si: el primero termina a ≥ FRAC_FIN_COSTURA de su página, el
  segundo empieza a ≤ FRAC_INICIO_COSTURA de la siguiente, tienen el mismo
  número de columnas, Y alguna de las primeras 2 filas del segundo repite
  VERBATIM alguna de las primeras 2 del primero (título o encabezado
  repetido en la continuación — casos medidos: ri_laft p.5→6 'TABLA FORMA
  JURIDICA' + 'Código/Descripción', p.6→7 'TABLA PRODUCTO…'; ri_acsf p.2→3
  encabezado 'CÓDIGO/…/DESCRIPCIÓN/…'). Las filas repetidas quedan marcadas
  `filas_encabezado_repetido` (no son datos). Sin repetición verbatim la
  costura queda CANDIDATA declarada, nunca fusionada (fusionar sin evidencia
  es emitir mal: el pecado RX-10).

R-ENC — encabezado (conservador; solo señales fuertes, nada se recorta):
  título = fila inicial con exactamente 1 celda con texto seguida de una
  fila con ≥2 (caso 'TABLA FORMA JURIDICA'); filas de encabezado = filas
  iniciales con ≥2 celdas no numéricas cuando existe una fila posterior que
  arranca numérica (caso 'Código/Descripción'); fila envuelta = continuación
  con texto SOLO en columnas donde la fila de encabezado tiene hueco (caso
  medido 'Factor de ponde-'/'ración (en %)' de ric p.8). Si las señales no
  alcanzan: estado `no_determinado` — las filas originales viajan completas
  en el artefacto igual.

R-VERIF — reconstrucción verificable (decisión 4 del mandato): para cada
  segmento, el contenido de sus celdas se compara contra las palabras de la
  página cuyo centro cae dentro del bbox. La métrica del VEREDICTO es el
  multiconjunto de CARACTERES no blancos (robusta a tokenización: en ric
  p.20 el encabezado rotado de la planilla de derivados sale de
  extract_words letra por letra — 'D','e','s'… — mientras extract() de la
  tabla lo reconstruye entero; por tokens daría 89 % de pérdida falsa, por
  caracteres da 0). La diferencia por TOKENS se declara igual como
  informativa. Pérdidas y sobrantes se DECLARAN por tabla (nunca se
  silencian); pérdida de caracteres > UMBRAL_PERDIDA_NO_CONFIABLE → la
  tabla se declara `perdida_reconstruccion` y no se emite como parseada.

R-NOTA — notas al pie (scoping §2.3: caen fuera del bbox; ri_niif p.20):
  línea de texto hasta VENTANA_NOTA_PT debajo del bbox cuyo primer token es
  un marcador '(*)'/'(**)'/'(n)' presente en alguna celda → nota asociada a
  la tabla, con su texto y página.

Uso: USD 0, sin LLM, determinístico. `parsear_to(pdf_path, to)` devuelve el
artefacto completo del TO (tablas lógicas, costuras candidatas, descartes por
regla con conteos, verificación por tabla).
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

import pdfplumber

# R-TC — regla de tabla de contenido (sellada por el censo B5.8.0)
MIN_FILAS_TC = 3
MIN_COLS_TC = 2
FRAC_BANNER = 0.12
FRAC_PIE = 0.10

# R-COSTURA (calibrada: ri_laft 0.86→0.13 y 0.87→0.14; ri_acsf 0.83→0.20)
FRAC_FIN_COSTURA = 0.78
FRAC_INICIO_COSTURA = 0.25
FILAS_COMPARADAS_COSTURA = 2

# R-COL (calibrada: ric p.8 t1 = 19 fragmentos numéricos; contraejemplo
# 'Vigencia:\n01/07/2021' y '3%\n6%' = 2 fragmentos)
MIN_FRAGMENTOS_COLAPSO = 4
FRAC_NUMERICOS_COLAPSO = 0.8
LARGO_FRAGMENTO_CORTO = 8
FRAC_COLUMNA_VACIA = 0.5

# R-VERIF
UMBRAL_PERDIDA_NO_CONFIABLE = 0.20

# R-NOTA
VENTANA_NOTA_PT = 80.0
RE_MARCADOR_NOTA = re.compile(r"^\((\*{1,3}|\d{1,2})\)$")

RE_NUMERICO = re.compile(r"^(?=.*\d)[\d.,%()\-–/\s]+$")


# ------------------------------------------------------------------ básicos

def _texto(celda) -> str:
    return (celda or "").strip()


def _es_numerica(celda) -> bool:
    t = _texto(celda)
    return bool(t) and bool(RE_NUMERICO.match(t))


def _fila_norm(fila: list) -> tuple:
    return tuple(_texto(c) for c in fila)


def _fragmentos(celda) -> list[str]:
    return [f.strip() for f in _texto(celda).split("\n") if f.strip()]


# ------------------------------------------------------------------ R-TC

def clasificar_tabla_contenido(n_filas: int, n_cols: int, bbox, alto_pagina: float):
    """(es_contenido, motivo_descarte). Regla sellada del censo B5.8.0."""
    if n_filas < MIN_FILAS_TC:
        return False, "min_filas"
    if n_cols < MIN_COLS_TC:
        return False, "min_cols"
    if bbox[3] <= FRAC_BANNER * alto_pagina:
        return False, "banner_superior"
    if bbox[1] >= (1.0 - FRAC_PIE) * alto_pagina:
        return False, "pie_inferior"
    return True, None


# ------------------------------------------------------------------ R-COL

def detectar_colapso(filas: list[list], filas_datos_desde: int = 0):
    """Celda colapsada = los valores de una columna empaquetados en una sola
    celda multilínea numérica mientras el resto de la columna quedó vacío.
    Devuelve el detalle de la primera celda que dispara, o None."""
    if not filas:
        return None
    n_cols = max(len(f) for f in filas)
    for fi, fila in enumerate(filas):
        for ci, celda in enumerate(fila):
            frags = _fragmentos(celda)
            if len(frags) < MIN_FRAGMENTOS_COLAPSO:
                continue
            numericos = [f for f in frags
                         if len(f) <= LARGO_FRAGMENTO_CORTO and RE_NUMERICO.match(f)]
            if len(numericos) / len(frags) < FRAC_NUMERICOS_COLAPSO:
                continue
            resto = [f[ci] if ci < len(f) else None
                     for fj, f in enumerate(filas)
                     if fj != fi and fj >= filas_datos_desde]
            if not resto:
                continue
            vacias = sum(1 for c in resto if not _texto(c))
            if vacias / len(resto) >= FRAC_COLUMNA_VACIA:
                return {"fila": fi, "columna": ci, "fragmentos": len(frags),
                        "fragmentos_numericos": len(numericos),
                        "columna_vacia_pct": round(vacias / len(resto), 3)}
    return None


# ------------------------------------------------------------------ R-ENC

MAX_FILAS_ZONA_ENCABEZADO = 4


def _es_fila_titulo(fila: list) -> bool:
    """Fila con texto SOLO en la primera celda (casos medidos: 'TABLA FORMA
    JURIDICA' de ri_laft; contraejemplo: 'Factor de ponde-' de ric p.8 está
    en la última columna y es encabezado envuelto, no título)."""
    return bool(_texto(fila[0])) and sum(1 for c in fila if _texto(c)) == 1


def detectar_encabezado(filas: list[list]) -> dict:
    """Título y zona de encabezado por señales fuertes; `no_determinado` si
    no alcanzan. La ZONA DE ENCABEZADO son las filas previas a la primera
    fila de datos (la primera cuya primera celda con texto es numérica); sus
    textos se fusionan por columna en orden — eso reconstruye el encabezado
    envuelto en varias filas ('Factor de ponde-' + 'ración (en %)', ric p.8,
    scoping §2.3). Sin fila de datos numérica, o con zona más larga que
    MAX_FILAS_ZONA_ENCABEZADO, no se determina nada. No modifica las filas:
    solo describe."""
    out = {"titulo": None, "filas_titulo": 0, "filas_encabezado": 0,
           "columnas": None, "estado": "no_determinado"}
    if len(filas) < 2:
        return out
    i = 0
    if _es_fila_titulo(filas[0]) and sum(1 for c in filas[1] if _texto(c)) >= 2:
        out["titulo"] = _texto(filas[0][0])
        out["filas_titulo"] = 1
        i = 1
    fila_datos = None
    for j in range(i, len(filas)):
        primera = next((c for c in filas[j] if _texto(c)), None)
        if primera is not None and _es_numerica(primera):
            fila_datos = j
            break
    if fila_datos is None or fila_datos == i \
            or fila_datos - i > MAX_FILAS_ZONA_ENCABEZADO:
        if out["titulo"]:
            out["estado"] = "determinado"
        return out
    zona = filas[i:fila_datos]
    n_cols = max(len(f) for f in filas)
    cols = []
    for ci in range(n_cols):
        partes = [_texto(f[ci]) for f in zona if ci < len(f) and _texto(f[ci])]
        cols.append(" ".join(partes) if partes else None)
    if sum(1 for c in cols if c) < 2:
        if out["titulo"]:
            out["estado"] = "determinado"
        return out
    out["filas_encabezado"] = fila_datos - i
    out["columnas"] = cols
    out["estado"] = "determinado"
    return out


# ------------------------------------------------------------------ R-VERIF

def verificar_reconstruccion(palabras_pagina: list[dict], bbox, filas: list[list]) -> dict:
    """Contenido de las celdas vs palabras de la página con centro dentro del
    bbox. Veredicto por multiconjunto de CARACTERES no blancos (robusto a
    tokenización distinta: encabezados rotados salen de extract_words letra
    por letra); la diferencia por tokens se declara como informativa."""
    x0, y0, x1, y1 = bbox
    en_bbox = [w["text"] for w in palabras_pagina
               if x0 <= (w["x0"] + w["x1"]) / 2 <= x1
               and y0 <= (w["top"] + w["bottom"]) / 2 <= y1]
    pagina_tok = collections.Counter(en_bbox)
    celdas_tok = collections.Counter(
        t for fila in filas for c in fila for t in _texto(c).split())
    pagina_ch = collections.Counter(ch for t in en_bbox for ch in t)
    celdas_ch = collections.Counter(
        ch for fila in filas for c in fila for ch in _texto(c) if not ch.isspace())
    perdidos_ch = pagina_ch - celdas_ch
    extra_ch = celdas_ch - pagina_ch
    total_ch = sum(pagina_ch.values())
    perdidos_tok = pagina_tok - celdas_tok
    extra_tok = celdas_tok - pagina_tok
    return {
        "chars_pagina_bbox": total_ch,
        "chars_celdas": sum(celdas_ch.values()),
        "chars_perdidos": sum(perdidos_ch.values()),
        "chars_extra": sum(extra_ch.values()),
        "pct_perdida": round(sum(perdidos_ch.values()) / total_ch, 4) if total_ch else 0.0,
        "tokens_perdidos": sum(perdidos_tok.values()),
        "tokens_extra": sum(extra_tok.values()),
        "muestra_perdidos": [t for t, _ in perdidos_tok.most_common(8)],
        "muestra_extra": [t for t, _ in extra_tok.most_common(8)],
    }


# ------------------------------------------------------------------ R-NOTA

def notas_al_pie(palabras_pagina: list[dict], bbox, filas: list[list]) -> list[dict]:
    """Notas '(*)'/'(n)' inmediatamente bajo el bbox cuyo marcador aparece en
    alguna celda de la tabla."""
    marcadores_en_celdas = set()
    for fila in filas:
        for c in fila:
            for m in re.findall(r"\((?:\*{1,3}|\d{1,2})\)", _texto(c)):
                marcadores_en_celdas.add(m)
    if not marcadores_en_celdas:
        return []
    y1 = bbox[3]
    debajo = [w for w in palabras_pagina
              if y1 < (w["top"] + w["bottom"]) / 2 <= y1 + VENTANA_NOTA_PT]
    lineas: list[tuple[float, list[dict]]] = []
    for w in sorted(debajo, key=lambda w: (w["top"], w["x0"])):
        if lineas and abs(lineas[-1][0] - w["top"]) <= 3.0:
            lineas[-1][1].append(w)
        else:
            lineas.append((w["top"], [w]))
    notas: list[dict] = []
    for _, ws in lineas:
        ws = sorted(ws, key=lambda w: w["x0"])
        primero = ws[0]["text"]
        if RE_MARCADOR_NOTA.match(primero) and primero in marcadores_en_celdas:
            notas.append({"marcador": primero,
                          "texto": " ".join(w["text"] for w in ws)})
        elif notas:
            notas[-1]["texto"] += " " + " ".join(w["text"] for w in ws)
    return notas


# ------------------------------------------------------------------ R-COSTURA

def _match_costura(seg_prev: dict, seg_nuevo: dict) -> list[int]:
    """Índices de filas iniciales del segmento nuevo que repiten verbatim
    filas iniciales del PRIMER segmento de la tabla lógica (título o
    encabezado repetido en la continuación). GUARDA: si el segmento nuevo
    trae fila de título propia y su texto difiere del título del primero,
    NO hay costura aunque el encabezado genérico coincida — dos tablas
    distintas comparten 'Código/Descripción' (ri_laft: TABLA PROVINCIA
    tras TABLA FORMA JURIDICA); coserlas sería emitir mal (RX-10)."""
    f_prev, f_nuevo = seg_prev["filas"], seg_nuevo["filas"]
    if (f_prev and f_nuevo and _es_fila_titulo(f_prev[0])
            and _es_fila_titulo(f_nuevo[0])
            and _texto(f_prev[0][0]) != _texto(f_nuevo[0][0])):
        return []
    previas = [_fila_norm(f) for f in f_prev[:FILAS_COMPARADAS_COSTURA]]
    repetidas = []
    for i, fila in enumerate(f_nuevo[:FILAS_COMPARADAS_COSTURA]):
        if _fila_norm(fila) in previas:
            repetidas.append(i)
    return repetidas


# ------------------------------------------------------------------ por TO

def parsear_to(pdf_path: Path, to: str) -> dict:
    """Corre el parser completo sobre un TO. Devuelve el artefacto del TO:
    tablas lógicas con provenance y verificación, costuras candidatas no
    fusionadas, descartes por regla (conteos + muestras)."""
    tablas_logicas: list[dict] = []
    costuras_candidatas: list[dict] = []
    descartes = collections.Counter()
    muestras_descarte: list[dict] = []
    paginas_con_tc = 0
    n_paginas = 0

    with pdfplumber.open(str(pdf_path)) as pdf:
        n_paginas = len(pdf.pages)
        abierta: dict | None = None    # tabla lógica candidata a continuar
        for pi, page in enumerate(pdf.pages, start=1):
            alto = float(page.height)
            palabras = page.extract_words()
            tablas_pag = page.find_tables()
            hubo_tc = False
            for ti, tb in enumerate(tablas_pag):
                filas = tb.extract()
                n_filas = len(filas)
                n_cols = max((len(f) for f in filas), default=0)
                es_tc, motivo = clasificar_tabla_contenido(
                    n_filas, n_cols, tb.bbox, alto)
                if es_tc and not any(_texto(c) for f in filas for c in f):
                    es_tc, motivo = False, "sin_contenido"
                if not es_tc:
                    descartes[motivo] += 1
                    if len(muestras_descarte) < 12:
                        muestras_descarte.append({
                            "pagina": pi, "indice_en_pagina": ti,
                            "motivo": motivo, "n_filas": n_filas,
                            "n_cols": n_cols,
                            "primera_celda": _texto(filas[0][0]) if filas and filas[0] else ""})
                    continue
                hubo_tc = True
                seg = {
                    "pagina": pi,
                    "indice_en_pagina": ti,
                    "bbox": [round(v, 1) for v in tb.bbox],
                    "frac_inicio": round(tb.bbox[1] / alto, 3),
                    "frac_fin": round(tb.bbox[3] / alto, 3),
                    "n_filas": n_filas,
                    "n_cols": n_cols,
                    "filas": filas,
                    "filas_encabezado_repetido": [],
                    "verificacion": verificar_reconstruccion(palabras, tb.bbox, filas),
                    "notas_pie": notas_al_pie(palabras, tb.bbox, filas),
                }
                # ¿continúa la tabla lógica abierta?
                if abierta is not None:
                    ult = abierta["segmentos"][-1]
                    geometria = (ult["pagina"] == pi - 1
                                 and ult["frac_fin"] >= FRAC_FIN_COSTURA
                                 and seg["frac_inicio"] <= FRAC_INICIO_COSTURA
                                 and ult["n_cols"] == seg["n_cols"])
                    if geometria:
                        repetidas = _match_costura(abierta["segmentos"][0], seg)
                        if repetidas:
                            seg["filas_encabezado_repetido"] = repetidas
                            abierta["segmentos"].append(seg)
                            continue
                        costuras_candidatas.append({
                            "tabla_previa": abierta["id"],
                            "pagina": pi, "indice_en_pagina": ti,
                            "motivo": "geometria_sin_encabezado_repetido"})
                nueva = {"id": f"{to}::tabla{len(tablas_logicas):03d}",
                         "segmentos": [seg]}
                tablas_logicas.append(nueva)
                abierta = nueva
            if hubo_tc:
                paginas_con_tc += 1
            else:
                # una página sin tabla de contenido corta cualquier costura
                abierta = None

    # consolidación por tabla lógica: encabezado, guardas, estado
    for t in tablas_logicas:
        seg0 = t["segmentos"][0]
        t["n_cols"] = seg0["n_cols"]
        t["encabezado"] = detectar_encabezado(seg0["filas"])
        causas = []
        colapsos = []
        for s in t["segmentos"]:
            d = detectar_colapso(s["filas"])
            if d:
                d["pagina"] = s["pagina"]
                colapsos.append(d)
        if colapsos:
            causas.append("alineacion_no_confiable")
        pct_max = max(s["verificacion"]["pct_perdida"] for s in t["segmentos"])
        if pct_max > UMBRAL_PERDIDA_NO_CONFIABLE:
            causas.append("perdida_reconstruccion")
        celdas = [c for s in t["segmentos"] for f in s["filas"] for c in f]
        multi = [c for c in celdas if _texto(c).count("\n") >= 1]
        t["declaraciones"] = {
            "celdas_total": len(celdas),
            "celdas_vacias": sum(1 for c in celdas if not _texto(c)),
            "celdas_multilinea": len(multi),
            "celdas_multilinea_numericas": sum(
                1 for c in multi
                if all(RE_NUMERICO.match(f) for f in _fragmentos(c))),
            "colapsos": colapsos,
            "pct_perdida_max": pct_max,
            "chars_perdidos_total": sum(
                s["verificacion"]["chars_perdidos"] for s in t["segmentos"]),
            "chars_extra_total": sum(
                s["verificacion"]["chars_extra"] for s in t["segmentos"]),
            "tokens_perdidos_total": sum(
                s["verificacion"]["tokens_perdidos"] for s in t["segmentos"]),
            "tokens_extra_total": sum(
                s["verificacion"]["tokens_extra"] for s in t["segmentos"]),
        }
        t["estado"] = "declarada" if causas else "parseada"
        t["causas"] = causas

    parseadas = [t for t in tablas_logicas if t["estado"] == "parseada"]
    filas_total = sum(s["n_filas"] for t in tablas_logicas for s in t["segmentos"])
    return {
        "to": to,
        "archivo": pdf_path.name,
        "paginas": n_paginas,
        "tablas_logicas": tablas_logicas,
        "costuras_candidatas": costuras_candidatas,
        "descartadas_por_regla": {"conteos": dict(descartes),
                                  "muestras": muestras_descarte},
        "conteos": {
            "tablas_logicas": len(tablas_logicas),
            "parseadas": len(parseadas),
            "declaradas": len(tablas_logicas) - len(parseadas),
            "segmentos": sum(len(t["segmentos"]) for t in tablas_logicas),
            "costuras_aplicadas": sum(len(t["segmentos"]) - 1 for t in tablas_logicas),
            "costuras_candidatas": len(costuras_candidatas),
            "filas_total": filas_total,
            "paginas_con_tabla_contenido": paginas_con_tc,
            "notas_pie": sum(len(s["notas_pie"]) for t in tablas_logicas
                             for s in t["segmentos"]),
            "rinde": bool(parseadas),
        },
    }
