import os
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
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
    """Turn a list of texts into a list of vectors (in batches)."""
    vectors = []
    for i in range(0, len(texts), 50):
        batch = texts[i:i + 50]
        result = client.models.embed_content(
            model=EMBED_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(task_type=task_type),
        )
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


def ask(question, k=4):
    """Retrieve the top-k chunks and answer from them."""
    if collection.count() == 0:
        return {"answer": "No documents uploaded yet.", "sources": []}

    q_vec = embed([question], "RETRIEVAL_QUERY")[0]
    res = collection.query(query_embeddings=[q_vec], n_results=k)
    docs, metas = res["documents"][0], res["metadatas"][0]

    context = "\n\n".join(
        f"[{m['source']} - page {m['page']}]\n{d}" for d, m in zip(docs, metas)
    )
    prompt = f"Context:\n{context}\n\nQuestion: {question}"

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    sources = sorted({(m["source"], m["page"]) for m in metas})
    return {
        "answer": response.text,
        "sources": [{"file": s, "page": p} for s, p in sources],
    }
