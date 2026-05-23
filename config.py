"""Shim so rag/graphrag.py can run inside the Docker container."""
import os
from neo4j import GraphDatabase

# Load .env from the same directory as this file (frontend/.env)
try:
    from dotenv import load_dotenv as _load_dotenv
    _here = os.path.dirname(os.path.abspath(__file__))
    for _candidate in [
        os.path.join(_here, ".env"),
        os.path.join(_here, "..", ".env"),
    ]:
        if os.path.exists(_candidate):
            _load_dotenv(_candidate, override=False)
            break
except ImportError:
    pass

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS  = 1536
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")


def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
