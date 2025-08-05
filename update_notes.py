import pandas as pd
from db_client import fetch_all
import asyncio
import aiohttp
from aiohttp import BasicAuth
from config import AFFINITY_API_KEY

from db_client import supabase

# Limit concurrent requests
semaphore = asyncio.Semaphore(10)

async def get_affinity_notes_by_org_id_async(
    session: aiohttp.ClientSession, organization_id: int, page_size: int = 500
) -> dict[int, str | None]:
    """
    Asynchronously retrieves all notes for a given organization ID and returns {org_id: concatenated_notes}.
    """
    url = "https://api.affinity.co/notes"
    headers = {"Content-Type": "application/json"}
    auth = BasicAuth('', AFFINITY_API_KEY)

    notes_list = []
    next_page_token = None

    async with semaphore:
        while True:
            params = {
                "organization_id": organization_id,
                "page_size": page_size
            }
            if next_page_token:
                params["page_token"] = next_page_token

            for attempt in range(5):
                async with session.get(url, headers=headers, auth=auth, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        notes = data.get("notes", [])
                        for note in notes:
                            notes_list.append(f"{note.get('created_at', '')}\n{note.get('content', '')}")
                        next_page_token = resp.headers.get("next_page_token")
                        break
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        print(f"[{organization_id}] Rate limited — retrying in {retry_after}s...")
                        await asyncio.sleep(retry_after)
                    elif resp.status >= 500:
                        print(f"[{organization_id}] Server error {resp.status} — retrying in 60s...")
                        await asyncio.sleep(60)
                    else:
                        print(f"[{organization_id}] Unrecoverable error {resp.status}")
                        return {organization_id: None}
            else:
                print(f"[{organization_id}] Max retries reached.")
                return {organization_id: None}

            if not next_page_token:
                break

    note_text = '\n'.join(notes_list)  # extra spacing between notes
    return {organization_id: note_text}


async def parallel_run(func, inputs):
    async with aiohttp.ClientSession() as session:
        tasks = [func(session, inp) for inp in inputs]
        results = await asyncio.gather(*tasks)

        # Merge individual {org_id: notes} dicts into one
        merged = {}
        for result in results:
            merged.update(result)
        return merged

def generate_notes_updates(df: pd.DataFrame, notes_by_id: dict[int, str | None]) -> list[dict]:
    """
    Compares existing notes from Supabase to new notes and returns update dicts where notes have changed.
    
    Args:
        df: DataFrame of companies, must include 'affinity_id', 'company_uuid', 'notes'.
        notes_by_id: Dict mapping affinity_id (int) -> new concatenated notes (str or None).
    
    Returns:
        List of updates: [{ "company_uuid": ..., "notes": ... }, ...]
    """
    updates = []
    for row in df.itertuples():
        try:
            affinity_id = int(row.affinity_id)
        except ValueError:
            continue

        new_note = notes_by_id.get(affinity_id)
        current_note = row.notes or ""

        if new_note is None:
            continue  # No new info
        if new_note.strip() != current_note.strip():
            updates.append({
                "company_uuid": row.company_uuid,
                "notes": new_note
            })
    print(f"Preparing to generate a total of {len(updates)} into the database")
    return updates


def update_notes_in_supabase(updates: list[dict]):
    """
    Pushes note updates to Supabase via upsert on company_uuid.
    """
    for update in updates:
        try:
            company_uuid = update["company_uuid"]
            update_fields = {k: v for k, v in update.items() if k != "company_uuid"}
            supabase.table("companies").update(update_fields).eq("company_uuid", company_uuid).execute()
        except Exception as e:
            print(f"Updating {company_uuid} with: {update_fields}")
            raise e


def main():
    companies = fetch_all()
    df = companies[companies["in_energize_affinity"] == True]
    org_ids = df["affinity_id"].astype(int).tolist()
    notes_dict = asyncio.run(parallel_run(get_affinity_notes_by_org_id_async, org_ids))    
    updates = generate_notes_updates(df,notes_dict)
    update_notes_in_supabase(updates)
    print("SUCCESSFULLY UPLOADED THE UPDATES")
    
if __name__ == "__main__":
    main()
