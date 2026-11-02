"""cruce_control_36_B63.py — el cruce de la muestra de control de B6.3 (36 respuestas) con los juicios del juez (mesa, unidad C36_a,
29/10/2026). USD 0, sin API. Armado y probado con una lectura de juguete (`probar_cruce_control_36_B63.py`); no se corrió sobre la lectura
de la autora.

Es el de la mitad de verificación de Q8 (`data/experiment/ev2_juez/gold_q12_verificacion/cruce/cruce_gold_q12_verificacion_mesa.py`),
con lo que fija el pre-registro de B6.3 (§7.3, `docs/preregistro_B6_3_evaluacion_final.md:406-418`):
  - las cifras van por tipo (varios_puntos y dato_directo, de la clave), con el total al lado;
  - por criterio: el acuerdo del juez con la autora y su Wilson al 95 %. En varios puntos, el piso es un Wilson inferior de al menos
    0,85, sobre la cifra principal (todas las marcas adentro), comparado sin redondear; en dato directo se informa sin piso;
  - por respuesta: el acuerdo, sin umbral;
  - la columna «error fuera de los criterios», contada por brazo (y por tipo), aparte de las cifras de acuerdo;
  - el orden: primero el sello de la autora, sus planillas y su estructura (con el sha256 que anotó la mesa en copia_vacia/ antes de la
    lectura); la clave y los agregados del juez se leen recién después. Si el sello no da, frena sin haberlos abierto.
Del lado del juez, sus agregados de B6.3 (`banco_b63/juez/agregados_b63_ciego.json`), con el sha256 que fijó la clave del sorteo. Las dos
propuestas de la mitad de ajuste, como en Q8: un «dudoso» del juez (o un «sin_consenso») cuenta como desacuerdo, con la cifra sin esos
pares al lado; y la cifra sin «necesita experto del dominio» ni «criterio mal planteado», al lado de la principal. El criterio i de la
ficha es el i del juez: los dos siguen el orden del archivo de las preguntas (`armar_fichas_control_36_B63.py`, `enumerate(q["criterios"], 1)`;
`comun_b63.cargar_preguntas`).
No lee ni guarda la nota, el fragmento ni «cuál». Imprime solo cifras.
Uso: python3 -I -B cruce_control_36_B63.py <para_leer> <copia_vacia> <clave_control_36_B63.json> <agregados_b63_ciego.json> <salida.json>
"""
import csv
import hashlib
import io
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

PC, PR = "planilla_criterios_control_36_B63.csv", "planilla_respuestas_control_36_B63.csv"
SELLO, ESTRUCTURA = "sello_control_36_B63.txt", "estructura_planillas.json"
LISTA_MESA = "sha256_para_leer_control_36_B63.txt"
AGR = "banco_b63/juez/agregados_b63_ciego.json"
BRAZOS = ["kg", "fragmentos_hibrida", "fragmentos_denso"]
TIPOS = ["varios_puntos", "dato_directo"]
PISO_WILSON = {"varios_puntos": 0.85}
ORD = {"incorrecto": 0, "parcial": 1, "correcto": 2}
VALOR = {"cumplido": "cumplido", "no cumplido": "no_cumplido"}
SINO = {"": False, "no": False, "si": True}


def frena(m):
    raise SystemExit(f"FRENO: {m}")


def plegar(s):
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").replace("_", " ").split())


def leer(p: Path):
    t = p.read_bytes().decode("utf-8-sig")
    pr = t.splitlines()[0] if t else ""
    d = ";" if pr.count(";") > pr.count(",") else ","
    filas = [f for f in csv.reader(io.StringIO(t), delimiter=d) if any(x.strip() for x in f)]
    cols = [c.strip() for c in filas[0]]
    return cols, [dict(zip(cols, [c.strip() for c in f] + [""] * (len(cols) - len(f)))) for f in filas[1:]], d, t


def wilson(k, n, z=1.959964):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [(c - r) / d, (c + r) / d]


