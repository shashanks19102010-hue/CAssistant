import os
import asyncio
import uvicorn
import git
import json
from fastapi import FastAPI, HTTPException, Body, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Text, select
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
from typing import List, Dict, Optional
import secrets  # For session tokens

# =========================
# CONFIG & ENVIRONMENT
# =========================

load_dotenv()

# Default MODEL
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Database URL
DATABASE_URL = "sqlite+aiosqlite:///./memory.db"

# Session storage (in-memory for local ease)
sessions = {}

# =========================
# DATABASE SETUP
# =========================

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Memory(Base):
    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# =========================
# OPENAI CLIENT (Dynamic per session)
# =========================

def get_client(api_key: str):
    return AsyncOpenAI(api_key=api_key)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
async def generate_response(client, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 4000) -> str:
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {str(e)}")

# =========================
# FASTAPI APP (Enhanced with CORS, Sessions)
# =========================

app = FastAPI(title="AI Builder Pro - Ultimate Extreme Edition", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    await init_db()

# ── MODELS FOR REQUEST BODY ────────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str
    session_token: str

class MemoryRequest(BaseModel):
    title: str
    content: str
    session_token: str

class ProjectRequest(BaseModel):
    name: str
    session_token: str

class CodeReviewRequest(BaseModel):
    code: str
    session_token: str

class SEORequest(BaseModel):
    description: str
    session_token: str

class GitInitRequest(BaseModel):
    path: str
    session_token: str

# ── ENDPOINTS ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    session_token = request.cookies.get("session_token", None)
    if not session_token or session_token not in sessions:
        return RedirectResponse(url="/setup")
    return templates.TemplateResponse("index.html", {"request": request, "session_token": session_token})

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    return templates.TemplateResponse("setup.html", {"request": request})

@app.post("/setup")
async def setup_api(openai_key: str = Form(...)):
    if not openai_key.strip():
        raise HTTPException(status_code=400, detail="API key is required")
    
    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {"openai_key": openai_key}
    
    # Optionally save to .env for persistence
    with open(".env", "w") as f:
        f.write(f"OPENAI_API_KEY={openai_key}\n")
    
    response = RedirectResponse(url="/")
    response.set_cookie(key="session_token", value=session_token, httponly=True)
    return response

@app.post("/chat", response_model=Dict[str, str])
async def chat(request: ChatRequest):
    if request.session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    api_key = sessions[request.session_token]["openai_key"]
    client = get_client(api_key)
    
    try:
        messages = [{"role": "user", "content": request.prompt}]
        response = await generate_response(client, messages)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-memory", response_model=Dict[str, str])
async def save_memory(request: MemoryRequest):
    if request.session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    async with AsyncSessionLocal() as session:
        async with session.begin():
            memory = Memory(title=request.title, content=request.content)
            session.add(memory)
        await session.commit()
    return {"message": "Memory saved successfully"}

@app.get("/memory", response_model=Dict[str, List[Dict[str, str]]])
async def get_memory(session_token: str):
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Memory))
        memories = result.scalars().all()
        return {
            "memory": [{"title": m.title, "content": m.content} for m in memories]
        }

@app.post("/create-project", response_model=Dict[str, str])
async def create_project(request: ProjectRequest):
    if request.session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    try:
        project_dir = request.name.strip()
        if not project_dir:
            raise ValueError("Project name cannot be empty")

        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(os.path.join(project_dir, "static"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "templates"), exist_ok=True)

        readme_path = os.path.join(project_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# {project_dir}\n\nGenerated by AI Builder Pro Ultimate\n\n## Description\n\nPowered by your own OpenAI key for ultimate privacy and control.\n")

        return {"message": f"Project '{project_dir}' created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/review-code", response_model=Dict[str, str])
async def review_code(request: CodeReviewRequest):
    if request.session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    api_key = sessions[request.session_token]["openai_key"]
    client = get_client(api_key)
    
    try:
        messages = [
            {"role": "system", "content": "You are a senior software engineer. Review the code carefully, point out bugs, suggest improvements, security issues, performance optimizations, and better practices. Provide code snippets for fixes."},
            {"role": "user", "content": f"Review this code:\n\n{request.code}"}
        ]
        result = await generate_response(client, messages, temperature=0.6)
        return {"review": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-seo", response_model=Dict[str, str])
async def generate_seo(request: SEORequest):
    if request.session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    api_key = sessions[request.session_token]["openai_key"]
    client = get_client(api_key)
    
    try:
        messages = [
            {"role": "system", "content": "You are an expert SEO specialist. Generate optimized title (50-60 chars), meta description (150-160 chars), 8-12 keywords, and structured JSON output for easy parsing."},
            {"role": "user", "content": f"Content description:\n{request.description}"}
        ]
        result = await generate_response(client, messages, temperature=0.5)
        return {"seo": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/init-git", response_model=Dict[str, str])
async def git_init(request: GitInitRequest):
    if request.session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    try:
        path = request.path.strip()
        if not path or not os.path.isdir(path):
            raise ValueError("Invalid or missing project path")

        git_path = os.path.join(path, ".git")

        if os.path.exists(git_path):
            repo = git.Repo(path)
            action = "using existing"
        else:
            repo = git.Repo.init(path)
            action = "initialized new"

        repo.git.add(all=True)
        repo.index.commit("Initial commit by AI Builder Pro Ultimate")

        return {"message": f"Git repository {action} and committed at {path}"}
    except git.exc.GitCommandError as e:
        raise HTTPException(status_code=400, detail=f"Git error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── RUN SERVER ──────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
)
