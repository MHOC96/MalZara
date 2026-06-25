from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app


class JWTService:
    ALGORITHM = "HS256"

    @staticmethod
    def _secret():
        return current_app.config["SECRET_KEY"]

    @staticmethod
    def create_access_token(user):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user["id"]),
            "name": user["name"],
            "is_admin": bool(user["is_admin"]),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=current_app.config["JWT_ACCESS_TOKEN_MINUTES"]),
        }
        return jwt.encode(payload, JWTService._secret(), algorithm=JWTService.ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=current_app.config["JWT_REFRESH_TOKEN_DAYS"]),
        }
        return jwt.encode(payload, JWTService._secret(), algorithm=JWTService.ALGORITHM)

    @staticmethod
    def decode_token(token):
        try:
            return jwt.decode(token, JWTService._secret(), algorithms=[JWTService.ALGORITHM])
        except jwt.PyJWTError:
            return None

    @staticmethod
    def issue_token_pair(user):
        return {
            "access_token": JWTService.create_access_token(user),
            "refresh_token": JWTService.create_refresh_token(user["id"]),
            "token_type": "Bearer",
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_MINUTES"] * 60,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "is_admin": bool(user["is_admin"]),
            },
        }
