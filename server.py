import os
import sys

# Forward to computer learning studio
target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "computer learning")
os.chdir(target_dir)
sys.path.insert(0, target_dir)

import uvicorn

if __name__ == "__main__":
    print(f"[Launcher] Starting BirdPath Computer Learning Studio from: {target_dir}")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
