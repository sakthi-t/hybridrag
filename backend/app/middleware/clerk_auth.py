import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db

_jwks_cache = None


async def _get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.clerk_jwks_url)
            _jwks_cache = resp.json()
    return _jwks_cache


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")

    token = auth_header.split(" ", 1)[1]
    jwks = await _get_jwks()

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    from app.services.auth_service import sync_clerk_user

    user = await sync_clerk_user(db, clerk_user_id, payload)
    return user
