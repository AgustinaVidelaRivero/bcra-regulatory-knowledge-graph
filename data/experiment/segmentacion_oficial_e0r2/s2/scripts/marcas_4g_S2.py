"""4.g de S2 (U-SEG-OFICIAL): la tabla de las marcas, con las 8 filas mínimas del mandato (`:348-361`) y una fila por
cada una de las tres marcas de la tesis vigente que da el despacho de S2 (versión 2), con su texto tal cual. Solo lectura.

Uso: python -B marcas_4g_S2.py --cifras <dir de s2/cifras> --e0 <E0 corregida> --raiz <copia del repo> --out <json>

Cada fila: a qué se refiere, la cifra o el dato que la resuelve, el archivo y la clave de donde sale (`s2/cifras/`), y
si se resuelve con lo que deja S2. Una marca que no se resuelve lo dice, con la razón; no se completa con una cifra
legada. Las marcas de U-BLOQUE-A no entran.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

T0R2B = "data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b/conteos.json"
T0LEG = "data/experiment/reextraccion_v2/e0_chunking/salida_tanda0/conteos.json"
B584 = "data/experiment/segmentacion_84/b584_particion/conteos_b584.json"
DESARROLLO = ["cap", "cla", "ext", "pro", "ric"]
MARCAS = [
    "% [AL CIERRE: U-SEG-OFICIAL] decir si la reconoce y con qué regla.",
    "% [AL CIERRE: U-SEG-OFICIAL] Comprobar que los roles de página no cambiaron. Si cambiaron, recontar con el script de "
    "VERIF-FORMAS-SEG y actualizar juntas esta tabla y la Tabla de las partes de un Texto Ordenado.",
    "% [AL CIERRE: U-SEG-OFICIAL] Rehacer la tabla con la segmentación oficial e0-r2: en ella la lectura de tablas corre en "
    "los 152 documentos, así que el grupo de las tablas deja de ser propio de los 84. Pedido a la otra mesa: el uso de cada "
    "regla por documento en el documento de cifras de S2.",
]


def cargar(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def miles(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def esc(s: str) -> str:
    return s.replace("|", "\\|")


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("--cifras", "--e0", "--raiz", "--out"):
        ap.add_argument(k, type=Path, required=True)
    a = ap.parse_args()
    p3 = cargar(a.cifras / "cifras_punto3_S2b.json")
    p7 = cargar(a.cifras / "p7_en_la_corregida_S2b.json")
    rg = cargar(a.cifras / "reglas_por_to_S2b.json")
    rp = cargar(a.cifras / "roles_pagina_S2b.json")
    cc = cargar(a.cifras / "cifras_conjuntos_clases_S2b.json")
    # roles por página, totales sobre los 157
    c_cor = {**cargar(a.e0 / "conteos.json"), **{t: v for t, v in cargar(a.raiz / T0R2B).items() if t in DESARROLLO}}
    c_leg = {**cargar(a.raiz / B584), **{t: v for t, v in cargar(a.raiz / T0LEG).items() if t in DESARROLLO}}
    roles_cor, roles_leg = Counter(), Counter()
    for t in c_cor:
        roles_cor.update(c_cor[t]["roles_pagina"])
        roles_leg.update(c_leg[t]["roles_pagina"])
    assert len(c_cor) == len(c_leg) == 157
    # reglas que actúan en cada no segmentable
    usa = {}
    for f in rg["capa_b_rastro_en_la_salida"]:
        for t in f["lista"]:
            usa.setdefault(t, []).append(f["regla"])
    pt = p3["por_to"]
    ns = p3["no_segmentables_y_parciales"]
    doce = [x["to"] for x in ns["no_segmentables_en_la_E0_corregida"]] + [x["to"] for x in ns["ri_spi_y_ri_con"]]
    filas = []

    def fila(n, que, dato, archivo, clave, resuelve="sí"):
        filas.append({"n": n, "que": que, "dato": dato, "archivo": archivo, "clave": clave, "resuelve": resuelve})

    los36 = p7["los_36"]
    resto = p7["censo_p7_resto_corregida"]
    fila("1", "Los párrafos sin numerar que empiezan con un número de punto (36 en la verificación del 03/10/2026; S0, punto 7)",
         f"Con el código vigente quedan {p7['censo_p7_corregida']['total']} intersticiales así. Los 36: "
         + ", ".join(f"{k} {v}" for k, v in los36["por_destino"].items())
         + f" ({', '.join(f'{k} {v}' for k, v in los36['por_to_y_destino'].items())}). Como límite, los rótulos que la regla no "
           f"alcanza (rechazados por «padre no abierto» con el padre presente): {resto['total']}, "
         + ", ".join(f"{k} {v}" for k, v in resto["por_to"].items()) + ".",
         "p7_en_la_corregida_S2b.json", "censo_p7_corregida.total; los_36.por_destino; censo_p7_resto_corregida")
    spi = pt["ri_spi"]
    fila("2", "ri_spi: si quedó segmentado, con qué regla y en cuántas unidades (S0, punto 4)",
         f"Sí: {spi['unidades']} unidades (" + ", ".join(f"{k} {v}" for k, v in spi["por_tipo"].items())
         + "), modo `sin_raiz_letra`, con la regla 4 de S0, el marcador de letra y número (`correr_e0.py:1561-1571`; aviso "
           "`marcador_letra_r2`). Queda fuera del grafo evaluado por la decisión 1 de la enmienda 8; en la partición legada era no "
           "segmentable, con 1 unidad.",
         "cifras_punto3_S2b.json; reglas_por_to_S2b.json", "por_to.ri_spi; capa_b_rastro_en_la_salida (marcador_letra_r2)")
    fila("3", "Los documentos no segmentables, uno por uno, con sus páginas",
         "; ".join(f"{x['to']} {x['paginas']} pp. y {x['unidades']} u" for x in ns["no_segmentables_en_la_E0_corregida"])
         + ". Aparte, por su razón vigente (enmienda 8): " + "; ".join(f"{x['to']}¹ {x['paginas']} pp. y {x['unidades']} u"
                                                                     for x in ns["ri_spi_y_ri_con"]) + ".",
         "cifras_punto3_S2b.json", "no_segmentables_y_parciales")
    g = cc["4e"]["corregida"]
    fila("4", "Las cifras y la tabla de los grupos de documentos, con la fila de lo que queda fuera del grafo (4.e)",
         f"Escritos en puntos: {g['puntos_de_principio_a_fin']['tos']} documentos, {miles(g['puntos_de_principio_a_fin']['paginas'])} páginas, "
         f"{miles(g['puntos_de_principio_a_fin']['unidades'])} unidades; con fichas y listados: {g['fichas_y_listados']['tos']}, "
         f"{miles(g['fichas_y_listados']['paginas'])} y {g['fichas_y_listados']['unidades']}; no segmentables: {g['no_segmentables']['tos']}, "
         f"{g['no_segmentables']['paginas']} y {g['no_segmentables']['unidades']}; ri_spi¹ y ri_con¹: {g['ri_spi_y_ri_con']['tos']}, "
         f"{g['ri_spi_y_ri_con']['paginas']} y {g['ri_spi_y_ri_con']['unidades']}. La fila de lo que queda fuera, en §5, 4.e.",
         "cifras_conjuntos_clases_S2b.json", "4e")
    x = cc["4a"]["corregida"]
    fila("5", "La tabla de los conjuntos de la sección 3.6 (4.a)",
         f"Desarrollo {x['desarrollo']['tos']} documentos, {miles(x['desarrollo']['unidades'])} unidades; validación {x['validacion']['tos']} "
         f"y {x['validacion']['unidades']}; universo {x['universo_152']['tos']} y {miles(x['universo_152']['unidades'])}; por tipo, en §5, 4.a.",
         "cifras_conjuntos_clases_S2b.json", "4a.corregida")
    fila("6", "La tabla de reglas del apéndice: las reglas vigentes, con los documentos que usa cada una (4.d)",
         f"Las {len(rg['capa_a_D3'])} reglas de la tabla legada, con el mismo criterio, sobre los 152; las "
         f"{len(rg['capa_b_rastro_en_la_salida'])} de e0-r2 con rastro en la salida; las de S0 sin rastro, declaradas. En §5, 4.d.",
         "reglas_por_to_S2b.json", "capa_a_D3; capa_b_rastro_en_la_salida; capa_c_sin_rastro")
    pp = p3["partidas_por_tamano"]
    fila("7", "Las unidades partidas por tamaño: cuántas, en cuántas partes, y las que quedan sin partir, con su causa",
         f"{pp['unidades_partidas']} unidades en {pp['partes']} partes; {pp['sin_partir']} sin partir ("
         + ", ".join(f"{k} {v}" for k, v in pp["sin_partir_por_motivo"].items()) + "). La lista, en §4.",
         "cifras_punto3_S2b.json", "partidas_por_tamano")
    tb = p3["tablas"]
    fila("8", "La regla de tablas: en cuántos TOs corre, en cuántos encuentra tablas y cuántas unidades llevan una tabla serializada",
         f"Corre en {tb['tos_donde_corre']}; encuentra tablas en {tb['tos_con_tablas']} ({tb['tablas']} tablas, {tb['tablas_serializadas']} "
         f"serializadas); {tb['unidades_con_tabla_serializada']} unidades llevan una tabla serializada, en "
         f"{tb['tos_con_unidades_con_tabla_serializada']} TOs.", "cifras_punto3_S2b.json", "tablas")
    # marcas
    doce_txt = "; ".join(f"{marcar_to(t)}: {pt[t]['unidades']} u. (" + ", ".join(f"{k} {v}" for k, v in pt[t]["por_tipo"].items())
                         + ")" + (f", reglas con rastro: {', '.join(sorted(set(usa.get(t, []))))}" if usa.get(t) else "") for t in doce)
    fila("M1", f"Cap. 4, al final del párrafo de los no segmentables, sobre el último, el que «tiene normas con una numeración propia»: "
               f"`{MARCAS[0]}`",
         "El texto vigente del párrafo está en Overleaf, no en el repo (CLAUDE.md §2): no identifico cuál es ese documento. Para cada uno "
         "de los 12 no segmentables de la partición legada, si la E0 corregida lo reconoce (lo lee por puntos) y con qué reglas: "
         + doce_txt + ". Solo ri_spi¹ queda leído por puntos (87 puntos terminales), con la regla 4 de S0; ri_con¹ queda en 34 "
                      "bloques sin puntos por la regla A de S0-6a; los otros 10 siguen sin puntos.",
         "cifras_punto3_S2b.json; reglas_por_to_S2b.json", "por_to.<to>.por_tipo; capa_b_rastro_en_la_salida",
         "en parte: falta saber de qué documento habla el párrafo")
    cambios = ", ".join(f"{t} {x['paginas_distintas']} ({', '.join(f'{k} {v}' for k, v in x['cambios'].items())}; pp. "
                        f"{', '.join(map(str, x['paginas']))})" for t, x in rp["por_to"].items() if x["paginas_distintas"])
    roles = ", ".join(f"{r} {miles(roles_cor[r])} / {miles(roles_leg[r])}" for r in sorted(set(roles_cor) | set(roles_leg)))
    fila("M2", f"Cap. 3, tabla de las formas del contenido: `{MARCAS[1]}`",
         f"Cambiaron: {rp['paginas_de_otro_rol']} páginas en {rp['tos_con_paginas_de_otro_rol']} TOs, de los roles que usa la tabla "
         f"(VERIF-FORMAS-SEG) a los de la E0 corregida: {cambios}. Páginas por rol sobre los 157, corregida / legada (`conteos.json`): "
         f"{roles}. El recuento no lo hago: el script de VERIF-FORMAS-SEG reconstruye los roles con el e0_lib legado (`78a757c`) y no "
         "tiene opción para leer los de e0-r2 (`recuento_formas_texto_completo.py:200-212, 303-312`); correrlo así recontaría con los "
         "roles viejos, y adaptarlo es otra unidad.",
         "roles_pagina_S2b.json", "por_to; paginas_de_otro_rol", "no: los roles cambiaron y el recuento pide adaptar el script")
    fila("M3", f"Apéndice, tabla de las reglas: `{MARCAS[2]}`",
         f"El uso de cada regla por documento está en §5, 4.d: la capa A rehace la tabla legada sobre los 152 (las reglas de tablas "
         f"corren en los 152 y actúan en hasta {max(f['tos'] for f in rg['capa_a_D3'] if f['unidad'] == 'B5.8.3')} TOs); la capa B "
         "agrega las reglas de e0-r2 con rastro en la salida.",
         "reglas_por_to_S2b.json", "capa_a_D3; capa_b_rastro_en_la_salida")
    md = ["Archivo: `marcas_4g_S2b.json`. Las filas 1 a 8 son las mínimas del mandato (`:348-361`); M1 a M3, las marcas de la tesis "
          "vigente que da el despacho de S2, con su texto tal cual. No entran las de U-BLOQUE-A.", "",
          "| fila | a qué se refiere | cifra o dato | archivo | clave | ¿se resuelve con S2? |", "|---|---|---|---|---|---|"]
    for f in filas:
        md.append(f"| {f['n']} | {esc(f['que'])} | {esc(f['dato'])} | `{f['archivo']}` | `{f['clave']}` | {f['resuelve']} |")
    out = {"filas": filas, "roles_por_pagina_157": {"corregida": dict(roles_cor), "legada": dict(roles_leg)}, "texto_md": "\n".join(md)}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(md))


def marcar_to(t: str) -> str:
    return f"{t}¹" if t in ("ri_spi", "ri_con") else t


if __name__ == "__main__":
    main()
