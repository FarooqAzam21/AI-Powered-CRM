import os
import uuid
import logging
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from .document_parser import DocumentParser

logger = logging.getLogger(__name__)

class KnowledgeBase:
    """
    Manages the Vector Database (ChromaDB) for RAG context.
    """

    def __init__(self, persist_directory: str = "./data/chroma"):
        self.persist_directory = persist_directory
        self.collection_name = "crm_knowledge_base"
        self.client = None
        self.collection = None
        
        self._initialize_db()

    def _initialize_db(self):
        if not chromadb:
            logger.warning("ChromaDB is not installed. RAG will be disabled.")
            return

        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")

    def add_document(self, content: str, metadata: dict = None) -> int:
        """
        Chunks the document content and stores it in the vector DB.
        Returns the number of chunks added.
        """
        if not self.collection:
            logger.warning("ChromaDB not initialized, skipping add_document.")
            return 0

        chunks = DocumentParser.chunk_text(content)
        if not chunks:
            return 0

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [metadata or {} for _ in chunks]

        try:
            self.collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            return len(chunks)
        except Exception as e:
            logger.error(f"Failed to add document to ChromaDB: {e}")
            return 0

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """
        Searches the vector DB for the most relevant chunks.
        """
        if not self.collection:
            return []

        if not query.strip():
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            if results and results.get("documents") and results["documents"][0]:
                return results["documents"][0]
            return []
        except Exception as e:
            logger.error(f"Failed to search ChromaDB: {e}")
            return []


_kb = None

def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
