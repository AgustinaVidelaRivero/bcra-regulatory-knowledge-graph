# Las instrucciones del juez de tripletas sin sus ejemplos: valen para la v2 y para la v3

`instrucciones_juez_tripletas_sin_ejemplos_v2_y_v3.txt` (sha256 `f29de17b2dcf4b11eacf615b65e025fc85874c76ff24a29393e2f959c2a01517`) es
el prompt congelado de la v2 del juez de precisión (la iteración 1, sha256 `cf40964d…`; congelación de la enmienda 4, punto 5, en
`congelacion_juez_v2_sha256.txt`) sin su bloque de casos resueltos: el bloque fijo del sistema y el formato de salida, tal cual.

- **Cómo se armó:** por código, con `prompt_juez_v2.armar` sin cambiarlo y el control de que el prompt diera su sha256 congelado
  (`extraer_instrucciones_juez_v2_mesa.py`, del paquete de la mesa, §287). El bloque de casos que se omite tiene sha256 `070383e1…`.
  Ninguna ventana de 40 ni de 80 caracteres de ese bloque, fuera de las que comparte con las instrucciones, quedó en lo escrito
  (`consola_controlar_ventanas_instrucciones_mesa.txt`, en el mismo paquete).
- **Valen para la v2 y para la v3,** que se distinguen solo en sus casos (enmienda 5 del pre-registro de tripletas, punto 4): la v3 usa
  estas mismas instrucciones, el mismo formato de salida y la misma ficha, con el bloque de casos de la v2 más los cinco casos nuevos
  que la enmienda 5 aprueba.
- **No trae ningún caso ni ninguna marca de la autora.** Los casos y los prompts enteros quedan fuera del repo, con su sha256 en la
  congelación de cada versión.
