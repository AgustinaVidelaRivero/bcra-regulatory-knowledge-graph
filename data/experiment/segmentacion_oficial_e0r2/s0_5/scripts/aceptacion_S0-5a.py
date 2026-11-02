"""Evidencia de las aceptaciones del §2 del mandato de S0-5a (U-SEG-OFICIAL; USD 0, solo lectura de las salidas).

Uso: python -B aceptacion_S0-5a.py --antes <E0 de S0-4b> --despues <E0 de S0-5a> --planilla-116 <planilla del 1.16 de
       S1-bis> --out <json>

Por regla, lo que pide el mandato, con el texto de antes y de después:
- R5-a: los 9 casos del mecanismo 1 (el final del ítem antes y después, y el principio del cierre del padre); los 27
  candidatos marcados correctos en S1-bis, con su sha256 propio antes y después;
- R5-a′: adónde va cada renglón de `ri_oc::C.11` y de `ri_oc::SC::cierre` (la unidad de después que lo tiene), y que
  ninguna herencia de C.1 a C.11 tenga tramos del bloque;
- R5-b: las uniones de snp_dd y snp_cheq (cada intersticial que desaparece, en qué unidad queda), contra la lista del
  censo de la mesa;
- R5-c: los 9 títulos de dos renglones (sin chapeau y con el título entero en la herencia de un hijo) y los 4 chapeaux
  de verdad (iguales antes y después);
- R5-d: ri_rml y snp_tr como los pide el mandato, con la corrección de la nota del control, y los 4 encabezados de
  verdad: en la salida final, la unidad sigue con el mismo texto propio y el mismo título (la herencia puede cambiar por
  otra regla: se listan los tramos nuevos, con la unidad de la que vienen); con `--solo-r5d` (R5-d sola), además, la
  unidad entera igual a la de antes;
- R5-e: el final de `ri_ccna::D1F3::S0` y las letras de `ri_ccna::D1F4::S0`.
Cada aceptación lleva `ok` y lo que la respalda.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CASOS_R5A = {"adfsp::1.1.10": "adfsp::1.1::cierre", "cajasc::11.4.4": "cajasc::11.4::cierre",
             "cajasc::4.2.2.3": "cajasc::4.2.2::cierre", "depaho::3.11.5.5": "depaho::3.11.5::cierre",
             "manori::1.4.1.3": "manori::1.4.1::cierre", "manori::3.4.1.3": "manori::3.4.1::cierre",
             "ri_oc::B.1.28": "ri_oc::B.1::cierre", "ri_oc::B.2.4": "ri_oc::B.2::cierre",
             "ri_oc::B.3.4": "ri_oc::B.3::cierre"}
TITULOS_R5C = ("manual::S2", "ri2_ae::S2", "ri_ccna::D1A1::S2", "ri_ccna::D1A3L2::S26", "ri_ccna::D1A3L2::S29",
               "ri_ccna::D1F2::S3", "ri_ccna::D1F6::S3", "ri_spi::SB", "ri_spi::SC")
CHAPEAUX_R5C = ("inspag::S3", "pfmipyme::S3", "ri_cr::S3", "snp_psp::S3")
# uniones del censo de la mesa (S0-5_evidencia_r5b_pares_salida.txt, y el mandato, §2: (i′) 7+8)
MESA_R5B = {"snp_dd": [(7, 8), (8, 9), (13, 14), (17, 18), (19, 20), (23, 24), (29, 30), (31, 32), (33, 34), (35, 36),
                       (37, 38), (39, 40), (41, 42), (43, 44), (48, 49), (52, 53), (54, 55)],
            "snp_cheq": [(11, 12), (13, 14), (16, 17), (18, 19)]}
ENCABEZADOS_R5D = ("gerc::2.4.2", "rdbcra::11.12.1", "ordcom::1.6.2", "pimf::4.18::intro")


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("antes", "despues", "planilla_116", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    ap.add_argument("--solo-r5d", dest="solo_r5d", type=Path, default=None)
    a = ap.parse_args()
    cache: dict = {}

    def ch(d: Path, to: str) -> dict:
        if (d, to) not in cache:
            cache[(d, to)] = {c["id"]: c for c in jl(d / f"chunks_{to}.json")}
        return cache[(d, to)]

    def u(d: Path, uid: str) -> dict | None:
        return ch(d, uid.split("::")[0]).get(uid)

    res: dict = {}
    # R5-a
    casos = {}
    for item, cid in CASOS_R5A.items():
        an, de, ci = u(a.antes, item), u(a.despues, item), u(a.despues, cid)
        casos[item] = {"item_antes_termina": an["texto"][-160:], "item_despues_termina": de["texto"][-160:],
                       "cierre": cid, "cierre_despues_empieza": ci["texto"][:200] if ci else None,
                       "ok": bool(ci) and ci["texto"].split("\n")[0] not in de["texto"]
                       and ci["texto"].split("\n")[0] in an["texto"]}
    correctos = [r["id"] for r in csv.DictReader(open(a.planilla_116, encoding="utf-8"), delimiter="\t")
                 if r["marca"] == "correcta"]
    neg = {i: {"sha_antes": u(a.antes, i)["sha256_propio"], "sha_despues": (u(a.despues, i) or {}).get("sha256_propio")}
           for i in correctos}
    res["R5-a"] = {"casos": casos, "casos_ok": sum(v["ok"] for v in casos.values()),
                   "correctos_116": len(neg), "correctos_116_iguales": sum(v["sha_antes"] == v["sha_despues"]
                                                                          for v in neg.values()),
                   "correctos_116_detalle": neg}
    # R5-a′
    oc_d = ch(a.despues, "ri_oc")
    renglones = u(a.antes, "ri_oc::C.11")["texto"].split("\n") + u(a.antes, "ri_oc::SC::cierre")["texto"].split("\n")
    destino = []
    for r in renglones:
        donde = [i for i, c in oc_d.items() if r in c["texto"].split("\n")]
        destino.append({"renglon": r[:90], "unidad_despues": donde})
    her = [k for k in range(1, 12) for t in oc_d[f"ri_oc::C.{k}"]["herencia"]
           if any(x in t["texto"] for x in ("Criterios de validación", "Se considerará no validada"))]
    res["R5-a′"] = {"destino_de_cada_renglon": destino,
                    "renglones": len(destino),
                    "por_unidad": {i: sum(1 for d in destino if d["unidad_despues"] == [i])
                                   for i in sorted({x for d in destino for x in d["unidad_despues"]})},
                    "sin_destino_unico": [d for d in destino if len(d["unidad_despues"]) != 1],
                    "C1_a_C11_con_tramos_del_bloque": her,
                    "SC_cierre_despues": "ri_oc::SC::cierre" in oc_d,
                    "ok": not her and "ri_oc::SC::cierre" not in oc_d
                    and all(d["unidad_despues"] for d in destino)}
    # R5-b
    uniones, ok_b = {}, True
    for to, base in (("snp_dd", "snp_dd::S7::intersticial::"), ("snp_cheq", "snp_cheq::7.1::intersticial::")):
        an, de = ch(a.antes, to), ch(a.despues, to)
        quitadas = sorted((int(i.rsplit("::", 1)[1]) for i in set(an) - set(de) if i.startswith(base)))
        pares = []
        for q in quitadas:
            k = q - 1
            while f"{base}{k}" not in de:
                k -= 1
            pares.append((k, q))
        mesa = set(MESA_R5B[to])
        mios = set()
        for k, q in pares:     # cada intersticial que se va, unida a la anterior de la cadena
            mios.add((q - 1, q))
        uniones[to] = {"quitadas": quitadas, "en_la_unidad": [f"{base}{k}" for k, _ in pares],
                       "pares_mios": sorted(mios), "pares_mesa": sorted(mesa),
                       "solo_mios": sorted(mios - mesa), "solo_mesa": sorted(mesa - mios),
                       "otras_unidades_distintas": sorted(i for i in set(an) & set(de) if an[i] != de[i]
                                                          and not i.startswith(base))}
        ok_b = ok_b and mios == mesa
    res["R5-b"] = {"uniones": uniones, "ok": ok_b}
    # R5-c
    tit = {}
    for s in TITULOS_R5C:
        cid = f"{s.split('::')[0]}::{s.split('::', 1)[1]}::chapeau_seccion"
        an = u(a.antes, cid)
        to, unidad = s.split("::")[0], s.split("::", 1)[1]
        enc = next((t["texto"] for c in ch(a.despues, to).values() for t in c["herencia"]
                    if t["tipo"] == "encabezado" and t["unidad_origen"] == unidad and an
                    and t["texto"].endswith("\n" + an["texto"].strip())), None)
        tit[s] = {"chapeau_antes": an["texto"] if an else None, "chapeau_despues": cid in ch(a.despues, to),
                  "titulo_en_la_herencia": enc, "ok": an is not None and cid not in ch(a.despues, to) and enc is not None}
    cha = {}
    for s in CHAPEAUX_R5C:
        cid = f"{s}::chapeau_seccion"
        an, de = u(a.antes, cid), u(a.despues, cid)
        cha[s] = {"chapeau": an["texto"] if an else None, "igual": bool(an) and an == de}
    res["R5-c"] = {"titulos": tit, "titulos_ok": sum(v["ok"] for v in tit.values()), "chapeaux_de_verdad": cha,
                   "chapeaux_iguales": sum(v["igual"] for v in cha.values())}
    # R5-d
    rml, tr = ch(a.despues, "ri_rml"), ch(a.despues, "snp_tr")
    lista_tr = ("1.3.4.1", "1.3.4.2", "1.3.5.1", "1.3.5.2", "1.3.5.3", "1.3.6.1", "1.3.6.2", "1.4.1", "1.4.2", "1.4.3",
                "1.4.4", "1.5.1", "1.5.2.1", "1.5.2.2")
    nodos_tr = {t["unidad_origen"] for c in tr.values() for t in c["herencia"]} | {i.split("::")[1] for i in tr}
    res["R5-d"] = {
        "ri_rml_1.2.3_termina": rml["ri_rml::1.2.3"]["texto"][-80:],
        "ri_rml_1.2.4": "ri_rml::1.2.4" in rml, "ri_rml_1.3_empieza": rml.get("ri_rml::1.3", {}).get("texto", "")[:60],
        "snp_tr_1.3.3_termina": tr["snp_tr::1.3.3"]["texto"][-90:],
        "snp_tr_existen": {k: f"snp_tr::{k}" in tr for k in lista_tr},
        "snp_tr_nodos_1.3.4_1.3.5_1.3.6_1.4_1.5_1.5.2": {k: k in nodos_tr for k in ("1.3.4", "1.3.5", "1.3.6", "1.4",
                                                                                       "1.5", "1.5.2")},
        "snp_tr_1.6_encabezado": next((t["texto"] for t in tr["snp_tr::1.6.1"]["herencia"]
                                       if t["unidad_origen"] == "1.6"), None),
        "snp_tr_1.6_intro_antes": "snp_tr::1.6::intro" in ch(a.antes, "snp_tr"),
        "snp_tr_1.6_intro_despues": "snp_tr::1.6::intro" in tr,
        "encabezados_de_verdad": {}}
    d = res["R5-d"]
    for i in ENCABEZADOS_R5D:
        an, de = u(a.antes, i), u(a.despues, i)
        tramos = lambda c: [(t["tipo"], t["unidad_origen"], t["texto"]) for t in c["herencia"]] if c else []
        e = {"existe": de is not None, "texto_igual": bool(an and de) and an["texto"] == de["texto"],
             "titulo_igual": bool(an and de) and an.get("titulo") == de.get("titulo"),
             "herencia_igual": tramos(an) == tramos(de),
             "tramos_nuevos_en_la_herencia": [list(t[:2]) + [t[2][:60]] for t in tramos(de) if t not in tramos(an)],
             "tramos_que_ya_no_estan": [list(t[:2]) + [t[2][:60]] for t in tramos(an) if t not in tramos(de)]}
        if a.solo_r5d is not None:
            e["igual_con_R5-d_sola"] = an == u(a.solo_r5d, i)
        e["ok"] = e["existe"] and e["texto_igual"] and e["titulo_igual"] and e.get("igual_con_R5-d_sola", True)
        d["encabezados_de_verdad"][i] = e
    d["ok"] = (d["ri_rml_1.2.3_termina"].endswith("estadounidenses-.") and d["ri_rml_1.2.4"]
               and d["ri_rml_1.3_empieza"].startswith("1.3. Integración del período")
               and d["snp_tr_1.3.3_termina"].endswith("el esquema de compensación entre CEC:")
               and all(d["snp_tr_existen"].values()) and all(d["snp_tr_nodos_1.3.4_1.3.5_1.3.6_1.4_1.5_1.5.2"].values())
               and d["snp_tr_1.6_encabezado"] == "1.6. Transacciones." and not d["snp_tr_1.6_intro_despues"]
               and all(e["ok"] for e in d["encabezados_de_verdad"].values()))
    # R5-e
    f3, f4 = u(a.despues, "ri_ccna::D1F3::S0")["texto"], u(a.despues, "ri_ccna::D1F4::S0")["texto"]
    res["R5-e"] = {"D1F3_termina": f3[-60:], "D1F4_empieza": f4[:260],
                   "letras_sueltas_en_D1F4": [r for r in f4.split("\n") if len(r.strip()) == 1 and r.strip().isupper()],
                   "ok": f3.endswith("Fórm. 4368 C (II-2006)") and "\nCODIGO\n" in f4
                   and not any(len(r.strip()) == 1 and r.strip().isupper() for r in f4.split("\n"))}
    res["resumen"] = {"R5-a": f"{res['R5-a']['casos_ok']} de 9 casos; {res['R5-a']['correctos_116_iguales']} de "
                              f"{res['R5-a']['correctos_116']} correctos iguales",
                      "R5-a′": res["R5-a′"]["ok"], "R5-b": res["R5-b"]["ok"],
                      "R5-c": f"{res['R5-c']['titulos_ok']} de 9 títulos; {res['R5-c']['chapeaux_iguales']} de 4 "
                              f"chapeaux iguales",
                      "R5-d": res["R5-d"]["ok"], "R5-e": res["R5-e"]["ok"]}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res["resumen"], ensure_ascii=False, indent=1))
    print(json.dumps({k: res["R5-b"]["uniones"][k] for k in res["R5-b"]["uniones"]}, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
