"""Driver de E0: corre parser + chunker sobre un corpus y escribe la salida.

Uso: python3 correr_e0.py [--salida DIR] [--manifiesto RUTA]

Sin --manifiesto: comportamiento legacy intacto (los 5 TOs del subset vía
E0.TO_KEYS y el mapa de territorio quemado). Con --manifiesto (U-B5.1): los
TOs, las rutas de PDF y el mapa-oráculo salen del manifiesto de corpus; con
`oraculo.mapa_territorio: null` NO se construye censo_oraculo.json (modo sin
oráculo — las etapas aguas abajo lo declaran, ver e2_lib.SIN_ORACULO).

Salida (por defecto ./salida/):
  estructura_<to>.json   árbol estructural del cuerpo (mapa de E0)
  indice_<to>.json       entradas parseadas del índice
  chunks_<to>.json       chunks terminales con herencia, flags y sha256
  divergencias_indice_cuerpo.json
  censo_oraculo.json     reconciliación vs mapa de territorio (inventario x.y)
  conteos.json           conteos agregados por TO
  cobertura.json         verificación de cero pérdida por TO
  correcciones.json      reglas post-parseo: reasignaciones por continuidad de
                         enumeración (regla 1) y fronteras intra-palabra
                         corridas (regla 2), con conteos antes/después
  sub_chunking.json      SOLO si alguna unidad superó el umbral C8 (U-B5.3):
                         particiones por ítems y unidades no particionables
                         declaradas; en el subset de desarrollo no se emite
                         (0 unidades sobre el umbral) y la salida es
                         byte-idéntica a la histórica
  tablas_<to>.json       SOLO con --version-e0 e0-r2 (U-R2-CODIGO): tablas
                         lógicas de e0_tablas y de R-TC2, guarda de recuadro,
                         líneas de E0 asignadas y chunk dueño de cada una
  version_e0.json        SOLO con --version-e0 e0-r2
  ids_desambiguados.json SOLO con --version-e0 e0-r2 y si algún TO trae ids
                         de chunk repetidos (BKL-0037): renombres por TO
  encabezados_conservados.json SOLO con --version-e0 e0-r2 y si la regla K
                         conservó alguna línea en mayúsculas del encabezado
                         de página: página, texto y chunk por TO
Con --version-e0 e0-r2, --salida es obligatoria y no puede ser salida/,
salida_enm01/ ni salida_tanda0/ (M).
"""

from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import re
import statistics
from pathlib import Path

import e0_lib as E0

REPO = Path(__file__).resolve().parents[3]
SUBSET = REPO / "experiment" / "subset"
MAPA = REPO / "experiment" / "exploracion" / "mapa_territorio_quemado_5TOs_5sets.json"


# ------------------------------------------------------------ sub-chunking
# U-B5.3 decisión 6 — partición por ítems de unidades que exceden el umbral
# de tamaño, SOLO relevante para TOs nuevos: el peor terminal del subset de
# desarrollo mide exactamente 26.182 chars (criterio C8 de la banda de
# referencia, escalado_prep/reporte_generalizacion.md §2, mismo valor que
# healthcheck_e0.UMBRAL_CHARS_TERMINAL) y el corte es ESTRICTO (>), así que
# ninguna unidad de desarrollo se toca y la salida dev queda byte-idéntica.
# Medición sobre el corpus de escalado (152 TOs de e0_dry): 6/6.670
# terminales superan el umbral (27.161–126.723 chars), todos de TOs
# "necesita reglas" — 0 en los 68 digeribles. Mecánica: se detectan ítems de
# lista por marcadores al inicio de línea, se agrupan bloques consecutivos
# hasta un objetivo de tamaño y el chapeau (texto previo al primer ítem)
# queda en el texto de la parte 1 y viaja como HERENCIA (tramos encabezado +
# intro, patrón E0) en las partes siguientes. Una unidad sobre el umbral SIN
# ítems detectables NO se particiona y queda declarada en sub_chunking.json
# (nunca en silencio).
UMBRAL_CHARS_SUBCHUNK = 26182            # == C8; > estricto preserva dev
OBJETIVO_CHARS_PARTE = UMBRAL_CHARS_SUBCHUNK // 2   # 13.091
MIN_ITEMS_SUBCHUNK = 3
# e0-r2, U-R2-CODIGO-2 (C2): tope de la herencia (punto h; diseño aprobado en
# data/experiment/r2_codigo2/freno_c2_diseno.md): U = el tamaño objetivo de una
# parte, B = 2.000 caracteres por bloque heredado.
TOPE_HERENCIA_E0_R2 = (OBJETIVO_CHARS_PARTE, 2000)
# e0-r2, U-R2-CODIGO-2 (C2, punto f): encabezados de punto que se abren con el
# número corregido, por (TO, página, número impreso). La p. 16 de ric imprime
# 4.3, 4.3.1 y 4.3.2 el bloque que la norma numera 4.4 (las citas a 4.4.1 y
# 4.4.2 y los encabezados 4.4.3 y 4.4.4 de la p. 18); sin la lista, E0 los
# rechaza como duplicados y deja las pp. 16 a 18 dentro de ric::4.3.3.
RENUMERACIONES_E0_R2 = {("ric", 16, "4.3"): "4.4", ("ric", 16, "4.3.1"): "4.4.1",
                        ("ric", 16, "4.3.2"): "4.4.2"}
# e0-r2, U-R2-CODIGO-2 (C2, punto l): páginas, por TO, donde la cola envuelta
# del título de sección se acepta solo si continúa el título (e0_lib,
# `continua_titulo`). Son las cuatro páginas de ric donde la regla histórica
# descartaba seis renglones de la norma (pp. 15, 30, 54 y 59). Una lista y no
# la regla en toda página: en la partición de 152 TOs la regla general mueve
# ids (snp_cheq) y deja sin serializar una tabla (fabcra).
COLA_TITULO_ESTRICTA_E0_R2 = {"ric": frozenset({15, 30, 54, 59})}
# U-SEG-OFICIAL, S0-2 (mandato firmado en e543cb2 y notas al pie; diseño en data/experiment/
# segmentacion_oficial_e0r2/s0_1/ y s0_1bis/): reglas de E0 que cambian ids de la partición. Corren solo en
# e0-r2; la versión legada no las conoce. Regla 1, sección escrita de otra forma; 2, rótulos de punto que no lo
# son; 3, continuación de índice solo con secciones con título, y página de cuerpo que es entera una lista de la
# regla 8; 4, marcador de letra y número (ri_spi); 5, cola de título en una lista de páginas; 6, unidades grandes
# (partición por renglones); 7, reapertura del padre cerrado por re-anclaje, con el acompañamiento T (una tabla
# partida en intersticiales de un mismo hueco se funde); 8, lista de puntos leída como cuerpo; 9, filas de un
# catálogo en tabla.
MIN_APARTADOS_R4 = 2
# regla 5 de S0: la lista de páginas de la cola de título estricta se amplía a las páginas donde la regla general
# recupera texto corrido de la norma sin mover ids ni dañar una tabla (medición de C2 de U-R2-CODIGO-2, `c2_e0.json`,
# `particion_152_cola_en_toda_pagina`, y de S0-1). Quedan fuera fabcra (pp. 10, 11 y 13: celdas de su tabla002,
# que dejaría de serializarse) y las pp. 89 a 93 de snp_cheq (encabezado de una tabla; mueve los ids de 7.1).
COLA_TITULO_ESTRICTA_R5 = {"cirmo3": frozenset({19}), "cryl": frozenset({27}), "manori": frozenset({6}),
                           "ri2_ci": frozenset({8, 9, 16, 24}), "snp_cheq": frozenset({80}),
                           "snp_mep": frozenset({19})}

# U-SEG-OFICIAL, S0-3 (tras la lectura de cortes de S1; diseño en data/experiment/segmentacion_oficial_e0r2/s0_3/):
# mecanismos de E0, solo en e0-r2. 1, cuerpo de punto que quedaba como intersticial del padre (formas a y b); 2,
# numeración o título no leído en la línea que abre una raíz del modo sin raíz (formas a, b y c); 3, cuarta forma de la
# regla 8 (lista de rótulos de un nivel); 5, zona de encabezado (formas a, b y c). El mecanismo 4 de S0-3 no está:
# lo reemplazan las reglas 4a y 4b de S0-4.
REGLAS_S0_3 = frozenset({"m1a", "m1b", "m2a", "m2b", "m2c", "m3", "m5a", "m5b", "m5c"})

# U-SEG-OFICIAL, S0-4 (diseño en data/experiment/segmentacion_oficial_e0r2/s0_4/): reglas de E0, solo en e0-r2. «sd»,
# sub-documento (`E0.limites_subdocumento`), solo en los TOs de TOS_SUBDOCUMENTO_S0_4 (lista explícita; ri_tsa y ri2_pm
# quedan fuera hasta una lectura propia); «sdg3», dentro de un sub-documento la guarda de columna (G3) no rechaza la
# raíz que sucede exactamente a la anterior; «sdmax» (S0-4a-bis), dentro de un sub-documento la raíz mayor que MAX_RAIZ
# que sucede exactamente a la anterior no se rechaza; «4a», oración tomada como título, y «4b», título envuelto
# (`E0.clase_titulo_4ab`), que no corren en los diez TOs de la tanda 0 (TOS_TANDA0_SIN_4AB: sus títulos partidos y sus
# oraciones tomadas como título quedan como límite declarado de la tanda 0, cuya E0 no cambia); «ap», apartados de una
# sección sin puntos, solo en los TOs de TOS_APARTADOS_S0_4. La regla «sd» no cambia el modo de lectura de un TO: la
# escalera elige la etapa sin ella y vuelve a leer esa etapa con los sub-documentos. S0-4a-ter: «sdr1», el régimen de la
# página 1 es el del TO y no abre sub-documento (TOS_SUBDOCUMENTO_R1_S0_4, que se leen con sub-documento); «apl»,
# apartados de letra «APARTADO X: …» con sus rótulos «X.n.» (el marcador de la regla 4 de S0) en la lectura sin raíz de
# los TOs de TOS_APARTADO_LETRA_S0_4, sin cambiar la etapa; y, en los de TOS_LETRA_S0_4, «sdl», sub-documento de letra
# («A. TÍTULO», «B. TÍTULO»…), «sdlh», herencia de su rótulo, y «sdla», el rótulo «X.n.» con la letra vigente.
REGLAS_S0_4 = frozenset({"sd", "sdg3", "sdmax", "sdr1", "apl", "sdl", "sdlh", "sdla", "4a", "4b", "ap"})
TOS_SUBDOCUMENTO_S0_4 = frozenset({"ri_sef", "nmcief", "ri_ccna", "ri_icpipsp", "ri_cc"})
TOS_SUBDOCUMENTO_R1_S0_4 = frozenset({"ri_oc"})
TOS_APARTADO_LETRA_S0_4 = frozenset({"ri_oc"})
TOS_LETRA_S0_4 = frozenset({"ri_ccna"})
TOS_APARTADOS_S0_4 = frozenset({"ri_ai"})
TOS_TANDA0_SIN_4AB = frozenset({"cap", "cla", "ext", "pro", "ric", "ctacte", "lingob", "polcre", "pagjub", "docvig"})

# U-SEG-OFICIAL, S0-5a (diseño en data/experiment/segmentacion_oficial_e0r2/s0_5/): reglas de corte de E0, solo en e0-r2 y
# fuera de los diez TOs de la tanda 0 (TOS_TANDA0_SIN_S0_5: su E0 no cambia; lo que las reglas cambiarían ahí queda como
# límite declarado de la tanda 0). «r5a», cierre al margen del último ítem de una lista del detector del hallazgo 1.16
# (`E0.aplicar_cierre_al_margen`); «r5a2», título de bloque después del último ítem, solo en TOS_TITULO_BLOQUE_S0_5;
# «r5b», intersticiales que continúan la anterior, solo en TOS_INTERSTICIAL_S0_5; «r5c», título de sección de dos
# renglones; «r5d», número de punto que continúa una remisión del renglón anterior; «r5e», rótulo vertical, solo en
# TOS_ROTULO_VERTICAL_S0_5.
# S0-5a-bis (diseño en data/experiment/segmentacion_oficial_e0r2/s0_5/bis/): «r5a» pasa a ser por lista, solo en las
# listas de LISTAS_R5A_S0_5 (las 43 de la lista v2 de la revisión de S0-5a: 41 con los párrafos de S0-5a y 3 con un
# rango de renglones), y no mueve renglones de las tablas que se serializan (`_excluir_tablas_r5a`); «r5f», rótulos de
# punto por lista (los saltos de la tanda 1 que el control de continuidad lista), solo en ROTULOS_POR_LISTA_S0_5; «r5g»,
# raíz por lista sin la guarda de columna G3, solo en RAICES_POR_LISTA_S0_5.
REGLAS_S0_5 = frozenset({"r5a", "r5a2", "r5b", "r5c", "r5d", "r5e", "r5f", "r5g"})
TOS_TITULO_BLOQUE_S0_5 = frozenset({"ri_oc"})
TOS_INTERSTICIAL_S0_5 = frozenset({"snp_dd", "snp_cheq"})
TOS_ROTULO_VERTICAL_S0_5 = frozenset({"ri_ccna"})
TOS_TANDA0_SIN_S0_5 = frozenset({"cap", "cla", "ext", "pro", "ric", "ctacte", "lingob", "polcre", "pagjub", "docvig"})
# R5-a por lista (S0-5a-bis): por TO, la clave del último ítem de cada lista y None (párrafos al margen, como en S0-5a) o
# un rango de renglones (página, top, comienzo del texto): en ri_rml 1.4.2 el cierre de 1.4 empieza en «Para el punto
# 1.4.1.» (p. 11), un párrafo antes del que mueve el criterio de S0-5a; en ri_spi C.1.3 y ri2_ae 14.3 solo los renglones
# del cierre (pp. 9, y 28 a 29), sin los anexos que siguen.
LISTAS_R5A_S0_5 = {
    "adfsp": {"1.1.10": None, "1.2.2.2": None, "2.6.3.2": None},
    "apnf": {"1.3.1.2": None},
    "cajasc": {"11.4.4": None, "4.2.2.3": None},
    "cedin": {"7.1.3.2": None},
    "consyr": {"3.4.4": None},
    "cryl": {"4.2.2": None},
    "ctacor": {"1.3.2": None},
    "ctavis": {"8.2.1.4": None},
    "depaho": {"3.11.5.5": None},
    "depinv": {"1.7.2.2": None, "1.9.2": None},
    "efemin": {"2.3.2": None},
    "evacre": {"2.1.2": None},
    "fimipyme": {"4.3.3": None, "5.1.2": None},
    "finsec": {"5.1.2": None, "5.2.5": None},
    "garant": {"1.2.8.2": None, "1.2.9.4": None},
    "gracre": {"6.7.2": None},
    "manori": {"1.1.6.5": None, "1.4.1.3": None, "3.4.1.3": None},
    "ratio": {"5.2.1.5": None},
    "ri2_ae": {"14.3": ("rango", (28, 664.2, 'La fecha de la manifestación escrita deb'), (29, 126.0, 'publicación.'))},
    "ri2_pm": {"1.6": None},
    "ri_oc": {"B.1.28": None, "B.2.4": None, "B.3.4": None},
    "ri_rml": {"1.4.2": ("rango", (11, 409.0, 'Para el punto 1.4.1.'), (11, 698.8, 'los códigos 651000/M-TP, 661000/M-TP y 671000/M-TP.'))},
    "ri_spi": {"C.1.3": ("rango", (9, 284.8, 'Además de los datos detallados precedent'), (9, 471.0, 'los datos reflejados en el formulario.'))},
    "seguef": {"2.1.6.2": None, "2.9.2": None},
    "snp_cec": {"9.1.3.3": None},
    "snp_mep": {"3.1.1.2": None, "3.1.2.2": None, "4.6.2": None},
    "snp_psp": {"1.3.2.2": None},
    "snp_tr_nc": {"5.2.3.2": None},
    "tasint": {"3.3.2": None},
}
# R5-f (S0-5a-bis): (página, top, número, padre o None) de cada rótulo que abre su punto. En ri_ccna, los rótulos pegados
# a su texto de D1A1 (2.1.1 a 2.1.8, pp. 3 y 4; 5.1, p. 6; 8.1, p. 8) y de D1A2 (5.1, p. 10); en snp_cheq, 3.3.6.2 (p.
# 38), colgado de 3.3 porque el PDF salta 3.3.6 y 3.3.6.1.
ROTULOS_POR_LISTA_S0_5 = {
    "ri_ccna": ((3, 401.8, "2.1.1", None), (3, 441.7, "2.1.2", None), (3, 481.6, "2.1.3", None),
                (3, 521.5, "2.1.4", None), (3, 574.2, "2.1.5", None), (3, 614.2, "2.1.6", None),
                (3, 704.6, "2.1.7", None), (4, 119.4, "2.1.8", None), (6, 506.3, "5.1", None),
                (8, 601.2, "8.1", None), (10, 496.9, "5.1", None)),
    "snp_cheq": ((38, 218.2, "3.3.6.2", "3.3"),),
}
# R5-g (S0-5a-bis): (página, top, número de la raíz) de cada título de raíz que abre sin la guarda de columna G3. En ri_oc,
# «3. Aclaraciones» (p. 6, x0 85,0): la p. 6 es de otra versión de la norma que la p. 5, con otro margen, y la guarda lo
# rechazaba por estar más adentro que la columna de las raíces (76,6).
RAICES_POR_LISTA_S0_5 = {"ri_oc": ((6, 117.4, "3"),)}

