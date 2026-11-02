# Formato del grafo

El grafo publicado es `data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz`: un JSON comprimido con gzip, con dos listas, `nodes` y `edges`.

| | Cantidad |
|---|---:|
| Nodos | 37168 |
| Aristas | 128552 |
| Tipos de nodo distintos (`type`) | 10 |
| Relaciones distintas (`relation`) | 19 |
| Documentos de origen nombrados en la procedencia | 133 (129 PDF y 4 JSON) |

## Nodos

Cada nodo tiene `id`, `label`, `type`, `properties` y su procedencia (`provenance` y `provenances`). Claves presentes,
con la cantidad de veces que aparecen en todo el grafo:

| Clave | Apariciones |
|---|---:|
| `nodes[].fuera_de_lista` | 449 |
| `nodes[].id` | 37168 |
| `nodes[].label` | 37168 |
| `nodes[].originales` | 653 |
| `nodes[].originales.frecuencia` | 617 |
| `nodes[].originales.tipo` | 36 |
| `nodes[].properties` | 37168 |
| `nodes[].properties.alias` | 37 |
| `nodes[].properties.archivo` | 128 |
| `nodes[].properties.codigo` | 384 |
| `nodes[].properties.colision_cross_to` | 116 |
| `nodes[].properties.cuarentena` | 656 |
| `nodes[].properties.descripcion` | 35783 |
| `nodes[].properties.frecuencia` | 638 |
| `nodes[].properties.instancia_de` | 5 |
| `nodes[].properties.materia` | 128 |
| `nodes[].properties.nivel` | 801 |
| `nodes[].properties.numero` | 76 |
| `nodes[].properties.padre_desde_sugerencia_modelo` | 52 |
| `nodes[].properties.padre_por_defecto` | 15 |
| `nodes[].properties.padre_por_defecto_generico` | 12 |
| `nodes[].properties.padre_sugerido` | 656 |
| `nodes[].properties.parte_de` | 1 |
| `nodes[].properties.termino` | 3720 |
| `nodes[].properties.tipo` | 24142 |
| `nodes[].properties.umbrales` | 4108 |
| `nodes[].properties.umbrales[].base` | 639 |
| `nodes[].properties.umbrales[].base_destino` | 44 |
| `nodes[].properties.umbrales[].base_no_resuelta` | 595 |
| `nodes[].properties.umbrales[].base_via` | 44 |
| `nodes[].properties.umbrales[].comparacion` | 4660 |
| `nodes[].properties.umbrales[].dias_tipo` | 625 |
| `nodes[].properties.umbrales[].fuera_de_lista` | 127 |
| `nodes[].properties.umbrales[].moneda` | 156 |
| `nodes[].properties.umbrales[].origen` | 4660 |
| `nodes[].properties.umbrales[].originales` | 2 |
| `nodes[].properties.umbrales[].originales.chunk_id` | 2 |
| `nodes[].properties.umbrales[].originales.regla_comparacion` | 2 |
| `nodes[].properties.umbrales[].originales.tabla` | 2 |
| `nodes[].properties.umbrales[].originales.unidad_desde_rotulo` | 2 |
| `nodes[].properties.umbrales[].regla_comparacion` | 4660 |
| `nodes[].properties.umbrales[].tramo` | 4660 |
| `nodes[].properties.umbrales[].tramo_verificado` | 4660 |
| `nodes[].properties.umbrales[].unidad` | 2952 |
| `nodes[].properties.umbrales[].valor` | 2952 |
| `nodes[].properties.umbrales[].verificado_en_tabla` | 285 |
| `nodes[].properties.version` | 127 |
| `nodes[].properties_no_definidas` | 820 |
| `nodes[].properties_no_definidas.abreviado` | 29 |
| `nodes[].properties_no_definidas.acunador` | 2 |
| `nodes[].properties_no_definidas.acunadora` | 1 |
| `nodes[].properties_no_definidas.alcance` | 3 |
| `nodes[].properties_no_definidas.alcance_direccional` | 1 |
| `nodes[].properties_no_definidas.aleacion` | 2 |
| `nodes[].properties_no_definidas.aniversario` | 1 |
| `nodes[].properties_no_definidas.aporte_por_entidad` | 1 |
| `nodes[].properties_no_definidas.año_acunacion` | 1 |
| `nodes[].properties_no_definidas.base_calculo` | 2 |
| `nodes[].properties_no_definidas.calidad` | 9 |
| `nodes[].properties_no_definidas.calificacion` | 1 |
| `nodes[].properties_no_definidas.campos_totales` | 1 |
| `nodes[].properties_no_definidas.cantidad` | 3 |
| `nodes[].properties_no_definidas.cantidad_acunada` | 4 |
| `nodes[].properties_no_definidas.cantidad_acunada_1` | 1 |
| `nodes[].properties_no_definidas.cantidad_acunada_2` | 1 |
| `nodes[].properties_no_definidas.cantidad_acuñada` | 1 |
| `nodes[].properties_no_definidas.cantidad_mercado_internacional` | 1 |
| `nodes[].properties_no_definidas.cantidad_mercado_local` | 1 |
| `nodes[].properties_no_definidas.canto` | 9 |
| `nodes[].properties_no_definidas.capacidad_reafectacion` | 1 |
| `nodes[].properties_no_definidas.caracter` | 7 |
| `nodes[].properties_no_definidas.caracteristica` | 1 |
| `nodes[].properties_no_definidas.caracteristica_especial` | 1 |
| `nodes[].properties_no_definidas.carácter` | 1 |
| `nodes[].properties_no_definidas.ceca` | 3 |
| `nodes[].properties_no_definidas.codigo` | 14 |
| `nodes[].properties_no_definidas.color_predominante` | 3 |
| `nodes[].properties_no_definidas.colores_predominantes` | 1 |
| `nodes[].properties_no_definidas.composicion_encabezado` | 1 |
| `nodes[].properties_no_definidas.condicion` | 1 |
| `nodes[].properties_no_definidas.condición_de_retorno` | 1 |
| `nodes[].properties_no_definidas.consecuencia` | 16 |
| `nodes[].properties_no_definidas.contenido` | 2 |
| `nodes[].properties_no_definidas.copia_nota_e3` | 298 |
| `nodes[].properties_no_definidas.copia_nota_e3.descripcion` | 230 |
| `nodes[].properties_no_definidas.copia_nota_e3.label` | 94 |
| `nodes[].properties_no_definidas.criterios_de_definicion` | 1 |
| `nodes[].properties_no_definidas.cuantificador` | 3 |
| `nodes[].properties_no_definidas.decreto_referencia` | 1 |
| `nodes[].properties_no_definidas.denominacion` | 6 |
| `nodes[].properties_no_definidas.descripcion_anverso` | 1 |
| `nodes[].properties_no_definidas.descripcion_reverso` | 1 |
| `nodes[].properties_no_definidas.destinatario` | 2 |
| `nodes[].properties_no_definidas.destinatarios` | 2 |
| `nodes[].properties_no_definidas.diametro` | 8 |
| `nodes[].properties_no_definidas.diseñador` | 1 |
| `nodes[].properties_no_definidas.documentos_incluidos` | 1 |
| `nodes[].properties_no_definidas.ejemplo` | 2 |
| `nodes[].properties_no_definidas.elementos_del_plan` | 1 |
| `nodes[].properties_no_definidas.espesor` | 1 |
| `nodes[].properties_no_definidas.factor_fer` | 1 |
| `nodes[].properties_no_definidas.familia` | 2 |
| `nodes[].properties_no_definidas.fecha_emision` | 12 |
| `nodes[].properties_no_definidas.fecha_emision_1` | 1 |
| `nodes[].properties_no_definidas.fecha_emision_2` | 1 |
| `nodes[].properties_no_definidas.fecha_vigencia` | 1 |
| `nodes[].properties_no_definidas.formato_datos` | 1 |
| `nodes[].properties_no_definidas.frecuencia_implícita` | 1 |
| `nodes[].properties_no_definidas.frecuencia_temporal` | 1 |
| `nodes[].properties_no_definidas.garantia_requerida` | 1 |
| `nodes[].properties_no_definidas.horario` | 34 |
| `nodes[].properties_no_definidas.incremento_tasa` | 2 |
| `nodes[].properties_no_definidas.metal` | 7 |
| `nodes[].properties_no_definidas.modalidad` | 225 |
| `nodes[].properties_no_definidas.modalidad_clasificada` | 241 |
| `nodes[].properties_no_definidas.modalidad_texto` | 2 |
| `nodes[].properties_no_definidas.moneda` | 29 |
| `nodes[].properties_no_definidas.motivo_anverso` | 4 |
| `nodes[].properties_no_definidas.motivo_principal` | 1 |
| `nodes[].properties_no_definidas.motivo_reverso` | 4 |
| `nodes[].properties_no_definidas.nombre_billete` | 1 |
| `nodes[].properties_no_definidas.norma_referenciada` | 1 |
| `nodes[].properties_no_definidas.nota` | 3 |
| `nodes[].properties_no_definidas.nota_cantidad` | 1 |
| `nodes[].properties_no_definidas.numero_inicial` | 1 |
| `nodes[].properties_no_definidas.otras_propiedades` | 2 |
| `nodes[].properties_no_definidas.otras_propiedades.consecuencia` | 1 |
| `nodes[].properties_no_definidas.otras_propiedades.modalidad` | 1 |
| `nodes[].properties_no_definidas.paises_participantes` | 3 |
| `nodes[].properties_no_definidas.periodo_conmemorado` | 1 |
| `nodes[].properties_no_definidas.peso` | 9 |
| `nodes[].properties_no_definidas.potestad_verificacion` | 2 |
| `nodes[].properties_no_definidas.presentacion` | 6 |
| `nodes[].properties_no_definidas.programa` | 1 |
| `nodes[].properties_no_definidas.referencia_encabezado` | 1 |
| `nodes[].properties_no_definidas.requisito_mercado` | 1 |
| `nodes[].properties_no_definidas.requisito_registro` | 1 |
| `nodes[].properties_no_definidas.serie` | 2 |
| `nodes[].properties_no_definidas.series` | 1 |
| `nodes[].properties_no_definidas.signo` | 9 |
| `nodes[].properties_no_definidas.subindice` | 1 |
| `nodes[].properties_no_definidas.subregímenes` | 1 |
| `nodes[].properties_no_definidas.sujeto_heredado` | 1 |
| `nodes[].properties_no_definidas.supuesto` | 1 |
| `nodes[].properties_no_definidas.tamaño` | 3 |
| `nodes[].properties_no_definidas.tipo` | 2 |
| `nodes[].properties_no_definidas.tipo_no_derivable` | 140 |
| `nodes[].properties_no_definidas.tipo_obligacion` | 1 |
| `nodes[].properties_no_definidas.tramo_modalidad` | 1 |
| `nodes[].properties_no_definidas.umbral_no_cuantificable` | 52 |
| `nodes[].properties_no_definidas.umbral_no_cuantificable_detector_sha256` | 52 |
| `nodes[].properties_no_definidas.umbral_no_cuantificable_motivo` | 52 |
| `nodes[].properties_no_definidas.umbral_no_cuantificable_tablas_forzadas_sha256` | 1 |
| `nodes[].properties_no_definidas.valor_facial` | 9 |
| `nodes[].properties_no_definidas.valor_factor` | 1 |
| `nodes[].properties_no_definidas.valores_válidos` | 1 |
| `nodes[].properties_no_definidas.ámbito_territorial` | 1 |
| `nodes[].provenance` | 37168 |
| `nodes[].provenance.ancestros` | 37168 |
| `nodes[].provenance.archivo` | 37168 |
| `nodes[].provenance.chunk_id` | 37168 |
| `nodes[].provenance.paginas` | 37168 |
| `nodes[].provenance.punto` | 37168 |
| `nodes[].provenance.punto_declarado_e1` | 99 |
| `nodes[].provenance.rol_declarado_e1` | 99 |
| `nodes[].provenance.rol_documental` | 37168 |
| `nodes[].provenance.termino_verificado` | 3723 |
| `nodes[].provenance.to` | 37168 |
| `nodes[].provenance.tramo` | 36239 |
| `nodes[].provenance.tramo_fuera_del_texto_de_e3` | 197 |
| `nodes[].provenance.tramo_modelo` | 90 |
| `nodes[].provenance.tramo_verificado` | 36239 |
| `nodes[].provenances` | 37168 |
| `nodes[].provenances[].ancestros` | 54642 |
| `nodes[].provenances[].archivo` | 54642 |
| `nodes[].provenances[].chunk_id` | 54642 |
| `nodes[].provenances[].paginas` | 54642 |
| `nodes[].provenances[].punto` | 54642 |
| `nodes[].provenances[].punto_declarado_e1` | 99 |
| `nodes[].provenances[].rol_declarado_e1` | 99 |
| `nodes[].provenances[].rol_documental` | 54642 |
| `nodes[].provenances[].termino_verificado` | 3729 |
| `nodes[].provenances[].to` | 54642 |
| `nodes[].provenances[].tramo` | 36551 |
| `nodes[].provenances[].tramo_fuera_del_texto_de_e3` | 210 |
| `nodes[].provenances[].tramo_modelo` | 93 |
| `nodes[].provenances[].tramo_verificado` | 36551 |
| `nodes[].rol_fuente` | 145 |
| `nodes[].type` | 37168 |

