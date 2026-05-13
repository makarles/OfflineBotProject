FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRANSFORMERS_OFFLINE=0 \
    HF_DATASETS_OFFLINE=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

RUN python - <<'PY'
from sentence_transformers import SentenceTransformer, CrossEncoder
SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
CrossEncoder('BAAI/bge-reranker-v2-m3', max_length=512)
PY

COPY . .

ENV TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    SKYASSIST_DATABASE_URL=sqlite:///./data/skyassist.db \
    OLLAMA_URL=http://ollama:11434/api/generate \
    OLLAMA_MODEL=llama3.1:8b \
    OLLAMA_TIMEOUT=120

RUN chmod +x /app/scripts/start.sh

EXPOSE 8000 8500

CMD ["/app/scripts/start.sh"]