# U-SEG-OFICIAL, S0-6a (diseño en data/experiment/segmentacion_oficial_e0r2/s0_6/): reglas generales de E0, solo en e0-r2 y
# fuera de los diez TOs de la tanda 0 (TOS_TANDA0_SIN_S0_6: su E0 no cambia; es el único lugar donde estas reglas nombran
# documentos). «a», títulos sin número (división por rótulo de anexo o apartado, por cambio de la banda de encabezado o por
# un título que encabeza solo su bloque); «b», encabezado de un punto con hijos; «c», párrafo sin número asignado por su
# columna; «d», rótulo heredado tal como está impreso; «e», número que E0 rechazaba por la columna; «f», encabezado de
# columnas de una tabla; «g», número partido por el extractor; «h», número sin espacio; «i», recuadro de encabezado de dos
# columnas; «j», carátula; «k», pie de formulario. Reemplazos de reglas por lista: «c» reemplaza a R5-a por lista, «a» a
# R5-a′, «e» a R5-g y «h» a R5-f en ri_ccna (`_r5`).
# S0-6a-bis (diseño en data/experiment/segmentacion_oficial_e0r2/s0_6/bis/): «l», un índice leído como cuerpo no corta la
# sucesión de números (`E0.lineas_de_indice_l`); «m», la raíz 0 de un sub-documento que abre A aporta a la herencia solo
# su título. Con «c», R5-a sigue por lista solo en LISTAS_R5A_S0_6, y C no toca esas listas.
REGLAS_S0_6 = frozenset({"a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m"})
TOS_TANDA0_SIN_S0_6 = frozenset({"cap", "cla", "ext", "pro", "ric", "ctacte", "lingob", "polcre", "pagjub", "docvig"})
REEMPLAZOS_S0_6 = {"r5a": ("c", None), "r5a2": ("a", None), "r5g": ("e", None), "r5f": ("h", frozenset({"ri_ccna"}))}
# R5-a por lista que queda con C (S0-6a-bis, decisión 3): las listas de LISTAS_R5A_S0_5 donde C no coincide con la
# página (comparadas con el criterio de S1-ter) y la de ri_oc B.1.28 (E2-098), tomadas de LISTAS_R5A_S0_5: seis de las
# trece donde C daba otra cosa en S0-6a (en adfsp, la que no es de las leídas; las tres de ri_oc; las de ri_rml y ri_spi)
# y dos donde C coincidía en S0-6a y C ajustada deja de coincidir (snp_mep 4.6.2 y tasint 3.3.2).
LISTAS_R5A_S0_6 = {
    "adfsp": {k: v for k, v in LISTAS_R5A_S0_5["adfsp"].items() if k not in ("1.2.2.2", "2.6.3.2")},
    "ri_oc": dict(LISTAS_R5A_S0_5["ri_oc"]),
    "ri_rml": dict(LISTAS_R5A_S0_5["ri_rml"]),
    "ri_spi": dict(LISTAS_R5A_S0_5["ri_spi"]),
    "snp_mep": {k: v for k, v in LISTAS_R5A_S0_5["snp_mep"].items() if k == "4.6.2"},
    "tasint": dict(LISTAS_R5A_S0_5["tasint"]),
}


def _r6(regla: str, to: str) -> bool:
    """Una regla de S0-6a corre en `to` (fuera de la tanda 0)."""
    return regla in REGLAS_S0_6 and to not in TOS_TANDA0_SIN_S0_6


def _sd_s04(to: str) -> bool:
    """La regla de sub-documento de S0-4 corre en `to` (los sub-documentos no los abre A)."""
    return ("sd" in REGLAS_S0_4 and to in TOS_SUBDOCUMENTO_S0_4) or \
        ("sdr1" in REGLAS_S0_4 and to in TOS_SUBDOCUMENTO_R1_S0_4)


def _r5(regla: str, to: str, lista: frozenset | None = None) -> bool:
    """Una regla de S0-5a corre en `to` (fuera de la tanda 0 y, si tiene lista, dentro de ella), salvo que la reemplace una
    regla general de S0-6a que corre en `to` (REEMPLAZOS_S0_6)."""
    reemplazo = REEMPLAZOS_S0_6.get(regla)
    if reemplazo is not None and _r6(reemplazo[0], to) and (reemplazo[1] is None or to in reemplazo[1]):
        return False
    return regla in REGLAS_S0_5 and to not in TOS_TANDA0_SIN_S0_5 and (lista is None or to in lista)


def _formas_s0_3(mecanismo: str) -> frozenset:
    return frozenset(r[len(mecanismo):] for r in REGLAS_S0_3 if r.startswith(mecanismo) and len(r) > len(mecanismo))


# familias de marcador de ítem, por precedencia de matcheo por línea
FAMILIAS_ITEM = [
    ("num", re.compile(r"^\d+(?:\.\d+)*\.(?:\s|$)")),      # "2.", "1.5.1. …"
    ("inciso", re.compile(r"^[a-zñ]\)(?:\s|$)")),          # "a) …"
    ("romano", re.compile(r"^[ivxlcdm]{2,}\)(?:\s|$)")),   # "ii) …"
    ("guion", re.compile(r"^[-–—•]\s")),                   # "— …"
]


RE_INICIO_BLOQUE_TABLA = re.compile(r"^\[TABLA ")
RE_FIN_BLOQUE_TABLA = re.compile(r"^\[FIN TABLA ")
# U-SEG-OFICIAL, S0, regla 6 (solo e0-r2 y la partición por corte del perfil r2): partición por
# renglones cuando la unidad no tiene ítems detectables, y para un ítem solo más grande que el
# objetivo. Corta después de un renglón que termina en punto, dos puntos o punto y coma; si en la
# ventana no hay ninguno, en el último renglón que entra; nunca dentro de un bloque [TABLA … FIN
# TABLA] (un bloque mayor que el objetivo queda en una parte propia).
RE_FIN_ORACION_R6 = re.compile(r"[.:;]\s*$")


def _piezas_renglones(lineas: list[str]) -> list[list[str]]:
    piezas, tabla = [], None
    for l in lineas:
        if tabla is not None:
            tabla.append(l)
            if RE_FIN_BLOQUE_TABLA.match(l):
                piezas.append(tabla)
                tabla = None
        elif RE_INICIO_BLOQUE_TABLA.match(l):
            tabla = [l]
        else:
            piezas.append([l])
    if tabla is not None:
        piezas.append(tabla)
    return piezas


def partir_por_renglones(lineas: list[str], objetivo: int) -> list[str]:
    """Grupos de renglones de a lo sumo `objetivo` caracteres (ver el comentario de RE_FIN_ORACION_R6)."""
    piezas = _piezas_renglones(lineas)
    tam = [len("\n".join(p)) + 1 for p in piezas]
    corte_ok = [len(p) > 1 or bool(RE_FIN_ORACION_R6.search(p[-1])) for p in piezas]
    grupos, i = [], 0
    while i < len(piezas):
        j, acum, ultimo_ok = i, 0, None
        while j < len(piezas) and (j == i or acum + tam[j] <= objetivo):
            acum += tam[j]
            if corte_ok[j]:
                ultimo_ok = j
            j += 1
        fin = j if j >= len(piezas) or ultimo_ok is None else ultimo_ok + 1
        grupos.append("\n".join(l for p in piezas[i:fin] for l in p))
        i = fin
    return grupos


def _lineas_en_bloque_tabla(lineas: list[str]) -> set[int]:
    """Índices de las líneas dentro de un bloque [TABLA … FIN TABLA] de e0-r2,
    incluidas las dos líneas de marca."""
    dentro, abierto = set(), False
    for i, l in enumerate(lineas):
        if RE_INICIO_BLOQUE_TABLA.match(l):
            abierto = True
        if abierto:
            dentro.add(i)
        if RE_FIN_BLOQUE_TABLA.match(l):
            abierto = False
    return dentro


def _particionar_texto(texto: str, respetar_tablas: bool = False,
                       renglones: int | None = None, umbral_renglones: int | None = None) -> dict | None:
    """Partición por ítems del texto propio de una unidad. La línea 0 (label/
    título) nunca es marcador. Devuelve chapeau + grupos (cada uno ≤ objetivo
    salvo bloque único mayor) o None si no hay familia con MIN_ITEMS líneas.
    Invariante: chapeau + grupos reconstruyen el texto línea a línea (cero
    pérdida, mismo principio que verificar_cobertura).

    `respetar_tablas` (solo la partición por corte del perfil r2, U-R2-CODIGO
    R4.b): una línea dentro de un bloque [TABLA … FIN TABLA] nunca es marcador
    de ítem, así que ningún límite de parte cae dentro de un bloque.

    `renglones` (regla 6 de S0): objetivo de las partes de la partición por renglones; `umbral_renglones`, el tamaño
    desde el que un ítem o el chapeau se parten por renglones (por omisión, el objetivo de las partes; la partición
    por corte de E1 pasa la capacidad del tercer escalón, para partir solo lo que hoy no tiene salida)."""
    lineas = texto.split("\n")
    umbral_r = umbral_renglones if umbral_renglones is not None else OBJETIVO_CHARS_PARTE
    en_tabla = _lineas_en_bloque_tabla(lineas) if respetar_tablas else set()
    conteo: dict[str, list[int]] = {f: [] for f, _ in FAMILIAS_ITEM}
    for i, l in enumerate(lineas[1:], start=1):
        if i in en_tabla:
            continue
        s = l.strip()
        for fam, pat in FAMILIAS_ITEM:
            if pat.match(s):
                conteo[fam].append(i)
                break
    familia = max(conteo, key=lambda f: len(conteo[f]))
    indices = conteo[familia]
    if len(indices) < MIN_ITEMS_SUBCHUNK:
        if renglones is None or len(lineas) < 2:
            return None
        # regla 6 de S0: sin ítems, partición por renglones; el primer renglón (rótulo o título) es
        # el chapeau
        grupos = partir_por_renglones(lineas[1:], renglones)
        if len(grupos) < 2:
            return None
        return {"chapeau": lineas[0], "grupos": grupos, "familia": "renglones", "n_items": 0}
    chapeau = "\n".join(lineas[:indices[0]])
    bloques = ["\n".join(lineas[i0:(indices[j + 1] if j + 1 < len(indices)
                                    else len(lineas))])
               for j, i0 in enumerate(indices)]
    grupos: list[str] = []
    actual: list[str] = []
    tam = 0
    if renglones is not None and len(chapeau) + 1 > umbral_r and indices[0] > 1:
        # regla 6 de S0: un chapeau mayor que el objetivo se parte por renglones; queda como chapeau
        # su primer renglón (rótulo o título)
        grupos.extend(partir_por_renglones(lineas[1:indices[0]], renglones))
        chapeau = lineas[0]
    for b in bloques:
        if renglones is not None and len(b) + 1 > umbral_r:
            # regla 6 de S0: un ítem solo más grande que el objetivo se parte por renglones
            if actual:
                grupos.append("\n".join(actual))
                actual, tam = [], 0
            grupos.extend(partir_por_renglones(b.split("\n"), renglones))
            continue
        if actual and tam + len(b) + 1 > OBJETIVO_CHARS_PARTE:
            grupos.append("\n".join(actual))
            actual, tam = [], 0
        actual.append(b)
        tam += len(b) + 1
    if actual:
        grupos.append("\n".join(actual))
    if renglones is not None and grupos and indices[0] > 1 and chapeau != lineas[0] \
            and len(chapeau) + 1 + len(grupos[0]) + 1 > umbral_r:
        # regla 6 de S0: el chapeau entra solo, pero con el primer grupo pasa el objetivo (la parte 1 lleva los
        # dos); su cuerpo va en partes propias y queda como chapeau su primer renglón
        grupos = partir_por_renglones(lineas[1:indices[0]], renglones) + grupos
        chapeau = lineas[0]
    if len(grupos) < 2 and renglones is not None and len(lineas) > 1:
        # regla 6 de S0: los ítems no alcanzan para partir; se parte por renglones
        grupos = partir_por_renglones(lineas[1:], renglones)
        if len(grupos) >= 2:
            return {"chapeau": lineas[0], "grupos": grupos, "familia": "renglones", "n_items": 0}
    if len(grupos) < 2:
        return None  # partir en 1 no remedia nada: se declara, no se parte
    return {"chapeau": chapeau, "grupos": grupos, "familia": familia,
            "n_items": len(indices)}


