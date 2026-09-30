"""
export_openapi.py — Export FastAPI OpenAPI specification to JSON file.

Used by `npm run generate:api` and CI drift checks to regenerate frontend types
without needing a running HTTP server.
"""

import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import create_app  # noqa: E402


def export_openapi() -> None:
    app = create_app()
    openapi_schema = app.openapi()

    # Destination paths
    backend_out = backend_dir / "openapi.json"
    frontend_api_dir = Path(__file__).resolve().parent.parent / "frontend" / "src" / "lib" / "api"
    frontend_api_dir.mkdir(parents=True, exist_ok=True)
    frontend_out = frontend_api_dir / "openapi.json"

    with open(backend_out, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Exported OpenAPI schema to {backend_out}")

    with open(frontend_out, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Exported OpenAPI schema to {frontend_out}")


if __name__ == "__main__":
    export_openapi()
