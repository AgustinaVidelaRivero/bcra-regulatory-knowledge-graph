# Enmienda 7 al protocolo entre tandas — la tanda 0 recibe, dentro del re-sellado único, el E3 corregido en dos grupos de unidades

**FIRMADA por la autora el 08/10/2026** (firma por mensaje de la autora; versión para firmar en `08ccdfa`, redactada por la mesa el mismo día
sobre las decisiones de la autora sobre el barrido de límites declarados, filas E3-01 y VAL-03b), con sus tres decisiones al firmar.
Rige desde esta firma: la excepción al §1.4 de la enmienda 5 queda declarada.

Enmienda con fecha al protocolo entre tandas (`docs/protocolo_entre_tandas.md`, FIRMADO en `a304b89`) y a su enmienda 5
(`docs/enmienda5_protocolo_entre_tandas_2026-10-06_grafo_evaluado_sin_cola.md`, FIRMADA el 06/10/2026, `ccd8fad`). Ninguno de los dos se
edita.

## 0. Qué enmienda y por qué

- **Lo que dice lo firmado.** La enmienda 5, §1.4: «La tanda 0 queda como está»; las 74 unidades de su cola no vuelven y la medición de O3
  de U-E3-LISTAS se declara al lado de la cifra de la cola, «sin re-sellar» (decisión de la autora del 06/10/2026, `9bca986`). En la misma
  línea, `docs/insumos_escritura.md` §7, ítem 4: «La tanda 0 no se re-verifica».
- **Lo que decidió la autora el 08/10/2026**, para escalar con el mejor grafo posible:
  - **E3-01:** las 20 unidades de ítems de lista afectadas por el verificador sin la NOTA del ítem (lista sellada `cc6b0cd6…` de O3) se
    re-verifican con el E3 corregido, reusando la verificación de O3 donde sirva, y se re-extraen las 13 cuyo reintento cambió la
    extracción, dentro del re-sellado único; las que estaban en la cola vuelven por el camino del §1.3 de la enmienda 5.
  - **VAL-03b:** si la lectura de las 41 relaciones (Excepcion, exceptua, Operacion) llega a 37 y la enmienda 8 a L-ESQ-R2 se firma, las 21
    unidades con esas relaciones rechazadas por firma en la tanda 0 reciben E3 dentro del re-sellado. Cambia la decisión (a) de la autora
    del 07/10/2026 (`data/experiment/esq/enmienda8_L-ESQ-R2_exceptua_operacion_2026-10-07.md:69-71`: sin E3 en la tanda 0).
- **Por qué una enmienda.** Las dos cosas contradicen el §1.4 de un texto firmado. El principio 9 del plan («el grafo evaluado se sella y no
  se corrige») protege el grafo de B6.3, que todavía no está sellado (`docs/protocolo_dos_grafos.md`, §2): los grafos de la tanda 0 ya se
  van a re-sellar una vez, en el re-sellado único decidido el 07/10/2026 para las correcciones de código. Lo que cambia es que ese
  re-sellado, además de código, lleva llamadas a E3 (y a E1 en los reintentos) en dos grupos chicos de unidades.

## 1. Qué decide

1. **Excepción declarada al §1.4 de la enmienda 5, solo para estos dos grupos.** La tanda 0 sigue sin re-verificarse en todo lo demás. La
   excepción se declara en la tesis y en el pre-registro de la tanda 1 con sus cifras.
2. **E3-01, el flujo** (hechos de la mesa del 08/10/2026, sobre las salidas guardadas):
   - el E1 del intento 0 de las 20 está en la caché, y el E3 de hoy es el de O3 (`prompt_e3.py` igual entre `7fe848c` y HEAD; candado
     `079d2489…` / `66bc8656…`), así que las 20 verificaciones de O3 se reusan si su clave es la que arma el runner (a controlar antes de
     correr; hoy NO VERIFICADO);
   - con los veredictos de O3: 16 unidades se aceptan con el intento 0 (11 de las 13 que habían reintentado y 5 de la cola: `ext::2.6.1.1`,
     `ext::3.5.6.1`, `ext::3.6.1.1`, `ext::3.6.4.2`, `ext::3.13.1.10`); reintentan 3 (`ext::3.6.4.1`, `ext::3.16.2.1`, `ext::3.18.1.1`), con
     E1 y E3 nuevos; `docvig::3.3.2` vuelve a la cola;
   - cada unidad aceptada recibe un registro final nuevo en `finales.jsonl` con su validación final, y el ensamblado del re-sellado toma la
     última versión, como manda el §1.3 de la enmienda 5.
