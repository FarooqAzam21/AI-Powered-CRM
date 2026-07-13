import re
import logging

logger = logging.getLogger(__name__)

class PIISanitizer:
    """
    Strips Personal Identifiable Information (PII) from text 
    before it is sent to the LLM.
    """

    # Regex patterns for common PII
    # Note: These are basic patterns for demonstration. 
    # Production systems should use robust NLP or specialized libraries like Presidio.
    SSN_PATTERN = re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b')
    CC_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b')

    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Masks SSNs, Credit Cards, and Phone numbers in the given text.
        """
        if not text:
            return text

        try:
            text = cls.SSN_PATTERN.sub('[REDACTED SSN]', text)
            text = cls.CC_PATTERN.sub('[REDACTED CREDIT CARD]', text)
            text = cls.PHONE_PATTERN.sub('[REDACTED PHONE]', text)
        except Exception as e:
            logger.error(f"Failed to sanitize PII: {e}")
            
        return text
