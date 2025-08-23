"""
PDF ingestion module for Legal Judgments Similarity Retrieval System.
Handles loading PDF files from the data directory and extracting text content using PyMuPDF.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Tuple, Any
import config
import utils

# Set up logging
logger = utils.setup_logging()

class DocumentIngestion:
    """
    Handles document ingestion from PDF files.
    Extracts text content and maintains metadata for each document.
    """
    
    def __init__(self):
        """Initialize the document ingestion system."""
        self.data_dir = config.DATA_DIR
        self.supported_formats = config.SUPPORTED_FORMATS
    
    def _extract_page_text(self, page) -> str:
        """
        Extract text from a single PDF page with version compatibility.
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            Extracted text from the page
        """
        try:
            # Try modern PyMuPDF method first
            if hasattr(page, 'get_text'):
                return page.get_text()
            # Fallback to legacy method
            elif hasattr(page, 'getText'):
                return page.getText()
            # Final fallback
            else:
                logger.warning("No text extraction method found for PyMuPDF page")
                return ""
        except Exception as e:
            logger.warning(f"Error extracting text from page: {str(e)}")
            return ""
    
    def load_pdf_text(self, pdf_path: Path) -> str:
        """
        Extract text content from a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content as string
            
        Raises:
            Exception: If PDF cannot be processed
        """
        try:
            # Open PDF document
            doc = fitz.open(pdf_path)
            text_content = ""
            
            # Extract text from each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = self._extract_page_text(page)
                text_content += page_text + "\n"
            
            # Close document to free memory
            doc.close()
            
            # Clean up the extracted text
            text_content = self._clean_text(text_content)
            
            logger.debug(f"Extracted {len(text_content)} characters from {pdf_path.name}")
            return text_content
            
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {str(e)}")
            raise Exception(f"PDF processing error: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw text from PDF extraction
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace while preserving paragraph structure
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace from each line
            line = line.strip()
            if line:  # Only keep non-empty lines
                cleaned_lines.append(line)
        
        # Join lines with single newlines and normalize spaces
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Replace multiple spaces with single space
        import re
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        
        return cleaned_text
    
    def get_document_files(self) -> List[Path]:
        """
        Get list of all PDF files in the data directory.
        
        Returns:
            List of Path objects for PDF files
        """
        pdf_files = utils.get_file_list(self.data_dir, self.supported_formats)
        logger.info(f"Found {len(pdf_files)} PDF files in {self.data_dir}")
        return pdf_files
    
    def load_documents(self) -> List[Dict[str, Any]]:
        """
        Load all PDF documents from the data directory.
        
        Returns:
            List of dictionaries containing document text and metadata
            Format: [{'content': text, 'metadata': {'filename': name}}, ...]
        """
        pdf_files = self.get_document_files()
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.data_dir}")
            return []
        
        documents = []
        successful_loads = 0
        
        logger.info(f"Starting to process {len(pdf_files)} PDF files...")
        
        for pdf_file in pdf_files:
            try:
                # Check file size before processing
                if not utils.validate_file_size(pdf_file):
                    logger.warning(f"Skipping {pdf_file.name} - file too large (>{config.MAX_FILE_SIZE_MB}MB)")
                    continue
                
                # Extract text from PDF
                text_content = self.load_pdf_text(pdf_file)
                
                # Skip if no meaningful content extracted
                if len(text_content.strip()) < 100:
                    logger.warning(f"Skipping {pdf_file.name} - insufficient text content")
                    continue
                
                # Create document dictionary
                document: Dict[str, Any] = {
                    'content': text_content,
                    'metadata': {
                        'filename': utils.safe_filename(pdf_file.name),
                        'file_path': str(pdf_file),
                        'file_size': pdf_file.stat().st_size
                    }
                }
                
                documents.append(document)
                successful_loads += 1
                
                if config.SHOW_PROGRESS:
                    logger.info(f"Processed {pdf_file.name} ({len(text_content)} characters)")
            
            except Exception as e:
                logger.error(f"Failed to process {pdf_file.name}: {str(e)}")
                continue
        
        logger.info(f"Successfully loaded {successful_loads} out of {len(pdf_files)} PDF files")
        return documents
    
    def validate_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate loaded documents for quality and completeness.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            List of validated documents
        """
        valid_documents: List[Dict[str, Any]] = []
        
        for doc in documents:
            # Check if document has required fields
            if not doc.get('content') or not doc.get('metadata', {}).get('filename'):
                logger.warning("Skipping document with missing content or filename")
                continue
            
            # Check content length
            content_length = len(doc['content'].strip())
            if content_length < 50:  # Minimum meaningful content
                metadata = doc.get('metadata', {})
                filename = metadata.get('filename', 'Unknown') if isinstance(metadata, dict) else 'Unknown'
                logger.warning(f"Skipping document with insufficient content: {filename}")
                continue
            
            valid_documents.append(doc)
        
        logger.info(f"Validated {len(valid_documents)} documents")
        return valid_documents