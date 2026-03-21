"""
Firebase Admin: verify Bearer ID tokens from the frontend (Google Sign-In).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, Tuple

from flask import current_app, jsonify, request

logger = logging.getLogger(__name__)

_initialized = False


def _get_credential():
    """Build credentials from env. Returns None if not configured."""
    cred_json = current_app.config.get("FIREBASE_CREDENTIALS_JSON")
    if cred_json:
        try:
            info = json.loads(cred_json)
        except json.JSONDecodeError as e:
            logger.error("FIREBASE_CREDENTIALS_JSON is not valid JSON: %s", e)
            return None
        from firebase_admin import credentials

        return credentials.Certificate(info)

    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.isfile(cred_path):
        from firebase_admin import credentials

        return credentials.Certificate(cred_path)

    return None


def init_firebase_admin() -> None:
    """Initialize Firebase Admin SDK once (no-op if auth disabled or already init)."""
    global _initialized

    if current_app.config.get("FIREBASE_AUTH_DISABLED"):
        logger.warning("FIREBASE_AUTH_DISABLED is set — API auth checks are bypassed")
        _initialized = True
        return

    import firebase_admin

    if firebase_admin._apps:
        _initialized = True
        return

    cred = _get_credential()
    if cred is None:
        logger.error(
            "Firebase Admin not initialized: set FIREBASE_CREDENTIALS_JSON or "
            "GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file path"
        )
        return

    firebase_admin.initialize_app(cred)
    _initialized = True
    logger.info("Firebase Admin SDK initialized")


def is_auth_effective() -> bool:
    """True if we enforce Firebase verification (not disabled and app initialized)."""
    if current_app.config.get("FIREBASE_AUTH_DISABLED"):
        return False
    import firebase_admin

    return bool(firebase_admin._apps)


def verify_bearer_token() -> Optional[Tuple[Any, int]]:
    """
    Verify Authorization: Bearer <idToken>.
    On success sets request.firebase_user to decoded claims and returns None.
    On failure returns (jsonify(...), status_code).
    """
    # CORS preflight never sends Authorization — skip auth so the browser can send the real GET/POST.
    if request.method.upper() == "OPTIONS":
        return None

    if current_app.config.get("FIREBASE_AUTH_DISABLED"):
        request.firebase_user = {
            "uid": "dev",
            "email": "dev@local",
            "email_verified": True,
        }
        return None

    import firebase_admin
    from firebase_admin import auth as fb_auth

    if not firebase_admin._apps:
        return (
            jsonify(
                {
                    "error": "Server authentication not configured",
                    "detail": "Set FIREBASE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS",
                }
            ),
            503,
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401

    token = auth_header[7:].strip()
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        decoded = fb_auth.verify_id_token(token, check_revoked=False)
    except Exception as e:
        logger.warning("verify_id_token failed: %s", e)
        return jsonify({"error": "Unauthorized"}), 401

    allowed_uids = current_app.config.get("ALLOWED_FIREBASE_UIDS") or []
    allowed_emails = current_app.config.get("ALLOWED_EMAILS") or []

    if allowed_uids:
        uid = decoded.get("uid") or ""
        if uid not in allowed_uids:
            return jsonify(
                {"error": "Forbidden", "detail": "Firebase UID not in allowlist"}
            ), 403
    elif allowed_emails:
        email = (decoded.get("email") or "").lower()
        if email not in allowed_emails:
            return jsonify({"error": "Forbidden", "detail": "Email not allowed"}), 403

    request.firebase_user = decoded
    return None


def register_protected_blueprint_guards(upload_bp, transactions_bp) -> None:
    """Require a valid Firebase token for all routes on these blueprints."""

    @upload_bp.before_request
    def _guard_upload():
        err = verify_bearer_token()
        if err is not None:
            return err[0], err[1]

    @transactions_bp.before_request
    def _guard_transactions():
        err = verify_bearer_token()
        if err is not None:
            return err[0], err[1]
