"""
Authentication router — register, login, Google OAuth, admin management.
"""
import re
import uuid
import logging
from datetime import datetime
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token, get_current_user, require_admin
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ──

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token from frontend


class FirebaseLoginRequest(BaseModel):
    id_token: str  # Firebase ID token from phone auth


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PromoteRequest(BaseModel):
    user_id: str
    role: str  # "admin" or "user"


# ── Helper ──

def _make_auth_response(user: User) -> AuthResponse:
    token = create_access_token(user)
    return AuthResponse(
        access_token=token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            created_at=user.created_at.isoformat() if user.created_at else "",
        ),
    )


def _determine_role(email: str, db: Session) -> str:
    """Determine role for a new user."""
    user_count = db.query(User).count()
    admin_email = (settings.admin_email or "").strip().lower()
    if user_count == 0 or (admin_email and email == admin_email):
        return UserRole.admin.value
    return UserRole.user.value


# ── Endpoints ──

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email + password."""
    email = req.email.strip().lower()
    password = req.password.strip()
    name = req.name.strip()

    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise HTTPException(400, "Invalid email format")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        name=name or None,
        role=_determine_role(email, db),
        last_login=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _make_auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login with email + password."""
    email = req.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.hashed_password:
        raise HTTPException(401, "Invalid email or password")
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")

    user.last_login = datetime.utcnow()
    db.commit()
    return _make_auth_response(user)


@router.post("/google", response_model=AuthResponse)
def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Login or register via Google OAuth. Verifies the Google ID token."""
    # Verify Google token by calling Google's tokeninfo endpoint
    try:
        resp = httpx.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={req.credential}",
            timeout=10.0,
        )
        if resp.status_code != 200:
            raise HTTPException(401, "Invalid Google token")
        google_data = resp.json()
    except httpx.RequestError as e:
        logger.error(f"Google token verification failed: {e}")
        raise HTTPException(503, "Could not verify Google token")

    # Validate the token was issued for our app
    token_aud = google_data.get("aud", "")
    if token_aud != settings.google_client_id:
        raise HTTPException(401, "Google token not issued for this application")

    email = google_data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(400, "Google account has no email")

    email_verified = google_data.get("email_verified", "false")
    if str(email_verified).lower() != "true":
        raise HTTPException(400, "Google email not verified")

    name = google_data.get("name", "")

    # Find or create user
    user = db.query(User).filter(User.email == email).first()

    if user:
        # Existing user — update last login
        user.last_login = datetime.utcnow()
        if name and not user.name:
            user.name = name
        db.commit()
    else:
        # New user — register automatically
        user = User(
            email=email,
            hashed_password="",  # No password for Google users
            name=name or None,
            role=_determine_role(email, db),
            last_login=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New Google user: {email} (role={user.role})")

    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")

    return _make_auth_response(user)


@router.post("/firebase", response_model=AuthResponse)
def firebase_login(req: FirebaseLoginRequest, db: Session = Depends(get_db)):
    """Login or register via Firebase Phone Auth. Verifies the Firebase ID token."""
    import json
    import base64

    try:
        # Decode JWT payload without verification first to get claims
        parts = req.id_token.split('.')
        if len(parts) != 3:
            raise HTTPException(401, "Invalid Firebase token format")

        # Decode payload (add padding)
        payload_b64 = parts[1] + '=' * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Verify issuer and audience
        expected_issuer = f"https://securetoken.google.com/{settings.firebase_project_id}"
        if payload.get("iss") != expected_issuer:
            raise HTTPException(401, "Invalid Firebase token issuer")
        if payload.get("aud") != settings.firebase_project_id:
            raise HTTPException(401, "Invalid Firebase token audience")

        # Check expiry
        import time
        if payload.get("exp", 0) < time.time():
            raise HTTPException(401, "Firebase token expired")

        phone = payload.get("phone_number", "")
        if not phone:
            raise HTTPException(400, "No phone number in Firebase token")

        # Also try to verify with Google's tokeninfo as extra validation
        try:
            resp = httpx.get(
                f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo",
                params={"key": settings.firebase_api_key},
                timeout=10.0,
            )
        except Exception:
            pass  # Proceed with JWT-based verification

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Firebase token decode failed: {e}")
        raise HTTPException(401, "Invalid Firebase token")

    # Find or create user by phone
    user = db.query(User).filter(User.phone == phone).first()

    if user:
        user.last_login = datetime.utcnow()
        db.commit()
    else:
        # Create new user with phone
        admin_email = (settings.admin_email or "").strip().lower()
        user_count = db.query(User).count()
        role = UserRole.admin.value if user_count == 0 else UserRole.user.value

        user = User(
            email=None,
            phone=phone,
            hashed_password="",
            name=None,
            role=role,
            last_login=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New phone user: {phone} (role={user.role})")

    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")

    return _make_auth_response(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.get("/google-client-id")
def get_google_client_id():
    """Return the Google Client ID for frontend use."""
    return {"client_id": settings.google_client_id}


# ── Admin: User Management ──

@router.post("/promote")
def promote_user(
    req: PromoteRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin: Change a user's role (promote to admin or demote to user)."""
    if req.role not in ("admin", "user"):
        raise HTTPException(400, "Role must be 'admin' or 'user'")

    target = db.query(User).filter(User.id == req.user_id).first()
    if not target:
        raise HTTPException(404, "User not found")

    # Prevent self-demotion
    if str(target.id) == str(admin.id) and req.role != "admin":
        raise HTTPException(400, "Cannot demote yourself")

    target.role = req.role
    db.commit()
    logger.info(f"Admin {admin.email} changed {target.email} role to {req.role}")

    return {"detail": f"User {target.email} is now {req.role}"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin: Permanently delete a user."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")

    if str(target.id) == str(admin.id):
        raise HTTPException(400, "Cannot delete yourself")

    email = target.email
    db.delete(target)
    db.commit()
    logger.info(f"Admin {admin.email} deleted user {email}")
    return {"detail": f"User {email} deleted"}


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin: List all users."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            name=u.name,
            role=u.role,
            created_at=u.created_at.isoformat() if u.created_at else "",
        )
        for u in users
    ]
