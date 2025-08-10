from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
import requests

from embeddings import generate_embedding
from db_client import supabase, cosine_similarity
from config import SUPABASE_API_KEY, SUPABASE_API_URL

app = FastAPI()

# --- Request Schema ---
class QueryRequest(BaseModel):
    query: Optional[str] = None
    match_count: int = 10
    filters: Optional[Dict[str, str]] = None
    order_by: Optional[Dict[str, str]] = None  # e.g., {"employees_growth_yoy": "desc.nullslast"}

# --- Helpers ---
def build_order_param(order_by: Optional[Dict[str, str]]) -> Optional[str]:
    if not order_by:
        return None

    parts = []
    for col, directive in order_by.items():
        # Normalize to lowercase and enforce "asc"/"desc" base
        base = directive.lower()
        if "desc" in base:
            direction = "desc.nullslast"
        else:
            direction = "asc.nullslast"
        parts.append(f"{col}.{direction}")
    return ",".join(parts)

def clean_result(items: List[dict], match_count: int) -> List[dict]:
    seen = set()
    cleaned = []
    for item in items:
        cid = item.get("company_uuid")
        if cid not in seen:
            seen.add(cid)
            for field in ["similarity", "embedding", "company_uuid", "deal_uuid"]:
                item.pop(field, None)
            cleaned.append(item)
        if len(cleaned) >= match_count:
            break
    return cleaned

@app.get("/")
def root():
    return {"status": "OK"}

@app.post("/enhanced-company-search")
def enhanced_company_search(req: QueryRequest):
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Accept": "application/json"
        }

        base_url = f"{SUPABASE_API_URL}/rest/v1/companies_funding"
        params = req.filters.copy() if req.filters else {}

        order_param = build_order_param(req.order_by)
        if order_param:
            params["order"] = order_param

        # --- Case 1: Structured filter only ---
        if not req.query:
            params["limit"] = str(req.match_count)
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            return clean_result(response.json(), req.match_count)

        # --- Case 2: Semantic query (with or without filters) ---
        embedding = generate_embedding(req.query)

        match_result = supabase.rpc("match_companies_by_embedding", {
            "query_embedding": embedding,
            "match_count": 100
        }).execute()

        uuids = [r["company_uuid"] for r in match_result.data]
        if not uuids:
            return []

        # Add semantic UUID filter
        params["company_uuid"] = f"in.({','.join(sorted(set(uuids)))})"
        params["limit"] = "100"  # fetch enough to filter/rank

        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        results = response.json()

        # --- Optional: re-rank by similarity if no explicit ordering ---
        if not req.order_by:
            for item in results:
                emb = item.get("embedding")
                item["similarity"] = cosine_similarity(embedding, emb) if emb else -1
            results.sort(key=lambda x: x["similarity"], reverse=True)

        return clean_result(results, req.match_count)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
