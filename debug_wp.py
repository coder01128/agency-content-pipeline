import httpx
from src.config import load_config

c = load_config()
print("URL:", c.wp_site_url)
print("Username:", c.wp_username)
print("Password:", c.wp_app_password[:8] + "...")

auth = httpx.BasicAuth(c.wp_username, c.wp_app_password)

r = httpx.get(
    f"{c.wp_site_url}/wp-json/wp/v2/users/me",
    auth=auth,
    timeout=30
)
print("Status:", r.status_code)
print("Response:", r.text[:500])