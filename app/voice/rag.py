import logging
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

async def fetch_client_knowledge_base(client_id: str) -> str:
    """
    Fetches the custom knowledge base for a specific client from Supabase.
    This enables multi-tenant RAG in the Pipecat pipeline.
    """
    try:
        db = get_supabase()
        # Assume we have a 'knowledge_bases' table with columns 'client_id' and 'content'
        response = db.table("knowledge_bases").select("content").eq("client_id", client_id).execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"Successfully fetched knowledge base for client {client_id}")
            return response.data[0].get("content", "")
        
        logger.warning(f"No knowledge base found for client {client_id}")
        return ""
    except Exception as e:
        logger.error(f"Error fetching knowledge base for {client_id}: {str(e)}")
        return ""

def build_system_prompt(base_prompt: str, context: str) -> str:
    """
    Combines the base system prompt with the client-specific knowledge context.
    """
    if not context:
        return base_prompt
        
    return f"""{base_prompt}

You must strictly adhere to the following specific knowledge and rules for this business:
<business_knowledge>
{context}
</business_knowledge>
"""
