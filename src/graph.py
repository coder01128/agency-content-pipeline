from __future__ import annotations

import argparse
import json

from langgraph.graph import END, StateGraph

from src.nodes.analyze_site import analyze_site
from src.nodes.generate import generate
from src.nodes.intake import intake
from src.nodes.notify import notify
from src.nodes.publish import publish
from src.nodes.review import review
from src.state import PipelineState

MAX_GENERATION_ATTEMPTS = 3


def route_after_review(state: PipelineState) -> str:
    if state.get("approval_status") == "approved":
        return "publish"
    if state.get("generation_attempts", 0) >= MAX_GENERATION_ATTEMPTS:
        return END
    return "generate"


def build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("intake", intake)
    graph.add_node("analyze_site", analyze_site)
    graph.add_node("generate", generate)
    graph.add_node("review", review)
    graph.add_node("publish", publish)
    graph.add_node("notify", notify)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "analyze_site")
    graph.add_edge("analyze_site", "generate")
    graph.add_edge("generate", "review")
    graph.add_conditional_edges("review", route_after_review)
    graph.add_edge("publish", "notify")
    graph.add_edge("notify", END)

    return graph


def compile_graph():
    return build_graph().compile()


def main() -> None:
    parser = argparse.ArgumentParser(description="Agency Content Pipeline")
    parser.add_argument("--brief", required=True, help="Brief text, file path, or Google Doc URL")
    parser.add_argument("--wp-url", required=True, help="WordPress site URL")
    args = parser.parse_args()

    app = compile_graph()

    initial_state: PipelineState = {
        "brief_source": args.brief,
        "wp_site_url": args.wp_url,
        "generation_attempts": 0,
        "errors": [],
    }

    print("--- Running Agency Content Pipeline ---\n")
    final_state = app.invoke(initial_state)
    print("\n--- Final State ---")
    print(json.dumps({k: v for k, v in final_state.items()}, indent=2, default=str))


if __name__ == "__main__":
    main()
