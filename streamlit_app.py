"""Single-file version of the chat page for Streamlit Community Cloud.
It calls the functions in rag.py directly, so no separate API server is needed."""
import os
import tempfile

import streamlit as st

from rag import ask, ingest_pdf, list_files

st.set_page_config(page_title="PDF Chatbot", page_icon="📄")
st.title("📄 PDF RAG Chatbot")
st.caption("Upload a PDF, then ask questions. Answers come only from your documents.")
st.info("This is a public demo. Uploaded files are shared with all visitors, so please do not upload private documents.")

# ---------- Sidebar: upload and file picker ----------
with st.sidebar:
    st.header("Upload PDF")
    pdf = st.file_uploader("Choose a PDF", type="pdf")
    if pdf and st.button("Process PDF"):
        with st.spinner("Reading and indexing the PDF..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf.getvalue())
            try:
                count = ingest_pdf(tmp.name, pdf.name)
                if count:
                    st.success(f"Done: {count} chunks stored from {pdf.name}")
                else:
                    st.error("No text found in this PDF (scanned PDF?)")
            except Exception as e:
                st.error(f"Upload failed: {e}")
            finally:
                os.remove(tmp.name)

    try:
        stored = list_files()
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
                data = ask(question, source)
                answer = data["answer"]
                sources = [f"{s['file']} (page {s['page']})" for s in data["sources"]]
            except Exception as e:
                answer, sources = f"Error: {e}", []

        st.markdown(answer)
        if sources:
            st.caption("Sources: " + ", ".join(sources))

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )