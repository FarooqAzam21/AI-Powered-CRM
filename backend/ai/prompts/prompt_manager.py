import os
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Manages loading and rendering of LLM prompt templates using Jinja2.
    Ensures separation of business logic from prompt engineering.
    """

    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            # Default to the templates directory relative to this file
            base_dir = os.path.dirname(__file__)
            templates_dir = os.path.join(base_dir, "templates")
            
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def render(self, template_name: str, **kwargs) -> str:
        """
        Renders a Jinja2 template with the given context arguments.
        """
        try:
            if not template_name.endswith('.jinja2'):
                template_name += '.jinja2'
                
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Failed to render prompt template '{template_name}': {e}")
            raise

_manager = None

def get_prompt_manager() -> PromptManager:
    global _manager
    if _manager is None:
        _manager = PromptManager()
    return _manager
