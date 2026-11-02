"""Control de continuidad de la numeración de E0 (U-SEG-OFICIAL, S0-5a; USD 0, sin API, solo lectura de la salida).

Uso: python -B control_continuidad_numeracion.py --e0 <salida de E0> --lineas <caché de renglones de lineas_152.py>
       --out <json> [--tos a,b,c]

Es un control, no una regla: no cambia ninguna unidad. Definición (nota del 09/10/2026 al pie del mandato de S0-5a):
- Salto: un punto cuyo hermano anterior o cuyo padre no existe como unidad. «Existe» se lee en el árbol de puntos de
  E0 (`estructura_<to>.json`), por sub-documento: el punto es una unidad o el encabezado que heredan sus unidades.
  - Hueco: faltan los hermanos desde el último que existe (o desde 1) hasta el anterior al punto; o falta el padre
    (si el padre es un punto: el de una sección siempre existe).
  - Cola: el sucesor del último hijo de un punto, y los que siguen mientras aparezcan, si aparece al principio de un
    renglón del texto propio de alguna unidad (sin esa aparición la lista termina ahí y no hay salto).
- Rótulo: un número de punto de dos o más componentes («1.2.4.», «B.1.28.»; el primer componente puede ser una letra)
  al principio de un renglón, seguido de espacio, de fin de renglón o pegado al título («2.8.Código 11»).
- Clase de cada rótulo que falta:
  - (ii) punto tragado: aparece al principio de un renglón del texto propio de otra unidad (no la del mismo número). Se
    dan la unidad, el renglón y el final del renglón anterior, con `posible_referencia` si ese renglón termina en
    «punto» o «puntos», o si el resto del renglón está vacío o empieza en minúscula;
  - (iii) otra: aparece al principio de un renglón de una página de cuerpo del sub-documento, pero no en el texto propio
    de ninguna unidad;
  - (i) el PDF salta: no aparece al principio de ningún renglón de las páginas de cuerpo del sub-documento; se marca si
    aparece solo en una página que no es de cuerpo (índice, portada).
  - En las tres, los descendientes del rótulo que aparecen al principio de un renglón de alguna unidad y no son puntos
    de E0. Un (i) con descendientes tragados se trata como (ii) en la lista para la autora.
- El sub-documento de un renglón del PDF es el del último sub-documento que empieza en su página o antes (registro de
  sub-documentos de `estructura_<to>.json`); el de una unidad, su prefijo.
Salida: por TO, cada salto con su clase; los totales por clase, por TO y por modo de lectura; y la lista de los (ii) y
(iii) (y los (i) con descendientes tragados) para la decisión de la autora, con la tanda de su TO.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

RE_ROT = re.compile(r"^\s*((?:\d+|[A-Z])(?:\.\d+)+)(?:\.?(?=\s|$)|\.(?=[^\d\s]))(.*)$")
RE_REF = re.compile(r"\b(?:punto|puntos)\s*$", re.IGNORECASE)
TANDA1 = ("ayccef", "expaef", "opefci", "adrei", "ri_ccna", "ri_pgn", "ri_rml", "ri_gerc", "snp_cheq", "ceninf",
          "cirmo3", "snp_tr", "lingeef", "depaho", "cajasc", "manori", "efemin", "nmcief", "ri_dcpc", "ri_oc")
TANDA0 = ("ctacte", "lingob", "polcre", "pagjub", "docvig")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _orden(rot: str) -> list:
    return [(0, int(x)) if x.isdigit() else (1, x) for x in rot.split(".")]


def _padre(rot: str) -> str:
    return rot.rsplit(".", 1)[0]


def _ult(rot: str) -> int | None:
    x = rot.rsplit(".", 1)[1]
    return int(x) if x.isdigit() else None


def control_to(e0: Path, lineas: Path | None, to: str) -> dict:
    est = jl(e0 / f"estructura_{to}.json")
    chunks = jl(e0 / f"chunks_{to}.json")
    roles = [d["rol"] for d in jl(e0 / f"pies_{to}.json")["paginas_detalle"]] if (e0 / f"pies_{to}.json").exists() \
        else None
    registro = est.get("subdocumentos") or []
    prefijos = {s["prefijo"] for s in registro}
    inicios = sorted((s["pagina"], s["prefijo"]) for s in registro)

    def pref_de_pagina(pg: int):
        p = None
        for ini, pr in inicios:
            if pg >= ini:
                p = pr
        return p

    pts: set[tuple] = set()
    hijos: dict[tuple, list[str]] = collections.defaultdict(list)

    def rec(n: dict, pr, padre_num) -> None:
        if n.get("tipo") == "punto":
            pts.add((pr, n["numero"]))
            if padre_num is not None and "." in n["numero"]:
                hijos[(pr, padre_num)].append(n["numero"])
        for h in n.get("hijos", []) or []:
            rec(h, pr, n["numero"] if n.get("tipo") == "punto" else None)

    for s in est["secciones"]:
        rec(s, s.get("prefijo"), None)
    # apariciones al principio de un renglón del texto propio de una unidad
    apar: dict[tuple, list[dict]] = collections.defaultdict(list)
    for c in chunks:
        partes = c["id"].split("::")
        pr = partes[1] if len(partes) > 2 and partes[1] in prefijos else None
        etiqueta = partes[2] if pr else partes[1]
        ls = c["texto"].split("\n")
        for i, l in enumerate(ls):
            m = RE_ROT.match(l)
            if not m:
                continue
            ant = ls[i - 1].strip() if i else ""
            resto = m.group(2).strip()
            apar[(pr, m.group(1))].append({
                "unidad": c["id"], "etiqueta_unidad": etiqueta, "renglon": l.strip()[:110],
                "final_renglon_anterior": ant[-50:],
                "posible_referencia": bool(RE_REF.search(ant)) or not resto or resto[:1].islower()})
    # renglones del PDF: de cuerpo y de otras páginas
    en_cuerpo, fuera = set(), set()
    if lineas is not None and (lineas / f"{to}.json").exists():
        for pag in jl(lineas / f"{to}.json"):
            for x in pag:
                m = RE_ROT.match(x[3])
                if not m:
                    continue
                cuerpo = roles is None or (x[0] - 1 < len(roles) and roles[x[0] - 1] == "cuerpo")
                (en_cuerpo if cuerpo else fuera).add((pref_de_pagina(x[0]), m.group(1)))
    faltan: dict[tuple, dict] = {}
    for (pr, p) in sorted(pts, key=lambda t: (str(t[0]), _orden(t[1]))):
        pa = _padre(p)
        if "." in pa and (pr, pa) not in pts:
            faltan.setdefault((pr, pa), {"forma": "padre", "referencia": p})
        k = _ult(p)
        if k is None:
            continue
        hs = [_ult(h) for h in hijos.get((pr, pa), []) if _ult(h) is not None] if "." in pa else \
            [_ult(q) for (pr2, q) in pts if pr2 == pr and q.count(".") == 1 and _padre(q) == pa and _ult(q) is not None]
        previo = max([h for h in hs if h < k], default=0)
        for j in range(previo + 1, k):
            faltan.setdefault((pr, f"{pa}.{j}"), {"forma": "hueco", "referencia": p})
    # cola: hijos de un punto, y raíces de una sección (puntos de un componente después del de la sección)
    grupos: dict[tuple, list[int]] = collections.defaultdict(list)
    for (pr, pa), hs in hijos.items():
        grupos[(pr, pa)] = [_ult(h) for h in hs if _ult(h) is not None]
    for (pr, q) in pts:
        if q.count(".") == 1 and _ult(q) is not None:
            grupos[(pr, _padre(q))].append(_ult(q))
    for (pr, pa), nums in grupos.items():
        if not nums:
            continue
        k = max(nums) + 1
        while (pr, f"{pa}.{k}") not in pts and any(a["etiqueta_unidad"] != f"{pa}.{k}" for a in apar.get((pr, f"{pa}.{k}"), [])):
            faltan.setdefault((pr, f"{pa}.{k}"), {"forma": "cola", "referencia": f"{pa}.{max(nums)}"})
            k += 1
    filas = []
    for (pr, rot), info in sorted(faltan.items(), key=lambda t: (str(t[0][0]), _orden(t[0][1]))):
        otras = [a for a in apar.get((pr, rot), []) if a["etiqueta_unidad"] != rot]
        desc = sorted({(r, a["unidad"]) for (pr2, r), aps in apar.items()
                       if pr2 == pr and r.startswith(rot + ".") and (pr, r) not in pts for a in aps},
                      key=lambda t: _orden(t[0]))
        fila = {"to": to, "subdocumento": pr, "rotulo": rot, **info,
                "descendientes_tragados": [{"rotulo": r, "unidad": u} for r, u in desc]}
        if otras:
            a = otras[0]
            fila.update(clase="ii", unidad=a["unidad"], renglon=a["renglon"],
                        final_renglon_anterior=a["final_renglon_anterior"],
                        posible_referencia=a["posible_referencia"], apariciones=len(otras))
        elif (pr, rot) in en_cuerpo:
            fila.update(clase="iii")
        else:
            fila.update(clase="i", aparece_solo_fuera_del_cuerpo=(pr, rot) in fuera)
        filas.append(fila)
    return {"modo_lectura": est.get("modo_lectura", "vigente"), "saltos": filas}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--lineas", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tos", default=None)
    a = ap.parse_args()
    tos = sorted(p.name[len("estructura_"):-5] for p in a.e0.glob("estructura_*.json"))
    if a.tos:
        tos = [t for t in tos if t in a.tos.split(",")]
    por_to, filas = {}, []
    for to in tos:
        r = control_to(a.e0, a.lineas, to)
        if r["saltos"]:
            por_to[to] = r
        filas += r["saltos"]
    def tanda(to):
        return 1 if to in TANDA1 else 0 if to in TANDA0 else None
    para_autora = [f for f in filas if f["clase"] in ("ii", "iii") or (f["clase"] == "i" and f["descendientes_tragados"])]
    res = {"tos_revisados": len(tos), "saltos": len(filas),
           "por_clase": dict(collections.Counter(f["clase"] for f in filas)),
           "ii_posible_referencia": sum(1 for f in filas if f.get("posible_referencia")),
           "tos_con_saltos": len(por_to),
           "por_to": {to: dict(collections.Counter(f["clase"] for f in r["saltos"])) for to, r in por_to.items()},
           "por_modo": dict(collections.Counter(por_to[f["to"]]["modo_lectura"] for f in filas)),
           "tanda1": {"saltos": sum(1 for f in filas if f["to"] in TANDA1),
                      "tos": len({f["to"] for f in filas if f["to"] in TANDA1}),
                      "por_clase": dict(collections.Counter(f["clase"] for f in filas if f["to"] in TANDA1))},
           "para_la_autora": [{**f, "tanda": tanda(f["to"])} for f in para_autora],
           "filas": filas}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("filas", "para_la_autora", "por_to")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
