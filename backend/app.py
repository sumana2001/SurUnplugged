"""
SurUnplugged - Flask Application Entry Point
"""
from flask import Flask, jsonify
from flask_cors import CORS

import config
from api.routes import api_bp


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config["DEBUG"] = config.DEBUG
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    
    # Enable CORS
    CORS(app, origins=config.CORS_ORIGINS)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Health check endpoint
    @app.route("/health")
    def health():
        return jsonify({"status": "healthy", "service": "SurUnplugged"})
    
    # Root endpoint
    @app.route("/")
    def index():
        return jsonify({
            "name": "SurUnplugged API",
            "version": "0.1.0",
            "description": "Acoustic guitar backing track generator with pitch control",
            "endpoints": {
                "upload": "POST /api/upload",
                "status": "GET /api/status/<job_id>",
                "result": "GET /api/result/<job_id>",
                "transpose": "POST /api/transpose",
            }
        })
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)
