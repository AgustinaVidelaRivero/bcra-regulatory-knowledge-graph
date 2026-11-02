"""llenar_esperado_B64.py — Mesa, §384 (01/11/2026): la copia llena de la plantilla de los esperados del análisis de B6.4
(`data/experiment/banco_mcp/b64/analisis/codigo/esperado_b64_plantilla.json`, en HEAD; la plantilla queda sellada con el código). Lo corre
la autora, justo antes del análisis, porque calcula el sha256 de la clave de su adjudicación, que la mesa no abre. USD 0.

Llena cada una de las 16 claves con el sha256 del archivo que el comando del análisis o el de la exactitud pasa en su argumento, con las
mismas rutas que esos comandos. Antes:
  - copia las dos entradas que armó la mesa (las clases de los documentos y los lugares) a `analisis_b64_corr/entradas_mesa/`, con su
    sha256 controlado;
  - controla los sha256 que ya se conocen: la entrada sellada, el manifiesto de lo que queda fuera (el del paso 0), el sello y la
    estructura de la adjudicación (los que controló la mesa en la §384), las dos entradas de la mesa y el armado de la E0; y el D-10 y las
    fechas, contra el manifiesto de lo que queda fuera.
`devueltas` lleva {nombre: sha256} de cada CSV que haya en `b64_material_expertos/devueltas/` en ese momento ({} si no hay ninguno).
Escribe `analisis_b64_corr/esperado/esperado_b64.json` (no pisa nada) e imprime cada clave con su sha256 y, al final, el sha256 del
JSON, que el comando del análisis y el de la exactitud reciben como segundo argumento. No imprime ningún contenido.
  python3 -I -B llenar_esperado_B64.py <repo> <fuera_del_repo> <scratchpad del análisis> <carpeta de la mesa con las dos entradas>
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

CONOCIDOS = {
    "entrada": "9064066b5caaec6b373087f37c429cbf6058ec0c07ee89a91380d8f0c040932c",
    "manifiesto_fuera": "c08a3909f8ffb5e6472486c466d6051bae3b3b20f5c601307e6a2485bb0e050b",
    "sello_planilla": "ecfd86bba85bd8f6e4ef024d59532195bbed787d95bbe04525b53d9367a952c2",
    "estructura_planilla": "220b076e4edfec9932bfbac348c72b649de703ec061d4b856c7f466614369bed",
    "clases_documentos": "74fdfbee78104d42d8e79b7e55e53f3c47d8e4b2de287c4764dfe018bb780bab",
    "lugares": "3e043e7ca75413c24d527e1d108f1db05ad08162778aee692581d4214bfdb594",
    "armado_e0": "71a9a78758b51f04b543dd14348b101e174abb4562ea3a37ebd0d86b9d791557",
}
EN_EL_MANIFIESTO = {"d10": "banco_b64/juez/d10_b63.json", "fechas": "banco_b64/resultados/real/fechas_b63.json"}
PLANTILLA = "data/experiment/banco_mcp/b64/analisis/codigo/esperado_b64_plantilla.json"
MESA = ("clases_documentos_B64.json", "lugares_B64.json")


def frena(m):
    raise SystemExit(f"FRENO: {m}")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rutas(R: Path, F: Path, SP: Path) -> dict:
    """Las rutas de los comandos del análisis y de la exactitud (corrida_analisis_B64.zsh y corrida_exactitud_de_cita_B64.zsh)."""
    H6, B = F / "analisis_b64_corr", F / "banco_b64"
    SA, PL = H6 / "salidas/a", H6 / "adjudicacion/para_leer"
    return {"entrada": R / "data/experiment/banco_mcp/b64/entrada_B64.json", "manifiesto_fuera": B / "manifiesto_fuera_B64.json",
            "agregados": SA / "aplicacion/juez_con_lectura_tolerante/agregados_b63_ciego.json",
            "agregados_tolerante": SA / "aplicacion/agregados_de_las_que_no_se_leian_b63.json",
            "veredictos_tolerante": SA / "aplicacion/veredictos_lectura_tolerante_b63.jsonl",
            "agregados_sin_lectura": SA / "aplicacion/agregados_sin_lectura_b64.json",
            "sello_planilla": PL / "sello_adjudicacion_b64.txt", "estructura_planilla": PL / "estructura_planilla_adjudicacion_b64.json",
            "clave_adjudicacion": SP / "clave_para_despues_B64/clave_adjudicacion_b64.json",
            "d10": B / "juez/d10_b63.json", "fechas": B / "resultados/real/fechas_b63.json",
            "clases_documentos": H6 / "entradas_mesa" / MESA[0], "lugares": H6 / "entradas_mesa" / MESA[1],
            "manifiesto_expertos": F / "b64_material_expertos/manifest.txt",
            "armado_e0": R / "data/experiment/tanda_final/t3/acumulado/armado_acumulado_128_tf.json"}


def devueltas(F: Path) -> dict:
    d = F / "b64_material_expertos/devueltas"
    if not d.is_dir():
        return {}
    return {p.name: sha(p) for p in sorted(d.iterdir())
            if p.is_file() and p.suffix == ".csv" and not p.name.startswith("NO_ABRIR_") and "SOLO_MESA" not in p.name}


def llenar(plantilla: dict, rs: dict, conocidos: dict, manifiesto_idx: dict, dev: dict) -> dict:
    claves = [k for k in plantilla if not k.startswith("_")]
    if sorted(claves) != sorted(list(rs) + ["devueltas"]):
        frena("las claves de la plantilla no son las rutas de los comandos más devueltas")
    out = {k: v for k, v in plantilla.items() if k.startswith("_")}
    for k in claves:
        if k == "devueltas":
            out[k] = dev
            continue
        if not Path(rs[k]).is_file():
            frena(f"falta el archivo de {k}")
        s = sha(rs[k])
        if k in conocidos and s != conocidos[k]:
            frena(f"{k} no da el sha256 que se conoce")
        if k in EN_EL_MANIFIESTO and manifiesto_idx.get(EN_EL_MANIFIESTO[k]) != s:
            frena(f"{k} no da el sha256 del manifiesto de lo que queda fuera")
        out[k] = s
    return out


def leer_plantilla(R: Path) -> dict:
    p = subprocess.run(["git", "--no-optional-locks", "-C", str(R), "show", f"HEAD:{PLANTILLA}"], capture_output=True)
    if p.returncode != 0:
        frena("la plantilla no está en HEAD")
    return json.loads(p.stdout)


def main(argv: list | None = None) -> int:
    R, F, SP, MESA_DIR = (Path(x).resolve() for x in (argv or sys.argv[1:5]))
    H6 = F / "analisis_b64_corr"
    sal, ent = H6 / "esperado" / "esperado_b64.json", H6 / "entradas_mesa"
    if sal.exists() or ent.exists():
        frena("ya existe esperado/esperado_b64.json o entradas_mesa/: no se pisa")
    plantilla = leer_plantilla(R)
    rs = rutas(R, F, SP)
    man = json.loads(rs["manifiesto_fuera"].read_bytes())
    idx = {a["ruta"]: a["sha256"] for a in man["archivos"]}
    # Primero todo en memoria, con las dos entradas de la mesa desde su carpeta: si algo frena, no se escribe nada.
    out = llenar(plantilla, rs | {"clases_documentos": MESA_DIR / MESA[0], "lugares": MESA_DIR / MESA[1]}, CONOCIDOS, idx, devueltas(F))
    ent.mkdir(parents=True)
    for n, k in zip(MESA, ("clases_documentos", "lugares")):
        shutil.copyfile(MESA_DIR / n, ent / n)
        if sha(ent / n) != out[k]:
            frena(f"la copia de {n} no da su sha256")
    sal.parent.mkdir(parents=True, exist_ok=True)
    sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k in [k for k in out if not k.startswith("_")]:
        print(f"{k}: {len(out[k])} planilla(s) devuelta(s)" if k == "devueltas" else f"{k}: {out[k]}")
    print(f"esperado_b64.json: {sha(sal)}")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
