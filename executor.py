"""
Safe command executor.

Handles the actual execution of validated commands.
All commands pass through policy validation before reaching this module.
"""

import subprocess
import logging
import shutil
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .commands import CommandRequest, CommandResponse, CommandType
from .config import get_config


logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context information for command execution."""
    dry_run: bool = False
    timeout: int = 60
    capture_output: bool = True


class SafeExecutor:
    """
    Executes commands safely after policy validation.
    
    This class assumes commands have already been validated
    by the policy layer.
    """
    
    def __init__(self, context: Optional[ExecutionContext] = None):
        """
        Initialize the executor.
        
        Args:
            context: Execution context with settings
        """
        config = get_config()
        self.context = context or ExecutionContext(
            dry_run=config.dry_run,
            timeout=config.command_timeout,
        )
        self.max_output_lines = config.max_output_lines
    
    def execute(self, request: CommandRequest) -> CommandResponse:
        """
        Execute a command request.
        
        Args:
            request: The validated command request
            
        Returns:
            CommandResponse with execution result
        """
        logger.info(f"Executing command: {request.action.value} - {request.target}")
        
        if self.context.dry_run:
            logger.info("DRY RUN - command not actually executed")
            return CommandResponse(
                success=True,
                action=request.action,
                target=request.target,
                output=f"[DRY RUN] Would execute: {request.action.value} on {request.target}",
            )
        
        try:
            if request.action == CommandType.START_APP:
                return self._execute_start_app(request)
            elif request.action == CommandType.KILL_PROCESS:
                return self._execute_kill_process(request)
            elif request.action == CommandType.LIST_PROCESSES:
                return self._execute_list_processes(request)
            elif request.action == CommandType.RESTART_SERVICE:
                return self._execute_restart_service(request)
            elif request.action == CommandType.SHELL_QUERY:
                return self._execute_shell_query(request)
            else:
                return CommandResponse(
                    success=False,
                    action=request.action,
                    target=request.target,
                    error=f"Unknown action type: {request.action}",
                )
        except Exception as e:
            logger.exception(f"Error executing command: {e}")
            return CommandResponse(
                success=False,
                action=request.action,
                target=request.target,
                error=str(e),
            )
    
    def _execute_start_app(self, request: CommandRequest) -> CommandResponse:
        """Start an application."""
        app_name = request.target.strip()
        
        # Check if the application exists
        app_path = shutil.which(app_name)
        if not app_path:
            # Try common application locations
            common_paths = [
                f"/usr/bin/{app_name}",
                f"/usr/local/bin/{app_name}",
                f"/snap/bin/{app_name}",
                f"/usr/share/applications/{app_name}.desktop",
            ]
            for path in common_paths:
                if shutil.which(path) or (path.endswith('.desktop') and 
                    subprocess.run(['test', '-f', path], capture_output=True).returncode == 0):
                    app_path = path
                    break
        
        if not app_path:
            return CommandResponse(
                success=False,
                action=request.action,
                target=request.target,
                error=f"Application '{app_name}' not found",
            )
        
        try:
            # Start the application in the background
            # Use Popen to avoid blocking
            if app_path.endswith('.desktop'):
                # Use gtk-launch for .desktop files
                process = subprocess.Popen(
                    ['gtk-launch', app_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            else:
                process = subprocess.Popen(
                    [app_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            
            logger.info(f"Started application '{app_name}' with PID {process.pid}")
            
            return CommandResponse(
                success=True,
                action=request.action,
                target=request.target,
                output=f"Started '{app_name}' (PID: {process.pid})",
                exit_code=0,
            )
        except Exception as e:
            return CommandResponse(
                success=False,
                action=request.action,
                target=request.target,
                error=f"Failed to start '{app_name}': {str(e)}",
            )
    
    def _execute_kill_process(self, request: CommandRequest) -> CommandResponse:
        """Kill a process by name."""
        process_name = request.target.strip()
        
        # Get signal from parameters
        signal = "TERM"
        if request.parameters and "signal" in request.parameters:
            signal = request.parameters["signal"]
        
        try:
            # First, find the processes
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                return CommandResponse(
                    success=False,
                    action=request.action,
                    target=request.target,
                    error=f"No process found matching '{process_name}'",
                )
            
            pids = result.stdout.strip().split('\n')
            pids = [p for p in pids if p]  # Remove empty strings
            
            # Kill the processes
            kill_result = subprocess.run(
                ["pkill", f"-{signal}", "-f", process_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if kill_result.returncode == 0:
                return CommandResponse(
                    success=True,
                    action=request.action,
                    target=request.target,
                    output=f"Killed {len(pids)} process(es) matching '{process_name}'",
                    exit_code=0,
                )
            else:
                return CommandResponse(
                    success=False,
                    action=request.action,
                    target=request.target,
                    error=f"Failed to kill process: {kill_result.stderr}",
                    exit_code=kill_result.returncode,
                )
                
        except subprocess.TimeoutExpired:
            return CommandResponse(
                success=False,
                action=request.action,
                target=request.target,
                error="Operation timed out",
            )
    
    def _execute_list_processes(self, request: CommandRequest) -> CommandResponse:
        """List running processes."""
        try:
            # Determine filter
            filter_arg = None
            if request.parameters and "filter" in request.parameters:
                filter_arg = request.parameters["filter"]
            
            # Build command based on filter
            if filter_arg == "cpu":
                cmd = ["ps", "aux", "--sort=-%cpu"]
            elif filter_arg == "memory":
                cmd = ["ps", "aux", "--sort=-%mem"]
            else:
                cmd = ["ps", "aux"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # Limit output lines
            lines = result.stdout.strip().split('\n')
            if len(lines) > self.max_output_lines:
                lines = lines[:self.max_output_lines]
                lines.append(f"... (truncated, showing first {self.max_output_lines} lines)")
            
            output = '\n'.join(lines)
            
            return CommandResponse(
                success=True,
                action=request.action,
                target=request.target,
                output=output,
                exit_code=result.returncode,
            )
            
        except subprocess.TimeoutExpired:
            return CommandResponse(
                success=False,
                action=request.action,
                target=request.target,
                error="Operation timed out",
            )
    
    def _execute_restart_service(self, request: CommandRequest) -> CommandResponse:
        """Restart a systemd service."""
        service_name = request.target.strip()
        
        # Add .service suffix if not present
        if not service_name.endswith('.service'):
            service_name = f"{service_name}.service"
        
        try:
            # Check if service exists first
            check_result = subprocess.run(
                ["systemctl", "status", service_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            # Exit code 4 means service not found
            if check_result.returncode == 4:
                return CommandResponse(
                    success=False,
                    action=request.action,
                    target=request.target,
                    error=f"Service '{service_name}' not found",
                )
            
            # Restart the service
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode == 0:
                return CommandResponse(
                    success=True,
                    action=request.action,
                    target=request.target,
                    output=f"Successfully restarted '{service_name}'",
                    exit_code=0,
                )
            else:
                # Check if we need sudo
                if "Access denied" in result.stderr or "authentication required" in result.stderr.lower():
                    return CommandResponse(
                        success=False,
                        action=request.action,
                        target=request.target,
                        error="Permission denied. Service management requires root privileges.",
                        exit_code=result.returncode,
                    )
                return CommandResponse(
                    success=False,
                    action=request.action,
                    target=request.target,
                    error=result.stderr.strip() or "Failed to restart service",
                    exit_code=result.returncode,
                )
                
        except subprocess.TimeoutExpired:
            return CommandResponse(
                success=False,
                action=request.action,
                target=request.target,
                error="Operation timed out",
            )
    
    def _execute_shell_query(self, request: CommandRequest) -> CommandResponse:
        """Execute a shell query command."""
        query = request.target.strip()
        
        try:
            # Execute the command via shell for pipe support
            # This is safe because the policy layer has already validated
            # that only allowed commands are in the query
            result = subprocess.run(
                query,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.context.timeout,
            )
            
            # Limit output lines
            output = result.stdout.strip()
            lines = output.split('\n')
            if len(lines) > self.max_output_lines:
                lines = lines[:self.max_output_lines]
                lines.append(f"... (truncated, showing first {self.max_output_lines} lines)")
                output = '\n'.join(lines)
            
            return CommandResponse(
                success=result.returncode == 0,
                action=request.action,
                target=request.target,
                output=output if output else "(no output)",
                error=result.stderr.strip() if result.returncode != 0 else None,
                exit_code=result.returncode,
            )
            
        except subprocess.TimeoutExpired:
            return CommandResponse(
                success=False,
                action=request.action,
                target=request.target,
                error=f"Command timed out after {self.context.timeout} seconds",
            )


def create_executor(
    dry_run: bool = False,
    timeout: int = 60,
) -> SafeExecutor:
    """Factory function to create an executor instance."""
    context = ExecutionContext(dry_run=dry_run, timeout=timeout)
    return SafeExecutor(context=context)
