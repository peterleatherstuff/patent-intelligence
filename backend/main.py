from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
from typing import List, Optional
from datetime import datetime

# === App setup ===
app = FastAPI(
    title="Patent Intelligence API",
    description="Find relevant patents for your project",
    version="1.0.0"
)

# === CORS setup ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://patent-app-frontend.onrender.com"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Models ===
class ProjectRequest(BaseModel):
    description: str

class PatentResult(BaseModel):
    id: str
    title: str
    abstract: str
    url: str
    status: str  # "Active" or "Expired"
    priority_date: Optional[str] = None
    assignee: Optional[str] = None

class AnalysisResponse(BaseModel):
    project_description: str
    patents: List[PatentResult]
    estimated_savings: float
    timestamp: str

# === Sample data (replace with real API later) ===
SAMPLE_PATENTS = [
    {
        "id": "US7377377B2",
        "title": "Thermal management system for battery packs",
        "abstract": "A thermal management system for battery packs in electric vehicles.",
        "url": "https://patents.google.com/patent/US7377377B2",
        "status": "Expired",
        "priority_date": "2005-06-15",
        "assignee": "General Motors"
    },
    {
        "id": "US8293412B2",
        "title": "Battery cell cooling system",
        "abstract": "A cooling system for battery cells using phase change materials.",
        "url": "https://patents.google.com/patent/US8293412B2",
        "status": "Active",
        "priority_date": "2010-03-22",
        "assignee": "Tesla Motors"
    },
    {
        "id": "US9126501B2",
        "title": "Thermal regulation of battery modules",
        "abstract": "System for regulating temperature in electric vehicle battery modules.",
        "url": "https://patents.google.com/patent/US9126501B2",
        "status": "Expired",
        "priority_date": "2012-11-30",
        "assignee": "Ford Global Technologies"
    }
]

# === Routes ===
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "live_data": os.getenv("ABACUS_API_KEY") is not None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_project(req: ProjectRequest):
    # Simulate analysis
    expired_count = sum(1 for p in SAMPLE_PATENTS if p["status"] == "Expired")
    estimated_savings = expired_count * 50000.0  # $50k per expired patent

    return AnalysisResponse(
        project_description=req.description,
        patents=[PatentResult(**p) for p in SAMPLE_PATENTS],
        estimated_savings=estimated_savings,
        timestamp=datetime.utcnow().isoformat()
    )