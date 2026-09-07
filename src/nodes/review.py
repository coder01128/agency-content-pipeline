from __future__ import annotations

from src.state import PipelineState

MAX_GENERATION_ATTEMPTS = 3


def review(state: PipelineState) -> dict:
    client = state.get("client_name", "Unknown")
    sections = state.get("sections", [])

    print(f"\n=== REVIEW: {client} -- {len(sections)} sections ===\n")

    for i, section in enumerate(sections, 1):
        target = section.get("target_page") or "NEW PAGE"
        body = section.get("body", "")
        preview = body[:200] + "..." if len(body) > 200 else body

        print(f"--- Section {i}: {section['title']} [{target}] ---")
        print(preview)
        print(f"Meta: {section.get('meta_description', '')}")
        print()

    while True:
        choice = input("[a]pprove / [r]eject with feedback / [q]uit: ").strip().lower()

        if choice == "a":
            return {"approval_status": "approved"}

        if choice == "r":
            feedback = input("Feedback: ").strip()
            return {"approval_status": "rejected", "generation_feedback": feedback}

        if choice == "q":
            return {
                "approval_status": "rejected",
                "generation_attempts": MAX_GENERATION_ATTEMPTS,
            }

        print("Invalid choice. Enter a, r, or q.")
