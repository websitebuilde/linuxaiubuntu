"""
Configuration module for AI System Assistant.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """Configuration settings for the AI assistant."""
    
    # Ollama settings
    ollama_model: str = "llama3"
    ollama_timeout: int = 30
    ollama_binary: str = "/usr/local/bin/ollama"
    
    # Logging settings
    log_file: str = "/var/log/ai-assistant.log"
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Application settings
    app_name: str = "AI System Assistant"
    app_version: str = "1.0.0"
    install_dir: str = "/opt/ai-system-assistant"
    
    # Execution settings
    max_output_lines: int = 100
    command_timeout: int = 60
    
    # Safety settings
    dry_run: bool = False
    require_confirmation: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure log directory exists (will be created by postinst)
        log_dir = Path(self.log_file).parent
        if not log_dir.exists():
            # Fallback to user-writable location for testing
            self.log_file = os.path.expanduser("~/.local/log/ai-assistant.log")
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            ollama_model=os.getenv("AI_ASSISTANT_MODEL", "llama3"),
            ollama_timeout=int(os.getenv("AI_ASSISTANT_TIMEOUT", "30")),
            ollama_binary=os.getenv("AI_ASSISTANT_OLLAMA_BIN", "/usr/local/bin/ollama"),
            log_file=os.getenv("AI_ASSISTANT_LOG", "/var/log/ai-assistant.log"),
            log_level=os.getenv("AI_ASSISTANT_LOG_LEVEL", "INFO"),
            dry_run=os.getenv("AI_ASSISTANT_DRY_RUN", "").lower() == "true",
            require_confirmation=os.getenv("AI_ASSISTANT_CONFIRM", "").lower() == "true",
        )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
