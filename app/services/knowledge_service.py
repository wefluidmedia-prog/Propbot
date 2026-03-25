"""
Knowledge base service.

Loads a client's markdown KB from Supabase and provides
search functionality for the lookup_property tool.
"""

from app.db.supabase_client import get_supabase


async def get_knowledge_base(client_id: str) -> str:
    """Load a client's full knowledge base from Supabase."""
    db = get_supabase()
    result = db.table("clients").select("knowledge_base").eq("id", client_id).single().execute()
    return result.data.get("knowledge_base", "")


async def search_knowledge_base(client_id: str, query: str) -> str:
    """
    Search a client's KB for relevant sections.

    Simple keyword matching — searches each section header and content
    for overlap with the query. Returns the most relevant sections.
    """
    kb = await get_knowledge_base(client_id)
    if not kb:
        return "Knowledge base not found for this client."

    query_lower = query.lower()
    sections = kb.split("\n## ")
    matches = []

    for section in sections:
        # Check if any query words appear in this section
        section_lower = section.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]
        score = sum(1 for word in query_words if word in section_lower)
        if score > 0:
            matches.append((score, section.strip()))

    if not matches:
        return "I don't have specific information about that in my listings. Let me connect you with the agent."

    # Return top 3 matches
    matches.sort(key=lambda x: x[0], reverse=True)
    results = [m[1] for m in matches[:3]]
    return "\n\n---\n\n".join(results)
