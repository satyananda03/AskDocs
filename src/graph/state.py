from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage

class State(TypedDict):
    query: str                       
    page_index_structure: list                        
    gathered_texts: list[str]        
    gathered_titles: list[str]        
    is_sufficient: bool                  
    missing_info: str                      
    iterations: int                   
    early_stop: bool                  
    answer: str
    chat_history: list[BaseMessage]
    node_queue: list[str]
    visited_node: list[str]      
    pages_number: list[list[int]]
    citations: dict