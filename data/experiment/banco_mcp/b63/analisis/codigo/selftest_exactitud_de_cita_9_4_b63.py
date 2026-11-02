#!/usr/bin/env python3
"""selftest_exactitud_de_cita_9_4_b63.py — La prueba de exactitud_de_cita_9_4_b63.py con datos de juguete (B6.3, punto 4 del §9, etapa
D1). USD 0, sin la API, sin ningún dato real de B6.3: arma en --trabajo (que no puede existir) mundos de juguete con la forma de las
entradas reales (la entrada, sus preguntas con sus anclas, el estado y las sesiones de banco_b63/ con su manifiesto, la E0 de dos TO y
su armado) y corre el punto 4 sobre ellos. Los valores esperados los calcula la prueba por su cuenta, desde su diseño, con una
normalización propia de las citas y las anclas de juguete.

Del código de HEAD y de las etapas anteriores usa solo el import (el clon de b63/v2/b2, analizar_b63.py sellado y el instrumento de
citas de HEAD, --ucita, con su sha256). El instrumento corre de verdad en un mundo (dos sesiones que entran); en los demás lo simula la
prueba, que controla lo que recibe y escribe su salida.

Las ramas:
  - un rango que se expande a sus hermanos y otro que no, porque sus extremos tienen distinto padre;
  - una unidad con sufijo y una de subdocumento, que el instrumento no lee y sacan su pregunta, con sus sesiones, declaradas por posición
    y por brazo;
  - una cita en un hermano del medio de un rango, que da en el ancla;
  - la columna informativa rearmada por ancla original: dos anclas de las que se cita solo una, y dos citadas, donde el rearmado cambia el
    valor del instrumento; sin JSON final y sin citas, el del instrumento; y un rearmado que no reproduce al instrumento, que deja la
    columna sin calcular para las preguntas con un rango;
  - el instrumento simulado que termina bien y que no, y una corrida real del instrumento de HEAD sobre dos sesiones de juguete;
  - los frenos: --salida que ya existe y un instrumento que no da su sha256;
  - que el punto 4 no imprime nada y que dos corridas sobre el mismo mundo dan el mismo JSON, byte a byte.

Imprime solo el nombre de cada control con PASS o FAIL y el sha256 del informe (sin rutas, para que dos corridas den lo mismo).

  python3 -I -B selftest_exactitud_de_cita_9_4_b63.py --clon <b63/v2/b2 de una copia de HEAD> --ucita <scripts/ucita2_indicadores_banco.py>
      --trabajo <carpeta nueva> --informe <json nuevo>
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import exactitud_de_cita_9_4_b63 as D  # noqa: E402

A = D.A
ARCHIVO = {"cla": "cla.pdf", "dos": "dos.pdf"}
SECCIONES = [{"tipo": "seccion", "numero": "1", "hijos": [
                 {"tipo": "punto", "numero": "1.1", "hijos": [{"tipo": "punto", "numero": f"1.1.{i}", "hijos": []} for i in (1, 2, 3)]},
                 {"tipo": "punto", "numero": "1.2", "hijos": [{"tipo": "punto", "numero": "1.2.1", "hijos": []}]}]},
             {"tipo": "seccion", "numero": "2", "hijos": [{"tipo": "punto", "numero": "2.1", "hijos": []},
                                                          {"tipo": "punto", "numero": "2.2", "hijos": []}]},
             {"tipo": "seccion", "numero": "bloque1", "hijos": []}]
# Las preguntas de juguete: sus anclas (ancla y otro punto) y, por brazo, la clasificación y las citas de su única corrida (k = 1)
PREGUNTAS = {
    "JUG-Q1": {"anclas": ["cla::1.1.1..1.1.3", "cla::2.1"],
               "kg": ("completa", ["cla.pdf | 1.1.2"]), "fragmentos_hibrida": ("completa", ["cla.pdf | 1.1.2", "cla.pdf | 2.1"])},
    "JUG-Q2": {"anclas": ["cla::1.1..1.2", "cla::2.2"],
               "kg": ("completa", ["cla.pdf | 1.2", "cla.pdf | Punto 2.2"]), "fragmentos_hibrida": ("incompleta_otra", None)},
    "JUG-Q3": {"anclas": ["cla::1.1.3..2.1"],
               "kg": ("completa", ["cla | 2.1"]), "fragmentos_hibrida": ("completa", ["cla.pdf | 1.2.1"])},
    "JUG-Q4": {"anclas": ["cla::1.2::intro"], "kg": ("completa", ["cla.pdf | 1.2"]), "fragmentos_hibrida": ("completa", ["cla.pdf | 1.2"])},
    "JUG-Q5": {"anclas": ["dos::SD::rep1", "dos::2.1"],
               "kg": ("completa", ["dos.pdf | 2.1"]), "fragmentos_hibrida": ("completa", ["dos.pdf | 2.1"])},
    "JUG-Q6": {"anclas": ["dos::S1", "dos::Sbloque1"],
               "kg": ("completa", ["dos.pdf | Sección 1"]), "fragmentos_hibrida": ("completa", [])},
}
# Lo que se espera de la lectura de las anclas (unidades por ancla, si tiene un rango, si sale) y del rearmado
UNIDADES = {"JUG-Q1": [["cla::1.1.1", "cla::1.1.2", "cla::1.1.3"], ["cla::2.1"]], "JUG-Q2": [["cla::1.1", "cla::1.2"], ["cla::2.2"]],
            "JUG-Q3": [["cla::1.1.3", "cla::2.1"]], "JUG-Q4": [["cla::1.2::intro"]], "JUG-Q5": [["dos::SD::rep1"], ["dos::2.1"]],
            "JUG-Q6": [["dos::S1"], ["dos::Sbloque1"]]}
SALEN = ["JUG-Q4", "JUG-Q5"]


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def escribir(p: Path, contenido) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    b = contenido if isinstance(contenido, (bytes, str)) else json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    b = b.encode("utf-8") if isinstance(b, str) else b
    p.write_bytes(b)
    return sha_b(b)


# --------------------------------------------------------------------------------------------------------------------- #
# Lo esperado, calculado por la prueba                                                                                  #
# --------------------------------------------------------------------------------------------------------------------- #
def punto_de_cita(loc: str) -> str:
    """La normalización de juguete: «Punto n» y «n» dan n; «Sección n» da n."""
    m = re.match(r"^(?:Punto |Sección )?(\S+)$", loc)
    return m.group(1)


def punto_de_unidad(u: str) -> str:
    """«S1» da 1 y «Sbloque1» da bloque1, como una sección; un número, tal cual."""
    return u[1:] if u.startswith("S") else u


def citas_a_pares(citas: list) -> list:
    out = []
    for c in citas:
        doc, loc = (x.strip() for x in c.split("|"))
        out.append((doc.replace(".pdf", ""), punto_de_cita(loc)))
    return out


def da(par, unidad: str) -> bool:
    to, u = unidad.split("::", 1)
    p = punto_de_unidad(u)
    return par[0] == to and (par[1] == p or par[1].startswith(p + "."))


def esperado_de_sesion(q: str, brazo: str) -> dict:
    """La fila que daría el instrumento sobre las unidades, y la columna informativa por ancla original."""
    clase, citas = PREGUNTAS[q][brazo]
    unidades = D.sin_repetir([u for anc in UNIDADES[q] for u in anc])
    if clase != "completa":
        return {"grupo": "sin_json", "ind3": "sin_json", "n_con": None, "info_instrumento": "sin_json", "info_rearmada": "sin_json"}
    if not citas:
        return {"grupo": "contenido", "ind3": "sin_citas", "n_con": None, "info_instrumento": "sin_citas", "info_rearmada": "sin_citas"}
    pares = citas_a_pares(citas)
    con = {j for j, u in enumerate(unidades) if any(da(p, u) for p in pares)}
    return {"grupo": "contenido", "ind3": "si" if con else "no", "n_con": len(con),
            "info_instrumento": "si" if len(con) == len(unidades) else "no",
            "info_rearmada": "si" if all(any(da(p, u) for p in pares for u in anc) for anc in UNIDADES[q]) else "no"}


# --------------------------------------------------------------------------------------------------------------------- #
# El mundo de juguete                                                                                                   #
# --------------------------------------------------------------------------------------------------------------------- #
def mundo(W: Path, JB, K, qids: list, brazos: list, ucita: Path) -> tuple[dict, dict]:
    W.mkdir(parents=True)
    esp = {k: D.ESPERADO[k] for k in ("mapping", "juez_b63", "aplicar_lectura_tolerante_b63", "ucita")}
    E0 = W / "e0"
    armado = {"e0": []}
    for to, arch in ARCHIVO.items():
        armado["e0"].append({"archivo": f"estructura_{to}.json", "to": to,
                             "sha256": escribir(E0 / f"estructura_{to}.json", {"to": to, "archivo": arch, "secciones": SECCIONES})})
    esp["armado_e0"] = escribir(W / "armado_e0_juguete.json", armado)
    preguntas = {"preguntas": [{"id": q, "pregunta": f"Pregunta de juguete {q[-1]}", "tipo": "varios_puntos" if len(PREGUNTAS[q]["anclas"]) > 1
                                else "dato_directo", "to": PREGUNTAS[q]["anclas"][0].split("::")[0],
                                "anclas": [{"rol": rol, "unidad": u} for rol, u in zip(("ancla", "otro_punto"), PREGUNTAS[q]["anclas"])],
                                "criterios": [{"criterio": "criterio de juguete", "cita_textual": "cita de juguete"}]} for q in qids]}
    sp = escribir(W / "preguntas_juguete.json", preguntas)
    entrada = {"preguntas": {"ruta": "preguntas_juguete.json", "sha256": sp, "ids_en_orden": qids,
                             "esquema": {"lista": "preguntas", "id": "id", "pregunta": "pregunta", "criterios": "criterios",
                                         "criterio": "criterio", "cita": "cita_textual"}},
               "k": 1, "brazos": {b: {} for b in brazos}}
    esp["entrada"] = escribir(W / "entrada_juguete.json", entrada)
    R = W / "banco_b63" / "resultados" / "real"
    st = {"bloques": {}}
    for b in K.orden_bloques(qids, 1, sorted(brazos)):
        blq = {"final": {}, "intentos_por_brazo": {}}
        for x in sorted(brazos):
            clase, citas = PREGUNTAS[b["qid"]][x]
            sid = K.id_sesion(b["qid"], b["r"], x)
            blq["final"][x] = {"clasificacion": clase, "id": sid, "intento": 1, "salida": f"pasada1/{sid}"}
            blq["intentos_por_brazo"][x] = 1
            S = R / "pasada1" / sid
            meta = {"brazo": x, "completitud_R3": {"completa": clase == "completa"}}
            if clase == "completa":
                meta["final_json_R4"] = {"respondible": True, "respuesta": f"Respuesta de juguete {b['qid'][-1]} {x}", "citas": citas}
            escribir(S / f"meta_{sid}.json", meta)
            escribir(S / f"log_r1_{sid}.jsonl", json.dumps({"evento": "inicio"}) + "\n")
            escribir(S / f"meta_sin_texto_{sid}.json", {"brazo": x})
        st["bloques"][b["bloque"]] = blq
    escribir(R / "estado_b63.json", st)
    archivos = sorted(p for p in (W / "banco_b63").rglob("*") if p.is_file())
    esp["manifiesto_fuera"] = escribir(W / "manifiesto_juguete.json", {"archivos": [{"ruta": str(p.relative_to(W)), "sha256": sha_b(p.read_bytes())}
                                                                                    for p in archivos]})
    rutas = {"clon": None, "entrada": W / "entrada_juguete.json", "manifiesto_fuera": W / "manifiesto_juguete.json",
             "banco_b63": W / "banco_b63", "e0": E0, "armado_e0": W / "armado_e0_juguete.json", "ucita": ucita}
    return rutas, esp


class Simulado:
    """El instrumento simulado: controla lo que recibe y escribe su salida con las filas que da la prueba (o una fila tocada)."""

    def __init__(self, UC, codigo: int = 0, tocar: str | None = None):
        self.UC, self.codigo, self.tocar, self.recibido = UC, codigo, tocar, None

    def __call__(self, argv):
        ses = argv[argv.index("--sesiones") + 1: argv.index("--anclas")]
        mapa = json.loads(Path(argv[argv.index("--mapa-sesiones") + 1]).read_text(encoding="utf-8"))
        anclas = json.loads(Path(argv[argv.index("--anclas") + 1]).read_text(encoding="utf-8"))
        sin_enlaces = all(not Path(s).is_symlink() and all(not p.is_symlink() for p in Path(s).iterdir()) for s in ses)
        self.recibido = {"anclas": anclas, "preguntas_del_mapa": sorted(set(mapa.values())), "sesiones": len(ses), "sin_enlaces": sin_enlaces,
                         "python": argv[0] == sys.executable and argv[1:3] == ["-I", "-B"]}
        if self.codigo != 0:
            return SimpleNamespace(returncode=self.codigo, stdout="", stderr="simulado: no termina bien\n")
        filas = []
        for sid, q in sorted(mapa.items()):
            brazo = next(b for b in ("kg", "fragmentos_hibrida", "fragmentos_denso") if sid.endswith("-" + b))
            x = esperado_de_sesion(q, brazo)
            f = {"sesion": sid, "pregunta": q, "brazo": brazo, "grupo": x["grupo"], "n_anclas_con_cita": x["n_con"],
                 "ind1_cita_fundada": "no" if x["ind3"] in ("si", "no") else x["ind3"],
                 "ind2_cita_existente": "si" if x["ind3"] in ("si", "no") else x["ind3"],
                 "ind3_cita_al_ancla": x["ind3"], "info_cada_ancla_con_cita": x["info_instrumento"]}
            if self.tocar == sid:
                f["n_anclas_con_cita"] = (f["n_anclas_con_cita"] or 0) + 1
            filas.append(f)
        Path(argv[argv.index("--out-json") + 1]).write_text(json.dumps({"agregados": self.UC.agregar(filas), "filas": filas,
                                                                        "anclas_en_indice": {"resueltas": 0, "total": 0, "no_resueltas": []}},
                                                                       ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="simulado\n", stderr="")


def correr(rutas, esp, W: Path, salida: Path, clon: Path, simulado=None):
    rutas = rutas | {"clon": clon}
    buf, previo = io.StringIO(), os.getcwd()
    os.chdir(W)
    try:
        with contextlib.redirect_stdout(buf):
            return D.punto4(rutas, esp, salida, simulado), None, buf.getvalue()
    except A.Freno as ex:
        return None, str(ex), buf.getvalue()
    finally:
        os.chdir(previo)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clon", type=Path, required=True)
    ap.add_argument("--ucita", type=Path, required=True)
    ap.add_argument("--trabajo", type=Path, required=True)
    ap.add_argument("--informe", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.trabajo.exists() or a.informe.exists():
        raise SystemExit("--trabajo y --informe no pueden existir")
    T = a.trabajo.resolve()
    T.mkdir(parents=True)
    AP, JB = A.importar(a.clon, D.ESPERADO)
    K = JB.K
    UC = D.importar_instrumento(a.ucita, D.ESPERADO)
    R: dict = {}
    frenos: dict = {}

    def control(nombre, cond):
        R[nombre] = "PASS" if cond else "FAIL"

    def info(o, brazo):
        return o["indicadores"]["la_columna_informativa_por_ancla_original"]["agregados"][brazo]["todas"]["info_cada_ancla_con_cita"]["si_n_de_N"]

    # --- El mundo de las ramas, con el instrumento simulado ----------------------------------------------------------- #
    qids, brazos = list(PREGUNTAS), ["fragmentos_hibrida", "kg"]
    rS, eS = mundo(T / "mundo_ramas", JB, K, qids, brazos, a.ucita)
    sim = Simulado(UC)
    oS, fS, impS = correr(rS, eS, T / "mundo_ramas", T / "salida_ramas", a.clon, sim)
    oS2, fS2, _ = correr(rS, eS, T / "mundo_ramas", T / "salida_ramas_bis", a.clon, Simulado(UC))
    control("ramas_corre_sin_freno", fS is None and fS2 is None)
    if fS is None:
        bS = (T / "salida_ramas" / "punto4_B63.json").read_bytes()
        control("ramas_dos_corridas_iguales_byte_a_byte", bS == (T / "salida_ramas_bis" / "punto4_B63.json").read_bytes())
        control("ramas_no_imprime_nada", impS == "")
        R["sha256_salida_ramas"] = sha_b(bS)
        pos = {p["posicion"]: p for p in oS["anclas"]["por_posicion"]}
        control("un_rango_que_se_expande_a_sus_hermanos", pos[1]["unidades_por_ancla"] == [3, 1] and pos[2]["unidades_por_ancla"] == [2, 1]
                and pos[1]["con_un_rango"] and pos[2]["con_un_rango"])
        control("un_rango_cuyos_extremos_tienen_distinto_padre_no_se_expande", pos[3]["unidades_por_ancla"] == [2] and pos[3]["con_un_rango"])
        control("sufijo_y_subdocumento_sacan_su_pregunta", pos[4]["sale"] and pos[4]["unidades_que_el_instrumento_no_lee"] == 1
                and pos[5]["sale"] and pos[5]["unidades_que_el_instrumento_no_lee"] == 1 and not any(pos[i]["sale"] for i in (1, 2, 3, 6))
                and oS["salen"] == {"preguntas": 2, "posiciones": [4, 5], "sesiones_por_brazo": {"fragmentos_hibrida": 2, "kg": 2}}
                and oS["sesiones_que_entran"] == 8)
        control("las_sesiones_de_las_que_salen_no_entran", sim.recibido["preguntas_del_mapa"] == ["JUG-Q1", "JUG-Q2", "JUG-Q3", "JUG-Q6"]
                and sim.recibido["sesiones"] == 8 and sim.recibido["sin_enlaces"] and sim.recibido["python"])
        control("el_archivo_de_anclas_lleva_las_unidades_de_todas_sus_anclas",
                sim.recibido["anclas"] == {q: D.sin_repetir([u for anc in UNIDADES[q] for u in anc]) for q in ("JUG-Q1", "JUG-Q2", "JUG-Q3", "JUG-Q6")})
        ci = oS["indicadores"]["la_columna_informativa_por_ancla_original"]
        esperadas = {(q, b): esperado_de_sesion(q, b) for q in ("JUG-Q1", "JUG-Q2", "JUG-Q3", "JUG-Q6") for b in brazos}
        cambian = sum(1 for (q, b), x in esperadas.items() if q != "JUG-Q6" and x["info_rearmada"] != x["info_instrumento"])
        control("la_columna_informativa_rearmada", ci["calculada"] is True and ci["control"] == {
            "sesiones": 8, "dan_el_indicador_3_y_las_unidades_con_cita": 8, "sin_rango": 2, "sin_rango_iguales_al_instrumento": 2,
            "con_rango": 6, "cambian_por_el_rearmado": cambian} and cambian == 3)
        ok = True
        for b in brazos:
            fs = [x for (q, bb), x in esperadas.items() if bb == b]
            ok &= info(oS, b) == f"{sum(x['info_rearmada'] == 'si' for x in fs)} de {len(fs)}"
            ok &= oS["indicadores"]["del_instrumento"][b]["todas"]["ind3_cita_al_ancla"]["si_n_de_N"] == f"{sum(x['ind3'] == 'si' for x in fs)} de {len(fs)}"
        control("los_indicadores_por_brazo_en_fraccion_cruda", ok)
        th = ci["agregados"]["fragmentos_hibrida"]["todas"]["info_cada_ancla_con_cita"]
        control("sin_json_y_sin_citas_quedan_como_el_instrumento", th["sin_json"] == 1 and th["sin_citas"] == 1)
    else:
        frenos["ramas"] = fS

    # --- Un rearmado que no reproduce al instrumento, y el instrumento que no termina bien ----------------------------- #
    r2, e2 = mundo(T / "mundo_fila_tocada", JB, K, qids, brazos, a.ucita)
    o2, f2, _ = correr(r2, e2, T / "mundo_fila_tocada", T / "salida_fila_tocada", a.clon,
                       Simulado(UC, tocar=K.id_sesion("JUG-Q1", 1, "kg")))
    control("un_rearmado_que_no_reproduce_deja_la_columna_sin_calcular_para_las_de_un_rango", f2 is None
            and o2["indicadores"]["la_columna_informativa_por_ancla_original"]["calculada"] is False
            and set(o2["indicadores"]["la_columna_informativa_por_ancla_original"]["agregados_de_las_preguntas_sin_rango"]) == set(brazos)
            and all(o2["indicadores"]["la_columna_informativa_por_ancla_original"]["agregados_de_las_preguntas_sin_rango"][b]["todas"]["N"] == 1
                    for b in brazos))
    r3, e3 = mundo(T / "mundo_no_termina", JB, K, qids, brazos, a.ucita)
    o3, f3, _ = correr(r3, e3, T / "mundo_no_termina", T / "salida_no_termina", a.clon, Simulado(UC, codigo=2))
    control("el_instrumento_que_no_termina_bien_se_declara", f3 is None and o3["instrumento"]["corrio"] is False
            and o3["instrumento"]["codigo_de_salida"] == 2 and "declarado" in o3["indicadores"]
            and (T / "salida_no_termina" / "punto4_B63.json").is_file())

    # --- La corrida real del instrumento de HEAD, sobre dos sesiones ---------------------------------------------------- #
    rR, eR = mundo(T / "mundo_real", JB, K, ["JUG-Q1", "JUG-Q2", "JUG-Q4", "JUG-Q5"], ["kg"], a.ucita)
    oR, fR, impR = correr(rR, eR, T / "mundo_real", T / "salida_real", a.clon)
    if fR is None and oR["instrumento"]["corrio"]:
        o = json.loads((T / "salida_real" / "trabajo_exactitud_de_cita" / "ucita_B63.json").read_text(encoding="utf-8"))
        fila = {f["pregunta"]: f for f in o["filas"]}
        ci = oR["indicadores"]["la_columna_informativa_por_ancla_original"]
        control("la_corrida_real_sobre_dos_sesiones", oR["sesiones_que_entran"] == 2 and sorted(fila) == ["JUG-Q1", "JUG-Q2"]
                and oR["salen"]["posiciones"] == [3, 4] and impR == ""
                and all(fila[q]["ind3_cita_al_ancla"] == "si" and fila[q]["n_anclas_con_cita"] == esperado_de_sesion(q, "kg")["n_con"]
                        and fila[q]["info_cada_ancla_con_cita"] == esperado_de_sesion(q, "kg")["info_instrumento"] for q in ("JUG-Q1", "JUG-Q2")))
        control("la_corrida_real_rearma_la_columna_informativa", ci["calculada"] is True and info(oR, "kg") == "1 de 2"
                and o["agregados"]["kg"]["todas"]["info_cada_ancla_con_cita"]["si_n_de_N"] == "0 de 2"
                and ci["control"]["cambian_por_el_rearmado"] == 1)
        control("una_cita_en_un_hermano_del_medio_da_en_el_ancla", fila["JUG-Q1"]["ind3_cita_al_ancla"] == "si"
                and fila["JUG-Q1"]["n_anclas_con_cita"] == 1)
        # de las dos, solo la segunda cambia (no a si): la primera, con dos anclas de las que se cita solo una, sigue en no
        control("dos_anclas_de_las_que_se_cita_solo_una", fila["JUG-Q1"]["info_cada_ancla_con_cita"] == "no"
                and fila["JUG-Q2"]["info_cada_ancla_con_cita"] == "no" and info(oR, "kg") == "1 de 2"
                and ci["control"]["cambian_por_el_rearmado"] == 1)
    else:
        frenos["real"] = fR or f"el instrumento salió con {oR['instrumento'].get('codigo_de_salida')}"
        for n in ("la_corrida_real_sobre_dos_sesiones", "la_corrida_real_rearma_la_columna_informativa",
                  "una_cita_en_un_hermano_del_medio_da_en_el_ancla", "dos_anclas_de_las_que_se_cita_solo_una"):
            control(n, False)

    # --- Los frenos ---------------------------------------------------------------------------------------------------- #
    o4, f4, _ = correr(rS, eS, T / "mundo_ramas", T / "salida_ramas", a.clon, Simulado(UC))
    frenos["salida_que_ya_existe"] = f4
    control("freno_salida_que_ya_existe", o4 is None and f4 == "--salida ya existe")
    o5, f5, _ = correr(rS, eS | {"ucita": "0" * 64}, T / "mundo_ramas", T / "salida_ucita_otro", a.clon, Simulado(UC))
    frenos["un_instrumento_que_no_da_su_sha256"] = f5
    control("freno_un_instrumento_que_no_da_su_sha256", o5 is None and f5 == "scripts/ucita2_indicadores_banco.py no da su sha256"
            and not (T / "salida_ucita_otro").exists())

    informe = {"que": "la prueba de exactitud_de_cita_9_4_b63.py con datos de juguete (B6.3, punto 4 del §9, etapa D1)",
               "codigo": {"exactitud_de_cita_9_4_b63.py": sha_b((AQUI / "exactitud_de_cita_9_4_b63.py").read_bytes()),
                          "selftest_exactitud_de_cita_9_4_b63.py": sha_b(Path(__file__).read_bytes()),
                          "analizar_b63.py": sha_b((AQUI / "analizar_b63.py").read_bytes()), "ucita2_indicadores_banco.py": sha_b(a.ucita.read_bytes())},
               "controles": R, "frenos": frenos, "da": all(v == "PASS" for k, v in R.items() if not k.startswith("sha256_"))}
    a.informe.parent.mkdir(parents=True, exist_ok=True)
    a.informe.write_text(json.dumps(informe, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in R.items():
        if not k.startswith("sha256_"):
            print(f"{v}  {k}")
    print(f"prueba: {'PASS' if informe['da'] else 'FAIL'} ({sum(v == 'PASS' for v in R.values())} de "
          f"{sum(1 for k in R if not k.startswith('sha256_'))}); informe sha256 {sha_b(a.informe.read_bytes())}")
    return 0 if informe["da"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
