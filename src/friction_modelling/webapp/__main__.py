"""Launch the friction-modelling website.

    friction-web                      # serve on http://localhost:8501
    python -m friction_modelling.webapp --port 8000 --reload

This is a thin wrapper around uvicorn so the site can be started with a single
console command both locally and inside Docker.
"""
from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the friction-modelling website.")
    parser.add_argument("--host", default=os.environ.get("FRICTION_WEB_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("FRICTION_WEB_PORT", "8501")),
    )
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes (dev only).")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "friction_modelling.webapp.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
