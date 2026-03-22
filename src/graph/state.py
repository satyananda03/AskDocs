from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage

class RAGState(TypedDict):
    # Input
    query: str                       
    # Document
    structure: list                  
    # Search state
    visited_ids: list[str]            
    gathered_texts: list[str]        
    gathered_titles: list[str]        # untuk display ke user
    # Control flow
    is_sufficient: bool                  # hasil is_sufficient
    missing_info: str                      # apa yang masih kurang
    iterations: int                   # counter
    early_stop: bool                  # flag dari consumer loop
    # Output
    answer: str
    # Chat
    chat_history: list[BaseMessage]   # untuk multi-turn
    _pending_node_ids: list[str]