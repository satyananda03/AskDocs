import json
import math
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy 
from src.services.embedding_service import get_embeddings

# ── 1. Load index.json ────────────────────────────────────────
with open("index.json") as f:
    result = json.load(f)

structure = result["structure"]

# ── 2. Flatten semua node ─────────────────────────────────────
def flatten_nodes(nodes: list) -> List[Dict]:
    flat = []
    for node in nodes:
        flat.append(node)
        if node.get("nodes"):
            flat.extend(flatten_nodes(node["nodes"]))
    return flat

all_nodes = flatten_nodes(structure)
print(f"Total nodes: {len(all_nodes)}")

# ── 3. Chunking dengan RecursiveCharacterTextSplitter ─────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""]
)

documents = []  # LangChain Document objects
for node in all_nodes:
    node_id = node.get("node_id")
    text = node.get("text", "")
    if not text.strip():
        continue
    chunks = splitter.create_documents(
        texts=[text],
        metadatas=[{"node_id": node_id}]
    )
    documents.extend(chunks)

print(f"Total chunks: {len(documents)}")

# ── 4. Build FAISS via LangChain ──────────────────────────────
embeddings = get_embeddings()

# 2. TAMBAHKAN PARAMETER distance_strategy SAAT BUILD
vectorstore = FAISS.from_documents(
    documents, 
    embeddings,
    distance_strategy=DistanceStrategy.COSINE
)

# Simpan index dengan nama baru agar tidak tertukar dengan yang lama
vectorstore.save_local("faiss_index_cosine")

print("Done! FAISS index (Cosine Similarity) saved to local path")