def _sub_chunks_de(c: dict, part: dict, tope_herencia: tuple[int, int] | None = None) -> list[dict]:
    """Materializa las partes de una unidad particionada. La parte 1 lleva el
    chapeau en su TEXTO (es la unidad responsable de su contenido normativo);
    las partes 2..n lo reciben como herencia (tramos `encabezado` + `intro`
    con unidad_origen = la unidad, patrón E0: el contexto ancla, la unidad
    extrae). `unidad` no cambia: la provenance de los elementos extraídos
    sigue anclando en la unidad documental real. Flags y páginas se heredan
    de la unidad completa (conservador, declarado).

    `tope_herencia` (e0-r2 y partición por corte del perfil r2;
    U-R2-CODIGO-2, C2, punto h): las partes reciben el recorte de la unidad
    (su herencia y `herencia_recortada`) y, si con el chapeau la herencia
    pasa U, se recortan los bloques que no estaban recortados; el lado de un
    intersticial sale de sus páginas (`E0.lados_por_pagina`)."""
    chapeau, grupos = part["chapeau"], part["grupos"]
    lineas_chapeau = chapeau.split("\n")
    tramos_chapeau = [{"tipo": "encabezado", "unidad_origen": c["unidad"],
                       "texto": lineas_chapeau[0], "paginas": list(c["paginas"])}]
    resto = "\n".join(lineas_chapeau[1:])
    if resto.strip():
        tramos_chapeau.append({"tipo": "intro", "unidad_origen": c["unidad"],
                               "texto": resto, "paginas": list(c["paginas"])})
    n = len(grupos)
    out = []
    for k, g in enumerate(grupos, start=1):
        texto = (chapeau + "\n" + g) if k == 1 else g
        herencia = copy.deepcopy(c["herencia"])
        recortada = copy.deepcopy(c.get("herencia_recortada") or [])
        if k > 1:
            herencia += copy.deepcopy(tramos_chapeau)
        if tope_herencia is not None:
            ya = frozenset((b["unidad_origen"], b["rol"], b["conservado"]) for b in recortada)
            herencia, nuevos = E0.recortar_herencia(herencia, E0.lados_por_pagina(herencia, c["paginas"]),
                                                    *tope_herencia, saltar=ya)
            recortada += nuevos
        texto_herencia = "\n".join(t["texto"] for t in herencia)
        completo = (texto_herencia + "\n" + texto) if texto_herencia else texto
        parte = {
            "id": f"{c['id']}::parte{k}",
            "to": c["to"],
            "archivo": c["archivo"],
            "unidad": c["unidad"],
            "titulo": f"{c['titulo']} (parte {k}/{n})",
            "tipo": c["tipo"],
            **({"rol_bloque": c["rol_bloque"]} if "rol_bloque" in c else {}),
            "paginas": list(c["paginas"]),
            "texto": texto,
            "chars_propio": len(texto),
            "chars_completo": len(completo),
            "herencia": herencia,
            "flags": copy.deepcopy(c["flags"]),
            "sub_chunk": {"parte": k, "de": n,
                          "id_unidad_completa": c["id"],
                          "chars_unidad_completa": c["chars_propio"],
                          "familia_items": part["familia"]},
            "sha256_propio": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
            "sha256_completo": hashlib.sha256(completo.encode("utf-8")).hexdigest(),
        }
        if recortada:
            parte["herencia_recortada"] = recortada
        out.append(parte)
    return out


# Regla 6 de S0 en E1 (S0-1 bis; nota del 05/10/2026 al pie del mandato de U-SEG-OFICIAL, d59921f): la partición
# por corte de las unidades de la tanda 0 no cambia, y la partición por renglones entra solo donde hoy no hay salida
# porque el tercer escalón del reintento por corte (cliente_e1, techo MAX_TOKENS_ESCALON_3_R2 = 40.960) no alcanza:
# en una unidad sin ítems que pasa su capacidad, o en el ítem (o el chapeau) que deja una parte por ítems sobre esa
# capacidad; las demás partes quedan como en la partición por ítems. La capacidad usa la salida por carácter de
# texto propio medida en T2 de U-REEXT-T0: el p90 de las 39 unidades de 3.000 caracteres o más, 1,5051
# (data/experiment/reext_t0/freno_t2.md:12; decisión de la autora del 06/10/2026, en la nota al pie del mandato de
# U-REEXT-T0, docs/mandatos/UREEXT_T0_reextraccion_tanda0.md:485-487). Con esa razón salen la capacidad del tercer
# escalón y el objetivo de las partes por renglones, en E0 y en E1; el objetivo de la partición por ítems
# (OBJETIVO_CHARS_PARTE, 13.091) no cambia.
MAX_TOKENS_ESCALON_3_R6 = 40960
RAZON_TOKENS_POR_CARACTER_R6 = 1.5051
CAPACIDAD_ESCALON_3_R6 = 27214           # 40.960 / 1,5051 = 27.214,1
OBJETIVO_PARTES_RENGLONES_R6 = 10886     # 16.384 / 1,5051 = 10.885,65


def particionar_por_corte(c: dict) -> tuple[list[dict] | None, dict]:
    """Partición de una unidad cuya extracción cortó por max_tokens también en
    el reintento (perfil r2, U-R2-CODIGO R4.b; BKL-0030, laudo de r2 §1.1 (b)):
    la mecánica de sub-chunking de E0 (`_particionar_texto` y `_sub_chunks_de`),
    disparada por el corte y no por el tamaño, sin cortar ningún bloque
    [TABLA … FIN TABLA] (agregado 7 de las decisiones sobre el freno R3). Las
    partes (`<id>::parteK`) conservan la unidad: la procedencia de lo extraído
    sigue en la unidad documental. Devuelve (partes, informe); partes es None
    si la unidad no tiene ítems para partir o si alguna parte quedara con un
    bloque de tabla abierto o cerrado a medias (se declara, nunca en
    silencio)."""
    info = {"id": c["id"], "chars_propio": c["chars_propio"],
            "bloques_tabla": sum(1 for l in c["texto"].split("\n") if RE_INICIO_BLOQUE_TABLA.match(l))}
    # regla 6 de S0 en E1: la partición por ítems es la de siempre; la partición por renglones rige solo donde
    # hoy no hay salida y el tercer escalón no alcanza (ver CAPACIDAD_ESCALON_3_R6)
    cap3 = CAPACIDAD_ESCALON_3_R6
    part = _particionar_texto(c["texto"], respetar_tablas=True)
    if part is None:
        if not ("sub_chunk" not in c and c["chars_propio"] > cap3):
            return None, {**info, "motivo": "sin_items_detectables"}
        part = _particionar_texto(c["texto"], respetar_tablas=True, renglones=OBJETIVO_PARTES_RENGLONES_R6)
        if part is None:
            return None, {**info, "motivo": "sin_items_detectables"}
        info["renglones_r6"] = "sin_items_y_sobre_el_tercer_escalon"
    subs = _sub_chunks_de(c, part, TOPE_HERENCIA_E0_R2)
    if "renglones_r6" not in info and any(s["chars_propio"] > cap3 for s in subs):
        # solo se parten por renglones los ítems (o el chapeau) que pasan el tercer escalón; las demás partes
        # quedan como en la partición por ítems
        part2 = _particionar_texto(c["texto"], respetar_tablas=True, renglones=OBJETIVO_PARTES_RENGLONES_R6,
                                   umbral_renglones=cap3)
        if part2 is not None:
            part, subs = part2, _sub_chunks_de(c, part2, TOPE_HERENCIA_E0_R2)
            info["renglones_r6"] = "parte_sobre_el_tercer_escalon"
    for s in subs:
        ls = s["texto"].split("\n")
        if sum(1 for l in ls if RE_INICIO_BLOQUE_TABLA.match(l)) != sum(1 for l in ls if RE_FIN_BLOQUE_TABLA.match(l)):
            return None, {**info, "motivo": "bloque_de_tabla_partido", "parte": s["id"]}
    return subs, {**info, "familia_items": part["familia"], "n_items": part["n_items"],
                  "partes": [{"id": s["id"], "chars_propio": s["chars_propio"]} for s in subs]}


def subdividir_unidades_grandes(chunks: list[dict],
                                umbral: int = UMBRAL_CHARS_SUBCHUNK,
                                no_partir: frozenset = frozenset(),
                                tope_herencia: tuple[int, int] | None = None) -> tuple[list[dict], dict]:
    """Aplica la partición a los chunks terminales cuyo texto propio EXCEDE el
    umbral (estricto). Los demás pasan tal cual (mismos objetos: con 0
    unidades sobre el umbral la salida serializada es byte-idéntica).
    Devuelve (chunks, reporte) con particiones y no-particionables."""
    out: list[dict] = []
    particiones: list[dict] = []
    no_particionables: list[dict] = []
    r6 = tope_herencia is not None     # e0-r2: regla 6 de S0
    for c in chunks:
        if (c.get("tipo") == "mini_chunk" and not r6) or c["chars_propio"] <= umbral:
            # regla 6 (a) de S0: en e0-r2 un mini-chunk sobre el umbral ya no se saltea
            out.append(c)
            continue
        if c["id"] in no_partir:
            # e0-r2 (U-R2-CODIGO): partir por ítems podría cortar un bloque de
            # tabla serializada; la unidad se declara y no se parte
            out.append(c)
            no_particionables.append({
                "id": c["id"], "chars_propio": c["chars_propio"],
                "motivo": "tabla_serializada"})
            continue
        part = (_particionar_texto(c["texto"], respetar_tablas=True, renglones=OBJETIVO_PARTES_RENGLONES_R6) if r6
                else _particionar_texto(c["texto"]))
        if part is None:
            out.append(c)
            no_particionables.append({
                "id": c["id"], "chars_propio": c["chars_propio"],
                "motivo": "sin_items_detectables",
                **({"tipo": c["rol_bloque"]} if r6 and c.get("tipo") == "mini_chunk" else {})})
            continue
        subs = _sub_chunks_de(c, part, tope_herencia)
        out.extend(subs)
        particiones.append({
            "id": c["id"], "chars_propio": c["chars_propio"],
            **({"tipo": c["rol_bloque"]} if r6 and c.get("tipo") == "mini_chunk" else {}),
            "familia_items": part["familia"], "n_items": part["n_items"],
            "n_partes": len(subs),
            "partes": [{"id": s["id"], "chars_propio": s["chars_propio"]}
                       for s in subs],
            "partes_sobre_umbral": [s["id"] for s in subs
                                    if s["chars_propio"] > umbral]})
    reporte = {"umbral_chars": umbral,
               "objetivo_chars_parte": OBJETIVO_CHARS_PARTE,
               "particiones": particiones,
               "no_particionables": no_particionables}
    return out, reporte


# ------------------------------------------- tablas en E0, versión e0-r2
# U-R2-CODIGO, etapa R1 (laudo de la release r2, §1.3; L-ESQ-R2 §1.4).
# Nada de esta sección corre con la versión legada de E0 ("e0-v1", el
# default): `correr` la invoca solo con `--version-e0 e0-r2`, y e0_tablas se
# importa dentro de las funciones, así que la salida legada es byte-idéntica
# a la sellada. La sección vive en este driver y no en e0_lib para conservar
# la garantía estructural de B5.8.3 (selftest_b583, A3: e0_lib no conoce a
# e0_tablas).
#
# R1.a — DETECCIÓN. Dos fuentes de tablas lógicas, con la misma forma de
# artefacto que e0_tablas.parsear_to:
#   (1) e0_tablas.parsear_to (B5.8.3), importado SIN editarse;
#   (2) R-TC2, detección propia de tablas de dos filas: una tabla de
#       `find_tables()` (settings por defecto, los de e0_tablas) que R-TC
#       descarta SOLO por `min_filas`, con exactamente 2 filas, que pasaría
#       R-TC si tuviera 3 (≥ 2 columnas, fuera de las zonas de banner y de
#       pie) y cuya segunda fila tiene al menos MIN_CELDAS_NUMERICAS_FILA2
#       celdas numéricas (e0_tablas._es_numerica). Casos que la motivan: los
#       cuadros de ponderadores de cap (encabezado de calificaciones + fila de
#       ponderadores), que R-TC descarta por tener 2 filas y que el patrón de
#       E0 no marca. La guarda numérica excluye el banner «B.C.R.A.» (2 filas
#       sin cifras), que de otro modo pasaría. A las tablas de R-TC2 se les
#       aplican R-ENC, R-COL, R-VERIF y R-NOTA de e0_tablas, sin cambios.
# Guarda G-RECUADRO: una tabla lógica cuyos caracteres no blancos están, en
#   una fracción ≥ FRAC_RECUADRO_PROSA, en filas con una sola celda no vacía
#   es un recuadro de prosa (texto corrido dentro de un marco), no una tabla:
#   no marca el chunk y no se serializa; queda registrada con su fracción.
# Asignación: geométrica. Una línea de E0 pertenece a un segmento de tabla si
#   está en su página y su `top` cae en [y0 − TOL_TOP_TABLA, y1 − TOL_TOP_TABLA]
#   del bbox; el segmento se asigna al chunk que es dueño de esas líneas.
#   Un segmento sin líneas de E0 (páginas fuera del cuerpo, banners de página)
#   queda sin chunk y se registra.
# Marca: un chunk con al menos una tabla asignada que no es recuadro recibe
#   `flags.contenido_tabular = True` y las claves de la marca F (abajo); la
#   evidencia textual de la heurística de E0 no se toca.

