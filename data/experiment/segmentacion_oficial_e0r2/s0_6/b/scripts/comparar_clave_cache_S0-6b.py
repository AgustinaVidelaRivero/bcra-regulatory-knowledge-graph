"""Compara la salida del selftest de claves de la caché de S0-6b con la de S0-6a-bis (U-SEG-OFICIAL, S0-6b; USD 0, solo
lectura): recorre los dos JSON y lista las rutas que difieren, con el tipo y, de listas y diccionarios, su largo; de
números y booleanos, el valor; de textos, solo su largo (los JSON llevan claves con ids de unidades de la tanda 0: no se
imprimen). Lo único que puede cambiar es una fila más en `contraste_tabla.filas` (la de F19d).

Uso: python -B comparar_clave_cache_S0-6b.py --antes <json de S0-6a-bis> --despues <json de S0-6b> --out <json>
"""
import argparse
import hashlib
import json
from pathlib import Path


def desc(x):
    if isinstance(x, (list, dict)):
        return {"tipo": type(x).__name__, "largo": len(x)}
    if isinstance(x, (bool, int, float)) or x is None:
        return {"tipo": type(x).__name__, "valor": x}
    return {"tipo": type(x).__name__, "largo": len(str(x))}


def comparar(a, b, ruta, out):
    if type(a) is not type(b):
        out.append({"ruta": ruta, "antes": desc(a), "despues": desc(b)})
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            r = f"{ruta}.{k}" if "::" not in str(k) else f"{ruta}.<clave>"
            if k not in a or k not in b:
                out.append({"ruta": r, "antes": desc(a.get(k)) if k in a else None,
                            "despues": desc(b.get(k)) if k in b else None})
            else:
                comparar(a[k], b[k], r, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            comunes = sum(1 for x, y in zip(a, b) if x == y)
            fila = {"ruta": ruta, "antes": desc(a), "despues": desc(b), "primeros_iguales": comunes}
            if len(b) == len(a) + 1:
                # un elemento insertado: sin él, la lista nueva es la vieja; de él, solo su rótulo de fila
                for i in range(len(b)):
                    if b[:i] + b[i + 1:] == a:
                        fila["insertado_en"] = i
                        fila["insertado_fila"] = b[i].get("fila") if isinstance(b[i], dict) else None
                        fila["sin_el_igual_a_antes"] = True
                        break
            out.append(fila)
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                comparar(x, y, f"{ruta}[{i}]", out)
    elif a != b:
        out.append({"ruta": ruta, "antes": desc(a), "despues": desc(b)})


ap = argparse.ArgumentParser()
for k in ("antes", "despues", "out"):
    ap.add_argument(f"--{k}", type=Path, required=True)
a = ap.parse_args()
A, B = (json.loads(p.read_text(encoding="utf-8")) for p in (a.antes, a.despues))
dif = []
comparar(A, B, "$", dif)
res = {"sha256_antes": hashlib.sha256(a.antes.read_bytes()).hexdigest(),
       "sha256_despues": hashlib.sha256(a.despues.read_bytes()).hexdigest(),
       "veredicto_despues": next((v for k, v in B.items() if k.lower() == "veredicto"), None) if isinstance(B, dict) else None,
       "diferencias": dif}
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
