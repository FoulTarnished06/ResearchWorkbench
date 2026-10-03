import uvicorn
import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "true").lower() in ("true", "1", "yes")

    print("==================================================================")
    print("  AI Research Workbench v3.0 - Server Starting")
    print("  Strict 2-LLM Budget Multi-Agent Autonomous Research Pipeline")
    print("==================================================================")
    print(f"  Access the Workbench in your browser at: http://{host}:{port}")
    print("==================================================================")
    uvicorn.run("backend.app:app", host=host, port=port, reload=reload)
