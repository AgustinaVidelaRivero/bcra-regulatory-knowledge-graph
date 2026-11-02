"""
ratchet_e3.py — Mecánica del MINI-RATCHET de E3 (T2).

Política (docs/diseno_reextraccion_v2.md §3-E3, tope resuelto para la
calibración en 1 reintento — resuelve la pregunta abierta §7.a por mandato de
esta unidad, laudable de nuevo con datos de calibración):

  veredicto E3 con faltantes
    → prompt de RE-EXTRACCIÓN: el prompt E1 del chunk, ÍNTEGRO, + bloque de
      feedback estructurado, marcado como reintento. El bloque va DESPUÉS del
      breakpoint de caché (dentro del mensaje de usuario): el prefijo E1
      (system + tools + tool_choice) queda byte-idéntico y el caching no se
      invalida — verificado en el selftest.
    → re-extracción (cliente E1) → re-validación E1 → re-verificación E3.
  tope: 1 reintento. Si persisten faltantes → el chunk va a COLA HUMANA con
  flag y TODO persistido. NUNCA ingreso silencioso al grafo.

El verificador JAMÁS corrige: este módulo solo transporta su feedback al
extractor. Todos los veredictos se persisten (RegistroE3).

Capa determinística sobre el veredicto (principio 2.b: lo mecánico va en
código, encima del juicio del LLM — mismo patrón que la capa determinística
del verificador de la Fase 2.4):
  - coherencia veredicto/faltantes (completo_ok ⇔ faltantes vacío);
  - verificación de cada cita textual contra el fuente real de la unidad
    (normalización del precedente C7). Una cita que NO verifica no se inyecta
    al reintento (una cita fabricada envenenaría la re-extracción); queda
    registrada. Si NINGÚN faltante BLOQUEANTE tiene cita verificada, el
    veredicto es inutilizable para el ratchet y el chunk va a cola humana con
    flag propio.

LAUDOS POST-MINI-RECALIBRACIÓN (2026-08-11; E3 congelado — el prompt del
verificador NO cambia, solo esta capa determinística):

  LAUDO A — política de aceptación por severidad: SOLO los faltantes de
  severidad 'alta' bloquean (disparan reintento o cola). Los media/baja se
  PERSISTEN como residuales declarados por unidad y la unidad se ACEPTA con
  residuales (estados nuevos: aceptado_con_residuales; los aceptados tras
  reintento también portan sus residuales). Motivación medida: en la
  mini-recalibración, 18 de las 22 unidades de cola tenían SOLO faltantes
  media/baja en su último veredicto — blanco móvil del verificador, no
  amputaciones que cambien una respuesta regulatoria.

  LAUDO B — guardia estructural de bloques ordenadores: en un MINI-CHUNK
  cuyo texto cierra abriendo una enumeración (última línea no vacía que
  termina en ':') y cuya unidad de origen tiene unidades descendientes en el
  corpus, un faltante `enumeracion_incompleta` cuya cita (verificada) es esa
  cláusula ordenadora se marca `estructural_no_bloqueante` y NO bloquea: los
  ítems de la enumeración SON los puntos hijos, que el mini no ve por diseño
  (caso caracterizado pro::2.7::intro). Queda registrado en el veredicto.
  La condición de descendencia exige el set de unidades del corpus
  (`unidades_corpus`); si no se provee, la guardia no se aplica (falla hacia
  bloquear, nunca hacia aceptar de más).

  ENMIENDA A LAUDO B (docs/enmienda_laudo_B_guarda_ratchet_2026-10-03.md,
  firmada en 0061244; implementada en U-PROMPT-R2, P2): con la forma de salida
  «r2» (marca forma_salida en la validación verificada, que pone validador_e1
  en el perfil r2b) y si esa validación quedó sin Obligacion, Restriccion ni
  Potestad, la guardia cubre cualquier faltante cuya cita verificada sea la
  cláusula ordenadora, sea cual sea su tipo. Las demás condiciones no cambian.
  Sin la marca (perfiles existentes) la guardia es la de LAUDO B tal cual. El
  faltante eximido se marca estructural_no_bloqueante, como siempre; el reporte
  de la corrida lista como exenciones de la ampliación las de tipo distinto de
  enumeracion_incompleta.

  U-PROMPT-R2, P3b (decisiones de la autora en el FRENO P3b-1, 023f9a0), solo con la forma de salida «r2»:
  - j (hallazgo 2.2): un `faltantes` que llega como texto se lee en código, con reparo (el objeto JSON entero,
    la lista, o el primer valor JSON con el veredicto del resto), y el veredicto lleva la marca de cómo se leyó
    (`lectura_faltantes`);
  - k4 (hallazgo 2.14): la unidad aceptada tras un reintento con menos entidades o relaciones que la primera
    extracción se acepta con la marca `reintento_con_menos_elementos`;
  - copia de la nota de E3: el feedback del reintento avisa que las notas no son texto de la norma (defensa 1),
    y después de la re-extracción se marcan, sin rechazar, las entidades cuya descripción o etiqueta lleva texto
    de una nota ausente de la unidad (defensa 2, `copia_nota_e3`, también en copias_nota_e3.jsonl);
  - el `todo` de cola_humana.jsonl dice que la unidad entra al grafo marcada (decisión de la autora del
    04/10/2026).
  Las marcas van en la validación (`marcas_e3`), que llega a finales.jsonl.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import comun_e3
from comun_e3 import cita_en_fuente, normalizar_para_cita
import prompt_e3
import cliente_e3

import prompt_e1      # módulos de E1: solo import (mecánica de re-inyección)
import validador_e1
import cliente_e1

TOPE_REINTENTOS = 1

SEVERIDAD_BLOQUEANTE = ("alta",)   # LAUDO A: media/baja son residuales

ESTADOS = ("completo_ok_directo", "aceptado_con_residuales",
           "aceptado_tras_reintento",
           "cola_humana", "cola_humana_veredicto_inutilizable",
           "cola_humana_reextraccion_invalida")

MARCA_REINTENTO = "# REINTENTO DE EXTRACCIÓN — feedback del verificador de completitud (E3)"

# P3b, defensa 1 (texto aprobado en el FRENO P3b-1): solo con la forma r2.
AVISO_NOTA_REINTENTO = ("Las notas del verificador explican qué falta y por qué; no son texto de la norma: no copies "
                        "sus palabras en descripciones, etiquetas ni tramos. Todo lo que extraigas sale del texto de "
                        "la unidad.")
# P3b, defensa 2: la regla de la medida de P3b-1 (p3b/lazo_e3_p3b.py): tokens de R-NORM, ventana de 5.
VENTANA_COPIA_NOTA = 5
_RE_VEREDICTO_EN_TEXTO = re.compile(r'"veredicto"\s*:\s*"([a-z_]+)"')


def _forma_r2(validacion: dict | None) -> bool:
    return isinstance(validacion, dict) and validacion.get("forma_salida") == "r2"


def _validador_r2():
    """R-NORM y el texto de la unidad de validador_r2 (pyd_r2/code), sin duplicarlos; solo con la forma r2."""
    code = str(Path(__file__).resolve().parents[2] / "pyd_r2" / "code")
    if code not in sys.path:
        sys.path.insert(0, code)
    import validador_r2  # noqa: PLC0415
    return validador_r2


def copias_nota(validacion: dict, faltantes: list[dict], chunk: dict) -> list[dict]:
    """P3b, defensa 2: entidades de la re-extracción cuya descripción o etiqueta tiene una ventana de
    VENTANA_COPIA_NOTA tokens de R-NORM que está en la `nota` de un faltante del feedback y no está ni en el texto de
    la unidad (propio y heredado) ni en las citas de esos faltantes. Marca; no rechaza ni corrige."""
    V = _validador_r2()

    def ventanas(t) -> set[tuple[str, ...]]:
        toks = V.norm_tokens(t or "")
        return {tuple(toks[i:i + VENTANA_COPIA_NOTA]) for i in range(len(toks) - VENTANA_COPIA_NOTA + 1)}
    notas = [f.get("nota") or "" for f in faltantes]
    if not notas:
        return []
    citas = " \n ".join(f.get("cita_textual_del_fuente") or "" for f in faltantes)
    de_la_nota = set().union(*(ventanas(n) for n in notas)) - ventanas(V.texto_completo(chunk)) - ventanas(citas)
    out = []
    for e in validacion.get("entidades") or []:
        campos = {}
        for campo, txt in (("descripcion", (e.get("properties") or {}).get("descripcion")), ("label", e.get("label"))):
            comunes = ventanas(txt) & de_la_nota if isinstance(txt, str) else set()
            if comunes:
                campos[campo] = sorted(" ".join(w) for w in comunes)[:5]
        if campos:
            out.append({"indice_crudo": e.get("indice_crudo"), "local_id": e.get("local_id"), "type": e.get("type"),
                        "campos": campos})
    return out


def leer_faltantes_texto(texto: str, veredicto_arriba) -> tuple[object, object, str]:
    """P3b, j: (faltantes, veredicto, lectura) de un `faltantes` que llegó como texto, con la regla de la medida de
    P3b-1 (p3b/lazo_e3_p3b.py). El texto se lee con `json.loads` («json») o, si no, con su primer valor JSON
    («reparo», `raw_decode`); si nada se lee, «no_se_lee». Un objeto con `faltantes` trae el veredicto entero (vale
    el suyo, o el de arriba); una lista son los faltantes (vale el veredicto de arriba y, con reparo y sin él, el
    que sigue en el texto)."""
    t = texto.lstrip()
    try:
        v, lectura, resto = json.loads(texto), "json", ""
    except json.JSONDecodeError:
        try:
            v, fin = json.JSONDecoder().raw_decode(t)
        except json.JSONDecodeError:
            return None, veredicto_arriba, "no_se_lee"
        lectura, resto = "reparo", t[fin:]
    if isinstance(v, dict) and "faltantes" in v:
        return v.get("faltantes"), v.get("veredicto") or veredicto_arriba, lectura
    if isinstance(v, list):
        m = _RE_VEREDICTO_EN_TEXTO.search(resto)
        return v, veredicto_arriba or (m.group(1) if m else None), lectura
    return None, veredicto_arriba, "no_se_lee"


# ------------------------------------------------------------------------- #
# Capa determinística sobre el veredicto del LLM                             #
# ------------------------------------------------------------------------- #

def _bloque_abre_enumeracion(chunk: dict) -> bool:
    """LAUDO B, condición textual: la última línea no vacía del texto del
    mini-chunk termina en ':' (u su variante de dos puntos ancho)."""
    lineas = [l.strip() for l in chunk.get("texto", "").split("\n") if l.strip()]
    return bool(lineas) and lineas[-1].rstrip().endswith((":", "："))


def _origen_tiene_descendientes(chunk: dict, unidades_corpus: set[str]) -> bool:
    """LAUDO B, condición estructural: la unidad de origen del mini tiene
    unidades descendientes en el corpus (los ítems de la enumeración viven en
    los hijos). Para secciones ('S3') el prefijo de descendencia es '3.'."""
    u = chunk["unidad"]
    pref = (u[1:] + ".") if u.startswith("S") else (u + ".")
    return any(x.startswith(pref) for x in unidades_corpus)


TIPOS_SALVAGUARDA_AMPLIACION = ("Obligacion", "Restriccion", "Potestad")


def ampliacion_activa(validacion: dict | None) -> bool:
    """Enmienda a LAUDO B: la ampliación rige con la forma de salida «r2» y solo si la extracción verificada
    quedó sin Obligacion, Restriccion ni Potestad (salvaguarda). Sin validación, o sin la marca, no rige."""
    if not isinstance(validacion, dict) or validacion.get("forma_salida") != "r2":
        return False
    return not any(isinstance(e, dict) and e.get("type") in TIPOS_SALVAGUARDA_AMPLIACION
                   for e in validacion.get("entidades") or [])


def _guardia_estructural(f: dict, chunk: dict,
                         unidades_corpus: set[str] | None, ampliada: bool = False) -> bool:
    """LAUDO B: ¿este faltante es estructural_no_bloqueante? Exige: mini-chunk
    ordenador (':' final) + descendientes en el corpus + tipo
    enumeracion_incompleta + cita verificada que ES la cláusula ordenadora
    (normalizada, termina en ':' y está contenida en el bloque). Sin
    `unidades_corpus` la guardia no aplica (falla hacia bloquear)."""
    if unidades_corpus is None or chunk.get("tipo") != "mini_chunk":
        return False
    if (not ampliada and f.get("tipo") != "enumeracion_incompleta") or not f.get("cita_verificada"):
        return False
    if not _bloque_abre_enumeracion(chunk):
        return False
    if not _origen_tiene_descendientes(chunk, unidades_corpus):
        return False
    cita_n = normalizar_para_cita(f.get("cita_textual_del_fuente") or "")
    return cita_n.endswith(":") and cita_n in normalizar_para_cita(chunk["texto"])


def evaluar_veredicto(tool_input, chunk: dict,
                      unidades_corpus: set[str] | None = None,
                      validacion: dict | None = None) -> dict:
    """Evalúa determinísticamente el tool input del verificador: coherencia
    del contrato + verificación de citas contra el fuente + política de
    severidad (LAUDO A) + guardia estructural (LAUDO B y su enmienda: la
    ampliación rige según `validacion`, la extracción verificada). No juzga
    contenido (eso es del LLM): juzga formato, anclaje y bloqueo."""
    ampliada = ampliacion_activa(validacion)
    ev = {
        "veredicto_crudo": tool_input,
        "es_completo_ok": False,
        "faltantes": [],               # todos, cada uno con cita_verificada
        "faltantes_utilizables": [],   # solo los de cita verificada
        "faltantes_bloqueantes": [],   # LAUDO A/B: alta y no estructural
        "bloqueantes_utilizables": [],  # bloqueantes con cita verificada
        "residuales": [],              # media/baja + estructural_no_bloqueante
        "incoherencias": [],
        "aceptable": False,            # coherente y sin faltantes bloqueantes
    }
    if not isinstance(tool_input, dict):
        ev["incoherencias"].append("tool_input_no_dict")
        return ev

    veredicto = tool_input.get("veredicto")
    faltantes = tool_input.get("faltantes")
    if isinstance(faltantes, str) and _forma_r2(validacion):
        # P3b, j: el veredicto llegó como texto dentro de `faltantes`; se lee en código y se marca cómo.
        leidos, ver_leido, lectura = leer_faltantes_texto(faltantes, veredicto)
        ev["lectura_faltantes"] = lectura
        if leidos is not None:
            faltantes, veredicto = leidos, ver_leido
    if not isinstance(faltantes, list):
        faltantes = []
        ev["incoherencias"].append("faltantes_no_lista")

    if veredicto == "completo_ok" and faltantes:
        ev["incoherencias"].append("completo_ok_con_faltantes")
    if veredicto == "faltantes_detectados" and not faltantes:
        ev["incoherencias"].append("faltantes_detectados_sin_faltantes")
    if veredicto not in ("completo_ok", "faltantes_detectados"):
        ev["incoherencias"].append(f"veredicto_invalido:{veredicto}")

    # Conservador: solo es completo_ok un veredicto coherente y sin faltantes.
    ev["es_completo_ok"] = (veredicto == "completo_ok" and not faltantes
                            and not ev["incoherencias"])

    for f in faltantes:
        if not isinstance(f, dict):
            ev["incoherencias"].append("faltante_no_dict")
            continue
        cita = f.get("cita_textual_del_fuente") or ""
        f_ev = dict(f)
        f_ev["cita_verificada"] = cita_en_fuente(cita, chunk, _forma_r2(validacion))
        f_ev["estructural_no_bloqueante"] = _guardia_estructural(
            f_ev, chunk, unidades_corpus, ampliada)
        # LAUDO A: solo 'alta' bloquea; LAUDO B la exime si es estructural.
        f_ev["bloqueante"] = (f_ev.get("severidad") in SEVERIDAD_BLOQUEANTE
                              and not f_ev["estructural_no_bloqueante"])
        ev["faltantes"].append(f_ev)
        if f_ev["cita_verificada"]:
            ev["faltantes_utilizables"].append(f_ev)
        if f_ev["bloqueante"]:
            ev["faltantes_bloqueantes"].append(f_ev)
            if f_ev["cita_verificada"]:
                ev["bloqueantes_utilizables"].append(f_ev)
        else:
            ev["residuales"].append(f_ev)

    # Aceptable: veredicto coherente sin faltantes bloqueantes (los residuales
    # se declaran, no bloquean). Un veredicto incoherente jamás es aceptable.
    ev["aceptable"] = (not ev["incoherencias"]
                       and not ev["faltantes_bloqueantes"]
                       and veredicto in ("completo_ok", "faltantes_detectados"))
    return ev


# ------------------------------------------------------------------------- #
# Prompt de re-extracción: prompt E1 del chunk + feedback, tras el breakpoint #
# ------------------------------------------------------------------------- #

def bloque_feedback(faltantes: list[dict], intento: int, forma_r2: bool = False) -> str:
    """Bloque de feedback estructurado que se anexa al MENSAJE DE USUARIO del
    request E1 (después del breakpoint de caché). Solo faltantes con cita
    verificada entran acá."""
    partes = [
        MARCA_REINTENTO,
        f"(reintento {intento} de {TOPE_REINTENTOS})",
        "",
        "Un verificador de completitud, en contexto independiente, comparó tu "
        "extracción anterior de este chunk contra el texto fuente y detectó "
        "contenido normativo NO representado:",
        "",
    ]
    for i, f in enumerate(faltantes, 1):
        partes.append(
            f"{i}. [{f.get('tipo', 'otro')} | ubicación: {f.get('ubicacion', '?')} "
            f"| severidad: {f.get('severidad', '?')}]"
        )
        partes.append(f"   Cita del fuente no representada: «{f.get('cita_textual_del_fuente', '')}»")
        nota = f.get("nota")
        if nota:
            partes.append(f"   Nota: {nota}")
    partes += [
        "",
        "Re-extraé el chunk COMPLETO desde cero (no solo lo faltante), con todas "
        "las reglas del sistema vigentes, asegurando que cada cita señalada quede "
        "representada: en la descripcion de una entidad, como entidad propia "
        "(p. ej. una Excepcion) o como relación, según corresponda al schema. "
        "No inventes contenido que el fuente no sostiene.",
    ]
    if forma_r2:
        partes += ["", AVISO_NOTA_REINTENTO]
    return "\n".join(partes)


def build_reextraccion_kwargs(chunk: dict, faltantes: list[dict], model: str,
                              intento: int = 1,
                              max_tokens_reintento: int | None = None,
                              perfil=None) -> dict:
    """Request de re-extracción: el request E1 canónico del chunk con el
    bloque de feedback ANEXADO al mensaje de usuario. El prefijo (system +
    tools + tool_choice) queda byte-idéntico al de la primera pasada: el
    feedback vive después del breakpoint y no invalida el caché.

    max_tokens_reintento: techo de salida SOLO para el reintento (el request
    base de E1 está sellado con su techo propio y no se toca). Un reintento
    que COMPLETA una extracción incompleta puede necesitar más salida que la
    primera pasada. Cambiar max_tokens no invalida la caché de prompts de la API
    (no integra el prefijo), pero sí la caché local: su clave incluye max_tokens.

    perfil (U-CABLE-V3): perfil E1 de la corrida (perfil_e1.PerfilE1). El
    reintento debe construirse con el MISMO prefijo que la fase E1 de su
    corrida (en una corrida v3, re-extraer con el prefijo dev mezclaría
    prefijos dentro de la unidad). None = prompt_e1 de producción dev, byte a
    byte el comportamiento sellado."""
    _build = prompt_e1.build_request_kwargs if perfil is None \
        else perfil.build_request_kwargs
    kwargs = _build(chunk, model=model)
    if max_tokens_reintento is not None:
        kwargs["max_tokens"] = max_tokens_reintento
    forma_r2 = perfil is not None and getattr(perfil.esquema, "forma_salida", "v3") == "r2"
    mensaje = kwargs["messages"][0]["content"] + "\n\n" + bloque_feedback(faltantes, intento, forma_r2)
    kwargs["messages"] = [{"role": "user", "content": mensaje}]
    return kwargs


def reextraer_chunk(cliente_extractor, chunk: dict, faltantes: list[dict],
                    model: str, intento: int = 1,
                    max_tokens_reintento: int | None = None,
                    perfil=None) -> dict:
    """Ejecuta la re-extracción con el cliente E1 inyectado (stub u real) y
    devuelve el tool input crudo + la re-validación E1. `perfil` (U-CABLE-V3):
    ver build_reextraccion_kwargs; la re-validación usa el esquema del perfil
    (None = validación de producción dev, byte-idéntica)."""
    kwargs = build_reextraccion_kwargs(chunk, faltantes, model=model, intento=intento,
                                       max_tokens_reintento=max_tokens_reintento,
                                       perfil=perfil)
    if isinstance(cliente_extractor, cliente_e1.ClienteE1Real):
        resp = cliente_extractor.create(doc=chunk["archivo"], **kwargs)
    else:
        resp = cliente_extractor.messages.create(**kwargs)

    tool_use = None
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            tool_use = block
            break
    tool_input = tool_use.input if tool_use is not None else None
    esquema = None if perfil is None else perfil.esquema
    validacion = (validador_e1.validar_salida(tool_input, chunk,
                                              esquema=esquema).as_dict()
                  if tool_input is not None else None)
    return {
        "chunk_id": chunk["id"],
        "intento": intento,
        "tool_input": tool_input,
        "validacion": validacion,
        "error": None if tool_use is not None else "no_tool_use",
    }


# ------------------------------------------------------------------------- #
# Persistencia: todos los veredictos + cola humana con flag y TODO           #
# ------------------------------------------------------------------------- #

class RegistroE3:
    """Persistencia append-only de la corrida: veredictos.jsonl (TODOS los
    veredictos, incluidas re-verificaciones) y cola_humana.jsonl (chunks
    flaggeados con su TODO)."""

    def __init__(self, dir_salida: Path):
        self.dir = Path(dir_salida)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path_veredictos = self.dir / "veredictos.jsonl"
        self.path_cola = self.dir / "cola_humana.jsonl"
        self.path_copias_nota = self.dir / "copias_nota_e3.jsonl"   # P3b, solo forma r2 y solo si hay casos

    def _append(self, path: Path, reg: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

    def veredicto(self, reg: dict) -> None:
        self._append(self.path_veredictos, reg)

    def copia_nota(self, chunk_id: str, copias: list[dict]) -> None:
        self._append(self.path_copias_nota, {"chunk_id": chunk_id, "entidades": copias})

    def cola_humana(self, chunk_id: str, estado: str, evaluacion: dict, forma_r2: bool = False) -> None:
        pendientes = [
            {"tipo": f.get("tipo"), "cita": f.get("cita_textual_del_fuente"),
             "ubicacion": f.get("ubicacion"), "severidad": f.get("severidad"),
             "cita_verificada": f.get("cita_verificada")}
            for f in evaluacion.get("faltantes", [])
        ]
        self._append(self.path_cola, {
            "chunk_id": chunk_id,
            "flag": estado,
            "faltantes_pendientes": pendientes,
            "incoherencias": evaluacion.get("incoherencias", []),
            "todo": (
                f"TODO: revisión humana del chunk {chunk_id} — faltantes "
                f"persistentes tras {TOPE_REINTENTOS} reintento(s) del "
                f"mini-ratchet E3; el chunk NO ingresa al grafo hasta resolución."
            ) if not forma_r2 else (
                f"TODO: revisión humana del chunk {chunk_id} — el mini-ratchet E3 no "
                f"terminó la unidad ({estado}); entra al grafo con la marca "
                f"cola_humana y se revisa por la muestra de cada tanda."
            ),
        })


# ------------------------------------------------------------------------- #
# Ciclo completo del mini-ratchet para una unidad                            #
# ------------------------------------------------------------------------- #

def ciclo_ratchet(chunk: dict, validacion: dict, *, cliente_verificador,
                  cliente_extractor, model_e3: str, model_e1: str,
                  registro: RegistroE3 | None = None,
                  max_tokens_reintento: int | None = None,
                  unidades_corpus: set[str] | None = None,
                  perfil=None) -> dict:
    """Ejecuta el ciclo E3 completo de una unidad:

      verificación → (si faltantes BLOQUEANTES) re-extracción con feedback →
      re-validación E1 → re-verificación E3 → aceptación o cola humana.

    Política de aceptación (LAUDO A): solo los faltantes 'alta' bloquean; una
    unidad con solo media/baja (o estructurales del LAUDO B) se acepta con
    esos faltantes declarados en `residuales`. El feedback del reintento
    lleva SOLO los bloqueantes con cita verificada (los residuales se
    declaran, no se pagan). `unidades_corpus` habilita la guardia B.

    Devuelve el expediente completo (auditable). La extracción que sobrevive
    (original o re-extraída) queda en `validacion_final`; si el estado es de
    cola humana, `validacion_final` es None: el ratchet no acepta ninguna
    extracción. Qué entra al grafo lo decide la cadena de ensamblado: en las
    cadenas r1 y r2 entra el primer intento, marcado `cola_humana`
    (decisión de la autora del 04/10/2026; runner_corpus.entrada_r2).
    Con la forma r2, las marcas de P3b van en `marcas_e3` del expediente y de
    la validación final."""

    def _persistir_veredicto(fase: str, intento: int, crudo: dict, ev: dict) -> None:
        if registro is not None:
            registro.veredicto({
                "chunk_id": chunk["id"], "fase": fase, "intento": intento,
                "tool_input": crudo["tool_input"], "error": crudo["error"],
                "es_completo_ok": ev["es_completo_ok"],
                "aceptable": ev["aceptable"],
                "n_faltantes": len(ev["faltantes"]),
                "n_faltantes_utilizables": len(ev["faltantes_utilizables"]),
                "n_bloqueantes": len(ev["faltantes_bloqueantes"]),
                "n_residuales": len(ev["residuales"]),
                "incoherencias": ev["incoherencias"],
                "faltantes": ev["faltantes"],
                **({"lectura_faltantes": ev["lectura_faltantes"]} if "lectura_faltantes" in ev else {}),
            })

    def _aceptar(estado: str, ev: dict, val: dict, feedback: list[dict] | None = None) -> dict:
        expediente["estado"] = estado
        expediente["validacion_final"] = val
        expediente["residuales"] = ev["residuales"]
        if forma_r2:
            # P3b: las marcas de la unidad (j, k4 y la copia de la nota) viajan en la validación final.
            marcas: dict = {}
            lecturas = [{"fase": "verificacion" if i == 0 else "re_verificacion", "intento": i,
                         "lectura": v["lectura_faltantes"]}
                        for i, v in enumerate(expediente["veredictos"]) if "lectura_faltantes" in v]
            if lecturas:
                marcas["lectura_veredicto_e3"] = lecturas
            if estado == "aceptado_tras_reintento":
                n = {k: [len(validacion.get(k) or []), len(val.get(k) or [])] for k in ("entidades", "relaciones")}
                if any(b < a for a, b in n.values()):
                    marcas["reintento_con_menos_elementos"] = n
                copias = copias_nota(val, feedback or [], chunk)
                if copias:
                    marcas["copia_nota_e3"] = copias
                    if registro is not None:
                        registro.copia_nota(chunk["id"], copias)
            if marcas:
                expediente["marcas_e3"] = marcas
                expediente["validacion_final"] = {**val, "marcas_e3": marcas}
        return expediente

    expediente: dict = {"chunk_id": chunk["id"], "veredictos": [],
                        "reintentos": [], "residuales": []}
    forma_r2 = _forma_r2(validacion)

    # --- Verificación inicial -------------------------------------------- #
    crudo1 = cliente_e3.verificar_chunk(cliente_verificador, chunk, validacion, model=model_e3)
    ev1 = evaluar_veredicto(crudo1["tool_input"], chunk, unidades_corpus, validacion)
    _persistir_veredicto("verificacion", 0, crudo1, ev1)
    expediente["veredictos"].append(ev1)

    if ev1["es_completo_ok"]:
        return _aceptar("completo_ok_directo", ev1, validacion)
    if ev1["aceptable"]:
        # LAUDO A/B: sin bloqueantes — se acepta con residuales declarados.
        return _aceptar("aceptado_con_residuales", ev1, validacion)

    validacion_actual = validacion
    ev_actual = ev1
    for intento in range(1, TOPE_REINTENTOS + 1):
        if not ev_actual["bloqueantes_utilizables"]:
            # Bloqueantes sin ninguna cita verificable: inutilizable para el
            # ratchet — no se re-extrae sobre citas fabricadas.
            expediente["estado"] = "cola_humana_veredicto_inutilizable"
            expediente["validacion_final"] = None
            if registro is not None:
                registro.cola_humana(chunk["id"], expediente["estado"], ev_actual, forma_r2)
            return expediente

        # --- Re-extracción con feedback (después del breakpoint) --------- #
        # Solo los bloqueantes con cita verificada entran al feedback.
        feedback = ev_actual["bloqueantes_utilizables"]
        reex = reextraer_chunk(cliente_extractor, chunk,
                               feedback,
                               model=model_e1, intento=intento,
                               max_tokens_reintento=max_tokens_reintento,
                               perfil=perfil)
        expediente["reintentos"].append(reex)
        if reex["error"] is not None or reex["validacion"] is None or any(
                r["nivel"] == "chunk" for r in reex["validacion"]["rechazos"]):
            expediente["estado"] = "cola_humana_reextraccion_invalida"
            expediente["validacion_final"] = None
            if registro is not None:
                registro.cola_humana(chunk["id"], expediente["estado"], ev_actual, forma_r2)
            return expediente

        # --- Re-verificación E3 sobre la nueva extracción ----------------- #
        validacion_actual = reex["validacion"]
        crudo_n = cliente_e3.verificar_chunk(cliente_verificador, chunk,
                                             validacion_actual, model=model_e3)
        ev_actual = evaluar_veredicto(crudo_n["tool_input"], chunk, unidades_corpus, validacion_actual)
        _persistir_veredicto("re_verificacion", intento, crudo_n, ev_actual)
        expediente["veredictos"].append(ev_actual)

        if ev_actual["es_completo_ok"] or ev_actual["aceptable"]:
            return _aceptar("aceptado_tras_reintento", ev_actual, validacion_actual, feedback)

    # --- Tope agotado con bloqueantes: cola humana, jamás ingreso silencioso #
    expediente["estado"] = "cola_humana"
    expediente["validacion_final"] = None
    if registro is not None:
        registro.cola_humana(chunk["id"], "cola_humana", ev_actual, forma_r2)
    return expediente
