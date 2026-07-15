import json
from pathlib import Path

from app.main import app


def main() -> None:
    output = Path("openapi.json")
    output.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print(f"OpenAPI written to {output.resolve()}")


if __name__ == "__main__":
    main()
