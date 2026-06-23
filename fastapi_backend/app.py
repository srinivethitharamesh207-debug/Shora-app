from datetime import datetime, timedelta
import hashlib
import uuid
import os

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from dotenv import load_dotenv
import certifi

# Add agent imports
import os
from openai import OpenAI

try:
    from google import genai
except Exception:
    genai = None

# Import agent functionality
# from agent.main import build_agent, AgentInput
# from langchain_core.messages import HumanMessage

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

APP_SECRET = "shora-demo-secret"
TOKEN_TTL = timedelta(hours=24)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_URI_LOCAL = os.getenv("MONGODB_URI_LOCAL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "shora")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY")
APPLE_REDIRECT_URI = os.getenv("APPLE_REDIRECT_URI", "http://localhost:8000/auth/apple/callback")

# Agent configuration
AGENT_NAME = os.getenv("AGENT_NAME", "ShoraAgent")
AGENT_MODE = os.getenv("AGENT_MODE", "mentor")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
GEMINI_MODEL = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.5-flash")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
gemini_client = genai.Client(api_key=GOOGLE_API_KEY) if (genai and GOOGLE_API_KEY) else None

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


def try_connect(uri: str, allow_tls: bool = True) -> bool:
    global client, db, users_col, courses_col, progress_col
    use_tls = allow_tls and env_bool("MONGODB_TLS", True)
    client = MongoClient(
        uri,
        tls=use_tls,
        tlsCAFile=certifi.where() if use_tls else None,
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
    return True


try:
    mongo_available = try_connect(MONGODB_URI, allow_tls=True)
    print("[INFO] Connected to MongoDB Atlas.")
except PyMongoError as exc:
    try:
        mongo_available = try_connect(MONGODB_URI_LOCAL, allow_tls=False)
        print("[INFO] Connected to local MongoDB.")
    except PyMongoError as exc_local:
        if not mongo_optional:
            raise
        print(f"[WARN] MongoDB connection failed, using in-memory data. Reason: {exc}")
        print(f"[WARN] Local MongoDB connection failed, using in-memory data. Reason: {exc_local}")


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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


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


@app.get("/api/auth/me")
def get_me(Authorization: str | None = Header(default=None)):
    token = Authorization
    if token and token.startswith("Bearer "):
        token = token[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Token is missing")

    stored = tokens.get(token)
    if not stored:
        raise HTTPException(status_code=401, detail="Token is invalid")

    if stored["expires_at"] < datetime.utcnow():
        tokens.pop(token, None)
        raise HTTPException(status_code=401, detail="Token expired")

    user = find_user_by_email(stored["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"user": build_user_response(user)}


@app.post("/api/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.strip().lower() if payload.email else ""
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    _ = find_user_by_email(email)
    return {"message": "If the email exists, a reset link has been sent."}


@app.get("/api/courses")
def list_courses():
    items = list_courses_data()
    return {"items": items}


@app.get("/api/progress")
def get_progress():
    return get_progress_data()


@app.get("/auth/google/login")
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return JSONResponse(
            status_code=501,
            content={"message": "Google OAuth not configured. Set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET."},
        )
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "consent",
    }
    qs = "&".join([f"{k}={str(v).replace(' ', '%20')}" for k, v in params.items()])
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{qs}")


@app.get("/auth/google/callback")
def google_callback(code: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"message": f"Google OAuth error: {error}"})
    if not code:
        return JSONResponse(status_code=400, content={"message": "Missing code from Google OAuth"})
    return JSONResponse(
        status_code=501,
        content={"message": "Google OAuth callback received. Token exchange not implemented yet."},
    )


@app.get("/auth/apple/login")
def apple_login():
    if not APPLE_CLIENT_ID or not APPLE_TEAM_ID or not APPLE_KEY_ID or not APPLE_PRIVATE_KEY:
        return JSONResponse(
            status_code=501,
            content={
                "message": "Apple OAuth not configured. Set APPLE_CLIENT_ID/TEAM_ID/KEY_ID/PRIVATE_KEY."
            },
        )
    params = {
        "client_id": APPLE_CLIENT_ID,
        "redirect_uri": APPLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "name email",
        "response_mode": "query",
    }
    qs = "&".join([f"{k}={str(v).replace(' ', '%20')}" for k, v in params.items()])
    return RedirectResponse(url=f"https://appleid.apple.com/auth/authorize?{qs}")


@app.get("/auth/apple/callback")
def apple_callback(code: str | None = None, error: str | None = None):
    if error:
        return JSONResponse(status_code=400, content={"message": f"Apple OAuth error: {error}"})
    if not code:
        return JSONResponse(status_code=400, content={"message": "Missing code from Apple OAuth"})
    return JSONResponse(
        status_code=501,
        content={"message": "Apple OAuth callback received. Token exchange not implemented yet."},
    )


class ChatMessage(BaseModel):
    message: str
    agent_type: str = "openai"  # Default to openai, can be "openai", "anthropic", or "gemini"


@app.post("/api/agent/chat")
def chat_with_agent(payload: ChatMessage, Authorization: str | None = Header(default=None)):
    # Validate token
    token = Authorization
    if token and token.startswith("Bearer "):
        token = token[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Token is missing")

    stored = tokens.get(token)
    if not stored:
        raise HTTPException(status_code=401, detail="Token is invalid")

    if stored["expires_at"] < datetime.utcnow():
        tokens.pop(token, None)
        raise HTTPException(status_code=401, detail="Token expired")

    # Process the chat message
    message = payload.message.strip() if payload.message else ""
    agent_type = (payload.agent_type or "generic").strip()

    if not message:
        return {"response": "Please enter a message."}

    use_openai = openai_client is not None
    use_gemini = gemini_client is not None

    if agent_type.lower() in ("gemini", "google"):
        if not use_gemini:
            raise HTTPException(
                status_code=500,
                detail="Gemini API key is not configured or Gemini client is unavailable.",
            )
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"Please respond in English. {message}",
            )
            text = getattr(response, "text", None) or "Okay."
            return {"response": text}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Gemini error: {exc}")

    if agent_type.lower() in ("openai", "chatgpt", "gpt", "generic"):
        if use_openai:
            try:
                system_text = (
                    f"You are {AGENT_NAME} in {AGENT_MODE} mode. "
                    "Please answer in English, be concise and helpful."
                )
                response = openai_client.responses.create(
                    model=OPENAI_MODEL,
                    input=[
                        {"role": "system", "content": system_text},
                        {"role": "user", "content": message},
                    ],
                )
                output_text = response.output_text or "Okay."
                return {"response": output_text}
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"OpenAI error: {exc}")
        elif use_gemini:
            try:
                response = gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=f"Please respond in English. {message}",
                )
                text = getattr(response, "text", None) or "Okay."
                return {"response": text}
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Gemini error: {exc}")
        else:
            raise HTTPException(
                status_code=500,
                detail="No API key configured for OpenAI or Gemini. Please set OPENAI_API_KEY or GOOGLE_API_KEY.",
            )

    raise HTTPException(
        status_code=400,
        detail="Unknown agent_type. Use 'openai', 'gemini', or 'generic'.",
    )
