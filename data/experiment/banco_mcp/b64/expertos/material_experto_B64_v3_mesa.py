"""material_experto_B64_v3_mesa.py — mesa, §375 (31/10/2026), v3 de la de la §361, que lee lo aprobado tal como lo arma
`decisiones_373_mesa/aprobadas/armar_aprobadas_B64_mesa.py`. Cambia solo esto:
  · cada pregunta trae solo `id`, `pregunta`, `criterios`, `tipo`, `to` y `anclas`: la ola sale del id (`B64-O<ola>-L<lugar>`, con o sin
    `-R<n>`), y todas cuentan como aprobadas, porque el armador escribe solo las aprobadas de las cuatro revisiones selladas;
  · el sello es `sello_aprobadas_B64.txt`: sus renglones con «#» se saltean, y el primero que queda empieza con el sha256.
La muestra, la semilla, la planilla, las instrucciones y la clave, iguales a las de la v2. El encabezado de la v2 sigue.

material_experto_B64_v2_mesa.py — mesa, §360 (30/10/2026), v2 de la §361: el material de la revisión de expertos de B6.4, con el de
B6.3 como molde
(`decisiones_272_mesa/nucleo/material_experto_B63_v2_mesa.py`), para que salga en minutos apenas se selle lo aprobado. USD 0, sin API.
No imprime ninguna pregunta, criterio ni texto: solo cuentas y sha256. La mesa no abre lo que escribe.

La decisión de la autora (30/10/2026, 14:51:57; registro, §197), en lo que el script hace:
- **la muestra:** 20 de las 96 aprobadas, sorteadas con semilla y estratificadas por tipo, 7, 7 y 6, en el orden de los tipos del §3.2 del
  pre-registro: 7 de agregación, 7 de remisión y 6 de condición o excepción. La semilla, como la de B6.3:
  `random.Random(f"b64:experto:{sha256 de lo aprobado sellado}")`;
- **el material y las instrucciones, los de B6.3:**
  - una sola planilla, igual para todos los expertos (decisión de la autora del 30/10/2026, 15:01:23: se reenvía a cada uno y cada
    uno devuelve su copia): `--expertos 1`. El script admite hasta 3 copias iguales, como en B6.3;
  - el PDF y la planilla para enviar los arma la autora, fuera de la mesa, como en B6.3: el script deja los CSV y las instrucciones;
  - las columnas de B6.3. La única diferencia es que el texto que acompaña cada fila es el de todos los puntos de la pregunta: el
    ancla primero y después los otros puntos, cada uno con lo heredado y lo propio y sus páginas, desde la E0 del grafo evaluado, la
    de los 128. Una pregunta de B6.4 junta varios puntos;
  - las instrucciones de B6.3, con «el texto del punto» cambiado por «el texto de los puntos»;
  - la clave de los códigos, aparte;
- el mensaje a los expertos lo escribe la autora: el script no lo escribe.
Lo que propone la mesa: el formato de lo aprobado (CAMPOS, abajo, el molde de las olas de la generación con `aprobada`), el orden de las 20
en la planilla (una permutación con la misma semilla), los códigos E01 a E20 y el CSV con «;» y BOM, como en B6.3.
Uso:
  python3 -I -B material_experto_B64_v3_mesa.py --repo <repo> --aprobadas <json> --sello <txt> --expertos <1 a 3> --salida <carpeta nueva>
  python3 -I -B material_experto_B64_v3_mesa.py --selftest
El sello de lo aprobado es la línea de siempre: `<sha256>  <archivo>  <fecha>`.
"""
import csv
import hashlib
import io
import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

CAMPOS = {"lista": "preguntas", "id": "id", "ola": "ola", "to": "to", "tipo": "tipo", "pregunta": "pregunta", "anclas": "anclas",
          "unidad": "unidad", "rol": "rol", "criterios": "criterios", "criterio": "criterio", "cita": "cita_textual",
          "aprobada": "aprobada"}
CUOTAS = {"agregacion": 7, "remision": 7, "condicion_excepcion": 6}
APROBADAS, POR_TIPO = 96, 32
COLUMNAS = ["codigo", "pregunta", "respuesta_de_referencia", "texto_de_los_puntos", "se_puede_responder_desde_el_texto (sí / no)",
            "la_respuesta_es_correcta (sí / parcial / no)", "relevancia_nota (1 a 5)", "relevancia_puesto", "comentario"]
PUESTOS = ["cumplimiento normativo", "riesgo de crédito", "operaciones y tesorería", "auditoría interna",
           "diseño de un producto o decisión del directorio", "ninguno"]
