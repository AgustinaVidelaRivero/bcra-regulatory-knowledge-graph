"""U-SEG-OFICIAL, S1-bis.3: doble corrida, tanda 0, health-check de E0 por TO y controles de la salida (USD 0).

Uso: python -B controles_S1bis.py --copia <raíz de una copia> --c1 <corrida 1> --c2 <corrida 2> --manifiesto <json>
       --lineas <caché de renglones de lineas_152.py> --s04b <manifiesto de los 768 de S0-4b> --out <json>

Copia de `s1/scripts/controles_S1.py` con un cambio: el control de los 26 TOs de S0-2 (`cmp_9f6361e_vs_S0-2.json`,
que comparaba contra el código de S0-2) se reemplaza por la comparación de los 768 archivos de la corrida 1 contra el
manifiesto de la salida de S0-4b (`manifiesto_salida_e0_152_S0-4b.json`, sha256 y bytes de cada archivo y unidades
por TO), el mismo código de E0. Lo demás, igual.

- Doble corrida: todos los archivos de las dos corridas, byte a byte.
- Tanda 0: ctacte, lingob, polcre, pagjub y docvig contra `reextraccion_v2/e0_chunking/salida_tanda0_r2b/` de la copia
  (igual a `9f6361e`): los archivos por TO byte a byte; en los agregados, la entrada del TO (igual como valor y como
  texto serializado con el formato de correr_e0); `version_e0.json` byte a byte; ningún id desambiguado.
- Health-check sobre la salida de e0-r2, con las cuatro señales de `healthcheck_e0.py` (que corre la versión legada y
  por eso no se usa sobre esta salida): cid (renglones del PDF, todos los roles), páginas sin sección (sin página de
  cuerpo, 0 secciones reales o avisos `pagina_cuerpo_sin_seccion`), unidades terminales de más de 26.182 caracteres
  propios (con su declaración en `sub_chunking.json`) y cobertura no exacta.
- Ningún TO de la vía por punto en 0 chunks; ningún id repetido; cobertura exacta; total de unidades; los 768
  archivos contra el manifiesto de S0-4b; modo de lectura de e0-r2 contra el de la partición;
  unidades de los 14 TOs fuera de las tandas contra la partición (hallazgo de clase); unidades por punto de ri2_pm con
  la regla de `no_segmentables_limite/l2_regla_parciales.md`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

TANDA0 = ("ctacte", "lingob", "polcre", "pagjub", "docvig")
POR_TO = ("chunks", "estructura", "indice", "pies", "tablas")
AGREGADOS = ("conteos.json", "cobertura.json", "correcciones.json", "divergencias_indice_cuerpo.json",
             "encabezados_conservados.json", "sub_chunking.json", "ids_desambiguados.json")
UMBRAL = 26182


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jl(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def doble_corrida(a: Path, b: Path) -> dict:
    fa = {p.name for p in a.iterdir()}
    fb = {p.name for p in b.iterdir()}
    comunes = sorted(fa & fb)
    distintos = [n for n in comunes if (a / n).read_bytes() != (b / n).read_bytes()]
    return {"archivos_corrida_1": len(fa), "archivos_corrida_2": len(fb), "comunes": len(comunes),
            "distintos": distintos, "solo_en_una": sorted(fa ^ fb)}


def tanda0(sal: Path, t0: Path) -> dict:
    out = {"por_to": {}, "agregados": {}}
    for to in TANDA0:
        d = {}
        for pre in POR_TO:
            n = f"{pre}_{to}.json"
            d[n] = (sal / n).exists() and (t0 / n).exists() and (sal / n).read_bytes() == (t0 / n).read_bytes()
        out["por_to"][to] = d
    for n in AGREGADOS:
        A = jl(sal / n) if (sal / n).exists() else {}
        B = jl(t0 / n) if (t0 / n).exists() else {}
        r = {}
        for to in TANDA0:
            ea, eb = A.get(to), B.get(to)
            r[to] = {"en_s1": ea is not None, "en_tanda0": eb is not None,
                     "igual_valor": ea == eb,
                     "igual_texto": json.dumps(ea, ensure_ascii=False, indent=1)
                     == json.dumps(eb, ensure_ascii=False, indent=1)}
        out["agregados"][n] = r
    out["version_e0.json"] = (sal / "version_e0.json").read_bytes() == (t0 / "version_e0.json").read_bytes()
    archivos = [v for d in out["por_to"].values() for v in d.values()]
    ag = [x["igual_valor"] and x["igual_texto"] for r in out["agregados"].values() for x in r.values()]
    out["resumen"] = {"archivos_por_to_iguales": sum(archivos), "archivos_por_to": len(archivos),
                      "entradas_de_agregados_iguales": sum(ag), "entradas_de_agregados": len(ag),
                      "version_e0_igual": out["version_e0.json"]}
    return out


def cargar_lineas(cache: Path, to: str) -> list:
    return jl(cache / f"{to}.json")


def health(sal: Path, to: str, lineas: list, roles: list[str], conteo: dict, cob: dict, sub: dict) -> dict:
    cid = [{"pagina": p + 1, "rol": roles[p], "texto": l[3][:90]}
           for p, pag in enumerate(lineas) for l in pag if "(cid:" in l[3]]
    est = jl(sal / f"estructura_{to}.json")
    secc = [s for s in est["secciones"] if not (s.get("sintetica") and s.get("numero") == "0")]
    avisos = [a for a in est["avisos"] if a["tipo"] == "pagina_cuerpo_sin_seccion"]
    n_cuerpo = roles.count("cuerpo")
    chunks = jl(sal / f"chunks_{to}.json")
    term = [c for c in chunks if c["tipo"] != "mini_chunk"]
    declaradas = {d.get("unidad") or d.get("id") for d in (sub.get("no_particionables") or [])}
    anom = [{"id": c["id"], "chars_propio": c["chars_propio"],
             "declarada_sin_partir": c["unidad"] in declaradas or c["id"] in declaradas}
            for c in term if c["chars_propio"] > UMBRAL]
    sen = []
    if cid:
        sen.append("cid")
    if n_cuerpo == 0 or not secc or avisos:
        sen.append("paginas_sin_seccion")
    if anom:
        sen.append("unidades_anomalas_por_tamano")
    if not cob["cobertura_exacta"]:
        sen.append("cobertura_no_exacta")
    return {"veredicto": "sano" if not sen else sen,
            "cid": {"renglones": len(cid), "paginas": sorted({c["pagina"] for c in cid})[:50]},
            "paginas_sin_seccion": {"paginas_cuerpo": n_cuerpo, "secciones_reales": len(secc),
                                    "avisos_pagina_cuerpo_sin_seccion": len(avisos)},
            "anomalas": anom}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("copia", "c1", "c2", "manifiesto", "lineas", "s04b", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    ex = a.copia / "data/experiment"
    sal = a.c1
    man = jl(a.manifiesto)
    tos = [t["id"] for t in man["tos"]]
    via = {t["id"]: t["via"] for t in man["tos"]}
    part = jl(ex / "segmentacion_84/b584_particion/particion_152.json")["por_to"]
    cb = jl(ex / "segmentacion_84/b584_particion/conteos_b584.json")
    s04b = jl(a.s04b)
    conteos, cobertura = jl(sal / "conteos.json"), jl(sal / "cobertura.json")
    sub = jl(sal / "sub_chunking.json") if (sal / "sub_chunking.json").exists() else {}
    desamb = jl(sal / "ids_desambiguados.json") if (sal / "ids_desambiguados.json").exists() else {}

    res: dict = {"doble_corrida": doble_corrida(a.c1, a.c2),
                 "tanda0": tanda0(sal, ex / "reextraccion_v2/e0_chunking/salida_tanda0_r2b")}
    res["tanda0"]["ids_desambiguados_de_la_tanda0"] = sorted(set(desamb) & set(TANDA0))

    por_to, ids_rep, cero, total = {}, {}, [], 0
    for to in tos:
        ch = jl(sal / f"chunks_{to}.json")
        pies = jl(sal / f"pies_{to}.json")
        roles = [d["rol"] for d in pies["paginas_detalle"]]
        n = len(ch)
        total += n
        rep = [i for i, k in Counter(c["id"] for c in ch).items() if k > 1]
        if rep:
            ids_rep[to] = rep
        if via[to] == "por_punto" and n == 0:
            cero.append(to)
        lin = cargar_lineas(a.lineas, to)
        assert len(lin) == len(roles), f"{to}: páginas del caché ≠ páginas de pies"
        por_to[to] = {"via": via[to], "clase": part[to]["clase"], "chunks": n,
                      "chunks_terminales": conteos[to]["chunks_terminales"], "mini_chunks": conteos[to]["mini_chunks"],
                      "modo_lectura_e0r2": conteos[to]["modo_lectura"], "modo_lectura_b584": cb[to]["modo_lectura"],
                      "unidades_particion": part[to]["unidades"], "cobertura_exacta": cobertura[to]["cobertura_exacta"],
                      "health_check": health(sal, to, lin, roles, conteos[to], cobertura[to], sub.get(to, {})),
                      "health_check_b584": cb[to].get("healthcheck_veredicto")}
    res["por_to"] = por_to
    res["ids_repetidos"] = ids_rep
    res["tos_por_punto_en_0_chunks"] = cero
    res["cobertura_no_exacta"] = [t for t in tos if not por_to[t]["cobertura_exacta"]]
    res["unidades_total"] = total
    res["unidades_por_tipo"] = dict(Counter(c["tipo"] for t in tos for c in jl(sal / f"chunks_{t}.json")))
    res["unidades_por_rol_bloque"] = dict(Counter(str(c.get("rol_bloque")) for t in tos
                                               for c in jl(sal / f"chunks_{t}.json")))
    arch = {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(sal.glob("*.json"))}
    ref = s04b["sha256"]
    res["contra_s04b"] = {"manifiesto": a.s04b.name, "archivos_s04b": len(ref), "archivos_s1bis": len(arch),
                          "iguales": sum(1 for n in arch if ref.get(n) == arch[n]),
                          "distintos": sorted(n for n in arch if n in ref and ref[n] != arch[n]),
                          "solo_en_una": sorted(set(arch) ^ set(ref)),
                          "unidades_s04b": s04b["unidades"], "unidades_s1bis": total,
                          "unidades_por_to_distintas": {t: [s04b["unidades_por_to"].get(t), por_to[t]["chunks"]]
                                                        for t in tos
                                                        if s04b["unidades_por_to"].get(t) != por_to[t]["chunks"]}}
    res["modo_lectura_distinto_de_b584"] = {t: [v["modo_lectura_b584"], v["modo_lectura_e0r2"]]
                                            for t, v in por_to.items()
                                            if v["modo_lectura_b584"] != v["modo_lectura_e0r2"]}
    res["fuera_de_las_tandas"] = {t: {"clase": v["clase"], "unidades_particion": v["unidades_particion"],
                                      "unidades_e0r2": v["chunks"], "modo_e0r2": v["modo_lectura_e0r2"],
                                      "igual": v["unidades_particion"] == v["chunks"]}
                                  for t, v in por_to.items() if v["clase"] != "reconocido_pleno"}
    hc = Counter("sano" if v["health_check"]["veredicto"] == "sano" else "con_senales" for v in por_to.values())
    res["health_check_resumen"] = {"veredictos": dict(hc),
                                   "por_senal": dict(Counter(s for v in por_to.values()
                                                             if v["health_check"]["veredicto"] != "sano"
                                                             for s in v["health_check"]["veredicto"]))}
    # ri2_pm: unidades por punto (regla de l2_regla_parciales.md)
    ch = jl(sal / "chunks_ri2_pm.json")
    roles = [d["rol"] for d in jl(sal / "pies_ri2_pm.json")["paginas_detalle"]]
    fichas = {i + 1 for i, r in enumerate(roles) if r == "ficha_registro"}
    pp, cruzan = [], []
    for c in ch:
        a_, b_ = min(c["paginas"]), max(c["paginas"])
        (cruzan if any(a_ <= f <= b_ for f in fichas) else pp).append(c["id"])
    res["ri2_pm"] = {"paginas_ficha_registro": len(fichas), "unidades": len(ch), "por_punto": len(pp),
                     "cruzan_fichas": cruzan, "ids_por_punto": pp,
                     "paginas_por_punto": sorted({p for c in ch if c["id"] in pp for p in c["paginas"]})}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("unidades_total", "tos_por_punto_en_0_chunks", "ids_repetidos",
                                          "cobertura_no_exacta", "modo_lectura_distinto_de_b584",
                                          "health_check_resumen")}, ensure_ascii=False, indent=1))
    print(json.dumps({"doble": {k: (v if not isinstance(v, list) else len(v)) for k, v in res["doble_corrida"].items()},
                      "tanda0": res["tanda0"]["resumen"], "s04b": res["contra_s04b"],
                      "ri2_pm": {k: v for k, v in res["ri2_pm"].items() if k not in ("ids_por_punto",)},
                      "fuera": res["fuera_de_las_tandas"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