VERSION_E0_LEGADA = "e0-v1"
VERSION_E0_R2 = "e0-r2"
VERSIONES_E0 = (VERSION_E0_LEGADA, VERSION_E0_R2)
# M (U-R2-CODIGO): salidas selladas de la versión legada en las que e0-r2 no
# escribe; de salida/ salen además los calibradores del prefijo de E3
SALIDAS_PROTEGIDAS = tuple(Path(__file__).resolve().parent / d
                           for d in ("salida", "salida_enm01", "salida_tanda0"))

MIN_CELDAS_NUMERICAS_FILA2 = 2
FRAC_RECUADRO_PROSA = 0.75
TOL_TOP_TABLA = 2.0


def _consolidar_tabla_r2(t: dict, e0t) -> None:
    """Consolidación de una tabla lógica de R-TC2 con las mismas reglas que
    e0_tablas.parsear_to aplica a las suyas (R-ENC, R-COL, R-VERIF)."""
    seg0 = t["segmentos"][0]
    t["n_cols"] = seg0["n_cols"]
    t["encabezado"] = e0t.detectar_encabezado(seg0["filas"])
    causas = []
    colapsos = []
    for s in t["segmentos"]:
        d = e0t.detectar_colapso(s["filas"])
        if d:
            d["pagina"] = s["pagina"]
            colapsos.append(d)
    if colapsos:
        causas.append("alineacion_no_confiable")
    pct_max = max(s["verificacion"]["pct_perdida"] for s in t["segmentos"])
    if pct_max > e0t.UMBRAL_PERDIDA_NO_CONFIABLE:
        causas.append("perdida_reconstruccion")
    t["declaraciones"] = {"colapsos": colapsos, "pct_perdida_max": pct_max}
    t["estado"] = "declarada" if causas else "parseada"
    t["causas"] = causas


def pasa_rtc2(filas: list[list], bbox, alto: float, e0t) -> bool:
    """Predicado de R-TC2 (ver el comentario de la sección) sobre las filas
    extraídas de una tabla de `find_tables()`, su bbox y el alto de página."""
    n_filas = len(filas)
    n_cols = max((len(f) for f in filas), default=0)
    es_tc, motivo = e0t.clasificar_tabla_contenido(n_filas, n_cols, bbox, alto)
    if es_tc or motivo != "min_filas" or n_filas != 2:
        return False
    pasaria, _ = e0t.clasificar_tabla_contenido(e0t.MIN_FILAS_TC, n_cols, bbox, alto)
    if not pasaria:
        return False
    return sum(1 for c in filas[1] if e0t._es_numerica(c)) >= MIN_CELDAS_NUMERICAS_FILA2


def detectar_tablas_dos_filas(pdf_path: Path, to: str) -> list[dict]:
    """R-TC2 (ver el comentario de la sección). Devuelve tablas lógicas de un
    solo segmento, con ids `<to>::tabla2f<NNN>` (espacio propio, distinto del
    de e0_tablas)."""
    import e0_tablas as e0t  # noqa: PLC0415 — solo en la versión e0-r2
    import pdfplumber  # noqa: PLC0415

    tablas: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for pi, page in enumerate(pdf.pages, start=1):
            alto = float(page.height)
            palabras = None
            for ti, tb in enumerate(page.find_tables()):
                filas = tb.extract()
                n_filas = len(filas)
                n_cols = max((len(f) for f in filas), default=0)
                if not pasa_rtc2(filas, tb.bbox, alto, e0t):
                    continue
                if palabras is None:
                    palabras = page.extract_words()
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
                    "verificacion": e0t.verificar_reconstruccion(palabras, tb.bbox, filas),
                    "notas_pie": e0t.notas_al_pie(palabras, tb.bbox, filas),
                }
                t = {"id": f"{to}::tabla2f{len(tablas):03d}", "segmentos": [seg]}
                _consolidar_tabla_r2(t, e0t)
                tablas.append(t)
    return tablas


def fraccion_recuadro(tabla: dict) -> float:
    """G-RECUADRO: fracción de caracteres no blancos de la tabla que están en
    filas con una sola celda no vacía."""
    total = 0
    en_una = 0
    for s in tabla["segmentos"]:
        for f in s["filas"]:
            llenas = [c for c in f if (c or "").strip()]
            n = sum(1 for c in f for ch in (c or "") if not ch.isspace())
            total += n
            if len(llenas) == 1:
                en_una += n
    return round(en_una / total, 4) if total else 0.0


# Regla 9 de S0 (S0-1 bis): filas de un catálogo en tabla (el catálogo de infracciones de rdbcra, sección 11, pp.
# 36-48). Cada fila lleva en la primera celda solo el número del punto, y en las otras la descripción, la gravedad y
# las multas; la descripción está centrada en la fila, así que empieza renglones antes del renglón del número, y el
# número puede quedar en un renglón cuyo resto sigue en minúscula. Fila de catálogo = fila cuya primera celda es solo
# un número de punto (primer componente hasta MAX_RAIZ, como todo rótulo de E0: deja afuera, por ejemplo, la tabla de
# códigos NCM de ext p. 167, «8802.11.00»), en un segmento de tabla de e0_tablas con al menos MIN_FILAS_CATALOGO_R9
# filas así. La banda de cada fila es la de `find_tables()` (los bordes de la tabla en el PDF; mismos ajustes que
# e0_tablas). Dos partes: 9a, en el parseo: el renglón del número de una fila es rótulo aunque su resto siga en
# minúscula (la celda es la evidencia; solo levanta los rechazos por resto en minúscula); 9b, después del parseo y
# antes de armar los chunks (y antes del acompañamiento T): los renglones de la banda que quedaron en otra unidad
# pasan al punto de la fila, los anteriores a su número como `lineas_previas`. El texto sigue el orden del PDF.
MIN_FILAS_CATALOGO_R9 = 3
RE_CELDA_ROTULO_R9 = re.compile(r"^(\d+(?:\.\d+)+)\.?$")


def _rotulo_de_celda_r9(fila: list):
    m = RE_CELDA_ROTULO_R9.match((fila[0] or "").strip()) if fila else None
    return m if m and int(m.group(1).split(".")[0]) <= E0.MAX_RAIZ else None


def filas_de_catalogo_r9(pdf_path: Path, tablas_to: dict, paginas: list) -> list[dict]:
    """Filas de catálogo de un TO (ver el comentario de la regla 9), cada una con su banda y la posición
    (página, top) del renglón de su número, si hay uno solo en la banda que empiece con él."""
    candidatos = []
    for t in tablas_to["tablas"]:
        if t["origen"] != "e0_tablas":
            continue
        for s in t["segmentos"]:
            n = sum(1 for f in s["filas"] if _rotulo_de_celda_r9(f))
            if n >= MIN_FILAS_CATALOGO_R9:
                candidatos.append((t, s))
    if not candidatos:
        return []
    import pdfplumber  # noqa: PLC0415 — solo con filas de catálogo
    filas = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for t, s in candidatos:
            tbs = pdf.pages[s["pagina"] - 1].find_tables()
            tb = tbs[s["indice_en_pagina"]] if s["indice_en_pagina"] < len(tbs) else None
            if tb is None or [round(v, 1) for v in tb.bbox] != s["bbox"] or tb.extract() != s["filas"]:
                continue        # la tabla no se reproduce: la fila no se toca
            lineas = paginas[s["pagina"] - 1]
            for k, (row, f) in enumerate(zip(tb.rows, s["filas"])):
                m = _rotulo_de_celda_r9(f)
                if not m:
                    continue
                y0, y1 = row.bbox[1], row.bbox[3]
                cand = [l for l in lineas if y0 - TOL_TOP_TABLA <= l.top < y1 - TOL_TOP_TABLA
                        and l.texto.split() and l.texto.split()[0].rstrip(".") == m.group(1)]
                filas.append({"tabla": t["id"], "pagina": s["pagina"], "fila": k,
                              "banda": [round(y0, 1), round(y1, 1)], "numero": m.group(1),
                              "rotulo": (s["pagina"], cand[0].top) if len(cand) == 1 else None})
    return filas


def anclar_filas_de_catalogo_r9(res: E0.ResultadoParseo, tablas_to: dict, filas: list[dict]) -> dict:
    """Parte 9b de la regla 9: cada renglón de la banda de una fila pasa al punto terminal de esa fila (el nodo cuyo
    label es el renglón del número). Una fila sin ese punto, o con el label de otro nodo en su banda, no se toca.
    Devuelve el informe por fila."""
    orden = E0._recolectar_orden_documental(res)
    cont = {id(l): c for l, c in orden}
    dueno_label = {(l.pagina, l.top): c[1] for l, c in orden if c[0] == "label"}
    segs = {(t["id"], s["pagina"]): s for t in tablas_to["tablas"] for s in t["segmentos"]}
    movidas: dict[int, tuple] = {}
    informe = []
    for f in filas:
        fila = {"numero": f["numero"], "pagina": f["pagina"], "banda": f["banda"]}
        informe.append(fila)
        nodo = dueno_label.get(tuple(f["rotulo"])) if f["rotulo"] else None
        if nodo is None or nodo.hijos or nodo.numero != f["numero"]:
            fila["estado"] = "sin_punto_terminal"
            continue
        y0, y1 = f["banda"]
        seg = segs.get((f["tabla"], f["pagina"]))
        banda = [l for l in (seg.get("_lineas", []) if seg else [])
                 if y0 - TOL_TOP_TABLA <= l.top < y1 - TOL_TOP_TABLA and l is not nodo.linea_label]
        if any(cont[id(l)][0] == "label" for l in banda):
            fila["estado"] = "otro_label_en_la_banda"
            continue
        pos_label = (nodo.linea_label.pagina, nodo.linea_label.top)
        antes = despues = 0
        desde = set()
        for l in banda:
            c = cont[id(l)]
            if c[1] is nodo and c[0] == "seg":
                continue
            lado = "antes" if (l.pagina, l.top) < pos_label else "despues"
            movidas[id(l)] = (l, nodo, lado)
            antes += lado == "antes"
            despues += lado == "despues"
            desde.add(c[1].numero if c[1].tipo == "punto" else f"S{c[1].numero}")
        fila.update({"estado": "anclada", "renglones_antes": antes, "renglones_despues": despues,
                     "desde": sorted(desde)})
    if movidas:
        def rec(n: E0.Nodo) -> None:
            n.segmentos = [sg for sg in ([l for l in s if id(l) not in movidas] for s in n.segmentos) if sg]
            for h in n.hijos:
                rec(h)
        for sec in res.secciones:
            rec(sec)
        clave = lambda l: (l.pagina, l.top, l.x0)  # noqa: E731
        por_nodo: dict[int, tuple] = {}
        for l, nodo, lado in movidas.values():
            por_nodo.setdefault(id(nodo), (nodo, [], []))[1 if lado == "antes" else 2].append(l)
        for nodo, antes, despues in por_nodo.values():
            nodo.lineas_previas = sorted(nodo.lineas_previas + antes, key=clave)
            if despues:
                nodo.segmentos = [sorted([l for s in nodo.segmentos for l in s] + despues, key=clave)]
    return {"filas": len(filas), "ancladas": sum(1 for f in informe if f["estado"] == "anclada"),
            "renglones_movidos": len(movidas), "detalle": informe}


def _excluir_tablas_r5a(tablas_to: dict):
    """S0-5a-bis: el predicado de renglón de las tablas que se serializan (las que no son recuadro de prosa), con la
    asignación geométrica de `asignar_lineas_a_tablas`: la página del segmento y el top en su bbox, menos TOL_TOP_TABLA.
    R5-a no mueve esos renglones."""
    zonas: dict[int, list[tuple[float, float]]] = {}
    for t in tablas_to["tablas"]:
        if t["recuadro_prosa"]["es_recuadro"]:
            continue
        for sg in t["segmentos"]:
            zonas.setdefault(sg["pagina"], []).append((sg["bbox"][1] - TOL_TOP_TABLA, sg["bbox"][3] - TOL_TOP_TABLA))

    def excluir(l) -> bool:
        return any(y0 <= l.top <= y1 for y0, y1 in zonas.get(l.pagina, ()))
    return excluir


def _filas_tabla_a(tablas_to: dict):
    """A de S0-6a: el predicado de renglón de las filas de las tablas que se serializan (las de `_excluir_tablas_r5a`),
    salvo el renglón del título de la tabla, que sí puede abrir división."""
    excluir = _excluir_tablas_r5a(tablas_to)
    titulos = {(t.get("encabezado") or {}).get("titulo") or "" for t in tablas_to["tablas"]}
    titulos = {" ".join(x.split("\n")[0].split()) for x in titulos if x}

    def fila(l) -> bool:
        return excluir(l) and " ".join(l.texto.split()) not in titulos
    return fila


def tablas_de_to_r2(pdf_path: Path, to: str) -> dict:
    """Tablas lógicas de un TO para la versión e0-r2: las de e0_tablas y las
    de R-TC2, cada una con su origen y la guarda G-RECUADRO aplicada."""
    import e0_tablas as e0t  # noqa: PLC0415 — solo en la versión e0-r2

    art = e0t.parsear_to(pdf_path, to)
    tablas = []
    for t in art["tablas_logicas"]:
        t["origen"] = "e0_tablas"
        tablas.append(t)
    for t in detectar_tablas_dos_filas(pdf_path, to):
        t["origen"] = "r_tc2"
        tablas.append(t)
    for t in tablas:
        frac = fraccion_recuadro(t)
        t["recuadro_prosa"] = {"fraccion": frac,
                               "es_recuadro": frac >= FRAC_RECUADRO_PROSA}
    return {"to": to,
            "conteos_e0_tablas": art["conteos"],
            "descartadas_por_regla_e0_tablas": art["descartadas_por_regla"],
            "costuras_candidatas_e0_tablas": art["costuras_candidatas"],
            "tablas": tablas}


def asignar_lineas_a_tablas(res: E0.ResultadoParseo, tablas_to: dict,
                            roles: list[str]) -> None:
    """Asignación geométrica (ver el comentario de la sección): agrega a cada
    segmento la lista `_lineas` (objetos Linea del árbol, en orden
    documental; la clave con guion bajo no se serializa) y el rol de E0 de
    su página (`rol_pagina`), que explica los segmentos sin líneas."""
    por_pagina: dict[int, list[E0.Linea]] = {}
    for l, _ in E0._recolectar_orden_documental(res):
        por_pagina.setdefault(l.pagina, []).append(l)
    for t in tablas_to["tablas"]:
        for s in t["segmentos"]:
            y0, y1 = s["bbox"][1], s["bbox"][3]
            s["_lineas"] = [l for l in por_pagina.get(s["pagina"], [])
                            if y0 - TOL_TOP_TABLA <= l.top <= y1 - TOL_TOP_TABLA]
            s["rol_pagina"] = roles[s["pagina"] - 1]


