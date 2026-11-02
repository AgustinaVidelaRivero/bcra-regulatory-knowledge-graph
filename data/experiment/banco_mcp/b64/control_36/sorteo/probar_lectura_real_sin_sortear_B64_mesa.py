#!/usr/bin/env python3
"""probar_lectura_real_sin_sortear_B64_mesa.py — Mesa, §382: la lectura de los datos reales del sorteo de la muestra de 36 de B6.4, sin
sortear. Corre `leer_real` del script del sorteo sobre banco_b64 con un manifiesto provisorio de la mesa (en el scratchpad: solo los
archivos que `leer_real` lee, con su sha256), porque el de lo que queda fuera todavía no existe. Controla así, antes del sello, lo que la
prueba de juguete no ve: la forma real del estado, las salidas de pasada1/ y pasada2/, la entrada, las preguntas, los ids de los cuatro
brazos y D-10. No llama a `sortear` ni escribe ninguna clave: imprime solo las líneas de control que imprime el sorteo antes de sortear y
una línea sin cifras del juez. USD 0.

  python3 -I -B probar_lectura_real_sin_sortear_B64_mesa.py <carpeta del script del sorteo> <repo> <banco_b64> <manifiesto provisorio>
"""
import hashlib, importlib.util, json, sys
from pathlib import Path

S_DIR, REPO, BANCO, MAN = (Path(x).resolve() for x in sys.argv[1:5])
spec = importlib.util.spec_from_file_location("S", S_DIR / "sortear_control_36_B64.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
if MAN.exists():
    raise SystemExit("el manifiesto provisorio ya existe")
est = json.loads((BANCO / "resultados/real/estado_b63.json").read_text(encoding="utf-8"))
rels = list(S.DEL_BANCO.values()) + [f"resultados/real/{f['salida']}/meta_{f['id']}.json" for v in est["bloques"].values()
                                     for f in v["final"].values() if f["clasificacion"] == "completa"]
archivos = [{"ruta": "banco_b64/" + r, "sha256": hashlib.sha256((BANCO / r).read_bytes()).hexdigest()} for r in rels]
MAN.write_text(json.dumps({"que": "manifiesto provisorio de la mesa, solo para esta prueba", "archivos": archivos}) + "\n",
               encoding="utf-8")
sha_man = hashlib.sha256(MAN.read_bytes()).hexdigest()
sha, filas, rec, salen, n_metas, n_agr = S.leer_real(REPO, BANCO, MAN, sha_man)
print(f"controles: {len(S.DEL_REPO) + 1} entradas del repo iguales a HEAD; {len(S.DEL_BANCO)} entradas de banco_b64/ y {n_metas} metas "
      "de pasada1/ y pasada2/ con el sha256 del manifiesto provisorio; las preguntas, con el sha256 de la entrada sellada")
print(f"ids: {len(rec)} recalculados en los cuatro brazos; los mismos que los de los veredictos, sin sobrar ni faltar ninguno")
print("D-10: la marca recalculada da la cuenta de d10_b63.json en los cuatro brazos de la corrida")
print("la población es la del cierre de la corrida (1152, 1146, 6 y 70); hay elegibles en las nueve celdas (brazo, tipo):",
      all(any((f["brazo"], f["tipo"]) == (b, t) for f in filas) for b in S.BRAZOS for t in S.TIPOS),
      "| ninguna elegible de kg_n7:", all(f["brazo"] in S.BRAZOS for f in filas))
