from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from typing import Annotated
from fastapi.middleware.cors import CORSMiddleware
import chromadb
import os

app = FastAPI()

collection_name = "zalgorithm"

chroma_host = os.getenv("CHROMA_HOST", "localhost")
chroma_port = os.getenv("CHROMA_PORT", "8000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1313", "https://zalgorithm.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/query", response_class=HTMLResponse)
async def query_collection(query: Annotated[str, Form()]):
    print("request received")
    print(query)
    try:
        chroma_client = await chromadb.AsyncHttpClient(
            host=chroma_host, port=int(chroma_port)
        )
        collection = await chroma_client.get_collection(name=collection_name)
        results = await collection.query(query_texts=[query], n_results=5)

        seen_sections = set()
        html_parts = []

        if not results["metadatas"]:
            return ""  # do better

        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            section_heading = metadata.get("section_heading", "")
            if section_heading in seen_sections:
                continue

            seen_sections.add(section_heading)

            heading = metadata.get("html_heading", "")
            fragment = metadata.get("html_fragment", "")
            html_parts.append(str(heading) + str(fragment))

        response_html = "".join(html_parts)
        return response_html

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
