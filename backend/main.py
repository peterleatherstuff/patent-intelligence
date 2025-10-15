from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

app = FastAPI()

# Allow requests from your local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ok for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static demo patents
STATIC_PATENTS: List[Dict[str, Any]] = [
    {
        "patent_number": "US10326145B2",
        "title": "Battery thermal management system using phase change material",
        "abstract": "A battery thermal management system for electric vehicles that uses phase change materials to maintain optimal operating temperature.",
        "status": "Expired - Free to Use",
        "url": "https://patents.google.com/patent/US10326145B2",
        "relevance_score": 0.46,
    },
    {
        "patent_number": "US9847537B2",
        "title": "Lithium-ion battery cooling system with integrated heat exchanger",
        "abstract": "An integrated cooling system for lithium-ion batteries featuring a compact heat exchanger design.",
        "status": "Active Patent",
        "url": "https://patents.google.com/patent/US9847537B2",
        "relevance_score": 0.46,
    },
    {
        "patent_number": "US10320031B2",
        "title": "Battery pack thermal management with liquid cooling",
        "abstract": "Advanced liquid cooling system for battery packs using optimized flow channels and cooling plate designs.",
        "status": "Active Patent",
        "url": "https://patents.google.com/patent/US10320031B2",
        "relevance_score": 0.46,
    },
    {
        "patent_number": "US8993134B2",
        "title": "Phase change material composition for battery thermal regulation",
        "abstract": "A phase change material composition for battery thermal management providing improved heat absorption and release characteristics.",
        "status": "Expired - Free to Use",
        "url": "https://patents.google.com/patent/US8993134B2",
        "relevance_score": 0.44,
    },
]

class AnalyzeRequest(BaseModel):
    description: str

class AnalyzeResponse(BaseModel):
    project_description: str
    key_concepts: List[str]
    total_patents_found: int
    estimated_savings: str
    patents: List[Dict[str, Any]]
    pagination: Dict[str, Optional[int]]

@app.get("/health")
def health():
    return {"status": "healthy", "live_data": False, "timestamp": datetime.utcnow().isoformat()}

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    if not req.description or not req.description.strip():
        raise HTTPException(status_code=400, detail="Description is required")

    text = req.description.lower()
    concepts: List[str] = []
    if "battery" in text:
        concepts.append("battery")
    if "thermal" in text or "cool" in text or "heat" in text:
        concepts.append("thermal")
    if not concepts:
        concepts = ["general"]

    patents = STATIC_PATENTS

    expired_count = sum(1 for p in patents if "Expired" in p["status"])
    estimated_savings_value = expired_count * 15000
    estimated_savings_formatted = f"£{estimated_savings_value:,.0f}"

    limit = 19
    offset = 0
    total = len(patents)

    return {
        "project_description": req.description,
        "key_concepts": concepts,
        "total_patents_found": total,
        "estimated_savings": estimated_savings_formatted,
        "patents": patents,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "next_offset": None,
            "prev_offset": None,
        },
    }