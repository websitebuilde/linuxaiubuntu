"""
Remote LLM integration via HTTP API (OpenAI compatible).

Handles communication with an external LLM API (like OpenAI, Anthropic, etc.)
using the standard chat completions format.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

from .config import get_config
from .commands import AIResponse
from .ai import LLMResult

logger = logging.getLogger(__name__)


class ApiLLM:
    """
    Interface to LLM via HTTP API.
    
    Sends requests to an OpenAI-compatible API endpoint.
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
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the API LLM interface.
        
        Args:
            api_key: API key for authentication (default: from config)
            model: Model name (default: from config)
            api_base_url: Base URL for API (default: from config)
            timeout: Request timeout in seconds (default: from config)
        """
        config = get_config()
        self.api_key = api_key or config.api_key
        self.model = model or config.api_model
        self.api_base_url = api_base_url or config.api_base_url
        self.timeout = timeout or config.ollama_timeout # reuse timeout setting or add new one? Config has command_timeout, maybe use that or hardcode default
        
        if not self.api_key:
            logger.warning("API key not provided. Requests may fail if auth is required.")
            
        # Ensure base URL ends correctly (remove trailing slash if present for cleaner joining, though manual join is safer)
        if self.api_base_url.endswith('/'):
            self.api_base_url = self.api_base_url[:-1]

    def query(self, user_input: str) -> LLMResult:
        """
        Send a query to the LLM API and get a structured response.
        
        Args:
            user_input: The natural language request from the user
            
        Returns:
            LLMResult with parsed response or error
        """
        if not self.api_key:
             return LLMResult(
                success=False,
                error="API key is missing. Please configure AI_ASSISTANT_API_KEY.",
            )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # Low temperature for deterministic outputs
            "response_format": {"type": "json_object"} # Force JSON mode if supported (OpenAI)
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        url = f"{self.api_base_url}/chat/completions"
        
        try:
            logger.debug(f"Sending request to {url} with model {self.model}")
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status_code = response.getcode()
                response_body = response.read().decode('utf-8')
                
                if status_code != 200:
                    logger.error(f"API returned status {status_code}: {response_body}")
                    return LLMResult(
                        success=False,
                        error=f"API error (status {status_code})",
                        raw_output=response_body
                    )
                
                logger.debug(f"Raw API response: {response_body[:500]}...")
                return self._parse_api_response(response_body)
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ""
            logger.error(f"HTTP error invoking API: {e.code} - {error_body}")
            return LLMResult(
                success=False,
                error=f"API HTTP error: {e.code} {e.reason}",
                raw_output=error_body
            )
        except urllib.error.URLError as e:
            logger.error(f"URL error invoking API: {e.reason}")
            return LLMResult(
                success=False,
                error=f"Network error: {e.reason}",
            )
        except Exception as e:
            logger.exception(f"Unexpected error invoking API: {e}")
            return LLMResult(
                success=False,
                error=f"Error communicating with API: {str(e)}",
            )

    def _parse_api_response(self, raw_output: str) -> LLMResult:
        """
        Parse the JSON response from the API.
        """
        try:
            data = json.loads(raw_output)
            
            # Extract content from OpenAI format
            # { "choices": [ { "message": { "content": "..." } } ] }
            choices = data.get("choices", [])
            if not choices:
                return LLMResult(
                    success=False,
                    error="API returned no choices",
                    raw_output=raw_output
                )
            
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                return LLMResult(
                    success=False,
                    error="API returned empty content",
                    raw_output=raw_output
                )
            
            # Now parse the inner JSON from the content string
            # Reusing logic similar to OllamaLLM._parse_response but adapted
            return self._parse_inner_json(content, raw_output)
            
        except json.JSONDecodeError as e:
             return LLMResult(
                success=False,
                error=f"Invalid JSON in API response: {str(e)}",
                raw_output=raw_output
            )

    def _parse_inner_json(self, content: str, full_raw_output: str) -> LLMResult:
        """Parse the JSON string returned by the model."""
        try:
             # Clean up markdown if present
            cleaned_content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(cleaned_content)
            response = AIResponse.model_validate(data)
            
            return LLMResult(
                success=True,
                response=response,
                raw_output=full_raw_output
            )
        except json.JSONDecodeError as e:
            # Try to recover using the regex extraction from ai.py if needed?
            # implementing a simple fallback extraction here
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                    response = AIResponse.model_validate(data)
                    return LLMResult(success=True, response=response, raw_output=full_raw_output)
                except Exception:
                    pass
            
            return LLMResult(
                success=False,
                error=f"Model output is not valid JSON: {str(e)}",
                raw_output=content
            )
        except Exception as e:
            return LLMResult(
                success=False,
                error=f"Error validating model response: {str(e)}",
                raw_output=content
            )

def create_api_llm(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    api_base_url: Optional[str] = None,
) -> ApiLLM:
    """Factory function to create an API LLM instance."""
    return ApiLLM(api_key=api_key, model=model, api_base_url=api_base_url)
