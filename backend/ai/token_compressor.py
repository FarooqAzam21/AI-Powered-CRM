"""
Token Compression Utilities - PHASE 5 OPTIMIZATION
Compress long emails and prompts to reduce token usage
Target: Reduce token count by 30-40%
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class TokenCompressor:
    """
    Compress text content while maintaining meaning
    Optimized for email content processing
    """
    
    # Stopwords that can be safely removed or shortened
    STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
        'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    # Common email phrases that can be shortened
    PHRASE_REPLACEMENTS = {
        r'\b(please|kindly|thanks?|thank you)\b': '',
        r'\bregards?\b': '',
        r'\b(yours? )?sincerely\b': '',
        r'\bbest wishes\b': '',
        r'\b(with )?regards\b': '',
        r'\b(have a )?great day\b': '',
        r'\btalk soon\b': '',
        r'\blooking forward to.*?\b': 'looking forward',
        r'\bdo not hesitate to.*?\b': 'contact if needed',
        r'\bif you have any questions.*?\b': 'contact if needed',
        r'\b(please )?let me know\b': 'contact me',
        r'\b(i )?would (like to|appreciate|be grateful for)\b': 'need',
        r'\b(can you|could you|would you|will you) (please )?\b': 'pls ',
    }
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count (rough approximation)
        Ollama/LLaMA: ~4 characters per token on average
        """
        return len(text) // 4
    
    @staticmethod
    def compress_email(subject: str, body: str, max_tokens: int = 1024) -> Tuple[str, str]:
        """
        Compress email subject and body
        Preserves key information while reducing token count
        
        Returns:
            (compressed_subject, compressed_body)
        """
        logger.debug(f"📦 Compressing email (est. {TokenCompressor.estimate_tokens(body)} tokens)")
        
        # Start with original
        compressed_subject = TokenCompressor._compress_text(subject, is_subject=True)
        compressed_body = TokenCompressor._compress_text(body, is_subject=False)
        
        # Check token count
        total_tokens = TokenCompressor.estimate_tokens(f"{compressed_subject} {compressed_body}")
        
        if total_tokens > max_tokens:
            logger.debug(f"⚙️  Reducing to {max_tokens} tokens (was {total_tokens})")
            # More aggressive compression
            compressed_body = TokenCompressor._aggressive_compress(compressed_body, max_tokens)
        
        reduction = 100 * (1 - len(f"{compressed_subject} {compressed_body}") / 
                          len(f"{subject} {body}"))
        logger.debug(f"✅ Compressed: {reduction:.1f}% reduction")
        
        return compressed_subject, compressed_body
    
    @staticmethod
    def _compress_text(text: str, is_subject: bool = False) -> str:
        """Internal compression logic"""
        if not text:
            return text
        
        # 1. Apply phrase replacements
        for pattern, replacement in TokenCompressor.PHRASE_REPLACEMENTS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # 2. Remove excessive punctuation
        text = re.sub(r'[.!?]{2,}', '.', text)  # Multiple punctuation -> single
        text = re.sub(r'\s{2,}', ' ', text)     # Multiple spaces -> single
        
        # 3. For body text (not subject), remove some stopwords
        if not is_subject:
            words = text.split()
            filtered = []
            for i, word in enumerate(words):
                # Keep some context by not removing all stopwords
                if word.lower() in TokenCompressor.STOPWORDS and i > 0 and i < len(words) - 1:
                    if i % 3 != 0:  # Keep every 3rd stopword for readability
                        continue
                filtered.append(word)
            text = ' '.join(filtered)
        
        # 4. Remove URLs (often not needed for classification)
        text = re.sub(r'https?://\S+', '[link]', text)
        
        # 5. Remove email addresses (often not needed)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[email]', text)
        
        # 6. Remove quoted text markers
        text = re.sub(r'(^|\n)>\s*.+', '', text)
        
        # 7. Abbreviate common words
        abbreviations = {
            r'\bwithout\b': 'w/o',
            r'\bwith\b': 'w/',
            r'\byou\b': 'u',
            r'\byour\b': 'ur',
            r'\bplease\b': 'pls',
            r'\bthank\s*you\b': 'thx',
            r'\binformation\b': 'info',
            r'\bsignature\b': 'sig',
            r'\breally\b': 'rly',
        }
        for pattern, abbr in abbreviations.items():
            text = re.sub(pattern, abbr, text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def _aggressive_compress(text: str, max_tokens: int) -> str:
        """
        More aggressive compression for very long emails
        Keep only first sentences
        """
        sentences = re.split(r'[.!?]+', text)
        
        # Calculate tokens per sentence (rough)
        result = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = TokenCompressor.estimate_tokens(sentence)
            if current_tokens + sentence_tokens <= max_tokens:
                result.append(sentence)
                current_tokens += sentence_tokens
            else:
                break
        
        return '. '.join(result) + '.'
    
    @staticmethod
    def compress_for_context(text: str, context_tokens: int = 2048, reserved: int = 500) -> str:
        """
        Compress text to fit within context window
        Reserved tokens are for model response
        
        Returns:
            Compressed text that fits in context
        """
        available_tokens = context_tokens - reserved
        current_tokens = TokenCompressor.estimate_tokens(text)
        
        if current_tokens <= available_tokens:
            return text
        
        logger.debug(f"🔄 Context compression: {current_tokens}→{available_tokens} tokens")
        
        # Truncate to approximate token count
        target_chars = available_tokens * 4
        truncated = text[:target_chars]
        
        # Find last complete sentence
        last_period = truncated.rfind('.')
        if last_period > target_chars * 0.8:  # Reasonable sentence
            truncated = truncated[:last_period + 1]
        
        return truncated
    
    @staticmethod
    def get_compression_stats(original: str, compressed: str) -> dict:
        """
        Get compression statistics
        """
        orig_tokens = TokenCompressor.estimate_tokens(original)
        comp_tokens = TokenCompressor.estimate_tokens(compressed)
        reduction = 100 * (1 - comp_tokens / orig_tokens) if orig_tokens > 0 else 0
        
        return {
            "original_chars": len(original),
            "compressed_chars": len(compressed),
            "original_tokens": orig_tokens,
            "compressed_tokens": comp_tokens,
            "token_reduction_percent": round(reduction, 1),
            "char_reduction_percent": round(100 * (1 - len(compressed) / len(original)), 1),
        }
