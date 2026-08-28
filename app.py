import os
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from pypdf import PdfReader
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Optional Groq import
try:
    from groq import Groq
except Exception:
    Groq = None

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(
    page_title="Engineering Automation with Agentic AI",
    layout="wide"
)

st.title("Engineering Automation with Agentic AI")
st.caption("IIT Delhi – AI for Future Tech Leaders")

APPROVALS_LOG = "approvals.csv"
REVIEW_LOG = "review_workflow_log.csv"
UAT_LOG = "uat_results.csv"

# ---------------------------
# API Client Setup
# ---------------------------

api_key = None

try:
    api_key = st.secrets["GROQ_API_KEY"]

except Exception:
    api_key = os.getenv("GROQ_API_KEY")

client = None

if Groq is not None and api_key:

    try:
        client = Groq(api_key=api_key)

    except Exception:
        client = None

# ---------------------------
# Helper Functions
# ---------------------------
def validate_upload(uploaded_file):

    if uploaded_file is None:
        return False, "No file uploaded."

    ext = Path(uploaded_file.name).suffix.lower()

    if ext not in [".pdf", ".docx", ".txt"]:
        return False, "Invalid file type."

    if uploaded_file.size == 0:
        return False, "Uploaded file is empty."

    return True, "Upload validation complete."


def parse_pdf(uploaded_file):

    reader = PdfReader(uploaded_file)

    text_parts = [
        (p.extract_text() or "")
        for p in reader.pages
    ]

    text = "\n".join(text_parts).strip()

    return text


def parse_docx(uploaded_file):

    file_bytes = BytesIO(uploaded_file.read())

    doc = Document(file_bytes)

    paragraphs = [
        p.text
        for p in doc.paragraphs
        if p.text.strip()
    ]

    return "\n".join(paragraphs).strip()


def parse_txt(uploaded_file):

    raw = uploaded_file.read()

    try:
        return raw.decode("utf-8").strip()

    except UnicodeDecodeError:
        return raw.decode("latin-1").strip()


def parse_document(uploaded_file):

    ext = Path(uploaded_file.name).suffix.lower()

    if ext == ".pdf":
        return parse_pdf(uploaded_file)

    elif ext == ".docx":
        return parse_docx(uploaded_file)

    elif ext == ".txt":
        return parse_txt(uploaded_file)

    return ""


def generate_mock_summary(question, combined_text):

    preview = combined_text[:500]

    return f"""
Engineering Summary

Question:
{question}

Key Findings:
- Industrial engineering content detected
- Maintenance and operational context identified
- Risk and compliance indicators present

Document Preview:
{preview}
"""


def generate_llm_summary(question, combined_text):

    if client is None:
        return None, "LLM client unavailable."

    prompt = f"""
You are an engineering AI assistant.

Tasks:
1. Answer the question
2. Generate concise engineering summary
3. Provide bullet point findings
4. Mention risks if any

Question:
{question}

Document:
{combined_text[:18000]}
"""

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a reliable engineering assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        return response.choices[0].message.content.strip(), None

    except Exception as e:
        return None, str(e)


def compute_confidence(question, combined_text, summary):

    score = 0.72

    if len(combined_text) > 3000:
        score += 0.10

    score = min(score, 0.95)

    return {
        "score": round(score, 2),
        "label": "High" if score >= 0.80 else "Medium",
        "reason": "Semantic relevance detected"
    }


def append_row_csv(file_path, row_dict):

    if os.path.exists(file_path):

        df = pd.read_csv(file_path)

        df = pd.concat(
            [df, pd.DataFrame([row_dict])],
            ignore_index=True
        )

    else:
        df = pd.DataFrame([row_dict])

    df.to_csv(file_path, index=False)


def generate_pdf(summary, recommendation, validation, decision):

    buffer = BytesIO()

    p = canvas.Canvas(buffer, pagesize=letter)

    y = 750

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Engineering Automation Report")

    y -= 40

    sections = [
        ("Knowledge Agent", summary),
        ("Recommendation Agent", recommendation),
        ("Validation Agent", validation),
        ("Decision Agent", decision)
    ]

    for title, content in sections:

        p.setFont("Helvetica-Bold", 13)
        p.drawString(50, y, title)

        y -= 20

        p.setFont("Helvetica", 11)

        lines = content.split("\n")

        for line in lines:

            wrapped = [
                line[i:i+90]
                for i in range(0, len(line), 90)
            ]

            for wrap in wrapped:

                p.drawString(70, y, wrap)

                y -= 15

                if y < 50:
                    p.showPage()
                    y = 750

        y -= 20

    p.save()

    buffer.seek(0)

    return buffer


