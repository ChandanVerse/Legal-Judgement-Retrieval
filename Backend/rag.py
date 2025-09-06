"""
RAG (Retrieval-Augmented Generation) system for legal judgments
"""
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.pipelines import pipeline
import torch
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import re
import asyncio

logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG system combining retrieval and generation for legal queries"""
    
    def __init__(self, config: Any, vector_db: Any):
        """Initialize with better type validation"""
        required_attrs = ['LLM_MODEL', 'MAX_NEW_TOKENS', 'TEMPERATURE', 'SIMILARITY_THRESHOLD']
        missing = [attr for attr in required_attrs if not hasattr(config, attr)]
        if missing:
            raise ValueError(f"Config missing required attributes: {', '.join(missing)}")
            
        self.config = config
        self.vector_db = vector_db
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.generator: Optional[Any] = None
        self.is_initialized = False
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    async def initialize(self):
        """Initialize the language model for generation"""
        try:
            logger.info("Initializing RAG system...")
            await self._initialize_llm()
            self.is_initialized = True
            logger.info("RAG system initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing RAG system: {e}")
            logger.warning("RAG system will use fallback mode without LLM")
            self.is_initialized = True  # Allow system to work with fallback
    
    async def _initialize_llm(self):
        """Initialize the language model for generation"""
        try:
            logger.info(f"Loading language model: {self.config.LLM_MODEL}")
            
            # Run model loading in thread pool to avoid blocking
            def load_model():
                try:
                    tokenizer = AutoTokenizer.from_pretrained(self.config.LLM_MODEL)
                    
                    # Add padding token if it doesn't exist
                    if tokenizer.pad_token is None:
                        tokenizer.pad_token = tokenizer.eos_token
                    
                    # Load model with appropriate settings for local deployment
                    model = AutoModelForCausalLM.from_pretrained(
                        self.config.LLM_MODEL,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                        device_map="auto" if torch.cuda.is_available() else None,
                        low_cpu_mem_usage=True
                    )
                    
                    # Create text generation pipeline
                    generator = pipeline(
                        "text-generation",
                        model=model,
                        tokenizer=tokenizer,
                        device=0 if torch.cuda.is_available() else -1,
                        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                    )
                    
                    return tokenizer, model, generator
                    
                except Exception as e:
                    logger.error(f"Error in model loading thread: {e}")
                    return None, None, None
            
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            self.tokenizer, self.model, self.generator = await loop.run_in_executor(
                None, load_model
            )
            
            if self.generator:
                logger.info("Language model initialized successfully")
            else:
                logger.warning("Failed to initialize language model, using fallback")
            
        except Exception as e:
            logger.error(f"Error initializing language model: {e}")
            self.generator = None
    
    def _create_legal_prompt(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        """Create a structured prompt for legal reasoning"""
        
        # Build context from retrieved documents
        context_text = ""
        for i, ctx in enumerate(contexts, 1):
            filename = ctx['metadata'].get('filename', 'Unknown')
            section = ctx['metadata'].get('section', 'general')
            preview = ctx['preview']
            
            context_text += f"\nSource {i} (from {filename}, {section} section):\n{preview}\n"
        
        # Create the prompt
        prompt = f"""Legal Query: {query}

Relevant Legal Documents:
{context_text}

Based on the above legal documents, provide a concise answer addressing the query. Reference specific sources when making legal points.

