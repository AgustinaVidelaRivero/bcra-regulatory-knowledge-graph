# Laudo ESQ-2 — Diseño y presupuesto del test de cobertura protocolizado

**Estado: FIRMADO — Agustina Videla Rivero, 01/09/2026.** Revisión de diseño que este laudo
resuelve: crítica de mesa contra material sellado (B1/B2/B3 + ajustes A1–A6,
sesión de mesa del 31/08–01/09). Contexto que lo habilita: la rama (b) del
árbol de U-ESQ-2-cal (`eadf4a5`, pre-registro `bca863f`) dejó a **ESQ-2
protocolizada como única vía** de evaluación de cobertura del esquema — el
censo por LLM quedó cerrado con doble evidencia.

## 1. Resoluciones

**(i) Presupuesto — re-asignación del remanente de D6.** El tope de USD 9,00
laudado en D6 (`docs/laudo_ESQ-1_diseno.md`) tenía por objeto ESQ-1 modo (i),
hoy falsado-cerrado (`38be6e5`; escalera + calibración, gasto real USD 0,92).
El **remanente (~USD 8,08) se re-asigna a ESQ-2**, con **tope propio de la
unidad: USD 6,50** — cubre la extracción E1-solo de los 10 TOs (estimación
gruesa 5,5, con re-estimación anclada obligatoria y freno duro del runner
antes y durante el gasto) más margen; las fichas, los disparadores y el gate
de paridad son USD 0 de API. Lo no gastado no se re-asigna de nuevo sin laudo.

**(ii) Naturaleza de la extracción — provisional, pre-B5.4.** La extracción de
los 10 TOs es **material de medición y de desarrollo, provisional**: corre
E1-solo (sin E3, sin ensamblado), con runner propio de la unidad sobre los
chunks de E0 ya calculados en `escalado_prep/`, en modo cerrado con flag
apagado, y **sin el atajo del rol de alcance** (D5 del laudo ESQ-1: lectura
absoluta, canal de sujetos en cuarentena). La frase «byte-idéntico a lo que
escalaría» queda **retirada del diseño**: esto NO es el arranque del escalado
— **B5.5 queda intacta** y el escalado real requerirá B5.1–B5.4 (roles,
parametrización, E3) y su propio laudo.

**(iii) Corrección de D4 por declaración.** D4 (`laudo_ESQ-1_diseno.md:30-34`)
selló dos listas de 10 documentos. **ESQ-2 usa los 10 TOs de la lista de
ESQ-1** (ayccef, expaef, opefci, adrei, cryl, actgar, prevmi, lavdin, traval,
ctacor — universo laudado D3, sorteo sellado semilla 20260827, 762 unidades,
254 páginas), porque ESQ-1 murió **sin correr** y ese material laudado queda
libre. **Ganancia registrada**: los 10 documentos de la lista original de
ESQ-2 (ctacte, depinv, lingob, rrci, polcre, gescre, pagjub, retype, docvig,
snp_atm) quedan **VÍRGENES para la evaluación final** — se queman 10
documentos, no 20. Esta es una corrección declarada del laudo D4, no una
enmienda de su texto.

**(iv) Absorciones.** (a) La fila de ESQ-2 en el plan decía «$0 de extracción»
— supuesto huérfano del diseño en que ESQ-1 pagaba la extracción; se corrige
con el costo laudado acá. (b) **`data/experiment/esq/documentos_excluidos_esq.json`
no existe** (ESQ-1 nunca corrió): crearlo con los 10 IDs y sus sha256 pasa a
ser **entregable de la unidad ESQ-2**, y B6.3 lo cita al construir su eval set
(nota de alcance del bloque ESQ, `docs/plan_tesis.md`).

## 2. Qué NO decide este laudo

- No decide el resultado de la lectura ni el destino de ninguna familia: eso
  es ESQ-3, con el criterio pre-registrado (no calibrado) del pre-registro.
- No arranca el escalado ni modifica B5.5, B5.1–B5.4 ni D5 del plan.
- No re-abre el censo por LLM (rama (b), final de un solo tiro de `bca863f`).
- No modifica el principio 10: los 10 TOs extraídos pasan al conjunto de
  desarrollo a efectos del esquema y quedan excluidos de la evaluación final;
  su contenido entrará al grafo escalado cuando el escalado corra con el
  pipeline completo.

## 3. Consecuencias operativas — checkbox de implementación

- [ ] Pre-registro de ESQ-2 sellado por commit ANTES de gastar
      (`data/experiment/esq/prerregistro_esq2.md`).
- [ ] Gate de paridad por caché aprobado ANTES de la corrida grande.
- [ ] Re-estimación anclada de la extracción bajo el tope de USD 6,50.
- [ ] `documentos_excluidos_esq.json` creado con los 10 IDs + sha256.
- [ ] Fila de ESQ-2 del plan corregida (costo real, universo, este laudo).
- [ ] Gasto real contra estimado registrado al cierre.

---
**Firma:** Agustina Videla Rivero · **Fecha:** 01/09/2026
