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
    
    def _create_legal_prompt(self, query: str, contexts: List[Dict[str, Any]], section_filter: Optional[List[str]] = None) -> str:
        """
        Create section-aware legal prompt

        Groups contexts by section for better structure
        """
        # Group contexts by section
        sections_dict = {}
        for ctx in contexts:
            section = ctx['metadata'].get('section', 'general')
            if section not in sections_dict:
                sections_dict[section] = []
            sections_dict[section].append(ctx)

        # Build context text organized by section
        context_text = ""

        # If specific sections were requested, show those first
        if section_filter:
            for section in section_filter:
                if section in sections_dict:
                    context_text += f"\n--- {section.upper().replace('_', ' ')} ---\n"
                    for i, ctx in enumerate(sections_dict[section], 1):
                        filename = ctx['metadata'].get('filename', 'Unknown')
                        content = ctx.get('content', '')
                        context_text += f"\nSource {i} (from {filename}):\n{content}\n"

        # Add remaining sections
        for section, ctxs in sections_dict.items():
            if section_filter and section in section_filter:
                continue  # Already added above

            context_text += f"\n--- {section.upper().replace('_', ' ')} ---\n"
            for i, ctx in enumerate(ctxs, 1):
                filename = ctx['metadata'].get('filename', 'Unknown')
                content = ctx.get('content', '')
                context_text += f"\nSource {i} (from {filename}):\n{content}\n"

        # Create structured prompt
        if section_filter:
            section_names = ', '.join([s.replace('_', ' ').title() for s in section_filter])
            prompt = f"""Legal Query: {query}
Focusing on: {section_names}

Relevant Legal Documents:
{context_text}

Based on the above legal documents from the specified sections, provide a concise and accurate answer. Reference specific sources and sections when making legal points.

Answer:"""
        else:
            prompt = f"""Legal Query: {query}

Relevant Legal Documents:
{context_text}

Based on the above legal documents, provide a concise and accurate answer. Reference specific sources and sections when making legal points.

Answer:"""
        return prompt

    async def query(
        self,
        query: str,
        section_filters: Optional[List[str]] = None,
        top_k: int = 5,
        multi_section: bool = False
    ) -> Dict[str, Any]:
        """
        Query the RAG system with section-aware filtering

        Args:
            query: User query
            section_filters: List of sections to filter (e.g., ['facts', 'prayers'])
            top_k: Number of results to retrieve
            multi_section: If True, retrieves from each section separately

        Returns:
            Dictionary with answer and sources
        """
        if not self.is_initialized or not self.model:
            raise RuntimeError("RAG system not initialized")

        all_contexts = []

        if multi_section and section_filters:
            # Retrieve top results from EACH section
            for section in section_filters:
                filter_dict = {"section": {"$in": [section]}}
                section_contexts = await self.vector_db.similarity_search(
                    query=query,
                    top_k=max(2, top_k // len(section_filters)),  # Distribute top_k across sections
                    filters=filter_dict
                )
                all_contexts.extend(section_contexts)
        else:
            # Standard retrieval with optional section filter
            filter_dict = {"section": {"$in": section_filters}} if section_filters else None
            all_contexts = await self.vector_db.similarity_search(
                query=query,
                top_k=top_k,
                filters=filter_dict
            )

        # Filter by similarity threshold
        filtered_contexts = [
            ctx for ctx in all_contexts
            if ctx.get('similarity_score', 0) >= self.config.SIMILARITY_THRESHOLD
        ]

        if not filtered_contexts:
            filtered_contexts = all_contexts[:3]

        # Create section-aware prompt
        prompt = self._create_legal_prompt(query, filtered_contexts, section_filters)

        # Generate response
        try:
            response = self.model.generate_content(prompt)
            answer = response.text
        except Exception as e:
            logger.error(f"Error generating response from Gemini: {e}")
            answer = "Could not generate an answer."

        # Prepare sources with enhanced metadata
        sources = [
            {
                'filename': ctx['metadata'].get('filename', 'Unknown'),
                'section': ctx['metadata'].get('section', 'general'),
                'section_header': ctx['metadata'].get('section_header', ''),
                'preview': ctx['content'][:300] + "..." if len(ctx['content']) > 300 else ctx['content'],
                'similarity_score': round(ctx.get('similarity_score', 0), 3),
                'id': ctx.get('id')
            } for ctx in filtered_contexts
        ]

        return {
            'answer': answer,
            'sources': sources,
            'sections_searched': section_filters or ['all']
        }

    # Backward compatibility alias
    async def query_legacy(self, query: str, filters: Optional[List[str]] = None, top_k: int = 5) -> Dict[str, Any]:
        """Legacy query method for backward compatibility"""
        return await self.query(query, section_filters=filters, top_k=top_k)