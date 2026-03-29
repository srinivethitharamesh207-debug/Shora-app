from datetime import datetime, timedelta
import hashlib
import uuid
import os

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from dotenv import load_dotenv
import certifi

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

APP_SECRET = "shora-demo-secret"
TOKEN_TTL = timedelta(hours=24)
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "shora")

if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI is not set. Add it to fastapi_backend/.env or environment variables.")

def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y")

def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

mongo_optional = env_bool("MONGODB_OPTIONAL", True)
mongo_available = False
client = None
db = None
users_col = None
courses_col = None
progress_col = None

try:
    client = MongoClient(
        MONGODB_URI,
        tls=env_bool("MONGODB_TLS", True),
        tlsCAFile=certifi.where(),
        tlsAllowInvalidCertificates=env_bool("MONGODB_TLS_ALLOW_INVALID", False),
        tlsAllowInvalidHostnames=env_bool("MONGODB_TLS_ALLOW_INVALID_HOSTNAMES", False),
        serverSelectionTimeoutMS=env_int("MONGODB_SERVER_SELECTION_TIMEOUT_MS", 10000),
        connectTimeoutMS=env_int("MONGODB_CONNECT_TIMEOUT_MS", 20000),
        socketTimeoutMS=env_int("MONGODB_SOCKET_TIMEOUT_MS", 20000),
    )
    client.admin.command("ping")
    db = client[MONGODB_DB]
    users_col = db["users"]
    courses_col = db["courses"]
    progress_col = db["progress"]
    users_col.create_index("email", unique=True)
    mongo_available = True
except PyMongoError as exc:
    if not mongo_optional:
        raise
    print(f"[WARN] MongoDB connection failed, using in-memory data. Reason: {exc}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://[::]:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirmPassword: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def hash_password(password: str) -> str:
    salted = (APP_SECRET + password).encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def build_user_response(user: dict) -> dict:
    return {"id": user["id"], "name": user["name"], "email": user["email"]}


tokens: dict[str, dict] = {}

COURSES = [
    {"id": "py-basics", "title": "Python Basics", "level": "Beginner", "tag": "Py"},
    {"id": "react-intermediate", "title": "React Fundamentals", "level": "Intermediate", "tag": "JS"},
    {"id": "ml-python", "title": "Machine Learning with Python", "level": "Advanced", "tag": "Py"},
    {"id": "uiux-essentials", "title": "UI/UX Essentials for Designers", "level": "Beginner", "tag": "UI"},
    {"id": "java-beginners", "title": "Java for Beginners", "level": "Beginner", "tag": "Ja"},
]

PROGRESS_SAMPLE = {
    "weekly_hours": [0, 0, 0, 0, 0, 0],
    "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    "completed_pct": 0,
    "badges_pct": 0,
    "courses_mastered": 0,
    "streak_days": 0,
}

memory_users: list[dict] = []
memory_progress: dict = {"id": "default", **PROGRESS_SAMPLE}


def seed_courses() -> None:
    if not mongo_available:
        return
    if courses_col.count_documents({}) == 0:
        courses_col.insert_many(COURSES)


def seed_progress() -> None:
    if not mongo_available:
        return
    if progress_col.count_documents({}) == 0:
        progress_col.insert_one({"id": "default", **PROGRESS_SAMPLE})


def seed_dummy_user() -> None:
    email = "test@shora.com"
    if mongo_available:
        if users_col.find_one({"email": email}):
            return
        users_col.insert_one(
            {
                "id": str(uuid.uuid4()),
                "name": "Test User",
                "email": email,
                "password_hash": hash_password("123456"),
            }
        )
        return
    if any(u["email"] == email for u in memory_users):
        return
    memory_users.append(
        {
            "id": str(uuid.uuid4()),
            "name": "Test User",
            "email": email,
            "password_hash": hash_password("123456"),
        }
    )


seed_courses()
seed_progress()
seed_dummy_user()

def find_user_by_email(email: str) -> dict | None:
    if mongo_available:
        return users_col.find_one({"email": email})
    for user in memory_users:
        if user["email"] == email:
            return user
    return None


def insert_user(user_doc: dict) -> None:
    if mongo_available:
        users_col.insert_one(user_doc)
        return
    if any(u["email"] == user_doc["email"] for u in memory_users):
        raise DuplicateKeyError("duplicate email")
    memory_users.append(user_doc)


def list_courses_data() -> list[dict]:
    if mongo_available:
        return list(courses_col.find({}, {"_id": 0}))
    return COURSES


def get_progress_data() -> dict:
    if mongo_available:
        doc = progress_col.find_one({"id": "default"}, {"_id": 0})
        return doc or PROGRESS_SAMPLE
    return memory_progress


@app.post("/api/auth/signup")
def signup(payload: SignupRequest):
    name = payload.name.strip() if payload.name else ""
    email = payload.email.strip().lower() if payload.email else ""
    password = payload.password or ""
    confirm = payload.confirmPassword or ""

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if password != confirm:
        raise HTTPException(status_code=400, detail="Password and confirm password must match")

    user_doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
    }

    try:
        insert_user(user_doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")

    token = str(uuid.uuid4())
    tokens[token] = {"email": email, "expires_at": datetime.utcnow() + TOKEN_TTL}

    return {"token": token, "user": build_user_response(user_doc)}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    email = payload.email.strip().lower() if payload.email else ""
    password = payload.password or ""

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = find_user_by_email(email)
    if not user or user["password_hash"] != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = str(uuid.uuid4())
    tokens[token] = {"email": email, "expires_at": datetime.utcnow() + TOKEN_TTL}

    return {"token": token, "user": build_user_response(user)}


@app.get("/api/auth/validate")
def validate_token(Authorization: str | None = Header(default=None)):
    token = Authorization
    if token and token.startswith("Bearer "):
        token = token[7:]

    if not token:
        return {"valid": False, "message": "Token is missing"}

    stored = tokens.get(token)
    if not stored:
        return {"valid": False, "message": "Token is invalid"}

    if stored["expires_at"] < datetime.utcnow():
        tokens.pop(token, None)
        return {"valid": False, "message": "Token expired"}

    return {"valid": True}


@app.get("/api/courses")
def list_courses():
    items = list_courses_data()
    return {"items": items}


@app.get("/api/progress")
def get_progress():
    return get_progress_data()
