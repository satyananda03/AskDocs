from langgraph.graph import StateGraph, END
from src.graph.state import RAGState
from src.graph.nodes import (
    generator_node,
    navigator_node,
    extract_and_evaluate_node,
)

def should_continue(state: RAGState) -> str:
    if state["is_sufficient"] or state["early_stop"]:
        return "generator"          
    if state["iterations"] >= 5:
        return "generator"         
    return "navigator"

def build_rag_graph() -> StateGraph:
    graph = StateGraph(RAGState)
    graph.add_node("navigator", navigator_node)
    graph.add_node("evaluator", extract_and_evaluate_node)
    graph.add_node("generator", generator_node)
    
    graph.set_entry_point("navigator")
    graph.add_edge("navigator", "evaluator")
    graph.add_conditional_edges("evaluator", should_continue, {
        "navigator": "navigator",
        "generator": "generator",
    })
    graph.add_edge("generator", END)
    return graph.compile()

aidocs_workflow = build_rag_graph()