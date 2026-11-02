"""Edición del selftest_e0.py de S0-4a-ter (casos q, r y s de las cinco reglas nuevas). Uso: python -B <este> <selftest_e0.py>"""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()
R = []
R.append(("""     guarda de columna dentro del sub-documento, la raíz mayor que MAX_RAIZ dentro del sub-documento (sdmax, de
     S0-4a-bis), 4a, 4b (con su guarda del verbo) y los apartados;
  s) un caso medido por regla, corriendo e0-r2 sobre siete TOs: sub-documento (ri_sef, nmcief, ri_ccna,
     ri_icpipsp, ri_cc: los cinco casos de prueba del FRENO S0-3), sdg3 (nmcief), sdmax (ri_ccna, ítems 31 a 40 del
     Anexo III; y ri_sef, cuyos códigos 101 a 126 no son sucesores), 4b (efemin), apartados (ri_ai), y la cobertura
     exacta.""",
          """     guarda de columna dentro del sub-documento, la raíz mayor que MAX_RAIZ dentro del sub-documento (sdmax, de
     S0-4a-bis), 4a, 4b (con su guarda del verbo) y los apartados; y las reglas de S0-4a-ter: el régimen de la página
     1 (sdr1), los apartados de letra con raíces numéricas (apl), el sub-documento de letra (sdl), la herencia de su
     rótulo (sdlh, con sdl y sin ella) y el rótulo «X.n.» con la letra vigente (sdla);
  s) un caso medido por regla, corriendo e0-r2 sobre ocho TOs: sub-documento (ri_sef, nmcief, ri_ccna,
     ri_icpipsp, ri_cc: los cinco casos de prueba del FRENO S0-3), sdg3 (nmcief), sdmax (ri_ccna, ítems 31 a 40 del
     Anexo III; y ri_sef, cuyos códigos 101 a 126 no son sucesores), sdr1 y apl (ri_oc), sdl, sdlh y sdla (ri_ccna,
     Anexo III), 4b (efemin), apartados (ri_ai), y la cobertura exacta."""))
R.append(("""Desde S0-4 cambian dos casos medidos de etapas anteriores: el de la regla 4 cuenta 93 unidades de ri_spi (4b retira
las intros de un renglón de B.1 y B.3) y el de 1a en nmcief lee nmcief::A2::3.2.1 (el punto es del Anexo II).
""", """Desde S0-4 cambian dos casos medidos de etapas anteriores: el de la regla 4 cuenta 93 unidades de ri_spi (4b retira
las intros de un renglón de B.1 y B.3) y el de 1a en nmcief lee nmcief::A2::3.2.1 (el punto es del Anexo II). Desde
S0-4a-ter, el caso medido de sdmax lee los ítems 31 a 40 en el sub-documento de letra (ri_ccna::D1A3L2::S31…).
"""))
R.append(("""    check("parsear_cuerpo: sub-documento, sdg3, sdmax y apartados apagados por default",
          p["subdocumentos"].default is None and p["g3_subdoc"].default is False
          and p["raiz_max_subdoc"].default is False and p["apartados_seccion"].default is False)""",
          """    check("parsear_cuerpo: sub-documento, sdg3, sdmax, las reglas de letra y apartados apagados por default",
          p["subdocumentos"].default is None and p["g3_subdoc"].default is False
          and p["raiz_max_subdoc"].default is False and p["apartados_seccion"].default is False
          and p["letra_corte"].default is False and p["letra_herencia"].default is False
          and p["letra_numero"].default is False)
    ls = inspect.signature(E0.limites_subdocumento).parameters
    check("limites_subdocumento: forma de letra y régimen de la página 1 apagados por default",
          ls["letras"].default is False and ls["sin_regimen_pagina_1"].default is False)"""))
R.append(("""          and correr_e0.REGLAS_S0_4 == frozenset({"sd", "sdg3", "sdmax", "4a", "4b", "ap"}))""",
          """          and correr_e0.REGLAS_S0_4 == frozenset({"sd", "sdg3", "sdmax", "sdr1", "apl", "sdl", "sdlh", "sdla", "4a",
                                                  "4b", "ap"})
          and correr_e0.TOS_SUBDOCUMENTO_R1_S0_4 == frozenset({"ri_oc"})
          and correr_e0.TOS_APARTADO_LETRA_S0_4 == frozenset({"ri_oc"})
          and correr_e0.TOS_LETRA_S0_4 == frozenset({"ri_ccna"}))"""))
