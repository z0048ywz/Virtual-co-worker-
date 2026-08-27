import os
from dotenv import load_dotenv
from groq import Groq

# Explicitly load .env from current folder
load_dotenv(dotenv_path=".env")

print("ENV VALUE:", os.getenv("GROQ_API_KEY"))

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Hello from IIT Delhi demo"
        }
    ]
)

print(response.choices[0].message.content)
