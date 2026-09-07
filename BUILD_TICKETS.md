# Build Tickets

Work these in order. Each ticket has a clear deliverable and test that proves it works before moving on. Don't skip ahead — each one builds on the last.

---

## T-01: Project scaffold and config

**Goal:** Repo compiles, config loads, nothing else.

**Work:**
- Create all directories per the file structure in CLAUDE.md
- Write `pyproject.toml` with all dependencies
- Write `src/config.py` — load `.env`, validate required vars, export `Settings` dataclass
- Write `src/state.py` — `PipelineState` TypedDict with all fields, `Section` TypedDict
- Create all `__init__.py` files
- Write `.env.example`, `.gitignore`
- `pip install -e ".[dev]"` must succeed

**Test:**
```bash
pip install -e ".[dev]"
python -c "from src.state import PipelineState, Section; print('State OK')"
python -c "from src.config import load_config; print('Config loads')"
# Should print validation errors for missing env vars, not crash
```

**Done when:** Install succeeds, state imports, config validates or reports missing vars cleanly.

**Commit:** `feat: project scaffold, config, state definition`

---

## T-02: Graph skeleton with stub nodes

**Goal:** LangGraph graph compiles and runs end-to-end with stub nodes that pass state through unchanged.

**Work:**
- Write `src/nodes/intake.py` — stub: returns `{"brief_content": "stub", "client_name": "Stub Client"}`
- Write `src/nodes/analyze_site.py` — stub: returns `{"wp_existing_pages": []}`
- Write `src/nodes/generate.py` — stub: returns `{"sections": [], "generation_attempts": 1}`
- Write `src/nodes/review.py` — stub: returns `{"approval_status": "approved"}`
- Write `src/nodes/publish.py` — stub: returns `{"draft_urls": []}`
- Write `src/nodes/notify.py` — stub: returns `{"notification_sent": True}`
- Write `src/graph.py`:
  - Import all node functions
  - Build `StateGraph(PipelineState)`
  - Add nodes: intake → analyze_site → generate → review → (conditional) → publish → notify → END
  - Conditional edge from review: approved → publish, rejected + attempts < 3 → generate, else → END
  - Add `__main__` block with argparse: `--brief` and `--wp-url`
  - Compile graph

**Test:**
```bash
python -m src.graph --brief "test brief text" --wp-url "https://example.com"
# Should run all stubs in sequence and print final state
# Verify: all nodes execute in order (add a print per stub to confirm)
```

**Test the conditional edge:**
- Temporarily make review stub return `{"approval_status": "rejected", "generation_feedback": "shorter"}` and `generation_attempts` starts at 0
- Verify graph loops back to generate
- Set `generation_attempts` to 3, verify graph exits

**Done when:** Graph runs end-to-end with stubs. Conditional edges route correctly. No crashes.

**Commit:** `feat: langgraph skeleton with stub nodes and conditional routing`

---

## T-03: WordPress REST client

**Goal:** Can read pages from and create drafts on a WordPress site.

**Work:**
- Write `src/tools/wordpress.py`:
  - `get_pages(site_url, username, app_password) -> list[dict]` — GET `/wp-json/wp/v2/pages?per_page=100&status=publish,draft`, return `[{id, slug, title, status}]`
  - `create_draft_page(site_url, username, app_password, title, content, slug) -> dict` — POST `/wp-json/wp/v2/pages` with `status="draft"` (HARD-CODED, not a parameter)
  - `update_draft_page(site_url, username, app_password, page_id, title, content) -> dict` — POST `/wp-json/wp/v2/pages/{id}` with `status="draft"`
  - All use httpx with Basic Auth (username:app_password)
  - Return types are dicts with the fields we need, not raw API responses
  - Handle HTTP errors: 401 → clear auth error message, 404 → site not found, 5xx → retry once then error

**Test:**
```bash
# Unit test with respx mocking:
pytest tests/test_wordpress.py -v

# Test cases:
# 1. get_pages returns parsed page list from mocked 200 response
# 2. create_draft_page sends correct payload with status="draft"
# 3. create_draft_page — verify status="draft" is present in request body (THE critical safety test)
# 4. get_pages handles 401 with clear error message
# 5. get_pages handles empty site (0 pages) without crashing
```

