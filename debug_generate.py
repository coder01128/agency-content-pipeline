from src.config import load_config
from src.tools.claude_tools import generate_sections

c = load_config()

try:
    result = generate_sections(
        brief="Build a 3-page site for a plumber in Phoenix. Pages: Home, Services, Contact.",
        existing_pages=[{"id": 1, "slug": "home", "title": "Home", "status": "publish"}],
        feedback=None,
        api_key=c.anthropic_api_key
    )
    print("SUCCESS:", len(result), "sections")
    for s in result:
        print(" -", s["title"], "| target:", s["target_page"])
except Exception as e:
    print("ERROR:", type(e).__name__)
    print(e)