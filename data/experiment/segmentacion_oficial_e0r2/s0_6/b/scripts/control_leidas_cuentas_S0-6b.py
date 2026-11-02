"""El control de las 286 leídas de S0-6b en ids y cuentas (U-SEG-OFICIAL; decisión 9 de la autora: «En S0-6b, el control
de las leídas lleva su texto a un NO_ABRIR_ y deja en el archivo abierto solo ids y cuentas»; USD 0, solo lectura).

Uso: python -B control_leidas_cuentas_S0-6b.py --json <NO_ABRIR_control_leidas_S0-6b.json>
       --referencia <s0_6/bis/censos/control_leidas_S0-6a-bis.json> --out <json abierto>

Lee el JSON `NO_ABRIR_` (la salida de `s0_6/scripts/control_leidas_S0-6a.py` sobre la salida de los 152 contra la E0 de
S1-ter) sin imprimir nada de él, y escribe solo: por leída, su id (el de S1-ter) y si el corte y la herencia siguen
iguales; las cuentas (leídas, iguales, corte igual, herencia igual, cambiadas); y el control: el resultado de cada leída es
el mismo que en S0-6a-bis. No copia los campos que cambian, las preguntas, las reglas ni las unidades que solapan (pueden
nombrar unidades que no son leídas). Sale con 1 si el control no da.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
for k in ("json", "referencia", "out"):
    ap.add_argument(f"--{k}", type=Path, required=True)
a = ap.parse_args()
d = json.loads(a.json.read_text(encoding="utf-8"))
r = json.loads(a.referencia.read_text(encoding="utf-8"))
res_d = {u["id"]: (u["corte_igual"], u["herencia_igual"]) for u in d["unidades"]}
res_r = {u["id"]: (u["corte_igual"], u["herencia_igual"]) for u in r["unidades"]}
distintas = sorted(i for i in set(res_d) | set(res_r) if res_d.get(i) != res_r.get(i))
cuentas = {"leidas": len(res_d),
           "iguales": sum(1 for c, h in res_d.values() if c and h),
           "corte_igual": sum(1 for c, _ in res_d.values() if c),
           "herencia_igual": sum(1 for _, h in res_d.values() if h),
           "cambiadas": sum(1 for c, h in res_d.values() if not (c and h))}
control = {"mismo_conjunto_de_leidas": set(res_d) == set(res_r),
           "mismo_resultado_que_S0-6a-bis": not distintas,
           "leidas_con_otro_resultado": len(distintas),
           "cuentas_del_json_iguales_a_las_calculadas": all(d.get(k) == v for k, v in cuentas.items())}
out = {"unidad": "U-SEG-OFICIAL, S0-6b: control de las 286 leídas de S1-ter, en ids y cuentas (el JSON con texto, en el "
                 "NO_ABRIR_ del paquete)",
       "sha256_no_abrir": hashlib.sha256(a.json.read_bytes()).hexdigest(),
       "sha256_referencia": hashlib.sha256(a.referencia.read_bytes()).hexdigest(),
       "cuentas": cuentas, "control": control,
       "leidas_con_otro_resultado": distintas,
       "unidades": [{"id": i, "corte_igual": c, "herencia_igual": h} for i, (c, h) in sorted(res_d.items())]}
a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"cuentas": cuentas, "control": control}, ensure_ascii=False))
sys.exit(0 if not distintas and control["mismo_conjunto_de_leidas"] else 1)