## Aristas

Cada arista tiene `source` y `target` (los `id` de dos nodos), `relation` y su procedencia. Claves presentes:

| Clave | Apariciones |
|---|---:|
| `edges[].calificador` | 79 |
| `edges[].coherencia_tipo_predicado` | 1499 |
| `edges[].mencion_verificada` | 12810 |
| `edges[].metodo_resolucion` | 12810 |
| `edges[].properties` | 69816 |
| `edges[].properties.alcance` | 69160 |
| `edges[].properties.destino` | 69160 |
| `edges[].properties.evidencia` | 69160 |
| `edges[].properties.flag` | 656 |
| `edges[].properties_no_definidas` | 2 |
| `edges[].properties_no_definidas.calificacion` | 1 |
| `edges[].properties_no_definidas.calificador` | 1 |
| `edges[].provenance` | 128552 |
| `edges[].provenance.ancestros` | 128552 |
| `edges[].provenance.archivo` | 128552 |
| `edges[].provenance.chunk_id` | 128552 |
| `edges[].provenance.paginas` | 128552 |
| `edges[].provenance.punto` | 128552 |
| `edges[].provenance.punto_declarado_e1` | 111 |
| `edges[].provenance.rol_declarado_e1` | 111 |
| `edges[].provenance.rol_documental` | 128552 |
| `edges[].provenance.termino_verificado` | 5493 |
| `edges[].provenance.to` | 128552 |
| `edges[].provenance.tramo` | 70964 |
| `edges[].provenance.tramo_fuera_del_texto_de_e3` | 398 |
| `edges[].provenance.tramo_modelo` | 143 |
| `edges[].provenance.tramo_verificado` | 71771 |
| `edges[].provenances` | 128552 |
| `edges[].provenances[].ancestros` | 129993 |
| `edges[].provenances[].archivo` | 129993 |
| `edges[].provenances[].chunk_id` | 129993 |
| `edges[].provenances[].paginas` | 129993 |
| `edges[].provenances[].punto` | 129993 |
| `edges[].provenances[].punto_declarado_e1` | 111 |
| `edges[].provenances[].rol_declarado_e1` | 111 |
| `edges[].provenances[].rol_documental` | 129993 |
| `edges[].provenances[].termino_verificado` | 5493 |
| `edges[].provenances[].to` | 129993 |
| `edges[].provenances[].tramo` | 71108 |
| `edges[].provenances[].tramo_fuera_del_texto_de_e3` | 400 |
| `edges[].provenances[].tramo_modelo` | 215 |
| `edges[].provenances[].tramo_verificado` | 72663 |
| `edges[].relation` | 128552 |
| `edges[].rol_fuente` | 3428 |
| `edges[].source` | 128552 |
| `edges[].sujeto_id_modelo` | 11625 |
| `edges[].sujeto_mencion` | 12810 |
| `edges[].sujeto_mencion_modelo` | 23 |
| `edges[].target` | 128552 |