def w4(k, n):
    w = wilson(k, n)
    return None if w is None else [round(w[0], 4), round(w[1], 4)]


def veredicto(marcas):
    """La regla de EV2 (`ev2_juez/mapping.py:40-54`) sobre los criterios de la autora, que nunca son dudosos."""
    if all(m == "cumplido" for m in marcas):
        return "correcto"
    if all(m == "no_cumplido" for m in marcas):
        return "incorrecto"
    return "parcial"


def controlar_lectura(A: Path, CV: Path) -> dict:
    """El sello de la autora, sus dos planillas y su estructura, sin abrir la clave ni los juicios del juez."""
    if not (A / SELLO).is_file():
        frena("no hay sello de la autora")
    texto = (A / SELLO).read_text(encoding="utf-8")
    sello = [ln for ln in texto.splitlines() if ln and not ln.startswith("#")]
    sel = {ln.split()[-1]: (ln.split()[0], int(ln.split()[1])) for ln in sello}
    if sorted(sel) != sorted([PC, PR]) or len(sello) != 2:
        frena("el sello no trae las dos planillas")
    for n, (sha, b) in sel.items():
        x = (A / n).read_bytes()
        if hashlib.sha256(x).hexdigest() != sha or len(x) != b:
            frena(f"{n} no da el sha256 o los bytes de su sello")
    mesa = {ln.split(maxsplit=2)[2]: ln.split()[0] for ln in (CV / LISTA_MESA).read_text(encoding="utf-8").splitlines()
            if ln and not ln.startswith("#")}
    est_b = (A / ESTRUCTURA).read_bytes()
    if mesa.get(ESTRUCTURA) != hashlib.sha256(est_b).hexdigest():
        frena(f"{ESTRUCTURA} no es la que anotó la mesa antes de la lectura")
    est = json.loads(est_b.decode("utf-8"))
    cab, crit, d_c, t_c = leer(A / PC)
    cab_r, filas_r, d_r, t_r = leer(A / PR)
    if cab != est["criterios"]["columnas"] or cab_r != est["respuestas"]["columnas"]:
        frena("las columnas no son las de la plantilla")
    if [[c["ficha"], c["criterio"]] for c in crit] != est["criterios"]["renglones"]:
        frena("los renglones de criterios no son los de la plantilla")
    if [[r["ficha"]] for r in filas_r] != est["respuestas"]["renglones"]:
        frena("los renglones de respuestas no son los de la plantilla")
    VER, DUD, EXP, MAL = cab[2], cab[4], cab[5], cab[6]
    CLAS, ERR, CUAL, MIN = cab_r[1], cab_r[2], cab_r[3], cab_r[4]
    salio = all(not r[ERR].strip() and not r[CUAL].strip() for r in filas_r)
    if salio != ("salió, declarada" in texto):
        frena("el sello y la planilla no dicen lo mismo sobre la columna de error fuera de los criterios")
    for c in crit:
        if plegar(c[VER]) not in VALOR or not all(plegar(c[k]) in SINO for k in (DUD, EXP, MAL)):
            frena(f"{c['ficha']}-{c['criterio']}: un valor fuera de la plantilla")
    for r in filas_r:
        if plegar(r[CLAS]) not in ("abstencion", "contenido") or (not salio and plegar(r[ERR]) not in ("si", "no")):
            frena(f"{r['ficha']}: un valor fuera de la plantilla")
    canon = {VER: {"cumplido", "no_cumplido"}, DUD: {"sí", "no", ""}, EXP: {"sí", "no", ""}, MAL: {"sí", "no", ""},
             CLAS: {"abstencion", "contenido"}, ERR: {"sí", "no"} | ({""} if salio else set())}
    crudo = {n: [f for f in csv.reader(io.StringIO(t), delimiter=d) if any(x.strip() for x in f)][1:]
             for n, t, d in ((PC, t_c, d_c), (PR, t_r, d_r))}
    formato = {"delimitador": {PC: d_c, PR: d_r},
               "bom": {n: (A / n).read_bytes().startswith(b"\xef\xbb\xbf") for n in (PC, PR)},
               "celdas_con_otra_forma_leidas_igual": {k: sum(f[k] not in v for f in (crit if k in (VER, DUD, EXP, MAL) else filas_r))
                                                      for k, v in canon.items()},
               "celdas_con_espacios_de_mas": {PC: sum(f[i] != f[i].strip() for f in crudo[PC] for i in (0, 1, 2, 4, 5, 6) if i < len(f)),
                                              PR: sum(f[i] != f[i].strip() for f in crudo[PR] for i in (0, 1, 2, 4) if i < len(f))}}
    return {"sel": sel, "est_sha": mesa[ESTRUCTURA], "crit": crit, "filas_r": filas_r, "cols": (VER, DUD, EXP, MAL, CLAS, ERR, MIN),
            "salio": salio, "formato": formato}


