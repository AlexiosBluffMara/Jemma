"""
Jemma SafeBrain — RAG Engine

Retrieval-Augmented Generation over the civic data database.
Chunks documents, builds embeddings (sentence-transformers fallback to TF-IDF),
provides semantic search, and generates answers using local Gemma 4 via Ollama.

Designed for overnight autonomous operation with retry logic.
"""

import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger("rag_engine")

DB_PATH = Path(__file__).parent.parent / "datasets" / "civic_data.db"
CHUNK_SIZE = 512       # tokens approximate (chars / 4)
CHUNK_OVERLAP = 64     # token overlap
EMBEDDING_DIM = 384    # all-MiniLM-L6-v2 dimension
TOP_K = 5              # default retrieval count

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE * 4,
               overlap: int = CHUNK_OVERLAP * 4) -> list[str]:
    """Split text into overlapping chunks by character count."""
    if not text or len(text) < chunk_size:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at sentence boundary
        last_period = chunk.rfind('. ')
        if last_period > chunk_size // 2:
            chunk = chunk[:last_period + 1]
            end = start + last_period + 1
        chunks.append(chunk.strip())
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Embedding store — SQLite backed
# ---------------------------------------------------------------------------
def init_rag_tables(conn: sqlite3.Connection):
    """Add RAG-specific tables to civic_data.db."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,  -- 'page', 'dataset', 'document'
            source_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            char_count INTEGER,
            UNIQUE(source_type, source_id, chunk_index)
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_type, source_id);

        CREATE TABLE IF NOT EXISTS embeddings (
            chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id),
            vector BLOB NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rag_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            retrieved_ids TEXT,
            answer TEXT,
            model TEXT,
            latency_ms REAL,
            timestamp TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Embedding backends
# ---------------------------------------------------------------------------
class TFIDFEmbedder:
    """Fallback TF-IDF based embedder when sentence-transformers unavailable."""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        self.vocab = {}
        self.idf = {}
        self._fitted = False

    def fit(self, texts: list[str]):
        """Build vocabulary from corpus."""
        df = {}
        n = len(texts)
        for text in texts:
            words = set(re.findall(r'\w+', text.lower()))
            for w in words:
                df[w] = df.get(w, 0) + 1
        # Keep top-dim words by df
        sorted_words = sorted(df.items(), key=lambda x: -x[1])[:self.dim]
        self.vocab = {w: i for i, (w, _) in enumerate(sorted_words)}
        self.idf = {w: math.log(n / (c + 1)) for w, c in sorted_words}
        self._fitted = True

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts to TF-IDF vectors."""
        vecs = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            words = re.findall(r'\w+', text.lower())
            tf = {}
            for w in words:
                tf[w] = tf.get(w, 0) + 1
            for w, count in tf.items():
                if w in self.vocab:
                    idx = self.vocab[w]
                    vecs[i, idx] = (1 + math.log(count)) * self.idf.get(w, 1.0)
            # L2 normalize
            norm = np.linalg.norm(vecs[i])
            if norm > 0:
                vecs[i] /= norm
        return vecs


