# PDF RAG Chatbot

Upload PDFs and ask questions. Answers come only from your documents, with page sources.

**Stack:** Python, FastAPI, Gemini (embeddings + chat), ChromaDB

## Run locally
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your Gemini API key
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs, use `/upload` then `/ask`.

## How it works
PDF -> pages -> chunks (800 chars, 150 overlap) -> Gemini embeddings -> ChromaDB.
Question -> embedding -> top 4 similar chunks -> Gemini answers from those chunks.