**Fixture:** `tests/fixtures/wp_pages_response.json` — realistic WP pages API response (3-4 pages)

**Done when:** All 5 test cases pass. The `status="draft"` assertion is the one that matters most.

**Commit:** `feat: wordpress REST client with draft-only safety constraint`

---

## T-04: Claude tool use integration

**Goal:** Can call Claude with a tool definition and get structured section output back.

**Work:**
- Write `src/tools/claude_tools.py`:
  - `SECTION_TOOL` — the tool definition dict (name, description, input_schema) matching the `Section` shape
  - `generate_sections(brief: str, existing_pages: list[dict], feedback: str | None, api_key: str) -> list[Section]`
    - Build messages: system prompt (you are a web copywriter for agencies...) + user message (the brief + existing pages + optional feedback)
    - Call `anthropic.Anthropic().messages.create()` with model `claude-sonnet-4-20250514`, tool definitions, `tool_choice={"type": "tool", "name": "create_sections"}`
    - Parse tool use response → extract sections list
    - Return typed `list[Section]`
  - Handle API errors: rate limit → retry with backoff, auth error → clear message, malformed tool response → error

**Test:**
```bash
pytest tests/test_claude_tools.py -v

# Test cases:
# 1. generate_sections sends correct tool definition in API call (mock the API, inspect request)
# 2. generate_sections parses a valid tool_use response into list[Section]
# 3. generate_sections includes feedback in the prompt when provided
# 4. generate_sections handles API error without crashing
# 5. Tool definition schema matches Section TypedDict fields exactly
```

**Fixture:** `tests/fixtures/claude_tool_response.json` — a realistic `messages.create()` response with `tool_use` content block

**Done when:** All 5 tests pass. Tool definition matches state schema.

**Commit:** `feat: claude API integration with structured tool use`

---

## T-05: Google Docs client (optional input)

**Goal:** Can read a Google Doc's text content given a URL.

**Work:**
- Write `src/tools/google_docs.py`:
  - `read_doc(doc_url: str, service_account_path: str | None) -> str`
  - Extract doc ID from URL (regex: `/document/d/([a-zA-Z0-9_-]+)`)
  - If no service account configured → raise clear error suggesting local file instead
  - Use `google-api-python-client` with service account credentials
  - Return plain text content (not HTML)

**Test:**
```bash
pytest tests/test_google_docs.py -v

# Test cases:
# 1. Extracts doc ID from standard Google Docs URL
# 2. Extracts doc ID from /edit, /preview URL variants
# 3. Raises clear error when service account not configured
# 4. Returns text content from mocked API response
```

**Done when:** Tests pass. This is a nice-to-have node — if it's fiddly, skip and note in README that Google Docs is a planned integration.

**Commit:** `feat: google docs read-only client`

---

## T-06: Wire intake node

**Goal:** `intake` node reads a brief from file, raw text, or Google Doc URL.

**Work:**
- Replace stub in `src/nodes/intake.py`:
  - If `brief_source` starts with `https://docs.google.com` → call `google_docs.read_doc()`
  - If `brief_source` is a path to an existing `.md` or `.txt` file → read it
  - Otherwise → use `brief_source` as raw text
  - Extract `client_name`: first `# heading` in the brief, or first line, or `"Unknown Client"`
  - Return `{"brief_content": ..., "client_name": ...}`
  - On error → append to `errors` list, return empty brief_content

**Test:**
```bash
pytest tests/test_nodes.py::test_intake -v

# Test cases:
# 1. Reads local .md file, extracts client name from heading
# 2. Uses raw text when brief_source is not a file or URL
# 3. Handles missing file gracefully (error in state, no crash)
# 4. Extracts client name from "# Client Brief: Acme Corp" → "Acme Corp"
```

**Done when:** Node reads sample_brief.md and returns correct content + client name.

**Commit:** `feat: wire intake node with file/text/gdoc routing`

---

## T-07: Wire analyze_site node

**Goal:** `analyze_site` node fetches WP page structure.

