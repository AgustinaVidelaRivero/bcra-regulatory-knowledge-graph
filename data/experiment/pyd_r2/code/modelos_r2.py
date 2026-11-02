"""
modelos_r2.py — U-PYD (plan, fila B2.11, unidad 7): módulo único de modelos
Pydantic del perfil r2.

Fuente del esquema: enmienda L-ESQ-R2, versión firmada (`git show
4ef7650:data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`), §0.2 con los
cambios de §1, §2, §3, §5 y §6. Catálogo de sujetos: el r2 de U-CAT-UNICO
(`bd2122d`), que se lee con candado de sha256 y no se edita.

Contenido:
  - listas cerradas (tipos, predicados, matriz de firmas congelada y r2,
    valores de propiedad, umbral, frecuencia, omisiones, marcas);
  - salida de E1 del perfil r2 (lo que emite el modelo en r2b): una entidad
    por tipo, relación con `sujeto_mencion` y `sujeto_id` como sugerencia,
    omisión con categoría, tramo y nota. De estos modelos se genera el tool
    schema (`tool_schema_e1_r2`);
  - elemento validado (salida del validador r2) y nodo y arista del grafo, con
    las marcas: `fuera_de_lista`, `properties_no_definidas`,
    `mencion_verificada`, `comparacion_asumida` (en el elemento de umbral),
    `no_verificada_e3` y `coherencia_tipo_predicado`;
  - predicados derivados por código en el ensamblado (`remite_a`, enmienda 2
    de L-ESQ-R2, 5f9a731): firma, lista de `alcance` y controles de la arista.
    No entran al tool schema ni a las listas de E1 (agregado de U-R2-CODIGO,
    enmienda 1 a su mandato);
  - lo que agrega el ensamblado del perfil r2, en el grafo (decisión 3 sobre
    el FRENO R3 de U-R2-CODIGO): las marcas de cola humana y de colisión
    cross-TO en el nodo, la resolución de la base y la verificación en tabla
    en el elemento de umbral, el calificador en la arista de sujeto y las
    relaciones del esqueleto (Sujeto → Sujeto). Tampoco entran al tool schema;
  - lectura de la forma r2 (U-PROMPT-R2, P3): el tramo de evidencia y su
    verificación en la procedencia (decisiones 15 y 16), las otras_propiedades
    de la relación y source y destino de la omisión (decisión 17), la marca
    `no_verificada_e3` por lo que pasó por E3 y la `establecida_en` derivada
    de la procedencia (nota del 04/10/2026 al mandato).

Los modelos validados no rechazan un valor fuera de lista: exigen que esté en
la lista o que lleve la marca `fuera_de_lista` (LN-1 de la suite propuesta).
Las claves por tipo son cerradas: lo que no está en la definición vive en
`properties_no_definidas` (LN-2).

Nada de este módulo llama a una API ni escribe archivos.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

AQUI = Path(__file__).resolve().parent          # pyd_r2/code
PYD_R2 = AQUI.parent                            # pyd_r2
REPO = AQUI.parents[3]                          # raíz del repo

# ------------------------------------------------------------------------- #
# Catálogo de sujetos r2 (U-CAT-UNICO, bd2122d): candado de sha256           #
# ------------------------------------------------------------------------- #
CATALOGO_R2 = REPO / "data" / "experiment" / "catalogo_unico" / "catalogo_sujetos_r2.json"
ENUMS_CATALOGO_R2 = (REPO / "data" / "experiment" / "catalogo_unico" / "generados_r2"
                     / "enums_tool_schema_r2.json")
CATALOGO_R2_SHA256 = "c3ad15811c7ea5fa2d0f6cbd56dc775c38dcffd0ae8874c22f5f45c1e82d3a83"
ENUMS_CATALOGO_R2_SHA256 = "bdc8c4371946e0148d192e99cda773c80b5cfa766dafec477112f0f35a33707c"
CATALOGO_R2_COMMIT = "bd2122d"


def sha256_archivo(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _cargar_sujetos_r2() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Ids vigentes del catálogo r2 (enum de `sujeto_id`) y lápidas. Frena si
    algún archivo no reproduce el sha256 de bd2122d."""
    for p, esperado in ((CATALOGO_R2, CATALOGO_R2_SHA256),
                        (ENUMS_CATALOGO_R2, ENUMS_CATALOGO_R2_SHA256)):
        s = sha256_archivo(p)
        if s != esperado:
            raise RuntimeError(f"candado del catálogo r2: {p.name} da {s[:12]}… "
                               f"(esperado {esperado[:12]}…, {CATALOGO_R2_COMMIT}) — se frena")
    enums = json.loads(ENUMS_CATALOGO_R2.read_text(encoding="utf-8"))
    cat = json.loads(CATALOGO_R2.read_text(encoding="utf-8"))
    vigentes = tuple(s["id"] for s in cat["sujetos"] if s["estado"]["valor"] == "vigente")
    lapidas = tuple(s["id"] for s in cat["sujetos"] if s["estado"]["valor"] != "vigente")
    if tuple(enums["sujeto_id"]) != vigentes:
        raise RuntimeError("enum de sujeto_id del catálogo r2 distinto de sus vigentes — se frena")
    return vigentes, lapidas


SUJETOS_R2, SUJETOS_R2_LAPIDAS = _cargar_sujetos_r2()
SUJETOS_R2_SET = frozenset(SUJETOS_R2)

# ------------------------------------------------------------------------- #
# Listas cerradas                                                            #
# ------------------------------------------------------------------------- #
# Nueve tipos y trece predicados: sin cambio (L-ESQ-R2 §10). El orden es el de
# prompt_congelado (ENTITY_TYPES_CONGELADO, PREDICATES_CONGELADO); el selftest
# lo compara contra el módulo sellado.
TIPOS_ENTIDAD = ("Comunicacion", "TextoOrdenado", "Operacion", "Restriccion", "Excepcion",
                 "Obligacion", "Potestad", "Condicion", "Definicion")
PREDICADOS = ("establecida_en", "referencia", "modificada_por", "aplica_a", "regula", "exceptua",
              "exceptua_obligacion", "prohibe", "limita", "ejecuta", "requiere", "condiciona",
              "condicion_de")
PREDICADOS_SUJETO = ("aplica_a", "ejecuta")
TIPO_SUJETO = "Sujeto"  # pseudo-tipo del extremo sujeto, como en producción

