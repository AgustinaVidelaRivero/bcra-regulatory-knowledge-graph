# Adenda P1″ al pre-registro de ESQ-1 — neutralización de los cierres (O2)

**Estado: FIRMADO — Agustina Videla Rivero, 31/08/2026. Sellado por el commit
que lo contiene; la corrida de O2 no arranca sin este sello previo.** El pre-registro (`38be6e5`) y la adenda P1′ (`e68e861`) no se
enmiendan: **P1 y P1′ quedan FALSADAS en el registro** (P1: A 0/20, B 3/10 —
commit de U-ESQ-1c; P1′: A′ 0/10 con tipo 0/5 y predicado 0/5, C 0/10 —
`c25273f`). Esta adenda declara el último peldaño de la
escalera, tal como P1′ lo dejó escrito antes de correr: con la description
corregida y contenido plantado claro, la hipótesis viva es la competencia del
lenguaje de cierre, y el paso declarado es O2.

## 1. Qué queda idéntico (cambio de UNA sola variable)

Entre la corrida P1′ y la corrida P1″ **lo único que cambia son los cierres
del system en modo abierto** (§3). Todo lo demás queda idéntico y sellado:

- **Las 10 unidades dopadas**: mismos fixtures (`dopadas_p1bis.json`, con la
  aprobación de la autora vigente y verificada por sha contra `c25273f`); ni
  una cláusula se toca.
- **Los umbrales**: A′ **≥7/10 en total y ≥3/5 en cada mitad**, sub-conteos
  por separado; C **≤1/10**. Idénticos a P1′.
- **La description del tool**: queda como la corrigió U-ESQ-1d. No se toca.
- **El brazo C**: las mismas 10 unidades limpias.
- Reglas de P1′ que se heredan: cruce de canal se reporta como tal y no
  cuenta como el propuesto esperado; el conteo es por disparo del canal
  esperado, no por valor de cadena; las dopadas no entran a ningún conteo de
  ESQ-1.

Si A′ pasa de 0/10 a disparar, la atribución al lenguaje de cierre es
limpia; cualquier cambio adicional la arruinaría.

## 2. Evidencia que funda este peldaño

El control P1′ mostró que el modelo **leyó las 10 cláusulas plantadas y las
extrajo todas forzadas dentro del esquema**: ni una omisión (desobedeciendo
la regla de omitir lo que no encaja) ni una propuesta (desobedeciendo el
canal). Re-tipado semánticamente erróneo en la mitad tipo y relaciones
nominalizadas como entidades válidas en la mitad predicado. El contenido que
no encaja no se pierde: **se deforma en extracciones esquema-conformes**
(hallazgo registrado en el plan: conforme-al-esquema ≠ fiel).

## 3. La variable: dos cierres del system, neutralizados SOLO en modo abierto

De los tres cierres identificados por el diagnóstico, uno (la description
del tool) ya fue corregido en U-ESQ-1d. Los **dos restantes** viven en el
system y se reemplazan ÚNICAMENTE cuando `canal_abierto=True`, con estos
textos sellados acá (el ejecutor los implementa verbatim, sin discreción):

**(i) Encabezado del catálogo de tipos** (hoy: «TIPOS DE ENTIDAD VÁLIDOS
(exactamente 6, ningún otro)»). En modo abierto pasa a:

> TIPOS DE ENTIDAD DEL CATÁLOGO (6) — si un contenido normativo claro no
> encaja en ninguno, NO lo fuerces: emitilo por el canal abierto
> (`tipo_propuesto`).

**(ii) Regla 4** (hoy: «NO inventes tipos ni predicados fuera de las listas.
Si una idea no encaja en los 6 tipos de entidad o 12 predicados, NO la
incluyas. Es preferible no extraer algo a forzarlo en una caja equivocada.»).
En modo abierto pasa a:

> **NO fuerces contenido en cajas equivocadas.** Si una idea no encaja en
> los 6 tipos de entidad o en los 12 predicados, NO la fuerces en el tipo o
> predicado más parecido NI la omitas: emitila por el canal abierto
> (`tipo_propuesto` para entidades, `predicado_propuesto` para relaciones).
> Forzar una caja equivocada es peor que proponer.

Prohibición vigente: los textos no incluyen ningún ejemplo de valor de tipo
o predicado (no sembrar). El modo cerrado (producción) queda byte-idéntico,
verificado por selftest contra los candados sellados.

## 4. P1″ — predicción sellada

**P1″: con los cierres neutralizados, el control aprueba en sus dos brazos.**
A′: ≥7/10 en total y ≥3/5 en cada mitad, sub-conteos por separado. C: ≤1/10.
*Fundamento:* la única explicación en pie tras dos controles es que el
lenguaje de cierre domina al canal; removido el cierre en el modo de
medición, un canal funcional debe disparar sobre contenido plantado claro.
*Falsada si:* cualquiera de los dos brazos no alcanza su umbral.

## 5. Tres declaraciones (se leen junto con el resultado)

**(a) Una sola variable.** Lo declarado en §1: dopadas, umbrales, description
y brazo C idénticos a P1′; solo cambian los dos textos de §3.

**(b) Honestidad interpretativa.** Con los cierres neutralizados, el modo
abierto **deja de ser «producción + posdata»**: se rompe la aditividad, y
ESQ-1 pasa a medir bajo un **prompt de medición distinto del de producción**.
Sus conteos se leen como propiedad de ese modo de medición, no del prompt de
producción. El recargo D7 se re-mide bajo el prefijo nuevo; el re-presupuesto
provisorio (lectura global, USD 6,51) se reemplaza por el medido.

**(c) Cierre de la escalera.** Si O2 también da cero, **el canal declarativo
queda declarado inviable con este modelo y este prompt** — no hay tercer
retoque de lenguaje. Las alternativas declaradas son: el **modo (ii)** de
U-ESQ-0 (segundo pase de descubrimiento, descartado entonces por costo y
revivido por esta evidencia) o **protocolizar el patrón de deformación
semántica en ESQ-2** como vía de detección de deriva. Sin margen para
estirar la escalera.

## 6. Checkbox de implementación

- [ ] Reemplazos (i) y (ii) implementados verbatim, SOLO en modo abierto;
      cerrado byte-idéntico verificado contra los candados.
- [ ] Fixtures de dopadas verificados por sha contra `c25273f`
      (cero cambios).
- [ ] Selftest completo en PASS antes del gasto.
- [ ] Corrida dentro del tope parcial; cruce db==jsonl; producción intacta.
- [ ] Reporte contra P1″ con sub-conteos por mitad, detalle por dopada y
      comparación pareada dopada-por-dopada contra la corrida P1′.
- [ ] Recargo D7 re-medido y re-presupuesto de ESQ-1 actualizado.

---
**Firma:** Agustina Videla Rivero · **Fecha:** 31/08/2026
