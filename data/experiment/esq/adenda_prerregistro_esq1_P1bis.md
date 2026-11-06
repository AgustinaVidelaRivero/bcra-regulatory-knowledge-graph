# Adenda al pre-registro de ESQ-1 — control de instrumento rediseñado (P1′)

**Estado: FIRMADO — Agustina Videla Rivero, 31/08/2026. Sellado por el commit
que lo contiene; el control rediseñado no corre sin este sello previo.** El pre-registro (`38be6e5`) no se enmienda: P1
queda FALSADA en el registro (control original: A 0/20, B 3/10, C 0/10 — commit
de U-ESQ-1c) y esta adenda declara su reemplazo. Diagnóstico que la funda:
`data/experiment/esq/control/diagnostico_control_esq.md` (U-ESQ-1c-diag).

## 1. Qué queda del pre-registro original (todo lo no tocado acá)

P2–P5 intactas (son sobre ESQ-1, que no corrió). Bandas §7.4, regla de
normalización §7.5, secuencia de diez pasos, blindaje de D9, tope D6 de USD
9,00 y re-presupuesto D7: sin cambio.

## 2. Por qué se rediseña el control (del diagnóstico, no de la narrativa)

- **Brazo A tenía la premisa mala, pre-declarada como debilidad de P1**: la
  regla NO-PROSA ordena omitir ANTES del tipado; para tablas, la instrucción
  vieja y el canal nuevo coinciden en omitir. A no medía el canal: medía la
  estabilidad de NO-PROSA (19/20).
- **Brazo B tenía el pool contaminado por re-expresabilidad**: ≥4/10 de las
  presiones de firma eran caja mal elegida, no inexpresabilidad — ahí, cero
  propuestas es extracción correcta. B se retira como gate; su hallazgo
  («teniendo el canal disponible, el modelo resolvió el 100 % dentro del
  esquema») se registra para ESQ-3 y C1.7.
- **Bug objetivo implicado**: la description del tool en modo abierto decía
  «schema cerrado v2» (entrada 4.ii de la cola de mejoras, promovida de
  cosmética a implicada). Se corrige SOLO en modo abierto; el flag apagado
  sigue byte-idéntico a producción.

## 3. El control rediseñado

**Brazo A′ — control positivo con contenido plantado.** 10 unidades dopadas:
unidades reales del conjunto de desarrollo a las que se les añade exactamente
UNA cláusula normativa plausible, EN PROSA, cuyo contenido está fuera del
esquema a sabiendas — 5 con un concepto que exige tipo nuevo, 5 con una
relación que exige predicado nuevo. Reglas duras: (a) el contenido plantado lo
aprueba la autora ANTES de gastar (define qué mide el control); (b) las
cadenas plantadas NO aparecen en el prompt ni en ningún ejemplo (no sembrar);
(c) las unidades dopadas son material de instrumento: NO entran a ningún
conteo de ESQ-1, ni al corpus, ni al archivo de exclusión como si fueran
documentos del test.
**Brazo C — sin cambio de diseño** (pasó): 10 unidades limpias re-corridas
bajo el prefijo nuevo.

Alcance declarado: este control prueba capacidad de disparo del canal sobre
contenido claro y plantado; no mide sensibilidad sobre contenido real sutil.
Un control aprobado habilita a ESQ-1, no garantiza recall del canal.

## 4. P1′ — predicción sellada del control rediseñado

**P1′: el control rediseñado aprueba en sus dos brazos.**
A′: **≥7 de 10 en total, y ≥3 de 5 en cada mitad** (las de tipo deben emitir
`tipo_propuesto`; las de predicado, `predicado_propuesto`). Los dos
sub-conteos se reportan por separado. C: **≤1 de 10** limpias emite un tipo
propuesto.
*Fundamento:* con contenido expresable en prosa y deliberadamente fuera de
esquema, un canal funcional debe dispararse; la description corregida elimina
la contradicción objetiva conocida.
*Falsada si:* cualquiera de los dos brazos no alcanza su umbral. Si A′ falla
con la description corregida, la hipótesis viva pasa a ser la competencia del
lenguaje de cierre, y el paso siguiente declarado es neutralizar los tres
cierres en modo abierto (O2 del diagnóstico) — nunca ajustar estos umbrales
post-hoc.

## 5. Consecuencia de lectura (se hereda a ESQ-1)

Con un control plantado que dispara, **una eventual banda A de ESQ-1 se
vuelve interpretable** (la revisión de instrumento que D9 exige ante una
banda A cuenta con este control como su evidencia central, y se ejecuta
igual). Sin control aprobado, rige lo sellado: ningún resultado de ESQ-1 es
admisible.

## 6. Checkbox de implementación

- [ ] Description corregida SOLO en modo abierto; flag apagado byte-idéntico a
      producción, verificado por selftest.
- [ ] 10 unidades dopadas construidas y aprobadas por la autora antes del gasto.
- [ ] Control re-corrido (A′ + C) bajo el prefijo nuevo, con tope parcial.
- [ ] Recargo D7 re-medido bajo el prefijo nuevo; re-presupuesto de ESQ-1.
- [ ] Entrada 4.ii de la cola de mejoras actualizada (resuelta por esta adenda).

---
**Firma:** Agustina Videla Rivero · **Fecha:** 31/08/2026
