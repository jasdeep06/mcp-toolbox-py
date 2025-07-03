# mcp_toolbox/tools/parameters.py
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json

class ParameterType(Enum):
    """Supported parameter types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

# Type alias for parameter values
ParameterValue = Union[str, int, float, bool, list, dict, None]

@dataclass
class Parameter:
    """Parameter definition for tools."""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[ParameterValue] = None
    enum: Optional[List[Any]] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    
    def __post_init__(self):
        """Validate parameter definition after initialization."""
        if isinstance(self.type, str):
            self.type = ParameterType(self.type)
        
        # If not required, must have a default value
        if not self.required and self.default is None:
            self.default = self._get_default_value()
    
    def _get_default_value(self) -> ParameterValue:
        """Get appropriate default value for the parameter type."""
        defaults = {
            ParameterType.STRING: "",
            ParameterType.INTEGER: 0,
            ParameterType.NUMBER: 0.0,
            ParameterType.BOOLEAN: False,
            ParameterType.ARRAY: [],
            ParameterType.OBJECT: {}
        }
        return defaults.get(self.type)
    
    def validate(self, value: ParameterValue) -> ParameterValue:
        """Validate and convert a parameter value."""
        if value is None:
            if self.required:
                raise ValueError(f"Parameter '{self.name}' is required")
            return self.default
        
        # Type validation and conversion
        validated_value = self._validate_type(value)
        
        # Additional constraints validation
        self._validate_constraints(validated_value)
        
        return validated_value
    
    def _validate_type(self, value: ParameterValue) -> ParameterValue:
        """Validate and convert parameter type."""
        if self.type == ParameterType.STRING:
            if not isinstance(value, str):
                return str(value)
            return value
            
        elif self.type == ParameterType.INTEGER:
            if isinstance(value, bool):
                raise ValueError(f"Parameter '{self.name}' must be an integer, got boolean")
            if isinstance(value, str):
                try:
                    return int(value)
                except ValueError:
                    raise ValueError(f"Parameter '{self.name}' must be an integer, got '{value}'")
            if isinstance(value, float):
                if value.is_integer():
                    return int(value)
                else:
                    raise ValueError(f"Parameter '{self.name}' must be an integer, got float {value}")
            if not isinstance(value, int):
                raise ValueError(f"Parameter '{self.name}' must be an integer")
            return value
            
        elif self.type == ParameterType.NUMBER:
            if isinstance(value, bool):
                raise ValueError(f"Parameter '{self.name}' must be a number, got boolean")
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    raise ValueError(f"Parameter '{self.name}' must be a number, got '{value}'")
            if not isinstance(value, (int, float)):
                raise ValueError(f"Parameter '{self.name}' must be a number")
            return float(value)
            
        elif self.type == ParameterType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lower_val = value.lower()
                if lower_val in ('true', '1', 'yes', 'on'):
                    return True
                elif lower_val in ('false', '0', 'no', 'off'):
                    return False
                else:
                    raise ValueError(f"Parameter '{self.name}' must be a boolean, got '{value}'")
            if isinstance(value, (int, float)):
                return bool(value)
            raise ValueError(f"Parameter '{self.name}' must be a boolean")
            
        elif self.type == ParameterType.ARRAY:
            if not isinstance(value, list):
                raise ValueError(f"Parameter '{self.name}' must be an array")
            return value
            
        elif self.type == ParameterType.OBJECT:
            if not isinstance(value, dict):
                raise ValueError(f"Parameter '{self.name}' must be an object")
            return value
        
        return value
    
    def _validate_constraints(self, value: ParameterValue) -> None:
        """Validate parameter constraints."""
        # Enum validation
        if self.enum is not None and value not in self.enum:
            raise ValueError(f"Parameter '{self.name}' must be one of {self.enum}, got {value}")
        
        # Numeric constraints
        if self.type in (ParameterType.INTEGER, ParameterType.NUMBER):
            if self.minimum is not None and value < self.minimum:
                raise ValueError(f"Parameter '{self.name}' must be >= {self.minimum}, got {value}")
            if self.maximum is not None and value > self.maximum:
                raise ValueError(f"Parameter '{self.name}' must be <= {self.maximum}, got {value}")
        
        # String constraints
        if self.type == ParameterType.STRING:
            if self.min_length is not None and len(value) < self.min_length:
                raise ValueError(f"Parameter '{self.name}' must be at least {self.min_length} characters")
            if self.max_length is not None and len(value) > self.max_length:
                raise ValueError(f"Parameter '{self.name}' must be at most {self.max_length} characters")
            if self.pattern is not None:
                import re
                if not re.match(self.pattern, value):
                    raise ValueError(f"Parameter '{self.name}' does not match pattern {self.pattern}")
        
        # Array constraints
        if self.type == ParameterType.ARRAY:
            if self.min_length is not None and len(value) < self.min_length:
                raise ValueError(f"Parameter '{self.name}' must have at least {self.min_length} items")
            if self.max_length is not None and len(value) > self.max_length:
                raise ValueError(f"Parameter '{self.name}' must have at most {self.max_length} items")

    def to_mcp_schema(self) -> Dict[str, Any]:
        """Convert parameter to MCP JSON Schema format."""
        schema = {
            "type": self.type.value,
            "description": self.description
        }
        
        # Add constraints to schema
        if self.enum is not None:
            schema["enum"] = self.enum
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.min_length is not None:
            if self.type == ParameterType.STRING:
                schema["minLength"] = self.min_length
            elif self.type == ParameterType.ARRAY:
                schema["minItems"] = self.min_length
        if self.max_length is not None:
            if self.type == ParameterType.STRING:
                schema["maxLength"] = self.max_length
            elif self.type == ParameterType.ARRAY:
                schema["maxItems"] = self.max_length
        if self.pattern is not None:
            schema["pattern"] = self.pattern
        
        return schema

class ParameterSet:
    """Collection of parameters with validation."""
    
    def __init__(self, parameters: List[Parameter]):
        self.parameters = {p.name: p for p in parameters}
        self._parameter_list = parameters
    
    def validate_values(self, values: Dict[str, Any]) -> Dict[str, ParameterValue]:
        """Validate a set of parameter values."""
        validated = {}
        
        # Validate provided values
        for name, value in values.items():
            if name not in self.parameters:
                raise ValueError(f"Unknown parameter: {name}")
            validated[name] = self.parameters[name].validate(value)
        
        # Check for missing required parameters and add defaults
        for name, param in self.parameters.items():
            if name not in validated:
                if param.required:
                    raise ValueError(f"Required parameter '{name}' not provided")
                validated[name] = param.default
        
        return validated
    
    def to_mcp_schema(self) -> Dict[str, Any]:
        """Convert parameter set to MCP JSON Schema format."""
        properties = {}
        required = []
        
        for param in self._parameter_list:
            properties[param.name] = param.to_mcp_schema()
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def get_manifests(self) -> List[Dict[str, Any]]:
        """Get parameter manifests for client SDKs."""
        manifests = []
        for param in self._parameter_list:
            manifest = {
                "name": param.name,
                "type": param.type.value,
                "description": param.description,
                "required": param.required
            }
            if param.default is not None:
                manifest["default"] = param.default
            if param.enum is not None:
                manifest["enum"] = param.enum
            manifests.append(manifest)
        return manifests

def parse_parameters(param_configs: List[Dict[str, Any]]) -> List[Parameter]:
    """Parse parameter configurations from YAML/dict format."""
    parameters = []
    
    for config in param_configs:
        param = Parameter(
            name=config["name"],
            type=config["type"],
            description=config["description"],
            required=config.get("required", True),
            default=config.get("default"),
            enum=config.get("enum"),
            minimum=config.get("minimum"),
            maximum=config.get("maximum"),
            min_length=config.get("minLength"),
            max_length=config.get("maxLength"),
            pattern=config.get("pattern")
        )
        parameters.append(param)
    
    return parameters

def create_parameter_set(param_configs: List[Dict[str, Any]]) -> ParameterSet:
    """Create a ParameterSet from configuration."""
    parameters = parse_parameters(param_configs)
    print("parameters: ", parameters)
    return ParameterSet(parameters)

# Utility functions for common parameter types
def string_param(name: str, description: str, required: bool = True, 
                default: Optional[str] = None, **kwargs) -> Parameter:
    """Create a string parameter."""
    return Parameter(name, ParameterType.STRING, description, required, default, **kwargs)

def int_param(name: str, description: str, required: bool = True, 
             default: Optional[int] = None, **kwargs) -> Parameter:
    """Create an integer parameter."""
    return Parameter(name, ParameterType.INTEGER, description, required, default, **kwargs)

def bool_param(name: str, description: str, required: bool = True, 
              default: Optional[bool] = None, **kwargs) -> Parameter:
    """Create a boolean parameter."""
    return Parameter(name, ParameterType.BOOLEAN, description, required, default, **kwargs)

def number_param(name: str, description: str, required: bool = True, 
                default: Optional[float] = None, **kwargs) -> Parameter:
    """Create a number parameter."""
    return Parameter(name, ParameterType.NUMBER, description, required, default, **kwargs)