RUBRICA = [("5", "sirve para una decisión u obligación central del puesto (un límite, un plazo o un requisito cuyo incumplimiento tiene "
                 "consecuencias)"),
           ("4", "sirve para una tarea frecuente del puesto"), ("3", "sirve, pero para una consulta ocasional"),
           ("2", "es un detalle formal o de procedimiento que el puesto rara vez consulta"),
           ("1", "no le sirve a ningún puesto de la lista")]
E0_GRAFO_EVALUADO = "data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b/chunks_{}.json"
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731


def sortear_20(preguntas, sha_aprobadas):
    """7 de agregación, 7 de remisión y 6 de condición o excepción, con la semilla; devuelve los ids en el orden de la planilla."""
    C = CAMPOS
    rng = random.Random(f"b64:experto:{sha_aprobadas}")
    elegidas = []
    for t in CUOTAS:                                   # el orden del §3.2
        ids = sorted(p[C["id"]] for p in preguntas if p[C["tipo"]] == t)
        if len(ids) < CUOTAS[t]:
            raise SystemExit(f"FRENO: lo aprobado no tiene {CUOTAS[t]} preguntas de {t}")
        elegidas += rng.sample(ids, CUOTAS[t])
    rng.shuffle(elegidas)
    return elegidas


def texto_punto(unidad, e0, n, rol):
    u = e0.get(unidad)
    if u is None:
        raise SystemExit("FRENO: un punto no está en la E0 del grafo evaluado")
    partes = [f"[heredado de {h.get('unidad_origen', '')}, p. {','.join(str(x) for x in h.get('paginas') or [])}] {h['texto'].strip()}"
              for h in (u.get("herencia") or [])]
    partes.append(f"[{unidad}, p. {','.join(str(x) for x in u.get('paginas') or [])}] {u['texto'].strip()}")
    return f"Punto {n} ({'ancla' if rol == 'ancla' else 'otro punto'}):\n" + "\n\n".join(partes)


def instrucciones() -> bytes:
    ins = ["# Instrucciones para la validación de las preguntas", "",
           "Cada fila de la planilla es una pregunta sobre la normativa del BCRA, con su respuesta de referencia (los criterios que una",
           "respuesta correcta tiene que cumplir, cada uno con la cita del texto) y el texto de los puntos de la norma en que se apoya. Le",
           "pedimos que lea cada fila solo con ese texto y complete cinco columnas:", "",
           ("1. **se_puede_responder_desde_el_texto:** «sí» si la pregunta se puede responder con el texto que acompaña la fila; "
            "si no, «no»."),
           "2. **la_respuesta_es_correcta:** si la respuesta de referencia es correcta según ese texto: «sí», «parcial» o «no».",
           "3. **relevancia_nota:** de 1 a 5, con esta escala:"]
    ins += [f"   - {n}: {t};" for n, t in RUBRICA]
    ins += ["4. **relevancia_puesto:** el puesto o la decisión a la que le sirve, de esta lista: " + "; ".join(PUESTOS[:-1]) + ". Si no le",
            "   sirve a ninguno, «ninguno».",
            "5. **comentario:** lo que quiera agregar (opcional).", "",
            ("No hace falta consultar otras fuentes: la validación es sobre el texto que acompaña cada fila. Por favor, no cambie "
             "las columnas"),
            "ni el orden de las filas.", ""]
    return "\n".join(ins).encode("utf-8")


def ola_del_id(qid):
    m = re.fullmatch(r"B64-O(\d)-L\d\d(?:-R\d)?", qid)
    if not m:
        raise SystemExit("FRENO: un id de lo aprobado no es el de un lugar")
    return int(m.group(1))


