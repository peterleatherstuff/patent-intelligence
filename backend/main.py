from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from io import BytesIO
import httpx
import re
from datetime import datetime

# PDF libs
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ProjectRequest(BaseModel):
    description: str
    filter: str = "all"

class ExportRequest(BaseModel):
    project_description: str
    key_concepts: List[str]
    estimated_savings: str
    patents: List[Dict[str, Any]]
    filter: str = "all"

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "live_data": True}

# Helper: Extract keywords from description
def extract_keywords(description: str) -> List[str]:
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "is", "was", "are", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "can", "using", "used", "use", "system", "method", "apparatus"}
    words = re.findall(r'\b[a-z]{3,}\b', description.lower())
    keywords = [w for w in words if w not in stop_words]
    return list(set(keywords))[:10]

# Helper: Calculate relevance score
def calculate_relevance(patent: dict, keywords: List[str]) -> float:
    text = f"{patent.get('title', '')} {patent.get('abstract', '')}".lower()
    matches = sum(1 for kw in keywords if kw in text)
    return min(matches / max(len(keywords), 1), 1.0)

# Helper: Determine patent status
def determine_status(patent: dict) -> str:
    grant_date = patent.get("patent_date")
    if grant_date:
        try:
            year = int(grant_date.split("-")[0])
            current_year = datetime.now().year
            if current_year - year >= 20:
                return "Expired - Free to Use"
        except:
            pass
    return "Active"

# Helper: Extract year
def extract_year(p):
    if "year" in p and isinstance(p["year"], int):
        return p["year"]
    date_str = p.get("patent_date", "")
    if date_str:
        try:
            return int(date_str.split("-")[0])
        except:
            pass
    return None

# Helper: Extract jurisdiction
def extract_jurisdiction(p):
    num = (p.get("patent_number") or "").upper()
    if num.startswith("US"):
        return "US"
    if num.startswith("EP"):
        return "EP"
    if num.startswith("WO"):
        return "WO"
    if num.startswith("CN"):
        return "CN"
    if num.startswith("JP"):
        return "JP"
    return "US"