def asignar_tablas_a_chunks(chunks: list[dict], lineas_por_chunk: list[list[E0.Linea]],
                            tablas_to: dict) -> None:
    """Asigna cada segmento al chunk dueño de sus líneas (`chunks` del segmento
    y de la tabla) y decide la marca: tabla con chunk que no es recuadro."""
    dueno: dict[int, int] = {}
    for i, ls in enumerate(lineas_por_chunk):
        for l in ls:
            dueno[id(l)] = i
    for t in tablas_to["tablas"]:
        indices_tabla: list[int] = []
        for s in t["segmentos"]:
            idx = sorted({dueno[id(l)] for l in s["_lineas"] if id(l) in dueno})
            s["chunks"] = [chunks[i]["id"] for i in idx]
            for i in idx:
                if i not in indices_tabla:
                    indices_tabla.append(i)
        t["_indices_chunk"] = indices_tabla
        t["chunks"] = [chunks[i]["id"] for i in indices_tabla]
        t["marca"] = bool(indices_tabla) and not t["recuadro_prosa"]["es_recuadro"]


# R1.c — SERIALIZACIÓN (formato aprobado en el freno intermedio de R1:
# data/experiment/r2_codigo/r1_freno_intermedio.md §3, con los agregados E y
# F de la aprobación). Cada tabla serializada reemplaza, en el texto del
# chunk y en la herencia que lo contiene, la corrida contigua de líneas de E0
# de su bbox por un bloque:
#   [TABLA <id> | página <p> | <e0_tablas o R-TC2> | <columnas o posicional>]
#   Rótulo: …              (solo modo columnas: fila de encabezado cuya primera
#                           celda abarca toda la fila)
#   Columnas: h1 | h2 | …  (solo modo columnas)
#   Fila k: clave = valor | clave = valor
#   [FIN TABLA <id>]
# Modo columnas si la zona de encabezado (filas anteriores a la primera con
# una celda numérica o de código, de 1 a MAX_FILAS_ENCABEZADO filas) no tiene
# celdas None fuera de los rótulos ni « = » en un encabezado; la clave es el
# texto del encabezado de la columna (o `colN` si no tiene). Si no, modo
# posicional: todas las filas, también las de encabezado, con clave `colN`.
# Celdas vacías y filas sin contenido propio se omiten; una celda multilínea
# se escribe con sus fragmentos unidos por un espacio (sin des-silabear).
# E — celdas combinadas en filas de datos: una celda None de una fila de
# datos cubierta, según la geometría de celdas de pdfplumber, por una celda
# que empieza en una fila anterior se escribe con el valor de esa celda y
# MARCA_COMBINADA con el número de fila del bloque donde empieza. La celda
# que la cubre se busca por el punto de la esquina de la celda faltante; si no
# hay exactamente una, la geometría no determina la combinación y la tabla no
# se serializa. Las filas de subtítulo internas (sin celdas numéricas ni de
# código, después de la primera fila de datos) no se propagan: se cuentan.
# G — combinaciones horizontales: una celda con valor que, según la
# geometría, abarca otras columnas de su fila (las celdas None que cubre) se
# escribe una vez, en su columna, con MARCA_ALCANCE y la clave de la última
# columna que cubre; rige en toda fila escrita del bloque (filas de datos de
# los dos modos y filas de encabezado del posicional). Una celda que empieza
# en una fila y una columna anteriores (bidimensional) es parte del alcance
# del valor propagado en esa fila y no se vuelve a escribir. Si la geometría
# no determina el alcance, la tabla no se serializa. V1 descuenta las dos
# marcas.
# No se serializa (la tabla queda marcada y su texto de E0 intacto) si:
# e0_tablas la declaró; R-VERIF da caracteres perdidos; las líneas de E0
# tienen caracteres que no están en las celdas; tiene una celda multilínea
# toda numérica (filas colapsadas); una celda contiene «|»; cae en más de un
# chunk; sus líneas no son contiguas o no están en un solo nodo de E0; la
# geometría no determina una combinación; la tabla re-detectada no coincide.
# En la herencia (decisión D: el bloque de un mini-chunk viaja igual en la
# herencia de sus descendientes), un segmento absorbido entero por un bloque
# que empieza en un segmento anterior no genera tramo.
# Verificaciones por tabla serializada: V1 relectura del bloque contra las
# celdas, descontando los valores propagados; V2 R-VERIF sin pérdida; V3
# multiconjunto de las líneas de E0 reemplazadas contenido en el de las
# celdas y en el del bloque. V4 (chunks sin tabla serializada iguales a la
# versión legada) lo comprueba el censo de la unidad sobre la salida.
# F — marca: `contenido_tabular` = hay tabla detectada; cada entrada de
# `flags.tablas_e0` lleva `serializada` y `bloque` (id del bloque o None);
# `flags.contenido_tabular_residual` = queda contenido tabular fuera de los
# bloques (una tabla marcada sin serializar, o la heurística legada de E0,
# con sus mismos umbrales, sobre las líneas del chunk que no caen en un
# bloque). Las dos claves nuevas van solo en los chunks con tabla marcada:
# en los demás, el chunk es idéntico al de la versión legada, y una clave
# `contenido_tabular_residual` ausente se lee como igual a
# `contenido_tabular` (en la tanda 0, 6 chunks marcados solo por la heurística
# legada, sin tabla detectada). H — cada entrada de `flags.tablas_e0` lleva
# además el modo, las celdas propagadas (E), las celdas con marca de alcance
# (G), las combinadas sin propagar y las filas de subtítulo (None si la tabla
# no se serializó); no cambian el texto.

SEP_PAR = " | "
SEP_CLAVE = " = "
MARCA_COMBINADA = "⟨combinada con fila {}⟩"
RE_MARCA_COMBINADA = re.compile(r" ⟨combinada con fila (\d+)⟩")
MARCA_ALCANCE = "⟨abarca hasta {}⟩"
RE_MARCA_ALCANCE = re.compile(r" ⟨abarca hasta [^⟩]*⟩$")
MAX_FILAS_ENCABEZADO = 4
RE_CODIGO_DATO = re.compile(r"^\d{3}")
EPS_GEOMETRIA = 0.5
RE_FILA_BLOQUE = re.compile(r"^Fila (\d+): (.*)$")


def _txc(c) -> str:
    return (c or "").strip()


def _celda(c) -> str:
    return " ".join(f.strip() for f in _txc(c).split("\n") if f.strip())


def _chars(textos) -> collections.Counter:
    return collections.Counter(ch for t in textos for ch in (t or "") if not ch.isspace())


def _es_dato(c, e0t) -> bool:
    t = _txc(c)
    return bool(t) and (e0t._es_numerica(t) or bool(RE_CODIGO_DATO.match(t)))


def _multilinea_numerica(c, e0t) -> bool:
    fr = [f.strip() for f in _txc(c).split("\n") if f.strip()]
    return len(fr) >= 2 and all(e0t.RE_NUMERICO.match(f) for f in fr)


def _geometria_segmento(page, seg: dict) -> dict | None:
    """Geometría de celdas del segmento (pdfplumber), en dos tablas:
    - `faltantes`: para cada celda None, (fila, col) → (tipo, fila_origen,
      col_origen) de la celda que la cubre: 'vertical' (empieza en una fila
      anterior, misma columna), 'horizontal' (misma fila, columna anterior),
      'bidimensional' (fila y columna anteriores) o 'indeterminada';
    - `ultima_col`: para cada celda con contenido, la última columna que
      cubre (su borde derecho).
    None si la tabla re-detectada en la página no reproduce las filas del
    artefacto."""
    tablas = page.find_tables()
    if seg["indice_en_pagina"] >= len(tablas):
        return None
    tb = tablas[seg["indice_en_pagina"]]
    if tb.extract() != seg["filas"]:
        return None
    xs = sorted({c[0] for c in tb.cells})
    filas_geo = [row.cells for row in tb.rows]
    faltantes: dict = {}
    ultima_col: dict = {}
    for r, cells in enumerate(filas_geo):
        llenas = [c for c in cells if c is not None]
        for ci, c in enumerate(cells):
            if c is not None:
                ultima_col[(r, ci)] = max(k for k, x in enumerate(xs)
                                          if x < c[2] - EPS_GEOMETRIA)
                continue
            if not llenas or ci >= len(xs):
                faltantes[(r, ci)] = ("indeterminada", None, None)
                continue
            px, py = xs[ci] + EPS_GEOMETRIA, llenas[0][1] + EPS_GEOMETRIA
            cubre = [k for k in tb.cells if k[0] <= px < k[2] and k[1] <= py < k[3]]
            if len(cubre) != 1:
                faltantes[(r, ci)] = ("indeterminada", None, None)
                continue
            r0 = next((rr for rr, cc in enumerate(filas_geo) if cubre[0] in cc), None)
            c0 = xs.index(cubre[0][0]) if cubre[0][0] in xs else None
            if r0 is None or c0 is None or r0 > r or c0 > ci or (r0, c0) == (r, ci):
                faltantes[(r, ci)] = ("indeterminada", None, None)
            elif r0 < r and c0 == ci:
                faltantes[(r, ci)] = ("vertical", r0, c0)
            elif r0 == r:
                faltantes[(r, ci)] = ("horizontal", r0, c0)
            else:
                faltantes[(r, ci)] = ("bidimensional", r0, c0)
    return {"faltantes": faltantes, "ultima_col": ultima_col}


def geometria_tablas(pdf_path: Path, tablas: list[dict]) -> None:
    """Agrega `_geometria` a cada segmento de las tablas dadas (solo las que
    tienen alguna celda None)."""
    import pdfplumber  # noqa: PLC0415

    por_pagina: dict[int, list[dict]] = {}
    for t in tablas:
        for s in t["segmentos"]:
            if any(c is None for f in s["filas"] for c in f):
                por_pagina.setdefault(s["pagina"], []).append(s)
            else:
                s["_geometria"] = {}
    if not por_pagina:
        return
    with pdfplumber.open(str(pdf_path)) as pdf:
        for p in sorted(por_pagina):
            for s in por_pagina[p]:
                s["_geometria"] = _geometria_segmento(pdf.pages[p - 1], s)


def _motivo_previo(t: dict, e0t) -> str | None:
    """Condiciones de no serialización que no dependen del chunk ni de la
    geometría."""
    celdas = [c for s in t["segmentos"] for f in s["filas"] for c in f]
    lineas = [l.texto for s in t["segmentos"] for l in s["_lineas"]]
    if t["estado"] != "parseada":
        return "declarada_por_e0_tablas:" + ",".join(t["causas"])
    if any(s["verificacion"]["chars_perdidos"] for s in t["segmentos"]):
        return "r_verif_con_perdida"
    if sum((_chars(lineas) - _chars(celdas)).values()):
        return "lineas_e0_no_contenidas_en_celdas"
    if any(_multilinea_numerica(c, e0t) for c in celdas):
        return "filas_colapsadas"
    if any("|" in _txc(c) for c in celdas):
        return "separador_en_celda"
    if len(t["chunks"]) != 1:
        return "mas_de_un_chunk"
    return None


