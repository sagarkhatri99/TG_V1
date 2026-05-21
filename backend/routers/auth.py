from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
import os

from database import get_db
import models
from models import User

router = APIRouter(tags=["Authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str  # Frontend sends 'username' (but value is email)
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

class RegisterRequest(BaseModel):
    email: str
    password: str
    subscription_plan: str = "free"

class RegisterResponse(BaseModel):
    token: str
    user: dict

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint - accepts username (email) and password
    Returns JWT token and user info
    """
    
    # Find user by email (username field contains email)
    user = db.query(models.User).filter(
        models.User.email == login_data.username
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    # Return token and user info
    return {
        "token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "subscription_plan": getattr(user, 'subscription_plan', 'free')
        }
    }

async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token
    """
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Add token endpoint for standard OAuth2 flow if needed
@router.post("/token")
async def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    return await login_for_access_token(form_data, db)

@router.post("/register", response_model=RegisterResponse)
async def register_user(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user and return a JWT token.
    """
    existing_user = db.query(models.User).filter(
        models.User.email == register_data.email
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    new_user = models.User(
        email=register_data.email,
        password_hash=get_password_hash(register_data.password),
        subscription_plan=register_data.subscription_plan,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(
        data={"sub": str(new_user.id), "email": new_user.email}
    )
    return {
        "token": access_token,
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "subscription_plan": new_user.subscription_plan
        }
    }

@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Return the currently authenticated user's info.
    Used by the frontend to hydrate user state on page reload.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "subscription_plan": getattr(current_user, 'subscription_plan', 'free')
    }
