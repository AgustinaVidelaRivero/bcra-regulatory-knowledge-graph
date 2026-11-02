"""Mesa, §118: fichas y planilla vacía para la lectura de los 14 límites de sub-documento de la tanda 1 que la regla no aplica
(decisión 1 de la autora del 16/10/2026). USD 0, sin API. No marca nada.

Uso: python3 -I -B <este> --censo <censo_sd_152_S2b.json> --e0 <E0 corregida> --manifiesto-e0 <manifest_salida_e0_152_S0-6b.json>
       --manifiesto-152 <segmentacion_oficial_e0r2_152.json> --raiz-repo <copia del repo> --out <carpeta>

Controla antes de escribir: el censo por su sha256 canónico (claves ordenadas), los 768 archivos de la E0 contra su manifiesto y
cada PDF contra el sha256 del manifiesto de los 152. Escribe en --out:
- fichas_subdocumento_tanda1.md: una ficha por unidad de E0 que contiene uno o más de los 14 límites (las unidades de la página
  del límite), con sus páginas, tipo, rol, caracteres, herencia y texto propio tal como salen de E0, y los límites que caen en ella;
- planilla_subdocumento_tanda1.tsv: una fila por límite, con las columnas de la lectura de S1-bis vacías;
- paginas/<to>_p<n>.png: las páginas de cada unidad mostrada (pdftoppm -r 110, como en S1-bis)."""
import argparse, csv, hashlib, json, os, subprocess, sys
ap = argparse.ArgumentParser()
for a in ("--censo", "--e0", "--manifiesto-e0", "--manifiesto-152", "--raiz-repo", "--out"):
    ap.add_argument(a, required=True)
A = ap.parse_args()
TOS = ("ri_rml", "ri_gerc", "ri_pgn", "snp_tr", "manori")   # los 5 de la tanda 1 con límites fuera de la lista (censos_S2b.json)
CANONICO = "899db5d198d18d8cff53b3aca5f77e464ab6e61ce9e29d5a2c7dc46ca59acf13"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
censo = json.load(open(A.censo, encoding="utf-8"))
if hashlib.sha256(json.dumps(censo, sort_keys=True, ensure_ascii=False).encode()).hexdigest() != CANONICO:
    sys.exit("FRENO: el censo no da su sha256 canónico")
me0 = json.load(open(A.manifiesto_e0, encoding="utf-8"))["sha256"]
mal = [k for k, v in me0.items() if k.startswith("e0/") and sha(os.path.join(A.e0, k[3:])) != v["sha256"]]
if mal: sys.exit(f"FRENO: {len(mal)} archivos de la E0 no dan su sha256")
m152 = {t["id"]: t for t in json.load(open(A.manifiesto_152, encoding="utf-8"))["tos"]}
for to in TOS:
    if sha(os.path.join(A.raiz_repo, m152[to]["pdf"])) != m152[to]["sha256_pdf"]:
        sys.exit(f"FRENO: el PDF de {to} no da su sha256")
limites = [(to, x) for to in TOS for x in censo["por_to"][to]]
if len(limites) != 14 or censo["lista"] != ["nmcief", "ri_cc", "ri_ccna", "ri_icpipsp", "ri_sef"]:
    sys.exit(f"FRENO: esperaba 14 límites fuera de la lista y la lista de la regla de S2; hay {len(limites)}")
os.makedirs(os.path.join(A.out, "paginas"), exist_ok=True)
unidades, por_unidad, filas = {}, {}, []
for i, (to, x) in enumerate(limites, 1):
    cs = json.load(open(os.path.join(A.e0, f"chunks_{to}.json"), encoding="utf-8"))
    en_pagina = [c for c in cs if x["pagina"] in c["paginas"]]
    for c in en_pagina:
        unidades[c["id"]] = c
        por_unidad.setdefault(c["id"], []).append(i)
    filas.append({"fila": i, "to": to, "pagina": x["pagina"], "top_pt": x["top"], "forma": x["forma"], "prefijo": x["prefijo"],
                  "titulo_detectado": x["titulo"], "unidades_de_la_pagina": " ".join(c["id"] for c in en_pagina)})
