# Supuestos del sitio del BCRA: declaración y línea de base

U-MANT, etapa M2 (a y b). El job de actualización y E0 dan por sentadas siete
cosas sobre lo que publica el sitio. Las declaro acá con su fuente, su valor
de línea de base, cómo las mido y qué dispara el aviso. El control que las
mide es `control_sitio.py`; la línea de base es `linea_base.json`.

## Línea de base

Medida sin red sobre los artefactos guardados:

- el índice crudo congelado (`data/experiment/escalado_prep/indice_oficial_raw.json`)
  y el de la corrida del 2026-09-07
  (`data/experiment/job_actualizacion/corridas/2026-09-07/indice_crudo.json`).
  Son byte a byte idénticos (sha256 `91dc9f86…` los dos);
- los 157 PDFs congelados (152 en `escalado_prep/pdfs/` y 5 en
  `data/experiment/subset/`, vía `lib_job.linea_base()`) y los 157 de la
  corrida del 2026-09-07. 146 son idénticos por sha256. Los otros 11 son los TOs
  con contenido modificado de esa corrida, y se miden en las dos versiones.

La referencia del control es el último estado observado del sitio, es decir,
el índice y los PDFs de la corrida del 2026-09-07. Construí la línea de base
con el comando de abajo y corrí la construcción tres veces: las tres salidas
son byte a byte idénticas (sha256 `f274f77e…`).

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/control_sitio/control_sitio.py --construir-linea-base data/experiment/mantenimiento/control_sitio/linea_base.json
```

## Los siete supuestos

| Id | Supuesto | Fuente | Línea de base | Cómo se mide | Qué dispara el aviso |
|---|---|---|---|---|---|
| S1 | Forma de la respuesta del endpoint del índice (`/api/endpoints/ordenamiento-y-resumenes.php?lang=es`) | `job_actualizacion/code/correr_job.py:41`, `:165-174` | JSON con claves de nivel superior `lang`, `regimenes_informativos`, `success`, `textos_ordenados`; `success` verdadero; las dos listas presentes | parseo de los bytes crudos | no es JSON, no es un objeto, cambia el conjunto de claves de nivel superior, `success` no es verdadero o falta una de las dos listas. Si S1 se rompe, S2 a S4 no se miden |
| S2 | Cuatro claves de cada entrada: `titulo`, `titulo_truncado`, `archivo`, `url` | `job_actualizacion/diseno_job_actualizacion.md:100-103`; `lib_job.py:92-110` | 158 de 158 entradas con exactamente esas cuatro | conjunto de claves de cada entrada | alguna entrada con una clave de menos o de más |
| S3 | Cantidad de entradas y de TOs únicos | `diseno_job_actualizacion.md:67-71` | 103 en `textos_ordenados` y 55 en `regimenes_informativos`; 158 entradas, 157 URLs únicas; 1 duplicada (`t-optico.pdf`); 157 ids (regla `lib_job.id_corto`, dedup por URL) | conteo y conjunto de ids con la regla del job | cambia cualquiera de esos números o el conjunto de ids (el aviso lista altas y bajas) |
| S4 | Patrón de URL de los PDFs | índice congelado | 158 de 158 con `https://www.bcra.gob.ar/archivos/Pdfs/Texord/<archivo>`, con `<archivo>` igual a la clave `archivo` y extensión `.pdf` (sin distinguir mayúsculas: dos son `.PDF`) | regex `^https://www\.bcra\.gob\.ar/archivos/Pdfs/Texord/(?P<archivo>[^/]+)$` | alguna URL fuera del patrón |
| S5 | Acierto de la regex de portada de `lib_job` (`RE_PORTADA`, `:64-66`) | `lib_job.procedencia` | 94 de 157 TOs con acierto en las 3 páginas de cabecera | `lib_job.procedencia`, sin cambios | un TO que tenía acierto lo pierde |
| S6 | Acierto de la regex de pie de `lib_job` (`RE_PIE`, `:69-71`) | `lib_job.procedencia` | 152 de 157 TOs con al menos una página de sondeo con acierto (3 de cabecera y hasta 5 de cuerpo, `lib_job.paginas_de_sondeo`) | `lib_job.procedencia`, sin cambios | un TO que tenía acierto lo pierde |
| S7 | Acierto de los marcadores de página de E0 (`RE_PIE` de `e0_chunking/e0_lib.py:224-229`) | `e0_lib.separar_encabezado_pie` (`:536`) | 153 de 157 TOs con al menos una página con marcador; 880 de 1.076 páginas de sondeo con texto | sobre las mismas páginas de sondeo: líneas armadas como `e0_lib.extraer_lineas` (palabras agrupadas por altura con `TOL_TOP` 2,0) y acierto si E0 descartaría al menos la última línea como pie | en un TO que tenía marcadores, la fracción de páginas con marcador cae por debajo de la mitad de la de la línea de base |

