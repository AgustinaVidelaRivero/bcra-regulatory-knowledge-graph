"""
prompt_v3_b54.py — U-B5.4 fase 2: materialización del PREFIJO v3 (catálogo de
sujetos v3 sobre el prefijo congelado del gate ESQ-3).

Gobernado por el laudo de fase 1 (docs/laudo_B5.4_fase1_catalogo.md, FIRMADO
05/09/2026) sobre el prefijo CONGELADO (`e69feaaa…`/`1be8304e3d77`,
data/experiment/esq/code/prompt_congelado.py). Unidad mecánica $0: construcción
de texto, sin ninguna llamada LLM.

REGLA DURA (mandato U-B5.4, decisión 3): el prefijo congelado se integra TAL
CUAL. Este módulo lo IMPORTA y aplica UNA transformación declarada con ancla
única: el reemplazo del BLOQUE DE CATÁLOGO (de `## Sujetos regulados` al fin de
`## Roles de alcance por TO`). Fuera de ese bloque el texto del sistema queda
BYTE-IDÉNTICO al congelado; en el tool schema solo cambian los DOS enums de
sujeto (`sujeto_id` y `sujeto_propuesto_padre_sugerido`). Ambas cosas las
DEMUESTRA selftest_prompt_v3_b54.py.

Contenido del catálogo v3 (laudo F1.2/F1.3/F1.4/F1.5):
  - RETIROS (5, con lápida en catalogo_sujetos_v3.md): acreedor_del_exterior,
    autoridad_nacional_de_aplicacion, secretaria_de_{comercio,energia,transporte}.
  - ADICIONES (7): entidad_{girada,depositaria,receptora} y
    entidad_originante_de_transferencia (SNP; renombrada por el laudo de
    cierre H1a, 06/09/2026 — def y guarda intactas),
    camara_electronica_de_compensacion (CEC, enmienda de alcance declarada en
    el laudo), banco_central_del_exterior, fmi. BIS NO entra (caso de promoción
    documentado en el artefacto del catálogo).
  - ROLES A2 (30): un id `Sujeto_rol_alcance_<to>` por TO cuyo alcance no es
    clase exacta (tabla_to_rol_post_f1.md, guarda del mapeo). El rol de
    snp_cec fue RETIRADO por el mini-laudo de la autora (05/09/2026, freno 2):
    con CEC en el catálogo, el alcance de snp_cec ES clase exacta y su rol
    duplicaba a la clase (criterio A2 aplicado a la interacción creada por la
    enmienda CEC). Corrección pre-sello, no lápida (el rol nunca integró un
    catálogo sellado); registro en catalogo_sujetos_v3.md.
  - DEFINICIONES: 24 dirigidas (F1.3) + 6 posicionales de adiciones (F1.4;
    `fmi` es instancia autoevidente y va sin def, mismo criterio que BCRA —
    ratificado por el mini-laudo).
  - Composición esperada (mini-laudo del freno 2): 70 − 5 + 7 + 30 = 102. El
    selftest la RECOMPUTA contra el artefacto construido (regla i).

ROL_POR_TO_V3: los 5 TOs dev (pass-through de producción, byte-idénticos) +
66 TOs nuevos (30 rol + 36 mapeo a clase). docvig y fimipyme SIN entrada
(laudo F1.2: huecos sin rol por defecto, válvula sujeto_propuesto abierta).

El cableado a producción NO es de esta unidad (frontera B5.3): este módulo es
el artefacto sellado; el pipeline de producción no lo importa todavía.

Caching (docs/decisiones_caching_extraccion.md, vinculantes): D1 prefijo v3
como bloque único de system con cache_control ephemeral. El sha del prefijo v3
es DISTINTO por construcción del congelado y de todos los previos → namespace
de caché nuevo (la rotación está aceptada por el mandato).
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

# Rutas SIN absolutos embebidos (corrección 1 del laudo de fase 1): todo se
# resuelve relativo a este archivo dentro del repo.
_CODE_DIR = Path(__file__).resolve().parent
_REPO = _CODE_DIR.parents[3]
_ESQ_CODE = _REPO / "data" / "experiment" / "esq" / "code"
for _p in (str(_CODE_DIR), str(_ESQ_CODE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import prompt_congelado as pcg  # noqa: E402 — el congelado se IMPORTA, jamás se edita
from prompt_congelado import (  # noqa: E402
    MAX_OUTPUT_TOKENS,
    NOMBRE_TOOL,
)
import prompt_e1  # noqa: E402 — vía path de la cadena (helpers del mensaje)

# ========================================================================== #
# Candado del texto base                                                     #
# ========================================================================== #

PREFIJO_SHA256_CONGELADO_ESPERADO = (
    "e69feaaa04779bd6347cc9e3974d2c1749519f1230e70a0459e66f46517cd720"
)
PREFIJO_HASH_CONGELADO_ESPERADO = "1be8304e3d77"

# ========================================================================== #
# Anclas del bloque de catálogo (únicas en el prefijo congelado)             #
# ========================================================================== #

ANCLA_INICIO_BLOQUE = "## Sujetos regulados"
ANCLA_FIN_BLOQUE = "\n# PROVENANCE OBLIGATORIA POR ELEMENTO"

# ========================================================================== #
# Laudo F1.5 — RETIROS (líneas exactas del bloque congelado)                 #
# ========================================================================== #

RETIROS_V3: tuple[str, ...] = (
    "Sujeto_acreedor_del_exterior",
    "Sujeto_autoridad_nacional_de_aplicacion",
    "Sujeto_secretaria_de_comercio",
    "Sujeto_secretaria_de_energia",
    "Sujeto_secretaria_de_transporte",
)

# Mantenidos con marca explícita de revisión en r2 (laudo F1.5):
MARCADOS_REVISION_R2: tuple[str, ...] = (
    "Sujeto_ministerio_de_economia",
    "Sujeto_sociedad_de_proposito_especial",
)

# ========================================================================== #
# Laudo F1.3 — 24 definiciones dirigidas (texto de                           #
# definiciones_positivas_post_f1.md, adoptado por el laudo)                  #
# ========================================================================== #

DEFINICIONES_V3: dict[str, str] = {
    "Sujeto_entidad_financiera": "ES el intermediario autorizado por el BCRA a operar bajo la Ley de Entidades Financieras (bancos, compañías financieras, cajas de crédito cooperativas). Quien no tiene esa autorización (aseguradoras, PSP, PNFC, transportadoras de valores) no es entidad financiera.",
    "Sujeto_banco": "ES la entidad financiera autorizada como banco (comercial, de inversión o hipotecario).",
    "Sujeto_banco_comercial": "ES el banco habilitado a todas las operaciones activas, pasivas y de servicios de la LEF (art. 21).",
    "Sujeto_compania_financiera": "ES la entidad financiera no bancaria autorizada como compañía financiera (LEF art. 24).",
    "Sujeto_caja_de_credito": "ES la entidad financiera «caja de crédito» de la Ley 25.782; no es la caja de crédito cooperativa (Ley 26.173), que tiene su propio id.",
    "Sujeto_caja_de_credito_cooperativa": "ES la cooperativa autorizada por el BCRA a operar como caja de crédito bajo la Ley 26.173.",
    "Sujeto_entidad_cambiaria": "ES la persona autorizada a operar en cambios sin ser entidad financiera (casas y agencias de cambio, operadores de cambio).",
    "Sujeto_proveedor_de_servicios_de_pago": "ES la persona jurídica que, sin ser entidad financiera, cumple funciones de provisión de servicios de pago en el sistema nacional de pagos (registro del BCRA).",
    "Sujeto_pspcp": "ES el PSP que ofrece cuentas de pago a sus clientes.",
    "Sujeto_psi_billetera_digital": "ES el PSP iniciador que presta el servicio de billetera digital.",
    "Sujeto_proveedor_no_financiero_de_credito": "ES la persona jurídica que, sin ser entidad financiera, oferta crédito al público de manera habitual (incluye mutuales, cooperativas y empresas emisoras de tarjetas).",
    "Sujeto_empresa_no_financiera_emisora_de_tarjetas": "ES el proveedor no financiero de crédito cuya operatoria es emitir tarjetas de crédito y/o compra.",
    "Sujeto_fiduciario_de_fideicomiso_financiero": "ES quien ejerce la fiducia de un fideicomiso financiero (una EF o una sociedad autorizada por la CNV); es distinto del fideicomiso mismo, que es una estructura.",
    "Sujeto_fideicomiso_financiero": "ES el fideicomiso (contrato/patrimonio) cuyos beneficiarios son titulares de títulos valores respaldados por los bienes fideicomitidos; no es su fiduciario.",
    "Sujeto_entidad_de_contraparte_central": "ES la infraestructura que se interpone como contraparte entre los participantes de un mercado (ECC/CCP); no es la cámara electrónica de compensación (CEC).",
    "Sujeto_miembro_compensador": "ES el participante que liquida y compensa a través de una entidad de contraparte central, por sí o por cuenta de terceros.",
    "Sujeto_cliente": "ES la unidad económica receptora de fondos de la entidad o titular de una garantía a su favor, residente o no.",
    "Sujeto_usuario_de_servicios_financieros": "ES la persona (humana o jurídica) destinataria final de un servicio financiero, en los términos de las normas de Protección de los usuarios.",
    "Sujeto_bcra": "ES el Banco Central de la República Argentina como autoridad. Las potestades de autorizar, reglamentar, fiscalizar o sancionar son SUYAS: se atribuyen a este id y nunca al sujeto regulado por la norma.",
    "Sujeto_sefyc": "ES la Superintendencia de Entidades Financieras y Cambiarias como órgano de supervisión (califica, inspecciona, sanciona).",
    # Def dirigida del laudo de cierre (H4a, cláusula F1.3): frontera reforzada.
    "Sujeto_sector_publico_no_financiero": "ES el conjunto Gobierno Nacional, provincias, municipios y CABA con sus entes controlados; NO incluye entidades financieras públicas (bancos públicos) ni entidades autorizadas a operar como entidades financieras.",
    "Sujeto_sector_privado_no_financiero": "ES el residente del sector privado que no es entidad financiera ni ente público.",
    "Sujeto_fondo_comun_de_inversion": "ES el fondo como vehículo de inversión; es distinto de su sociedad gerente y de su depositaria.",
    "Sujeto_empresa_de_servicios_complementarios": "ES la empresa no financiera del perímetro de la entidad dedicada a actividades complementarias admitidas (normas de Servicios complementarios).",
}

# ========================================================================== #
# Laudo F1.4 — ADICIONES (7). Cada una: línea de catálogo + def posicional.  #
# El campo `padre` es metadato para la integración documental futura (el     #
# bloque del prefijo agrupa por rama, no serializa padres).                  #
# ========================================================================== #

ADICIONES_V3: tuple[dict, ...] = (
    {"id": "Sujeto_entidad_girada", "nivel": "clase", "padre": "Sujeto_sujeto_regulado",
     "grupo": "## Sujetos regulados",
     "linea": "Sujeto_entidad_girada — Entidades giradas (alias: entidad girada, banco girado)",
     "def": "ES la entidad sobre la cual está girado el cheque u otro instrumento compensable, obligada a su pago o rechazo."},
    {"id": "Sujeto_entidad_depositaria", "nivel": "clase", "padre": "Sujeto_sujeto_regulado",
     "grupo": "## Sujetos regulados",
     "linea": "Sujeto_entidad_depositaria — Entidades depositarias (alias: entidad depositaria)",
     "def": "ES la entidad en la que se deposita el instrumento compensable y que lo presenta a la compensación."},
    # Rename del laudo de cierre (H1a, 06/09/2026): entidad_originante →
    # entidad_originante_de_transferencia; def y guarda INTACTAS, solo el id.
    {"id": "Sujeto_entidad_originante_de_transferencia", "nivel": "clase", "padre": "Sujeto_sujeto_regulado",
     "grupo": "## Sujetos regulados",
     "linea": "Sujeto_entidad_originante_de_transferencia — Entidades originantes (alias: entidad originante)",
     "def": "ES la entidad que origina o ingresa la transacción al esquema de pago (transferencias, débitos directos, DEBIN). NO es el originante de una securitización o fideicomiso: ese sujeto sigue en sujeto_propuesto."},
    {"id": "Sujeto_entidad_receptora", "nivel": "clase", "padre": "Sujeto_sujeto_regulado",
     "grupo": "## Sujetos regulados",
     "linea": "Sujeto_entidad_receptora — Entidades receptoras (alias: entidad receptora)",
     "def": "ES la entidad que recibe la transacción del esquema de pago con destino a cuentas de sus clientes."},
    {"id": "Sujeto_camara_electronica_de_compensacion", "nivel": "clase", "padre": "Sujeto_sujeto_regulado",
     "grupo": "## Sujetos regulados",
     "linea": "Sujeto_camara_electronica_de_compensacion — Cámaras electrónicas de compensación (CEC) (alias: CEC, cámaras compensadoras)",
     "def": "ES la cámara que compensa y liquida las posiciones entre entidades en el sistema nacional de pagos; no es la entidad de contraparte central (CCP)."},
    {"id": "Sujeto_banco_central_del_exterior", "nivel": "clase", "padre": "Sujeto_organismo_publico",
     "grupo": "## Organismos públicos (clases e instancias)",
     "linea": "Sujeto_banco_central_del_exterior — Bancos centrales del exterior (alias: bancos centrales de otros estados soberanos, Banco Central Europeo)",
     "def": "ES el banco central de otro estado soberano (incluido el Banco Central Europeo); no es el BCRA."},
    {"id": "Sujeto_fmi", "nivel": "instancia", "padre": "Sujeto_organismo_internacional",
     "grupo": "## Organismos públicos (clases e instancias)",
     "linea": "Sujeto_fmi — FMI (Fondo Monetario Internacional) (alias: Fondo Monetario Internacional) [instancia]",
     "def": None},
)

# ========================================================================== #
# Laudo F1.2 — 31 roles A2 + 35 mapeos a clase (tabla_to_rol_post_f1.md)     #
# ========================================================================== #

# (to, label del rol, miembros_labels). El id es Sujeto_rol_alcance_<to>; el
# archivo del TO en el corpus nuevo es <to>.pdf (campo `archivo` de E0).
ROLES_V3: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("adrei", "Entidades alcanzadas (Agregación de datos sobre riesgos: D-SIB)",
     ("Entidades financieras de importancia sistémica local (D-SIB)",)),
    ("autenf", "Autoridades comprendidas (Autoridades de entidades financieras)",
     ("Personas que ejercen cargos de administración, fiscalización o gerencia en entidades financieras",)),
    ("ccbcra", "Entidades alcanzadas (Cuentas a la vista en el BCRA)",
     ("Entidades financieras", "Cajas de crédito (Ley 25.782)", "Entidades cambiarias")),
    ("convca", "Entidades habilitadas (Conversión cambiaria)",
     ("Entidades financieras y otras habilitadas a conversión cambiaria",)),
    ("cryl", "Sujetos habilitados (CRyL)",
     ("Entidades financieras", "Mercados de Valores del país", "Fondos comunes de inversión",
      "Centrales depositarias de valores", "Cámaras electrónicas de compensación (CEC)")),
    ("ctacor", "Entidades intervinientes (Cuentas de corresponsalía)",
     ("Entidades financieras del país", "Casas de cambio (Sección 3)")),
    ("depaho", "Entidades intervinientes (Depósitos de ahorro)",
     ("Bancos comerciales de primer grado", "Compañías financieras", "Cajas de crédito",
      "Sociedades de ahorro y préstamo para la vivienda u otros inmuebles")),
    ("efemin", "Entidades alcanzadas (Efectivo mínimo)",
     ("Entidades financieras (filiales del país)",)),
    ("fabcra", "Entidades registrantes de firmas (Firmas autorizadas ante el BCRA)",
     ("Entidades financieras", "Operadores de cambio", "Cámaras electrónicas de compensación",
      "Cajas de valores", "Mercados", "Compañías financieras",
      "Agentes de liquidación y compensación", "Ministerio de Economía", "ANSES")),
    ("icmecma", "Sujetos alcanzados (Comunicación por medios electrónicos)",
     ("Entidades financieras", "Empresas no financieras emisoras de tarjetas de crédito y/o compra",
      "Fiduciarios de fideicomisos financieros",
      "Administradores de carteras crediticias de ex-entidades financieras",
      "Otros proveedores no financieros de crédito")),
    ("lavdin", "Entidades alcanzadas (Prevención del lavado de activos)",
     ("Entidades financieras", "Entidades cambiarias")),
    ("ordcom", "Destinatarios de Comunicaciones (Ordenamiento de Comunicaciones)",
     ("BCRA (emisor)", "Destinatarios de Comunicaciones (entidades financieras, cajas de crédito cooperativas, etc.)")),
    ("osapsa", "Sujetos alcanzados (Otros servicios y actividades)",
     ("Entidades financieras (Secciones 2, 4 y 5)",
      "Empresas no financieras emisoras de tarjetas (Secciones 3 y 5)",
      "Operadores de cambio y empresas de cobranzas extrabancarias (Sección 5)")),
    ("pagjub", "Entidades participantes (Pago de beneficios ANSES)",
     ("Entidades financieras participantes del pago de beneficios ANSES",)),
    ("pfmipyme", "Plataformas para el financiamiento MiPyME (PFM)",
     ("Plataformas para el financiamiento MiPyME (PFM)",)),
    ("pimf", "Infraestructuras del mercado financiero alcanzadas (PIMF)",
     ("Infraestructuras del mercado financiero (IMF) nominadas en la Sección 5",)),
    ("ratiofn", "Entidades alcanzadas (Ratio de fondeo neto estable: D-SIB y suc. G-SIB)",
     ("Entidades financieras D-SIB", "Sucursales o subsidiarias de bancos del exterior G-SIB")),
    ("rdbcra", "Personas sumariables (Régimen disciplinario del BCRA)",
     ("Personas jurídicas y humanas sometidas al ámbito de la Ley de Entidades Financieras",)),
    ("repefe", "Representantes de entidades financieras del exterior (Representantes)",
     ("Representantes de entidades financieras del exterior no autorizadas",)),
    ("retype", "Entidades bancarias participantes (Pago de retiros y pensiones militares)",
     ("Banco de la Nación Argentina", "Otros bancos públicos participantes (IAF)")),
    ("rmrtsd", "Sujetos obligados (Servicios financieros digitales)",
     ("Entidades financieras", "Proveedores de servicios de pago (PSP)")),
    ("rrci", "Sujetos alcanzados (Respuesta y recuperación ante ciberincidentes)",
     ("Entidades financieras", "PSP incluidos en el Registro del BCRA",
      "Infraestructuras del mercado financiero de importancia sistémica")),
    ("servco", "Entidades alcanzadas (Servicios complementarios)",
     ("Entidades financieras (Sección 2: bancos comerciales y compañías financieras)",)),
    ("snp_atm", "Entidades alcanzadas (SNP - Cajeros automáticos)",
     ("Entidades financieras que ofrezcan cuentas a la vista",
      "Empresas no financieras operadoras de cajeros automáticos")),
    # snp_cec NO está acá: su rol fue retirado por el mini-laudo del freno 2
    # (mapea a la clase Sujeto_camara_electronica_de_compensacion, abajo).
    ("snp_debin", "Entidades y PSPCP alcanzados (SNP - Débito Inmediato)",
     ("Entidades financieras", "PSPCP")),
    ("snp_psp", "Sujetos alcanzados (SNP - Proveedores de servicios de pago)",
     ("Proveedores de servicios de pago (PSP)", "Entidades financieras")),
    ("snp_spd", "Sujetos alcanzados (SNP - Servicios de pago)",
     ("Entidades financieras", "PSP (según el servicio)")),
    ("snp_tr_nc", "Sujetos alcanzados (SNP - Transferencias - Normas complementarias)",
     ("Entidades financieras", "Proveedores de servicios de pago (PSP)")),
    ("supcon", "Entidades y empresas alcanzadas (Supervisión consolidada)",
     ("Entidades financieras", "Empresas del perímetro de supervisión consolidada")),
    ("traval", "Sujetos comprendidos (Transportadoras de valores)",
     ("Transportadoras de valores (TV)", "Prestadoras de Servicios de Transporte de Valores (PSTV)",
      "Transportadoras de Valores Propias (TVP)")),
)

# to → (clase_ids, labels) para los 36 TOs cuyo alcance ES clase exacta
# (35 de la tabla del freno 1 + snp_cec por el mini-laudo del freno 2).
_EF = ("Sujeto_entidad_financiera",)
MAPEO_CLASE_V3: dict[str, tuple[str, ...]] = {
    "actgar": _EF, "adfsp": _EF, "afiltr": _EF,
    "apnf": ("Sujeto_proveedor_no_financiero_de_credito",),
    "ayccef": _EF,
    "cajasc": ("Sujeto_caja_de_credito_cooperativa",),
    "cescar": _EF, "coltit": _EF,
    "ctacte": ("Sujeto_banco",),
    "ctavis": ("Sujeto_caja_de_credito_cooperativa",),
    "depinv": _EF, "disres": _EF, "evacre": _EF, "expaef": _EF,
    "fclef": ("Sujeto_fideicomiso_financiero",),
    "fgarcp": ("Sujeto_fondo_de_garantia_publico",),
    "finsec": _EF, "gerc": _EF, "gescre": _EF, "gracre": _EF, "graloc": _EF,
    "incuca": _EF, "lingeef": _EF, "lingob": _EF, "opefci": _EF,
    "pognme": _EF, "polcre": _EF, "prevmi": _EF,
    "pscpp": ("Sujeto_pscpp",),
    "raapal": _EF, "relact": _EF,
    "ri2_ci": ("Sujeto_casa_de_cambio", "Sujeto_agencia_de_cambio"),
    "secfin": _EF,
    "snp_cec": ("Sujeto_camara_electronica_de_compensacion",),
    "socgar": ("Sujeto_sociedad_de_garantia_reciproca",),
    "tasint": _EF,
}

# Huecos del laudo F1.2: SIN entrada en ROL_POR_TO_V3 (válvula abierta).
HUECOS_SIN_ROL: tuple[str, ...] = ("docvig", "fimipyme")


def rol_id_de(to: str) -> str:
    return f"Sujeto_rol_alcance_{to}"


# ========================================================================== #
# Construcción del bloque de catálogo v3                                     #
# ========================================================================== #

def _label_de(catalogo_linea: str) -> str:
    return catalogo_linea.split(" — ", 1)[1]


def bloque_catalogo_congelado() -> str:
    """Extrae el bloque de catálogo del prefijo congelado por anclas únicas."""
    t = pcg.PREFIJO_SISTEMA_CONGELADO
    if hashlib.sha256(t.encode("utf-8")).hexdigest() != PREFIJO_SHA256_CONGELADO_ESPERADO:
        raise RuntimeError("candado: el prefijo congelado no es el sellado e69feaaa… — se frena")
    if pcg.PREFIJO_HASH_CONGELADO != PREFIJO_HASH_CONGELADO_ESPERADO:
        raise RuntimeError("candado: PREFIJO_HASH_CONGELADO != 1be8304e3d77 — se frena")
    for ancla in (ANCLA_INICIO_BLOQUE, ANCLA_FIN_BLOQUE):
        n = t.count(ancla)
        if n != 1:
            raise RuntimeError(f"ancla {ancla!r} aparece {n} veces (esperado 1) — se frena")
    i = t.index(ANCLA_INICIO_BLOQUE)
    k = t.index(ANCLA_FIN_BLOQUE)
    if not i < k:
        raise RuntimeError("anclas del bloque en orden inválido — se frena")
    return t[i:k]


def bloque_catalogo_v3() -> str:
    """Transforma el bloque congelado con los cuatro laudos, línea a línea y
    con assert de unicidad por edición. Función pura y determinística."""
    lineas = bloque_catalogo_congelado().rstrip("\n").split("\n")

    def _id_de(linea: str) -> str | None:
        if linea.startswith("Sujeto_") and " — " in linea:
            return linea.split(" — ", 1)[0]
        return None

    ids_presentes = [x for x in (_id_de(l) for l in lineas) if x]
    if len(ids_presentes) != len(set(ids_presentes)):
        raise RuntimeError("bloque congelado con ids duplicados — se frena")
    if len(ids_presentes) != 70:
        raise RuntimeError(f"bloque congelado con {len(ids_presentes)} ids (esperado 70) — se frena")

    # 1) Retiros (laudo F1.5) — cada id retirado debe estar exactamente una vez.
    for rid in RETIROS_V3:
        n = sum(1 for l in lineas if _id_de(l) == rid)
        if n != 1:
            raise RuntimeError(f"retiro {rid}: {n} líneas en el bloque (esperado 1) — se frena")
    lineas = [l for l in lineas if _id_de(l) not in RETIROS_V3]

    # 2) Definiciones dirigidas (laudo F1.3) — línea `  def:` bajo la entrada.
    salida: list[str] = []
    for l in lineas:
        salida.append(l)
        lid = _id_de(l)
        if lid in DEFINICIONES_V3:
            salida.append(f"  def: {DEFINICIONES_V3[lid]}")
    faltantes = set(DEFINICIONES_V3) - {x for x in (_id_de(l) for l in lineas) if x}
    if faltantes:
        raise RuntimeError(f"definiciones sin entrada en el bloque: {sorted(faltantes)} — se frena")
    lineas = salida

    # 3) Adiciones (laudo F1.4) — al final de su grupo (antes del heading
    #    siguiente), en el orden declarado.
    headings = [i for i, l in enumerate(lineas) if l.startswith("## ")]
    for ad in ADICIONES_V3:
        idxs = [i for i, l in enumerate(lineas) if l == ad["grupo"]]
        if len(idxs) != 1:
            raise RuntimeError(f"grupo {ad['grupo']!r}: {len(idxs)} headings — se frena")
        g = idxs[0]
        fin = next((i for i in range(g + 1, len(lineas)) if lineas[i].startswith("## ")), len(lineas))
        nuevas = [ad["linea"]] + ([f"  def: {ad['def']}"] if ad["def"] else [])
        lineas[fin:fin] = nuevas

    # 4) Roles A2 (laudo F1.2) — al final del bloque (sección de roles).
    if lineas[-1].startswith("Sujeto_rol_alcance_capmin — ") is False:
        raise RuntimeError("el bloque congelado no termina en el rol capmin — se frena")
    for to, label, _miembros in ROLES_V3:
        lineas.append(f"{rol_id_de(to)} — {label} [rol del TO {to}.pdf]")

    return "\n".join(lineas) + "\n"


def prefijo_sistema_v3() -> str:
    """Prefijo congelado con el bloque de catálogo v3 espliceado por ancla.
    Fuera del bloque: byte-idéntico (lo demuestra el selftest)."""
    t = pcg.PREFIJO_SISTEMA_CONGELADO
    viejo = bloque_catalogo_congelado()
    nuevo = bloque_catalogo_v3()
    n = t.count(viejo)
    if n != 1:
        raise RuntimeError(f"el bloque congelado aparece {n} veces en el prefijo (esperado 1) — se frena")
    return t.replace(viejo, nuevo)


PREFIJO_SISTEMA_V3 = prefijo_sistema_v3()
BLOQUE_CATALOGO_CONGELADO = bloque_catalogo_congelado()
BLOQUE_CATALOGO_V3 = bloque_catalogo_v3()

# ========================================================================== #
# Enum v3 y tool schema                                                      #
# ========================================================================== #

def sujetos_catalogo_v3() -> list[str]:
    """Orden del enum: el del congelado sin los retiros, luego las 7 adiciones
    (orden declarado), luego los 31 roles (orden de ROLES_V3, alfabético)."""
    base = [s for s in pcg.SUJETOS_CATALOGO if s not in RETIROS_V3]
    return base + [a["id"] for a in ADICIONES_V3] + [rol_id_de(to) for to, _, _ in ROLES_V3]


SUJETOS_CATALOGO_V3 = sujetos_catalogo_v3()

TOOL_SCHEMA_V3 = copy.deepcopy(pcg.TOOL_SCHEMA_CONGELADO)
_props_rel = TOOL_SCHEMA_V3["input_schema"]["properties"]["relations"]["items"]["properties"]
_props_rel["sujeto_id"]["enum"] = list(SUJETOS_CATALOGO_V3)
_props_rel["sujeto_propuesto_padre_sugerido"]["enum"] = list(SUJETOS_CATALOGO_V3)

# ========================================================================== #
# ROL_POR_TO_V3 — 5 dev (pass-through) + 66 nuevos                           #
# ========================================================================== #

_LABEL_POR_ID = {
    _id: _label_de(l).replace(" [instancia]", "")
    for l in (BLOQUE_CATALOGO_V3.split("\n"))
    if (l.startswith("Sujeto_") and " — " in l)
    for _id in [l.split(" — ", 1)[0]]
}


def _rol_por_to_v3() -> dict[str, dict]:
    tabla: dict[str, dict] = {}
    # (a) dev: pass-through byte-idéntico de producción.
    for archivo, rol in prompt_e1.ROL_POR_TO.items():
        tabla[archivo] = copy.deepcopy(rol)
    # (b) 31 roles nuevos.
    for to, label, miembros in ROLES_V3:
        tabla[f"{to}.pdf"] = {
            "rol_id": rol_id_de(to),
            "label": label,
            "miembros_ids": [],
            "miembros_labels": list(miembros),
        }
    # (c) 35 mapeos a clase.
    for to, clase_ids in MAPEO_CLASE_V3.items():
        tabla[f"{to}.pdf"] = {
            "rol_id": clase_ids[0] if len(clase_ids) == 1 else None,
            "clase_ids": list(clase_ids),
            "label": " / ".join(_LABEL_POR_ID[c].split(" (alias", 1)[0] for c in clase_ids),
            "miembros_ids": list(clase_ids),
            "miembros_labels": [_LABEL_POR_ID[c].split(" (alias", 1)[0] for c in clase_ids],
        }
    return tabla


ROL_POR_TO_V3 = _rol_por_to_v3()

# ========================================================================== #
# Mensaje de usuario v3 (mecanismo de rol por mensaje, patrón de producción) #
# ========================================================================== #

def build_user_message_v3(chunk: dict) -> str:
    """Producción (prompt_e1.build_user_message) con la tabla v3: para un TO
    dev el resultado es BYTE-IDÉNTICO al de producción (lo asserta el
    selftest); para un TO nuevo agrega la línea de alcance según su entrada
    v3 (rol o clase). docvig/fimipyme: sin entrada → sin línea (hueco F1.2).

    Implementación: se reconstruye el mensaje de producción SIN la línea de
    alcance y se re-inserta la línea según ROL_POR_TO_V3, reutilizando los
    helpers de producción (es_mini_chunk, puntos_admitidos, chunk_flaggeado)
    para no duplicar lógica frágil."""
    rol = ROL_POR_TO_V3.get(chunk["archivo"])
    if rol is None:
        return prompt_e1.build_user_message(chunk)
    if chunk["archivo"] in prompt_e1.ROL_POR_TO:
        # dev: producción ya emite la línea con la misma entrada.
        return prompt_e1.build_user_message(chunk)

    base = prompt_e1.build_user_message(chunk)  # sin línea de alcance (TO nuevo)
    if "Alcance de este TO:" in base:
        raise RuntimeError("TO nuevo con línea de alcance en producción — tabla inconsistente, se frena")
    miembros = ", ".join(rol["miembros_labels"])
    if rol.get("rol_id"):
        linea = (
            f"Alcance de este TO: {rol['rol_id']} = {{{miembros}}}. "
            f"Cuando la norma se dirija genéricamente a 'las entidades' / 'los sujetos obligados' / "
            f"el colectivo del TO, usá {rol['rol_id']} como sujeto. "
            f"Es el sujeto de aplica_a cuando la norma se dirige al colectivo; "
            f"NO es el ejecutor por defecto en ejecuta."
        )
    else:
        # Mapeo a DOS clases (ri2_ci): variante declarada de la línea.
        ids = " o ".join(rol["clase_ids"])
        linea = (
            f"Alcance de este TO: {{{miembros}}}. "
            f"Cuando la norma se dirija genéricamente a 'las entidades' / 'los sujetos obligados' / "
            f"el colectivo del TO, usá {ids} como sujeto, según corresponda. "
            f"Es el sujeto de aplica_a cuando la norma se dirige al colectivo; "
            f"NO es el ejecutor por defecto en ejecuta."
        )
    # Inserción en la MISMA posición que producción: tras la línea de
    # "Puntos admitidos" y su línea en blanco.
    marcador = "\n\n"
    idx = base.index(marcador, base.index("Puntos admitidos para `punto`:"))
    return base[:idx] + "\n\n" + linea + base[idx:]


def bloques_sistema_v3() -> list[dict]:
    """D1: system como bloque único con el breakpoint de caching."""
    return [
        {
            "type": "text",
            "text": PREFIJO_SISTEMA_V3,
            "cache_control": {"type": "ephemeral"},
        }
    ]


PREFIJO_CANONICO_V3 = json.dumps(
    {"system": bloques_sistema_v3(), "tools": [TOOL_SCHEMA_V3]},
    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
)
PREFIJO_HASH_V3 = hashlib.sha256(PREFIJO_CANONICO_V3.encode("utf-8")).hexdigest()[:12]
PREFIJO_SHA256_V3 = hashlib.sha256(PREFIJO_SISTEMA_V3.encode("utf-8")).hexdigest()


def build_request_kwargs_v3(chunk: dict, model: str,
                            max_tokens: int = MAX_OUTPUT_TOKENS) -> dict:
    """Request completo con el prefijo v3 (para la pareada de fase 3; el
    cableado a producción NO es de esta unidad)."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": bloques_sistema_v3(),
        "tools": [TOOL_SCHEMA_V3],
        "tool_choice": {"type": "tool", "name": NOMBRE_TOOL},
        "messages": [{"role": "user", "content": build_user_message_v3(chunk)}],
    }


__all__ = [
    "PREFIJO_SISTEMA_V3", "TOOL_SCHEMA_V3", "SUJETOS_CATALOGO_V3",
    "BLOQUE_CATALOGO_CONGELADO", "BLOQUE_CATALOGO_V3",
    "RETIROS_V3", "ADICIONES_V3", "ROLES_V3", "MAPEO_CLASE_V3",
    "DEFINICIONES_V3", "MARCADOS_REVISION_R2", "HUECOS_SIN_ROL",
    "ROL_POR_TO_V3", "rol_id_de", "build_user_message_v3",
    "bloques_sistema_v3", "build_request_kwargs_v3",
    "PREFIJO_HASH_V3", "PREFIJO_SHA256_V3", "PREFIJO_CANONICO_V3",
    "PREFIJO_SHA256_CONGELADO_ESPERADO", "PREFIJO_HASH_CONGELADO_ESPERADO",
    "MAX_OUTPUT_TOKENS", "NOMBRE_TOOL",
]
