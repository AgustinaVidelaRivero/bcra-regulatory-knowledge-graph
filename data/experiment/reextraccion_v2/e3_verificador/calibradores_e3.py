"""
calibradores_e3.py — Ejemplos RESUELTOS que calibran al verificador E3.

Hallazgo H12 del proyecto (docs/hallazgos_tesis.md): los jueces LLM honran
calibradores con ejemplos resueltos y circunvalan reglas declarativas
equivalentes. Por eso el prompt de E3 se calibra con casos del backlog
(especificación ejecutable del pipeline, diseño §5) y no solo con reglas.

Cuatro calibradores (diseño §3-E3), cada uno con fuente + extracción +
veredicto correcto + porqué:

  1. calificador_despojado — BKL-0005 / corrección C7 (RegInf 7.1): la
     enumeración del esquema "Posición mes n" perdió dos calificadores en la
     extracción v2 histórica. La extracción del ejemplo reproduce la
     `descripcion` ANTES laudada (data/backlog/retests/C7_retest_2026-08-03.md).
  2. excepcion_ausente — BKL-0003 / corrección C6 (Protección 1.1.2.5): la
     salvedad "excepto ... asociaciones mutuales o cooperativas" ausente del
     grafo v2/v3, restaurada a mano como C6. La extracción del ejemplo
     reproduce esa amputación histórica.
  3. enumeracion_incompleta — BKL-0004 / corrección C5 (Clasificación 6.5):
     la cláusula que ordena la enumeración de los cinco niveles ("Cada
     cliente ... se incluirá en una de las siguientes cinco categorías")
     ausente del grafo, restaurada a mano como C5. En E0 v2 esa cláusula viaja
     como intro heredado del 6.5: el ejemplo muestra una extracción que
     representa todo lo demás y la omite.
  4. completo_ok — contraejemplo resuelto: la extracción REAL de la
     calibración E1 fase B para pro::1.1.2.5, que SÍ capturó la salvedad de
     BKL-0003 (nodo Excepcion + exceptua_obligacion). Par mínimo con el
     calibrador 2: misma fuente, extracción completa.

Los textos fuente salen de la salida sellada de E0 y la extracción real del
calibrador 4 de la salida sellada de E1 fase B: los verbatims no se duplican
a mano donde existe el dato. Las extracciones amputadas (1-3) son literales
construidos aquí, con la amputación exacta documentada en el backlog.

ENMIENDA 01 — render CONGELADO: estos calibradores forman parte del PREFIJO
cacheado de E3, cuya calidad se midió en la calibración sellada (detección
gold 8/8, prefijo_hash_e3 en resumen_faseB_e3.json). La enmienda cambió
comun_e3.fuente_integro (el blanco del hijo pasa al texto propio), pero el
prompt del verificador NO cambia (§5 de la enmienda): el fuente de los
calibradores se renderiza acá con `_fuente_estilo_calibracion`, la réplica
byte a byte del fuente_integro vigente durante la calibración (herencia
completa + texto propio). El selftest verifica que PREFIJO_HASH quede
idéntico al sellado. El ejemplo CAL-3 sigue siendo pedagógicamente válido:
enseña que todo contenido normativo DEL FUENTE RECIBIDO debe estar
representado — exactamente la regla que el verificador aplica, cualquiera sea
el recorte del fuente que reciba por unidad.
"""

from __future__ import annotations

import comun_e3
from comun_e3 import cargar_chunks, cargar_extracciones_faseB


def _fuente_estilo_calibracion(chunk: dict) -> str:
    """Réplica CONGELADA del comun_e3.fuente_integro vigente en la
    calibración sellada de E3 (herencia estructural completa, con rótulos,
    + texto propio). No seguir a comun_e3: cambiarla rotaría el prefijo."""
    partes: list[str] = []
    for h in chunk.get("herencia", []):
        partes.append(f"[{h['tipo']} | punto {h['unidad_origen']}]")
        partes.append(h["texto"])
    partes.append(f"[texto propio | punto {chunk['unidad']}]")
    partes.append(chunk["texto"])
    return "\n".join(partes)


