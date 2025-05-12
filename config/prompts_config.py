import os
from dotenv import load_dotenv
from jinja2 import Template

class PromptManager:
    def __init__(self, env_prefix="AGENT_"):
        load_dotenv()
        self.templates = {}

        for key, value in os.environ.items():
            if key.startswith(env_prefix) and key.endswith("_PROMPT"):
                name = key[len(env_prefix):-7].lower()
                self.templates[name] = value.replace("\\n", "\n")

    def get_prompt(self, template_name, **kwargs):
        if template_name not in self.templates:
            raise ValueError(f"Unknown prompt template: {template_name}")

        template = Template(self.templates[template_name])
        result = template.render(**kwargs)

        return result