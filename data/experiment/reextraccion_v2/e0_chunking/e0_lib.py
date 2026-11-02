"""E0 — Chunking estructural determinístico (issue #9, diseño docs/diseno_reextraccion_v2.md §3-E0).

Deriva la estructura normativa de cada TO desde el CUERPO del PDF (nunca del
índice): puntos numerados jerárquicos x.y.z…, secciones, y prosa sin numerar
(chapeaus de sección, intros y cierres de punto) ANCLADA a su contenedor por
indentación. El índice se parsea por separado y solo se usa como contraste
(reporte de divergencias); no gobierna ningún corte.

Señal estructural central: la columna x0 de cada línea. En los TOs del BCRA la
escalera de indentación es estable (≈35pt por nivel): el label de un punto de
profundidad d arranca en la columna c_d, y su texto corre en c_{d+1}. Un
párrafo sin numerar cuya x0 coincide con la columna de texto de un ANCESTRO
del punto abierto es un cierre/intersticial de ese ancestro, no una
continuación del punto profundo (caso documentado: cierres del 2.7 de Exterior
y Cambios en x0≈104.9 = columna de texto del nivel 2, mientras la continuación
de 2.7.x corre en ≈140.3).

Validación de headers de punto (mata los falsos headers RX-03 de
docs/backlog_reextraccion.md): un candidato "N.N.…" solo abre punto si
(a) su primer componente es el número de la sección corriente,
(b) su padre está abierto y el último componente supera al último hermano
    visto (los saltos se aceptan y se REPORTAN, los duplicados se rechazan),
(c) su x0 es compatible con la escalera de columnas del TO (±TOL_X pt).
Todo candidato rechazado queda registrado con su motivo (nada se descarta en
silencio).

Correcciones post-parseo (dos reglas de principio, aplicadas sobre el árbol ya
construido, en este orden):

REGLA 1 — continuidad de enumeración en costuras: un segmento clasificado
intersticial de un padre, cuyo primer marcador de enumeración (romanos,
letras, números — 'vii)', 'h)', '3)') continúa la secuencia con la que termina
el texto propio del hermano terminal inmediatamente anterior, se reasigna como
continuación del texto propio de ese hermano; las líneas envueltas del ítem
(sin marcador, en columna más profunda que la del marcador) lo siguen. Caso
medido: los acápites vii)–x) de pro 2.3.1.1, que la deriva de columnas de la
p.9 hacía re-anclar como intersticiales de 2.3.1. Ver
`aplicar_continuidad_enumeracion` (detector de secuencias y límites en su
docstring).

REGLA 2 — cero cortes intra-palabra: ninguna frontera de segmento puede caer
en una palabra partida por guion de fin de línea ('presta-' / 'ciones…'): la
frontera se corre línea por línea hasta cerrar la palabra. Solo se corrige
DÓNDE cae la frontera; el des-silabeo del texto sigue siendo decisión de E1.
Ver `corregir_fronteras_intra_palabra` (detector y exclusiones en su
docstring).

MINI-CHUNKS (enmienda 01, docs/enmienda_01_diseno_reextraccion_v2.md §2.a):
los bloques estructurales de los nodos NO terminales (chapeau de sección,
intro, intersticial, cierre) se emiten además como unidades de extracción de
primera clase. Criterio de materialización (letra de §2.a): un bloque se
materializa si y solo si contiene texto además de su línea de título — los
tramos `encabezado` son la línea de label y tras descontarla no queda nada
(jamás materializan); los segmentos de prosa no contienen la línea de label y
materializan siempre que su texto normalizado no sea vacío. La heurística de
escala de la enmienda (una línea ≤140 chars ≈ título) queda descartada como
criterio: excluiría intros normativos de una línea (caso pro 2.7,
'deberán contar con sendos hipervínculos…'). Invariante resultante: todo
bloque de prosa de un ancestro con texto no vacío tiene exactamente un
responsable de extracción (su mini-chunk).

Agrupado: los segmentos intro (y el chapeau de sección) de una unidad son
contiguos por construcción (todos antes del primer hijo), ídem los cierre
(después del último); cada grupo se funde en UN mini-chunk — evita fragmentar
fórmulas y colas envueltas que el parser separó por cambio de columna. Los
intersticiales viven en huecos distintos entre hijos: uno por segmento, con
sufijo ::<n> (orden documental) cuando hay más de uno del mismo rol.
Id determinístico: <to>::<unidad_origen>::<rol>[::<n>] — función de la unidad
de origen y el rol documental, nunca del orden de emisión. Emisión
interleaved en orden documental: intro antes de los hijos, intersticial en su
hueco, cierre después. Ver `construir_chunks`.

MODO DE LECTURA SIN RAÍZ DE SECCIÓN (unidad B5.8.1, diseño
docs/diseno_B5.8_segmentacion_universal.md §2): para los TOs cuyo camino
vigente produce CERO unidades (compuerta de rol de página cerrada por falta
de índice — familia a del censo B5.8.0 — o cuerpo sin ninguna línea
'Sección N.' — familia c), `parsear_cuerpo(..., modo_sin_raiz=True)` deriva
la raíz de lectura de la propia espina de puntos:

  * raíz EXPLÍCITA: un label de profundidad 1 ('N. Título') abre un nodo
    sección sintético N, con cuatro guardas ancladas a casos medidos del
    censo: (G0) no es un banner repetido de encabezado (línea numerada que
    se repite en la zona de título de ≥MIN_PAGS_BANNER páginas: el
    «17. BASE DE DATOS PADRÓN» de ri_bdp encabeza las 3 páginas y no es
    espina); (G1) el resto tiene forma de título (arranca en mayúscula:
    rechaza la referencia envuelta '1. de las normas sobre…'); (G2)
    monotonía estricta (N mayor que la última raíz/sección abierta: los
    ítems '1.'/'2.' de las listas internas de ri_cr reinician numeración y
    quedan rechazados; los saltos hacia adelante se aceptan y se REPORTAN);
    (G3) columna no más profunda que la de las raíces ya aceptadas
    (las enumeraciones internas corren a la derecha del margen de raíz).
  * raíz IMPLÍCITA: un label de profundidad 2 con forma de título cuyo
    primer componente no coincide con la raíz abierta (arranque medido de
    ri_niif: '2.1. Disposiciones generales…' sin ningún '2.' previo) abre
    la sección sintética de su componente raíz, bajo las mismas guardas de
    monotonía y columna; profundidad ≥3 jamás abre raíz (la referencia
    envuelta medida de ri_dsf p.1 '2.1.4. de las normas…' queda rechazada).
  * PREÁMBULO: el contenido previo a la primera raíz se ancla a un nodo
    sección sintético '0' (título 'Preámbulo') — nada queda huérfano y la
    cobertura de cero pérdida se sostiene.
  * PÁGINAS DE REGISTRO: una página de cuerpo cuya densidad de líneas
    ficha/código supera DENS_REGISTRO_MIN pasa al rol `ficha_registro` y
    queda FUERA del parseo de prosa, declarada en los roles (cuerpos
    ficha/lista de manual y ri2_pm — decisión 3 del mandato B5.8.1 — y
    páginas de listado de códigos de ri_laft; su destino es el parser de
    registros/tablas, no la espina).

GARANTÍA ESTRUCTURAL DE NO-CAMBIO: el modo se activa SOLO en los call
sites que comprobaron cero unidades por el camino vigente
(healthcheck_e0 y el runner de B5.8.1); con `modo_sin_raiz=False` (el
default de todos los call sites vigentes) ninguna rama nueva se ejecuta.

REGLAS DE MARCADOR POR FAMILIA (unidad B5.8.2; censo B5.8.0 familias
b_idx/b_sec): `marcadores_b582=True` (parámetro de `clasificar_paginas`,
`parsear_cuerpo` y `parsear_indice`; False por default en todos los call
sites vigentes) habilita las variantes de marcador MEDIDAS en el censo:

  * MARCADOR DE ÍNDICE (RE_MARCA_INDICE_B582; misma guarda de tres capas
    que B5.2 — línea entera, mayúscula inicial estricta, zona de título
    POS_MARCA_INDICE): 'INDICE'/'ÍNDICE' en mayúsculas sostenidas
    (nmaeef p.1, ri_dcpc p.1-2, ri_msrl p.1, ri_psp p.1), 'Índice -' con
    guion solo a la derecha (consyr p.2) y '– Índice –' con guion largo
    (seguef p.2). Contraejemplos medidos que NO matchean: '3.7.2. Indice
    a utilizar' (ri_dcpc p.24: numeración adelante, no es línea-marcador),
    la prosa de ri_dcpc p.10 ('…actualizables por algún índice.') y la
    línea envuelta 'índice' en minúscula del cuerpo de cap (B5.2). La
    heurística de continuación de índice (n_secc >= 2) NO se extiende a
    las variantes: en ri_dcpc p.3 el encabezado 'SECCION 1 – MARCO
    CONTABLE' aparece DOS veces en la zona de título y la página de
    cuerpo se clasificaría índice (contraejemplo medido).
  * ENCABEZADO DE SECCIÓN VARIANTE (solo capturado en la zona de
    encabezado de página, igual que el vigente): 'SECCION/SECCIÓN
    <n|romano> – Título' en mayúsculas (RE_SECCION_B582_CAPS; ri_dcpc
    'SECCION 1 - MARCO CONTABLE', ri_psp 'SECCIÓN I – INSTRUCCIONES
    GENERALES') y 'Sección <letra|romano> [.:-–] Título' (RE_SECCION_
    B582_LETRA; reqcac 'Sección A – Introducción' en cuerpo y 'Sección
    A. Introducción' en índice; ri_psp índice 'Sección I – …'). El
    número de sección queda VERBATIM ('C', 'I'); la continuidad se
    evalúa por familias de interpretación (letra/romano/número:
    reqcac A→B→C sin saltos aun siendo C también romano; ri_psp IV→VI
    con salto_seccion reportado) y los puntos bajo una sección no
    numérica quedan rechazados como fuera_de_seccion (registrados,
    nunca en silencio). La cola envuelta de título queda DESACTIVADA
    para secciones matcheadas por variante: los títulos medidos caben
    en una línea, y en reqcac p.3 la prosa inmediata (interlineado
    < GAP_TOP_TITULO) se pegaría al título. Contraejemplos que NO
    matchean: 'Sección Punto Párrafo Com. Anexo…' (seguef p.19: sin
    separador tras el token) y 'la sección 4…' (remisión en prosa,
    minúscula — guarda heredada del vigente).
  * BANNER DE PÁGINA DE CAJA MIXTA (detectar_banners_texto): una línea
    de la zona de título repetida VERBATIM en >=MIN_PAGS_BANNER páginas
    se descarta como encabezado (reqcac p.2-10: 'Requisitos Operativos
    Mínimos…' / 'Casas y Agencias de Cambio' — sin este descarte el
    escaneo de encabezado corta en la primera línea mixta y nunca llega
    a la línea de sección). El chequeo de sección corre ANTES del
    descarte: 'SECCION 3 – CRITERIOS GENERALES' se repite en 20 páginas
    de ri_dcpc y ES el encabezado corrido de su sección.

  Misma garantía estructural que B5.8.1: los call sites (healthcheck_e0
  y el runner de B5.8.2) solo pasan `marcadores_b582=True` tras
  comprobar cero unidades por el camino vigente; con el default False
  ninguna rama nueva se ejecuta. Casos medidos protegidos por la
  compuerta: ri_pspapt y ri_psprca (familia a, secundaria b_sec) llevan
  'SECCION <romano> –' en zona de título, pero sin página de índice
  ninguna página llega a cuerpo en la etapa de marcadores y su camino
  sigue siendo el de B5.8.1, byte-idéntico.

VERSIÓN e0-r2, U-R2-CODIGO-2 (C2). Cuatro cambios que rigen solo en los
call sites de e0-r2 (correr_e0.escalera_e0_r2, procesar_tablas_r2 y
subdividir_unidades_grandes con su tope); con los defaults ninguna rama
nueva se ejecuta y la E0 legada queda byte-idéntica:
  * renumeración por lista (`parsear_cuerpo(renumeraciones=…)`): un
    encabezado de punto cuyo (TO, página, número impreso) está en la lista
    abre el punto con el número corregido; el aviso `renumerado_por_lista`
    y el nodo (`numero_impreso`) guardan el número impreso, y el chunk lo
    declara en sus flags (`numero_impreso`, `correccion_numeracion`). Caso
    único: la p. 16 de ric imprime 4.3, 4.3.1 y 4.3.2 donde la norma sigue
    con 4.4, 4.4.1 y 4.4.2 (las citas a 4.4.1 y 4.4.2 y los encabezados
    4.4.3 y 4.4.4 de la p. 18);
  * cola de título estricta, en las páginas de una lista explícita
    (`parsear_cuerpo(cola_titulo_estricta=…)`; `separar_encabezado_pie`):
    el renglón que sigue a la línea de sección solo es la cola envuelta del
    título si el título no terminó (sin punto final) y el renglón lo
    continúa (empieza en minúscula, o el título termina en guion, coma o una
    palabra de PALABRAS_QUE_CONTINUAN_TITULO); si no, es texto de la norma
    («De corresponder, la exigencia…» en la p. 15 de ric). La lista son las
    pp. 15, 30, 54 y 59 de ric: aplicada a toda página, la regla también
    recupera texto de la norma en 7 TOs de la partición de 152, pero en
    snp_cheq cambia la segmentación del 7.1 (un id nuevo) y en fabcra una
    tabla deja de serializarse, y los cambios de E0 que mueven ids de la
    partición no son de esta unidad (r2_codigo2/freno_c2.md);
  * tope de la herencia (`construir_chunks(tope_herencia=(U, B))` y
    `recortar_herencia`): la unidad cuya herencia pasa U caracteres
    conserva los títulos de todos los ancestros y, de cada bloque de prosa
    heredado, el extremo cercano a la unidad hasta B caracteres más; lo
    omitido se reemplaza por una línea marcador y el chunk lo declara en
    `herencia_recortada`;
  * pies de página (`pies_de_paginas`): la versión de la hoja, la
    Comunicación, la hoja y la fecha de vigencia que trae el pie de cada
    página, leído con el mismo criterio con que e0-r2 lo recorta, y la
    versión vigente del TO.

U-SEG-OFICIAL, S0-4 (solo e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_4/). Seis reglas, cada
una detrás de su parámetro, apagado por default: sub-documento (`limites_subdocumento` y
`parsear_cuerpo(subdocumentos=…)`), la guarda de columna dentro de un sub-documento (`g3_subdoc`), la raíz mayor que
MAX_RAIZ dentro de un sub-documento (`raiz_max_subdoc`, S0-4a-bis), oración tomada como título
(`construir_chunks(oracion_titulo_4a=…)`), título envuelto (`titulo_envuelto_4b`) y apartados de una sección sin
puntos (`apartados_seccion`). El mecanismo 4 de S0-3 (intro desde el rótulo en todo punto cuyo título no
termina en punto) no está: lo reemplazan 4a y 4b.

U-SEG-OFICIAL, S0-5a (solo e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_5/). Seis reglas de corte,
cada una detrás de su parámetro, apagado por default: el cierre al margen del último ítem de una lista
(`aplicar_cierre_al_margen(cierre=…)`, R5-a) y el título de bloque que sigue al último ítem (`titulo_bloque`, R5-a′),
sobre las listas del detector del hallazgo 1.16 (`listas_116`); las intersticiales que continúan la anterior
(`construir_chunks(intersticial_continuado=…)`, R5-b); el título de sección de dos renglones
(`titulo_seccion_envuelto`, R5-c); el número de punto que sigue a una palabra de referencia
(`parsear_cuerpo(numero_en_referencia=…)`, R5-d), y las letras de un rótulo vertical (`juntar_rotulo_vertical`, R5-e,
sobre el árbol).

U-SEG-OFICIAL, S0-5a-bis (solo e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_5/bis/). R5-a por lista
(`aplicar_cierre_al_margen(listas=…)`): solo los últimos ítems de las listas dadas, sin el detector como alcance, con
el criterio de párrafos de S0-5a o con un rango explícito de renglones; R5-a no mueve renglones de tablas
(`excluir=…`). Y los rótulos de punto por lista (`parsear_cuerpo(rotulos_por_lista=…)`, R5-f): un renglón dado por su
página y su altura abre su punto aunque el número esté pegado al texto, empiece en minúscula o su padre no esté abierto.
Y la raíz por lista (`parsear_cuerpo(raices_por_lista=…)`, R5-g, en el modo sin raíz): un renglón dado por su página y su
altura abre su raíz aunque esté más adentro que la columna de las raíces (guarda G3).

U-SEG-OFICIAL, S0-6a (solo e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_6/). Once reglas generales,
cada una detrás de su parámetro, apagado por default, o de una función sobre el árbol: títulos sin número
(`dividir_a`, A, y `limites_subdocumento(solo_anexo=…)`); encabezado de un punto con hijos
(`construir_chunks(encabezado_b=…)`, B); párrafo sin número por su columna (`asignar_por_columna_c`, C); rótulo
heredado tal como está impreso (`construir_chunks(rotulo_impreso_d=…)`, D); y, en `parsear_cuerpo`, la raíz que
continúa la numeración (`raiz_sucesora_e`, E), el encabezado de columnas reimpreso (`encabezado_tabla_f`, F1; F2 es
`mover_encabezado_tabla_f`), el número partido (`numero_partido_g`, G), el número sin espacio (`numero_pegado_h`, H), el
recuadro de dos columnas (`recuadro_i`, I), la carátula (`caratula_j`, J) y el pie de formulario
(`separar_encabezado_pie(pie_formulario_k=…)`, K). Cada regla está descrita en el comentario de su constante.

U-SEG-OFICIAL, S0-6a-bis (solo e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_6/bis/). Dos reglas más,
también detrás de su parámetro: el índice leído como cuerpo, que no corta la sucesión de números (`lineas_de_indice_l` y
`parsear_cuerpo(indice_l=…)`, L), y la raíz 0 de un sub-documento que abre A, que aporta a la herencia solo su título
(`construir_chunks(raiz0_solo_titulo_m=…)`, M). Y dos ajustes: C no mueve un párrafo cuyos renglones no comparten
columna, mide el párrafo por la columna que comparten y no toca las listas que siguen en R5-a
(`asignar_por_columna_c(listas_fijas=…)`); A no abre divisiones en la carátula (`ResultadoParseo.paginas_caratula_a`).

Sin llamadas a LLM: código determinístico puro.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

# ---------------------------------------------------------------- constantes

TO_KEYS = {
    "TO_capitales_minimos_actual.pdf": "cap",
    "TO_clasificacion_deudores_actual.pdf": "cla",
    "TO_exterior_cambios_actual.pdf": "ext",
    "TO_proteccion_usuarios_servicios_financieros_actual.pdf": "pro",
    "TO_regimen_informativo_contable_mensual_actual.pdf": "ric",
}

TOL_X = 3.0          # tolerancia de coincidencia de columnas (pt)
TOL_TOP = 2.0        # tolerancia de agrupamiento vertical de palabras en línea (pt)
GAP_COL = 15.0       # hueco horizontal mínimo (pt) para contar frontera de columna (tablas)

RE_MARCA_INDICE = re.compile(r"^-\s*[ÍI]ndice\s*[-–]?\s*$", re.IGNORECASE)
# Variante SIN guiones del marcador de índice (B5.2; el subset solo usa la
# forma con guiones). GUARDA contra falsos marcadores, en tres capas:
# (1) línea entera — la palabra sola, sin prosa alrededor ni puntuación
#     final: la mención en prosa ('… actualizables por algún índice.',
#     medida en el corpus de escalado) no matchea;
# (2) mayúscula inicial ESTRICTA (sin IGNORECASE): la línea envuelta
#     'índice' en minúscula existe en el cuerpo de cap y con case-insensitive
#     reclasificaría esa página como índice, perdiendo su contenido;
# (3) posición de título — solo cuenta dentro de las primeras
#     POS_MARCA_INDICE líneas de la página (los 11 marcadores con guiones
#     medidos en el subset caen todos en las primeras 4).
RE_MARCA_INDICE_SIN_GUIONES = re.compile(r"^[ÍI]ndice$")
POS_MARCA_INDICE = 5
MARCA_TABLA_ORIGEN = "NORMA DE ORIGEN"
MARCA_HISTORIAL = "historial de la norma"
# separador del header de sección: punto (todo el subset) o dos puntos
# (variante de escritura del corpus de escalado, B5.2). 'Secci[oó]n' queda
# case-sensitive a propósito: las remisiones en prosa ('la sección 4…') no
# abren sección.
RE_SECCION = re.compile(r"^Secci[oó]n\s+(\d+)\s*[.:]\s*(.*)$")
RE_SECCION_EN_LINEA = re.compile(r"Secci[oó]n\s+(\d+)\s*[.:]\s*(.*)$")
GAP_TOP_TITULO = 16.0   # separación vertical máxima (pt) de la cola envuelta de un título de sección
# e0-r2 (U-R2-CODIGO-2): palabras finales de un título que lo dejan abierto a una cola en mayúscula
# («Régimen de Incentivo para» / «Grandes Inversiones (RIGI).»).
PALABRAS_QUE_CONTINUAN_TITULO = frozenset({"a", "al", "con", "como", "de", "del", "e", "el", "en", "entre", "la",
                                          "las", "los", "o", "para", "por", "que", "sin", "sobre", "su", "sus",
                                          "u", "y"})
RE_NUM_TOKEN = re.compile(r"^(\d+(?:\.\d+)*)\.$")   # primer token de un header de punto
# el BCRA a veces omite el punto final del label ('13.4.1 el pago…',
# '8.5.14.1 la norma…' — medidos en ext p.172 y p.117): se admite numeración
# sin punto final solo con profundidad ≥2 (un entero solo nunca es label)
RE_NUM_TOKEN_SIN_PUNTO = re.compile(r"^(\d+(?:\.\d+)+)$")
# título de sección repetido en el cuerpo con numeración de un nivel
# ('3.INSTRUCCIONES OPERATIVAS.', '6. TRANSACCIONES Y MENSAJES.'): en e0-r2
# (K-b) se descarta en la zona de encabezado aunque no se repita en otra página
RE_TITULO_SECCION_NUMERADO_K = re.compile(r"^\d{1,2}\.\s*[^\d\s.]")
RE_PIE = [
    re.compile(r"^Vigencia:?$"),
    re.compile(r"^Versi[oó]n:.*P[aá]gina\s+\d+"),
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$"),
    re.compile(r"^P[aá]gina\s+\d+$"),
]
RE_NUMERICO = re.compile(r"^-?[\d.,]+%?$")
# Pie desde la línea «Versión» (solo la versión e0-r2, U-R2-CODIGO; ver
# separar_encabezado_pie): la línea de versión del pie y todo lo que la sigue
# en la página son pie, si está entre las últimas VENTANA_PIE_VERSION líneas.
RE_PIE_VERSION = re.compile(r"^Versi[oó]n\s*:.*Comunicaci[oó]n", re.I)
VENTANA_PIE_VERSION = 3

MAX_RAIZ = 30        # un primer componente mayor es cita de Comunicación, no punto

# --------- modo de lectura sin raíz de sección (B5.8.1; ver docstring) ---------
# Campos de ficha de registro: formas medidas en manual (scoping U-B5.6-0 §1.4,
# 'Capítulo/Rubro/Imputación…' con inicial mayúscula) y en ri2_pm p.50/120/300
# ('CAPITULO ACTIVO', 'SUB-RUBRO … Código', 'IMPUTACION …', sostenidas).
RE_FICHA_REGISTRO = re.compile(
    r"^(Cap[ií]tulo|CAP[IÍ]TULO|Rubro|RUBRO|SUB-?RUBRO|Moneda|MONEDA|RESIDENCIA"
    r"|Otros Atributos|OTROS ATRIBUTOS|Imputaci[oó]n|IMPUTACI[OÓ]N|Incluye|INCLUYE)\b")
# fila de lista de códigos cortos (scoping §1.4: plandecuentas '311106 Cuentas
# corrientes…'; mismas filas medidas en ri_laft p.13-20)
RE_LISTA_CODIGO = re.compile(r"^\d{6}(?:\.\d+)?\s+\D")
# código de cuenta largo del plan/manual de ri2_pm (medidos: '102011ARS0000101',
# '3060000000000001'); se busca en cualquier posición (aparece fusionado al
# final de la fila: 'Títulos públicos - Con cotización 102011ARS0100101')
RE_CODIGO_CUENTA = re.compile(r"(?<![\dA-Z])\d{6}(?:[A-Z]{3}|\d{3})\d{7}(?![\dA-Z])")
DENS_REGISTRO_MIN = 0.30   # fracción de líneas ficha/código que vuelca la página
                           # (medido: cuerpo de manual 0,32-0,91; su preámbulo 0,00-0,11)
MIN_PAGS_BANNER = 3        # una línea numerada de zona de título repetida en esta
                           # cantidad de páginas es banner de encabezado, no espina
POS_ZONA_BANNER = 6        # zona de detección de banners (líneas iniciales de página)
# forma de título de una raíz (guarda G1): misma clase que el chequeo de
# `titulo_mayuscula` del parser vigente
RE_TITULO_RAIZ = re.compile(r'^[A-ZÁÉÍÓÚÜÑ"“\'(«]')

# --------- reglas de marcador por familia (B5.8.2; ver docstring) ---------
# Variantes de marcador de índice MEDIDAS (censo B5.8.0, familia b_idx):
# mayúsculas sostenidas ('INDICE' nmaeef p.1 / ri_dcpc p.1-2 / ri_psp p.1,
# 'ÍNDICE' ri_msrl p.1), guion solo a la derecha ('Índice -' consyr p.2) y
# guion largo a ambos lados ('– Índice –' seguef p.2). Línea entera y
# mayúscula inicial ESTRICTA (sin IGNORECASE), como la guarda B5.2; la capa
# posicional (POS_MARCA_INDICE) la aplican los call sites.
RE_MARCA_INDICE_B582 = re.compile(
    r"^(?:[ÍI]NDICE|[ÍI]ndice\s*[-–—]|[–—]\s*[ÍI]ndice\s*[-–—]?)$")
# Encabezado de sección variante (censo familias b_idx/b_sec). CAPS: separador
# guion/guion largo, número arábigo (ri_dcpc 'SECCION 1 - MARCO CONTABLE') o
# romano (ri_psp 'SECCIÓN I – INSTRUCCIONES GENERALES'); el separador [.:] en
# mayúsculas no está medido y queda fuera. LETRA: 'Sección' con inicial
# mayúscula + letra sola o romano + separador punto/dos puntos/guion (reqcac
# cuerpo 'Sección A – Introducción' / 'Sección B - Controles…' e índice
# 'Sección A. Introducción'; ri_psp índice 'Sección I – …'). Sin separador no
# hay match ('Sección Punto Párrafo…' de seguef p.19); 'sección' minúscula
# (remisión en prosa) tampoco.
RE_SECCION_B582_CAPS = re.compile(r"^SECCI[OÓ]N\s+(\d+|[IVX]{1,6})\s*[-–—]\s*(.*)$")
RE_SECCION_B582_LETRA = re.compile(r"^Secci[oó]n\s+([A-Z]{1,6})\s*[.:\-–—]\s*(.*)$")


# --------- U-SEG-OFICIAL, S0 (solo e0-r2; con los defaults ninguna rama nueva corre) ---------
# Regla 1: sección escrita de otra forma. Además de «Sección N.» y «Sección N:», la línea de sección
# de la zona de encabezado admite «Seccón N.» (opecam pp. 14 y 25), «Sección N – Título» (snp_dd
# pp. 31-65, dmrd) y «Sección N Título» sin separador antes de un título en mayúscula (garopt pp. 6
# y 7, inspag). 'S' mayúscula, como RE_SECCION: una remisión en prosa no abre sección.
RE_SECCION_VARIANTE_R2 = re.compile(r"^Secci?[oó]n\s+(\d+)\s*(?:[.:]|[-–—]|(?=[A-ZÁÉÍÓÚÑ]))\s*(.*)$")
# Regla 2: rótulos de punto que no lo son. (a) remisión envuelta: el resto del rótulo empieza en
# minúscula con «y/a/al/hasta N.» o «de las normas / de la Sección / del presente…»
# (rdbcra::2.3.1 «y 2.3.2. siguientes.», ri_tsa::1.1 «de las normas sobre…»); (b) un componente de
# tres cifras o más es un número de ley o una cifra (ri_niif «21.526.»); (c) fila de una lista de
# códigos: sin punto final, con hueco de columna, y al menos MIN_FILAS_CODIGO_R2 en la página
# (los códigos de actividad «10.1 Producción…» de ri_dsf).
RE_REMISION_ENVUELTA_R2 = re.compile(
    r"^(?:(?:y|e|o|u|a|al|hasta)\s+(?:(?:los|el)\s+puntos?\s+)?\d+(?:\.\d+)*\.?(?=[\s,;:)]|$)"
    r"|de\s+(?:las|los|la|el|este|esta|estas|estos)\s+(?:normas|presente|[Ss]ecci[oó]n|texto|[Aa]nexo|[Cc]ap[ií]tulo)\b"
    r"|del\s+(?:presente|[Aa]nexo|[Cc]ap[ií]tulo|texto)\b)")
MIN_FILAS_CODIGO_R2 = 3
# Regla 4: marcador de letra y número (ri_spi): «APARTADO A: Título» abre la raíz A; «A.1.»,
# «A.1.1.» son puntos de la raíz A. Solo en el modo sin raíz y solo si se pide.
RE_APARTADO_R2 = re.compile(r"^APARTADO\s+([A-Z])\s*[:.\-–—]\s*(.+)$")
RE_ROTULO_LETRA_R2 = re.compile(r"^([A-Z])\.(\d+(?:\.\d+)*)\.?$")


# Regla 8 de S0 (S0-1 bis): una lista de puntos leída como cuerpo. En los 152 TOs hay doce: la lista de una sección
# («La sección se encuentra organizada en cinco puntos:» y 1.1 a 1.5, manori pp. 3 y 57) y páginas de índice que E0
# lee como cuerpo (adfsp p. 3, ceninf p. 2, cirmo3 pp. 3 y 4, nmaeef pp. 2, 14 y 36, ri2_ae p. 13 y ri_niif p. 1).
# Sus renglones no son rótulos: quedan como texto del nodo abierto. Una lista es una corrida de rótulos en una
# página, con al menos MIN_ROTULOS_LISTA_R8 de dos niveles o más, en la que entre rótulos solo hay líneas
# «Sección N.», renglones más a la derecha que el rótulo anterior, de menos de LARGO_ITEM_LISTA_R8 caracteres, que no
# empiezan en minúscula (ítems y títulos de la lista), y, como mucho, un renglón en minúscula por rótulo (el corte
# del título); en la que cada número reaparece como rótulo en una página posterior del TO, con el mismo
# título en al menos FRAC_TITULO_LISTA_R8 de los rótulos (el índice de cirmo3 difiere del cuerpo en 4 de 62; deja
# afuera ri_pnp p. 6, una enumeración de requisitos); en la que a lo sumo FRAC_CORTE_LISTA_R8 de los rótulos lleva
# un renglón en minúscula (una lista es de títulos); y cuyos números no reaparecen a su vez en forma de lista: entre
# las reapariciones hay, en mediana, más de BRECHA_REAPARICION_R8 renglones (el cuerpo tiene texto entre punto y
# punto; la declaración jurada de ri_ccna p. 32, repetida como formulario en p. 41, no). Es un veto, como la regla 2:
# actúa sobre un rótulo que se aceptaría o abriría una raíz; un renglón que ya se rechazaba conserva su motivo.
# Ocho de esas páginas son enteras una lista y pasan a índice por la ampliación de la regla 3 (`paginas_indice_r8`):
# adfsp p. 3, ceninf p. 2, cirmo3 pp. 3 y 4, nmaeef pp. 2 y 14, ri2_ae p. 13 y ri_niif p. 1. Las otras tres siguen
# en cuerpo: el veto actúa en manori pp. 3 y 57, y en nmaeef p. 36 no cambia nada (sus rótulos ya se rechazaban).
MIN_ROTULOS_LISTA_R8 = 3
LARGO_ITEM_LISTA_R8 = 70
FRAC_TITULO_LISTA_R8 = 0.8
FRAC_CORTE_LISTA_R8 = 0.25
BRECHA_REAPARICION_R8 = 3

# --------- U-SEG-OFICIAL, S0-3 (solo e0-r2; con los defaults ninguna rama nueva corre) ---------
# Mecanismo 2 de S0-3, numeración o título no leído, en la línea que abre una raíz del modo sin raíz. Forma (a): el
# número pegado al título, «4.Integración de los aportes.» (seggar p. 4); forma (b): número, guion y título en
# mayúsculas, «1- INTRODUCCIÓN» (ri2_pm pp. 1 y 3). La forma (c), título en mayúsculas sin punto final en una
# columna más profunda que la de las raíces ya abiertas («2. CUADRO 1 – CANTIDAD DE TARJETAS EMITIDAS», ri_tar p. 2),
# no tiene expresión propia: levanta la guarda de columna (G3) de `parsear_cuerpo`.
RE_NUM_PEGADO_M2 = re.compile(r"^(\d{1,2})\.(?=[A-ZÁÉÍÓÚÜÑ\"“(«])")
RE_NUM_GUION_M2 = re.compile(r"^(\d{1,2})-(?=\s)")
# Mecanismo 3 de S0-3, cuarta forma de la regla 8: una lista de rótulos de un nivel («1. Designación» a «9.
# Confidencialidad», el índice del Anexo I de ri2_ae p. 3), con al menos MIN_ROTULOS_LISTA_R8 rótulos, todos de un
# nivel y consecutivos, con las mismas guardas de la regla 8 (reaparición con el mismo título, renglones en
# minúscula, brecha entre reapariciones).


# --------- U-SEG-OFICIAL, S0-4 (solo e0-r2; con los defaults ninguna rama nueva corre) ---------
# Regla de sub-documento (`limites_subdocumento`; la lista de TOs donde corre es correr_e0.TOS_SUBDOCUMENTO_S0_4): un
# rótulo de anexo, de parte o de régimen abre una raíz nueva con su propio espacio de ids (un prefijo por
# sub-documento) y con herencia desde el rótulo. Tres formas:
# - anexo: un renglón entero «ANEXO <n>», «Anexo <n>» o «-ANEXO-», o «Anexo <n> – Título», entre los primeros
#   POS_ZONA_BANNER renglones de una página de cuerpo (el encabezado corrido de cada anexo en nmcief y ri_ccna; el
#   renglón que abre cada anexo en ri_sef y ri_icpipsp). <n> va en romanos o en arábigos y sucede al anexo anterior;
#   un anexo 1 (o sin número) después de otro abre un documento nuevo (ri_ccna junta dos normas, cada una con sus
#   anexos I a IV). Una serie de letras («ANEXO A» a «ANEXO L», los modelos de publicación de ri_cc) no es de
#   sub-documentos: una letra que sigue a la anterior del alfabeto no se lee como romano («ANEXO I» tras «ANEXO H»);
# - parte: un renglón de cuerpo «I. Título», «I.- TÍTULO», «I - TÍTULO», «II- TÍTULO» o, sin separador, «I TÍTULO»
#   en mayúsculas, con el título en mayúscula inicial, dentro de una serie de al menos MIN_PARTES_SD partes
#   consecutivas desde la I en el mismo anexo (o fuera de todo anexo): las partes I a III de ri_sef, I a IV del
#   Anexo I de nmcief y I y II del Anexo I de la segunda norma de ri_ccna. Un «I.» suelto (el rubro «I. Bienes
#   Diversos» de un modelo de balance de ri_cc) no forma serie;
# - régimen: un renglón «<n> - TÍTULO EN MAYÚSCULAS» o con la sigla «(R.I. – <sigla>)» entre los primeros
#   POS_ZONA_BANNER renglones de una página de cuerpo (los regímenes 4 y 5 y el R.I. – P. de ri_cc);
# - formulario: una página de cuerpo con el membrete «BANCO CENTRAL DE LA REPÚBLICA ARGENTINA» entre sus primeros
#   POS_MEMBRETE_SD renglones y sin rótulo de anexo (las fórmulas de la primera norma de ri_ccna, pp. 31 a 41); una
#   página que lleva «Cont. <n>» entre sus primeros renglones sigue el formulario de la anterior;
# - circular: un renglón de cuerpo «Circular <SIGLA> <n>. Título», dentro de una serie de al menos MIN_PARTES_SD en el
#   mismo anexo (los bloques SINAP, CONAU y RUNOR de la tabla del Anexo I de ri_icpipsp, cuyas filas vuelven a
#   numerarse desde 1).
# El prefijo de un sub-documento es la concatenación de R<n> (o RI<sigla>), D<k> (solo si el régimen junta más de un
# documento), A<n> (A, si el anexo no tiene número) o F<k> (formulario), y P<n> o C<k> (circular): «P1», «A2», «A1P2»,
# «D2A1P1», «D1F2», «A1C3», «R5», «RIP».
RE_ANEXO_SD = re.compile(r"^[-–]?\s*(?:ANEXO|Anexo)(?:\s+(?P<n>[IVXL]{1,5}|\d{1,2}|[A-Z]))?"
                         r"\s*(?:[-–:]\s*(?P<t>\S.*)?)?$")
RE_PARTE_SD = re.compile(r"^(?P<r>[IVX]{1,4})(?P<sep>\s*\.\s*[-–]|\s*[.\-–])?\s+(?P<t>[A-ZÁÉÍÓÚÑ].*)$")
RE_REGIMEN_SD = re.compile(r"^(?:B\.C\.R\.A\.\s+)?(?P<n>\d{1,2})\s*[-–]\s*(?P<t>[A-ZÁÉÍÓÚÑ].*)$")
RE_SIGLA_REGIMEN_SD = re.compile(r"\(R\.\s*I\.\s*[-–]\s*(?P<s>[A-Z][A-Z.\s]*?)\s*\)")
MIN_PARTES_SD = 2
RE_MEMBRETE_SD = re.compile(r"BANCO CENTRAL DE LA REP[ÚU]BLICA ARGENTINA")
RE_CONT_SD = re.compile(r"\bCont\.\s*\d")
POS_MEMBRETE_SD = 3
RE_CIRCULAR_SD = re.compile(r"^Circular\s+(?P<s>[A-Z]{3,})\s+\d+\.\s+\S")
# S0-4a-ter, forma de letra (solo con `letras`): un renglón «<letra>. <TÍTULO EN MAYÚSCULAS>», en serie desde la A
# dentro del mismo contenedor y de al menos MIN_PARTES_SD rótulos, abre el sub-documento L<k> (ri_ccna, Anexo III de la
# primera norma: «A. GENERAL» y «B. PRUEBAS SUSTANTIVAS»). Va después de la parte, así que «I.» sigue siendo parte.
RE_LETRA_SD = re.compile(r"^(?P<l>[A-Z])\.\s+(?P<t>\S.*)$")
# Regla 4a, oración tomada como título: en un punto con hijos cuyo rótulo es el primer renglón de su texto (el título no
# termina en punto y la intro sigue en minúscula), la primera oración (el título con los renglones de la intro hasta
# el primero que termina en punto o en dos puntos) termina en dos puntos o lleva un verbo de RE_VERBO_ORACION_4AB. La
# intro empieza en el rótulo y el encabezado heredado del punto es solo su número (seguef 2.1.6).
# Regla 4b, título envuelto: en esos puntos, si el primer renglón de la intro completa el título (termina en punto, o
# es toda la intro y no termina en dos puntos) y no lleva un verbo de RE_VERBO_ORACION_4AB, el renglón se junta al
# título y sale de la intro (los títulos partidos «…autorizadas a operar en» / «ellas.»). 4b se evalúa antes que 4a.
RE_VERBO_ORACION_4AB = re.compile(r"\b(?:deber[áa]n?|deben?|podr[áa]n?|pueden?|corresponde(?:n|r[áa]n?)?|ser[áa]n?"
                                  r"|tendr[áa]n?|se\s+[a-záéíóúñ]+r[áa]n?)\b", re.IGNORECASE)

# --------- U-SEG-OFICIAL, S0-5a (solo e0-r2; con los defaults ninguna rama nueva corre) ---------
# Detector del hallazgo 1.16 (`listas_116`, el de S1-bis unido con su corrección): una lista es un nodo con dos o más
# puntos hijos, todos sin hijos. Es candidata si el último ítem tiene un corte de párrafo (renglón con mayúscula inicial
# después de uno que termina en «.» o «:») y ninguno de los anteriores lo tiene, o si el último ítem tiene más párrafos
# que cualquiera de los anteriores, contando el renglón del rótulo como párrafo propio (el segundo renglón abre párrafo
# si empieza con mayúscula, aunque el título no termine en punto).
# R5-a, cierre al margen (`aplicar_cierre_al_margen(cierre=True)`): en una lista candidata, cada párrafo del último ítem
# desde el segundo pasa al cierre del padre si no está en la columna del texto de los ítems (a más de TOL_COL_R5A de
# ella) y está más cerca de la columna de sus rótulos. La columna de los rótulos es la mediana de los de la lista; la
# del texto, la mediana de las columnas de texto de los ítems anteriores al último, porque la del último puede ser la
# del propio cierre (cajasc 11.4.4). Si ningún ítem anterior tiene texto, pasa el párrafo que no corre más adentro que
# los rótulos (ri_oc B.2.4). Se evalúa cada párrafo, no solo el primero (cajasc 4.2.2.3).
TOL_COL_R5A = TOL_X     # tolerancia de columna de R5-a, fijada antes del censo de S0-5a: la de las columnas de E0
RE_MAYUSCULA_R5A = re.compile(r"^[A-ZÁÉÍÓÚÜÑ]")
# R5-a′, título de bloque (`aplicar_cierre_al_margen(titulo_bloque=True)`, por lista en correr_e0): en una lista
# candidata cuyo padre es una sección, el primer párrafo del último ítem, desde el segundo, que empieza con un renglón
# con forma de título de bloque (MAX_CHARS_TITULO_BLOQUE caracteres o menos, mayúscula inicial, sin puntuación final ni
# número de punto, sin huecos de columna) y al que sigue más texto abre una sección nueva, después de la del padre,
# con ese renglón como rótulo, el resto del ítem y el cierre del padre: el bloque llega hasta el encabezado siguiente
# de igual o mayor nivel. Su número es «bloque<k>» (k-ésimo bloque del TO): la clave es `<to>::Sbloque<k>`.
MAX_CHARS_TITULO_BLOQUE = 60
# R5-d, número en referencia (`parsear_cuerpo(numero_en_referencia=True)`): un renglón que empieza con un número de
# punto de dos o más componentes no es encabezado si el renglón anterior (de la misma página) termina en una palabra de
# PALABRAS_REFERENCIA_R5D y el renglón, sin huecos de columna, empieza en la columna del anterior (la del cuerpo del
# texto) y no en la de los rótulos de sus hermanos (la del último hermano abierto; sin hermanos, la de los hijos del
# padre). Sigue como prosa.
PALABRAS_REFERENCIA_R5D = frozenset({
    "punto", "puntos", "sección", "capítulo", "apartado", "inciso", "numeral", "anexo", "artículo", "ley",
    "comunicación", "nº", "n°",
    # artículos
    "el", "la", "los", "las", "lo", "un", "una", "unos", "unas", "al", "del",
    # preposiciones
    "a", "ante", "bajo", "con", "contra", "de", "desde", "durante", "en", "entre", "hacia", "hasta", "mediante",
    "para", "por", "según", "sin", "sobre", "tras"})
# R5-b, intersticial continuada (`construir_chunks(intersticial_continuado=True)`): dos intersticiales consecutivas del
# mismo hueco y de la misma página se unen si (i) la segunda empieza con minúscula y la primera no termina en «.», «:»
# ni «;»; (i′) la segunda es solo un código de tabla (RE_CODIGO_R5B) y la primera no termina en «.», «:» ni «;»; o
# (ii) la primera es un solo renglón de rótulo numerado (RE_ROTULO_R5B) y la segunda no empieza con otro. Las uniones
# se encadenan; la unidad unida conserva el número de la primera y las siguientes no se renumeran.
RE_CODIGO_R5B = re.compile(r"^[A-Z]\d{2}$")
RE_ROTULO_R5B = re.compile(r"^\d{1,2}\.\s+\S.*\.$")
RE_ROTULO_INICIO_R5B = re.compile(r"^\d{1,2}\.\s")
# R5-c, título de sección envuelto (`construir_chunks(titulo_seccion_envuelto=True)`): el chapeau de una sección que es
# un solo renglón, con un título sin puntuación final, es la continuación del título si (a) el título termina en una
# palabra partida con guion, (b) en una palabra de PALABRAS_FUNCIONALES_R5C, (c) deja abierta una comilla o un
# paréntesis, o (d) el chapeau empieza con minúscula. El renglón se junta al título (en un renglón aparte del
# encabezado, como en el PDF) y la sección queda sin chapeau.
PALABRAS_FUNCIONALES_R5C = frozenset({
    "el", "la", "los", "las", "lo", "un", "una", "unos", "unas", "al", "del",
    "a", "ante", "bajo", "con", "contra", "de", "desde", "durante", "en", "entre", "hacia", "hasta", "mediante",
    "para", "por", "según", "sin", "sobre", "tras",
    "y", "e", "o", "u", "ni", "que", "pero", "sino"})
# R5-e, rótulo vertical (`juntar_rotulo_vertical`, por lista en correr_e0, sobre el árbol): MIN_LETRAS_VERTICAL o más
# renglones de una sola letra mayúscula en la misma columna (TOL_X) y a no más de MAX_SALTO_VERTICAL pt uno del
# siguiente forman un rótulo vertical: se juntan en un renglón con la palabra, en el lugar de la última letra, y así van
# con el contenido de la página en que están (la «C» de «CODIGO» quedaba al final del formulario anterior de ri_ccna).
MIN_LETRAS_VERTICAL = 3
MAX_SALTO_VERTICAL = 15.0
# S0-5a-bis. R5-a por lista (`aplicar_cierre_al_margen(listas=…)`): la clave de una lista es la del último ítem
# (`<numero>`, o `<prefijo>::<numero>` dentro de un sub-documento); su valor, None (los párrafos del último ítem que R5-a
# mueve por columna, como en S0-5a) o ("rango", (página, top, comienzo del texto), (página, top, comienzo del texto)):
# exactamente los renglones del último ítem desde el primero hasta el segundo, inclusive. Un renglón del rango se
# reconoce por su página, su top (a TOL_TOP_POR_LISTA pt o menos) y el comienzo de su texto. R5-f, rótulo por lista
# (`parsear_cuerpo(rotulos_por_lista=…)`): (página, top, número sin el punto final, padre o None) de cada renglón que
# abre su punto; el renglón empieza con el número seguido de un punto. R5-g, raíz por lista
# (`parsear_cuerpo(raices_por_lista=…)`): (página, top, número de la raíz) de cada renglón que abre su raíz sin la guarda
# de columna G3; las otras guardas de la raíz explícita siguen.
TOL_TOP_POR_LISTA = 0.5

# --------- U-SEG-OFICIAL, S0-6a (solo e0-r2; con los defaults ninguna rama nueva corre) ---------
# B, encabezado de un punto con hijos (`construir_chunks(encabezado_b=True)`, `clase_encabezado_b`): en un punto (o una raíz
# del modo sin raíz) con hijos cuyo rótulo no termina en «.», «:» ni «;» y cuyo texto sigue en la intro (el renglón
# siguiente lo continúa con las condiciones de R5-c, o el renglón del rótulo es largo, de LARGO_RENGLON_TITULO_B caracteres o
# más), los renglones de la intro hasta el que termina en «.» (a lo sumo MAX_RENGLONES_TITULO_B) son el resto del título si
# no llevan un verbo de RE_VERBO_ORACION_4AB y además corren fuera de la columna del cuerpo del punto (sangría del título) o
# los sigue más texto de la intro: van enteros en la entrada de encabezado (B1, que incluye la regla 4b de S0-4). Si no, el
# número va seguido de un párrafo: no se fabrica encabezado y el texto va entero, con su número, en la entrada de intro (B2,
# que incluye la regla 4a de S0-4). Un rótulo que entra entero en un renglón no cambia.
LARGO_RENGLON_TITULO_B = 70
MAX_RENGLONES_TITULO_B = 3
# E, número que E0 rechaza por la columna (`parsear_cuerpo(raiz_sucesora_e=True)`, modo sin raíz): la raíz que la guarda
# de columna (G3) rechazaba se abre si continúa la numeración de su nivel (sucede exactamente a la última raíz abierta),
# no tiene huecos de columna (no es una fila de tabla) y el renglón anterior de la página no termina en una palabra de
# PALABRAS_REFERENCIA_R5D (no es una remisión). Las otras guardas de la raíz (banner, forma de título, sucesión, regla 8)
# siguen.
# G, número partido por el extractor (`parsear_cuerpo(numero_partido_g=True)`, `unir_numero_partido_g`): antes de
# reconocer números, un renglón que empieza con dígitos sueltos seguidos de «N.» («6 2 1 10. Supervisar…») y el renglón
# pegado a él, a DIST_NUMERO_PARTIDO_G pt o menos, que tiene solo los puntos (« . . . », uno por dígito) se unen en un solo
# renglón con el número entero («6.2.1.10. Supervisar…»); y una corrida de renglones que son solo un dígito o un punto,
# seguida de un renglón que empieza con «N.», se une a ese renglón.
RE_DIGITOS_G = re.compile(r"^((?:\d\s+)+)(\d+\.(?:\s.*)?)$")
RE_PUNTOS_G = re.compile(r"^\.(?:\s*\.)*$")
RE_DIGITO_O_PUNTO_G = re.compile(r"^(?:\d|\.)$")
DIST_NUMERO_PARTIDO_G = 6.0
# H, número sin espacio (`parsear_cuerpo(numero_pegado_h=True)`): un rótulo de punto de dos o más componentes pegado al
# título, al principio del renglón («1.2.3.Conceptos», «2.1.1.no sean…»), se lee como «N. resto» y abre su punto si el
# padre está abierto y sucede exactamente al último hermano (continúa la numeración), sin las validaciones de columna ni
# de minúscula; los vetos de siempre (regla 2, R5-d, regla 8) siguen. El renglón no cambia. No abre raíces.
RE_NUM_PEGADO_H = re.compile(r"^(\d+(?:\.\d+)+)\.(?=[^\s\d.])")
# K, pie de formulario (`separar_encabezado_pie(pie_formulario_k=True)`): el código de formulario («Fórm. 4421 C
# (II-2006)») como último renglón de la página es pie y sale del texto, como los demás renglones del pie.
RE_PIE_FORMULARIO_K = re.compile(r"^F[óo]rm\.\s*\d{3,5}\b")
# J, carátula (`parsear_cuerpo(caratula_j=True)`, `es_caratula_j`): la página 1 leída como cuerpo que es la carátula del TO
# (a lo sumo MAX_RENGLONES_CARATULA_J renglones, alguno con «Última comunicación» o «Texto ordenado», ninguno con un
# rótulo de punto ni de sección) no pierde renglones por el recorte de encabezado y pie (el título del TO y la fecha son
# texto de la carátula), y el preámbulo que empieza en ella no lleva el rótulo «Preámbulo», que E0 fabricaba.
RE_CARATULA_J = re.compile(r"[ÚU]ltima\s+comunicaci[oó]n|Texto\s+ordenado", re.IGNORECASE)
MAX_RENGLONES_CARATULA_J = 8
# F, encabezado de columnas de una tabla. F1 (`parsear_cuerpo(encabezado_tabla_f=True)`): el bloque del tope del contenido
# de una página (al menos dos renglones de MAX_CHARS_CELDA_F caracteres o menos, sin rótulo de punto) que repite, palabra
# por palabra en cualquier orden, el del tope de la página de cuerpo anterior es el encabezado de columnas de la tabla
# reimpreso: resto de encabezado, sale del texto. La primera aparición queda. F2 (`mover_encabezado_tabla_f`, sobre el
# árbol): el bloque de intro de un punto hecho solo de renglones de encabezado de columnas (cortos, a la derecha del
# rótulo de su primer hijo) delante de filas con columnas no es intro ni herencia: va con su tabla, al principio de la
# primera unidad terminal de la tabla.
MAX_CHARS_CELDA_F = 25
# C, párrafo sin número (`asignar_por_columna_c`, sobre el árbol, después de A): cada párrafo sin número que va después de
# un hijo o entre dos hijos se asigna al nivel abierto cuya columna comparte (D21), medida en coordenadas del PDF: el de la
# columna más cercana. Las columnas de un nivel son la de su texto (`text_col`) y la de los rótulos de sus hijos
# (`col_hijos` y, en la página del párrafo, la de los rótulos de sus hijos en esa página); la de un párrafo, el x0 menor de sus renglones. Un párrafo del texto de una unidad que corre en la columna
# de ese texto o más adentro es suyo (esa columna se mide sin el párrafo que se evalúa:
# `_col_propia_c`): solo uno sangrado hacia afuera puede pasar a otro nivel. Si empata entre dos niveles (sus columnas quedan a menos de
# TOL_COL_C pt de la más cercana), va al más interno (D8); si en el empate está el texto propio de la unidad, o ningún nivel
# tiene columna, la columna no discrimina y el párrafo queda como está. Recorre (1) los párrafos del texto propio de cada
# punto o raíz sin hijos, desde el segundo (el del rótulo es suyo): el primero que pasa a otro nivel lleva tras de sí a los
# que siguen, que van con él o a un nivel menos profundo; y (2) las intersticiales y los cierres de cada nodo, que pasan al
# nivel abierto en su posición (los ancestros del nodo, el nodo y sus descendientes con hijos: un segmento no vuelve al
# texto de una hoja) de la columna más cercana. No mueve renglones de las tablas que se serializan (como R5-a). Tolerancia:
# TOL_COL_C, fijada antes del censo de S0-6a, una sola para los 152: la de las columnas de E0, como R5-a. Reemplaza a R5-a
# por lista.
TOL_COL_C = TOL_X
# I, recuadro de encabezado de dos columnas (`parsear_cuerpo(recuadro_i=True)`, `leer_recuadro_por_columna_i`): en una
# página de formulario (el membrete RE_MEMBRETE_SD entre sus primeros POS_MEMBRETE_SD renglones), el recuadro de
# encabezado (los renglones del tope del contenido, mientras el salto vertical entre uno y el siguiente no pase
# MAX_SALTO_RECUADRO_I pt)
# que tiene dos columnas (las separa un hueco horizontal de al menos MIN_HUECO_COLUMNAS_I pt entre los comienzos de sus
# partes) se lee por columna: primero los renglones (o partes de renglón) de la izquierda, después los de la derecha. El
# membrete institucional nunca es madre: el rótulo heredable del formulario es la columna derecha, si tiene dos palabras o
# más, o el primer renglón en mayúsculas que sigue al recuadro; los renglones del recuadro no se heredan.
MAX_SALTO_RECUADRO_I = 15.0
MIN_HUECO_COLUMNAS_I = 100.0
# A, títulos sin número (`dividir_a`, sobre el árbol, antes de C). Generaliza R5-a′ a los 152. Un renglón sin número abre
# división si es (rango entre paréntesis; uno menor es una división mayor):
# - (0) un rótulo «ANEXO …» de sub-documento (la forma de anexo de `limites_subdocumento`, en todos los TOs);
# - (1) un cambio del título de sección en la banda de encabezado (D5): el texto distintivo de la banda de una página de
#   cuerpo (sus renglones sin «B.C.R.A.», sin la línea que E0 lee como sección y sin los que se repiten en la banda de más
#   de la mitad de las páginas de cuerpo) difiere del último no vacío (salvo en la primera página de cuerpo) y tiene forma de título
#   (en mayúsculas, o un rótulo de anexo, de apartado o de sección); en el modo sin raíz abre una división de primer
#   nivel, y dentro de una sección real cuelga de la sección;
# - (2) un rótulo «APARTADO X: …» o «Apartado X: …» (RE_APARTADO_A), o una raíz de apartado ya abierta por la regla 4;
# - (3) un título que encabeza solo su bloque (D14): un renglón con forma de título de bloque (`_es_titulo_bloque`, sin
#   numeración arábiga, romana, de letra ni de letra y número —«C.2.», «IV.INGRESO»— y sin viñeta, y sin número en
#   ningún lugar del renglón —RE_CON_NUMERO_A: un renglón con un número o un código, como «Código 205010» o «Formulario
#   OR1: …», no es un renglón sin número—), en una frontera de bloque (precedido por el tope de la página, un
#   renglón que termina en «.» o «:», un título o un salto vertical de GAP_BLOQUE_A pt o más) y seguido, en la misma
#   página, de un renglón que no lo continúa.
# No abren división: un renglón al que sigue el rótulo de un punto o raíz (D18: está entre una madre y sus hijos
# numerados), una fila de una tabla que se serializa (su título sí), un renglón que repite el título de la división que
# lo contiene, un título dentro del texto de un punto sin hijos —el primer renglón de ese texto (justo después del
# rótulo: encabeza el texto del punto), un subtítulo en la columna de ese texto (más adentro que el rótulo) o un título
# seguido del rótulo de un ítem de la misma lista (la lista sigue: el bloque es del ítem)—, el primer renglón del texto
# de un nodo sin rótulo (el comienzo del preámbulo, la carátula, el título de un
# sub-documento, un renglón del recuadro de un formulario que lee I). Lo que abre es madre de lo que sigue, hasta la
# próxima división de igual o mayor nivel: la división se
# lleva su renglón (rótulo) y el texto que sigue hasta el próximo número; en el modo sin raíz adopta las raíces que le
# siguen (las de un apartado aunque su número no lleve la letra) y, dentro de un sub-documento, la raíz «0» adopta las
# raíces del sub-documento (su texto se hereda); dentro de una sección real, la división cuelga de la sección. Un título
# que es el primer renglón del texto de otra división es su hijo. La división es una sección sintética con la clave de
# R5-a′, `<to>::Sbloque<k>`, o `<to>::S<letra>` si es un apartado.
RE_APARTADO_A = re.compile(r"^(?:APARTADO|Apartado)\s+([A-Z])\s*[:.\-–—]\s*(\S.*)$")
RE_NUMERACION_A = re.compile(r"^(?:\d+(?:\.\d+)*|[IVXLC]+|[A-Za-z])\s*[.)\-–](?:\s|(?=[A-ZÁÉÍÓÚÑ]))"
                             r"|^[A-Za-z](?:\.\d+)+\.?\s|^[-–—•−]")
RE_CON_NUMERO_A = re.compile(r"\d")
GAP_BLOQUE_A = 18.0
RANGO_SUBDOC_A, RANGO_BANDA_A, RANGO_APARTADO_A, RANGO_TITULO_A = 0, 1, 2, 3


def _es_linea_de_recuadro_m5(texto: str) -> bool:
    """Mecanismo 5 de S0-3 (forma c): renglón del recuadro del encabezado de página, en mayúsculas o con «B.C.R.A.»."""
    return "B.C.R.A." in texto or _es_titulo_mayusculas(texto)


def _rotulo_lista_r8(linea: "Linea"):
    t = linea.texto.strip()
    tok = t.split()[0] if t.split() else ""
    m = RE_NUM_TOKEN.match(tok) or RE_NUM_TOKEN_SIN_PUNTO.match(tok)
    if not m or int(m.group(1).split(".")[0]) > MAX_RAIZ:
        return None
    resto = t[len(tok):].strip()
    if not resto or not RE_TITULO_RAIZ.match(resto):
        return None
    return m.group(1), _norm_titulo(resto)[:20].strip()


def lineas_de_listas_r8(paginas: list[list["Linea"]], roles: list[str], informe: list | None = None,
                        renglones: list | None = None, forma4_m3: bool = False) -> frozenset:
    """(página, top) de los rótulos de las listas de puntos leídas como cuerpo (ver MIN_ROTULOS_LISTA_R8).
    Con `informe`, agrega una fila por corrida candidata con sus medidas y la guarda que la descarta (censo).
    Con `renglones`, agrega por cada lista detectada el conjunto (página, top) de todos sus renglones: los
    rótulos y los que la corrida admite entre ellos (lo usa el rol de índice de la regla 3, `paginas_indice_r8`).
    `forma4_m3` (mecanismo 3 de S0-3, solo e0-r2): admite además la lista de rótulos de un nivel, consecutivos."""
    cuerpo = [l for ls, r in zip(paginas, roles) if r == ROL_CUERPO for l in ls]
    corridas, actual, ult, minus = [], [], None, 0
    cortes: set = set()
    entre: dict = {}        # renglones admitidos después de cada rótulo
    for l in cuerpo:
        r = _rotulo_lista_r8(l)
        if r is not None:
            if actual and actual[-1][0].pagina != l.pagina:
                corridas.append(actual)
                actual = []
            actual.append((l, r))
            entre[id(l)] = []
            ult, minus = l, 0
            continue
        t = l.texto.strip()
        if actual and l.pagina == ult.pagina:
            if RE_SECCION.match(t):
                entre[id(ult)].append(l)
                continue
            if l.x0 > ult.x0 + TOL_X and len(t) < LARGO_ITEM_LISTA_R8:
                if not t[:1].islower():
                    entre[id(ult)].append(l)
                    continue
                if minus < 1:
                    minus += 1
                    cortes.add(id(ult))
                    entre[id(ult)].append(l)
                    continue
                actual.pop()        # el último rótulo tiene texto propio: no es de la lista
        if actual:
            corridas.append(actual)
        actual, ult, minus = [], None, 0
    if actual:
        corridas.append(actual)
    out = set()
    for c in corridas:
        prof2 = sum(1 for _, (n, _t) in c if "." in n)
        fila = {"pagina": c[0][0].pagina, "rotulos": len(c), "rotulos_prof2": prof2,
                "numeros": [n for _, (n, _t) in c], "primera": c[0][0].texto[:70]}
        if informe is not None and len(c) >= MIN_ROTULOS_LISTA_R8:
            informe.append(fila)
        nums1 = [int(n) for _, (n, _t) in c if "." not in n]
        forma4 = (forma4_m3 and prof2 == 0 and len(nums1) >= MIN_ROTULOS_LISTA_R8
                  and all(b == a + 1 for a, b in zip(nums1, nums1[1:])))
        if prof2 < MIN_ROTULOS_LISTA_R8 and not forma4:
            fila["descarte"] = "menos_de_3_rotulos_prof2"
            continue
        if forma4:
            fila["forma"] = "un_nivel_m3"
        pag = c[-1][0].pagina
        despues: dict = {}
        primera_pos: dict = {}
        for i, l in enumerate(cuerpo):
            if l.pagina > pag:
                r = _rotulo_lista_r8(l)
                if r is not None:
                    despues.setdefault(r[0], set()).add(r[1])
                    primera_pos.setdefault(r[0], i)
        def igual(t1: str, t2: str) -> bool:
            return bool(t1 and t2) and (t1.startswith(t2) or t2.startswith(t1))
        fila["reaparecen"] = sum(1 for _, (n, _t) in c if n in despues)
        if not all(n in despues for _, (n, _t) in c):
            fila["descarte"] = "no_reaparecen_todos"
            continue
        con_titulo = sum(1 for _, (n, tit) in c if any(igual(tit, t2) for t2 in despues[n]))
        con_corte = sum(1 for l, _ in c if id(l) in cortes)
        pos = [primera_pos[n] for _, (n, _t) in c]
        brechas = sorted(b - a for a, b in zip(pos, pos[1:]))
        brecha = brechas[len(brechas) // 2] if brechas else 0
        fila.update({"con_titulo": con_titulo, "con_corte": con_corte, "brecha_mediana": brecha})
        if con_titulo < FRAC_TITULO_LISTA_R8 * len(c):
            fila["descarte"] = "titulos_distintos"
        elif con_corte > FRAC_CORTE_LISTA_R8 * len(c):
            fila["descarte"] = "renglones_en_minuscula"
        elif brecha <= BRECHA_REAPARICION_R8:
            fila["descarte"] = "reaparicion_en_forma_de_lista"
        else:
            fila["descarte"] = None
            out.update((l.pagina, l.top) for l, _ in c)
            if renglones is not None:
                renglones.append(frozenset((x.pagina, x.top) for l, _ in c for x in [l] + entre[id(l)]))
    return frozenset(out)


# L de S0-6a-bis, índice (`lineas_de_indice_l`, `parsear_cuerpo(indice_l=…)`; D15: un índice no es texto de ninguna
# unidad): un índice leído como cuerpo es una corrida de rótulos en una página que empieza en «1.», sin números
# repetidos, en la que entre un rótulo y el siguiente solo hay renglones que continúan su título (a la altura de su
# rótulo o más adentro, a lo sumo MAX_RENGLONES_TITULO_L) y que termina en el primer renglón más a la izquierda que no es
# un rótulo, en un número repetido (el cuerpo que vuelve a empezar) o al final de la página; tiene al menos
# MIN_ROTULOS_LISTA_R8 rótulos, cada número reaparece como rótulo después de la corrida, con el mismo título en al menos
# FRAC_TITULO_LISTA_R8 de ellos, y no en forma de lista (como la regla 8: la mediana de los renglones entre
# reapariciones pasa BRECHA_REAPARICION_R8). Sus rótulos no abren raíz ni punto: el índice no corta la sucesión de
# números, y el cuerpo que vuelve a empezar en «1.» no se rechaza por ella. Es la regla 8 con los títulos partidos en
# varios renglones, que la regla 8 no admite.
MAX_RENGLONES_TITULO_L = 4
# M de S0-6a-bis (`construir_chunks(raiz0_solo_titulo_m=True)`): la raíz «0» de un sub-documento que abre A aporta a la
# herencia solo su título: los renglones con forma de título de bloque (`_es_titulo_bloque`) con que empieza su primer
# segmento. Su índice y sus bloques de cuerpo dejan de heredarse.


# Regla 3 de S0, ampliación (S0-2; nota del 05/10/2026 sobre el FRENO S0-1 bis al pie del mandato de U-SEG-OFICIAL):
# una página de cuerpo cuyo contenido, quitados el encabezado, el pie, las líneas «Sección N.» y «Tabla de
# correlaciones.», es entero una lista de la regla 8 es índice, siga o no a otra página de índice. Además de los
# renglones de la corrida de la regla 8, la lista admite tres formas que la corrida no toma: un rótulo pegado a su
# título («6.10.Declaración…», adfsp p. 3), el renglón en minúscula que sigue a una palabra partida de la lista
# («Uni-» / «versitarios.», nmaeef p. 2) y, antes del primer rótulo, a lo sumo un renglón sin número y sin punto
# final (el título de la lista: «Disposiciones generales sobre auditorías externas», nmaeef p. 2). La página
# anterior no se reclasifica (ceninf p. 1 sigue siendo cuerpo, no portada).
RE_TABLA_CORRELACIONES_R3 = re.compile(r"^Tabla\s+de\s+correlaciones\.?$", re.IGNORECASE)
RE_ROTULO_PEGADO_R3 = re.compile(r"^\d+(?:\.\d+)+\.(?=[A-ZÁÉÍÓÚÑ\"“(«])")


def lineas_de_indice_l(paginas: list[list["Linea"]], roles: list[str], informe: list | None = None) -> frozenset:
    """L de S0-6a-bis (ver MAX_RENGLONES_TITULO_L): (página, top) de los rótulos de los índices leídos como cuerpo. Con
    `informe`, una fila por corrida candidata con su descarte."""
    cuerpo = [l for ls, r in zip(paginas, roles) if r == ROL_CUERPO for l in ls]
    out: set = set()
    i = 0
    while i < len(cuerpo):
        l0 = cuerpo[i]
        r0 = _rotulo_lista_r8(l0)
        if r0 is None or r0[0] != "1":
            i += 1
            continue
        corrida, vistos, ult, cont, j = [(i, l0, r0)], {"1"}, l0, 0, i + 1
        while j < len(cuerpo) and cuerpo[j].pagina == l0.pagina:
            l = cuerpo[j]
            r = _rotulo_lista_r8(l)
            if r is not None:
                if r[0] in vistos:
                    break     # el cuerpo vuelve a empezar
                corrida.append((j, l, r))
                vistos.add(r[0])
                ult, cont = l, 0
            elif l.x0 >= ult.x0 - TOL_X and cont < MAX_RENGLONES_TITULO_L:
                cont += 1     # continúa el título del último rótulo
            else:
                break
            j += 1
        fin = corrida[-1][0]
        fila = {"pagina": l0.pagina, "rotulos": len(corrida), "numeros": [r[0] for _, _, r in corrida]}
        despues: dict = {}
        primera_pos: dict = {}
        for k in range(fin + 1, len(cuerpo)):
            r = _rotulo_lista_r8(cuerpo[k])
            if r is not None:
                despues.setdefault(r[0], set()).add(r[1])
                primera_pos.setdefault(r[0], k)

        def igual(t1: str, t2: str) -> bool:
            return bool(t1 and t2) and (t1.startswith(t2) or t2.startswith(t1))
        if len(corrida) < MIN_ROTULOS_LISTA_R8:
            fila["descarte"] = "menos_de_3_rotulos"
        elif not all(r[0] in despues for _, _, r in corrida):
            fila["descarte"] = "no_reaparecen_todos"
        elif sum(1 for _, _, r in corrida if any(igual(r[1], t2) for t2 in despues[r[0]])) \
                < FRAC_TITULO_LISTA_R8 * len(corrida):
            fila["descarte"] = "titulos_distintos"
        else:
            pos = [primera_pos[r[0]] for _, _, r in corrida]
            brechas = sorted(b - a for a, b in zip(pos, pos[1:]))
            if (brechas[len(brechas) // 2] if brechas else 0) <= BRECHA_REAPARICION_R8:
                fila["descarte"] = "reaparicion_en_forma_de_lista"
            else:
                fila["descarte"] = None
                out.update((l.pagina, l.top) for _, l, _ in corrida)
        if informe is not None:
            informe.append(fila)
        i = fin + 1
    return frozenset(out)


def paginas_indice_r8(paginas: list[list["Linea"]], roles: list[str], forma4_m3: bool = False) -> list[str]:
    """Roles con las páginas de índice de la ampliación de la regla 3 (ver RE_TABLA_CORRELACIONES_R3).
    `forma4_m3`: con la cuarta forma de la regla 8 (mecanismo 3 de S0-3)."""
    renglones: list = []
    lineas_de_listas_r8(paginas, roles, renglones=renglones, forma4_m3=forma4_m3)
    if not renglones:
        return roles
    miembros = frozenset().union(*renglones)
    rep = titulos_mayusculas_repetidos(paginas, roles)
    out = list(roles)
    for p in sorted({pag for pag, _top in miembros}):
        if roles[p - 1] != ROL_CUERPO:
            continue
        contenido, _desc, _sec = separar_encabezado_pie(paginas[p - 1], mayusculas_repetidas=rep,
                                                       pie_desde_version=True, seccion_variante=True)
        resto = [l for l in contenido if not RE_SECCION.match(l.texto.strip())
                 and not RE_TABLA_CORRELACIONES_R3.match(l.texto.strip())]
        en = [(l.pagina, l.top) in miembros for l in resto]
        if not any(en):
            continue
        primero = en.index(True)
        acepta = list(en)
        for i, l in enumerate(resto):
            if acepta[i]:
                continue
            t = l.texto.strip()
            if i < primero:
                acepta[i] = (i == 0 and primero == 1 and not RE_NUM_TOKEN.match(t.split()[0] if t.split() else "")
                             and not t.endswith("."))
            elif t[:1].islower() and acepta[i - 1] and resto[i - 1].texto.rstrip().endswith("-"):
                acepta[i] = True
            elif RE_ROTULO_PEGADO_R3.match(t):
                acepta[i] = True
            if not acepta[i]:
                break
        if all(acepta):
            out[p - 1] = ROL_INDICE
    return out

def _match_seccion_r2(texto: str, variante: bool, abierta: str | None = None):
    """RE_SECCION y, con `variante` (regla 1 de S0), RE_SECCION_VARIANTE_R2 con su guarda: la línea
    variante abre o continúa una sección solo si no retrocede respecto de la sección abierta
    (`abierta`) y, si no hay ninguna abierta, solo si es la 1 (la p. 5 de dmrd, una tabla resumen,
    trae en su primer renglón la fila «Sección 9 – CCRA…»)."""
    m = RE_SECCION.match(texto)
    if m or not variante:
        return m
    m = RE_SECCION_VARIANTE_R2.match(texto)
    if m is None:
        return None
    n = int(m.group(1))
    if abierta is None or not abierta.isdigit():
        return m if n == 1 else None
    return m if n >= int(abierta) else None


def _match_seccion_b582(texto: str) -> tuple[str, str] | None:
    """(numero VERBATIM, título) si la línea es un encabezado de sección en
    alguna variante B5.8.2; None si no. Solo la consultan los caminos con
    `marcadores_b582=True` (el vigente RE_SECCION se chequea siempre antes)."""
    m = RE_SECCION_B582_CAPS.match(texto) or RE_SECCION_B582_LETRA.match(texto)
    return (m.group(1), m.group(2).strip()) if m else None


def _valor_romano_sd(t: str) -> int | None:
    t = t.upper()
    return _ROMANOS_MAY_SD.get(t)


def limites_subdocumento(paginas: list[list["Linea"]], roles: list[str], letras: bool = False,
                          sin_regimen_pagina_1: bool = False, solo_anexo: bool = False) -> list[dict]:
    """U-SEG-OFICIAL, S0-4: los límites de sub-documento de un TO (formas y prefijo en RE_ANEXO_SD y su comentario), en
    orden documental. Cada límite: página y top del renglón del rótulo, forma (regimen, anexo, formulario, parte o
    circular), prefijo, título (el renglón del rótulo, tal cual) y prefijo del sub-documento que lo contiene (None si
    no hay). Un anexo que repite el número del anterior (el encabezado corrido de cada página) no es un límite.
    S0-4a-ter (con los defaults no cambia nada): `letras` agrega la forma de letra (RE_LETRA_SD; el límite lleva además
    su letra), y `sin_regimen_pagina_1` (regla sdr1) toma el régimen de la página 1 como el del propio TO: ni él ni los
    rótulos del mismo régimen en las páginas siguientes (el encabezado corrido) abren sub-documento o prefijan ids
    (ri_oc: «B.C.R.A. 10 – OPERACIONES DE CAMBIOS»). U-SEG-OFICIAL, S0-6a (A): `solo_anexo` toma solo la forma de anexo (la
    regla A abre los anexos en todos los TOs; las demás formas siguen por lista)."""
    cand: list[tuple] = []          # (página, top, forma, valor, renglón)
    for pi, (ls, rol) in enumerate(zip(paginas, roles), start=1):
        if rol != ROL_CUERPO:
            continue
        zona = ls[:POS_ZONA_BANNER]
        for l in zona:
            t = l.texto.strip()
            mr = RE_REGIMEN_SD.match(t)
            if mr and _es_titulo_mayusculas(mr.group("t")):
                cand.append((pi, l.top, "regimen", f"R{int(mr.group('n'))}", l))
                break
            ms = RE_SIGLA_REGIMEN_SD.search(t)
            if ms:
                cand.append((pi, l.top, "regimen", "RI" + re.sub(r"[.\s]", "", ms.group("s")), l))
                break
        anexo_en_pagina = False
        for l in zona:
            ma = RE_ANEXO_SD.match(l.texto.strip())
            if ma:
                cand.append((pi, l.top, "anexo", ma.group("n") or "", l))
                anexo_en_pagina = True
                break
        if not anexo_en_pagina:
            memb = next((l for l in ls[:POS_MEMBRETE_SD] if RE_MEMBRETE_SD.search(l.texto)), None)
            if memb is not None:
                cont = any(RE_CONT_SD.search(l.texto) for l in zona)
                cand.append((pi, memb.top, "formulario", "cont" if cont else "nuevo", memb))
        for l in ls:
            t = l.texto.strip()
            mp = RE_PARTE_SD.match(t)
            if mp and _valor_romano_sd(mp.group("r")) and (mp.group("sep") or _es_titulo_mayusculas(mp.group("t"))):
                cand.append((pi, l.top, "parte", _valor_romano_sd(mp.group("r")), l))
            elif RE_CIRCULAR_SD.match(t):
                cand.append((pi, l.top, "circular", 0, l))
            elif letras:
                ml = RE_LETRA_SD.match(t)
                if ml and _es_titulo_mayusculas(ml.group("t")):
                    cand.append((pi, l.top, "letra", ord(ml.group("l")) - ord("A") + 1, l))
    cand.sort(key=lambda c: (c[0], c[1]))
    if solo_anexo:
        cand = [c for c in cand if c[2] == "anexo"]     # A de S0-6a
    if sin_regimen_pagina_1:
        # regla sdr1 de S0-4a-ter: el régimen de la página 1 es el del TO
        reg_p1 = next((c[3] for c in cand if c[2] == "regimen" and c[0] == 1), None)
        if reg_p1 is not None:
            cand = [c for c in cand if not (c[2] == "regimen" and c[3] == reg_p1)]
    # contextos: (régimen, documento, contenedor) con contenedor = ("A", n) anexo, ("F", k) formulario o None
    eventos: list[dict] = []
    reg, doc, anexo, cont, nform, crudo_ant = None, 1, None, None, 0, None
    for pi, top, forma, valor, l in cand:
        if forma == "regimen":
            if valor != reg:
                reg, doc, anexo, cont, nform, crudo_ant = valor, 1, None, None, 0, None
                eventos.append({"forma": forma, "pagina": pi, "top": top, "linea": l, "ctx": (reg, doc, cont)})
            continue
        if forma == "anexo":
            letra = len(valor) == 1 and valor.isalpha()
            serie_letras = (letra and crudo_ant is not None and len(crudo_ant) == 1 and crudo_ant.isalpha()
                            and ord(valor) == ord(crudo_ant) + 1)
            v = 0 if valor == "" else (int(valor) if valor.isdigit() else _valor_romano_sd(valor))
            crudo_ant = valor
            if serie_letras or v is None or (letra and valor not in "IVXL"):
                continue
            if anexo is None:
                if v not in (0, 1):
                    continue
            elif v == anexo and cont == ("A", v):
                continue
            elif v == anexo + 1:
                pass
            elif v in (0, 1):
                doc, nform = doc + 1, 0
            else:
                continue
            anexo, cont = v, ("A", v)
            eventos.append({"forma": forma, "pagina": pi, "top": top, "linea": l, "ctx": (reg, doc, cont)})
            continue
        if forma == "formulario":
            if valor == "cont" and cont is not None and cont[0] == "F":
                continue
            nform += 1
            cont = ("F", nform)
            eventos.append({"forma": forma, "pagina": pi, "top": top, "linea": l, "ctx": (reg, doc, cont)})
            continue
        eventos.append({"forma": forma, "pagina": pi, "top": top, "linea": l, "ctx": (reg, doc, cont), "valor": valor})
    # series de partes (consecutivas desde la I) y de circulares, por contexto, de al menos MIN_PARTES_SD
    aceptadas: dict[int, int] = {}
    por_ctx: dict[tuple, list[int]] = {}
    for i, e in enumerate(eventos):
        if e["forma"] in ("parte", "circular", "letra"):
            por_ctx.setdefault((e["ctx"], e["forma"]), []).append(i)
    for (ctx, forma), idx in por_ctx.items():
        if forma == "circular":
            serie = list(idx)
        else:
            serie, esperado = [], 1
            for i in idx:
                if eventos[i]["valor"] == esperado:
                    serie.append(i)
                    esperado += 1
        if len(serie) >= MIN_PARTES_SD:
            for k, i in enumerate(serie, start=1):
                aceptadas[i] = k
    docs_por_reg: dict = {}
    for e in eventos:
        docs_por_reg[e["ctx"][0]] = max(docs_por_reg.get(e["ctx"][0], 1), e["ctx"][1])

    def prefijo(ctx: tuple, sub: str | None) -> str:
        r, d, c = ctx
        out = r or ""
        if docs_por_reg.get(r, 1) > 1:
            out += f"D{d}"
        if c is not None:
            out += c[0] + ("" if c[0] == "A" and c[1] == 0 else str(c[1]))
        return out + (sub or "")

    out: list[dict] = []
    for i, e in enumerate(eventos):
        r, d, c = e["ctx"]
        if e["forma"] in ("parte", "circular", "letra"):
            if i not in aceptadas:
                continue
            # el sub-documento que lo contiene: el anexo o el formulario, o el régimen fuera de ellos (un documento
            # D<k> no es un sub-documento: solo distingue prefijos)
            sub = {"parte": "P", "circular": "C", "letra": "L"}[e["forma"]] + str(aceptadas[i])
            p, padre = prefijo(e["ctx"], sub), (prefijo(e["ctx"], None) if c is not None else r)
        elif e["forma"] in ("anexo", "formulario"):
            p, padre = prefijo(e["ctx"], None), r
        else:
            p, padre = prefijo(e["ctx"], None), None
        out.append({"pagina": e["pagina"], "top": e["top"], "forma": e["forma"], "prefijo": p,
                    "titulo": e["linea"].texto.strip(), "padre": padre})
        if e["forma"] == "letra":
            out[-1]["letra"] = chr(ord("A") + e["valor"] - 1)
    return out


# ------------------------------------------------------------------- líneas

@dataclass
class Linea:
    pagina: int          # 1-based
    top: float
    x0: float
    texto: str
    ngaps: int           # fronteras de columna (huecos > GAP_COL) dentro de la línea
    ultimo_numerico: bool
    primer_codigo: bool  # primer token arranca con ≥3 dígitos (fila código-partida)
    # U-SEG-OFICIAL, S0-6a (I): (x0, x1, texto) de cada palabra, en orden x0; solo lo lee la regla I (recuadro por columna)
    palabras: tuple = ()


def extraer_lineas(pdf_path: Path) -> list[list[Linea]]:
    """Extrae las líneas de cada página agrupando palabras por 'top' (±TOL_TOP).

    El texto de una línea es el join por espacio simple de sus palabras en
    orden x0. Este texto ES el corpus de E0: la verificación de cobertura se
    define sobre él.
    """
    paginas: list[list[Linea]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for pi, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            grupos: list[tuple[float, list[dict]]] = []
            for w in words:
                for i, (t, ws) in enumerate(grupos):
                    if abs(t - w["top"]) <= TOL_TOP:
                        ws.append(w)
                        break
                else:
                    grupos.append((w["top"], [w]))
            lineas: list[Linea] = []
            for t, ws in sorted(grupos, key=lambda g: g[0]):
                ws = sorted(ws, key=lambda w: w["x0"])
                ngaps = sum(1 for a, b in zip(ws, ws[1:]) if b["x0"] - a["x1"] > GAP_COL)
                texto = " ".join(w["text"] for w in ws)
                lineas.append(Linea(
                    pagina=pi, top=round(t, 1), x0=round(ws[0]["x0"], 1),
                    texto=texto, ngaps=ngaps,
                    ultimo_numerico=bool(RE_NUMERICO.match(ws[-1]["text"])),
                    primer_codigo=bool(re.match(r"^\d{3}", ws[0]["text"])),
                    palabras=tuple((round(w["x0"], 1), round(w["x1"], 1), w["text"]) for w in ws),
                ))
            paginas.append(lineas)
    return paginas


# ------------------------------------------------------------ roles de página

ROL_PORTADA = "portada"
ROL_INDICE = "indice"
ROL_TABLA = "tabla_norma_origen"
ROL_HISTORIAL = "historial"
ROL_CUERPO = "cuerpo"
ROL_REGISTRO = "ficha_registro"   # solo lo asigna el modo sin raíz (B5.8.1)


def clasificar_paginas(paginas: list[list[Linea]],
                       marcadores_b582: bool = False,
                       continuacion_con_titulo: bool = False) -> list[str]:
    """portada = antes de la primera página de índice; índice = marcador
    '-Índice-' (variantes con espacio/guion largo), 'Índice' a línea entera
    sin guiones (con la guarda de RE_MARCA_INDICE_SIN_GUIONES: mayúscula
    inicial y primeras POS_MARCA_INDICE líneas de la página) o continuación
    (página que sigue a una de índice con ≥2 líneas 'Sección N.'); tabla_norma_origen =
    contiene 'NORMA DE ORIGEN'; historial = desde la página cuyo primer
    contenido anuncia el historial de Comunicaciones de la norma (pegajoso
    hasta el próximo marcador explícito de otro rol); cuerpo = resto.

    Con `marcadores_b582=True` (B5.8.2; SOLO tras comprobar cero unidades por
    el camino vigente) el marcador de índice admite además las variantes
    medidas de RE_MARCA_INDICE_B582, con la misma guarda posicional. La
    heurística de continuación (n_secc >= 2) NO se extiende: ver docstring
    del módulo (contraejemplo ri_dcpc p.3)."""
    roles: list[str] = []
    visto_indice = False
    en_historial = False
    for lineas in paginas:
        textos = [l.texto.strip() for l in lineas]
        if continuacion_con_titulo:
            # regla 3 de S0 (e0-r2): para la continuación de índice cuentan solo las líneas de
            # sección con título; «Sección 8.» sola o «Sección 4. de las normas…» son remisiones
            # en prosa de una página de cuerpo (snp_mep p. 3, venliq p. 3, fimipyme p. 4)
            n_secc = sum(1 for t in textos if (m := RE_SECCION.match(t))
                         and RE_TITULO_RAIZ.match(m.group(2).strip()))
        else:
            n_secc = sum(1 for t in textos if RE_SECCION.match(t))
        if any(MARCA_TABLA_ORIGEN in t.upper() for t in textos):
            rol = ROL_TABLA
            en_historial = False
        elif any(RE_MARCA_INDICE.match(t) for t in textos) \
                or any(RE_MARCA_INDICE_SIN_GUIONES.match(t)
                       for t in textos[:POS_MARCA_INDICE]) \
                or (marcadores_b582
                    and any(RE_MARCA_INDICE_B582.match(t)
                            for t in textos[:POS_MARCA_INDICE])):
            rol = ROL_INDICE
            visto_indice = True
            en_historial = False
        elif any(MARCA_HISTORIAL in t.lower() for t in textos[:3]):
            rol = ROL_HISTORIAL
            en_historial = True
        elif en_historial:
            rol = ROL_HISTORIAL
        elif roles and roles[-1] == ROL_INDICE and n_secc >= 2:
            rol = ROL_INDICE  # continuación de índice sin marcador (caso ric p.2)
        elif not visto_indice:
            rol = ROL_PORTADA
        else:
            rol = ROL_CUERPO
        roles.append(rol)
    return roles


# ------------------- modo sin raíz: roles derivados y banners (B5.8.1) -------------------

def _clave_banner(texto: str) -> tuple[str, str] | None:
    """Clave de identidad de una línea numerada candidata a banner: su token
    numérico y los primeros 25 caracteres del resto (los banners largos se
    envuelven distinto según la página — 'INFORMACION INSTITUCIONAL DE
    ENTIDADES' vs '… DE ENTIDADES FINANCIERAS Y', medidos en ri_ii_31_12_19 —
    pero comparten número y arranque)."""
    tokens = texto.split()
    if not tokens:
        return None
    m = RE_NUM_TOKEN.match(tokens[0]) or RE_NUM_TOKEN_SIN_PUNTO.match(tokens[0])
    if not m:
        return None
    resto = texto[len(tokens[0]):].strip()
    if not resto:
        return None
    return (m.group(1), resto[:25])


def detectar_banners(paginas: list[list[Linea]]) -> set[tuple[str, str]]:
    """Líneas numeradas EN MAYÚSCULAS SOSTENIDAS de la zona de título
    (primeras POS_ZONA_BANNER líneas) que se repiten en ≥MIN_PAGS_BANNER
    páginas: encabezado corrido del TO, no espina (caso medido: '17. BASE DE
    DATOS PADRÓN (R.I. – B.P.)' abre las 3 páginas de ri_bdp; la espina real
    corre en '1.'/'2.'/'3.'). La forma de mayúsculas es parte de la
    definición: las líneas de campo en minúscula que se repiten al tope de
    página ('1. Entidad responsable.' encabeza los datos de cada apartado de
    ri_secoexpo) son espina genuina, no banner. En TOs de 1-2 páginas ninguna
    línea alcanza el umbral y nada se marca."""
    paginas_por_clave: dict[tuple[str, str], set[int]] = {}
    for pi, lineas in enumerate(paginas, start=1):
        for l in lineas[:POS_ZONA_BANNER]:
            t = l.texto.strip()
            if not _es_titulo_mayusculas(t):
                continue
            clave = _clave_banner(t)
            if clave is not None:
                paginas_por_clave.setdefault(clave, set()).add(pi)
    return {c for c, ps in paginas_por_clave.items() if len(ps) >= MIN_PAGS_BANNER}


def detectar_banners_texto(paginas: list[list[Linea]]) -> set[str]:
    """B5.8.2 — banner de página de caja mixta: líneas de la zona de título
    (primeras POS_ZONA_BANNER) repetidas VERBATIM en ≥MIN_PAGS_BANNER páginas.
    A diferencia de `detectar_banners` (B5.8.1: líneas NUMERADAS en mayúsculas
    sostenidas), acá la identidad es el texto completo y sin requisito de
    forma: el banner medido de reqcac ('Requisitos Operativos Mínimos de
    Tecnología…' / 'Casas y Agencias de Cambio', p.2-10) va en caja mixta y
    el descarte vigente de títulos en mayúsculas no lo alcanza. Solo lo
    consumen los caminos con `marcadores_b582=True`, y el chequeo de sección
    de `separar_encabezado_pie` corre ANTES del descarte (contraejemplo:
    'SECCION 3 – CRITERIOS GENERALES' se repite en 20 páginas de ri_dcpc y
    ES el encabezado corrido de su sección)."""
    por_texto: dict[str, set[int]] = {}
    for pi, lineas in enumerate(paginas, start=1):
        for l in lineas[:POS_ZONA_BANNER]:
            t = l.texto.strip()
            if t:
                por_texto.setdefault(t, set()).add(pi)
    return {t for t, ps in por_texto.items() if len(ps) >= MIN_PAGS_BANNER}


def marcar_paginas_registro(paginas: list[list[Linea]], roles: list[str]) -> list[str]:
    """Página de cuerpo cuya fracción de líneas ficha/código alcanza
    DENS_REGISTRO_MIN → rol `ficha_registro` (fuera del parseo de prosa,
    declarada en los conteos de roles). Las páginas de prosa con una mención
    aislada ('Incluye…' en un párrafo) quedan muy por debajo del umbral."""
    out = list(roles)
    for i, (lineas, rol) in enumerate(zip(paginas, roles)):
        if rol != ROL_CUERPO:
            continue
        no_vacias = registro = 0
        for l in lineas:
            t = l.texto.strip()
            if not t:
                continue
            no_vacias += 1
            if RE_FICHA_REGISTRO.match(t) or RE_LISTA_CODIGO.match(t) \
                    or RE_CODIGO_CUENTA.search(t):
                registro += 1
        if no_vacias and registro / no_vacias >= DENS_REGISTRO_MIN:
            out[i] = ROL_REGISTRO
    return out


def roles_para_modo_sin_raiz(paginas: list[list[Linea]],
                             roles: list[str]) -> list[str]:
    """Roles de página del modo sin raíz. Familia a (censo B5.8.0): sin página
    de índice la clasificación vigente dejó todo en `portada` — esas páginas
    pasan a `cuerpo` (historial, tabla de origen e índice conservan su rol tal
    cual). Familia c: la compuerta vigente ya produjo cuerpo y los roles se
    respetan sin cambio. En ambos casos se aplica después la compuerta de
    páginas de registro."""
    if not any(r == ROL_CUERPO for r in roles):
        roles = [ROL_CUERPO if r == ROL_PORTADA else r for r in roles]
    return marcar_paginas_registro(paginas, roles)


# ------------------------------------------------- encabezados y pies (cuerpo)

def _es_titulo_mayusculas(texto: str) -> bool:
    """Línea de encabezado corrido: sin minúsculas (títulos de TO, 'B.C.R.A.',
    la línea de aparato del ric '4. EXIGENCIA…')."""
    letras = [c for c in texto if c.isalpha()]
    return bool(letras) and not any(c.islower() for c in letras)


def separar_encabezado_pie(lineas: list[Linea], capturar_seccion: bool = True,
                           labels_preservables: set | None = None,
                           seccion_b582: bool = False,
                           banners_texto: set | None = None,
                           mayusculas_repetidas: set | None = None,
                           pie_desde_version: bool = False,
                           cola_titulo_estricta: bool = False,
                           seccion_variante: bool = False,
                           seccion_abierta: str | None = None,
                           cierre_m5: bool = False,
                           cola_m5: bool = False,
                           zona6_m5: bool = False,
                           pie_formulario_k: bool = False,
                           ) -> tuple[list[Linea], list[Linea], str | None]:
    """Devuelve (contenido, descartadas, seccion_corrida).

    Encabezado: dentro de las primeras 5 líneas, las que son título en
    mayúsculas, contienen 'B.C.R.A.' o —solo si capturar_seccion— son la línea
    corrida 'Sección N. …' (que se captura como metadata de página; en páginas
    de índice una línea 'Sección N.' es una ENTRADA, no encabezado). Pie:
    desde el final, las que matchean los patrones de RE_PIE.

    `labels_preservables` (solo lo pasa el modo sin raíz de B5.8.1): con un
    set de claves de banner, una línea numerada en mayúsculas sostenidas de la
    zona de encabezado se CONSERVA como contenido salvo que sea banner
    repetido — las raíces genuinas de la espina van en mayúsculas en varios
    TOs medidos ('1. DATOS GENERALES' de ri_ii_31_12_19) y el descarte
    genérico de títulos las perdería; los banners ('17. BASE DE DATOS
    PADRÓN…') siguen descartándose como hasta ahora.

    `seccion_b582` y `banners_texto` (solo los pasan los caminos B5.8.2, ver
    docstring del módulo): con seccion_b582, una línea de la zona que matchea
    una variante de sección (RE_SECCION_B582_*) se captura como
    seccion_corrida SIN cola envuelta (títulos medidos completos en una
    línea; en reqcac p.3 la prosa inmediata se pegaría al título); con
    banners_texto, una línea de la zona repetida verbatim en
    ≥MIN_PAGS_BANNER páginas se descarta como encabezado — DESPUÉS de los
    chequeos de sección, que tienen precedencia.

    `mayusculas_repetidas` (solo la versión e0-r2, U-R2-CODIGO, K; ver
    `titulos_mayusculas_repetidos`): todo lo que en la zona precede a la
    última línea con «B.C.R.A.» o de sección (incluida) es encabezado; después
    de esa línea, una línea sin minúsculas se descarta solo si su texto, sin
    espacios, está en el conjunto de los que se repiten en la zona de título
    de al menos 2 páginas. Dos excepciones (complemento final de la unidad,
    medidas sobre los 152 TOs de la partición): K-a′, después de un renglón
    que empieza con numeración de punto y tiene minúsculas, una línea con
    «B.C.R.A.» ya no cierra el encabezado (es texto de la norma: el título
    de `ri_rml::1.11` partido en dos renglones, la oración de `nmaeef::S11`
    que nombra al B.C.R.A.); la línea de sección sí lo cierra. K-b, una línea
    en mayúsculas con numeración de un nivel (RE_TITULO_SECCION_NUMERADO_K)
    se descarta como antes de K (`snp_cheq`, `snp_dd`), salvo en el modo sin
    raíz, que la decide por `labels_preservables`. None (todos los demás call
    sites) deja el descarte histórico.

    `pie_desde_version` (solo la versión e0-r2, U-R2-CODIGO, agregado 8): si
    una de las últimas VENTANA_PIE_VERSION líneas cumple RE_PIE_VERSION
    («Versión: … Comunicación …»), esa línea y todas las que la siguen en la
    página son pie, antes del recorte por RE_PIE. Cubre las formas del pie que
    RE_PIE no reconoce («Versión :», sin «Página») y las líneas que quedan
    debajo y cortaban el recorte (fechas con puntos o con año de cinco
    dígitos, «Comunicación “C” …», «Circular CONAU …», «… 1 de 3»). False
    (todos los demás call sites) deja el recorte histórico.

    `cola_titulo_estricta` (solo la versión e0-r2, U-R2-CODIGO-2, C2): la
    cola envuelta del título de sección se acepta solo si continúa el título
    (`continua_titulo`); un renglón que no lo continúa es texto de la norma.
    False deja la regla histórica (renglón inmediato sin numeración).

    Mecanismo 5 de S0-3 (solo la versión e0-r2; con los tres en False, la regla de antes). `cierre_m5` (forma a):
    después de la primera línea de sección de la zona, una línea de sección de otro número o con «B.C.R.A.» cierra
    el encabezado, y una con «B.C.R.A.» se descarta como encabezado, solo si su texto se repite en la zona de título
    de otra página de cuerpo (`mayusculas_repetidas`): la remisión «Sección 4. de las normas…» de fimipyme p. 4 y
    los renglones de ri_cc pp. 60 y 62 que nombran al B.C.R.A. son texto de la norma; el título de la misma sección
    repetido bajo el recuadro (dmrd pp. 6 a 60) sigue cerrándolo. `cola_m5` (forma b, `_no_es_cola_m5`): un
    renglón no es cola del título si empieza con un inciso («ii)», RE_MARCADOR_ENUM: snp_cheq p. 71), ni si el
    título no quedó abierto, el renglón no está en la columna de la línea de sección y el que le sigue está en su
    misma columna, a interlineado de párrafo (ri2_ci p. 5: el texto del punto 1.1.1.4 en la columna del cuerpo).
    `zona6_m5` (forma
    c): si los cinco primeros renglones son el recuadro (`_es_linea_de_recuadro_m5`) y el sexto es la línea de
    sección, la zona es de seis renglones y la sección se abre (ri_ai p. 3).

    `pie_formulario_k` (K de S0-6a, solo e0-r2): el código de formulario («Fórm. 4421 C (II-2006)», RE_PIE_FORMULARIO_K)
    como último renglón de la página es pie."""
    descartadas: list[Linea] = []
    contenido = list(lineas)
    seccion_corrida: str | None = None

    # pie (desde el final)
    if pie_desde_version:
        for i in range(len(contenido) - 1, max(-1, len(contenido) - 1 - VENTANA_PIE_VERSION), -1):
            if RE_PIE_VERSION.match(contenido[i].texto.strip()):
                while len(contenido) > i:
                    descartadas.append(contenido.pop())
                break
    while contenido and (any(p.match(contenido[-1].texto.strip()) for p in RE_PIE)
                         or (pie_formulario_k and RE_PIE_FORMULARIO_K.match(contenido[-1].texto.strip()))):
        descartadas.append(contenido.pop())     # K de S0-6a: también el código de formulario del pie

    # encabezado (desde el principio, zona de 5 líneas)
    quitadas = 0
    ultima_top_seccion: float | None = None
    x0_seccion: float | None = None
    forzadas = 0
    zona = 5
    if zona6_m5 and capturar_seccion and len(contenido) > 5 \
            and all(_es_linea_de_recuadro_m5(l.texto.strip()) for l in contenido[:5]) \
            and not any(_match_seccion_r2(l.texto.strip(), seccion_variante, seccion_abierta) for l in contenido[:5]) \
            and _match_seccion_r2(contenido[5].texto.strip(), seccion_variante, seccion_abierta):
        zona = 6    # mecanismo 5 de S0-3, forma c
    rep_m5 = mayusculas_repetidas if mayusculas_repetidas is not None else set()
    if mayusculas_repetidas is not None:
        # e0-r2: la línea «B.C.R.A.» o de sección marca el final del
        # encabezado corrido; lo anterior de la zona es encabezado aunque no se
        # repita (título partido distinto en esa página). K-a′: después de un
        # renglón numerado con minúsculas, «B.C.R.A.» es texto de la norma
        prosa_numerada = False
        num_seccion_vista: str | None = None
        for i, l in enumerate(contenido[:zona]):
            ti = l.texto.strip()
            tok = ti.split()[0] if ti.split() else ""
            if (RE_NUM_TOKEN.match(tok) or RE_NUM_TOKEN_SIN_PUNTO.match(tok)) \
                    and not _es_titulo_mayusculas(ti):
                prosa_numerada = True
            ms = _match_seccion_r2(ti, seccion_variante, seccion_abierta) if capturar_seccion else None
            mb = _match_seccion_b582(ti) if capturar_seccion and seccion_b582 and not ms else None
            num_i = ms.group(1) if ms else (mb[0] if mb else None)
            cierra = ("B.C.R.A." in ti and not prosa_numerada) or num_i is not None
            if cierra and cierre_m5 and num_seccion_vista is not None and num_i != num_seccion_vista \
                    and "".join(ti.split()) not in rep_m5:
                cierra = False      # mecanismo 5 de S0-3, forma a
            if cierra:
                forzadas = i + 1
            if num_seccion_vista is None and num_i is not None:
                num_seccion_vista = num_i
    while contenido and quitadas < zona:
        t = contenido[0].texto.strip()
        m = _match_seccion_r2(t, seccion_variante, seccion_abierta)
        m_en_linea = RE_SECCION_EN_LINEA.search(t) if "B.C.R.A." in t else None
        m_b582 = (_match_seccion_b582(t)
                  if seccion_b582 and capturar_seccion and seccion_corrida is None
                  else None)
        if m and capturar_seccion and seccion_corrida is None:
            # la línea 'Sección N. …' puede contener 'B.C.R.A.' en su TÍTULO
            # (ric Sección 7), por eso se chequea antes que el descarte genérico
            seccion_corrida = t
            ultima_top_seccion = contenido[0].top
            x0_seccion = contenido[0].x0
            descartadas.append(contenido.pop(0))
            quitadas += 1
        elif m_en_linea and capturar_seccion and seccion_corrida is None:
            # títulos largos: el PDF fusiona 'B.C.R.A. Sección N. …' en una línea
            seccion_corrida = t[m_en_linea.start():]
            ultima_top_seccion = contenido[0].top
            descartadas.append(contenido.pop(0))
            quitadas += 1
        elif m_b582 is not None:
            # sección por variante B5.8.2 — cola envuelta DESACTIVADA
            # (ultima_top_seccion queda en None; ver docstring)
            seccion_corrida = t
            descartadas.append(contenido.pop(0))
            quitadas += 1
        elif quitadas < forzadas:
            descartadas.append(contenido.pop(0))
            quitadas += 1
        elif ("B.C.R.A." in t and not (cierre_m5 and seccion_corrida is not None
                                       and "".join(t.split()) not in rep_m5)) or (_es_titulo_mayusculas(t)
                                 and (mayusculas_repetidas is None
                                      or "".join(t.split()) in mayusculas_repetidas
                                      or (labels_preservables is None
                                          and RE_TITULO_SECCION_NUMERADO_K.match(t)))
                                 and not (labels_preservables is not None
                                          and _clave_banner(t) is not None
                                          and _clave_banner(t) not in labels_preservables)):
            descartadas.append(contenido.pop(0))
            quitadas += 1
        elif banners_texto is not None and t in banners_texto:
            # banner de página de caja mixta (B5.8.2): repetido verbatim en
            # la zona de título de ≥MIN_PAGS_BANNER páginas
            descartadas.append(contenido.pop(0))
            quitadas += 1
        elif seccion_corrida is not None and ultima_top_seccion is not None \
                and contenido[0].top - ultima_top_seccion <= GAP_TOP_TITULO \
                and not RE_NUM_TOKEN.match(t.split()[0] if t.split() else "") \
                and (not cola_titulo_estricta or continua_titulo(seccion_corrida, t)) \
                and not (cola_m5 and _no_es_cola_m5(contenido, x0_seccion, seccion_corrida)):
            # cola envuelta del título de sección ('dos.', '(SECOEXPO).'):
            # renglón inmediato (interlineado de encabezado, no de contenido).
            # Una línea que arranca con numeración NUNCA es cola de título:
            # es el primer punto de la página (ric: '6.1. Normas…' a 13pt).
            seccion_corrida = seccion_corrida + " " + t
            ultima_top_seccion = contenido[0].top
            descartadas.append(contenido.pop(0))
            quitadas += 1
        else:
            break
    return contenido, descartadas, seccion_corrida


def _titulo_abierto(titulo: str) -> bool:
    """El título de sección no terminó: sin punto final, y termina en guion, coma o una palabra de
    PALABRAS_QUE_CONTINUAN_TITULO (la parte de `continua_titulo` que no mira el renglón siguiente)."""
    tit = titulo.rstrip()
    if not tit or tit.endswith("."):
        return False
    if tit.endswith(("-", "‐", "–", ",")):
        return True
    palabras = re.findall(r"\w+", tit.lower())
    return bool(palabras) and palabras[-1] in PALABRAS_QUE_CONTINUAN_TITULO


def _no_es_cola_m5(contenido: list[Linea], x0_seccion: float | None, seccion_corrida: str) -> bool:
    """Mecanismo 5 de S0-3, forma b: el primer renglón de `contenido` no es cola del título de sección si empieza con
    un inciso, o si el título no quedó abierto (`_titulo_abierto`), el renglón no está en la columna de la línea de
    sección y el que le sigue está en su misma columna a interlineado de párrafo (no más de GAP_TOP_TITULO): es el
    primer renglón de un párrafo de la norma (ri2_ci p. 5). Un título partido en varios renglones (ctacte pp. 44 a 48,
    ctavis pp. 30 a 33) queda abierto y su cola se sigue leyendo como antes."""
    c = contenido[0]
    if RE_MARCADOR_ENUM.match(c.texto.strip()):
        return True
    if x0_seccion is None or abs(c.x0 - x0_seccion) <= TOL_X or len(contenido) < 2 \
            or _titulo_abierto(seccion_corrida):
        return False
    sig = contenido[1]
    return abs(sig.x0 - c.x0) <= TOL_X and sig.top - c.top <= GAP_TOP_TITULO


def continua_titulo(titulo: str, renglon: str) -> bool:
    """e0-r2 (U-R2-CODIGO-2, C2): `renglon` continúa el título de sección
    `titulo` si el título no termina en punto y el renglón empieza en
    minúscula o el título termina en guion, coma o una palabra de
    PALABRAS_QUE_CONTINUAN_TITULO."""
    tit = titulo.rstrip()
    if not tit or tit.endswith("."):
        return False
    r = renglon.lstrip()
    if r[:1].islower():
        return True
    if tit.endswith(("-", "‐", "–", ",")):
        return True
    palabras = re.findall(r"\w+", tit.lower())
    return bool(palabras) and palabras[-1] in PALABRAS_QUE_CONTINUAN_TITULO


# ------------------------------------------------- pies de página (e0-r2, U-R2-CODIGO-2)
_COMILLAS_PIE = "\"“”'«»‘’"
RE_PIE_COMUNICACION = re.compile(r"comunicaci[oó]n\s*[" + _COMILLAS_PIE + r"]?\s*(?P<l>[ABC])\s*[" + _COMILLAS_PIE
                                 + r"]?\s*(?P<n>\d{1,2}\.?\d{3}|\d{1,4})", re.I)
RE_PIE_VERSION_HOJA = re.compile(r"versi[oó]n\s*:\s*(?P<v>\S+?)\s*comunicaci", re.I)
RE_PIE_HOJA = re.compile(r"p[aá]gina\s+(\d+)", re.I)
RE_PIE_FECHA = re.compile(r"(?<!\d)(\d{1,2})[/.](\d{1,2})[/.](\d{2,5})(?!\d)")
RE_ULTIMA_COMUNICACION = re.compile(
    r"ltima\s+comunicaci[oó]n\s+incorporada\s*:?\s*[" + _COMILLAS_PIE + r"]?\s*([ABC])\s*[" + _COMILLAS_PIE
    + r"]?\s*(\S+?)-?\s*(?:texto ordenado al\s*(.*))?$", re.I)
CRITERIO_VERSION_VIGENTE = ("entre las páginas legibles, la de vigencia más reciente; si empatan, la de mayor número "
                            "de Comunicación")


def _fecha_pie(s: str):
    import datetime  # noqa: PLC0415
    m = RE_PIE_FECHA.search(s)
    if not m:
        return None
    d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    a = a + 2000 if a < 100 else a
    try:
        return datetime.date(a, mes, d)
    except ValueError:
        return None


def renglones_del_pie(lineas: list[Linea]) -> list[str] | None:
    """Renglones del pie de una página con el criterio con que e0-r2 lo
    recorta (`separar_encabezado_pie`, `pie_desde_version`): la línea de
    RE_PIE_VERSION entre las últimas VENTANA_PIE_VERSION y las que la
    siguen, más los renglones de RE_PIE que quedan encima. None si la página
    no tiene pie de versión."""
    textos = [ln.texto.strip() for ln in lineas]
    for i in range(len(textos) - 1, max(-1, len(textos) - 1 - VENTANA_PIE_VERSION), -1):
        if RE_PIE_VERSION.match(textos[i]):
            j = i
            while j > 0 and any(p.match(textos[j - 1]) for p in RE_PIE):
                j -= 1
            return textos[j:i] + textos[i:]
    return None


def leer_pie(lineas: list[Linea]) -> dict:
    """Pie de una página (U-R2-CODIGO-2, C2, punto n): estado («legible»:
    trae la Comunicación y una fecha; «no_legible»: hay línea de versión pero
    falta una de las dos; «sin_pie»), versión de la hoja (None si no se lee),
    Comunicación, número de hoja, fecha de vigencia y renglones."""
    pie = renglones_del_pie(lineas)
    if pie is None:
        return {"estado": "sin_pie"}
    txt = " ".join(pie)
    mc, mv, mh = RE_PIE_COMUNICACION.search(txt), RE_PIE_VERSION_HOJA.search(txt), RE_PIE_HOJA.search(txt)
    f = _fecha_pie(" ".join(x for x in pie if not RE_PIE_COMUNICACION.search(x)) or txt)
    ver = mv.group("v") if mv else None
    ver_ok = bool(ver and re.fullmatch(r"\d+[aª]?\.?", ver))
    return {"estado": "legible" if (mc and f) else "no_legible", "version_hoja": ver if ver_ok else None,
            "version_hoja_legible": ver_ok,
            "comunicacion": f"{mc.group('l').upper()} {mc.group('n').replace('.', '')}" if mc else None,
            "hoja": int(mh.group(1)) if mh else None, "vigencia": f.isoformat() if f else None, "lineas": pie}


def pies_de_paginas(to: str, archivo: str, paginas: list[list[Linea]], roles: list[str]) -> dict:
    """`pies_<to>.json` de e0-r2 (U-R2-CODIGO-2, C2, punto n; diseño aprobado
    en r2_codigo2/freno_c2_diseno.md): el pie de cada página (`leer_pie`), la
    versión vigente del TO (CRITERIO_VERSION_VIGENTE; valor «Comunicación A
    8378 (vigencia 20/12/2025)») y la «Última comunicación incorporada» de la
    carátula, donde se lee, con el contraste. Las páginas sin pie y los pies
    que no se leen no cuentan para la versión."""
    import datetime  # noqa: PLC0415
    filas = [{"pagina": i, "rol": rol, **leer_pie(ls)} for i, (ls, rol) in enumerate(zip(paginas, roles), 1)]
    leg = [f for f in filas if f["estado"] == "legible"]
    vig = max(leg, key=lambda f: (f["vigencia"], int(f["comunicacion"].split()[1]))) if leg else None
    car = None
    for ln in (paginas[0][:20] if paginas else []):
        m = RE_ULTIMA_COMUNICACION.search(ln.texto.strip())
        if m:
            car = {"ultima_comunicacion_incorporada": f"{m.group(1).upper()} {m.group(2)}",
                   "texto_ordenado_al": (m.group(3) or "").strip() or None, "linea": ln.texto.strip()}
            break
    coincide = (None if car is None or vig is None
                or not re.fullmatch(r"\d+", car["ultima_comunicacion_incorporada"].split()[1])
                else car["ultima_comunicacion_incorporada"] == vig["comunicacion"])
    estados: dict[str, int] = {}
    for f in filas:
        estados[f["estado"]] = estados.get(f["estado"], 0) + 1
    return {"to": to, "archivo": archivo, "criterio_version_vigente": CRITERIO_VERSION_VIGENTE,
            "paginas": len(filas), "estados": dict(sorted(estados.items())),
            "version_vigente": None if vig is None else {
                "comunicacion": vig["comunicacion"], "vigencia": vig["vigencia"], "pagina": vig["pagina"],
                "valor": f"Comunicación {vig['comunicacion']} (vigencia "
                         f"{datetime.date.fromisoformat(vig['vigencia']).strftime('%d/%m/%Y')})"},
            "caratula": car, "coincide_con_la_caratula": coincide, "paginas_detalle": filas}


# ----------------------------------------------------------------- estructura

@dataclass
class Nodo:
    tipo: str                    # 'seccion' | 'punto'
    numero: str                  # '3' para sección, '3.9.1' para punto
    titulo: str                  # texto de la línea de label tras el número
    pagina: int
    label_x0: float | None = None
    text_col: float | None = None
    col_hijos: float | None = None       # columna donde corren los labels de sus hijos
    linea_label: Linea | None = None
    segmentos: list[list[Linea]] = field(default_factory=list)
    hijos: list["Nodo"] = field(default_factory=list)
    padre: "Nodo | None" = None
    sintetica: bool = False      # raíz del modo sin raíz (B5.8.1); jamás en vigente
    numero_impreso: str | None = None   # e0-r2: el número impreso, si una lista lo corrigió (U-R2-CODIGO-2)
    # regla 9 de S0 (S0-1 bis): renglones de la fila de catálogo del punto que están antes del renglón de su
    # número (la descripción empieza más arriba, centrada en la fila); el texto del punto los lleva antes del label
    lineas_previas: list[Linea] = field(default_factory=list)
    # U-SEG-OFICIAL, S0-4: prefijo del sub-documento (solo en las raíces; los puntos lo toman de su raíz) y punto
    # abierto por la regla de apartados de una sección sin puntos
    prefijo: str | None = None
    apartado: bool = False
    # U-SEG-OFICIAL, S0-6a (A): rango de la división que abrió el nodo (RANGO_BANDA_A, RANGO_APARTADO_A, RANGO_TITULO_A)
    rango_a: int | None = None

    def profundidad(self) -> int:
        return self.numero.count(".") + 1 if self.tipo == "punto" else 0


@dataclass
class ResultadoParseo:
    to: str
    archivo: str
    secciones: list[Nodo]
    rechazos_header: list[dict]
    saltos_numeracion: list[dict]
    avisos: list[dict]
    accounting: dict
    lineas_contenido: int
    paginas_cuerpo: int
    lineas_huerfanas: int = 0
    reasignaciones_continuidad: list[dict] = field(default_factory=list)
    correccion_fronteras: dict = field(default_factory=dict)
    modo_lectura: str = "vigente"   # "sin_raiz" solo cuando parsea el modo B5.8.1
    subdocumentos: list[dict] = field(default_factory=list)   # U-SEG-OFICIAL, S0-4 (registro de sub-documentos)
    rotulos_letra: list[dict] = field(default_factory=list)   # S0-4a-ter, regla sdlh sin sdl (rótulos de letra)
    bandas_a: dict = field(default_factory=dict)      # S0-6a, A: renglones de la banda de encabezado de cada página de cuerpo
    recuadro_i: set = field(default_factory=set)      # S0-6a, I: ids de los renglones del recuadro de un formulario
    paginas_caratula_a: set = field(default_factory=set)   # S0-6a-bis, A: la página 1 leída como cuerpo, si es carátula


def _componentes(num: str) -> list[int]:
    return [int(x) for x in num.split(".")]


def _termina_en_referencia_r5d(texto: str) -> bool:
    """R5-d de S0-5a: el renglón termina en una palabra de PALABRAS_REFERENCIA_R5D (sin comillas ni paréntesis)."""
    toks = texto.strip().split()
    return bool(toks) and toks[-1].strip("«»“”\"'()").lower() in PALABRAS_REFERENCIA_R5D


def _columna_hermanos_r5d(pila: list["Nodo"], num: str) -> float | None:
    """R5-d de S0-5a: la columna de los rótulos de los hermanos del punto `num`: la del último hermano abierto en su
    padre (abierto en la pila) o, si no tiene hermanos, la de los hijos del padre; None si no hay columna."""
    comp = num.split(".")
    padre_num = ".".join(comp[:-1])
    padre = None
    for n in pila:
        if (n.tipo == "seccion" and len(comp) == 2) or (n.tipo == "punto" and n.numero == padre_num):
            padre = n
            break
    if padre is None:
        return None
    hermanos = [h for h in padre.hijos if h.tipo == "punto"]
    if hermanos and hermanos[-1].label_x0 is not None:
        return hermanos[-1].label_x0
    return padre.col_hijos


def unir_numero_partido_g(lineas: list[Linea]) -> tuple[list[Linea], list[dict]]:
    """G de S0-6a (ver RE_DIGITOS_G): los renglones de un número partido por el extractor se unen en uno. Devuelve los
    renglones de la página y un evento por número unido."""
    out: list[Linea] = []
    eventos: list[dict] = []
    i = 0
    while i < len(lineas):
        l = lineas[i]
        t = l.texto.strip()
        m = RE_DIGITOS_G.match(t)
        if m:
            digs = m.group(1).split()
            vecinos = [j for j in (i + 1, i - 1) if 0 <= j < len(lineas) and lineas[j].pagina == l.pagina
                       and abs(lineas[j].top - l.top) <= DIST_NUMERO_PARTIDO_G
                       and RE_PUNTOS_G.match(lineas[j].texto.strip())
                       and lineas[j].texto.count(".") == len(digs)]
            if vecinos:
                j = vecinos[0]
                texto = ".".join(digs) + "." + m.group(2)
                if j == i - 1:
                    out.pop()
                out.append(Linea(pagina=l.pagina, top=l.top, x0=min(l.x0, lineas[j].x0), texto=texto, ngaps=l.ngaps,
                                 ultimo_numerico=l.ultimo_numerico, primer_codigo=l.primer_codigo))
                eventos.append({"tipo": "numero_partido_g", "pagina": l.pagina, "texto": texto[:90],
                                "renglones": [l.texto[:40], lineas[j].texto[:40]]})
                i += 2 if j == i + 1 else 1
                continue
        if RE_DIGITO_O_PUNTO_G.match(t):
            k = i
            while k < len(lineas) and lineas[k].pagina == l.pagina and RE_DIGITO_O_PUNTO_G.match(lineas[k].texto.strip()):
                k += 1
            if k < len(lineas) and k - i >= 2 and lineas[k].pagina == l.pagina:
                texto = "".join(x.texto.strip() for x in lineas[i:k]) + lineas[k].texto.strip()
                if RE_NUM_TOKEN.match(texto.split()[0]):
                    out.append(Linea(pagina=l.pagina, top=l.top, x0=min(x.x0 for x in lineas[i:k + 1]), texto=texto,
                                     ngaps=lineas[k].ngaps, ultimo_numerico=lineas[k].ultimo_numerico,
                                     primer_codigo=False))
                    eventos.append({"tipo": "numero_partido_g", "pagina": l.pagina, "texto": texto[:90],
                                    "renglones": [x.texto[:40] for x in lineas[i:k + 1]]})
                    i = k + 1
                    continue
        out.append(l)
        i += 1
    return out, eventos


def _partes_i(l: Linea) -> list[Linea]:
    """I de S0-6a: las partes de un renglón separadas por huecos de columna (GAP_COL), cada una como renglón."""
    if not l.palabras or l.ngaps == 0:
        return [l]
    grupos, actual = [], [l.palabras[0]]
    for a, b in zip(l.palabras, l.palabras[1:]):
        if b[0] - a[1] > GAP_COL:
            grupos.append(actual)
            actual = []
        actual.append(b)
    grupos.append(actual)
    out = []
    for g in grupos:
        texto = " ".join(w[2] for w in g)
        out.append(Linea(pagina=l.pagina, top=l.top, x0=g[0][0], texto=texto, ngaps=0,
                         ultimo_numerico=bool(RE_NUMERICO.match(g[-1][2])), primer_codigo=bool(re.match(r"^\d{3}", g[0][2])),
                         palabras=tuple(g)))
    return out


def leer_recuadro_por_columna_i(lineas: list[Linea], contenido: list[Linea]) -> tuple[list[Linea], list[Linea], str | None,
                                                                                     dict | None]:
    """I de S0-6a (ver MAX_SALTO_RECUADRO_I): (contenido con el recuadro leído por columna, renglones del recuadro, rótulo
    del formulario o None, evento o None). La página es de formulario si el membrete está entre sus primeros
    POS_MEMBRETE_SD renglones (como en `limites_subdocumento`; el recorte de encabezado puede haberlo descartado). Sin
    recuadro de dos columnas, el contenido no cambia."""
    if not contenido or not any(RE_MEMBRETE_SD.search(l.texto) for l in lineas[:POS_MEMBRETE_SD]):
        return contenido, [], None, None
    n = 1
    while n < len(contenido) and contenido[n].pagina == contenido[0].pagina \
            and contenido[n].top - contenido[n - 1].top <= MAX_SALTO_RECUADRO_I:
        n += 1
    partes = [p for l in contenido[:n] for p in _partes_i(l)]
    xs = sorted({p.x0 for p in partes})
    huecos = [(b - a, b) for a, b in zip(xs, xs[1:])]
    if not huecos or max(huecos)[0] < MIN_HUECO_COLUMNAS_I:
        return contenido, [], None, None
    corte = max(huecos)[1]
    izq = [p for p in partes if p.x0 < corte - TOL_X]
    der = [p for p in partes if p.x0 >= corte - TOL_X]
    recuadro = izq + der
    titulo = " ".join(p.texto.strip() for p in der) if sum(len(p.texto.split()) for p in der) >= 2 else None
    if titulo is None and n < len(contenido) and _es_titulo_mayusculas(contenido[n].texto) \
            and len(contenido[n].texto.strip()) <= 80:
        titulo = contenido[n].texto.strip()
    evento = {"tipo": "recuadro_por_columna_i", "pagina": contenido[0].pagina, "renglones": n,
              "izquierda": [p.texto[:40] for p in izq], "derecha": [p.texto[:40] for p in der], "rotulo": titulo}
    return recuadro + contenido[n:], recuadro, titulo, evento


def es_caratula_j(lineas: list[Linea]) -> bool:
    """J de S0-6a (ver RE_CARATULA_J): la página es la carátula del TO."""
    ts = [l.texto.strip() for l in lineas if l.texto.strip()]
    return (0 < len(ts) <= MAX_RENGLONES_CARATULA_J and any(RE_CARATULA_J.search(t) for t in ts)
            and not any(RE_NUM_TOKEN.match(t.split()[0]) or RE_NUM_TOKEN_SIN_PUNTO.match(t.split()[0]) for t in ts)
            and not any(RE_SECCION.match(t) for t in ts))


def _bloque_tope_f(contenido: list[Linea]) -> int:
    """F1 de S0-6a: cuántos renglones del tope del contenido forman un bloque de celdas cortas sin rótulo de punto."""
    n = 0
    for l in contenido:
        t = l.texto.strip()
        tok = t.split()[0] if t.split() else ""
        if not t or len(t) > MAX_CHARS_CELDA_F or RE_NUM_TOKEN.match(tok) or RE_NUM_TOKEN_SIN_PUNTO.match(tok):
            break
        n += 1
    return n


def parsear_cuerpo(to: str, archivo: str, paginas: list[list[Linea]],
                   roles: list[str], modo_sin_raiz: bool = False,
                   marcadores_b582: bool = False,
                   mayusculas_repetidas: set | None = None,
                   pie_desde_version: bool = False,
                   cola_titulo_estricta: frozenset = frozenset(),
                   renumeraciones: dict | None = None,
                   seccion_variante: bool = False,
                   rotulos_r2: bool = False,
                   marcador_letra: bool = False,
                   reabrir_padre: bool = False,
                   no_rotulos: frozenset = frozenset(),
                   indice_l: frozenset = frozenset(),
                   rotulos_fila: frozenset = frozenset(),
                   formas_m1: frozenset = frozenset(),
                   formas_m2: frozenset = frozenset(),
                   formas_m5: frozenset = frozenset(),
                   subdocumentos: list[dict] | None = None,
                   g3_subdoc: bool = False,
                   raiz_max_subdoc: bool = False,
                   letra_corte: bool = False,
                   letra_herencia: bool = False,
                   letra_numero: bool = False,
                   apartados_seccion: bool = False,
                   numero_en_referencia: bool = False,
                   rotulos_por_lista: tuple = (),
                   raices_por_lista: tuple = (),
                   raiz_sucesora_e: bool = False,
                   numero_partido_g: bool = False,
                   numero_pegado_h: bool = False,
                   pie_formulario_k: bool = False,
                   caratula_j: bool = False,
                   encabezado_tabla_f: bool = False,
                   recuadro_i: bool = False,
                   banda_a: bool = False) -> ResultadoParseo:
    """Con `modo_sin_raiz=False` (todos los call sites vigentes) el
    comportamiento es el histórico. Con True rige además la gramática de
    raíces sintéticas del modo sin raíz de sección (B5.8.1; ver docstring del
    módulo): SOLO debe invocarse así tras comprobar que el camino vigente
    produjo cero unidades para el TO.

    Con `marcadores_b582=True` (B5.8.2; misma condición de activación, y
    nunca combinado con modo_sin_raiz en los call sites) rigen además las
    variantes de encabezado de sección y el descarte de banner de caja mixta
    (ver docstring del módulo).

    `cola_titulo_estricta` y `renumeraciones` (solo la versión e0-r2,
    U-R2-CODIGO-2; ver el docstring del módulo): la primera es el conjunto
    de páginas del TO donde `separar_encabezado_pie` aplica la cola de
    título estricta; la segunda, la lista {(TO, página, número impreso):
    número} de encabezados de punto que se abren con el número corregido.

    U-SEG-OFICIAL, S0 (solo e0-r2; ver las constantes de la sección «U-SEG-OFICIAL, S0»):
    `seccion_variante` (regla 1), `rotulos_r2` (regla 2), `marcador_letra` (regla 4, solo con
    modo_sin_raiz) y `reabrir_padre` (punto 7: un rótulo con título en mayúscula cuyo padre se cerró
    por un re-anclaje de prosa a un ancestro reabre ese padre, si es el último hijo de la cadena
    abierta, y la prosa re-anclada después del padre vuelve a él o a su último hijo terminal).
    `no_rotulos` (regla 8): (página, top) de los renglones de las listas de puntos leídas como cuerpo
    (`lineas_de_listas_r8`), que no abren raíz ni se aceptan como punto. `rotulos_fila` (regla 9, parte
    9a): (página, top) de los renglones con el número de una fila de catálogo, que son rótulo aunque su
    resto siga en minúscula.

    U-SEG-OFICIAL, S0-3 (solo e0-r2; vacíos, ninguna rama nueva corre). `formas_m1` (mecanismo 1, cuerpo de punto
    que quedaba como intersticial del padre): «a», la prosa que sigue a un punto que todavía es solo su rótulo y
    que está en la columna del rótulo es cuerpo del punto, salvo que un hermano anterior tenga el cuerpo más
    adentro que su rótulo (sangría colgante: en ese documento, la prosa a la altura del rótulo es del padre, como
    el cierre del 2.7 de ext); «b», un punto cuyo cuerpo corre a la izquierda de su rótulo no devuelve prosa a un
    ancestro (snp_cheq 7.1.x: las descripciones de campos coinciden por azar con la columna de texto de 7.1).
    `formas_m2` (mecanismo 2, numeración o título no leído, solo en el modo sin raíz): «a», número pegado al título
    («4.Integración…»); «b», número con guion y título en mayúsculas («1- INTRODUCCIÓN»); «c», una raíz con título
    en mayúsculas sin punto final no se rechaza por la columna (G3). En las tres, la raíz sucede exactamente a la
    anterior (o es la 1): si no, el renglón queda como antes; en las formas a y b, además, el renglón no se repite
    textualmente en la zona de título de MIN_PAGS_BANNER páginas o más (`detectar_banners_texto`), y la raíz no fija
    la columna de las raíces. `formas_m5` (mecanismo 5, zona de encabezado):
    las formas a, b y c de `separar_encabezado_pie`.

    U-SEG-OFICIAL, S0-4 (solo e0-r2; con los defaults ninguna rama nueva corre). `subdocumentos` (regla de
    sub-documento): los límites de `limites_subdocumento`. En cada uno se cierra la pila, se abre una raíz sintética
    «0» con el prefijo del sub-documento (su título es el renglón del rótulo; si el rótulo es un renglón de contenido,
    es su renglón de label) y la numeración de raíces vuelve a empezar (G2 y G3 sin estado); las raíces que se abren
    después llevan el prefijo. Un rótulo que quedó en la zona de encabezado abre el sub-documento al empezar su página.
    La raíz «0» que no lleva texto se retira al final, como el preámbulo; el registro de sub-documentos queda en
    `ResultadoParseo.subdocumentos` (lo usa la herencia). `g3_subdoc`: dentro de un sub-documento, la guarda de
    columna (G3) no rechaza una raíz con forma de título que sucede exactamente a la anterior («4. Periodicidad…» de
    nmcief, 9,5 pt más adentro que la 3). `raiz_max_subdoc` (S0-4a-bis): dentro de un sub-documento, en el modo sin
    raíz, una raíz explícita mayor que MAX_RAIZ no se rechaza si sucede exactamente a la anterior (ri_ccna, Anexo III
    de la primera norma: ítems 31 a 40); las demás guardas rigen igual. S0-4a-ter, con los límites de la forma de
    letra (`limites_subdocumento(letras=True)`): `letra_corte` (regla sdl) los abre como los demás sub-documentos;
    `letra_herencia` (regla sdlh) hace que las unidades del sub-documento de letra hereden su rótulo, o, sin
    `letra_corte`, que lo hereden las raíces abiertas después del rótulo en el mismo contenedor (hasta el rótulo de
    letra siguiente); `letra_numero` (regla sdla), en el modo sin raíz, abre la raíz «X.n» en un renglón «X.n. Título»
    cuya letra es la del último rótulo de letra del contenedor, más afuera que la raíz numérica abierta (ri_ccna:
    «A.3. El relevamiento…» después del ítem 2 de A.2). `apartados_seccion` (apartados de una sección
    sin puntos): en una sección
    de la lectura vigente que no tiene puntos, un rótulo de un nivel «N. Título» con N = 1, 2, 3… consecutivos abre
    el punto «<sección>.N» (número impreso N), en lugar de rechazarse por estar fuera de la sección (ri_ai, Sección 4:
    «1. Posición», «2. Franquicias», «3. Incumplimientos»).

    U-SEG-OFICIAL, S0-5a (solo e0-r2; con el default no corre). `numero_en_referencia` (R5-d, ver
    PALABRAS_REFERENCIA_R5D): un renglón que empieza con un número de punto y continúa una remisión del renglón
    anterior (que termina en una palabra de referencia), en la columna de ese renglón y no en la de los rótulos de sus
    hermanos, sigue como prosa («…descripto en el punto» / «1.3. “Integración” de las presentes normas…» en ri_rml).

    U-SEG-OFICIAL, S0-5a-bis (solo e0-r2; con el default no corre). `rotulos_por_lista` (R5-f, ver TOL_TOP_POR_LISTA):
    el renglón de cada (página, top, número, padre) abre el punto `número`, hijo del padre dado o, si es None, del que
    indica el número (la sección, con un número de dos componentes), si ese padre está abierto; sin las validaciones de
    siempre (número pegado al texto, texto en minúscula, hermano anterior, padre no abierto). El texto del renglón no
    cambia: el título del punto es lo que sigue al número.

    `raices_por_lista` (R5-g de S0-5a-bis, modo sin raíz; con el default no corre): el renglón de cada (página, top,
    número) abre la raíz explícita `número` aunque esté más adentro que la columna de las raíces (guarda G3); las otras
    guardas (banner, forma de título, sucesión, regla 8) siguen. La columna de las raíces no cambia.

    U-SEG-OFICIAL, S0-6a (solo e0-r2; con los defaults no corre): `raiz_sucesora_e` (E), `numero_partido_g` (G),
    `numero_pegado_h` (H), `pie_formulario_k` (K), `caratula_j` (J), `encabezado_tabla_f` (F1) y `recuadro_i` (I); ver
    RE_DIGITOS_G y las constantes que lo siguen. `banda_a` (A) registra en `ResultadoParseo.bandas_a` los renglones de la
    banda de encabezado de cada página de cuerpo, que lee `dividir_a`."""
    secciones: list[Nodo] = []
    rechazos: list[dict] = []
    saltos: list[dict] = []
    avisos: list[dict] = []
    acc_descartes: list[dict] = []
    pila: list[Nodo] = []                # [seccion, punto, subpunto, …]
    n_contenido = 0
    n_paginas_cuerpo = 0
    n_huerfanas = 0

    # estado del modo sin raíz (inerte con modo_sin_raiz=False)
    banners = detectar_banners(paginas) if modo_sin_raiz else set()
    nodo_preambulo: Nodo | None = None
    ultima_raiz_num: int | None = None   # última raíz/sección abierta (monotonía G2)
    col_raiz: float | None = None        # columna mínima de raíz explícita aceptada (G3)
    # estado B5.8.2 (inerte con marcadores_b582=False)
    banners_texto = detectar_banners_texto(paginas) if marcadores_b582 else None
    # mecanismo 2 de S0-3: renglones repetidos textualmente en la zona de título (no abren raíz por una forma nueva)
    banners_m2 = detectar_banners_texto(paginas) if (formas_m2 and modo_sin_raiz) else set()
    # regla de sub-documento de S0-4 (inerte sin `subdocumentos`)
    sd_por_pagina: dict[int, list[dict]] = {}
    for b in subdocumentos or ():
        if b["forma"] != "letra" or letra_corte:     # regla sdl de S0-4a-ter: la forma de letra abre solo con ella
            sd_por_pagina.setdefault(b["pagina"], []).append(b)
    sd_por_linea: dict[tuple, dict] = {}
    subdoc_actual: str | None = None
    registro_sd: list[dict] = []
    # S0-4a-ter: los rótulos de letra (para sdlh sin sdl y para sdla) y la letra vigente del contenedor
    rotulos_letra = [b for b in subdocumentos or () if b["forma"] == "letra"]
    rotulo_letra_por_pos = {(b["pagina"], b["top"]): b for b in rotulos_letra}
    letra_vigente: tuple | None = None    # (letra, prefijo del contenedor)
    bloque_previo_f: list | None = None   # F1 de S0-6a: el bloque del tope de la página de cuerpo anterior
    recuadro_ids: set = set()             # I de S0-6a
    bandas: dict = {}                     # A de S0-6a

    def cerrar_hasta(nodo: Nodo | None) -> None:
        """Deja la pila abierta hasta `nodo` inclusive (None → vacía)."""
        while pila and (nodo is None or pila[-1] is not nodo):
            pila.pop()

    def anexar(nodo: Nodo, linea: Linea, nuevo_segmento: bool) -> None:
        if nuevo_segmento or not nodo.segmentos or nodo.segmentos[-1] is None:
            nodo.segmentos.append([linea])
        else:
            nodo.segmentos[-1].append(linea)

    # ---- punto 7 de S0 (reabrir_padre); inertes sin el parámetro ----
    def _pos(l: Linea) -> tuple:
        return (l.pagina, l.top)

    def _ultima_pos(n: Nodo) -> tuple:
        ps = [_pos(n.linea_label)] if n.linea_label is not None else []
        ps += [_pos(s[-1]) for s in n.segmentos if s]
        ps += [_ultima_pos(h) for h in n.hijos]
        return max(ps) if ps else (n.pagina, 0.0)

    def camino_para_reabrir(padre_num: str) -> list[Nodo] | None:
        """Desde el nodo más profundo de la pila, baja por últimos hijos hasta el punto
        `padre_num`; None si en algún paso el último hijo no es un ancestro de ese punto (hay
        algo abierto después) o si no existe."""
        if not pila:
            return None
        n, camino = pila[-1], []
        while n.hijos:
            h = n.hijos[-1]
            if h.tipo != "punto":
                return None
            if h.numero == padre_num:
                return camino + [h]
            if not padre_num.startswith(h.numero + "."):
                return None
            camino.append(h)
            n = h
        return None

    def reabrir(camino: list[Nodo], hijo: str, linea: Linea) -> None:
        """Reabre el punto (último de `camino`): la prosa de la pila posterior a su última línea
        (la que el re-anclaje le dio a un ancestro) vuelve a él, o a su último hijo si es terminal
        (continuación), y la pila sigue por el camino."""
        objetivo = camino[-1]
        tope = _ultima_pos(objetivo)
        movidos = []
        for x in pila:
            for sg in list(x.segmentos):
                if sg and _pos(sg[0]) > tope:
                    x.segmentos.remove(sg)
                    movidos.append(sg)
        movidos.sort(key=lambda sg: _pos(sg[0]))
        destino = objetivo.hijos[-1] if objetivo.hijos and not objetivo.hijos[-1].hijos else objetivo
        destino.segmentos.extend(movidos)
        pila.extend(camino)
        avisos.append({"tipo": "padre_reabierto_r2", "numero": objetivo.numero, "hijo": hijo,
                       "pagina": linea.pagina, "segmentos_devueltos": len(movidos),
                       "lineas_devueltas": sum(len(sg) for sg in movidos), "destino": destino.numero})

    def abrir_subdocumento(b: dict, linea: Linea | None) -> None:
        """Regla de sub-documento de S0-4: raíz «0» del sub-documento y numeración de raíces desde cero."""
        nonlocal ultima_raiz_num, col_raiz, subdoc_actual, letra_vigente
        cerrar_hasta(None)
        raiz = Nodo(tipo="seccion", numero="0", titulo=b["titulo"], pagina=b["pagina"],
                    label_x0=linea.x0 if linea is not None else None, linea_label=linea, sintetica=True,
                    prefijo=b["prefijo"])
        secciones.append(raiz)
        pila.append(raiz)
        ultima_raiz_num = None
        col_raiz = None
        subdoc_actual = b["prefijo"]
        registro_sd.append({"prefijo": b["prefijo"], "forma": b["forma"], "titulo": b["titulo"],
                            "pagina": b["pagina"], "padre": b["padre"]})
        if b["forma"] == "letra":
            # reglas sdl y sdlh de S0-4a-ter: el rótulo de letra se hereda solo con sdlh
            registro_sd[-1]["heredable"] = letra_herencia
            letra_vigente = (b["letra"], b["prefijo"])
        else:
            letra_vigente = None
        avisos.append({"tipo": "subdocumento_sd", "forma": b["forma"], "prefijo": b["prefijo"],
                       "pagina": b["pagina"], "texto": b["titulo"][:90]})

    paginas_caratula_a: set = set()
    for pi, (lineas, rol) in enumerate(zip(paginas, roles), start=1):
        if rol != ROL_CUERPO:
            continue
        n_paginas_cuerpo += 1
        if pi == 1 and len(lineas) <= MAX_RENGLONES_CARATULA_J:
            paginas_caratula_a.add(pi)     # S0-6a-bis: carátula para A (el tope de renglones de J)
        contenido, descartadas, seccion_corrida = separar_encabezado_pie(
            lineas, labels_preservables=banners if modo_sin_raiz else None,
            seccion_b582=marcadores_b582, banners_texto=banners_texto,
            mayusculas_repetidas=mayusculas_repetidas, pie_desde_version=pie_desde_version,
            cola_titulo_estricta=pi in cola_titulo_estricta, seccion_variante=seccion_variante,
            seccion_abierta=(next((x.numero for x in reversed(secciones) if x.numero.isdigit()
                                   and not x.sintetica), None) if seccion_variante else None),
            cierre_m5="a" in formas_m5, cola_m5="b" in formas_m5, zona6_m5="c" in formas_m5,
            pie_formulario_k=pie_formulario_k)
        caratula = caratula_j and pi == 1 and es_caratula_j(lineas)
        if caratula:
            # J de S0-6a: la carátula no pierde renglones por el recorte de encabezado y pie
            contenido, descartadas, seccion_corrida = list(lineas), [], None
            avisos.append({"tipo": "caratula_j", "pagina": pi, "renglones": len(contenido)})
        if encabezado_tabla_f:
            # F1 de S0-6a: el bloque del tope que repite el de la página de cuerpo anterior es encabezado reimpreso
            n_f = _bloque_tope_f(contenido)
            firma_f = sorted(tok for l in contenido[:n_f] for tok in l.texto.split()) if n_f >= 2 else None
            if firma_f is not None and firma_f == bloque_previo_f:
                descartadas = descartadas + contenido[:n_f]
                avisos.append({"tipo": "encabezado_de_tabla_repetido_f", "pagina": pi, "renglones": n_f,
                               "texto": " | ".join(l.texto for l in contenido[:n_f])[:120]})
                contenido = contenido[n_f:]
            bloque_previo_f = firma_f
        if numero_partido_g:
            contenido, eventos_g = unir_numero_partido_g(contenido)     # G de S0-6a
            avisos.extend(eventos_g)
        if recuadro_i:
            # I de S0-6a: el recuadro de encabezado de un formulario se lee por columna
            contenido, recuadro, titulo_i, evento_i = leer_recuadro_por_columna_i(lineas, contenido)
            if evento_i is not None:
                avisos.append(evento_i)
                recuadro_ids.update(id(l) for l in recuadro)
                if titulo_i:
                    for b in sd_por_pagina.get(pi, []):
                        if b["forma"] == "formulario":
                            b["titulo"] = titulo_i     # el membrete nunca es madre
        if banda_a:
            # A de S0-6a: la banda de encabezado de la página (lo descartado arriba del contenido)
            tope_a = contenido[0].top if contenido else float("inf")
            bandas[pi] = [d.texto for d in descartadas
                          if d.top < tope_a and not (seccion_corrida and d.texto.strip() in seccion_corrida)]
        # regla 1 de S0: en una página cuya sección se leyó por la variante, el modo sin raíz no abre
        # raíces sintéticas (los ítems «1.», «2.» de la sección no son raíces: dmrd p. 6)
        pagina_con_variante = bool(seccion_variante and seccion_corrida is not None
                                   and not RE_SECCION.match(seccion_corrida))
        for d in descartadas:
            acc_descartes.append({"pagina": d.pagina, "texto": d.texto})
        if sd_por_pagina.get(pi):
            # regla de sub-documento de S0-4: el rótulo que quedó en la zona de encabezado abre el sub-documento al
            # empezar la página; el que es un renglón de contenido, en ese renglón
            en_contenido = {(l.pagina, l.top) for l in contenido}
            for b in sd_por_pagina[pi]:
                if (b["pagina"], b["top"]) in en_contenido:
                    sd_por_linea[(b["pagina"], b["top"])] = b
                else:
                    abrir_subdocumento(b, None)

        if seccion_corrida is None:
            if not modo_sin_raiz:
                # en el modo sin raíz la ausencia de 'Sección N.' es la condición
                # de entrada del TO, no una anomalía por página
                avisos.append({"tipo": "pagina_cuerpo_sin_seccion", "pagina": pi,
                               "primeras_lineas": [l.texto for l in contenido[:3]]})
            # las líneas siguen el flujo del punto abierto (página de continuación
            # con encabezado anómalo); no se tiran.
        else:
            m = _match_seccion_r2(seccion_corrida, seccion_variante, "0")
            if m:
                num_sec, titulo_sec = m.group(1), m.group(2).strip()
            else:
                # solo alcanzable con marcadores_b582=True: la línea fue
                # capturada por una variante B5.8.2 (número VERBATIM: 'C', 'I')
                num_sec, titulo_sec = _match_seccion_b582(seccion_corrida)
            actual = pila[0] if pila else None
            if actual is None or actual.numero != num_sec:
                # arranca una sección nueva
                if any(s.numero == num_sec and s.prefijo == subdoc_actual for s in secciones):
                    avisos.append({"tipo": "seccion_reabierta", "numero": num_sec,
                                   "pagina": pi})
                cerrar_hasta(None)
                sec = Nodo(tipo="seccion", numero=num_sec, titulo=titulo_sec, pagina=pi, prefijo=subdoc_actual)
                if secciones:
                    previa_num = secciones[-1].numero
                    if num_sec.isdigit() and previa_num.isdigit():
                        if _componentes(num_sec)[0] != _componentes(previa_num)[0] + 1:
                            saltos.append({"tipo": "salto_seccion", "de": previa_num,
                                           "a": num_sec, "pagina": pi})
                    elif not _es_sucesor_seccion(previa_num, num_sec):
                        # numeración no numérica (B5.8.2): sucesión por familias
                        # de interpretación (letra/romano/número)
                        saltos.append({"tipo": "salto_seccion", "de": previa_num,
                                       "a": num_sec, "pagina": pi})
                secciones.append(sec)
                pila.append(sec)
                if modo_sin_raiz:
                    ultima_raiz_num = int(num_sec)

        if not pila:
            if not modo_sin_raiz:
                if contenido:
                    n_huerfanas += len(contenido)
                    avisos.append({"tipo": "contenido_antes_de_seccion", "pagina": pi,
                                   "n_lineas": len(contenido),
                                   "lineas": [l.texto for l in contenido[:3]]})
                continue
            if not contenido:
                continue
            # modo sin raíz: nada queda huérfano — el contenido previo a la
            # primera raíz ancla en el preámbulo sintético '0'
            if nodo_preambulo is None:
                # J de S0-6a: el preámbulo que empieza en la carátula no lleva el rótulo fabricado «Preámbulo»
                nodo_preambulo = Nodo(tipo="seccion", numero="0",
                                      titulo="" if caratula else "Preámbulo", pagina=pi, sintetica=True,
                                      prefijo=subdoc_actual)
                secciones.insert(0, nodo_preambulo)
            pila.append(nodo_preambulo)

        seccion = pila[0]
        ultima_fue_label = False
        previa: Linea | None = None
        # regla 2 (c) de S0: filas de lista de códigos de la página (sin punto final, con hueco)
        codigos_pagina = sum(1 for l in contenido if rotulos_r2 and l.ngaps >= 1 and l.texto.split()
                             and RE_NUM_TOKEN_SIN_PUNTO.match(l.texto.split()[0]))

        for linea in contenido:
            anterior, previa = previa, linea
            n_contenido += 1
            if sd_por_linea and (linea.pagina, linea.top) in sd_por_linea:
                # regla de sub-documento de S0-4: el renglón del rótulo es el label de la raíz del sub-documento
                abrir_subdocumento(sd_por_linea.pop((linea.pagina, linea.top)), linea)
                seccion = pila[0]
                ultima_fue_label = False
                continue
            if not letra_corte and (linea.pagina, linea.top) in rotulo_letra_por_pos:
                # S0-4a-ter, sin sdl: el rótulo de letra queda como texto, pero fija la letra vigente del contenedor
                letra_vigente = (rotulo_letra_por_pos[(linea.pagina, linea.top)]["letra"], subdoc_actual)
            texto_l = linea.texto      # texto del rótulo (el mecanismo 2 de S0-3 lo normaliza)
            tokens = texto_l.split()
            m_num = RE_NUM_TOKEN.match(tokens[0]) if tokens else None
            if not m_num and tokens:
                m_num = RE_NUM_TOKEN_SIN_PUNTO.match(tokens[0])
            forma_m2 = None
            if not m_num and tokens and modo_sin_raiz and formas_m2:
                # mecanismo 2 de S0-3, formas a y b: el rótulo se lee como «N. Título»
                t_m2 = linea.texto.strip()
                mp, mg = RE_NUM_PEGADO_M2.match(t_m2), RE_NUM_GUION_M2.match(t_m2)
                if mp and "a" in formas_m2:
                    texto_l, forma_m2 = f"{mp.group(1)}. {t_m2[mp.end():]}", "a"
                elif mg and "b" in formas_m2 and _es_titulo_mayusculas(t_m2[mg.end():]):
                    texto_l, forma_m2 = f"{mg.group(1)}. {t_m2[mg.end():].strip()}", "b"
                if forma_m2 and (int(texto_l.split(".")[0]) != (ultima_raiz_num + 1 if ultima_raiz_num is not None
                                                              else 1) or t_m2 in banners_m2):
                    # guardas: la raíz de una forma nueva sucede exactamente a la anterior (o es la 1) y no es un
                    # título corrido de página; si no, el renglón queda como estaba («26.ANTICIPO DE OPERACIONES»,
                    # el número del régimen en ri_ao; «3.Deudores del Sistema Financiero.», el de ri_dsf)
                    texto_l, forma_m2 = linea.texto, None
                if forma_m2:
                    tokens = texto_l.split()
                    m_num = RE_NUM_TOKEN.match(tokens[0])
            forma_h = False
            if numero_pegado_h and not m_num and tokens:
                # H de S0-6a: rótulo de punto pegado al título, al principio del renglón; se lee como «N. resto»
                mh = RE_NUM_PEGADO_H.match(linea.texto.strip())
                if mh:
                    texto_l = f"{mh.group(1)}. {linea.texto.strip()[mh.end():]}"
                    tokens = texto_l.split()
                    m_num = RE_NUM_TOKEN.match(tokens[0])
                    forma_h = True
            if rotulos_por_lista and tokens:
                # ------- R5-f de S0-5a-bis: rótulo de punto por lista -------
                rf = next((r for r in rotulos_por_lista if r[0] == linea.pagina
                           and abs(r[1] - linea.top) <= TOL_TOP_POR_LISTA
                           and linea.texto.strip().startswith(r[2] + ".")), None)
                if rf is not None:
                    num_f = rf[2]
                    padre_f = rf[3] or ".".join(num_f.split(".")[:-1])
                    padre_n = None
                    for n in pila:
                        if (n.tipo == "seccion" and "." not in padre_f and n.numero == padre_f) or \
                                (n.tipo == "punto" and n.numero == padre_f):
                            padre_n = n
                            break
                    if padre_n is not None:
                        resto_f = linea.texto.strip()[len(num_f):].lstrip(".").strip()
                        padre_n.col_hijos = padre_n.col_hijos if padre_n.col_hijos is not None else linea.x0
                        cerrar_hasta(padre_n)
                        nodo = Nodo(tipo="punto", numero=num_f, titulo=resto_f, pagina=linea.pagina,
                                    label_x0=linea.x0, linea_label=linea, padre=padre_n)
                        padre_n.hijos.append(nodo)
                        pila.append(nodo)
                        avisos.append({"tipo": "rotulo_por_lista_r5f", "numero": num_f, "padre": padre_n.numero,
                                       "prefijo": subdoc_actual, "pagina": linea.pagina, "texto": linea.texto[:90]})
                        ultima_fue_label = True
                        continue
                    avisos.append({"tipo": "rotulo_por_lista_r5f_sin_padre", "numero": num_f, "padre": padre_f,
                                   "prefijo": subdoc_actual, "pagina": linea.pagina, "texto": linea.texto[:90]})
            # regla 8 de S0: renglón de una lista de puntos leída como cuerpo (veto; no abre raíces)
            en_lista = bool(m_num) and (linea.pagina, linea.top) in no_rotulos
            en_indice_l = bool(m_num) and not en_lista and (linea.pagina, linea.top) in indice_l     # L de S0-6a-bis
            en_lista = en_lista or en_indice_l
            # regla 9 de S0: el renglón lleva el número de una fila de catálogo (la celda de la tabla es solo ese
            # número); el resto en minúscula es la descripción de la fila, no una referencia envuelta
            fila_r9 = bool(m_num) and (linea.pagina, linea.top) in rotulos_fila
            # R5-d de S0-5a: número de punto que continúa una remisión del renglón anterior. Es un veto, como el de la
            # regla 2: actúa solo sobre un rótulo que la validación de siempre aceptaría (más abajo) y no deja abrir una
            # raíz implícita; un renglón que ya se rechazaba conserva su motivo
            veto_5d = None
            if numero_en_referencia and m_num and "." in m_num.group(1) and anterior is not None and pila \
                    and linea.ngaps == 0 and abs(linea.x0 - anterior.x0) <= TOL_X \
                    and _termina_en_referencia_r5d(anterior.texto):
                col_d = _columna_hermanos_r5d(pila, m_num.group(1))
                if col_d is not None and abs(linea.x0 - col_d) > TOL_X:
                    veto_5d = {"tipo": "numero_en_referencia_r5d", "pagina": linea.pagina,
                               "numero": m_num.group(1), "x0": linea.x0, "columna_hermanos": col_d,
                               "anterior": anterior.texto[-60:], "texto": linea.texto[:90]}

            if letra_numero and modo_sin_raiz and tokens and letra_vigente is not None and pila \
                    and pila[0].sintetica and pila[0].numero.isdigit() and pila[0].numero != "0" \
                    and pila[0].label_x0 is not None and linea.x0 < pila[0].label_x0 - TOL_X:
                # ------- regla sdla de S0-4a-ter: «X.n. Título» con la letra vigente cierra la raíz numérica -------
                ml_a = RE_ROTULO_LETRA_R2.match(tokens[0])
                resto_a = linea.texto[len(tokens[0]):].strip() if ml_a else ""
                if ml_a and "." not in ml_a.group(2) and ml_a.group(1) == letra_vigente[0] \
                        and letra_vigente[1] == subdoc_actual and resto_a[:1].isupper():
                    cerrar_hasta(None)
                    raiz = Nodo(tipo="seccion", numero=f"{ml_a.group(1)}.{ml_a.group(2)}", titulo=resto_a,
                                pagina=linea.pagina, label_x0=linea.x0, linea_label=linea, sintetica=True,
                                prefijo=subdoc_actual)
                    secciones.append(raiz)
                    pila.append(raiz)
                    avisos.append({"tipo": "rotulo_letra_numero_sdla", "numero": raiz.numero,
                                   "prefijo": subdoc_actual, "pagina": linea.pagina, "texto": linea.texto[:90]})
                    ultima_fue_label = False
                    continue

            if marcador_letra and modo_sin_raiz and tokens:
                # ------- regla 4 de S0: marcador de letra y número (ri_spi) -------
                ma = RE_APARTADO_R2.match(linea.texto.strip())
                if ma:
                    cerrar_hasta(None)
                    raiz = Nodo(tipo="seccion", numero=ma.group(1), titulo=ma.group(2).strip(),
                                pagina=linea.pagina, label_x0=linea.x0, linea_label=linea, sintetica=True,
                                prefijo=subdoc_actual)
                    secciones.append(raiz)
                    pila.append(raiz)
                    ultima_fue_label = False
                    continue
                ml = RE_ROTULO_LETRA_R2.match(tokens[0])
                resto_l = linea.texto[len(tokens[0]):].strip()
                if ml and resto_l and pila and pila[0].numero == ml.group(1):
                    num_l = f"{ml.group(1)}.{ml.group(2)}"
                    partes_l = num_l.split(".")
                    padre_l = (pila[0] if len(partes_l) == 2 else
                               next((n for n in pila if n.tipo == "punto" and n.numero == ".".join(partes_l[:-1])),
                                    None))
                    hermanos_l = [h for h in padre_l.hijos if h.tipo == "punto"] if padre_l else []
                    ultimo_l = int(hermanos_l[-1].numero.split(".")[-1]) if hermanos_l else 0
                    if padre_l is None:
                        rechazos.append({"pagina": linea.pagina, "x0": linea.x0, "texto": linea.texto[:120],
                                         "motivo": f"padre_{'.'.join(partes_l[:-1])}_no_abierto"})
                    elif int(partes_l[-1]) <= ultimo_l:
                        rechazos.append({"pagina": linea.pagina, "x0": linea.x0, "texto": linea.texto[:120],
                                         "motivo": f"no_sucede_al_hermano_{ultimo_l}"})
                    else:
                        padre_l.col_hijos = padre_l.col_hijos if padre_l.col_hijos is not None else linea.x0
                        cerrar_hasta(padre_l)
                        nodo = Nodo(tipo="punto", numero=num_l, titulo=resto_l, pagina=linea.pagina,
                                    label_x0=linea.x0, linea_label=linea, padre=padre_l)
                        padre_l.hijos.append(nodo)
                        pila.append(nodo)
                        ultima_fue_label = True
                        continue

            motivo_2 = None
            if m_num and rotulos_r2:
                # ------- regla 2 de S0: rótulos de punto que no lo son. Es un veto: actúa solo
                # sobre un rótulo que la validación de siempre aceptaría (más abajo), y no deja
                # abrir una raíz implícita; un renglón que ya se rechazaba conserva su motivo -------
                resto_2 = texto_l[len(tokens[0]):].strip()
                if resto_2[:1].islower() and RE_REMISION_ENVUELTA_R2.match(resto_2):
                    motivo_2 = "remision_envuelta_r2"
                elif any(len(x) >= 3 for x in m_num.group(1).split(".")):
                    motivo_2 = "numero_con_componente_de_tres_cifras_r2"
                elif not tokens[0].endswith(".") and linea.ngaps >= 1 \
                        and codigos_pagina >= MIN_FILAS_CODIGO_R2:
                    motivo_2 = "fila_de_lista_de_codigos_r2"

            if m_num and modo_sin_raiz:
                # ------- gramática de raíces sintéticas (B5.8.1; docstring) -------
                comp_r = _componentes(m_num.group(1))
                partes = texto_l.split(None, 1)
                resto_r = partes[1] if len(partes) > 1 else ""
                titulo_may_r = bool(RE_TITULO_RAIZ.match(resto_r)) if resto_r else False
                # regla sdmax de S0-4a-bis: dentro de un sub-documento, la raíz que sucede exactamente a la anterior
                # no se rechaza por ser mayor que MAX_RAIZ
                max_sd = raiz_max_subdoc and subdoc_actual is not None and ultima_raiz_num is not None \
                    and comp_r[0] == ultima_raiz_num + 1
                if (comp_r[0] <= MAX_RAIZ or max_sd) and resto_r and len(comp_r) == 1 and not pagina_con_variante:
                    # raíz EXPLÍCITA: guardas G0-G3
                    motivo_raiz = None
                    por_e = False
                    # R5-g de S0-5a-bis: la raíz por lista no pasa por la guarda de columna G3
                    raiz_forzada = any(r[0] == linea.pagina and abs(r[1] - linea.top) <= TOL_TOP_POR_LISTA
                                       and r[2] == str(comp_r[0]) for r in raices_por_lista)
                    if _clave_banner(texto_l.strip()) in banners:
                        motivo_raiz = "raiz_banner_repetido"
                    elif not titulo_may_r:
                        motivo_raiz = "raiz_sin_forma_de_titulo"
                    elif ultima_raiz_num is not None and comp_r[0] <= ultima_raiz_num:
                        motivo_raiz = f"raiz_{comp_r[0]}_no_sucede_a_{ultima_raiz_num}"
                    elif col_raiz is not None and linea.x0 > col_raiz + TOL_X \
                            and not ("c" in formas_m2 and _es_titulo_mayusculas(resto_r)
                                     and not resto_r.rstrip().endswith(".")
                                     and comp_r[0] == (ultima_raiz_num or 0) + 1) \
                            and not (g3_subdoc and subdoc_actual is not None
                                     and comp_r[0] == (ultima_raiz_num or 0) + 1) \
                            and not raiz_forzada:
                        if raiz_sucesora_e and comp_r[0] == (ultima_raiz_num or 0) + 1 and linea.ngaps == 0 \
                                and not (anterior is not None and _termina_en_referencia_r5d(anterior.texto)):
                            por_e = True     # E de S0-6a: continúa la numeración de su nivel
                        else:
                            motivo_raiz = (f"raiz_en_columna_profunda_{linea.x0}"
                                           f"_vs_{col_raiz}")
                    if motivo_raiz is None and en_lista:
                        motivo_raiz = "indice_l" if en_indice_l else "lista_de_puntos_r8"   # veto de la regla 8 de S0 o de L
                    if motivo_raiz is None:
                        if ultima_raiz_num is not None \
                                and comp_r[0] != ultima_raiz_num + 1:
                            saltos.append({"tipo": "salto_raiz", "de": ultima_raiz_num,
                                           "a": comp_r[0], "pagina": linea.pagina})
                        cerrar_hasta(None)
                        raiz = Nodo(tipo="seccion", numero=str(comp_r[0]),
                                    titulo=resto_r, pagina=linea.pagina,
                                    label_x0=linea.x0, linea_label=linea,
                                    sintetica=True, prefijo=subdoc_actual)
                        secciones.append(raiz)
                        pila.append(raiz)
                        profunda = col_raiz is not None and linea.x0 > col_raiz + TOL_X
                        por_m2c = profunda and "c" in formas_m2 and _es_titulo_mayusculas(resto_r) \
                            and not resto_r.rstrip().endswith(".")
                        if raiz_forzada:
                            avisos.append({"tipo": "raiz_por_lista_r5g", "numero": str(comp_r[0]),
                                           "prefijo": subdoc_actual, "pagina": linea.pagina, "x0": linea.x0,
                                           "columna_raices": col_raiz, "texto": linea.texto[:90]})
                        elif forma_m2 or por_m2c:
                            avisos.append({"tipo": "raiz_m2", "forma": forma_m2 or "c", "numero": str(comp_r[0]),
                                           "pagina": linea.pagina, "texto": linea.texto[:90]})
                        elif por_e:
                            avisos.append({"tipo": "raiz_sucesora_e", "numero": str(comp_r[0]),
                                           "prefijo": subdoc_actual, "pagina": linea.pagina, "x0": linea.x0,
                                           "columna_raices": col_raiz, "texto": linea.texto[:90]})
                        elif profunda:
                            # regla sdg3 de S0-4: la raíz sucede exactamente a la anterior dentro de un sub-documento
                            avisos.append({"tipo": "raiz_g3_subdocumento_sd", "numero": str(comp_r[0]),
                                           "prefijo": subdoc_actual, "pagina": linea.pagina,
                                           "x0": linea.x0, "columna_raices": col_raiz, "texto": linea.texto[:90]})
                        if comp_r[0] > MAX_RAIZ:
                            avisos.append({"tipo": "raiz_mayor_a_max_subdocumento_sdmax", "numero": str(comp_r[0]),
                                           "prefijo": subdoc_actual, "pagina": linea.pagina,
                                           "texto": linea.texto[:90]})
                        ultima_raiz_num = comp_r[0]
                        if forma_m2 is None:
                            # mecanismo 2 de S0-3: una raíz de una forma nueva no fija la columna de las raíces (G3);
                            # en ri_dsf, «1.Instrucciones generales.» la fijaría más afuera que las raíces 3 a 8
                            col_raiz = (linea.x0 if col_raiz is None
                                        else min(col_raiz, linea.x0))
                        ultima_fue_label = False
                        continue
                    rechazos.append({"pagina": linea.pagina, "x0": linea.x0,
                                     "texto": linea.texto[:120],
                                     "motivo": motivo_raiz})
                    m_num = None    # sigue como prosa (registro único del rechazo)
                elif comp_r[0] <= MAX_RAIZ and resto_r and len(comp_r) == 2 and not motivo_2 and not veto_5d \
                        and not pagina_con_variante and not forma_h \
                        and str(comp_r[0]) != pila[0].numero and titulo_may_r \
                        and (ultima_raiz_num is None or comp_r[0] > ultima_raiz_num):
                    # raíz IMPLÍCITA en profundidad 2 (arranque medido de ri_niif);
                    # el punto en sí se valida después por la cadena vigente
                    raiz_previa = next((s for s in reversed(secciones)
                                        if s is not nodo_preambulo), None)
                    if not (raiz_previa is not None
                            and raiz_previa.col_hijos is not None
                            and linea.x0 > raiz_previa.col_hijos + TOL_X) and en_lista:
                        # veto de la regla 8 de S0: un renglón de lista no abre la raíz; queda como texto
                        rechazos.append({"pagina": linea.pagina, "x0": linea.x0, "texto": linea.texto[:120],
                                         "motivo": "lista_de_puntos_r8"})
                        m_num = None
                    elif not (raiz_previa is not None
                              and raiz_previa.col_hijos is not None
                              and linea.x0 > raiz_previa.col_hijos + TOL_X):
                        if ultima_raiz_num is not None \
                                and comp_r[0] != ultima_raiz_num + 1:
                            saltos.append({"tipo": "salto_raiz", "de": ultima_raiz_num,
                                           "a": comp_r[0], "pagina": linea.pagina})
                        cerrar_hasta(None)
                        raiz = Nodo(tipo="seccion", numero=str(comp_r[0]),
                                    titulo="", pagina=linea.pagina, sintetica=True, prefijo=subdoc_actual)
                        secciones.append(raiz)
                        pila.append(raiz)
                        ultima_raiz_num = comp_r[0]

            if m_num:
                seccion = pila[0]   # las raíces sintéticas cambian pila a mitad de página
                num = m_num.group(1)
                impreso = None
                if renumeraciones and (to, linea.pagina, num) in renumeraciones:
                    impreso, num = num, renumeraciones[(to, linea.pagina, num)]
                    avisos.append({"tipo": "renumerado_por_lista", "pagina": linea.pagina, "impreso": impreso,
                                   "numero": num, "texto": linea.texto[:90]})
                comp = _componentes(num)
                resto = texto_l.split(None, 1)
                resto = resto[1] if len(resto) > 1 else ""
                # forma del resto: un punto real lleva título/texto en la línea
                # del label. Numeración sola ('9.3.13.') = referencia envuelta,
                # rechazo incondicional. Resto en minúscula puede ser referencia
                # envuelta (RX-03: 'en el marco de…') PERO también hay labels
                # reales en minúscula (ext 10.11.1 'el pago corresponda…'): se
                # acepta solo bajo secuencia ESTRICTA (sucesor inmediato) y
                # columna exactamente compatible, sin fallback de deriva.
                titulo_mayuscula = bool(resto) and bool(
                    re.match(r'^[A-ZÁÉÍÓÚÜÑ"“\'(«]', resto))
                if apartados_seccion and len(comp) == 1 and titulo_mayuscula and impreso is None \
                        and not motivo_2 and not en_lista and seccion.tipo == "seccion" and not seccion.sintetica \
                        and str(comp[0]) != seccion.numero and all(h.apartado for h in seccion.hijos) \
                        and comp[0] == len(seccion.hijos) + 1:
                    # regla de apartados de S0-4: «N. Título» en una sección sin puntos abre el punto <sección>.N
                    num_ap = f"{seccion.numero}.{comp[0]}"
                    seccion.col_hijos = seccion.col_hijos if seccion.col_hijos is not None else linea.x0
                    cerrar_hasta(seccion)
                    nodo = Nodo(tipo="punto", numero=num_ap, titulo=resto, pagina=linea.pagina, label_x0=linea.x0,
                                linea_label=linea, padre=seccion, numero_impreso=num, apartado=True)
                    seccion.hijos.append(nodo)
                    pila.append(nodo)
                    avisos.append({"tipo": "apartado_de_seccion_ap", "numero": num_ap, "impreso": num,
                                   "pagina": linea.pagina, "texto": linea.texto[:90]})
                    ultima_fue_label = True
                    continue
                motivo = None
                if comp[0] > MAX_RAIZ:
                    motivo = "raiz_mayor_a_max"
                elif not resto:
                    motivo = "resto_vacio_referencia_envuelta"
                elif str(comp[0]) != seccion.numero:
                    motivo = f"fuera_de_seccion_{seccion.numero}"
                elif len(comp) == 1:
                    motivo = "profundidad_1_es_seccion"
                else:
                    # padre abierto en la pila
                    padre_num = ".".join(str(c) for c in comp[:-1])
                    padre = None
                    for n in pila:
                        if n.tipo == "seccion" and len(comp) == 2:
                            padre = n
                            break
                        if n.tipo == "punto" and n.numero == padre_num:
                            padre = n
                            break
                    reapertura = None
                    if padre is None and reabrir_padre and titulo_mayuscula and len(comp) >= 3:
                        reapertura = camino_para_reabrir(padre_num)
                        if reapertura:
                            padre = reapertura[-1]
                    if padre is None:
                        motivo = f"padre_{padre_num}_no_abierto"
                    else:
                        hermanos = [h for h in padre.hijos if h.tipo == "punto"]
                        ultimo = _componentes(hermanos[-1].numero)[-1] if hermanos else 0
                        # contexto de lista: la línea previa abre o continúa una
                        # enumeración (':' de intro, ';' entre ítems). Los labels
                        # reales en minúscula viven en estas listas de condiciones
                        # (ext 10.11.x, 13.3.x, 13.4.x, 8.5.14.x — medidos).
                        contexto_lista = anterior is not None and bool(re.search(
                            r"[:;]\s*$|;\s*[yo]\s*$", anterior.texto.strip()))
                        if forma_h:
                            # H de S0-6a: el número pegado abre su punto si continúa la numeración (sin las
                            # validaciones de columna ni de minúscula)
                            if comp[-1] != ultimo + 1:
                                motivo = f"numero_pegado_no_sucede_al_hermano_{ultimo}_h"
                        elif comp[-1] <= ultimo:
                            motivo = f"no_sucede_al_hermano_{ultimo}"
                        elif not titulo_mayuscula and comp[-1] != ultimo + 1 \
                                and not contexto_lista and not fila_r9:
                            motivo = (f"resto_minuscula_y_salto_de_{ultimo}"
                                      f"_a_{comp[-1]}_sin_contexto_de_lista")
                        else:
                            # chequeo de columna, con fallback documentado: las
                            # columnas de label DERIVAN entre páginas (páginas
                            # provenientes de Comunicaciones con márgenes
                            # distintos), así que una columna incompatible solo
                            # rechaza si el resto de la línea NO parece título
                            # (los falsos headers RX-03 —referencias cruzadas a
                            # inicio de renglón— continúan una oración en
                            # minúscula: 'de las normas…', 'en el marco…').
                            columna_ok = True
                            detalle = ""
                            if hermanos:
                                if padre.col_hijos is not None \
                                        and abs(linea.x0 - padre.col_hijos) > TOL_X:
                                    columna_ok = False
                                    detalle = f"hermanos_en_{padre.col_hijos}"
                            elif padre.tipo == "punto":
                                if padre.text_col is not None:
                                    if abs(linea.x0 - padre.text_col) > TOL_X:
                                        columna_ok = False
                                        detalle = f"texto_del_padre_en_{padre.text_col}"
                                elif linea.x0 <= (padre.label_x0 or 0) + TOL_X:
                                    columna_ok = False
                                    detalle = f"label_del_padre_en_{padre.label_x0}"
                            # primer punto de una sección: sin restricción de
                            # columna (sección + secuencia bastan)
                            if not columna_ok:
                                if titulo_mayuscula:
                                    # deriva de columna tolerada solo con forma
                                    # de título; queda registrada como aviso
                                    avisos.append({
                                        "tipo": "aceptado_con_columna_derivada",
                                        "numero": num, "pagina": linea.pagina,
                                        "x0": linea.x0, "esperada": detalle,
                                        "texto": linea.texto[:90],
                                    })
                                elif contexto_lista:
                                    # label real en minúscula con columna derivada
                                    # dentro de una lista (caso medido: ext 13.3.1
                                    # 'el cliente accede…')
                                    avisos.append({
                                        "tipo": "aceptado_lista_minuscula",
                                        "numero": num, "pagina": linea.pagina,
                                        "x0": linea.x0, "esperada": detalle,
                                        "texto": linea.texto[:90],
                                    })
                                elif fila_r9:
                                    avisos.append({
                                        "tipo": "aceptado_fila_de_catalogo_r9",
                                        "numero": num, "pagina": linea.pagina,
                                        "x0": linea.x0, "esperada": detalle,
                                        "texto": linea.texto[:90],
                                    })
                                else:
                                    motivo = (f"resto_minuscula_y_columna_"
                                              f"{linea.x0}_incompatible_{detalle}")
                if motivo is None and motivo_2:
                    motivo = motivo_2   # veto de la regla 2 de S0
                if motivo is None and veto_5d:
                    motivo = "numero_en_referencia_r5d"     # veto de R5-d de S0-5a
                    avisos.append(veto_5d)
                if motivo is None and en_lista:
                    motivo = "indice_l" if en_indice_l else "lista_de_puntos_r8"   # veto de la regla 8 de S0 o de L
                if motivo is None and len(comp) > 1 and reapertura:
                    reabrir(reapertura, num, linea)
                if motivo is None:
                    if forma_h:
                        avisos.append({"tipo": "numero_pegado_h", "numero": num, "padre": padre.numero,
                                       "prefijo": subdoc_actual, "pagina": linea.pagina, "texto": linea.texto[:90]})
                    padre.col_hijos = padre.col_hijos if padre.col_hijos is not None else linea.x0
                    if comp[-1] != (ultimo + 1):
                        saltos.append({"tipo": "salto_hermano", "padre": padre.numero,
                                       "de": ultimo, "a": comp[-1], "pagina": linea.pagina})
                    cerrar_hasta(padre)
                    titulo = texto_l[len(tokens[0]):].strip()
                    nodo = Nodo(tipo="punto", numero=num, titulo=titulo,
                                pagina=linea.pagina, label_x0=linea.x0,
                                linea_label=linea, padre=padre, numero_impreso=impreso)
                    padre.hijos.append(nodo)
                    pila.append(nodo)
                    ultima_fue_label = True
                    continue
                else:
                    rechazos.append({"pagina": linea.pagina, "x0": linea.x0,
                                     "texto": linea.texto[:120], "motivo": motivo})
                    # sigue como prosa

            # prosa: anclar por columna
            profundo = pila[-1]
            # Primera continuación de un punto recién abierto: solo si corre
            # ESTRICTAMENTE más adentro que su label. Una línea a la altura del
            # label no es continuación del punto: es prosa del contenedor (la
            # columna de label de profundidad d es la columna de texto de d-1;
            # caso cierres del 2.7 de ext tras el 2.7.4 sin continuación).
            if ultima_fue_label and profundo.tipo == "punto" \
                    and profundo.text_col is None \
                    and linea.x0 > (profundo.label_x0 or 0) + TOL_X:
                profundo.text_col = linea.x0
                anexar(profundo, linea, nuevo_segmento=not profundo.segmentos)
                ultima_fue_label = False
                continue
            ultima_fue_label = False

            # re-anclaje a un ancestro: solo para líneas con forma de PROSA
            # (largo pleno y sin fronteras de columna). Las filas de tabla son
            # cortas o multi-columna y pueden caer por azar en la columna de un
            # ancestro (caso medido: tabla de aforos de cap p.108 en x0=103.3);
            # si re-anclaran, cerrarían puntos abiertos a mitad de tabla.
            es_prosa = linea.ngaps == 0 and len(linea.texto) >= 55
            ancla = None
            if es_prosa:
                for n in pila[:-1]:      # ancestros estrictos, del más superficial al más profundo
                    col = n.text_col
                    if col is not None and abs(linea.x0 - col) <= TOL_X:
                        ancla = n
                        break
            if ancla is not None and "a" in formas_m1 and profundo.tipo == "punto" \
                    and profundo.text_col is None and not profundo.segmentos and not profundo.hijos \
                    and profundo.label_x0 is not None and abs(linea.x0 - profundo.label_x0) <= TOL_X \
                    and not _sangria_colgante_m1(profundo):
                # mecanismo 1 de S0-3, forma a: el punto es solo su rótulo y la prosa sigue en su columna
                profundo.text_col = linea.x0
                anexar(profundo, linea, nuevo_segmento=True)
                avisos.append({"tipo": "cuerpo_al_rotulo_m1", "forma": "a", "numero": profundo.numero,
                               "pagina": linea.pagina, "texto": linea.texto[:90]})
                continue
            if ancla is not None and "b" in formas_m1 and profundo.tipo == "punto" \
                    and profundo.text_col is not None and profundo.label_x0 is not None \
                    and profundo.text_col < profundo.label_x0 - TOL_X \
                    and abs(linea.x0 - profundo.text_col) > TOL_X:
                # mecanismo 1 de S0-3, forma b: el cuerpo del punto corre a la izquierda de su rótulo
                avisos.append({"tipo": "cuerpo_al_rotulo_m1", "forma": "b", "numero": profundo.numero,
                               "pagina": linea.pagina, "texto": linea.texto[:90]})
                ancla = None
            if ancla is not None and (profundo.text_col is None
                                      or abs(linea.x0 - profundo.text_col) > TOL_X):
                cerrar_hasta(ancla)
                anexar(ancla, linea, nuevo_segmento=True)
                continue

            # sección sin text_col aún (chapeau): la primera prosa la fija
            if profundo.tipo == "seccion" and profundo.text_col is None:
                profundo.text_col = linea.x0
            if profundo.tipo == "punto" and profundo.text_col is None:
                profundo.text_col = linea.x0
            nuevo = bool(profundo.segmentos) and profundo.segmentos[-1] \
                and abs(linea.x0 - profundo.segmentos[-1][-1].x0) > TOL_X
            anexar(profundo, linea, nuevo_segmento=nuevo)

    if modo_sin_raiz and nodo_preambulo is not None \
            and not nodo_preambulo.segmentos and not nodo_preambulo.hijos:
        # el preámbulo se creó pero la primera línea abrió raíz: no materializa
        secciones.remove(nodo_preambulo)
    for r in [x for x in secciones if x.prefijo is not None and x.numero == "0" and x.sintetica
              and x.linea_label is None and not x.segmentos and not x.hijos]:
        # regla de sub-documento de S0-4: raíz «0» sin texto (el rótulo estaba en la zona de encabezado y la página
        # empieza con una raíz o una sección); el sub-documento sigue en el registro
        secciones.remove(r)

    accounting = {
        "lineas_descartadas_encabezado_pie": len(acc_descartes),
        "detalle_descartes": acc_descartes,
    }
    return ResultadoParseo(
        to=to, archivo=archivo, secciones=secciones, rechazos_header=rechazos,
        saltos_numeracion=saltos, avisos=avisos, accounting=accounting,
        lineas_contenido=n_contenido, paginas_cuerpo=n_paginas_cuerpo,
        lineas_huerfanas=n_huerfanas,
        modo_lectura=("sin_raiz" if modo_sin_raiz
                      else "marcadores" if marcadores_b582 else "vigente"),
        subdocumentos=registro_sd,
        rotulos_letra=(rotulos_letra if letra_herencia and not letra_corte else []),
        bandas_a=bandas, recuadro_i=recuadro_ids, paginas_caratula_a=paginas_caratula_a,
    )


def _sangria_colgante_m1(nodo: Nodo) -> bool:
    """Mecanismo 1 de S0-3, forma a, guarda: algún hermano anterior del punto tiene su cuerpo más adentro que su
    rótulo (sangría colgante: la prosa a la altura del rótulo es del padre, el cierre del 2.7 de ext), o es un
    renglón suelto, sin cuerpo ni hijos (una lista de ítems de un renglón: la prosa que sigue al último es el cierre
    del padre, cap 8.6, ctacte 5.1.1 y ext 11.1.3 en la tanda 0)."""
    hermanos = nodo.padre.hijos if nodo.padre is not None else []
    return any(h is not nodo and h.tipo == "punto"
               and ((h.text_col is not None and h.label_x0 is not None and h.text_col > h.label_x0 + TOL_X)
                    or (h.text_col is None and not h.segmentos and not h.hijos))
               for h in hermanos)


# ------------------------------------- Regla 1: continuidad de enumeración

# marcador de enumeración a inicio de línea: 'vii)', 'h)', '3)', '(ii)'.
# Solo minúsculas y solo con paréntesis de cierre: es la única forma de
# acápite usada en los 5 TOs (los estilos 'a.', 'I)', '1.-' no aparecen como
# ítems de enumeración y quedan fuera del detector — límite documentado).
RE_MARCADOR_ENUM = re.compile(r"^\(?([a-z]{1,5}|\d{1,2})\)\s+\S")


def _romano(n: int) -> str:
    out = ""
    for v, s in ((10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out, n = out + s, n - v
    return out


_ROMANOS = {_romano(n): n for n in range(1, 40)}


def _interpretaciones(token: str) -> set[tuple[str, int]]:
    """Familias de secuencia en las que el token es un valor: romano canónico
    minúscula (1–39), letra simple a–z (1–26), número (1–99). Un token puede
    vivir en varias ('i' es romano 1 y letra 9; 'x' romano 10 y letra 24): la
    ambigüedad se resuelve en `_es_sucesor`, que exige UNA familia común donde
    el candidato sea el sucesor inmediato."""
    out: set[tuple[str, int]] = set()
    if token in _ROMANOS:
        out.add(("romano", _ROMANOS[token]))
    if len(token) == 1 and "a" <= token <= "z":
        out.add(("letra", ord(token) - ord("a") + 1))
    if token.isdigit():
        out.add(("numero", int(token)))
    return out


def _es_sucesor(previo: str, candidato: str) -> bool:
    inter_c = _interpretaciones(candidato)
    return any((f, v + 1) in inter_c for f, v in _interpretaciones(previo))


# ----- numeración de sección no numérica (B5.8.2: letras y romanos) -----

_ROMANOS_MAY = {_romano(n).upper(): n for n in range(1, 40)}
_ROMANOS_MAY_SD = _ROMANOS_MAY      # U-SEG-OFICIAL, S0-4: romanos de anexos y partes (I a XXXIX)


def _interpretaciones_seccion(num: str) -> set[tuple[str, int]]:
    """Familias en las que un número de sección B5.8.2 es un valor: número
    arábigo, romano canónico en mayúsculas (1–39) o letra sola A–Z. Un token
    puede vivir en varias ('C' es letra 3; 'I' es romano 1 y letra 9): la
    sucesión se resuelve en `_es_sucesor_seccion` exigiendo UNA familia común
    (reqcac A→B→C avanza por letras; ri_psp IV→VI no tiene sucesor y el
    salto se reporta). Mismo patrón que `_interpretaciones` (regla 1)."""
    out: set[tuple[str, int]] = set()
    if num.isdigit():
        out.add(("numero", int(num)))
    if num in _ROMANOS_MAY:
        out.add(("romano", _ROMANOS_MAY[num]))
    if len(num) == 1 and "A" <= num <= "Z":
        out.add(("letra", ord(num) - ord("A") + 1))
    return out


def _es_sucesor_seccion(previo: str, candidato: str) -> bool:
    inter_c = _interpretaciones_seccion(candidato)
    return any((f, v + 1) in inter_c for f, v in _interpretaciones_seccion(previo))


def _orden_componente_seccion(x: str) -> int:
    """Clave de orden de un componente de numeración para reportes (B5.8.2:
    admite letras y romanos; para dígitos es int(x), idéntico al orden
    histórico). Ante ambigüedad usa la interpretación de menor valor ('C' →
    3, 'I' → 1); un token fuera de toda familia ordena al final por su primer
    carácter (determinístico)."""
    if x.isdigit():
        return int(x)
    interps = _interpretaciones_seccion(x)
    if interps:
        return min(v for _, v in interps)
    return 10000 + (ord(x[0]) if x else 0)


def _ultimo_marcador_propio(nodo: Nodo) -> str | None:
    """Último marcador de enumeración a inicio de línea en el texto propio
    (label + segmentos) de un nodo. Límite: si el propio termina con una
    enumeración ANIDADA (ítems 'a)' dentro del acápite 'vi)'), el último
    marcador es el interno y una continuación del nivel externo no se
    detecta — falla hacia no reasignar, nunca hacia reasignar de más."""
    ultimo: str | None = None
    lineas: list[Linea] = [nodo.linea_label] if nodo.linea_label else []
    for s in nodo.segmentos:
        lineas.extend(s)
    for l in lineas:
        m = RE_MARCADOR_ENUM.match(l.texto.strip())
        if m:
            ultimo = m.group(1)
    return ultimo


def aplicar_continuidad_enumeracion(res: ResultadoParseo) -> list[dict]:
    """REGLA 1. Para cada hueco entre hijos consecutivos de un nodo: si los
    segmentos intersticiales que caen en ese hueco arrancan con un marcador
    que SUCEDE al último marcador del texto propio del hermano terminal
    inmediatamente anterior, se reasignan (segmento a segmento, en orden
    documental) como continuación del propio de ese hermano:

      * segmento cuyo primer renglón porta el marcador sucesor → se reasigna
        y el estado avanza con cada marcador line-initial del segmento que
        siga sucediendo;
      * segmento sin marcador cuyo primer renglón corre MÁS PROFUNDO que la
        columna del marcador (> TOL_X) → continuación envuelta del ítem, se
        reasigna con el estado sin avanzar;
      * cualquier otro segmento corta la cadena: nada posterior del hueco se
        reasigna (un marcador que reinicia en 'i)' es una enumeración nueva
        del padre, no una continuación).

    Alcance y límites (documentados): solo segmentos intersticiales (los
    'cierre' — tras el último hijo — son el mecanismo chapeau-perdido de U6 y
    quedan fuera); solo hermano anterior TERMINAL (si tiene hijos, su propio
    no es el texto que termina en la costura); familias romanos/letras/números
    con las formas de `RE_MARCADOR_ENUM`; enumeraciones anidadas: ver
    `_ultimo_marcador_propio`. Toda reasignación queda registrada con su
    evidencia."""
    reasignaciones: list[dict] = []

    def visitar(nodo: Nodo) -> None:
        for h in nodo.hijos:
            visitar(h)
        if not nodo.hijos:
            return
        marcas = [(h.pagina, h.linea_label.top if h.linea_label else 0.0)
                  for h in nodo.hijos]
        por_hueco: dict[int, list[list[Linea]]] = {}
        for s in nodo.segmentos:
            pos = (s[0].pagina, s[0].top)
            if pos <= marcas[0] or pos > marcas[-1]:
                continue  # intro / cierre: fuera del alcance de la regla
            k = max(i for i, mp in enumerate(marcas) if mp < pos)
            por_hueco.setdefault(k, []).append(s)
        for k in sorted(por_hueco):
            hermano = nodo.hijos[k]
            if hermano.hijos:
                continue
            estado = _ultimo_marcador_propio(hermano)
            if estado is None:
                continue
            marc_x0: float | None = None
            for s in por_hueco[k]:
                primera = s[0]
                m = RE_MARCADOR_ENUM.match(primera.texto.strip())
                if m and _es_sucesor(estado, m.group(1)):
                    motivo = f"marcador '{m.group(1)}' sucede a '{estado}'"
                    for l in s:
                        mm = RE_MARCADOR_ENUM.match(l.texto.strip())
                        if mm and _es_sucesor(estado, mm.group(1)):
                            estado = mm.group(1)
                    marc_x0 = primera.x0
                elif m is None and marc_x0 is not None \
                        and primera.x0 > marc_x0 + TOL_X:
                    motivo = (f"continuación envuelta del ítem '{estado}' "
                              f"(x0 {primera.x0} > columna del marcador {marc_x0})")
                else:
                    break
                nodo.segmentos.remove(s)
                hermano.segmentos.append(s)
                reasignaciones.append({
                    "padre": nodo.numero if nodo.tipo == "punto" else f"S{nodo.numero}",
                    "destino": hermano.numero,
                    "pagina": primera.pagina, "x0": primera.x0,
                    "n_lineas": len(s), "motivo": motivo,
                    "primera_linea": primera.texto[:100],
                })

    for s in res.secciones:
        visitar(s)
    return reasignaciones


# --------------------------------- U-SEG-OFICIAL, S0-5a: R5-a y R5-a′ (sobre el árbol, después de las reglas 1 y 2)

def _mediana(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _lineas_item_116(n: Nodo) -> list[Linea]:
    """Los renglones del texto propio de un ítem, en el orden en que los escribe `construir_chunks`."""
    return list(n.lineas_previas) + ([n.linea_label] if n.linea_label is not None else []) + \
        [l for s in n.segmentos for l in s]


def _cortes_116(lineas: list[Linea]) -> list[int]:
    """Cortes de párrafo del detector de S1-bis: renglón con mayúscula inicial después de uno terminado en «.» o «:»."""
    return [i for i in range(1, len(lineas)) if RE_MAYUSCULA_R5A.match(lineas[i].texto.strip())
            and lineas[i - 1].texto.rstrip().endswith((".", ":"))]


def _inicios_parrafo_116(lineas: list[Linea], con_rotulo: bool) -> list[int]:
    """Índices de los renglones que abren párrafo, con el renglón del rótulo como párrafo propio (corrección del
    detector): el segundo renglón abre párrafo si empieza con mayúscula, aunque el título no termine en punto."""
    return [0] + [i for i in range(1, len(lineas)) if RE_MAYUSCULA_R5A.match(lineas[i].texto.strip())
                  and (lineas[i - 1].texto.rstrip().endswith((".", ":")) or (i == 1 and con_rotulo))]


def _con_rotulo_116(n: Nodo, lineas: list[Linea]) -> bool:
    return bool(lineas) and n.linea_label is not None and lineas[0] is n.linea_label


def listas_116(res: ResultadoParseo) -> list[tuple[Nodo, list[Nodo], str]]:
    """Detector del hallazgo 1.16 (ver el comentario de TOL_COL_R5A): (padre, ítems, criterio) de cada lista candidata,
    en orden documental; criterio «original», «corregido» o «ambos»."""
    out: list[tuple[Nodo, list[Nodo], str]] = []

    def visitar(n: Nodo) -> None:
        hijos = [h for h in n.hijos if h.tipo == "punto"]
        if len(hijos) >= 2 and all(not h.hijos for h in hijos):
            ls = [_lineas_item_116(h) for h in hijos]
            orig = bool(_cortes_116(ls[-1])) and not any(_cortes_116(x) for x in ls[:-1])
            np_ = [len(_inicios_parrafo_116(x, _con_rotulo_116(h, x))) for x, h in zip(ls, hijos)]
            corr = np_[-1] > max(np_[:-1])
            if orig or corr:
                out.append((n, hijos, "ambos" if orig and corr else "original" if orig else "corregido"))
        for h in n.hijos:
            visitar(h)

    for s in res.secciones:
        visitar(s)
    return out


def _es_titulo_bloque(linea: Linea) -> bool:
    t = linea.texto.strip()
    tok = t.split()[0] if t.split() else ""
    return (0 < len(t) <= MAX_CHARS_TITULO_BLOQUE and bool(RE_MAYUSCULA_R5A.match(t))
            and not t.endswith((".", ",", ";", ":")) and linea.ngaps == 0
            and not (RE_NUM_TOKEN.match(tok) or RE_NUM_TOKEN_SIN_PUNTO.match(tok)))


def _sacar_lineas(n: Nodo, quitar: set[int]) -> None:
    """Saca de los segmentos de `n` las líneas de `quitar` (ids de objeto), sin cambiar el corte de los que quedan."""
    nuevos: list[list[Linea]] = []
    for s in n.segmentos:
        actual: list[Linea] = []
        for l in s:
            if id(l) in quitar:
                if actual:
                    nuevos.append(actual)
                    actual = []
            else:
                actual.append(l)
        if actual:
            nuevos.append(actual)
    n.segmentos = nuevos


def _corridas(lineas: list[Linea], ids: set[int]) -> list[list[Linea]]:
    """Las corridas consecutivas de `lineas` cuyos ids están en `ids`, en orden."""
    out: list[list[Linea]] = []
    actual: list[Linea] = []
    for l in lineas:
        if id(l) in ids:
            actual.append(l)
        elif actual:
            out.append(actual)
            actual = []
    if actual:
        out.append(actual)
    return out


def _clave_r5a(n: Nodo) -> str:
    """S0-5a-bis: la clave de una lista para R5-a por lista, la de su último ítem (ver TOL_TOP_POR_LISTA)."""
    r = n
    while r.padre is not None:
        r = r.padre
    return f"{r.prefijo}::{n.numero}" if r.prefijo else n.numero


def _indice_renglon_r5a(lineas: list[Linea], ref: tuple) -> int | None:
    """S0-5a-bis: el índice del renglón (página, top, comienzo del texto) en `lineas`, o None."""
    for i, l in enumerate(lineas):
        if l.pagina == ref[0] and abs(l.top - ref[1]) <= TOL_TOP_POR_LISTA and l.texto.strip().startswith(ref[2]):
            return i
    return None


def aplicar_cierre_al_margen(res: ResultadoParseo, cierre: bool = False, titulo_bloque: bool = False,
                             listas: dict | None = None, excluir=None) -> list[dict]:
    """U-SEG-OFICIAL, S0-5a: R5-a (`cierre`) y R5-a′ (`titulo_bloque`) sobre las listas de `listas_116` (ver el
    comentario de TOL_COL_R5A y MAX_CHARS_TITULO_BLOQUE). R5-a′ se evalúa primero: lo que abre la sección nueva ya no
    pasa por R5-a. Devuelve un evento por cada párrafo movido y por cada bloque abierto.

    S0-5a-bis: con `listas` (ver TOL_TOP_POR_LISTA), R5-a actúa solo sobre las listas dadas, encontradas en el árbol
    por la clave de su último ítem y no por el detector; con None, sobre las de `listas_116`, como en S0-5a. Con
    `excluir` (un predicado de renglón: los de las tablas que se serializan), R5-a no mueve un párrafo ni un rango que
    tenga algún renglón que lo cumpla, y lo registra."""
    eventos: list[dict] = []
    if not (cierre or titulo_bloque):
        return eventos
    nbloque = 0

    def _pos(l: Linea) -> tuple:
        return (l.pagina, l.top)

    def _raiz(n: Nodo) -> Nodo:
        while n.padre is not None:
            n = n.padre
        return n

    pares = listas_116(res)
    if listas is not None:
        # S0-5a-bis: las listas dadas que el detector no marca también entran a R5-a
        vistos = {id(pa) for pa, _, _ in pares}
        extra: list[tuple[Nodo, list[Nodo], str]] = []

        def visitar(n: Nodo) -> None:
            hijos = [h for h in n.hijos if h.tipo == "punto"]
            if hijos and id(n) not in vistos and _clave_r5a(hijos[-1]) in listas:
                extra.append((n, hijos, "por_lista"))
            for h in n.hijos:
                visitar(h)
        for s0 in res.secciones:
            visitar(s0)
        pares = pares + extra
    for padre, items, criterio in pares:
        ult = items[-1]
        lineas = _lineas_item_116(ult)
        ini = _inicios_parrafo_116(lineas, _con_rotulo_116(ult, lineas))
        propias = {id(l) for s in ult.segmentos for l in s}     # solo se mueven líneas de los segmentos del ítem
        parrafos = [(a, b) for a, b in zip(ini, ini[1:] + [len(lineas)])][1:]
        parrafos = [(a, b) for a, b in parrafos if all(id(l) in propias for l in lineas[a:b])]
        clave = _clave_r5a(ult)
        con_r5a = cierre and (listas is None or clave in listas)
        spec = listas.get(clave) if listas is not None else None
        if spec is not None:
            # S0-5a-bis: un rango explícito de renglones reemplaza a los párrafos
            i_a, i_b = _indice_renglon_r5a(lineas, spec[1]), _indice_renglon_r5a(lineas, spec[2])
            if i_a is None or i_b is None or i_b < i_a or not all(id(l) in propias for l in lineas[i_a:i_b + 1]):
                eventos.append({"tipo": "r5a_por_lista_sin_rango", "item": ult.numero, "prefijo": _raiz(ult).prefijo,
                                "desde": list(spec[1]), "hasta": list(spec[2])})
                con_r5a = False
                parrafos = []
            else:
                parrafos = [(i_a, i_b + 1)]
        if not parrafos:
            continue
        unidad_padre = padre.numero if padre.tipo == "punto" else f"S{padre.numero}"
        corte_bloque = None
        if titulo_bloque and padre.tipo == "seccion" and padre.padre is None and criterio != "por_lista":
            for a, b in parrafos:
                if _es_titulo_bloque(lineas[a]):
                    resto = lineas[a + 1:] + [l for it in _rol_segmentos(padre) if it["rol"] == "cierre"
                                              for l in it["seg"]]
                    if resto:
                        corte_bloque = a
                    break
        mover: set[int] = set()
        if con_r5a:
            col_rot = _mediana([h.label_x0 for h in items if h.label_x0 is not None]) \
                if any(h.label_x0 is not None for h in items) else None
            prev_tc = [h.text_col for h in items[:-1] if h.text_col is not None]
            col_txt = _mediana(prev_tc) if prev_tc else None
            for a, b in parrafos:
                if corte_bloque is not None and a >= corte_bloque:
                    break
                x = lineas[a].x0
                if spec is not None:
                    al_margen = True
                elif col_rot is None:
                    continue
                elif col_txt is not None:
                    al_margen = abs(x - col_txt) > TOL_COL_R5A and abs(x - col_rot) < abs(x - col_txt)
                else:
                    al_margen = x <= col_rot + TOL_COL_R5A
                if al_margen and excluir is not None and any(excluir(l) for l in lineas[a:b]):
                    eventos.append({"tipo": "r5a_no_mueve_tabla", "lista": unidad_padre, "item": ult.numero,
                                    "prefijo": _raiz(ult).prefijo, "pagina": lineas[a].pagina,
                                    "renglones": b - a, "texto": lineas[a].texto[:90]})
                    continue
                if al_margen:
                    mover.update(id(l) for l in lineas[a:b])
                    eventos.append({"tipo": "cierre_al_margen_r5a", "lista": unidad_padre, "item": ult.numero,
                                    "prefijo": _raiz(ult).prefijo, "criterio_116": criterio,
                                    "modo": "rango" if spec is not None else "parrafo",
                                    "pagina": lineas[a].pagina, "renglones": b - a, "x0": round(x, 1),
                                    "columna_rotulos": round(col_rot, 1) if col_rot is not None else None,
                                    "columna_texto": round(col_txt, 1) if col_txt is not None else None,
                                    "texto": lineas[a].texto[:90]})
        bloque: list[Linea] = []
        if corte_bloque is not None:
            bloque = lineas[corte_bloque:]
            mover_bloque = {id(l) for l in bloque}
            cierres = [it["seg"] for it in _rol_segmentos(padre) if it["rol"] == "cierre"]
            _sacar_lineas(ult, mover_bloque)
            padre.segmentos = [s for s in padre.segmentos if not any(s is c for c in cierres)]
            nbloque += 1
            rotulo = bloque[0]
            nueva = Nodo(tipo="seccion", numero=f"bloque{nbloque}", titulo=rotulo.texto.strip(), pagina=rotulo.pagina,
                         label_x0=rotulo.x0, linea_label=rotulo, sintetica=True, prefijo=padre.prefijo)
            cuerpo = bloque[1:] + [l for c in cierres for l in c]
            if cuerpo:
                nueva.segmentos = [cuerpo]
            res.secciones.insert(res.secciones.index(padre) + 1, nueva)
            eventos.append({"tipo": "titulo_de_bloque_r5a2", "lista": unidad_padre, "item": ult.numero,
                            "prefijo": padre.prefijo, "seccion_nueva": f"Sbloque{nbloque}",
                            "pagina": rotulo.pagina, "rotulo": rotulo.texto[:90],
                            "renglones_del_item": len(bloque), "renglones_del_cierre": sum(len(c) for c in cierres)})
        if mover:
            corr = _corridas(lineas, mover)
            _sacar_lineas(ult, mover)
            padre.segmentos = sorted(padre.segmentos + corr, key=lambda s: _pos(s[0]))
    return eventos


def _pos_c(n: Nodo) -> tuple:
    """Posición del comienzo de un nodo: su rótulo o, sin rótulo, su primer renglón."""
    if n.linea_label is not None:
        return (n.linea_label.pagina, n.linea_label.top)
    ps = [(s[0].pagina, s[0].top) for s in n.segmentos if s] + [_pos_c(h) for h in n.hijos]
    return min(ps) if ps else (n.pagina, 0.0)


def _distancia_c(n: Nodo, x: float, pagina: int | None = None) -> float | None:
    """C de S0-6a: la distancia de `x` a la columna más cercana del nivel `n` (None si no tiene columnas). Las columnas de un
    nivel son la de su texto, la de los rótulos de sus hijos y, en la página `pagina`, la de los rótulos de sus hijos que
    están en esa página (un TO compila páginas de versiones con márgenes distintos)."""
    cols = [c for c in (n.text_col, n.col_hijos) if c is not None]
    if pagina is not None:
        cols += [h.label_x0 for h in n.hijos if h.linea_label is not None and h.label_x0 is not None
                 and h.linea_label.pagina == pagina]
    return min(abs(x - c) for c in cols) if cols else None


def _col_propia_c(t: Nodo) -> float | None:
    """C de S0-6a: la columna del texto propio de una unidad sin hijos (la de su nivel), sin que la fije el párrafo que se
    evalúa (la `text_col` de E0 la fija el primer renglón después del rótulo, que puede ser ese mismo párrafo o una
    fórmula centrada). (1) Si el primer párrafo (el del rótulo, que siempre es suyo) tiene renglones de continuación, el
    x0 menor de esos renglones. (2) Si es un solo renglón, la columna no se puede medir sin ambigüedad, y vale la menor
    de las medidas que hay (la menor: ante la duda, el párrafo no sale, porque la columna no discrimina): la `text_col`
    de E0 si el renglón del rótulo es un título (no termina en «.», «:» ni «;»: su texto sigue abajo, aunque corra en la
    columna del rótulo; S0-6a-bis); el x0 menor de los renglones de prosa, fuera del rótulo, de los otros puntos sin hijos
    de la misma madre (la columna del texto de los ítems de la lista); el comienzo de la primera palabra después del
    rótulo. Sin medidas, la `text_col` de E0."""
    lineas = _lineas_item_116(t)
    if not lineas:
        return t.text_col
    con = _con_rotulo_116(t, lineas)
    ini = _inicios_parrafo_116(lineas, con)
    cont = lineas[1:ini[1] if len(ini) > 1 else len(lineas)]
    if cont:
        return min(l.x0 for l in cont)
    medidas = []
    if con and t.text_col is not None and not lineas[0].texto.rstrip().endswith((".", ":", ";")):
        medidas.append(t.text_col)
    if t.padre is not None:
        for h in t.padre.hijos:
            if h is t or h.hijos or h.tipo != "punto":
                continue
            lh = _lineas_item_116(h)
            medidas += [l.x0 for l in (lh[1:] if _con_rotulo_116(h, lh) else lh) if l.ngaps == 0]
    pal = lineas[0].palabras
    if con and len(pal) >= 2 and pal[0][2].rstrip(".)") == t.numero:
        medidas.append(pal[1][0])
    return min(medidas) if medidas else t.text_col


def _comparte_columna_c(ps: list[Linea]) -> bool:
    """C de S0-6a-bis (D21, regla 3): los renglones de un párrafo comparten columna si todos, salvo el primero (sangría de
    primera línea o rótulo colgante), están a TOL_COL_C o menos del x0 del segundo. Un párrafo de un renglón la comparte."""
    return len(ps) < 3 or all(abs(l.x0 - ps[1].x0) <= TOL_COL_C for l in ps[2:])


def _col_parrafo_c(ps: list[Linea]) -> float:
    """C de S0-6a-bis: la columna de un párrafo, la que comparten sus renglones (el x0 del segundo), o la de su único
    renglón; no la de su renglón más a la izquierda."""
    return ps[1].x0 if len(ps) > 1 else ps[0].x0


def _parrafos_c(lineas: list[Linea]) -> list[list[Linea]]:
    """Los párrafos de un segmento (sin renglón de rótulo), con el criterio de C."""
    ini = _inicios_parrafo_116(lineas, False)
    return [lineas[a:b] for a, b in zip(ini, ini[1:] + [len(lineas)])]


def _elegir_c(niveles: list[Nodo], x: float, col_propia: float | None, pagina: int | None = None) -> int | None:
    """C de S0-6a: el índice del nivel de la columna más cercana a `x` (empate dentro de TOL_COL_C: el más interno, el de
    índice mayor), o None si no discrimina (en el empate está la columna del texto propio, o ningún nivel tiene
    columna)."""
    ds = [(i, _distancia_c(n, x, pagina)) for i, n in enumerate(niveles)]
    ds = [(i, d) for i, d in ds if d is not None]
    dp = abs(x - col_propia) if col_propia is not None else None
    if not ds:
        return None
    mejor = min([d for _, d in ds] + ([dp] if dp is not None else []))
    if dp is not None and dp <= mejor + TOL_COL_C:
        return None
    return max(i for i, d in ds if d <= mejor + TOL_COL_C)


def _nombre_c(n: Nodo) -> str:
    base = n.numero if n.tipo == "punto" else f"S{n.numero}"
    p = _raiz_nodo(n).prefijo
    return f"{p}::{base}" if p else base


def asignar_por_columna_c(res: ResultadoParseo, excluir=None, listas_fijas: frozenset = frozenset()) -> list[dict]:
    """C de S0-6a (ver TOL_COL_C). Devuelve un evento por párrafo o segmento movido. S0-6a-bis: un párrafo se mide por la
    columna que comparten sus renglones (`_col_parrafo_c`); no se mueve un párrafo cuyos renglones no comparten columna
    (`_comparte_columna_c`), ni el grupo que arrastra; y no se tocan las listas de `listas_fijas` (claves de su último
    ítem, las de R5-a por lista que quedan: ni la madre ni sus ítems)."""
    eventos: list[dict] = []

    def fija(n: Nodo) -> bool:
        items = [h for h in n.hijos if h.tipo == "punto"]
        return bool(items) and _clave_r5a(items[-1]) in listas_fijas

    def _pos(l: Linea) -> tuple:
        return (l.pagina, l.top)

    def tabla(lineas: list[Linea]) -> bool:
        return excluir is not None and any(excluir(l) for l in lineas)

    def poner(n: Nodo, lineas: list[Linea]) -> None:
        n.segmentos = sorted(n.segmentos + [lineas], key=lambda s: _pos(s[0]))

    def terminal(t: Nodo, ancestros: list[Nodo]) -> None:
        lineas = _lineas_item_116(t)
        ini = _inicios_parrafo_116(lineas, _con_rotulo_116(t, lineas))
        propias = {id(l) for s in t.segmentos for l in s}
        parrafos = [(a, b) for a, b in zip(ini, ini[1:] + [len(lineas)])][1:]
        destino = None
        col = _col_propia_c(t)
        mover: dict[int, list[list[Linea]]] = {}
        grupo: list[list[Linea]] = []
        ev: list[dict] = []
        con_tabla = False
        for a, b in parrafos:
            ps = lineas[a:b]
            if not all(id(l) in propias for l in ps) or tabla(ps):
                if destino is None:
                    continue
                con_tabla = all(id(l) in propias for l in ps) and tabla(ps)
                break
            x = _col_parrafo_c(ps)
            if destino is None:
                if col is not None and x >= col - TOL_COL_C:
                    continue     # en la columna de su texto o más adentro: es suyo
                i = _elegir_c(ancestros, x, col, ps[0].pagina)
                if i is None:
                    continue
                destino = i
            else:
                i = _elegir_c(ancestros[:destino + 1], x, None, ps[0].pagina)
                if i is not None and i < destino:
                    destino = i
            mover.setdefault(destino, []).append(ps)
            grupo.append(ps)
            ev.append({"tipo": "parrafo_por_columna_c", "de": _nombre_c(t), "a": _nombre_c(ancestros[destino]),
                       "pagina": ps[0].pagina, "renglones": len(ps), "x0": round(x, 1), "texto": ps[0].texto[:90]})
        if grupo and (con_tabla or not all(_comparte_columna_c(ps) for ps in grupo)):
            # (con_tabla: la tabla que sigue en el texto de la hoja es parte del bloque, y sus filas no comparten columna)
            # S0-6a-bis: un párrafo del grupo no comparte columna (D21, regla 3: decide el contenido): no sale ninguno
            eventos.append({"tipo": "grupo_sin_columna_comun_c", "de": _nombre_c(t), "pagina": grupo[0][0].pagina,
                            "parrafos": len(grupo), "renglones": sum(len(ps) for ps in grupo)})
            return
        eventos.extend(ev)
        if mover:
            quitar = {id(l) for grupos in mover.values() for ps in grupos for l in ps}
            _sacar_lineas(t, quitar)
            for i, grupos in mover.items():
                for c in _corridas(lineas, {id(l) for ps in grupos for l in ps}):
                    poner(ancestros[i], c)

    def visitar(n: Nodo, ancestros: list[Nodo]) -> None:
        for h in list(n.hijos):
            if h.hijos:
                visitar(h, ancestros + [n])
            elif not (h.tipo == "punto" and fija(n)):
                terminal(h, ancestros + [n])

    for s0 in res.secciones:
        if s0.hijos:
            visitar(s0, [])

    def segmentos(n: Nodo, ancestros: list[Nodo]) -> None:
        for h in list(n.hijos):
            segmentos(h, ancestros + [n])
        if not n.hijos or fija(n):
            return
        primero = _pos_c(n.hijos[0])
        for s in [s for s in n.segmentos if s and _pos(s[0]) > primero]:
            if tabla(s):
                continue
            pars = _parrafos_c(s)
            if not all(_comparte_columna_c(ps) for ps in pars):
                continue     # S0-6a-bis: un párrafo del segmento no comparte columna: decide el contenido
            x = _col_parrafo_c(pars[0])
            abiertos, m = ancestros + [n], n
            while m.hijos:
                prev = [h for h in m.hijos if _pos_c(h) < _pos(s[0])]
                if not prev or not prev[-1].hijos:
                    break     # un segmento no vuelve al texto de una hoja: solo pasa a un nivel con hijos
                m = prev[-1]
                abiertos.append(m)
            i = _elegir_c(abiertos, x, None, s[0].pagina)
            if i is None or abiertos[i] is n:
                continue
            dest = abiertos[i]
            n.segmentos = [z for z in n.segmentos if z is not s]
            poner(dest, s)
            eventos.append({"tipo": "segmento_por_columna_c", "de": _nombre_c(n), "a": _nombre_c(dest),
                            "pagina": s[0].pagina, "renglones": len(s), "x0": round(x, 1), "texto": s[0].texto[:90]})

    for s0 in res.secciones:
        segmentos(s0, [])
    return eventos


def _texto_banda_a(renglones: list[str]) -> list[str]:
    """A de S0-6a: los renglones de la banda sin «B.C.R.A.» (la línea que E0 leyó como sección no se registra)."""
    out = []
    for t in renglones:
        t = re.sub(r"\bB\.C\.R\.A\.", "", t).strip()
        if t:
            out.append(" ".join(t.split()))
    return out


def _rango_a(n: Nodo) -> int | None:
    """Rango de división de un nodo de primer nivel (ver RANGO_TITULO_A), o None si no es una división."""
    if not n.sintetica:
        return None
    if n.numero == "0" and n.prefijo is not None and n.titulo not in ("Preámbulo", ""):
        return RANGO_SUBDOC_A
    if n.rango_a is not None:
        return n.rango_a
    if n.linea_label is not None and RE_APARTADO_R2.match(n.linea_label.texto.strip()):
        return RANGO_APARTADO_A     # raíz de apartado de la regla 4
    return None


def dividir_a(res: ResultadoParseo, sin_raiz: bool, fila_tabla=None) -> list[dict]:
    """A de S0-6a (ver RE_APARTADO_A). Devuelve un evento por división abierta y por nodo adoptado."""
    eventos: list[dict] = []
    nbloque = [0]

    def _pos(l: Linea) -> tuple:
        return (l.pagina, l.top)

    def raiz(n: Nodo) -> Nodo:
        while n.padre is not None:
            n = n.padre
        return n

    def indice() -> tuple[list[tuple], dict]:
        """Renglones en orden documental: (renglón, nodo, es_rótulo); y el nodo de cada renglón de segmento."""
        filas, dueno = [], {}

        def rec(n: Nodo) -> None:
            if n.linea_label is not None:
                filas.append((n.linea_label, n, True))
            for s in n.segmentos:
                for l in s:
                    filas.append((l, n, False))
                    dueno[id(l)] = n
            for h in n.hijos:
                rec(h)
        for s0 in res.secciones:
            rec(s0)
        filas.sort(key=lambda f: (f[0].pagina, f[0].top))
        return filas, dueno

    def numerados_despues(h: Nodo, pos: tuple) -> bool:
        def rec(n: Nodo) -> bool:
            for c in n.hijos:
                if c.linea_label is not None and _pos(c.linea_label) > pos and c.rango_a is None:
                    return True
                if rec(c):
                    return True
            return False
        return rec(h)

    def nueva(numero: str, titulo: str, label: Linea | None, pagina: int, prefijo, rango: int) -> Nodo:
        d = Nodo(tipo="seccion", numero=numero, titulo=titulo, pagina=pagina,
                 label_x0=label.x0 if label is not None else None, linea_label=label, sintetica=True, prefijo=prefijo)
        d.rango_a = rango
        return d

    def cortar(x: Nodo, desde: Linea, d: Nodo) -> None:
        """Lleva a `d` los renglones del subárbol de `x` desde `desde` (incluido), en orden."""
        pos = _pos(desde)
        movidos: list[list[Linea]] = []

        def rec(n: Nodo) -> None:
            nuevos = []
            for s in n.segmentos:
                quedan = [l for l in s if _pos(l) < pos]
                van = [l for l in s if _pos(l) >= pos and l is not d.linea_label]
                if quedan:
                    nuevos.append(quedan)
                if van:
                    movidos.append(van)
            n.segmentos = nuevos
            for h in n.hijos:
                rec(h)
        rec(x)
        movidos.sort(key=lambda s: _pos(s[0]))
        d.segmentos.extend(movidos)

    def colocar(d: Nodo, x: Nodo, l: Linea, primero: bool) -> bool:
        """Ubica la división `d` abierta por el renglón `l` del texto de `x` (`primero`: es el primer renglón de ese
        texto); False si no tiene lugar."""
        if x.rango_a is not None:
            if primero:     # primer renglón del texto de otra división: es su hijo
                cortar(x, l, d)
                d.padre = x
                x.hijos.insert(0, d)
                return True
            cortar(x, l, d)
            contenedor = x.padre.hijos if x.padre is not None else res.secciones
            d.padre = x.padre
            contenedor.insert(contenedor.index(x) + 1, d)
            return True
        cadena = []
        n = x
        while n is not None:
            cadena.append(n)
            n = n.padre
        cadena.reverse()
        h = next((c for c in cadena if not numerados_despues(c, _pos(l))), None)
        if h is None:
            return False
        cortar(h, l, d)
        if h.padre is None:
            if h.sintetica:
                d.padre = None
                res.secciones.insert(res.secciones.index(h) + 1, d)
            else:
                d.padre = h
                h.hijos.append(d)
        else:
            d.padre = h.padre
            h.padre.hijos.insert(h.padre.hijos.index(h) + 1, d)
        return True

    # (1) bandas: texto distintivo por página de cuerpo
    paginas_sd = {sd["pagina"] for sd in res.subdocumentos}
    eventos_banda: list[tuple] = []
    if res.bandas_a:
        textos = {p: _texto_banda_a(r) for p, r in res.bandas_a.items()}
        cuenta: dict[str, int] = {}
        for p, ts in textos.items():
            for t in set(ts):
                cuenta[t] = cuenta.get(t, 0) + 1
        comunes = {t for t, c in cuenta.items() if c > len(textos) / 2}
        anterior = None
        primera_pagina = min(textos)
        for p in sorted(textos):
            dist = tuple(t for t in textos[p] if t not in comunes)
            if not dist:
                continue
            titulo_banda = " / ".join(dist)
            if p != primera_pagina and dist != anterior and p not in paginas_sd and p not in res.paginas_caratula_a \
                    and (_es_titulo_mayusculas(titulo_banda) or RE_ANEXO_SD.match(dist[0])
                         or RE_APARTADO_A.match(dist[0]) or RE_SECCION_B582_CAPS.match(dist[0])):
                eventos_banda.append((p, titulo_banda))
            anterior = dist

    # (2) y (3) renglones candidatos, y las bandas, en orden documental
    filas, dueno = indice()
    cand: list[tuple] = []
    for i, (l, n, es_rotulo) in enumerate(filas):
        if es_rotulo or l.pagina in res.paginas_caratula_a:
            continue     # S0-6a-bis: en la carátula no se abre ninguna división
        t = l.texto.strip()
        primero_sin_rotulo = n.linea_label is None and next((s[0] for s in n.segmentos if s), None) is l
        if primero_sin_rotulo or (fila_tabla is not None and fila_tabla(l)) or id(l) in res.recuadro_i:
            continue     # el recuadro de un formulario lo lee I
        sig = filas[i + 1] if i + 1 < len(filas) else None
        if sig is None or sig[2]:
            continue     # D18: entre una madre y sus hijos numerados (o fin del documento)
        ant = filas[i - 1] if i > 0 and filas[i - 1][0].pagina == l.pagina else None
        frontera = ant is None or ant[2] or ant[0].texto.rstrip().endswith((".", ":")) \
            or l.top - ant[0].top >= GAP_BLOQUE_A or _es_titulo_bloque(ant[0])
        ma = RE_APARTADO_A.match(t)
        if ma:
            cand.append((_pos(l), "apartado", l, ma.group(1)))
            continue
        if not _es_titulo_bloque(l) or RE_NUMERACION_A.match(t) or RE_CON_NUMERO_A.search(t) \
                or _continua_titulo_r5c(t, sig[0].texto) or sig[0].pagina != l.pagina:
            continue     # sin numeración ni número, y su bloque sigue en la página
        if n.linea_label is not None and next((x for s in n.segmentos for x in s if x is not n.linea_label), None) is l:
            continue     # el primer renglón del texto de un punto, justo después de su rótulo: encabeza el texto del punto
        if n.linea_label is not None and n.label_x0 is not None and n.text_col is not None \
                and l.x0 > n.label_x0 + TOL_X and l.x0 >= n.text_col - TOL_X:
            continue     # un subtítulo del texto de un punto: corre en la columna de ese texto, más adentro que su rótulo
        prox = next((f for f in filas[i + 1:] if f[2]), None)
        if n.tipo == "punto" and not n.hijos and prox is not None and prox[1].tipo == "punto" \
                and prox[1].padre is n.padre:
            continue     # entre dos ítems seguidos de la misma lista: la lista sigue, y el bloque es del ítem
        if frontera:
            cand.append((_pos(l), "titulo", l, None))
    for p, texto in eventos_banda:
        cand.append(((p, -1.0), "banda", None, texto))
    cand.sort(key=lambda c: c[0])

    for pos, forma, l, extra in cand:
        filas, dueno = indice()
        if forma == "banda":
            primera = next((f for f in filas if f[0].pagina == pos[0]), None)
            if primera is None:
                continue
            l0, n0, es_rotulo = primera
            t0 = raiz(n0)
            if es_rotulo and n0.padre is not None:
                continue     # la banda cambia a mitad de una raíz: no es un límite
            d = nueva(f"bloque{nbloque[0] + 1}", extra, None, pos[0], t0.prefijo, RANGO_BANDA_A)
            if t0.sintetica:
                # modo sin raíz (o raíz de un sub-documento): la banda abre una división de primer nivel
                if es_rotulo:
                    res.secciones.insert(res.secciones.index(n0), d)
                elif numerados_despues(t0, _pos(l0)):
                    continue
                else:
                    cortar(t0, l0, d)
                    res.secciones.insert(res.secciones.index(t0) + 1, d)
            elif es_rotulo or not colocar(d, n0, l0, False):
                continue     # dentro de una sección real, la división cuelga de la sección
            nbloque[0] += 1
            eventos.append({"tipo": "division_a", "forma": "banda", "seccion": f"S{d.numero}", "prefijo": d.prefijo,
                            "pagina": pos[0], "rotulo": extra[:90]})
            continue
        x = dueno.get(id(l))
        if x is None:
            continue
        if x.rango_a is not None and " ".join(l.texto.split()) == " ".join(x.titulo.split()):
            continue     # repite el título de la división que lo contiene
        es_primero = next((s[0] for s in x.segmentos if s), None) is l
        if forma == "apartado":
            d = nueva(extra, l.texto.strip(), l, l.pagina, raiz(x).prefijo, RANGO_APARTADO_A)
        else:
            nbloque[0] += 1
            d = nueva(f"bloque{nbloque[0]}", l.texto.strip(), l, l.pagina, raiz(x).prefijo, RANGO_TITULO_A)
        # el renglón deja el texto de su nodo: es el rótulo de la división
        x.segmentos = [[y for y in s if y is not l] for s in x.segmentos]
        x.segmentos = [s for s in x.segmentos if s]
        if not colocar(d, x, l, es_primero):
            x.segmentos = sorted(x.segmentos + [[l]], key=lambda s: _pos(s[0]))
            if forma != "apartado":
                nbloque[0] -= 1
            continue
        eventos.append({"tipo": "division_a", "forma": forma, "seccion": f"S{d.numero}", "prefijo": d.prefijo,
                        "pagina": l.pagina, "rotulo": l.texto[:90]})

    # adopción: cada división de primer nivel (y la raíz «0» de un sub-documento) es madre de lo que sigue, hasta la
    # próxima de igual o mayor nivel; en el modo sin raíz adopta las raíces; un cambio de sub-documento lo cierra todo
    nuevas: list[Nodo] = []
    pila: list[tuple[int, Nodo]] = []
    prefijo_ant = object()
    for n in res.secciones:
        if n.prefijo != prefijo_ant:
            pila = []
            prefijo_ant = n.prefijo
        rango = _rango_a(n)
        if rango is not None:
            while pila and pila[-1][0] >= rango:
                pila.pop()
            if pila:
                madre = pila[-1][1]
                n.padre = madre
                madre.hijos.append(n)
                eventos.append({"tipo": "adoptado_a", "madre": f"S{madre.numero}", "nodo": f"S{n.numero}",
                                "prefijo": n.prefijo})
            else:
                nuevas.append(n)
            pila.append((rango, n))
            m = n
            while m.hijos and m.hijos[-1].rango_a is not None:
                m = m.hijos[-1]
                pila.append((m.rango_a, m))
            continue
        adoptable = n.sintetica and (sin_raiz or (pila and pila[0][0] == RANGO_SUBDOC_A))
        if pila and (adoptable or pila[0][0] == RANGO_SUBDOC_A):
            madre = pila[-1][1]
            n.padre = madre
            madre.hijos.append(n)
            eventos.append({"tipo": "adoptado_a", "madre": f"S{madre.numero}", "nodo": f"S{n.numero}",
                            "prefijo": n.prefijo})
        else:
            nuevas.append(n)
    res.secciones = nuevas

    # columnas de las divisiones y de las raíces «0»; el rótulo del sub-documento que no es su renglón de rótulo (el
    # membrete de un formulario, I) pasa al texto propio de la raíz «0», que la herencia no repite
    def columnas(n: Nodo) -> None:
        for h in n.hijos:
            columnas(h)
        if _rango_a(n) is not None and n.text_col is None:
            primero = next((s[0] for s in n.segmentos if s), None)
            n.text_col = primero.x0 if primero is not None else None     # la columna de su texto
        if _rango_a(n) is not None and n.hijos:
            if n.col_hijos is None:
                n.col_hijos = next((h.label_x0 for h in n.hijos if h.label_x0 is not None), None)
            if n.numero == "0" and n.linea_label is not None \
                    and " ".join(n.linea_label.texto.split()) != " ".join(n.titulo.split()):
                n.segmentos.insert(0, [n.linea_label])
                n.linea_label = None
    for s0 in res.secciones:
        columnas(s0)
    return eventos


def mover_encabezado_tabla_f(res: ResultadoParseo) -> list[dict]:
    """F2 de S0-6a (ver MAX_CHARS_CELDA_F): el bloque final de la intro de un nodo hecho solo de renglones de encabezado de
    columnas (de MAX_CHARS_CELDA_F caracteres o menos, a la derecha del rótulo de su primer hijo), delante de un primer hijo
    con filas en columnas, pasa al principio de la primera unidad terminal de la tabla (`lineas_previas`). Una intro de un
    renglón que continúa el título del nodo (las condiciones de R5-c) no es encabezado de columnas."""
    eventos: list[dict] = []

    def todas(n: Nodo) -> list[Linea]:
        out = list(n.lineas_previas) + ([n.linea_label] if n.linea_label is not None else []) + \
            [l for s in n.segmentos for l in s]
        for h in n.hijos:
            out += todas(h)
        return out

    def visitar(n: Nodo) -> None:
        for h in n.hijos:
            visitar(h)
        if not n.hijos:
            return
        h0 = n.hijos[0]
        if h0.linea_label is None or h0.label_x0 is None:
            return
        marca = (h0.linea_label.pagina, h0.linea_label.top)
        intro = [s for s in n.segmentos if s and (s[0].pagina, s[0].top) < marca]
        if len(intro) == 1 and len(intro[0]) == 1 and _continua_titulo_r5c(n.titulo or "", intro[0][0].texto):
            return     # el renglón continúa el título (R5-c, que sigue como está; B1): no es encabezado de columnas
        cola: list[list[Linea]] = []
        for s in reversed(intro):
            if all(len(l.texto.strip()) <= MAX_CHARS_CELDA_F and l.x0 > h0.label_x0 + TOL_X for l in s):
                cola.insert(0, s)
            else:
                break
        if not cola or not any(l.ngaps >= 1 for l in todas(h0)):
            return
        hoja = h0
        while hoja.hijos:
            hoja = hoja.hijos[0]
        lineas = [l for s in cola for l in s]
        n.segmentos = [s for s in n.segmentos if not any(s is c for c in cola)]
        hoja.lineas_previas = lineas + hoja.lineas_previas
        eventos.append({"tipo": "encabezado_de_tabla_con_su_tabla_f", "de": _nombre_c(n), "a": _nombre_c(hoja),
                        "pagina": lineas[0].pagina, "renglones": len(lineas),
                        "texto": " | ".join(l.texto for l in lineas)[:120]})

    for s0 in res.secciones:
        visitar(s0)
    return eventos


def juntar_rotulo_vertical(res: ResultadoParseo) -> list[dict]:
    """U-SEG-OFICIAL, S0-5a, R5-e (ver MIN_LETRAS_VERTICAL), sobre el árbol ya parseado (la lectura de la página no
    cambia: una letra suelta al principio de la página corta la zona de encabezado, y sacarla antes del parseo hacía
    descartar el membrete del formulario). Cada rótulo vertical (renglones de una sola letra mayúscula en la misma
    columna, uno debajo del otro, en segmentos de prosa) se junta en un renglón con la palabra, en el lugar de la
    última letra y en la unidad que la tiene, y las otras letras salen de sus unidades. El rótulo juntado cuenta como
    un renglón en `lineas_contenido` (la cobertura sigue exacta). Devuelve un evento por rótulo."""
    eventos: list[dict] = []
    ubic: dict[int, tuple[Nodo, list[Linea]]] = {}

    def rec(n: Nodo) -> None:
        for sg in n.segmentos:
            for l in sg:
                if len(l.texto.strip()) == 1 and RE_MAYUSCULA_R5A.match(l.texto.strip()):
                    ubic[id(l)] = (n, sg)
        for h in n.hijos:
            rec(h)
    for s0 in res.secciones:
        rec(s0)
    letras = sorted((sg[[id(x) for x in sg].index(i)] for i, (n, sg) in ubic.items()),
                    key=lambda l: (l.pagina, l.top))
    grupos: list[list[Linea]] = []
    for l in letras:
        for g in grupos:
            if g[0].pagina == l.pagina and abs(l.x0 - g[0].x0) <= TOL_X and 0 < l.top - g[-1].top <= MAX_SALTO_VERTICAL:
                g.append(l)
                break
        else:
            grupos.append([l])
    for g in (g for g in grupos if len(g) >= MIN_LETRAS_VERTICAL):
        palabra = "".join(x.texto.strip() for x in g)
        dueno, sg_dueno = ubic[id(g[-1])]
        unida = Linea(pagina=g[-1].pagina, top=g[-1].top, x0=min(x.x0 for x in g), texto=palabra, ngaps=0,
                      ultimo_numerico=False, primer_codigo=False)
        sg_dueno[[id(x) for x in sg_dueno].index(id(g[-1]))] = unida
        quitar = {id(x) for x in g[:-1]}
        for n in {id(ubic[id(x)][0]): ubic[id(x)][0] for x in g[:-1]}.values():
            n.segmentos = [[l for l in sg if id(l) not in quitar] for sg in n.segmentos]
            n.segmentos = [sg for sg in n.segmentos if sg]
        res.lineas_contenido -= len(g) - 1
        eventos.append({"tipo": "rotulo_vertical_r5e", "pagina": unida.pagina, "texto": palabra,
                        "x0": round(unida.x0, 1), "tops": [round(x.top, 1) for x in g],
                        "unidades_de_las_letras": sorted({_nombre_r5e(ubic[id(x)][0]) for x in g}),
                        "unidad_destino": _nombre_r5e(dueno)})
    return eventos


def _raiz_nodo(n: Nodo) -> Nodo:
    while n.padre is not None:
        n = n.padre
    return n


def _nombre_r5e(n: Nodo) -> str:
    base = n.numero if n.tipo == "punto" else f"S{n.numero}"
    p = _raiz_nodo(n).prefijo
    return f"{p}::{base}" if p else base


# --------------------------------- Regla 2: cero cortes intra-palabra

RE_GUION_FINAL = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]-$")
RE_INICIO_MINUSCULA = re.compile(r"^[a-záéíóúüñ]")


def _recolectar_orden_documental(res: ResultadoParseo) -> list[tuple[Linea, tuple]]:
    """Todas las líneas de la estructura en orden documental (pagina, top, x0),
    cada una con su contenedor: ('label', nodo, i_seccion) o
    ('seg', nodo, segmento, i_seccion)."""
    entradas: list[tuple[Linea, tuple]] = []

    def rec(n: Nodo, i_sec: int) -> None:
        for l in n.lineas_previas:
            entradas.append((l, ("previa", n, i_sec)))
        if n.linea_label is not None:
            entradas.append((n.linea_label, ("label", n, i_sec)))
        for s in n.segmentos:
            for l in s:
                entradas.append((l, ("seg", n, s, i_sec)))
        for h in n.hijos:
            rec(h, i_sec)

    for i, s in enumerate(res.secciones):
        rec(s, i)
    entradas.sort(key=lambda e: (e[0].pagina, e[0].top, e[0].x0))
    return entradas


def _clasificar_frontera(ult: Linea, prox_entrada: tuple | None, i_sec: int) -> str:
    """Clasifica la frontera que sigue a `ult` (última línea de un segmento):
    'intra_palabra' (corte a corregir), 'ok', o un motivo de exclusión
    auditable. Detector: la línea termina en letra+guion ASCII y la línea
    documental siguiente existe, no es label de nodo, está en la misma
    sección, tiene forma de prosa (sin fronteras de columna) y arranca en
    minúscula (el silabeo del BCRA continúa siempre en minúscula). Los guards
    sobre la línea SIGUIENTE matan los falsos positivos medidos: filas de
    rating 'AA- A- BBB- B-' y encabezados '-En millones de pesos-' (la fila
    siguiente arranca en dígito o mayúscula), cierres de aparte '-…-'
    seguidos de mayúscula, y celdas de tabla cuya continuación quedó
    desplazada por la linealización (la línea siguiente es otra fila o un
    código de partida). La línea que termina partida NO se filtra por ngaps
    propios: los renglones de definición de fórmula ('RM: … en la Sec-' →
    'ción 6.') tienen fronteras de columna y su continuación es genuina."""
    if not RE_GUION_FINAL.search(ult.texto.strip()):
        return "ok"
    if prox_entrada is None:
        return "sin_linea_siguiente"
    prox, cont = prox_entrada
    if cont[0] == "label":
        return "siguiente_es_label"
    if cont[-1] != i_sec:
        return "siguiente_en_otra_seccion"
    if prox.ngaps:
        return "excluida_siguiente_fila_tabla"
    if not RE_INICIO_MINUSCULA.match(prox.texto.strip()):
        return "excluida_inicio_no_minuscula"
    return "intra_palabra"


def detectar_fronteras_intra_palabra(res: ResultadoParseo) -> dict:
    """Cuenta las fronteras de segmento que caen intra-palabra (detector de
    `_clasificar_frontera`) sin corregir nada. Devuelve también las líneas
    sospechosas excluidas, para auditoría."""
    entradas = _recolectar_orden_documental(res)
    idx = {id(l): i for i, (l, _) in enumerate(entradas)}
    intra, excluidas = [], []
    vistos: set[int] = set()
    for l, cont in entradas:
        if cont[0] != "seg":
            continue
        seg = cont[2]
        if id(seg) in vistos or seg[-1] is not l:
            continue
        vistos.add(id(seg))
        i = idx[id(l)]
        prox = entradas[i + 1] if i + 1 < len(entradas) else None
        clase = _clasificar_frontera(l, prox, cont[3])
        unidad = cont[1].numero if cont[1].tipo == "punto" else f"S{cont[1].numero}"
        if clase == "intra_palabra":
            intra.append({"unidad": unidad, "pagina": l.pagina,
                          "ultima_linea": l.texto[-60:],
                          "siguiente": prox[0].texto[:60] if prox else None})
        elif clase != "ok":
            excluidas.append({"unidad": unidad, "pagina": l.pagina,
                              "clase": clase, "ultima_linea": l.texto[-60:]})
    return {"n_intra_palabra": len(intra), "fronteras": intra,
            "sospechosas_excluidas": excluidas}


def corregir_fronteras_intra_palabra(res: ResultadoParseo) -> dict:
    """REGLA 2. Corre cada frontera intra-palabra línea por línea: la línea
    documental siguiente (la que cierra la palabra) se mueve al final del
    segmento que terminaba partido, hasta punto fijo (si la línea movida
    también termina partida, la frontera se vuelve a correr). El donante que
    queda vacío se elimina. Solo cambia DÓNDE cae la frontera: ninguna línea
    se crea, se pierde ni se parte (la cobertura por identidad de objeto lo
    verifica). Los movimientos entre segmentos de un mismo nodo no alteran el
    texto propio (la concatenación es idéntica); los movimientos entre nodos
    corrigen costuras de re-anclaje que caían a mitad de palabra."""
    corridas: list[dict] = []
    guarda = 20000
    while guarda:
        guarda -= 1
        entradas = _recolectar_orden_documental(res)
        idx = {id(l): i for i, (l, _) in enumerate(entradas)}
        mov = None
        vistos: set[int] = set()
        for l, cont in entradas:
            if cont[0] != "seg":
                continue
            seg = cont[2]
            if id(seg) in vistos or seg[-1] is not l:
                continue
            vistos.add(id(seg))
            i = idx[id(l)]
            prox = entradas[i + 1] if i + 1 < len(entradas) else None
            if _clasificar_frontera(l, prox, cont[3]) == "intra_palabra":
                mov = (cont, prox)
                break
        if mov is None:
            break
        (_, nodo, seg, _), (prox_l, prox_cont) = mov
        _, nodo_don, seg_don, _ = prox_cont
        if seg_don[0] is not prox_l:
            # inconsistencia estructural: la línea siguiente no encabeza su
            # segmento; se registra y no se corrige (esperado: nunca)
            res.avisos.append({"tipo": "frontera_intra_palabra_no_corregible",
                               "pagina": prox_l.pagina, "texto": prox_l.texto[:80]})
            break
        seg_don.pop(0)
        seg.append(prox_l)
        if not seg_don:
            nodo_don.segmentos.remove(seg_don)
        corridas.append({
            "pagina": prox_l.pagina,
            "de_unidad": nodo_don.numero if nodo_don.tipo == "punto" else f"S{nodo_don.numero}",
            "a_unidad": nodo.numero if nodo.tipo == "punto" else f"S{nodo.numero}",
            "mismo_nodo": nodo_don is nodo,
            "linea_movida": prox_l.texto[:90],
        })
    return {"lineas_corridas": corridas, "n_corridas": len(corridas)}


# -------------------------------------------------------------------- índice

def parsear_indice(paginas: list[list[Linea]], roles: list[str],
                   marcadores_b582: bool = False) -> list[dict]:
    """Entradas del índice: {tipo: seccion|punto|otro, numero, titulo, pagina}.
    Los títulos envueltos en varias líneas se re-unen (una línea sin numeración
    continúa la entrada previa). Con `marcadores_b582=True` (B5.8.2) las
    variantes de marcador de índice se saltan como marcador, las entradas de
    sección variante ('Sección A. Introducción' de reqcac, 'SECCION 1 - …' de
    ri_dcpc) se leen como entradas de sección, y el banner de caja mixta se
    descarta como encabezado."""
    entradas: list[dict] = []
    banners_texto = detectar_banners_texto(paginas) if marcadores_b582 else None
    for lineas, rol in zip(paginas, roles):
        if rol != ROL_INDICE:
            continue
        contenido, _desc, _sec = separar_encabezado_pie(
            lineas, capturar_seccion=False, banners_texto=banners_texto)
        for linea in contenido:
            t = linea.texto.strip()
            if RE_MARCA_INDICE.match(t) or RE_MARCA_INDICE_SIN_GUIONES.match(t) \
                    or (marcadores_b582 and RE_MARCA_INDICE_B582.match(t)):
                # la variante sin guiones se salta en cualquier posición: en una
                # página ya clasificada índice, 'Índice' a línea entera es el
                # marcador (ninguna sección se titula así), no una entrada
                continue
            m_sec = RE_SECCION.match(t)
            sec_b582 = (_match_seccion_b582(t)
                        if marcadores_b582 and not m_sec else None)
            tokens = t.split()
            m_num = RE_NUM_TOKEN.match(tokens[0]) if tokens else None
            if not m_num and tokens and re.match(r"^\d+(\.\d+)*$", tokens[0]) and len(tokens) > 1:
                m_num = re.match(r"^(\d+(?:\.\d+)*)$", tokens[0])  # índice sin punto final
            if m_sec:
                entradas.append({"tipo": "seccion", "numero": m_sec.group(1),
                                 "titulo": m_sec.group(2).strip(), "pagina": linea.pagina})
            elif sec_b582 is not None:
                entradas.append({"tipo": "seccion", "numero": sec_b582[0],
                                 "titulo": sec_b582[1], "pagina": linea.pagina})
            elif m_num and int(m_num.group(1).split(".")[0]) <= MAX_RAIZ:
                entradas.append({"tipo": "punto", "numero": m_num.group(1),
                                 "titulo": t[len(tokens[0]):].strip(), "pagina": linea.pagina})
            elif entradas:
                entradas[-1]["titulo"] = (entradas[-1]["titulo"] + " " + t).strip()
            else:
                entradas.append({"tipo": "otro", "numero": None, "titulo": t,
                                 "pagina": linea.pagina})
    return entradas


# --------------------------------------------------------------- divergencias

def divergencias_indice_cuerpo(res: ResultadoParseo, indice: list[dict]) -> dict:
    """Comparación bidireccional a la granularidad que declara el índice."""
    idx_secciones = {e["numero"]: e for e in indice if e["tipo"] == "seccion"}
    idx_puntos = {e["numero"]: e for e in indice if e["tipo"] == "punto"}

    cuerpo_secciones = {s.numero: s for s in res.secciones}
    cuerpo_puntos: dict[str, Nodo] = {}

    def rec(n: Nodo):
        for h in n.hijos:
            if h.tipo == "seccion":
                cuerpo_secciones.setdefault(h.numero, h)     # A de S0-6a: una sección que adoptó una división
            else:
                cuerpo_puntos[h.numero] = h
            rec(h)
    for s in res.secciones:
        rec(s)

    anunciado_sin_cuerpo = []
    for num, e in idx_puntos.items():
        if num not in cuerpo_puntos:
            anunciado_sin_cuerpo.append({"numero": num, "titulo": e["titulo"],
                                         "pagina_indice": e["pagina"]})
    for num, e in idx_secciones.items():
        if num not in cuerpo_secciones:
            anunciado_sin_cuerpo.append({"numero": f"S{num}", "titulo": e["titulo"],
                                         "pagina_indice": e["pagina"]})

    profundidad_indice = max((n.count(".") + 1 for n in idx_puntos), default=0)
    en_cuerpo_sin_anunciar = []
    for num, n in cuerpo_puntos.items():
        if num.count(".") + 1 <= profundidad_indice and num not in idx_puntos:
            en_cuerpo_sin_anunciar.append({"numero": num, "titulo": n.titulo[:100],
                                           "pagina_cuerpo": n.pagina})
    for num, s in cuerpo_secciones.items():
        if num not in idx_secciones:
            en_cuerpo_sin_anunciar.append({"numero": f"S{num}", "titulo": s.titulo[:100],
                                           "pagina_cuerpo": s.pagina})

    def _clave(d):
        # _orden_componente_seccion == int(x) para dígitos (orden histórico
        # intacto); letras y romanos (B5.8.2) ordenan por su interpretación
        return [_orden_componente_seccion(x)
                for x in d["numero"].lstrip("S").split(".")]
    return {
        "to": res.to,
        "profundidad_declarada_indice": profundidad_indice,
        "anunciado_sin_cuerpo": sorted(anunciado_sin_cuerpo, key=_clave),
        "en_cuerpo_sin_anunciar": sorted(en_cuerpo_sin_anunciar, key=_clave),
        "titulos_distintos": _titulos_distintos(idx_puntos, cuerpo_puntos),
    }


def _norm_titulo(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _titulos_distintos(idx_puntos: dict, cuerpo_puntos: dict[str, Nodo]) -> list[dict]:
    out = []
    for num, e in idx_puntos.items():
        n = cuerpo_puntos.get(num)
        if n is None:
            continue
        ti, tc = _norm_titulo(e["titulo"]), _norm_titulo(n.titulo)
        if ti and tc and not (ti.startswith(tc[:25]) or tc.startswith(ti[:25])):
            out.append({"numero": num, "titulo_indice": e["titulo"][:90],
                        "titulo_cuerpo": n.titulo[:90]})
    return out


# ------------------------------------------------------------------- chunker

def _texto_segmento(seg: list[Linea]) -> str:
    return "\n".join(l.texto for l in seg)


def _paginas_de(lineas: list[Linea]) -> list[int]:
    return sorted({l.pagina for l in lineas})


def _flags_tabla_formula(lineas: list[Linea]) -> dict:
    """Heurísticas documentadas de detección (solo flag, sin tratamiento):

    contenido_tabular — señales de filas en columnas:
      * fuerte: línea con ≥2 fronteras de columna (huecos > GAP_COL pt), o
        marcador lexical 'Cuadro N' (modelos de información del ric);
      * débil: línea con ≥1 frontera y último token numérico (patrón
        'concepto … valor' de los cuadros de ponderadores), o con ≥1 frontera
        y primer token código (≥3 dígitos: filas 'código partida descripción').
      Flag si fuertes ≥ 3, o fuertes+débiles ≥ 5.

    formula — señales de expresión matemática:
      * línea con '=' (asignación de expresión, p.ej. 'C = (k x 0,08 x APR) + INC');
      * línea 'donde:' aislada (definición de términos de una expresión);
      * anuncio '…siguiente expresión:'.
    """
    fuertes = [l for l in lineas
               if l.ngaps >= 2 or re.match(r"^Cuadro \d", l.texto.strip())]
    debiles = [l for l in lineas
               if l.ngaps == 1 and (l.ultimo_numerico or l.primer_codigo)]
    tabular = len(fuertes) >= 3 or (len(fuertes) + len(debiles)) >= 5
    ev_tab = (fuertes + debiles)[:3]

    ev_for = []
    for l in lineas:
        t = l.texto.strip()
        if "=" in t or re.fullmatch(r"donde\s*:", t, re.IGNORECASE) \
                or re.search(r"siguiente\s+expresi[oó]n\s*:?\s*$", t, re.IGNORECASE):
            ev_for.append(l)
    formula = bool(ev_for)
    return {
        "contenido_tabular": tabular,
        "formula": formula,
        "evidencia_tabular": [l.texto[:90] for l in ev_tab] if tabular else [],
        "evidencia_formula": [l.texto[:90] for l in ev_for[:3]],
    }


def _marca_hijo(h: Nodo) -> tuple:
    """Posición de un hijo para ubicar los segmentos de su padre: la de su rótulo o, sin rótulo (una raíz implícita que
    adoptó una división de A de S0-6a), la de su primer renglón."""
    if h.linea_label is not None:
        return (h.pagina, h.linea_label.top)
    return _pos_c(h)


def _es_raiz_subdoc(n: Nodo) -> bool:
    """A de S0-6a: la raíz «0» de un sub-documento (su rótulo va en la cadena de sub-documentos de la herencia)."""
    return n.sintetica and n.numero == "0" and n.prefijo is not None and n.titulo not in ("Preámbulo", "")


def _rol_segmentos(nodo: Nodo) -> list[dict]:
    """Clasifica los segmentos de un nodo CON hijos por posición relativa:
    intro (antes del primer hijo), cierre (después del último), intersticial.
    La posición se determina por (página, top) de la primera línea del
    segmento contra las de los labels de los hijos."""
    if not nodo.hijos:
        return [{"rol": "contenido", "seg": s} for s in nodo.segmentos]
    marcas = [_marca_hijo(h) for h in nodo.hijos]
    primera, ultima = marcas[0], marcas[-1]
    out = []
    for s in nodo.segmentos:
        pos = (s[0].pagina, s[0].top)
        if pos <= primera:     # igualdad: solo con las partes de un renglón que I lee por columna
            rol = "intro"
        elif pos > ultima:
            rol = "cierre"
        else:
            rol = "intersticial"
        out.append({"rol": rol, "seg": s})
    return out


def _materializa_bloque(texto: str) -> bool:
    """Criterio de materialización de mini-chunks (enmienda 01 §2.a, letra):
    el bloque contiene texto además de su línea de título. Los tramos
    `encabezado` SON la línea de título (construida del label) y nunca llegan
    acá; para los segmentos de prosa —que no contienen la línea de label— el
    criterio se reduce a texto normalizado no vacío."""
    return bool("".join(texto.split()))


# --------------------------------------- tope de la herencia (e0-r2, U-R2-CODIGO-2)
MARCA_RECORTE_HERENCIA = "[recorte de E0: no se transcriben {n} caracteres de este bloque heredado]"


def _piezas_tramo(texto: str) -> list[str]:
    """Renglones de un tramo; un bloque de tabla serializada ([TABLA … FIN
    TABLA …]) es una sola pieza."""
    out, tabla = [], None
    for ln in texto.split("\n"):
        if tabla is not None:
            tabla.append(ln)
            if ln.startswith("[FIN TABLA "):
                out.append("\n".join(tabla))
                tabla = None
        elif ln.startswith("[TABLA "):
            tabla = [ln]
        else:
            out.append(ln)
    if tabla is not None:
        out.append("\n".join(tabla))
    return out


def _recortar_tramo(texto: str, lado: str, bloque: int) -> str:
    """Piezas enteras desde el extremo cercano (`lado`: «final» o «inicio»)
    hasta `bloque` caracteres; la más cercana entra siempre."""
    piezas = _piezas_tramo(texto)
    idx = list(range(len(piezas)))
    if lado == "final":
        idx.reverse()
    acum, quedan = 0, []
    for k, i in enumerate(idx):
        n = len(piezas[i]) + 1
        if k == 0 or acum + n <= bloque:
            quedan.append(i)
            acum += n
        else:
            break
    return "\n".join(piezas[i] for i in sorted(quedan))


def recortar_herencia(tramos: list[dict], lados: list[str | None], umbral: int, bloque: int,
                      saltar: frozenset = frozenset()) -> tuple[list[dict], list[dict]]:
    """Tope de la herencia (e0-r2, U-R2-CODIGO-2, C2, punto h; diseño
    aprobado en r2_codigo2/freno_c2_diseno.md). Si la suma del texto de los
    tramos pasa `umbral`, de cada bloque de prosa heredado se conserva el
    tramo más cercano a la unidad (si pasa `bloque` caracteres, sus renglones
    desde el extremo cercano hasta `bloque`, sin partir una tabla
    serializada) y, a continuación, tramos enteros hasta sumar `bloque`
    caracteres más; los tramos `encabezado` (títulos) quedan enteros. Un
    bloque es la intro o el chapeau de un ancestro, su cierre, o sus
    intersticiales de un mismo lado de la unidad. `lados[i]` es el extremo
    que se conserva del tramo i: «final» (intro, chapeau e intersticial
    anterior a la unidad) o «inicio» (cierre e intersticial posterior);
    None en los encabezados. En el lugar de lo omitido va un tramo marcador
    de una línea (MARCA_RECORTE_HERENCIA), con el rol y la unidad de origen
    del bloque. `saltar`: claves de bloque (unidad, rol, lado) que no se
    recortan (ya recortados). Devuelve (tramos, bloques recortados)."""
    if sum(len(t["texto"]) for t in tramos) <= umbral:
        return tramos, []
    grupos: dict[tuple, list[int]] = {}
    for i, t in enumerate(tramos):
        if t["tipo"] == "encabezado":
            continue
        clave = (t["unidad_origen"], t["tipo"], lados[i])
        grupos.setdefault(clave, []).append(i)
    reemplazo: dict[int, list[dict]] = {}
    declarados = []
    for clave, blq in grupos.items():
        if clave in saltar:
            continue
        lado = clave[2]
        orden = list(reversed(blq)) if lado == "final" else list(blq)
        acum, conservados = 0, [orden[0]]
        for i in orden[1:]:
            n = len(tramos[i]["texto"])
            if acum + n <= bloque:
                conservados.append(i)
                acum += n
            else:
                break
        omitidos = [i for i in blq if i not in conservados]
        cercano = orden[0]
        recorte = None
        if len(tramos[cercano]["texto"]) > bloque:
            recorte = _recortar_tramo(tramos[cercano]["texto"], lado, bloque)
            if recorte == tramos[cercano]["texto"]:
                recorte = None
        if not omitidos and recorte is None:
            continue
        n_om = sum(len(tramos[i]["texto"]) for i in omitidos)
        if recorte is not None:
            n_om += len(tramos[cercano]["texto"]) - len(recorte)
        t0 = tramos[blq[0]]
        declarados.append({"unidad_origen": t0["unidad_origen"], "rol": t0["tipo"], "conservado": lado,
                           "caracteres_omitidos": n_om})
        marca = {"tipo": t0["tipo"], "unidad_origen": t0["unidad_origen"],
                 "texto": MARCA_RECORTE_HERENCIA.format(n=n_om),
                 "paginas": sorted({p for i in blq for p in tramos[i].get("paginas") or []})}
        for i in omitidos:
            reemplazo[i] = []
        nuevo = [{**tramos[cercano], "texto": recorte}] if recorte is not None else [tramos[cercano]]
        if omitidos and lado == "final":
            reemplazo[cercano] = nuevo
            reemplazo[min(omitidos)] = [marca]
        elif omitidos:
            reemplazo[cercano] = nuevo
            reemplazo[max(omitidos)] = [marca]
        else:
            reemplazo[cercano] = [marca] + nuevo if lado == "final" else nuevo + [marca]
    if not declarados:
        return tramos, []
    out = []
    for i, t in enumerate(tramos):
        out.extend(reemplazo.get(i, [t]))
    return out, declarados


def lados_por_pagina(tramos: list[dict], paginas_unidad: list[int]) -> list[str | None]:
    """Lado que se conserva de cada tramo, cuando no se tienen las líneas de
    los segmentos (las partes `::parteK`, que arman su herencia en
    correr_e0._sub_chunks_de): «final» en la intro y el chapeau, «inicio» en
    el cierre; un intersticial es posterior a la unidad solo si todas sus
    páginas son posteriores a las de la unidad."""
    out: list[str | None] = []
    for t in tramos:
        if t["tipo"] == "encabezado":
            out.append(None)
        elif t["tipo"] == "cierre":
            out.append("inicio")
        elif t["tipo"] == "intersticial" and t.get("paginas") and paginas_unidad \
                and min(t["paginas"]) > max(paginas_unidad):
            out.append("inicio")
        else:
            out.append("final")
    return out


def _flags_numeracion(nodo: "Nodo") -> dict:
    """e0-r2 (U-R2-CODIGO-2, C2, punto f): el número impreso de una unidad
    renumerada por lista, y la corrección declarada. U-SEG-OFICIAL, S0-4: el de un apartado de una sección sin
    puntos (regla de apartados)."""
    if not nodo.numero_impreso:
        return {}
    if nodo.apartado:
        return {"numero_impreso": nodo.numero_impreso,
                "correccion_numeracion": f"apartado_de_seccion: el PDF imprime {nodo.numero_impreso}. dentro de la "
                                         f"Sección {nodo.padre.numero}; E0 lo abre como el punto {nodo.numero}"}
    return {"numero_impreso": nodo.numero_impreso,
            "correccion_numeracion": f"renumerado_por_lista: el PDF imprime {nodo.numero_impreso} donde la "
                                     f"numeración del TO sigue con {nodo.numero}"}


def clase_titulo_4ab(nodo: "Nodo") -> tuple[str, "Linea"] | None:
    """U-SEG-OFICIAL, S0-4, reglas 4a y 4b (ver RE_VERBO_ORACION_4AB). Condición común: un punto con hijos cuyo
    título no termina en punto (termina en guion de corte, en coma o sin puntuación) y cuya intro empieza en
    minúscula: el renglón del rótulo es el primero de un texto que sigue en la intro. Devuelve («4b», primer renglón
    de la intro) si ese renglón completa el título (termina en punto, o es toda la intro y no termina en dos puntos)
    y no lleva un verbo; («4a», primer renglón) si la primera oración (el título con los renglones del primer segmento
    de la intro hasta el primero que termina en punto o en dos puntos) termina en dos puntos o lleva un verbo; None si
    no."""
    if nodo.tipo != "punto" or not nodo.hijos or nodo.linea_label is None:
        return None
    intro = [it["seg"] for it in _rol_segmentos(nodo) if it["rol"] == "intro"]
    if not intro or not intro[0]:
        return None
    t = nodo.titulo.rstrip()
    l1 = intro[0][0]
    if not t or t.endswith(".") or not l1.texto.lstrip()[:1].islower():
        return None
    r1 = l1.texto.rstrip()
    toda = len(intro) == 1 and len(intro[0]) == 1
    if (r1.endswith(".") or (toda and not r1.endswith(":"))) and not RE_VERBO_ORACION_4AB.search(r1):
        return "4b", l1
    oracion = [r1]
    for l in intro[0][1:]:
        if oracion[-1].endswith((".", ":")):
            break
        oracion.append(l.texto.rstrip())
    if oracion[-1].endswith(":") or RE_VERBO_ORACION_4AB.search(t + " " + " ".join(oracion)):
        return "4a", l1
    return None


def _continua_titulo_r5c(titulo: str, chapeau: str) -> bool:
    """R5-c de S0-5a (ver PALABRAS_FUNCIONALES_R5C): el renglón `chapeau` continúa `titulo`."""
    t, c = titulo.rstrip(), chapeau.strip()
    if not t or not c or t.endswith((".", ":", ";")):
        return False
    ult = t.split()[-1].strip("«»“”\"'()").lower()
    abierta = (t.count("“") > t.count("”") or t.count("«") > t.count("»") or t.count("(") > t.count(")")
               or t.count('"') % 2 == 1)
    return bool(RE_GUION_FINAL.search(t)) or ult in PALABRAS_FUNCIONALES_R5C or abierta or c[:1].islower()


def clase_encabezado_b(nodo: "Nodo") -> tuple[str, list] | None:
    """B de S0-6a (ver LARGO_RENGLON_TITULO_B): («b1», renglones de la intro que completan el título), («b2», []) si el
    número va seguido de un párrafo, o None si el rótulo no sigue en la intro (o el nodo no es un punto o una raíz del
    modo sin raíz con rótulo e hijos)."""
    if not nodo.hijos or nodo.linea_label is None:
        return None
    if nodo.tipo != "punto" and not (nodo.sintetica and nodo.numero != "0" and not nodo.numero.startswith("bloque")):
        return None
    intro = [it["seg"] for it in _rol_segmentos(nodo) if it["rol"] == "intro"]
    if not intro or not intro[0]:
        return None
    t = nodo.titulo.rstrip()
    if not t or t.endswith((".", ":", ";")):
        return None
    lineas = intro[0]
    if not (_continua_titulo_r5c(t, lineas[0].texto) or len(nodo.linea_label.texto.rstrip()) >= LARGO_RENGLON_TITULO_B):
        return None
    if nodo.tipo == "punto":
        c4 = clase_titulo_4ab(nodo)
        if c4 is not None:
            return ("b1", [c4[1]]) if c4[0] == "4b" else ("b2", [])
    k = None
    for j, l in enumerate(lineas[:MAX_RENGLONES_TITULO_B]):
        tx = l.texto.rstrip()
        if tx.endswith("."):
            k = j
            break
        if tx.endswith((":", ";")):
            break
        if j + 1 >= len(lineas):
            if len(intro) == 1:
                k = j     # como en 4b: la intro entera completa el título y no termina en dos puntos
            break
        if not _continua_titulo_r5c(tx, lineas[j + 1].texto):
            break
    if k is not None and not RE_VERBO_ORACION_4AB.search(" ".join([t] + [l.texto for l in lineas[:k + 1]])):
        r0 = lineas[0].texto.rstrip()
        sangria = nodo.col_hijos is not None and all(abs(l.x0 - nodo.col_hijos) > TOL_X for l in lineas[:k + 1])
        sigue = len(lineas) > k + 1 or len(intro) > 1
        unico = k == 0 and len(lineas) == 1 and len(intro) == 1 and not r0.endswith(":")      # como 4b: toda la intro
        minuscula = k == 0 and r0.endswith(".") and lineas[0].texto.lstrip()[:1].islower()   # como 4b
        if unico or minuscula or sangria or sigue:
            return "b1", lineas[:k + 1]
    return "b2", []


def _continua_intersticial_r5b(previos: list[list[Linea]], s: list[Linea]) -> bool:
    """R5-b de S0-5a (ver RE_CODIGO_R5B): la intersticial `s` continúa la unión `previos` del mismo hueco."""
    ult = previos[-1]
    if not ult or not s or ult[-1].pagina != s[0].pagina:
        return False
    t1, t2 = ult[-1].texto.rstrip(), s[0].texto.strip()
    abierta = not t1.endswith((".", ":", ";"))
    if abierta and t2[:1].islower():
        return True     # (i)
    if abierta and RE_CODIGO_R5B.match(" ".join(l.texto.strip() for l in s)):
        return True     # (i′)
    return (len(previos) == 1 and len(ult) == 1 and bool(RE_ROTULO_R5B.match(ult[0].texto.strip()))
            and not RE_ROTULO_INICIO_R5B.match(t2))     # (ii)


def construir_chunks(res: ResultadoParseo,
                     texto_lineas: Callable[[list[Linea]], str] | None = None,
                     lineas_por_chunk: list[list[Linea]] | None = None,
                     tope_herencia: tuple[int, int] | None = None,
                     oracion_titulo_4a: bool = False,
                     titulo_envuelto_4b: bool = False,
                     intersticial_continuado: bool = False,
                     titulo_seccion_envuelto: bool = False,
                     encabezado_b: bool = False,
                     raiz0_solo_titulo_m: bool = False,
                     rotulo_impreso_d: bool = False) -> list[dict]:
    """Con los dos argumentos opcionales en None (todos los call sites de la
    versión legada de E0) el comportamiento es el histórico, byte a byte.
    Versión e0-r2 (U-R2-CODIGO, R1): `texto_lineas` arma el texto de una
    lista de líneas (sustituye las líneas de una tabla por su bloque
    serializado) y `lineas_por_chunk` recibe, en paralelo a la salida, las
    líneas propias de cada chunk (insumo de la asignación de tablas).
    `tope_herencia` = (U, B) (solo e0-r2, U-R2-CODIGO-2, C2, punto h): la
    herencia de un chunk terminal que pasa U caracteres se recorta con
    `recortar_herencia` y el chunk lo declara en `herencia_recortada`; el
    lado de cada intersticial sale de la línea de su segmento.
    U-SEG-OFICIAL, S0-4 (solo e0-r2): `oracion_titulo_4a` (regla 4a, `clase_titulo_4ab`): el encabezado heredado del
    punto es solo su número y el renglón del rótulo encabeza el bloque de la intro (el mini-chunk y el tramo
    heredado); `titulo_envuelto_4b` (regla 4b): el primer renglón de la intro se junta al título (en un renglón aparte
    del encabezado, tal cual está en el PDF) y sale de la intro, que se emite solo si le queda texto. Los ids de las
    unidades de un sub-documento llevan su prefijo (`<to>::<prefijo>::<unidad>`) y su herencia empieza con los rótulos
    de la cadena de sub-documentos (ResultadoParseo.subdocumentos), uno por tramo `encabezado`; la raíz «0» de un
    sub-documento hereda solo los de los sub-documentos que la contienen.
    U-SEG-OFICIAL, S0-5a (solo e0-r2): `intersticial_continuado` (R5-b, ver RE_CODIGO_R5B): las intersticiales que
    continúan la anterior del mismo hueco se emiten en una sola unidad, con el número de la primera, sin renumerar las
    siguientes; `titulo_seccion_envuelto` (R5-c, ver PALABRAS_FUNCIONALES_R5C): el chapeau de un renglón que continúa el
    título de la sección se junta al título (en un renglón aparte del encabezado) y no se emite.
    U-SEG-OFICIAL, S0-6a (solo e0-r2): `encabezado_b` (B, `clase_encabezado_b`): el título de varios renglones va entero en
    la entrada de encabezado (B1, incluye 4b), y el número seguido de un párrafo no fabrica encabezado: el texto va entero
    en la intro (B2, incluye 4a); `rotulo_impreso_d` (D): el encabezado heredado de un nodo con renglón de rótulo es el
    texto impreso de ese renglón, sin normalizarlo («APARTADO C: …», «1.3.8 Código…»)."""
    chunks: list[dict] = []
    sin_titulo = set()                  # regla 4a
    envuelto: dict[int, Linea] = {}     # regla 4b: el renglón que se junta al título
    sin_titulo_b: set = set()                   # B2 de S0-6a: sin encabezado fabricado
    envuelto_b: dict[int, list[Linea]] = {}     # B1 de S0-6a: los renglones que completan el título
    if oracion_titulo_4a or titulo_envuelto_4b:
        def marcar(n: Nodo) -> None:
            c = clase_titulo_4ab(n)
            if c is not None and c[0] == "4a" and oracion_titulo_4a:
                sin_titulo.add(id(n))
            elif c is not None and c[0] == "4b" and titulo_envuelto_4b:
                envuelto[id(n)] = c[1]
            for h in n.hijos:
                marcar(h)
        for s0 in res.secciones:
            marcar(s0)
    envuelto_sec: dict[int, Linea] = {}     # R5-c de S0-5a: el chapeau que continúa el título de la sección
    if titulo_seccion_envuelto:
        def secciones(n: Nodo):     # las de primer nivel y, con A de S0-6a, las que adoptó una división
            yield n
            for h in n.hijos:
                if h.tipo == "seccion":
                    yield from secciones(h)
        for s0 in [x for r in res.secciones for x in secciones(r)]:
            if s0.tipo == "seccion" and s0.hijos:
                intro0 = [it["seg"] for it in _rol_segmentos(s0) if it["rol"] == "intro"]
                if len(intro0) == 1 and len(intro0[0]) == 1 and _continua_titulo_r5c(s0.titulo, intro0[0][0].texto):
                    envuelto_sec[id(s0)] = intro0[0][0]
    if encabezado_b:
        def marcar_b(n: Nodo) -> None:
            # B de S0-6a, salvo donde rige R5-c (sigue como está)
            c = clase_encabezado_b(n) if id(n) not in envuelto_sec else None
            if c is not None:
                sin_titulo.discard(id(n))
                envuelto.pop(id(n), None)
                if c[0] == "b1":
                    envuelto_b[id(n)] = c[1]
                else:
                    sin_titulo_b.add(id(n))
            for h in n.hijos:
                marcar_b(h)
        for s0 in res.secciones:
            marcar_b(s0)
    sd = {d["prefijo"]: d for d in res.subdocumentos}

    def _seg_intro(a: Nodo, rol: str, seg: list[Linea], primero: bool) -> list[Linea]:
        # reglas 4a y 4b de S0-4: el primer segmento de la intro lleva delante el renglón del rótulo (4a) o pierde el
        # renglón que completa el título (4b)
        if primero and rol == "intro" and (id(a) in sin_titulo or id(a) in sin_titulo_b):
            return [a.linea_label] + seg
        if primero and rol == "intro" and (id(a) in envuelto or id(a) in envuelto_sec):
            return seg[1:]
        if primero and rol == "intro" and id(a) in envuelto_b:     # B1 de S0-6a
            return seg[len(envuelto_b[id(a)]):]
        return seg

    def _raiz(n: Nodo) -> Nodo:
        while n.padre is not None:
            n = n.padre
        return n

    def _unidad(n: Nodo) -> str:
        base = n.numero if n.tipo == "punto" else f"S{n.numero}"
        p = _raiz(n).prefijo
        return f"{p}::{base}" if p else base

    def _tramos_subdoc(n: Nodo) -> list[dict]:
        # regla de sub-documento de S0-4: un tramo `encabezado` por cada sub-documento de la cadena del de la unidad
        r = _raiz(n)
        if not r.prefijo:
            return []
        cadena, q = [], r.prefijo
        while q is not None:
            cadena.append(sd[q])
            q = sd[q]["padre"]
        cadena.reverse()
        if n is r and r.numero == "0" and r.sintetica:
            cadena = cadena[:-1]
        # reglas sdl y sdlh de S0-4a-ter: el rótulo de un sub-documento de letra se hereda solo con sdlh
        cadena = [d for d in cadena if d.get("heredable", True)]
        tramos = [{"tipo": "encabezado", "unidad_origen": d["prefijo"], "texto": d["titulo"], "paginas": [d["pagina"]]}
                  for d in cadena]
        if res.rotulos_letra and r.linea_label is not None and not (r.numero == "0" and r.sintetica):
            # regla sdlh sin sdl: la raíz hereda el último rótulo de letra de su contenedor anterior a su rótulo
            pos = (r.linea_label.pagina, r.linea_label.top)
            previos = [b for b in res.rotulos_letra if b["padre"] == r.prefijo and (b["pagina"], b["top"]) < pos]
            if previos:
                b = max(previos, key=lambda x: (x["pagina"], x["top"]))
                tramos.append({"tipo": "encabezado", "unidad_origen": b["prefijo"], "texto": b["titulo"],
                               "paginas": [b["pagina"]]})
        return tramos

    def _texto(lineas: list[Linea]) -> str:
        return "\n".join(l.texto for l in lineas)

    tx = texto_lineas or _texto

    def _rotulo(a: Nodo, normalizado: str) -> str:
        # D de S0-6a: el rótulo tal como está impreso en su renglón
        if rotulo_impreso_d and a.linea_label is not None and not (a.sintetica and a.numero == "0"):
            return a.linea_label.texto.strip()
        return normalizado

    def _titulo_linea(a: Nodo) -> str | None:
        if id(a) in sin_titulo_b:
            return None     # B2 de S0-6a: el número va seguido de un párrafo, no se fabrica encabezado
        extra_b = "".join(f"\n{l.texto}" for l in envuelto_b.get(id(a), []))     # B1 de S0-6a
        if a.sintetica and a.numero == "0" and not a.titulo:
            return None     # J de S0-6a: el preámbulo de la carátula no lleva rótulo fabricado
        if a.sintetica and a.rango_a is not None:
            # A de S0-6a: el rótulo de la división, tal como está impreso (con el renglón que le junta R5-c)
            return a.titulo + (f"\n{envuelto_sec[id(a)].texto}" if id(a) in envuelto_sec else "") + extra_b
        if a.sintetica:
            # raíz del modo sin raíz (B5.8.1): el documento no dice 'Sección';
            # el encabezado reproduce el estilo del label real ('17. BASE…'),
            # la raíz implícita lleva su número solo y el preámbulo su título
            base = a.titulo if a.numero == "0" else _rotulo(a, f"{a.numero}. {a.titulo}".rstrip())
            return base + (f"\n{envuelto_sec[id(a)].texto}" if id(a) in envuelto_sec else "") + extra_b     # R5-c de S0-5a
        if id(a) in sin_titulo:
            return f"{a.numero}."     # regla 4a de S0-4
        if id(a) in envuelto:
            return f"{_rotulo(a, f'{a.numero}. {a.titulo}')}\n{envuelto[id(a)].texto}"     # regla 4b de S0-4
        if id(a) in envuelto_sec:
            return f"Sección {a.numero}. {a.titulo}\n{envuelto_sec[id(a)].texto}"     # R5-c de S0-5a
        return (f"Sección {a.numero}. {a.titulo}" if a.tipo == "seccion"
                else _rotulo(a, f"{a.numero}. {a.titulo}") + extra_b)

    def herencia_de(nodo: Nodo) -> tuple[list[dict], list[dict]]:
        """Cadena de herencia: por cada ancestro (sección → … → padre),
        su título y sus segmentos no-terminales, cada tramo con provenance.
        Devuelve (tramos, bloques recortados); los recortados, solo con
        `tope_herencia`."""
        cadena: list[Nodo] = []
        n = nodo.padre
        while n is not None:
            cadena.append(n)
            n = n.padre
        cadena.reverse()
        tramos: list[dict] = _tramos_subdoc(nodo)
        lados: list[str | None] = [None] * len(tramos)
        for k, a in enumerate(cadena):
            unidad = _unidad(a)
            titulo_a = None if _es_raiz_subdoc(a) else _titulo_linea(a)     # A de S0-6a: el rótulo ya está en la cadena
            if titulo_a is not None:     # B2 de S0-6a: sin encabezado fabricado
                tramos.append({"tipo": "encabezado", "unidad_origen": unidad,
                               "texto": titulo_a, "paginas": [a.pagina]})
                lados.append(None)
            # hijo de `a` en el camino a la unidad: marca la posición de sus intersticiales
            hijo = cadena[k + 1] if k + 1 < len(cadena) else nodo
            marca_hijo = _marca_hijo(hijo)
            primera_intro = True
            solo_titulo = raiz0_solo_titulo_m and _es_raiz_subdoc(a)     # M de S0-6a-bis
            for item in _rol_segmentos(a):
                if item["rol"] == "contenido":
                    continue  # no ocurre: los ancestros tienen hijos
                if solo_titulo:
                    # M de S0-6a-bis: de la raíz 0 de un sub-documento, solo su título (los renglones con forma de
                    # título con que empieza su primer segmento); su índice y sus bloques de cuerpo no se heredan
                    if item["rol"] == "intro" and primera_intro:
                        primera_intro = False
                        tit = []
                        for l in item["seg"]:
                            if not _es_titulo_bloque(l):
                                break
                            tit.append(l)
                        if tit:
                            tramos.append({"tipo": "chapeau_seccion", "unidad_origen": unidad, "texto": tx(tit),
                                           "paginas": _paginas_de(tit)})
                            lados.append("final")
                    continue
                rol = {"intro": "intro", "cierre": "cierre",
                       "intersticial": "intersticial"}[item["rol"]]
                seg = _seg_intro(a, rol, item["seg"], primera_intro)
                if res.recuadro_i:
                    seg = [l for l in seg if id(l) not in res.recuadro_i]     # I de S0-6a: el recuadro no se hereda
                if rol == "intro":
                    primera_intro = False
                if not seg and item["seg"]:
                    continue    # regla 4b de S0-4: la intro era solo el renglón que completa el título
                texto_seg = tx(seg)
                if texto_lineas is not None and not texto_seg:
                    # e0-r2: segmento absorbido entero por el bloque de una
                    # tabla serializada que empieza en un segmento anterior
                    continue
                tramos.append({
                    "tipo": f"{'chapeau_seccion' if a.tipo == 'seccion' else rol}"
                            if a.tipo == "seccion" and rol == "intro"
                            else rol,
                    "unidad_origen": unidad,
                    "texto": texto_seg,
                    "paginas": _paginas_de(seg),
                })
                lados.append("inicio" if rol == "cierre" or (rol == "intersticial" and seg
                                                             and (seg[0].pagina, seg[0].top) > marca_hijo)
                             else "final")
        if tope_herencia is not None:
            return recortar_herencia(tramos, lados, *tope_herencia)
        return tramos, []

    def herencia_titulos(nodo: Nodo) -> list[dict]:
        """Cadena de títulos (tramos `encabezado`) desde la sección hasta el
        propio nodo inclusive: el contexto mínimo de orientación de un
        mini-chunk. Sin bloques de prosa: la prosa de cada ancestro tiene su
        propio mini-chunk responsable."""
        cadena: list[Nodo] = [nodo]
        n = nodo.padre
        while n is not None:
            cadena.append(n)
            n = n.padre
        cadena.reverse()
        return _tramos_subdoc(nodo) + [{"tipo": "encabezado",
                                        "unidad_origen": _unidad(a),
                                        "texto": _titulo_linea(a), "paginas": [a.pagina]}
                                       for a in cadena if _titulo_linea(a) is not None
                                       and not (_es_raiz_subdoc(a) and a is not nodo)]     # B2 y A de S0-6a

    def emitir_mini(nodo: Nodo, rol: str, segs: list[list[Linea]],
                    n_tramo: int | None) -> None:
        """Emite un mini-chunk desde uno o más segmentos contiguos del mismo
        rol de un nodo NO terminal (enmienda 01 §2.a). `n_tramo` numera los
        tramos múltiples de un mismo rol (solo intersticiales); None = único."""
        if texto_lineas is None:
            texto = "\n".join(_texto_segmento(s) for s in segs)
        else:
            texto = texto_lineas([l for s in segs for l in s])
        if not _materializa_bloque(texto):
            return
        unidad = _unidad(nodo)
        mini_id = f"{res.to}::{unidad}::{rol}" + (f"::{n_tramo}" if n_tramo else "")
        lineas = [l for s in segs for l in s]
        herencia = herencia_titulos(nodo)
        texto_herencia = "\n".join(t["texto"] for t in herencia)
        completo = (texto_herencia + "\n" + texto) if texto_herencia else texto
        if lineas_por_chunk is not None:
            lineas_por_chunk.append(lineas)
        chunks.append({
            "id": mini_id,
            "to": res.to,
            "archivo": res.archivo,
            "unidad": unidad,
            "titulo": f"[bloque {rol}] {nodo.titulo}" + (f"\n{envuelto[id(nodo)].texto}" if id(nodo) in envuelto
                                                         else f"\n{envuelto_sec[id(nodo)].texto}"
                                                         if id(nodo) in envuelto_sec else "")
                     + "".join(f"\n{l.texto}" for l in envuelto_b.get(id(nodo), [])),     # B1 de S0-6a
            "tipo": "mini_chunk",
            "rol_bloque": rol,
            "paginas": _paginas_de(lineas),
            "texto": texto,
            "chars_propio": len(texto),
            "chars_completo": len(completo),
            "herencia": herencia,
            "flags": {**_flags_tabla_formula(lineas), **_flags_numeracion(nodo)},
            "sha256_propio": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
            "sha256_completo": hashlib.sha256(completo.encode("utf-8")).hexdigest(),
        })

    def emitir(nodo: Nodo) -> None:
        es_terminal = not nodo.hijos
        if es_terminal:
            lineas: list[Linea] = list(nodo.lineas_previas)
            if nodo.linea_label is not None:
                lineas.append(nodo.linea_label)
            for s in nodo.segmentos:
                lineas.extend(s)
            if nodo.tipo == "seccion":
                unidad = _unidad(nodo)
                if nodo.sintetica and nodo.linea_label is not None:
                    # raíz explícita del modo sin raíz: la línea del label ya
                    # encabeza `lineas` tal como está en el documento — no se
                    # fabrica un encabezado que la duplique
                    texto_propio = tx(lineas)
                else:
                    encabezado = _titulo_linea(nodo)
                    texto_propio = "\n".join(([encabezado] if encabezado is not None else [])     # J de S0-6a
                                             + ([tx(lineas)] if lineas else []))
            else:
                unidad = _unidad(nodo)
                texto_propio = tx(lineas)
            herencia, recortada = herencia_de(nodo)
            texto_herencia = "\n".join(t["texto"] for t in herencia)
            completo = (texto_herencia + "\n" + texto_propio) if texto_herencia else texto_propio
            flags = _flags_tabla_formula(lineas)
            flags.update(_flags_numeracion(nodo))
            if lineas_por_chunk is not None:
                lineas_por_chunk.append(lineas)
            chunk = {
                "id": f"{res.to}::{unidad}",
                "to": res.to,
                "archivo": res.archivo,
                "unidad": unidad,
                "titulo": nodo.titulo,
                "tipo": "seccion_sin_puntos" if nodo.tipo == "seccion" else "punto_terminal",
                "paginas": _paginas_de(lineas) or [nodo.pagina],
                "texto": texto_propio,
                "chars_propio": len(texto_propio),
                "chars_completo": len(completo),
                "herencia": herencia,
                "flags": flags,
                "sha256_propio": hashlib.sha256(texto_propio.encode("utf-8")).hexdigest(),
                "sha256_completo": hashlib.sha256(completo.encode("utf-8")).hexdigest(),
            }
            if recortada:
                chunk["herencia_recortada"] = recortada
            chunks.append(chunk)
        else:
            # Nodo NO terminal: sus bloques estructurales se emiten como
            # mini-chunks (enmienda 01 §2.a) interleaved en orden documental —
            # intro/chapeau antes de los hijos, intersticiales en su hueco,
            # cierre después. La herencia de los hijos no cambia: el bloque
            # sigue viajando además como contexto.
            items = _rol_segmentos(nodo)
            intro_segs = [it["seg"] for it in items if it["rol"] == "intro"]
            cierre_segs = [it["seg"] for it in items if it["rol"] == "cierre"]
            intersticiales = [it["seg"] for it in items if it["rol"] == "intersticial"]
            rol_intro = "chapeau_seccion" if nodo.tipo == "seccion" else "intro"

            # hueco de cada intersticial: después del hijo k (mismas marcas
            # posicionales que _rol_segmentos)
            marcas = [_marca_hijo(h) for h in nodo.hijos]
            por_hueco: dict[int, list[list[Linea]]] = {}
            for s in intersticiales:
                pos = (s[0].pagina, s[0].top)
                k = max(i for i, mp in enumerate(marcas) if mp < pos)
                por_hueco.setdefault(k, []).append(s)
            n_inter = len(intersticiales)
            contador_inter = 0

            if intro_segs:
                primero = _seg_intro(nodo, "intro", intro_segs[0], True)
                # regla 4b de S0-4: si la intro era solo el renglón que completa el título, no queda intro
                intro_segs = ([primero] if primero else []) + intro_segs[1:]
            if intro_segs:
                emitir_mini(nodo, rol_intro, intro_segs, None)
            for k, h in enumerate(nodo.hijos):
                emitir(h)
                grupos: list[tuple[int, list[list[Linea]]]] = []     # (número de la primera, segmentos)
                for s in por_hueco.get(k, []):
                    contador_inter += 1
                    if intersticial_continuado and grupos and _continua_intersticial_r5b(grupos[-1][1], s):
                        grupos[-1][1].append(s)     # R5-b de S0-5a: la unión conserva el número de la primera
                    else:
                        grupos.append((contador_inter, [s]))
                for num_g, segs_g in grupos:
                    emitir_mini(nodo, "intersticial", segs_g,
                                num_g if n_inter > 1 else None)
            if cierre_segs:
                emitir_mini(nodo, "cierre", cierre_segs, None)

    for s in res.secciones:
        emitir(s)
    return chunks


def titulos_mayusculas_repetidos(paginas: list[list[Linea]], roles: list[str],
                                 zona: int = 5) -> set[str]:
    """Versión e0-r2 (U-R2-CODIGO, complemento de R1, K): textos, sin espacios,
    que están en las primeras `zona` líneas de al menos 2 páginas de cuerpo
    del TO. Con este conjunto, `separar_encabezado_pie` descarta una línea de
    la rama de mayúsculas solo si es un encabezado de página que se repite; la
    que no se repite es contenido (encabezados de tabla, códigos con letras) y
    queda. Lo que precede a la última línea «B.C.R.A.» o de sección de la zona
    es encabezado sin consultar este conjunto (decisión sobre el arrastre
    medido fuera de muestra, r2_codigo/rk_fuera_de_muestra.json): un título
    partido distinto en una página ya no deja «B.C.R.A.» ni la sección como
    contenido. Con un TO de una sola página de cuerpo ningún texto se repite."""
    paginas_de: dict[str, set[int]] = {}
    for pi, (lineas, rol) in enumerate(zip(paginas, roles), start=1):
        if rol != ROL_CUERPO:
            continue
        for l in lineas[:zona]:
            t = "".join(l.texto.split())
            if t:
                paginas_de.setdefault(t, set()).add(pi)
    return {t for t, ps in paginas_de.items() if len(ps) >= 2}


def desambiguar_ids(chunks: list[dict]) -> list[dict]:
    """Versión e0-r2 (U-R2-CODIGO, R2 y complemento L; BKL-0037): ids de chunk
    únicos por TO. Regla: entre los chunks con el mismo id, conserva el id el
    de más texto propio (`chars_propio`; empate: el primero en orden
    documental); los demás reciben, en orden documental, el sufijo `::rep<k>`
    (k = 2, 3, …), conservan `unidad` (la procedencia sigue anclada en la
    unidad documental) y guardan el id de E0 en `id_e0_original`. Motivo: en
    las colisiones medidas, la aparición corta es la línea del índice del TO
    leída como cuerpo y la larga es el cuerpo. Modifica los chunks en el lugar
    y devuelve la lista de renombres {id_e0_original, id}. Sin ids repetidos
    no toca nada."""
    grupos: dict[str, list[int]] = {}
    for i, c in enumerate(chunks):
        grupos.setdefault(c["id"], []).append(i)
    renombres: list[dict] = []
    for original, idx in grupos.items():
        if len(idx) < 2:
            continue
        canonico = max(idx, key=lambda i: (chunks[i]["chars_propio"], -i))
        k = 1
        for i in idx:
            if i == canonico:
                continue
            k += 1
            chunks[i]["id"] = f"{original}::rep{k}"
            chunks[i]["id_e0_original"] = original
            renombres.append({"id_e0_original": original, "id": chunks[i]["id"]})
    return renombres


# ------------------------------------------------------------------ cobertura

def verificar_cobertura(res: ResultadoParseo) -> dict:
    """Cero pérdida: toda línea de contenido del cuerpo pertenece a exactamente
    un lugar de la estructura (label de nodo o línea de un segmento).

    Método: se recorre el árbol contando líneas por identidad de objeto; el
    total debe igualar `lineas_contenido` del parseo, y ninguna línea puede
    aparecer dos veces (ids de objeto únicos)."""
    vistos: set[int] = set()
    duplicadas = 0
    total = 0

    def contar(l: Linea):
        nonlocal duplicadas, total
        if id(l) in vistos:
            duplicadas += 1
        vistos.add(id(l))
        total += 1

    def rec(n: Nodo):
        for l in n.lineas_previas:
            contar(l)
        if n.linea_label is not None:
            contar(n.linea_label)
        for s in n.segmentos:
            for l in s:
                contar(l)
        for h in n.hijos:
            rec(h)

    for s in res.secciones:
        rec(s)
    return {
        "lineas_contenido_parseadas": res.lineas_contenido,
        "lineas_en_estructura": total,
        "lineas_duplicadas": duplicadas,
        "lineas_huerfanas": res.lineas_huerfanas,
        "cobertura_exacta": (total == res.lineas_contenido and duplicadas == 0
                             and res.lineas_huerfanas == 0),
    }


# ------------------------------------------------------------- serialización

def serializar_estructura(res: ResultadoParseo) -> dict:
    def ser(n: Nodo) -> dict:
        d = {
            "tipo": n.tipo, "numero": n.numero, "titulo": n.titulo,
            "pagina": n.pagina, "label_x0": n.label_x0, "text_col": n.text_col,
            "segmentos": [
                {"rol": item["rol"], "paginas": _paginas_de(item["seg"]),
                 "chars": len(_texto_segmento(item["seg"])),
                 "texto": _texto_segmento(item["seg"])}
                for item in _rol_segmentos(n)
            ],
            "hijos": [ser(h) for h in n.hijos],
        }
        if n.sintetica:
            d["sintetica"] = True   # clave condicional: los artefactos vigentes
        if n.numero_impreso:        # quedan byte-idénticos (ídem numero_impreso, e0-r2)
            d["numero_impreso"] = n.numero_impreso
        if n.prefijo:               # regla de sub-documento de S0-4; ídem
            d["prefijo"] = n.prefijo
        if n.apartado:              # regla de apartados de S0-4; ídem
            d["apartado"] = True
        if n.rango_a is not None:   # A de S0-6a; ídem
            d["division_a"] = n.rango_a
        if n.lineas_previas:        # regla 9 de S0; ídem
            d["lineas_previas"] = {"paginas": _paginas_de(n.lineas_previas),
                                   "chars": len(_texto_segmento(n.lineas_previas)),
                                   "texto": _texto_segmento(n.lineas_previas)}
        return d
    return {
        **({"modo_lectura": res.modo_lectura}
           if res.modo_lectura != "vigente" else {}),
        "to": res.to, "archivo": res.archivo,
        "paginas_cuerpo": res.paginas_cuerpo,
        "lineas_contenido": res.lineas_contenido,
        "secciones": [ser(s) for s in res.secciones],
        "rechazos_header": res.rechazos_header,
        "saltos_numeracion": res.saltos_numeracion,
        "avisos": res.avisos,
        "accounting": res.accounting,
        "reasignaciones_continuidad": res.reasignaciones_continuidad,
        "correccion_fronteras": res.correccion_fronteras,
        **({"subdocumentos": res.subdocumentos} if res.subdocumentos else {}),
    }


# ---------------------------------------------------------------- censo x.y

def inventario_nivel_mapa(res: ResultadoParseo) -> set[str]:
    """Unidades a la granularidad del mapa oráculo: puntos x.y del cuerpo, más
    'S<n>' para secciones sin puntos."""
    unidades: set[str] = set()
    for s in res.secciones:
        hijos_punto = [h for h in s.hijos if h.tipo == "punto"]
        if not hijos_punto:
            unidades.add(f"S{s.numero}")
        for h in hijos_punto:
            unidades.add(h.numero)
    return unidades
