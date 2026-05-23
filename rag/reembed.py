"""
One-time migration: re-embed PolicySection, CarrierAgreement, and WeatherMemo
nodes using OpenAI text-embedding-3-small (1536 dims), replacing the old
all-MiniLM-L6-v2 (384-dim) vectors.

Steps:
  1. Drop old 384-dim vector indexes
  2. Re-embed each node and update its .embedding property
  3. Create new 1536-dim vector indexes

Usage:
  cd <repo-root>
  OPENAI_API_KEY=sk-... NEO4J_URI=... NEO4J_USERNAME=... NEO4J_PASSWORD=...
  python rag/reembed.py

Or with a .env file in the repo root:
  python rag/reembed.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_driver, EMBEDDING_MODEL, EMBEDDING_DIMS, OPENAI_API_KEY
from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)


def embed(text: str) -> list[float]:
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


def drop_old_indexes(session):
    for index in ("policy_section_embedding", "carrier_agreement_embedding", "weather_memo_embedding"):
        try:
            session.run(f"DROP INDEX {index} IF EXISTS")
            print(f"  Dropped index: {index}")
        except Exception as e:
            print(f"  Warning dropping {index}: {e}")


def create_new_indexes(session, dims: int):
    indexes = [
        ("policy_section_embedding",    "PolicySection",    "embedding"),
        ("carrier_agreement_embedding", "CarrierAgreement", "embedding"),
        ("weather_memo_embedding",      "WeatherMemo",      "embedding"),
    ]
    for name, label, prop in indexes:
        try:
            session.run(f"""
                CREATE VECTOR INDEX {name} IF NOT EXISTS
                FOR (n:{label}) ON n.{prop}
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {dims},
                    `vector.similarity_function`: 'cosine'
                }}}}
            """)
            print(f"  Created index: {name} ({label}.{prop}, {dims} dims)")
        except Exception as e:
            print(f"  Warning creating {name}: {e}")


def reembed_label(session, label: str, text_field: str, id_field: str = "id"):
    result = session.run(f"MATCH (n:{label}) RETURN n.{id_field} AS id, n.{text_field} AS text")
    rows = list(result)
    print(f"  {label}: {len(rows)} nodes to re-embed")
    for i, row in enumerate(rows, 1):
        node_id = row["id"]
        text = row["text"] or ""
        if not text.strip():
            print(f"    [{i}/{len(rows)}] {node_id}: SKIPPED (empty text)")
            continue
        vec = embed(text)
        session.run(
            f"MATCH (n:{label} {{{id_field}: $id}}) SET n.embedding = $vec",
            id=node_id, vec=vec,
        )
        print(f"    [{i}/{len(rows)}] {node_id}: OK")


def main():
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY is not set.")
        sys.exit(1)

    print(f"Model: {EMBEDDING_MODEL}  |  Dims: {EMBEDDING_DIMS}")
    driver = get_driver()
    try:
        with driver.session() as session:
            print("\n[1/5] Dropping old vector indexes...")
            drop_old_indexes(session)

            print("\n[2/5] Re-embedding PolicySection nodes...")
            reembed_label(session, "PolicySection", text_field="text")

            print("\n[3/5] Re-embedding CarrierAgreement nodes...")
            reembed_label(session, "CarrierAgreement", text_field="text")

            print("\n[4/5] Re-embedding WeatherMemo nodes...")
            reembed_label(session, "WeatherMemo", text_field="text")

            print("\n[5/5] Creating new vector indexes...")
            create_new_indexes(session, EMBEDDING_DIMS)

    finally:
        driver.close()

    print("\nDone. Run the backend and try a search_policies call to verify.")


if __name__ == "__main__":
    main()
