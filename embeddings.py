from config import OPENAI_API_KEY, SUPABASE_API_KEY,SUPABASE_API_URL
from supabase import create_client, Client
from openai import OpenAI
import pandas as pd

client = OpenAI()

supabase: Client = create_client(SUPABASE_API_URL,SUPABASE_API_KEY)

def build_embedding_text(row):
    parts = [
        f"Company: {row['name']}",
        f"Tagline: {row['tagline'] or ''}",
        f"Location: {row['location'] or ''}",
        f"Industry: {row['industry'] or ''}",
        f"Investors: {row['investors'] or ''}",
    ]
    return "\n".join([p for p in parts if p.strip()])

def fetch_all_companies_without_embeddings(batch_size=1000, max_rows=5000):
    all_rows = []
    for offset in range(0, max_rows, batch_size):
        response = supabase.table("companies")\
            .select("*")\
            .filter("embedding", "is", "null")\
            .range(offset, offset + batch_size - 1)\
            .execute()

        rows = response.data
        if not rows:
            break  # Exit early if no more results
        all_rows.extend(rows)

    return all_rows

def enhance_query_semantically(raw_query: str) -> str:
    """
    Reformulates the user's input to be clearer and more useful for embedding-based semantic search.
    """
    system_prompt = (
        "You are a helpful assistant that reformulates vague or casual user queries "
        "into precise, information-rich descriptions of climate or tech startups. "
        "Do not answer the query, just rewrite it for embedding search. "
        "Focus on domain, sector, region, and startup type if applicable."
    )
    
    user_prompt = f"User query: \"{raw_query}\""

    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
)
    return completion.choices[0].message.content


def generate_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=enhance_query_semantically(text)
    )
    return response.data[0].embedding

def update_embedding(company_id, embedding_vector):
    supabase.table("companies").update({
        "embedding": embedding_vector
    }).eq("id", company_id).execute()

def embed_batch():
    rows = fetch_all_companies_without_embeddings()
    for index, row in enumerate(rows):
        try:
            text = build_embedding_text(row)
            embedding = generate_embedding(text)
            update_embedding(row["id"], embedding)
            if index%20==0:
                print(f"processing {index}/{len(rows)}")
                print(f"✅ Embedded: {row['name']}")
        except Exception as e:
            print(f"❌ Error on {row['id']}: {e}")

def embed_companies(companies):
    text = build_embedding_text(companies)
    embedding = generate_embedding(text)
    return embedding
        


query = "Membrion, Seattle, WA, ceramic desalination membranes maker"
def create_embedding(query):
    query_embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding
    return query_embedding


# Find a way to also process the querry into something that is more manageable
def embedding_search(query_embedding, top_k=10):
    embedding_str = str(query_embedding)  # Converts list to PostgreSQL array syntax
    response = supabase.rpc(
        "match_companies_by_embedding",
        {"query_embedding": embedding_str, "match_count": top_k}
    ).execute()
    return response.data

def semantic_search(query,top_k):
    query_embedding = create_embedding(query)
    search_result = embedding_search(query_embedding,top_k)
    return search_result

# pd.DataFrame(search_companies_by_semantics(query_embedding,50))