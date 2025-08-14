# apps/api/scripts/export_openapi.py
import json
from pathlib import Path
from app.main import app  # your FastAPI instance

def main():
    schema = app.openapi()  # FastAPI app -> OpenAPI dict
    out = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
