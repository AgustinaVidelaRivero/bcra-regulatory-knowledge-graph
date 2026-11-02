"""Comparación de las E0 de los 152 entre commits del código de E0 (U-SEG-OFICIAL, S2, puntos 1 y 2; solo lectura).

Uso: python -B comparar_e0_historicas_S2.py --e0 <etiqueta>=<dir> [--e0 …] --out <json>
     (en orden: 92b45d6, e1c9456, 9f6361e6, corregida)

Para cada par consecutivo y por TO: ids solo en el anterior, ids solo en el siguiente, ids comunes con `texto` distinto y
con la herencia distinta (`chars_completo` o `sha256_completo`, con el mismo `texto`). Sin texto en la salida.
Además, para el punto 2: las diferencias entre las dos primeras (la corrida de R5, `92b45d6`, y el cierre, `e1c9456`,
que agrega K-a′+K-b) y en qué quedaron en la última (la E0 corregida): el id sigue o no, y su texto es el del cierre o
cambió después.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def cargar(d: Path, to: str) -> list[dict]:
    p = d / f"chunks_{to}.json"
    if not p.exists():
        return []
    x = json.loads(p.read_text(encoding="utf-8"))
    return x["chunks"] if isinstance(x, dict) else x


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    dirs = [(x.split("=", 1)[0], Path(x.split("=", 1)[1])) for x in a.e0]
    tos = sorted(p.name[len("chunks_"):-5] for p in dirs[-1][1].glob("chunks_*.json"))
    datos = {et: {to: {c["id"]: c for c in cargar(d, to)} for to in tos} for et, d in dirs}
    out = {"etiquetas": [et for et, _ in dirs], "tos": len(tos),
           "conteos_sha256": {et: hashlib.sha256((d / "conteos.json").read_bytes()).hexdigest() for et, d in dirs},
           "pares": {}}
    for (ea, _), (eb, _) in zip(dirs, dirs[1:]):
        por_to, tot = {}, {"solo_antes": 0, "solo_despues": 0, "texto_distinto": 0, "herencia_distinta": 0}
        for to in tos:
            A, B = datos[ea][to], datos[eb][to]
            sa, sb = sorted(set(A) - set(B)), sorted(set(B) - set(A))
            comunes = set(A) & set(B)
            txt = sorted(i for i in comunes if A[i]["texto"] != B[i]["texto"])
            her = sorted(i for i in comunes if A[i]["texto"] == B[i]["texto"]
                         and (A[i].get("chars_completo"), A[i].get("sha256_completo"))
                         != (B[i].get("chars_completo"), B[i].get("sha256_completo")))
            if sa or sb or txt or her:
                por_to[to] = {"solo_antes": sa, "solo_despues": sb, "texto_distinto": txt, "herencia_distinta": her}
                for k, v in (("solo_antes", sa), ("solo_despues", sb), ("texto_distinto", txt), ("herencia_distinta", her)):
                    tot[k] += len(v)
        out["pares"][f"{ea} -> {eb}"] = {"tos_con_cambios": len(por_to), "totales": tot,
                                         "tos": {t: {k: len(v) for k, v in x.items()} for t, x in por_to.items()},
                                         "detalle": por_to}
    # punto 2: K-a′+K-b (primer par) en la E0 final
    e_r5, e_cierre, e_fin = dirs[0][0], dirs[1][0], dirs[-1][0]
    p = out["pares"][f"{e_r5} -> {e_cierre}"]["detalle"]
    seg = {}
    for to, x in p.items():
        F, Cc = datos[e_fin][to], datos[e_cierre][to]
        seg[to] = {
            "ids_nuevos_del_cierre": {"n": len(x["solo_despues"]),
                                      "siguen_en_la_final": sum(1 for i in x["solo_despues"] if i in F),
                                      "con_el_texto_del_cierre": sum(1 for i in x["solo_despues"] if i in F and F[i]["texto"] == Cc[i]["texto"])},
            "ids_que_el_cierre_quito": {"n": len(x["solo_antes"]),
                                        "siguen_fuera_en_la_final": sum(1 for i in x["solo_antes"] if i not in F)},
            "textos_que_el_cierre_cambio": {"n": len(x["texto_distinto"]),
                                            "con_el_texto_del_cierre": sum(1 for i in x["texto_distinto"] if i in F and F[i]["texto"] == Cc[i]["texto"]),
                                            "cambiados_despues": sum(1 for i in x["texto_distinto"] if i in F and F[i]["texto"] != Cc[i]["texto"]),
                                            "id_ya_no_esta": sum(1 for i in x["texto_distinto"] if i not in F)}}
    out["punto_2_ka_kb_en_la_final"] = seg
    out["ric_en_los_152"] = "ric" in tos
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in out["pares"].items():
        print(k, v["tos_con_cambios"], v["totales"])
        print("   ", dict(list(v["tos"].items())[:12]))
    print("punto 2", json.dumps(seg, ensure_ascii=False))
    print("ric en los 152:", out["ric_en_los_152"])


if __name__ == "__main__":
    main()
