from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy # <--- TAMBAH INI
from src.services.embedding_service import get_embeddings
from typing import List, Dict
import math 
import json

embeddings = get_embeddings()

def load_vector_index(embeddings):
    return FAISS.load_local(
        "faiss_index_cosine", 
        embeddings, 
        allow_dangerous_deserialization=True,
        distance_strategy=DistanceStrategy.COSINE
    )

def value_based_node_search(query: str, vectorstore, all_nodes: List[Dict], top_k: int = 20, threshold: float = 0.2) -> List[Dict]: 
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    node_chunk_scores: Dict[str, List[float]] = {}
    for doc, score in results: 
        node_id = doc.metadata.get("node_id")
        if not node_id:
            continue
        similarity = float(score)
        if similarity < threshold:
            continue 
        node_chunk_scores.setdefault(node_id, []).append(similarity)
    
    # Hitung NodeScore per node
    node_scores = []
    for node_id, chunk_scores in node_chunk_scores.items():
        N = len(chunk_scores)
        node_score = (1 / math.sqrt(N + 1)) * sum(chunk_scores)
        node_scores.append({"node_id": node_id, "score": node_score})
    
    node_scores.sort(key=lambda x: x["score"], reverse=True)
    
    # Enrich dengan info node
    node_map = {n["node_id"]: n for n in all_nodes}
    for item in node_scores:
        node = node_map.get(item["node_id"], {})
        item["title"] = node.get("title", "")
        item["text"] = node.get("text", "")
        item["summary"] = node.get("summary", "")
    
    return node_scores


with open("index.json") as f:
    result = json.load(f)

structure = result["structure"]

def flatten_nodes(nodes: list) -> List[Dict]:
    flat = []
    for node in nodes:
        flat.append(node)
        if node.get("nodes"):
            flat.extend(flatten_nodes(node["nodes"]))
    return flat

all_nodes = flatten_nodes(structure)
print(f"Total nodes in memory: {len(all_nodes)}")

embeddings = get_embeddings()
vectorstore = load_vector_index(embeddings)

query = "siapa rafi ahmad"
ranked_nodes = value_based_node_search(query, vectorstore, all_nodes, top_k=15)

print(f"\nTop nodes untuk query: '{query}'\n")
for item in ranked_nodes[:3]:
    print(f"  [Score: {item['score']:.4f}] {item['title']} (node_id: {item['node_id']})")