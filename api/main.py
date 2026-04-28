from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio

app = FastAPI(
    title="OSINT-Fusion API",
    description="Modern OSINT framework API",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    domain: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "OK", "framework": "OSINT-Fusion"}

@app.post("/search")
async def search(request: SearchRequest):
    # Placeholder - will call actual modules
    return {
        "status": "accepted",
        "task_id": "placeholder",
        "message": "Module execution coming soon"
    }

@app.get("/modules")
async def list_modules():
    return {
        "available": ["maigret", "holehe", "theharvester", "photon", "exif"],
        "coming_soon": 15
    }
