"""selftest_kg_gz.py — el selftest de scripts/kg_gz.py (hoja de ruta de la mesa, §156). USD 0, sin red, en una carpeta temporal.
Uso: python -I -B selftest_kg_gz.py"""
import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("kg_gz", AQUI / "kg_gz.py")
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)
res = []


def check(nombre, cond):
    res.append((nombre, bool(cond)))
    print(("OK  " if cond else "FAIL"), nombre)


def frena(f, *a):
    try:
        f(*a)
    except K.ErrorKgGz:
        return True
    return False


with tempfile.TemporaryDirectory(prefix="selftest_kg_gz_") as t:
    T = Path(t)
    datos = json.dumps({"nodes": [{"id": f"n{i}", "label": "Á" * (i % 7)} for i in range(5000)], "edges": []}, ensure_ascii=False).encode()
    a, b = T / "a", T / "b"
    a.mkdir()
    b.mkdir()
    (a / "kg.json").write_bytes(datos)
    (b / "kg.json").write_bytes(datos)
    s1, s2 = K.comprimir(a / "kg.json"), K.comprimir(b / "kg.json")
    check("1 dos compresiones dan los mismos bytes", (a / "kg.json.gz").read_bytes() == (b / "kg.json.gz").read_bytes())
    check("2 el sello guarda el sha256 del kg.json y el del .gz", s1["kg_json_sha256"] == K.sha(datos) and s1["gz_sha256"] == K.sha((a / "kg.json.gz").read_bytes()))
    check("3 gzip.decompress de la biblioteca da el original", gzip.decompress((a / "kg.json.gz").read_bytes()) == datos)
    g = subprocess.run(["gunzip", "-c", str(a / "kg.json.gz")], capture_output=True)
    check("4 gunzip da el original", g.returncode == 0 and g.stdout == datos)
    check("5 la cabecera es la fija (sin nombre, MTIME 0, OS 255)", (a / "kg.json.gz").read_bytes()[:10] == K.CABECERA)
    check("6 comprimir otra vez frena (no pisa)", frena(K.comprimir, a / "kg.json"))
    check("7 verificar da OK, también contra el kg.json", K.verificar(a / "kg.json.gz", a / "kg.json")["kg_json_sha256"] == K.sha(datos))
    (a / "kg.json").unlink()
    check("8 restaurar escribe el kg.json igual al original", K.restaurar(a / "kg.json.gz").startswith("restaurado") and (a / "kg.json").read_bytes() == datos)
    check("9 restaurar con el kg.json igual no hace nada", K.restaurar(a / "kg.json.gz").startswith("ya estaba"))
    (a / "kg.json").write_bytes(datos + b" ")
    check("10 restaurar con un kg.json distinto frena y no lo toca", frena(K.restaurar, a / "kg.json.gz") and (a / "kg.json").read_bytes() == datos + b" ")
    check("11 verificar contra un kg.json distinto frena", frena(K.verificar, a / "kg.json.gz", a / "kg.json"))
    gzb = (b / "kg.json.gz").read_bytes()
    (b / "kg.json.gz").write_bytes(gzb[:-9] + bytes([gzb[-9] ^ 1]) + gzb[-8:])
    check("12 un .gz cambiado frena", frena(K.verificar, b / "kg.json.gz"))
    (b / "kg.json.gz").write_bytes(gzb[:-20])
    sb = json.loads((b / "kg.json.gz.sello.json").read_text())
    sb["gz_sha256"], sb["gz_bytes"] = K.sha(gzb[:-20]), len(gzb) - 20
    (b / "kg.json.gz.sello.json").write_text(json.dumps(sb))
    try:
        K.verificar(b / "kg.json.gz")
        trunc = False
    except (K.ErrorKgGz, Exception):
        trunc = True
    check("13 un .gz truncado frena aunque el sello lo acompañe", trunc)
    (b / "kg.json.gz").write_bytes(gzb)
    sb["gz_sha256"], sb["gz_bytes"], sb["kg_json_sha256"] = K.sha(gzb), len(gzb), "0" * 64
    (b / "kg.json.gz.sello.json").write_text(json.dumps(sb))
    check("14 un sello con otro sha256 del kg.json frena", frena(K.verificar, b / "kg.json.gz"))
    r = subprocess.run([sys.executable, "-I", "-B", str(AQUI / "kg_gz.py"), "verificar", str(a / "kg.json.gz")], capture_output=True, text=True)
    check("15 la línea de comandos: verificar da 0 y OK", r.returncode == 0 and r.stdout.startswith("OK"))
    r = subprocess.run([sys.executable, "-I", "-B", str(AQUI / "kg_gz.py"), "verificar", str(b / "kg.json.gz")], capture_output=True, text=True)
    check("16 la línea de comandos: un sello malo da 1 y FRENO", r.returncode == 1 and r.stdout.startswith("FRENO"))
ok = sum(1 for _, c in res if c)
print(f"selftest_kg_gz: {ok}/{len(res)} {'OK' if ok == len(res) else 'FAIL'}")
sys.exit(0 if ok == len(res) else 1)