## Procedencia

`provenance` es la procedencia principal de un nodo o de una arista; `provenances`, la lista de todas. Cada una nombra
el documento de origen (`archivo`, que se busca en `corpus/manifiesto_corpus.csv`), el Texto Ordenado (`to`), el
punto (`punto`) y sus ancestros (`ancestros`), las páginas (`paginas`), el fragmento (`chunk_id`), el rol del
documento (`rol_documental`) y, cuando existe, el tramo de texto del que sale (`tramo`) y si se verificó contra el
documento (`tramo_verificado`). El texto citado en `tramo` y en las descripciones es texto del BCRA (ver `NOTICE`).

## Cómo verificar el sello

El sello (`data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz.sello.json`) trae las claves `compresor`, `formato`, `gz`, `gz_bytes`, `gz_sha256`, `kg_json`, `kg_json_bytes`, `kg_json_sha256`, `manda`. `gz_sha256` es el sha256 del archivo comprimido y
`kg_json_sha256`, el del JSON descomprimido:

```python
import gzip, hashlib, json
gz = open("data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz", "rb").read()
sello = json.load(open("data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz.sello.json"))
assert hashlib.sha256(gz).hexdigest() == sello["gz_sha256"]
assert hashlib.sha256(gzip.decompress(gz)).hexdigest() == sello["kg_json_sha256"]
```