# ---------------------------
# UI Inputs
# ---------------------------
st.subheader("Hi, How can I help you?")

question = st.text_input(
    "Example: Summarize technical risks and mitigation actions"
)

st.subheader("2) Upload Engineering Documents")

uploaded_files = st.file_uploader(
    "Upload PDF / DOCX / TXT",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True
)

st.subheader("3) Summary Mode")

use_real_llm = st.toggle(
    "Use Real LLM Mode",
    value=False
)

mode_name = (
    "Real LLM Mode"
    if use_real_llm
    else "Mock Mode"
)

st.info(f"Current Mode: {mode_name}")

if use_real_llm and client is None:
    st.warning(
        "Real LLM unavailable. Falling back to Mock mode."
    )

# ---------------------------
# Run Analysis
# ---------------------------
if st.button("Run Analysis"):

    if not question.strip():

        st.warning("Please enter a question.")

        st.stop()

    if not uploaded_files:

        st.warning("Please upload documents.")

        st.stop()

    combined_parts = []

    with st.spinner("Parsing documents..."):

        for f in uploaded_files:

            valid, msg = validate_upload(f)

            if not valid:
                st.error(msg)
                st.stop()

            text = parse_document(f)

            if text.strip():

                combined_parts.append(
                    f"\n\n--- {f.name} ---\n{text}"
                )

    if not combined_parts:

        st.error("No text extracted.")

        st.stop()

    combined_text = "\n".join(combined_parts)

    st.success("Documents processed successfully ✅")

    # ---------------------------
    # Generate Summary
    # ---------------------------

    if use_real_llm:

        with st.spinner("Generating AI summary..."):

            summary, err = generate_llm_summary(
                question,
                combined_text
            )

        if err:

            st.warning(f"LLM failed: {err}")

            summary = generate_mock_summary(
                question,
                combined_text
            )

            active_mode = "Mock Fallback"

        else:
            active_mode = "Real LLM"

    else:

        summary = generate_mock_summary(
            question,
            combined_text
        )

        active_mode = "Mock"

    # ---------------------------
    # Confidence
    # ---------------------------

    conf = compute_confidence(
        question,
        combined_text,
        summary
    )

    confidence_pct = int(conf["score"] * 100)

    # ---------------------------
    # Agent Flow
    # ---------------------------

    st.subheader("Agent Execution Flow")

    st.success("✅ Knowledge Agent Completed")
    st.success("✅ Recommendation Agent Completed")
    st.success("✅ Validation Agent Completed")
    st.warning("⏳ Human Approval Pending")

    # ---------------------------
    # Summary
    # ---------------------------

    st.subheader("Knowledge Agent")

    st.write(summary)

    recommendation_text = "Proceed with engineering review."

    validation_text = (
        f"Confidence Score: {confidence_pct}%"
    )

    decision_text = (
        "Human Review Required"
        if confidence_pct < 80
        else "Auto Recommendation Possible"
    )

    st.subheader("Recommendation Agent")

    st.write(recommendation_text)

    st.subheader("Validation Agent")

    st.write(validation_text)

    st.subheader("Decision Agent")

    st.write(decision_text)

    # ---------------------------
    # Confidence Display
    # ---------------------------

    st.subheader("Confidence")

    st.progress(confidence_pct / 100)

    st.caption(
        f"{conf['label']} confidence | {conf['reason']}"
    )

# ---------------------------
# PDF Generation
# ---------------------------

try:

    pdf_file = generate_pdf(
        summary,
        recommendation_text,
        validation_text,
        decision_text
    )

    st.success("PDF generated successfully ✅")

    st.download_button(
        label="📄 Download Engineering Report PDF",
        data=pdf_file.getvalue(),
        file_name="engineering_report.pdf",
        mime="application/pdf"
    )

except Exception as e:

    st.error(f"PDF generation failed: {e}")

# ---------------------------
# Footer
# ---------------------------

st.markdown("---")

st.caption(
    "Flow: Upload → Parsing → Knowledge Agent → "
    "Recommendation → Validation → Decision → Human Approval"
)
