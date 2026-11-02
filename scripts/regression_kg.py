#!/usr/bin/env python3
"""regression_kg.py — U-B2.1 fase 2: regression suite del grafo de conocimiento.

Convierte cada uno de los 46 ítems del inventario de la fase 1
(reports/revision_UB21_diag/inventario_B21_fase1.md, §2; partición 19
convertibles / 23 con condición / 4 no convertibles según
tabla_resumen_B21_fase1.md §1) en un test de respuesta conocida ejecutable
sobre cualquier kg.json, y produce la tabla defecto → estado por grafo con
tres estados posibles: resuelto / persiste / no_aplicable.

Decisiones vinculantes (docs/mandatos/UB21_fase2_regression_suite.md):
  1. Direccionamiento sin ids de contenido: (archivo del TO, punto ∈ conjunto
     de provenances, tipo, cadena normalizada en label o properties) o id de
     catálogo de Sujetos. Nunca provenance[0] ni id de nodo de contenido.
  2. Adaptador de provenance propio: gen 2 lee {source_doc, location}
     («Punto 1.2.» → 1.2); gen 3 lee provenances[].archivo / .punto. La
     cuarentena se normaliza a booleano en las dos generaciones (gen 2 guarda
     un booleano; r1_tests.py:68 compara con la cadena "true"). No comparte
     código con scripts/shapes_validator.py.
  3. Política de cuarentena por generación: --politica-cuarentena laudada
     espera subclase_de desde los propuestos (KG-Refinado, laudo C4);
     flaggeada espera padre_sugerido (r1, T7).
  4. Rank (RK) solo con el retriever in-memory GraphIndex de
     data/experiment/evaluacion/harness.py (importado, no copiado), cargado
     con loader.load_graph_from_path(path, adapter_key=None). Cada consulta
     declara su limite (≥ rank esperado; tope 50 del harness). La forma
     «posición en ver_vecinos» (C4 paso e) se reduce a arista presente.
  5. RT-C5-1..4, RT-C6-1..3 y RT-C7-1..3 entran solo como tests de valor.
     RT-C5-5 es no_aplicable cuando el grafo no tiene nodos con punto 7.2 de
     Clasificación (gen 3).
  6/6bis. Salida .md + .json por grafo; la regresión se computa contra la
     fixture scripts/regression_kg_esperado.json (estado medido ≠ esperado),
     nunca contra la corrida anterior. Código de salida ≠ 0 solo con
     regresión; «persiste» esperado no es fallo.
  7. Catálogo leído del artefacto (--catalogo), nunca copiado.
  8. T4 lee el esqueleto del grafo de referencia (--esqueleto-referencia)
     excluyendo las aristas con rol_fuente cuarentena_laudada.
     REEMPLAZADA por R-T4 (U-R2-CODIGO, R5.a; D1 de U-PRE-R2-DIAG, propuesta
     A): T4 compara el esqueleto del grafo con el que
     assemble.build_skeleton construye sobre el catálogo de --catalogo.
     --esqueleto-referencia queda en la interfaz y no lo usa ningún ítem.

Perfil r2 (U-R2-CODIGO, R5; enmienda 1 al mandato, R5.b). Con --perfil r2:
  - la remisión entre puntos es `remite_a`; T5 y el test del ejemplo la leen
    con scripts/remisiones.py, que reconoce las dos formas;
  - T5 por contenido (R-T5), E4-a8 sobre la tabla e4_propuestos.json del
    ensamblado bajo prueba (R-E4a8), BKL-0028 contra los tres ids «del
    exterior» esperados, BKL-0006 y BKL-0023 con la lista de umbrales y
    direccionados por punto y monto (cap 1.2, Restriccion, valor normalizado
    de la lista), sin exigir la frase «exigencia básica»;
  - ítems nuevos fuera de la partición de 46 (ITEMS_R2): el test del ejemplo
    `cla::5.1.1.1` y LN-1 a LN-8 (diseño de U-LISTAS-NOMAP, §g);
  - censos informativos, fuera de los ítems y de la fixture: aristas entre dos
    nodos con la misma descripción y remisiones por firma y por alcance.

U-REEXT-T0, T1, punto 4 (mandato firmado en e2027dd), ítems fuera de la
partición de 46 (ITEMS_UREEXT):
  - T6 y E4-b leen los TOs del manifiesto del grafo bajo prueba (--manifiesto,
    o el `manifiesto.path` del reporte de su ensamblado); sin manifiesto, los
    cinco TOs de desarrollo, como antes;
  - BKL-0001 (cap 2.8.3.3) y BKL-0002 (ext 3.5.3), tests por punto como T1;
  - FIRMAS-condicion_de: las dos firmas nuevas y 0 relaciones no verificadas
    por E3 (L-ESQ-R2 §6.5);
  - SIN-VERIF-E3: cero elementos de extracción sin verificar, con la cola
    humana aparte (FRENO P3 de U-PROMPT-R2, A3); no_aplicable en r2a;
  - ID-<id>: una entrada por cada id nuevo del catálogo r2 (L-ESQ-R2 §7.5),
    con su lectura de la tanda 0 en DEF_IDS_NUEVOS.

Estados: resuelto = la comprobación del ítem se cumple sobre el grafo;
persiste = no se cumple (el defecto está presente); no_aplicable = la
precondición del ítem no se da en este grafo (objeto o capa ausente cuya
ausencia no es el defecto) o el ítem no es observable sobre un kg.json.
Nunca hay PASS vacuo: una comprobación sin objeto sobre el que aplicar es
no_aplicable, con la razón.

Interfaz:
  python3 scripts/regression_kg.py --kg RUTA --generacion {2,3} --catalogo RUTA
      --politica-cuarentena {laudada,flaggeada} [--esperado RUTA]
      [--esqueleto-referencia RUTA] [--out RUTA.md] [--manifiesto RUTA]
  Sin --out no escribe nada. Sin --esperado reporta estados y no computa
  regresión. --solo ID[,ID] (opcional, para el selftest y depuración) corre un
  subconjunto de ítems.

Intérprete: los tests de E4 y T4/T6 importan r1_e4 / e2_lib / schema
(pydantic): correr con .venv/bin/python3 y PYTHONDONTWRITEBYTECODE=1. El
módulo en sí solo importa stdlib (los imports pesados son diferidos), para
que scripts/selftest_regression_kg.py corra con cualquier python3.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, OrderedDict
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
import remisiones  # noqa: E402  scripts/remisiones.py, solo stdlib (enmienda 1, R5.a)

# --------------------------------------------------------------------------- #
# Rutas y constantes                                                           #
# --------------------------------------------------------------------------- #
RAIZ = Path(__file__).resolve().parent.parent
CORPUS_V2 = RAIZ / "data" / "experiment" / "reextraccion_v2" / "corpus_v2"
E2_REDUCE = RAIZ / "data" / "experiment" / "reextraccion_v2" / "e2_reduce"
EVALUACION = RAIZ / "data" / "experiment" / "evaluacion"
GRAFO_V2_CODE = RAIZ / "data" / "experiment" / "grafo_v2" / "code"
MUESTRA30 = CORPUS_V2 / "salida_r1" / "referencias_muestra30_inspeccionada_A2.json"
SHA_MUESTRA30 = "4dbc2d306df867dedc4464c54b56bf6f7224ee6d820577ffe83141b6cbba8da4"
E4_PROPUESTOS_R1 = CORPUS_V2 / "salida_r1" / "e4_propuestos.json"
E4_PROPUESTOS_NOMBRE = "e4_propuestos.json"           # R-E4a8: junto al kg.json bajo prueba
PYD_R2_CODE = RAIZ / "data" / "experiment" / "pyd_r2" / "code"
ENUMS_R2 = RAIZ / "data" / "experiment" / "pyd_r2" / "generados" / "enums_r2.json"
CATALOGO_UNICO = RAIZ / "data" / "experiment" / "catalogo_unico"
CATALOGO_SUJETOS_R2 = CATALOGO_UNICO / "catalogo_sujetos_r2.json"
GENERADOS_R2 = CATALOGO_UNICO / "generados_r2"
LECTURA_MATRIZ = RAIZ / "reports" / "u_estudio_matriz" / "lectura"
LECTURA_MATRIZ_CSV = ("uestmat_muestra_60_leida.csv", "uestmat_muestra_complementaria_leida.csv")
REGISTRO_NO_MAPEADOS = "no_mapeados_sujetos.jsonl"
RESOLUCION_SUJETOS = "resolucion_sujetos.jsonl"
PERFILES = ("existente", "r2")
# U-REEXT-T0, T1, punto 4.a: el manifiesto del grafo bajo prueba se lee del reporte de su ensamblado
# (`manifiesto.path`) cuando --manifiesto no lo da; sin ninguno de los dos, los cinco TOs de desarrollo de E0.
REPORTES_ENSAMBLADO = ("reporte_ensamblado_r2.json", "reporte_ensamblado_r1.json", "reporte_ensamblado.json")
DEFAULT_ESQUELETO_REF = RAIZ / "data" / "experiment" / "grafo_v2" / "reensamblado_v3" / "kg.json"

ESTADOS = ("resuelto", "persiste", "no_aplicable")
LIMITE_DEFAULT = 10          # corte de los retests («en top-10»)
TOPE_HARNESS = 50            # harness.py:159
POLITICAS = ("laudada", "flaggeada")

CLA, CAP, PRO, RIC, EXT = ("TO_clasificacion", "TO_capitales", "TO_proteccion",
                           "TO_regimen_informativo", "TO_exterior")
TO_PREFIJO = {"pro": PRO, "cla": CLA, "ric": RIC, "cap": CAP, "ext": EXT}

RE_PUNTO = re.compile(r"punto\s+(\d+(?:\.\d+)*)")
RE_MONTO = re.compile(r"(?<![\d.])(5\.000|2\.500)(?![\d.])")

NOTA_SIN_APLICACION = "defecto confirmado, no corrección aplicada"

# Partición de la tabla resumen §1 (tabla_resumen_B21_fase1.md:14-16).
CONVERTIBLES = ("BKL-0017", "BKL-0006", "BKL-0023", "BKL-0004", "BKL-0003", "BKL-0005",
                "BKL-0007", "RT-C5-4", "RT-C5-5", "RT-C6-4", "RT-C7-1", "RT-C7-2",
                "RT-C7-3", "T1", "T2", "T3", "I3", "I4", "I5")
CON_CONDICION = ("BKL-0019", "BKL-0028", "BKL-0029", "RT-C5-1", "RT-C5-2", "RT-C5-3",
                 "RT-C6-1", "RT-C6-2", "RT-C6-3", "T4", "T5", "T6", "T7",
                 "E4-a1", "E4-a2", "E4-a3", "E4-a4", "E4-a5", "E4-a6", "E4-a7", "E4-a8",
                 "E4-b", "E4-c")
NO_CONVERTIBLES = ("BKL-0026", "BKL-0027", "I1", "I2")
# Ítems del perfil r2 (U-R2-CODIGO), fuera de los 46 del inventario de la fase 1
# y de su partición: RT-C6-5, la cláusula de mutuales como test (R4.d); el
# test del ejemplo cla::5.1.1.1 y LN-1 a LN-8 (R5.a).
ITEMS_LN = tuple(f"LN-{i}" for i in range(1, 9))
# U-REEXT-T0, T1, punto 4 (mandato firmado en e2027dd), fuera de la partición de 46: los tests por punto de BKL-0001
# y BKL-0002 (f), la entrada de las dos firmas nuevas de condicion_de (c), el control de cero elementos sin verificar
# por E3 (e) y una entrada por cada id nuevo decidido del catálogo r2 (d).
ITEMS_PUNTO = ("BKL-0001", "BKL-0002")
IDS_NUEVOS_R2 = ("Sujeto_entidad_financiera_del_exterior", "Sujeto_banco_del_exterior",
                 "Sujeto_entidad_cambiaria_del_exterior", "Sujeto_titular_de_cuenta_corriente_en_el_bcra",
                 "Sujeto_instancia_de_gobierno_societario", "Sujeto_directorio", "Sujeto_alta_gerencia",
                 "Sujeto_comite_de_auditoria")
ITEMS_ID = tuple("ID-" + i.removeprefix("Sujeto_") for i in IDS_NUEVOS_R2)
ITEMS_UREEXT = ITEMS_PUNTO + ("FIRMAS-condicion_de", "SIN-VERIF-E3") + ITEMS_ID
ITEMS_R2 = ("RT-C6-5", "EJ-cla-5.1.1.1") + ITEMS_LN + ITEMS_UREEXT
# Dependen del retriever (tabla_resumen_B21_fase1.md:20).
RETRIEVER = ("BKL-0017", "BKL-0019", "BKL-0004", "BKL-0003", "BKL-0005",
             "RT-C5-1", "RT-C5-2", "RT-C5-3", "RT-C5-4",
             "RT-C6-1", "RT-C6-2", "RT-C6-3", "RT-C7-1", "RT-C7-2", "RT-C7-3")


# --------------------------------------------------------------------------- #
# Utilidades                                                                    #
# --------------------------------------------------------------------------- #
def sha256_path(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_canonico(obj) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def norm(s) -> str:
    """NFD sin diacríticos, comillas tipográficas → rectas, minúsculas,
    espacios colapsados (misma normalización que las sondas del re-diagnóstico,
    reports/revision_UB21_diag/sonda_anclas_C1_C7_UB21.py:57-61)."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    return re.sub(r"\s+", " ", s.lower()).strip()


