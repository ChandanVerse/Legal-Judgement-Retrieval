"""
PDF ingestion and text processing for legal judgments
"""
import pdfplumber
import re
from typing import List
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

class JudgmentIngestor:
    """Handles PDF ingestion and text processing"""
    
    def __init__(self, config):
        self.config = config
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
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[^\w\s.,;:!?()\[\]{}\'"\-/]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def create_chunks(self, text: str, filename: str) -> List[Document]:
        """Create chunks with metadata"""
        chunks = self.text_splitter.split_text(text)
        documents = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            metadata = {
                'filename': filename,
                'chunk_index': i,
                'total_chunks': len(chunks)
            }
            
            documents.append(Document(
                page_content=chunk,
                metadata=metadata
            ))
        
        return documents
    
    def process_pdf(self, pdf_path: str) -> List[Document]:
        """Complete PDF processing pipeline"""
        print(f"Processing: {pdf_path}")
        
        raw_text = self.extract_text_from_pdf(pdf_path)
        clean_text = self.preprocess_text(raw_text)
        
        filename = Path(pdf_path).name
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