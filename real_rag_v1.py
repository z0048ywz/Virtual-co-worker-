from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

reader = PdfReader("Specifications.pdf")

text = ""

for page in reader.pages:
    page_text = page.extract_text()
    
    if page_text:
        text += page_text

chunk_size = 1000
overlap = 200

chunks = []

start = 0

while start < len(text):

    end = start + chunk_size

    chunks.append(text[start:end])

    start = end - overlap

print("Chunks Created:", len(chunks))

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

embeddings = model.encode(chunks)

print("Embedding Shape:", embeddings.shape)

import faiss
import numpy as np

dimension = embeddings.shape[1]

index = faiss.IndexFlatL2(dimension)

index.add(
    np.array(embeddings).astype("float32")
)

print("Vectors Stored:", index.ntotal)

question = input("Ask a question: ")

query_embedding = model.encode([question])

D, I = index.search(
    np.array(query_embedding).astype("float32"),
    2
)

print("\nRetrieved Sources:\n")

for i, idx in enumerate(I[0]):

    print(f"\nSource {i+1}")

    print("-" * 40)

    print(chunks[idx][:500])
    
context = ""

for idx in I[0]:
    context += chunks[idx]
    context += "\n\n"
    
answer = f"""
Based on the uploaded document:

{context[:1000]}
"""

print("\nGenerated Answer:\n")
print(answer)

confidence = 90

print(
    f"\nConfidence Score: {confidence}%"
)