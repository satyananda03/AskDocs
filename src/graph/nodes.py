from src.graph.state import RAGState
from src.pageindex.utils import get_nodes_by_ids
from src.pageindex.search.tree_search import (
    navigator_agent,
    evaluator_agent,
    answer_question,
    extractor_agent
)
from src.core.logging import get_logger

logger = get_logger(__name__)
async def navigator_node(state: RAGState) -> RAGState:
    node_ids = await navigator_agent(
        query=state["query"],
        structure=state["structure"],
        visited_ids=set(state["visited_ids"]),
        missing_info=state["missing_info"]
    )
    # Simpan queue di state sementara
    return {**state, "_pending_node_ids": node_ids}

async def extract_and_evaluate_node(state: RAGState) -> RAGState:
    pending_ids = state.get("_pending_node_ids", [])
    new_ids = [nid for nid in pending_ids if nid not in state["visited_ids"]]
    if not new_ids:
        return {**state, "early_stop": True}

    visited_ids = list(state["visited_ids"])
    gathered_texts = list(state["gathered_texts"])
    gathered_titles = list(state["gathered_titles"])
    is_sufficient = False
    missing_info = state.get("missing_info", "")
    early_stop = False

    new_nodes = get_nodes_by_ids(state["structure"], new_ids)

    for node in new_nodes:
        nid = node.get("node_id", "")
        visited_ids.append(nid)
        
        print(f"Membaca Node: [{nid}] {node['title']}")
        
        # ── 1. CONSUMER (Nova Lite) ───────────────────────────
        # Panggil extractor_agent yang mengembalikan Pydantic model
        extraction_result = await extractor_agent(
            query=state["query"], 
            node_title=node["title"], 
            node_text=node.get("text", "")
        )
        
        # Cek hasil dari Pydantic Field 'has_relevant_info'
        if not extraction_result.has_relevant_info:
            print(f"SKIP NODE {nid} : Tidak ada info relevan (Alasan: {extraction_result.thinking})")
            continue # ← BYPASS: Lewati Evaluator, langsung ke iterasi loop/node berikutnya
            
        print(f"Info ditemukan: Menambahkan ke Knowledge Stack.")
        
        # Masukkan hasil ekstraksi (BUKAN raw text) ke Stack
        gathered_titles.append(node["title"])
        gathered_texts.append(f"[Section: {node['title']}]\n{extraction_result.extracted_info}")
        
        # ── 2. EVALUATOR (Nova Pro) ───────────────────────────
        # Evaluator HANYA dipanggil jika ada info baru yang masuk ke Stack
        is_sufficient, missing_info = await evaluator_agent(state["query"], gathered_texts)
        print(f"Evaluasi -> Sufficient: {is_sufficient} | Missing: {missing_info}")

        if is_sufficient:
            early_stop = True
            break # ← EARLY STOP: Info sudah cukup, hentikan loop antrean

    return {
        **state,
        "visited_ids": visited_ids,
        "gathered_texts": gathered_texts,
        "gathered_titles": gathered_titles,       
        "is_sufficient": is_sufficient,
        "missing_info": missing_info,
        "early_stop": early_stop,
        "iterations": state.get("iterations", 0) + 1,
        "_pending_node_ids": [] # Bersihkan antrean karena sudah diproses semua/dihentikan
    }

async def generator_node(state: RAGState) -> RAGState:
    answer = await answer_question(
        state["query"],
        state["gathered_texts"]
    )
    return {**state, "answer": answer}