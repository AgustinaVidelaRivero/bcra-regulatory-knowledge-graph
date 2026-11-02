"""Selftest de la unidad B5.8.2: reglas de marcador por familia
(módulo nuevo; NO toca selftest_e0.py, selftest_b52.py ni selftest_b581.py).

Cubre, con los casos MEDIDOS del censo B5.8.0 y de la corrida B5.8.2 como
fixtures:

  A. GARANTÍA ESTRUCTURAL de no-cambio: `marcadores_b582` es False por
     default en clasificar_paginas/parsear_cuerpo/parsear_indice (y
     seccion_b582/banners_texto en separar_encabezado_pie); sin el flag,
     una página con 'INDICE' en mayúsculas sigue siendo portada y un TO
     digerible sintético produce unidades por el camino vigente (el
     predicado de activación es falso y jamás entra); el health-check de
     ri_ieccm (objetivo B5.8.1, sin variantes de marcador) reproduce
     EXACTAMENTE el artefacto sellado de la corrida B5.8.1 — la escalera
     nueva no altera el camino sin_raiz histórico.
  B. RE_MARCA_INDICE_B582: matchea las tres formas medidas ('INDICE'/
     'ÍNDICE' sostenidas, 'Índice -', '– Índice –') y rechaza los falsos
     medidos ('3.7.2. Indice a utilizar' de ri_dcpc p.24, la prosa de
     ri_dcpc p.10, la mención capitalizada no línea-entera de ri_dcpc p.24,
     'índice' minúscula del cuerpo de cap, 'ÍNDICE DE ACTUALIZACIÓN');
     la forma 'Índice' sola NO la toma (ya es del vigente B5.2). Guarda
     posicional vía clasificar_paginas; la heurística de continuación de
     índice NO se extiende (contraejemplo ri_dcpc p.3: dos líneas
     'SECCION 1 – …' en zona de título y la página sigue siendo cuerpo).
  C. RE_SECCION_B582_CAPS/LETRA: matchean las formas medidas de ri_dcpc,
     ri_psp y reqcac; rechazan 'Sección Punto Párrafo…' (seguef p.19),
     la remisión en prosa minúscula, la forma sin separador y la CAPS con
     punto (no medida). Sucesión por familias: A→B→C avanza (C es letra 3,
     no romano); IV→VI no sucede (salto); orden de reporte con letras y
     romanos.
  D. Integración sintética reqcac: banner de caja mixta repetido en ≥3
     páginas descartado, sección por variante capturada SIN cola envuelta
     (la prosa inmediata no se pega al título), continuación sin encabezado
     fluye a la sección abierta, puntos bajo sección con letra rechazados
     con registro, unidades SA/SB, cobertura exacta, índice extendido y
     divergencias con letras sin crash. Banner repetido en solo 2 páginas
     NO se descarta.
  E. Escalera del health-check sobre PDFs reales: reqcac sale en
     'marcadores'; consyr sale en 'sin_raiz' con la clave condicional
     `indice_b582` (roles reclasificados); pro (dev) sale 'vigente' sin
     claves nuevas.

Uso: python3 selftest_b582.py  (sin argumentos, USD 0, sin LLM).
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import e0_lib as E0
from healthcheck_e0 import health_check_to

RESULTADOS: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, ok, detalle))
    print(f"  [{'PASS' if ok else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""))


# ---------------------------------------------------------------- fixtures

def linea(texto: str, pagina: int = 1, top: float = 50.0, x0: float = 60.0,
          ngaps: int = 0) -> E0.Linea:
    return E0.Linea(pagina=pagina, top=top, x0=x0, texto=texto, ngaps=ngaps,
                    ultimo_numerico=False, primer_codigo=False)


def pagina_de(textos: list[str | tuple[str, float]], pagina: int = 1) -> list[E0.Linea]:
    """Cada ítem es un texto (x0=60) o una tupla (texto, x0)."""
    out = []
    for i, t in enumerate(textos):
        if isinstance(t, tuple):
            out.append(linea(t[0], pagina=pagina, top=30.0 + 14.0 * i, x0=t[1]))
        else:
            out.append(linea(t, pagina=pagina, top=30.0 + 14.0 * i))
    return out


BANNER = "Requisitos operativos de la caja mixta del título"
BANNER2 = "Casas de cambio de la caja mixta"


def paginas_reqcac_sintetico() -> list[list[E0.Linea]]:
    """Fixture con la anatomía medida de reqcac: índice reconocido por el
    vigente, banner de caja mixta (3 líneas, una de ellas B.C.R.A.) repetido
    en las 3 páginas de cuerpo, secciones por variante en la zona de
    encabezado y una página de continuación sin encabezado de sección."""
    p1 = pagina_de(["-INDICE-", "Sección A. Introducción",
                    "Sección B. Controles Generales"], pagina=1)
    p2 = pagina_de([
        (BANNER, 146.2), ("B.C.R.A.", 77.9), (BANNER2, 274.0),
        ("Sección A – Introducción", 97.9),
        ("Las casas y agencias deberán establecer una estrategia de control", 97.9),
        ("para la protección de sus activos informáticos en general", 97.9),
    ], pagina=2)
    p3 = pagina_de([
        (BANNER, 146.2), ("B.C.R.A.", 77.9), (BANNER2, 274.0),
        ("Sección B - Controles Generales", 97.9),
        ("El personal propio de tecnología deberá depender funcionalmente", 97.9),
        ("1.1. Algo con forma de punto que no pertenece a esta gramática", 97.9),
    ], pagina=3)
    p4 = pagina_de([
        (BANNER, 146.2), ("B.C.R.A.", 77.9), (BANNER2, 274.0),
        ("En los casos en que el procesamiento se realice en dependencias", 97.9),
        ("de terceros deberá existir una adecuada separación de ambientes", 97.9),
    ], pagina=4)
    return [p1, p2, p3, p4]


# ------------------------------------------------------------------- tests

def test_garantia_estructural() -> None:
    print("== A. garantía estructural de no-cambio")
    for fn, param in ((E0.clasificar_paginas, "marcadores_b582"),
                      (E0.parsear_cuerpo, "marcadores_b582"),
                      (E0.parsear_indice, "marcadores_b582")):
        firma = inspect.signature(fn)
        check(f"{fn.__name__}: {param} default False",
              firma.parameters[param].default is False)
    firma = inspect.signature(E0.separar_encabezado_pie)
    check("separar_encabezado_pie: seccion_b582 default False y "
          "banners_texto default None",
          firma.parameters["seccion_b582"].default is False
          and firma.parameters["banners_texto"].default is None)

    # sin el flag, el marcador en mayúsculas NO clasifica índice
    p = pagina_de(["TITULO DEL TO", "B.C.R.A.", "INDICE",
                   "1. Primera entrada del índice"])
    check("sin flag: página con 'INDICE' sostenidas sigue siendo portada",
          E0.clasificar_paginas([p]) == [E0.ROL_PORTADA],
          str(E0.clasificar_paginas([p])))
    check("con flag: la misma página clasifica índice",
          E0.clasificar_paginas([p], marcadores_b582=True) == [E0.ROL_INDICE])

    # un digerible sintético produce unidades vigentes: jamás entra
    p_idx = pagina_de(["-Índice-", "Sección 1. Una."], pagina=1)
    p_cuerpo = [
        linea("Sección 1: Título", pagina=2, top=30.0, x0=60.0),
        linea("1.1. Primer punto con su texto en la línea del label", pagina=2,
              top=60.0, x0=60.0),
    ]
    roles = E0.clasificar_paginas([p_idx, p_cuerpo])
    res = E0.parsear_cuerpo("dig", "dig.pdf", [p_idx, p_cuerpo], roles)
    chunks = E0.construir_chunks(res)
    check("digerible sintético: unidades por el camino vigente "
          "(el predicado de activación es falso)",
          len(chunks) > 0 and res.modo_lectura == "vigente", f"chunks={len(chunks)}")

    # regresión fuerte: el health-check de un objetivo B5.8.1 SIN variantes
    # de marcador reproduce EXACTAMENTE el artefacto sellado de esa corrida
    repo = Path(E0.__file__).resolve().parents[3]
    sellado = (repo / "experiment/segmentacion_84/b581_sin_raiz/ri_ieccm"
               / "healthcheck_ri_ieccm.json")
    r = health_check_to(repo / "experiment/escalado_prep/pdfs/ri_ieccm.pdf")
    check("ri_ieccm: health-check byte-idéntico al artefacto sellado de B5.8.1 "
          "(la escalera nueva no toca el camino sin_raiz histórico)",
          json.dumps(r, ensure_ascii=False, indent=1)
          == sellado.read_text(encoding="utf-8"),
          f"modo={r['modo_lectura']}")
    check("ri_ieccm: sin clave indice_b582 (roles sin variantes)",
          "indice_b582" not in r)


def test_regex_indice_b582() -> None:
    print("== B. variantes de marcador de índice y sus guardas")
    for forma, motivo in [("INDICE", "sostenidas: nmaeef p.1, ri_dcpc p.1-2, ri_psp p.1"),
                          ("ÍNDICE", "sostenidas con tilde: ri_msrl p.1"),
                          ("Índice -", "guion a la derecha: consyr p.2"),
                          ("– Índice –", "guion largo a ambos lados: seguef p.2")]:
        check(f"B582 matchea {forma!r} ({motivo})",
              bool(E0.RE_MARCA_INDICE_B582.match(forma)))
    falsos = [
        ("3.7.2. Indice a utilizar", "numeración adelante (ri_dcpc p.24)"),
        ("para aquellos que sean actualizables por algún índice.",
         "prosa medida (ri_dcpc p.10)"),
        ("Se utilizará el Índice de Precios al Consumidor Nacional (IPC)",
         "mención capitalizada no línea-entera (ri_dcpc p.24)"),
        ("índice", "minúscula (línea envuelta medida en cap, guarda B5.2)"),
        ("ÍNDICE DE ACTUALIZACIÓN", "título de otra cosa"),
        ("INDICE GENERAL", "más de una palabra"),
        ("Índice", "forma sola: ya la toma el vigente B5.2, no esta regla"),
    ]
    for t, motivo in falsos:
        check(f"B582 rechaza {t!r} ({motivo})",
              not E0.RE_MARCA_INDICE_B582.match(t))

    # guarda posicional: el marcador fuera de la zona de título no clasifica
    p_tarde = pagina_de(["UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS",
                         "INDICE", "texto"])
    check(f"'INDICE' en línea 7 (> POS_MARCA_INDICE={E0.POS_MARCA_INDICE}) "
          "NO clasifica índice ni con el flag",
          E0.clasificar_paginas([p_tarde], marcadores_b582=True) == [E0.ROL_PORTADA])

    # la heurística de continuación NO se extiende (contraejemplo ri_dcpc p.3:
    # el encabezado 'SECCION 1 – …' aparece dos veces en la zona de título)
    p_idx = pagina_de(["TITULO", "B.C.R.A.", "INDICE",
                       "SECCION 1 - MARCO CONTABLE"], pagina=1)
    p_cuerpo = pagina_de([
        ("TITULO", 196.2), ("B.C.R.A.", 91.2),
        ("SECCION 1 – MARCO CONTABLE", 147.5),
        ("SECCION 1 – MARCO CONTABLE", 80.3),
        ("El presente documento es un compendio normativo complementario", 85.2),
    ], pagina=2)
    roles = E0.clasificar_paginas([p_idx, p_cuerpo], marcadores_b582=True)
    check("página tras el índice con dos líneas 'SECCION 1 – …' en zona sigue "
          "siendo cuerpo (la continuación de índice queda en la regla vigente)",
          roles == [E0.ROL_INDICE, E0.ROL_CUERPO], str(roles))


def test_regex_seccion_b582() -> None:
    print("== C. variantes de encabezado de sección y numeración no numérica")
    casos_ok = [
        ("SECCION 1 - MARCO CONTABLE", "1", "caps + arábigo + guion (ri_dcpc índice)"),
        ("SECCION 1 – MARCO CONTABLE", "1", "caps + arábigo + guion largo (ri_dcpc p.3)"),
        ("SECCIÓN I – INSTRUCCIONES GENERALES", "I", "caps + romano (ri_psp p.2)"),
        ("SECCIÓN III – APARTADO B: INFORMACIÓN ESTADÍSTICA", "III",
         "caps + romano compuesto (ri_psp p.5)"),
        ("Sección A – Introducción", "A", "letra + guion largo (reqcac p.3)"),
        ("Sección B - Controles Generales de Tecnología", "B",
         "letra + guion (reqcac p.4)"),
        ("Sección C. Controles a los Sistemas de Información", "C",
         "letra + punto (reqcac índice p.2)"),
        ("Sección I – Instrucciones generales", "I", "romano mixto (ri_psp índice)"),
    ]
    for t, num, motivo in casos_ok:
        m = E0._match_seccion_b582(t)
        check(f"B582 sección matchea {t[:44]!r} → {num} ({motivo})",
              m is not None and m[0] == num, str(m))
    casos_no = [
        ("Sección Punto Párrafo Com. Anexo Punto Párrafo",
         "sin separador tras el token (seguef p.19)"),
        ("la sección 4: requisitos", "remisión en prosa (guarda vigente)"),
        ("sección C – controles", "minúscula inicial"),
        ("Sección C establece los controles aplicables", "sin separador"),
        ("SECCION 1. MARCO CONTABLE", "caps con punto: forma no medida"),
        ("SECCIONES 2 – DE OTRA COSA", "palabra distinta"),
    ]
    for t, motivo in casos_no:
        check(f"B582 sección rechaza {t[:44]!r} ({motivo})",
              E0._match_seccion_b582(t) is None)

    # sucesión por familias de interpretación
    check("interpretaciones de 'C': letra 3 y NO romano (fuera del rango 1-39)",
          E0._interpretaciones_seccion("C") == {("letra", 3)})
    check("A→B→C avanza por letras (sin salto)",
          E0._es_sucesor_seccion("A", "B") and E0._es_sucesor_seccion("B", "C"))
    check("I→II avanza por romanos", E0._es_sucesor_seccion("I", "II"))
    check("IV→VI NO sucede (salto reportable, caso ri_psp)",
          not E0._es_sucesor_seccion("IV", "VI"))
    check("3→4 avanza por números", E0._es_sucesor_seccion("3", "4"))
    ordenes = [E0._orden_componente_seccion(x) for x in ("I", "C", "VI", "7")]
    check("orden de reporte: I→1, C→3, VI→6, '7'→7 (dígitos = orden histórico)",
          ordenes == [1, 3, 6, 7], str(ordenes))


def test_integracion_reqcac() -> None:
    print("== D. integración sintética con la anatomía de reqcac")
    paginas = paginas_reqcac_sintetico()
    roles = E0.clasificar_paginas(paginas, marcadores_b582=True)
    check("roles: índice vigente + 3 páginas de cuerpo",
          roles == [E0.ROL_INDICE] + [E0.ROL_CUERPO] * 3, str(roles))
    res = E0.parsear_cuerpo("tst", "tst.pdf", paginas, roles, marcadores_b582=True)
    res.reasignaciones_continuidad = E0.aplicar_continuidad_enumeracion(res)
    res.correccion_fronteras = E0.corregir_fronteras_intra_palabra(res)
    chunks = E0.construir_chunks(res)

    check("secciones A y B por variante, en orden y sin saltos",
          [s.numero for s in res.secciones] == ["A", "B"]
          and not res.saltos_numeracion,
          str([s.numero for s in res.secciones]))
    check("cola envuelta desactivada: el título de A queda 'Introducción' "
          "(la prosa inmediata NO se pega)",
          res.secciones[0].titulo == "Introducción",
          repr(res.secciones[0].titulo))
    check("banner de caja mixta descartado en las 3 páginas de cuerpo",
          sum(1 for d in res.accounting["detalle_descartes"]
              if d["texto"] == BANNER) == 3
          and sum(1 for d in res.accounting["detalle_descartes"]
                  if d["texto"] == BANNER2) == 3)
    check("la página de continuación fluye a la sección B abierta "
          "(aviso pagina_cuerpo_sin_seccion registrado)",
          any(a["tipo"] == "pagina_cuerpo_sin_seccion" and a["pagina"] == 4
              for a in res.avisos))
    check("punto '1.1.' bajo sección con letra: rechazado con registro "
          "(fuera_de_seccion_B), sigue como prosa",
          any(r["motivo"] == "fuera_de_seccion_B" for r in res.rechazos_header)
          and not res.secciones[1].hijos,
          str([r["motivo"] for r in res.rechazos_header]))
    check("unidades SA y SB emitidas",
          [c["id"] for c in chunks] == ["tst::SA", "tst::SB"],
          str([c["id"] for c in chunks]))
    check("cobertura exacta (cero pérdida) con banner y variantes activos",
          E0.verificar_cobertura(res)["cobertura_exacta"])
    check("el texto de SB contiene la prosa de la página de continuación",
          "procesamiento se realice" in chunks[1]["texto"])

    entradas = E0.parsear_indice(paginas, roles, marcadores_b582=True)
    secs_idx = [(e["numero"], e["titulo"]) for e in entradas if e["tipo"] == "seccion"]
    check("índice extendido: entradas de sección A y B por variante letra+punto",
          secs_idx == [("A", "Introducción"), ("B", "Controles Generales")],
          str(secs_idx))
    div = E0.divergencias_indice_cuerpo(res, entradas)
    check("divergencias con letras: sin crash y sin faltantes en ambas direcciones",
          div["anunciado_sin_cuerpo"] == [] and div["en_cuerpo_sin_anunciar"] == [])

    # salto de romanos reportado (caso medido ri_psp IV→VI)
    p_idx = pagina_de(["-INDICE-", "Sección IV – Una."], pagina=1)
    p_a = pagina_de([("SECCIÓN IV – APARTADO UNO", 236.1),
                     ("prosa de la sección cuatro con largo suficiente", 86.0)],
                    pagina=2)
    p_b = pagina_de([("SECCIÓN VI – APARTADO DOS", 236.1),
                     ("prosa de la sección seis con largo suficiente", 86.0)],
                    pagina=3)
    roles2 = E0.clasificar_paginas([p_idx, p_a, p_b], marcadores_b582=True)
    res2 = E0.parsear_cuerpo("tst", "tst.pdf", [p_idx, p_a, p_b], roles2,
                             marcadores_b582=True)
    check("IV→VI abre ambas secciones y reporta salto_seccion",
          [s.numero for s in res2.secciones] == ["IV", "VI"]
          and any(s["tipo"] == "salto_seccion" and s["de"] == "IV"
                  and s["a"] == "VI" for s in res2.saltos_numeracion),
          str(res2.saltos_numeracion))

    # banner repetido en solo 2 páginas: NO es banner (bajo MIN_PAGS_BANNER)
    dos = [pagina_de([("Encabezado mixto repetido dos veces", 146.2),
                      ("prosa de la página con largo pleno de oración", 90.0)],
                     pagina=pi) for pi in (1, 2)]
    check("línea mixta repetida en 2 páginas < MIN_PAGS_BANNER: no se marca banner",
          E0.detectar_banners_texto(dos) == set(), str(E0.detectar_banners_texto(dos)))


def test_healthcheck_escalera() -> None:
    print("== E. escalera del health-check sobre PDFs reales")
    prep = Path(E0.__file__).resolve().parents[3] / "experiment" / "escalado_prep" / "pdfs"
    r = health_check_to(prep / "reqcac.pdf")
    check("reqcac: modo 'marcadores', 3 unidades (SA/SB/SC), sin clave "
          "indice_b582 (sus roles ya eran los vigentes)",
          r["modo_lectura"] == "marcadores" and r["unidades_extraccion"] == 3
          and "indice_b582" not in r,
          f"modo={r['modo_lectura']} unid={r['unidades_extraccion']}")
    r = health_check_to(prep / "consyr.pdf")
    check("consyr: modo 'sin_raiz' con clave indice_b582 (variante 'Índice -' "
          "reclasificó la página) y unidades > 0",
          r["modo_lectura"] == "sin_raiz" and r.get("indice_b582") is True
          and r["unidades_extraccion"] > 0,
          f"modo={r['modo_lectura']} unid={r['unidades_extraccion']}")
    check("consyr: la página de índice quedó fuera del cuerpo",
          r["roles_pagina"].get("indice", 0) == 1, str(r["roles_pagina"]))
    subset = Path(E0.__file__).resolve().parents[3] / "experiment" / "subset"
    r = health_check_to(subset / "TO_proteccion_usuarios_servicios_financieros_actual.pdf")
    check("pro (subset dev): modo 'vigente', sano y sin claves nuevas",
          r["modo_lectura"] == "vigente" and r["veredicto"] == "sano"
          and "indice_b582" not in r,
          f"modo={r['modo_lectura']} veredicto={r['veredicto']}")


def main() -> int:
    test_garantia_estructural()
    test_regex_indice_b582()
    test_regex_seccion_b582()
    test_integracion_reqcac()
    test_healthcheck_escalera()
    total = len(RESULTADOS)
    ok = sum(1 for _, b, _ in RESULTADOS if b)
    print(f"\nSELFTEST B5.8.2: {ok}/{total} PASS")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
