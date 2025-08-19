from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List
import asyncio
from relationship import process_companies_parallel

app = FastAPI()

class InputText(BaseModel):
    text: str

@app.get("/")
def root():
    return {"status": "API running"}

@app.post("/process")
async def process(text_input: InputText):
    output_path = "output.csv"
    await process_companies_parallel(text_input.text, output_csv_path=output_path)
    return {"message": "Processing complete", "output_file": output_path}

