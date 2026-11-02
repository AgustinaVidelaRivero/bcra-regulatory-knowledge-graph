# Enmienda 3 al protocolo entre tandas — la clase de reprocesamiento de F05, F10 y F14 sigue la composición real de las claves

**FIRMADA por la autora el 04/10/2026.**

Enmienda con fecha al protocolo entre tandas (`docs/protocolo_entre_tandas.md`, FIRMADO en `a304b89`; texto
firmado: las primeras 398 líneas, sha256 `b23d37c5396a…`). El protocolo no se edita: esta enmienda vive al lado
y se lee junto con él, con la enmienda sobre la cola humana (`8d01b04`) y con la enmienda 2 (`0b98045`).

## 0. Qué enmienda y por qué

- **Lo que dice el protocolo.** §2, eje A (`a304b89:79-85`):
  - «solo código sobre lo guardado (filas F13 a F16: validador, E2 y ensamblado, remisiones, E4 y esqueleto)»;
  - «E1 y E3 de las afectadas (F01 a F05 y F19: texto o marcas de E0, numeración)»;
  - «todo (F06 a F11: prefijo, tool schema, modelo, versión de código, catálogo del prompt): todas las unidades
    pagan E1 y E3».
- **Lo que se encontró.** U-TABLA-REPROC (mandato firmado en `3a4b980`) contrastó cada fila de la tabla de
  reprocesamiento con la composición real de las claves de la caché, con el perfil r2b
  (`data/experiment/mantenimiento/freno_utabla_reproc.md` y `code/selftest_clave_cache.py`, sin commit al
  04/10/2026). En tres filas la clave no se comporta como dice el protocolo:
  - **F05**, páginas, id, sha256 y conteos de una unidad sin cambio de texto. No mueve ninguna clave de E1 ni
    de E3 (variaciones R05 y R06): ni el mensaje de E1 ni el de E3 leen esos campos. Se rehacen E2 y el
    ensamblado, en código.
  - **F10**, prompt de E3 o su modelo. Mueve la clave de E3 de todas las unidades y ninguna de E1 (R16 y R17).
    Un cambio en los calibradores frena antes de armar el pedido, por el candado del prefijo de E3 (R22d;
    `e3_verificador/prompt_e3.py`, `924ef4d`).
  - **F14**, validador. Con el perfil r2b hay dos. `validador_e1` corre antes de E3 y su salida es el mensaje
    de E3 (R18: cambia la clave de E3 y no la de E1). Y desde `4aa92c7`, posterior a la firma del protocolo, el
    ensamblado r2b deja entrar solo lo que vio E3 (`pyd_r2/code/validador_r2.py`, «lo que E3 no vio no entra»).
    Un cambio en `validador_e1` no llega al grafo sin volver a correr E3 en las unidades cuya salida validada
    cambia.
- **Verificación.** Corrí el selftest dos veces sobre una copia: da el mismo resultado que el del freno, byte
  a byte. Y repetí las pruebas con un programa propio, que arma los pedidos con el código de la cadena, sobre
  las 2.439 unidades de `salida_tanda0_r2b/`:
  - con las páginas o los metadatos cambiados, cambian 0 claves de E1 y 0 de E3;
  - con el texto de sistema o el modelo de E3 cambiados, cambian las 2.439 claves de E3;
  - con un espacio de más en la unidad de un calibrador, la importación del prompt de E3 frena;
  - con la salida validada cambiada, cambia la clave de E3 y no la de E1, en 59 de 59 salidas reales del
    brazo nuevo de la pareada de P4 (`data/experiment/prompt_r2/p4/`, sin commit al 04/10/2026).
- **Por qué una enmienda.** Cambia una regla de un texto firmado.

## 1. Qué decide

1. **F05 pasa a «solo código sobre lo guardado».** Entre las filas de E0, el rango de «E1 y E3 de las
   afectadas» queda en F01 a F04 y F19.
2. **F10 sigue en la clase «todo» y paga E3 de todas las unidades**, más los reintentos de E1 donde cambie el
   feedback de E3. E1 sale de la caché: no pagan E1 y E3 todas las unidades.
3. **F14, `validador_e1`, pasa a «E1 y E3 de las afectadas».** Se rehace la validación en código y pagan E3
   las unidades cuya salida validada cambia. E1 sale de la caché.
4. **`validador_r2`, en el ensamblado, queda en «solo código sobre lo guardado», como fila F14b.**
5. El eje A del §2 se lee así:
   - solo código sobre lo guardado: F05, F13, F14b, F15 y F16;
   - E1 y E3 de las afectadas: F01 a F04 y F19, por E0, y F14, por el validador de E1;
   - todo: F06 a F11; en F10 pagan E3 todas las unidades y E1 solo en los reintentos donde cambia el feedback.
6. Las filas que la tabla suma con el perfil r2b llevan su clase en la tabla
   (`data/experiment/mantenimiento/tabla_reprocesamiento.md`, §3). Esta enmienda cambia solo F05, F10 y F14.

## 2. Qué no cambia

- El texto del protocolo, sus notas, la enmienda sobre la cola humana y la enmienda 2.
- Las definiciones de las cuatro clases y el eje B.
- El costo de ninguna corrida ya hecha. En F05 no pagaba ninguna unidad en ninguna de las dos lecturas: cambian
  la clase y el principio declarados.
- La fila F13: la trata la fe de erratas de la enmienda 2, de la misma fecha.

## 3. La regla de cruce para F14

La regla de cruce del §2 (`a304b89:97-100`) dice que un hallazgo de clase «E1 y E3 de las afectadas» se corrige
entre tandas cuando es por E0. Un cambio de `validador_e1` entra ahora a esa clase y no es por E0. Los cambios
de la clase F14 (`validador_e1`) se corrigen entre tandas igual que los de E0: se vuelven a correr E1 y E3 solo
de las unidades afectadas, con su costo declarado antes de correr. Como dice el punto 3 del §1, E1 sale de la
caché.

**Nota del 04/10/2026.** En la versión commiteada en `0cb0c70` (sha256 `5023adc0ae2d…`), este §3 se titulaba
«Qué no decide» y dejaba la regla a decisión de la autora con el primer caso. La autora la decidió el
04/10/2026 y firmó la enmienda con este cambio. La fecha de la firma no cambia, y el resto del texto es el de
`0cb0c70`.

## Firma

FIRMADA por la autora el 04/10/2026. Rige desde esta firma.
