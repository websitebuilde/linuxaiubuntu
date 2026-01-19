"""
Command schema definitions using Pydantic.

Defines structured command types for safe system operations.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import re


class CommandType(str, Enum):
    """Enumeration of supported command types."""
    START_APP = "start_app"
    KILL_PROCESS = "kill_process"
    LIST_PROCESSES = "list_processes"
    RESTART_SERVICE = "restart_service"
    SHELL_QUERY = "shell_query"


class CommandRequest(BaseModel):
    """
    Structured command request from the AI.
    
    The AI must output JSON conforming to this schema.
    """
    action: CommandType = Field(
        ...,
        description="The type of action to perform"
    )
    target: str = Field(
        ...,
        description="The target of the action (app name, process name, service name, or shell command)"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional additional parameters for the action"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Brief explanation of why this action was chosen"
    )
    
    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Validate and sanitize the target field."""
        if not v or not v.strip():
            raise ValueError("Target cannot be empty")
        
        # Remove any shell metacharacters that could be dangerous
        # Allow only alphanumeric, dash, underscore, dot, space, and forward slash
        sanitized = re.sub(r'[;&|`$(){}[\]<>!\\"\']', '', v)
        
        if len(sanitized) > 256:
            raise ValueError("Target too long (max 256 characters)")
        
        return sanitized.strip()
    
    @field_validator("action", mode="before")
    @classmethod
    def validate_action(cls, v: Any) -> CommandType:
        """Ensure action is a valid CommandType."""
        if isinstance(v, str):
            try:
                return CommandType(v.lower())
            except ValueError:
                valid_actions = [ct.value for ct in CommandType]
                raise ValueError(f"Invalid action '{v}'. Must be one of: {valid_actions}")
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "action": "start_app",
                    "target": "firefox",
                    "parameters": None,
                    "reason": "User requested to open Firefox browser"
                },
                {
                    "action": "kill_process",
                    "target": "firefox",
                    "parameters": {"signal": "TERM"},
                    "reason": "User requested to stop Firefox"
                },
                {
                    "action": "list_processes",
                    "target": "all",
                    "parameters": {"filter": "cpu"},
                    "reason": "User wants to see running processes"
                },
                {
                    "action": "restart_service",
                    "target": "nginx",
                    "parameters": None,
                    "reason": "User requested to restart nginx service"
                },
                {
                    "action": "shell_query",
                    "target": "ps aux | grep python",
                    "parameters": None,
                    "reason": "User wants to find Python processes"
                }
            ]
        }
    }


class CommandResponse(BaseModel):
    """
    Response from command execution.
    """
    success: bool = Field(
        ...,
        description="Whether the command executed successfully"
    )
    action: CommandType = Field(
        ...,
        description="The action that was executed"
    )
    target: str = Field(
        ...,
        description="The target of the action"
    )
    output: Optional[str] = Field(
        default=None,
        description="Output from the command execution"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the command failed"
    )
    exit_code: Optional[int] = Field(
        default=None,
        description="Exit code from the executed command"
    )


class AIResponse(BaseModel):
    """
    Expected response format from the AI/LLM.
    
    The LLM must respond with JSON matching this schema,
    or an error response if the request cannot be fulfilled.
    """
    command: Optional[CommandRequest] = Field(
        default=None,
        description="The structured command to execute"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the request cannot be processed"
    )
    cannot_process: bool = Field(
        default=False,
        description="Set to true if the request falls outside supported capabilities"
    )
    
    @field_validator("command", mode="after")
    @classmethod
    def validate_command_or_error(cls, v, info):
        """Ensure either command or error is provided."""
        # This runs after the model is constructed
        return v
    
    def model_post_init(self, __context):
        """Validate that we have either a command or an error."""
        if self.command is None and self.error is None and not self.cannot_process:
            raise ValueError("Response must have either a command, an error, or cannot_process=true")


def get_command_schema() -> Dict[str, Any]:
    """Return the JSON schema for CommandRequest."""
    return CommandRequest.model_json_schema()


def get_ai_response_schema() -> Dict[str, Any]:
    """Return the JSON schema for AIResponse."""
    return AIResponse.model_json_schema()