class SentenceTransformerEmbedder:
    """Wrapper around sentence-transformers for high quality embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str], batch_size: int = 32,
               show_progress: bool = False) -> np.ndarray:
        return self.model.encode(
            texts, batch_size=batch_size, show_progress_bar=show_progress,
            normalize_embeddings=True,
        )


def get_embedder():
    """Get best available embedder."""
    try:
        emb = SentenceTransformerEmbedder()
        log.info(f"Using SentenceTransformer (dim={emb.dim})")
        return emb
    except ImportError:
        log.warning("sentence-transformers not found, falling back to TF-IDF")
        return TFIDFEmbedder()


# ---------------------------------------------------------------------------
# Build RAG index
# ---------------------------------------------------------------------------
def build_rag_index(db_path: Path = DB_PATH, force_rebuild: bool = False):
    """Chunk all civic data and build embeddings."""
    start = time.time()
    log.info("Building RAG index...")

    conn = sqlite3.connect(str(db_path))
    init_rag_tables(conn)

    # Check if already built
    existing = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    if existing > 0 and not force_rebuild:
        log.info(f"RAG index already has {existing} chunks. Use force_rebuild=True to rebuild.")
        conn.close()
        return existing

    if force_rebuild:
        conn.execute("DELETE FROM embeddings")
        conn.execute("DELETE FROM chunks")
        conn.commit()

    # Chunk pages
    chunk_count = 0
    pages = conn.execute("SELECT id, content FROM pages WHERE content IS NOT NULL").fetchall()
    for page_id, content in pages:
        if not content:
            continue
        chunks = chunk_text(content)
        for idx, chunk in enumerate(chunks):
            text_hash = hashlib.sha256(chunk.encode()).hexdigest()
            conn.execute("""
                INSERT OR IGNORE INTO chunks (source_type, source_id, chunk_index,
                    text, text_hash, char_count)
                VALUES ('page', ?, ?, ?, ?, ?)
            """, (page_id, idx, chunk, text_hash, len(chunk)))
            chunk_count += 1

    # Chunk dataset descriptions + samples
    datasets = conn.execute(
        "SELECT id, description, sample_json FROM datasets"
    ).fetchall()
    for ds_id, desc, sample in datasets:
        text = (desc or "") + "\n" + (sample[:2000] if sample else "")
        if not text.strip():
            continue
        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            text_hash = hashlib.sha256(chunk.encode()).hexdigest()
            conn.execute("""
                INSERT OR IGNORE INTO chunks (source_type, source_id, chunk_index,
                    text, text_hash, char_count)
                VALUES ('dataset', ?, ?, ?, ?, ?)
            """, (ds_id, idx, chunk, text_hash, len(chunk)))
            chunk_count += 1

    # Chunk documents
    docs = conn.execute("SELECT id, content FROM documents WHERE content IS NOT NULL").fetchall()
    for doc_id, content in docs:
        chunks = chunk_text(content)
        for idx, chunk in enumerate(chunks):
            text_hash = hashlib.sha256(chunk.encode()).hexdigest()
            conn.execute("""
                INSERT OR IGNORE INTO chunks (source_type, source_id, chunk_index,
                    text, text_hash, char_count)
                VALUES ('document', ?, ?, ?, ?, ?)
            """, (doc_id, idx, chunk, text_hash, len(chunk)))
            chunk_count += 1

    conn.commit()
    log.info(f"Created {chunk_count} chunks from {len(pages)} pages, "
             f"{len(datasets)} datasets, {len(docs)} documents")

    # Build embeddings
    all_chunks = conn.execute("SELECT id, text FROM chunks").fetchall()
    if not all_chunks:
        log.warning("No chunks to embed")
        conn.close()
        return 0

    chunk_ids = [c[0] for c in all_chunks]
    chunk_texts = [c[1] for c in all_chunks]

    embedder = get_embedder()
    if isinstance(embedder, TFIDFEmbedder):
        embedder.fit(chunk_texts)
    vectors = embedder.encode(chunk_texts)
    log.info(f"Computed {len(vectors)} embeddings (dim={vectors.shape[1]})")

    # Store embeddings as BLOBs
    for cid, vec in zip(chunk_ids, vectors):
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (chunk_id, vector) VALUES (?, ?)",
            (cid, vec.tobytes()),
        )
    conn.commit()

    elapsed = time.time() - start
    log.info(f"RAG index built: {chunk_count} chunks, {elapsed:.1f}s")
    conn.close()
    return chunk_count


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
def retrieve(query: str, db_path: Path = DB_PATH, top_k: int = TOP_K) -> list[dict]:
    """Retrieve top-k most relevant chunks for a query."""
    conn = sqlite3.connect(str(db_path))

    # Get all embeddings
    rows = conn.execute("""
        SELECT c.id, c.text, c.source_type, c.source_id, e.vector
        FROM chunks c JOIN embeddings e ON c.id = e.chunk_id
    """).fetchall()

    if not rows:
        log.warning("No embeddings in database. Run build_rag_index first.")
        conn.close()
        return []

    # Compute query embedding
    embedder = get_embedder()
    if isinstance(embedder, TFIDFEmbedder):
        # Rebuild vocab from stored chunks
        all_texts = [r[1] for r in rows]
        embedder.fit(all_texts)
    q_vec = embedder.encode([query])[0]

    # Compute cosine similarity
    dim = len(q_vec)
    scored = []
    for cid, text, src_type, src_id, vec_bytes in rows:
        vec = np.frombuffer(vec_bytes, dtype=np.float32)
        if len(vec) != dim:
            continue
        sim = float(np.dot(q_vec, vec))  # vectors are L2-normalized
        scored.append({
            "chunk_id": cid,
            "text": text,
            "source_type": src_type,
            "source_id": src_id,
            "score": sim,
        })

    scored.sort(key=lambda x: -x["score"])
    conn.close()
    return scored[:top_k]


# ---------------------------------------------------------------------------
# Generation (Ollama or transformers)
# ---------------------------------------------------------------------------
def generate_answer(query: str, context_chunks: list[dict],
                    model: str = "gemma4-e4b-it:q8_0") -> dict:
    """Generate an answer using retrieved context via Ollama HTTP API."""
    import requests

    context = "\n\n---\n\n".join([
        f"[Source: {c['source_type']} #{c['source_id']}, score={c['score']:.3f}]\n{c['text']}"
        for c in context_chunks
    ])

    system_prompt = (
        "You are Jemma SafeBrain, a civic AI assistant for the Town of Normal, IL "
        "and Illinois State University. Answer questions using ONLY the provided context. "
        "If the context doesn't contain enough information, say so honestly. "
        "Be specific with numbers, dates, and official details."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
    ]

    start = time.time()
    try:
        resp = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("message", {}).get("content", "")
        latency = (time.time() - start) * 1000

        return {
            "answer": answer,
            "model": model,
            "latency_ms": latency,
            "context_chunks": len(context_chunks),
        }
    except requests.exceptions.ConnectionError:
        log.warning("Ollama not running. Returning context-only response.")
        return {
            "answer": f"[Ollama offline] Top context:\n{context_chunks[0]['text'][:500]}",
            "model": "context-only",
            "latency_ms": (time.time() - start) * 1000,
            "context_chunks": len(context_chunks),
        }
    except Exception as e:
        log.error(f"Generation error: {e}")
        return {"answer": f"Error: {e}", "model": model, "latency_ms": 0, "context_chunks": 0}


# ---------------------------------------------------------------------------
# Full RAG pipeline
# ---------------------------------------------------------------------------
def rag_query(query: str, db_path: Path = DB_PATH, top_k: int = TOP_K,
              model: str = "gemma4-e4b-it:q8_0") -> dict:
    """End-to-end RAG: retrieve + generate."""
    chunks = retrieve(query, db_path=db_path, top_k=top_k)
    if not chunks:
        return {"answer": "No relevant data found. Run data ingestion first.",
                "model": "none", "chunks": []}

    result = generate_answer(query, chunks, model=model)
    result["retrieved_chunks"] = chunks

    # Log query
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            INSERT INTO rag_queries (query, retrieved_ids, answer, model, latency_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (
            query,
            json.dumps([c["chunk_id"] for c in chunks]),
            result["answer"],
            result["model"],
            result["latency_ms"],
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rag_engine.py build          # Build RAG index")
        print("  python rag_engine.py query <text>    # Query the RAG system")
        print("  python rag_engine.py stats           # Show index stats")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "build":
        n = build_rag_index(force_rebuild="--force" in sys.argv)
        print(f"Built index with {n} chunks")

    elif cmd == "query":
        q = " ".join(sys.argv[2:])
        result = rag_query(q)
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print(f"{'='*60}")
        print(f"Answer ({result['model']}, {result['latency_ms']:.0f}ms):\n")
        print(result["answer"])
        if result.get("retrieved_chunks"):
            print(f"\n--- {len(result['retrieved_chunks'])} chunks retrieved ---")

    elif cmd == "stats":
        conn = sqlite3.connect(str(DB_PATH))
        for table in ["chunks", "embeddings", "rag_queries"]:
            try:
                n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  {table}: {n} rows")
            except Exception:
                print(f"  {table}: not created yet")
        conn.close()
