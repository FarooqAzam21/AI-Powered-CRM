"""
AgentRegistry — Maintains a registry of all available specialized agents.
"""
import logging
from typing import Dict, Type, Optional
from ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._task_map: Dict[str, str] = {}  # task_type -> agent_name

    def register(self, agent_class: Type[BaseAgent]):
        agent = agent_class()
        self._agents[agent.agent_name] = agent
        
        for task in agent.supported_tasks:
            if task in self._task_map:
                logger.warning(f"Task '{task}' overwritten by agent '{agent.agent_name}'")
            self._task_map[task] = agent.agent_name
            
        logger.info(f"Registered agent: {agent.agent_name} (tasks: {agent.supported_tasks})")

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_name)

    def get_agent_for_task(self, task_type: str) -> Optional[BaseAgent]:
        agent_name = self._task_map.get(task_type)
        if agent_name:
            return self._agents.get(agent_name)
        return None

# Singleton instance
_registry = AgentRegistry()

def get_agent_registry() -> AgentRegistry:
    return _registry
