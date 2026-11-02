"""Mesa, §145 (17/10/2026): el control de las tres lecturas de la autora del 17/10 contra el material de la mesa y contra sus sellos. USD 0.
Lee copias de sus archivos (nunca los originales) y las plantillas del paquete. No escribe nada fuera de <salida>.

Controla, en cada lectura:
  1. el sha256 de cada archivo, contra el sello de la autora;
  2. la plantilla: la misma cabecera, la misma cantidad de filas y las columnas fijas iguales, fila por fila;
  3. las marcas: los códigos válidos de la regla de lectura (sub-documento y 1.16: los de S1-quater, `cifras_lectura_S1quater.py:16-17`,
     `:45-46` y `:85-97`, en el paquete `decisiones_93_mesa/para_el_repo/adjudicacion/`, igual al de HEAD por su blob `0995ecfb`; el
     gold: los de `regla_de_lectura_gold_q12_ajuste.md`);
  4. la exportación de Numbers (con punto y coma) contra el archivo sellado: el mismo contenido, celda por celda;
  5. las cuentas: lo que da cada lectura.
Uso: python3 -I -B controlar_lecturas_1710_mesa.py <carpeta con las copias de la autora> <paquete H> <salida.json>"""
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

A, H, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
SUB_CORTE = {"empieza_fuera", "termina_fuera", "falta_texto_propio", "trae_texto_de_otro_punto", "numero_equivocado"}
SUB_LIMPIEZA = {"restos_encabezado", "restos_pie"}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
res, fallas, obs = {}, [], []


def leer(p, delim):
    t = p.read_text(encoding="utf-8-sig")
    return list(csv.reader(io.StringIO(t), delimiter=delim))


