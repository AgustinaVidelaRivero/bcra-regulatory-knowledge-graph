"""
mapping.py — Agregación modal y veredicto por pregunta del juez de fidelidad EV2.

Implementa en código, de forma determinística y testeable, los §2 y §4 del
pre-registro (docs/preregistro_evaluacion_fidelidad_ev2.md, commit be8a84f):

  §4 — N repeticiones por par (respuesta, criterio) → veredicto MODAL;
       sin mayoría estricta → "sin_consenso".
  §2 — sobre los veredictos modales por criterio:
       - todos "cumplido"                         → "correcto"
       - cero "cumplido"                          → "incorrecto"
       - mezcla                                   → "parcial"
       - cualquier "dudoso" o "sin_consenso"      → "requiere_adjudicacion"
         (el veredicto lo pone la adjudicación humana, no este mapping)

El LLM solo clasifica pares; el veredicto por pregunta sale de acá.
"""

from __future__ import annotations

from collections import Counter

VEREDICTOS_CRITERIO = ("cumplido", "no_cumplido", "dudoso")
VEREDICTOS_MODALES = VEREDICTOS_CRITERIO + ("sin_consenso",)
VEREDICTOS_PREGUNTA = ("correcto", "parcial", "incorrecto", "requiere_adjudicacion")


def veredicto_modal(reps: list[str]) -> str:
    """Moda de los veredictos de las N repeticiones de UN par (respuesta, criterio).
    Mayoría estricta (> N/2) o "sin_consenso"; con N=3 eso es 2-de-3."""
    if not reps:
        raise ValueError("lista de repeticiones vacía")
    for v in reps:
        if v not in VEREDICTOS_CRITERIO:
            raise ValueError(f"veredicto de criterio inválido: {v!r}")
    valor, n = Counter(reps).most_common(1)[0]
    return valor if n > len(reps) / 2 else "sin_consenso"


def veredicto_pregunta(modales: list[str]) -> str:
    """Mapping fijo §2 sobre los veredictos modales de TODOS los criterios de la
    pregunta. La regla de adjudicación tiene precedencia sobre las otras tres."""
    if not modales:
        raise ValueError("lista de veredictos modales vacía")
    for v in modales:
        if v not in VEREDICTOS_MODALES:
            raise ValueError(f"veredicto modal inválido: {v!r}")
    if any(v in ("dudoso", "sin_consenso") for v in modales):
        return "requiere_adjudicacion"
    if all(v == "cumplido" for v in modales):
        return "correcto"
    if all(v == "no_cumplido" for v in modales):
        return "incorrecto"
    return "parcial"
