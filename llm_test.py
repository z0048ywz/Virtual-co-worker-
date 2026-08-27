import os
from openai import OpenAI

key = os.getenv("OPENAI_API_KEY")
print("KEY_SET:", bool(key))

client = OpenAI(api_key=key)
resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role":"user","content":"Say hello in one line."}],
    temperature=0
)
print(resp.choices[0].message.content)