import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    print("\n" + "=" * 60)
    print("JOBBRIDGE - INTEGRATED AI CAREER & RECRUITMENT PLATFORM")
    print("=" * 60)
    print(f"Server URL: http://{host}:{port}/")
    print(f"Health API: http://{host}:{port}/api/health")
    print(f"DB Status:  http://{host}:{port}/api/database-status")
    print("=" * 60 + "\n")

    app.run(
        host=host,
        port=port,
        debug=debug
    )
