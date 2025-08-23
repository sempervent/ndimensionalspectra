# src/ndimensionalspectra/__main__.py
from __future__ import annotations
import argparse
import os
import sys

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ndimensionalspectra",
        description="Unified entrypoint: CLI (default) or API (--api).",
    )
    parser.add_argument(
        "--api", dest="api", action="store_true",
        help="Serve the FastAPI app via Uvicorn."
    )
    parser.add_argument(
        "--host", default=os.environ.get("HOST", "0.0.0.0"),
        help="API host (when --api)."
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8080")),
        help="API port (when --api)."
    )
    parser.add_argument(
        "cli_args", nargs=argparse.REMAINDER,
        help="CLI args forwarded to 'om' when not using --api."
    )
    args = parser.parse_args()

    if args.api:
        # Defer import: keep CLI fast and avoid uvicorn import if not needed
        import uvicorn
        from .ontogenic_api import app
        uvicorn.run(app, host=args.host, port=args.port)
        return

    # Default to CLI mode; forward remaining args to Click group
    from .ontogenic_cli import om
    # Forward CLI args directly to the Click group
    cli_args = [a for a in args.cli_args if a not in ("--",)]
    om.main(args=cli_args, prog_name="om")

def main_api() -> None:
    # Helper script entry to run API directly (for pyproject scripts)
    import uvicorn
    from .ontogenic_api import app
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()