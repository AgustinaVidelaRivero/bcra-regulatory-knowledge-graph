"""Selftest de la unidad B5.8.3: parser de tablas (módulo e0_tablas.py;
NO toca selftest_e0.py, selftest_b52.py, selftest_b581.py ni selftest_b582.py).

Cubre, con los casos MEDIDOS del scoping U-B5.6-0 y de la calibración de
B5.8.3 como fixtures:

  A. GARANTÍA DE NO-CAMBIO estructural: e0_tablas es standalone — no importa
     e0_lib ni healthcheck_e0 ni correr_e0 (ninguna rama del chunker de
     prosa pasa por él; los caminos que hoy producen unidades no lo conocen).
  B. R-TC — regla de tabla de contenido (la sellada del censo B5.8.0):
     retiene la 3×2 de zona media (tabla de montos de capmin p.4) y las
     grillas de ri_acsf; descarta banner (2 filas / bbox en el 12 % sup),
     pie (1 fila / bbox en el 10 % inf) y tablas de 1 columna.
  C. R-COL — guarda de alineación (lección RX-10, scoping §2.4): dispara con
     el colapso medido de ric p.8 (19 fragmentos numéricos en una celda,
     columna 91 % vacía); NO dispara con 'Vigencia:\\n01/07/2021' (2
     fragmentos), ni con '3%\\n6%' de manual p.256 (fusión declarada, no
     rechazo), ni con descripciones envueltas no numéricas (ri_laft), ni
     con una columna numérica poblada fila a fila.
  D. R-ENC — encabezado conservador: título en primera columna ('TABLA
     FORMA JURIDICA') capturado; 'Factor de ponde-' (última columna, ric
     p.8) NO es título y se fusiona como encabezado envuelto con
     'ración (en %)'; encabezado directo sin título (capmin); estado
     no_determinado sin señales.
  E. R-COSTURA — _match_costura: repetición verbatim de título/encabezado
     detectada; sin repetición devuelve vacío (la costura queda candidata,
     jamás fusionada).
  F. Casos reales sobre PDFs del repo (determinístico, USD 0):
     - CASO TESTIGO RX-10 (obligatorio del mandato): capmin p.4 — la tabla
       de montos del punto 1.2 parseada con estructura: encabezado
       'Bancos'/'Restantes entidades…', fila de valores ['5.000','2.500'] →
       bancos 5.000 / restantes 2.500 (el par que la linealización invirtió
       en el grafo), reconstrucción con pérdida 0.
     - ric p.8: la tabla de ponderadores se DECLARA alineacion_no_confiable
       (colapso en columna 2); ric p.20: la planilla de derivados con
       encabezado rotado da pérdida 0 por caracteres (el falso 89 % por
       tokens queda como declaración informativa).
     - ri_acsf (control negativo de B5.8.1: su vía es ESTA unidad): rinde
       con 1 tabla lógica de 2 segmentos cosidos (encabezado repetido
       verbatim p.2→3).
     - ri_laft: 8 tablas lógicas / 43 segmentos físicos (los del scoping
       §2.1) / 35 costuras aplicadas; la geometría sin encabezado repetido
       de p.9 (TABLA PROVINCIA tras TABLA PRODUCTO…) queda CANDIDATA sin
       fusionar — y es en efecto otra tabla.

Uso: python3 selftest_b583.py  (sin argumentos, USD 0, sin LLM).
"""

from __future__ import annotations

import sys
from pathlib import Path

import e0_tablas as T

REPO = Path(__file__).resolve().parents[4]
PDF_DEV = REPO / "data" / "experiment" / "subset"
PDF_PREP = REPO / "data" / "experiment" / "escalado_prep" / "pdfs"

