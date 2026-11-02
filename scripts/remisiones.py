"""Reconocimiento de la remisión entre puntos en sus dos formas (U-R2-CODIGO,
R5; enmienda 1 al mandato, R5.a; enmienda 2 de L-ESQ-R2, firmada en 5f9a731).

- Con el perfil r2, la remisión es la arista `remite_a`, con `alcance`,
  `destino` y `evidencia`, sin `rol_fuente`.
- Con los perfiles existentes (grafos sellados), es la arista `referencia` con
  `rol_fuente = referencia_cruzada`.

La usan scripts/regression_kg.py, el perfil r2 de scripts/shapes_validator.py
y scripts/muestra_aristas_obs12.py. Solo stdlib, sin dependencias del
pipeline: importarla no carga nada más.
"""

from __future__ import annotations

PREDICADO_REMISION = "remite_a"
PREDICADO_REFERENCIA = "referencia"
ROL_FUENTE_REFERENCIA_CRUZADA = "referencia_cruzada"

# Enmienda 2 de L-ESQ-R2, §2 y §3: firma (56 = 7 × 7 + 7) y alcance.
TIPOS_CONTENIDO = ("Operacion", "Restriccion", "Excepcion", "Obligacion", "Potestad", "Condicion", "Definicion")
TIPO_TEXTO_ORDENADO = "TextoOrdenado"
ALCANCES = ("interna", "externa", "to_entero")
PROPIEDADES_REMITE_A = ("alcance", "destino", "evidencia")


def es_remision(e: dict) -> bool:
    """La arista es una remisión entre puntos, en cualquiera de las dos formas."""
    rel = e.get("relation")
    return rel == PREDICADO_REMISION or (
        rel == PREDICADO_REFERENCIA and e.get("rol_fuente") == ROL_FUENTE_REFERENCIA_CRUZADA)


def forma_remision(e: dict) -> str | None:
    """«remite_a», «referencia» (con rol_fuente referencia_cruzada) o None."""
    if not es_remision(e):
        return None
    return PREDICADO_REMISION if e.get("relation") == PREDICADO_REMISION else PREDICADO_REFERENCIA


def firma_remite_a_ok(tipo_origen: str | None, tipo_destino: str | None) -> bool:
    """La firma de `remite_a`: origen en los siete tipos de contenido; destino en
    esos siete o TextoOrdenado."""
    return tipo_origen in TIPOS_CONTENIDO and (tipo_destino in TIPOS_CONTENIDO or tipo_destino == TIPO_TEXTO_ORDENADO)


def destino(e: dict) -> str | None:
    return (e.get("properties") or {}).get("destino")


def evidencia(e: dict) -> str | None:
    return (e.get("properties") or {}).get("evidencia")


def alcance_esperado(destino_codigo: str | None, to_procedencia: str | None, destino_es_texto_ordenado: bool) -> str | None:
    """`to_entero` si el destino es un TextoOrdenado; si no, `interna` cuando la
    unidad citada es del mismo TO que la procedencia y `externa` cuando es de
    otro (enmienda 2, §3). None si falta el destino o el TO de la procedencia."""
    if destino_es_texto_ordenado:
        return "to_entero"
    if not destino_codigo or "::" not in destino_codigo or not to_procedencia:
        return None
    return "interna" if destino_codigo.split("::", 1)[0] == to_procedencia else "externa"
