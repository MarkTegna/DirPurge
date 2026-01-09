"""
Configuration schema validation for DirPurge
Provides structured validation and type safety for configuration
"""

from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from .logger import get_logger
from .validators import ValidationError

logger = get_logger()


class ConfigFieldType(Enum):
    """Configuration field types"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    PATH = "path"
    EMAIL = "email"
    LIST = "list"
    OBJECT = "object"


@dataclass
class ConfigField:
    """Configuration field definition"""
    name: str
    field_type: ConfigFieldType
    required: bool = False
    default: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""
    sensitive: bool = False  # Mark sensitive fields for logging


@dataclass
class ConfigSection:
    """Configuration section definition"""
    name: str
    fields: List[ConfigField] = field(default_factory=list)
    required: bool = True
    description: str = ""


class ConfigSchema:
    """
    Configuration schema definition and validation
    """
    
    def __init__(self):
        self.sections = self._define_schema()
    
    def _define_schema(self) -> List[ConfigSection]:
        """Define the complete configuration schema"""
        
        # General section
        general_section = ConfigSection(
            name="general",
            description="General application settings",
            fields=[
                ConfigField(
                    name="target_directory",
                    field_type=ConfigFieldType.PATH,
                    required=True,
                    description="Target directory to purge files from"
                ),
                ConfigField(
                    name="min_files_to_keep",
                    field_type=ConfigFieldType.INTEGER,
                    default=50,
                    min_value=0,
                    max_value=10000,
                    description="Minimum number of files to keep per file set"
                ),
                ConfigField(
                    name="max_age_days",
                    field_type=ConfigFieldType.INTEGER,
                    default=366,
                    min_value=0,
                    max_value=36500,
                    description="Maximum age in days for files to preserve"
                ),
                ConfigField(
                    name="excluded_extensions",
                    field_type=ConfigFieldType.LIST,
                    default=[".PL", ".TXT", ".CSV", ".ZIP"],
                    description="Comma-separated list of file extensions to exclude"
                ),
                ConfigField(
                    name="dry_run",
                    field_type=ConfigFieldType.BOOLEAN,
                    default=False,
                    description="Preview mode - show what would be deleted without actually deleting"
                ),
                ConfigField(
                    name="reports_directory",
                    field_type=ConfigFieldType.PATH,
                    default="./reports",
                    description="Directory to save reports"
                ),
                ConfigField(
                    name="generate_xlsx",
                    field_type=ConfigFieldType.BOOLEAN,
                    default=False,
                    description="Generate Excel file with file set summary"
                )
            ]
        )
        
        # Email section
        email_section = ConfigSection(
            name="email",
            required=False,
            description="Email notification settings",
            fields=[
                ConfigField(
                    name="send_email",
                    field_type=ConfigFieldType.BOOLEAN,
                    default=False,
                    description="Enable email notifications"
                ),
                ConfigField(
                    name="smtp_server",
                    field_type=ConfigFieldType.STRING,
                    max_length=253,
                    description="SMTP server hostname"
                ),
                ConfigField(
                    name="smtp_port",
                    field_type=ConfigFieldType.INTEGER,
                    default=25,
                    min_value=1,
                    max_value=65535,
                    description="SMTP server port"
                ),
                ConfigField(
                    name="smtp_use_tls",
                    field_type=ConfigFieldType.BOOLEAN,
                    default=False,
                    description="Use TLS for SMTP connection"
                ),
                ConfigField(
                    name="smtp_username",
                    field_type=ConfigFieldType.STRING,
                    max_length=256,
                    sensitive=True,
                    description="SMTP authentication username"
                ),
                ConfigField(
                    name="smtp_password",
                    field_type=ConfigFieldType.STRING,
                    max_length=256,
                    sensitive=True,
                    description="SMTP authentication password"
                ),
                ConfigField(
                    name="from_email",
                    field_type=ConfigFieldType.EMAIL,
                    max_length=254,
                    description="Email address to send from"
                ),
                ConfigField(
                    name="to_email",
                    field_type=ConfigFieldType.EMAIL,
                    max_length=254,
                    description="Email address to send to"
                )
            ]
        )
        
        return [general_section, email_section]
    
    def validate_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration against schema
        
        Args:
            config_dict: Configuration dictionary to validate
            
        Returns:
            Validated and normalized configuration
            
        Raises:
            ValidationError: If validation fails
        """
        validated_config = {}
        errors = []
        
        # Process each section
        for section in self.sections:
            section_data = config_dict.get(section.name, {})
            
            # Check if required section is missing
            if section.required and not section_data:
                errors.append(f"Required section '{section.name}' is missing")
                continue
            
            validated_section = {}
            
            # Process each field in the section
            for field in section.fields:
                field_value = section_data.get(field.name)
                
                try:
                    validated_value = self._validate_field(field, field_value)
                    if validated_value is not None:
                        validated_section[field.name] = validated_value
                except ValidationError as e:
                    errors.append(f"Section '{section.name}', field '{field.name}': {e}")
            
            if validated_section:
                validated_config[section.name] = validated_section
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValidationError(error_msg)
        
        return validated_config
    
    def _validate_field(self, field: ConfigField, value: Any) -> Any:
        """
        Validate a single field value
        
        Args:
            field: Field definition
            value: Value to validate
            
        Returns:
            Validated value
            
        Raises:
            ValidationError: If validation fails
        """
        # Handle missing values
        if value is None or value == "":
            if field.required:
                raise ValidationError(f"Required field is missing")
            return field.default
        
        # Type-specific validation
        if field.field_type == ConfigFieldType.STRING:
            return self._validate_string(field, value)
        elif field.field_type == ConfigFieldType.INTEGER:
            return self._validate_integer(field, value)
        elif field.field_type == ConfigFieldType.BOOLEAN:
            return self._validate_boolean(field, value)
        elif field.field_type == ConfigFieldType.PATH:
            return self._validate_path(field, value)
        elif field.field_type == ConfigFieldType.EMAIL:
            return self._validate_email(field, value)
        elif field.field_type == ConfigFieldType.LIST:
            return self._validate_list(field, value)
        elif field.field_type == ConfigFieldType.OBJECT:
            return self._validate_object(field, value)
        else:
            raise ValidationError(f"Unknown field type: {field.field_type}")
    
    def _validate_string(self, field: ConfigField, value: Any) -> str:
        """Validate string field"""
        if not isinstance(value, str):
            try:
                value = str(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Cannot convert to string: {value}")
        
        # Length validation
        if field.min_length is not None and len(value) < field.min_length:
            raise ValidationError(f"String too short (min {field.min_length}): {len(value)}")
        
        if field.max_length is not None and len(value) > field.max_length:
            raise ValidationError(f"String too long (max {field.max_length}): {len(value)}")
        
        # Pattern validation
        if field.pattern:
            import re
            if not re.match(field.pattern, value):
                raise ValidationError(f"String does not match pattern: {field.pattern}")
        
        # Allowed values validation
        if field.allowed_values and value not in field.allowed_values:
            raise ValidationError(f"Value not in allowed list: {field.allowed_values}")
        
        return value
    
    def _validate_integer(self, field: ConfigField, value: Any) -> int:
        """Validate integer field"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Cannot convert to integer: {value}")
        
        # Range validation
        if field.min_value is not None and int_value < field.min_value:
            raise ValidationError(f"Value too small (min {field.min_value}): {int_value}")
        
        if field.max_value is not None and int_value > field.max_value:
            raise ValidationError(f"Value too large (max {field.max_value}): {int_value}")
        
        return int_value
    
    def _validate_boolean(self, field: ConfigField, value: Any) -> bool:
        """Validate boolean field"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower_val = value.lower().strip()
            if lower_val in ('true', '1', 'yes', 'on'):
                return True
            elif lower_val in ('false', '0', 'no', 'off'):
                return False
        
        raise ValidationError(f"Cannot convert to boolean: {value}")
    
    def _validate_path(self, field: ConfigField, value: Any) -> str:
        """Validate path field"""
        if not isinstance(value, str):
            try:
                value = str(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Cannot convert to path string: {value}")
        
        # Basic path validation (detailed validation done elsewhere)
        if not value.strip():
            raise ValidationError("Path cannot be empty")
        
        return value.strip()
    
    def _validate_email(self, field: ConfigField, value: Any) -> str:
        """Validate email field"""
        if not isinstance(value, str):
            try:
                value = str(value)
            except (ValueError, TypeError):
                raise ValidationError(f"Cannot convert to email string: {value}")
        
        value = value.strip()
        
        # Basic email format validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValidationError(f"Invalid email format: {value}")
        
        return value
    
    def _validate_list(self, field: ConfigField, value: Any) -> List[Any]:
        """Validate list field"""
        if isinstance(value, str):
            # Handle comma-separated string
            if not value.strip():
                return []
            return [item.strip() for item in value.split(',') if item.strip()]
        elif isinstance(value, list):
            return value
        else:
            raise ValidationError(f"Cannot convert to list: {value}")
    
    def _validate_object(self, field: ConfigField, value: Any) -> Dict[str, Any]:
        """Validate object field"""
        if isinstance(value, dict):
            return value
        else:
            raise ValidationError(f"Value must be an object: {value}")
    
    def get_schema_documentation(self) -> str:
        """
        Generate documentation for the configuration schema
        
        Returns:
            Formatted schema documentation
        """
        doc_lines = ["# DirPurge Configuration Schema", ""]
        
        for section in self.sections:
            doc_lines.append(f"## [{section.name}]")
            if section.description:
                doc_lines.append(f"{section.description}")
            doc_lines.append("")
            
            for field in section.fields:
                required_str = " (REQUIRED)" if field.required else ""
                default_str = f" (default: {field.default})" if field.default is not None else ""
                
                doc_lines.append(f"### {field.name}{required_str}")
                doc_lines.append(f"**Type:** {field.field_type.value}")
                
                if field.description:
                    doc_lines.append(f"**Description:** {field.description}")
                
                if field.min_value is not None or field.max_value is not None:
                    range_str = f"Range: {field.min_value or 'unlimited'} - {field.max_value or 'unlimited'}"
                    doc_lines.append(f"**{range_str}**")
                
                if field.allowed_values:
                    doc_lines.append(f"**Allowed values:** {', '.join(map(str, field.allowed_values))}")
                
                if default_str:
                    doc_lines.append(f"**Default:** {field.default}")
                
                doc_lines.append("")
            
            doc_lines.append("")
        
        return "\n".join(doc_lines)
    
    def export_schema_json(self) -> str:
        """
        Export schema as JSON for external tools
        
        Returns:
            JSON schema representation
        """
        schema_dict = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for section in self.sections:
            section_schema = {
                "type": "object",
                "properties": {},
                "description": section.description
            }
            
            if section.required:
                schema_dict["required"].append(section.name)
            
            for field in section.fields:
                field_schema = {
                    "description": field.description
                }
                
                if field.field_type == ConfigFieldType.STRING:
                    field_schema["type"] = "string"
                elif field.field_type == ConfigFieldType.INTEGER:
                    field_schema["type"] = "integer"
                elif field.field_type == ConfigFieldType.BOOLEAN:
                    field_schema["type"] = "boolean"
                elif field.field_type == ConfigFieldType.LIST:
                    field_schema["type"] = "array"
                elif field.field_type == ConfigFieldType.OBJECT:
                    field_schema["type"] = "object"
                else:
                    field_schema["type"] = "string"
                
                if field.default is not None:
                    field_schema["default"] = field.default
                
                if field.min_value is not None:
                    field_schema["minimum"] = field.min_value
                
                if field.max_value is not None:
                    field_schema["maximum"] = field.max_value
                
                if field.allowed_values:
                    field_schema["enum"] = field.allowed_values
                
                section_schema["properties"][field.name] = field_schema
            
            schema_dict["properties"][section.name] = section_schema
        
        return json.dumps(schema_dict, indent=2)


# Global schema instance
config_schema = ConfigSchema()