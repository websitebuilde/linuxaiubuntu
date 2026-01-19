"""
Security policy enforcement layer.

Implements hard rules for blocking dangerous operations.
All commands must pass through this layer before execution.
"""

import re
import logging
from typing import Set, List, Tuple, Optional
from dataclasses import dataclass

from .commands import CommandRequest, CommandType


logger = logging.getLogger(__name__)


class PolicyViolationError(Exception):
    """Raised when a command violates security policy."""
    
    def __init__(self, message: str, command: str, rule: str):
        self.message = message
        self.command = command
        self.rule = rule
        super().__init__(self.message)


@dataclass
class PolicyResult:
    """Result of policy validation."""
    allowed: bool
    reason: Optional[str] = None
    matched_rule: Optional[str] = None


class SecurityPolicy:
    """
    Security policy enforcement for command execution.
    
    Implements a blocklist approach - commands are allowed unless
    they match a blocked pattern.
    """
    
    # Commands that are NEVER allowed
    BLOCKED_COMMANDS: Set[str] = {
        # File destruction
        "rm", "rmdir", "shred", "unlink",
        # Disk operations
        "mkfs", "dd", "fdisk", "parted", "gdisk",
        # Mount operations
        "mount", "umount", "losetup",
        # User management
        "useradd", "userdel", "usermod", "passwd", "chpasswd",
        "groupadd", "groupdel", "groupmod",
        # Permission changes
        "chmod", "chown", "chgrp", "setfacl",
        # Network/firewall
        "iptables", "ip6tables", "nft", "ufw", "firewall-cmd",
        # Privilege escalation
        "sudo", "su", "pkexec", "doas",
        # System state
        "reboot", "shutdown", "poweroff", "halt", "init", "telinit",
        # Dangerous utilities
        "wget", "curl",  # Block to prevent downloading malicious content
        "nc", "netcat", "ncat",  # Network tools
        "python", "python3", "perl", "ruby", "bash", "sh", "zsh",  # Interpreters
        "eval", "exec",
        # Cron/scheduling
        "crontab", "at", "batch",
        # Kernel/modules
        "insmod", "rmmod", "modprobe",
    }
    
    # Shell commands that ARE allowed for shell_query
    ALLOWED_SHELL_COMMANDS: Set[str] = {
        "ps", "pgrep", "pidof",
        "grep", "egrep", "fgrep",
        "top", "htop",
        "free", "df", "du",
        "uptime", "uname", "hostname",
        "cat", "head", "tail", "less", "more",  # Read-only file viewing
        "ls", "find", "locate",
        "wc", "sort", "uniq",
        "date", "cal",
        "who", "w", "last",
        "systemctl status",  # Only status, not start/stop/restart
        "journalctl",
    }
    
    # Patterns that indicate dangerous operations
    BLOCKED_PATTERNS: List[Tuple[str, str]] = [
        (r"[;&|]", "Shell command chaining is not allowed"),
        (r"\$\(", "Command substitution is not allowed"),
        (r"`", "Backtick command substitution is not allowed"),
        (r">\s*\/", "Output redirection to root filesystem is not allowed"),
        (r"\.\.", "Parent directory traversal is not allowed"),
        (r"\/etc\/", "Direct access to /etc is not allowed"),
        (r"\/root", "Access to root home directory is not allowed"),
        (r"\/dev\/", "Direct device access is not allowed"),
        (r"\/proc\/", "Direct proc access is not allowed"),
        (r"\/sys\/", "Direct sys access is not allowed"),
    ]
    
    # Services that cannot be restarted
    PROTECTED_SERVICES: Set[str] = {
        "systemd", "init", "dbus", "udev",
        "NetworkManager", "networking",
        "sshd", "ssh",  # Prevent lockout
        "gdm", "lightdm", "sddm",  # Display managers
    }
    
    def __init__(self):
        """Initialize the security policy."""
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), message)
            for pattern, message in self.BLOCKED_PATTERNS
        ]
    
    def validate_command(self, request: CommandRequest) -> PolicyResult:
        """
        Validate a command request against security policy.
        
        Args:
            request: The command request to validate
            
        Returns:
            PolicyResult indicating if the command is allowed
            
        Raises:
            PolicyViolationError: If the command violates policy
        """
        # Check based on command type
        if request.action == CommandType.START_APP:
            return self._validate_start_app(request)
        elif request.action == CommandType.KILL_PROCESS:
            return self._validate_kill_process(request)
        elif request.action == CommandType.LIST_PROCESSES:
            return self._validate_list_processes(request)
        elif request.action == CommandType.RESTART_SERVICE:
            return self._validate_restart_service(request)
        elif request.action == CommandType.SHELL_QUERY:
            return self._validate_shell_query(request)
        else:
            raise PolicyViolationError(
                f"Unknown command type: {request.action}",
                str(request),
                "unknown_command_type"
            )
    
    def _validate_start_app(self, request: CommandRequest) -> PolicyResult:
        """Validate an application start request."""
        target = request.target.lower().strip()
        
        # Check if trying to start a blocked command
        first_word = target.split()[0] if target else ""
        if first_word in self.BLOCKED_COMMANDS:
            raise PolicyViolationError(
                f"Starting '{first_word}' is not allowed",
                request.target,
                "blocked_application"
            )
        
        # Check for dangerous patterns
        for pattern, message in self._compiled_patterns:
            if pattern.search(target):
                raise PolicyViolationError(
                    message,
                    request.target,
                    "dangerous_pattern"
                )
        
        return PolicyResult(allowed=True)
    
    def _validate_kill_process(self, request: CommandRequest) -> PolicyResult:
        """Validate a process kill request."""
        target = request.target.lower().strip()
        
        # Don't allow killing critical system processes
        critical_processes = {
            "init", "systemd", "dbus", "udev", "kernel",
            "kthreadd", "kworker", "ksoftirqd",
        }
        
        if target in critical_processes:
            raise PolicyViolationError(
                f"Killing '{target}' is not allowed - critical system process",
                request.target,
                "protected_process"
            )
        
        # Check for dangerous patterns
        for pattern, message in self._compiled_patterns:
            if pattern.search(target):
                raise PolicyViolationError(
                    message,
                    request.target,
                    "dangerous_pattern"
                )
        
        return PolicyResult(allowed=True)
    
    def _validate_list_processes(self, request: CommandRequest) -> PolicyResult:
        """Validate a process listing request."""
        # List processes is generally safe
        return PolicyResult(allowed=True)
    
    def _validate_restart_service(self, request: CommandRequest) -> PolicyResult:
        """Validate a service restart request."""
        target = request.target.lower().strip()
        
        # Remove .service suffix if present
        if target.endswith(".service"):
            target = target[:-8]
        
        # Check protected services
        if target in self.PROTECTED_SERVICES:
            raise PolicyViolationError(
                f"Restarting '{target}' is not allowed - protected service",
                request.target,
                "protected_service"
            )
        
        # Check for dangerous patterns
        for pattern, message in self._compiled_patterns:
            if pattern.search(target):
                raise PolicyViolationError(
                    message,
                    request.target,
                    "dangerous_pattern"
                )
        
        return PolicyResult(allowed=True)
    
    def _validate_shell_query(self, request: CommandRequest) -> PolicyResult:
        """Validate a shell query request."""
        target = request.target.strip()
        
        # Extract the base command
        # Handle pipes by checking each command in the pipeline
        parts = re.split(r'\s*\|\s*', target)
        
        for part in parts:
            words = part.strip().split()
            if not words:
                continue
                
            base_cmd = words[0].lower()
            
            # Check if the command is in the allowed list
            allowed = False
            for allowed_cmd in self.ALLOWED_SHELL_COMMANDS:
                if base_cmd == allowed_cmd or base_cmd == allowed_cmd.split()[0]:
                    allowed = True
                    break
            
            if not allowed:
                raise PolicyViolationError(
                    f"Shell command '{base_cmd}' is not in the allowed list",
                    request.target,
                    "disallowed_shell_command"
                )
            
            # Even for allowed commands, check for dangerous patterns
            for pattern, message in self._compiled_patterns:
                # Skip the pipe pattern check since we're handling pipes explicitly
                if pattern.pattern == r"[;&|]":
                    # Only check for ; and & not |
                    if re.search(r"[;&]", part):
                        raise PolicyViolationError(
                            "Command chaining with ; or & is not allowed",
                            request.target,
                            "dangerous_pattern"
                        )
                elif pattern.search(part):
                    raise PolicyViolationError(
                        message,
                        request.target,
                        "dangerous_pattern"
                    )
        
        return PolicyResult(allowed=True)
    
    def is_command_blocked(self, command: str) -> bool:
        """Quick check if a command name is in the blocked list."""
        return command.lower().strip() in self.BLOCKED_COMMANDS
    
    def get_blocked_commands(self) -> Set[str]:
        """Return the set of blocked commands."""
        return self.BLOCKED_COMMANDS.copy()
    
    def get_allowed_shell_commands(self) -> Set[str]:
        """Return the set of allowed shell commands."""
        return self.ALLOWED_SHELL_COMMANDS.copy()


# Global policy instance
_policy: Optional[SecurityPolicy] = None


def get_policy() -> SecurityPolicy:
    """Get the global security policy instance."""
    global _policy
    if _policy is None:
        _policy = SecurityPolicy()
    return _policy


def validate_command(request: CommandRequest) -> PolicyResult:
    """Convenience function to validate a command against the global policy."""
    return get_policy().validate_command(request)
