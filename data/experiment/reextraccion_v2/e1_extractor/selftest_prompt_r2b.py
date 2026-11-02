"""
selftest_prompt_r2b.py — U-PROMPT-R2, P2, P3b-2, P3c-2 y P5: selftest OFFLINE del perfil r2b (prompt_r2b.py). Cero
llamadas a la API.

  P3c-2: el prefijo se re-congela con el parche de P3c sobre el de P3b-2 (3817de475c93), con su candado; la lista de
  tablas forzadas trae cap::tabla037 y se lee con su sha256; la línea de alcance es la de P3c, punto e; y el candado
  del mensaje compara el de un conjunto fijo de unidades (G).

  A. Candados: el texto armado y el hash canónico son los congelados (re-congelados en P3b-2); el tool schema, la
     tabla de alcance r2, los labels, el bloque de catálogo, los reemplazos de P2 y el parche de P3b tienen los sha
     esperados.
  B. Fuera de los tramos reemplazados, el texto es byte a byte el del sellado v3_b54 (precedente:
     selftest_prompt_v3_b54.py): cada `nuevo` del parche de P3b aparece una sola vez y, revirtiéndolos, se obtiene
     el prefijo de P2 (14d6b63b508e); cada `nuevo` de P2 aparece una sola vez en él y, revirtiendo esos reemplazos
     en orden inverso y el bloque de catálogo, se obtiene exactamente prompt_v3_b54.PREFIJO_SISTEMA_V3.
  C. El prefijo de P2 es el del borrador B aprobado en el FRENO P1 (prompt_r2/p1/salida/prefijo_r2_borrador_B.txt) y
     el congelado es el borrador de P3b-1 aprobado (prompt_r2/p3b/salida/prefijo_r2b_parche_borrador.txt), con los
     mismos 12 reemplazos (reemplazos_p3b_borrador.json).
  D. Request: system como bloque único con cache_control al final, tools = el tool schema r2, tool_choice forzado,
     max_tokens 8.192; prefijo idéntico entre unidades; mismo chunk → mismo request.
  E. Mensaje: igual, en las 2.434 unidades de la e0-r2 de la tanda 0, al del borrador de P3b-1 aprobado
     (prompt_r2/p3b/mensaje_p3b_borrador.build_user_message_p3b); igual al de P1
     (prompt_r2/p1/mensaje_r2_borrador.build_user_message_r2, con la tabla de alcance v3, que coincide con la r2)
     salvo en los 1.053 ítems (g) y los 121 mini-chunks a mitad de oración (h); la línea del recorte de E0 va solo
     en un chunk con `herencia_recortada`.
  F. Tablas forzadas a residual: con una tabla en la lista, cambia el mensaje de su unidad y no el prefijo.
  H. P5: el pedido lleva `temperature` 0 (TEMPERATURA_E1_R2B) en las 2.434 unidades, sin cambiar el prefijo; la
     temperatura del reintento por salida mal formada es 1 (TEMPERATURA_REINTENTO_FORMA_R2B). El camino del runner
     (reintento por corte, tercer escalón, ratchet y reintento por forma) lo prueba selftest_ub53.py, P8.
  I. U-ALCANCE-E1: el registro de alcance por tanda entra al mensaje por su derivado
     (catalogo_unico/registro_alcance_r2b.json), con su candado; el derivado se regenera byte a byte desde el registro con
     el lector de R2-2; la regla lee primero la tabla de la release; un caso por rama (una clase, dos clases, rol
     reutilizado, documento declarado sin alcance); la tanda 0 no cambia. En G, la fixture del candado suma cuatro
     sintéticas con documentos del registro, y una entrada del derivado alterada en memoria hace frenar el candado; las
     dos comprobaciones de la fixture de P3c-2 miran sus 13 primeras unidades. Los casos de U-ALCANCE-E1 se evalúan
     protegidos (check_protegido): con el código de HEAD, que no tiene el derivado, dan FAIL sin cortar el selftest
     (control negativo de los FRENOs A1 y A2). Desde A2, el derivado sale del registro final de la tanda 1 (10
     entradas, con ri_mmsef), y el perfil r2b (perfil_e1, la tabla que valida el manifiesto) da a cada documento la
     entrada de la misma regla que arma el mensaje. Desde A3, el derivado sale de `--tandas 1,final` (43 entradas: las 10
     de la tanda 1 y 33 de la tabla «## Tanda final» del registro); los casos de la tanda 1 miran sus 10 primeras
     entradas, y un caso nuevo controla que las filas de la tanda final entran con `--tandas 1,final` y no con
     `--tandas 1` (con el código de HEAD falla solo ese caso: control negativo del FRENO A3).

Uso (desde la raíz del repo):
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/reextraccion_v2/e1_extractor/selftest_prompt_r2b.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[3]
sys.path.insert(0, str(AQUI))
import comun_e1  # noqa: E402
import prompt_r2b as P  # noqa: E402
import prompt_v3_b54 as v3  # noqa: E402  (en el path vía prompt_r2b)

P1 = REPO / "data" / "experiment" / "prompt_r2" / "p1"
sys.path.insert(0, str(P1))
import mensaje_r2_borrador as MB  # noqa: E402

P3B = REPO / "data" / "experiment" / "prompt_r2" / "p3b"
sys.path.insert(0, str(P3B))
import mensaje_p3b_borrador as MB3  # noqa: E402

sys.path.insert(0, str(REPO / "data" / "experiment" / "prompt_r2" / "p3c"))
import mensaje_p3c_borrador as MP3C  # noqa: E402

OK = FAIL = 0


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok  {nombre}")
    else:
        FAIL += 1
        print(f"  FAIL {nombre} {detalle}")


def check_protegido(nombre: str, fn) -> None:
    """Un caso de U-ALCANCE-E1: `fn` devuelve (condición, detalle). Si usa algo que el módulo no tiene (el código de HEAD,
    sin el derivado), cuenta FAIL con el error, sin cortar el selftest."""
    try:
        cond, detalle = fn()
    except Exception as e:  # noqa: BLE001
        cond, detalle = False, f"{type(e).__name__}: {e}"
    check(nombre, cond, detalle)


# U-ALCANCE-E1: el derivado del registro de alcance por tanda, su generador y las tandas con que se genera.
DERIVADO_REGISTRO = REPO / "data" / "experiment" / "catalogo_unico" / "registro_alcance_r2b.json"
GENERADOR_DERIVADO = REPO / "data" / "experiment" / "catalogo_unico" / "code" / "derivar_registro_alcance_r2b.py"
TANDAS_DEL_DERIVADO = "1,final"
CON_ALCANCE_TANDA1 = ("ri_ccna.pdf", "ri_rml.pdf", "ri_gerc.pdf", "ri_pgn.pdf", "ri_dcpc.pdf", "snp_cheq.pdf",
                      "snp_tr.pdf", "manori.pdf", "nmcief.pdf", "ri_mmsef.pdf")
SIN_ALCANCE_TANDA1 = ("ri_oc.pdf", "ceninf.pdf", "cirmo3.pdf")
# A3: las filas de la tabla «## Tanda final» del registro, en su orden (lectura de la autora del 18/10/2026).
CON_ALCANCE_TANDA_FINAL = ("ri_acsf.pdf", "ri_ai.pdf", "ri_bdp.pdf", "ri_esd.pdf", "ri_ii_31_12_19.pdf", "ri_msrl.pdf",
                           "ri_nge.pdf", "ri_ot.pdf", "ri_rcl.pdf", "ri_secoexpo.pdf", "ri_sef.pdf", "ri_tar.pdf",
                           "ri_tvf.pdf", "ribspc.pdf", "cateloc.pdf", "horari.pdf", "inspag.pdf", "opecam.pdf",
                           "reqcac.pdf", "ri_iepsp.pdf", "ri_psp.pdf", "seguef.pdf", "cedin.pdf", "consyr.pdf",
                           "garant.pdf", "garopt.pdf", "jafip.pdf", "ri_ieccm.pdf", "ri_tsa.pdf", "seggar.pdf",
                           "snp_dd.pdf", "venliq.pdf", "verac.pdf")
SIN_ALCANCE_TANDA_FINAL = ("ri_cr.pdf", "ri_dsf.pdf", "ri_transpa.pdf", "regpri.pdf", "ri_pspapt.pdf", "asomut.pdf",
                           "fimipyme.pdf", "micemp.pdf", "ratio.pdf", "ri_iesinap.pdf", "ri_laft.pdf", "rmgcti.pdf",
                           "snp_mep.pdf")
ARCHIVO_RIC = "TO_regimen_informativo_contable_mensual_actual.pdf"


def main() -> int:
    print("[A] candados")
    check("sha256 del texto y hash canónico congelados",
          P.PREFIJO_SHA256_R2B == P.PREFIJO_SHA256_R2B_ESPERADO and P.PREFIJO_HASH_R2B == P.PREFIJO_HASH_R2B_ESPERADO,
          f"{P.PREFIJO_SHA256_R2B[:12]} {P.PREFIJO_HASH_R2B}")
    for nombre, ruta, esperado in (("tool schema", P.TOOL_SCHEMA_R2_JSON, P.TOOL_SCHEMA_R2_SHA256_ESPERADO),
                                   ("rol_por_to_r2", P.ROL_POR_TO_R2_JSON, P.ROL_POR_TO_R2_SHA256_ESPERADO),
                                   ("labels_e2_r2", P.LABELS_E2_R2_JSON, P.LABELS_E2_R2_SHA256_ESPERADO),
                                   ("bloque de catálogo r2", P.BLOQUE_CATALOGO_R2, P.BLOQUE_CATALOGO_R2_SHA256_ESPERADO),
                                   ("reemplazos congelados", P.REEMPLAZOS_JSON, P.REEMPLAZOS_SHA256_ESPERADO),
                                   ("parche de P3b", P.PARCHE_P3B_JSON, P.PARCHE_P3B_SHA256_ESPERADO),
                                   ("parche de P3c", P.PARCHE_P3C_JSON, P.PARCHE_P3C_SHA256_ESPERADO),
                                   ("tablas forzadas a residual", P.TABLAS_FORZADAS_JSON, P.TABLAS_FORZADAS_SHA256_ESPERADO),
                                   ("fixture del candado del mensaje", P.CANDADO_MENSAJE_JSON,
                                    P.CANDADO_MENSAJE_JSON_SHA256_ESPERADO)):
        check(f"{nombre}: sha256 esperado", hashlib.sha256(ruta.read_bytes()).hexdigest() == esperado)
    man = json.loads((P.BLOQUE_CATALOGO_R2.parent / "manifest_generados_r2.json").read_text(encoding="utf-8"))
    check("bloque de catálogo r2 = el de su manifiesto (LN-8)",
          man["archivos"]["bloque_catalogo_r2.txt"] == P.BLOQUE_CATALOGO_R2_SHA256_ESPERADO)
    check("el sellado v3_b54 sigue intacto", v3.PREFIJO_SHA256_V3 == P.PREFIJO_SHA256_V3_ESPERADO
          and v3.PREFIJO_HASH_V3 == "54a111e2175f")
    check("re-congelado de P3c-2: 322c5a23e9b7, 59.909 caracteres", P.PREFIJO_HASH_R2B == "322c5a23e9b7"
          and len(P.PREFIJO_SISTEMA_R2B) == 59909, f"{P.PREFIJO_HASH_R2B} {len(P.PREFIJO_SISTEMA_R2B)}")
    check("prefijo de P3b-2, base del parche de P3c: sha esperado (3817de475c93), 55.105 caracteres",
          hashlib.sha256(P.PREFIJO_SISTEMA_R2B_P3B.encode("utf-8")).hexdigest() == P.PREFIJO_SHA256_R2B_P3B
          and len(P.PREFIJO_SISTEMA_R2B_P3B) == 55105)
    check("prefijo de P2: sha esperado (14d6b63b508e)",
          hashlib.sha256(P.PREFIJO_SISTEMA_R2B_P2.encode("utf-8")).hexdigest() == P.PREFIJO_SHA256_R2B_P2)

    print("\n[B] fuera de los tramos reemplazados, byte a byte el sellado")
    t = P.PREFIJO_SISTEMA_R2B
    check("cada texto nuevo del parche de P3c aparece una sola vez (15 reemplazos)",
          all(t.count(r["nuevo"]) == 1 for r in P.REEMPLAZOS_P3C) and len(P.REEMPLAZOS_P3C) == 15)
    for r in reversed(P.REEMPLAZOS_P3C):
        t = t.replace(r["nuevo"], r["viejo"])
    check("revirtiendo el parche de P3c se obtiene el prefijo de P3b-2 byte a byte", t == P.PREFIJO_SISTEMA_R2B_P3B)
    check("cada texto nuevo del parche de P3b aparece una sola vez (12 reemplazos)",
          all(t.count(r["nuevo"]) == 1 for r in P.REEMPLAZOS_P3B) and len(P.REEMPLAZOS_P3B) == 12)
    for r in reversed(P.REEMPLAZOS_P3B):
        t = t.replace(r["nuevo"], r["viejo"])
    check("revirtiendo el parche de P3b se obtiene el prefijo de P2 byte a byte", t == P.PREFIJO_SISTEMA_R2B_P2)
    bloque = P.BLOQUE_CATALOGO_R2.read_text(encoding="utf-8")
    check("el bloque de catálogo r2 aparece una sola vez", t.count(bloque) == 1)
    i = v3.PREFIJO_SISTEMA_V3.index(P.ANCLA_INICIO_BLOQUE)
    k = v3.PREFIJO_SISTEMA_V3.index(P.ANCLA_FIN_BLOQUE)
    t = t.replace(bloque, v3.PREFIJO_SISTEMA_V3[i:k])
    unicos = all(t.count(r["nuevo"]) == 1 for r in P.REEMPLAZOS_R2B)
    check("cada texto nuevo aparece una sola vez (30 reemplazos)", unicos and len(P.REEMPLAZOS_R2B) == 30)
    for r in reversed(P.REEMPLAZOS_R2B):
        t = t.replace(r["nuevo"], r["viejo"])
    check("revirtiendo reemplazos y bloque se obtiene el sellado v3_b54 byte a byte", t == v3.PREFIJO_SISTEMA_V3)

    print("\n[C] el texto congelado es el de los borradores aprobados")
    b = (P1 / "salida" / "prefijo_r2_borrador_B.txt").read_text(encoding="utf-8")
    check("prefijo_r2_borrador_B.txt == prefijo de P2", b == P.PREFIJO_SISTEMA_R2B_P2)
    b3 = (P3B / "salida" / "prefijo_r2b_parche_borrador.txt").read_text(encoding="utf-8")
    check("prefijo_r2b_parche_borrador.txt (P3b-1) == prefijo de P3b-2", b3 == P.PREFIJO_SISTEMA_R2B_P3B)
    P3C = REPO / "data" / "experiment" / "prompt_r2" / "p3c"
    b4 = (P3C / "salida" / "prefijo_r2b_p3c_borrador.txt").read_text(encoding="utf-8")
    check("prefijo_r2b_p3c_borrador.txt (P3c-1, aprobado) == PREFIJO_SISTEMA_R2B", b4 == P.PREFIJO_SISTEMA_R2B)
    r4 = json.loads((P3C / "salida" / "reemplazos_p3c_borrador.json").read_text(encoding="utf-8"))
    check("los 15 reemplazos congelados == los del borrador de P3c-1", r4["reemplazos"] == P.REEMPLAZOS_P3C)
    check("la línea de alcance == la del borrador de P3c-1 (punto e)", P.LINEA_ALCANCE == MP3C.ALCANCE_NUEVO)
    r3 = json.loads((P3B / "salida" / "reemplazos_p3b_borrador.json").read_text(encoding="utf-8"))
    check("los 12 reemplazos congelados == los del borrador de P3b-1", r3 == P.REEMPLAZOS_P3B)
    check("las dos oraciones del FRENO P1 están en el texto (R8 y R14)",
          "emití la Condicion sin condicion_de: no la conectes con otro elemento del chunk." in P.PREFIJO_SISTEMA_R2B
          and "Esto no cambia la Comunicacion: una Comunicación o una norma externa citada sigue siendo una entidad "
              "Comunicacion, con su referencia desde el TextoOrdenado; lo que no emitís es la remisión desde el "
              "contenido." in P.PREFIJO_SISTEMA_R2B
          and "| `referencia` | TextoOrdenado → Comunicacion |" in P.PREFIJO_SISTEMA_R2B)

    print("\n[D] request")
    tos = ("pro", "cla", "ric", "cap", "ext", "ctacte", "lingob", "polcre", "pagjub", "docvig")
    e0r2 = REPO / "data" / "experiment" / "reextraccion_v2" / "e0_chunking" / "salida_tanda0_r2"
    chunks = comun_e1.cargar_chunks(tos, e0_dir=e0r2)
    check("2.434 unidades en la e0-r2 de la tanda 0", len(chunks) == 2434, str(len(chunks)))
    prefijos, deterministas = set(), 0
    for c in chunks:
        a = P.build_request_kwargs_r2b(c, model="m")
        prefijos.add(json.dumps({x: a[x] for x in ("system", "tools", "tool_choice", "max_tokens")}, sort_keys=True,
                                ensure_ascii=False))
        deterministas += a == P.build_request_kwargs_r2b(json.loads(json.dumps(c)), model="m")
    a = P.build_request_kwargs_r2b(chunks[0], model="m")
    check("system: un bloque, cache_control ephemeral al final", len(a["system"]) == 1
          and a["system"][-1]["cache_control"] == {"type": "ephemeral"})
    check("tools = tool schema r2; tool_choice forzado; max_tokens 8.192",
          a["tools"] == [P.TOOL_SCHEMA_R2B] and a["tool_choice"] == {"type": "tool", "name": "extraer_kg_e1"}
          and a["max_tokens"] == 8192)
    check("prefijo idéntico entre las 2.434 unidades", len(prefijos) == 1, str(len(prefijos)))
    check("mismo chunk → mismo request (2.434)", deterministas == 2434, str(deterministas))

    print("\n[E] mensaje igual a los borradores aprobados")
    actual = {c["id"]: P.build_user_message_r2b(c) for c in chunks}
    # El mensaje de P3b-2: la línea de alcance de P1 y la lista de tablas forzadas vacía (P3c-2 solo pasa las líneas
    # fijas a constantes: fuera de esas dos cosas, no cambia un byte).
    alc0, forz0 = P.linea_alcance, P.TABLAS_RESIDUALES_FORZADAS
    try:
        P.linea_alcance, P.TABLAS_RESIDUALES_FORZADAS = MB.linea_alcance, frozenset()
        previo = {c["id"]: P.build_user_message_r2b(c) for c in chunks}
        iguales3 = sum(previo[c["id"]] == MB3.build_user_message_p3b(c) for c in chunks)
    finally:
        P.linea_alcance, P.TABLAS_RESIDUALES_FORZADAS = alc0, forz0
    check("con la línea de alcance de P1 y la lista vacía, mensaje == borrador de P3b-1 en las 2.434 unidades",
          iguales3 == 2434, f"{iguales3}/2434")
    def solo_alcance_y_tablas(a: str, b: str, cid: str) -> bool:
        la, lb = a.split("\n"), b.split("\n")
        if len(la) != len(lb) and cid != "cap::6.2.2.6":
            return False
        if cid == "cap::6.2.2.6":
            return [x for x in la if x.startswith("Alcance de este TO")] != [x for x in lb if x.startswith("Alcance de este TO")]
        dif = [(x, y) for x, y in zip(la, lb) if x != y]
        return all(x.startswith("Alcance de este TO") and y.startswith("Alcance de este TO") for x, y in dif)
    cambia = [c["id"] for c in chunks if actual[c["id"]] != previo[c["id"]]]
    con_rol = [c["id"] for c in chunks if P.ROL_POR_TO_R2.get(c["archivo"]) is not None]
    check("P3c: cambia el mensaje de las unidades con línea de alcance (todas menos docvig), solo en esa línea, y el "
          "de cap::6.2.2.6 además en sus tablas",
          sorted(cambia) == sorted(set(con_rol) | {"cap::6.2.2.6"})
          and all(solo_alcance_y_tablas(actual[x], previo[x], x) for x in cambia), f"{len(cambia)}/{len(con_rol)}")
    cambian = [c for c in chunks if P.es_item(c) or P.mini_a_mitad(c)]
    check("ítems (g) y mini-chunks a mitad de oración (h): 1.053 + 121 = 1.174",
          sum(P.es_item(c) for c in chunks) == 1053 and sum(P.mini_a_mitad(c) for c in chunks) == 121
          and len(cambian) == 1174, f"{len(cambian)}")
    ids_cambian = {c["id"] for c in cambian}
    iguales = sum(previo[c["id"]] == MB.build_user_message_r2(c, v3.ROL_POR_TO_V3, comun_e1.puntos_admitidos,
                                                               comun_e1.es_mini_chunk)
                  for c in chunks if c["id"] not in ids_cambian)
    check("fuera de esos 1.174, el mensaje de P3b-2 == borrador de P1 (1.260)", iguales == 1260, f"{iguales}/1260")
    check("ninguna unidad de la e0-r2 de la tanda 0 lleva herencia_recortada, ni la línea del recorte",
          not any(c.get("herencia_recortada") for c in chunks)
          and not any(P.LINEA_RECORTE in P.build_user_message_r2b(c) for c in chunks))
    c_rec = json.loads(json.dumps(next(c for c in chunks if c.get("herencia"))))
    c_rec["herencia_recortada"] = True
    check("con herencia_recortada, el mensaje lleva la línea del recorte una vez y el prefijo no cambia",
          P.build_user_message_r2b(c_rec).count(P.LINEA_RECORTE) == 1
          and P.build_request_kwargs_r2b(c_rec, model="m")["system"] == P.bloques_sistema_r2b())
    check("tabla de alcance r2 == la v3 en los 71 TOs", P.ROL_POR_TO_R2 == v3.ROL_POR_TO_V3)

    print("\n[F] tablas forzadas a residual")
    c6 = next(c for c in chunks if c["id"] == "cap::6.2.2.6")
    forzado = P.build_user_message_r2b(c6)
    sistema_forzado = P.build_request_kwargs_r2b(c6, model="m")["system"]
    viejo = P.TABLAS_RESIDUALES_FORZADAS
    try:
        P.TABLAS_RESIDUALES_FORZADAS = frozenset()
        normal = P.build_user_message_r2b(c6)
    finally:
        P.TABLAS_RESIDUALES_FORZADAS = viejo
    check("la lista versionada trae cap::tabla037 (alta de P3c, punto f), con motivo y fecha",
          viejo == frozenset({"cap::tabla037"}))
    check("con cap::tabla037 en la lista, el mensaje de cap::6.2.2.6 la declara no confiable; sin ella, confiable",
          forzado != normal and "se tratan como contenido NO-CONFIABLE (`cap::tabla037`)" in forzado
          and "se tratan como contenido NO-CONFIABLE" not in normal)
    check("con la lista, el prefijo no cambia", sistema_forzado == P.bloques_sistema_r2b())
    check("solo cap::6.2.2.6 trae cap::tabla037 en la e0-r2 de la tanda 0",
          [c["id"] for c in chunks if any(t["tabla"] == "cap::tabla037" for t in (c.get("flags") or {}).get("tablas_e0") or [])]
          == ["cap::6.2.2.6"])

    print("\n[G] candado del mensaje (F22 y F22b)")
    fix = json.loads(P.CANDADO_MENSAJE_JSON.read_text(encoding="utf-8"))
    # U-ALCANCE-E1: las dos comprobaciones de la fixture de P3c-2 miran sus 13 primeras unidades (después vienen las
    # cuatro sintéticas del registro de alcance).
    check("la fixture: 12 unidades de salida_tanda0_r2b y una sintética (alcance por clase), declarada, en sus 13 "
          "primeras",
          len(fix["chunks"]) >= 13 and fix["sinteticos"][:1] == [fix["chunks"][12]["id"]]
          and "sintetico" in fix["chunks"][12] and not any("sintetico" in c for c in fix["chunks"][:12])
          and P.ROL_POR_TO_R2[fix["chunks"][12]["archivo"]]["rol_id"] is None)
    check("el sha256 de sus mensajes es el sellado", P.sha256_mensajes(fix["chunks"]) == P.MENSAJE_R2B_SHA256_ESPERADO)
    check("la rama del alcance por clase está en la fixture (sintética)",
          "según corresponda" in P.build_user_message_r2b(fix["chunks"][12]))

    def fixture_suma_registro():
        base = next(c for c in fix["chunks"] if c["id"] == "cap::1.4.1")
        nuevas = fix["chunks"][13:]
        archivos = [c["archivo"] for c in nuevas]
        copias = all({k: v for k, v in c.items() if k not in ("id", "archivo", "sintetico")}
                     == {k: v for k, v in base.items() if k not in ("id", "archivo")} for c in nuevas)
        ok = (len(fix["chunks"]) == 17 and fix["sinteticos"][1:] == [c["id"] for c in nuevas]
              and archivos == ["ri_ccna.pdf", "snp_cheq.pdf", "ri_rml.pdf", "ri_oc.pdf"] and copias
              and all(a in P.REGISTRO_ALCANCE_R2B for a in archivos[:3]) and archivos[3] not in P.REGISTRO_ALCANCE_R2B
              and not any(a in P.ROL_POR_TO_R2 for a in archivos))
        return ok, f"{len(fix['chunks'])} unidades; {archivos}"
    check_protegido("U-ALCANCE-E1: la fixture suma cuatro sintéticas declaradas, copias de cap::1.4.1 con otro archivo: "
                    "una clase, dos clases, rol reutilizado (con entrada en el derivado) y declarado sin alcance (sin "
                    "ella)", fixture_suma_registro)

    def derivado_alterado_frena():
        import copy  # noqa: PLC0415
        orig = P.REGISTRO_ALCANCE_R2B
        frenos = []
        alteraciones = (("ri_ccna.pdf", lambda d: d["ri_ccna.pdf"]["miembros_labels"].pop()),
                        ("snp_cheq.pdf", lambda d: d["snp_cheq.pdf"]["clase_ids"].append("Sujeto_banco")),
                        ("ri_oc.pdf", lambda d: d.__setitem__("ri_oc.pdf", copy.deepcopy(d["ri_ccna.pdf"]))))
        try:
            for nombre, alterar in alteraciones:
                P.REGISTRO_ALCANCE_R2B = copy.deepcopy(orig)
                alterar(P.REGISTRO_ALCANCE_R2B)
                try:
                    P._candado_mensaje()
                    frenos.append((nombre, False))
                except RuntimeError:
                    frenos.append((nombre, True))
        finally:
            P.REGISTRO_ALCANCE_R2B = orig
        P._candado_mensaje()
        return all(f for _, f in frenos) and P.REGISTRO_ALCANCE_R2B is orig, str(frenos)
    check_protegido("U-ALCANCE-E1: una entrada del derivado alterada en memoria (un miembro menos en ri_ccna, un id más "
                    "en snp_cheq) o una entrada para ri_oc hace frenar el candado del mensaje; restaurado, pasa",
                    derivado_alterado_frena)
    frena = []
    for nombre in ("LINEA_CIERRE", "LINEA_ITEM", "LINEA_ALCANCE", "LINEA_MINI_MITAD", "LINEA_HERENCIA_PUNTO",
                   "LINEA_TITULOS_MINI"):
        orig = getattr(P, nombre)
        try:
            setattr(P, nombre, orig + " ")
            try:
                P._candado_mensaje()
                frena.append((nombre, False))
            except RuntimeError:
                frena.append((nombre, True))
        finally:
            setattr(P, nombre, orig)
    check("un espacio más en cualquiera de las seis líneas fijas hace frenar el candado", all(f for _, f in frena),
          str(frena))
    try:
        P.TABLAS_RESIDUALES_FORZADAS = frozenset()
        try:
            P._candado_mensaje()
            sin_lista = False
        except RuntimeError:
            sin_lista = True
    finally:
        P.TABLAS_RESIDUALES_FORZADAS = viejo
    check("sacar cap::tabla037 de la lista hace frenar el candado del mensaje", sin_lista)
    P._candado_mensaje()
    check("restaurado, el candado pasa; el candado no entra al pedido (mismas claves del request, con la temperatura "
          "de P5)",
          set(P.build_request_kwargs_r2b(chunks[0], model="m")) == {"model", "max_tokens", "temperature", "system",
                                                                     "tools", "tool_choice", "messages"})

    print("\n[H] temperatura (P5)")
    temps = {repr(P.build_request_kwargs_r2b(c, model="m")["temperature"]) for c in chunks}
    check("el pedido lleva temperature 0 (TEMPERATURA_E1_R2B, entero) en las 2.434 unidades",
          temps == {"0"} and P.TEMPERATURA_E1_R2B == 0 and type(P.TEMPERATURA_E1_R2B) is int, str(temps))
    check("la temperatura del reintento por salida mal formada es 1 (TEMPERATURA_REINTENTO_FORMA_R2B, entero)",
          P.TEMPERATURA_REINTENTO_FORMA_R2B == 1 and type(P.TEMPERATURA_REINTENTO_FORMA_R2B) is int)
    sin_t = {k: v for k, v in P.build_request_kwargs_r2b(chunks[0], model="m").items() if k != "temperature"}
    check("fuera de la temperatura, el pedido es el de P3c-2: el prefijo y su hash no cambian",
          sin_t["system"] == P.bloques_sistema_r2b() and sin_t["tools"] == [P.TOOL_SCHEMA_R2B]
          and P.PREFIJO_HASH_R2B == "322c5a23e9b7" and sin_t["max_tokens"] == 8192)
    base = P.build_request_kwargs_r2b(chunks[0], model="m")
    con_techo = dict(base, max_tokens=16384)
    rf = P.kwargs_reintento_forma_r2b(con_techo)
    check("kwargs_reintento_forma_r2b: el pedido recibido (con su techo) con temperature 1, sin tocar el recibido",
          rf["temperature"] == 1 and con_techo["temperature"] == 0 and rf["max_tokens"] == 16384
          and {k: v for k, v in rf.items() if k != "temperature"}
          == {k: v for k, v in con_techo.items() if k != "temperature"})

    print("\n[I] registro de alcance por tanda en el mensaje (U-ALCANCE-E1)")
    # El derivado se lee del archivo, no del módulo, para las líneas esperadas: con el código de HEAD, los casos por rama
    # fallan por el mensaje (no lleva la línea), no por un atributo que falta.
    der = json.loads(DERIVADO_REGISTRO.read_text(encoding="utf-8"))
    base = next(c for c in fix["chunks"] if c["id"] == "cap::1.4.1")

    def con_archivo(archivo: str) -> dict:
        c = json.loads(json.dumps(base))
        c["archivo"] = archivo
        return c

    def lineas_alcance(m: str) -> list[str]:
        return [x for x in m.split("\n") if x.startswith("Alcance de este TO")]

    def solo_cambia_la_linea(archivo: str, linea: str) -> bool:
        """El mensaje del documento, sin su línea de alcance, es el de un documento sin alcance (ri_oc) con su nombre."""
        m = P.build_user_message_r2b(con_archivo(archivo))
        sin = P.build_user_message_r2b(con_archivo("ri_oc.pdf")).replace("Documento fuente: ri_oc.pdf",
                                                                        f"Documento fuente: {archivo}")
        return m.count(linea + "\n\n") == 1 and m.replace(linea + "\n\n", "") == sin

    def candado_del_derivado():
        b = P.REGISTRO_ALCANCE_R2B_JSON.read_bytes()
        return (hashlib.sha256(b).hexdigest() == P.REGISTRO_ALCANCE_R2B_SHA256_ESPERADO
                and P.REGISTRO_ALCANCE_R2B == json.loads(b.decode("utf-8"))
                and P.REGISTRO_ALCANCE_R2B_JSON.resolve() == DERIVADO_REGISTRO.resolve()
                and P.REGISTRO_ALCANCE_R2B_JSON.parent.name == "catalogo_unico"), \
            P.REGISTRO_ALCANCE_R2B_SHA256_ESPERADO[:12]
    check_protegido("el derivado del registro (catalogo_unico/registro_alcance_r2b.json, fuera de generados_r2/): sha256 "
                    "esperado, candado del módulo, y es lo que el módulo cargó", candado_del_derivado)

    def generar(tandas: str):
        return subprocess.run([sys.executable, "-B", str(GENERADOR_DERIVADO), "--tandas", tandas, "--salida", "-"],
                              capture_output=True, cwd=REPO, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})

    def regenera():
        # Desde A3, la parte de la tanda 1: sus 10 entradas, las primeras del derivado (el de la tanda final, en el caso
        # de A3, abajo).
        r = generar("1")
        t1 = {a: der[a] for a in list(der)[:len(CON_ALCANCE_TANDA1)]}
        texto_t1 = json.dumps(t1, ensure_ascii=False, indent=1) + "\n"
        return (r.returncode == 0 and r.stdout == texto_t1.encode("utf-8")), \
            f"rc={r.returncode} {r.stderr.decode('utf-8', 'replace')[-300:]}"
    check_protegido("las entradas de la tanda 1, las primeras del derivado, se regeneran byte a byte desde "
                    "registro_alcance_por_tanda.md con el lector de R2-2 (--tandas 1)", regenera)

    def rama_clase():
        e = der["ri_ccna.pdf"]
        linea = P.linea_alcance(e)[0]
        m = P.build_user_message_r2b(con_archivo("ri_ccna.pdf"))
        return (e["rol_id"] == "Sujeto_caja_de_credito" and e["clase_ids"] == ["Sujeto_caja_de_credito"]
                and lineas_alcance(m) == [linea] and "sugerí Sujeto_caja_de_credito en `sujeto_id`" in linea
                and solo_cambia_la_linea("ri_ccna.pdf", linea)), str(lineas_alcance(m))[:160]
    check_protegido("rama de una clase: ri_ccna.pdf lleva la línea de linea_alcance con su entrada del derivado "
                    "(Sujeto_caja_de_credito), una vez, y nada más cambia", rama_clase)

    def rama_dos_clases():
        e = der["snp_cheq.pdf"]
        linea = P.linea_alcance(e)[0]
        m = P.build_user_message_r2b(con_archivo("snp_cheq.pdf"))
        return (e["rol_id"] is None and len(e["clase_ids"]) == 2 and lineas_alcance(m) == [linea]
                and "sugerí Sujeto_entidad_financiera o Sujeto_camara_electronica_de_compensacion en `sujeto_id`, "
                    "según corresponda" in linea
                and solo_cambia_la_linea("snp_cheq.pdf", linea)), str(lineas_alcance(m))[:160]
    check_protegido("rama de dos clases: snp_cheq.pdf lleva la línea con las dos clases («según corresponda»), una vez, y "
                    "nada más cambia", rama_dos_clases)

    def rama_rol():
        linea_ric = P.linea_alcance(P.ROL_POR_TO_R2[ARCHIVO_RIC])[0]
        linea_snp = P.linea_alcance(P.ROL_POR_TO_R2["snp_tr_nc.pdf"])[0]
        ok = all(lineas_alcance(P.build_user_message_r2b(con_archivo(a))) == [linea_ric]
                 and solo_cambia_la_linea(a, linea_ric)
                 for a in ("ri_rml.pdf", "ri_gerc.pdf", "ri_pgn.pdf", "ri_mmsef.pdf"))
        ok = ok and lineas_alcance(P.build_user_message_r2b(con_archivo("snp_tr.pdf"))) == [linea_snp]
        return ok, linea_ric[:100]
    check_protegido("rol reutilizado: ri_rml, ri_gerc, ri_pgn y ri_mmsef llevan la línea del rol de ric "
                    "(Sujeto_rol_entidad_comprendida_reginf) y snp_tr la de snp_tr_nc, y nada más cambia", rama_rol)

    def rama_sin_alcance():
        ok = all(a not in P.REGISTRO_ALCANCE_R2B and a not in P.ROL_POR_TO_R2 and P.alcance_del_documento(a) is None
                 and not lineas_alcance(P.build_user_message_r2b(con_archivo(a))) for a in SIN_ALCANCE_TANDA1)
        return ok, str(SIN_ALCANCE_TANDA1)
    check_protegido("declarado sin alcance: ri_oc, ceninf y cirmo3 no tienen entrada en el derivado, "
                    "alcance_del_documento da None y el mensaje va sin línea", rama_sin_alcance)

    def primero_la_release():
        orig = P.REGISTRO_ALCANCE_R2B
        archivo_cla = "TO_clasificacion_deudores_actual.pdf"
        c_cla = next(c for c in chunks if c["archivo"] == archivo_cla)
        c_doc = next(c for c in chunks if c["archivo"] == "docvig.pdf")
        linea_cla = P.linea_alcance(P.ROL_POR_TO_R2[archivo_cla])[0]
        linea_reg = P.linea_alcance(der["ri_ccna.pdf"])[0]
        try:
            P.REGISTRO_ALCANCE_R2B = {**orig, archivo_cla: der["ri_ccna.pdf"], "docvig.pdf": der["ri_ccna.pdf"]}
            ok = (lineas_alcance(P.build_user_message_r2b(c_cla)) == [linea_cla]
                  and lineas_alcance(P.build_user_message_r2b(c_doc)) == [linea_reg])
        finally:
            P.REGISTRO_ALCANCE_R2B = orig
        return ok and not lineas_alcance(P.build_user_message_r2b(c_doc)), ""
    check_protegido("la regla lee primero la tabla de la release: con un derivado en memoria que también trae cla y "
                    "docvig, cla conserva su línea de la release y docvig toma la del derivado; restaurado, docvig va "
                    "sin línea", primero_la_release)

    def solo_agrega():
        roles = {e["rol_id"]: e for e in P.ROL_POR_TO_R2.values() if e.get("rol_id")}
        formas = {("rol_id", "clase_ids", "label", "miembros_ids", "miembros_labels"),
                  ("rol_id", "label", "miembros_ids", "miembros_labels")}
        reutilizados = [e for e in P.REGISTRO_ALCANCE_R2B.values() if "clase_ids" not in e]
        t1 = list(P.REGISTRO_ALCANCE_R2B)[:len(CON_ALCANCE_TANDA1)]
        ok = (not set(P.REGISTRO_ALCANCE_R2B) & set(P.ROL_POR_TO_R2)
              and t1 == list(CON_ALCANCE_TANDA1)
              and all(tuple(e) in formas for e in P.REGISTRO_ALCANCE_R2B.values())
              and all(roles.get(e["rol_id"]) == e for e in reutilizados)
              and sum("clase_ids" not in P.REGISTRO_ALCANCE_R2B[a] for a in t1) == 5)
        return ok, str(list(P.REGISTRO_ALCANCE_R2B))
    check_protegido("el derivado solo agrega: ningún documento de la tabla de la release; empieza por los 10 de la tanda "
                    "1 con alcance (5 de clase, 5 de rol reutilizado); todas sus entradas con la forma de rol_por_to_r2, "
                    "y las de rol reutilizado iguales a la entrada del rol en la release", solo_agrega)

    def tanda_final():
        # A3: el caso nuevo. Las entradas del derivado que siguen a las 10 de la tanda 1 son las filas con alcance de la
        # tabla «## Tanda final», que entran con --tandas 1,final y no con --tandas 1.
        r_final, r_t1 = generar(TANDAS_DEL_DERIVADO), generar("1")
        if r_final.returncode or r_t1.returncode:
            return False, f"rc={r_final.returncode},{r_t1.returncode} {r_final.stderr.decode('utf-8', 'replace')[-300:]}"
        d = P.REGISTRO_ALCANCE_R2B
        roles = {e["rol_id"]: e for e in P.ROL_POR_TO_R2.values() if e.get("rol_id")}
        nuevas = list(d)[len(CON_ALCANCE_TANDA1):]
        n_clases = [len(d[a]["clase_ids"]) for a in nuevas if "clase_ids" in d[a]]
        reutilizados = [d[a] for a in nuevas if "clase_ids" not in d[a]]
        ramas = (("ri_acsf.pdf", P.ROL_POR_TO_R2[ARCHIVO_RIC], "Sujeto_rol_entidad_comprendida_reginf en `sujeto_id`"),
                 ("cateloc.pdf", d.get("cateloc.pdf"), "sugerí Sujeto_entidad_financiera en `sujeto_id`"),
                 ("reqcac.pdf", d.get("reqcac.pdf"),
                  "sugerí Sujeto_casa_de_cambio o Sujeto_agencia_de_cambio en `sujeto_id`, según corresponda"))
        ok = (r_final.stdout == P.REGISTRO_ALCANCE_R2B_JSON.read_bytes()
              and not set(CON_ALCANCE_TANDA_FINAL) & set(json.loads(r_t1.stdout))
              and nuevas == list(CON_ALCANCE_TANDA_FINAL)
              and n_clases.count(1) == 17 and n_clases.count(2) == 3 and len(reutilizados) == 13
              and all(roles.get(e["rol_id"]) == e and e["rol_id"] == "Sujeto_rol_entidad_comprendida_reginf"
                      for e in reutilizados)
              and all(a not in d and a not in P.ROL_POR_TO_R2 and P.alcance_del_documento(a) is None
                      and not lineas_alcance(P.build_user_message_r2b(con_archivo(a))) for a in SIN_ALCANCE_TANDA_FINAL))
        for archivo, entrada, sugerencia in ramas:
            linea = P.linea_alcance(entrada)[0] if entrada else ""
            ok = (ok and sugerencia in linea and lineas_alcance(P.build_user_message_r2b(con_archivo(archivo))) == [linea]
                  and solo_cambia_la_linea(archivo, linea))
        return ok, f"{len(d)} entradas; {len(nuevas)} después de las de la tanda 1"
    check_protegido("A3: las filas de la tabla «## Tanda final» entran con --tandas 1,final y no con --tandas 1: el "
                    "derivado es byte a byte el de --tandas 1,final; con --tandas 1 no trae ninguna; después de las 10 "
                    "de la tanda 1 vienen las 33 con alcance, en el orden del registro (17 de una clase, 3 de dos y 13 "
                    "de rol reutilizado, el de ric, igual a su entrada en la release); las 13 declaradas sin alcance no "
                    "tienen entrada ni línea; y ri_acsf (rol), cateloc (una clase) y reqcac (dos clases) llevan su línea "
                    "una vez, y nada más cambia", tanda_final)

    def perfil_con_el_derivado():
        import perfil_e1  # noqa: PLC0415 — el perfil que carga el runner (runner_corpus.configurar)
        pf = perfil_e1.perfil("r2b")
        rpt = pf.rol_por_to
        orden = list(P.ROL_POR_TO_R2) + [a for a in der if a not in P.ROL_POR_TO_R2]
        ok = (list(rpt) == orden
              and all(rpt[a] is P.ROL_POR_TO_R2[a] for a in P.ROL_POR_TO_R2)
              and all(rpt[a] == der[a] for a in CON_ALCANCE_TANDA1)
              and all(rpt[a] == P.alcance_del_documento(a) for a in orden)
              and not any(a in rpt for a in SIN_ALCANCE_TANDA1)
              and pf.build_user_message is P.build_user_message_r2b)
        return ok, f"{len(rpt)} entradas; {len(P.ROL_POR_TO_R2)} de la release"
    check_protegido("el perfil r2b (perfil_e1, la tabla que valida el manifiesto) es la tabla de la release seguida de "
                    "las entradas del derivado, con la entrada de alcance_del_documento: la de los 10 de la tanda 1 con "
                    "alcance, y ninguna para los declarados sin alcance", perfil_con_el_derivado)

    def tanda0_igual():
        regla_previa = P.alcance_del_documento
        e0r2b = REPO / "data" / "experiment" / "reextraccion_v2" / "e0_chunking" / "salida_tanda0_r2b"
        chunks_b = comun_e1.cargar_chunks(tos, e0_dir=e0r2b)
        archivos = {c["archivo"] for c in chunks + chunks_b}
        ahora = [P.build_user_message_r2b(c) for c in chunks_b]
        try:
            P.alcance_del_documento = lambda a: P.ROL_POR_TO_R2.get(a)
            antes = [P.build_user_message_r2b(c) for c in chunks_b]
        finally:
            P.alcance_del_documento = regla_previa
        return (len(chunks_b) == 2439 and not archivos & set(P.REGISTRO_ALCANCE_R2B) and ahora == antes), \
            f"{len(chunks_b)} unidades; {sum(a != b for a, b in zip(ahora, antes))} distintas"
    check_protegido("la tanda 0 no cambia: ningún documento de salida_tanda0_r2 ni de salida_tanda0_r2b en el derivado, "
                    "y los mensajes de las 2.439 unidades de salida_tanda0_r2b son los de la regla de antes (solo la "
                    "tabla de la release)", tanda0_igual)

    print(f"\nRESULTADO: {OK} ok, {FAIL} FAIL")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
