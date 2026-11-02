#!/bin/zsh
# levantar_neo4j_b63.zsh — Levanta el Neo4j de B6.3 (etapa b1; decisión de la autora del 27/10/2026, 10:24:11): el propio de los
# índices, proyecto neo4j_indices_eval (contenedor neo4j-bcra-kg-indices-eval, puertos 47474 y 47687 en 127.0.0.1), con el override
# de HEAD (data/experiment/neo4j/docker-compose.indices_eval.yml), desde la carpeta donde está su volumen cargado:
#   $BCRA_KG_FUERA_DEL_REPO/indices_eval/copia_b/data/experiment/neo4j/
# Desde la carpeta del repo, el mismo override monta un volumen vacío (./volumen_indices_eval/ es relativo a la carpeta del compose):
# por eso controla la carpeta antes de levantar. El volumen no se abre, no se copia y no se lista: solo se controla que su carpeta
# exista.
#
# Lo corre la etapa b (el testigo, después de N7), nunca durante N6. Antes de correrlo, la VM de Docker se topea en 2,5 GiB (Docker
# Desktop, Settings > Resources > Memory; decisión del 27/10/2026, 11:31:49): el comando lo controla y frena si no.
# Pasos, cada uno frena si no da (código 1, con su motivo):
#   1. la carpeta es la de la copia b, fuera del repo, y su docker-compose.yml y su override son, byte a byte, los de HEAD;
#   2. la carpeta del volumen (volumen_indices_eval/data) existe;
#   3. la VM de Docker tiene 2,5 GiB o menos (docker info --format '{{.MemTotal}}', hasta 2.684.354.560 bytes);
#   4. levanta y espera la salud (docker compose ... up -d --wait), y el contenedor da healthy (docker inspect, solo ese);
#   5. la huella de contenido del grafo evaluado es la de la entrada (b63/v2/control_neo4j_b63.py, con NEO4J_URI en 47687).
# Para bajarlo (después de la corrida, desde la misma carpeta):
#   docker compose -p neo4j_indices_eval -f docker-compose.yml -f docker-compose.indices_eval.yml down
# Uso: zsh levantar_neo4j_b63.zsh <repo> <huella de contenido esperada>
set -euo pipefail
R="$1"; HUELLA="$2"
D="${BCRA_KG_FUERA_DEL_REPO:-${0:A:h:h:h:h:h:h}/fuera_del_repo}/indices_eval/copia_b/data/experiment/neo4j"
TOPE=2684354560
frena() { print -r -- "FRENO (USD 0): $1"; exit 1; }
[[ -d "$D" ]] || frena "no existe la carpeta de la copia b"
cd "$D"
case "$(pwd -P)/" in "$(cd "$R" && pwd -P)/"*) frena "la carpeta está dentro del repo: ahí el override monta un volumen vacío";; esac
for f in docker-compose.yml docker-compose.indices_eval.yml; do
  [[ "$(shasum -a 256 "$f" | cut -c1-64)" == "$(git -C "$R" show "HEAD:data/experiment/neo4j/$f" | shasum -a 256 | cut -c1-64)" ]] \
    || frena "$f de la copia b no es el de HEAD"
done
[[ -d volumen_indices_eval/data ]] || frena "no existe la carpeta del volumen cargado (volumen_indices_eval/data)"
VM="$(docker info --format '{{.MemTotal}}')"
[[ "$VM" == <-> && "$VM" -le "$TOPE" ]] || frena "la VM de Docker tiene $VM bytes: más que el tope de $TOPE (2,5 GiB); topearla antes"
docker compose -p neo4j_indices_eval -f docker-compose.yml -f docker-compose.indices_eval.yml up -d --wait
[[ "$(docker inspect -f '{{.State.Health.Status}}' neo4j-bcra-kg-indices-eval)" == healthy ]] || frena "el contenedor no está sano"
NEO4J_URI=bolt://127.0.0.1:47687 "$R/.venv/bin/python" -B "$R/data/experiment/banco_mcp/b63/v2/control_neo4j_b63.py" \
  --huella-esperada "$HUELLA" || frena "la huella de contenido no es la de la entrada"
print -r -- "Neo4j de B6.3 arriba, sano y con la huella de la entrada (bolt://127.0.0.1:47687)"
