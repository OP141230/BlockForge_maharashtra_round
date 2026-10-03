"""Root entrypoint for running BLACKBOX: AI Agent Flight Recorder."""
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  BLACKBOX: AI Agent Flight Recorder")
    print("  Server starting at: http://localhost:8000")
    print("  API Documentation:  http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
