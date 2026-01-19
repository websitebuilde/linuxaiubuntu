# AI System Assistant

A local AI assistant for Ubuntu that executes system commands safely using Ollama LLM.

## Features

- Natural language system command execution
- Local LLM (no cloud APIs, no internet required)
- Strict command validation via Pydantic schemas
- Policy enforcement blocking dangerous operations
- Systemd service integration
- Debian package for easy installation

## Supported Actions

- Start applications
- Kill processes by name
- List running processes
- Restart systemd services
- Limited shell queries (ps, grep)

## Installation

### From .deb Package

```bash
sudo dpkg -i ai-system-assistant_1.0.0_amd64.deb
sudo apt-get install -f  # Install dependencies if needed
```

### Manual Installation

```bash
cd /opt/ai-system-assistant
pip3 install -r requirements.txt
sudo cp systemd/ai-assistant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-assistant
sudo systemctl start ai-assistant
```

## Usage

### Interactive Mode

```bash
ai-assistant
```

### Single Command Mode

```bash
ai-assistant "start firefox"
ai-assistant "list all running processes"
ai-assistant "kill process named firefox"
ai-assistant "restart nginx service"
```

## Demo Commands

```bash
# List processes
ai-assistant "show me all running processes"

# Start an application
ai-assistant "open the file manager"

# Kill a process
ai-assistant "stop the firefox browser"

# Check system status
ai-assistant "what processes are using the most CPU"

# Restart a service
ai-assistant "restart the ssh service"
```

## Blocked Operations

The following commands are blocked by policy:
- rm, rmdir (file deletion)
- mkfs, dd (disk operations)
- mount, umount
- useradd, userdel, passwd (user management)
- iptables, ufw (firewall)
- sudo (privilege escalation)
- chmod, chown (permission changes)
- reboot, shutdown, init

## Logging

Logs are written to `/var/log/ai-assistant.log`

## Requirements

- Ubuntu 22.04 LTS or later
- Python 3.10+
- Ollama with llama3 model

## License

MIT License