def _vals(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _vals(v)
    elif isinstance(o, list):
        for v in o:
            yield from _vals(v)
    else:
        yield str(o)


def texto(n: dict) -> str:
    """label + todos los valores de properties, normalizados (cadena
    normalizada «en label o properties», decisión 1)."""
    return norm(" | ".join([n.get("label") or ""] + list(_vals(n.get("properties") or {}))))


def prop(n: dict, k: str):
    return (n.get("properties") or {}).get(k)


# =========================================================================== #
# ADAPTADOR DE PROVENANCE (decisión 2) — módulo propio de la suite            #
# =========================================================================== #
def provenances(o: dict) -> list:
    """Conjunto completo de provenances de un nodo o arista, en las dos
    generaciones: `provenances` si existe; si no, `provenance` (dict) más
    `additional_provenance` (lista, gen 1). Nunca solo provenance[0]."""
    ps = list(o.get("provenances") or [])
    if not ps and isinstance(o.get("provenance"), dict):
        ps = [o["provenance"]]
    extra = o.get("additional_provenance")
    if isinstance(extra, list):
        ps += [p for p in extra if isinstance(p, dict)]
    return ps


def formato_provenance(p: dict) -> int:
    """3 si la provenance es gen 3 ({archivo, punto}); 2 si es gen 1/2
    ({source_doc, location}); 0 si no es reconocible."""
    if not isinstance(p, dict):
        return 0
    if "punto" in p or "archivo" in p:
        return 3
    if "source_doc" in p or "location" in p:
        return 2
    return 0


def anclas(o: dict) -> set:
    """Conjunto de (archivo, punto) sobre TODAS las provenances del objeto.
    gen 3: (archivo, punto) directos. gen 1/2: (source_doc, N.N) por cada
    «Punto N.N.» que aparezca en location."""
    out = set()
    for p in provenances(o):
        if formato_provenance(p) == 3:
            out.add((p.get("archivo") or "", str(p.get("punto") or "")))
        else:
            for pt in RE_PUNTO.findall(norm(p.get("location"))):
                out.add((p.get("source_doc") or "", pt))
    return out


def con_ancla(o: dict, archivo_pref: str, punto: str | None = None, prefijo_punto: bool = False) -> bool:
    """¿Alguna provenance del objeto ancla en (archivo que empieza por
    archivo_pref, punto)? punto None = cualquier punto de ese archivo;
    prefijo_punto = acepta también punto.x."""
    for a, p in anclas(o):
        if not a.startswith(archivo_pref):
            continue
        if punto is None or p == punto or (prefijo_punto and p.startswith(punto + ".")):
            return True
    return False


def cuarentena_bool(v) -> bool:
    """Normaliza `properties.cuarentena`: booleano (gen 2) o cadena "true"
    (gen 3) → booleano. Cualquier otro valor → False."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return False


def es_propuesto(n: dict) -> bool:
    return n.get("type") == "Sujeto" and prop(n, "nivel") == "propuesto"


def umbrales_lista(n: dict) -> list:
    """Elementos de la lista de umbrales del perfil r2 (L-ESQ-R2 §1); [] si el
    nodo no la tiene (grafos de los perfiles existentes)."""
    v = prop(n, "umbrales")
    return [u for u in v if isinstance(u, dict)] if isinstance(v, list) else []


def valor_normalizado(u: dict) -> str:
    """Valor normalizado de un elemento de umbral: «valor unidad [moneda]»."""
    return " ".join(str(x) for x in (u.get("valor"), u.get("unidad"), u.get("moneda")) if x is not None)


def detectar_generacion(kg: dict) -> int:
    """Generación por el formato de la primera provenance reconocible
    (informativo: --generacion es lo declarado y se coteja contra esto)."""
    for n in kg.get("nodes", []):
        for p in provenances(n):
            f = formato_provenance(p)
            if f:
                return f
    return 0


# =========================================================================== #
# Grafo, catálogo y direccionamiento                                          #
# =========================================================================== #
class Grafo:
    def __init__(self, kg: dict, ruta: str = "", sha256: str = ""):
        self.kg = kg
        self.ruta = ruta
        self.sha256 = sha256
        self.N = kg["nodes"]
        self.E = kg["edges"]
        self.by_id = {n["id"]: n for n in self.N}
        self.out_e: dict = {}
        self.in_e: dict = {}
        for e in self.E:
            self.out_e.setdefault(e["source"], []).append(e)
            self.in_e.setdefault(e["target"], []).append(e)
        self.generacion_detectada = detectar_generacion(kg)

    @classmethod
    def desde_ruta(cls, ruta) -> "Grafo":
        ruta = Path(ruta)
        return cls(json.loads(ruta.read_text(encoding="utf-8")), str(ruta), sha256_path(ruta))

    def tipo(self, nid: str):
        n = self.by_id.get(nid)
        return n.get("type") if n else None

    def salientes(self, nid: str) -> list:
        return self.out_e.get(nid, [])

    def entrantes(self, nid: str) -> list:
        return self.in_e.get(nid, [])

    def buscar(self, tipo=None, archivo=None, punto=None, contiene=(), no_contiene=(), prefijo_punto=False) -> list:
        """Direccionamiento (decisión 1): (archivo del TO, punto ∈ conjunto de
        provenances, tipo, cadenas normalizadas contenidas / no contenidas)."""
        out = []
        for n in self.N:
            if tipo and n.get("type") != tipo:
                continue
            if archivo and not con_ancla(n, archivo, punto, prefijo_punto):
                continue
            t = texto(n)
            if any(norm(c) not in t for c in contiene):
                continue
            if any(norm(c) in t for c in no_contiene):
                continue
            out.append(n)
        return out

    def arista(self, src: str, relation: str, tgt: str | None = None, tgt_type: str | None = None) -> bool:
        """Forma F4: arista presente src --relation--> (tgt | cualquier nodo de tipo tgt_type)."""
        for e in self.salientes(src):
            if e.get("relation") != relation:
                continue
            if tgt is not None and e.get("target") != tgt:
                continue
            if tgt_type is not None and self.tipo(e.get("target")) != tgt_type:
                continue
            return True
        return False

    def sujeto_por_label(self, label: str):
        k = norm(label)
        for n in self.N:
            if n.get("type") == "Sujeto" and norm(n.get("label")) == k:
                return n
        return None


class Catalogo:
    """Catálogo de Sujetos leído del artefacto (decisión 7)."""

    def __init__(self, data: dict, ruta: str = "", sha256: str = ""):
        self.data = data
        self.ruta = ruta
        self.sha256 = sha256
        self.version = str(data.get("version", ""))
        self.clases = OrderedDict((e["id"], e) for e in data.get("clases", []))
        self.roles = OrderedDict((r["id"], r) for r in data.get("roles", []))
        self.ids = frozenset(list(self.clases) + list(self.roles))
        if len(self.ids) != len(self.clases) + len(self.roles):
            raise RuntimeError(f"catálogo con ids duplicados: {ruta}")

    @classmethod
    def desde_ruta(cls, ruta) -> "Catalogo":
        ruta = Path(ruta)
        return cls(json.loads(ruta.read_text(encoding="utf-8")), str(ruta), sha256_path(ruta))

    def miembros(self, rol_id: str) -> list:
        r = self.roles.get(rol_id)
        return list((r or {}).get("miembros") or [])


def rank_de(idx, consulta: str, ids_obj, limite: int):
    """Forma F5: menor posición (1-based) de cualquier id objetivo en
    buscar_nodos(consulta, limite) del retriever in-memory; None si no entra
    en la ventana pedida. `idx` expone buscar_nodos(consulta, limite) →
    {"resultados": [{"id": ...}, ...]} (harness.GraphIndex)."""
    limite = max(1, min(int(limite), TOPE_HARNESS))
    res = idx.buscar_nodos(consulta, limite)["resultados"]
    for k, r in enumerate(res, 1):
        if r["id"] in ids_obj:
            return k
    return None


def evaluar_consultas(idx, consultas: list) -> list:
    """consultas: [(consulta, {objetivo: {"ids": set, "esperado": int|None,
    "limite": int, "cuenta": bool}}, fuente)]. Devuelve una fila por consulta
    con rank medido, en_ventana (rank ≤ limite declarado) y coincide_sellado
    (rank == esperado; esperado None = fuera del top-10 sellado)."""
    filas = []
    for consulta, objetivos, fuente in consultas:
        lim_q = max([o["limite"] for o in objetivos.values()] + [LIMITE_DEFAULT])
        fila = {"consulta": consulta, "limite_pedido": lim_q, "fuente": fuente, "objetivos": []}
        for nombre, o in objetivos.items():
            ids = set(o["ids"])
            rank = rank_de(idx, consulta, ids, lim_q) if ids else None
            esperado = o["esperado"]
            en_ventana = rank is not None and rank <= o["limite"]
            if esperado is None:
                coincide = rank is None or rank > LIMITE_DEFAULT
            else:
                coincide = rank == esperado
            fila["objetivos"].append({
                "objetivo": nombre, "objetivo_presente": bool(ids), "n_ids": len(ids),
                "rank": rank, "rank_esperado_sellado": esperado, "limite": o["limite"],
                "en_ventana": en_ventana, "coincide_sellado": coincide, "cuenta_para_estado": o["cuenta"],
            })
        filas.append(fila)
    return filas


def alcanzabilidad_ok(filas: list) -> tuple:
    """(todos en ventana, n_fallan, n_cuentan) sobre los objetivos que cuentan
    para el estado y tienen rank sellado numérico."""
    cuentan = [o for f in filas for o in f["objetivos"] if o["cuenta_para_estado"] and o["rank_esperado_sellado"] is not None]
    fallan = [o for o in cuentan if not o["en_ventana"]]
    return (not fallan, len(fallan), len(cuentan))


def _obj(ids, esperado, limite=LIMITE_DEFAULT, cuenta=True) -> dict:
    return {"ids": set(ids), "esperado": esperado, "limite": limite, "cuenta": cuenta}


# =========================================================================== #
# Contexto de una corrida (imports pesados diferidos)                          #
# =========================================================================== #
class Contexto:
    def __init__(self, grafo: Grafo, catalogo: Catalogo, generacion: int, politica: str,
                 esqueleto_ref_ruta=None, relaciones_esqueleto=None, indice=None,
                 muestra30=None, archivos_e0=None, e4=None, esqueleto_ref: Grafo | None = None,
                 perfil: str = "existente", registro_dir=None, esqueleto_catalogo=None,
                 enums_r2=None, marcas_nodo_r2=None, manifiesto=None, tos_bajo_prueba=None,
                 generados_resolucion=None):
        self.grafo = grafo
        # R2 de U-RERESOL-CAT, W3: generados del catálogo de resolución que leyó el ensamblado (LN-6); None = los
        # del catálogo del request (generados_r2/), como siempre
        self.generados_resolucion = Path(generados_resolucion) if generados_resolucion else None
        # U-REEXT-T0, T1, punto 4.a: manifiesto del grafo bajo prueba (ruta), o la tabla ya resuelta
        # (fuente, {to: archivo}) para el selftest
        self._manifiesto = manifiesto
        self._tos_bajo_prueba = tos_bajo_prueba
        self.cat = catalogo
        self.generacion = generacion
        self.politica = politica
        self.perfil = perfil
        # directorio del ensamblado con los registros del perfil r2 (default: el del kg.json)
        self.registro_dir = Path(registro_dir) if registro_dir else (Path(grafo.ruta).parent if grafo.ruta else None)
        self._esqueleto_catalogo = esqueleto_catalogo
        self._enums_r2 = enums_r2
        self._marcas_nodo_r2 = marcas_nodo_r2
        self.esqueleto_ref_ruta = esqueleto_ref_ruta
        self._esqueleto_ref = esqueleto_ref
        self._relaciones_esqueleto = relaciones_esqueleto
        self._indice = indice
        self._muestra30 = muestra30
        self._archivos_e0 = archivos_e0
        self._e4 = e4

    # --- retriever in-memory (decisión 4): importado, no copiado ---
    @property
    def indice(self):
        if self._indice is None:
            if str(EVALUACION) not in sys.path:
                sys.path.insert(0, str(EVALUACION))
            import harness   # noqa: E402  data/experiment/evaluacion/harness.py:130 (GraphIndex)
            import loader    # noqa: E402  data/experiment/evaluacion/loader.py:325 (load_graph_from_path)
            kg = loader.load_graph_from_path(self.grafo.ruta, adapter_key=None)
            self._indice = harness.GraphIndex(kg)
        return self._indice

    # --- esqueleto de referencia (decisión 8) ---
    @property
    def esqueleto_ref(self) -> Grafo:
        if self._esqueleto_ref is None:
            ruta = self.esqueleto_ref_ruta or DEFAULT_ESQUELETO_REF
            if self.grafo.ruta and Path(ruta).resolve() == Path(self.grafo.ruta).resolve():
                self._esqueleto_ref = self.grafo
            else:
                self._esqueleto_ref = Grafo.desde_ruta(ruta)
        return self._esqueleto_ref

    @property
    def relaciones_esqueleto(self) -> tuple:
        if self._relaciones_esqueleto is None:
            if str(GRAFO_V2_CODE) not in sys.path:
                sys.path.insert(0, str(GRAFO_V2_CODE))
            from schema import RELACIONES_ESQUELETO   # noqa: E402  grafo_v2/code/schema.py:76
            self._relaciones_esqueleto = tuple(RELACIONES_ESQUELETO)
        return self._relaciones_esqueleto

    # --- muestra sellada de T5 ---
    @property
    def muestra30(self) -> list:
        if self._muestra30 is None:
            sha = sha256_path(MUESTRA30)
            if sha != SHA_MUESTRA30:
                raise RuntimeError(f"muestra30 con sha distinto del sellado: {sha}")
            self._muestra30 = json.loads(MUESTRA30.read_text(encoding="utf-8"))
        return self._muestra30

    # --- E4: r1_e4 / e2_lib / r1_comun importados, no copiados (pieza c) ---
    @property
    def e4(self):
        if self._e4 is None:
            for p in (str(CORPUS_V2), str(GRAFO_V2_CODE), str(E2_REDUCE)):
                if p not in sys.path:
                    sys.path.insert(0, p)
            import r1_comun   # noqa: E402
            import r1_e4      # noqa: E402  indice_catalogo :74, resolver_label :97
            import e2_lib     # noqa: E402  slugify_full :90
            self._e4 = {"r1_e4": r1_e4, "e2_lib": e2_lib, "r1_comun": r1_comun,
                        "indice": r1_e4.indice_catalogo(self.cat.data)}
        return self._e4

    # --- R-T4: esqueleto que build_skeleton construye sobre el catálogo ---
    @property
    def esqueleto_catalogo(self) -> tuple:
        if self._esqueleto_catalogo is None:
            self._esqueleto_catalogo = esqueleto_de_catalogo(self.cat.ruta, self.relaciones_esqueleto)
        return self._esqueleto_catalogo

    # --- perfil r2: listas cerradas (pyd_r2, generado) y marcas de nodo ---
    @property
    def enums_r2(self) -> dict:
        if self._enums_r2 is None:
            self._enums_r2 = json.loads(ENUMS_R2.read_text(encoding="utf-8"))
        return self._enums_r2

    @property
    def marcas_nodo_r2(self) -> tuple:
        """modelos_r2.MARCAS_NODO (marcas de la cadena de ensamblado en las
        properties del nodo), importado, no copiado."""
        if self._marcas_nodo_r2 is None:
            if str(PYD_R2_CODE) not in sys.path:
                sys.path.insert(0, str(PYD_R2_CODE))
            import modelos_r2   # noqa: E402  pyd_r2/code/modelos_r2.py:380
            self._marcas_nodo_r2 = tuple(modelos_r2.MARCAS_NODO)
        return self._marcas_nodo_r2

    def registro(self, nombre: str):
        """Filas de un registro jsonl del ensamblado (None si no existe)."""
        if self.registro_dir is None or not (self.registro_dir / nombre).exists():
            return None
        return [json.loads(x) for x in (self.registro_dir / nombre).read_text(encoding="utf-8").splitlines() if x.strip()]

    @property
    def archivos_e0(self) -> dict:
        """Archivo PDF por TO según E0 (r1_comun.archivo_de_to, única fuente)."""
        if self._archivos_e0 is None:
            rc = self.e4["r1_comun"]
            self._archivos_e0 = {to: rc.archivo_de_to(to) for to in rc.TOS_ORDEN}
        return self._archivos_e0

    def ruta_manifiesto(self):
        """(ruta del manifiesto del grafo bajo prueba, de dónde sale) o (None, motivo): --manifiesto, o el
        `manifiesto.path` del reporte del ensamblado junto al kg.json (REPORTES_ENSAMBLADO, en ese orden)."""
        if self._manifiesto:
            return Path(self._manifiesto), "--manifiesto"
        if self.registro_dir is not None:
            for nombre in REPORTES_ENSAMBLADO:
                p = self.registro_dir / nombre
                if p.exists():
                    m = json.loads(p.read_text(encoding="utf-8")).get("manifiesto")
                    if isinstance(m, dict) and m.get("path"):
                        return RAIZ / m["path"], f"{nombre} (manifiesto.path)"
        return None, "sin --manifiesto ni manifiesto en el reporte del ensamblado"

    @property
    def tos_bajo_prueba(self) -> tuple:
        """U-REEXT-T0, T1, punto 4.a: (fuente, {to: archivo}) de los TOs del manifiesto del grafo bajo prueba; sin
        manifiesto, los cinco TOs de desarrollo de E0 (archivos_e0), como antes."""
        if self._tos_bajo_prueba is None:
            ruta, origen = self.ruta_manifiesto()
            if ruta is not None:
                man = json.loads(Path(ruta).read_text(encoding="utf-8"))
                rel = str(Path(ruta).resolve().relative_to(RAIZ)) if Path(ruta).resolve().is_relative_to(RAIZ) else str(ruta)
                self._tos_bajo_prueba = (f"manifiesto {rel} ({origen})", {t["id"]: t["archivo"] for t in man["tos"]})
            else:
                self._tos_bajo_prueba = (f"los cinco TOs de desarrollo de E0, r1_comun.TOS_ORDEN ({origen})",
                                         dict(self.archivos_e0))
        return self._tos_bajo_prueba


def res(estado: str, detalle: str, **extra) -> dict:
    assert estado in ESTADOS, estado
    out = {"estado": estado, "detalle": detalle}
    out.update(extra)
    return out


def _ids(ns, k=3):
    return [n["id"][:72] for n in ns[:k]]


# =========================================================================== #
# Objetivos compartidos (direccionados sin id)                                 #
# =========================================================================== #
C5_NODOS = [("N1", "6.5", "cada cliente, y la totalidad de sus financiaciones comprendidas"),
            ("N2", "6.5.1", "situacion normal"), ("N3", "6.5.2", "seguimiento especial"),
            ("N4", "6.5.2.1", "en observacion"), ("N5", "6.5.2.2", "en negociacion o con acuerdos de refinanciacion"),
            ("N6", "6.5.2.3", "tratamiento especial"), ("N7", "6.5.3", "con problemas"),
            ("N8", "6.5.4", "alto riesgo de insolvencia"), ("N9", "6.5.5", "irrecuperable")]

# C4: (id de cuarentena registrado en C4_retest_2026-08-02.md:35-42, label de
# cuarentena.json, padre laudado). El sujeto se localiza por label
# normalizado (los ids Sujeto_propuesto_* derivan del label; no son de
# catálogo) o por ese id de cuarentena; nunca por id de contenido.
C4_OCHO = [("Sujeto_propuesto_inversor", "Inversor", "Sujeto_contraparte"),
           ("Sujeto_propuesto_entidades_financieras_del_grupo_1", "Entidades financieras del grupo 1", "Sujeto_entidad_financiera"),
           ("Sujeto_propuesto_beneficiarios_de_radpip_y_o_radpign", "Beneficiarios de RADPIP y/o RADPIGN", "Sujeto_contraparte"),
           ("Sujeto_propuesto_entidades_del_grupo_a", "Entidades del Grupo A", "Sujeto_entidad_financiera"),
           ("Sujeto_propuesto_entidades_financieras_del_grupo_2", "Entidades financieras del grupo 2", "Sujeto_entidad_financiera"),
           ("Sujeto_propuesto_inversores_y_tenedores_de_titulizacion", "Inversores y tenedores de titulización", "Sujeto_contraparte"),
           ("Sujeto_propuesto_originante_fiduciario", "Originante/fiduciario", "Sujeto_fiduciario_de_fideicomiso_financiero"),
           ("Sujeto_propuesto_personas_juridicas_beneficiarias_del_regimen_de_economia_del_conocimiento",
            "Personas jurídicas beneficiarias del régimen de economía del conocimiento", "Sujeto_beneficiario_economia_conocimiento")]
C4_EXCLUIDA = ("Sujeto_propuesto_originante_acreedor_inicial", "Originante/acreedor inicial")

ROL_PROTECCION = "Sujeto_rol_sujeto_obligado_proteccion"
PNFC = "Sujeto_proveedor_no_financiero_de_credito"
EMISORAS = "Sujeto_empresa_no_financiera_emisora_de_tarjetas"
C7_FRASE = "para el calculo del importe correspondiente al mes n"
C7_RPC = "responsabilidad patrimonial computable informada en el mes n"
C7_FRANQUICIA = "franquicia informada en el mes n calculada segun datos del mes n"
C1_FRASE = "los clientes de la entidad (tanto residentes en el pais"
C3_FRASE = "companias financieras que realicen, en forma directa, operaciones de comercio exterior"


def obj_c1(G: Grafo):
    return G.buscar("Obligacion", CLA, "1.1", contiene=[C1_FRASE])


def obj_c5(G: Grafo) -> dict:
    return {k: G.buscar(None, CLA, pt, contiene=[fr]) for k, pt, fr in C5_NODOS}


def obj_c6(G: Grafo):
    return G.buscar("Excepcion", PRO, "1.1.2.5", contiene=["mutuales o cooperativas"])


def obj_c7(G: Grafo):
    return G.buscar("Obligacion", RIC, "7.1", contiene=[C7_FRASE])


def localizar_c4(G: Grafo, id_cuarentena: str, label: str):
    n = G.sujeto_por_label(label)
    if n is None and id_cuarentena in G.by_id and G.by_id[id_cuarentena].get("type") == "Sujeto":
        n = G.by_id[id_cuarentena]
    return n


# =========================================================================== #
# Tests — grupo (i): BKL cerrados                                              #
# =========================================================================== #
def t_bkl_0017(ctx: Contexto) -> dict:
    """C1: criterio general 1.1 de Clasificación (F1 + F4 + F5)."""
    G = ctx.grafo
    c1 = obj_c1(G)
    sub = OrderedDict()
    sub["nodo_1_1"] = bool(c1)
    if not c1:
        return res("persiste", "sin Obligacion anclada en cla 1.1 con la frase del criterio general", subchecks=sub)
    n = c1[0]
    sub["arista_establecida_en_TextoOrdenado"] = G.arista(n["id"], "establecida_en", tgt_type="TextoOrdenado")
    sub["arista_aplica_a_Sujeto"] = G.arista(n["id"], "aplica_a", tgt_type="Sujeto") or G.arista(n["id"], "aplica_a", tgt_type="EntidadFinanciera")
    ids = {x["id"] for x in c1}
    f = "data/backlog/retests/C1_retest_2026-07-31.md:42-44"
    consultas = [("criterio general clasificación deudores", {"C1": _obj(ids, 1)}, f),
                 ("qué clientes deben ser clasificados", {"C1": _obj(ids, 1)}, f),
                 ("clasificación residentes en el exterior", {"C1": _obj(ids, 3)}, f)]
    filas = evaluar_consultas(ctx.indice, consultas)
    ok_rk, n_fallan, n_cuentan = alcanzabilidad_ok(filas)
    sub["alcanzable_en_ventana"] = ok_rk
    estado = "resuelto" if all(sub.values()) else "persiste"
    det = (f"nodo={len(c1)} {_ids(c1, 1)}; establecida_en={sub['arista_establecida_en_TextoOrdenado']}; "
           f"aplica_a={sub['arista_aplica_a_Sujeto']}; consultas en ventana={n_cuentan - n_fallan}/{n_cuentan}"
           + ("" if ok_rk else " (persiste solo por alcanzabilidad si lo demás cumple)"))
    return res(estado, det, subchecks=sub, ranks=filas)


# Montos de la tabla del 1.2 de CapMin en la forma normalizada de la lista de
# umbrales (millones de pesos → valor en pesos, unidad moneda, ARS).
MONTO_DE_VALOR = {("5000000000", "moneda", "ARS"): "5.000", ("2500000000", "moneda", "ARS"): "2.500"}
UMBRAL_C3 = ("5000000000", "moneda", "ARS")


def _clave_umbral(u: dict) -> tuple:
    return (u.get("valor"), u.get("unidad"), u.get("moneda"))


def montos_de_lista(lista: list) -> list:
    """Montos de la tabla del 1.2 («5.000», «2.500») que lleva una lista de umbrales."""
    return sorted({MONTO_DE_VALOR[_clave_umbral(u)] for u in lista if _clave_umbral(u) in MONTO_DE_VALOR})


def clase_1_2(t: str) -> str:
    """Columna de la tabla del 1.2 a la que se refiere un texto normalizado."""
    return "restantes" if "restantes entidades" in t else ("bancos" if "bancos" in t else "otro")


def tabla_1_2_r2(G: Grafo) -> list:
    """Perfil r2: direccionamiento de BKL-0006 y BKL-0023 por punto y monto.
    Las Restricciones ancladas en cap 1.2 cuya lista de umbrales lleva, en
    valor normalizado, un monto de la tabla del 1.2 (MONTO_DE_VALOR), sin
    exigir una frase del texto: la extracción r2 no escribe «exigencia
    básica» en esos nodos y la frase dejaba el ítem en no_aplicable aunque la
    tabla estuviera invertida."""
    return [n for n in G.buscar("Restriccion", CAP, "1.2") if montos_de_lista(umbrales_lista(n))]


def t_bkl_0006(ctx: Contexto) -> dict:
    """C2: montos del 1.2 de CapMin (F3 + F4; F5 informativo sin criterio).
    Perfil r2: los nodos se direccionan por punto y monto (`tabla_1_2_r2`)."""
    G = ctx.grafo
    r2 = ctx.perfil == "r2"
    tabla = tabla_1_2_r2(G) if r2 else G.buscar(None, CAP, "1.2", contiene=["exigencia basica"])
    filas, bancos_ok, restantes_ok, invertido = [], False, False, False
    for n in tabla:
        t = texto(n)
        clase = clase_1_2(t)
        lista = umbrales_lista(n)
        if lista:
            # perfil r2: el monto sale del valor normalizado de la lista (L-ESQ-R2 §1.5)
            montos = montos_de_lista(lista)
            umbral = [valor_normalizado(u) for u in lista]
        else:
            montos = sorted(set(RE_MONTO.findall(t)))
            umbral = prop(n, "umbral") or prop(n, "monto")
        filas.append(f"{n['type']}:{n['id'][:50]} clase={clase} montos={montos} umbral={umbral!r}")
        if n["type"] != "Excepcion":
            if clase == "bancos":
                bancos_ok |= ("5.000" in montos and "2.500" not in montos)
                invertido |= ("2.500" in montos)
            if clase == "restantes":
                restantes_ok |= ("2.500" in montos and "5.000" not in montos)
                invertido |= ("5.000" in montos)
    sub = OrderedDict()
    if not tabla:
        if r2:
            return res("no_aplicable", "sin Restriccion anclada en cap 1.2 con un monto de la tabla del 1.2 en la lista de umbrales",
                       subchecks=sub)
        return res("no_aplicable", "sin nodos anclados en cap 1.2 con «exigencia básica»: tabla del 1.2 no extraída", subchecks=sub)
    sub["tabla_bancos_5000_restantes_2500"] = bancos_ok and restantes_ok and not invertido
    exc = G.buscar("Excepcion", CAP, "1.2", contiene=["cajas de credito cooperativas"])
    if exc:
        tg = [(e["relation"], texto(G.by_id[e["target"]])[:40]) for e in G.salientes(exc[0]["id"])
              if e["relation"].startswith("exceptua") and e["target"] in G.by_id]
        sub["excepcion_cajas_apunta_a_restantes"] = any("restantes" in t for _, t in tg)
    else:
        tg = None
    # F5 informativo (C2_retest:59: «informativo, sin criterio de corte»); el
    # «bancos 13» exige limite 13 (decisión 4, inventario §5.6).
    if r2:
        bancos = {n["id"] for n in tabla if clase_1_2(texto(n)) == "bancos"}
        restantes = {n["id"] for n in tabla if clase_1_2(texto(n)) == "restantes"}
    else:
        bancos = {n["id"] for n in G.buscar("Restriccion", CAP, "1.2", contiene=["bancos", "exigencia basica"], no_contiene=["restantes entidades"])}
        restantes = {n["id"] for n in G.buscar("Restriccion", CAP, "1.2", contiene=["restantes entidades", "exigencia basica"])}
    excep = {n["id"] for n in exc}
    f = "data/backlog/retests/C2_retest_2026-07-31.md:61-63"
    consultas = [("exigencia básica bancos", {"C2.bancos": _obj(bancos, 1, cuenta=False), "C2.excepcion": _obj(excep, 3, cuenta=False), "C2.restantes": _obj(restantes, 4, cuenta=False)}, f),
                 ("exigencia básica restantes entidades", {"C2.excepcion": _obj(excep, 1, cuenta=False), "C2.restantes": _obj(restantes, 2, cuenta=False), "C2.bancos": _obj(bancos, 13, limite=13, cuenta=False)}, f)]
    rk = evaluar_consultas(ctx.indice, consultas)
    estado = "resuelto" if all(sub.values()) else "persiste"
    det = (("invertido: " if invertido else "") + f"tabla={sub['tabla_bancos_5000_restantes_2500']}; "
           + (f"excepcion→restantes={sub['excepcion_cajas_apunta_a_restantes']} targets={tg}" if exc else "sin Excepcion de cajas en cap 1.2 (sub-check no aplicable)")
           + "; " + " || ".join(filas))
    return res(estado, det, subchecks=sub, ranks=rk)


def t_bkl_0023(ctx: Contexto) -> dict:
    """C3: umbral de compañías financieras con comercio exterior (F3). Sin
    nodo o sin umbral → no_aplicable (pieza e: nunca PASS vacuo).

    Perfil r2: direccionamiento por punto y monto (`tabla_1_2_r2`). El nodo
    objetivo es la Restriccion de las compañías financieras, si la tabla la
    tiene; si no, la de bancos: la oración del 1.2 remite a «las exigencias
    establecidas para los bancos», y en la extracción r2 es una Obligacion sin
    monto, así que el umbral de las compañías financieras es el que el grafo
    da a los bancos. Resuelto si cada nodo objetivo lleva 5.000 millones de
    pesos (UMBRAL_C3) en su lista."""
    G = ctx.grafo
    if ctx.perfil == "r2":
        tabla = tabla_1_2_r2(G)
        propias = [n for n in tabla if "companias financieras" in texto(n)]
        via = "Restriccion de las compañías financieras" if propias else "Restriccion de bancos (remisión de la oración de compañías financieras)"
        objetivo = propias or [n for n in tabla if clase_1_2(texto(n)) == "bancos"]
        if not objetivo:
            return res("no_aplicable", "sin Restriccion anclada en cap 1.2 con un monto de la tabla del 1.2 en la lista de "
                                       "umbrales, ni de compañías financieras ni de bancos")
        u = [[valor_normalizado(x) for x in umbrales_lista(n)] for n in objetivo]
        ok = all(any(_clave_umbral(x) == UMBRAL_C3 for x in umbrales_lista(n)) for n in objetivo)
        return res("resuelto" if ok else "persiste", f"{via}: n={len(objetivo)} {_ids(objetivo, 1)} umbrales={u}",
                   valores={"umbrales": u, "direccionamiento": via})
    c3 = G.buscar("Restriccion", CAP, "1.2", contiene=[C3_FRASE])
    if not c3:
        return res("no_aplicable", "ninguna Restriccion anclada en cap 1.2 con la oración de compañías financieras")
    listas = [umbrales_lista(n) for n in c3]
    if any(listas):
        # perfil r2: valor normalizado de la lista de umbrales (L-ESQ-R2 §1.5)
        u = [[valor_normalizado(x) for x in lst] for lst in listas]
        ok = any(_clave_umbral(x) == UMBRAL_C3 for lst in listas for x in lst)
        return res("resuelto" if ok else "persiste", f"n={len(c3)} umbrales={u}", valores={"umbrales": u})
    u = [prop(n, "umbral") for n in c3]
    if all(x is None for x in u):
        return res("no_aplicable", f"nodo presente ({_ids(c3, 1)}) sin properties.umbral: no hay valor que comprobar", valores={"umbral": u})
    ok = any(norm(x) == "5.000 millones de pesos" for x in u if x)
    return res("resuelto" if ok else "persiste", f"n={len(c3)} umbral={u}", valores={"umbral": u})


def t_bkl_0019(ctx: Contexto) -> dict:
    """C4: jerarquía de los 8 sujetos de cuarentena, según política (F4 ×8 +
    F4 ausente para la excluida; la posición en ver_vecinos se reduce a
    arista presente, decisión 4)."""
    G = ctx.grafo
    rel = "subclase_de" if ctx.politica == "laudada" else "padre_sugerido"
    filas, presentes, con_arista = [], 0, 0
    for idc, lab, padre in C4_OCHO:
        n = localizar_c4(G, idc, lab)
        if n is None:
            filas.append(f"{lab[:30]}: src ausente")
            continue
        presentes += 1
        ok = G.arista(n["id"], rel, tgt=padre)
        con_arista += ok
        filas.append(f"{lab[:30]}: {rel}→{padre[7:]}={'si' if ok else 'NO'} tgt_presente={padre in G.by_id}")
    sub = OrderedDict()
    if presentes == 0:
        return res("no_aplicable", "ninguno de los 8 sujetos propuestos está en el grafo (por label ni por id de cuarentena)", valores={"presentes": 0})
    sub[f"{rel}_en_todos_los_presentes"] = con_arista == presentes
    if ctx.politica == "laudada":
        ex = localizar_c4(G, *C4_EXCLUIDA)
        if ex is not None:
            sub["excluida_sin_subclase_de"] = not any(e["relation"] == "subclase_de" for e in G.salientes(ex["id"]))
        else:
            filas.append("excluida: ausente (sub-check no aplicable)")
    estado = "resuelto" if all(sub.values()) else "persiste"
    return res(estado, f"politica={ctx.politica}: {rel} {con_arista}/{presentes} presentes (de 8); " + " || ".join(filas),
               subchecks=sub, valores={"presentes": presentes, "con_arista": con_arista})


def _consultas_c5(hall: dict) -> list:
    ids = {k: {n["id"] for n in v} for k, v in hall.items()}
    f = "data/backlog/propuestas/E4_enumeracion_65.md:283-289 (retest C5 (c) 7/7 en top-10, C5_retest_2026-08-02.md:65)"
    q = [("niveles clasificación deudores cartera comercial", {"N1": 1, "N7": 4, "N9": 5, "N2": 6, "N3": 8}),
         ("seguimiento especial deudores", {"N1": 1, "N4": 3, "N6": 4, "N5": 5, "N3": 6}),
         ("punto 6.5 niveles clasificación", {"N1": 1, "N7": 2, "N9": 3, "N2": 4, "N8": 5, "N3": 6}),
         ("situaciones que integran el seguimiento especial", {"N3": 7}),
         ("cinco categorías cartera comercial", {"N1": 1, "N7": 7, "N9": 8, "N2": 9, "N4": 10}),
         ("en negociación o con acuerdos de refinanciación", {"N5": 1, "N3": 2}),
         ("situación normal cartera comercial", {"N2": 1, "N1": 2, "N4": 3, "N6": 4, "N5": 5})]
    out = [(c, {("C5." + k): _obj(ids[k], r) for k, r in esp.items()}, f) for c, esp in q]
    out.append(("reclasificación en tratamiento especial refinanciación", {"C5.N6": _obj(ids["N6"], 4)},
                "data/backlog/retests/C5_retest_2026-08-02.md:70-72 (proxy RT-C5-4, consulta plausible mínima)"))
    return out


def t_bkl_0004(ctx: Contexto) -> dict:
    """C5: enumeración del 6.5 (F1 ×9 + F4 8 regula + 9 establecida_en + F5)."""
    G = ctx.grafo
    hall = obj_c5(G)
    n_ok = sum(1 for k in hall if hall[k])
    sub = OrderedDict()
    sub["9_nodos_por_ancla_y_frase"] = n_ok == 9
    det = [f"nodos {n_ok}/9 -> " + " ".join(f"{k}@{pt}:{len(hall[k])}" for k, pt, _ in C5_NODOS)]
    if hall["N1"]:
        n1 = hall["N1"][0]
        hijos = {n["id"] for k in hall if k != "N1" for n in hall[k]}
        regula = sum(1 for e in G.salientes(n1["id"]) if e["relation"] == "regula" and e["target"] in hijos)
        est_en = sum(1 for k in hall if any(G.arista(n["id"], "establecida_en", tgt_type="TextoOrdenado") for n in hall[k]))
        sub["8_regula_N1_a_hijos"] = regula == 8
        sub["9_establecida_en"] = est_en == 9
        det.append(f"regula={regula}/8 establecida_en={est_en}/9")
    else:
        det.append("sin N1: aristas no evaluables")
    rk = evaluar_consultas(ctx.indice, _consultas_c5(hall))
    ok_rk, n_fallan, n_cuentan = alcanzabilidad_ok(rk)
    sub["alcanzable_en_ventana"] = ok_rk
    det.append(f"objetivos en ventana={n_cuentan - n_fallan}/{n_cuentan}")
    estado = "resuelto" if all(sub.values()) else "persiste"
    return res(estado, "; ".join(det), subchecks=sub, ranks=rk, valores={"nodos": n_ok})


def _consultas_c6(G: Grafo, n1_ids: set) -> list:
    f = "data/backlog/propuestas/E3_salvedad_mutuales.md:288-298 (columna post; — = fuera del top-10; retest C6 (c) 14/14, C6_retest_2026-08-03.md:61)"
    rol = {ROL_PROTECCION} if ROL_PROTECCION in G.by_id else set()
    pnfc = {PNFC} if PNFC in G.by_id else set()
    tabla = [("asociación mutual financiaciones proveedor no financiero crédito", 1, None, 2),
             ("sujeto obligado protección usuarios servicios financieros", 1, 5, None),
             ("proveedor no financiero crédito", None, None, 1),
             ("asociación mutual", 1, None, None),
             ("definición proveedor no financiero crédito PNFC", None, None, 1),
             ("proveedor no financiero crédito comercios empresas personas jurídicas", None, None, 1),
             ("exclusión excluido no alcanzado no incluido sujeto obligado", 4, None, None),
             ("mutuales cooperativas sujeto obligado protección usuarios", 1, 2, None),
             ("excepción asociaciones mutuales cooperativas", 1, None, None),
             ("cooperativa que otorga financiaciones protección de usuarios", 1, 5, None),
             ("asociaciones mutuales proveedores no financieros de crédito", 1, None, 2)]
    return [(q, {"C6.N1": _obj(n1_ids, a), "C6.rol": _obj(rol, b), "C6.pnfc": _obj(pnfc, c)}, f) for q, a, b, c in tabla]


def t_bkl_0003(ctx: Contexto) -> dict:
    """C6: salvedad mutuales/cooperativas del 1.1.2.5 (F1 + F4 ×2 + F4 ausente a Sujeto + F5 ×11)."""
    G = ctx.grafo
    c6 = obj_c6(G)
    sub = OrderedDict()
    sub["excepcion_1_1_2_5_mutuales"] = bool(c6)
    det = [f"Excepcion={len(c6)} {_ids(c6, 1)}"]
    if c6:
        n = c6[0]
        sub["arista_establecida_en_TextoOrdenado"] = G.arista(n["id"], "establecida_en", tgt_type="TextoOrdenado")
        sub["arista_exceptua_obligacion_Obligacion"] = G.arista(n["id"], "exceptua_obligacion", tgt_type="Obligacion")
        a_suj = sum(1 for e in G.salientes(n["id"]) + G.entrantes(n["id"])
                    if G.tipo(e["target"]) == "Sujeto" or G.tipo(e["source"]) == "Sujeto")
        sub["sin_aristas_a_Sujeto"] = a_suj == 0
        det.append(f"establecida_en={sub['arista_establecida_en_TextoOrdenado']} exceptua_obligacion={sub['arista_exceptua_obligacion_Obligacion']} aristas_con_Sujeto={a_suj}")
    rk = evaluar_consultas(ctx.indice, _consultas_c6(G, {n["id"] for n in c6}))
    ok_rk, n_fallan, n_cuentan = alcanzabilidad_ok(rk)
    sub["alcanzable_en_ventana"] = ok_rk
    det.append(f"objetivos en ventana={n_cuentan - n_fallan}/{n_cuentan}")
    estado = "resuelto" if all(sub.values()) else "persiste"
    return res(estado, "; ".join(det), subchecks=sub, ranks=rk)


def _portador_c7(G: Grafo):
    port = obj_c7(G)
    con = [n for n in port if C7_RPC in texto(n) and C7_FRANQUICIA in texto(n)]
    return port, con


def t_bkl_0005(ctx: Contexto) -> dict:
    """C7: calificadores del 7.1 de RegInf (F3 + F5 ×3)."""
    G = ctx.grafo
    port, con = _portador_c7(G)
    if not port:
        return res("no_aplicable", "sin portador: ninguna Obligacion anclada en ric 7.1 con «para el cálculo del importe correspondiente al mes n»")
    sub = OrderedDict()
    sub["descripcion_con_RPC_y_franquicia"] = bool(con)
    ids = {n["id"] for n in port}
    f = "data/backlog/retests/C7_retest_2026-08-03.md:78"
    consultas = [("esquema cálculo importe mes n disminución exigencia franquicia", {"C7": _obj(ids, 1)}, f),
                 ("responsabilidad patrimonial computable cálculo importe correspondiente al mes", {"C7": _obj(ids, 1)}, f),
                 ("franquicia importe correspondiente al mes n cálculo esquema", {"C7": _obj(ids, 1)}, f)]
    rk = evaluar_consultas(ctx.indice, consultas)
    ok_rk, n_fallan, n_cuentan = alcanzabilidad_ok(rk)
    sub["alcanzable_en_ventana"] = ok_rk
    estado = "resuelto" if all(sub.values()) else "persiste"
    return res(estado, f"portadores={len(port)} con_ambos_calificadores={len(con)} {_ids(port, 1)}; consultas en ventana={n_cuentan - n_fallan}/{n_cuentan}",
               subchecks=sub, ranks=rk)


def t_bkl_0007(ctx: Contexto) -> dict:
    """Dedupe con BKL-0017 (pieza e): mismo objeto, sin test propio; el estado
    es el de BKL-0017."""
    r = t_bkl_0017(ctx)
    return res(r["estado"], "= BKL-0017 (cerrada por referencia; " + NOTA_SIN_APLICACION + "): " + r["detalle"], subchecks=r.get("subchecks"))


def t_bkl_0026(ctx: Contexto) -> dict:
    return res("no_aplicable", "no convertible: conducta del agente (paráfrasis invertida del verbatim con ver_nodo byte-idéntico, "
               "RT-C6-1 vs RT-C6-2, 3/3 en N=3); no es observable con una comprobación determinística sobre un kg.json "
               "(inventario_B21_fase1.md:107). El nodo objetivo se testea en BKL-0003. " + NOTA_SIN_APLICACION + ".")


def t_bkl_0027(ctx: Contexto) -> dict:
    return res("no_aplicable", "no convertible: conducta del agente (pidió ver_vecinos salientes de un rol que solo tiene miembro_de "
               "entrantes, RT-C6-3); la estructura del rol se testea en RT-C6-3 (inventario_B21_fase1.md:108). " + NOTA_SIN_APLICACION + ".")


def t_bkl_0028(ctx: Contexto) -> dict:
    """Tres ids con definición doméstica y alias «del exterior» en el
    catálogo v3 (b54): remedio = ids separados. Observable solo con un
    catálogo v3 y un grafo extraído con él (perfil v3_b54)."""
    cat = ctx.cat
    tres = ("Sujeto_entidad_financiera", "Sujeto_banco", "Sujeto_entidad_cambiaria")
    con_alias_ext = [i for i in tres if i in cat.clases and any("del exterior" in norm(a) for a in (cat.clases[i].get("alias") or []))]
    # los tres ids esperados, por nombre (U-R2-CODIGO, R5.a): el prefijo no
    # alcanza, porque Sujeto_banco_central_del_exterior empieza con Sujeto_banco
    esperados = tuple(f"{t}_del_exterior" for t in tres)
    ids_ext = [i for i in esperados if i in cat.ids]
    val = {"catalogo_version": cat.version, "ids_con_alias_del_exterior": con_alias_ext, "ids_separados_del_exterior": ids_ext,
           "ids_del_exterior_esperados": list(esperados)}
    if not cat.version.startswith("3"):
        return res("no_aplicable", f"catálogo {cat.version}: el defecto se registró sobre el catálogo v3 de b54 y su remedio exige ids "
                   "nuevos en ese catálogo y un grafo extraído con perfil v3_b54 (inventario_B21_fase1.md:109); "
                   + NOTA_SIN_APLICACION + ".", valores=val)
    presentes = [i for i in ids_ext if i in ctx.grafo.by_id]
    val["ids_separados_presentes_en_grafo"] = presentes
    ok = not con_alias_ext and len(ids_ext) == len(esperados) and bool(presentes)
    return res("resuelto" if ok else "persiste", f"catálogo v3: alias «del exterior» en {con_alias_ext}; ids separados {ids_ext}; "
               f"presentes en el grafo {presentes}. " + NOTA_SIN_APLICACION + ".", valores=val)


def t_bkl_0029(ctx: Contexto) -> dict:
    """Colectivo «titulares de cuenta corriente en el BCRA» sin id (rol de
    convca). no_aplicable en todo grafo que no cubra convca (pieza e)."""
    G, cat = ctx.grafo, ctx.cat
    rol = "Sujeto_rol_alcance_convca"
    cubre = any("convca" in norm(a) for n in G.N for a, _ in anclas(n)) or \
        any("convca" in norm(prop(n, "archivo")) for n in G.N if n.get("type") == "TextoOrdenado") or \
        bool(G.entrantes(rol))
    if not cubre:
        return res("no_aplicable", "el grafo no cubre convca (ninguna provenance ni TextoOrdenado de convca; el rol "
                   f"{rol} no tiene miembro_de entrantes); " + NOTA_SIN_APLICACION + ".")
    cand = [i for i, c in cat.clases.items() if "titular" in norm(c.get("label")) and "cuenta corriente" in norm(c.get("label"))]
    miembros = [e["source"] for e in G.entrantes(rol) if e["relation"] == "miembro_de"]
    residuo = ((cat.roles.get(rol) or {}).get("residuo_declarado") or {})
    ok = bool(cand) and any(c in miembros for c in cand) and not residuo.get("colectivo_operativo_sin_id", False)
    return res("resuelto" if ok else "persiste", f"ids candidatos en catálogo={cand}; miembro_de del rol={miembros}; "
               f"residuo colectivo_operativo_sin_id={residuo.get('colectivo_operativo_sin_id')}. " + NOTA_SIN_APLICACION + ".",
               valores={"candidatos": cand, "miembros": miembros})


# =========================================================================== #
# Tests — grupo (i): preguntas RT (solo valor, decisión 5)                    #
# =========================================================================== #
def _valor_en(nodos: list, frases: list, etiqueta: str, ausente: str) -> dict:
    if not nodos:
        return res("persiste", ausente)
    faltan = [f for f in frases if not any(norm(f) in texto(n) for n in nodos)]
    return res("resuelto" if not faltan else "persiste",
               f"{etiqueta} {_ids(nodos, 1)}: gold {len(frases) - len(faltan)}/{len(frases)}" + (f"; faltan {faltan}" if faltan else ""),
               valores={"faltan": faltan})


def t_rt_c5_1(ctx: Contexto) -> dict:
    n1 = obj_c5(ctx.grafo)["N1"]
    return _valor_en(n1, ["en situacion normal", "con seguimiento especial", "con problemas", "con alto riesgo de insolvencia", "irrecuperable"],
                     "N1", "sin N1 (Obligacion del 6.5 con el encabezado): el gold no está en el grafo")


def t_rt_c5_2(ctx: Contexto) -> dict:
    n3 = obj_c5(ctx.grafo)["N3"]
    return _valor_en(n3, ["en observacion", "en negociacion o con acuerdos de refinanciacion", "en tratamiento especial"],
                     "N3", "sin N3 (nodo del 6.5.2 «seguimiento especial»): el gold no está en el grafo")


def t_rt_c5_3(ctx: Contexto) -> dict:
    n5 = obj_c5(ctx.grafo)["N5"]
    return _valor_en(n5, ["antes de los 60 dias", "mora"], "N5", "sin N5 (nodo del 6.5.2.2): el gold no está en el grafo")


def t_rt_c5_4(ctx: Contexto) -> dict:
    n6 = obj_c5(ctx.grafo)["N6"]
    return _valor_en(n6, ["por primera vez dentro del ano calendario", "primera cuota", "por unica vez"],
                     "N6", "sin N6 (nodo del 6.5.2.3): el gold no está en el grafo")


def t_rt_c5_5(ctx: Contexto) -> dict:
    """F2 (nodo con «riesgo medio» anclado exactamente en cla 7.2) + F3 (N1
    sin niveles del 7.2). Sin nodos con punto 7.2 → no_aplicable por ancla."""
    G = ctx.grafo
    n72 = G.buscar(None, CLA, "7.2")
    if not n72:
        return res("no_aplicable", "sin nodos con punto exactamente 7.2 de Clasificación: el proxy falla por ancla, no por contenido "
                   "(inventario_B21_fase1.md:267, §5.7; decisión 5)", valores={"nodos_en_7_2": 0})
    rm = G.buscar(None, CLA, "7.2", contiene=["riesgo medio"])
    sub = OrderedDict([("riesgo_medio_anclado_en_7_2", bool(rm))])
    n1 = obj_c5(G)["N1"]
    if n1:
        sub["N1_sin_niveles_del_7_2"] = not any(x in texto(n1[0]) for x in ("riesgo medio", "riesgo bajo", "riesgo alto"))
    estado = "resuelto" if all(sub.values()) else "persiste"
    return res(estado, f"nodos_en_7_2={len(n72)} con_riesgo_medio={len(rm)}; N1={'presente' if n1 else 'ausente (sub-check no aplicable)'}",
               subchecks=sub, valores={"nodos_en_7_2": len(n72), "con_riesgo_medio": len(rm)})


def _valor_c6(ctx: Contexto, etiqueta: str) -> dict:
    """Gold de RT-C6-1/2 en N1 de C6. Criterio de estado = el de la sonda de
    anclas (Excepcion anclada en pro 1.1.2.5 con «mutuales o cooperativas»,
    sonda_anclas_C1_C7_UB21.py:262); la cláusula de operaciones del gold
    («por las financiaciones que otorguen») se reporta como informativa."""
    c6 = obj_c6(ctx.grafo)
    if not c6:
        return res("persiste", f"{etiqueta}: sin Excepcion anclada en pro 1.1.2.5 con «mutuales o cooperativas»")
    clausula = any("por las financiaciones que otorguen" in texto(n) for n in c6)
    return res("resuelto", f"{etiqueta}: gold «mutuales o cooperativas» presente en {_ids(c6, 1)}; "
               f"cláusula «por las financiaciones que otorguen» (informativa)={'presente' if clausula else 'AUSENTE'}",
               valores={"clausula_financiaciones": clausula})


def t_rt_c6_1(ctx: Contexto) -> dict:
    return _valor_c6(ctx, "RT-C6-1")


def t_rt_c6_2(ctx: Contexto) -> dict:
    return _valor_c6(ctx, "RT-C6-2 (= RT-C6-1 en la parte de valor)")


def t_rt_c6_5(ctx: Contexto) -> dict:
    """Cláusula de operaciones de la Excepcion de mutuales (laudo de r2, §1.5,
    opción (c); U-R2-CODIGO, R4.d): el punto 1.1.2.5 de protección exceptúa a
    las mutuales o cooperativas «por las financiaciones que otorguen»; sin la
    cláusula la excepción queda más ancha que la norma (amputación). La
    cláusula, que RT-C6-1 reporta como informativa, pasa a test: «persiste»
    documenta que sigue ausente hasta el remedio de raíz (U-PROMPT-R2)."""
    c6 = obj_c6(ctx.grafo)
    if not c6:
        return res("no_aplicable", "sin Excepcion anclada en pro 1.1.2.5 con «mutuales o cooperativas» (N1 de C6)")
    con = [n for n in c6 if "por las financiaciones que otorguen" in texto(n)]
    return res("resuelto" if con else "persiste",
               f"cláusula «por las financiaciones que otorguen» en N1 de C6: {'presente en ' + str(_ids(con, 1)) if con else 'AUSENTE'} "
               f"(N1: {_ids(c6, 1)})", valores={"clausula_financiaciones": bool(con), "n_N1": len(c6)})


def t_rt_c6_3(ctx: Contexto) -> dict:
    """Rol de sujetos obligados de Protección con sus miembro_de entrantes
    = miembros del rol en el catálogo parametrizado (F4 ×n, ids de catálogo)."""
    G, cat = ctx.grafo, ctx.cat
    if ROL_PROTECCION not in G.by_id:
        return res("no_aplicable", f"rol {ROL_PROTECCION} ausente: grafo sin esqueleto de roles")
    esperados = set(cat.miembros(ROL_PROTECCION))
    mde = {e["source"] for e in G.entrantes(ROL_PROTECCION) if e["relation"] == "miembro_de"}
    ok = bool(esperados) and mde == esperados
    return res("resuelto" if ok else "persiste",
               f"miembro_de entrantes={len(mde)} esperados(catálogo)={len(esperados)}; faltan={sorted(esperados - mde)} sobran={sorted(mde - esperados)}",
               valores={"n_miembro_de": len(mde), "n_esperados": len(esperados)})


def t_rt_c6_4(ctx: Contexto) -> dict:
    G = ctx.grafo
    if ROL_PROTECCION not in G.by_id:
        return res("no_aplicable", f"rol {ROL_PROTECCION} ausente: grafo sin esqueleto de roles")
    sub = OrderedDict()
    sub["emisoras_miembro_de_rol"] = G.arista(EMISORAS, "miembro_de", tgt=ROL_PROTECCION)
    c6 = obj_c6(G)
    if c6:
        n = c6[0]
        a_suj = sum(1 for e in G.salientes(n["id"]) + G.entrantes(n["id"]) if G.tipo(e["target"]) == "Sujeto" or G.tipo(e["source"]) == "Sujeto")
        sub["N1_sin_aristas_a_Sujeto"] = a_suj == 0
    estado = "resuelto" if all(sub.values()) else "persiste"
    return res(estado, f"emisoras→rol={sub['emisoras_miembro_de_rol']}; N1={'presente, aristas con Sujeto=' + str(not sub['N1_sin_aristas_a_Sujeto']) if c6 else 'ausente (sub-check no aplicable)'}",
               subchecks=sub)


def _valor_c7(ctx: Contexto, frases: list, etiqueta: str) -> dict:
    port, _ = _portador_c7(ctx.grafo)
    if not port:
        return res("no_aplicable", f"{etiqueta}: sin portador del 7.1 (Obligacion con «para el cálculo del importe correspondiente al mes n»)")
    return _valor_en(port, frases, etiqueta + " portador", "")


def t_rt_c7_1(ctx: Contexto) -> dict:
    return _valor_c7(ctx, [C7_RPC, C7_FRANQUICIA], "RT-C7-1")


def t_rt_c7_2(ctx: Contexto) -> dict:
    return _valor_c7(ctx, [C7_RPC], "RT-C7-2")


def t_rt_c7_3(ctx: Contexto) -> dict:
    return _valor_c7(ctx, [C7_FRANQUICIA], "RT-C7-3")


# =========================================================================== #
# Tests — grupo (ii): T1–T7 sobre el adaptador (pieza d) e I1–I5             #
# =========================================================================== #
def t_t1(ctx: Contexto) -> dict:
    """ensamblar_corpus.py:237-249 sobre el adaptador: ext 3.9 (y 3.9.x) con
    nodos de contenido y alguno con «200»."""
    G = ctx.grafo
    ext39 = G.buscar(None, EXT, "3.9", prefijo_punto=True)
    con_200 = [n for n in ext39 if "200" in texto(n)]
    puntos = sorted({p for n in ext39 for a, p in anclas(n) if a.startswith(EXT) and (p == "3.9" or p.startswith("3.9."))})
    val = {"pass": bool(ext39) and bool(con_200), "nodos_anclados_3_9": len(ext39), "puntos": puntos,
           "nodos_con_usd_200": [{"id": n["id"], "label": n.get("label")} for n in con_200][:8]}
    return res("resuelto" if val["pass"] else "persiste",
               f"anclados_3_9={len(ext39)} puntos={puntos} con_usd_200={len(con_200)}", valores=val)


def t_t2(ctx: Contexto) -> dict:
    """ensamblar_corpus.py:251-265: ≥ 5 nodos separados de ext con «125 %»/«125%» y ≥ 4 puntos distintos."""
    G = ctx.grafo
    n125 = [n for n in G.buscar(None, EXT) if "125 %" in texto(n) or "125%" in texto(n)]
    puntos = sorted({p for n in n125 for a, p in anclas(n) if a.startswith(EXT)})
    val = {"pass": len(n125) >= 5 and len(puntos) >= 4, "n_nodos_separados_ext": len(n125), "puntos_distintos": puntos,
           "nodos": [{"id": n["id"], "label": n.get("label"), "puntos": sorted(p for a, p in anclas(n) if a.startswith(EXT))} for n in n125][:12]}
    return res("resuelto" if val["pass"] else "persiste", f"nodos_separados_ext={len(n125)} puntos_distintos={puntos}", valores=val)


def t_t3(ctx: Contexto) -> dict:
    """ensamblar_corpus.py:267-280: pro 1.1.2.5 con un nodo con «mutual» o «cooperativ»."""
    G = ctx.grafo
    pro = G.buscar(None, PRO, "1.1.2.5")
    con = [n for n in pro if "mutual" in texto(n) or "cooperativ" in texto(n)]
    exc = [n for n in con if n.get("type") == "Excepcion"]
    val = {"pass": bool(con), "nodos_anclados": len(pro), "nodos_con_salvedad": [{"id": n["id"], "type": n["type"], "label": n.get("label")} for n in con][:6],
           "de_los_cuales_excepcion": len(exc)}
    return res("resuelto" if val["pass"] else "persiste", f"anclados_1_1_2_5={len(pro)} con_salvedad={len(con)} de_los_cuales_excepcion={len(exc)}", valores=val)


def t4_paridad(G: Grafo, ref: Grafo, relaciones_esqueleto: tuple) -> dict:
    """Decisión 8: la referencia es el conjunto de aristas de relaciones de
    esqueleto del grafo de referencia MENOS las de rol_fuente
    cuarentena_laudada; los nodos de referencia son los de rol_fuente
    esqueleto (r1_tests.py:32). En el grafo bajo prueba se cuenta con el
    mismo filtro."""
    ids_ref = {n["id"] for n in ref.N if n.get("rol_fuente") == "esqueleto"}
    trip_ref_total = {(e["source"], e["relation"], e["target"]) for e in ref.E if e["relation"] in relaciones_esqueleto}
    excl_ref = {(e["source"], e["relation"], e["target"]) for e in ref.E if e["relation"] in relaciones_esqueleto and e.get("rol_fuente") == "cuarentena_laudada"}
    trip_ref = trip_ref_total - excl_ref
    trip_g_total = [e for e in G.E if e["relation"] in relaciones_esqueleto]
    excl_g = [e for e in trip_g_total if e.get("rol_fuente") == "cuarentena_laudada"]
    trip_g = {(e["source"], e["relation"], e["target"]) for e in trip_g_total if e.get("rol_fuente") != "cuarentena_laudada"}
    falt_n = sorted(ids_ref - set(G.by_id))
    falt_t = sorted(trip_ref - trip_g)
    return {"pass": not falt_n and not falt_t and len(trip_g) == len(trip_ref),
            "nodos_esqueleto_esperados": len(ids_ref), "faltan_nodos": falt_n,
            "aristas_esqueleto_referencia": len(trip_ref), "aristas_excluidas_referencia_cuarentena_laudada": len(excl_ref),
            "aristas_esqueleto_en_grafo": len(trip_g), "aristas_excluidas_grafo_cuarentena_laudada": len(excl_g),
            "aristas_relaciones_esqueleto_total_grafo": len(trip_g_total), "faltan_triplas": falt_t}


def esqueleto_de_catalogo(ruta_catalogo, relaciones: tuple) -> tuple:
    """R-T4 (D1 de U-PRE-R2-DIAG, propuesta A; U-R2-CODIGO, R5.a): nodos y
    aristas de relaciones de esqueleto que assemble.build_skeleton
    (grafo_v2/code/assemble.py:118) construye sobre el catálogo, invocado por
    import vía ensamblar_corpus.inyectar_esqueleto_v3 sobre un grafo vacío."""
    for p in (str(CORPUS_V2), str(GRAFO_V2_CODE), str(E2_REDUCE)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import ensamblar_corpus as EC   # noqa: E402  corpus_v2/ensamblar_corpus.py:83 (inyectar_esqueleto_v3)
    kg = {"nodes": [], "edges": []}
    EC.inyectar_esqueleto_v3(kg, Path(ruta_catalogo))
    return ({n["id"] for n in kg["nodes"]},
            {(e["source"], e["relation"], e["target"]) for e in kg["edges"] if e["relation"] in relaciones})


def t4_esqueleto_catalogo(G: Grafo, nodos_cat: set, trip_cat: set, relaciones: tuple) -> dict:
    """R-T4: el esqueleto del grafo (aristas de relaciones de esqueleto, menos
    rol_fuente cuarentena_laudada) es el de build_skeleton sobre el catálogo,
    sin faltantes ni sobrantes, y sus nodos están en el grafo."""
    trip_g_total = [e for e in G.E if e["relation"] in relaciones]
    excl_g = [e for e in trip_g_total if e.get("rol_fuente") == "cuarentena_laudada"]
    trip_g = {(e["source"], e["relation"], e["target"]) for e in trip_g_total if e.get("rol_fuente") != "cuarentena_laudada"}
    falt_n = sorted(nodos_cat - set(G.by_id))
    falt_t = sorted(trip_cat - trip_g)
    sobran = sorted(trip_g - trip_cat)
    return {"pass": not falt_n and not falt_t and not sobran,
            "nodos_esqueleto_del_catalogo": len(nodos_cat), "faltan_nodos": falt_n,
            "aristas_esqueleto_del_catalogo": len(trip_cat), "aristas_esqueleto_en_grafo": len(trip_g),
            "aristas_excluidas_grafo_cuarentena_laudada": len(excl_g),
            "aristas_relaciones_esqueleto_total_grafo": len(trip_g_total),
            "faltan_triplas": [list(x) for x in falt_t], "sobran_triplas": [list(x) for x in sobran]}


def t_t4(ctx: Contexto) -> dict:
    """R-T4 (reemplaza la paridad contra --esqueleto-referencia de la decisión 8)."""
    G = ctx.grafo
    nodos_cat, trip_cat = ctx.esqueleto_catalogo
    val = t4_esqueleto_catalogo(G, nodos_cat, trip_cat, ctx.relaciones_esqueleto)
    val["catalogo"] = {"ruta": ctx.cat.ruta, "sha256": ctx.cat.sha256}
    if val["aristas_relaciones_esqueleto_total_grafo"] == 0:
        return res("no_aplicable", f"sin aristas de relaciones de esqueleto {ctx.relaciones_esqueleto}: el paso de esqueleto (E5/assemble) no corrió sobre este grafo; "
                   f"faltan {len(val['faltan_nodos'])}/{val['nodos_esqueleto_del_catalogo']} nodos de esqueleto del catálogo", valores=val)
    return res("resuelto" if val["pass"] else "persiste",
               f"R-T4: build_skeleton(catálogo) nodos={val['nodos_esqueleto_del_catalogo']} aristas={val['aristas_esqueleto_del_catalogo']}; "
               f"grafo aristas={val['aristas_esqueleto_en_grafo']} (excluidas cuarentena_laudada={val['aristas_excluidas_grafo_cuarentena_laudada']}); "
               f"faltan_nodos={len(val['faltan_nodos'])} faltan_triplas={len(val['faltan_triplas'])} sobran_triplas={len(val['sobran_triplas'])}", valores=val)


def _ancla_desde_codigo(codigo: str) -> tuple:
    """'ext::7.5.2' → (prefijo de archivo del TO, punto)."""
    to, punto = codigo.split("::", 1)
    return TO_PREFIJO[to], punto


RE_TOK_PUNTO = re.compile(r"\d+(?:\.\d+)*")


def tokens_punto(s) -> set:
    """Números de punto de un texto (regex \\d+(\\.\\d+)*, normalizados, sin punto final)."""
    return {t.rstrip(".") for t in RE_TOK_PUNTO.findall(norm(s))}


def remisiones_con_evidencia(G: Grafo) -> list:
    """Remisiones entre puntos con evidencia, en cualquiera de las dos formas (scripts/remisiones.py)."""
    return [e for e in G.E if remisiones.es_remision(e) and remisiones.evidencia(e) is not None]


def presente_por_contenido(G: Grafo, x: dict, refs: list, con_tipo: bool = True) -> list:
    """R-T5 (D1 de U-PRE-R2-DIAG, propuesta A): remisiones de `refs` con (1)
    origen anclado en x.source_ancla (todas las provenances); (2) destino
    anclado en x.target_ancla y properties.destino == x.destino; (3) tipo del
    destino == x.target_type (solo con `con_tipo`); (4) intersección no vacía
    entre los números de punto de la evidencia y los de x.evidencia_verbatim."""
    sa, sp = _ancla_desde_codigo(x["source_ancla"])
    ta, tp = _ancla_desde_codigo(x["target_ancla"])
    tok_x = tokens_punto(x["evidencia_verbatim"])
    out = []
    for e in refs:
        if not con_ancla(G.by_id.get(e["source"], {}), sa, sp):
            continue
        if not con_ancla(G.by_id.get(e["target"], {}), ta, tp) or remisiones.destino(e) != x["destino"]:
            continue
        if con_tipo and G.tipo(e["target"]) != x["target_type"]:
            continue
        if tokens_punto(remisiones.evidencia(e)) & tok_x:
            out.append(e)
    return out


def t_t5(ctx: Contexto) -> dict:
    """r1_tests.py:44-54, re-direccionado por contenido (R-T5; U-R2-CODIGO,
    R5.a) sobre la muestra sellada de 30 filas: una fila está presente si una
    remisión cumple R-T5. Lee las remisiones en las dos formas (enmienda 1,
    R5.b). Informa también la presencia verbatim (la comprobación anterior) y
    R-T5 sin la condición de tipo."""
    G = ctx.grafo
    refs = remisiones_con_evidencia(G)
    if not refs:
        return res("no_aplicable", "sin remisiones con properties.evidencia (remite_a, o referencia con rol_fuente referencia_cruzada): "
                   "el paso de remisiones no corrió sobre este grafo",
                   valores={"n_muestra": len(ctx.muestra30), "remisiones_con_evidencia": 0})
    fallas, verbatim, sin_tipo = [], 0, 0
    for x in ctx.muestra30:
        rt5 = presente_por_contenido(G, x, refs)
        rt5_st = rt5 or presente_por_contenido(G, x, refs, con_tipo=False)
        sa, sp = _ancla_desde_codigo(x["source_ancla"])
        ta, tp = _ancla_desde_codigo(x["target_ancla"])
        cands = [e for e in refs if con_ancla(G.by_id.get(e["source"], {}), sa, sp) and con_ancla(G.by_id.get(e["target"], {}), ta, tp)]
        verbatim += any(remisiones.evidencia(e) == x["evidencia_verbatim"] for e in cands)
        sin_tipo += bool(rt5_st)
        if not rt5:
            fallas.append({"n": x["n"], "source_ancla": x["source_ancla"], "target_ancla": x["target_ancla"],
                           "presente_sin_tipo": bool(rt5_st), "arista_entre_anclas": bool(cands)})
    val = {"pass": not fallas, "n_muestra": len(ctx.muestra30), "presentes_rt5": len(ctx.muestra30) - len(fallas),
           "presentes_rt5_sin_tipo": sin_tipo, "presentes_verbatim": verbatim, "fallas": fallas,
           "remisiones_con_evidencia": len(refs),
           "por_forma": dict(sorted(Counter(remisiones.forma_remision(e) for e in refs).items()))}
    return res("resuelto" if not fallas else "persiste",
               f"R-T5: presentes {val['presentes_rt5']}/{len(ctx.muestra30)} (sin tipo {sin_tipo}; verbatim {verbatim}); "
               f"remisiones con evidencia={len(refs)} {val['por_forma']}", valores=val)


def t_t6(ctx: Contexto) -> dict:
    """r1_tests.py:56-61: un TextoOrdenado por TO, con id TextoOrdenado_<slugify_full(archivo)>. U-REEXT-T0, T1,
    punto 4.a: los TOs son los del manifiesto del grafo bajo prueba (Contexto.tos_bajo_prueba); sin manifiesto, los
    cinco de desarrollo de E0, como antes (scripts/regression_kg.py:1306-1313 en 53b7708)."""
    G = ctx.grafo
    slug = ctx.e4["e2_lib"].slugify_full
    fuente, archivos = ctx.tos_bajo_prueba
    ids_esp = {f"TextoOrdenado_{slug(a)}" for a in archivos.values()}
    tos = [n for n in G.N if n.get("type") == "TextoOrdenado"]
    ids = sorted(n["id"] for n in tos)
    val = {"pass": len(tos) == len(ids_esp) and set(ids) == ids_esp, "n": len(tos), "n_esperado": len(ids_esp),
           "fuente_de_los_tos": fuente, "ids": ids, "ids_esperados": sorted(ids_esp)}
    return res("resuelto" if val["pass"] else "persiste", f"n={len(tos)} de {len(ids_esp)} ({fuente}) "
               f"fuera_del_esperado={sorted(set(ids) - ids_esp)} faltan={sorted(ids_esp - set(ids))}", valores=val)


def t7_cuarentena(G: Grafo, catalogo_ids: frozenset, politica: str) -> dict:
    """r1_tests.py:63-82 con cuarentena normalizada (decisión 2) y política
    (decisión 3): flaggeada prohíbe subclase_de desde propuesto; laudada lo
    admite hacia un id de catálogo (laudo C4) y sigue prohibiéndolo fuera."""
    assert politica in POLITICAS, politica
    propuestos = [n for n in G.N if es_propuesto(n)]
    malos = []
    for n in propuestos:
        if not cuarentena_bool(prop(n, "cuarentena")):
            malos.append((n["id"], "sin cuarentena=true"))
        if n["id"] in catalogo_ids:
            malos.append((n["id"], "propuesto con id de catálogo"))
    n_ps = 0
    for e in G.E:
        if e["relation"] == "padre_sugerido":
            n_ps += 1
            if e["target"] not in catalogo_ids:
                malos.append((e["source"], f"padre_sugerido a {e['target']} fuera de catálogo"))
        if e["relation"] == "subclase_de" and es_propuesto(G.by_id.get(e["source"], {})):
            if politica == "flaggeada":
                malos.append((e["source"], "subclase_de desde propuesto"))
            elif e["target"] not in catalogo_ids:
                malos.append((e["source"], f"subclase_de laudada a {e['target']} fuera de catálogo"))
    fuera = [n["id"] for n in G.N if n.get("type") == "Sujeto" and n["id"] not in catalogo_ids and prop(n, "nivel") != "propuesto"]
    n_sujetos = sum(1 for n in G.N if n.get("type") == "Sujeto")
    return {"pass": not malos and not fuera, "politica": politica, "n_sujetos": n_sujetos, "n_propuestos": len(propuestos),
            "n_padre_sugerido": n_ps, "malos": malos, "sujetos_fuera_catalogo_no_propuestos": fuera}


def t_t7(ctx: Contexto) -> dict:
    val = t7_cuarentena(ctx.grafo, ctx.cat.ids, ctx.politica)
    if val["n_sujetos"] == 0:
        return res("no_aplicable", "sin nodos Sujeto: test vacuo", valores=val)
    motivos = Counter(m.split(" a ")[0] for _, m in val["malos"])
    return res("resuelto" if val["pass"] else "persiste",
               f"politica={ctx.politica} propuestos={val['n_propuestos']} aristas_padre_sugerido={val['n_padre_sugerido']} malos={len(val['malos'])} "
               f"{dict(motivos)} fuera_catalogo_no_propuestos={len(val['sujetos_fuera_catalogo_no_propuestos'])}", valores=val)


def t_i1(ctx: Contexto) -> dict:
    return res("no_aplicable", "no convertible: conservación de nodos Σ pre-merge − merges = finales exige los grafos pre-merge "
               "(salida/<to>/grafo_<to>.json) y los conteos de merge, que solo existen para la cadena r1 (inventario_B21_fase1.md:135)")


def t_i2(ctx: Contexto) -> dict:
    return res("no_aplicable", "no convertible: conservación de aristas, ídem I1 (inventario_B21_fase1.md:136)")


def t_i3(ctx: Contexto) -> dict:
    """r1_invariantes.py:72-77 sobre el JSON crudo (el loader del harness funde ids duplicados en silencio, loader.py:180)."""
    G = ctx.grafo
    ids = [n["id"] for n in G.N]
    trip = [(e["source"], e["relation"], e["target"]) for e in G.E]
    dup_n, dup_t = len(ids) - len(set(ids)), len(trip) - len(set(trip))
    return res("resuelto" if dup_n == 0 and dup_t == 0 else "persiste", f"nodes={len(ids)} edges={len(trip)} ids_duplicados={dup_n} triplas_duplicadas={dup_t}",
               valores={"nodes": len(ids), "edges": len(trip), "ids_duplicados": dup_n, "triplas_duplicadas": dup_t})


def t_i4(ctx: Contexto) -> dict:
    G = ctx.grafo
    colg = [(e["source"], e["relation"], e["target"]) for e in G.E if e["source"] not in G.by_id or e["target"] not in G.by_id]
    return res("resuelto" if not colg else "persiste", f"colgantes={len(colg)}" + (f" p.ej. {colg[:3]}" if colg else ""), valores={"aristas_colgantes": len(colg)})


def t_i5(ctx: Contexto) -> dict:
    """r1_invariantes.py:83-90 sobre el adaptador: al menos una provenance por nodo y por arista."""
    G = ctx.grafo
    sin_n = [n["id"] for n in G.N if not provenances(n)]
    sin_e = [(e["source"], e["relation"], e["target"]) for e in G.E if not provenances(e)]
    return res("resuelto" if not sin_n and not sin_e else "persiste", f"nodos_sin={len(sin_n)} aristas_sin={len(sin_e)}",
               valores={"nodos_sin_provenance": len(sin_n), "aristas_sin_provenance": len(sin_e)})


# =========================================================================== #
# Tests — grupo (iii): reglas de E4 (importadas, pieza c)                     #
# =========================================================================== #
def _resolucion_propuestos(ctx: Contexto) -> list:
    """Por cada Sujeto propuesto residual: (nodo, id_resuelto, motivo, candidatos) vía r1_e4.resolver_label."""
    E4 = ctx.e4
    out = []
    for n in ctx.grafo.N:
        if es_propuesto(n):
            rid, motivo, cands = E4["r1_e4"].resolver_label(n.get("label") or "", prop(n, "padre_sugerido"), E4["indice"])
            out.append((n, rid, motivo, cands))
    return out


def _e4_criterio(ctx: Contexto, criterio: str, extra_detalle: str = "") -> dict:
    """F1 ausente: ningún propuesto residual que E4 resolvería (motivo
    resuelto_por_*) con `criterio` entre sus candidatos. Sin propuestos →
    no_aplicable (vacuo)."""
    filas = _resolucion_propuestos(ctx)
    if not filas:
        return res("no_aplicable", "sin Sujetos propuestos: la regla no tiene sobre qué aplicarse (vacuo)", valores={"n_propuestos": 0})
    resolubles = [(n["id"], rid, motivo) for n, rid, motivo, cands in filas if rid is not None and any(c == criterio for c, _ in cands)]
    con_cand = sum(1 for n, rid, motivo, cands in filas if any(c == criterio for c, _ in cands))
    return res("resuelto" if not resolubles else "persiste",
               f"propuestos={len(filas)} con candidato {criterio}={con_cand} resolubles no resueltos={len(resolubles)} {resolubles[:3]}{extra_detalle}",
               valores={"n_propuestos": len(filas), "resolubles": resolubles})


def t_e4_a1(ctx): return _e4_criterio(ctx, "label_exacto")
def t_e4_a2(ctx): return _e4_criterio(ctx, "alias_exacto")
def t_e4_a3(ctx): return _e4_criterio(ctx, "id_slug")
def t_e4_a4(ctx): return _e4_criterio(ctx, "label_singularizado")


def t_e4_a5(ctx: Contexto) -> dict:
    """alias_en_parentesis, condicionado por properties.padre_sugerido (F3): la
    condición sobre el padre la aplica resolver_label (r1_e4.py:108-112)."""
    filas = _resolucion_propuestos(ctx)
    con_padre = sum(1 for n, _, _, _ in filas if prop(n, "padre_sugerido"))
    return _e4_criterio(ctx, "alias_en_parentesis", f"; propuestos con padre_sugerido={con_padre}")


def t_e4_a6(ctx: Contexto) -> dict:
    """Ambigüedad: (i) claves ambiguas del índice del catálogo; (ii) todo alias
    en alias_resueltos re-resuelve, sin ambigüedad, al id que lo porta; (iii)
    ningún propuesto residual con motivo distinto de sin_match_en_catalogo /
    ambiguo se contabiliza acá (es de a1–a5). El caso positivo (dos criterios
    a ids distintos) no ocurre en el catálogo v2: se ejercita en el selftest."""
    E4 = ctx.e4
    ambiguas = sum(1 for v in E4["indice"].values() if v == "__AMBIGUO__")
    filas = _resolucion_propuestos(ctx)
    portadores = [n for n in ctx.grafo.N if n.get("type") == "Sujeto" and prop(n, "alias_resueltos")]
    if not filas and not portadores:
        return res("no_aplicable", f"sin propuestos ni alias_resueltos: la regla no tiene sobre qué aplicarse (claves ambiguas del índice={ambiguas})",
                   valores={"claves_ambiguas": ambiguas})
    malos = []
    for n in portadores:
        for alias in prop(n, "alias_resueltos") or []:
            rid, motivo, _ = E4["r1_e4"].resolver_label(alias, None, E4["indice"])
            if motivo == "ambiguo" or rid != n["id"]:
                malos.append((n["id"], alias, rid, motivo))
    n_amb = sum(1 for _, _, motivo, _ in filas if motivo == "ambiguo")
    return res("resuelto" if not malos else "persiste",
               f"claves ambiguas del índice={ambiguas}; propuestos residuales con motivo ambiguo={n_amb}/{len(filas)}; "
               f"alias_resueltos re-resueltos={sum(len(prop(n, 'alias_resueltos') or []) for n in portadores) - len(malos)}/"
               f"{sum(len(prop(n, 'alias_resueltos') or []) for n in portadores)} malos={malos[:3]}",
               valores={"claves_ambiguas": ambiguas, "ambiguos_residuales": n_amb, "malos": malos})


def t_e4_a7(ctx: Contexto) -> dict:
    """Lo no resuelto queda tal cual: nivel=propuesto + cuarentena=true (bool o
    "true"), y ningún Sujeto fuera del catálogo que no sea propuesto (F3 +
    F1). Es la parte de T7 que no depende de la política."""
    G = ctx.grafo
    propuestos = [n for n in G.N if es_propuesto(n)]
    fuera = [n["id"] for n in G.N if n.get("type") == "Sujeto" and n["id"] not in ctx.cat.ids and not es_propuesto(n)]
    if not propuestos and not fuera and not any(n.get("type") == "Sujeto" for n in G.N):
        return res("no_aplicable", "sin nodos Sujeto (vacuo)")
    sin_cuar = [n["id"] for n in propuestos if not cuarentena_bool(prop(n, "cuarentena"))]
    en_cat = [n["id"] for n in propuestos if n["id"] in ctx.cat.ids]
    ok = not sin_cuar and not en_cat and not fuera
    return res("resuelto" if ok else "persiste", f"propuestos={len(propuestos)} sin_cuarentena_true={len(sin_cuar)} con_id_de_catalogo={len(en_cat)} "
               f"sujetos_fuera_catalogo_no_propuestos={len(fuera)}", valores={"n_propuestos": len(propuestos), "sin_cuarentena": sin_cuar, "fuera": fuera})


def t_e4_a8(ctx: Contexto) -> dict:
    """Merge aditivo registrado: alias_resueltos (F3) en los ids de catálogo a
    los que resolvieron los propuestos de e4_propuestos.json (cadena r1,
    estado resuelto) y ausencia de esos propuestos (F1 ausente) y de aristas
    que los toquen (F4 ausente). La acumulación de provenances y el dedup de
    triplas solo son observables con el grafo pre-E4: no_aplicable, con razón."""
    G = ctx.grafo
    # R-E4a8 (D1 de U-PRE-R2-DIAG, propuesta A; U-R2-CODIGO, R5.a): la tabla
    # del ensamblado del grafo bajo prueba, junto a su kg.json
    ruta_tabla = Path(G.ruta).parent / E4_PROPUESTOS_NOMBRE if G.ruta else None
    if ruta_tabla is None or not ruta_tabla.exists():
        return res("no_aplicable", f"el ensamblado del grafo bajo prueba no tiene {E4_PROPUESTOS_NOMBRE} junto al kg.json "
                   "(el perfil r2 registra la resolución de sujetos en resolucion_sujetos.jsonl): sin evento de E4-a8 que verificar",
                   valores={"tabla": str(ruta_tabla) if ruta_tabla else None})
    tabla = json.loads(ruta_tabla.read_text(encoding="utf-8"))
    remap = [(f["id_propuesto"], f["resuelto_a"], f["label"]) for f in tabla if f.get("estado") == "resuelto"]
    portadores = {n["id"]: prop(n, "alias_resueltos") for n in G.N if n.get("type") == "Sujeto" and prop(n, "alias_resueltos")}
    presentes_prop = [p for p, _, _ in remap if p in G.by_id]
    if not portadores and not presentes_prop:
        return res("no_aplicable", f"ninguno de los {len(remap)} propuestos resueltos en r1 existe en el grafo y no hay alias_resueltos: sin evento de E4-a8 que verificar; "
                   "la acumulación de provenances y el dedup de triplas exigen el grafo pre-E4 (solo cadena r1)", valores={"remap": remap})
    sub = OrderedDict()
    for p, rid, label in remap:
        sub[f"alias_en_{rid}"] = label in (portadores.get(rid) or [])
        sub[f"ausente_{p[:40]}"] = p not in G.by_id and not G.salientes(p) and not G.entrantes(p)
    ok = all(sub.values())
    return res("resuelto" if ok else "persiste", f"alias_resueltos en {sum(1 for p, rid, l in remap if l in (portadores.get(rid) or []))}/{len(remap)} ids de catálogo; "
               f"propuestos resueltos aún presentes={len(presentes_prop)}; provenances acumuladas y dedup: no observables sin el grafo pre-E4 (no_aplicable parcial)",
               subchecks=sub, valores={"remap": remap, "portadores": portadores})


def t_e4_b(ctx: Contexto) -> dict:
    """Un único TextoOrdenado por TO con id y archivo desde E0 (= T6 + F3 properties.archivo ∈ archivos de E0).
    U-REEXT-T0, T1, punto 4.a: los archivos son los de los TOs del manifiesto del grafo bajo prueba, como en T6."""
    r = t_t6(ctx)
    G = ctx.grafo
    arch = set(ctx.tos_bajo_prueba[1].values())
    tos = [(n["id"], prop(n, "archivo")) for n in G.N if n.get("type") == "TextoOrdenado"]
    fuera = [(i, a) for i, a in tos if a not in arch]
    ok = r["estado"] == "resuelto" and not fuera
    return res("resuelto" if ok else "persiste", f"TextoOrdenado={len(tos)}; con properties.archivo en el conjunto de E0: {len(tos) - len(fuera)}/{len(tos)}; fuera={fuera}; T6={r['estado']}",
               valores={"n": len(tos), "fuera": fuera})


def t_e4_c(ctx: Contexto) -> dict:
    G = ctx.grafo
    tos = [n for n in G.N if n.get("type") == "TextoOrdenado"]
    return res("no_aplicable", "solo observable con el registro de conflictos (salida_r1/e4_conflictos.json) o los grafos pre-E4: los conflictos de "
               "properties no se persisten en el kg.json; el proxy débil (un solo valor de materia/version por TextoOrdenado) no es la regla "
               f"(inventario_B21_fase1.md:176). Informativo: TextoOrdenado={len(tos)}, materia={sorted({str(prop(n, 'materia')) for n in tos})[:6]}")


# =========================================================================== #
# Tests del perfil r2 (U-R2-CODIGO, R5.a; enmienda 1, R5.b)                   #
# =========================================================================== #
NOTA_PERFIL_EXISTENTE = ("ítem del perfil r2 (U-R2-CODIGO, R5.a; diseño de U-LISTAS-NOMAP §g): este grafo se corre con "
                         "--perfil existente, sin las marcas ni los registros del perfil r2")
EJ_DESTINO = "cla::3.7"


def t_ej_cla_5111(ctx: Contexto) -> dict:
    """Test del ejemplo `cla::5.1.1.1` (laudo de r2, §4, :334; mandato de
    U-R2-CODIGO, R5.a). (i) la Operacion del punto recibe dos vínculos
    normativos de nodos del punto: `condicion_de` desde dos Condicion o, en la
    estructura de r1, `limita` desde dos Restriccion; (ii) un nodo del punto
    remite a cla::3.7: con --perfil r2, `remite_a`; con los perfiles
    existentes, la remisión en su forma de origen (`referencia` con rol_fuente
    referencia_cruzada; enmienda 1, R5.b); (iii) informativo, con --perfil r2:
    elemento de umbral mínimo estricto, valor 2, unidad «veces», base resuelta
    a cla::3.7. Estado: resuelto si (i) y (ii)."""
    G = ctx.grafo
    ns = [n for n in G.buscar(None, CLA, "5.1.1.1") if n.get("type") in remisiones.TIPOS_CONTENIDO]
    if not ns:
        return res("no_aplicable", "sin nodos de contenido anclados en cla 5.1.1.1")
    ids = {n["id"] for n in ns}
    sub, val = OrderedDict(), OrderedDict()
    vinculos = []
    for op in (n for n in ns if n["type"] == "Operacion"):
        for rel, tipo in (("condicion_de", "Condicion"), ("limita", "Restriccion")):
            es = [e for e in G.entrantes(op["id"]) if e["relation"] == rel and e["source"] in ids and G.tipo(e["source"]) == tipo]
            if len({e["source"] for e in es}) >= 2:
                vinculos.append({"operacion": op["id"][:72], "relacion": rel, "origenes": len({e["source"] for e in es}),
                                 "no_verificadas_e3": sum(1 for e in es if e.get("no_verificada_e3"))})
    sub["i_dos_vinculos_normativos"] = bool(vinculos)
    val["i_vinculos"] = vinculos
    forma = remisiones.PREDICADO_REMISION if ctx.perfil == "r2" else remisiones.PREDICADO_REFERENCIA
    rem = [e for n in ns for e in G.salientes(n["id"])
           if remisiones.forma_remision(e) == forma and remisiones.destino(e) == EJ_DESTINO]
    sub["ii_remision_a_cla_3_7"] = bool(rem)
    val["ii_forma_exigida"] = forma
    val["ii_remisiones"] = [{"origen": G.tipo(e["source"]), "destino_tipo": G.tipo(e["target"]),
                             "alcance": (e.get("properties") or {}).get("alcance"),
                             "evidencia": remisiones.evidencia(e)} for e in rem]
    if ctx.perfil == "r2":
        elems = [u for n in ns for u in umbrales_lista(n)
                 if u.get("comparacion") == "minimo_estricto" and u.get("valor") == "2" and u.get("unidad") == "veces"
                 and u.get("base_destino") == EJ_DESTINO]
        val["iii_informativo_umbral_minimo_estricto_2_veces_base_cla_3_7"] = bool(elems)
        val["iii_elementos"] = elems
    estado = "resuelto" if all(sub.values()) else "persiste"
    nv = sum(v["no_verificadas_e3"] for v in vinculos)
    det = (f"(i) {sub['i_dos_vinculos_normativos']} {[(v['relacion'], v['origenes']) for v in vinculos]}"
           + (f" [{nv} relaciones marcadas no_verificada_e3: todavía no pasaron por E3]" if nv else "")
           + f"; (ii) {forma} a {EJ_DESTINO}: {len(rem)}"
           + (f"; (iii) informativo: {val['iii_informativo_umbral_minimo_estricto_2_veces_base_cla_3_7']}" if ctx.perfil == "r2" else ""))
    return res(estado, det, subchecks=sub, valores=val)


def _campos_con_lista(enums: dict) -> tuple:
    """(tipo de nodo, campo) y campos del elemento de umbral con lista cerrada,
    leídos de pyd_r2/generados/enums_r2.json (claves «Tipo.campo» y «umbral.campo»)."""
    tipos = set(enums.get("tipo_entidad") or [])
    nodo = [(k.split(".", 1)[0], k.split(".", 1)[1], tuple(v)) for k, v in enums.items()
            if "." in k and k.split(".", 1)[0] in tipos and isinstance(v, list)]
    umbral = [(k.split(".", 1)[1], tuple(v)) for k, v in enums.items() if k.startswith("umbral.") and isinstance(v, list)]
    return nodo, umbral


def t_ln_1(ctx: Contexto) -> dict:
    """LN-1: ningún valor fuera de lista sin tratar. Todo campo con lista
    cerrada (del nodo y del elemento de umbral) está en la lista o lleva la
    marca `fuera_de_lista`; un valor de la lista con la marca también es
    defecto. Cubre además el test de L-ESQ-R2 §1.5 (comparación, unidad y
    frecuencia en su lista o con marca; todo elemento con `tramo_verificado`)."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    G, enums = ctx.grafo, ctx.enums_r2
    campos_nodo, campos_umbral = _campos_con_lista(enums)
    tramo_ok = set(enums.get("tramo_verificado") or [])
    sin_tratar, marca_de_mas = Counter(), Counter()
    marcados, ejemplos = Counter(), []
    elems = sin_tramo = 0
    for n in G.N:
        fl = n.get("fuera_de_lista") or []
        for tipo, campo, lista in campos_nodo:
            if n.get("type") != tipo or prop(n, campo) is None:
                continue
            v = prop(n, campo)
            if v not in lista and campo not in fl:
                sin_tratar[f"{tipo}.{campo}"] += 1
                ejemplos.append((n["id"][:60], campo, v))
            elif v in lista and campo in fl:
                marca_de_mas[f"{tipo}.{campo}"] += 1
            elif campo in fl:
                marcados[f"{tipo}.{campo}"] += 1
        for u in umbrales_lista(n):
            elems += 1
            ufl = u.get("fuera_de_lista") or []
            if u.get("tramo_verificado") not in tramo_ok:
                sin_tramo += 1
            for campo, lista in campos_umbral:
                v = u.get(campo)
                if v is None:
                    continue
                if v not in lista and campo not in ufl:
                    sin_tratar[f"umbral.{campo}"] += 1
                    ejemplos.append((n["id"][:60], f"umbral.{campo}", v))
                elif v in lista and campo in ufl:
                    marca_de_mas[f"umbral.{campo}"] += 1
                elif campo in ufl:
                    marcados[f"umbral.{campo}"] += 1
    ok = not sin_tratar and not marca_de_mas and not sin_tramo
    val = {"campos_nodo": [f"{t}.{c}" for t, c, _ in campos_nodo], "campos_umbral": [c for c, _ in campos_umbral],
           "sin_tratar": dict(sorted(sin_tratar.items())), "marca_en_valor_de_la_lista": dict(sorted(marca_de_mas.items())),
           "fuera_de_lista_marcados": dict(sorted(marcados.items())), "elementos_de_umbral": elems,
           "elementos_sin_tramo_verificado_valido": sin_tramo, "ejemplos": ejemplos[:10]}
    return res("resuelto" if ok else "persiste",
               f"sin tratar {sum(sin_tratar.values())} {dict(sin_tratar)}; marca en valor de la lista {sum(marca_de_mas.values())}; "
               f"marcados fuera de lista {dict(sorted(marcados.items()))}; elementos de umbral {elems} (sin tramo_verificado válido {sin_tramo})",
               valores=val)


def t_ln_2(ctx: Contexto) -> dict:
    """LN-2: las `properties` de cada nodo de los nueve tipos están dentro de
    la definición del tipo (claves_por_tipo de enums_r2.json más las marcas de
    nodo de modelos_r2.MARCAS_NODO); lo demás vive en `properties_no_definidas`
    (o en `campos_heredados_v3`), y nada definido figura como no definido."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    G, enums = ctx.grafo, ctx.enums_r2
    claves = {t: set(v) | set(ctx.marcas_nodo_r2) for t, v in (enums.get("claves_por_tipo") or {}).items()}
    fuera, definida_como_no, n_eval = Counter(), Counter(), 0
    ejemplos = []
    for n in G.N:
        t = n.get("type")
        if t not in claves:
            continue
        n_eval += 1
        for k in (n.get("properties") or {}):
            if k not in claves[t]:
                fuera[f"{t}.{k}"] += 1
                ejemplos.append((n["id"][:60], k))
        for k in (n.get("properties_no_definidas") or {}):
            if k in claves[t]:
                definida_como_no[f"{t}.{k}"] += 1
    ok = not fuera and not definida_como_no
    return res("resuelto" if ok else "persiste",
               f"nodos evaluados {n_eval}; claves fuera de la definición {sum(fuera.values())} {dict(sorted(fuera.items()))}; "
               f"definidas que figuran como no definidas {sum(definida_como_no.values())}; con properties_no_definidas "
               f"{sum(1 for n in G.N if n.get('properties_no_definidas'))}",
               valores={"fuera_de_la_definicion": dict(sorted(fuera.items())), "definidas_como_no_definidas": dict(sorted(definida_como_no.items())),
                        "marcas_nodo": list(ctx.marcas_nodo_r2), "ejemplos": ejemplos[:10]})


def _aristas_de_sujeto(ctx: Contexto) -> list:
    preds = set(ctx.enums_r2.get("predicados_sujeto") or [])
    return [e for e in ctx.grafo.E if e.get("relation") in preds and e.get("rol_fuente") != "esqueleto"]


def t_ln_3(ctx: Contexto) -> dict:
    """LN-3: toda arista de sujeto (aplica_a, ejecuta) que no es de esqueleto
    lleva la mención (`sujeto_mencion`) y `mencion_verificada` en su lista
    (L-ESQ-R2 §3.5). En r2a la mención falta salvo donde el crudo guardó el
    sujeto propuesto: persiste hasta r2b (P-b1)."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    lista = set(ctx.enums_r2.get("mencion_verificada") or [])
    es = _aristas_de_sujeto(ctx)
    if not es:
        return res("no_aplicable", "sin aristas de sujeto fuera del esqueleto")
    con_mencion = sum(1 for e in es if (e.get("sujeto_mencion") or "").strip())
    con_verif = sum(1 for e in es if e.get("mencion_verificada") in lista)
    ambas = sum(1 for e in es if (e.get("sujeto_mencion") or "").strip() and e.get("mencion_verificada") in lista)
    por_verif = dict(sorted(Counter(str(e.get("mencion_verificada")) for e in es).items()))
    return res("resuelto" if ambas == len(es) else "persiste",
               f"aristas de sujeto {len(es)}: con mención {con_mencion}, con mencion_verificada en la lista {con_verif}, con las dos {ambas}; "
               f"mencion_verificada {por_verif}",
               valores={"aristas": len(es), "con_mencion": con_mencion, "con_mencion_verificada": con_verif, "con_las_dos": ambas,
                        "por_mencion_verificada": por_verif})


def t_ln_4(ctx: Contexto) -> dict:
    """LN-4: toda arista de sujeto que no es de esqueleto lleva
    `metodo_resolucion`; los desacuerdos entre la regla y el modelo se cuentan
    (resolucion_sujetos.jsonl del ensamblado, campo desacuerdo_regla_modelo)."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    es = _aristas_de_sujeto(ctx)
    if not es:
        return res("no_aplicable", "sin aristas de sujeto fuera del esqueleto")
    sin = [e for e in es if not e.get("metodo_resolucion")]
    filas = ctx.registro(RESOLUCION_SUJETOS)
    desac = None if filas is None else sum(1 for f in filas if f.get("desacuerdo_regla_modelo"))
    por_metodo = dict(sorted(Counter(str(e.get("metodo_resolucion")) for e in es).items()))
    return res("resuelto" if not sin else "persiste",
               f"aristas de sujeto {len(es)}, sin metodo_resolucion {len(sin)}; por método {por_metodo}; desacuerdos regla/modelo "
               + (str(desac) if desac is not None else f"no computable (sin {RESOLUCION_SUJETOS})"),
               valores={"aristas": len(es), "sin_metodo": len(sin), "por_metodo": por_metodo, "desacuerdos_regla_modelo": desac})


def t_ln_5(ctx: Contexto) -> dict:
    """LN-5: registro y grafo coinciden. Cada Sujeto propuesto tiene al menos
    una fila en no_mapeados_sujetos.jsonl (campo id_nodo) y cada fila en
    cuarentena tiene su nodo."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    filas = ctx.registro(REGISTRO_NO_MAPEADOS)
    if filas is None:
        return res("no_aplicable", f"sin {REGISTRO_NO_MAPEADOS} en {ctx.registro_dir}: el registro no se puede cotejar")
    G = ctx.grafo
    propuestos = {n["id"] for n in G.N if es_propuesto(n)}
    con_fila = {f.get("id_nodo") for f in filas}
    sin_fila = sorted(propuestos - con_fila)
    cuar_sin_nodo = sorted({f.get("id_nodo") for f in filas if f.get("estado") == "cuarentena"} - set(G.by_id))
    return res("resuelto" if not sin_fila and not cuar_sin_nodo else "persiste",
               f"filas {len(filas)} {dict(sorted(Counter(str(f.get('estado')) for f in filas).items()))}; propuestos {len(propuestos)}; "
               f"propuestos sin fila {len(sin_fila)}; filas en cuarentena sin nodo {len(cuar_sin_nodo)}",
               valores={"filas": len(filas), "propuestos": len(propuestos), "propuestos_sin_fila": sin_fila,
                        "cuarentena_sin_nodo": cuar_sin_nodo})


def t_ln_6(ctx: Contexto) -> dict:
    """LN-6: la re-resolución es idempotente. r1_e4.reresolver_registro
    (P-d3), importado, con el índice del mismo catálogo
    (generados_r2/indice_e4_r2.json y rol_por_to_r2.json), deja el registro
    byte a byte igual. El contrafáctico de N1 (3/1/4) con el catálogo ampliado
    de R-CAT es del catálogo v3: el catálogo r2 ya contiene los ids de R-CAT
    (U-CAT-UNICO), así que no se reproduce acá. Con --generados-resolucion (R2
    de U-RERESOL-CAT, W3), el índice, el rol_por_to y el sha son los del
    catálogo de resolución que leyó el ensamblado, cargado con su candado
    (r1_e4.catalogo_resolucion_r2)."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    filas = ctx.registro(REGISTRO_NO_MAPEADOS)
    if filas is None:
        return res("no_aplicable", f"sin {REGISTRO_NO_MAPEADOS} en {ctx.registro_dir}")
    E4 = ctx.e4["r1_e4"]
    if ctx.generados_resolucion is None:
        idx = E4.indice_desde_lista(json.loads((GENERADOS_R2 / "indice_e4_r2.json").read_text(encoding="utf-8")))
        rol_por_archivo = json.loads((GENERADOS_R2 / "rol_por_to_r2.json").read_text(encoding="utf-8"))
        sha_cat = sha256_path(CATALOGO_SUJETOS_R2)
        cual = ""
    else:
        cat_res = E4.catalogo_resolucion_r2(ctx.generados_resolucion)
        idx, rol_por_archivo, sha_cat = cat_res["indice"], cat_res["rol_por_to"], cat_res["catalogo_sha256"]
        cual = f" de resolución ({ctx.generados_resolucion})"
    archivo_por_to = {}
    for n in ctx.grafo.N:
        for pv in provenances(n):
            if pv.get("to") and pv.get("archivo"):
                archivo_por_to.setdefault(pv["to"], pv["archivo"])
    r = E4.reresolver_registro(filas, idx, rol_por_archivo, archivo_por_to, sha_cat)
    antes = [json.dumps(f, ensure_ascii=False, sort_keys=True) for f in filas]
    despues = [json.dumps(f, ensure_ascii=False, sort_keys=True) for f in r["filas"]]
    igual = antes == despues
    return res("resuelto" if igual and not r["resueltas_ahora"] else "persiste",
               f"re-resolución con el mismo catálogo{cual} (sha {sha_cat[:12]}…): filas {len(filas)}, resueltas ahora {r['resueltas_ahora']}, "
               f"registro igual byte a byte: {igual}",
               valores={"filas": len(filas), "resueltas_ahora": r["resueltas_ahora"], "igual": igual})


def t_ln_7(ctx: Contexto) -> dict:
    """LN-7: toda omisión con categoría del enum y tramo verificado o marcado;
    0 chunks marcados con extracción y sin omisión. Las omisiones con
    categoría y tramo son de r2b (L-ESQ-R2 §5.4); el ensamblado r2a no deja
    un registro de omisiones junto al grafo."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    filas = ctx.registro("omisiones.jsonl")
    if filas is None:
        return res("no_aplicable", f"sin registro de omisiones (omisiones.jsonl) en {ctx.registro_dir}: las omisiones con categoría y tramo "
                   "las emite E1 en r2b (L-ESQ-R2 §5.4)")
    cats = set(ctx.enums_r2.get("omision.categoria") or [])
    malas = [f for f in filas if not ((f.get("categoria") in cats or "categoria" in (f.get("fuera_de_lista") or []))
                                      and f.get("tramo_verificado") in (ctx.enums_r2.get("tramo_verificado") or []))]
    return res("resuelto" if not malas else "persiste", f"omisiones {len(filas)}; sin categoría del enum o sin tramo verificado/marcado {len(malas)}",
               valores={"omisiones": len(filas), "malas": len(malas)})


RE_ID_BLOQUE = re.compile(r"^(Sujeto_[a-z0-9_]+) — (.+?)(?: \(alias: (.+?)\))?( \[instancia\])?(?: \[rol del TO ([^\]]+)\])?$")


def lineas_bloque(texto_bloque: str) -> dict:
    """id → (label, alias, es_instancia, TO del rol) de cada línea de sujeto del
    bloque, con la forma `id — label[ (alias: …)][ [instancia]][ [rol del TO x]]`
    (catalogo_unico/code/generar_desde_catalogo.py:96-106)."""
    out = {}
    for linea in texto_bloque.splitlines():
        m = RE_ID_BLOQUE.match(linea)
        if m:
            out[m.group(1)] = (m.group(2), m.group(3) or "", bool(m.group(4)), m.group(5))
    return out


def t_ln_8(ctx: Contexto) -> dict:
    """LN-8: catálogo único. El bloque del prompt generado
    (generados_r2/bloque_catalogo_r2.txt) y el JSON único
    (catalogo_sujetos_r2.json, sujetos con estado vigente) no difieren: mismos
    ids, y por id el mismo label, los mismos alias, la misma marca de instancia
    y el mismo TO del rol. Los retiros con lápida no van al bloque."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    bloque = lineas_bloque((GENERADOS_R2 / "bloque_catalogo_r2.txt").read_text(encoding="utf-8"))
    cat = json.loads(CATALOGO_SUJETOS_R2.read_text(encoding="utf-8"))
    vig = {x["id"]: (x.get("label"), ", ".join(x.get("alias") or []), x.get("nivel") == "instancia",
                     (x.get("rol_por_to") or [None])[0] if x.get("nivel") == "rol" else None)
           for x in cat.get("sujetos") or [] if (x.get("estado") or {}).get("valor") == "vigente"}
    lapidas = sorted(x["id"] for x in cat.get("sujetos") or [] if (x.get("estado") or {}).get("valor") == "lapida")
    solo_bloque, solo_json = sorted(set(bloque) - set(vig)), sorted(set(vig) - set(bloque))
    distintos = sorted(i for i in set(bloque) & set(vig) if bloque[i] != vig[i])
    ok = not solo_bloque and not solo_json and not distintos
    return res("resuelto" if ok else "persiste",
               f"bloque {len(bloque)} ids, JSON vigentes {len(vig)} (lápidas {len(lapidas)}); solo en el bloque {len(solo_bloque)}, "
               f"solo en el JSON {len(solo_json)}, con label, alias, instancia o TO del rol distintos {len(distintos)}",
               valores={"solo_en_bloque": solo_bloque, "solo_en_json": solo_json, "distintos": distintos, "lapidas": lapidas,
                        "catalogo_sha256": sha256_path(CATALOGO_SUJETOS_R2)})


# =========================================================================== #
# Censos informativos (U-R2-CODIGO, R5.a y enmienda 1, R5.b): fuera de los     #
# ítems y de la fixture                                                        #
# =========================================================================== #
def misma_descripcion(a, b) -> bool:
    """Dos descripciones iguales salvo espacios, mayúsculas y acentos (norm)."""
    if not a or not b:
        return False
    return " ".join(norm(a).split()) == " ".join(norm(b).split())


def censo_igual_descripcion(G: Grafo, limite: int = 50) -> dict:
    """Aristas entre dos nodos distintos con la misma `properties.descripcion`
    (L-ESQ-R2 §6.5; laudo de r2, §4): informativo, sin regla de retiro."""
    filas, por_rel = [], Counter()
    for e in G.E:
        if e["source"] == e["target"]:
            continue
        a, b = G.by_id.get(e["source"]), G.by_id.get(e["target"])
        if a is None or b is None or not misma_descripcion(prop(a, "descripcion"), prop(b, "descripcion")):
            continue
        clave = f"{a.get('type')} --{e['relation']}--> {b.get('type')}"
        por_rel[clave] += 1
        filas.append({"relacion": clave, "chunk_id": (e.get("provenance") or {}).get("chunk_id"),
                      "descripcion": (prop(a, "descripcion") or "")[:120]})
    return {"aristas": len(filas), "por_firma": dict(sorted(por_rel.items())), "primeras": filas[:limite],
            "regla_de_retiro": "ninguna (censo informativo)"}


def control_igual_descripcion_lectura() -> dict:
    """Control del censo sobre las 105 relaciones de la lectura de la matriz
    (reports/u_estudio_matriz/lectura/): debe marcar C22, M50 y M56 a M59; M50
    es correcta en la lectura (caso a revisar)."""
    import csv   # noqa: PLC0415
    filas = []
    for nombre in LECTURA_MATRIZ_CSV:
        with open(LECTURA_MATRIZ / nombre, encoding="utf-8-sig", newline="") as f:
            filas += list(csv.DictReader(f))
    marcadas = [r["id_muestra"] for r in filas if misma_descripcion(r["origen_descripcion"], r["destino_descripcion"])]
    return {"relaciones": len(filas), "marcadas": marcadas,
            "correctas_en_la_lectura_entre_las_marcadas": [r["id_muestra"] for r in filas
                                                           if r["id_muestra"] in marcadas and r.get("veredicto") == "correcta"]}


def censo_remisiones(G: Grafo) -> dict:
    """Remisiones por forma, por firma y por alcance, en aristas y en citas
    (cita = chunk de origen, evidencia y destino). Para la forma
    `referencia` de los grafos existentes, el alcance es el de la regla de la
    enmienda 2 de L-ESQ-R2 §3, aplicada (remisiones.alcance_esperado)."""
    por_forma, por_firma, por_alcance, citas, citas_alcance = Counter(), Counter(), Counter(), set(), Counter()
    for e in G.E:
        forma = remisiones.forma_remision(e)
        if forma is None:
            continue
        a, b = G.by_id.get(e["source"]) or {}, G.by_id.get(e["target"]) or {}
        pv = e.get("provenance") or {}
        alc = (e.get("properties") or {}).get("alcance") if forma == remisiones.PREDICADO_REMISION else \
            remisiones.alcance_esperado(remisiones.destino(e), pv.get("to"), b.get("type") == remisiones.TIPO_TEXTO_ORDENADO)
        por_forma[forma] += 1
        por_firma[f"{a.get('type')}->{b.get('type')}"] += 1
        por_alcance[str(alc)] += 1
        cita = (pv.get("chunk_id"), remisiones.evidencia(e), remisiones.destino(e))
        if cita not in citas:
            citas.add(cita)
            citas_alcance[str(alc)] += 1
    return {"aristas": sum(por_forma.values()), "por_forma": dict(sorted(por_forma.items())),
            "aristas_por_alcance": dict(sorted(por_alcance.items())), "aristas_por_firma": dict(sorted(por_firma.items())),
            "citas": len(citas), "citas_por_alcance": dict(sorted(citas_alcance.items())),
            "firmas_fuera_de_remite_a": sum(v for k, v in por_firma.items()
                                            if not remisiones.firma_remite_a_ok(*k.split("->", 1)))}


# =========================================================================== #
# Tests de U-REEXT-T0, T1, punto 4 (mandato firmado en e2027dd)               #
# =========================================================================== #
RE_75 = re.compile(r"(?<![\d.,])75(?![\d.,])")
RE_TRES = re.compile(r"(?<![\d.,])3(?![\d.,])|\btres\b")
TIPOS_NORMA = ("Obligacion", "Restriccion", "Potestad")
EXPEDIENTE = "data/backlog/expediente_retriage_v3.md"


def cubre_to(G: Grafo, archivo_pref: str) -> bool:
    """¿El grafo tiene nodos de contenido del TO? Los Sujeto del esqueleto llevan la procedencia del catálogo
    (source_doc y location del TO donde se dio de alta el id): no cuentan como cobertura."""
    return any(n.get("type") != "Sujeto" for n in G.buscar(None, archivo_pref))


def t_bkl_0001(ctx: Contexto) -> dict:
    """BKL-0001 por punto (punto 4.f, como T1 lo es de BKL-0024). El contenido sale del expediente del retriage
    (EXPEDIENTE, E1): la exposición máxima frente a una misma contraparte individual, para personas humanas en
    cartera de consumo, de 75 veces el Salario Mínimo, Vital y Móvil (cap 2.8.3.3). Resuelto: algún nodo anclado en
    cap 2.8.3.3 dice «75» y «salario minimo». El defecto registrado es que el contenido estaba anclado en otro punto
    (location «Punto 2.10.», RX-03). no_aplicable: el grafo no tiene nodos anclados en Capitales Mínimos."""
    G = ctx.grafo
    if not cubre_to(G, CAP):
        return res("no_aplicable", "el grafo no tiene nodos anclados en Capitales Mínimos")
    nodos = G.buscar(None, CAP, "2.8.3.3")
    con = [n for n in nodos if RE_75.search(texto(n)) and "salario minimo" in texto(n)]
    val = {"pass": bool(con), "nodos_anclados_2_8_3_3": len(nodos),
           "nodos_con_75_veces_smvm": [{"id": n["id"][:72], "type": n.get("type"), "label": n.get("label")} for n in con][:6]}
    return res("resuelto" if con else "persiste", f"anclados_2_8_3_3={len(nodos)} con_75_veces_smvm={len(con)}", valores=val)


def t_bkl_0002(ctx: Contexto) -> dict:
    """BKL-0002 por punto (punto 4.f). El contenido sale del expediente del retriage (EXPEDIENTE, E2): «El acceso al
    mercado de cambios se produce con una anterioridad no mayor a los 3 (tres) días hábiles a la fecha de vencimiento
    del servicio de capital o interés a pagar» (ext 3.5.3). Resuelto: algún nodo anclado en ext 3.5.3 o en uno de sus
    sub-puntos dice «dias habiles», «3» o «tres», «vencimiento» y «capital» o «interes». El defecto registrado es que
    el contenido estaba anclado en otros puntos (locations «Punto 1.2.» y «Punto 3.17.», RX-02 y RX-03).
    no_aplicable: el grafo no tiene nodos anclados en Exterior y Cambios."""
    G = ctx.grafo
    if not cubre_to(G, EXT):
        return res("no_aplicable", "el grafo no tiene nodos anclados en Exterior y Cambios")
    nodos = G.buscar(None, EXT, "3.5.3", prefijo_punto=True)

    def dice(n: dict) -> bool:
        t = texto(n)
        return "dias habiles" in t and bool(RE_TRES.search(t)) and "vencimiento" in t and ("capital" in t or "interes" in t)
    con = [n for n in nodos if dice(n)]
    puntos = sorted({p for n in con for a, p in anclas(n) if a.startswith(EXT)})
    val = {"pass": bool(con), "nodos_anclados_3_5_3": len(nodos), "puntos": puntos,
           "nodos_con_la_ventana": [{"id": n["id"][:72], "type": n.get("type"), "label": n.get("label")} for n in con][:6]}
    return res("resuelto" if con else "persiste", f"anclados_3_5_3={len(nodos)} con_la_ventana_de_3_dias_habiles={len(con)} "
               f"puntos={puntos}", valores=val)


def t_firmas_condicion_de(ctx: Contexto) -> dict:
    """Las dos firmas nuevas de `condicion_de` (punto 4.c; L-ESQ-R2 §6.3 y §6.5): Condicion → Operacion y
    Condicion → Potestad están en la matriz del perfil r2 (`firmas_r2` y `ampliacion_r2` de enums_r2.json), y el
    grafo no tiene relaciones marcadas como no verificadas por E3 (`no_verificada_e3`), que en el grafo de la
    release tiene que dar 0 (en r2a entran marcadas por la firma: §6.4). Los conteos de las dos firmas son
    informativos: su confirmación es la lectura posterior a U-REEXT-T0 (§6.3)."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    G = ctx.grafo
    dom, rng = (ctx.enums_r2.get("firmas_r2") or {}).get("condicion_de") or [[], []]
    amp = {tuple(x) for x in ctx.enums_r2.get("ampliacion_r2") or []}
    en_matriz = OrderedDict((f"Condicion->{t}", "Condicion" in dom and t in rng and ("condicion_de", "Condicion", t) in amp)
                            for t in ("Operacion", "Potestad"))
    por_destino = Counter(G.tipo(e["target"]) for e in G.E
                          if e.get("relation") == "condicion_de" and G.tipo(e["source"]) == "Condicion")
    nv = [e for e in G.E if e.get("no_verificada_e3")]
    nv_firma = Counter(f"{G.tipo(e['source'])}-{e['relation']}-{G.tipo(e['target'])}" for e in nv)
    sub = OrderedDict([("firmas_en_la_matriz", all(en_matriz.values())), ("cero_no_verificadas_e3", not nv)])
    val = {"firmas_en_la_matriz": en_matriz,
           "condicion_de_desde_condicion_por_destino": dict(sorted(por_destino.items(), key=lambda kv: str(kv[0]))),
           "no_verificadas_e3": len(nv), "no_verificadas_e3_por_firma": dict(sorted(nv_firma.items()))}
    return res("resuelto" if all(sub.values()) else "persiste",
               f"matriz {dict(en_matriz)}; condicion_de → Operacion {por_destino.get('Operacion', 0)}, → Potestad "
               f"{por_destino.get('Potestad', 0)}; no_verificada_e3 {len(nv)} {dict(sorted(nv_firma.items()))}",
               subchecks=sub, valores=val)


# Exentos del control de cero elementos sin verificar (FRENO P3 de U-PROMPT-R2, A3, punto 5; 4aa92c7): los
# elementos de umbral, los Sujeto (no están entre los nueve tipos), el TextoOrdenado canónico y las aristas derivadas.
ROL_FUENTE_DERIVADA = ("derivada_de_procedencia", "esqueleto")
REPORTE_ENSAMBLADO_R2 = "reporte_ensamblado_r2.json"


def es_derivada(e: dict) -> bool:
    return e.get("rol_fuente") in ROL_FUENTE_DERIVADA or e.get("relation") == remisiones.PREDICADO_REMISION


def t_sin_verif_e3(ctx: Contexto) -> dict:
    """Cero elementos de extracción sin verificar por E3 (punto 4.e), con la especificación del FRENO P3 de
    U-PROMPT-R2, A3 (data/experiment/prompt_r2/freno_p3.md, seis puntos; 4aa92c7):
      1. ámbito: perfil r2 y fase r2b (la fase sale del reporte del ensamblado, `fase`); con r2a, no_aplicable;
      2. aristas de E1 (predicados de enums_r2 que no son derivadas: rol_fuente derivada_de_procedencia o esqueleto,
         o `remite_a`) sin `no_verificada_e3`;
      3. nodos de los nueve tipos, salvo el TextoOrdenado: todo nodo tiene una procedencia de una unidad
         (chunk_id); el que viene de la cola humana lleva la marca `cola_humana` y se cuenta aparte;
      4. el registro de la entrada, del reporte del ensamblado r2b (punto s de C2 de U-R2-CODIGO-2,
         `paso_por_e3.total`): 0 entidades y 0 relaciones sin verificar fuera de la cola, y 0 aristas
         `aristas_no_verificadas_e3`; la cola, los excluidos (`no_vistos_e3`) y las unidades sin índices, aparte;
      5. exentos: ROL_FUENTE_DERIVADA, `remite_a`, los Sujeto, el TextoOrdenado y los elementos de umbral;
      6. persiste con cualquier conteo mayor que 0."""
    if ctx.perfil != "r2":
        return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
    p = ctx.registro_dir / REPORTE_ENSAMBLADO_R2 if ctx.registro_dir is not None else None
    if p is None or not p.exists():
        return res("no_aplicable", f"sin {REPORTE_ENSAMBLADO_R2} en {ctx.registro_dir}: el control lee el conteo del "
                   "reporte del ensamblado r2b")
    rep = json.loads(p.read_text(encoding="utf-8"))
    if rep.get("fase") != "r2b":
        return res("no_aplicable", f"fase {rep.get('fase') or 'r2a'}: el control rige desde r2b; los grafos r2a llevan "
                   "la marca no_verificada_e3 por la firma (FRENO P3 de U-PROMPT-R2, A3, punto 1)")
    G = ctx.grafo
    preds = set(ctx.enums_r2.get("predicado") or [])
    tipos = set(ctx.enums_r2.get("tipo_entidad") or []) - {"TextoOrdenado"}
    aristas_e1 = [e for e in G.E if e.get("relation") in preds and not es_derivada(e)]
    sin_verif = [e for e in aristas_e1 if e.get("no_verificada_e3")]
    nodos = [n for n in G.N if n.get("type") in tipos]
    sin_proc = [n for n in nodos if not any(pv.get("chunk_id") for pv in provenances(n))]
    cola = [n for n in nodos if str(prop(n, "cola_humana")).lower() == "true"]
    tot = (rep.get("paso_por_e3") or {}).get("total") or {}
    conteos = OrderedDict([("aristas_e1_con_no_verificada_e3", len(sin_verif)),
                           ("nodos_sin_procedencia_de_unidad", len(sin_proc)),
                           ("registro_entidades_sin_verificar", tot.get("entidades_sin_verificar")),
                           ("registro_relaciones_sin_verificar", tot.get("relaciones_sin_verificar")),
                           ("reporte_aristas_no_verificadas_e3", (rep.get("aristas_no_verificadas_e3") or {}).get("total"))])
    ausentes = [k for k, v in conteos.items() if v is None]
    ok = not ausentes and all(v == 0 for v in conteos.values())
    aparte = {"cola_humana_registro": tot.get("cola_humana"), "nodos_con_la_marca_de_la_cola": len(cola),
              "aristas_derivadas_que_tocan_un_nodo_solo_de_la_cola":
                  rep.get("aristas_derivadas_que_tocan_un_nodo_solo_de_la_cola"),
              "no_vistos_e3": {"entidades": tot.get("excluidos_entidades"), "relaciones": tot.get("excluidos_relaciones")},
              "unidades_sin_indices_e3": tot.get("unidades_sin_indices_e3")}
    return res("resuelto" if ok else "persiste",
               f"{dict(conteos)}" + (f"; ausentes del reporte: {ausentes}" if ausentes else "")
               + f"; aparte: cola {tot.get('cola_humana')}, nodos con la marca {len(cola)}",
               valores={"conteos": conteos, "aparte": aparte, "aristas_e1": len(aristas_e1), "nodos": len(nodos),
                        "ejemplos_sin_verificar": [(e["source"][:60], e["relation"], e["target"][:60]) for e in sin_verif[:5]],
                        "ejemplos_sin_procedencia": [n["id"][:72] for n in sin_proc[:5]]})


# Una entrada por cada id nuevo decidido (punto 4.d; L-ESQ-R2 §7.3 y §7.5), leída contra su chunk. «lectura» es mi
# lectura de la e0 de la tanda 0 (salida_tanda0_r2b, 9f6361e) hecha en T1; «anclas»: (archivo, punto, prefijo,
# id que no debe recibir la norma) donde el id es el sujeto de la norma.
DEF_IDS_NUEVOS = OrderedDict([
    ("Sujeto_entidad_financiera_del_exterior", {
        "bkl": "BKL-0028", "domestico": "Sujeto_entidad_financiera", "anclas": (),
        "lectura": "34 chunks de la tanda 0 nombran a las entidades financieras del exterior; en los 34 son "
                   "contraparte u objeto (prestamista, depositario, beneficiario, garante), no el sujeto de una norma"}),
    ("Sujeto_banco_del_exterior", {
        "bkl": "BKL-0028", "domestico": "Sujeto_banco", "anclas": (),
        "lectura": "9 chunks de la tanda 0 nombran a los bancos del exterior; en los 9 son contraparte u objeto"}),
    ("Sujeto_entidad_cambiaria_del_exterior", {
        "bkl": "BKL-0028", "domestico": "Sujeto_entidad_cambiaria", "anclas": (),
        "lectura": "ningún chunk de la tanda 0 nombra a las entidades cambiarias o compañías cambistas del exterior"}),
    ("Sujeto_titular_de_cuenta_corriente_en_el_bcra", {
        "bkl": "BKL-0029", "rol": "Sujeto_rol_alcance_convca", "anclas": (),
        "lectura": "ningún chunk de la tanda 0 nombra a los titulares de cuenta corriente en el BCRA (convca no está "
                   "en la tanda 0): la condición de cierre es la del rol de convca"}),
    ("Sujeto_instancia_de_gobierno_societario", {
        "bkl": "BKL-0034", "subclases": ("Sujeto_directorio", "Sujeto_alta_gerencia", "Sujeto_comite_de_auditoria"),
        "anclas": (),
        "lectura": "clase que agrupa a los tres órganos; ningún chunk de la tanda 0 la nombra"}),
    ("Sujeto_directorio", {
        "bkl": "BKL-0034", "padre": "Sujeto_instancia_de_gobierno_societario",
        "anclas": (("lingob", "2.3.2", False, "Sujeto_entidad_financiera"),),
        "lectura": "lingob::2.3.2::intro: «2.3.2. Se asegurará de que la Alta Gerencia implemente procedimientos…», "
                   "bajo «A esos efectos, el Directorio:» (lingob::2.3::intro); condición de cierre de BKL-0034"}),
    ("Sujeto_alta_gerencia", {
        "bkl": "BKL-0034", "padre": "Sujeto_instancia_de_gobierno_societario",
        "anclas": (("lingob", "3.1", True, "Sujeto_entidad_financiera"),),
        "lectura": "lingob::3.1::intro: «La Alta Gerencia, como una buena práctica, será responsable de:», con los "
                   "ítems 3.1.1 a 3.1.7, todos de la Alta Gerencia"}),
    ("Sujeto_comite_de_auditoria", {
        "bkl": "BKL-0034", "padre": "Sujeto_instancia_de_gobierno_societario",
        "anclas": (("lingob", "4.1", False, None), ("lingob", "5.1.4", False, None)),
        "lectura": "lingob::4.1: «El Comité de auditoría deberá considerar la implementación de programas de "
                   "capacitación…»; lingob::5.1.4: «El Comité de auditoría deberá coordinar los esfuerzos de las "
                   "auditorías externa e interna…»"}),
])
RE_ARTICULO_INICIAL = re.compile(r"^(?:el|la|los|las|del|de la|de los|de las|al)\s+")


def mencion_normalizada(s) -> str:
    return RE_ARTICULO_INICIAL.sub("", norm(s))


def t_id_nuevo(id_: str):
    d = DEF_IDS_NUEVOS[id_]

    def fn(ctx: Contexto) -> dict:
        """Entrada del id nuevo (punto 4.d): (a) el id está en el catálogo; (b) la condición de cierre de su entrada
        del backlog sobre el catálogo y el esqueleto; (c) toda arista de sujeto cuya mención es el label o un alias
        del id (sin artículo) llega al id; (d) en cada ancla de la lectura, alguna norma (Obligacion, Restriccion o
        Potestad) anclada tiene aplica_a hacia el id, y ninguna hacia el id excluido. Si el grafo no tiene nodos del
        TO de ninguna de sus anclas, no_aplicable."""
        if ctx.perfil != "r2":
            return res("no_aplicable", NOTA_PERFIL_EXISTENTE)
        G, cat = ctx.grafo, ctx.cat
        sub, val = OrderedDict(), OrderedDict([("bkl", d["bkl"]), ("lectura", d["lectura"])])
        sub["a_en_el_catalogo"] = id_ in cat.ids
        ent = cat.clases.get(id_) or cat.roles.get(id_) or {}
        nombres = {mencion_normalizada(x) for x in [ent.get("label")] + list(ent.get("alias") or []) if x}
        if "domestico" in d:
            alias_dom = [a for a in ((cat.clases.get(d["domestico"]) or {}).get("alias") or []) if "del exterior" in norm(a)]
            sub["b_domestico_sin_alias_del_exterior"] = not alias_dom
            val["b_alias_del_exterior_en_el_domestico"] = alias_dom
        if "rol" in d:
            miembro = any(e["relation"] == "miembro_de" and e["target"] == d["rol"] for e in G.salientes(id_))
            residuo = (cat.roles.get(d["rol"]) or {}).get("residuo_declarado") or {}
            sub["b_miembro_del_rol_en_el_grafo"] = miembro
            sub["b_residuo_sin_colectivo_operativo_sin_id"] = "colectivo_operativo_sin_id" not in residuo
        if "subclases" in d:
            hijos = sorted(e["source"] for e in G.entrantes(id_) if e["relation"] == "subclase_de")
            sub["b_subclases_en_el_esqueleto"] = all(h in hijos for h in d["subclases"])
            val["b_subclases"] = hijos
        if "padre" in d:
            sub["b_padre_en_el_esqueleto"] = any(e["relation"] == "subclase_de" and e["target"] == d["padre"]
                                                 for e in G.salientes(id_))
        preds = set(ctx.enums_r2.get("predicados_sujeto") or [])
        con_mencion = [e for e in G.E if e.get("relation") in preds and e.get("rol_fuente") != "esqueleto"
                       and mencion_normalizada(e.get("sujeto_mencion")) in nombres]
        otro = [e for e in con_mencion if e["target"] != id_]
        sub["c_menciones_al_id"] = not otro
        val["c_aristas_con_la_mencion"] = len(con_mencion)
        val["c_a_otro_id"] = [(e["source"][:60], e["relation"], e["target"], e.get("sujeto_mencion")) for e in otro[:8]]
        val["d_anclas"] = []
        cubiertas = [x for x in d["anclas"] if cubre_to(G, x[0])]
        if d["anclas"] and not cubiertas:
            return res("no_aplicable", f"{d['bkl']}: el grafo no tiene nodos del TO de las anclas de la lectura "
                       f"({sorted({x[0] for x in d['anclas']})}); la entrada se lee contra esos chunks", valores=val)
        for to_pref, punto, pref, excluido in cubiertas:
            normas = [n for n in G.buscar(None, to_pref, punto, prefijo_punto=pref) if n.get("type") in TIPOS_NORMA]
            hacia = [n for n in normas if G.arista(n["id"], "aplica_a", id_)]
            mal = [n for n in normas if excluido and G.arista(n["id"], "aplica_a", excluido)]
            ok = bool(hacia) and not mal
            sub[f"d_{to_pref}_{punto}"] = ok
            val["d_anclas"].append({"ancla": f"{to_pref}::{punto}" + (" y sub-puntos" if pref else ""),
                                    "normas": len(normas), "con_aplica_a_al_id": len(hacia),
                                    "con_aplica_a_al_excluido": len(mal), "excluido": excluido})
        estado = "resuelto" if all(sub.values()) else "persiste"
        return res(estado, f"{d['bkl']}: " + "; ".join(f"{k} {v}" for k, v in sub.items())
                   + f"; aristas con la mención {len(con_mencion)}"
                   + ("; sin anclas en la tanda 0 (" + d["lectura"] + ")" if not d["anclas"] else ""),
                   subchecks=sub, valores=val)
    fn.__name__ = "t_id_" + id_.removeprefix("Sujeto_")
    return fn


# =========================================================================== #
# Registro de los 46 ítems (id del inventario, forma, direccionamiento, evidencia)
# =========================================================================== #
def T(id_, fn, forma, direcc, evidencia, nota=""):
    return {"id": id_, "fn": fn, "forma": forma, "direccionamiento": direcc, "evidencia": evidencia, "nota": nota}


INV = "reports/revision_UB21_diag/inventario_B21_fase1.md"
SA = "reports/revision_UB21_diag/sonda_anclas_C1_C7_UB21"
ST = "reports/revision_UB21_diag/sonda_T1_T7_cuatro_grafos_UB21"
SR = "reports/revision_UB21_diag/sonda_ranks_buscar_nodos_UB21"

TESTS = [
    T("BKL-0017", t_bkl_0017, "F1 + F4 ×2 + F5 ×3 (limite 10)",
      "(TO_clasificacion, 1.1, Obligacion, «los clientes de la entidad (tanto residentes en el pais»)",
      f"data/backlog/retests/C1_retest_2026-07-31.md:33-44 (4/4; ranks 1/1/3 :42-44); {SA}.py:100-111; {INV}:99"),
    T("BKL-0006", t_bkl_0006, "F3 (montos de la tabla) + F4 (exceptua → restantes) + F5 ×2 informativo (limite 10 / 13)",
      "(TO_capitales, 1.2, cualquier tipo, «exigencia basica» + «bancos» / «restantes entidades»); Excepcion por (cap, 1.2, Excepcion, «cajas de credito cooperativas»)",
      f"data/backlog/retests/C2_retest_2026-07-31.md:51-63 ((1)-(4) PASS; (5) informativo :59-63); {SA}.py:114-134; {INV}:100",
      "los ids viejos/nuevos del retest (3) son ids de contenido: excluidos del estado por la decisión 1"),
    T("BKL-0023", t_bkl_0023, "F3 (properties.umbral)",
      "(TO_capitales, 1.2, Restriccion, «companias financieras que realicen, en forma directa, operaciones de comercio exterior»)",
      f"data/backlog/retests/C3_retest_2026-08-02.md:30-37 ((a)-(d) 4/4); {SA}.py:146-155; {INV}:101",
      "sin nodo o sin umbral → no_aplicable, nunca PASS vacuo (pieza e)"),
    T("BKL-0019", t_bkl_0019, "F4 ×8 (subclase_de si laudada / padre_sugerido si flaggeada) + F4 ausente (excluida, laudada)",
      "8 sujetos por label normalizado de cuarentena.json (o id de cuarentena C4_retest:35-42) → padre laudado (id de catálogo); ver_vecinos (e) reducido a arista presente",
      f"data/backlog/retests/C4_retest_2026-08-02.md:35-42 (tabla), :52-58 ((a)-(e) 5/5); {SA}.py:158-190; {INV}:102"),
    T("BKL-0004", t_bkl_0004, "F1 ×9 + F4 (8 regula + 9 establecida_en) + F5 ×8 (7 consultas + proxy RT-C5-4; limite 10)",
      "(TO_clasificacion, 6.5 / 6.5.1 / 6.5.2 / 6.5.2.1 / 6.5.2.2 / 6.5.2.3 / 6.5.3 / 6.5.4 / 6.5.5, cualquier tipo, frase del título)",
      f"data/backlog/retests/C5_retest_2026-08-02.md:56-66 (32/32), :68-74 (proxy RT-4); data/backlog/propuestas/E4_enumeracion_65.md:283-289 (ranks); {SA}.py:193-226; {INV}:103"),
    T("BKL-0003", t_bkl_0003, "F1 + F4 ×2 + F4 ausente (a Sujeto) + F5 ×11 (N1 + controles rol/pnfc; limite 10)",
      "(TO_proteccion, 1.1.2.5, Excepcion, «mutuales o cooperativas»); controles por id de catálogo Sujeto_rol_sujeto_obligado_proteccion / Sujeto_proveedor_no_financiero_de_credito",
      f"data/backlog/retests/C6_retest_2026-08-03.md:52-62 (38/38); data/backlog/propuestas/E3_salvedad_mutuales.md:288-298 (ranks); {SA}.py:229-254; {INV}:104"),
    T("BKL-0005", t_bkl_0005, "F3 (dos calificadores en descripcion) + F5 ×3 (limite 10)",
      "(TO_regimen_informativo, 7.1, Obligacion, «para el calculo del importe correspondiente al mes n»)",
      f"data/backlog/retests/C7_retest_2026-08-03.md:67-78 (27/27; ranks :78); {SA}.py:257-264; {INV}:105"),
    T("BKL-0007", t_bkl_0007, "= BKL-0017 (sin test propio)", "= BKL-0017",
      f"data/backlog/backlog.jsonl líneas 42 y 46 (cerrada por referencia); {INV}:106, §5.9 :269", NOTA_SIN_APLICACION),
    T("BKL-0026", t_bkl_0026, "ninguna (no convertible)", "—", f"{INV}:107; data/backlog/retests/C6_retest_2026-08-03.md:99-103", NOTA_SIN_APLICACION),
    T("BKL-0027", t_bkl_0027, "ninguna (no convertible)", "—", f"{INV}:108; data/backlog/retests/C6_retest_2026-08-03.md:104-108", NOTA_SIN_APLICACION),
    T("BKL-0028", t_bkl_0028, "F1 sobre el catálogo parametrizado (ids «del exterior» separados; sin alias del exterior en los domésticos) + F1 en el grafo",
      "ids de catálogo Sujeto_entidad_financiera / Sujeto_banco / Sujeto_entidad_cambiaria", f"{INV}:109 (backlog línea 73)", NOTA_SIN_APLICACION),
    T("BKL-0029", t_bkl_0029, "F4 (miembro_de del rol de convca → id nuevo del catálogo)",
      "id de catálogo Sujeto_rol_alcance_convca; cobertura de convca por provenance", f"{INV}:110 (backlog línea 74)",
      NOTA_SIN_APLICACION + "; no_aplicable en todo grafo que no cubra convca (pieza e)"),
    T("RT-C5-1", t_rt_c5_1, "F3 (valor: cinco categorías en N1)", "N1 de C5", f"data/backlog/propuestas/E4_enumeracion_65.md:227-230; C5_retest:66 (d); {INV}:111", "solo valor (decisión 5)"),
    T("RT-C5-2", t_rt_c5_2, "F3 (valor: tres situaciones en N3)", "N3 de C5", f"data/backlog/propuestas/E4_enumeracion_65.md:231-234; C5_retest:66 (d); {INV}:112", "solo valor (decisión 5)"),
    T("RT-C5-3", t_rt_c5_3, "F3 (valor: «antes de los 60 días … mora» en N5)", "N5 de C5", f"data/backlog/propuestas/E4_enumeracion_65.md:235-238; C5_retest:66 (d); {INV}:113", "solo valor (decisión 5)"),
    T("RT-C5-4", t_rt_c5_4, "F3 (valor: primera vez / primera cuota / única vez en N6)", "N6 de C5",
      f"data/backlog/propuestas/E4_enumeracion_65.md:239-242; C5_retest:66-74 (d, observación RT-4); {INV}:114", "solo valor (decisión 5); su consulta proxy se evalúa en BKL-0004"),
    T("RT-C5-5", t_rt_c5_5, "F2 (nodo con «riesgo medio» anclado en 7.2 exacto) + F3 (N1 sin niveles del 7.2)",
      "(TO_clasificacion, 7.2 exacto, cualquier tipo, «riesgo medio»); N1 de C5", f"data/backlog/propuestas/E4_enumeracion_65.md:243-247; C5_retest:66 (d); {SA}.py:219-226; {INV}:115, §5.7 :267"),
    T("RT-C6-1", t_rt_c6_1, "F3 (valor en N1)", "N1 de C6", f"data/backlog/propuestas/E3_salvedad_mutuales.md:151-156; C6_retest:62 (d); {INV}:116", "solo valor (decisión 5)"),
    T("RT-C6-2", t_rt_c6_2, "F3 (valor en N1; = RT-C6-1)", "N1 de C6", f"data/backlog/propuestas/E3_salvedad_mutuales.md:157-164; C6_retest:62 (d); {INV}:117", "solo valor (decisión 5)"),
    T("RT-C6-5", t_rt_c6_5, "F3 (cláusula «por las financiaciones que otorguen» en N1)", "N1 de C6",
      "docs/laudo_release_r2_pipeline.md §1.5 opción (c); data/backlog/propuestas/E3_salvedad_mutuales.md:151-156; "
      "mandato U-R2-CODIGO, R4.d", "test de persistencia; el remedio de raíz es de U-PROMPT-R2"),
    T("RT-C6-3", t_rt_c6_3, "F4 ×n (miembro_de entrantes = miembros del rol en el catálogo)", "id de catálogo Sujeto_rol_sujeto_obligado_proteccion",
      f"data/backlog/propuestas/E3_salvedad_mutuales.md:165-174; C6_retest:62 (RT-3); {SA}.py:246-252; {INV}:118", "solo valor/estructura (decisión 5)"),
    T("RT-C6-4", t_rt_c6_4, "F4 (emisoras --miembro_de--> rol) + F4 ausente (N1 ↔ Sujeto)", "ids de catálogo; N1 de C6",
      f"data/backlog/propuestas/E3_salvedad_mutuales.md:175-179; C6_retest:62 (RT-4); {SA}.py:241-253; {INV}:119"),
    T("RT-C7-1", t_rt_c7_1, "F3 (valor: ambos calificadores en el portador)", "portador de C7", f"data/backlog/retests/C7_retest_2026-08-03.md:78 (d); {INV}:120, §5.8 :268", "solo valor (decisión 5); su consulta se evalúa en BKL-0005"),
    T("RT-C7-2", t_rt_c7_2, "F3 (valor: calificador de la RPC)", "portador de C7", f"data/backlog/retests/C7_retest_2026-08-03.md:78 (d); {INV}:121", "solo valor (decisión 5); su consulta se evalúa en BKL-0005"),
    T("RT-C7-3", t_rt_c7_3, "F3 (valor: calificador de la franquicia)", "portador de C7", f"data/backlog/retests/C7_retest_2026-08-03.md:78 (d); {INV}:122", "solo valor (decisión 5); su consulta se evalúa en BKL-0005"),
    T("T1", t_t1, "F2 + F3", "(TO_exterior, 3.9 y 3.9.x, cualquier tipo, «200»)",
      f"data/experiment/reextraccion_v2/corpus_v2/ensamblar_corpus.py:237-249 (reescrito sobre el adaptador); salida_r1/tests_respuesta_conocida_r1.json:2-4; {ST}_salida.txt:52; {INV}:128"),
    T("T2", t_t2, "F1 (conteo) + F2 (conteo de puntos)", "(TO_exterior, cualquier punto, cualquier tipo, «125 %» o «125%»)",
      f"ensamblar_corpus.py:251-265 (reescrito sobre el adaptador); tests_respuesta_conocida_r1.json:20-22; {ST}_salida.txt:53; {INV}:129"),
    T("T3", t_t3, "F2 + F3", "(TO_proteccion, 1.1.2.5, cualquier tipo, «mutual» o «cooperativ»)",
      f"ensamblar_corpus.py:267-280 (reescrito sobre el adaptador); tests_respuesta_conocida_r1.json:75-77; {ST}_salida.txt:54; {INV}:130"),
    T("T4", t_t4, "F1 + F4 (R-T4: esqueleto igual al de build_skeleton sobre --catalogo; U-R2-CODIGO, R5.a)",
      "nodos y aristas de relaciones de esqueleto de assemble.build_skeleton sobre el catálogo, menos rol_fuente=cuarentena_laudada",
      f"data/experiment/reextraccion_v2/corpus_v2/r1_tests.py:30-42; tests_respuesta_conocida_r1.json:92-96; {ST}_salida.txt:27,55; {INV}:131, §5.1 :261"),
    T("T5", t_t5, "F4 + F3 (R-T5: remisión por contenido, en las dos formas; U-R2-CODIGO, R5.a)",
      "(ancla origen, ancla y destino, tipo del destino, números de punto de la evidencia) de salida_r1/referencias_muestra30_inspeccionada_A2.json (sha256 4dbc2d30…)",
      f"r1_tests.py:44-54; tests_respuesta_conocida_r1.json:99-101; {ST}_salida.txt:56; {INV}:132"),
    T("T6", t_t6, "F1", "TextoOrdenado_<e2_lib.slugify_full(archivo de E0 por TO)>",
      f"r1_tests.py:56-61; tests_respuesta_conocida_r1.json:104-105; {ST}_salida.txt:57; {INV}:133"),
    T("T7", t_t7, "F3 + F4 + F4 ausente (política de cuarentena, decisión 3)", "Sujetos con nivel=propuesto; catálogo parametrizado",
      f"r1_tests.py:63-82; tests_respuesta_conocida_r1.json:115-118; {ST}_salida.txt:30,58; {INV}:134, §5.2 :262"),
    T("I1", t_i1, "ninguna (no convertible)", "—", f"data/experiment/reextraccion_v2/corpus_v2/r1_invariantes.py:7,62-68; {INV}:135"),
    T("I2", t_i2, "ninguna (no convertible)", "—", f"r1_invariantes.py:8,69-70; {INV}:136"),
    T("I3", t_i3, "F1 (conteo: unicidad de ids y de triplas)", "JSON crudo", f"r1_invariantes.py:9,72-77; {ST}_salida.txt:60; {INV}:137"),
    T("I4", t_i4, "F4 (cero colgantes)", "JSON crudo", f"r1_invariantes.py:10,79-81; {ST}_salida.txt:61; {INV}:138"),
    T("I5", t_i5, "F2 (al menos una provenance por nodo y arista, adaptador)", "JSON crudo", f"r1_invariantes.py:11-12,83-90; {ST}_salida.txt:62; {INV}:139"),
    T("E4-a1", t_e4_a1, "F1 ausente (ningún propuesto residual resoluble por label_exacto)", "Sujetos propuestos; r1_e4.indice_catalogo / resolver_label sobre el catálogo parametrizado",
      f"data/experiment/reextraccion_v2/corpus_v2/r1_e4.py:10,89,101; {INV}:167, §4 :234-250"),
    T("E4-a2", t_e4_a2, "F1 ausente (alias_exacto)", "ídem", f"r1_e4.py:11,92-93,102; {INV}:168, §4"),
    T("E4-a3", t_e4_a3, "F1 ausente (id_slug; e2_lib.slugify_full importado)", "ídem", f"r1_e4.py:12,90,103; data/experiment/reextraccion_v2/e2_reduce/e2_lib.py:90; {INV}:169, §4"),
    T("E4-a4", t_e4_a4, "F1 ausente (label_singularizado)", "ídem", f"r1_e4.py:13-14,53-58,91,104; {INV}:170, §4"),
    T("E4-a5", t_e4_a5, "F1 ausente (alias_en_parentesis) + F3 (padre_sugerido)", "ídem", f"r1_e4.py:15-17,108-112; {INV}:171, §4"),
    T("E4-a6", t_e4_a6, "F1 ausente (claves ambiguas / alias_resueltos que re-resuelven sin ambigüedad)", "ídem + Sujetos con properties.alias_resueltos", f"r1_e4.py:7-9,79-84,113-117; {INV}:172, §4"),
    T("E4-a7", t_e4_a7, "F3 (cuarentena=true normalizada) + F1 (todo Sujeto no propuesto ∈ catálogo)", "Sujetos; catálogo parametrizado", f"r1_e4.py:18-19,141-147; {INV}:173"),
    T("E4-a8", t_e4_a8, "F3 (alias_resueltos en ids de catálogo) + F1 ausente + F4 ausente; parte pre-E4 no_aplicable",
      "ids de catálogo de la tabla e4_propuestos.json junto al kg.json bajo prueba (R-E4a8; estado resuelto)", f"r1_e4.py:20-24,152-171,178-202; salida_r1/e4_propuestos.json; {INV}:174, §4 :248"),
    T("E4-b", t_e4_b, "F1 (= T6) + F3 (properties.archivo ∈ archivos de E0)", "TextoOrdenado", f"r1_e4.py:26-30,208-250; salida_r1/e4_texto_ordenado.json; {INV}:175, §4"),
    T("E4-c", t_e4_c, "ninguna directa (no observable sobre un kg.json)", "—", f"r1_e4.py:32-36,256-291; salida_r1/e4_conflictos.json; {INV}:176"),
    T("EJ-cla-5.1.1.1", t_ej_cla_5111, "F4 ×2 (vínculos normativos a la Operacion) + F4 (remisión a cla::3.7) + F3 informativo (umbral)",
      "(TO_clasificacion, 5.1.1.1, tipos de contenido); destino cla::3.7",
      "laudo de r2, §4, :334; tablero, fila del test del ejemplo; mandato U-R2-CODIGO, R5.a; enmienda 1, R5.b",
      "esperado: KG-Reextraído-r1 resuelto, KG-Tanda0-Desarrollo-r1 persiste, r2a resuelto (con (i) no verificado por E3), r2b resuelto"),
    T("LN-1", t_ln_1, "F3 (valores de lista cerrada o marca fuera_de_lista; nodo y elemento de umbral)", "todos los nodos; listas de enums_r2.json",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g; L-ESQ-R2 §1.5 y §2.5"),
    T("LN-2", t_ln_2, "F3 (claves cerradas por tipo)", "nodos de los nueve tipos; claves_por_tipo de enums_r2.json + modelos_r2.MARCAS_NODO",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g; L-ESQ-R2 §2.5"),
    T("LN-3", t_ln_3, "F3 (mención y mencion_verificada en aristas de sujeto)", "aristas aplica_a / ejecuta fuera del esqueleto",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g; L-ESQ-R2 §3.5", "persiste en r2a hasta la mención de E1 de r2b (P-b1)"),
    T("LN-4", t_ln_4, "F3 (metodo_resolucion) + conteo de desacuerdos", "aristas aplica_a / ejecuta fuera del esqueleto; resolucion_sujetos.jsonl",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g; L-ESQ-R2 §3.5"),
    T("LN-5", t_ln_5, "F1 (registro ↔ grafo)", "Sujetos propuestos; no_mapeados_sujetos.jsonl (id_nodo, estado)",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g y §d; L-ESQ-R2 §4.5"),
    T("LN-6", t_ln_6, "F1 (re-resolución idempotente, byte a byte)", "no_mapeados_sujetos.jsonl; r1_e4.reresolver_registro importado",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g y §d (P-d3); L-ESQ-R2 §4.5"),
    T("LN-7", t_ln_7, "F3 (categoría del enum y tramo de cada omisión)", "registro de omisiones del ensamblado",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g; L-ESQ-R2 §5.5", "no_aplicable en r2a: las omisiones con categoría y tramo son de r2b"),
    T("LN-8", t_ln_8, "F1 (bloque del prompt = JSON único)", "generados_r2/bloque_catalogo_r2.txt; catalogo_sujetos_r2.json",
      "reports/u_listas_nomap/diseno_listas_nomap.md §g; L-ESQ-R2 §7.5"),
    # U-REEXT-T0, T1, punto 4 (mandato firmado en e2027dd)
    T("BKL-0001", t_bkl_0001, "F1 (nodo anclado en el punto con el contenido)",
      "(TO_capitales, 2.8.3.3, cualquier tipo, «75» + «salario minimo»)",
      f"{EXPEDIENTE}:28-41 (E1); docs/mandatos/UREEXT_T0_reextraccion_tanda0.md:152-154 (e2027dd)",
      "test por punto, como T1 de BKL-0024; no_aplicable sin nodos de Capitales Mínimos"),
    T("BKL-0002", t_bkl_0002, "F1 (nodo anclado en el punto o un sub-punto con el contenido)",
      "(TO_exterior, 3.5.3 y sub-puntos, cualquier tipo, «dias habiles» + «3»/«tres» + «vencimiento» + «capital»/«interes»)",
      f"{EXPEDIENTE}:43-55 (E2); docs/mandatos/UREEXT_T0_reextraccion_tanda0.md:152-154 (e2027dd)",
      "test por punto, como T1 de BKL-0024; no_aplicable sin nodos de Exterior y Cambios"),
    T("FIRMAS-condicion_de", t_firmas_condicion_de,
      "F3 (firmas en la matriz de enums_r2.json) + conteo de no_verificada_e3 = 0 + F4 informativo (aristas por firma)",
      "firmas_r2 y ampliacion_r2 de pyd_r2/generados/enums_r2.json; aristas condicion_de desde Condicion; no_verificada_e3",
      "data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md:784-822 (§6.3 a §6.5, 4ef7650)"),
    T("SIN-VERIF-E3", t_sin_verif_e3,
      "conteos del grafo (aristas de E1 con no_verificada_e3, nodos sin procedencia de unidad) + del reporte del ensamblado r2b (paso_por_e3, aristas_no_verificadas_e3)",
      "aristas con predicado de E1 no derivadas; nodos de los nueve tipos salvo TextoOrdenado; reporte_ensamblado_r2.json",
      "data/experiment/prompt_r2/freno_p3.md:82-111 (A3, seis puntos; 4aa92c7); data/experiment/r2_codigo2/freno_c2.md (punto s; 9f6361e)",
      "la cola humana es la excepción explícita y se cuenta aparte (A5); no_aplicable en r2a"),
] + [T(i, t_id_nuevo(s), "F1 (id en el catálogo) + condición de cierre sobre catálogo y esqueleto + F4 (menciones y anclas)",
       f"{s}: menciones por label y alias; anclas de la lectura en DEF_IDS_NUEVOS",
       "data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md:887-925 (§7.3 a §7.5, 4ef7650); data/backlog/backlog.jsonl "
       f"(condicion_de_cierre de {DEF_IDS_NUEVOS[s]['bkl']})", DEF_IDS_NUEVOS[s]["lectura"])
     for i, s in zip(ITEMS_ID, IDS_NUEVOS_R2)]


def convertibilidad(id_: str) -> str:
    if id_ in ITEMS_UREEXT:
        return "U-REEXT-T0"
    if id_ in CONVERTIBLES:
        return "convertible"
    if id_ in CON_CONDICION:
        return "con condición"
    if id_ in NO_CONVERTIBLES:
        return "no convertible"
    if id_ in ITEMS_R2:
        return "perfil r2"
    raise KeyError(id_)


def grupo(id_: str) -> str:
    if id_ in ITEMS_PUNTO:
        return "ii"
    if id_ in ITEMS_R2 and not id_.startswith("RT"):
        return "r2"
    return "i-BKL" if id_.startswith("BKL") else "i-RT" if id_.startswith("RT") else "ii" if id_[0] in "TI" else "iii"


def verificar_particion() -> dict:
    """46 ítems, ids únicos, partición 19 / 23 / 4 y 15 dependientes del retriever, tal como la tabla resumen §1;
    los ítems del perfil r2 (ITEMS_R2) se registran aparte."""
    todos = [t["id"] for t in TESTS]
    assert len(set(todos)) == len(todos) and set(ITEMS_R2) <= set(todos), todos
    ids = [i for i in todos if i not in ITEMS_R2]
    assert len(ids) == 46 and len(set(ids)) == 46, len(ids)
    assert set(ids) == set(CONVERTIBLES) | set(CON_CONDICION) | set(NO_CONVERTIBLES)
    assert (len(CONVERTIBLES), len(CON_CONDICION), len(NO_CONVERTIBLES)) == (19, 23, 4)
    assert len(RETRIEVER) == 15 and set(RETRIEVER) <= set(ids)
    c = Counter(grupo(i) for i in ids)
    assert c == {"i-BKL": 12, "i-RT": 12, "ii": 12, "iii": 10}, c
    return {"items": 46, "convertibles": 19, "con_condicion": 23, "no_convertibles": 4, "retriever": 15, "por_grupo": dict(c),
            "items_r2": list(ITEMS_R2)}


# =========================================================================== #
# Ejecución, salida y regresión                                                #
# =========================================================================== #
def ejecutar(ctx: Contexto, solo=None) -> list:
    out = []
    for t in TESTS:
        if solo and t["id"] not in solo:
            continue
        r = t["fn"](ctx)
        item = OrderedDict()
        item["id"] = t["id"]
        item["grupo"] = grupo(t["id"])
        item["convertibilidad"] = convertibilidad(t["id"])
        item["retriever"] = "sí" if t["id"] in RETRIEVER else "no"
        item["forma"] = t["forma"]
        item["direccionamiento"] = t["direccionamiento"]
        item["evidencia"] = t["evidencia"]
        if t["nota"]:
            item["nota"] = t["nota"]
        item["estado"] = r["estado"]
        item["detalle"] = r["detalle"]
        for k in ("subchecks", "valores", "ranks"):
            if r.get(k) is not None:
                item[k] = r[k]
        out.append(item)
    return out


def resumen_ranks(items: list) -> dict:
    filas = [f for it in items for f in it.get("ranks") or []]
    objs = [o for f in filas for o in f["objetivos"]]
    return {"consultas": len(filas), "consultas_coinciden_sellado": sum(1 for f in filas if all(o["coincide_sellado"] for o in f["objetivos"])),
            "objetivos": len(objs), "objetivos_coinciden_sellado": sum(1 for o in objs if o["coincide_sellado"]),
            "objetivos_en_ventana": sum(1 for o in objs if o["en_ventana"]),
            "objetivos_ausentes": sum(1 for o in objs if not o["objetivo_presente"])}


def seleccionar_esperado(fixture: dict, kg_sha: str):
    """Entrada de la fixture cuyo kg_sha256 coincide: ('estado_esperado' | 'linea_de_base_observada', nombre, entrada) o None."""
    for parte in ("estado_esperado", "linea_de_base_observada"):
        for nombre, ent in (fixture.get(parte) or {}).items():
            if isinstance(ent, dict) and ent.get("kg_sha256") == kg_sha:
                return parte, nombre, ent
    return None


def computar_regresion(items: list, esperado: dict, ranks: dict | None = None) -> dict:
    """Regresión = estado medido ≠ estado esperado (6bis). esperado null =
    NO VERIFICADA: no computa. Ítems medidos sin entrada esperada y
    viceversa se listan. `ranks_sellados` esperado (consultas/objetivos que
    coinciden) se compara como pseudo-ítem RANKS_SELLADOS."""
    esp_items = esperado.get("items") or {}
    medido = {it["id"]: it["estado"] for it in items}
    regresiones, no_verificadas, coinciden = [], [], []
    for id_, m in medido.items():
        e = esp_items.get(id_)
        if e is None:
            continue
        est = e.get("estado") if isinstance(e, dict) else e
        if est is None:
            no_verificadas.append(id_)
        elif est != m:
            regresiones.append({"item": id_, "esperado": est, "medido": m, "evidencia_del_esperado": (e.get("evidencia") if isinstance(e, dict) else None)})
        else:
            coinciden.append(id_)
    sin_esperado = sorted(set(medido) - set(esp_items))
    sin_medido = sorted(set(esp_items) - set(medido))
    rk_esp = esperado.get("ranks_sellados")
    if rk_esp and ranks is not None:
        m = {"consultas": ranks["consultas_coinciden_sellado"], "objetivos": ranks["objetivos_coinciden_sellado"]}
        e = {"consultas": rk_esp.get("consultas"), "objetivos": rk_esp.get("objetivos")}
        if m != e:
            regresiones.append({"item": "RANKS_SELLADOS", "esperado": e, "medido": m, "evidencia_del_esperado": rk_esp.get("evidencia")})
        else:
            coinciden.append("RANKS_SELLADOS")
    return {"n_regresiones": len(regresiones), "regresiones": regresiones, "coinciden": len(coinciden),
            "no_verificadas": no_verificadas, "sin_esperado": sin_esperado, "sin_medido": sin_medido}


def codigo_salida(regresion: dict | None) -> int:
    return 1 if regresion and regresion.get("n_regresiones") else 0


def _fila_md(it: dict) -> str:
    det = it["detalle"].replace("|", "\\|").replace("\n", " ")
    if len(det) > 220:
        det = det[:217] + "…"
    return f"| {it['id']} | {it['grupo']} | {it['convertibilidad']} | {it['retriever']} | {it['forma'].replace('|', '/')} | **{it['estado']}** | {det} |"


def render_md(salida: dict) -> str:
    p = salida["parametros"]
    L = ["# Regression suite — " + p["kg"], ""]
    L.append(f"- kg: `{p['kg']}` sha256 `{p['kg_sha256']}` — {p['n_nodes']} nodos / {p['n_edges']} aristas; generación declarada {p['generacion']} (formato detectado: {p['generacion_detectada']})")
    L.append(f"- catálogo: `{p['catalogo']}` (versión {p['catalogo_version']}, sha256 `{p['catalogo_sha256']}`); política de cuarentena: **{p['politica_cuarentena']}**")
    L.append(f"- esqueleto de referencia (T4): `{p['esqueleto_referencia']}`" + (f" sha256 `{p['esqueleto_referencia_sha256']}`" if p.get("esqueleto_referencia_sha256") else " (no cargado)"))
    L.append(f"- retriever: GraphIndex de data/experiment/evaluacion/harness.py (importado; sha256 `{p['harness_sha256']}`), loader.load_graph_from_path adapter_key=None")
    L.append(f"- partición declarada: {p['particion']}")
    L.append("")
    r = salida["resumen"]
    L.append(f"## Resumen: {r['items']} ítems — resuelto {r['resuelto']} / persiste {r['persiste']} / no_aplicable {r['no_aplicable']}")
    rk = salida["ranks_sellados"]
    L.append(f"Ranks sellados (retriever in-memory): consultas que coinciden con el sellado {rk['consultas_coinciden_sellado']}/{rk['consultas']}; "
             f"objetivos {rk['objetivos_coinciden_sellado']}/{rk['objetivos']}; objetivos en ventana declarada {rk['objetivos_en_ventana']}; objetivos ausentes {rk['objetivos_ausentes']}.")
    L.append("")
    L.append("| Id | Grupo | Convertibilidad | Retr. | Forma | Estado | Detalle |")
    L.append("|---|---|---|---|---|---|---|")
    for it in salida["items"]:
        L.append(_fila_md(it))
    L.append("")
    reg = salida.get("regresion")
    L.append("## Regresión contra la fixture")
    if reg is None:
        L.append(salida.get("regresion_nota") or "Sin `--esperado`: no se computa regresión.")
    else:
        L.append(f"Fixture `{reg['fixture']}` (sha256 `{reg['fixture_sha256']}`; subárbol estado_esperado sha256 `{reg['estado_esperado_sha256']}`), entrada **{reg['entrada']}** ({reg['parte']}).")
        if reg.get("nota"):
            L.append(reg["nota"])
        if "n_regresiones" in reg:
            L.append(f"- regresiones: **{reg['n_regresiones']}**; coinciden: {reg['coinciden']}; NO VERIFICADAS (esperado null): {reg['no_verificadas']}; sin esperado: {reg['sin_esperado']}; sin medido: {reg['sin_medido']}")
            for x in reg["regresiones"]:
                L.append(f"  - REGRESIÓN {x['item']}: esperado {x['esperado']} / medido {x['medido']} — evidencia del esperado: {x['evidencia_del_esperado']}")
    L.append("")
    cen = salida.get("censos")
    if cen:
        L.append("## Censos informativos (fuera de los ítems y de la fixture)")
        ig = cen["igual_descripcion"]
        L.append(f"- aristas entre dos nodos con la misma descripción: {ig['aristas']} {ig['por_firma']} (sin regla de retiro)")
        ct = cen["igual_descripcion_control_lectura_matriz"]
        L.append(f"- control sobre la lectura de la matriz ({ct['relaciones']} relaciones): marca {ct['marcadas']}; correctas en la lectura entre las marcadas: "
                 f"{ct['correctas_en_la_lectura_entre_las_marcadas']}")
        rm = cen["remisiones"]
        L.append(f"- remisiones: {rm['aristas']} aristas {rm['por_forma']}; por alcance {rm['aristas_por_alcance']}; citas {rm['citas']} "
                 f"{rm['citas_por_alcance']}; firmas fuera de la de remite_a {rm['firmas_fuera_de_remite_a']}")
        L.append(f"  - por firma: {rm['aristas_por_firma']}")
        L.append("")
    L.append("## Consultas de rank (por ítem)")
    for it in salida["items"]:
        for f in it.get("ranks") or []:
            partes = [f"{o['objetivo']}: rank={o['rank']} sellado={o['rank_esperado_sellado']} limite={o['limite']} "
                      f"{'=' if o['coincide_sellado'] else '≠'}{'' if o['objetivo_presente'] else ' [objetivo AUSENTE]'}" for o in f["objetivos"]]
            L.append(f"- [{it['id']}] «{f['consulta']}» (limite pedido {f['limite_pedido']}): " + " | ".join(partes))
    L.append("")
    return "\n".join(L)


def correr(args) -> tuple:
    """Devuelve (salida dict, código de salida)."""
    kg_path = Path(args.kg)
    G = Grafo.desde_ruta(kg_path)
    cat = Catalogo.desde_ruta(args.catalogo)
    if G.generacion_detectada and G.generacion_detectada != args.generacion:
        raise SystemExit(f"--generacion {args.generacion} no coincide con el formato de provenance detectado (gen {G.generacion_detectada}) en {kg_path}")
    generados_resolucion = getattr(args, "generados_resolucion", None)
    ctx = Contexto(G, cat, args.generacion, args.politica_cuarentena, esqueleto_ref_ruta=args.esqueleto_referencia,
                   perfil=args.perfil, registro_dir=args.registro_dir, manifiesto=args.manifiesto,
                   generados_resolucion=generados_resolucion)
    solo = set(args.solo.split(",")) if args.solo else None
    items = ejecutar(ctx, solo)
    resumen = Counter(it["estado"] for it in items)
    salida = OrderedDict()
    salida["suite"] = "scripts/regression_kg.py (U-B2.1 fase 2)"
    salida["parametros"] = OrderedDict([
        ("kg", str(kg_path)), ("kg_sha256", G.sha256), ("n_nodes", len(G.N)), ("n_edges", len(G.E)),
        ("generacion", args.generacion), ("generacion_detectada", G.generacion_detectada),
        ("catalogo", str(args.catalogo)), ("catalogo_version", cat.version), ("catalogo_sha256", cat.sha256),
        ("politica_cuarentena", args.politica_cuarentena),
        ("esqueleto_referencia", str(args.esqueleto_referencia or DEFAULT_ESQUELETO_REF)),
        ("esqueleto_referencia_sha256", ctx._esqueleto_ref.sha256 if ctx._esqueleto_ref is not None else None),
        ("harness_sha256", sha256_path(EVALUACION / "harness.py")), ("loader_sha256", sha256_path(EVALUACION / "loader.py")),
        ("particion", verificar_particion()), ("solo", sorted(solo) if solo else None),
        ("perfil", args.perfil), ("registro_dir", str(ctx.registro_dir) if ctx.registro_dir else None),
        ("tos_bajo_prueba", ctx._tos_bajo_prueba[0] if ctx._tos_bajo_prueba is not None else None),
    ])
    if generados_resolucion:
        # W3: solo con la opción, para que sin ella la salida sea byte a byte la de siempre
        salida["parametros"]["generados_resolucion"] = str(generados_resolucion)
    salida["resumen"] = {"items": len(items), "resuelto": resumen.get("resuelto", 0), "persiste": resumen.get("persiste", 0), "no_aplicable": resumen.get("no_aplicable", 0)}
    salida["ranks_sellados"] = resumen_ranks(items)
    salida["items"] = items
    if not args.sin_censos:
        salida["censos"] = OrderedDict([
            ("igual_descripcion", censo_igual_descripcion(G)),
            ("igual_descripcion_control_lectura_matriz", control_igual_descripcion_lectura()),
            ("remisiones", censo_remisiones(G)),
        ])
    codigo = 0
    if args.esperado:
        fx_path = Path(args.esperado)
        fixture = json.loads(fx_path.read_text(encoding="utf-8"))
        reg = OrderedDict([("fixture", str(fx_path)), ("fixture_sha256", sha256_path(fx_path)),
                           ("estado_esperado_sha256", sha256_canonico(fixture.get("estado_esperado") or {}))])
        sel = seleccionar_esperado(fixture, G.sha256)
        if sel is None:
            reg["parte"], reg["entrada"] = None, None
            reg["nota"] = f"la fixture no tiene entrada con kg_sha256 {G.sha256}: no se computa regresión"
        else:
            parte, nombre, ent = sel
            reg["parte"], reg["entrada"] = parte, nombre
            difieren = [k for k, v in (("generacion", args.generacion), ("politica_cuarentena", args.politica_cuarentena), ("catalogo_sha256", cat.sha256))
                        if ent.get(k) is not None and ent.get(k) != v]
            if parte != "estado_esperado":
                reg["nota"] = "entrada de LÍNEA DE BASE OBSERVADA: no participa del cómputo de regresión en esta fase (pieza f.2)"
            elif difieren:
                reg["nota"] = f"parámetros de la corrida distintos de los de la fixture ({difieren}): no se computa regresión"
                codigo = 2
            else:
                reg.update(computar_regresion(items, ent, salida["ranks_sellados"]))
                codigo = codigo_salida(reg)
        salida["regresion"] = reg
    else:
        salida["regresion"] = None
    if args.out:
        out_md = Path(args.out)
        out_json = out_md.with_suffix(".json")
        out_md.write_text(render_md(salida), encoding="utf-8")
        out_json.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return salida, codigo


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Regression suite del grafo (U-B2.1 fase 2).")
    ap.add_argument("--kg", required=True, help="ruta al kg.json (solo lectura)")
    ap.add_argument("--generacion", type=int, choices=(2, 3), required=True, help="2 = {source_doc, location}; 3 = {archivo, punto}")
    ap.add_argument("--catalogo", required=True, help="esquema_v2_clases.json o esquema_v3_clases.json (leído del artefacto)")
    ap.add_argument("--politica-cuarentena", choices=POLITICAS, required=True, dest="politica_cuarentena")
    ap.add_argument("--esperado", default=None, help="fixture scripts/regression_kg_esperado.json; sin ella no se computa regresión")
    ap.add_argument("--esqueleto-referencia", default=None, dest="esqueleto_referencia", help=f"grafo de referencia de T4 (default {DEFAULT_ESQUELETO_REF.relative_to(RAIZ)})")
    ap.add_argument("--out", default=None, help="RUTA.md (escribe también RUTA.json); sin --out no escribe nada")
    ap.add_argument("--solo", default=None, help="ids separados por coma (subconjunto; selftest/depuración)")
    ap.add_argument("--perfil", choices=PERFILES, default="existente",
                    help="existente (default: grafos sellados) o r2 (U-R2-CODIGO: remite_a, listas y registros del perfil r2)")
    ap.add_argument("--registro-dir", default=None, dest="registro_dir",
                    help="directorio con no_mapeados_sujetos.jsonl y resolucion_sujetos.jsonl (default: el del kg.json)")
    ap.add_argument("--sin-censos", action="store_true", dest="sin_censos", help="no computa los censos informativos")
    ap.add_argument("--generados-resolucion", default=None, dest="generados_resolucion",
                    help="R2 de U-RERESOL-CAT, W3: directorio con los generados del catálogo de resolución que leyó el "
                         "ensamblado; LN-6 los lee con su candado (r1_e4.catalogo_resolucion_r2). Sin la opción, LN-6 "
                         "lee generados_r2/ y la salida es la de siempre")
    ap.add_argument("--manifiesto", default=None,
                    help="manifiesto del grafo bajo prueba (U-REEXT-T0, T1, punto 4.a: TOs de T6 y E4-b); default: el "
                         "manifiesto.path del reporte del ensamblado junto al kg.json, o los cinco TOs de desarrollo")
    return ap


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    salida, codigo = correr(args)
    p, r, rk = salida["parametros"], salida["resumen"], salida["ranks_sellados"]
    print(f"regression_kg — {p['kg']} sha256 {p['kg_sha256']} gen {p['generacion']} catálogo v{p['catalogo_version']} política {p['politica_cuarentena']}")
    print(f"  ítems {r['items']}: resuelto {r['resuelto']} / persiste {r['persiste']} / no_aplicable {r['no_aplicable']}")
    print(f"  ranks sellados: consultas {rk['consultas_coinciden_sellado']}/{rk['consultas']}, objetivos {rk['objetivos_coinciden_sellado']}/{rk['objetivos']}")
    for it in salida["items"]:
        print(f"  {it['id']:9s} {it['estado']:13s} {it['detalle'][:150]}")
    reg = salida.get("regresion")
    if reg is not None:
        print(f"  fixture {reg['fixture']} sha256 {reg['fixture_sha256']} | estado_esperado sha256 {reg['estado_esperado_sha256']} | entrada {reg['entrada']} ({reg['parte']})")
        if reg.get("nota"):
            print("  " + reg["nota"])
        if "n_regresiones" in reg:
            print(f"  regresiones: {reg['n_regresiones']} (coinciden {reg['coinciden']}; NO VERIFICADAS {reg['no_verificadas']}; sin esperado {reg['sin_esperado']}; sin medido {reg['sin_medido']})")
            for x in reg["regresiones"]:
                print(f"    REGRESIÓN {x['item']}: esperado {x['esperado']} / medido {x['medido']}")
    if args.out:
        print(f"  escrito: {args.out} y {Path(args.out).with_suffix('.json')}")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