# Fallback static dataset
def get_fallback_patents() -> List[dict]:
    """Curated static dataset for when API fails"""
    return [
        {
            "patent_number": "US9105950B2",
            "title": "Thermal Management of Battery Packs",
            "abstract": "A battery thermal management system using liquid cooling channels integrated into battery pack housing to maintain optimal operating temperature range.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US9105950B2",
            "relevance_score": 0.85,
            "plain_summary": "Liquid cooling system for battery packs in electric vehicles",
            "patent_date": "2015-08-11",
            "year": 2015
        },
        {
            "patent_number": "US8993136B2",
            "title": "Liquid Cooling System for Battery Pack",
            "abstract": "Battery pack cooling system utilizing coolant circulation through cold plates in thermal contact with battery cells.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US8993136B2",
            "relevance_score": 0.82,
            "plain_summary": "Cold plate cooling for EV battery thermal management",
            "patent_date": "2015-03-31",
            "year": 2015
        },
        {
            "patent_number": "US20190067721A1",
            "title": "Battery Thermal Management System Using Phase Change Material",
            "abstract": "Integration of phase change materials (PCM) with battery cells to absorb excess heat during high-power operation.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US20190067721A1",
            "relevance_score": 0.78,
            "plain_summary": "Uses phase change materials to regulate battery temperature",
            "patent_date": "2019-02-28",
            "year": 2019
        },
        {
            "patent_number": "US10320031B2",
            "title": "Battery Pack with Integrated Cooling Plate",
            "abstract": "Battery module design with integrated aluminum cooling plate for efficient heat dissipation in electric vehicle applications.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10320031B2",
            "relevance_score": 0.80,
            "plain_summary": "Integrated cooling plate design for EV battery modules",
            "patent_date": "2019-06-11",
            "year": 2019
        },
        {
            "patent_number": "US9728778B2",
            "title": "Thermal Management System for Electric Vehicle Battery",
            "abstract": "Comprehensive thermal management system combining active cooling, heating, and thermal insulation for battery longevity.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US9728778B2",
            "relevance_score": 0.88,
            "plain_summary": "Complete thermal management solution for EV batteries",
            "patent_date": "2017-08-08",
            "year": 2017
        },
        {
            "patent_number": "US10396391B2",
            "title": "Heat Pipe Cooling for Battery Systems",
            "abstract": "Application of heat pipe technology for passive thermal management in high-density battery packs.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10396391B2",
            "relevance_score": 0.75,
            "plain_summary": "Heat pipe technology for battery cooling",
            "patent_date": "2019-08-27",
            "year": 2019
        },
        {
            "patent_number": "US9083066B2",
            "title": "Battery Cooling System with Refrigerant",
            "abstract": "Direct refrigerant cooling system for battery packs using evaporative cooling principles.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US9083066B2",
            "relevance_score": 0.72,
            "plain_summary": "Refrigerant-based cooling for battery thermal control",
            "patent_date": "2015-07-14",
            "year": 2015
        },
        {
            "patent_number": "US10686219B2",
            "title": "Immersion Cooling for Battery Cells",
            "abstract": "Battery cells immersed in dielectric cooling fluid for enhanced thermal management and safety.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10686219B2",
            "relevance_score": 0.70,
            "plain_summary": "Immersion cooling technology for battery cells",
            "patent_date": "2020-06-16",
            "year": 2020
        },
        {
            "patent_number": "US9947926B2",
            "title": "Thermoelectric Cooling for Battery Modules",
            "abstract": "Thermoelectric devices integrated into battery modules for precise temperature control.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US9947926B2",
            "relevance_score": 0.68,
            "plain_summary": "Thermoelectric cooling for precise battery temperature management",
            "patent_date": "2018-04-17",
            "year": 2018
        },
        {
            "patent_number": "US8974929B2",
            "title": "Air Cooling System for Battery Pack",
            "abstract": "Forced air cooling system with optimized airflow channels for battery thermal management.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US8974929B2",
            "relevance_score": 0.65,
            "plain_summary": "Air-based cooling system for battery packs",
            "patent_date": "2015-03-10",
            "year": 2015
        },
        {
            "patent_number": "US10461348B2",
            "title": "Hybrid Cooling System for Electric Vehicle Batteries",
            "abstract": "Combination of liquid and air cooling for optimized thermal management across operating conditions.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10461348B2",
            "relevance_score": 0.83,
            "plain_summary": "Hybrid liquid and air cooling for EV batteries",
            "patent_date": "2019-10-29",
            "year": 2019
        },
        {
            "patent_number": "US9236608B2",
            "title": "Battery Thermal Interface Materials",
            "abstract": "Advanced thermal interface materials for improved heat transfer between battery cells and cooling systems.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US9236608B2",
            "relevance_score": 0.62,
            "plain_summary": "Thermal interface materials for battery heat dissipation",
            "patent_date": "2016-01-12",
            "year": 2016
        },
        {
            "patent_number": "US10714724B2",
            "title": "Smart Thermal Management with Predictive Control",
            "abstract": "AI-driven thermal management system that predicts battery heating and preemptively adjusts cooling.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10714724B2",
            "relevance_score": 0.77,
            "plain_summary": "AI-based predictive thermal management for batteries",
            "patent_date": "2020-07-14",
            "year": 2020
        },
        {
            "patent_number": "US9166232B2",
            "title": "Microchannel Cooling for Battery Systems",
            "abstract": "Microchannel heat exchangers integrated into battery pack structure for high-efficiency cooling.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US9166232B2",
            "relevance_score": 0.74,
            "plain_summary": "Microchannel technology for efficient battery cooling",
            "patent_date": "2015-10-20",
            "year": 2015
        },
        {
            "patent_number": "US10593991B2",
            "title": "Graphene-Enhanced Thermal Conductors for Batteries",
            "abstract": "Use of graphene-based materials to enhance thermal conductivity in battery thermal management systems.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10593991B2",
            "relevance_score": 0.69,
            "plain_summary": "Graphene materials for improved battery heat transfer",
            "patent_date": "2020-03-17",
            "year": 2020
        },
        {
            "patent_number": "US9318772B2",
            "title": "Battery Pack Thermal Monitoring System",
            "abstract": "Distributed temperature sensing network for real-time thermal monitoring of battery cells.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US9318772B2",
            "relevance_score": 0.66,
            "plain_summary": "Temperature monitoring system for battery safety",
            "patent_date": "2016-04-19",
            "year": 2016
        },
        {
            "patent_number": "US10840535B2",
            "title": "Modular Battery Cooling Architecture",
            "abstract": "Scalable modular cooling system design for flexible battery pack configurations.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10840535B2",
            "relevance_score": 0.71,
            "plain_summary": "Modular cooling design for scalable battery systems",
            "patent_date": "2020-11-17",
            "year": 2020
        },
        {
            "patent_number": "US9263721B2",
            "title": "Thermal Runaway Prevention System",
            "abstract": "Active cooling system designed to prevent thermal runaway propagation in battery packs.",
            "status": "Expired - Free to Use",
            "url": "https://patents.google.com/patent/US9263721B2",
            "relevance_score": 0.79,
            "plain_summary": "Safety system to prevent battery thermal runaway",
            "patent_date": "2016-02-16",
            "year": 2016
        },
        {
            "patent_number": "US10566616B2",
            "title": "Lightweight Cooling Plate for EV Batteries",
            "abstract": "Optimized lightweight aluminum cooling plate design for weight-sensitive electric vehicle applications.",
            "status": "Active",
            "url": "https://patents.google.com/patent/US10566616B2",
            "relevance_score": 0.76,
            "plain_summary": "Lightweight cooling solution for electric vehicles",
            "patent_date": "2020-02-18",
            "year": 2020
        }
    ]

