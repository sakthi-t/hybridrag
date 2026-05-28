import logging
import httpx
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)


async def _fetch_private_metadata(clerk_user_id: str) -> dict:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_user_id}",
                headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return (data.get("private_metadata") or {})
    except Exception as e:
        logger.warning(f"Clerk API unreachable for metadata: {e}")
    return {}


async def sync_clerk_user(db: Session, clerk_user_id: str, jwt_payload: dict) -> User:
    email = jwt_payload.get("email") or None
    private_meta = jwt_payload.get("private_metadata") or {}

    if not private_meta:
        private_meta = await _fetch_private_metadata(clerk_user_id)

    role_from_private = private_meta.get("role", "")

    user = db.query(User).filter_by(clerk_user_id=clerk_user_id).first()
    if user:
        if email and user.email != email:
            user.email = email
        if role_from_private and user.role != role_from_private:
            logger.info(f"Role change for {email}: {user.role} -> {role_from_private}")
            user.role = role_from_private
        db.commit()
        return user

    role = role_from_private or "user"
    user = User(clerk_user_id=clerk_user_id, email=email, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
