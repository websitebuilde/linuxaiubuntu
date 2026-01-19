"""
Main dispatcher for the AI System Assistant.

Orchestrates the flow from user input through AI processing,
validation, policy enforcement, and execution.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config import get_config, Config
from .commands import CommandRequest, CommandResponse, AIResponse
from .policy import SecurityPolicy, get_policy, PolicyViolationError
from .ai import OllamaLLM, create_llm, LLMResult
from .executor import SafeExecutor, create_executor


logger = logging.getLogger(__name__)


@dataclass
class AssistantResult:
    """Result from the assistant processing."""
    success: bool
    message: str
    command: Optional[CommandRequest] = None
    response: Optional[CommandResponse] = None
    error: Optional[str] = None


class AIAssistant:
    """
    Main AI Assistant class.
    
    Orchestrates the full pipeline:
    1. User Input
    2. LLM Processing
    3. Response Parsing
    4. Policy Validation
    5. Command Execution
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        llm: Optional[OllamaLLM] = None,
        policy: Optional[SecurityPolicy] = None,
        executor: Optional[SafeExecutor] = None,
    ):
        """
        Initialize the AI Assistant.
        
        Args:
            config: Configuration instance
            llm: LLM instance
            policy: Security policy instance
            executor: Command executor instance
        """
        self.config = config or get_config()
        self.llm = llm or create_llm()
        self.policy = policy or get_policy()
        self.executor = executor or create_executor()
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the assistant."""
        log_format = self.config.log_format
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
        )
        
        # Add file handler if possible
        try:
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            
            logging.getLogger().addHandler(file_handler)
            logger.info(f"Logging to {self.config.log_file}")
        except PermissionError:
            # Fall back to stderr only
            logger.warning(
                f"Cannot write to {self.config.log_file}, logging to stderr only"
            )
        except Exception as e:
            logger.warning(f"Error setting up file logging: {e}")
    
    def process(self, user_input: str) -> AssistantResult:
        """
        Process a user request through the full pipeline.
        
        Args:
            user_input: Natural language request from the user
            
        Returns:
            AssistantResult with the outcome
        """
        logger.info(f"Processing user input: {user_input}")
        
        # Validate input
        if not user_input or not user_input.strip():
            return AssistantResult(
                success=False,
                message="Empty input provided",
                error="Please provide a command or request",
            )
        
        user_input = user_input.strip()
        
        # Step 1: Query the LLM
        logger.debug("Step 1: Querying LLM")
        llm_result = self.llm.query(user_input)
        
        if not llm_result.success:
            return AssistantResult(
                success=False,
                message="Failed to process request with AI",
                error=llm_result.error,
            )
        
        # Step 2: Check AI response
        logger.debug("Step 2: Validating AI response")
        ai_response = llm_result.response
        
        if ai_response.cannot_process:
            return AssistantResult(
                success=False,
                message="Cannot process this request",
                error=ai_response.error or "Request outside supported capabilities",
            )
        
        if ai_response.error:
            return AssistantResult(
                success=False,
                message="AI could not fulfill request",
                error=ai_response.error,
            )
        
        if not ai_response.command:
            return AssistantResult(
                success=False,
                message="No command generated",
                error="AI did not generate a valid command",
            )
        
        command = ai_response.command
        
        # Step 3: Policy validation
        logger.debug("Step 3: Policy validation")
        try:
            policy_result = self.policy.validate_command(command)
            if not policy_result.allowed:
                return AssistantResult(
                    success=False,
                    message="Command blocked by policy",
                    command=command,
                    error=policy_result.reason,
                )
        except PolicyViolationError as e:
            logger.warning(f"Policy violation: {e.message}")
            return AssistantResult(
                success=False,
                message="Command blocked by security policy",
                command=command,
                error=e.message,
            )
        
        # Step 4: Execute command
        logger.debug("Step 4: Executing command")
        
        if self.config.require_confirmation:
            # In non-interactive mode, we'd need confirmation
            # For CLI, this will be handled by the CLI layer
            pass
        
        response = self.executor.execute(command)
        
        # Step 5: Return result
        if response.success:
            logger.info(f"Command executed successfully: {command.action.value}")
            return AssistantResult(
                success=True,
                message=f"Successfully executed: {command.action.value}",
                command=command,
                response=response,
            )
        else:
            logger.error(f"Command execution failed: {response.error}")
            return AssistantResult(
                success=False,
                message="Command execution failed",
                command=command,
                response=response,
                error=response.error,
            )
    
    def check_health(self) -> dict:
        """Check the health of the assistant components."""
        health = {
            "status": "healthy",
            "components": {},
        }
        
        # Check Ollama
        try:
            if self.llm.check_model_available():
                health["components"]["ollama"] = {
                    "status": "available",
                    "model": self.llm.model,
                }
            else:
                health["components"]["ollama"] = {
                    "status": "model_not_found",
                    "model": self.llm.model,
                }
                health["status"] = "degraded"
        except Exception as e:
            health["components"]["ollama"] = {
                "status": "error",
                "error": str(e),
            }
            health["status"] = "unhealthy"
        
        # Check logging
        try:
            log_path = Path(self.config.log_file)
            if log_path.exists() or log_path.parent.exists():
                health["components"]["logging"] = {
                    "status": "available",
                    "path": str(log_path),
                }
            else:
                health["components"]["logging"] = {
                    "status": "unavailable",
                    "path": str(log_path),
                }
        except Exception as e:
            health["components"]["logging"] = {
                "status": "error",
                "error": str(e),
            }
        
        return health


def create_assistant(
    config: Optional[Config] = None,
) -> AIAssistant:
    """Factory function to create an AIAssistant instance."""
    return AIAssistant(config=config)
