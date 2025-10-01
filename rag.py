"""
RAG (Retrieval-Augmented Generation) system for legal judgments
"""
import google.generativeai as genai
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG system combining retrieval and generation for legal queries"""
    
    def __init__(self, config: Any, vector_db: Any):
        self.config = config
        self.vector_db = vector_db
        self.model: Optional[genai.GenerativeModel] = None
        self.is_initialized = False

    async def initialize(self):
        try:
            logger.info("Initializing RAG system...")
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(self.config.LLM_MODEL)
            self.is_initialized = True
            logger.info("RAG system initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing RAG system: {e}")
            raise
    
    def _create_legal_prompt(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        context_text = ""
        for i, ctx in enumerate(contexts, 1):
            filename = ctx['metadata'].get('filename', 'Unknown')
            section = ctx['metadata'].get('section', 'general')
            content = ctx.get('content', '')
            context_text += f"\nSource {i} (from {filename}, {section} section):\n{content}\n"
        
        prompt = f"""Legal Query: {query}

Relevant Legal Documents:
{context_text}

Based on the above legal documents, provide a concise answer addressing the query. Reference specific sources when making legal points.

Answer:"""
        return prompt

    async def query(self, query: str, filters: Optional[List[str]] = None, top_k: int = 5) -> Dict[str, Any]:
        if not self.is_initialized or not self.model:
            raise RuntimeError("RAG system not initialized")
            
        filter_dict = {"section": {"$in": filters}} if filters else None
        
        contexts = await self.vector_db.similarity_search(
            query=query,
            top_k=top_k,
            filters=filter_dict
        )
        
        filtered_contexts = [
            ctx for ctx in contexts 
            if ctx.get('similarity_score', 0) >= self.config.SIMILARITY_THRESHOLD
        ]
        
        if not filtered_contexts:
            filtered_contexts = contexts[:3]
            
        prompt = self._create_legal_prompt(query, filtered_contexts)
        
        try:
            response = self.model.generate_content(prompt)
            answer = response.text
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {e}")
            answer = "Could not generate an answer."
            
        sources = [
            {
                'filename': ctx['metadata'].get('filename', 'Unknown'),
                'section': ctx['metadata'].get('section', 'general'),
                'preview': ctx['content'][:300] + "...",
                'similarity_score': round(ctx.get('similarity_score', 0), 3),
                'id': ctx.get('id')
            } for ctx in filtered_contexts
        ]
        
        return {'answer': answer, 'sources': sources}