# Agency Content Pipeline

LangGraph agent that turns a client brief into WordPress draft pages — with human approval before anything publishes.

Built to demonstrate agentic workflow design, Anthropic API tool use, multi-service orchestration, and human-in-the-loop safety patterns in a real agency production context.

## Demo

<!-- TODO: Add Loom link after recording -->
[Watch the 3-minute walkthrough →](#)

## How It Works

```
Brief (file / raw text)
        │
        ▼
   ┌─────────┐
   │  Intake  │  Read and parse the client brief
   └────┬─────┘
        ▼
  ┌────────────┐
  │ Analyze WP │  Fetch existing WordPress page structure
  └────┬───────┘
        ▼
   ┌──────────┐
   │ Generate  │  Claude API with tool use → structured sections
   └────┬─────┘
        ▼
   ┌──────────┐        ┌──────────┐
   │  Review   │──no───▶│ Generate  │  (with feedback, max 3 tries)
   └────┬─────┘        └──────────┘
        │ yes
        ▼
   ┌──────────┐
   │ Publish   │  Create WordPress DRAFT pages (never live)
   └────┬─────┘
        ▼
   ┌──────────┐
   │  Notify   │  Confirmation via terminal / Slack / email
   └──────────┘
```

**Key safety constraint:** The agent can only create draft pages. It cannot publish live content. This is a hard-coded invariant, not a configuration option.

## Quick Start

```bash
git clone https://github.com/coder01128/agency-content-pipeline.git
cd agency-content-pipeline
cp .env.example .env          # add your API keys
pip install -e ".[dev]"       # install dependencies
python -m src.config           # verify configuration
python -m src.graph \
  --brief examples/sample_brief.md \
  --wp-url https://your-wp-site.com
```

## Tech Stack

| Component | Technology |
|---|---|
| Orchestration | LangGraph (state machine with typed state) |
| LLM | Anthropic Claude API with tool use |
| Content target | WordPress REST API |
| Brief source | Local markdown or raw text (Google Docs planned) |
| Language | Python 3.11+ |
| HTTP client | httpx |
| Testing | pytest + respx |

## Configuration

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `WP_SITE_URL` | Yes | WordPress site URL (with https://) |
| `WP_USERNAME` | Yes | WordPress username |
| `WP_APP_PASSWORD` | Yes | WordPress Application Password |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | No | Path to Google service account JSON |
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook for notifications |
| `SENDGRID_API_KEY` | No | SendGrid key for email notifications |
| `NOTIFICATION_EMAIL` | No | Email address for notifications |

See [SETUP.md](SETUP.md) for detailed configuration instructions.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full graph design, state schema, node contracts, and safety model.

## Design Decisions

See [docs/DECISIONS.md](docs/DECISIONS.md) for documented design choices and their rationale.

## License

MIT
