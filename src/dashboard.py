"""
Type 1 Diabetes RAG Bot - Static SPA Dashboard Launcher

The Streamlit dashboard has been migrated to a high-performance, zero-rerun Static SPA
served directly by the FastAPI backend (service.py).

Run this script to start the service and launch the web UI in your default browser:
    python src/dashboard.py
"""

import os
import sys
import webbrowser
import urllib.request
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def is_service_running(url: str) -> bool:
    """Check if the T1D RAG Bot service is already running on the target port."""
    try:
        req = urllib.request.Request(f"{url}/health")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("status") == "ok"
    except Exception:
        pass
    return False

def main():
    port = int(os.getenv("RAG_SERVICE_PORT", "8002"))
    url = f"http://localhost:{port}"

    if is_service_running(url):
        print(f"[INFO] T1D RAG Bot Service is ALREADY running at {url}.")
        print(f"Opening browser UI at {url}...")
        webbrowser.open(url)
        return

    import uvicorn
    print(f"Starting T1D RAG Bot Service & Static SPA at {url}...")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Open browser manually at: {url}")
    uvicorn.run("src.service:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