# Matriz congelada (prompt_congelado.DOMAIN_RANGE_CONGELADO, sin cambio desde el v2).
FIRMAS_CONGELADAS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "establecida_en": (("Restriccion", "Obligacion", "Excepcion", "Operacion", "Potestad",
                        "Condicion", "Definicion"), ("TextoOrdenado",)),
    "referencia": (("TextoOrdenado",), ("Comunicacion",)),
    "modificada_por": (("TextoOrdenado",), ("Comunicacion",)),
    "aplica_a": (("Restriccion", "Obligacion", "Operacion", "Excepcion", "Potestad"), (TIPO_SUJETO,)),
    "regula": (("Restriccion", "Obligacion"), ("Operacion",)),
    "exceptua": (("Excepcion",), ("Restriccion",)),
    "exceptua_obligacion": (("Excepcion",), ("Obligacion",)),
    "prohibe": (("Restriccion",), ("Operacion",)),
    "limita": (("Restriccion",), ("Operacion",)),
    "ejecuta": ((TIPO_SUJETO,), ("Operacion",)),
    "requiere": (("Operacion",), ("Obligacion",)),
    "condiciona": (("Obligacion",), ("Operacion",)),
    "condicion_de": (("Condicion",), ("Excepcion", "Obligacion", "Restriccion")),
}
# Ampliación de L-ESQ-R2 §6.3 (X1, opción ii): condicion_de → Operacion y → Potestad.
AMPLIACION_R2: tuple[tuple[str, str, str], ...] = (
    ("condicion_de", "Condicion", "Operacion"),
    ("condicion_de", "Condicion", "Potestad"),
)


def _matriz_r2() -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    m = {p: (tuple(d), tuple(r)) for p, (d, r) in FIRMAS_CONGELADAS.items()}
    for p, d, r in AMPLIACION_R2:
        dom, ran = m[p]
        m[p] = (dom if d in dom else dom + (d,), ran if r in ran else ran + (r,))
    return m


FIRMAS_R2 = _matriz_r2()


def firma_congelada(src: str, pred: str, tgt: str) -> bool:
    if pred not in FIRMAS_CONGELADAS:
        return False
    d, r = FIRMAS_CONGELADAS[pred]
    return src in d and tgt in r


def firma_r2(src: str, pred: str, tgt: str) -> bool:
    if pred not in FIRMAS_R2:
        return False
    d, r = FIRMAS_R2[pred]
    return src in d and tgt in r


# Predicados derivados por código en el ensamblado (enmienda 2 de L-ESQ-R2,
# FIRMADA en 5f9a731; enmienda 1 al mandato de U-R2-CODIGO). E1 no los emite:
# PREDICADOS, FIRMAS_CONGELADAS, RelacionR2 y el tool schema no cambian. E3 no
# los verifica, así que no llevan las marcas de las relaciones de E1.
PREDICADOS_DERIVADOS = ("remite_a",)
TIPOS_CONTENIDO = ("Operacion", "Restriccion", "Excepcion", "Obligacion", "Potestad", "Condicion",
                   "Definicion")
# §2: siete tipos de contenido como origen; los siete y TextoOrdenado como destino
# (56 firmas). Comunicacion y Sujeto quedan fuera.
FIRMAS_DERIVADAS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "remite_a": (TIPOS_CONTENIDO, TIPOS_CONTENIDO + ("TextoOrdenado",)),
}
# §3: alcance de la remisión, propiedad de la arista (lista cerrada).
ALCANCE_REMISION = ("to_entero", "interna", "externa")
PROPIEDADES_REMISION = ("alcance", "destino", "evidencia")


def firma_derivada(src: str, pred: str, tgt: str) -> bool:
    if pred not in FIRMAS_DERIVADAS:
        return False
    d, r = FIRMAS_DERIVADAS[pred]
    return src in d and tgt in r


# `establecida_en` derivada de la procedencia (decisión 11 del mandato de U-R2-CODIGO;
# ensamblar_tanda0.derivar_establecida_en): el ensamblado la agrega hacia el TextoOrdenado de cada TO de la
# procedencia de un nodo de contenido que no la trae de E1. El predicado es también de E1, así que la arista se
# declara derivada por su `rol_fuente` y no por el predicado: no lleva las marcas de una relación emitida por E1 y
# E3 no la verifica (U-PROMPT-R2, nota del 04/10/2026 al mandato, punto d).
ROL_FUENTE_DERIVADA_DE_PROCEDENCIA = "derivada_de_procedencia"
PREDICADOS_DERIVADOS_DE_PROCEDENCIA = ("establecida_en",)


# Relaciones del esqueleto (E5; grafo_v2/code/schema.py, RELACIONES_ESQUELETO) y
# la arista de cuarentena `padre_sugerido`: entre sujetos (Sujeto → Sujeto).
# Las agrega el ensamblado; E1 no las emite (decisión 3 sobre el FRENO R3 de
# U-R2-CODIGO).
RELACIONES_ESQUELETO = ("subclase_de", "miembro_de", "instancia_de", "parte_de")
RELACIONES_SUJETO_A_SUJETO = RELACIONES_ESQUELETO + ("padre_sugerido",)


def firma_esqueleto(src: str, rel: str, tgt: str) -> bool:
    return rel in RELACIONES_SUJETO_A_SUJETO and src == TIPO_SUJETO and tgt == TIPO_SUJETO


def firma_arista(src: str, rel: str, tgt: str) -> bool:
    """Firma de una arista del grafo r2: la matriz r2 de E1, la de los
    predicados derivados o la del esqueleto."""
    return firma_r2(src, rel, tgt) or firma_derivada(src, rel, tgt) or firma_esqueleto(src, rel, tgt)


OBLIGACION_TIPO = ("presentacion_informativa", "calculo", "asignacion", "comunicacion_a_cliente",
                   "reporte_al_supervisor", "otra")
RESTRICCION_TIPO = ("prohibicion", "limite_cuantitativo", "limite_cualitativo")
COMUNICACION_TIPO = ("A", "B", "C", "externa")
FRECUENCIA = ("diaria", "semanal", "mensual", "trimestral", "semestral", "anual")
COMPARACION = ("maximo_inclusivo", "maximo_estricto", "minimo_inclusivo", "minimo_estricto",
               "igual", "coeficiente", "no_determinada")
