# Enmienda 3 al pre-registro de la evaluación por tripletas — el intervalo de la precisión ponderada, con Wilson y el n efectivo de Kish

**FIRMADA por la autora el 20/10/2026, tal cual, con la regla del estrato sin esenciales** (por mensaje recibido a las 10:01:39; hoja de
ruta de la mesa, §195), antes de cualquier cifra de V. Rige desde esta firma. La versión para firmar está en el paquete de la mesa
(`decisiones_191_mesa/enmienda3/`, sha256 `2458eb86…`). La redactó la mesa el 20/10/2026 (hoja de ruta de la mesa, §191) sobre la decisión
de la autora del 20/10/2026, recibida a las 08:36:59, tal cual: «El intervalo de la precisión ponderada de las tripletas pasa de Wald a
Wilson con el n efectivo de Kish, como las tasas ponderadas de la tanda 1, en V y en T, incluida la cifra sobre las esenciales. […] La
firmo antes de que se calcule cualquier cifra de V.» El texto firmado son las líneas anteriores a «## Firma»: no se edita después y recibe
notas fechadas debajo de esa sección.

Enmienda con fecha a `docs/preregistro_evaluacion_tripletas.md`, FIRMADO por la autora el 07/10/2026 en `4afbe511` (texto firmado, sha256
`8ce611ba…`). Va al lado de la enmienda 1 (la vía de umbrales, firmada el 08/10/2026, `a0f98152`) y de la enmienda 2 (el solapamiento con
la desambiguación y la etapa T sin la tanda 0, firmada el 19/10/2026, `593e5db2`). **Ni el pre-registro ni las enmiendas 1 y 2 se
editan:** al firmarse, el pre-registro recibe una nota fechada al pie que remite a esta.

## 0. Por qué

- **El texto firmado pide Wilson en toda proporción, y en la ponderada usa Wald.** El §0 trae, de B4.1, los «intervalos de Wilson en toda
  proporción (exigencia 4)» (`4afbe511:docs/preregistro_evaluacion_tripletas.md:13-14`). El §3.6 da a la cruda su Wilson (`:86`), pero a la
  ponderada le da un intervalo de Wald, con la varianza Σ_h W_h² · p̂_h (1 − p̂_h) / n_h (`:87-91`).
- **Wald falla justo donde está esta cifra.** Con una precisión cerca de 0,85 o más y estratos de pocas aristas, el intervalo de Wald queda
  corto, y con un estrato de precisión 1 su aporte a la varianza es 0. Wilson no tiene ese problema.
- **Es el método de las tasas ponderadas de la tanda 1** (`95b18217:docs/preregistro_tanda1.md:590-591` y `:594`): Wilson al 95 % con el
  tamaño efectivo de Kish, n_ef = 1 / Σ w_c² / n_c, que con un sorteo simple da el Wilson de siempre.
- **No mira ningún dato.** Se firma antes de calcular cualquier cifra de V (decisión de la autora): ninguna precisión de V ni de T está
  calculada. El método no depende de ningún resultado.

## 1. Lo que cambia

1. **El intervalo de la cifra ponderada** (§3.6, `:87-91`), en V y en T:
   - la estimación puntual no cambia: p̂_w = Σ_h W_h · p̂_h, con W_h = N_h / N (`:88`);
   - **el intervalo es el de Wilson al 95 %** (z = 1,959964), con p̂_w y el n efectivo de Kish, n_ef = 1 / Σ_h (W_h² / n_h), en lugar del
     intervalo de Wald;
   - con una muestra autoponderada (n_h / n = W_h), n_ef = n y p̂_w es la cruda, así que da el Wilson de la cruda;
   - **los estratos con n_h < 5** se agrupan en «otros» para el intervalo, como el §3.6 los agrupa para la varianza (`:90-91`): el estrato
     agrupado lleva W = Σ W_h y n = Σ n_h. La estimación puntual sigue sumando cada estrato, y cada uno se informa con su fracción cruda
     «n de N»;
   - **un estrato sin muestra** (en V, «otros», con cuota 0; nota al pie del 19/10/2026 sobre el sorteo de V) no entra en n_ef, y p̂_w se
     informa con las dos cotas de ese estrato, como dice esa nota.
