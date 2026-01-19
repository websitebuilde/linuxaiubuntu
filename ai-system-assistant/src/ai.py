"""
Local LLM integration via Ollama subprocess.

Handles communication with the Ollama LLM without using HTTP API.
"""

import subprocess
import json
import logging
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .config import get_config
from .commands import AIResponse, CommandRequest, CommandType, get_ai_response_schema


logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """Result from LLM invocation."""
    success: bool
    response: Optional[AIResponse] = None
    raw_output: Optional[str] = None
    error: Optional[str] = None


class OllamaLLM:
    """
    Interface to Ollama LLM via subprocess.
    
    Invokes `ollama run <model>` directly without HTTP API.
    """
    
    SYSTEM_PROMPT = '''You are a Linux system assistant that converts natural language requests into structured commands.

You MUST respond with ONLY valid JSON matching this exact schema:
{
    "command": {
        "action": "<action_type>",
        "target": "<target>",
        "parameters": null,
        "reason": "<brief explanation>"
    },
    "error": null,
    "cannot_process": false
}

Valid action types:
- "start_app": Start an application (target = app name like "firefox", "nautilus", "gedit")
- "kill_process": Kill a process (target = process name)
- "list_processes": List running processes (target = "all" or filter criteria)
- "restart_service": Restart a systemd service (target = service name without .service)
- "shell_query": Run allowed shell commands (target = command like "ps aux | grep python")

For shell_query, ONLY these commands are allowed: ps, pgrep, grep, top, htop, free, df, du, uptime, uname, cat, head, tail, ls, find, wc, sort, date, who, w

If you cannot process the request, respond with:
{
    "command": null,
    "error": "<explanation>",
    "cannot_process": true
}

CRITICAL RULES:
1. Output ONLY JSON - no markdown, no backticks, no explanations
2. Do NOT suggest dangerous commands (rm, sudo, chmod, etc.)
3. For starting apps, use the actual binary name (firefox, nautilus, gedit, etc.)
4. For services, use the service name without .service suffix

Examples:
User: "open firefox"
{"command": {"action": "start_app", "target": "firefox", "parameters": null, "reason": "Opening Firefox browser"}, "error": null, "cannot_process": false}

User: "show running processes"
{"command": {"action": "list_processes", "target": "all", "parameters": null, "reason": "Listing all processes"}, "error": null, "cannot_process": false}

User: "restart nginx"
{"command": {"action": "restart_service", "target": "nginx", "parameters": null, "reason": "Restarting nginx web server"}, "error": null, "cannot_process": false}

User: "find python processes"
{"command": {"action": "shell_query", "target": "ps aux | grep python", "parameters": null, "reason": "Finding Python processes"}, "error": null, "cannot_process": false}

User: "delete all files"
{"command": null, "error": "Cannot execute destructive operations like file deletion", "cannot_process": true}
'''

    def __init__(
        self,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        ollama_binary: Optional[str] = None,
    ):
        """
        Initialize the Ollama LLM interface.
        
        Args:
            model: Model name (default: from config)
            timeout: Timeout in seconds (default: from config)
            ollama_binary: Path to ollama binary (default: from config)
        """
        config = get_config()
        self.model = model or config.ollama_model
        self.timeout = timeout or config.ollama_timeout
        self.ollama_binary = ollama_binary or config.ollama_binary
        
        # Try common locations for ollama
        if not self._find_ollama():
            logger.warning(
                f"Ollama binary not found at {self.ollama_binary}. "
                "Will attempt to use 'ollama' from PATH."
            )
            self.ollama_binary = "ollama"
    
    def _find_ollama(self) -> bool:
        """Check if ollama binary exists at configured path."""
        import shutil
        return shutil.which(self.ollama_binary) is not None
    
    def query(self, user_input: str) -> LLMResult:
        """
        Send a query to the LLM and get a structured response.
        
        Args:
            user_input: The natural language request from the user
            
        Returns:
            LLMResult with parsed response or error
        """
        # Construct the full prompt
        full_prompt = f"{self.SYSTEM_PROMPT}\n\nUser: {user_input}\n"
        
        try:
            # Run ollama via subprocess
            logger.debug(f"Invoking Ollama with model: {self.model}")
            
            result = subprocess.run(
                [self.ollama_binary, "run", self.model],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                logger.error(f"Ollama returned non-zero exit code: {error_msg}")
                return LLMResult(
                    success=False,
                    error=f"Ollama error: {error_msg}",
                    raw_output=result.stdout,
                )
            
            raw_output = result.stdout.strip()
            logger.debug(f"Raw LLM output: {raw_output[:500]}...")
            
            # Parse the response
            return self._parse_response(raw_output)
            
        except subprocess.TimeoutExpired:
            logger.error(f"Ollama timed out after {self.timeout} seconds")
            return LLMResult(
                success=False,
                error=f"LLM request timed out after {self.timeout} seconds",
            )
        except FileNotFoundError:
            logger.error(f"Ollama binary not found: {self.ollama_binary}")
            return LLMResult(
                success=False,
                error=f"Ollama not found. Please install Ollama first.",
            )
        except Exception as e:
            logger.exception(f"Error invoking Ollama: {e}")
            return LLMResult(
                success=False,
                error=f"Error communicating with LLM: {str(e)}",
            )
    
    def _parse_response(self, raw_output: str) -> LLMResult:
        """
        Parse the raw LLM output into a structured response.
        
        Args:
            raw_output: Raw string output from the LLM
            
        Returns:
            LLMResult with parsed AIResponse or error
        """
        try:
            # Try to extract JSON from the output
            json_str = self._extract_json(raw_output)
            
            if not json_str:
                logger.error("No JSON found in LLM output")
                return LLMResult(
                    success=False,
                    error="LLM did not return valid JSON",
                    raw_output=raw_output,
                )
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate against schema
            response = AIResponse.model_validate(data)
            
            logger.info(f"Successfully parsed AI response: {response}")
            return LLMResult(
                success=True,
                response=response,
                raw_output=raw_output,
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return LLMResult(
                success=False,
                error=f"Invalid JSON in LLM response: {str(e)}",
                raw_output=raw_output,
            )
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return LLMResult(
                success=False,
                error=f"Error parsing LLM response: {str(e)}",
                raw_output=raw_output,
            )
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        Extract JSON from LLM output, handling various formats.
        
        The LLM might wrap JSON in markdown code blocks or include
        additional text before/after the JSON.
        """
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Try to find JSON object
        # Look for content between first { and last }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group()
        
        return None
    
    def check_model_available(self) -> bool:
        """Check if the configured model is available in Ollama."""
        try:
            result = subprocess.run(
                [self.ollama_binary, "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return self.model in result.stdout
        except Exception:
            return False


def create_llm(
    model: Optional[str] = None,
    timeout: Optional[int] = None,
) -> OllamaLLM:
    """Factory function to create an LLM instance."""
    return OllamaLLM(model=model, timeout=timeout)
