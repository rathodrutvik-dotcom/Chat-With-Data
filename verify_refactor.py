
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from models.session import PipelineResult, RagSession
    print("✅ PipelineResult imported from models.session")
    
    from rag.pipeline import proceed_input
    print("✅ proceed_input imported from rag.pipeline")
    
    from api_server import upload_documents
    print("✅ upload_documents imported from api_server")
    
    import main
    print("✅ main module imported")

    print("\nRefactoring verification successful: All modules load without import errors.")
except ImportError as e:
    print(f"\n❌ ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    sys.exit(1)
