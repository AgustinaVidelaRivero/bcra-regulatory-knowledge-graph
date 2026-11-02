"""
conexion.py — Conexión compartida a Neo4j Community local (backend experimental).

Configuración por variables de entorno, con defaults del contenedor local
documentado en el README de este directorio:

  NEO4J_URI       (default bolt://localhost:7687)
  NEO4J_USER      (default neo4j)
  NEO4J_PASSWORD  (default bcra-kg-local — password de desarrollo local,
                   fijada al crear el contenedor; no es una credencial real)

Este módulo NO forma parte del pipeline de evaluación: es infraestructura
del backend experimental Neo4j (ver README.md de este directorio).
"""

from __future__ import annotations

import os

from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "bcra-kg-local")


def abrir_driver():
    """Driver verificado contra el servidor (falla rápido si Neo4j no corre)."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    return driver
