# Build context: repository root.
ARG OLLAMA_IMAGE=ollama/ollama:0.40.4
FROM ${OLLAMA_IMAGE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/qa-venv
ENV PATH="/opt/qa-venv/bin:${PATH}" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8000 PORT_HEALTH=8081 QA_DATA_DIR=/runpod-volume
WORKDIR /srv/qa
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu && python -m pip install --no-cache-dir -r requirements.txt && python -m pip check
COPY app/*.py ./app/
COPY web/ ./web/
COPY deploy/setup_ollama.py ./deploy/setup_ollama.py
COPY deploy/runpod-demo/runtime/ ./runtime/
COPY deploy/runpod-demo/assets.json ./assets.json
RUN python -c "import faiss, torch, transformers, sentence_transformers; import runtime.launch"
EXPOSE 8000 8081
ENTRYPOINT ["python", "-m", "runtime.launch"]
CMD []
