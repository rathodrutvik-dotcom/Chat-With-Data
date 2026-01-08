import sys
from pathlib import Path

# Add src to python path to emulate app structure
sys.path.append(str(Path.cwd() / "src"))

try:
    from config.settings import PROJECT_ROOT, EMBEDDING_STORE_DIR, DATA_DIR
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"EMBEDDING_STORE_DIR: {EMBEDDING_STORE_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"EMBEDDING_STORE_DIR exists: {EMBEDDING_STORE_DIR.exists()}")
    
    if EMBEDDING_STORE_DIR.exists():
        import os
        print(f"Permissions: {oct(os.stat(EMBEDDING_STORE_DIR).st_mode)}")
        
except Exception as e:
    print(f"Error: {e}")