En este árbol: `gz_sha256` = `8a448e9185ee950d6157fb0a02ca88caba2b645f6220a210fdcd81609cd860f9` y `kg_json_sha256` = `576c97256185a0d5741cb2c35a2a85e91412f3e1119ad7a85d960b7d60c35ad3`.

## Coincidencias con criterios de evaluación

En este texto, EV2 es una evaluación anterior de la tesis, con 40 preguntas y 164 criterios (`docs/preregistro_evaluacion_fidelidad_ev2.md`, renglones 23 y 24), y «la media de d» es la media, sobre las preguntas, de d_q: la diferencia por pregunta entre el grafo y cada sistema por fragmentos en la proporción de sus 3 corridas juzgadas correctas (`docs/preregistro_B6_4_evaluacion_confirmatoria_varios_puntos.md`, renglones 222 y 223; `docs/preregistro_B6_3_evaluacion_final.md`, renglones 424 y 425).

**Coincidencias del grafo con criterios de evaluación.** Al preparar la publicación busqué todos los criterios de evaluación de B6.3,
B6.4 y EV2 en los textos del grafo evaluado, palabra por palabra, sin distinguir mayúsculas ni puntuación y sin piso de largo.
Diecinueve aparecen enteros: 4 de B6.3, 13 de B6.4 y 2 de EV2; seis de ellos son también una cita del gold. Dieciséis están en la
descripción de un nodo, nueve en el tramo de la norma que cita la procedencia de un nodo o de una arista y uno en el label de un
nodo; seis están en una descripción y en un tramo, y el del label también está en un tramo. Siete son texto literal de la norma: el
criterio cita la norma, y el grafo también. Seis son casi texto de la norma: comparten con una unidad de la norma una secuencia de
al menos el 80 % de sus palabras seguidas. Fijé ese umbral antes de ver los resultados, y uno de los criterios queda justo en el
80 % (4 de sus 5 palabras). Los seis restantes están redactados; dos de ellos están enteros
en el tramo que cita la procedencia, aunque no en el texto segmentado de la norma. Busqué en las sesiones que redactaron las
preguntas y los criterios de B6.3 y de B6.4 (una y cinco), y ninguna tuvo el grafo: sus instrucciones lo excluían, trabajaron desde
los PDF y el texto segmentado de la norma, y ninguna de sus llamadas a herramientas abrió ni consultó un archivo del grafo. En las
otras seis carpetas de sesiones de esas evaluaciones, ninguna sesión escribió archivos con nombre de preguntas o de criterios. Los dos criterios de EV2 se
redactaron el 16/08/2026; la primera descripción del repositorio de la tesis con sus palabras es del 05/10/2026, y el grafo evaluado, del 23/10/2026.
Una explicación posible de las coincidencias redactadas o casi literales, que no verifiqué, es la paráfrasis de un mismo texto de la
norma por dos caminos. Como análisis posterior, no pre-registrado y sin afirmación principal nueva, rehice el análisis confirmatorio
sin esas preguntas. En B6.4, sin las 11 preguntas con alguna coincidencia, la media de d contra el sistema híbrido es 0,031
(intervalo del 95 %, de −0,028 a 0,090; p = 0,36), y contra el denso, 0,110 (de 0,031 a 0,188; p = 0,010). Con las 96 son 0,038
(p = 0,20) y 0,132 (p = 0,001). Sin las 6 cuya coincidencia no es literal, son 0,037 (p = 0,25) y 0,133 (p = 0,002); como esta
segunda sensibilidad saca juntas las casi literales y las redactadas, ninguna cifra de la sensibilidad depende del umbral. En B6.3,
sin sus 4 preguntas con
coincidencia, son −0,036 (p = 0,17) y −0,007 (p = 0,90), frente a −0,038 (p = 0,13) y −0,010 (p = 0,80) con las 96. Ninguna
diferencia cambia de signo, ningún intervalo que excluía el cero pasa a incluirlo ni al revés, y ningún p cruza 0,05. De las 15
preguntas de B6.3 y B6.4 con alguna coincidencia, 5 están en las muestras de control del juez (1 de B6.3 y 4 de B6.4); de esas
cinco respuestas sorteadas, cuatro eran correctas y una, parcial o incorrecta.

