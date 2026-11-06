# Enmienda 5 a L-ESQ-R2 — la negación de un verbo alcanza al comparador, y el comparador pegado a la cuantía gana sobre el coeficiente

**FIRMADA por la autora** el 04/10/2026 · Redactada: 2026-10-04.

Enmienda con fecha a L-ESQ-R2 (`data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`, FIRMADA en `4ef7650`;
sha256 del texto firmado `66c4a1b9…`). L-ESQ-R2 no se edita: esta enmienda vive al lado y se lee junto con
ella, con sus notas posteriores a la firma y con las enmiendas 2 (`5f9a731`), 3 (`8d01b04`) y 4 (`5c58f38`).
Por la regla k de CLAUDE.md §4, toda cita de L-ESQ-R2 es del texto firmado
(`git show 4ef7650:data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`), con su línea.

C2 de U-R2-CODIGO-2 aplicó las correcciones pedidas a su freno (`data/experiment/r2_codigo2/freno_c2.md`,
sin commit al 04/10/2026). Su código coincide con el §1, y las cifras del §2 son las de ese freno,
verificadas en su revisión.

---

## 0. Qué enmienda y por qué

**Lo que dice L-ESQ-R2**, §1.3, punto 3:

- Negación general (`:277-278`): «"No" o "sin" delante del verbo o del comparativo, con hasta tres palabras
  en el medio, invierte el sentido».
- Precedencia (`:294-295`): «primero coeficiente, después la negación, después las compuestas y por último
  las simples».
- Formas: «más de» y «menos de» entre las simples (`:275-276`); «igual o superior» e «igual o mayor» entre
  las compuestas (`:283`).

**Lo que se encontró.** La revisión independiente de KG-Tanda0-Diez-r2a (U-REVISION-LIBRE,
`reports/u_revision_libre/freno_b1.md:18` y `reporte.md:48` y `:57`, `54f57cd`):

- Hallazgo 1.9: 12 de los 79 elementos de umbral con regla simple son falsos. En 10, una negación queda a
  más de tres palabras del comparador y no lo invierte («no podrán tener un plazo de pago que exceda a los
  360 días», `ext::4.2::cierre`, quedó como mínimo estricto). En 2, «equivalente o superior al 1 %» quedó
  como estricto (`cla::3.4.4`).
- Hallazgo 1.10: 28 de los 140 elementos con `coeficiente` tienen un comparador pegado a la cuantía («no
  superarán el 1,25 % de los activos ponderados»): el valor acota, no multiplica.
- Los denominadores, recomputados sobre el grafo sellado (`99fe2bfa…`): 79 elementos con regla simple y 140
  con `coeficiente`, de 842.

**Lo que hace el código de C2** (`data/experiment/pyd_r2/code/reglas_comparacion.py`, puntos (i) y (j); sin
commit al 04/10/2026). La negación de un verbo alcanza al comparador más allá de las tres palabras, y un
comparador pegado a la cuantía gana sobre el marcador de coeficiente. Las dos cosas cambian el §1.3
firmado.

**Lo que se midió**, con el código de C2 sobre las fuentes de los dos grafos r2a (FRENO C2 corregido,
`data/experiment/r2_codigo2/salidas/c2_cadena.json`, `umbrales`; recomputado en la revisión del freno, con
una simulación fuera del repo que re-aplica las reglas nodo por nodo, reproduce los 842 y los 758 elementos
sellados y da los mismos 50 y 46 nodos que cambian):

- Negación (i): cambian 13 elementos en diez y 11 en desarrollo. Los 13 de diez son los 12 de la revisión
  independiente más `ctacte::1.5.2.12` («no podrán registrar una antigüedad superior a…»): 11 por la
  negación y 2 por «equivalente o superior». Leídos los 13, todos quedan bien.
- La misma regla, sobre el texto propio de las 2.439 unidades de la E0 de la tanda 0
  (`salida_tanda0_r2b/`), no solo sobre lo extraído: la negación nueva invierte 12 cuantías. Leídas las 12,
  todas son cotas negadas («sin haber incurrido en atrasos superiores a 31 días», «en ningún caso el
  registro del cheque podrá demorarse más de 15 días corridos»).
- Comparador pegado (j): 26 elementos en diez y 26 en desarrollo dejan `coeficiente`. De los 28 de la
  revisión independiente, el FRENO C2 atribuye 2 a dobles conteos del script de esa revisión (NO VERIFICADO:
  ese script no está versionado). Entre los 26 están «más del 5%» (`cap::3.1.11.2`), que deja `coeficiente`
  por la forma del punto 3.b, y el «3 %» de `cap::6.2.2.3`, que corrige el punto 1.d. Leídos los 26 de diez,
  25 quedan bien y el de `cap::6.2.2.3` queda con el límite del §3.
