"""
PDF ingestion and text processing for legal judgments
"""
import fitz  # PyMuPDF
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
        Extract text from PDF using PyMuPDF
        """
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            doc.close()
            logger.info(f"Extracted {len(text)} characters from {pdf_path}")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess legal judgment text
        """
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
        
        return text.strip()
    
    def identify_sections(self, text: str) -> Dict[str, str]:
        """
        Attempt to identify legal document sections (facts, grounds, prayers, etc.)
        """
        sections = {}
        
        # Common section patterns in legal judgments
        section_patterns = {
            'facts': [
                r'FACTS?\s*:?\s*\n',
                r'BRIEF\s+FACTS?\s*:?\s*\n',
                r'FACTUAL\s+BACKGROUND\s*:?\s*\n'
            ],
            'grounds': [
                r'GROUNDS?\s*:?\s*\n',
                r'LEGAL\s+GROUNDS?\s*:?\s*\n',
                r'GROUNDS?\s+OF\s+APPEAL\s*:?\s*\n'
            ],
            'prayers': [
                r'PRAYERS?\s*:?\s*\n',
                r'RELIEF\s+SOUGHT\s*:?\s*\n',
                r'PRAYERS?\s+FOR\s+RELIEF\s*:?\s*\n'
            ],
            'judgment': [
                r'JUDGMENT\s*:?\s*\n',
                r'HELD\s*:?\s*\n',
                r'DECISION\s*:?\s*\n'
            ]
        }
        
        for section_type, patterns in section_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    start_pos = match.end()
                    # Find the next section or end of document
                    next_section_pos = len(text)
                    for other_patterns in section_patterns.values():
                        for other_pattern in other_patterns:
                            next_match = re.search(other_pattern, text[start_pos:], re.IGNORECASE | re.MULTILINE)
                            if next_match:
                                next_section_pos = min(next_section_pos, start_pos + next_match.start())
                    
                    sections[section_type] = text[start_pos:next_section_pos].strip()
                    break
        
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
            if section_text.strip():
                # Split section into chunks
                chunks = self.text_splitter.split_text(section_text)
                
                for i, chunk in enumerate(chunks):
                    if chunk.strip():  # Skip empty chunks
                        metadata = {
                            'filename': filename,
                            'section': section_type,
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'char_count': len(chunk)
                        }
                        
                        # Add citation info if found
                        citation_match = re.search(r'(\d{4})\s+\w+\s+\d+', chunk)
                        if citation_match:
                            metadata['year'] = citation_match.group(1)
                        
                        # Add court info if found
                        court_patterns = [
                            r'Supreme Court',
                            r'High Court',
                            r'District Court',
                            r'Tribunal'
                        ]
                        for pattern in court_patterns:
                            if re.search(pattern, chunk, re.IGNORECASE):
                                metadata['court_type'] = pattern.lower().replace(' ', '_')
                                break
                        
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
            
            # Extract text
            raw_text = self.extract_text_from_pdf(pdf_path)
            
            # Preprocess
            clean_text = self.preprocess_text(raw_text)
            
            # Create chunks with metadata
            filename = Path(pdf_path).name
            documents = self.create_chunks_with_metadata(clean_text, filename)
            
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
        all_documents = []
        
        pdf_files = list(directory.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {directory_path}")
        
        for pdf_file in pdf_files:
            try:
                documents = self.process_pdf(str(pdf_file))
                all_documents.extend(documents)
            except Exception as e:
                logger.error(f"Skipping {pdf_file} due to error: {e}")
                continue
        
        logger.info(f"Processed {len(all_documents)} total chunks from {len(pdf_files)} files")
        return all_documents