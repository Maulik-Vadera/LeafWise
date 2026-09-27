"""Run from the project folder with the virtual environment's Python."""
from pathlib import Path
import os
import threading
import time
import urllib.request
import webbrowser

def main():
    try:
        import uvicorn
        from dotenv import load_dotenv
    except ImportError:
        raise SystemExit("Run Start-Windows.cmd first, or: python -m pip install -r requirements.txt")
    root = Path(__file__).resolve().parent
    os.chdir(root)
    load_dotenv(root / ".env")
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    url = f"http://127.0.0.1:{port}"
    def open_when_ready():
        for _ in range(20):
            try:
                with urllib.request.urlopen(url + "/api/status", timeout=1):
                    webbrowser.open(url)
                    return
            except Exception:
                time.sleep(.4)
    if os.getenv("NO_BROWSER", "0") != "1":
        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f"\nLeafwise is starting at {url}\nKeep this terminal open. Press Ctrl+C to stop.\n")
    uvicorn.run("app.main:app", host=host, port=port, access_log=False)

if __name__ == "__main__":
    main()
