# GPU Ingestion Checkpoint & Next Steps

This file serves as a checkpoint and resume guide for the remote GPU ingestion pipeline migration.

---

## 🔍 Current State (June 26, 2026)
*   **Model Config:** Google `gemma4:12b` (Ollama) + `BAAI/bge-m3` (PyTorch Embedder) + `Milvus Lite` (in-process database file `t1d_corpus.db`).
*   **Hardware:** Kubernetes interactive pod `gpu-interactive` (namespace `dgx-s-bmu-soet-230512-restricted`) running on an NVIDIA H200 GPU partition (16 GB VRAM).
*   **Ingestion Status:** The full ingestion pipeline was started in the background using `nohup` on the remote pod container inside `/workspace/t1d_bot/`.
*   **Log Output:** Being written to `/workspace/t1d_bot/pipeline.log`.

---

## 📋 Resuming Checklist (For Tomorrow)

### Step 1: Recreate Pod & Start Ollama inside Container
SSH back into the head node, ensure the pod is running, exec into the container, and start the Ollama background process:
```bash
ssh dgx-s-bmu-soet-230512@10.1.0.176

# If the pod was terminated, recreate it:
kubectl apply -f gpu-pod.yaml

# Exec into the container:
kubectl exec -it gpu-interactive -n dgx-s-bmu-soet-230512-restricted -- /bin/bash

# Start the Ollama background process:
export OLLAMA_MODELS=/user-home/.ollama/models
/user-home/bin/ollama serve > /workspace/ollama.log 2>&1 &

# Test that Ollama is responding (wait a few seconds first):
curl http://localhost:11434
```

### Step 2: Check or Resume Ingestion Progress
Check the end of the log file:
```bash
cd /workspace/t1d_bot
tail -n 50 pipeline.log
```
*   **Success Indicator:** Look for a line like:
    `[SUCCESS] Flow run completed. Processed XX pending sources.`

*   **Resume/Rerun Pipeline:** If the run failed/stopped, reset statuses and restart:
    ```bash
    # Reset any error statuses back to pending
    sed -i 's/status: error/status: pending/g' sources.yaml

    # Run in the background
    nohup venv/bin/python -m src.pipeline.run > pipeline.log 2>&1 &
    ```

### Step 3: Backup the Database
Once the run is complete, copy the generated Milvus database file from the ephemeral NVMe workspace to your persistent user home directory:
```bash
cp /workspace/t1d_bot/t1d_corpus.db /user-home/t1d_corpus.db
```

### Step 4: Stop & Delete the GPU Pod
Exit the container session to return to the head node, and delete the pod to release cluster resources:
```bash
exit
kubectl delete pod gpu-interactive -n dgx-s-bmu-soet-230512-restricted
```

### Step 5: Download Database to Local Laptop
Open a **new terminal on your local Windows laptop** (not the SSH session) and download the database file:
```bash
scp dgx-s-bmu-soet-230512@10.1.0.176:~/t1d_corpus.db C:\Users\SHREY\Desktop\t1d_bot\
```

### Step 6: Start Streamlit App Locally
Update your local environment configuration at `C:\Users\SHREY\Desktop\t1d_bot\.env`:
```env
LLM_PROVIDER=gemini
MILVUS_HOST=t1d_corpus.db
MILVUS_COLLECTION=t1d_corpus
```

Launch the Streamlit dashboard using your local database:
```bash
conda run -n t1d streamlit run app.py
```
