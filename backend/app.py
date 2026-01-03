# app.py — FINAL, CLEAN, PRODUCTION-READY (2025 VERSION)
from flask import Flask
from flask_cors import CORS

# Import all blueprints
from routes.content_routes import content_bp
from routes.auth_routes import auth_bp
from routes.webscraping_routes import lead_generator_bp
from routes.EmailGenerateAndValidator_routes import file_processor_bp

def create_app():
    app = Flask(__name__)

    # CORS — allows your live site + local development
    CORS(
        app,
        origins=[
            "https://emailagent.cubegtp.com",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://localhost",
            "http://65.1.129.37:3000",
            "http://65.1.129.37:8000",
            "http://65.1.129.37:5000",
            "http://65.1.129.37",
        ],
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-User-ID"]
    )

    # === REGISTER ALL BLUEPRINTS ===
    app.register_blueprint(content_bp)                                    # /generate, /send-campaign, etc.
    app.register_blueprint(auth_bp, url_prefix="/auth")                  # /auth/login, /auth/check-auth
    app.register_blueprint(lead_generator_bp, url_prefix="/webscraping") # Clean future path

    # THIS IS THE LINE THAT MAKES /api/upload-file WORK
    app.register_blueprint(file_processor_bp, url_prefix="/api")

    # Optional: Keep old /generate-leads working (safe with unique name)
    app.register_blueprint(
        lead_generator_bp,
        name="lead_generator_root",
        url_prefix=""
    )

    # Optional: Keep old /upload-file working too (if you want)
    app.register_blueprint(file_processor_bp, name="upload_root", url_prefix="")

    @app.route("/health")
    def health():
        return {"status": "healthy", "service": "emailagent-backend"}, 200

    return app


# Create app instance
app = create_app()

# Run in Docker / local
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
