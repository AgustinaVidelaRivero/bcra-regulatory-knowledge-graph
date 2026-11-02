"""4.d de S2 (U-SEG-OFICIAL): las reglas de segmentación vigentes en la E0 corregida, con el lugar del código y los TOs
en los que actúa cada una (solo lectura).

Uso: python -B reglas_por_to_S2.py --e0 <salida de E0 de los 152> --raiz <copia del repo> --ablacion <json> --out <json>

Tres capas:
A. Las 21 reglas de la tabla D3 legada (`reports/u_cap3_datos/u_cap3_datos.py`, `REGLAS_D3` y `CRITERIOS_D3`,
   `:568-645`, y su aplicación, `:749-812`), con el mismo criterio de «usa» sobre la salida de la E0 corregida, en los 152
   (y, en columna aparte, en los 84 del D3 legado, `segmentacion_84/censo_84.json`). Adaptaciones declaradas, por los
   nombres de campo de e0-r2: `conteos.json` no tiene `tabular` ni `preambulo`; los criterios de tablas leen
   `tablas_<to>.json` con `conteos_e0_tablas`, `descartadas_por_regla_e0_tablas` y `tablas` (filtradas a
   `origen == "e0_tablas"`; las de `r_tc2` son otra regla, en la capa B); `parser_tablas` es `conteos_e0_tablas.rinde`;
   las tres reglas de B5.8.2 por ablación (`ablacion_b582_S2.py`), y el índice variante también por ablación (el legado
   lo leía del health-check por TO, que no corre en la salida de e0-r2).
B. Las reglas de e0-r2 (U-R2-CODIGO, U-R2-CODIGO-2 y S0) que dejan rastro en la salida: un tipo de aviso de
   `estructura.avisos`, un motivo de `estructura.rechazos_header` (guardas), una clave de nodo de `estructura`, o un
   agregado (`encabezados_conservados.json`, `ids_desambiguados.json`, `sub_chunking.json`, `correcciones.json`,
   `tablas_<to>.json`, chunks con tabla serializada). El lugar del código es la primera línea de e0_lib.py,
   correr_e0.py o e0_tablas.py donde aparece el literal que la salida registra (para una guarda, el prefijo fijo de su
   motivo). El preámbulo cambió de literal con J de S0-6a: el ancla es la de la línea vigente.
C. Las reglas de S0 de `correr_e0.py` (`REGLAS_S0_3` a `REGLAS_S0_6`) y sus listas de TOs, que no dejan rastro propio:
   su uso por documento no se lee en la salida (pide una ablación por regla, que S2 no corre).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path

E0D = "data/experiment/reextraccion_v2/e0_chunking"
ARCHIVOS = ("e0_lib.py", "correr_e0.py", "e0_tablas.py")
RE_G2 = re.compile(r"^raiz_\d+_no_sucede_a_\d+$")
# capa A: (id, unidad, criterio, anclas: (archivo, literal)) de REGLAS_D3 (u_cap3_datos.py:568-613)
D3 = [
    ("sin_raiz", "B5.8.1", "modo_lectura sin_raiz (o sin_raiz_letra, su variante de S0)",
     [("e0_lib.py", "def roles_para_modo_sin_raiz("), ("e0_lib.py", "if m_num and modo_sin_raiz:")]),
    ("raiz_explicita", "B5.8.1", "≥1 sección sintética con número ≠ '0' y título no vacío",
     [("e0_lib.py", "# raíz EXPLÍCITA: guardas G0-G3")]),
    ("G0", "B5.8.1", "motivo 'raiz_banner_repetido'", [("e0_lib.py", 'motivo_raiz = "raiz_banner_repetido"')]),
    ("G1", "B5.8.1", "motivo 'raiz_sin_forma_de_titulo'", [("e0_lib.py", 'motivo_raiz = "raiz_sin_forma_de_titulo"')]),
    ("G2", "B5.8.1", "motivo 'raiz_<n>_no_sucede_a_<m>'",
     [("e0_lib.py", 'motivo_raiz = f"raiz_{comp_r[0]}_no_sucede_a_{ultima_raiz_num}"')]),
    ("G3", "B5.8.1", "motivo 'raiz_en_columna_profunda_…'", [("e0_lib.py", 'motivo_raiz = (f"raiz_en_columna_profunda_')]),
    ("raiz_implicita", "B5.8.1", "≥1 sección sintética con número ≠ '0' y título vacío",
     [("e0_lib.py", "# raíz IMPLÍCITA en profundidad 2")]),
    ("preambulo", "B5.8.1", "sección sintética con número '0'",
     [("e0_lib.py", 'titulo="" if caratula else "Preámbulo", pagina=pi, sintetica=True')]),
    ("paginas_de_registro", "B5.8.1", "roles_pagina.ficha_registro > 0", [("e0_lib.py", "def marcar_paginas_registro(")]),
    ("marcadores", "B5.8.2", "conteos.marcadores_b582 == true", [("correr_e0.py", "marcadores_b582=True")]),
    ("indice_variante", "B5.8.2", "ablación: anular RE_MARCA_INDICE_B582 cambia el modo o los chunks",
     [("e0_lib.py", "RE_MARCA_INDICE_B582 = re.compile(")]),
    ("seccion_variante", "B5.8.2", "ablación: anular _match_seccion_b582 cambia el modo o los chunks",
     [("e0_lib.py", "def _match_seccion_b582(")]),
    ("banner_caja_mixta", "B5.8.2", "ablación: anular detectar_banners_texto cambia el modo o los chunks",
     [("e0_lib.py", "def detectar_banners_texto(")]),
    ("parser_tablas", "B5.8.3", "tablas_<to>.json: conteos_e0_tablas.rinde == true", [("e0_tablas.py", "def parsear_to(")]),
    ("R-TC", "B5.8.3", "conteos_e0_tablas.tablas_logicas > 0", [("e0_tablas.py", "def clasificar_tabla_contenido(")]),
    ("R-TC sin_contenido", "B5.8.3", "descartadas_por_regla_e0_tablas.conteos.sin_contenido > 0",
     [("e0_tablas.py", 'es_tc, motivo = False, "sin_contenido"')]),
    ("R-COL", "B5.8.3", "≥1 tabla de e0_tablas con causa 'alineacion_no_confiable'", [("e0_tablas.py", "def detectar_colapso(")]),
    ("R-COSTURA", "B5.8.3", "conteos_e0_tablas.costuras_aplicadas > 0", [("e0_tablas.py", "def _match_costura(")]),
    ("R-ENC", "B5.8.3", "≥1 tabla de e0_tablas con encabezado.estado ≠ 'no_determinado'",
     [("e0_tablas.py", "def detectar_encabezado(")]),
    ("R-VERIF", "B5.8.3", "≥1 tabla de e0_tablas con causa 'perdida_reconstruccion'",
     [("e0_tablas.py", "def verificar_reconstruccion(")]),
    ("R-NOTA", "B5.8.3", "conteos_e0_tablas.notas_pie > 0", [("e0_tablas.py", "def notas_al_pie(")]),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--raiz", type=Path, required=True)
    ap.add_argument("--ablacion", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    fuentes = {n: (a.raiz / E0D / n).read_text(encoding="utf-8").split("\n") for n in ARCHIVOS}

    def ancla(archivo: str, literal: str) -> str | None:
        for i, l in enumerate(fuentes[archivo], 1):
            if literal in l:
                return f"{E0D}/{archivo}:{i}"
        return None

    def ancla_cualquiera(literal: str) -> str | None:
        for n in ARCHIVOS:
            x = ancla(n, literal)
            if x:
                return x
        return None

    conteos = json.loads((a.e0 / "conteos.json").read_text(encoding="utf-8"))
    abl = json.loads(a.ablacion.read_text(encoding="utf-8"))
    tos84 = set(json.loads((a.raiz / "data/experiment/segmentacion_84/censo_84.json").read_text(encoding="utf-8")))
    assert len(tos84) == 84, len(tos84)
    leg_d3 = {}
    p_leg = a.raiz / "reports/u_cap3_datos/datos.json"
    if p_leg.exists():
        leg_d3 = {r["id"]: r["n_documentos"] for r in json.loads(p_leg.read_text(encoding="utf-8"))["D3"]["reglas"]}
    tos = sorted(conteos)
    usa = defaultdict(set)
    avisos, rechazos, nodos, agregados = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    for t in tos:
        c = conteos[t]
        est = json.loads((a.e0 / f"estructura_{t}.json").read_text(encoding="utf-8"))
        tj = json.loads((a.e0 / f"tablas_{t}.json").read_text(encoding="utf-8"))
        sint = [s for s in est["secciones"] if s.get("sintetica")]
        motivos = [r["motivo"] for r in est.get("rechazos_header", [])]
        if (c.get("modo_lectura") or "").startswith("sin_raiz"):
            usa["sin_raiz"].add(t)
        if any(s["numero"] != "0" and s["titulo"] != "" for s in sint):
            usa["raiz_explicita"].add(t)
        if any(s["numero"] != "0" and s["titulo"] == "" for s in sint):
            usa["raiz_implicita"].add(t)
        if any(s["numero"] == "0" for s in sint):
            usa["preambulo"].add(t)
        if "raiz_banner_repetido" in motivos:
            usa["G0"].add(t)
        if "raiz_sin_forma_de_titulo" in motivos:
            usa["G1"].add(t)
        if any(RE_G2.match(m) for m in motivos):
            usa["G2"].add(t)
        if any(m.startswith("raiz_en_columna_profunda_") for m in motivos):
            usa["G3"].add(t)
        if c["roles_pagina"].get("ficha_registro", 0) > 0:
            usa["paginas_de_registro"].add(t)
        if c.get("marcadores_b582"):
            usa["marcadores"].add(t)
        ct = tj["conteos_e0_tablas"]
        tl = [x for x in tj["tablas"] if x["origen"] == "e0_tablas"]
        if ct.get("rinde"):
            usa["parser_tablas"].add(t)
        if ct["tablas_logicas"] > 0:
            usa["R-TC"].add(t)
        if tj["descartadas_por_regla_e0_tablas"]["conteos"].get("sin_contenido", 0) > 0:
            usa["R-TC sin_contenido"].add(t)
        if any("alineacion_no_confiable" in x["causas"] for x in tl):
            usa["R-COL"].add(t)
        if ct["costuras_aplicadas"] > 0:
            usa["R-COSTURA"].add(t)
        if any(x["encabezado"]["estado"] != "no_determinado" for x in tl):
            usa["R-ENC"].add(t)
        if any("perdida_reconstruccion" in x["causas"] for x in tl):
            usa["R-VERIF"].add(t)
        if ct["notas_pie"] > 0:
            usa["R-NOTA"].add(t)
        # capa B
        for x in est["avisos"]:
            avisos[x["tipo"]].add(t)
        for m in motivos:
            rechazos[re.sub(r"\d+", "<n>", m)].add(t)

        def rec(n: dict) -> None:
            for k in ("prefijo", "apartado", "division_a", "numero_impreso", "lineas_previas"):
                if n.get(k):
                    nodos[k].add(t)
            for h in n.get("hijos", []):
                rec(h)
        for s in est["secciones"]:
            rec(s)
        if est.get("subdocumentos"):
            nodos["subdocumentos"].add(t)
        if any(x["origen"] == "r_tc2" for x in tj["tablas"]):
            agregados["R-TC2 (tablas de origen r_tc2)"].add(t)
        ch = json.loads((a.e0 / f"chunks_{t}.json").read_text(encoding="utf-8"))
        if any(any(y.get("serializada") for y in (c_.get("flags", {}).get("tablas_e0") or [])) for c_ in ch):
            agregados["serializacion de tablas (chunks con flags.tablas_e0[].serializada)"].add(t)
        if c.get("reasignaciones_continuidad"):
            agregados["regla 1 (continuidad de enumeración; conteos.reasignaciones_continuidad > 0)"].add(t)
        if c.get("lineas_corridas_por_frontera"):
            agregados["regla 2 (fronteras intra-palabra; conteos.lineas_corridas_por_frontera > 0)"].add(t)
    for v, k in (("indice", "indice_variante"), ("seccion", "seccion_variante"), ("banner", "banner_caja_mixta")):
        usa[k] = set(abl["usa"][v])
    for nombre, clave in (("K (encabezados_conservados.json)", "encabezados_conservados.json"),
                          ("L (ids_desambiguados.json)", "ids_desambiguados.json")):
        d = json.loads((a.e0 / clave).read_text(encoding="utf-8")) if (a.e0 / clave).exists() else {}
        agregados[nombre] = {t for t, v in d.items() if v}
    sub = json.loads((a.e0 / "sub_chunking.json").read_text(encoding="utf-8"))
    agregados["C8 partición por tamaño (sub_chunking.json, particiones)"] = {t for t, v in sub.items() if v.get("particiones")}
    agregados["C8 sin partir (sub_chunking.json, no_particionables)"] = {t for t, v in sub.items() if v.get("no_particionables")}
    for k in ("regla 1 (continuidad de enumeración; conteos.reasignaciones_continuidad > 0)",
              "regla 2 (fronteras intra-palabra; conteos.lineas_corridas_por_frontera > 0)"):
        agregados.setdefault(k, set())

    anclas_agregados = {
        "K (encabezados_conservados.json)": ancla("correr_e0.py", "def lineas_conservadas_k("),
        "L (ids_desambiguados.json)": ancla("e0_lib.py", "def desambiguar_ids("),
        "C8 partición por tamaño (sub_chunking.json, particiones)": ancla("correr_e0.py", "def subdividir_unidades_grandes("),
        "C8 sin partir (sub_chunking.json, no_particionables)": ancla("correr_e0.py", '"no_particionables"'),
        "R-TC2 (tablas de origen r_tc2)": ancla_cualquiera('"r_tc2"'),
        "serializacion de tablas (chunks con flags.tablas_e0[].serializada)": ancla_cualquiera('"tablas_e0"'),
        "regla 1 (continuidad de enumeración; conteos.reasignaciones_continuidad > 0)":
            ancla("e0_lib.py", "def aplicar_continuidad_enumeracion("),
        "regla 2 (fronteras intra-palabra; conteos.lineas_corridas_por_frontera > 0)":
            ancla("e0_lib.py", "def corregir_fronteras_intra_palabra("),
    }

    def fila(k, ts, **x):
        ts = sorted(ts)
        return {"regla": k, **x, "tos": len(ts), "tos_en_los_84": len([t for t in ts if t in tos84]), "lista": ts}

    capa_a = [fila(rid, sorted(usa[rid]), unidad=u, criterio=cr,
                   codigo=[ancla(f, lit) for f, lit in anc], legado_n_en_los_84=leg_d3.get(rid)) for rid, u, cr, anc in D3]
    capa_b = ([fila(k, v, origen="aviso", codigo=ancla_cualquiera(f'"{k}"')) for k, v in sorted(avisos.items())]
              + [fila(k, v, origen="guarda (rechazos_header)",
                      codigo=ancla_cualquiera(re.split(r"<n>|[IVX]+$", k)[0] or k)) for k, v in sorted(rechazos.items())]
              + [fila(k, v, origen="clave de nodo de estructura", codigo=ancla("e0_lib.py", f'd["{k}"]')
                      or ancla_cualquiera(f'"{k}"')) for k, v in sorted(nodos.items())]
              + [fila(k, v, origen="agregado", codigo=anclas_agregados.get(k)) for k, v in sorted(agregados.items())])
    capa_c = []
    for conjunto in ("REGLAS_S0_3", "REGLAS_S0_4", "REGLAS_S0_5", "REGLAS_S0_6"):
        capa_c.append({"conjunto": conjunto, "codigo": ancla("correr_e0.py", f"{conjunto} = frozenset("),
                       "uso_por_documento": "no medible en la salida (pide ablación por regla; S2 no la corre)"})
    listas_tos = {}
    for i, l in enumerate(fuentes["correr_e0.py"], 1):
        m = re.match(r"^(TOS_[A-Z0-9_]+) = frozenset\(\{(.*)\}\)", l)
        if m:
            listas_tos[m.group(1)] = {"codigo": f"{E0D}/correr_e0.py:{i}", "tos": sorted(re.findall(r'"([a-z0-9_]+)"', m.group(2)))}
    out = {"codigo_sha256": {n: sha(a.raiz / E0D / n) for n in ARCHIVOS}, "e0_conteos_sha256": sha(a.e0 / "conteos.json"),
           "ablacion_sha256": sha(a.ablacion), "capa_a_D3": capa_a, "capa_b_rastro_en_la_salida": capa_b,
           "capa_c_sin_rastro": capa_c, "listas_de_tos_del_codigo": listas_tos}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for f in capa_a:
        print("A", f["regla"], f["tos"], f["tos_en_los_84"], f["legado_n_en_los_84"], f["codigo"])
    print("B", len(capa_b), "reglas;", sum(1 for f in capa_b if not f["codigo"]), "sin ancla:",
          [f["regla"] for f in capa_b if not f["codigo"]])


if __name__ == "__main__":
    main()
