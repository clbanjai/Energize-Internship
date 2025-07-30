from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
import os
import sys


from embeddings import generate_embedding

from db_client import supabase

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    match_count: int = 10


@app.get("/")
def root():
    return {"status": "OK"}

@app.post("/enhanced-company-search")
def enhanced_company_search(req: QueryRequest):
    try:
        embedding = generate_embedding(req.query)
        result = supabase.rpc("match_companies_by_embedding", {
            "query_embedding": embedding,
            "match_count": req.match_count
        }).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