3. **VAL-03b:** E3 de las 21 unidades (41 relaciones; ninguna en la cola y ninguna entre las 20 de E3-01), con la firma ampliada de la
   enmienda 8, solo si se firma.
4. **Quién lo corre y con qué tope.** Ni U-OMISIONES-COD (solo código, sin API) ni la etapa de sello del re-sellado (USD 0). Una etapa
   propia, **R0**, con API, antes del ensamblado del re-sellado único y después de U-OMISIONES-COD. Tope propuesto: **USD 1,50**. Costo
   estimado con las tarifas medidas (E3 0,011911 por llamada, O3; E1 de reintento 0,012072, tanda 0): E3-01, USD 0,072 si se reusan las
   verificaciones de O3 y 0,92 en el peor caso (las 20 reintentan, sin caché de E1); VAL-03b, USD 0,2306.
5. **Lo que cambia con esto, y se declara:**
   - el selftest de claves: su control A3r exige que las 1.054 claves de E3 de los ítems de la tanda 0 estén ausentes «exactamente»; se
     redefine para las 20 (y las 21) que entran, con su nota en la tabla de reprocesamiento;
   - la población de U-LECTURA-ACEPTADAS (2.366 aceptadas) crece al menos en 5, y `ext::2.6.1.2`, que está en su muestra de 60, se leyó
     sobre el reintento: las cifras de L2 se declaran como medidas sobre el grafo sellado anterior;
   - la cola de la tanda 0 baja de 74 (al menos 5 vuelven); la línea de base del pre-registro de la tanda 1 dice las dos cifras, la medida
     en r2b y la del grafo re-sellado;
   - `docs/insumos_escritura.md` §7, ítems 4 y 6, reciben su nota.

## 2. Lo que no cambia

El resto del §1 de la enmienda 5; el principio 9 para el grafo evaluado de B6.3; la regla de que una unidad de la cola vuelve solo si el
verificador la acepta, nunca por una lectura humana sola.

## 3. Decisiones que la autora toma al firmar

1. **El tope de R0.** **Recomendación de la mesa:** USD 1,50.
2. **Si R0 corre aunque la enmienda 8 no se firme.** Entonces corre solo E3-01. **Recomendación de la mesa:** sí.
3. **Qué pasa si una de las 3 que reintentan vuelve a reintentar o termina en la cola.** **Recomendación de la mesa:** la regla de siempre
   (el ratchet y la cola), declarada con su cifra.

**Decididas al firmar (08/10/2026):**
1. **El tope de R0: USD 1,50.**
2. **R0 corre aunque la enmienda 8 no se firme**; entonces corre solo E3-01.
3. **Si una de las 3 que reintentan vuelve a reintentar o termina en la cola, rige la regla de siempre** (el ratchet y la cola),
   declarada con su cifra.

## Firma

FIRMADA por la autora el 08/10/2026 (versión para firmar en `08ccdfa`), con sus tres decisiones. Rige desde esta firma.

## Notas al pie

- **09/10/2026 — La parte de VAL-03b no se ejecuta.** La enmienda 8 a L-ESQ-R2 quedó NO FIRMADA: la lectura de las 41 dio 7 de 41
  (`data/experiment/esq/enmienda8_L-ESQ-R2_exceptua_operacion_2026-10-07.md`, sección del resultado). Por la decisión 2 al firmar, R0
  corre solo E3-01, con el mismo tope de USD 1,50; el E3 de las 21 unidades no corre (USD 0,2306 estimados que no se gastan). El texto
  firmado no cambia.
