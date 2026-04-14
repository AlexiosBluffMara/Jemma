#!/usr/bin/env python3
"""
Jemma GraphRAG — Markdown Knowledge Base with Graph Relationships

Ingests markdown documentation + civic data into a graph-aware RAG index.
Nodes are chunks; edges are extracted entity co-references, cross-doc links,
and hierarchical (heading → subheading) relationships.

Uses sentence-transformers for embeddings, SQLite for storage, and
NetworkX for graph traversal during retrieval.
"""
import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger("graphrag")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

DB_PATH = Path(__file__).parent.parent / "datasets" / "graphrag.db"
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
DOCS_DIR = Path(__file__).parent.parent / "docs"
CHUNK_SIZE = 1500  # chars (~375 tokens)
CHUNK_OVERLAP = 200
EMBEDDING_DIM = 384
TOP_K = 8

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    title TEXT,
    doc_type TEXT,  -- 'knowledge', 'doc', 'dataset', 'civic'
    char_count INTEGER,
    chunk_count INTEGER DEFAULT 0,
    indexed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    heading TEXT,           -- nearest parent heading
    text TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    char_count INTEGER,
    UNIQUE(doc_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);

CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id),
    vector BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    entity_type TEXT,  -- 'person', 'org', 'place', 'concept', 'benchmark', 'model'
    UNIQUE(name, entity_type)
);

CREATE TABLE IF NOT EXISTS chunk_entities (
    chunk_id INTEGER REFERENCES chunks(id),
    entity_id INTEGER REFERENCES entities(id),
    PRIMARY KEY(chunk_id, entity_id)
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_chunk_id INTEGER REFERENCES chunks(id),
    target_chunk_id INTEGER REFERENCES chunks(id),
    edge_type TEXT,  -- 'cross_ref', 'hierarchy', 'entity_coref', 'sequential'
    weight REAL DEFAULT 1.0,
    UNIQUE(source_chunk_id, target_chunk_id, edge_type)
);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_chunk_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_chunk_id);

CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    strategy TEXT,  -- 'vector', 'graph', 'hybrid'
    retrieved_ids TEXT,
    answer TEXT,
    model TEXT,
    latency_ms REAL,
    timestamp TEXT DEFAULT (datetime('now'))
);
"""


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------
def chunk_markdown(text: str, source_path: str = "") -> list[dict]:
    """Split markdown into heading-aware chunks."""
    chunks = []
    current_heading = ""
    lines = text.split("\n")
    buffer = []
    buf_len = 0

    def flush():
        nonlocal buffer, buf_len
        if buffer:
            chunk_text = "\n".join(buffer).strip()
            if chunk_text:
                chunks.append({
                    "heading": current_heading,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                })
            buffer = []
            buf_len = 0

    for line in lines:
        # Detect headings
        heading_match = re.match(r"^(#{1,4})\s+(.+)", line)
        if heading_match:
            flush()
            current_heading = heading_match.group(2).strip()

        buffer.append(line)
        buf_len += len(line) + 1

        if buf_len >= CHUNK_SIZE:
            # Try to break at paragraph boundary
            text_so_far = "\n".join(buffer)
            last_blank = text_so_far.rfind("\n\n")
            if last_blank > CHUNK_SIZE // 3:
                keep = text_so_far[:last_blank].strip()
                remainder = text_so_far[last_blank:].strip()
                if keep:
                    chunks.append({
                        "heading": current_heading,
                        "text": keep,
                        "char_count": len(keep),
                    })
                buffer = [remainder] if remainder else []
                buf_len = len(remainder) if remainder else 0
            else:
                flush()

    flush()
    return chunks


def extract_entities(text: str) -> list[tuple[str, str]]:
    """Extract named entities using pattern matching (no ML dependency)."""
    entities = []

    # Model names
    for m in re.finditer(r"\b(Gemma\s*[234]?\s*(?:E[24]B|31B|26B|4B|2B|e[24]b)(?:-it)?)\b", text, re.I):
        entities.append((m.group(1).strip(), "model"))
    for m in re.finditer(r"\b(GPT-4o?(?:-mini)?|Claude\s*3\.?5?\s*(?:Haiku|Sonnet|Opus)?|Llama\s*[34]\s*\w*|Qwen\s*[23]\s*\w*)\b", text, re.I):
        entities.append((m.group(1).strip(), "model"))

    # Benchmark names
    for m in re.finditer(r"\b(MMLU(?:-Pro)?|GSM8K|HumanEval\+?|HellaSwag|ARC(?:-Challenge|-C)?|TruthfulQA|MATH|MBPP|IFEval|RULER)\b", text):
        entities.append((m.group(1), "benchmark"))

    # Organizations
    for m in re.finditer(r"\b(Google|OpenAI|Anthropic|Meta|Alibaba|NVIDIA|Unsloth|Ollama)\b", text):
        entities.append((m.group(1), "org"))

    # Places (civic domain)
    for m in re.finditer(r"\b(Normal|Illinois|Chicago|ISU|Illinois State University|Bloomington)\b", text, re.I):
        entities.append((m.group(1).strip(), "place"))

    # Technical concepts
    for m in re.finditer(r"\b(QLoRA|LoRA|GGUF|PEFT|RAG|GraphRAG|KV[- ]?cache|MoE|bitsandbytes|NF4|Q4_K_M)\b", text, re.I):
        entities.append((m.group(1), "concept"))

    # Deduplicate
    seen = set()
    unique = []
    for name, etype in entities:
        key = (name.lower(), etype)
        if key not in seen:
            seen.add(key)
            unique.append((name, etype))
    return unique


def extract_cross_references(text: str) -> list[str]:
    """Extract markdown links and file references."""
    refs = []
    # [text](path) links
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        target = m.group(2)
        if not target.startswith("http"):
            refs.append(target)
    # Backtick file references
    for m in re.finditer(r"`([a-zA-Z0-9_/\-]+\.\w{1,5})`", text):
        refs.append(m.group(1))
    return refs


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            log.info(f"Loaded SentenceTransformer (dim={_embedder.get_sentence_embedding_dimension()})")
        except ImportError:
            log.warning("sentence-transformers not found, using random embeddings (TESTING ONLY)")
            class FakeEmbedder:
                def encode(self, texts, **kw):
                    return np.random.randn(len(texts), EMBEDDING_DIM).astype(np.float32)
                def get_sentence_embedding_dimension(self):
                    return EMBEDDING_DIM
            _embedder = FakeEmbedder()
    return _embedder


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------
def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    return conn


def index_markdown_file(conn: sqlite3.Connection, filepath: Path,
                        doc_type: str = "knowledge") -> int:
    """Index a single markdown file into GraphRAG."""
    rel_path = str(filepath)
    text = filepath.read_text(encoding="utf-8", errors="replace")

    # Upsert document
    existing = conn.execute(
        "SELECT id FROM documents WHERE path = ?", (rel_path,)
    ).fetchone()
    if existing:
        doc_id = existing[0]
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
    else:
        cur = conn.execute(
            "INSERT INTO documents (path, title, doc_type, char_count) VALUES (?, ?, ?, ?)",
            (rel_path, filepath.stem, doc_type, len(text)),
        )
        doc_id = cur.lastrowid

    # Chunk
    chunks = chunk_markdown(text, rel_path)
    chunk_ids = []

    for idx, chunk in enumerate(chunks):
        text_hash = hashlib.sha256(chunk["text"].encode()).hexdigest()
        cur = conn.execute(
            "INSERT OR REPLACE INTO chunks (doc_id, chunk_index, heading, text, text_hash, char_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, idx, chunk["heading"], chunk["text"], text_hash, chunk["char_count"]),
        )
        chunk_ids.append(cur.lastrowid)

        # Extract entities
        entities = extract_entities(chunk["text"])
        for name, etype in entities:
            conn.execute(
                "INSERT OR IGNORE INTO entities (name, entity_type) VALUES (?, ?)",
                (name, etype),
            )
            ent_id = conn.execute(
                "SELECT id FROM entities WHERE name = ? AND entity_type = ?",
                (name, etype),
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO chunk_entities (chunk_id, entity_id) VALUES (?, ?)",
                (cur.lastrowid, ent_id),
            )

        # Sequential edges (chunk N → chunk N+1)
        if idx > 0 and chunk_ids[idx - 1]:
            conn.execute(
                "INSERT OR IGNORE INTO edges (source_chunk_id, target_chunk_id, edge_type, weight) "
                "VALUES (?, ?, 'sequential', 0.5)",
                (chunk_ids[idx - 1], cur.lastrowid),
            )

    conn.execute(
        "UPDATE documents SET chunk_count = ? WHERE id = ?",
        (len(chunks), doc_id),
    )
    conn.commit()

    # Build embeddings for this doc's chunks
    doc_chunks = conn.execute(
        "SELECT id, text FROM chunks WHERE doc_id = ?", (doc_id,)
    ).fetchall()
    if doc_chunks:
        embedder = get_embedder()
        texts = [c[1] for c in doc_chunks]
        vectors = embedder.encode(texts, normalize_embeddings=True)
        for (cid, _), vec in zip(doc_chunks, vectors):
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (chunk_id, vector) VALUES (?, ?)",
                (cid, vec.tobytes()),
            )
        conn.commit()

    return len(chunks)


def build_entity_coref_edges(conn: sqlite3.Connection):
    """Create edges between chunks that share entities."""
    log.info("Building entity co-reference edges...")
    entities = conn.execute(
        "SELECT entity_id, GROUP_CONCAT(chunk_id) FROM chunk_entities GROUP BY entity_id"
    ).fetchall()
    edge_count = 0
    for ent_id, chunk_ids_str in entities:
        cids = [int(x) for x in chunk_ids_str.split(",")]
        if len(cids) < 2:
            continue
        # Connect all pairs (capped for large clusters)
        for i in range(min(len(cids), 20)):
            for j in range(i + 1, min(len(cids), 20)):
                conn.execute(
                    "INSERT OR IGNORE INTO edges (source_chunk_id, target_chunk_id, edge_type, weight) "
                    "VALUES (?, ?, 'entity_coref', 0.3)",
                    (cids[i], cids[j]),
                )
                edge_count += 1
    conn.commit()
    log.info(f"Created {edge_count} entity co-reference edges")


def build_full_index(db_path: Path = DB_PATH, force: bool = False) -> dict:
    """Index all knowledge markdown + docs markdown files."""
    conn = init_db(db_path)
    stats = {"documents": 0, "chunks": 0, "entities": 0, "edges": 0}

    # Index knowledge/ dir
    knowledge_dir = KNOWLEDGE_DIR
    if knowledge_dir.exists():
        for md_file in sorted(knowledge_dir.glob("**/*.md")):
            n = index_markdown_file(conn, md_file, doc_type="knowledge")
            log.info(f"  {md_file.name}: {n} chunks")
            stats["documents"] += 1
            stats["chunks"] += n

    # Index docs/ dir
    docs_dir = DOCS_DIR
    if docs_dir.exists():
        for md_file in sorted(docs_dir.glob("*.md")):
            n = index_markdown_file(conn, md_file, doc_type="doc")
            log.info(f"  {md_file.name}: {n} chunks")
            stats["documents"] += 1
            stats["chunks"] += n

    # Build entity edges
    build_entity_coref_edges(conn)

    stats["entities"] = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    stats["edges"] = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

    log.info(f"GraphRAG index: {stats}")
    conn.close()
    return stats


# ---------------------------------------------------------------------------
# Retrieval — three strategies
# ---------------------------------------------------------------------------
def _load_all_embeddings(conn) -> tuple[list[int], np.ndarray, list[str]]:
    rows = conn.execute(
        "SELECT c.id, e.vector, c.text FROM chunks c JOIN embeddings e ON c.id = e.chunk_id"
    ).fetchall()
    if not rows:
        return [], np.array([]), []
    ids = [r[0] for r in rows]
    vecs = np.array([np.frombuffer(r[1], dtype=np.float32) for r in rows])
    texts = [r[2] for r in rows]
    return ids, vecs, texts


def retrieve_vector(query: str, conn: sqlite3.Connection, top_k: int = TOP_K) -> list[dict]:
    """Pure vector similarity retrieval."""
    ids, vecs, texts = _load_all_embeddings(conn)
    if len(ids) == 0:
        return []
    embedder = get_embedder()
    q_vec = embedder.encode([query], normalize_embeddings=True)[0]
    scores = vecs @ q_vec
    top_idx = np.argsort(-scores)[:top_k]
    results = []
    for idx in top_idx:
        results.append({
            "chunk_id": ids[idx],
            "text": texts[idx],
            "score": float(scores[idx]),
            "strategy": "vector",
        })
    return results


def retrieve_graph(query: str, conn: sqlite3.Connection, top_k: int = TOP_K) -> list[dict]:
    """Graph-expanded retrieval: vector search → expand via edges → re-rank."""
    # Start with vector search (2x seeds)
    seeds = retrieve_vector(query, conn, top_k=top_k * 2)
    if not seeds:
        return []

    seed_ids = {s["chunk_id"] for s in seeds}
    seed_scores = {s["chunk_id"]: s["score"] for s in seeds}

    # Expand via graph edges
    expanded = {}
    for seed in seeds[:top_k]:
        cid = seed["chunk_id"]
        neighbors = conn.execute(
            "SELECT target_chunk_id, edge_type, weight FROM edges WHERE source_chunk_id = ? "
            "UNION ALL "
            "SELECT source_chunk_id, edge_type, weight FROM edges WHERE target_chunk_id = ?",
            (cid, cid),
        ).fetchall()
        for ncid, etype, weight in neighbors:
            if ncid not in seed_ids:
                # Propagated score = parent_score * edge_weight * 0.5
                prop_score = seed_scores[cid] * weight * 0.5
                if ncid in expanded:
                    expanded[ncid] = max(expanded[ncid], prop_score)
                else:
                    expanded[ncid] = prop_score

    # Fetch expanded chunk texts
    all_ids = list(seed_ids) + list(expanded.keys())
    all_scores = {**seed_scores, **expanded}

    results = []
    placeholders = ",".join("?" * len(all_ids))
    rows = conn.execute(
        f"SELECT id, text FROM chunks WHERE id IN ({placeholders})", all_ids
    ).fetchall()
    text_map = {r[0]: r[1] for r in rows}

    for cid in all_ids:
        if cid in text_map:
            results.append({
                "chunk_id": cid,
                "text": text_map[cid],
                "score": all_scores.get(cid, 0),
                "strategy": "graph" if cid in expanded else "vector",
            })

    results.sort(key=lambda x: -x["score"])
    return results[:top_k]


def retrieve_hybrid(query: str, conn: sqlite3.Connection, top_k: int = TOP_K) -> list[dict]:
    """Hybrid: merge vector + graph results with unified scoring."""
    vec_results = retrieve_vector(query, conn, top_k=top_k)
    graph_results = retrieve_graph(query, conn, top_k=top_k)

    # Merge by chunk_id, take max score
    merged = {}
    for r in vec_results + graph_results:
        cid = r["chunk_id"]
        if cid not in merged or r["score"] > merged[cid]["score"]:
            merged[cid] = r
            merged[cid]["strategy"] = "hybrid"

    results = sorted(merged.values(), key=lambda x: -x["score"])
    return results[:top_k]


# ---------------------------------------------------------------------------
# Generation with context
# ---------------------------------------------------------------------------
def generate_with_rag(query: str, chunks: list[dict],
                      model: str = "gemma4:e4b",
                      strategy: str = "hybrid") -> dict:
    """Generate answer using retrieved context via Ollama."""
    import httpx

    context = "\n\n---\n\n".join([
        f"[Relevance: {c['score']:.3f} | {c['strategy']}]\n{c['text'][:1500]}"
        for c in chunks
    ])

    system = (
        "You are Jemma SafeBrain, a civic AI assistant. Answer using ONLY the provided context. "
        "If context is insufficient, say so. Be specific with facts, numbers, dates."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
    ]

    t0 = time.time()
    try:
        resp = httpx.post(
            "http://127.0.0.1:11434/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("message", {}).get("content", "")
        latency = (time.time() - t0) * 1000
        return {"answer": answer, "model": model, "latency_ms": latency, "chunks_used": len(chunks)}
    except Exception as e:
        return {"answer": f"[Error: {e}]", "model": model, "latency_ms": 0, "chunks_used": 0}


def query(query_text: str, strategy: str = "hybrid",
          model: str = "gemma4:e4b", db_path: Path = DB_PATH) -> dict:
    """End-to-end GraphRAG query."""
    conn = sqlite3.connect(str(db_path))
    init_db(db_path)  # ensure tables exist

    retriever = {"vector": retrieve_vector, "graph": retrieve_graph, "hybrid": retrieve_hybrid}
    chunks = retriever.get(strategy, retrieve_hybrid)(query_text, conn)

    if not chunks:
        conn.close()
        return {"answer": "No relevant context found. Build index first.", "chunks": []}

    result = generate_with_rag(query_text, chunks, model=model, strategy=strategy)
    result["retrieved_chunks"] = chunks

    # Log query
    conn.execute(
        "INSERT INTO queries (query, strategy, retrieved_ids, answer, model, latency_ms) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (query_text, strategy,
         json.dumps([c["chunk_id"] for c in chunks]),
         result["answer"], model, result["latency_ms"]),
    )
    conn.commit()
    conn.close()
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Jemma GraphRAG")
    sub = parser.add_subparsers(dest="cmd")

    build_p = sub.add_parser("build", help="Build index from knowledge/ and docs/")
    build_p.add_argument("--force", action="store_true")

    query_p = sub.add_parser("query", help="Query the GraphRAG index")
    query_p.add_argument("question", type=str)
    query_p.add_argument("--strategy", choices=["vector", "graph", "hybrid"], default="hybrid")
    query_p.add_argument("--model", default="gemma4:e4b")

    stats_p = sub.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()

    if args.cmd == "build":
        stats = build_full_index(force=args.force)
        print(json.dumps(stats, indent=2))

    elif args.cmd == "query":
        result = query(args.question, strategy=args.strategy, model=args.model)
        print(f"\nAnswer ({result.get('model','?')}, {result.get('latency_ms',0):.0f}ms):")
        print(result["answer"])
        print(f"\nRetrieved {len(result.get('retrieved_chunks',[]))} chunks")

    elif args.cmd == "stats":
        conn = sqlite3.connect(str(DB_PATH))
        for table in ["documents", "chunks", "embeddings", "entities", "edges", "queries"]:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {cnt}")
        conn.close()

    else:
        parser.print_help()
