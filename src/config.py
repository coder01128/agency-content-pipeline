from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    wp_site_url: str
    wp_username: str
    wp_app_password: str
    google_service_account_json: str | None = None
    slack_webhook_url: str | None = None
    sendgrid_api_key: str | None = None
    notification_email: str | None = None


_REQUIRED = [
    "ANTHROPIC_API_KEY",
    "WP_SITE_URL",
    "WP_USERNAME",
    "WP_APP_PASSWORD",
]

_OPTIONAL = [
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "SLACK_WEBHOOK_URL",
    "SENDGRID_API_KEY",
    "NOTIFICATION_EMAIL",
]


def load_config() -> Settings:
    load_dotenv()

    missing: list[str] = []
    for var in _REQUIRED:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in the values."
        )

    return Settings(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        wp_site_url=os.environ["WP_SITE_URL"],
        wp_username=os.environ["WP_USERNAME"],
        wp_app_password=os.environ["WP_APP_PASSWORD"],
        google_service_account_json=os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"),
        slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
        sendgrid_api_key=os.environ.get("SENDGRID_API_KEY"),
        notification_email=os.environ.get("NOTIFICATION_EMAIL"),
    )


def print_config_checklist() -> None:
    load_dotenv()

    print("\n=== Agency Content Pipeline -- Config Checklist ===\n")

    all_ok = True
    for var in _REQUIRED:
        val = os.environ.get(var)
        if val:
            display = val if var == "WP_SITE_URL" else "configured"
            print(f"  [ok] {var:<30} {display}")
        else:
            print(f"  [!!] {var:<30} MISSING (required)")
            all_ok = False

    print()
    for var in _OPTIONAL:
        val = os.environ.get(var)
        if val:
            print(f"  [ok] {var:<30} configured")
        else:
            print(f"  [--] {var:<30} not configured (optional)")

    print()
    if all_ok:
        print("  All required variables set. Ready to run.\n")
    else:
        print("  Fix the missing required variables above before running.\n")
        sys.exit(1)


if __name__ == "__main__":
    print_config_checklist()