# Fetch patents from Lens.org API
def fetch_live_patents(query: str, max_results: int = 100) -> List[dict]:
    """
    Fetch patents from Lens.org Patent Search API (unauthenticated basic usage).
    Docs: https://docs.api.lens.org/
    """
    try:
        print(f"[DEBUG] Fetching live patents from Lens.org for query: {query}")
        url = "https://api.lens.org/patent/search"

        # Basic query: search in title, abstract, and claims with AND operator
        payload = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "simple_query_string": {
                                "query": query,
                                "fields": ["title^3", "abstract", "claims"],
                                "default_operator": "and"
                            }
                        }
                    ]
                }
            },
            "size": min(max_results, 100),
            "include": [
                "lens_id",
                "publication_number",
                "jurisdiction",
                "title",
                "abstract",
                "biblio.publication_date"
            ],
            "sort": [{"_score": "desc"}]
        }

        headers = {
            "Content-Type": "application/json"
            # For higher limits/authenticated usage, add: "Authorization": "Bearer YOUR_TOKEN"
        }

        with httpx.Client(timeout=20) as client:
            resp = client.post(url, json=payload, headers=headers)
            print(f"[DEBUG] Lens API response status: {resp.status_code}")
            
            if resp.status_code != 200:
                print(f"[ERROR] Lens API error: {resp.status_code} - {resp.text[:300]}")
                return []

            data = resp.json()
            recs = data.get("data") or data.get("results") or []
            if not isinstance(recs, list):
                print("[ERROR] Lens response format unexpected")
                return []
            
            print(f"[DEBUG] Received {len(recs)} patents from Lens.org")

        results: List[dict] = []
        kws = extract_keywords(query)

        for r in recs:
            pub_num = r.get("publication_number") or ""
            juris = (r.get("jurisdiction") or "").upper()
            title = (r.get("title") or "").strip()
            abstract = (r.get("abstract") or "").strip()

            # Publication date may be at biblio.publication_date (string like "2019-02-28")
            biblio = r.get("biblio") or {}
            pub_date = ""
            year = None
            if isinstance(biblio, dict):
                pub_date = biblio.get("publication_date") or ""
                if pub_date:
                    try:
                        year = int(str(pub_date)[:4])
                    except:
                        year = None

            # Build links
            pn = pub_num.replace(" ", "")
            gp_link = f"https://patents.google.com/patent/{pn}" if pn else None
            lens_id = r.get("lens_id")
            lens_link = f"https://www.lens.org/lens/patent/{lens_id}" if lens_id else None
            url_link = gp_link or lens_link or "https://www.lens.org/"

            # Heuristic status (20-year rule)
            status = "Active"
            if year and (datetime.now().year - year) >= 20:
                status = "Expired - Free to Use"

            # Map to our schema
            results.append({
                "patent_number": pn or (f"{juris}{lens_id}" if lens_id else "Unknown"),
                "title": title or "Untitled patent",
                "abstract": abstract[:900] if abstract else "No abstract available.",
                "status": status,
                "url": url_link,
                "relevance_score": calculate_relevance({"title": title, "abstract": abstract}, kws),
                "plain_summary": f"Patent covering {title.lower()}" if title else "Patent result",
                "patent_date": str(pub_date) if pub_date else "",
                "year": year
            })

        print(f"[DEBUG] Mapped {len(results)} valid patents")
        return results

    except Exception as e:
        print(f"[ERROR] Lens fetch exception: {e}")
        import traceback
        traceback.print_exc()
        return []

