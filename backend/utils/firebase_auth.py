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


def _resolve_service_account_path() -> Optional[str]:
    """
    Path to Firebase service account JSON file.
    Render mounts secret files at /etc/secrets/<filename>; set FIREBASE_CREDENTIALS_PATH to that path.
    """
    for source in (
        (os.environ.get("FIREBASE_CREDENTIALS_PATH") or "").strip(),
        (current_app.config.get("FIREBASE_CREDENTIALS_PATH") or "").strip(),
    ):
        if source and os.path.isfile(source):
            return source

    gac = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if gac and os.path.isfile(gac):
        return gac

    return None


def _get_credential():
    """Build credentials from env. Returns None if not configured."""
    from firebase_admin import credentials

    path = _resolve_service_account_path()
    if path:
        try:
            return credentials.Certificate(path)
        except Exception as e:
            logger.error("Failed to load Firebase credentials from %s: %s", path, e)
            return None

    cred_json = (os.environ.get("FIREBASE_CREDENTIALS_JSON") or "").strip()
    if not cred_json:
        cfg = current_app.config.get("FIREBASE_CREDENTIALS_JSON")
        cred_json = (cfg or "").strip() if isinstance(cfg, str) else ""

    if cred_json:
        try:
            info = json.loads(cred_json)
        except json.JSONDecodeError as e:
            logger.error("FIREBASE_CREDENTIALS_JSON is not valid JSON: %s", e)
            return None
        try:
            return credentials.Certificate(info)
        except Exception as e:
            logger.error("FIREBASE_CREDENTIALS_JSON could not build credentials: %s", e)
            return None

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
            "Firebase Admin not initialized: set FIREBASE_CREDENTIALS_PATH (e.g. "
            "/etc/secrets/your_file.json on Render), FIREBASE_CREDENTIALS_JSON, or "
            "GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file path"
        )
        return

    firebase_admin.initialize_app(cred)
    _initialized = True
    p = _resolve_service_account_path()
    logger.info(
        "Firebase Admin SDK initialized%s",
        f" (service account file: {p})" if p else " (inline JSON)",
    )


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
        request.is_super_admin = True
        return None

    import firebase_admin
    from firebase_admin import auth as fb_auth

    if not firebase_admin._apps:
        return (
            jsonify(
                {
                    "error": "Server authentication not configured",
                    "detail": "Set FIREBASE_CREDENTIALS_PATH (Render: /etc/secrets/...), "
                    "FIREBASE_CREDENTIALS_JSON, or GOOGLE_APPLICATION_CREDENTIALS",
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

    uid = decoded.get("uid") or ""
    super_admin_uids = current_app.config.get("SUPER_ADMIN_UIDS") or []

    request.firebase_user = decoded
    request.is_super_admin = uid in super_admin_uids
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
