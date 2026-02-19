#!/bin/bash
# IndustrialRAG — start all services
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── LLM config ──────────────────────────────────────────
export USE_OLLAMA="true"           # set to "false" to skip Ollama
export OLLAMA_MODEL="mistral"      # change to llama3, gemma2, etc.
# export OPENAI_API_KEY="sk-..."
# export ANTHROPIC_API_KEY="sk-ant-..."

# ── Shared config ────────────────────────────────────────
export API_BASE="http://localhost:8000"

echo "⚙️  IndustrialRAG starting..."
echo ""

# ── Backend ──────────────────────────────────────────────
echo "Starting backend on :8000"
cd "$SCRIPT_DIR/backend"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend..."
for i in $(seq 1 15); do
    sleep 1
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend ready."
        break
    fi
    if [ $i -eq 15 ]; then
        echo "WARNING: Backend did not respond after 15s. Continuing anyway."
    fi
done

# ── Frontend ─────────────────────────────────────────────
echo "Starting frontend on :8501"
cd "$SCRIPT_DIR/frontend"
streamlit run app.py \
    --server.port 8501 \
    --server.headless true \
    --server.address 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "────────────────────────────────────────────"
echo "  Frontend : http://localhost:8501"
echo "  Backend  : http://localhost:8000"
echo "  API docs : http://localhost:8000/docs"
echo "────────────────────────────────────────────"
echo "  LLM: $([ "$USE_OLLAMA" = "true" ] && echo "Ollama ($OLLAMA_MODEL)" || echo "Cloud API")"
echo ""
echo "  Ctrl+C to stop"
echo ""

# Trap Ctrl+C and kill both
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait $BACKEND_PID $FRONTEND_PID
