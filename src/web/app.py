"""Flask application factory for the local analytics dashboard."""

from __future__ import annotations

from flask import Flask

from src.web.routes import create_dashboard_blueprint


def create_app() -> Flask:
    """Create and configure the dashboard Flask app."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.register_blueprint(create_dashboard_blueprint())
    return app


def main() -> None:
    """Run the dashboard on localhost for interactive use."""
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
