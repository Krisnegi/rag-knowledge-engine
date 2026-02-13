from langgraph.graph import END, StateGraph
from src.agent.nodes import (
    retrieve,
    grade_documents,
    generate,
    web_search,
    route_question,
    grade_generation_v_documents_and_question,
)
from src.agent.state import GraphState


def build_agent_graph():
    workflow = StateGraph(GraphState)

    # Add Nodes
    workflow.add_node("web_search", web_search)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)

    # Define the Edges

    # 1. Entry Point: Conditional Logic based on Router
    workflow.set_conditional_entry_point(
        route_question,
        {
            "web_search": "web_search",
            "vectorstore": "retrieve",
        },
    )

    # 2. Edges from Retrieval/Search to Grading
    workflow.add_edge("web_search", "grade_documents")
    workflow.add_edge("retrieve", "grade_documents")

    # 3. Conditional Edge: Grade Documents -> Generate OR Web Search (if docs irrelevant)

    def decide_to_generate(state):
        if state["web_search"] == "Yes":
            return "web_search"
        else:
            return "generate"

    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "web_search": "web_search",
            "generate": "generate",
        },
    )

    # 4. Conditional Edge: Hallucination Check -> End OR Regenerate
    workflow.add_conditional_edges(
        "generate",
        grade_generation_v_documents_and_question,
        {
            "useful": END,               # If good, finish
            # If hallucinated, try generating again (Simple loop)
            "not supported": "generate",
            # "not supported": "web_search" # Alternatively, fall back to web search
        },
    )

    app = workflow.compile()
    return app
