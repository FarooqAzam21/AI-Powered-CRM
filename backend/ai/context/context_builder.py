from sqlalchemy.orm import Session
from models.crm import Contact, CustomerProfile, Lead, Interaction, Activity, Deal, Note
from models.ai_memory import CustomerMemory
from ai.rag.knowledge_base import get_knowledge_base
from ai.utils.sanitizer import PIISanitizer

class ContextBuilder:
    """
    Constructs a comprehensive, optimized context string for the AI Engine
    by aggregating data across multiple CRM tables.
    """

    def build_context(self, db: Session, contact_id: int, query: str = None) -> str:
        """
        Gathers CRM data and builds the context. Searches KB if query provided.
        """
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return "Context: Contact not found."

        context_parts = []

        # 1. Basic Info & Lead Score
        basic_info = f"Contact: {contact.name or 'Unknown'} ({contact.email})"
        if contact.company:
            basic_info += f" at {contact.company}"
        if contact.title:
            basic_info += f", {contact.title}"
            
        lead = db.query(Lead).filter(Lead.contact_id == contact_id).first()
        if lead:
            basic_info += f"\nLead Score: {lead.score} (Label: {lead.label})"
            basic_info += f"\nBuying Intent: {lead.buying_intent}, Urgency: {lead.urgency}"
        context_parts.append(f"### Contact Information\n{basic_info}")

        # 2. Customer Memory (AI Managed)
        memory = db.query(CustomerMemory).filter(CustomerMemory.contact_id == contact_id).first()
        if memory:
            mem_info = "### Customer AI Memory\n"
            if memory.communication_style:
                mem_info += f"- Communication Style: {memory.communication_style}\n"
            if memory.pain_points and memory.pain_points != "[]":
                mem_info += f"- Pain Points: {memory.pain_points}\n"
            if memory.buying_signals and memory.buying_signals != "[]":
                mem_info += f"- Buying Signals: {memory.buying_signals}\n"
            if memory.objections and memory.objections != "[]":
                mem_info += f"- Objections: {memory.objections}\n"
            if memory.products_discussed and memory.products_discussed != "[]":
                mem_info += f"- Products Discussed: {memory.products_discussed}\n"
            if memory.preferences and memory.preferences != "[]":
                mem_info += f"- Preferences: {memory.preferences}\n"
            context_parts.append(mem_info)
        else:
            # Fallback to Profile if Memory doesn't exist yet
            profile = db.query(CustomerProfile).filter(CustomerProfile.contact_id == contact_id).first()
            if profile:
                prof_info = "### Customer Profile\n"
                prof_info += f"- Persona: {profile.buyer_persona}\n"
                prof_info += f"- Pain Points: {profile.pain_points}\n"
                prof_info += f"- Interests: {profile.interests}\n"
                context_parts.append(prof_info)

        # 3. Recent Interactions
        interactions = (
            db.query(Interaction)
            .filter(Interaction.contact_id == contact_id)
            .order_by(Interaction.occurred_at.desc())
            .limit(5)
            .all()
        )
        if interactions:
            int_info = "### Recent Interactions\n"
            for ix in interactions:
                dir_arrow = "<-" if ix.direction == "inbound" else "->"
                int_info += f"[{ix.occurred_at.strftime('%Y-%m-%d')}] {dir_arrow} ({ix.channel}) {ix.subject}: {ix.snippet}\n"
            context_parts.append(int_info)

        # 4. Active Deals
        deals = (
            db.query(Deal)
            .filter(Deal.contact_id == contact_id, Deal.status == "open")
            .order_by(Deal.expected_close_at.asc())
            .limit(3)
            .all()
        )
        if deals:
            deal_info = "### Active Pipeline Deals\n"
            for d in deals:
                deal_info += f"- {d.title} (Stage: {d.stage}, Value: ${d.value}, Prob: {d.probability*100}%)\n"
            context_parts.append(deal_info)

        # 5. Recent Notes & Activities
        notes = db.query(Note).filter(Note.contact_id == contact_id).order_by(Note.created_at.desc()).limit(3).all()
        activities = db.query(Activity).filter(Activity.contact_id == contact_id).order_by(Activity.due_at.desc()).limit(3).all()
        
        if notes or activities:
            na_info = "### CRM Notes & Activities\n"
            for n in notes:
                na_info += f"Note ({n.created_at.strftime('%Y-%m-%d')}): {n.body}\n"
            for a in activities:
                due = a.due_at.strftime('%Y-%m-%d') if a.due_at else 'No date'
                na_info += f"Activity [{a.status}] due {due}: {a.title}\n"
            context_parts.append(na_info)

        # 6. Company Knowledge (Phase 3 - RAG)
        if query:
            kb = get_knowledge_base()
            relevant_chunks = kb.search(query, top_k=3)
            if relevant_chunks:
                kb_info = "### Company Knowledge\n"
                for i, chunk in enumerate(relevant_chunks):
                    kb_info += f"[Snippet {i+1}]: {chunk}\n\n"
                context_parts.append(kb_info)
            else:
                context_parts.append("### Company Knowledge\n(No relevant knowledge found for the query)")

        # Combine into final context string and sanitize PII
        final_context = "\n\n".join(context_parts)
        return PIISanitizer.sanitize(final_context)

_builder = None

def get_context_builder() -> ContextBuilder:
    global _builder
    if _builder is None:
        _builder = ContextBuilder()
    return _builder