def armar_bloque(t: dict, e0t, bloque_externo: str | None = None) -> dict:
    """Bloque serializado de una tabla (formato del comentario de la sección)
    o el motivo por el que no se serializa. Con `bloque_externo` (solo lo usa
    el selftest de e0-r2), V1 relee ese texto en lugar del bloque armado."""
    filas = []                         # (segmento, fila en el segmento, celdas)
    for si, s in enumerate(t["segmentos"]):
        rep = set(s.get("filas_encabezado_repetido") or [])
        for fi, f in enumerate(s["filas"]):
            if not (si > 0 and fi in rep):
                filas.append((si, fi, f))
    n_cols = max(len(f) for _, _, f in filas)
    i_dato = next((i for i, (_, _, f) in enumerate(filas)
                   if any(_es_dato(c, e0t) for c in f)), None)
    n_zona = i_dato if i_dato is not None and 1 <= i_dato <= MAX_FILAS_ENCABEZADO else 0
    rotulos, enc_filas = [], []
    for _, _, f in filas[:n_zona]:
        if _txc(f[0]) and all(c is None for c in f[1:]):
            rotulos.append(_celda(f[0]))
        else:
            enc_filas.append(f)
    simple = (bool(enc_filas)
              and not any(c is None for f in enc_filas for c in f)
              and not any(SEP_CLAVE in _celda(c) for f in enc_filas for c in f))
    enc = [""] * n_cols
    if simple:
        for f in enc_filas:
            for k, c in enumerate(f):
                if _txc(c):
                    enc[k] = (enc[k] + " " + _celda(c)).strip()
    modo = "columnas" if simple else "posicional"
    clave_de = (lambda k: enc[k] if (simple and enc[k]) else f"col{k + 1}")
    desde = n_zona if simple else 0
    visibles = [i for i in range(desde, len(filas)) if any(_txc(c) for c in filas[i][2])]
    numero = {i: k for k, i in enumerate(visibles, start=1)}
    subtitulos = [i for i in visibles
                  if i_dato is not None and i > i_dato
                  and not any(_es_dato(c, e0t) for c in filas[i][2])]
    pos_de = {(si, fi): i for i, (si, fi, _) in enumerate(filas)}
    es_fila_dato = (lambda i: i_dato is not None and i >= i_dato and i not in subtitulos)
    zona = (lambda i: "datos" if i_dato is not None and i >= i_dato else "encabezado")
    desglose: collections.Counter = collections.Counter()
    cont: collections.Counter = collections.Counter()
    sin_propagar: collections.Counter = collections.Counter()
    alcance_de: dict = {}               # (fila, col) de una celda propia → clave final

    def _alcance(si: int, fila_origen: int, k: int, fila: int):
        """Clave de la última columna que cubre la celda que empieza en
        (fila_origen, k) del segmento si, vista desde `fila` (la misma fila o
        una fila donde se propaga); None si no abarca otras columnas; False si
        la geometría no determina el alcance (las celdas que cubre no son,
        todas, horizontales en la fila de origen o bidimensionales en una fila
        posterior, cubiertas por esa misma celda)."""
        geo = t["segmentos"][si].get("_geometria")
        if not geo:
            return None
        uc = geo["ultima_col"].get((fila_origen, k))
        if uc is None or uc <= k:
            return None
        esperado = (("horizontal", fila_origen, k) if fila == fila_origen
                    else ("bidimensional", fila_origen, k))
        if any(geo["faltantes"].get((fila, cc)) != esperado for cc in range(k + 1, uc + 1)):
            return False
        return clave_de(uc)

    pags = ", ".join(str(p) for p in sorted({s["pagina"] for s in t["segmentos"]}))
    origen = "e0_tablas" if t["origen"] == "e0_tablas" else "R-TC2"
    lineas = [f"[TABLA {t['id']} | página {pags} | {origen} | {modo}]"]
    if simple:
        lineas.extend(f"Rótulo: {r}" for r in rotulos)
        lineas.append("Columnas: " + SEP_PAR.join(clave_de(k) for k in range(n_cols)))
    for i in visibles:
        si, fi, f = filas[i]
        geo = t["segmentos"][si].get("_geometria")
        pares = []
        for k, c in enumerate(f):
            clave = clave_de(k)
            if _txc(c):
                fin = _alcance(si, fi, k, fi)
                if fin is False:
                    return {"serializada": False, "motivo": "alcance_no_determinado"}
                valor = _celda(c)
                if fin:
                    valor += " " + MARCA_ALCANCE.format(fin)
                    alcance_de[(i, k)] = fin
                    cont["celdas_con_alcance"] += 1
                    desglose["con_alcance_" + zona(i)] += 1
                pares.append(f"{clave}{SEP_CLAVE}{valor}")
                continue
            if c is not None:
                continue
            if geo is None:
                return {"serializada": False, "motivo": "geometria_no_disponible"}
            tipo, r0, c0 = geo["faltantes"].get((fi, k), ("indeterminada", None, None))
            if tipo == "indeterminada":
                return {"serializada": False, "motivo": "geometria_no_determinada"}
            if tipo in ("horizontal", "bidimensional"):
                cont["celdas_cubiertas_por_alcance"] += 1
                desglose[f"cubiertas_{tipo}_{zona(i)}"] += 1
                continue
            if not es_fila_dato(i):
                continue
            io = pos_de.get((si, r0))
            if io is None:
                sin_propagar["origen_en_fila_de_encabezado_repetido"] += 1
                continue
            if i_dato is None or io < i_dato:
                sin_propagar["origen_en_encabezado"] += 1
                continue
            if io in subtitulos:
                sin_propagar["origen_en_subtitulo"] += 1
                continue
            if io not in numero or not _txc(filas[io][2][k]):
                sin_propagar["origen_vacio"] += 1
                continue
            fin = _alcance(si, r0, k, fi)
            if fin is False:
                return {"serializada": False, "motivo": "alcance_no_determinado"}
            valor = f"{_celda(filas[io][2][k])} {MARCA_COMBINADA.format(numero[io])}"
            if fin:
                valor += " " + MARCA_ALCANCE.format(fin)
                cont["celdas_propagadas_con_alcance"] += 1
            pares.append(f"{clave}{SEP_CLAVE}{valor}")
            cont["celdas_propagadas"] += 1
        lineas.append(f"Fila {numero[i]}: " + SEP_PAR.join(pares))
    lineas.append(f"[FIN TABLA {t['id']}]")
    bloque = "\n".join(lineas)
    v1 = _v1_relectura(bloque if bloque_externo is None else bloque_externo,
                       filas, visibles, numero, enc, rotulos, simple, alcance_de)
    return {"serializada": True, "motivo": None, "modo": modo, "bloque": bloque,
            "filas_bloque": len(visibles), "celdas_propagadas": cont["celdas_propagadas"],
            "celdas_propagadas_con_alcance": cont["celdas_propagadas_con_alcance"],
            "celdas_con_alcance": cont["celdas_con_alcance"],
            "celdas_cubiertas_por_alcance": cont["celdas_cubiertas_por_alcance"],
            "alcance_por_zona": dict(sorted(desglose.items())),
            "celdas_combinadas_sin_propagar": sum(sin_propagar.values()),
            "celdas_combinadas_sin_propagar_por_motivo": dict(sorted(sin_propagar.items())),
            "filas_subtitulo": len(subtitulos), "v1": v1}


def _v1_relectura(bloque: str, filas: list, visibles: list[int], numero: dict,
                  enc: list[str], rotulos: list[str], simple: bool, alcance_de: dict) -> dict:
    """V1: relee el bloque y lo compara con las celdas, descontando los valores
    propagados (marca de E) y la marca de alcance (G) de los propios: rótulos,
    encabezados, numeración, claves, valores propios y su marca de alcance por
    fila, y multiconjunto de caracteres de las celdas no vacías."""
    lin = bloque.split("\n")
    errores = []
    leidos_rot = [l[len("Rótulo: "):] for l in lin if l.startswith("Rótulo: ")]
    if leidos_rot != (rotulos if simple else []):
        errores.append("rotulos")
    col = [l[len("Columnas: "):] for l in lin if l.startswith("Columnas: ")]
    if simple and col != [SEP_PAR.join(e or f"col{k + 1}" for k, e in enumerate(enc))]:
        errores.append("columnas")
    filas_leidas = [m for m in (RE_FILA_BLOQUE.match(l) for l in lin) if m]
    if [int(m.group(1)) for m in filas_leidas] != list(range(1, len(visibles) + 1)):
        errores.append("numeracion")
    propios_leidos: list[str] = []
    for m, i in zip(filas_leidas, visibles):
        pares = [p.split(SEP_CLAVE, 1) for p in m.group(2).split(SEP_PAR)] if m.group(2) else []
        propios = [(k, v) for k, v in pares if "⟨combinada con fila " not in v]
        esperados = [((enc[c] if simple and enc[c] else f"col{c + 1}"),
                      _celda(x) + (" " + MARCA_ALCANCE.format(alcance_de[(i, c)])
                                   if (i, c) in alcance_de else ""))
                     for c, x in enumerate(filas[i][2]) if _txc(x)]
        if [tuple(p) for p in propios] != esperados:
            errores.append(f"fila_{numero[i]}")
        propios_leidos.extend(RE_MARCA_ALCANCE.sub("", v) for _, v in propios)
    celdas = [x for _, _, f in filas for x in f if _txc(x)]
    leido = propios_leidos + (leidos_rot + [e for e in enc if e] if simple else [])
    if _chars(leido) != _chars(celdas):
        errores.append("multiconjunto_celdas")
    return {"ok": not errores, "errores": errores}


def preparar_serializacion(res: E0.ResultadoParseo, lineas_por_chunk: list[list[E0.Linea]],
                           tablas_to: dict, pdf_path: Path) -> tuple[dict, set]:
    """Decide qué tablas marcadas se serializan, arma sus bloques y devuelve
    (sustituciones: id de la primera línea → bloque, omitidas: ids de las
    demás líneas de cada tabla serializada)."""
    import e0_tablas as e0t  # noqa: PLC0415

    nodo_de: dict[int, object] = {}
    for l, cont in E0._recolectar_orden_documental(res):
        nodo_de[id(l)] = cont[1]
    candidatas = []
    for t in tablas_to["tablas"]:
        if not t["marca"]:
            t["serializacion"] = {"serializada": False,
                                  "motivo": "recuadro" if t["chunks"] else "sin_chunk"}
            continue
        motivo = _motivo_previo(t, e0t)
        if motivo is None:
            pos = {id(l): j for j, l in enumerate(lineas_por_chunk[t["_indices_chunk"][0]])}
            lineas = [l for s in t["segmentos"] for l in s["_lineas"]]
            idx = sorted(pos[id(l)] for l in lineas if id(l) in pos)
            if len(idx) != len(lineas):
                motivo = "lineas_fuera_del_chunk"
            elif idx != list(range(idx[0], idx[0] + len(idx))):
                motivo = "lineas_no_contiguas"
            elif len({id(nodo_de[id(l)]) for l in lineas}) != 1:
                motivo = "lineas_en_mas_de_un_nodo"
        t["serializacion"] = {"serializada": False, "motivo": motivo}
        if motivo is None:
            candidatas.append(t)
    geometria_tablas(pdf_path, candidatas)
    sustituciones: dict[int, str] = {}
    omitidas: set[int] = set()
    for t in candidatas:
        ser = armar_bloque(t, e0t)
        if ser["serializada"]:
            lineas = [l for s in t["segmentos"] for l in s["_lineas"]]
            celdas = [c for s in t["segmentos"] for f in s["filas"] for c in f]
            repetidas = [c for si, s in enumerate(t["segmentos"]) if si > 0
                         for fi in (s.get("filas_encabezado_repetido") or [])
                         for c in s["filas"][fi]]
            e0 = _chars([l.texto for l in lineas])
            ser["v2_r_verif_sin_perdida"] = not any(
                s["verificacion"]["chars_perdidos"] for s in t["segmentos"])
            ser["v3_e0_en_celdas"] = not sum((e0 - _chars(celdas)).values())
            ser["v3_e0_en_bloque"] = not sum(
                (e0 - _chars(repetidas) - _chars([ser["bloque"]])).values())
            ser["chars_lineas_e0"] = len("\n".join(l.texto for l in lineas))
            ser["chars_bloque"] = len(ser["bloque"])
            if not (ser["v1"]["ok"] and ser["v2_r_verif_sin_perdida"]
                    and ser["v3_e0_en_celdas"] and ser["v3_e0_en_bloque"]):
                ser = {"serializada": False, "motivo": "verificacion_fallida",
                       "detalle": {k: ser[k] for k in ("v1", "v2_r_verif_sin_perdida",
                                                       "v3_e0_en_celdas", "v3_e0_en_bloque")}}
        t["serializacion"] = ser
        if ser["serializada"]:
            orden = {id(l): j for j, l in enumerate(lineas_por_chunk[t["_indices_chunk"][0]])}
            lineas = sorted((l for s in t["segmentos"] for l in s["_lineas"]),
                            key=lambda l: orden[id(l)])
            sustituciones[id(lineas[0])] = ser["bloque"]
            omitidas.update(id(l) for l in lineas[1:])
    return sustituciones, omitidas


def texto_con_tablas(sustituciones: dict[int, str], omitidas: set):
    """Constructor de texto para E0.construir_chunks: la primera línea de cada
    tabla serializada se reemplaza por su bloque y las demás se omiten."""
    def tx(lineas: list[E0.Linea]) -> str:
        return "\n".join(sustituciones.get(id(l), l.texto)
                         for l in lineas if id(l) not in omitidas)
    return tx


def _entrada_tablas_e0(t: dict) -> dict:
    """Entrada de `flags.tablas_e0` (marca F y metadatos H): no cambian el
    texto del chunk."""
    ser = t["serializacion"]
    sa = ser["serializada"]
    return {"tabla": t["id"], "origen": t["origen"], "estado": t["estado"],
            "paginas": sorted({s["pagina"] for s in t["segmentos"]}),
            "serializada": sa, "bloque": t["id"] if sa else None,
            "modo": ser["modo"] if sa else None,
            "celdas_propagadas": ser["celdas_propagadas"] if sa else None,
            "celdas_con_alcance": ser["celdas_con_alcance"] if sa else None,
            "combinadas_sin_propagar": ser["celdas_combinadas_sin_propagar"] if sa else None,
            "filas_subtitulo": ser["filas_subtitulo"] if sa else None}


def aplicar_marcas_r2(chunks: list[dict], lineas_por_chunk: list[list[E0.Linea]],
                      tablas_to: dict, sustituciones: dict, omitidas: set) -> None:
    """Marca F (ver el comentario de la sección) en los chunks con tabla."""
    por_chunk: dict[int, list[dict]] = {}
    for t in tablas_to["tablas"]:
        if t["marca"]:
            for i in t["_indices_chunk"]:
                por_chunk.setdefault(i, []).append(t)
    en_bloque = set(sustituciones) | omitidas
    for i in sorted(por_chunk):
        f = chunks[i]["flags"]
        f["contenido_tabular"] = True
        f["tablas_e0"] = [_entrada_tablas_e0(t) for t in por_chunk[i]]
        fuera = [l for l in lineas_por_chunk[i] if id(l) not in en_bloque]
        f["contenido_tabular_residual"] = (
            any(not t["serializacion"]["serializada"] for t in por_chunk[i])
            or E0._flags_tabla_formula(fuera)["contenido_tabular"])


def fundir_tabla_en_intersticiales(res: E0.ResultadoParseo, tablas_to: dict, chunks0: list[dict]) -> list[dict]:
    """Acompañamiento de las reglas 1 y 7 de S0 (e0-r2): una tabla marcada cuyas líneas caen en dos
    o más intersticiales de un mismo nodo y de un mismo hueco entre hijos (sus celdas en la columna
    de texto del ancestro se re-anclan renglón a renglón) se lleva a un solo segmento: se funden los
    segmentos del nodo desde el primero hasta el último con líneas de la tabla. La tabla queda en un
    solo chunk y puede serializarse. Devuelve las fusiones hechas."""
    fusiones = []
    for t in tablas_to["tablas"]:
        if not t["marca"] or len(t["chunks"]) < 2 or not all("::intersticial" in c for c in t["chunks"]):
            continue
        nodo_seg: dict[int, tuple] = {}     # se recalcula: una fusión anterior cambia los segmentos
        for l, cont in E0._recolectar_orden_documental(res):
            if cont[0] == "seg":
                nodo_seg[id(l)] = (cont[1], cont[2])
        pares = [nodo_seg.get(id(l)) for s in t["segmentos"] for l in s["_lineas"]]
        if any(p is None for p in pares) or len({id(p[0]) for p in pares}) != 1:
            continue
        nodo = pares[0][0]
        idx = sorted({next(i for i, sg in enumerate(nodo.segmentos) if sg is p[1]) for p in pares})
        i0, i1 = idx[0], idx[-1]
        if i0 == i1:
            continue
        marcas = [(h.pagina, h.linea_label.top if h.linea_label else 0.0) for h in nodo.hijos]
        pos = [(sg[0].pagina, sg[0].top) for sg in nodo.segmentos[i0:i1 + 1]]
        hueco = {sum(1 for m in marcas if m < p) for p in pos}
        if len(hueco) != 1 or min(pos) < marcas[0] or max(pos) > marcas[-1]:
            continue     # cruza un hijo, o es intro o cierre: no se toca
        fundido = [l for sg in nodo.segmentos[i0:i1 + 1] for l in sg]
        nodo.segmentos[i0:i1 + 1] = [fundido]
        fusiones.append({"tabla": t["id"], "nodo": nodo.numero, "segmentos_fundidos": i1 - i0 + 1})
    return fusiones


