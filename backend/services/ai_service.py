"""
Legacy AI Service Wrapper
Provides backwards compatibility for background tasks after the Phase 2-12 Multi-Agent refactoring.
"""
from ai.services.ai_engine import get_ai_engine

class LegacyAIService:
    def __init__(self):
        self.engine = get_ai_engine()

    async def classify_email(self, subject: str, body: str):
        return await self.engine.classify_email(subject, body)

    async def generate_reply(self, db, contact_id, email_body, tone="professional"):
        return await self.engine.generate_reply(db, contact_id, email_body, tone)

    async def extract_entities(self, text: str):
        # AIEngine has legacy methods, let's proxy to provider if extract_entities isn't there
        prompt = f"Extract key entities (names, organizations, dates, locations, action items) from the following text:\\n\\n{text}\\n\\nReturn JSON."
        from ai.parser.json_parser import ResponseParser
        return await ResponseParser.parse_with_retry(
            llm_callable=self.engine.provider.generate,
            initial_prompt=prompt,
            fallback_response={"entities": []}
        )

ai_service = LegacyAIService()
