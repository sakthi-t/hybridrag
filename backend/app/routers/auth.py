from fastapi import APIRouter, Depends
from app.models.user import User
from app.middleware.clerk_auth import get_current_user

router = APIRouter()


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_admin": user.is_admin(),
    }
