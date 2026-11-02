"""control_salidas_B64_mesa.py — Mesa, §387 (01/11/2026): las salidas del análisis y de la exactitud de cita de B6.4 contra el esperado, y
el sello de la muestra de 36 contra sus planillas. Por código y en solo lectura:
  1. el esperado (`esperado/esperado_b64.json`) da el sha256 que informó la autora, y cada clave da el sha256 de su archivo, con las
     rutas de `llenar_esperado_B64.py`; `devueltas` está vacía y no hay ningún CSV en `devueltas/`;
  2. el análisis y la exactitud: cada JSON da el sha256 que informó la autora; su código de salida es 0 y su consola nombra ese sha256;
     el esperado que cada uno guarda es el del archivo;
  3. la muestra de 36:
     - el sello da el sha256, los bytes y la hora de cada planilla;
     - las planillas tienen las columnas y los renglones de su estructura, con valores válidos;
     - los demás archivos de para_leer/ y la copia vacía siguen con el sha256 que anotó el armado;
     - la salida del cruce guarda el sello, la clave (`b491fdc5…`) y los agregados que da cada archivo.
Lee las planillas solo por código. Imprime solo OK o MAL, cuentas y sha256: ningún valor de una planilla. USD 0.
  python3 -I -B control_salidas_B64_mesa.py <repo> <fuera_del_repo> <carpeta del llenado en el paquete (analisis/ de la §384)>
"""
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

R, F, LL = (Path(x).resolve() for x in sys.argv[1:4])
A, C36 = F / "analisis_b64_corr", F / "banco_b64_control_36"
SA = A / "salidas/a"
ESP_SHA = "7b70ce7e230ff41c1dc6993677073b6b2f8da403168e6f0ee6142a9b55dffba1"
ANA_SHA = "e05110545684a7b1a68e41278e7d2137cc244e8d2c113a2e1aa8b8a405a58ae8"
EXA_SHA = "3defc8a175be0c93d89eb430001fbee9b3e884d02148a1a467e0ea69dab25c23"
CLAVE_SHA = "b491fdc593f885b31d8b40a2e45824aead92d464d9e5abb8a75df393e31a69e4"
ok = {}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
spec = importlib.util.spec_from_file_location("L", LL / "llenar_esperado_B64.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

# 1. el esperado
esp_p = A / "esperado/esperado_b64.json"
esp = json.loads(esp_p.read_text(encoding="utf-8"))
rs = L.rutas(R, F, F / "banco_b64_sp_382")
ok["1a el esperado da el sha256 que informó la autora"] = sha(esp_p) == ESP_SHA
dan = [k for k, p in rs.items() if esp.get(k) == sha(p)]
ok[f"1b cada clave da el sha256 de su archivo ({len(dan)} de {len(rs)}), y devueltas está vacía, sin ningún CSV en devueltas/"] = \
    len(dan) == len(rs) and esp.get("devueltas") == {} and L.devueltas(F) == {}
ok["1c las dos entradas de la mesa en entradas_mesa/ son las armadas en la §384"] = \
    esp["clases_documentos"] == L.CONOCIDOS["clases_documentos"] and esp["lugares"] == L.CONOCIDOS["lugares"]

# 2. el análisis y la exactitud
import subprocess  # noqa: E402
head = lambda r: hashlib.sha256(subprocess.run(["git", "--no-optional-locks", "-C", str(R), "show", f"HEAD:{r}"],  # noqa: E731
                                               capture_output=True, check=True).stdout).hexdigest()
CODIGO = {"aplicar_lectura_tolerante_b63": head("data/experiment/banco_mcp/b63/analisis/codigo/aplicar_lectura_tolerante_b63.py"),
          "juez_b63": head("data/experiment/banco_mcp/b63/v2/b2/juez_b63.py"), "mapping": head("data/experiment/ev2_juez/mapping.py")}
for nombre, p, h, cod, con in (("análisis", SA / "analisis/analisis_B64.json", ANA_SHA, "codigo_de_salida_analisis_B64.txt",
                                 "consola_analisis_B64.txt"),
                                ("exactitud", SA / "exactitud_de_cita/exactitud_de_cita_B64.json", EXA_SHA,
                                 "codigo_de_salida_exactitud_de_cita_B64.txt", "consola_exactitud_de_cita_B64.txt")):
    ok[f"2 {nombre}: da el sha256 informado, sale con 0 y su consola lo nombra"] = \
        sha(p) == h and (SA / cod).read_text().strip() == "0" and h in (SA / con).read_text(encoding="utf-8")
a = json.loads((SA / "analisis/analisis_B64.json").read_text(encoding="utf-8"))
g = a["esperado"]
con_valor = {k: v for k, v in esp.items() if not k.startswith("_")}      # sin las notas de la plantilla, que el análisis no guarda
ok[f"2 análisis: guarda las {len(con_valor)} claves del esperado, iguales, más {len(set(g) - set(esp))} sha256 de código, los de HEAD"] = \
    all(g.get(k) == v for k, v in con_valor.items()) and {k: g[k] for k in set(g) - set(esp)} == CODIGO
ent = a["entradas"]
comunes = [k for k in ent if k in esp and isinstance(esp[k], str)]
ok[f"2 análisis: las entradas que leyó dan el esperado ({len(comunes)} con sha256)"] = all(ent[k] == esp[k] for k in comunes)
x = json.loads((SA / "exactitud_de_cita/exactitud_de_cita_B64.json").read_text(encoding="utf-8"))["entradas"]
ok["2 exactitud: sus entradas dan el esperado (entrada, manifiesto, armado de la E0) y el instrumento de citas 3a58e5be…"] = \
    all(x[k] == esp[k] for k in ("entrada", "manifiesto_fuera", "armado_e0")) and x["ucita"].startswith("3a58e5be")
print("las horas del análisis:", (SA / "horas_analisis_B64.txt").read_text(encoding="utf-8").strip().replace("\n", " | "))

# 3. la muestra de 36
PL = C36 / "para_leer"
PC, PR = PL / "planilla_criterios_control_36_B64.csv", PL / "planilla_respuestas_control_36_B64.csv"
sello = (PL / "sello_control_36_B64.txt").read_text(encoding="utf-8").splitlines()
fil = {l.split("  ")[-1]: l.split("  ") for l in sello if re.match(r"[0-9a-f]{64}  ", l)}
ok["3a el sello da el sha256, los bytes y la hora de las dos planillas"] = all(
    fil[p.name][0] == sha(p) and int(fil[p.name][1]) == p.stat().st_size
    and fil[p.name][2] == time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(p.stat().st_mtime)) for p in (PC, PR))
