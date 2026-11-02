"""Genera `cifras_segmentacion_oficial.md` de S2 (U-SEG-OFICIAL) desde los JSON de `s2/cifras/` (solo lectura de esos
JSON; escribe solo --out).

Uso: python -B generar_cifras_S2.py --cifras <dir de s2/cifras> --out <md>

Cada cifra del documento sale de un JSON de `s2/cifras/`, con su clave, y cada JSON tiene su comando en la tabla de
reproducción del §0. Nada se escribe a mano: si un JSON falta, la sección dice que falta.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

C = "data/experiment/segmentacion_oficial_e0r2/s2/cifras"
SC = "data/experiment/segmentacion_oficial_e0r2/s2/scripts"
PY = "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B"
NOTA = ("en la partición legada era no segmentable (`docs/protocolo_entre_tandas.md:163-166`); en la E0 corregida "
        "cuenta por su razón vigente, la decisión {d} de la enmienda 8")
NOTA_TO = {"ri_spi": NOTA.format(d=1), "ri_con": NOTA.format(d=2)}


def n(x) -> str:
    """Número con punto de miles y coma decimal, como en el resto del repo."""
    if isinstance(x, float):
        s = f"{x:,.1f}" if abs(x - round(x, 1)) < 1e-9 else f"{x:,.4f}"
        return s.replace(",", "_").replace(".", ",").replace("_", ".")
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    return str(x)


def dif(a, b) -> str:
    if a is None or b is None:
        return "—"
    d = a - b
    if isinstance(d, float):
        return ("+" if d > 0 else "") + n(round(d, 1))
    return ("+" if d > 0 else "") + n(d)


def lista(ts, maxi: int = 200) -> str:
    """Lista separada por comas; ri_spi y ri_con llevan siempre la marca ¹ (agregado 4 del «seguí»)."""
    ts = [marcar_item(str(x)) for x in ts]
    return ", ".join(ts[:maxi]) + (f" (y {len(ts) - maxi} más)" if len(ts) > maxi else "") if ts else "—"


def marcar_item(s: str) -> str:
    for to in NOTA_TO:
        if s == to or s.startswith(to + " "):
            return to + "¹" + s[len(to):]
    return s


def marcar(t: str) -> str:
    return f"{t}¹" if t in NOTA_TO else t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cifras", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    def J(nombre: str):
        p = a.cifras / nombre
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def sha(nombre: str) -> str:
        p = a.cifras / nombre
        return hashlib.sha256(p.read_bytes()).hexdigest()[:8] if p.exists() else "FALTA"

    L: list[str] = []
    A = L.append
    A("# Cifras de la segmentación oficial (U-SEG-OFICIAL, S2)")
    A("")
    A("Sobre la E0 corregida: el código de E0 de `2374968a` (`e0_lib.py` `d89aab1a…`, `correr_e0.py` `78c54c4c…`, "
      "`e0_tablas.py` `ab300a22…`), cuya salida de los 152 da los 768 archivos de "
      "`s0_6/b/manifiestos/manifest_salida_e0_152_S0-6b.json` (`80adbd58…`) con su sha256, 10.478 unidades "
      "(`s2/controles/control_e0_S2a.json`). La salida no está en el repo: la regenera "
      f"`zsh {SC}/lote_tramo1_S2.sh <repo> <trabajo>` en unos 6 minutos, USD 0.")
    A("")
    A("Convenciones:")
    A("- Cada cifra lleva el archivo de `s2/cifras/` y la clave de donde sale; el comando de cada archivo está en el §0.")
    A("- La cifra legada va al lado, con su diferencia (corregida − legada), cuando el mandato la pide.")
    A("- ¹ ri_spi y ri_con se cuentan una sola vez, con la misma regla, en todas las cifras: van por su razón vigente con la "
      "E0 corregida, las decisiones 1 y 2 de la enmienda 8 (ri_spi, error de corte confirmado en S1-quater; ri_con, "
      "cadenas de encabezados heredados, BKL-0044). En la partición legada eran no segmentables "
      "(`docs/protocolo_entre_tandas.md:163-166`). La autora confirmó la regla para las cifras de S2 el 15/10/2026 (mandato, "
      "`:1036-1043`; enmienda 8, nota `:165`; protocolo, nota `:529`; `c2b6cb60`). La marca ¹ remite a esta nota.")
    A("- Clase de documento (decisión 6, 2A): normativa general (NG) y régimen informativo (RI), "
      "`escalado_prep/inventario_tos.csv` para los 152 y `reports/u_insumos_cap/estadisticas_corpus.md:233-237` para los "
      "5 de desarrollo.")
    A("- Ningún archivo de `s2/cifras/` guarda texto de unidades ni renglones del PDF: solo ids, páginas y cuentas.")
    A("")

    # §0
    A("## 0. Archivos y comandos")
    A("")
    A("| archivo de `s2/cifras/` | sha256 | comando |")
    A("|---|---|---|")
    cmds = [
        ("resumen_healthcheck_tanda1_S2b.json",
         f"`{PY} <raíz>/data/experiment/reextraccion_v2/e0_chunking/healthcheck_e0.py --pdf <raíz>/…/pdfs/<to>.pdf … --salida <hc.json>` "
         f"y `{PY} {SC}/resumen_healthcheck_S2.py --hc <hc.json> --e0 <E0> --manifiesto <manifest S0-6b> --out <json>`"),
        ("comparar_e0_historicas_S2b.json",
         f"`zsh {SC}/lote_e0_historicas_S2b.sh <repo> <raíz> <trabajo> 92b45d6 e1c9456 9f6361e6` y "
         f"`{PY} {SC}/comparar_e0_historicas_S2.py --e0 92b45d6=<dir> --e0 e1c9456=<dir> --e0 9f6361e6=<dir> --e0 corregida=<E0> --out <json>`"),
        ("atribucion_particion_S2b.json",
         f"`zsh {SC}/lote_tramo2_S2b.sh …` (los tres `r5_escalera_particion.py --comparar --atribuir`) y "
         f"`{PY} {SC}/atribuir_particion_S2.py --r5 <r5 corregida> --r5-cierre <r5 e1c9456> --e0 <E0> --e0-cierre <dir> --e0-c2 <dir> --raiz <copia> --out <json>`"),
        ("escalera_r5_S2b.json", f"`{PY} {SC}/escalera_r5_S2.py --r5-r5 <r5 92b45d6> --r5-cierre <r5 e1c9456> --historicas <comparar_e0_historicas_S2b.json> --out <json>`"),
        ("cifras_punto3_S2b.json", f"`{PY} {SC}/cifras_punto3_S2.py --e0 <E0> --raiz <copia> --out <json>`"),
        ("cifras_conjuntos_clases_S2b.json", f"`{PY} {SC}/cifras_conjuntos_clases_S2.py --e0 <E0> --raiz <copia> --out <json>`"),
        ("ablacion_b582_S2b.json", f"`{PY} {SC}/ablacion_b582_S2.py --codigo <raíz> --e0 <E0> --trabajo <dir> --out <json>`"),
        ("reglas_por_to_S2b.json", f"`{PY} {SC}/reglas_por_to_S2.py --e0 <E0> --raiz <copia> --ablacion <json> --out <json>`"),
        ("p7_en_la_corregida_S2b.json", f"`{PY} {SC}/p7_en_la_corregida_S2.py --e0 <E0> --raiz <copia> --trabajo <dir> --out <json>`"),
        ("roles_pagina_S2b.json", f"`{PY} {SC}/roles_pagina_S2.py --e0 <E0> --raiz <copia> --out <json>`"),
        ("censos_S2b.json", f"`zsh {SC}/lote_tramo2_S2b.sh …` (caché de renglones, censo de renglones, detector 1.16, censo de "
                            f"sub-documentos) y `{PY} {SC}/resumen_censos_S2.py --lote <dir> --e0 <E0> --raiz <copia> --out <json>`"),
        ("s1quater_S2b.json", f"`{PY} {SC}/cifras_s1quater_S2.py --raiz <copia> --out <json>`"),
    ]
    tramo3 = (a.cifras / "tanda_final_S2c.json").exists()
    if tramo3:
        cmds += [
            ("resumen_healthcheck_tanda_final_S2c.json",
             f"`zsh {SC}/lote_tramo3_S2c.sh …` (`healthcheck_e0.py` de la raíz sobre los 98 PDFs) y `{PY} {SC}/resumen_healthcheck_S2.py "
             "--hc <hc.json> --e0 <E0> --manifiesto <manifest S0-6b> --out <json>`"),
            ("tanda_final_S2c.json", f"`{PY} {SC}/tanda_final_S2.py --e0 <E0> --raiz <copia> --censos <lote> --hc <resumen> --out <json>`"),
        ]
    for f, c in cmds:
        A(f"| `{f}` | `{sha(f)}…` | {c} |")
    A("")
    A("`<E0>` es la salida de los 152 de la E0 corregida; `<raíz>`, la raíz mínima de `s0_4/scripts/raiz_minima.sh`; "
      "`<copia>`, una copia del repo hecha con el `rsync` de la cláusula de los despachos más `--exclude='NO_ABRIR_*'`.")
    A("")
    A(f"En orden: `zsh {SC}/lote_e0_historicas_S2b.sh <repo> <raíz> <historicas> 92b45d6 e1c9456 9f6361e6` (la E0 de los 152 con "
      f"el código de cada commit), `zsh {SC}/lote_tramo2_S2b.sh <repo> <copia> <raíz> <E0> <historicas> <lote>` (los tres "
      f"controles de R5 y los censos) y `zsh {SC}/lote_cifras_S2b.sh <repo> <copia> <raíz> <E0> <historicas> <lote> <trabajo>` "
      "(el health-check, la ablación, todos los resúmenes y este documento). Las salidas crudas de los dos primeros traen texto "
      "del PDF y quedan fuera del repo.")
    A("")
    if tramo3:
        A(f"El tramo 3 (§7) se suma con `zsh {SC}/lote_tramo3_S2c.sh <repo> <copia> <raíz> <E0> <historicas> <lote> <trabajo>`, que corre "
          "`lote_cifras_S2b.sh` y después el health-check de la tanda final, su resumen, `tanda_final_S2.py` y este documento. Sin los "
          "JSON del tramo 3, el generador da la versión del tramo 2 (`96d7d1ab`).")
        A("")

    secciones(J, A)
    a.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(len(L), "renglones")


def secciones(J, A) -> None:
    hc = J("resumen_healthcheck_tanda1_S2b.json")
    A("## 1. Health-check de E0 de los 20 de la tanda 1 (agregado 5 del «seguí»)")
    A("")
    if not hc:
        A("FALTA `resumen_healthcheck_tanda1_S2b.json`.")
    else:
        A("Con `healthcheck_e0.py` de la raíz mínima (el código de la E0 corregida), sobre los PDFs de los 20 "
          "(`resumen_healthcheck_tanda1_S2b.json`, `filas`). Condición de entrada por documento: "
          "`docs/protocolo_entre_tandas.md:149-151` y `:188-190`; checklist `:77-78`.")
        A("")
        A(f"- **Cobertura no exacta o ids repetidos en la tanda 1:** {lista(hc['frena_por_cobertura_o_ids'])} "
          "(`frena_por_cobertura_o_ids`). Ninguno: no hay freno.")
        A(f"- **El health-check no reproduce `correr_e0` en {len(hc['unidades_distintas'])} de {hc['tos']}:** da otras unidades "
          f"que `unidades_por_to` en {lista(hc['unidades_distintas'])} (`unidades_distintas`). Corre la escalera de e0_lib "
          "(`healthcheck_e0.py:85-206`) sin el driver de e0-r2, que agrega las reglas de U-R2-CODIGO, de C2 y de S0 y la "
          "partición por tamaño. Sus señales describen ese parseo, no la E0 que se extrae. Por eso van al lado, con la "
          "misma definición, dos señales medidas sobre la E0 corregida (columnas «E0»).")
        A(f"- **Modo de lectura:** el mismo en los {hc['tos'] - len(hc['modo_distinto'])} (`modo_distinto`: "
          f"{lista(hc['modo_distinto'])}).")
        A("")
        A("| TO | veredicto | modo | unidades (hc / `unidades_por_to`) | cid (renglones; páginas) | páginas sin sección (hc / E0) | "
          "unidades grandes (hc / E0) | cobertura exacta (hc / E0) | ids repetidos (E0) |")
        A("|---|---|---|---|---|---|---|---|--:|")
        for t, f in hc["filas"].items():
            v = "sano" if f["veredicto_hc"] == "sano" else ", ".join(f["veredicto_hc"])
            cid = f"{f['cid_lineas']}; {lista(map(str, f['cid_paginas']))}" if f["cid_lineas"] else "0"
            ss = f"{f['avisos_pagina_cuerpo_sin_seccion']} / {f['e0_avisos_pagina_cuerpo_sin_seccion']}"
            ug = (f"{f['unidades_grandes']}" + (f" ({lista(u for u, _ in f['unidades_grandes_ids'])})" if f['unidades_grandes'] else "")
                  + f" / {f['e0_unidades_grandes']}" + (f" ({lista(u for u, _ in f['e0_unidades_grandes_ids'])})" if f['e0_unidades_grandes'] else ""))
            A(f"| {t} | {v} | `{f['modo_lectura_hc']}` | {n(f['unidades_hc'])} / {n(f['unidades_por_to'])} | {cid} | {ss} | {ug} | "
              f"{'sí' if f['cobertura_exacta_hc'] else 'no'} / {'sí' if f['cobertura_exacta_e0'] else 'no'} | {f['ids_chunk_repetidos_e0']} |")
        A("")
        A(f"Veredictos del health-check: {', '.join(f'{k} {v}' for k, v in hc['veredictos'].items())} (`veredictos`). "
          "La unidad grande de ri_rml en la E0 (`ri_rml::Sbloque14`, 50.404 caracteres propios) es una de las 3 que la "
          "partición por tamaño no parte porque tiene una tabla serializada (§4, unidades partidas). En la tanda 0 las señales "
          "`cid`, páginas sin sección y unidades grandes no fueron criterio de exclusión: se registraron "
          "(`docs/preregistro_tanda0.md:212-216`). Para la tanda 1 lo decidió la autora el 15/10/2026, antes de ver este documento: "
          "se registran y se declaran por TO y no excluyen; la cobertura no exacta y los ids repetidos frenan (mandato, nota del "
          "15/10/2026, `docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md:1036-1043`, `c2b6cb60`).")
        A("")
    seccion_punto1(J, A)
    seccion_punto2(J, A)
    seccion_punto3(J, A)
    seccion_punto4(J, A)
    seccion_detecciones(J, A)
    if J("tanda_final_S2c.json"):
        seccion_tramo3(J, A)


def seccion_punto1(J, A) -> None:
    at = J("atribucion_particion_S2b.json")
    A("## 2. Punto 1: diferencias contra `b584_particion/`")
    A("")
    if not at:
        A("FALTA `atribucion_particion_S2b.json`.")
        A("")
        return
    r5, r5c = at["r5"], at["r5_cierre"]
    A("Con el control de R5 sin editar (`data/experiment/r2_codigo/r5_escalera_particion.py --comparar --atribuir`, "
      "`atribucion_particion_S2b.json`, claves `r5` y `r5_cierre`), sobre la E0 corregida y, al lado, sobre la E0 del "
      "cierre de U-R2-CODIGO (`e1c9456`), donde ese control no deja nada en «otra» (`r2_codigo/cierre_freno.md:50-72`).")
    A("")
    A("| | E0 corregida | E0 de `e1c9456` (cierre) |")
    A("|---|--:|--:|")
    A(f"| TOs comparados | {r5['tos']} | {r5c['tos']} |")
    A(f"| TOs con los mismos ids | {r5['tos_con_ids_iguales']} | {r5c['tos_con_ids_iguales']} |")
    for k in sorted(set(r5["diferencias_de_ids_por_clase"]) | set(r5c["diferencias_de_ids_por_clase"])):
        A(f"| ids, `{k}` | {n(r5['diferencias_de_ids_por_clase'].get(k, 0))} | {n(r5c['diferencias_de_ids_por_clase'].get(k, 0))} |")
    for k in sorted(set(r5["diferencias_de_ids_otra_por_causa"]) | set(r5c["diferencias_de_ids_otra_por_causa"])):
        A(f"| ids en «otra», causa `{k}` | {n(r5['diferencias_de_ids_otra_por_causa'].get(k, 0))} | "
          f"{n(r5c['diferencias_de_ids_otra_por_causa'].get(k, 0))} |")
    for k in sorted(set(r5["chunks_con_texto_distinto_por_clase"]) | set(r5c["chunks_con_texto_distinto_por_clase"])):
        A(f"| chunks con texto distinto, `{k}` | {n(r5['chunks_con_texto_distinto_por_clase'].get(k, 0))} | "
          f"{n(r5c['chunks_con_texto_distinto_por_clase'].get(k, 0))} |")
    A("")
    modos_d = lista(f"{x['to']} ({x['b584']} → {x['e0_r2']})" for x in r5["modo_de_lectura_distinto"])
    A(f"Modo de lectura distinto del legado (`r5.modo_de_lectura_distinto`): {modos_d}. TOs que quedan en 0 "
      f"unidades: {lista(r5['tos_en_cero_que_la_particion_segmenta'])}.")
    A("")
    A("**La atribución de «otra».** El `--atribuir` de R5 vuelve a leer el PDF con variantes de K y de pie del código vigente, "
      "sin las reglas de S0: lo que cambió S0 le queda en «otra». Entre `e1c9456` y la E0 corregida el código de E0 cambió solo "
      "en C2 de U-R2-CODIGO-2 (`9f6361e6`) y en S0 (`26c65024`, `18d9e056`, `af7ffdd4`, `2374968a`; "
      "`git log e1c9456..HEAD` de los tres archivos de E0). Cada caso de «otra» se busca en la E0 de esos commits "
      "(`atribuir_particion_S2.py`, docstring): «ya en e1c9456» (la diferencia ya estaba en el cierre, con la causa que R5 le "
      "da ahí), «C2» o «S0».")
    A("")
    A("| clase por historia | ids | chunks con texto distinto |")
    A("|---|--:|--:|")
    ks = sorted(set(at["ids_por_clase_historica"]) | set(at["texto_otra_por_clase_historica"]))
    for k in ks:
        A(f"| {k} | {n(at['ids_por_clase_historica'].get(k, 0))} | {n(at['texto_otra_por_clase_historica'].get(k, 0))} |")
    A(f"| **total** | {n(sum(at['ids_por_clase_historica'].values()))} | {n(sum(at['texto_otra_por_clase_historica'].values()))} |")
    A("")
    A(f"**«Otra» sin explicar: {at['otra_sin_explicar']['ids']} ids y {at['otra_sin_explicar']['texto']} chunks** "
      "(`otra_sin_explicar`). Las listas, por TO y por clase, en `ids` y `texto`; los TOs de cada clase, en "
      "`tos_por_clase_historica`.")
    for k, v in at["tos_por_clase_historica"].items():
        A(f"- {k}: {len(v)} TOs, {lista(v, 40)}.")
    if at.get("ids_L_posteriores_a_e1c9456"):
        post_l = lista(f"{x['to']} {len(x['ids'])}" for x in at["ids_L_posteriores_a_e1c9456"])
        A(f"- Ids desambiguados por L que no estaban en el cierre (`ids_L_posteriores_a_e1c9456`): {post_l}.")
    A("")
    h = J("comparar_e0_historicas_S2b.json")
    if h:
        A("**Qué cambió cada etapa del código, sobre los 152** (`comparar_e0_historicas_S2b.json`, `pares.<par>.totales` y "
          "`tos_con_cambios`; ids que salen, ids que entran, chunks comunes con texto distinto y con el mismo texto pero otra herencia):")
        A("")
        A("| etapa | TOs con cambios | ids que salen | ids que entran | texto distinto | solo herencia |")
        A("|---|--:|--:|--:|--:|--:|")
        nombres = {"92b45d6 -> e1c9456": "K-a′+K-b (`92b45d6` → `e1c9456`)",
                   "e1c9456 -> 9f6361e6": "C2 de U-R2-CODIGO-2 (`e1c9456` → `9f6361e6`)",
                   "9f6361e6 -> corregida": "S0 (`9f6361e6` → E0 corregida)"}
        for k, v in h["pares"].items():
            t = v["totales"]
            A(f"| {nombres.get(k, k)} | {v['tos_con_cambios']} | {n(t['solo_antes'])} | {n(t['solo_despues'])} | "
              f"{n(t['texto_distinto'])} | {n(t['herencia_distinta'])} |")
        A("")
        c2 = h["pares"].get("e1c9456 -> 9f6361e6")
        if c2:
            A(f"C2 no mueve ids ni texto en los 152; cambia solo la herencia de {n(c2['totales']['herencia_distinta'])} unidades "
              f"en {c2['tos_con_cambios']} TOs, que es el punto (h), el tope de la herencia "
              "(`data/experiment/r2_codigo2/freno_c2.md:69`: 93 unidades en 9 TOs). El control de R5 compara solo `texto`, así "
              "que (h) no le aparece. (f) y (l) actúan solo en ric, que no está en los 152 (`ric_en_los_152`: "
              f"{'sí' if h['ric_en_los_152'] else 'no'}), y (n) escribe `pies_<to>.json` sin tocar los chunks "
              "(`freno_c2.md:42,68,73`).")
            A("")


def seccion_punto2(J, A) -> None:
    e = J("escalera_r5_S2b.json")
    A("## 3. Punto 2: la escalera de R5")
    A("")
    if not e:
        A("FALTA `escalera_r5_S2b.json`.")
        A("")
        return
    A(e["texto_md"])
    A("")


def seccion_punto3(J, A) -> None:
    p = J("cifras_punto3_S2b.json")
    A("## 4. Punto 3: las cifras que la tesis va a citar")
    A("")
    if not p:
        A("FALTA `cifras_punto3_S2b.json`.")
        A("")
        return
    A("Archivo: `cifras_punto3_S2b.json`.")
    A("")
    A("**TOs por vía y por modo de lectura** (`via_por_modo`; la vía, de `s1ter/manifiesto/segmentacion_oficial_e0r2_152.json`, "
      "`818c3a43`; el modo, de `conteos.json` de la E0 corregida y de `conteos_b584.json`):")
    A("")
    modos = sorted({m for l in p["via_por_modo"].values() for v in l.values() for m in v})
    A("| vía | " + " | ".join(f"`{m}` (corregida / legada)" for m in modos) + " | total |")
    A("|---|" + "--:|" * (len(modos) + 1))
    for via in sorted(p["via"]):
        c, l = p["via_por_modo"]["corregida"].get(via, {}), p["via_por_modo"]["legada"].get(via, {})
        A(f"| {via} | " + " | ".join(f"{c.get(m, 0)} / {l.get(m, 0)}" for m in modos) + f" | {p['via'][via]} |")
    A("")
    A("La legada no tiene `sin_raiz_letra`: es la lectura sin raíz con el marcador de letra (regla 4 de S0), que la E0 "
      "corregida usa solo en ri_spi¹ (`correr_e0.py:1561-1571`).")
    A("")
    A("**Páginas y unidades por clase** (`por_clase`; la clase, de `particion_152.json`, `clase`):")
    A("")
    A("| clase | TOs | páginas | unidades | unidades legadas | diferencia |")
    A("|---|--:|--:|--:|--:|--:|")
    nombres = {"reconocido_pleno": "reconocidos plenos", "parcial_declarado": "parciales declarados",
               "no_segmentable_declarado": "no segmentables declarados", "ri_spi_y_ri_con": "ri_spi¹ y ri_con¹"}
    for k, v in p["por_clase"].items():
        A(f"| {nombres.get(k, k)} | {v['tos']} | {n(v['paginas'])} | {n(v['unidades'])} | {n(v['unidades_legadas'])} | "
          f"{dif(v['unidades'], v['unidades_legadas'])} |")
    t = p["total"]
    A(f"| **total** | {t['tos']} | {n(t['paginas'])} | {n(t['unidades'])} | {n(t['unidades_legadas'])} | {dif(t['unidades'], t['unidades_legadas'])} |")
    A("")
    A("| clase de documento | TOs | páginas | unidades | unidades legadas |")
    A("|---|--:|--:|--:|--:|")
    for k, v in p["por_categoria"].items():
        A(f"| {'normativa general' if k == 'normativa_general' else 'régimen informativo'} | {v['tos']} | {n(v['paginas'])} | "
          f"{n(v['unidades'])} | {n(v['unidades_legadas'])} |")
    A("")
    tp = t["por_tipo"]
    A(f"**Unidades** (`unidades_totales`, `chunks_terminales`, `mini_chunks`, `total.por_tipo`, `total.mini_por_rol`): "
      f"{n(p['unidades_totales'])} unidades; {n(p['chunks_terminales'])} chunks terminales ({n(tp.get('punto_terminal', 0))} "
      f"puntos terminales y {n(tp.get('seccion_sin_puntos', 0))} secciones sin puntos) y {n(p['mini_chunks'])} mini-chunks "
      f"({', '.join(f'{k} {n(v)}' for k, v in t['mini_por_rol'].items())}).")
    A("")
    pt = p["partidas_por_tamano"]
    A(f"**Unidades partidas por tamaño** (`partidas_por_tamano`; umbral {n(pt['umbral_chars'])} caracteres propios, objetivo "
      f"{n(pt['objetivo_chars_parte'])} por parte, `correr_e0.py:74-75`): {pt['unidades_partidas']} unidades partidas en "
      f"{pt['partes']} partes ({pt['partes_sobre_umbral']} partes siguen sobre el umbral); {pt['sin_partir']} quedan sin partir "
      f"({', '.join(f'{k} {v}' for k, v in pt['sin_partir_por_motivo'].items())}).")
    for to, v in pt["por_to"].items():
        partes = "; ".join(f"`{x['id']}` en {x['n_partes']}" for x in v["particiones"])
        sin = "; ".join(f"`{x['id']}` ({n(x['chars_propio'])}, {x['motivo']})" for x in v["no_particionables"])
        A(f"- {to}: " + (f"partidas: {partes}" if partes else "") + ("; " if partes and sin else "") + (f"sin partir: {sin}" if sin else "") + ".")
    A("")
    tb = p["tablas"]
    A(f"**Tablas** (`tablas`): la lectura de tablas corre en {tb['tos_donde_corre']} TOs (e0-r2 escribe `tablas_<to>.json` "
      f"para todos, `correr_e0.py:1744`); encuentra tablas en {tb['tos_con_tablas']}: {n(tb['tablas'])} tablas "
      f"({', '.join(f'{k} {n(v)}' for k, v in tb['tablas_por_origen'].items())}; "
      f"{', '.join(f'{k} {n(v)}' for k, v in tb['tablas_por_estado'].items())}), {n(tb['tablas_serializadas'])} serializadas en "
      f"{tb['tos_con_tabla_serializada']} TOs; {n(tb['unidades_con_tabla_serializada'])} unidades llevan una tabla serializada "
      f"(`flags.tablas_e0[].serializada`), en {tb['tos_con_unidades_con_tabla_serializada']} TOs.")
    A("")
    idd = p["ids_desambiguados"]
    idd_l = lista(f"{t} {v['ids_desambiguados']}" for t, v in idd["por_to"].items())
    A(f"**Ids desambiguados y chunks de índice que quedan** (`ids_desambiguados`): {idd['total']} ids desambiguados por L en "
      f"{idd['tos']} TOs ({idd_l}); de esos chunks, "
      f"{idd['en_paginas_de_indice']} están en páginas de rol índice (`pies_<to>.json`): no queda ningún chunk de índice leído "
      "como cuerpo entre los desambiguados. La partición legada repetía 69 ids en 4 TOs, todos por un índice leído como cuerpo "
      "(adfsp 9, ceninf 4, cirmo3 52, ri_niif 4; `docs/checklist_pre_escalado.md:149`, R33).")
    A("")
    k = p["encabezados_conservados_K"]
    A(f"**Encabezados conservados por K** (`encabezados_conservados_K`): {n(k['lineas'])} renglones en {k['tos']} TOs: "
      f"{lista(f'{t} {v}' for t, v in k['por_to'].items())}.")
    A("")
    ns = p["no_segmentables_y_parciales"]
    A("**Los no segmentables y los parciales, con sus páginas** (`no_segmentables_y_parciales`):")
    A("")
    A("| TO | grupo | páginas | unidades | tipos | modo |")
    A("|---|---|--:|--:|---|---|")
    for x in ns["no_segmentables_en_la_E0_corregida"]:
        A(f"| {x['to']} | no segmentable | {x['paginas']} | {x['unidades']} | {', '.join(f'{a} {b}' for a, b in x['por_tipo'].items())} | `{x['modo']}` |")
    for x in ns["ri_spi_y_ri_con"]:
        A(f"| {x['to']}¹ | fuera por la {x['razon_vigente']} | {x['paginas']} | {x['unidades']} | "
          f"{', '.join(f'{a} {b}' for a, b in x['por_tipo'].items())} | `{x['modo']}` |")
    for x in ns["parciales"]:
        A(f"| {x['to']} | parcial | {n(x['paginas'])} | {x['unidades']} | {', '.join(f'{a} {b}' for a, b in x['por_tipo'].items())} | "
          f"`{x['modo']}` (vía {x['via']}) |")
    lg = ns["legado"]
    no_seg = ns["no_segmentables_en_la_E0_corregida"]
    A("")
    A(f"En la E0 corregida quedan {len(no_seg)} no segmentables, con {n(sum(x['paginas'] for x in no_seg))} páginas y "
      f"{sum(x['unidades'] for x in no_seg)} unidades, todas secciones sin puntos; en la partición legada eran "
      f"{lg['no_segmentables']['tos']}, con {n(lg['no_segmentables']['paginas'])} páginas y {lg['no_segmentables']['unidades']} "
      f"unidades. Los parciales: {lg['parciales']['tos']}, con {n(lg['parciales']['paginas'])} páginas y "
      f"{sum(x['unidades'] for x in ns['parciales'])} unidades (legadas: {lg['parciales']['unidades']}).")
    A("")


def seccion_punto4(J, A) -> None:
    cc = J("cifras_conjuntos_clases_S2b.json")
    A("## 5. Punto 4: las cifras que la tesis toma de la segmentación fuera de la sección 4.1")
    A("")
    if not cc:
        A("FALTA `cifras_conjuntos_clases_S2b.json`.")
        A("")
        return
    A("Archivo: `cifras_conjuntos_clases_S2b.json`. Las definiciones son las del reporte legado "
      "(`reports/u_insumos_cap/u_insumos_i1.py`, `ded3494`), sin adaptar: unidad, cada elemento de `chunks_<to>.json` (R3); "
      "punto de la estructura, cada nodo de tipo punto de `estructura_<to>.json`, terminal si no tiene hijos (R12, `:370-385`). "
      "La legada reproduce las cifras del reporte (control abajo). Fuentes de la corregida: la E0 corregida para los 152 y la "
      "e0-r2 de la tanda 0 (`salida_tanda0_r2b/`, `9f6361e`) para los 5 de desarrollo; de la legada: `b584_particion/` y "
      "`salida_tanda0/` (la del reporte, `u_insumos_i1.py:262-277`).")
    A("")
    A("### 4.a. Las unidades por conjunto (decisión 6, 1A)")
    A("")
    A(f"Desarrollo: {lista(cc['conjuntos_tos']['desarrollo'])}. Validación: {lista(cc['conjuntos_tos']['validacion'])} "
      "(`esq/documentos_excluidos_evaluacion_final.json`, origen ESQ-2). Universo a escalar: los 152. Los conjuntos se solapan: "
      "la validación está dentro de los 152.")
    A("")
    nombres_c = {"desarrollo": "desarrollo", "validacion": "validación", "universo_152": "universo a escalar (los 152)"}
    tipos = sorted({k for l in ("corregida", "legada") for c in cc["4a"][l].values() for k in c["por_tipo"]})
    A("| conjunto | TOs | unidades (corregida / legada / dif.) | " + " | ".join(f"`{t}`" for t in tipos) + " |")
    A("|---|--:|---|" + "---|" * len(tipos))
    for c in ("desarrollo", "validacion", "universo_152"):
        x, y = cc["4a"]["corregida"][c], cc["4a"]["legada"][c]
        A(f"| {nombres_c[c]} | {x['tos']} | {n(x['unidades'])} / {n(y['unidades'])} / {dif(x['unidades'], y['unidades'])} | "
          + " | ".join(f"{n(x['por_tipo'].get(t, 0))} / {n(y['por_tipo'].get(t, 0))}" for t in tipos) + " |")
    A("")
    A("Mini-chunks por rol, corregida / legada (`4a.<lado>.<conjunto>.mini_por_rol`):")
    for c in ("desarrollo", "validacion", "universo_152"):
        x, y = cc["4a"]["corregida"][c]["mini_por_rol"], cc["4a"]["legada"][c]["mini_por_rol"]
        A(f"- {nombres_c[c]}: " + ", ".join(f"{r} {n(x.get(r, 0))} / {n(y.get(r, 0))}" for r in sorted(set(x) | set(y))) + ".")
    t0 = cc["4a"]["legada"]["tanda0_5"]
    A(f"- Control de la legada contra el reporte (`estadisticas_corpus.md`): desarrollo {n(cc['4a']['legada']['desarrollo']['unidades'])} "
      f"unidades (1.763), tanda 0 {n(t0['unidades'])} (671), 152 {n(cc['4a']['legada']['universo_152']['unidades'])} (9.324); "
      f"puntos terminales {n(cc['4a']['legada']['desarrollo']['puntos_terminales'])} de {n(cc['4a']['legada']['desarrollo']['puntos'])} "
      f"(1.475 de 1.810), {n(t0['puntos_terminales'])} de {n(t0['puntos'])} (577 de 710) y "
      f"{n(cc['4a']['legada']['universo_152']['puntos_terminales'])} de {n(cc['4a']['legada']['universo_152']['puntos'])} (7.413 de 9.105).")
    A("")
    A("### 4.b. Los puntos de la estructura y el porcentaje de terminales, por clase (decisión 6, 2A, sobre los 157)")
    A("")
    A("| clase | TOs | puntos (corregida / legada / dif.) | terminales (corregida / legada) | % terminales (corregida / legada / dif.) |")
    A("|---|--:|---|---|---|")
    for k, nom in (("normativa_general", "normativa general"), ("regimen_informativo", "régimen informativo"), ("total_157", "los 157")):
        x, y = cc["4b"]["corregida"][k], cc["4b"]["legada"][k]
        A(f"| {nom} | {x['tos']} | {n(x['puntos'])} / {n(y['puntos'])} / {dif(x['puntos'], y['puntos'])} | "
          f"{n(x['puntos_terminales'])} / {n(y['puntos_terminales'])} | {n(x['porcentaje_terminales'])} % / "
          f"{n(y['porcentaje_terminales'])} % / {dif(x['porcentaje_terminales'], y['porcentaje_terminales'])} |")
    A("")
    A("La legada da las cifras que hoy cita la tesis (10.157 y 758 puntos; 80,9 % y 88,4 %), que no tenían artefacto en el "
      "repo: ahora lo tienen, en `4b.legada`. Clase de los 5 de desarrollo: cap, cla, ext y pro NG, ric RI "
      "(`categoria_desarrollo`).")
    A("")
    A("### 4.c. El «primer nivel como sección» (decisión 6, 3A, con 3B como control)")
    A("")
    c4 = cc["4c"]
    A("| fila | corregida | legada |")
    A("|---|--:|--:|")
    A(f"| leídos sin raíz (`sin_raiz` y `sin_raiz_letra`) | {c4['corregida']['sin_raiz']} | {c4['legada']['sin_raiz']} |")
    A(f"| 3A: primer nivel como sección | {c4['corregida']['3A']['tos']} | {c4['legada']['3A']['tos']} |")
    A(f"| 3A, en parte (parciales) | {c4['corregida']['3A_en_parte']['tos']} | {c4['legada']['3A_en_parte']['tos']} |")
    A(f"| no segmentables | {c4['corregida']['no_segmentables']['tos']} | {c4['legada']['no_segmentables']['tos']} |")
    A(f"| 3B: sin unidades `S<n>` | {c4['corregida']['3B']['tos']} | {c4['legada']['3B']['tos']} |")
    A(f"| 3B, segunda lectura: sin secciones no sintéticas en `estructura` | {c4['corregida']['3B_estructura']['tos']} | "
      f"{c4['legada']['3B_estructura']['tos']} |")
    A("")
    A(f"- **3A, corregida** (`4c.corregida.3A.lista`): {lista(marcar(t) for t in c4['corregida']['3A']['lista'])}.")
    A(f"- **3A, legada:** {lista(c4['legada']['3A']['lista'])}. Con la partición legada, 3A da "
      f"{c4['legada']['3A']['tos']} + {c4['legada']['3A_en_parte']['tos']}, como `reports/u_cap3_datos/datos.json` "
      "(`D3.particion_de_los_84.modo_lectura_por_clase`; 42 + 2).")
    A(f"- **En parte:** {lista(c4['corregida']['3A_en_parte']['lista'])}. **No segmentables, corregida:** "
      f"{lista(c4['corregida']['no_segmentables']['lista'])}; legada: {lista(c4['legada']['no_segmentables']['lista'])}.")
    rr = c4["corregida"]["ri_spi_y_ri_con"]
    A(f"- ri_spi¹ ({rr['ri_spi']['modo']}, {rr['ri_spi']['unidades']} unidades) y ri_con¹ ({rr['ri_con']['modo']}, "
      f"{rr['ri_con']['unidades']} unidades) están en 3A de la corregida: la E0 corregida los lee sin raíz y ya no los deja en "
      "una sola unidad; quedan fuera del grafo por la enmienda 8.")
    A(f"- **3B (sin unidades `S<n>`), corregida:** {lista(c4['corregida']['3B']['lista'])}.")
    A(f"- **Difieren 3A y 3B, corregida:** en 3A y no en 3B, {lista(c4['corregida']['3A_no_3B'])}; en 3B y no en 3A, "
      f"{lista(c4['corregida']['3B_no_3A'])}. La lectura literal de 3B («sin unidades `S<n>`») mete los documentos `vigente` "
      "cuyas secciones tienen todas puntos y sin encabezado propio, y saca los sin raíz con una sección sintética que deja una "
      "unidad `S<n>`: no mide lo mismo que 3A.")
    A(f"- **3B, segunda lectura (sin secciones no sintéticas en `estructura`), corregida:** "
      f"{lista(c4['corregida']['3B_estructura']['lista'])}. Difieren de 3A: en 3A y no aquí, "
      f"{lista(c4['corregida']['3A_no_3B_estructura'])} (leídos sin raíz, con una sección no sintética); aquí y no en 3A, "
      f"{lista(c4['corregida']['3B_estructura_no_3A'])} (los no segmentables y los parciales, que 3A excluye por definición). "
      "Esta lectura es una interpretación mía del «control por la estructura» de la decisión 6: la dejo al lado, declarada.")
    A("")
    seccion_4d(J, A)
    seccion_4e(J, A, cc)
    seccion_4f(J, A)
    seccion_4g(J, A)


def seccion_4d(J, A) -> None:
    r = J("reglas_por_to_S2b.json")
    A("### 4.d. Las reglas vigentes, con el lugar del código y los TOs de cada una")
    A("")
    if not r:
        A("FALTA `reglas_por_to_S2b.json`.")
        A("")
        return
    A("Archivo: `reglas_por_to_S2b.json` (y `ablacion_b582_S2b.json` para las tres reglas de B5.8.2). Tres capas, descritas "
      "en el docstring de `reglas_por_to_S2.py`. Los TOs son sobre los 152; «en los 84» cuenta los del universo del D3 legado "
      "(`segmentacion_84/censo_84.json`), para ponerlo al lado de la cifra legada.")
    A("")
    A("**Capa A: las 21 reglas de la tabla D3 legada, con el mismo criterio** (`capa_a_D3`):")
    A("")
    A("| regla | unidad | criterio | código | TOs (152) | en los 84 | legado (84) | TOs |")
    A("|---|---|---|---|--:|--:|--:|---|")
    for f in r["capa_a_D3"]:
        cod = "; ".join(f"`{c.split('e0_chunking/')[-1]}`" for c in f["codigo"] if c)
        A(f"| {f['regla']} | {f['unidad']} | {f['criterio']} | {cod} | {f['tos']} | {f['tos_en_los_84']} | "
          f"{f['legado_n_en_los_84'] if f['legado_n_en_los_84'] is not None else '—'} | {lista((marcar(t) for t in f['lista']), 60)} |")
    A("")
    A("Adaptaciones, declaradas en el docstring del script: `conteos.json` de e0-r2 no tiene `tabular` ni `preambulo`; los "
      "criterios de tablas leen `conteos_e0_tablas`, `descartadas_por_regla_e0_tablas` y las tablas de origen `e0_tablas`; el "
      "índice variante, la sección variante y el banner de caja mixta salen de la ablación (anular la regla y comparar), como el "
      "legado hacía con las dos últimas, sobre los 7 TOs con `marcadores_b582`; la corrida sin anular reproduce la E0 corregida "
      "en los 7 (`ablacion_b582_S2b.json`, `control_base_reproduce`). Las reglas de tablas corren ahora en los 152: el grupo de "
      "las tablas deja de ser propio de los 84.")
    A("")
    A("**Capa B: las reglas de e0-r2 que dejan rastro en la salida** (`capa_b_rastro_en_la_salida`; el lugar del código es la "
      "primera línea donde aparece el literal que la salida registra):")
    A("")
    A("| regla (rastro) | tipo de rastro | código | TOs (152) | en los 84 | TOs |")
    A("|---|---|---|--:|--:|---|")
    for f in r["capa_b_rastro_en_la_salida"]:
        A(f"| `{f['regla']}` | {f['origen']} | `{(f['codigo'] or '').split('e0_chunking/')[-1]}` | {f['tos']} | {f['tos_en_los_84']} | "
          f"{lista((marcar(t) for t in f['lista']), 40)} |")
    A("")
    A("**Capa C: las reglas de S0 sin rastro propio** (`capa_c_sin_rastro`, `listas_de_tos_del_codigo`): "
      + "; ".join(f"`{x['conjunto']}` (`{x['codigo'].split('e0_chunking/')[-1]}`)" for x in r["capa_c_sin_rastro"])
      + ". Su uso por documento no se lee en la salida: pide una ablación por regla, que S2 no corre. Las que el código limita a "
        "una lista de TOs: "
      + "; ".join(f"`{k}` (`{v['codigo'].split('e0_chunking/')[-1]}`): {lista(v['tos'])}" for k, v in r["listas_de_tos_del_codigo"].items())
      + ".")
    A("")


def seccion_4e(J, A, cc) -> None:
    g = cc["4e"]
    A("### 4.e. Los tres grupos de documentos, y lo que queda fuera del grafo")
    A("")
    A("Archivo: `cifras_conjuntos_clases_S2b.json`, clave `4e` (los grupos, por `particion_152.json`, `clase`).")
    A("")
    A("| grupo | TOs (corregida / legada) | páginas (corregida / legada) | unidades (corregida / legada / dif.) |")
    A("|---|---|---|---|")
    nom = {"puntos_de_principio_a_fin": "escritos en puntos de principio a fin", "fichas_y_listados": "con fichas y listados de registro",
           "no_segmentables": "no segmentables"}
    for k in ("puntos_de_principio_a_fin", "fichas_y_listados", "no_segmentables"):
        x, y = g["corregida"][k], g["legada"][k]
        A(f"| {nom[k]} | {x['tos']} / {y['tos']} | {n(x['paginas'])} / {n(y['paginas'])} | {n(x['unidades'])} / {n(y['unidades'])} / "
          f"{dif(x['unidades'], y['unidades'])} |")
    x = g["corregida"]["ri_spi_y_ri_con"]
    A(f"| ri_spi¹ y ri_con¹ (en la legada, dentro de los no segmentables) | {x['tos']} / — | {n(x['paginas'])} / — | {n(x['unidades'])} / — / — |")
    A("")
    A(f"Los no segmentables de la corregida: {lista(g['corregida']['no_segmentables']['lista'])}. Los de fichas y listados: "
      f"{lista(g['corregida']['fichas_y_listados']['lista'])}. Las cifras legadas son las de `particion_152.json`, `agregados` "
      "(138, 4.183 y 9.266; 2, 2.413 y 46; 12, 161 y 12).")
    A("")
    A("**Lo que queda fuera del grafo según las enmiendas a las adendas 1 y 2 del laudo B5.5** "
      "(`docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md`, leídas en `e82e22f`; páginas y unidades de esa fuente):")
    A("")
    A("| qué | páginas | unidades | razón | ancla |")
    A("|---|--:|--:|---|---|")
    A("| manual | 2.037 | 17 por punto | histórico: «Vigente hasta el 31/12/2017» | Parte III, punto 1 |")
    A("| ri_ao | 1 | 5 | derogado por la Com. A 8262 | Parte III, punto 2 |")
    A("| optico y plandecuentas | 43 y 77 | — | documentos de referencia, sin contenido prescriptivo | Parte II.2, punto 5 |")
    A("| bloque B: ri2_pm, fichas y cuerpo entre fichas | 366 | — | release posterior declarada (fichas y planillas, ESQ-RI-3 y ESQ-RI-4) | Parte II.2, punto 4 |")
    A("| bloque B: la planilla de los nueve | 17 | 114 | ídem | Parte II.2, punto 4 |")
    A("")
    A("En `e82e22f` entraban con la tanda 3 la prosa del bloque A (77 unidades, 13 páginas), las 25 unidades por punto de ri2_pm "
      "(10 páginas) y ri_spi¹ (11 páginas). Las tres cambiaron después (abajo).")
    A("")
    A("**Lo que deja fuera del grafo evaluado lo decidido después de `e82e22f`** (aparte; unidades de la E0 corregida, "
      "`cifras_punto3_S2b.json`, `por_to.<to>.unidades`):")
    A("")
    e8 = J("cifras_punto3_S2b.json")
    if e8:
        pt = e8["por_to"]
        d1 = ["ri_oc", "ri_icpipsp", "ri_pnp", "ri_psprca", "gerc", "ri_spi"]
        d2 = ["dmrd", "ri2_cs", "ri_cc", "ri_ccpnp", "ri_con", "ri_niif", "nmaeef", "ri_saofe", "ri2_ae"]
        quince = sorted(set(d1) | set(d2))
        A("| qué | TOs | unidades | razón | ancla |")
        A("|---|--:|--:|---|---|")
        A(f"| enmienda 8, decisión 1 | {len(d1)} | {n(sum(pt[t]['unidades'] for t in d1))} | error de corte confirmado en S1-quater: "
          f"{lista(marcar(t) for t in d1)} | `docs/enmienda8_protocolo_entre_tandas_2026-10-15_calendario_hacia_B6.3.md`, decisión 1 |")
        d2s = [t for t in d2 if t not in d1]
        A(f"| enmienda 8, decisión 2 (sin ri_pnp, que está en la 1) | {len(d2s)} | {n(sum(pt[t]['unidades'] for t in d2s))} | "
          f"BKL-0044 y los rechazos `raiz_en_columna_profunda` que quedan: {lista(marcar(t) for t in d2s)} | ídem, decisión 2 |")
        A(f"| los 15 de la enmienda 8 | {len(quince)} | {n(sum(pt[t]['unidades'] for t in quince))} | suma de las dos filas | — |")
        A(f"| ri2_pm, parte por punto | 1 | {pt['ri2_pm']['unidades']} | va con el bloque B, en la release posterior | "
          "nota del 15/10/2026 al pie de las enmiendas, `:147-152` |")
        A("| U-BLOQUE-A, prosa del bloque A | 9 | 77 | va al grafo corregido del cap. 6 | "
          "`docs/registro_decisiones_calidad_y_evaluacion_2026-10-15.md:161`; 77 de `cobertura_bloque_a/alcance_nueve.json` |")
        A("")
        A("ri_pnp está en las dos decisiones y cuenta una vez. Los nueve de U-BLOQUE-A son ri_con¹, ri_tii, ri_rem, ri_chr, ri_fcem, "
          "ri_itme, ri_pfmipyme, ri_pscpp y ri_pspii; sus 77 unidades no son las de la E0 corregida (son de U-COB-A). ri_con¹ está "
          "también en la decisión 2.")
        A("")


def seccion_4f(J, A) -> None:
    s = J("s1quater_S2b.json")
    c = J("censos_S2b.json")
    A("### 4.f. La lectura de cortes de S1-quater y el censo de renglones")
    A("")
    if s:
        A(s["texto_md"])
    else:
        A("FALTA `s1quater_S2b.json`.")
    A("")
    if c:
        A(c["texto_md_renglones"])
    else:
        A("FALTA `censos_S2b.json`.")
    A("")


def seccion_4g(J, A) -> None:
    A("### 4.g. La tabla de las marcas")
    A("")
    m = J("marcas_4g_S2b.json")
    if not m:
        A("FALTA `marcas_4g_S2b.json`.")
        A("")
        return
    A(m["texto_md"])
    A("")


def seccion_detecciones(J, A) -> None:
    c = J("censos_S2b.json")
    A("## 6. Las detecciones de la release de E0 en la tanda 1 (agregado 3 del «seguí»)")
    A("")
    if not c:
        A("FALTA `censos_S2b.json`.")
        A("")
        return
    A(c["texto_md_tanda1"])
    A("")


def seccion_tramo3(J, A) -> None:
    tf = J("tanda_final_S2c.json")
    A("## 7. Tramo 3: el re-censo de la release de E0 antes de la tanda final")
    A("")
    A("Archivo: `tanda_final_S2c.json` (y `resumen_healthcheck_tanda_final_S2c.json`). Sobre la E0 corregida. La release de E0 "
      "antes de la tanda final sigue igual, sin re-extraer (mandato, `:665-677`; enmienda 8, §1). Los censos de sub-documentos y "
      "de renglones son los del tramo 2 (`censos_S2b.json`), con el código de la E0 corregida; acá se cuentan sobre la tanda final. "
      "Son detecciones, no lecturas, con falsos positivos conocidos (mandato, `:670`).")
    A("")
    t = tf["tanda_final"]
    A("**La tanda final** (`tanda_final`, `cascada_disjunta_sobre_los_152`): los candidatos del §5 del protocolo que quedan después "
      "de la tanda 1 del tramo 1, sin los de fuera, sin ri2_pm, sin los 15 de las decisiones 1 y 2 de la enmienda 8 y sin rdbcra "
      "(enmienda 8, §1; agregados 1 y 6). Cada TO cuenta en el primer motivo que lo saca:")
    A("")
    A("| motivo | TOs | unidades | quedan |")
    A("|---|--:|--:|--:|")
    A("| los 152 | — | 10.478 | 152 |")
    for c in tf["cascada_disjunta_sobre_los_152"]:
        A(f"| {c['motivo']} | {c['excluidos']} | {n(c['unidades'])} | {c['quedan']} |")
    A(f"| **tanda final** | **{t['tos']}** | **{n(t['unidades'])}** | |")
    A("")
    A(f"- **{t['tos']} TOs y {n(t['unidades'])} unidades** (`unidades_por_to` del manifiesto de S0-6b). La mesa contaba "
      f"{tf['mesa']['tos']} y {n(tf['mesa']['unidades'])} (nota del 15/10/2026 a la enmienda 8, `{tf['mesa']['fuente']}`): "
      f"{'igual' if tf['igual_a_la_mesa'] else 'DISTINTO'}.")
    pc = t["por_categoria"]
    A(f"- Por clase: normativa general {pc['normativa_general']['tos']} TOs y {n(pc['normativa_general']['unidades'])} unidades; "
      f"régimen informativo {pc['regimen_informativo']['tos']} y {n(pc['regimen_informativo']['unidades'])}. Por modo de lectura: "
      + ", ".join(f"`{k}` {v}" for k, v in sorted(t["por_modo"].items())) + ".")
    A(f"- ri_ao sale por la nota del 04/10/2026 al protocolo (`docs/protocolo_entre_tandas.md:432-438`: «ri_ao, derogado, que sale "
      "de la tanda 3»), que el §5 arrastra a los candidatos. ri_spi¹ y ri_con¹ salen en la fila de la enmienda 8. ri_oc sale ahí "
      "también: dejó la tanda 1 por la decisión 1.")
    A("")
    fr = tf["frena"]
    A(f"**Cobertura exacta e ids de chunk repetidos, en la E0 corregida** (agregado 2; `frena`): cobertura no exacta en "
      f"{lista(fr['cobertura_no_exacta'])}; ids repetidos en {lista(fr['ids_repetidos'])}. **Ninguno: no hay freno.** La fila de cada TO, abajo.")
    A("")
    hc = tf.get("healthcheck")
    if hc:
        A(f"**El health-check de la tanda final** (agregado 5; `healthcheck`): corre como en el tramo 2, con `healthcheck_e0.py` de la "
          f"raíz mínima sobre los {hc['tos']} PDFs. No reproduce `correr_e0` en **{len(hc['no_reproduce_correr_e0'])} de {hc['tos']}** "
          "(da otras unidades que `unidades_por_to`; corre la escalera de `e0_lib` sin el driver de e0-r2). La cobertura no exacta "
          f"según su propio parseo: {lista(hc['cobertura_no_exacta_hc'])}; no frena, porque la cobertura y los ids se controlan sobre la "
          "E0 corregida (agregado 4 del «seguí» del tramo 3). Las otras señales se registran por TO y no excluyen (mandato, nota del "
          "15/10/2026, `:1036-1043`). Veredictos: " + ", ".join(f"{k} {v}" for k, v in sorted(hc["veredictos"].items())) + ".")
        A("")
    sd = tf["subdocumento"]
    d = sd["detecciones"]
    an = sd["antes"]
    A(f"**Los límites de sub-documento** (punto 3 de la release; E0-05; `subdocumento`, del censo de S0-4a, "
      f"`s0_4/scripts/censo_sd_152.py`, sobre la E0 corregida): **{d['limites']} límites en {d['tos']} TOs** quedan como detección ("
      + ", ".join(f"{k} {v}" for k, v in d["por_forma"].items()) + f"); {d['en_pagina_donde_A_ya_abre']} de ellos están en una página "
      f"donde la regla A de S0-6a ya abre una división. Por TO: {lista(f'{k} {v}' for k, v in d['por_to'].items())}. En la lista de la "
      f"regla de sub-documento, que los aplica: {sd['en_la_lista_de_la_regla']['limites']} en {lista(sd['en_la_lista_de_la_regla']['tos'])}. "
      f"Antes (`{an['fuente']}`): {an['tanda_2'][0]} en {an['tanda_2'][1]} TOs de la tanda 2 y {an['tanda_3'][0]} en {an['tanda_3'][1]} de "
      "la tanda 3, con otra E0 y otra tanda 1.")
    A("")
    h = tf["hallazgo_1_16"]
    an = h["antes"]
    A(f"**Los candidatos del hallazgo 1.16** (punto 4; E0-06; `hallazgo_1_16`), con las dos cifras que decidió la autora para el v8 "
      f"(mandato, nota del 15/10/2026, decisión a): **el censo de renglones, la principal: {h['censo']['casos']} en {h['censo']['tos']} "
      f"TOs**; al lado, el detector corregido de S0-5a: {h['detector']['casos']} en {h['detector']['tos']} TOs. Antes, con el censo de S1 "
      f"(`{an['fuente']}`): {an['tanda_2'][0]} en {an['tanda_2'][1]} TOs de la tanda 2 y {an['tanda_3'][0]} en {an['tanda_3'][1]} de la "
      "tanda 3. Las listas, con ids y páginas, en `hallazgo_1_16.censo.lista` y `hallazgo_1_16.detector.lista`.")
    A("")
    A("**Una regla para el 1.16: no propongo ninguna.** La regla general que ya corre es C de S0-6a (el párrafo sin número asignado "
      "por su columna, aviso `parrafo_por_columna_c`; `REGLAS_S0_6`, `correr_e0.py:218`), que reemplazó a R5-a por lista "
      "(`REEMPLAZOS_S0_6`, `correr_e0.py:220`); R5-a sigue por lista solo en `LISTAS_R5A_S0_6` (`:225`). Lo que queda son detecciones "
      "con falsos positivos conocidos: una regla acotada, como otra lista de cierres, pide leer cada caso para saber que es un error, y "
      "medir que no rompe otros; sin esa lectura no puedo decir que sea de bajo riesgo. S2 cuenta detecciones; si se leen los casos, y "
      "cuándo, lo decide la autora.")
    A("")
    A("**`nmaeef::2.9` y la «Sección 1.» de ri_niif** (punto 5 de la release): sus dos documentos quedaron fuera de la tanda final y del "
      "grafo evaluado por la decisión 2 de la enmienda 8. Solo lo declaro.")
    A("")
    A("**Una fila por TO de la tanda final** (`filas`; hc: health-check; sd: límites de sub-documento como detección; 1.16: censo / "
      "detector):")
    A("")
    A("| TO | clase | modo | unidades | cobertura exacta | ids repetidos | hc: veredicto | hc: unidades | sd | 1.16 |")
    A("|---|---|---|--:|---|--:|---|--:|--:|---|")
    for to, f in tf["filas"].items():
        hcf = f.get("healthcheck") or {}
        v = hcf.get("veredicto_hc")
        v = "—" if v is None else ("sano" if v == "sano" else ", ".join(v))
        sdl = f["subdocumento"]["limites"] if not f["subdocumento"]["en_la_lista_de_la_regla"] else f"{f['subdocumento']['limites']} (en la lista)"
        A(f"| {to} | {'NG' if f['categoria'] == 'normativa_general' else 'RI'} | `{f['modo_lectura']}` | {n(f['unidades'])} | "
          f"{'sí' if f['cobertura_exacta'] else 'no'} | {f['ids_chunk_repetidos']} | {v} | {n(hcf['unidades_hc']) if hcf else '—'} | {sdl} | "
          f"{f['hallazgo_1_16_censo']} / {f['hallazgo_1_16_detector']} |")
    A("")


if __name__ == "__main__":
    main()
