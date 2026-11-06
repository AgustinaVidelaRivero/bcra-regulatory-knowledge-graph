# Corrida del control del sitio del BCRA — 2026-10-02

U-MANT, etapa M3. Es la única corrida con red autorizada por la autora para
esta unidad, con el alcance «índice y 157 PDFs con pedidos condicionales». Todo
lo de abajo sale de los archivos de esta carpeta:
- `resumen_corrida.json`;
- `pedidos.json`;
- `resultado_control.json`;
- `clasificacion_cambios.json`.

Costo de API: USD 0.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/control_sitio/correr_control_sitio.py --modo indice-y-pdfs --autorizado-red
```

## Pedidos

- **158 pedidos lógicos** (1 al índice y 157 a PDFs) y **158 intentos HTTP**:
  ningún reintento, ningún error, sin modo lento. Duración de pared: 263,4 s.
- **Cortesía**, con los valores de `correr_job.py:47-54`:
  - un pedido cada 0,5 s, uno por vez;
  - 60 s de timeout y 3 intentos por pedido;
  - User-Agent «AcademicResearchBot/1.0 (control de supuestos del sitio de un
    corpus regulatorio; investigacion academica)».
- **Índice:** HTTP 200, 39.143 bytes, sha256 `91dc9f86…`. Es byte a byte
  idéntico al congelado y al del 2026-09-07.
- **PDFs:** los 157 pedidos llevaron `If-None-Match` e `If-Modified-Since` con
  el ETag y el Last-Modified de la corrida del 2026-09-07.
  - 138 volvieron con 304.
  - 19 volvieron con 200, y los 19 tienen un sha256 distinto del de esa
    corrida. Se guardaron en `pdfs/`, ignorados por `.gitignore:35`; el sha de
    cada uno está en `pedidos.json`. Suman 43.621.088 bytes.

## Control de los supuestos

**Veredicto OK: los siete supuestos en verde, sin aviso** (`resultado_control.json`):
- S1 a S4 sobre el índice.
- S5 a S7 sobre los 19 PDFs nuevos, medidos uno por uno.
- Los 138 con 304 son, según el servidor, los mismos del 2026-09-07, que ya
  estaban en verde en la línea de base.

## TOs que cambiaron, clasificados con la tabla de M1

**Desde la corrida del 2026-09-07 cambiaron 19:** `capmin`, `ctacte`,
`depaho`, `depinv`, `excbio`, `expaef`, `finsec`, `gerc`, `optico`, `polcre`,
`ri_cm`, `ri_dsf`, `ri_icpipsp`, `ri_psprca`, `ri_rml`, `seggar`, `servco`,
`snp_tr_nc` y `tasint`.

**Contra el corpus congelado, sobre el que se construyó la E0 guardada,
difieren 23.** Cada uno se clasificó con la tabla de M1 según en qué páginas
del PDF congelado cae el cambio:
- `F18b`, el cambio cae en páginas que usan unidades de E0: 15;
- `F18b + F05`, lo mismo con otra cantidad de páginas: 5 (`capmin`, `excbio`,
  `expaef`, `optico`, `ri_oc`);
- `F18a`, el cambio cae solo en páginas que ninguna unidad usa: 3 (`ctacte`,
  `seggar`, `tasint`).

Las páginas de cuerpo se toman de las unidades de E0 guardadas: la E0 de la
tanda 0 para sus diez TOs y la partición del corpus escalado para el resto
(`correr_control_sitio.py`, `paginas_de_unidades`).

Conjunto de desarrollo, ventana desde la descarga de mayo: **cuatro de los
cinco cambiaron**.
- `capmin` (`cap`): de 204 a 207 páginas, 44 páginas viejas tocadas, 37 de
  unidades. F18b + F05.
- `cladeu` (`cla`): 5 páginas tocadas, 1 de unidades. F18b. Volvió con 304:
  no cambió desde el 2026-09-07.
- `excbio` (`ext`): de 201 a 213 páginas, 130 tocadas, 120 de unidades. F18b
  + F05. Es la primera vez que cambia.
- `ri_cm` (`ric`): 14 tocadas, 14 de unidades. F18b.
- `pusf` (`pro`) no cambió.

TOs nuevos de la tanda 0, ventana desde el 2026-08-13:
- `ctacte`: F18a, 1 página tocada y ninguna de unidades;
- `polcre`: F18b, 10 tocadas, 5 de unidades.

Del resto del corpus de 152, en la misma ventana, difieren 17.

## Qué no dice esta clasificación

- **F18a** es «nada» solo si E0 sobre el PDF nuevo devuelve las mismas
  unidades byte a byte. Eso es NO VERIFICADO: no corrí E0 sobre los PDFs
  nuevos.
- **F18b** dice que hay que re-extraer, no cuántas unidades. Cuántas lo dice
  la clave de cada unidad tras correr E0 (procedimiento de empalme, paso 2),
  y eso es de U-SUBGRAFO.
- **El diff por página es un localizador**, no un comparador de sentido
  (`job_actualizacion/corridas/2026-09-07/reporte.md:91-99`).
- **El corpus no se actualizó.** El inventario, los manifiestos y los PDFs
  congelados no se tocaron (mandato U-MANT, decisiones 2 y 3).
