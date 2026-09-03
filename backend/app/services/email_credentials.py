import base64
import hashlib

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EmailCredential
from app.schemas.email_credentials import EmailCredentialRead, EmailCredentialUpsert


def get_email_credential_status(db: Session, *, user_id: str) -> EmailCredentialRead:
    credential = _get(db, user_id=user_id)
    if credential is None:
        return EmailCredentialRead(configured=False)
    address, _ = decrypt_email_credential(credential)
    return EmailCredentialRead(
        configured=True,
        masked_email_address=_mask_email(address),
        enabled=credential.enabled,
        last_synced_at=credential.last_synced_at,
    )


def upsert_email_credential(
    db: Session, *, user_id: str, payload: EmailCredentialUpsert
) -> EmailCredentialRead:
    cipher = _cipher()
    credential = _get(db, user_id=user_id)
    if credential is None:
        credential = EmailCredential(user_id=user_id)
        db.add(credential)
    credential.provider = "qq"
    credential.encrypted_email_address = cipher.encrypt(payload.email_address.encode()).decode()
    credential.encrypted_authorization_code = cipher.encrypt(payload.authorization_code.encode()).decode()
    credential.enabled = True
    db.commit()
    db.refresh(credential)
    return get_email_credential_status(db, user_id=user_id)


def delete_email_credential(db: Session, *, user_id: str) -> bool:
    credential = _get(db, user_id=user_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def decrypt_email_credential(credential: EmailCredential) -> tuple[str, str]:
    cipher = _cipher()
    return (
        cipher.decrypt(credential.encrypted_email_address.encode()).decode(),
        cipher.decrypt(credential.encrypted_authorization_code.encode()).decode(),
    )


def get_email_credential(db: Session, *, user_id: str) -> EmailCredential | None:
    credential = _get(db, user_id=user_id)
    return credential if credential and credential.enabled else None


def list_email_credential_user_ids(db: Session) -> list[str]:
    return list(db.scalars(select(EmailCredential.user_id).where(EmailCredential.enabled.is_(True))).all())


def mark_email_credential_synced(db: Session, credential: EmailCredential, synced_at) -> None:
    credential.last_synced_at = synced_at
    db.commit()


def _get(db: Session, *, user_id: str) -> EmailCredential | None:
    return db.scalar(select(EmailCredential).where(EmailCredential.user_id == user_id))


def _cipher() -> Fernet:
    if not settings.app_encryption_key:
        raise RuntimeError("APP_ENCRYPTION_KEY is not configured")
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.app_encryption_key.encode()).digest())
    return Fernet(key)


def _mask_email(address: str) -> str:
    local, separator, domain = address.partition("@")
    if not separator:
        return "***"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"
