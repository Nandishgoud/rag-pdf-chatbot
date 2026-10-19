import os
import time

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pypdf import PdfReader

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
EMBED_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-3.6-flash"

db = chromadb.PersistentClient(path="chroma_db")
collection = db.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})


def read_pdf(path):
    """Return a list of (page_number, text)."""
    reader = PdfReader(path)
    return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]


def chunk_text(text, size=800, overlap=150):
    """Split text into overlapping chunks."""
    chunks, start = [], 0
    while start < len(text):
        piece = text[start:start + size].strip()
        if piece:
            chunks.append(piece)
        start += size - overlap
    return chunks


def embed(texts, task_type):
    """Turn a list of texts into a list of vectors (in batches).
    If Gemini's free-tier limit (429) is hit, wait and try again."""
    vectors = []
    for i in range(0, len(texts), 50):
        batch = texts[i:i + 50]
        for attempt in range(5):
            try:
                result = client.models.embed_content(
                    model=EMBED_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type=task_type),
                )
                break
            except errors.ClientError as e:
                if e.code == 429 and attempt < 4:
                    time.sleep(30)
                else:
                    raise
        vectors.extend(e.values for e in result.embeddings)
    return vectors


def ingest_pdf(path, filename):
    """Read a PDF, chunk it, embed it, store it. Returns number of chunks."""
    ids, docs, metas = [], [], []
    for page_no, text in read_pdf(path):
        for j, chunk in enumerate(chunk_text(text)):
            ids.append(f"{filename}-p{page_no}-c{j}")
            docs.append(chunk)
            metas.append({"source": filename, "page": page_no})
    if not docs:
        return 0
    vectors = embed(docs, "RETRIEVAL_DOCUMENT")
    collection.upsert(ids=ids, documents=docs, embeddings=vectors, metadatas=metas)
    return len(docs)


SYSTEM_PROMPT = (
    "You answer questions using ONLY the context provided. "
    "If the answer is not in the context, say you could not find it in the documents. "
    "Keep answers short and clear."
)


def generate(prompt):
    """Ask Gemini for the answer. If it is busy or over the limit (429/500/503), wait and retry."""
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=CHAT_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            return response.text
        except errors.APIError as e:
            if e.code in (429, 500, 503) and attempt < 3:
                time.sleep(10 * (attempt + 1))
            else:
                raise


def list_files():
    """Names of all PDFs stored so far."""
    data = collection.get(include=["metadatas"])
    return sorted({m["source"] for m in data["metadatas"]})


def ask(question, source=None, k=4):
    """Retrieve the top-k chunks (optionally from one file only) and answer from them."""
    if collection.count() == 0:
        return {"answer": "No documents uploaded yet.", "sources": []}

    q_vec = embed([question], "RETRIEVAL_QUERY")[0]
    query = {"query_embeddings": [q_vec], "n_results": k}
    if source:
        query["where"] = {"source": source}
    res = collection.query(**query)
    docs, metas = res["documents"][0], res["metadatas"][0]
    if not docs:
        return {"answer": "No matching content found in that file.", "sources": []}

    context = "\n\n".join(
        f"[{m['source']} - page {m['page']}]\n{d}" for d, m in zip(docs, metas)
    )
    prompt = f"Context:\n{context}\n\nQuestion: {question}"

    answer = generate(prompt)
    sources = sorted({(m["source"], m["page"]) for m in metas})
    return {
        "answer": answer,
        "sources": [{"file": s, "page": p} for s, p in sources],
    }