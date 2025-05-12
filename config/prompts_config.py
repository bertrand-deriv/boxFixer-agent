import os
from dotenv import load_dotenv
from string import Template
load_dotenv()

class PromptManager:
    def __init__(self, env_prefix="AGENT_"):
        """Initialize the prompt manager by loading from .env file
        
        Args:
            env_prefix: Prefix for environment variables to load as prompts
        """
        # Load environment variables
        load_dotenv()
        
        # Find and load all prompt templates with the given prefix
        self.templates = {}
        for key, value in os.environ.items():
            if key.startswith(env_prefix) and key.endswith("_PROMPT"):
                # Extract prompt name (remove prefix and _PROMPT suffix)
                name = key[len(env_prefix):-7].lower()
                # Store with newlines properly converted
                self.templates[name] = value.replace("\\n", "\n")
    
    def get_prompt(self, template_name, **kwargs):
        """
        Get a prompt with arguments filled in
        Args:
            template_name: Name of the prompt template to use
            **kwargs: Arguments to fill into the template
            
        Returns:
            Formatted prompt string with arguments filled in
        """
        if template_name not in self.templates:
            raise ValueError(f"Unknown prompt template: {template_name}")
        template = Template(self.templates[template_name])
        result = template.safe_substitute(**kwargs)
        
        # Debug output
        print(f"Template variables: {kwargs.keys()}")
        print(f"Substitution result contains placeholder? {'${' in result}")
        
        return result
    
    def list_available_prompts(self):
        """List all available prompt templates"""
        return list(self.templates.keys())