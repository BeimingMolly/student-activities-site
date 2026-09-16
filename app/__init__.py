from __future__ import annotations

import os
from pathlib import Path
import secrets

from flask import Flask

from .database import init_db


def load_secret_key(base_dir: Path) -> str:
    env_secret = os.environ.get("STUDENT_ACTIVITIES_SECRET_KEY")
    if env_secret:
        return env_secret

    secret_path = base_dir / "data" / "session.secret"
    secret_path.parent.mkdir(exist_ok=True)
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()

    secret = secrets.token_hex(32)
    secret_path.write_text(secret, encoding="utf-8")
    return secret


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    web_dir = base_dir / "web"

    flask_app = Flask(__name__, static_folder=None)
    flask_app.config["WEB_DIR"] = web_dir
    flask_app.json.ensure_ascii = False
    flask_app.secret_key = load_secret_key(base_dir)

    init_db()

    from .routes import register_routes

    register_routes(flask_app)
    return flask_app
