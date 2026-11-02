"""por_pregunta_y_sensibilidad_B64_mesa.py — Mesa, §393 (01/11/2026): B6.4 y las coincidencias del grafo con sus criterios. ANÁLISIS
POSTERIOR, NO PRE-REGISTRADO, sin Holm ni ninguna afirmación principal nueva. USD 0.
  1. El análisis de B6.4 otra vez, sobre la copia de la reproducción de la §387 (el código copiado de `analisis_b64_corr/codigo/`,
     controlado contra `lista_H6_corr.txt`, y los clones de HEAD), con los mismos argumentos que en la §389. Se frena en la primera
     llamada a `confirmatorio` (la del escenario principal), después de calcularla con el código del análisis, y se controla que su
     resultado sea, valor por valor, el `confirmatorio.principal` de `analisis_B64.json` de `C` (`e0511054…`).
  2. De la métrica del escenario principal: en cada pregunta de B6.4 con alguna coincidencia, las correctas sobre las contadas de cada
     brazo (los cuatro) y su d en cada comparación principal (kg contra cada sistema por fragmentos).
  3. La sensibilidad, con el mismo `confirmatorio`, los mismos remuestreos y las mismas semillas, sin el análisis por documento: la media
     de d de cada comparación principal, con su intervalo del 95 % y el p de la misma permutación de signos, y la fidelidad de
     cada brazo con su intervalo, (i) sin las preguntas con alguna coincidencia y (ii) sin las que
     tienen una coincidencia que no es literal (redactada o casi texto de la norma) (las clases de `las_15_coincidencias.json`).
Imprime solo ids, cuentas y cifras.
  python3 -I -B por_pregunta_y_sensibilidad_B64_mesa.py <repro de la §387> <fuera_del_repo> <repo> <trabajo, que no existe> <las_15…json>
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

RP, F, R, T, J = (Path(x).resolve() for x in sys.argv[1:6])
C = "c190505c3ac63bf9d7cf51b94e3be04358cd7832"
assert not T.exists(), "FRENO: el trabajo ya existe"
H6, SA = F / "analisis_b64_corr", F / "analisis_b64_corr/salidas/a"
CA = RP / "clon_head_analisis_B64/data/experiment"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
lista = (H6 / "lista_H6_corr.txt").read_text(encoding="utf-8")
assert all(f"{sha(p)}  {p.stat().st_size}  codigo/{p.name}" in lista for p in (RP / "codigo").glob("*") if p.is_file()), \
    "FRENO: el código de la copia no es el de la lista"
os.environ["B64_CODIGO_B63"] = str(CA / "banco_mcp/b63/analisis/codigo")
spec = importlib.util.spec_from_file_location("analizar_b64", RP / "codigo/analizar_b64.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class Alto(Exception):
    pass


original = B.confirmatorio
capt = {}


def envoltura(qids, m, P, n_perm=B.N_PERM, n_boot=B.N_BOOT, por_documento=True, **kw):
    capt.update(qids=qids, m=m, P=P, n_perm=n_perm, n_boot=n_boot, res=original(qids, m, P, n_perm, n_boot, por_documento, **kw))
    raise Alto


B.confirmatorio = envoltura
args = ["--clon", CA / "banco_mcp/b63/v2/b2", "--entrada", R / "data/experiment/banco_mcp/b64/entrada_B64.json",
        "--manifiesto-fuera", F / "banco_b64/manifiesto_fuera_B64.json", "--banco-b64", F / "banco_b64",
        "--agregados", SA / "aplicacion/juez_con_lectura_tolerante/agregados_b63_ciego.json",
        "--agregados-tolerante", SA / "aplicacion/agregados_de_las_que_no_se_leian_b63.json",
        "--veredictos-tolerante", SA / "aplicacion/veredictos_lectura_tolerante_b63.jsonl",
        "--agregados-sin-lectura", SA / "aplicacion/agregados_sin_lectura_b64.json",
        "--planilla", H6 / "adjudicacion/para_leer/planilla_adjudicacion_b64.csv",
        "--sello-planilla", H6 / "adjudicacion/para_leer/sello_adjudicacion_b64.txt",
        "--estructura-planilla", H6 / "adjudicacion/para_leer/estructura_planilla_adjudicacion_b64.json",
        "--clave-adjudicacion", F / "banco_b64_sp_382/clave_para_despues_B64/clave_adjudicacion_b64.json",
        "--d10", F / "banco_b64/juez/d10_b63.json", "--fechas", F / "banco_b64/resultados/real/fechas_b63.json",
        "--clases-documentos", H6 / "entradas_mesa/clases_documentos_B64.json", "--lugares", H6 / "entradas_mesa/lugares_B64.json",
        "--expertos", F / "b64_material_expertos", "--esperado", H6 / "esperado/esperado_b64.json", "--salida", T / "analisis"]
try:
    B.main([str(x) for x in args])
except Alto:
    pass
B.confirmatorio = original
assert capt, "FRENO: el análisis no llegó al confirmatorio"
norm = lambda x: json.loads(json.dumps(x, sort_keys=True))  # noqa: E731
cb = subprocess.run(["git", "--no-optional-locks", "-C", str(R), "show",
                     f"{C}:data/experiment/banco_mcp/b64/analisis/salidas/a/analisis/analisis_B64.json"],
                    capture_output=True, check=True).stdout
assert hashlib.sha256(cb).hexdigest().startswith("e0511054")
igual = norm(capt["res"]) == norm(json.loads(cb)["confirmatorio"]["principal"])
print(f"1. B6.4 otra vez, sobre la copia de la §387, hasta el confirmatorio principal: {len(capt['qids'])} preguntas; {capt['n_perm']} "
      f"permutaciones y {capt['n_boot']} remuestreos; las semillas {B.SEMILLAS['bootstrap']} y {B.SEMILLAS['permutacion']}; "
      f"el confirmatorio "
      f"principal es, valor por valor, el de analisis_B64.json de C (e0511054…): {igual}")
assert igual, "FRENO: el confirmatorio principal no es el commiteado"
m, P, qids = capt["m"], capt["P"], capt["qids"]
fil = json.loads(J.read_text(encoding="utf-8"))["coincidencias"]
con = sorted({r["pregunta"] for r in fil if r["fuente"] == "B6.4"})
blandas = sorted({r["pregunta"] for r in fil if r["fuente"] == "B6.4" and r["clase"] != "texto de la norma"})
print(f"2. ANÁLISIS POSTERIOR, NO PRE-REGISTRADO. Las {len(con)} preguntas de B6.4 con alguna coincidencia, en el escenario principal:")
for q in con:
    clases = sorted({r["clase"] for r in fil if r["pregunta"] == q})
    por = "; ".join(f"{b} {m[(q, b)][0]} de {m[(q, b)][1]}" if (q, b) in m else f"{b} sin corridas contadas" for b in B.BRAZOS)
    ds = "; ".join(f"kg − {f} {B.d6(m, q, x, y) / 6:+.4f}" for f, (x, y) in B.COMPARACIONES.items() if (q, x) in m and (q, y) in m)
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
    mostrar(nombre, original(qs, m, P, capt["n_perm"], capt["n_boot"], por_documento=False), B.BRAZOS, B.COMPARACIONES)


print("3. ANÁLISIS POSTERIOR, NO PRE-REGISTRADO: la sensibilidad, con el confirmatorio del análisis, sus remuestreos y sus "
      "semillas, sin el "
      "análisis por documento; el p es el de la misma permutación de signos, sin Holm y sin ninguna afirmación principal nueva")
mostrar(f"con las {len(qids)} (el principal, el commiteado, para comparar)", capt["res"], B.BRAZOS, B.COMPARACIONES)
resumen(f"(i) sin las {len(con)} con alguna coincidencia", [q for q in qids if q not in set(con)])
resumen(f"(ii) sin las {len(blandas)} con una coincidencia que no es literal (redactada o casi texto de la norma)",
        [q for q in qids if q not in set(blandas)])