def sello(p):
    filas = [l.split() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {f[1]: f[0] for f in filas if len(f) == 2 and len(f[0]) == 64}, filas[-1]


def ok(cond, que):
    if not cond:
        fallas.append(que)
    return cond


def marcas_segmentacion(filas, cab, nombre, solo=None):
    i = {c: cab.index(c) for c in cab}
    err = []
    for k, f in enumerate(filas):
        if solo and not solo(f, i):
            if any(f[i[c]] for c in ("marca", "clase", "subclase", "subclase_adicional", "limpieza")):
                err.append(f"fila {k + 1}: marcada fuera del tramo que se lee")
            continue
        m, cl, sc, sa, li = (f[i[c]].strip() for c in ("marca", "clase", "subclase", "subclase_adicional", "limpieza"))
        if m not in ("correcta", "error", "dudosa"):
            err.append(f"fila {k + 1}: marca «{m}»")
        if m == "error":
            subs = {s for s in (sc, sa) if s}
            validas = SUB_CORTE if cl == "corte" else SUB_LIMPIEZA
            if cl not in ("corte", "limpieza") or not subs or not subs <= (SUB_CORTE | SUB_LIMPIEZA) or sc not in validas:
                err.append(f"fila {k + 1}: clase o subclase («{cl}», «{sc}», «{sa}»)")
        if li and li not in SUB_LIMPIEZA:
            err.append(f"fila {k + 1}: limpieza «{li}»")
    ok(not err, f"{nombre}: marcas inválidas: {err}")
    return err


# --- sub-documento de la tanda 1 ---
plant = leer(H / "decisiones_118_mesa/lectura_subdocumento_tanda1/material/planilla_subdocumento_tanda1.tsv", "\t")
p_sub = A / "lecturas_1710/planilla_subdocumento_tanda1.tsv"
aut = leer(p_sub, "\t")
s, hora = sello(A / "lecturas_1710/sello_planilla_subdocumento_tanda1.txt")
cab = plant[0]
FIJAS = cab[:cab.index("unidad_leida")]
ok(s.get(p_sub.name) == sha(p_sub), "sub-documento: el sha256 de la planilla no es el del sello")
ok(s.get("planilla_subdocumento_tanda1_puntoycoma.csv") == sha(A / "lecturas_1710/planilla_subdocumento_tanda1_puntoycoma.csv"),
   "sub-documento: el sha256 de la exportación no es el del sello")
ok(aut[0] == cab, "sub-documento: la cabecera cambió")
ok(len(aut) == len(plant) == 15, f"sub-documento: filas {len(aut) - 1} (plantilla {len(plant) - 1})")
fijas_ok = all(a[:len(FIJAS)] == p[:len(FIJAS)] for a, p in zip(aut[1:], plant[1:]))
ok(fijas_ok, "sub-documento: alguna columna fija cambió")
exp = leer(A / "lecturas_1710/planilla_subdocumento_tanda1_puntoycoma.csv", ";")
ok(exp == aut, "sub-documento: la exportación no tiene el mismo contenido que la planilla sellada")
i = {c: cab.index(c) for c in cab}
unidad_ok = all(f[i["unidad_leida"]] in f[i["unidades_de_la_pagina"]].split() for f in aut[1:])
ok(unidad_ok, "sub-documento: alguna unidad_leida no está entre las unidades de la página")
marcas_segmentacion(aut[1:], cab, "sub-documento")
cuenta = Counter(f[i["marca"]] for f in aut[1:])
cortes = [f[i["fila"]] for f in aut[1:] if f[i["marca"]] == "error" and f[i["clase"]] == "corte"]
dudosas = [f[i["fila"]] for f in aut[1:] if f[i["marca"]] == "dudosa"]
res["subdocumento_tanda1"] = {"sha256": sha(p_sub), "sello": " ".join(hora), "filas": len(aut) - 1, "columnas_fijas_iguales": fijas_ok,
                              "exportacion_igual": exp == aut, "marcas": dict(cuenta), "errores_de_corte": cortes, "dudosas": dudosas,
                              "unidades_leidas": sorted({f[i["unidad_leida"]] for f in aut[1:]}),
                              "rasgo_confirmado": bool(cortes)}

# --- 1.16 en la tanda final, cortes 1 a 10 ---
plant = leer(H / "decisiones_119_mesa/lectura_116_tanda_final/material/planilla_116_tanda_final.tsv", "\t")
p116 = A / "lecturas_1710/planilla_116_tanda_final.tsv"
aut = leer(p116, "\t")
s3, hora3 = sello(A / "lecturas_1710/sello_planilla_116_tanda_final_v3.txt")
s1, hora1 = sello(A / "lecturas_1710/sello_planilla_116_tanda_final_v1_plantilla_vacia.txt")
s2, hora2 = sello(A / "lecturas_1710/sello_planilla_116_tanda_final_v2_plantilla_vacia.txt")
cab = plant[0]
FIJAS = cab[:cab.index("marca")]
ok(s3.get(p116.name) == sha(p116), "1.16: el sha256 de la planilla no es el del sello v3")
ok(s3.get("planilla_116_tanda_final_puntoycoma.csv") == sha(A / "lecturas_1710/planilla_116_tanda_final_puntoycoma.csv"),
   "1.16: el sha256 de la exportación no es el del sello v3")
vacia = sha(H / "decisiones_119_mesa/lectura_116_tanda_final/material/planilla_116_tanda_final.tsv")
v12 = s1.get("planilla_116_tanda_final.tsv") == s2.get("planilla_116_tanda_final.tsv") == vacia
ok(v12, "1.16: los sellos v1 y v2 no son los de la plantilla vacía de la mesa")
ok(aut[0] == cab, "1.16: la cabecera cambió")
ok(len(aut) == len(plant) == 31, f"1.16: filas {len(aut) - 1} (plantilla {len(plant) - 1})")
fijas_ok = all(a[:len(FIJAS)] == p[:len(FIJAS)] for a, p in zip(aut[1:], plant[1:]))
ok(fijas_ok, "1.16: alguna columna fija cambió")
exp = leer(A / "lecturas_1710/planilla_116_tanda_final_puntoycoma.csv", ";")
ok(exp == aut, "1.16: la exportación no tiene el mismo contenido que la planilla sellada")
i = {c: cab.index(c) for c in cab}
marcas_segmentacion(aut[1:], cab, "1.16", solo=lambda f, i: f[i["tramo"]] == "1")
t1 = [f for f in aut[1:] if f[i["tramo"]] == "1"]
cortes = [f[i["orden"]] for f in t1 if f[i["marca"]] == "error" and f[i["clase"]] == "corte"]
dud_corte = [f[i["orden"]] for f in t1 if f[i["marca"]] == "dudosa"]
res["116_tanda_final"] = {"sha256": sha(p116), "sello_v3": " ".join(hora3), "sellos_v1_y_v2": [" ".join(hora1), " ".join(hora2)],
                          "v1_y_v2_sellaron_la_plantilla_vacia": v12, "sha256_plantilla_vacia": vacia,
                          "exportacion_primera_de_v1_y_v2": s1.get("planilla_116_tanda_final_puntoycoma.csv"),
                          "filas": len(aut) - 1, "columnas_fijas_iguales": fijas_ok, "exportacion_igual": exp == aut,
                          "leidos_tramo_1": len(t1), "marcas_tramo_1": dict(Counter(f[i["marca"]] for f in t1)),
                          "tramo_2_vacio": all(not f[i["marca"]] for f in aut[1:] if f[i["tramo"]] == "2"),
                          "errores_de_corte": cortes, "dudosas": dud_corte, "rama": 0 if not cortes and not dud_corte else 1,
                          "documentos_tramo_1": [f[i["documento"]] for f in t1]}

# --- gold de Q12, mitad de ajuste ---
P = H / "decisiones_128_mesa/gold/para_leer"
sg, horag = sello(A / "gold/sello_gold_q12_ajuste.txt")
g = {}
for nombre, n in (("planilla_criterios_gold_q12_ajuste", 82), ("planilla_respuestas_gold_q12_ajuste", 20)):
    plant = leer(P / f"{nombre}.csv", ",")
    pa = A / f"gold/{nombre}.csv"
    aut = leer(pa, ",")
    exp = leer(A / f"gold/{nombre}_puntoycoma.csv", ";")
    nf = 2 if "criterios" in nombre else 1
    ok(sg.get(pa.name) == sha(pa), f"gold: el sha256 de {pa.name} no es el del sello")
    ok(sg.get(f"{nombre}_puntoycoma.csv") == sha(A / f"gold/{nombre}_puntoycoma.csv"), f"gold: el sha256 de la exportación de {nombre}")
    ok(aut[0] == plant[0], f"gold: la cabecera de {nombre} cambió")
    ok(len(aut) - 1 == len(plant) - 1 == n, f"gold: {nombre} tiene {len(aut) - 1} filas")
    fijas_ok = all(a[:nf] == p[:nf] for a, p in zip(aut[1:], plant[1:]))
    ok(fijas_ok, f"gold: alguna columna fija de {nombre} cambió")
    ok(exp == aut, f"gold: la exportación de {nombre} no tiene el mismo contenido")
    g[nombre] = {"sha256": sha(pa), "filas": len(aut) - 1, "columnas_fijas_iguales": fijas_ok, "exportacion_igual": exp == aut,
                 "cabecera": aut[0], "filas_datos": aut[1:]}
cc = g["planilla_criterios_gold_q12_ajuste"]
cab = cc["cabecera"]
VER, DUD, EXP, MAL = cab[2], cab[4], cab[5], cab[6]
ix = {c: cab.index(c) for c in cab}
norm = lambda x: {"sí": "si"}.get(x.strip(), x.strip())  # noqa: E731
mal = [f"{f[0]}-{f[1]}" for f in cc["filas_datos"] if f[ix[VER]] not in ("cumplido", "no_cumplido")]
ok(not mal, f"gold: veredictos inválidos {mal}")
for col in (DUD, EXP, MAL):
    raros = [f"{f[0]}-{f[1]}: «{f[ix[col]]}»" for f in cc["filas_datos"] if norm(f[ix[col]]) not in ("si", "no")]
    ok(not raros, f"gold: «{col}» con valores fuera de sí/no: {raros}")
    sin_norma = [f"{f[0]}-{f[1]}: «{f[ix[col]]}»" for f in cc["filas_datos"] if f[ix[col]] not in ("si", "no", "sí")]
    if sin_norma:
        obs.append(f"gold, «{col}»: {len(sin_norma)} valor(es) con un espacio de más ({sin_norma}); lo leo como «no», sin tocar la planilla")
rr = g["planilla_respuestas_gold_q12_ajuste"]
cabr = rr["cabecera"]
ir = {c: cabr.index(c) for c in cabr}
clas = Counter(f[ir[cabr[1]]] for f in rr["filas_datos"])
ok(set(clas) <= {"abstencion", "abstención", "contenido"}, f"gold: clasificación fuera de los códigos: {dict(clas)}")
if "abstención" in clas:
    obs.append(f"gold: la clasificación usa «abstención» con tilde ({clas['abstención']} veces); el código de la plantilla es «abstencion». Lo leo igual")
if all(not f[ir["minutos"]] for f in rr["filas_datos"]):
    obs.append("gold: la columna «minutos» está vacía en las 20; el tiempo total lo dio la autora en su mensaje (unas 1 h 25 min)")
if any(f[ix[DUD]] == "si" for f in cc["filas_datos"]) or any(f[ix[MAL]] == "si" for f in cc["filas_datos"]):
    obs.append("gold: «sí» va escrito «si», sin tilde; lo leo igual")
res["gold_q12_ajuste"] = {
    "sello": " ".join(horag),
    "planillas": {k: {x: v[x] for x in ("sha256", "filas", "columnas_fijas_iguales", "exportacion_igual")} for k, v in g.items()},
    "veredictos": dict(Counter(f[ix[VER]] for f in cc["filas_datos"])),
    "dudosa": sum(norm(f[ix[DUD]]) == "si" for f in cc["filas_datos"]),
    "experto": sum(norm(f[ix[EXP]]) == "si" for f in cc["filas_datos"]),
    "mal_planteado": sum(norm(f[ix[MAL]]) == "si" for f in cc["filas_datos"]),
    "clasificacion": dict(clas),
    "error_fuera_de_los_criterios": dict(Counter(norm(f[ir[cabr[2]]]) for f in rr["filas_datos"])),
}
res["fallas"], res["observaciones"] = fallas, obs
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for k in ("subdocumento_tanda1", "116_tanda_final", "gold_q12_ajuste"):
    print(k, json.dumps({x: y for x, y in res[k].items() if x not in ("planillas",)}, ensure_ascii=False)[:900])
print("observaciones:", *obs, sep="\n  ")
print("FALLAS:", len(fallas), *fallas, sep="\n  ")
sys.exit(1 if fallas else 0)