def armar(aprob_b, sello_txt, e0, n_expertos, salida):
    C = CAMPOS
    s_apr = sha(aprob_b)
    campos_sello = next((l for l in sello_txt.splitlines() if l.strip() and not l.lstrip().startswith("#")), "").split()
    if not campos_sello or campos_sello[0] != s_apr:
        raise SystemExit("FRENO: el sello no es el de lo aprobado")
    pre = json.loads(aprob_b)[C["lista"]]
    falta = [k for k in ("id", "to", "tipo", "pregunta", "anclas", "criterios") if any(C[k] not in p for p in pre)]
    if falta:
        raise SystemExit(f"FRENO: a lo aprobado le faltan campos: {falta}")
    pre = [dict(p, **{C["ola"]: ola_del_id(p[C["id"]])}) for p in pre]
    if len(pre) != APROBADAS or len({p[C["id"]] for p in pre}) != APROBADAS \
            or Counter(p[C["tipo"]] for p in pre) != Counter({t: POR_TIPO for t in CUOTAS}):
        raise SystemExit(f"FRENO: lo aprobado tiene que ser 96 preguntas aprobadas y distintas, 32 por tipo (tiene {len(pre)})")
    if n_expertos not in (1, 2, 3):
        raise SystemExit("FRENO: los expertos son de 1 a 3")
    if salida.exists():
        raise SystemExit("FRENO: la carpeta de salida ya existe")
    elegidas = sortear_20(pre, s_apr)
    por_id = {p[C["id"]]: p for p in pre}
    filas, clave = [], []
    for i, q in enumerate(elegidas, 1):
        p = por_id[q]
        cod = f"E{i:02d}"
        crit = "\n".join(f"{j}. {c[C['criterio']].strip()} (cita: «{c[C['cita']].strip()}»)" for j, c in enumerate(p[C["criterios"]], 1))
        anclas = sorted(p[C["anclas"]], key=lambda a: a.get(C["rol"]) != "ancla")      # el ancla primero, los demás en su orden
        txt = "\n\n---\n\n".join(texto_punto(a[C["unidad"]], e0, n, a.get(C["rol"])) for n, a in enumerate(anclas, 1))
        filas.append([cod, p[C["pregunta"]].strip(), crit, txt, "", "", "", "", ""])
        clave.append({"codigo": cod, "id": q, "tipo": p[C["tipo"]], "ola": p[C["ola"]], "to": p[C["to"]]})
    salida.mkdir(parents=True)
    escritos = {}
    for k in range(1, n_expertos + 1):
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        w.writerow(COLUMNAS)
        w.writerows(filas)
        b = ("﻿" + buf.getvalue()).encode("utf-8")
        (salida / f"planilla_experto_{k}.csv").write_bytes(b)
        escritos[f"planilla_experto_{k}.csv"] = sha(b)
    ib = instrucciones()
    (salida / "instrucciones_experto.md").write_bytes(ib)
    escritos["instrucciones_experto.md"] = sha(ib)
    cb = (json.dumps({"aprobadas_sha256": s_apr, "semilla": f"b64:experto:{s_apr}", "cuotas": CUOTAS, "filas": clave},
                     ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    (salida / "clave_codigos_experto.json").write_bytes(cb)
    escritos["clave_codigos_experto.json"] = sha(cb)
    (salida / "manifest.txt").write_text("".join(f"{h}  {n}\n" for n, h in sorted(escritos.items())), encoding="utf-8")
    return elegidas, escritos


def e0_del_repo(repo, tos):
    """La E0 del grafo evaluado de cada documento, leída con `git show` de HEAD."""
    e0 = {}
    for t in sorted(tos):
        r = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "show", "HEAD:" + E0_GRAFO_EVALUADO.format(t)],
                           capture_output=True)
        if r.returncode != 0:
            raise SystemExit(f"FRENO: {t} no tiene E0 del grafo evaluado en HEAD")
        e0.update({u["id"]: u for u in json.loads(r.stdout)})
    return e0


