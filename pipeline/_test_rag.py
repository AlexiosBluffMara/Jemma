"""Quick RAG test"""
import sys
sys.path.insert(0, "pipeline")
from rag_engine import retrieve

results = retrieve("Town of Normal budget and finance information")
print(f"Retrieved {len(results)} chunks:")
for i, r in enumerate(results):
    score = r["score"]
    src = r["source_type"]
    sid = r["source_id"]
    print(f"\n--- Chunk {i+1} (score={score:.3f}, {src} #{sid}) ---")
    print(r["text"][:300])
