import os, requests
k = os.getenv("OPENAI_API_KEY")
h = {"Authorization": f"Bearer {k}"}
r = requests.get("https://api.openai.com/v1/models", headers=h, timeout=30)
print(r.status_code)
print(r.text[:300])