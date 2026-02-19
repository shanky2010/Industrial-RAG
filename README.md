# ⚙️ IndustrialRAG

Generalized industrial maintenance troubleshooting system.
Admins upload machine manuals (PDF) and repair logs (Excel/CSV).
Maintenance personnel query problems in plain language and receive
structured answers — strictly from the uploaded documents, never hallucinated —
with clickable links to the exact manual page.

---

## Quick Start

```bash
pip install -r requirements.txt
chmod +x start.sh
./start.sh
```

Open **http://localhost:8501**

---

## Setup

### LLM (pick one — edit start.sh)

| Option | Setup |
|--------|-------|
| Ollama (local, free) | `ollama pull mistral` — default, works offline |
| OpenAI | Set `OPENAI_API_KEY` in start.sh |
| Anthropic | Set `ANTHROPIC_API_KEY` in start.sh |
| None | Rule-based fallback activates automatically |

### First run

1. Open Admin tab → enter machine name (e.g. `Pioneer 3`)
2. Upload the PDF manual for that machine
3. Optionally upload an Excel/CSV repair log
4. Switch to Troubleshoot tab → select machine → describe the problem

---

## Features

- **Strict grounding** — LLM is given only retrieved chunks, temperature=0, told explicitly not to use general knowledge
- **Relevance threshold** — chunks below 0.35 similarity score are dropped before the LLM sees them
- **Per-file delete** — remove a single PDF or Excel without wiping everything
- **Re-upload = refresh** — uploading the same filename replaces old chunks, no duplicates
- **All Machines mode** — separate results per machine, context never mixed
- **Chunk inspector** — expand any result to see which chunks were retrieved and their scores
- **PDF page links** — clickable references open the exact page in the manual

---

## File Structure

```
industrial_rag/
├── backend/
│   ├── main.py            API: upload, delete, query, format, serve PDFs
│   └── llm_formatter.py   LLM layer with strict grounding
├── frontend/
│   └── app.py             Streamlit UI
├── uploads/               Created automatically
│   ├── pdfs/
│   └── excels/
├── vectorstore/           Created automatically
│   ├── index.faiss
│   └── metadata.pkl
├── requirements.txt
├── start.sh
└── README.md
```

---

## API

```
POST   /admin/upload/pdf              Upload + index PDF
POST   /admin/upload/excel            Upload + index Excel/CSV
DELETE /admin/delete/pdf/{filename}   Remove PDF and its chunks
DELETE /admin/delete/excel/{filename} Remove Excel and its chunks
DELETE /admin/reset                   Wipe everything
POST   /query                         Query the knowledge base
POST   /format                        Format RAG context with LLM
GET    /admin/machines                List machine names
GET    /admin/stats                   Chunk counts + file list
GET    /pdf/{filename}                Serve PDF file
GET    /health                        Health check
```

Full docs: http://localhost:8000/docs

---

## Tuning

`RELEVANCE_THRESHOLD` in `backend/main.py`:
- `0.25` — loose, more results, possible weak matches
- `0.35` — default
- `0.45` — strict, only strong matches

`OLLAMA_MODEL` in `start.sh`:
- `mistral` — fast, good quality (default)
- `llama3` — larger, slower, better reasoning
- `gemma2` — good alternative