Answer:"""

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
            
            response += f"{i}. **{filename}** (Relevance: {similarity:.1%})\n"
            response += f"   Section: {section.title()}\n"
            response += f"   Excerpt: {ctx['preview'][:150]}...\n\n"
        
        response += "**Legal Analysis:**\n"
        response += "The above precedents contain relevant legal principles for your query. "
        response += "For detailed legal advice, please consult with a qualified legal professional "
        response += "and review the full judgment texts."
        
        return response
    
    async def query(
        self,
        query: str,
        filters: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Main RAG query function with input validation
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        top_k = min(max(1, top_k), 100)  # Bound between 1 and 100

        try:
            if not self.is_initialized:
                raise RuntimeError("RAG system not initialized")
            
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
                # Use top 3 contexts if none meet threshold
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
                    'similarity_score': round(ctx.get('similarity_score', 0), 3),
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
    
    def _get_safe_token_id(self) -> int:
        """Safely get a token ID with proper type checking"""
        if not self.tokenizer:
            return 0
        
        # Cast tokenizer to Any to avoid type checking issues with dynamic attributes
        tokenizer: Any = self.tokenizer
        
        # Try different token IDs in order of preference
        token_candidates = [
            getattr(tokenizer, 'eos_token_id', None),
            getattr(tokenizer, 'pad_token_id', None),
            getattr(tokenizer, 'bos_token_id', None),
        ]
        
        for token_id in token_candidates:
            if token_id is not None:
                return int(token_id)
        
        return 0  # Final fallback
    
    async def _generate_with_llm(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        """Generate with proper null checks"""
        if not self.generator or not self.tokenizer:
            raise RuntimeError("LLM not properly initialized")
            
        try:
            prompt = self._create_legal_prompt(query, contexts)
            
            def generate():
                try:
                    with torch.inference_mode(), torch.cuda.amp.autocast(enabled=self._device=="cuda"):
                        generation_config = {
                            "max_new_tokens": min(self.config.MAX_NEW_TOKENS, 1000),
                            "temperature": min(max(0.1, self.config.TEMPERATURE), 1.0),
                            "do_sample": True,
                            "truncation": True,
                            "return_full_text": False,
                            "num_return_sequences": 1,
                            "pad_token_id": self._get_safe_token_id(),
                            "repetition_penalty": 1.2,
                            "no_repeat_ngram_size": 3,
                        }
                        
                        # Handle potential CUDA OOM with proper null checks
                        try:
                            if not self.generator:
                                raise RuntimeError("Generator not available")
                                
                            response = self.generator(prompt, **generation_config)
                            if not response or not isinstance(response, list):
                                raise ValueError("Invalid response format")
                            if not response[0].get('generated_text'):
                                raise ValueError("Empty response from generator")
                            return response[0]['generated_text']
                            
                        except RuntimeError as e:
                            if "out of memory" in str(e):
                                if torch.cuda.is_available():
                                    torch.cuda.empty_cache()
                                if not self.generator:
                                    raise RuntimeError("Generator not available after OOM")
                                logger.warning("CUDA OOM, attempting with reduced parameters")
                                generation_config["max_new_tokens"] //= 2
                                response = self.generator(prompt, **generation_config)
                                if not response or not isinstance(response, list):
                                    raise ValueError("Invalid response format after OOM recovery")
                                return response[0].get('generated_text')
                            raise
                            
                except Exception as e:
                    logger.error(f"Error in generation thread: {str(e)}")
                    return None

            loop = asyncio.get_event_loop()
            generated_text = await loop.run_in_executor(None, generate)
            
            if generated_text is None:
                raise RuntimeError("Text generation failed")
            
            return self._clean_generated_text(generated_text)
            
        except Exception as e:
            logger.error(f"Error generating with LLM: {str(e)}")
            raise
    
    def _clean_generated_text(self, text: str) -> str:
        """Clean and format generated text"""
        if not text:
            return "Unable to generate response."
        
        # Remove repetitive patterns
        text = re.sub(r'(.{10,}?)\1{2,}', r'\1', text)
        
        # Remove incomplete sentences at the end
        sentences = text.split('. ')
        if len(sentences) > 1 and sentences[-1] and not sentences[-1].strip().endswith(('.', '!', '?')):
            text = '. '.join(sentences[:-1]) + '.'
        
        # Clean up common artifacts
        text = re.sub(r'\n+', ' ', text)  # Replace newlines with spaces
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        # Limit length
        max_length = 1000  # Reasonable limit for responses
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