2. **La cifra sobre las esenciales** (§3.6, `:92-93`): la ponderada con los mismos W_h, sobre las esenciales de cada estrato, lleva el
   mismo intervalo de Wilson con n_ef, calculado con los n_h de las esenciales decididas.
   - **Un estrato sin ninguna esencial decidida** no tiene p̂_h: sale de la suma, y los W_h de los demás se renormalizan para que sumen 1.
     Se declara con su W_h y con las dos cotas de ese estrato.
3. **En T** (§7, `:217`; enmienda 2, §2), lo mismo para cada cifra ponderada:
   - la precisión de todo;
   - la precisión sin las aristas de la tanda 0, con los W_h recalculados como dice la enmienda 2;
   - y las dos sobre las esenciales.
   - La precisión de `aplica_a` sola es cruda (enmienda 2, §2, punto 3) y ya va con su Wilson.
4. **El script:** `wilson_kish_tripletas_mesa.py` (paquete de la mesa, `decisiones_191_mesa/enmienda3/`). Implementa la fórmula y la
   prueba sin ningún dato de V ni de T, en 12 casos:
   - con una muestra autoponderada da el Wilson simple;
   - reproduce los dos anclajes del pre-registro (`:285`: 84 de 100 da 0,7558, y 26 de 30, 0,7032);
   - con pesos desiguales, n_ef queda por debajo de n y el intervalo, más ancho;
   - con p̂_w = 1, el límite inferior queda por debajo de 1;
   - el agrupamiento de los estratos chicos.
   Entra al repo con el código de la etapa V, antes de su primera cifra.

## 2. Lo que no cambia

- **Las once decisiones del §10** del pre-registro, la etapa V, la etapa T, la vía de cobertura y la vía de umbrales (enmienda 1).
- **La muestra, los estratos, los W_h, la cruda con su Wilson** (`:86`) y las fracciones por predicado y por TO (`:94`).
- **El criterio de acuerdo del juez** (§4.6, `:133-142`): compara la precisión según el juez y según la autora, cruda y ponderada (condición
  (ii)), sobre las estimaciones puntuales, que no cambian.
- **Los topes** de V y de T. La enmienda no agrega lecturas ni llamadas.
- **La comparación con la cifra de U-LECTURA-ACEPTADAS:** el §1 ya dice que no se comparan (`:39`). La cifra ponderada de esa lectura
  llevaba el intervalo normal (`:37`). El pre-registro de la tanda 1 la recalculó con Wilson y Kish, y dejó la normal al lado
  (`95b18217:docs/preregistro_tanda1.md:594-595`).

## 3. Cuándo

- **Se firma antes de calcular cualquier cifra de V.** Hoy no hay ninguna: el juez de V no corrió y la autora todavía no selló todos los
  lotes del gold.
- **Con la firma, la nota al pie del pre-registro** remite a esta enmienda, con su commit, como las notas del 08/10 y del 19/10/2026.

## Firma

**FIRMADA por la autora el 20/10/2026,** por mensaje recibido a las 10:01:39 (hoja de ruta de la mesa, §195), tal cual: «Firmo la enmienda
3 al pre-registro de tripletas tal cual, con la regla del estrato sin esenciales
(decisiones_191_mesa/enmienda3/ENMIENDA3_preregistro_tripletas_PARA_FIRMAR_mesa.md, sha256
2458eb86df91ac47f6fa41373cc1bdc8a3e1bd5b2b770180ee225b14611e99bf). Rige desde este mensaje, antes de cualquier cifra de V. Su commit va
después de los de T3, y la calibración del juez puede correr antes de ese commit.»

El script del §1, punto 4, entra con el commit de esta firma, antes de cualquier cifra de V:
`data/experiment/tripletas_v/analisis/wilson_kish_tripletas_mesa.py` (sha256 `8b0440bc…`, el del paquete de la mesa).