R.append(("""TOS_S04 = ("ri_sef", "nmcief", "ri_ccna", "ri_icpipsp", "ri_cc", "ri_ai", "efemin")""",
          """TOS_S04 = ("ri_sef", "nmcief", "ri_ccna", "ri_icpipsp", "ri_cc", "ri_ai", "efemin", "ri_oc")"""))
SINT = '''    # S0-4a-ter, sdr1: el régimen de la página 1 es el del TO (y su encabezado corrido en las páginas siguientes)
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
          "A1::S3 «B. PRUEBAS SUSTANTIVAS»), sin otro cambio; con sdl, las del sub-documento de letra heredan su rótulo",
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
    # 4a: oración tomada como título (el caso del mecanismo 4)'''
R.append(("""    # 4a: oración tomada como título (el caso del mecanismo 4)""", SINT))
R.append(("""    check("sdmax, ri_ccna (Anexo III de la primera norma): los ítems 31 a 40 abren su raíz y la 30 ya no los lleva; "
          "159 unidades",
          all(f"ri_ccna::D1A3::S{k}" in ch["ri_ccna"] for k in range(31, 41))
          and txt("ri_ccna", "ri_ccna::D1A3::S31").startswith("31. Arqueo sorpresivo de los valores")
          and len(txt("ri_ccna", "ri_ccna::D1A3::S30")) == 350
          and "31. Arqueo" not in txt("ri_ccna", "ri_ccna::D1A3::S30")
          and len(ch["ri_ccna"]) == 159)""",
          """    check("sdmax, ri_ccna (Anexo III de la primera norma): los ítems 31 a 40 abren su raíz y la 30 ya no los "
          "lleva (desde S0-4a-ter, en el sub-documento de letra D1A3L2)",
          all(f"ri_ccna::D1A3L2::S{k}" in ch["ri_ccna"] for k in range(31, 41))
          and txt("ri_ccna", "ri_ccna::D1A3L2::S31").startswith("31. Arqueo sorpresivo de los valores")
          and len(txt("ri_ccna", "ri_ccna::D1A3L2::S30")) == 350
          and "31. Arqueo" not in txt("ri_ccna", "ri_ccna::D1A3L2::S30"))
    l2 = [i for i in ch["ri_ccna"] if i.startswith("ri_ccna::D1A3L2::") and i != "ri_ccna::D1A3L2::S0"]
    check("sdl, sdlh y sdla, ri_ccna (Anexo III): A.3, B.1 y B.2 son unidades propias; el ítem 2 de A.2 queda "
          "solo; las 49 unidades de la lista B heredan «B. PRUEBAS SUSTANTIVAS»; 164 unidades",
          txt("ri_ccna", "ri_ccna::D1A3L1::SA.3").startswith("A.3. El relevamiento y evaluación")
          and txt("ri_ccna", "ri_ccna::D1A3L2::S1").startswith("1. Arqueo sorpresivo de las existencias")
          and txt("ri_ccna", "ri_ccna::D1A3L2::S2").startswith("2. Obtención de confirmaciones")
          and len(txt("ri_ccna", "ri_ccna::D1A3L1::S2")) == 667 and len(l2) == 49
          and all(any(h["texto"] == "B. PRUEBAS SUSTANTIVAS" for h in ch["ri_ccna"][i]["herencia"]) for i in l2)
          and len(ch["ri_ccna"]) == 164, str(len(l2)))
    oc = ch["ri_oc"]
    check("sdr1, ri_oc: los Anexos I y II son sub-documentos sin el prefijo del régimen de la página 1",
          bool(txt("ri_oc", "ri_oc::A1::S0")) and all(f"ri_oc::A2::S{k}" in oc for k in range(1, 7))
          and not any("R10" in i for i in oc))
    check("apl, ri_oc: «APARTADO B» y «APARTADO C» abren sus raíces, B.1.1 a B.3.4 y C.1 a C.11 son puntos, y "
          "3.51 queda con su texto (p. 15)",
          all(f"ri_oc::B.1.{k}" in oc for k in range(1, 29)) and "ri_oc::B.3.4" in oc and "ri_oc::C.11" in oc
          and oc["ri_oc::3.51"]["paginas"] == [15] and "APARTADO B" not in txt("ri_oc", "ri_oc::3.51")
          and [h["unidad_origen"] for h in oc["ri_oc::B.1.1"]["herencia"]] == ["SB", "B.1"] and len(oc) == 184)"""))
for a, b in R:
    assert s.count(a) == 1, a[:70]
    s = s.replace(a, b)
open(p, "w", encoding="utf-8").write(s)
print([k + 1 for k, l in enumerate(s.splitlines()) if len(l) > 120])
