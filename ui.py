import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="PDF Chatbot", page_icon="📄")
st.title("📄 PDF RAG Chatbot")
st.caption("Upload a PDF, then ask questions. Answers come only from your documents.")


def error_text(response, default):
    try:
        return response.json().get("detail", default)
    except ValueError:
        return default


# ---------- Sidebar: upload ----------
with st.sidebar:
    st.header("Upload PDF")
    pdf = st.file_uploader("Choose a PDF", type="pdf")
    if pdf and st.button("Process PDF"):
        with st.spinner("Reading and indexing the PDF..."):
            try:
                r = requests.post(
                    f"{API_URL}/upload",
                    files={"file": (pdf.name, pdf.getvalue(), "application/pdf")},
                    timeout=300,
                )
                if r.ok:
                    st.success(f"Done: {r.json()['chunks_stored']} chunks stored from {pdf.name}")
                else:
                    st.error(error_text(r, "Upload failed"))
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the API. Is uvicorn running?")

    try:
        stored = requests.get(f"{API_URL}/files", timeout=10).json()["files"]
    except Exception:
        stored = []
    choice = st.selectbox("Search in", ["All files"] + stored)
    source = None if choice == "All files" else choice

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ---------- Chat history ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption("Sources: " + ", ".join(msg["sources"]))

# ---------- New question ----------
question = st.chat_input("Ask a question about your PDFs")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                r = requests.post(f"{API_URL}/ask", json={"question": question, "source": source}, timeout=120)
                if r.ok:
                    data = r.json()
                    answer = data["answer"]
                    sources = [f"{s['file']} (page {s['page']})" for s in data["sources"]]
                else:
                    answer, sources = f"Error: {error_text(r, 'Server error, check the terminal')}", []
            except requests.exceptions.ConnectionError:
                answer, sources = "Cannot reach the API. Is uvicorn running?", []

        st.markdown(answer)
        if sources:
            st.caption("Sources: " + ", ".join(sources))

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )