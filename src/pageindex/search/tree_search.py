import json
from src.pageindex.utils import remove_fields
from src.core.logging import get_logger
from pydantic import BaseModel, Field
from src.services.llm_service import get_llm
from langchain_core.output_parsers import StrOutputParser
logger = get_logger(__name__)

class TreeSearchOutput(BaseModel):
    thinking: str = Field(description="reasoning why these nodes contain the missing info/answer")
    node_list: list[str] = Field(description="list of selected node IDs", default_factory=list)

tree_search_llm = get_llm(model_id="amazon.nova-pro-v1:0", max_tokens=300, streaming=False, temperature=0.0).with_structured_output(TreeSearchOutput)
async def tree_search_agent(query: str, page_index_structure: dict, visited_node: set, missing_info: str):
    table_of_contents = json.dumps(remove_fields(page_index_structure, fields=["text"]), indent=2, ensure_ascii=False)
    # logger.info(f"TABLE OF CONTENTS : {table_of_contents}")
    visited_info = (
        f"Already visited node IDs (DO NOT select these): {list(visited_node)}"
        if visited_node else "No nodes visited yet."
    )

    if missing_info :
        gap_instruction = f"CURRENT STATUS : We have gathered some info, but the following is STILL MISSING : {missing_info}\nTASK : Select UNVISITED node IDs most likely to contain this missing information."
    else:
        gap_instruction = "TASK : Find all nodes that are likely contain information to answer the Query."

    prompt = f"""
# EXPERT IDENTITY
- You are an Expert Information Retrieval Agent specializing in hierarchical document navigation. 
- Your objective is to systematically analyze a Document Table of Contents to find all nodes that are likely to contain relevant information to answer the Query

# INSTRUCTIONS

Query : {query}

Document Table of Contents :
{table_of_contents}

{visited_info}

{gap_instruction}

# IMPORTANT RULES 
- DO NOT select already visited nodes.
"""
    result = await tree_search_llm.ainvoke(prompt)
    return result.node_list

class ExtractorOutput(BaseModel):
    thinking: str = Field(description="<reasoning why these information is relevant to answer the query>")
    extracted_info: str = Field(description="extracted information results")
    has_relevant_info: bool = Field(description="True if there is relevant information, False otherwise")

extractor_llm = get_llm(model_id = "global.amazon.nova-2-lite-v1:0", temperature=0.0, max_tokens=1000, streaming=False).with_structured_output(ExtractorOutput)
async def extractor_agent(query: str, node_title: str, node_text: str):
    prompt = f"""
    # EXPERT IDENTITY
    - You are an Expert Information Extraction Agent. 
    - Your primary goal is to extract relevant information from a given text to answer the Query.
    
    # INSTRUCTIONS
    Given the User Query: "{query}"
    Extract the complete information from the following text that relevant to answer the query. 
    
    Section Title: {node_title}

    Text: {node_text}
    """
    result = await extractor_llm.ainvoke(prompt)
    return result

class EvaluatorOutput(BaseModel):
    thinking: str = Field(description="Briefly explain if the core intent is met and why it is sufficient or strictly missing.")
    sufficient: str = Field(description="'yes' or 'no'")
    missing_info: str = Field(description="what is still missing, or 'nothing' if sufficient")

evaluator_llm = get_llm(model_id = "amazon.nova-pro-v1:0", temperature=0.0, max_tokens=200, streaming=False).with_structured_output(EvaluatorOutput)     
async def evaluator_agent(query: str, gathered_texts: list[str]):
    if not gathered_texts:
        return False, "No information gathered yet."

    context = "\n---\n".join(gathered_texts)

    prompt = f"""
# EXPERT IDENTITY
- You are a Pragmatic Search Stopping Evaluator for a Document Retrieval System. Your primary goal is to determine if the system has gathered enough context to adequately answer the user's core Query. 
- Focus on providing a helpful and adequate information, instead of seeking exhaustively complete information.

# EVALUATION CRITERIA
1. Core Intent : Can the fundamental question be answered directly and accurately using ONLY the gathered information?
2. Pragmatic Sufficiency : Deem the information "sufficient" ('yes') if a helpful answer can be formulated right now. Do NOT demand perfectly comprehensive details if the main point is already addressed.
3. Critical Gaps : Only say 'no' if the core answer is completely missing, fundamentally flawed, or if a highly specific requested metric/fact is absent.

Query: {query}

Gathered information:
{context}

# INSTRUCTIONS
Based on the criteria above, evaluate the gathered information.
"""

    result = await evaluator_llm.ainvoke(prompt)
    is_sufficient = result.sufficient.strip().lower() == "yes"
    missing_info = result.missing_info
    return is_sufficient, missing_info


generator_llm = get_llm(model_id="amazon.nova-pro-v1:0", temperature=0.1, max_tokens=900, streaming=True)
generator_chain = generator_llm | StrOutputParser()
async def answer_question(query: str, gathered_texts: list[str], pages_number: list[list[int]]) -> dict: 
    if not gathered_texts:
        return {
            "answer": "Tidak ditemukan informasi yang relevan dalam dokumen.",
            "citations": {}
        }

    contexts = []
    citations = {} 
    for i, (text, pages) in enumerate(zip(gathered_texts, pages_number)):
        ref_id = str(i + 1)
        contexts.append(f"[{ref_id}]\n{text}")
        if not pages:
            page_str = "[]"
        elif len(pages) == 1:
            page_str = f"Halaman {pages[0]}"
        else:
            page_str = f"Halaman {pages[0]} - {pages[-1]}"
        citations[f"[{ref_id}]"] = page_str

    context = "\n\n".join(contexts)

    prompt = f"""You are a highly analytical AI assistant strictly bound by data references. 
Your task is to answer the query comprehensively using ONLY the provided context.

<mandatory_rules>
1. Citations: You MUST append reference IDs (e.g., [1]) to facts extracted from the context.
2. Readability: DO NOT repeat the same ID after every sentence. If consecutive sentences or an entire paragraph rely on the SAME source, place the ID ONCE at the end of the paragraph.
3. Format: Strictly use brackets for IDs (e.g., [1], [2]).
4. Multiple Sources: Combine IDs at the end of a paragraph if multiple sources are used (e.g., [1][2]).
</mandatory_rules>

<context>
{context}
</context>

<query>
{query}
</query>
"""
    result = await generator_chain.ainvoke(prompt)
    return {
        "answer": result,
        "citations": citations
    }

def extract_text_from_nodes(nodes: list[dict]) -> list[str]:
    return [
        f"[Section: {n['title']}]\n{n.get('text', '')}"
        for n in nodes
    ]