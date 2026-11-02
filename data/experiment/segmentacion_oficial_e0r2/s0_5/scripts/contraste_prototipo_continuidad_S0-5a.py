"""Contraste del control de continuidad de S0-5a con el prototipo de la mesa (U-SEG-OFICIAL; solo lectura).
Uso: python -B contraste_prototipo_continuidad_S0-5a.py <salida del prototipo sobre S0-4b> <salida de S0-5a sobre S0-4b>
Por salto (TO, subdocumento, rótulo): los que están en los dos y si coinciden la clase y la forma; los que están en uno
solo, por TO. La forma del prototipo se nombra «a_hueco» y «b_cola»; acá, «hueco» y «cola».
"""
import collections
import json
import sys

m, a = json.load(open(sys.argv[1], encoding="utf-8")), json.load(open(sys.argv[2], encoding="utf-8"))
k = lambda f: (f["to"], f.get("subdocumento") or "", f["rotulo"])
fm, fa = {k(f): f for f in m["filas"]}, {k(f): f for f in a["filas"]}
comunes = sorted(set(fm) & set(fa))
forma = lambda f: f["forma"].split("_", 1)[-1]
distinta = [x for x in comunes if (fm[x]["clase"], forma(fm[x])) != (fa[x]["clase"], forma(fa[x]))]
solo_a = sorted(set(fa) - set(fm))
print(json.dumps({"prototipo": len(fm), "S0-5a": len(fa), "en_los_dos": len(comunes),
                  "en_los_dos_con_otra_clase_o_forma": distinta, "solo_en_el_prototipo": sorted(set(fm) - set(fa)),
                  "solo_en_S0-5a_por_to": dict(collections.Counter(x[0] for x in solo_a))}, ensure_ascii=False))
