"""U-SEG-OFICIAL, S1-ter.1: el manifiesto de S1-ter contra el de S1-bis, campo por campo (USD 0, sin API).

Uso: python -B comparar_manifiestos_S1ter.py --s1bis <manifiesto de S1-bis> --s1ter <manifiesto de S1-ter>
       --copia <raíz de una copia del repo> --out <json>

Copia de `s1bis/scripts/comparar_manifiestos_S1bis.py` con la referencia corrida un paso (S1-bis en lugar de S1) y los
nombres de los argumentos y de las claves de la salida en consecuencia; la lógica, igual.

- Lista cada campo que difiere entre los dos manifiestos (claves de primer nivel y, en `tos`, cada campo de cada TO).
  Los cambios declarados en `armar_manifiesto_S1ter.py` son `descripcion`, `rutas.e0_salida`, `sellos.unidad` y
  `sellos.commit_codigo_e0`; cualquier otro es hallazgo.
- Controla el rol de alcance de los documentos con alcance del registro (`catalogo_unico/registro_alcance_por_tanda.md`,
  primera columna de sus tablas): qué declara el manifiesto y si `manifiesto_corpus.cargar` lo carga.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DECLARADOS = {"descripcion", "rutas.e0_salida", "sellos.unidad", "sellos.commit_codigo_e0"}


def plano(d, pre=""):
    out = {}
    for k, v in d.items():
        r = f"{pre}{k}"
        if isinstance(v, dict) and k != "estimado_usd":
            out.update(plano(v, r + "."))
        else:
            out[r] = v
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("s1bis", "s1ter", "copia", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    m1 = json.loads(a.s1bis.read_text(encoding="utf-8"))
    m2 = json.loads(a.s1ter.read_text(encoding="utf-8"))
    t1, t2 = {t["id"]: t for t in m1["tos"]}, {t["id"]: t for t in m2["tos"]}
    p1 = plano({k: v for k, v in m1.items() if k != "tos"})
    p2 = plano({k: v for k, v in m2.items() if k != "tos"})
    primer = {k: [p1.get(k), p2.get(k)] for k in sorted(set(p1) | set(p2)) if p1.get(k) != p2.get(k)}
    por_to = {}
    for to in sorted(set(t1) | set(t2)):
        a_, b_ = t1.get(to) or {}, t2.get(to) or {}
        dif = {k: [a_.get(k), b_.get(k)] for k in sorted(set(a_) | set(b_)) if a_.get(k) != b_.get(k)}
        if dif:
            por_to[to] = dif
    # documentos con alcance en el registro: primera columna de las tablas, salvo las de candidatos sin decidir
    reg = (a.copia / "data/experiment/catalogo_unico/registro_alcance_por_tanda.md").read_text(encoding="utf-8")
    con_alcance, tabla = [], None
    for ln in reg.splitlines():
        if ln.startswith("## "):
            tabla = ln
        m = re.match(r"^\| (\w+) \| .*?\| (clase|clase \(dos\)|rol reutilizado|sin alcance declarado) \|", ln)
        if m and tabla and "Candidatos" not in tabla:
            con_alcance.append({"to": m.group(1), "decision": m.group(2), "tabla": tabla.strip("# ").split(" — ")[0]})
    for e in con_alcance:
        e["rol_alcance_manifiesto"] = t2[e["to"]]["rol_alcance"] if e["to"] in t2 else "fuera del manifiesto"
    sys.path.insert(0, str(a.copia / "data/experiment/reextraccion_v2"))
    import manifiesto_corpus
    carga = {"ok": True, "error": None}
    try:
        man = manifiesto_corpus.cargar(a.s1ter)
        carga["tos"] = len(man.ids)
        carga["e0_salida"] = str(man.e0_salida.relative_to(a.copia))
    except Exception as ex:  # el error de carga se registra, no se corrige
        carga = {"ok": False, "error": repr(ex)}
    res = {"cambios_declarados": sorted(DECLARADOS),
           "difieren_primer_nivel": primer,
           "no_declarados_primer_nivel": sorted(set(primer) - DECLARADOS),
           "declarados_que_no_cambian": sorted(DECLARADOS - set(primer)),
           "tos_s1bis": len(t1), "tos_s1ter": len(t2), "tos_que_difieren": por_to,
           "documentos_del_registro": con_alcance,
           "con_alcance_y_rol_null": [e["to"] for e in con_alcance
                                      if e["decision"] != "sin alcance declarado" and e["rol_alcance_manifiesto"] is None],
           "carga_manifiesto_corpus": carga}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
