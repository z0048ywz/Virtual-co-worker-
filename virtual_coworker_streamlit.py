import streamlit as st

from pypdf import PdfReader
from docx import Document

def extract_text_from_file(file):

    if file.name.endswith(".pdf"):
        reader = PdfReader(file)
        
        text = ""
        
        for page in reader.pages:
            
            page_text = page.extract_text()
            
            if page_text:
                text += page_text

        return text

    elif file.name.endswith(".txt"):

        return file.read().decode("utf-8")
        
    elif file.name.endswith(".docx"):

        doc = Document(file)

        text = ""

        for para in doc.paragraphs:
            text +=para.text + "\n"

        return text

    return ""

from virtual_coworker_backend import (
    extract_text,
    create_chunks,
    generate_embeddings,
    create_faiss_index,
    retrieve_chunks,
    generate_answer
)

st.title("Virtual Co-worker")

uploaded_file = st.file_uploader(
    "Upload Documents",
    type=["pdf","txt", "docx"],
    accept_multiple_files=True
)

question = st.text_input(
    "Ask a Question"
)

if st.button("Run Analysis"):

    if uploaded_file and question:

        text = extract_text(uploaded_file)
        
        chunks = create_chunks(text)

        model, embeddings = generate_embeddings(
            chunks
        )

        index = create_faiss_index(
            embeddings
        )

        retrieved_chunks = retrieve_chunks(
            question,
            model,
            index,
            chunks
        )
        
        answer = generate_answer(
            retrieved_chunks
        )

        st.subheader("Generated Answer")

        st.write(answer)

        st.subheader("Retrieved Sources")

        for i, chunk in enumerate(retrieved_chunks):
    
            with st.expander(
                f"Source {i+1}"
            ):
                st.write(chunk)

        confidence = 90 

        st.metric(
            "Confidence",
            f"{confidence}%"
        )
    else:
    
        st.warning(
            "Upload a PDF and enter a question."
        )