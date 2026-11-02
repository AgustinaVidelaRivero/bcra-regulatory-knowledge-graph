"""Reconstruye el r1_referencias.py de la segunda pasada de D (blob 84e8831f) desde el de HEAD, quitando lo de la opción B, y
lo acepta solo si su blob de git empieza con 84e8831f. Uso: python3 -I -B reconstruir_ref_d.py <HEAD> <salida>"""
import hashlib, re, sys
src = open(sys.argv[1], encoding="utf-8").read()
def blob(t):
    b = t.encode()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()
firma_head = ("                           punto_declarado_e1: bool = False, remisiones_a_subpuntos: bool = False,\n"
              "                           unidades_excluidas: list[str] | None = None) -> dict:\n")
assert src.count(firma_head) == 1
i = src.index("\n\n    `remisiones_a_subpuntos` (opción B;")
j = src.index('siempre."""', i)
doc_b = src[i:j + len("siempre.")]
bloque_ini = src.index("    if remisiones_a_subpuntos:\n        # Opción B, en una segunda pasada")
bloque_fin = src.index("    nuevas = [aristas[k] for k in sorted(aristas)]")
cands = {}
for firma in ("                           punto_declarado_e1: bool = False) -> dict:\n",):
    t = src.replace(firma_head, firma)
    t = t.replace(doc_b, "")
    t = t.replace("    # la procedencia completa con que se resolvió cada cita del registro (la segunda pasada de la opción B)\n"
                  "    procedencia_de_cita: dict[int, dict] = {}\n", "")
    t = t.replace("        procedencia_de_cita[id(cita)] = procedencia\n", "")
    a = t.index("    if remisiones_a_subpuntos:\n        # Opción B")
    b = t.index("    nuevas = [aristas[k] for k in sorted(aristas)]")
    t = t[:a] + t[b:]
    t = t.replace("    if remisiones_a_subpuntos:\n        resumen[\"remisiones_a_subpuntos\"] = conteo[\"remisiones_a_subpuntos\"]\n", "")
    cands[firma] = t
for f, t in cands.items():
    print(blob(t), "remisiones_a_subpuntos" in t, len(t))
    if blob(t).startswith("84e8831f"):
        open(sys.argv[2], "w", encoding="utf-8").write(t)
        print("OK: blob", blob(t))