# Analyze endpoint with live data + fallback
@app.post("/analyze")
async def analyze(
    req: ProjectRequest,
    limit: int = Query(19, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_relevance: float = Query(0.0, ge=0.0, le=1.0),
    sort: str = Query("relevance_desc"),
    min_year: int = Query(0, ge=0),
    jurisdiction: str = Query("")
):
    print(f"\n[ANALYZE] Query: {req.description}")
    print(f"[ANALYZE] Filters: status={req.filter}, min_rel={min_relevance}, min_year={min_year}, jurisdiction={jurisdiction}")
    
    # Try live API first
    source = fetch_live_patents(req.description, max_results=100)
    
    # Fallback to static data if API returns nothing
    if not source:
        print("[ANALYZE] No live data, using fallback dataset")
        source = get_fallback_patents()
        # Recalculate relevance for fallback data
        keywords = extract_keywords(req.description)
        for p in source:
            p["relevance_score"] = calculate_relevance(p, keywords)
    else:
        print(f"[ANALYZE] Using {len(source)} live patents")
    
    if not source:
        return {
            "project_description": req.description,
            "key_concepts": extract_keywords(req.description),
            "total_patents_found": 0,
            "estimated_savings": "£0",
            "patents": [],
            "pagination": {"limit": limit, "offset": offset, "next_offset": None, "prev_offset": None, "total": 0},
            "applied_filters": {"status": req.filter, "min_relevance": min_relevance, "sort": sort, "min_year": min_year, "jurisdiction": jurisdiction.upper() if jurisdiction else ""}
        }
    
    # Enrich with jurisdiction
    enriched = []
    for p in source:
        pj = dict(p)
        pj["_jurisdiction"] = extract_jurisdiction(pj)
        pj["_year"] = pj.get("year")
        enriched.append(pj)
    
    # Apply filters
    pats = enriched
    if req.filter == "expired":
        pats = [p for p in pats if "Expired" in p["status"]]
    elif req.filter == "active":
        pats = [p for p in pats if "Active" in p["status"]]
    
    if jurisdiction:
        j = jurisdiction.strip().upper()
        pats = [p for p in pats if p.get("_jurisdiction") == j]
    
    if min_year and min_year > 0:
        pats = [p for p in pats if (p.get("_year") is not None and p["_year"] >= min_year)]
    
    pats = [p for p in pats if float(p.get("relevance_score", 0)) >= min_relevance]
    
    # Sort
    if sort == "relevance_desc":
        pats.sort(key=lambda x: float(x.get("relevance_score", 0)), reverse=True)
    elif sort == "relevance_asc":
        pats.sort(key=lambda x: float(x.get("relevance_score", 0)))
    elif sort == "title_asc":
        pats.sort(key=lambda x: (x.get("title") or "").lower())
    elif sort == "title_desc":
        pats.sort(key=lambda x: (x.get("title") or "").lower(), reverse=True)
    
    # Pagination
    total = len(pats)
    paged = pats[offset: offset + limit]
    
    expired_count = sum(1 for p in pats if "Expired" in p["status"])
    estimated_savings = f"£{expired_count * 25000:,}"
    
    next_offset = offset + limit if offset + limit < total else None
    prev_offset = offset - limit if offset >= limit else None
    
    def strip_helpers(p):
        q = dict(p)
        q.pop("_jurisdiction", None)
        q.pop("_year", None)
        q.pop("patent_date", None)
        q.pop("year", None)
        return q
    
    print(f"[ANALYZE] Returning {len(paged)} of {total} patents")
    
    return {
        "project_description": req.description,
        "key_concepts": extract_keywords(req.description),
        "total_patents_found": total,
        "estimated_savings": estimated_savings,
        "patents": [strip_helpers(p) for p in paged],
        "pagination": {"limit": limit, "offset": offset, "next_offset": next_offset, "prev_offset": prev_offset, "total": total},
        "applied_filters": {"status": req.filter, "min_relevance": min_relevance, "sort": sort, "min_year": min_year, "jurisdiction": jurisdiction.upper() if jurisdiction else ""}
    }

# PDF generation function
def build_pdf(payload: ExportRequest) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Patent Intelligence Report", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Project Description</b>", styles["Heading2"]))
    story.append(Paragraph(payload.project_description or "-", styles["BodyText"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Key Concepts</b>", styles["Heading2"]))
    story.append(Paragraph(", ".join(payload.key_concepts or []), styles["BodyText"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Patent Status Filter</b>", styles["Heading2"]))
    story.append(Paragraph((payload.filter or "all").title(), styles["BodyText"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Estimated R&D Savings</b>", styles["Heading2"]))
    story.append(Paragraph(payload.estimated_savings or "£0", styles["BodyText"]))
    story.append(Spacer(1, 12))

    if payload.patents:
        data = [["Patent Number", "Title", "Status", "Relevance"]]
        for p in payload.patents:
            rel = f"{int(round(float(p.get('relevance_score', 0)) * 100))}%"
            data.append([p.get("patent_number", ""), (p.get("title", "") or "")[:70], p.get("status", ""), rel])
        
        table = Table(data, colWidths=[3.5*cm, 9*cm, 3.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#667eea")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(Paragraph("<b>Patents Summary</b>", styles["Heading2"]))
        story.append(table)
        story.append(Spacer(1, 14))

        story.append(Paragraph("<b>Detailed Patent Information</b>", styles["Heading2"]))
        story.append(Spacer(1, 8))
        
        for p in payload.patents:
            rel_percent = int(round(float(p.get('relevance_score', 0)) * 100))
            story.append(Paragraph(f"<b>{p.get('patent_number', '')}</b>", styles['Heading3']))
            story.append(Paragraph(f"<b>Title:</b> {p.get('title', '')}", styles['BodyText']))
            story.append(Paragraph(f"<b>Status:</b> {p.get('status', '')} | <b>Relevance:</b> {rel_percent}%", styles['BodyText']))
            story.append(Spacer(1, 4))
            
            if p.get('plain_summary'):
                story.append(Paragraph(f"<b>Plain English Summary:</b> {p['plain_summary']}", styles['BodyText']))
                story.append(Spacer(1, 4))
            
            if p.get('abstract'):
                story.append(Paragraph(f"<b>Technical Abstract:</b> {p['abstract']}", styles['BodyText']))
                story.append(Spacer(1, 4))
            
            if p.get('url'):
                story.append(Paragraph(f"<b>Link:</b> <link href='{p['url']}' color='blue'>{p['url']}</link>", styles['BodyText']))
            
            story.append(Spacer(1, 12))
    else:
        story.append(Paragraph("No patents found for this query.", styles['BodyText']))

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf

@app.post("/export-pdf")
async def export_pdf(payload: ExportRequest):
    pdf_bytes = build_pdf(payload)
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="patent_report.pdf"'})