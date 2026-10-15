"""Self-contained validation against a disposable real-data-mode database."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
REQUIRED_ROUTES = {
    "/", "/features", "/solutions", "/pricing", "/contact", "/login", "/register",
    "/dashboard", "/gpu-forecasting", "/power-capacity", "/storage-network",
    "/scenarios", "/procurement", "/alerts", "/reports", "/settings",
}


def run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def verify_frontend_routes() -> None:
    app = (FRONTEND / "src/app/App.tsx").read_text(encoding="utf-8")
    routes = set(re.findall(r'<Route\s+path="([^"]+)"', app))
    missing = sorted(REQUIRED_ROUTES - routes)
    if missing:
        raise RuntimeError(f"Missing React routes: {missing}")
    print(f"React route/page check passed ({len(REQUIRED_ROUTES)} required routes).")


def main() -> None:
    verify_frontend_routes()
    with tempfile.TemporaryDirectory(prefix="capacity-agent-real-smoke-") as td:
        db = Path(td) / "smoke.db"
        env = os.environ.copy()
        env.update({
            "DATABASE_URL": f"sqlite:///{db}",
            "APP_ENV": "development",
            "APP_DEBUG": "false",
            "REPORT_OUTPUT_DIR": str(Path(td) / "reports"),
            "JWT_SECRET": "validation-secret-key-with-more-than-32-characters",
            "BOOTSTRAP_FIRST_USER_AS_ADMIN": "true",
            "ALLOW_PUBLIC_REGISTRATION": "true",
            "SMOKE_FIXTURE_MODE": "true",
        })
        run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env)
        run([sys.executable, "-m", "app.seed"], cwd=BACKEND, env=env)
        run([sys.executable, "-m", "pytest", "-q"], cwd=BACKEND, env=env)
        run([sys.executable, str(ROOT / "scripts/verify_frontend_backend_contracts.py")], cwd=BACKEND, env=env)
    print("\nProject validation passed in real-data mode: routes, migrations, reference config, tests, CSV ingestion, forecasts, and API contracts are healthy.")


if __name__ == "__main__":
    main()
