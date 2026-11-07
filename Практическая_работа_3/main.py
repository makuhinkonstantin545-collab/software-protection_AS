import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import List

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

app = FastAPI(title="User Service", version="1.0.0")

NOTIFY_URL = "http://localhost:8001/notify/"
SECRET_KEY = os.environ.get("JWT_SECRET", "dev-only-secret-change-me")
ALGORITHM = "HS256"
TOKEN_MINUTES = 30
security = HTTPBearer()


class UserBase(BaseModel):
    name: str
    email: str
    age: int | None = None


class UserCreate(UserBase):
    pass


class SignupRequest(UserBase):
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class User(UserBase):
    id: int
    created_at: datetime
    is_active: bool = True


class Notification(BaseModel):
    user_id: int
    email: str
    message: str


users_db: dict[int, User] = {}
credentials_db: dict[str, dict] = {}
next_user_id = 1


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = int(payload["sub"])
    if user_id not in users_db:
        raise HTTPException(status_code=401, detail="User not found")
    return users_db[user_id]


async def send_welcome_notification(new_user: User):
    async with httpx.AsyncClient() as client:
        try:
            notification = Notification(
                user_id=new_user.id,
                email=new_user.email,
                message=f"Welcome, {new_user.name}!",
            )
            response = await client.post(
                NOTIFY_URL,
                json=notification.model_dump(),
                timeout=5.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            print(f"Failed to send notification for user {new_user.id}: {error}")


def add_user(data: UserCreate) -> User:
    global next_user_id
    for existing in users_db.values():
        if existing.email == data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        id=next_user_id,
        name=data.name,
        email=data.email,
        age=data.age,
        created_at=datetime.now(),
    )
    users_db[next_user_id] = new_user
    next_user_id += 1
    return new_user


@app.get("/")
async def root():
    return {"message": "User Service is running!", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/signup", response_model=User, status_code=201)
async def signup(data: SignupRequest):
    salt = secrets.token_bytes(16)
    new_user = add_user(UserCreate(name=data.name, email=data.email, age=data.age))
    credentials_db[data.email] = {
        "user_id": new_user.id,
        "salt": salt,
        "password_hash": hash_password(data.password, salt),
    }
    await send_welcome_notification(new_user)
    return new_user


@app.post("/login")
async def login(data: LoginRequest):
    record = credentials_db.get(data.email)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if hash_password(data.password, record["salt"]) != record["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(record["user_id"]), "token_type": "bearer"}


@app.post("/users/", response_model=User, status_code=201)
async def create_user(user: UserCreate):
    new_user = add_user(user)
    await send_welcome_notification(new_user)
    return new_user


@app.get("/users/", response_model=List[User])
async def get_users(skip: int = 0, limit: int = 10, min_age: int | None = None):
    users_list = list(users_db.values())
    if min_age is not None:
        users_list = [u for u in users_list if u.age is not None and u.age > min_age]
    return users_list[skip:skip + limit]


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]


@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user: UserCreate, current_user: User = Depends(get_current_user)):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = users_db[user_id]
    updated_user.name = user.name
    updated_user.email = user.email
    updated_user.age = user.age
    return updated_user


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: User = Depends(get_current_user)):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    del users_db[user_id]
    return {"message": f"User {user_id} deleted successfully"}
