from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import requests
from embeddings import generate_embedding
from db_client import supabase, cosine_similarity
from config import SUPABASE_API_KEY, SUPABASE_API_URL

app = FastAPI()

class QueryRequest(BaseModel):
    query: Optional[str] = None
    match_count: int = 10
    filters: Optional[Dict[str, str]] = None  # e.g. {"series": "eq.Series A"}

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

        # Case 1: Only filters, no query
        if not req.query:
            response = requests.get(
                base_url,
                headers=headers,
                params={**params, "limit": str(req.match_count)}
            )
            response.raise_for_status()
            results = response.json()

        # Case 2 & 3: Semantic query (with or without filters)
        else:
            # Step 1: Generate embedding for the query
            embedding = generate_embedding(req.query)

            # Step 2: Semantic search via Supabase RPC
            match_result = supabase.rpc("match_companies_by_embedding", {
                "query_embedding": embedding,
                "match_count": 100  # large enough pool to filter from
            }).execute()

            uuids = [r["company_uuid"] for r in match_result.data]
            if not uuids:
                return []

            # Step 3: Apply filters to semantically matched UUIDs
            uuid_filter = ",".join(sorted(set(uuids)))
            params["company_uuid"] = f"in.({uuid_filter})"

            response = requests.get(
                base_url,
                headers=headers,
                params={**params}
            )
            response.raise_for_status()
            results = response.json()

            # Step 4: Re-rank by cosine similarity (if embeddings available)
            def compute_similarity(item):
                company_embedding = item.get("embedding")
                if company_embedding:
                    return cosine_similarity(embedding, company_embedding)
                else:
                    return -1  # fallback for missing vectors

            for item in results:
                item["similarity"] = compute_similarity(item)

            results = sorted(results, key=lambda x: x["similarity"], reverse=True)

        # Step 5: Deduplicate and limit to match_count
        seen = set()
        unique_results = []
        for item in results:
            cid = item.get("company_uuid")
            if cid not in seen:
                seen.add(cid)
                item.pop("similarity", None)
                item.pop("embedding", None)
                item.pop("company_uuid", None)
                item.pop("deal_uuid", None)
                unique_results.append(item)
            if len(unique_results) >= req.match_count:
                break

        return unique_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
