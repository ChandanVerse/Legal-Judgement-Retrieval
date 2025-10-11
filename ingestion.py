"""
PDF ingestion and text processing for legal judgments
"""
import pdfplumber
import re
from typing import List, Dict, Optional
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from section_detector import SectionDetector, Section

class JudgmentIngestor:
    """Handles PDF ingestion and text processing with section detection"""

    def __init__(self, config):
        self.config = config
        self.section_detector = SectionDetector()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if not text.strip():
            raise ValueError(f"No text extracted from {pdf_path}")
        
        return text
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        # Remove special characters but keep legal symbols
        text = re.sub(r'[^\w\s.,;:!?()\[\]{}\'"\-/]', ' ', text)
        # Normalize whitespace again
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def create_chunks_with_sections(self, text: str, filename: str) -> List[Document]:
        """
        Create chunks with section detection and enhanced metadata

        This is the new section-aware chunking method
        """
        documents = []

        # Detect sections in the document
        sections = self.section_detector.detect_with_fallback(text)

        print(f"  Detected {len(sections)} sections:")
        section_stats = self.section_detector.get_section_stats(sections)
        for section_type, count in section_stats.items():
            print(f"    - {section_type}: {count}")

        # Process each section separately
        for section in sections:
            section_content = self.section_detector.extract_section_content(text, section)

            if not section_content.strip():
                continue

            # Split section into chunks if it's too large
            section_chunks = self.text_splitter.split_text(section_content)

            # Create documents with enhanced metadata
            for i, chunk in enumerate(section_chunks):
                if not chunk.strip():
                    continue

                metadata = {
                    'filename': filename,
                    'section': section.section_type,
                    'section_confidence': round(section.confidence, 2),
                    'section_header': section.header_text,
                    'chunk_index': i,
                    'total_chunks_in_section': len(section_chunks),
                }

                documents.append(Document(
                    page_content=chunk,
                    metadata=metadata
                ))

        return documents

    def create_chunks(self, text: str, filename: str) -> List[Document]:
        """
        Legacy method for backward compatibility
        Creates chunks WITHOUT section detection
        """
        chunks = self.text_splitter.split_text(text)
        documents = []

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            metadata = {
                'filename': filename,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'section': 'general',  # Default section for legacy mode
            }

            documents.append(Document(
                page_content=chunk,
                metadata=metadata
            ))

        return documents
    
    def process_pdf(self, pdf_path: str, use_section_detection: bool = True) -> List[Document]:
        """
        Complete PDF processing pipeline

        Args:
            pdf_path: Path to PDF file
            use_section_detection: If True, uses section-aware chunking (recommended)

        Returns:
            List of Document objects with metadata
        """
        print(f"Processing: {pdf_path}")

        raw_text = self.extract_text_from_pdf(pdf_path)
        clean_text = self.preprocess_text(raw_text)

        filename = Path(pdf_path).name

        # Use section-aware chunking by default
        if use_section_detection:
            documents = self.create_chunks_with_sections(clean_text, filename)
        else:
            documents = self.create_chunks(clean_text, filename)

        print(f"Created {len(documents)} chunks for {filename}")
        return documents
    
    def process_directory(self, directory_path: str) -> List[Document]:
        """Process all PDFs in a directory"""
        directory = Path(directory_path)
        pdf_files = list(directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {directory_path}")
            return []
        
        print(f"Found {len(pdf_files)} PDF files")
        
        all_documents = []
        for pdf_file in pdf_files:
            try:
                documents = self.process_pdf(str(pdf_file))
                all_documents.extend(documents)
            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
        
        print(f"Total chunks created: {len(all_documents)}")
        return all_documents