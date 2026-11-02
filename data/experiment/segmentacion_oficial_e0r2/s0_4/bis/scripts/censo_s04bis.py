"""Censo de una corrida de E0 contra la base, por TO (U-SEG-OFICIAL, S0-4 y S0-4a-bis; USD 0, sin API). Es el de S0-3
(`s0_3/scripts/censo_s03.py`) con los avisos de S0-4, contados como diferencia con los de la base.

Cuenta, por TO: (1) páginas que cambian de rol (`pies_<to>.json`, `paginas_detalle`); (2) renglones que cambian de
rol entre encabezado o pie y texto (`estructura_<to>.json`, `accounting.detalle_descartes`, como multiconjunto de
(página, texto), sin las páginas que cambian de rol); (3) rótulos que aparecen o desaparecen (nodos de la estructura, como (página, número, título));
(4) unidades: ids nuevos, ids que desaparecen y chunks que cambian (mismo criterio que `comparar_e0.py`); (5) avisos
de S0-3 y S0-4 (`cuerpo_al_rotulo_m1`, `raiz_m2`, `subdocumento_sd`, `raiz_g3_subdocumento_sd`, `apartado_de_seccion_ap`
y, desde S0-4a-bis, `raiz_mayor_a_max_subdocumento_sdmax`).

Uso: python -B censo_s04.py <dir base> <dir nueva> <salida.json> [--tos a,b]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparar_e0 as CMP  # noqa: E402

AVISOS_S03 = ("cuerpo_al_rotulo_m1", "raiz_m2", "subdocumento_sd", "raiz_g3_subdocumento_sd", "apartado_de_seccion_ap",
              "raiz_mayor_a_max_subdocumento_sdmax")


def _json(d: Path, nombre: str):
    p = d / nombre
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _rotulos(e: dict) -> Counter:
    out: Counter = Counter()

    def rec(n: dict) -> None:
        out[(n["pagina"], n["numero"], n["titulo"])] += 1
        for h in n["hijos"]:
            rec(h)
    for s in e["secciones"]:
        rec(s)
    return out


def censo_to(base: Path, nueva: Path, to: str) -> OrderedDict:
    eb, en = _json(base, f"estructura_{to}.json"), _json(nueva, f"estructura_{to}.json")
    pb, pn = _json(base, f"pies_{to}.json"), _json(nueva, f"pies_{to}.json")
    roles_b = {f["pagina"]: f["rol"] for f in pb["paginas_detalle"]} if pb else {}
    roles_n = {f["pagina"]: f["rol"] for f in pn["paginas_detalle"]} if pn else {}
    paginas = [{"pagina": p, "de": roles_b.get(p), "a": roles_n.get(p)}
               for p in sorted(set(roles_b) | set(roles_n)) if roles_b.get(p) != roles_n.get(p)]
    pag_rol = {f["pagina"] for f in paginas}
    # las líneas de una página que cambia de rol se cuentan con la página, no como encabezado o texto
    db = Counter((d["pagina"], d["texto"]) for d in eb["accounting"]["detalle_descartes"] if d["pagina"] not in pag_rol)
    dn = Counter((d["pagina"], d["texto"]) for d in en["accounting"]["detalle_descartes"] if d["pagina"] not in pag_rol)
    for f in paginas:
        f["renglones_descartados_antes"] = sum(1 for d in eb["accounting"]["detalle_descartes"]
                                              if d["pagina"] == f["pagina"])
    a_texto = sorted((db - dn).elements())
    a_encabezado = sorted((dn - db).elements())
    rb, rn = _rotulos(eb), _rotulos(en)
    rot_nuevos = sorted((rn - rb).elements(), key=lambda x: (x[0], x[1]))
    rot_idos = sorted((rb - rn).elements(), key=lambda x: (x[0], x[1]))
    cmp = CMP.comparar_to(CMP.leer_chunks(base, to), CMP.leer_chunks(nueva, to))
    # avisos de S0-3 y S0-4 que la corrida nueva tiene y la base no (diferencia de multiconjuntos: contra una base que
    # ya lleva las reglas de S0-3, sus avisos están en los dos lados y no cuentan)
    av, avb = Counter(), Counter()
    for a in en.get("avisos", []):
        if a.get("tipo") in AVISOS_S03:
            av[f"{a['tipo']}:{a.get('forma')}"] += 1
    for a in eb.get("avisos", []):
        if a.get("tipo") in AVISOS_S03:
            avb[f"{a['tipo']}:{a.get('forma')}"] += 1
    av = av - avb
    return OrderedDict([
        ("paginas_que_cambian_de_rol", paginas),
        ("renglones_de_encabezado_a_texto", [list(x) for x in a_texto]),
        ("renglones_de_texto_a_encabezado", [list(x) for x in a_encabezado]),
        ("rotulos_nuevos", [list(x) for x in rot_nuevos]),
        ("rotulos_que_desaparecen", [list(x) for x in rot_idos]),
        ("unidades", [len(CMP.leer_chunks(base, to)), len(CMP.leer_chunks(nueva, to))]),
        ("ids_nuevos", cmp["ids_nuevos"]),
        ("ids_que_desaparecen", cmp["ids_que_desaparecen"]),
        ("orden_igual_en_comunes", cmp["orden_igual_en_comunes"]),
        ("chunks_que_cambian", list(cmp["cambian"])),
        ("avisos_s03", dict(sorted(av.items())))])


def main() -> None:
    base, nueva, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    tos = (sys.argv[sys.argv.index("--tos") + 1].split(",") if "--tos" in sys.argv
           else sorted(p.name[len("chunks_"):-len(".json")] for p in nueva.glob("chunks_*.json")))
    por_to = OrderedDict()
    for to in tos:
        c = censo_to(base, nueva, to)
        if any(c[k] for k in ("paginas_que_cambian_de_rol", "renglones_de_encabezado_a_texto",
                              "renglones_de_texto_a_encabezado", "rotulos_nuevos", "rotulos_que_desaparecen",
                              "ids_nuevos", "ids_que_desaparecen", "chunks_que_cambian", "avisos_s03")) \
                or not c["orden_igual_en_comunes"]:
            por_to[to] = c
    tot = OrderedDict([
        ("tos", len(tos)), ("tos_que_cambian", sorted(por_to)),
        ("paginas_que_cambian_de_rol", sum(len(c["paginas_que_cambian_de_rol"]) for c in por_to.values())),
        ("renglones_de_encabezado_a_texto", sum(len(c["renglones_de_encabezado_a_texto"]) for c in por_to.values())),
        ("renglones_de_texto_a_encabezado", sum(len(c["renglones_de_texto_a_encabezado"]) for c in por_to.values())),
        ("rotulos_nuevos", sum(len(c["rotulos_nuevos"]) for c in por_to.values())),
        ("rotulos_que_desaparecen", sum(len(c["rotulos_que_desaparecen"]) for c in por_to.values())),
        ("ids_nuevos", sum(len(c["ids_nuevos"]) for c in por_to.values())),
        ("ids_que_desaparecen", sum(len(c["ids_que_desaparecen"]) for c in por_to.values())),
        ("chunks_que_cambian", sum(len(c["chunks_que_cambian"]) for c in por_to.values())),
        ("unidades", [sum(len(CMP.leer_chunks(base, t)) for t in tos), sum(len(CMP.leer_chunks(nueva, t)) for t in tos)]),
        ("avisos_s03", dict(sorted(sum((Counter(c["avisos_s03"]) for c in por_to.values()), Counter()).items()))),
        ("por_to_resumen", OrderedDict((t, {"unidades": c["unidades"], "nuevos": len(c["ids_nuevos"]),
                                            "desaparecen": len(c["ids_que_desaparecen"]),
                                            "cambian": len(c["chunks_que_cambian"]),
                                            "renglones_rol": len(c["renglones_de_encabezado_a_texto"])
                                            + len(c["renglones_de_texto_a_encabezado"]),
                                            "rotulos": [len(c["rotulos_nuevos"]), len(c["rotulos_que_desaparecen"])],
                                            "paginas_rol": len(c["paginas_que_cambian_de_rol"]),
                                            "avisos_s03": c["avisos_s03"]})
                                       for t, c in por_to.items()))])
    sal.write_text(json.dumps(OrderedDict([("resumen", tot), ("por_to", por_to)]), ensure_ascii=False, indent=1)
                   + "\n", encoding="utf-8")
    r = dict(tot)
    r.pop("por_to_resumen")
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
