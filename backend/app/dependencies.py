from fastapi import Depends, HTTPException
from app.middleware.clerk_auth import get_current_user
from app.models.user import User


async def require_admin(user: User = Depends(get_current_user)):
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
