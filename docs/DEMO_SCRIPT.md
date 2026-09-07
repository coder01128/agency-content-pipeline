# Demo Recording Script

Target length: 3–4 minutes. One take. Terminal + browser.

## Setup Before Recording

- LocalWP running with test site, 2-3 existing pages (Home, About, Contact)
- Terminal open in repo root
- Browser open to WP admin → Pages (to show drafts after publish)
- `.env` configured and validated

## Script

```
0:00  "This is Agency Content Pipeline — a LangGraph agent that takes a
       client brief and turns it into WordPress draft pages, with human
       approval before anything gets written."

       [Show: terminal, repo visible in background]

0:15  "Here's a sample brief for a landscaping company."

       [Run: cat examples/sample_brief.md]
       [Let it scroll — pause 2 seconds so viewer can read the structure]

0:30  "I run the pipeline pointing at my test WordPress site."

       [Run: python -m src.graph --brief examples/sample_brief.md --wp-url http://test-site.local]

0:40  "It reads the brief, checks what pages already exist on the
       WordPress site, then calls Claude to generate sections. Claude
       uses tool use — structured output, not free text — so the
       sections come back as typed data with titles, slugs, body copy,
       and meta descriptions."

       [Terminal shows: intake, analyze_site, generate nodes executing]

1:10  "Now it stops and asks me to review. Nothing has touched WordPress yet."

       [Terminal shows: review prompt with sections listed]
       [Pause — let the viewer read 2-3 sections]

1:30  "The meta descriptions are too long. I'll reject and ask for shorter ones."

       [Type: r]
       [Type feedback: "Meta descriptions must be under 120 characters. Tighten the body copy too — less corporate, more local family business."]

1:50  "It goes back to Claude with my feedback and regenerates."

       [Terminal shows: generate node running again, new sections appear]
       [Review prompt appears again]

2:10  "These are better. Approving."

       [Type: a]

2:15  "Now it creates draft pages in WordPress."

       [Terminal shows: publish node creating drafts, URLs printed]

2:25  "Let me show those in WordPress admin."

       [Switch to browser → WP admin → Pages]
       [Click into one draft page, show the generated content]

2:45  "Four draft pages, all with the generated content, all in draft
       status. The agent can never publish live — that's a hard-coded
       safety constraint, not a setting."

       [Show: status column in WP pages list — all say "Draft"]

3:00  "Under the hood: LangGraph state machine with typed state,
       Anthropic API with tool use for structured output, WordPress
       REST API for publishing, and a human approval gate before any
       write operation."

       [Briefly show: ARCHITECTURE.md in editor or terminal — the graph diagram]

3:15  "Repo link in the description."

       [End]
```

## Post-Recording

- Upload to Loom
- Copy the share link
- Add to README.md under the Demo section
- Test the link works when not logged in
