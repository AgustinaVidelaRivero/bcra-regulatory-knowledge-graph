"""Punto 2 de S2 (U-SEG-OFICIAL): la escalera de R5, si se reproduce, y las diferencias que explican K-a′+K-b y el punto
(f) (solo lectura).

Uso: python -B escalera_r5_S2.py --r5-r5 <control de R5 sobre la E0 de 92b45d6> --r5-cierre <ídem, e1c9456>
       --historicas <comparar_e0_historicas_S2b.json> --out <json>

- Reproducción: el control de R5 (`r5_escalera_particion.py --comparar --atribuir`) sobre la E0 de los 152 con el código
  de 92b45d6 (el commit de R5) y de e1c9456 (el del cierre, que agrega K-a′+K-b), contra las cifras de sus FRENOs
  (`data/experiment/r2_codigo/r5_freno.md:59-66` y `cierre_freno.md:50-72`), escritas abajo tal como las da cada FRENO.
- K-a′+K-b: las diferencias entre esas dos E0 (`pares["92b45d6 -> e1c9456"]`) y en qué quedaron en la E0 corregida
  (`punto_2_ka_kb_en_la_final`).
- (f): solo actúa en ric (`docs/mandatos/UR2CODIGO2_correcciones_previas_a_reext.md:101-110`), que no está en los 152.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ESPERADO = {
    "92b45d6": {"freno": "data/experiment/r2_codigo/r5_freno.md:59-66", "tos_con_ids_iguales": 128,
                "ids": {"ids_desambiguados": 69, "particion_no_aplicada_por_tabla": 7}, "K": 205, "tos_K": 19,
                "texto": {"tablas": 145, "K": 72, "K (arrastre de un cambio de ids)": 32, "pies": 45, "pies y K": 5},
                "otra": 0},
    "e1c9456": {"freno": "data/experiment/r2_codigo/cierre_freno.md:50-72", "tos_con_ids_iguales": 129,
                "ids": {"ids_desambiguados": 69, "particion_no_aplicada_por_tabla": 8}, "K": 93, "tos_K": 16,
                "texto": {"tablas": 146, "K": 64, "K (arrastre de un cambio de ids)": 1, "pies": 45, "pies y K": 5},
                "otra": 0},
}


def resumen(r5: dict) -> dict:
    causa = r5["diferencias_de_ids_otra_por_causa"]
    tos_k = sorted({x["to"] for x in r5["unidades_por_causa"].get("K", [])})
    txt = dict(r5["chunks_con_texto_distinto_por_clase"])
    return {"tos": r5["tos"], "tos_en_cero": len(r5["tos_en_cero_que_la_particion_segmenta"]),
            "modo_distinto": len(r5["modo_de_lectura_distinto"]), "tos_con_ids_iguales": r5["tos_con_ids_iguales"],
            "ids": {k: v for k, v in r5["diferencias_de_ids_por_clase"].items() if k != "otra"},
            "K": causa.get("K", 0), "tos_K": len(tos_k), "lista_tos_K": tos_k,
            "ids_otra_sin_K": sum(v for k, v in causa.items() if k not in ("K",)),
            "texto": {k: v for k, v in txt.items() if k != "otra"}, "texto_otra": txt.get("otra", 0)}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("--r5-r5", "--r5-cierre", "--historicas", "--out"):
        ap.add_argument(k, type=Path, required=True)
    a = ap.parse_args()
    res = {"92b45d6": resumen(json.loads(a.r5_r5.read_text(encoding="utf-8"))),
           "e1c9456": resumen(json.loads(a.r5_cierre.read_text(encoding="utf-8")))}
    h = json.loads(a.historicas.read_text(encoding="utf-8"))
    rep = {}
    for c, e in ESPERADO.items():
        r = res[c]
        rep[c] = {"tos_con_ids_iguales": r["tos_con_ids_iguales"] == e["tos_con_ids_iguales"],
                  "ids": all(r["ids"].get(k, 0) == v for k, v in e["ids"].items()),
                  "K": r["K"] == e["K"] and r["tos_K"] == e["tos_K"],
                  "texto": all(r["texto"].get(k, 0) == v for k, v in e["texto"].items()) and set(r["texto"]) <= set(e["texto"]),
                  "otra": r["ids_otra_sin_K"] == 0 and r["texto_otra"] == 0}
        rep[c]["reproduce"] = all(rep[c].values())
    ka = h["pares"]["92b45d6 -> e1c9456"]
    seg = h["punto_2_ka_kb_en_la_final"]
    out = {"esperado": ESPERADO, "obtenido": res, "reproduce": rep, "ka_kb": {"tos": ka["tos"], "totales": ka["totales"]},
           "ka_kb_en_la_corregida": seg, "f_en_los_152": 0 if not h["ric_en_los_152"] else None,
           "historicas_sha256": hashlib.sha256(a.historicas.read_bytes()).hexdigest()}

    def fila(c):
        r, e = res[c], ESPERADO[c]
        return (f"| `{c}` (`{e['freno'].split(':')[0].split('/')[-1]}`) | {r['tos_con_ids_iguales']} ({e['tos_con_ids_iguales']}) | "
                f"{r['ids'].get('ids_desambiguados', 0)} ({e['ids']['ids_desambiguados']}) | "
                f"{r['ids'].get('particion_no_aplicada_por_tabla', 0)} ({e['ids']['particion_no_aplicada_por_tabla']}) | "
                f"{r['K']} en {r['tos_K']} ({e['K']} en {e['tos_K']}) | "
                + ", ".join(f"{k} {r['texto'].get(k, 0)} ({v})" for k, v in e["texto"].items())
                + f" | {r['ids_otra_sin_K']} / {r['texto_otra']} (0 / 0) | {'sí' if rep[c]['reproduce'] else 'no'} |")
    md = ["El control de R5 sobre la E0 de los 152 con el código de cada commit (`lote_e0_historicas_S2b.sh`, después "
          "`r5_escalera_particion.py --comparar --atribuir` con el `e0_lib` de ese commit; `escalera_r5_S2b.json`, claves "
          "`obtenido` y `reproduce`). Entre paréntesis, la cifra del FRENO de cada corrida.", "",
          "| código | TOs con los mismos ids | ids L | partición por tabla | ids K | texto distinto por clase | «otra» (ids / texto) | reproduce |",
          "|---|--:|--:|--:|---|---|---|---|", fila("92b45d6"), fila("e1c9456"), ""]
    md.append(f"- **Con `e1c9456` se reproduce el cierre, no la corrida de R5.** `e1c9456` ya trae K-a′+K-b; las cifras del "
              f"FRENO R5 (205 ids de K en 19 TOs) salen con el código de `92b45d6`. Las dos se reproducen: "
              f"`92b45d6` {'sí' if rep['92b45d6']['reproduce'] else 'no'}, `e1c9456` {'sí' if rep['e1c9456']['reproduce'] else 'no'}.")
    t = ka["totales"]
    md.append(f"- **Lo que explica K-a′+K-b** (`92b45d6` → `e1c9456`, `comparar_e0_historicas_S2b.json`, "
              f"`pares[\"92b45d6 -> e1c9456\"]`): cambia {len(ka['tos'])} TOs, {', '.join(ka['tos'])}; salen "
              f"{t['solo_antes']} ids, entran {t['solo_despues']}, cambia el texto de {t['texto_distinto']} chunks y solo la "
              f"herencia de {t['herencia_distinta']}. Son los cuatro TOs del commit (`git show e1c9456`).")
    md.append("  En qué quedaron en la E0 corregida (`punto_2_ka_kb_en_la_final`):")
    for to, s in seg.items():
        partes = []
        a_, q_, t_ = s["ids_nuevos_del_cierre"], s["ids_que_el_cierre_quito"], s["textos_que_el_cierre_cambio"]
        if a_["n"]:
            partes.append(f"ids que trajo: {a_['n']}, siguen {a_['siguen_en_la_final']} ({a_['con_el_texto_del_cierre']} con el mismo texto)")
        if q_["n"]:
            partes.append(f"ids que quitó: {q_['n']}, siguen fuera {q_['siguen_fuera_en_la_final']}")
        if t_["n"]:
            partes.append(f"textos que cambió: {t_['n']}; siguen iguales {t_['con_el_texto_del_cierre']}, cambiaron después "
                          f"{t_['cambiados_despues']}, id que ya no está (lo movió S0) {t_['id_ya_no_esta']}")
        md.append(f"  - {to}: " + "; ".join(partes) + ".")
    md.append("- **El punto (f):** 0 diferencias en los 152. Solo actúa en ric (`RENUMERACIONES_E0_R2`, `correr_e0.py:86-87`), "
              "que es de desarrollo y no está en los 152 (`comparar_e0_historicas_S2b.json`, `ric_en_los_152`).")
    out["texto_md"] = "\n".join(md)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"reproduce": rep, "obtenido": {c: {k: v for k, v in r.items() if k != "lista_tos_K"} for c, r in res.items()}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
