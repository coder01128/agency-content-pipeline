# Design Decisions

## 1. LangGraph Over Raw LangChain Chains

**Context:** LangChain offers both chain-based composition and LangGraph's state machine model. Which one?

**Decision:** LangGraph with an explicit StateGraph.

**Rationale:** A content pipeline has branching logic (approve/reject), a feedback loop, and a safety gate. These are control flow decisions, not prompt chains. A state machine makes the flow visible, testable, and debuggable — you can inspect state at any node boundary. Chain-based composition hides control flow inside prompt engineering.

**Trade-off:** LangGraph has a steeper initial learning curve and more boilerplate for simple linear flows. Worth it here because the flow isn't linear.

## 2. Direct Anthropic SDK Over LangChain's ChatAnthropic

**Context:** LangChain provides a `ChatAnthropic` wrapper. We could also call the Anthropic Python SDK directly.

**Decision:** Use the `anthropic` SDK directly for the generate node.

**Rationale:** The core value of this project is demonstrating Anthropic API competence — function calling, tool definitions, structured output. Wrapping it in LangChain's abstraction hides the exact mechanics the hiring team wants to see. Direct SDK usage makes the tool definition, the `tool_choice` parameter, and the response parsing explicit and inspectable.

**Trade-off:** Lose LangChain's automatic retry and output parsing helpers. Acceptable — we handle retries manually and parsing is straightforward with tool use (the model returns structured JSON, not free text).

## 3. Tool Use Over Free-Text Generation

**Context:** Claude can return structured data either via tool use (the model calls a defined tool with typed arguments) or via a prompt that says "return JSON in this format."

**Decision:** Tool use with `tool_choice={"type": "tool", "name": "create_sections"}`.

**Rationale:** Tool use guarantees the response matches the schema. Free-text JSON requires parsing, validation, and handling of malformed output (markdown fences, extra commentary, missing fields). Tool use eliminates that entire class of bugs. It also demonstrates the specific API feature the role requires.

**Trade-off:** Slightly less flexible — the model can't add free-text commentary alongside the structured output. That's fine; we don't need commentary in the pipeline.

## 4. CLI Review Over Web UI

**Context:** The human approval step could be a web interface, a Slack interactive message, or a CLI prompt.

**Decision:** CLI prompt.

**Rationale:** The demo's purpose is the approval *pattern*, not the approval *interface*. A CLI implementation is trivial to build, dead simple to demo in a Loom, and eliminates an entire class of frontend complexity that would distract from the pipeline design. The architecture document notes webhook-based review as a production scaling path.

**Trade-off:** Can't demo to non-technical stakeholders as easily. Doesn't matter — the audience is the Blacksmith engineering team.

## 5. Draft-Only Publishing

**Context:** The publish node writes to WordPress. Should it support publishing live pages?

**Decision:** Hard-code `status="draft"` in every WordPress API call. Not configurable.

**Rationale:** An AI agent that can publish live content on a client's website without a second review step is a liability. Making draft-only a hard constraint (not a config flag) means there's no code path that accidentally publishes. The test suite explicitly asserts this on every outgoing request body.

**Trade-off:** If someone wants to extend this to auto-publish, they need to change the code and the tests. That friction is intentional.

## 6. Google Docs Deferred to Post-v1

**Context:** Briefs could come from Google Docs, local files, or raw text. How much weight to give each input path?

**Decision:** Local `.md` file and raw text are the only implemented input paths in v1. Google Docs integration is designed for but not built — the intake node has a clearly marked TODO where it would slot in.

**Rationale:** Google service account auth is the fiddliest part of the setup. Making it a v1 requirement would mean every person evaluating this repo hits a 15-minute auth detour before seeing the pipeline run. Local file input works immediately. The `pyproject.toml` includes Google API dependencies as an optional extra (`pip install -e ".[google]"`) so the integration path is ready.

**Trade-off:** One fewer integration to demo. Acceptable — the pipeline's value is in the LangGraph orchestration and Claude tool use, not in reading a Google Doc.

## 7. No Streaming in v1

**Context:** The Anthropic API supports streaming responses. Should the generate node stream?

**Decision:** No streaming. Receive the complete response.

**Rationale:** When using `tool_choice` to force tool use, the response is a single structured block. Streaming adds implementation complexity (chunked tool call assembly, partial state handling) with no meaningful UX benefit in a CLI pipeline. The user sees "Generating..." and then the complete output. Streaming would be valuable in a web UI where you want to show progress — noted as a production enhancement.

**Trade-off:** Longer apparent wait during generation. For a 3-4 section brief, this is a few seconds — negligible.

## 8. Error Accumulation Over Fail-Fast

**Context:** When a node encounters an external failure (WordPress unreachable, Claude API error, missing config), should the graph halt or continue?

**Decision:** Every node catches its own exceptions, appends a message to `state["errors"]`, and returns partial state. The graph always runs to completion. Errors are summarized at the end.

**Rationale:** In an agency context, partial output is more useful than no output. If WordPress is down but Claude generates good sections, the reviewer should still see them. If one of three pages fails to publish, the two that succeeded shouldn't be rolled back. Fail-fast is appropriate for libraries; for a user-facing pipeline, graceful degradation and clear error reporting is better.

**Trade-off:** Downstream nodes must handle missing upstream data (empty sections, empty page list). Every node already does this — they check for empty inputs and short-circuit cleanly.
