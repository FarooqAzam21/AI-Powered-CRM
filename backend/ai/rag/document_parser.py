import os
import io
import logging
from typing import List
from PyPDF2 import PdfReader
import docx
import pandas as pd

logger = logging.getLogger(__name__)

class DocumentParser:
    """
    Parses various document types and extracts text into chunks.
    """

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Splits text into chunks of roughly `chunk_size` characters with `overlap`.
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            chunks.append(text[start:end])
            start += (chunk_size - overlap)
            
        return chunks

    @staticmethod
    def parse_pdf(file_content: bytes) -> str:
        text = ""
        try:
            reader = PdfReader(io.BytesIO(file_content))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
        return text

    @staticmethod
    def parse_docx(file_content: bytes) -> str:
        text = ""
        try:
            doc = docx.Document(io.BytesIO(file_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            logger.error(f"Failed to parse DOCX: {e}")
        return text

    @staticmethod
    def parse_csv(file_content: bytes) -> str:
        text = ""
        try:
            df = pd.read_csv(io.BytesIO(file_content))
            text = df.to_string(index=False)
        except Exception as e:
            logger.error(f"Failed to parse CSV: {e}")
        return text

    @classmethod
    def parse_file(cls, filename: str, file_content: bytes) -> str:
        """
        Parses a file based on its extension and returns extracted text.
        """
        ext = filename.split(".")[-1].lower()
        if ext == "pdf":
            return cls.parse_pdf(file_content)
        elif ext in ["doc", "docx"]:
            return cls.parse_docx(file_content)
        elif ext == "csv":
            return cls.parse_csv(file_content)
        elif ext in ["txt", "md"]:
            try:
                return file_content.decode("utf-8")
            except Exception as e:
                logger.error(f"Failed to decode text file: {e}")
                return ""
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return ""