def _ent(local_id: str, type_: str, label: str, punto: str, **props) -> dict:
    return {"local_id": local_id, "type": type_, "label": label,
            "properties": {k: v for k, v in props.items()},
            "provenance": {"punto": punto}}


def _rel(source, target, predicate, punto, sujeto_id=None, sujeto_propuesto=None) -> dict:
    return {"source": source, "target": target, "predicate": predicate,
            "sujeto_id": sujeto_id, "sujeto_propuesto": sujeto_propuesto,
            "sujeto_propuesto_padre_sugerido": None,
            "provenance": {"punto": punto}}


def construir_calibradores() -> list[dict]:
    chunks = {c["id"]: c for c in cargar_chunks(("cla", "pro", "ric"))}
    regs = cargar_extracciones_faseB()

    calibradores: list[dict] = []

    # ------------------------------------------------------------------ #
    # 1. calificador_despojado — BKL-0005 / C7 (ric::7.1)                #
    # ------------------------------------------------------------------ #
    ch_ric = chunks["ric::7.1"]
    extr_1 = {
        "entidades": [
            _ent("to", "TextoOrdenado", "Régimen Informativo Contable Mensual", "7.1",
                 materia="Régimen informativo contable mensual",
                 archivo=ch_ric["archivo"], version="actual"),
            _ent("e1", "Obligacion", "Informar importes por franquicias — códigos 60100000-61100000", "7.1",
                 descripcion=("En los códigos 60100000 a 61100000 se incluirán los importes que "
                              "surjan como consecuencia de la aplicación de franquicias otorgadas "
                              "por el BCRA, consignándose, además, el número y fecha de Resolución "
                              "a través de la cual se la otorgó o el número de nota y fecha mediante "
                              "la cual se comunicó tal decisión."),
                 tipo="presentacion_informativa"),
            _ent("e2", "Obligacion", "Descripción detallada del cálculo de la franquicia", "7.1",
                 descripcion=("También se agregará una descripción detallada del cálculo de la "
                              "franquicia para el período informado, a partir de lo dispuesto en la "
                              "Resolución o nota a que se hace referencia en el párrafo anterior."),
                 tipo="presentacion_informativa"),
            # ANTES laudado de C7: la descripcion amputada que vivió en el grafo
            # (perdió "informada en el mes n" de la RPC y "calculada según datos
            # del mes n" de la Franquicia).
            _ent("e3", "Obligacion", "Aplicar esquema de cálculo para disminución de exigencia", "7.1",
                 descripcion=("Para el cálculo del importe correspondiente al mes n procederá "
                              "tenerse en cuenta el siguiente esquema: Datos exigencia riesgo de "
                              "crédito del mes n (incluyendo INC), Exigencia por riesgo de mercado "
                              "del último día del mes n, Exigencia por riesgo operacional del mes n, "
                              "Responsabilidad Patrimonial Computable, Franquicia informada en el mes n"),
                 tipo="calculo"),
        ],
        "relaciones": [
            _rel("e1", "to", "establecida_en", "7.1"),
            _rel("e2", "to", "establecida_en", "7.1"),
            _rel("e3", "to", "establecida_en", "7.1"),
        ],
        "omisiones_no_prosa": [],
    }
    calibradores.append({
        "id": "CAL-1",
        "titulo": "calificador_despojado — enumeración con renglones despojados de sus calificadores",
        "chunk_id": "ric::7.1",
        "fuente": _fuente_estilo_calibracion(ch_ric),
        "extraccion": extr_1,
        "veredicto": {
            "veredicto": "faltantes_detectados",
            "faltantes": [
                {"tipo": "calificador_despojado",
                 "cita_textual_del_fuente": "Responsabilidad Patrimonial Computable informada en el mes n",
                 "ubicacion": "7.1",
                 "severidad": "alta",
                 "nota": ("la extracción dice solo 'Responsabilidad Patrimonial Computable': "
                          "perdió el calificador que fija DE QUÉ MES es la RPC del esquema")},
                {"tipo": "calificador_despojado",
                 "cita_textual_del_fuente": "Franquicia informada en el mes n calculada según datos del mes n",
                 "ubicacion": "7.1",
                 "severidad": "alta",
                 "nota": ("la extracción conserva 'Franquicia informada en el mes n' pero perdió "
                          "'calculada según datos del mes n': el renglón quedó a medias")},
            ],
        },
        "porque": (
            "Caso real del backlog (BKL-0005, especie amputacion; corregido a mano como C7). "
            "El punto 7.1 está presente y el esquema también, pero dos renglones perdieron sus "
            "calificadores temporales. Sin ellos la norma no puede responder '¿de qué mes es la "
            "RPC que entra al cálculo?'. Notá que la amputación sobrevivió a un extractor que "
            "tenía el texto completo a la vista: por eso el veredicto exige comparar renglón por "
            "renglón la enumeración del fuente contra la descripcion extraída. Cada faltante "
            "cita el renglón ÍNTEGRO del fuente, no una paráfrasis."
        ),
    })

    # ------------------------------------------------------------------ #
    # 2. excepcion_ausente — BKL-0003 / C6 (pro::1.1.2.5)                 #
    # ------------------------------------------------------------------ #
    ch_pro = chunks["pro::1.1.2.5"]
    extr_2 = {
        "entidades": [
            _ent("to", "TextoOrdenado", "Protección de usuarios servicios financieros", "1.1.2.5",
                 materia="Protección de usuarios de servicios financieros",
                 archivo=ch_pro["archivo"], version="actual"),
            # Amputación histórica de BKL-0003: el alcance sin la salvedad.
            _ent("e1", "Obligacion", "Alcance Otros PNFC — financiaciones que otorguen", "1.1.2.5",
                 descripcion=("Otros proveedores no financieros de crédito alcanzados por las "
                              "normas sobre 'Proveedores no financieros de crédito', por las "
                              "financiaciones que otorguen."),
                 tipo="otra"),
        ],
        "relaciones": [
            _rel("e1", "to", "establecida_en", "1.1.2.5"),
            _rel("e1", None, "aplica_a", "1.1.2.5",
                 sujeto_id="Sujeto_proveedor_no_financiero_de_credito"),
        ],
        "omisiones_no_prosa": [],
    }
    calibradores.append({
        "id": "CAL-2",
        "titulo": "excepcion_ausente — salvedad del alcance no representada",
        "chunk_id": "pro::1.1.2.5",
        "fuente": _fuente_estilo_calibracion(ch_pro),
        "extraccion": extr_2,
        "veredicto": {
            "veredicto": "faltantes_detectados",
            "faltantes": [
                {"tipo": "excepcion_ausente",
                 "cita_textual_del_fuente": "excepto que se trate de asociaciones mutuales o cooperativas",
                 "ubicacion": "1.1.2.5",
                 "severidad": "alta",
                 "nota": ("la salvedad recorta QUIÉNES quedan alcanzados por el punto; sin ella "
                          "el grafo afirma un alcance más amplio que el de la norma")},
            ],
        },
        "porque": (
            "Caso real del backlog (BKL-0003, especie ausencia; corregido a mano como C6). La "
            "extracción representa la obligación de alcance pero su descripcion omite el "
            "'excepto ...' del fuente, y no existe ningún nodo Excepcion que lo porte. Una "
            "salvedad ausente no es un matiz de redacción: invierte la respuesta para toda la "
            "clase exceptuada (las mutuales y cooperativas SÍ quedan afuera y el grafo decía "
            "que no). La captura correcta esperada es la del calibrador 4 (misma fuente): la "
            "salvedad presente en la descripcion Y como nodo Excepcion con exceptua_obligacion."
        ),
    })

    # ------------------------------------------------------------------ #
    # 3. enumeracion_incompleta — BKL-0004 / C5 (cla::6.5.1.1)            #
    # ------------------------------------------------------------------ #
    ch_cla = chunks["cla::6.5.1.1"]
    extr_3 = {
        "entidades": [
            _ent("to", "TextoOrdenado", "Clasificación de Deudores", "6.5.1.1",
                 materia="Clasificación de deudores",
                 archivo=ch_cla["archivo"], version="actual"),
            _ent("e1", "Obligacion", "Criterios situación normal — liquidez y capacidad de pago", "6.5.1.1",
                 descripcion=("presente una situación financiera líquida, con bajo nivel y adecuada "
                              "estructura de endeudamiento en relación con su capacidad de ganancia, "
                              "y muestre una alta capacidad de pago de las deudas (capital e "
                              "intereses) en las condiciones pactadas generando fondos -medido a "
                              "través del análisis de su flujo- en grado aceptable. El flujo de "
                              "fondos no es susceptible de variaciones significativas ante "
                              "modificaciones importantes en el comportamiento de las variables "
                              "tanto propias como vinculadas a su sector de actividad."),
                 tipo="otra"),
            _ent("e2", "Obligacion", "Considerar grupo de contrapartes conectadas — análisis", "6.5.1.1",
                 descripcion=("En el análisis que se lleve a cabo deberá tenerse en cuenta, de "
                              "corresponder, la eventual incidencia que en su capacidad de pago "
                              "pueda tener la situación en la que se encuentran los demás "
                              "integrantes del grupo de contrapartes conectadas al cual pertenece."),
                 tipo="calculo"),
            _ent("e3", "Obligacion", "Definición situación normal — flujo de fondos", "6.5.1",
                 descripcion=("El análisis del flujo de fondos del cliente demuestra que es capaz "
                              "de atender adecuadamente todos sus compromisos financieros."),
                 tipo="otra"),
            _ent("e4", "Obligacion", "Clasificación por flujo proyectado — clientes sin asistencia", "6.5",
                 descripcion=("Los clientes que no registren asistencia crediticia de la entidad y "
                              "que posteriormente reciban financiaciones de ésta que no superen el "
                              "importe resultante de aplicar sobre el saldo de deuda registrado en "
                              "el sistema financiero, según la última información disponible en la "
                              "'Central de deudores' a la fecha de su otorgamiento, el porcentaje "
                              "establecido en el punto 2.2.5. de las normas sobre 'Previsiones "
                              "mínimas por riesgo de incobrabilidad' correspondiente a la peor "
                              "clasificación asignada, podrán ser clasificados por la entidad "
                              "teniendo en cuenta únicamente el análisis del flujo de fondos "
                              "proyectado. Las asistencias así otorgadas no serán consideradas a "
                              "los fines a que se refiere el punto 6.6."),
                 tipo="asignacion"),
            _ent("e5", "Restriccion", "Facilidades adicionales no consideradas refinanciaciones — condiciones", "6.5",
                 descripcion=("A fin de verificar el cumplimiento de las obligaciones sin recurrir "
                              "a nueva financiación directa o indirecta o a refinanciaciones, no se "
                              "considerarán refinanciaciones las facilidades adicionales que se "
                              "otorguen respecto de los márgenes vigentes acordados, siempre que el "
                              "nuevo apoyo crediticio implique nuevos desembolsos de fondos y no "
                              "supere el 10 % del cupo asignado en oportunidad de la última "
                              "evaluación crediticia del cliente, en la medida en que éstas sean "
                              "consistentes con el curso normal de los negocios y exista capacidad "
                              "para atender el resto de las obligaciones financieras, ni las nuevas "
                              "financiaciones y las refinanciaciones asociadas a una mayor inversión "
                              "derivada de la expansión de las actividades, y siempre que pueda "
                              "demostrarse que el flujo de fondos proyectado permitirá afrontar la "
                              "totalidad de sus obligaciones."),
                 tipo="limite_cualitativo"),
            _ent("e6", "Restriccion", "Emergencia agropecuaria — refinanciaciones y clasificación", "6.5",
                 descripcion=("Tampoco se considerarán dentro de ese concepto las refinanciaciones "
                              "otorgadas a los productores agropecuarios cuando ello resulte de la "
                              "aplicación de disposiciones vinculadas a la Ley de Emergencia "
                              "Agropecuaria, sin perjuicio de lo cual, a los fines de la "
                              "clasificación, deberá tenerse en cuenta el flujo de fondos "
                              "proyectado para el momento en que concluya la vigencia de la "
                              "emergencia declarada. El tratamiento que se dispense en ese marco "
                              "no podrá implicar mejoramiento de la clasificación asignada al "
                              "cliente en función de su situación individual, preexistente a la "
                              "emergencia, ni su aplicación extenderse más allá de la vigencia "
                              "fijada para ella."),
                 tipo="prohibicion"),
        ],
        "relaciones": [
            _rel("e1", "to", "establecida_en", "6.5.1.1"),
            _rel("e2", "to", "establecida_en", "6.5.1.1"),
            _rel("e3", "to", "establecida_en", "6.5.1"),
            _rel("e4", "to", "establecida_en", "6.5"),
            _rel("e5", "to", "establecida_en", "6.5"),
            _rel("e6", "to", "establecida_en", "6.5"),
        ],
        "omisiones_no_prosa": [],
    }
    calibradores.append({
        "id": "CAL-3",
        "titulo": "enumeracion_incompleta — la cláusula que ordena la enumeración quedó afuera",
        "chunk_id": "cla::6.5.1.1",
        "fuente": _fuente_estilo_calibracion(ch_cla),
        "extraccion": extr_3,
        "veredicto": {
            "veredicto": "faltantes_detectados",
            "faltantes": [
                {"tipo": "enumeracion_incompleta",
                 "cita_textual_del_fuente": ("Cada cliente, y la totalidad de sus financiaciones "
                                             "comprendidas, se incluirá en una de las siguientes "
                                             "cinco categorías, las que se definen teniendo en "
                                             "cuenta las condiciones que se detallan en cada caso."),
                 "ubicacion": "6.5 (intro heredado)",
                 "severidad": "alta",
                 "nota": ("la extracción representa los criterios del punto propio y varias normas "
                          "del intro heredado, pero la cláusula que ORDENA la clasificación en "
                          "cinco categorías no está en ninguna descripcion ni entidad")},
            ],
        },
        "porque": (
            "Caso real del backlog (BKL-0004, especie ausencia; corregido a mano como C5). El "
            "encabezado del 6.5 enuncia la obligación troncal —todo cliente se incluye en una de "
            "cinco categorías— y esa cláusula viaja en el chunk como contexto heredado (intro del "
            "6.5). El contexto heredado NO es decorado: si enuncia una norma, debe estar "
            "representado, anclado a su unidad de origen. Sin ella el grafo conoce los criterios "
            "de cada nivel pero no puede responder cuáles son los niveles de clasificación. "
            "Observá también qué NO se marca: los demás párrafos del intro 6.5 SÍ están "
            "representados (e4-e6), y los encabezados puros ('6.5. Niveles de clasificación.') "
            "no son faltante: son jerarquía documental, no contenido normativo."
        ),
    })

    # ------------------------------------------------------------------ #
    # 4. completo_ok — la extracción REAL v2 de pro::1.1.2.5 (fase B)     #
    # ------------------------------------------------------------------ #
    val_real = regs["pro::1.1.2.5"]["validacion"]
    extr_4 = {
        "entidades": val_real["entidades"],
        "relaciones": val_real["relaciones"],
        "omisiones_no_prosa": val_real["omisiones_no_prosa"],
    }
    calibradores.append({
        "id": "CAL-4",
        "titulo": "completo_ok — misma fuente que el calibrador 2, extracción completa",
        "chunk_id": "pro::1.1.2.5",
        "fuente": _fuente_estilo_calibracion(ch_pro),
        "extraccion": extr_4,
        "veredicto": {"veredicto": "completo_ok", "faltantes": []},
        "porque": (
            "Contraejemplo resuelto, par mínimo del calibrador 2: misma fuente, y esta vez la "
            "salvedad está representada DOS veces — dentro de la descripcion de la obligación de "
            "alcance ('... excepto que se trate de asociaciones mutuales o cooperativas ...') y "
            "como nodo Excepcion conectado por exceptua_obligacion. Los encabezados heredados "
            "('Sección 1. Disposiciones generales.', '1.1. Partes.', '1.1.2. Sujetos obligados.') "
            "no exigen representación: son jerarquía documental sin contenido normativo propio. "
            "Que los labels sean cortos NO es amputación: el contenido vive en descripcion. "
            "Veredicto: completo_ok con faltantes vacío."
        ),
    })

    return calibradores
