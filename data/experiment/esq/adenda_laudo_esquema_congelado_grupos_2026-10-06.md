# Adenda al laudo de esquema congelado — grupo de cada fila de la tabla §3 (laudo (a) de P7)

**DECIDIDA por la autora el 06/10/2026 (opción a1 de las presentadas por la mesa); queda FIRMADA con su commit, que es
PENDIENTE hasta que ocurra.** El laudo (`data/experiment/esq/laudo_esquema_congelado.md`, FIRMADO el 03/09/2026) no se
edita: esta adenda vive al lado y se lee junto con él. Fuente: la tabla §3 del laudo (`:92-102`) y la Tabla 4 de la tesis
(«Límites declarados del esquema congelado», `tab:limites`; en el repo, `git show ed389c4:docs/tesis/main.tex`, `:919-1029`;
la versión vigente se cita desde Overleaf por sección, no por línea).

## Qué resuelve

La tabla §3 del laudo («Residuos y límites conocidos, con sus tasas») tiene nueve filas sin columna de grupo. La Tabla 4 de la
tesis declara ocho límites «del vocabulario» y su caption dice que el laudo declara además límites del ensamblado, que quedan
fuera de la tabla. Esta adenda agrega a cada fila su grupo, para que el lector del laudo sepa qué fila terminó en la Tabla 4 y
qué pasó con las que no, sin cambiar ninguna fila ni ningún número.

## La columna «grupo»

| fila del laudo (`:n`) | límite | grupo | dónde está hoy |
|---|---|---|---|
| `:94` | Vaciamiento (omisión total nueva del brazo retocado) | límite del vocabulario | Tabla 4, límite 3 (vigilancia) |
| `:95` | Cláusula interpretativa ignora la regla 9 | límite del vocabulario | Tabla 4, límite 4 (conclusión) |
| `:96` | Duplicación de contenido entre cajas | límite del vocabulario | Tabla 4, límite 6 (vigilancia) |
| `:97` | Migración de modalidad a Condicion | límite del vocabulario | Tabla 4, límite 5 (vigilancia) |
| `:98` | Degradación de calidad entre iteraciones | límite del vocabulario | Tabla 4, límite 7 (conclusión; por casos, sin denominador) |
| `:99` | Fusión de rótulos de TO con nombres de otros TOs reales | límite del ensamblado, tratado por código en r2 | los nodos TextoOrdenado se unifican por archivo, nunca por rótulo (ids `TextoOrdenado_to_<archivo>` en los grafos r2b, `a9631a64` y `6e756043`) |
| `:100` | Cola larga del subtipado de Obligacion | límite del vocabulario | Tabla 4, límite 8 (conclusión) |
| `:101` | Rol de alcance del sujeto (cuarentena D5) | límite de la resolución de sujetos, tratado por código en r2 | roles de alcance por documento en el catálogo único (`Sujeto_rol_alcance_*`, `data/experiment/catalogo_unico/catalogo_sujetos_r2.json`; L-ESQ-R2, `4ef7650`); los documentos sin rol, con la regla de la condición 11 de la tanda 1 |
| `:102` | Remisiones intra-texto sin arista en E1 (11 de 38 azarosas en ESQ-2) | límite del ensamblado, tratado por código en r2 | `remite_a` derivada por el detector de citas del ensamblado (enmienda 2 de L-ESQ-R2, `5f9a731`; reglas (a) a (i), `26d274d`), fuera de E1 |

Los dos límites de la Tabla 4 que no tienen fila en esta tabla vienen de otras partes del mismo laudo: el límite 1 (hechos
con valor n-arios) de la lista de §2 (`:88`, «Hechos con valor / properties en relaciones → ESQ-RI-3 y C1.7; limitación
declarada de este esquema»), y el límite 2 (la condición solo cubre el supuesto enunciado dentro de la misma unidad) del
resultado del test de ESQ-1 que el laudo cierra («su predicción principal, una condición que remite a otra unidad»). No se
agregan filas: la tabla del laudo queda como se congeló.

## Qué no cambia

- Ninguna fila, tasa ni destino de la tabla §3; ningún otro texto del laudo.
- La Tabla 4 de la tesis (ocho límites) y su caption.
- El tratamiento por código de `:99`, `:101` y `:102` es el de la release r2 (L-ESQ-R2 y sus enmiendas); esta adenda lo
  cita, no lo decide.

## Firma

Decidida por la autora el 06/10/2026; firmada con su commit (PENDIENTE hasta ese commit).
