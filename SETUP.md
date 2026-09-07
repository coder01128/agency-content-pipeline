# Setup Guide

## Prerequisites

- Python 3.11 or higher
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- A WordPress site you control (for the demo, LocalWP works perfectly)
- Git

## 1. Clone and Install

```bash
git clone https://github.com/coder01128/agency-content-pipeline.git
cd agency-content-pipeline
pip install -e ".[dev]"
```

## 2. Create Your .env File

```bash
cp .env.example .env          # Linux/macOS
copy .env.example .env        # Windows
```

Open `.env` and fill in the values below.

## 3. Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Navigate to API Keys
3. Create a new key
4. Paste it into `.env` as `ANTHROPIC_API_KEY`

## 4. WordPress Setup

You need a WordPress site with REST API access and an Application Password.

### Option A: LocalWP (recommended for demo)

1. Download [LocalWP](https://localwp.com/) — free, runs WordPress on your machine
2. Create a new site (any name, use the default settings)
3. Start the site
4. Your site URL will be something like `http://your-site.local`

### Option B: Existing WordPress Site

Any WordPress site with REST API enabled (it's on by default in WP 4.7+).

### Create an Application Password

1. Log into your WordPress admin panel
2. Go to **Users → Your Profile** (or Users → All Users → click your username)
3. Scroll down to **Application Passwords**
4. Enter a name: `content-pipeline`
5. Click **Add New Application Password**
6. Copy the generated password — it looks like `xxxx xxxx xxxx xxxx xxxx xxxx`
7. Add to your `.env`:

```
WP_SITE_URL=http://your-site.local
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

### Verify WordPress API Access

```bash
curl -s "http://your-site.local/wp-json/wp/v2/pages" | python -m json.tool | head -20
```

You should see a JSON array. If you get a 404, your site may not have the REST API enabled.

## 5. Google Docs (Planned — Not Yet Implemented)

The pipeline works with local `.md` files. Google Docs integration is planned but not yet built. The intake node has a placeholder for it.

If you want to prepare for future support:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project (or use an existing one)
3. Enable the Google Docs API
4. Create a Service Account (IAM → Service Accounts → Create)
5. Download the JSON key file
6. Save it somewhere safe and add the path to `.env`:

```
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

7. Share any Google Doc you want the pipeline to read with the service account's email address (it looks like `name@project.iam.gserviceaccount.com`)

## 6. Notifications (Optional)

### Slack

1. Create a Slack app or use an existing incoming webhook
2. Add the webhook URL to `.env`:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
```

### Email (SendGrid)

```
SENDGRID_API_KEY=SG.xxx
NOTIFICATION_EMAIL=you@example.com
```

## 7. Verify Configuration

```bash
python -m src.config
```

This prints a checklist showing which services are configured and which are missing. Required services will show an error; optional services will show a warning.

Expected output when everything is set up:

```
  [ok] ANTHROPIC_API_KEY              configured
  [ok] WP_SITE_URL                    http://your-site.local
  [ok] WP_USERNAME                    configured
  [ok] WP_APP_PASSWORD                configured

  [--] GOOGLE_SERVICE_ACCOUNT_JSON    not configured (optional)
  [--] SLACK_WEBHOOK_URL              not configured (optional)
  [--] SENDGRID_API_KEY               not configured (optional)
  [--] NOTIFICATION_EMAIL             not configured (optional)

  All required variables set. Ready to run.
```

## 8. Run the Demo

```bash
python -m src.graph \
  --brief examples/sample_brief.md \
  --wp-url http://your-site.local
```

Or use the one-liner:

```bash
bash examples/run_demo.sh
```

## Troubleshooting

**"Connection refused" from WordPress**
→ If using LocalWP, make sure the site is started (green dot in LocalWP)

**401 Unauthorized from WordPress**
→ Check that the Application Password hasn't expired and that the username matches exactly

**"status=draft not in request body" test failure**
→ This is a safety test. If you've changed the publish logic, check that status is still hard-coded to "draft"

**Claude API rate limit**
→ The pipeline uses a single API call per generation. If you're on a low tier, wait a moment and retry. For development iteration, switch to `claude-haiku` in `src/tools/claude_tools.py`
