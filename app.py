import os
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from pypdf import PdfReader
from docx import Document

# Optional Groq import (used only in Real LLM mode)
try:
    from groq import Groq
except Exception:
    Groq = None

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(page_title="Virtual Coworker - Final Consolidated MVP", layout="wide")
st.title("Virtual Coworker (Final Consolidated MVP)")

APPROVALS_LOG = "approvals.csv"
REVIEW_LOG = "review_workflow_log.csv"
UAT_LOG = "uat_results.csv"

# ---------------------------
# API Client Setup (optional)
# ---------------------------
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
        return False, "Invalid file type. Upload PDF, DOCX, or TXT."

    if uploaded_file.size == 0:
        return False, "Uploaded file is empty."

    return True, "Upload validation complete."


def parse_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)

    pages = len(reader.pages)

    text_parts = [
        (p.extract_text() or "")
        for p in reader.pages
    ]

    text = "\n".join(text_parts).strip()

    words = len(text.split())

    return text, words, pages


def parse_docx(uploaded_file):
    file_bytes = BytesIO(uploaded_file.read())

    doc = Document(file_bytes)

    paragraphs = [
        p.text
        for p in doc.paragraphs
        if p.text.strip()
    ]

    text = "\n".join(paragraphs).strip()

    words = len(text.split())

    est_pages = max(1, round(words / 500)) if words > 0 else 0

    return text, words, est_pages


def parse_txt(uploaded_file):
    raw = uploaded_file.read()

    try:
        text = raw.decode("utf-8").strip()

    except UnicodeDecodeError:
        text = raw.decode("latin-1").strip()

    words = len(text.split())

    est_pages = max(1, round(words / 500)) if words > 0 else 0

    return text, words, est_pages


def parse_document(uploaded_file):
    ext = Path(uploaded_file.name).suffix.lower()

    if ext == ".pdf":
        return parse_pdf(uploaded_file), "exact"

    elif ext == ".docx":
        return parse_docx(uploaded_file), "estimated"

    elif ext == ".txt":
        return parse_txt(uploaded_file), "estimated"

    return ("", 0, 0), "na"


def agent_decision(total_words: int, question: str):
    q = question.lower()

    if total_words > 5000:
        return {
            "selected_model": "Claude (simulated)",
            "reason": "Large document size (>5000 words), better for long-context summarization."
        }

    elif any(
        k in q
        for k in [
            "technical",
            "analysis",
            "root cause",
            "failure",
            "engineering"
        ]
    ):
        return {
            "selected_model": "Groq Llama",
            "reason": "Technical analysis required."
        }

    else:
        return {
            "selected_model": "Groq Llama",
            "reason": "General Q&A and summarization."
        }


def generate_mock_summary(question: str, combined_text: str):
    preview = combined_text[:1200].replace("\n", " ").strip()

    if len(preview) > 400:
        preview = preview[:400] + "..."

    return (
        "The uploaded document(s) describe industrial equipment operation, maintenance, "
        "technical constraints, and risk/compliance considerations.\n\n"
        f"Question considered: {question}\n\n"
        f"Context preview: {preview}"
    )