RESULTADOS: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, ok, detalle))
    print(f"  [{'PASS' if ok else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""))


# ------------------------------------------------------- A. no-cambio
print("A. Garantía estructural de no-cambio")
fuente = (Path(__file__).parent / "e0_tablas.py").read_text(encoding="utf-8")
check("A1 e0_tablas no importa e0_lib",
      "import e0_lib" not in fuente and "from e0_lib" not in fuente)
check("A2 e0_tablas no importa healthcheck_e0 ni correr_e0",
      "healthcheck_e0" not in fuente and "import correr_e0" not in fuente)
check("A3 e0_lib no conoce a e0_tablas (ninguna rama del camino vigente pasa por el parser)",
      "e0_tablas" not in (Path(__file__).parent / "e0_lib.py").read_text(encoding="utf-8"))

# ------------------------------------------------------- B. R-TC
print("B. Regla de tabla de contenido (sellada por el censo B5.8.0)")
ALTO = 842.0
check("B1 3x2 en zona media es tabla de contenido (montos capmin p.4)",
      T.clasificar_tabla_contenido(3, 2, (178, 265, 465, 322), ALTO) == (True, None))
check("B2 banner de 2 filas cae por min_filas (capmin p.4 t0)",
      T.clasificar_tabla_contenido(2, 2, (73, 74, 566, 100), ALTO) == (False, "min_filas"))
check("B3 pie de 1 fila cae por min_filas",
      T.clasificar_tabla_contenido(1, 4, (73, 784, 566, 809), ALTO) == (False, "min_filas"))
check("B4 3 filas integramente en el 12% superior caen por banner_superior",
      T.clasificar_tabla_contenido(3, 2, (73, 10, 566, 95), ALTO) == (False, "banner_superior"))
check("B5 3 filas integramente en el 10% inferior caen por pie_inferior",
      T.clasificar_tabla_contenido(3, 4, (73, 770, 566, 830), ALTO) == (False, "pie_inferior"))
check("B6 una columna cae por min_cols",
      T.clasificar_tabla_contenido(5, 1, (73, 300, 566, 500), ALTO) == (False, "min_cols"))
check("B7 tabla grande que ARRANCA en zona de banner pero sigue no cae (no esta integramente contenida)",
      T.clasificar_tabla_contenido(19, 2, (73, 50, 566, 700), ALTO) == (True, None))
# B8 se verifica sobre PDF real en F11 (cajas de carátula sin contenido:
# manual p.2 / ri2_pm p.1 → descarte sin_contenido)

# ------------------------------------------------------- C. R-COL
print("C. Guarda de alineación (RX-10)")
colapso_ric = [
    ["", "", "Factor de ponde-"],
    ["Código", "Concepto", None],
    [None, None, "ración (en %)"],
    ["", "", None],
    ["11000000", "Disponibilidades",
     "0\n2\n4\n10\n20\n30\n40\n45\n50\n60\n65\n75\n85\n100\n130\n150\n200\n250\n1250"],
    ["11100000", "Exposiciones a gobiernos y bancos centrales", None],
    ["11200000", "Exposiciones a BMD", None],
]
d = T.detectar_colapso(colapso_ric)
check("C1 el colapso de ric p.8 dispara (19 fragmentos numericos, columna vacia)",
      d is not None and d["fragmentos"] == 19 and d["columna"] == 2,
      str(d))
check("C2 'Vigencia:\\n01/07/2021' no dispara (2 fragmentos)",
      T.detectar_colapso([["Versión: 1a.", "Vigencia:\n01/07/2021"],
                          ["a", "b"], ["c", "d"], ["e", "f"]]) is None)
check("C3 la fusion '3%\\n6%' de manual p.256 no dispara (fusion declarada, no rechazo)",
      T.detectar_colapso([["Categoría", "Con garantías", "Sin garantías"],
                          ["2. a) En observación\nb) En riesgo", "3%\n6%", "5%\n12%"],
                          ["3. Con problemas", "12%", "25%"],
                          ["4. Alto riesgo", "25%", "50%"]]) is None)
check("C4 descripcion envuelta no numerica no dispara (ri_laft)",
      T.detectar_colapso([["Código", "Descripción"],
                          ["3005", "Sociedad de\nResponsabilidad\nLimitada\ncon variantes\nde escritura"],
                          ["3006", "Sociedad Anónima"],
                          ["3007", "Sociedad en Comandita"]]) is None)
check("C5 columna numerica poblada fila a fila no dispara aunque haya una celda multilinea",
      T.detectar_colapso([["Código", "Valor"],
                          ["100", "1\n2\n3\n4"],
                          ["200", "5"], ["300", "6"], ["400", "7"], ["500", "8"]]) is None)

# ------------------------------------------------------- D. R-ENC
print("D. Encabezado conservador")
enc = T.detectar_encabezado([
    ["TABLA FORMA JURIDICA", None],
    ["Código", "Descripción"],
    ["3001", "Sociedad de Bolsa"],
    ["3002", "Sociedad Colectiva"],
])
check("D1 titulo en primera columna capturado (ri_laft)",
      enc["titulo"] == "TABLA FORMA JURIDICA" and enc["filas_encabezado"] == 1
      and enc["columnas"] == ["Código", "Descripción"], str(enc))
enc = T.detectar_encabezado(colapso_ric)
check("D2 'Factor de ponde-' (ultima columna) NO es titulo y se fusiona envuelto",
      enc["titulo"] is None
      and enc["columnas"] is not None
      and enc["columnas"][2] == "Factor de ponde- ración (en %)", str(enc))
enc = T.detectar_encabezado([
    ["Bancos", "Restantes entidades\n(salvo Cajas de Crédito Cooperativas)"],
    ["-En millones de pesos-", None],
    ["5.000", "2.500"],
])
check("D3 encabezado directo sin titulo (capmin p.4; la fila de unidad de "
      "medida integra la zona de encabezado)",
      enc["titulo"] is None and enc["filas_encabezado"] == 2
      and enc["columnas"][0] == "Bancos -En millones de pesos-"
      and enc["columnas"][1].startswith("Restantes entidades"), str(enc))
enc = T.detectar_encabezado([["1", "2"], ["3", "4"], ["5", "6"]])
check("D4 sin señales queda no_determinado y nada se recorta",
      enc["estado"] == "no_determinado" and enc["filas_encabezado"] == 0)

# ------------------------------------------------------- E. R-COSTURA
print("E. Costura: repeticion verbatim o nada")
seg_a = {"filas": [["TABLA FORMA JURIDICA", None], ["Código", "Descripción"],
                   ["3001", "Sociedad de Bolsa"]]}
seg_b = {"filas": [["TABLA FORMA JURIDICA", None], ["Código", "Descripción"],
                   ["3018", "Federación"]]}
check("E1 titulo y encabezado repetidos verbatim detectados (ri_laft p.5→6)",
      T._match_costura(seg_a, seg_b) == [0, 1])
seg_c = {"filas": [["TABLA PROVINCIA", None], ["Código", "Descripción"],
                   ["01", "Buenos Aires"]]}
check("E2 sin repeticion verbatim devuelve vacio (candidata, jamas fusion)",
      T._match_costura(seg_a, seg_c) == [])
seg_d = {"filas": [["CÓDIGO", "", "DESCRIPCIÓN"], ["600", "", "RECEPCION"]]}
seg_e = {"filas": [["CÓDIGO", "", "DESCRIPCIÓN"], ["700", "", "OTROS"]]}
check("E3 encabezado repetido sin titulo tambien cose (ri_acsf p.2→3)",
      T._match_costura(seg_d, seg_e) == [0])

# ------------------------------------------------------- F. PDFs reales
print("F. Casos reales (PDFs del repo)")

r = T.parsear_to(PDF_DEV / "TO_capitales_minimos_actual.pdf", "capmin")
t0 = next((t for t in r["tablas_logicas"] if t["segmentos"][0]["pagina"] == 4), None)
filas_testigo = t0["segmentos"][0]["filas"] if t0 else []
check("F1 TESTIGO RX-10: la tabla de montos de capmin 1.2 se parsea con estructura",
      t0 is not None and t0["estado"] == "parseada"
      and filas_testigo[-1] == ["5.000", "2.500"]
      and filas_testigo[0][0] == "Bancos"
      and filas_testigo[0][1].startswith("Restantes entidades"),
      str(filas_testigo))
check("F2 TESTIGO RX-10: emparejamiento por columna = bancos 5.000 / restantes 2.500",
      t0 is not None
      and dict(zip([_c.split("\n")[0] for _c in filas_testigo[0]], filas_testigo[-1]))
      == {"Bancos": "5.000", "Restantes entidades": "2.500"})
check("F3 TESTIGO RX-10: reconstruccion con perdida 0",
      t0 is not None and t0["declaraciones"]["pct_perdida_max"] == 0.0
      and t0["declaraciones"]["chars_perdidos_total"] == 0)

r = T.parsear_to(PDF_DEV / "TO_regimen_informativo_contable_mensual_actual.pdf", "ric")
t1 = next((t for t in r["tablas_logicas"]
           if t["segmentos"][0]["pagina"] == 8 and t["segmentos"][0]["n_filas"] > 3), None)
check("F4 ric p.8 (ponderadores) DECLARADA alineacion_no_confiable, no emitida",
      t1 is not None and t1["estado"] == "declarada"
      and t1["causas"] == ["alineacion_no_confiable"]
      and t1["declaraciones"]["colapsos"][0]["fragmentos"] == 19,
      str(t1["causas"] if t1 else None))
t20 = next((t for t in r["tablas_logicas"]
            if t["segmentos"][0]["pagina"] == 20 and t["segmentos"][0]["n_cols"] == 13), None)
check("F5 ric p.20 (planilla con encabezado rotado): perdida 0 por caracteres, "
      "diferencia por tokens declarada informativa",
      t20 is not None and t20["estado"] == "parseada"
      and t20["declaraciones"]["pct_perdida_max"] == 0.0
      and t20["declaraciones"]["tokens_perdidos_total"] > 0,
      str(t20["declaraciones"]["pct_perdida_max"] if t20 else None))

r = T.parsear_to(PDF_PREP / "ri_acsf.pdf", "ri_acsf")
check("F6 ri_acsf rinde por la via tabular (control negativo de B5.8.1)",
      r["conteos"]["rinde"] and r["conteos"]["tablas_logicas"] == 1
      and r["conteos"]["segmentos"] == 2 and r["conteos"]["costuras_aplicadas"] == 1,
      str(r["conteos"]))
seg2 = r["tablas_logicas"][0]["segmentos"][1]
check("F7 ri_acsf: el encabezado repetido de la continuacion queda marcado, no es dato",
      seg2["filas_encabezado_repetido"] == [0])

r = T.parsear_to(PDF_PREP / "ri_laft.pdf", "ri_laft")
check("F8 ri_laft: 8 tablas logicas sobre los 43 segmentos fisicos del scoping",
      r["conteos"]["tablas_logicas"] == 8 and r["conteos"]["segmentos"] == 43
      and r["conteos"]["costuras_aplicadas"] == 35, str(r["conteos"]))
check("F9 ri_laft p.9: geometria sin encabezado repetido queda CANDIDATA sin fusionar",
      len(r["costuras_candidatas"]) == 1
      and r["costuras_candidatas"][0]["pagina"] == 9
      and r["costuras_candidatas"][0]["motivo"] == "geometria_sin_encabezado_repetido")
t_prov = next((t for t in r["tablas_logicas"]
               if t["encabezado"]["titulo"] == "TABLA PROVINCIA"), None)
check("F10 ...y es en efecto otra tabla (TABLA PROVINCIA, logica propia)",
      t_prov is not None and t_prov["segmentos"][0]["pagina"] == 9)

r = T.parsear_to(PDF_PREP / "ri2_pm.pdf", "ri2_pm")
check("F11 ri2_pm: la caja de caratula vacia de p.1 se descarta sin_contenido "
      "y el TO queda declarado (su material es ficha, no tabla)",
      r["descartadas_por_regla"]["conteos"].get("sin_contenido", 0) >= 1
      and not r["conteos"]["rinde"], str(r["conteos"]))

# ------------------------------------------------------- resumen
ok = sum(1 for _, o, _ in RESULTADOS if o)
print(f"\n{ok}/{len(RESULTADOS)} checks OK")
if ok != len(RESULTADOS):
    for n, o, det in RESULTADOS:
        if not o:
            print(f"  FALLA: {n} {det}")
    sys.exit(1)
