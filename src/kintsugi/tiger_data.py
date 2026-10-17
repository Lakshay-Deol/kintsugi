"""Tiger Data integration for Kintsugi repair assistant.

Supports:
1. Storing 384-dimensional FastEmbed embeddings with pgvector on Tiger Data PostgreSQL.
2. Hybrid keyword (tsvector/trigram) + vector search (cosine distance).
3. Tiger MCP Server interface: lets external AI agents query and manage the manual database.
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


def get_tiger_connection_string() -> str:
    """Return configured Tiger Data Postgres connection string."""
    return os.getenv("TIGER_DATA_URI", "postgresql://postgres:postgres@localhost:5432/tiger_repair")


def init_tiger_schema(conn) -> None:
    """Initialize pgvector extension and hybrid search tables on Tiger Data."""
    with conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

        # Create hybrid chunks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tiger_chunks (
                id TEXT PRIMARY KEY,
                manual_id TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                page INT NOT NULL,
                section TEXT,
                type TEXT,
                text TEXT NOT NULL,
                embedding vector(384),
                tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
            );
            CREATE INDEX IF NOT EXISTS tiger_chunks_embedding_idx ON tiger_chunks USING ivfflat (embedding vector_cosine_ops);
            CREATE INDEX IF NOT EXISTS tiger_chunks_tsv_idx ON tiger_chunks USING gin (tsv);
            CREATE INDEX IF NOT EXISTS tiger_chunks_model_idx ON tiger_chunks (model);
        """)
        conn.commit()
    log.info("Tiger Data pgvector schema initialized successfully.")


def tiger_hybrid_search(
    conn,
    query_text: str,
    query_vector: list[float],
    model: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Execute hybrid search using pgvector cosine distance + Postgres text search on Tiger Data."""
    with conn.cursor() as cur:
        sql = """
            WITH vector_matches AS (
                SELECT id, 1 - (embedding <=> %s::vector) AS v_score,
                       ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector) AS v_rank
                FROM tiger_chunks
                WHERE UPPER(model) = UPPER(%s)
                LIMIT 20
            ),
            text_matches AS (
                SELECT id, ts_rank(tsv, plainto_tsquery('english', %s)) AS t_score,
                       ROW_NUMBER() OVER (ORDER BY ts_rank(tsv, plainto_tsquery('english', %s)) DESC) AS t_rank
                FROM tiger_chunks
                WHERE UPPER(model) = UPPER(%s) AND tsv @@ plainto_tsquery('english', %s)
                LIMIT 20
            )
            SELECT c.id, c.brand, c.model, c.page, c.section, c.text,
                   COALESCE(1.0 / (60 + v.v_rank), 0.0) + COALESCE(1.0 / (60 + t.t_rank), 0.0) AS rrf_score
            FROM tiger_chunks c
            LEFT JOIN vector_matches v ON c.id = v.id
            LEFT JOIN text_matches t ON c.id = t.id
            WHERE v.id IS NOT NULL OR t.id IS NOT NULL
            ORDER BY rrf_score DESC
            LIMIT %s;
        """
        cur.execute(
            sql,
            (query_vector, query_vector, model, query_text, query_text, model, query_text, top_k),
        )
        rows = cur.fetchall()
        results = []
        for r in rows:
            results.append({
                "_id": r[0],
                "brand": r[1],
                "model": r[2],
                "page": r[3],
                "section": r[4],
                "text": r[5],
                "rrf_score": float(r[6]),
            })
        return results


# ---------------------------------------------------------------------------
# Tiger MCP Tool Definitions (for AI Agents managing Tiger Data)
# ---------------------------------------------------------------------------

TIGER_MCP_TOOLS = [
    {
        "name": "tiger_search_manual",
        "description": "Run hybrid pgvector + full-text search on Tiger Data repair manuals.",
        "parameters": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Appliance model number"},
                "symptom": {"type": "string", "description": "Symptom or diagnostic query"},
            },
            "required": ["model", "symptom"],
        },
    },
    {
        "name": "tiger_list_indexed_models",
        "description": "List all appliance models currently indexed with pgvector on Tiger Data.",
        "parameters": {"type": "object", "properties": {}},
    },
]
