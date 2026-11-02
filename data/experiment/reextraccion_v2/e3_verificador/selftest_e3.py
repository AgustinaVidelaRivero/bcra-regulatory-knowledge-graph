"""
selftest_e3.py — Selftest OFFLINE de E3 (T4). Cero llamadas a APIs de LLM:
los únicos clientes que se instancian son StubClienteE3 y StubClienteE1.

Verifica:
  A. Prefijo E3 estable e idéntico entre unidades (condición del caching):
     system + tools + tool_choice byte-idénticos en las 87 unidades aceptadas,
     breakpoint ephemeral en el último bloque, nada variable antes del
     breakpoint.
  B. CONTEXTO FRESCO verificable (principio 2.c): el request de E3 no
     contiene NADA del prompt del extractor — ni sus instrucciones, ni su
     tool, ni su system; el mensaje lleva solo fuente + extracción como datos.
  C. Determinismo: mismos datos → mismo request byte a byte.
  D. Calibradores: 4, resueltos, con citas que verifican contra su fuente
     (incluida la normalización de guiones de corte de línea del PDF) y el
     completo_ok igual a la extracción real de fase B.
  E. Capa determinística de citas: positivo con guiones, negativo con cita
     fabricada, insensible a espacios/saltos.
  F. Flujo del mini-ratchet con fixtures (stub): amputación detectada →
     reintento con prefijo E1 byte-idéntico y feedback después del breakpoint
     → re-validación → re-verificación → aceptado; completa pasa directo;
     tope 1 respetado → cola humana con flag y TODO persistidos; veredicto
     incoherente y cita fabricada manejados.
  G. Keys de caché local (llm_cache puro, sin DB) y namespace propio.
  H. Estimación reproducible.
  L. U-PROMPT-R2, P3b-2 (solo con la forma r2): veredicto como texto leído en código con su marca (j), reintento
     con menos elementos marcado (k4), aviso de la nota en el reintento y marca de la copia de la nota (defensas 1
     y 2), el `todo` r2 de la cola humana y la NOTA de las omisiones declaradas (i); con los perfiles existentes,
     todo igual.
  M. U-PROMPT-R2, P3c-2: las NOTAS de los puntos a y b son las del borrador aprobado, y el candado del mensaje de E3
     (F23) compara el de su fixture y frena ante un espacio más en cualquiera de las dos NOTAS; el prefijo de E3 y su
     candado no cambian. U-E3-LISTAS: la fixture suma tres ítems de lista (19 casos) y la NOTA del ítem también frena.
  N. U-E3-LISTAS, O2 (solo con la forma r2): el bloque que abre la lista entra al fuente y a las citas de un ítem
     con intro, el de un ítem con encabezado no cambia, los fragmentos contiguos de D2 entran, un mini-chunk y una
     unidad r1 no cambian, la NOTA del ítem va con su variante, y la cita al bloque verifica en el ratchet (D1).

Uso:  python3 selftest_e3.py
"""

from __future__ import annotations

import json
import shutil
import sys

import comun_e3
from comun_e3 import (BASE, cargar_chunks, cita_en_fuente, fuente_integro,
                      normalizar_para_cita, pares_calibracion, render_extraccion)
import prompt_e3
import cliente_e3
import ratchet_e3

import prompt_e1
import cliente_e1
import llm_cache as lc

