# Enmienda 2 al pre-registro de la evaluación por tripletas — el solapamiento con la lectura de la desambiguación y la etapa T sin la tanda 0

**FIRMADA por la autora el 19/10/2026, tal cual** (por mensaje recibido a las 12:13:24; hoja de ruta de la mesa, §178), antes del
sorteo de la etapa T. Rige desde esta firma. La versión para firmar está en el paquete de la mesa
(`decisiones_140_mesa/tripletas/para_firmar/`, sha256 `98931dae…`). El texto firmado son las líneas anteriores a «## Firma»: no se edita
después y recibe notas fechadas debajo de esa sección.

Enmienda con fecha a `docs/preregistro_evaluacion_tripletas.md`, FIRMADO por la autora el 07/10/2026 en `4afbe51`. El sha256 del texto
firmado es `8ce611ba…`; el archivo de HEAD `ca5b39fd` es `ffaea196…`, con las notas fechadas al pie. Va al lado de la enmienda 1 (vía de
umbrales, firmada el 08/10/2026). **Ni el pre-registro ni la enmienda 1 se editan:** al firmarse, el pre-registro recibe una nota fechada
al pie que remite a esta.

La redactó la mesa sobre la decisión 9 de la autora del 17/10/2026, recibida a las 11:31:33 (hoja de ruta de la mesa, §140), tal cual:
«Tripletas: el solapamiento con V y con el control de T se declara y no se excluye. T informa las tres cifras de tu §7.»

## 0. Por qué

- **Una lectura nueva sobre la tanda 0.** U-MED-DESAMB, la medición de la desambiguación del grafo, tiene su diseño sellado
  (`data/experiment/med_desamb/diseno_sellado_med_desamb_2026-10-17.md`, sha256 `05445091…`).
  - La autora lee 52 relaciones de sujeto (`aplica_a` y `ejecuta`) y 12 calibradores del grafo sin cola diez rs1 (`61dd1b69…`).
  - Ese grafo tiene los cinco documentos del grafo de la etapa V (cap, cla, ext, pro y ric).
  - La población de V incluye `aplica_a` y `ejecuta` (§3.1).
  - Así, una arista de V, o del control a ciegas de 30 de T, puede ser una relación que la autora ya leyó.
- **Unas reglas elegidas mirando la tanda 0.** Las reglas S1, S2 y C1 de esa unidad se deciden con lecturas de la tanda 0. Si pasan,
  entran al grafo evaluado con la re-aplicación única del código antes de su sello (enmienda 8 al protocolo, R3).
  - Así, la precisión de T sobre las aristas de la tanda 0 no es una estimación independiente de las reglas.
  - Sobre las aristas de los demás documentos, sí.

## 1. El solapamiento: se declara y no se excluye

- **La regla** es la del pre-registro para U-LECTURA-ACEPTADAS (`:41-42`), la misma que la enmienda 1 usa para la ficha común (§11).
- **Un caso de solapamiento** es una arista de la muestra de V (100 más el pool de 20) o del control de 30 de T, de predicado `aplica_a` o
  `ejecuta`, cuya procedencia incluye el `chunk_id` de un ítem leído en U-MED-DESAMB (de los 64), con el mismo predicado y la misma norma
  como extremo de contenido.
- **Cuándo se cuenta:** al sortear V y al sortear el control de T. El acta de cada sorteo lleva el conteo y la lista de las aristas
  solapadas, con el ítem de U-MED-DESAMB al que corresponden.
- **Ninguna arista sale de la muestra por esto.** Las cifras se informan como están, con el conteo al lado.

## 2. La etapa T: tres cifras de precisión

Sobre la misma muestra de 400 aristas del grafo evaluado (§7), sin leer nada más:
1. **La precisión de todo,** como hoy: la cruda y la ponderada por predicado (§3.6).
2. **La precisión sin las aristas de la tanda 0,** con los dos mismos estimadores.
   - Salen las aristas cuyo extremo de contenido tiene su procedencia primaria en uno de los diez documentos de la tanda 0: cap, cla,
     ext, pro, ric, ctacte, lingob, pagjub, polcre y docvig.
   - El extremo de contenido es el nodo fuente, como en la asignación de una arista a su nodo fuente del pre-registro de la tanda 1, §5.4
     bis, salvo en `ejecuta`, donde la fuente es un Sujeto y vale el destino.
   - Los pesos W_h se recalculan con los N_h del grafo evaluado sin esos documentos.
3. **La precisión de `aplica_a` sola,** cruda con Wilson, con y sin las aristas de la tanda 0.

**Qué se declara:**
- el n de cada subconjunto, que es menor que 400 y se informa;
- las cifras 2 y 3 son restricciones de la misma muestra, no muestras nuevas;
- si un estrato de predicado se queda con menos de 5 aristas en un subconjunto, se informa con su fracción cruda y se agrupa en «otros»
  para la varianza, como dice el §3.6.

## 3. Qué no cambia

- **Las once decisiones del §10** del pre-registro.
- **La etapa V entera:** su grafo, su muestra, el juez y su validación.
- **La vía de cobertura.**
- **Los tamaños** (100 en V, 400 en T, el control de 30), los estimadores, el juez, sus calibradores y su umbral de validez.
- **Los topes:** USD 35 en V y USD 55 en T. Esta enmienda no agrega lecturas ni llamadas.
- **La enmienda 1 entera.** Su etapa T ya mide sobre los documentos fuera de `data/experiment/esq/documentos_excluidos_evaluacion_final.json`,
  y esta enmienda no toca la vía de umbrales.
  - Se controló que no choque con su §11 (la ficha común, con la misma regla de solapamiento) ni con su §13 (lo que no cambia de la vía
    de precisión, que esta enmienda tampoco cambia: agrega dos cifras sobre la misma muestra).
  - Tampoco choca con las notas fechadas del pre-registro: la del 15/10/2026 sobre quién adjudica y la del re-sellado único.

## Firma

FIRMADA por la autora el 19/10/2026 a las 12:13:24 (por mensaje; hoja de ruta de la mesa, §178), tal cual. Rige desde esta firma.