paginas = sorted({(c["to"], p) for c in unidades.values() for p in c["paginas"]})
for to, p in paginas:
    base = os.path.join(A.out, "paginas", f"{to}_p{p}")
    subprocess.run(["pdftoppm", "-r", "110", "-f", str(p), "-l", str(p), "-png", "-singlefile",
                    os.path.join(A.raiz_repo, m152[to]["pdf"]), base], check=True)
L = ["# Lectura de los 14 límites de sub-documento de la tanda 1: fichas (mesa, §118)", "",
     "Qué se lee: en cada página, el límite que detecta `limites_subdocumento` y que E0 no aplica en estos cinco documentos, porque no",
     "están en la lista de la regla (`censo_sd_152_S2b.json`, `899db5d1…`, con las claves ordenadas). Las unidades se leen contra la página",
     "renderizada (`paginas/`, `pdftoppm -r 110`), no contra el texto que extrae la librería.", "",
     "**El criterio** es el de la lectura de cortes de S1 (`docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md:284-292`), el mismo de S1-bis.",
     "Una unidad es correcta si: (1) empieza donde empieza su punto; (2) termina donde termina; (3) no trae texto de otro punto ni restos",
     "de encabezados o pies de página; (4) no le falta texto propio; y (5) su número es el del punto. Rigen las tres reglas de los casos",
     "dudosos y las dos clases de error, con su subclase.", "",
     "**La pregunta de cada fila de la planilla:** con ese límite, ¿la unidad de E0 que lo contiene cumple el criterio? Si el límite abre de",
     "verdad un sub-documento y la unidad lo atraviesa, es un error de corte (termina fuera de su punto o trae texto de otro punto). Si el",
     "límite no abre nada (un encabezado de página, el renglón de una tabla o de un formulario) y la unidad está bien, es correcta.", "",
     "La posición del límite: `top` en puntos desde el borde de arriba de la página; en la imagen, a unos `top × 110 / 72` píxeles.",
     "Las marcas van en `planilla_subdocumento_tanda1.tsv`, una fila por límite.", ""]
for uid, c in unidades.items():
    fs = por_unidad[uid]
    L += [f"## `{uid}`", "",
          f"- TO: {c['to']}; páginas: {', '.join(map(str, c['paginas']))} (" +
          ", ".join(f"`paginas/{c['to']}_p{p}.png`" for p in c["paginas"]) + ")",
          f"- tipo: {c['tipo']}; rol: {c.get('rol_bloque')}; caracteres propios: {c.get('chars_propio')}",
          "- límites en sus páginas (filas de la planilla):"]
    for i in fs:
        f = filas[i - 1]
        L.append(f"  - fila {i}: p. {f['pagina']}, top {f['top_pt']} pt (≈ {round(f['top_pt'] * 110 / 72)} px), forma {f['forma']}, "
                 f"«{f['titulo_detectado']}»")
    L.append("- herencia:" + ("" if c["herencia"] else " (ninguna)"))
    L += [f"  - {t['tipo']}: «{t['texto'].replace(chr(10), ' / ')}»" for t in c["herencia"]]
    L += ["", "```text", c["texto"], "```", ""]
open(os.path.join(A.out, "fichas_subdocumento_tanda1.md"), "w", encoding="utf-8").write("\n".join(L))
COL = ("fila", "to", "pagina", "top_pt", "forma", "prefijo", "titulo_detectado", "unidades_de_la_pagina", "unidad_leida", "marca",
       "clase", "subclase", "subclase_adicional", "limpieza", "nota")
with open(os.path.join(A.out, "planilla_subdocumento_tanda1.tsv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter="\t", lineterminator="\n")
    w.writerow(COL)
    for f in filas:
        w.writerow([f.get(k, "") for k in COL])
print(json.dumps({"limites": len(filas), "unidades": len(unidades), "paginas": len(paginas)}, ensure_ascii=False))
