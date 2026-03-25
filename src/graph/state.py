from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage

class RAGState(TypedDict):
    query: str                       
    structure: list                  
    visited_ids: list[str]            
    gathered_texts: list[str]        
    gathered_titles: list[str]        
    is_sufficient: bool                  
    missing_info: str                      
    iterations: int                   
    early_stop: bool                  
    answer: str
    chat_history: list[BaseMessage]
    _pending_node_ids: list[str]
    pages_number: list[list[int]]
    citations: dict