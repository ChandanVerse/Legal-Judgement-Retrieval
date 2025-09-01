"""
PDF ingestion and text processing for legal judgments
"""
import pdfplumber
import re
from typing import List, Dict, Any
from pathlib import Path
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger(__name__)

class JudgmentIngestor:
    """Handles PDF ingestion and text processing for legal judgments"""
    
    def __init__(self, config):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=[
                "\n\n",  # Paragraph breaks
                "\n",    # Line breaks
                ". ",    # Sentence endings
                ", ",    # Clause separators
                " ",     # Word separators
                ""       # Character level
            ]
        )
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using pdfplumber
        """
        try:
            text = ""
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")
            
            logger.info(f"Extracted {len(text)} characters from {pdf_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess legal judgment text
        """
        if not text or not text.strip():
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page headers/footers common in legal documents
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'--- Page \d+ ---', '', text)
        
        # Clean up common legal document artifacts
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalize paragraph breaks
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Fix sentence spacing
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{3,}', '---', text)
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s.,;:!?()\[\]{}\'"\-/]', ' ', text)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def identify_sections(self, text: str) -> Dict[str, str]:
        """
        Attempt to identify legal document sections (facts, grounds, prayers, etc.)
        """
        sections = {}
        
        # Enhanced section patterns in legal judgments
        section_patterns = {
            'facts': [
                r'(?:BRIEF\s+)?FACTS?\s*(?:OF\s+THE\s+CASE)?\s*:?\s*\n',
                r'FACTUAL\s+BACKGROUND\s*:?\s*\n',
                r'BACKGROUND\s*:?\s*\n'
            ],
            'grounds': [
                r'GROUNDS?\s*(?:OF\s+APPEAL)?\s*:?\s*\n',
                r'LEGAL\s+GROUNDS?\s*:?\s*\n',
                r'CONTENTIONS?\s*:?\s*\n'
            ],
            'prayers': [
                r'PRAYERS?\s*(?:FOR\s+RELIEF)?\s*:?\s*\n',
                r'RELIEF\s+SOUGHT\s*:?\s*\n',
                r'PRAYERS?\s*:?\s*\n'
            ],
            'judgment': [
                r'JUDGMENT\s*(?:AND\s+ORDER)?\s*:?\s*\n',
                r'HELD\s*:?\s*\n',
                r'DECISION\s*:?\s*\n',
                r'ORDER\s*:?\s*\n'
            ],
            'ratio': [
                r'RATIO\s*(?:DECIDENDI)?\s*:?\s*\n',
                r'LEGAL\s+PRINCIPLE\s*:?\s*\n'
            ],
            'obiter': [
                r'OBITER\s*(?:DICTA)?\s*:?\s*\n',
                r'OBSERVATIONS?\s*:?\s*\n'
            ]
        }
        
        # Sort sections by their position in the text
        section_positions = []
        
        for section_type, patterns in section_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    section_positions.append((match.start(), section_type, match.end()))
                    break  # Use first matching pattern for each section
        
        # Sort by position
        section_positions.sort(key=lambda x: x[0])
        
        # Extract sections based on positions
        for i, (start_pos, section_type, content_start) in enumerate(section_positions):
            # Find the end position (start of next section or end of text)
            if i + 1 < len(section_positions):
                end_pos = section_positions[i + 1][0]
            else:
                end_pos = len(text)
            
            section_text = text[content_start:end_pos].strip()
            if section_text:
                sections[section_type] = section_text
        
        # If no sections found, treat entire text as general content
        if not sections:
            sections['general'] = text
        
        return sections
    
    def create_chunks_with_metadata(self, text: str, filename: str) -> List[Document]:
        """
        Create chunks with metadata for legal document
        """
        # Identify sections first
        sections = self.identify_sections(text)
        
        documents = []
        
        for section_type, section_text in sections.items():
            if not section_text.strip():
                continue
                
            # Split section into chunks
            chunks = self.text_splitter.split_text(section_text)
            
            for i, chunk in enumerate(chunks):
                if not chunk.strip():  # Skip empty chunks
                    continue
                
                metadata = {
                    'filename': filename,
                    'section': section_type,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'char_count': len(chunk)
                }
                
                # Add basic citation info if found
                citation_match = re.search(r'(\d{4})', chunk)
                if citation_match:
                    metadata['year'] = citation_match.group(1)
                
                # Add simple court info
                if re.search(r'Supreme Court', chunk, re.IGNORECASE):
                    metadata['court_type'] = 'supreme_court'
                elif re.search(r'High Court', chunk, re.IGNORECASE):
                    metadata['court_type'] = 'high_court'
                
                documents.append(Document(
                    page_content=chunk,
                    metadata=metadata
                ))
        
        return documents
    
    def process_pdf(self, pdf_path: str) -> List[Document]:
        """
        Complete PDF processing pipeline
        """
        try:
            logger.info(f"Processing PDF: {pdf_path}")
            
            # Validate PDF path
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Extract text
            raw_text = self.extract_text_from_pdf(pdf_path)
            
            if not raw_text.strip():
                raise ValueError(f"No text extracted from {pdf_path}")
            
            # Preprocess
            clean_text = self.preprocess_text(raw_text)
            
            if not clean_text.strip():
                raise ValueError(f"No usable text after preprocessing {pdf_path}")
            
            # Create chunks with metadata
            filename = Path(pdf_path).name
            documents = self.create_chunks_with_metadata(clean_text, filename)
            
            if not documents:
                raise ValueError(f"No chunks created from {pdf_path}")
            
            logger.info(f"Created {len(documents)} chunks for {filename}")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise
    
    def process_directory(self, directory_path: str) -> List[Document]:
        """
        Process all PDFs in a directory
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        all_documents = []
        pdf_files = list(directory.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory_path}")
            return all_documents
        
        logger.info(f"Found {len(pdf_files)} PDF files in {directory_path}")
        
        for pdf_file in pdf_files:
            try:
                documents = self.process_pdf(str(pdf_file))
                all_documents.extend(documents)
                logger.info(f"Successfully processed {pdf_file.name}")
            except Exception as e:
                logger.error(f"Skipping {pdf_file} due to error: {e}")
                continue
        
        logger.info(f"Processed {len(all_documents)} total chunks from {len(pdf_files)} files")
        return all_documents
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        Validate if PDF is readable and contains text using pdfplumber
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return False
                
                # Check if at least one page has text
                for page_num in range(min(3, len(pdf.pages))):  # Check first 3 pages
                    page = pdf.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text and page_text.strip():
                        return True
                
                return False
            
        except Exception as e:
            logger.error(f"Error validating PDF {pdf_path}: {e}")
            return False