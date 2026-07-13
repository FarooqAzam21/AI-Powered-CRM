import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from auth.dependencies import get_current_user
from ai.rag.knowledge_base import get_knowledge_base
from ai.rag.document_parser import DocumentParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a company document to the knowledge base (RAG).
    Supports: .pdf, .docx, .csv, .txt, .md
    """
    try:
        content_bytes = await file.read()
        extracted_text = DocumentParser.parse_file(file.filename, content_bytes)

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file or file is empty.")

        kb = get_knowledge_base()
        
        metadata = {
            "filename": file.filename,
            "uploader_id": current_user.get("id"),
            "content_type": file.content_type
        }
        
        chunks_added = kb.add_document(extracted_text, metadata)

        if chunks_added == 0:
            raise HTTPException(status_code=500, detail="Failed to add document to Knowledge Base.")

        return {
            "status": "success",
            "message": f"Successfully indexed {chunks_added} chunks from {file.filename}."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/status")
async def kb_status(current_user: dict = Depends(get_current_user)):
    kb = get_knowledge_base()
    return {
        "status": "active" if kb.collection else "inactive",
        "message": "Knowledge Base is operational." if kb.collection else "ChromaDB not initialized."
    }
