from langgraph.graph import StateGraph, END
from src.graph.state import State
from src.graph.nodes import (
    generator_node,
    search_node,
    extract_and_evaluate_node,
)
from src.core.config import settings

def should_continue_search(state: State) -> str:
    if state["is_sufficient"] or state["early_stop"]:
        return "generator"          
    if state["iterations"] >= settings.max_search_iterations:
        return "generator"         
    return "navigator"

def build_rag_graph() -> StateGraph:
    graph = StateGraph(State)
    graph.add_node("navigator", search_node)
    graph.add_node("evaluator", extract_and_evaluate_node)
    graph.add_node("generator", generator_node)
    graph.set_entry_point("navigator")
    graph.add_edge("navigator", "evaluator")
    graph.add_conditional_edges("evaluator", should_continue_search, {
        "navigator": "navigator",
        "generator": "generator",
    })
    graph.add_edge("generator", END)
    return graph.compile()

aidocs_workflow = build_rag_graph()