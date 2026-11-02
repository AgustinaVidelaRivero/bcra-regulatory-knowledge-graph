"""Censos complementarios de S0-3 (USD 0, solo lectura de las corridas de E0).
Uso: python -B censos_complementarios.py <dir base> <dir final> <dir tanda0 base> <dir censos>
1. Apartados de un nivel dentro de una sección (vigente y marcadores): rótulos «1.», «2.», … consecutivos desde 1,
   rechazados por fuera_de_seccion_N o profundidad_1_es_seccion, por sección y página.
2. Formas de la intro de los puntos que cambia el mecanismo 4 (intro de la corrida final que termina con el texto de
   la intro de la base): termina en dos puntos; un renglón sin dos puntos; varios renglones.
3. Raíces del modo sin raíz rechazadas por la guarda de columna (G3) que suceden exactamente a la última raíz abierta
   en una página anterior o la misma (aproximación por página)."""
import json, re, sys, collections
from pathlib import Path
sys.dont_write_bytecode = True
base, final, t0, dc = map(Path, sys.argv[1:5])

def apartados(d):
    out = []
    for p in sorted(d.glob("estructura_*.json")):
        e = json.loads(p.read_text())
        if e.get("modo_lectura") == "sin_raiz":
            continue
        sinp = {s["numero"] for s in e["secciones"] if not s["hijos"]}
        rech = collections.defaultdict(list)
        for r in e["rechazos_header"]:
            m = re.match(r"^(\d+)\.\s+(\S.*)$", r["texto"])
            mo = re.match(r"^(fuera_de_seccion_|profundidad_1_es_seccion)(.*)$", r["motivo"])
            if m and mo:
                sec = mo.group(2) if mo.group(1).startswith("fuera") else None
                rech[(sec, r["pagina"])].append((int(m.group(1)), r["texto"][:50]))
        for (sec, pag), xs in rech.items():
            nums = [n for n, _ in xs]
            if len(nums) >= 2 and nums[0] == 1 and all(b == a + 1 for a, b in zip(nums, nums[1:])):
                out.append({"to": e["to"], "seccion": sec, "pagina": pag, "seccion_sin_puntos": bool(sec in sinp),
                            "rotulos": [t for _, t in xs]})
    return out

ap152, apt0 = apartados(base), apartados(t0)
sec_sinp = sorted({(a["to"], a["seccion"]) for a in ap152 if a["seccion_sin_puntos"]})
sec_conp = sorted({(a["to"], a["seccion"]) for a in ap152 if not a["seccion_sin_puntos"]})
(dc / "apartados_un_nivel_en_seccion.json").write_text(json.dumps({
    "criterio": __doc__.split("\n")[3].strip(),
    "152": {"listas": len(ap152), "secciones_sin_puntos": [list(x) for x in sec_sinp],
            "secciones_con_puntos": [list(x) for x in sec_conp], "detalle": ap152},
    "tanda0": {"listas": len(apt0), "detalle": apt0}}, ensure_ascii=False, indent=1) + "\n")
print("apartados: 152", len(ap152), "listas;", len(sec_sinp), "secciones sin puntos en", len({t for t, _ in sec_sinp}),
      "TOs;", len(sec_conp), "secciones con puntos en", len({t for t, _ in sec_conp}), "TOs; tanda0", len(apt0))

formas = collections.Counter(); ej = collections.defaultdict(list)
for p in sorted(final.glob("chunks_*.json")):
    to = p.name[len("chunks_"):-5]
    b = {c["id"]: c for c in json.loads((base / p.name).read_text())}
    for c in json.loads(p.read_text()):
        if c["tipo"] == "mini_chunk" and c["rol_bloque"] == "intro" and c["id"] in b \
                and c["texto"] != b[c["id"]]["texto"] and c["texto"].endswith(b[c["id"]]["texto"]):
            antes = b[c["id"]]["texto"]
            k = ("termina_en_dos_puntos" if antes.rstrip().endswith(":") else
                 "un_renglon_sin_dos_puntos" if len(antes.split("\n")) == 1 else "varios_renglones")
            formas[k] += 1; ej[k].append(c["id"])
(dc / "m4_formas_de_la_intro.json").write_text(json.dumps({"total": sum(formas.values()), "por_forma": dict(formas),
    "tos": len({i.split("::")[0] for v in ej.values() for i in v}), "ids": ej}, ensure_ascii=False, indent=1) + "\n")
print("m4:", sum(formas.values()), dict(formas))

g3 = []
for p in sorted(final.glob("estructura_*.json")):
    e = json.loads(p.read_text())
    if e.get("modo_lectura") != "sin_raiz":
        continue
    raices = sorted(((s["pagina"], int(s["numero"])) for s in e["secciones"] if s["numero"].isdigit()))
    for r in e["rechazos_header"]:
        m = re.match(r"raiz_en_columna_profunda_([\d.]+)_vs_([\d.]+)", r["motivo"])
        if not m:
            continue
        n = int(re.match(r"^(\d+)", r["texto"]).group(1))
        prev = [k for pg, k in raices if pg <= r["pagina"]]
        if n == (max(prev) if prev else 0) + 1:
            g3.append({"to": e["to"], "pagina": r["pagina"], "pt_mas_adentro": round(float(m.group(1)) - float(m.group(2)), 1),
                       "texto": r["texto"][:70]})
(dc / "g3_raices_sucesoras_rechazadas.json").write_text(json.dumps({"candidatos": len(g3),
    "tos": sorted({x["to"] for x in g3}), "detalle": g3}, ensure_ascii=False, indent=1) + "\n")
print("g3:", len(g3), "en", len({x["to"] for x in g3}), "TOs")
