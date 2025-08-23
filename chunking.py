"""
Text chunking module for Legal Judgments Similarity Retrieval System.
Splits documents into smaller chunks using RecursiveCharacterTextSplitter for optimal embedding generation.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Optional
import config
import utils

# Set up logging
logger = utils.setup_logging()

class DocumentChunker:
    """
    Handles document chunking using LangChain's RecursiveCharacterTextSplitter.
    Splits large documents into manageable chunks while preserving context.
    """
    
    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        """
        Initialize the document chunker.
        
        Args:
            chunk_size: Size of each chunk in characters (uses config default if None)
            chunk_overlap: Overlap between chunks in characters (uses config default if None)
        """
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        
        # Initialize the text splitter with appropriate separators for legal documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            # Separators optimized for legal documents (paragraphs, sections, sentences)
            separators=[
                "\n\n\n",  # Multiple line breaks (major sections)
                "\n\n",    # Paragraph breaks
                "\n",      # Line breaks
                ".",       # Sentences
                "!",       # Exclamatory sentences
                "?",       # Questions
                ";",       # Semi-colons
                ",",       # Commas
                " ",       # Spaces
                ""         # Characters (fallback)
            ]
        )
        
        logger.info(f"Initialized chunker with chunk_size={self.chunk_size}, overlap={self.chunk_overlap}")
    
    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a single document into chunks.
        
        Args:
            document: Document dictionary with 'content' and 'metadata'
            
        Returns:
            List of chunk dictionaries with content and enhanced metadata
        """
        content = document.get('content', '')
        metadata = document.get('metadata', {})
        
        if not content.strip():
            logger.warning(f"Empty content for document: {metadata.get('filename', 'Unknown')}")
            return []
        
        try:
            # Split the text into chunks
            text_chunks = self.text_splitter.split_text(content)
            
            # Create chunk dictionaries with metadata
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                # Skip very small chunks that don't contain meaningful content
                if len(chunk_text.strip()) < 50:
                    continue
                
                # Create enhanced metadata for each chunk
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    'chunk_id': i,
                    'chunk_index': f"{metadata.get('filename', 'unknown')}_{i}",
                    'chunk_size': len(chunk_text),
                    'total_chunks': len(text_chunks)
                })
                
                chunk_dict = {
                    'content': chunk_text.strip(),
                    'metadata': chunk_metadata
                }
                
                chunks.append(chunk_dict)
            
            filename = metadata.get('filename', 'Unknown')
            logger.debug(f"Split {filename} into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking document {metadata.get('filename', 'Unknown')}: {str(e)}")
            return []
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Split multiple documents into chunks.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            List of all chunks from all documents
        """
        if not documents:
            logger.warning("No documents provided for chunking")
            return []
        
        all_chunks = []
        total_docs = len(documents)
        
        logger.info(f"Starting to chunk {total_docs} documents...")
        
        for doc_idx, document in enumerate(documents):
            filename = document.get('metadata', {}).get('filename', f'doc_{doc_idx}')
            
            try:
                # Chunk the current document
                doc_chunks = self.chunk_document(document)
                
                if doc_chunks:
                    all_chunks.extend(doc_chunks)
                    if config.SHOW_PROGRESS:
                        logger.info(f"Chunked {filename}: {len(doc_chunks)} chunks")
                else:
                    logger.warning(f"No chunks created for {filename}")
            
            except Exception as e:
                logger.error(f"Failed to chunk document {filename}: {str(e)}")
                continue
        
        logger.info(f"Created {len(all_chunks)} total chunks from {total_docs} documents")
        return all_chunks
    
    def get_chunk_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics about the chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {}
        
        chunk_sizes = [len(chunk['content']) for chunk in chunks]
        
        stats = {
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'total_characters': sum(chunk_sizes),
            'unique_documents': len(set(chunk['metadata']['filename'] for chunk in chunks))
        }
        
        logger.info(f"Chunk statistics: {stats}")
        return stats
    
    def preview_chunks(self, chunks: List[Dict[str, Any]], num_preview: int = 3) -> None:
        """
        Print preview of chunks for debugging and validation.
        
        Args:
            chunks: List of chunk dictionaries
            num_preview: Number of chunks to preview
        """
        if not chunks:
            logger.info("No chunks to preview")
            return
        
        logger.info(f"Previewing first {min(num_preview, len(chunks))} chunks:")
        utils.print_separator()
        
        for i, chunk in enumerate(chunks[:num_preview]):
            metadata = chunk['metadata']
            content_preview = utils.format_preview(chunk['content'], 150)
            
            print(f"Chunk {i+1}:")
            print(f"  File: {metadata.get('filename', 'Unknown')}")
            print(f"  Chunk ID: {metadata.get('chunk_id', 'N/A')}")
            print(f"  Size: {len(chunk['content'])} characters")
            print(f"  Preview: {content_preview}")
            print()
        
        utils.print_separator()