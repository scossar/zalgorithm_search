from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from typing import Annotated, Any
from fastapi.middleware.cors import CORSMiddleware
import chromadb

from chromadb.api.models.AsyncCollection import AsyncCollection
from chromadb.api import AsyncClientAPI
import os

import aiosqlite
from contextlib import asynccontextmanager


chroma_host = os.getenv("CHROMA_HOST", "localhost")
chroma_port = os.getenv("CHROMA_PORT", "8000")
db_path = os.getenv("SQLITE_DB_PATH", "/data/sections.db")


collection_name = "zalgorithm"
chroma_client: AsyncClientAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: create a single Chroma client for entire app lifetime
    global chroma_client
    chroma_client = await chromadb.AsyncHttpClient(
        host=chroma_host, port=int(chroma_port)
    )

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1313", "https://zalgorithm.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db_connection() -> aiosqlite.Connection | Any:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row

    try:
        yield db
    finally:
        await db.close()


async def get_chroma_collection() -> AsyncCollection:
    collection = await chroma_client.get_collection(name=collection_name)
    return collection


@app.post("/query", response_class=HTMLResponse)
async def query_collection(
    query: Annotated[str, Form()],
    db: aiosqlite.Connection = Depends(get_db_connection, scope="function"),
    collection: AsyncCollection = Depends(get_chroma_collection),
):
    try:
        results = await collection.query(query_texts=[query], n_results=5)
        seen_sections = set()
        html_sections = []

        if not results["metadatas"]:
            return ""  # for now

        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]

            section_heading = metadata.get("section_heading", "")
            if section_heading in seen_sections:
                continue

            seen_sections.add(section_heading)

            row_id = metadata.get("db_id", None)
            cursor = await db.execute(
                f"SELECT html_heading, html_fragment FROM sections WHERE id = {row_id}"
            )
            row = await cursor.fetchone()
            if row:
                section_html = "".join(row)
                html_sections.append(section_html)

        response_html = "".join(html_sections)
        return response_html

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fragment/{row_id}", response_class=HTMLResponse)
async def get_fragment(
    row_id, db: aiosqlite.Connection = Depends(get_db_connection, scope="function")
):
    cursor = await db.execute(
        f"SELECT html_heading, html_fragment FROM sections WHERE id = {row_id}"
    )
    row = await cursor.fetchone()
    if row:
        return f"{row[0]}{row[1]}"
    else:
        return "<p>Something went wrong</p>"
