# PDF RAG Chatbot

A chatbot that answers questions from your own PDF files. Answers come only from the uploaded documents, and each answer shows the file name and page number it used.

![Demo](screenshots/demo.png)

## Features
- Upload one or more PDFs
- Ask questions in a chat page
- Answers are based only on the document text, with sources (file and page)
- Pick one file to search in, or search all files
- Runs with Docker, or directly with Python

## Tech stack
- Python
- FastAPI (backend API)
- Streamlit (chat page)
- Gemini API (embeddings and answers)
- ChromaDB (vector database)
- Docker and Docker Compose

## How it works
1. **Upload:** the PDF text is split into chunks of 800 characters, with a 150 character overlap.
2. **Embed:** each chunk is turned into an embedding with the Gemini API and stored in ChromaDB, along with its file name and page number.
3. **Ask:** the question is turned into an embedding, and ChromaDB returns the 4 most similar chunks.
4. **Answer:** Gemini writes the answer using only those chunks. If the answer is not in them, it says it could not find it.

## Run with Docker
1. Install Docker Desktop.
2. Create a `.env` file in the project folder:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   You can get a free key from Google AI Studio.
3. Start the app:
   ```
   docker compose up --build
   ```
4. Open http://localhost:8501

The API runs on http://localhost:8000 (docs at `/docs`).

## Run without Docker
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Add the `.env` file as above, then start the two parts in separate terminals:
```
uvicorn main:app --reload
streamlit run ui.py
```

## API endpoints
| Method | Endpoint | What it does |
|--------|----------|--------------|
| POST | `/upload` | Upload a PDF and store its chunks |
| POST | `/ask` | Ask a question (optional `source` to search one file) |
| GET | `/files` | List the uploaded files |

## Project files
- `rag.py`: PDF reading, chunking, embeddings, search and answer
- `main.py`: FastAPI endpoints
- `ui.py`: Streamlit chat page
- `Dockerfile` and `docker-compose.yml`: container setup

## Limitations
- It reads only the 4 most similar chunks per question, so it cannot answer questions that need the whole document, such as counting how many times a word appears.
- Scanned PDFs (images without text) are not supported.
- The free Gemini plan allows about 100 embedding requests per minute. Large PDFs take longer because the app waits and retries when the limit is reached.