**Scripts que sostienen estas cifras.** Están en `data/experiment/banco_mcp/coincidencias_con_el_grafo/` y leen el gold y las sesiones, que no se publican, así que no corren con este repositorio solo:

| Cifra | Script |
|---|---|
| La búsqueda de los 19 | `busqueda_por_palabras/todos_los_criterios_en_el_grafo_mesa.py` |
| Clases y campos | `coincidencias/las_coincidencias_y_la_norma_v2_mesa.py` y `coincidencias/cruzan_unidades_mesa.py` |
| Por pregunta y sensibilidad | `sensibilidad/por_pregunta_y_sensibilidad_B63_mesa.py` y `sensibilidad/por_pregunta_y_sensibilidad_B64_mesa.py` |
| Muestras de control | `control_36/control_36_y_coincidencias_mesa.py` |
| Sesiones de la generación | `sesiones/carpetas_de_las_transcripciones_mesa.py`, `sesiones/el_grafo_en_las_sesiones_de_la_generacion_mesa.py`, `sesiones/el_grafo_en_los_despachos_mesa.py`, `sesiones/neo4j_y_kg_json_en_la_P2_de_B63_mesa.py`, `sesiones/tres_controles_de_la_redaccion_mesa.py` y `sesiones/el_grafo_en_las_seis_carpetas_mesa.py` |

El script de las fechas de EV2 (`fechas/fechas_de_los_dos_criterios_de_ev2_mesa.py`) no se publica porque trae el sha256 corto de dos criterios.
