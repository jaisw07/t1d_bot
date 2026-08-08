import os
import sys
import subprocess

# Ensure Milvus Lite compatibility on Windows
if os.name == "nt":
    os.rename = os.replace

if __name__ == "__main__":
    cmd = [sys.executable, "-m", "chainlit", "run", "src/chainlit_app.py", "--port", "8000"]
    sys.exit(subprocess.call(cmd))


