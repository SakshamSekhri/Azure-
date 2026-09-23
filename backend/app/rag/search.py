import httpx
from typing import List, Dict, Any, Optional
from backend.app.config.settings import settings
from backend.app.core.logging import logger
from backend.app.rag.knowledge_base import EDUCATIONAL_DOCUMENTS


class AzureSearchClient:
    """Client for Azure AI Search with bounded retrieval.
    Falls back gracefully to local educational knowledge base if Azure Search is not configured.
    """

    def __init__(self):
        self.endpoint = settings.AZURE_AI_SEARCH_ENDPOINT.strip().rstrip("/")
        self.api_key = settings.AZURE_AI_SEARCH_KEY.strip()
        self.index_name = settings.AZURE_AI_SEARCH_INDEX

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.index_name)

    def search_documents(self, query: str, top: int = 3, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve bounded relevant educational documents."""
        if not self.is_configured():
            logger.info("Azure AI Search not configured. Searching local educational documents.")
            return self._local_search(query, top, topic)

        # Query Azure AI Search REST API
        url = f"{self.endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        body = {
            "search": query,
            "top": top,
            "queryType": "simple"
        }
        if topic:
            body["filter"] = f"topic eq '{topic}'"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                results = []
                for item in data.get("value", []):
                    results.append({
                        "id": item.get("id", "azure_doc"),
                        "title": item.get("title", "Azure Retrieved Doc"),
                        "topic": item.get("topic", "General"),
                        "skill": item.get("skill", ""),
                        "source": item.get("source", "Azure AI Search"),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")
                    })
                return results if results else self._local_search(query, top, topic)
        except Exception as e:
            logger.warning(f"Azure AI Search query failed ({e}). Falling back to local knowledge base.")
            return self._local_search(query, top, topic)

    def _local_search(self, query: str, top: int = 3, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Score local educational documents based on query terms."""
        terms = [t.lower() for t in query.split() if len(t) > 2]
        scored_docs = []

        for doc in EDUCATIONAL_DOCUMENTS:
            if topic and doc.get("topic", "").lower() != topic.lower():
                continue

            score = 0
            doc_text = f"{doc['title']} {doc['skill']} {doc['topic']} {doc['content']}".lower()

            for term in terms:
                if term in doc['title'].lower():
                    score += 5
                if term in doc['skill'].lower():
                    score += 4
                if term in doc_text:
                    score += 1

            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:top]]


azure_search_client = AzureSearchClient()
