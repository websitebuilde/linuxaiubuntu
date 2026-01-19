#!/bin/bash
#
# Cubic chroot setup script for AI System Assistant
#
# Run this script inside the Cubic chroot environment to set up
# all components for the custom Ubuntu ISO.
#
# Usage: ./setup-chroot.sh
#

set -e

echo "=========================================="
echo "AI System Assistant - Cubic Chroot Setup"
echo "=========================================="
echo ""

# Update system
echo "[1/8] Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "[2/8] Installing dependencies..."
apt install -y \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    git

# Install Ollama
echo "[3/8] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama and pull model
echo "[4/8] Pulling llama3 model (this may take 10-20 minutes)..."
ollama serve &
OLLAMA_PID=$!
sleep 10

ollama pull llama3

# Verify model
echo "[5/8] Verifying model installation..."
ollama list

# Stop Ollama
kill $OLLAMA_PID 2>/dev/null || true
sleep 2

# Install AI System Assistant
echo "[6/8] Installing AI System Assistant..."

# Check if .deb exists
if [ -f "/tmp/ai-system-assistant_1.0.0_amd64.deb" ]; then
    dpkg -i /tmp/ai-system-assistant_1.0.0_amd64.deb
    apt-get install -f -y
else
    echo "WARNING: .deb package not found in /tmp/"
    echo "Please copy the package to the chroot before running this script."
    echo "Attempting source installation..."
    
    # Fallback to source installation
    if [ -d "/opt/ai-system-assistant/src" ]; then
        cd /opt/ai-system-assistant
        pip3 install pydantic
        
        # Create wrapper script
        mkdir -p /opt/ai-system-assistant/bin
        cat > /opt/ai-system-assistant/bin/ai-assistant << 'WRAPPER'
#!/bin/bash
cd /opt/ai-system-assistant
exec /usr/bin/python3 -m src.cli "$@"
WRAPPER
        chmod +x /opt/ai-system-assistant/bin/ai-assistant
        
        # Create symlink
        ln -sf /opt/ai-system-assistant/bin/ai-assistant /usr/local/bin/ai-assistant
        
        # Create log file
        touch /var/log/ai-assistant.log
        chmod 640 /var/log/ai-assistant.log
    else
        echo "ERROR: Neither .deb package nor source files found!"
        exit 1
    fi
fi

# Configure systemd services
echo "[7/8] Configuring systemd services..."

# Ollama service
cat > /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=root
Group=root
Restart=always
RestartSec=3
Environment="HOME=/usr/share/ollama"

[Install]
WantedBy=multi-user.target
EOF

# Copy AI Assistant service if not already present
if [ -f "/opt/ai-system-assistant/systemd/ai-assistant.service" ]; then
    cp /opt/ai-system-assistant/systemd/ai-assistant.service /etc/systemd/system/
fi

# Enable services
systemctl enable ollama.service
systemctl enable ai-assistant.service

# Create desktop entry
cat > /usr/share/applications/ai-assistant.desktop << 'EOF'
[Desktop Entry]
Name=AI System Assistant
Comment=Local AI for Ubuntu system management
Exec=gnome-terminal -- ai-assistant
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=System;Utility;
Keywords=ai;assistant;system;
EOF

# Create welcome message
cat > /etc/profile.d/ai-assistant-welcome.sh << 'EOF'
#!/bin/bash
if [ ! -f "$HOME/.ai-assistant-welcomed" ]; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║     AI System Assistant is ready!                     ║"
    echo "║                                                       ║"
    echo "║     Type 'ai-assistant' to start                      ║"
    echo "║     or use: ai-assistant \"your command\"               ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""
    touch "$HOME/.ai-assistant-welcomed"
fi
EOF
chmod +x /etc/profile.d/ai-assistant-welcome.sh

# Cleanup
echo "[8/8] Cleaning up..."
apt clean
apt autoclean
apt autoremove -y
rm -rf /tmp/*
rm -rf /var/tmp/*

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Installed components:"
echo "  - Ollama: $(ollama --version)"
echo "  - Python: $(python3 --version)"
echo "  - llama3 model: $(ollama list | grep llama3)"
echo ""
echo "Next steps:"
echo "  1. Exit the chroot (type 'exit' or press Ctrl+D)"
echo "  2. Complete the Cubic wizard to generate the ISO"
echo ""
