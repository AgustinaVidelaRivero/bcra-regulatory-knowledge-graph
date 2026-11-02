"""Mesa, §322: lo que entraría al commit de las salidas sin texto de B6.3, controlado por código sin imprimir ningún texto: las claves
de cada archivo, el string más largo, si aparece la carpeta personal (en su forma con barras o con guiones) y si aparece algún tramo de
40 caracteres de una pregunta o de un criterio (leídos por código del archivo de las 96, sin imprimirlos)."""
import json, sys
from pathlib import Path
FUERA, ENT = Path(sys.argv[1]), Path(sys.argv[2])
HOME = str(Path.home())
GUION = HOME.replace("/", "-")
e = json.loads(ENT.read_text(encoding="utf-8"))
preg = json.loads(Path(e["preguntas"]["ruta"].replace("~", HOME, 1)).read_text(encoding="utf-8"))["preguntas"]
tramos = set()
for q in preg:
    for t in [q["pregunta"]] + [c["criterio"] for c in q["criterios"]] + [c["cita_textual"] for c in q["criterios"]]:
        t = " ".join(str(t).split())
        tramos |= {t[i:i + 40] for i in range(0, max(1, len(t) - 39), 20)}
RR = FUERA / "banco_b63" / "resultados" / "real"
JD = FUERA / "banco_b63" / "juez"


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def revisar(paths):
    n, larg, home, guion, texto, claves = 0, 0, 0, 0, 0, set()
    for p in paths:
        raw = p.read_text(encoding="utf-8")
        n += 1
        home += HOME in raw
        guion += GUION in raw
        o = json.loads(raw)
        if isinstance(o, dict):
            claves |= set(o)
        for s in strings(o):
            larg = max(larg, len(s))
            s2 = " ".join(s.split())
            if len(s2) >= 40 and any(s2[i:i + 40] in tramos for i in range(0, len(s2) - 39)):
                texto += 1
    return {"archivos": n, "string_mas_largo": larg, "con_la_carpeta_personal": home, "con_la_carpeta_en_guiones": guion,
            "strings_con_un_tramo_de_pregunta_criterio_o_cita": texto, "claves": sorted(claves)[:40]}


metas = sorted((RR / "pasada1").glob("*/meta_sin_texto_*.json"))
print("metas sin texto:", json.dumps(revisar(metas), ensure_ascii=False))
for n in ("estado_b63.json", "resumen_b63.json", "fechas_b63.json", "orden_b63.json", "pasada1/registro_lote.json"):
    print(n, json.dumps(revisar([RR / n]), ensure_ascii=False)[:600])
print("d10_b63.json", json.dumps(revisar([JD / "d10_b63.json"]), ensure_ascii=False)[:600])
for n in sys.argv[3:]:
    print(Path(n).name, json.dumps(revisar([Path(n)]), ensure_ascii=False)[:400])
