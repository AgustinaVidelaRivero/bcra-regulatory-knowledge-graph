"""Selftest de la unidad B5.2: regex de marcadores relajado + guarda, y
health-check de troceo (módulos nuevos; NO toca selftest_e0.py).

Cubre, con los casos MEDIDOS del proyecto como fixtures:

  A. RE_MARCA_INDICE (con guiones, sin cambios): las formas reales del subset
     ('-Índice-', '- Indice-', '-Índice –') siguen matcheando.
  B. RE_MARCA_INDICE_SIN_GUIONES (nuevo) y su guarda:
     - matchea las formas reales del corpus de escalado ('Índice' a línea
       entera: casos cedin p.2, ri2_ae p.2, ri_transpa p.1);
     - NO matchea la prosa medida de ri_dcpc p.10 ('para aquellos que sean
       actualizables por algún índice.') ni la línea envuelta en minúscula
       'índice' medida en el cuerpo de cap — los dos falsos marcadores que
       motivan la guarda;
     - la guarda posicional (POS_MARCA_INDICE) se testea vía
       clasificar_paginas con páginas sintéticas.
  C. RE_SECCION / RE_SECCION_EN_LINEA con separador [.:]:
     - el punto sigue funcionando (todo el subset);
     - los dos puntos matchean el estilo medido de optico ('Sección 50:
       Información institucional…');
     - 'sección' en minúscula (remisión en prosa) sigue sin matchear.
  D. Integración sintética: clasificar_paginas y parsear_cuerpo sobre
     páginas fabricadas con la variante ':' producen la sección y sus puntos.
  E. Health-check (healthcheck_e0): las señales disparan sobre el caso
     sintético que corresponde y no disparan sobre los sanos.

Uso: python3 selftest_b52.py  (sin argumentos, $0, sin LLM).
"""

from __future__ import annotations

import sys

import e0_lib as E0
from healthcheck_e0 import MARCA_CID, health_check_to  # noqa: F401  (import chequea el módulo)

