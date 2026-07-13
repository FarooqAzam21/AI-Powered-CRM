import json
import logging
from sqlalchemy.orm import Session
from models.ai_memory import CustomerMemory
from models.crm import Contact
from ai.prompts.prompt_manager import get_prompt_manager
from ai.parser.json_parser import ResponseParser

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manages persistent AI memory for customers.
    Automatically updates memory based on new interactions.
    """

    async def update_memory(self, db: Session, contact_id: int, interaction_text: str):
        """
        Analyze an interaction and update the CustomerMemory.
        """
        # Import inside to avoid circular dependencies
        from ai.services.ai_engine import get_ai_engine
        
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            logger.warning(f"Contact {contact_id} not found, skipping memory update.")
            return

        memory = db.query(CustomerMemory).filter(CustomerMemory.contact_id == contact_id).first()
        if not memory:
            memory = CustomerMemory(contact_id=contact_id)
            db.add(memory)
            db.flush()

        ai_engine = get_ai_engine()
        
        pm = get_prompt_manager()
        prompt = pm.render("memory_extraction", memory=memory, interaction_text=interaction_text)

        try:
            updates = await ResponseParser.parse_with_retry(
                llm_callable=ai_engine.provider.generate,
                initial_prompt=prompt,
                fallback_response={}
            )

            if not updates:
                logger.warning(f"No memory updates extracted for contact {contact_id}")
                return

            if "communication_style" in updates and updates["communication_style"]:
                memory.communication_style = str(updates["communication_style"])
            if "pain_points" in updates and isinstance(updates["pain_points"], list):
                memory.pain_points = json.dumps(updates["pain_points"])
            if "products_discussed" in updates and isinstance(updates["products_discussed"], list):
                memory.products_discussed = json.dumps(updates["products_discussed"])
            if "objections" in updates and isinstance(updates["objections"], list):
                memory.objections = json.dumps(updates["objections"])
            if "buying_signals" in updates and isinstance(updates["buying_signals"], list):
                memory.buying_signals = json.dumps(updates["buying_signals"])
            if "preferences" in updates and isinstance(updates["preferences"], list):
                memory.preferences = json.dumps(updates["preferences"])

            db.commit()
            logger.info(f"Successfully updated memory for contact {contact_id}")

        except Exception as e:
            logger.error(f"Failed to update memory for contact {contact_id}: {e}")
            db.rollback()


_manager = None

def get_memory_manager() -> MemoryManager:
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager
