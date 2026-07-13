"""
BaseAgent — Abstract base class that every specialized agent must implement.

All shared services (ContextBuilder, PromptManager, MemoryManager, 
ResponseParser, SemanticCache, RAG) are injected once here.
No agent ever instantiates these itself.
"""
from __future__ import annotations
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from ai.agents.agent_context import AgentContext
from ai.agents.agent_result import AgentResult, AgentStatus
from ai.agents.agent_memory import AgentMemory

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.

    Lifecycle (called in order by execute()):
      1. prepare_context()  — fetch CRM data, build context string
      2. build_prompt()     — render Jinja2 template with context
      3. _generate()        — call AIEngine (shared Ollama provider)
      4. validate()         — parse & validate LLM output
      5. post_process()     — transform data, enrich result
      6. update_memory()    — write back to CustomerMemory
    """

    # Subclasses declare their name and what tasks they handle
    agent_name: str = "base_agent"
    supported_tasks: list[str] = []

    def __init__(self):
        # We don't initialize these here to avoid infinite recursion
        # during AIEngine startup since agents are registered inside AIEngine.__init__
        pass

    @property
    def engine(self):
        from ai.services.ai_engine import get_ai_engine
        return get_ai_engine()

    @property
    def context_builder(self):
        from ai.context.context_builder import get_context_builder
        return get_context_builder()

    @property
    def prompt_manager(self):
        from ai.prompts.prompt_manager import get_prompt_manager
        return get_prompt_manager()

    @property
    def parser(self):
        from ai.parser.json_parser import ResponseParser
        return ResponseParser

    @property
    def memory_manager(self):
        from ai.memory.memory_manager import get_memory_manager
        return get_memory_manager()

    @property
    def kb(self):
        from ai.rag.knowledge_base import get_knowledge_base
        return get_knowledge_base()

    @abstractmethod
    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        """
        Builds the CRM context string for this agent's task.
        Default implementations should call self.context_builder.build_context().
        """
        pass

    @abstractmethod
    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        """
        Renders the appropriate Jinja2 template for this task.
        Must use self.prompt_manager.render(template_name, **kwargs).
        """
        pass

    @abstractmethod
    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        Parses and validates the LLM's raw output.
        For JSON tasks, use self.parser.parse_with_retry().
        For text tasks, perform basic validation here.
        """
        pass

    async def post_process(self, validated_data: Dict[str, Any], ctx: AgentContext) -> Dict[str, Any]:
        """
        Optional: transform or enrich the validated output before returning.
        Override in subclasses if needed. Default: pass-through.
        """
        return validated_data

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        """
        Optional: update CustomerMemory after task completion.
        Override in subclasses for domain-specific memory updates.
        Default: no-op.
        """
        pass

    async def run(self, ctx: AgentContext, db: Session) -> AgentResult:
        """
        Main entry point. Executes the full agent lifecycle.
        Never override this in subclasses — override the individual hooks.
        """
        start_time = time.time()
        logger.info(f"[{self.agent_name}] Starting task: {ctx.task_type}")

        try:
            # Step 1: Build CRM context
            if ctx.crm_context:
                crm_context = ctx.crm_context  # pre-built context from workflow
            else:
                crm_context = await self.prepare_context(ctx, db)

            # Step 2: Build initial prompt
            prompt = await self.build_prompt(ctx, crm_context)

            # Try up to 3 times to get valid output
            max_retries = 3
            validated_data = None
            current_prompt = prompt
            
            for attempt in range(max_retries):
                # Step 3: Generate
                raw_output = await self.engine.provider.generate(current_prompt)

                # Step 4: Validate output
                try:
                    validated_data = await self.validate(raw_output, ctx)
                    break  # Success
                except Exception as val_error:
                    if attempt < max_retries - 1:
                        logger.warning(f"[{self.agent_name}] Validation failed on attempt {attempt+1}: {val_error}. Retrying...")
                        error_feedback = (
                            f"\n\n--- SYSTEM ERROR ON PREVIOUS ATTEMPT ---\n"
                            f"Your previous response was invalid. Error: {str(val_error)}\n"
                            f"Please correct the error and try again."
                        )
                        current_prompt = prompt + error_feedback
                    else:
                        raise ValueError(f"Failed validation after {max_retries} attempts: {val_error}")

            # Step 5: Post-process
            final_data = await self.post_process(validated_data, ctx)

            # Step 6: Update memory
            if ctx.contact_id and db:
                await self.update_memory(final_data, ctx, db)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"[{self.agent_name}] Completed {ctx.task_type} in {elapsed_ms:.0f}ms")

            return AgentResult(
                agent_name=self.agent_name,
                task_type=ctx.task_type,
                status=AgentStatus.SUCCESS,
                data=final_data,
                contact_id=ctx.contact_id,
                execution_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"[{self.agent_name}] Failed {ctx.task_type}: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.agent_name,
                task_type=ctx.task_type,
                status=AgentStatus.FAILED,
                data={},
                contact_id=ctx.contact_id,
                execution_time_ms=elapsed_ms,
                error=str(e),
            )

    def _get_agent_memory(self, db: Session, contact_id: int) -> Optional[AgentMemory]:
        if not contact_id or not db:
            return None
        return AgentMemory(db, contact_id)
