"""Selftest de la unidad B5.8.1: modo de lectura sin raíz de sección
(módulo nuevo; NO toca selftest_e0.py ni selftest_b52.py).

Cubre, con los casos MEDIDOS del censo B5.8.0 como fixtures:

  A. GARANTÍA ESTRUCTURAL de no-cambio: el flag `modo_sin_raiz` es False por
     default; con roles vigentes la compuerta sigue cerrada para una familia
     a sintética (0 secciones, 0 unidades); la serialización vigente no
     emite ninguna clave nueva; el health-check de un TO del subset de
     desarrollo (pro) declara modo 'vigente' y no cambia de veredicto.
  B. Roles derivados del modo: familia a (todo portada → cuerpo, con
     historial/tabla intactos), familia c (roles vigentes respetados), y la
     compuerta de páginas de registro (fichas de ri2_pm p.50 y códigos de
     cuenta largos medidos; la mención aislada 'Incluye…' en prosa no
     vuelca la página).
  C. Raíces EXPLÍCITAS con sus guardas: el banner repetido de ri_bdp se
     descarta y la espina '1.'/'2.' abre raíces; monotonía (los ítems que
     reinician numeración quedan rechazados); forma de título (la
     referencia '1. de las normas…' no abre raíz); columna profunda
     rechazada; saltos aceptados y reportados; raíz genuina en mayúsculas
     sostenidas ('1. DATOS GENERALES' de ri_ii_31_12_19) preservada del
     descarte de encabezado.
  D. Raíces IMPLÍCITAS: arranque en profundidad 2 (ri_niif '2.1.
     Disposiciones generales…') y transición 2.x→3.x; la referencia envuelta
     de ri_dsf p.1 ('2.1.4. de las normas…') NO abre nada; profundidad 2
     que retrocede no abre; una fecha '1.1.2019.' no abre.
  E. Preámbulo sintético: el contenido previo a la primera raíz materializa
     como unidad S0 con cobertura exacta; si la primera línea abre raíz no
     queda preámbulo vacío.
  F. Integración con healthcheck_e0: un TO objetivo real chico (ri_ieccm)
     se desbloquea sano en modo 'sin_raiz'; ri_acsf (sin espina utilizable,
     vía B5.8.3) NO rinde y su señal paginas_sin_seccion dispara — el
     preámbulo no cuenta como sección efectiva.

Uso: python3 selftest_b581.py  (sin argumentos, USD 0, sin LLM).
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


def correr_modo(paginas: list[list[E0.Linea]]) -> tuple[E0.ResultadoParseo, list[dict]]:
    """Flujo de activación completo del modo (mismo orden que healthcheck):
    roles vigentes → roles derivados → parseo modo_sin_raiz → chunks."""
    roles = E0.roles_para_modo_sin_raiz(paginas, E0.clasificar_paginas(paginas))
    res = E0.parsear_cuerpo("tst", "tst.pdf", paginas, roles, modo_sin_raiz=True)
    res.reasignaciones_continuidad = E0.aplicar_continuidad_enumeracion(res)
    res.correccion_fronteras = E0.corregir_fronteras_intra_palabra(res)
    return res, E0.construir_chunks(res)


# fixture de familia a (censo: sin página de índice, espina de puntos):
# banner en mayúsculas repetido en la zona de título de las 3 páginas
# (verbatim ri_bdp) + raíces de espina en columna 60 con texto en 95
def paginas_familia_a() -> list[list[E0.Linea]]:
    def pag(pagina, cuerpo):
        base = [("17. BASE DE DATOS PADRÓN (R.I. – B.P.)", 139.4),
                ("B.C.R.A.", 83.0)]
        return pagina_de(base + cuerpo, pagina=pagina)
    p1 = pag(1, [
        "1. Se informará toda persona física o jurídica con la que se opere",
        ("continuación del punto uno con largo de prosa plena para el ancla", 95.0),
        "2. La información se remitirá por primera vez en forma completa",
    ])
    p2 = pag(2, [
        "3. Posteriormente, con frecuencia mensual se informarán las altas",
        ("continuación del punto tres con largo de prosa plena para el ancla", 95.0),
    ])
    p3 = pag(3, [
        ("texto final de cierre con largo de prosa plena para anclar al nodo", 95.0),
    ])
    return [p1, p2, p3]


# ------------------------------------------------------------------- tests

def test_garantia_estructural() -> None:
    print("== A. garantía estructural de no-cambio")
    firma = inspect.signature(E0.parsear_cuerpo)
    check("parsear_cuerpo: modo_sin_raiz default False",
          firma.parameters["modo_sin_raiz"].default is False)

    paginas = paginas_familia_a()
    roles_v = E0.clasificar_paginas(paginas)
    check("familia a sintética: roles vigentes todo portada (compuerta cerrada)",
          set(roles_v) == {E0.ROL_PORTADA}, str(set(roles_v)))
    res_v = E0.parsear_cuerpo("tst", "tst.pdf", paginas, roles_v)
    chunks_v = E0.construir_chunks(res_v)
    check("camino vigente sobre familia a: 0 secciones y 0 unidades (sin cambio)",
          not res_v.secciones and not chunks_v,
          f"secc={len(res_v.secciones)} chunks={len(chunks_v)}")
    ser = json.dumps(E0.serializar_estructura(res_v), ensure_ascii=False)
    check("serialización vigente sin claves nuevas (ni modo_lectura ni sintetica)",
          "modo_lectura" not in ser and "sintetica" not in ser)

    # un TO digerible sintético NO pasa por el modo nuevo: produce unidades
    # por el camino vigente y el predicado de activación (cero unidades) es falso
    p_idx = pagina_de(["-Índice-", "Sección 1. Una."], pagina=1)
    p_cuerpo = [
        linea("Sección 1: Título", pagina=2, top=30.0, x0=60.0),
        linea("1.1. Primer punto con su texto en la línea del label", pagina=2,
              top=60.0, x0=60.0),
        linea("1.2. Segundo punto con su texto en la línea del label", pagina=2,
              top=90.0, x0=60.0),
    ]
    roles_d = E0.clasificar_paginas([p_idx, p_cuerpo])
    res_d = E0.parsear_cuerpo("dig", "dig.pdf", [p_idx, p_cuerpo], roles_d)
    chunks_d = E0.construir_chunks(res_d)
    check("digerible sintético: unidades por el camino vigente (no entra al modo)",
          len(chunks_d) > 0 and res_d.modo_lectura == "vigente",
          f"chunks={len(chunks_d)}")


def test_roles_derivados() -> None:
    print("== B. roles derivados del modo")
    p_hist = pagina_de(["Últimas comunicaciones incorporadas historial de la norma",
                        "texto"], pagina=2)
    paginas = [paginas_familia_a()[0], p_hist]
    roles = E0.roles_para_modo_sin_raiz(paginas, E0.clasificar_paginas(paginas))
    check("familia a: portada pasa a cuerpo, historial intacto",
          roles == [E0.ROL_CUERPO, E0.ROL_HISTORIAL], str(roles))

    roles_c = [E0.ROL_PORTADA, E0.ROL_INDICE, E0.ROL_CUERPO]
    p_portada = pagina_de(["CERTIFICADOS DE DEPÓSITO"], pagina=1)
    p_idx = pagina_de(["Índice", "Sección 1. Alta."], pagina=2)
    p_c = pagina_de(["1. Alta del CEDIN."], pagina=3)
    derivados = E0.roles_para_modo_sin_raiz([p_portada, p_idx, p_c], roles_c)
    check("familia c: con cuerpo vigente los roles se respetan (portada NO se abre)",
          derivados == roles_c, str(derivados))

    # compuerta de registro: ficha de ri2_pm p.50 (verbatims medidos)
    p_ficha = pagina_de([
        ("CAPITULO ACTIVO", 76.6), ("RUBRO DISPONIBILIDADES", 79.1),
        ("SUB-RUBRO Código", 79.1), ("RESIDENCIA EN EL PAÍS", 79.1),
        ("MONEDA EXTRANJERA 101011ZZZ0000001", 79.1),
        ("OTROS ATRIBUTOS", 79.1),
        ("IMPUTACION Efectivo en caja - Operaciones de turismo", 79.1),
        ("Incluye el equivalente en pesos de los billetes y las monedas", 76.6),
        ("agencias de cambio radicadas en el país.", 76.6),
    ], pagina=1)
    r = E0.marcar_paginas_registro([p_ficha], [E0.ROL_CUERPO])
    check("página de ficha (ri2_pm p.50): rol ficha_registro",
          r == [E0.ROL_REGISTRO], str(r))

    p_codigos = pagina_de([
        ("PLAN DE CUENTAS", 141.6),
        ("Fondos Comunes de inversión - Con cotización", 147.4),
        ("102011ARS0000101", 462.2),
        ("Títulos públicos - Con cotización 102011ARS0100101", 147.4),
        ("Títulos públicos - Sin cotización", 147.4),
        ("102011ARS0100201", 462.2),
    ], pagina=1)
    r = E0.marcar_paginas_registro([p_codigos], [E0.ROL_CUERPO])
    check("página de plan de cuentas (códigos largos de ri2_pm p.5): ficha_registro",
          r == [E0.ROL_REGISTRO], str(r))

    p_prosa = pagina_de(
        ["1. Alcance de la norma sobre depósitos de ahorro",
         "texto de prosa plena con largo suficiente para no ser título corto",
         "Incluye a las cajas de crédito cooperativas en su alcance general.",
         "más prosa de desarrollo del punto con largo de oración plena",
         "y todavía más prosa para que la densidad quede muy por debajo",
         "del umbral de registro que vuelca una página entera de fichas"],
        pagina=1)
    r = E0.marcar_paginas_registro([p_prosa], [E0.ROL_CUERPO])
    check("mención aislada 'Incluye…' en prosa: la página sigue siendo cuerpo",
          r == [E0.ROL_CUERPO], str(r))


def test_raices_explicitas() -> None:
    print("== C. raíces explícitas y sus guardas")
    res, chunks = correr_modo(paginas_familia_a())
    nums = [s.numero for s in res.secciones]
    check("ri_bdp sintético: raíces 1-3 de la espina (banner no abre raíz)",
          nums == ["1", "2", "3"], str(nums))
    check("banner en zona de título descartado como encabezado (accounting)",
          sum(1 for d in res.accounting["detalle_descartes"]
              if d["texto"].startswith("17. BASE")) == 3,
          str(res.accounting["lineas_descartadas_encabezado_pie"]))
    cob = E0.verificar_cobertura(res)
    check("cobertura exacta (cero huérfanas) con el modo activo",
          cob["cobertura_exacta"], str(cob))
    ids = [c["id"] for c in chunks]
    check("unidades S1-S3 emitidas", ids == ["tst::S1", "tst::S2", "tst::S3"], str(ids))
    u1 = next(c for c in chunks if c["id"] == "tst::S1")
    check("raíz explícita: el texto propio arranca en el label verbatim "
          "(sin encabezado 'Sección' fabricado)",
          u1["texto"].startswith("1. Se informará") and "Sección" not in u1["texto"],
          u1["texto"][:60])

    # monotonía: ítem que reinicia numeración no abre raíz (caso ri_cr)
    p = pagina_de([
        "5. Datos a solicitar sobre los reclamos del período informado",
        ("texto del punto cinco con largo de prosa plena para fijar columna", 95.0),
        ("1. Stock de casos al inicio del período informado", 60.0),
        ("2. Casos ingresados durante el período informado", 60.0),
    ])
    res, chunks = correr_modo([p])
    check("monotonía G2: '1.'/'2.' tras la raíz 5 no abren raíz (reinicio de lista)",
          [s.numero for s in res.secciones] == ["5"]
          and sum(1 for r in res.rechazos_header
                  if r["motivo"].startswith("raiz_") and "no_sucede" in r["motivo"]) == 2,
          str([r["motivo"] for r in res.rechazos_header]))
    check("los ítems rechazados siguen como prosa de la raíz abierta (cero pérdida)",
          E0.verificar_cobertura(res)["cobertura_exacta"])

    # forma de título: referencia envuelta en minúscula no abre raíz
    p = pagina_de([
        "1. Normas generales para la integración del régimen informativo",
        ("texto del punto uno con largo de prosa plena para fijar su columna", 95.0),
        ("2. de las normas sobre financiaciones vigentes a cada cierre", 60.0),
    ])
    res, _ = correr_modo([p])
    check("guarda G1: '2. de las normas…' (minúscula) no abre raíz",
          [s.numero for s in res.secciones] == ["1"]
          and any(r["motivo"] == "raiz_sin_forma_de_titulo"
                  for r in res.rechazos_header),
          str([r["motivo"] for r in res.rechazos_header]))

    # columna profunda: enumeración interna a la derecha del margen de raíz
    p = pagina_de([
        "1. Requisitos de la solicitud presentada ante la autoridad",
        ("texto del punto uno con largo de prosa plena para fijar columna", 95.0),
        ("2. Nombre de la entidad solicitante del trámite en curso", 130.0),
    ])
    res, _ = correr_modo([p])
    check("guarda G3: candidato a raíz en columna profunda rechazado",
          [s.numero for s in res.secciones] == ["1"]
          and any(r["motivo"].startswith("raiz_en_columna_profunda")
                  for r in res.rechazos_header),
          str([r["motivo"] for r in res.rechazos_header]))

    # saltos hacia adelante: se aceptan y se reportan (caso seggar 3→6)
    p = pagina_de([
        "3. Depósitos comprendidos en el régimen de garantía vigente",
        ("texto del punto tres con largo de prosa plena para anclar acá", 95.0),
        ("6. Exclusiones del régimen por disposición de la autoridad", 60.0),
    ])
    res, _ = correr_modo([p])
    check("salto de raíz 3→6 aceptado y reportado como salto_raiz",
          [s.numero for s in res.secciones] == ["3", "6"]
          and any(s.get("tipo") == "salto_raiz" for s in res.saltos_numeracion),
          str(res.saltos_numeracion))

    # raíz genuina en mayúsculas sostenidas (ri_ii_31_12_19), única, se preserva
    paginas = [pagina_de([
        ("20. INFORMACION INSTITUCIONAL DE ENTIDADES", 102.8),
        ("B.C.R.A.", 83.0),
        ("1. DATOS GENERALES", 60.0),
        ("texto del punto con largo de prosa plena para anclar al nodo", 95.0),
    ], pagina=pi) if pi == 1 else pagina_de([
        ("20. INFORMACION INSTITUCIONAL DE ENTIDADES", 102.8),
        ("B.C.R.A.", 83.0),
        (f"{pi}. OTRO PUNTO EN MAYUSCULAS SOSTENIDAS", 60.0),
        ("texto del punto con largo de prosa plena para anclar al nodo", 95.0),
    ], pagina=pi) for pi in (1, 2, 3)]
    res, _ = correr_modo(paginas)
    check("raíz única en mayúsculas ('1. DATOS GENERALES') preservada del descarte; "
          "banner repetido no",
          [s.numero for s in res.secciones] == ["1", "2", "3"]
          and not any(d["texto"].startswith("1. DATOS")
                      for d in res.accounting["detalle_descartes"]),
          str([s.numero for s in res.secciones]))


def test_raices_implicitas() -> None:
    print("== D. raíces implícitas")
    # arranque medido de ri_niif: espina que empieza en profundidad 2
    p = pagina_de([
        "2.1. Disposiciones generales respecto de los estados financieros",
        ("texto del punto con largo de prosa plena para fijar la columna", 95.0),
        ("2.2. Otras disposiciones sobre los estados financieros anuales", 60.0),
        ("3.1. Régimen de presentación ante la superintendencia del área", 60.0),
    ])
    res, chunks = correr_modo([p])
    secc = [(s.numero, s.titulo, s.linea_label is None) for s in res.secciones]
    check("arranque en profundidad 2: raíz implícita '2' + puntos 2.1/2.2",
          secc[0] == ("2", "", True)
          and [h.numero for h in res.secciones[0].hijos] == ["2.1", "2.2"],
          str(secc))
    check("transición 2.x→3.x: raíz implícita '3' + punto 3.1",
          len(res.secciones) == 2 and secc[1][0] == "3"
          and [h.numero for h in res.secciones[1].hijos] == ["3.1"], str(secc))
    h21 = next(c for c in chunks if c["id"] == "tst::2.1")
    check("herencia del punto 2.1: encabezado de raíz implícita = '2.' "
          "(sin 'Sección' fabricada)",
          h21["herencia"][0]["texto"] == "2." and h21["herencia"][0]["unidad_origen"] == "S2",
          str(h21["herencia"][:1]))

    # contraejemplo medido (ri_dsf p.1): referencia envuelta de profundidad 3
    p = pagina_de([
        "Los conceptos comprendidos se computarán según lo previsto en el punto",
        ("2.1.4. de las normas sobre “Cesión de cartera de créditos”", 60.0),
        "y las demás disposiciones complementarias sobre la materia vigente",
    ])
    res, chunks = correr_modo([p])
    check("'2.1.4. de las normas…' (ri_dsf p.1) NO abre raíz ni punto: todo al preámbulo",
          [s.numero for s in res.secciones] == ["0"] and not res.secciones[0].hijos
          and E0.verificar_cobertura(res)["cobertura_exacta"],
          str([s.numero for s in res.secciones]))
    check("la referencia quedó rechazada con registro (nada en silencio)",
          any(r["texto"].startswith("2.1.4.") for r in res.rechazos_header),
          str([r["motivo"] for r in res.rechazos_header]))

    # retroceso en profundidad 2 no abre raíz
    p = pagina_de([
        "3.1. Primer punto del capítulo tres con su título en la línea",
        ("texto del punto con largo de prosa plena para fijar la columna", 95.0),
        ("2.1. Referencia retrospectiva con forma de título en la línea", 60.0),
    ])
    res, _ = correr_modo([p])
    check("profundidad 2 que retrocede (3.x→2.x) no abre raíz implícita",
          [s.numero for s in res.secciones] == ["3"]
          and any(r["motivo"].startswith("fuera_de_seccion")
                  for r in res.rechazos_header),
          str([r["motivo"] for r in res.rechazos_header]))

    # una fecha con puntos no abre nada
    p = pagina_de([
        "1. Información institucional requerida a las entidades financieras",
        ("texto del punto uno con largo de prosa plena para fijar columna", 95.0),
        ("1.1.2019. Desde esa fecha rige la versión vigente del régimen", 60.0),
    ])
    res, _ = correr_modo([p])
    check("fecha '1.1.2019.' no abre raíz ni punto",
          [s.numero for s in res.secciones] == ["1"] and not res.secciones[0].hijos,
          str([s.numero for s in res.secciones]))


def test_preambulo() -> None:
    print("== E. preámbulo sintético")
    p = pagina_de([
        "El presente régimen informativo alcanza a las entidades financieras",
        "comprendidas en la ley y sus disposiciones complementarias vigentes",
        ("1. Sujetos alcanzados por el régimen informativo del período", 60.0),
        ("texto del punto uno con largo de prosa plena para anclar acá", 95.0),
    ])
    res, chunks = correr_modo([p])
    check("prosa previa a la primera raíz: unidad S0 'Preámbulo'",
          [c["id"] for c in chunks] == ["tst::S0", "tst::S1"]
          and chunks[0]["titulo"] == "Preámbulo",
          str([c["id"] for c in chunks]))
    check("S0 conserva la prosa y la cobertura es exacta",
          "El presente régimen" in chunks[0]["texto"]
          and E0.verificar_cobertura(res)["cobertura_exacta"])

    p = pagina_de([
        "1. Sujetos alcanzados por el régimen informativo del período",
        ("texto del punto uno con largo de prosa plena para anclar acá", 95.0),
    ])
    res, chunks = correr_modo([p])
    check("primera línea abre raíz: no queda preámbulo vacío",
          [c["id"] for c in chunks] == ["tst::S1"], str([c["id"] for c in chunks]))


def test_healthcheck_integracion() -> None:
    print("== F. integración con healthcheck_e0 (PDFs reales)")
    prep = Path(E0.__file__).resolve().parents[3] / "experiment" / "escalado_prep" / "pdfs"
    r = health_check_to(prep / "ri_ieccm.pdf")
    check("ri_ieccm (objetivo, 1 pág): modo sin_raiz, unidades > 0, sano",
          r["modo_lectura"] == "sin_raiz" and r["unidades_extraccion"] > 0
          and r["veredicto"] == "sano",
          f"unid={r['unidades_extraccion']} veredicto={r['veredicto']}")
    r = health_check_to(prep / "ri_acsf.pdf")
    check("ri_acsf (sin espina, vía B5.8.3): el modo NO rinde y la señal dispara",
          r["modo_lectura"] == "sin_raiz"
          and "paginas_sin_seccion" in r["veredicto"]
          and r["senales"]["paginas_sin_seccion"]["secciones_parseadas"] == 0,
          f"veredicto={r['veredicto']}")
    subset = Path(E0.__file__).resolve().parents[3] / "experiment" / "subset"
    r = health_check_to(subset / "TO_proteccion_usuarios_servicios_financieros_actual.pdf")
    check("pro (subset dev): modo 'vigente' y veredicto sano (activación jamás entra)",
          r["modo_lectura"] == "vigente" and r["veredicto"] == "sano",
          f"modo={r['modo_lectura']} veredicto={r['veredicto']}")


def main() -> int:
    test_garantia_estructural()
    test_roles_derivados()
    test_raices_explicitas()
    test_raices_implicitas()
    test_preambulo()
    test_healthcheck_integracion()
    total = len(RESULTADOS)
    ok = sum(1 for _, b, _ in RESULTADOS if b)
    print(f"\nSELFTEST B5.8.1: {ok}/{total} PASS")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
