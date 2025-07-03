# mcp_toolbox/utils/yaml_parser.py
import os
import re
import yaml
from typing import Dict, Any

class YamlConfigParser:
    """Parser for YAML configuration with environment variable substitution."""
    
    ENV_VAR_PATTERN = re.compile(r'\$\{(\w+)\}')
    
    @classmethod
    def load_config(cls, file_path: str) -> Dict[str, Any]:
        """Load and parse YAML configuration file."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Substitute environment variables
        content = cls._substitute_env_vars(content)
        
        # Parse YAML
        config = yaml.safe_load(content)
        return config
    
    @classmethod
    def _substitute_env_vars(cls, content: str) -> str:
        """Substitute environment variables in the content."""
        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        
        return cls.ENV_VAR_PATTERN.sub(replace_env_var, content)