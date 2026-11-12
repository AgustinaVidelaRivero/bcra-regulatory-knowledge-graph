"""
generar_fixtures_e3.py — Genera fixtures/fixtures_e3.json para el selftest (T4).

Determinístico y offline: los datos salen de la salida sellada de E0 y de la
calibración E1 fase B (solo lectura). La amputación es quirúrgica y declarada:

  - AMPUTADA: la extracción REAL aceptada de pro::2.3.1.2 (Contratos
    multiproducto) con UN calificador eliminado a mano de la descripcion de la
    Restriccion e2: "cuando el sujeto obligado así lo disponga" — el
    calificador que vuelve facultativa (del sujeto obligado) la pérdida de
    beneficios por revocación. Especie calificador_despojado de manual.
  - COMPLETA: la extracción real aceptada de pro::1.1.1, sin tocar.
  - Veredictos stub enlatados (lo que devolvería el verificador) para
    ejercitar el flujo del mini-ratchet sin ninguna llamada a API: detección,
    reintento aceptado, tope agotado → cola humana, veredicto incoherente y
    veredicto con cita fabricada.

Uso:  python3 generar_fixtures_e3.py    (escribe fixtures/fixtures_e3.json)
"""

from __future__ import annotations

import copy
import json

import comun_e3
from comun_e3 import BASE, cargar_extracciones_faseB

CALIFICADOR = "cuando el sujeto obligado así lo disponga"


def main() -> None:
    regs = cargar_extracciones_faseB()

    # --- Amputada: pro::2.3.1.2 sin el calificador facultativo ----------- #
    reg = regs["pro::2.3.1.2"]
    val_amputada = copy.deepcopy(reg["validacion"])
    e2 = next(e for e in val_amputada["entidades"] if e["local_id"] == "e2")
    desc = e2["properties"]["descripcion"]
    assert CALIFICADOR in desc, f"el calificador esperado no está en la descripcion real: {desc!r}"
    e2["properties"]["descripcion"] = desc.replace(f"{CALIFICADOR}, ", "").replace(CALIFICADOR, "")
    assert CALIFICADOR not in e2["properties"]["descripcion"]

    veredicto_faltante = {
        "veredicto": "faltantes_detectados",
        "faltantes": [
            {"tipo": "calificador_despojado",
             "cita_textual_del_fuente": CALIFICADOR,
             "ubicacion": "2.3.1.2",
             "severidad": "alta",
             "nota": ("la restricción extraída presenta la pérdida de beneficios como "
                      "efecto directo de la revocación; el fuente la condiciona a que el "
                      "sujeto obligado así lo disponga (facultad, no automatismo)")},
        ],
    }

    fixtures = {
        "amputada": {
            "chunk_id": "pro::2.3.1.2",
            "calificador_eliminado": CALIFICADOR,
            "validacion_amputada": val_amputada,
            "veredicto_stub_faltante": veredicto_faltante,
            # Lo que el extractor stub devuelve en el reintento: su extracción
            # REAL de fase B (que sí contiene el calificador).
            "tool_input_reintento": reg["tool_input_crudo"],
            "veredicto_stub_ok": {"veredicto": "completo_ok", "faltantes": []},
        },
        "completa": {
            "chunk_id": "pro::1.1.1",
            "validacion": regs["pro::1.1.1"]["validacion"],
            "veredicto_stub_ok": {"veredicto": "completo_ok", "faltantes": []},
        },
        "veredicto_incoherente": {
            "veredicto": "completo_ok",
            "faltantes": [
                {"tipo": "otro", "cita_textual_del_fuente": CALIFICADOR,
                 "ubicacion": "2.3.1.2", "severidad": "baja"},
            ],
        },
        "veredicto_cita_inventada": {
            "veredicto": "faltantes_detectados",
            "faltantes": [
                {"tipo": "calificador_despojado",
                 "cita_textual_del_fuente": "los sujetos obligados presentarán una declaración jurada trimestral",
                 "ubicacion": "2.3.1.2",
                 "severidad": "alta"},
            ],
        },
    }

    out = BASE / "fixtures" / "fixtures_e3.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(fixtures, f, ensure_ascii=False, indent=1)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
