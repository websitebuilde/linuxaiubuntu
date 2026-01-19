#!/usr/bin/env python3
"""
CLI interface for AI System Assistant.

Provides both interactive REPL mode and single-command execution.
"""

import argparse
import sys
import readline  # Enables arrow key support in input
from typing import Optional

from .main import AIAssistant, create_assistant, AssistantResult
from .config import Config, get_config
from . import __version__


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def colorize(text: str, color: str, bold: bool = False) -> str:
    """Apply color to text if terminal supports it."""
    if not sys.stdout.isatty():
        return text
    if bold:
        return f"{Colors.BOLD}{color}{text}{Colors.RESET}"
    return f"{color}{text}{Colors.RESET}"


def print_banner():
    """Print the application banner."""
    banner = f"""
{colorize('╔═══════════════════════════════════════════════════════╗', Colors.CYAN)}
{colorize('║', Colors.CYAN)}     {colorize('AI System Assistant', Colors.BLUE, bold=True)} v{__version__}                   {colorize('║', Colors.CYAN)}
{colorize('║', Colors.CYAN)}     Local AI for Ubuntu System Management             {colorize('║', Colors.CYAN)}
{colorize('╚═══════════════════════════════════════════════════════╝', Colors.CYAN)}
"""
    print(banner)


def print_help_text():
    """Print help text for interactive mode."""
    help_text = f"""
{colorize('Available Commands:', Colors.YELLOW, bold=True)}
  • Start an application: {colorize('"open firefox"', Colors.GREEN)} or {colorize('"start gedit"', Colors.GREEN)}
  • Kill a process: {colorize('"kill firefox"', Colors.GREEN)} or {colorize('"stop chrome"', Colors.GREEN)}
  • List processes: {colorize('"show running processes"', Colors.GREEN)} or {colorize('"list processes"', Colors.GREEN)}
  • Restart a service: {colorize('"restart nginx"', Colors.GREEN)} or {colorize('"restart ssh service"', Colors.GREEN)}
  • Shell queries: {colorize('"find python processes"', Colors.GREEN)} or {colorize('"show disk usage"', Colors.GREEN)}

{colorize('Special Commands:', Colors.YELLOW, bold=True)}
  • {colorize('help', Colors.CYAN)}    - Show this help
  • {colorize('health', Colors.CYAN)}  - Check system health
  • {colorize('exit', Colors.CYAN)}    - Exit the assistant
  • {colorize('quit', Colors.CYAN)}    - Exit the assistant

{colorize('Note:', Colors.GRAY)} Dangerous operations (rm, sudo, etc.) are blocked.
"""
    print(help_text)


def format_result(result: AssistantResult) -> str:
    """Format an assistant result for display."""
    output_lines = []
    
    if result.success:
        output_lines.append(colorize("✓ ", Colors.GREEN, bold=True) + result.message)
        
        if result.response and result.response.output:
            output_lines.append("")
            output_lines.append(colorize("Output:", Colors.CYAN))
            output_lines.append(result.response.output)
    else:
        output_lines.append(colorize("✗ ", Colors.RED, bold=True) + result.message)
        
        if result.error:
            output_lines.append(colorize(f"  Error: {result.error}", Colors.RED))
        
        if result.command:
            output_lines.append(
                colorize(f"  Command: {result.command.action.value} → {result.command.target}", Colors.GRAY)
            )
    
    return "\n".join(output_lines)


def run_interactive(assistant: AIAssistant):
    """Run the assistant in interactive REPL mode."""
    print_banner()
    print_help_text()
    
    prompt = colorize("ai> ", Colors.BLUE, bold=True)
    
    while True:
        try:
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            lower_input = user_input.lower()
            
            if lower_input in ("exit", "quit", "q"):
                print(colorize("\nGoodbye!", Colors.CYAN))
                break
            
            if lower_input == "help":
                print_help_text()
                continue
            
            if lower_input == "health":
                health = assistant.check_health()
                print(colorize("\nSystem Health:", Colors.YELLOW, bold=True))
                print(f"  Status: {colorize(health['status'], Colors.GREEN if health['status'] == 'healthy' else Colors.RED)}")
                for component, info in health.get("components", {}).items():
                    status_color = Colors.GREEN if info.get("status") == "available" else Colors.RED
                    print(f"  {component}: {colorize(info.get('status', 'unknown'), status_color)}")
                print()
                continue
            
            # Process the request
            result = assistant.process(user_input)
            print()
            print(format_result(result))
            print()
            
        except KeyboardInterrupt:
            print(colorize("\n\nInterrupted. Type 'exit' to quit.", Colors.YELLOW))
        except EOFError:
            print(colorize("\n\nGoodbye!", Colors.CYAN))
            break


def run_single_command(assistant: AIAssistant, command: str) -> int:
    """
    Run a single command and exit.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    result = assistant.process(command)
    print(format_result(result))
    return 0 if result.success else 1


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="ai-assistant",
        description="Local AI assistant for Ubuntu system management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ai-assistant                         Interactive mode
  ai-assistant "start firefox"         Start Firefox
  ai-assistant "list processes"        List running processes
  ai-assistant "restart nginx"         Restart nginx service
  ai-assistant --health                Check system health
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to execute (if not provided, starts interactive mode)"
    )
    
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "--health",
        action="store_true",
        help="Check system health and exit"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually execute commands, just show what would be done"
    )
    
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model to use (default: llama3)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="LLM timeout in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = get_config()
    
    if args.dry_run:
        config.dry_run = True
    if args.model:
        config.ollama_model = args.model
    if args.timeout:
        config.ollama_timeout = args.timeout
    if args.log_level:
        config.log_level = args.log_level
    
    # Create assistant
    assistant = create_assistant(config=config)
    
    # Handle health check
    if args.health:
        health = assistant.check_health()
        print(f"Status: {health['status']}")
        for component, info in health.get("components", {}).items():
            print(f"  {component}: {info.get('status', 'unknown')}")
        return 0 if health['status'] == 'healthy' else 1
    
    # Run in appropriate mode
    if args.command:
        return run_single_command(assistant, args.command)
    else:
        run_interactive(assistant)
        return 0


if __name__ == "__main__":
    sys.exit(main())
