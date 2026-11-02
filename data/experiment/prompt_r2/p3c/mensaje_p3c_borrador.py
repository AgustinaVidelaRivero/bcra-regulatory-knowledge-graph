"""
mensaje_p3c_borrador.py — U-PROMPT-R2, P3c-1 (USD 0, sin API): borrador de lo que P3c cambia fuera del prefijo, con
sus conteos sobre la E0 que lee U-REEXT-T0 (`e0_chunking/salida_tanda0_r2b`, `9f6361e`):
  - e: la línea «Alcance de este TO» del mensaje de E1 (`prompt_r2b.linea_alcance`): la mención se copia del texto y,
    si el texto no nombra a ningún sujeto, no hay relación;
  - a: la NOTA de E3 de las omisiones de esquema (`prompt_e3.NOTA_E3_OMISIONES`), alineada con la regla 9 nueva (sin
    el alcance en `meta_normativo`, y con la lista completa de lo que no puede ser `meta_normativo`);
  - b: la última oración de la NOTA de E3 del encabezado de lista (`prompt_e3.notas_r2`), con la excepción cuyas
    condiciones son los ítems;
  - f: `cap::tabla037` en la lista de tablas forzadas a residual (`tablas_residuales_forzadas_r2b.json`): el mensaje
    de E1 y la NOTA de E3 de las unidades que la traen.
Los textos nuevos se aplican en memoria sobre los módulos importados (no se edita ningún archivo).

Escribe en --salida:
  - mensaje_p3c.json: conteos de unidades cuyo mensaje cambia, por punto;
  - mensaje_p3c_lado_a_lado.md: lo congelado y lo nuevo, en unidades de control;
  - literales_mensaje_p3c.txt: el texto fijo nuevo (para la no-filtración);
  - tablas_residuales_forzadas_r2b_p3c.json: la lista con el alta de f, como quedaría.

Uso (desde la raíz de una copia del repo):
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/prompt_r2/p3c/mensaje_p3c_borrador.py --salida DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

P3C = Path(__file__).resolve().parent
REPO = P3C.parents[3]
REX = REPO / "data" / "experiment" / "reextraccion_v2"
for sub in ("e1_extractor", "e3_verificador"):
    sys.path.insert(0, str(REX / sub))
import prompt_r2b as P  # noqa: E402
import prompt_e3  # noqa: E402

E0_R2B = REX / "e0_chunking" / "salida_tanda0_r2b"
TOS = ("pro", "cla", "ric", "cap", "ext", "ctacte", "lingob", "polcre", "pagjub", "docvig")
TABLA_F = "cap::tabla037"
FECHA_F = "2026-10-04"
MOTIVO_F = ("La pareada de U-PROMPT-R2 (P4, cap::6.2.2.6) asoció una cuantía de una celda combinada sin asignar a una "
            "banda equivocada; la nota del 03/10/2026 al mandato manda la tabla a residual.")

# ---- texto fijo nuevo -------------------------------------------------------------------------------------------
ALCANCE_VIEJO = ("Cuando la norma se dirija genéricamente a 'las entidades' / 'los sujetos obligados' / el colectivo "
                 "del TO, {sug}, con la expresión del texto como `sujeto_mencion`. Es el sujeto de aplica_a cuando la "
                 "norma se dirige al colectivo; NO es el ejecutor por defecto en ejecuta.")
ALCANCE_NUEVO = ("Cuando el texto (el de tu unidad o el heredado) nombre al colectivo del TO con una expresión genérica "
                 "('las entidades', 'los sujetos obligados'), {sug}, con esa expresión copiada del texto como "
                 "`sujeto_mencion`. Si el texto no nombra a ningún sujeto, no emitas la relación: este alcance no "
                 "reemplaza la mención. Es el sujeto de aplica_a cuando el texto se dirige al colectivo; NO es el "
                 "ejecutor por defecto en ejecuta.")
NOTA_OMISIONES_NUEVA = (
    "NOTA: el extractor declaró, en las omisiones, tramos que el esquema deja afuera a propósito: "
    "[meta_normativo] (contenido sobre el sentido, el objetivo o la entrada en vigencia de una norma, que no prescribe "
    "la conducta de nadie ni dice a quién o a qué se aplica), [fuera_de_tipos] (contenido normativo que ningún tipo del "
    "esquema representa) y [relacion_sin_predicado] (un vínculo que ningún predicado del esquema representa). Un tramo "
    "declarado así no es un faltante: no lo reclames. Sí es un faltante si lo declarado no es lo que dice su categoría: "
    "un deber, una prohibición, una facultad, una condición, una excepción, un alcance o una modalidad declarados como "
    "meta-normativos.")
ENCABEZADO_VIEJO = ("Sí es faltante, si no fue extraído, lo que el encabezado enuncia aparte de la lista: una norma "
                    "propia, una excepción a la lista entera, o la norma principal cuando los ítems son sus supuestos o "
                    "condiciones.")
ENCABEZADO_NUEVO = ("Sí es faltante, si no fue extraído, lo que el encabezado enuncia aparte de la lista: una norma "
                    "propia, una excepción a la lista entera, la norma principal cuando los ítems son sus supuestos o "
                    "condiciones, o la norma y su excepción cuando los ítems son las condiciones de esa excepción.")


def linea_alcance_p3c(rol: dict | None) -> list[str]:
    """La de prompt_r2b.linea_alcance con la oración nueva de e; la cabecera y la sugerencia no cambian."""
    if rol is None:
        return []
    miembros = ", ".join(rol["miembros_labels"])
    if rol.get("rol_id"):
        cab, sug = f"Alcance de este TO: {rol['rol_id']} = {{{miembros}}}. ", f"sugerí {rol['rol_id']} en `sujeto_id`"
    else:
        ids = " o ".join(rol["clase_ids"])
        cab, sug = f"Alcance de este TO: {{{miembros}}}. ", f"sugerí {ids} en `sujeto_id`, según corresponda"
    return [cab + ALCANCE_NUEVO.format(sug=sug), ""]


def cargar() -> list[dict]:
    out = []
    for to in TOS:
        out += json.loads((E0_R2B / f"chunks_{to}.json").read_text(encoding="utf-8"))
    return out


def con_tabla(c: dict, tabla: str) -> bool:
    return any(t["tabla"] == tabla and t.get("serializada") for t in (c.get("flags") or {}).get("tablas_e0") or [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    sal = ap.parse_args().salida.resolve()
    if REPO in sal.parents or sal == REPO:
        raise SystemExit("--salida no puede estar dentro del repo")
    sal.mkdir(parents=True, exist_ok=True)
    # el texto viejo del borrador es el que arma hoy el código (control)
    ejemplo = {"rol_id": "X", "miembros_labels": ["a"]}
    viejo_hoy = P.linea_alcance(ejemplo)[0]
    assert viejo_hoy.endswith(ALCANCE_VIEJO.format(sug="sugerí X en `sujeto_id`")), viejo_hoy
    assert ENCABEZADO_VIEJO in " ".join(prompt_e3.notas_r2(
        {"tipo": "mini_chunk", "rol_bloque": "intro", "texto": "x:", "flags": {}}, None))
    chunks = cargar()
    base = {c["id"]: P.build_user_message_r2b(c) for c in chunks}
    nota_base = {c["id"]: prompt_e3.notas_r2(c, None) for c in chunks}

    # e: la línea de alcance
    P.linea_alcance, original = linea_alcance_p3c, P.linea_alcance
    try:
        e_msg = {c["id"]: P.build_user_message_r2b(c) for c in chunks}
    finally:
        P.linea_alcance = original
    cambia_e = sorted(cid for cid in base if e_msg[cid] != base[cid])
    sin_rol = sorted({c["to"] for c in chunks if P.ROL_POR_TO_R2.get(c["archivo"]) is None})
    # f: la tabla forzada
    P.TABLAS_RESIDUALES_FORZADAS, forz0 = frozenset({TABLA_F}), P.TABLAS_RESIDUALES_FORZADAS
    try:
        f_msg = {c["id"]: P.build_user_message_r2b(c) for c in chunks if con_tabla(c, TABLA_F)}
        f_nota = {cid: prompt_e3.notas_r2(next(c for c in chunks if c["id"] == cid), None) for cid in f_msg}
    finally:
        P.TABLAS_RESIDUALES_FORZADAS = forz0
    cambia_f = sorted(cid for cid in f_msg if f_msg[cid] != base[cid])
    cambia_f_e3 = sorted(cid for cid in f_nota if f_nota[cid] != nota_base[cid])
    # b: la NOTA del encabezado de lista (va en las unidades de encabezado)
    encabezados = sorted(cid for cid, ns in nota_base.items() if any(ENCABEZADO_VIEJO in n for n in ns))
    # a: la NOTA de omisiones va donde la extracción declare esas categorías: no se cuenta sin la salida de E1

    controles_e = [cid for cid in ("ric::4.1.1.1", "cap::8.5.1", "docvig::3.3::cierre") if cid in base]
    md = ["# Mensaje de E1 y NOTAS de E3: congelado y P3c, en unidades de control", ""]
    md += ["## e: la línea «Alcance de este TO» (mensaje de E1)", ""]
    for cid in controles_e:
        lv = next((x for x in base[cid].split("\n") if x.startswith("Alcance de este TO")), "(sin línea de alcance)")
        ln = next((x for x in e_msg[cid].split("\n") if x.startswith("Alcance de este TO")), "(sin línea de alcance)")
        md += [f"### {cid}", "", "Congelado:", "", "```text", lv, "```", "", "P3c:", "", "```text", ln, "```", ""]
    md += ["## a: NOTA de E3 de las omisiones de esquema", "", "Congelado:", "", "```text",
           prompt_e3.NOTA_E3_OMISIONES, "```", "", "P3c:", "", "```text", NOTA_OMISIONES_NUEVA, "```", ""]
    md += ["## b: última oración de la NOTA de E3 del encabezado de lista", "", "Congelado:", "", "```text",
           ENCABEZADO_VIEJO, "```", "", "P3c:", "", "```text", ENCABEZADO_NUEVO, "```", ""]
    md += ["## f: `cap::tabla037` a residual", ""]
    for cid in cambia_f:
        bv = [x for x in base[cid].split("\n") if x.startswith(("TABLAS", "- `", "FLAGS", "Tablas", "E0 detectó"))]
        bn = [x for x in f_msg[cid].split("\n") if x.startswith(("TABLAS", "- `", "FLAGS", "Tablas", "E0 detectó"))]
        md += [f"### {cid}: bloque de tablas del mensaje de E1", "", "Congelado:", "", "```text", *bv, "```", "",
               "P3c:", "", "```text", *bn, "```", "", f"### {cid}: NOTA de E3", "", "Congelado:", "", "```text",
               *nota_base[cid], "```", "", "P3c:", "", "```text", *f_nota[cid], "```", ""]
    (sal / "mensaje_p3c_lado_a_lado.md").write_text("\n".join(md), encoding="utf-8")
    lit = [ALCANCE_NUEVO.format(sug=""), NOTA_OMISIONES_NUEVA, ENCABEZADO_NUEVO]
    (sal / "literales_mensaje_p3c.txt").write_text("\n".join(lit) + "\n", encoding="utf-8")
    lista = json.loads(P.TABLAS_FORZADAS_JSON.read_text(encoding="utf-8"))
    lista["tablas"].append({"tabla": TABLA_F, "motivo": MOTIVO_F, "fecha": FECHA_F})
    (sal / "tablas_residuales_forzadas_r2b_p3c.json").write_text(
        json.dumps(lista, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    por_to = Counter(c["to"] for c in chunks if c["id"] in set(cambia_e))
    res = {"comando": "data/experiment/prompt_r2/p3c/mensaje_p3c_borrador.py --salida DIR",
           "e0": str(E0_R2B.relative_to(REPO)), "unidades": len(chunks),
           "e_linea_alcance": {"cambia_mensaje_e1": len(cambia_e), "por_to": dict(sorted(por_to.items())),
                               "tos_sin_linea_de_alcance": sin_rol},
           "f_tabla_forzada": {"tabla": TABLA_F, "unidades_con_la_tabla": sorted(f_msg),
                               "cambia_mensaje_e1": cambia_f, "cambia_nota_e3": cambia_f_e3},
           "b_nota_encabezado_de_lista": {"unidades_con_la_nota": len(encabezados)},
           "a_nota_omisiones": "va en las unidades cuya extracción declare meta_normativo, fuera_de_tipos o "
                               "relacion_sin_predicado: depende de la salida de E1"}
    (sal / "mensaje_p3c.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
