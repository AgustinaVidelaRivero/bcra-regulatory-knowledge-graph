"""U-SEG-OFICIAL, S1-bis.1: manifiesto de los 152 TOs en el formato de `manifiesto_corpus` (USD 0, sin API).

Uso: python -B armar_manifiesto_S1bis.py <raíz de una copia del repo> <salida.json>

Copia de `s1/scripts/armar_manifiesto_S1.py` (sellado en S1) con cuatro cambios, todos en el bloque del manifiesto, al
final de `main`: la ruta de salida de E0 (`rutas.e0_salida`, `s1/e0` → `s1bis/e0`), el commit del código de E0
(`sellos.commit_codigo_e0`, `26c6502` → `18d9e05`), el nombre de la etapa en `sellos.unidad` y el comienzo de
`descripcion` (S1-bis, notas al pie hasta `a757b32`). La vía, la clase, el modo de lectura, el sha256 de cada PDF, la
vigencia y el rol de alcance salen igual que en S1: el rol de alcance sigue saliendo del perfil r2b, que trae null en
los 9 documentos con alcance del registro (`catalogo_unico/registro_alcance_por_tanda.md`) porque la corrección del
perfil entra en A2 de U-ALCANCE-E1, después de S2; E0 no lo lee.

Lee, de la copia: la clase de cada TO (`segmentacion_84/b584_particion/particion_152.json`), su modo de lectura
(`conteos_b584.json`, campo `modo_lectura`), la causa de los no segmentables (`adjudicaciones_b584.json`,
`e_no_segmentables`), el sha256 de la descarga (`escalado_prep/descarga_log.json`), las unidades por página de
U-COB-A (`cobertura_bloque_a/chunks_a2.json`), las páginas de norma sin unidad de ri_cc y ri_tsa
(`segmentacion_oficial_e0r2/s0_1/censos/censo_r3b.json`) y el rol de alcance del catálogo del perfil r2b
(`reextraccion_v2/e1_extractor/perfil_e1.py`, fuente única que `manifiesto_corpus.cargar` valida). Calcula el sha256
de cada PDF de `escalado_prep/pdfs/` y lo compara con el de la descarga. La vía de los 14 TOs fuera de las tandas y la
vigencia de manual y ri_ao son las de las enmiendas firmadas a las adendas 1 y 2 del laudo B5.5 (`e82e22f`). No corre E0.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True

ENMIENDAS = "docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md (e82e22f)"
NOMBRE = "segmentacion_oficial_e0r2_152"

# Vía de los TOs que la clase de la partición no decide sola (enmiendas firmadas, e82e22f; nota d59921f)
BLOQUE_A = ("ri_chr", "ri_con", "ri_fcem", "ri_itme", "ri_pfmipyme", "ri_pscpp", "ri_pspii", "ri_rem", "ri_tii")
REFERENCIA = ("optico", "plandecuentas")
# páginas de norma sin unidad (nota al pie del mandato del 05/10/2026, d59921f, decisión 4)
NORMA_SIN_UNIDAD = {"ri_cc": (2, 47), "ri_tsa": (3, 61)}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    raiz, salida = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    ex = raiz / "data/experiment"
    part = json.loads((ex / "segmentacion_84/b584_particion/particion_152.json").read_text(encoding="utf-8"))["por_to"]
    cont = json.loads((ex / "segmentacion_84/b584_particion/conteos_b584.json").read_text(encoding="utf-8"))
    adj = json.loads((ex / "segmentacion_84/b584_particion/adjudicaciones_b584.json").read_text(encoding="utf-8"))
    causa_ns = {e["to"]: e["causa_censo"] for e in adj["e_no_segmentables"]}
    descarga = json.loads((ex / "escalado_prep/descarga_log.json").read_text(encoding="utf-8"))
    a2 = json.loads((ex / "cobertura_bloque_a/chunks_a2.json").read_text(encoding="utf-8"))
    a2_por_to = Counter((c["to"], c["brazo"]) for c in a2)
    r3b = json.loads((ex / "segmentacion_oficial_e0r2/s0_1/censos/censo_r3b.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(ex / "reextraccion_v2/e1_extractor"))
    import perfil_e1
    rol_por_to = perfil_e1.perfil("r2b").rol_por_to

    tos = sorted(part)
    assert len(tos) == 152 and sorted(descarga) == tos, "los 152 de la partición y de la descarga no coinciden"
    filas = []
    for to in tos:
        p, c = part[to], cont[to]
        archivo = f"{to}.pdf"
        pdf = ex / "escalado_prep/pdfs" / archivo
        sha = sha256(pdf)
        rc = rol_por_to.get(archivo)
        rol = None if rc is None else (rc.get("rol_id") or rc.get("clase_ids"))
        t = {"id": to, "archivo": archivo, "pdf": f"data/experiment/escalado_prep/pdfs/{archivo}",
             "sha256_pdf": sha, "sha256_descarga": descarga[to]["sha256"],
             "sha256_igual_a_la_descarga": sha == descarga[to]["sha256"],
             "rol_alcance": rol, "nombres_remision": [],
             "clase": p["clase"], "modo_lectura": c["modo_lectura"], "paginas": p["paginas"],
             "categoria": p["categoria"]}
        if p["clase"] == "reconocido_pleno":
            t["via"] = "por_punto"
            t["fuente_via"] = "e0-r2, escalera de correr_e0.escalera_e0_r2 (esta corrida)"
            if to in NORMA_SIN_UNIDAD:
                ini, fin = NORMA_SIN_UNIDAD[to]
                assert r3b[to]["primer_indice"] - 1 == fin, f"{to}: el censo de S0-1 no da la última página {fin}"
                t["paginas_de_norma_sin_unidad"] = {
                    "paginas": f"{ini}-{fin}",
                    "destino": "vía por página con la tanda 3 (U-BLOQUE-A, docs/plan_tesis.md:772)",
                    "fuente": "nota al pie del mandato del 05/10/2026 (d59921f), decisión 4; "
                              "segmentacion_oficial_e0r2/s0_1/censos/censo_r3b.json"}
        elif to in BLOQUE_A:
            t["via"] = "por_pagina"
            t["fuente_via"] = "U-COB-A, data/experiment/cobertura_bloque_a/chunks_a2.json (074a712); no se regenera"
            t["unidades_por_pagina_u_cob_a"] = {b: n for (tt, b), n in sorted(a2_por_to.items()) if tt == to}
            t["destino"] = (f"prosa con la tanda 3, con procedencia por página; planilla como release posterior "
                            f"(bloque B) ({ENMIENDAS}, Parte II.2, puntos 1 y 4)")
            t["causa_clase"] = causa_ns[to]
        elif to in REFERENCIA:
            t["via"] = "fuera"
            t["causa"] = (f"referencia pura, fuera del recurso ({ENMIENDAS}, Parte II.2, punto 5); "
                          f"causa del censo: {causa_ns[to]}")
        elif to == "ri_spi":
            t["via"] = "por_punto"
            t["fuente_via"] = "e0-r2, escalera de correr_e0.escalera_e0_r2, regla 4 de S0 (marcador de letra y número)"
            t["destino"] = (f"entra por su espina con la tanda 3 si antes cierra su unidad de E0 "
                            f"({ENMIENDAS}, Parte II.2, punto 2)")
            t["causa_clase"] = causa_ns[to]
            t["hallazgo_clase"] = ("la partición lo declara no segmentable; e0-r2 con las reglas de S0 lo segmenta "
                                   "(S0-2: 95 unidades, modo sin_raiz_letra, s0_2/censos/cmp_9f6361e_vs_S0-2.json). "
                                   "La clase queda la declarada; la decisión es de la autora")
        elif to == "manual":
            t["via"] = "fuera"
            t["causa"] = (f"histórico: «Vigente hasta el 31/12/2017», fuera del recurso con sus 2.037 páginas "
                          f"({ENMIENDAS}, Parte III, punto 1); parcial declarado (familia ficha, "
                          f"adjudicaciones_b584.json, d_parser_registro)")
        elif to == "ri2_pm":
            t["via"] = "por_punto"
            t["alcance_via"] = "solo sus unidades por punto (25 en la partición), con la tanda 3"
            t["via_resto"] = {"via": "fuera",
                              "causa": (f"366 páginas (345 de ficha y 21 de cuerpo entre fichas, con sus 2 unidades "
                                        f"que cruzan fichas) como release posterior declarada, bloque B "
                                        f"({ENMIENDAS}, Parte II.2, puntos 3 y 4); parcial declarado (familia "
                                        f"ficha, adjudicaciones_b584.json, d_parser_registro)")}
            t["regla_por_punto"] = ("data/experiment/no_segmentables_limite/l2_regla_parciales.md: una unidad es "
                                    "por punto si ninguna página de ficha_registro cae entre su primera y su "
                                    "última página")
        else:
            raise SystemExit(f"TO sin vía: {to}")
        if to == "manual":
            t["vigencia"] = {"vigente": False, "marca": "Vigente hasta el 31/12/2017",
                             "fuente": f"{ENMIENDAS}, Parte III, punto 1"}
        elif to == "ri_ao":
            t["vigencia"] = {"vigente": False, "marca": "RI Derogado por la Com. A 8262",
                             "fuente": f"{ENMIENDAS}, Parte III, punto 2"}
            t["destino"] = f"fuera del recurso por derogado ({ENMIENDAS}, Parte III, punto 2)"
        else:
            t["vigencia"] = {"vigente": True,
                             "fuente": "sin marca conocida al armar el manifiesto; el censo de vigencia de S1 "
                                       "(punto 5) la controla y una marca nueva se reporta como hallazgo"}
        filas.append(t)

    m = {
        "version": "1",
        "nombre": NOMBRE,
        "descripcion": (
            "U-SEG-OFICIAL, S1-bis.1 (mandato firmado en e543cb2, con sus notas al pie hasta a757b32): los 152 TOs de la "
            "partición (segmentacion_84/b584_particion/particion_152.json), con su clase, su modo de lectura "
            "(conteos_b584.json, campo modo_lectura), su vía (por_punto, por_pagina o fuera), el sha256 del PDF de "
            "escalado_prep/pdfs/ contra el de la descarga (escalado_prep/descarga_log.json) y su vigencia. Es un "
            "manifiesto de E0: USD 0 y sin API; rol_alcance sale del catálogo del perfil r2b porque la carga lo "
            "valida; nombres_remision no se fija acá (lo fija el ensamblado); limites lleva ceros porque no hay "
            "extracción. La vía de los 14 TOs fuera de las tandas y la vigencia de manual y ri_ao son las de las "
            "enmiendas firmadas a las adendas 1 y 2 del laudo B5.5 (e82e22f)."),
        "tos": filas,
        "orden_corrida": tos,
        "perfil_e1": "r2b",
        "rutas": {"e0_salida": "data/experiment/segmentacion_oficial_e0r2/s1bis/e0"},
        "oraculo": {"mapa_territorio": None, "limitaciones_e0": []},
        "limites": {"tope_global_usd": 0.0, "margen_unidad_usd": 0.0,
                    "estimado_usd": {t: {"e1": 0.0, "e3": 0.0} for t in tos},
                    "checkpoint_cada": {}, "chequeos_hits": []},
        "tests_respuesta_conocida": None,
        "sellos": {"unidad": "U-SEG-OFICIAL, S1-bis (mandato firmado en e543cb2)", "commit_codigo_e0": "18d9e05",
                   "version_e0": "e0-r2"},
        "indice_fragmentos": None,
    }
    salida.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    vias = Counter(t["via"] for t in filas)
    print(json.dumps({"tos": len(filas), "clase": Counter(t["clase"] for t in filas),
                      "modo_lectura": Counter(t["modo_lectura"] for t in filas), "via": vias,
                      "sha_igual_a_la_descarga": sum(t["sha256_igual_a_la_descarga"] for t in filas),
                      "con_rol_alcance": sum(t["rol_alcance"] is not None for t in filas),
                      "no_vigentes": [t["id"] for t in filas if not t["vigencia"]["vigente"]]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