Los supuestos son siete y no cinco porque separé lo que el mandato agrupa. En
«endpoint y claves», la forma de la respuesta (S1) es una cosa y las claves de
cada entrada (S2), otra. En «regex de portada y pie», la portada (S5) es una y
el pie (S6), otra. Así cada alteración del selftest dispara un solo aviso.

## Qué no mide el control

- No compara contenido: un PDF que cambió con el mismo formato no rompe ningún
  supuesto. Eso lo detecta el job, por el sha256.
- S5 a S7 se miden sobre las páginas de sondeo del job (3 de cabecera y hasta
  5 de cuerpo). Un cambio de formato que afecte solo a otras páginas puede no
  verse.
- La medición por sha reutiliza la de la línea de base cuando el PDF no
  cambió (`control_sitio.py`, `--remedir-todo` la recalcula).

## Hallazgos de la línea de base

1. **Los cuatro TOs que el diseño del job declara «sin procedencia en ninguna
   forma» sí imprimen el pie.** El diseño lo afirma en `diseno_job_actualizacion.md:345-349`:
   `ri_cc`, `ri_ccna`, `ri_ccpnp`, `ri_spi`. En la práctica, `RE_PIE` no
   reconoce el ordinal «1ª» (U+00AA) de los tres primeros ni el «1a..» de
   `ri_spi`. Por ejemplo, la página 1 de `ri_cc` dice
   «Versión: 1ª. COMUNICACIÓN “A“ 4468 Página 1». Con el quinto TO sin acierto
   (`optico`, que es una lista de Comunicaciones sin pie), son los 5 de S6.
2. **E0 no reconoce el pie de `fabcra`, `horari` y `ribspc`** en las páginas
   sondeadas, aunque el pie existe:
   - `fabcra` trae la fecha «28/03/20206», con el año de cinco dígitos;
   - `horari` y `ribspc` traen la fecha con puntos («18.05.00», «23.10.03»);
   - `ribspc` escribe además «Página:1».

   La regex de fecha de E0 es `^\d{1,2}/\d{1,2}/\d{2,4}$`, así que E0 no
   descarta la última línea y el pie entero queda en el texto de esas
   páginas. Con `optico`, son los 4 TOs sin marcador de S7. Los tres son de la
   partición del corpus escalado, no de la tanda 0.
3. Entre la versión congelada y la del 2026-09-07 cambian solo tres
   mediciones de portada (`capmin`, `cladeu`, `optico`: la Comunicación de la
   portada avanza) y una de S7 (`ri_cm`: 8 → 7 páginas con marcador de 8).
   Ninguna rompe un supuesto (`linea_base.json`, clave `corrida_vs_congelado`).

## Selftest

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/control_sitio/selftest_control_sitio.py --trabajo <dir fuera del repo> --out data/experiment/mantenimiento/control_sitio/selftest_control_sitio.json
```

El selftest corre 8 casos sobre copias en un directorio fuera del repo; el
caso base y las 7 alteraciones dan lo esperado. El caso base, sin alteración y
re-midiendo todo, sale con código 0 y sin aviso. Cada alteración dispara su
aviso y solo el suyo, con código 1:

| Alteración | Aviso |
|---|---|
| A1, entrada sin `titulo_truncado` | S2 |
| A2, una entrada menos | S3 |
| A3, URL con `/Pdfs/Texord/` en lugar de `/archivos/Pdfs/Texord/` (la forma de 2 filas `TO_actual` de `data/raw/manifiesto.csv`) | S4 |
| A4, PDF sin portada | S5 |
| A5, PDF sin marcadores de E0 | S7 |
| A6, respuesta sin `textos_ordenados` | S1 |
| A7, PDF sin el pie «Versión … COMUNICACIÓN» | S6 |

Detalles del selftest:
- Los PDFs alterados salen de la copia de `capmin` de la corrida.
- A4 le quita la página 1.
- A5 y A7 le quitan, con pypdf, bloques de texto del pie, identificados por
  su altura y su texto.
- La réplica de líneas de E0 del control coincide con `e0_lib.extraer_lineas`
  en las páginas de sondeo de `ribspc`, `ri_spi` y `snp_psp`.
- Dos corridas dan el mismo JSON byte a byte.