- «O no»: en `cap::6.2.2.3`, «represente o no un rendimiento menor a 3 % anual» pasaba de `coeficiente` a
  mínimo inclusivo con el punto 2 solo, porque el «no» de «o no» está a menos de tres palabras de «menor a». En el texto propio
  de las 2.439 unidades de la E0 de la tanda 0 (`salida_tanda0_r2b/`), «o no» delante de un comparador
  aparece dos veces, las dos en `cap::6.2.2.3`.
- «Más del» y «menos del»: en el mismo texto, 7 cuantías llevan una de las dos formas pegada y quedaban sin
  marcador. Leídas las 7, las 7 son comparaciones («no menos del 50 %», «menos del 20 %», «más del 10 %»).

## 1. Qué decide

1. **Alcance de la negación.** La regla «Negación general» del §1.3 se lee así:
   a. Con cero a tres palabras entre el negador y el comparador, la negación invierte el sentido, como hasta
      ahora. A «no» y «sin» se suman «ningún» y «ninguna».
   b. Más allá de las tres palabras, la negación alcanza al comparador solo si niega un verbo:
      - «no» seguido de una forma de haber, poder o deber («no podrán registrar una antigüedad superior
        a…», «no ha utilizado este mecanismo por un monto superior a…»);
      - «sin» seguido de un infinitivo («sin haber incurrido en atrasos superiores a…»);
      - «ningún» y «ninguna», siempre.
      Y solo si entre el negador y el comparador, dentro de la cláusula, no hay una coma, otra forma de
      comparación ni una palabra de corte: «y», «e», «o», «u», «ni», «cuando», «si», «cuyo» y sus formas,
      «donde», «aunque», «pero», «salvo», «excepto», «mientras» y «siempre». «Otra forma de comparación» es
      una simple o una compuesta; no cuentan la adyacencia de «mínimo» y «máximo» ni «o más».
   c. Un «no» que no niega un verbo («sector privado no financiero», «no residentes») no alcanza más allá de
      las tres palabras.
   d. «O no» no es una negación. Un «no» precedido por «o» («sea o no», «haya o no», «represente o no»,
      también entre comas) no cuenta como negador, a ninguna distancia. El comparador se lee sin invertir.
   e. Los sentidos de la inversión no cambian: la negación de un mínimo estricto es máximo inclusivo, y la
      de un máximo estricto, mínimo inclusivo.
2. **Precedencia.** Un comparador pegado a la cuantía gana sobre el marcador de coeficiente. La regla
   «Precedencia» del §1.3 se lee así: «primero coeficiente, salvo que un comparador esté pegado a la
   cuantía; después la negación, después las compuestas y por último las simples».
   - «Pegado» es una forma simple, compuesta o de adyacencia que termina justo antes de la cuantía, con solo
     artículos o «de», «del», «a», «al» o «en» en el medio; o una forma pospuesta que va inmediatamente
     después de la cuantía. «O más» y «o menos» cuentan también con un paréntesis en el medio. Y cuentan los
     marcadores que la detección de la cuantía exige o incluye: el de un ordinal («hasta el», «dentro del»,
     «a más tardar») y el «o más» que va entre el paréntesis y la unidad.
   - Con un comparador pegado, la cuantía sigue las demás reglas, en su orden. El marcador de coeficiente
     no se le aplica, venga del tramo, de la descripción o del título.
3. **Formas que se suman**, con el sentido de las que ya están:
   a. «equivalente o superior» y las formas verbales («igualen o superen», «iguale o exceda») valen como
      «igual o superior»; lo mismo hacia abajo, como «igual o inferior».
   b. «más del» y «menos del» valen como «más de» y «menos de». Esta forma la sumé al revisar el FRENO C2, y
      la autora la aceptó el 04/10/2026.
4. **Desde cuándo rige.** Desde el commit de C2, para toda fase. Los grafos r2a sellados no se tocan. La
   cadena r2a, corrida con el código de C2, deja de dar los sha256 sellados: cambian solo los elementos de
   umbral que esta enmienda y los puntos (c) e (i) a (k) de C2 declaran, y las `remite_a` de su punto (a).
   Con el código de C2 da `70d51e42…` en diez y `fa4c1043…` en desarrollo: cambian los umbrales de 50 y de
   46 nodos. La autora lo aceptó el 04/10/2026. Los dos grafos r2a sellados (`99fe2bfa…` y `93a7af72…`) siguen en el
   repo y se reproducen con el código de `f8dedd4`, el commit que los selló: la tesis cita sus cifras con ese
   commit. Reproducción hecha el 04/10/2026 sobre una copia de ese commit, byte a byte en los dos. Además
   de lo versionado pide dos entradas que el repo no versiona: los diez PDF, con el sha256 del manifiesto, y
   `e3_verificador/cache/e1_reintentos.db` (sha256 `e71380308cbe…`).

