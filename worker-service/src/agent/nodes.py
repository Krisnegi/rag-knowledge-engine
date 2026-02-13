from langchain_core.documents import Document
from langchain_tavily import TavilySearch
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser
from typing import Literal

# Import from our new utils adapter
from src.utils import get_llm, get_retriever

# --- 1. ROUTER NODE ---


class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""
    datasource: str = Field(
        ...,
        description="Given a user question choose to route it to web_search or vectorstore.",
    )


def route_question(state):
    print("---ROUTE QUESTION---")
    question = state["question"]

    llm = get_llm()
    structured_llm_router = llm.with_structured_output(RouteQuery)

    system = """You are an expert at routing a user question to a vectorstore or web search.
    The vectorstore contains documents specifically ingested by the user.
    Use the vectorstore for questions about the context provided by the user.
    Otherwise, use web-search."""

    route_prompt = ChatPromptTemplate.from_messages(
        [("system", system), ("human", "{question}")]
    )

    router = route_prompt | structured_llm_router
    source = router.invoke({"question": question})

    if source.datasource == "web_search":
        print("---ROUTE: WEB SEARCH---")
        return "web_search"
    else:
        print("---ROUTE: VECTORSTORE---")
        return "vectorstore"

# --- 2. RETRIEVAL NODE ---


def retrieve(state):
    print("---RETRIEVE FROM PINECONE---")
    question = state["question"]
    user_id = state["user_id"]

    # Get the retriever for this specific user
    retriever = get_retriever(user_id)
    documents = retriever.invoke(question)

    return {"documents": documents, "question": question}

# --- 3. WEB SEARCH NODE ---


def web_search(state):
    print("---WEB SEARCH (Tavily)---")
    question = state["question"]

    tool = TavilySearch(max_results=3)
    response = tool.invoke({"query": question})
    tavily_results = response.get("results", [])

    # Convert Tavily JSON results to a standard string format
    web_results = "\n".join([d["content"] for d in tavily_results])
    web_documents = [Document(page_content=web_results)]

    return {"documents": web_documents, "question": question}


# --- 4. RELEVANCE GRADER ---
class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""
    binary_score: Literal["yes", "no"] = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )


def grade_documents(state):
    print("---CHECK DOCUMENT RELEVANCE---")
    question = state["question"]
    documents = state["documents"]
    llm = get_llm()
    structured_llm_grader = llm.with_structured_output(GradeDocuments)

    system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
    If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
    Return ONLY valid JSON in one of the following formats:
    {{"binary_score": "yes"}} OR {{"binary_score": "no"}}
    No extra text."""

    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human",
             "Retrieved document: \n\n {document} \n\n User question: {question}"),
        ]
    )

    retrieval_grader = grade_prompt | structured_llm_grader

    filtered_docs = []
    web_search = "No"

    for d in documents:
        score = retrieval_grader.invoke(
            {"question": question, "document": d.page_content})
        if score.binary_score == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            # If ANY doc is irrelevant, we might want to fall back to web search
            web_search = "Yes"
            continue

    return {"documents": filtered_docs, "question": question, "web_search": web_search}


# --- 5. GENERATION NODE ---


def generate(state):
    print("---GENERATE ANSWER---")
    question = state["question"]
    documents = state["documents"]
    loop_count = state.get("generation_loop_count", 0)  # Get current count

    llm = get_llm()

    prompt = ChatPromptTemplate.from_template(
        """You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Keep the answer concise.
        
        Question: {question} 
        Context: {context} 
        Answer:"""
    )

    # LangChain Expression Language (LCEL) Chain
    rag_chain = prompt | llm | StrOutputParser()

    generation = rag_chain.invoke({"context": documents, "question": question})
    return {
        "documents": documents,
        "question": question,
        "generation": generation,
        "generation_loop_count": loop_count + 1  # Increment loop count
    }


# --- 6. HALLUCINATION GRADER ---
def grade_generation_v_documents_and_question(state):
    print("---CHECK HALLUCINATIONS & RELEVANCE---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    loop_count = state.get("generation_loop_count", 0)

    # --- SAFETY CHECK: MAX RETRIES ---
    if loop_count > 2:  # Max 2 retries (Total 3 attempts)
        print("---DECISION: MAX RETRIES EXCEEDED. ACCEPTING ANSWER AS IS.---")
        return "useful"  # Force exit

    llm = get_llm()

    # --- CHECK 1: Hallucinations (Groundedness) ---
    class GradeHallucinations(BaseModel):
        binary_score: Literal["yes", "no"] = Field(
            description="Answer is grounded in the facts, 'yes' or 'no'")

    structured_llm_grader = llm.with_structured_output(GradeHallucinations)
    system = "You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts."
    hallucination_prompt = ChatPromptTemplate.from_messages(
        [("system", system), ("human",
                              "Set of facts: \n\n {documents} \n\n LLM generation: {generation}")]
    )

    hallucination_grader = hallucination_prompt | structured_llm_grader

    docs_text = "\n\n".join(d.page_content for d in documents)
    score = hallucination_grader.invoke(
        {"documents": docs_text, "generation": generation})

    if score.binary_score == "no":
        print("---DECISION: GENERATION IS NOT GROUNDED (HALLUCINATION)---")
        return "not supported"  # Triggers retry

    # --- CHECK 2: Answer Relevance (Does it actually answer?) ---
    # We only check this if it passed the first check!
    print("---DECISION: GENERATION IS GROUNDED, CHECKING RELEVANCE---")

    class GradeAnswer(BaseModel):
        binary_score: Literal["yes", "no"] = Field(
            description="Answer addresses the question, 'yes' or 'no'")

    structured_llm_grader_answer = llm.with_structured_output(GradeAnswer)
    system_answer = "You are a grader assessing whether an answer addresses / resolves a question."
    answer_prompt = ChatPromptTemplate.from_messages(
        [("system", system_answer), ("human",
                                     "User question: \n\n {question} \n\n LLM generation: {generation}")]
    )

    answer_grader = answer_prompt | structured_llm_grader_answer
    score_answer = answer_grader.invoke(
        {"question": question, "generation": generation})

    if score_answer.binary_score == "yes":
        print("---DECISION: GENERATION IS USEFUL---")
        return "useful"
    else:
        print("---DECISION: GENERATION IS NOT RELEVANT---")
        return "not supported"  # Triggers retry (or could trigger web_search)