def selftest():
    import tempfile
    rng = random.Random(1)
    e0 = {f"doc{d}::u{j}": {"id": f"doc{d}::u{j}", "texto": f"TEXTO_PRUEBA_{d}_{j}", "paginas": [j],
                            "herencia": [{"unidad_origen": f"doc{d}", "paginas": [1], "texto": "HEREDADO"}] if j == 0 else []}
          for d in range(24) for j in range(8)}
    tipos = [t for t in CUOTAS for _ in range(POR_TIPO)]
    pre = []
    for i, t in enumerate(tipos):
        d = i % 24
        pre.append({"id": f"B64-O{i // 16 + 1}-L{i % 16 + 1:02d}" + ("-R1" if i % 11 == 0 else ""), "to": f"doc{d}", "tipo": t,
                    "pregunta": f"PREGUNTA_PRUEBA_{i}",
                    "anclas": [{"unidad": f"doc{(d + 1) % 24}::u{(i + 3) % 8}", "rol": "otro_punto"},
                               {"unidad": f"doc{d}::u{i % 8}", "rol": "ancla"}],
                    "criterios": [{"criterio": f"CRITERIO_{i}", "cita_textual": f"CITA_{i}", "unidad": f"doc{d}::u{i % 8}"}]})
    rng.shuffle(pre)
    def nucleo(lista):
        return (json.dumps({"preguntas": lista}) + "\n").encode()
    nb = nucleo(pre)
    sello = (f"# sello de la mesa (§373): sha256, bytes, hora y nombre del archivo de las 96 aprobadas de B6.4\n"
             f"{sha(nb)}  234798  2026-10-31 07:49:50 -0300  aprobadas_B64.json\n")
    casos = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        el, es = armar(nb, sello, e0, 3, td / "a")
        tipo_de = {p["id"]: p["tipo"] for p in pre}
        casos.append(("20, con 7 de agregación, 7 de remisión y 6 de condición o excepción",
                      len(el) == len(set(el)) == 20 and Counter(tipo_de[x] for x in el) == Counter(CUOTAS)))
        el2, es2 = armar(nb, sello, e0, 3, td / "b")
        casos.append(("determinista: la misma muestra y los mismos bytes", el == el2 and es == es2))
        q2 = nucleo(list(reversed(pre)))
        el3, _ = armar(q2, f"{sha(q2)}  x", e0, 3, td / "c")
        casos.append(("otro conjunto aprobado (otro sha256) da otra semilla", el3 != el))
        p = [(td / "a" / f"planilla_experto_{k}.csv").read_bytes() for k in (1, 2, 3)]
        casos.append(("las mismas 20 filas para cada experto", p[0] == p[1] == p[2]))
        filas = list(csv.reader(io.StringIO(p[0].decode("utf-8-sig")), delimiter=";"))
        casos.append(("la planilla: la cabecera, 20 filas, las cinco columnas del experto vacías",
                      filas[0] == COLUMNAS and len(filas) == 21 and all(f[4:] == [""] * 5 for f in filas[1:])))
        casos.append(("el texto de cada fila trae sus dos puntos, el ancla primero",
                      all(f[3].startswith("Punto 1 (ancla):") and "Punto 2 (otro punto):" in f[3] for f in filas[1:])))
        casos.append(("el CSV abre con BOM y «;»", p[0].startswith("﻿".encode("utf-8"))))
        clave = json.loads((td / "a" / "clave_codigos_experto.json").read_text())
        casos.append(("la clave: E01 a E20, con su id, su tipo y su ola (la del id), y la semilla con el sha256 de lo aprobado",
                      [f["codigo"] for f in clave["filas"]] == [f"E{i:02d}" for i in range(1, 21)]
                      and clave["semilla"] == f"b64:experto:{sha(nb)}"
                      and all(f["ola"] == int(f["id"][5]) for f in clave["filas"])))
        ins = (td / "a" / "instrucciones_experto.md").read_text()
        casos.append(("las instrucciones traen la rúbrica tal cual y no nombran el grafo, los brazos ni el agente",
                      all(t in ins for _, t in RUBRICA) and not any(x in ins.lower() for x in ("grafo", "brazo", "fragmento", "agente"))))
        cambiada = [dict(x, id="OTRO-01") if i == 0 else x for i, x in enumerate(pre)]
        tipo_mal = [dict(x, tipo="agregacion") if i == 0 and x["tipo"] != "agregacion" else x for i, x in enumerate(pre)]
        for nombre, f in (("un sello de otro archivo frena", lambda: armar(nb, "0" * 64 + "  x", e0, 3, td / "d")),
                          ("95 aprobadas frena", lambda: (lambda q: armar(q, f"{sha(q)}  x", e0, 3, td / "e"))(nucleo(pre[:-1]))),
                          ("un id que no es de un lugar frena",
                           lambda: (lambda q: armar(q, f"{sha(q)}  x", e0, 3, td / "f"))(nucleo(cambiada))),
                          ("un sello de la mesa con otro sha256 frena",
                           lambda: armar(nb, "# comentario\n" + "1" * 64 + "  234798  x  aprobadas_B64.json\n", e0, 3, td / "j")),
                          ("33 de un tipo frena", lambda: (lambda q: armar(q, f"{sha(q)}  x", e0, 3, td / "g"))(nucleo(tipo_mal))),
                          ("4 expertos frena", lambda: armar(nb, sello, e0, 4, td / "h")),
                          ("una salida que existe frena", lambda: armar(nb, sello, e0, 3, td / "a")),
                          ("un punto fuera de la E0 frena", lambda: (lambda q: armar(q, f"{sha(q)}  x", e0, 3, td / "i"))(
                              nucleo([dict(x, anclas=[{"unidad": "otro::u1", "rol": "ancla"}]) for x in pre])))):
            try:
                f()
                casos.append((nombre, False))
            except SystemExit:
                casos.append((nombre, True))
    for n, ok in casos:
        print("OK " if ok else "MAL", n)
    print(f"selftest: {sum(ok for _, ok in casos)} de {len(casos)}")
    return all(ok for _, ok in casos)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    a = lambda k: sys.argv[sys.argv.index(k) + 1]  # noqa: E731
    nb = Path(a("--aprobadas")).read_bytes()
    pre = json.loads(nb)[CAMPOS["lista"]]
    e0 = e0_del_repo(Path(a("--repo")), {x[CAMPOS["unidad"]].split("::", 1)[0] for p in pre for x in p[CAMPOS["anclas"]]})
    el, es = armar(nb, Path(a("--sello")).read_text(encoding="utf-8"), e0, int(a("--expertos")), Path(a("--salida")))
    print(f"aprobadas {sha(nb)[:16]}: las 20 sorteadas ({CUOTAS}); archivos: " + ", ".join(f"{n} {h[:12]}" for n, h in sorted(es.items())))
