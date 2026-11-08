"""
analisis_validacion_v3.py — el análisis de la validación de la v3 congelada del juez de tripletas (etapa c, USD 0; lo corre
la autora después de la validación paga). Rige la enmienda 5 (firmada en el commit 6d9fbf10) del pre-registro de tripletas,
punto 9, que remite al §4.6 y al punto 8 de la enmienda 4. No llama a la API.

Qué aplica, sobre las 100 fichas del acta de la validación (el agregado de la v3 congelada contra la lectura sellada de la
autora, solo «correcta»):
  - el §4.6 en lo que toca a «correcta», por criterios() de la v1 (analisis_gold_juez_v.py, el que importa
    analisis_T_v2.py, sin copiarlo ni cambiarlo), en sus tres partes: (i) el acuerdo en dos clases sobre las fichas que
    deciden los dos, en proporción 0,84; (ii) entre la precisión que da el juez y la que da la autora, sobre esas mismas
    fichas, una distancia de 0,05 como máximo, tanto en la cruda como en la ponderada, y cada distancia se redondea a diez
    decimales antes de compararla (así lo fijó la enmienda 4 en su punto 8); (iii) entre las que el juez decide, de las
    que la autora tiene por incorrectas, la mitad o más también lo son para el juez. Pasa si se cumplen las tres, con la
    (ii) en sus dos formas;
  - la ponderada de (ii) tiene un solo estrato, el predicado, con W_h = N_h / N del acta (poblacion_por_predicado): la
    misma cuenta que usó la prueba de la v2, fijada antes de la validación y sin ningún resultado a la vista; no hay
    otra ponderada ni una opción para elegirla;
  - al lado, como descriptiva y fuera del pase: la (ii), cruda y ponderada, recalculada solo sobre las fichas que la
    autora marcó esenciales. Se informa y no decide nada;
  - aparte, sin entrar en el pase: las que la v3 manda a adjudicación (o deja sin consenso), con su proporción, y si
    pasan de 15 en 100 (en ese caso el JSON declara esa frontera del instrumento); el kappa de Cohen de «correcta», que
    se informa y no es umbral. La v3 no juzga la importancia: no hay condición de importancia.
Si la validación no se completó (su declaración, con la forma que valida analisis_T_v2.validar_no_completada), no pasa, y
no se lee ninguna hoja.

Lo que toma de analisis_T_v2.py (v2/codigo/, sha256 47e4128b…, el del commit 8b45dc7a), importado sin editarlo:
validar_no_completada (la declaración) y a_adjudicacion (las que el juez no decide); y, por él, criterios() de la v1. La
lectura de las hojas es casos_v3.leer_hojas_T (la de analisis_T_v2.py, copiada sin cambios en la etapa a), con el campo
acta_sorteo_T_v3.json_sha256 y los lotes lote_v3_01 a lote_v3_10 (el formato del sellador de la mesa, sellar_hoja_v3.py).

Antes de leer una hoja: el sello conjunto de la lectura de validación (su sha256, y cada hoja y cada sello que nombra, por
su sha256 desde tripletas_t_v3/); el acta, con su sha256 y su sello; el registro de la congelación y el agregado (el prompt
congelado en el agregado y en cada ficha, 0 cruces, el modelo, el esfuerzo y las 100 fichas del acta).
Escribe v3/corridas/validacion/analisis_validacion_v3.json (no pisa uno existente). La consola dice solo si pasa o no y por
qué condición. rc 0: escrito; un FRENO no escribe nada.

  .venv/bin/python -B analisis_validacion_v3.py [--corridas C] [--tt3 D] [--sello-lectura-v3 S] [--registro R]
      [--salida D]
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import hashlib  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import casos_v3 as CV  # noqa: E402
import congelar_v3 as CG  # noqa: E402
import correr_validacion_v3 as CVAL  # noqa: E402
import juez_v3 as J  # noqa: E402
import prompt_juez_v3 as PV  # noqa: E402
from v1_importada import AG  # noqa: E402

CODE_VER = "analisis-validacion-v3.2"
AT2_RUTA = CV.V2_REAL / "codigo" / "analisis_T_v2.py"
AT2_SHA256 = "47e4128be544b507c49f9eb2941331aec52993d4c64b1cbc084768bf8b019997"
CAMPO_ACTA = "acta_sorteo_T_v3.json_sha256"
LOTES = tuple(f"lote_v3_{i:02d}" for i in range(1, 11))
SALIDA_NOMBRE = "analisis_validacion_v3.json"
CONDICIONES = ("i", "ii_cruda", "ii_ponderada", "iii")
NOMBRE_CONDICION = {"i": "(i) el acuerdo en «correcta»", "ii_cruda": "(ii) la precisión, cruda",
                    "ii_ponderada": "(ii) la precisión, ponderada", "iii": "(iii) las incorrectas de la autora"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cargar_at2():
    """analisis_T_v2.py de la v2, importado por su ruta después de controlar su sha256 (sin editarlo ni copiarlo)."""
    if sha(AT2_RUTA.read_bytes()) != AT2_SHA256:
        raise SystemExit(f"FRENO: analisis_T_v2.py no es el del commit 8b45dc7a ({AT2_SHA256[:8]}…)")
    previo = sys.modules.get("analisis_T_v2")
    if previo is not None:
        return previo
    if str(AT2_RUTA.parent) not in sys.path:
        sys.path.append(str(AT2_RUTA.parent))
    spec = importlib.util.spec_from_file_location("analisis_T_v2", AT2_RUTA)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["analisis_T_v2"] = mod
    spec.loader.exec_module(mod)
    if mod.AG is not AG:
        raise SystemExit("FRENO: analisis_T_v2 no usa el analisis_gold_juez_v de la v1 que importa la v3")
    return mod


# --------------------------------------------------------------------------- #
# Las entradas                                                                #
# --------------------------------------------------------------------------- #
def del_acta(acta: dict) -> dict:
    """De las 100 del acta: ref -> predicado (por su código) y los W_h de predicado (poblacion_por_predicado)."""
    pred = {c: h for h, cs in acta["codigos"]["las_100"].items() for c in cs}
    refs = dict(zip(acta["codigos"]["orden"], acta["refs_en_orden"]))
    if set(pred) != set(refs) or len(refs) != CVAL.N_VALIDACION:
        raise SystemExit("FRENO: los códigos del acta no son los de sus 100 refs")
    n_h = acta["poblacion_por_predicado"]
    N = sum(n_h.values())
    if not N or set(pred.values()) - set(n_h):
        raise SystemExit("FRENO: el acta no trae los N_h de los predicados de sus 100")
    return {"predicado": {refs[c]: pred[c] for c in refs}, "W_h": {h: v / N for h, v in n_h.items()}, "N": N}


def leer_agregado(d: dict, refs: set[str], prompt_sha: str) -> dict[str, dict]:
    """ref -> {veredicto, via} (los modales) del agregado de la validación: el modo, 0 cruces, el modelo, el esfuerzo, la
    versión del código y del prompt, el prompt congelado en el agregado y en cada ficha, las tres repeticiones y las 100."""
    if not isinstance(d, dict) or (d.get("verificacion_cross_hits") or {}).get("cross_hits") != 0:
        raise SystemExit("FRENO: el agregado no trae la verificación de 0 cruces entre las tres bases")
    esperado = {"modo": CVAL.MODO, "modelo": J.MODELO, "esfuerzo": J.ESFUERZO, "code_ver_base": J.CODE_VER_BASE,
                "version_prompt": PV.VERSION, "prompt_sha256": prompt_sha, "reps": J.REPS}
    for campo, v in esperado.items():
        if d.get(campo) != v:
            raise SystemExit(f"FRENO: el agregado trae {campo} {d.get(campo)!r}, no el de la v3 congelada")
    out = {}
    for x in d.get("fichas") or []:
        if x.get("prompt_sha256") != prompt_sha or x["ref"] in out:
            raise SystemExit("FRENO: una ficha del agregado no trae el prompt congelado, o está dos veces")
        try:
            out[x["ref"]] = {"veredicto": x["agregado"]["veredicto"]["modal"], "via": x["agregado"]["veredicto"]["via"]}
        except (KeyError, TypeError):
            raise SystemExit("FRENO: una ficha del agregado no trae su veredicto modal")
    if set(out) != set(refs):
        raise SystemExit("FRENO: el agregado no trae exactamente las 100 fichas del acta")
    return out


# --------------------------------------------------------------------------- #
# La regla de pase                                                            #
# --------------------------------------------------------------------------- #
def pares(juez: dict, autora: dict, estrato: dict[str, str]) -> list[dict]:
    """Los pares de criterios(): la clave `predicado` lleva el estrato de la ponderada; la v3 no da importancia."""
    return [{"ref": r, "predicado": estrato[r], "juez_veredicto": juez[r]["veredicto"], "juez_via": juez[r]["via"],
             "juez_importancia": None, "autora_correcta": autora[r]["correcta"],
             "autora_importancia": autora[r]["importancia"]} for r in sorted(juez)]


def condiciones(c: dict) -> dict:
    return {"i": bool(c["i_acuerdo"]["pasa"]), "ii_cruda": bool(c["ii_precision"]["cruda"]["pasa"]),
            "ii_ponderada": bool(c["ii_precision"]["ponderada"]["pasa"]), "iii": bool(c["iii_incorrectas"]["pasa"])}


def sin_importancia(c: dict) -> dict:
    """criterios() sin lo de la importancia del juez (la v3 no la juzga) ni su decision_46, que la pide."""
    return {k: v for k, v in c.items() if k not in ("importancia", "decision_46")}


def evaluar(juez: dict, autora: dict, del_acta_: dict, at2) -> dict:
    """El pase sale solo de criterios() con el estrato de predicado; las esenciales se calculan aparte y no lo tocan."""
    refs = sorted(juez)
    if set(autora) != set(refs):
        raise SystemExit("FRENO: la lectura de la autora no trae las 100 fichas del acta")
    rige = at2.AG.criterios(pares(juez, autora, del_acta_["predicado"]), del_acta_["W_h"])
    cond = condiciones(rige)
    pasa = all(cond.values())
    esenciales = [r for r in refs if autora[r]["importancia"] == "esencial"]
    ese = at2.AG.criterios(pares({r: juez[r] for r in esenciales}, autora, del_acta_["predicado"]), del_acta_["W_h"]) \
        if esenciales else None
    adj = at2.a_adjudicacion(juez)
    return {"pasa": pasa, "condiciones": cond, "fallan": [NOMBRE_CONDICION[k] for k in CONDICIONES if not cond[k]],
            "ponderada_de_ii": {"estrato": "predicado", "W_h": del_acta_["W_h"]},
            "criterios": sin_importancia(rige),
            "ii_sobre_las_esenciales_de_la_autora": None if ese is None else
            {"descriptiva": True, "entra_en_el_pase": False, "fichas": len(esenciales), "ii_precision": ese["ii_precision"],
             "pasaria_ii": condiciones(ese)["ii_cruda"] and condiciones(ese)["ii_ponderada"]},
            "adjudicacion": {"a_adjudicacion": len(adj), "proporcion": len(adj) / len(refs),
                             "mas_de_15": len(adj) > AG.UMBRAL_ADJUDICACION * len(refs),
                             "declaracion": "pasan de 15 en 100 las que van a adjudicación: es la frontera del "
                                            "instrumento" if len(adj) > AG.UMBRAL_ADJUDICACION * len(refs) else None,
                             "refs": adj},
            "kappa_correcta_reportado": rige["kappa_correcta"]}


def analizar(*, agregado: dict | None, no_completada: dict | None, autora: dict | None, acta: dict, prompt_sha: str,
             at2=None) -> dict:
    at2 = at2 or cargar_at2()
    if (agregado is None) == (no_completada is None):
        raise SystemExit("FRENO: va el agregado de la validación o su declaración de no completada: uno de los dos")
    da = del_acta(acta)
    if no_completada is not None:
        decl = at2.validar_no_completada(no_completada, CVAL.MODO)
        return {"code_ver": CODE_VER, "pasa": False, "decide": "la validación no se completó (enmienda 5, punto 13)",
                "fallan": ["la validación no se completó"], "validacion_no_completada": {"declaracion": decl}}
    juez = leer_agregado(agregado, set(da["predicado"]), prompt_sha)
    if autora is None:
        raise SystemExit("FRENO: falta la lectura de la autora")
    return {"code_ver": CODE_VER, "decide": "la validación sobre las 100 del acta (enmienda 5, punto 9)",
            **evaluar(juez, autora, da, at2)}


def main(argv=None, consola=print) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corridas", type=Path, default=CV.CORRIDAS)
    ap.add_argument("--tt3", type=Path, default=CVAL.TT3)
    ap.add_argument("--acta-sha256", default=CVAL.ACTA_SHA256)
    ap.add_argument("--sello-lectura-v3", type=Path, default=CVAL.SELLO_LECTURA_V3)
    ap.add_argument("--sello-lectura-v3-sha256", default=CVAL.SELLO_LECTURA_V3_SHA256)
    ap.add_argument("--registro", type=Path, default=CG.CONGELACION / CG.REGISTRO)
    ap.add_argument("--salida", type=Path)
    a = ap.parse_args(argv)
    d = Path(a.corridas) / CVAL.MODO
    salida = a.salida or d
    ruta = Path(salida) / SALIDA_NOMBRE
    if ruta.exists():
        raise SystemExit(f"FRENO: {ruta.name} ya existe: no se pisa")
    at2 = cargar_at2()
    reg = json.loads(Path(a.registro).read_text(encoding="utf-8"))
    acta = CVAL.leer_acta(a.tt3, a.acta_sha256)
    decl_p = Path(a.corridas) / f"declaracion_{CVAL.MODO}_no_completado.json"
    ag_p, res_p = d / "NO_ABRIR_agregado.json", d / "resumen.json"
    leidos = {"registro": Path(a.registro), "acta": Path(a.tt3) / CVAL.ACTA_REL}
    if decl_p.exists():
        leidos["declaracion"] = decl_p
        out = analizar(agregado=None, no_completada=json.loads(decl_p.read_text(encoding="utf-8")), autora=None,
                       acta=acta["acta"], prompt_sha=reg["prompt"]["sha256"], at2=at2)
        shas_hojas = None
    else:
        res = json.loads(res_p.read_text(encoding="utf-8")) if res_p.exists() else {}
        if not (res.get("corrida") or {}).get("completada") or res.get("agregado") != ag_p.name:
            raise SystemExit("FRENO: la validación no se completó o su resumen no nombra su agregado")
        sl = CVAL.controlar_sello_lectura(a.sello_lectura_v3, a.sello_lectura_v3_sha256, a.tt3)   # antes de leer una hoja
        leidos |= {"agregado": ag_p, "resumen": res_p, "sello_lectura": Path(a.sello_lectura_v3)}
        da = del_acta(acta["acta"])
        lect, shas_hojas = CV.leer_hojas_T(Path(a.tt3) / "lectura", da["predicado"], sha256_acta=acta["sha256"],
                                           campo_acta=CAMPO_ACTA, lotes=LOTES)
        out = analizar(agregado=json.loads(ag_p.read_text(encoding="utf-8")), no_completada=None,
                       autora={r: {"correcta": v["correcta"], "importancia": v["importancia"]} for r, v in lect.items()},
                       acta=acta["acta"], prompt_sha=reg["prompt"]["sha256"], at2=at2)
        out["sello_de_la_lectura"] = sl
    out["entradas_sha256"] = {**{n: sha(p.read_bytes()) for n, p in leidos.items()}, "hojas": shas_hojas}
    out["codigo_sha256"] = {"analisis_validacion_v3.py": sha(Path(__file__).read_bytes()), "analisis_T_v2.py": AT2_SHA256,
                            "analisis_gold_juez_v.py (v1)": sha(Path(AG.__file__).read_bytes())}
    Path(salida).mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    consola(f"validación de la v3: {'PASA' if out['pasa'] else 'NO PASA'}"
            + ("" if out["pasa"] else f" | falla: {'; '.join(out['fallan'])}") + f" | {ruta.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
