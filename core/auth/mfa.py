"""TOTP-based Multi-Factor Authentication"""
import pyotp
import qrcode
import io
import base64
from db.database import db_manager
from db.models.user import User


class MFAService:
    ISSUER = "Governex+"

    @staticmethod
    def generate_secret() -> str:
        """Generate a new random TOTP base32 secret."""
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, email: str) -> str:
        """Return the otpauth:// provisioning URI for QR encoding."""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email, issuer_name=MFAService.ISSUER
        )

    @staticmethod
    def generate_qr_base64(uri: str) -> str:
        """Render the provisioning URI as a base64-encoded PNG QR code."""
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """
        Verify a 6-digit TOTP code against the given secret.
        valid_window=1 allows ±30s clock skew (one window either side).
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def enable_mfa(user_id: int, secret: str) -> bool:
        """Persist the MFA secret and flip mfa_enabled for the given user."""
        with db_manager.session_scope() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.mfa_secret = secret
                user.mfa_enabled = True
                return True
            return False

    @staticmethod
    def disable_mfa(user_id: int) -> bool:
        """Clear MFA secret and disable MFA for the given user."""
        with db_manager.session_scope() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.mfa_secret = None
                user.mfa_enabled = False
                return True
            return False

    @staticmethod
    def is_mfa_enabled(user_id: int) -> bool:
        """Return True if MFA is currently enabled for the given user."""
        with db_manager.session_scope() as session:
            user = session.query(User).filter(User.id == user_id).first()
            return bool(user and user.mfa_enabled)

    @staticmethod
    def get_user_secret(user_id: int) -> str | None:
        """Return the stored TOTP secret for the given user, or None."""
        with db_manager.session_scope() as session:
            user = session.query(User).filter(User.id == user_id).first()
            return user.mfa_secret if user else None
