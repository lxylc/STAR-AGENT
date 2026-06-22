"""对话式学习画像自主构建 - Flask 入口。"""
import logging
import sys
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

from config import Config
from models import db
from routes.profile_routes import bp as profile_bp

# 保证包内 import 在直接运行 app.py 时可用
sys.path.insert(0, str(Path(__file__).resolve().parent))


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def create_app() -> Flask:
    setup_logging()
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    app.register_blueprint(profile_bp)

    @app.route("/media/<int:student_id>/<path:filename>")
    def serve_media(student_id: int, filename: str):
        base = Path(Config.MEDIA_DIR) / str(student_id)
        return send_from_directory(base, filename)

    with app.app_context():
        try:
            from services.mongo_client import ensure_indexes
            ensure_indexes()
        except Exception as exc:
            logging.getLogger(__name__).warning("MongoDB 未连接，对话功能将不可用: %s", exc)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
