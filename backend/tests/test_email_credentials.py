from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base_class import Base
from app.db.models import EmailCredential
from app.schemas.email_credentials import EmailCredentialUpsert
from app.services.email_credentials import (
    decrypt_email_credential,
    delete_email_credential,
    get_email_credential_status,
    upsert_email_credential,
)


def test_user_email_credentials_are_encrypted_and_isolated(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_encryption_key", "test-only-secret")
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        status = upsert_email_credential(
            db,
            user_id="user-a",
            payload=EmailCredentialUpsert(
                email_address="student@qq.com",
                authorization_code="mail-authorization-code",
            ),
        )
        stored = db.scalar(select(EmailCredential).where(EmailCredential.user_id == "user-a"))

        assert status.configured is True
        assert status.masked_email_address == "st***@qq.com"
        assert stored is not None
        assert "student@qq.com" not in stored.encrypted_email_address
        assert "mail-authorization-code" not in stored.encrypted_authorization_code
        assert decrypt_email_credential(stored) == ("student@qq.com", "mail-authorization-code")
        assert get_email_credential_status(db, user_id="user-b").configured is False
        assert delete_email_credential(db, user_id="user-a") is True
        assert get_email_credential_status(db, user_id="user-a").configured is False
