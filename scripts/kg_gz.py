"""
kg_gz.py — un `kg.json` comprimido de forma determinista para guardarlo en git, y su restauración con control (decisión de la autora
del 18/10/2026, hoja de ruta de la mesa, §156: el `.gz` dentro de git; manda el sha256 del `kg.json` sin comprimir, y el del `.gz` va al
lado, con el compresor y su versión).

- **comprimir <kg.json>** escribe, al lado, `kg.json.gz` y `kg.json.gz.sello.json`.
  - El contenedor gzip lo arma este script con una cabecera fija (sin nombre de archivo, con MTIME 0, XFL 2 y OS 255), el flujo deflate
    de `zlib.compressobj(9, zlib.DEFLATED, -15, 9, zlib.Z_DEFAULT_STRATEGY)`, el CRC-32 y el tamaño. No depende del módulo `gzip`, que
    cambia la cabecera entre versiones de Python.
  - El sello guarda el sha256 y los bytes del `kg.json` (el que manda), el sha256 y los bytes del `.gz`, y con qué se hizo (este script,
    sus parámetros, Python y la versión de zlib).
  - Frena si el `.gz` o el sello ya existen.
- **restaurar <kg.json.gz>** escribe el `kg.json` al lado, si no existe, y controla que su sha256 sea el del sello. Si existe y es igual,
  no hace nada; si existe y es distinto, frena sin tocarlo.
- **verificar <kg.json.gz> [--kg <kg.json>]** controla el `.gz` contra el sello y, descomprimido, el sha256 del `kg.json` del sello. Con
  `--kg`, también que ese archivo sea el del sello. No escribe nada.
USD 0, sin red. El `.gz` se lee con cualquier gzip (`gunzip`, `gzip.decompress`).
Uso: python -I -B kg_gz.py comprimir|restaurar|verificar <ruta> [--kg <ruta>]
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

FORMATO = "kg_gz/1"
PARAMETROS = {"nivel": 9, "metodo": "DEFLATED", "wbits": -15, "memLevel": 9, "estrategia": "Z_DEFAULT_STRATEGY"}
CABECERA = b"\x1f\x8b\x08\x00" + struct.pack("<I", 0) + b"\x02\xff"   # ID1 ID2 CM FLG, MTIME 0, XFL 2, OS 255


class ErrorKgGz(Exception):
    pass


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def gz_bytes(datos: bytes) -> bytes:
    c = zlib.compressobj(9, zlib.DEFLATED, -15, 9, zlib.Z_DEFAULT_STRATEGY)
    cuerpo = c.compress(datos) + c.flush()
    return CABECERA + cuerpo + struct.pack("<II", zlib.crc32(datos) & 0xFFFFFFFF, len(datos) & 0xFFFFFFFF)


def descomprimir(gz: bytes) -> bytes:
    d = zlib.decompressobj(31)                       # gzip con su cabecera y su CRC: lo controla zlib
    out = d.decompress(gz) + d.flush()
    if not d.eof or d.unused_data:
        raise ErrorKgGz("el .gz está truncado o trae bytes de más")
    return out


def rutas(kg_o_gz: Path) -> tuple[Path, Path, Path]:
    p = Path(kg_o_gz)
    kg = p.with_suffix("") if p.suffix == ".gz" else p
    gz = kg.with_name(kg.name + ".gz")
    return kg, gz, kg.with_name(kg.name + ".gz.sello.json")


def comprimir(kg_path: Path) -> dict:
    kg, gz, sello = rutas(kg_path)
    if gz.exists() or sello.exists():
        raise ErrorKgGz(f"ya existe {gz.name} o su sello: no los piso")
    datos = kg.read_bytes()
    b = gz_bytes(datos)
    if descomprimir(b) != datos:
        raise ErrorKgGz("la vuelta no da el original")
    s = {"formato": FORMATO, "kg_json": kg.name, "kg_json_sha256": sha(datos), "kg_json_bytes": len(datos),
         "gz": gz.name, "gz_sha256": sha(b), "gz_bytes": len(b),
         "compresor": {"script": "scripts/kg_gz.py", "parametros": PARAMETROS, "cabecera": CABECERA.hex(),
                       "python": sys.version.split()[0], "zlib": zlib.ZLIB_VERSION, "zlib_en_ejecucion": zlib.ZLIB_RUNTIME_VERSION},
         "manda": "kg_json_sha256: el sha256 del kg.json sin comprimir es el que controlan el cargador y la suite; el del .gz depende de "
                  "la versión de zlib y va como información"}
    gz.write_bytes(b)
    sello.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return s


def verificar(gz_path: Path, kg_extra: Path | None = None) -> dict:
    kg, gz, sello = rutas(gz_path)
    s = json.loads(sello.read_text(encoding="utf-8"))
    if s.get("formato") != FORMATO:
        raise ErrorKgGz(f"formato del sello desconocido: {s.get('formato')}")
    b = gz.read_bytes()
    if sha(b) != s["gz_sha256"] or len(b) != s["gz_bytes"]:
        raise ErrorKgGz("el .gz no es el del sello")
    datos = descomprimir(b)
    if sha(datos) != s["kg_json_sha256"] or len(datos) != s["kg_json_bytes"]:
        raise ErrorKgGz("descomprimido no da el kg.json del sello")
    if kg_extra is not None and sha(Path(kg_extra).read_bytes()) != s["kg_json_sha256"]:
        raise ErrorKgGz(f"{kg_extra} no es el kg.json del sello")
    return s


def restaurar(gz_path: Path) -> str:
    kg, gz, _ = rutas(gz_path)
    s = verificar(gz)
    if kg.exists():
        if sha(kg.read_bytes()) != s["kg_json_sha256"]:
            raise ErrorKgGz(f"{kg} existe y no es el del sello: no lo toco")
        return "ya estaba, igual al sello"
    datos = descomprimir(gz.read_bytes())
    kg.write_bytes(datos)
    if sha(kg.read_bytes()) != s["kg_json_sha256"]:
        raise ErrorKgGz("el kg.json restaurado no es el del sello")
    return "restaurado, igual al sello"


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("comprimir", "restaurar", "verificar"):
        print(__doc__)
        return 2
    try:
        if argv[0] == "comprimir":
            s = comprimir(Path(argv[1]))
            print(f"comprimido: {s['gz']} {s['gz_bytes']} bytes, sha256 {s['gz_sha256']}; kg.json {s['kg_json_sha256']}")
        elif argv[0] == "verificar":
            kg = Path(argv[argv.index("--kg") + 1]) if "--kg" in argv else None
            s = verificar(Path(argv[1]), kg)
            print(f"OK: {Path(argv[1]).name} es el del sello y da el kg.json {s['kg_json_sha256']}" + (" (también el del árbol)" if kg else ""))
        else:
            print(f"OK: {restaurar(Path(argv[1]))}")
    except (ErrorKgGz, OSError, zlib.error, json.JSONDecodeError, KeyError) as e:
        print(f"FRENO: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
