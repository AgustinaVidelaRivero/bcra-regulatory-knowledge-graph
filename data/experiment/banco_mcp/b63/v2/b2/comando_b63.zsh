#!/bin/zsh
# comando_b63.zsh (v2/b2, etapa b2; el de la b1 bis, para el runner de esta carpeta) — El comando que corre la autora desde su Terminal para lanzar el Python del runner de B6.3
# (lo que suma la mesa en la etapa b1 bis, punto 5): con `env -i` y una lista cerrada, PATH, HOME y la variable de la entrada
# (NEO4J_URI, que el comando lee de la entrada sellada y el runner compara con la suya), más ANTHROPIC_API_KEY si está en el entorno de la
# Terminal, que la vía api de las sesiones necesita (agentes/lanzar_agente.py:130-131). La clave pasa sin imprimirse. Nada más del
# entorno de la Terminal llega al runner: con LANG=es_AR.UTF-8, `sysctl` da la coma decimal y `memoria_maquina` corta.
#
# Uso:
#   zsh comando_b63.zsh medir <entrada.json>
#       mide la memoria de la máquina con el mismo entorno que el runner (memoria_b63.py: lo fijo, para la P), sin la clave;
#   zsh comando_b63.zsh correr <entrada.json> <sha256 de la entrada> --modo real|init [los demás argumentos del runner]
#       lanza b63/v2/b2/correr_b63.py con --entrada y --sha256-entrada.
# Imprime los nombres de las variables que pasa (nunca sus valores). Si el PATH no trae /usr/sbin (sysctl), frena con el 10.
# El Python es el del .venv del repo; B63_PYTHON lo cambia, solo para las pruebas sobre una copia del repo (que no trae el .venv), y no
# pasa al runner.
set -u
D=${0:A:h}                                   # b63/v2/b1bis
R=${D:h:h:h:h:h:h}                           # la raíz del repo
PY="${B63_PYTHON:-$R/.venv/bin/python}"
frena() { print -r -- "FRENO (comando_b63): $1"; exit 10 }
[[ -x "$PY" ]] || frena "no está el Python del .venv del repo"
(( $# >= 2 )) || frena "uso: zsh comando_b63.zsh medir <entrada.json> | correr <entrada.json> <sha256> --modo ..."
ACCION=$1; ENTRADA=$2
[[ -f "$ENTRADA" ]] || frena "no existe la entrada sellada"
[[ ":$PATH:" == *":/usr/sbin:"* ]] || frena "el PATH no trae /usr/sbin (sysctl, para la memoria)"
URI=$(env -i PATH=/usr/bin:/bin "$PY" -I -B -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["neo4j"]["uri"])' "$ENTRADA") \
  || frena "la entrada no trae neo4j.uri"
ENV=(PATH="$PATH" HOME="$HOME" NEO4J_URI="$URI")
case $ACCION in
  medir)
    print -r -- "comando_b63: env -i con ${(j:, :)${(@)ENV%%=*}}"
    exec env -i "${ENV[@]}" "$PY" -B "$D/memoria_b63.py" ;;
  correr)
    (( $# >= 3 )) || frena "falta el sha256 de la entrada"
    SHA=$3; shift 3
    [[ -n "${ANTHROPIC_API_KEY:-}" ]] && ENV+=(ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY")
    print -r -- "comando_b63: env -i con ${(j:, :)${(@)ENV%%=*}}"
    exec env -i "${ENV[@]}" "$PY" -B "$D/correr_b63.py" --entrada "$ENTRADA" --sha256-entrada "$SHA" "$@" ;;
  *)
    frena "acción desconocida: $ACCION" ;;
esac
