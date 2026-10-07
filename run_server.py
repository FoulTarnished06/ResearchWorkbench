import uvicorn
import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "false").lower() in ("true", "1", "yes")

    print("==================================================================")
    print("  AI Research Workbench v5.0 (Dual-Engine: v4.0 + v5.0 Tier 1)")
    print("  Deep-Verification Multi-Agent Autonomous Research Pipeline")
    print("==================================================================")
    print(f"  Access the Workbench in your browser at: http://{host}:{port}")
    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=["backend", "frontend"] if reload else None,
        reload_includes=["*.py", "*.html", "*.css", "*.js"] if reload else None,
        reload_excludes=[
            "*.db", "*.db*", "*.sqlite*", "cache.db*", "*.log", 
            "data/*", "*.jsonl", "*.tmp", "__pycache__/*", "*.pyc"
        ] if reload else None
    )