def procesar_tablas_r2(res: E0.ResultadoParseo, pdf_path: Path, to: str,
                       roles: list[str], tablas_to: dict | None = None,
                       filas_r9: list[dict] | None = None) -> tuple[list[dict], dict, frozenset]:
    """Camino e0-r2 completo de un TO: detección, asignación, serialización y
    marca. Devuelve (chunks, tablas_to, ids de chunks con bloque). Con la regla 9 de S0, las tablas llegan ya
    detectadas (se detectan antes del parseo) y las filas de catálogo se anclan antes de armar los chunks."""
    if tablas_to is None:
        tablas_to = tablas_de_to_r2(pdf_path, to)
    asignar_lineas_a_tablas(res, tablas_to, roles)
    if filas_r9:
        inf = anclar_filas_de_catalogo_r9(res, tablas_to, filas_r9)
        if inf["ancladas"]:     # una tabla con forma de catálogo sin ninguna fila anclada no deja rastro
            res.avisos.append({"tipo": "filas_de_catalogo_r9", **inf})
    lineas0: list = []
    # reglas 4a y 4b de S0-4 (fuera de la tanda 0)
    r4 = {"oracion_titulo_4a": "4a" in REGLAS_S0_4 and to not in TOS_TANDA0_SIN_4AB,
          "titulo_envuelto_4b": "4b" in REGLAS_S0_4 and to not in TOS_TANDA0_SIN_4AB,
          # R5-b y R5-c de S0-5a
          "intersticial_continuado": _r5("r5b", to, TOS_INTERSTICIAL_S0_5),
          "titulo_seccion_envuelto": _r5("r5c", to),
          # B y D de S0-6a
          "encabezado_b": _r6("b", to),
          "rotulo_impreso_d": _r6("d", to),
          # M de S0-6a-bis: solo en los sub-documentos que abre A
          "raiz0_solo_titulo_m": _r6("m", to) and not _sd_s04(to)}
    chunks0 = E0.construir_chunks(res, lineas_por_chunk=lineas0, **r4)
    E0.desambiguar_ids(chunks0)
    asignar_tablas_a_chunks(chunks0, lineas0, tablas_to)
    # acompañamiento T de las reglas 1 y 7 de S0
    fusiones = fundir_tabla_en_intersticiales(res, tablas_to, chunks0)
    if fusiones:
        res.avisos.append({"tipo": "tabla_fundida_en_un_intersticial_r2", "fusiones": fusiones})
        lineas0 = []
        chunks0 = E0.construir_chunks(res, lineas_por_chunk=lineas0, **r4)
        E0.desambiguar_ids(chunks0)
        asignar_tablas_a_chunks(chunks0, lineas0, tablas_to)
    sustituciones, omitidas = preparar_serializacion(res, lineas0, tablas_to, pdf_path)
    lineas: list = []
    chunks = E0.construir_chunks(res, texto_lineas=texto_con_tablas(sustituciones, omitidas),
                                 lineas_por_chunk=lineas, tope_herencia=TOPE_HERENCIA_E0_R2, **r4)
    renombres = E0.desambiguar_ids(chunks)
    tablas_to["ids_desambiguados"] = renombres
    tablas_to["_dueno_linea"] = {id(l): chunks[i]["id"]
                                 for i, ls in enumerate(lineas) for l in ls}
    if [c["id"] for c in chunks] != [c["id"] for c in chunks0] or \
            [[id(l) for l in ls] for ls in lineas] != [[id(l) for l in ls] for ls in lineas0]:
        raise RuntimeError(f"{to}: la serialización cambió la segmentación en chunks")
    aplicar_marcas_r2(chunks, lineas, tablas_to, sustituciones, omitidas)
    con_bloque = frozenset(chunks[t["_indices_chunk"][0]]["id"] for t in tablas_to["tablas"]
                           if t.get("serializacion", {}).get("serializada"))
    return chunks, tablas_to, con_bloque


def escalera_e0_r2(to: str, archivo: str, paginas: list, roles_v: list[str],
                   rotulos_fila_r9: frozenset = frozenset()):
    """Escalera de E0 de la partición (correr_b584.correr_to), solo para la
    versión e0-r2 (U-R2-CODIGO, agregado 9). Etapa 1: camino vigente. Si no da
    chunks, etapa 2: reglas de marcador (B5.8.2). Si tampoco, etapa 3: modo
    sin raíz (B5.8.1) sobre la clasificación de marcadores. En cada etapa, K
    (`mayusculas_repetidas` con los roles de esa etapa) y el pie desde la
    línea «Versión». Devuelve (res, roles, repetidos, modo_lectura,
    marcadores). Reglas de S0-4: la de apartados corre en cada lectura (TOS_APARTADOS_S0_4); la de sub-documento
    (TOS_SUBDOCUMENTO_S0_4, y con sdr1 TOS_SUBDOCUMENTO_R1_S0_4) no cambia la etapa: la etapa se elige sin ella y se
    vuelve a leer con los sub-documentos; la de apartados de letra (apl, TOS_APARTADO_LETRA_S0_4) tampoco: si la etapa
    es la sin raíz, se vuelve a leer con el marcador de letra."""
    m3 = "m3" in REGLAS_S0_3     # mecanismo 3 de S0-3 (cuarta forma de la regla 8)
    r1 = "sdr1" in REGLAS_S0_4 and to in TOS_SUBDOCUMENTO_R1_S0_4     # regla sdr1 de S0-4a-ter
    sd = ("sd" in REGLAS_S0_4 and to in TOS_SUBDOCUMENTO_S0_4) or r1     # regla de sub-documento de S0-4
    sd_a = _r6("a", to) and not sd     # A de S0-6a: los sub-documentos de anexo, en todos los TOs
    letras = {r: r in REGLAS_S0_4 and to in TOS_LETRA_S0_4 for r in ("sdl", "sdlh", "sdla")}     # S0-4a-ter

    def indice(roles: list[str]) -> list[str]:
        # regla 3 de S0, ampliación: páginas de cuerpo que son enteras una lista de la regla 8
        return E0.paginas_indice_r8(paginas, roles, forma4_m3=m3)

    def parsear(roles: list[str], con_sd: bool = False, **kw):
        rep = E0.titulos_mayusculas_repetidos(paginas, roles)
        if con_sd:
            # regla de sub-documento de S0-4, con la guarda de columna dentro del sub-documento (sdg3) y la raíz
            # mayor que MAX_RAIZ que sucede a la anterior (sdmax)
            kw["subdocumentos"] = E0.limites_subdocumento(paginas, roles, letras=any(letras.values()),
                                                          sin_regimen_pagina_1=r1, solo_anexo=sd_a)
            kw["g3_subdoc"] = "sdg3" in REGLAS_S0_4
            kw["raiz_max_subdoc"] = "sdmax" in REGLAS_S0_4
            # reglas sdl, sdlh y sdla de S0-4a-ter (forma de letra)
            kw["letra_corte"], kw["letra_herencia"], kw["letra_numero"] = letras["sdl"], letras["sdlh"], letras["sdla"]
        if "ap" in REGLAS_S0_4 and to in TOS_APARTADOS_S0_4:
            kw["apartados_seccion"] = True     # regla de apartados de S0-4
        if _r5("r5d", to):
            kw["numero_en_referencia"] = True     # R5-d de S0-5a
        if _r5("r5f", to, frozenset(ROTULOS_POR_LISTA_S0_5)):
            kw["rotulos_por_lista"] = ROTULOS_POR_LISTA_S0_5[to]     # R5-f de S0-5a-bis
        if _r5("r5g", to, frozenset(RAICES_POR_LISTA_S0_5)):
            kw["raices_por_lista"] = RAICES_POR_LISTA_S0_5[to]     # R5-g de S0-5a-bis
        # A (banda), E, F1, G, H, I, J y K de S0-6a
        kw.update({"banda_a": _r6("a", to), "raiz_sucesora_e": _r6("e", to), "encabezado_tabla_f": _r6("f", to),
                   "numero_partido_g": _r6("g", to), "numero_pegado_h": _r6("h", to), "recuadro_i": _r6("i", to),
                   "caratula_j": _r6("j", to), "pie_formulario_k": _r6("k", to)})
        # regla 8 de S0: renglones de listas de puntos leídas como cuerpo, con los roles de esta etapa
        kw["no_rotulos"] = E0.lineas_de_listas_r8(paginas, roles, forma4_m3=m3)
        if _r6("l", to):
            kw["indice_l"] = E0.lineas_de_indice_l(paginas, roles)     # L de S0-6a-bis
        if rotulos_fila_r9:
            kw["rotulos_fila"] = rotulos_fila_r9     # regla 9 de S0, parte 9a
        # U-R2-CODIGO-2 (C2): cola de título estricta (punto l, ampliada por la regla 5 de S0) y renumeración
        # por lista (punto f); reglas 1, 2 y 7 de S0
        return E0.parsear_cuerpo(to, archivo, paginas, roles, mayusculas_repetidas=rep,
                                 pie_desde_version=True,
                                 cola_titulo_estricta=(COLA_TITULO_ESTRICTA_E0_R2.get(to, frozenset())
                                                       | COLA_TITULO_ESTRICTA_R5.get(to, frozenset())),
                                 renumeraciones=RENUMERACIONES_E0_R2,
                                 seccion_variante=True, rotulos_r2=True, reabrir_padre=True,
                                 formas_m1=_formas_s0_3("m1"), formas_m2=_formas_s0_3("m2"),
                                 formas_m5=_formas_s0_3("m5"), **kw), rep

    def con_chunks(res) -> bool:
        r = copy.deepcopy(res)
        r.reasignaciones_continuidad = E0.aplicar_continuidad_enumeracion(r)
        E0.corregir_fronteras_intra_palabra(r)
        return bool(E0.construir_chunks(r))

    roles_v0 = roles_v
    roles_v = indice(roles_v0)
    res, rep = parsear(roles_v)
    if con_chunks(res):
        if sd or sd_a:
            res, rep = parsear(roles_v, con_sd=True)
        return res, roles_v, rep, "vigente", False
    roles_m0 = E0.clasificar_paginas(paginas, marcadores_b582=True, continuacion_con_titulo=True)
    roles_m = indice(roles_m0)
    res_m, rep_m = parsear(roles_m, marcadores_b582=True)
    if con_chunks(res_m):
        if sd or sd_a:
            res_m, rep_m = parsear(roles_m, con_sd=True, marcadores_b582=True)
        return res_m, roles_m, rep_m, "marcadores", True
    roles_s = indice(E0.roles_para_modo_sin_raiz(paginas, roles_m0))
    res_s, rep_s = parsear(roles_s, modo_sin_raiz=True)
    # regla 4 de S0: si el modo sin raíz deja el TO en una sola unidad y el cuerpo tiene al menos
    # MIN_APARTADOS_R4 líneas «APARTADO X: …», se lee con el marcador de letra y número (ri_spi)
    apartados = sum(1 for ls, rol in zip(paginas, roles_s) if rol == E0.ROL_CUERPO
                    for l in ls if E0.RE_APARTADO_R2.match(l.texto.strip()))
    r = copy.deepcopy(res_s)
    r.reasignaciones_continuidad = E0.aplicar_continuidad_enumeracion(r)
    E0.corregir_fronteras_intra_palabra(r)
    if apartados >= MIN_APARTADOS_R4 and len(E0.construir_chunks(r)) <= 1:
        res_l, rep_l = parsear(roles_s, con_sd=sd or sd_a, modo_sin_raiz=True, marcador_letra=True)
        res_l.avisos.append({"tipo": "marcador_letra_r2", "apartados": apartados})
        return res_l, roles_s, rep_l, "sin_raiz_letra", roles_m0 != roles_v0
    if "apl" in REGLAS_S0_4 and to in TOS_APARTADO_LETRA_S0_4 and apartados >= MIN_APARTADOS_R4:
        # regla apl de S0-4a-ter: la etapa sin raíz se vuelve a leer con el marcador de letra de la regla 4
        res_s, rep_s = parsear(roles_s, con_sd=sd or sd_a, modo_sin_raiz=True, marcador_letra=True)
        res_s.avisos.append({"tipo": "apartado_letra_apl", "apartados": apartados})
    elif sd or sd_a:
        res_s, rep_s = parsear(roles_s, con_sd=True, modo_sin_raiz=True)
    return res_s, roles_s, rep_s, "sin_raiz", roles_m0 != roles_v0


def lineas_conservadas_k(paginas: list, roles: list[str], repetidos: set[str]) -> list:
    """K (U-R2-CODIGO): líneas que el descarte histórico del encabezado de
    página quitaba y que la regla de e0-r2 conserva (en mayúsculas, sin
    repetirse en la zona de título de otra página de cuerpo)."""
    out = []
    for lineas, rol in zip(paginas, roles):
        if rol != E0.ROL_CUERPO:
            continue
        _, viejas, _ = E0.separar_encabezado_pie(lineas)
        # mecanismo 5 de S0-3, forma a: K conserva también lo que esa forma deja como texto
        _, nuevas, _ = E0.separar_encabezado_pie(lineas, mayusculas_repetidas=repetidos,
                                                  cierre_m5="a" in _formas_s0_3("m5"))
        ids_nuevas = {id(l) for l in nuevas}
        out.extend(l for l in viejas if id(l) not in ids_nuevas)
    return out


def serializar_tablas_to(tablas_to: dict) -> dict:
    """Artefacto `tablas_<to>.json` de la versión e0-r2: tablas, guarda,
    líneas de E0 asignadas (página, top, texto), chunk dueño y serialización;
    sin objetos Linea ni geometría interna."""
    out = {k: v for k, v in tablas_to.items() if k != "tablas"}
    tablas = []
    for t in tablas_to["tablas"]:
        tt = {k: v for k, v in t.items() if k != "segmentos" and not k.startswith("_")}
        segs = []
        for s in t["segmentos"]:
            ss = {k: v for k, v in s.items() if not k.startswith("_")}
            ss["lineas_e0"] = [{"pagina": l.pagina, "top": l.top, "texto": l.texto}
                               for l in s.get("_lineas", [])]
            segs.append(ss)
        tt["segmentos"] = segs
        tablas.append(tt)
    out["tablas"] = tablas
    return out


