"""Selftest de E0: determinismo, cero pérdida de texto y tests de aceptación.

Uso: python3 selftest_e0.py [--dir-a DIR] [--dir-b DIR]

Sin argumentos corre el pipeline DOS veces en directorios temporales del
scratchpad de la sesión (o de sistema) y compara sha256 archivo por archivo;
después corre los tests de aceptación T4 sobre la primera corrida.

Tests de aceptación (casos reales documentados del proyecto):
  a) ext 3.9 entero: chunks 3.9.1–3.9.5 presentes, tope 'USD 200' en 3.9.1,
     y 3.9 NO es chunk terminal (es contenedor: título+intro+cierre en herencia).
  b) herencia de chapeau: el plazo '20 (veinte) días hábiles' del encabezado sin
     numerar del 7.6 de ext viaja en la herencia de TODOS los chunks 7.6.x;
     los cierres sin numerar del 2.7 de ext (cómputo a límites + declaración
     jurada) viajan en la herencia de TODOS los chunks 2.7.x.
  c) cla 1.1, cla 4.5 y ext 9.2: el cuerpo SÍ los contiene (labels reales en el
     PDF, verificados contra páginas 4, 15 y 123). El test es que existen como
     chunks CON contenido sustantivo (no cáscaras fabricadas) y con el título
     que el índice anuncia. NOTA: el mandato de la unidad esperaba verlos como
     divergencia 'anunciado sin cuerpo'; esa expectativa proviene de RX-04, que
     describe el output del chunker v1 (que los absorbía en vecinos), no el PDF.
     La contradicción se reporta; el archivo del repo (docs/backlog_reextraccion.md,
     RX-04: 'Su texto está en el corpus … pero no existe como pasaje con nombre')
     respalda esta lectura.
  d) ric: la divergencia de la Sección 3 capturada — el índice anuncia 3.2
     'Modelo de información' sin cuerpo propio; el cuerpo lo rinde como 3.1.4.
  e) tablas: cuadros de ponderadores de cap (2.12.2.4, 2.13) y cuadros de
     partidas de ric (3.1.4, 7.2) flaggeados contenido_tabular.

Tests de mini-chunks (enmienda 01 §2.a, ver e0_lib):
  i) determinismo y criterio: 286 mini-chunks en los 5 TOs (pro: 13), ids
     <to>::<unidad>::<rol>[::<n>] únicos, sha256 propio correcto, herencia
     solo de tramos encabezado, provenance (unidad) = unidad de origen;
     cero mini-chunks de rol encabezado (los títulos puros no materializan);
     el intro de 1.144 chars del 7.6 de ext (el 'encabezado sin numerar' del
     INFORME §6.b, tipo intro en la salida real) SÍ materializa; el intro
     normativo de una línea del 2.7 de pro SÍ materializa (la letra del
     criterio, no la heurística de escala); terminales byte-idénticos a la
     emisión sin minis (mismo contenido, minis interleaved); conteos con
     mini_chunks y censo-oráculo sin cambios.

Tests de la corrección post-calibración (reglas 1 y 2, ver e0_lib):
  f) regla 1 — continuidad de enumeración: los acápites vii)–x) de pro
     2.3.1.1 salen en su texto PROPIO y la herencia de 2.3.1.2–2.3.1.4 ya no
     los porta; el registro de reasignaciones contiene exactamente ese caso.
  g) regla 2 — cero fronteras de segmento intra-palabra en los 5 TOs
     (detector de e0_lib._clasificar_frontera; exclusiones auditadas en
     correcciones.json).
  h) ric 4.4: la regla 1 no aplica (no hay continuidad de lista en esa
     costura) — cero reasignaciones en ric y el contenido de 4.4.3/4.4.4
     sigue, como limitación documentada, dentro del propio de 4.3.3.

Tests de S0 de U-SEG-OFICIAL (S0-2; solo la versión e0-r2, con los PDFs de la
partición, data/experiment/escalado_prep/pdfs/; diseño en
data/experiment/segmentacion_oficial_e0r2/s0_1/ y s0_1bis/):
  j) la versión legada no cambia: los parámetros nuevos de clasificar_paginas
     y parsear_cuerpo están apagados por default;
  k) un caso medido por regla, corriendo e0-r2 sobre nueve TOs: regla 1
     (garopt, «Sección N –»), 2 (ri_dsf, códigos de actividad que no son
     puntos), 3 (venliq, primera página de cuerpo; adfsp p. 3, índice por
     lista), 4 (ri_spi, marcador de letra), 7 (manori, reapertura del
     padre), T (snp_dd, tablas fundidas), 8 (manori, lista de la sección
     vetada), 9 (rdbcra, filas del catálogo) y la cobertura exacta;
  l) casos sintéticos de las reglas 5 (cola de título en la lista de
     páginas), 6 (partición por renglones en E0 y en E1, con la capacidad
     del tercer escalón) y 8 (detección de la lista y sus guardas);
  m) doble corrida de e0-r2 sobre dos de esos TOs, byte a byte igual.
Desde S0-3, el caso medido del acompañamiento T es snp_dd y el de la regla 7, manori: con el mecanismo 1 de S0-3
las tablas de ri_dcpc quedan en el cuerpo de 2.4 y 2.5 y T ya no actúa ahí, y ri_mmsef 2.2 no se cierra, así que
la regla 7 no tiene que reabrirlo (sus unidades no cambian).

Tests de S0-3 de U-SEG-OFICIAL (solo la versión e0-r2; diseño en
data/experiment/segmentacion_oficial_e0r2/s0_3/):
  n) la versión legada no cambia: los parámetros de los mecanismos están apagados por default;
  o) casos sintéticos de cada forma: 1a (y sus dos guardas), 1b, 2 (a, b y c), 3 y 5 (a, b, la cola real y el
     inciso, c);
  p) un caso medido por mecanismo, corriendo e0-r2 sobre nueve TOs: 1a (ri_dcpc, nmcief), 2a (seggar), 2c
     (ri_tar), 3 (ri2_ae), 4a de S0-4 (seguef, que era el caso del mecanismo 4), 5a (fimipyme), 5b (ri2_ci) y 5c
     (ri_ai), y la cobertura exacta.
El mecanismo 4 de S0-3 no está desde S0-4 (lo reemplazan las reglas 4a y 4b).

Tests de S0-4 de U-SEG-OFICIAL (solo la versión e0-r2; diseño en
data/experiment/segmentacion_oficial_e0r2/s0_4/):
  q) la versión legada no cambia: los parámetros de las reglas de S0-4 están apagados por default, y las listas de
     TOs son las del diseño (sub-documento sin ri_tsa ni ri2_pm; 4a y 4b fuera de los diez TOs de la tanda 0);
  r) casos sintéticos: la detección de sub-documentos (anexo, parte, régimen, formulario y circular, con sus
     guardas: el anexo repetido, la serie de letras, la parte suelta, la continuación de un formulario y la
     circular suelta), la lectura con sub-documentos (prefijo, numeración desde cero y herencia del rótulo), la
     guarda de columna dentro del sub-documento, la raíz mayor que MAX_RAIZ dentro del sub-documento (sdmax, de
     S0-4a-bis), 4a, 4b (con su guarda del verbo) y los apartados; y las reglas de S0-4a-ter: el régimen de la página
     1 (sdr1), los apartados de letra con raíces numéricas (apl), el sub-documento de letra (sdl), la herencia de su
     rótulo (sdlh, con sdl y sin ella) y el rótulo «X.n.» con la letra vigente (sdla);
  s) un caso medido por regla, corriendo e0-r2 sobre ocho TOs: sub-documento (ri_sef, nmcief, ri_ccna,
     ri_icpipsp, ri_cc: los cinco casos de prueba del FRENO S0-3), sdg3 (nmcief), sdmax (ri_ccna, ítems 31 a 40 del
     Anexo III; y ri_sef, cuyos códigos 101 a 126 no son sucesores), sdr1 y apl (ri_oc), sdl, sdlh y sdla (ri_ccna,
     Anexo III), 4b (efemin), apartados (ri_ai), y la cobertura exacta.
Desde S0-4 cambian dos casos medidos de etapas anteriores: el de la regla 4 cuenta 93 unidades de ri_spi (4b retira
las intros de un renglón de B.1 y B.3) y el de 1a en nmcief lee nmcief::A2::3.2.1 (el punto es del Anexo II). Desde
S0-4a-ter, el caso medido de sdmax lee los ítems 31 a 40 en el sub-documento de letra (ri_ccna::D1A3L2::S31…).
Desde S0-5a cambian cuatro casos medidos de etapas anteriores: ri_spi cuenta 92 unidades (R5-c quita los chapeaux de
SB y SC, que eran la segunda línea de su título, y R5-a abre ri_spi::C.1::cierre); ri_ccna, 159 (R5-c quita cinco
chapeaux), y su lista B, 47 unidades (sin los chapeaux de S26 y S29); ri_oc, 187 (R5-a abre los cierres de B.1, B.2 y
B.3, que heredan sus ítems, y R5-a′ abre ri_oc::Sbloque1 en lugar de ri_oc::SC::cierre).

Tests de S0-5a de U-SEG-OFICIAL (solo la versión e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_5/):
  t) la versión legada no cambia: los parámetros de las seis reglas están apagados por default, y las listas de TOs
     son las del mandato (R5-a′ en ri_oc, R5-b en snp_dd y snp_cheq, R5-e en ri_ccna, ninguna en la tanda 0);
  u) casos sintéticos: R5-a (el cierre al margen y su caso negativo), R5-a′ (el bloque nuevo), R5-b (las tres
     condiciones, la cadena, el rótulo seguido de otro, la otra página y el número de la unión), R5-c (las condiciones
     a a d y el chapeau de verdad), R5-d (la remisión, la enumeración con «y» y el encabezado en la columna de sus
     hermanos) y R5-e (las letras repartidas entre dos unidades, y la cobertura);
  v) un caso medido por regla, corriendo e0-r2 sobre 25 TOs: los 9 casos del mecanismo 1 y los 27 correctos del 1.16
     (R5-a), el bloque de validaciones de ri_oc (R5-a′), las uniones de snp_dd y snp_cheq (R5-b), 8 de los 9 títulos
     de dos renglones y los 4 chapeaux de verdad (R5-c; manual queda fuera de esta corrida por su tamaño), ri_rml y
     snp_tr con los 4 encabezados de verdad (R5-d), el rótulo vertical de ri_ccna (R5-e), y la cobertura exacta.

Tests de S0-5a-bis de U-SEG-OFICIAL (solo e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_5/bis/):
  t) además: los parámetros nuevos (`listas`, `excluir`, `rotulos_por_lista`) apagados por default, y las listas de
     R5-a por lista (43: 40 con los párrafos de S0-5a y 3 con un rango de renglones), de R5-f (ri_ccna 11, snp_cheq 1) y
     de R5-g (ri_oc, «3. Aclaraciones»);
  w) casos sintéticos (R5-a por lista: solo la lista dada; el rango exacto; el párrafo con un renglón de tabla no se
     mueve; R5-f: el rótulo pegado al texto en minúscula abre su punto, y el colgado de un padre dado; R5-g: la raíz
     más adentro que la columna de las raíces abre solo si está en la lista) y medidos, corriendo e0-r2 sobre 22 TOs:
     ri_rml 1.4.2 desde «Para el punto 1.4.1.»; los dos mixtos con el cierre igual, renglón por renglón, a la lista v2
     y el resto del ítem igual a S0-4b; ri_ccna 2.1.1 y 5.1; snp_cheq 3.3.6.2; ri_oc, la sección 3 con su título y S2
     sin ese renglón; las 14 listas que no se tocan, con el texto propio de S0-4b; los 87 rechazos por columna profunda
     de los 7 documentos fuera de la tanda 1, como en S0-4b; y cuatro tablas serializadas como en S0-4b.
Desde S0-5a-bis cambia un caso medido de etapas anteriores: ri_ccna cuenta 169 unidades (R5-f abre 11 puntos, 2.1.1
a 2.1.8, 5.1 y 8.1 de D1A1 y 5.1 de D1A2, y quita el chapeau de D1A1::S5, que era el texto de 5.1).

Tests de S0-6a de U-SEG-OFICIAL (solo e0-r2; diseño en data/experiment/segmentacion_oficial_e0r2/s0_6/). Las pruebas de
etapas anteriores (j a w) corren con las reglas de S0-6a apagadas (`_sin_s06`): prueban sus reglas, y las reglas por
lista que S0-6a reemplaza vuelven a correr; por eso ningún caso medido de etapas anteriores cambia.
  x) la versión legada: los parámetros de A a K apagados por default; las once reglas, la tanda 0 fuera por la misma
     lista de diez TOs y los reemplazos (C de R5-a, A de R5-a′, E de R5-g, H de R5-f en ri_ccna); A a K no corren en
     ningún TO de la tanda 0, y con S0-6a apagada las listas vuelven a correr;
  y) casos sintéticos de cada regla y lo que la nota dice que no hace (A: el renglón entre la madre y sus hijos
     numerados, la fila de tabla; B: el título que entra en un renglón; C: el párrafo en la columna del texto del ítem
     o más adentro; E: la raíz que no sucede y la fila con huecos; G: sin el renglón de los puntos; H: el que no
     continúa la numeración; I: sin recuadro de dos columnas; K: el código que no es el último renglón de la página);
  z) un caso positivo por regla, de las 40 filas, corriendo e0-r2 sobre los TOs de TOS_S06; los reemplazos (E da el
     resultado de R5-g, H abre los rótulos de R5-f en ri_ccna, A el de R5-a′); la aceptación de R5-e actualizada por K;
     los negativos del §4 (NEGATIVOS_LEIDAS_S06: las unidades leídas en S1-ter de esos TOs, de corte y herencia
     correctos, conservan su corte y su herencia, cada una con su ficha de origen); la cobertura exacta; y la fila de la
     tanda 0 (E2-055, polcre) con la exclusión apagada solo ahí, sin tocar el camino de la salida.
Tests de S0-6a-bis (diseño en data/experiment/segmentacion_oficial_e0r2/s0_6/bis/):
  x) además: los parámetros de L (`indice_l`), M (`raiz0_solo_titulo_m`) y de las listas fijas de C, apagados por default;
     las trece reglas; R5-a por lista que queda con C (LISTAS_R5A_S0_6, ocho listas de LISTAS_R5A_S0_5); M no corre
     donde los sub-documentos son de S0-4;
  y′) casos sintéticos: C no saca un grupo si un párrafo no comparte columna ni el párrafo al que sigue una tabla, y mide
     el párrafo por su segundo renglón; A no abre divisiones en la carátula; L veta los rótulos de un índice cuyos
     títulos reaparecen, y el cuerpo vuelve a empezar en 1;
  z) además: L en el Anexo IV de nmaeef (E1-008), M en el Anexo III de ri2_ae (E2-002), R5-a por lista en ri_oc B.1 y
     ri_spi C.1 (E2-098, E2-058), A sin divisiones en la carátula de ri_ii_31_12_19, y los negativos del §4 de esta etapa
     (las leídas correctas de los TOs de TOS_S06, entre ellos los de los grupos que empeoraban en S0-6a).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import correr_e0

AQUI = Path(__file__).parent

RESULTADOS: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, ok, detalle))
    print(f"  [{'PASS' if ok else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""))


def cargar(d: Path, nombre: str):
    return json.loads((d / nombre).read_text(encoding="utf-8"))


def test_determinismo(dir_a: Path, dir_b: Path) -> None:
    print("== determinismo (dos corridas → sha idénticos)")
    sha_a = correr_e0.shas_salida(dir_a)
    sha_b = correr_e0.shas_salida(dir_b)
    check("mismos archivos de salida", set(sha_a) == set(sha_b),
          f"{len(sha_a)} archivos")
    distintos = [n for n in sha_a if sha_a[n] != sha_b.get(n)]
    check("sha256 idénticos archivo por archivo", not distintos,
          f"difieren: {distintos}" if distintos else f"{len(sha_a)}/{len(sha_a)} iguales")


def test_cobertura(d: Path) -> None:
    print("== cero pérdida de texto (cobertura por línea + suma de chars)")
    cob = cargar(d, "cobertura.json")
    for to, c in cob.items():
        check(f"cobertura exacta {to}", c["cobertura_exacta"],
              f"{c['lineas_en_estructura']}/{c['lineas_contenido_parseadas']} líneas, "
              f"{c['lineas_duplicadas']} duplicadas, {c['lineas_huerfanas']} huérfanas")
    # suma de chars: el texto de la estructura reconstruye el contenido del cuerpo
    for to in ("cap", "cla", "ext", "pro", "ric"):
        est = cargar(d, f"estructura_{to}.json")
        def chars_nodo(n):
            total = len(f"{n['numero']}. {n['titulo']}") if n["tipo"] == "punto" else 0
            total += sum(s["chars"] for s in n["segmentos"])
            return total + sum(chars_nodo(h) for h in n["hijos"])
        total = sum(chars_nodo(s) for s in est["secciones"])
        check(f"chars en estructura {to} > 0 y serializados", total > 0, f"{total:,} chars")


def test_t4(d: Path) -> None:
    print("== T4(a) ext 3.9 entero")
    # T4 habla de chunks TERMINALES; desde la enmienda 01 los archivos traen
    # además mini-chunks (que comparten `unidad` con su punto de origen) — se
    # filtran acá y se testean aparte en test_minichunks.
    ext = [c for c in cargar(d, "chunks_ext.json") if c["tipo"] != "mini_chunk"]
    por_unidad = {c["unidad"]: c for c in ext}
    esperados = [f"3.9.{i}" for i in range(1, 6)]
    check("chunks 3.9.1–3.9.5 presentes", all(u in por_unidad for u in esperados),
          str([u for u in esperados if u in por_unidad]))
    check("'USD 200' en el texto propio de 3.9.1",
          "USD 200" in por_unidad.get("3.9.1", {}).get("texto", ""))
    check("3.9 no es chunk (es contenedor con herencia)", "3.9" not in por_unidad)
    her = por_unidad.get("3.9.1", {}).get("herencia", [])
    check("herencia de 3.9.1 trae intro y cierre del 3.9",
          any(t["unidad_origen"] == "3.9" and t["tipo"] == "intro" for t in her)
          and any(t["unidad_origen"] == "3.9" and t["tipo"] == "cierre" for t in her))

    print("== T4(b) herencia de chapeau (ext 7.6 y 2.7)")
    c76 = [c for c in ext if c["unidad"].startswith("7.6.")]
    check("hay chunks 7.6.x", len(c76) >= 6, f"{len(c76)} chunks")
    ok76 = all(any(t["unidad_origen"] == "7.6"
                   and "20 (veinte) días hábiles" in t["texto"]
                   for t in c["herencia"]) for c in c76)
    check("'20 (veinte) días hábiles' del encabezado del 7.6 viaja en la herencia "
          "de todos los 7.6.x", ok76)
    c27 = [c for c in ext if c["unidad"].startswith("2.7.")]
    check("hay chunks 2.7.1–2.7.4", sorted(c["unidad"] for c in c27) ==
          ["2.7.1", "2.7.2", "2.7.3", "2.7.4"])
    ok27 = all(any(t["unidad_origen"] == "2.7" and t["tipo"] == "cierre"
                   and "límites" in t["texto"] and "declaración jurada" in t["texto"]
                   for t in c["herencia"]) for c in c27)
    check("cierres sin numerar del 2.7 (cómputo a límites + DDJJ) viajan en la "
          "herencia de todos los 2.7.x", ok27)

    print("== T4(c) cla 1.1, cla 4.5, ext 9.2 (ver docstring: contradicción con "
          "el mandato, reportada)")
    cla = [c for c in cargar(d, "chunks_cla.json") if c["tipo"] != "mini_chunk"]
    cla_u = {c["unidad"]: c for c in cla}
    for u, titulo in [("1.1", "Criterio general"),
                      ("4.5", "Deudores que no deben ser objeto de clasificación")]:
        c = cla_u.get(u)
        check(f"cla {u} existe como chunk real (no cáscara)",
              c is not None and c["chars_propio"] > 200 and titulo in c["titulo"],
              f"{c['chars_propio']} chars" if c else "ausente")
    c92 = por_unidad.get("9.2")
    check("ext 9.2 existe como chunk real (no cáscara)",
          c92 is not None and c92["chars_propio"] > 200
          and "Entidad nominada" in c92["titulo"],
          f"{c92['chars_propio']} chars" if c92 else "ausente")
    div = cargar(d, "divergencias_indice_cuerpo.json")
    fabricados = [u for u in ("1.1", "4.5") if cla_u.get(u, {}).get("chars_propio", 0) <= 60]
    check("ningún chunk vacío fabricado para estos puntos", not fabricados)

    print("== T4(d) ric Sección 3: 3.2 anunciado sin cuerpo; el cuerpo lo rinde 3.1.4")
    anuncios = [x["numero"] for x in div["ric"]["anunciado_sin_cuerpo"]]
    check("ric 3.2 en anunciado_sin_cuerpo", "3.2" in anuncios, str(anuncios))
    ric = [c for c in cargar(d, "chunks_ric.json") if c["tipo"] != "mini_chunk"]
    ric_u = {c["unidad"]: c for c in ric}
    check("ric 3.1.4 'Modelo de información' existe como chunk",
          "3.1.4" in ric_u and "Modelo de información" in ric_u["3.1.4"]["titulo"])

    print("== T4(e) tablas flaggeadas")
    cap = [c for c in cargar(d, "chunks_cap.json") if c["tipo"] != "mini_chunk"]
    cap_u = {c["unidad"]: c for c in cap}
    for u in ("2.12.2.4", "2.13"):
        check(f"cap {u} (cuadro de ponderadores/CCF) flag contenido_tabular",
              cap_u.get(u, {}).get("flags", {}).get("contenido_tabular", False))
    for u in ("3.1.4", "7.2"):
        check(f"ric {u} (cuadro de partidas) flag contenido_tabular",
              ric_u.get(u, {}).get("flags", {}).get("contenido_tabular", False))


def test_correcciones(d: Path) -> None:
    print("== T6(f) regla 1: acápites vii)–x) en el propio de pro 2.3.1.1")
    pro = [c for c in cargar(d, "chunks_pro.json") if c["tipo"] != "mini_chunk"]
    pro_u = {c["unidad"]: c for c in pro}
    propio = pro_u["2.3.1.1"]["texto"]
    check("'vii)' en el texto propio de pro 2.3.1.1", "vii)" in propio)
    check("'Régimen de Transparencia' en el texto propio de pro 2.3.1.1",
          "Régimen de Transparencia" in propio)
    check("'x) Los restantes requisitos' en el texto propio de pro 2.3.1.1",
          "x) Los restantes requisitos" in propio)
    sin_acapites = all(
        "vii)" not in t["texto"] and "Régimen de Transparencia" not in t["texto"]
        for u in ("2.3.1.2", "2.3.1.3", "2.3.1.4")
        for t in pro_u[u]["herencia"])
    check("la herencia de 2.3.1.2–2.3.1.4 ya no porta los acápites", sin_acapites)
    corr = cargar(d, "correcciones.json")
    reasig = [(to, r) for to, dd in corr.items()
              for r in dd["reasignaciones_continuidad"]]
    check("toda reasignación de la regla 1 es pro 2.3.1→2.3.1.1 (caso conocido)",
          reasig and all(to == "pro" and r["padre"] == "2.3.1"
                         and r["destino"] == "2.3.1.1" for to, r in reasig),
          f"{len(reasig)} reasignaciones")

    print("== T6(g) regla 2: cero fronteras de segmento intra-palabra")
    for to in ("cap", "cla", "ext", "pro", "ric"):
        f = corr[to]["fronteras_intra_palabra"]
        check(f"fronteras intra-palabra {to}: {f['antes']} → 0",
              f["despues"] == 0, f"{len(f['lineas_corridas'])} líneas corridas")

    print("== T6(h) ric 4.4: regla 1 no aplica (limitación se mantiene)")
    check("cero reasignaciones en ric", not corr["ric"]["reasignaciones_continuidad"])
    ric = [c for c in cargar(d, "chunks_ric.json") if c["tipo"] != "mini_chunk"]
    ric_u = {c["unidad"]: c for c in ric}
    t433 = ric_u["4.3.3"]["texto"]
    check("contenido de 4.4.3/4.4.4 sigue en el propio de ric 4.3.3",
          "4.4.3. Riesgo de cambio" in t433 and "4.4.4." in t433)


def test_minichunks(d: Path) -> None:
    print("== T7(i) mini-chunks (enmienda 01 §2.a)")
    todos = {to: cargar(d, f"chunks_{to}.json") for to in ("cap", "cla", "ext", "pro", "ric")}
    minis = {to: [c for c in cs if c["tipo"] == "mini_chunk"] for to, cs in todos.items()}
    n_total = sum(len(m) for m in minis.values())
    check("286 mini-chunks en los 5 TOs (contraste con estimación 284 de la enmienda)",
          n_total == 286, f"{n_total} ({ {to: len(m) for to, m in minis.items()} })")
    check("pro emite 13 mini-chunks (== estimación de la enmienda)",
          len(minis["pro"]) == 13, str([m["id"] for m in minis["pro"]]))

    ids = [m["id"] for cs in minis.values() for m in cs]
    check("ids de mini-chunks únicos", len(ids) == len(set(ids)))
    import re as _re
    patron = _re.compile(r"^(cap|cla|ext|pro|ric)::[S0-9.]+::(chapeau_seccion|intro|intersticial|cierre)(::\d+)?$")
    malformados = [i for i in ids if not patron.match(i)]
    check("ids con forma <to>::<unidad>::<rol>[::<n>]", not malformados, str(malformados[:5]))
    check("cero mini-chunks de rol encabezado (títulos puros no materializan)",
          not any(m["rol_bloque"] == "encabezado" for cs in minis.values() for m in cs))

    import hashlib as _hl
    check("sha256_propio de cada mini = sha del texto del bloque",
          all(m["sha256_propio"] == _hl.sha256(m["texto"].encode()).hexdigest()
              for cs in minis.values() for m in cs))
    check("herencia de todo mini: solo tramos encabezado (títulos de la cadena)",
          all(t["tipo"] == "encabezado" for cs in minis.values()
              for m in cs for t in m["herencia"]))
    check("la unidad del mini es su unidad de origen (el id la contiene)",
          all(m["id"].split("::")[1] == m["unidad"] for cs in minis.values() for m in cs))

    m76 = [m for m in minis["ext"] if m["id"] == "ext::7.6::intro"]
    check("el bloque de 1.144 chars del 7.6 de ext materializa como intro",
          len(m76) == 1 and m76[0]["chars_propio"] == 1144
          and "20 (veinte) días hábiles" in m76[0]["texto"])
    m27 = [m for m in minis["pro"] if m["id"] == "pro::2.7::intro"]
    check("el intro normativo de UNA línea del 2.7 de pro materializa (letra del "
          "criterio, no la heurística de escala)",
          len(m27) == 1 and "sendos hipervínculos" in m27[0]["texto"])
    m231 = [m for m in minis["pro"] if m["id"] == "pro::2.3.1::intro"]
    check("pro::2.3.1::intro (norma de Caja de ahorros) materializa",
          len(m231) == 1 and "Caja de" in m231[0]["texto"])
    check("pro::S3::chapeau_seccion materializa",
          any(m["id"] == "pro::S3::chapeau_seccion" for m in minis["pro"]))

    inter = sorted(m["id"] for cs in minis.values() for m in cs
                   if m["rol_bloque"] == "intersticial")
    check("los 3 intersticiales de ext materializan (uno por segmento)",
          inter == ["ext::3.16.3::intersticial", "ext::4.2::intersticial",
                    "ext::7.9.3::intersticial"], str(inter))

    # interleaved documental: intro antes del primer hijo, cierre tras el último
    ids_pro = [c["id"] for c in todos["pro"]]
    check("emisión interleaved: pro::2.3.1::intro antes de pro::2.3.1.1 y "
          "pro::2.7::cierre después de pro::2.7.2",
          ids_pro.index("pro::2.3.1::intro") < ids_pro.index("pro::2.3.1.1")
          and ids_pro.index("pro::2.7::cierre") > ids_pro.index("pro::2.7.2"))

    conteos = cargar(d, "conteos.json")
    check("conteos: chunks = terminales + mini_chunks en los 5 TOs",
          all(c["chunks"] == c["chunks_terminales"] + c["mini_chunks"]
              for c in conteos.values()),
          str({to: (c["chunks_terminales"], c["mini_chunks"]) for to, c in conteos.items()}))


# ------------------------------------------- S0 de U-SEG-OFICIAL (e0-r2)

PDFS_PARTICION = AQUI.resolve().parents[1] / "escalado_prep" / "pdfs"
TOS_S0 = ("garopt", "ri_dsf", "venliq", "adfsp", "ri_spi", "ri_mmsef", "snp_dd", "manori", "rdbcra")


class _ManifiestoParticion:
    """Lo que `correr_e0.correr` lee de un manifiesto: ids, archivo y PDF (los de la partición)."""
    tiene_oraculo = False
    mapa_territorio = None

    def __init__(self, ids):
        self.ids = list(ids)

    def archivo_de(self, to: str) -> str:
        return f"{to}.pdf"

    def pdf_de(self, to: str) -> Path:
        return PDFS_PARTICION / f"{to}.pdf"


def _linea(texto: str, pagina: int, top: float, x0: float = 60.0, ngaps: int = 0):
    return correr_e0.E0.Linea(pagina=pagina, top=top, x0=x0, texto=texto, ngaps=ngaps,
                              ultimo_numerico=False, primer_codigo=False)


def _unidad(texto: str, uid: str = "x::S1", tipo: str = "seccion_sin_puntos") -> dict:
    return {"id": uid, "to": "x", "archivo": "x.pdf", "unidad": uid.split("::", 1)[1], "titulo": "t",
            "tipo": tipo, "paginas": [1], "texto": texto, "chars_propio": len(texto),
            "chars_completo": len(texto), "herencia": [], "flags": {}, "sha256_propio": "",
            "sha256_completo": ""}


def test_s0_legada() -> None:
    import inspect
    E0 = correr_e0.E0
    print("== j) S0 de U-SEG-OFICIAL: la versión legada no cambia")
    p = inspect.signature(E0.parsear_cuerpo).parameters
    nuevos = {"seccion_variante": False, "rotulos_r2": False, "marcador_letra": False, "reabrir_padre": False,
              "no_rotulos": frozenset(), "rotulos_fila": frozenset()}
    check("parsear_cuerpo: los parámetros de las reglas 1, 2, 4, 7, 8 y 9 apagados por default",
          all(p[k].default == v for k, v in nuevos.items()), str({k: p[k].default for k in nuevos}))
    q = inspect.signature(E0.clasificar_paginas).parameters
    check("clasificar_paginas: la regla 3 apagada por default", q["continuacion_con_titulo"].default is False)
    r = inspect.signature(E0.separar_encabezado_pie).parameters
    check("separar_encabezado_pie: la regla 1 apagada por default",
          r["seccion_variante"].default is False and r["seccion_abierta"].default is None)


def test_s0_casos(d: Path) -> None:
    print(f"== k) S0 de U-SEG-OFICIAL: un caso medido por regla (e0-r2 sobre {len(TOS_S0)} TOs)")
    correr_e0.correr(d, manifiesto=_ManifiestoParticion(TOS_S0), version_e0="e0-r2")
    ch = {to: cargar(d, f"chunks_{to}.json") for to in TOS_S0}
    ids = {to: [c["id"] for c in ch[to]] for to in TOS_S0}
    est = {to: cargar(d, f"estructura_{to}.json") for to in TOS_S0}

    def avisos(to: str, tipo: str) -> list:
        return [x for x in est[to]["avisos"] if x["tipo"] == tipo]

    check("regla 1: garopt abre «Sección 2 –» y sus puntos (garopt::2.1.1)",
          "garopt::2.1.1" in ids["garopt"], f"{len(ids['garopt'])} chunks")
    check("regla 2: ri_dsf no lee como puntos los códigos de actividad de la sección 10 (sin ri_dsf::10.1)",
          "ri_dsf::10.1" not in ids["ri_dsf"]
          and any(r["motivo"] == "fila_de_lista_de_codigos_r2" for r in est["ri_dsf"]["rechazos_header"]))
    check("regla 3: venliq recupera la primera página de cuerpo (venliq::1.1.1, sin chapeau de S1)",
          "venliq::1.1.1" in ids["venliq"] and "venliq::S1::chapeau_seccion" not in ids["venliq"])
    check("regla 3, ampliación: adfsp p. 3 (una lista entera de la regla 8) es índice: sin adfsp::S6",
          "adfsp::S6" not in ids["adfsp"] and "adfsp::6.1" in ids["adfsp"])
    # desde S0-4, la regla 4b junta al título el renglón que completa los de B.1 y B.3 y retira sus dos intros de un
    # renglón: 93 unidades (95 en S0-2 y S0-3); desde S0-5a, R5-c quita los chapeaux de SB y SC y R5-a abre
    # ri_spi::C.1::cierre: 92
    check("regla 4: ri_spi en 92 unidades por el marcador de letra (ri_spi::A.1.1)",
          len(ids["ri_spi"]) == 92 and "ri_spi::A.1.1" in ids["ri_spi"]
          and bool(avisos("ri_spi", "marcador_letra_r2")), f"{len(ids['ri_spi'])} unidades")
    # desde S0-3, el mecanismo 1a no cierra ri_mmsef 2.2 (su cuerpo está en la columna del rótulo) y la regla 7 ya
    # no actúa ahí; las unidades son las mismas. El caso medido de la reapertura pasa a manori 1.5 (p. 39)
    check("regla 7: manori reabre el padre (manori::1.5.2, aviso padre_reabierto_r2); ri_mmsef::2.2.1 sigue",
          "manori::1.5.2" in ids["manori"] and bool(avisos("manori", "padre_reabierto_r2"))
          and "ri_mmsef::2.2.1" in ids["ri_mmsef"])
    check("acompañamiento T: snp_dd funde tablas partidas en intersticiales",
          bool(avisos("snp_dd", "tabla_fundida_en_un_intersticial_r2")))
    vetos = [r for r in est["manori"]["rechazos_header"] if r["motivo"] == "lista_de_puntos_r8"]
    check("regla 8: manori veta los 10 rótulos de sus listas de sección (pp. 3 y 57) y 1.1.1 encuentra padre",
          len(vetos) == 10 and sorted({r["pagina"] for r in vetos}) == [3, 57] and "manori::1.1.1" in ids["manori"],
          f"{len(vetos)} vetos")
    cat = avisos("rdbcra", "filas_de_catalogo_r9")
    u = next((c for c in ch["rdbcra"] if c["id"] == "rdbcra::11.2.7"), None)
    check("regla 9: rdbcra ancla las 119 filas del catálogo (223 renglones) y acepta rdbcra::11.1.1",
          len(cat) == 1 and (cat[0]["filas"], cat[0]["ancladas"], cat[0]["renglones_movidos"]) == (119, 119, 223)
          and "rdbcra::11.1.1" in ids["rdbcra"])
    check("regla 9: rdbcra::11.2.7 lleva su fila entera, en el orden del PDF",
          u is not None and u["texto"] == "Operaciones de cambio en\n11.2.7. días y horarios no habilita- "
                                        "Alta 200 100\ndos al efecto.")
    cob = cargar(d, "cobertura.json")
    check("cobertura exacta en los nueve TOs", all(cob[to]["cobertura_exacta"] for to in TOS_S0))


def test_s0_sinteticos() -> None:
    E0 = correr_e0.E0
    print("== l) S0 de U-SEG-OFICIAL: casos sintéticos de las reglas 5, 6 y 8")
    check("regla 5: la lista de las 9 páginas de la cola de título estricta",
          correr_e0.COLA_TITULO_ESTRICTA_R5 == {"cirmo3": {19}, "cryl": {27}, "manori": {6}, "ri2_ci": {8, 9, 16, 24},
                                                "snp_cheq": {80}, "snp_mep": {19}})
    pag = [_linea("B.C.R.A.", 1, 30.0), _linea("Sección 3. Normas generales.", 1, 44.0),
           _linea("Las entidades deberán informar el saldo diario.", 1, 56.0)]
    _, _, sec_h = E0.separar_encabezado_pie(pag)
    _, _, sec_e = E0.separar_encabezado_pie(pag, cola_titulo_estricta=True)
    check("regla 5: con la cola estricta, un renglón que no continúa el título es texto de la norma",
          sec_h != sec_e and sec_e == "Sección 3. Normas generales.", f"{sec_h!r} / {sec_e!r}")
    check("regla 6: constantes (tercer escalón 27.214, partes por renglones 10.886, por ítems 13.091)",
          (correr_e0.CAPACIDAD_ESCALON_3_R6, correr_e0.OBJETIVO_PARTES_RENGLONES_R6,
           correr_e0.OBJETIVO_CHARS_PARTE) == (27214, 10886, 13091))
    renglon = "Las entidades financieras deberán cumplir con las disposiciones de esta sección y su anexo."
    grande = _unidad("Título de la sección\n" + "\n".join([renglon] * 330))
    chica = _unidad("Título\n" + "\n".join([renglon] * 220))
    p, info = correr_e0.particionar_por_corte(grande)
    check("regla 6 en E1: una unidad sin ítems sobre el tercer escalón se parte por renglones (partes de 10.886 o menos)",
          p is not None and info.get("renglones_r6") == "sin_items_y_sobre_el_tercer_escalon"
          and max(s["chars_propio"] for s in p) <= 10886, str([s["chars_propio"] for s in p] if p else None))
    p, info = correr_e0.particionar_por_corte(chica)
    check("regla 6 en E1: una unidad sin ítems bajo el tercer escalón no se parte (llega entera al tercer escalón)",
          p is None and info["motivo"] == "sin_items_detectables", str(len(chica["texto"])))
    items = ("Encabezado del punto\n1. Primer ítem corto.\n" + "\n".join([renglon] * 5)
             + "\n2. Segundo ítem largo.\n" + "\n".join([renglon] * 440)
             + "\n3. Tercer ítem corto.\n" + "\n".join([renglon] * 5))
    p, info = correr_e0.particionar_por_corte(_unidad(items, "x::1.1", "punto_terminal"))
    tam = [s["chars_propio"] for s in p] if p else []
    check("regla 6 en E1: solo se parte por renglones el ítem que pasa el tercer escalón",
          info.get("renglones_r6") == "parte_sobre_el_tercer_escalon" and len(tam) == 6
          and tam[0] == tam[-1] + 21 and max(tam[1:-1]) <= 10886, str(tam))
    out, rep = correr_e0.subdividir_unidades_grandes([grande], tope_herencia=correr_e0.TOPE_HERENCIA_E0_R2)
    check("regla 6 en E0 (e0-r2): una unidad sin ítems sobre el umbral se parte por renglones",
          len(out) == 3 and not rep["no_particionables"], str([c["chars_propio"] for c in out]))
    out, rep = correr_e0.subdividir_unidades_grandes([grande])
    check("regla 6 en E0 (legada): la misma unidad queda declarada sin partir",
          len(out) == 1 and rep["no_particionables"][0]["motivo"] == "sin_items_detectables")
    out, rep = correr_e0.subdividir_unidades_grandes([grande], no_partir=frozenset({"x::S1"}),
                                                     tope_herencia=correr_e0.TOPE_HERENCIA_E0_R2)
    check("regla 6 en E0: una unidad con tabla serializada no se parte (declarada)",
          len(out) == 1 and rep["no_particionables"][0]["motivo"] == "tabla_serializada")
    # regla 8: lista en la p. 1 cuyos números reaparecen con su título más adelante, con texto entre punto y punto
    titulos = ["Alcance general.", "Requisitos de información.", "Plazos de presentación."]
    p1 = [_linea("Sección 1. Disposiciones.", 1, 30.0)] + [
        _linea(f"1.{i + 1}. {t}", 1, 50.0 + 14 * i, x0=80.0) for i, t in enumerate(titulos)]
    cuerpo = []
    for i, t in enumerate(titulos):
        cuerpo += [_linea(f"1.{i + 1}. {t}", 2, 50.0 + 70 * i, x0=80.0)] + [
            _linea("Texto de la norma que desarrolla el punto con su contenido propio.", 2, 64.0 + 70 * i + 12 * k)
            for k in range(4)]
    roles = [E0.ROL_CUERPO, E0.ROL_CUERPO]
    check("regla 8: detecta la lista de la p. 1 (sus tres rótulos)",
          E0.lineas_de_listas_r8([p1, cuerpo], roles) == frozenset((1, 50.0 + 14 * i) for i in range(3)))
    otro = [_linea(f"1.{i + 1}. {t}", 2, 50.0 + 70 * i, x0=80.0) for i, t in
            enumerate(["Otra cosa.", "Distinto título.", "Nada que ver."])]
    check("regla 8: si los títulos de la reaparición son otros, no es una lista",
          E0.lineas_de_listas_r8([p1, otro], roles) == frozenset())
    check("regla 3, ampliación: la página que es entera la lista pasa a índice; la de cuerpo, no",
          E0.paginas_indice_r8([p1, cuerpo], roles) == [E0.ROL_INDICE, E0.ROL_CUERPO])


TOS_S03 = ("nmcief", "seggar", "ri_tar", "ri2_ae", "fimipyme", "ri2_ci", "ri_ai", "seguef")


def test_s03_legada() -> None:
    import inspect
    E0 = correr_e0.E0
    print("== n) S0-3 de U-SEG-OFICIAL: la versión legada no cambia")
    p = inspect.signature(E0.parsear_cuerpo).parameters
    check("parsear_cuerpo: los mecanismos 1, 2 y 5 apagados por default",
          all(p[k].default == frozenset() for k in ("formas_m1", "formas_m2", "formas_m5")))
    r = inspect.signature(E0.separar_encabezado_pie).parameters
    check("separar_encabezado_pie: las tres formas del mecanismo 5 apagadas por default",
          not any(r[k].default for k in ("cierre_m5", "cola_m5", "zona6_m5")))
    q = inspect.signature(E0.lineas_de_listas_r8).parameters
    s = inspect.signature(E0.construir_chunks).parameters
    check("lineas_de_listas_r8: el mecanismo 3 apagado por default; construir_chunks ya no tiene el mecanismo 4",
          q["forma4_m3"].default is False and "titulo_texto_m4" not in s)


def _parse(paginas, **kw):
    E0 = correr_e0.E0
    roles = [E0.ROL_CUERPO] * len(paginas)
    res = E0.parsear_cuerpo("x", "x.pdf", paginas, roles, mayusculas_repetidas=set(), pie_desde_version=True, **kw)
    return res, E0.construir_chunks(res)


def _texto(chunks, uid):
    return next((c["texto"] for c in chunks if c["id"] == uid), None)


def test_s03_sinteticos() -> None:
    E0 = correr_e0.E0
    print("== o) S0-3 de U-SEG-OFICIAL: casos sintéticos de los cinco mecanismos")
    largo = "Texto de la norma que corre en la columna del rótulo y ocupa un renglón entero de prosa."
    # mecanismo 1, forma a: diseño plano (rótulos y cuerpo en la misma columna)
    p = [_linea("Sección 1. Criterios generales.", 1, 30.0),
         _linea("1.1. Criterios de imputación.", 1, 50.0), _linea(largo, 1, 64.0),
         _linea("1.1.1. Baja en cuentas.", 1, 90.0), _linea(largo, 1, 104.0), _linea(largo, 1, 118.0),
         _linea("1.1.2. Medición.", 1, 140.0), _linea(largo, 1, 154.0)]
    _, ch_h = _parse([p])
    _, ch_a = _parse([p], formas_m1=frozenset({"a"}))
    check("mecanismo 1a: la prosa que sigue al rótulo en su columna es cuerpo del punto (x::1.1.1, x::1.1.2)",
          _texto(ch_a, "x::1.1.1") == "1.1.1. Baja en cuentas.\n" + largo + "\n" + largo
          and _texto(ch_a, "x::1.1.2") == "1.1.2. Medición.\n" + largo
          and _texto(ch_h, "x::1.1.1") == "1.1.1. Baja en cuentas.",
          str([c["id"] for c in ch_a]))
    # guarda: lista de ítems de un renglón; la prosa que sigue al último es el cierre del padre
    q = [_linea("Sección 1. Aportes.", 1, 30.0), _linea("1.1. Aportes de capital.", 1, 50.0),
         _linea(largo, 1, 64.0), _linea("1.1.1. títulos valores públicos nacionales;", 1, 90.0),
         _linea("1.1.2. instrumentos de regulación monetaria;", 1, 104.0),
         _linea("1.1.3. depósitos de la entidad.", 1, 118.0), _linea(largo, 1, 132.0)]
    _, ch_q = _parse([q], formas_m1=frozenset({"a"}))
    check("mecanismo 1a, guarda: tras una lista de renglones sueltos, la prosa sigue siendo el cierre del padre",
          _texto(ch_q, "x::1.1::cierre") == largo and _texto(ch_q, "x::1.1.3") == "1.1.3. depósitos de la entidad.")
    # guarda: sangría colgante (el cuerpo de un hermano corre más adentro que su rótulo)
    g = [_linea("Sección 2. Excepciones.", 1, 30.0), _linea("2.7. Excepción.", 1, 50.0, x0=60.0),
         _linea(largo, 1, 64.0, x0=80.0),
         _linea("2.7.1. El ejercicio de la excepción se efectúe dentro del plazo previsto para la", 1, 90.0, x0=80.0),
         _linea("liquidación de los fondos.", 1, 104.0, x0=100.0),
         _linea("2.7.2. La utilización de este mecanismo deberá resultar neutral.", 1, 118.0, x0=80.0),
         _linea(largo, 1, 132.0, x0=80.0)]
    _, ch_g = _parse([g], formas_m1=frozenset({"a"}))
    check("mecanismo 1a, guarda: con sangría colgante, la prosa a la altura del rótulo es del padre (cierre del 2.7)",
          _texto(ch_g, "x::2.7::cierre") == largo)
    # mecanismo 1, forma b: el cuerpo del punto corre a la izquierda de su rótulo
    b = [_linea("Sección 7. Diseño de registros.", 1, 30.0), _linea("7.1. Registros.", 1, 50.0, x0=40.0),
         _linea(largo, 1, 64.0, x0=56.0), _linea("7.1.1. Registro de cabecera.", 1, 90.0, x0=64.0),
         _linea("Campo 1 2 3", 1, 104.0, x0=48.0), _linea("1. Identificador de registro", 1, 118.0, x0=42.0),
         _linea(largo, 1, 132.0, x0=57.0)]
    _, ch_b0 = _parse([b])
    _, ch_b = _parse([b], formas_m1=frozenset({"b"}))
    check("mecanismo 1b: un punto con el cuerpo a la izquierda de su rótulo no devuelve prosa al padre",
          largo in (_texto(ch_b, "x::7.1.1") or "") and largo not in (_texto(ch_b0, "x::7.1.1") or ""))
    # mecanismo 2 (modo sin raíz): las tres formas de la línea que abre una raíz
    m2 = [_linea("1. Fideicomiso accionista.", 1, 50.0, x0=70.0), _linea(largo, 1, 64.0, x0=90.0),
          _linea("2.Integración de los aportes.", 1, 90.0, x0=70.0), _linea(largo, 1, 104.0, x0=90.0),
          _linea("3- DISPOSICIONES FINALES", 1, 130.0, x0=70.0), _linea(largo, 1, 144.0, x0=90.0),
          _linea("4. CUADRO 1 – DATOS DE LAS CUENTAS", 1, 170.0, x0=85.0), _linea(largo, 1, 184.0, x0=90.0)]
    r0, _ = _parse([m2], modo_sin_raiz=True)
    r2, _ = _parse([m2], modo_sin_raiz=True, formas_m2=frozenset({"a", "b", "c"}))
    check("mecanismo 2: sin las formas, la raíz 1 sola; con a, b y c, las raíces 1 a 4",
          [s.numero for s in r0.secciones] == ["1"] and [s.numero for s in r2.secciones] == ["1", "2", "3", "4"],
          f"{[s.numero for s in r0.secciones]} / {[s.numero for s in r2.secciones]}")
    check("mecanismo 2: cada raíz nueva declarada por su forma (aviso raiz_m2)",
          [(a["numero"], a["forma"]) for a in r2.avisos if a["tipo"] == "raiz_m2"] == [("2", "a"), ("3", "b"), ("4", "c")])
    # mecanismo 3: lista de rótulos de un nivel (índice de un anexo) y su página de cuerpo
    titulos = ["Designación.", "Condiciones para el ejercicio.", "Exclusión del registro.", "Baja del registro."]
    p1 = [_linea("DISPOSICIONES GENERALES", 1, 40.0)] + [
        _linea(f"{i + 1}. {t.rstrip('.')}", 1, 60.0 + 20 * i, x0=76.0, ngaps=1) for i, t in enumerate(titulos)]
    p2 = []
    for i, t in enumerate(titulos):
        p2 += [_linea(f"{i + 1}. {t}", 2, 50.0 + 70 * i, x0=76.0)] + [
            _linea(largo, 2, 64.0 + 70 * i + 12 * k, x0=90.0) for k in range(4)]
    roles = [E0.ROL_CUERPO, E0.ROL_CUERPO]
    check("mecanismo 3: sin la cuarta forma, la lista de un nivel no se detecta; con ella, sí, y la página es índice",
          E0.lineas_de_listas_r8([p1, p2], roles) == frozenset()
          and E0.lineas_de_listas_r8([p1, p2], roles, forma4_m3=True) == frozenset((1, 60.0 + 20 * i) for i in range(4))
          and E0.paginas_indice_r8([p1, p2], roles, forma4_m3=True) == [E0.ROL_INDICE, E0.ROL_CUERPO])
    # mecanismo 5: la zona de encabezado
    enc = [_linea("LÍNEA DE FINANCIAMIENTO", 1, 72.0, x0=220.0), _linea("B.C.R.A. PRODUCTIVA", 1, 85.0, x0=83.0),
           _linea("Sección 1. Entidades alcanzadas.", 1, 98.0, x0=139.0),
           _linea("Las entidades financieras que estén comprendidas en el Grupo A conforme a lo previsto en la",
                  1, 124.0, x0=76.0),
           _linea("Sección 4. de las normas sobre autoridades, para lo cual el indicador del", 1, 137.0, x0=76.0),
           _linea("punto 4.1. de esas normas deberá computarse.", 1, 150.0, x0=76.0)]
    c0, _, _ = E0.separar_encabezado_pie(enc, mayusculas_repetidas=set())
    ca, _, _ = E0.separar_encabezado_pie(enc, mayusculas_repetidas=set(), cierre_m5=True)
    check("mecanismo 5a: una segunda línea de sección que no se repite no cierra el encabezado",
          c0[0].texto.startswith("punto 4.1.") and ca[0].texto.startswith("Las entidades financieras"))
    bc = [_linea("REGIMEN INFORMATIVO", 1, 72.0, x0=259.0), _linea("B.C.R.A. CAJAS DE CRÉDITO", 1, 87.0, x0=91.0),
          _linea("Sección 3. Capitales Mínimos", 1, 103.0, x0=152.0),
          _linea("4. Facilidades Otorgadas por el B.C.R.A.", 1, 128.0, x0=76.0),
          _linea("4.1. Normas de procedimiento", 1, 166.0, x0=90.0)]
    b0, _, _ = E0.separar_encabezado_pie(bc, mayusculas_repetidas=set())
    ba, _, _ = E0.separar_encabezado_pie(bc, mayusculas_repetidas=set(), cierre_m5=True)
    check("mecanismo 5a: después de la sección, un renglón con «B.C.R.A.» que no se repite es texto",
          b0[0].texto.startswith("4.1.") and ba[0].texto.startswith("4. Facilidades"))
    cola = [_linea("NORMAS MINIMAS", 1, 76.0, x0=143.0), _linea("B.C.R.A. DE CAMBIO", 1, 89.0, x0=83.0),
            _linea("Sección 1. Aspectos generales", 1, 102.0, x0=139.0),
            _linea("abordando las expectativas, las responsabilidades de los indivi-", 1, 116.0, x0=184.0),
            _linea("duos y grupos, teniendo en cuenta la clasificación y confidenciali-", 1, 130.0, x0=184.0),
            _linea("dad de la información.", 1, 144.0, x0=184.0)]
    k0, _, _ = E0.separar_encabezado_pie(cola, mayusculas_repetidas=set())
    kb, _, _ = E0.separar_encabezado_pie(cola, mayusculas_repetidas=set(), cola_m5=True)
    check("mecanismo 5b: un renglón en la columna del cuerpo, seguido de otro a interlineado, no es cola del título",
          k0[0].texto.startswith("dad de") and kb[0].texto.startswith("abordando"))
    real = [_linea("TEXTO ORDENADO", 1, 76.0, x0=200.0), _linea("B.C.R.A.", 1, 89.0, x0=83.0),
            _linea("Sección 5. Garantía de los depósitos y Superintendencia de Entidades Financieras y", 1, 102.0,
                   x0=139.0), _linea("Cambiarias.", 1, 115.0, x0=139.0),
            _linea("5.1. Depósitos comprendidos.", 1, 140.0, x0=76.0)]
    _, _, sec_r = E0.separar_encabezado_pie(real, mayusculas_repetidas=set(), cola_m5=True)
    inc = [_linea("B.C.R.A.", 1, 89.0, x0=83.0), _linea("Sección 7. Diseño de registros", 1, 102.0, x0=139.0),
           _linea("ii) Cabecera de lote", 1, 115.0, x0=175.0), _linea(largo, 1, 140.0, x0=76.0)]
    i0, _, _ = E0.separar_encabezado_pie(inc, mayusculas_repetidas=set())
    ib, _, _ = E0.separar_encabezado_pie(inc, mayusculas_repetidas=set(), cola_m5=True)
    check("mecanismo 5b: la cola real del título sigue siéndolo; un inciso «ii)» no es cola",
          sec_r.endswith("Cambiarias.") and i0[0].texto == largo and ib[0].texto == "ii) Cabecera de lote")
    ai = [_linea("REGIMEN INFORMATIVO CONTABLE MENSUAL", 1, 80.0, x0=242.0),
          _linea("6. TEXTO ORDENADO DEL REGIMEN INFORMATIVO", 1, 93.0, x0=189.0),
          _linea("SOBRE LA RELACION PARA LOS ACTIVOS INMOVILIZADOS", 1, 105.0, x0=183.0),
          _linea("B.C.R.A.", 1, 108.0, x0=98.0), _linea("CONCEPTOS. (R.I. – A.I.)", 1, 118.0, x0=302.0),
          _linea("Sección 2. Instrucciones generales", 1, 131.0, x0=172.0),
          _linea("2.1. La información tendrá frecuencia mensual.", 1, 198.0, x0=112.0)]
    _, _, s0 = E0.separar_encabezado_pie(ai, mayusculas_repetidas=set())
    zc, _, sc = E0.separar_encabezado_pie(ai, mayusculas_repetidas=set(), zona6_m5=True)
    check("mecanismo 5c: con el recuadro en los cinco primeros renglones, la sección del sexto se abre",
          s0 is None and sc == "Sección 2. Instrucciones generales" and zc[0].texto.startswith("2.1."))


def test_s03_casos(d: Path) -> None:
    print(f"== p) S0-3 de U-SEG-OFICIAL: un caso medido por mecanismo (e0-r2 sobre {len(TOS_S03)} TOs y ri_dcpc)")
    correr_e0.correr(d, manifiesto=_ManifiestoParticion(TOS_S03 + ("ri_dcpc",)), version_e0="e0-r2")
    ch = {to: cargar(d, f"chunks_{to}.json") for to in TOS_S03 + ("ri_dcpc",)}

    def txt(to: str, uid: str) -> str:
        return next((c["texto"] for c in ch[to] if c["id"] == uid), "")

    check("mecanismo 1a: ri_dcpc::3.1.1 lleva su cuerpo («A los fines de aplicar…»)",
          "A los fines de aplicar las disposiciones de baja" in txt("ri_dcpc", "ri_dcpc::3.1.1"))
    # desde S0-4, el punto es del Anexo II de nmcief (regla de sub-documento): nmcief::A2::3.2.1
    check("mecanismo 1a: nmcief::A2::3.2.1 lleva su cuerpo («El sistema contable constituye…»)",
          "El sistema contable constituye" in txt("nmcief", "nmcief::A2::3.2.1"))
    check("mecanismo 2a: seggar abre la sección 4 («4.Integración de los aportes.») y el cierre de S3 ya no la lleva",
          "Los aportes normales" in txt("seggar", "seggar::S4")
          and "Integración" not in txt("seggar", "seggar::S3::cierre"))
    check("mecanismo 2c: ri_tar abre los cuadros (ri_tar::2.1.1) y ri_tar::1.1 ya no se lleva el documento",
          bool(txt("ri_tar", "ri_tar::2.1.1")) and "CUADRO 1" not in txt("ri_tar", "ri_tar::1.1"))
    pies = cargar(d, "pies_ri2_ae.json")
    check("mecanismo 3: ri2_ae p. 3 es índice y ri2_ae::S1 es la sección 1 del cuerpo",
          next(f["rol"] for f in pies["paginas_detalle"] if f["pagina"] == 3) == "indice"
          and "deberán informar a la Gerencia de Control" in txt("ri2_ae", "ri2_ae::S1"))
    check("regla 4a de S0-4 (el caso del mecanismo 4 de S0-3): seguef::2.1.6::intro empieza en su rótulo",
          txt("seguef", "seguef::2.1.6::intro").startswith("2.1.6. Cuando se decida"))
    check("mecanismo 5a: fimipyme::S1 lleva el comienzo de su párrafo («Las entidades financieras que estén…»)",
          "Las entidades financieras que estén comprendidas" in txt("fimipyme", "fimipyme::S1"))
    check("mecanismo 5b: ri2_ci::1.1.1.4 lleva sus dos renglones («abordando las expectativas…»)",
          "abordando las expectativas" in txt("ri2_ci", "ri2_ci::1.1.1.4"))
    check("mecanismo 5c: ri_ai abre la sección 2 (ri_ai::2.1) y ri_ai::1.2.2 ya no la lleva",
          bool(txt("ri_ai", "ri_ai::2.1")) and "Sección 2." not in txt("ri_ai", "ri_ai::1.2.2"))
    cob = cargar(d, "cobertura.json")
    check("cobertura exacta en los nueve TOs", all(cob[to]["cobertura_exacta"] for to in TOS_S03 + ("ri_dcpc",)))


TOS_S04 = ("ri_sef", "nmcief", "ri_ccna", "ri_icpipsp", "ri_cc", "ri_ai", "efemin", "ri_oc")
TOS_TANDA0 = frozenset({"cap", "cla", "ext", "pro", "ric", "ctacte", "lingob", "polcre", "pagjub", "docvig"})


def test_s04_legada() -> None:
    import inspect
    E0 = correr_e0.E0
    print("== q) S0-4 de U-SEG-OFICIAL: la versión legada no cambia; listas de TOs")
    p = inspect.signature(E0.parsear_cuerpo).parameters
    check("parsear_cuerpo: sub-documento, sdg3, sdmax, las reglas de letra y apartados apagados por default",
          p["subdocumentos"].default is None and p["g3_subdoc"].default is False
          and p["raiz_max_subdoc"].default is False and p["apartados_seccion"].default is False
          and p["letra_corte"].default is False and p["letra_herencia"].default is False
          and p["letra_numero"].default is False)
    ls = inspect.signature(E0.limites_subdocumento).parameters
    check("limites_subdocumento: forma de letra y régimen de la página 1 apagados por default",
          ls["letras"].default is False and ls["sin_regimen_pagina_1"].default is False)
    s = inspect.signature(E0.construir_chunks).parameters
    check("construir_chunks: 4a y 4b apagadas por default",
          s["oracion_titulo_4a"].default is False and s["titulo_envuelto_4b"].default is False)
    check("listas de S0-4: sub-documento en los cinco TOs del diseño (sin ri_tsa ni ri2_pm), apartados en ri_ai, "
          "4a y 4b fuera de la tanda 0, y el mecanismo 4 de S0-3 fuera de las reglas",
          correr_e0.TOS_SUBDOCUMENTO_S0_4 == frozenset({"ri_sef", "nmcief", "ri_ccna", "ri_icpipsp", "ri_cc"})
          and correr_e0.TOS_APARTADOS_S0_4 == frozenset({"ri_ai"})
          and correr_e0.TOS_TANDA0_SIN_4AB == TOS_TANDA0
          and "m4" not in correr_e0.REGLAS_S0_3
          and correr_e0.REGLAS_S0_4 == frozenset({"sd", "sdg3", "sdmax", "sdr1", "apl", "sdl", "sdlh", "sdla", "4a",
                                                  "4b", "ap"})
          and correr_e0.TOS_SUBDOCUMENTO_R1_S0_4 == frozenset({"ri_oc"})
          and correr_e0.TOS_APARTADO_LETRA_S0_4 == frozenset({"ri_oc"})
          and correr_e0.TOS_LETRA_S0_4 == frozenset({"ri_ccna"}))


def _enc(pagina: int, *extra):
    """Zona de encabezado de una página sintética: título del TO, «B.C.R.A.» y los renglones extra."""
    out = [_linea("NORMAS MINIMAS DE PRUEBA", pagina, 72.0, x0=200.0), _linea("B.C.R.A.", pagina, 85.0, x0=83.0)]
    for k, t in enumerate(extra):
        out.append(_linea(t, pagina, 98.0 + 13 * k, x0=140.0))
    return out


def test_s04_sinteticos() -> None:
    E0 = correr_e0.E0
    print("== r) S0-4 de U-SEG-OFICIAL: casos sintéticos")
    largo = "Texto de la norma que corre en la columna del cuerpo y ocupa un renglón entero de prosa."
    # detección: anexo en el encabezado, partes I y II, anexo repetido, anexo II con una parte suelta, serie de letras
    pags = [
        _enc(1, "ANEXO I") + [_linea("I.- CONCEPTOS BÁSICOS", 1, 130.0, x0=76.0),
                              _linea("1. Control interno.", 1, 150.0), _linea(largo, 1, 164.0, x0=90.0)],
        _enc(2, "ANEXO I") + [_linea("II.- COMITÉ DE AUDITORÍA", 2, 130.0, x0=76.0),
                              _linea("1. Integración.", 2, 150.0), _linea(largo, 2, 164.0, x0=90.0)],
        _enc(3, "Anexo II") + [_linea("I. Bienes diversos", 3, 130.0, x0=76.0), _linea(largo, 3, 150.0, x0=90.0)],
        _enc(4, "ANEXO H") + [_linea(largo, 4, 130.0, x0=90.0)],
        _enc(5, "ANEXO I") + [_linea(largo, 5, 130.0, x0=90.0)]]
    roles = [E0.ROL_CUERPO] * len(pags)
    lim = E0.limites_subdocumento(pags, roles)
    check("sub-documento: anexo I con sus partes I y II, anexo II; el anexo repetido, la parte suelta y la serie de "
          "letras («ANEXO I» tras «ANEXO H») no abren sub-documento",
          [(d["prefijo"], d["forma"], d["padre"]) for d in lim]
          == [("A1", "anexo", None), ("A1P1", "parte", "A1"), ("A1P2", "parte", "A1"), ("A2", "anexo", None)],
          str([(d["prefijo"], d["forma"]) for d in lim]))
    # régimen, formulario (con su continuación) y circular (y la circular suelta de otro anexo)
    reg = [_enc(1, "4 - REGULACIONES Y RELACIONES TÉCNICAS") + [_linea(largo, 1, 130.0)],
           _enc(2, "5– PREVENCION DEL LAVADO DE DINERO") + [_linea(largo, 2, 130.0)],
           [_linea("RÉGIMEN INFORMATIVO PARA PUBLICACIÓN", 3, 72.0, x0=200.0),
            _linea("PARA CAJAS DE CRÉDITO (R.I. – P.)", 3, 84.0, x0=258.0), _linea(largo, 3, 130.0)]]
    check("sub-documento: régimen por «N - TÍTULO» y por la sigla «(R.I. – P.)»",
          [d["prefijo"] for d in E0.limites_subdocumento(reg, [E0.ROL_CUERPO] * 3)] == ["R4", "R5", "RIP"])
    form = [_enc(1, "ANEXO I") + [_linea("1. Toma de conocimiento.", 1, 130.0)],
            [_linea("BANCO CENTRAL DE LA REPÚBLICA ARGENTINA", 2, 72.0), _linea("DECLARACIÓN JURADA", 2, 84.0),
             _linea("1. No soy socio de la entidad.", 2, 130.0)],
            [_linea("SOLICITUD Cont. 2", 3, 70.0), _linea("BANCO CENTRAL DE LA REPUBLICA ARGENTINA", 3, 75.0),
             _linea(largo, 3, 130.0)],
            [_linea("BANCO CENTRAL DE LA REPÚBLICA ARGENTINA", 4, 72.0), _linea("SOLICITUD DE INSCRIPCIÓN", 4, 84.0),
             _linea(largo, 4, 130.0)]]
    check("sub-documento: formulario por el membrete; la página con «Cont. 2» sigue el formulario anterior",
          [d["prefijo"] for d in E0.limites_subdocumento(form, [E0.ROL_CUERPO] * 4)] == ["A1", "F1", "F2"])
    circ = [_enc(1, "ANEXO I") + [_linea("Circular SINAP 1. Sistema Nacional de Pagos", 1, 130.0),
                                  _linea("1. Exclusiones - Corroborar.", 1, 150.0),
                                  _linea("Circular CONAU 1. Régimen Informativo", 1, 170.0),
                                  _linea("1. Proveedores de servicios.", 1, 190.0)],
            _enc(2, "ANEXO II") + [_linea("Circular RUNOR 1. Protección de los usuarios", 2, 130.0)]]
    check("sub-documento: dos circulares en el mismo anexo abren C1 y C2; una suelta no",
          [d["prefijo"] for d in E0.limites_subdocumento(circ, [E0.ROL_CUERPO] * 2)] == ["A1", "A1C1", "A1C2", "A2"])
    # lectura con sub-documentos (modo sin raíz): prefijo, numeración desde cero y herencia del rótulo
    sd = [[_linea("Preámbulo de la norma con su texto corrido en la columna del cuerpo de la página.", 1, 100.0),
           _linea("I. Información solicitada", 1, 130.0, x0=76.0), _linea("1. Tipo de trámite.", 1, 150.0, x0=76.0),
           _linea(largo, 1, 164.0, x0=90.0), _linea("2. Etapa del trámite.", 1, 190.0, x0=76.0),
           _linea(largo, 1, 204.0, x0=90.0)],
          [_linea("II. Otras informaciones.", 2, 100.0, x0=76.0),
           _linea("1. Información adicional.", 2, 130.0, x0=76.0), _linea(largo, 2, 144.0, x0=90.0)]]
    rs = [E0.ROL_CUERPO] * 2
    lim_sd = E0.limites_subdocumento(sd, rs)
    r0 = E0.parsear_cuerpo("x", "x.pdf", sd, rs, modo_sin_raiz=True, mayusculas_repetidas=set())
    r1 = E0.parsear_cuerpo("x", "x.pdf", sd, rs, modo_sin_raiz=True, mayusculas_repetidas=set(),
                           subdocumentos=lim_sd)
    ch0 = {c["id"]: c for c in E0.construir_chunks(r0)}
    ch1 = {c["id"]: c for c in E0.construir_chunks(r1)}
    check("sub-documento: sin la regla, la parte II queda dentro del ítem 2; con ella, cada parte con su espacio "
          "de ids",
          "x::S2" in ch0 and "II. Otras informaciones." in ch0["x::S2"]["texto"]
          and set(ch1) == {"x::S0", "x::P1::S0", "x::P1::S1", "x::P1::S2", "x::P2::S0", "x::P2::S1"},
          str(sorted(ch1)))
    check("sub-documento: la unidad hereda el rótulo de su sub-documento; la raíz «0» no se hereda a sí misma",
          ch1["x::P2::S1"]["herencia"][0]["texto"] == "II. Otras informaciones."
          and ch1["x::P2::S1"]["herencia"][0]["unidad_origen"] == "P2"
          and ch1["x::P2::S0"]["herencia"] == [] and ch1["x::P2::S0"]["texto"].startswith("II. Otras"))
    cob = E0.verificar_cobertura(r1)
    check("sub-documento: cobertura exacta", cob["cobertura_exacta"], str(cob))
    # sdg3: dentro de un sub-documento, la raíz que sucede exactamente a la anterior y está más adentro
    g = [[_linea("I. Comité", 1, 100.0, x0=76.0), _linea("1. Integración.", 1, 120.0, x0=76.0),
          _linea(largo, 1, 134.0, x0=100.0), _linea("2. Periodicidad de las reuniones", 1, 160.0, x0=86.0),
          _linea(largo, 1, 174.0, x0=100.0)],
         [_linea("II. Auditoría", 2, 100.0, x0=76.0), _linea(largo, 2, 120.0, x0=100.0)]]
    lg = E0.limites_subdocumento(g, [E0.ROL_CUERPO] * 2)
    sin = E0.parsear_cuerpo("x", "x.pdf", g, [E0.ROL_CUERPO] * 2, modo_sin_raiz=True, mayusculas_repetidas=set(),
                            subdocumentos=lg)
    con = E0.parsear_cuerpo("x", "x.pdf", g, [E0.ROL_CUERPO] * 2, modo_sin_raiz=True, mayusculas_repetidas=set(),
                            subdocumentos=lg, g3_subdoc=True)
    check("sdg3: sin la guarda nueva, la raíz 2 (10 pt más adentro) se rechaza; con ella, se abre y se declara",
          [s.numero for s in sin.secciones if s.prefijo == "P1"] == ["0", "1"]
          and [s.numero for s in con.secciones if s.prefijo == "P1"] == ["0", "1", "2"]
          and any(a["tipo"] == "raiz_g3_subdocumento_sd" for a in con.avisos))
    # sdmax (S0-4a-bis): dentro de un sub-documento, la raíz mayor que MAX_RAIZ que sucede exactamente a la anterior
    items = [_linea("I. Procedimientos mínimos", 1, 60.0, x0=76.0)]
    for k in list(range(1, 32)) + [33]:
        items.append(_linea(f"{k}. Revisión del rubro {k} de los estados contables.", 1, 80.0 + 14 * k, x0=76.0))
    mx = [items, [_linea("II. Códigos de actividad", 2, 60.0, x0=76.0),
                  _linea("101. Estación de servicio", 2, 80.0, x0=76.0), _linea(largo, 2, 94.0, x0=90.0)]]
    lmx = E0.limites_subdocumento(mx, [E0.ROL_CUERPO] * 2)
    kmx = dict(modo_sin_raiz=True, mayusculas_repetidas=set())
    sin_mx = E0.parsear_cuerpo("x", "x.pdf", mx, [E0.ROL_CUERPO] * 2, subdocumentos=lmx, **kmx)
    con_mx = E0.parsear_cuerpo("x", "x.pdf", mx, [E0.ROL_CUERPO] * 2, subdocumentos=lmx, raiz_max_subdoc=True, **kmx)
    fuera = E0.parsear_cuerpo("x", "x.pdf", mx, [E0.ROL_CUERPO] * 2, raiz_max_subdoc=True, **kmx)
    raices_p1 = [s.numero for s in con_mx.secciones if s.prefijo == "P1"]
    rech = [r["texto"].split()[0] for r in con_mx.rechazos_header if r["motivo"] == "raiz_mayor_a_max"]
    check("sdmax: sin la regla, la raíz 31 se rechaza por MAX_RAIZ; con ella, se abre la 31 (sucede a la 30) y no "
          "la 33 ni el código 101 de la parte II; fuera de un sub-documento no corre",
          [s.numero for s in sin_mx.secciones if s.prefijo == "P1"][-1] == "30" and raices_p1[-1] == "31"
          and len(raices_p1) == 32 and rech == ["33.", "101."]
          and [a["numero"] for a in con_mx.avisos if a["tipo"] == "raiz_mayor_a_max_subdocumento_sdmax"] == ["31"]
          and not any(a["tipo"] == "raiz_mayor_a_max_subdocumento_sdmax" for a in fuera.avisos),
          str((raices_p1[-3:], rech)))
    # S0-4a-ter, sdr1: el régimen de la página 1 es el del TO (y su encabezado corrido en las páginas siguientes)
    r1 = [_enc(1, "10 – OPERACIONES DE CAMBIOS") + [_linea(largo, 1, 130.0)],
          _enc(2, "10 – OPERACIONES DE CAMBIOS") + [_linea(largo, 2, 130.0)],
          _enc(3, "10 – OPERACIONES DE CAMBIOS", "ANEXO I: Códigos de instrumentos") + [_linea(largo, 3, 150.0)]]
    sin_r1 = E0.limites_subdocumento(r1, [E0.ROL_CUERPO] * 3)
    con_r1 = E0.limites_subdocumento(r1, [E0.ROL_CUERPO] * 3, sin_regimen_pagina_1=True)
    check("sdr1: sin la regla, el régimen de la página 1 prefija el anexo (R10, R10A1); con ella, solo el anexo, "
          "sin padre",
          [(d["prefijo"], d["padre"]) for d in sin_r1] == [("R10", None), ("R10A1", "R10")]
          and [(d["prefijo"], d["padre"]) for d in con_r1] == [("A1", None)], str((sin_r1, con_r1)))
    # S0-4a-ter, apl: apartados de letra en una lectura sin raíz que también tiene raíces numéricas
    ap_l = [[_linea("APARTADO A: OPERACIONES DE CAMBIOS", 1, 100.0, x0=77.0),
             _linea("1. Instrucciones generales.", 1, 120.0, x0=77.0), _linea(largo, 1, 134.0, x0=85.0),
             _linea("1.1. Para las operaciones de compra.", 1, 150.0, x0=85.0), _linea(largo, 1, 164.0, x0=98.0),
             _linea("APARTADO B: POSICIÓN GENERAL DE CAMBIOS", 1, 190.0, x0=76.0),
             _linea("B.1. Variación Diaria", 1, 210.0, x0=76.0),
             _linea("B.1.1. Posición General de Cambios al cierre del día anterior", 1, 230.0, x0=112.0),
             _linea("B.1.2. Compras concertadas de billetes y divisas con clientes.", 1, 244.0, x0=112.0)]]
    kl = dict(modo_sin_raiz=True, mayusculas_repetidas=set())
    ch_l0 = {c["id"]: c for c in E0.construir_chunks(E0.parsear_cuerpo("x", "x.pdf", ap_l, [E0.ROL_CUERPO], **kl))}
    ch_l1 = {c["id"]: c for c in E0.construir_chunks(E0.parsear_cuerpo("x", "x.pdf", ap_l, [E0.ROL_CUERPO],
                                                                        marcador_letra=True, **kl))}
    check("apl: sin el marcador, el Apartado B queda dentro del punto 1.1; con él, «APARTADO B:» cierra la raíz 1 y "
          "B.1.1 y B.1.2 son puntos de B, con la raíz 1 y su 1.1 como estaban",
          "APARTADO B" in ch_l0.get("x::1.1", {}).get("texto", "") and "x::B.1.1" not in ch_l0
          and {"x::B.1.1", "x::B.1.2", "x::1.1"} <= set(ch_l1) and "APARTADO B" not in ch_l1["x::1.1"]["texto"]
          and [h["unidad_origen"] for h in ch_l1["x::B.1.1"]["herencia"]] == ["SB", "B.1"], str(sorted(ch_l1)))
    # S0-4a-ter, sdl, sdlh y sdla: el Anexo III de ri_ccna en chico
    lt = [_enc(1, "ANEXO I") + [_linea("A. GENERAL", 1, 120.0, x0=115.0),
                                _linea("A.1. PRUEBAS DE CUMPLIMIENTO DEL CONTROL INTERNO.", 1, 134.0, x0=149.0),
                                _linea(largo, 1, 148.0, x0=149.0),
                                _linea("1. Evaluación de las variaciones del activo.", 1, 170.0, x0=203.0),
                                _linea("2. Evaluación de las variaciones de resultados.", 1, 184.0, x0=203.0),
                                _linea(largo, 1, 198.0, x0=203.0),
                                _linea("A.3. El relevamiento del control interno sirve de base.", 1, 220.0, x0=149.0),
                                _linea("B. PRUEBAS SUSTANTIVAS", 1, 240.0, x0=115.0),
                                _linea("1. Arqueo sorpresivo de las existencias.", 1, 260.0, x0=150.0),
                                _linea("2. Obtención de confirmaciones directas.", 1, 274.0, x0=150.0),
                                _linea("3. Revisión de las conciliaciones bancarias.", 1, 288.0, x0=150.0),
                                _linea("C. Datos de la entidad", 1, 310.0, x0=115.0)]]
    rl = [E0.ROL_CUERPO]
    lim_l = E0.limites_subdocumento(lt, rl, letras=True)
    lim_0 = E0.limites_subdocumento(lt, rl)
    check("sdl: la forma de letra da A1L1 y A1L2 dentro del anexo, con su letra; «C. Datos…» (sin mayúsculas) no",
          [(d["prefijo"], d["forma"], d["padre"], d.get("letra")) for d in lim_l]
          == [("A1", "anexo", None, None), ("A1L1", "letra", "A1", "A"), ("A1L2", "letra", "A1", "B")]
          and [d["prefijo"] for d in lim_0] == ["A1"], str(lim_l))
    serie_b = [_enc(1, "ANEXO I") + [_linea("B. PRUEBAS SUSTANTIVAS", 1, 120.0, x0=115.0),
                                     _linea("C. OTRAS PRUEBAS", 1, 140.0, x0=115.0)]]
    check("sdl, guarda: una serie que no empieza en la A no abre sub-documento de letra",
          [d["prefijo"] for d in E0.limites_subdocumento(serie_b, rl, letras=True)] == ["A1"])

    def _chl(**kw):
        return {c["id"]: c for c in E0.construir_chunks(E0.parsear_cuerpo("x", "x.pdf", lt, rl, subdocumentos=lim_l,
                                                                             **kl, **kw))}
    c0, c_sdl, c_h = _chl(), _chl(letra_corte=True), _chl(letra_herencia=True)
    c_sdl_h, c_a = _chl(letra_corte=True, letra_herencia=True), _chl(letra_numero=True)
    c_todas = _chl(letra_corte=True, letra_herencia=True, letra_numero=True)

    def her(c, uid):
        return [h["texto"] for h in c.get(uid, {}).get("herencia", [])]
    check("sdl: sin la regla, B.1 y B.2 se rechazan (la numeración no reinicia) y quedan en el ítem 2 de A; con "
          "ella, B abre su sub-documento y B.1 a B.3 son sus raíces, sin heredar su rótulo",
          "1. Arqueo" in c0["x::A1::S2"]["texto"] and "x::A1::S3" in c0
          and c_sdl["x::A1L2::S1"]["texto"].startswith("1. Arqueo") and "x::A1L2::S3" in c_sdl
          and "B. PRUEBAS SUSTANTIVAS" not in her(c_sdl, "x::A1L2::S3"), str(sorted(c_sdl)))
    check("sdlh: sin sdl, las raíces abiertas después del rótulo heredan la letra vigente (A1::S1 «A. GENERAL», "
          "A1::S3 «B. PRUEBAS SUSTANTIVAS»), sin otro cambio; con sdl, las del sub-documento de letra heredan su "
          "rótulo",
          her(c_h, "x::A1::S1") == ["ANEXO I", "A. GENERAL"]
          and her(c_h, "x::A1::S3") == ["ANEXO I", "B. PRUEBAS SUSTANTIVAS"]
          and set(c_h) == set(c0) and all(c_h[i]["texto"] == c0[i]["texto"] for i in c0)
          and her(c_sdl_h, "x::A1L2::S3") == ["ANEXO I", "B. PRUEBAS SUSTANTIVAS"])
    check("sdla: «A.3.» con la letra vigente y más afuera que la raíz 2 abre la raíz A.3 (sin sdl, A1::SA.3; con "
          "sdl, A1L1::SA.3), y la raíz 2 ya no la lleva",
          c_a["x::A1::SA.3"]["texto"].startswith("A.3. El relevamiento") and "A.3." not in c_a["x::A1::S2"]["texto"]
          and "A.3." in c0["x::A1::S2"]["texto"]
          and c_todas["x::A1L1::SA.3"]["texto"].startswith("A.3.")
          and "B. PRUEBAS" not in c_todas["x::A1L1::SA.3"]["texto"]
          and her(c_todas, "x::A1L1::SA.3") == ["ANEXO I", "A. GENERAL"], str(sorted(c_todas)))
    cob_l = E0.verificar_cobertura(E0.parsear_cuerpo("x", "x.pdf", lt, rl, subdocumentos=lim_l, letra_corte=True,
                                                     letra_herencia=True, letra_numero=True, **kl))
    check("reglas de letra: cobertura exacta", cob_l["cobertura_exacta"], str(cob_l))
    # 4a: oración tomada como título (el caso del mecanismo 4)
    m4 = [_linea("Sección 2. Dispositivos de seguridad.", 1, 30.0),
          _linea("2.1. Sistema de monitoreo.", 1, 50.0, x0=76.0), _linea(largo, 1, 64.0, x0=98.0),
          _linea("2.1.6. Cuando se decida contar con video vigilancia remota, deberán complementar su seguri-",
                 1, 90.0, x0=98.0),
          _linea("dad con dispositivos que dificulten la accesibilidad al dinero, como ser:", 1, 104.0, x0=129.0),
          _linea("2.1.6.1. Sistema de alerta (último billete): consiste en la emisión de una alerta.", 1, 130.0,
                 x0=133.0)]
    r4, ch4 = _parse([m4])
    ch4a = E0.construir_chunks(r4, oracion_titulo_4a=True)
    intro = _texto(ch4a, "x::2.1.6::intro") or ""
    hoja = next((c for c in ch4a if c["id"] == "x::2.1.6.1"), {})
    check("4a: la intro de 2.1.6 empieza en su rótulo y el encabezado heredado es solo el número",
          intro.startswith("2.1.6. Cuando se decida") and (_texto(ch4, "x::2.1.6::intro") or "").startswith("dad con")
          and any(t["texto"] == "2.1.6." for t in hoja.get("herencia", []))
          and E0.clase_titulo_4ab(next(n for n in r4.secciones[0].hijos[0].hijos if n.numero == "2.1.6"))[0] == "4a")
    # 4b: título envuelto, con la intro de un renglón y con una intro más larga; guarda del verbo
    tb = [_linea("Sección 1. Titulares.", 1, 30.0),
          _linea("1.3. Identificación de los titulares de cuentas y de las personas autorizadas a operar en", 1, 50.0,
                 x0=76.0),
          _linea("ellas.", 1, 64.0, x0=98.0),
          _linea("1.3.1. Personas humanas.", 1, 90.0, x0=98.0), _linea(largo, 1, 104.0, x0=120.0),
          _linea("1.4. Reporte de otras circunstancias que modifiquen las obligaciones con el", 1, 130.0, x0=76.0),
          _linea("exterior del importador.", 1, 144.0, x0=98.0), _linea(largo, 1, 158.0, x0=98.0),
          _linea("1.4.1. Plazos.", 1, 180.0, x0=98.0), _linea(largo, 1, 194.0, x0=120.0),
          _linea("1.5. La letra de cambio extendida a favor de una persona determinada, que no posea la", 1, 220.0,
                 x0=76.0),
          _linea("cláusula “no a la orden”, será transmisible por endoso.", 1, 234.0, x0=98.0),
          _linea("1.5.1. Endoso.", 1, 260.0, x0=98.0), _linea(largo, 1, 274.0, x0=120.0)]
    rb, chb0 = _parse([tb])
    chb = E0.construir_chunks(rb, titulo_envuelto_4b=True, oracion_titulo_4a=True)
    ids_b = {c["id"]: c for c in chb}
    h131 = [t["texto"] for t in ids_b["x::1.3.1"]["herencia"] if t["tipo"] == "encabezado"]
    check("4b: el renglón que completa el título se junta al título y la intro de un renglón no se emite",
          "x::1.3::intro" in {c["id"] for c in chb0} and "x::1.3::intro" not in ids_b
          and h131[-1] == "1.3. Identificación de los titulares de cuentas y de las personas autorizadas a operar "
                          "en\nellas.", str(h131))
    check("4b: con más intro, la intro sigue sin ese renglón",
          ids_b["x::1.4::intro"]["texto"] == largo and _texto(chb0, "x::1.4::intro").startswith("exterior del"))
    check("4b, guarda: un renglón con verbo («será transmisible») no se junta; la oración es 4a",
          ids_b["x::1.5::intro"]["texto"].startswith("1.5. La letra de cambio")
          and any(t["texto"] == "1.5." for t in ids_b["x::1.5.1"]["herencia"]))
    # apartados de una sección sin puntos (lectura vigente)
    ap = [_linea("REGIMEN INFORMATIVO", 1, 72.0, x0=226.0), _linea("B.C.R.A.", 1, 85.0, x0=83.0),
          _linea("Sección 4. Determinación de la relación", 1, 98.0, x0=139.0),
          _linea("1. Posición", 1, 130.0, x0=76.0),
          _linea("a) General (sin computar el código 107):", 1, 150.0, x0=90.0),
          _linea("2. Franquicias", 1, 180.0, x0=76.0), _linea(largo, 1, 194.0, x0=90.0)]
    a0 = E0.parsear_cuerpo("x", "x.pdf", [ap], [E0.ROL_CUERPO], mayusculas_repetidas=set(), pie_desde_version=True)
    a1 = E0.parsear_cuerpo("x", "x.pdf", [ap], [E0.ROL_CUERPO], mayusculas_repetidas=set(), pie_desde_version=True,
                           apartados_seccion=True)
    cha = {c["id"]: c for c in E0.construir_chunks(a1)}
    check("apartados: sin la regla, «1. Posición» se rechaza fuera de la sección 4; con ella, abre el punto 4.1",
          any(r["motivo"] == "fuera_de_seccion_4" for r in a0.rechazos_header)
          and set(cha) == {"x::4.1", "x::4.2"} and cha["x::4.1"]["flags"].get("numero_impreso") == "1"
          and cha["x::4.1"]["texto"].startswith("1. Posición"), str(sorted(cha)))


def test_s04_casos(d: Path) -> None:
    print(f"== s) S0-4 de U-SEG-OFICIAL: un caso medido por regla (e0-r2 sobre {len(TOS_S04)} TOs)")
    correr_e0.correr(d, manifiesto=_ManifiestoParticion(TOS_S04), version_e0="e0-r2")
    ch = {to: {c["id"]: c for c in cargar(d, f"chunks_{to}.json")} for to in TOS_S04}

    def txt(to: str, uid: str) -> str:
        return ch[to].get(uid, {}).get("texto", "")

    check("sub-documento, ri_sef (fila 58 de S1): el preámbulo ya no trae la parte I; partes I a III y anexos I a "
          "III",
          "Información solicitada" not in txt("ri_sef", "ri_sef::S0") and bool(txt("ri_sef", "ri_sef::P1::S1"))
          and txt("ri_sef", "ri_sef::P2::S0").startswith("II. Requisitos") and bool(txt("ri_sef", "ri_sef::P3::S1"))
          and txt("ri_sef", "ri_sef::A3::S0").startswith("Anexo III"))
    check("sub-documento, nmcief (fila 71): el Anexo II con su numeración (nmcief::A2::3.2.1) y la herencia desde "
          "«Anexo II»",
          bool(txt("nmcief", "nmcief::A2::3.2.1"))
          and ch["nmcief"]["nmcief::A2::3.2.1"]["herencia"][0]["texto"] == "Anexo II")
    check("sdg3, nmcief (fila 71): «4. Periodicidad…» abre su raíz y la 3 ya no la lleva",
          txt("nmcief", "nmcief::A1P2::S4").startswith("4. Periodicidad")
          and "Periodicidad" not in txt("nmcief", "nmcief::A1P2::S3"))
    check("sub-documento, ri_ccna (fila 82): los anexos de la segunda norma (D2) y los formularios (D1F2) con su "
          "numeración; el Anexo IV ya no lleva los ítems de la declaración jurada",
          bool(txt("ri_ccna", "ri_ccna::D2A2::3.4.1")) and txt("ri_ccna", "ri_ccna::D1F2::S1").startswith("1. No soy")
          and "ri_ccna::D1A4::S5" not in ch["ri_ccna"])
    check("sub-documento, ri_icpipsp (fila 85): la fila 8 de SINAP ya no lleva el bloque CONAU; el Anexo II aparte",
          bool(txt("ri_icpipsp", "ri_icpipsp::A1C1::S8"))
          and "CONAU" not in txt("ri_icpipsp", "ri_icpipsp::A1C1::S8")
          and txt("ri_icpipsp", "ri_icpipsp::A2::S0").startswith("ANEXO II"))
    check("sub-documento, ri_cc: los tres regímenes (R4, R5 y RIP); R5::S3 es solo la p. 75",
          bool(txt("ri_cc", "ri_cc::R4::1.1")) and bool(txt("ri_cc", "ri_cc::R5::2.1"))
          and ch["ri_cc"]["ri_cc::R5::S3"]["paginas"] == [75] and bool(txt("ri_cc", "ri_cc::RIP::S0")))
    check("sdmax, ri_ccna (Anexo III de la primera norma): los ítems 31 a 40 abren su raíz y la 30 ya no los "
          "lleva (desde S0-4a-ter, en el sub-documento de letra D1A3L2)",
          all(f"ri_ccna::D1A3L2::S{k}" in ch["ri_ccna"] for k in range(31, 41))
          and txt("ri_ccna", "ri_ccna::D1A3L2::S31").startswith("31. Arqueo sorpresivo de los valores")
          and len(txt("ri_ccna", "ri_ccna::D1A3L2::S30")) == 350
          and "31. Arqueo" not in txt("ri_ccna", "ri_ccna::D1A3L2::S30"))
    l2 = [i for i in ch["ri_ccna"] if i.startswith("ri_ccna::D1A3L2::") and i != "ri_ccna::D1A3L2::S0"]
    check("sdl, ri_ccna (Anexo III): «A. GENERAL» y «B. PRUEBAS SUSTANTIVAS» abren D1A3L1 y D1A3L2; B.1 y B.2 son "
          "las raíces 1 y 2 de D1A3L2; 169 unidades (164 en S0-4; R5-c de S0-5a quita cinco chapeaux; R5-f de "
          "S0-5a-bis abre 11 puntos de D1A1 y D1A2 y quita el chapeau de D1A1::S5)",
          txt("ri_ccna", "ri_ccna::D1A3L1::S0").startswith("A. GENERAL")
          and txt("ri_ccna", "ri_ccna::D1A3L2::S0") == "B. PRUEBAS SUSTANTIVAS"
          and txt("ri_ccna", "ri_ccna::D1A3L2::S1").startswith("1. Arqueo sorpresivo de las existencias")
          and txt("ri_ccna", "ri_ccna::D1A3L2::S2").startswith("2. Obtención de confirmaciones")
          and "ri_ccna::D1A3::S2" not in ch["ri_ccna"] and len(ch["ri_ccna"]) == 169)
    check("sdlh, ri_ccna (Anexo III): las 47 unidades de la lista B (B.1 a B.40, con los sub-ítems de 26 y 29; desde "
          "S0-5a sin los chapeaux de 26 y 29) heredan «B. PRUEBAS SUSTANTIVAS», y las de A.2 y A.3, «A. GENERAL»",
          len(l2) == 47
          and all(any(h["texto"] == "B. PRUEBAS SUSTANTIVAS" for h in ch["ri_ccna"][i]["herencia"]) for i in l2)
          and all(any(h["texto"] == "A. GENERAL" for h in ch["ri_ccna"][i]["herencia"])
                  for i in ("ri_ccna::D1A3L1::S1", "ri_ccna::D1A3L1::S2", "ri_ccna::D1A3L1::SA.3")), str(len(l2)))
    check("sdla, ri_ccna (Anexo III): A.3 es su propia unidad (D1A3L1::SA.3) y el ítem 2 de A.2 queda solo (667 "
          "caracteres)",
          txt("ri_ccna", "ri_ccna::D1A3L1::SA.3").startswith("A.3. El relevamiento y evaluación")
          and len(txt("ri_ccna", "ri_ccna::D1A3L1::S2")) == 667 and "A.3." not in txt("ri_ccna", "ri_ccna::D1A3L1::S2"))
    oc = ch["ri_oc"]
    check("sdr1, ri_oc: los Anexos I y II son sub-documentos sin el prefijo del régimen de la página 1",
          bool(txt("ri_oc", "ri_oc::A1::S0")) and all(f"ri_oc::A2::S{k}" in oc for k in range(1, 7))
          and not any("R10" in i for i in oc))
    check("apl, ri_oc: «APARTADO B» y «APARTADO C» abren sus raíces, B.1.1 a B.3.4 y C.1 a C.11 son puntos, y "
          "3.51 queda con su texto (p. 15); 187 unidades (184 en S0-4; desde S0-5a, B.1.1 hereda el cierre de B.1 que abre "
          "R5-a)",
          all(f"ri_oc::B.1.{k}" in oc for k in range(1, 29)) and "ri_oc::B.3.4" in oc and "ri_oc::C.11" in oc
          and oc["ri_oc::3.51"]["paginas"] == [15] and "APARTADO B" not in txt("ri_oc", "ri_oc::3.51")
          and [h["unidad_origen"] for h in oc["ri_oc::B.1.1"]["herencia"]] == ["SB", "B.1", "B.1"] and len(oc) == 187)
    est_sef = cargar(d, "estructura_ri_sef.json")
    check("sdmax, ri_sef: los códigos 101 a 126 del Anexo II no suceden a la raíz anterior y siguen rechazados",
          sum(r["motivo"] == "raiz_mayor_a_max" for r in est_sef["rechazos_header"]) == 24
          and not any(a["tipo"] == "raiz_mayor_a_max_subdocumento_sdmax" for a in est_sef["avisos"]))
    check("apartados, ri_ai: «1. Posición», «2. Franquicias», «3. Incumplimientos» son 4.1 a 4.3",
          all(f"ri_ai::4.{k}" in ch["ri_ai"] for k in (1, 2, 3)) and "ri_ai::S4" not in ch["ri_ai"]
          and ch["ri_ai"]["ri_ai::4.1"]["flags"].get("numero_impreso") == "1")
    hijo = next(c for i, c in ch["efemin"].items() if i.startswith("efemin::1.3.1.") and c["tipo"] == "punto_terminal")
    check("4b, efemin 1.3.1 (uno de los 30 títulos partidos de un renglón): sin intro y con el título entero",
          "efemin::1.3.1::intro" not in ch["efemin"]
          and any(t["texto"].endswith("abiertas en las cajas de crédito cooperativas.") for t in hijo["herencia"]))
    cob = cargar(d, "cobertura.json")
    check(f"cobertura exacta en los {len(TOS_S04)} TOs", all(cob[to]["cobertura_exacta"] for to in TOS_S04))


# ------------------------------------------------------------------ S0-5a de U-SEG-OFICIAL
TOS_S05 = ("ri_rml", "snp_tr", "ri_oc", "snp_dd", "snp_cheq", "ri_ccna", "adfsp", "cajasc", "depaho", "manori",
           "ri2_ae", "ri_spi", "gerc", "rdbcra", "ordcom", "pimf", "inspag", "pfmipyme", "ri_cr", "snp_psp", "adrei",
           "ayccef", "cirmo3", "efemin", "lingeef")
# los 27 candidatos del hallazgo 1.16 de la tanda 1 que la lectura de S1-bis marcó correctos: el sha256 de su texto
# propio en la salida de S0-4b (s1bis/e0), que S0-5a no cambia (caso negativo de R5-a)
CORRECTOS_116 = {
    "adrei::2.2.2.2": "bd6c46a527e5a377", "adrei::4.2.1.4": "0edfda329c31c139",
    "ayccef::2.3.2.2": "29605e048abc9231", "ayccef::2.9.4.2": "3a8d9f9e4b4fe8a2",
    "ayccef::3.6.2.2": "869dafbd6b3ccad0", "ayccef::4.4.5": "ce7a2b7ade345961",
    "ayccef::5.2.5.2": "55f382adfd6b67ac", "cajasc::11.1.2": "29a2640fce87483b",
    "cajasc::6.2.1.3": "904f2433090a71dd", "cirmo3::8.9.4": "d503b7ffab47fed2",
    "depaho::1.12.2": "fc95f4416a1124af", "depaho::1.5.5": "56580bb43c1c7995",
    "depaho::3.1.6.4": "918914aac8038c46", "depaho::3.4.10.2": "a36de14e4d6774b5",
    "depaho::3.4.4.5": "d3e64d5864bd96b0", "depaho::3.6.2.4": "3025ab5828628ecb",
    "depaho::3.8.6.4": "8d43d58dd7e20dd2", "efemin::3.2.2": "651990d6f23bc8f5",
    "lingeef::10.3.2": "76eb53fc79b08318", "lingeef::12.8.2": "ceade401db3af6aa",
    "lingeef::3.3.1.8": "0624c4f7cb9c873c", "lingeef::5.1.1.3": "1836a453ac950182",
    "lingeef::5.3.4.5": "32378fa47c38a089", "lingeef::5.4.3.3": "2120f6c8653dbe4b",
    "lingeef::6.2.1.9": "418c3a38b5817a9a", "lingeef::7.3.2.2": "f524b0b4e1ebb7d0",
    "snp_tr::4.2": "8068ac542d7a2e7d"}
# los 9 casos del mecanismo 1 (R5-a): el cierre del padre y su primer renglón
CIERRES_R5A = {
    "adfsp::1.1.10": ("adfsp::1.1::cierre", "En caso de que alguna entidad financiera deje de reunir los"),
    "cajasc::11.4.4": ("cajasc::11.4::cierre", "Ello, sin perjuicio de lo que se haya establecido en forma"),
    "cajasc::4.2.2.3": ("cajasc::4.2.2::cierre", "Los préstamos a que se refieren los puntos 4.2.2.1. y 4.2.2.3."),
    "depaho::3.11.5.5": ("depaho::3.11.5::cierre", "Los movimientos –cualquiera sea su naturaleza– no podrán"),
    "manori::1.4.1.3": ("manori::1.4.1::cierre", "La entidad financiera deberá desarrollar documentación"),
    "manori::3.4.1.3": ("manori::3.4.1::cierre", "La entidad financiera deberá desarrollar documentación"),
    "ri_oc::B.1.28": ("ri_oc::B.1::cierre", "En el punto B.1.24 deben informarse:"),
    "ri_oc::B.2.4": ("ri_oc::B.2::cierre", "La información solicitada en los puntos B.2.1. y B.2.3."),
    "ri_oc::B.3.4": ("ri_oc::B.3::cierre", "La información solicitada en los puntos B.3.1. y B.3.3.")}


def test_s05_legada() -> None:
    import inspect
    E0 = correr_e0.E0
    print("== t) S0-5a de U-SEG-OFICIAL: la versión legada no cambia; listas de TOs")
    p = inspect.signature(E0.parsear_cuerpo).parameters
    s = inspect.signature(E0.construir_chunks).parameters
    a = inspect.signature(E0.aplicar_cierre_al_margen).parameters
    check("parsear_cuerpo (R5-d), construir_chunks (R5-b, R5-c) y aplicar_cierre_al_margen (R5-a, R5-a′) apagados por "
          "default",
          p["numero_en_referencia"].default is False and s["intersticial_continuado"].default is False
          and s["titulo_seccion_envuelto"].default is False and a["cierre"].default is False
          and a["titulo_bloque"].default is False)
    check("listas de S0-5a: R5-a′ en ri_oc, R5-b en snp_dd y snp_cheq, R5-e en ri_ccna; ninguna regla en la tanda 0; "
          "la tolerancia de R5-a es la de E0",
          correr_e0.REGLAS_S0_5 == frozenset({"r5a", "r5a2", "r5b", "r5c", "r5d", "r5e", "r5f", "r5g"})
          and correr_e0.TOS_TITULO_BLOQUE_S0_5 == frozenset({"ri_oc"})
          and correr_e0.TOS_INTERSTICIAL_S0_5 == frozenset({"snp_dd", "snp_cheq"})
          and correr_e0.TOS_ROTULO_VERTICAL_S0_5 == frozenset({"ri_ccna"})
          and correr_e0.TOS_TANDA0_SIN_S0_5 == TOS_TANDA0 and E0.TOL_COL_R5A == E0.TOL_X)


def test_s05bis_legada() -> None:
    import inspect
    E0 = correr_e0.E0
    print("== t′) S0-5a-bis de U-SEG-OFICIAL: parámetros nuevos apagados; listas")
    p = inspect.signature(E0.parsear_cuerpo).parameters
    a = inspect.signature(E0.aplicar_cierre_al_margen).parameters
    check("parsear_cuerpo (R5-f, R5-g) y aplicar_cierre_al_margen (R5-a por lista, sin tablas) apagados por default",
          p["rotulos_por_lista"].default == () and p["raices_por_lista"].default == ()
          and a["listas"].default is None and a["excluir"].default is None)
    L = correr_e0.LISTAS_R5A_S0_5
    n = sum(len(v) for v in L.values())
    rangos = sorted(f"{to}::{k}" for to, v in L.items() for k, x in v.items() if x is not None)
    check("R5-a por lista: 43 listas, 3 con un rango de renglones (ri_rml 1.4.2 y los dos mixtos); ninguna de la tanda 0 "
          "ni de las 14 que no se tocan",
          n == 43 and rangos == ["ri2_ae::14.3", "ri_rml::1.4.2", "ri_spi::C.1.3"]
          and not set(L) & TOS_TANDA0
          and not {f"{to}::{k}" for to, v in L.items() for k in v} & set(NO_SE_TOCAN_S05BIS), f"{n}, {rangos}")
    R = correr_e0.ROTULOS_POR_LISTA_S0_5
    check("R5-f por lista: ri_ccna 11 rótulos y snp_cheq 1 (3.3.6.2, colgado de 3.3)",
          sorted(R) == ["ri_ccna", "snp_cheq"] and len(R["ri_ccna"]) == 11
          and R["snp_cheq"] == ((38, 218.2, "3.3.6.2", "3.3"),))
    check("R5-g por lista: solo ri_oc, «3. Aclaraciones» (p. 6)",
          correr_e0.RAICES_POR_LISTA_S0_5 == {"ri_oc": ((6, 117.4, "3"),)})


def _res_sintetico(secciones, n_lineas: int):
    E0 = correr_e0.E0
    return E0.ResultadoParseo(to="x", archivo="x.pdf", secciones=secciones, rechazos_header=[], saltos_numeracion=[],
                              avisos=[], accounting={"lineas_descartadas_encabezado_pie": 0, "detalle_descartes": []},
                              lineas_contenido=n_lineas, paginas_cuerpo=1)


def test_s05_sinteticos() -> None:
    E0 = correr_e0.E0
    print("== u) S0-5a de U-SEG-OFICIAL: casos sintéticos de las seis reglas")
    cuerpo = "Texto de la norma que corre en la columna del cuerpo del ítem y termina en punto final."
    cierre = "Las entidades deberán observar lo dispuesto en los puntos anteriores durante todo el plazo."
    # R5-a: lista con sangría colgante (rótulos en 110, texto en 150); el cierre al margen queda en el último ítem
    def lista(x_cierre: float):
        return [_linea("Sección 1. Requisitos.", 1, 30.0), _linea("1.1. Condiciones generales.", 1, 50.0, x0=76.0),
                _linea("1.1.1. Primer requisito.", 1, 70.0, x0=110.0), _linea(cuerpo, 1, 84.0, x0=150.0),
                _linea("1.1.2. Segundo requisito.", 1, 110.0, x0=110.0), _linea(cuerpo, 1, 124.0, x0=150.0),
                _linea("1.1.3. Tercer requisito.", 1, 150.0, x0=110.0), _linea(cuerpo, 1, 164.0, x0=150.0),
                _linea(cierre, 1, 190.0, x0=x_cierre)]
    res, ch0 = _parse([lista(110.0)])
    ev = E0.aplicar_cierre_al_margen(res, cierre=True)
    ch = E0.construir_chunks(res)
    check("R5-a: sin la regla el cierre queda en el último ítem; con ella pasa a x::1.1::cierre y el ítem conserva su "
          "cuerpo",
          (_texto(ch0, "x::1.1.3") or "").endswith(cierre) and _texto(ch, "x::1.1::cierre") == cierre
          and _texto(ch, "x::1.1.3") == "1.1.3. Tercer requisito.\n" + cuerpo
          and [e["tipo"] for e in ev] == ["cierre_al_margen_r5a"], str([c["id"] for c in ch]))
    res, _ = _parse([lista(150.0)])
    check("R5-a, caso negativo: el párrafo en la columna del texto se queda en el ítem",
          E0.aplicar_cierre_al_margen(res, cierre=True) == [])
    # R5-a′: el título de bloque y el cierre de la sección abren una sección nueva
    tb = [_linea("Sección 2. Composición.", 1, 30.0), _linea(cierre, 1, 56.0, x0=76.0),
          _linea("2.1. Primer concepto.", 1, 70.0, x0=76.0), _linea(cuerpo, 1, 84.0, x0=110.0),
          _linea("2.2. Segundo concepto.", 1, 110.0, x0=76.0), _linea(cuerpo, 1, 124.0, x0=110.0),
          _linea("Criterios de validación", 1, 150.0, x0=76.0), _linea(cierre, 1, 164.0, x0=76.0)]
    res, ch0 = _parse([tb])
    ev = E0.aplicar_cierre_al_margen(res, titulo_bloque=True)
    ch = E0.construir_chunks(res)
    check("R5-a′: «Criterios de validación» y el cierre de la sección abren x::Sbloque1, después de la sección; la sección "
          "queda sin cierre y el ítem con su texto",
          _texto(ch0, "x::S2::cierre") == cierre and "x::S2::cierre" not in {c["id"] for c in ch}
          and _texto(ch, "x::Sbloque1") == "Criterios de validación\n" + cierre
          and _texto(ch, "x::2.2") == "2.2. Segundo concepto.\n" + cuerpo
          and [c["id"] for c in ch][-1] == "x::Sbloque1" and [e["tipo"] for e in ev] == ["titulo_de_bloque_r5a2"],
          str([c["id"] for c in ch]))
    # R5-b: intersticiales de una sección entre dos hijos
    def lin(t, top, pagina=1):
        return _linea(t, pagina, top, x0=90.0)
    sec = E0.Nodo(tipo="seccion", numero="7", titulo="Campos.", pagina=1)
    h1 = E0.Nodo(tipo="punto", numero="7.1", titulo="Registro.", pagina=1, label_x0=60.0,
                 linea_label=_linea("7.1. Registro.", 1, 40.0), padre=sec)
    h2 = E0.Nodo(tipo="punto", numero="7.2", titulo="Otro.", pagina=2, label_x0=60.0,
                 linea_label=_linea("7.2. Otro.", 2, 100.0), padre=sec)
    sec.hijos = [h1, h2]
    sec.segmentos = [[lin("R95 Reversión de En- Este código podrá ser utilizado por el banco", 60.0)],
                     [lin("tidad receptora reversión de banco", 80.0), lin("presentada fuera", 92.0)],
                     [lin("Cuenta cerrada o suspendida en la que recae la transacción", 120.0)],
                     [lin("R02", 135.0)], [lin("se encuentre cerrada o suspendida.", 150.0)],
                     [lin("5. Reservado.", 180.0)], [lin("Este campo queda reservado para usos futuros.", 195.0)],
                     [lin("6. Cuenta a debitar.", 220.0)], [lin("7. Contador de registro.", 240.0)],
                     [lin("Este campo lleva el contador sin punto final", 260.0)],
                     [lin("sigue en la página siguiente", 30.0, pagina=2)]]
    res = _res_sintetico([sec], 15)
    ids0 = [c["id"] for c in E0.construir_chunks(res) if "intersticial" in c["id"]]
    chb = E0.construir_chunks(res, intersticial_continuado=True)
    idsb = [c["id"] for c in chb if "intersticial" in c["id"]]
    check("R5-b: (i) 1+2, (i′) y (i) 3+4+5, (ii) 6+7 y 9+10; 8 y 9 no (la segunda es otro rótulo); 10 y 11 no (otra "
          "página); las uniones conservan el número de la primera y las siguientes no se renumeran",
          ids0 == [f"x::S7::intersticial::{k}" for k in range(1, 12)]
          and idsb == [f"x::S7::intersticial::{k}" for k in (1, 3, 6, 8, 9, 11)]
          and _texto(chb, "x::S7::intersticial::3") == "Cuenta cerrada o suspendida en la que recae la transacción\nR02\n"
                                                        "se encuentre cerrada o suspendida.", str(idsb))
    # R5-c: chapeaux de un renglón
    def seccion(num, titulo, chapeau, top):
        s = E0.Nodo(tipo="seccion", numero=num, titulo=titulo, pagina=1)
        h = E0.Nodo(tipo="punto", numero=f"{num}.1", titulo="Punto.", pagina=1, label_x0=60.0,
                    linea_label=_linea(f"{num}.1. Punto.", 1, top + 20.0), padre=s)
        s.hijos = [h]
        s.segmentos = [[_linea(chapeau, 1, top)]]
        h.segmentos = [[_linea(cuerpo, 1, top + 30.0, x0=90.0)]]
        return s
    secs = [seccion("1", "Registro de auditores y", "permanencia en el registro", 100.0),
            seccion("2", "Seguimiento de pagos realizados con ANTE-", "RIORIDAD AL REGISTRO DEL BIEN", 200.0),
            seccion("3", 'Inscripción en el "Registro', 'de Auditores":', 300.0),
            seccion("4", "Presentación de solicitudes", "Metodología que deberán cumplimentar las entidades.", 400.0)]
    chc = E0.construir_chunks(_res_sintetico(secs, 16), titulo_seccion_envuelto=True)
    idsc = {c["id"] for c in chc}
    her = next(c for c in chc if c["id"] == "x::1.1")["herencia"][0]["texto"]
    check("R5-c: (b), (a) y (c)+(d) juntan el chapeau al título y no lo emiten; el chapeau que es una oración completa "
          "después de un título completo queda",
          not idsc & {"x::S1::chapeau_seccion", "x::S2::chapeau_seccion", "x::S3::chapeau_seccion"}
          and "x::S4::chapeau_seccion" in idsc
          and her == "Sección 1. Registro de auditores y\npermanencia en el registro", her)
    # R5-d: número de punto que continúa una remisión
    rd = [_linea("Sección 1. Normas.", 1, 30.0), _linea("1.1. Alcance.", 1, 50.0, x0=76.0),
          _linea(cuerpo, 1, 64.0, x0=100.0), _linea("1.2. Integración.", 1, 90.0, x0=76.0),
          _linea("1.2.1. Primer punto.", 1, 110.0, x0=100.0),
          _linea("Se computa de acuerdo con el procedimiento descripto en el punto", 1, 124.0, x0=120.0),
          _linea("1.3. “Integración” de las presentes normas, en la parte pertinente.", 1, 138.0, x0=120.0),
          _linea("Las entidades informarán los conceptos y montos previstos en los puntos 1.1. y", 1, 152.0, x0=120.0),
          _linea("1.2.2. Segundo punto, que se incluye en la lista.", 1, 166.0, x0=120.0),
          _linea("1.2.3. Tercer punto.", 1, 190.0, x0=100.0),
          _linea("Rige lo previsto en el punto", 1, 204.0, x0=120.0),
          _linea("1.3. Integración del período.", 1, 230.0, x0=76.0)]
    _, ch0 = _parse([rd])
    resd, chd = _parse([rd], numero_en_referencia=True)
    check("R5-d: «…en el punto» / «1.3. “Integración”…» sigue como prosa de 1.2.1; tras «y» el 1.2.2 es encabezado; "
          "«1.3. Integración del período.», en la columna de sus hermanos, abre el 1.3",
          "x::1.3" in {c["id"] for c in ch0} and (_texto(ch0, "x::1.2.1") or "").count("\n") == 1
          and "1.3. “Integración”" in (_texto(chd, "x::1.2.1") or "")
          and (_texto(chd, "x::1.3") or "").startswith("1.3. Integración del período.")
          and "x::1.2.2" in {c["id"] for c in chd} and "x::1.2.3" in {c["id"] for c in chd}
          and [r["motivo"] for r in resd.rechazos_header] == ["numero_en_referencia_r5d"],
          str([(c["id"], c["texto"][:30]) for c in chd]))
    # R5-e: rótulo vertical repartido entre dos unidades
    s1 = E0.Nodo(tipo="seccion", numero="1", titulo="Formulario 3.", pagina=1, linea_label=_linea("Formulario 3.", 1, 10.0),
                 sintetica=True)
    s1.segmentos = [[_linea(cuerpo, 1, 30.0), _linea("C", 1, 68.0, x0=380.0)]]
    s2 = E0.Nodo(tipo="seccion", numero="2", titulo="Formulario 4.", pagina=1, linea_label=_linea("Formulario 4.", 1, 73.0),
                 sintetica=True)
    s2.segmentos = [[_linea("O", 1, 78.5, x0=380.0), _linea("MEMBRETE DEL FORMULARIO", 1, 82.0),
                     _linea("D", 1, 89.0, x0=380.0), _linea("I", 1, 99.0, x0=381.5), _linea("G", 1, 109.5, x0=380.0),
                     _linea("O", 1, 120.0, x0=380.0), _linea(cuerpo, 1, 131.0)]]
    rese = _res_sintetico([s1, s2], 11)
    eve = E0.juntar_rotulo_vertical(rese)
    che = E0.construir_chunks(rese)
    cob = E0.verificar_cobertura(rese)
    check("R5-e: «C», «O», «D», «I», «G», «O» se juntan en «CODIGO», en la unidad de la página que tiene la última letra; "
          "la cobertura sigue exacta",
          _texto(che, "x::S1") == "Formulario 3.\n" + cuerpo
          and _texto(che, "x::S2") == f"Formulario 4.\nMEMBRETE DEL FORMULARIO\nCODIGO\n{cuerpo}"
          and len(eve) == 1 and cob["cobertura_exacta"], str(cob))


def test_s05_casos(d: Path) -> None:
    print(f"== v) S0-5a de U-SEG-OFICIAL: un caso medido por regla (e0-r2 sobre {len(TOS_S05)} TOs)")
    correr_e0.correr(d, manifiesto=_ManifiestoParticion(TOS_S05), version_e0="e0-r2")
    ch = {to: {c["id"]: c for c in cargar(d, f"chunks_{to}.json")} for to in TOS_S05}

    def txt(uid: str) -> str:
        return ch[uid.split("::")[0]].get(uid, {}).get("texto", "")

    ok_a = []
    for item, (cid, primero) in CIERRES_R5A.items():
        ok_a.append(txt(cid).startswith(primero) and primero not in txt(item))
    check("R5-a: los 9 casos del mecanismo 1 quedan con el cierre en el del padre, fuera del ítem", all(ok_a), str(ok_a))
    malos = [i for i, h in CORRECTOS_116.items() if ch[i.split("::")[0]].get(i, {}).get("sha256_propio", "")[:16] != h]
    check("R5-a, casos negativos: los 27 candidatos del 1.16 marcados correctos en S1-bis no cambian", not malos, str(malos))
    oc = ch["ri_oc"]
    check("R5-a′, ri_oc: el bloque de validaciones es ri_oc::Sbloque1, con sus dos títulos; C.11 termina en su texto; "
          "ri_oc::SC::cierre no existe y ninguna herencia de C.1 a C.11 tiene tramos del bloque",
          txt("ri_oc::Sbloque1").startswith("Criterios de validación\nValidación del Apartado A – Operaciones de cambios")
          and txt("ri_oc::C.11").endswith("para el último día de cada mes).") and "ri_oc::SC::cierre" not in oc
          and not any("Criterios de validación" in t["texto"] or "Se considerará no validada" in t["texto"]
                      for k in range(1, 12) for t in oc[f"ri_oc::C.{k}"]["herencia"]))
    quitadas_dd = {f"snp_dd::S7::intersticial::{k}" for k in (8, 9, 14, 18, 20, 24, 30, 32, 34, 36, 38, 40, 42, 44, 49,
                                                              53, 55)}
    quitadas_cheq = {f"snp_cheq::7.1::intersticial::{k}" for k in (12, 14, 17, 19)}
    check("R5-b: en snp_dd se unen 13+14, 7+8+9 y 14 pares de rótulo y descripción; en snp_cheq, 4 pares; la unión "
          "conserva el número de la primera",
          not quitadas_dd & set(ch["snp_dd"]) and not quitadas_cheq & set(ch["snp_cheq"])
          and "snp_dd::S7::intersticial::15" in ch["snp_dd"]
          and "tidad receptora" in txt("snp_dd::S7::intersticial::13")
          and "R02" in txt("snp_dd::S7::intersticial::7") and "se encuentre cerrada" in txt("snp_dd::S7::intersticial::7"))
    sin = ["ri2_ae::S2::chapeau_seccion", "ri_ccna::D1A1::S2::chapeau_seccion", "ri_ccna::D1A3L2::S26::chapeau_seccion",
           "ri_ccna::D1A3L2::S29::chapeau_seccion", "ri_ccna::D1F2::S3::chapeau_seccion",
           "ri_ccna::D1F6::S3::chapeau_seccion", "ri_spi::SB::chapeau_seccion", "ri_spi::SC::chapeau_seccion"]
    con = ["inspag::S3::chapeau_seccion", "pfmipyme::S3::chapeau_seccion", "ri_cr::S3::chapeau_seccion",
           "snp_psp::S3::chapeau_seccion"]
    hijo_c = next(c for i, c in ch["ri_spi"].items() if i.startswith("ri_spi::C.") and c["tipo"] != "mini_chunk")
    check("R5-c: los 8 títulos de dos renglones medidos acá (el noveno es manual, fuera de esta corrida) quedan sin "
          "chapeau; los 4 chapeaux de verdad quedan; el título de C de ri_spi, entero en la herencia",
          not any(i in ch[i.split("::")[0]] for i in sin) and all(i in ch[i.split("::")[0]] for i in con)
          and any(t["texto"].endswith("APARTADO B") for t in hijo_c["herencia"]))
    tr = ch["snp_tr"]
    check("R5-d: ri_rml::1.2.3 termina en «estadounidenses-.», existen 1.2.4 y el 1.3 verdadero; snp_tr::1.3.3 termina "
          "en «…entre CEC:», existen 1.3.4 a 1.5.2.2 y el 1.6 abre en «1.6. Transacciones.»; ninguna unidad es solo "
          "el renglón de la remisión",
          txt("ri_rml::1.2.3").endswith("estadounidenses-.") and "ri_rml::1.2.4" in ch["ri_rml"]
          and txt("ri_rml::1.3").startswith("1.3. Integración del período")
          and txt("snp_tr::1.3.3").endswith("el esquema de compensación entre CEC:")
          and all(f"snp_tr::{k}" in tr for k in ("1.3.4.1", "1.3.4.2", "1.3.5.1", "1.3.5.2", "1.3.5.3", "1.3.6.1",
                                                 "1.3.6.2", "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.5.1",
                                                 "1.5.2.1", "1.5.2.2"))
          and any(t["texto"] == "1.6. Transacciones." for t in tr["snp_tr::1.6.1"]["herencia"])
          and "snp_tr::1.6::intro" not in tr)
    check("R5-d, casos negativos: gerc 2.4.2, rdbcra 11.12, ordcom 1.6.2 y pimf 4.18 siguen siendo encabezados",
          "gerc::2.4.2" in ch["gerc"] and any(i.startswith("rdbcra::11.12") for i in ch["rdbcra"])
          and "ordcom::1.6.2" in ch["ordcom"] and "pimf::4.18::intro" in ch["pimf"] and "pimf::4.18.1" in ch["pimf"])
    f4 = txt("ri_ccna::D1F4::S0")
    check("R5-e: ri_ccna::D1F3::S0 termina en «Fórm. 4368 C (II-2006)», sin la «C» suelta, y D1F4::S0 lleva «CODIGO» "
          "y ninguna letra suelta",
          txt("ri_ccna::D1F3::S0").endswith("Fórm. 4368 C (II-2006)") and "\nCODIGO\n" in f4
          and not any(len(r.strip()) == 1 and r.strip().isupper() for r in f4.split("\n")))
    cob = cargar(d, "cobertura.json")
    check(f"cobertura exacta en los {len(TOS_S05)} TOs", all(cob[to]["cobertura_exacta"] for to in TOS_S05))


# ------------------------------------------------------------------ S0-5a-bis de U-SEG-OFICIAL
TOS_S05BIS = ("ri_rml", "ri_spi", "ri2_ae", "ri_ccna", "snp_cheq", "apnf", "cirmo3", "cryl", "gerc", "gescre",
              "inspag", "manori", "ri_ot", "ri_pnp", "seggar", "manual", "ri_cc", "ri_oc", "nmaeef", "ri_saofe",
              "ri2_cs", "ri_laft")
# los 87 rechazos por columna profunda (raíz más adentro que la columna de las raíces) de los 7 documentos fuera de la
# tanda 1, que R5-g no toca: por documento, y el sha256 de la lista ordenada «to|página|texto|motivo» en S0-4b
RECHAZOS_G3_S05BIS = ({"manual": 23, "nmaeef": 24, "ri2_ae": 15, "ri2_cs": 7, "ri_laft": 2, "ri_saofe": 15, "seggar": 1},
                      "2e9f86598f7483d8")
# las 14 listas que no se tocan: el sha256 del texto propio del último ítem en la salida de S0-4b (unido, si se parte)
# y el cierre del padre, con el sha256 de su texto si existía
NO_SE_TOCAN_S05BIS = {
    "apnf::1.3.2.5": ("78369ee7eb369ccd", "apnf::1.3.2::cierre", "e0a9c91eff80facf"),
    "cirmo3::1.2.11.3": ("1c3d74a3cff055b0", "cirmo3::1.2.11::cierre", None),
    "cirmo3::1.2.23.3": ("10ab8c34dad0919c", "cirmo3::1.2.23::cierre", None),
    "cryl::12.2": ("9d303f55a2f7094a", "cryl::S12::cierre", None),
    "gerc::2.4.3": ("1937c9e6b7cffbad", "gerc::2.4::cierre", None),
    "gescre::1.2.8.2": ("7f5887bfd4dab4f5", "gescre::1.2.8::cierre", None),
    "inspag::3.3.2": ("2e048de30b1524f7", "inspag::3.3::cierre", None),
    "manori::3.5.2": ("6514f904a7fa799a", "manori::3.5::cierre", None),
    "ri2_ae::3.3": ("2e458be65f2e4294", "ri2_ae::S3::cierre", None),
    "ri_ot::13.4": ("005c8cd4e4666b05", "ri_ot::S13::cierre", None),
    "ri_pnp::5.7": ("ab26d8716ce3c6e0", "ri_pnp::S5::cierre", None),
    "seggar::5.3.5": ("dc2ebf1a8922ac99", "seggar::5.3::cierre", None),
    "manual::2.3.2": ("bf0d789ed10b00b6", "manual::2.3::cierre", None),
    "ri_cc::R5::2.2.1.2": ("80ce0925d5804a66", "ri_cc::R5::2.2.1::cierre", None)}
# los renglones del cierre de los dos mixtos (lista v2 de la revisión de S0-5a) y el sha256 del resto del ítem en S0-4b
MIXTOS_S05BIS = {
    "ri_spi::C.1.3": ("ri_spi::C.1::cierre", (
        "Además de los datos detallados precedentemente, el formulario permitirá visualizar la si-",
        "guiente información:", "- Código Único de Identificación Tributaria (C.U.I.T) del responsable del pago",
        "- Número de Boleto", "- Concepto de Liquidación", "- Moneda", "- Fecha de Vencimiento", "- Importe pendiente",
        "La entidad informante es la responsable final por la totalidad de los datos que estén incluidos",
        "en la denuncia, debiendo realizar los ajustes necesarios en caso de no estar de acuerdo con",
        "los datos reflejados en el formulario."), "b42412e80d009cb5"),
    "ri2_ae::14.3": ("ri2_ae::S14::cierre", (
        "La fecha de la manifestación escrita deberá coincidir con la fecha del",
        "informe del auditor sobre los estados financieros de publicación.",
        "En caso de que la manifestación escrita señalada no haya sido puesta a",
        "disposición, o la misma no sea consistente con la evidencia de auditoría",
        "obtenida, el auditor deberá evaluar el impacto de dicha situación al",
        "momento de emitir su opinión sobre los estados financieros de", "publicación."), "cce522c30ce724f0")}
# tablas que se serializan: la unidad y el sha256 del bloque en S0-4b (gerc::tabla005; y las tres que el R5-a de S0-5a,
# sin la guarda de tablas, dejaba de serializar)
TABLAS_S05BIS = {
    "gerc::tabla005": ("gerc::4.3.2", "f12c2a7af01b108d"),
    "manori::tabla014": ("manori::3.5.2", "53ea3f953d5fe35a"),
    "manori::tabla015": ("manori::3.5.2", "3df76823a2134c2d"),
    "ri_spi::tabla001": ("ri_spi::C.1.3", "17a05588e249b12c")}


def _sha16(t: str) -> str:
    import hashlib
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def test_s05bis_sinteticos() -> None:
    E0 = correr_e0.E0
    print("== w) S0-5a-bis de U-SEG-OFICIAL: casos sintéticos")
    cuerpo = "Texto de la norma que corre en la columna del cuerpo del ítem y termina en punto final."
    cierre = "Las entidades deberán observar lo dispuesto en los puntos anteriores durante todo el plazo."

    def dos_listas():
        return [_linea("Sección 1. Requisitos.", 1, 30.0), _linea("1.1. Condiciones generales.", 1, 50.0, x0=76.0),
                _linea("1.1.1. Primer requisito.", 1, 70.0, x0=110.0), _linea(cuerpo, 1, 84.0, x0=150.0),
                _linea("1.1.2. Segundo requisito.", 1, 110.0, x0=110.0), _linea(cuerpo, 1, 124.0, x0=150.0),
                _linea(cierre, 1, 150.0, x0=110.0),
                _linea("1.2. Otras condiciones.", 1, 180.0, x0=76.0),
                _linea("1.2.1. Primer caso.", 1, 200.0, x0=110.0), _linea(cuerpo, 1, 214.0, x0=150.0),
                _linea("1.2.2. Segundo caso.", 1, 240.0, x0=110.0), _linea(cuerpo, 1, 254.0, x0=150.0),
                _linea("Ello, sin perjuicio de lo previsto en otras secciones de estas normas.", 1, 280.0, x0=110.0)]
    res, _ = _parse([dos_listas()])
    ev = E0.aplicar_cierre_al_margen(res, cierre=True, listas={"1.2.2": None})
    ch = E0.construir_chunks(res)
    check("R5-a por lista: solo la lista dada (1.2) pasa su cierre al del padre; la otra (1.1) queda como en S0-4b",
          "x::1.2::cierre" in {c["id"] for c in ch} and "x::1.1::cierre" not in {c["id"] for c in ch}
          and (_texto(ch, "x::1.1.2") or "").endswith(cierre) and [e["item"] for e in ev] == ["1.2.2"],
          str([c["id"] for c in ch]))
    res, _ = _parse([dos_listas()])
    ev = E0.aplicar_cierre_al_margen(res, cierre=True, listas={"1.1.2": ("rango", (1, 124.0, "Texto de la norma"),
                                                                         (1, 150.0, "Las entidades"))})
    ch = E0.construir_chunks(res)
    check("R5-a por lista con un rango: exactamente los renglones del rango pasan al cierre (aunque el primero esté en "
          "la columna del texto)",
          _texto(ch, "x::1.1::cierre") == cuerpo + "\n" + cierre and _texto(ch, "x::1.1.2") == "1.1.2. Segundo requisito."
          and ev and ev[0]["modo"] == "rango", str([(c["id"], c["texto"][:30]) for c in ch]))
    res, _ = _parse([dos_listas()])
    ev = E0.aplicar_cierre_al_margen(res, cierre=True, listas={"1.1.2": None},
                                     excluir=lambda l: l.pagina == 1 and 145.0 <= l.top <= 155.0)
    ch = E0.construir_chunks(res)
    check("R5-a sin tablas: el párrafo con un renglón de tabla no se mueve, y queda registrado",
          "x::1.1::cierre" not in {c["id"] for c in ch} and (_texto(ch, "x::1.1.2") or "").endswith(cierre)
          and [e["tipo"] for e in ev] == ["r5a_no_mueve_tabla"], str(ev))
    pag = [_linea("Sección 2. Auditores.", 1, 30.0), _linea("2.1. Podrán prestar servicios quienes:", 1, 50.0, x0=76.0),
           _linea("2.1.1.no sean socios de la entidad auditada, o de", 1, 70.0, x0=110.0),
           _linea("empresas vinculadas a ella;", 1, 84.0, x0=150.0),
           _linea("2.1.2.no se desempeñen en relación de dependencia;", 1, 110.0, x0=110.0),
           _linea("2.2. Inscripción.", 1, 140.0, x0=76.0), _linea("Texto de la inscripción.", 1, 154.0, x0=110.0),
           _linea("2.2.2.1. Instrucciones operativas.", 1, 180.0, x0=146.0),
           _linea("Texto de las instrucciones.", 1, 194.0, x0=180.0)]
    _, ch0 = _parse([pag])
    rot = ((1, 70.0, "2.1.1", None), (1, 110.0, "2.1.2", None), (1, 180.0, "2.2.2.1", "2.2"))
    res, ch = _parse([pag], rotulos_por_lista=rot)
    ids = [c["id"] for c in ch]
    check("R5-f: «2.1.1.no sean…» y «2.1.2.no se…» abren sus puntos (pegados y en minúscula) y «2.2.2.1.» abre colgado "
          "de 2.2, su padre dado; el texto de los renglones no cambia; sin la lista, no abren",
          "x::2.1.1" not in {c["id"] for c in ch0} and "x::2.2.2.1" not in {c["id"] for c in ch0}
          and "x::2.1.1" in ids and "x::2.1.2" in ids and "x::2.2.2.1" in ids
          and _texto(ch, "x::2.1.1") == "2.1.1.no sean socios de la entidad auditada, o de\nempresas vinculadas a ella;"
          and [t["unidad_origen"] for t in next(c for c in ch if c["id"] == "x::2.2.2.1")["herencia"]
               if t["tipo"] == "encabezado"][-1] == "2.2"
          and sum(1 for a in res.avisos if a["tipo"] == "rotulo_por_lista_r5f") == 3, str(ids))
    raices = [_linea("1. Alcance", 1, 30.0, x0=60.0), _linea("1.1. Texto del punto uno.", 1, 50.0, x0=80.0),
              _linea("2. Anulaciones", 1, 80.0, x0=60.0), _linea("2.1. Texto del punto dos.", 1, 100.0, x0=80.0),
              _linea("3. Aclaraciones", 1, 130.0, x0=70.0), _linea("3.1. Texto del punto tres.", 1, 150.0, x0=88.0)]
    res0, ch0 = _parse([raices], modo_sin_raiz=True)
    res, ch = _parse([raices], modo_sin_raiz=True, raices_por_lista=((1, 130.0, "3"),))
    her = next((c for c in ch if c["id"] == "x::3.1"), {}).get("herencia", [])
    check("R5-g: «3. Aclaraciones», más adentro que la columna de las raíces, se rechaza sin la lista y queda al final de "
          "la sección 2; con la lista abre la raíz 3 con su título, que hereda 3.1",
          any(r["motivo"].startswith("raiz_en_columna_profunda") for r in res0.rechazos_header)
          and "3. Aclaraciones" in (_texto(ch0, "x::2.1") or "") + (_texto(ch0, "x::S2") or "")
          and not any(r["motivo"].startswith("raiz_en_columna_profunda") for r in res.rechazos_header)
          and "3. Aclaraciones" not in (_texto(ch, "x::2.1") or "") + (_texto(ch, "x::S2") or "")
          and [t["texto"] for t in her if t["tipo"] == "encabezado"][:1] == ["3. Aclaraciones"]
          and [a["tipo"] for a in res.avisos if a["tipo"] == "raiz_por_lista_r5g"] == ["raiz_por_lista_r5g"],
          str([(c["id"], c["texto"][:25]) for c in ch]))


def test_s05bis_casos(d: Path) -> None:
    print(f"== w′) S0-5a-bis de U-SEG-OFICIAL: casos medidos (e0-r2 sobre {len(TOS_S05BIS)} TOs)")
    correr_e0.correr(d, manifiesto=_ManifiestoParticion(TOS_S05BIS), version_e0="e0-r2")
    ch = {to: {c["id"]: c for c in cargar(d, f"chunks_{to}.json")} for to in TOS_S05BIS}

    def txt(uid: str):
        c = ch[uid.split("::")[0]]
        if uid in c:
            return c[uid]["texto"]
        ps = sorted((i for i in c if i.startswith(uid + "::parte")), key=lambda i: int(i.rsplit("parte", 1)[1]))
        return "\n".join(c[i]["texto"] for i in ps) if ps else None

    cie = (txt("ri_rml::1.4::cierre") or "").split("\n")
    check("ri_rml 1.4.2: el cierre de 1.4 empieza en «Para el punto 1.4.1.» y termina en «…671000/M-TP.»; el ítem queda "
          "con su rótulo y sus dos fórmulas",
          bool(cie) and cie[0].startswith("Para el punto 1.4.1.") and cie[-1].endswith("671000/M-TP.") and len(cie) == 19
          and len((txt("ri_rml::1.4.2") or "").split("\n")) == 3, f"{len(cie)} renglones")
    for item, (cid, ren, sha_resto) in MIXTOS_S05BIS.items():
        check(f"{item}: el cierre ({cid}) es, renglón por renglón, el de la lista v2, y el resto del ítem es el de S0-4b",
              (txt(cid) or "").split("\n") == list(ren) and _sha16(txt(item) or "") == sha_resto)
    a1 = ch["ri_ccna"]
    check("R5-f, ri_ccna: 2.1.1 a 2.1.8 de D1A1 abren («2.1.1.no sean socios…»), y 5.1 de D1A1 y de D1A2 y 8.1 de D1A1; "
          "el chapeau de la sección 5 de D1A1 ya no lleva «5.1.»",
          all(f"ri_ccna::D1A1::2.1.{k}" in a1 for k in range(1, 9))
          and (txt("ri_ccna::D1A1::2.1.1") or "").startswith("2.1.1.no sean socios")
          and (txt("ri_ccna::D1A1::5.1") or "").startswith("5.1.Designación.")
          and "ri_ccna::D1A1::8.1" in a1 and (txt("ri_ccna::D1A2::5.1") or "").startswith("5.1.Perfil")
          and "5.1." not in (txt("ri_ccna::D1A1::S5::chapeau_seccion") or ""))
    u = ch["snp_cheq"].get("snp_cheq::3.3.6.2")
    check("R5-f, snp_cheq: 3.3.6.2 abre como unidad propia, colgada de 3.3 (sin 3.3.6 en la herencia)",
          u is not None and u["texto"].startswith("3.3.6.2. Instrucciones operativas.")
          and [t["unidad_origen"] for t in u["herencia"] if t["tipo"] == "encabezado"][-1] == "3.3"
          and not any(t["unidad_origen"] == "3.3.6" for t in u["herencia"]))
    oc = ch["ri_oc"]
    tres = [i for i in oc if i.startswith("ri_oc::3.")]
    check("R5-g, ri_oc: «3. Aclaraciones» sale de ri_oc::S2 y abre la sección 3; las 51 unidades de 3.1 a 3.51 heredan "
          "«3. Aclaraciones»",
          not (txt("ri_oc::S2") or "").endswith("3. Aclaraciones") and len(tres) == 51
          and all([t["texto"] for t in oc[i]["herencia"] if t["unidad_origen"] == "S3"] == ["3. Aclaraciones"]
                  for i in tres), f"{len(tres)} unidades")
    import hashlib
    filas_g3 = []
    for to in RECHAZOS_G3_S05BIS[0]:
        e = cargar(d, f"estructura_{to}.json")
        filas_g3 += [(to, f"{to}|{r['pagina']}|{r['texto']}|{r['motivo']}") for r in e["rechazos_header"]
                     if r["motivo"].startswith("raiz_en_columna_profunda")]
    por_to = {to: sum(1 for t, _ in filas_g3 if t == to) for to in RECHAZOS_G3_S05BIS[0]}
    huella = hashlib.sha256("\n".join(sorted(f for _, f in filas_g3)).encode("utf-8")).hexdigest()[:16]
    check("R5-g, caso negativo: los 87 rechazos por columna profunda de los 7 documentos fuera de la tanda 1 quedan como "
          "en S0-4b", por_to == RECHAZOS_G3_S05BIS[0] and huella == RECHAZOS_G3_S05BIS[1], f"{len(filas_g3)}, {huella}")
    malos = []
    for item, (sha_item, cid, sha_cierre) in NO_SE_TOCAN_S05BIS.items():
        tc = txt(cid)
        if _sha16(txt(item) or "") != sha_item or (None if tc is None else _sha16(tc)) != sha_cierre:
            malos.append(item)
    check("las 14 listas que no se tocan: el último ítem y el cierre del padre, con el texto propio de S0-4b", not malos,
          str(malos))
    import re
    malas = []
    for tid, (uid, sha) in TABLAS_S05BIS.items():
        m = re.search(r"\[TABLA (" + re.escape(tid) + r") \|.*?\[FIN TABLA \1\]", txt(uid) or "", re.S)
        if not m or _sha16(m.group(0)) != sha:
            malas.append(tid)
    check("tablas: gerc::tabla005, manori::tabla014 y tabla015 y ri_spi::tabla001 siguen serializadas, como en S0-4b",
          not malas, str(malas))
    cob = cargar(d, "cobertura.json")
    check(f"cobertura exacta en los {len(TOS_S05BIS)} TOs", all(cob[to]["cobertura_exacta"] for to in TOS_S05BIS))


# ------------------------------------------------------------------ S0-6a de U-SEG-OFICIAL
import contextlib


@contextlib.contextmanager
def _sin_s06():
    """Las pruebas de etapas anteriores prueban sus reglas: corren con las reglas de S0-6a apagadas (también las reglas
    por lista que S0-6a reemplaza, que vuelven a correr)."""
    previas = correr_e0.REGLAS_S0_6
    correr_e0.REGLAS_S0_6 = frozenset()
    try:
        yield
    finally:
        correr_e0.REGLAS_S0_6 = previas


@contextlib.contextmanager
def _tanda0_sin_exclusion():
    """Solo en el selftest: la exclusión de la tanda 0 apagada, para correr las filas de la tanda 0 como casos positivos.
    No toca el camino de `correr_e0` que produce la salida."""
    previa = correr_e0.TOS_TANDA0_SIN_S0_6
    correr_e0.TOS_TANDA0_SIN_S0_6 = frozenset()
    try:
        yield
    finally:
        correr_e0.TOS_TANDA0_SIN_S0_6 = previa


def test_s06_legada() -> None:
    import inspect
    E0 = correr_e0.E0
    print("== x) S0-6a de U-SEG-OFICIAL: parámetros apagados por default; listas; A a K fuera de la tanda 0")
    p = inspect.signature(E0.parsear_cuerpo).parameters
    nuevos = ("raiz_sucesora_e", "numero_partido_g", "numero_pegado_h", "pie_formulario_k", "caratula_j",
              "encabezado_tabla_f", "recuadro_i", "banda_a")
    q = inspect.signature(E0.construir_chunks).parameters
    check("parsear_cuerpo, construir_chunks, separar_encabezado_pie y limites_subdocumento: los parámetros de A a K "
          "apagados por default; Linea.palabras vacío por default",
          all(p[k].default is False for k in nuevos) and q["encabezado_b"].default is False
          and q["rotulo_impreso_d"].default is False
          and inspect.signature(E0.separar_encabezado_pie).parameters["pie_formulario_k"].default is False
          and inspect.signature(E0.limites_subdocumento).parameters["solo_anexo"].default is False
          and _linea("x", 1, 1.0).palabras == ())
    check("S0-6a-bis: los parámetros de L, M y de las listas fijas de C, apagados por default",
          p["indice_l"].default == frozenset() and q["raiz0_solo_titulo_m"].default is False
          and inspect.signature(E0.asignar_por_columna_c).parameters["listas_fijas"].default == frozenset())
    l6 = correr_e0.LISTAS_R5A_S0_6
    check("S0-6a-bis: R5-a por lista que queda con C, ocho listas tomadas de LISTAS_R5A_S0_5 con su forma; M no corre donde "
          "los sub-documentos son de S0-4",
          sum(len(v) for v in l6.values()) == 8
          and all(correr_e0.LISTAS_R5A_S0_5[to][k] == v for to, d in l6.items() for k, v in d.items())
          and correr_e0._sd_s04("ri_ccna") and not correr_e0._sd_s04("ri2_ae"))
    check("listas de S0-6a: las trece reglas (once de S0-6a y L y M de S0-6a-bis); la tanda 0 fuera por la misma lista de "
          "diez TOs; los reemplazos (C de R5-a, A de R5-a′, E de R5-g, H de R5-f en ri_ccna); la tolerancia de C es TOL_X",
          correr_e0.REGLAS_S0_6 == frozenset("abcdefghijklm") and correr_e0.TOS_TANDA0_SIN_S0_6 == TOS_TANDA0
          and correr_e0.REEMPLAZOS_S0_6 == {"r5a": ("c", None), "r5a2": ("a", None), "r5g": ("e", None),
                                             "r5f": ("h", frozenset({"ri_ccna"}))}
          and E0.TOL_COL_C == E0.TOL_X)
    check("A a M no corren en ningún TO de la tanda 0; las reglas por lista reemplazadas no corren donde corre su "
          "reemplazo (R5-f sigue en snp_cheq)",
          not any(correr_e0._r6(r, to) for r in "abcdefghijklm" for to in TOS_TANDA0)
          and not correr_e0._r5("r5a", "cryl", frozenset({"cryl"}))
          and not correr_e0._r5("r5a2", "ri_oc", frozenset({"ri_oc"}))
          and not correr_e0._r5("r5g", "ri_oc", frozenset({"ri_oc"}))
          and not correr_e0._r5("r5f", "ri_ccna", frozenset({"ri_ccna"}))
          and correr_e0._r5("r5f", "snp_cheq", frozenset({"snp_cheq"})))
    with _sin_s06():
        check("con las reglas de S0-6a apagadas, las reglas por lista vuelven a correr",
              correr_e0._r5("r5a", "cryl", frozenset({"cryl"})) and correr_e0._r5("r5g", "ri_oc", frozenset({"ri_oc"})))


def _lp(partes, pagina: int, top: float):
    """Renglón con las posiciones de sus palabras (para I): `partes` es [(x0, texto)], una por columna."""
    pals = []
    for x0, t in partes:
        x = x0
        for w in t.split():
            pals.append((x, x + 5.0 * len(w), w))
            x += 5.0 * len(w) + 3.0
    return correr_e0.E0.Linea(pagina=pagina, top=top, x0=partes[0][0], texto=" ".join(t for _, t in partes),
                              ngaps=len(partes) - 1, ultimo_numerico=False, primer_codigo=False, palabras=tuple(pals))


def test_s06_sinteticos() -> None:
    E0 = correr_e0.E0
    print("== y) S0-6a de U-SEG-OFICIAL: casos sintéticos (lo que cada regla hace y lo que la nota dice que no hace)")
    cuerpo = "Texto de la norma que corre en la columna del cuerpo del ítem y termina en punto final."
    cierre = "Las entidades deberán observar lo dispuesto en los puntos anteriores durante todo el plazo."
    # A: título que encabeza solo su bloque; D18; fila de tabla
    pa = [_linea("Sección 3. Criterios.", 1, 30.0), _linea("3.1. Primer criterio.", 1, 50.0, x0=76.0),
          _linea(cuerpo, 1, 64.0, x0=100.0), _linea("3.2. Segundo criterio.", 1, 90.0, x0=76.0),
          _linea(cuerpo, 1, 104.0, x0=100.0), _linea("TABLA DE CORRESPONDENCIA DE PARTIDAS", 2, 40.0, x0=76.0),
          _linea("Partida Cuenta", 2, 56.0, x0=76.0, ngaps=1), _linea("Resultado monetario 131145", 2, 70.0, x0=76.0,
                                                                     ngaps=1)]
    res, _ = _parse([pa])
    ev = E0.dividir_a(res, sin_raiz=False)
    ch = E0.construir_chunks(res)
    check("A: «TABLA DE CORRESPONDENCIA…» abre x::Sbloque1, que cuelga de la sección real; 3.2 termina en su texto",
          _texto(ch, "x::3.2") == "3.2. Segundo criterio.\n" + cuerpo
          and (_texto(ch, "x::Sbloque1") or "").startswith("TABLA DE CORRESPONDENCIA DE PARTIDAS\nPartida Cuenta")
          and [e["forma"] for e in ev if e["tipo"] == "division_a"] == ["titulo"], str([c["id"] for c in ch]))
    res, _ = _parse([pa])
    check("A, caso negativo: una fila de tabla serializada no abre división",
          E0.dividir_a(res, sin_raiz=False, fila_tabla=lambda l: l.texto.startswith("TABLA")) == [])
    pd = [_linea("Sección 4. Normas.", 1, 30.0), _linea(cierre, 1, 50.0, x0=76.0),
          _linea("Instrucciones generales", 1, 76.0, x0=76.0), _linea("4.1. Primera instrucción.", 1, 96.0, x0=76.0),
          _linea(cuerpo, 1, 110.0, x0=100.0)]
    res, _ = _parse([pd])
    check("A, caso negativo (D18): el renglón entre la madre y sus hijos numerados no abre división",
          E0.dividir_a(res, sin_raiz=False) == [])
    # B
    pb = [_linea("Sección 1. Reglas.", 1, 30.0),
          _linea("1.1. Las entidades deberán observar las siguientes condiciones durante todo el plazo de la", 1, 50.0,
                 x0=76.0),
          _linea("operación y hasta su cancelación total:", 1, 64.0, x0=100.0),
          _linea("1.1.1. Primera condición.", 1, 90.0, x0=100.0), _linea("1.1.2. Segunda condición.", 1, 110.0, x0=100.0)]
    res, _ = _parse([pb])
    h0 = next(c for c in E0.construir_chunks(res) if c["id"] == "x::1.1.1")["herencia"]
    h = next(c for c in E0.construir_chunks(res, encabezado_b=True) if c["id"] == "x::1.1.1")["herencia"]
    check("B (B2): el número seguido de un párrafo no fabrica encabezado; la intro lleva el texto entero con su número",
          [t["tipo"] for t in h if t["unidad_origen"] == "1.1"] == ["intro"]
          and next(t for t in h if t["unidad_origen"] == "1.1")["texto"].startswith("1.1. Las entidades deberán")
          and [t["tipo"] for t in h0 if t["unidad_origen"] == "1.1"] == ["encabezado", "intro"], str(h))
    pt = [_linea("Sección 2. Dispositivos.", 1, 30.0),
          _linea("2.13. Promoción de servicios en dispositivos móviles e identificación de clientes con Documento", 1,
                 50.0, x0=76.0),
          _linea("Nacional de Identidad digital en formato credencial virtual.", 1, 64.0, x0=104.0),
          _linea("Bajo la supervisión de personas autorizadas, se podrán utilizar dispositivos en estos casos:", 1,
                 90.0, x0=104.0),
          _linea("2.13.1. para promocionar aplicaciones; y", 1, 116.0, x0=104.0),
          _linea("2.13.2. para identificar clientes.", 1, 136.0, x0=104.0),
          _linea("2.14. Recinto para operaciones importantes.", 1, 170.0, x0=76.0), _linea(cuerpo, 1, 184.0, x0=104.0),
          _linea("2.14.1. Primer recinto.", 1, 200.0, x0=104.0)]
    res, _ = _parse([pt])
    ch0, ch = E0.construir_chunks(res), E0.construir_chunks(res, encabezado_b=True)
    enc = [t["texto"] for t in next(c for c in ch if c["id"] == "x::2.13.1")["herencia"]
           if t["tipo"] == "encabezado" and t["unidad_origen"] == "2.13"]
    check("B (B1): el título de dos renglones va entero en la entrada de encabezado y la intro empieza en «Bajo la "
          "supervisión»",
          enc == ["2.13. Promoción de servicios en dispositivos móviles e identificación de clientes con Documento\n"
                  "Nacional de Identidad digital en formato credencial virtual."]
          and (_texto(ch, "x::2.13::intro") or "").startswith("Bajo la supervisión"), str(enc))
    h14 = lambda cs: [t for t in next(c for c in cs if c["id"] == "x::2.14.1")["herencia"] if t["unidad_origen"] == "2.14"]
    check("B, caso negativo: la entrada que sale entera cuando el título entra en un renglón no cambia",
          h14(ch) == h14(ch0))
    # C
    def lista_c(x):
        return [_linea("Sección 1. Requisitos.", 1, 30.0), _linea("1.1. Condiciones generales.", 1, 50.0, x0=76.0),
                _linea("1.1.1. Primer requisito.", 1, 70.0, x0=110.0), _linea(cuerpo, 1, 84.0, x0=150.0),
                _linea("1.1.2. Segundo requisito.", 1, 110.0, x0=110.0), _linea(cuerpo, 1, 124.0, x0=150.0),
                _linea(cierre, 1, 150.0, x0=x)]
    res_c = {}
    for x in (110.0, 76.0, 150.0, 175.0):
        res, _ = _parse([lista_c(x)])
        E0.asignar_por_columna_c(res)
        res_c[x] = E0.construir_chunks(res)
    check("C: el párrafo sangrado hacia afuera pasa al nivel de la columna más cercana (110 → cierre de 1.1; 76 → cierre "
          "de la sección)",
          _texto(res_c[110.0], "x::1.1::cierre") == cierre and _texto(res_c[76.0], "x::S1::cierre") == cierre)
    check("C, casos negativos: el párrafo en la columna del texto del ítem, o más adentro, es del ítem",
          (_texto(res_c[150.0], "x::1.1.2") or "").endswith(cierre) and (_texto(res_c[175.0], "x::1.1.2") or "").endswith(cierre))
    # D
    pdl = [_linea("APARTADO C: DENUNCIAS POR INCUMPLIMIENTOS", 1, 50.0, x0=76.0), _linea("C.1. Información.", 1, 70.0, x0=76.0),
           _linea(cuerpo, 1, 84.0, x0=100.0), _linea("C.2. Otros datos.", 1, 110.0, x0=76.0)]
    r, _ = _parse([pdl], modo_sin_raiz=True, marcador_letra=True)
    hd = lambda **kw: [t["texto"] for t in next(c for c in E0.construir_chunks(r, **kw) if c["id"] == "x::C.1")["herencia"]
                       if t["tipo"] == "encabezado"][0]
    check("D: el rótulo heredado es el impreso («APARTADO C: …»), no el normalizado («C. …»)",
          hd(rotulo_impreso_d=True) == "APARTADO C: DENUNCIAS POR INCUMPLIMIENTOS"
          and hd() == "C. DENUNCIAS POR INCUMPLIMIENTOS")
    # E
    pe = [_linea("1. Uno.", 1, 50.0, x0=76.0), _linea(cuerpo, 1, 64.0, x0=90.0), _linea("2. Dos.", 1, 90.0, x0=76.0),
          _linea(cuerpo, 1, 104.0, x0=90.0), _linea("3. Tres.", 1, 130.0, x0=95.0), _linea(cuerpo, 1, 144.0, x0=110.0),
          _linea("5. Cinco.", 1, 170.0, x0=95.0), _linea(cuerpo, 1, 184.0, x0=110.0),
          _linea("4. Cuatro 10 20", 1, 200.0, x0=95.0, ngaps=1)]
    r0, _ = _parse([pe], modo_sin_raiz=True)
    r1, _ = _parse([pe], modo_sin_raiz=True, raiz_sucesora_e=True)
    check("E: la raíz rechazada por la columna que continúa la numeración abre (3); la que no sucede (5) y la fila con "
          "huecos (4) no",
          [s.numero for s in r0.secciones] == ["1", "2"] and [s.numero for s in r1.secciones] == ["1", "2", "3"],
          str([s.numero for s in r1.secciones]))
    # F1
    enc1 = ["Tasas en %", "Grupo A", "Concepto"]
    p1 = [_linea("Sección 1. Exigencia.", 1, 30.0)] + [_linea(t, 1, 50.0 + 10 * i, x0=400.0) for i, t in enumerate(enc1)] \
        + [_linea("1.1. Depósitos. 45 20", 1, 100.0, x0=76.0, ngaps=2)]
    p2 = [_linea("Sección 1. Exigencia.", 2, 30.0)] \
        + [_linea(t, 2, 50.0 + 10 * i, x0=400.0) for i, t in enumerate(["Grupo A", "Tasas en %", "Concepto"])] \
        + [_linea("1.2. Inversiones. 30 10", 2, 100.0, x0=76.0, ngaps=2)]
    r0, _ = _parse([p1, p2])
    r1, ch1 = _parse([p1, p2], encabezado_tabla_f=True)
    check("F1: el encabezado de columnas que se repite al tope de la página siguiente sale del texto; la primera "
          "aparición queda",
          r0.lineas_contenido - r1.lineas_contenido == 3
          and [a["pagina"] for a in r1.avisos if a["tipo"] == "encabezado_de_tabla_repetido_f"] == [2]
          and "Tasas en %" in "\n".join(c["texto"] for c in ch1))
    # G
    pg = [_linea("Sección 6. Gestión.", 1, 30.0), _linea("6.1. Directorio.", 1, 50.0, x0=76.0),
          _linea("6.1.1. Aprobar el plan.", 1, 70.0, x0=100.0),
          _linea("6 1 2. Supervisar regularmente la eficacia.", 1, 90.0, x0=100.0), _linea(". .", 1, 93.0, x0=105.0)]
    _, chg = _parse([pg], numero_partido_g=True)
    _, chg0 = _parse([pg[:-1]], numero_partido_g=True)
    check("G: los dígitos sueltos y sus puntos se unen en el número («6.1.2.») y abren el punto; sin el renglón de los "
          "puntos, no",
          _texto(chg, "x::6.1.2") == "6.1.2. Supervisar regularmente la eficacia." and "x::6.1.2" not in
          {c["id"] for c in chg0})
    # H
    ph = [_linea("Sección 1. Efectivo.", 1, 30.0), _linea("1.2. Exigencia.", 1, 50.0, x0=76.0),
          _linea("1.2.1. Los importes.", 1, 70.0, x0=100.0), _linea("1.2.2. En el caso.", 1, 90.0, x0=100.0),
          _linea("1.2.3.Conceptos comprendidos", 1, 110.0, x0=100.0), _linea(cuerpo, 1, 124.0, x0=120.0),
          _linea("1.2.5.Otros conceptos", 1, 150.0, x0=100.0)]
    _, chh = _parse([ph], numero_pegado_h=True)
    check("H: el rótulo pegado al título que continúa la numeración abre su punto (1.2.3); el que no la continúa (1.2.5), "
          "no",
          "x::1.2.3" in {c["id"] for c in chh} and "x::1.2.5" not in {c["id"] for c in chh}
          and (_texto(chh, "x::1.2.3") or "").startswith("1.2.3.Conceptos comprendidos"))
    # I
    box = [_linea("BANCO CENTRAL DE LA REPÚBLICA ARGENTINA", 1, 72.9, x0=95.8),
           _lp([(122.1, "SUPERINTENDENCIA DE ENTIDADES"), (330.0, "DECLARACIÓN JURADA DEL SOCIO")], 1, 83.2),
           _lp([(139.0, "FINANCIERAS Y CAMBIARIAS"), (360.0, "RESPONSABLE")], 1, 93.5),
           _linea("Gerencia de Control de Auditores", 1, 104.0, x0=135.2),
           _linea("Declaro bajo juramento que:", 1, 127.7, x0=119.2)]
    cont, rec, tit, evi = E0.leer_recuadro_por_columna_i(box, box)
    check("I: el recuadro de dos columnas se lee por columna (izquierda, después derecha), y el rótulo del formulario es "
          "la columna derecha: el membrete institucional nunca es madre",
          tit == "DECLARACIÓN JURADA DEL SOCIO RESPONSABLE"
          and [l.texto for l in cont][:6] == ["BANCO CENTRAL DE LA REPÚBLICA ARGENTINA", "SUPERINTENDENCIA DE ENTIDADES",
                                              "FINANCIERAS Y CAMBIARIAS", "Gerencia de Control de Auditores",
                                              "DECLARACIÓN JURADA DEL SOCIO", "RESPONSABLE"]
          and cont[-1].texto == "Declaro bajo juramento que:", str([l.texto for l in cont]))
    sin = [_linea("BANCO CENTRAL DE LA REPÚBLICA ARGENTINA", 1, 72.9, x0=95.8), _linea(cuerpo, 1, 100.0, x0=76.0)]
    check("I, caso negativo: sin recuadro de dos columnas el contenido no cambia",
          E0.leer_recuadro_por_columna_i(sin, sin)[3] is None)
    # J
    car = [_linea("CENTRALES DE INFORMACIÓN", 1, 370.6, x0=169.6),
           _linea("-Última comunicación incorporada: “A” 8393-", 1, 450.7, x0=170.5),
           _linea("Texto ordenado al", 1, 557.8, x0=182.8), _linea("28/01/2026", 1, 561.1, x0=360.6)]
    p2j = [_linea("CENTRALES DE INFORMACIÓN", 2, 70.0, x0=170.0), _linea("1. Primero.", 2, 100.0, x0=76.0),
           _linea(cuerpo, 2, 114.0, x0=90.0)]
    roles = [E0.ROL_CUERPO] * 2
    rep = {"CENTRALESDEINFORMACIÓN"}
    sj0 = E0.construir_chunks(E0.parsear_cuerpo("x", "x.pdf", [car, p2j], roles, modo_sin_raiz=True,
                                                mayusculas_repetidas=rep, pie_desde_version=True))
    sj = E0.construir_chunks(E0.parsear_cuerpo("x", "x.pdf", [car, p2j], roles, modo_sin_raiz=True,
                                               mayusculas_repetidas=rep, pie_desde_version=True, caratula_j=True))
    check("J: la carátula conserva el título y la fecha y el preámbulo no lleva «Preámbulo»; sin J, los pierde",
          _texto(sj, "x::S0") == "CENTRALES DE INFORMACIÓN\n-Última comunicación incorporada: “A” 8393-\n"
                                 "Texto ordenado al\n28/01/2026"
          and (_texto(sj0, "x::S0") or "").startswith("Preámbulo") and "28/01/2026" not in (_texto(sj0, "x::S0") or ""),
          repr(_texto(sj, "x::S0")))
    # K
    pk = [_linea("Sección 1. Declaración.", 1, 30.0), _linea(cuerpo, 1, 50.0), _linea("Fórm. 4421 C (II-2006)", 1, 700.0)]
    _, chk0 = _parse([pk])
    _, chk = _parse([pk], pie_formulario_k=True)
    pk2 = [_linea("Sección 1. Declaración.", 1, 30.0), _linea("Fórm. 4421 C (II-2006)", 1, 50.0), _linea(cuerpo, 1, 70.0)]
    _, chk2 = _parse([pk2], pie_formulario_k=True)
    check("K: el código de formulario al pie de la página es pie; el que no es el último renglón queda",
          "Fórm. 4421" in (_texto(chk0, "x::S1") or "") and "Fórm. 4421" not in (_texto(chk, "x::S1") or "")
          and "Fórm. 4421" in (_texto(chk2, "x::S1") or ""))


def test_s06bis_sinteticos() -> None:
    E0 = correr_e0.E0
    print("== y′) S0-6a-bis de U-SEG-OFICIAL: casos sintéticos (C, A y L ajustadas o nuevas)")
    cuerpo = "Texto de la norma que corre en la columna del cuerpo del ítem y termina en punto final."
    cierre = "Las entidades deberán observar lo dispuesto en los puntos anteriores durante todo el plazo."

    def lista(cola):
        return [_linea("Sección 1. Requisitos.", 1, 30.0), _linea("1.1. Condiciones generales.", 1, 50.0, x0=76.0),
                _linea("1.1.1. Primer requisito.", 1, 70.0, x0=110.0), _linea(cuerpo, 1, 84.0, x0=150.0),
                _linea("1.1.2. Segundo requisito.", 1, 110.0, x0=110.0), _linea(cuerpo, 1, 124.0, x0=150.0)] + cola

    def correr(cola, excluir=None):
        res, _ = _parse([lista(cola)])
        ev = E0.asignar_por_columna_c(res, excluir=excluir)
        return E0.construir_chunks(res), ev
    ch, ev = correr([_linea(cierre, 1, 150.0, x0=76.0)])
    check("C, control: el cierre en la columna de la sección, solo, sale (a la Sección 1)", _texto(ch, "x::S1::cierre") == cierre)
    ch, ev = correr([_linea(cierre, 1, 150.0, x0=76.0), _linea("Datos del formulario:", 1, 170.0, x0=76.0),
                     _linea("nombre y apellido del titular", 1, 184.0, x0=200.0),
                     _linea("domicilio del titular de la cuenta", 1, 198.0, x0=90.0)])
    check("C (D21, regla 3): si un párrafo del grupo que saldría no comparte columna, no sale ninguno",
          _texto(ch, "x::S1::cierre") is None and any(e["tipo"] == "grupo_sin_columna_comun_c" for e in ev)
          and (_texto(ch, "x::1.1.2") or "").endswith("domicilio del titular de la cuenta"))
    ch, ev = correr([_linea("Nota: el plazo se cuenta desde la", 1, 150.0, x0=76.0),
                     _linea("fecha de la solicitud y vence a los treinta días.", 1, 164.0, x0=150.0)])
    check("C: el párrafo se mide por la columna que comparten sus renglones (el segundo, 150), no por el más a la "
          "izquierda (76): queda en el ítem",
          (_texto(ch, "x::1.1.2") or "").endswith("vence a los treinta días.") and _texto(ch, "x::S1::cierre") is None)
    fila = _linea("Código Concepto Importe", 1, 170.0, x0=76.0, ngaps=2)
    ch, ev = correr([_linea(cierre, 1, 150.0, x0=76.0), fila], excluir=lambda l: l is fila)
    check("C: el párrafo al que sigue una tabla de su texto no sale (la tabla es parte del bloque)",
          _texto(ch, "x::S1::cierre") is None and any(e["tipo"] == "grupo_sin_columna_comun_c" for e in ev))
    # A: carátula
    car = [_linea("REGIMEN INFORMATIVO CONTABLE MENSUAL", 1, 360.0, x0=90.0),
           _linea("INFORMACION INSTITUCIONAL DE ENTIDADES", 1, 425.0, x0=102.0),
           _linea("FINANCIERAS Y CAMBIARIAS", 1, 444.0, x0=184.0), _linea("Vigente a partir del 31/12/19", 1, 508.0, x0=201.0)]
    p2 = [_linea("Las entidades deberán remitir a esta Institución la información.", 2, 147.0, x0=76.0),
          _linea("1. Datos de la entidad.", 2, 170.0, x0=76.0), _linea(cuerpo, 2, 184.0, x0=90.0),
          _linea("2. Datos de los directivos.", 2, 210.0, x0=76.0), _linea(cuerpo, 2, 224.0, x0=90.0)]
    r, _ = _parse([car, p2], modo_sin_raiz=True)
    ev = E0.dividir_a(r, sin_raiz=True)
    larga = car + [_linea(cuerpo, 1, 520.0 + 12 * k, x0=76.0) for k in range(5)]
    r2, _ = _parse([larga, p2], modo_sin_raiz=True)
    check("A: la página 1 leída como cuerpo con a lo sumo 8 renglones es carátula y no abre divisiones; con más, no es "
          "carátula", r.paginas_caratula_a == {1} and not any(e.get("pagina") == 1 for e in ev)
          and r2.paginas_caratula_a == set())
    # L: índice con un título partido en dos renglones
    idx = [_linea("INFORMES", 1, 60.0, x0=290.0), _linea("1. Informe anual sobre los estados financieros.", 1, 80.0, x0=90.0),
           _linea("2. Informe de revisión de estados financieros de períodos intermedios con los", 1, 100.0, x0=90.0),
           _linea("las revisiones limitadas de los estados financieros de la entidad al cierre de cada", 1, 112.0, x0=108.0),
           _linea("3. Memorando sobre el sistema de control interno.", 1, 132.0, x0=90.0)]
    cpo = []
    for k, t in enumerate(["1. Informe anual sobre los estados financieros.",
                           "2. Informe de revisión de estados financieros de períodos intermedios con los",
                           "3. Memorando sobre el sistema de control interno."]):
        cpo.append(_linea(t, 2, 60.0 + 100 * k, x0=90.0))
        cpo += [_linea(cuerpo, 2, 74.0 + 100 * k + 14 * j, x0=110.0) for j in range(4)]
    roles = [E0.ROL_CUERPO] * 2
    il = E0.lineas_de_indice_l([idx, cpo], roles)
    sin_idx = E0.lineas_de_indice_l([idx[:3] + [_linea("3. Otro título que no reaparece.", 1, 132.0, x0=90.0)], cpo[:5]],
                                    roles)
    r0, _ = _parse([idx, cpo], modo_sin_raiz=True)
    r1, _ = _parse([idx, cpo], modo_sin_raiz=True, indice_l=il)
    check("L: el índice (sus títulos reaparecen después) no abre raíces y el cuerpo que vuelve a empezar en 1 sí; una "
          "lista cuyos títulos no reaparecen no es índice",
          il == {(1, 80.0), (1, 100.0), (1, 132.0)} and sin_idx == frozenset()
          and [s.pagina for s in r1.secciones if s.numero in ("1", "2", "3")] == [2, 2, 2]
          and [s.pagina for s in r0.secciones if s.numero in ("1", "2", "3")] == [1, 1, 1]
          and sum(1 for x in r1.rechazos_header if x["motivo"] == "indice_l") == 3, str(il))


TOS_S06 = ("nmaeef", "ri_dcpc", "ceninf", "seguef", "snp_cheq", "ri2_ae", "ri_cc", "ri_ccna", "ri_oc", "manori",
           "snp_psp", "ctavis", "cedin", "cryl", "ribspc", "garant", "snp_spd", "efemin", "ri_psprca", "ri_spi",
           "seggar", "gerc", "lingeef",
           # negativos del §4 (sus leídas motivaron ajustes de C y de A: DISENO_S0-6a.md, §3)
           "fimipyme", "cajasc", "ri_rml", "ri_msrl", "dmrd", "gracre",
           # S0-6a-bis: los de los grupos que empeoraban en S0-6a (G5, G10, G11) y los de las listas que quedan en R5-a
           "ri_ii_31_12_19", "depaho", "apnf", "ayccef", "snp_dd", "snp_tr", "expaef", "tasint", "snp_mep")
# Negativos del §4 de S0-6a (s0_6/scripts/negativos_leidas_S0-6a.py), regenerados en S0-6a-bis con los TOs agregados a
# TOS_S06 (s0_6/bis/scripts/negativos_al_selftest_S0-6a-bis.py): las unidades leídas en S1-ter de los TOs de TOS_S06, de
# corte (y herencia, si se juzgó y no cambia) correctos, que la E0 corregida conserva. Por id: su origen (ficha y
# pregunta de S1-ter), lo que se fija («corte»: sha256 propio y páginas; «corte y herencia»: además la herencia) y los 16
# primeros hex del sha256 de esos campos en la E0 que leyó S1-ter, iguales en la corregida.
NEGATIVOS_LEIDAS_S06: dict[str, tuple[str, str, str]] = {
    "apnf::1.3.1.2": ("E2-019 la_unidad, E2-019 la_herencia", "corte y herencia", "59fc301b0570ce97"),
    "apnf::1.3.1::cierre": ("E2-019 la_que_sigue", "corte y herencia", "eca8ea35f35d9fd5"),
    "ayccef::2.3.2.2": ("E2-069 la_unidad, E2-069 la_herencia", "corte y herencia", "00738fee343fd4d9"),
    "ayccef::2.3.3": ("E2-069 la_que_sigue", "corte y herencia", "479dc6829e3d3279"),
    "ayccef::2.9.4.2": ("E2-070 la_unidad, E2-070 la_herencia", "corte y herencia", "a85e7a7f6fa6e201"),
    "ayccef::2.9.5": ("E2-070 la_que_sigue", "corte y herencia", "4cb3fd6530a5c87b"),
    "ayccef::3.6.2.2": ("E2-071 la_unidad, E2-071 la_herencia", "corte y herencia", "6f21c563a8f5e815"),
    "ayccef::3.6.3": ("E2-071 la_que_sigue", "corte y herencia", "52a9c29f1c6d335e"),
    "ayccef::4.4.5": ("E2-072 la_unidad, E2-072 la_herencia", "corte y herencia", "98c4702363f408be"),
    "ayccef::4.5": ("E2-072 la_que_sigue", "corte y herencia", "14f0e8024512460d"),
    "ayccef::5.2.5.2": ("E2-073 la_unidad, E2-073 la_herencia", "corte y herencia", "5bff5481c0f12a38"),
    "ayccef::5.3.1": ("E2-073 la_que_sigue", "corte y herencia", "a06fcd60f8b9d8fe"),
    "cajasc::11.1.2": ("E2-074 la_unidad, E2-074 la_herencia", "corte y herencia", "e9aab9ba19451ee1"),
    "cajasc::11.2": ("E2-074 la_que_sigue", "corte y herencia", "433b69efea50defb"),
    "cajasc::11.4.4": ("E2-075 la_unidad, E2-075 la_herencia", "corte y herencia", "1eb511789254819d"),
    "cajasc::11.4::cierre": ("E2-075 la_que_sigue", "corte y herencia", "a01b594fc12e3d7b"),
    "cajasc::4.2.2.3": ("E2-076 la_unidad, E2-076 la_herencia", "corte y herencia", "cc0672ade7d5432f"),
    "cajasc::4.2.2::cierre": ("E2-076 la_que_sigue", "corte y herencia", "afab42aca1315c34"),
    "cajasc::6.2.1.3": ("E2-077 la_unidad, E2-077 la_herencia", "corte y herencia", "664696892c6978a4"),
    "cajasc::6.2.2": ("E2-077 la_que_sigue", "corte y herencia", "5ce16c85558e7e47"),
    "cedin::11.2": ("E2-042 la_unidad, E2-042 la_herencia", "corte y herencia", "6513ff46062bf057"),
    "cedin::13.2::cierre": ("E1-050 la_unidad", "corte", "e6e5f1a121dc1e90"),
    "cedin::2.1.4": ("E1-001 la_unidad", "corte y herencia", "023a4f7d659f8789"),
    "cedin::7.1.3::cierre": ("E2-028 la_que_sigue", "corte", "dd0405a0ee8cccd8"),
    "cedin::S12::chapeau_seccion": ("E1-002 la_unidad, E2-042 la_que_sigue", "corte y herencia", "64d5f58679ed07f7"),
    "ceninf::S4::chapeau_seccion": ("E1-075 la_unidad", "corte y herencia", "08c440f8551e13bb"),
    "cryl::4.2.2": ("E2-033 la_unidad, E2-033 la_herencia", "corte", "d273d781bd720172"),
    "ctavis::4.1.2::cierre": ("E2-016 la_que_sigue", "corte", "945b9e30dc320fe8"),
    "ctavis::5.3.7": ("E2-040 la_que_sigue", "corte y herencia", "bd2a46d60f4aff88"),
    "ctavis::7.7": ("E1-082 la_unidad", "corte y herencia", "bd5576ff589ec640"),
    "ctavis::8.1.3": ("E1-043 la_unidad", "corte y herencia", "415ad5feaba37a68"),
    "ctavis::8.2.1.4": ("E2-036 la_unidad, E2-036 la_herencia", "corte y herencia", "96910c570561f378"),
    "ctavis::8.2.1::cierre": ("E2-036 la_que_sigue", "corte y herencia", "d2763246bcdfa87b"),
    "depaho::1.12.2": ("E2-079 la_unidad, E2-079 la_herencia", "corte y herencia", "e9d08a5afbbb58f9"),
    "depaho::1.12::cierre": ("E2-079 la_que_sigue", "corte y herencia", "0774a4b235451602"),
    "depaho::1.5.5": ("E2-080 la_unidad, E2-080 la_herencia", "corte y herencia", "5f2f9a60352203b6"),
    "depaho::1.6.1::intro": ("E2-080 la_que_sigue", "corte y herencia", "6cb763b03009f04e"),
    "depaho::1.7.5": ("E1-061 la_unidad", "corte y herencia", "cc952d5ebc08a4a5"),
    "depaho::3.1.6.4": ("E2-081 la_unidad, E2-081 la_herencia", "corte y herencia", "cde2a51fd2663c9a"),
    "depaho::3.1.7.1": ("E2-081 la_que_sigue", "corte y herencia", "44934258a415ab69"),
    "depaho::3.11.5.5": ("E2-082 la_unidad, E2-082 la_herencia", "corte y herencia", "3a48dd66f0b5fca2"),
    "depaho::3.11.5::cierre": ("E2-082 la_que_sigue", "corte y herencia", "dbc1b110a346e5b9"),
    "depaho::3.4.10.2": ("E2-083 la_unidad, E2-083 la_herencia", "corte y herencia", "38822da995e4596b"),
    "depaho::3.4.10::cierre": ("E2-083 la_que_sigue", "corte y herencia", "ed5bcacea800c9ea"),
    "depaho::3.4.4.5": ("E2-084 la_unidad, E2-084 la_herencia", "corte y herencia", "c21904521b56bcc4"),
    "depaho::3.4.5.1": ("E2-084 la_que_sigue", "corte y herencia", "879ff88696878bdf"),
    "depaho::3.6.2.4": ("E1-083 la_unidad, E2-085 la_unidad, E2-085 la_herencia", "corte y herencia", "c8bb10ed476ec201"),
    "depaho::3.6.3": ("E2-085 la_que_sigue", "corte y herencia", "e2413e045e041f6d"),
    "depaho::3.8.6.4": ("E2-086 la_unidad, E2-086 la_herencia", "corte y herencia", "793b20e5dbfc1b0f"),
    "depaho::3.8.7": ("E2-086 la_que_sigue", "corte y herencia", "94f4365ff17d1657"),
    "dmrd::S14": ("E1-007 la_unidad", "corte y herencia", "89cd209763efb098"),
    "efemin::1.3.8": ("E2-046 la_que_sigue", "corte", "a35f2ec92a7fe40a"),
    "efemin::2.3.2": ("E2-015 la_unidad, E2-015 la_herencia", "corte y herencia", "dd8a7c820a8d3346"),
    "efemin::2.3::cierre": ("E2-015 la_que_sigue", "corte y herencia", "282586c1d22421d0"),
    "efemin::3.1.4": ("E1-020 la_unidad", "corte y herencia", "58df1750a28758b0"),
    "efemin::3.2.2": ("E2-087 la_unidad, E2-087 la_herencia", "corte y herencia", "a4e13cb9defddc08"),
    "efemin::3.2::cierre": ("E2-087 la_que_sigue", "corte y herencia", "6ad8611f4d3ad4d0"),
    "expaef::1.9": ("E1-035 la_unidad", "corte y herencia", "4ba65e9f3215a6c7"),
    "fimipyme::4.3.3": ("E2-024 la_unidad, E2-024 la_herencia", "corte y herencia", "fdb0103581f62add"),
    "fimipyme::4.3::cierre": ("E2-024 la_que_sigue", "corte y herencia", "20b55fc1e1c2230f"),
    "fimipyme::5.1.2": ("E2-004 la_unidad, E2-004 la_herencia", "corte y herencia", "fd318a5a54b643ce"),
    "fimipyme::5.1::cierre": ("E2-004 la_que_sigue", "corte y herencia", "b34defb58bc33742"),
    "garant::1.2.8.2": ("E2-052 la_unidad, E2-052 la_herencia", "corte y herencia", "f61d9d13b1e732f6"),
    "garant::1.2.8::cierre": ("E2-052 la_que_sigue", "corte y herencia", "5a557c9000683865"),
    "garant::1.2.9::cierre": ("E2-043 la_que_sigue", "corte", "2c8bd63b79c1c534"),
    "gerc::6.2": ("E2-027 la_unidad, E2-027 la_herencia", "corte y herencia", "f5ff9b80d3bc7dba"),
    "gracre::6.5.2": ("E2-054 la_unidad, E2-054 la_herencia", "corte y herencia", "79d0ed00c6504e2f"),
    "gracre::6.6": ("E2-054 la_que_sigue", "corte y herencia", "0e750d1a614b860c"),
    "gracre::6.7.2": ("E2-021 la_unidad, E2-021 la_herencia", "corte y herencia", "cd47cf5a1b6147d1"),
    "gracre::6.7::cierre": ("E2-021 la_que_sigue", "corte y herencia", "97e5aea6229bbadd"),
    "lingeef::10.3.2": ("E2-088 la_unidad, E2-088 la_herencia", "corte y herencia", "c4de1eea00969e4b"),
    "lingeef::10.4::intro": ("E2-088 la_que_sigue", "corte y herencia", "777ac6f969d625b9"),
    "lingeef::12.8.2": ("E2-089 la_unidad, E2-089 la_herencia", "corte y herencia", "46807b483635d6e1"),
    "lingeef::3.3.1.8": ("E2-090 la_unidad, E2-090 la_herencia", "corte y herencia", "ddcaaf0480340e20"),
    "lingeef::3.3.2::intro": ("E2-090 la_que_sigue", "corte y herencia", "bb3ed4bb3db91ab8"),
    "lingeef::3.3.8": ("E1-031 la_unidad", "corte y herencia", "e10761a045d2e5dd"),
    "lingeef::4.3.3.6": ("E2-020 la_unidad, E2-020 la_herencia", "corte y herencia", "8ea0ffb85f3799cb"),
    "lingeef::4.3.4::intro": ("E2-020 la_que_sigue", "corte y herencia", "8e3fd04c53ea5c96"),
    "lingeef::5.1.1.3": ("E2-091 la_unidad, E2-091 la_herencia", "corte y herencia", "1cf4320e12533af2"),
    "lingeef::5.1.1::cierre": ("E2-091 la_que_sigue", "corte y herencia", "fe89cbecb02b9f5f"),
    "lingeef::5.3.4.5": ("E2-092 la_unidad, E2-092 la_herencia", "corte y herencia", "e32b98a0e9e97765"),
    "lingeef::5.3.4::cierre": ("E2-092 la_que_sigue", "corte y herencia", "d87c06c4576f062b"),
    "lingeef::5.4.2.3": ("E2-023 la_unidad, E2-023 la_herencia", "corte y herencia", "6da59c792019150a"),
    "lingeef::5.4.3.3": ("E2-093 la_unidad, E2-093 la_herencia", "corte y herencia", "4639094a2a036098"),
    "lingeef::5.4.3::intro": ("E2-023 la_que_sigue", "corte y herencia", "f32beb653b96a4f3"),
    "lingeef::5.4.4::intro": ("E2-093 la_que_sigue", "corte y herencia", "e78710ce9624aa53"),
    "lingeef::7.3.2.2": ("E2-095 la_unidad, E2-095 la_herencia", "corte y herencia", "fa97162895c38302"),
    "lingeef::7.3.3::intro": ("E2-095 la_que_sigue", "corte y herencia", "b4a35d7dc94f3dbb"),
    "manori::1.1.4.1": ("E1-027 la_unidad", "corte", "3b67aa482ec6a0eb"),
    "manori::1.1.6::cierre": ("E2-008 la_que_sigue", "corte y herencia", "51a4360b7da8533d"),
    "manori::1.4.1::cierre": ("E2-096 la_que_sigue", "corte y herencia", "8ce5dbf768f138ce"),
    "manori::3.4.1::cierre": ("E2-097 la_que_sigue", "corte y herencia", "f9c0b10256e653a1"),
    "ri_cc::R4::1.3": ("E2-005 la_que_sigue", "corte y herencia", "24e20420b491eb0e"),
    "ri_ccna::D1A3L2::26.4": ("E1-019 la_unidad", "corte y herencia", "c058432e26c788b4"),
    "ri_ccna::D1A3L2::S34": ("E1-018 la_unidad", "corte y herencia", "2f0cc9ca7818e6a7"),
    "ri_ccna::D1A3L2::S4": ("E1-089 la_unidad", "corte y herencia", "0f5304e624639ad4"),
    "ri_ccna::D1A3L2::S40": ("E1-065 la_unidad", "corte y herencia", "d2c332b3d8cc270b"),
    "ri_ccna::D2A2::S3::chapeau_seccion": ("E2-057 la_que_sigue", "corte y herencia", "12fe0492f1223a09"),
    "ri_ccna::D2A3::S0": ("E1-006 la_unidad", "corte y herencia", "778c6ad53e242475"),
    "ri_dcpc::2.4": ("E1-034 la_unidad", "corte y herencia", "d6ef1ee351769d4c"),
    "ri_dcpc::3.7.1": ("E1-057 la_unidad", "corte y herencia", "d6b3191f82baab29"),
    "ri_ii_31_12_19::2.5": ("E1-067 la_unidad", "corte y herencia", "9e84763fe980e636"),
    "ri_ii_31_12_19::6.3": ("E1-052 la_unidad", "corte", "bc55567e47c4ae84"),
    "ri_msrl::7.2": ("E1-078 la_unidad", "corte y herencia", "71505a7c88f4e95c"),
    "ri_oc::1.2.4": ("E1-056 la_unidad", "corte", "11f17a53dc9e00c2"),
    "ri_oc::1.4.3": ("E1-044 la_unidad", "corte", "d8bc8949eb8822e6"),
    "ri_oc::3.1": ("E2-007 la_que_sigue", "corte", "ad615523b7cb6c8f"),
    "ri_oc::3.16": ("E1-014 la_unidad", "corte", "5565ee0ee9a98dab"),
    "ri_oc::3.38": ("E1-011 la_unidad", "corte", "3cf1af5c61f48cc4"),
    "ri_oc::3.45": ("E2-044 la_unidad, E2-044 la_herencia", "corte", "99d4067397255045"),
    "ri_oc::3.46": ("E2-044 la_que_sigue", "corte", "ebe59b98e83b28c6"),
    "ri_oc::B.1.5": ("E1-015 la_unidad", "corte", "2d152d6da34df92c"),
    "ri_oc::B.1::cierre": ("E2-098 la_que_sigue", "corte", "d4a374695787ff63"),
    "ri_psprca::4.1": ("E1-005 la_unidad", "corte", "facccab4e27ec3d8"),
    "ri_rml::1.2.3": ("E2-100 la_unidad, E2-100 la_herencia", "corte y herencia", "352adc75e5080399"),
    "ri_rml::1.2.4": ("E2-100 la_que_sigue", "corte y herencia", "7f7a7e081df1081f"),
    "ri_rml::1.4.2": ("E2-062 la_unidad, E2-062 la_herencia", "corte y herencia", "5555f612378b02ef"),
    "ri_rml::1.4::cierre": ("E2-062 la_que_sigue", "corte y herencia", "b7bc643d08334459"),
    "ri_spi::A.1.4": ("E1-069 la_unidad", "corte", "1ee96c2458487e81"),
    "ri_spi::A.1.6": ("E1-026 la_unidad", "corte", "6f32dc9600033bc8"),
    "ri_spi::B.2.9": ("E1-030 la_unidad", "corte", "f62ae29b4c9b3955"),
    "ri_spi::B.3.6": ("E1-085 la_unidad", "corte", "fa8207664c39ab1d"),
    "ri_spi::B.5.15": ("E1-066 la_unidad", "corte", "6f036b1f83440284"),
    "ri_spi::B.5.16": ("E1-062 la_unidad", "corte", "6db38525e3dfeb51"),
    "ri_spi::C.1::cierre": ("E2-058 la_que_sigue", "corte", "6ef455c87c30ac92"),
    "seggar::5.2.4": ("E1-088 la_unidad", "corte", "6bbbfb0de528498e"),
    "seggar::S3::chapeau_seccion": ("E1-012 la_unidad", "corte y herencia", "820c858841de977c"),
    "seggar::S7::chapeau_seccion": ("E2-065 la_que_sigue", "corte y herencia", "e85b29ae1f6e8fc4"),
    "seguef::2.1.6::cierre": ("E2-034 la_que_sigue", "corte", "e3589e353e03c3e6"),
    "seguef::2.15": ("E1-077 la_unidad", "corte y herencia", "056074f99933be10"),
    "seguef::2.3.1.2": ("E1-086 la_unidad", "corte y herencia", "5a891dec00f0096d"),
    "seguef::2.9.2": ("E2-059 la_unidad, E2-059 la_herencia", "corte y herencia", "0fbe3bcb18cb09ce"),
    "seguef::2.9::cierre": ("E2-059 la_que_sigue", "corte y herencia", "3a32edd4a7071537"),
    "seguef::3.7": ("E1-084 la_unidad", "corte y herencia", "b44ac03c2bf95356"),
    "seguef::6.3.2": ("E1-060 la_unidad", "corte y herencia", "8dd08ba4c6a2bad6"),
    "seguef::6.3::intro": ("E1-025 la_unidad", "corte y herencia", "931d98bd311c40af"),
    "snp_cheq::8.1.3": ("E1-080 la_unidad", "corte y herencia", "4f35f5e112488b68"),
    "snp_cheq::8.8": ("E1-046 la_unidad", "corte y herencia", "4fcc2e1c36feeb76"),
    "snp_dd::2.2.2.1": ("E1-070 la_unidad", "corte y herencia", "621f9f311b4b6d49"),
    "snp_mep::3.1.1.2": ("E2-018 la_unidad, E2-018 la_herencia", "corte y herencia", "4d022f1a41907494"),
    "snp_mep::3.1.1::cierre": ("E2-018 la_que_sigue", "corte y herencia", "2303ca7ba3f353f3"),
    "snp_mep::3.1.2.2": ("E2-022 la_unidad, E2-022 la_herencia", "corte y herencia", "6dded9b8ca9c3cfe"),
    "snp_mep::3.1.2::cierre": ("E2-022 la_que_sigue", "corte y herencia", "7c352211f25005a2"),
    "snp_mep::3.2.3::intro": ("E1-032 la_unidad", "corte y herencia", "2d189ead602d387d"),
    "snp_mep::4.6.2": ("E2-053 la_unidad, E2-053 la_herencia", "corte y herencia", "f4aac510c683102d"),
    "snp_mep::4.6::cierre": ("E2-053 la_que_sigue", "corte y herencia", "b50317d444c30711"),
    "snp_psp::1.3.2::cierre": ("E2-011 la_que_sigue", "corte", "e9911188d972335b"),
    "snp_spd::1.1::intro": ("E1-076 la_unidad", "corte y herencia", "e2010a8dca494023"),
    "snp_tr::1.3.1.3": ("E1-039 la_unidad", "corte y herencia", "0156648f9eb0572a"),
    "snp_tr::1.6.2.1": ("E1-068 la_unidad", "corte y herencia", "748b01674738ab44"),
    "snp_tr::4.2": ("E2-101 la_unidad, E2-101 la_herencia", "corte y herencia", "30cf50a764153418"),
    "tasint::1.7": ("E1-073 la_unidad", "corte y herencia", "2a985e7b815367a5"),
    "tasint::3.3.2": ("E2-032 la_unidad, E2-032 la_herencia", "corte y herencia", "fde47c3355b9d2fd"),
    "tasint::3.3::cierre": ("E2-032 la_que_sigue", "corte y herencia", "814d952435db3962"),
}


def _sha16_campos(c: dict, campos: tuple) -> str:
    return _sha16(json.dumps([c[k] for k in campos], ensure_ascii=False, sort_keys=True))


def test_s06_casos(d: Path) -> None:
    print(f"== z) S0-6a de U-SEG-OFICIAL: un caso positivo por regla, de las 40 filas (e0-r2 sobre {len(TOS_S06)} TOs)")
    correr_e0.correr(d, manifiesto=_ManifiestoParticion(TOS_S06), version_e0="e0-r2")
    ch = {to: {c["id"]: c for c in cargar(d, f"chunks_{to}.json")} for to in TOS_S06}

    def u(uid: str) -> dict:
        return ch[uid.split("::")[0]].get(uid) or {}

    def txt(uid: str) -> str:
        return u(uid).get("texto", "")

    def her(uid: str) -> list:
        return [(t["tipo"], t["unidad_origen"], t["texto"]) for t in u(uid).get("herencia", [])]

    def sigue(uid: str) -> str:
        ids = list(ch[uid.split("::")[0]])
        return ids[ids.index(uid) + 1] if uid in ids and ids.index(uid) + 1 < len(ids) else ""

    check("A (E1-010): ri_dcpc::3.7.6 termina en la p. 26; la tabla de correspondencia es una división de la Sección 3",
          u("ri_dcpc::3.7.6").get("paginas") == [26]
          and any(c["texto"].startswith("TABLA DE CORRESPONDENCIA PARA REEXPRESION DE PARTIDAS") and
                  c["herencia"][0]["texto"].startswith("Sección 3.") for c in ch["ri_dcpc"].values()))
    check("A (E2-039): ribspc::S4 termina en la p. 1 y hereda «NORMAS DE PROCEDIMIENTO» e «Instrucciones generales»",
          u("ribspc::S4").get("paginas") == [1]
          and [t[2] for t in her("ribspc::S4")] == ["NORMAS DE PROCEDIMIENTO", "Instrucciones generales"])
    hs10 = her("ri_psprca::S10")
    check("A (E2-056): ri_psprca::S10 es un renglón y hereda la banda «SECCION II – …», «Apartado A: …» y «Datos "
          "solicitados:»",
          txt("ri_psprca::S10") == "10. Moneda total en moneda de origen."
          and hs10[0][2] == "SECCION II – INSTRUCCIONES PARTICULARES" and hs10[1][2] == "Apartado A: ATMs en Argentina"
          and hs10[2][2].endswith("Datos solicitados:"), str(hs10))
    check("A y D (E2-007): ri_oc::S2 hereda «APARTADO A: OPERACIONES DE CAMBIOS»",
          her("ri_oc::S2")[0][2] == "APARTADO A: OPERACIONES DE CAMBIOS")
    check("A (E2-099): la unidad que sigue a ri_oc::C.11 es el bloque «Validación del Apartado A – …» y termina antes de "
          "«Validación del Apartado B»",
          txt(sigue("ri_oc::C.11")).startswith("Validación del Apartado A – Operaciones de cambios")
          and "Validación del Apartado B" not in txt(sigue("ri_oc::C.11")))
    h57 = [t[2] for t in her("ri_ccna::D2A2::S2")]
    check("A (E2-057): ri_ccna::D2A2::S2 hereda «ANEXO II», el título del anexo y su introducción",
          len(h57) >= 3 and h57[0] == "ANEXO II" and h57[1].startswith("METODOLOGÍA PARA LA EVALUACIÓN DEL CONTROL")
          and h57[2].startswith("La evaluación de la estructura de control"), str([t[:40] for t in h57]))
    check("A (E2-002): ri2_ae 14.3 (en el sub-documento del Anexo III) son dos renglones y hereda «ANEXO III»",
          txt("ri2_ae::A3::14.3").count("\n") == 1 and her("ri2_ae::A3::14.3")[0][2] == "ANEXO III")
    check("B (E1-081): el título de 2.13 de seguef va entero en el encabezado y la intro empieza en «Bajo la supervisión»",
          txt("seguef::2.13::intro").startswith("Bajo la supervisión")
          and any(t[2].endswith("en formato credencial virtual.") for t in her("seguef::2.13.1") if t[0] == "encabezado"))
    check("B (E1-090): el título de 8.4.4 de snp_cheq, tres renglones, va entero en el encabezado; no queda intro",
          "snp_cheq::8.4.4::intro" not in ch["snp_cheq"]
          and any(t[2].count("\n") == 2 and t[1] == "8.4.4" for t in her("snp_cheq::8.4.4.1")))
    sin_num = {"snp_psp::1.3.2.2": "1.3.2", "ctavis::4.1.2.3": "4.1.2", "cedin::7.1.3.2": "7.1",
               "seguef::2.1.6.2": "2.1.6", "ctavis::5.3.6.3": "5.3.6", "garant::1.2.9.4": "1.2.9",
               "snp_spd::5.5.2.4": "5.5.2", "efemin::1.3.7.2": "1.3.7"}
    malos = [k for k, n in sin_num.items() if any(t[0] == "encabezado" and t[1] == n for t in her(k))
             or not any(t[0] == "intro" and t[1] == n and t[2].startswith(n + ".") for t in her(k))]
    check("B (E2-011, E2-016, E2-028, E2-034, E2-040, E2-043, E2-045, E2-046): sin encabezado fabricado; la intro "
          "lleva el texto entero con su número", not malos, str(malos))
    check("C (E2-033): la que sigue a cryl::4.2.2 es cryl::S4::cierre", sigue("cryl::4.2.2") == "cryl::S4::cierre")
    check("C (E2-045): la que sigue a snp_spd::5.5.3 es la intersticial del 5.5; 5.5.3 termina en su texto",
          sigue("snp_spd::5.5.3") == "snp_spd::5.5::intersticial" and "Las actividades" not in txt("snp_spd::5.5.3"))
    contaminadas = [k for k in ("manori::1.1.6.5", "manori::1.4.1.3", "manori::3.4.1.3")
                    if any(t[1] in ("S1", "S3") and t[0] in ("intersticial", "cierre") for t in her(k))]
    check("C (E2-008, E2-096, E2-097): manori 1.1.6.5, 1.4.1.3 y 3.4.1.3 no heredan intersticiales ni cierres de su "
          "sección (el cierre del 1.2 y del 3.2, y los formularios)", not contaminadas, str(contaminadas))
    check("C, A y K (E2-006): ri_ccna::D1F6::S8 termina en «…normas reglamentarias.», sin el cierre de la declaración, "
          "los rótulos de firma ni el código del formulario",
          txt("ri_ccna::D1F6::S8").endswith("Nº 21.526 y normas reglamentarias.")
          and "Asimismo" not in txt("ri_ccna::D1F6::S8") and "Fórm." not in txt("ri_ccna::D1F6::S8"))
    check("I y A (E2-006): ri_ccna::D1F6::S8 hereda el título del formulario y su introducción, no el membrete",
          [t[2] for t in her("ri_ccna::D1F6::S8")][:2]
          == ["DECLARACIÓN JURADA DEL SOCIO RESPONSABLE",
              "Declaro bajo juramento, como Socio Responsable por la labor del auditor externo de la Entidad que:"])
    check("D (E2-058, E2-098, E2-099): los apartados heredados con su texto impreso (el de ri_spi, con el renglón que le "
          "junta R5-c, que sigue como está)",
          her("ri_spi::C.1.3")[0][2] == "APARTADO C: DENUNCIAS POR INCUMPLIMIENTOS RELACIONADOS CON EL\nAPARTADO B"
          and her("ri_oc::B.1.28")[0][2].startswith("APARTADO B: POSICIÓN GENERAL DE CAMBIOS")
          and her("ri_oc::C.11")[0][2].startswith("APARTADO C: COMPOSICIÓN"))
    check("E (E2-065): seggar::5.3.5 termina en «…cobro indebido de la garantía.» y la Sección 6 es seggar::S6",
          txt("seggar::5.3.5").endswith("cobro indebido de la garantía.")
          and txt("seggar::S6").startswith("6. Instrumentación."))
    check("F (E2-046): efemin::1.3.7.2 es un renglón (el encabezado de columnas reimpreso sale del texto) y su herencia "
          "no lleva celdas de ese encabezado",
          txt("efemin::1.3.7.2") == "1.3.7.2. En moneda extranjera. 15 15"
          and not any(t[2] in ("Tasas en %", "Grupo A", "Concepto") for t in her("efemin::1.3.7.2")))
    check("F (E2-066): gerc::2.3.1.4 no hereda «Exposiciones Límite» como intro del 2.3.1",
          not any(t[1] == "2.3.1" and t[0] == "intro" for t in her("gerc::2.3.1.4"))
          and "gerc::2.3.1::intro" not in ch["gerc"])
    check("G (E2-094): lingeef::6.2.1.10 abre y sigue a 6.2.1.9; 6.2.1::cierre no existe; 6.2.1.9 no hereda los "
          "fragmentos del número",
          sigue("lingeef::6.2.1.9") == "lingeef::6.2.1.10" and "lingeef::6.2.1::cierre" not in ch["lingeef"]
          and not any(t[2].strip(". ") == "" for t in her("lingeef::6.2.1.9")))
    check("H (E2-005): ri_cc::R4::1.2.3 abre («1.2.3.Conceptos…») y 1.2.2 son cinco renglones",
          txt("ri_cc::R4::1.2.3").startswith("1.2.3.Conceptos comprendidos") and txt("ri_cc::R4::1.2.2").count("\n") == 4)
    check("J (E1-047): ceninf::S0 lleva el título y la fecha de la carátula, sin «Preámbulo»",
          txt("ceninf::S0") == "CENTRALES DE INFORMACIÓN\n-Última comunicación incorporada: “A” 8393-\n"
                               "Texto ordenado al\n28/01/2026")
    f3 = [c["texto"] for i, c in ch["ri_ccna"].items() if i.startswith("ri_ccna::D1F3::")]
    f4 = "\n".join(c["texto"] for i, c in ch["ri_ccna"].items() if i.startswith("ri_ccna::D1F4::"))
    check("K, aceptación de R5-e actualizada (las unidades del formulario, que A divide en bloques): el código de "
          "formulario del pie de D1F3 ya no está en el texto (es pie), ninguna unidad de D1F3 termina en la «C» suelta; "
          "D1F4 sigue sin letras sueltas y con su «CODIGO»",
          bool(f3) and not any("Fórm. 4368" in t for t in f3) and not any(t.endswith("\nC") for t in f3)
          and "CODIGO" in f4 and not any(len(r.strip()) == 1 and r.strip().isupper() for r in f4.split("\n")))
    oc = ch["ri_oc"]
    tres = [i for i in oc if i.startswith("ri_oc::3.")]
    check("E reemplaza a R5-g: «3. Aclaraciones» sale de ri_oc::S2 y las 51 unidades de 3.1 a 3.51 lo heredan",
          not txt("ri_oc::S2").endswith("3. Aclaraciones") and len(tres) == 51
          and all(any(t["texto"] == "3. Aclaraciones" for t in oc[i]["herencia"]) for i in tres), str(len(tres)))
    check("H reemplaza a R5-f en ri_ccna: abren 2.1.1 a 2.1.8, 5.1 y 8.1 de D1A1 y 5.1 de D1A2",
          all(f"ri_ccna::D1A1::2.1.{k}" in ch["ri_ccna"] for k in range(1, 9)) and "ri_ccna::D1A1::5.1" in ch["ri_ccna"]
          and "ri_ccna::D1A1::8.1" in ch["ri_ccna"] and "ri_ccna::D1A2::5.1" in ch["ri_ccna"])
    check("A reemplaza a R5-a′: ri_oc::C.11 conserva sus dos renglones y ninguna herencia de C.1 a C.11 tiene el bloque "
          "de validaciones",
          txt("ri_oc::C.11").endswith("para el último día de cada mes).") and txt("ri_oc::C.11").count("\n") == 1
          and not any("Criterios de validación" in t["texto"] or "Se considerará no validada" in t["texto"]
                      for k in range(1, 12) for t in oc[f"ri_oc::C.{k}"]["herencia"]))
    rech36 = [x for x in cargar(d, "estructura_nmaeef.json")["rechazos_header"] if x["pagina"] == 36]
    ids_n = list(ch["nmaeef"])
    check("L (E1-008): los rótulos del índice del Anexo IV de nmaeef (p. 36) no abren raíz (L o la regla 8); el cuerpo "
          "abre, y 4.4.2 termina antes de 4.5.1",
          sum(1 for x in rech36 if x["motivo"] == "indice_l") == 4
          and all(x["motivo"] in ("indice_l", "lista_de_puntos_r8") for x in rech36)
          and "nmaeef::A4::4.4.2" in ch["nmaeef"]
          and ids_n[ids_n.index("nmaeef::A4::4.4.2") + 1] == "nmaeef::A4::4.5.1", str([x["motivo"] for x in rech36]))
    h143 = her("ri2_ae::A3::14.3")
    check("M (E2-002): de la raíz 0 del Anexo III de ri2_ae se hereda solo su título",
          [t[2] for t in h143 if t[1] == "A3::S0"] == ["PROCEDIMIENTOS MINIMOS DE AUDITORÍA"], str(h143))
    check("R5-a por lista que queda (E2-098, E2-058): ri_oc::B.1.28 hereda el cierre de B.1, y ri_spi::C.1::cierre está",
          any(t[0] == "cierre" and t[1] == "B.1" and t[2].startswith("En el punto B.1.24") for t in her("ri_oc::B.1.28"))
          and "ri_spi::C.1::cierre" in ch["ri_spi"])
    check("A en la carátula (G5): ri_ii_31_12_19 no abre divisiones en la p. 1",
          not any(a.get("tipo") == "division_a" and a.get("pagina") == 1
                  for a in cargar(d, "estructura_ri_ii_31_12_19.json")["avisos"]))
    malos = []
    for uid, (origen, fija, sha16) in NEGATIVOS_LEIDAS_S06.items():
        c = u(uid)
        campos = ("sha256_propio", "paginas") + (("herencia",) if fija == "corte y herencia" else ())
        if not c or _sha16_campos(c, campos) != sha16:
            malos.append(f"{uid} ({origen})")
    check(f"negativos del §4: las {len(NEGATIVOS_LEIDAS_S06)} leídas en S1-ter, correctas, de estos TOs conservan su corte "
          f"({sum(1 for v in NEGATIVOS_LEIDAS_S06.values() if v[1] == 'corte y herencia')} también su herencia)",
          bool(NEGATIVOS_LEIDAS_S06) and not malos, str(malos))
    cob = cargar(d, "cobertura.json")
    check(f"cobertura exacta en los {len(TOS_S06)} TOs", all(cob[to]["cobertura_exacta"] for to in TOS_S06),
          str([to for to in TOS_S06 if not cob[to]["cobertura_exacta"]]))
    # la fila de la tanda 0, solo acá, con la exclusión apagada
    with _tanda0_sin_exclusion():
        correr_e0.correr(d / "tanda0_sin_exclusion", manifiesto=_ManifiestoParticion(("polcre",)), version_e0="e0-r2")
    pc = {c["id"]: c for c in cargar(d / "tanda0_sin_exclusion", "chunks_polcre.json")}
    h611 = [(t["tipo"], t["texto"]) for t in pc["polcre::6.1.1.3"]["herencia"] if t["unidad_origen"] == "6.1.1"]
    check("B (E2-055, tanda 0, solo en el selftest y con la exclusión apagada acá): polcre 6.1.1 no se parte en encabezado "
          "e intro: el párrafo va entero, con su número, en la intro",
          len(h611) == 1 and h611[0][0] == "intro" and h611[0][1].startswith("6.1.1. Las operaciones")
          and "Coe-\nficiente" in h611[0][1], str(h611))
    check("la exclusión de la tanda 0 vuelve a regir después del caso", correr_e0.TOS_TANDA0_SIN_S0_6 == TOS_TANDA0)


def test_s0_doble(base: Path) -> None:
    print("== m) S0 de U-SEG-OFICIAL: doble corrida de e0-r2, byte a byte")
    for nombre in ("a", "b"):
        correr_e0.correr(base / f"doble_{nombre}", manifiesto=_ManifiestoParticion(("garopt", "ri_spi")),
                         version_e0="e0-r2")
    sha_a, sha_b = correr_e0.shas_salida(base / "doble_a"), correr_e0.shas_salida(base / "doble_b")
    check("e0-r2 sobre garopt y ri_spi: dos corridas con los mismos sha256", sha_a == sha_b and bool(sha_a),
          f"{len(sha_a)} archivos")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir-a", default=None)
    ap.add_argument("--dir-b", default=None)
    args = ap.parse_args()

    if args.dir_a and args.dir_b:
        dir_a, dir_b = Path(args.dir_a), Path(args.dir_b)
    else:
        base = Path(tempfile.mkdtemp(prefix="e0_selftest_"))
        dir_a, dir_b = base / "corrida_a", base / "corrida_b"
        print(f"corriendo el pipeline dos veces bajo {base} …")
        correr_e0.correr(dir_a)
        correr_e0.correr(dir_b)

    test_determinismo(dir_a, dir_b)
    test_cobertura(dir_a)
    test_t4(dir_a)
    test_correcciones(dir_a)
    test_minichunks(dir_a)
    base_s0 = Path(tempfile.mkdtemp(prefix="e0_selftest_s0_"))
    # las pruebas de etapas anteriores corren con las reglas de S0-6a apagadas: prueban sus reglas (S0-6a)
    with _sin_s06():
        test_s0_legada()
        test_s0_casos(base_s0 / "casos")
        test_s0_sinteticos()
        test_s03_legada()
        test_s03_sinteticos()
        test_s03_casos(base_s0 / "casos_s03")
        test_s04_legada()
        test_s04_sinteticos()
        test_s04_casos(base_s0 / "casos_s04")
        test_s05_legada()
        test_s05_sinteticos()
        test_s05_casos(base_s0 / "casos_s05")
        test_s05bis_legada()
        test_s05bis_sinteticos()
        test_s05bis_casos(base_s0 / "casos_s05bis")
    test_s0_doble(base_s0)
    test_s06_legada()
    test_s06_sinteticos()
    test_s06bis_sinteticos()
    test_s06_casos(base_s0 / "casos_s06")

    total = len(RESULTADOS)
    ok = sum(1 for _, b, _ in RESULTADOS if b)
    print(f"\nSELFTEST: {ok}/{total} PASS")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