print("el sello:", [l for l in sello if l.startswith("# sellado")], "| planillas:",
      {p.name: (sha(p)[:16], p.stat().st_size) for p in (PC, PR)})


def plegar(s):
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").replace("_", " ").split())


def leer(p):
    t = p.read_bytes().decode("utf-8-sig")
    d = ";" if t.splitlines()[0].count(";") > t.splitlines()[0].count(",") else ","
    filas = [f for f in csv.reader(io.StringIO(t), delimiter=d) if any(x.strip() for x in f)]
    return [c.strip() for c in filas[0]], [[c.strip() for c in f] for f in filas[1:]]


est = json.loads((PL / "estructura_planillas.json").read_text(encoding="utf-8"))
cc, fc = leer(PC)
cr, fr = leer(PR)
validos_c = sum(1 for f in fc if plegar((f + [""] * 8)[2]) in ("cumplido", "no cumplido")
                and all(plegar((f + [""] * 8)[i]) in ("", "si", "no") for i in (4, 5, 6)))
validos_r = sum(1 for f in fr if plegar((f + [""] * 6)[1]) in ("abstencion", "contenido") and plegar((f + [""] * 6)[2]) in ("si", "no")
                and (plegar((f + [""] * 6)[2]) == "no" or (f + [""] * 6)[3].strip()))
ok[f"3b las planillas: columnas y renglones de su estructura; valores válidos en {validos_c} de {len(fc)} criterios y {validos_r} de "
   f"{len(fr)} respuestas"] = cc == est["criterios"]["columnas"] and cr == est["respuestas"]["columnas"] \
    and [f[:2] for f in fc] == est["criterios"]["renglones"] and [f[:1] for f in fr] == est["respuestas"]["renglones"] \
    and validos_c == len(fc) == 135 and validos_r == len(fr) == 36
antes = {}
for ln in (C36 / "copia_vacia/sha256_para_leer_control_36_B64.txt").read_text(encoding="utf-8").splitlines():
    if ln and not ln.startswith("#"):
        s_, b_, n_ = ln.split("  ", 2)
        antes[n_] = s_
iguales = [n for n, s_ in antes.items() if n not in (PC.name, PR.name) and (PL / n).is_file() and sha(PL / n) == s_]
ok[f"3c los demás archivos de para_leer/ siguen con el sha256 del armado ({len(iguales)} de {len(antes) - 2})"] = \
    len(iguales) == len(antes) - 2
de_mas = sorted(str(p.relative_to(PL)) for p in PL.rglob("*") if p.is_file() and str(p.relative_to(PL)) not in antes)
print("archivos de más en para_leer/:", de_mas)
cz = json.loads((C36 / "cruce/cruce_control_36_B64.json").read_text(encoding="utf-8"))
ins = cz["insumos"]
clave_p = C36 / "clave_para_despues/clave_control_36_B64.json"
clave = json.loads(clave_p.read_text(encoding="utf-8"))
agr_p = F / "banco_b64/juez/agregados_b63_ciego.json"
ok["3d la salida del cruce guarda el sello de las planillas, la clave b491fdc5… y los agregados del sorteo"] = \
    ins["sello"] == {PC.name: sha(PC), PR.name: sha(PR)} and ins["clave_sha256"] == CLAVE_SHA == sha(clave_p) \
    and ins["agregados_sha256"] == sha(agr_p) == clave["sha256_entradas"]["banco_b64/juez/agregados_b63_ciego.json"]
print("la salida del cruce:", sha(C36 / "cruce/cruce_control_36_B64.json"))
for k, v in ok.items():
    print(("OK  " if v else "MAL ") + k)
print(f"{sum(ok.values())} de {len(ok)} controles dan")