def inventario_mapa(mapa_path: Path = MAPA) -> dict[str, list[str]]:
    m = json.loads(mapa_path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for to, d in m["por_to"].items():
        unidades = []
        for cat in ("quemadas_enteras", "quemadas_parcialmente", "disponibles"):
            for it in d.get(cat, []):
                unidades.append(it["unidad"] if isinstance(it, dict) else it)
        out[to] = unidades
    return out


def correr(salida: Path, manifiesto=None,
           version_e0: str = VERSION_E0_LEGADA) -> dict:
    """`version_e0` (U-R2-CODIGO): con la legada ("e0-v1", el default) la
    salida es byte-idéntica a la sellada; con "e0-r2" corre además la
    sección «tablas en E0, versión e0-r2» de este módulo (no de e0_lib:
    selftest_b583, A3) y escribe `tablas_<to>.json` y `version_e0.json`."""
    if version_e0 not in VERSIONES_E0:
        raise ValueError(f"version_e0 desconocida: {version_e0!r} "
                         f"(conocidas: {VERSIONES_E0})")
    r2 = version_e0 == VERSION_E0_R2
    if r2 and Path(salida).resolve() in {d.resolve() for d in SALIDAS_PROTEGIDAS}:
        raise ValueError(f"e0-r2 no escribe en {salida}: es una salida sellada de la "
                         f"versión legada (de e0_chunking/salida salen los calibradores "
                         f"del prefijo de E3)")
    salida.mkdir(parents=True, exist_ok=True)
    if manifiesto is None:
        items = sorted(E0.TO_KEYS.items(), key=lambda kv: kv[1])
        pdfs = {to: SUBSET / archivo for archivo, to in items}
        mapa = inventario_mapa()
    else:
        items = sorted(((manifiesto.archivo_de(t), t) for t in manifiesto.ids),
                       key=lambda kv: kv[1])
        pdfs = {to: manifiesto.pdf_de(to) for _, to in items}
        mapa = (inventario_mapa(manifiesto.mapa_territorio)
                if manifiesto.tiene_oraculo else None)
    conteos: dict = {}
    divergencias: dict = {}
    censo: dict = {}
    cobertura: dict = {}

    correcciones: dict = {}
    sub_chunking: dict = {}
    ids_desambiguados: dict = {}
    encabezados_conservados: dict = {}

    for archivo, to in items:
        pdf = pdfs[to]
        paginas = E0.extraer_lineas(pdf)
        roles = (E0.clasificar_paginas(paginas, continuacion_con_titulo=True) if r2
                 else E0.clasificar_paginas(paginas))
        if r2:
            # K (U-R2-CODIGO): en la rama de mayúsculas del encabezado de página
            # se descarta solo lo que se repite en al menos 2 páginas de cuerpo;
            # agregado 8: pie desde la línea «Versión»; agregado 9: escalera
            # de la partición (marcadores y sin raíz) cuando el camino vigente
            # no da chunks
            # regla 9 de S0: las tablas se detectan antes del parseo para leer las filas de catálogo
            tablas_r9 = tablas_de_to_r2(pdf, to)
            filas_r9 = filas_de_catalogo_r9(pdf, tablas_r9, paginas)
            res, roles, repetidos, modo_lectura, marcadores_e0 = escalera_e0_r2(
                to, archivo, paginas, roles,
                rotulos_fila_r9=frozenset(f["rotulo"] for f in filas_r9 if f["rotulo"]))
            conservadas = lineas_conservadas_k(paginas, roles, repetidos)
        else:
            res = E0.parsear_cuerpo(to, archivo, paginas, roles)
        # correcciones post-parseo (reglas 1 y 2; ver docstring de e0_lib):
        # el conteo "antes" se toma sobre el árbol recién parseado, idéntico
        # al de la corrida sin reglas
        fronteras_antes = E0.detectar_fronteras_intra_palabra(res)
        res.reasignaciones_continuidad = E0.aplicar_continuidad_enumeracion(res)
        regla2 = E0.corregir_fronteras_intra_palabra(res)
        fronteras_despues = E0.detectar_fronteras_intra_palabra(res)
        res.correccion_fronteras = {
            "antes": fronteras_antes["n_intra_palabra"],
            "despues": fronteras_despues["n_intra_palabra"],
            **regla2,
        }
        # R5-a por lista: la de S0-5a-bis, o con C la que queda (S0-6a-bis, LISTAS_R5A_S0_6)
        listas_r5a = (LISTAS_R5A_S0_6.get(to, {}) if _r6("c", to)
                      else LISTAS_R5A_S0_5.get(to, {}) if _r5("r5a", to, frozenset(LISTAS_R5A_S0_5)) else {})
        if r2 and (listas_r5a or _r5("r5a2", to, TOS_TITULO_BLOQUE_S0_5)):
            # R5-a y R5-a′ de S0-5a, sobre el árbol corregido por las reglas 1 y 2; R5-a, por lista y sin tablas
            # (S0-5a-bis)
            res.avisos.extend(E0.aplicar_cierre_al_margen(
                res, cierre=bool(listas_r5a),
                titulo_bloque=_r5("r5a2", to, TOS_TITULO_BLOQUE_S0_5),
                listas=listas_r5a, excluir=_excluir_tablas_r5a(tablas_r9)))
        if r2 and _r5("r5e", to, TOS_ROTULO_VERTICAL_S0_5):
            res.avisos.extend(E0.juntar_rotulo_vertical(res))     # R5-e de S0-5a, sobre el árbol
        if r2 and _r6("a", to):
            # A de S0-6a, sobre el árbol y antes de C: divisiones por títulos sin número y adopción
            res.avisos.extend(E0.dividir_a(res, sin_raiz=modo_lectura.startswith("sin_raiz"),
                                           fila_tabla=_filas_tabla_a(tablas_r9)))
        if r2 and _r6("c", to):
            # C de S0-6a, sobre el árbol (reemplaza a R5-a por lista); como R5-a, no mueve renglones de tablas
            res.avisos.extend(E0.asignar_por_columna_c(res, excluir=_excluir_tablas_r5a(tablas_r9),
                                                       listas_fijas=frozenset(LISTAS_R5A_S0_6.get(to, {}))))
        if r2 and _r6("f", to):
            res.avisos.extend(E0.mover_encabezado_tabla_f(res))     # F2 de S0-6a, sobre el árbol
        correcciones[to] = {
            "reasignaciones_continuidad": res.reasignaciones_continuidad,
            "fronteras_intra_palabra": {
                "antes": fronteras_antes["n_intra_palabra"],
                "despues": fronteras_despues["n_intra_palabra"],
                "detalle_antes": fronteras_antes["fronteras"],
                "sospechosas_excluidas": fronteras_antes["sospechosas_excluidas"],
                "lineas_corridas": regla2["lineas_corridas"],
            },
        }
        indice = (E0.parsear_indice(paginas, roles, marcadores_b582=marcadores_e0) if r2
                  else E0.parsear_indice(paginas, roles))
        no_partir: frozenset = frozenset()
        if r2:
            chunks, tablas_to, no_partir = procesar_tablas_r2(res, pdf, to, roles, tablas_to=tablas_r9,
                                                              filas_r9=filas_r9)
            dueno = tablas_to.pop("_dueno_linea")
            if conservadas:
                encabezados_conservados[to] = [
                    {"pagina": l.pagina, "top": l.top, "texto": l.texto,
                     "chunk": dueno.get(id(l))} for l in conservadas]
            if tablas_to["ids_desambiguados"]:
                ids_desambiguados[to] = tablas_to.pop("ids_desambiguados")
            else:
                tablas_to.pop("ids_desambiguados")
            (salida / f"tablas_{to}.json").write_text(
                json.dumps(serializar_tablas_to(tablas_to), ensure_ascii=False,
                           indent=1), encoding="utf-8")
        else:
            chunks = E0.construir_chunks(res)
        # U-B5.3 decisión 6: partición por ítems de unidades sobre el umbral
        # C8 (identidad en el subset de desarrollo: 0 unidades lo superan).
        chunks, rep_sub = subdividir_unidades_grandes(chunks, no_partir=no_partir,
                                                      tope_herencia=TOPE_HERENCIA_E0_R2 if r2 else None)
        if rep_sub["particiones"] or rep_sub["no_particionables"]:
            sub_chunking[to] = rep_sub
        div = E0.divergencias_indice_cuerpo(res, indice)
        cob = E0.verificar_cobertura(res)

        (salida / f"estructura_{to}.json").write_text(
            json.dumps(E0.serializar_estructura(res), ensure_ascii=False, indent=1),
            encoding="utf-8")
        (salida / f"indice_{to}.json").write_text(
            json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
        (salida / f"chunks_{to}.json").write_text(
            json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
        if r2:
            # U-R2-CODIGO-2 (C2, punto n): versión y Comunicación del pie de cada página, en un archivo propio
            (salida / f"pies_{to}.json").write_text(
                json.dumps(E0.pies_de_paginas(to, archivo, paginas, roles), ensure_ascii=False, indent=1),
                encoding="utf-8")

        divergencias[to] = div
        cobertura[to] = cob

        if mapa is not None:
            inv_parser = E0.inventario_nivel_mapa(res)
            inv_mapa = set(mapa[to])
            censo[to] = {
                "n_parser": len(inv_parser),
                "n_mapa": len(inv_mapa),
                "coincidencias": sorted(inv_parser & inv_mapa),
                "solo_mapa": sorted(inv_mapa - inv_parser),
                "solo_parser": sorted(inv_parser - inv_mapa),
            }

        terminales = [c for c in chunks if c["tipo"] != "mini_chunk"]
        minis = [c for c in chunks if c["tipo"] == "mini_chunk"]
        minis_por_rol: dict[str, int] = {}
        for c in minis:
            minis_por_rol[c["rol_bloque"]] = minis_por_rol.get(c["rol_bloque"], 0) + 1
        propios = [c["chars_propio"] for c in terminales]
        completos = [c["chars_completo"] for c in terminales]
        roles_pag = {r: roles.count(r) for r in sorted(set(roles))}
        conteos[to] = {
            "archivo": archivo,
            "paginas": len(paginas),
            "roles_pagina": roles_pag,
            "secciones": len(res.secciones),
            "puntos_terminales": sum(1 for c in terminales if c["tipo"] == "punto_terminal"),
            "secciones_sin_puntos": sum(1 for c in terminales if c["tipo"] == "seccion_sin_puntos"),
            "chunks_terminales": len(terminales),
            "mini_chunks": len(minis),
            "mini_chunks_por_rol": dict(sorted(minis_por_rol.items())),
            "chunks": len(chunks),
            "flag_contenido_tabular": sum(1 for c in chunks if c["flags"]["contenido_tabular"]),
            "flag_formula": sum(1 for c in chunks if c["flags"]["formula"]),
            "mediana_chars_propio": statistics.median(propios) if propios else 0,
            "mediana_chars_completo": statistics.median(completos) if completos else 0,
            "mediana_chars_mini_chunk": statistics.median(
                [c["chars_propio"] for c in minis]) if minis else 0,
            "rechazos_header": len(res.rechazos_header),
            "saltos_numeracion": len(res.saltos_numeracion),
            "avisos": len(res.avisos),
            "lineas_descartadas_encabezado_pie":
                res.accounting["lineas_descartadas_encabezado_pie"],
            "lineas_contenido": res.lineas_contenido,
            "lineas_huerfanas": res.lineas_huerfanas,
            "reasignaciones_continuidad": len(res.reasignaciones_continuidad),
            "fronteras_intra_palabra_antes": res.correccion_fronteras["antes"],
            "fronteras_intra_palabra_despues": res.correccion_fronteras["despues"],
            "lineas_corridas_por_frontera": res.correccion_fronteras["n_corridas"],
        }
        if r2:
            conteos[to]["modo_lectura"] = modo_lectura
            conteos[to]["marcadores_b582"] = marcadores_e0

    (salida / "divergencias_indice_cuerpo.json").write_text(
        json.dumps(divergencias, ensure_ascii=False, indent=1), encoding="utf-8")
    if mapa is not None:
        (salida / "censo_oraculo.json").write_text(
            json.dumps(censo, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "conteos.json").write_text(
        json.dumps(conteos, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "cobertura.json").write_text(
        json.dumps(cobertura, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "correcciones.json").write_text(
        json.dumps(correcciones, ensure_ascii=False, indent=1), encoding="utf-8")
    if sub_chunking:  # solo si hubo unidades sobre el umbral (jamás en dev)
        (salida / "sub_chunking.json").write_text(
            json.dumps(sub_chunking, ensure_ascii=False, indent=1),
            encoding="utf-8")
    if encabezados_conservados:   # solo e0-r2 y solo si K conservó alguna línea
        (salida / "encabezados_conservados.json").write_text(
            json.dumps(encabezados_conservados, ensure_ascii=False, indent=1), encoding="utf-8")
    if ids_desambiguados:   # solo e0-r2 y solo si hubo ids repetidos (BKL-0037)
        (salida / "ids_desambiguados.json").write_text(
            json.dumps(ids_desambiguados, ensure_ascii=False, indent=1), encoding="utf-8")
    if r2:
        (salida / "version_e0.json").write_text(
            json.dumps({"version_e0": version_e0}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    return conteos


def shas_salida(salida: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(salida.glob("*.json"))}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=None,
                    help="directorio de salida; por defecto, salida/ (solo con la "
                         "versión legada: e0-r2 exige --salida explícita)")
    ap.add_argument("--manifiesto", default=None,
                    help="ruta a un manifiesto de corpus (U-B5.1); sin él, "
                         "comportamiento legacy sobre los 5 TOs del subset")
    ap.add_argument("--version-e0", default=VERSION_E0_LEGADA,
                    choices=VERSIONES_E0,
                    help="versión de E0 (U-R2-CODIGO); la legada reproduce "
                         "la salida sellada byte a byte")
    args = ap.parse_args()
    if args.salida is None:
        if args.version_e0 == VERSION_E0_R2:
            ap.error("--version-e0 e0-r2 exige --salida explícita (M, U-R2-CODIGO)")
        args.salida = str(Path(__file__).parent / "salida")
    man = None
    if args.manifiesto:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import manifiesto_corpus
        man = manifiesto_corpus.cargar(Path(args.manifiesto))
    conteos = correr(Path(args.salida), manifiesto=man, version_e0=args.version_e0)
    print(json.dumps(conteos, ensure_ascii=False, indent=1))
