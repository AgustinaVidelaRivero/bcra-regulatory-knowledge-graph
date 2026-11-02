# Pre-registro: método de evaluación del eje de fidelidad de EV2

Cierra la pregunta abierta §8.c de `docs/diseno_ev2.md`, según el régimen del
§6 de `docs/protocolo_corrida_ev2.md`: redactado DESPUÉS de la corrida del
agente (commit bb89a8e, 456 trazas) y ANTES de evaluar respuesta alguna.

**Declaración de ceguera:** al momento de sellar este documento no se computó
la métrica de navegabilidad ni se leyó ninguna de las 120 respuestas de
fidelidad persistidas. La elección del método no pudo mirar ni respuestas ni
resultados parciales de ningún eje.

**Laudos registrados (2026-08-14):** modelo del juez, mapping de veredicto,
régimen de adjudicación y criterio de frenado de calibración, laudados por la
autora según se fija abajo. Este documento se sella por commit; toda
modificación posterior es enmienda separada, jamás ajuste silencioso.

## 1. Instrumento

Juez LLM + veredicto computado en código. El juez es un instrumento de
medición separado del verificador causal del proyecto (roles no se mezclan).

- **Modelo:** claude-sonnet-4-6 (verificador histórico del proyecto).
- **Unidad de juicio:** el par (respuesta, criterio). Para cada uno de los
  criterios de la pregunta (164 en total sobre 40 preguntas), el juez
  clasifica: `cumplido` / `no_cumplido` / `dudoso`, citando el fragmento de
  la respuesta que sostiene la clasificación. El juez recibe: pregunta,
  respuesta final del agente, y los criterios con sus citas textuales del
  gold sellado. Nada más.
- **Clasificación auxiliar** (no entra al veredicto): la respuesta es
  `abstencion` (declara no encontrar información) o `contenido`. Se persiste
  para el análisis grounded≠correct.

## 2. Veredicto por pregunta (código, mapping fijo)

Sobre los veredictos modales por criterio (§4):
- todos `cumplido` → **correcto**
- cero `cumplido` → **incorrecto**
- mezcla → **parcial**
- cualquier criterio `dudoso` o `sin_consenso` → la pregunta se marca
  **requiere_adjudicacion** (el veredicto lo pone la adjudicación humana, no
  el mapping).

El mapping vive en código versionado, con tests de respuesta conocida.

## 3. Ceguera de grafo y orden

El input del juez NO contiene el grafo de origen, label, ni metadata que lo
identifique. Las 120 respuestas se evalúan en orden aleatorizado único:
`random.Random("juez-ev2-v1").shuffle` sobre la lista ordenada por
(id_pregunta, hash de la respuesta).

## 4. No-determinismo del juez

N=3 por par (respuesta, criterio), veredicto **modal**; sin mayoría →
`sin_consenso`. Cada repetición corre bajo label propio con db de caché
propia (patrón rt_c6_n3); el reporte verifica y declara 0 cross-hits entre
repeticiones. La distribución completa (3 veredictos por par) se persiste.

## 5. Calibración (antes de ver respuesta alguna de EV2)

- **Fuente exclusiva:** las 25 preguntas de U6 ya adjudicadas humanamente
  (respuestas reales del mismo agente, previas e independientes de EV2).
  PROHIBIDO calibrar con cualquier material de EV2.
- Método: conjunto resuelto por la autora; los criterios problemáticos se
  incorporan al prompt como EJEMPLOS RESUELTOS (caso + veredicto + porqué),
  no como reglas declarativas. Todo ajuste se justifica con evidencia del
  PDF/criterio, jamás mirando el veredicto esperado. Cada ajuste re-corre el
  conjunto completo de calibración.
- **Criterio de frenado:** la calibración termina cuando los desacuerdos
  residuales son pocos y de etiqueta (no de evidencia). El % de acuerdo final
  juez-humana sobre el set de calibración se REPORTA como dato; no funciona
  como gate numérico.
- El prompt final del juez queda congelado por sha256 antes de la primera
  llamada sobre material de EV2, y lleva escrita la prohibición de
  modificarlo sin laudo de la autora.

## 6. Adjudicación humana

Adjudica la autora, contra el PDF fuente y el gold sellado, con worksheet.
Van a adjudicación:
1. toda pregunta `requiere_adjudicacion` (§2);
2. muestra simétrica del resto: 10% de los `correcto` y 10% de los
   `parcial`+`incorrecto`, por grafo, muestreados con
   `random.Random("adjudicacion-ev2-v1")` sobre ids ordenados.
La adjudicación de la muestra mide la tasa de error del juez en ambas
direcciones y se reporta junto al resultado principal.

## 7. Encadenamiento con el protocolo sellado (§3 del protocolo)

Los veredictos de la corrida base disparan lo ya sellado: re-corrida N=3 del
AGENTE para cada pregunta con veredicto `parcial` (mediana categórica), y
auditoría simétrica N=3 sobre el 10% de los `correcto` (semilla
`auditoria-ev2-v1`). Las respuestas de esas re-corridas se evalúan con ESTE
mismo método, sin cambios.

## 8. Qué no cubre este pre-registro

La métrica de navegabilidad (determinística, ya implementada y sellada en su
código) y el análisis causal posterior (verificador) tienen sus propios
artefactos. Este documento fija únicamente cómo se mide fidelidad.