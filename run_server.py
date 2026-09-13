import uvicorn
import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("==================================================================")
    print("  AI Research Workbench v2 - Server Starting")
    print("  Strict 2-LLM Budget Multi-Agent Autonomous Research Pipeline")
    print("==================================================================")
    print("  Access the Workbench in your browser at: http://127.0.0.1:8000")
    print("==================================================================")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