OK, FAIL = 0, 0


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok  {nombre}")
    else:
        FAIL += 1
        print(f" FAIL {nombre}  {detalle}")


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    pares = pares_calibracion()
    chunks_pro = {c["id"]: c for c in cargar_chunks(("pro",))}
    print(f"pares (chunk aceptado, validación E1) cargados: {len(pares)}")

    # ---------------- A. Prefijo estable e idéntico entre unidades --------- #
    print("\n[A] prefijo estable")
    check("la calibración E3 son 87 unidades aceptadas (fan-in E2: 88 − 1)",
          len(pares) == 87, f"hay {len(pares)}")
    ref = None
    prefijo_identico = True
    texto_en_prefijo = False
    for chunk, val in pares:
        kw = prompt_e3.build_request_kwargs(chunk, val, model="MODELO_FASE_B")
        pref = canon({"system": kw["system"], "tools": kw["tools"],
                      "tool_choice": kw["tool_choice"]})
        if ref is None:
            ref = pref
        elif pref != ref:
            prefijo_identico = False
            break
        if chunk["texto"][:60] in pref and chunk["id"] not in (
                "ric::7.1", "pro::1.1.2.5", "cla::6.5.1.1"):  # los calibradores sí viven en el prefijo
            texto_en_prefijo = True
            break
    check("prefijo (system+tools+tool_choice) idéntico en las 87 unidades",
          prefijo_identico and ref is not None)
    check("nada del texto variable (fuera de calibradores) aparece en el prefijo",
          not texto_en_prefijo)

    ch0, val0 = pares[0]
    kw0 = prompt_e3.build_request_kwargs(ch0, val0, model="MODELO_FASE_B")
    sistema = kw0["system"]
    check("system es lista de bloques (jamás string plano)", isinstance(sistema, list))
    check("breakpoint cache_control ephemeral en el ÚLTIMO bloque del system",
          isinstance(sistema, list) and sistema
          and sistema[-1].get("cache_control") == {"type": "ephemeral"})
    check("un solo bloque de system (todo lo estable antes del breakpoint)",
          isinstance(sistema, list) and len(sistema) == 1)
    check("lo variable va en messages, después del breakpoint",
          ch0["texto"][:60] in kw0["messages"][0]["content"])
    check("tool_choice fuerza la tool del verificador",
          kw0["tool_choice"] == {"type": "tool", "name": prompt_e3.NOMBRE_TOOL})

    # ---------------- B. Contexto fresco (principio 2.c) ------------------- #
    print("\n[B] contexto fresco: nada del extractor en el request de E3")
    req_canon = canon(kw0)
    centinelas_e1 = [
        "Sos un extractor de tripletas",          # apertura del system E1
        "REGLAS NO NEGOCIABLES",                  # sección del system E1
        "extraer_kg_e1",                          # tool del extractor
        "ANTI-FUSIÓN",                            # regla 5 del system E1
        "Puntos admitidos para `punto`",          # mensaje de usuario E1
    ]
    for c in centinelas_e1:
        check(f"centinela E1 ausente del request E3: «{c[:40]}»", c not in req_canon)
    msg = kw0["messages"][0]["content"]
    check("el mensaje E3 contiene el fuente íntegro de la unidad (datos)",
          fuente_integro(ch0) in msg)
    check("el mensaje E3 contiene la extracción renderizada (datos)",
          render_extraccion(val0) in msg)

    # ---------------- C. Determinismo -------------------------------------- #
    print("\n[C] determinismo del prompt")
    muestra = pares[::17]
    det = all(
        canon(prompt_e3.build_request_kwargs(c, v, model="M")) ==
        canon(prompt_e3.build_request_kwargs(c, v, model="M"))
        for c, v in muestra
    )
    check(f"mismos datos → mismo request byte a byte ({len(muestra)} unidades)", det)
    c0 = json.loads(json.dumps(ch0))
    v0 = json.loads(json.dumps(val0))
    check("datos re-parseados desde JSON → request idéntico",
          canon(prompt_e3.build_request_kwargs(c0, v0, model="M")) ==
          canon(prompt_e3.build_request_kwargs(ch0, val0, model="M")))

    # tratamiento de flaggeados (ningún chunk de pro está flaggeado: se
    # ejercita con un chunk flaggeado real de otro TO y validación mínima)
    ch_flag = {c["id"]: c for c in cargar_chunks(("ric",))}["ric::3.1.2"]
    val_min = {"entidades": [], "relaciones": [], "omisiones_no_prosa": []}
    check("chunk flaggeado por E0 → el mensaje E3 instruye evaluar "
          "contenido_tabular_no_declarado",
          "contenido_tabular_no_declarado" in prompt_e3.build_user_message(ch_flag, val_min)
          and "contenido_tabular_no_declarado" not in prompt_e3.build_user_message(ch0, val0))

    # ---------------- D. Calibradores --------------------------------------- #
    print("\n[D] calibradores resueltos")
    cals = prompt_e3.CALIBRADORES
    check("hay exactamente 4 calibradores", len(cals) == 4)
    check("tipos cubiertos: calificador_despojado, excepcion_ausente, "
          "enumeracion_incompleta y completo_ok",
          [c["veredicto"]["veredicto"] for c in cals] ==
          ["faltantes_detectados"] * 3 + ["completo_ok"]
          and [f["tipo"] for c in cals[:3] for f in c["veredicto"]["faltantes"]] ==
          ["calificador_despojado", "calificador_despojado",
           "excepcion_ausente", "enumeracion_incompleta"])
    todos_chunks = {c["id"]: c for c in cargar_chunks(("cla", "pro", "ric"))}
    # Enmienda 01: el fuente del hijo ya no porta la prosa heredada, así que
    # las citas de los calibradores (congelados con el render de la
    # calibración sellada, prosa heredada incluida) se verifican contra el
    # PROPIO fuente del calibrador — que es lo que el verificador ve en el
    # prefijo — con la misma normalización de la capa de citas.
    citas_ok = all(
        normalizar_para_cita(f["cita_textual_del_fuente"])
        in normalizar_para_cita(cal["fuente"])
        for cal in cals for f in cal["veredicto"]["faltantes"]
    )
    check("toda cita de calibrador verifica contra el fuente del calibrador "
          "(render congelado, normalización de la capa de citas)", citas_ok)
    cal3 = cals[2]
    check("la cita del calibrador 3 cruza un guion de corte de línea del PDF "
          "('si-\\nguientes') y aun así verifica",
          "si-\nguientes" in cal3["fuente"]
          and "siguientes" in cal3["veredicto"]["faltantes"][0]["cita_textual_del_fuente"]
          and normalizar_para_cita(
              cal3["veredicto"]["faltantes"][0]["cita_textual_del_fuente"])
          in normalizar_para_cita(cal3["fuente"]))
    import calibradores_e3 as _cal_mod
    from comun_e3 import cargar_extracciones_faseB
    val_real = cargar_extracciones_faseB()["pro::1.1.2.5"]["validacion"]
    cal4 = cals[3]
    check("el calibrador completo_ok ES la extracción real de fase B (byte a byte)",
          canon(cal4["extraccion"]["entidades"]) == canon(val_real["entidades"])
          and canon(cal4["extraccion"]["relaciones"]) == canon(val_real["relaciones"]))
    check("el par mínimo CAL-2/CAL-4 comparte fuente y difiere en extracción",
          cals[1]["fuente"] == cal4["fuente"]
          and canon(cals[1]["extraccion"]) != canon(cal4["extraccion"]))
    cal1 = cals[0]
    extr1_desc = next(e for e in cal1["extraccion"]["entidades"]
                      if e["local_id"] == "e3")["properties"]["descripcion"]
    check("CAL-1 reproduce la amputación C7: la extracción NO contiene los dos "
          "calificadores y el fuente SÍ",
          "Responsabilidad Patrimonial Computable informada" not in extr1_desc
          and "calculada según datos del mes n" not in extr1_desc
          and normalizar_para_cita("Responsabilidad Patrimonial Computable informada en el mes n")
          in normalizar_para_cita(cal1["fuente"]))

    # ---------------- E. Capa determinística de citas ----------------------- #
    print("\n[E] verificación determinística de citas")
    ch_ric = todos_chunks["ric::7.1"]
    check("positivo: cita que cruza guiones del PDF verifica "
          "('dismi-\\nnución de la exigencia')",
          cita_en_fuente("disminución de la exigencia", ch_ric))
    check("negativo: cita fabricada NO verifica",
          not cita_en_fuente("los sujetos presentarán declaración jurada anual", ch_ric))
    check("insensible a espacios y saltos de línea",
          cita_en_fuente("Franquicia   informada\nen el mes n", ch_ric))
    check("cita vacía NO verifica", not cita_en_fuente("   ", ch_ric))

    # casos REALES caídos en la calibración fase B (laudo: normalización
    # extendida + fuente sin rótulos). Chunk real: pro::2.3.1.1.
    ch_2311 = chunks_pro["pro::2.3.1.1"]
    cita_guion_espacio = ("ix) El derecho de solicitar la apertura de la Caja de Ahorros "
                          "en pesos con las presta- ciones previstas en el punto 1.8. del "
                          "TO sobre Depósitos de Ahorro, Cuenta Sueldo y Especiales, las "
                          "cuales serán gratuitas.")
    check("caso real fase B: cita con guion+espacio del PDF («presta- ciones») "
          "verifica con la normalización extendida",
          cita_en_fuente(cita_guion_espacio, ch_2311))
    cita_cruza_bloques = ("x) Los restantes requisitos normativamente reglamentados "
                          "según el producto o servicio de que se trate.")
    check("caso real fase B: cita que cruza una frontera de bloques intersticiales "
          "cortada a mitad de palabra ('servi-'/'cio') verifica contra el fuente "
          "sin rótulos",
          cita_en_fuente(cita_cruza_bloques, ch_2311)
          and "servi-" in comun_e3.fuente_integro(ch_2311)
          and "[intersticial | punto 2.3.1]" not in comun_e3.fuente_para_citas(ch_2311))

    # ---------------- F. Flujo del mini-ratchet (fixtures + stubs) ---------- #
    print("\n[F] mini-ratchet con stubs (fixtures)")
    with (BASE / "fixtures" / "fixtures_e3.json").open(encoding="utf-8") as f:
        fx = json.load(f)

    out_dir = BASE / "salida" / "selftest_out"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    # F.1 — amputada: detección → reintento → aceptado
    fa = fx["amputada"]
    chunk_a = chunks_pro[fa["chunk_id"]]
    check("la fixture amputada NO contiene el calificador y el fuente SÍ",
          all(fa["calificador_eliminado"] not in canon(e)
              for e in fa["validacion_amputada"]["entidades"])
          and cita_en_fuente(fa["calificador_eliminado"], chunk_a))

    stub_e3 = cliente_e3.StubClienteE3([fa["veredicto_stub_faltante"], fa["veredicto_stub_ok"]])
    stub_e1 = cliente_e1.StubClienteE1([fa["tool_input_reintento"]])
    registro = ratchet_e3.RegistroE3(out_dir)
    exp = ratchet_e3.ciclo_ratchet(
        chunk_a, fa["validacion_amputada"],
        cliente_verificador=stub_e3, cliente_extractor=stub_e1,
        model_e3="MODELO_FUERTE", model_e1="MODELO_CHICO", registro=registro)
    check("amputada: estado aceptado_tras_reintento",
          exp["estado"] == "aceptado_tras_reintento", exp["estado"])
    check("amputada: la extracción final SÍ contiene el calificador",
          fa["calificador_eliminado"] in canon(exp["validacion_final"]["entidades"]))
    check("amputada: 2 llamadas E3 (verificación + re-verificación), 1 E1 (reintento)",
          len(stub_e3.requests_recibidos) == 2 and len(stub_e1.requests_recibidos) == 1)

    # el reintento preserva el prefijo E1 byte a byte (feedback tras el breakpoint)
    kw_orig = prompt_e1.build_request_kwargs(chunk_a, model="MODELO_CHICO")
    kw_reint = stub_e1.requests_recibidos[0]
    check("reintento: system + tools + tool_choice E1 byte-idénticos al request "
          "original (el caché del prefijo NO se invalida)",
          canon({"system": kw_reint["system"], "tools": kw_reint["tools"],
                 "tool_choice": kw_reint["tool_choice"]}) ==
          canon({"system": kw_orig["system"], "tools": kw_orig["tools"],
                 "tool_choice": kw_orig["tool_choice"]}))
    msg_reint = kw_reint["messages"][0]["content"]
    msg_orig = kw_orig["messages"][0]["content"]
    check("reintento: el mensaje E1 original es PREFIJO del mensaje del reintento "
          "(el feedback va anexado al final, después del breakpoint)",
          msg_reint.startswith(msg_orig) and msg_reint != msg_orig)
    check("reintento: marcado como reintento, con la cita del faltante",
          ratchet_e3.MARCA_REINTENTO in msg_reint
          and fa["calificador_eliminado"] in msg_reint)

    # F.2 — completa: pasa directo, sin tocar al extractor
    fc = fx["completa"]
    stub_e3b = cliente_e3.StubClienteE3([fc["veredicto_stub_ok"]])
    stub_e1b = cliente_e1.StubClienteE1([])
    exp_ok = ratchet_e3.ciclo_ratchet(
        chunks_pro[fc["chunk_id"]], fc["validacion"],
        cliente_verificador=stub_e3b, cliente_extractor=stub_e1b,
        model_e3="MODELO_FUERTE", model_e1="MODELO_CHICO", registro=registro)
    check("completa: estado completo_ok_directo con 1 sola llamada E3 y 0 E1",
          exp_ok["estado"] == "completo_ok_directo"
          and len(stub_e3b.requests_recibidos) == 1
          and len(stub_e1b.requests_recibidos) == 0)
    check("completa: la validación final es la original, intacta",
          canon(exp_ok["validacion_final"]) == canon(fc["validacion"]))

    # F.3 — tope agotado: faltantes persistentes → cola humana con flag y TODO
    stub_e3c = cliente_e3.StubClienteE3([fa["veredicto_stub_faltante"],
                                         fa["veredicto_stub_faltante"]])
    stub_e1c = cliente_e1.StubClienteE1([fa["tool_input_reintento"]])
    exp_tope = ratchet_e3.ciclo_ratchet(
        chunk_a, fa["validacion_amputada"],
        cliente_verificador=stub_e3c, cliente_extractor=stub_e1c,
        model_e3="MODELO_FUERTE", model_e1="MODELO_CHICO", registro=registro)
    check("tope: estado cola_humana tras exactamente 1 reintento "
          "(2 llamadas E3, 1 llamada E1)",
          exp_tope["estado"] == "cola_humana"
          and len(stub_e3c.requests_recibidos) == 2
          and len(stub_e1c.requests_recibidos) == 1)
    check("tope: validacion_final es None — nada ingresa al grafo en silencio",
          exp_tope["validacion_final"] is None)

    # F.4 — veredicto incoherente y cita fabricada
    ev_inc = ratchet_e3.evaluar_veredicto(fx["veredicto_incoherente"], chunk_a)
    check("veredicto incoherente (completo_ok con faltantes) NO cuenta como ok",
          not ev_inc["es_completo_ok"]
          and "completo_ok_con_faltantes" in ev_inc["incoherencias"])
    ev_fab = ratchet_e3.evaluar_veredicto(fx["veredicto_cita_inventada"], chunk_a)
    check("cita fabricada: faltante registrado pero NO utilizable para el ratchet",
          len(ev_fab["faltantes"]) == 1 and not ev_fab["faltantes_utilizables"])
    stub_e3d = cliente_e3.StubClienteE3([fx["veredicto_cita_inventada"]])
    stub_e1d = cliente_e1.StubClienteE1([])
    exp_fab = ratchet_e3.ciclo_ratchet(
        chunk_a, fa["validacion_amputada"],
        cliente_verificador=stub_e3d, cliente_extractor=stub_e1d,
        model_e3="MODELO_FUERTE", model_e1="MODELO_CHICO", registro=registro)
    check("veredicto sin ninguna cita verificable → cola humana con flag propio, "
          "sin re-extraer sobre citas fabricadas",
          exp_fab["estado"] == "cola_humana_veredicto_inutilizable"
          and len(stub_e1d.requests_recibidos) == 0)

    # F.5 — persistencia: TODOS los veredictos + cola humana con TODO
    with (out_dir / "veredictos.jsonl").open(encoding="utf-8") as f:
        veredictos = [json.loads(l) for l in f]
    with (out_dir / "cola_humana.jsonl").open(encoding="utf-8") as f:
        cola = [json.loads(l) for l in f]
    check("todos los veredictos persistidos (2 amputada + 1 completa + 2 tope "
          "+ 1 fabricada = 6)", len(veredictos) == 6, f"hay {len(veredictos)}")
    check("cola humana: 2 entradas (tope + veredicto inutilizable), cada una "
          "con flag y TODO",
          len(cola) == 2
          and all(c["flag"] and c["todo"].startswith("TODO:") for c in cola)
          and {c["flag"] for c in cola} ==
          {"cola_humana", "cola_humana_veredicto_inutilizable"})

    # ---------------- G. Keys de caché local y namespace -------------------- #
    print("\n[G] keys de caché local (never-pay-twice, offline)")
    ns = cliente_e3.namespace_e3()
    k1 = lc.compute_key(ns, lc.canonical_request(
        prompt_e3.build_request_kwargs(*pares[0], model="M")))
    k2 = lc.compute_key(ns, lc.canonical_request(
        prompt_e3.build_request_kwargs(*pares[0], model="M")))
    k3 = lc.compute_key(ns, lc.canonical_request(
        prompt_e3.build_request_kwargs(*pares[1], model="M")))
    check("key determinística por unidad", k1 == k2)
    check("keys distintas entre unidades", k1 != k3)
    check("namespace propio: dominio e3_verificacion + code-version + hash del "
          "prompt del verificador",
          ns.startswith("e3_verificacion") and "e3-verificador-v1" in ns
          and prompt_e3.PREFIJO_HASH in ns and "think=0" in ns, ns)
    check("el hash del prompt E3 difiere del de E1 (contratos independientes)",
          prompt_e3.PREFIJO_HASH != prompt_e1.PREFIJO_HASH)

    # ---------------- I. Enmienda 01: fuente por tipo de unidad ------------- #
    print("\n[I] enmienda 01: blanco de completitud por tipo de unidad")
    resumen_sellado = json.loads(
        (BASE / "salida" / "faseB_pro" / "resumen_faseB_e3.json").read_text(encoding="utf-8"))
    check("PREFIJO E3 INTACTO respecto del sellado (calibradores congelados; "
          "§5 de la enmienda: el prompt del verificador no cambia)",
          prompt_e3.PREFIJO_HASH == resumen_sellado["prefijo_hash_e3"],
          f"{prompt_e3.PREFIJO_HASH} vs {resumen_sellado['prefijo_hash_e3']}")

    chunks_enm = {c["id"]: c for c in cargar_chunks(("pro",),
                                                    e0_dir=comun_e3.E0_SALIDA_ENM01)}
    hijo = chunks_enm["pro::2.7.1"]
    mini = chunks_enm["pro::2.7::intro"]
    f_hijo = fuente_integro(hijo)
    f_mini = fuente_integro(mini)
    check("fuente del hijo: blanco = texto propio, con rótulo [texto propio]",
          "[texto propio | punto 2.7.1]" in f_hijo and hijo["texto"] in f_hijo)
    check("fuente del hijo: la prosa heredada NO viaja (el intro del 2.7 tiene "
          "su propio mini-chunk)",
          "sendos hipervínculos" not in f_hijo)
    check("fuente del hijo: los títulos de la cadena SÍ viajan (contexto no "
          "normativo)",
          "[encabezado | punto 2.7]" in f_hijo
          and "2.7. Revocación de la aceptación" in f_hijo)
    check("fuente del mini: blanco = su bloque, con rótulo [bloque intro]",
          "[bloque intro | punto 2.7]" in f_mini
          and "sendos hipervínculos" in f_mini)
    check("fuente del mini: solo títulos como contexto (ningún otro bloque)",
          all(l.startswith("[encabezado") for l in f_mini.split("\n")
              if l.startswith("[") and not l.startswith("[bloque intro")))
    check("capa de citas del hijo excluye la prosa heredada y la del mini la "
          "incluye",
          not cita_en_fuente("sendos hipervínculos", hijo)
          and cita_en_fuente("sendos hipervínculos", mini))
    check("capa de citas del hijo sigue cubriendo su texto propio",
          cita_en_fuente(hijo["texto"].split("\n")[1], hijo)
          if len(hijo["texto"].split("\n")) > 1 else cita_en_fuente(hijo["texto"], hijo))
    # el request E3 de un mini es función pura y lleva su fuente como datos
    val_min = {"entidades": [], "relaciones": [], "omisiones_no_prosa": []}
    kw_mini = prompt_e3.build_request_kwargs(mini, val_min, model="M")
    check("request E3 del mini: prefijo idéntico al de los chunks (mismo "
          "contrato) y fuente del bloque en el mensaje",
          canon({"system": kw_mini["system"], "tools": kw_mini["tools"],
                 "tool_choice": kw_mini["tool_choice"]}) == ref
          and f_mini in kw_mini["messages"][0]["content"])

    # ---------------- J. Laudos A y B (política de severidad + guardia) ----- #
    print("\n[J] laudos A (severidad) y B (guardia estructural) — E3 congelado")
    unidades_pro = {c["unidad"] for c in chunks_enm.values()}

    # J.1 — LAUDO A: unidad con SOLO faltantes media/baja → aceptada con
    # residuales, cero reintentos (el stub E1 con cola vacía lo prueba).
    chunk_a = chunks_pro["pro::1.1.1"]
    ver_mb = {"veredicto": "faltantes_detectados", "faltantes": [
        {"tipo": "calificador_despojado", "severidad": "media",
         "cita_textual_del_fuente": chunk_a["texto"].split("\n")[0],
         "ubicacion": chunk_a["unidad"]},
        {"tipo": "otro", "severidad": "baja",
         "cita_textual_del_fuente": chunk_a["texto"].split("\n")[-1],
         "ubicacion": chunk_a["unidad"]},
    ]}
    val_a = {"entidades": [], "relaciones": [], "omisiones_no_prosa": [],
             "rechazos": [], "advertencias": [], "metricas": {}}
    stub_e3_j1 = cliente_e3.StubClienteE3([ver_mb])
    stub_e1_j1 = cliente_e1.StubClienteE1([])
    exp_j1 = ratchet_e3.ciclo_ratchet(
        chunk_a, val_a, cliente_verificador=stub_e3_j1, cliente_extractor=stub_e1_j1,
        model_e3="M3", model_e1="M1", unidades_corpus=unidades_pro)
    check("LAUDO A: solo media/baja → aceptado_con_residuales, 0 reintentos, "
          "validación final intacta",
          exp_j1["estado"] == "aceptado_con_residuales"
          and len(stub_e1_j1.requests_recibidos) == 0
          and exp_j1["validacion_final"] is val_a
          and len(exp_j1["residuales"]) == 2, exp_j1["estado"])
    check("LAUDO A: los residuales quedan declarados con su severidad",
          sorted(f["severidad"] for f in exp_j1["residuales"]) == ["baja", "media"])
    ev_j1 = exp_j1["veredictos"][0]
    check("LAUDO A: el veredicto no es completo_ok pero sí aceptable "
          "(distinción persistida)",
          not ev_j1["es_completo_ok"] and ev_j1["aceptable"]
          and not ev_j1["faltantes_bloqueantes"])

    # J.2 — LAUDO A: 'alta' sigue bloqueando (mezcla alta+media → reintento
    # con feedback SOLO del bloqueante).
    ver_mix = {"veredicto": "faltantes_detectados", "faltantes": [
        {"tipo": "excepcion_ausente", "severidad": "alta",
         "cita_textual_del_fuente": chunk_a["texto"].split("\n")[0],
         "ubicacion": chunk_a["unidad"]},
        {"tipo": "otro", "severidad": "media",
         "cita_textual_del_fuente": chunk_a["texto"].split("\n")[-1],
         "ubicacion": chunk_a["unidad"]},
    ]}
    ver_ok = {"veredicto": "completo_ok", "faltantes": []}
    stub_e3_j2 = cliente_e3.StubClienteE3([ver_mix, ver_ok])
    stub_e1_j2 = cliente_e1.StubClienteE1([fx["amputada"]["tool_input_reintento"]])
    exp_j2 = ratchet_e3.ciclo_ratchet(
        chunk_a, val_a, cliente_verificador=stub_e3_j2, cliente_extractor=stub_e1_j2,
        model_e3="M3", model_e1="M1", unidades_corpus=unidades_pro)
    msg_j2 = stub_e1_j2.requests_recibidos[0]["messages"][0]["content"]
    feedback_j2 = msg_j2.split(ratchet_e3.MARCA_REINTENTO)[1]
    check("LAUDO A: alta+media → reintenta y el bloque de feedback lleva SOLO "
          "el bloqueante (el residual no se paga)",
          exp_j2["estado"] == "aceptado_tras_reintento"
          and len(stub_e1_j2.requests_recibidos) == 1
          and "excepcion_ausente" in feedback_j2
          and chunk_a["texto"].split("\n")[0] in feedback_j2
          and chunk_a["texto"].split("\n")[-1] not in feedback_j2)

    # J.3 — LAUDO B: caso REAL pro::2.7::intro — mini ordenador (':' final,
    # origen con descendientes) + enumeracion_incompleta alta sobre la
    # cláusula → estructural_no_bloqueante → aceptado con residuales.
    mini27 = chunks_enm["pro::2.7::intro"]
    ver_27 = {"veredicto": "faltantes_detectados", "faltantes": [
        {"tipo": "enumeracion_incompleta", "severidad": "alta",
         "cita_textual_del_fuente":
             "Los sujetos obligados deberán contar con sendos hipervínculos "
             "que permitan al usuario:",
         "ubicacion": "2.7"},
    ]}
    stub_e3_j3 = cliente_e3.StubClienteE3([ver_27])
    stub_e1_j3 = cliente_e1.StubClienteE1([])
    exp_j3 = ratchet_e3.ciclo_ratchet(
        mini27, val_a, cliente_verificador=stub_e3_j3, cliente_extractor=stub_e1_j3,
        model_e3="M3", model_e1="M1", unidades_corpus=unidades_pro)
    check("LAUDO B: pro::2.7::intro (caso real) → estructural_no_bloqueante, "
          "aceptado_con_residuales sin reintento",
          exp_j3["estado"] == "aceptado_con_residuales"
          and len(stub_e1_j3.requests_recibidos) == 0
          and exp_j3["residuales"][0]["estructural_no_bloqueante"] is True,
          exp_j3["estado"])
    check("LAUDO B: condiciones determinísticas del caso (':' final + "
          "descendientes 2.7.x en el corpus)",
          ratchet_e3._bloque_abre_enumeracion(mini27)
          and ratchet_e3._origen_tiene_descendientes(mini27, unidades_pro))

    # J.4 — LAUDO B falla hacia bloquear: sin unidades_corpus la guardia no
    # aplica y el mismo veredicto (alta) dispara el ratchet.
    ev_sin = ratchet_e3.evaluar_veredicto(ver_27, mini27, None)
    check("LAUDO B: sin unidades_corpus la guardia NO aplica (falla hacia "
          "bloquear)", len(ev_sin["faltantes_bloqueantes"]) == 1
          and not ev_sin["aceptable"])
    # …y tampoco aplica en un chunk hijo, ni con tipo distinto, ni con cita
    # que no es la cláusula ordenadora.
    ev_hijo = ratchet_e3.evaluar_veredicto(ver_27, chunks_enm["pro::2.7.1"], unidades_pro)
    ver_otro = json.loads(json.dumps(ver_27))
    ver_otro["faltantes"][0]["tipo"] = "otro"
    ev_tipo = ratchet_e3.evaluar_veredicto(ver_otro, mini27, unidades_pro)
    check("LAUDO B: no aplica a hijos ni a tipos distintos de "
          "enumeracion_incompleta",
          not ev_hijo["faltantes"][0]["estructural_no_bloqueante"]
          and not ev_tipo["faltantes"][0]["estructural_no_bloqueante"]
          and ev_tipo["faltantes"][0]["bloqueante"])

    # J.5 — E3 congelado: el prompt no cambió con los laudos (re-chequeo del
    # hash sellado al cierre de la unidad).
    check("LAUDOS: prefijo E3 sigue INTACTO tras implementar A y B",
          prompt_e3.PREFIJO_HASH == resumen_sellado["prefijo_hash_e3"])

    # ---------------- K. U-PROMPT-R2: NOTA r2 y enmienda a LAUDO B ------------ #
    print("\n[K] U-PROMPT-R2: NOTA de la forma r2 y guarda ampliada (enmienda a LAUDO B)")
    import perfil_e1
    import validador_e1
    esq_r2 = perfil_e1.perfil("r2b").esquema
    ti_vacio = {"entities": [{"local_id": "to", "type": "TextoOrdenado", "label": "TO", "punto": "2.7"}],
                "relations": [], "omisiones": []}
    val_r2_vacia = validador_e1.validar_salida(ti_vacio, mini27, esquema=esq_r2).as_dict()
    ti_con_norma = json.loads(json.dumps(ti_vacio))
    ti_con_norma["entities"].append({"local_id": "e1", "type": "Obligacion", "label": "Hipervínculos",
                                     "punto": "2.7", "tramo": "deberán contar con sendos hipervínculos",
                                     "properties": {"descripcion": "x"}})
    val_r2_norma = validador_e1.validar_salida(ti_con_norma, mini27, esquema=esq_r2).as_dict()
    val_v3_vacia = {k: v for k, v in val_r2_vacia.items() if k != "forma_salida"}
    check("K: la validación r2 lleva la marca forma_salida; sin O/R/P la ampliación rige, con una O/R/P no",
          val_r2_vacia.get("forma_salida") == "r2" and ratchet_e3.ampliacion_activa(val_r2_vacia)
          and not ratchet_e3.ampliacion_activa(val_r2_norma) and not ratchet_e3.ampliacion_activa(val_v3_vacia)
          and not ratchet_e3.ampliacion_activa(None))
    ev_r2 = ratchet_e3.evaluar_veredicto(ver_otro, mini27, unidades_pro, val_r2_vacia)
    ev_r2_norma = ratchet_e3.evaluar_veredicto(ver_otro, mini27, unidades_pro, val_r2_norma)
    ev_v3 = ratchet_e3.evaluar_veredicto(ver_otro, mini27, unidades_pro, val_v3_vacia)
    check("K: ampliación — un faltante «otro» que cita la cláusula ordenadora se exime con la forma r2 y la "
          "unidad sin O/R/P",
          ev_r2["faltantes"][0]["estructural_no_bloqueante"] and ev_r2["aceptable"])
    check("K: salvaguarda — con una Obligacion en la extracción, el mismo faltante bloquea",
          not ev_r2_norma["faltantes"][0]["estructural_no_bloqueante"] and ev_r2_norma["faltantes"][0]["bloqueante"])
    check("K: sin la marca r2 (perfiles existentes), LAUDO B tal cual: el faltante «otro» bloquea",
          not ev_v3["faltantes"][0]["estructural_no_bloqueante"] and ev_v3["faltantes"][0]["bloqueante"])
    ev_r2_sin = ratchet_e3.evaluar_veredicto(ver_otro, mini27, None, val_r2_vacia)
    ev_r2_hijo = ratchet_e3.evaluar_veredicto(ver_otro, chunks_enm["pro::2.7.1"], unidades_pro, val_r2_vacia)
    check("K: la ampliación conserva las demás condiciones (sin unidades del corpus o en un hijo, bloquea)",
          ev_r2_sin["faltantes"][0]["bloqueante"] and ev_r2_hijo["faltantes"][0]["bloqueante"])
    stub_e3_k = cliente_e3.StubClienteE3([ver_otro])
    stub_e1_k = cliente_e1.StubClienteE1([])
    exp_k = ratchet_e3.ciclo_ratchet(
        mini27, val_r2_vacia, cliente_verificador=stub_e3_k, cliente_extractor=stub_e1_k,
        model_e3="M3", model_e1="M1", unidades_corpus=unidades_pro)
    check("K: en el ciclo, el encabezado sin norma reclamado por la cláusula se acepta con residual y sin "
          "reintento (el reintento no crea el nodo)",
          exp_k["estado"] == "aceptado_con_residuales" and len(stub_e1_k.requests_recibidos) == 0
          and exp_k["residuales"][0]["tipo"] == "otro" and exp_k["residuales"][0]["estructural_no_bloqueante"])
    msg_r2 = prompt_e3.build_user_message(mini27, val_r2_vacia)
    msg_v3 = prompt_e3.build_user_message(mini27, val_v3_vacia)
    check("K: NOTA del encabezado de lista solo con la forma r2",
          "es el encabezado de una lista" in msg_r2 and "es el encabezado de una lista" not in msg_v3)
    # chunk con flags de E0 legada (sin tablas_e0): la NOTA depende solo de los flags
    flag = dict(chunks_enm["pro::2.7.1"], flags={"contenido_tabular": True, "formula": True})
    val_flag_v3 = {"chunk_id": flag["id"], "entidades": [], "relaciones": [], "omisiones_no_prosa": [],
                   "rechazos": [], "advertencias": [], "metricas": {}}
    val_flag_r2 = dict(val_flag_v3, forma_salida="r2")
    m_v3 = prompt_e3.build_user_message(flag, val_flag_v3)
    m_r2 = prompt_e3.build_user_message(flag, val_flag_r2)
    # U-E3-LISTAS: pro::2.7.1 es un ítem de lista; con la marca r2 su mensaje suma la NOTA del ítem y el bloque que
    # abre la lista. La NOTA de los flags sigue siendo la de siempre, byte a byte.
    nota_item_k = prompt_e3.nota_item_lista(flag)
    notas_k = lambda m: m.split("TEXTO FUENTE ÍNTEGRO DE LA UNIDAD", 1)[0]  # noqa: E731

    def k_igual(m_v3: str, m_r2: str) -> bool:
        # U-E3-LISTAS, O4: el mensaje r2 esperado se arma desde el v3 (las NOTAS de siempre más la NOTA del ítem, y el
        # resto con el fuente entre cercas sustituido por el que lleva el bloque) y se compara byte a byte, con el
        # rótulo y las cercas del fuente.
        if nota_item_k is None:
            return m_r2 == m_v3
        fuente_v3_entre_cercas = "```\n" + fuente_integro(flag) + "\n```"
        fuente_r2_entre_cercas = "```\n" + fuente_integro(flag, True) + "\n```"
        resto_v3 = m_v3[len(notas_k(m_v3)):]
        esperado = (notas_k(m_v3) + nota_item_k + "\n\n"
                    + resto_v3.replace(fuente_v3_entre_cercas, fuente_r2_entre_cercas, 1))
        return m_r2 == esperado
    check("K: sin tablas serializadas (E0 legada), la NOTA r2 es la de siempre, byte a byte (U-E3-LISTAS: en un "
          "ítem, más la NOTA del ítem y el bloque que abre la lista)",
          "detectados determinísticamente (flag de E0)" in m_v3 and k_igual(m_v3, m_r2))
    # los tres mensajes manipulados que el check dejaba pasar en O2 tienen que frenar
    fuente_r2_k = fuente_integro(flag, True)
    m_linea = m_r2.replace("```\n\nELEMENTOS EXTRAÍDOS", "```\nTEXTO ESPURIO\n\nELEMENTOS EXTRAÍDOS", 1)
    m_rotulo = m_r2.replace("TEXTO FUENTE ÍNTEGRO DE LA UNIDAD (contexto heredado + punto propio):",
                            "TEXTO FUENTE ÍNTEGRO DE LA UNIDAD (otro rótulo):", 1)
    m_dup_dentro = m_r2.replace(f"```\n{fuente_r2_k}\n```", f"```\n{fuente_r2_k}\n{fuente_r2_k}\n```", 1)
    m_dup_cercas = m_r2.replace(f"```\n{fuente_r2_k}\n```", f"```\n{fuente_r2_k}\n```\n```\n{fuente_r2_k}\n```", 1)
    check("K: frena una línea extra entre la cerca de cierre del fuente y «ELEMENTOS EXTRAÍDOS»",
          m_linea != m_r2 and not k_igual(m_v3, m_linea))
    check("K: frena otro rótulo de la sección del fuente",
          m_rotulo != m_r2 and not k_igual(m_v3, m_rotulo))
    check("K: frena el fuente duplicado, dentro de las mismas cercas y con sus propias cercas",
          m_dup_dentro != m_r2 and m_dup_cercas != m_r2
          and not k_igual(m_v3, m_dup_dentro) and not k_igual(m_v3, m_dup_cercas))
    check("K: E3 congelado — el prefijo sigue intacto con la NOTA r2 y la ampliación",
          prompt_e3.PREFIJO_HASH == resumen_sellado["prefijo_hash_e3"])

    # ---------------- L. U-PROMPT-R2, P3b-2 ------------------------------------ #
    print("\n[L] U-PROMPT-R2, P3b-2: lazo de E3 con la forma r2")
    f_l = {"tipo": "otro", "severidad": "alta", "ubicacion": "2.7",
           "cita_textual_del_fuente": ver_otro["faltantes"][0]["cita_textual_del_fuente"],
           "nota": "falta la obligación de informar al ente rector dentro del plazo previsto"}
    # j: el veredicto como texto
    ti_json = {"veredicto": "faltantes_detectados", "faltantes": json.dumps([f_l], ensure_ascii=False)}
    ti_obj = {"faltantes": json.dumps({"veredicto": "completo_ok", "faltantes": []})}
    ti_rep = {"faltantes": json.dumps([f_l], ensure_ascii=False) + ', "veredicto": "faltantes_detectados"}'}
    ti_mal = {"veredicto": "faltantes_detectados", "faltantes": "sin JSON"}
    ev_json = ratchet_e3.evaluar_veredicto(ti_json, mini27, unidades_pro, val_r2_norma)
    ev_obj = ratchet_e3.evaluar_veredicto(ti_obj, mini27, unidades_pro, val_r2_norma)
    ev_rep = ratchet_e3.evaluar_veredicto(ti_rep, mini27, unidades_pro, val_r2_norma)
    ev_mal = ratchet_e3.evaluar_veredicto(ti_mal, mini27, unidades_pro, val_r2_norma)
    ev_v3j = ratchet_e3.evaluar_veredicto(ti_json, mini27, unidades_pro, val_v3_vacia)
    check("L j: lista como texto → leída («json»), un bloqueante con cita verificada",
          ev_json.get("lectura_faltantes") == "json" and len(ev_json["bloqueantes_utilizables"]) == 1
          and not ev_json["incoherencias"])
    check("L j: el veredicto entero como texto → completo_ok leído («json»)",
          ev_obj.get("lectura_faltantes") == "json" and ev_obj["es_completo_ok"])
    check("L j: con reparo — primer valor JSON y el veredicto del resto («reparo»)",
          ev_rep.get("lectura_faltantes") == "reparo" and not ev_rep["incoherencias"]
          and len(ev_rep["faltantes_bloqueantes"]) == 1)
    check("L j: texto que no se lee → «no_se_lee», faltantes_no_lista como hoy",
          ev_mal.get("lectura_faltantes") == "no_se_lee" and "faltantes_no_lista" in ev_mal["incoherencias"])
    check("L j: sin la forma r2, igual que hoy (sin lectura ni marca)",
          "lectura_faltantes" not in ev_v3j and "faltantes_no_lista" in ev_v3j["incoherencias"])
    # defensa 1: el aviso de la nota, solo con la forma r2
    fb_v3, fb_r2 = ratchet_e3.bloque_feedback([f_l], 1), ratchet_e3.bloque_feedback([f_l], 1, True)
    check("L defensa 1: el aviso de la nota va solo con la forma r2, al final del bloque",
          ratchet_e3.AVISO_NOTA_REINTENTO not in fb_v3 and fb_r2 == fb_v3 + "\n\n" + ratchet_e3.AVISO_NOTA_REINTENTO)
    # ciclo r2 con reintento: lectura (j), copia de la nota (defensa 2) y reintento con menos elementos (k4)
    perfil_r2 = perfil_e1.perfil("r2b")
    reex_copia = {"entities": [{"local_id": "to", "type": "TextoOrdenado", "label": "TO", "punto": "2.7"},
                               {"local_id": "o", "type": "Obligacion", "label": "Informar", "punto": "2.7",
                                "tramo": "deberán contar con sendos hipervínculos",
                                "properties": {"descripcion": "falta la obligación de informar al ente rector"}}],
                  "relations": [], "omisiones": []}
    out_l = BASE / "salida" / "selftest_out_p3b"
    if out_l.exists():
        shutil.rmtree(out_l)
    reg_l = ratchet_e3.RegistroE3(out_l)
    st3 = cliente_e3.StubClienteE3([ti_json, {"veredicto": "completo_ok", "faltantes": []}])
    st1 = cliente_e1.StubClienteE1([reex_copia])
    exp_l = ratchet_e3.ciclo_ratchet(mini27, val_r2_norma, cliente_verificador=st3, cliente_extractor=st1,
                                     model_e3="M3", model_e1="M1", registro=reg_l, unidades_corpus=unidades_pro,
                                     perfil=perfil_r2)
    m_l = exp_l.get("marcas_e3") or {}
    check("L: aceptado tras el reintento; el pedido del reintento lleva el aviso de la nota",
          exp_l["estado"] == "aceptado_tras_reintento"
          and ratchet_e3.AVISO_NOTA_REINTENTO in st1.requests_recibidos[0]["messages"][0]["content"])
    check("L j: la marca de cómo se leyó el veredicto, en la validación final y en veredictos.jsonl",
          m_l.get("lectura_veredicto_e3") == [{"fase": "verificacion", "intento": 0, "lectura": "json"}]
          and exp_l["validacion_final"]["marcas_e3"] == m_l
          and json.loads((out_l / "veredictos.jsonl").read_text(encoding="utf-8").splitlines()[0])
          .get("lectura_faltantes") == "json")
    copias = m_l.get("copia_nota_e3") or []
    check("L defensa 2: la descripción que copia la nota queda marcada (no rechazada), con su índice del crudo",
          len(copias) == 1 and copias[0]["indice_crudo"] == 1 and list(copias[0]["campos"]) == ["descripcion"]
          and len(exp_l["validacion_final"]["entidades"]) == 2
          and (out_l / "copias_nota_e3.jsonl").exists())
    check("L k4: con las mismas entidades y relaciones, sin la marca del reintento",
          "reintento_con_menos_elementos" not in m_l)
    st3b = cliente_e3.StubClienteE3([ver_otro, {"veredicto": "completo_ok", "faltantes": []}])
    st1b = cliente_e1.StubClienteE1([ti_vacio])
    exp_k4 = ratchet_e3.ciclo_ratchet(mini27, val_r2_norma, cliente_verificador=st3b, cliente_extractor=st1b,
                                      model_e3="M3", model_e1="M1", unidades_corpus=unidades_pro, perfil=perfil_r2)
    check("L k4: el reintento con menos entidades se acepta con la marca y los conteos",
          exp_k4["estado"] == "aceptado_tras_reintento"
          and exp_k4["marcas_e3"] == {"reintento_con_menos_elementos": {"entidades": [2, 1], "relaciones": [0, 0]}}
          and exp_k4["validacion_final"]["marcas_e3"] == exp_k4["marcas_e3"])
    # cola humana: el todo r2; el de los perfiles existentes no cambia
    st3c = cliente_e3.StubClienteE3([ver_otro, ver_otro])
    st1c = cliente_e1.StubClienteE1([reex_copia])
    ratchet_e3.ciclo_ratchet(mini27, val_r2_norma, cliente_verificador=st3c, cliente_extractor=st1c,
                             model_e3="M3", model_e1="M1", registro=reg_l, unidades_corpus=unidades_pro,
                             perfil=perfil_r2)
    todo_r2 = json.loads((out_l / "cola_humana.jsonl").read_text(encoding="utf-8").splitlines()[-1])["todo"]
    todo_v3 = json.loads((out_dir / "cola_humana.jsonl").read_text(encoding="utf-8").splitlines()[0])["todo"]
    check("L: el todo de la cola humana con la forma r2 dice que la unidad entra marcada; el de siempre no cambia",
          "entra al grafo con la marca cola_humana" in todo_r2 and "NO ingresa al grafo" in todo_v3)
    check("L: con los perfiles existentes, el expediente no lleva marcas_e3",
          "marcas_e3" not in exp and "marcas_e3" not in exp_ok and "marcas_e3" not in exp_k)
    # i: la NOTA de las omisiones declaradas, solo con la forma r2 y con esas categorías
    val_om = dict(val_r2_norma, omisiones_no_prosa=["[meta_normativo] Vigencia: desde el 1.1.20"])
    m_om, m_om3 = prompt_e3.build_user_message(mini27, val_om), prompt_e3.build_user_message(
        mini27, {k: v for k, v in val_om.items() if k != "forma_salida"})
    check("L i: la NOTA de las omisiones declaradas va con la forma r2 y una categoría de la lista",
          prompt_e3.NOTA_E3_OMISIONES in m_om and prompt_e3.NOTA_E3_OMISIONES not in m_om3
          and prompt_e3.NOTA_E3_OMISIONES not in prompt_e3.build_user_message(mini27, val_r2_norma))
    check("L: E3 congelado — el prefijo sigue intacto con P3b",
          prompt_e3.PREFIJO_HASH == resumen_sellado["prefijo_hash_e3"])

    # ---------------- M. U-PROMPT-R2, P3c-2 -------------------------------- #
    print("\n[M] P3c-2: NOTAS de los puntos a y b, y candado del mensaje (F23)")
    from pathlib import Path as _P
    repo = _P(prompt_e3.__file__).resolve().parents[4]
    sys.path.insert(0, str(repo / "data" / "experiment" / "prompt_r2" / "p3c"))
    import mensaje_p3c_borrador as MP3C  # noqa: PLC0415 — el borrador aprobado en el FRENO P3c-1
    check("M a: la NOTA de las omisiones es la del borrador aprobado (sin el alcance; lista completa)",
          prompt_e3.NOTA_E3_OMISIONES == MP3C.NOTA_OMISIONES_NUEVA
          and "el alcance" not in prompt_e3.NOTA_E3_OMISIONES)
    check("M b: la NOTA del encabezado de lista termina con la oración del borrador aprobado",
          prompt_e3.NOTA_E3_ENCABEZADO_LISTA.endswith(MP3C.ENCABEZADO_NUEVO))
    fix = json.loads(prompt_e3.CANDADO_MENSAJE_E3_JSON.read_text(encoding="utf-8"))
    sint = [c for c in fix["casos"] if "sintetico" in c]
    items_fix = sorted({c["chunk"]["id"] for c in fix["casos"] if comun_e3.indices_bloque_lista(c["chunk"])})
    check("M: la fixture tiene 9 unidades con y sin la marca r2 (las 6 de P3c-2 y 3 ítems de lista, U-E3-LISTAS) y un "
          "caso sintético (la NOTA de las omisiones)",
          len(fix["casos"]) == 19 and len(sint) == 1
          and items_fix == ["cap::6.8.3.1", "ext::3.5.6.1", "pro::2.3.6.1"]
          and prompt_e3.NOTA_E3_OMISIONES in prompt_e3.build_user_message(sint[0]["chunk"], sint[0]["validacion"]))
    check("M: el sha256 de los mensajes de la fixture es el sellado",
          prompt_e3.sha256_mensajes_e3(fix["casos"]) == prompt_e3.MENSAJE_E3_SHA256_ESPERADO)
    frena_e3 = []
    for nombre in ("NOTA_E3_OMISIONES", "NOTA_E3_ENCABEZADO_LISTA", "NOTA_E3_ITEM_LISTA"):
        orig = getattr(prompt_e3, nombre)
        try:
            setattr(prompt_e3, nombre, orig + " ")
            try:
                prompt_e3._candado_mensaje_e3()
                frena_e3.append(False)
            except RuntimeError:
                frena_e3.append(True)
        finally:
            setattr(prompt_e3, nombre, orig)
    prompt_e3._candado_mensaje_e3()
    check("M: un espacio más en cualquiera de las tres NOTAS (la del ítem, U-E3-LISTAS) hace frenar el candado; "
          "restaurado, pasa",
          all(frena_e3), str(frena_e3))
    check("M: el prefijo de E3 y su candado no cambian (21a836c7de6d); importar prompt_e3 importa prompt_r2b "
          "(acoplamiento de la opción i)",
          prompt_e3.PREFIJO_HASH == prompt_e3.PREFIJO_HASH_SELLADO == "21a836c7de6d" and "prompt_r2b" in sys.modules)

    # ---------------- N. U-E3-LISTAS, O2 ----------------------------------- #
    print("\n[N] U-E3-LISTAS: el bloque que abre la lista y la NOTA del ítem, solo con la forma r2")
    e0r2b = comun_e3.REEXTRACCION / "e0_chunking" / "salida_tanda0_r2b"
    ch_r2b = {c["id"]: c for c in cargar_chunks(("ext", "cap", "pro"), e0_dir=e0r2b)}
    v_r2 = {"forma_salida": "r2", "entidades": [], "relaciones": []}
    v_v3 = {"entidades": [], "relaciones": []}

    def fuente_msg(m: str) -> str:
        return m.split("TEXTO FUENTE ÍNTEGRO DE LA UNIDAD", 1)[1].split("ELEMENTOS EXTRAÍDOS DE ESTA UNIDAD", 1)[0]
    # N1: ítem cuyo bloque que abre la lista es intro, con un chapeau y una intro de un ancestro antes y un cierre después
    it1 = ch_r2b["ext::3.5.6.1"]
    abre1 = it1["herencia"][comun_e3.indices_bloque_lista(it1)[0]]
    otros1 = [h for h in it1["herencia"] if h["tipo"] != "encabezado" and h is not abre1]
    m1_r2, m1_v3 = prompt_e3.build_user_message(it1, v_r2), prompt_e3.build_user_message(it1, v_v3)
    check("N1 ítem con intro (ext::3.5.6.1): con la forma r2, el bloque que abre la lista con su rótulo en el fuente y la "
          "NOTA del ítem de unidad propia",
          f"[intro | punto 3.5.6]\n{abre1['texto']}" in fuente_msg(m1_r2)
          and prompt_e3.nota_item_lista(it1) in m1_r2 and prompt_e3.NOTA_E3_ITEM_UNIDAD["propia"] in m1_r2
          and "[intro | punto 3.5.6]" in prompt_e3.nota_item_lista(it1))
    check("N1 ítem con intro: el chapeau, la intro del ancestro y el cierre no entran al fuente",
          [h["tipo"] for h in otros1] == ["chapeau_seccion", "intro", "cierre"]
          and all(h["texto"] not in fuente_msg(m1_r2) for h in otros1))
    check("N1 ítem con intro: sin la marca r2, el fuente y las NOTAS de siempre",
          f"```\n{fuente_integro(it1)}\n```" in m1_v3 and abre1["texto"] not in fuente_msg(m1_v3)
          and "es un ítem de la lista" not in m1_v3)
    # N2: ítem cuyo bloque que abre la lista es la línea de título del punto (encabezado)
    it2 = ch_r2b["cap::6.8.3.1"]
    m2_r2, m2_v3 = prompt_e3.build_user_message(it2, v_r2), prompt_e3.build_user_message(it2, v_v3)
    intro_68 = next(h for h in it2["herencia"] if h["tipo"] == "intro")
    check("N2 ítem con encabezado (cap::6.8.3.1): el fuente es el de siempre (la intro de 6.8, que termina en «:», no "
          "entra) y la NOTA es la de la línea de título",
          fuente_msg(m2_r2) == fuente_msg(m2_v3) and intro_68["texto"] not in fuente_msg(m2_r2)
          and prompt_e3.NOTA_E3_ITEM_UNIDAD["linea_de_titulo"] in m2_r2
          and prompt_e3.NOTA_E3_ITEM_COMPUESTA["linea_de_titulo"] in m2_r2
          and "[encabezado | punto 6.8.3]" in m2_r2 and "es un ítem de la lista" not in m2_v3)
    # N3: D2, el párrafo partido en dos bloques contiguos con el mismo rótulo (pro::2.3.6.1)
    it3 = ch_r2b["pro::2.3.6.1"]
    idx3 = comun_e3.indices_bloque_lista(it3)
    frag3 = [it3["herencia"][k] for k in idx3]
    m3_r2 = prompt_e3.build_user_message(it3, v_r2)
    cita_1 = " ".join(frag3[0]["texto"].split()[:8])
    check("N3 D2 (pro::2.3.6.1): el bloque son dos fragmentos contiguos del mismo tipo y unidad, y los dos entran al fuente",
          len(idx3) == 2 and idx3[1] == idx3[0] + 1 and frag3[0]["tipo"] == frag3[1]["tipo"] == "intro"
          and frag3[0]["unidad_origen"] == frag3[1]["unidad_origen"] == "2.3.6"
          and all(f["texto"] in fuente_msg(m3_r2) for f in frag3))
    check("N3 D2: una cita del primer fragmento verifica con el bloque en las citas y no sin él",
          cita_en_fuente(cita_1, it3, True) and not cita_en_fuente(cita_1, it3))
    # N4: un mini-chunk (la unidad propia del encabezado de la lista de N1): ni bloque ni NOTA del ítem
    mini4 = {c["id"]: c for c in cargar_chunks(("ext",), e0_dir=e0r2b)}["ext::3.5.6::intro"]
    m4_r2, m4_v3 = prompt_e3.build_user_message(mini4, v_r2), prompt_e3.build_user_message(mini4, v_v3)
    check("N4 mini-chunk (ext::3.5.6::intro): la NOTA del encabezado de lista, sin la del ítem, y el fuente de siempre",
          comun_e3.indices_bloque_lista(mini4) == [] and prompt_e3.NOTA_E3_ENCABEZADO_LISTA in m4_r2
          and "es un ítem de la lista" not in m4_r2 and fuente_msg(m4_r2) == fuente_msg(m4_v3))
    # N5: una unidad r1 (E0 de la enmienda 01, corpus_v2), con su validación sin la marca: sin cambio
    ch5 = {c["id"]: c for c in cargar_chunks(("cla",), e0_dir=comun_e3.E0_SALIDA_ENM01)}["cla::5.1.1.1"]
    v5 = comun_e3.cargar_extracciones(comun_e3.REEXTRACCION / "corpus_v2" / "salida" / "cla" /
                                      "extracciones_e1.jsonl")["cla::5.1.1.1"]["validacion"]
    m5 = prompt_e3.build_user_message(ch5, v5)
    check("N5 unidad r1 (cla::5.1.1.1, sin la marca r2): es un ítem, pero el mensaje lleva el fuente de siempre y ninguna "
          "NOTA del ítem",
          v5.get("forma_salida") is None and comun_e3.indices_bloque_lista(ch5) != []
          and f"```\n{fuente_integro(ch5)}\n```" in m5 and fuente_integro(ch5, True) != fuente_integro(ch5)
          and "es un ítem de la lista" not in m5)
    # N6: D1, la cita al bloque que abre la lista verifica en el ratchet solo con la forma r2 (ratchet_e3.py:283)
    ti6 = {"veredicto": "faltantes_detectados",
           "faltantes": [{"tipo": "otro", "cita_textual_del_fuente": " ".join(abre1["texto"].split()[:10]),
                          "ubicacion": "3.5.6.1", "severidad": "alta", "nota": "faltante del selftest"}]}
    ev6_r2 = ratchet_e3.evaluar_veredicto(ti6, it1, None, v_r2)
    ev6_v3 = ratchet_e3.evaluar_veredicto(ti6, it1, None, v_v3)
    check("N6 D1: con la forma r2 la cita al bloque que abre la lista está verificada y es utilizable; sin la marca, no",
          ev6_r2["faltantes"][0]["cita_verificada"] and len(ev6_r2["bloqueantes_utilizables"]) == 1
          and not ev6_v3["faltantes"][0]["cita_verificada"] and not ev6_v3["bloqueantes_utilizables"])
    check("N: el prefijo de E3 no cambia (21a836c7de6d)",
          prompt_e3.PREFIJO_HASH == prompt_e3.PREFIJO_HASH_SELLADO == "21a836c7de6d")

    # ---------------- H. Estimación reproducible ---------------------------- #
    print("\n[H] estimación reproducible")
    import estimacion_e3
    r1 = estimacion_e3.estimar()
    r2 = estimacion_e3.estimar()
    check("dos corridas de la estimación → resultado idéntico", canon(r1) == canon(r2))
    check("calibración = 87 unidades aceptadas; corpus = 1.477",
          r1["calibracion"]["n_unidades"] == 87 and r1["corpus"]["n_unidades"] == 1477)

    print(f"\nprefijo E3: hash {prompt_e3.PREFIJO_HASH} | namespace {ns}")
    print(f"RESULTADO: {OK} ok, {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
