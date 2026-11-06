# Fe de erratas — la fecha del corpus congelado («marzo de 2026»)

**Estado: FIRMADA — Agustina Videla Rivero, 07/09/2026.** Redactada por la instancia del plan,
que origina el error y lo asume. Detectado por el ejecutor de U-JOB-ACT
en su freno de diseño (07/09), verificado independientemente por la
instancia del plan contra los artefactos y la historia del repositorio.

## El hecho

El registro afirma en tres lugares que el corpus quedó descargado y
congelado en **marzo de 2026**. Es falso: esa fecha no tiene respaldo en
ningún artefacto y la historia del repositorio la contradice — su primer
commit es del **26 de abril de 2026**, de modo que en marzo el proyecto
no existía.

Las fechas ancladas en artefactos son:

| corpus | fecha | fuente |
|---|---|---|
| Los 5 TOs del conjunto de desarrollo | **2026-05-07 a 2026-05-10** | `fecha_descarga` de `data/raw/manifiesto.csv` (los 161 `TO_actual` caen todos en 2026-05) |
| Los 152 TOs del inventario de escalado | **2026-08-13** | commit de alta `111ed19` (`escalado_prep/`) |

## Dónde se propagó

- `docs/laudo_B5.5_alcance_corpus_y_catalogo.md` §5.2 — **laudo FIRMADO**
  (04/09, sello `c0daef1`): «el corpus congelado es de marzo de 2026, así
  que la primera corrida del job produce el delta marzo→presente».
- `docs/registro_reunion_mentores_2026-09-04.md` §2 (dos menciones).
- `docs/plan_tesis.md`, fila U-JOB-ACT.
- La adenda al laudo B5.5 NO la contiene (verificado).

Los tres textos fueron redactados por la instancia del plan. El laudo
firmado no se edita: esta fe de erratas lo supersede en ese punto.

## Causa raíz

La fecha se escribió por inferencia, no por lectura de artefacto: es
exactamente la clase de dato que la disciplina del circuito exige
verificar contra archivos antes de escribir, y no se verificó. A
diferencia del despacho fantasma (`docs/fe_erratas_despacho_UB53.md`),
acá el rastro SÍ existía en el repositorio y estaba a un comando de
distancia. Es la tercera imprecisión de la instancia del plan en la
serie de mandatos recientes, y la primera que alcanza un documento
firmado.

## Qué cambia y qué no

**Cambia** el dimensionamiento de la ventana de delta, y con él la
expectativa sobre la exigencia 6 (validación contra material posterior a
la construcción): la ventana real es de unos cuatro meses para los 5 TOs
del conjunto de desarrollo y de unas tres semanas y media para los 152.
Si el delta aparece, se apoyará en los 5 —los de ventana larga, y los
únicos que el grafo vigente cubre— y no en el volumen de los 152. Un
delta chico o nulo es, con estas fechas, el resultado esperable y no un
fracaso del instrumento.

**No cambia** nada más: la sinergia sigue en pie con su tamaño real; la
exigencia 7 (el mecanismo de actualización) es el compromiso principal y
no depende del tamaño del delta; el corpus sigue congelado por sha y
ningún número del capítulo, laudo o medición se apoya en la fecha.

## Firma

**Firma: Agustina Videla Rivero · Fecha: 07/09/2026.**
