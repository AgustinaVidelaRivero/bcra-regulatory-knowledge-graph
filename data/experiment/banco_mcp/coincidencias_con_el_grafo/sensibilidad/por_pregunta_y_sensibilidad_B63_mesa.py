"""por_pregunta_y_sensibilidad_B63_mesa.py — Mesa, §393 (01/11/2026): B6.3 y las coincidencias del grafo con sus criterios. ANÁLISIS
POSTERIOR, NO PRE-REGISTRADO, sin Holm ni ninguna afirmación principal nueva. USD 0.
  1. El análisis de B6.3 otra vez, sobre copias: el código de `fuera_del_repo/analisis_b63/codigo/` (controlado contra el sello de la
     etapa B) en <trabajo>/codigo, y el clon de `C` con los archivos que lista `corrida_analisis_C.zsh`, con las mismas entradas que ese
     comando. Se frena en la primera llamada a `confirmatorio` (la del escenario principal), después de calcularla con el código del
     análisis, y se controla que su resultado sea, valor por valor, el `confirmatorio.principal` de `analisis_B63.json` de `C`.
  2. De la métrica del escenario principal: en cada pregunta de B6.3 con alguna coincidencia, las correctas sobre las contadas de cada
     brazo y su d en cada comparación principal (kg contra cada sistema por fragmentos).
  3. La sensibilidad, con el mismo `confirmatorio`, los mismos remuestreos y las mismas semillas, sin el análisis por documento: la media
     de d de cada comparación principal, con su intervalo del 95 % y el p de la misma permutación de signos, y la fidelidad de
     cada brazo con su intervalo (bootstrap percentil), (i) sin las preguntas con alguna coincidencia y
     (ii) sin las que tienen una coincidencia que no es literal, redactada o casi texto de la norma (las clases de
     `las_15_coincidencias.json`).
Imprime solo ids, cuentas y cifras.
  python3 -I -B por_pregunta_y_sensibilidad_B63_mesa.py <repo> <fuera_del_repo> <trabajo, que no existe> <las_15_coincidencias.json>
"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

R, F, T, J = (Path(x).resolve() for x in sys.argv[1:5])
C = "c190505c3ac63bf9d7cf51b94e3be04358cd7832"
M = F / "hoja_de_ruta_tanda1_mesa"
PA = F / "revision_B63_analisis_A"
COLA = "9c865fc416f4238791d6437df9d64d1e3c0a47724cf7ec98e23f0edc26cb00ab"
CLON = ["data/experiment/banco_mcp/b63/v2/b2/comun_b63.py", "data/experiment/banco_mcp/b63/v2/b2/juez_b63.py",
        "data/experiment/banco_mcp/b63/entrada_B63.json", "data/experiment/banco_mcp/comun_banco.py",
        "data/experiment/banco_mcp/lectura_tolerante_juez.py", "data/experiment/ev2_juez/juez.py", "data/experiment/ev2_juez/mapping.py",
        "data/experiment/ev2_juez/prompt_juez_v1.md", "data/experiment/evaluacion/llm_cache.py",
        "data/experiment/banco_mcp/b63/real/manifiesto_fuera_resultados_y_juez_B63.json",
        "data/experiment/banco_mcp/b63/real/juez/d10_b63.json",
        "data/experiment/banco_mcp/b63/real/fechas_b63.json", "data/experiment/tanda_final/t3/acumulado/armado_acumulado_128_tf.json"]
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
assert not T.exists(), "FRENO: el trabajo ya existe"
(T / "codigo").mkdir(parents=True)
sello = (F / "analisis_b63/salidas/b/sello_analisis_B63.txt").read_text(encoding="utf-8")
for x in sorted((F / "analisis_b63/codigo").glob("*.py")):
    shutil.copyfile(x, T / "codigo" / x.name)
for n in ("analizar_b63.py", "selftest_analizar_b63.py"):
    b = (T / "codigo" / n).read_bytes()
    assert f"{sha(b)}  {len(b)}  codigo/{n}" in sello, f"FRENO: {n} no es el del sello"
(T / "clon").mkdir()
arch = subprocess.run(["git", "--no-optional-locks", "-C", str(R), "archive", C, *CLON], capture_output=True, check=True).stdout
subprocess.run(["tar", "-x", "-C", str(T / "clon")], input=arch, check=True)
X = T / "clon/data/experiment"
spec = importlib.util.spec_from_file_location("analizar_b63", T / "codigo/analizar_b63.py")
A = importlib.util.module_from_spec(spec)
sys.modules["analizar_b63"] = A
spec.loader.exec_module(A)
assert Path(A.__file__).resolve().is_relative_to(T)
rutas = {"clon": X / "banco_mcp/b63/v2/b2", "entrada": X / "banco_mcp/b63/entrada_B63.json",
         "manifiesto_fuera": X / "banco_mcp/b63/real/manifiesto_fuera_resultados_y_juez_B63.json", "banco_b63": F / "banco_b63",
         "agregados": F / "analisis_b63/salidas/aplicacion/juez_con_lectura_tolerante/agregados_b63_ciego.json",
         "agregados_tolerante": F / "analisis_b63/salidas/aplicacion/agregados_de_las_que_no_se_leian_b63.json",
         "veredictos_tolerante": F / "analisis_b63/salidas/aplicacion/veredictos_lectura_tolerante_b63.jsonl",
         "planilla": F / "analisis_b63/adjudicacion/para_leer/planilla_adjudicacion_b63.csv",
         "sello_planilla": F / "analisis_b63/adjudicacion/para_leer/sello_adjudicacion_b63.txt",
         "estructura_planilla": F / "analisis_b63/adjudicacion/para_leer/estructura_planilla_adjudicacion_b63.json",
         "clave_adjudicacion": PA / "clave_para_despues/clave_adjudicacion_b63.json", "d10": X / "banco_mcp/b63/real/juez/d10_b63.json",
         "fechas": X / "banco_mcp/b63/real/fechas_b63.json", "relevancia": M / "decisiones_279_mesa/relevancia_96/relevancia_96_B63.json",
         "etapa1": F / "b63_etapa1", "tabla_cruce": M / "decisiones_182_mesa/cruce/tabla_cruce_ext_v2_mesa.json",
         "sello_tabla": M / "decisiones_182_mesa/cruce/sello_tabla_cruce_ext_v2_mesa.txt",
         "pesos_mesa": M / "decisiones_182_mesa/cruce/salida_aplicar_cruce_ext_mesa.json",
         "cola": M / "decisiones_329_mesa/cola/cola_grafo_evaluado_b63_CANDIDATA_mesa.json",
         "kg": R / "data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json",
         "e0": R / "data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b",
         "armado_e0": X / "tanda_final/t3/acumulado/armado_acumulado_128_tf.json", "expertos": F / "b63_material_expertos",
         "ucita": R / "scripts/ucita2_indicadores_banco.py"}


class Alto(Exception):
    pass


original = A.confirmatorio
capt = {}


def envoltura(qids, m, P, pesos, n_perm, n_boot, por_documento=True):
    capt.update(qids=qids, m=m, P=P, pesos=pesos, n_perm=n_perm, n_boot=n_boot,
                res=original(qids, m, P, pesos, n_perm, n_boot, por_documento))
    raise Alto


A.confirmatorio = envoltura
try:
    A.analizar(rutas, A.ESPERADO | {"cola": COLA}, T / "salida")
except Alto:
    pass
A.confirmatorio = original
norm = lambda x: json.loads(json.dumps(x, sort_keys=True))  # noqa: E731
comm = json.loads(subprocess.run(["git", "--no-optional-locks", "-C", str(R), "show",
                                  f"{C}:data/experiment/banco_mcp/b63/analisis/c/analisis_B63.json"],
                                 capture_output=True, check=True).stdout)
igual = norm(capt["res"]) == norm(comm["confirmatorio"]["principal"])
print(f"1. B6.3 otra vez, sobre copias, hasta el confirmatorio principal: {len(capt['qids'])} preguntas; {capt['n_perm']} permutaciones y "
      f"{capt['n_boot']} remuestreos; las semillas {A.SEMILLAS['bootstrap']} y {A.SEMILLAS['permutacion']}; el confirmatorio principal es, "
      f"valor por valor, el de analisis_B63.json de C: {igual}")
assert igual, "FRENO: el confirmatorio principal no es el commiteado"
m, P, qids = capt["m"], capt["P"], capt["qids"]
fil = json.loads(J.read_text(encoding="utf-8"))["coincidencias"]
con = sorted({r["pregunta"] for r in fil if r["fuente"] == "B6.3"})
blandas = sorted({r["pregunta"] for r in fil if r["fuente"] == "B6.3" and r["clase"] != "texto de la norma"})
print(f"2. ANÁLISIS POSTERIOR, NO PRE-REGISTRADO. Las {len(con)} preguntas de B6.3 con alguna coincidencia, en el escenario principal:")
for q in con:
    clases = sorted({r["clase"] for r in fil if r["pregunta"] == q})
    por = "; ".join(f"{b} {m[(q, b)][0]} de {m[(q, b)][1]}" if (q, b) in m else f"{b} sin corridas contadas" for b in A.BRAZOS)
    ds = "; ".join(f"kg − {f} {A.d6(m, q, f) / 6:+.4f}" for f in A.FRAGMENTOS if (q, A.BRAZO_GRAFO) in m and (q, f) in m)
    print(f"   {q} ({', '.join(clases)}): {por} | d: {ds}")


def mostrar(nombre, r, brazos, comps):
    for f in comps:
        c = r["por_comparacion"][f]
        lo, hi = c["intervalo_95"]
        print(f"   {nombre}: kg − {f}: {c['preguntas']} preguntas, media de d {c['media_d']:+.4f}, "
              f"intervalo del 95 % [{lo:+.4f}; {hi:+.4f}], "
              f"p de la permutación de signos {c['permutacion']['p']:.5f} ({c['permutacion']['mayores_o_iguales']} de las permutaciones "
              f"con |suma| mayor o igual)")
    print(f"   {nombre}: la fidelidad de cada brazo (la media de la proporción de correctas, con su intervalo del 95 %): " + "; ".join(
        f"{b} {r['por_brazo'][b]['media']:.4f} [{r['por_brazo'][b]['intervalo_95'][0]:.4f}; {r['por_brazo'][b]['intervalo_95'][1]:.4f}]"
        for b in brazos))


def resumen(nombre, qs):
    mostrar(nombre, original(qs, m, P, capt["pesos"], capt["n_perm"], capt["n_boot"], por_documento=False), A.BRAZOS, A.FRAGMENTOS)


print("3. ANÁLISIS POSTERIOR, NO PRE-REGISTRADO: la sensibilidad, con el confirmatorio del análisis, sus remuestreos y sus "
      "semillas, sin el "
      "análisis por documento; el p es el de la misma permutación de signos, sin Holm y sin ninguna afirmación principal nueva")
mostrar(f"con las {len(qids)} (el principal, el commiteado, para comparar)", capt["res"], A.BRAZOS, A.FRAGMENTOS)
resumen(f"(i) sin las {len(con)} con alguna coincidencia", [q for q in qids if q not in set(con)])
resumen(f"(ii) sin las {len(blandas)} con una coincidencia que no es literal (redactada o casi texto de la norma)",
        [q for q in qids if q not in set(blandas)])
