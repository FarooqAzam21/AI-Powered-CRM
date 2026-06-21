"""
Contact Relationship Service - Phase 6
Tracks relationships between contacts via email interactions
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from auth.models import ContactRelationship, Contact, Email, User
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class RelationshipService:
    """Service for tracking relationships between contacts"""
    
    RELATIONSHIP_TYPES = ["mentions", "cc'd_with", "replied_to", "forwarded_to"]
    
    @staticmethod
    def link_contacts(db: Session, user_id: int, from_contact_id: int, 
                     to_contact_id: int, relationship_type: str = "mentions") -> ContactRelationship:
        """Create or update relationship between contacts"""
        try:
            # Check if relationship exists
            relationship = db.query(ContactRelationship).filter(
                and_(
                    ContactRelationship.user_id == user_id,
                    ContactRelationship.from_contact_id == from_contact_id,
                    ContactRelationship.to_contact_id == to_contact_id
                )
            ).first()
            
            if relationship:
                # Update existing relationship
                relationship.email_count += 1
                relationship.last_interaction = datetime.utcnow()
                relationship.strength = min(100, relationship.strength + 5)
            else:
                # Create new relationship
                relationship = ContactRelationship(
                    user_id=user_id,
                    from_contact_id=from_contact_id,
                    to_contact_id=to_contact_id,
                    relationship_type=relationship_type,
                    email_count=1,
                    last_interaction=datetime.utcnow(),
                    strength=10
                )
            
            db.add(relationship)
            db.commit()
            db.refresh(relationship)
            
            logger.debug(f"🔗 Linked contacts: {from_contact_id} → {to_contact_id}")
            return relationship
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Link contacts failed: {e}")
            raise
    
    @staticmethod
    def extract_relationships_from_email(db: Session, user_id: int, email: Email) -> int:
        """
        Extract relationships from email recipients and CC'd contacts
        Returns count of relationships created
        """
        try:
            count = 0
            
            # Get or create sender contact
            sender_contact = None
            if email.sender:
                sender_contact = db.query(Contact).filter(
                    and_(
                        Contact.user_id == user_id,
                        Contact.email == email.sender
                    )
                ).first()
            
            if not sender_contact or not email.contact_id:
                return count
            
            # Link sender to main contact
            RelationshipService.link_contacts(
                db, user_id, sender_contact.id, email.contact_id, "email_sent"
            )
            count += 1
            
            # Parse CC and BCC if available (would need email headers)
            # This is a placeholder for when full email headers are available
            
            return count
            
        except Exception as e:
            logger.error(f"❌ Email relationship extraction failed: {e}")
            return 0
    
    @staticmethod
    def get_contact_relationships(db: Session, contact_id: int, 
                                 limit: int = 20) -> List[Dict]:
        """
        Get all relationships for a contact
        Returns list of connected contacts with relationship details
        """
        try:
            relationships = db.query(ContactRelationship).filter(
                or_(
                    ContactRelationship.from_contact_id == contact_id,
                    ContactRelationship.to_contact_id == contact_id
                )
            ).order_by(desc(ContactRelationship.strength)).limit(limit).all()
            
            result = []
            for rel in relationships:
                # Get the other contact
                other_contact_id = (
                    rel.to_contact_id if rel.from_contact_id == contact_id 
                    else rel.from_contact_id
                )
                
                other_contact = db.query(Contact).filter(
                    Contact.id == other_contact_id
                ).first()
                
                if other_contact:
                    result.append({
                        "id": rel.id,
                        "contact_id": other_contact_id,
                        "contact_email": other_contact.email,
                        "contact_name": other_contact.name,
                        "contact_company": other_contact.company,
                        "relationship_type": rel.relationship_type,
                        "strength": rel.strength,
                        "email_count": rel.email_count,
                        "last_interaction": rel.last_interaction,
                        "inferred_role": rel.inferred_role
                    })
            
            logger.debug(f"📊 Found {len(result)} relationships for contact {contact_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Relationships retrieval failed: {e}")
            return []
    
    @staticmethod
    def build_relationship_graph(db: Session, user_id: int) -> Dict:
        """
        Build relationship graph for all user contacts
        Returns nodes and edges for visualization
        """
        try:
            contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
            relationships = db.query(ContactRelationship).filter(
                ContactRelationship.user_id == user_id
            ).all()
            
            # Build nodes
            nodes = []
            for contact in contacts:
                nodes.append({
                    "id": contact.id,
                    "label": contact.name or contact.email,
                    "email": contact.email,
                    "company": contact.company,
                    "size": min(30, 10 + contact.interaction_count),  # Size by interactions
                    "color": "green" if contact.score > 50 else "orange" if contact.score > 20 else "gray"
                })
            
            # Build edges
            edges = []
            for rel in relationships:
                edges.append({
                    "from": rel.from_contact_id,
                    "to": rel.to_contact_id,
                    "weight": min(10, rel.strength / 10),
                    "label": f"{rel.email_count} emails",
                    "type": rel.relationship_type
                })
            
            graph = {
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_contacts": len(nodes),
                    "total_connections": len(edges),
                    "avg_connections_per_contact": len(edges) / len(nodes) if nodes else 0
                }
            }
            
            logger.info(f"📊 Graph: {len(nodes)} contacts, {len(edges)} connections")
            return graph
            
        except Exception as e:
            logger.error(f"❌ Graph building failed: {e}")
            return {"nodes": [], "edges": [], "stats": {}}
    
    @staticmethod
    def identify_key_influencers(db: Session, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Identify key influencers (most connected contacts)
        """
        try:
            # Get contacts with their relationship counts
            contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
            
            influencer_scores = []
            for contact in contacts:
                # Count relationships
                relationship_count = db.query(ContactRelationship).filter(
                    or_(
                        ContactRelationship.from_contact_id == contact.id,
                        ContactRelationship.to_contact_id == contact.id
                    )
                ).count()
                
                # Calculate influence score
                score = (relationship_count * 30) + (contact.interaction_count * 10) + contact.score
                
                influencer_scores.append({
                    "contact_id": contact.id,
                    "email": contact.email,
                    "name": contact.name,
                    "company": contact.company,
                    "title": contact.title,
                    "connections": relationship_count,
                    "interactions": contact.interaction_count,
                    "score": contact.score,
                    "influence_score": score
                })
            
            # Sort by influence score
            influencers = sorted(influencer_scores, key=lambda x: x["influence_score"], reverse=True)[:limit]
            
            logger.info(f"⭐ Identified {len(influencers)} key influencers")
            return influencers
            
        except Exception as e:
            logger.error(f"❌ Influencer identification failed: {e}")
            return []
    
    @staticmethod
    def get_connection_path(db: Session, from_contact_id: int, 
                           to_contact_id: int, max_depth: int = 3) -> Optional[List[int]]:
        """
        Find shortest connection path between two contacts
        Useful for identifying shared contacts or introduction chains
        """
        try:
            from collections import deque
            
            # BFS to find shortest path
            queue = deque([(from_contact_id, [from_contact_id])])
            visited = {from_contact_id}
            
            while queue:
                current, path = queue.popleft()
                
                if current == to_contact_id:
                    return path
                
                if len(path) >= max_depth:
                    continue
                
                # Get connected contacts
                relationships = db.query(ContactRelationship).filter(
                    or_(
                        ContactRelationship.from_contact_id == current,
                        ContactRelationship.to_contact_id == current
                    )
                ).all()
                
                for rel in relationships:
                    next_contact = (
                        rel.to_contact_id if rel.from_contact_id == current 
                        else rel.from_contact_id
                    )
                    
                    if next_contact not in visited:
                        visited.add(next_contact)
                        queue.append((next_contact, path + [next_contact]))
            
            return None  # No path found
            
        except Exception as e:
            logger.error(f"❌ Path finding failed: {e}")
            return None
    
    @staticmethod
    def get_company_relationships(db: Session, user_id: int, 
                                 company: str) -> Dict:
        """
        Get all contacts and relationships at a specific company
        """
        try:
            company_contacts = db.query(Contact).filter(
                and_(
                    Contact.user_id == user_id,
                    Contact.company == company
                )
            ).all()
            
            # Build relationship map within company
            internal_relationships = []
            for contact in company_contacts:
                relationships = db.query(ContactRelationship).filter(
                    or_(
                        ContactRelationship.from_contact_id == contact.id,
                        ContactRelationship.to_contact_id == contact.id
                    )
                ).all()
                
                for rel in relationships:
                    other_id = (
                        rel.to_contact_id if rel.from_contact_id == contact.id 
                        else rel.from_contact_id
                    )
                    
                    # Check if other contact is in same company
                    other_contact = db.query(Contact).filter(Contact.id == other_id).first()
                    if other_contact and other_contact.company == company:
                        internal_relationships.append({
                            "from": contact.email,
                            "to": other_contact.email,
                            "strength": rel.strength
                        })
            
            result = {
                "company": company,
                "total_contacts": len(company_contacts),
                "contacts": [
                    {
                        "email": c.email,
                        "name": c.name,
                        "title": c.title,
                        "interactions": c.interaction_count
                    }
                    for c in company_contacts
                ],
                "internal_relationships": internal_relationships
            }
            
            logger.debug(f"🏢 Company map: {len(company_contacts)} contacts at {company}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Company relationships retrieval failed: {e}")
            return {}
