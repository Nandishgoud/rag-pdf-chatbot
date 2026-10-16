import os
import shutil
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from rag import ask, ingest_pdf, list_files

app = FastAPI(title="PDF RAG Chatbot")


class Question(BaseModel):
    question: str
    source: str | None = None


@app.get("/")
def home():
    return {"status": "ok", "docs": "/docs"}


@app.post("/upload")
def upload(file: UploadFile):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
    try:
        count = ingest_pdf(tmp.name, file.filename)
    finally:
        os.remove(tmp.name)
    if count == 0:
        raise HTTPException(status_code=422, detail="No text found (scanned PDF?)")
    return {"file": file.filename, "chunks_stored": count}


@app.get("/files")
def files():
    return {"files": list_files()}


@app.post("/ask")
def ask_question(body: Question):
    return ask(body.question, body.source)