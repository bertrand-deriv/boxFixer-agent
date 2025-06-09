import os
from jinja2 import Template
import yaml

class PromptManager:
    def __init__(self, env_prefix="BOX_AGENT_"):
        with open("config/prompts.yaml") as f:
            PROMPTS = yaml.safe_load(f)
        self.templates = {}

        for key, value in PROMPTS.items():
            if key.startswith(env_prefix) and key.endswith("_PROMPT"):
                name = key[len(env_prefix):-7].lower()
                self.templates[name] = value

    def get_prompt(self, template_name, **kwargs):
        if template_name not in self.templates:
            raise ValueError(f"Unknown prompt template: {template_name}")

        template = Template(self.templates[template_name])
        result = template.render(**kwargs)

        return result