def cifras_criterio(ps):
    n = len(ps)
    acu = sum(p["juez"] == p["autora"] for p in ps)
    dud = [p for p in ps if p["juez"] in ("dudoso", "sin_consenso")]
    A_ = [p["par"] for p in ps if p["juez"] == "cumplido" and p["autora"] == "no_cumplido"]
    B_ = [p["par"] for p in ps if p["juez"] == "no_cumplido" and p["autora"] == "cumplido"]
    sin_d = [p for p in ps if p not in dud]
    k2 = sum(p["juez"] == p["autora"] for p in sin_d)
    w = wilson(acu, n)
    return {"n": n, "acuerdo": acu, "fraccion": round(acu / n, 4) if n else None, "wilson95": w4(acu, n),
            "wilson_inferior_sin_redondear": None if w is None else w[0],
            "direccion_A_juez_acredita": len(A_), "pares_A": A_, "direccion_B_juez_no_acredita": len(B_), "pares_B": B_,
            "dudoso_del_juez": len(dud), "pares_dudoso_del_juez": [p["par"] for p in dud],
            "sin_dudosos_del_juez": {"n": len(sin_d), "acuerdo": k2, "fraccion": round(k2 / len(sin_d), 4) if sin_d else None,
                                     "wilson95": w4(k2, len(sin_d))}}


def cifras_respuesta(rs):
    n = len(rs)
    acu = sum(r["juez"] == r["autora"] for r in rs)
    adj = [r["ficha"] for r in rs if r["juez"] == "requiere_adjudicacion"]
    A_ = [r["ficha"] for r in rs if r["juez"] in ORD and ORD[r["juez"]] > ORD[r["autora"]]]
    B_ = [r["ficha"] for r in rs if r["juez"] in ORD and ORD[r["juez"]] < ORD[r["autora"]]]
    return {"n": n, "acuerdo": acu, "fraccion": round(acu / n, 4) if n else None, "wilson95": w4(acu, n),
            "direccion_A_juez_mas_favorable": len(A_), "fichas_A": A_, "direccion_B_juez_menos_favorable": len(B_), "fichas_B": B_,
            "requiere_adjudicacion": len(adj), "fichas_requiere_adjudicacion": adj}


def clasificacion(rs):
    return {"n": len(rs), "acuerdo": sum(r["clas_juez"] == r["clas_autora"] for r in rs),
            "desacuerdos": [r["ficha"] for r in rs if r["clas_juez"] != r["clas_autora"]]}


