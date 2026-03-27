import json
from src.pageindex.utils import (remove_fields, ChatGPT_API_async, extract_json, get_nodes_by_ids, load_toc_with_text)
from src.core.logging import get_logger
from pydantic import BaseModel, Field
from src.services.llm_service import get_llm
from langchain_core.output_parsers import StrOutputParser
logger = get_logger(__name__)

navigator_llm = get_llm(model_id="amazon.nova-pro-v1:0", max_tokens=300, streaming=False, temperature=0.0)
async def navigator_agent(query: str, structure: dict, visited_ids: set, missing_info: str) -> list[str]:
    table_of_contents = json.dumps(remove_fields(structure, fields=["text"]), indent=2, ensure_ascii=False)
    # logger.info(f"TABLE OF CONTENTS : {table_of_contents}")
    visited_info = (
        f"Already visited node IDs (DO NOT select these): {list(visited_ids)}"
        if visited_ids else "No nodes visited yet."
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
- Reply ONLY in the following JSON format:
{{
  "thinking": "<reasoning why these nodes contain the missing info/answer>",
  "node_list": ["node_id_1", "node_id_3", "node_id_n"]
}}"""

    response = await ChatGPT_API_async(prompt=prompt, llm=navigator_llm)
    result = extract_json(response)
    return result.get("node_list", [])


def extract_text_from_nodes(nodes: list[dict]) -> list[str]:
    return [
        f"[Section: {n['title']}]\n{n.get('text', '')}"
        for n in nodes
    ]

class ExtractorOutput(BaseModel):
    thinking: str = Field(description="<reasoning why these information is relevant to answer the query>")
    extracted_info: str = Field(description="extracted information results")
    has_relevant_info: bool = Field(description="True if there is relevant information, False otherwise")

extractor_llm = get_llm(model_id = "global.amazon.nova-2-lite-v1:0", temperature=0.0, max_tokens=1200, streaming=False).with_structured_output(ExtractorOutput)
async def extractor_agent(query: str, node_title: str, node_text: str) -> str:
    prompt = f"""
    # EXPERT IDENTITY
    - You are an Expert Information Extraction Agent. 
    - Your primary goal is to extract relevant information from a given text to answer the Query.
    
    # INSTRUCTIONS
    Given the User Query: "{query}"
    Extract ONLY the information from the following text that relevant to answer the query. 
    
    Section Title: {node_title}

    Text: {node_text}
    """
    result = await extractor_llm.ainvoke(prompt)
    return result

evaluator_llm = get_llm(model_id = "amazon.nova-pro-v1:0", temperature=0.0, max_tokens=200, streaming=False) 
async def evaluator_agent(
    query: str,
    gathered_texts: list[str],
) -> tuple[bool, str]:
    """
    Step 4: Cek apakah informasi yang terkumpul sudah cukup untuk menjawab.
    Returns (sufficient: bool, reason: str)
    """
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
Reply ONLY in the following valid JSON format:
{{
  "thinking": "Briefly explain if the core intent is met and why it is sufficient or strictly missing.",
  "sufficient": "yes" or "no",
  "missing_info": "<what is still missing, or 'nothing' if sufficient>"
}}"""

    response = await ChatGPT_API_async(prompt=prompt, llm=evaluator_llm)
    result = extract_json(response)
    is_sufficient = result.get("sufficient", "no") == "yes"
    missing_info = result.get("missing_info")
    return is_sufficient, missing_info


# Hapus import json/dll yang tidak perlu untuk bagian ini
generator_llm = get_llm(model_id="amazon.nova-pro-v1:0", temperature=0.1, max_tokens=700, streaming=True)
generator_chain = generator_llm | StrOutputParser()

async def answer_question(
    query: str,
    gathered_texts: list[str],
    pages_number: list[list[int]] 
) -> dict: 
    if not gathered_texts:
        return {
            "answer": "Tidak ditemukan informasi yang relevan dalam dokumen.",
            "citations": {}
        }

    context_blocks = []
    citations = {} 

    for i, (text, pages) in enumerate(zip(gathered_texts, pages_number)):
        ref_id = str(i + 1)
        context_blocks.append(f"[{ref_id}]\n{text}")
        if not pages:
            page_str = "[]"
        elif len(pages) == 1:
            page_str = f"Hal {pages[0]}."
        else:
            page_str = f"Hal {pages[0]} - {pages[-1]}."
        citations[f"[{ref_id}]"] = page_str

    context = "\n\n".join(context_blocks)

    prompt = f"""Anda adalah asisten AI analitis yang sangat ketat terhadap referensi data. 
Tugas Anda adalah menjawab pertanyaan HANYA berdasarkan informasi dari konteks yang diberikan selengkap mungkin

<aturan_wajib>
1. Anda WAJIB menyertakan ID referensi (misal: [1]) untuk fakta yang diambil dari konteks.
2. PENTING (ATURAN KENYAMANAN MEMBACA): Jika beberapa kalimat berurutan atau satu paragraf penuh berasal dari SUMBER YANG SAMA, JANGAN mengulang ID di setiap kalimat! Cukup letakkan ID tersebut SATU KALI saja di akhir paragraf.
3. Gunakan format persis seperti ini: [X] (contoh: [1], [2]).
4. Jika dalam satu paragraf terdapat informasi dari referensi yang berbeda, gabungkan di akhir paragraf seperti ini: [1][2].
</aturan_wajib>

<konteks>
{context}
</konteks>

<pertanyaan>
{query}
</pertanyaan>
"""
    result = await generator_chain.ainvoke(prompt)
    
    return {
        "answer": result,
        "citations": citations
    }