def generate_llm_summary(question: str, combined_text: str):

    if client is None:
        return None, "LLM client not available (missing GROQ_API_KEY or Groq package)."

    prompt = f"""
You are an accurate document assistant. Use ONLY the provided document text.

Tasks:
1) Answer the user's question.
2) Provide 5-8 concise bullet points.
3) If information is missing, explicitly say: Not found in document.

Question: {question}

Document Text:
{combined_text[:18000]}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a reliable assistant for multi-document QA and summarization."
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


def compute_confidence(question: str, combined_text: str, summary: str):

    terms = [
        t
        for t in re.findall(r"[a-zA-Z0-9]+", question.lower())
        if len(t) > 3
    ]

    terms = sorted(set(terms))

    if not terms:
        return {
            "score": 0.65,
            "label": "Medium",
            "reason": "Generic question"
        }

    hits = sum(
        1
        for t in terms
        if t in combined_text.lower()
    )

    coverage = hits / len(terms)

    penalty = 0.10 if "not found in document" in summary.lower() else 0.0

    score = max(
        0.0,
        min(1.0, 0.55 + 0.45 * coverage - penalty)
    )

    label = (
        "High"
        if score >= 0.80
        else "Medium"
        if score >= 0.60
        else "Low"
    )

    return {
        "score": round(score, 2),
        "label": label,
        "reason": f"Keyword coverage={coverage:.2f}"
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


def log_approval(
    question,
    decision,
    confidence,
    selected_model,
    reason,
    filenames,
    mode_used
):

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "question": question,
        "decision": decision,
        "confidence_percent": confidence,
        "selected_model": selected_model,
        "reason": reason,
        "filenames": filenames,
        "mode_used": mode_used
    }

    append_row_csv(APPROVALS_LOG, row)


def log_review_action(
    question,
    filenames,
    summary_text,
    confidence,
    selected_model,
    reviewer_name,
    action,
    review_comments,
    mode_used
):

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "reviewer": reviewer_name,
        "action": action,
        "review_comments": review_comments,
        "question": question,
        "filenames": filenames,
        "confidence_percent": confidence,
        "selected_model": selected_model,
        "mode_used": mode_used,
        "summary_preview": (
            summary_text[:300] + "..."
        ) if len(summary_text) > 300 else summary_text
    }

    append_row_csv(REVIEW_LOG, row)


# ---------------------------
# UI - Inputs
# ---------------------------
st.subheader("1) Ask your question")

question = st.text_input(
    "Example: Summarize key technical risks and mitigation actions."
)

st.subheader("2) Upload document(s): PDF / DOCX / TXT")

uploaded_files = st.file_uploader(
    "Upload one or more files",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True
)

st.subheader("3) Summary Mode")

use_real_llm = st.toggle(
    "Use Real LLM Mode (OFF = Mock Mode)",
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
        "Real LLM Mode selected, but GROQ_API_KEY/client is unavailable. Fallback to Mock will be used."
    )

if uploaded_files:
    st.success(f"{len(uploaded_files)} file(s) uploaded ✅")

    for f in uploaded_files:
        st.write(f"- {f.name} ({f.size} bytes)")

else:
    st.caption(
        "Demo checkpoint: User uploads one or multiple documents"
    )


# ---------------------------
# Run Analysis
# ---------------------------
if st.button("Run Analysis"):

    if not question:
        st.warning("Please enter a question.")
        st.stop()

    if not uploaded_files:
        st.warning("Please upload at least one document.")
        st.stop()

    parsed_rows = []

    combined_parts = []

    used_files = []

    total_words_all_docs = 0

    with st.spinner("Parsing documents..."):

        for f in uploaded_files:

            valid, msg = validate_upload(f)

            if not valid:
                st.error(f"{f.name}: {msg}")
                st.stop()

            (text, words, pages), page_mode = parse_document(f)

            total_words_all_docs += words

            parsed_rows.append({
                "Document Name": f.name,
                "Type": Path(f.name).suffix.lower().replace(".", "").upper(),
                "Pages": pages,
                "Page Count Type": page_mode,
                "Words": words
            })

            if text.strip():

                combined_parts.append(
                    f"\n\n--- Document: {f.name} ---\n{text}"
                )

                used_files.append(f.name)

            else:
                st.warning(
                    f"{f.name}: text extraction returned empty."
                )

    if not combined_parts:
        st.error("No usable text extracted from uploaded documents.")
        st.stop()

    combined_text = "\n".join(combined_parts)

    st.success("Text extracted successfully ✅")

    st.subheader("Document Statistics")

    st.dataframe(
        pd.DataFrame(parsed_rows),
        use_container_width=True
    )

    st.write(
        f"**Total Words (All Documents):** {total_words_all_docs}"
    )

    decision = agent_decision(
        total_words_all_docs,
        question
    )

    st.subheader("Agent Decision")

    st.write(
        f"**Selected Model:** {decision['selected_model']}"
    )

    st.write(
        f"**Reason:** {decision['reason']}"
    )

    if use_real_llm:

        with st.spinner("Generating Real LLM summary..."):

            summary, err = generate_llm_summary(
                question,
                combined_text
            )

        if err:

            st.warning(f"LLM failed: {err}")

            st.info("Falling back to Mock summary.")

            summary = generate_mock_summary(
                question,
                combined_text
            )

            active_mode_used = "Mock (fallback)"

        else:
            active_mode_used = "Real LLM"

    else:

        with st.spinner("Generating Mock summary..."):

            summary = generate_mock_summary(
                question,
                combined_text
            )

        active_mode_used = "Mock"

    st.subheader("4) Summary displayed")

    st.write(summary)

    st.caption(f"Summary Mode Used: {active_mode_used}")

    conf = compute_confidence(
        question,
        combined_text,
        summary
    )

    confidence_pct = int(conf["score"] * 100)

    st.subheader("5) Confidence shown")

    st.markdown(f"**Confidence:** {confidence_pct}%")

    st.progress(confidence_pct / 100)

    bar_blocks = int(confidence_pct / 10)

    st.code("█" * bar_blocks + "░" * (10 - bar_blocks))

    st.caption(
        f"{conf['label']} confidence | {conf['reason']}"
    )

    st.session_state["latest"] = {
        "question": question,
        "confidence": confidence_pct,
        "selected_model": decision["selected_model"],
        "reason": decision["reason"],
        "filenames": ", ".join(used_files),
        "mode_used": active_mode_used,
        "summary_text": summary
    }


# ---------------------------
# Human Approval & Review Workflow
# ---------------------------
if "latest" in st.session_state:

    st.subheader("6) Human Approval & Review Workflow")

    d = st.session_state["latest"]

    reviewer_name = st.text_input(
        "Reviewer Name",
        value="Reviewer_1"
    )

    review_comments = st.text_area(
        "Review Comments (mandatory for Reject / Need Changes)",
        placeholder="Add your review notes here..."
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        if st.button("Approve ✅"):

            log_approval(
                question=d["question"],
                decision="Approved",
                confidence=d["confidence"],
                selected_model=d["selected_model"],
                reason=d["reason"],
                filenames=d["filenames"],
                mode_used=d["mode_used"]
            )

            log_review_action(
                question=d["question"],
                filenames=d["filenames"],
                summary_text=d["summary_text"],
                confidence=d["confidence"],
                selected_model=d["selected_model"],
                reviewer_name=reviewer_name,
                action="Approved",
                review_comments=review_comments.strip(),
                mode_used=d["mode_used"]
            )

            st.success(
                "Status: Approved ✅ | Logged successfully"
            )

    with c2:

        if st.button("Reject ❌"):

            if not review_comments.strip():

                st.warning(
                    "Please enter review comments for Reject."
                )

            else:

                log_approval(
                    question=d["question"],
                    decision="Rejected",
                    confidence=d["confidence"],
                    selected_model=d["selected_model"],
                    reason=d["reason"],
                    filenames=d["filenames"],
                    mode_used=d["mode_used"]
                )

                log_review_action(
                    question=d["question"],
                    filenames=d["filenames"],
                    summary_text=d["summary_text"],
                    confidence=d["confidence"],
                    selected_model=d["selected_model"],
                    reviewer_name=reviewer_name,
                    action="Rejected",
                    review_comments=review_comments.strip(),
                    mode_used=d["mode_used"]
                )

                st.error(
                    "Status: Rejected ❌ | Logged successfully"
                )

    with c3:

        if st.button("Need Changes 🛠️"):

            if not review_comments.strip():

                st.warning(
                    "Please enter review comments for Need Changes."
                )

            else:

                log_approval(
                    question=d["question"],
                    decision="Need Changes",
                    confidence=d["confidence"],
                    selected_model=d["selected_model"],
                    reason=d["reason"],
                    filenames=d["filenames"],
                    mode_used=d["mode_used"]
                )

                log_review_action(
                    question=d["question"],
                    filenames=d["filenames"],
                    summary_text=d["summary_text"],
                    confidence=d["confidence"],
                    selected_model=d["selected_model"],
                    reviewer_name=reviewer_name,
                    action="Need Changes",
                    review_comments=review_comments.strip(),
                    mode_used=d["mode_used"]
                )

                st.info(
                    "Status: Need Changes 🛠️ | Logged successfully"
                )


# ---------------------------
# UAT Checklist
# ---------------------------
st.markdown("---")

st.subheader("7) User Acceptance Testing (UAT) Checklist")

uat_items = [
    "Upload works for PDF/DOCX/TXT",
    "Text extraction works",
    "Document stats shown",
    "Agent decision shown",
    "Summary shown",
    "Confidence shown with progress bar",
    "Approve action works",
    "Reject action works",
    "Need Changes action works",
]

uat_results = {}

for item in uat_items:
    uat_results[item] = st.checkbox(item, value=False)

if st.button("Save UAT Result"):

    row = {
        "timestamp": datetime.utcnow().isoformat()
    }

    row.update({
        k: "Pass" if v else "Fail"
        for k, v in uat_results.items()
    })

    append_row_csv(UAT_LOG, row)

    st.success("UAT result saved to uat_results.csv")

st.markdown("---")

st.caption(
    "Flow: Question → Multi-file Upload → Parsing → Agent Decision → "
    "Summary → Confidence → Human Approval → UAT"
)