## 2. Efectos declarados

Con KG-Tanda0-Diez-r2a y KG-Tanda0-Desarrollo-r2a como referencia:

| Regla | Diez | Desarrollo | Qué pasa |
|---|--:|--:|---|
| 1.a a 1.c y 3.a, negación e «igual o superior» | 13 | 11 | salen de un sentido invertido o de un borde equivocado |
| 2, comparador pegado | 26 | 26 | dejan `coeficiente` |
| 1.d, «o no» | 1 | 1 | `cap::6.2.2.3`, «3 %»: queda máximo estricto («menor a 3 %»); sin esta regla quedaba mínimo inclusivo |
| 3.b, «más del» y «menos del» | 4 | 4 | 3 dejan `no_determinada` y 1 deja `coeficiente` (`cap::3.1.11.2`) |

Son las cifras del FRENO C2 corregido (`c2_cadena.json`, `umbrales.elementos_por_regla`), verificadas en su
revisión. Las filas suman 44 y 42, y los elementos distintos son 42 y 40, porque dos cuentan en dos filas:
`cap::6.2.2.3`, en la del comparador pegado y en la de «o no», y `cap::3.1.11.2`, en la del comparador pegado
y en la de «más del».
Los 4 de la última fila son `cla::6.3.2` («no menos del 50%», a mínimo inclusivo), `cap::8.4.2.1` («menos
del 10 %») y `cla::6.5.4.7` («menos del 20 %»), a máximo estricto, y `cap::3.1.11.2` («más del 5%»), a
mínimo estricto.

## 3. Límites declarados

- **«O no».** El elemento de `cap::6.2.2.3` queda con el comparador literal, «menor a 3 %». La norma
  distingue dos ramas, según el cupón sea o no menor a 3 %, y el elemento no dice que hay dos.
- **Lista de verbos.** Más allá de las tres palabras, «no» alcanza solo con una lista cerrada de formas de
  haber, poder y deber (`AUXILIARES_NEGADOS`). Una negación lejana con otro verbo, o con una forma fuera de
  la lista («no hubiere», «no pudiera»), no invierte el comparador. No está medido cuántas hay.
- **«Sin» con infinitivo.** El infinitivo se reconoce por la terminación de la palabra que sigue a «sin»
  («-ar», «-er» o «-ir»). Un sustantivo con esa terminación («sin lugar a…») se toma por verbo. No está
  medido.
- **Palabras de corte.** Una «o» o una «y» entre el negador y el comparador corta el alcance, también cuando
  la negación sigue valiendo para el segundo término. No está medido.

## 4. Implementación

Puntos (i) y (j) de C2 de U-R2-CODIGO-2 (`docs/mandatos/UR2CODIGO2_correcciones_previas_a_reext.md`), con
las correcciones pedidas en la revisión de su freno:

- `pyd_r2/code/reglas_comparacion.py`: `NEGADORES`, `NEGACION_BARRERAS`, `AUXILIARES_NEGADOS`,
  `_niega_un_verbo` y `_negada`, para el punto 1; la función `pegado` de `fijar_comparacion`, para el punto
  2; `_IGUAL_O` y las formas `mas_de` y `menos_de` de `SIMPLES`, para el punto 3;
- `pyd_r2/code/selftest_pyd_r2.py`, grupo G15 (42 casos; el selftest da 385 de 385): un caso por regla, con
  `cap::6.2.2.3` como caso de control de «o no»;
- control: la lista de cada elemento que cambia en los dos grafos r2a, por regla.

## 5. Qué no cambia

- El texto de L-ESQ-R2, sus notas y las enmiendas 2, 3 y 4.
- Los valores cerrados de `comparacion` y el sentido de cada forma.
- El marcador de coeficiente y sus fuentes, cuando no hay un comparador pegado.
- La adyacencia de «mínimo» y «máximo», las compuestas y la regla de «igual».
- E1 no emite `comparacion`: la fija el código. El prefijo, el tool schema y el esquema no cambian.
- Los grafos sellados.

## Firma

FIRMADA por la autora el 04/10/2026. Rige desde esta firma. El código que la aplica es el de C2 de
U-R2-CODIGO-2, cuyo commit está PENDIENTE al firmarse.
