"""probar_sorteo_control_36_B63.py — la prueba con datos de juguete del sorteo de la muestra de control de B6.3, antes de su sello (mesa,
unidad C36_a, 29/10/2026). Corre la regla entera, `poblacion` y `sortear` del script, con el código del juez de B6.3 importado sin
editarlo (`id_opaco`, `sha256_texto`, `marcas_d10` y `contar_d10` de `juez_b63.py`), sobre una población inventada: 48 preguntas (30 de
varios puntos y 18 de dato directo), tres brazos y k = 3, con sesiones `incompleta_otra`, respuestas con error del juez en una o en sus
tres repeticiones y `requiere_adjudicacion`. Ningún dato real. Imprime OK o MAL por caso y, al final, el sha256 de la clave de juguete de
la base, para comparar dos corridas byte a byte. USD 0.
  python3 -I -B probar_sorteo_control_36_B63.py <repo>
"""
import copy
import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("S", Path(__file__).with_name("sortear_control_36_B63.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
JB = S.cargar_juez(Path(sys.argv[1]).resolve())
TOS = ["to_a", "to_b", "to_c", "to_d", "to_e"]
QV = [f"QV{i:02d}" for i in range(30)]
QD = [f"QD{i:02d}" for i in range(18)]
PREG = ({q: {"tipo": "varios_puntos", "to": TOS[i % 5], "n_criterios": 3 + i % 3} for i, q in enumerate(QV)}
        | {q: {"tipo": "dato_directo", "to": TOS[i % 5], "n_criterios": 1 + i % 2} for i, q in enumerate(QD)})
FRAG = {"tools_esperadas": ["mcp__fragmentos__buscar_pasajes"]}
E_JUGUETE = {"_cfg": {"brazos": {"kg": {"tools_esperadas": ["mcp__kg__ver_nodo"]}, "fragmentos_hibrida": FRAG, "fragmentos_denso": FRAG}},
             "brazos": {"kg": {"rol": "grafo"}, "fragmentos_hibrida": {"rol": "fragmentos_principal"},
                        "fragmentos_denso": {"rol": "fragmentos_denso"}}}
MARCAS = {b: JB.marcas_d10(E_JUGUETE, b) for b in S.BRAZOS}
P_CORRECTO = {"kg": 0.6, "fragmentos_hibrida": 0.45, "fragmentos_denso": 0.5}
res = []


def c(nombre, ok):
    res.append(bool(ok))
    print("OK " if ok else "MAL", nombre)


def poblacion_de_juguete(semilla: int) -> dict:
    """Las entradas de `poblacion`, inventadas: el orden, el estado, las respuestas, los veredictos, los errores y los agregados."""
    r = random.Random(semilla)
    bloques, finales, textos = [], {}, {}
    for q in QV + QD:
        for rep in S.REPS:
            bl = f"{q}-r{rep}"
            bloques.append({"bloque": bl, "qid": q, "r": rep, "brazos": list(S.BRAZOS)})
            finales[bl] = {}
            for x in S.BRAZOS:
                sid = f"JUG-{q}-r{rep}-{x}"
                finales[bl][x] = {"clasificacion": "incompleta_otra" if r.random() < 0.03 else "completa", "id": sid, "intento": 1,
                                  "salida": f"pasada1/{sid}"}
                textos[sid] = f"Respuesta de juguete {sid}." + (" Según los nodos y los pasajes citados." if r.random() < 0.3 else "")
    ver, err, agr, info = {rep: [] for rep in S.REPS}, {rep: [] for rep in S.REPS}, {"agregados": [], "incompletas": []}, {}
    for b in bloques:
        for x in b["brazos"]:
            f = finales[b["bloque"]][x]
            if f["clasificacion"] != "completa":
                continue
            i = JB.id_opaco(b["qid"], x, b["r"], JB.sha256_texto(textos[f["id"]]))
            info[i] = {"qid": b["qid"], "brazo": x, "tipo": PREG[b["qid"]]["tipo"], "id_sesion": f["id"]}
            u = r.random()
            if u < 0.04:                                   # error del juez: en las tres repeticiones o en una
                malas = list(S.REPS) if u < 0.015 else [r.choice(S.REPS)]
                for rep in S.REPS:
                    (err if rep in malas else ver)[rep].append({"id_opaco": i, "rep": rep})
                agr["incompletas"].append({"id_opaco": i, "reps_faltantes": malas})
                continue
            for rep in S.REPS:
                ver[rep].append({"id_opaco": i, "rep": rep})
            v = ("requiere_adjudicacion" if r.random() < 0.06 else
                 "correcto" if r.random() < P_CORRECTO[x] else r.choice(["parcial", "incorrecto"]))
            agr["agregados"].append({"id_opaco": i, "n_criterios": PREG[b["qid"]]["n_criterios"], "veredicto_pregunta": v})
    return {"bloques": bloques, "finales": finales, "textos": textos, "ver": ver, "err": err, "agr": agr, "info": info}


def correr(P: dict, respuesta_de=None) -> tuple:
    rd = respuesta_de or (lambda f: P["textos"][f["id"]])
    filas, rec, salen = S.poblacion(P["bloques"], P["finales"], rd, PREG, P["ver"], P["err"], P["agr"], JB, MARCAS)
    return S.sortear(filas), filas, rec, salen


def frena_con(fn, motivo: str) -> bool:
    try:
        fn()
    except SystemExit as e:
        return str(e).startswith("FRENO") and motivo in str(e)
    return False


def con_veredictos(P: dict, nuevo) -> dict:
    """Una copia de P con el veredicto de cada agregado cambiado por nuevo(id, info, veredicto) (None: lo deja)."""
    Q = copy.deepcopy(P)
    for a in Q["agr"]["agregados"]:
        v = nuevo(a["id_opaco"], Q["info"][a["id_opaco"]], a["veredicto_pregunta"])
        if v is not None:
            a["veredicto_pregunta"] = v
    return Q


def elegibles(P: dict, brazo: str, tipo: str) -> list:
    return [a for a in P["agr"]["agregados"] if a["veredicto_pregunta"] != "requiere_adjudicacion"
            and (P["info"][a["id_opaco"]]["brazo"], P["info"][a["id_opaco"]]["tipo"]) == (brazo, tipo)]


def invariantes(k: dict, filas: list) -> bool:
    f = k["fichas"]
    ids = {x["id_opaco"] for x in filas}
    return (len(f) == 36 and len({x["id_pregunta"] for x in f}) == 36
            and all(sum(1 for x in f if x["brazo"] == b) == 12 for b in S.BRAZOS)
            and all(sum(1 for x in f if (x["brazo"], x["tipo"]) == (b, t)) == S.CUOTA_TIPO[t] for b in S.BRAZOS for t in S.TIPOS)
            and [x["ficha"] for x in f] == [f"C{i:02d}" for i in range(1, 37)] and all(x["id_opaco"] in ids for x in f))


# --- la base ------------------------------------------------------------------------------------------------------------ #
P = poblacion_de_juguete(1)
k1, f1, rec1, salen1 = correr(P)
k1b = correr(P)[0]
c("base: 36 fichas, 36 preguntas distintas, 12 por brazo, 9 y 3 por tipo en cada brazo, ids C01 a C36", invariantes(k1, f1))
c("base: cada clase con respuestas en su celda entra al menos una vez",
  {(x["brazo"], x["tipo"], x["clase"]) for x in f1} <= {(x["brazo"], x["tipo"], x["clase"]) for x in k1["fichas"]})
c("el mismo sorteo con las mismas entradas: determinístico (la clave y sus bytes)",
  k1 == k1b and json.dumps(k1, ensure_ascii=False, indent=1) == json.dumps(k1b, ensure_ascii=False, indent=1))
ids_err = {v["id_opaco"] for rep in S.REPS for v in P["err"][rep]}
ids_adj = {a["id_opaco"] for a in P["agr"]["agregados"] if a["veredicto_pregunta"] == "requiere_adjudicacion"}
n_otra = sum(1 for b in P["finales"].values() for f in b.values() if f["clasificacion"] == "incompleta_otra")
c("salen las incompleta_otra, las que tienen alguna salida en errores y las requiere_adjudicacion; ninguna está en las 36",
  salen1["incompleta_otra"] == n_otra and salen1["con_alguna_salida_en_errores"] == len(ids_err) == salen1["sin_sus_tres_juicios"]
  and salen1["requiere_adjudicacion"] == len(ids_adj) and not ({x["id_opaco"] for x in k1["fichas"]} & (ids_err | ids_adj)))
c("las cuotas por clase son proporcionales dentro de cada celda (restos mayores, con al menos 1 por clase presente)",
  all(abs(k1["cuotas_por_estrato"][f"{b}|{t}|correcto"] - S.CUOTA_TIPO[t] * k1["elegibles_por_estrato"][f"{b}|{t}|correcto"]
          / sum(k1["elegibles_por_estrato"][f"{b}|{t}|{cl}"] for cl in S.CLASES)) < 1.0001
      and all(k1["cuotas_por_estrato"][f"{b}|{t}|{cl}"] >= 1 for cl in S.CLASES if k1["elegibles_por_estrato"][f"{b}|{t}|{cl}"])
      for b in S.BRAZOS for t in S.TIPOS))
c("la marca de D-10 de la clave es la de contar_d10 de juez_b63, y hay fichas con y sin marca",
  all(x["marca_d10"] == JB.contar_d10(P["textos"][x["id_sesion"]], MARCAS[x["brazo"]])["con_alguna"] for x in k1["fichas"])
  and len({x["marca_d10"] for x in k1["fichas"]}) == 2)
c("la clave no trae ningún texto de una respuesta", "Respuesta de juguete" not in json.dumps(k1, ensure_ascii=False))

# --- 1. una celda chica -------------------------------------------------------------------------------------------------- #
celda = ("fragmentos_denso", "dato_directo")
tres, vistos = [], set()
for a in elegibles(P, *celda):
    if P["info"][a["id_opaco"]]["qid"] not in vistos and len(tres) < 3:
        tres.append(a["id_opaco"])
        vistos.add(P["info"][a["id_opaco"]]["qid"])
v_chica = {tres[0]: "correcto", tres[1]: "correcto", tres[2]: "parcial"}
P1 = con_veredictos(P, lambda i, inf, v: v_chica.get(i, "requiere_adjudicacion") if (inf["brazo"], inf["tipo"]) == celda else None)
k, f, _, _ = correr(P1)
c("una celda chica (3 elegibles, su cuota justa): se llena primero y entran sus tres",
  invariantes(k, f) and {x["id_opaco"] for x in k["fichas"] if (x["brazo"], x["tipo"]) == celda} == set(tres)
  and k["orden_de_llenado"].index("fragmentos_denso|dato_directo|correcto") < 3)
P1b = con_veredictos(P1, lambda i, inf, v: "requiere_adjudicacion" if i == tres[2] else None)
c("una celda con menos elegibles que su cuota frena con su motivo",
  frena_con(lambda: correr(P1b), "la celda fragmentos_denso|dato_directo tiene menos respuestas elegibles que su cuota"))

# --- 2. una clase sin respuestas ----------------------------------------------------------------------------------------- #
P2 = con_veredictos(P, lambda i, inf, v: "parcial" if (inf["brazo"], inf["tipo"]) == ("kg", "varios_puntos") and v == "correcto" else None)
k, f, _, _ = correr(P2)
c("una celda sin ninguna «correcto»: su cuota va entera a la otra clase",
  invariantes(k, f) and k["cuotas_por_estrato"]["kg|varios_puntos|correcto"] == 0
  and k["cuotas_por_estrato"]["kg|varios_puntos|parcial_o_incorrecto"] == 9
  and all(x["clase"] == "parcial_o_incorrecto" for x in k["fichas"] if (x["brazo"], x["tipo"]) == ("kg", "varios_puntos")))

# --- 3. una pregunta que se repite entre estratos ------------------------------------------------------------------------ #
def de_la_pregunta(P, brazo, q):
    return [a["id_opaco"] for a in elegibles(P, brazo, "dato_directo") if P["info"][a["id_opaco"]]["qid"] == q]


X = next(q for q in QD if de_la_pregunta(P, "kg", q) and de_la_pregunta(P, "fragmentos_hibrida", q))
unica = {de_la_pregunta(P, "kg", X)[0], de_la_pregunta(P, "fragmentos_hibrida", X)[0]}
P3 = con_veredictos(P, lambda i, inf, v: ("correcto" if i in unica else "parcial" if v == "correcto" else None)
                    if inf["brazo"] in ("kg", "fragmentos_hibrida") and inf["tipo"] == "dato_directo" else None)
k, f, _, _ = correr(P3)
c("una pregunta que es la única de dos estratos: entra una vez y el otro lugar pasa a la otra clase de su celda",
  invariantes(k, f) and sum(x["id_pregunta"] == X for x in k["fichas"]) == 1 and len(k["pasadas_a_la_otra_clase"]) == 1
  and k["pasadas_a_la_otra_clase"][0]["de"] in ("kg|dato_directo|correcto", "fragmentos_hibrida|dato_directo|correcto")
  and k["pasadas_a_la_otra_clase"][0]["a"] == k["pasadas_a_la_otra_clase"][0]["de"].replace("|correcto", "|parcial_o_incorrecto"))
Y = next(q for q in QD if len(de_la_pregunta(P, "kg", q)) == 3)
ys = de_la_pregunta(P, "kg", Y)
P3b = con_veredictos(P, lambda i, inf, v: ({ys[0]: "correcto", ys[1]: "parcial", ys[2]: "incorrecto"}.get(i, "requiere_adjudicacion")
                                            if (inf["brazo"], inf["tipo"]) == ("kg", "dato_directo") else None))
c("si la otra clase de la celda tampoco tiene una pregunta libre, frena",
  frena_con(lambda: correr(P3b), "y la otra clase de su celda se quedaron sin respuestas con pregunta libre"))

# --- 4. un id que no se recalcula ---------------------------------------------------------------------------------------- #
sid_x = next(f["id"] for b in P["finales"].values() for f in b.values() if f["clasificacion"] == "completa")
c("un id que no se recalcula (la respuesta de su meta cambió) frena",
  frena_con(lambda: correr(P, lambda f: P["textos"][f["id"]] + (" " if f["id"] == sid_x else "")),
            "los ids recalculados no son los de los veredictos"))
P4 = copy.deepcopy(P)
P4["ver"][1].append({"id_opaco": "B63J-0000000000", "rep": 1})
c("un id de los veredictos que no sale de ninguna sesión (sobra) frena", frena_con(lambda: correr(P4), "los ids recalculados no son"))

# --- 5. el empate de restos ---------------------------------------------------------------------------------------------- #
def parejo(P, brazo, tipo, n):
    """Deja n «correcto» y n «parcial o incorrecto» elegibles en la celda; el resto, requiere_adjudicacion."""
    cor = [a["id_opaco"] for a in elegibles(P, brazo, tipo) if a["veredicto_pregunta"] == "correcto"][:n]
    poi = [a["id_opaco"] for a in elegibles(P, brazo, tipo) if a["veredicto_pregunta"] != "correcto"][:n]
    quedan = set(cor) | set(poi)
    return con_veredictos(P, lambda i, inf, v: (None if i in quedan else "requiere_adjudicacion")
                          if (inf["brazo"], inf["tipo"]) == (brazo, tipo) else None)


P5 = parejo(parejo(P, "fragmentos_denso", "varios_puntos", 10), "fragmentos_hibrida", "dato_directo", 4)
k, f, _, _ = correr(P5)
gana = {}
for b, t in (("fragmentos_denso", "varios_puntos"), ("fragmentos_hibrida", "dato_directo")):
    d = S.CLASES[:]
    random.Random(f"{S.SEMILLA}|empate|{b}|{t}").shuffle(d)
    gana[(b, t)] = d[0]
c("el empate de restos (10 y 10 con cuota 9; 4 y 4 con cuota 3) lo rompe la semilla de su celda",
  invariantes(k, f) and all(k["cuotas_por_estrato"][f"{b}|{t}|{cl}"] == S.CUOTA_TIPO[t] // 2 + (cl == gana[(b, t)])
                            for (b, t) in gana for cl in S.CLASES))
c("restos_mayores: el empate va a la primera clase del desempate",
  S.restos_mayores({"correcto": 1, "parcial_o_incorrecto": 1}, 3, ["parcial_o_incorrecto", "correcto"])
  == {"correcto": 1, "parcial_o_incorrecto": 2}
  and S.restos_mayores({"correcto": 1, "parcial_o_incorrecto": 1}, 3, ["correcto", "parcial_o_incorrecto"])
  == {"correcto": 2, "parcial_o_incorrecto": 1})

print(f"pruebas: {sum(res)} de {len(res)}")
print("sha256 de la clave de juguete de la base:",
      hashlib.sha256(json.dumps(k1, ensure_ascii=False, indent=1).encode("utf-8")).hexdigest())
