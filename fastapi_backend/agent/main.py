import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

try:
    from google import genai
except Exception:
    genai = None

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://[::]:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_NAME = os.getenv("AGENT_NAME", "ShoraAgent")
AGENT_MODE = os.getenv("AGENT_MODE", "mentor")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
GEMINI_MODEL = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.5-flash")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
gemini_client = genai.Client(api_key=GOOGLE_API_KEY) if (genai and GOOGLE_API_KEY) else None


class AgentInput(BaseModel):
    message: str
    agent_type: str | None = "generic"


@app.get("/health")
def health():
    return {"status": "ok", "agent": AGENT_NAME, "mode": AGENT_MODE}


@app.get("/agent/info")
def agent_info():
    return {"name": AGENT_NAME, "mode": AGENT_MODE}


@app.post("/agent/chat")
def agent_chat(payload: AgentInput):
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