def minutos(s):
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(?:min|minutos|')?", s.strip().lower())
    return float(m.group(1).replace(",", ".")) if m else None


def cruzar(L: dict, clave_d: dict, agr_d: dict) -> dict:
    crit, filas_r = L["crit"], L["filas_r"]
    VER, DUD, EXP, MAL, CLAS, ERR, MIN = L["cols"]
    resp = {r["ficha"]: r for r in filas_r}
    agr = {x["id_opaco"]: x for x in agr_d["agregados"]}
    clave = clave_d["fichas"]
    if [f["ficha"] for f in clave] != [r["ficha"] for r in filas_r]:
        frena("las fichas de la clave no son las de la planilla de respuestas")
    pares, respuestas = [], []
    for f in clave:
        a = agr.get(f["id_opaco"])
        if a is None:
            frena(f"{f['ficha']}: su id opaco no está en los agregados del juez")
        if not (a["n_criterios"] == f["n_criterios"] == len(a["modales"])):
            frena(f"{f['ficha']}: el número de criterios del juez no es el de la clave")
        mias = [c for c in crit if c["ficha"] == f["ficha"]]
        if [int(c["criterio"]) for c in mias] != list(range(1, f["n_criterios"] + 1)):
            frena(f"{f['ficha']}: los criterios de la planilla no son los de la clave")
        ps = [{"par": f"{f['ficha']}-{c['criterio']}", "ficha": f["ficha"], "tipo": f["tipo"], "brazo": f["brazo"], "juez": j,
               "autora": VALOR[plegar(c[VER])], "dudosa": SINO[plegar(c[DUD])], "experto": SINO[plegar(c[EXP])],
               "mal_planteado": SINO[plegar(c[MAL])]} for c, j in zip(mias, a["modales"])]
        pares += ps
        r = resp[f["ficha"]]
        respuestas.append({"ficha": f["ficha"], "tipo": f["tipo"], "brazo": f["brazo"], "juez": a["veredicto_pregunta"],
                           "autora": veredicto([p["autora"] for p in ps]), "clas_juez": a["clasificacion_respuesta_modal"],
                           "clas_autora": plegar(r[CLAS]), "error_fuera": None if L["salio"] else plegar(r[ERR]) == "si",
                           "clase_del_sorteo": f["clase"], "to": f["to"]})
    por_tipo = {}
    for t in TIPOS + ["total"]:
        ps = [p for p in pares if t == "total" or p["tipo"] == t]
        rs = [r for r in respuestas if t == "total" or r["tipo"] == t]
        x = {"criterio": cifras_criterio(ps),
             "criterio_sin_experto_ni_mal_planteado": cifras_criterio([p for p in ps if not p["experto"] and not p["mal_planteado"]]),
             "respuesta": cifras_respuesta(rs), "clasificacion_abstencion_contenido": clasificacion(rs)}
        if t in PISO_WILSON:
            wi = x["criterio"]["wilson_inferior_sin_redondear"]
            x["piso"] = {"wilson_inferior": None if wi is None else round(wi, 4), "piso": PISO_WILSON[t],
                         "llega": wi is not None and wi >= PISO_WILSON[t]}
        por_tipo[t] = x
    if L["salio"]:
        err = {"salio_declarada": True}
    else:
        err = {"salio_declarada": False, "n": sum(r["error_fuera"] for r in respuestas),
               "fichas": [r["ficha"] for r in respuestas if r["error_fuera"]],
               "por_brazo": {b: {"n": sum(r["error_fuera"] for r in respuestas if r["brazo"] == b),
                                 "de": sum(1 for r in respuestas if r["brazo"] == b),
                                 "fichas": [r["ficha"] for r in respuestas if r["brazo"] == b and r["error_fuera"]]} for b in BRAZOS},
               "por_tipo": {t: {"n": sum(r["error_fuera"] for r in respuestas if r["tipo"] == t),
                                "de": sum(1 for r in respuestas if r["tipo"] == t)} for t in TIPOS}}
    mins = [minutos(r[MIN]) for r in filas_r]
    return {"por_tipo": por_tipo, "errores_fuera_de_los_criterios": err,
            "marcas_de_la_autora": {"dudosa": [p["par"] for p in pares if p["dudosa"]], "experto": [p["par"] for p in pares if p["experto"]],
                                    "mal_planteado": [p["par"] for p in pares if p["mal_planteado"]]},
            "minutos": {"con_numero": sum(v is not None for v in mins), "vacios": sum(not r[MIN].strip() for r in filas_r),
                        "sin_numero_legible": sum(v is None and bool(r[MIN].strip()) for r, v in zip(filas_r, mins)),
                        "total": round(sum(v for v in mins if v is not None), 1)},
            "marcas_de_la_autora_por_criterio": dict(Counter(p["autora"] for p in pares)),
            "veredictos_de_la_autora_por_respuesta": dict(Counter(r["autora"] for r in respuestas)),
            "clasificacion_de_la_autora": dict(Counter(r["clas_autora"] for r in respuestas)),
            "veredictos_del_juez_por_respuesta": dict(Counter(r["juez"] for r in respuestas)),
            "modales_del_juez_por_criterio": dict(Counter(p["juez"] for p in pares)),
            "pares": pares, "respuestas": respuestas}


def imprimir(out: dict) -> None:
    for t in TIPOS + ["total"]:
        x = out["por_tipo"][t]
        c, s, r = x["criterio"], x["criterio_sin_experto_ni_mal_planteado"], x["respuesta"]
        print(f"{t}, por criterio ({c['n']}): {c['acuerdo']} de {c['n']} ({c['fraccion']}; Wilson {c['wilson95']}); "
              f"A {c['direccion_A_juez_acredita']} {c['pares_A']}, B {c['direccion_B_juez_no_acredita']} {c['pares_B']}, "
              f"dudoso del juez {c['dudoso_del_juez']}")
        print(f"  sin experto ni mal planteado: {s['acuerdo']} de {s['n']} ({s['fraccion']}; Wilson {s['wilson95']})")
        if "piso" in x:
            print(f"  piso: Wilson inferior {x['piso']['wilson_inferior']} (>= {x['piso']['piso']}: {x['piso']['llega']})")
        print(f"{t}, por respuesta ({r['n']}, sin umbral): {r['acuerdo']} de {r['n']} ({r['fraccion']}; Wilson {r['wilson95']}); "
              f"A {r['direccion_A_juez_mas_favorable']} {r['fichas_A']}, B {r['direccion_B_juez_menos_favorable']} {r['fichas_B']}")
        k = x["clasificacion_abstencion_contenido"]
        print(f"  abstención o contenido: {k['acuerdo']} de {k['n']} {k['desacuerdos']}")
    e = out["errores_fuera_de_los_criterios"]
    if e["salio_declarada"]:
        print("error fuera de los criterios: la columna salió, declarada")
    else:
        por_b = {b: f"{v['n']} de {v['de']}" for b, v in e["por_brazo"].items()}
        por_t = {t: f"{v['n']} de {v['de']}" for t, v in e["por_tipo"].items()}
        print(f"error fuera de los criterios: {e['n']} de 36 {e['fichas']}; por brazo {por_b}; por tipo {por_t}")
    print(f"aparte: marcas {json.dumps(out['marcas_de_la_autora'], ensure_ascii=False)}; minutos {out['minutos']}")
    print(f"formato: {json.dumps(out['formato_de_las_planillas'], ensure_ascii=False)}")


def main(argv: list) -> int:
    A, CV, CLAVE, AGR_P, OUT = (Path(x) for x in argv)
    L = controlar_lectura(A, CV)                       # 1. el sello y las planillas, antes que nada
    clave_b = CLAVE.read_bytes()                       # 2. recién ahora, la clave y los juicios del juez
    clave_d = json.loads(clave_b.decode("utf-8"))
    agr_b = AGR_P.read_bytes()
    if hashlib.sha256(agr_b).hexdigest() != clave_d["sha256_entradas"][AGR]:
        frena("los agregados del juez no son los del sorteo")
    out = {"insumos": {"sello": {n: s for n, (s, _) in L["sel"].items()}, "estructura_sha256": L["est_sha"],
                       "clave_sha256": hashlib.sha256(clave_b).hexdigest(), "agregados_sha256": hashlib.sha256(agr_b).hexdigest()},
           "formato_de_las_planillas": L["formato"]} | cruzar(L, clave_d, json.loads(agr_b.decode("utf-8")))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    imprimir(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
