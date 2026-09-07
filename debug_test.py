import anthropic
from src.config import load_config

c = load_config()
key = c.anthropic_api_key
print("Key length:", len(key))
print("Key starts:", key[:20])
print("Key ends:", key[-5:])
print("Any quotes in key:", '"' in key or "'" in key)
print("Any spaces in key:", " " in key)

client = anthropic.Anthropic(api_key=key)
try:
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say hello"}]
    )
    text = next((b.text for b in response.content if b.type == "text"), None)
    print("SUCCESS:", text)
except Exception as e:
    print("RAW ERROR TYPE:", type(e).__name__)
    print("RAW ERROR:", e)