**Work:**
- Replace stub in `src/nodes/analyze_site.py`:
  - Load WP credentials from config
  - Call `wordpress.get_pages()`
  - Return `{"wp_existing_pages": [...]}`
  - If WP is unreachable → append to `errors`, return empty list (don't halt — generate can work without it)

**Test:**
```bash
pytest tests/test_nodes.py::test_analyze_site -v

# Test cases:
# 1. Returns parsed page list from mocked WP response
# 2. Returns empty list + error message when WP is unreachable
# 3. Passes credentials correctly from config
```

**Done when:** Node returns page list from mocked WP, handles failures gracefully.

**Commit:** `feat: wire analyze_site node`

---

## T-08: Wire generate node

**Goal:** `generate` node calls Claude and produces structured sections.

**Work:**
- Replace stub in `src/nodes/generate.py`:
  - Build context from `brief_content` + `wp_existing_pages` + optional `generation_feedback`
  - Call `claude_tools.generate_sections()`
  - Increment `generation_attempts`
  - Return `{"sections": [...], "generation_attempts": n}`

**Test:**
```bash
pytest tests/test_nodes.py::test_generate -v

# Test cases:
# 1. Calls generate_sections with brief content and existing pages
# 2. Increments generation_attempts
# 3. Passes generation_feedback when present
# 4. Handles Claude API failure gracefully (error in state)
```

**Done when:** Node returns sections from mocked Claude response. Attempt counter increments.

**Commit:** `feat: wire generate node with claude tool use`

---

## T-09: Wire review node

**Goal:** `review` node displays sections and waits for human input.

**Work:**
- Replace stub in `src/nodes/review.py`:
  - Print header: `"=== REVIEW: {client_name} — {n} sections ==="`
  - For each section: print title, target page (or "NEW PAGE"), body (first 200 chars + "..."), meta description
  - Prompt: `"[a]pprove / [r]eject with feedback / [q]uit: "`
  - `a` → `{"approval_status": "approved"}`
  - `r` → capture feedback via `input("Feedback: ")` → `{"approval_status": "rejected", "generation_feedback": feedback}`
  - `q` → `{"approval_status": "rejected", "generation_attempts": 3}` (forces exit at conditional edge)

**Test:**
```bash
# This one is manual — it's a CLI interactive node
# Run the graph with real stubs except review:
python -m src.graph --brief examples/sample_brief.md --wp-url https://example.com
# Verify: sections display readably, approve/reject/quit all work
# Automated: monkeypatch input() in test to simulate approve and reject paths
```

**Done when:** Sections display cleanly in terminal. All three input paths work.

**Commit:** `feat: wire review node with CLI approval flow`

---

## T-10: Wire publish node

**Goal:** `publish` node creates WordPress drafts from approved sections.

**Work:**
- Replace stub in `src/nodes/publish.py`:
  - For each section in `sections`:
    - If `target_page` matches a slug in `wp_existing_pages` → call `wordpress.update_draft_page()` with the matching page ID
    - If `target_page` is None → call `wordpress.create_draft_page()`
  - Collect URLs from responses → `{"draft_urls": [...]}`
  - On partial failure (some pages fail) → create what you can, append errors for failures

**Test:**
```bash
pytest tests/test_nodes.py::test_publish -v

# Test cases:
# 1. Creates new draft page for section with target_page=None
# 2. Updates existing page for section with matching target_page slug
# 3. ALL WordPress calls use status="draft" (CRITICAL — assert on request body)
# 4. Handles partial failure (2 of 3 pages succeed, 1 fails)
# 5. Returns draft URLs for successful pages
```

**Done when:** All 5 tests pass. Test 3 is the safety gate — must explicitly assert `status="draft"` in every outgoing request.

**Commit:** `feat: wire publish node with draft-only constraint`

---

## T-11: Wire notify node

**Goal:** `notify` node confirms completion.

**Work:**
- Replace stub in `src/nodes/notify.py`:
  - Print summary: client name, number of drafts created, each URL on its own line
  - If `SLACK_WEBHOOK_URL` is set → POST summary to Slack
  - If `SENDGRID_API_KEY` + `NOTIFICATION_EMAIL` are set → send summary email
  - Both optional — stdout is always the primary output
  - Return `{"notification_sent": True}`

**Test:**
```bash
pytest tests/test_nodes.py::test_notify -v

# Test cases:
# 1. Prints summary to stdout with all draft URLs
# 2. Sends Slack webhook when configured (mock the POST, verify payload)
# 3. Works fine with no Slack/email configured (stdout only)
```

**Done when:** Summary prints. Optional integrations work when configured, don't break when absent.

**Commit:** `feat: wire notify node with optional slack/email`

---

## T-12: End-to-end integration test

**Goal:** Full graph runs with all APIs mocked. Verify state at every step.

**Work:**
- Write `tests/test_graph.py`:
  - Mock all external calls (WP API, Claude API, Google Docs)
  - Monkeypatch `review` node's `input()` to return `"a"` (approve)
  - Run graph with sample brief
  - Assert: state flows through all nodes in order
  - Assert: final state has `draft_urls` populated, `notification_sent=True`, `approval_status="approved"`
- Write a second test: reject → regenerate → approve path
  - Monkeypatch input sequence: first call returns `"r"` + feedback, second returns `"a"`
  - Assert: generate runs twice, `generation_attempts == 2`

**Test:**
```bash
pytest tests/test_graph.py -v

# Test cases:
# 1. Happy path: intake → analyze → generate → review(approve) → publish → notify → END
# 2. Reject-then-approve: intake → analyze → generate → review(reject) → generate → review(approve) → publish → notify → END
# 3. Triple reject exits: generate runs 3 times, graph exits without publishing
```

**Done when:** All 3 integration tests pass.

**Commit:** `test: end-to-end graph integration tests`

---

## T-13: Error handling hardening

**Goal:** Every failure mode has a graceful path.

**Work:**
- Review every node for unhandled exceptions
- Add try/except at node level — catch, append to `state["errors"]`, return partial state
- `graph.py`: after graph completes, if `errors` is non-empty, print error summary
- Config validation: `python -m src.config` prints a clear checklist of what's configured vs missing
- Timeout on all httpx calls: 30s default

**Test:**
```bash
pytest tests/ -v
# All existing tests still pass

# Additional test cases:
# 1. Graph completes (doesn't crash) when WP site is unreachable
# 2. Graph completes when Claude API returns a malformed response
# 3. Config validation prints clear error for each missing required var
```

**Done when:** You cannot crash the pipeline with a missing API or bad response. It always exits cleanly with error messages.

**Commit:** `fix: error handling hardening across all nodes`

---

## T-14: Documentation

**Goal:** All markdown files written and accurate.

**Work:**
- Finalise `README.md` — verify quick start commands actually work
- Finalise `ARCHITECTURE.md` — graph diagram matches actual implementation
- Finalise `SETUP.md` — follow your own setup instructions from scratch on a clean machine
- Write `docs/DECISIONS.md` — 7 design decisions with rationale (see spec)
- Write `docs/DEMO_SCRIPT.md` — timestamped Loom script
- Write `CONTRIBUTING.md` — short, standard
- Update `examples/sample_brief.md` if the brief format changed during build
- Create `examples/sample_output.json` — actual output from a real run
- Create `examples/run_demo.sh` — one-liner that runs the pipeline with sample brief

**Test:**
```bash
# Follow SETUP.md from scratch — does it work?
# Run examples/run_demo.sh — does it run?
# Read README.md as a stranger — does it make sense in under 2 minutes?
```

**Done when:** Someone who has never seen this project can clone, setup, and run the demo by following the docs alone.

**Commit:** `docs: complete all project documentation`

---

## T-15: Demo recording

**Goal:** Loom video recorded, linked in README.

**Work:**
- Set up LocalWP with a test WordPress site (avoids remote site going down during recording)
- Populate WP site with 2-3 existing pages (Home, About) to show the page-matching feature
- Follow `docs/DEMO_SCRIPT.md` exactly
- Record in one take if possible — agency teams value directness over polish
- Upload to Loom, add link to README under the Demo section
- Create `examples/sample_output.json` from the actual demo run

**Test:**
```
# Watch your own Loom:
# - Is it under 4 minutes?
# - Do you show the rejection + feedback loop?
# - Do you show the drafts in WordPress admin?
# - Do you mention the safety constraint (draft-only)?
# - Is the repo link visible?
```

**Done when:** Loom is uploaded, linked in README, and you'd be comfortable with a hiring manager watching it.

**Commit:** `docs: add demo video link`
