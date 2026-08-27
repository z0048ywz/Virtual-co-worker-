import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ---------------------------
# 1) Extract text from uploaded files
# ---------------------------
from pypdf import PdfReader
from docx import Document
from io import BytesIO

def extract_text(uploaded_files):
    all_text = ""

    for file in uploaded_files:
        name = file.name.lower()

        if name.endswith(".pdf"):
            reader = PdfReader(file)
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    all_text += txt + "\n"

        elif name.endswith(".txt"):
            all_text += file.read().decode("utf-8", errors="ignore") + "\n"

        elif name.endswith(".docx"):
            doc_bytes = BytesIO(file.read())
            doc = Document(doc_bytes)
            for para in doc.paragraphs:
                all_text += para.text + "\n"

    return all_text.strip()

# ---------------------------
# 2) Chunking
# ---------------------------
def create_chunks(text, chunk_size=500, overlap=100):
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - overlap)

    return chunks

# ---------------------------
# 3) Embeddings
# ---------------------------
def generate_embeddings(chunks):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(chunks, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")
    return model, embeddings

# ---------------------------
# 4) FAISS Index
# ---------------------------
def create_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index

# ---------------------------
# 5) Retrieval
# ---------------------------
def retrieve_chunks(question, model, index, chunks, top_k=3):
    q_emb = model.encode([question], convert_to_numpy=True).astype("float32")
    distances, indices = index.search(q_emb, top_k)

    retrieved = []
    for i in indices[0]:
        if 0 <= i < len(chunks):
            retrieved.append(chunks[i])

    return retrieved

# ---------------------------
# 6) Answer Generation (mock)
# ---------------------------
def generate_answer(retrieved_chunks):
    if not retrieved_chunks:
        return "No relevant information found in the uploaded documents."

    answer = "Based on retrieved document sections:\n\n"
    for i, ch in enumerate(retrieved_chunks, 1):
        answer += f"{i}. {ch[:250]}...\n\n"

    answer += "This is a retrieval-based draft answer (Week 2 RAG stage)."
    return answer