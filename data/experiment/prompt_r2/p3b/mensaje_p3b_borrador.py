"""
mensaje_p3b_borrador.py — U-PROMPT-R2, P3b-1 (USD 0, sin API): borrador del mensaje de E1 (puntos g y h) y de la
NOTA de E3 sobre las omisiones declaradas (punto i), con sus conteos sobre la e0-r2 de la tanda 0
(`e0_chunking/salida_tanda0_r2`, versionada en `f8dedd4`).

g (hallazgo 1.2). Ítem de una lista: chunk de punto cuya herencia trae un bloque que no es de cierre y termina en
«:», y después de él solo bloques de cierre (`tipo` = «cierre»), o ninguno. Un cierre que termina en «:» (el que
presenta una fórmula, por ejemplo) no abre la lista de los ítems. Hoy (`prompt_r2b.es_item`) se exige que el ÚLTIMO bloque
termine en «:», y los ítems a los que E0 les hereda además los párrafos de cierre del padre quedan sin marca. La
regla nueva da el mismo resultado si C2 de U-R2-CODIGO-2 recorta la herencia (punto h de ese mandato): sin bloques
de cierre, el bloque con «:» es el último.

h (hallazgo 2.16). Mini-chunk que empieza a mitad de una oración: el último bloque heredado es el `encabezado` de la
misma unidad y no termina en «.», «:» ni «;», y el texto del bloque empieza en minúscula. E0 tomó la primera línea
del punto como título: esa línea es el comienzo de la oración del bloque.

i (hallazgo 3.4). NOTA de E3 cuando la extracción declara omisiones de las categorías que el esquema no extrae a
propósito (`meta_normativo`, `fuera_de_tipos`, `relacion_sin_predicado`): en el mensaje de E3 aparecen como
«[categoría] tramo — nota» en el bloque de omisiones (validador_e1.proyectar_r2).

Escribe en --salida:
  - mensaje_p3b.json: conteos y ejemplos;
  - mensaje_p3b_lado_a_lado.md: el mensaje congelado y el nuevo de los casos de control;
  - literales_mensaje_p3b.txt: el texto fijo nuevo (para la no-filtración).

Uso (desde la raíz de una copia del repo):
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/prompt_r2/p3b/mensaje_p3b_borrador.py --salida DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

P3B = Path(__file__).resolve().parent
REPO = P3B.parents[3]
REX = REPO / "data" / "experiment" / "reextraccion_v2"
sys.path.insert(0, str(REX / "e1_extractor"))
sys.path.insert(0, str(REPO / "data" / "experiment" / "pyd_r2" / "code"))
import comun_e1  # noqa: E402
import prompt_r2b as P  # noqa: E402
import validador_r2 as V  # noqa: E402

E0_R2 = REX / "e0_chunking" / "salida_tanda0_r2"
TOS = ("pro", "cla", "ric", "cap", "ext", "ctacte", "lingob", "polcre", "pagjub", "docvig")
CASOS = ("cap::8.5.1", "pro::4.2.1::intro", "cap::2.7.2::intro", "cla::5.1.1.1", "cla::5.1.1::intro")
FIN_DE_ORACION = (".", ":", ";", "：")

# ---- texto fijo nuevo -------------------------------------------------------------------------------------------
LINEA_ITEM = ("Contexto estructural heredado (contexto y anclaje; NO extraigas contenido normativo de estos bloques, "
              "salvo un caso: el bloque [{tipo} | punto {unidad}] termina en «:» y abre la lista de la que este punto "
              "es un ítem{cierres}, así que la norma del ítem se compone con ese encabezado — ver COMPOSICIÓN CON EL "
              "ENCABEZADO DE UNA LISTA):")
CIERRES = "; los bloques que lo siguen son párrafos de cierre del punto que lo contiene, no parte del encabezado"
LINEA_MINI_MITAD = ("Cadena de títulos (ubica el bloque; NO es contenido a extraer, salvo su última línea: E0 la tomó "
                    "como título, pero es el comienzo de la oración que sigue en tu bloque. Leela con el bloque, "
                    "extraé la oración entera, y el `tramo` puede empezar en esa línea):")
NOTA_E3_OMISIONES = (
    "NOTA: el extractor declaró, en las omisiones, tramos que el esquema deja afuera a propósito: "
    "[meta_normativo] (contenido sobre el sentido, el alcance, el objetivo o la vigencia de una norma, que no "
    "prescribe la conducta de nadie), [fuera_de_tipos] (contenido normativo que ningún tipo del esquema representa) "
    "y [relacion_sin_predicado] (un vínculo que ningún predicado del esquema representa). Un tramo declarado así no "
    "es un faltante: no lo reclames. Sí es un faltante si lo declarado no es lo que dice su categoría (por ejemplo, "
    "un deber o una prohibición declarados como meta-normativos).")
CATEGORIAS_NOTA = ("meta_normativo", "fuera_de_tipos", "relacion_sin_predicado")
# k, defensa 1 (agregado 2 del 04/10/2026): frase que se suma al bloque de feedback del reintento, solo con la forma r2.
AVISO_NOTA_REINTENTO = ("Las notas del verificador explican qué falta y por qué; no son texto de la norma: no copies "
                        "sus palabras en descripciones, etiquetas ni tramos. Todo lo que extraigas sale del texto de "
                        "la unidad.")


def bloque_lista(chunk: dict) -> int | None:
    """g: índice del bloque heredado que abre la lista de la que el chunk es ítem, o None."""
    if comun_e1.es_mini_chunk(chunk):
        return None
    her = chunk.get("herencia") or []
    idx = [i for i, h in enumerate(her) if h["tipo"] != "cierre"
           and " ".join(h["texto"].split()).endswith((":", "："))]
    if not idx:
        return None
    i = idx[-1]
    return i if all(h["tipo"] == "cierre" for h in her[i + 1:]) else None


def mini_a_mitad(chunk: dict) -> bool:
    """h: el mini-chunk empieza a mitad de la oración que arranca en su última línea de títulos."""
    if not comun_e1.es_mini_chunk(chunk):
        return False
    her = chunk.get("herencia") or []
    if not her:
        return False
    h = her[-1]
    titulo = " ".join(h["texto"].split())
    texto = (chunk.get("texto") or "").lstrip()
    return (h["tipo"] == "encabezado" and h["unidad_origen"] == chunk["unidad"]
            and not titulo.endswith(FIN_DE_ORACION) and bool(texto) and texto[0].islower())


def build_user_message_p3b(chunk: dict) -> str:
    """El mensaje de prompt_r2b.build_user_message_r2b con los cambios g y h."""
    partes: list[str] = []
    mini = comun_e1.es_mini_chunk(chunk)
    partes.append(f"Documento fuente: {chunk['archivo']}")
    partes.append(f"TO: {chunk['to']}")
    if mini:
        partes.append(f"Tipo de unidad: MINI-CHUNK de bloque estructural ({chunk['rol_bloque']} del punto "
                      f"{chunk['unidad']})")
        partes.append(f"Unidad de origen: {chunk['unidad']} — {chunk['titulo']}")
    else:
        partes.append("Tipo de unidad: chunk de punto")
        partes.append(f"Punto del chunk: {chunk['unidad']} — {chunk['titulo']}")
    partes.append("Puntos admitidos para `punto`: " + ", ".join(comun_e1.puntos_admitidos(chunk)))
    partes.append("")
    partes.extend(P.linea_alcance(P.ROL_POR_TO_R2.get(chunk["archivo"])))
    herencia = chunk.get("herencia", [])
    if herencia:
        i = bloque_lista(chunk)
        if mini:
            partes.append(LINEA_MINI_MITAD if mini_a_mitad(chunk)
                          else "Cadena de títulos (ubica el bloque; NO es contenido a extraer):")
        elif i is not None:
            h = herencia[i]
            partes.append(LINEA_ITEM.format(tipo=h["tipo"], unidad=h["unidad_origen"],
                                            cierres=CIERRES if i < len(herencia) - 1 else ""))
        else:
            partes.append("Contexto estructural heredado (SOLO contexto y anclaje: NO extraigas contenido normativo "
                          "de estos bloques — cada uno tiene su propia unidad de extracción; ver PROVENANCE):")
        for h in herencia:
            partes.append(f"[{h['tipo']} | punto {h['unidad_origen']}]")
            partes.append(h["texto"])
        partes.append("")
    partes.extend(P.bloque_flags(chunk))
    if mini:
        partes.append(f"Texto del bloque {chunk['rol_bloque']} del punto {chunk['unidad']} (TU unidad de extracción):")
    else:
        partes.append(f"Texto del punto {chunk['unidad']}:")
    partes.append("```")
    partes.append(chunk["texto"])
    partes.append("```")
    partes.append("")
    partes.append("Extraé las entidades y relaciones según el schema. Recordá: nodo TextoOrdenado con local_id='to'; "
                  "todo elemento con `punto` de la lista admitida; toda entidad con su `tramo`; toda relación de "
                  "sujeto con su `sujeto_mencion`; `omisiones` siempre (vacía si no omitiste nada).")
    return "\n".join(partes)


def nota_e3_omisiones(validacion: dict | None) -> str | None:
    """i: la NOTA, si la validación (forma r2) declara omisiones de esas categorías."""
    if not validacion or validacion.get("forma_salida") != "r2":
        return None
    cats = {o.split("]", 1)[0].lstrip("[") for o in validacion.get("omisiones_no_prosa") or []
            if isinstance(o, str) and o.startswith("[")}
    return NOTA_E3_OMISIONES if cats & set(CATEGORIAS_NOTA) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    sal = ap.parse_args().salida.resolve()
    if REPO in sal.parents or sal == REPO:
        raise SystemExit("--salida no puede estar dentro del repo")
    sal.mkdir(parents=True, exist_ok=True)
    chunks = comun_e1.cargar_chunks(TOS, e0_dir=E0_R2)
    items_hoy = [c for c in chunks if P.es_item(c)]
    items_p3b = [c for c in chunks if bloque_lista(c) is not None]
    agregados = [c for c in items_p3b if not P.es_item(c)]
    minis = [c for c in chunks if comun_e1.es_mini_chunk(c)]
    a_mitad = [c for c in minis if mini_a_mitad(c)]
    minuscula = [c for c in minis if (c.get("texto") or "").lstrip()[:1].islower()]
    # h, el par en la verificación del tramo: un tramo que cruza del título al cuerpo
    cruzan = {"verifica_hoy": 0, "verifica_en_orden_de_lectura": 0}
    for c in a_mitad:
        titulo = c["herencia"][-1]["texto"].split()
        cuerpo = c["texto"].split()
        if titulo[-1].endswith("-"):     # palabra cortada entre el título y el cuerpo: se copia unida
            titulo, cuerpo = titulo[:-1] + [titulo[-1][:-1] + cuerpo[0]], cuerpo[1:]
        tramo = " ".join(titulo[-4:] + cuerpo[:4])
        cruzan["verifica_hoy"] += V.verificar_tramo(tramo, V.texto_completo(c), 2)[0] == "exacta"
        cruzan["verifica_en_orden_de_lectura"] += V.verificar_tramo(
            tramo, c["herencia"][-1]["texto"] + "\n" + c["texto"], 2)[0] == "exacta"
    cambian = [c for c in chunks if build_user_message_p3b(c) != P.build_user_message_r2b(c)]
    res = {"comando": "data/experiment/prompt_r2/p3b/mensaje_p3b_borrador.py --salida DIR",
           "e0": str(E0_R2.relative_to(REPO)), "unidades": len(chunks),
           "g_items": {"hoy": len(items_hoy), "con_la_regla_nueva": len(items_p3b), "agregados": len(agregados),
                       "perdidos": sum(1 for c in items_hoy if bloque_lista(c) is None),
                       "agregados_por_to": dict(Counter(c["to"] for c in agregados).most_common()),
                       "cap_8_5": [c["id"] for c in agregados if c["id"].startswith("cap::8.5.")]},
           "h_minis": {"minis": len(minis), "a_mitad_de_oracion": len(a_mitad),
                       "texto_en_minuscula": len(minuscula),
                       "minuscula_y_no_a_mitad": [c["id"] for c in minuscula if c not in a_mitad],
                       "tramo_titulo_cuerpo_de_8_palabras": cruzan,
                       "ejemplos": [c["id"] for c in a_mitad][:10]},
           "mensajes_que_cambian": len(cambian),
           "mensajes_que_cambian_por_motivo": {"item": sum(1 for c in cambian if bloque_lista(c) is not None),
                                               "mini_a_mitad": sum(1 for c in cambian if mini_a_mitad(c))}}
    (sal / "mensaje_p3b.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    por_id = {c["id"]: c for c in chunks}
    md = ["# Mensaje de E1: congelado y P3b, en los casos de control", ""]
    for cid in CASOS:
        c = por_id.get(cid)
        if c is None:
            md += [f"## {cid}", "", "NO ENCONTRADO en la e0-r2 de la tanda 0.", ""]
            continue
        a, b = P.build_user_message_r2b(c), build_user_message_p3b(c)
        md += [f"## {cid}", "", "Igual al congelado." if a == b else "", ""]
        if a != b:
            la, lb = a.splitlines(), b.splitlines()
            dif = [(x, y) for x, y in zip(la, lb) if x != y]
            for x, y in dif:
                md += ["Congelado:", "", "```text", x, "```", "", "P3b:", "", "```text", y, "```", ""]
    md += ["## NOTA de E3 sobre las omisiones declaradas (punto i)", "", "```text", NOTA_E3_OMISIONES, "```", "",
           "## Aviso del reintento sobre las notas de E3 (punto k, defensa 1)", "", "```text", AVISO_NOTA_REINTENTO,
           "```", ""]
    (sal / "mensaje_p3b_lado_a_lado.md").write_text("\n".join(md), encoding="utf-8")
    (sal / "literales_mensaje_p3b.txt").write_text("\n".join(
        [LINEA_ITEM.format(tipo="", unidad="", cierres=CIERRES), LINEA_MINI_MITAD, NOTA_E3_OMISIONES,
         AVISO_NOTA_REINTENTO]) + "\n",
        encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