UNIDAD = ("porcentaje", "moneda", "dias", "meses", "anios", "veces", "uva")
UNIDADES_TEMPORALES = ("dias", "meses", "anios")
# Plazos con unidad fuera de la lista cerrada (llevan la marca): siguen siendo
# plazos para la regla «sin marcador» de L-ESQ-R2 §1.3.3.
UNIDADES_TEMPORALES_FUERA = ("horas", "semanas")
MONEDA = ("ARS", "USD", "EUR")
DIAS_TIPO = ("corridos", "habiles")
CATEGORIA_OMISION = ("meta_normativo", "tabla", "formula", "fuera_de_tipos", "relacion_sin_predicado")
MENCION_VERIFICADA = ("exacta", "tokens", "no", "ausente")
TRAMO_VERIFICADO = ("exacta", "tokens", "no", "ausente")
COHERENCIA_TIPO_PREDICADO = ("coherente", "incoherente", "no_evaluable")
ORIGEN_OMISION = ("e1", "v3_omisiones_no_prosa", "validador_p_e3")
ORIGEN_UMBRAL = ("e1", "descripcion", "campo_v3")

# Tipos que llevan la lista de umbrales (L-ESQ-R2 §1.3 a). Potestad queda fuera
# (decisión 5): su clave `umbral` va a properties_no_definidas.
TIPOS_CON_UMBRALES = ("Restriccion", "Obligacion", "Condicion", "Excepcion")

# Claves de properties por tipo en r2 (§0.2 con §1: el plazo pasa a la lista,
# la frecuencia a un campo propio; `umbrales` es la lista).
CLAVES_R2: dict[str, tuple[str, ...]] = {
    "Comunicacion": ("codigo", "tipo", "numero"),
    "TextoOrdenado": ("materia", "archivo", "version"),
    "Operacion": ("tipo", "descripcion"),
    "Restriccion": ("descripcion", "tipo", "umbrales"),
    "Excepcion": ("descripcion", "umbrales"),
    "Obligacion": ("descripcion", "tipo", "frecuencia", "umbrales"),
    "Potestad": ("descripcion",),
    "Condicion": ("descripcion", "umbrales"),
    "Definicion": ("termino", "descripcion"),
}
# Claves definidas en v3 que r2 reemplaza por la lista: se conservan aparte
# como insumo del paso de r2a (L-ESQ-R2 §1.4), sin renombrarse.
CLAVES_HEREDADAS_V3: dict[str, tuple[str, ...]] = {
    "Restriccion": ("umbral",),
    "Obligacion": ("plazo",),
}
# Campos de propiedad con lista cerrada: (tipo, clave) → lista.
LISTAS_PROPIEDAD: dict[tuple[str, str], tuple[str, ...]] = {
    ("Obligacion", "tipo"): OBLIGACION_TIPO,
    ("Restriccion", "tipo"): RESTRICCION_TIPO,
    ("Comunicacion", "tipo"): COMUNICACION_TIPO,
    ("Obligacion", "frecuencia"): FRECUENCIA,
}

Texto = Annotated[str, Field(min_length=1)]


# ------------------------------------------------------------------------- #
# Elemento de umbral (L-ESQ-R2 §1.3 a)                                        #
# ------------------------------------------------------------------------- #
class ElementoUmbral(BaseModel):
    """Un elemento de la lista de umbrales: tramo literal, valor, unidad,
    comparación y base. Lo arma el código (U-R2-CODIGO, r2a sobre la
    descripción, r2b sobre el tramo de E1); un valor fuera de lista lleva la
    marca, no se descarta."""
    model_config = ConfigDict(extra="forbid")

    tramo: Texto
    valor: Optional[str] = Field(default=None, pattern=r"^-?\d+(\.\d+)?$")
    unidad: Optional[str] = None
    moneda: Optional[str] = None
    dias_tipo: Optional[str] = None
    comparacion: str
    base: Optional[str] = None
    comparacion_asumida: bool = False
    regla_comparacion: Optional[str] = None
    origen: Optional[Literal["e1", "descripcion", "campo_v3"]] = None
    tramo_verificado: Optional[str] = None
    fuera_de_lista: list[str] = Field(default_factory=list)
    originales: dict[str, Any] = Field(default_factory=dict)
    # Resolución de la base (L-ESQ-R2 §1.3 c) y verificación contra las tablas
    # de E0 (§1.4), en el elemento (decisión 3 sobre el FRENO R3 de U-R2-CODIGO).
    base_destino: Optional[Texto] = None
    base_via: Optional[Literal["remision", "definicion"]] = None
    base_no_resuelta: bool = False
    verificado_en_tabla: Optional[bool] = None

    @model_validator(mode="after")
    def _listas(self) -> "ElementoUmbral":
        for campo, lista in (("comparacion", COMPARACION), ("unidad", UNIDAD),
                             ("moneda", MONEDA), ("dias_tipo", DIAS_TIPO)):
            v = getattr(self, campo)
            if v is None:
                continue
            if v not in lista and campo not in self.fuera_de_lista:
                raise ValueError(f"{campo}={v!r} fuera de lista sin la marca fuera_de_lista")
            if v in lista and campo in self.fuera_de_lista:
                raise ValueError(f"{campo}={v!r} está en la lista y lleva la marca fuera_de_lista")
        if self.comparacion_asumida and (
                self.comparacion != "maximo_inclusivo"
                or self.unidad not in UNIDADES_TEMPORALES + UNIDADES_TEMPORALES_FUERA):
            raise ValueError("comparacion_asumida solo en un plazo, con maximo_inclusivo")
        if self.moneda is not None and self.unidad != "moneda":
            raise ValueError("moneda sin unidad moneda")
        if self.dias_tipo is not None and self.unidad != "dias":
            raise ValueError("dias_tipo sin unidad dias")
        if (self.base_destino is None) != (self.base_via is None):
            raise ValueError("base_destino y base_via van juntas")
        if self.base_destino is not None and self.base is None:
            raise ValueError("base_destino sin base")
        if self.base_no_resuelta and (self.base is None or self.base_destino is not None):
            raise ValueError("base_no_resuelta solo con base y sin destino")
        return self


