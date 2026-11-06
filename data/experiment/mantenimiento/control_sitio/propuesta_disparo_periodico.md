# Propuesta de disparo periódico del control del sitio, y alcance de M3

U-MANT, etapa M2 (f). Es una propuesta para que la autora decida: no se
instala nada en M2 (mandato U-MANT, decisión 5).

## Qué corre en cada disparo

El disparo es un runner que hace tres cosas:
1. Trae el índice y, según la opción, los PDFs, con los parámetros de
   cortesía del job (`job_actualizacion/diseno_job_actualizacion.md`, §6):
   - un pedido cada 0,5 s, sin concurrencia;
   - 60 s de timeout y 3 reintentos;
   - User-Agent propio sin datos personales.
2. Escribe lo traído en `control_sitio/corridas/<fecha>/`.
3. Llama a `control_sitio.py`, que no toca la red.

Códigos de salida:
- 0: supuestos en verde;
- 1: aviso, con `aviso.md` escrito;
- 3: el sitio no respondió (lo agrega el runner de M3; mismo código que usa
  el job cuando el endpoint no responde, `correr_job.py:160-165`).

## Periodicidad

Propongo mensual, por el diseño del job (`diseno_job_actualizacion.md`,
§2.a.6, `:229-247`):
- el volumen de una corrida es chico;
- una ventana de un mes deja un cambio adjudicable a un puñado de
  Comunicaciones.

Lo que midió la primera corrida, cada fracción con su ventana y sin
combinarlas (plan, fila U-JOB-ACT):
- 8 de 152 TOs cambiaron en ~3,5 semanas;
- 3 de los 5 de desarrollo cambiaron en ~4 meses.

Si el job de actualización también corre mensual, el control puede correr
sobre la corrida del job y no agrega ningún pedido al sitio.

## Opciones de alcance por corrida

| | Pedidos por corrida | Supuestos | Bytes |
|---|---|---|---|
| (i) solo el índice | 1 (hasta 3 intentos si falla) | S1 a S4 | ~39 KB (índice crudo de la corrida del 2026-09-07: 39.143 bytes) |
| (ii) índice y PDFs, con pedidos condicionales | 158 = 1 + 157 | S1 a S7 | solo los PDFs que cambiaron. Con 304 no hay cuerpo y se reutiliza la medición por sha |

Detalles de la opción (ii):
- Cada pedido de PDF lleva `If-None-Match` con el `ETag` y
  `If-Modified-Since` con el `Last-Modified` de la última corrida. Los 157 de
  la corrida del 2026-09-07 tienen los dos (`observaciones.json`, campo
  `cabeceras`).
- Un 304 cuenta como «sin cambio». Un 200 se verifica por sha256: la cabecera
  decide si se baja, el sha decide si cambió (diseño del job, §6).
- Que el sitio responda 304 es NO VERIFICADO. Si no lo hace, los 157 vuelven
  con 200 y cuerpo completo: ~166 MiB y el mismo número de pedidos.

## Dónde correría

**(a) Programador de tareas de la máquina local** (en macOS, un LaunchAgent
de launchd con intervalo mensual).
- Qué necesita: la máquina encendida y con red el día del disparo, el repo
  clonado y el `.venv`. No hay credenciales: el sitio es público.
- Qué pasa si la máquina no está disponible: si estaba dormida, launchd
  corre la tarea al despertar; si estaba apagada, la corrida se pierde. Ese
  comportamiento es NO VERIFICADO en esta máquina.
- Dónde quedan las corridas: en `control_sitio/corridas/<fecha>/` del repo
  local, sin commit automático. Versionarlas es decisión de la autora.
- A dónde llega el aviso y quién lo ve: el código de salida y `aviso.md`
  quedan en la corrida. Para que alguien lo vea sin abrir el repo, la tarea
  puede mostrar una notificación del sistema cuando el código no es 0. Lo ve
  la autora, en esa máquina.

**(b) Tarea programada fuera de la máquina** (por ejemplo, un workflow
programado del servicio que aloja el repo).
- Qué necesita:
  - el workflow versionado en el repo, que es un archivo nuevo fuera de este
    mandato;
  - Python con las dependencias del control (pdfplumber, pypdf);
  - permiso de lectura del repo, y de escritura solo si las corridas se
    commitean (token con permiso de contenidos).
- Dónde quedan las corridas: como artefactos de la ejecución, con retención
  limitada, o commiteadas por el workflow.
- A dónde llega el aviso y quién lo ve: la ejecución termina con código
  distinto de 0 y el servicio notifica por correo a la cuenta dueña.
- Riesgos NO VERIFICADOS:
  - que el sitio del BCRA responda a pedidos desde la infraestructura del
    servicio;
  - que el servicio no deshabilite los workflows programados de un repo sin
    actividad;
  - si el repo es público o privado.

## Qué pasa si una corrida falla o no puede preguntar al sitio

- **El índice no responde** (agotados los 3 intentos): la corrida se aborta
  antes de pedir un solo PDF, con código 3 y un `corrida_fallida.md` con el
  error. No se registra como supuesto roto: «no pude preguntar» no es «el
  sitio cambió» (diseño del job, §6).
- **El índice responde, pero no es JSON o le faltan las listas:** acá difiero
  del job, que en ese caso también sale con 3 (`correr_job.py:166-175`). La
  respuesta cruda se guarda y el control la mide: es S1 roto, con código 1 y
  aviso, porque el sitio respondió algo distinto. Tampoco se pide ningún PDF.
- **Un PDF falla:** queda «no medido» en esa corrida. No es aviso, y se
  reintenta en la siguiente.
- **Latido**, propuesta:
  - cada corrida exitosa deja su fecha en `control_sitio/corridas/ultima_ok.txt`;
  - si la última exitosa tiene más de 45 días, la corrida siguiente, aunque
    falle, escribe un aviso «control sin corrida exitosa desde <fecha>»;
  - así, un disparo que falla en silencio termina por avisar;
  - si el disparo no corre nunca, solo lo detecta quien mire esa fecha: el
    runner puede imprimirla con una opción de estado.

## Recomendación, para la decisión de la autora

**Disparo periódico:**
- opción (a), mensual, solo el índice: 1 pedido, sin credenciales ni archivos
  nuevos fuera de `mantenimiento/`;
- los supuestos S5 a S7 se controlan cada vez que corre el job de
  actualización, sobre sus PDFs, sin pedidos adicionales;
- con el latido de 45 días.

**Alcance de M3:** propongo la opción (ii), índice y 157 PDFs con pedidos
condicionales: 158 pedidos, 1 al índice y 157 a PDFs.
- Es la única que ejercita S5 a S7 contra el sitio.
- Los PDFs que vuelvan con 200 van al scratchpad, no al repo, porque el
  mandato no autoriza tocar el `.gitignore`.
- En la corrida del repo quedan el índice crudo, `resultado_control.json` y,
  si corresponde, `aviso.md`.
- Si la autora prefiere la opción (i), M3 es 1 pedido.
