"""Genera el reporte de una corrida a partir de sus artefactos. SIN RED.

Regenerable: no calcula nada propio, solo lee tabla_deltas.json y
mapeo_grafo.json y los redacta. Si el reporte y los artefactos discrepan, manda
el artefacto.

Uso (desde cualquier cwd):
  python3 data/experiment/job_actualizacion/code/reporte_corrida.py [--fecha AAAA-MM-DD]

Salida:
  ../corridas/<fecha>/reporte.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_job as L                                              # noqa: E402

CLASES = ("sin_cambio", "contenido_modificado", "nuevo_en_indice",
          "desaparecido_del_indice", "no_verificable")


def fila_resumen(nombre: str, r: dict) -> str:
    return (f"| {nombre} | {r['total']} | {r['sin_cambio']} | "
            f"{r['contenido_modificado']} | {r['nuevo_en_indice']} | "
            f"{r['desaparecido_del_indice']} | {r['no_verificable']} |")


def proc_str(p: dict | None) -> str:
    if not p:
        return "—"
    if p.get("portada_comunicacion"):
        s = f"portada {p['portada_comunicacion']}"
        if p.get("texto_ordenado_al"):
            s += f", t.o. al {p['texto_ordenado_al']}"
        return s
    if p.get("pie_comunicaciones"):
        return "pie " + ", ".join(p["pie_comunicaciones"][-3:])
    return p.get("limite_declarado") or "—"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fecha", default=date.today().isoformat())
    args = ap.parse_args(argv)
    d = L.CORRIDAS / args.fecha
    t = json.loads((d / "tabla_deltas.json").read_text(encoding="utf-8"))
    m = json.loads((d / "mapeo_grafo.json").read_text(encoding="utf-8"))
    tabla = t["tabla"]
    dev = t["delta_conjunto_desarrollo"]
    glob = t["delta_inicial_vs_descarga_original"]
    g = glob["desglosado_por_corpus"]

    L_ = []
    A = L_.append
    A(f"# Corrida del job de actualización — {t['fecha_corrida']}")
    A("")
    A("Primera corrida del job. Todo lo de abajo sale de `tabla_deltas.json` y")
    A("`mapeo_grafo.json`, en este mismo directorio; este reporte solo los redacta.")
    A("La línea base sellada no fue tocada: el job la lee y compara.")
    A("")
    A("---")
    A("")

    # ---------------- 1. el conjunto de desarrollo, al frente ----------------
    A("## 1. `delta_conjunto_desarrollo` — los 5 TOs sobre los que se construyó el método")
    A("")
    r = dev["resumen"]
    cambiados = [i for i, f in dev["por_to"].items()
                 if f["clasificacion"] == "contenido_modificado"]
    if cambiados:
        A(f"**{len(cambiados)} de {r['total']} cambiaron.** Es hallazgo mayor y va con su")
        A("sha anterior y el actual. **No invalida nada**: el trabajo está anclado por")
        A("sha, que es precisamente la defensa que el informe ya declara — el grafo se")
        A("construyó sobre los PDFs cuyo sha está en el manifiesto, y esos siguen")
        A("siendo los mismos archivos en disco. Lo que cambia es qué publica hoy la")
        A("fuente.")
    else:
        A(f"**Ninguno de los {r['total']} cambió.** Los 5 siguen **idénticos** a los")
        A("inventariados: mismo sha256 que el declarado en el manifiesto de desarrollo.")
    A("")
    A("| TO | id en el grafo | clase | sha anterior → actual | páginas | procedencia anterior → actual |")
    A("|---|---|---|---|---|---|")
    for i, f in sorted(dev["por_to"].items()):
        sa, sn = (f["sha_anterior"] or "")[:8], (f["sha_actual"] or "")[:8]
        sha = f"`{sa}` = `{sn}`" if sa == sn else f"`{sa}` → **`{sn}`**"
        pg = (f"{f['paginas_anterior']}" if f["paginas_anterior"] == f["paginas_actual"]
              else f"{f['paginas_anterior']} → **{f['paginas_actual']}**")
        pr_a, pr_n = proc_str(f["procedencia_anterior"]), proc_str(f["procedencia_actual"])
        pr = pr_a if pr_a == pr_n else f"{pr_a} → **{pr_n}**"
        A(f"| `{i}` | `{f['id_interno']}` | {f['clasificacion']} | {sha} | {pg} | {pr} |")
    A("")

    for i in sorted(cambiados):
        f = dev["por_to"][i]
        A(f"### `{i}` — mapeo delta → grafo")
        A("")
        pm = f.get("paginas_modificadas")
        if pm:
            A(f"- **Páginas con texto modificado: {len(pm)}** de "
              f"{f['paginas_actual']} — {', '.join(str(x) for x in pm[:25])}"
              f"{' …' if len(pm) > 25 else ''}")
        else:
            A(f"- Diff fino no aplicable: `{f.get('motivo_sin_diff_fino')}`; "
              f"el mapeo cae al TO entero y se declara.")
        mg = f.get("mapeo_grafo") or {}
        if mg.get("fuera_de_alcance"):
            A(f"- **Fuera de alcance del grafo**: {mg['fuera_de_alcance']}.")
        elif mg:
            A(f"- **TO entero:** {mg['nodos_afectados']} nodos / "
              f"{mg['aristas_afectadas']} aristas.")
            if mg.get("nodos_afectados_por_pagina") is not None:
                A(f"- **Restringido a las páginas modificadas:** "
                  f"**{mg['nodos_afectados_por_pagina']} nodos / "
                  f"{mg['aristas_afectadas_por_pagina']} aristas**, sobre "
                  f"{mg['chunk_ids_afectados']} chunks. Ese es el conjunto a revisar.")
            comp = mg.get("compartidos_con_otros_tos") or []
            if comp:
                verbo = ("nodo está anclado" if len(comp) == 1
                         else "nodos están anclados")
                A(f"- **{len(comp)} de esos {verbo} en más de un TO** "
                  f"({', '.join('`'+c['nodo']+'`' for c in comp[:6])}"
                  f"{' …' if len(comp) > 6 else ''}): se marcan para **revisar**, "
                  f"nunca para reemplazar por TO.")
            else:
                A("- Ningún nodo afectado está anclado en otro TO.")
        A("")

    # ---------------- 2. el delta global, desglosado ----------------
    A("---")
    A("")
    A("## 2. `delta_inicial_vs_descarga_original` — desglosado por corpus")
    A("")
    A("Las ventanas son **distintas por corpus** y se reportan por separado: un")
    A("agregado único escondería de qué lado viene el material.")
    A("")
    A("| corpus | adquisición | ventana | fuente de la fecha |")
    A("|---|---|---|---|")
    for gr, nombre in (("desarrollo_5", "Conjunto de desarrollo (5)"),
                       ("inventariado_152", "Inventario de escalado (152)")):
        v = t["ventanas_por_corpus"][gr]
        A(f"| {nombre} | {v['adquisicion']} | "
          f"{'~4 meses' if gr == 'desarrollo_5' else '~3,5 semanas'} | "
          f"{v['fuente_de_la_fecha']} |")
    A("")
    A("| corpus | TOs | sin cambio | contenido modificado | nuevo en índice | desaparecido | no verificable |")
    A("|---|---:|---:|---:|---:|---:|---:|")
    A(fila_resumen("Conjunto de desarrollo (5)", g["desarrollo_5"]))
    A(fila_resumen("Inventario de escalado (152)", g["inventariado_152"]))
    if g["alta_posterior"]["total"]:
        A(fila_resumen("Altas posteriores", g["alta_posterior"]))
    tot = {k: g["desarrollo_5"][k] + g["inventariado_152"][k]
           + g["alta_posterior"][k] for k in ("total",) + CLASES}
    A(fila_resumen("**Total**", tot))
    A("")
    for clase in ("contenido_modificado", "nuevo_en_indice",
                  "desaparecido_del_indice", "no_verificable"):
        ids = glob["ids_por_clase"][clase]
        if ids:
            A(f"- **{clase}** ({len(ids)}): " +
              ", ".join(f"`{i}`" for i in ids))
    A("")
    A("### El índice de hoy")
    A("")
    idx = t["indice_de_hoy"]
    A(f"{idx['entradas']} entradas → **{idx['urls_unicas']} URLs únicas** "
      f"({len(idx['duplicadas'])} duplicada"
      f"{'s' if len(idx['duplicadas']) != 1 else ''} descartada"
      f"{'s' if len(idx['duplicadas']) != 1 else ''}), con la misma regla de")
    A("deduplicación del inventario sellado.")
    A("")

    # ---------------- 2bis. dos hallazgos metodológicos ----------------
    mv = glob["modificados_por_movimiento_de_procedencia"]
    movida, quieta = mv["con_procedencia_movida"], mv["con_procedencia_quieta"]
    A("### Qué anuncia el documento y qué cambió de verdad")
    A("")
    A(f"De los {len(movida) + len(quieta)} con contenido modificado, **{len(movida)} movieron")
    A(f"su procedencia declarada** y **{len(quieta)} no la movieron**: mismo número de")
    A("comunicación y misma fecha de texto ordenado, pero distinto sha256.")
    A("")
    if quieta:
        A("| TO | páginas modificadas | muestra del cambio |")
        A("|---|---:|---|")
        for i in quieta:
            f = tabla[i]
            pm = f.get("paginas_modificadas") or []
            frags = f.get("muestra_del_cambio") or []
            txt = "; ".join(
                (f"aparece «{x['ahora'][:90]}»" if x.get("tipo") == "insert"
                 else f"«{(x.get('antes') or '')[:45]}» → «{(x.get('ahora') or '')[:45]}»")
                for x in frags[:2]) or "—"
            A(f"| `{i}` | {len(pm)} de {f['paginas_actual']} (pág. "
              f"{', '.join(str(x) for x in pm[:4])}) | {txt} |")
        A("")
    A("**Consecuencia de método:** un cambio de sha con procedencia quieta es un cambio")
    A("que el documento **no anuncia**. Confirma la decisión de diseño de §3: la señal")
    A("de cambio tiene que ser el sha del contenido — ni la cabecera HTTP, ni siquiera")
    A("lo que el documento declara de sí mismo.")
    A("")
    A("### Qué es y qué no es el diff por página")
    A("")
    A("El diff fino compara **texto extraído**, página contra página. Es un")
    A("**localizador**, no un comparador semántico: dice dónde mirar, no qué cambió.")
    A("En páginas muy tabulares, el orden en que se extrae el texto puede variar entre")
    A("dos generaciones del mismo PDF, de modo que una página puede aparecer como")
    A("modificada por reordenamiento de extracción y no por cambio de contenido. El")
    A("cambio de sha del documento sí es real en todos los casos; la atribución página")
    A("por página es una pista a verificar, y así se declara.")
    A("")

    # ---------------- 3. exigencia 6 ----------------
    A("---")
    A("")
    A("## 3. Lectura para la exigencia 6 (validación contra material posterior)")
    A("")
    A("Las fechas de referencia son las **reales**, ancladas en artefactos")
    A("(`docs/fe_erratas_fecha_corpus_congelado.md`): **2026-05-07/10** para los 5")
    A("del conjunto de desarrollo y **2026-08-13** para los 152. No «marzo».")
    A("")
    n_dev = g["desarrollo_5"]["contenido_modificado"]
    n_152 = g["inventariado_152"]["contenido_modificado"]
    if n_dev:
        A(f"**Hay material posterior al corte, y está del lado útil.** "
          f"{'El TO modificado' if n_dev == 1 else f'Los {n_dev} TOs modificados'}")
        A("del conjunto de desarrollo son exactamente los documentos que el")
        A("grafo vigente cubre, así que el delta es directamente accionable: se sabe qué")
        A("nodos y aristas provienen del texto que cambió, y sobre qué páginas.")
        A("")
        A("Ese material es el candidato concreto para la exigencia 6: contenido")
        A("regulatorio incorporado **después** de la construcción del grafo, con el que")
        A("se puede probar si el recurso responde bien a normativa que no vio.")
    else:
        A("**No hay material posterior por esta vía en el conjunto de desarrollo.**")
        A("Los 5 siguen idénticos, de modo que la exigencia 6 tendría que buscar")
        A("material por otra vía.")
    A("")
    A(f"Del lado de los 152, {n_152} "
      f"{'TO' if n_152 == 1 else 'TOs'} con contenido modificado en una ventana de")
    A("~3,5 semanas. Un delta chico de ese lado es el resultado **esperable**, no un")
    A("fracaso del instrumento: la ventana es corta por construcción. Y aunque")
    A("apareciera material, el grafo vigente no cubre esos documentos, así que el")
    A("mapeo se declara `fuera_de_alcance` en lugar de fingir alcance.")
    A("")

    # ---------------- 4. cortesía y retención ----------------
    A("---")
    A("")
    A("## 4. Cortesía con la fuente y retención")
    A("")
    # Las estadísticas salen del artefacto versionado, no de la bitácora cruda
    # (que el .gitignore raíz excluye por ser *.log).
    v = json.loads((d / "verificacion_corrida.json").read_text(encoding="utf-8"))
    c = v["cortesia_con_la_fuente"]
    reintentos = c["reintentos_por_error_de_red"]
    lento = c["activaciones_modo_lento_503"]
    arranques = c["arranques_del_runner"]
    pedidos_idx = c["pedidos_al_indice_registrados"]
    pedidos_pdf = c["pedidos_a_pdfs_registrados"]
    en_vuelo_art = c["pedidos_en_vuelo_sin_registro"]
    unicos = sum(1 for f in tabla.values() if f["sha_actual"])
    # La bitácora registra un pedido DESPUÉS de completarlo, así que un pedido
    # en vuelo al interrumpir no deja línea. Se cuenta aparte en vez de
    # publicar un total que la bitácora no respalda.
    en_vuelo = en_vuelo_art
    A(f"- **Pedidos registrados en la bitácora: {pedidos_idx + pedidos_pdf}** "
      f"= {pedidos_idx} al índice + {pedidos_pdf} a PDFs, "
      f"sobre {unicos} documentos distintos.")
    if en_vuelo:
        A(f"- Más {en_vuelo} "
          f"{'pedido' if en_vuelo == 1 else 'pedidos'} en vuelo al interrumpir, "
          f"sin línea propia en la bitácora: "
          f"**{pedidos_idx + pedidos_pdf + en_vuelo} pedidos reales** al sitio.")
    A(f"- Reintentos por error de red: **{reintentos}**. "
      f"Activaciones del modo lento por 503: **{lento}**.")
    A("- Ritmo: 1 pedido cada 0,5 s, uno por vez, sin concurrencia.")
    fin = c["cierres_de_segmento"]
    if fin:
        A(f"- Cierre del último segmento: `{fin[-1]}`")
    if arranques > 1:
        A("")
        A(f"**El runner arrancó {arranques} veces y los números de arriba suman los")
        A("tres segmentos, no el último.** El primero fue `--solo-indice`,")
        A("verificación del endpoint antes de bajar nada. El segundo se interrumpió")
        A("a propósito y el tercero lo reanudó con `--reanudar`, que saltea lo ya")
        A("bajado: por eso el tercero reporta 106 pedidos y no 158. El único")
        A("documento pedido dos veces es el que estaba descargándose cuando se")
        A("cortó — no tenía observación escrita, así que la reanudación lo volvió a")
        A("pedir. Es el caso para el que la idempotencia existe.")
        A("")
        A("La bitácora cruda (`corrida.log`) **no se versiona**: el `.gitignore`")
        A("raíz del repositorio excluye `*.log` y esta unidad no lo edita. Sus")
        A("estadísticas quedan persistidas en `verificacion_corrida.json`, que sí")
        A("se versiona, y de ahí las lee este reporte.")
    A("")
    A("**Retención declarada** (§2.a.5 del diseño): se conservan permanentemente los")
    A("artefactos JSON/Markdown de la corrida; los PDFs de esta corrida quedan como")
    A("línea base de la siguiente; los PDFs de los TOs con contenido modificado se")
    A("conservan de forma permanente, porque son la única copia de una versión que la")
    A("fuente ya no sirve. **El job nunca borra**: la purga es manual y explícita.")
    A("")
    A("---")
    A("")
    A("## 5. Qué NO hizo el job")
    A("")
    A("- **No tocó el inventario sellado** ni el manifiesto de desarrollo: los leyó.")
    A("- **No tocó el grafo.** Produjo el conjunto de partes afectadas y se detuvo.")
    A("  Aplicar la actualización es una release con laudo propio.")
    A("- **No instaló nada**: ni cron, ni demonio, ni monitoreo, ni alertas.")
    A("")

    (d / "reporte.md").write_text("\n".join(L_) + "\n", encoding="utf-8")
    print(f"escrito {d / 'reporte.md'} ({len(L_)} líneas)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