# ------------------------------------------------------------------------- #
# Properties por tipo (elemento validado y nodo)                              #
# ------------------------------------------------------------------------- #
class _Props(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PropsComunicacion(_Props):
    codigo: Optional[Texto] = None
    tipo: Optional[str] = None
    numero: Optional[int] = None


class PropsTextoOrdenado(_Props):
    materia: Optional[Texto] = None
    archivo: Optional[Texto] = None
    version: Optional[Texto] = None


class PropsOperacion(_Props):
    tipo: Optional[Texto] = None
    descripcion: Optional[Texto] = None


class PropsRestriccion(_Props):
    descripcion: Optional[Texto] = None
    tipo: Optional[str] = None
    umbrales: list[ElementoUmbral] = Field(default_factory=list)


class PropsExcepcion(_Props):
    descripcion: Optional[Texto] = None
    umbrales: list[ElementoUmbral] = Field(default_factory=list)


class PropsObligacion(_Props):
    descripcion: Optional[Texto] = None
    tipo: Optional[str] = None
    frecuencia: Optional[str] = None
    umbrales: list[ElementoUmbral] = Field(default_factory=list)


class PropsPotestad(_Props):
    descripcion: Optional[Texto] = None


class PropsCondicion(_Props):
    descripcion: Optional[Texto] = None
    umbrales: list[ElementoUmbral] = Field(default_factory=list)


class PropsDefinicion(_Props):
    termino: Optional[Texto] = None
    descripcion: Optional[Texto] = None


PROPS_POR_TIPO: dict[str, type[_Props]] = {
    "Comunicacion": PropsComunicacion, "TextoOrdenado": PropsTextoOrdenado,
    "Operacion": PropsOperacion, "Restriccion": PropsRestriccion, "Excepcion": PropsExcepcion,
    "Obligacion": PropsObligacion, "Potestad": PropsPotestad, "Condicion": PropsCondicion,
    "Definicion": PropsDefinicion,
}

# Marcas de la cadena de ensamblado en las properties del nodo del grafo, con
# la forma de los grafos sellados: la cola humana (r1_cola_flaggeada.
# flaggear_grafo: cola_humana, cola_chunks, estado_e3) y la colisión cross-TO
# (r1_invariantes.merge_grafos_guardado: colision_cross_to). Solo el nodo del
# grafo las admite (NodoR2); la entidad validada de E1 (EntidadR2), no
# (decisión 3 sobre el FRENO R3 de U-R2-CODIGO).
MARCAS_NODO = ("cola_humana", "cola_chunks", "estado_e3", "colision_cross_to")
PROPS_NODO_POR_TIPO: dict[str, type[_Props]] = {
    t: create_model(f"{c.__name__}Nodo", __base__=c,
                    cola_humana=(Optional[Literal["true"]], None),
                    cola_chunks=(Optional[list[Texto]], None),
                    estado_e3=(Optional[Texto], None),
                    colision_cross_to=(Optional[Literal["true"]], None))
    for t, c in PROPS_POR_TIPO.items()}


def _controlar_marcas_entidad(tipo: str, props: _Props, fuera_de_lista: list[str],
                              valores_no_tipados: dict[str, Any]) -> None:
    for (t, clave), lista in LISTAS_PROPIEDAD.items():
        if t != tipo:
            continue
        v = getattr(props, clave)
        if v is None:
            continue
        if v not in lista and clave not in fuera_de_lista:
            raise ValueError(f"{tipo}.{clave}={v!r} fuera de lista sin la marca fuera_de_lista")
        if v in lista and clave in fuera_de_lista:
            raise ValueError(f"{tipo}.{clave}={v!r} está en la lista y lleva la marca")
    for k in valores_no_tipados:
        if getattr(props, k, None) is not None:
            raise ValueError(f"{tipo}.{k} figura a la vez tipado y no tipado")


class Provenance(BaseModel):
    model_config = ConfigDict(extra="allow")
    to: Optional[str] = None
    archivo: Optional[str] = None
    punto: Optional[str] = None
    rol_documental: Optional[str] = None

    @model_validator(mode="after")
    def _evidencia(self) -> "Provenance":
        # Decisión 15 (protocolo D6): el tramo de evidencia de la entidad, con su verificación, va en la
        # procedencia: un nodo fundido de varios chunks guarda un tramo por procedencia (diseño de U-PROMPT-R2,
        # §8.2). Decisión 16: la verificación del término literal de la Definicion, también por procedencia.
        extra = self.model_extra or {}
        if "tramo" in extra or "tramo_verificado" in extra:
            tv = extra.get("tramo_verificado")
            if tv not in TRAMO_VERIFICADO:
                raise ValueError(f"tramo_verificado={tv!r} fuera de {TRAMO_VERIFICADO}")
            if (tv == "ausente") != (extra.get("tramo") is None):
                raise ValueError("tramo_verificado ausente ⇔ sin tramo")
        if extra.get("tramo_modelo") is not None and extra.get("tramo_verificado") != "tokens":
            raise ValueError("tramo_modelo solo con tramo_verificado tokens")
        if "termino_verificado" in extra and extra["termino_verificado"] not in TRAMO_VERIFICADO:
            raise ValueError(f"termino_verificado={extra['termino_verificado']!r} fuera de {TRAMO_VERIFICADO}")
        return self


# ------------------------------------------------------------------------- #
# Elemento validado (salida del validador r2)                                 #
# ------------------------------------------------------------------------- #
class EntidadR2(BaseModel):
    """Entidad aceptada por el validador r2. `properties` cumple la definición
    del tipo; lo demás vive en `properties_no_definidas` o, si es una clave v3
    que r2 reemplaza, en `campos_heredados_v3`."""
    model_config = ConfigDict(extra="forbid")

    local_id: Texto
    type: Literal[TIPOS_ENTIDAD]  # type: ignore[valid-type]
    label: Texto
    punto: Texto
    provenance: Provenance
    properties: dict[str, Any]
    umbrales_tramos: list[Texto] = Field(default_factory=list)
    fuera_de_lista: list[str] = Field(default_factory=list)
    originales: dict[str, Any] = Field(default_factory=dict)
    properties_no_definidas: dict[str, Any] = Field(default_factory=dict)
    campos_heredados_v3: dict[str, Any] = Field(default_factory=dict)
    valores_no_tipados: dict[str, Any] = Field(default_factory=dict)
    campos_no_definidos: dict[str, Any] = Field(default_factory=dict)
    # Si el elemento pasó por E3 (nota del 04/10/2026 al mandato de U-PROMPT-R2): lo fija el validador r2 con lo
    # que vio E3 en la forma r2; None en la forma v3, que no lo registra.
    paso_por_e3: Optional[bool] = None

    @model_validator(mode="after")
    def _definicion(self) -> "EntidadR2":
        modelo = PROPS_POR_TIPO[self.type]
        props = modelo.model_validate(self.properties)
        _controlar_marcas_entidad(self.type, props, self.fuera_de_lista, self.valores_no_tipados)
        heredadas = CLAVES_HEREDADAS_V3.get(self.type, ())
        for k in self.campos_heredados_v3:
            if k not in heredadas:
                raise ValueError(f"{self.type}: {k!r} no es clave heredada de v3")
        if self.umbrales_tramos and self.type not in TIPOS_CON_UMBRALES:
            raise ValueError(f"{self.type} no lleva umbrales")
        for k in self.properties_no_definidas:
            if k in CLAVES_R2[self.type]:
                raise ValueError(f"{self.type}.{k} está definida y figura como no definida")
        return self


class RelacionR2(BaseModel):
    """Relación aceptada por el validador r2. En las de sujeto, `sujeto_id_modelo`
    es la sugerencia del modelo (P-b2) y la mención lleva su verificación."""
    model_config = ConfigDict(extra="forbid")

    source: Optional[Texto] = None
    target: Optional[Texto] = None
    predicate: Literal[PREDICADOS]  # type: ignore[valid-type]
    punto: Texto
    provenance: Provenance
    tipo_source: Texto
    tipo_target: Texto
    sujeto_mencion: Optional[Texto] = None
    sujeto_mencion_modelo: Optional[Texto] = None
    mencion_verificada: Optional[Literal[MENCION_VERIFICADA]] = None  # type: ignore[valid-type]
    sujeto_id_modelo: Optional[str] = None
    padre_sugerido: Optional[str] = None
    padre_sugerido_crudo: Optional[str] = None
    no_verificada_e3: bool = False
    coherencia_tipo_predicado: Optional[Literal[COHERENCIA_TIPO_PREDICADO]] = None  # type: ignore[valid-type]
    indice_crudo: Optional[int] = None
    originales: dict[str, Any] = Field(default_factory=dict)
    campos_no_definidos: dict[str, Any] = Field(default_factory=dict)
    # Decisión 17 (protocolo D8): las otras_propiedades de la relación, como no definidas.
    properties_no_definidas: dict[str, Any] = Field(default_factory=dict)
    # Si la relación pasó por E3 (nota del 04/10/2026 al mandato de U-PROMPT-R2): None en la forma v3.
    paso_por_e3: Optional[bool] = None

    @model_validator(mode="after")
    def _invariantes(self) -> "RelacionR2":
        if not firma_r2(self.tipo_source, self.predicate, self.tipo_target):
            raise ValueError(f"firma fuera de la matriz r2: {self.tipo_source} --{self.predicate}--> "
                             f"{self.tipo_target}")
        if self.paso_por_e3 is None:
            # Forma v3 (los grafos r2a sellados): la marca va por la firma, porque E3 vio la validación del
            # perfil de E1, con la matriz congelada.
            nueva = not firma_congelada(self.tipo_source, self.predicate, self.tipo_target)
            if nueva != self.no_verificada_e3:
                raise ValueError("no_verificada_e3 debe marcar exactamente las firmas nuevas de r2")
        elif self.no_verificada_e3 == self.paso_por_e3:
            # Forma r2: la marca va por lo que pasó por E3, no por la firma (nota del 04/10/2026, punto c).
            raise ValueError("no_verificada_e3 debe marcar exactamente lo que no pasó por E3")
        if self.predicate in PREDICADOS_SUJETO:
            if self.mencion_verificada is None:
                raise ValueError("relación de sujeto sin mencion_verificada")
            if (self.mencion_verificada == "ausente") != (self.sujeto_mencion is None):
                raise ValueError("mencion_verificada ausente ⇔ sin sujeto_mencion")
            if self.sujeto_id_modelo is not None and self.sujeto_id_modelo not in SUJETOS_R2_SET:
                raise ValueError(f"sujeto_id_modelo fuera del catálogo r2: {self.sujeto_id_modelo}")
            if self.padre_sugerido is not None and self.padre_sugerido not in SUJETOS_R2_SET:
                raise ValueError(f"padre_sugerido fuera del catálogo r2: {self.padre_sugerido}")
        else:
            if any(v is not None for v in (self.sujeto_mencion, self.mencion_verificada,
                                           self.sujeto_id_modelo, self.padre_sugerido)):
                raise ValueError(f"campos de sujeto en {self.predicate}")
        if (self.predicate in ("prohibe", "limita")) != (self.coherencia_tipo_predicado is not None):
            raise ValueError("coherencia_tipo_predicado va exactamente en prohibe y limita")
        return self


class OmisionR2(BaseModel):
    """Omisión con categoría, tramo y nota (P-e1). Las del crudo v3 llegan sin
    categoría ni tramo (L-ESQ-R2 §5.4); las de P-e3, con categoría
    fuera_de_tipos y sin tramo."""
    model_config = ConfigDict(extra="forbid")

    categoria: Optional[str] = None
    tramo: Optional[str] = None
    nota: Optional[str] = None
    origen: Literal[ORIGEN_OMISION]  # type: ignore[valid-type]
    tramo_verificado: Literal[TRAMO_VERIFICADO]  # type: ignore[valid-type]
    tramo_modelo: Optional[str] = None
    tramo_corto: bool = False
    senal_tabla_no_detectada: bool = False
    fuera_de_lista: list[str] = Field(default_factory=list)
    originales: dict[str, Any] = Field(default_factory=dict)
    campos_no_definidos: dict[str, Any] = Field(default_factory=dict)
    # Decisión 17 (protocolo D8): los local_id de la relación que el esquema no representa.
    source: Optional[Texto] = None
    destino: Optional[Texto] = None

    @model_validator(mode="after")
    def _invariantes(self) -> "OmisionR2":
        if (self.source is not None or self.destino is not None) and self.categoria != "relacion_sin_predicado":
            raise ValueError("source y destino solo en relacion_sin_predicado")
        if self.categoria is None:
            if self.origen != "v3_omisiones_no_prosa" and "categoria" not in self.fuera_de_lista:
                raise ValueError("omisión sin categoría fuera de la lectura del crudo v3 y sin marca")
        elif self.categoria not in CATEGORIA_OMISION and "categoria" not in self.fuera_de_lista:
            raise ValueError(f"categoria={self.categoria!r} fuera de lista sin la marca")
        if (self.tramo_verificado == "ausente") != (self.tramo is None):
            raise ValueError("tramo_verificado ausente ⇔ sin tramo")
        if self.origen == "validador_p_e3" and self.categoria != "fuera_de_tipos":
            raise ValueError("la omisión de P-e3 es fuera_de_tipos")
        return self


# ------------------------------------------------------------------------- #
# Nodo y arista del grafo                                                     #
# ------------------------------------------------------------------------- #
class NodoR2(BaseModel):
    """Nodo del grafo r2. `properties.umbrales` es la lista de elementos de
    umbral (en los cuatro tipos que la llevan); las marcas van al nivel del
    nodo. Lo construye E2 con el perfil r2 (U-R2-CODIGO)."""
    model_config = ConfigDict(extra="forbid")

    id: Texto
    type: Literal[TIPOS_ENTIDAD + (TIPO_SUJETO,)]  # type: ignore[valid-type]
    label: Texto
    properties: dict[str, Any]
    provenance: Optional[Provenance] = None
    provenances: list[Provenance] = Field(default_factory=list)
    rol_fuente: Optional[str] = None
    fuera_de_lista: list[str] = Field(default_factory=list)
    originales: dict[str, Any] = Field(default_factory=dict)
    properties_no_definidas: dict[str, Any] = Field(default_factory=dict)
    campos_heredados_v3: dict[str, Any] = Field(default_factory=dict)
    valores_no_tipados: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _definicion(self) -> "NodoR2":
        if self.type == TIPO_SUJETO:
            return self
        props = PROPS_NODO_POR_TIPO[self.type].model_validate(self.properties)
        _controlar_marcas_entidad(self.type, props, self.fuera_de_lista, self.valores_no_tipados)
        if len({getattr(props, k) is None for k in ("cola_humana", "cola_chunks", "estado_e3")}) > 1:
            raise ValueError("cola_humana, cola_chunks y estado_e3 van juntas")
        return self


class AristaR2(BaseModel):
    """Arista del grafo r2, con las marcas de la relación de origen. Una arista
    de predicado derivado (`remite_a`) lleva `alcance`, `destino` y `evidencia`
    en `properties` y ninguna marca de relación emitida por E1."""
    model_config = ConfigDict(extra="forbid")

    source: Texto
    target: Texto
    relation: Literal[PREDICADOS + PREDICADOS_DERIVADOS + RELACIONES_SUJETO_A_SUJETO]  # type: ignore[valid-type]
    provenance: Optional[Provenance] = None
    provenances: list[Provenance] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    rol_fuente: Optional[str] = None
    sujeto_mencion: Optional[str] = None
    sujeto_mencion_modelo: Optional[str] = None
    mencion_verificada: Optional[Literal[MENCION_VERIFICADA]] = None  # type: ignore[valid-type]
    sujeto_id_modelo: Optional[str] = None
    metodo_resolucion: Optional[str] = None
    no_verificada_e3: bool = False
    coherencia_tipo_predicado: Optional[Literal[COHERENCIA_TIPO_PREDICADO]] = None  # type: ignore[valid-type]
    calificador: Optional[Texto] = None
    # Decisión 17 (protocolo D8): las otras_propiedades de la relación de E1, como no definidas.
    properties_no_definidas: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _invariantes(self) -> "AristaR2":
        derivada = (self.relation in PREDICADOS_DERIVADOS or self.relation in RELACIONES_SUJETO_A_SUJETO
                    or self.rol_fuente == ROL_FUENTE_DERIVADA_DE_PROCEDENCIA)
        if derivada and self.properties_no_definidas:
            raise ValueError(f"{self.relation}: properties_no_definidas solo en una relación emitida por E1")
        if self.rol_fuente == ROL_FUENTE_DERIVADA_DE_PROCEDENCIA:
            if self.relation not in PREDICADOS_DERIVADOS_DE_PROCEDENCIA:
                raise ValueError(f"{self.relation}: rol_fuente {ROL_FUENTE_DERIVADA_DE_PROCEDENCIA} solo en "
                                 f"{PREDICADOS_DERIVADOS_DE_PROCEDENCIA}")
            if self.no_verificada_e3 or self.properties or any(
                    v is not None for v in (self.sujeto_mencion, self.sujeto_mencion_modelo, self.mencion_verificada,
                                            self.sujeto_id_modelo, self.metodo_resolucion,
                                            self.coherencia_tipo_predicado, self.calificador)):
                raise ValueError(f"{self.relation} derivada de la procedencia: lleva una marca de relación emitida "
                                 f"por E1")
        if (self.relation in ("prohibe", "limita")) != (self.coherencia_tipo_predicado is not None):
            raise ValueError("coherencia_tipo_predicado va exactamente en prohibe y limita")
        if self.mencion_verificada is not None and self.relation not in PREDICADOS_SUJETO:
            raise ValueError("mencion_verificada solo en aristas de sujeto")
        if self.calificador is not None and self.relation not in PREDICADOS_SUJETO:
            raise ValueError("calificador solo en aristas de sujeto")
        if self.relation in RELACIONES_SUJETO_A_SUJETO and (self.no_verificada_e3 or any(
                v is not None for v in (self.sujeto_mencion, self.sujeto_mencion_modelo, self.sujeto_id_modelo,
                                        self.metodo_resolucion, self.coherencia_tipo_predicado))):
            raise ValueError(f"{self.relation}: lleva una marca de relación emitida por E1")
        if self.relation in PREDICADOS_DERIVADOS:
            p = self.properties
            if tuple(sorted(p)) != tuple(sorted(PROPIEDADES_REMISION)):
                raise ValueError(f"{self.relation}: properties debe ser exactamente {PROPIEDADES_REMISION}")
            if p["alcance"] not in ALCANCE_REMISION:
                raise ValueError(f"{self.relation}: alcance={p['alcance']!r} fuera de {ALCANCE_REMISION}")
            for k in ("destino", "evidencia"):
                if not isinstance(p[k], str) or not p[k].strip():
                    raise ValueError(f"{self.relation}: {k} vacío")
            if (p["alcance"] == "to_entero") != p["destino"].endswith("::TO"):
                raise ValueError(f"{self.relation}: alcance to_entero ⇔ destino de texto ordenado entero")
            if self.no_verificada_e3 or self.rol_fuente is not None or any(
                    v is not None for v in (self.sujeto_mencion, self.sujeto_mencion_modelo,
                                            self.sujeto_id_modelo, self.metodo_resolucion,
                                            self.coherencia_tipo_predicado)):
                raise ValueError(f"{self.relation}: lleva una marca de relación emitida por E1 o rol_fuente")
        return self


# ------------------------------------------------------------------------- #
# Salida de E1 del perfil r2 (forma de r2b): de acá sale el tool schema        #
# ------------------------------------------------------------------------- #
SujetoIdR2 = Literal[SUJETOS_R2]  # type: ignore[valid-type]


class _PropsE1(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PropsComunicacionE1(_PropsE1):
    # Decisión 16 (protocolo D7): tipo y numero se derivan en código desde codigo.
    codigo: str = Field(default=None, description=(
        'Código de la Comunicación, ej. "A-7825"; para una ley, un decreto o una resolución, su denominación '
        'tal como la cita el texto.'))


class PropsOperacionE1(_PropsE1):
    tipo: str = Field(default=None, description="Texto libre.")
    descripcion: str = Field(default=None)


class PropsRestriccionE1(_PropsE1):
    descripcion: str = Field(default=None)
    tipo: Literal[RESTRICCION_TIPO] = Field(default=None)  # type: ignore[valid-type]


class PropsExcepcionE1(_PropsE1):
    descripcion: str = Field(default=None)


class PropsObligacionE1(_PropsE1):
    descripcion: str = Field(default=None)
    tipo: Literal[OBLIGACION_TIPO] = Field(default=None)  # type: ignore[valid-type]
    frecuencia: str = Field(default=None, description="Tramo literal de la frecuencia, copiado del texto.")


class PropsPotestadE1(_PropsE1):
    descripcion: str = Field(default=None)


class PropsCondicionE1(_PropsE1):
    descripcion: str = Field(default=None)


class PropsDefinicionE1(_PropsE1):
    termino: str = Field(default=None, description="Término definido, copiado tal cual lo nombra el texto.")
    descripcion: str = Field(default=None)


class UmbralE1(BaseModel):
    # Par A (L-ESQ-R2 §1.2 y §1.3 b): E1 copia el tramo literal; valor, unidad,
    # comparación y base los fija el código. Sin docstring: iría al tool schema.
    model_config = ConfigDict(extra="forbid")
    tramo: str = Field(description="Tramo del texto con la cuantía y su comparación, copiado tal cual.")


_DESC_LOCAL_ID = "Identificador local único dentro del chunk."
_DESC_LABEL = "Etiqueta corta y canónica, contenido distintivo al principio."
_DESC_PUNTO = "Unidad estructural que funda la entidad. Uno de los 'Puntos admitidos' del mensaje del chunk."
_DESC_UMBRALES = "Un elemento por cuantía (monto, porcentaje, plazo, «veces»): el tramo literal."
_DESC_TRAMO = ("Tramo del texto que funda la entidad, copiado tal cual: el más corto que la sostenga "
               "por sí solo.")
_DESC_OTRAS = ("Opcional: propiedades que el texto expresa y la definición del tipo no prevé "
               "(nombre → valor). Nunca se descartan: se registran aparte.")


class _EntidadE1(BaseModel):
    # Las properties de cada tipo son cerradas; lo no previsto va a
    # otras_propiedades (decisión de la autora sobre P1: L-ESQ-R2 §2 registra y
    # nunca rechaza una clave no prevista, y un schema cerrado sin un lugar para
    # ella hace que el modelo deje de emitirla).
    model_config = ConfigDict(extra="forbid")
    local_id: str = Field(description=_DESC_LOCAL_ID)
    label: str = Field(description=_DESC_LABEL)
    punto: str = Field(description=_DESC_PUNTO)
    otras_propiedades: dict[str, str] = Field(default=None, description=_DESC_OTRAS)


class _EntidadConTramoE1(_EntidadE1):
    # Decisión 15 (protocolo D6): tramo literal de evidencia por entidad.
    tramo: str = Field(description=_DESC_TRAMO)


class ComunicacionE1(_EntidadConTramoE1):
    type: Literal["Comunicacion"]
    properties: PropsComunicacionE1 = Field(default=None)


class TextoOrdenadoE1(_EntidadE1):
    # Decisión 16 (protocolo D7): materia, archivo y version se derivan en código desde E0.
    type: Literal["TextoOrdenado"]


class OperacionE1(_EntidadConTramoE1):
    type: Literal["Operacion"]
    properties: PropsOperacionE1 = Field(default=None)


class RestriccionE1(_EntidadConTramoE1):
    type: Literal["Restriccion"]
    properties: PropsRestriccionE1 = Field(default=None)
    umbrales: list[UmbralE1] = Field(default=None, description=_DESC_UMBRALES)


class ExcepcionE1(_EntidadConTramoE1):
    type: Literal["Excepcion"]
    properties: PropsExcepcionE1 = Field(default=None)
    umbrales: list[UmbralE1] = Field(default=None, description=_DESC_UMBRALES)


class ObligacionE1(_EntidadConTramoE1):
    type: Literal["Obligacion"]
    properties: PropsObligacionE1 = Field(default=None)
    umbrales: list[UmbralE1] = Field(default=None, description=_DESC_UMBRALES)


class PotestadE1(_EntidadConTramoE1):
    type: Literal["Potestad"]
    properties: PropsPotestadE1 = Field(default=None)


class CondicionE1(_EntidadConTramoE1):
    type: Literal["Condicion"]
    properties: PropsCondicionE1 = Field(default=None)
    umbrales: list[UmbralE1] = Field(default=None, description=_DESC_UMBRALES)


class DefinicionE1(_EntidadConTramoE1):
    type: Literal["Definicion"]
    properties: PropsDefinicionE1 = Field(default=None)


EntidadE1 = Annotated[
    Union[ComunicacionE1, TextoOrdenadoE1, OperacionE1, RestriccionE1, ExcepcionE1,
          ObligacionE1, PotestadE1, CondicionE1, DefinicionE1],
    Field(discriminator="type"),
]
ENTIDADES_E1 = (ComunicacionE1, TextoOrdenadoE1, OperacionE1, RestriccionE1, ExcepcionE1,
                ObligacionE1, PotestadE1, CondicionE1, DefinicionE1)


class RelacionE1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(default=None, description=(
        "local_id de la entidad source. En aplica_a: el elemento alcanzado. NO usar en ejecuta."))
    target: str = Field(default=None, description=(
        "local_id de la entidad target. En ejecuta: la Operacion. NO usar en aplica_a."))
    predicate: Literal[PREDICADOS]  # type: ignore[valid-type]
    punto: str = Field(description=(
        "Unidad estructural cuyo texto enuncia la conexión. Uno de los 'Puntos admitidos' del mensaje del chunk."))
    sujeto_mencion: str = Field(default=None, description=(
        "SOLO aplica_a/ejecuta, obligatoria en ellos: tramo del texto que nombra al sujeto, copiado tal "
        "cual aparece (mismas palabras, artículos y orden); no la forma del catálogo."))
    sujeto_id: SujetoIdR2 = Field(default=None, description=(  # type: ignore[valid-type]
        "SOLO aplica_a/ejecuta: id del catálogo que corresponde a la mención (sugerencia)."))
    sujeto_propuesto_padre_sugerido: SujetoIdR2 = Field(default=None, description=(  # type: ignore[valid-type]
        "Opcional, sin sujeto_id: id del catálogo sugerido como padre del sujeto mencionado."))
    otras_propiedades: dict[str, str] = Field(default=None, description=_DESC_OTRAS)


class OmisionE1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categoria: Literal[CATEGORIA_OMISION]  # type: ignore[valid-type]
    tramo: str = Field(description="Tramo del texto propio de la unidad que no se extrajo, copiado tal cual.")
    nota: str = Field(default=None, description=(
        "Por qué quedó afuera; en fuera_de_tipos y relacion_sin_predicado, el tipo o el predicado que se habría usado."))
    source: str = Field(default=None, description=(
        "Solo relacion_sin_predicado: local_id de la entidad de origen, si se extrajo."))
    destino: str = Field(default=None, description=(
        "Solo relacion_sin_predicado: local_id de la entidad de destino, si se extrajo."))


class SalidaE1R2(BaseModel):
    # Input del tool call de E1 en el perfil r2 (sin docstring, por el tool schema).
    model_config = ConfigDict(extra="forbid")
    entities: list[EntidadE1]
    relations: list[RelacionE1]
    omisiones: list[OmisionE1] = Field(description=(
        "Obligatoria en todo chunk; vacía si no se omitió nada."))


# ------------------------------------------------------------------------- #
# Generación: tool schema y enums                                            #
# ------------------------------------------------------------------------- #
NOMBRE_TOOL_R2 = "extraer_kg_e1"  # el mismo nombre que prompt_e1.NOMBRE_TOOL
DESCRIPCION_TOOL_R2 = (
    "Extrae entidades y relaciones del chunk según el esquema r2 (9 tipos, 13 predicados, catálogo "
    "cerrado de sujetos). Todo elemento lleva `punto`; toda entidad salvo el TextoOrdenado, el tramo literal que la "
    "funda. Los umbrales van como tramos literales; la mención del sujeto, tal cual aparece; las omisiones, con "
    "categoría y tramo.")


def _limpiar_schema(nodo: Any, defs: dict) -> Any:
    """Inline de $ref, sin `title`, sin `default: null`, Optional → tipo simple,
    unión discriminada → anyOf (el campo `type` con `const` la discrimina)."""
    if isinstance(nodo, list):
        return [_limpiar_schema(x, defs) for x in nodo]
    if not isinstance(nodo, dict):
        return nodo
    if "$ref" in nodo:
        nombre = nodo["$ref"].split("/")[-1]
        base = _limpiar_schema(copy.deepcopy(defs[nombre]), defs)
        extra = {k: v for k, v in nodo.items() if k != "$ref"}
        base.update(_limpiar_schema(extra, defs))
        return base
    out: dict[str, Any] = {}
    for k, v in nodo.items():
        if k in ("title", "$defs", "discriminator"):
            continue
        if k == "default" and v is None:
            continue
        out[k] = _limpiar_schema(v, defs)
    if "oneOf" in out:
        out["anyOf"] = out.pop("oneOf")
    if "anyOf" in out:
        alt = [a for a in out["anyOf"] if a != {"type": "null"}]
        if len(alt) == 1 and len(out["anyOf"]) == 2:
            del out["anyOf"]
            for k, v in alt[0].items():
                out.setdefault(k, v)
    if "const" in out and "type" not in out:
        out["type"] = "string"
    return out


def tool_schema_e1_r2() -> dict:
    """Tool schema del perfil r2, generado de SalidaE1R2."""
    crudo = SalidaE1R2.model_json_schema()
    defs = crudo.get("$defs", {})
    input_schema = _limpiar_schema(crudo, defs)
    return {"name": NOMBRE_TOOL_R2, "description": DESCRIPCION_TOOL_R2, "input_schema": input_schema}


def enums_r2() -> dict:
    """Listas cerradas del perfil r2, desde este módulo y el catálogo r2."""
    return {
        "perfil": "r2",
        "catalogo_r2": {"ruta": str(CATALOGO_R2.relative_to(REPO)), "commit": CATALOGO_R2_COMMIT,
                        "sha256": CATALOGO_R2_SHA256},
        "tipo_entidad": list(TIPOS_ENTIDAD),
        "predicado": list(PREDICADOS),
        "predicados_sujeto": list(PREDICADOS_SUJETO),
        "firmas_congeladas": {p: [list(d), list(r)] for p, (d, r) in FIRMAS_CONGELADAS.items()},
        "ampliacion_r2": [list(x) for x in AMPLIACION_R2],
        "firmas_r2": {p: [list(d), list(r)] for p, (d, r) in FIRMAS_R2.items()},
        "claves_por_tipo": {t: list(c) for t, c in CLAVES_R2.items()},
        "claves_heredadas_v3": {t: list(c) for t, c in CLAVES_HEREDADAS_V3.items()},
        "tipos_con_umbrales": list(TIPOS_CON_UMBRALES),
        "Obligacion.tipo": list(OBLIGACION_TIPO),
        "Restriccion.tipo": list(RESTRICCION_TIPO),
        "Comunicacion.tipo": list(COMUNICACION_TIPO),
        "Obligacion.frecuencia": list(FRECUENCIA),
        "umbral.comparacion": list(COMPARACION),
        "umbral.unidad": list(UNIDAD),
        "umbral.moneda": list(MONEDA),
        "umbral.dias_tipo": list(DIAS_TIPO),
        "omision.categoria": list(CATEGORIA_OMISION),
        "mencion_verificada": list(MENCION_VERIFICADA),
        "tramo_verificado": list(TRAMO_VERIFICADO),
        "coherencia_tipo_predicado": list(COHERENCIA_TIPO_PREDICADO),
        "sujeto_id": list(SUJETOS_R2),
        "sujeto_lapidas": list(SUJETOS_R2_LAPIDAS),
    }
