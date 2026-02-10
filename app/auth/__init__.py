"""Auth module — Apple Sign-In, JWT management, and credits."""

from app.auth.apple import verify_apple_identity_token
from app.auth.credits import CREDIT_COSTS, check_balance, grant_credits, spend_credits
from app.auth.dependencies import get_current_user, require_credits
from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    rotate_refresh_token,
)

__all__ = [
    "CREDIT_COSTS",
    "check_balance",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "get_current_user",
    "grant_credits",
    "require_credits",
    "rotate_refresh_token",
    "spend_credits",
    "verify_apple_identity_token",
]
