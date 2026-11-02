"""Mesa, §119: fichas y planilla vacía de los 30 cortes de la lectura corta de 1.16 en la tanda final, en el orden sellado. USD 0, sin
API. No marca nada.

Uso: python3 -I -B <este> --orden <orden_y_cortes_116_tanda_final.json> --sha-orden <sha256 del sello> --detector <detector_116_S2b.json>
       --e0 <E0 corregida> --manifiesto-e0 <manifest_salida_e0_152_S0-6b.json> --manifiesto-152 <segmentacion_oficial_e0r2_152.json>
       --raiz-repo <copia del repo> --out <carpeta>

Controla antes de escribir: el orden contra el sha256 de su sello, los 768 archivos de la E0 contra su manifiesto y cada PDF contra el
manifiesto de los 152. Cada ficha, como las de 1.16 de S1-bis: id, documento, páginas (con su imagen), tipo, rol, caracteres, la lista
(el padre y sus ítems) y el cierre candidato del detector, la herencia y el texto propio, tal como salen de E0; y, como contexto, la
unidad que sigue en E0 con su texto."""
import argparse, csv, hashlib, json, os, subprocess, sys
ap = argparse.ArgumentParser()
for a in ("--orden", "--sha-orden", "--detector", "--e0", "--manifiesto-e0", "--manifiesto-152", "--raiz-repo", "--out"):
    ap.add_argument(a, required=True)
A = ap.parse_args()
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
if sha(A.orden) != A.sha_orden: sys.exit("FRENO: el orden no da el sha256 de su sello")
orden = json.load(open(A.orden, encoding="utf-8"))["cortes"]
me0 = json.load(open(A.manifiesto_e0, encoding="utf-8"))["sha256"]
if [k for k, v in me0.items() if k.startswith("e0/") and sha(os.path.join(A.e0, k[3:])) != v["sha256"]]:
    sys.exit("FRENO: la E0 no da su manifiesto")
m152 = {t["id"]: t for t in json.load(open(A.manifiesto_152, encoding="utf-8"))["tos"]}
det = {c["id"]: c for c in json.load(open(A.detector, encoding="utf-8"))["candidatos"]}
os.makedirs(os.path.join(A.out, "paginas"), exist_ok=True)
L = ["# Lectura corta de 1.16 en la tanda final: fichas de los 30 cortes (mesa, §119)", "",
     "En el orden sellado (`orden_y_cortes_116_tanda_final.json`). **Tramo 1: cortes 1 a 10. Si ninguno de los 10 tiene un error de corte",
     "confirmado, la lectura para ahí** y el resto se declara con «0 de 10». Si alguno se confirma, se sigue con el tramo 2 (cortes 11 a 30).",
     "Sale solo el documento con un error de corte confirmado.", "",
     "**El criterio** es el de la lectura de cortes de S1 (`docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md:284-292`): la unidad es",
     "correcta si (1) empieza donde empieza su punto; (2) termina donde termina; (3) no trae texto de otro punto ni restos de encabezados o",
     "pies de página; (4) no le falta texto propio; y (5) su número es el del punto. Rigen las tres reglas de los casos dudosos y las dos",
     "clases de error, con su subclase. Se lee contra la página renderizada (`paginas/`, `pdftoppm -r 110`), no contra el texto.", "",
     "**Qué mira el patrón:** cada corte es el último ítem de una lista. El detector marca que después de su texto hay un párrafo que podría",
     "ser el cierre de la lista (del padre) y no del ítem. Si ese párrafo es del padre y la unidad lo trae, es un error de corte (termina",
     "fuera de su punto y trae texto de otro punto). Si es del ítem, la unidad es correcta. El «cierre candidato» es lo que marca el",
     "detector, no un juicio.", ""]
filas = []
for c in orden:
    to = c["doc"]; i = c["id"]
    cs = json.load(open(os.path.join(A.e0, f"chunks_{to}.json"), encoding="utf-8"))
    ids = [x["id"] for x in cs]; k = ids.index(i); u = cs[k]; sig = cs[k + 1] if k + 1 < len(cs) else None
    pdf = os.path.join(A.raiz_repo, m152[to]["pdf"])
    if sha(pdf) != m152[to]["sha256_pdf"]: sys.exit(f"FRENO: el PDF de {to} no da su sha256")
    pags = sorted(set(u["paginas"]) | ({sig["paginas"][0]} if sig else set()))
    for p in pags:
        base = os.path.join(A.out, "paginas", f"{to}_p{p}")
        if not os.path.exists(base + ".png"):
            subprocess.run(["pdftoppm", "-r", "110", "-f", str(p), "-l", str(p), "-png", "-singlefile", pdf, base], check=True)
    d = det[i]
    L += [f"## Corte {c['orden']} (tramo {c['tramo']}) — `{i}`", "",
          f"- documento: {to}; páginas de la unidad: {', '.join(map(str, u['paginas']))}; imágenes: " +
          ", ".join(f"`paginas/{to}_p{p}.png`" for p in pags),
          f"- tipo: {u['tipo']}; rol: {u.get('rol_bloque')}; caracteres propios: {u.get('chars_propio')}",
          f"- lista: hijos de `{d.get('padre')}`, {d.get('items')} ítems; cierre candidato del detector: «{d.get('cierre_candidato')}»",
          "- herencia:" + ("" if u["herencia"] else " (ninguna)")]
    L += [f"  - {t['tipo']}: «{t['texto'].replace(chr(10), ' / ')}»" for t in u["herencia"]]
    L += ["", "```text", u["texto"], "```", ""]
    if sig:
        L += [f"Contexto, la unidad que sigue en E0: `{sig['id']}` (páginas {', '.join(map(str, sig['paginas']))})", "", "```text",
              sig["texto"][:1500] + (" […]" if len(sig["texto"]) > 1500 else ""), "```", ""]
    filas.append([c["orden"], c["tramo"], to, i, "", "", "", "", "", ""])
open(os.path.join(A.out, "fichas_116_tanda_final.md"), "w", encoding="utf-8").write("\n".join(L))
with open(os.path.join(A.out, "planilla_116_tanda_final.tsv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t", lineterminator="\n")
    w.writerow(["orden", "tramo", "documento", "id", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota"])
    w.writerows(filas)
print(json.dumps({"cortes": len(filas), "paginas": len(os.listdir(os.path.join(A.out, "paginas")))}, ensure_ascii=False))
