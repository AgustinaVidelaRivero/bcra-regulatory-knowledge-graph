"""Evidencia de la aceptación de S0-5a-bis (U-SEG-OFICIAL; USD 0, solo lectura de las salidas).

Uso: python -B aceptacion_S0-5a-bis.py --s04b <E0 de S0-4b> --s05a <E0 de S0-5a> --bis <E0 de S0-5a-bis>
       --lista-v2 <lista_R5a_por_lista_v2_decision4_mesa.json> --lista-88 <lista_88_rechazos_columna_profunda_mesa.json>
       --solo-r5g <E0 con R5-g sola> --out <json>

Por punto del «seguí» de S0-5a-bis, con lo que lo respalda:
1. R5-a por lista (la lista v2):
   - las 40 listas enteras sin rango: el último ítem y el cierre del padre, con el texto de S0-5a;
   - ri_rml 1.4.2: el cierre de 1.4 desde «Para el punto 1.4.1.» hasta «…671000/M-TP.», y el ítem con su rótulo y sus
     dos fórmulas;
   - los dos mixtos: el cierre, renglón por renglón, igual a `renglones_del_cierre`, y el resto del ítem igual al de
     S0-4b sin esos renglones, en el mismo orden;
   - las 14 que no se tocan: el último ítem y el cierre del padre con el texto de S0-4b (y, si la unidad entera cambia,
     los campos que cambian);
   - ningún evento de R5-a fuera de las 43.
2. Las tablas: el conjunto de las serializadas y el texto de cada bloque «[TABLA …] … [FIN TABLA …]», iguales a los de
   S0-4b; y los eventos `r5a_no_mueve_tabla`.
3. R5-f: los 11 rótulos de ri_ccna y 3.3.6.2 de snp_cheq abren su unidad; las unidades que los tenían.
4. R5-g (agregado del 09/10/2026): «3. Aclaraciones» sale del texto propio de ri_oc::S2 y las 51 unidades de 3.1 a 3.51
   heredan «3. Aclaraciones»; los otros 87 rechazos por columna profunda de la lista de la mesa siguen, con el mismo
   motivo; con R5-g sola, las claves que cambian son exactamente ri_oc::S2 y las 51 (S3 no es una clave propia).
(R5-a′ a R5-e «como en S0-5a» y los 9 casos y los 27 correctos: `s0_5/scripts/aceptacion_S0-5a.py` sobre S0-4b y la
salida de S0-5a-bis, y la diferencia contra S0-5a unidad por unidad, `contra_S0-5a_S0-5a-bis.py`.)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RE_BLOQUE = re.compile(r"\[TABLA (\S+) \|.*?\[FIN TABLA \1\]", re.S)
RANGOS = {"ri_rml::1.4.2": "ri_rml::1.4::cierre"}


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("s04b", "s05a", "bis", "lista_v2", "lista_88", "solo_r5g", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    v2 = jl(a.lista_v2)
    cache: dict = {}

    def ch(d: Path, to: str) -> dict:
        if (d, to) not in cache:
            cache[(d, to)] = {c["id"]: c for c in jl(d / f"chunks_{to}.json")}
        return cache[(d, to)]

    def txt(d: Path, uid: str):
        c = ch(d, uid.split("::")[0])
        if uid in c:
            return c[uid]["texto"]
        ps = sorted((i for i in c if i.startswith(uid + "::parte")), key=lambda i: int(i.rsplit("parte", 1)[1]))
        return "\n".join(c[i]["texto"] for i in ps) if ps else None

    res: dict = {}
    # 1. R5-a por lista
    enteras = [x for x in v2["por_lista"] if "renglones_del_cierre" not in x and x["lista"] not in RANGOS]
    det = {}
    for x in enteras:
        it, ci = x["lista"], x["cierre"]
        det[it] = {"item_igual_a_S0-5a": txt(a.bis, it) == txt(a.s05a, it),
                   "cierre_igual_a_S0-5a": txt(a.bis, ci) == txt(a.s05a, ci) and txt(a.bis, ci) is not None}
    res["R5-a_enteras"] = {"listas": len(enteras), "iguales_a_S0-5a": sum(all(v.values()) for v in det.values()),
                           "distintas": {k: v for k, v in det.items() if not all(v.values())}}
    cie = (txt(a.bis, "ri_rml::1.4::cierre") or "").split("\n")
    item_rml = (txt(a.bis, "ri_rml::1.4.2") or "").split("\n")
    ant = (txt(a.s04b, "ri_rml::1.4.2") or "").split("\n")
    res["ri_rml_1.4.2"] = {"cierre_empieza": cie[0], "cierre_termina": cie[-1], "renglones_del_cierre": len(cie),
                           "item": item_rml,
                           "ok": cie[0].startswith("Para el punto 1.4.1.") and cie[-1].endswith("671000/M-TP.")
                           and item_rml + cie == ant}
    mix = {}
    for x in (x for x in v2["por_lista"] if "renglones_del_cierre" in x):
        it, ci = x["lista"], x["cierre"]
        ren = [r["texto"] for r in x["renglones_del_cierre"]]
        ls0 = (txt(a.s04b, it) or "").split("\n")
        i = next((k for k in range(len(ls0)) if ls0[k:k + len(ren)] == ren), None)
        resto = ls0[:i] + ls0[i + len(ren):] if i is not None else None
        c_bis = (txt(a.bis, ci) or "").split("\n")
        mix[it] = {"cierre": ci, "renglones_v2": len(ren), "cierre_igual_renglon_por_renglon": c_bis == ren,
                   "posicion_en_S0-4b": i, "resto_del_item_igual_a_S0-4b": (txt(a.bis, it) or "").split("\n") == resto,
                   "ids_del_item": sorted(k for k in ch(a.bis, it.split("::")[0]) if k == it or k.startswith(it + "::parte")),
                   "limites_que_quedan": x["limites_que_quedan"]}
    res["mixtos"] = mix
    nst = {}
    for x in v2["no_se_tocan"]:
        it, ci = x["lista"], x["cierre"]
        to = it.split("::")[0]
        u0, u1 = ch(a.s04b, to).get(it), ch(a.bis, to).get(it)
        nst[it] = {"item_texto_igual_a_S0-4b": txt(a.bis, it) == txt(a.s04b, it),
                   "cierre_igual_a_S0-4b": txt(a.bis, ci) == txt(a.s04b, ci),
                   "cierre_existe": txt(a.bis, ci) is not None,
                   "campos_que_cambian": sorted(k for k in set(u0 or {}) | set(u1 or {})
                                                if (u0 or {}).get(k) != (u1 or {}).get(k)) if u0 and u1 else "partido"}
    res["no_se_tocan"] = {"listas": len(nst), "iguales_a_S0-4b": sum(v["item_texto_igual_a_S0-4b"]
                                                                     and v["cierre_igual_a_S0-4b"] for v in nst.values()),
                          "detalle": nst}
    claves = {f"{x['lista']}" for x in v2["por_lista"]}
    fuera, sin_tabla, sin_rango = [], [], []
    for p in sorted(a.bis.glob("estructura_*.json")):
        e = jl(p)
        for x in e["avisos"]:
            k = f"{e['to']}::{(x.get('prefijo') + '::') if x.get('prefijo') else ''}{x.get('item')}"
            if x["tipo"] == "cierre_al_margen_r5a" and k not in claves:
                fuera.append(k)
            if x["tipo"] == "r5a_no_mueve_tabla":
                sin_tabla.append({**x, "to": e["to"]})
            if x["tipo"] == "r5a_por_lista_sin_rango":
                sin_rango.append({**x, "to": e["to"]})
    res["R5-a_eventos"] = {"fuera_de_las_43": sorted(set(fuera)), "no_mueve_tabla": sin_tabla,
                           "por_lista_sin_rango": sin_rango}
    # 2. tablas
    def bloques(d: Path) -> dict:
        out = {}
        for p in sorted(d.glob("chunks_*.json")):
            for c in jl(p):
                for m in RE_BLOQUE.finditer(c["texto"]):
                    out[m.group(1)] = (c["id"], m.group(0))
        return out
    b0, b1 = bloques(a.s04b), bloques(a.bis)
    res["tablas"] = {"serializadas_S0-4b": len(b0), "serializadas_S0-5a-bis": len(b1),
                     "mismo_conjunto": set(b0) == set(b1),
                     "mismo_texto": sum(1 for k in b0 if k in b1 and b1[k][1] == b0[k][1]),
                     "en_otra_unidad": {k: [b0[k][0], b1[k][0]] for k in b0 if k in b1 and b1[k][0] != b0[k][0]},
                     "texto_distinto": sorted(k for k in b0 if k in b1 and b1[k][1] != b0[k][1]),
                     "faltan": sorted(set(b0) - set(b1)), "sobran": sorted(set(b1) - set(b0))}
    # 3. R5-f
    cc, cq = ch(a.bis, "ri_ccna"), ch(a.bis, "snp_cheq")
    esperados = [f"ri_ccna::D1A1::2.1.{k}" for k in range(1, 9)] + ["ri_ccna::D1A1::5.1", "ri_ccna::D1A1::8.1",
                                                                     "ri_ccna::D1A2::5.1"]
    eventos_f = []
    for to in ("ri_ccna", "snp_cheq"):
        eventos_f += [x for x in jl(a.bis / f"estructura_{to}.json")["avisos"] if x["tipo"].startswith("rotulo_por_lista")]
    u = cq.get("snp_cheq::3.3.6.2")
    res["R5-f"] = {"ri_ccna_abren": {k: (k in cc) for k in esperados},
                   "ri_ccna_inicio": {k: cc[k]["texto"][:60] for k in esperados if k in cc},
                   "snp_cheq_3.3.6.2": {"existe": u is not None, "inicio": u["texto"][:60] if u else None,
                                        "herencia": [[t["tipo"], t["unidad_origen"]] for t in u["herencia"]] if u else None},
                   "eventos": len(eventos_f), "sin_padre": [x for x in eventos_f if x["tipo"].endswith("sin_padre")]}
    # 4. R5-g
    oc0, oc1 = ch(a.s04b, "ri_oc"), ch(a.bis, "ri_oc")
    tres = sorted(i for i in oc1 if i.startswith("ri_oc::3."))
    l88 = jl(a.lista_88)["filas"]
    quedan = []
    for f in l88:
        e = jl(a.bis / f"estructura_{f['to']}.json")
        quedan.append(any(r["pagina"] == f["pagina"] and r["texto"] == f["texto"] and r["motivo"] == f["motivo"]
                          for r in e["rechazos_header"]))
    otros = [f for f, q in zip(l88, quedan) if f["to"] != "ri_oc"]
    g = jl(a.solo_r5g / "chunks_ri_oc.json")
    g = {c["id"]: c for c in g}
    cambian_g = sorted(i for i in set(g) | set(oc0) if g.get(i) != oc0.get(i))
    esperadas = sorted(["ri_oc::S2"] + [f"ri_oc::3.{k}" for k in range(1, 52)])
    otros_tos_g = [p.name for p in sorted(a.solo_r5g.glob("chunks_*.json"))
                   if p.name != "chunks_ri_oc.json" and p.read_bytes() != (a.s04b / p.name).read_bytes()]
    res["R5-g"] = {
        "S2_termina_antes": oc0["ri_oc::S2"]["texto"][-40:], "S2_termina_despues": oc1["ri_oc::S2"]["texto"][-40:],
        "unidades_3": len(tres),
        "heredan_3_Aclaraciones": sum([t["texto"] for t in oc1[i]["herencia"] if t["unidad_origen"] == "S3"]
                                      == ["3. Aclaraciones"] for i in tres),
        "S3_es_clave_propia": "ri_oc::S3" in oc1,
        "rechazo_de_ri_oc_sigue": [q for f, q in zip(l88, quedan) if f["to"] == "ri_oc"],
        "otros_87_siguen": f"{sum(quedan[i] for i, f in enumerate(l88) if f['to'] != 'ri_oc')} de {len(otros)}",
        "con_R5-g_sola_cambian": len(cambian_g), "son_exactamente_S2_y_las_51": cambian_g == esperadas,
        "con_R5-g_sola_otros_TOs_distintos": otros_tos_g}
    rg = res["R5-g"]
    rg["ok"] = (not rg["S2_termina_despues"].endswith("3. Aclaraciones") and rg["S2_termina_antes"].endswith("3. Aclaraciones")
                and rg["unidades_3"] == 51 and rg["heredan_3_Aclaraciones"] == 51 and rg["rechazo_de_ri_oc_sigue"] == [False]
                and rg["otros_87_siguen"] == f"{len(otros)} de {len(otros)}" and len(otros) == 87
                and rg["son_exactamente_S2_y_las_51"] and not otros_tos_g)
    res["resumen"] = {
        "R5-a enteras iguales a S0-5a": f"{res['R5-a_enteras']['iguales_a_S0-5a']} de {len(enteras)}",
        "ri_rml 1.4.2": res["ri_rml_1.4.2"]["ok"],
        "mixtos": {k: v["cierre_igual_renglon_por_renglon"] and v["resto_del_item_igual_a_S0-4b"] for k, v in mix.items()},
        "no se tocan, iguales a S0-4b": f"{res['no_se_tocan']['iguales_a_S0-4b']} de {len(nst)}",
        "R5-a fuera de las 43": len(res["R5-a_eventos"]["fuera_de_las_43"]),
        "tablas": f"{res['tablas']['mismo_texto']} de {len(b0)} con el mismo texto; mismo conjunto "
                  f"{res['tablas']['mismo_conjunto']}",
        "R5-f": f"{sum(res['R5-f']['ri_ccna_abren'].values())} de 11 en ri_ccna; snp_cheq 3.3.6.2 "
                f"{res['R5-f']['snp_cheq_3.3.6.2']['existe']}",
        "R5-g": rg["ok"]}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res["resumen"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
