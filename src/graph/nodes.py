from src.graph.state import State
from src.pageindex.utils import get_nodes_by_ids
from src.pageindex.search.tree_search import (
    tree_search_agent,
    evaluator_agent,
    answer_question,
    extractor_agent
)
from src.core.logging import get_logger

logger = get_logger(__name__)

async def search_node(state: State) -> State:
    node_ids = await tree_search_agent(
        query=state["query"],
        page_index_structure=state["page_index_structure"],
        visited_node=set(state["visited_node"]),
        missing_info=state["missing_info"]
    )
    return {**state, 
            "node_queue": node_ids}

async def extract_and_evaluate_node(state: State) -> State:
    node_queue = state.get("node_queue", [])
    new_ids = [nid for nid in node_queue if nid not in state["visited_node"]]
    if not new_ids:
        return {**state, 
                "early_stop": True}
    visited_node = list(state["visited_node"])
    gathered_texts = list(state["gathered_texts"])
    gathered_titles = list(state["gathered_titles"])
    pages_number = list(state.get("pages_number", []))
    is_sufficient = False
    missing_info = state.get("missing_info", "")
    early_stop = False

    new_nodes = get_nodes_by_ids(state["page_index_structure"], new_ids)

    for node in new_nodes:
        nid = node.get("node_id", "")
        visited_node.append(nid)        
        logger.info(f"EXTRACT NODE: [{nid}], TITLE: {node['title']}")
        extraction_result = await extractor_agent(
            query=state["query"], 
            node_title=node["title"], 
            node_text=node.get("text", "")
        )
        if not extraction_result.has_relevant_info:
            logger.info(f"SKIP NODE {nid} : Tidak ada info relevan (Alasan: {extraction_result.thinking})")
            continue # Lewati Evaluator, langsung ke node berikutnya di queue
            
        logger.info(f"Informasi relevan ditemukan, Menambahkan ke Knowledge Stack.")
        
        # Masukkan hasil ekstraksi ke Stack
        gathered_titles.append(node["title"])
        gathered_texts.append(f"[Section: {node['title']}]\n{extraction_result.extracted_info}")
        start_pages = node.get("start_index", 0)
        end_pages = node.get("end_index", 0)
        if isinstance(start_pages, int) and isinstance(end_pages, int):
            node_pages = list(range(start_pages, end_pages + 1))
        else:
            node_pages = []
        pages_number.append(node_pages)

        is_sufficient, missing_info = await evaluator_agent(state["query"], gathered_texts)
        logger.info(f"EVALUATOR -> is_sufficient: {is_sufficient} | Missing: {missing_info}")

        if is_sufficient:
            early_stop = True
            break 

    return {
        **state,
        "visited_node": visited_node,
        "gathered_texts": gathered_texts,
        "gathered_titles": gathered_titles,    
        "pages_number": pages_number,   
        "is_sufficient": is_sufficient,
        "missing_info": missing_info,
        "early_stop": early_stop,
        "iterations": state.get("iterations", 0) + 1,
        "node_queue": [] 
    }

async def generator_node(state: State) -> State:
    response = await answer_question(
        query=state["query"],
        gathered_texts=state["gathered_texts"],
        pages_number=state["pages_number"]
    )
    return {
        **state, 
        "answer": response["answer"],
        "citations": response["citations"]
    }