RESULTADOS: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, ok, detalle))
    print(f"  [{'PASS' if ok else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""))


# ---------------------------------------------------------------- fixtures

def linea(texto: str, pagina: int = 1, top: float = 50.0, x0: float = 60.0,
          ngaps: int = 0) -> E0.Linea:
    return E0.Linea(pagina=pagina, top=top, x0=x0, texto=texto, ngaps=ngaps,
                    ultimo_numerico=False, primer_codigo=False)


def pagina_de(textos: list[str], pagina: int = 1) -> list[E0.Linea]:
    return [linea(t, pagina=pagina, top=30.0 + 14.0 * i)
            for i, t in enumerate(textos)]


# ------------------------------------------------------------------- tests

def test_regex_indice() -> None:
    print("== A. marcador con guiones: formas reales del subset, sin cambios")
    for forma in ("-Índice-", "- Indice-", "-Índice –", "-Índice -"):
        check(f"RE_MARCA_INDICE matchea {forma!r}",
              bool(E0.RE_MARCA_INDICE.match(forma)))

    print("== B. marcador sin guiones (nuevo) y su guarda de forma")
    for forma in ("Índice", "Indice"):
        check(f"SIN_GUIONES matchea {forma!r} (formas medidas: cedin, ri2_ae, "
              "ri_transpa)", bool(E0.RE_MARCA_INDICE_SIN_GUIONES.match(forma)))
    falsos = [
        ("para aquellos que sean actualizables por algún índice.",
         "prosa medida ri_dcpc p.10"),
        ("índice", "línea envuelta en minúscula medida en el cuerpo de cap"),
        ("Índice.", "puntuación final"),
        ("Índice General", "más de una palabra"),
        ("el Índice", "palabra no inicial"),
        ("ÍNDICE DE ACTUALIZACIÓN", "título de otra cosa"),
    ]
    for t, motivo in falsos:
        check(f"SIN_GUIONES rechaza {t!r} ({motivo})",
              not E0.RE_MARCA_INDICE_SIN_GUIONES.match(t))


def test_regex_seccion() -> None:
    print("== C. header de sección con separador [.:]")
    casos_ok = [
        ("Sección 1. Capitales mínimos", "1", "punto (subset)"),
        ("Sección 10 . Título", "10", "punto con espacio (subset)"),
        ("Sección 50: Información institucional de entidades financieras",
         "50", "dos puntos (estilo medido de optico p.3)"),
        ("Sección 7 : Título", "7", "dos puntos con espacio"),
        ("Sección 3:", "3", "dos puntos sin título en línea"),
    ]
    for t, num, motivo in casos_ok:
        m = E0.RE_SECCION.match(t)
        check(f"RE_SECCION matchea {t!r} → num {num} ({motivo})",
              bool(m) and m.group(1) == num)
    casos_no = [
        ("sección 4: requisitos", "minúscula: remisión en prosa"),
        ("Sección 5 Título", "sin separador"),
        ("la Sección 6: aplicable", "no inicia la línea"),
        ("Sección A. Título", "número no numérico"),
    ]
    for t, motivo in casos_no:
        check(f"RE_SECCION rechaza {t!r} ({motivo})", not E0.RE_SECCION.match(t))
    m = E0.RE_SECCION_EN_LINEA.search("B.C.R.A. Sección 7: Título largo")
    check("RE_SECCION_EN_LINEA matchea 'B.C.R.A. Sección 7: …'",
          bool(m) and m.group(1) == "7")


def test_guarda_en_clasificar_paginas() -> None:
    print("== B(cont). guarda posicional y de forma vía clasificar_paginas")
    # página real de índice sin guiones (forma cedin p.2: título, 'Índice', entradas)
    p_indice = pagina_de(["B.C.R.A. CERTIFICADOS", "Índice",
                          "Sección 1. Alta.", "Sección 2. Baja."])
    roles = E0.clasificar_paginas([p_indice])
    check("página con 'Índice' en línea 2 → rol indice", roles == [E0.ROL_INDICE],
          str(roles))

    # el mismo marcador FUERA de la zona de título (línea > POS_MARCA_INDICE)
    p_tarde = pagina_de(["UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS",
                         "Índice", "texto"])
    roles = E0.clasificar_paginas([p_tarde])
    check(f"'Índice' en línea 7 (> POS_MARCA_INDICE={E0.POS_MARCA_INDICE}) "
          "NO clasifica índice", roles == [E0.ROL_PORTADA], str(roles))

    # prosa medida de ri_dcpc: no clasifica índice
    p_prosa = pagina_de(["B.C.R.A. RÉGIMEN", "los valores de origen",
                         "para aquellos que sean actualizables por algún índice.",
                         "más prosa"])
    roles = E0.clasificar_paginas([p_prosa])
    check("prosa sobre índices de actualización NO clasifica índice",
          roles == [E0.ROL_PORTADA], str(roles))

    # línea envuelta en minúscula (caso cap): en página de cuerpo, tras índice real
    p_idx = pagina_de(["-Índice-", "Sección 1. Una.", "Sección 2. Otra."], pagina=1)
    p_cuerpo = pagina_de(["B.C.R.A. TÍTULO", "Sección 1. Una.",
                          "1.1. Punto con texto de largo suficiente para prosa.",
                          "índice",
                          "continuación."], pagina=2)
    roles = E0.clasificar_paginas([p_idx, p_cuerpo])
    check("página de cuerpo con línea envuelta 'índice' (minúscula, caso cap) "
          "sigue siendo cuerpo", roles == [E0.ROL_INDICE, E0.ROL_CUERPO], str(roles))

    # la forma con guiones sigue clasificando en cualquier posición (sin cambio)
    p_guiones = pagina_de(["UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS",
                           "-Índice-"])
    roles = E0.clasificar_paginas([p_guiones])
    check("'-Índice-' fuera de la zona de título sigue clasificando índice "
          "(comportamiento vigente intacto)", roles == [E0.ROL_INDICE], str(roles))


def test_integracion_seccion_colon() -> None:
    print("== D. integración sintética: sección con ':' se parsea entera")
    p_idx = pagina_de(["-Índice-", "Sección 2. Algo.", "Sección 3. Otra."], pagina=1)
    p_cuerpo = [
        linea("Sección 2: Título de la sección", pagina=2, top=30.0, x0=60.0),
        linea("2.1. Primer punto con su texto en la línea del label",
              pagina=2, top=60.0, x0=60.0),
        linea("texto de continuación del punto dos uno, con largo de prosa plena",
              pagina=2, top=74.0, x0=95.0),
        linea("2.2. Segundo punto con su texto en la línea del label",
              pagina=2, top=90.0, x0=60.0),
    ]
    paginas = [p_idx, p_cuerpo]
    roles = E0.clasificar_paginas(paginas)
    check("roles [indice, cuerpo]", roles == [E0.ROL_INDICE, E0.ROL_CUERPO], str(roles))
    res = E0.parsear_cuerpo("tst", "tst.pdf", paginas, roles)
    check("una sección parseada, numero '2'",
          len(res.secciones) == 1 and res.secciones[0].numero == "2",
          str([s.numero for s in res.secciones]))
    check("título de la sección capturado tras ':'",
          res.secciones[0].titulo == "Título de la sección",
          repr(res.secciones[0].titulo))
    hijos = [h.numero for h in res.secciones[0].hijos]
    check("puntos 2.1 y 2.2 colgados de la sección", hijos == ["2.1", "2.2"], str(hijos))
    # el índice también parsea entradas 'Sección N:' si aparecieran allí
    entradas = E0.parsear_indice(paginas, roles)
    secs_idx = [e["numero"] for e in entradas if e["tipo"] == "seccion"]
    check("parsear_indice sigue leyendo las entradas de sección del índice",
          secs_idx == ["2", "3"], str(secs_idx))
    # y el marcador sin guiones se salta como marcador, no entra como entrada
    p_idx2 = pagina_de(["Índice", "Sección 4. Una."], pagina=1)
    entradas2 = E0.parsear_indice([p_idx2], [E0.ROL_INDICE])
    check("'Índice' sin guiones en página de índice se salta (no es entrada)",
          all(e["titulo"] != "Índice" for e in entradas2),
          str(entradas2))


def test_healthcheck_sintetico() -> None:
    print("== E. health-check: señales sobre estructuras sintéticas")
    # señal cid: detector textual
    check("MARCA_CID presente en línea corrupta",
          MARCA_CID in "los dep(cid:243)sitos en pesos")
    check("MARCA_CID ausente en línea sana",
          MARCA_CID not in "los depósitos en pesos")
    # señal de tamaño y de páginas sin sección: sobre el reporte de un TO real
    # del subset con umbral artificialmente bajo, las unidades anómalas
    # aparecen y el veredicto deja de ser 'sano' — el mecanismo de umbral y
    # veredicto queda ejercitado sin fabricar PDFs
    from pathlib import Path
    pdf_pro = Path(E0.__file__).resolve().parents[3] / "experiment" / "subset" \
        / "TO_proteccion_usuarios_servicios_financieros_actual.pdf"
    r_sano = health_check_to(pdf_pro)
    check("pro con umbral de banda: sin unidades anómalas",
          not r_sano["senales"]["unidades_anomalas_por_tamano"]["anomalas"],
          f"max={r_sano['senales']['unidades_anomalas_por_tamano']['max_chars_propio']}")
    check("pro: cobertura exacta (señal 4 apagada)",
          r_sano["senales"]["cobertura_no_exacta"] is None)
    r_bajo = health_check_to(pdf_pro, umbral_chars=100)
    check("pro con umbral 100: dispara unidades_anomalas_por_tamano",
          "unidades_anomalas_por_tamano" in r_bajo["veredicto"],
          str(r_bajo["veredicto"]))
    check("las anómalas vienen ordenadas de mayor a menor",
          [a["chars_propio"] for a in
           r_bajo["senales"]["unidades_anomalas_por_tamano"]["anomalas"][:3]] ==
          sorted([a["chars_propio"] for a in
                  r_bajo["senales"]["unidades_anomalas_por_tamano"]["anomalas"]],
                 reverse=True)[:3])


def main() -> int:
    test_regex_indice()
    test_regex_seccion()
    test_guarda_en_clasificar_paginas()
    test_integracion_seccion_colon()
    test_healthcheck_sintetico()
    total = len(RESULTADOS)
    ok = sum(1 for _, b, _ in RESULTADOS if b)
    print(f"\nSELFTEST B5.2: {ok}/{total} PASS")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
