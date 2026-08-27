import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

documents = [
	"Compressor technical specification",
	"Maintenance procedure",
	"Project risk assessment"
]

model = SentenceTransformer("all-MiniLM-L6-v2")

embeddings = model.encode(documents)

index = faiss.IndexFlatL2(
    embeddings.shape[1]
)

index.add(
	np.array(embeddings).astype("float32")
)

question = "maintenance requirements"

query_embedding = model.encode([question])

D, I = index.search(
    np.array(query_embedding).astype("float32"),
    k=2
)

print("Top Matches:\n")

for idx in I[0]:
    print(...)