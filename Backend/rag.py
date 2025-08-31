"""
RAG (Retrieval-Augmented Generation) system for legal judgments
"""
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import logging
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG system combining retrieval and generation for legal queries"""
    
    def __init__(self, config, vector_db):
        self.config = config
        self.vector_db = vector_db
        self.tokenizer = None
        self.model = None
        self.generator = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the language model for generation"""
        try:
            logger.info(f"Loading language model: {self.config.LLM_MODEL}")
            
            # Use a lighter model for local deployment
            model_name = "microsoft/DialoGPT-medium"  # Lighter alternative
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Add padding token if it doesn't exist
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with appropriate settings for local deployment
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                low_cpu_mem_usage=True
            )
            
            # Create text generation pipeline
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            logger.info("Language model initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing language model: {e}")
            # Fallback to a simpler approach if model loading fails
            logger.warning("Using fallback text generation")
            self.generator = None
    
    def _create_legal_prompt(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        """Create a structured prompt for legal reasoning"""
        
        # Build context from retrieved documents
        context_text = ""
        for i, ctx in enumerate(contexts, 1):
            filename = ctx['metadata'].get('filename', 'Unknown')
            section = ctx['metadata'].get('section', 'general')
            preview = ctx['preview']
            
            context_text += f"\n**Source {i}** (from {filename}, {section} section):\n{preview}\n"
        
        # Create the prompt
        prompt = f"""You are a legal research assistant. Based on the provided legal documents, answer the following query with accurate legal reasoning.

**Query:** {query}

**Relevant Legal Documents:**
{context_text}

**Instructions:**
- Provide a clear, well-reasoned answer based on the legal precedents shown above
- Reference specific sources when making legal points
- If the available information is insufficient, clearly state what additional information would be needed
- Use proper legal terminology and structure your response logically

**Answer:**"""

        return prompt
    
    def _generate_fallback_response(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        """Generate a fallback response when LLM is not available"""
        
        if not contexts:
            return "No relevant legal precedents found in the database for your query. Please try refining your search terms or ensure relevant judgments have been uploaded."
        
        # Create a structured response from the retrieved contexts
        response = f"Based on the search through legal judgments, here are the most relevant precedents for your query:\n\n"
        
        for i, ctx in enumerate(contexts, 1):
            filename = ctx['metadata'].get('filename', 'Unknown Document')
            section = ctx['metadata'].get('section', 'general')
            similarity = ctx.get('similarity_score', 0)
            
            response += f"**{i}. {filename}** (Similarity: {similarity:.2f})\n"
            response += f"Section: {section.title()}\n"
            response += f"Excerpt: {ctx['preview']}\n\n"
        
        response += "**Legal Analysis:**\n"
        response += "The above precedents suggest relevant legal principles. For detailed legal advice, please consult with a qualified legal professional and review the full judgment texts."
        
        return response
    
    async def query(self, query: str, filters: Optional[List[str]] = None, top_k: int = 5) -> Dict[str, Any]:
        """
        Main RAG query function
        """
        try:
            logger.info(f"Processing RAG query: {query[:100]}...")
            
            # Build filter dictionary
            filter_dict = None
            if filters:
                filter_dict = {"section": filters}
            
            # Retrieve relevant documents
            contexts = await self.vector_db.similarity_search(
                query=query,
                top_k=top_k,
                filters=filter_dict
            )
            
            # Filter by similarity threshold
            filtered_contexts = [
                ctx for ctx in contexts 
                if ctx.get('similarity_score', 0) >= self.config.SIMILARITY_THRESHOLD
            ]
            
            if not filtered_contexts:
                logger.warning("No contexts above similarity threshold found")
                # Use all contexts if none meet threshold
                filtered_contexts = contexts[:3] if contexts else []
            
            # Generate response
            if self.generator and filtered_contexts:
                try:
                    answer = await self._generate_with_llm(query, filtered_contexts)
                except Exception as e:
                    logger.error(f"LLM generation failed: {e}")
                    answer = self._generate_fallback_response(query, filtered_contexts)
            else:
                answer = self._generate_fallback_response(query, filtered_contexts)
            
            # Prepare sources for response
            sources = []
            for ctx in filtered_contexts:
                source = {
                    'filename': ctx['metadata'].get('filename', 'Unknown'),
                    'section': ctx['metadata'].get('section', 'general'),
                    'preview': ctx['preview'],
                    'similarity_score': ctx.get('similarity_score', 0),
                    'metadata': ctx['metadata']
                }
                sources.append(source)
            
            return {
                'answer': answer,
                'sources': sources,
                'query': query,
                'total_sources': len(sources)
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return {
                'answer': f"An error occurred while processing your query: {str(e)}",
                'sources': [],
                'query': query,
                'total_sources': 0
            }
    
    async def _generate_with_llm(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        """Generate answer using the language model"""
        try:
            prompt = self._create_legal_prompt(query, contexts)
            
            # Generate response
            response = self.generator(
                prompt,
                max_new_tokens=self.config.MAX_NEW_TOKENS,
                temperature=self.config.TEMPERATURE,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                truncation=True
            )
            
            # Extract generated text
            generated_text = response[0]['generated_text']
            
            # Extract only the answer part (after "**Answer:**")
            if "**Answer:**" in generated_text:
                answer = generated_text.split("**Answer:**")[-1].strip()
            else:
                answer = generated_text[len(prompt):].strip()
            
            # Clean up the response
            answer = self._clean_generated_text(answer)
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating with LLM: {e}")
            raise
    
    def _clean_generated_text(self, text: str) -> str:
        """Clean and format generated text"""
        # Remove repetitive patterns
        text = re.sub(r'(.+?)\1{2,}', r'\1', text)
        
        # Remove incomplete sentences at the end
        sentences = text.split('. ')
        if len(sentences) > 1 and not sentences[-1].strip().endswith(('.', '!', '?')):
            text = '. '.join(sentences[:-1]) + '.'
        
        # Limit length
        max_length = self.config.MAX_NEW_TOKENS * 4  # Approximate character limit
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '...'
        
        return text.strip()
    
    async def analyze_legal_concepts(self, query: str) -> Dict[str, Any]:
        """Analyze and extract legal concepts from the query"""
        try:
            # Legal concept patterns
            legal_patterns = {
                'statutes': [
                    r'Section \d+',
                    r'Article \d+',
                    r'Rule \d+',
                    r'\b\w+\s+Act\b',
                    r'\b\w+\s+Code\b'
                ],
                'case_citations': [
                    r'\d{4}\s+\w+\s+\d+',
                    r'AIR\s+\d{4}',
                    r'SCC\s+\d{4}'
                ],
                'legal_terms': [
                    r'habeas corpus',
                    r'mandamus',
                    r'certiorari',
                    r'res judicata',
                    r'natural justice',
                    r'due process'
                ]
            }
            
            concepts = {}
            for category, patterns in legal_patterns.items():
                found_concepts = []
                for pattern in patterns:
                    matches = re.findall(pattern, query, re.IGNORECASE)
                    found_concepts.extend(matches)
                
                if found_concepts:
                    concepts[category] = list(set(found_concepts))
            
            return concepts
            
        except Exception as e:
            logger.error(f"Error analyzing legal concepts: {e}")
            return {}
    
    async def get_similar_cases(self, case_facts: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Find similar cases based on factual similarity"""
        try:
            # Search specifically in facts sections
            similar_cases = await self.vector_db.similarity_search(
                query=case_facts,
                top_k=top_k,
                filters={"section": ["facts", "general"]}
            )
            
            return similar_cases
            
        except Exception as e:
            logger.error(f"Error finding similar cases: {e}")
            return []