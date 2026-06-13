# Deployment & Remote Access

This document describes how to deploy the T1D RAG bot locally and expose it for remote testing.

## Prerequisites
- **Conda**: Environment `t1d` with all dependencies installed.
- **Docker**: For running Milvus (vector database).
- **Ollama**: For running the local LLM (`gemma4:e4b`).
- **VS Code**: For local port forwarding.

## Local Execution
1. **Start Milvus**:
   ```powershell
   docker compose up -d
   ```
2. **Start Ollama**: Ensure the Ollama service is running and the model is pulled.
3. **Run Streamlit**:
   ```powershell
   conda run -n t1d streamlit run app.py
   ```

## Remote Access (Mentors)
To allow mentors to access the bot from different locations, we use **VS Code Local Port Forwarding**:
- **Port**: `8501` (Default Streamlit port).
- **Visibility**: Must be set to **Public** in the VS Code Ports view.
- **Protocol**: HTTPS (Automatic via Dev Tunnels).

Refer to `local_port_forwarding_setup.md` in the root for a step-by-step guide on setting this up.
