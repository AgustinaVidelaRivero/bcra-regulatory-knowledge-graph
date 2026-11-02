"""Censo de las reglas 4a (oración tomada como título) y 4b (título envuelto) de S0-4 (USD 0, solo lectura).

Clasifica, sobre la estructura de una corrida de E0 (`estructura_<to>.json`), los puntos con hijos cuyo título no
termina en punto y cuya intro empieza en minúscula (la condición común), con el mismo criterio que
`e0_lib.clase_titulo_4ab` (reescrito sobre el texto de la estructura, con la expresión de verbos del código), y los
cruza con lo que hicieron las corridas con la regla: en la de 4a, los encabezados heredados que son solo el número
del punto; en la de 4b, los encabezados con el renglón juntado. Los dos conjuntos tienen que coincidir. Da también la
forma de la intro del censo de S0-3 (`termina_en_dos_puntos`, `un_renglon_sin_dos_puntos`, `varios_renglones`) y la
clasificación en los diez TOs de la tanda 0, donde las reglas no corren (límite declarado).

Uso: python -B censo_4ab.py --codigo <raíz> --base <dir> --r4a <dir> --r4b <dir> --tanda0 <dir> --salida <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path


def candidatos(d: Path, tos: list[str], RE) -> list[dict]:
    out = []
    for to in tos:
        e = json.loads((d / f"estructura_{to}.json").read_text(encoding="utf-8"))

        def rec(n, raiz_pref):
            if n["tipo"] == "punto" and n["hijos"]:
                intro = [s for s in n["segmentos"] if s["rol"] == "intro"]
                t = (n["titulo"] or "").rstrip()
                if intro and t and not t.endswith("."):
                    lin = intro[0]["texto"].split("\n")
                    if lin[0].lstrip()[:1].islower():
                        r1 = lin[0].rstrip()
                        toda = len(intro) == 1 and len(lin) == 1
                        if (r1.endswith(".") or (toda and not r1.endswith(":"))) and not RE.search(r1):
                            clase = "4b"
                        else:
                            orac = [r1]
                            for x in lin[1:]:
                                if orac[-1].endswith((".", ":")):
                                    break
                                orac.append(x.rstrip())
                            clase = "4a" if (orac[-1].endswith(":") or RE.search(t + " " + " ".join(orac))) else "ninguna"
                        texto_intro = "\n".join(s["texto"] for s in intro)
                        forma = ("termina_en_dos_puntos" if texto_intro.rstrip().endswith(":") else
                                 "un_renglon_sin_dos_puntos" if len(texto_intro.split("\n")) == 1 else
                                 "varios_renglones")
                        unidad = (f"{raiz_pref}::" if raiz_pref else "") + n["numero"]
                        out.append({"to": to, "unidad": unidad, "clase": clase, "forma_intro_s03": forma,
                                    "titulo": t, "renglon_1": lin[0], "paginas": intro[0]["paginas"]})
            for h in n["hijos"]:
                rec(h, raiz_pref)
        for s in e["secciones"]:
            rec(s, s.get("prefijo"))
    return out


def observados(d: Path, tos: list[str], clase: str) -> set:
    vistos = set()
    for to in tos:
        p = d / f"chunks_{to}.json"
        if not p.exists():
            continue
        for c in json.loads(p.read_text(encoding="utf-8")):
            for t in c.get("herencia", []):
                if t["tipo"] != "encabezado":
                    continue
                u = t["unidad_origen"]
                num = u.split("::")[-1]
                if clase == "4a" and t["texto"] == f"{num}." and not num.startswith("S"):
                    vistos.add((to, u))
                if clase == "4b" and "\n" in t["texto"] and not num.startswith("S"):
                    vistos.add((to, u))
    return vistos


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("codigo", "base", "r4a", "r4b", "tanda0", "salida"):
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    raiz = Path(a.codigo).resolve()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(raiz / "data/experiment/reextraccion_v2/e0_chunking"))
    import correr_e0 as CE  # noqa: PLC0415
    RE = CE.E0.RE_VERBO_ORACION_4AB
    t0 = CE.TOS_TANDA0_SIN_4AB
    base = Path(a.base)
    tos = sorted(p.name[len("estructura_"):-5] for p in base.glob("estructura_*.json") if p.name[11:-5] not in t0)
    cand = candidatos(base, tos, RE)
    por_clase = {k: {(c["to"], c["unidad"]) for c in cand if c["clase"] == k} for k in ("4a", "4b", "ninguna")}
    obs4a, obs4b = observados(Path(a.r4a), tos, "4a"), observados(Path(a.r4b), tos, "4b")
    tos_t0 = sorted(p.name[len("estructura_"):-5] for p in Path(a.tanda0).glob("estructura_*.json"))
    cand_t0 = candidatos(Path(a.tanda0), tos_t0, RE)
    out = OrderedDict([
        ("criterio", __doc__.split("\n\n")[1].replace("\n", " ")),
        ("base", str(base.name)),
        ("candidatos", len(cand)),
        ("por_clase", dict(Counter(c["clase"] for c in cand))),
        ("tos_por_clase", {k: len({t for t, _ in v}) for k, v in por_clase.items()}),
        ("clase_por_forma_intro_s03", {f: dict(Counter(c["clase"] for c in cand if c["forma_intro_s03"] == f))
                                       for f in ("termina_en_dos_puntos", "un_renglon_sin_dos_puntos",
                                                 "varios_renglones")}),
        ("control_contra_las_corridas", {
            "4a_clasificados": len(por_clase["4a"]), "4a_observados": len(obs4a),
            "4a_iguales": por_clase["4a"] == obs4a,
            "4a_solo_clasificados": sorted(map(list, por_clase["4a"] - obs4a)),
            "4a_solo_observados": sorted(map(list, obs4a - por_clase["4a"])),
            "4b_clasificados": len(por_clase["4b"]), "4b_observados": len(obs4b),
            "4b_iguales": por_clase["4b"] == obs4b,
            "4b_solo_clasificados": sorted(map(list, por_clase["4b"] - obs4b)),
            "4b_solo_observados": sorted(map(list, obs4b - por_clase["4b"]))}),
        ("tanda0_limite_declarado", {"candidatos": len(cand_t0), "por_clase": dict(Counter(c["clase"] for c in cand_t0)),
                                     "por_to": {t: dict(Counter(c["clase"] for c in cand_t0 if c["to"] == t))
                                                for t in tos_t0 if any(c["to"] == t for c in cand_t0)},
                                     "casos": cand_t0}),
        ("casos", cand)])
    Path(a.salida).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    r = dict(out)
    for k in ("casos", "tanda0_limite_declarado"):
        r.pop(k)
    r["tanda0"] = {k: v for k, v in out["tanda0_limite_declarado"].items() if k != "casos"}
    print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
