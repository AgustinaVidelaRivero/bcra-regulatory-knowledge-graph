"""U-SEG-OFICIAL, S1-quater: lo común de los scripts del diseño (mesa, 11/10/2026; USD 0, sin API).

Fijado y sellado antes de que exista la E0 corregida (decisión de la autora del 11/10/2026, punto 8; `../diseno_S1quater.md`). Lo
usan `poblaciones_S1quater.py`, `regresion_S1quater.py`, `sorteo_S1quater.py` y `fichas_S1quater.py`.

- Semillas: las dos de la nota del plan B al pie del mandato de S0-5a (`521e220a`) y la del orden de lectura, nueva, que sella este
  diseño. Cada estrato usa `random.Random(f"{SEMILLA}:{estrato}")`, como S1-ter (`s1ter/scripts/sorteo_S1ter.py`).
- La E0 vieja es la que leyó S1-ter (`s1ter/e0/`), controlada contra `s1ter/manifest_salida.json`; la nueva es la E0 corregida,
  controlada contra el manifiesto de su corrida, con el mismo formato.
- La alineación de dos segmentaciones del mismo documento (`alinear_to`) decide qué unidades de la E0 corregida ya se leyeron en
  S1-ter aunque la corrección cambie ids o cortes; ver `diseno_S1quater.md`, §3.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ESTRATOS = {"vigente": 40, "marcadores": 10, "sin_raiz": 40}
SEMILLA = "U-SEG-OFICIAL:cortes:S1-quater"                    # sellada en 521e220a
SEMILLA_REVISION = "U-SEG-OFICIAL:cortes:S1-quater:revision"  # sellada en 521e220a
SEMILLA_ORDEN = "U-SEG-OFICIAL:cortes:S1-quater:orden"        # sellada por este diseño
UMBRAL_COBERTURA = 0.95
RE_PARTE = re.compile(r"^(.*)::parte(\d+)$")
_GUION = re.compile(r"(\w)-[ \t]*\n\s*(\w)")

# Insumos de S1-ter, commiteados en 818c3a43 (el orden y el manifiesto de TOs, además, en sus sellos de S1-ter).
SHA_ORDEN_S1TER = "acd57e37c039bd17a027fbd73cd0579f9f7460f054edf8d06be4fda2144e9681"           # tramo_b/orden_lectura_S1ter.json
SHA_MANIFEST_SALIDA_S1TER = "5e63dff235326c4b2bb73cb95ca409037afa93fbb4903fe89fbd59b17dccc432"  # manifest_salida.json
SHA_MANIFIESTO_TOS_S1TER = "f59cdea0f552452957930f79c8ab8592a20ea7d24a8ae8fca270b5c5ca5113cd"   # manifiesto/…_152.json


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def leer_sellado(p: Path, esperado: str, que: str) -> bytes:
    b = Path(p).read_bytes()
    if hashlib.sha256(b).hexdigest() != esperado:
        raise SystemExit(f"FRENO: {que} no da el sha256 de su sello")
    return b


def verificar_e0(d: Path, manifest: Path, sha_manifest: str | None, que: str) -> dict:
    """Controla cada archivo `e0/…` del manifiesto (formato de `s1ter/manifest_salida.json`) contra la carpeta `d`, y que la
    carpeta no tenga archivos de más. Devuelve el manifiesto."""
    raw = leer_sellado(manifest, sha_manifest, f"el manifiesto de {que}") if sha_manifest else Path(manifest).read_bytes()
    m = json.loads(raw)
    e0 = {k[3:]: v["sha256"] for k, v in m["sha256"].items() if k.startswith("e0/")}
    if not e0:
        raise SystemExit(f"FRENO: el manifiesto de {que} no lista archivos de e0/")
    presentes = {p.name for p in Path(d).iterdir() if p.is_file() and p.name != ".DS_Store"}
    if presentes != set(e0):
        raise SystemExit(f"FRENO: la carpeta de {que} no tiene exactamente los archivos de su manifiesto")
    malos = [n for n, h in e0.items() if sha(Path(d) / n) != h]
    if malos:
        raise SystemExit(f"FRENO: {len(malos)} archivos de {que} no dan su sha256")
    return m


class E0:
    """Una salida de E0: `chunks_<to>.json` por TO, en el orden del documento."""

    def __init__(self, d: Path):
        self.d = Path(d)
        self._c: dict[str, list] = {}

    def tos(self) -> list[str]:
        return sorted(p.name[len("chunks_"):-len(".json")] for p in self.d.glob("chunks_*.json"))

    def chunks(self, to: str) -> list[dict]:
        if to not in self._c:
            self._c[to] = json.loads((self.d / f"chunks_{to}.json").read_text(encoding="utf-8"))
        return self._c[to]

    def json_de(self, nombre: str):
        return json.loads((self.d / nombre).read_text(encoding="utf-8"))

    def por_id(self, uid: str) -> dict:
        return next(c for c in self.chunks(uid.split("::")[0]) if c["id"] == uid)

    def partes(self, uid: str) -> list[dict]:
        """La unidad, o sus partes en orden si está partida por tamaño (como `fichas_S1ter.py`)."""
        L = self.chunks(uid.split("::")[0])
        exacto = [c for c in L if c["id"] == uid]
        if exacto:
            return exacto
        ps = [c for c in L if RE_PARTE.match(c["id"]) and RE_PARTE.match(c["id"]).group(1) == uid]
        if not ps:
            raise SystemExit(f"FRENO: {uid} no está en la E0")
        return sorted(ps, key=lambda c: int(RE_PARTE.match(c["id"]).group(2)))

    def siguiente(self, uid: str) -> dict | None:
        L = self.chunks(uid.split("::")[0])
        ids = [c["id"] for c in L]
        k = max(ids.index(c["id"]) for c in self.partes(uid))
        return L[k + 1] if k + 1 < len(L) else None


def tokens(texto: str) -> list[str]:
    """Tokens para alinear: une el corte de renglón con guion, saca tildes, pasa a minúsculas y deja letras y dígitos."""
    t = _GUION.sub(r"\1\2", texto or "")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)).lower()
    return re.findall(r"[0-9a-z]+", t)


def alinear_to(viejos: list[dict], nuevos: list[dict]) -> dict:
    """Alinea dos segmentaciones del mismo documento por su texto propio, sin usar los ids.

    1. Anclas: las unidades con el mismo texto propio (`sha256_propio`), en el orden del documento (SequenceMatcher sobre la
       lista de sha256).
    2. Entre dos anclas seguidas, los tokens de las unidades del medio, alineados con SequenceMatcher sin autojunk.
    Una unidad nueva solapa una vieja si comparten un ancla o un token alineado. Devuelve `solapes` ({id nuevo: [ids viejos]}),
    `cobertura` (tokens viejos alineados sobre tokens viejos) y los conteos."""
    hv = [c["sha256_propio"] for c in viejos]
    hn = [c["sha256_propio"] for c in nuevos]
    anclas = [(a + k, b + k) for a, b, n in SequenceMatcher(None, hv, hn, autojunk=False).get_matching_blocks()
              for k in range(n)]
    solapes: dict[str, set] = {c["id"]: set() for c in nuevos}
    tv = [len(tokens(c["texto"])) for c in viejos]
    alineados = 0
    for iv, i_n in anclas:
        solapes[nuevos[i_n]["id"]].add(viejos[iv]["id"])
        alineados += tv[iv]
    cortes = [(-1, -1)] + anclas + [(len(viejos), len(nuevos))]
    for (av, an), (bv, bn) in zip(cortes, cortes[1:]):
        gv, gn = viejos[av + 1:bv], nuevos[an + 1:bn]
        if not gv or not gn:
            continue
        tok_v, due_v = [], []
        for c in gv:
            t = tokens(c["texto"])
            tok_v += t
            due_v += [c["id"]] * len(t)
        tok_n, due_n = [], []
        for c in gn:
            t = tokens(c["texto"])
            tok_n += t
            due_n += [c["id"]] * len(t)
        for a, b, n in SequenceMatcher(None, tok_v, tok_n, autojunk=False).get_matching_blocks():
            for k in range(n):
                solapes[due_n[b + k]].add(due_v[a + k])
            alineados += n
    total = sum(tv)
    return {"solapes": {k: sorted(v) for k, v in solapes.items()}, "cobertura": (alineados / total) if total else 1.0,
            "tokens_viejos": total, "anclas": len(anclas)}


def mostradas_S1ter(orden: dict, viejo: E0) -> dict[str, str]:
    """Las unidades de la E0 vieja cuyo texto propio mostró una ficha de S1-ter, con la etapa: en la etapa 1, la unidad; en la
    etapa 2, la unidad (o sus partes), las unidades calificadas y la que le sigue en el documento."""
    out: dict[str, str] = {}
    for f in orden["etapa_1"]["fichas"]:
        out.setdefault(f["id"], "etapa_1")
    for f in orden["etapa_2"]["fichas"]:
        ids = [c["id"] for c in viejo.partes(f["id"])] + list(f.get("unidades_calificadas") or [])
        sig = viejo.siguiente(f["id"])
        if sig is not None:
            ids.append(sig["id"])
        for i in ids:
            out.setdefault(i, "etapa_2")
    return out


def excluir(viejo: E0, nuevo: E0, mostradas: set[str], tos: list[str]) -> dict:
    """Qué unidades de la E0 nueva ya se leyeron en S1-ter: las del mismo id que una mostrada, y las que solapan el texto
    propio de una mostrada (`alinear_to`). Frena si un TO falta en alguna de las dos o si su cobertura queda debajo del umbral."""
    faltan = [t for t in tos if not (viejo.d / f"chunks_{t}.json").exists() or not (nuevo.d / f"chunks_{t}.json").exists()]
    if faltan:
        raise SystemExit(f"FRENO: TOs sin chunks en alguna de las dos E0: {faltan}")
    excluidas: dict[str, dict] = {}
    alineacion = {}
    for t in tos:
        al = alinear_to(viejo.chunks(t), nuevo.chunks(t))
        alineacion[t] = {"cobertura": al["cobertura"], "tokens_viejos": al["tokens_viejos"], "anclas": al["anclas"]}
        for c in nuevo.chunks(t):
            sol = sorted(set(al["solapes"][c["id"]]) & mostradas)
            if c["id"] in mostradas or sol:
                excluidas[c["id"]] = {"mismo_id": c["id"] in mostradas, "solapa_con": sol}
    bajos = sorted(t for t, v in alineacion.items() if v["cobertura"] < UMBRAL_COBERTURA)
    if bajos:
        raise SystemExit(f"FRENO: la alineación cubre menos del {UMBRAL_COBERTURA:.0%} del texto viejo en {bajos}: lo decide la "
                         "autora antes de seguir")
    return {"excluidas": excluidas, "alineacion": alineacion}
