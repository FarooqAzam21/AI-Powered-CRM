"""
Context Window Manager - PHASE 5 OPTIMIZATION
Manages Ollama model context windows (2048 tokens for tinyllama)
Prevents context overflow, implements sliding window for long conversations
"""
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ContextWindowManager:
    """
    Manages context window for LLM calls
    - Tracks conversation history
    - Implements sliding window for long contexts
    - Optimizes token usage
    """
    
    def __init__(self, max_tokens: int = 2048, model: str = "tinyllama"):
        """
        Initialize context manager
        
        Args:
            max_tokens: Maximum context window size (2048 for tinyllama)
            model: Model name for logging
        """
        self.max_tokens = max_tokens
        self.model = model
        self.reserved_for_response = 256  # Reserve tokens for model response
        self.available_tokens = max_tokens - self.reserved_for_response
        self.conversation_history: List[Dict] = []
        logger.info(f"📊 Context Manager initialized: {model} ({max_tokens} tokens)")
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count
        Ollama/LLaMA: ~4 characters per token average
        """
        return len(text) // 4
    
    def _count_history_tokens(self) -> int:
        """Count tokens in conversation history"""
        total = 0
        for msg in self.conversation_history:
            total += self.estimate_tokens(msg.get("content", ""))
        return total
    
    def add_message(self, role: str, content: str) -> bool:
        """
        Add message to conversation history
        Implements sliding window if needed
        
        Returns:
            True if added, False if would exceed limit even alone
        """
        msg_tokens = self.estimate_tokens(content)
        
        if msg_tokens > self.available_tokens:
            logger.warning(f"⚠️  Message too long ({msg_tokens} > {self.available_tokens} tokens)")
            return False
        
        # Add message
        self.conversation_history.append({
            "role": role,
            "content": content,
            "tokens": msg_tokens,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Remove old messages if context overflow
        while self._count_history_tokens() > self.available_tokens:
            if len(self.conversation_history) > 1:
                removed = self.conversation_history.pop(0)
                logger.debug(f"🔄 Removed old message ({removed['tokens']} tokens)")
            else:
                break
        
        return True
    
    def get_context_prompt(self, system_prompt: str, new_query: str) -> str:
        """
        Build complete prompt within context limits
        
        Format:
        <SYSTEM>
        {system_prompt}
        </SYSTEM>
        
        <CONTEXT>
        {previous messages}
        </CONTEXT>
        
        <QUERY>
        {new_query}
        </QUERY>
        
        Returns:
            Complete prompt ready for model
        """
        system_tokens = self.estimate_tokens(system_prompt)
        query_tokens = self.estimate_tokens(new_query)
        context_available = self.available_tokens - system_tokens - query_tokens
        
        # Build context from history
        context_lines = []
        context_tokens = 0
        
        for msg in reversed(self.conversation_history):
            if context_tokens + msg["tokens"] <= context_available:
                role = msg["role"].upper()
                content = msg["content"]
                context_lines.append(f"[{role}]: {content}")
                context_tokens += msg["tokens"]
            else:
                break
        
        # Reverse to chronological order
        context_lines.reverse()
        context_text = "\n".join(context_lines) if context_lines else "[No previous context]"
        
        # Build final prompt
        prompt = f"""<SYSTEM>
{system_prompt}
</SYSTEM>

<CONTEXT>
{context_text}
</CONTEXT>

<QUERY>
{new_query}
</QUERY>

Please respond:"""
        
        logger.debug(f"📝 Context prompt built: {self.estimate_tokens(prompt)}/{self.max_tokens} tokens")
        
        return prompt
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.debug("🧹 Conversation history cleared")
    
    def get_stats(self) -> Dict:
        """Get context usage statistics"""
        total_tokens = self._count_history_tokens()
        
        return {
            "max_tokens": self.max_tokens,
            "reserved_for_response": self.reserved_for_response,
            "available_for_context": self.available_tokens,
            "used_tokens": total_tokens,
            "remaining_tokens": self.available_tokens - total_tokens,
            "usage_percent": round(100 * total_tokens / self.available_tokens, 1),
            "messages_in_history": len(self.conversation_history)
        }
    
    def should_clear_history(self) -> bool:
        """
        Determine if history should be cleared
        Returns True if usage > 80%
        """
        usage = self._count_history_tokens()
        threshold = self.available_tokens * 0.8
        return usage > threshold


class PromptOptimizer:
    """
    Optimize prompts for efficiency
    - Removes unnecessary words
    - Uses structured formats
    - Provides clear instructions
    """
    
    @staticmethod
    def optimize_classification_prompt(subject: str, body: str) -> str:
        """
        Optimize prompt for email classification
        Focuses model on key aspects
        """
        prompt = f"""Classify email.
Subject: {subject}
Body: {body[:500]}

Respond JSON: {{"category": "...", "confidence": 0.0, "action": "...", "priority": "..."}}"""
        
        return prompt
    
    @staticmethod
    def optimize_reply_prompt(email_body: str, tone: str) -> str:
        """
        Optimize prompt for reply generation
        """
        prompt = f"""Generate {tone} reply to:
{email_body[:500]}

Reply:"""
        
        return prompt
    
    @staticmethod
    def optimize_intent_prompt(text: str) -> str:
        """
        Optimize prompt for intent detection
        """
        prompt = f"""Detect intent in: {text[:300]}
Intent (hiring/buying/support/other):"""
        
        return prompt
    
    @staticmethod
    def optimize_sentiment_prompt(text: str) -> str:
        """
        Optimize prompt for sentiment analysis
        """
        prompt = f"""Sentiment of: {text[:300]}
(positive/neutral/negative):"""
        
        return prompt
    
    @staticmethod
    def optimize_entity_prompt(text: str) -> str:
        """
        Optimize prompt for entity extraction
        """
        prompt = f"""Extract entities from: {text[:400]}
Format: companies: [...], people: [...], dates: [...]
Entities:"""
        
        return prompt


# Global context manager instance for single conversation
_context_manager: Optional[ContextWindowManager] = None

def get_context_manager(max_tokens: int = 2048) -> ContextWindowManager:
    """
    Get or create global context manager
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextWindowManager(max_tokens)
    return _context_manager

def reset_context():
    """Reset global context manager"""
    global _context_manager
    _context_manager = None
