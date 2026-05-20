import os

import httpx
from mcp.server.fastmcp import FastMCP

EZRAG_URL = os.environ.get("EZRAG_URL", "http://localhost:8000")

mcp = FastMCP("ezrag-search")


@mcp.tool()
def search(query: str) -> str:
    """
    Search the knowledge base using semantic similarity.
    Returns relevant text chunks from ingested documents.
    Use this to answer questions based on notes, documents, or any other ingested content.
    """
    try:
        resp = httpx.post(
            f"{EZRAG_URL}/retrieve",
            json={"query": query},
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.ConnectError:
        return "EzRag is not running. Start it with: docker compose up"
    except Exception as e:
        return f"Error querying knowledge base: {e}"

    chunks = resp.json().get("chunks", [])
    if not chunks:
        return "No relevant content found for that query."

    parts = []
    for chunk in chunks:
        header = f"**{chunk['filename']}** (score: {chunk['score']})"
        parts.append(f"{header}\n{chunk['text']}")

    return "\n\n---\n\n".join(parts)


if __name__ == "__main__":
    mcp.run()
