import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import db
from config import config

def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Register models; optional create_all (skipped in production by default — faster cold boot)
    with app.app_context():
        from models.transaction import Transaction  # noqa: F401 — register model

        if app.config.get('ENABLE_DB_CREATE_ALL'):
            db.create_all()
    
    # Firebase Admin (verify Google Sign-In tokens)
    from utils.firebase_auth import init_firebase_admin, register_protected_blueprint_guards, verify_bearer_token

    with app.app_context():
        init_firebase_admin()

    # Register blueprints
    from routes.upload import upload_bp
    from routes.transactions import transactions_bp

    register_protected_blueprint_guards(upload_bp, transactions_bp)

    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(transactions_bp, url_prefix='/api')

    # Health check endpoint (public)
    @app.route('/api/health', methods=['GET'])
    def health():
        return {'status': 'ok'}, 200

    @app.route('/api/me', methods=['GET', 'OPTIONS'])
    def api_me():
        """Return current user from verified Firebase ID token (requires Bearer token)."""
        if request.method == 'OPTIONS':
            return '', 204
        err = verify_bearer_token()
        if err is not None:
            return err[0], err[1]
        u = getattr(request, 'firebase_user', {}) or {}
        return jsonify(
            {
                'uid': u.get('uid') or u.get('user_id'),
                'email': u.get('email'),
                'email_verified': u.get('email_verified', False),
            }
        ), 200
    
    # Error handlers
    @app.errorhandler(413)
    def handle_file_too_large(error):
        return {
            'error': f'File too large (max {app.config["MAX_UPLOAD_SIZE_MB"]}MB)'
        }, 413
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
