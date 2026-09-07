# Agency Content Pipeline — Claude Code Reference

## What This Is

A LangGraph agent that turns a client brief into WordPress draft pages with human approval. Portfolio piece demonstrating agentic workflow design for an AI Engineer role at a web agency.

## Tech Stack

- **Python 3.11+** — primary language
- **LangGraph >=0.2** — state machine orchestration
- **langchain-core >=0.3** — base abstractions (do NOT pull full langchain, only core)
- **anthropic >=0.40** — Claude API client (tool use, structured output)
- **httpx >=0.27** — async HTTP client for WordPress REST API and Google Docs
- **python-dotenv** — env loading
- **pytest + respx** — testing with mocked HTTP

## Project Structure

```
src/
  graph.py          — LangGraph graph: node wiring, conditional edges, compile
  state.py          — PipelineState TypedDict (single source of truth for state shape)
  config.py         — load .env, validate all required vars, export a Settings dataclass
  nodes/            — one file per graph node, each exports a single function
    intake.py       — read brief from Google Doc URL, local file, or raw text
    analyze_site.py — GET WordPress pages via REST API
    generate.py     — Claude API call with tool use → structured sections
    review.py       — CLI human approval checkpoint
    publish.py      — POST WordPress draft pages via REST API
    notify.py       — print summary, optional Slack/email
  tools/            — external API clients, no business logic
    claude_tools.py — tool definitions + Anthropic API call wrapper
    wordpress.py    — WP REST client: get_pages(), create_draft()
    google_docs.py  — read-only doc fetch via service account
```

## Key Constraints

1. **Draft-only publishing** — `publish.py` MUST set `status="draft"` on every WP API call. Never `"publish"`. This is a safety invariant, not a config option. Hard-code it.
2. **Generation cap** — max 3 generation attempts before the graph exits. Prevents infinite review loops.
3. **Human-in-the-loop** — the `review` node blocks on CLI input. Nothing writes to WordPress until a human types `a` for approve.
4. **Google Docs is optional** — the pipeline must work with a local `.md` file. Google Docs is a bonus integration. Don't make it a hard dependency.
5. **No streaming in v1** — tool use responses arrive as complete blocks. Don't add streaming complexity.

## Code Conventions

- **Type hints everywhere** — every function signature fully typed
- **One node = one file = one function** — node functions take `PipelineState`, return partial `PipelineState` dict
- **Node function signature:** `def node_name(state: PipelineState) -> dict:`
- **No print() in nodes except review and notify** — use `errors` list in state for error reporting
- **httpx over requests** — we use httpx for all HTTP calls (sync is fine for v1)
- **Ruff for formatting** — `ruff check . && ruff format .`
- **Conventional commits** — `feat:`, `fix:`, `docs:`, `test:`

## Running

```bash
# Install
pip install -e ".[dev]"

# Validate config
python -m src.config

# Run with sample brief
python -m src.graph --brief examples/sample_brief.md --wp-url https://your-site.com

# Run tests
pytest tests/ -v
```

## Environment Variables

All loaded via `src/config.py`. See `.env.example` for the full list.

Required: `ANTHROPIC_API_KEY`, `WP_SITE_URL`, `WP_USERNAME`, `WP_APP_PASSWORD`
Optional: `GOOGLE_SERVICE_ACCOUNT_JSON`, `SLACK_WEBHOOK_URL`, `SENDGRID_API_KEY`, `NOTIFICATION_EMAIL`

## Testing Approach

- **Unit tests per node** — mock external APIs with `respx`, test state transformations
- **Graph integration test** — run full graph with all APIs mocked, verify state at each step
- **Fixtures in `tests/fixtures/`** — sample brief, mocked WP API responses, mocked Claude tool use responses
- **No live API calls in tests** — every external call is mocked

## Build Tickets

See `BUILD_TICKETS.md` for the sequenced build plan with per-ticket acceptance tests. Work through them in order — each ticket builds on the last.

## What NOT To Do

- Don't install full `langchain` — only `langchain-core` and `langgraph`
- Don't add a web UI for review — CLI is deliberate (see docs/DECISIONS.md)
- Don't add streaming — adds complexity, no demo value
- Don't auto-publish — draft status is a hard safety constraint
- Don't use LangChain's ChatAnthropic wrapper — use the `anthropic` SDK directly for tool use, it's cleaner and shows direct API knowledge
