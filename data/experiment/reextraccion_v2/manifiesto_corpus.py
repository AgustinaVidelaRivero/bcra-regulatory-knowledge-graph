"""
manifiesto_corpus.py — U-B5.1: carga y validación del manifiesto de corpus.

Un manifiesto (JSON en manifiestos/<nombre>.json) declara TODO lo que el
pipeline E0→E5 tenía cableado a los 5 TOs del desarrollo: la lista de TOs
(id, PDF, sha256, rol de alcance esperado, nombres de remisión), el orden de
corrida, la salida de E0 a consumir, el oráculo del censo con sus
limitaciones ex ante, los límites de la corrida y la suite de tests de
respuesta conocida. Código puro, sin LLM.

Diseño aprobado en el freno 1 de U-B5.1 (diseno_manifiesto_UB5.1.md del
paquete de revisión). Reglas duras:

  - Toda violación de validación es ErrorManifiesto con mensaje; nada sigue
    de largo (en particular, el gap de rol de alcance de un TO nuevo revienta
    ACÁ, no como línea de alcance ausente en silencio — la tabla TO→rol del
    corpus escalado la puebla B5.4, mecanismo §0.4 de su diseño).
  - El manifiesto NO transporta los miembros del rol: la fuente única sigue
    siendo esquema_v2_clases.json vía grafo_v2/code/schema.py; acá solo se
    VALIDA la consistencia (rol declarado ↔ rol del catálogo, por archivo).
  - `indice_fragmentos` es un GANCHO reservado: un eventual brazo comparativo
    en B6.3 (regla de admisibilidad de su pre-registro) necesitaría un índice
    de fragmentos sobre el corpus escalado; ese constructor declararía acá su
    configuración (p. ej. granularidad y destino) y se alimentaría de los
    mismos chunks_<to>.json de E0 que `rutas.e0_salida` ya localiza. Este
    módulo lo valida (null u objeto) y lo expone VERBATIM; NINGÚN módulo del
    pipeline lo consume todavía (cero implementación, por mandato).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent                   # reextraccion_v2/
REPO = AQUI.parents[2]                                   # raíz del repo
MANIFIESTOS_DIR = AQUI / "manifiestos"
GRAFO_V2_CODE = REPO / "data" / "experiment" / "grafo_v2" / "code"
E1_DIR = AQUI / "e1_extractor"

VERSIONES_CONOCIDAS = ("1",)

# Suites de tests de respuesta conocida registradas en código. "dev5" es la
# suite del corpus de desarrollo (ensamblar_corpus.tests_respuesta_conocida);
# un corpus sin suite declara null y el ensamblado la saltea con nota.
SUITES_TESTS = ("dev5",)


class ErrorManifiesto(ValueError):
    """Manifiesto inválido: la carga aborta con el detalle de la violación."""


class Manifiesto:
    """Manifiesto cargado y validado. Solo lectura."""

    def __init__(self, datos: dict, path: Path):
        self._d = datos
        self.path = path
        self.nombre: str = datos["nombre"]
        self.tos: list[dict] = datos["tos"]
        self.orden_corrida: list[str] = list(datos["orden_corrida"])
        self.ids: list[str] = [t["id"] for t in self.tos]
        self._por_id: dict[str, dict] = {t["id"]: t for t in self.tos}
        # U-CABLE-V3: perfil de extracción E1 del corpus. Campo OPCIONAL:
        # ausente = el perfil de desarrollo vigente (el manifiesto dev no se
        # edita); el corpus escalado declara "v3_b54".
        self.perfil_e1: str = datos.get("perfil_e1") or "produccion_dev"

    # ------------------------------ accessors ---------------------------- #
    def to_de(self, tid: str) -> dict:
        return self._por_id[tid]

    def archivo_de(self, tid: str) -> str:
        return self._por_id[tid]["archivo"]

    def pdf_de(self, tid: str) -> Path:
        return REPO / self._por_id[tid]["pdf"]

    def rol_de(self, tid: str) -> str | None:
        return self._por_id[tid]["rol_alcance"]

    @property
    def e0_salida(self) -> Path:
        return REPO / self._d["rutas"]["e0_salida"]

    @property
    def mapa_territorio(self) -> Path | None:
        m = self._d["oraculo"]["mapa_territorio"]
        return None if m is None else REPO / m

    @property
    def tiene_oraculo(self) -> bool:
        return self._d["oraculo"]["mapa_territorio"] is not None

    def limitaciones_e0(self) -> dict[tuple[str, str], dict]:
        """Limitaciones ex ante en el formato interno de e2_lib:
        (to, unidad) → {clase, cubierta_por, cita}."""
        return {
            (r["to"], r["unidad"]): {
                "clase": r["clase"],
                "cubierta_por": list(r["cubierta_por"]),
                "cita": r["cita"],
            }
            for r in self._d["oraculo"]["limitaciones_e0"]
        }

    @property
    def limites(self) -> dict:
        return self._d["limites"]

    @property
    def chequeos_hits(self) -> list[dict]:
        return self._d["limites"]["chequeos_hits"]

    @property
    def tests_respuesta_conocida(self) -> str | None:
        return self._d["tests_respuesta_conocida"]

    @property
    def sellos(self) -> dict:
        return self._d.get("sellos") or {}

    @property
    def indice_fragmentos(self):
        """GANCHO (ver docstring del módulo): se expone verbatim, sin
        interpretación alguna."""
        return self._d["indice_fragmentos"]


# ------------------------------------------------------------------------- #
# Validación                                                                 #
# ------------------------------------------------------------------------- #

def _err(msg: str) -> None:
    raise ErrorManifiesto(msg)


def _validar_roles_contra_catalogo(tos: list[dict],
                                   nombre_perfil: str = "produccion_dev") -> None:
    """Consistencia manifiesto ↔ catálogo de sujetos del PERFIL del corpus
    (fuente única: schema.py para el perfil de desarrollo; el módulo v3
    sellado, vía perfil_e1, para "v3_b54"). Solo lectura.

    Reglas del modo v3 (U-CABLE-V3, decisión 2 — el campo rol_id de un mapeo
    a clase porta un id de CLASE y se lee como «sujeto por defecto del TO»):
      - entrada con rol_id (rol A2 o clase única): rol_alcance == rol_id;
      - entrada con rol_id null y clase_ids (ri2_ci): rol_alcance declara la
        LISTA exacta de clase_ids (única forma admitida de lista);
      - TO sin entrada (huecos docvig/fimipyme y desconocidos): rol_alcance
        null obligatorio."""
    if nombre_perfil == "produccion_dev":
        if str(GRAFO_V2_CODE) not in sys.path:
            sys.path.insert(0, str(GRAFO_V2_CODE))
        from schema import ROL_POR_TO  # import diferido: solo lectura del catálogo
        rol_por_to = ROL_POR_TO
    else:
        if str(E1_DIR) not in sys.path:
            sys.path.insert(0, str(E1_DIR))
        import perfil_e1  # import diferido: candados del perfil corren acá
        rol_por_to = perfil_e1.perfil(nombre_perfil).rol_por_to

    for t in tos:
        rol_cat = rol_por_to.get(t["archivo"])
        declarado = t["rol_alcance"]
        if declarado is None and rol_cat is not None:
            _err(f"TO '{t['id']}': rol_alcance null pero el catálogo declara "
                 f"'{rol_cat.get('rol_id') or rol_cat.get('clase_ids')}' para "
                 f"{t['archivo']} — una entrada del catálogo no se silencia "
                 f"por manifiesto")
        if declarado is not None and rol_cat is None:
            _err(f"TO '{t['id']}': rol_alcance '{declarado}' declarado pero el "
                 f"catálogo del perfil '{nombre_perfil}' no declara rol para "
                 f"{t['archivo']} — o el manifiesto declara rol_alcance null o "
                 f"el TO entra al catálogo por su circuito de refinamiento")
        if declarado is not None and rol_cat is not None:
            if rol_cat.get("rol_id"):
                if declarado != rol_cat["rol_id"]:
                    _err(f"TO '{t['id']}': rol_alcance '{declarado}' ≠ rol del "
                         f"catálogo '{rol_cat['rol_id']}' para {t['archivo']}")
            else:
                # Mapeo a DOS clases (ri2_ci): la declaración es la lista exacta.
                if declarado != rol_cat.get("clase_ids"):
                    _err(f"TO '{t['id']}': rol_alcance {declarado!r} ≠ clase_ids "
                         f"del catálogo {rol_cat.get('clase_ids')!r} para "
                         f"{t['archivo']} (entrada sin rol único: se declara la "
                         f"lista exacta)")


def cargar(path: Path | str, verificar_sha: bool = True,
           validar_roles: bool = True) -> Manifiesto:
    """Carga y valida un manifiesto. `verificar_sha=False` saltea el sha256 de
    los PDFs (solo para pruebas/drys explícitos); `validar_roles=False` evita
    importar el catálogo (solo para fixtures sintéticos de selftest)."""
    path = Path(path)
    if not path.exists():
        _err(f"manifiesto inexistente: {path}")
    d = json.loads(path.read_text(encoding="utf-8"))

    # 1. versión y nombre
    if d.get("version") not in VERSIONES_CONOCIDAS:
        _err(f"version desconocida: {d.get('version')!r} (conocidas: "
             f"{VERSIONES_CONOCIDAS})")
    if not d.get("nombre"):
        _err("nombre vacío")
    if d["nombre"] != path.stem:
        _err(f"nombre '{d['nombre']}' ≠ nombre del archivo '{path.stem}'")

    # 2. tos: ids/archivos únicos, PDFs presentes, sha correcto
    tos = d.get("tos") or []
    if not tos:
        _err("lista de tos vacía")
    ids = [t["id"] for t in tos]
    if len(ids) != len(set(ids)):
        _err(f"ids de TO duplicados: {sorted({i for i in ids if ids.count(i) > 1})}")
    archivos = [t["archivo"] for t in tos]
    if len(archivos) != len(set(archivos)):
        _err("archivos de TO duplicados")
    for t in tos:
        pdf = REPO / t["pdf"]
        if not pdf.exists():
            _err(f"TO '{t['id']}': PDF inexistente: {t['pdf']}")
        if verificar_sha:
            sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
            if sha != t["sha256_pdf"]:
                _err(f"TO '{t['id']}': sha256 del PDF no coincide "
                     f"(manifiesto {t['sha256_pdf'][:12]}…, disco {sha[:12]}…)")

    # 3. orden_corrida: permutación exacta de los ids
    orden = d.get("orden_corrida") or []
    if sorted(orden) != sorted(ids) or len(orden) != len(ids):
        _err(f"orden_corrida no es permutación exacta de los ids: "
             f"orden={orden} ids={sorted(ids)}")

    # 3bis. perfil de extracción (U-CABLE-V3): campo opcional; un valor fuera
    # del registro de perfiles frena SIEMPRE (aunque validar_roles sea False:
    # es un typo del manifiesto, no una consulta al catálogo). El import es
    # barato: perfil_e1 no carga nada pesado a nivel módulo.
    nombre_perfil = d.get("perfil_e1") or "produccion_dev"
    if str(E1_DIR) not in sys.path:
        sys.path.insert(0, str(E1_DIR))
    import perfil_e1
    if nombre_perfil not in perfil_e1.PERFILES_CONOCIDOS:
        _err(f"perfil_e1 desconocido: {nombre_perfil!r} (conocidos: "
             f"{perfil_e1.PERFILES_CONOCIDOS})")

    # 4. roles contra el catálogo del perfil (fuente única)
    if validar_roles:
        _validar_roles_contra_catalogo(tos, nombre_perfil)

    # 5. oráculo y limitaciones
    ora = d.get("oraculo") or {}
    if "mapa_territorio" not in ora or "limitaciones_e0" not in ora:
        _err("bloque oraculo incompleto (mapa_territorio, limitaciones_e0)")
    if ora["mapa_territorio"] is not None \
            and not (REPO / ora["mapa_territorio"]).exists():
        _err(f"mapa_territorio inexistente: {ora['mapa_territorio']}")
    if ora["mapa_territorio"] is None and ora["limitaciones_e0"]:
        _err("limitaciones_e0 declaradas sin oráculo: una limitación del "
             "censo no tiene contra qué aplicarse con mapa_territorio null")
    ids_set = set(ids)
    for r in ora["limitaciones_e0"]:
        if r["to"] not in ids_set:
            _err(f"limitación de TO desconocido: {r['to']}")
        for k in ("unidad", "clase", "cubierta_por", "cita"):
            if k not in r:
                _err(f"limitación ({r.get('to')}, {r.get('unidad')}) sin campo '{k}'")

    # 6. límites
    lim = d.get("limites") or {}
    for k in ("tope_global_usd", "margen_unidad_usd", "estimado_usd",
              "checkpoint_cada", "chequeos_hits"):
        if k not in lim:
            _err(f"limites sin campo '{k}'")
    if sorted(lim["estimado_usd"].keys()) != sorted(ids):
        _err(f"estimado_usd debe tener clave por CADA id: "
             f"{sorted(lim['estimado_usd'].keys())} vs {sorted(ids)}")
    for tid, fases in lim["estimado_usd"].items():
        if sorted(fases.keys()) != ["e1", "e3"]:
            _err(f"estimado_usd['{tid}'] debe tener exactamente e1 y e3")
    if not set(lim["checkpoint_cada"].keys()) <= ids_set:
        _err(f"checkpoint_cada con TO desconocido: "
             f"{sorted(set(lim['checkpoint_cada']) - ids_set)}")
    for chk in lim["chequeos_hits"]:
        if chk["to"] not in ids_set:
            _err(f"chequeo de hits de TO desconocido: {chk['to']}")
        for k in ("e1_max_usd", "e3_max_usd"):
            if k not in chk:
                _err(f"chequeo de hits de '{chk['to']}' sin campo '{k}'")

    # 7. suite de tests
    suite = d.get("tests_respuesta_conocida")
    if suite is not None and suite not in SUITES_TESTS:
        _err(f"suite de tests desconocida: {suite!r} (registradas: "
             f"{SUITES_TESTS}; null = sin suite, se saltea con nota)")

    # 8. rutas y gancho
    if not (d.get("rutas") or {}).get("e0_salida"):
        _err("rutas.e0_salida ausente")
    if "indice_fragmentos" not in d:
        _err("campo indice_fragmentos ausente (gancho reservado: null u objeto)")
    if d["indice_fragmentos"] is not None \
            and not isinstance(d["indice_fragmentos"], dict):
        _err("indice_fragmentos debe ser null u objeto")

    return Manifiesto(d, path)
