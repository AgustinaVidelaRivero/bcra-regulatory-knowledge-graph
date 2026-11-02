# Enmienda 01 al pre-registro del piloto sin-gold U6

Condición de corrida detectada en la preparación, registrada antes de gastar API.

## Condición

Los 13 casos corren con `n_seen = 0`: los nodos vistos por el agente no son
recuperables íntegros, porque las llamadas de la corrida U6 se persistieron en
una base distinta de la que consulta el mecanismo de recuperación. En
consecuencia el verificador opera con el fallback propio del builder sellado
("no se pudieron recuperar los nodos vistos; usá las tools") y debe investigar
el grafo con sus tools en lugar de partir de los nodos ya vistos. Las trazas
del agente sí entran completas al contexto; lo que falta es el contenido
íntegro de los nodos, que en la traza está truncado.

## Alcance y por qué no se compensa

La condición es uniforme en los 13 casos y tiene precedente sellado (el caso
G-3 del gate U5 corrió en la misma condición). No la compenso: la ruta de la
base consultada por `recover_seen` está fijada en el código
(`verifier_pilot.py:102`, `cache/calls.db`, sin parámetro ni variable de
entorno), y modificarla tocaría el camino de invocación del verificador
sellado, lo que exigiría re-gatearlo.

No modifico los umbrales del pre-registro. Registro que un eventual acuerdo
bajo admite dos lecturas no separables con n=13: menor capacidad diagnóstica
del verificador, o menor contexto de entrada respecto de su calibración.
Cualquier conclusión sobre la rama resultante debe mencionar esta condición.

## Tope de la corrida

Tope laudado: 6M tokens de entrada / 200K de salida (mismo tope del gate U5).
