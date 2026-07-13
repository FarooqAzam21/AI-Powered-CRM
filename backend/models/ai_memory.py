from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from models.crm import TimestampMixin

class CustomerMemory(Base, TimestampMixin):
    __tablename__ = "crm_customer_memory"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("crm_contacts.id"), unique=True, index=True, nullable=False)
    
    communication_style = Column(String, default="")
    products_discussed = Column(Text, default="[]")
    pain_points = Column(Text, default="[]")
    meeting_history = Column(Text, default="")
    faq = Column(Text, default="{}")
    buying_signals = Column(Text, default="[]")
    objections = Column(Text, default="[]")
    previous_summaries = Column(Text, default="")
    preferences = Column(Text, default="[]")
    
    # Phase 6 Multi-Agent Extensions
    support_history = Column(Text, default="[]")
    campaign_history = Column(Text, default="[]")
    hiring_notes = Column(Text, default="[]")

    contact = relationship("models.crm.Contact", foreign_keys=[contact_id])
