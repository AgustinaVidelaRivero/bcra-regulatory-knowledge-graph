"""
selftest_canal_abierto_e1.py — Selftest OFFLINE del canal abierto experimental
de E1 (U-ESQ-1b): campos `tipo_propuesto` y `predicado_propuesto`, calcados de
`sujeto_propuesto`, por flag explícito `canal_abierto` apagado por defecto.
Cero llamadas a APIs de LLM: fixtures inline + StubClienteE1.

Verifica:
  A. NO REGRESIÓN con flag apagado: prefijo byte-idéntico al de producción
     (sha256 completo sellado pre-edición como candado), tool schema
     byte-idéntico, namespace idéntico al de la corrida sellada enm01,
     request y validación por default == explícito False, y los campos nuevos
     ausentes de toda salida validada.
  B. Flag ENCENDIDO — prefijo/schema/caché: bloque estrictamente aditivo,
     enums intactos (decisión: los enums no se relajan), additionalProperties
     sigue False, Decisión 1 de caching respetada (system en lista de bloques,
     breakpoint ephemeral en el último, nada variable por chunk antes del
     breakpoint, prefijo idéntico entre las 1.763 unidades), namespace
     DISTINTO del de producción (partición de caché) y keys distintas
     on/off para el mismo chunk.
  C. Flag ENCENDIDO — validador: una propuesta de tipo y una de predicado se
     ubican en validacion.entidades junto a `type` y en validacion.relaciones
     junto a `predicate`, sin type_invalido/predicado_invalido; un tipo fuera
     de esquema NO entra silencioso al enum (exclusión mutua exacta, rechazo
     con motivo propio); una propuesta transportada por un elemento que el
     validador rechaza sigue INTACTA en el crudo (caso agencia de crédito del
     exterior vía firma_invalida, más los análogos de tipo y predicado); el
     validador no muta su input.
  D. Dato conocido a no romper: contenedor entities/relations con tipo
     no-lista (cortes por max_tokens) → mismo rechazo a nivel chunk, salida
     byte-idéntica con flag apagado y encendido.

Uso:  python3 selftest_canal_abierto_e1.py
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys

import comun_e1
from comun_e1 import BASE, E0_SALIDA_ENM01, cargar_chunks
import prompt_e1
import cliente_e1
import validador_e1
import llm_cache as lc

OK, FAIL = 0, 0

# Candados de no-regresión: huellas del contrato de producción registradas
# ANTES de la edición de U-ESQ-1b (pre-edición == corrida sellada enm01).
SHA256_PREFIJO_PROD = "4793d61526087fba8963041a3ef72682712ed44b45952806ab79a68c8885c719"
SHA256_TOOL_SCHEMA_PROD = "3eca62d001a282ac105f8df8b91660de4e98bc042315ca5701ccf3c983bf3473"
NAMESPACE_PROD = "e1_extraccion|cv=e1-extractor-v1-p4793d6152608|think=0"


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


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    chunks = cargar_chunks(e0_dir=E0_SALIDA_ENM01)
    por_id = {c["id"]: c for c in chunks}
    chunk = por_id["pro::1.1.1"]
    p = chunk["unidad"]  # punto admitido seguro (el propio)

    # ---------------- A. No regresión con flag apagado ----------------------
    print("[A] no regresión con flag apagado (candados pre-edición)")
    check("prefijo de producción byte-idéntico (sha256 completo del canónico)",
          sha(prompt_e1.PREFIJO_CANONICO) == SHA256_PREFIJO_PROD,
          sha(prompt_e1.PREFIJO_CANONICO))
    check("PREFIJO_HASH == prefijo_hash de la corrida sellada enm01",
          prompt_e1.PREFIJO_HASH == json.loads(
              (BASE / "salida" / "faseB_pro_enm01" / "resumen_faseB.json")
              .read_text(encoding="utf-8"))["prefijo_hash"])
    check("tool schema flag-apagado byte-idéntico al de producción",
          sha(canon(prompt_e1.tool_schema_e1())) == SHA256_TOOL_SCHEMA_PROD)
    check("tool_schema_e1() devuelve EL MISMO objeto de producción",
          prompt_e1.tool_schema_e1() is prompt_e1.TOOL_SCHEMA_E1)
    check("namespace flag-apagado IDÉNTICO al de producción",
          cliente_e1.namespace_e1() == NAMESPACE_PROD, cliente_e1.namespace_e1())
    check("namespace: default == explícito canal_abierto=False",
          cliente_e1.namespace_e1() == cliente_e1.namespace_e1(canal_abierto=False))
    check("request: default == explícito canal_abierto=False, byte a byte",
          canon(prompt_e1.build_request_kwargs(chunk, model="M")) ==
          canon(prompt_e1.build_request_kwargs(chunk, model="M", canal_abierto=False)))

    ti_normal = {
        "entities": [
            {"local_id": "to", "type": "TextoOrdenado", "label": "TO Protección",
             "punto": p, "properties": {}},
            {"local_id": "e1", "type": "Obligacion", "label": "Obligación de prueba",
             "punto": p, "properties": {"descripcion": "x"}},
        ],
        "relations": [
            {"source": "e1", "target": "to", "predicate": "establecida_en", "punto": p},
        ],
    }
    v_def = validador_e1.validar_salida(copy.deepcopy(ti_normal), chunk).as_dict()
    v_off = validador_e1.validar_salida(copy.deepcopy(ti_normal), chunk,
                                        canal_abierto=False).as_dict()
    check("validación: default == explícito canal_abierto=False, byte a byte",
          canon(v_def) == canon(v_off))
    check("flag apagado: NINGUNA clave tipo_propuesto/predicado_propuesto en la salida",
          all("tipo_propuesto" not in e for e in v_def["entidades"])
          and all("predicado_propuesto" not in r for r in v_def["relaciones"]))

    # comportamiento vigente preservado ante los campos nuevos con flag apagado
    ti_stray = copy.deepcopy(ti_normal)
    ti_stray["entities"][1]["tipo_propuesto"] = "TipoAjeno"           # junto a type válido
    v_stray = validador_e1.validar_salida(ti_stray, chunk)
    check("flag apagado: tipo_propuesto espurio junto a type válido → ignorado como "
          "toda clave desconocida (entidad aceptada, sin la clave en la salida)",
          len(v_stray.entidades) == 2 and not v_stray.rechazos
          and all("tipo_propuesto" not in e for e in v_stray.entidades))
    ti_solo_prop = {
        "entities": [{"local_id": "e1", "tipo_propuesto": "TipoAjeno",
                      "label": "x", "punto": p, "properties": {}}],
        "relations": [{"source": "e1", "predicado_propuesto": "predicado_ajeno",
                       "punto": p}],
    }
    v_solo = validador_e1.validar_salida(ti_solo_prop, chunk)
    motivos_solo = {r["motivo"] for r in v_solo.rechazos}
    check("flag apagado: entidad SOLO con tipo_propuesto → type_invalido (hoy)",
          "type_invalido" in motivos_solo, str(motivos_solo))
    check("flag apagado: relación SOLO con predicado_propuesto → predicado_invalido (hoy)",
          "predicado_invalido" in motivos_solo, str(motivos_solo))

    # ---------------- B. Flag encendido: prefijo, schema, caché -------------
    print("\n[B] flag encendido: prefijo aditivo, enums intactos, caché particionada")
    check("prefijo encendido = prefijo producción + bloque (estrictamente aditivo)",
          prompt_e1.prefijo_sistema(True) ==
          prompt_e1.PREFIJO_SISTEMA + prompt_e1.BLOQUE_CANAL_ABIERTO)
    check("el bloque declara ambos campos y la exclusión mutua",
          "tipo_propuesto" in prompt_e1.BLOQUE_CANAL_ABIERTO
          and "predicado_propuesto" in prompt_e1.BLOQUE_CANAL_ABIERTO
          and "MUTUAMENTE EXCLUYENTES" in prompt_e1.BLOQUE_CANAL_ABIERTO)

    ts_on = prompt_e1.tool_schema_e1(canal_abierto=True)
    ent_on = ts_on["input_schema"]["properties"]["entities"]["items"]
    rel_on = ts_on["input_schema"]["properties"]["relations"]["items"]
    ent_off = prompt_e1.TOOL_SCHEMA_E1["input_schema"]["properties"]["entities"]["items"]
    rel_off = prompt_e1.TOOL_SCHEMA_E1["input_schema"]["properties"]["relations"]["items"]
    check("schema encendido declara tipo_propuesto y predicado_propuesto",
          "tipo_propuesto" in ent_on["properties"]
          and "predicado_propuesto" in rel_on["properties"])
    check("los enums NO se relajan (type y predicate byte-idénticos on/off)",
          ent_on["properties"]["type"]["enum"] == ent_off["properties"]["type"]["enum"]
          and rel_on["properties"]["predicate"]["enum"] == rel_off["properties"]["predicate"]["enum"])
    check("sujeto_id/sujeto_propuesto_padre_sugerido: enums de sujetos intactos",
          rel_on["properties"]["sujeto_id"]["enum"] == rel_off["properties"]["sujeto_id"]["enum"])
    check("additionalProperties sigue False en entities y relations (el campo se "
          "declara, el schema no se abre)",
          ent_on["additionalProperties"] is False and rel_on["additionalProperties"] is False)
    check("required encendido: type/predicate dejan de ser required (la exclusión "
          "mutua exacta la exige el validador, como con sujeto_*)",
          ent_on["required"] == ["local_id", "label", "punto"]
          and rel_on["required"] == ["punto"])
    check("construir el schema encendido NO mutó el de producción (deepcopy)",
          sha(canon(prompt_e1.TOOL_SCHEMA_E1)) == SHA256_TOOL_SCHEMA_PROD)

    check("hash del prefijo encendido DISTINTO del de producción",
          prompt_e1.PREFIJO_HASH_CANAL_ABIERTO != prompt_e1.PREFIJO_HASH,
          prompt_e1.PREFIJO_HASH_CANAL_ABIERTO)
    ns_on = cliente_e1.namespace_e1(canal_abierto=True)
    check("namespace encendido DISTINTO del de producción y porta el hash nuevo",
          ns_on != NAMESPACE_PROD and prompt_e1.PREFIJO_HASH_CANAL_ABIERTO in ns_on, ns_on)

    # Decisión 1 con flag encendido: prefijo estable e idéntico entre unidades
    ref = None
    prefijo_identico = True
    texto_en_prefijo = False
    for c in chunks:
        kw = prompt_e1.build_request_kwargs(c, model="M", canal_abierto=True)
        pref = canon({"system": kw["system"], "tools": kw["tools"],
                      "tool_choice": kw["tool_choice"]})
        if ref is None:
            ref = pref
        elif pref != ref:
            prefijo_identico = False
            break
        if len(c["texto"]) >= 40 and c["texto"][:80] in pref:
            texto_en_prefijo = True
            break
    check("prefijo encendido idéntico en las 1.763 unidades (nada variable por chunk)",
          prefijo_identico and ref is not None and len(chunks) == 1763)
    check("nada del texto variable (≥40 chars) aparece en el prefijo encendido",
          not texto_en_prefijo)
    kw_on = prompt_e1.build_request_kwargs(chunk, model="M", canal_abierto=True)
    check("system encendido: lista de UN bloque con cache_control ephemeral en el último",
          isinstance(kw_on["system"], list) and len(kw_on["system"]) == 1
          and kw_on["system"][-1].get("cache_control") == {"type": "ephemeral"})
    check("mensaje de usuario idéntico on/off (lo variable no cambia con el flag)",
          kw_on["messages"] == prompt_e1.build_request_kwargs(chunk, model="M")["messages"])
    check("request encendido determinístico (mismo chunk → byte a byte)",
          canon(kw_on) == canon(prompt_e1.build_request_kwargs(chunk, model="M",
                                                               canal_abierto=True)))
    k_off = lc.compute_key(cliente_e1.namespace_e1(),
                           lc.canonical_request(prompt_e1.build_request_kwargs(chunk, model="M")))
    k_on = lc.compute_key(ns_on, lc.canonical_request(kw_on))
    check("keys de caché local DISTINTAS on/off para el mismo chunk", k_off != k_on)

    # el stub recibe el request canónico encendido vía extraer_chunk
    ti_min = {"entities": [], "relations": []}
    stub = cliente_e1.StubClienteE1([ti_min])
    cliente_e1.extraer_chunk(stub, chunk, model="M", canal_abierto=True)
    check("extraer_chunk(canal_abierto=True) manda el request encendido al cliente",
          canon(stub.requests_recibidos[0]) == canon(kw_on))

    # ---------------- C. Flag encendido: validador --------------------------
    print("\n[C] flag encendido: el validador ubica las propuestas y no las rechaza")
    ti_prop = {
        "entities": [
            {"local_id": "to", "type": "TextoOrdenado", "label": "TO Protección",
             "punto": p, "properties": {}},
            {"local_id": "e1", "tipo_propuesto": "TipoFueraDeEsquema",
             "label": "Concepto fuera de esquema", "punto": p,
             "properties": {"descripcion": "x"}},
            {"local_id": "e2", "type": "Obligacion", "label": "Obligación normal",
             "punto": p, "properties": {"descripcion": "y"}},
            {"local_id": "e3", "type": "Operacion", "label": "Operación normal",
             "punto": p, "properties": {}},
        ],
        "relations": [
            {"source": "e2", "target": "e3", "predicado_propuesto": "predicado_fuera_de_esquema",
             "punto": p},
            {"source": "e2", "target": "e3", "predicate": "regula", "punto": p},
        ],
    }
    crudo_antes = copy.deepcopy(ti_prop)
    res = validador_e1.validar_salida(ti_prop, chunk, canal_abierto=True)
    motivos = {r["motivo"] for r in res.rechazos}
    check("cero rechazos; en particular NI type_invalido NI predicado_invalido",
          not res.rechazos, str(res.rechazos))
    ent_prop = next((e for e in res.entidades if e["local_id"] == "e1"), None)
    check("tipo_propuesto ubicado en validacion.entidades junto a type "
          "(type=None, tipo_propuesto poblado)",
          ent_prop is not None and ent_prop["type"] is None
          and ent_prop["tipo_propuesto"] == "TipoFueraDeEsquema"
          and "type" in ent_prop and "tipo_propuesto" in ent_prop, str(ent_prop))
    check("entidad de enum lleva la clave tipo_propuesto=None (uniforme, como "
          "sujeto_propuesto en relaciones)",
          all("tipo_propuesto" in e for e in res.entidades)
          and next(e for e in res.entidades if e["local_id"] == "e2")["tipo_propuesto"] is None)
    rel_prop = next((r for r in res.relaciones if r["predicado_propuesto"]), None)
    check("predicado_propuesto ubicado en validacion.relaciones junto a predicate "
          "(predicate=None, predicado_propuesto poblado, extremos preservados)",
          rel_prop is not None and rel_prop["predicate"] is None
          and rel_prop["predicado_propuesto"] == "predicado_fuera_de_esquema"
          and rel_prop["source"] == "e2" and rel_prop["target"] == "e3", str(rel_prop))
    check("relación de enum lleva la clave predicado_propuesto=None",
          all("predicado_propuesto" in r for r in res.relaciones)
          and next(r for r in res.relaciones if r["predicate"] == "regula")
          ["predicado_propuesto"] is None)
    check("provenance completa también en los elementos propuestos",
          set(ent_prop["provenance"]) == {"to", "archivo", "punto", "rol_documental"}
          and set(rel_prop["provenance"]) == {"to", "archivo", "punto", "rol_documental"})
    check("el crudo llega intacto (el validador no muta su input)",
          canon(ti_prop) == canon(crudo_antes))

    # un tipo/predicado fuera de esquema NO entra silencioso en el enum
    ti_mixto = {
        "entities": [
            {"local_id": "to", "type": "TextoOrdenado", "label": "TO", "punto": p,
             "properties": {}},
            {"local_id": "e1", "type": "Obligacion", "tipo_propuesto": "TipoColado",
             "label": "ambos campos", "punto": p, "properties": {}},
            {"local_id": "e2", "type": "TipoInventadoDirecto", "label": "enum roto",
             "punto": p, "properties": {}},
            {"local_id": "e3", "type": "Obligacion", "label": "obl", "punto": p,
             "properties": {}},
            {"local_id": "e4", "type": "Operacion", "label": "op", "punto": p,
             "properties": {}},
        ],
        "relations": [
            {"source": "e3", "target": "e4", "predicate": "regula",
             "predicado_propuesto": "predicado_colado", "punto": p},
        ],
    }
    res_mx = validador_e1.validar_salida(ti_mixto, chunk, canal_abierto=True)
    motivos_mx = {r["motivo"] for r in res_mx.rechazos}
    check("type + tipo_propuesto juntos → tipo_canal_invalido (exclusión mutua "
          "exacta: la propuesta no entra silenciosa al enum)",
          "tipo_canal_invalido" in motivos_mx
          and all(e["local_id"] != "e1" for e in res_mx.entidades), str(motivos_mx))
    check("type fuera de enum sin propuesta → type_invalido (igual que hoy)",
          "type_invalido" in motivos_mx
          and all(e["local_id"] != "e2" for e in res_mx.entidades))
    check("predicate + predicado_propuesto juntos → predicado_canal_invalido",
          "predicado_canal_invalido" in motivos_mx and not res_mx.relaciones)

    # propuesta transportada por un elemento rechazado → sobrevive en el crudo
    ti_agencia = {
        "entities": [
            {"local_id": "to", "type": "TextoOrdenado", "label": "TO", "punto": p,
             "properties": {}},
            {"local_id": "e1", "type": "Excepcion", "label": "Excepción de prueba",
             "punto": p, "properties": {"descripcion": "x"}},
            {"local_id": "e9", "tipo_propuesto": "TipoEnPuntoInvalido",
             "label": "propuesta mal anclada", "punto": "999.999", "properties": {}},
        ],
        "relations": [
            # firma_invalida: aplica_a exige {Restriccion, Obligacion} como dominio
            {"source": "e1", "predicate": "aplica_a",
             "sujeto_propuesto": "agencia de crédito del exterior", "punto": p},
            # predicado propuesto transportado por relación con punto inválido
            {"source": "e1", "target": "to", "predicado_propuesto": "predicado_perdido",
             "punto": "999.999"},
        ],
    }
    crudo_agencia = copy.deepcopy(ti_agencia)
    res_ag = validador_e1.validar_salida(ti_agencia, chunk, canal_abierto=True)
    motivos_ag = {r["motivo"] for r in res_ag.rechazos}
    check("caso agencia de crédito del exterior: la relación cae por firma_invalida "
          "(el canal abierto NO cambia la semántica de rechazos)",
          "firma_invalida" in motivos_ag and not any(
              r["sujeto_propuesto"] for r in res_ag.relaciones), str(motivos_ag))
    check("…y la propuesta sigue INTACTA en el crudo",
          canon(ti_agencia) == canon(crudo_agencia)
          and ti_agencia["relations"][0]["sujeto_propuesto"]
          == "agencia de crédito del exterior")
    check("análogo tipo: entidad propuesta con punto inválido → rechazada del "
          "validado, tipo_propuesto intacto en el crudo",
          "punto_fuera_de_admitidos" in motivos_ag
          and all(e["local_id"] != "e9" for e in res_ag.entidades)
          and ti_agencia["entities"][2]["tipo_propuesto"] == "TipoEnPuntoInvalido")
    check("análogo predicado: relación propuesta con punto inválido → rechazada "
          "del validado, predicado_propuesto intacto en el crudo",
          not any(r.get("predicado_propuesto") for r in res_ag.relaciones)
          and ti_agencia["relations"][1]["predicado_propuesto"] == "predicado_perdido")

    # el registro con forma de runner transporta el crudo tal cual
    reg = {"tool_input_crudo": ti_agencia,
           "validacion": res_ag.as_dict()}
    check("registro forma-runner: tool_input_crudo conserva ambas propuestas",
          reg["tool_input_crudo"]["relations"][0]["sujeto_propuesto"]
          == "agencia de crédito del exterior"
          and reg["tool_input_crudo"]["entities"][2]["tipo_propuesto"]
          == "TipoEnPuntoInvalido"
          and reg["tool_input_crudo"]["relations"][1]["predicado_propuesto"]
          == "predicado_perdido")

    # ---------------- D. Dato conocido: contenedor no-lista -----------------
    print("\n[D] contenedor no-lista (cortes por max_tokens): comportamiento intacto")
    ti_trunc = {"entities": "[{\"local_id\": \"to\", \"type\": \"TextoOrde",
                "relations": []}
    v_t_off = validador_e1.validar_salida(copy.deepcopy(ti_trunc), chunk).as_dict()
    v_t_on = validador_e1.validar_salida(copy.deepcopy(ti_trunc), chunk,
                                         canal_abierto=True).as_dict()
    check("contenedor no-lista → rechazo chunk entities_o_relations_invalidos, "
          "byte-idéntico con flag apagado y encendido",
          canon(v_t_off) == canon(v_t_on)
          and any(r["motivo"] == "entities_o_relations_invalidos"
                  for r in v_t_off["rechazos"]))
    ti_dict = {"entities": {"0": {}}, "relations": []}
    check("contenedor dict → ídem, byte-idéntico on/off",
          canon(validador_e1.validar_salida(copy.deepcopy(ti_dict), chunk).as_dict())
          == canon(validador_e1.validar_salida(copy.deepcopy(ti_dict), chunk,
                                               canal_abierto=True).as_dict()))

    print(f"\nRESULTADO: {OK} ok, {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
