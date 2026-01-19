"""
Unit tests for the policy module.
"""

import pytest
from src.commands import CommandRequest, CommandType
from src.policy import (
    SecurityPolicy,
    PolicyViolationError,
    get_policy,
    validate_command,
)


class TestSecurityPolicy:
    """Tests for the SecurityPolicy class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.policy = SecurityPolicy()
    
    # === START_APP Tests ===
    
    def test_start_app_allowed(self):
        """Test that safe applications can be started."""
        request = CommandRequest(
            action=CommandType.START_APP,
            target="firefox",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    def test_start_app_blocked_rm(self):
        """Test that rm is blocked as an application."""
        request = CommandRequest(
            action=CommandType.START_APP,
            target="rm -rf /",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "blocked" in exc_info.value.message.lower() or "not allowed" in exc_info.value.message.lower()
    
    def test_start_app_blocked_sudo(self):
        """Test that sudo is blocked."""
        request = CommandRequest(
            action=CommandType.START_APP,
            target="sudo bash",
        )
        with pytest.raises(PolicyViolationError):
            self.policy.validate_command(request)
    
    def test_start_app_command_chaining_blocked(self):
        """Test that command chaining is blocked."""
        request = CommandRequest(
            action=CommandType.START_APP,
            target="firefox; rm -rf /",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "chaining" in exc_info.value.message.lower()
    
    # === KILL_PROCESS Tests ===
    
    def test_kill_process_allowed(self):
        """Test that normal processes can be killed."""
        request = CommandRequest(
            action=CommandType.KILL_PROCESS,
            target="firefox",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    def test_kill_process_systemd_blocked(self):
        """Test that systemd cannot be killed."""
        request = CommandRequest(
            action=CommandType.KILL_PROCESS,
            target="systemd",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "critical" in exc_info.value.message.lower()
    
    def test_kill_process_init_blocked(self):
        """Test that init cannot be killed."""
        request = CommandRequest(
            action=CommandType.KILL_PROCESS,
            target="init",
        )
        with pytest.raises(PolicyViolationError):
            self.policy.validate_command(request)
    
    # === LIST_PROCESSES Tests ===
    
    def test_list_processes_allowed(self):
        """Test that listing processes is always allowed."""
        request = CommandRequest(
            action=CommandType.LIST_PROCESSES,
            target="all",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    # === RESTART_SERVICE Tests ===
    
    def test_restart_service_allowed(self):
        """Test that normal services can be restarted."""
        request = CommandRequest(
            action=CommandType.RESTART_SERVICE,
            target="nginx",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    def test_restart_service_systemd_blocked(self):
        """Test that systemd service cannot be restarted."""
        request = CommandRequest(
            action=CommandType.RESTART_SERVICE,
            target="systemd",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "protected" in exc_info.value.message.lower()
    
    def test_restart_service_ssh_blocked(self):
        """Test that ssh service cannot be restarted (prevents lockout)."""
        request = CommandRequest(
            action=CommandType.RESTART_SERVICE,
            target="sshd",
        )
        with pytest.raises(PolicyViolationError):
            self.policy.validate_command(request)
    
    def test_restart_service_with_suffix(self):
        """Test that .service suffix is handled correctly."""
        request = CommandRequest(
            action=CommandType.RESTART_SERVICE,
            target="nginx.service",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    # === SHELL_QUERY Tests ===
    
    def test_shell_query_ps_allowed(self):
        """Test that ps command is allowed."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="ps aux",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    def test_shell_query_grep_allowed(self):
        """Test that grep command is allowed."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="grep python",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    def test_shell_query_pipe_allowed(self):
        """Test that piping between allowed commands works."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="ps aux | grep python",
        )
        result = self.policy.validate_command(request)
        assert result.allowed is True
    
    def test_shell_query_rm_blocked(self):
        """Test that rm command is blocked in shell queries."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="rm -rf /",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "not in the allowed list" in exc_info.value.message.lower()
    
    def test_shell_query_sudo_blocked(self):
        """Test that sudo is blocked in shell queries."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="sudo cat /etc/shadow",
        )
        with pytest.raises(PolicyViolationError):
            self.policy.validate_command(request)
    
    def test_shell_query_command_substitution_blocked(self):
        """Test that command substitution is blocked."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="ps aux | grep $(whoami)",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "substitution" in exc_info.value.message.lower()
    
    def test_shell_query_backtick_blocked(self):
        """Test that backtick substitution is blocked."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="ps aux | grep `whoami`",
        )
        with pytest.raises(PolicyViolationError):
            self.policy.validate_command(request)
    
    def test_shell_query_etc_blocked(self):
        """Test that /etc access is blocked."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="cat /etc/passwd",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "/etc" in exc_info.value.message.lower()
    
    # === Pattern Tests ===
    
    def test_parent_directory_traversal_blocked(self):
        """Test that .. is blocked."""
        request = CommandRequest(
            action=CommandType.START_APP,
            target="../../../bin/bash",
        )
        with pytest.raises(PolicyViolationError) as exc_info:
            self.policy.validate_command(request)
        assert "traversal" in exc_info.value.message.lower()
    
    def test_dev_access_blocked(self):
        """Test that /dev access is blocked."""
        request = CommandRequest(
            action=CommandType.SHELL_QUERY,
            target="cat /dev/sda",
        )
        with pytest.raises(PolicyViolationError):
            self.policy.validate_command(request)
    
    # === Utility Method Tests ===
    
    def test_is_command_blocked(self):
        """Test the is_command_blocked utility method."""
        assert self.policy.is_command_blocked("rm") is True
        assert self.policy.is_command_blocked("sudo") is True
        assert self.policy.is_command_blocked("firefox") is False
        assert self.policy.is_command_blocked("ps") is False
    
    def test_get_blocked_commands(self):
        """Test that blocked commands list is returned."""
        blocked = self.policy.get_blocked_commands()
        assert "rm" in blocked
        assert "sudo" in blocked
        assert "mkfs" in blocked
    
    def test_get_allowed_shell_commands(self):
        """Test that allowed shell commands list is returned."""
        allowed = self.policy.get_allowed_shell_commands()
        assert "ps" in allowed
        assert "grep" in allowed
        assert "df" in allowed


class TestGlobalPolicy:
    """Tests for global policy functions."""
    
    def test_get_policy_returns_instance(self):
        """Test that get_policy returns a SecurityPolicy instance."""
        policy = get_policy()
        assert isinstance(policy, SecurityPolicy)
    
    def test_validate_command_function(self):
        """Test the validate_command convenience function."""
        request = CommandRequest(
            action=CommandType.START_APP,
            target="firefox",
        )
        result = validate_command(request)
        assert result.allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
