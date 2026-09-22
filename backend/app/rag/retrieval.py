from typing import List, Dict, Any, Optional
from backend.app.rag.search import azure_search_client


def retrieve_grounded_context(
    query: str,
    top_k: int = 3,
    topic: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve bounded educational context to supply to the AI Gateway for grounded answering."""
    return azure_search_client.search_documents(query=query, top=top_k, topic=topic)
