# Architecture

## Graph Design

The pipeline is a LangGraph `StateGraph` with six nodes and one conditional loop. State is a single `PipelineState` TypedDict passed through every node.

```
[START] → intake → analyze_site → generate → review ─┐
                                     ▲                │
                                     │ rejected        │ approved
                                     │ (attempts < 3)  │
                                     └────────────────┘
                                                       │
                                                       ▼
                                               publish → notify → [END]
```

If the reviewer rejects three times, the graph exits without publishing and prints a summary of what was generated.

## State Schema

```python
class Section(TypedDict):
    title: str  # Page or section heading
    body: str  # HTML-formatted copy
    meta_description: str  # SEO meta, max 160 chars
    target_page: str | None  # Existing WP slug to update, or None = new


class PipelineState(TypedDict, total=False):
    brief_source: str  # File path or raw text (Google Docs planned)
    brief_content: str  # Parsed brief text
    client_name: str  # Extracted from brief heading

    wp_site_url: str  # Target WordPress site
    wp_existing_pages: list[dict]  # [{id, slug, title, status}]

    sections: list[Section]  # Generated content
    generation_feedback: str | None  # Reviewer's change request
    generation_attempts: int  # Counter, max 3

    approval_status: str  # "approved" | "rejected"

    draft_urls: list[str]  # Created WP draft page URLs

    notification_sent: bool  # True after notify completes

    errors: list[str]  # Accumulated error messages
```

## Node Contracts

### intake
- **Reads:** `brief_source`
- **Writes:** `brief_content`, `client_name`
- **External calls:** Local filesystem (Google Docs planned, not yet implemented)
- **Failure mode:** Unreadable source → error appended, empty `brief_content`

### analyze_site
- **Reads:** `wp_site_url` (from config)
- **Writes:** `wp_existing_pages`
- **External calls:** WordPress REST API `GET /wp-json/wp/v2/pages`
- **Failure mode:** Site unreachable → empty list, error appended, pipeline continues

### generate
- **Reads:** `brief_content`, `wp_existing_pages`, `generation_feedback`, `generation_attempts`
- **Writes:** `sections`, `generation_attempts`
- **External calls:** Anthropic Messages API with tool use
- **Failure mode:** API error → error appended, empty sections

### review
- **Reads:** `sections`, `client_name`
- **Writes:** `approval_status`, `generation_feedback`
- **External calls:** None (CLI input)
- **Failure mode:** N/A — blocks until human input

### publish
- **Reads:** `sections`, `wp_site_url`, `wp_existing_pages`
- **Writes:** `draft_urls`
- **External calls:** WordPress REST API `POST /wp-json/wp/v2/pages`
- **Failure mode:** Partial failure → creates what it can, errors for the rest
- **Safety invariant:** Every POST sets `status="draft"`, hard-coded

### notify
- **Reads:** `draft_urls`, `client_name`
- **Writes:** `notification_sent`
- **External calls:** Slack webhook (optional), SendGrid (optional)
- **Failure mode:** Notification failure → error appended, `notification_sent` still True (pipeline completed)

## Conditional Edges

| From | Condition | To |
|---|---|---|
| review | `approval_status == "approved"` | publish |
| review | `approval_status == "rejected"` AND `generation_attempts < 3` | generate |
| review | `approval_status == "rejected"` AND `generation_attempts >= 3` | END |
| publish | always | notify |
| notify | always | END |

## Safety Model

1. **Human-in-the-loop:** Nothing writes to WordPress until a human approves. The review node blocks execution.

2. **Draft-only publishing:** The `create_draft_page` and `update_draft_page` functions hard-code `status="draft"`. This is not configurable. The test suite explicitly asserts this on every outgoing request body.

3. **Generation cap:** Maximum 3 generation attempts prevents infinite rejection loops.

4. **Error accumulation:** Nodes append to `state["errors"]` rather than raising exceptions. The graph always completes; errors are reported at the end.

5. **Principle of least authority:** The WordPress Application Password only needs `edit_pages` capability. No admin access required.

## Scaling Notes (Production)

These are out of scope for v1 but documented to show production thinking:

- **Async execution:** Replace CLI review with a webhook callback (Slack interactive message, email approval link)
- **Batch processing:** Accept multiple briefs, run graphs in parallel
- **Rate limiting:** Queue Claude API calls to stay within tier limits
- **Persistence:** Store state in a database between nodes for long-running workflows
- **Observability:** LangSmith tracing for debugging production runs
- **Content versioning:** Track draft revisions, diff against previous versions
